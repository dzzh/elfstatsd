import logging
import apachelog
import log_record

SECOND_EXPONENT = 0
MILLISECOND_EXPONENT = 3
MICROSECOND_EXPONENT = 6
NANOSECOND_EXPONENT = 9

SEEK_BACKWARD_PERCENTS = 1

BYTES_IN_MB = 1024 * 1024

END_OF_FILE = 'EOF'

logger = logging.getLogger("elfstatsd")

def parse_latency(latency, precision = MILLISECOND_EXPONENT):
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
        record.line = line
        record.time = apachelog.parse_date(data['%t'])
        request = data['%r']
        if len(request) > 1:
            record.request = request.split(' ')[1]
        else:
            logger.warn('Parser was not able to parse the request in the following line: ')
            logger.warn(line)
            return None
        record.response_code = int(data['%>s'])
        latency = data['%D']
        if latency.find('.') == -1 and latency_in_millis:
            latency += '000'
        record.latency = parse_latency(latency)
    except apachelog.ApacheLogParserError:
        logger.warn('Parser has caught an error while processing the following record: ')
        logger.warn(line)
        return None
    return record

def format_value_for_munin(value, zero_allowed=False):
    return value if value or (zero_allowed and value == 0) else 'U'

def format_filename(name, dt):
    """Generate file name from a template containing formatted string and time value"""
    return dt.strftime(name)