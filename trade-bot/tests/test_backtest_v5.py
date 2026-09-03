import numpy as np
import pandas as pd

from tradebot.backtest import run_backtest
from tradebot.backtest_v5 import FAR_ZONE_SIZE_MULTIPLIER, _position_size, run_backtest_v5
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


def test_v5_trades_same_days_as_v1():
    """A V5 só muda tamanho de posição, não timing de entrada/saída -> mesmo
    número de trades completos que a V1 (ela nunca recusa um trade)."""
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    v1 = run_backtest(df, "TEST", cfg)
    v5 = run_backtest_v5(df, "TEST", cfg)
    assert v5.metrics["num_trades"] == v1.metrics["num_trades"]
    assert v5.final_summary["num_fills"] == v1.final_summary["num_fills"]


def test_position_size_full_near_fib_zone():
    row = pd.Series({"fib_382": 106.18, "fib_500": 100.0, "fib_618": 93.82})
    assert _position_size(100.5, row, cash_fraction=0.5) == 0.5


def test_position_size_reduced_far_from_fib_zone():
    row = pd.Series({"fib_382": 106.18, "fib_500": 100.0, "fib_618": 93.82})
    assert _position_size(115.0, row, cash_fraction=0.5) == 0.5 * FAR_ZONE_SIZE_MULTIPLIER


def test_run_backtest_v5_does_not_crash_and_produces_valid_result():
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    result = run_backtest_v5(df, "TEST", cfg)
    assert "fib_500" in result.signals.columns
    assert result.final_summary["cash"] >= 0
    assert len(result.equity_curve) == len(df)
