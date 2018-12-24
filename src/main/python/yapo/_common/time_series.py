import pandas as pd
import numpy as np
from enum import Enum


class TimeSeriesKind(Enum):
    VALUES = 1
    DIFF = 2
    REDUCED_VALUE = 3
    YTD = 4
    CUMULATIVE = 5
    CURRENCY_RATE = 6

    def __mul__(self, other):
        if isinstance(other, (int, float, complex)):
            return self
        if self == TimeSeriesKind.CURRENCY_RATE:
            return other
        if other == TimeSeriesKind.CURRENCY_RATE:
            return self
        if self != other:
            raise ValueError('kinds are incompatible')
        return self

    def __add__(self, other):
        if isinstance(other, (int, float, complex)):
            return self
        if self != other:
            raise ValueError('kinds are incompatible')
        return self

    def __radd__(self, other):
        if isinstance(other, (int, float, complex)):
            return self
        if self != other:
            raise ValueError('kinds are incompatible')
        return self

    def __rsub__(self, other):
        if isinstance(other, (int, float, complex)):
            return self
        if self != other:
            raise ValueError('kinds are incompatible')
        return self

    def __sub__(self, other):
        if isinstance(other, (int, float, complex)):
            return self
        if self != other:
            raise ValueError('kinds are incompatible')
        return self

    def __truediv__(self, other):
        if isinstance(other, (int, float, complex)):
            return self
        if self == TimeSeriesKind.CURRENCY_RATE:
            return other
        if other == TimeSeriesKind.CURRENCY_RATE:
            return self
        if self != other:
            raise ValueError('kinds are incompatible')
        return self

    def __pow__(self, power, modulo=None):
        return self

    def sqrt(self):
        return self

    def std(self):
        return self

    def mean(self):
        return self

    def sum(self):
        return self

    def prod(self):
        return self

    def cumprod(self):
        return TimeSeriesKind.CUMULATIVE

    def pct_change(self):
        return TimeSeriesKind.DIFF


class TimeSeries:
    def __init__(self, values, start_period: pd.Period, end_period: pd.Period, kind):
        if not isinstance(values, np.ndarray):
            raise ValueError('values should be numpy array')

        self._values = values
        self._size = self._values.size
        self._start_period = start_period
        self._end_period = end_period
        self._kind = kind

        if self.kind == TimeSeriesKind.DIFF or \
                self.kind == TimeSeriesKind.VALUES or \
                self.kind == TimeSeriesKind.CUMULATIVE:
            if self.size != end_period - start_period + 1:
                raise ValueError('values and period range have different lengths')

        if self.kind == TimeSeriesKind.YTD:
            if start_period.month != 1:
                raise ValueError('start period month should be 1')
            if end_period.month != 12:
                raise ValueError('end period month should be 1')
            if len(values) != end_period.year - start_period.year + 1:
                raise ValueError('values len should be equal to full years count')

        if self.kind == TimeSeriesKind.REDUCED_VALUE:
            if self.size > 1:
                raise ValueError('size is greater than 1')

    def __validate(self, time_series):
        if self._start_period != time_series.start_period:
            raise ValueError('start periods are incompatible')
        if self._end_period != time_series.end_period:
            raise ValueError('end periods are incompatible')

    @property
    def values(self):
        return self._values

    @property
    def value(self):
        if self.kind == TimeSeriesKind.REDUCED_VALUE:
            return self._values[0]
        raise ValueError('incorrect `kind` to get value')

    @property
    def kind(self):
        return self._kind

    @property
    def start_period(self):
        return self._start_period

    @property
    def end_period(self):
        return self._end_period

    @property
    def size(self):
        return self._size

    def pct_change(self):
        if len(self._values) < 2:
            raise ValueError('`value` length should be >= 2')
        vals = np.diff(self._values) / self._values[:-1]
        return TimeSeries(values=vals,
                          start_period=self._start_period + 1, end_period=self._end_period,
                          kind=self.kind.pct_change())

    def apply(self, fun, *args):
        if len(args) == 0:
            ts = TimeSeries(values=fun(self._values),
                            start_period=self._start_period, end_period=self._end_period,
                            kind=fun(self.kind))
            return ts
        else:
            other = args[0]
            if isinstance(other, TimeSeries):
                self.__validate(other)
                ts = TimeSeries(values=fun(self._values, other._values),
                                start_period=self._start_period, end_period=self._end_period,
                                kind=fun(self.kind, other.kind))
                return ts
            elif isinstance(other, (int, float, complex)):
                ts = TimeSeries(values=fun(self._values, other),
                                start_period=self._start_period, end_period=self._end_period,
                                kind=self._kind)
                return ts
            else:
                raise ValueError('argument has incompatible type')

    def reduce(self, fun):
        return TimeSeries(values=np.array([fun(self._values)]),
                          start_period=self._start_period, end_period=self._end_period,
                          kind=TimeSeriesKind.REDUCED_VALUE)

    def __mul__(self, other):
        return self.apply(lambda x, y: x * y, other)

    def __add__(self, other):
        return self.apply(lambda x, y: x + y, other)

    def __radd__(self, other):
        return self.apply(lambda x, y: y + x, other)

    def __rsub__(self, other):
        return self.apply(lambda x, y: y - x, other)

    def __sub__(self, other):
        return self.apply(lambda x, y: x - y, other)

    def __truediv__(self, other):
        return self.apply(lambda x, y: x / y, other)

    def __getitem__(self, key):
        if isinstance(key, slice):
            if not (key.step is None or key.step == 1):
                raise ValueError('step value is not supported: {}'.format(key.step))
            pr = pd.period_range(start=self._start_period, end=self._end_period, freq='M')
            pr = pr[key.start:key.stop]
            ts = TimeSeries(values=self._values[key.start:key.stop],
                            start_period=pr.min(), end_period=pr.max(),
                            kind=self._kind)
            return ts
        return self._values[key]

    def __pow__(self, power, modulo=None):
        return self.apply(lambda x: x ** power)

    def sqrt(self):
        return self.apply(lambda x: np.sqrt(x))

    def std(self):
        return self.reduce(lambda x: x.std())

    def mean(self):
        return self.reduce(lambda x: x.mean())

    def sum(self):
        return self.reduce(lambda x: x.sum())

    def prod(self):
        return self.reduce(lambda x: x.prod())

    def cumprod(self):
        return self.apply(lambda x: x.cumprod())

    def __repr__(self):
        return 'TimeSeries(start_period={}, end_period={}, kind={}, values={}'.format(
            self._start_period, self._end_period, self._kind, self._values
        )
