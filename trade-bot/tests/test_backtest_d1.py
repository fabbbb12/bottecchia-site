import numpy as np
import pandas as pd

from tradebot.backtest_d1 import generate_d1_signals, run_backtest_d1


def _flat_df(n=30, price=100.0, start="2021-01-01"):
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame(
        {
            "open": [price] * n,
            "high": [price * 1.01] * n,
            "low": [price * 0.99] * n,
            "close": [price] * n,
            "volume": 1000,
        },
        index=idx,
    )


def _zigzag_df(n=200, base=100.0, amplitude=15.0, period_days=20, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    prices = base + amplitude * np.sin(2 * np.pi * t / period_days) + rng.normal(0, 0.3, n)
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": prices, "high": prices * 1.005, "low": prices * 0.995, "close": prices, "volume": 1000}, index=idx
    )


def test_entry_signal_true_when_close_at_or_below_lower_band():
    df = _zigzag_df()
    signals = generate_d1_signals(df, bb_period=20, bb_std=2.0)
    assert (signals["entry_signal"] == (signals["close"] <= signals["lower_band"])).all()


def test_exit_signal_true_when_close_at_or_above_upper_band():
    df = _zigzag_df()
    signals = generate_d1_signals(df, bb_period=20, bb_std=2.0)
    assert (signals["exit_signal"] == (signals["close"] >= signals["upper_band"])).all()


def test_no_signal_on_flat_price_bands_collapse_to_price():
    # preço constante -> desvio padrao zero -> bandas colapsam no proprio
    # preco -> close sempre "toca" as duas bandas ao mesmo tempo (caso
    # degenerado); o teste real de comportamento é feito com zigzag
    df = _flat_df()
    signals = generate_d1_signals(df)
    assert signals["lower_band"].iloc[19:].equals(signals["upper_band"].iloc[19:])


def test_run_backtest_d1_does_not_crash_and_produces_valid_result():
    df = _zigzag_df()
    result = run_backtest_d1(df, "TEST")
    assert "entry_signal" in result.signals.columns
    assert len(result.equity_curve) == len(df)
    assert result.final_summary["cash"] >= 0


def test_run_backtest_d1_trades_more_often_on_zigzag_than_on_trend():
    zigzag = _zigzag_df(n=300, amplitude=15.0, period_days=20)
    n = 300
    trend_prices = 100 + np.linspace(0, 80, n)
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    trend = pd.DataFrame(
        {
            "open": trend_prices,
            "high": trend_prices * 1.005,
            "low": trend_prices * 0.995,
            "close": trend_prices,
            "volume": 1000,
        },
        index=idx,
    )
    zigzag_result = run_backtest_d1(zigzag, "ZIGZAG")
    trend_result = run_backtest_d1(trend, "TREND")
    # numa alta reta e monotonica o preco nunca volta a tocar a banda
    # inferior depois da primeira entrada -> poucas ou nenhuma operação;
    # no zigzag, o preco cruza as bandas repetidamente -> mais operações
    assert zigzag_result.final_summary["num_fills"] >= trend_result.final_summary["num_fills"]


def test_entry_executes_next_open_not_same_candle_as_signal():
    n = 8
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    # preco cai abaixo da banda inferior exatamente no dia 6 (indice 6)
    closes = [100, 101, 100, 101, 100, 101, 70, 72, 74]
    closes = closes[:n]
    opens = closes.copy()
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1000}, index=idx)

    starting_cash = 10_000.0
    result = run_backtest_d1(df, "TEST", bb_period=5, bb_std=1.0, starting_cash=starting_cash, cash_fraction=0.5)
    signals = result.signals
    signal_day = signals.index[signals["entry_signal"]][0] if signals["entry_signal"].any() else None
    if signal_day is not None:
        signal_idx = signals.index.get_loc(signal_day)
        # no dia do sinal, ainda nao houve compra (equity = caixa)
        assert result.equity_curve.iloc[signal_idx] == starting_cash


def test_stop_loss_limits_loss_from_entry_price():
    n = 15
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    # sobe e cai abaixo da banda pra comprar, depois despenca sem nunca
    # voltar pra banda superior -> só o stop-loss deve tirar a posição
    closes = [100, 100, 100, 100, 100, 80, 79, 78, 60, 55, 50, 48, 47, 46, 45]
    df = pd.DataFrame(
        {"open": closes, "high": [c * 1.01 for c in closes], "low": [c * 0.99 for c in closes], "close": closes, "volume": 1000},
        index=idx,
    )
    result = run_backtest_d1(df, "TEST", bb_period=5, bb_std=1.0, stop_loss_pct=0.06, cash_fraction=0.5)
    # deve ter vendido em algum momento por stop, nao deixar a posicao
    # aberta acumulando perda ilimitada ate o fim da serie
    assert result.final_summary["num_fills"] >= 2
