from __future__ import annotations

import time

import pandas as pd
import requests


class BinanceDataError(RuntimeError):
    """Raised when trustworthy Binance market data cannot be obtained."""


BASE_URLS = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
)

FUTURES_BASE_URLS = (
    "https://fapi.binance.com",
)


def fetch_live_price(symbol: str, product: str = "spot") -> float:
    if symbol not in {"BTCUSDT", "ETHUSDT"}:
        raise ValueError("Only BTCUSDT and ETHUSDT are supported in Version 3.")
    errors: list[str] = []
    if product not in {"spot", "futures"}:
        raise ValueError("Product must be spot or futures.")
    base_urls = FUTURES_BASE_URLS if product == "futures" else BASE_URLS
    path = "/fapi/v1/ticker/price" if product == "futures" else "/api/v3/ticker/price"
    for base_url in base_urls:
        try:
            response = requests.get(
                f"{base_url}{path}",
                params={"symbol": symbol},
                timeout=8,
            )
            response.raise_for_status()
            value = float(response.json()["price"])
            if value <= 0:
                raise ValueError("non-positive live price")
            return value
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{base_url}: {exc}")
    raise BinanceDataError("Live price could not be verified. " + " | ".join(errors))


def fetch_closed_klines(symbol: str, interval: str = "1h", limit: int = 1000, product: str = "spot") -> pd.DataFrame:
    if symbol not in {"BTCUSDT", "ETHUSDT"}:
        raise ValueError("Only BTCUSDT and ETHUSDT are supported in Version 3.")
    if product not in {"spot", "futures"}:
        raise ValueError("Product must be spot or futures.")
    params = {"symbol": symbol, "interval": interval, "limit": min(max(limit, 100), 1000)}
    errors: list[str] = []
    payload = None
    base_urls = FUTURES_BASE_URLS if product == "futures" else BASE_URLS
    path = "/fapi/v1/klines" if product == "futures" else "/api/v3/klines"
    for base_url in base_urls:
        try:
            response = requests.get(f"{base_url}{path}", params=params, timeout=12)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or len(payload) < 100:
                raise ValueError("unexpected or insufficient candle payload")
            break
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{base_url}: {exc}")
    if payload is None:
        raise BinanceDataError("Binance data could not be verified. " + " | ".join(errors))

    columns = [
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
    ]
    frame = pd.DataFrame(payload, columns=columns)
    numeric = ["open", "high", "low", "close", "volume", "quote_volume", "trades"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame["close_time"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True)
    frame = frame.set_index("open_time").sort_index()

    now_ms = int(time.time() * 1000)
    frame = frame[frame["close_time"].astype("int64") // 1_000_000 < now_ms]
    frame = frame.dropna(subset=["open", "high", "low", "close", "volume"])
    if len(frame) < 100:
        raise BinanceDataError("Fewer than 100 verified closed candles were returned.")
    if not (frame[["open", "high", "low", "close"]] > 0).all().all():
        raise BinanceDataError("Invalid non-positive market prices were returned.")
    return frame
