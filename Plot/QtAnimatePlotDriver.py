"""PyQtGraph 逐帧动画驱动：复用画布 + K 线增量 + 结构 sure/tip 分层。"""

from __future__ import annotations

import sys
from typing import Dict, Iterator, Optional

from PyQt5 import QtCore, QtWidgets

from Chan import CChan

from .QtPlotDriver import CQtPlotDriver, PlotConfigInput, PlotPara


class CQtAnimateDriver:
    """
    用 QTimer 驱动 chan.step_load()。

    计算侧增量；绘图侧复用同一个 CQtPlotDriver：
    - K 线 CandlestickItem.setData
    - bi/seg/zs 的 sure 前缀冻结，未确认尾部每帧重画
    """

    def __init__(
        self,
        chan: CChan,
        plot_config: Optional[PlotConfigInput] = None,
        plot_para: Optional[PlotPara] = None,
        auto_start: bool = True,
    ) -> None:
        if plot_config is None:
            plot_config = {}
        if plot_para is None:
            plot_para = {}
        self.chan: CChan = chan
        self.plot_config: PlotConfigInput = plot_config
        self.plot_para: PlotPara = plot_para
        figure_cfg: Dict = plot_para.get("figure", {})
        self.interval_ms: int = int(figure_cfg.get("animate_interval_ms", 50))
        # 兼容旧行为：figure.full_redraw=True 时每帧销毁重建
        self.full_redraw: bool = bool(figure_cfg.get("full_redraw", False))

        existing_app = QtWidgets.QApplication.instance()
        self.app: QtWidgets.QApplication
        if existing_app is None:
            self.app = QtWidgets.QApplication(sys.argv)
        else:
            self.app = existing_app

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle(f"chan.py animate - {chan.code}")
        self.container = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.window.setCentralWidget(self.container)

        self._driver: Optional[CQtPlotDriver] = None
        self._step_iter: Iterator[CChan] = chan.step_load()
        self._paused: bool = False
        self._frame: int = 0

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._on_tick)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_pause = QtWidgets.QPushButton("暂停")
        self.btn_pause.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self.btn_pause)
        btn_row.addStretch(1)
        self.layout.addLayout(btn_row)

        self.plot_host = QtWidgets.QWidget()
        self.plot_host_layout = QtWidgets.QVBoxLayout(self.plot_host)
        self.plot_host_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.plot_host, stretch=1)

        self.window.resize(1920, 900)
        self.window.setStyleSheet("background-color: white;")
        self.window.show()

        self._on_tick()
        if auto_start:
            self.timer.start(self.interval_ms)
            self.app.exec_()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self.btn_pause.setText("继续" if self._paused else "暂停")
        if self._paused:
            self.timer.stop()
        else:
            self.timer.start(self.interval_ms)

    def _clear_plot_host(self) -> None:
        while self.plot_host_layout.count():
            item = self.plot_host_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._driver = None

    def _ensure_driver(self) -> CQtPlotDriver:
        if self._driver is not None:
            return self._driver
        self._driver = CQtPlotDriver(
            self.chan,
            plot_config=self.plot_config,
            plot_para=self.plot_para,
            parent_widget=self.plot_host,
            create_app=False,
            defer_draw=True,
        )
        self.plot_host_layout.addWidget(self._driver.widget)
        return self._driver

    def _on_tick(self) -> None:
        if self._paused:
            return
        try:
            next(self._step_iter)
        except StopIteration:
            self.timer.stop()
            self.btn_pause.setText("结束")
            self.btn_pause.setEnabled(False)
            return

        self._frame += 1
        if self.full_redraw:
            self._clear_plot_host()
            self._driver = CQtPlotDriver(
                self.chan,
                plot_config=self.plot_config,
                plot_para=self.plot_para,
                parent_widget=self.plot_host,
                create_app=False,
            )
            self.plot_host_layout.addWidget(self._driver.widget)
        else:
            driver = self._ensure_driver()
            driver.refresh()
        QtWidgets.QApplication.processEvents()
