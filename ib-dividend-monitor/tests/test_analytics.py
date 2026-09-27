from datetime import date

import pytest

from divmon.analytics.amortization import simulate
from divmon.analytics.concentration import check_concentration
from divmon.analytics.dividends import ANNOUNCED, forecast_dividends, received_by_year
from divmon.analytics.margin import LiveMargin, compute_margin
from divmon.analytics.portfolio import build_holdings, currency_exposure
from divmon.analytics.radar import CANDIDATE, FAILS, HOLDING, INCOMPLETE, MEETS, evaluate, transitions
from divmon.config import Criteria
from divmon.sources.fundamentals import Fundamentals

GROSS = 25500 + 10400 + 10800 + 15000 * 0.9 + 17400 * 0.9 + 13200 * 1.18


def test_margin_estimated(stmt, cfg):
    m = compute_margin(stmt, cfg)
    assert m.gross_position_value == pytest.approx(GROSS)
    assert m.loan == pytest.approx(25000)
    assert m.net_liquidation == pytest.approx(GROSS - 25000 + 300 * 0.9)
    assert m.maintenance_margin == pytest.approx(GROSS * 0.25)
    assert m.estimated_annual_interest == pytest.approx(25000 * 0.045)
    # Caída uniforme d que agota el exceso: EL - d·(GPV - MM) = 0
    el = m.net_liquidation - m.maintenance_margin
    assert m.drop_to_margin_call == pytest.approx(el / (GROSS * 0.75))
    assert m.interest_last_month == pytest.approx(95)


def test_margin_live_overrides_estimate(stmt, cfg):
    live = LiveMargin(net_liquidation=60000, maintenance_margin=30000, excess_liquidity=30000, gross_position_value=90000)
    m = compute_margin(stmt, cfg, live=live)
    assert m.margin_source == "IB Gateway"
    assert m.cushion == pytest.approx(0.5)
    assert m.drop_to_margin_call == pytest.approx(0.5)


def test_margin_without_loan_has_no_call_distance(stmt, cfg):
    stmt.cash = [c for c in stmt.cash if c.ending_cash > 0]
    assert compute_margin(stmt, cfg).drop_to_margin_call is None


def test_dividend_forecast(stmt):
    f = forecast_dividends(stmt, stmt.transactions)
    mo = [e for e in f.events if e.symbol == "MO"]
    # El dividendo anunciado de octubre sustituye al estimado; quedan 4 pagos.
    assert len(mo) == 4
    assert [e.status for e in mo].count(ANNOUNCED) == 1
    assert mo[0].net_base == pytest.approx(270.3 * 0.9)
    o = [e for e in f.events if e.symbol == "O"]
    assert len(o) == 12
    assert o[0].gross_base == pytest.approx(0.2695 * 250 * 0.9)
    assert o[0].net_base == pytest.approx(o[0].gross_base * 0.85, rel=1e-3)
    assert all(stmt.report_date < e.pay_date <= date(2027, 9, 25) for e in f.events)
    assert f.by_symbol_gross["SAN"] == pytest.approx(0.10 * 3000 + 0.11 * 3000)
    assert f.annual_net < f.annual_gross
    assert sum(1 for _ in f.monthly) == 13


def test_forecast_uses_provider_yield_without_history(stmt):
    stmt.transactions = [t for t in stmt.transactions if t.symbol != "ALV"]
    f = forecast_dividends(stmt, stmt.transactions, {"ALV": Fundamentals("ALV", dividend_yield=0.05)})
    assert f.flat_symbols == ["ALV"]
    assert f.by_symbol_gross["ALV"] == pytest.approx(10800 * 0.05)


def test_received_by_year(stmt):
    years = received_by_year(stmt.transactions)
    assert years[2024] == pytest.approx((285, 285 - 54.15))


def test_holdings_and_yield_on_cost(stmt, cfg):
    f = forecast_dividends(stmt, stmt.transactions)
    holdings = build_holdings(stmt, cfg, {}, f.by_symbol_gross)
    assert holdings[0].symbol == "SAN"
    assert sum(h.weight for h in holdings) == pytest.approx(1)
    san = holdings[0]
    assert san.yield_on_cost == pytest.approx(630 / 15000)
    assert san.country == "ES" and san.sector == "Sin dato"
    eng = next(h for h in holdings if h.symbol == "ENG")
    assert eng.sector == "Utilities"


def test_currency_exposure_is_net_of_loans(stmt):
    exp = {e.name: e for e in currency_exposure(stmt)}
    assert exp["EUR"].value_base == pytest.approx(25500 + 10400 + 10800 - 25000)
    assert sum(e.weight for e in exp.values()) == pytest.approx(1)


def test_concentration(stmt, cfg):
    holdings = build_holdings(stmt, cfg, {}, {})
    breaches = check_concentration(holdings, currency_exposure(stmt), cfg.concentration, "EUR")
    kinds = {(b.kind, b.name) for b in breaches}
    assert ("posición", "SAN") in kinds
    assert ("país", "ES") in kinds
    assert ("divisa", "USD") in kinds
    assert not any(b.kind == "divisa" and b.name == "EUR" for b in breaches)
    assert not any(b.kind == "sector" for b in breaches), "'Sin dato' no cuenta como sector"


def test_amortization_zero_rate():
    plan = simulate(12000, 1000, 0.0)
    assert plan.months == 12 and plan.total_interest == 0
    assert plan.payoff_date(date(2026, 9, 25)) == date(2027, 9, 1)


def test_amortization_with_dividends_is_faster():
    base = simulate(25000, 500, 0.045)
    with_div = simulate(25000, 500, 0.045, [350] * 12)
    assert with_div.months < base.months
    assert base.total_interest > with_div.total_interest > 0


def test_amortization_never_pays_off():
    plan = simulate(100000, 100, 0.06)
    assert plan.months is None and plan.payoff_date(date.today()) is None


CRIT = Criteria(per_max=15, dividend_yield_min=0.045, payout_max=0.8, debt_ebitda_max=3.5)


def test_radar_evaluate():
    ok = evaluate(Fundamentals("A", per=10, dividend_yield=0.05, payout=0.6, debt_ebitda=2), CRIT, CANDIDATE)
    assert ok.status == MEETS
    bad = evaluate(Fundamentals("B", per=-5, dividend_yield=0.05, payout=0.6, debt_ebitda=2), CRIT, CANDIDATE)
    assert bad.status == FAILS and [c.name for c in bad.failing()] == ["PER"]
    missing = evaluate(Fundamentals("C", per=10, dividend_yield=0.05), CRIT, CANDIDATE)
    assert missing.status == INCOMPLETE


def test_radar_symbol_override_disables_criterion():
    reit = Fundamentals("O", per=50, dividend_yield=0.055, payout=2.5, debt_ebitda=3)
    crit = CRIT.merged({"payout_max": None, "per_max": None})
    assert evaluate(reit, crit, HOLDING).status == MEETS


def test_radar_transitions():
    cand = evaluate(Fundamentals("A", per=10, dividend_yield=0.05, payout=0.6, debt_ebitda=2), CRIT, CANDIDATE)
    held_bad = evaluate(Fundamentals("B", per=30, dividend_yield=0.05, payout=0.6, debt_ebitda=2), CRIT, HOLDING)
    held_ok = evaluate(Fundamentals("C", per=10, dividend_yield=0.05, payout=0.6, debt_ebitda=2), CRIT, HOLDING)
    first = transitions([cand, held_bad, held_ok], {})
    assert {t.result.symbol for t in first} == {"A", "B"}
    assert transitions([cand, held_bad, held_ok], {"A": MEETS, "B": FAILS, "C": MEETS}) == []
    back = transitions([held_ok], {"C": FAILS})
    assert [t.result.symbol for t in back] == ["C"]
