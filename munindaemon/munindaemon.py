"""A daemon parsing Apache access logs and dumping aggregated results to the files.
   These dump files can later be used by Munin or other clients to monitor server behavior in near-real-time.
"""
import ConfigParser
import logging
import datetime
import cStringIO
import traceback
import apachelog
import os
import re
import time
import math
import bisect
from daemon import runner
from types import NoneType
from logging.handlers import RotatingFileHandler
from __init__ import __version__ as daemon_version
import munindaemon_settings

#3 for milliseconds, 6 for microseconds, etc.
LATENCY_PRECISION = 3

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
            try:
                started = datetime.datetime.now()
                logger.info('Munindaemon version %s invoked at %s' %(daemon_version, str(started)))

                for log_file, dump_file in munindaemon_settings.DATA_FILES:

                    #create entries in dictionaries with aggregated data
                    storage_key = dump_file
                    if not storage_key in self.method_stats:
                        self.method_stats[storage_key] = dict()
                        self.response_codes_stats[storage_key] = dict()

                    #Generate file names from a template and timestamps
                    file_at_period_start = self.format_filename(log_file,self.period_start)
                    file_at_started = self.format_filename(log_file,started)

                    #File processing. If a file cannot be read, daemon just logs an error and continues execution.

                    #If the daemon has just started, it does not have seek for the input file and it has to be adjusted to period_start
                    if not file_at_period_start in self.seek.keys():
                        self.set_seek(file_at_period_start)

                    if file_at_period_start == file_at_started:
                        #All the records we are interested in are in the same file
                        self.process_file(storage_key, file_at_started, read_to_time=started)
                    else:
                        #First read previous file to the end, then current from beginning
                        self.process_file(storage_key, file_at_period_start)
                        self.process_file(storage_key, file_at_started, read_from_start=True, read_to_time=started)

                    self.dump_stats(dump_file)
                    self.cleanup(storage_key)

                self.period_start = started
                finished = datetime.datetime.now()
                elapsed_seconds = (finished-started).seconds
                elapsed_microseconds = (finished-started).microseconds
                elapsed_microseconds /= 1000000.0
                if elapsed_seconds < munindaemon_settings.INTERVAL:
                    time.sleep(munindaemon_settings.INTERVAL-elapsed_seconds-elapsed_microseconds)
            except SystemExit:
                raise
            except:
                logger.exception('An error has occurred.')

    def parse_line(self, line, log_parser):
        """
        Convert a line from a log into LogRecord.

        Contains code that parses log records. This code may need to be changed if Apache log format changes.
        @param unicode line: log line to parse
        @param ApacheLogParser log_parser: instance of ApacheLogParser containing log format description
        """
        record = LogRecord()

        try:
            data = log_parser.parse(line)
            record.line = line
            record.time = apachelog.parse_date(data['%t'])
            record.request = data['%r'].split(' ')[1]
            record.response_code = int(data['%>s'])
            #Latency rounded to the nearest millisecond
            record.latency = self.parse_latency(data['%D'])
        except apachelog.ApacheLogParserError:
            logger.warn('Parser has caught an error while processing the following record: ')
            logger.warn(line)
            return None
        return record

    def parse_latency(self, latency):
        """
        Convert string value of latency to integer with predefined precision.
        Work with integer and float formats, e.g. '123456' -> 123 and '2.123456789' -> 2123.
        @param str latency: latency representation from a log file
        @return int parsed latency
        """
        if not '.' in latency:
            return int(round(int(latency) / float(10 ** LATENCY_PRECISION)))
        else:
            return int(round(float(latency), LATENCY_PRECISION) * 10 ** LATENCY_PRECISION)


    def set_seek(self, file):
        """Is needed to correctly set seek value when daemon launches"""
        try:
            f = open(file, 'r')
        except IOError as e:
            logger.error('Could not open file %s' %file)
            logger.error('I/O error({0}): {1}'.format(e.errno, e.strerror))
            return

        log_parser = apachelog.parser(munindaemon_settings.APACHE_LOG_FORMAT)

        while True:
            seek_candidate = f.tell()
            line = f.readline()
            if not line:
                #reached end of file, maybe no new records were added within tracked period
                # or we have opened a newly created empty file
                self.seek[file] = seek_candidate
                break
            record = self.parse_line(line, log_parser)
            if record:
                dt = record.get_time()
                if dt and dt > self.period_start:
                    self.seek[file] = seek_candidate
                    break
        f.close()

    def format_filename(self, name, dt):
        """Generate file name from a template containing formatted string and time value"""
        return dt.strftime(name)

    def process_file(self, storage_key, file, read_from_start=False, read_to_time=None):
        """Read recent part of the log file, update statistics storages, adjust seek.

        If only file parameter is supplied, reads file from self.seek to the end.

        @param str storage_key: a key to define statistics storage
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
            return

        if not read_from_start:
            f.seek(self.seek[file])

        log_parser = apachelog.parser(munindaemon_settings.APACHE_LOG_FORMAT)

        while True:
            current_seek = f.tell()
            line = f.readline()
            if not line:
                #Reached end of file, record seek and stop
                self.seek[file] = current_seek
                break
            record = self.parse_line(line,log_parser)
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
            if record:
                self.process_record(storage_key, record)

    def process_record(self, storage_key, record):
        """Update statistics storages with values of a current record
        @param str storage_key: a key to define statistics storage
        @param LogRecord record: record to process
        """
        method_name = record.get_method_name()
        if method_name:
            self.add_call(storage_key, method_name, record.latency)
        self.add_response_code(storage_key, record.response_code)

    def dump_stats(self, file):
        """Dump statistics to DUMP_FILE in ConfigParser format"""
        storage_key = file
        dump = ConfigParser.RawConfigParser()
        for method in self.method_stats[storage_key].values():
            section = 'method_' + method.name
            dump.add_section(section)
            dump.set(section,'calls',self.format_value(method.num_calls))
            dump.set(section,'stalled_calls',self.format_value(method.stalled))
            dump.set(section, 'shortest', self.format_value(method.min))
            dump.set(section, 'longest', self.format_value(method.max))
            dump.set(section,'average', self.format_value(method.avg))
            dump.set(section,'p50',self.format_value(method.percentile(0.50)))
            dump.set(section,'p90',self.format_value(method.percentile(0.90)))
            dump.set(section,'p99',self.format_value(method.percentile(0.99)))

        section = 'response_codes'
        dump.add_section(section)
        for code,value in self.response_codes_stats[storage_key].iteritems():
            dump.set(section,str(code),self.format_value(value))
        #Add response codes from settings with 0 value if they are not met in logs
        #Is needed for Munin not to drop these codes from the charts
        for code in munindaemon_settings.RESPONSE_CODES:
            if not code in self.response_codes_stats[storage_key].keys():
                dump.set(section,str(code),self.format_value(''))

        with open(file, 'wb') as f:
            dump.write(f)

    def format_value(self,value):
        """
        Formats value for proper processing by Munin.
        """
        return value if value else 'U'

    def cleanup(self,storage_key):
        """Prepare values for the next round.
           Save the method names and existed response codes to keep them in Munin output.
           @param str storage_key: a key to define statistics storage
        """
        for method in self.method_stats[storage_key].values():
            method.calls = []
        for code in self.response_codes_stats[storage_key]:
            self.response_codes_stats[storage_key][code] = 0

    def get_called_method_stats(self,storage_key,name):
        """Get a CalledMethod instance from a storage. If there is no record, place a new there first.
        @param str storage_key: a key to define statistics storage
        """
        try:
            return self.method_stats[storage_key][name]
        except KeyError:
            method = CalledMethod(name)
            self.method_stats[storage_key][name] = method
            return method

    def add_call(self,storage_key,name,latency):
        """Adds latency of a given call to the storage
        @param str storage_key: a key to define statistics storage
        """
        method = self.get_called_method_stats(storage_key,name)
        bisect.insort(method.calls,latency)

    def add_response_code(self,storage_key,code):
        """Remember response code in the storage
        @param str storage_key: a key to define statistics storage
        """
        if code in self.response_codes_stats[storage_key]:
            self.response_codes_stats[storage_key][code] += 1
        else:
            self.response_codes_stats[storage_key][code] = 1


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
            dt = datetime.datetime.strptime(self.time[0],'%Y%m%d%H%M%S')
        except ValueError:
            logger.warn('Could not parse time string "%s" for the following log record:' % self.time)
            logger.warn(self.line)
        return dt

    def get_method_name(self):
        """Return cleaned method name from a request string"""
        group, method = self.parse_request()
        if not group and not method:
            return None
        elif not group:
            group = 'nogroup'
        name = group + '_' + method
        valid_name = re.sub(munindaemon_settings.BAD_SYMBOLS,'',name)
        return valid_name

    def match_against_regexes(self, regexes):
        """Determine whether a record is in proper form for processing"""
        for regex in regexes:
            search = regex.search(self.request)
            if search:
                return search
        return None

    def parse_request(self):
        match = self.match_against_regexes(munindaemon_settings.VALID_REQUESTS)
        if match:
            try:
                group = match.group('group')
            except IndexError:
                group = None
            try:
                method = match.group('method')
            except IndexError:
                method = None
            return group, method
        else:
            match = self.match_against_regexes(munindaemon_settings.REQUESTS_TO_SKIP)
            if not match:
                logger.info('Request not parsed: %s' %self.request)
            return None, None


class CalledMethod():

    def __init__(self,name):
        self.name = name
        self.calls = list()

    @property
    def num_calls(self):
        return len(self.calls) if self.calls else 0

    def percentile(self, percent):
        """Compute percentile of values in an array

        @param float percent: percent from 0.0 to 1.0
        @return int: percent or 0 if no values are found
        """
        if not len(self.calls):
            return 0

        k = (len(self.calls)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            result = self.calls[int(k)]
        else:
            d0 = self.calls[int(f)] * (c-k)
            d1 = self.calls[int(c)] * (k-f)
            result = int(round(d0+d1))

        return result

    @property
    def stalled(self):
        """
        Return number of stalled calls
        """
        return len([i for i in self.calls if i > munindaemon_settings.STALLED_CALL_THRESHOLD])

    @property
    def min(self):
        return self.calls[0] if self.calls else 0

    @property
    def max(self):
        return self.calls[-1] if self.calls else 0

    @property
    def avg(self):
        return sum(self.calls)/len(self.calls) if self.calls else 0


class FormatterWithLongerTraceback(logging.Formatter):
    def formatException(self, ei):
        sio = cStringIO.StringIO()
        traceback.print_exception(ei[0], ei[1], ei[2], munindaemon_settings.TRACEBACK_LENGTH, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == "\n":
            s = s[:-1]
        return s

daemon = MuninDaemon()
logger = logging.getLogger(__name__)
logger.setLevel(munindaemon_settings.LOGGING_LEVEL)
formatter = FormatterWithLongerTraceback("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = RotatingFileHandler(os.path.join(munindaemon_settings.DAEMON_LOG_DIR, 'munindaemon.log'),
    maxBytes=munindaemon_settings.MAX_LOG_FILE_SIZE, backupCount=munindaemon_settings.MAX_LOG_FILES)
handler.setFormatter(formatter)
logger.addHandler(handler)

daemon_runner = runner.DaemonRunner(daemon)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve=[handler.stream]
daemon_runner.do_action()
