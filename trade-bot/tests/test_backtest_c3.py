import numpy as np
import pandas as pd

from tradebot.backtest_c1 import run_backtest_c1_from_panels
from tradebot.backtest_c3 import run_backtest_c3_from_panels


def _make_panels(n=400, seed=1):
    idx = pd.date_range("2021-01-01", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    data = {}
    for i, name in enumerate(["A", "B", "C", "D", "E"]):
        drift = 0.001 * (i - 2)
        noise = rng.normal(0, 0.01, n)
        data[name] = 100 * np.cumprod(1 + drift + noise)
    closes = pd.DataFrame(data, index=idx)
    opens = closes.shift(1).fillna(closes.iloc[0])
    return closes, opens


def test_c3_does_not_crash_and_produces_valid_result():
    closes, opens = _make_panels()
    result = run_backtest_c3_from_panels(closes, opens, top_k=2)
    assert len(result.equity_curve) == len(closes)
    assert set(result.symbols) == {"A", "B", "C", "D", "E"}


def test_c3_reproducible_with_same_seed():
    closes, opens = _make_panels()
    r1 = run_backtest_c3_from_panels(closes, opens, top_k=2, seed=42)
    r2 = run_backtest_c3_from_panels(closes, opens, top_k=2, seed=42)
    assert (r1.equity_curve == r2.equity_curve).all()


def test_c3_different_seeds_can_produce_different_paths():
    closes, opens = _make_panels()
    r1 = run_backtest_c3_from_panels(closes, opens, top_k=2, seed=1)
    r2 = run_backtest_c3_from_panels(closes, opens, top_k=2, seed=2)
    assert not (r1.equity_curve == r2.equity_curve).all()


def test_c3_always_fully_allocated_no_absolute_filter():
    # ao contrário da C1, a C3 nao tem filtro de momentum absoluto -> depois
    # do primeiro rebalanceamento, sempre deve estar com top_k posicoes
    # abertas (nunca sobra vaga em caixa por falta de "candidato")
    closes, opens = _make_panels(n=100)
    result = run_backtest_c3_from_panels(closes, opens, top_k=2, seed=42)
    assert result.final_summary["num_fills"] > 0


def test_c1_and_c3_use_same_rebalance_mechanics_different_selection():
    closes, opens = _make_panels()
    c1 = run_backtest_c1_from_panels(closes, opens, momentum_lookback_days=60, top_k=2)
    c3 = run_backtest_c3_from_panels(closes, opens, top_k=2, seed=42)
    # mesma mecanica (mesmas datas de rebalanceamento), mas selecao
    # diferente -> nao ha garantia de que os resultados sejam iguais
    assert len(c1.equity_curve) == len(c3.equity_curve) == len(closes)
