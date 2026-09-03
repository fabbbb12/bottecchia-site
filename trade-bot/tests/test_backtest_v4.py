import numpy as np
import pandas as pd

from tradebot.backtest import run_backtest
from tradebot.backtest_v4 import run_backtest_v4
from tradebot.comparison import print_fibonacci_placebo_test
from tradebot.strategy import StrategyConfig


def _uptrend_with_pullbacks(n=400, seed=1):
    rng = np.random.default_rng(seed)
    trend = np.linspace(0, 50, n)
    pullback = np.sin(np.linspace(0, 8 * np.pi, n)) * 8
    noise = rng.normal(0, 2.0, n)
    prices = 100 + trend + pullback + noise
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.01, "low": prices * 0.99, "close": prices, "volume": 1000}, index=idx
    )


def test_v4_is_deterministic_with_same_seed():
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    r1 = run_backtest_v4(df, "TEST", cfg, seed=42)
    r2 = run_backtest_v4(df, "TEST", cfg, seed=42)
    assert r1.final_summary["pnl_pct"] == r2.final_summary["pnl_pct"]
    assert r1.metrics["num_trades"] == r2.metrics["num_trades"]


def test_v4_differs_with_different_seed():
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    r1 = run_backtest_v4(df, "TEST", cfg, seed=1)
    r2 = run_backtest_v4(df, "TEST", cfg, seed=2)
    # sementes diferentes devem produzir sorteios diferentes em algum ponto
    assert r1.final_summary["pnl_pct"] != r2.final_summary["pnl_pct"] or r1.metrics["num_trades"] != r2.metrics[
        "num_trades"
    ]


def test_v4_trades_less_than_or_equal_to_v1():
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    v1 = run_backtest(df, "TEST", cfg)
    v4 = run_backtest_v4(df, "TEST", cfg)
    # o placebo só recusa compras, nunca adiciona -> nunca deve operar mais que a V1
    assert v4.metrics["num_trades"] <= v1.metrics["num_trades"]


def test_print_fibonacci_placebo_test_runs_without_crashing(capsys):
    cfg = StrategyConfig()
    from tradebot.backtest_v3 import run_backtest_v3

    df_a = _uptrend_with_pullbacks(seed=3)
    df_b = _uptrend_with_pullbacks(seed=4)
    v1_results = {"A": run_backtest(df_a, "A", cfg), "B": run_backtest(df_b, "B", cfg)}
    v3_results = {"A": run_backtest_v3(df_a, "A", cfg), "B": run_backtest_v3(df_b, "B", cfg)}
    v4_results = {"A": run_backtest_v4(df_a, "A", cfg), "B": run_backtest_v4(df_b, "B", cfg)}
    print_fibonacci_placebo_test(v1_results, v3_results, v4_results)
    out = capsys.readouterr().out
    assert "Teste de placebo" in out
    assert "V3 tem drawdown melhor que V4" in out


def test_print_fibonacci_placebo_test_handles_no_common_symbols(capsys):
    print_fibonacci_placebo_test({}, {}, {})
    out = capsys.readouterr().out
    assert "Nenhum símbolo em comum" in out
