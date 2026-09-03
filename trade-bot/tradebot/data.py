"""Obtenção de dados de mercado (OHLCV) via yfinance.

Funciona tanto para ações/índices (ex: "PETR4.SA", "AAPL") quanto para
criptomoedas (ex: "BTC-USD", "ETH-USD"), sem precisar de chave de API.
"""

import pandas as pd
import yfinance as yf


def fetch_ohlcv(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Baixa histórico de preços e devolve um DataFrame com colunas
    padronizadas em minúsculo: open, high, low, close, volume.

    Se `start` (e opcionalmente `end`) forem informados (formato
    'AAAA-MM-DD'), usa esse intervalo de datas fixo em vez de `period` —
    necessário para testes fora da amostra (out-of-sample), onde o período
    precisa ser uma janela específica do passado, não "os últimos N anos a
    partir de hoje"."""
    if start:
        raw = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
    else:
        raw = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
    if raw.empty:
        raise ValueError(f"Nenhum dado retornado para o símbolo '{symbol}'.")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    raw = raw.rename(columns=str.lower)
    return raw[["open", "high", "low", "close", "volume"]].dropna()


def fetch_latest_price(symbol: str) -> float:
    df = fetch_ohlcv(symbol, period="5d", interval="1d")
    return float(df["close"].iloc[-1])
