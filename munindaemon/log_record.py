import datetime
import logging
import re
import settings

LOG_DATETIME_FORMAT = '%Y%m%d%H%M%S'

logger = logging.getLogger("munindaemon")

class LogRecord():

    def __init__(self):
        #stored in raw string, converted in access method
        self.time = ''
        self.request = ''
        self.response_code = 0
        self.latency = 0
        self.line = ''

    @property
    def get_time(self):
        dt = None
        try:
            dt = datetime.datetime.strptime(self.time[0], LOG_DATETIME_FORMAT)
        except ValueError:
            logger.warn('Could not parse time string "%s" for the following log record:' % self.time)
            logger.warn(self.line)
        return dt

    @property
    def get_method_name(self):
        """Return cleaned method name from a request string"""
        group, method = self.parse_request()
        if not group and not method:
            return None
        elif not group:
            group = 'nogroup'
        name = group + '_' + method
        valid_name = re.sub(settings.BAD_SYMBOLS,'',name)
        return valid_name

    def _match_against_regexes(self, regexes):
        """Determine whether a record is in proper form for processing"""
        for regex in regexes:
            search = regex.search(self.request)
            if search:
                return search
        return None

    def parse_request(self):
        match = self._match_against_regexes(settings.VALID_REQUESTS)
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
            match = self._match_against_regexes(settings.REQUESTS_TO_SKIP)
            if not match:
                logger.info('Request not parsed: %s' %self.request)
            return None, None