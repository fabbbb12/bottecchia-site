from datetime import datetime

from tradebot.portfolio import Portfolio, compute_round_trip_pnls


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


def test_short_receives_cash_and_opens_negative_position():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    fill = p.short(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=0.5)
    assert fill is not None
    assert fill.side == "SHORT"
    assert p.cash == 1500.0  # recebeu o valor da venda a descoberto
    assert p.position("BTC-USD").quantity == -5.0


def test_cover_profits_when_price_falls():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.short(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=1.0)
    # preço caiu -> recompra mais barato -> lucro
    fill = p.cover(datetime(2024, 1, 2), "BTC-USD", market_price=60.0, position_fraction=1.0)
    assert fill is not None
    assert fill.side == "COVER"
    assert p.position("BTC-USD").quantity == 0.0
    # vendeu 10 unidades a 100 (recebeu 1000, caixa vai a 2000) e recomprou
    # a 60 (paga 600) -> sobra 1400, lucro de 400 sobre os 1000 iniciais
    assert p.cash == 1400.0


def test_cover_loses_when_price_rises():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.short(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=1.0)
    equity_before = p.equity({"BTC-USD": 100.0})
    p.cover(datetime(2024, 1, 2), "BTC-USD", market_price=150.0, position_fraction=1.0)
    equity_after = p.equity({"BTC-USD": 150.0})
    assert equity_after < equity_before


def test_equity_reflects_short_position_mark_to_market():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.short(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=0.5)
    # preço subiu -> posição vendida perde valor -> equity cai frente ao caixa recebido
    equity_up = p.equity({"BTC-USD": 120.0})
    equity_down = p.equity({"BTC-USD": 80.0})
    assert equity_down > equity_up


def test_summary_positions_includes_short_quantity():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.short(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=0.5)
    summary = p.summary({"BTC-USD": 100.0})
    assert summary["positions"]["BTC-USD"] == -5.0


def test_round_trip_pnl_for_short_trade():
    p = Portfolio(starting_cash=1000.0, fee_rate=0.0, slippage_rate=0.0)
    p.short(datetime(2024, 1, 1), "BTC-USD", market_price=100.0, cash_fraction=1.0)  # 10 unidades vendidas a 100
    p.cover(datetime(2024, 1, 2), "BTC-USD", market_price=60.0, position_fraction=1.0)  # recompra a 60
    trades = compute_round_trip_pnls(p.fills)
    assert len(trades) == 1
    assert trades[0] > 0  # lucro: vendeu caro, recomprou barato
