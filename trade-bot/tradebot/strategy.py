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
    buy_threshold: float = 2.0
    sell_threshold: float = -2.0
    stop_loss_pct: float = 0.06
    # Em vez de vender sempre ao bater um alvo fixo de lucro (o que corta
    # tendências longas cedo demais), usa um stop móvel: só vende a posição
    # lucrativa quando o preço recuar a partir do maior preço atingido desde
    # a entrada, e só depois de já estar com pelo menos `trailing_activate_pct`
    # de lucro (evita apertar o stop logo na entrada). A distância do stop é
    # baseada no ATR (volatilidade recente do próprio ativo, "Chandelier
    # Exit") em vez de uma % fixa igual para todos — assim ações voláteis
    # (ex: NVDA) ganham mais espaço e não são vendidas por oscilação normal.
    atr_period: int = 14
    trailing_activate_pct: float = 0.08
    trailing_atr_mult: float = 3.0


def compute_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Recebe um DataFrame com coluna 'close' e devolve um novo DataFrame
    com todas as colunas de indicadores anexadas."""
    out = df.copy()
    close = out["close"]
    high = out["high"] if "high" in out.columns else close
    low = out["low"] if "low" in out.columns else close

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

    out["atr"] = ind.atr(high, low, close, cfg.atr_period)

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


def apply_risk_management(
    action: str,
    position_qty: float,
    position_avg_price: float,
    position_peak_price: float,
    current_price: float,
    atr: float,
    cfg: StrategyConfig,
) -> str:
    """Força uma venda quando a posição aberta atinge o stop-loss, ou quando
    o stop móvel (trailing stop, distância baseada no ATR) é acionado —
    protege contra segurar uma perda grande esperando o indicador virar, sem
    travar o lucro cedo demais numa tendência longa nem ser expulso por
    oscilações normais em ativos mais voláteis."""
    if position_qty > 0 and position_avg_price > 0:
        change_from_entry = (current_price - position_avg_price) / position_avg_price
        if change_from_entry <= -cfg.stop_loss_pct:
            return "SELL"

        peak = max(position_peak_price, position_avg_price)
        gain_from_entry_at_peak = (peak - position_avg_price) / position_avg_price
        if gain_from_entry_at_peak >= cfg.trailing_activate_pct:
            if pd.isna(atr) or atr <= 0:
                stop_price = peak * (1 - cfg.stop_loss_pct)
            else:
                stop_price = peak - cfg.trailing_atr_mult * atr
            if current_price <= stop_price:
                return "SELL"
    return action


def generate_signals(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Recebe OHLCV, devolve DataFrame com colunas de indicadores + 'score' + 'action'."""
    enriched = compute_indicators(df, cfg)
    enriched["score"] = enriched.apply(lambda row: score_row(row, cfg), axis=1)
    enriched["action"] = enriched["score"].apply(lambda s: decide_action(s, cfg))
    return enriched
