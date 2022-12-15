from typing import Dict, Optional

from Common.CEnum import TRADE_INFO_LST


class CTradeInfo:
    def __init__(self, info: Dict[str, float]):
        self.metric: Dict[str, Optional[float]] = {}
        for metric_name in TRADE_INFO_LST:
            self.metric[metric_name] = info.get(metric_name)

    def __str__(self):
        return " ".join([f"{metric_name}:{value}" for metric_name, value in self.metric.items()])
