"""Estratégia de análise: combina múltiplos indicadores em um sinal único.

Cada indicador vota em COMPRA (+1), VENDA (-1) ou NEUTRO (0). Os votos são
somados com pesos; o resultado é comparado a um limiar para decidir a ação
final. Isso evita depender de um único indicador (que gera muitos falsos
sinais isolado) e é fácil de ajustar via `StrategyConfig`.
"""

from dataclasses import dataclass, field

import pandas as pd

from tradebot import indicators as ind


@dataclass
class StrategyConfig:
    sma_fast: int = 20
    sma_slow: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    weights: dict = field(
        default_factory=lambda: {"trend": 1.0, "rsi": 1.0, "macd": 1.0, "bollinger": 0.5}
    )
    buy_threshold: float = 1.5
    sell_threshold: float = -1.5


def compute_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Recebe um DataFrame com coluna 'close' e devolve um novo DataFrame
    com todas as colunas de indicadores anexadas."""
    out = df.copy()
    close = out["close"]

    out["sma_fast"] = ind.sma(close, cfg.sma_fast)
    out["sma_slow"] = ind.sma(close, cfg.sma_slow)
    out["rsi"] = ind.rsi(close, cfg.rsi_period)

    macd_df = ind.macd(close, cfg.macd_fast, cfg.macd_slow, cfg.macd_signal)
    out["macd"] = macd_df["macd"]
    out["macd_signal"] = macd_df["signal"]
    out["macd_hist"] = macd_df["histogram"]

    bb_df = ind.bollinger_bands(close, cfg.bb_period, cfg.bb_std)
    out["bb_upper"] = bb_df["upper"]
    out["bb_mid"] = bb_df["mid"]
    out["bb_lower"] = bb_df["lower"]

    return out


def _trend_vote(row: pd.Series) -> float:
    if pd.isna(row["sma_fast"]) or pd.isna(row["sma_slow"]):
        return 0.0
    return 1.0 if row["sma_fast"] > row["sma_slow"] else -1.0


def _rsi_vote(row: pd.Series, cfg: StrategyConfig) -> float:
    if pd.isna(row["rsi"]):
        return 0.0
    if row["rsi"] < cfg.rsi_oversold:
        return 1.0
    if row["rsi"] > cfg.rsi_overbought:
        return -1.0
    return 0.0


def _macd_vote(row: pd.Series) -> float:
    if pd.isna(row["macd_hist"]):
        return 0.0
    if row["macd_hist"] > 0:
        return 1.0
    if row["macd_hist"] < 0:
        return -1.0
    return 0.0


def _bollinger_vote(row: pd.Series) -> float:
    if pd.isna(row["bb_lower"]) or pd.isna(row["bb_upper"]):
        return 0.0
    if row["close"] <= row["bb_lower"]:
        return 1.0
    if row["close"] >= row["bb_upper"]:
        return -1.0
    return 0.0


def score_row(row: pd.Series, cfg: StrategyConfig) -> float:
    weights = cfg.weights
    return (
        weights.get("trend", 0.0) * _trend_vote(row)
        + weights.get("rsi", 0.0) * _rsi_vote(row, cfg)
        + weights.get("macd", 0.0) * _macd_vote(row)
        + weights.get("bollinger", 0.0) * _bollinger_vote(row)
    )


def decide_action(score: float, cfg: StrategyConfig) -> str:
    if score >= cfg.buy_threshold:
        return "BUY"
    if score <= cfg.sell_threshold:
        return "SELL"
    return "HOLD"


def generate_signals(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Recebe OHLCV, devolve DataFrame com colunas de indicadores + 'score' + 'action'."""
    enriched = compute_indicators(df, cfg)
    enriched["score"] = enriched.apply(lambda row: score_row(row, cfg), axis=1)
    enriched["action"] = enriched["score"].apply(lambda s: decide_action(s, cfg))
    return enriched
