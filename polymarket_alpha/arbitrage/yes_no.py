"""Arbitragem YES + NO — Seção 5.

Detecção: ASK(YES) + ASK(NO) < 1 usando o topo do book (candidata).
Mas o tamanho realmente executável — e portanto o lucro líquido real —
depende de caminhar a profundidade dos dois books simultaneamente
(Seção 6 e 14): comprar 1 unidade de YES e 1 de NO ao mesmo tempo, nível
por nível, até o ponto em que a próxima unidade marginal deixaria de ser
lucrativa ou a profundidade de um dos dois lados acabar.
"""

from dataclasses import dataclass

from execution import Level, _cumulative_levels, _price_at_depth
from fees import FeeConfig, compute_fee_cost


@dataclass
class YesNoOpportunity:
    market_id: str
    timestamp: int
    best_ask_yes: float
    best_ask_no: float
    gross_edge: float           # 1 - best_ask_yes - best_ask_no, usando só o topo do book
    is_candidate: bool          # gross_edge > 0 (ainda não confirma que é executável)
    capital_executable: float   # unidades que dá pra comprar dos dois lados de forma lucrativa
    avg_price_yes: float | None
    avg_price_no: float | None
    net_edge: float | None      # por unidade, já líquido de taxas
    fees: float | None          # custo total de taxas na execução completa
    slippage: float | None      # quanto o preço médio piorou vs. o topo do book (soma dos dois lados)
    capital_required: float | None  # capital total (USD) para executar capital_executable unidades


def detect_gross_edge(best_ask_yes: float, best_ask_no: float) -> float:
    return 1 - best_ask_yes - best_ask_no


def max_profitable_size(
    yes_levels: list[Level], no_levels: list[Level], fee_config: FeeConfig
) -> tuple[float, float | None, float | None]:
    """Tamanho máximo (em unidades) em que comprar 1 YES + 1 NO simultaneamente
    continua lucrativo na margem, respeitando a profundidade real dos dois
    books. Devolve (quantidade, preço médio YES, preço médio NO).

    Isso é o que faz uma oportunidade "desaparecer" quando a profundidade
    real é considerada: se o segundo nível do book já não for lucrativo,
    o tamanho para exatamente no fim do primeiro nível lucrativo."""
    cum_yes = _cumulative_levels(yes_levels)
    cum_no = _cumulative_levels(no_levels)
    if not cum_yes or not cum_no:
        return 0.0, None, None

    breakpoints = sorted({depth for depth, _ in cum_yes} | {depth for depth, _ in cum_no})

    max_q = 0.0
    cost_yes = 0.0
    cost_no = 0.0
    prev_q = 0.0
    fee_rate = fee_config.trading_fee_bps / 10_000

    for bp in breakpoints:
        price_yes = _price_at_depth(cum_yes, bp)
        price_no = _price_at_depth(cum_no, bp)
        if price_yes is None or price_no is None:
            break  # um dos dois lados ficou sem profundidade

        marginal_cost = (price_yes + price_no) * (1 + fee_rate)
        if marginal_cost >= 1.0:
            break  # a próxima unidade marginal já não compensa

        segment_qty = bp - prev_q
        cost_yes += segment_qty * price_yes
        cost_no += segment_qty * price_no
        max_q = bp
        prev_q = bp

    if max_q <= 0:
        return 0.0, None, None
    return max_q, cost_yes / max_q, cost_no / max_q


def evaluate_yes_no_opportunity(
    market_id: str,
    timestamp: int,
    yes_levels: list[Level],
    no_levels: list[Level],
    fee_config: FeeConfig,
) -> YesNoOpportunity:
    best_ask_yes = yes_levels[0][0] if yes_levels else float("nan")
    best_ask_no = no_levels[0][0] if no_levels else float("nan")
    gross_edge = detect_gross_edge(best_ask_yes, best_ask_no)
    is_candidate = gross_edge > 0

    if not is_candidate:
        return YesNoOpportunity(
            market_id, timestamp, best_ask_yes, best_ask_no, gross_edge, False,
            0.0, None, None, None, None, None, None,
        )

    qty, avg_yes, avg_no = max_profitable_size(yes_levels, no_levels, fee_config)
    if qty <= 0 or avg_yes is None or avg_no is None:
        # candidata pelo topo do book, mas não sobrevive à profundidade real
        return YesNoOpportunity(
            market_id, timestamp, best_ask_yes, best_ask_no, gross_edge, True,
            0.0, None, None, None, None, None, None,
        )

    capital_required = (avg_yes + avg_no) * qty
    fees = compute_fee_cost(capital_required, fee_config, num_legs=2)
    net_edge = (1 - avg_yes - avg_no) - (fees / qty if qty else 0.0)
    slippage = (avg_yes - best_ask_yes) + (avg_no - best_ask_no)

    return YesNoOpportunity(
        market_id=market_id,
        timestamp=timestamp,
        best_ask_yes=best_ask_yes,
        best_ask_no=best_ask_no,
        gross_edge=gross_edge,
        is_candidate=True,
        capital_executable=qty,
        avg_price_yes=avg_yes,
        avg_price_no=avg_no,
        net_edge=net_edge,
        fees=fees,
        slippage=slippage,
        capital_required=capital_required,
    )
