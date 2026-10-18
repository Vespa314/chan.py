"""从决策收盘价向后看的三屏障。同一根 K 线同时碰到上下屏障时，按下屏障处理。"""

from __future__ import annotations

from dataclasses import dataclass

from Research.config import (
    HORIZON_PRIMARY,
    HORIZON_SENSITIVITY,
    LOWER_RETURN,
    SIDE_COST,
    UPPER_RETURN,
)


@dataclass
class BarrierExit:
    reason: str
    time: str
    price: float
    label: int


def net_return(entry: float, exit_price: float, side_cost: float = SIDE_COST) -> float:
    """往返各扣一次单边成本。"""
    return exit_price / entry - 1.0 - 2.0 * side_cost


class PendingBuy:
    """一只股票上尚未走完观察窗口的买点。特征在创建时已经冻结，这里只追加之后的 K 线。"""

    def __init__(
        self,
        entry: float,
        upper: float = UPPER_RETURN,
        lower: float = LOWER_RETURN,
        upper_zs: float | None = None,
        horizons: tuple[int, ...] = (HORIZON_PRIMARY, HORIZON_SENSITIVITY),
    ):
        self.entry = entry
        self.upper_px = entry * (1.0 + upper)
        self.lower_px = entry * (1.0 - lower)
        self.upper_zs_px = None if upper_zs is None else entry * (1.0 + upper_zs)
        self.horizons = horizons
        self.bars: list[dict] = []
        self.trade: dict[int, BarrierExit | None] = {h: None for h in horizons}
        self.barrier: dict[int, BarrierExit | None] = {h: None for h in horizons}
        self.barrier_zs: BarrierExit | None = None

    def add_bar(self, time: str, high: float, low: float, close: float, sell_price: float | None = None) -> None:
        self.bars.append({"time": time, "high": high, "low": low, "close": close})
        n = len(self.bars)
        for horizon in self.horizons:
            if n > horizon:
                continue
            if self.barrier[horizon] is None:
                self.barrier[horizon] = self._resolve(
                    high, low, close, time, n, horizon, self.upper_px, sell_price=None,
                )
            if self.trade[horizon] is None:
                self.trade[horizon] = self._resolve(
                    high, low, close, time, n, horizon, self.upper_px, sell_price=sell_price,
                )
        if (
            HORIZON_PRIMARY in self.horizons
            and n <= HORIZON_PRIMARY
            and self.barrier_zs is None
            and self.upper_zs_px is not None
        ):
            self.barrier_zs = self._resolve(
                high, low, close, time, n, HORIZON_PRIMARY, self.upper_zs_px, sell_price=None,
            )

    def _resolve(
        self,
        high: float,
        low: float,
        close: float,
        time: str,
        n: int,
        horizon: int,
        upper_px: float,
        sell_price: float | None,
    ) -> BarrierExit | None:
        # 同一根 K 线没有路径顺序。先碰到下屏障，避免把日内振幅记成盈利。
        if low <= self.lower_px:
            return BarrierExit("lower", time, self.lower_px, 0)
        if high >= upper_px:
            return BarrierExit("upper", time, upper_px, 1)
        if sell_price is not None:
            return BarrierExit("sell", time, sell_price, 0)
        if n == horizon:
            return BarrierExit("time", time, close, 0)
        return None

    def _horizon_end(self, horizon: int) -> str:
        if len(self.bars) < horizon:
            return ""
        return self.bars[horizon - 1]["time"]

    def _excursion(self, horizon: int) -> tuple[float, float, float]:
        window = self.bars[:horizon]
        if not window or self.entry == 0:
            return float("nan"), float("nan"), float("nan")
        mfe = max(bar["high"] for bar in window) / self.entry - 1.0
        mae = min(bar["low"] for bar in window) / self.entry - 1.0
        if len(window) < horizon:
            return mfe, mae, float("nan")
        forward = window[-1]["close"] / self.entry - 1.0
        return mfe, mae, forward

    def _path(self, horizon: int) -> str:
        return "|".join(f"{bar['time']}:{bar['close']}" for bar in self.bars[:horizon])

    def outcome(self) -> dict:
        """标签与交易结果。未走完窗口的收益留空，调用方丢弃这些样本。"""
        row: dict = {"obs_bars": len(self.bars)}
        for horizon in self.horizons:
            barrier = self.barrier[horizon]
            trade = self.trade[horizon]
            mfe, mae, forward = self._excursion(horizon)
            # 时间到期必须凑满窗口；提前碰到屏障则结论已经确定。
            if barrier is None or trade is None:
                complete = 0
            elif barrier.reason == "time" or trade.reason == "time":
                complete = int(len(self.bars) >= horizon)
            else:
                complete = 1
            prefix = f"_{horizon}"
            row[f"complete{prefix}"] = complete
            row[f"label{prefix}"] = None if barrier is None else barrier.label
            row[f"barrier_reason{prefix}"] = None if barrier is None else barrier.reason
            row[f"exit_reason{prefix}"] = None if trade is None else trade.reason
            row[f"exit_time{prefix}"] = None if trade is None else trade.time
            row[f"exit_price{prefix}"] = None if trade is None else trade.price
            row[f"net_return{prefix}"] = None if trade is None else net_return(self.entry, trade.price)
            row[f"forward_return{prefix}"] = forward
            row[f"mfe{prefix}"] = mfe
            row[f"mae{prefix}"] = mae
            row[f"horizon_end{prefix}"] = self._horizon_end(horizon)
            row[f"path{prefix}"] = self._path(horizon)
        zs = self.barrier_zs
        row["label_zs_10"] = None if zs is None else zs.label
        row["barrier_zs_reason_10"] = None if zs is None else zs.reason
        return row
