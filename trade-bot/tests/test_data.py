from unittest.mock import patch

import numpy as np
import pandas as pd

from tradebot.data import fetch_ohlcv


def _fake_raw(n=10):
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    prices = 100 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {"Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": 1000}, index=idx
    )


def test_fetch_ohlcv_uses_period_by_default():
    with patch("tradebot.data.yf.download", return_value=_fake_raw()) as mock_download:
        fetch_ohlcv("AAPL", period="1y", interval="1d")
        _, kwargs = mock_download.call_args
        assert kwargs["period"] == "1y"
        assert "start" not in kwargs


def test_fetch_ohlcv_uses_start_end_when_given():
    with patch("tradebot.data.yf.download", return_value=_fake_raw()) as mock_download:
        fetch_ohlcv("AAPL", period="1y", interval="1d", start="2018-01-01", end="2020-01-01")
        _, kwargs = mock_download.call_args
        assert kwargs["start"] == "2018-01-01"
        assert kwargs["end"] == "2020-01-01"
        assert "period" not in kwargs


def test_fetch_ohlcv_start_without_end_is_allowed():
    with patch("tradebot.data.yf.download", return_value=_fake_raw()) as mock_download:
        fetch_ohlcv("AAPL", start="2018-01-01")
        _, kwargs = mock_download.call_args
        assert kwargs["start"] == "2018-01-01"
        assert kwargs["end"] is None
