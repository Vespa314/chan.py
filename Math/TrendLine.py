import copy
from dataclasses import dataclass
from math import sqrt

from Common.CEnum import BI_DIR


@dataclass
class Point:
    x: int
    y: float

    def cal_slope(self, p):
        return (self.y-p.y)/(self.x-p.x) if self.x != p.x else float("inf")


@dataclass
class Line:
    p: Point
    slope: float

    def cal_dis(self, p):
        return abs(self.slope*p.x - p.y + self.p.y - self.slope*self.p.x) / sqrt(self.slope**2 + 1)


class CTrendLine:
    def __init__(self, lst):
        self.line = None
        self.cal(lst)

    def cal(self, lst):
        bench = float('inf')
        all_p = [Point(bi.get_begin_klu().idx, bi.get_begin_val()) for bi in lst[-1::-2]]
        c_p = copy.copy(all_p)
        while True:
            line, idx = cal_tl(c_p, lst[-1].dir)
            dis = sum(line.cal_dis(p) for p in all_p)
            if dis < bench:
                bench = dis
                self.line = line
            c_p = c_p[idx:]
            if len(c_p) == 1:
                break


def cal_tl(c_p, _dir):
    p = c_p[0]
    peak_slope = 0
    idx = 1
    for point_idx, p2 in enumerate(c_p[1:]):
        slope = p.cal_slope(p2)
        if (_dir == BI_DIR.UP and slope > peak_slope) or (_dir == BI_DIR.DOWN and slope < peak_slope):
            peak_slope = slope
            idx = point_idx+1
    return Line(p, peak_slope), idx
