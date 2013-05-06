"""A daemon parsing Apache access logs and dumping aggregated results to the files.
   These dump files can later be used by Munin or other clients to monitor server behavior in near-real-time.
"""
import ConfigParser
import logging
import datetime
import os
import re
import time
import math
import bisect
from daemon import runner
from types import NoneType
from logging.handlers import RotatingFileHandler
import munindaemon_settings

class MuninDaemon():

    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path =  os.path.join(munindaemon_settings.DAEMON_PID_DIR, 'munindaemon.pid')
        self.pidfile_timeout = 5

        #Beginning of the analysis period
        self.period_start = datetime.datetime.now() + datetime.timedelta(seconds=-munindaemon_settings.INTERVAL)

        #Position in the file to start reading
        self.seek = {}

        #Storages for round statistics
        self.method_stats = dict()
        self.response_codes_stats = dict()

    def run(self):
        """Main code of a daemon"""

        while True:
            started = datetime.datetime.now()
            logger.info('Daemon invoked at ' + str(started))

            for log_file, dump_file in munindaemon_settings.DATA_FILES:

                #Generate file names from a template and timestamps
                file_at_period_start = self.format_filename(log_file,self.period_start)
                file_at_started = self.format_filename(log_file,started)

                #File processing. If a file cannot be read, daemon just logs an error and continues execution.

                #If the daemon has just started, it does not have seek for the input file and it has to be adjusted to period_start
                if not file_at_period_start in self.seek.keys():
                    self.adjust_seek(file_at_period_start)

                if file_at_period_start == file_at_started:
                    #All the records we are interested in are in the same file
                    self.process_file(file_at_started, read_to_time=started)
                else:
                    #First read previous file to the end, then current from beginning
                    self.process_file(file_at_period_start)
                    self.process_file(file_at_started, read_from_start=True, read_to_time=started)

                self.dump_stats(dump_file)
                self.cleanup()

            self.period_start = started
            finished = datetime.datetime.now()
            elapsed_seconds = (finished-started).seconds
            elapsed_microseconds = (finished-started).microseconds
            elapsed_microseconds /= 1000000.0
            if elapsed_seconds < munindaemon_settings.INTERVAL:
                time.sleep(munindaemon_settings.INTERVAL-elapsed_seconds-elapsed_microseconds)

    def parse_line(self,line):
        """
        Convert a line from a log into LogRecord.

        Contains code that parses log records. This code may need to be changed if Apache log format changes.
        """

        record = LogRecord()
        split = line.split(" ")
        record.line = line
        try:
            record.time = split[3][1:]
            record.request = split[6]
            record.response_code = int(split[8])
            #Latency rounded to the nearest millisecond
            record.latency = int(round(int(split[-1])/1000.0))
        except ValueError:
            logger.warn('Parser has caught an error while processing the following record: ')
            logger.warn(line)
            return None
        return record

    def adjust_seek(self, file):
        """Is needed to correctly set seek value when daemon is launched or file name changes"""
        try:
            f = open(file, 'r')
        except IOError as e:
            logger.error('Could not open file %s' %file)
            logger.error('I/O error({0}): {1}'.format(e.errno, e.strerror))
            return 1

        while True:
            seek_candidate = f.tell()
            line = f.readline()
            if not line:
                #reached end of file, maybe no new records were added within tracked period
                # or we have opened a newly created empty file
                self.seek[file] = seek_candidate
                break
            record = self.parse_line(line)
            if record:
                dt = record.get_time()
                if dt and dt > self.period_start:
                    self.seek[file] = seek_candidate
                    break
        f.close()

    def format_filename(self, name, dt):
        """Generate file name from a template containing formatted string and time value"""
        return dt.strftime(name)

    def process_file(self, file, read_from_start=False, read_to_time=None):
        """Read recent part of the log file, update statistics storages, adjust seek.

        If only file parameter is supplied, reads file from self.seek to the end.

        @param string file: path to file for parsing
        @param bool read_from_start: if true, read from beginning of file, otherwise from self.seek
        @param datetime read_to_time: if set, records are parsed until their time is greater or equal of parameter value. \
        Otherwise the file is read till the end.

        If the file is not found or cannot be read, an error is logged and the function returns
        """
        try:
            f = open(file, 'r')
        except IOError as e:
            logger.error('Could not open file %s' %file)
            logger.error('I/O error({0}): {1}'.format(e.errno, e.strerror))
            return 1

        if not read_from_start:
            f.seek(self.seek[file])

        while True:
            current_seek = f.tell()
            line = f.readline()
            if not line:
                #Reached end of file, record seek and stop
                self.seek[file] = current_seek
                break
            record = self.parse_line(line)
            if not record:
                continue
            if read_to_time:
                time = record.get_time()
                if type(time) == NoneType:
                    logger.error('Could not process time string: ' + record.time)
                    logger.error('Line: ' + record.line)
                    continue
                if time >= read_to_time:
                    #Reached a record with timestamp higher than end of current analysis period
                    #Stop here and leave it for the next invocation.
                    self.seek[file] = current_seek
                    break
            if record.is_valid():
                self.process_record(record)
            else:
                logger.debug('Request not processed: ' + record.request)

    def process_record(self,record):
        """Update statistics storages with values of a current record

        @param LogRecord|None record: record to process

        """
        if record:
            self.add_call(record.get_method_name(),record.latency)
            self.add_response_code(record.response_code)

    def dump_stats(self, file):
        """Dump statistics to DUMP_FILE in ConfigParser format"""
        dump = ConfigParser.RawConfigParser()
        for method in self.method_stats.values():
            section = 'method_' + method.name
            dump.add_section(section)
            dump.set(section,'calls',len(method.calls))
            dump.set(section,'stalled_calls',method.stalled())
            dump.set(section, 'shortest', method.min())
            dump.set(section, 'longest', method.max())
            dump.set(section,'average', method.avg())
            dump.set(section,'p50',method.percentile(0.50))
            dump.set(section,'p90',method.percentile(0.90))
            dump.set(section,'p99',method.percentile(0.99))

        section = 'response_codes'
        dump.add_section(section)
        for code,value in self.response_codes_stats.iteritems():
            dump.set(section,str(code),value)
        #Add response codes from settings with 0 value if they are not met in logs
        #Is needed for Munin not to drop these codes from the charts
        for code in munindaemon_settings.RESPONSE_CODES:
            if not code in self.response_codes_stats.keys():
                dump.set(section,str(code),0)


        with open(file, 'wb') as f:
            dump.write(f)

    def cleanup(self):
        """Prepare values for the next round"""
        self.method_stats.clear()
        self.response_codes_stats.clear()

    def get_called_method_stats(self,name):
        """Get a CalledMethod instance from a storage. If there is no record, place a new there first."""
        try:
            return self.method_stats[name]
        except KeyError:
            method = CalledMethod(name)
            self.method_stats[name] = method
            return method

    def add_call(self,name,latency):
        """Adds latency of a given call to the storage"""
        method = self.get_called_method_stats(name)
        bisect.insort(method.calls,latency)

    def add_response_code(self,code):
        """Remember response code in the storage"""
        if code in self.response_codes_stats:
            self.response_codes_stats[code] += 1
        else:
            self.response_codes_stats[code] = 1


class LogRecord():

    def __init__(self):
        #stored in raw string, converted in access method
        self.time = ''
        self.request = ''
        self.response_code = 0
        self.latency = 0
        self.line = ''

    def get_time(self):
        dt = None
        try:
            dt = datetime.datetime.strptime(self.time,'%d/%b/%Y:%H:%M:%S')
        except ValueError:
            logger.warn('Could not parse time string "%s" for the following log record:' % self.time)
            logger.warn(self.line)
        return dt

    def get_method_name(self):
        """Return cleaned method name from a request string"""
        split = self.request.split('/')
        name = split[2] + '_' + split[3].split('?')[0]
        valid_name = re.sub(munindaemon_settings.BAD_SYMBOLS,'',name)
        return valid_name

    def is_valid(self):
        """Determine whether a record is in proper form for processing"""
        return re.search(munindaemon_settings.VALID_REQUEST,self.request)

class CalledMethod():

    def __init__(self,name):
        self.name = name
        self.calls = list()

    def percentile(self, percent):
        """Compute percentile of values in an array

        @param float percent: percent from 0.0 to 1.0
        """
        k = (len(self.calls)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return self.calls[int(k)]
        d0 = self.calls[int(f)] * (c-k)
        d1 = self.calls[int(c)] * (k-f)
        return int(round(d0+d1))

    def stalled(self):
        stalled = [i for i in self.calls if i > munindaemon_settings.STALLED_CALL_THRESHOLD]
        return len(stalled)

    def min(self):
        return self.calls[0]

    def max(self):
        return self.calls[-1]

    def avg(self):
        return sum(self.calls)/len(self.calls)


daemon = MuninDaemon()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = RotatingFileHandler(os.path.join(munindaemon_settings.DAEMON_LOG_DIR, 'munindaemon.log'),
    maxBytes=munindaemon_settings.MAX_LOG_FILE_SIZE, backupCount=munindaemon_settings.MAX_LOG_FILES)
handler.setFormatter(formatter)
logger.addHandler(handler)

daemon_runner = runner.DaemonRunner(daemon)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve=[handler.stream]
daemon_runner.do_action()
