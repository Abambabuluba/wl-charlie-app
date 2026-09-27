"""Uso de margen, intereses y distancia al margin call."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from divmon.config import Config
from divmon.models import INTEREST_PAID_TYPE, INTEREST_RECEIVED_TYPE, CashTransaction, Statement


@dataclass
class LiveMargin:
    """Datos exactos de IB Gateway (opcional). Sustituyen a la estimación."""

    net_liquidation: float
    maintenance_margin: float
    excess_liquidity: float
    gross_position_value: float


@dataclass
class MarginStatus:
    net_liquidation: float
    gross_position_value: float
    loan: float
    loan_by_currency: dict[str, float]
    maintenance_margin: float
    margin_source: str                      # "estimado" o "IB Gateway"
    excess_liquidity: float
    estimated_annual_interest: float
    missing_rates: list[str] = field(default_factory=list)
    interest_last_month: float | None = None   # último cargo real de IBKR (en base)

    @property
    def cushion(self) -> float | None:
        return self.excess_liquidity / self.net_liquidation if self.net_liquidation > 0 else None

    @property
    def loan_to_value(self) -> float:
        return self.loan / self.gross_position_value if self.gross_position_value else 0.0

    @property
    def leverage(self) -> float | None:
        return self.gross_position_value / self.net_liquidation if self.net_liquidation > 0 else None

    @property
    def drop_to_margin_call(self) -> float | None:
        """Caída uniforme de todas las posiciones que agotaría el exceso de liquidez.

        Si la cartera cae un d %, el exceso pasa a ser EL - d·(GPV - MM): el valor baja d·GPV
        y el margen exigido baja d·MM. Despejando EL - d·(GPV - MM) = 0 sale d = EL / (GPV - MM).
        """
        if self.loan <= 0:
            return None
        exposed = self.gross_position_value - self.maintenance_margin
        if exposed <= 0:
            return 0.0
        return max(0.0, min(1.0, self.excess_liquidity / exposed))

    @property
    def blended_rate(self) -> float | None:
        return self.estimated_annual_interest / self.loan if self.loan else None


def last_month_interest(transactions: list[CashTransaction], report_date) -> float | None:
    """Intereses netos del último mes con cargo (IBKR los liquida a principios de mes)."""
    window = [
        t for t in transactions
        if t.type in (INTEREST_PAID_TYPE, INTEREST_RECEIVED_TYPE)
        and report_date - timedelta(days=45) <= t.date <= report_date
    ]
    if not window:
        return None
    last = max(t.date for t in window)
    month = [t for t in window if (t.date.year, t.date.month) == (last.year, last.month)]
    return -sum(t.amount_base for t in month)


def compute_margin(
    stmt: Statement,
    cfg: Config,
    transactions: list[CashTransaction] | None = None,
    live: LiveMargin | None = None,
) -> MarginStatus:
    gross = sum(abs(p.value_base) for p in stmt.positions)
    cash_base = sum(c.ending_cash * stmt.fx(c.currency) for c in stmt.cash if c.ending_cash)
    loan_by_currency = {
        c.currency: -c.ending_cash * stmt.fx(c.currency) for c in stmt.cash if c.ending_cash < 0
    }
    loan = sum(loan_by_currency.values())

    interest, missing = 0.0, []
    for currency, amount in loan_by_currency.items():
        rate = cfg.margin.interest_rates.get(currency)
        if rate is None:
            missing.append(currency)
        else:
            interest += amount * rate

    if live:
        nlv, mm, el, gross = live.net_liquidation, live.maintenance_margin, live.excess_liquidity, live.gross_position_value
        source = "IB Gateway"
    else:
        nlv = gross + cash_base
        mm = sum(
            abs(p.value_base) * (cfg.override(p.symbol).maintenance_rate or cfg.margin.maintenance_rate_default)
            for p in stmt.positions
        )
        el = nlv - mm
        source = "estimado"

    return MarginStatus(
        net_liquidation=nlv,
        gross_position_value=gross,
        loan=loan,
        loan_by_currency=loan_by_currency,
        maintenance_margin=mm,
        margin_source=source,
        excess_liquidity=el,
        estimated_annual_interest=interest,
        missing_rates=missing,
        interest_last_month=last_month_interest(transactions or stmt.transactions, stmt.report_date),
    )
