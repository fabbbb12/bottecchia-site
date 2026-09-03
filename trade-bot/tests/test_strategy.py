import numpy as np
import pandas as pd

from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals


def _trending_df(n=100, start=100.0, step=0.5, noise=0.05, seed=1):
    rng = np.random.default_rng(seed)
    prices = start + np.cumsum(np.full(n, step) + rng.normal(0, noise, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.005, "low": prices * 0.995, "close": prices}, index=idx
    )


def test_generate_signals_has_expected_columns():
    df = _trending_df()
    cfg = StrategyConfig()
    result = generate_signals(df, cfg)
    for col in ["sma_fast", "sma_slow", "rsi", "macd", "atr", "score", "action"]:
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
    action = apply_risk_management(
        "HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=100.0,
        current_price=90.0, atr=2.0, cfg=cfg,
    )
    assert action == "SELL"


def test_trailing_stop_lets_small_gains_run():
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_atr_mult=3.0)
    # só 5% de lucro (abaixo do gatilho de ativação) -> trailing não deve interferir
    action = apply_risk_management(
        "HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=105.0,
        current_price=103.0, atr=2.0, cfg=cfg,
    )
    assert action == "HOLD"


def test_trailing_stop_locks_in_large_gain_on_pullback():
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_atr_mult=3.0)
    # posição chegou a +50% (peak=150), stop = peak - 3*atr = 150 - 15 = 135
    # preço recuou para 130, abaixo do stop -> trava o lucro
    action = apply_risk_management(
        "HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=150.0,
        current_price=130.0, atr=5.0, cfg=cfg,
    )
    assert action == "SELL"


def test_trailing_stop_does_not_trigger_on_small_pullback_after_big_gain():
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_atr_mult=3.0)
    # mesmo stop em 135, mas preço só recuou para 142.5 -> ainda acima do stop
    action = apply_risk_management(
        "HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=150.0,
        current_price=142.5, atr=5.0, cfg=cfg,
    )
    assert action == "HOLD"


def test_trailing_stop_widens_with_higher_atr():
    # mesmo cenário de queda, mas ativo mais volátil (ATR maior) dá mais espaço
    # e não deve ser vendido pela mesma oscilação que venderia um ativo calmo
    cfg = StrategyConfig(trailing_activate_pct=0.08, trailing_atr_mult=3.0)
    action = apply_risk_management(
        "HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=150.0,
        current_price=130.0, atr=15.0, cfg=cfg,
    )
    assert action == "HOLD"


def test_no_open_position_leaves_action_untouched():
    cfg = StrategyConfig()
    action = apply_risk_management(
        "BUY", position_qty=0, position_avg_price=0.0, position_peak_price=0.0,
        current_price=100.0, atr=1.0, cfg=cfg,
    )
    assert action == "BUY"


def test_missing_atr_falls_back_to_stop_loss_pct():
    cfg = StrategyConfig(trailing_activate_pct=0.08, stop_loss_pct=0.06)
    # atr NaN (ex: início da série, sem histórico suficiente) -> usa stop_loss_pct como distância
    action = apply_risk_management(
        "HOLD", position_qty=10, position_avg_price=100.0, position_peak_price=150.0,
        current_price=130.0, atr=float("nan"), cfg=cfg,
    )
    assert action == "SELL"  # 130 <= 150 * (1 - 0.06) = 141
