import numpy as np
import pandas as pd

from tradebot.backtest import run_backtest
from tradebot.strategy import StrategyConfig
from tradebot.walkforward import WalkForwardResult, generate_windows, print_walk_forward_report


def test_generate_windows_splits_into_expected_number_of_chunks():
    windows = generate_windows("2012-01-01", "2024-01-01", window_years=2.0)
    assert len(windows) == 6
    assert windows[0] == ("2012-01-01", "2014-01-01")
    assert windows[-1] == ("2022-01-01", "2024-01-01")


def test_generate_windows_windows_are_contiguous_and_non_overlapping():
    windows = generate_windows("2010-01-01", "2020-01-01", window_years=3.0)
    for (start1, end1), (start2, end2) in zip(windows, windows[1:]):
        assert end1 == start2  # próxima janela começa exatamente onde a anterior terminou


def test_generate_windows_drops_small_residual_window():
    # sobra só ~45 dias depois de duas janelas de 2 anos -> descarta (< 90 dias)
    windows = generate_windows("2012-01-01", "2016-02-15", window_years=2.0, min_window_days=90)
    assert windows == [("2012-01-01", "2014-01-01"), ("2014-01-01", "2016-01-01")]


def test_generate_windows_keeps_residual_window_above_threshold():
    # sobra ~5 meses (> 90 dias) -> mantém como janela final mais curta
    windows = generate_windows("2012-01-01", "2016-06-01", window_years=2.0, min_window_days=90)
    assert windows == [
        ("2012-01-01", "2014-01-01"),
        ("2014-01-01", "2016-01-01"),
        ("2016-01-01", "2016-06-01"),
    ]


def test_generate_windows_empty_range_returns_empty_list():
    assert generate_windows("2020-01-01", "2020-01-01", window_years=2.0) == []


def _fake_df(seed, drift, n=500, start="2012-01-01"):
    rng = np.random.default_rng(seed)
    prices = 100 + np.cumsum(rng.normal(drift, 1.0, n))
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.01, "low": prices * 0.99, "close": prices, "volume": 1000}, index=idx
    )


def test_print_walk_forward_report_runs_without_crashing(capsys):
    cfg = StrategyConfig()
    window_results = {
        "2012-01-01 a 2014-01-01": {
            "A": run_backtest(_fake_df(1, 0.05, start="2012-01-01"), "A", cfg),
            "B": run_backtest(_fake_df(2, -0.02, start="2012-01-01"), "B", cfg),
        },
        "2014-01-01 a 2016-01-01": {
            "A": run_backtest(_fake_df(3, 0.02, start="2014-01-01"), "A", cfg),
            "B": run_backtest(_fake_df(4, 0.01, start="2014-01-01"), "B", cfg),
        },
    }
    wf = WalkForwardResult(windows=[("2012-01-01", "2014-01-01"), ("2014-01-01", "2016-01-01")], window_results=window_results)
    print_walk_forward_report(wf)
    out = capsys.readouterr().out
    assert "WALK-FORWARD" in out
    assert "Consistência entre 2 janelas" in out
    assert "Agregado geral" in out


def test_print_walk_forward_report_handles_no_windows(capsys):
    print_walk_forward_report(WalkForwardResult(windows=[], window_results={}))
    out = capsys.readouterr().out
    assert "Nenhuma janela" in out
