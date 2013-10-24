import ConfigParser
import logging
import datetime
import os
import time
import bisect
import apachelog
from __init__ import __version__ as daemon_version
from called_method import CalledMethod
import seek_utils
import utils
import settings

logger = logging.getLogger("elfstatsd")


class ElfStatsDaemon():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = os.path.join(settings.DAEMON_PID_DIR, 'elfstatsd.pid')
        self.pidfile_timeout = 5

        #Beginning of the analysis period
        self.period_start = datetime.datetime.now() + datetime.timedelta(seconds=-settings.INTERVAL)

        #Position in the file to start reading
        self.seek = {}

        #Storages for round statistics
        self.method_stats = {}
        self.response_codes_stats = {}
        self.metadata_stats = {}
        self.record_stats = {}

    def run(self):
        """Main daemon code."""

        while True:
            started = datetime.datetime.now()
            logger.info('elfstatsd v%s invoked at %s' % (daemon_version, str(started)))
            try:
                for current_log_file, previous_log_file, dump_file in settings.DATA_FILES:
                    self._process_log(started, current_log_file, previous_log_file, dump_file)
            except SystemExit:
                raise
            except BaseException as e:
                logger.exception('An error has occurred: %s' % e.message)
            finally:
                self.period_start = started
                self._good_night(started)

    def _good_night(self, started):
        """Wait until it's time for a new round.

        @param datetime started: starting time of current round
        """

        finished = datetime.datetime.now()
        elapsed_seconds = (finished - started).seconds
        elapsed_microseconds = (finished - started).microseconds
        elapsed_microseconds /= 1000000.0
        if elapsed_seconds < settings.INTERVAL:
            time.sleep(settings.INTERVAL - int(elapsed_seconds) - float(elapsed_microseconds))

    def _process_log(self, started, current_log_file, previous_log_file, dump_file):
        """
        Read records from log_file starting at started and dump them to dump_file.

        @param datetime started: start of the tracked period
        @param str current_log_file: path to log file
        @param str previous_log_file: if in-place rotation of access logs is used, path to log file before current
        @param str dump_file: file to save aggregated data
        """

        self._reset_storages(dump_file)

        self.metadata_stats[dump_file]['daemon_invoked'] = started.strftime("%Y-%m-%d %H:%M:%S")
        self.metadata_stats[dump_file]['daemon_version'] = daemon_version

        #Generate file names from a template and timestamps
        file_at_period_start = utils.format_filename(current_log_file, self.period_start)
        file_at_started = utils.format_filename(current_log_file, started)

        if not os.path.exists(file_at_started):
            logger.error('File %s is not found and will not be processed' % file_at_started)
            self._finalize_processing(dump_file)
            return

        if file_at_period_start != file_at_started:
            if not os.path.exists(file_at_period_start):
                logger.error('File %s is not found and will not be processed' % file_at_period_start)
                self._finalize_processing(dump_file)
                return

        #If the daemon has just started, it does not have associated seek for the input file
        #and it has to be set to period_start
        if not file_at_period_start in self.seek.keys():
            self.seek[file_at_period_start] = seek_utils.get_seek(file_at_period_start, self.period_start)

        if file_at_period_start == file_at_started:
            #All the records we are interested in are in the same file
            current_file_size = os.stat(file_at_started).st_size

            #Processing the situation when the log was rotated in-place between daemon executions.
            #In this situation we start reading file from start.
            cur_seek = self.seek[file_at_started]
            read_from_start = True if current_file_size < cur_seek or cur_seek == 0 else False

            if read_from_start and previous_log_file:
                replaced_file = utils.format_filename(previous_log_file, started)

                if not os.path.exists(replaced_file):
                    logger.error('File %s is not found and will not be processed' % replaced_file)
                else:
                    self.seek[replaced_file] = \
                        cur_seek if cur_seek > 0 else seek_utils.get_seek(replaced_file, self.period_start)
                    self._parse_file(dump_file, replaced_file)

            self._parse_file(dump_file, file_at_started, read_from_start=read_from_start, read_to_time=started)
        else:
            #First read previous file to the end, then current from beginning
            self._parse_file(dump_file, file_at_period_start)
            self._parse_file(dump_file, file_at_started, read_from_start=True, read_to_time=started)

        self._finalize_processing(dump_file)

    def _finalize_processing(self, dump_file):
        """
        Perform finalizing procedures after processing log files.
        @param str dump_file: path to file for dumping aggregated data
        """

        self._dump_stats(dump_file)

    def _parse_file(self, storage_key, file_path, read_from_start=False, read_to_time=None):
        """
        Read recent part of the log file, update statistics storages, adjust seek.
        If only file parameter is supplied, reads file from self.seek to the end.
        If the file is not found or cannot be read, an error is logged and the function returns

        @param str storage_key: a key to define statistics storage
        @param string file_path: path to file for parsing
        @param bool read_from_start: if true, read from beginning of file, otherwise from self.seek
        @param datetime read_to_time: if set, records are parsed until their time is greater or equal of parameter value
        Otherwise the file is read till the end.
        """

        f = open(file_path, 'r')

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

        log_parser = apachelog.parser(settings.ELF_FORMAT)

        while True:
            current_seek = f.tell()
            line = f.readline()

            if not line:
                #Reached end of file, record seek and stop
                self.seek[file_path] = current_seek
                logger.debug('Reached end of file %s, set seek in storage to %d' % (f.name, current_seek))
                break

            record = utils.parse_line(line, log_parser, settings.LATENCY_IN_MILLISECONDS)

            if not record:
                self._record_processed(storage_key, 'error')
                continue

            record_time = record.get_time()
            if record_time is None:
                logger.error('Could not process time string: ' + record.time)
                logger.error('Line: ' + record.line)
                self._record_processed(storage_key, 'error')
                continue
            self._update_metadata_time(storage_key, record_time)

            if read_to_time and record_time >= read_to_time:
                #Reached a record with timestamp higher than end of current analysis period
                #Stop here and leave it for the next invocation.
                self.seek[file_path] = current_seek
                logger.debug('Reached end of period, set seek for %s in storage to %d' % (f.name, current_seek))
                break

            status = self._process_record(storage_key, record)
            self._record_processed(storage_key, status)

        f.close()

    def _update_metadata_time(self, storage_key, time):
        """
        Update time-related metrics in metadata storage with given timestamp
        @param str storage_key: a key to define statistics storage
        @param str time: string representation of record time
        """

        if not 'first_record' in self.metadata_stats[storage_key] or \
                not self.metadata_stats[storage_key]['first_record']:
            self.metadata_stats[storage_key]['first_record'] = time
        self.metadata_stats[storage_key]['last_record'] = time

    def _record_processed(self, storage_key, status):
        """
        After the record is read and its status obtained, remember it in metadata storage
        and increase total number of records
        @param str storage_key: a key to define statistics storage
        @param str status: status of a record to be stored
        """

        self._inc_record_counter(storage_key, 'total')
        self._inc_record_counter(storage_key, status)

    def _inc_record_counter(self, storage_key, status):
        """
        Update aggregation counter for the given storage key according to the provided status
        @param str storage_key: a key to define statistics storage
        @param str status: one of 'total', 'parsed', 'skipped', 'error'
        """

        if not status in self.record_stats[storage_key]:
            self.record_stats[storage_key][status] = 0
        self.record_stats[storage_key][status] += 1

    def _process_record(self, storage_key, record):
        """
        Update statistics storages with values of a current record.

        @param str storage_key: a key to define statistics storage
        @param LogRecord record: record to process
        @return str status: status of processed record
        """

        method_name, status = record.get_method_name()
        if method_name:
            self._add_call(storage_key, method_name, record.latency)
        self._add_response_code(storage_key, record.response_code)
        return status

    def _dump_stats(self, file_path):
        """Dump statistics to DUMP_FILE in ConfigParser format."""

        storage_key = file_path
        dump = ConfigParser.RawConfigParser()
        self._dump_metadata_and_records(dump, storage_key)
        self._dump_methods(dump, storage_key)
        self._dump_response_codes(dump, storage_key)

        with open(file_path, 'wb') as f:
            dump.write(f)

    def _dump_metadata_and_records(self, dump, storage_key):
        """Save values from metadata and record storages to dump file"""

        storages = [('metadata', self.metadata_stats),
                    ('records_count', self.record_stats)]

        for storage in storages:
            dump.add_section(storage[0])
            for record_key in sorted(storage[1][storage_key].keys()):
                value = storage[1][storage_key][record_key]
                dump.set(storage[0], str(record_key), utils.format_value_for_munin(value))

    def _dump_methods(self, dump, storage_key):
        """Save values from methods storage to dump file"""

        for method in self.method_stats[storage_key].values():
            section = 'method_' + method.name
            dump.add_section(section)
            dump.set(section, 'calls', utils.format_value_for_munin(method.num_calls))
            dump.set(section, 'stalled_calls', utils.format_value_for_munin(method.stalled))
            dump.set(section, 'shortest', utils.format_value_for_munin(method.min))
            dump.set(section, 'longest', utils.format_value_for_munin(method.max))
            dump.set(section, 'average', utils.format_value_for_munin(method.avg))
            dump.set(section, 'p50', utils.format_value_for_munin(method.percentile(0.50)))
            dump.set(section, 'p90', utils.format_value_for_munin(method.percentile(0.90)))
            dump.set(section, 'p99', utils.format_value_for_munin(method.percentile(0.99)))

    def _dump_response_codes(self, dump, storage_key):
        """Save values from response codes storage to dump file"""

        section = 'response_codes'
        dump.add_section(section)
        for code, value in self.response_codes_stats[storage_key].iteritems():
            dump.set(section, str(code), utils.format_value_for_munin(value))
        #Add response codes from settings with 0 value if they are not found in logs
        #Is needed for Munin not to drop these codes from the charts
        for code in settings.RESPONSE_CODES:
            if not code in self.response_codes_stats[storage_key].keys():
                dump.set(section, str(code), utils.format_value_for_munin(''))

    def _reset_storages(self, storage_key):
        """
        Prepare storages for the next round.
        Save all necessary data to keep it in Munin output.

        @param str storage_key: a key to define statistics storage
        """

        if storage_key in self.method_stats:
            for method in self.method_stats[storage_key].values():
                method.calls = []
        else:
            self.method_stats[storage_key] = {}

        if storage_key in self.response_codes_stats:
            for code in self.response_codes_stats[storage_key]:
                self.response_codes_stats[storage_key][code] = 0
        else:
            self.response_codes_stats[storage_key] = {}

        self.metadata_stats[storage_key] = {}

        record_statuses = ['parsed', 'skipped', 'error', 'total']
        self.record_stats[storage_key] = {}
        for status in record_statuses:
            self.record_stats[storage_key][status] = 0

    def _get_called_method_stats(self, storage_key, name):
        """
        Get a CalledMethod instance from a storage.
        If there is no record, place a new there first.

        @param str storage_key: a key to define statistics storage
        @return CalledMethod method with stats set
        """

        try:
            return self.method_stats[storage_key][name]
        except KeyError:
            method = CalledMethod(name)
            self.method_stats[storage_key][name] = method
            return method

    def _add_call(self, storage_key, name, latency):
        """Add latency of a given call to the storage.

        @param str storage_key: a key to define statistics storage
        @param str name: call name
        @param int latency: call latency
        """

        method = self._get_called_method_stats(storage_key, name)
        bisect.insort(method.calls, latency)

    def _add_response_code(self, storage_key, code):
        """
        Remember response code in the storage.

        @param str storage_key: a key to define statistics storage
        @param int code: response code
        """

        if code in self.response_codes_stats[storage_key]:
            self.response_codes_stats[storage_key][code] += 1
        else:
            self.response_codes_stats[storage_key][code] = 1