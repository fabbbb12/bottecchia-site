"""Coleta de histórico de preços — grava em `price_history`."""

import logging
import sqlite3

from collectors.client import PolymarketClient
from normalization.normalize import normalize_price_point

logger = logging.getLogger("polymarket_alpha.collectors.prices")


def collect_price_history(
    conn: sqlite3.Connection, client: PolymarketClient, token_id: str, start_ts: int, end_ts: int, fidelity: int = 60
) -> int:
    try:
        raw_points = client.get_price_history(token_id, start_ts, end_ts, fidelity)
    except Exception:
        logger.exception("Falha ao buscar histórico de preço para token %s", token_id)
        return 0

    count = 0
    for raw_point in raw_points:
        point = normalize_price_point(raw_point, token_id)
        if point["timestamp"] is None:
            continue
        conn.execute(
            "INSERT INTO price_history (timestamp, token_id, price, source) VALUES (:timestamp, :token_id, :price, :source)",
            point,
        )
        count += 1
    conn.commit()
    return count
