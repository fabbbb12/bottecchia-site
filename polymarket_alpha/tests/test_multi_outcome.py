from arbitrage.multi_outcome import (
    MarketStructure,
    detect_gross_edge,
    evaluate_multi_outcome_opportunity,
    max_profitable_size,
)
from fees import FeeConfig

ZERO_FEE = FeeConfig(trading_fee_bps=0, gas_cost_usd=0.0, slippage_model="x", verified_against=None, verified_at=None)

VALID_STRUCTURE = MarketStructure(
    mutually_exclusive=True, collectively_exhaustive=True, neg_risk=True, classification_notes="4 candidatos, 1 vence"
)
UNVERIFIED_STRUCTURE = MarketStructure(
    mutually_exclusive=None, collectively_exhaustive=None, neg_risk=None, classification_notes="não verificado"
)


def test_detect_gross_edge_multi_outcome():
    assert round(detect_gross_edge([0.2, 0.2, 0.2, 0.3]), 6) == 0.1


def test_rejects_opportunity_when_structure_not_confirmed():
    """SUM(ASK) < 1 não é o suficiente -- sem confirmação de mutuamente
    exclusivo + exaustivo, nunca tratamos como arbitragem real."""
    levels = [[(0.20, 100.0)]] * 4  # soma = 0.80, gross_edge = 0.20
    opp = evaluate_multi_outcome_opportunity("MKT1", 1, levels, UNVERIFIED_STRUCTURE, ZERO_FEE)
    assert opp.is_candidate  # o preço sugere oportunidade
    assert not opp.structure_valid  # mas a estrutura não foi confirmada
    assert opp.capital_executable == 0.0  # então não executamos nada
    assert opp.net_edge is None


def test_accepts_opportunity_when_structure_confirmed():
    levels = [[(0.20, 100.0)]] * 4
    opp = evaluate_multi_outcome_opportunity("MKT2", 1, levels, VALID_STRUCTURE, ZERO_FEE)
    assert opp.is_candidate
    assert opp.structure_valid
    assert opp.capital_executable == 100.0
    assert opp.net_edge is not None and round(opp.net_edge, 6) == 0.20


def test_max_profitable_size_stops_at_shallow_leg():
    # 2o nivel do 1o outcome sobe pra 0.85: 0.85 + 0.20*3 = 1.45 > 1 -> para ali
    levels = [
        [(0.20, 10.0), (0.85, 1000.0)],
        [(0.20, 1000.0)],
        [(0.20, 1000.0)],
        [(0.20, 1000.0)],
    ]
    qty, avg_prices = max_profitable_size(levels, ZERO_FEE)
    assert qty == 10.0
    assert avg_prices == [0.20, 0.20, 0.20, 0.20]


def test_no_candidate_when_sum_above_one():
    levels = [[(0.30, 100.0)]] * 4  # soma = 1.20
    opp = evaluate_multi_outcome_opportunity("MKT3", 1, levels, VALID_STRUCTURE, ZERO_FEE)
    assert not opp.is_candidate
    assert opp.capital_executable == 0.0
