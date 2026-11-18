import re
from datetime import date, datetime


class CTime:
    def __init__(self, year, month, day, hour, minute, second=0, auto=True, *, trading_day=None):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.auto = auto  # 自适应对天的理解
        self._trading_day = self.parse_trading_day(trading_day) if trading_day is not None else None
        self.set_timestamp()  # set self.ts

    def __str__(self):
        return self.to_str()

    def to_str(self, show_seconds=False):
        if self.hour == self.minute == self.second == 0 and self.auto and not show_seconds:
            return f"{self.year:04}/{self.month:02}/{self.day:02}"
        text = f"{self.year:04}/{self.month:02}/{self.day:02} {self.hour:02}:{self.minute:02}"
        return f"{text}:{self.second:02}" if self.second or show_seconds else text

    @staticmethod
    def parse_trading_day(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            if re.fullmatch(r'\d{8}', value):
                return datetime.strptime(value, '%Y%m%d').date()
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                return date.fromisoformat(value)
        raise ValueError(f'Invalid trading day: {value!r}')

    @property
    def trading_day(self):
        # getattr keeps older pickles (without this metadata) readable.
        return getattr(self, '_trading_day', None) or date(self.year, self.month, self.day)

    @classmethod
    def from_str(cls, value, *, auto=None, trading_day=None):
        """Parse date/minute/second timestamps; compact 17-digit input has milliseconds truncated."""
        formats = (
            (r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'),
            (r'\d{8}', '%Y%m%d'),
            (r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', '%Y-%m-%d %H:%M'),
            (r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '%Y-%m-%d %H:%M:%S'),
            (r'\d{14}', '%Y%m%d%H%M%S'),
            (r'\d{17}', '%Y%m%d%H%M%S%f'),
        )
        for pattern, fmt in formats:
            if re.fullmatch(pattern, value):
                dt = datetime.strptime(value, fmt)
                if auto is None:
                    auto = len(value) in (8, 10)
                return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
                           auto=auto, trading_day=trading_day)
        raise ValueError(f'Unknown time format: {value!r}')

    def toDateStr(self, splt=''):
        return f"{self.year:04}{splt}{self.month:02}{splt}{self.day:02}"

    def toDate(self):
        return CTime(self.year, self.month, self.day, 0, 0, auto=False)

    def set_timestamp(self):
        if self.hour == self.minute == self.second == 0 and self.auto:
            date = datetime(self.year, self.month, self.day, 23, 59, self.second)
        else:
            date = datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)
        self.ts = date.timestamp()

    def __gt__(self, t2):
        return self.ts > t2.ts

    def __ge__(self, t2):
        return self.ts >= t2.ts
