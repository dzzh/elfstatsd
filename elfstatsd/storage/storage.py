from abc import ABCMeta, abstractmethod
from elfstatsd import utils, settings


class Storage():
    """Abstract class used as a parent for statistics storages"""

    __metaclass__ = ABCMeta

    def __init__(self, name):
        self.storage = {}
        self.name = name

    def set(self, storage_key, key, value):
        """
        Set a value of specified key in storage determined by storage_key
        @param str storage_key: a key to define statistics storage
        @param str key: key of a record to set
        @param value: value to set
        """
        if not storage_key in self.storage:
            self.storage[storage_key] = {}
        self.storage[storage_key][key] = value

    def inc_counter(self, storage_key, counter_key):
        """
        Update aggregation counter for the given key in storage determined by storage key
        @param str storage_key: a key to define statistics storage
        @param str counter_key: key for the counter to increase
        """
        if not storage_key in self.storage or not counter_key in self.storage[storage_key]:
            self.set(storage_key, counter_key, 0)
        self.storage[storage_key][counter_key] += 1

    @abstractmethod
    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round
        @param str storage_key: a key to define statistics storage
        """
        self.storage[storage_key] = {}

    @abstractmethod
    def dump(self, storage_key, parser):
        """
        Add storage data to ConfigParser instance
        @param str storage_key: a key to define statistics storage
        @param ConfigParser parser: instance of ConfigParser to store the data
        """
        section = self.name
        if not parser.has_section(section):
            parser.add_section(section)
        for record_key in sorted(self.storage[storage_key].keys()):
            value = self.storage[storage_key][record_key]
            parser.set(section, str(record_key), utils.format_value_for_munin(value))


class MetadataStorage(Storage):
    """Storage for metadata values, like daemon's version and starting time"""

    def __init__(self):
        super(MetadataStorage, self).__init__('metadata')

    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round
        @param str storage_key: a key to define statistics storage
        """
        super(MetadataStorage, self).reset(storage_key)

    def dump(self, storage_key, parser):
        """
        Add storage data to ConfigParser instance
        @param str storage_key: a key to define statistics storage
        @param ConfigParser parser: instance of ConfigParser to store the data
        """
        super(MetadataStorage, self).dump(storage_key, parser)

    def update_time(self, storage_key, time):
        """
        Update time-related metrics with given timestamp
        @param str storage_key: a key to define statistics storage
        @param str time: string representation of record time
        """

        if not 'first_record' in self.storage[storage_key] or \
                not self.storage[storage_key]['first_record']:
            self.storage[storage_key]['first_record'] = time
        self.storage[storage_key]['last_record'] = time


class RecordsStorage(Storage):
    """Storage for records counters, like the number of parsed and skipped records"""

    def __init__(self):
        super(RecordsStorage, self).__init__('records')
        self.record_statuses = ['parsed', 'skipped', 'error', 'total']

    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round
        @param str storage_key: a key to define statistics storage
        """
        super(RecordsStorage, self).reset(storage_key)

        for status in self.record_statuses:
            self.storage[storage_key][status] = 0

    def dump(self, storage_key, parser):
        """
        Add storage data to ConfigParser instance
        @param str storage_key: a key to define statistics storage
        @param ConfigParser parser: instance of ConfigParser to store the data
        """
        super(RecordsStorage, self).dump(storage_key, parser)


class ResponseCodesStorage(Storage):
    """Storage for response codes distribution"""

    def __init__(self):
        super(ResponseCodesStorage, self).__init__('response_codes')
        self.permanent_codes = getattr(settings, 'RESPONSE_CODES', [])

    def reset(self, storage_key):
        """
        Properly reset the storage and prepare it for the next round
        @param str storage_key: a key to define statistics storage
        """
        if storage_key in self.storage:
            for code in self.storage[storage_key]:
                self.storage[storage_key][code] = 0
        else:
            self.storage[storage_key] = {}

    def dump(self, storage_key, parser):
        """
        Add storage data to ConfigParser instance
        @param str storage_key: a key to define statistics storage
        @param ConfigParser parser: instance of ConfigParser to store the data
        """
        self.flexible_dump(storage_key, parser, self.name)

    def flexible_dump(self, storage_key, parser, section, prefix='rc'):
        """
        Add storage data to ConfigParser instance
        @param str storage_key: a key to define statistics storage
        @param ConfigParser parser: instance of ConfigParser to store the data
        @param str section: name of section to write data
        @param str prefix: prefix to be added to response code
        """
        if not parser.has_section(section):
            parser.add_section(section)
        for code in sorted(self.storage[storage_key].keys()):
            parser.set(section, prefix+str(code), utils.format_value_for_munin(self.storage[storage_key][code]))

        #Add response codes from settings with 0 value if they are not found in logs
        #Is needed for Munin not to drop these codes from the charts
        for code in sorted(self.permanent_codes):
            if not code in self.storage[storage_key].keys():
                parser.set(section, prefix+str(code), utils.format_value_for_munin(''))