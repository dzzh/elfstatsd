import math
import settings


class CalledMethod():

    def __init__(self, name):
        self.name = name
        self.calls = []
        self.response_codes = {}

    @property
    def num_calls(self):
        return len(self.calls) if self.calls else 0

    def percentile(self, percent):
        """
        Compute percentile of values in an array.

        @param float percent: percent from 0.0 to 1.0
        @return int: percent or 0 if no values are found
        """
        if not len(self.calls):
            return 0

        k = (len(self.calls)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            result = self.calls[int(k)]
        else:
            d0 = self.calls[int(f)] * (c-k)
            d1 = self.calls[int(c)] * (k-f)
            result = int(round(d0+d1))

        return result

    @property
    def stalled(self):
        """
        Return number of stalled calls
        """
        return len([i for i in self.calls if i > settings.STALLED_CALL_THRESHOLD])

    @property
    def min(self):
        return self.calls[0] if self.calls else 0

    @property
    def max(self):
        return self.calls[-1] if self.calls else 0

    @property
    def avg(self):
        return sum(self.calls)/len(self.calls) if self.calls else 0
