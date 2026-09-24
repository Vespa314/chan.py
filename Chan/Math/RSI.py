class RSI:
    def __init__(self, period: int = 14):
        super(RSI, self).__init__()
        self.close_arr = []
        self.period = period
        self.diff = []
        self.up = []
        self.down = []

    def add(self, close):
        self.close_arr.append(close)
        if len(self.close_arr) == 1:
            return 50.0

        self.diff.append(self.close_arr[-1] - self.close_arr[-2])

        if len(self.diff) < self.period:
            up_sum = sum(x for x in self.diff if x > 0)
            down_sum = sum(-x for x in self.diff if x < 0)
            self.up.append(up_sum / len(self.diff))
            self.down.append(down_sum / len(self.diff))
        else:
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
