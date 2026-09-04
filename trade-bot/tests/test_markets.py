import pytest

from tradebot.markets import (
    BR_WATCHLIST,
    CRYPTO_WATCHLIST,
    US_DIVERSIFIED_WATCHLIST,
    US_WATCHLIST,
    resolve_symbols,
)


def test_resolve_symbols_market_us():
    assert resolve_symbols("us", None) == US_WATCHLIST


def test_resolve_symbols_market_br():
    assert resolve_symbols("br", None) == BR_WATCHLIST


def test_resolve_symbols_market_all_has_both():
    result = resolve_symbols("all", None)
    for s in US_WATCHLIST + BR_WATCHLIST:
        assert s in result


def test_resolve_symbols_custom_list():
    result = resolve_symbols(None, "AAPL, PETR4.SA ,VALE3.SA")
    assert result == ["AAPL", "PETR4.SA", "VALE3.SA"]


def test_resolve_symbols_dedupes_preserving_order():
    result = resolve_symbols("us", "AAPL,TSLA")
    assert result[0] == "AAPL"
    assert result.count("AAPL") == 1
    assert "TSLA" in result


def test_resolve_symbols_unknown_market_raises():
    with pytest.raises(ValueError):
        resolve_symbols("xx", None)


def test_resolve_symbols_market_diversified_has_diversified_us_and_br():
    result = resolve_symbols("diversified", None)
    for s in US_DIVERSIFIED_WATCHLIST + BR_WATCHLIST:
        assert s in result
    # não deve trazer os mega caps de tecnologia da US_WATCHLIST original
    for s in US_WATCHLIST:
        assert s not in result


def test_diversified_watchlist_same_size_as_original_us_watchlist():
    # mesmo tamanho, pra comparação justa (só muda a composição setorial)
    assert len(US_DIVERSIFIED_WATCHLIST) == len(US_WATCHLIST)


def test_resolve_symbols_market_crypto():
    assert resolve_symbols("crypto", None) == CRYPTO_WATCHLIST


def test_crypto_watchlist_tickers_use_usd_suffix():
    # formato aceito pelo yfinance pra cripto, sem precisar de API da corretora
    for s in CRYPTO_WATCHLIST:
        assert s.endswith("-USD")
