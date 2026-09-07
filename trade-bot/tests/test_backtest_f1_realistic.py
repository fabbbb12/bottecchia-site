import pandas as pd

from tradebot.backtest_f1_realistic import run_backtest_f1_realistic


def _make_funding(rates, freq_hours=8):
    n = len(rates)
    idx = pd.date_range("2023-01-01", periods=n, freq=f"{freq_hours}h")
    return pd.DataFrame({"funding_rate": rates, "mark_price": [100.0] * n}, index=idx)


def _make_prices(prices, idx):
    return pd.DataFrame({"close": prices}, index=idx)


def test_matches_pure_funding_when_basis_constant():
    funding = _make_funding([0.0005] * 10)
    spot = _make_prices([100.0] * 10, funding.index)
    perp = _make_prices([100.0] * 10, funding.index)  # basis sempre zero -> sem efeito extra
    result = run_backtest_f1_realistic(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.0)
    expected = 10_000.0 * (1.0005) ** 10
    assert round(result["final_capital"], 4) == round(expected, 4)


def test_widening_basis_hurts_short_perp_leg():
    funding = _make_funding([0.0] * 3)
    spot = _make_prices([100.0, 100.0, 100.0], funding.index)  # à vista parado
    perp = _make_prices([100.0, 105.0, 110.0], funding.index)  # perpétuo sobe MAIS que o à vista
    result = run_backtest_f1_realistic(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.0)
    # basis abrindo contra a perna vendida (sem funding compensando) -> perde dinheiro
    assert result["final_capital"] < 10_000.0


def test_narrowing_basis_helps_short_perp_leg():
    funding = _make_funding([0.0] * 3)
    spot = _make_prices([100.0, 100.0, 100.0], funding.index)
    perp = _make_prices([110.0, 105.0, 100.0], funding.index)  # perpétuo converge de volta pro à vista
    result = run_backtest_f1_realistic(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.0)
    assert result["final_capital"] > 10_000.0


def test_entry_fee_applied_once():
    funding = _make_funding([0.0] * 3)
    spot = _make_prices([100.0] * 3, funding.index)
    perp = _make_prices([100.0] * 3, funding.index)
    result = run_backtest_f1_realistic(funding, spot, perp, starting_cash=10_000.0, entry_fee_rate=0.001)
    assert result["final_capital"] == 10_000.0 * (1 - 2 * 0.001)
