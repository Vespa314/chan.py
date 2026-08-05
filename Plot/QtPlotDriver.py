"""PyQtGraph 版缠论绘图驱动，配置与绘制能力对齐 CPlotDriver。"""

from __future__ import annotations

import sys
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple, Union

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from Chan import CChan
from Common.CEnum import BI_DIR, FX_TYPE, KL_TYPE, KLINE_DIR, TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Math.Demark import T_DEMARK_INDEX, CDemarkEngine

from .PlotDriver import GetPlotMeta, cal_x_limit, parse_plot_config, show_func_helper
from .PlotMeta import (
    CBi_meta,
    CBS_Point_meta,
    CChanPlotMeta,
    CEigenFX_meta,
    CSeg_meta,
    CZS_meta,
)

ColorLike = Union[str, QtGui.QColor, Tuple[float, ...], List[float]]
XLimits = Sequence[float]
CandleBar = Tuple[float, float, float, float, float]  # x, open, high, low, close
MarkerPos = Literal["up", "down"]
MarkerValue = Union[Tuple[str, MarkerPos], Tuple[str, MarkerPos, str]]
PlotConfigInput = Union[str, Dict, List]
PlotPara = Dict[str, Dict]

_COLOR_MAP: Dict[str, str] = {
    "r": "#FF0000",
    "g": "#008000",
    "b": "#0000FF",
    "c": "#00FFFF",
    "m": "#FF00FF",
    "y": "#FFFF00",
    "k": "#000000",
    "w": "#FFFFFF",
    "orange": "#FFA500",
    "brown": "#A52A2A",
    "purple": "#800080",
    "pink": "#FFC0CB",
    "yellow": "#FFFF00",
    "black": "#000000",
    "blue": "#0000FF",
    "red": "#FF0000",
    "green": "#008000",
}


def to_qt_color(color: ColorLike) -> QtGui.QColor:
    """把 matplotlib 风格颜色名或 RGB 转为 QColor。"""
    if isinstance(color, QtGui.QColor):
        return color
    if isinstance(color, (tuple, list)):
        if len(color) < 3:
            raise CChanException(f"invalid rgb color={color}", ErrCode.PLOT_ERR)
        channels: List[int] = []
        for channel in color[:3]:
            value = float(channel)
            channels.append(int(value * 255) if value <= 1 else int(value))
        if len(color) >= 4:
            alpha = float(color[3])
            alpha_i = int(alpha * 255) if alpha <= 1 else int(alpha)
            return QtGui.QColor(channels[0], channels[1], channels[2], alpha_i)
        return QtGui.QColor(channels[0], channels[1], channels[2])
    key = str(color)
    if key in _COLOR_MAP:
        return QtGui.QColor(_COLOR_MAP[key])
    return QtGui.QColor(key)


def make_pen(
    color: ColorLike,
    width: float = 1,
    dashed: bool = False,
    style: Optional[str] = None,
) -> QtGui.QPen:
    """构造画笔；线宽按像素（cosmetic），避免缩放后变粗。"""
    pen = pg.mkPen(to_qt_color(color), width=max(1, round(width)))
    pen.setCosmetic(True)
    if dashed or style in ("dashed", "--", "dash"):
        pen.setStyle(Qt.PenStyle.DashLine)
    elif style in ("dotted", ":"):
        pen.setStyle(Qt.PenStyle.DotLine)
    return pen


def cal_y_range_by_limits(meta: CChanPlotMeta, x_limits: XLimits) -> Tuple[float, float]:
    """按可见 X 范围估算主图 Y 轴范围。"""
    x_begin = x_limits[0]
    y_min = float("inf")
    y_max = float("-inf")
    for klc_meta in meta.klc_list:
        if klc_meta.klu_list[-1].idx < x_begin:
            continue
        y_max = max(y_max, klc_meta.high)
        y_min = min(y_min, klc_meta.low)
    if y_min == float("inf"):
        return 0.0, 1.0
    return y_min, y_max


class DateAxisItem(pg.AxisItem):
    """用 K 线索引显示日期字符串的 X 轴。"""

    def __init__(self, datetick: List[str], *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.datetick: List[str] = datetick

    def tickStrings(self, values: Iterable[float], scale: float, spacing: float) -> List[str]:
        labels: List[str] = []
        n = len(self.datetick)
        for value in values:
            idx = round(value)
            labels.append(self.datetick[idx] if 0 <= idx < n else "")
        return labels


class CandlestickItem(pg.GraphicsObject):
    """批量绘制蜡烛图；对齐 matplotlib：红涨绿跌、阳线空心、阴线实心。"""

    def __init__(
        self,
        data: Sequence[CandleBar],
        width: float = 0.4,
        rugd: bool = True,
    ) -> None:
        super().__init__()
        self.data: Sequence[CandleBar] = data
        self.width: float = width
        self.rugd: bool = rugd
        if data:
            xs = [bar[0] for bar in data]
            self._x_min = min(xs) - width
            self._x_max = max(xs) + width
            self._y_min = min(bar[3] for bar in data)
            self._y_max = max(bar[2] for bar in data)
        else:
            self._x_min = 0.0
            self._x_max = 1.0
            self._y_min = 0.0
            self._y_max = 1.0

    def paint(
        self,
        painter: QtGui.QPainter,
        *args: object,
    ) -> None:
        up_color = to_qt_color("r" if self.rugd else "g")
        down_color = to_qt_color("g" if self.rugd else "r")
        half_w = self.width
        for x, open_p, high, low, close in self.data:
            is_up = close > open_p
            color = up_color if is_up else down_color
            pen = QtGui.QPen(color)
            pen.setCosmetic(True)
            pen.setWidth(1)
            painter.setPen(pen)
            # 与 PlotDriver.draw_klu 一致：阳线影线分段，阴线贯通
            if is_up:
                painter.drawLine(QtCore.QPointF(x, low), QtCore.QPointF(x, open_p))
                painter.drawLine(QtCore.QPointF(x, close), QtCore.QPointF(x, high))
                painter.setBrush(Qt.BrushStyle.NoBrush)
            else:
                painter.drawLine(QtCore.QPointF(x, low), QtCore.QPointF(x, high))
                painter.setBrush(QtGui.QBrush(color))
            body_low = min(open_p, close)
            body_h = abs(close - open_p)
            if body_h < 1e-12:
                body_h = (high - low) * 0.01 if high > low else 1e-6
            painter.drawRect(QtCore.QRectF(x - half_w / 2, body_low, half_w, body_h))

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(
            self._x_min,
            self._y_min,
            max(self._x_max - self._x_min, 1e-6),
            max(self._y_max - self._y_min, 1e-6),
        )


class CQtPlotDriver:
    """
    PyQtGraph 缠论绘图入口。

    对外用法对齐 CPlotDriver：相同 plot_config / plot_para，提供 show/save2img。
    """

    def __init__(
        self,
        chan: CChan,
        plot_config: PlotConfigInput = "",
        plot_para: Optional[PlotPara] = None,
        parent_widget: Optional[QtWidgets.QWidget] = None,
        create_app: bool = True,
    ) -> None:
        if plot_para is None:
            plot_para = {}
        self.plot_para: PlotPara = plot_para
        figure_config: Dict = plot_para.get("figure", {})

        self.app: Optional[QtWidgets.QApplication]
        if create_app:
            existing = QtWidgets.QApplication.instance()
            self.app = existing if existing is not None else QtWidgets.QApplication(sys.argv)
        else:
            self.app = QtWidgets.QApplication.instance()

        pg.setConfigOptions(antialias=True, foreground="k", background="w")

        parsed_config = parse_plot_config(plot_config, chan.lv_list)
        plot_metas = GetPlotMeta(chan, figure_config)
        self.lv_lst: List[KL_TYPE] = chan.lv_list[: len(plot_metas)]
        self.chan: CChan = chan

        x_range = self.GetRealXrange(figure_config, plot_metas[0])
        plot_macd: Dict[KL_TYPE, bool] = {
            kl_type: conf.get("plot_macd", False) for kl_type, conf in parsed_config.items()
        }

        # 对齐 matplotlib figsize 英寸量级（约 100dpi）
        default_w = float(figure_config.get("w", 24))
        default_h = float(figure_config.get("h", 10))
        macd_h_ration = float(figure_config.get("macd_h", 0.3))
        px_w = int(default_w * 100)
        total_rows_h = 0.0
        for lv in self.lv_lst:
            total_rows_h += default_h * (1 + macd_h_ration if plot_macd[lv] else 1)
        px_h = int(max(500.0, total_rows_h * 80))

        self.widget: pg.GraphicsLayoutWidget = pg.GraphicsLayoutWidget(parent=parent_widget)
        self.widget.resize(px_w, px_h)
        self.widget.setWindowTitle(f"chan.py - {chan.code}")
        self.widget.setBackground("w")
        self.figure: pg.GraphicsLayoutWidget = self.widget

        self.plot_items: Dict[KL_TYPE, List[pg.PlotItem]] = {}
        self._twin_views: List[pg.ViewBox] = []
        self.y_min: float = 0.0
        self.y_max: float = 1.0

        sseg_begin = 0
        slv_seg_cnt = plot_para.get("seg", {}).get("sub_lv_cnt", None)
        sbi_begin = 0
        slv_bi_cnt = plot_para.get("bi", {}).get("sub_lv_cnt", None)
        srange_begin = 0
        if slv_seg_cnt is not None and slv_bi_cnt is not None:
            raise CChanException(
                "you can set at most one of seg_sub_lv_cnt/bi_sub_lv_cnt",
                ErrCode.PLOT_ERR,
            )

        first_plot: Optional[pg.PlotItem] = None
        row = 0
        for meta, lv in zip(plot_metas, self.lv_lst):
            x_limits = cal_x_limit(meta, x_range)
            if lv != self.lv_lst[0]:
                if sseg_begin != 0 or sbi_begin != 0:
                    x_limits[0] = max(sseg_begin, sbi_begin)
                elif srange_begin != 0:
                    x_limits[0] = srange_begin

            axis = DateAxisItem(meta.datetick, orientation="bottom")
            plot = self.widget.addPlot(row=row, col=0, axisItems={"bottom": axis})
            plot.hideButtons()
            plot.setMenuEnabled(False)
            self._apply_grid(plot, figure_config.get("grid", "xy"))
            # 对齐 matplotlib：左上角红色标题
            title = f"{chan.code}/{lv.name.split('K_')[1]}"
            plot.setTitle(f'<span style="color:#ff0000;font-size:14pt">{title}</span>')
            plot.titleLabel.setAttr("justify", "left")
            plot.setXRange(x_limits[0], x_limits[1] + 1, padding=0)
            if first_plot is None:
                first_plot = plot
            else:
                plot.setXLink(first_plot)

            ax_macd: Optional[pg.PlotItem] = None
            items: List[pg.PlotItem] = [plot]
            row += 1
            if plot_macd[lv]:
                macd_axis = DateAxisItem(meta.datetick, orientation="bottom")
                ax_macd = self.widget.addPlot(row=row, col=0, axisItems={"bottom": macd_axis})
                ax_macd.showGrid(x=True, y=True, alpha=0.3)
                ax_macd.setXRange(x_limits[0], x_limits[1] + 1, padding=0)
                ax_macd.setXLink(first_plot)
                self.widget.ci.layout.setRowStretchFactor(row - 1, 10)
                self.widget.ci.layout.setRowStretchFactor(row, max(1, int(10 * macd_h_ration)))
                items.append(ax_macd)
                row += 1

            self.plot_items[lv] = items
            self.y_min, self.y_max = cal_y_range_by_limits(meta, x_limits)
            self.DrawElement(parsed_config[lv], meta, plot, lv, plot_para, ax_macd, x_limits)
            # 给买卖点箭头/文字留边，避免贴边裁切
            plot.setYRange(self.y_min, self.y_max, padding=0.06)

            if lv != self.lv_lst[-1]:
                if slv_seg_cnt is not None:
                    sseg_begin = meta.sub_last_kseg_start_idx(slv_seg_cnt)
                if slv_bi_cnt is not None:
                    sbi_begin = meta.sub_last_kbi_start_idx(slv_bi_cnt)
                if x_range != 0:
                    srange_begin = meta.sub_range_start_idx(x_range)

    @staticmethod
    def _apply_grid(plot: pg.PlotItem, grid_cfg: Optional[str]) -> None:
        if grid_cfg is None:
            plot.showGrid(x=False, y=False)
            return
        if grid_cfg == "xy":
            plot.showGrid(x=True, y=True, alpha=0.2)
            return
        if grid_cfg == "x":
            plot.showGrid(x=True, y=False, alpha=0.2)
            return
        if grid_cfg == "y":
            plot.showGrid(x=False, y=True, alpha=0.2)
            return
        raise CChanException(f"unsupport grid config={grid_cfg}", ErrCode.PLOT_ERR)

    def GetRealXrange(self, figure_config: Dict, meta: CChanPlotMeta) -> int:
        """解析 figure 配置中的可见 X 窗口长度。"""
        x_range = figure_config.get("x_range", 0)
        bi_cnt = figure_config.get("x_bi_cnt", 0)
        seg_cnt = figure_config.get("x_seg_cnt", 0)
        x_begin_date = figure_config.get("x_begin_date", 0)
        exclusive = [x_range != 0, bi_cnt != 0, seg_cnt != 0, x_begin_date != 0]
        if sum(bool(flag) for flag in exclusive) > 1:
            raise CChanException(
                "x_range/x_bi_cnt/x_seg_cnt/x_begin_date can not be set at the same time",
                ErrCode.PLOT_ERR,
            )
        if x_range != 0:
            return int(x_range)
        if bi_cnt != 0:
            if len(meta.bi_list) < bi_cnt:
                return 0
            return meta.klu_len - meta.bi_list[-bi_cnt].begin_x
        if seg_cnt != 0:
            if len(meta.seg_list) < seg_cnt:
                return 0
            return meta.klu_len - meta.seg_list[-seg_cnt].begin_x
        if x_begin_date != 0:
            count = 0
            for date_tick in meta.datetick[::-1]:
                if date_tick >= x_begin_date:
                    count += 1
                else:
                    break
            return count
        return 0

    def DrawElement(
        self,
        plot_config: Dict[str, bool],
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        lv: KL_TYPE,
        plot_para: PlotPara,
        ax_macd: Optional[pg.PlotItem],
        x_limits: XLimits,
    ) -> None:
        """按开关调用各 draw_*。"""
        if plot_config.get("plot_kline", False):
            self.draw_klu(meta, ax, x_limits=x_limits, **plot_para.get("kl", {}))
        if plot_config.get("plot_kline_combine", False):
            self.draw_klc(meta, ax, x_limits=x_limits, **plot_para.get("klc", {}))
        if plot_config.get("plot_bi", False):
            self.draw_bi(meta, ax, lv, x_limits=x_limits, **plot_para.get("bi", {}))
        if plot_config.get("plot_seg", False):
            self.draw_seg(meta, ax, lv, x_limits=x_limits, **plot_para.get("seg", {}))
        if plot_config.get("plot_segseg", False):
            self.draw_segseg(meta, ax, x_limits=x_limits, **plot_para.get("segseg", {}))
        if plot_config.get("plot_eigen", False):
            self.draw_eigen(meta, ax, x_limits=x_limits, **plot_para.get("eigen", {}))
        if plot_config.get("plot_segeigen", False):
            self.draw_segeigen(meta, ax, x_limits=x_limits, **plot_para.get("segeigen", {}))
        if plot_config.get("plot_zs", False):
            self.draw_zs(meta, ax, x_limits=x_limits, **plot_para.get("zs", {}))
        if plot_config.get("plot_segzs", False):
            self.draw_segzs(meta, ax, x_limits=x_limits, **plot_para.get("segzs", {}))
        if plot_config.get("plot_macd", False):
            if ax_macd is None:
                raise CChanException("macd axes missing", ErrCode.PLOT_ERR)
            self.draw_macd(meta, ax_macd, x_limits, **plot_para.get("macd", {}))
        if plot_config.get("plot_mean", False):
            self.draw_mean(meta, ax, **plot_para.get("mean", {}))
        if plot_config.get("plot_channel", False):
            self.draw_channel(meta, ax, **plot_para.get("channel", {}))
        if plot_config.get("plot_boll", False):
            self.draw_boll(meta, ax, x_limits=x_limits, **plot_para.get("boll", {}))
        if plot_config.get("plot_bsp", False):
            self.draw_bs_point(meta, ax, x_limits=x_limits, **plot_para.get("bsp", {}))
        if plot_config.get("plot_segbsp", False):
            self.draw_seg_bs_point(meta, ax, x_limits=x_limits, **plot_para.get("seg_bsp", {}))
        if plot_config.get("plot_demark", False):
            self.draw_demark(meta, ax, x_limits=x_limits, **plot_para.get("demark", {}))
        if plot_config.get("plot_marker", False):
            self.draw_marker(meta, ax, x_limits=x_limits, **plot_para.get("marker", {"markers": {}}))
        if plot_config.get("plot_rsi", False):
            self.draw_rsi(meta, ax, x_limits=x_limits, **plot_para.get("rsi", {}))
        if plot_config.get("plot_kdj", False):
            self.draw_kdj(meta, ax, x_limits=x_limits, **plot_para.get("kdj", {}))

    def ShowDrawFuncHelper(self) -> None:
        """打印全部 draw_* 默认参数，便于对照 README。"""
        for name in dir(self):
            if name.startswith("draw_"):
                show_func_helper(getattr(self, name))

    def show(self) -> None:
        """显示窗口并进入 Qt 事件循环。"""
        self.widget.show()
        if self.app is not None:
            self.app.exec_()

    def save2img(self, path: str) -> None:
        """导出当前图为图片文件。"""
        self.widget.show()
        QtWidgets.QApplication.processEvents()
        # grab 比 ImageExporter 更稳；放大后再抓以提高清晰度
        target_w = max(self.widget.width(), 1920)
        scale = target_w / max(self.widget.width(), 1)
        pixmap = self.widget.grab()
        if scale > 1.01:
            pixmap = pixmap.scaled(
                int(pixmap.width() * scale),
                int(pixmap.height() * scale),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        if not pixmap.save(path):
            raise CChanException(f"save image failed: {path}", ErrCode.PLOT_ERR)

    def _x_begin(self, ax: pg.PlotItem, x_limits: Optional[XLimits]) -> float:
        if x_limits is not None:
            return float(x_limits[0])
        return float(ax.viewRange()[0][0])

    def _x_end(self, ax: pg.PlotItem, x_limits: Optional[XLimits]) -> float:
        if x_limits is not None:
            return float(x_limits[1])
        return float(ax.viewRange()[0][1])

    def _add_rect(
        self,
        ax: pg.PlotItem,
        x: float,
        y: float,
        w: float,
        h: float,
        color: ColorLike,
        width: float = 1,
        dashed: bool = False,
        fill: bool = False,
        alpha: float = 0.5,
        z_value: float = 6,
    ) -> QtWidgets.QGraphicsRectItem:
        rect_w = w if w > 0 else 1e-6
        rect_h = h if h > 0 else 1e-6
        c = to_qt_color(color)
        rect = QtWidgets.QGraphicsRectItem(QtCore.QRectF(x, y, rect_w, rect_h))
        rect.setPen(make_pen(c, width=width, dashed=dashed))
        if fill:
            brush = QtGui.QBrush(QtGui.QColor(c.red(), c.green(), c.blue(), int(255 * alpha)))
            rect.setBrush(brush)
        else:
            rect.setBrush(QtGui.QBrush(Qt.BrushStyle.NoBrush))
        rect.setZValue(z_value)
        ax.addItem(rect)
        return rect

    def _add_line(
        self,
        ax: pg.PlotItem,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        color: ColorLike,
        width: float = 1,
        dashed: bool = False,
    ) -> pg.PlotDataItem:
        item = pg.PlotDataItem([x0, x1], [y0, y1], pen=make_pen(color, width=width, dashed=dashed))
        item.setZValue(10)
        ax.addItem(item)
        return item

    def _add_text(
        self,
        ax: pg.PlotItem,
        x: float,
        y: float,
        text: str,
        color: ColorLike,
        fontsize: float = 12,
        anchor: Tuple[float, float] = (0.5, 0.5),
    ) -> pg.TextItem:
        ti = pg.TextItem(text=str(text), color=to_qt_color(color), anchor=anchor)
        font = QtGui.QFont()
        font.setPointSize(max(1, int(fontsize * 0.75)))
        ti.setFont(font)
        ti.setPos(x, y)
        ti.setZValue(20)
        ax.addItem(ti)
        return ti

    def _add_arrow(
        self,
        ax: pg.PlotItem,
        x: float,
        y_tip: float,
        y_tail: float,
        color: ColorLike,
    ) -> None:
        """从 y_tail 指向 y_tip 的竖向箭头（scatter 三角更稳，对齐 matplotlib 观感）。"""
        self._add_line(ax, x, y_tail, x, y_tip, color, width=1.5)
        # pyqtgraph: t1=朝上三角, t=朝下三角
        symbol = "t1" if y_tip > y_tail else "t"
        c = to_qt_color(color)
        scatter = pg.ScatterPlotItem(
            [x],
            [y_tip],
            symbol=symbol,
            size=14,
            brush=pg.mkBrush(c),
            pen=pg.mkPen(c, width=1),
            pxMode=True,
        )
        scatter.setZValue(15)
        ax.addItem(scatter)

    def _add_highlight(
        self,
        ax: pg.PlotItem,
        x0: float,
        x1: float,
        color: ColorLike,
        alpha: float = 0.1,
    ) -> None:
        c = to_qt_color(color)
        region = pg.LinearRegionItem(
            values=[x0, x1],
            movable=False,
            brush=pg.mkBrush(c.red(), c.green(), c.blue(), int(255 * alpha)),
        )
        region.setZValue(-10)
        ax.addItem(region)

    def draw_klu(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        width: float = 0.4,
        rugd: bool = True,
        plot_mode: str = "kl",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = self._x_begin(ax, x_limits)
        if plot_mode == "kl":
            data: List[CandleBar] = []
            for kl in meta.klu_iter():
                if kl.idx + width < x_begin:
                    continue
                data.append((float(kl.idx), kl.open, kl.high, kl.low, kl.close))
            if data:
                candle = CandlestickItem(data, width=width, rugd=rugd)
                candle.setZValue(0)
                ax.addItem(candle)
            return

        xs: List[float] = []
        ys: List[float] = []
        for kl in meta.klu_iter():
            if kl.idx + width < x_begin:
                continue
            if plot_mode == "close":
                ys.append(kl.close)
            elif plot_mode == "high":
                ys.append(kl.high)
            elif plot_mode == "low":
                ys.append(kl.low)
            elif plot_mode == "open":
                ys.append(kl.open)
            else:
                raise CChanException(
                    f"unknow plot mode={plot_mode}, must be one of kl/close/open/high/low",
                    ErrCode.PLOT_ERR,
                )
            xs.append(float(kl.idx))
        if xs:
            ax.plot(xs, ys, pen=make_pen("b"))

    def draw_klc(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        width: float = 0.4,
        plot_single_kl: bool = True,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        color_type = {
            FX_TYPE.TOP: "red",
            FX_TYPE.BOTTOM: "blue",
            KLINE_DIR.UP: "green",
            KLINE_DIR.DOWN: "green",
        }
        x_begin = self._x_begin(ax, x_limits)
        for klc_meta in meta.klc_list:
            if klc_meta.klu_list[-1].idx + width < x_begin:
                continue
            if klc_meta.end_idx == klc_meta.begin_idx and not plot_single_kl:
                continue
            self._add_rect(
                ax,
                klc_meta.begin_idx - width,
                klc_meta.low,
                klc_meta.end_idx - klc_meta.begin_idx + width * 2,
                klc_meta.high - klc_meta.low,
                color_type[klc_meta.type],
                width=1,
                fill=False,
                z_value=3,
            )

    def draw_bi(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        lv: KL_TYPE,
        color: ColorLike = "black",
        show_num: bool = False,
        num_fontsize: float = 15,
        num_color: ColorLike = "red",
        sub_lv_cnt: Optional[int] = None,
        facecolor: ColorLike = "green",
        alpha: float = 0.1,
        disp_end: bool = False,
        end_color: ColorLike = "black",
        end_fontsize: float = 10,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = self._x_begin(ax, x_limits)
        x_end = int(self._x_end(ax, x_limits))
        for bi_idx, bi in enumerate(meta.bi_list):
            if bi.end_x < x_begin:
                continue
            self._add_line(ax, bi.begin_x, bi.begin_y, bi.end_x, bi.end_y, color, dashed=not bi.is_sure)
            if show_num and bi.begin_x >= x_begin:
                self._add_text(
                    ax,
                    (bi.begin_x + bi.end_x) / 2,
                    (bi.begin_y + bi.end_y) / 2,
                    f"{bi.idx}",
                    num_color,
                    fontsize=num_fontsize,
                )
            if disp_end:
                _bi_text(self, bi_idx, ax, bi, end_fontsize, end_color)
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            if sub_lv_cnt >= len(meta.bi_list):
                return
            begin_idx = meta.bi_list[-sub_lv_cnt].begin_x
            self._add_highlight(ax, begin_idx, x_end + 1, facecolor, alpha=alpha)

    def draw_seg(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        lv: KL_TYPE,
        width: float = 5,
        color: ColorLike = "g",
        sub_lv_cnt: Optional[int] = None,
        facecolor: ColorLike = "green",
        alpha: float = 0.1,
        disp_end: bool = False,
        end_color: ColorLike = "g",
        end_fontsize: float = 13,
        plot_trendline: bool = False,
        trendline_color: ColorLike = "r",
        trendline_width: float = 3,
        show_num: bool = False,
        num_fontsize: float = 25,
        num_color: ColorLike = "blue",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = self._x_begin(ax, x_limits)
        x_end = int(self._x_end(ax, x_limits))
        for seg_idx, seg_meta in enumerate(meta.seg_list):
            if seg_meta.end_x < x_begin:
                continue
            self._add_line(
                ax,
                seg_meta.begin_x,
                seg_meta.begin_y,
                seg_meta.end_x,
                seg_meta.end_y,
                color,
                width=width,
                dashed=not seg_meta.is_sure,
            )
            if disp_end:
                _bi_text(self, seg_idx, ax, seg_meta, end_fontsize, end_color)
            if plot_trendline:
                if seg_meta.tl.get("support"):
                    tl_meta = seg_meta.format_tl(seg_meta.tl["support"])
                    self._add_line(
                        ax, tl_meta[0], tl_meta[1], tl_meta[2], tl_meta[3],
                        trendline_color, width=trendline_width,
                    )
                if seg_meta.tl.get("resistance"):
                    tl_meta = seg_meta.format_tl(seg_meta.tl["resistance"])
                    self._add_line(
                        ax, tl_meta[0], tl_meta[1], tl_meta[2], tl_meta[3],
                        trendline_color, width=trendline_width,
                    )
            if show_num and seg_meta.begin_x >= x_begin:
                self._add_text(
                    ax,
                    (seg_meta.begin_x + seg_meta.end_x) / 2,
                    (seg_meta.begin_y + seg_meta.end_y) / 2,
                    f"{seg_meta.idx}",
                    num_color,
                    fontsize=num_fontsize,
                )
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            if sub_lv_cnt >= len(meta.seg_list):
                return
            begin_idx = meta.seg_list[-sub_lv_cnt].begin_x
            self._add_highlight(ax, begin_idx, x_end + 1, facecolor, alpha=alpha)

    def draw_segseg(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        width: float = 7,
        color: ColorLike = "brown",
        disp_end: bool = False,
        end_color: ColorLike = "brown",
        end_fontsize: float = 15,
        show_num: bool = False,
        num_fontsize: float = 30,
        num_color: ColorLike = "blue",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = self._x_begin(ax, x_limits)
        for seg_idx, seg_meta in enumerate(meta.segseg_list):
            if seg_meta.end_x < x_begin:
                continue
            self._add_line(
                ax,
                seg_meta.begin_x,
                seg_meta.begin_y,
                seg_meta.end_x,
                seg_meta.end_y,
                color,
                width=width,
                dashed=not seg_meta.is_sure,
            )
            if disp_end:
                if seg_idx == 0:
                    anchor = (0.5, 1.0) if seg_meta.dir == BI_DIR.UP else (0.5, 0.0)
                    self._add_text(
                        ax, seg_meta.begin_x, seg_meta.begin_y,
                        f"{seg_meta.begin_y:.2f}", end_color,
                        fontsize=end_fontsize, anchor=anchor,
                    )
                anchor = (0.5, 1.0) if seg_meta.dir == BI_DIR.DOWN else (0.5, 0.0)
                self._add_text(
                    ax, seg_meta.end_x, seg_meta.end_y,
                    f"{seg_meta.end_y:.2f}", end_color,
                    fontsize=end_fontsize, anchor=anchor,
                )
            if show_num and seg_meta.begin_x >= x_begin:
                self._add_text(
                    ax,
                    (seg_meta.begin_x + seg_meta.end_x) / 2,
                    (seg_meta.begin_y + seg_meta.end_y) / 2,
                    f"{seg_meta.idx}",
                    num_color,
                    fontsize=num_fontsize,
                )

    def plot_single_eigen(
        self,
        eigenfx_meta: CEigenFX_meta,
        ax: pg.PlotItem,
        color_top: ColorLike,
        color_bottom: ColorLike,
        aplha: float,
        only_peak: bool,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = self._x_begin(ax, x_limits)
        color = color_top if eigenfx_meta.fx == FX_TYPE.TOP else color_bottom
        for idx, eigen_meta in enumerate(eigenfx_meta.ele):
            if eigen_meta.begin_x + eigen_meta.w < x_begin:
                continue
            if only_peak and idx != 1:
                continue
            self._add_rect(
                ax, eigen_meta.begin_x, eigen_meta.begin_y, eigen_meta.w, eigen_meta.h,
                color, fill=True, alpha=aplha,
            )

    def draw_eigen(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        color_top: ColorLike = "r",
        color_bottom: ColorLike = "b",
        aplha: float = 0.5,
        only_peak: bool = False,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        for eigenfx_meta in meta.eigenfx_lst:
            self.plot_single_eigen(eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak, x_limits)

    def draw_segeigen(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        color_top: ColorLike = "r",
        color_bottom: ColorLike = "b",
        aplha: float = 0.5,
        only_peak: bool = False,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        for eigenfx_meta in meta.seg_eigenfx_lst:
            self.plot_single_eigen(eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak, x_limits)

    def draw_zs(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        color: ColorLike = "orange",
        linewidth: float = 2,
        sub_linewidth: float = 0.5,
        show_text: bool = False,
        fontsize: float = 14,
        text_color: ColorLike = "orange",
        draw_one_bi_zs: bool = False,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        linewidth = max(linewidth, 2)
        x_begin = self._x_begin(ax, x_limits)
        for zs_meta in meta.zs_lst:
            if not draw_one_bi_zs and zs_meta.is_onebi_zs:
                continue
            if zs_meta.begin + zs_meta.w < x_begin:
                continue
            self._add_rect(
                ax, zs_meta.begin, zs_meta.low, zs_meta.w, zs_meta.h, color,
                width=linewidth, dashed=not zs_meta.is_sure,
            )
            for sub_zs_meta in zs_meta.sub_zs_lst:
                self._add_rect(
                    ax, sub_zs_meta.begin, sub_zs_meta.low, sub_zs_meta.w, sub_zs_meta.h,
                    color, width=max(sub_linewidth, 0.5), dashed=not zs_meta.is_sure,
                )
            if show_text:
                _add_zs_text(self, ax, zs_meta, fontsize, text_color)
                for sub_zs_meta in zs_meta.sub_zs_lst:
                    _add_zs_text(self, ax, sub_zs_meta, fontsize, text_color)

    def draw_segzs(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        color: ColorLike = "red",
        linewidth: float = 10,
        sub_linewidth: float = 4,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        linewidth = max(linewidth, 2)
        x_begin = self._x_begin(ax, x_limits)
        for zs_meta in meta.segzs_lst:
            if zs_meta.begin + zs_meta.w < x_begin:
                continue
            self._add_rect(
                ax, zs_meta.begin, zs_meta.low, zs_meta.w, zs_meta.h, color,
                width=linewidth, dashed=not zs_meta.is_sure,
            )
            for sub_zs_meta in zs_meta.sub_zs_lst:
                self._add_rect(
                    ax, sub_zs_meta.begin, sub_zs_meta.low, sub_zs_meta.w, sub_zs_meta.h,
                    color, width=sub_linewidth, dashed=not zs_meta.is_sure,
                )

    def draw_macd(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        x_limits: XLimits,
        width: float = 0.4,
    ) -> None:
        macd_lst = [klu.macd for klu in meta.klu_iter()]
        if not macd_lst or macd_lst[0] is None:
            raise CChanException("you can't draw macd until you delete macd_metric=False", ErrCode.PLOT_ERR)
        x_begin = int(x_limits[0])
        x_idx = np.arange(x_begin, len(macd_lst))
        dif_line = [macd.DIF for macd in macd_lst[x_begin:]]
        dea_line = [macd.DEA for macd in macd_lst[x_begin:]]
        macd_bar = [macd.macd for macd in macd_lst[x_begin:]]
        if not macd_bar:
            return
        y_min = min(min(dif_line), min(dea_line), min(macd_bar))
        y_max = max(max(dif_line), max(dea_line), max(macd_bar))
        ax.plot(x_idx, dif_line, pen=make_pen("#FFA500"))
        ax.plot(x_idx, dea_line, pen=make_pen("#0000ff"))
        brushes = [pg.mkBrush("#FF0000" if v >= 0 else "#006400") for v in macd_bar]
        ax.addItem(pg.BarGraphItem(x=x_idx, height=macd_bar, width=width, brushes=brushes))
        ax.setYRange(y_min, y_max, padding=0.05)

    def draw_mean(self, meta: CChanPlotMeta, ax: pg.PlotItem) -> None:
        mean_lst = [klu.trend[TREND_TYPE.MEAN] for klu in meta.klu_iter()]
        if not mean_lst or not mean_lst[0]:
            return
        periods = list(mean_lst[0].keys())
        n = max(10, len(periods))
        for cmap_idx, period in enumerate(periods):
            mean_arr = [mean_dict[period] for mean_dict in mean_lst]
            hue = int(360 * cmap_idx / n)
            color = QtGui.QColor.fromHsv(hue, 255, 230)
            ax.plot(range(len(mean_arr)), mean_arr, pen=make_pen(color), name=f"{period} meanline")
        ax.addLegend()

    def draw_channel(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        T: Optional[int] = None,
        top_color: ColorLike = "r",
        bottom_color: ColorLike = "b",
        linewidth: float = 3,
        linestyle: str = "solid",
    ) -> None:
        max_lst = [klu.trend[TREND_TYPE.MAX] for klu in meta.klu_iter()]
        min_lst = [klu.trend[TREND_TYPE.MIN] for klu in meta.klu_iter()]
        if not max_lst or not max_lst[0]:
            raise CChanException("plot channel requires trend_metrics in CChanConfig", ErrCode.PLOT_ERR)
        config_t_lst = sorted(max_lst[0].keys())
        period = config_t_lst[-1] if T is None else T
        if period not in max_lst[0]:
            raise CChanException(
                f"plot channel of T={period} is not setted in CChanConfig.trend_metrics = {config_t_lst}",
                ErrCode.PLOT_ERR,
            )
        top_array = [_d[period] for _d in max_lst]
        bottom_array = [_d[period] for _d in min_lst]
        dashed = linestyle in ("dashed", "--", "dash")
        ax.plot(
            range(len(top_array)), top_array,
            pen=make_pen(top_color, width=linewidth, dashed=dashed),
            name=f"{period}-TOP-channel",
        )
        ax.plot(
            range(len(bottom_array)), bottom_array,
            pen=make_pen(bottom_color, width=linewidth, dashed=dashed),
            name=f"{period}-BUTTOM-channel",
        )
        ax.addLegend()

    def draw_boll(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        mid_color: ColorLike = "black",
        up_color: ColorLike = "blue",
        down_color: ColorLike = "purple",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = int(self._x_begin(ax, x_limits))
        try:
            ma = [klu.boll.MID for klu in meta.klu_iter()][x_begin:]
            up = [klu.boll.UP for klu in meta.klu_iter()][x_begin:]
            down = [klu.boll.DOWN for klu in meta.klu_iter()][x_begin:]
        except AttributeError as exc:
            raise CChanException(
                "you can't draw boll until you set boll_n in CChanConfig",
                ErrCode.PLOT_ERR,
            ) from exc
        xs = list(range(x_begin, x_begin + len(ma)))
        ax.plot(xs, ma, pen=make_pen(mid_color))
        ax.plot(xs, up, pen=make_pen(up_color))
        ax.plot(xs, down, pen=make_pen(down_color))
        if down:
            self.y_min = min(self.y_min, min(down))
            self.y_max = max(self.y_max, max(up))

    def bsp_common_draw(
        self,
        bsp_list: Iterable[CBS_Point_meta],
        ax: pg.PlotItem,
        buy_color: ColorLike,
        sell_color: ColorLike,
        fontsize: float,
        arrow_l: float,
        arrow_h: float,
        arrow_w: float,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        del arrow_h, arrow_w  # 保留参数以对齐 CPlotDriver 签名
        x_begin = self._x_begin(ax, x_limits)
        y_range = self.y_max - self.y_min
        if y_range <= 0:
            y_range = 1.0
        for bsp in bsp_list:
            if bsp.x < x_begin:
                continue
            color = buy_color if bsp.is_buy else sell_color
            # 买点：箭头从下方指到低点；卖点：从上方指到高点（同 PlotDriver）
            arrow_dir = 1 if bsp.is_buy else -1
            arrow_len = arrow_l * y_range
            text_y = bsp.y - arrow_len * arrow_dir
            # TextItem: anchor y=1 表示文本顶对齐坐标点（卖点文字在上方）
            anchor = (0.5, 1.0) if bsp.is_buy else (0.5, 0.0)
            self._add_arrow(ax, bsp.x, bsp.y, text_y, color)
            self._add_text(ax, bsp.x, text_y, f"{bsp.desc()}", color, fontsize=fontsize, anchor=anchor)
            self.y_min = min(self.y_min, text_y)
            self.y_max = max(self.y_max, text_y)

    def draw_bs_point(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        buy_color: ColorLike = "r",
        sell_color: ColorLike = "g",
        fontsize: float = 15,
        arrow_l: float = 0.15,
        arrow_h: float = 0.2,
        arrow_w: float = 1,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        self.bsp_common_draw(
            meta.bs_point_lst, ax, buy_color, sell_color, fontsize,
            arrow_l, arrow_h, arrow_w, x_limits=x_limits,
        )

    def draw_seg_bs_point(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        buy_color: ColorLike = "r",
        sell_color: ColorLike = "g",
        fontsize: float = 18,
        arrow_l: float = 0.2,
        arrow_h: float = 0.25,
        arrow_w: float = 1.2,
        x_limits: Optional[XLimits] = None,
    ) -> None:
        self.bsp_common_draw(
            meta.seg_bsp_lst, ax, buy_color, sell_color, fontsize,
            arrow_l, arrow_h, arrow_w, x_limits=x_limits,
        )

    def draw_marker(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        markers: Dict[Union[CTime, str], MarkerValue],
        arrow_l: float = 0.15,
        arrow_h_r: float = 0.2,
        arrow_w: float = 1,
        fontsize: float = 14,
        default_color: ColorLike = "b",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        del arrow_h_r, arrow_w
        x_begin = self._x_begin(ax, x_limits)
        x_end = self._x_end(ax, x_limits)
        datetick_dict = {date: idx for idx, date in enumerate(meta.datetick)}

        new_marker: Dict[Union[CTime, str], MarkerValue] = {}
        for klu in meta.klu_iter():
            for date, marker in markers.items():
                date_str = date.to_str() if isinstance(date, CTime) else date
                if klu.include_sub_lv_time(date_str) and klu.time.to_str() != date_str:
                    new_marker[klu.time.to_str()] = marker
        new_marker.update(markers)

        kl_dict = dict(enumerate(meta.klu_iter()))
        y_range = self.y_max - self.y_min
        if y_range <= 0:
            y_range = 1.0
        arrow_len = arrow_l * y_range
        for date, marker in new_marker.items():
            date_key = date.to_str() if isinstance(date, CTime) else date
            if date_key not in datetick_dict:
                continue
            x = datetick_dict[date_key]
            if x < x_begin or x > x_end:
                continue
            if len(marker) == 2:
                color: ColorLike = default_color
                marker_content, position = marker
            else:
                marker_content, position, color = marker
            if position not in ("up", "down"):
                raise CChanException(f"invalid marker position={position}", ErrCode.PLOT_ERR)
            direction = -1 if position == "up" else 1
            bench = kl_dict[x].high if position == "up" else kl_dict[x].low
            text_y = bench - arrow_len * direction
            self._add_arrow(ax, x, bench, text_y, color)
            # matplotlib: down=top alignment, up=bottom alignment
            anchor = (0.5, 1.0) if position == "down" else (0.5, 0.0)
            self._add_text(ax, x, text_y, marker_content, color, fontsize=fontsize, anchor=anchor)

    def draw_demark_begin_line(
        self,
        ax: pg.PlotItem,
        begin_line_color: Optional[ColorLike],
        plot_begin_set: set[int],
        linestyle: str,
        demark_idx: T_DEMARK_INDEX,
    ) -> None:
        series = demark_idx["series"]
        if begin_line_color is None or series.TDST_peak is None or id(series) in plot_begin_set:
            return
        if series.countdown is not None:
            end_idx = series.countdown.kl_list[-1].idx
        else:
            end_idx = series.kl_list[-1].idx
        start_idx = series.kl_list[CDemarkEngine.SETUP_BIAS].idx
        peak = series.TDST_peak
        self._add_line(
            ax, start_idx, peak, end_idx, peak, begin_line_color,
            dashed=linestyle in ("dashed", "--", "dash"),
        )
        plot_begin_set.add(id(series))

    def _ensure_twin_vb(self, ax: pg.PlotItem) -> pg.ViewBox:
        vb = pg.ViewBox()
        scene = ax.scene()
        if scene is None:
            raise CChanException("plot item has no scene", ErrCode.PLOT_ERR)
        scene.addItem(vb)
        ax.getAxis("right").linkToView(vb)
        ax.showAxis("right")
        vb.setXLink(ax)

        def update_views() -> None:
            vb.setGeometry(ax.vb.sceneBoundingRect())
            vb.linkedViewChanged(ax.vb, vb.XAxis)

        update_views()
        ax.vb.sigResized.connect(update_views)
        self._twin_views.append(vb)
        return vb

    def draw_rsi(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        color: ColorLike = "b",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        data = [klu.rsi for klu in meta.klu_iter()]
        x_begin = int(self._x_begin(ax, x_limits))
        x_end = int(self._x_end(ax, x_limits))
        xs = list(range(x_begin, x_end))
        ys = data[x_begin:x_end]
        if not xs:
            return
        twin = self._ensure_twin_vb(ax)
        twin.addItem(pg.PlotCurveItem(xs, ys, pen=make_pen(color)))
        if ys:
            twin.setYRange(min(ys), max(ys), padding=0.1)

    def draw_kdj(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        k_color: ColorLike = "orange",
        d_color: ColorLike = "blue",
        j_color: ColorLike = "pink",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        kdj = [klu.kdj for klu in meta.klu_iter()]
        x_begin = int(self._x_begin(ax, x_limits))
        x_end = int(self._x_end(ax, x_limits))
        xs = list(range(x_begin, x_end))
        if not xs:
            return
        twin = self._ensure_twin_vb(ax)
        k_vals = [item.k for item in kdj][x_begin:x_end]
        d_vals = [item.d for item in kdj][x_begin:x_end]
        j_vals = [item.j for item in kdj][x_begin:x_end]
        twin.addItem(pg.PlotCurveItem(xs, k_vals, pen=make_pen(k_color), name="K"))
        twin.addItem(pg.PlotCurveItem(xs, d_vals, pen=make_pen(d_color), name="D"))
        twin.addItem(pg.PlotCurveItem(xs, j_vals, pen=make_pen(j_color), name="J"))
        all_y = k_vals + d_vals + j_vals
        if all_y:
            twin.setYRange(min(all_y), max(all_y), padding=0.1)

    def draw_demark(
        self,
        meta: CChanPlotMeta,
        ax: pg.PlotItem,
        setup_color: ColorLike = "b",
        countdown_color: ColorLike = "r",
        fontsize: float = 12,
        min_setup: int = 9,
        max_countdown_background: ColorLike = "yellow",
        begin_line_color: Optional[ColorLike] = "purple",
        begin_line_style: str = "dashed",
        x_limits: Optional[XLimits] = None,
    ) -> None:
        x_begin = self._x_begin(ax, x_limits)
        text_height = (self.y_max - self.y_min) * 0.015 if self.y_max > self.y_min else 0.01
        for klu in meta.klu_iter():
            if klu.idx < x_begin:
                continue
            under_bias = 0.0
            upper_bias = 0.0
            plot_begin_set: set[int] = set()
            for demark_idx in klu.demark.get_setup():
                if demark_idx["series"].idx < min_setup or not demark_idx["series"].setup_finished:
                    continue
                self.draw_demark_begin_line(
                    ax, begin_line_color, plot_begin_set, begin_line_style, demark_idx,
                )
                if demark_idx["dir"] == BI_DIR.DOWN:
                    y = klu.low - under_bias
                    anchor = (0.5, 1.0)
                    under_bias += text_height
                else:
                    y = klu.high + upper_bias
                    anchor = (0.5, 0.0)
                    upper_bias += text_height
                self._add_text(
                    ax, klu.idx, y, str(demark_idx["idx"]), setup_color,
                    fontsize=fontsize, anchor=anchor,
                )
            for demark_idx in klu.demark.get_countdown():
                box_bias = 0.5 * text_height if demark_idx["idx"] == CDemarkEngine.MAX_COUNTDOWN else 0.0
                if demark_idx["dir"] == BI_DIR.DOWN:
                    y = klu.low - under_bias - box_bias
                    anchor = (0.5, 1.0)
                else:
                    y = klu.high + upper_bias + box_bias
                    anchor = (0.5, 0.0)
                ti = self._add_text(
                    ax, klu.idx, y, str(demark_idx["idx"]), countdown_color,
                    fontsize=fontsize, anchor=anchor,
                )
                if demark_idx["idx"] == CDemarkEngine.MAX_COUNTDOWN:
                    ti.fill = pg.mkBrush(to_qt_color(max_countdown_background))
                    ti.border = pg.mkPen(to_qt_color(max_countdown_background))
                if demark_idx["dir"] == BI_DIR.DOWN:
                    under_bias += text_height
                else:
                    upper_bias += text_height


def _bi_text(
    driver: CQtPlotDriver,
    bi_idx: int,
    ax: pg.PlotItem,
    bi: Union[CBi_meta, CSeg_meta],
    end_fontsize: float,
    end_color: ColorLike,
) -> None:
    if bi_idx == 0:
        anchor = (0.5, 1.0) if bi.dir == BI_DIR.UP else (0.5, 0.0)
        driver._add_text(
            ax, bi.begin_x, bi.begin_y, f"{bi.begin_y:.5f}", end_color,
            fontsize=end_fontsize, anchor=anchor,
        )
    anchor = (0.5, 1.0) if bi.dir == BI_DIR.DOWN else (0.5, 0.0)
    driver._add_text(
        ax, bi.end_x, bi.end_y, f"{bi.end_y:.5f}", end_color,
        fontsize=end_fontsize, anchor=anchor,
    )


def _add_zs_text(
    driver: CQtPlotDriver,
    ax: pg.PlotItem,
    zs_meta: CZS_meta,
    fontsize: float,
    text_color: ColorLike,
) -> None:
    driver._add_text(
        ax, zs_meta.begin, zs_meta.low, f"{zs_meta.low:.2f}", text_color,
        fontsize=fontsize, anchor=(0.5, 1.0),
    )
    driver._add_text(
        ax, zs_meta.begin + zs_meta.w, zs_meta.low + zs_meta.h,
        f"{zs_meta.low + zs_meta.h:.2f}", text_color,
        fontsize=fontsize, anchor=(0.5, 0.0),
    )
