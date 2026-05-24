from contextlib import contextmanager
from typing import Optional

import baostock as bs
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

app = FastAPI(title="缠论免画图网站")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@contextmanager
def bao_login():
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: {lg.error_msg}")
    try:
        yield
    finally:
        bs.logout()


@app.get("/api/chan")
def chan_analysis(code: str = None, start: str = ""):
    if not code:
        return JSONResponse({"error": "缺少股票代码参数"}, status_code=400)

    try:
        config = CChanConfig({
            "bi_strict": True,
            "divergence_rate": float("inf"),
            "trigger_step": False,
            "zs_algo": "normal",
        })

        chan = CChan(
            code=code,
            begin_time=start or None,
            end_time=None,
            data_src=DATA_SRC.BAO_STOCK,
            lv_list=[KL_TYPE.K_DAY],
            config=config,
            autype=AUTYPE.QFQ,
        )
    except Exception:
        return JSONResponse({"error": "未找到该股票或无交易数据"}, status_code=404)

    kl_list = chan[KL_TYPE.K_DAY]
    klines_raw = kl_list.lst

    klines = []
    for kl in klines_raw:
        for unit in kl:
            klines.append({
                "time": unit.time.to_str(),
                "open": round(unit.open, 2),
                "high": round(unit.high, 2),
                "low": round(unit.low, 2),
                "close": round(unit.close, 2),
            })

    bi_list = []
    for bi in kl_list.bi_list:
        bi_list.append({
            "startIdx": bi.get_begin_klu().idx,
            "endIdx": bi.get_end_klu().idx,
            "dir": "up" if bi.is_up() else "down",
            "startVal": round(bi.get_begin_val(), 2),
            "endVal": round(bi.get_end_val(), 2),
            "isSure": bi.is_sure,
            "idx": bi.idx,
        })

    seg_list = []
    for seg in kl_list.seg_list:
        seg_list.append({
            "startIdx": seg.start_bi.get_begin_klu().idx,
            "endIdx": seg.end_bi.get_end_klu().idx,
            "dir": "up" if seg.is_up() else "down",
            "startVal": round(seg.get_begin_val(), 2),
            "endVal": round(seg.get_end_val(), 2),
            "isSure": seg.is_sure,
            "idx": seg.idx,
        })

    zs_list = []
    for zs in kl_list.zs_list:
        zs_list.append({
            "startIdx": zs.begin.idx,
            "endIdx": zs.end.idx,
            "low": round(zs.low, 2),
            "high": round(zs.high, 2),
            "isSure": zs.is_sure,
        })

    macd_list = []
    for kl in klines_raw:
        for unit in kl:
            macd_list.append({
                "idx": unit.idx,
                "dif": round(unit.macd.DIF, 4),
                "dea": round(unit.macd.DEA, 4),
                "macd": round(unit.macd.macd, 4),
            })

    bsp_list = []
    for bsp in kl_list.bs_point_lst.bsp_iter():
        bsp_list.append({
            "idx": bsp.klu.idx,
            "isBuy": bsp.is_buy,
            "type": bsp.type2str(),
            "price": round(bsp.klu.low if bsp.is_buy else bsp.klu.high, 2),
            "date": bsp.klu.time.to_str(),
        })

    return {
        "code": code,
        "klines": klines,
        "bi": bi_list,
        "seg": seg_list,
        "zs": zs_list,
        "macd": macd_list,
        "bsp": bsp_list,
    }


@app.get("/api/search")
def search_stock(q: Optional[str] = None):
    if not q or not q.strip():
        return JSONResponse({"error": "请输入搜索关键词"}, status_code=400)

    try:
        with bao_login():
            rs = bs.query_stock_basic(code_name=q)
            results = []
            while rs.next():
                row = rs.get_row_data()
                results.append(f"{row[0]} {row[1]}")
        return results
    except RuntimeError as e:
        return JSONResponse({"error": f"数据源连接失败: {str(e)}"}, status_code=503)
    except Exception:
        return JSONResponse({"error": "查询失败，请稍后重试"}, status_code=500)
