import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from collectors.markets import collect_markets
from collectors.orderbook import collect_order_book_snapshot
from collectors.prices import collect_price_history
from collectors.trades import collect_trades
from db import get_connection, init_db


def _make_db():
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    init_db(db_path)
    return tmp, get_connection(db_path)


def _make_db_with_token(token_id="tok_yes", market_id="0xabc"):
    tmp, conn = _make_db()
    conn.execute("INSERT INTO markets (market_id) VALUES (?)", (market_id,))
    conn.execute("INSERT INTO tokens (token_id, market_id) VALUES (?, ?)", (token_id, market_id))
    conn.commit()
    return tmp, conn


def test_collect_markets_writes_markets_and_tokens():
    tmp, conn = _make_db()
    try:
        client = MagicMock()
        client.get_markets.side_effect = [
            [
                {
                    "conditionId": "0xabc",
                    "question": "Will X happen?",
                    "active": True,
                    "closed": False,
                    "clobTokenIds": json.dumps(["tok_yes", "tok_no"]),
                    "outcomes": json.dumps(["Yes", "No"]),
                }
            ],
            [],  # segunda página vazia -> para o loop
        ]
        total = collect_markets(conn, client, page_size=100)
        assert total == 1
        market = conn.execute("SELECT * FROM markets WHERE market_id = ?", ("0xabc",)).fetchone()
        assert market["question"] == "Will X happen?"
        tokens = conn.execute("SELECT * FROM tokens WHERE market_id = ?", ("0xabc",)).fetchall()
        assert len(tokens) == 2
    finally:
        conn.close()
        tmp.cleanup()


def test_collect_markets_skips_market_without_id():
    tmp, conn = _make_db()
    try:
        client = MagicMock()
        client.get_markets.side_effect = [[{"question": "sem id"}], []]
        total = collect_markets(conn, client)
        assert total == 0
    finally:
        conn.close()
        tmp.cleanup()


def test_collect_order_book_snapshot_writes_row():
    tmp, conn = _make_db_with_token()
    try:
        client = MagicMock()
        client.get_order_book.return_value = {
            "bids": [{"price": "0.48", "size": "10"}],
            "asks": [{"price": "0.52", "size": "8"}],
        }
        snapshot = collect_order_book_snapshot(conn, client, token_id="tok_yes")
        assert snapshot["best_bid"] == 0.48
        assert snapshot["best_ask"] == 0.52
        row = conn.execute("SELECT * FROM orderbook_snapshots WHERE token_id = ?", ("tok_yes",)).fetchone()
        assert row is not None
    finally:
        conn.close()
        tmp.cleanup()


def test_collect_order_book_snapshot_handles_client_error_gracefully():
    tmp, conn = _make_db_with_token()
    try:
        client = MagicMock()
        client.get_order_book.side_effect = RuntimeError("network down")
        result = collect_order_book_snapshot(conn, client, token_id="tok_yes")
        assert result is None
    finally:
        conn.close()
        tmp.cleanup()


def test_collect_price_history_writes_points():
    tmp, conn = _make_db_with_token()
    try:
        client = MagicMock()
        client.get_price_history.return_value = [{"t": 1_700_000_000, "p": "0.42"}, {"t": 1_700_003_600, "p": "0.45"}]
        count = collect_price_history(conn, client, "tok_yes", 1_700_000_000, 1_700_003_600)
        assert count == 2
        rows = conn.execute("SELECT * FROM price_history WHERE token_id = ?", ("tok_yes",)).fetchall()
        assert len(rows) == 2
    finally:
        conn.close()
        tmp.cleanup()


def test_collect_trades_writes_rows():
    tmp, conn = _make_db_with_token()
    try:
        client = MagicMock()
        client.get_trades.return_value = [{"timestamp": 1_700_000_000, "price": "0.5", "size": "10", "side": "buy"}]
        count = collect_trades(conn, client, "tok_yes")
        assert count == 1
        row = conn.execute("SELECT * FROM trades WHERE token_id = ?", ("tok_yes",)).fetchone()
        assert row["side"] == "buy"
    finally:
        conn.close()
        tmp.cleanup()
