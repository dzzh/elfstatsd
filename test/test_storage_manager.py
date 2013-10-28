import ConfigParser
from elfstatsd.storage.storage_manager import StorageManager
from elfstatsd.storage.storage import PatternsMatchesStorage
from elfstatsd.storage.called_method_storage import CalledMethodStorage

SK = 'apache_log'


class TestStorageManager():

    def test_storage_manager_get(self):
        sm = StorageManager()
        assert len(sm.storages) == 5
        assert sm.get('metadata').name == 'metadata'
        assert type(sm.get('patterns')) == PatternsMatchesStorage

    def test_storage_manager_reset(self):
        sm = StorageManager()
        sm.get('metadata').set(SK, 'daemon_version', '1.0')
        sm.get('records').set(SK, 'parsed', 100)
        sm.reset(SK)
        assert len(sm.storages) == 5
        assert len(sm.get('metadata')._storage[SK].keys()) == 0
        assert type(sm.get('methods')) == CalledMethodStorage

    def test_storage_manager_dump(self, tmpdir):
        path = str(tmpdir.mkdir('log').join('apache.log').realpath())

        sm = StorageManager()
        sm.get('metadata').set(path, 'daemon_version', '1.0')

        sm.dump(path)

        parser = ConfigParser.RawConfigParser()
        parser.read(path)

        assert len(parser.sections()) == 4
        assert len(parser.options('metadata')) == 1
        assert parser.get('metadata', 'daemon_version') == '1.0'
