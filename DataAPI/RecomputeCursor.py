# -*- coding: utf-8 -*-
"""
重算游标 - 把「已处理时间」操作态持久化到 PostgreSQL。

D14 的库分工：K 线分析数据落 DuckDB，操作态（重算游标、任务状态）落 PG。
重算进程每处理完一批新 bar 就推进 `last_processed_time`，存 PG（而非写回
DuckDB 的 kline 库，避免与灌数进程抢 DuckDB 单写锁）。

游标表以 (code, kl_type, autype) 为主键，与 kline 表的标识维度一致（缺 time_key）。
"""

import psycopg2

_TABLE = "recompute_cursor"
_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
  code                VARCHAR,
  kl_type             VARCHAR,
  autype              VARCHAR,
  last_processed_time VARCHAR,
  PRIMARY KEY (code, kl_type, autype)
)
"""


class RecomputeCursor:
    """PG 后端游标；get/set 语义与内存版 MemoryCursor 一致，便于测试替换。"""

    def __init__(self, dsn):
        self.dsn = dsn
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA)
            conn.commit()

    def _connect(self):
        return psycopg2.connect(self.dsn)

    def get(self, code, kl_type, autype):
        """返回某 (code, kl_type, autype) 的 last_processed_time，无记录返回 None。"""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT last_processed_time FROM {_TABLE} WHERE code=%s AND kl_type=%s AND autype=%s",
                    (code, kl_type, autype),
                )
                row = cur.fetchone()
        return row[0] if row else None

    def set(self, code, kl_type, autype, time_key):
        """upsert 游标（后写覆盖）。"""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {_TABLE} (code, kl_type, autype, last_processed_time)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (code, kl_type, autype)
                    DO UPDATE SET last_processed_time = EXCLUDED.last_processed_time
                    """,
                    (code, kl_type, autype, time_key),
                )
            conn.commit()


class MemoryCursor:
    """内存版游标（本地测试/无 PG 环境降级用），与 RecomputeCursor 同接口。"""

    def __init__(self):
        self._store = {}

    def get(self, code, kl_type, autype):
        return self._store.get((code, kl_type, autype))

    def set(self, code, kl_type, autype, time_key):
        self._store[(code, kl_type, autype)] = time_key
