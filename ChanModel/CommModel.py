import abc

from CustomBuySellPoint.CustomBSP import CCustomBSP


class CCommModel:
    def __init__(self, path):
        self.load(path)

    @abc.abstractmethod
    def load(self, path):
        ...

    @abc.abstractmethod
    def predict(self, cbsp: CCustomBSP) -> float:
        ...
