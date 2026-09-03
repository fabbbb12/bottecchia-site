import numpy as np
import pandas as pd

from tradebot import indicators as ind
from tradebot.backtest_v3 import FIB_TOLERANCE_PCT, _near_fib_zone, run_backtest_v3
from tradebot.strategy import StrategyConfig


def test_fibonacci_levels_basic_range():
    high = pd.Series([110.0] * 60)
    low = pd.Series([90.0] * 60)
    levels = ind.fibonacci_levels(high, low, period=50)
    row = levels.iloc[-1]
    assert row["swing_high"] == 110.0
    assert row["swing_low"] == 90.0
    # 50% de retração de um range de 20 (110 a 90) -> 100
    assert row["fib_500"] == 100.0
    # 61.8% a partir da máxima -> mais perto da mínima
    assert row["fib_618"] < row["fib_500"] < row["fib_382"]


def test_fibonacci_levels_nan_before_period():
    high = pd.Series(np.arange(100, 130, dtype=float))
    low = high - 5
    levels = ind.fibonacci_levels(high, low, period=50)
    assert levels["fib_500"].iloc[:49].isna().all()


def test_near_fib_zone_true_within_tolerance():
    row = pd.Series({"fib_382": 106.18, "fib_500": 100.0, "fib_618": 93.82})
    assert _near_fib_zone(100.5, row) is True  # perto do 500


def test_near_fib_zone_false_far_from_all_levels():
    row = pd.Series({"fib_382": 106.18, "fib_500": 100.0, "fib_618": 93.82})
    assert _near_fib_zone(115.0, row) is False


def test_near_fib_zone_handles_nan_levels():
    row = pd.Series({"fib_382": float("nan"), "fib_500": float("nan"), "fib_618": float("nan")})
    assert _near_fib_zone(100.0, row) is False


def _uptrend_with_pullbacks(n=400, seed=1):
    rng = np.random.default_rng(seed)
    trend = np.linspace(0, 50, n)
    noise = rng.normal(0, 2.5, n)
    prices = 100 + trend + noise
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.01, "low": prices * 0.99, "close": prices, "volume": 1000}, index=idx
    )


def test_run_backtest_v3_does_not_crash_and_produces_valid_result():
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    result = run_backtest_v3(df, "TEST", cfg)
    assert "fib_500" in result.signals.columns
    assert result.final_summary["cash"] >= 0
    assert len(result.equity_curve) == len(df)


def test_run_backtest_v3_never_buys_far_from_fib_zone():
    # sobe reto sem nunca recuar perto de um nivel de fibonacci -> V3 nao deve comprar
    cfg = StrategyConfig()
    n = 300
    prices = 100 + np.linspace(0, 100, n)  # alta monotonica, sem pullback
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {"open": prices, "high": prices * 1.001, "low": prices * 0.999, "close": prices, "volume": 1000}, index=idx
    )
    result = run_backtest_v3(df, "TEST", cfg)
    # numa alta reta e monotonica o preco atual esta sempre no topo do swing,
    # nunca perto dos niveis de retracao -> nenhuma compra deveria acontecer
    assert result.final_summary["num_fills"] == 0
