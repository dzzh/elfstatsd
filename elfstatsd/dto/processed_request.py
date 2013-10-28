import re
from elfstatsd import settings


class ProcessedRequest():
    """Stores information about a single request appearing in a log record"""

    group = None
    method = None
    status = 'error'
    patterns = []

    def __init__(self, raw_string):
        self.raw_string = raw_string

    def get_method_id(self):
        """
        Form method_identifier from a raw request string.
        @return str or None name
        """
        if self.status != 'parsed':
            return ''

        group = self.group if self.group else 'nogroup'
        name = group + '_' + self.method
        valid_name = re.sub(getattr(settings, 'FORBIDDEN_SYMBOLS', ''), '', name)
        return valid_name