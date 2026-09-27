import sys
import types

import pytest

from divmon.config import SymbolOverride
from divmon.sources.fundamentals import Fundamentals, YahooProvider, _yield, yahoo_symbol


@pytest.mark.parametrize("symbol, exchange, expected", [
    ("SAN", "BM", "SAN.MC"),
    ("ALV", "IBIS", "ALV.DE"),
    ("BATS", "LSE", "BATS.L"),
    ("BRK B", "NYSE", "BRK-B"),
    ("MO", None, "MO"),
    ("IGN1L", "N.VILNIUS", "IGN1L.VS"),
])
def test_yahoo_symbol(symbol, exchange, expected):
    assert yahoo_symbol(symbol, exchange) == expected


def test_yahoo_symbol_override():
    assert yahoo_symbol("ENG", "BM", SymbolOverride(yahoo="ENG.MC")) == "ENG.MC"


def test_yield_handles_london_pence():
    assert _yield(2.45, 3300, "GBp") == pytest.approx(2.45 / 33)
    assert _yield(245, 3300, "GBp") == pytest.approx(245 / 3300)
    assert _yield(4.0, 80, "USD") == pytest.approx(0.05)


def test_yahoo_provider_maps_fields(monkeypatch):
    info = {"trailingPE": 9.1, "dividendRate": 4.08, "currentPrice": 58.0, "payoutRatio": 0.78,
            "totalDebt": 25e9, "ebitda": 11e9, "sector": "Consumer Defensive", "country": "United States",
            "currency": "USD"}
    fake = types.SimpleNamespace(Ticker=lambda s: types.SimpleNamespace(info=info))
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    f = YahooProvider().get("MO", "MO")
    assert f.per == 9.1 and f.payout == 0.78
    assert f.dividend_yield == pytest.approx(4.08 / 58)
    assert f.debt_ebitda == pytest.approx(25 / 11)
    assert f.source == "yahoo:MO"


def test_manual_override_wins():
    f = Fundamentals("X", per=20, sector="Tech").with_override(SymbolOverride(per=12, sector="Utilities"))
    assert (f.per, f.sector) == (12, "Utilities")
