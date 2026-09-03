import numpy as np
import pandas as pd

from tradebot import indicators as ind


def _series(values):
    return pd.Series(values, dtype=float)


def test_sma_basic():
    s = _series([1, 2, 3, 4, 5])
    result = ind.sma(s, 3)
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == 2.0
    assert result.iloc[4] == 4.0


def test_ema_length_matches_input():
    s = _series(range(1, 21))
    result = ind.ema(s, 5)
    assert len(result) == len(s)
    assert not result.iloc[-1] != result.iloc[-1]  # not NaN


def test_rsi_all_gains_is_100():
    s = _series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
    result = ind.rsi(s, period=14)
    assert result.iloc[-1] == 100.0


def test_rsi_all_losses_is_0():
    s = _series(list(reversed(range(1, 17))))
    result = ind.rsi(s, period=14)
    assert result.iloc[-1] == 0.0


def test_macd_columns():
    s = _series(np.linspace(10, 20, 60))
    df = ind.macd(s)
    assert list(df.columns) == ["macd", "signal", "histogram"]
    assert len(df) == len(s)


def test_bollinger_bands_ordering():
    s = _series(np.random.default_rng(0).normal(100, 5, 60))
    df = ind.bollinger_bands(s, period=20)
    valid = df.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["mid"] >= valid["lower"]).all()
