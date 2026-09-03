import numpy as np
import pandas as pd

from tradebot import indicators as ind
from tradebot.backtest import run_backtest
from tradebot.backtest_v6 import RVOL_THRESHOLD, run_backtest_v6
from tradebot.strategy import StrategyConfig


def test_relative_volume_above_average():
    # 20 dias anteriores com volume 100, dia atual com volume 300
    volume = pd.Series([100.0] * 20 + [300.0])
    rvol = ind.relative_volume(volume, period=20)
    assert round(rvol.iloc[-1], 2) == 3.0  # 300 / média dos 20 dias anteriores (100) = 3x


def test_relative_volume_nan_before_period():
    volume = pd.Series(np.full(15, 100.0))
    rvol = ind.relative_volume(volume, period=20)
    assert rvol.isna().all()


def test_relative_volume_handles_zero_average():
    volume = pd.Series([0.0] * 20 + [50.0])
    rvol = ind.relative_volume(volume, period=20)
    assert pd.isna(rvol.iloc[-1])


def test_relative_volume_excludes_current_day_from_average():
    # se o dia atual entrasse na própria média, o rvol seria diluído (< 3.0)
    volume = pd.Series([100.0] * 20 + [300.0])
    rvol = ind.relative_volume(volume, period=20)
    assert rvol.iloc[-1] == 3.0


def _uptrend_with_pullbacks(n=400, seed=1, volume=None):
    rng = np.random.default_rng(seed)
    trend = np.linspace(0, 50, n)
    pullback = np.sin(np.linspace(0, 8 * np.pi, n)) * 8
    noise = rng.normal(0, 2.0, n)
    prices = 100 + trend + pullback + noise
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    if volume is None:
        volume = np.full(n, 1000.0)
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.01, "low": prices * 0.99, "close": prices, "volume": volume}, index=idx
    )


def test_v6_never_trades_more_than_v1():
    """A V6 só recusa compras, nunca adiciona -> nunca deve operar mais que a V1."""
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    v1 = run_backtest(df, "TEST", cfg)
    v6 = run_backtest_v6(df, "TEST", cfg)
    assert v6.metrics["num_trades"] <= v1.metrics["num_trades"]


def test_v6_skips_buy_when_volume_flat():
    """Volume constante (rvol sempre ~1.0, abaixo do limiar de 1.5) -> a V6
    nunca deveria comprar, mesmo que a V1 compre."""
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks(volume=np.full(400, 1000.0))
    v1 = run_backtest(df, "TEST", cfg)
    v6 = run_backtest_v6(df, "TEST", cfg)
    assert v1.final_summary["num_fills"] > 0  # a V1 de fato comprou em algum momento
    assert v6.final_summary["num_fills"] == 0


def test_v6_buys_when_volume_spikes_at_signal():
    """Quando o volume dispara bem acima da média exatamente nos dias em que
    a V1 compraria, a V6 deve aceitar essas mesmas compras."""
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    v1 = run_backtest(df, "TEST", cfg)
    # descobre os dias em que a V1 comprou e infla o volume desses dias
    from tradebot.strategy import apply_risk_management, generate_signals
    from tradebot.portfolio import Portfolio

    signals = generate_signals(df, cfg)
    portfolio = Portfolio(10_000.0)
    volume = np.full(len(df), 1000.0)
    for i, (timestamp, row) in enumerate(signals.iterrows()):
        price = float(row["close"])
        pos = portfolio.position("TEST")
        if pos.quantity > 0:
            pos.peak_price = max(pos.peak_price, price)
        action = apply_risk_management(
            row["action"], pos.quantity, pos.avg_price, pos.peak_price, price, row["atr"], cfg
        )
        if action == "BUY":
            volume[i] = 5000.0  # bem acima da média -> rvol alto
            fill = portfolio.buy(timestamp, "TEST", price, 0.5)
            if fill:
                pos.peak_price = fill.price
        elif action == "SELL":
            portfolio.sell(timestamp, "TEST", price, 1.0)

    df_boosted = df.copy()
    df_boosted["volume"] = volume
    v6 = run_backtest_v6(df_boosted, "TEST", cfg)
    assert v6.final_summary["num_fills"] == v1.final_summary["num_fills"]


def test_run_backtest_v6_does_not_crash_and_produces_valid_result():
    cfg = StrategyConfig()
    df = _uptrend_with_pullbacks()
    result = run_backtest_v6(df, "TEST", cfg)
    assert "rvol" in result.signals.columns
    assert result.final_summary["cash"] >= 0
    assert len(result.equity_curve) == len(df)
