from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    trades: int
    win_rate: float
    net_return_pct: float
    max_drawdown_pct: float
    profit_factor: float
    average_trade_pct: float
    equity_curve: pd.Series

    @property
    def profit_factor_label(self) -> str:
        return "∞" if np.isinf(self.profit_factor) else f"{self.profit_factor:.2f}"


def run_backtest(
    df: pd.DataFrame,
    fee_pct: float = 0.10,
    slippage_pct: float = 0.05,
    allocation_pct: float = 25.0,
    leverage: int = 1,
    allow_short: bool = False,
    max_hold_hours: int = 48,
) -> BacktestResult:
    equity = 1.0
    curve: list[tuple[pd.Timestamp, float]] = [(df.index[0], equity)]
    returns: list[float] = []
    i = 0
    one_way_cost = (fee_pct + slippage_pct) / 100

    while i < len(df) - 2:
        setup = df.iloc[i]
        if bool(setup["long_setup"]):
            direction = 1
        elif allow_short and bool(setup["short_setup"]):
            direction = -1
        else:
            i += 1
            continue
        entry_i = i + 1
        entry = float(df.iloc[entry_i]["open"])
        atr = float(df.iloc[i]["atr14"])
        distance = max(1.5 * atr, entry * 0.005)
        if direction == 1:
            stop, target = entry - distance, entry + 2 * distance
        else:
            stop, target = entry + distance, entry - 2 * distance
        exit_price = float(df.iloc[min(entry_i + max_hold_hours, len(df) - 1)]["close"])
        exit_i = min(entry_i + max_hold_hours, len(df) - 1)

        for j in range(entry_i, min(entry_i + max_hold_hours, len(df) - 1) + 1):
            row = df.iloc[j]
            stop_hit = float(row["low"]) <= stop if direction == 1 else float(row["high"]) >= stop
            target_hit = float(row["high"]) >= target if direction == 1 else float(row["low"]) <= target
            reversal = bool(row["weak_market"]) if direction == 1 else bool(row["strong_market"])
            if stop_hit:
                exit_price, exit_i = stop, j
                break
            if target_hit:
                exit_price, exit_i = target, j
                break
            if j > entry_i and reversal:
                exit_price, exit_i = float(row["close"]), j
                break

        gross_trade_return = direction * ((exit_price - entry) / entry)
        net_trade_return = gross_trade_return - 2 * one_way_cost
        allocated_return = net_trade_return * (allocation_pct / 100) * leverage
        equity *= 1 + allocated_return
        equity = max(equity, 0.0)
        returns.append(net_trade_return)
        curve.append((df.index[exit_i], equity))
        if equity == 0:
            break
        i = exit_i + 1

    series = pd.Series(dict(curve), dtype=float).sort_index()
    if not returns:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0, 0.0, series)
    values = np.asarray(returns)
    gains = values[values > 0].sum()
    losses = -values[values < 0].sum()
    profit_factor = gains / losses if losses else float("inf")
    drawdown = series / series.cummax() - 1
    return BacktestResult(
        trades=len(values),
        win_rate=float((values > 0).mean() * 100),
        net_return_pct=float((equity - 1) * 100),
        max_drawdown_pct=float(drawdown.min() * 100),
        profit_factor=float(profit_factor),
        average_trade_pct=float(values.mean() * 100),
        equity_curve=series,
    )
