"""Varre o banco coletado em busca de oportunidades candidatas e grava
TODAS elas (lucrativas ou não) na tabela `opportunities` — Seção 9.

Nota de design: os coletores (collectors/*.py) já gravam dados
normalizados diretamente nas tabelas finais (Seção da normalização vira
parte do próprio `collect`, em vez de uma etapa JSON bruto -> banco
separada) — mais simples e igualmente auditável, já que a normalização
é determinística e testada isoladamente em tests/test_normalize.py.
"""

import json
import sqlite3

from arbitrage.multi_outcome import MarketStructure, evaluate_multi_outcome_opportunity
from arbitrage.yes_no import evaluate_yes_no_opportunity
from execution import Level
from fees import FeeConfig


def _latest_book(conn: sqlite3.Connection, token_id: str) -> tuple[int, list[Level]] | None:
    """Devolve (timestamp, ask_levels) do snapshot de book mais recente
    de um token, ou None se não há nenhum snapshot."""
    row = conn.execute(
        "SELECT timestamp, book_data FROM orderbook_snapshots WHERE token_id = ? "
        "ORDER BY timestamp DESC LIMIT 1",
        (token_id,),
    ).fetchone()
    if row is None:
        return None
    book = json.loads(row["book_data"])
    ask_levels = [(price, size) for price, size in book.get("asks", [])]
    return row["timestamp"], ask_levels


def _is_oos(timestamp: int, oos_start: int | None, oos_end: int | None) -> bool:
    if oos_start is None:
        return False
    if oos_end is not None:
        return oos_start <= timestamp <= oos_end
    return timestamp >= oos_start


def _log_opportunity(conn: sqlite3.Connection, opp, strategy_type: str, timestamp: int, is_oos: bool, tokens: list[str]) -> None:
    conn.execute(
        """INSERT INTO opportunities
           (timestamp_detected, market_id, strategy_type, tokens, gross_edge, net_edge, fees,
            capital_executable, capital_required, is_oos)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            timestamp,
            opp.market_id,
            strategy_type,
            json.dumps(tokens),
            opp.gross_edge,
            getattr(opp, "net_edge", None),
            getattr(opp, "fees", None),
            opp.capital_executable,
            getattr(opp, "capital_required", None),
            1 if is_oos else 0,
        ),
    )


def scan_yes_no(
    conn: sqlite3.Connection, fee_config: FeeConfig, oos_start: int | None = None, oos_end: int | None = None
) -> int:
    """Para cada mercado com exatamente 2 tokens (YES/NO), avalia a
    oportunidade usando o snapshot de book mais recente de cada lado."""
    markets = conn.execute(
        "SELECT m.market_id FROM markets m "
        "JOIN tokens t ON t.market_id = m.market_id "
        "GROUP BY m.market_id HAVING COUNT(*) = 2"
    ).fetchall()

    logged = 0
    for market in markets:
        market_id = market["market_id"]
        tokens = conn.execute(
            "SELECT token_id, outcome, outcome_index FROM tokens WHERE market_id = ? ORDER BY outcome_index",
            (market_id,),
        ).fetchall()
        yes_token, no_token = tokens[0], tokens[1]

        yes_book = _latest_book(conn, yes_token["token_id"])
        no_book = _latest_book(conn, no_token["token_id"])
        if yes_book is None or no_book is None:
            continue

        ts_yes, yes_levels = yes_book
        ts_no, no_levels = no_book
        timestamp = max(ts_yes, ts_no)  # momento em que os dois lados já estavam disponíveis

        opp = evaluate_yes_no_opportunity(market_id, timestamp, yes_levels, no_levels, fee_config)
        is_oos = _is_oos(timestamp, oos_start, oos_end)
        _log_opportunity(conn, opp, "yes_no", timestamp, is_oos, [yes_token["token_id"], no_token["token_id"]])
        logged += 1

    conn.commit()
    return logged


def scan_multi_outcome(
    conn: sqlite3.Connection, fee_config: FeeConfig, oos_start: int | None = None, oos_end: int | None = None
) -> int:
    """Agrupa mercados pelo mesmo `event_id` e testa SUM(ASK) < 1 sobre o
    token índice 0 ("Yes"/vencedor) de cada mercado do grupo — só quando
    a estrutura (mutuamente exclusivo + exaustivo) já foi confirmada
    manualmente (Seção 7); nunca inferida aqui."""
    events = conn.execute(
        "SELECT event_id FROM markets WHERE event_id IS NOT NULL AND event_id != '' GROUP BY event_id HAVING COUNT(*) > 1"
    ).fetchall()

    logged = 0
    for event in events:
        event_id = event["event_id"]
        markets = conn.execute(
            "SELECT market_id, mutually_exclusive, collectively_exhaustive, classification_notes "
            "FROM markets WHERE event_id = ?",
            (event_id,),
        ).fetchall()

        structure = MarketStructure(
            mutually_exclusive=_to_bool(markets[0]["mutually_exclusive"]),
            collectively_exhaustive=_to_bool(markets[0]["collectively_exhaustive"]),
            neg_risk=None,
            classification_notes=markets[0]["classification_notes"] or "",
        )

        outcome_levels = []
        timestamps = []
        skip_event = False
        for market in markets:
            first_token = conn.execute(
                "SELECT token_id FROM tokens WHERE market_id = ? ORDER BY outcome_index LIMIT 1",
                (market["market_id"],),
            ).fetchone()
            if first_token is None:
                skip_event = True
                break
            book = _latest_book(conn, first_token["token_id"])
            if book is None:
                skip_event = True
                break
            ts, levels = book
            timestamps.append(ts)
            outcome_levels.append(levels)

        if skip_event or not outcome_levels:
            continue

        timestamp = max(timestamps)
        opp = evaluate_multi_outcome_opportunity(event_id, timestamp, outcome_levels, structure, fee_config)
        is_oos = _is_oos(timestamp, oos_start, oos_end)
        _log_opportunity(conn, opp, "multi_outcome", timestamp, is_oos, [m["market_id"] for m in markets])
        logged += 1

    conn.commit()
    return logged


def _to_bool(value) -> bool | None:
    if value is None:
        return None
    return bool(value)
