import pytest

from tradebot.markets import BR_WATCHLIST, US_WATCHLIST, resolve_symbols


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
