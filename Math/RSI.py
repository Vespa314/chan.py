# -*- coding: utf-8 -*-
"""
RSI 指标模块 - 计算相对强弱指标（Relative Strength Index）

Java 开发者注意：
- super(RSI, self).__init__() 是 Python 2 兼容写法，调用父类构造
  Python 3 可简写为 super().__init__()
- Python 列表的 append/pop 类似于 Java 的 ArrayList.add/remove
- Python 的 sum(x for x in list if cond) 是生成器表达式求和
  Java 对比：stream.filter(cond).mapToDouble().sum()
"""


class RSI:
    """
    RSI（相对强弱指标）计算器

    参数:
        period: RSI 周期（默认 14）

    计算流程：
    1. 初始阶段（数据不足 period 时）：简单平均法
       - up = 涨幅平均值
       - down = 跌幅平均值
    2. 后续阶段（数据 >= period 时）：Wilder 平滑法
       - up = (前日up * (period-1) + 当前涨幅) / period
       - down = (前日down * (period-1) + 当前跌幅) / period
    3. RS = up / down
    4. RSI = 100 - 100 / (1 + RS)

    缠论知识 - RSI 背驰：
    价格创新高但 RSI 没有同步创新高 → 顶背驰
    价格创新低但 RSI 没有同步创新低 → 底背驰
    """

    def __init__(self, period: int = 14):
        super(RSI, self).__init__()
        self.close_arr = []
        self.period = period
        self.diff = []   # 价格变化列表
        self.up = []     # 涨幅平均值列表
        self.down = []   # 跌幅平均值列表

    def add(self, close):
        """
        添加新收盘价并计算 RSI

        参数:
            close: 收盘价

        返回:
            当前 RSI 值（0-100）
        """
        self.close_arr.append(close)
        if len(self.close_arr) == 1:
            return 50.0  # 第一个值返回中性值

        self.diff.append(self.close_arr[-1] - self.close_arr[-2])  # 计算价格变化

        if len(self.diff) < self.period:
            # 初始阶段：简单平均
            up_sum = sum(x for x in self.diff if x > 0)
            down_sum = sum(-x for x in self.diff if x < 0)
            self.up.append(up_sum / len(self.diff))
            self.down.append(down_sum / len(self.diff))
        else:
            # Wilder 平滑法
            if self.diff[-1] > 0:
                upval = self.diff[-1]
                downval = 0.0
            else:
                upval = 0.0
                downval = -self.diff[-1]

            self.up.append((self.up[-1] * (self.period - 1) + upval) / self.period)
            self.down.append((self.down[-1] * (self.period - 1) + downval) / self.period)

        if self.down[-1] == 0:
            return 100.0 if self.up[-1] > 0 else 0.0

        rs = self.up[-1] / self.down[-1]
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return rsi