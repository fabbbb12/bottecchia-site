"""Coleta de trades executados — grava em `trades`."""

import logging
import sqlite3

from collectors.client import PolymarketClient
from normalization.normalize import normalize_trade

logger = logging.getLogger("polymarket_alpha.collectors.trades")


def collect_trades(conn: sqlite3.Connection, client: PolymarketClient, token_id: str, limit: int = 100) -> int:
    try:
        raw_trades = client.get_trades(token_id, limit=limit)
    except Exception:
        logger.exception("Falha ao buscar trades para token %s", token_id)
        return 0

    count = 0
    for raw_trade in raw_trades:
        trade = normalize_trade(raw_trade, token_id)
        if trade["timestamp"] is None:
            continue
        conn.execute(
            "INSERT INTO trades (timestamp, token_id, price, size, side) VALUES (:timestamp, :token_id, :price, :size, :side)",
            trade,
        )
        count += 1
    conn.commit()
    return count
