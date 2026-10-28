# -*- coding: utf-8 -*-
"""
绘图驱动模块 - 使用 matplotlib 绘制缠论分析图表

Java 开发者注意：
- matplotlib 是 Python 的绘图库，类似于 Java 的 JFreeChart 或 JavaFX Chart
- Python 的 isinstance(obj, type) 类似于 Java 的 obj instanceof type
- Python 的 enumerate(iterable) 返回 (索引, 值) 元组
  Java 对比：Java 没有直接对应，需要手动维护计数器
- Python 的 f-string f"{var}" 类似于 Java 的 String.format("%s", var)
- Python 的 **kwargs 是关键字参数解包，允许传递任意命名参数
  Java 对比：Java 没有直接对应，通常用 Builder 模式或 Map 传参
- Python 的 dict.get(key, default) 类似于 Java 的 map.getOrDefault(key, default)
- Python 的 assert 断言，类似于 Java 的 assert 关键字
- Python 的 zip(a, b) 将两个列表配对，类似于同时遍历两个列表
  Java 对比：Java 没有内置 zip，通常用循环索引或第三方库
- Python 的 eval() 执行字符串表达式，类似于 Java 的 ScriptEngine
- Python 的 plt.cm.get_cmap('hsv', N) 获取颜色映射
  Java 对比：类似于 Java 的 Color.getHSBColor() 系列
"""

import inspect
from typing import Dict, List, Literal, Optional, Tuple, Union

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from Chan import CChan
from Common.CEnum import BI_DIR, FX_TYPE, KL_TYPE, KLINE_DIR, TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Math.Demark import T_DEMARK_INDEX, CDemarkEngine

from .PlotMeta import CBi_meta, CChanPlotMeta, CZS_meta


def reformat_plot_config(plot_config: Dict[str, bool]):
    """
    兼容不填写 `plot_` 前缀的情况

    如果配置项没有 `plot_` 前缀，自动添加。
    例如：'bi' → 'plot_bi', 'seg' → 'plot_seg'

    参数:
        plot_config: 原始配置字典

    返回:
        格式化后的配置字典

    Python 特性：字典推导式 {k: v for k, v in dict.items()}
    Java 对比：stream().collect(Collectors.toMap(...))
    """

    def _format(s):
        """内部函数：添加 plot_ 前缀"""
        return s if s.startswith("plot_") else f"plot_{s}"

    return {_format(k): v for k, v in plot_config.items()}


def parse_single_lv_plot_config(plot_config: Union[str, dict, list]) -> Dict[str, bool]:
    """
    解析单个级别的绘图配置

    支持多种输入格式：
    - dict: {"plot_bi": True, "plot_seg": False}
    - str: "bi,seg,zs"（逗号分隔，默认开启）
    - list: ["bi", "seg", "zs"]

    参数:
        plot_config: 原始配置

    返回:
        格式化后的 {plot_xxx: bool} 字典
    """
    if isinstance(plot_config, dict):
        return reformat_plot_config(plot_config)
    elif isinstance(plot_config, str):
        # 字符串转字典：每个元素默认 True
        return reformat_plot_config(dict([(k.strip().lower(), True) for k in plot_config.split(",")]))
    elif isinstance(plot_config, list):
        return reformat_plot_config(dict([(k.strip().lower(), True) for k in plot_config]))
    else:
        raise CChanException("plot_config only support list/str/dict", ErrCode.PLOT_ERR)


def parse_plot_config(plot_config: Union[str, dict, list], lv_list: List[KL_TYPE]) -> Dict[KL_TYPE, Dict[str, bool]]:
    """
    解析多级别绘图配置

    支持：
    - 单层字典 → 所有级别使用相同配置
    - key为KL_TYPE的字典 → 每个级别使用不同配置
    - 字符串/列表 → 所有级别使用相同配置

    参数:
        plot_config: 原始配置
        lv_list: 级别列表

    返回:
        {KL_TYPE: {plot_xxx: bool}} 配置字典
    """
    if isinstance(plot_config, dict):
        if all(isinstance(_key, str) for _key in plot_config.keys()):
            # 单层字典：所有级别使用相同配置
            return {lv: parse_single_lv_plot_config(plot_config) for lv in lv_list}
        elif all(isinstance(_key, KL_TYPE) for _key in plot_config.keys()):
            # key为KL_TYPE：每个级别独立配置
            for lv in lv_list:
                assert lv in plot_config
            return {lv: parse_single_lv_plot_config(plot_config[lv]) for lv in lv_list}
        else:
            raise CChanException("plot_config if is dict, key must be str/KL_TYPE", ErrCode.PLOT_ERR)
    # 非字典类型：所有级别使用相同配置
    return {lv: parse_single_lv_plot_config(plot_config) for lv in lv_list}


def set_x_tick(ax, x_limits, tick, x_tick_num: int):
    """
    设置 X 轴刻度

    参数:
        ax: matplotlib Axes 对象
        x_limits: [x_min, x_max] 范围
        tick: 刻度标签列表
        x_tick_num: 显示的刻度数量
    """
    assert x_tick_num > 1
    ax.set_xlim(x_limits[0], x_limits[1] + 1)
    ax.set_xticks(range(x_limits[0], x_limits[1], max([1, int((x_limits[1] - x_limits[0]) / float(x_tick_num))])))
    ax.set_xticklabels([tick[i] for i in ax.get_xticks()], rotation=20)


def cal_y_range(meta: CChanPlotMeta, ax):
    """
    计算 Y 轴范围

    参数:
        meta: 绘图元数据
        ax: matplotlib Axes 对象

    返回:
        (y_min, y_max) Y 轴范围

    遍历所有可见的合并K线，找到最高价和最低价。
    """
    x_begin = ax.get_xlim()[0]
    y_min = float("inf")
    y_max = float("-inf")
    for klc_meta in meta.klc_list:
        if klc_meta.klu_list[-1].idx < x_begin:
            continue  # 不绘制范围外的
        if klc_meta.high > y_max:
            y_max = klc_meta.high
        if klc_meta.low < y_min:
            y_min = klc_meta.low
    return (y_min, y_max)


def create_figure(plot_macd: Dict[KL_TYPE, bool], figure_config, lv_lst: List[KL_TYPE]) -> Tuple[Figure, Dict[KL_TYPE, List[Axes]]]:
    """
    创建 matplotlib 图表

    参数:
        plot_macd: {级别: 是否显示MACD}
        figure_config: 图表配置（宽、高、MACD高度比例）
        lv_lst: 级别列表

    返回:
        (Figure, {级别: [Axes列表]})

    布局逻辑：
    - 每个级别一个子图行
    - 如果显示MACD，该级别使用两个子图（K线图 + MACD图）
    - MACD 子图高度 = K线图高度 * macd_h_ration

    多级别垂直排列，从上到下依次是高级别到低级别。
    """
    default_w, default_h = 24, 10
    macd_h_ration = figure_config.get('macd_h', 0.3)
    w = figure_config.get('w', default_w)
    h = figure_config.get('h', default_h)

    total_h = 0
    gridspec_kw = []
    sub_pic_cnt = 0

    # 计算总高度和子图数量
    for lv in lv_lst:
        if plot_macd[lv]:
            total_h += h * (1 + macd_h_ration)  # K线图 + MACD图
            gridspec_kw.extend((1, macd_h_ration))
            sub_pic_cnt += 2
        else:
            total_h += h
            gridspec_kw.append(1)
            sub_pic_cnt += 1

    # 创建子图
    figure, axes = plt.subplots(
        sub_pic_cnt,
        1,
        figsize=(w, total_h),
        gridspec_kw={'height_ratios': gridspec_kw}
    )

    # 处理只有一个子图的情况（plt.subplots 返回单个 Axes 而非列表）
    try:
        axes[0]
    except Exception:  # 只有一个级别，且不需要画macd
        axes = [axes]

    # 分配子图到各级别
    axes_dict: Dict[KL_TYPE, List[Axes]] = {}
    idx = 0
    for lv in lv_lst:
        if plot_macd[lv]:
            axes_dict[lv] = axes[idx: idx + 2]  # type: ignore
            idx += 2
        else:
            axes_dict[lv] = [axes[idx]]  # type: ignore
            idx += 1
    assert idx == len(axes)
    return figure, axes_dict


def cal_x_limit(meta: CChanPlotMeta, x_range):
    """
    计算 X 轴范围

    参数:
        meta: 绘图元数据
        x_range: 显示范围（K线数量）

    返回:
        [x_min, x_max] X 轴范围

    如果 x_range 为 0，显示全部范围。
    """
    X_LEN = meta.klu_len
    return [X_LEN - x_range, X_LEN - 1] if x_range and X_LEN > x_range else [0, X_LEN - 1]


def set_grid(ax, config):
    """
    设置网格线

    参数:
        ax: matplotlib Axes 对象
        config: 网格配置（"x", "y", "xy", None）
    """
    if config is None:
        return
    if config == "xy":
        ax.grid(True)
        return
    if config in ("x", "y"):
        ax.grid(True, axis=config)
        return
    raise CChanException(f"unsupport grid config={config}", ErrCode.PLOT_ERR)


def GetPlotMeta(chan: CChan, figure_config) -> List[CChanPlotMeta]:
    """
    获取所有级别的绘图元数据

    参数:
        chan: CChan 对象
        figure_config: 图表配置

    返回:
        CChanPlotMeta 列表

    如果 only_top_lv=True，只返回最高级别。
    """
    plot_metas = [CChanPlotMeta(chan[kl_type]) for kl_type in chan.lv_list]
    if figure_config.get("only_top_lv", False):
        plot_metas = [plot_metas[0]]
    return plot_metas


class CPlotDriver:
    """
    绘图驱动 - 使用 matplotlib 绘制缠论分析结果

    支持绘制：
    - K线（阴阳烛）
    - 合并K线
    - 笔（确定/虚拟）
    - 线段（确定/虚拟）
    - 特征序列
    - 中枢（笔中枢/线段中枢）
    - MACD 指标
    - 均线
    - 趋势通道
    - 布林带
    - 买卖点
    - Demark 序列
    - RSI/KDJ 指标
    - 自定义标记

    参数:
        chan: CChan 对象（已完成分析）
        plot_config: 绘图配置，控制显示哪些元素
        plot_para: 绘图参数，控制颜色、线宽等样式

    使用示例:
        chan = CChan("sh.600000")
        CPlotDriver(chan, plot_config="bi,seg,zs,macd")
    """

    def __init__(self, chan: CChan, plot_config: Union[str, dict, list] = '', plot_para=None):
        if plot_para is None:
            plot_para = {}
        figure_config: dict = plot_para.get('figure', {})

        # 解析绘图配置
        plot_config = parse_plot_config(plot_config, chan.lv_list)
        plot_metas = GetPlotMeta(chan, figure_config)
        self.lv_lst = chan.lv_list[:len(plot_metas)]

        # 计算 X 轴范围
        x_range = self.GetRealXrange(figure_config, plot_metas[0])

        # 确定哪些级别需要绘制 MACD
        plot_macd: Dict[KL_TYPE, bool] = {
            kl_type: conf.get("plot_macd", False)
            for kl_type, conf in plot_config.items()
        }

        # 创建图表
        self.figure, axes = create_figure(plot_macd, figure_config, self.lv_lst)
        self.figure.patch.set_facecolor('black')

        # 多级别联动相关变量
        sseg_begin = 0
        slv_seg_cnt = plot_para.get('seg', {}).get('sub_lv_cnt', None)
        sbi_begin = 0
        slv_bi_cnt = plot_para.get('bi', {}).get('sub_lv_cnt', None)
        srange_begin = 0
        assert slv_seg_cnt is None or slv_bi_cnt is None, "you can set at most one of seg_sub_lv_cnt/bi_sub_lv_cnt"

        # 为每个级别绘制图表
        for meta, lv in zip(plot_metas, self.lv_lst):  # type: ignore
            ax = axes[lv][0]  # K线图主坐标轴
            ax_macd = None if len(axes[lv]) == 1 else axes[lv][1]  # MACD 坐标轴（可选）

            # 设置网格、标题
            set_grid(ax, figure_config.get("grid", "xy"))
            ax.set_title(f"{chan.code}/{lv.name.split('K_')[1]}", fontsize=16, loc='left', color='r')

            # 计算 X 轴范围（多级别联动）
            x_limits = cal_x_limit(meta, x_range)
            if lv != self.lv_lst[0]:
                # 子级别根据高级别的显示范围调整
                if sseg_begin != 0 or sbi_begin != 0:
                    x_limits[0] = max(sseg_begin, sbi_begin)
                elif srange_begin != 0:
                    x_limits[0] = srange_begin

            # 设置 X 轴刻度
            set_x_tick(ax, x_limits, meta.datetick, figure_config.get('x_tick_num', 10))
            if ax_macd:
                set_x_tick(ax_macd, x_limits, meta.datetick, figure_config.get('x_tick_num', 10))

            # 计算 Y 轴范围（需要先设置 x_tick）
            self.y_min, self.y_max = cal_y_range(meta, ax)

            # 绘制所有元素
            self.DrawElement(plot_config[lv], meta, ax, lv, plot_para, ax_macd, x_limits)

            # 多级别联动：记录子级别的起始位置
            if lv != self.lv_lst[-1]:
                if slv_seg_cnt is not None:
                    sseg_begin = meta.sub_last_kseg_start_idx(slv_seg_cnt)
                if slv_bi_cnt is not None:
                    sbi_begin = meta.sub_last_kbi_start_idx(slv_bi_cnt)
                if x_range != 0:
                    srange_begin = meta.sub_range_start_idx(x_range)

            ax.set_ylim(self.y_min, self.y_max)

    def GetRealXrange(self, figure_config, meta: CChanPlotMeta):
        """
        计算真实的 X 轴显示范围

        支持多种范围指定方式（互斥）：
        - x_range: 显示最后 N 根K线
        - x_bi_cnt: 显示最后 N 个笔
        - x_seg_cnt: 显示最后 N 个线段
        - x_begin_date: 从指定日期开始显示

        参数:
            figure_config: 图表配置
            meta: 绘图元数据

        返回:
            K线数量范围
        """
        x_range = figure_config.get("x_range", 0)
        bi_cnt = figure_config.get("x_bi_cnt", 0)
        seg_cnt = figure_config.get("x_seg_cnt", 0)
        x_begin_date = figure_config.get("x_begin_date", 0)

        if x_range != 0:
            assert bi_cnt == 0 and seg_cnt == 0 and x_begin_date == 0
            return x_range

        if bi_cnt != 0:
            assert x_range == 0 and seg_cnt == 0 and x_begin_date == 0
            X_LEN = meta.klu_len
            if len(meta.bi_list) < bi_cnt:
                return 0
            x_range = X_LEN - meta.bi_list[-bi_cnt].begin_x
            return x_range

        if seg_cnt != 0:
            assert x_range == 0 and bi_cnt == 0 and x_begin_date == 0
            X_LEN = meta.klu_len
            if len(meta.seg_list) < seg_cnt:
                return 0
            x_range = X_LEN - meta.seg_list[-seg_cnt].begin_x
            return x_range

        if x_begin_date != 0:
            assert x_range == 0 and bi_cnt == 0 and seg_cnt == 0
            x_range = 0
            for date_tick in meta.datetick[::-1]:  # 从后往前数
                if date_tick >= x_begin_date:
                    x_range += 1
                else:
                    break
            return x_range

        return x_range

    def DrawElement(self, plot_config: Dict[str, bool], meta: CChanPlotMeta, ax: Axes, lv, plot_para, ax_macd: Optional[Axes], x_limits):
        """
        根据配置绘制所有元素

        参数:
            plot_config: 绘图配置字典
            meta: 绘图元数据
            ax: 主坐标轴
            lv: 当前级别
            plot_para: 绘图参数
            ax_macd: MACD 坐标轴（可选）
            x_limits: X 轴范围

        当前为开发占位阶段：主图和副图均使用黑色背景占位显示。
        后续根据开发再进行调整。
        """
        # === 主图（K线图）黑色背景占位 ===
        ax.set_facecolor('black')

        # === 副图（MACD指标图）黑色背景占位 ===
        if ax_macd is not None:
            ax_macd.set_facecolor('black')

    def ShowDrawFuncHelper(self):
        """
        显示所有绘图函数的参数和默认值

        用于写 README 时生成文档。
        遍历所有 draw_ 开头的方法，打印其签名和默认参数。

        Python 特性：eval() 动态获取方法对象
        - eval(f'self.{func}') 将字符串转为方法引用
        Java 对比：Java 需要使用 Method.invoke() 反射
        """
        for func in dir(self):
            if not func.startswith("draw_"):
                continue
            show_func_helper(eval(f'self.{func}'))

    def save2img(self, path):
        """
        保存图表为图片

        参数:
            path: 保存路径（支持 .png, .jpg, .pdf 等格式）
        """
        plt.savefig(path, bbox_inches='tight')

    def draw_klu(self, meta: CChanPlotMeta, ax: Axes, width=0.4, rugd=True, plot_mode="kl"):
        """
        绘制原始K线（阴阳烛）

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            width: K线宽度
            rugd: 阳线颜色（True=红涨绿跌, False=绿涨红跌）
            plot_mode: 绘制模式
              - "kl": 阴阳烛（默认）
              - "close": 收盘价连线
              - "high": 最高价连线
              - "low": 最低价连线
              - "open": 开盘价连线

        使用 matplotlib.patches.Rectangle 绘制K线实体，
        使用 ax.plot 绘制上下影线。
        """
        # rugd: red up green down
        up_color = 'r' if rugd else 'g'
        down_color = 'g' if rugd else 'r'

        x_begin = ax.get_xlim()[0]
        _x, _y = [], []
        for kl in meta.klu_iter():
            i = kl.idx
            if i + width < x_begin:
                continue  # 不绘制范围外的

            if plot_mode == "kl":
                # 绘制K线：实体 + 上下影线
                if kl.close > kl.open:
                    # 阳线：空心矩形 + 上下影线
                    ax.add_patch(
                        Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, fill=False, color=up_color))
                    ax.plot([i, i], [kl.low, kl.open], up_color)      # 下影线
                    ax.plot([i, i], [kl.close, kl.high], up_color)     # 上影线
                else:
                    # 阴线：实心矩形
                    ax.add_patch(Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, color=down_color))
                    ax.plot([i, i], [kl.low, kl.high], color=down_color)  # 影线
            elif plot_mode in "close":
                _y.append(kl.close)
                _x.append(i)
            elif plot_mode == "high":
                _y.append(kl.high)
                _x.append(i)
            elif plot_mode == "low":
                _y.append(kl.low)
                _x.append(i)
            elif plot_mode == "open":
                _y.append(kl.low)
                _x.append(i)
            else:
                raise CChanException(f"unknow plot mode={plot_mode}, must be one of kl/close/open/high/low", ErrCode.PLOT_ERR)

        if _x:  # 折线模式
            ax.plot(_x, _y)

    def draw_klc(self, meta: CChanPlotMeta, ax: Axes, width=0.4, plot_single_kl=True):
        """
        绘制合并K线

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            width: 矩形宽度
            plot_single_kl: 是否绘制只有一根原始K线的合并K线

        合并K线用矩形框绘制，颜色区分类型：
        - 红色：顶分型
        - 蓝色：底分型
        - 绿色：普通K线

        缠论知识 - 合并K线可视化：
        合并K线的宽度 = 原始K线数量（多根K线合并后形成的矩形更宽）
        """
        color_type = {FX_TYPE.TOP: 'red', FX_TYPE.BOTTOM: 'blue', KLINE_DIR.UP: 'green', KLINE_DIR.DOWN: 'green'}
        x_begin = ax.get_xlim()[0]

        for klc_meta in meta.klc_list:
            if klc_meta.klu_list[-1].idx + width < x_begin:
                continue  # 不绘制范围外的
            if klc_meta.end_idx == klc_meta.begin_idx and not plot_single_kl:
                continue  # 单根K线且不绘制单根
            ax.add_patch(
                Rectangle(
                    (klc_meta.begin_idx - width, klc_meta.low),
                    klc_meta.end_idx - klc_meta.begin_idx + width * 2,
                    klc_meta.high - klc_meta.low,
                    fill=False,
                    color=color_type[klc_meta.type]))

    def draw_bi(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        lv,
        color='black',
        show_num=False,
        num_fontsize=15,
        num_color="red",
        sub_lv_cnt=None,
        facecolor='green',
        alpha=0.1,
        disp_end=False,
        end_color='black',
        end_fontsize=10,
    ):
        """
        绘制笔

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            lv: 当前级别
            color: 笔的颜色
            show_num: 是否显示笔的编号
            num_fontsize: 编号字体大小
            num_color: 编号颜色
            sub_lv_cnt: 子级别联动（显示最后 N 个笔在子级别的位置）
            facecolor: 子级别联动区域颜色
            alpha: 子级别联动区域透明度
            disp_end: 是否显示端点价格
            end_color: 端点价格颜色
            end_fontsize: 端点价格字体大小

        确定笔用实线，虚拟笔用虚线。
        """
        x_begin = ax.get_xlim()[0]
        for bi_idx, bi in enumerate(meta.bi_list):
            if bi.end_x < x_begin:
                continue
            plot_bi_element(bi, ax, color)  # 绘制笔线
            # 显示笔编号
            if show_num and bi.begin_x >= x_begin:
                ax.text((bi.begin_x + bi.end_x) / 2, (bi.begin_y + bi.end_y) / 2,
                        f'{bi.idx}', fontsize=num_fontsize, color=num_color)
            # 显示端点价格
            if disp_end:
                bi_text(bi_idx, ax, bi, end_fontsize, end_color)

        # 多级别联动：标记子级别对应区域
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            if sub_lv_cnt >= len(meta.bi_list):
                return
            else:
                begin_idx = meta.bi_list[-sub_lv_cnt].begin_x
            y_begin, y_end = ax.get_ylim()
            x_end = int(ax.get_xlim()[1])
            ax.fill_between(range(begin_idx, x_end + 1), y_begin, y_end, facecolor=facecolor, alpha=alpha)

    def draw_seg(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        lv,
        width=5,
        color="g",
        sub_lv_cnt=None,
        facecolor='green',
        alpha=0.1,
        disp_end=False,
        end_color='g',
        end_fontsize=13,
        plot_trendline=False,
        trendline_color='r',
        trendline_width=3,
        show_num=False,
        num_fontsize=25,
        num_color="blue",
    ):
        """
        绘制线段

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            lv: 当前级别
            width: 线宽
            color: 线段颜色
            sub_lv_cnt: 子级别联动
            facecolor: 子级别联动区域颜色
            alpha: 子级别联动区域透明度
            disp_end: 是否显示端点价格
            end_color: 端点价格颜色
            end_fontsize: 端点价格字体大小
            plot_trendline: 是否绘制趋势线（支撑线/阻力线）
            trendline_color: 趋势线颜色
            trendline_width: 趋势线宽度
            show_num: 是否显示编号
            num_fontsize: 编号字体大小
            num_color: 编号颜色

        确定线段用实线，未确定线段用虚线。
        """
        x_begin = ax.get_xlim()[0]

        for seg_idx, seg_meta in enumerate(meta.seg_list):
            if seg_meta.end_x < x_begin:
                continue
            # 确定线段：实线；未确定：虚线
            if seg_meta.is_sure:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y],
                        color=color, linewidth=width)
            else:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y],
                        color=color, linewidth=width, linestyle='dashed')

            if disp_end:
                bi_text(seg_idx, ax, seg_meta, end_fontsize, end_color)

            # 绘制趋势线（支撑线/阻力线）
            if plot_trendline:
                if seg_meta.tl.get('support'):
                    tl_meta = seg_meta.format_tl(seg_meta.tl['support'])
                    ax.plot([tl_meta[0], tl_meta[2]], [tl_meta[1], tl_meta[3]],
                            color=trendline_color, linewidth=trendline_width)
                if seg_meta.tl.get('resistance'):
                    tl_meta = seg_meta.format_tl(seg_meta.tl['resistance'])
                    ax.plot([tl_meta[0], tl_meta[2]], [tl_meta[1], tl_meta[3]],
                            color=trendline_color, linewidth=trendline_width)

            if show_num and seg_meta.begin_x >= x_begin:
                ax.text((seg_meta.begin_x + seg_meta.end_x) / 2, (seg_meta.begin_y + seg_meta.end_y) / 2,
                        f'{seg_meta.idx}', fontsize=num_fontsize, color=num_color)

        # 多级别联动
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            if sub_lv_cnt >= len(meta.seg_list):
                return
            else:
                begin_idx = meta.seg_list[-sub_lv_cnt].begin_x
            y_begin, y_end = ax.get_ylim()
            x_end = int(ax.get_xlim()[1])
            ax.fill_between(range(begin_idx, x_end + 1), y_begin, y_end, facecolor=facecolor, alpha=alpha)

    def draw_segseg(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        width=7,
        color="brown",
        disp_end=False,
        end_color='brown',
        end_fontsize=15,
        show_num=False,
        num_fontsize=30,
        num_color="blue",
    ):
        """
        绘制线段构成的线段（segseg）

        这是更高级别的结构，由线段构成的线段。
        外观比普通线段更粗，颜色不同（棕色）。

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            width: 线宽（比普通线段更粗）
            color: 颜色（棕色）
            disp_end: 是否显示端点价格
            end_color: 端点价格颜色
            end_fontsize: 端点价格字体大小
            show_num: 是否显示编号
            num_fontsize: 编号字体大小
            num_color: 编号颜色
        """
        x_begin = ax.get_xlim()[0]

        for seg_idx, seg_meta in enumerate(meta.segseg_list):
            if seg_meta.end_x < x_begin:
                continue
            if seg_meta.is_sure:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y],
                        color=color, linewidth=width)
            else:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y],
                        color=color, linewidth=width, linestyle='dashed')

            if disp_end:
                # 第一个线段显示起点价格
                if seg_idx == 0:
                    ax.text(
                        seg_meta.begin_x, seg_meta.begin_y,
                        f'{seg_meta.begin_y:.2f}',
                        fontsize=end_fontsize, color=end_color,
                        verticalalignment="top" if seg_meta.dir == BI_DIR.UP else "bottom",
                        horizontalalignment='center')
                # 所有线段显示终点价格
                ax.text(
                    seg_meta.end_x, seg_meta.end_y,
                    f'{seg_meta.end_y:.2f}',
                    fontsize=end_fontsize, color=end_color,
                    verticalalignment="top" if seg_meta.dir == BI_DIR.DOWN else "bottom",
                    horizontalalignment='center')

            if show_num and seg_meta.begin_x >= x_begin:
                ax.text((seg_meta.begin_x + seg_meta.end_x) / 2, (seg_meta.begin_y + seg_meta.end_y) / 2,
                        f'{seg_meta.idx}', fontsize=num_fontsize, color=num_color)

    def plot_single_eigen(self, eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak):
        """
        绘制单个特征序列分型

        参数:
            eigenfx_meta: 特征序列分型元数据
            ax: 坐标轴
            color_top: 顶分型颜色
            color_bottom: 底分型颜色
            aplha: 透明度
            only_peak: 是否只绘制峰值元素（中间那个）

        特征序列分型包含三个元素，用矩形绘制。
        如果 only_peak=True，只绘制中间的元素（峰值）。
        """
        x_begin = ax.get_xlim()[0]
        color = color_top if eigenfx_meta.fx == FX_TYPE.TOP else color_bottom
        for idx, eigen_meta in enumerate(eigenfx_meta.ele):
            if eigen_meta.begin_x + eigen_meta.w < x_begin:
                continue
            if only_peak and idx != 1:
                continue  # 只绘制峰值（中间元素）
            ax.add_patch(
                Rectangle(
                    (eigen_meta.begin_x, eigen_meta.begin_y),
                    eigen_meta.w,
                    eigen_meta.h,
                    fill=True,
                    alpha=aplha,
                    color=color
                )
            )

    def draw_eigen(self, meta: CChanPlotMeta, ax: Axes, color_top="r", color_bottom="b", aplha=0.5, only_peak=False):
        """绘制笔级别的特征序列分型"""
        for eigenfx_meta in meta.eigenfx_lst:
            self.plot_single_eigen(eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak)

    def draw_segeigen(self, meta: CChanPlotMeta, ax: Axes, color_top="r", color_bottom="b", aplha=0.5, only_peak=False):
        """绘制线段级别的特征序列分型"""
        for eigenfx_meta in meta.seg_eigenfx_lst:
            self.plot_single_eigen(eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak)

    def draw_zs(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        color='orange',
        linewidth=2,
        sub_linewidth=0.5,
        show_text=False,
        fontsize=14,
        text_color='orange',
        draw_one_bi_zs=False,
    ):
        """
        绘制笔中枢

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            color: 中枢颜色
            linewidth: 中枢框线宽
            sub_linewidth: 子中枢框线宽
            show_text: 是否显示中枢高低点数值
            fontsize: 文字大小
            text_color: 文字颜色
            draw_one_bi_zs: 是否绘制单笔中枢

        中枢用矩形框绘制：
        - 确定中枢：实线框
        - 未确定中枢：虚线框
        - 子中枢：细线框（虚线）
        """
        linewidth = max(linewidth, 2)
        x_begin = ax.get_xlim()[0]
        for zs_meta in meta.zs_lst:
            if not draw_one_bi_zs and zs_meta.is_onebi_zs:
                continue
            if zs_meta.begin + zs_meta.w < x_begin:
                continue
            line_style = '-' if zs_meta.is_sure else '--'
            # 主中枢框
            ax.add_patch(Rectangle(
                (zs_meta.begin, zs_meta.low), zs_meta.w, zs_meta.h,
                fill=False, color=color, linewidth=linewidth, linestyle=line_style))
            # 子中枢框
            for sub_zs_meta in zs_meta.sub_zs_lst:
                ax.add_patch(Rectangle(
                    (sub_zs_meta.begin, sub_zs_meta.low), sub_zs_meta.w, sub_zs_meta.h,
                    fill=False, color=color, linewidth=sub_linewidth, linestyle=line_style))
            if show_text:
                add_zs_text(ax, zs_meta, fontsize, text_color)
                for sub_zs_meta in zs_meta.sub_zs_lst:
                    add_zs_text(ax, sub_zs_meta, fontsize, text_color)

    def draw_segzs(self, meta: CChanPlotMeta, ax: Axes, color='red', linewidth=10, sub_linewidth=4):
        """绘制线段中枢（比笔中枢更粗的线宽）"""
        linewidth = max(linewidth, 2)
        x_begin = ax.get_xlim()[0]
        for zs_meta in meta.segzs_lst:
            if zs_meta.begin + zs_meta.w < x_begin:
                continue
            line_style = '-' if zs_meta.is_sure else '--'
            ax.add_patch(Rectangle(
                (zs_meta.begin, zs_meta.low), zs_meta.w, zs_meta.h,
                fill=False, color=color, linewidth=linewidth, linestyle=line_style))
            for sub_zs_meta in zs_meta.sub_zs_lst:
                ax.add_patch(Rectangle(
                    (sub_zs_meta.begin, sub_zs_meta.low), sub_zs_meta.w, sub_zs_meta.h,
                    fill=False, color=color, linewidth=sub_linewidth, linestyle=line_style))

    def draw_macd(self, meta: CChanPlotMeta, ax: Axes, x_limits, width=0.4):
        """
        绘制 MACD 指标

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            x_limits: X 轴范围
            width: MACD 柱宽度

        绘制内容：
        - DIF 线（橙色 #FFA500）
        - DEA 线（蓝色 #0000ff）
        - MACD 柱（红涨绿跌）
        """
        macd_lst = [klu.macd for klu in meta.klu_iter()]
        assert macd_lst[0] is not None, "you can't draw macd until you delete macd_metric=False"

        x_begin = x_limits[0]
        x_idx = range(len(macd_lst))[x_begin:]
        dif_line = [macd.DIF for macd in macd_lst[x_begin:]]
        dea_line = [macd.DEA for macd in macd_lst[x_begin:]]
        macd_bar = [macd.macd for macd in macd_lst[x_begin:]]

        # 计算 Y 轴范围
        y_min = min([min(dif_line), min(dea_line), min(macd_bar)])
        y_max = max([max(dif_line), max(dea_line), max(macd_bar)])

        ax.plot(x_idx, dif_line, "#FFA500")   # DIF 线（橙色）
        ax.plot(x_idx, dea_line, "#0000ff")   # DEA 线（蓝色）

        # MACD 柱状图：正值为红，负值为深绿
        _bar = ax.bar(x_idx, macd_bar, color="r", width=width)
        for idx, macd in enumerate(macd_bar):
            if macd < 0:
                _bar[idx].set_color("#006400")

        ax.set_ylim(y_min, y_max)

    def draw_mean(self, meta: CChanPlotMeta, ax: Axes):
        """
        绘制均线

        参数:
            meta: 绘图元数据
            ax: 坐标轴

        为每个配置的均线周期绘制一条线。
        均线周期通过 CChanConfig.mean_metrics 配置。
        """
        mean_lst = [klu.trend[TREND_TYPE.MEAN] for klu in meta.klu_iter()]
        Ts = list(mean_lst[0].keys())
        cmap = plt.cm.get_cmap('hsv', max([10, len(Ts)]))  # type: ignore
        for cmap_idx, T in enumerate(Ts):
            mean_arr = [mean_dict[T] for mean_dict in mean_lst]
            ax.plot(range(len(mean_arr)), mean_arr, c=cmap(cmap_idx), label=f'{T} meanline')
        ax.legend()

    def draw_channel(self, meta: CChanPlotMeta, ax: Axes, T=None, top_color="r", bottom_color="b", linewidth=3, linestyle="solid"):
        """
        绘制趋势通道（最高价通道和最低价通道）

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            T: 周期（默认使用最大周期）
            top_color: 上轨颜色
            bottom_color: 下轨颜色
            linewidth: 线宽
            linestyle: 线型

        趋势通道由 CTrendModel(MAX) 和 CTrendModel(MIN) 组成，
        上轨是周期内最高价，下轨是周期内最低价。
        """
        max_lst = [klu.trend[TREND_TYPE.MAX] for klu in meta.klu_iter()]
        min_lst = [klu.trend[TREND_TYPE.MIN] for klu in meta.klu_iter()]
        config_T_lst = sorted(list(max_lst[0].keys()))
        if T is None:
            T = config_T_lst[-1]  # 默认使用最大周期
        elif T not in max_lst[0]:
            raise CChanException(
                f"plot channel of T={T} is not setted in CChanConfig.trend_metrics = {config_T_lst}",
                ErrCode.PLOT_ERR)
        top_array = [_d[T] for _d in max_lst]
        bottom_array = [_d[T] for _d in min_lst]
        ax.plot(range(len(top_array)), top_array, c=top_color, linewidth=linewidth, linestyle=linestyle, label=f'{T}-TOP-channel')
        ax.plot(range(len(bottom_array)), bottom_array, c=bottom_color, linewidth=linewidth, linestyle=linestyle, label=f'{T}-BUTTOM-channel')
        ax.legend()

    def draw_boll(self, meta: CChanPlotMeta, ax: Axes, mid_color="black", up_color="blue", down_color="purple"):
        """
        绘制布林带

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            mid_color: 中轨颜色
            up_color: 上轨颜色
            down_color: 下轨颜色

        布林带由三条线组成：
        - MID: 中轨（移动平均线）
        - UP: 上轨（中轨 + 标准差）
        - DOWN: 下轨（中轨 - 标准差）

        同时更新 Y 轴范围以包含布林带的上下轨。
        """
        x_begin = int(ax.get_xlim()[0])
        try:
            ma = [klu.boll.MID for klu in meta.klu_iter()][x_begin:]
            up = [klu.boll.UP for klu in meta.klu_iter()][x_begin:]
            down = [klu.boll.DOWN for klu in meta.klu_iter()][x_begin:]
        except AttributeError as e:
            raise CChanException("you can't draw boll until you set boll_n in CChanConfig", ErrCode.PLOT_ERR) from e

        ax.plot(range(x_begin, x_begin + len(ma)), ma, c=mid_color)
        ax.plot(range(x_begin, x_begin + len(up)), up, c=up_color)
        ax.plot(range(x_begin, x_begin + len(down)), down, c=down_color)
        self.y_min = min([self.y_min, min(down)])
        self.y_max = max([self.y_max, max(up)])

    def bsp_common_draw(self, bsp_list, ax: Axes, buy_color, sell_color, fontsize, arrow_l, arrow_h, arrow_w):
        """
        买卖点通用绘制方法

        参数:
            bsp_list: 买卖点元数据列表
            ax: 坐标轴
            buy_color: 买点颜色
            sell_color: 卖点颜色
            fontsize: 字体大小
            arrow_l: 箭头长度比例
            arrow_h: 箭头头部比例
            arrow_w: 箭头宽度

        每个买卖点用箭头 + 文字标注，买点箭头向上，卖点箭头向下。
        同时更新 Y 轴范围以包含标注文字。
        """
        x_begin = ax.get_xlim()[0]
        y_range = self.y_max - self.y_min
        for bsp in bsp_list:
            if bsp.x < x_begin:
                continue
            color = buy_color if bsp.is_buy else sell_color
            verticalalignment = 'top' if bsp.is_buy else 'bottom'

            arrow_dir = 1 if bsp.is_buy else -1  # 买点向上，卖点向下
            arrow_len = arrow_l * y_range
            arrow_head = arrow_len * arrow_h

            # 标注文字
            ax.text(bsp.x,
                    bsp.y - arrow_len * arrow_dir,
                    f'{bsp.desc()}',
                    fontsize=fontsize,
                    color=color,
                    verticalalignment=verticalalignment,
                    horizontalalignment='center')
            # 箭头
            ax.arrow(bsp.x,
                     bsp.y - arrow_len * arrow_dir,
                     0,
                     (arrow_len - arrow_head) * arrow_dir,
                     head_width=arrow_w,
                     head_length=arrow_head,
                     color=color)

            # 更新 Y 轴范围
            if bsp.y - arrow_len * arrow_dir < self.y_min:
                self.y_min = bsp.y - arrow_len * arrow_dir
            if bsp.y - arrow_len * arrow_dir > self.y_max:
                self.y_max = bsp.y - arrow_len * arrow_dir

    def draw_bs_point(self, meta: CChanPlotMeta, ax: Axes, buy_color='r', sell_color='g', fontsize=15, arrow_l=0.15, arrow_h=0.2, arrow_w=1):
        """绘制笔级别的买卖点"""
        self.bsp_common_draw(
            bsp_list=meta.bs_point_lst,
            ax=ax,
            buy_color=buy_color,
            sell_color=sell_color,
            fontsize=fontsize,
            arrow_l=arrow_l,
            arrow_h=arrow_h,
            arrow_w=arrow_w,
        )

    def draw_seg_bs_point(self, meta: CChanPlotMeta, ax: Axes, buy_color='r', sell_color='g', fontsize=18, arrow_l=0.2, arrow_h=0.25, arrow_w=1.2):
        """绘制线段级别的买卖点（字体和箭头更大）"""
        self.bsp_common_draw(
            bsp_list=meta.seg_bsp_lst,
            ax=ax,
            buy_color=buy_color,
            sell_color=sell_color,
            fontsize=fontsize,
            arrow_l=arrow_l,
            arrow_h=arrow_h,
            arrow_w=arrow_w,
        )

    def update_y_range(self, text_box, text_y):
        """更新 Y 轴范围以包含文字标注"""
        text_height = text_box.y1 - text_box.y0
        self.y_min = min([self.y_min, text_y - text_height])
        self.y_max = max([self.y_max, text_y + text_height])

    def plot_closeAction(self, plot_cover, cbsp, ax: Axes, text_y, arrow_len, arrow_dir, color):
        """绘制买卖点的平仓动作箭头（指示平仓位置）"""
        if not plot_cover:
            return
        for closeAction in cbsp.close_action:
            ax.arrow(
                cbsp.x,
                text_y,
                closeAction.x - cbsp.x,
                arrow_len * arrow_dir + (closeAction.y - cbsp.y),
                color=color,
            )

    def draw_marker(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        markers: Dict[CTime | str, Tuple[str, Literal['up', 'down'], str] | Tuple[str, Literal['up', 'down']]],
        arrow_l=0.15,
        arrow_h_r=0.2,
        arrow_w=1,
        fontsize=14,
        default_color='b',
    ):
        """
        绘制自定义标记

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            markers: 标记字典
              格式: {'2022/03/01': ('标记内容', 'up', 'red'), '2022/03/02': ('标记内容', 'down')}
              - 'up': 标记在K线上方
              - 'down': 标记在K线下方
              颜色可选，默认蓝色
            arrow_l: 箭头长度比例
            arrow_h_r: 箭头头部比例
            arrow_w: 箭头宽度
            fontsize: 字体大小
            default_color: 默认颜色

        用于在图表上标记特定日期的事件或注释。
        """
        x_begin, x_end = ax.get_xlim()
        datetick_dict = {date: idx for idx, date in enumerate(meta.datetick)}

        # 处理子级别时间匹配（如分钟级别的K线匹配日期的标记）
        new_marker = {}
        for klu in meta.klu_iter():
            for date, marker in markers.items():
                date_str = date.to_str() if isinstance(date, CTime) else date
                if klu.include_sub_lv_time(date_str) and klu.time.to_str() != date_str:
                    new_marker[klu.time.to_str()] = marker
        new_marker.update(markers)

        kl_dict = dict(enumerate(meta.klu_iter()))
        y_range = self.y_max - self.y_min
        arror_len = arrow_l * y_range
        arrow_h = arror_len * arrow_h_r

        for date, marker in new_marker.items():
            if isinstance(date, CTime):
                date = date.to_str()
            if date not in datetick_dict:
                continue
            x = datetick_dict[date]
            if x < x_begin or x > x_end:
                continue

            # 解析标记参数
            if len(marker) == 2:
                color = default_color
                marker_content, position = marker
            else:
                assert len(marker) == 3
                marker_content, position, color = marker
            assert position in ['up', 'down']

            _dir = -1 if position == 'up' else 1
            bench = kl_dict[x].high if position == 'up' else kl_dict[x].low

            # 绘制箭头
            ax.arrow(
                x,
                bench - arror_len * _dir,
                0,
                (arror_len - arrow_h) * _dir,
                head_width=arrow_w,
                head_length=arrow_h,
                color=color
            )
            # 绘制文字
            ax.text(
                x,
                bench - arror_len * _dir,
                marker_content,
                fontsize=fontsize,
                color=color,
                verticalalignment='top' if position == 'down' else 'bottom',
                horizontalalignment='center'
            )

    def draw_demark_begin_line(self, ax, begin_line_color, plot_begin_set: set, linestyle: str, demark_idx: T_DEMARK_INDEX):
        """绘制 Demark TDST 峰值线"""
        if begin_line_color is not None and demark_idx['series'].TDST_peak is not None and id(demark_idx['series']) not in plot_begin_set:
            if demark_idx['series'].countdown is not None:
                end_idx = demark_idx['series'].countdown.kl_list[-1].idx
            else:
                end_idx = demark_idx['series'].kl_list[-1].idx
            ax.plot(
                [demark_idx['series'].kl_list[CDemarkEngine.SETUP_BIAS].idx, end_idx],
                [demark_idx['series'].TDST_peak, demark_idx['series'].TDST_peak],
                c=begin_line_color,
                linestyle=linestyle
            )
            plot_begin_set.add(id(demark_idx['series']))

    def draw_rsi(
        self,
        meta: CChanPlotMeta,
        ax,
        color='b',
    ):
        """
        绘制 RSI 指标

        参数:
            meta: 绘图元数据
            ax: 坐标轴（使用 twinx 创建的副坐标轴）
            color: 线条颜色
        """
        data = [klu.rsi for klu in meta.klu_iter()]
        x_begin, x_end = int(ax.get_xlim()[0]), int(ax.get_xlim()[1])
        ax.plot(range(x_begin, x_end), data[x_begin: x_end], c=color)

    def draw_kdj(
        self,
        meta: CChanPlotMeta,
        ax,
        k_color='orange',
        d_color='blue',
        j_color='pink',
    ):
        """
        绘制 KDJ 指标

        参数:
            meta: 绘图元数据
            ax: 坐标轴（使用 twinx 创建的副坐标轴）
            k_color: K 线颜色
            d_color: D 线颜色
            j_color: J 线颜色

        分别绘制 K/D/J 三条线。
        """
        kdj = [klu.kdj for klu in meta.klu_iter()]
        x_begin, x_end = int(ax.get_xlim()[0]), int(ax.get_xlim()[1])
        ax.plot(range(x_begin, x_end), [x.k for x in kdj][x_begin: x_end], c=k_color, label='K')
        ax.plot(range(x_begin, x_end), [x.d for x in kdj][x_begin: x_end], c=d_color, label='D')
        ax.plot(range(x_begin, x_end), [x.j for x in kdj][x_begin: x_end], c=j_color, label='J')
        ax.legend()

    def draw_demark(
            self,
            meta: CChanPlotMeta,
            ax: Axes,
            setup_color='b',
            countdown_color='r',
            fontsize=12,
            min_setup=9,
            max_countdown_background='yellow',
            begin_line_color: Optional[str] = 'purple',
            begin_line_style='dashed',
    ):  # sourcery skip: low-code-quality
        """
        绘制 Demark 序列

        参数:
            meta: 绘图元数据
            ax: 坐标轴
            setup_color: Setup 数字颜色
            countdown_color: Countdown 数字颜色
            fontsize: 字体大小
            min_setup: 最小显示 Setup 值
            max_countdown_background: 最大倒计时背景色
            begin_line_color: TDST 峰值线颜色
            begin_line_style: TDST 峰值线型

        绘制内容：
        - Setup 数字：在 K 线下方（下降）或上方（上升）
        - Countdown 数字：紧接着 Setup 数字显示
        - TDST 峰值线：水平虚线
        - 最大倒计时（13）：黄色高亮背景
        """
        x_begin = ax.get_xlim()[0]
        text_height: Optional[float] = None
        for klu in meta.klu_iter():
            if klu.idx < x_begin:
                continue
            under_bias, upper_bias = 0, 0  # 累计偏移量，避免文字重叠
            plot_begin_set = set()

            # 绘制 Setup 数字
            for demark_idx in klu.demark.get_setup():
                if demark_idx['series'].idx < min_setup or not demark_idx['series'].setup_finished:
                    continue
                self.draw_demark_begin_line(ax, begin_line_color, plot_begin_set, begin_line_style, demark_idx)
                txt_instance = ax.text(
                    klu.idx,
                    klu.low - under_bias if demark_idx['dir'] == BI_DIR.DOWN else klu.high + upper_bias,
                    str(demark_idx['idx']),
                    fontsize=fontsize,
                    color=setup_color,
                    verticalalignment='top' if demark_idx['dir'] == BI_DIR.DOWN else 'bottom',
                    horizontalalignment='center'
                )
                # 累计偏移量，避免文字重叠
                if demark_idx['dir'] == BI_DIR.DOWN:
                    under_bias += getTextBox(ax, txt_instance).height if demark_idx['dir'] == BI_DIR.DOWN else 0
                else:
                    upper_bias += getTextBox(ax, txt_instance).height

            # 绘制 Countdown 数字
            for demark_idx in klu.demark.get_countdown():
                box_bias = 0.5 * text_height if text_height is not None and demark_idx['idx'] == CDemarkEngine.MAX_COUNTDOWN else 0
                txt_instance = ax.text(
                    klu.idx,
                    klu.low - under_bias - box_bias if demark_idx['dir'] == BI_DIR.DOWN else klu.high + upper_bias + box_bias,
                    str(demark_idx['idx']),
                    fontsize=fontsize,
                    color=countdown_color,
                    verticalalignment='top' if demark_idx['dir'] == BI_DIR.DOWN else 'bottom',
                    horizontalalignment='center',
                )
                if text_height is None:
                    text_height = getTextBox(ax, txt_instance).height
                # 最大倒计时（13）黄色高亮背景
                if demark_idx['idx'] == CDemarkEngine.MAX_COUNTDOWN:
                    txt_instance.set_bbox(dict(facecolor=max_countdown_background, edgecolor=max_countdown_background, pad=0))
                if demark_idx['dir'] == BI_DIR.DOWN:
                    under_bias += getTextBox(ax, txt_instance).height
                else:
                    upper_bias += getTextBox(ax, txt_instance).height


def getTextBox(ax: Axes, txt_instance):
    """
    获取文字对象的边界框（数据坐标）

    参数:
        ax: 坐标轴
        txt_instance: matplotlib Text 对象

    返回:
        转换到数据坐标的边界框

    用于计算文字标注的实际大小，避免重叠。
    """
    return txt_instance.get_window_extent().transformed(ax.transData.inverted())


def plot_bi_element(bi: CBi_meta, ax: Axes, color: str):
    """
    绘制单根笔

    参数:
        bi: 笔元数据
        ax: 坐标轴
        color: 颜色

    确定笔用实线，虚拟笔用虚线。
    """
    if bi.is_sure:
        ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], color=color)
    else:
        ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], linestyle='dashed', color=color)


def bi_text(bi_idx, ax: Axes, bi, end_fontsize, end_color):
    """
    绘制笔/线段的端点价格文字

    参数:
        bi_idx: 笔/线段索引
        ax: 坐标轴
        bi: 笔/线段元数据
        end_fontsize: 字体大小
        end_color: 文字颜色

    第一个笔/线段同时显示起点和终点价格，后续只显示终点价格。
    """
    if bi_idx == 0:
        # 第一个：显示起点价格
        ax.text(
            bi.begin_x, bi.begin_y,
            f'{bi.begin_y:.5f}',
            fontsize=end_fontsize, color=end_color,
            verticalalignment="top" if bi.dir == BI_DIR.UP else "bottom",
            horizontalalignment='center')
    # 显示终点价格
    ax.text(
        bi.end_x, bi.end_y,
        f'{bi.end_y:.5f}',
        fontsize=end_fontsize, color=end_color,
        verticalalignment="top" if bi.dir == BI_DIR.DOWN else "bottom",
        horizontalalignment='center')


def show_func_helper(func):
    """
    显示函数签名和默认参数

    参数:
        func: 函数对象

    用于生成文档，打印函数名和参数默认值。
    Python 特性：inspect.signature 获取函数签名
    Java 对比：Java 的反射 Method.getParameters()
    """
    print(f"{func.__name__}:")
    insp = inspect.signature(func)
    for name, para in insp.parameters.items():
        if para.default == inspect.Parameter.empty:
            continue  # 跳过没有默认值的参数
        elif isinstance(para.default, str):
            print(f"\t{name}: '{para.default}'")
        else:
            print(f"\t{name}: {para.default}")


def add_zs_text(ax: Axes, zs_meta: CZS_meta, fontsize, text_color):
    """
    在中枢框上显示高低点数值

    参数:
        ax: 坐标轴
        zs_meta: 中枢元数据
        fontsize: 字体大小
        text_color: 文字颜色

    在左下角显示低点，右上角显示高点。
    """
    ax.text(
        zs_meta.begin, zs_meta.low,
        f'{zs_meta.low:.2f}',
        fontsize=fontsize, color=text_color,
        verticalalignment="top",
        horizontalalignment='center',
    )
    ax.text(
        zs_meta.begin + zs_meta.w, zs_meta.low + zs_meta.h,
        f'{zs_meta.low + zs_meta.h:.2f}',
        fontsize=fontsize, color=text_color,
        verticalalignment="bottom",
        horizontalalignment='center',
    )