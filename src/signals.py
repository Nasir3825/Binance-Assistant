from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Signal:
    timestamp: pd.Timestamp
    close: float
    atr: float
    score: int
    decision: str
    direction: str
    rsi: float
    volume_ratio: float
    atr_pct: float
    one_hour_change_label: str
    reasons: tuple[str, ...]


def add_signal_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["long_trend_point"] = ((out["close"] > out["ema20"]) & (out["ema20"] > out["ema50"])).astype(int)
    out["long_momentum_point"] = out["rsi14"].between(50, 68, inclusive="both").astype(int)
    out["long_macd_point"] = (out["macd"] > out["macd_signal"]).astype(int)
    out["short_trend_point"] = ((out["close"] < out["ema20"]) & (out["ema20"] < out["ema50"])).astype(int)
    out["short_momentum_point"] = out["rsi14"].between(32, 50, inclusive="both").astype(int)
    out["short_macd_point"] = (out["macd"] < out["macd_signal"]).astype(int)
    out["volume_point"] = (out["volume_ratio"] >= 1.0).astype(int)
    out["long_score"] = out[["long_trend_point", "long_momentum_point", "long_macd_point", "volume_point"]].sum(axis=1)
    out["short_score"] = out[["short_trend_point", "short_momentum_point", "short_macd_point", "volume_point"]].sum(axis=1)
    out["overbought"] = out["rsi14"] >= 70
    out["oversold"] = out["rsi14"] <= 30
    out["long_setup"] = (out["long_score"] >= 3) & (~out["overbought"])
    out["short_setup"] = (out["short_score"] >= 3) & (~out["oversold"])
    out["weak_market"] = (out["close"] < out["ema50"]) | ((out["long_score"] <= 1) & (out["macd"] < out["macd_signal"]))
    out["strong_market"] = (out["close"] > out["ema50"]) | ((out["short_score"] <= 1) & (out["macd"] > out["macd_signal"]))
    return out


def latest_signal(df: pd.DataFrame, allow_short: bool = False) -> Signal:
    row = df.iloc[-1]
    reasons: list[str] = []
    if row["long_setup"]:
        decision, direction, score = "LONG SETUP", "LONG", int(row["long_score"])
        reasons.append("Bullish EMA structure" if row["long_trend_point"] else "EMA structure is not fully bullish")
        reasons.append("RSI is in the preferred long zone" if row["long_momentum_point"] else f"RSI {row['rsi14']:.1f} is outside the preferred long zone")
        reasons.append("MACD supports the long" if row["long_macd_point"] else "MACD does not support the long")
    elif allow_short and row["short_setup"]:
        decision, direction, score = "SHORT SETUP", "SHORT", int(row["short_score"])
        reasons.append("Bearish EMA structure" if row["short_trend_point"] else "EMA structure is not fully bearish")
        reasons.append("RSI is in the preferred short zone" if row["short_momentum_point"] else f"RSI {row['rsi14']:.1f} is outside the preferred short zone")
        reasons.append("MACD supports the short" if row["short_macd_point"] else "MACD does not support the short")
    else:
        direction = "NONE"
        score = int(max(row["long_score"], row["short_score"] if allow_short else 0))
        if not allow_short and row["weak_market"]:
            decision = "EXIT / AVOID"
        else:
            decision = "NEUTRAL / WAIT"
        reasons.append(f"Long score: {int(row['long_score'])}/4")
        if allow_short:
            reasons.append(f"Short score: {int(row['short_score'])}/4")
        reasons.append("Neither direction currently meets every entry gate")

    reasons.append("Volume confirms the move" if row["volume_point"] else "Volume is below its 20-hour average")
    if row["overbought"]:
        reasons.append("New long entries are blocked because RSI is overbought")
    if row["oversold"]:
        reasons.append("New short entries are blocked because RSI is oversold")

    change = float(row["return_1h"] * 100)
    return Signal(
        timestamp=df.index[-1],
        close=float(row["close"]),
        atr=float(row["atr14"]),
        score=score,
        decision=decision,
        direction=direction,
        rsi=float(row["rsi14"]),
        volume_ratio=float(row["volume_ratio"]),
        atr_pct=float(row["atr14"] / row["close"] * 100),
        one_hour_change_label=f"{change:+.2f}% last hour",
        reasons=tuple(reasons),
    )
