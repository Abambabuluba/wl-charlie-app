"""Datos fundamentales (PER, rentabilidad, payout, deuda/EBITDA, sector, país)."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, fields
from typing import Protocol

from divmon.config import SymbolOverride

log = logging.getLogger(__name__)

# Bolsa de IBKR → sufijo de Yahoo Finance.
EXCHANGE_SUFFIX = {
    "BM": ".MC", "BME": ".MC",
    "IBIS": ".DE", "IBIS2": ".DE", "XETRA": ".DE", "FWB": ".F",
    "SBF": ".PA", "ENEXT.BE": ".BR", "AEB": ".AS",
    "BVME": ".MI", "LSE": ".L", "LSEETF": ".L",
    "EBS": ".SW", "VIRTX": ".SW",
    "N.VILNIUS": ".VS", "N.TALLINN": ".TL", "N.RIGA": ".RG",
    "BVL": ".LS", "SFB": ".ST", "CPH": ".CO", "OSE": ".OL", "HEX": ".HE",
    "TSE": ".TO", "VENTURE": ".V", "ASX": ".AX", "SEHK": ".HK", "SGX": ".SI",
}
METRICS = ("per", "dividend_yield", "payout", "debt_ebitda")


@dataclass
class Fundamentals:
    symbol: str
    per: float | None = None
    dividend_yield: float | None = None   # en tanto por uno
    payout: float | None = None           # en tanto por uno
    debt_ebitda: float | None = None
    sector: str | None = None
    country: str | None = None
    price: float | None = None
    currency: str | None = None
    source: str = "manual"

    def with_override(self, ov: SymbolOverride) -> "Fundamentals":
        data = asdict(self)
        for name in (*METRICS, "sector", "country"):
            value = getattr(ov, name)
            if value is not None:
                data[name] = value
        return Fundamentals(**data)

    @classmethod
    def from_row(cls, row: dict) -> "Fundamentals":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in row.items() if k in names})


class FundamentalsProvider(Protocol):
    def get(self, symbol: str, yahoo_symbol: str) -> Fundamentals: ...


def yahoo_symbol(symbol: str, listing_exchange: str | None, override: SymbolOverride | None = None) -> str:
    if override and override.yahoo:
        return override.yahoo
    suffix = EXCHANGE_SUFFIX.get((listing_exchange or "").upper(), "")
    base = symbol.replace(" ", "-")
    if not suffix:
        base = base.replace(".", "-")   # BRK.B → BRK-B en Yahoo
    return base + suffix


def _positive(value) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v else None   # descarta NaN


def _yield(rate: float | None, price: float | None, currency: str | None) -> float | None:
    if not rate or not price:
        return None
    if currency == "GBp":
        # Londres cotiza en peniques; el dividendo puede venir en libras o en peniques.
        in_pounds = rate / (price / 100)
        return in_pounds if in_pounds <= 0.4 else rate / price
    return rate / price


class YahooProvider:
    """Yahoo Finance vía yfinance: gratuito y no oficial; puede fallar o tener huecos."""

    def get(self, symbol: str, yahoo_symbol: str) -> Fundamentals:
        import yfinance as yf

        info = yf.Ticker(yahoo_symbol).info or {}
        price = _positive(info.get("currentPrice") or info.get("regularMarketPrice"))
        rate = _positive(info.get("dividendRate") or info.get("trailingAnnualDividendRate"))
        dividend_yield = _yield(rate, price, info.get("currency"))
        if dividend_yield is None or dividend_yield > 0.4:
            dividend_yield = _positive(info.get("trailingAnnualDividendYield"))
        debt, ebitda = _positive(info.get("totalDebt")), _positive(info.get("ebitda"))
        return Fundamentals(
            symbol=symbol,
            per=_positive(info.get("trailingPE")),
            dividend_yield=dividend_yield,
            payout=_positive(info.get("payoutRatio")),
            debt_ebitda=debt / ebitda if debt is not None and ebitda and ebitda > 0 else None,
            sector=info.get("sector") or ("ETF" if info.get("quoteType") == "ETF" else None),
            country=info.get("country"),
            price=price,
            currency=info.get("currency"),
            source=f"yahoo:{yahoo_symbol}",
        )


def yahoo_fx_rate(currency: str, base: str) -> float | None:
    """Tipo de cambio de ``currency`` a ``base`` en Yahoo (por ejemplo CADEUR=X)."""
    import yfinance as yf

    ticker = yf.Ticker(f"{currency}{base}=X")
    rate = _positive(getattr(ticker.fast_info, "last_price", None))
    return rate or _positive((ticker.info or {}).get("regularMarketPrice"))


class NullProvider:
    """Sin proveedor externo: solo cuenta lo que pongas a mano en config.yaml."""

    def get(self, symbol: str, yahoo_symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, source="manual")


def make_provider(name: str) -> FundamentalsProvider:
    return YahooProvider() if name == "yahoo" else NullProvider()
