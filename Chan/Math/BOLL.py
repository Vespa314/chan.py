import math


def _truncate(x):
    return x if x != 0 else 1e-7


class BOLL_Metric:
    def __init__(self, ma, theta):
        self.theta = _truncate(theta)
        self.UP = ma + 2*theta
        self.DOWN = _truncate(ma - 2*theta)
        self.MID = ma


class BollModel:
    def __init__(self, N=20):
        assert N > 1
        self.N = N
        self.arr = []

    def add(self, value) -> BOLL_Metric:
        self.arr.append(value)
        if len(self.arr) > self.N:
            self.arr = self.arr[-self.N:]
        ma = sum(self.arr)/len(self.arr)
        theta = math.sqrt(sum((x-ma)**2 for x in self.arr) / len(self.arr))
        return BOLL_Metric(ma, theta)
