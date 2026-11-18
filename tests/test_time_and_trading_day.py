import copy
import pickle
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import DATA_FIELD, DATA_SRC, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.TradingCalendar import TradingCalendar
from DataAPI import csvAPI
from KLine.KLine_Unit import CKLine_Unit


def bar(timestamp, trading_day=None):
    return CKLine_Unit({
        DATA_FIELD.FIELD_TIME: CTime.from_str(timestamp, trading_day=trading_day),
        DATA_FIELD.FIELD_OPEN: 10,
        DATA_FIELD.FIELD_HIGH: 12,
        DATA_FIELD.FIELD_LOW: 9,
        DATA_FIELD.FIELD_CLOSE: 11,
    })


class TimeTests(unittest.TestCase):
    def test_formats_preserve_seconds_and_order(self):
        for text in ('2026-07-03 09:30:01', '20260703093001', '20260703093001123'):
            with self.subTest(text=text):
                time = CTime.from_str(text)
                self.assertEqual(time.second, 1)
                self.assertEqual(str(time), '2026/07/03 09:30:01')
                self.assertGreater(CTime.from_str('2026-07-03 09:30:02'), time)
        self.assertEqual(CTime.from_str('2026-07-03 09:30').to_str(), '2026/07/03 09:30')
        self.assertEqual(CTime.from_str('2026-07-03 09:30').to_str(True), '2026/07/03 09:30:00')

    def test_midnight_and_legacy_daily_semantics(self):
        time = CTime.from_str('2026-07-04 00:00:00')
        self.assertEqual(datetime.fromtimestamp(time.ts), datetime(2026, 7, 4))
        self.assertEqual(str(time), '2026/07/04 00:00')
        self.assertEqual(datetime.fromtimestamp(CTime(2026, 7, 4, 0, 0, 5).ts), datetime(2026, 7, 4, 0, 0, 5))
        daily = CTime.from_str('2026-07-03')
        self.assertEqual(str(daily), '2026/07/03')
        self.assertEqual(datetime.fromtimestamp(daily.ts), datetime(2026, 7, 3, 23, 59))
        self.assertEqual(str(CTime.from_str('20260703')), str(daily))

    def test_trading_day_does_not_change_chronology(self):
        night = CTime.from_str('2026-07-03 21:00:01', trading_day='20260706')
        self.assertEqual(night.trading_day, date(2026, 7, 6))
        self.assertEqual(datetime.fromtimestamp(night.ts), datetime(2026, 7, 3, 21, 0, 1))
        self.assertEqual(str(night), '2026/07/03 21:00:01')
        for restored in (copy.deepcopy(night), pickle.loads(pickle.dumps(night))):
            self.assertEqual(restored.trading_day, night.trading_day)
            self.assertEqual(restored.ts, night.ts)
        del night._trading_day  # Simulate a CTime from an older pickle.
        self.assertEqual(night.trading_day, date(2026, 7, 3))

    def test_invalid_input_is_rejected(self):
        for value in ('2026-07-03 09:30:60', '2026-02-30', '2026070309300', 'garbage'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CTime.from_str(value)
        with self.assertRaises(ValueError):
            CTime.from_str('2026-07-03', trading_day='not-a-date')

    def test_all_adapters_keep_seconds(self):
        # No provider SDK or live connection is needed to exercise these parsers.
        with patch.dict('sys.modules', {'baostock': ModuleType('baostock'), 'ccxt': ModuleType('ccxt')}):
            from DataAPI.BaoStockAPI import parse_time_column as parse_bao
            from DataAPI.ccxt import CCXT
            exchange = CCXT('example', KL_TYPE.K_1S)
            for parser in (csvAPI.parse_time_column, parse_bao, exchange.parse_time_column):
                for value in ('2026-07-04 00:00:01', '20260704000001000'):
                    with self.subTest(parser=parser, value=value):
                        time = parser(value)
                        self.assertEqual(time.second, 1)
                        self.assertEqual(datetime.fromtimestamp(time.ts), datetime(2026, 7, 4, 0, 0, 1))


class CalendarTests(unittest.TestCase):
    def test_explicit_weekend_and_holiday_sessions(self):
        # Illustrative supplied schedule, not an embedded exchange holiday calendar.
        calendar = TradingCalendar([
            (datetime(2026, 7, 3, 21), datetime(2026, 7, 4, 2, 30), '2026-07-06'),
            (datetime(2026, 7, 6, 9), datetime(2026, 7, 6, 15), '2026-07-06'),
            (datetime(2026, 7, 8, 9), datetime(2026, 7, 8, 15), '2026-07-08'),
        ])
        for timestamp in (datetime(2026, 7, 3, 21), datetime(2026, 7, 4, 0), datetime(2026, 7, 4, 2, 30), datetime(2026, 7, 6, 15)):
            self.assertEqual(calendar(timestamp), date(2026, 7, 6))
        for timestamp in (datetime(2026, 7, 4, 2, 30, 1), datetime(2026, 7, 5, 21), datetime(2026, 7, 6, 21), datetime(2026, 7, 7, 9)):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                calendar(timestamp)
        self.assertEqual(calendar(datetime(2026, 7, 8, 9)), date(2026, 7, 8))

    def test_overlapping_sessions_rejected(self):
        with self.assertRaises(ValueError):
            TradingCalendar([
                (datetime(2026, 7, 3, 21), datetime(2026, 7, 4, 2, 30), '2026-07-06'),
                (datetime(2026, 7, 4, 0), datetime(2026, 7, 4, 1), '2026-07-06'),
            ])


class LoadingTests(unittest.TestCase):
    def make_chan(self, levels):
        return CChan('example', lv_list=levels, config=CChanConfig({
            'trigger_step': True, 'print_warning': False,
            'max_kl_inconsistent_cnt': 1,
        }))

    def test_second_bars_are_distinct_and_monotonic(self):
        chan = self.make_chan([KL_TYPE.K_1S])
        chan.trigger_load({KL_TYPE.K_1S: [bar(f'2026-07-03 09:30:0{i}') for i in range(3)]})
        times = [klu.time.to_str() for klu in chan[0].klu_iter()]
        self.assertEqual(len(set(times)), 3)
        with self.assertRaises(CChanException) as error:
            chan.trigger_load({KL_TYPE.K_1S: [bar('2026-07-03 09:30:02')]})
        self.assertEqual(error.exception.errcode, ErrCode.KL_NOT_MONOTONOUS)

    def test_weekend_night_routes_to_next_daily_parent(self):
        chan = self.make_chan([KL_TYPE.K_DAY, KL_TYPE.K_1S])
        calendar = TradingCalendar([
            (datetime(2026, 7, 3, 21), datetime(2026, 7, 4, 2, 30), '2026-07-06'),
        ])
        children = [
            bar('2026-07-03 15:00:00'),
            bar('2026-07-03 21:00:01', calendar(datetime(2026, 7, 3, 21, 0, 1))),
            bar('2026-07-04 00:00:00', calendar(datetime(2026, 7, 4))),
            bar('2026-07-06 15:00:00'),
            bar('2026-07-06 21:00:01', '2026-07-07'),
        ]
        chan.trigger_load({KL_TYPE.K_DAY: [bar('2026-07-03')], KL_TYPE.K_1S: children})
        self.assertEqual(children[0].sup_kl.time.trading_day, date(2026, 7, 3))
        self.assertIsNone(children[1].sup_kl)
        chan.trigger_load({KL_TYPE.K_DAY: [bar('2026-07-06'), bar('2026-07-07')]})
        self.assertEqual([child.sup_kl.time.trading_day for child in children], [
            date(2026, 7, 3), date(2026, 7, 6), date(2026, 7, 6), date(2026, 7, 6), date(2026, 7, 7),
        ])
        self.assertFalse(chan.kl_inconsistent_detail)

    def test_intraday_parent_crosses_midnight_using_real_time(self):
        chan = self.make_chan([KL_TYPE.K_60M, KL_TYPE.K_1S])
        parents = [bar('2026-07-04 00:00:01', '2026-07-06'), bar('2026-07-04 01:00:01', '2026-07-06')]
        children = [bar('2026-07-03 23:59:59', '2026-07-06'), bar('2026-07-04 00:00:01', '2026-07-06'), bar('2026-07-04 00:00:02', '2026-07-06')]
        chan.trigger_load({KL_TYPE.K_60M: parents, KL_TYPE.K_1S: children})
        self.assertIs(children[0].sup_kl, parents[0])
        self.assertIs(children[1].sup_kl, parents[0])
        self.assertIs(children[2].sup_kl, parents[1])

    def test_weekly_parent_does_not_consume_next_weeks_night(self):
        chan = self.make_chan([KL_TYPE.K_WEEK, KL_TYPE.K_1S])
        parents = [bar('2026-07-03'), bar('2026-07-10')]
        children = [bar('2026-07-03 15:00:00'), bar('2026-07-03 21:00:01', '2026-07-06')]
        chan.trigger_load({KL_TYPE.K_WEEK: parents, KL_TYPE.K_1S: children})
        self.assertIs(children[0].sup_kl, parents[0])
        self.assertIs(children[1].sup_kl, parents[1])

    def test_three_levels_keep_daily_and_intraday_boundaries(self):
        chan = self.make_chan([KL_TYPE.K_DAY, KL_TYPE.K_60M, KL_TYPE.K_1S])
        daily = bar('2026-07-06')
        parents = [bar('2026-07-03 22:00:00', '2026-07-06'), bar('2026-07-04 00:00:01', '2026-07-06')]
        children = [bar('2026-07-03 21:00:01', '2026-07-06'), bar('2026-07-04 00:00:00', '2026-07-06')]
        chan.trigger_load({KL_TYPE.K_DAY: [daily], KL_TYPE.K_60M: parents, KL_TYPE.K_1S: children})
        self.assertEqual(daily.sub_kl_list, parents)
        self.assertIs(children[0].sup_kl, parents[0])
        self.assertIs(children[1].sup_kl, parents[1])

    def test_stock_late_seconds_stay_in_same_day(self):
        chan = self.make_chan([KL_TYPE.K_DAY, KL_TYPE.K_1S])
        child = bar('2026-07-03 23:59:59')
        chan.trigger_load({KL_TYPE.K_DAY: [bar('2026-07-03')], KL_TYPE.K_1S: [child]})
        self.assertEqual(child.sup_kl.time.trading_day, date(2026, 7, 3))

    def test_mismatched_trading_day_still_rejected(self):
        chan = self.make_chan([KL_TYPE.K_60M, KL_TYPE.K_1S])
        with self.assertRaises(CChanException) as error:
            chan.trigger_load({
                KL_TYPE.K_60M: [bar('2026-07-04 00:00:01', '2026-07-06')],
                KL_TYPE.K_1S: [bar('2026-07-03 23:59:59')],
            })
        self.assertEqual(error.exception.errcode, ErrCode.KL_TIME_INCONSISTENT)

    def test_csv_batch_loading_and_trading_day_filters(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'DataAPI').mkdir()
            (root / 'example_day.csv').write_text('time,open,high,low,close\n2026-07-06,10,12,9,11\n', encoding='utf-8')
            (root / 'example_1s.csv').write_text(
                'time,open,high,low,close,trading_day\n'
                '2026-07-03 21:00:01,10,12,9,11,20260706\n'
                '2026-07-04 00:00:00,10,12,9,11,2026-07-06\n'
                '2026-07-06 15:00:00,10,12,9,11,2026-07-06\n'
                '2026-07-06 21:00:01,10,12,9,11,2026-07-07\n', encoding='utf-8')
            with patch.object(csvAPI, '__file__', str(root / 'DataAPI' / 'csvAPI.py')):
                chan = CChan('example', begin_time='2026-07-06', end_time='2026-07-06',
                             data_src=DATA_SRC.CSV, lv_list=[KL_TYPE.K_DAY, KL_TYPE.K_1S],
                             config=CChanConfig({'max_kl_inconsistent_cnt': 1}))
                children = list(chan[0].klu_iter())[0].sub_kl_list
                self.assertEqual(len(children), 3)
                self.assertEqual(children[0].time.day, 3)
                self.assertEqual(children[0].time.second, 1)
                api = csvAPI.CSV_API('example', KL_TYPE.K_1S, '2026-07-04 00:00:00', '2026-07-06 15:00:00')
                self.assertEqual(len(list(api.get_kl_data())), 2)


if __name__ == '__main__':
    unittest.main()
