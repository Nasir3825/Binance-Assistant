import numpy as np
import pandas as pd

from src.indicators import add_indicators


def sample_frame(rows: int = 120) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = np.linspace(100, 130, rows) + np.sin(np.arange(rows) / 3)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.linspace(1000, 1500, rows),
        },
        index=index,
    )


def test_indicators_are_bounded_and_complete():
    result = add_indicators(sample_frame())
    assert not result.empty
    assert result[["ema20", "ema50", "rsi14", "atr14", "volume_ratio"]].notna().all().all()
    assert result["rsi14"].between(0, 100).all()
    assert (result["atr14"] > 0).all()

