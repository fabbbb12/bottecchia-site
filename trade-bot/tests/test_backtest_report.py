import pandas as pd

from tradebot.backtest import BacktestResult, _max_drawdown_pct, print_report


def test_max_drawdown_pct_basic():
    equity = pd.Series([100.0, 120.0, 90.0, 110.0])
    # cai de 120 para 90 -> -25%
    assert round(_max_drawdown_pct(equity), 2) == -25.0


def test_max_drawdown_pct_empty_series():
    assert _max_drawdown_pct(pd.Series([], dtype=float)) == 0.0


def _make_result(equity_values, benchmark_values):
    idx = pd.date_range("2024-01-01", periods=len(equity_values), freq="D")
    equity = pd.Series(equity_values, index=idx, name="equity")
    benchmark = pd.Series(benchmark_values, index=idx, name="benchmark")
    signals = pd.DataFrame({"close": benchmark_values}, index=idx)
    summary = {
        "cash": equity_values[-1],
        "equity": equity_values[-1],
        "pnl": equity_values[-1] - equity_values[0],
        "pnl_pct": (equity_values[-1] - equity_values[0]) / equity_values[0] * 100,
        "positions": {},
        "num_fills": 0,
    }
    return BacktestResult(equity, benchmark, signals, summary)


def test_print_report_flags_worse_drawdown_than_benchmark(capsys):
    # estratégia cai mais (pior) do que o buy-and-hold no pior momento
    result = _make_result([100, 120, 90, 110], [100, 120, 100, 130])
    print_report(result, "TEST")
    out = capsys.readouterr().out
    assert "teve queda pior" in out


def test_print_report_flags_better_drawdown_than_benchmark(capsys):
    # estratégia protege melhor: cai menos que o buy-and-hold no pior momento
    result = _make_result([100, 120, 100, 130], [100, 120, 90, 110])
    print_report(result, "TEST")
    out = capsys.readouterr().out
    assert "protegeu capital melhor" in out
