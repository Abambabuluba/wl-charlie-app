"""Reglas de alerta y envío por Telegram (o consola), con enfriamiento para no repetir avisos."""

from __future__ import annotations

import html
import logging
import re
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

import requests

from divmon.analytics.concentration import Breach
from divmon.analytics.margin import MarginStatus
from divmon.analytics.radar import CANDIDATE, FAILS, MEETS, Transition
from divmon.config import Config
from divmon.models import Statement
from divmon.storage import Store

log = logging.getLogger(__name__)

WARNING = "aviso"
CRITICAL = "crítico"
TELEGRAM_LIMIT = 4000


@dataclass
class Alert:
    key: str
    severity: str
    text: str


def pct(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value * 100:.{digits}f} %".replace(".", ",")


def money(value: float | None, currency: str = "EUR") -> str:
    if value is None:
        return "—"
    s = f"{value:,.0f}".replace(",", ".")
    return f"{s} €" if currency == "EUR" else f"{s} {currency}"


# --- Reglas ------------------------------------------------------------------------------------


def margin_alerts(m: MarginStatus, cfg: Config) -> list[Alert]:
    a, cur, out = cfg.margin.alerts, cfg.base_currency, []
    source = "" if m.margin_source == "IB Gateway" else " (margen estimado)"
    if m.loan <= 0:
        return out
    if a.loan_to_value_max is not None and m.loan_to_value > a.loan_to_value_max:
        out.append(Alert(
            "margin:ltv", WARNING,
            f"Préstamo de margen al {pct(m.loan_to_value)} del valor de la cartera "
            f"(límite {pct(a.loan_to_value_max)}). Deuda: {money(m.loan, cur)}.",
        ))
    if a.cushion_min is not None and m.cushion is not None and m.cushion < a.cushion_min:
        severity = CRITICAL if m.cushion < a.cushion_min / 2 else WARNING
        out.append(Alert(
            "margin:cushion", severity,
            f"Colchón de margen en {pct(m.cushion)} (mínimo {pct(a.cushion_min)}){source}. "
            f"Exceso de liquidez: {money(m.excess_liquidity, cur)}.",
        ))
    drop = m.drop_to_margin_call
    if a.drop_to_call_min is not None and drop is not None and drop < a.drop_to_call_min:
        severity = CRITICAL if drop < a.drop_to_call_min / 2 else WARNING
        out.append(Alert(
            "margin:drop", severity,
            f"Una caída del {pct(drop)} de toda la cartera provocaría margin call "
            f"(tu mínimo es {pct(a.drop_to_call_min)}){source}.",
        ))
    if m.missing_rates:
        out.append(Alert(
            "margin:rates", WARNING,
            f"Tienes deuda en {', '.join(m.missing_rates)} sin tipo de interés en config.yaml; "
            "los intereses estimados están incompletos.",
        ))
    return out


def concentration_alerts(breaches: list[Breach]) -> list[Alert]:
    return [
        Alert(
            f"conc:{b.kind}:{b.name}", WARNING,
            f"Concentración por {b.kind}: {b.name} pesa {pct(b.weight)} (límite {pct(b.limit)}).",
        )
        for b in breaches
    ]


PERCENT_METRICS = ("Rentabilidad", "Payout")


def _fmt(name: str, value: float) -> str:
    return pct(value) if name in PERCENT_METRICS else f"{value:.1f}".replace(".", ",")


def _shares_hint(t: Transition, target_weight: float, nlv: float, stmt: Statement) -> str:
    f = t.result.fundamentals
    if not f.price or not f.currency or nlv <= 0:
        return ""
    price, currency = f.price, f.currency
    if currency == "GBp":            # Yahoo cotiza Londres en peniques
        price, currency = price / 100, "GBP"
    fx = stmt.fx_to_base.get(currency)
    if not fx:
        return ""
    shares = int(target_weight * nlv / (price * fx))
    if not shares:
        return ""
    return f" Con tu peso de referencia ({pct(target_weight)}) serían unas {shares} acciones a {price:,.2f} {currency}."


def radar_alerts(changes: list[Transition], cfg: Config, stmt: Statement, margin: MarginStatus) -> list[Alert]:
    out = []
    for t in changes:
        r, f = t.result, t.result.fundamentals
        metrics = ", ".join(f"{c.name} {_fmt(c.name, c.value)}" for c in r.checks if c.value is not None)
        if r.role == CANDIDATE and r.status == MEETS:
            text = f"🟢 {r.symbol} cumple tus criterios de compra ({metrics})."
            text += _shares_hint(t, cfg.radar.target_weight, margin.net_liquidation, stmt)
            rate = margin.blended_rate
            if margin.loan > 0 and rate is not None and f.dividend_yield is not None:
                comparison = "más" if f.dividend_yield > rate else "menos"
                text += (
                    f" Ojo: tu plan es amortizar margen. Su rentabilidad ({pct(f.dividend_yield)}) da {comparison} "
                    f"de lo que te cuesta la deuda ({pct(rate)})."
                )
            text += " Es una propuesta para que la valores tú: no se ha enviado ninguna orden."
        elif r.status == FAILS:
            fails = ", ".join(
                f"{c.name} {_fmt(c.name, c.value)} (límite {_fmt(c.name, c.limit)})" for c in r.failing()
            )
            text = f"🟠 Tu posición {r.symbol} se aleja de tus criterios: {fails}. Revísala; no hace falta actuar ya."
        else:
            text = f"🔵 Tu posición {r.symbol} vuelve a cumplir tus criterios ({metrics})."
        out.append(Alert(f"radar:{r.symbol}:{r.status}", WARNING, text))
    return out


# --- Envío -------------------------------------------------------------------------------------


class Notifier(Protocol):
    def send(self, text: str) -> None: ...
    def send_report(self, summary: str, path: Path, subject: str) -> None: ...


class ConsoleNotifier:
    def send(self, text: str) -> None:
        print(text)

    def send_report(self, summary: str, path: Path, subject: str) -> None:
        print(f"{subject}\n{summary}\n[archivo] {path}")


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, session: requests.Session | None = None):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id
        self.http = session or requests.Session()

    def send(self, text: str) -> None:
        for chunk in _chunks(text, TELEGRAM_LIMIT):
            resp = self.http.post(
                f"{self.base}/sendMessage",
                data={"chat_id": self.chat_id, "text": chunk, "parse_mode": "HTML", "disable_web_page_preview": "true"},
                timeout=20,
            )
            _check(resp)

    def send_report(self, summary: str, path: Path, subject: str) -> None:
        self.send(html.escape(summary))
        with open(path, "rb") as fh:
            resp = self.http.post(
                f"{self.base}/sendDocument",
                data={"chat_id": self.chat_id, "caption": subject[:1000]},
                files={"document": (path.name, fh)},
                timeout=60,
            )
        _check(resp)


class EmailNotifier:
    """Correo por SMTP con SSL. Con Gmail se usa una contraseña de aplicación, no la de la cuenta."""

    def __init__(self, host: str, port: int, user: str, password: str, to: str, smtp_factory=smtplib.SMTP_SSL):
        self.host, self.port, self.user, self.password, self.to = host, port, user, password, to
        self.smtp_factory = smtp_factory

    def send(self, text: str) -> None:
        first = re.sub(r"<[^>]+>", "", text.split("\n", 1)[0])
        self._deliver(html.unescape(first) or "divmon", text)

    def send_report(self, summary: str, path: Path, subject: str) -> None:
        self._deliver(subject, html.escape(summary), attachment=path)

    def _deliver(self, subject: str, html_body: str, attachment: Path | None = None) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject[:150]
        msg["From"] = self.user
        msg["To"] = self.to
        plain = html.unescape(re.sub(r"<[^>]+>", "", html_body))
        msg.set_content(plain)
        msg.add_alternative(
            '<div style="font-family:sans-serif;font-size:14px;line-height:1.5">'
            + html_body.replace("\n", "<br>") + "</div>",
            subtype="html",
        )
        if attachment:
            msg.add_attachment(Path(attachment).read_bytes(), maintype="text", subtype="html",
                               filename=Path(attachment).name)
        try:
            with self.smtp_factory(self.host, self.port, timeout=30) as smtp:
                smtp.login(self.user, self.password)
                smtp.send_message(msg)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(
                "El servidor de correo rechazó el usuario o la contraseña. Con Gmail necesitas una "
                "contraseña de aplicación (ver README)."
            ) from exc


def _check(resp: requests.Response) -> None:
    if resp.status_code != 200 or not resp.json().get("ok"):
        raise RuntimeError(f"Telegram rechazó el mensaje ({resp.status_code}): {resp.text[:200]}")


def _chunks(text: str, size: int) -> list[str]:
    out, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > size and current:
            out.append(current)
            current = ""
        current += line
    return [*out, current] if current else out


def make_notifier(cfg: Config) -> Notifier:
    a = cfg.alerts
    if a.channel == "console":
        return ConsoleNotifier()
    if a.channel == "email":
        if not a.smtp_user or not a.smtp_password:
            raise RuntimeError("Faltan SMTP_USER / SMTP_PASSWORD en .env (o usa alerts.channel: console)")
        return EmailNotifier(a.smtp_host, a.smtp_port, a.smtp_user, a.smtp_password, a.email_to or a.smtp_user)
    if not a.telegram_token or not a.telegram_chat_id:
        raise RuntimeError("Faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID en .env (o usa alerts.channel: console)")
    return TelegramNotifier(a.telegram_token, a.telegram_chat_id)


def dispatch(
    alerts: list[Alert],
    store: Store,
    notifier: Notifier,
    cooldown_hours: float,
    title: str = "Cartera IBKR",
    now: datetime | None = None,
) -> list[Alert]:
    """Envía en un único mensaje las alertas que no se hayan enviado dentro del periodo de enfriamiento."""
    now = now or datetime.now()
    fresh = []
    for a in alerts:
        last = store.last_alert_time(a.key)
        if last is None or now - last >= timedelta(hours=cooldown_hours):
            fresh.append(a)
    if not fresh:
        return []
    fresh.sort(key=lambda a: a.severity != CRITICAL)
    heading = f"{'🔴 ' if fresh[0].severity == CRITICAL else ''}{title}: {len(fresh)} aviso{'s' if len(fresh) > 1 else ''}"
    lines = [f"<b>{html.escape(heading)}</b>"]
    lines += [f"{'🔴' if a.severity == CRITICAL else '•'} {html.escape(a.text)}" for a in fresh]
    notifier.send("\n\n".join(lines))
    for a in fresh:
        store.log_alert(a.key, a.severity, a.text, delivered=True, ts=now)
    return fresh
