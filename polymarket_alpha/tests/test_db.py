import tempfile
from pathlib import Path

from db import get_connection, init_db


def test_init_db_creates_all_tables():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        try:
            tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        expected = {"markets", "tokens", "price_history", "orderbook_snapshots", "trades", "resolutions", "opportunities"}
        assert expected.issubset(tables)


def test_opportunities_table_accepts_insert_and_null_resolution_fields():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        try:
            conn.execute(
                "INSERT INTO opportunities (timestamp_detected, market_id, strategy_type, gross_edge, is_oos) "
                "VALUES (?, ?, ?, ?, ?)",
                (1_700_000_000, "MKT1", "yes_no", 0.05, 0),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM opportunities WHERE market_id = ?", ("MKT1",)).fetchone()
        finally:
            conn.close()
        assert row["gross_edge"] == 0.05
        assert row["realized_pnl"] is None  # ainda não resolvido
