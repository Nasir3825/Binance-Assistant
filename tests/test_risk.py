import pandas as pd
import pytest

from src.risk import build_trade_plan
from src.signals import Signal


def test_trade_plan_respects_account_caps():
    signal = Signal(
        timestamp=pd.Timestamp("2026-01-01", tz="UTC"),
        close=100.0,
        atr=2.0,
        score=4,
        decision="LONG SETUP",
        direction="LONG",
        rsi=60.0,
        volume_ratio=1.2,
        atr_pct=2.0,
        one_hour_change_label="+1.00% last hour",
        reasons=(),
    )
    plan = build_trade_plan(signal, account_size=100, risk_pct=0.5, max_allocation_pct=25)
    assert plan.notional_value <= 25.000001
    assert plan.margin_required <= 25.000001
    assert plan.planned_loss <= 0.500001
    assert plan.stop < plan.entry < plan.target
    assert plan.reward_to_risk == 2.0


def test_short_leveraged_plan_respects_100_dollar_cap():
    signal = Signal(
        timestamp=pd.Timestamp("2026-01-01", tz="UTC"),
        close=100.0,
        atr=2.0,
        score=4,
        decision="SHORT SETUP",
        direction="SHORT",
        rsi=40.0,
        volume_ratio=1.2,
        atr_pct=2.0,
        one_hour_change_label="-1.00% last hour",
        reasons=(),
    )
    plan = build_trade_plan(signal, account_size=100, risk_pct=0.5, max_allocation_pct=25, leverage=3)
    assert plan.margin_required <= 25.000001
    assert plan.notional_value <= 75.000001
    assert plan.planned_loss <= 0.500001
    assert plan.target < plan.entry < plan.stop
    assert plan.danger_price > plan.entry


def test_capital_above_100_is_rejected():
    signal = Signal(
        timestamp=pd.Timestamp("2026-01-01", tz="UTC"),
        close=100.0,
        atr=2.0,
        score=4,
        decision="LONG SETUP",
        direction="LONG",
        rsi=60.0,
        volume_ratio=1.2,
        atr_pct=2.0,
        one_hour_change_label="+1.00% last hour",
        reasons=(),
    )
    with pytest.raises(ValueError):
        build_trade_plan(signal, account_size=101, risk_pct=0.5, max_allocation_pct=25, leverage=2)
