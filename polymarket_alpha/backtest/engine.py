"""Backtest temporal e resolução — Seções 10 e 11.

Regra inegociável: a resolução de um mercado só pode ser usada DEPOIS do
timestamp em que a oportunidade foi detectada. Nunca embaralhar
timestamps, nunca usar resolução antes da hora, nunca usar preço
posterior para preencher uma ordem anterior.

Para YES+NO e multi-outcome (mutuamente exclusivo + exaustivo), o payout
é estruturalmente garantido em $1 por unidade na resolução,
independentemente de qual outcome vence — por isso o PnL realizado
dessas duas estratégias não depende de qual foi o resultado, só de
quando ele saiu (para calcular a duração/capital preso). Isso é
diferente de uma violação de relação (Seção 8), cujo PnL realizado
depende de qual outcome de fato resolveu — ver `RELATIONSHIP_PNL_NOTE`
abaixo para a suposição usada e sua limitação.
"""

import sqlite3

STRUCTURAL_STRATEGIES = {"yes_no", "multi_outcome"}

RELATIONSHIP_PNL_NOTE = (
    "PnL de violação de relação assume a operação clássica de hedge "
    "(comprar o lado mais barato, vender/hedgear o lado mais caro) e usa "
    "o valor de resolução (0 ou 1) de cada token. Essa é uma SUPOSIÇÃO DE "
    "MODELAGEM, não uma confirmação de que essa operação é executável na "
    "prática na Polymarket (shorting pode não estar disponível do jeito "
    "modelado aqui) — revisar antes de considerar o resultado confiável."
)


class LookaheadError(Exception):
    """Levantado quando uma resolução seria usada antes do timestamp de
    detecção da oportunidade — nunca deve acontecer num backtest correto."""


def resolve_opportunity(conn: sqlite3.Connection, opportunity_id: int) -> dict | None:
    """Tenta casar uma oportunidade já registrada com a resolução do
    mercado correspondente, respeitando a ordem temporal. Devolve um dict
    com duration/resolution/realized_pnl calculados, ou None se o mercado
    ainda não foi resolvido."""
    opp = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    if opp is None:
        raise ValueError(f"Oportunidade {opportunity_id} não encontrada")

    resolution = conn.execute(
        "SELECT * FROM resolutions WHERE market_id = ?", (opp["market_id"],)
    ).fetchone()
    if resolution is None:
        return None  # ainda não resolvido -- nada a fazer

    if resolution["resolution_timestamp"] is not None and resolution["resolution_timestamp"] < opp["timestamp_detected"]:
        raise LookaheadError(
            f"Resolução do mercado {opp['market_id']} ({resolution['resolution_timestamp']}) é anterior "
            f"ao timestamp de detecção da oportunidade {opportunity_id} ({opp['timestamp_detected']}) "
            "-- dado corrompido ou join errado, não pode ser usado."
        )

    duration = None
    if resolution["resolution_timestamp"] is not None:
        duration = resolution["resolution_timestamp"] - opp["timestamp_detected"]

    realized_pnl = None
    if opp["strategy_type"] in STRUCTURAL_STRATEGIES and opp["capital_executable"] and opp["capital_required"] is not None:
        # payout garantido de $1 por unidade, independente de qual outcome venceu
        realized_pnl = opp["capital_executable"] * 1.0 - opp["capital_required"] - (opp["fees"] or 0.0)

    return {
        "duration": duration,
        "resolution": resolution["resolved_outcome"],
        "realized_pnl": realized_pnl,
    }


def apply_resolution(conn: sqlite3.Connection, opportunity_id: int) -> bool:
    """Resolve e grava o resultado de volta na tabela `opportunities`.
    Devolve True se resolveu algo, False se o mercado ainda estava aberto."""
    result = resolve_opportunity(conn, opportunity_id)
    if result is None:
        return False
    conn.execute(
        "UPDATE opportunities SET duration = ?, resolution = ?, realized_pnl = ? WHERE id = ?",
        (result["duration"], result["resolution"], result["realized_pnl"], opportunity_id),
    )
    conn.commit()
    return True


def resolve_all_pending(conn: sqlite3.Connection) -> int:
    """Roda `apply_resolution` para toda oportunidade ainda sem resolução
    registrada. Devolve quantas foram resolvidas nesta chamada."""
    pending_ids = [
        row["id"] for row in conn.execute("SELECT id FROM opportunities WHERE realized_pnl IS NULL")
    ]
    resolved_count = 0
    for opp_id in pending_ids:
        if apply_resolution(conn, opp_id):
            resolved_count += 1
    return resolved_count
