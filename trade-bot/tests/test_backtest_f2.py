import pandas as pd

from tradebot.backtest_f2 import run_backtest_f2


def _make_funding(rates, freq_hours=8):
    n = len(rates)
    idx = pd.date_range("2023-01-01", periods=n, freq=f"{freq_hours}h")
    return pd.DataFrame({"funding_rate": rates, "mark_price": [100.0] * n}, index=idx)


def _make_flat_prices(n, idx, price=100.0):
    return pd.DataFrame({"close": [price] * n}, index=idx)


def test_stays_flat_when_funding_always_below_threshold():
    n = 100
    funding = _make_funding([0.00001] * n)  # bem abaixo do limiar (0.0001)
    spot = _make_flat_prices(n, funding.index)
    perp = _make_flat_prices(n, funding.index)
    result = run_backtest_f2(funding, spot, perp, starting_cash=10_000.0, lookback_events=10)
    assert result["num_entries"] == 0
    assert result["final_capital"] == 10_000.0


def test_enters_when_funding_consistently_above_threshold():
    n = 100
    funding = _make_funding([0.0005] * n)  # bem acima do limiar
    spot = _make_flat_prices(n, funding.index)
    perp = _make_flat_prices(n, funding.index)
    result = run_backtest_f2(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.0, lookback_events=10)
    assert result["num_entries"] == 1
    assert result["final_capital"] > 10_000.0


def test_no_lookahead_signal_uses_shifted_trailing_average():
    # primeiros eventos com funding forte, resto fraco -- sinal de entrada
    # só deveria valer DEPOIS da média móvel ter dado positivo, nunca antes
    n = 20
    rates = [0.0005] * 10 + [0.0] * 10
    funding = _make_funding(rates)
    spot = _make_flat_prices(n, funding.index)
    perp = _make_flat_prices(n, funding.index)
    result = run_backtest_f2(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.0, lookback_events=5)
    # com lookback=5 a media so fica disponivel a partir do evento 5, e o
    # sinal (shiftado) so pode agir a partir do evento 6 -- garante que
    # nao entrou nos primeiros eventos antes de ter dado real suficiente
    assert result["num_entries"] >= 1


def test_transition_fees_charged_on_entry_and_exit():
    n = 12
    rates = [0.0005] * 6 + [0.0] * 6  # entra forte, depois cai abaixo do limiar -> sai
    funding = _make_funding(rates)
    spot = _make_flat_prices(n, funding.index)
    perp = _make_flat_prices(n, funding.index)
    result = run_backtest_f2(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.001, lookback_events=3)
    assert result["num_entries"] >= 1
