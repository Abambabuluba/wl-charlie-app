"""Titulares recientes de cada valor (Yahoo Finance vía yfinance)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)


@dataclass
class NewsItem:
    symbol: str
    title: str
    publisher: str
    url: str
    published: datetime
    summary: str = ""


def _parse(symbol: str, raw: dict) -> NewsItem | None:
    """Admite el formato nuevo de Yahoo ({'content': {...}}) y el antiguo (campos planos)."""
    c = raw.get("content") or {}
    if c:
        title = c.get("title")
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
        publisher = (c.get("provider") or {}).get("displayName", "")
        try:
            published = datetime.fromisoformat((c.get("pubDate") or "").replace("Z", "+00:00"))
        except ValueError:
            return None
        summary = c.get("summary") or ""
    else:
        title, url, publisher = raw.get("title"), raw.get("link"), raw.get("publisher", "")
        ts = raw.get("providerPublishTime")
        if not ts:
            return None
        published = datetime.fromtimestamp(ts, tz=timezone.utc)
        summary = ""
    if not title or not url:
        return None
    return NewsItem(symbol, title.strip(), publisher, url, published, summary.strip())


def yahoo_news(symbol: str, yahoo_symbol: str, max_items: int = 4, max_age_days: int = 7,
               now: datetime | None = None) -> list[NewsItem]:
    import yfinance as yf

    now = now or datetime.now(timezone.utc)
    items = [_parse(symbol, raw) for raw in (yf.Ticker(yahoo_symbol).news or [])]
    recent = [i for i in items if i and now - i.published <= timedelta(days=max_age_days)]
    seen, unique = set(), []
    for i in sorted(recent, key=lambda i: i.published, reverse=True):
        if i.title.lower() not in seen:
            seen.add(i.title.lower())
            unique.append(i)
    return unique[:max_items]


def news_for(symbols: dict[str, str], max_items: int, max_age_days: int, fetch=yahoo_news) -> dict[str, list[NewsItem]]:
    """Noticias por símbolo de IBKR ({símbolo: símbolo_yahoo}). Un valor que falla no bloquea al resto."""
    out = {}
    for symbol, ysym in symbols.items():
        try:
            out[symbol] = fetch(symbol, ysym, max_items, max_age_days)
        except Exception as exc:
            log.warning("Sin noticias para %s (%s): %s", symbol, ysym, exc)
            out[symbol] = []
    return out
