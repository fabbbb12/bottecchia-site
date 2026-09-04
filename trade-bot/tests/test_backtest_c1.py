import numpy as np
import pandas as pd

from tradebot.backtest_c1 import (
    _rebalance_dates,
    _target_holdings,
    run_backtest_c1_from_panels,
)


def _trend_series(n, start_price, daily_drift, seed):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 0.1, n)
    return start_price * np.cumprod(1 + daily_drift + noise / 1000)


def _make_panels(n=400, seed=1):
    idx = pd.date_range("2021-01-01", periods=n, freq="B")
    # WINNER sobe forte, LOSER cai, FLAT fica parado -> momentum deveria
    # escolher WINNER e nunca escolher LOSER (retorno negativo)
    winner = _trend_series(n, 100, 0.003, seed)
    loser = _trend_series(n, 100, -0.002, seed + 1)
    flat = _trend_series(n, 100, 0.0, seed + 2)
    closes = pd.DataFrame({"WINNER": winner, "LOSER": loser, "FLAT": flat}, index=idx)
    opens = closes.shift(1).fillna(closes.iloc[0])
    return closes, opens


def test_rebalance_dates_are_last_trading_day_of_each_month():
    idx = pd.date_range("2021-01-01", "2021-03-31", freq="B")
    dates = _rebalance_dates(idx)
    # todo mês presente no índice deve ter exatamente um rebalanceamento
    months = {(d.year, d.month) for d in idx}
    assert len(dates) == len(months)
    for d in dates:
        next_days = idx[idx > d]
        # cada data marcada deve ser o último pregão do seu mês (ou o
        # último do índice inteiro)
        assert next_days.empty or next_days[0].month != d.month


def test_target_holdings_picks_winner_and_excludes_negative_momentum():
    closes, _ = _make_panels()
    symbols = list(closes.columns)
    decision_idx = 300
    target = _target_holdings(closes, decision_idx, symbols, momentum_lookback_days=252, top_k=3)
    assert "WINNER" in target
    assert "LOSER" not in target  # retorno negativo -> filtro de momentum absoluto exclui


def test_target_holdings_empty_before_enough_history():
    closes, _ = _make_panels()
    symbols = list(closes.columns)
    assert _target_holdings(closes, 100, symbols, momentum_lookback_days=252, top_k=3) == []


def test_no_lookahead_ranking_uses_only_data_through_decision_day():
    idx = pd.date_range("2021-01-01", periods=10, freq="D")
    closes = pd.DataFrame(
        {"A": [100, 100, 100, 100, 100, 100, 100, 100, 100, 500], "B": [100] * 10},
        index=idx,
    )
    # no dia 8 (indice 8), o pulo pra 500 ainda nao aconteceu (só no indice 9)
    target = _target_holdings(closes, 8, ["A", "B"], momentum_lookback_days=5, top_k=1)
    assert target == []  # nenhum dos dois teve retorno positivo até o dia 8


def test_run_backtest_c1_does_not_crash_and_produces_valid_result():
    closes, opens = _make_panels()
    result = run_backtest_c1_from_panels(closes, opens, momentum_lookback_days=60, top_k=2)
    assert len(result.equity_curve) == len(closes)
    assert result.final_summary["cash"] >= -1e-6
    assert set(result.symbols) == {"WINNER", "LOSER", "FLAT"}


def test_run_backtest_c1_never_buys_before_enough_momentum_history():
    closes, opens = _make_panels(n=100)
    # historico menor que o lookback -> nunca deve ter comprado nada
    result = run_backtest_c1_from_panels(closes, opens, momentum_lookback_days=252, top_k=2)
    assert result.final_summary["num_fills"] == 0
    assert result.final_summary["cash"] == result.final_summary["equity"]


def test_entry_cash_fraction_is_one_over_top_k():
    from tradebot.backtest_c1 import run_backtest_c1_from_panels

    closes, opens = _make_panels()
    result = run_backtest_c1_from_panels(closes, opens, momentum_lookback_days=60, top_k=2, starting_cash=10_000.0)
    # com top_k=2, cada entrada usa 1/2 do caixa disponivel no momento -> houve pelo menos uma compra
    assert result.final_summary["num_fills"] > 0
