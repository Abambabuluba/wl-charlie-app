"""Estructuras de datos comunes. Los importes *_local van en la divisa del valor."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

DIVIDEND_TYPES = frozenset({"Dividends", "Payment In Lieu Of Dividends"})
WITHHOLDING_TYPE = "Withholding Tax"
INTEREST_PAID_TYPE = "Broker Interest Paid"
INTEREST_RECEIVED_TYPE = "Broker Interest Received"

_PER_SHARE_RE = re.compile(r"\b([A-Z]{3})\s+([0-9]*\.?[0-9]+)\s+per\s+share", re.IGNORECASE)


@dataclass
class Position:
    conid: str
    symbol: str
    description: str
    currency: str
    quantity: float
    mark_price: float
    value_local: float
    cost_local: float
    fx_to_base: float
    asset_category: str = "STK"
    isin: str | None = None
    listing_exchange: str | None = None
    issuer_country: str | None = None

    @property
    def value_base(self) -> float:
        return self.value_local * self.fx_to_base

    @property
    def cost_base(self) -> float:
        return self.cost_local * self.fx_to_base

    @property
    def unrealized_base(self) -> float:
        return self.value_base - self.cost_base


@dataclass
class CashBalance:
    currency: str
    ending_cash: float


@dataclass
class CashTransaction:
    transaction_id: str
    date: date
    type: str
    currency: str
    amount: float
    fx_to_base: float
    symbol: str | None = None
    conid: str | None = None
    isin: str | None = None
    description: str = ""

    @property
    def amount_base(self) -> float:
        return self.amount * self.fx_to_base

    @property
    def per_share(self) -> float | None:
        """Dividendo por acción, leído de la descripción de IBKR ("USD 0.25 PER SHARE")."""
        match = _PER_SHARE_RE.search(self.description or "")
        return float(match.group(2)) if match else None


@dataclass
class DividendAccrual:
    """Dividendo ya declarado (entre la fecha ex y la de pago)."""

    conid: str
    symbol: str
    currency: str
    ex_date: date | None
    pay_date: date | None
    quantity: float
    gross_rate: float
    gross_amount: float
    net_amount: float
    fx_to_base: float


@dataclass
class Statement:
    account_id: str
    report_date: date
    positions: list[Position] = field(default_factory=list)
    cash: list[CashBalance] = field(default_factory=list)
    transactions: list[CashTransaction] = field(default_factory=list)
    accruals: list[DividendAccrual] = field(default_factory=list)
    fx_to_base: dict[str, float] = field(default_factory=dict)
    ignored_cash: list[CashBalance] = field(default_factory=list)   # saldos sin tipo de cambio

    def missing_fx(self) -> list[str]:
        return sorted({c.currency for c in self.cash if c.ending_cash and c.currency not in self.fx_to_base})

    def fx(self, currency: str) -> float:
        try:
            return self.fx_to_base[currency]
        except KeyError:
            raise KeyError(
                f"No hay tipo de cambio {currency}→base en el Flex. "
                "Añade la sección 'Conversion Rates' a tu Flex Query o revisa la conexión con Yahoo."
            ) from None
