import ConfigParser
import re
from elfstatsd.log_record import LogRecord
from elfstatsd import settings
import pytest
from elfstatsd.storage.storage import MetadataStorage, RecordsStorage, ResponseCodesStorage, PatternsMatchesStorage
from elfstatsd.storage.called_method_storage import CalledMethodStorage

#storage key, which is the highest-level key used for differentiating data related to the different access log files
SK = 'apache_log'


@pytest.fixture(scope='function')
def response_codes_storage_setup(monkeypatch):
    """Monkeypatch settings setup for testing ResponseCodesStorage class."""
    monkeypatch.setattr(settings, 'RESPONSE_CODES', [200, 404, 500])
    return monkeypatch

@pytest.fixture(scope='function')
def called_method_storage_setup(monkeypatch):
    """Monkeypatch settings setup for testing ResponseCodesStorage class."""
    monkeypatch.setattr(settings, 'RESPONSE_CODES', [200, 404, 500])
    monkeypatch.setattr(settings, 'LATENCY_PERCENTILES', [50, 90, 99])
    monkeypatch.setattr(settings, 'VALID_REQUESTS',
                        [
                            re.compile(r'^/data/(?P<group>[\w.]+)/(?P<method>[\w.]+)[/?%&]?'),
                        ])
    return monkeypatch


class TestMetadataStorage():

    def test_storage_metadata_get_unset(self):
        storage = MetadataStorage()
        with pytest.raises(KeyError) as exc_info:
            storage.get(SK, 'record_key')

        assert exc_info.value.message.find('record_key') > -1

    def test_storage_metadata_set_empty(self):
        storage = MetadataStorage()
        storage.set(SK, 'record_key', 'value')
        assert storage.get(SK, 'record_key') == 'value'

    def test_storage_metadata_set_twice(self):
        storage = MetadataStorage()
        storage.set(SK, 'record_key', 'value1')
        storage.set(SK, 'record_key', 'value2')
        assert storage.get(SK, 'record_key') == 'value2'

    def test_storage_metadata_reset(self):
        storage = MetadataStorage()
        storage.set(SK, 'record_key1', 'value1')
        storage.set(SK, 'record_key2', 'value2')
        storage.reset(SK)
        assert len(storage._storage[SK].keys()) == 0

    def test_storage_metadata_dump(self):
        storage = MetadataStorage()
        dump = ConfigParser.RawConfigParser()
        storage.set(SK, 'record_key1', 'value1')
        storage.set(SK, 'record_key2', 'value2')
        storage.dump(SK, dump)
        assert len(dump.sections()) == 1
        assert dump.has_section(storage.name)
        assert len(dump.options(storage.name)) == 2
        assert dump.has_option(storage.name, 'record_key1')
        assert dump.has_option(storage.name, 'record_key2')

    def test_storage_metadata_update_time(self):
        time1 = '2013-10-09 12:00:00'
        time2 = '2013-10-09 12:00:01'
        storage = MetadataStorage()
        storage.update_time(SK, time1)
        storage.update_time(SK, time2)
        assert storage.get(SK, 'first_record') == time1
        assert storage.get(SK, 'last_record') == time2


class TestRecordsStorage():

    def test_storage_records_reset(self):
        storage = RecordsStorage()
        assert len(storage._storage[SK].keys()) == 0
        storage.reset(SK)
        assert len(storage._storage[SK].keys()) == len(storage.record_statuses)

    def test_storage_records_inc_counter(self):
        storage = RecordsStorage()
        storage.inc_counter(SK, 'record_key')
        storage.inc_counter(SK, 'record_key')
        storage.inc_counter(SK, 'record_key')
        storage.inc_counter(SK, 'record_key2')
        assert storage.get(SK, 'record_key') == 3
        assert storage.get(SK, 'record_key2') == 1

    def test_storage_records_dump(self):
        storage = RecordsStorage()
        dump = ConfigParser.RawConfigParser()
        storage.set(SK, 'parsed', 50)
        storage.set(SK, 'skipped', 50)
        storage.dump(SK, dump)
        assert len(dump.sections()) == 1
        assert dump.has_section(storage.name)
        assert len(dump.options(storage.name)) == 2
        assert dump.has_option(storage.name, 'parsed')
        assert dump.has_option(storage.name, 'skipped')


@pytest.mark.usefixtures('response_codes_storage_setup')
class TestResponseCodesStorage():

    def test_storage_response_codes_reset(self, monkeypatch):
        response_codes_storage_setup(monkeypatch)
        storage = ResponseCodesStorage()
        assert len(storage._storage[SK].keys()) == 0
        storage.reset(SK)
        assert len(storage._storage[SK].keys()) == len(storage.permanent_codes)

    def test_storage_response_codes_dump(self, monkeypatch):
        response_codes_storage_setup(monkeypatch)
        storage = ResponseCodesStorage()
        dump = ConfigParser.RawConfigParser()
        section = 'response_codes'
        storage.reset(SK)
        storage.set(SK, '200', 10)
        storage.inc_counter(SK, '200')
        storage.inc_counter(SK, '200')
        storage.inc_counter(SK, '502')
        storage.dump(SK, dump)
        assert len(dump.sections()) == 1
        assert dump.has_section(section)
        assert len(dump.options(section)) == 4
        assert dump.has_option(section, 'rc200')
        assert dump.has_option(section, 'rc404')
        assert dump.has_option(section, 'rc502')
        assert dump.get(section, 'rc200') == 12
        assert dump.get(section, 'rc502') == 1


class TestPatternsMatchesStorage():

    def test_storage_patterns_set(self):
        storage = PatternsMatchesStorage()
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'yyy')
        storage.set(SK, 'pattern', 'yyy')
        assert len(storage.get(SK, 'pattern').keys()) == 2
        assert storage.get(SK, 'pattern')['xxx'] == 3
        assert storage.get(SK, 'pattern')['yyy'] == 2

    def test_storage_patterns_dump(self):
        storage = PatternsMatchesStorage()
        dump = ConfigParser.RawConfigParser()
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'yyy')
        storage.set(SK, 'pattern', 'yyy')
        storage.dump(SK, dump)
        assert len(dump.sections()) == 1
        assert dump.has_section(storage.name)
        assert dump.get(storage.name, 'pattern.total') == 5
        assert dump.get(storage.name, 'pattern.distinct') == 2

    def test_storage_patterns_reset(self):
        storage = PatternsMatchesStorage()
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'xxx')
        storage.set(SK, 'pattern', 'yyy')
        storage.set(SK, 'pattern', 'yyy')
        assert len(storage.get(SK, 'pattern').keys()) == 2
        storage.reset(SK)
        assert len(storage.get(SK, 'pattern').keys()) == 0


@pytest.mark.usefixtures('called_method_storage_setup')
class TestCalledMethodStorage():

    def test_storage_called_method_set(self, monkeypatch):
        called_method_storage_setup(monkeypatch)
        storage = CalledMethodStorage()
        record = LogRecord()
        record.response_code = 404
        record.latency = 100
        storage.set(SK, 'some_call', record)
        record.response_code = 200
        record.latency = 200
        storage.set(SK, 'some_call', record)
        method = storage.get(SK, 'some_call')

        assert len(method.calls) == 2
        assert method.min == 100
        assert method.max == 200
        assert method.response_codes.get(SK, 404) == 1
        assert method.response_codes.get(SK, 200) == 1

    def test_storage_called_method_reset(self, monkeypatch):
        called_method_storage_setup(monkeypatch)
        storage = CalledMethodStorage()
        record = LogRecord()
        record.response_code = 404
        record.latency = 100
        storage.set(SK, 'some_call', record)
        record.response_code = 200
        record.latency = 200
        storage.set(SK, 'some_call', record)
        storage.reset(SK)

        assert len(storage._storage[SK]) == 1
        assert 'some_call' in storage._storage[SK]
        assert len(storage._storage[SK]['some_call'].response_codes._storage[SK].values()) == 3

        storage.reset('some_SK')
        assert 'some_SK' in storage._storage

    def test_storage_called_method_dump(self, monkeypatch):
        called_method_storage_setup(monkeypatch)
        storage = CalledMethodStorage()
        storage.reset(SK)
        record = LogRecord()
        record.raw_request = '/data/some/call/'
        record.response_code = 401
        record.latency = 100
        storage.set(SK, 'some_call', record)
        record.response_code = 201
        record.latency = 200
        storage.set(SK, 'some_call', record)
        method = storage.get(SK, 'some_call')
        method.name = 'some_stuff'

        dump = ConfigParser.RawConfigParser()
        storage.dump(SK, dump)

        section = 'method_some_stuff'

        assert len(dump.sections()) == 1
        assert dump.has_section(section)
        assert dump.get(section, 'calls') == 2
        assert dump.get(section, 'shortest') == 100
        assert dump.get(section, 'average') == 150
        assert dump.get(section, 'longest') == 200
        assert dump.has_option(section, 'p50')
        assert dump.has_option(section, 'p90')
        assert dump.has_option(section, 'p99')
        assert dump.has_option(section, 'rc200')
        assert dump.has_option(section, 'rc404')
        assert dump.has_option(section, 'rc500')