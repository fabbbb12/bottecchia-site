"""Arbitragem multi-outcome — Seção 7.

IMPORTANTE: SUM(ASK_i) < 1 NÃO é automaticamente arbitragem. Só é
arbitragem se os outcomes forem mutuamente exclusivos E coletivamente
exaustivos (garantindo que exatamente um deles paga $1 na resolução).
Essa classificação precisa vir do metadado do mercado (campos
`mutually_exclusive` / `collectively_exhaustive` / `neg_risk` na tabela
`markets`), nunca inferida aqui — ver Seção 7 e `classification_notes`.
"""

from dataclasses import dataclass

from execution import Level, _cumulative_levels, _price_at_depth
from fees import FeeConfig, compute_fee_cost


@dataclass
class MarketStructure:
    """Classificação explícita do mercado — nunca inferida por este módulo,
    sempre vinda do metadado coletado (Seção 7, passos 1-5)."""

    mutually_exclusive: bool | None
    collectively_exhaustive: bool | None
    neg_risk: bool | None
    classification_notes: str = ""

    @property
    def is_valid_for_arbitrage(self) -> bool:
        """Só podemos testar SUM(ASK_i) < 1 como arbitragem de verdade se
        os outcomes forem comprovadamente ambos: mutuamente exclusivos e
        coletivamente exaustivos. Qualquer valor None (não verificado)
        conta como "não confirmado" — não assume o melhor caso."""
        return self.mutually_exclusive is True and self.collectively_exhaustive is True


@dataclass
class MultiOutcomeOpportunity:
    market_id: str
    timestamp: int
    num_outcomes: int
    sum_best_ask: float
    gross_edge: float
    is_candidate: bool
    structure_valid: bool        # MarketStructure.is_valid_for_arbitrage
    classification_notes: str
    capital_executable: float
    avg_prices: list[float] | None
    net_edge: float | None
    fees: float | None
    capital_required: float | None


def detect_gross_edge(best_asks: list[float]) -> float:
    return 1 - sum(best_asks)


def max_profitable_size(
    outcome_levels: list[list[Level]], fee_config: FeeConfig
) -> tuple[float, list[float] | None]:
    """Generalização do caso YES/NO para N outcomes: compra 1 unidade de
    cada outcome simultaneamente, nível por nível, até a próxima unidade
    marginal deixar de ser lucrativa ou algum lado ficar sem profundidade."""
    cumulative = [_cumulative_levels(levels) for levels in outcome_levels]
    if any(not c for c in cumulative):
        return 0.0, None

    breakpoints = sorted(set().union(*[{depth for depth, _ in c} for c in cumulative]))

    max_q = 0.0
    costs = [0.0] * len(outcome_levels)
    prev_q = 0.0
    fee_rate = fee_config.trading_fee_bps / 10_000

    for bp in breakpoints:
        prices = [_price_at_depth(c, bp) for c in cumulative]
        if any(p is None for p in prices):
            break

        marginal_cost = sum(prices) * (1 + fee_rate)
        if marginal_cost >= 1.0:
            break

        segment_qty = bp - prev_q
        for i, price in enumerate(prices):
            costs[i] += segment_qty * price
        max_q = bp
        prev_q = bp

    if max_q <= 0:
        return 0.0, None
    return max_q, [c / max_q for c in costs]


def evaluate_multi_outcome_opportunity(
    market_id: str,
    timestamp: int,
    outcome_levels: list[list[Level]],
    structure: MarketStructure,
    fee_config: FeeConfig,
) -> MultiOutcomeOpportunity:
    best_asks = [levels[0][0] if levels else float("nan") for levels in outcome_levels]
    gross_edge = detect_gross_edge(best_asks)
    is_candidate = gross_edge > 0
    num_outcomes = len(outcome_levels)

    base = dict(
        market_id=market_id,
        timestamp=timestamp,
        num_outcomes=num_outcomes,
        sum_best_ask=sum(best_asks),
        gross_edge=gross_edge,
        is_candidate=is_candidate,
        structure_valid=structure.is_valid_for_arbitrage,
        classification_notes=structure.classification_notes,
    )

    if not is_candidate or not structure.is_valid_for_arbitrage:
        # Ou não há discrepância de preço, ou a estrutura do mercado não
        # foi confirmada como mutuamente exclusiva + exaustiva — nesse
        # caso NUNCA tratamos como arbitragem, mesmo que os preços sugiram.
        return MultiOutcomeOpportunity(
            **base, capital_executable=0.0, avg_prices=None, net_edge=None, fees=None, capital_required=None
        )

    qty, avg_prices = max_profitable_size(outcome_levels, fee_config)
    if qty <= 0 or avg_prices is None:
        return MultiOutcomeOpportunity(
            **base, capital_executable=0.0, avg_prices=None, net_edge=None, fees=None, capital_required=None
        )

    capital_required = sum(avg_prices) * qty
    fees = compute_fee_cost(capital_required, fee_config, num_legs=num_outcomes)
    net_edge = (1 - sum(avg_prices)) - (fees / qty if qty else 0.0)

    return MultiOutcomeOpportunity(
        **base,
        capital_executable=qty,
        avg_prices=avg_prices,
        net_edge=net_edge,
        fees=fees,
        capital_required=capital_required,
    )
