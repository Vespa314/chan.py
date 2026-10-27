from bisect import bisect_right
from datetime import datetime

from Common.CTime import CTime


class TradingCalendar:
    """Resolve exchange-local wall times from explicit (start, end, trading_day) sessions.

    Bounds are inclusive, matching bar end timestamps. Supply actual sessions from
    the exchange/vendor, including holidays and each instrument's night schedule.
    Missing sessions raise rather than guessing the next weekday.
    """

    def __init__(self, sessions):
        self.sessions = [(start, end, CTime.parse_trading_day(day)) for start, end, day in sessions]
        for start, end, _ in self.sessions:
            if not isinstance(start, datetime) or not isinstance(end, datetime):
                raise ValueError('Session bounds must be datetime objects')
            if start.tzinfo is not None or end.tzinfo is not None:
                raise ValueError('Use exchange-local naive datetimes for session bounds')
            if start > end:
                raise ValueError('Session start must not follow its end')
        self.sessions.sort(key=lambda session: session[0])
        previous_end = None
        for start, end, _ in self.sessions:
            if previous_end is not None and start <= previous_end:
                raise ValueError('Trading sessions must have ordered, non-overlapping bounds')
            previous_end = end
        self.starts = [start for start, _, _ in self.sessions]

    def __call__(self, timestamp):
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is not None:
            raise ValueError('Use an exchange-local naive datetime for the timestamp')
        idx = bisect_right(self.starts, timestamp) - 1
        if idx >= 0 and timestamp <= self.sessions[idx][1]:
            return self.sessions[idx][2]
        raise ValueError(f'No trading session for {timestamp}')
