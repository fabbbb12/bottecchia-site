"""Normaliza respostas brutas da API em linhas prontas para o banco.

Separado dos coletores de propósito: esta camada não faz nenhuma
chamada de rede, então é 100% testável com dados de exemplo (fixtures),
mesmo sem acesso à API real. Os nomes de campo assumidos abaixo (`id`,
`conditionId`, `clobTokenIds`, `outcomes`, etc.) seguem o formato mais
comum documentado publicamente para a Gamma API da Polymarket, mas NÃO
foram confirmados contra uma resposta real nesta sessão — depois da
primeira coleta bem-sucedida, compare um payload real com o mapeamento
abaixo e ajuste se necessário.
"""

import json


def normalize_market(raw: dict) -> dict:
    """Mercado (Gamma API) -> linha da tabela `markets`."""
    return {
        "market_id": str(raw.get("conditionId") or raw.get("id") or ""),
        "event_id": str(raw.get("eventId") or raw.get("event_id") or "") or None,
        "question": raw.get("question"),
        "slug": raw.get("slug"),
        "status": "closed" if raw.get("closed") else ("active" if raw.get("active") else "unknown"),
        "neg_risk": 1 if raw.get("negRisk") else 0,
        "mutually_exclusive": None,       # nunca inferido -- preencher manualmente (Seção 7)
        "collectively_exhaustive": None,
        "classification_notes": "",
        "start_time": _parse_timestamp(raw.get("startDate")),
        "end_time": _parse_timestamp(raw.get("endDate")),
        "resolution_time": _parse_timestamp(raw.get("resolutionDate")),
        "category": raw.get("category"),
        "created_at": _parse_timestamp(raw.get("createdAt")),
        "updated_at": _parse_timestamp(raw.get("updatedAt")),
    }


def normalize_tokens(raw_market: dict) -> list[dict]:
    """Extrai os tokens (outcomes) de um mercado -> linhas da tabela
    `tokens`. Assume `clobTokenIds` e `outcomes` como listas paralelas
    serializadas em JSON (formato comum na Gamma API)."""
    market_id = str(raw_market.get("conditionId") or raw_market.get("id") or "")
    token_ids = _parse_json_list(raw_market.get("clobTokenIds"))
    outcomes = _parse_json_list(raw_market.get("outcomes"))

    tokens = []
    for i, token_id in enumerate(token_ids):
        outcome = outcomes[i] if i < len(outcomes) else None
        tokens.append(
            {"token_id": str(token_id), "market_id": market_id, "outcome": outcome, "outcome_index": i}
        )
    return tokens


def normalize_order_book(raw: dict, token_id: str, timestamp: int) -> dict:
    """Order book (CLOB API) -> linha da tabela `orderbook_snapshots`.
    Assume `bids`/`asks` como listas de {"price": ..., "size": ...}."""
    bids = [(float(b["price"]), float(b["size"])) for b in raw.get("bids", [])]
    asks = [(float(a["price"]), float(a["size"])) for a in raw.get("asks", [])]
    bids.sort(key=lambda x: -x[0])  # melhor bid primeiro (maior preço)
    asks.sort(key=lambda x: x[0])   # melhor ask primeiro (menor preço)

    return {
        "timestamp": timestamp,
        "token_id": token_id,
        "best_bid": bids[0][0] if bids else None,
        "best_ask": asks[0][0] if asks else None,
        "bid_depth": sum(size for _, size in bids),
        "ask_depth": sum(size for _, size in asks),
        "book_data": json.dumps({"bids": bids, "asks": asks}),
    }


def normalize_trade(raw: dict, token_id: str) -> dict:
    """Trade (CLOB API) -> linha da tabela `trades`."""
    return {
        "timestamp": _parse_timestamp(raw.get("timestamp") or raw.get("match_time")),
        "token_id": token_id,
        "price": float(raw["price"]) if raw.get("price") is not None else None,
        "size": float(raw["size"]) if raw.get("size") is not None else None,
        "side": raw.get("side"),
    }


def normalize_price_point(raw: dict, token_id: str, source: str = "clob_prices_history") -> dict:
    """Ponto de preço histórico (CLOB API) -> linha da tabela `price_history`."""
    return {
        "timestamp": _parse_timestamp(raw.get("t") or raw.get("timestamp")),
        "token_id": token_id,
        "price": float(raw["p"]) if raw.get("p") is not None else float(raw.get("price", "nan")),
        "source": source,
    }


def _parse_json_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def _parse_timestamp(value) -> int | None:
    """Aceita epoch (int/str numérica) ou ISO 8601 -> epoch UTC em segundos."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except ValueError:
            return None
    return None
