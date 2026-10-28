# -*- coding: utf-8 -*-
"""
端到端 + 数据源可互换离线自测（tasks 2.3 / 6.1）。

网络在沙箱不可达，无法直连 BaoStock，因此用「确定性合成日线」做等价验证：
- 生成合成 CKLine_Unit → 写入 DuckDB → CDuckDB 读回 → 与原始数据逐根比对（round-trip）。
- 分别用 DuckDB 源与「直接内存源」跑 CChan，比较笔/段/中枢/买卖点签名一致。

round-trip 逐根一致 ⟹ DuckDB 源喂给 CChan 的输入与原始源完全相同；CChan 是确定性
纯函数，输入相同 ⟹ 输出相同。两源签名再直接比对，双重印证「数据源可互换」。

运行：  .venv/bin/python Debug/test_e2e_duckdb.py
"""

import math
import os
import random
import shutil
import sys
import tempfile
import types
import datetime as dt

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from DataAPI.CommonStockAPI import CCommonStockApi
from DataAPI.DuckDBAPI import CDuckDB
from DataAPI.IngestUtil import klu_to_row
from DataAPI.KLineStore import KLineStore
from KLine.KLine_Unit import CKLine_Unit

import pandas as pd

PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ok - {name}")


# ---------------------------------------------------------------------------
# 合成日线（确定性）
# ---------------------------------------------------------------------------
def gen_bars(n=500, seed=42):
    random.seed(seed)
    bars = []
    price = 10.0
    for i in range(n):
        d = dt.date(2020, 1, 1) + dt.timedelta(days=i)
        o = price
        c = o + math.sin(i / 20.0) * 0.02 + random.uniform(-0.02, 0.02)
        hi = max(o, c) + random.uniform(0, 0.05)
        lo = min(o, c) - random.uniform(0, 0.05)
        bars.append(CKLine_Unit({
            DATA_FIELD.FIELD_TIME: CTime(d.year, d.month, d.day, 0, 0, 0, auto=False),
            DATA_FIELD.FIELD_OPEN: o,
            DATA_FIELD.FIELD_HIGH: hi,
            DATA_FIELD.FIELD_LOW: lo,
            DATA_FIELD.FIELD_CLOSE: c,
            DATA_FIELD.FIELD_VOLUME: 10000.0,
        }))
        price = c
    return bars


def klu_signature(klu):
    t = klu.time
    return (t.year, t.month, t.day, t.hour, t.minute, t.second,
            round(klu.open, 8), round(klu.high, 8), round(klu.low, 8), round(klu.close, 8),
            round(klu.trade_info.metric.get("volume") or 0.0, 6))


def chan_signature(kl):
    """抽取 CChan 单级别结果的结构化签名，用于两源比对。"""
    def bi_sig(b):
        return (str(b.dir), b.is_sure,
                b.get_begin_klu().time.to_str(), b.get_end_klu().time.to_str())

    def seg_sig(s):
        return (str(s.dir), s.is_sure,
                s.get_begin_klu().time.to_str(), s.get_end_klu().time.to_str())

    def zs_sig(z):
        return (z.begin.time.to_str(), z.end.time.to_str(),
                round(z.low, 8), round(z.high, 8), z.is_sure)

    bs = kl.bs_point_lst.getSortedBspList()
    return {
        "bi": [bi_sig(b) for b in kl.bi_list],
        "seg": [seg_sig(s) for s in kl.seg_list],
        "zs": [zs_sig(z) for z in kl.zs_list],
        "bs": sorted((str(p.type), p.is_buy, p.klu.time.to_str()) for p in bs),
    }


# ---------------------------------------------------------------------------
# 直接内存源（注入到 DataAPI 命名空间，供 custom: 机制加载）
# ---------------------------------------------------------------------------
def install_mem_source(bars):
    class CMemSource(CCommonStockApi):
        def get_kl_data(self):
            yield from bars

        def SetBasciInfo(self):
            self.name = None
            self.is_stock = None

        @classmethod
        def do_init(cls):
            pass

        @classmethod
        def do_close(cls):
            pass

    mod = types.ModuleType("DataAPI._mem_source")
    mod.CMemSource = CMemSource
    sys.modules["DataAPI._mem_source"] = mod


def run_chan(data_src):
    from Chan import CChan
    return CChan(code="sz.000001", data_src=data_src,
                 lv_list=[KL_TYPE.K_DAY], autype=AUTYPE.QFQ)


def main():
    global PASS
    PASS = 0
    bars = gen_bars()
    tmpdir = tempfile.mkdtemp(prefix="kl_e2e_")
    db_path = os.path.join(tmpdir, "kl.duckdb")
    try:
        # --- 2.3/6.1a: 写入 DuckDB 并读回，验证逐根一致 ---
        print("[round-trip] 写入 DuckDB 并读回")
        df = pd.DataFrame([klu_to_row(k, "sz.000001", KL_TYPE.K_DAY, AUTYPE.QFQ) for k in bars])
        with KLineStore(db_path) as store:
            store.upsert(df)
            n_rows = store._conn.execute("SELECT count(*) FROM kline").fetchone()[0]
        check("库中行数 = 合成 bar 数", n_rows == len(bars))

        CDuckDB.db_path = db_path
        back = list(CDuckDB(code="sz.000001", k_type=KL_TYPE.K_DAY,
                            autype=AUTYPE.QFQ).get_kl_data())
        check("读回行数一致", len(back) == len(bars))
        for i, (a, b) in enumerate(zip(bars, back)):
            if klu_signature(a) != klu_signature(b):
                check(f"第 {i} 根逐字段一致", False)
                break
        else:
            check("全部 K 线逐字段一致（时间/OHLC/成交量）", True)

        # --- 2.3/6.1b: 两源跑 CChan，签名一致 ---
        print("[equivalence] DuckDB 源 vs 直接内存源")
        sig_duck = chan_signature(run_chan("custom:DuckDBAPI.CDuckDB")[KL_TYPE.K_DAY])
        install_mem_source(bars)
        sig_mem = chan_signature(run_chan("custom:_mem_source.CMemSource")[KL_TYPE.K_DAY])

        check("笔结果一致", sig_duck["bi"] == sig_mem["bi"])
        check("段结果一致", sig_duck["seg"] == sig_mem["seg"])
        check("中枢结果一致", sig_duck["zs"] == sig_mem["zs"])
        check("买卖点结果一致", sig_duck["bs"] == sig_mem["bs"])

        # 非平凡：确有笔/段/买卖点产出，避免「两边都空」的假一致
        check("产出非平凡（有笔/段/买卖点）",
              len(sig_duck["bi"]) > 0 and len(sig_duck["seg"]) > 0 and len(sig_duck["bs"]) > 0)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\nall {PASS} checks passed")


if __name__ == "__main__":
    main()
