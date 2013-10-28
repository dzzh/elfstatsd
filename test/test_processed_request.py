import re
from elfstatsd import settings, log_record
import pytest


@pytest.fixture(scope='function')
def processed_request_setup(monkeypatch):
    """Monkeypatch settings setup for processed_request module."""
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
    monkeypatch.setattr(settings, 'PATTERNS_TO_EXTRACT',
                        [
                            {'name': 'uid',
                             'patterns': [
                                 re.compile(r'/data/male_user/(?P<pattern>[\w.]+)'),
                                 re.compile(r'/data/female_user/(?P<pattern>[\w.]+)'),
                             ]},
                            {'patterns': [
                                re.compile(r'/data/chewbakka/(?P<pattern>[\w.]+)'),
                                re.compile(r'/data/r2d2/(?P<pattern>[\w.]+)'),
                            ]},
                            {'name': 'no_patterns'}
                        ])
    monkeypatch.setattr(settings, 'FORBIDDEN_SYMBOLS', re.compile(r'[.-]'))
    return monkeypatch


@pytest.mark.usefixtures('processed_request_setup')
class TestProcessedRequest():
    def test_get_method_name_valid(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/valid/request'
        request = record.get_processed_request()

        assert request.get_method_id() == 'valid_request'
        assert request.status == 'parsed'

    def test_get_method_name_skipped(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/skipped/request'
        request = record.get_processed_request()

        assert request.get_method_id() == ''
        assert request.status == 'skipped'

    def test_get_method_name_nogroup(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/short'
        request = record.get_processed_request()

        assert request.get_method_id() == 'nogroup_short'
        assert request.status == 'parsed'

    def test_get_method_name_forbidden_symbols(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/xml.test.zip'
        request = record.get_processed_request()

        assert request.get_method_id() == 'nogroup_xmltestzip'
        assert request.status == 'parsed'

    def test_get_method_no_method_match(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data'
        request = record.get_processed_request()

        assert request.get_method_id() == ''
        assert request.status == 'error'

    def test_get_method_never_matches(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/subtle/joe'
        request = record.get_processed_request()

        assert request.get_method_id() == ''
        assert request.status == 'error'

    def test_get_method_aggregate(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/aggregate/me'
        request = record.get_processed_request()

        assert request.get_method_id() == 'newgroup_newmethod'
        assert request.status == 'parsed'

    def test_get_method_extract_patterns_found_first(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/male_user/1'
        request = record.get_processed_request()

        assert len(request.patterns) == 1
        assert request.patterns['uid'] == '1'

    def test_get_method_extract_patterns_found_not_first(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/female_user/194'
        request = record.get_processed_request()

        assert len(request.patterns) == 1
        assert request.patterns['uid'] == '194'

    def test_get_method_extract_patterns_not_found(self, monkeypatch):
        processed_request_setup(monkeypatch)

        record = log_record.LogRecord()
        record.raw_request = '/data/no_male_user/84'
        request = record.get_processed_request()

        assert len(request.patterns) == 0
