"""基于 QUANTAXIS QAClickhouse 的缠论数据源。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterator, Optional, Union

import pandas as pd
from QUANTAXIS.QAFetch.QAClickhouse import QACKClient, stock_format

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi

_TimeLike = Union[datetime, date, pd.Timestamp, str]


def to_order_book_id(code: str) -> str:
    """把 chan.py / BaoStock 风格代码转为 QAClickhouse order_book_id。

    Args:
        code: 如 ``sz.000001``、``000001``、``000001.XSHE``。

    Returns:
        带 ``.XSHG`` / ``.XSHE`` / ``.XBEI`` 后缀的代码。
    """
    text = str(code).strip()
    lower = text.lower()
    if lower.startswith("sz."):
        return f"{text.split('.', 1)[1]}.XSHE"
    if lower.startswith("sh."):
        return f"{text.split('.', 1)[1]}.XSHG"
    if lower.startswith("bj."):
        return f"{text.split('.', 1)[1]}.XBEI"
    return stock_format(text)


def _parse_ctime(value: _TimeLike, *, auto: bool) -> CTime:
    """把日期/时间字段解析为 CTime。"""
    if isinstance(value, pd.Timestamp):
        return CTime(value.year, value.month, value.day, value.hour, value.minute, auto=auto)
    if isinstance(value, datetime):
        return CTime(value.year, value.month, value.day, value.hour, value.minute, auto=auto)
    if isinstance(value, date):
        return CTime(value.year, value.month, value.day, 0, 0, auto=auto)
    text = str(value).strip().replace("T", " ")
    if len(text) >= 19 and text[4] == "-":
        # 行情库本地时间无时区，按字段字面值解析
        dt = datetime.fromisoformat(text[:19])
        return CTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, auto=auto)
    if len(text) >= 10 and text[4] == "-":
        d = date.fromisoformat(text[:10])
        return CTime(d.year, d.month, d.day, 0, 0, auto=auto)
    raise CChanException(f"unknown time from clickhouse: {value}", ErrCode.SRC_DATA_TYPE_ERR)


def _row_to_klu(row: pd.Series, *, is_intraday: bool) -> CKLine_Unit:
    time_val = row.name[0] if isinstance(row.name, tuple) else row.get("datetime", row.get("date"))
    item = {
        DATA_FIELD.FIELD_TIME: _parse_ctime(time_val, auto=not is_intraday),
        DATA_FIELD.FIELD_OPEN: str2float(row["open"]),
        DATA_FIELD.FIELD_HIGH: str2float(row["high"]),
        DATA_FIELD.FIELD_LOW: str2float(row["low"]),
        DATA_FIELD.FIELD_CLOSE: str2float(row["close"]),
    }
    if "volume" in row.index and pd.notna(row["volume"]):
        item[DATA_FIELD.FIELD_VOLUME] = str2float(row["volume"])
    amount = None
    if "total_turnover" in row.index and pd.notna(row["total_turnover"]):
        amount = row["total_turnover"]
    elif "amount" in row.index and pd.notna(row["amount"]):
        amount = row["amount"]
    if amount is not None:
        item[DATA_FIELD.FIELD_TURNOVER] = str2float(amount)
    return CKLine_Unit(item)


class CQAClickhouse(CCommonStockApi):
    """从 ClickHouse（QUANTAXIS QACKClient）读取股票 K 线。"""

    _client: Optional[QACKClient] = None

    def __init__(
        self,
        code: str,
        k_type: KL_TYPE = KL_TYPE.K_DAY,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
        autype: AUTYPE = AUTYPE.QFQ,
    ) -> None:
        self.order_book_id: str = to_order_book_id(code)
        super().__init__(code, k_type, begin_date, end_date, autype)

    @classmethod
    def do_init(cls) -> None:
        if cls._client is None:
            cls._client = QACKClient()

    @classmethod
    def do_close(cls) -> None:
        cls._client = None

    @classmethod
    def _get_client(cls) -> QACKClient:
        if cls._client is None:
            cls.do_init()
        assert cls._client is not None
        return cls._client

    def SetBasciInfo(self) -> None:
        self.name = self.order_book_id
        self.is_stock = True

    def _date_range(self) -> tuple[str, str]:
        begin = self.begin_date if self.begin_date else "1990-01-01"
        if self.end_date:
            end = self.end_date
        else:
            end = datetime.now(tz=timezone.utc).astimezone().date().isoformat()
        return str(begin), str(end)

    def _min_frequence(self) -> str:
        mapping = {
            KL_TYPE.K_1M: "1min",
            KL_TYPE.K_5M: "5min",
        }
        if self.k_type not in mapping:
            raise CChanException(
                f"QAClickhouse 暂不支持级别 {self.k_type}，目前支持日线/1分钟/5分钟",
                ErrCode.PARA_ERROR,
            )
        return mapping[self.k_type]

    def _load_day_frame(self) -> pd.DataFrame:
        client = self._get_client()
        begin, end = self._date_range()
        if self.autype == AUTYPE.QFQ:
            frame = client.get_stock_day_qfq(self.order_book_id, begin, end)
            return frame if isinstance(frame, pd.DataFrame) else frame.data
        if self.autype == AUTYPE.NONE:
            return client.get_stock_day(self.order_book_id, begin, end).data
        raise CChanException(
            "QAClickhouse 数据源暂只支持 AUTYPE.QFQ / AUTYPE.NONE",
            ErrCode.PARA_ERROR,
        )

    def _load_min_frame(self) -> pd.DataFrame:
        client = self._get_client()
        begin, end = self._date_range()
        # 分钟查询需要时间粒度；仅日期时补全交易时段边界
        if len(begin) == 10:
            begin = f"{begin} 09:00:00"
        if len(end) == 10:
            end = f"{end} 15:30:00"
        frequence = self._min_frequence()
        raw = client.get_stock_min(self.order_book_id, begin, end, frequence=frequence)
        frame = raw.data
        if frame is None or frame.empty:
            return pd.DataFrame()
        if self.autype == AUTYPE.NONE:
            return frame
        if self.autype == AUTYPE.QFQ:
            # to_qfq 在空数据上会失败，已在上面拦截
            qfq = client.to_qfq(raw)
            return qfq.data if hasattr(qfq, "data") else qfq
        raise CChanException(
            "QAClickhouse 数据源暂只支持 AUTYPE.QFQ / AUTYPE.NONE",
            ErrCode.PARA_ERROR,
        )

    def get_kl_data(self) -> Iterator[CKLine_Unit]:
        """读取并 yield 单根 CKLine_Unit。"""
        is_intraday = kltype_lt_day(self.k_type)
        if self.k_type == KL_TYPE.K_DAY:
            frame = self._load_day_frame()
        elif is_intraday:
            frame = self._load_min_frame()
        else:
            raise CChanException(
                f"QAClickhouse 暂不支持级别 {self.k_type}",
                ErrCode.PARA_ERROR,
            )

        if frame is None or getattr(frame, "empty", True):
            raise CChanException(
                f"QAClickhouse 无数据: {self.order_book_id} {self.k_type} "
                f"{self.begin_date}~{self.end_date}",
                ErrCode.SRC_DATA_NOT_FOUND,
            )

        frame = frame.sort_index()
        for _, row in frame.iterrows():
            yield _row_to_klu(row, is_intraday=is_intraday)
