# -*- coding: utf-8 -*-
"""
趋势线模块 - 计算线段的支撑/阻力趋势线

Java 开发者注意：
- @dataclass 是 Python 的数据类装饰器，自动生成 __init__/__eq__/__repr__
  Java 对比：类似于 Java 14+ record 或 Lombok @Data
- Python 的 math.sqrt 类似于 Java 的 Math.sqrt()
- Python 的 copy.copy 是浅拷贝，类似于 Java 的 clone() 或 new + 复制引用
- Python 的多重赋值 a, b = func() 可以同时接收多个返回值
  Java 对比：Java 只能返回一个值，需要包装类或数组
"""

import copy
from dataclasses import dataclass
from math import sqrt

from Common.CEnum import BI_DIR, TREND_LINE_SIDE


@dataclass
class Point:
    """二维点 - 用于趋势线计算"""
    x: int
    y: float

    def cal_slope(self, p):
        """计算与另一个点的斜率"""
        return (self.y-p.y)/(self.x-p.x) if self.x != p.x else float("inf")


@dataclass
class Line:
    """直线 - 由点和斜率定义"""
    p: Point
    slope: float

    def cal_dis(self, p):
        """计算点到直线的距离"""
        return abs(self.slope*p.x - p.y + self.p.y - self.slope*self.p.x) / sqrt(self.slope**2 + 1)


class CTrendLine:
    """
    趋势线 - 计算线段的支撑线或阻力线

    参数:
        lst: 笔列表（至少3笔）
        side: 趋势线类型
          - INSIDE: 支撑线（连接低点）
          - OUTSIDE: 阻力线（连接高点）

    缠论知识 - 趋势线：
    支撑线：连接上升线段中相邻笔的低点
    阻力线：连接下降线段中相邻笔的高点

    趋势线用于判断线段内部的支撑/压力位，
    以及线段是否被有效突破。
    """

    def __init__(self, lst, side=TREND_LINE_SIDE.OUTSIDE):
        self.line = None
        self.side = side
        self.cal(lst)

    def cal(self, lst):
        """
        计算趋势线

        算法：
        1. 取所有笔的端点（INSIDE=起始点，OUTSIDE=结束点），从后往前取
        2. 以第一个点为基础，尝试与后面的点连线
        3. 计算所有点到该直线的距离之和
        4. 选择距离最小的直线作为趋势线

        从后往前逐点连线，取距离最小的那条。
        """
        bench = float('inf')
        if self.side == TREND_LINE_SIDE.INSIDE:
            # 支撑线：取相邻笔的起始点（低点）
            all_p = [Point(bi.get_begin_klu().idx, bi.get_begin_val()) for bi in lst[-1::-2]]
        else:
            # 阻力线：取相邻笔的结束点（高点）
            all_p = [Point(bi.get_end_klu().idx, bi.get_end_val()) for bi in lst[-1::-2]]

        c_p = copy.copy(all_p)  # 浅拷贝，用于迭代
        while True:
            line, idx = cal_tl(c_p, lst[-1].dir, self.side)
            dis = sum(line.cal_dis(p) for p in all_p)  # 所有点到直线的距离之和
            if dis < bench:
                bench = dis
                self.line = line
            c_p = c_p[idx:]  # 从找到的极值点开始继续
            if len(c_p) == 1:
                break


def init_peak_slope(_dir, side):
    """
    初始化峰值斜率

    参数:
        _dir: 线段方向
        side: 趋势线类型

    返回:
        初始斜率值

    支撑线（INSIDE）初始斜率 = 0
    阻力线（OUTSIDE）：
    - 上升线段：初始斜率 = +inf（找最小斜率）
    - 下降线段：初始斜率 = -inf（找最大斜率）
    """
    if side == TREND_LINE_SIDE.INSIDE:
        return 0
    elif _dir == BI_DIR.UP:
        return float("inf")
    else:
        return -float("inf")


def cal_tl(c_p, _dir, side):
    """
    计算趋势线

    参数:
        c_p: 候选点列表
        _dir: 线段方向
        side: 趋势线类型

    返回:
        (Line, idx) 最优直线和对应点的索引

    算法：
    以第一个点为基准，遍历后续点，找最优斜率。

    - 支撑线（INSIDE）：找最大斜率（最陡的支撑线）
    - 阻力线（OUTSIDE）：找最小斜率（最平坦的阻力线）

    约束：斜率方向必须与线段方向一致
    - 上升线段：斜率 > 0
    - 下降线段：斜率 < 0
    """
    p = c_p[0]
    peak_slope = init_peak_slope(_dir, side)
    idx = 1
    for point_idx, p2 in enumerate(c_p[1:]):
        slope = p.cal_slope(p2)
        # 斜率方向必须与线段方向一致
        if (_dir == BI_DIR.UP and slope < 0) or (_dir == BI_DIR.DOWN and slope > 0):
            continue
        if side == TREND_LINE_SIDE.INSIDE:
            # 支撑线：找更大斜率
            if (_dir == BI_DIR.UP and slope > peak_slope) or (_dir == BI_DIR.DOWN and slope < peak_slope):
                peak_slope = slope
                idx = point_idx+1
        else:
            # 阻力线：找更小斜率
            if (_dir == BI_DIR.UP and slope < peak_slope) or (_dir == BI_DIR.DOWN and slope > peak_slope):
                peak_slope = slope
                idx = point_idx+1
    return Line(p, peak_slope), idx