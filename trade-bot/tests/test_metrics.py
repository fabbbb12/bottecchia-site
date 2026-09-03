from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from tradebot.backtest import _return_metrics
from tradebot.portfolio import Fill, compute_round_trip_pnls, profit_factor


def _equity_series(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def test_return_metrics_positive_trend_has_positive_sharpe_and_cagr():
    rng = np.random.default_rng(1)
    # tendência de alta com um pouco de ruído -> existe algum drawdown, não fica em 0/inf
    values = 100 + np.arange(300) + rng.normal(0, 0.3, 300)
    metrics = _return_metrics(_equity_series(values))
    assert metrics["cagr_pct"] > 0
    assert metrics["sharpe"] > 0
    assert metrics["calmar"] > 0


def test_return_metrics_no_drawdown_gives_infinite_calmar():
    values = [100 + i for i in range(300)]  # sobe sempre, nunca cai do pico
    metrics = _return_metrics(_equity_series(values))
    assert metrics["calmar"] == float("inf")


def test_return_metrics_downtrend_has_negative_sharpe_and_cagr():
    values = [400 - i for i in range(300)]
    metrics = _return_metrics(_equity_series(values))
    assert metrics["cagr_pct"] < 0
    assert metrics["sharpe"] < 0


def test_return_metrics_flat_line_is_all_zero():
    values = [100.0] * 50
    metrics = _return_metrics(_equity_series(values))
    assert metrics["sharpe"] == 0.0
    assert metrics["sortino"] == 0.0


def test_return_metrics_short_series_does_not_crash():
    metrics = _return_metrics(_equity_series([100.0]))
    assert metrics == {"cagr_pct": 0.0, "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0}


def test_sortino_is_infinite_when_there_is_no_downside():
    rng = np.random.default_rng(0)
    values = 100 + np.cumsum(np.abs(rng.normal(1, 1, 200)))  # sempre sobe ou fica igual
    metrics = _return_metrics(_equity_series(values))
    assert metrics["sortino"] == float("inf")


def test_sortino_ignores_upside_volatility():
    # mistura pequenas quedas ocasionais com bastante volatilidade positiva ->
    # sortino não deve ser penalizado pela volatilidade "boa" como o sharpe é
    rng = np.random.default_rng(0)
    steps = rng.normal(1.5, 1.0, 200)
    steps[::10] -= 3.0  # queda ocasional a cada 10 dias
    values = 100 + np.cumsum(steps)
    metrics = _return_metrics(_equity_series(values))
    assert metrics["sortino"] >= metrics["sharpe"]


def _fill(side, qty, price, fee=0.0, ts=None):
    return Fill(ts or datetime(2024, 1, 1), "TEST", side, qty, price, fee)


def test_compute_round_trip_pnls_single_trade():
    fills = [_fill("BUY", 10, 100.0), _fill("SELL", 10, 120.0)]
    trades = compute_round_trip_pnls(fills)
    assert trades == [200.0]  # (10*120) - (10*100)


def test_compute_round_trip_pnls_multiple_buys_before_sell():
    fills = [_fill("BUY", 5, 100.0), _fill("BUY", 5, 110.0), _fill("SELL", 10, 130.0)]
    trades = compute_round_trip_pnls(fills)
    # custo: 5*100 + 5*110 = 1050; venda: 10*130 = 1300 -> lucro 250
    assert trades == [250.0]


def test_compute_round_trip_pnls_accounts_for_fees():
    fills = [_fill("BUY", 10, 100.0, fee=5.0), _fill("SELL", 10, 120.0, fee=6.0)]
    trades = compute_round_trip_pnls(fills)
    # (1200 - 6) - (1000 + 5) = 189
    assert trades == [189.0]


def test_profit_factor_no_losses_is_infinite():
    assert profit_factor([100.0, 50.0]) == float("inf")


def test_profit_factor_no_trades_is_zero():
    assert profit_factor([]) == 0.0


def test_profit_factor_mixed_trades():
    # ganhos 150, perdas 50 -> profit factor 3.0
    assert profit_factor([100.0, 50.0, -50.0]) == 3.0
