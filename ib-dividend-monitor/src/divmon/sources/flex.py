"""Flex Web Service de IBKR: descarga y lectura de informes Flex (solo lectura por diseño).

El servicio solo sirve informes ya generados por IBKR; no existe forma de operar con él.
"""

from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime

import requests

from divmon.models import CashBalance, CashTransaction, DividendAccrual, Position, Statement

SEND_REQUEST_URL = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest"
# IBKR rechaza peticiones sin User-Agent reconocible.
HEADERS = {"User-Agent": "Java"}
# Códigos que significan "vuelve a intentarlo en unos segundos".
RETRYABLE = {"1004", "1005", "1006", "1007", "1008", "1009", "1018", "1019", "1021"}
AUTH_ERRORS = {"1012": "el token ha caducado", "1015": "el token no es válido", "1013": "restricción de IP"}


class FlexError(RuntimeError):
    def __init__(self, code: str | None, message: str):
        self.code = code
        hint = AUTH_ERRORS.get(code or "")
        text = f"Flex {code}: {message}" if code else message
        if hint:
            text += f" ({hint}; genera uno nuevo en el Portal de IBKR y actualiza .env)"
        super().__init__(text)


def fetch_statement_xml(
    token: str,
    query_id: str,
    *,
    session: requests.Session | None = None,
    max_wait_seconds: int = 300,
    sleep=time.sleep,
) -> bytes:
    """Pide a IBKR que genere el informe y espera hasta poder descargarlo."""
    http = session or requests.Session()
    resp = http.get(SEND_REQUEST_URL, params={"t": token, "q": query_id, "v": "3"}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    if root.findtext("Status") != "Success":
        raise FlexError(root.findtext("ErrorCode"), root.findtext("ErrorMessage") or "respuesta inesperada")
    reference = root.findtext("ReferenceCode")
    url = root.findtext("Url")
    if not reference or not url:
        raise FlexError(None, "La respuesta de SendRequest no trae ReferenceCode/Url")

    waited, delay = 0, 5
    while True:
        resp = http.get(url, params={"t": token, "q": reference, "v": "3"}, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        if b"<FlexQueryResponse" in resp.content[:500]:
            return resp.content
        err = ET.fromstring(resp.content)
        code = err.findtext("ErrorCode")
        if code not in RETRYABLE or waited >= max_wait_seconds:
            raise FlexError(code, err.findtext("ErrorMessage") or "no se pudo descargar el informe")
        sleep(delay)
        waited += delay
        delay = min(delay * 2, 30)


# --- Lectura del XML --------------------------------------------------------------------------


def _num(value: str | None) -> float | None:
    if value is None or value.strip() in {"", "--"}:
        return None
    return float(value.replace(",", ""))


def _date(value: str | None) -> date | None:
    """Admite los formatos yyyyMMdd y yyyy-MM-dd (con o sin hora)."""
    if not value or not value.strip():
        return None
    head = value.strip().replace(";", " ").replace(",", " ").split()[0]
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            pass
    raise ValueError(
        f"Formato de fecha no soportado en el Flex: {value!r}. "
        "Configura la Flex Query con formato de fecha yyyyMMdd."
    )


def _rows(stmt: ET.Element, section: str, row: str) -> list[dict[str, str]]:
    container = stmt.find(section)
    return [dict(el.attrib) for el in container.iter(row)] if container is not None else []


def parse_statement(xml: bytes | str, base_currency: str) -> Statement:
    root = ET.fromstring(xml)
    statements = root.findall("./FlexStatements/FlexStatement")
    if not statements:
        raise ValueError("El XML no contiene ningún FlexStatement")
    if len(statements) > 1:
        raise ValueError("El informe contiene varias cuentas; configura la Flex Query para una sola")
    stmt = statements[0]
    report_date = _date(stmt.get("toDate")) or date.today()

    fx: dict[str, float] = {base_currency: 1.0}
    latest: dict[str, date] = {}
    for r in _rows(stmt, "ConversionRates", "ConversionRate"):
        if r.get("toCurrency") != base_currency:
            continue
        cur, day, rate = r.get("fromCurrency"), _date(r.get("reportDate")), _num(r.get("rate"))
        if cur and rate and (cur not in latest or (day and day >= latest[cur])):
            fx[cur], latest[cur] = rate, day or report_date

    positions = []
    for r in _rows(stmt, "OpenPositions", "OpenPosition"):
        if r.get("levelOfDetail", "SUMMARY").upper() not in {"SUMMARY", ""}:
            continue
        if r.get("assetCategory") == "CASH":
            continue
        currency = r["currency"]
        fx_rate = _num(r.get("fxRateToBase")) or fx.get(currency)
        if fx_rate is None:
            raise ValueError(f"Falta fxRateToBase para {r.get('symbol')}")
        fx.setdefault(currency, fx_rate)
        quantity = _num(r.get("position")) or 0.0
        cost = _num(r.get("costBasisMoney"))
        if cost is None:
            cost = (_num(r.get("costBasisPrice")) or 0.0) * quantity
        positions.append(
            Position(
                conid=r.get("conid", ""),
                symbol=r.get("symbol", ""),
                description=r.get("description", ""),
                currency=currency,
                quantity=quantity,
                mark_price=_num(r.get("markPrice")) or 0.0,
                value_local=_num(r.get("positionValue")) or 0.0,
                cost_local=cost,
                fx_to_base=fx_rate,
                asset_category=r.get("assetCategory", "STK"),
                isin=r.get("isin") or None,
                listing_exchange=r.get("listingExchange") or None,
                issuer_country=r.get("issuerCountryCode") or None,
            )
        )

    # Los restos de céntimo en divisas antiguas (p. ej. 0.0003 HKD) no aportan nada y no
    # suelen tener tipo de cambio en el informe: se descartan.
    cash = [
        CashBalance(currency=r["currency"], ending_cash=round(_num(r.get("endingCash")) or 0.0, 2))
        for r in _rows(stmt, "CashReport", "CashReportCurrency")
        if r.get("currency") and r["currency"] != "BASE_SUMMARY" and abs(_num(r.get("endingCash")) or 0.0) >= 0.01
    ]

    transactions = []
    tx_fx: dict[str, tuple[date, float]] = {}
    for r in _rows(stmt, "CashTransactions", "CashTransaction"):
        if r.get("levelOfDetail", "DETAIL").upper() not in {"DETAIL", ""}:
            continue
        day = _date(r.get("dateTime")) or _date(r.get("settleDate")) or _date(r.get("reportDate"))
        amount = _num(r.get("amount"))
        if day is None or amount is None:
            continue
        currency = r.get("currency", base_currency)
        explicit = _num(r.get("fxRateToBase"))
        if explicit and (currency not in tx_fx or day >= tx_fx[currency][0]):
            tx_fx[currency] = (day, explicit)
        fx_rate = explicit or fx.get(currency, 1.0)
        tid = r.get("transactionID") or hashlib.sha1(
            "|".join([r.get("type", ""), r.get("symbol", ""), str(day), r.get("amount", ""), r.get("description", "")]).encode()
        ).hexdigest()[:16]
        transactions.append(
            CashTransaction(
                transaction_id=tid,
                date=day,
                type=r.get("type", ""),
                currency=currency,
                amount=amount,
                fx_to_base=fx_rate,
                symbol=r.get("symbol") or None,
                conid=r.get("conid") or None,
                isin=r.get("isin") or None,
                description=r.get("description", ""),
            )
        )

    accruals = []
    for r in _rows(stmt, "OpenDividendAccruals", "OpenDividendAccrual"):
        currency = r.get("currency", base_currency)
        if _num(r.get("fxRateToBase")):
            tx_fx.setdefault(currency, (date.min, _num(r.get("fxRateToBase"))))
        accruals.append(
            DividendAccrual(
                conid=r.get("conid", ""),
                symbol=r.get("symbol", ""),
                currency=currency,
                ex_date=_date(r.get("exDate")),
                pay_date=_date(r.get("payDate")),
                quantity=_num(r.get("quantity")) or 0.0,
                gross_rate=_num(r.get("grossRate")) or 0.0,
                gross_amount=_num(r.get("grossAmount")) or 0.0,
                net_amount=_num(r.get("netAmount")) or 0.0,
                fx_to_base=_num(r.get("fxRateToBase")) or fx.get(currency, 1.0),
            )
        )

    # Sin la sección Conversion Rates, se usan los tipos explícitos que IBKR pone en dividendos,
    # intereses y dividendos anunciados (el más reciente de cada divisa).
    for currency, (_, rate) in tx_fx.items():
        fx.setdefault(currency, rate)

    return Statement(
        account_id=stmt.get("accountId", ""),
        report_date=report_date,
        positions=positions,
        cash=cash,
        transactions=transactions,
        accruals=accruals,
        fx_to_base=fx,
    )
