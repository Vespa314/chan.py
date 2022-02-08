from common.ChanException import CChanException, ErrCode


class CNormOutlinerDetection:
    def __init__(self,
                 name,
                 win_width=100,
                 mean_thred=3.0,
                 max_zero_cnt=None,
                 skip_zero=True,
                 ):
        self.name = name
        self.data = []
        self.N = 0
        self.sum = 0
        self.mean = 0
        self.std = 0
        self.win_width = win_width
        self.mean_thred = mean_thred
        self.MAX_ZERO_CNT = max_zero_cnt
        self.zero_cnt = 0
        self.skip_zero = skip_zero

    def add(self, a):
        if a is None:
            a = 0
        if a == 0:
            self.zero_cnt += 1
            if self.MAX_ZERO_CNT is not None and self.zero_cnt >= self.MAX_ZERO_CNT:
                raise CChanException(f"{self.name} has more than {self.zero_cnt} zero kline", ErrCode.TRADEINFO_TOO_MUCH_ZERO)
        if self.skip_zero:
            return 0.0
        self.data.append(a)
        self.sum += a
        self.N += 1
        self.update_std(a)
        self.update_mean()

        if self.N < self.win_width:
            return 0.0
        else:
            return self.cal_score(a)

    def cal_score(self, a):
        return abs((a-self.mean)/self.std**0.5) if self.std != 0 else 0.0

    def update_std(self, a):
        self.std = float(self.N-1)/(self.N)*(self.std+(self.mean-a)**2/(self.N))

    def update_mean(self):
        if self.N < self.win_width:
            self.mean = sum(self.data)/float(len(self.data))
            return
        inner_data = []
        for a in self.data[-self.win_width:]:
            if self.cal_score(a) < self.mean_thred:
                inner_data.append(a)
        self.mean = sum(inner_data)/float(len(inner_data))


if __name__ == "__main__":
    data = [float(x) for x in open("/home/ubuntu/tmp/volume").read().split("\n") if len(x) > 0]
    od = CNormOutlinerDetection()
    for d in data:
        od.add(d)

    print(od.score_lst)
