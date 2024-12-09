import copy
from dataclasses import dataclass
from math import sqrt
from Common.CEnum import BI_DIR, TREND_LINE_SIDE

# 定义一个点类
@dataclass
class Point:
    x: int  # 点的 x 坐标
    y: float  # 点的 y 坐标

    # 计算当前点与另一个点的斜率
    def cal_slope(self, p):
        return (self.y - p.y) / (self.x - p.x) if self.x != p.x else float("inf")  # 避免除以零

# 定义一条直线类
@dataclass
class Line:
    p: Point  # 直线上的一个点
    slope: float  # 直线的斜率

    # 计算点到直线的距离
    def cal_dis(self, p):
        return abs(self.slope * p.x - p.y + self.p.y - self.slope * self.p.x) / sqrt(self.slope**2 + 1)

# 定义趋势线类
class CTrendLine:
    def __init__(self, lst, side=TREND_LINE_SIDE.OUTSIDE):
        self.line = None  # 初始化趋势线
        self.side = side  # 趋势线的侧面（内部或外部）
        self.cal(lst)  # 计算趋势线

    # 计算趋势线
    def cal(self, lst):
        bench = float('inf')  # 初始化基准值为无穷大
        # 根据趋势线的侧面选择点
        if self.side == TREND_LINE_SIDE.INSIDE:
            all_p = [Point(bi.get_begin_klu().idx, bi.get_begin_val()) for bi in lst[-1::-2]]  # 选择内部点
        else:
            all_p = [Point(bi.get_end_klu().idx, bi.get_end_val()) for bi in lst[-1::-2]]  # 选择外部点

        c_p = copy.copy(all_p)  # 复制所有点
        while True:
            line, idx = cal_tl(c_p, lst[-1].dir, self.side)  # 计算趋势线
            dis = sum(line.cal_dis(p) for p in all_p)  # 计算所有点到趋势线的距离之和
            if dis < bench:  # 如果当前距离小于基准值
                bench = dis  # 更新基准值
                self.line = line  # 更新趋势线
            c_p = c_p[idx:]  # 更新点列表
            if len(c_p) == 1:  # 如果只剩下一个点，停止循环
                break

# 初始化峰值斜率
def init_peak_slope(_dir, side):
    if side == TREND_LINE_SIDE.INSIDE:
        return 0  # 内部趋势线的初始斜率为0
    elif _dir == BI_DIR.UP:
        return float("inf")  # 向上趋势线的初始斜率为无穷大
    else:
        return -float("inf")  # 向下趋势线的初始斜率为负无穷大

# 计算趋势线
def cal_tl(c_p, _dir, side):
    p = c_p[0]  # 取第一个点
    peak_slope = init_peak_slope(_dir, side)  # 初始化峰值斜率
    idx = 1  # 初始化索引
    for point_idx, p2 in enumerate(c_p[1:]):  # 遍历剩余的点
        slope = p.cal_slope(p2)  # 计算当前点与下一个点的斜率
        # 根据方向过滤斜率
        if (_dir == BI_DIR.UP and slope < 0) or (_dir == BI_DIR.DOWN and slope > 0):
            continue
        # 根据侧面更新峰值斜率
        if side == TREND_LINE_SIDE.INSIDE:
            if (_dir == BI_DIR.UP and slope > peak_slope) or (_dir == BI_DIR.DOWN and slope < peak_slope):
                peak_slope = slope  # 更新峰值斜率
                idx = point_idx + 1  # 更新索引
        else:
            if (_dir == BI_DIR.UP and slope < peak_slope) or (_dir == BI_DIR.DOWN and slope > peak_slope):
                peak_slope = slope  # 更新峰值斜率
                idx = point_idx + 1  # 更新索引
    return Line(p, peak_slope), idx  # 返回计算得到的趋势线和索引