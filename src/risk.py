from __future__ import annotations

from dataclasses import dataclass

from src.signals import Signal


@dataclass(frozen=True)
class TradePlan:
    direction: str
    entry: float
    min_valid_entry: float
    max_valid_entry: float
    stop: float
    target: float
    quantity: float
    notional_value: float
    margin_required: float
    planned_loss: float
    reward_to_risk: float
    leverage: int
    danger_price: float | None


def build_trade_plan(
    signal: Signal,
    account_size: float = 100.0,
    risk_pct: float = 0.5,
    max_allocation_pct: float = 25.0,
    leverage: int = 1,
) -> TradePlan:
    if signal.direction not in {"LONG", "SHORT"}:
        raise ValueError("A LONG or SHORT signal is required to build a trade plan.")
    if not (0 < account_size <= 100) or not (0 < risk_pct <= 1) or not (0 < max_allocation_pct <= 30) or not (1 <= leverage <= 5):
        raise ValueError("Invalid account risk settings.")
    entry = signal.close
    stop_distance = max(1.5 * signal.atr, entry * 0.005)
    if signal.direction == "LONG":
        stop = max(entry - stop_distance, 0.01)
        target = entry + 2.0 * stop_distance
    else:
        stop = entry + stop_distance
        target = max(entry - 2.0 * stop_distance, 0.01)
    min_valid_entry = max(entry - 0.25 * signal.atr, 0.01)
    max_valid_entry = entry + 0.25 * signal.atr
    risk_budget = account_size * risk_pct / 100
    quantity_by_risk = risk_budget / stop_distance
    max_margin = account_size * max_allocation_pct / 100
    quantity_by_allocation = (max_margin * leverage) / entry
    quantity = min(quantity_by_risk, quantity_by_allocation)
    notional_value = quantity * entry
    margin_required = notional_value / leverage
    planned_loss = quantity * abs(entry - stop)
    danger_price = None
    if leverage > 1:
        danger_price = entry * (1 - 1 / leverage) if signal.direction == "LONG" else entry * (1 + 1 / leverage)
    return TradePlan(
        direction=signal.direction,
        entry=entry,
        min_valid_entry=min_valid_entry,
        max_valid_entry=max_valid_entry,
        stop=stop,
        target=target,
        quantity=quantity,
        notional_value=notional_value,
        margin_required=margin_required,
        planned_loss=planned_loss,
        reward_to_risk=2.0,
        leverage=leverage,
        danger_price=danger_price,
    )
