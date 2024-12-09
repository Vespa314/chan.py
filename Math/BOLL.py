import math

# 定义一个辅助函数，用于避免零值
def _truncate(x):
    return x if x != 0 else 1e-7  # 如果 x 为 0，则返回一个很小的数 1e-7

# 定义 BOLL_Metric 类，用于表示布林带指标
class BOLL_Metric:
    def __init__(self, ma, theta):
        self.theta = _truncate(theta)  # 存储标准差，避免为零
        self.UP = ma + 2 * theta  # 计算布林带上轨
        self.DOWN = _truncate(ma - 2 * theta)  # 计算布林带下轨，避免为零
        self.MID = ma  # 存储中轨（移动平均）

# 定义 BollModel 类，用于计算布林带
class BollModel:
    def __init__(self, N=20):
        assert N > 1  # 确保 N 大于 1
        self.N = N  # 设置周期 N
        self.arr = []  # 存储价格值的列表

    # 添加新的价格值并计算布林带指标
    def add(self, value) -> BOLL_Metric:
        self.arr.append(value)  # 将新值添加到列表中
        if len(self.arr) > self.N:  # 如果列表长度超过周期 N
            self.arr = self.arr[-self.N:]  # 只保留最近 N 个值
        ma = sum(self.arr) / len(self.arr)  # 计算移动平均
        theta = math.sqrt(sum((x - ma) ** 2 for x in self.arr) / len(self.arr))  # 计算标准差
        return BOLL_Metric(ma, theta)  # 返回计算得到的布林带指标对象