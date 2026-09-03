"""Coleta de mercados e tokens — grava nas tabelas `markets` e `tokens`."""

import logging
import sqlite3

from collectors.client import PolymarketClient
from normalization.normalize import normalize_market, normalize_tokens

logger = logging.getLogger("polymarket_alpha.collectors.markets")


def collect_markets(conn: sqlite3.Connection, client: PolymarketClient, max_pages: int = 50, page_size: int = 100) -> int:
    """Pagina sobre `get_markets`, grava cada mercado e seus tokens.
    Devolve o número de mercados gravados."""
    total = 0
    for page in range(max_pages):
        raw_markets = client.get_markets(limit=page_size, offset=page * page_size)
        if not raw_markets:
            break

        for raw_market in raw_markets:
            market_row = normalize_market(raw_market)
            if not market_row["market_id"]:
                logger.warning("Mercado sem market_id, pulando: %r", raw_market)
                continue

            conn.execute(
                """INSERT INTO markets
                   (market_id, event_id, question, slug, status, neg_risk, mutually_exclusive,
                    collectively_exhaustive, classification_notes, start_time, end_time,
                    resolution_time, category, created_at, updated_at)
                   VALUES (:market_id, :event_id, :question, :slug, :status, :neg_risk,
                           :mutually_exclusive, :collectively_exhaustive, :classification_notes,
                           :start_time, :end_time, :resolution_time, :category, :created_at, :updated_at)
                   ON CONFLICT(market_id) DO UPDATE SET
                       status=excluded.status, updated_at=excluded.updated_at""",
                market_row,
            )

            for token_row in normalize_tokens(raw_market):
                conn.execute(
                    """INSERT OR IGNORE INTO tokens (token_id, market_id, outcome, outcome_index)
                       VALUES (:token_id, :market_id, :outcome, :outcome_index)""",
                    token_row,
                )
            total += 1

        conn.commit()
        if len(raw_markets) < page_size:
            break  # última página

    return total
