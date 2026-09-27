"""Plan de amortización del préstamo de margen con aportaciones y dividendos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MAX_MONTHS = 600


@dataclass
class Plan:
    label: str
    start_debt: float
    months: int | None              # None = no se amortiza nunca con estos supuestos
    total_interest: float
    balances: list[float]           # saldo al final de cada mes (índice 0 = hoy)

    def payoff_date(self, start: date) -> date | None:
        if self.months is None:
            return None
        y, m = divmod(start.month - 1 + self.months, 12)
        return date(start.year + y, m + 1, 1)


def simulate(
    debt: float,
    monthly_contribution: float,
    annual_rate: float,
    monthly_dividends: list[float] | None = None,
    dividend_growth: float = 0.0,
    label: str = "",
) -> Plan:
    """Mes a mes: se cargan intereses sobre el saldo y se resta aportación + dividendos netos.

    ``monthly_dividends`` es el perfil de 12 meses (neto) a partir del mes siguiente; se repite
    cada año aplicando ``dividend_growth``.
    """
    profile = monthly_dividends or [0.0] * 12
    balance, interest_total, balances = debt, 0.0, [debt]
    for month in range(1, MAX_MONTHS + 1):
        if balance <= 0:
            break
        interest = balance * annual_rate / 12
        growth = (1 + dividend_growth) ** ((month - 1) // 12)
        payment = monthly_contribution + profile[(month - 1) % 12] * growth
        interest_total += interest
        balance = balance + interest - payment
        balances.append(max(balance, 0.0))
        if month >= 24 and balances[-1] >= balances[-13]:
            # En un año entero el saldo no baja: la deuda crece más que lo que aportas.
            return Plan(label, debt, None, interest_total, balances)
    months = len(balances) - 1 if balance <= 0 else None
    return Plan(label, debt, months, interest_total, balances)


def standard_plans(
    debt: float,
    monthly_contribution: float,
    annual_rate: float,
    monthly_dividends: list[float],
    dividend_growth: float,
    dividends_to_debt: bool,
) -> list[Plan]:
    plans = [simulate(debt, monthly_contribution, annual_rate, label="Solo aportaciones")]
    if dividends_to_debt:
        plans.insert(
            0,
            simulate(debt, monthly_contribution, annual_rate, monthly_dividends, dividend_growth,
                     label="Aportaciones + dividendos netos"),
        )
    return plans
