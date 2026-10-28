# -*- coding: utf-8 -*-
"""
DuckDB 数据API模块 - 从本地 DuckDB 单文件读取已持久化的原始 K 线。

与 BaoStock/Akshare 等网络适配器不同，本适配器不请求网络，而是查询
KLineStore 建好的 `kline` 表，把结果逐根还原为 CKLine_Unit。因此 CChan
的计算流水线对数据来源完全无感知：只要把 data_src 切为
`"custom:DuckDBAPI.CDuckDB"` 即可离线复算，结果应与网络源一致。

接入方式（见 design.md D3）：
    chan = CChan(code="sz.000001", data_src="custom:DuckDBAPI.CDuckDB", ...)
    # 可选：指定库路径（须与 Debug/download_kl.py 写入的路径一致）
    CDuckDB.db_path = "kl_store.duckdb"

可配置属性：
- db_path: DuckDB 单文件路径，类属性，默认取 KLineStore.DEFAULT_DB_PATH。
"""

import math
from enum import Enum

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi
from .KLineStore import DEFAULT_DB_PATH, KLineStore, str_to_ctime


def _to_name(x):
    """把枚举或字符串规范化为其 `.name`（如 KL_TYPE.K_DAY -> "K_DAY"）。

    读库时 `kl_type`/`autype` 通常由 CChan 以枚举实例传入，这里统一转成
    存储时使用的 `.name` 字符串；若调用方直接传字符串则原样返回。
    """
    return x.name if isinstance(x, Enum) else str(x)


class CDuckDB(CCommonStockApi):
    """
    DuckDB 数据源实现 - 从本地库读取 K 线。

    参数与 CCommonStockApi 一致：
        code: 股票代码（如 "sz.000001"）
        k_type: K线级别（KL_TYPE 枚举）
        begin_date/end_date: 可选时间区间（纯日期或完整时间字符串）
        autype: 复权类型（AUTYPE 枚举）
    """

    db_path = DEFAULT_DB_PATH  # 类属性，使用前可覆盖

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(CDuckDB, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """
        从 DuckDB 查询并按时间升序逐根 yield CKLine_Unit。

        处理逻辑：
        1. 以 (code, k_type.name, autype.name) 定位数据子集
        2. 按 [begin, end] 过滤
        3. 每行还原为 {字段名: 值} 字典，构造 CKLine_Unit
        4. 交易信息（volume/turnover/turnover_rate）仅在非空时注入，
           与 BaoStock 分钟线无交易信息的行为一致
        """
        with KLineStore(self.db_path) as store:
            df = store.query(
                self.code,
                _to_name(self.k_type),
                _to_name(self.autype),
                self.begin_date,
                self.end_date,
            )
        for _, row in df.iterrows():
            yield CKLine_Unit(self._row_to_dict(row))

    def _row_to_dict(self, row) -> dict:
        """把一行查询结果还原为 CKLine_Unit 构造所需的字典。"""
        d = {
            DATA_FIELD.FIELD_TIME: str_to_ctime(row["time_key"]),
            DATA_FIELD.FIELD_OPEN: row["open"],
            DATA_FIELD.FIELD_HIGH: row["high"],
            DATA_FIELD.FIELD_LOW: row["low"],
            DATA_FIELD.FIELD_CLOSE: row["close"],
        }
        for field in (
            DATA_FIELD.FIELD_VOLUME,
            DATA_FIELD.FIELD_TURNOVER,
            DATA_FIELD.FIELD_TURNRATE,
        ):
            v = row[field]
            # None / NaN 均视为「无交易信息」，与分钟线场景一致
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            d[field] = v
        return d

    def SetBasciInfo(self):
        """本地库不存股票名称/是否个股，置空即可（CChan 不消费这两个字段）。"""
        self.name = None
        self.is_stock = None

    @classmethod
    def do_init(cls):
        """无登录/连接需要，空实现。"""
        pass

    @classmethod
    def do_close(cls):
        """无连接需要清理，空实现。"""
        pass
