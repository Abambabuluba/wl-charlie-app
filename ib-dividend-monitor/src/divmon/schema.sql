CREATE TABLE IF NOT EXISTS account_snapshots (
    date TEXT PRIMARY KEY,
    net_liquidation REAL NOT NULL,
    gross_position_value REAL NOT NULL,
    loan REAL NOT NULL,
    maintenance_margin REAL,
    margin_source TEXT,
    excess_liquidity REAL,
    annual_dividends_net REAL
);

CREATE TABLE IF NOT EXISTS position_snapshots (
    date TEXT NOT NULL,
    conid TEXT NOT NULL,
    symbol TEXT NOT NULL,
    currency TEXT NOT NULL,
    quantity REAL NOT NULL,
    mark_price REAL,
    value_base REAL NOT NULL,
    cost_base REAL NOT NULL,
    PRIMARY KEY (date, conid)
);

-- Dividendos, retenciones e intereses tal como los liquida IBKR.
CREATE TABLE IF NOT EXISTS cash_transactions (
    transaction_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    symbol TEXT,
    currency TEXT NOT NULL,
    amount REAL NOT NULL,
    amount_base REAL NOT NULL,
    per_share REAL,
    description TEXT
);
CREATE INDEX IF NOT EXISTS ix_cash_tx_type_date ON cash_transactions(type, date);

CREATE TABLE IF NOT EXISTS fundamentals (
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    per REAL,
    dividend_yield REAL,
    payout REAL,
    debt_ebitda REAL,
    sector TEXT,
    country TEXT,
    price REAL,
    currency TEXT,
    source TEXT,
    PRIMARY KEY (date, symbol)
);

CREATE TABLE IF NOT EXISTS radar_state (
    symbol TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    key TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    delivered INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_alerts_key_ts ON alerts_log(key, ts);
