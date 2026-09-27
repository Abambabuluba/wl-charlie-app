"""Conexión opcional a IB Gateway con ib_async, blindada en solo lectura.

Tres barreras: el Gateway con "Read-Only API" activado, la conexión con readonly=True y esta
clase, que solo deja pasar una lista cerrada de métodos de consulta.
"""

from __future__ import annotations

from divmon.analytics.margin import LiveMargin

# Únicos métodos de ib_async que este proyecto puede usar.
ALLOWED_METHODS = frozenset({
    "isConnected",
    "disconnect",
    "managedAccounts",
    "accountSummary",
    "accountValues",
    "portfolio",
    "positions",
})


class ReadOnlyViolation(PermissionError):
    pass


class ReadOnlyIB:
    def __init__(self, host: str, port: int, client_id: int, timeout: float = 15):
        from ib_async import IB   # dependencia opcional: pip install -e ".[gateway]"

        self._ib = IB()
        self._ib.connect(host, port, clientId=client_id, timeout=timeout, readonly=True)

    def __getattr__(self, name: str):
        if name not in ALLOWED_METHODS:
            raise ReadOnlyViolation(f"'{name}' no está permitido: esta herramienta es de solo lectura")
        return getattr(self._ib, name)

    def __enter__(self) -> "ReadOnlyIB":
        return self

    def __exit__(self, *exc) -> None:
        self.disconnect()


def fetch_live_margin(host: str, port: int, client_id: int, base_currency: str) -> LiveMargin:
    with ReadOnlyIB(host, port, client_id) as ib:
        values = {
            v.tag: float(v.value)
            for v in ib.accountSummary()
            if v.currency in (base_currency, "") and v.value not in ("", None)
        }
    try:
        return LiveMargin(
            net_liquidation=values["NetLiquidation"],
            maintenance_margin=values["MaintMarginReq"],
            excess_liquidity=values["ExcessLiquidity"],
            gross_position_value=values["GrossPositionValue"],
        )
    except KeyError as missing:
        raise RuntimeError(f"IB Gateway no devolvió {missing} en {base_currency}") from None
