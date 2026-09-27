"""Calendario de cobros, estimación de ingresos e histórico de dividendos."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from divmon.models import DIVIDEND_TYPES, WITHHOLDING_TYPE, CashTransaction, Statement
from divmon.sources.fundamentals import Fundamentals

ANNOUNCED = "anunciado"
ESTIMATED = "estimado"
# Un dividendo anunciado sustituye al estimado del mismo valor si caen a menos de estos días.
MATCH_WINDOW_DAYS = 45


@dataclass
class DividendEvent:
    pay_date: date
    symbol: str
    gross_base: float
    net_base: float
    status: str


@dataclass
class DividendForecast:
    report_date: date
    events: list[DividendEvent]
    monthly: dict[str, tuple[float, float]]           # "AAAA-MM" → (bruto, neto)
    by_symbol_gross: dict[str, float]
    flat_symbols: list[str] = field(default_factory=list)   # sin histórico: estimación repartida

    @property
    def annual_gross(self) -> float:
        return sum(g for g, _ in self.monthly.values())

    @property
    def annual_net(self) -> float:
        return sum(n for _, n in self.monthly.values())

    def upcoming(self, days: int = 45) -> list[DividendEvent]:
        limit = self.report_date + timedelta(days=days)
        return [e for e in self.events if e.pay_date <= limit]


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _month_keys(start: date, count: int) -> list[str]:
    keys, y, m = [], start.year, start.month
    for _ in range(count):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return keys


def withholding_ratios(history: list[CashTransaction]) -> dict[str, float]:
    gross: dict[str, float] = defaultdict(float)
    withheld: dict[str, float] = defaultdict(float)
    for t in history:
        if not t.symbol:
            continue
        if t.type in DIVIDEND_TYPES:
            gross[t.symbol] += t.amount_base
        elif t.type == WITHHOLDING_TYPE:
            withheld[t.symbol] += -t.amount_base
    return {s: min(max(withheld[s] / g, 0.0), 0.6) for s, g in gross.items() if g > 0}


def forecast_dividends(
    stmt: Statement,
    history: list[CashTransaction],
    fundamentals: dict[str, Fundamentals] | None = None,
) -> DividendForecast:
    """Proyecta 12 meses: repite los pagos del último año con las acciones actuales.

    Los dividendos ya declarados (Open Dividend Accruals) tienen prioridad sobre la estimación.
    Los valores sin histórico usan la rentabilidad del proveedor de fundamentales, repartida por meses.
    """
    today = stmt.report_date
    horizon = today + timedelta(days=365)
    positions = {p.symbol: p for p in stmt.positions if p.quantity > 0}
    wh = withholding_ratios(history)
    default_wh = sum(wh.values()) / len(wh) if wh else 0.0

    # Pagos del último año agrupados por (valor, fecha); suma anulaciones y reemisiones.
    grouped: dict[tuple[str, date], list[CashTransaction]] = defaultdict(list)
    for t in history:
        if t.type in DIVIDEND_TYPES and t.symbol in positions and today - timedelta(days=365) < t.date <= today:
            grouped[(t.symbol, t.date)].append(t)

    events: list[DividendEvent] = []
    for (symbol, paid), txs in grouped.items():
        amount_local = sum(t.amount for t in txs)
        if amount_local <= 0:
            continue
        pos = positions[symbol]
        per_share = next((t.per_share for t in txs if t.per_share), None)
        currency = txs[0].currency
        fx = stmt.fx_to_base.get(currency, txs[0].fx_to_base)
        gross_local = per_share * pos.quantity if per_share else amount_local
        gross = gross_local * fx
        events.append(
            DividendEvent(paid + timedelta(days=365), symbol, gross, gross * (1 - wh.get(symbol, default_wh)), ESTIMATED)
        )

    for a in stmt.accruals:
        pay = a.pay_date or (a.ex_date + timedelta(days=30) if a.ex_date else None)
        if pay is None or not (today - timedelta(days=7) <= pay <= horizon):
            continue
        events = [
            e for e in events
            if not (e.symbol == a.symbol and e.status == ESTIMATED and abs((e.pay_date - pay).days) <= MATCH_WINDOW_DAYS)
        ]
        events.append(DividendEvent(max(pay, today), a.symbol, a.gross_amount * a.fx_to_base, a.net_amount * a.fx_to_base, ANNOUNCED))

    events.sort(key=lambda e: (e.pay_date, e.symbol))
    keys = _month_keys(today, 13)
    monthly = {k: [0.0, 0.0] for k in keys}
    by_symbol: dict[str, float] = defaultdict(float)
    for e in events:
        k = _month_key(e.pay_date)
        if k in monthly:
            monthly[k][0] += e.gross_base
            monthly[k][1] += e.net_base
        by_symbol[e.symbol] += e.gross_base

    flat = []
    for symbol, pos in positions.items():
        if symbol in by_symbol:
            continue
        fund = (fundamentals or {}).get(symbol)
        if not fund or not fund.dividend_yield:
            continue
        annual = fund.dividend_yield * pos.value_base
        by_symbol[symbol] = annual
        flat.append(symbol)
        for k in keys[1:]:
            monthly[k][0] += annual / 12
            monthly[k][1] += annual / 12 * (1 - wh.get(symbol, default_wh))

    return DividendForecast(
        report_date=today,
        events=events,
        monthly={k: (g, n) for k, (g, n) in monthly.items()},
        by_symbol_gross=dict(by_symbol),
        flat_symbols=sorted(flat),
    )


def received_by_month(history: list[CashTransaction], months: int, today: date) -> dict[str, tuple[float, float]]:
    """Dividendos cobrados por mes: (bruto, neto tras retenciones), en divisa base."""
    start_year, start_month = today.year, today.month
    for _ in range(months - 1):
        start_year, start_month = (start_year - 1, 12) if start_month == 1 else (start_year, start_month - 1)
    keys = _month_keys(date(start_year, start_month, 1), months)
    out = {k: [0.0, 0.0] for k in keys}
    for t in history:
        k = _month_key(t.date)
        if k not in out:
            continue
        if t.type in DIVIDEND_TYPES:
            out[k][0] += t.amount_base
            out[k][1] += t.amount_base
        elif t.type == WITHHOLDING_TYPE:
            out[k][1] += t.amount_base
    return {k: (g, n) for k, (g, n) in out.items()}


def received_by_year(history: list[CashTransaction]) -> dict[int, tuple[float, float]]:
    out: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for t in history:
        if t.type in DIVIDEND_TYPES:
            out[t.date.year][0] += t.amount_base
            out[t.date.year][1] += t.amount_base
        elif t.type == WITHHOLDING_TYPE:
            out[t.date.year][1] += t.amount_base
    return {y: (g, n) for y, (g, n) in sorted(out.items())}
