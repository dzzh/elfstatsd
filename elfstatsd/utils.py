import logging
import apachelog
import datetime
import urlparse
import log_record

SECOND_EXPONENT = 0
MILLISECOND_EXPONENT = 3
MICROSECOND_EXPONENT = 6
NANOSECOND_EXPONENT = 9

SEEK_BACKWARD_PERCENTS = 1

BYTES_IN_MB = 1024 * 1024

END_OF_FILE = 'EOF'

logger = logging.getLogger('elfstatsd')


def parse_latency(latency, precision=MILLISECOND_EXPONENT):
    """
    Parse string value of latency to integer with predefined precision of returned result.
    Convert from int value in microseconds and from float value in nanoseconds
    (e.g. '123456' -> 123, '4135' -> 4 and '2.123456789' -> 2123).
    For other formats, correctness of the results is not guaranteed.
    @param str latency: latency representation from a log file
    @param int precision: precision of returned result
    @return int parsed latency
    """
    if not '.' in latency:
        #integer in microseconds
        return int(round(int(latency) / float(10 ** (MICROSECOND_EXPONENT - precision))))
    else:
        #float in nanoseconds
        return int(round(float(latency), precision) * 10 ** precision)


def parse_line(line, log_parser, latency_in_millis=False):
    """
    Convert a line from a log into LogRecord.

    Contains code that parses log records. This code may need to be changed if Apache log format changes.
    @param unicode line: log line to parse
    @param ApacheLogParser log_parser: instance of ApacheLogParser containing log format description
    @param boolean latency_in_millis: if True, latency is considered to be in milliseconds, otherwise in microseconds
    """
    record = log_record.LogRecord()

    try:
        data = log_parser.parse(line)
    except apachelog.ApacheLogParserError:
        logger.warn('Parser has caught an error while processing the following record: ')
        logger.warn(line)
        return None

    try:
        record.time = apachelog.parse_date(data['%t'])
    except (IndexError, KeyError):
        logger.warn('Parser was not able to parse date %s: ' % data['%t'])
        logger.warn('Record with error: %s' % line)
        return None

    record.line = line

    request = data['%r']
    try:
        record.raw_request = request.split(' ')[1]
    except IndexError:
        logger.warn('Parser was not able to parse the request %s: ' % request)
        logger.warn('Record with error: %s' % line)
        return None

    try:
        record.response_code = int(data['%>s'])
    except ValueError:
        logger.warn('Parser was not able to parse response code %s: ' % data['%>s'])
        logger.warn('Record with error: %s' % line)
        return None

    latency = data['%D']
    if latency.find('.') == -1 and latency_in_millis:
        latency += '000'
    record.latency = parse_latency(latency)

    return record


def format_value_for_munin(value, zero_allowed=False):
    """
    Convert value into a format that will be understood by Munin
    @param value: value to write
    @param boolean zero_allowed: if True, 0 will be reported as 0, otherwise as unknown ('U')
    @return value
    """
    return value if value or (zero_allowed and value == 0) else 'U'


def format_filename(name, dt):
    """
    Generate file name from a template containing formatted string and time value
    Template may contain datetime specifiers and optionally additional key=value parameters after '?' symbol
    and separated by '&' symbol (as in URLs).

    Supported parameters:
    * ts (int) - time shift in seconds, positive or negative. Default 0
    * ts-name-only (boolean) - if true, only use time shift to correctly resolve the file name,
    otherwise also for records. Default false.

    Example: '/var/log/httpd/apache.log-%Y-%m-%d-%H?ts=-3600&ts-name-only=true' -
    shift time by 3600 seconds (or 1 hour) back and use this shift only to resolve the name.

    @param str name: filename template
    @param datetime dt: datetime to use for generation
    @return (str, {}) generated filename with all specifiers resolved and a dict of additional parameters
    """
    if not '?' in name:
        return dt.strftime(name), _default_filename_params()

    filename, params = name.split('?')[0], dict(urlparse.parse_qsl(name.split('?')[1]))

    try:
        if 'ts' in params:
            td = datetime.timedelta(seconds=int(params['ts']))
            filename = (dt + td).strftime(filename)
            params['ts'] = td
        else:
            filename = dt.strftime(filename)
            params['ts'] = datetime.timedelta()

        if 'ts-name-only' in params and params['ts-name-only'].lower() == 'true':

            # Here we reset ts as it is not needed anymore.
            # This allows to avoid checking for ts-name-only at the clients
            # However, if the ts behavior will change, this may have to be re-thought.
            params['ts'] = datetime.timedelta()

            params['ts-name-only'] = True
        else:
            params['ts-name-only'] = False

        return filename, params

    except ValueError:
        logger.warn('Daemon was not able to recognize parameters in string %s' % name)
        return dt.strftime(filename), _default_filename_params()


def _default_filename_params():
    params = dict()
    params['ts'] = datetime.timedelta()
    params['ts-name-only'] = False
    return params