import numpy as np
import pandas as pd

from tradebot.backtest_f1 import run_backtest_f1


def _make_funding(rates, seed=1, freq_hours=8):
    n = len(rates)
    idx = pd.date_range("2023-01-01", periods=n, freq=f"{freq_hours}h")
    return pd.DataFrame({"funding_rate": rates, "mark_price": [100.0] * n}, index=idx)


def test_positive_funding_grows_capital():
    funding = _make_funding([0.0005] * 50)  # sempre positivo
    result = run_backtest_f1(funding, starting_cash=10_000.0, entry_fee_rate=0.0)
    assert result["final_capital"] > 10_000.0
    assert result["positive_events"] == 50
    assert result["negative_events"] == 0


def test_negative_funding_shrinks_capital():
    funding = _make_funding([-0.0005] * 50)  # sempre negativo
    result = run_backtest_f1(funding, starting_cash=10_000.0, entry_fee_rate=0.0)
    assert result["final_capital"] < 10_000.0
    assert result["negative_events"] == 50


def test_zero_funding_keeps_capital_flat_ignoring_fees():
    funding = _make_funding([0.0] * 20)
    result = run_backtest_f1(funding, starting_cash=10_000.0, entry_fee_rate=0.0)
    assert result["final_capital"] == 10_000.0


def test_entry_fee_reduces_starting_capital():
    funding = _make_funding([0.0] * 5)
    result = run_backtest_f1(funding, starting_cash=10_000.0, entry_fee_rate=0.001)
    # duas pernas, 0.1% cada -> 0.2% de custo de entrada
    assert result["final_capital"] == 10_000.0 * (1 - 2 * 0.001)


def test_positive_rate_pct_computed_correctly():
    # o evento com taxa exatamente 0.0 não conta nem como positivo nem
    # como negativo -- só entra no denominador dos que têm sinal definido
    funding = _make_funding([0.0005, 0.0005, -0.0003, 0.0])
    result = run_backtest_f1(funding, starting_cash=10_000.0, entry_fee_rate=0.0)
    assert result["positive_events"] == 2
    assert result["negative_events"] == 1
    assert result["num_funding_events"] == 3
    assert round(result["positive_rate_pct"], 2) == round(2 / 3 * 100, 2)


def test_equity_curve_has_one_more_point_than_funding_events():
    funding = _make_funding([0.0001] * 10)
    result = run_backtest_f1(funding, starting_cash=10_000.0)
    assert len(result["equity_curve"]) == len(funding) + 1
