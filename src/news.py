from __future__ import annotations

from dataclasses import dataclass
import re
from statistics import mean

import requests


GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

POSITIVE_TERMS = {
    "adoption", "approval", "approved", "inflow", "inflows", "partnership",
    "upgrade", "rally", "surge", "record high", "breakout", "institutional",
    "accumulation", "launch", "expansion", "recovery",
}
NEGATIVE_TERMS = {
    "hack", "hacked", "exploit", "breach", "ban", "banned", "crackdown",
    "lawsuit", "fraud", "liquidation", "liquidations", "outflow", "outflows",
    "sell-off", "collapse", "bankruptcy", "attack", "sanctions", "rejection",
}
HIGH_IMPACT_TERMS = {
    "federal reserve", "fed", "interest rate", "cpi", "inflation", "sec",
    "etf", "regulation", "regulator", "hack", "exploit", "breach",
    "liquidation", "war", "sanctions", "binance", "coinbase", "institutional",
}


class NewsDataError(RuntimeError):
    """Raised when current news cannot be retrieved or verified."""


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    domain: str
    seen_date: str
    score: int
    impact: str


@dataclass(frozen=True)
class NewsSummary:
    items: tuple[NewsItem, ...]
    average_score: float
    label: str
    high_impact_count: int
    risk_gate: bool


def score_headline(title: str) -> tuple[int, str]:
    text = title.casefold()
    contains = lambda term: re.search(rf"\b{re.escape(term)}\b", text) is not None
    positive = sum(contains(term) for term in POSITIVE_TERMS)
    negative = sum(contains(term) for term in NEGATIVE_TERMS)
    score = max(-100, min(100, (positive - negative) * 25))
    impact = "HIGH" if any(contains(term) for term in HIGH_IMPACT_TERMS) else "NORMAL"
    return score, impact


def summarize_news(items: list[NewsItem]) -> NewsSummary:
    if not items:
        raise NewsDataError("No recent English-language crypto headlines were returned.")
    average_score = mean(item.score for item in items)
    high_impact = [item for item in items if item.impact == "HIGH"]
    high_impact_negative = [item for item in high_impact if item.score < 0]
    if average_score <= -20:
        label = "CAUTIOUS / NEGATIVE"
    elif average_score >= 20:
        label = "SUPPORTIVE / POSITIVE"
    else:
        label = "MIXED / NEUTRAL"
    risk_gate = average_score <= -30 or len(high_impact_negative) >= 2
    return NewsSummary(
        items=tuple(items),
        average_score=float(average_score),
        label=label,
        high_impact_count=len(high_impact),
        risk_gate=risk_gate,
    )


def fetch_crypto_news(max_records: int = 25) -> NewsSummary:
    params = {
        "query": "(bitcoin OR ethereum OR cryptocurrency) sourcelang:english",
        "mode": "ArtList",
        "maxrecords": min(max(max_records, 10), 50),
        "format": "json",
        "sort": "HybridRel",
        "timespan": "24h",
    }
    try:
        response = requests.get(GDELT_DOC_URL, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise NewsDataError(f"Current news could not be verified: {exc}") from exc

    articles = payload.get("articles", []) if isinstance(payload, dict) else []
    items: list[NewsItem] = []
    seen_urls: set[str] = set()
    for article in articles:
        title = str(article.get("title", "")).strip()
        url = str(article.get("url", "")).strip()
        if not title or not url or url in seen_urls:
            continue
        seen_urls.add(url)
        score, impact = score_headline(title)
        items.append(
            NewsItem(
                title=title,
                url=url,
                domain=str(article.get("domain", "Unknown")),
                seen_date=str(article.get("seendate", "")),
                score=score,
                impact=impact,
            )
        )
    return summarize_news(items)
