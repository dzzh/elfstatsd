import logging
import datetime
import os
import time
import apachelog
import seek_utils
import utils
import settings
from storage.storage_manager import StorageManager
from __init__ import __version__ as daemon_version

DEFAULT_DAEMON_PID_DIR = '/var/run/elfstatsd'
DEFAULT_INTERVAL = 300

logger = logging.getLogger('elfstatsd')


class ElfStatsDaemon():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'

        self.pidfile_path = os.path.join(getattr(settings, 'DAEMON_PID_DIR', DEFAULT_DAEMON_PID_DIR), 'elfstatsd.pid')
        self.pidfile_timeout = 5

        #Beginning of the analysis period
        self.interval = getattr(settings, 'INTERVAL', DEFAULT_INTERVAL)
        self.period_start = datetime.datetime.now() + datetime.timedelta(seconds=-self.interval)

        #Position in the file to start reading
        self.seek = {}

        #Statistics storages
        self.sm = StorageManager()

    def run(self):
        """Main daemon code. Run processing for all the files and manage error handling."""

        while True:
            started = datetime.datetime.now()
            logger.info('elfstatsd v%s invoked at %s' % (daemon_version, str(started)))
            data_files = getattr(settings, 'DATA_FILES', [])

            try:
                for current_log_file, previous_log_file, dump_file in data_files:
                    try:
                        self._process_log(started, current_log_file, previous_log_file, dump_file)
                    except BaseException as e:
                        logger.exception('An error has occurred: %s' % e.message)
            except SystemExit:
                raise
            finally:
                self.period_start = started
                self._good_night(started)

    def _good_night(self, started):
        """
        Wait until it's time for a new round.

        @param datetime started: starting time of current round
        """

        finished = datetime.datetime.now()
        elapsed_seconds = (finished - started).seconds
        elapsed_microseconds = (finished - started).microseconds
        elapsed_microseconds /= 1000000.0
        if elapsed_seconds < self.interval:
            time.sleep(self.interval - int(elapsed_seconds) - float(elapsed_microseconds))

    def _process_log(self, started, current_log_file, previous_log_file, dump_file):
        """
        Read records from associated log files starting at `started` time and dump their statistics to `dump_file`.

        @param datetime started: timestamp for the beginning of the tracked period
        @param str current_log_file: path to access log file
        @param str previous_log_file: if in-place rotation of access logs is used, path to log file before current
        @param str dump_file: file to save aggregated data
        """

        #Reset all storages
        self.sm.reset(dump_file)

        #Save metadata
        self.sm.get('metadata').set(dump_file, 'daemon_invoked', started.strftime('%Y-%m-%d %H:%M:%S'))
        self.sm.get('metadata').set(dump_file, 'daemon_version', 'v'+daemon_version)

        #Generate file names from a template and timestamps
        file_at_period_start, dt_at_period_start = utils.format_filename(current_log_file, self.period_start)
        file_at_started, dt_at_started = utils.format_filename(current_log_file, started)

        if not os.path.exists(file_at_started):
            logger.error('File %s is not found and will not be processed' % file_at_started)

        elif file_at_period_start != file_at_started and not os.path.exists(file_at_period_start):
                logger.error('File %s is not found and will not be processed' % file_at_period_start)

        else:
            #If the daemon has just started, it does not have associated seek for the input file
            #and it has to be set to period_start
            if not file_at_period_start in self.seek.keys():
                self.seek[file_at_period_start] = seek_utils.get_seek(
                    file_at_period_start, self.period_start + dt_at_period_start)

            if file_at_period_start == file_at_started:
                #All the records we are interested in are in the same file
                current_file_size = os.stat(file_at_started).st_size

                #Processing the situation when the log was rotated in-place between daemon executions.
                #In this situation we start reading the file from the beginning.
                cur_seek = self.seek[file_at_started]
                read_from_start = True if current_file_size < cur_seek or cur_seek == 0 else False

                if read_from_start and previous_log_file:
                    replaced_file, dt_at_replaced = utils.format_filename(previous_log_file, started)

                    if not os.path.exists(replaced_file):
                        logger.error('File %s is not found and will not be processed' % replaced_file)
                    else:
                        self.seek[replaced_file] = \
                            cur_seek if cur_seek > 0 else seek_utils.get_seek(
                                replaced_file, self.period_start + dt_at_replaced)
                        self._parse_file(dump_file, replaced_file)

                self._parse_file(dump_file, file_at_started, read_from_start, started + dt_at_started)
            else:
                #First read previous file to the end, then current from beginning
                self._parse_file(dump_file, file_at_period_start)
                self._parse_file(dump_file, file_at_started, True, started + dt_at_started)

        self.sm.dump(dump_file)

    def _parse_file(self, storage_key, file_path, read_from_start=False, read_to_time=None):
        """
        Read recent part of the log file, update statistics storages and adjust seek.
        If only file parameter is supplied, read file from self.seek to the end.
        If the file is not found or cannot be read, log an error and return.

        @param str storage_key: a key to define statistics storage
        @param string file_path: path to file for parsing
        @param bool read_from_start: if true, read from the beginning of file, otherwise from `self.seek`
        @param datetime read_to_time: if set, records are parsed until their time is greater or equal of parameter value
        Otherwise the file is read till the end.
        """

        with open(file_path, 'r') as f:
            if read_from_start:
                logger.debug('Reading file %s from the beginning to %s'
                             % (file_path, read_to_time))
            else:
                logger.debug('Reading file %s from position %d to %s'
                             % (file_path, self.seek[file_path], read_to_time or 'the end'))

            if not read_from_start:
                f.seek(self.seek[file_path])
                logger.debug('Setting seek for file %s to %d based on a value from the storage'
                             % (f.name, self.seek[file_path]))

            log_parser = apachelog.parser(getattr(settings, 'ELF_FORMAT', ''))

            while True:
                current_seek = f.tell()
                line = f.readline()

                if not line:
                    #Reached end of file, record seek and stop
                    self.seek[file_path] = current_seek
                    logger.debug('Reached end of file %s, set seek in storage to %d' % (f.name, current_seek))
                    break

                record = utils.parse_line(line, log_parser, getattr(settings, 'LATENCY_IN_MILLISECONDS', False))

                if not record:
                    self._count_record(storage_key, 'error')
                    continue

                record_time = record.get_time()
                if record_time is None:
                    logger.error('Could not process time string: ' + record.time)
                    logger.error('Line: ' + record.line)
                    self._count_record(storage_key, 'error')
                    continue

                if read_to_time and record_time >= read_to_time:
                    #Reached a record with timestamp higher than end of current analysis period
                    #Stop here and leave it for the next invocation.
                    self.seek[file_path] = current_seek
                    logger.debug('Reached end of period, set seek for %s in storage to %d' % (f.name, current_seek))
                    break

                status = self._process_record(storage_key, record)
                self._count_record(storage_key, status)

    def _count_record(self, storage_key, status):
        """
        After the record is read and its status is obtained, count this status in records storage
        and increase the total number of records
        @param str storage_key: a key to define statistics storage
        @param str status: status of a record to be stored
        """

        self.sm.get('records').inc_counter(storage_key, 'total')
        self.sm.get('records').inc_counter(storage_key, status)

    def _process_record(self, storage_key, record):
        """
        Update statistics storages with values of a current record.

        @param str storage_key: access log-related key to define statistics storage
        @param LogRecord record: record to process
        @return str status: status of processed record
        """
        request = record.get_processed_request()
        if request.status == 'parsed':
            self.sm.get('methods').set(storage_key, request.get_method_id(), record)
            self.sm.get('response_codes').inc_counter(storage_key, record.response_code)
            self.sm.get('metadata').update_time(storage_key, record.get_time())
            for key in sorted(request.patterns.keys()):
                self.sm.get('patterns').set(storage_key, key, request.patterns[key])

        return request.status