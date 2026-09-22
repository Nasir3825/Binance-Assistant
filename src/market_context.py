from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests

from src.binance_client import BinanceDataError, fetch_closed_klines


@dataclass(frozen=True)
class MarketContext:
    symbol: str
    trends: dict[str, str]
    overall_trend: str
    price_change_24h_pct: float
    quote_volume_24h: float
    funding_rate_pct: float | None
    open_interest: float | None


def classify_trend(frame: pd.DataFrame) -> str:
    close = frame["close"]
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    last = float(close.iloc[-1])
    if last > ema20 > ema50:
        return "BULLISH"
    if last < ema20 < ema50:
        return "BEARISH"
    return "MIXED"


def overall_trend(trends: dict[str, str]) -> str:
    bullish = sum(value == "BULLISH" for value in trends.values())
    bearish = sum(value == "BEARISH" for value in trends.values())
    if bullish >= 2:
        return "BULLISH"
    if bearish >= 2:
        return "BEARISH"
    return "MIXED"


def _get_json(url: str, params: dict[str, str] | None = None) -> dict:
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("unexpected response type")
        return payload
    except (requests.RequestException, ValueError) as exc:
        raise BinanceDataError(f"Market context request failed: {exc}") from exc


def fetch_market_context(symbol: str, product: str = "spot") -> MarketContext:
    if product not in {"spot", "futures"}:
        raise ValueError("Product must be spot or futures.")

    trends: dict[str, str] = {}
    for interval in ("1h", "4h", "1d"):
        frame = fetch_closed_klines(symbol, interval=interval, limit=120, product=product)
        trends[interval] = classify_trend(frame)

    ticker_base = "https://fapi.binance.com/fapi/v1" if product == "futures" else "https://api.binance.com/api/v3"
    ticker = _get_json(f"{ticker_base}/ticker/24hr", {"symbol": symbol})

    funding_rate = None
    open_interest = None
    try:
        premium = _get_json("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": symbol})
        funding_rate = float(premium["lastFundingRate"]) * 100
        interest = _get_json("https://fapi.binance.com/fapi/v1/openInterest", {"symbol": symbol})
        open_interest = float(interest["openInterest"])
    except (BinanceDataError, KeyError, TypeError, ValueError):
        # Derivatives context is optional when Spot data remains valid.
        funding_rate = None
        open_interest = None

    try:
        price_change = float(ticker["priceChangePercent"])
        quote_volume = float(ticker["quoteVolume"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BinanceDataError(f"Invalid 24-hour market statistics: {exc}") from exc

    return MarketContext(
        symbol=symbol,
        trends=trends,
        overall_trend=overall_trend(trends),
        price_change_24h_pct=price_change,
        quote_volume_24h=quote_volume,
        funding_rate_pct=funding_rate,
        open_interest=open_interest,
    )


def context_conflicts(direction: str, context: MarketContext) -> bool:
    return (direction == "LONG" and context.overall_trend == "BEARISH") or (
        direction == "SHORT" and context.overall_trend == "BULLISH"
    )
