import datetime
import logging
from dto.processed_request import ProcessedRequest
import settings

APACHELOG_DATETIME_FORMAT = '%Y%m%d%H%M%S'

logger = logging.getLogger("elfstatsd")


class LogRecord():

    def __init__(self):
        #stored in raw string, converted in access method
        self.time = ''
        self.raw_request = ''
        self.response_code = 0
        self.latency = 0
        self.line = ''

    def get_time(self):
        """
        Return string representation of record time
        @return str time string
        """
        dt = None
        try:
            dt = datetime.datetime.strptime(self.time[0], APACHELOG_DATETIME_FORMAT)
        except ValueError:
            logger.warn('Could not parse time string "%s" for the following log record:' % str(self.time))
            logger.warn(self.line)
        return dt

    def _match_against_regexes(self, regexes):
        """
        Try to match request against given regexes and return matched object if match is found
        @param [] regexes: list of compiled regexes to validate against
        @return MatchObject or None
        """
        for regex in regexes:
            search = regex.search(self.raw_request)
            if search:
                return search
        return None

    def _aggregate_request(self):
        """
        Try to match request against aggregation rules in settings
        and return its group and method if match is found. Otherwise return (None, None)
        @return (group, method)
        """
        aggregation_rules = getattr(settings, 'REQUESTS_AGGREGATION', [])
        for group, method, regex in aggregation_rules:
            if self._match_against_regexes([regex]):
                return str(group), str(method)
        return None, None

    def _find_patterns(self):
        """
        Match request against patterns in settings.PATTERNS_TO_EXTRACT.
        @return dict with keys being identifiers of matched patterns, values being matched values
        """
        patterns = getattr(settings, 'PATTERNS_TO_EXTRACT', [])
        matches = {}
        for pattern in patterns:
            if not 'name' in pattern or not 'patterns' in pattern:
                continue
            match = self._match_against_regexes(pattern['patterns'])
            if match:
                matches[pattern['name']] = match.group('pattern')
        return matches

    def is_before_time(self, time):
        """
        Return true if record's timestamp is before given time, false otherwise
        @param datetime time: time for comparison
        @return true if record's timestamp is before given time, false otherwise
        """
        dt = self.get_time()
        if dt < time:
            return True
        return False

    def get_method_id(self):
        """
        Form method_identifier from a raw request string.
        @return str name
        """
        request = self.get_processed_request()
        return request.get_method_id()

    def get_processed_request(self):
        """
        Process the request contained in the record and return ProcessedRequest instance.
        Group and method name are derived from URI by matching against VALID_REQUESTS
        and are maybe substituted by REQUESTS_AGGREGATION setting.
        If the request is not valid and does not match by REQUESTS_TO_SKIP, it is reported in logs as invalid.
        @return ProcessedRequest
        """
        request = ProcessedRequest(self.raw_request)
        match = self._match_against_regexes(getattr(settings, 'VALID_REQUESTS', []))

        if match:
            request.group, request.method = self._aggregate_request()
            if not request.group and not request.method:
                try:
                    request.group = match.group('group')
                except IndexError:
                    request.group = None
                try:
                    request.method = match.group('method')
                except IndexError:
                    # method should always be presented in valid requests
                    logger.info('Method name not parsed: %s' % self.raw_request)
                    request.status = 'error'
                    return request
            request.status = 'parsed'
            request.patterns = self._find_patterns()
            return request

        else:
            match = self._match_against_regexes(getattr(settings, 'REQUESTS_TO_SKIP', []))
            if not match:
                logger.info('Request not parsed: %s' % self.raw_request)
            else:
                request.status = 'skipped'
            return request