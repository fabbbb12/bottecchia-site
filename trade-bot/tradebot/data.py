"""Obtenção de dados de mercado (OHLCV) via yfinance (ações/índices/cripto
agregada) ou, para pares terminados em "USDT", diretamente da API pública
da Binance (intraday de verdade, sem precisar de chave de API — ver
`tradebot/binance_data.py`).
"""

import logging

import pandas as pd
import yfinance as yf

from tradebot.binance_data import fetch_binance_klines, is_binance_symbol

logger = logging.getLogger("tradebot.data")

DOWNLOAD_TIMEOUT_SECONDS = 30


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
    partir de hoje".

    O log de progresso (`logger.info`) é emitido a cada download porque,
    em walk-forward/multi-ativo, dezenas de chamadas de rede acontecem em
    sequência e sem isso não dá pra distinguir "ainda baixando" de
    "travou" — e o `logging.StreamHandler` já dá flush a cada linha, então
    aparece mesmo com a saída redirecionada pra arquivo. `timeout` evita
    que uma chamada de rede trave indefinidamente: estoura exceção (que
    quem chama já trata pulando o símbolo) em vez de nunca retornar.

    Símbolos terminados em "USDT" (ex: "BTCUSDT") são roteados pra API da
    Binance em vez do yfinance — mesmo formato de saída, mas com histórico
    intraday de verdade em vez dos poucos dias que o yfinance guarda."""
    if is_binance_symbol(symbol):
        return fetch_binance_klines(symbol, interval=interval, period=period, start=start, end=end)

    logger.info("Baixando %s (period=%s, interval=%s, start=%s, end=%s)...", symbol, period, interval, start, end)
    if start:
        raw = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
    else:
        raw = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
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
