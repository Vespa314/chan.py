class CMean:
    def __init__(self, T=5):
        self.T = T
        self.arr = []

    def add(self, value):
        self.arr.append(value)
        if len(self.arr) > self.T:
            self.arr = self.arr[-self.T:]
        return sum(self.arr)/len(self.arr)
