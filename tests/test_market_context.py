import numpy as np
import pandas as pd

from src.market_context import MarketContext, classify_trend, context_conflicts, overall_trend


def test_multi_timeframe_trend_and_conflict():
    index = pd.date_range("2026-01-01", periods=100, freq="h", tz="UTC")
    close = np.linspace(100, 150, 100)
    frame = pd.DataFrame({"close": close}, index=index)
    assert classify_trend(frame) == "BULLISH"
    assert overall_trend({"1h": "BULLISH", "4h": "BULLISH", "1d": "MIXED"}) == "BULLISH"
    context = MarketContext("BTCUSDT", {"1h": "BULLISH"}, "BULLISH", 2.0, 1_000_000.0, 0.01, 10_000.0)
    assert context_conflicts("SHORT", context) is True
    assert context_conflicts("LONG", context) is False

