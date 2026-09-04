from unittest.mock import Mock, patch

import pandas as pd
import pytest

from tradebot import binance_data
from tradebot.binance_data import _period_to_start_date, fetch_binance_klines, is_binance_symbol


def test_is_binance_symbol_true_for_usdt_pairs():
    assert is_binance_symbol("BTCUSDT") is True
    assert is_binance_symbol("ethusdt") is True  # case-insensitive


def test_is_binance_symbol_false_for_other_tickers():
    assert is_binance_symbol("AAPL") is False
    assert is_binance_symbol("BTC-USD") is False  # formato yfinance, não Binance
    assert is_binance_symbol("PETR4.SA") is False


def test_period_to_start_date_parses_common_formats():
    assert _period_to_start_date("1y") is not None
    assert _period_to_start_date("6mo") is not None
    assert _period_to_start_date("5d") is not None


def test_period_to_start_date_rejects_unsupported_format():
    with pytest.raises(ValueError):
        _period_to_start_date("ytd")
    with pytest.raises(ValueError):
        _period_to_start_date("max")


def _make_kline_row(open_time_ms, close_time_ms, price=100.0):
    return [
        open_time_ms,
        str(price),
        str(price * 1.01),
        str(price * 0.99),
        str(price * 1.005),
        "1000.0",
        close_time_ms,
        "100000.0",
        50,
        "500.0",
        "50000.0",
        "0",
    ]


def test_fetch_binance_klines_single_page_returns_expected_shape():
    rows = [_make_kline_row(1700000000000 + i * 86400000, 1700000000000 + (i + 1) * 86400000 - 1) for i in range(5)]
    mock_response = Mock()
    mock_response.json.return_value = rows
    mock_response.raise_for_status.return_value = None

    with patch.object(binance_data.requests, "get", return_value=mock_response) as mock_get:
        df = fetch_binance_klines("BTCUSDT", interval="1d", start="2023-01-01", end="2023-01-10")

    assert mock_get.call_count == 1
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 5
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df["close"].dtype == float


def test_fetch_binance_klines_paginates_until_full_page_not_returned(monkeypatch):
    monkeypatch.setattr(binance_data, "MAX_KLINES_PER_REQUEST", 2)
    monkeypatch.setattr(binance_data, "PAGINATION_SLEEP_SECONDS", 0)

    day = 86400000
    base = binance_data._to_millis("2023-01-01")  # dentro da janela start/end pedida no teste
    page1 = [_make_kline_row(base, base + day - 1), _make_kline_row(base + day, base + 2 * day - 1)]
    page2 = [_make_kline_row(base + 2 * day, base + 3 * day - 1)]  # última pagina, menor que o limite

    mock_response_1 = Mock(json=Mock(return_value=page1), raise_for_status=Mock())
    mock_response_2 = Mock(json=Mock(return_value=page2), raise_for_status=Mock())

    with patch.object(binance_data.requests, "get", side_effect=[mock_response_1, mock_response_2]) as mock_get:
        df = fetch_binance_klines("BTCUSDT", interval="1d", start="2023-01-01", end="2023-01-10")

    assert mock_get.call_count == 2
    assert len(df) == 3


def test_fetch_binance_klines_empty_response_raises():
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None

    with patch.object(binance_data.requests, "get", return_value=mock_response):
        with pytest.raises(ValueError):
            fetch_binance_klines("BTCUSDT", interval="1d", start="2023-01-01", end="2023-01-10")


def test_fetch_ohlcv_routes_usdt_symbols_to_binance():
    from tradebot import data

    fake_df = pd.DataFrame(
        {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]},
        index=pd.DatetimeIndex(["2023-01-01"]),
    )
    with patch.object(data, "fetch_binance_klines", return_value=fake_df) as mock_binance:
        with patch.object(data, "yf") as mock_yf:
            result = data.fetch_ohlcv("BTCUSDT", period="1y")

    mock_binance.assert_called_once()
    mock_yf.download.assert_not_called()
    assert result is fake_df
