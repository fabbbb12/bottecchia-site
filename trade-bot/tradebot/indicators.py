"""Indicadores técnicos calculados sobre uma série de preços de fechamento."""

import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period, min_periods=period).mean()


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    result = 100 - (100 / (1 + rs))
    return result.where(avg_loss != 0, 100.0)


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "histogram": histogram}
    )


def bollinger_bands(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    mid = sma(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame({"upper": upper, "mid": mid, "lower": lower})


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range: mede a volatilidade recente (em unidades de
    preço, não em %), usada para adaptar stops à volatilidade de cada
    ativo em vez de usar a mesma % fixa para todos."""
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def fibonacci_levels(high: pd.Series, low: pd.Series, period: int = 50) -> pd.DataFrame:
    """Níveis de retração de Fibonacci calculados sobre a máxima e a mínima
    dos últimos `period` candles (o "swing" recente). Convenção: retração
    medida a partir da máxima do swing em direção à mínima — a leitura
    padrão para um recuo (pullback) dentro de uma tendência de alta."""
    swing_high = high.rolling(window=period, min_periods=period).max()
    swing_low = low.rolling(window=period, min_periods=period).min()
    swing_range = swing_high - swing_low

    out = pd.DataFrame(index=high.index)
    out["swing_high"] = swing_high
    out["swing_low"] = swing_low
    for pct, suffix in [(0.236, "236"), (0.382, "382"), (0.5, "500"), (0.618, "618"), (0.786, "786")]:
        out[f"fib_{suffix}"] = swing_high - swing_range * pct
    return out
