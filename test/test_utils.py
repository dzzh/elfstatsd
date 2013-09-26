import datetime
import pytest
import apachelog
from elfstatsd.log_record import LOG_DATETIME_FORMAT
from elfstatsd.utils import parse_latency, MILLISECOND_EXPONENT, MICROSECOND_EXPONENT, SECOND_EXPONENT, NANOSECOND_EXPONENT, parse_line

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

@pytest.fixture(scope='class')
def parser():
    """
    Instance of an apachelog parser with pre-defined log format.
    """
    format = r'%h %l %u %t \"%r\" %>s %B \"%{Referer}i\" \"%{User-Agent}i\" %{JK_LB_FIRST_NAME}n %{JK_LB_LAST_NAME}n %{JK_LB_LAST_STATE}n %I %O %D'
    return apachelog.parser(format)

@pytest.mark.usefixtures("parser")
class TestParseLine():

    def test_1(self):
        line = u'172.19.0.40 - - [08/Aug/2013:10:59:59 +0200] "POST /content/csl/contentupdate/xxx HTTP/1.1" 200 8563 "-" ' \
               u'"Apache-HttpClient/4.2.1 (java 1.5)" community1 community1 OK 14987 8785 53047'
        record = parse_line(line, parser())

        assert record.request == '/content/csl/contentupdate/xxx'
        assert record.get_time() == datetime.datetime.strptime('20130808105959', LOG_DATETIME_FORMAT)
        assert record.response_code == 200
        assert record.latency == 53
        assert record.get_method_name() == 'csl_contentupdate'