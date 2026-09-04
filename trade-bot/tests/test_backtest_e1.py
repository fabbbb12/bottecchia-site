import numpy as np
import pandas as pd

from tradebot.backtest_e1 import compute_spread_signals, run_backtest_e1


def _make_pair_dfs(n=150, spike_start=100, spike_end=115, seed=1):
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    rng = np.random.default_rng(seed)
    b = 100 + rng.normal(0, 0.3, n).cumsum() * 0.05 + 100  # ativo B, leve caminhada
    noise_a = rng.normal(0, 0.002, n)  # ruído relativo pequeno em condições normais
    a = b * (1 + noise_a)
    # spread se afasta muito da média durante a janela de "spike" -> deve
    # gerar sinal de entrada; antes e depois disso o spread é só ruído
    a = a.copy()
    a[spike_start:spike_end] = b[spike_start:spike_end] * 1.30

    df_a = pd.DataFrame({"open": a, "high": a * 1.005, "low": a * 0.995, "close": a, "volume": 1000}, index=idx)
    df_b = pd.DataFrame({"open": b, "high": b * 1.005, "low": b * 0.995, "close": b, "volume": 1000}, index=idx)
    return df_a, df_b


def test_spread_signals_nan_before_lookback():
    df_a, df_b = _make_pair_dfs()
    signals = compute_spread_signals(df_a, df_b, lookback_days=60)
    assert signals["zscore"].iloc[:59].isna().all()


def test_spread_signals_aligns_by_common_dates():
    df_a, df_b = _make_pair_dfs()
    # remove um dia só do B -> a interseção deve excluir esse dia dos dois
    df_b_missing = df_b.drop(df_b.index[10])
    signals = compute_spread_signals(df_a, df_b_missing, lookback_days=60)
    assert len(signals) == len(df_a) - 1


def test_spike_produces_large_absolute_zscore():
    df_a, df_b = _make_pair_dfs()
    signals = compute_spread_signals(df_a, df_b, lookback_days=60)
    # durante o spike (A 30% mais caro que B), o z-score deve estourar o
    # limiar de entrada (2.0) -- valor bem alto, não é ruído
    spike_zscore = signals["zscore"].iloc[102]
    assert abs(spike_zscore) > 2.0


def test_run_backtest_e1_does_not_crash_and_produces_valid_result():
    df_a, df_b = _make_pair_dfs()
    result = run_backtest_e1(df_a, df_b, "A", "B")
    assert len(result.equity_curve) > 0
    assert set(result.symbols) == {"A", "B"}


def test_run_backtest_e1_opens_both_legs_on_entry():
    df_a, df_b = _make_pair_dfs()
    result = run_backtest_e1(df_a, df_b, "A", "B", lookback_days=60)
    # o spike deve ter disparado pelo menos uma entrada com as duas pernas
    # abertas simultaneamente em algum momento (compra + venda a descoberto)
    assert result.final_summary["num_fills"] >= 2


def test_no_trade_before_enough_lookback_history():
    n = 40  # menor que o lookback padrão (60) -> nunca deve operar
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    a = np.full(n, 100.0)
    b = np.full(n, 100.0)
    df_a = pd.DataFrame({"open": a, "high": a, "low": a, "close": a, "volume": 1000}, index=idx)
    df_b = pd.DataFrame({"open": b, "high": b, "low": b, "close": b, "volume": 1000}, index=idx)
    result = run_backtest_e1(df_a, df_b, "A", "B", lookback_days=60)
    assert result.final_summary["num_fills"] == 0


def test_benchmark_is_flat_cash_not_directional():
    df_a, df_b = _make_pair_dfs()
    result = run_backtest_e1(df_a, df_b, "A", "B")
    # estratégia mercado-neutro: benchmark é caixa parado, não buy-and-hold
    assert (result.benchmark_curve == result.benchmark_curve.iloc[0]).all()
