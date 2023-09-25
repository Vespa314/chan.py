class KDJ_Item:
    def __init__(self, k, d, j):
        self.k = k
        self.d = d
        self.j = j


class KDJ:
    def __init__(self, period: int = 9):
        super(KDJ, self).__init__()
        self.arr = []
        self.period = period
        self.pre_kdj = KDJ_Item(50, 50, 50)

    def add(self, high, low, close) -> KDJ_Item:
        self.arr.append({
            'high': high,
            'low': low,
        })
        if len(self.arr) > self.period:
            self.arr.pop(0)

        hn = max([x['high'] for x in self.arr])
        ln = min([x['low'] for x in self.arr])
        cn = close
        rsv = 100 * (cn - ln) / (hn - ln) if hn != ln else 0.0

        cur_k = 2 / 3 * self.pre_kdj.k + 1 / 3 * rsv
        cur_d = 2 / 3 * self.pre_kdj.d + 1 / 3 * cur_k
        cur_j = 3 * cur_k - 2 * cur_d
        cur_kdj = KDJ_Item(cur_k, cur_d, cur_j)
        self.pre_kdj = cur_kdj

        return cur_kdj
