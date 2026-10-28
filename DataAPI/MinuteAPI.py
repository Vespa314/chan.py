# -*- coding: utf-8 -*-
"""
分钟级数据源适配器 - 使用 akshare（东方财富）拉取 A 股分钟 K 线。

BaoStock 的分钟数据偏历史、有延迟，盘中准实时分钟线走 Akshare 的
`stock_zh_a_hist_min_em` 接口（东财）。本适配器与 CBaoStock 同构，
继承 CCommonStockApi，可直接经 `custom:MinuteAPI.CMinute` 接入 CChan，
也可被盘中轮询引擎（Debug/intraday_poll.py）复用。

akshare 为可选依赖：仅在实际调用 get_kl_data 时才 import，避免无 akshare
环境下 import 本模块即报错。
"""

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def _parse_time(val) -> CTime:
    """把 akshare 分钟线的时间列（"YYYY-MM-DD HH:MM:SS" 或 pd.Timestamp）解析为 CTime。"""
    if hasattr(val, "year"):  # pd.Timestamp / datetime
        return CTime(val.year, val.month, val.day, val.hour, val.minute, val.second, auto=False)
    s = str(val)
    date_part, time_part = s.split(" ")
    year, month, day = (int(x) for x in date_part.split("-"))
    hour, minute, second = (int(x) for x in time_part.split(":"))
    return CTime(year, month, day, hour, minute, second, auto=False)


def _create_item_dict(row) -> dict:
    """把 akshare 分钟线一行转成 CKLine_Unit 所需的字典。"""
    d = {
        DATA_FIELD.FIELD_TIME: _parse_time(row["时间"]),
        DATA_FIELD.FIELD_OPEN: str2float(row["开盘"]),
        DATA_FIELD.FIELD_HIGH: str2float(row["最高"]),
        DATA_FIELD.FIELD_LOW: str2float(row["最低"]),
        DATA_FIELD.FIELD_CLOSE: str2float(row["收盘"]),
    }
    if "成交量" in row:
        d[DATA_FIELD.FIELD_VOLUME] = str2float(row["成交量"])
    if "成交额" in row:
        d[DATA_FIELD.FIELD_TURNOVER] = str2float(row["成交额"])
    return d


class CMinute(CCommonStockApi):
    """
    分钟级数据源（akshare 东方财富）。

    仅支持分钟级别（K_5M/K_15M/K_30M/K_60M），不支持日线及以上。
    """

    _PERIOD = {
        KL_TYPE.K_5M: "5",
        KL_TYPE.K_15M: "15",
        KL_TYPE.K_30M: "30",
        KL_TYPE.K_60M: "60",
    }

    def __init__(self, code, k_type=KL_TYPE.K_5M, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CMinute, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """
        拉取分钟 K 线（生成器）。akshare 延迟导入，仅在调用时加载。
        """
        if self.k_type not in self._PERIOD:
            raise Exception(f"MinuteAPI 仅支持分钟级别，不支持 {self.k_type}")

        import akshare as ak

        adjust = {AUTYPE.QFQ: "qfq", AUTYPE.HFQ: "hfq", AUTYPE.NONE: ""}.get(self.autype, "")
        # akshare 东财分钟接口 symbol 为 6 位纯数字（去 sz./sh. 前缀）
        symbol = self.code.replace("sz.", "").replace("sh.", "")
        start = self.begin_date or "1970-01-01 09:30:00"
        end = self.end_date or "2099-12-31 15:00:00"
        df = ak.stock_zh_a_hist_min_em(
            symbol=symbol, period=self._PERIOD[self.k_type],
            start_date=start, end_date=end, adjust=adjust,
        )
        for _, row in df.iterrows():
            yield CKLine_Unit(_create_item_dict(row))

    def SetBasciInfo(self):
        """复用 akshare 的股票/指数判断逻辑。"""
        self.name = self.code
        code_num = self.code.replace("sz.", "").replace("sh.", "")
        self.is_stock = not (code_num.startswith("000") or code_num.startswith("399"))

    @classmethod
    def do_init(cls):
        """akshare 无需登录。"""
        pass

    @classmethod
    def do_close(cls):
        """akshare 无需登出。"""
        pass
