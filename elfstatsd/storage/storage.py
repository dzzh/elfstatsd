from abc import ABCMeta, abstractmethod
from collections import defaultdict
from counter_backport import Counter
from elfstatsd import utils, settings


class Storage():
    """Abstract class used as a parent for statistics storages"""

    __metaclass__ = ABCMeta

    def __init__(self, name):
        self.name = name

        # Basic storage structure - dict of dicts, with the first-level dict responsible for
        # storing data related to different access log files, and the second-level dict
        # storing key-value pairs we're interested in.
        self._storage = defaultdict(dict)

    def get(self, storage_key, record_key):
        """
        Get value of a given counter_key associated with given storage_key. Create storage_key if missing.
        @param str storage_key: access log-related key to define statistics storage
        @param str record_key: record-related key
        @return value
        @raise KeyError if record_key is not found by storage_key
        """
        return self._storage[storage_key][record_key]

    def set(self, storage_key, record_key, value):
        """
        Set a value of specified key in storage determined by storage_key. Create storage_key if missing.
        @param str storage_key: access log-related key to define statistics storage
        @param str record_key: record-related key
        @param value: value to set
        """
        self._storage[storage_key][record_key] = value

    @abstractmethod
    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round
        @param str storage_key: access log-related key to define statistics storage
        """
        self._storage[storage_key] = {}

    @abstractmethod
    def dump(self, storage_key, parser):
        """
        Dump storage data defined by the storage_key to RawConfigParser instance
        @param str storage_key: access log-related key to define statistics storage
        @param RawConfigParser parser: instance of ConfigParser to store the data
        """
        section = self.name
        if not parser.has_section(section):
            parser.add_section(section)

        for record_key in sorted(self._storage[storage_key].keys()):
            value = self.get(storage_key, record_key)
            parser.set(section, str(record_key), utils.format_value_for_munin(value))


class CounterStorage(Storage):
    """Abstract class representing a storage for incrementing counters"""

    def __init__(self, name):
        super(CounterStorage, self).__init__(name)

        # Storage structure - dict of Counters, with the first-level dict responsible for
        # storing data related to different access log files, and the second-level dict
        # being a Counter storing key-value pairs with values being incrementing integers
        self._storage = defaultdict(Counter)

    def inc_counter(self, storage_key, record_key):
        """
        Increment the counter for the given key in storage determined by storage key. Create storage_key if missing.
        @param str storage_key: access log-related key to define statistics storage
        @param str record_key: record-related key. If the value for this key is missing, it will be set to 1.
        """
        self._storage[storage_key][record_key] += 1

    @abstractmethod
    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round. Save all the keys, but reset the values.
        @param str storage_key: access log-related key to define statistics storage
        """
        for record_key in self._storage[storage_key].keys():
            self._storage[storage_key][record_key] = 0


class MetadataStorage(Storage):
    """Simple storage for metadata values, like daemon's version and starting time"""

    def __init__(self):
        super(MetadataStorage, self).__init__('metadata')

    def reset(self, storage_key):
        super(MetadataStorage, self).reset(storage_key)

    def dump(self, storage_key, parser):
        super(MetadataStorage, self).dump(storage_key, parser)

    def update_time(self, storage_key, time):
        """
        Update time-related metrics (first and last record) with given timestamp
        @param str storage_key: access log-related key to define statistics storage
        @param str time: string representation of record time
        """
        if not 'first_record' in self._storage[storage_key] or \
                not self._storage[storage_key]['first_record']:
            self._storage[storage_key]['first_record'] = time
        self._storage[storage_key]['last_record'] = time


class RecordsStorage(CounterStorage):
    """Storage for records counters, like the number of parsed and skipped records"""

    def __init__(self):
        super(RecordsStorage, self).__init__('records')
        self.record_statuses = ['parsed', 'skipped', 'error', 'total']

    def reset(self, storage_key):
        super(RecordsStorage, self).reset(storage_key)

        for status in self.record_statuses:
            self._storage[storage_key][status] = 0

    def dump(self, storage_key, parser):
        super(RecordsStorage, self).dump(storage_key, parser)


class ResponseCodesStorage(CounterStorage):
    """Storage for response codes distribution"""

    def __init__(self):
        super(ResponseCodesStorage, self).__init__('response_codes')
        self.permanent_codes = getattr(settings, 'RESPONSE_CODES', [])

    def reset(self, storage_key):
        super(ResponseCodesStorage, self).reset(storage_key)

        for code in self.permanent_codes:
            self.set(storage_key, code, 0)

    def dump(self, storage_key, parser):
        self.flexible_dump(storage_key, parser, self.name)

    def flexible_dump(self, storage_key, parser, section, prefix='rc'):
        """
        Dump storage data defined by the storage_key to RawConfigParser instance
        @param str storage_key: access log-related key to define statistics storage
        @param RawConfigParser parser: instance of RawConfigParser to store the data
        @param str section: name of section to write data
        @param str prefix: prefix to be added to response code
        """
        if not parser.has_section(section):
            parser.add_section(section)
        for code in sorted(self._storage[storage_key].keys()):
            parser.set(section, prefix+str(code), utils.format_value_for_munin(self._storage[storage_key][code]))


class PatternsMatchesStorage(Storage):
    """Storage for additional patterns found in the requests"""

    def __init__(self):
        super(PatternsMatchesStorage, self).__init__('patterns')

        # Storage structure - dict of dicts of Counters, with the first-level dict responsible for
        # storing data related to different access log files, the second-level dict
        # responsible for storing data per pattern found in settings.PATTERNS_TO_EXTRACT and
        # the third-level Counter storing key-value pairs with values being incrementing integers
        # for the specific occurrences of the values extracted using the pattern.
        self._storage = defaultdict(lambda: defaultdict(Counter))

    def set(self, storage_key, record_key, value):
        """
        Increment match counter found in specific pattern defined by record_key
        from specific access log defined by storage_key. If storage_key or record_key are not found, they
        are created automatically. If value is not found, it is set to 1.
        @param str storage_key: access log-related key to define statistics storage
        @param record_key: identifier of a matched pattern
        @param str value: value of a matched pattern
        """
        self._storage[storage_key][record_key][value] += 1

    def reset(self, storage_key):
        self._storage[storage_key] = defaultdict(Counter)

    def dump(self, storage_key, parser):
        """
        For each pattern existing in given access log file defined by storage_key, dump two values:
         `pattern.total` with total number of pattern matches, and `pattern.distinct` with total number
          of different matches.
        @param str storage_key: access log-related key to define statistics storage
        @param RawConfigParser parser: instance of RawConfigParser to store the data
        """
        section = self.name
        if not parser.has_section(section):
            parser.add_section(section)
        for record_key in sorted(self._storage[storage_key].keys()):
            total = sum([value for value in self.get(storage_key, record_key).values()])
            parser.set(section, str(record_key)+'.total', utils.format_value_for_munin(total))
            distinct = len(self._storage[storage_key][record_key])
            parser.set(section, str(record_key)+'.distinct', utils.format_value_for_munin(distinct))

        #adding missing patterns by name
        patterns = getattr(settings, 'PATTERNS_TO_EXTRACT', [])
        for pattern in patterns:
            if 'name' in pattern and not parser.has_option(section, pattern['name']+'.total'):
                parser.set(section, pattern['name'] + '.total', utils.format_value_for_munin(0))
                parser.set(section, pattern['name'] + '.distinct', utils.format_value_for_munin(0))
