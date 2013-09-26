import datetime
import logging
import re
import settings

APACHELOG_DATETIME_FORMAT = '%Y%m%d%H%M%S'

logger = logging.getLogger("elfstatsd")

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
            dt = datetime.datetime.strptime(self.time[0], APACHELOG_DATETIME_FORMAT)
        except ValueError:
            logger.warn('Could not parse time string "%s" for the following log record:' % str(self.time))
            logger.warn(self.line)
        return dt

    def get_method_name(self):
        """Return cleaned method name from a request string"""
        group, method = self._parse_request()
        if not group and not method:
            return None
        elif not group:
            group = 'nogroup'
        name = group + '_' + method
        print name
        valid_name = re.sub(settings.FORBIDDEN_SYMBOLS, '', name)
        return valid_name

    def _match_against_regexes(self, regexes):
        """Determine whether a record is in proper form for processing"""
        for regex in regexes:
            search = regex.search(self.request)
            if search:
                return search
        return None

    def _aggregate_request(self):
        """Try to match request against aggregation rules in settings
           and return its group and method if match is found
        """
        aggregation_rules = settings.REQUESTS_AGGREGATION
        for group, method, regex in aggregation_rules:
            if self._match_against_regexes([regex]):
                return group, method
        return None, None

    def _parse_request(self):
        """
        Return group and method of a request contained in the class.
        Values are derived from URI by matching against VALID_REQUESTS
        and maybe substituted by REQUESTS_AGGREGATION setting.
        If a request is not valid and does not match by REQUESTS_TO_SKIP,
        it is reported in logs as invalid.
        """
        match = self._match_against_regexes(settings.VALID_REQUESTS)
        if match:
            group, method = self._aggregate_request()
            if not group and not method:
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