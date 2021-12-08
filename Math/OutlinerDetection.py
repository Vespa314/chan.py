class CNormOutlinerDetection:
    def __init__(self, win_width=100, thred=1.0):
        self.data = []
        self.N = 0
        self.sum = 0
        self.mean = 0
        self.std = 0
        self.win_width = win_width
        self.thred = thred

    def add(self, a):
        if a is None:
            a = 0
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
            if self.cal_score(a) < self.thred:
                inner_data.append(a)
        self.mean = sum(inner_data)/float(len(inner_data))


if __name__ == "__main__":
    data = [float(x) for x in open("/home/ubuntu/tmp/volumn").read().split("\n") if len(x) > 0]
    od = CNormOutlinerDetection()
    for d in data:
        od.add(d)

    print(od.score_lst)
