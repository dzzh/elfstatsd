import bisect
from collections import defaultdict
from elfstatsd.dto.called_method import CalledMethod
from elfstatsd import settings, utils
from storage import Storage


class CalledMethodStorage(Storage):
    """Storage for CalledMethod instances keeping tracks of request latencies and response codes distribution"""

    def __init__(self):
        super(CalledMethodStorage, self).__init__('methods')

        # Storage structure - dict of dicts of CalledMethod instances, with the first-level dict responsible for
        # storing data related to different access log files, the second-level dict
        # responsible for storing data per method found by matching settings.VALID_REQUESTS.
        self._storage = defaultdict(lambda: defaultdict(lambda: CalledMethod('')))

    def set(self, storage_key, record_key, record):
        method = self.get(storage_key, record_key)
        if not method.name and record.get_method_id():
            method.name = record.get_method_id()
            method.response_codes.reset(storage_key)
        bisect.insort(method.calls, record.latency)
        method.response_codes.inc_counter(storage_key, record.response_code)

    def reset(self, storage_key):
        if storage_key in self._storage:
            for method in self._storage[storage_key].values():
                method.calls = []
                method.response_codes.reset(storage_key)
        else:
            self._storage[storage_key] = defaultdict(lambda: CalledMethod(''))

    def dump(self, storage_key, parser):
        raw_percentiles = getattr(settings, 'LATENCY_PERCENTILES', [])
        percentiles = sorted([p for p in raw_percentiles if type(p) == int and 0 <= p <= 100])

        for method in self._storage[storage_key].values():
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