import sys
import types
from datetime import datetime, timezone

from divmon.sources.news import news_for, yahoo_news

NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
RAW = [
    {"content": {"title": "Kaspi raises dividend", "pubDate": "2026-09-26T08:00:00Z",
                 "provider": {"displayName": "Reuters"}, "canonicalUrl": {"url": "https://x/1"}}},
    {"content": {"title": "Kaspi raises dividend", "pubDate": "2026-09-25T08:00:00Z",
                 "provider": {"displayName": "Otro"}, "canonicalUrl": {"url": "https://x/2"}}},
    {"content": {"title": "Old news", "pubDate": "2026-08-01T08:00:00Z",
                 "provider": {"displayName": "Reuters"}, "canonicalUrl": {"url": "https://x/3"}}},
    {"title": "Legacy format item", "publisher": "Yahoo", "link": "https://x/4",
     "providerPublishTime": int(datetime(2026, 9, 24, tzinfo=timezone.utc).timestamp())},
    {"content": {"title": "Sin enlace", "pubDate": "2026-09-26T08:00:00Z"}},
]


def test_yahoo_news_filters_and_dedupes(monkeypatch):
    fake = types.SimpleNamespace(Ticker=lambda s: types.SimpleNamespace(news=RAW))
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    items = yahoo_news("KSPI", "KSPI", max_items=5, max_age_days=7, now=NOW)
    assert [i.title for i in items] == ["Kaspi raises dividend", "Legacy format item"]
    assert items[0].publisher == "Reuters" and items[0].url == "https://x/1"


def test_news_for_survives_failures():
    def fetch(symbol, ysym, n, days):
        if symbol == "RED":
            raise ConnectionError("sin red")
        return ["ok"]
    assert news_for({"KSPI": "KSPI", "RED": "RED.MC"}, 4, 7, fetch=fetch) == {"KSPI": ["ok"], "RED": []}


def test_report_includes_news(stmt, cfg):
    from divmon.report import render_html
    from divmon.service import analyze
    from divmon.sources.news import NewsItem
    from divmon.storage import Store

    analysis = analyze(cfg, stmt, stmt.transactions, {})
    news = {"SAN": [NewsItem("SAN", "Santander sube el dividendo", "Expansión", "https://x/san", NOW)]}
    html = render_html(cfg, analysis, Store(":memory:"), news)
    assert "Noticias de tus posiciones" in html and "https://x/san" in html
    assert "Noticias de tus posiciones" not in render_html(cfg, analysis, Store(":memory:"))
