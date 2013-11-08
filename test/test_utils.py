import datetime
import re
from elfstatsd import log_record, settings
import pytest
import apachelog
from elfstatsd.utils import MILLISECOND_EXPONENT, MICROSECOND_EXPONENT, SECOND_EXPONENT, NANOSECOND_EXPONENT
from elfstatsd.utils import parse_line, format_value_for_munin, format_filename, parse_latency


@pytest.fixture(scope='function')
def utils_setup(monkeypatch):
    """
    Monkeypatch settings setup for utils module.
    """
    monkeypatch.setattr(log_record, 'APACHELOG_DATETIME_FORMAT', '%Y%m%d%H%M%S')
    monkeypatch.setattr(settings, 'ELF_FORMAT',
                        r'%h %l %u %t \"%r\" %>s %B \"%{Referer}i\" \"%{User-Agent}i\" '
                        r'%{JK_LB_FIRST_NAME}n %{JK_LB_LAST_NAME}n %{JK_LB_LAST_STATE}n %I %O %D')
    monkeypatch.setattr(settings, 'VALID_REQUESTS',
                        [
                            re.compile(r'^/data/(?P<group>[\w.]+)/(?P<method>[\w.]+)[/?%&]?'),
                            re.compile(r'^/data/(?P<method>[\w.]+)[/?%&]?'),
                            re.compile(r'^/data'),
                        ])
    return monkeypatch


class TestLatency():
    def test_int_0(self):
        assert parse_latency('0', MILLISECOND_EXPONENT) == 0

    def test_int_12(self):
        assert parse_latency('012', MILLISECOND_EXPONENT) == 0

    def test_int_114(self):
        assert parse_latency('114', MILLISECOND_EXPONENT) == 0

    def test_int_114(self):
        assert parse_latency('114', MICROSECOND_EXPONENT) == 114

    def test_int_4135(self):
        assert parse_latency('4135', MILLISECOND_EXPONENT) == 4

    def test_int_4135_6(self):
        assert parse_latency('4135', MICROSECOND_EXPONENT) == 4135

    def test_int_4466(self):
        assert parse_latency('4466', MILLISECOND_EXPONENT) == 4

    def test_int_99999(self):
        assert parse_latency('99999', MILLISECOND_EXPONENT) == 100

    def test_int_100000(self):
        assert parse_latency('100000', MILLISECOND_EXPONENT) == 100

    def test_int_5104543(self):
        assert parse_latency('5104543', MILLISECOND_EXPONENT) == 5105

    def test_int_5104543_6(self):
        assert parse_latency('5104543', MICROSECOND_EXPONENT) == 5104543

    def test_int_5104543_0(self):
        assert parse_latency('5104543', SECOND_EXPONENT) == 5

    def test_float_0(self):
        assert parse_latency('0.000000000', MILLISECOND_EXPONENT) == 0

    def test_float_01(self):
        assert parse_latency('0.000123456', MILLISECOND_EXPONENT) == 0

    def test_float_02(self):
        assert parse_latency('0.000123456', MICROSECOND_EXPONENT) == 123

    def test_float_1(self):
        assert parse_latency('0.123456789', MILLISECOND_EXPONENT) == 123

    def test_float_2_3(self):
        assert parse_latency('1.123456789', MILLISECOND_EXPONENT) == 1123

    def test_float_2_6(self):
        assert parse_latency('1.123456789', MICROSECOND_EXPONENT) == 1123457

    def test_float_2_9(self):
        assert parse_latency('1.123456789', NANOSECOND_EXPONENT) == 1123456789

    def test_float_2_0(self):
        assert parse_latency('1.123456789', SECOND_EXPONENT) == 1

    def test_float_3(self):
        assert parse_latency('0.54478', MILLISECOND_EXPONENT) == 545


@pytest.mark.usefixtures('utils_setup')
class TestParseLine():
    def test_valid(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "POST /data/csl/contentupdate/xxx HTTP/1.1" 200 8563 '\
               u'"-" "Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)

        assert record.raw_request == '/data/csl/contentupdate/xxx'
        assert record.get_time() == datetime.datetime.strptime('20130808105959', log_record.APACHELOG_DATETIME_FORMAT)
        assert record.response_code == 200
        assert record.latency == 53
        assert record.get_method_id() == 'csl_contentupdate'

    def test_empty(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u''
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)

        assert record is None

    def test_empty_request(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "" 200 8563 "-" ' \
               u'"Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)

        assert record is None

    def test_wrong_request(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "\x80w\x01\x03\x01" 200 8563 "-" ' \
               u'"Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)

        assert record is None

    def test_with_latency_in_milliseconds(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "POST /content/csl/contentupdate/xxx HTTP/1.1" 200 8563 '\
               u'"-" "Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 1253'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser, True)

        assert record.latency == 1253

    def test_with_latency_in_microseconds(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "POST /content/csl/contentupdate/xxx HTTP/1.1" 200 8563 '\
               u'"-" "Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 1253'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser, False)

        assert record.latency == 1

    def test_invalid_date_day(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Jah/2013:10:59:59 +0200] "POST /content/csl/contentupdate/xxx HTTP/1.1" 200 8563 '\
               u'"-" "Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)
        assert record is None

    def test_invalid_response_code(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "POST /content/csl/contentupdate/xxx HTTP/1.1" 200.1 ' \
            u'8563 "-" "Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)
        assert record is None

    def test_empty_response_code(self, monkeypatch):
        utils_setup(monkeypatch)

        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "POST /content/csl/contentupdate/xxx HTTP/1.1" "" 8563 ' \
               u'"-" "Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        parser = apachelog.parser(settings.ELF_FORMAT)
        record = parse_line(line, parser)
        assert record is None


class TestFormatEmptyValue():
    def test_format_valid(self):
        assert format_value_for_munin(17) == 17

    def test_zero_allowed(self):
        assert format_value_for_munin(0, True) == 0

    def test_zero_not_allowed(self):
        assert format_value_for_munin(0, False) == 'U'

    def test_none(self):
        assert format_value_for_munin(None) == 'U'


class TestFormatFilename():
    def test_format_filename_no_template(self):
        f, p = format_filename('file.log', datetime.datetime.now())
        assert f == 'file.log'
        assert p['ts'] == datetime.timedelta()
        assert p['ts-name-only'] is False

    def test_format_filename_with_template(self):
        dt = datetime.datetime.now()
        f, p = format_filename('file.log-%y-%m-%d-%H', dt)
        assert f == dt.strftime('file.log-%y-%m-%d-%H')
        assert p['ts'] == datetime.timedelta()
        assert p['ts-name-only'] is False

    def test_format_filename_shift_error(self):
        f, p = format_filename('file.log?xx', datetime.datetime.now())
        assert f == 'file.log'
        assert p['ts'] == datetime.timedelta()
        assert p['ts-name-only'] is False

    def test_format_filename_shift_positive(self):
        name = 'file.log-%Y-%m-%d-%H'
        dt = datetime.datetime.now()
        dt_shifted = dt + datetime.timedelta(hours=1)
        formatted_name = dt_shifted.strftime(name)
        f, p = format_filename(name+'?ts=+3600', dt)
        assert f == formatted_name
        assert p['ts'] == datetime.timedelta(hours=1)
        assert p['ts-name-only'] is False

    def test_format_filename_shift_negative(self):
        name = 'file.log-%Y-%m-%d-%H'
        dt = datetime.datetime.now()
        dt_shifted = dt + datetime.timedelta(hours=-1)
        formatted_name = dt_shifted.strftime(name)
        f, p = format_filename(name+'?ts=-3600', dt)
        assert f == formatted_name
        assert p['ts'] == datetime.timedelta(hours=-1)
        assert p['ts-name-only'] is False

    def test_format_filename_name_only_true(self):
        name = 'file.log-%Y-%m-%d-%H'
        dt = datetime.datetime.now()
        dt_shifted = dt + datetime.timedelta(hours=1)
        formatted_name = dt_shifted.strftime(name)
        f, p = format_filename(name+'?ts=+3600&ts-name-only=true', dt)
        assert f == formatted_name
        assert p['ts'] == datetime.timedelta()
        assert p['ts-name-only'] is True

    def test_format_filename_name_only_false(self):
        name = 'file.log-%Y-%m-%d-%H'
        dt = datetime.datetime.now()
        dt_shifted = dt + datetime.timedelta(hours=1)
        formatted_name = dt_shifted.strftime(name)
        f, p = format_filename(name+'?ts=+3600&ts-name-only=false', dt)
        assert f == formatted_name
        assert p['ts'] == datetime.timedelta(hours=1)
        assert p['ts-name-only'] is False