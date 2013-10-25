import bisect
from elfstatsd.called_method import CalledMethod
from elfstatsd import settings, utils
from storage import Storage


class CalledMethodStorage(Storage):
    """Storage for CalledMethod instances keeping tracks of request latencies and more"""

    def __init__(self):
        super(CalledMethodStorage, self).__init__('methods')

    def dump(self, storage_key, parser):
        """
        Add storage data to ConfigParser instance
        @param str storage_key: a key to define statistics storage
        @param ConfigParser parser: instance of ConfigParser to store the data
        """

        raw_percentiles = getattr(settings, 'LATENCY_PERCENTILES', [])
        percentiles = sorted([p for p in raw_percentiles if type(p) == int and 0 <= p <= 100])

        for method in self.storage[storage_key].values():
            section = 'method_' + method.name
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, 'calls', utils.format_value_for_munin(method.num_calls))
            parser.set(section, 'stalled_calls', utils.format_value_for_munin(method.stalled))
            parser.set(section, 'shortest', utils.format_value_for_munin(method.min))
            parser.set(section, 'longest', utils.format_value_for_munin(method.max))
            parser.set(section, 'average', utils.format_value_for_munin(method.avg))

            for p in percentiles:
                parser.set(section, 'p' + str(p), utils.format_value_for_munin(method.percentile(p)))

            method.response_codes.flexible_dump(storage_key, parser, section)

    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round
        @param str storage_key: a key to define statistics storage
        """
        if storage_key in self.storage:
            for method in self.storage[storage_key].values():
                method.calls = []
                method.response_codes.reset(storage_key)
        else:
            self.storage[storage_key] = {}

    def get(self, storage_key, record_key):
        """
        Get a CalledMethod instance from a storage.
        If there is no record, place a new there first.
        @param str storage_key: a key to define statistics storage
        @return CalledMethod method with stats set
        """
        try:
            return self.storage[storage_key][record_key]
        except KeyError:
            method = CalledMethod(record_key)
            self.storage[storage_key][record_key] = method
            return method

    def set(self, storage_key, record_key, record):
        """
        Add latency of a given call and its response code to the method's storage.
        @param str storage_key: a key to define statistics storage
        @param str record_key: call name
        @param LogRecord record: parsed record
        """
        method = self.get(storage_key, record_key)
        bisect.insort(method.calls, record.latency)
        method.response_codes.inc_counter(storage_key, record.response_code)