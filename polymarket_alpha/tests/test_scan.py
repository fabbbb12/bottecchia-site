import json
import tempfile
from pathlib import Path

from arbitrage.scan import scan_multi_outcome, scan_yes_no
from db import get_connection, init_db
from fees import FeeConfig

ZERO_FEE = FeeConfig(trading_fee_bps=0, gas_cost_usd=0.0, slippage_model="x", verified_against=None, verified_at=None)


def _make_db():
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    init_db(db_path)
    return tmp, get_connection(db_path)


def _insert_market(conn, market_id, event_id=None, mutually_exclusive=None, collectively_exhaustive=None):
    conn.execute(
        "INSERT INTO markets (market_id, event_id, mutually_exclusive, collectively_exhaustive) VALUES (?, ?, ?, ?)",
        (market_id, event_id, mutually_exclusive, collectively_exhaustive),
    )


def _insert_token(conn, token_id, market_id, outcome, outcome_index):
    conn.execute(
        "INSERT INTO tokens (token_id, market_id, outcome, outcome_index) VALUES (?, ?, ?, ?)",
        (token_id, market_id, outcome, outcome_index),
    )


def _insert_book(conn, token_id, timestamp, asks):
    conn.execute(
        "INSERT INTO orderbook_snapshots (timestamp, token_id, book_data) VALUES (?, ?, ?)",
        (timestamp, token_id, json.dumps({"bids": [], "asks": asks})),
    )


def test_scan_yes_no_logs_opportunity_for_binary_market():
    tmp, conn = _make_db()
    try:
        _insert_market(conn, "MKT1")
        _insert_token(conn, "tok_yes", "MKT1", "Yes", 0)
        _insert_token(conn, "tok_no", "MKT1", "No", 1)
        _insert_book(conn, "tok_yes", 1_700_000_000, [[0.45, 100.0]])
        _insert_book(conn, "tok_no", 1_700_000_100, [[0.50, 100.0]])
        conn.commit()

        logged = scan_yes_no(conn, ZERO_FEE)
        assert logged == 1

        opp = conn.execute("SELECT * FROM opportunities WHERE strategy_type = 'yes_no'").fetchone()
        assert opp["market_id"] == "MKT1"
        assert round(opp["gross_edge"], 6) == 0.05
        assert opp["capital_executable"] == 100.0
    finally:
        conn.close()
        tmp.cleanup()


def test_scan_yes_no_skips_market_without_two_tokens():
    tmp, conn = _make_db()
    try:
        _insert_market(conn, "MKT1")
        _insert_token(conn, "tok_yes", "MKT1", "Yes", 0)  # só 1 token
        conn.commit()
        assert scan_yes_no(conn, ZERO_FEE) == 0
    finally:
        conn.close()
        tmp.cleanup()


def test_scan_yes_no_skips_market_missing_orderbook():
    tmp, conn = _make_db()
    try:
        _insert_market(conn, "MKT1")
        _insert_token(conn, "tok_yes", "MKT1", "Yes", 0)
        _insert_token(conn, "tok_no", "MKT1", "No", 1)
        conn.commit()  # nenhum book coletado ainda
        assert scan_yes_no(conn, ZERO_FEE) == 0
    finally:
        conn.close()
        tmp.cleanup()


def test_scan_multi_outcome_requires_confirmed_structure():
    tmp, conn = _make_db()
    try:
        for i in range(3):
            _insert_market(conn, f"MKT{i}", event_id="EVT1")  # mutually_exclusive/exhaustive não setados
            _insert_token(conn, f"tok{i}", f"MKT{i}", "Yes", 0)
            _insert_book(conn, f"tok{i}", 1_700_000_000, [[0.2, 100.0]])
        conn.commit()

        logged = scan_multi_outcome(conn, ZERO_FEE)
        assert logged == 1
        opp = conn.execute("SELECT * FROM opportunities WHERE strategy_type = 'multi_outcome'").fetchone()
        assert opp["capital_executable"] == 0.0  # estrutura não confirmada -> não executa
    finally:
        conn.close()
        tmp.cleanup()


def test_scan_multi_outcome_executes_when_structure_confirmed():
    tmp, conn = _make_db()
    try:
        for i in range(3):
            _insert_market(conn, f"MKT{i}", event_id="EVT1", mutually_exclusive=1, collectively_exhaustive=1)
            _insert_token(conn, f"tok{i}", f"MKT{i}", "Yes", 0)
            _insert_book(conn, f"tok{i}", 1_700_000_000, [[0.2, 100.0]])
        conn.commit()

        logged = scan_multi_outcome(conn, ZERO_FEE)
        assert logged == 1
        opp = conn.execute("SELECT * FROM opportunities WHERE strategy_type = 'multi_outcome'").fetchone()
        assert opp["capital_executable"] == 100.0
        assert round(opp["gross_edge"], 6) == 0.4  # 1 - 0.6
    finally:
        conn.close()
        tmp.cleanup()


def test_scan_marks_is_oos_correctly():
    tmp, conn = _make_db()
    try:
        _insert_market(conn, "MKT1")
        _insert_token(conn, "tok_yes", "MKT1", "Yes", 0)
        _insert_token(conn, "tok_no", "MKT1", "No", 1)
        _insert_book(conn, "tok_yes", 2_000_000_000, [[0.45, 100.0]])
        _insert_book(conn, "tok_no", 2_000_000_000, [[0.50, 100.0]])
        conn.commit()

        scan_yes_no(conn, ZERO_FEE, oos_start=1_900_000_000)
        opp = conn.execute("SELECT * FROM opportunities").fetchone()
        assert opp["is_oos"] == 1
    finally:
        conn.close()
        tmp.cleanup()
