import pandas as pd

from tradebot.backtest import (
    BacktestResult,
    _max_drawdown_pct,
    _return_metrics,
    print_aggregate_comparison,
    print_report,
)


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
    metrics = _return_metrics(equity)
    metrics.update(
        {
            "max_drawdown_pct": _max_drawdown_pct(equity),
            "profit_factor": 0.0,
            "num_trades": 0,
            "time_exposed_pct": 100.0,
            "turnover": 0.0,
            "total_fees": 0.0,
        }
    )
    benchmark_metrics = _return_metrics(benchmark)
    benchmark_metrics["max_drawdown_pct"] = _max_drawdown_pct(benchmark)
    return BacktestResult(equity, benchmark, signals, summary, metrics, benchmark_metrics)


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


def test_print_aggregate_comparison_win_count_ignores_average_distortion(capsys):
    # A: estratégia perde feio (arrasta a média pra baixo), mas B e C ela vence
    # por pouco -> a média pode enganar, a contagem de vitórias não.
    results = {
        "A": _make_result([100, 100, 50, 60], [100, 200, 250, 300]),
        "B": _make_result([100, 105, 108, 110], [100, 102, 103, 104]),
        "C": _make_result([100, 103, 105, 107], [100, 101, 102, 103]),
    }
    print_aggregate_comparison(results)
    out = capsys.readouterr().out
    assert "2/3" in out  # vence em Retorno em 2 dos 3 ativos (B e C, perde em A)


def test_print_aggregate_comparison_reports_median_separately_from_mean(capsys):
    results = {
        "A": _make_result([100, 120, 90, 110], [100, 105, 108, 112]),
        "B": _make_result([100, 110, 120, 130], [100, 101, 102, 103]),
    }
    print_aggregate_comparison(results)
    out = capsys.readouterr().out
    assert "Med. Estr" in out and "Média Estr" in out
