"""Informe semanal en HTML autocontenido (y PDF opcional)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from divmon.alerts import money, pct
from divmon.analytics.dividends import received_by_month, received_by_year
from divmon.analytics.portfolio import exposure
from divmon.config import Config
from divmon.report import charts
from divmon.service import Analysis
from divmon.storage import Store


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, 1)


def build_context(cfg: Config, analysis: Analysis, store: Store, news: dict | None = None) -> dict:
    a, m, f = analysis, analysis.margin, analysis.forecast
    today = a.stmt.report_date
    lim = cfg.concentration

    sectors = [(e.name, e.weight) for e in exposure(a.holdings, "sector")]
    countries = [(e.name, e.weight) for e in exposure(a.holdings, "country")]
    currencies = [(e.name, e.weight) for e in a.currencies]
    received = received_by_month(a.history, 12, today)

    history = store.account_history(today - timedelta(days=730))
    history_chart = None
    if len(history) >= 2:
        xs = [date.fromisoformat(r["date"]) for r in history]
        history_chart = charts.lines(
            "Valor liquidativo y préstamo de margen",
            xs,
            [("Valor liquidativo", [r["net_liquidation"] for r in history]), ("Préstamo", [r["loan"] for r in history])],
        )

    plan_chart = None
    if a.plans:
        longest = max(len(p.balances) for p in a.plans)
        xs = [_add_months(today, i) for i in range(longest)]
        plan_chart = charts.lines("Deuda de margen pendiente", xs, [(p.label, p.balances) for p in a.plans])

    forecast_months = list(f.monthly)[1:13]
    return {
        "cfg": cfg,
        "a": a,
        "m": m,
        "f": f,
        "today": today,
        "generated": datetime.now(),
        "money": lambda v: money(v, cfg.base_currency),
        "pct": pct,
        "sectors": sectors,
        "countries": countries,
        "currencies": currencies,
        "received_years": received_by_year(a.history),
        "upcoming": f.upcoming(60),
        "recent_alerts": store.recent_alerts(datetime.now() - timedelta(days=7)),
        "total_value": sum(h.value_base for h in a.holdings),
        "total_cost": sum(h.cost_base for h in a.holdings),
        "charts": {
            "positions": charts.weights_bar("Peso por posición", [(h.symbol, h.weight) for h in a.holdings], lim.position_max),
            "sectors": charts.weights_bar("Sector", sectors, lim.sector_max),
            "countries": charts.weights_bar("País (domicilio)", countries, lim.country_max),
            "currencies": charts.weights_bar("Divisa (neta de préstamos, sobre valor liquidativo)", currencies,
                                             None if lim.exclude_base_currency else lim.currency_max),
            "forecast": charts.monthly_bar("Dividendos netos previstos por mes", forecast_months,
                                           [f.monthly[k][1] for k in forecast_months]),
            "received": charts.monthly_bar("Dividendos netos cobrados (últimos 12 meses)", list(received),
                                           [n for _, n in received.values()]),
            "plan": plan_chart,
            "history": history_chart,
        },
        "plan_rows": [(p, p.payoff_date(today)) for p in a.plans],
        "news": {h.symbol: news[h.symbol] for h in a.holdings if news and news.get(h.symbol)},
        "news_checked": news is not None,
    }


def render_html(cfg: Config, analysis: Analysis, store: Store, news: dict | None = None) -> str:
    env = Environment(loader=PackageLoader("divmon", "report/templates"), autoescape=select_autoescape(["j2", "html"]))
    return env.get_template("weekly.html.j2").render(**build_context(cfg, analysis, store, news))


def write_report(cfg: Config, analysis: Analysis, store: Store, pdf: bool = False, news: dict | None = None) -> Path:
    cfg.reports_dir.mkdir(parents=True, exist_ok=True)
    stem = cfg.reports_dir / f"informe-{analysis.stmt.report_date.isoformat()}"
    html_text = render_html(cfg, analysis, store, news)
    html_path = stem.with_suffix(".html")
    html_path.write_text(html_text, encoding="utf-8")
    if not pdf:
        return html_path
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError('Para PDF instala el extra: pip install -e ".[pdf]"') from exc
    pdf_path = stem.with_suffix(".pdf")
    HTML(string=html_text).write_pdf(pdf_path)
    return pdf_path
