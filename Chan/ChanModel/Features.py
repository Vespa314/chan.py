from typing import Optional


class CFeatures:
    def __init__(self, initFeat=None):
        self.__features = {} if initFeat is None else dict(initFeat)

    def items(self):
        yield from self.__features.items()

    def __getitem__(self, k):
        return self.__features[k]

    def add_feat(self, inp1, inp2: Optional[float] = None):
        if inp2 is None:
            self.__features.update(inp1)
        else:
            self.__features.update({inp1: inp2})
