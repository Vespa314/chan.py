class RSI:
    def __init__(self, period: int = 14):
        super(RSI, self).__init__()
        self.close_arr = []  # 存储收盘价的列表
        self.period = period  # RSI计算的周期，默认为14
        self.diff = []  # 存储收盘价的差值
        self.up = []  # 存储上涨的平均值
        self.down = []  # 存储下跌的平均值

    # 添加新的收盘价并计算当前的RSI值
    def add(self, close):
        self.close_arr.append(close)  # 将新的收盘价添加到列表中

        # 如果是第一个收盘价，返回默认的RSI值50.0
        if len(self.close_arr) == 1:
            return 50.0

        # 计算当前收盘价与前一个收盘价的差值
        self.diff.append(self.close_arr[-1] - self.close_arr[-2])

        # 如果差值列表的长度小于周期，计算初始的上涨和下跌平均值
        if len(self.diff) < self.period:
            self.up.append(sum(x for x in self.diff if x > 0) / self.period)  # 计算上涨平均值
            self.down.append(sum(-x for x in self.diff if x < 0) / self.period)  # 计算下跌平均值
        else:
            # 根据当前差值更新上涨和下跌平均值
            if self.diff[-1] > 0:
                upval = self.diff[-1]  # 当前上涨值
                downval = 0.0  # 当前下跌值为0
            else:
                upval = 0.0  # 当前上涨值为0
                downval = -self.diff[-1]  # 当前下跌值

            # 更新上涨和下跌的平均值
            self.up.append((self.up[-1] * (self.period - 1) + upval) / self.period)
            self.down.append((self.down[-1] * (self.period - 1) + downval) / self.period)

        # 计算相对强弱指数RSI
        rs = self.up[-1] / self.down[-1] if self.down[-1] != 0 else 0  # 避免除以零
        rsi = 100.0 - 100.0 / (1.0 + rs)  # 计算RSI值
        return rsi  # 返回计算得到的RSI值