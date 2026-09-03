import numpy as np
import pandas as pd

from tradebot.backtest import run_backtest
from tradebot.backtest_v2 import print_v1_v2_comparison, run_backtest_v2
from tradebot.strategy import StrategyConfig


def _crash_and_recover_df(n=500, seed=1):
    """Simula o padrão MSFT/NVDA/GOOGL 2022: cai forte e recupera dentro
    do período — o cenário que motivou a hipótese da V2."""
    rng = np.random.default_rng(seed)
    first_half = np.linspace(0, -40, n // 2) + rng.normal(0, 1.5, n // 2)
    second_half = np.linspace(-40, 20, n - n // 2) + rng.normal(0, 1.5, n - n // 2)
    prices = 100 + np.concatenate([first_half, second_half])
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.01, "low": prices * 0.99, "close": prices, "volume": 1000}, index=idx
    )


def test_v2_reenters_faster_than_v1_in_crash_and_recover_scenario():
    cfg = StrategyConfig()
    df = _crash_and_recover_df()
    v1 = run_backtest(df, "TEST", cfg)
    v2 = run_backtest_v2(df, "TEST", cfg)

    # a hipótese da V2 é reentrar mais rápido -> não deve ter MENOS trades
    # que a V1 no cenário desenhado justamente para forçar reentradas
    assert v2.metrics["num_trades"] >= v1.metrics["num_trades"]


def test_v2_runs_on_flat_market_without_crashing():
    cfg = StrategyConfig()
    idx = pd.date_range("2021-01-01", periods=300, freq="D")
    prices = np.full(300, 100.0)
    df = pd.DataFrame(
        {"open": prices, "high": prices * 1.001, "low": prices * 0.999, "close": prices, "volume": 1000}, index=idx
    )
    result = run_backtest_v2(df, "FLAT", cfg)
    assert result.metrics["num_trades"] == 0


def test_v2_never_ends_with_negative_cash():
    cfg = StrategyConfig()
    df = _crash_and_recover_df(seed=2)
    result = run_backtest_v2(df, "TEST", cfg)
    assert result.final_summary["cash"] >= 0


def test_print_v1_v2_comparison_runs_without_crashing(capsys):
    cfg = StrategyConfig()
    df_a = _crash_and_recover_df(seed=3)
    df_b = _crash_and_recover_df(seed=4)
    v1_results = {"A": run_backtest(df_a, "A", cfg), "B": run_backtest(df_b, "B", cfg)}
    v2_results = {"A": run_backtest_v2(df_a, "A", cfg), "B": run_backtest_v2(df_b, "B", cfg)}
    print_v1_v2_comparison(v1_results, v2_results)
    out = capsys.readouterr().out
    assert "V1 vs V2 vs Buy&Hold" in out
    assert "V2>V1" in out


def test_print_v1_v2_comparison_handles_no_common_symbols(capsys):
    print_v1_v2_comparison({}, {})
    out = capsys.readouterr().out
    assert "Nenhum símbolo em comum" in out
