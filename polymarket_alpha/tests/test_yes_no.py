from arbitrage.yes_no import detect_gross_edge, evaluate_yes_no_opportunity, max_profitable_size
from fees import FeeConfig

ZERO_FEE = FeeConfig(trading_fee_bps=0, gas_cost_usd=0.0, slippage_model="x", verified_against=None, verified_at=None)


def test_detect_gross_edge_positive_when_sum_below_one():
    assert round(detect_gross_edge(0.45, 0.50), 6) == 0.05


def test_detect_gross_edge_negative_when_sum_above_one():
    assert detect_gross_edge(0.55, 0.55) < 0


def test_max_profitable_size_limited_by_shallow_depth():
    # só 10 unidades no melhor nível de cada lado -> não pode ir além disso
    yes_levels = [(0.45, 10.0), (0.60, 1000.0)]
    no_levels = [(0.50, 10.0), (0.60, 1000.0)]
    qty, avg_yes, avg_no = max_profitable_size(yes_levels, no_levels, ZERO_FEE)
    assert qty == 10.0
    assert avg_yes == 0.45
    assert avg_no == 0.50


def test_opportunity_disappears_when_real_depth_considered():
    """Teste explícito exigido pela Seção 19: uma oportunidade aparente no
    topo do book (best ask) some quando a profundidade real é considerada
    — aqui, o segundo nível já não é lucrativo (0.55 + 0.55 > 1), então o
    tamanho executável para exatamente no fim do primeiro nível."""
    yes_levels = [(0.45, 5.0), (0.55, 1000.0)]
    no_levels = [(0.50, 5.0), (0.55, 1000.0)]

    # candidata pelo topo do book: 0.45 + 0.50 = 0.95 < 1 -> parece lucrativa
    assert detect_gross_edge(yes_levels[0][0], no_levels[0][0]) > 0

    qty, avg_yes, avg_no = max_profitable_size(yes_levels, no_levels, ZERO_FEE)
    # mas só 5 unidades são realmente lucrativas -- além disso, 0.55+0.55=1.10 > 1
    assert qty == 5.0

    opp = evaluate_yes_no_opportunity("MKT1", 1_700_000_000, yes_levels, no_levels, ZERO_FEE)
    assert opp.is_candidate
    assert opp.capital_executable == 5.0
    assert opp.net_edge is not None and opp.net_edge > 0


def test_no_candidate_when_gross_edge_negative():
    yes_levels = [(0.55, 100.0)]
    no_levels = [(0.55, 100.0)]
    opp = evaluate_yes_no_opportunity("MKT2", 1_700_000_000, yes_levels, no_levels, ZERO_FEE)
    assert not opp.is_candidate
    assert opp.capital_executable == 0.0
    assert opp.net_edge is None


def test_fees_reduce_net_edge():
    yes_levels = [(0.45, 100.0)]
    no_levels = [(0.50, 100.0)]
    fee_cfg = FeeConfig(trading_fee_bps=500, gas_cost_usd=0.0, slippage_model="x", verified_against=None, verified_at=None)
    opp_no_fee = evaluate_yes_no_opportunity("MKT3", 1, yes_levels, no_levels, ZERO_FEE)
    opp_with_fee = evaluate_yes_no_opportunity("MKT3", 1, yes_levels, no_levels, fee_cfg)
    assert opp_with_fee.net_edge < opp_no_fee.net_edge


def test_empty_book_returns_zero_size():
    qty, avg_yes, avg_no = max_profitable_size([], [(0.5, 10.0)], ZERO_FEE)
    assert qty == 0.0
    assert avg_yes is None
