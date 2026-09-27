"""Orquestación: obtener datos, analizarlos, guardar histórico y generar alertas."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

from divmon.alerts import Alert, concentration_alerts, margin_alerts, radar_alerts
from divmon.analytics.amortization import Plan, standard_plans
from divmon.analytics.concentration import Breach, check_concentration
from divmon.analytics.dividends import DividendForecast, forecast_dividends
from divmon.analytics.margin import LiveMargin, MarginStatus, compute_margin
from divmon.analytics.portfolio import Exposure, Holding, build_holdings, currency_exposure
from divmon.analytics.radar import CANDIDATE, HOLDING, INCOMPLETE, RadarResult, Transition, evaluate, transitions
from divmon.config import Config
from divmon.models import CashTransaction, Statement
from divmon.sources.flex import fetch_statement_xml, parse_statement
from divmon.sources.fundamentals import (
    Fundamentals, FundamentalsProvider, make_provider, yahoo_fx_rate, yahoo_symbol,
)
from divmon.storage import Store

log = logging.getLogger(__name__)


@dataclass
class Analysis:
    stmt: Statement
    history: list[CashTransaction]
    fundamentals: dict[str, Fundamentals]
    holdings: list[Holding]
    forecast: DividendForecast
    margin: MarginStatus
    currencies: list[Exposure]
    breaches: list[Breach]
    radar: list[RadarResult]
    plans: list[Plan]
    warnings: list[Alert] = field(default_factory=list)


# --- Obtención de datos ----------------------------------------------------------------------------


def archive_path(cfg: Config, report_date: date) -> Path:
    return cfg.flex_dir / f"{report_date.isoformat()}.xml"


def complete_fx(stmt: Statement, base_currency: str, lookup=None) -> Statement:
    """Busca en Yahoo los tipos de cambio que no trae el Flex; si no hay, aparta ese saldo."""
    lookup = lookup or yahoo_fx_rate
    for currency in stmt.missing_fx():
        try:
            rate = lookup(currency, base_currency)
        except Exception as exc:
            log.warning("Sin tipo de cambio %s→%s: %s", currency, base_currency, exc)
            rate = None
        if rate:
            stmt.fx_to_base[currency] = rate
    if stmt.missing_fx():
        missing = set(stmt.missing_fx())
        stmt.ignored_cash = [c for c in stmt.cash if c.currency in missing]
        stmt.cash = [c for c in stmt.cash if c.currency not in missing]
    return stmt


def _archive(cfg: Config, xml: bytes) -> Statement:
    stmt = complete_fx(parse_statement(xml, cfg.base_currency), cfg.base_currency)
    path = archive_path(cfg, stmt.report_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(xml)
    return stmt


def download_statement(cfg: Config) -> Statement:
    """Descarga el informe Flex del día y lo archiva en data/flex/."""
    if not cfg.flex.token or not cfg.flex.query_id:
        raise RuntimeError("Faltan IB_FLEX_TOKEN / IB_FLEX_QUERY_ID en .env")
    return _archive(cfg, fetch_statement_xml(cfg.flex.token, cfg.flex.query_id))


def import_statement(cfg: Config, path: Path) -> Statement:
    """Carga un informe Flex guardado a mano y lo archiva como si se hubiera descargado."""
    return _archive(cfg, Path(path).read_bytes())


def load_statement_file(cfg: Config, path: Path) -> Statement:
    return complete_fx(parse_statement(Path(path).read_bytes(), cfg.base_currency), cfg.base_currency)


def latest_archived_statement(cfg: Config) -> Statement:
    files = sorted(cfg.flex_dir.glob("*.xml"))
    if not files:
        raise RuntimeError("No hay informes Flex guardados todavía. Ejecuta primero: divmon daily")
    return load_statement_file(cfg, files[-1])


def refresh_fundamentals(
    cfg: Config,
    store: Store,
    stmt: Statement,
    provider: FundamentalsProvider | None = None,
) -> dict[str, Fundamentals]:
    """Devuelve fundamentales de posiciones y candidatas, usando la caché si es reciente."""
    wanted: dict[str, str] = {
        p.symbol: yahoo_symbol(p.symbol, p.listing_exchange, cfg.symbols.get(p.symbol)) for p in stmt.positions
    }
    for c in cfg.radar.candidates:
        wanted.setdefault(c.symbol, c.yahoo or yahoo_symbol(c.symbol, None, cfg.symbols.get(c.symbol)))

    today = date.today()
    cached = store.latest_fundamentals(list(wanted), cfg.fundamentals.max_age_days, today)
    provider = provider or make_provider(cfg.fundamentals.provider)
    fresh = []
    for symbol, ysym in wanted.items():
        if symbol in cached:
            continue
        try:
            fresh.append(provider.get(symbol, ysym))
        except Exception as exc:   # un valor que falla no debe tumbar el resto
            log.warning("Sin fundamentales para %s (%s): %s", symbol, ysym, exc)
    if fresh:
        store.save_fundamentals(today, fresh)
    merged = {**cached, **{f.symbol: f for f in fresh}}
    return {
        s: merged.get(s, Fundamentals(symbol=s)).with_override(cfg.override(s)) for s in wanted
    }


# --- Análisis ---------------------------------------------------------------------------------


def analyze(
    cfg: Config,
    stmt: Statement,
    history: list[CashTransaction],
    fundamentals: dict[str, Fundamentals],
    live: LiveMargin | None = None,
) -> Analysis:
    forecast = forecast_dividends(stmt, history, fundamentals)
    holdings = build_holdings(stmt, cfg, fundamentals, forecast.by_symbol_gross)
    margin = compute_margin(stmt, cfg, history, live)
    currencies = currency_exposure(stmt)
    breaches = check_concentration(holdings, currencies, cfg.concentration, cfg.base_currency)

    held = {h.symbol for h in holdings}
    # En tus posiciones, la rentabilidad sale de tus propios cobros si el proveedor no la da.
    fundamentals = dict(fundamentals)
    for h in holdings:
        fund = fundamentals.get(h.symbol)
        if fund and fund.dividend_yield is None and h.current_yield is not None:
            fundamentals[h.symbol] = replace(fund, dividend_yield=h.current_yield)
    radar =[evaluate(fundamentals[s], cfg.criteria_for(s), HOLDING) for s in sorted(held) if s in fundamentals]
    radar += [
        evaluate(fundamentals[c.symbol], cfg.criteria_for(c.symbol), CANDIDATE)
        for c in cfg.radar.candidates
        if c.symbol not in held and c.symbol in fundamentals
    ]

    plans: list[Plan] = []
    if margin.loan > 0:
        rate = margin.blended_rate
        if rate is None or margin.missing_rates:
            rate = cfg.margin.interest_rates.get(cfg.base_currency, 0.0)
        profile = [n for _, n in list(forecast.monthly.values())[1:13]]
        a = cfg.amortization
        plans = standard_plans(margin.loan, a.monthly_contribution, rate, profile, a.dividend_growth, a.dividends_to_debt)

    return Analysis(stmt, history, fundamentals, holdings, forecast, margin, currencies, breaches, radar, plans)


def build_alerts(cfg: Config, analysis: Analysis, previous_radar: dict[str, str]) -> tuple[list[Alert], list[Transition]]:
    changes = transitions(analysis.radar, previous_radar)
    alerts = [
        *analysis.warnings,
        *margin_alerts(analysis.margin, cfg),
        *concentration_alerts(analysis.breaches, cfg.concentration.cooldown_hours),
        *radar_alerts(changes, cfg, analysis.stmt, analysis.margin),
    ]
    return alerts, changes


def persist(store: Store, analysis: Analysis) -> None:
    m = analysis.margin
    store.save_account_snapshot(
        analysis.stmt.report_date,
        net_liquidation=m.net_liquidation,
        gross_position_value=m.gross_position_value,
        loan=m.loan,
        maintenance_margin=m.maintenance_margin,
        margin_source=m.margin_source,
        excess_liquidity=m.excess_liquidity,
        annual_dividends_net=analysis.forecast.annual_net,
    )
    for r in analysis.radar:
        if r.status != INCOMPLETE:
            store.set_radar_state(r.symbol, r.role, r.status)

