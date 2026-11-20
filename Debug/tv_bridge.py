"""把 CChan 的笔、线段、中枢、买卖点按图表前端的 JSON 契约提供出去。

前端 `charting_library前端完整版` 把 `/api` 代理到本服务（默认 127.0.0.1:3000）。
数据来自 ClickHouse 前复权 K 线，只读调用 CChan，不改笔、线段、中枢算法。

支持的周期：1d、1m、5m。股票代码用交易所后缀，例如 XSHE:000001 → 000001.XSHE。

启动（在 chan.py 根目录）::

    /home/tedzenghk/MyProject/quantaxis/.venv/bin/python Debug/tv_bridge.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.ChanException import CChanException

_FREQ = {
    "1d": KL_TYPE.K_DAY,
    "1m": KL_TYPE.K_1M,
    "5m": KL_TYPE.K_5M,
}
_BEGIN = {
    KL_TYPE.K_DAY: "2020-01-01",
    KL_TYPE.K_1M: "2024-12-01",
    KL_TYPE.K_5M: "2024-06-01",
}
_BSP_NAME = {
    "1": "T1",
    "1p": "T1P",
    "2": "T2",
    "2s": "T2S",
    "3a": "T3A",
    "3b": "T3B",
}
_EXCHANGE_SUFFIX = {
    "XSHE": ".XSHE",
    "SZ": ".XSHE",
    "SZSE": ".XSHE",
    "XSHG": ".XSHG",
    "SH": ".XSHG",
    "SSE": ".XSHG",
}

_lock = threading.Lock()
_cache: dict[tuple[str, str], CChan] = {}


def _order_book_id(exchange: str, symbol: str) -> str:
    symbol = symbol.strip().upper()
    exchange = exchange.strip().upper()
    if "." in symbol:
        return symbol
    suffix = _EXCHANGE_SUFFIX.get(exchange)
    if suffix is None:
        raise ValueError(f"chan.py 没有 {exchange}:{symbol} 的行情源，当前桥接只接 ClickHouse 股票（XSHE / XSHG）")
    return f"{symbol}{suffix}"


def _parse_bound(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip().replace("T", " ")
    for fmt, n in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:n], fmt).timestamp()
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {text}")


def _unix(ctime) -> int:
    return int(ctime.ts)


def _dir(up: bool) -> str:
    return "UP" if up else "DOWN"


def _finite_features(features) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in features.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out[str(key)] = number
    return out


def _load(exchange: str, symbol: str, freq: str) -> tuple[str, CChan]:
    code = _order_book_id(exchange, symbol)
    if freq not in _FREQ:
        raise ValueError(f"周期 {freq} 未接入，当前支持 {', '.join(_FREQ)}")
    key = (code, freq)
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return code, cached
        lv = _FREQ[freq]
        chan = CChan(
            code=code,
            begin_time=_BEGIN[lv],
            end_time=None,
            data_src=DATA_SRC.QAClickhouse,
            lv_list=[lv],
            config=CChanConfig({
                "trigger_step": False,
                "print_warning": False,
                "print_err_time": False,
                "bs_type": "1,1p,2,2s,3a,3b",
            }),
            autype=AUTYPE.QFQ,
        )
        _cache[key] = chan
        return code, chan


def _bars(chan: CChan, start: float | None, end: float | None, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for klc in chan[0].lst:
        for klu in klc.lst:
            t = _unix(klu.time)
            if start is not None and t < start:
                continue
            if end is not None and t > end:
                continue
            volume = klu.trade_info.metric.get("volume", 0) or 0
            rows.append({
                "t": t,
                "o": klu.open,
                "h": klu.high,
                "l": klu.low,
                "c": klu.close,
                "v": float(volume),
            })
    if limit is not None and limit > 0 and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def _overlap(t0: int, t1: int, start: float | None, end: float | None) -> bool:
    if start is not None and t1 < start:
        return False
    if end is not None and t0 > end:
        return False
    return True


def _line(idx: int, item, seg_idx: int | None) -> dict[str, Any] | None:
    try:
        t0 = _unix(item.get_begin_klu().time)
        t1 = _unix(item.get_end_klu().time)
    except (AssertionError, AttributeError, IndexError):
        return None
    body = {
        "dir": _dir(item.is_up()),
        "t0": t0,
        "p0": item.get_begin_val(),
        "t1": t1,
        "p1": item.get_end_val(),
        "sure": bool(item.is_sure),
    }
    if seg_idx is None:
        body["id"] = idx
        body["zs_count"] = len(item.zs_lst)
        body["element_count"] = len(item.bi_list)
    else:
        body["idx"] = idx
        body["seg_idx"] = seg_idx if seg_idx >= 0 else None
    return body


def _zs(idx: int, zs) -> dict[str, Any] | None:
    try:
        t0 = _unix(zs.begin.time)
        t1 = _unix(zs.end.time)
    except (AssertionError, AttributeError):
        return None
    elements = getattr(zs, "bi_lst", None) or []
    return {
        "idx": idx,
        "dir": "UP",
        "t0": t0,
        "t1": t1,
        "low": zs.low,
        "high": zs.high,
        "peak_low": zs.peak_low,
        "peak_high": zs.peak_high,
        "is_sure": bool(zs.is_sure),
        "sub_zs_count": len(zs.sub_zs_lst),
        "element_count": len(elements),
    }


def _bsp(point, is_segbsp: bool) -> dict[str, Any]:
    return {
        "element_idx": point.bi.idx,
        "klu_idx": point.klu.idx,
        "t": _unix(point.klu.time),
        "is_buy": bool(point.is_buy),
        "is_segbsp": is_segbsp,
        "is_target": True,
        "types": [_BSP_NAME.get(tp.value, tp.value.upper()) for tp in point.type],
        "features": _finite_features(point.features),
    }


def _slice(items: list[dict[str, Any]], start: float | None, end: float | None) -> list[dict[str, Any]]:
    return [item for item in items if _overlap(item["t0"], item["t1"], start, end)]


def _chan_slice(code: str, freq: str, chan: CChan, start: float | None, end: float | None) -> dict[str, Any]:
    kl = chan[0]
    bis = []
    for bi in kl.bi_list:
        row = _line(bi.idx, bi, bi.parent_seg.idx if bi.parent_seg is not None else -1)
        if row is not None:
            bis.append(row)
    segs = []
    for seg in kl.seg_list:
        row = _line(seg.idx, seg, None)
        if row is not None:
            segs.append(row)
    zs = [row for i, item in enumerate(kl.zs_list) if (row := _zs(i, item)) is not None]
    segzs = [row for i, item in enumerate(kl.segzs_list) if (row := _zs(i, item)) is not None]
    bsps = [_bsp(p, False) for p in kl.bs_point_lst.getSortedBspList()]
    seg_bsps = [_bsp(p, True) for p in kl.seg_bs_point_lst.getSortedBspList()]
    return {
        "symbol": code,
        "freq": freq,
        "bis": _slice(bis, start, end),
        "segs": _slice(segs, start, end),
        "zs": _slice(zs, start, end),
        "segzs": _slice(segzs, start, end),
        "bsps": [p for p in bsps if (start is None or p["t"] >= start) and (end is None or p["t"] <= end)],
        "seg_bsps": [p for p in seg_bsps if (start is None or p["t"] >= start) and (end is None or p["t"] <= end)],
    }


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/health":
                self._send(200, {"ok": True, "data_root": "chan.py QAClickhouse"})
                return
            if path == "/symbols":
                self._send(200, {"symbols": [
                    {"exchange": "XSHE", "symbol": "000001", "name": "平安银行", "freqs": ["1d", "1m", "5m"]},
                    {"exchange": "XSHG", "symbol": "000300", "name": "沪深300", "freqs": ["1d"]},
                ]})
                return
            if path == "/backtest/strategies":
                self._send(200, {"strategies": []})
                return
            if path in ("/bars", "/chan"):
                exchange = qs.get("exchange", ["XSHE"])[0]
                symbol = qs.get("symbol", [""])[0]
                freq = qs.get("freq", ["1d"])[0]
                start = _parse_bound(qs.get("from", [None])[0])
                end = _parse_bound(qs.get("to", [None])[0])
                code, chan = _load(exchange, symbol, freq)
                if path == "/bars":
                    limit_text = qs.get("limit", [None])[0]
                    limit = int(limit_text) if limit_text else None
                    rows = _bars(chan, start, end, limit)
                    self._send(200, {"symbol": code, "freq": freq, "n": len(rows), "bars": rows})
                else:
                    self._send(200, _chan_slice(code, freq, chan, start, end))
                return
            self._send(404, {"error": f"未知路径 {path}"})
        except (CChanException, ValueError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    host = "127.0.0.1"
    port = 3000
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"tv_bridge listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
