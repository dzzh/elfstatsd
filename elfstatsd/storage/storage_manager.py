import ConfigParser
from called_method_storage import CalledMethodStorage
from storage import MetadataStorage, RecordsStorage, ResponseCodesStorage


class StorageManager():

    def __init__(self):
        self.storages = {}
        s = MetadataStorage()
        self.storages[s.name] = s
        s = RecordsStorage()
        self.storages[s.name] = s
        s = ResponseCodesStorage()
        self.storages[s.name] = s
        s = CalledMethodStorage()
        self.storages[s.name] = s

    def get(self, name):
        """
        Return a storage given its name or KeyError if name is not found
        @param str name: name of the storage
        @return Storage storage
        """
        return self.storages[name]

    def reset(self, storage_key):
        """
        Correctly reset all the storages and prepare them for the next round
        @param str storage_key: a key to define statistics storage
        """
        [s.reset(storage_key) for s in self.storages.values()]

    def dump(self, file_path):
        """
        Dump statistics to the file in ConfigParser format
        @param str file_path: path to a file for storing data
        """
        dump = ConfigParser.RawConfigParser()
        [s.dump(file_path, dump) for s in sorted(self.storages.values())]
        with open(file_path, 'wb') as f:
            dump.write(f)