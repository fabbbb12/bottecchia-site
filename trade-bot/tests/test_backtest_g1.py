import pandas as pd

from tradebot.backtest_g1 import ENTRY_IBS_THRESHOLD, EXIT_IBS_THRESHOLD, generate_g1_signals
from tradebot.indicators import ibs


def test_ibs_zero_when_close_at_low():
    s = ibs(pd.Series([10.0]), pd.Series([8.0]), pd.Series([8.0]))
    assert s.iloc[0] == 0.0


def test_ibs_one_when_close_at_high():
    s = ibs(pd.Series([10.0]), pd.Series([8.0]), pd.Series([10.0]))
    assert s.iloc[0] == 1.0


def test_ibs_handles_zero_range_without_crash():
    s = ibs(pd.Series([10.0]), pd.Series([10.0]), pd.Series([10.0]))
    assert s.isna().all() or (s.iloc[0] >= 0 and s.iloc[0] <= 1)


def _make_df(closes, highs=None, lows=None):
    n = len(closes)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    highs = highs or [c * 1.02 for c in closes]
    lows = lows or [c * 0.98 for c in closes]
    return pd.DataFrame({"open": closes, "high": highs, "low": lows, "close": closes, "volume": [1] * n}, index=idx)


def test_no_buy_signal_below_trend_sma():
    # preco em queda constante, sempre abaixo da propria SMA200 -> nunca compra
    closes = [100 - i * 0.5 for i in range(250)]
    df = _make_df(closes, lows=[c * 0.90 for c in closes])  # IBS baixo o tempo todo
    signals = generate_g1_signals(df)
    assert not (signals["action"] == "BUY").any()


def test_buy_signal_when_uptrend_and_low_ibs():
    closes = [100 + i * 0.3 for i in range(250)]  # tendencia de alta sustentada
    highs = [c * 1.20 for c in closes]  # faixa do dia larga, fechamento perto da minima -> IBS baixo
    lows = [c * 0.99 for c in closes]
    df = _make_df(closes, highs=highs, lows=lows)
    signals = generate_g1_signals(df)
    assert (signals["action"] == "BUY").any()
