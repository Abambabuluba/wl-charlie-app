"""Riesgos de concentración por posición, país, sector y divisa."""

from __future__ import annotations

from dataclasses import dataclass

from divmon.analytics.portfolio import UNKNOWN, Exposure, Holding, exposure
from divmon.config import ConcentrationConfig


@dataclass
class Breach:
    kind: str
    name: str
    weight: float
    limit: float


def check_concentration(
    holdings: list[Holding],
    currencies: list[Exposure],
    cfg: ConcentrationConfig,
    base_currency: str,
) -> list[Breach]:
    breaches: list[Breach] = []

    def scan(kind: str, items, limit: float | None, skip: set[str] = frozenset()) -> None:
        if limit is None:
            return
        for name, weight in items:
            if name not in skip and weight > limit:
                breaches.append(Breach(kind, name, weight, limit))

    scan("posición", ((h.symbol, h.weight) for h in holdings), cfg.position_max)
    scan("país", ((e.name, e.weight) for e in exposure(holdings, "country")), cfg.country_max, {UNKNOWN})
    scan("sector", ((e.name, e.weight) for e in exposure(holdings, "sector")), cfg.sector_max, {UNKNOWN})
    scan(
        "divisa",
        ((e.name, e.weight) for e in currencies),
        cfg.currency_max,
        {base_currency} if cfg.exclude_base_currency else set(),
    )
    return breaches
