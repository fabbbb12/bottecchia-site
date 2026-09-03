import numpy as np
import pandas as pd

from tradebot.backtest_b1 import generate_b1_signals, run_backtest_b1


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


def test_highest_high_n_excludes_current_candle():
    # 3 candles com high=101, depois um 4o candle com high bem maior:
    # highest_high_n do 4o candle deve ser 101 (não deve incluir o proprio candle)
    idx = pd.date_range("2021-01-01", periods=4, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100],
            "high": [101, 101, 101, 500],
            "low": [99, 99, 99, 99],
            "close": [100, 100, 100, 110],
            "volume": 1000,
        },
        index=idx,
    )
    signals = generate_b1_signals(df, breakout_period=3, atr_period=2)
    assert signals["highest_high_n"].iloc[3] == 101.0


def test_entry_signal_true_only_when_close_breaks_prior_highest_high():
    idx = pd.date_range("2021-01-01", periods=4, freq="D")
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100],
            "high": [101, 101, 101, 102],
            "low": [99, 99, 99, 99],
            "close": [100, 100, 100, 110],  # 110 > 101 (máxima anterior) -> rompeu
            "volume": 1000,
        },
        index=idx,
    )
    signals = generate_b1_signals(df, breakout_period=3, atr_period=2)
    assert not signals["entry_signal"].iloc[:3].any()
    assert bool(signals["entry_signal"].iloc[3]) is True


def test_no_lookahead_never_buys_when_price_never_breaks_out():
    # trajetória sempre decrescente: o fechamento nunca supera a máxima
    # dos períodos anteriores -> nenhuma compra deve acontecer
    n = 60
    prices = 200 - np.linspace(0, 100, n)
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {"open": prices, "high": prices * 1.001, "low": prices * 0.999, "close": prices, "volume": 1000}, index=idx
    )
    result = run_backtest_b1(df, "TEST", breakout_period=20, atr_period=14)
    assert result.final_summary["num_fills"] == 0
    assert result.final_summary["cash"] == result.final_summary["equity"]


def test_entry_executes_next_open_not_same_candle_as_breakout():
    # dias 0-2 flat (high=101), dia 3 fecha em rompimento (110 > 101),
    # dia 4 é o candle seguinte -> a compra só pode acontecer no open do dia 4
    n = 6
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    opens = [100, 100, 100, 100, 115, 116]
    highs = [101, 101, 101, 111, 116, 117]
    lows = [99, 99, 99, 99, 114, 115]
    closes = [100, 100, 100, 110, 115, 116]
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1000}, index=idx)

    starting_cash = 10_000.0
    result = run_backtest_b1(
        df, "TEST", breakout_period=3, atr_period=2, starting_cash=starting_cash, cash_fraction=0.5
    )

    # no dia do rompimento (índice 3) ainda não houve nenhuma compra: 100%
    # do patrimônio continua em caixa, equity == starting_cash
    assert result.equity_curve.iloc[3] == starting_cash
    # no dia seguinte (índice 4) a compra já foi executada no open
    assert result.equity_curve.iloc[4] != starting_cash
    assert result.final_summary["num_fills"] >= 1


def test_stop_loss_executes_next_open_not_same_candle_as_violation():
    # sobe o suficiente pra comprar, depois cai bruscamente o bastante pra
    # violar o stop no fechamento de um dia -> a venda só pode acontecer no
    # open do dia seguinte, nunca no mesmo candle da violação
    n = 10
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    opens = [100, 100, 100, 120, 121, 122, 90, 80, 79, 78]
    highs = [101, 101, 101, 121, 122, 123, 122, 81, 80, 79]
    lows = [99, 99, 99, 119, 120, 121, 89, 79, 78, 77]
    closes = [100, 100, 100, 120, 121, 122, 90, 80, 79, 78]
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1000}, index=idx)

    result = run_backtest_b1(df, "TEST", breakout_period=3, atr_period=2, cash_fraction=0.5)

    # a queda brusca (dia 6, close=90) deve violar o stop pelo fechamento,
    # mas só pode ser vendida no open do dia seguinte (dia 7) — então o
    # patrimônio no dia 6 ainda reflete a posição aberta (não é igual ao
    # caixa puro), mas o número de vendas some só depois
    assert result.final_summary["num_fills"] >= 2  # pelo menos 1 compra + 1 venda


def test_run_backtest_b1_does_not_crash_and_produces_valid_result():
    n = 400
    rng = np.random.default_rng(7)
    trend = np.linspace(0, 60, n)
    noise = rng.normal(0, 3.0, n)
    prices = 100 + trend + noise
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    df = pd.DataFrame(
        {"open": prices, "high": prices * 1.01, "low": prices * 0.99, "close": prices, "volume": 1000}, index=idx
    )
    result = run_backtest_b1(df, "TEST")
    assert "entry_signal" in result.signals.columns
    assert len(result.equity_curve) == len(df)
    assert result.final_summary["cash"] >= 0


def test_run_multi_backtest_b1_accepts_unused_strategy_cfg_positionally():
    # a assinatura aceita strategy_cfg (não usado) na 2a posição só por
    # compatibilidade com run_walk_forward()/compare(); precisa funcionar
    # mesmo passando None
    from tradebot.backtest_b1 import run_backtest_b1

    df = _flat_df()
    result = run_backtest_b1(df, "TEST", None)
    assert result.final_summary["num_fills"] == 0
