import tempfile
from pathlib import Path

import pytest

from backtest.engine import LookaheadError, apply_resolution, resolve_all_pending, resolve_opportunity
from db import get_connection, init_db


def _make_db():
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    init_db(db_path)
    return tmp, get_connection(db_path)


def _insert_market(conn, market_id):
    conn.execute("INSERT OR IGNORE INTO markets (market_id) VALUES (?)", (market_id,))
    conn.commit()


def _insert_opportunity(conn, market_id, strategy_type, timestamp_detected, capital_executable=10.0, capital_required=9.5, fees=0.1):
    _insert_market(conn, market_id)
    cur = conn.execute(
        "INSERT INTO opportunities (timestamp_detected, market_id, strategy_type, capital_executable, "
        "capital_required, fees) VALUES (?, ?, ?, ?, ?, ?)",
        (timestamp_detected, market_id, strategy_type, capital_executable, capital_required, fees),
    )
    conn.commit()
    return cur.lastrowid


def test_resolve_opportunity_returns_none_when_market_still_open():
    tmp, conn = _make_db()
    try:
        opp_id = _insert_opportunity(conn, "MKT1", "yes_no", 1_000)
        assert resolve_opportunity(conn, opp_id) is None
    finally:
        conn.close()
        tmp.cleanup()


def test_structural_strategy_pnl_is_deterministic_regardless_of_outcome():
    tmp, conn = _make_db()
    try:
        opp_id = _insert_opportunity(conn, "MKT1", "yes_no", timestamp_detected=1_000, capital_executable=10.0, capital_required=9.5, fees=0.1)
        conn.execute(
            "INSERT INTO resolutions (market_id, resolved_outcome, resolution_timestamp) VALUES (?, ?, ?)",
            ("MKT1", "YES", 2_000),
        )
        conn.commit()
        result = resolve_opportunity(conn, opp_id)
        assert result["duration"] == 1_000
        assert result["resolution"] == "YES"
        # payout garantido = 10 * 1.0 = 10; custo = 9.5 + 0.1 fee -> lucro = 0.4
        assert round(result["realized_pnl"], 6) == 0.4
    finally:
        conn.close()
        tmp.cleanup()


def test_lookahead_error_when_resolution_precedes_detection():
    tmp, conn = _make_db()
    try:
        opp_id = _insert_opportunity(conn, "MKT1", "yes_no", timestamp_detected=5_000)
        conn.execute(
            "INSERT INTO resolutions (market_id, resolved_outcome, resolution_timestamp) VALUES (?, ?, ?)",
            ("MKT1", "YES", 1_000),  # resolução ANTES da detecção -- dado corrompido
        )
        conn.commit()
        with pytest.raises(LookaheadError):
            resolve_opportunity(conn, opp_id)
    finally:
        conn.close()
        tmp.cleanup()


def test_apply_resolution_writes_back_to_table():
    tmp, conn = _make_db()
    try:
        opp_id = _insert_opportunity(conn, "MKT1", "yes_no", timestamp_detected=1_000)
        conn.execute(
            "INSERT INTO resolutions (market_id, resolved_outcome, resolution_timestamp) VALUES (?, ?, ?)",
            ("MKT1", "NO", 2_000),
        )
        conn.commit()
        assert apply_resolution(conn, opp_id) is True
        row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,)).fetchone()
        assert row["resolution"] == "NO"
        assert row["realized_pnl"] is not None
    finally:
        conn.close()
        tmp.cleanup()


def test_resolve_all_pending_skips_unresolved_markets():
    tmp, conn = _make_db()
    try:
        _insert_opportunity(conn, "OPEN_MKT", "yes_no", timestamp_detected=1_000)
        resolved_id = _insert_opportunity(conn, "RESOLVED_MKT", "yes_no", timestamp_detected=1_000)
        conn.execute(
            "INSERT INTO resolutions (market_id, resolved_outcome, resolution_timestamp) VALUES (?, ?, ?)",
            ("RESOLVED_MKT", "YES", 2_000),
        )
        conn.commit()
        count = resolve_all_pending(conn)
        assert count == 1
        row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (resolved_id,)).fetchone()
        assert row["realized_pnl"] is not None
    finally:
        conn.close()
        tmp.cleanup()
