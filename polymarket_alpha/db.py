"""Camada de banco de dados (SQLite) — Seção 4 da spec.

Nenhuma dependência de banco externo; o dataset inteiro vive em um único
arquivo .db, reproduzível. Todos os timestamps são armazenados como
inteiros de época UTC (segundos), nunca com timezone implícita local.
"""

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "database" / "polymarket_alpha.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    market_id TEXT PRIMARY KEY,
    event_id TEXT,
    question TEXT,
    slug TEXT,
    status TEXT,
    neg_risk INTEGER,              -- 1 se é mercado negRisk (Seção 7), 0/NULL caso contrário
    mutually_exclusive INTEGER,    -- 1/0/NULL — classificação explícita, nunca inferida por NLP
    collectively_exhaustive INTEGER,
    classification_notes TEXT,     -- justificativa registrada da classificação (Seção 7)
    start_time INTEGER,            -- epoch UTC
    end_time INTEGER,
    resolution_time INTEGER,
    category TEXT,
    created_at INTEGER,
    updated_at INTEGER
);

CREATE TABLE IF NOT EXISTS tokens (
    token_id TEXT PRIMARY KEY,
    market_id TEXT NOT NULL,
    outcome TEXT,
    outcome_index INTEGER,
    FOREIGN KEY (market_id) REFERENCES markets(market_id)
);
CREATE INDEX IF NOT EXISTS idx_tokens_market ON tokens(market_id);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,    -- epoch UTC
    token_id TEXT NOT NULL,
    price REAL,
    source TEXT,
    FOREIGN KEY (token_id) REFERENCES tokens(token_id)
);
CREATE INDEX IF NOT EXISTS idx_price_history_token_ts ON price_history(token_id, timestamp);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    token_id TEXT NOT NULL,
    best_bid REAL,
    best_ask REAL,
    bid_depth REAL,
    ask_depth REAL,
    book_data TEXT,                 -- JSON serializado: {"bids": [[price, size], ...], "asks": [...]}
    FOREIGN KEY (token_id) REFERENCES tokens(token_id)
);
CREATE INDEX IF NOT EXISTS idx_orderbook_token_ts ON orderbook_snapshots(token_id, timestamp);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    token_id TEXT NOT NULL,
    price REAL,
    size REAL,
    side TEXT,                      -- 'buy' / 'sell'
    FOREIGN KEY (token_id) REFERENCES tokens(token_id)
);
CREATE INDEX IF NOT EXISTS idx_trades_token_ts ON trades(token_id, timestamp);

CREATE TABLE IF NOT EXISTS resolutions (
    market_id TEXT PRIMARY KEY,
    resolved_outcome TEXT,
    resolution_timestamp INTEGER,
    FOREIGN KEY (market_id) REFERENCES markets(market_id)
);

-- Seção 9: registrar TODAS as oportunidades candidatas, lucrativas ou não,
-- para evitar survivorship bias.
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_detected INTEGER NOT NULL,
    market_id TEXT NOT NULL,
    strategy_type TEXT NOT NULL,    -- 'yes_no' | 'multi_outcome' | 'relationship'
    tokens TEXT,                    -- JSON: lista de token_ids envolvidos
    prices TEXT,                    -- JSON: preços usados no cálculo
    best_bid TEXT,                  -- JSON por token, quando relevante
    best_ask TEXT,
    available_depth TEXT,           -- JSON
    gross_edge REAL,
    fees REAL,
    slippage REAL,
    net_edge REAL,
    capital_required REAL,
    capital_executable REAL,
    duration INTEGER,               -- segundos até resolução/convergência, preenchido depois
    resolution TEXT,                -- preenchido depois de resolvido
    realized_pnl REAL,              -- preenchido depois de resolvido
    is_oos INTEGER                  -- 1 se está no período out-of-sample (Seção 16)
);
CREATE INDEX IF NOT EXISTS idx_opportunities_market ON opportunities(market_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_strategy ON opportunities(strategy_type);
CREATE INDEX IF NOT EXISTS idx_opportunities_ts ON opportunities(timestamp_detected);
"""


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
