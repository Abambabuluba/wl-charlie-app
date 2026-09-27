"""Resumen de cartera: pesos, exposiciones, plusvalías y rentabilidad sobre coste."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from divmon.config import Config
from divmon.models import Statement
from divmon.sources.fundamentals import Fundamentals

UNKNOWN = "Sin dato"


@dataclass
class Holding:
    symbol: str
    name: str
    currency: str
    country: str
    sector: str
    quantity: float
    price: float
    value_base: float
    cost_base: float
    weight: float
    annual_dividend_base: float | None   # bruto estimado para los próximos 12 meses

    @property
    def unrealized_base(self) -> float:
        return self.value_base - self.cost_base

    @property
    def unrealized_pct(self) -> float | None:
        return self.unrealized_base / self.cost_base if self.cost_base else None

    @property
    def yield_on_cost(self) -> float | None:
        if self.annual_dividend_base is None or not self.cost_base:
            return None
        return self.annual_dividend_base / self.cost_base

    @property
    def current_yield(self) -> float | None:
        if self.annual_dividend_base is None or not self.value_base:
            return None
        return self.annual_dividend_base / self.value_base


@dataclass
class Exposure:
    name: str
    value_base: float
    weight: float


def build_holdings(
    stmt: Statement,
    cfg: Config,
    fundamentals: dict[str, Fundamentals],
    annual_dividends: dict[str, float],
) -> list[Holding]:
    gross = sum(abs(p.value_base) for p in stmt.positions) or 1.0
    holdings = []
    for p in stmt.positions:
        ov = cfg.override(p.symbol)
        fund = fundamentals.get(p.symbol)
        country = ov.country or p.issuer_country or (p.isin[:2] if p.isin else None) or (fund and fund.country)
        sector = ov.sector or (fund and fund.sector)
        holdings.append(
            Holding(
                symbol=p.symbol,
                name=p.description,
                currency=p.currency,
                country=country or UNKNOWN,
                sector=sector or UNKNOWN,
                quantity=p.quantity,
                price=p.mark_price,
                value_base=p.value_base,
                cost_base=p.cost_base,
                weight=abs(p.value_base) / gross,
                annual_dividend_base=annual_dividends.get(p.symbol),
            )
        )
    return sorted(holdings, key=lambda h: h.value_base, reverse=True)


def exposure(holdings: list[Holding], attr: str) -> list[Exposure]:
    totals: dict[str, float] = defaultdict(float)
    for h in holdings:
        totals[getattr(h, attr)] += abs(h.value_base)
    gross = sum(totals.values()) or 1.0
    return sorted((Exposure(k, v, v / gross) for k, v in totals.items()), key=lambda e: e.value_base, reverse=True)


def currency_exposure(stmt: Statement) -> list[Exposure]:
    """Exposición neta por divisa: posiciones más efectivo (un préstamo en USD resta exposición al USD)."""
    totals: dict[str, float] = defaultdict(float)
    for p in stmt.positions:
        totals[p.currency] += p.value_base
    for c in stmt.cash:
        if c.ending_cash:
            totals[c.currency] += c.ending_cash * stmt.fx(c.currency)
    nlv = sum(totals.values()) or 1.0
    return sorted((Exposure(k, v, v / nlv) for k, v in totals.items()), key=lambda e: e.value_base, reverse=True)
