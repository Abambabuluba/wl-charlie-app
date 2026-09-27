"""Radar: comprueba los criterios de compra en candidatas y posiciones."""

from __future__ import annotations

from dataclasses import dataclass

from divmon.config import Criteria
from divmon.sources.fundamentals import Fundamentals

MEETS = "cumple"
FAILS = "no_cumple"
INCOMPLETE = "datos_incompletos"

CANDIDATE = "candidata"
HOLDING = "posicion"


@dataclass
class Check:
    name: str
    value: float | None
    limit: float
    ok: bool | None      # None = sin dato


@dataclass
class RadarResult:
    symbol: str
    role: str
    status: str
    checks: list[Check]
    fundamentals: Fundamentals

    def failing(self) -> list[Check]:
        return [c for c in self.checks if c.ok is False]

    def missing(self) -> list[Check]:
        return [c for c in self.checks if c.ok is None]


def evaluate(fund: Fundamentals, criteria: Criteria, role: str) -> RadarResult:
    checks: list[Check] = []

    def add(name: str, value: float | None, limit: float | None, ok) -> None:
        if limit is not None:
            checks.append(Check(name, value, limit, None if value is None else ok(value, limit)))

    # Un PER negativo (pérdidas) no cumple un PER máximo.
    add("PER", fund.per, criteria.per_max, lambda v, lim: 0 < v <= lim)
    add("Rentabilidad", fund.dividend_yield, criteria.dividend_yield_min, lambda v, lim: v >= lim)
    add("Payout", fund.payout, criteria.payout_max, lambda v, lim: 0 <= v <= lim)
    add("Deuda/EBITDA", fund.debt_ebitda, criteria.debt_ebitda_max, lambda v, lim: v <= lim)

    if any(c.ok is False for c in checks):
        status = FAILS
    elif any(c.ok is None for c in checks):
        status = INCOMPLETE
    else:
        status = MEETS
    return RadarResult(fund.symbol, role, status, checks, fund)


@dataclass
class Transition:
    result: RadarResult
    previous: str | None


def transitions(results: list[RadarResult], previous: dict[str, str]) -> list[Transition]:
    """Cambios que merecen aviso.

    Candidatas: cuando pasan a cumplir. Posiciones: cuando dejan de cumplir o vuelven a cumplir.
    La falta de datos no dispara avisos ni borra el estado anterior.
    """
    out = []
    for r in results:
        before = previous.get(r.symbol)
        if r.status == INCOMPLETE or r.status == before:
            continue
        if r.role == CANDIDATE and r.status == MEETS:
            out.append(Transition(r, before))
        elif r.role == HOLDING and (r.status == FAILS or (r.status == MEETS and before == FAILS)):
            out.append(Transition(r, before))
    return out
