from datetime import datetime

from tradebot.portfolio import Portfolio


def test_buy_reduces_cash_and_creates_position():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    fill = p.buy(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=0.5)
    assert fill is not None
    assert fill.side == "BUY"
    assert p.cash == 500.0
    assert p.position("BTC-USD").quantity == 5.0


def test_sell_full_position_returns_cash():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.buy(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=1.0)
    fill = p.sell(datetime(2024, 1, 2), "BTC-USD", market_price=120.0, position_fraction=1.0)
    assert fill is not None
    assert p.position("BTC-USD").quantity == 0.0
    assert p.cash > 1000.0  # lucro simulado


def test_fees_reduce_proceeds():
    p_no_fee = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p_with_fee = Portfolio(starting_cash=1000.0, fee_rate=0.01, slippage_rate=0.0)

    for p in (p_no_fee, p_with_fee):
        p.buy(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=1.0)
        p.sell(datetime(2024, 1, 2), "BTC-USD", market_price=100.0, position_fraction=1.0)

    assert p_with_fee.cash < p_no_fee.cash


def test_summary_reports_pnl():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.buy(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=1.0)
    summary = p.summary({"BTC-USD": 150.0})
    assert summary["equity"] == 1500.0
    assert summary["pnl"] == 500.0
    assert round(summary["pnl_pct"], 2) == 50.0
