import datetime
import pytest
from elfstatsd import log_record


@pytest.fixture(scope='function')
def log_record_setup(monkeypatch):
    """Monkeypatch settings setup for log_record module."""
    monkeypatch.setattr(log_record, 'APACHELOG_DATETIME_FORMAT', '%Y%m%d%H%M%S')
    return monkeypatch


@pytest.mark.usefixtures('log_record_setup')
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

    def test_is_before_time_true(self, monkeypatch):
        log_record_setup(monkeypatch)
        record = log_record.LogRecord()
        record.time = ('20130808105959', '+0200')
        time = datetime.datetime.strptime('20130808120000', log_record.APACHELOG_DATETIME_FORMAT)
        assert record.is_before_time(time)

    def test_is_before_time_false(self, monkeypatch):
        log_record_setup(monkeypatch)
        record = log_record.LogRecord()
        record.time = ('20130808105959', '+0200')
        time = datetime.datetime.strptime('20130808100000', log_record.APACHELOG_DATETIME_FORMAT)
        assert not record.is_before_time(time)
