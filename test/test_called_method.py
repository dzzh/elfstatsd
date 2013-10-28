import pytest

from elfstatsd import settings
from elfstatsd.dto.called_method import CalledMethod


@pytest.fixture(scope='class')
def called_method():
    """
    Instance of a CalledMethod class with pre-set attributes
    """
    method = CalledMethod('method')
    method.calls = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    return method


@pytest.mark.usefixtures('called_method')
class TestCalledMethod():
    def test_num_calls(self):
        assert called_method().num_calls == 9

    def test_num_calls_empty(self):
        assert CalledMethod('method').num_calls == 0

    def test_percentile_25(self):
        assert called_method().percentile(25) == 30

    def test_percentile_50(self):
        assert called_method().percentile(50) == 50

    def test_percentile_50_2(self):
        method = called_method()
        method.calls.append(100)
        assert method.percentile(50) == 55

    def test_percentile_75(self):
        assert called_method().percentile(75) == 70

    def test_percentile_empty(self):
        assert CalledMethod('method').percentile(50) == 0

    def test_stalled(self, monkeypatch):
        monkeypatch.setattr(settings, 'STALLED_CALL_THRESHOLD', 69)
        assert called_method().stalled == 3

    def test_avg(self):
        assert called_method().avg == 50

    def test_min(self):
        assert called_method().min == 10

    def test_max(self):
        assert called_method().max == 90