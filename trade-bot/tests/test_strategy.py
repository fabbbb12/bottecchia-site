import numpy as np
import pandas as pd

from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals


def _trending_df(n=100, start=100.0, step=0.5, noise=0.05, seed=1):
    rng = np.random.default_rng(seed)
    prices = start + np.cumsum(np.full(n, step) + rng.normal(0, noise, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({"close": prices}, index=idx)


def test_generate_signals_has_expected_columns():
    df = _trending_df()
    cfg = StrategyConfig()
    result = generate_signals(df, cfg)
    for col in ["sma_fast", "sma_slow", "rsi", "macd", "score", "action"]:
        assert col in result.columns


def test_generate_signals_actions_are_valid():
    df = _trending_df()
    cfg = StrategyConfig()
    result = generate_signals(df, cfg)
    assert set(result["action"].unique()).issubset({"BUY", "SELL", "HOLD"})


def test_uptrend_favors_buy_over_sell():
    df = _trending_df(step=1.0)
    cfg = StrategyConfig()
    result = generate_signals(df, cfg).dropna(subset=["sma_slow"])
    counts = result["action"].value_counts()
    assert counts.get("BUY", 0) >= counts.get("SELL", 0)


def test_downtrend_favors_sell_over_buy():
    df = _trending_df(step=-1.0)
    cfg = StrategyConfig()
    result = generate_signals(df, cfg).dropna(subset=["sma_slow"])
    counts = result["action"].value_counts()
    assert counts.get("SELL", 0) >= counts.get("BUY", 0)


def test_hard_stop_loss_forces_sell():
    cfg = StrategyConfig(stop_loss_pct=0.06)
    # preço caiu 10% desde a entrada -> stop-loss deve forçar venda mesmo com HOLD
    action = apply_risk_management("HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=100.0, current_price=90.0, cfg=cfg)
    assert action == "SELL"


def test_trailing_stop_lets_small_gains_run():
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_stop_pct=0.10)
    # só 5% de lucro (abaixo do gatilho de ativação) -> trailing não deve interferir
    action = apply_risk_management("HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=105.0, current_price=103.0, cfg=cfg)
    assert action == "HOLD"


def test_trailing_stop_locks_in_large_gain_on_pullback():
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_stop_pct=0.10)
    # posição chegou a +50%, depois recuou mais de 10% do pico -> trava o lucro
    action = apply_risk_management("HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=150.0, current_price=130.0, cfg=cfg)
    assert action == "SELL"


def test_trailing_stop_does_not_trigger_on_small_pullback_after_big_gain():
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_stop_pct=0.10)
    # posição chegou a +50%, recuou só 5% do pico -> ainda dentro da margem, deixa correr
    action = apply_risk_management("HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=150.0, current_price=142.5, cfg=cfg)
    assert action == "HOLD"


def test_no_open_position_leaves_action_untouched():
    cfg = StrategyConfig()
    action = apply_risk_management("BUY", position_qty=0, position_avg_price=0.0, position_peak_price=0.0, current_price=100.0, cfg=cfg)
    assert action == "BUY"
