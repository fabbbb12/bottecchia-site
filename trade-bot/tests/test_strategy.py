import numpy as np
import pandas as pd

from tradebot.strategy import StrategyConfig, generate_signals


def _trending_df(n=100, start=100.0, step=0.5, noise=0.05, seed=1):
    rng = np.random.default_rng(seed)
    prices = start + np.cumsum(np.full(n, step) + rng.normal(0, noise, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({"close": prices}, index=idx)


def test_generate_signals_has_expected_columns():
    df = _trending_df()
    cfg = StrategyConfig()
    result = generate_signals(df, cfg)
    for col in ["sma_fast", "sma_slow", "rsi", "macd", "score", "action"]:
        assert col in result.columns


def test_generate_signals_actions_are_valid():
    df = _trending_df()
    cfg = StrategyConfig()
    result = generate_signals(df, cfg)
    assert set(result["action"].unique()).issubset({"BUY", "SELL", "HOLD"})


def test_uptrend_favors_buy_over_sell():
    df = _trending_df(step=1.0)
    cfg = StrategyConfig()
    result = generate_signals(df, cfg).dropna(subset=["sma_slow"])
    counts = result["action"].value_counts()
    assert counts.get("BUY", 0) >= counts.get("SELL", 0)


def test_downtrend_favors_sell_over_buy():
    df = _trending_df(step=-1.0)
    cfg = StrategyConfig()
    result = generate_signals(df, cfg).dropna(subset=["sma_slow"])
    counts = result["action"].value_counts()
    assert counts.get("SELL", 0) >= counts.get("BUY", 0)
