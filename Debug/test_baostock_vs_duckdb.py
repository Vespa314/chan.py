# -*- coding: utf-8 -*-
"""
数据源可互换 + 端到端的真网络冒烟测试（tasks 2.3 / 6.1，需联网）。

流程完全复刻 tasks 6.1：下载（BaoStock）→ 灌数（DuckDB）→ 以 DuckDB 源离线跑 CChan
出买卖点，与 BaoStock 源同参数结果一致。与 Debug/test_e2e_duckdb.py 的离线合成版
互为印证（那个不依赖网络，本脚本验证真实 BaoStock 数据路径）。

运行（需能访问 BaoStock）：  .venv/bin/python Debug/test_baostock_vs_duckdb.py
"""

import os
import shutil
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import pandas as pd

from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock
from DataAPI.DuckDBAPI import CDuckDB
from DataAPI.IngestUtil import klu_to_row
from DataAPI.KLineStore import KLineStore

CODE = "sz.000001"
K_TYPE = KL_TYPE.K_DAY
AU = AUTYPE.QFQ
BEGIN = "2020-01-01"  # 固定起始，保证两源取同一区间、结果可复现

PASS = 0


def check(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ok - {name}")


def chan_signature(kl):
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


def run_chan(data_src):
    from Chan import CChan
    return CChan(code=CODE, begin_time=BEGIN, end_time=None,
                 data_src=data_src, lv_list=[K_TYPE], autype=AU)


def main():
    global PASS
    PASS = 0
    tmpdir = tempfile.mkdtemp(prefix="kl_bao_")
    db_path = os.path.join(tmpdir, "kl.duckdb")
    try:
        # 1) 下载：BaoStock 拉取原始 K 线
        print("[下载] BaoStock 拉取", CODE, K_TYPE.name, AU.name)
        CBaoStock.do_init()
        try:
            orig = list(CBaoStock(code=CODE, k_type=K_TYPE, begin_date=BEGIN,
                                  end_date=None, autype=AU).get_kl_data())
        finally:
            CBaoStock.do_close()
        check("拉到原始 K 线", len(orig) > 0)
        print(f"    拉取 {len(orig)} 根")

        # 2) 灌数：写入 DuckDB
        print("[灌数] 写入 DuckDB")
        df = pd.DataFrame([klu_to_row(k, CODE, K_TYPE, AU) for k in orig])
        with KLineStore(db_path) as store:
            store.upsert(df)

        # 3) 两源跑 CChan 比对
        print("[比对] DuckDB 源 vs BaoStock 源")
        CDuckDB.db_path = db_path
        sig_duck = chan_signature(run_chan("custom:DuckDBAPI.CDuckDB")[K_TYPE])
        sig_bao = chan_signature(run_chan(DATA_SRC.BAO_STOCK)[K_TYPE])

        check("笔结果一致", sig_duck["bi"] == sig_bao["bi"])
        check("段结果一致", sig_duck["seg"] == sig_bao["seg"])
        check("中枢结果一致", sig_duck["zs"] == sig_bao["zs"])
        check("买卖点结果一致", sig_duck["bs"] == sig_bao["bs"])
        check("产出非平凡（有笔/段/买卖点）",
              len(sig_duck["bi"]) > 0 and len(sig_duck["seg"]) > 0 and len(sig_duck["bs"]) > 0)
        print(f"    笔 {len(sig_duck['bi'])} / 段 {len(sig_duck['seg'])} / "
              f"中枢 {len(sig_duck['zs'])} / 买卖点 {len(sig_duck['bs'])}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\nall {PASS} checks passed")


if __name__ == "__main__":
    main()
