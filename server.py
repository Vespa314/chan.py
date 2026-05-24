from contextlib import contextmanager
from typing import Optional

import baostock as bs
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

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
