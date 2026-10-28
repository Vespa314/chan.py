"""
KLineStore —— 原始 K 线的本地持久化层（DuckDB 单文件）。

职责：把 DataAPI 适配器拉到的原始 K 线（OHLCV + 时间 + code/kl_type/autype 元信息）
落盘到本地 DuckDB 单文件，并提供幂等写入（INSERT OR REPLACE）与区间查询。

本模块只做「存储」，不负责拉取（拉取复用既有 BaoStock/Akshare 适配器，见
Debug/download_kl.py）与回读（回读见 DataAPI/DuckDBAPI.py 的 CDuckDB 适配器）。

设计约定（对应 openspec 变更 persist-kl-to-duckdb 的 design.md）：
- 一行 = 一根 K 线，主键为 (code, kl_type, autype, time_key)。
- kl_type / autype 存枚举的 `.name` 字符串（如 "K_DAY" / "QFQ"），由读适配器还原为枚举。
- time_key 存规范化的「无时区北京时间」字符串 "YYYY-MM-DD HH:MM:SS"（而非 TIMESTAMP），
  以便日线（时分秒均为 0）与分钟线都能无损往返，且不受 DuckDB TIMESTAMP 隐式时区影响。
"""

import pandas as pd

# DuckDB 为可选依赖，仅在使用 KLineStore 时才会 import；延迟导入避免无依赖场景报错。
import duckdb

# 字段顺序固定，upsert 与 query 均按此对齐。
# 默认 DuckDB 单文件路径（灌数脚本与读适配器共用；可用 KLineStore 构造参数覆盖）。
DEFAULT_DB_PATH = "kl_store.duckdb"

_TIME_KEY = "time_key"
_COLUMNS = [
    "code",
    "kl_type",
    "autype",
    _TIME_KEY,
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
    "turnover_rate",
]

_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS kline (
  code          VARCHAR,
  kl_type       VARCHAR,
  autype        VARCHAR,
  time_key      VARCHAR,
  open          DOUBLE,
  high          DOUBLE,
  low           DOUBLE,
  close         DOUBLE,
  volume        DOUBLE,
  turnover      DOUBLE,
  turnover_rate DOUBLE,
  PRIMARY KEY (code, kl_type, autype, time_key)
)
"""


def ctime_to_str(ct) -> str:
    """把 CTime（含 year/month/day/hour/minute/second 字段）序列化为规范化时间字符串。

    CTime 有 `auto` 语义：日线的 hour/minute/second 均为 0，`to_str()` 会省略时间部分。
    这里统一补零输出完整 "YYYY-MM-DD HH:MM:SS"，保证读回时能精确重建字段。
    """
    return (
        f"{ct.year:04d}-{ct.month:02d}-{ct.day:02d} "
        f"{ct.hour:02d}:{ct.minute:02d}:{ct.second:02d}"
    )


def str_to_ctime(s: str):
    """把 ctime_to_str 产出的字符串还原为 CTime。仅在读适配器需要时调用。

    使用 auto=True（CTime 默认），与 BaoStock 的 `parse_time_column` 一致：
    日线（时分秒为 0）读回后时间戳落在当日 23:59:59，从而在多级别分析中正确
    成为当日分钟线的父级。若用 auto=False 则日线时间戳停在 00:00:00，会排在
    当日分钟线之前，破坏父子对齐。
    """
    from Common.CTime import CTime

    date_part, time_part = str(s).split(" ")
    year, month, day = (int(x) for x in date_part.split("-"))
    hour, minute, second = (int(x) for x in time_part.split(":"))
    return CTime(year, month, day, hour, minute, second, auto=True)


def _normalize_time(value, is_end: bool = False) -> str:
    """把用户传入的区间边界规范化为 time_key 字符串。

    - "YYYY-MM-DD"（纯日期）：begin 补为 "00:00:00"，end 补为 "23:59:59"，
      使日期边界能覆盖当日全部 bar（含分钟线）。
    - 已是 "YYYY-MM-DD HH:MM:SS" 则原样返回。
    """
    s = str(value).strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s + (" 23:59:59" if is_end else " 00:00:00")
    return s


class KLineStore:
    """K 线存储：打开/创建 DuckDB 单文件，建表，提供 upsert 与 query。"""

    def __init__(self, db_path: str):
        # duckdb.connect 对不存在的路径会自动创建文件；read_only 默认 False。
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_TABLE_SCHEMA)

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def upsert(self, df: pd.DataFrame) -> int:
        """幂等写入：按主键 (code, kl_type, autype, time_key) 去重，后写覆盖前写。

        返回实际写入行数（INSERT OR REPLACE 对重复键亦计为一行）。
        入参 DataFrame 需包含 _COLUMNS 中的列；缺失列以 NULL 填充。
        """
        if df is None or len(df) == 0:
            return 0
        # 对齐列序，缺失列补 NULL，多余列丢弃。
        normalized = df.reindex(columns=_COLUMNS)
        self._conn.register("_upsert_df", normalized)
        self._conn.execute(
            "INSERT OR REPLACE INTO kline SELECT * FROM _upsert_df"
        )
        self._conn.unregister("_upsert_df")
        return len(normalized)

    def query(self, code, kl_type, autype, begin=None, end=None) -> pd.DataFrame:
        """按 code/kl_type/autype 与可选时间区间查询，按 time_key 升序返回。

        begin/end 支持纯日期（补零/补满）或完整时间字符串。
        """
        params = [code, kl_type, autype]
        where = "WHERE code = ? AND kl_type = ? AND autype = ?"
        if begin is not None:
            where += " AND time_key >= ?"
            params.append(_normalize_time(begin, is_end=False))
        if end is not None:
            where += " AND time_key <= ?"
            params.append(_normalize_time(end, is_end=True))
        sql = f"SELECT {', '.join(_COLUMNS)} FROM kline {where} ORDER BY time_key"
        return self._conn.execute(sql, params).fetchdf()

    def delete(self, code, kl_type, autype, begin=None, end=None) -> int:
        """删除某 (code, kl_type, autype) 的全部或指定区间 K 线。

        用于 --full 全量重刷与 --begin/--end 区间重刷。返回被删除行数。
        """
        params = [code, kl_type, autype]
        where = "code = ? AND kl_type = ? AND autype = ?"
        if begin is not None:
            where += " AND time_key >= ?"
            params.append(_normalize_time(begin, is_end=False))
        if end is not None:
            where += " AND time_key <= ?"
            params.append(_normalize_time(end, is_end=True))
        cnt = self._conn.execute(f"SELECT count(*) FROM kline WHERE {where}", params).fetchone()[0]
        self._conn.execute(f"DELETE FROM kline WHERE {where}", params)
        return cnt

    def max_time_key(self, code, kl_type, autype):
        """返回某 (code, kl_type, autype) 当前最新的 time_key，作为断点续拉的水位。

        无任何数据时返回 None。
        """
        row = self._conn.execute(
            "SELECT max(time_key) FROM kline WHERE code = ? AND kl_type = ? AND autype = ?",
            [code, kl_type, autype],
        ).fetchone()
        return row[0] if row else None
