"""Coleta de snapshots de order book — grava em `orderbook_snapshots`."""

import logging
import sqlite3
import time

from collectors.client import PolymarketClient
from normalization.normalize import normalize_order_book

logger = logging.getLogger("polymarket_alpha.collectors.orderbook")


def collect_order_book_snapshot(conn: sqlite3.Connection, client: PolymarketClient, token_id: str) -> dict | None:
    """Busca o book atual de um token e grava um snapshot com o
    timestamp de agora (UTC)."""
    try:
        raw_book = client.get_order_book(token_id)
    except Exception:
        logger.exception("Falha ao buscar order book para token %s", token_id)
        return None

    timestamp = int(time.time())
    snapshot = normalize_order_book(raw_book, token_id, timestamp)
    conn.execute(
        """INSERT INTO orderbook_snapshots
           (timestamp, token_id, best_bid, best_ask, bid_depth, ask_depth, book_data)
           VALUES (:timestamp, :token_id, :best_bid, :best_ask, :bid_depth, :ask_depth, :book_data)""",
        snapshot,
    )
    conn.commit()
    return snapshot


def collect_order_books_for_tokens(conn: sqlite3.Connection, client: PolymarketClient, token_ids: list[str]) -> int:
    count = 0
    for token_id in token_ids:
        if collect_order_book_snapshot(conn, client, token_id) is not None:
            count += 1
    return count
