"""Línea de comandos: divmon <comando>. Ninguno envía órdenes."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from divmon.alerts import (
    Alert, ConsoleNotifier, WARNING, dispatch, make_notifier, margin_alerts, money, pct,
)
from divmon.analytics.amortization import simulate
from divmon.config import Config, load_config
from divmon.service import (
    Analysis, analyze, build_alerts, download_statement, import_statement, latest_archived_statement,
    load_statement_file, persist, refresh_fundamentals,
)
from divmon.storage import Store

log = logging.getLogger("divmon")


def format_summary(cfg: Config, a: Analysis) -> str:
    m, f, cur = a.margin, a.forecast, cfg.base_currency
    lines = [
        f"Cartera a {a.stmt.report_date:%d/%m/%Y}",
        f"  Valor liquidativo {money(m.net_liquidation, cur)} · posiciones {money(m.gross_position_value, cur)}",
        f"  Préstamo {money(m.loan, cur)} ({pct(m.loan_to_value)} de las posiciones) · "
        f"colchón {pct(m.cushion)} · caída hasta margin call {pct(m.drop_to_margin_call)} [{m.margin_source}]",
        f"  Intereses estimados {money(m.estimated_annual_interest, cur)}/año ({pct(m.blended_rate)})",
        f"  Dividendos próximos 12 meses: {money(f.annual_net, cur)} netos (≈ {money(f.annual_net / 12, cur)}/mes)",
    ]
    for p in a.plans:
        payoff = p.payoff_date(a.stmt.report_date)
        lines.append(f"  Plan «{p.label}»: " + (f"deuda a cero en {p.months} meses ({payoff:%m/%Y})" if payoff else "no se amortiza"))
    upcoming = f.upcoming(30)
    if upcoming:
        lines.append("  Próximos cobros (30 días): " + ", ".join(
            f"{e.symbol} {e.pay_date:%d/%m} {money(e.net_base, cur)}" for e in upcoming))
    return "\n".join(lines)


def _run_analysis(cfg: Config, store: Store, xml: Path | None) -> tuple[Analysis | None, list[Alert]]:
    warnings: list[Alert] = []
    try:
        stmt = import_statement(cfg, xml) if xml else download_statement(cfg)
    except Exception as exc:
        log.error("No se pudo obtener el informe Flex: %s", exc)
        return None, [Alert("flex:error", WARNING, f"No se pudo descargar el informe Flex de IBKR: {exc}")]
    store.save_statement(stmt)
    history = store.cash_transactions()
    fundamentals = refresh_fundamentals(cfg, store, stmt)

    live = None
    if cfg.ib_gateway.enabled:
        from divmon.sources.ib_gateway import fetch_live_margin

        g = cfg.ib_gateway
        try:
            live = fetch_live_margin(g.host, g.port, g.client_id, cfg.base_currency)
        except Exception as exc:
            warnings.append(Alert(
                "gateway:down", WARNING,
                f"IB Gateway no responde ({exc}). ¿Toca reautenticar? Mientras tanto uso el margen estimado.",
            ))

    analysis = analyze(cfg, stmt, history, fundamentals, live)
    analysis.warnings = warnings
    return analysis, warnings


def cmd_daily(cfg: Config, args) -> int:
    store = Store(cfg.db_path)
    notifier = ConsoleNotifier() if args.dry_run else make_notifier(cfg)
    analysis, failures = _run_analysis(cfg, store, args.xml)
    if analysis is None:
        if args.dry_run:
            print(failures[0].text)
        else:
            dispatch(failures, store, notifier, cfg.alerts.cooldown_hours)
        return 1

    alerts, _ = build_alerts(cfg, analysis, store.radar_states())
    print(format_summary(cfg, analysis))
    if args.dry_run:
        print("\n[simulación] Alertas que se enviarían:")
        for a in alerts:
            print(f"  - ({a.severity}) {a.text}")
        if not alerts:
            print("  (ninguna)")
        return 0
    sent = dispatch(alerts, store, notifier, cfg.alerts.cooldown_hours)
    persist(store, analysis)
    print(f"\nAlertas enviadas: {len(sent)} de {len(alerts)} (el resto ya se avisó hace menos de {cfg.alerts.cooldown_hours:.0f} h)")
    return 0


def cmd_report(cfg: Config, args) -> int:
    from divmon.report import write_report

    store = Store(cfg.db_path)
    stmt = load_statement_file(cfg, args.xml) if args.xml else latest_archived_statement(cfg)
    history = store.cash_transactions()
    analysis = analyze(cfg, stmt, history, refresh_fundamentals(cfg, store, stmt))
    path = write_report(cfg, analysis, store, pdf=args.pdf)
    print(f"Informe generado: {path}")
    if args.send:
        notifier = make_notifier(cfg)
        notifier.send(format_summary(cfg, analysis))
        notifier.send_file(path, caption=f"Informe semanal {stmt.report_date:%d/%m/%Y}")
    return 0


def cmd_summary(cfg: Config, args) -> int:
    store = Store(cfg.db_path)
    stmt = load_statement_file(cfg, args.xml) if args.xml else latest_archived_statement(cfg)
    analysis = analyze(cfg, stmt, store.cash_transactions(), refresh_fundamentals(cfg, store, stmt))
    print(format_summary(cfg, analysis))
    print("\nPosiciones:")
    for h in analysis.holdings:
        print(f"  {h.symbol:<8} {pct(h.weight):>8} {money(h.value_base, cfg.base_currency):>12}  "
              f"{h.country:<4} {h.sector[:22]:<22} rent. s/coste {pct(h.yield_on_cost)}")
    print("\nRadar:")
    for r in analysis.radar:
        extra = ", ".join(c.name for c in r.failing()) or ", ".join(c.name for c in r.missing())
        print(f"  {r.symbol:<8} {r.role:<10} {r.status:<18} {extra}")
    return 0


def cmd_plan(cfg: Config, args) -> int:
    store = Store(cfg.db_path)
    stmt = load_statement_file(cfg, args.xml) if args.xml else latest_archived_statement(cfg)
    analysis = analyze(cfg, stmt, store.cash_transactions(), refresh_fundamentals(cfg, store, stmt))
    m = analysis.margin
    if m.loan <= 0:
        print("No tienes préstamo de margen.")
        return 0
    rate = m.blended_rate or cfg.margin.interest_rates.get(cfg.base_currency, 0.0)
    profile = [n for _, n in list(analysis.forecast.monthly.values())[1:13]]
    print(f"Deuda actual {money(m.loan)} al {pct(rate)} · dividendos netos {money(sum(profile))}/año\n")
    print(f"{'Aportación/mes':>15} {'Con dividendos':>18} {'Solo aportación':>18}")
    amounts = sorted({args.aportacion or cfg.amortization.monthly_contribution, 250, 500, 750, 1000})
    for amount in amounts:
        with_div = simulate(m.loan, amount, rate, profile, cfg.amortization.dividend_growth)
        only = simulate(m.loan, amount, rate)
        fmt = lambda p: f"{p.months} meses" if p.months is not None else "nunca"
        print(f"{money(amount):>15} {fmt(with_div):>18} {fmt(only):>18}")
    return 0


def cmd_margin_live(cfg: Config, args) -> int:
    """Comprobación intradía del margen con IB Gateway (requiere ib_gateway.enabled)."""
    from divmon.analytics.margin import compute_margin
    from divmon.sources.ib_gateway import fetch_live_margin

    store = Store(cfg.db_path)
    notifier = ConsoleNotifier() if args.dry_run else make_notifier(cfg)
    g = cfg.ib_gateway
    if not g.enabled:
        print("IB Gateway está desactivado en config.yaml (ib_gateway.enabled).")
        return 2
    try:
        live = fetch_live_margin(g.host, g.port, g.client_id, cfg.base_currency)
    except Exception as exc:
        dispatch([Alert("gateway:down", WARNING, f"IB Gateway no responde ({exc}). ¿Toca reautenticar?")],
                 store, notifier, cfg.alerts.cooldown_hours)
        return 1
    status = compute_margin(latest_archived_statement(cfg), cfg, store.cash_transactions(), live)
    alerts = margin_alerts(status, cfg)
    dispatch(alerts, store, notifier, cfg.alerts.cooldown_hours)
    print(f"Colchón {pct(status.cushion)} · caída hasta margin call {pct(status.drop_to_margin_call)}")
    return 0


def cmd_import_history(cfg: Config, args) -> int:
    """Carga dividendos, retenciones e intereses de informes Flex antiguos (no toca posiciones)."""
    store = Store(cfg.db_path)
    total = 0
    for path in args.files:
        new = store.save_transactions(load_statement_file(cfg, path).transactions)
        print(f"{path}: {new} movimientos nuevos")
        total += new
    print(f"Total: {total} movimientos añadidos al histórico")
    return 0


def cmd_test_telegram(cfg: Config, args) -> int:
    make_notifier(cfg).send("✅ divmon conectado. Aquí recibirás las alertas de tu cartera.")
    print("Mensaje de prueba enviado.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="divmon", description="Monitor de solo lectura de tu cartera en IBKR.")
    parser.add_argument("--config", default="config.yaml", help="ruta a config.yaml")
    parser.add_argument("--env", default=".env", help="ruta al archivo .env")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, func, help_text: str, xml: bool = True, dry: bool = False):
        p = sub.add_parser(name, help=help_text)
        if xml:
            p.add_argument("--xml", type=Path, help="usar un informe Flex guardado en lugar de descargarlo")
        if dry:
            p.add_argument("--dry-run", action="store_true", help="mostrar las alertas por pantalla sin enviarlas")
        p.set_defaults(func=func)
        return p

    add("daily", cmd_daily, "descargar el Flex, analizar, guardar histórico y alertar", dry=True)
    rp = add("report", cmd_report, "generar el informe semanal")
    rp.add_argument("--pdf", action="store_true", help="generar PDF (requiere el extra [pdf])")
    rp.add_argument("--send", action="store_true", help="enviar el informe por Telegram")
    add("summary", cmd_summary, "resumen por pantalla")
    pp = add("plan", cmd_plan, "plan de amortización del margen")
    pp.add_argument("--aportacion", type=float, help="aportación mensual a simular")
    add("margin-live", cmd_margin_live, "comprobar el margen en tiempo real con IB Gateway", xml=False, dry=True)
    hp = add("import-history", cmd_import_history, "importar el histórico de cobros de informes Flex antiguos", xml=False)
    hp.add_argument("files", nargs="+", type=Path, help="archivos XML de Flex")
    add("test-telegram", cmd_test_telegram, "enviar un mensaje de prueba", xml=False)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    try:
        cfg = load_config(args.config, args.env)
        return args.func(cfg, args)
    except Exception as exc:
        if args.verbose:
            raise
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
