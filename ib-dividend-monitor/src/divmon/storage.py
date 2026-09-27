"""Histórico en SQLite."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from importlib import resources
from pathlib import Path

from divmon.models import CashTransaction, Statement
from divmon.sources.fundamentals import Fundamentals


class Store:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(resources.files("divmon").joinpath("schema.sql").read_text(encoding="utf-8"))

    def close(self) -> None:
        self.conn.close()

    # --- Escritura ----------------------------------------------------------------

    def save_statement(self, stmt: Statement) -> int:
        """Guarda posiciones y movimientos de caja. Devuelve cuántos movimientos son nuevos."""
        day = stmt.report_date.isoformat()
        with self.conn:
            self.conn.execute("DELETE FROM position_snapshots WHERE date = ?", (day,))
            self.conn.executemany(
                "INSERT INTO position_snapshots VALUES (?,?,?,?,?,?,?,?)",
                [
                    (day, p.conid, p.symbol, p.currency, p.quantity, p.mark_price, p.value_base, p.cost_base)
                    for p in stmt.positions
                ],
            )
        return self.save_transactions(stmt.transactions)

    def save_transactions(self, transactions: list[CashTransaction]) -> int:
        """Añade movimientos de caja nuevos (los ya guardados se ignoran). Devuelve cuántos son nuevos."""
        with self.conn:
            before = self.conn.total_changes
            self.conn.executemany(
                "INSERT OR IGNORE INTO cash_transactions VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (t.transaction_id, t.date.isoformat(), t.type, t.symbol, t.currency, t.amount,
                     t.amount_base, t.per_share, t.description)
                    for t in transactions
                ],
            )
            return self.conn.total_changes - before

    def save_account_snapshot(self, day: date, **values) -> None:
        cols = ["date", *values]
        with self.conn:
            self.conn.execute(
                f"INSERT OR REPLACE INTO account_snapshots ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [day.isoformat(), *values.values()],
            )

    def save_fundamentals(self, day: date, items: list[Fundamentals]) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO fundamentals VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (day.isoformat(), f.symbol, f.per, f.dividend_yield, f.payout, f.debt_ebitda,
                     f.sector, f.country, f.price, f.currency, f.source)
                    for f in items
                ],
            )

    # --- Lectura ------------------------------------------------------------------

    def cash_transactions(self, since: date | None = None) -> list[CashTransaction]:
        rows = self.conn.execute(
            "SELECT * FROM cash_transactions WHERE date >= ? ORDER BY date",
            ((since or date.min).isoformat(),),
        ).fetchall()
        return [
            CashTransaction(
                transaction_id=r["transaction_id"],
                date=date.fromisoformat(r["date"]),
                type=r["type"],
                currency=r["currency"],
                amount=r["amount"],
                fx_to_base=(r["amount_base"] / r["amount"]) if r["amount"] else 1.0,
                symbol=r["symbol"],
                description=r["description"] or "",
            )
            for r in rows
        ]

    def latest_fundamentals(self, symbols: list[str], max_age_days: int, today: date) -> dict[str, Fundamentals]:
        """Últimos datos de cada símbolo que no superen la antigüedad indicada."""
        if not symbols:
            return {}
        cutoff = (today - timedelta(days=max_age_days)).isoformat()
        marks = ",".join("?" * len(symbols))
        rows = self.conn.execute(
            f"""SELECT f.* FROM fundamentals f
                JOIN (SELECT symbol, MAX(date) AS d FROM fundamentals
                      WHERE symbol IN ({marks}) AND date >= ? GROUP BY symbol) last
                ON f.symbol = last.symbol AND f.date = last.d""",
            [*symbols, cutoff],
        ).fetchall()
        return {r["symbol"]: Fundamentals.from_row(dict(r)) for r in rows}

    def account_history(self, since: date | None = None) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM account_snapshots WHERE date >= ? ORDER BY date",
            ((since or date.min).isoformat(),),
        ).fetchall()

    def radar_states(self) -> dict[str, str]:
        return {r["symbol"]: r["status"] for r in self.conn.execute("SELECT symbol, status FROM radar_state")}

    def set_radar_state(self, symbol: str, role: str, status: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO radar_state VALUES (?,?,?,?)",
                (symbol, role, status, datetime.now().isoformat(timespec="seconds")),
            )

    # --- Registro de alertas --------------------------------------------------------

    def last_alert_time(self, key: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT MAX(ts) AS ts FROM alerts_log WHERE key = ? AND delivered = 1", (key,)
        ).fetchone()
        return datetime.fromisoformat(row["ts"]) if row and row["ts"] else None

    def log_alert(self, key: str, severity: str, message: str, delivered: bool, ts: datetime | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO alerts_log (ts, key, severity, message, delivered) VALUES (?,?,?,?,?)",
                ((ts or datetime.now()).isoformat(timespec="seconds"), key, severity, message, int(delivered)),
            )

    def recent_alerts(self, since: datetime) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM alerts_log WHERE ts >= ? ORDER BY ts DESC", (since.isoformat(timespec="seconds"),)
        ).fetchall()

