"""离线回归：uv run --with PyQt6 --with matplotlib --with akshare python Script/test_scanner_gui.py"""
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from App import ashare_bsp_scanner_gui as gui


def stocks():
    return gui.pd.DataFrame([{'代码': '000001', '名称': '测试', '最新价': 10, '涨跌幅': 1}])


class ScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gui.QApplication.instance() or gui.QApplication([])
        gui.apply_theme(cls.app)

    def setUp(self):
        self.window = gui.AkshareGUI()
        self.window.plot_chart = lambda: None
        self.release = Event()

    def pump_until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate(), '后台任务未按预期完成')

    def tearDown(self):
        self.release.set()
        self.window.close()
        self.pump_until(lambda: self.window.scan_thread is None and self.window.analysis_thread is None)
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_list_loading_is_async_and_cancelled_before_analysis(self):
        started = Event()

        def load():
            started.set()
            self.release.wait(3)
            return stocks()

        with patch.object(gui, 'get_tradable_stocks', load), patch.object(gui, 'CChan') as chan:
            self.window.stock_table.setRowCount(1)
            self.window.stock_cache['old'] = object()
            self.window.start_scan()
            self.assertEqual(self.window.stock_table.rowCount(), 0)
            self.assertEqual(self.window.stock_cache, {})
            self.pump_until(started.is_set)
            self.assertFalse(self.window.scan_btn.isEnabled())
            self.window.stop_scan()
            self.release.set()
            self.pump_until(lambda: self.window.scan_thread is None)
            chan.assert_not_called()
            self.assertIn('已停止', self.window.statusBar.currentMessage())
            self.assertTrue(self.window.scan_btn.isEnabled())

    def test_stop_during_stock_request_discards_result(self):
        started = Event()

        def analyze(**kwargs):
            started.set()
            self.release.wait(3)
            return object()  # 停止后不应访问这个结果

        with patch.object(gui, 'get_tradable_stocks', stocks), patch.object(gui, 'CChan', analyze):
            self.window.start_scan()
            self.pump_until(started.is_set)
            self.window.stop_scan()
            self.release.set()
            self.pump_until(lambda: self.window.scan_thread is None)
            self.assertEqual(self.window.stock_table.rowCount(), 0)
            self.assertIn('已停止', self.window.progress_label.text())

    def test_only_latest_analysis_is_displayed_and_pending_requests_coalesce(self):
        calls = []

        def analyze(**kwargs):
            calls.append(kwargs['code'])
            if len(calls) == 1:
                self.release.wait(3)
            return SimpleNamespace(code=kwargs['code'])

        with patch.object(gui, 'CChan', analyze):
            self.window.analyze_stock('000001')
            self.pump_until(lambda: len(calls) == 1)
            self.window.analyze_stock('000002')
            self.window.analyze_stock('000003')
            self.release.set()
            self.pump_until(lambda: self.window.analysis_thread is None)
            self.assertEqual(calls, ['000001', '000003'])
            self.assertEqual(self.window.chan.code, '000003')

    def test_cached_selection_invalidates_running_analysis(self):
        started = Event()

        def analyze(**kwargs):
            started.set()
            self.release.wait(3)
            return SimpleNamespace(code='000001')

        with patch.object(gui, 'CChan', analyze):
            self.window.analyze_stock('000001')
            self.pump_until(started.is_set)
            cached = SimpleNamespace(code='000002')
            self.window.on_buy_point_found(dict(code='000002', name='缓存', price=10,
                change=1, bsp_type='1', bsp_time='2026-01-01', chan=cached))
            self.window.on_stock_clicked(0, 0)
            self.release.set()
            self.pump_until(lambda: self.window.analysis_thread is None)
            self.assertIs(self.window.chan, cached)

    def test_loading_failure_restores_controls(self):
        with patch.object(gui, 'get_tradable_stocks', return_value=gui.pd.DataFrame()):
            self.window.start_scan()
            self.pump_until(lambda: self.window.scan_thread is None)
            self.assertTrue(self.window.scan_btn.isEnabled())
            self.assertFalse(self.window.stop_btn.isEnabled())
            self.assertIn('获取股票列表失败', self.window.statusBar.currentMessage())

    def test_cancelled_scan_ignores_queued_results(self):
        worker = gui.ScanThread(stocks(), self.window.get_chan_config())
        worker.stop()
        self.window.scan_thread = worker
        self.window.on_buy_point_found({})
        self.assertEqual(self.window.stock_table.rowCount(), 0)
        self.window.on_scan_finished()
        self.assertIn('已停止', self.window.progress_label.text())

    def test_history_requests_have_timeout(self):
        from DataAPI.AkshareAPI import CAkshare
        with patch.object(gui.ak, 'stock_zh_a_hist', return_value=gui.pd.DataFrame()) as fetch:
            api = CAkshare('000001')
            api.SetBasciInfo()
            list(api.get_kl_data())
            self.assertEqual(fetch.call_args.kwargs['timeout'], 15)

    def test_close_waits_without_blocking_event_loop(self):
        started = Event()

        def analyze(**kwargs):
            started.set()
            self.release.wait(3)
            return SimpleNamespace(code='000001')

        with patch.object(gui, 'CChan', analyze):
            self.window.show()
            self.window.analyze_stock('000001')
            self.pump_until(started.is_set)
            self.window.close()
            self.assertTrue(self.window.isVisible())
            self.assertFalse(self.window.isEnabled())
            self.release.set()
            self.pump_until(lambda: not self.window.isVisible())

    def test_date_boundary_and_failure_counts(self):
        cutoff = datetime.now() - timedelta(days=3)
        point = SimpleNamespace(is_buy=True, klu=SimpleNamespace(time=cutoff), type2str=lambda: '1')

        class Chan:
            def __getitem__(self, index):
                return [[SimpleNamespace(time=datetime.now())]]

            def get_latest_bsp(self, number):
                return [point]

        worker = gui.ScanThread(stocks(), self.window.get_chan_config())
        found = []
        worker.found_signal.connect(found.append)
        with patch.object(gui, 'CChan', return_value=Chan()):
            worker.run()
        self.assertEqual(len(found), 1)
        self.assertEqual((worker.success_count, worker.fail_count), (1, 0))
        with patch.object(Chan, 'get_latest_bsp', side_effect=ValueError('bad data')), \
                patch.object(gui, 'CChan', return_value=Chan()):
            worker.run()
        self.assertEqual((worker.success_count, worker.fail_count), (0, 1))


if __name__ == '__main__':
    unittest.main()
