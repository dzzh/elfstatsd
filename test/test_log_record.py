import datetime
import pytest
import re
from elfstatsd import settings, log_record

@pytest.fixture(scope='function')
def log_record_setup(monkeypatch):
    """
    Monkeypatch settings setup for log_record module.
    """
    monkeypatch.setattr(log_record, 'APACHELOG_DATETIME_FORMAT', '%Y%m%d%H%M%S')
    monkeypatch.setattr(settings, 'VALID_REQUESTS',
        [
        re.compile(r'^/data/(?P<group>[\w.]+)/(?P<method>[\w.]+)[/?%&]?'),
        re.compile(r'^/data/(?P<method>[\w.]+)[/?%&]?'),
        re.compile(r'^/data'),
        ])
    monkeypatch.setattr(settings, 'REQUESTS_TO_SKIP',
        [
        re.compile(r'^/$'),
        re.compile(r'^/skipped/request'),
        ])
    monkeypatch.setattr(settings, 'REQUESTS_AGGREGATION',
        [
        ('newgroup', 'newmethod', re.compile(r'^/data/aggregate/me$'))
        ])
    monkeypatch.setattr(settings,'FORBIDDEN_SYMBOLS', re.compile(r'[.-]'))
    return monkeypatch

@pytest.mark.usefixtures("log_record_setup")
class TestLogRecord():

    def test_get_time_correct(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.time = ('20130808105959', '+0200')

        assert record.get_time() == datetime.datetime.strptime('20130808105959', log_record.APACHELOG_DATETIME_FORMAT)

    def test_get_time_wrong(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.time = 'xxx', 'yyy'

        assert record.get_time() is None

    def test_get_method_name_valid(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/data/valid/request'

        assert record.get_method_name() == 'valid_request'

    def test_get_method_name_skipped(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/skipped/request'

        assert record.get_method_name() is None

    def test_get_method_name_nogroup(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/data/short'

        assert record.get_method_name() == 'nogroup_short'

    def test_get_method_name_forbidden_symbols(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/data/xml.test.zip'

        assert record.get_method_name() == 'nogroup_xmltestzip'

    def test_get_method_no_method_match(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/data'

        assert record.get_method_name() is None

    def test_get_method_never_matches(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/subtle/joe'

        assert record.get_method_name() is None

    def test_get_method_aggregate(self, monkeypatch):
        log_record_setup(monkeypatch)

        record = log_record.LogRecord()
        record.request = '/data/aggregate/me'

        assert record.get_method_name() == 'newgroup_newmethod'
