from dataSrc.CommonStockAPI import CCommonStockApi, TRADE_INFO_LST


class CTradeInfo:
    def __init__(self, info: dict):
        self.metric = {}
        self.od_score = {}
        self.od_mean = {}
        for metric_name in TRADE_INFO_LST:
            self.metric[metric_name] = info.get(metric_name, None)
            self.od_score[metric_name] = None
            self.od_mean[metric_name] = None

    def __str__(self):
        return " ".join([f"{metric_name}:{value}" for metric_name, value in self.metric.items()])

    def toJson(self):
        return {
            "metric": self.metric,
            "od_score": self.od_score,
        }

    def update_od(self, tradeinfo_outlinerdetection_dict: dict) -> None:
        for metric_name, model in tradeinfo_outlinerdetection_dict.items():
            self.od_score[metric_name] = model.add(self.metric[metric_name])
            self.od_mean[metric_name] = model.mean

    def getOutlinearScore(self):
        return {
            "volume_outlinear_score": self.od_score[CCommonStockApi.FIELD_VOLUME],
            "turnover_outlinear_score": self.od_score[CCommonStockApi.FIELD_TURNOVER],
            "turnover_rate_outlinear_score": self.od_score[CCommonStockApi.FIELD_TURNRATE],
            "turnover_rate": self.metric[CCommonStockApi.FIELD_TURNRATE],
        }
