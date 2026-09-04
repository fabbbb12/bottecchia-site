"""Obtenção de candles (klines) diretamente da API pública da Binance —
histórico intraday de verdade (anos, não só os últimos dias que o
yfinance guarda), sem precisar de chave de API.

O endpoint de candles históricos (`/api/v3/klines`) é público — não
exige autenticação nem assinatura. Uma chave de API só ajudaria com
limite de taxa mais alto em uso intenso, e mesmo assim seria só a
chave pública como header (nunca a privada) — este módulo funciona
sem nenhuma chave.

IMPORTANTE: este módulo só chama o endpoint de candles (dado de
mercado público). Nunca chama endpoint de conta, ordem ou qualquer
coisa que exija autenticação — consistente com o resto do projeto,
que é 100% paper trading e nunca envia ordem real a lugar nenhum.
"""

import logging
import re
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

logger = logging.getLogger("tradebot.binance_data")

BASE_URL = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
MAX_KLINES_PER_REQUEST = 1000
REQUEST_TIMEOUT_SECONDS = 30
PAGINATION_SLEEP_SECONDS = 0.2  # educado com o rate limit em buscas longas


def _to_millis(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _period_to_start_date(period: str) -> str:
    """Converte um período relativo no mesmo formato aceito pelo yfinance
    (ex: "6mo", "1y", "5d") numa data de início absoluta, pra poder pedir
    o mesmo período à API da Binance (que só trabalha com datas fixas)."""
    match = re.fullmatch(r"(\d+)(d|mo|y)", period.strip().lower())
    if not match:
        raise ValueError(f"Período '{period}' não suportado pra símbolos Binance — use '--start'/'--end' fixos.")
    amount, unit = int(match.group(1)), match.group(2)
    today = datetime.now(timezone.utc)
    if unit == "d":
        start = today - relativedelta(days=amount)
    elif unit == "mo":
        start = today - relativedelta(months=amount)
    else:
        start = today - relativedelta(years=amount)
    return start.strftime("%Y-%m-%d")


def is_binance_symbol(symbol: str) -> bool:
    """Convenção usada neste projeto: símbolo termina em USDT (o par mais
    líquido da Binance) -> roteia pra API da Binance em vez do yfinance.
    Nenhuma ação/ticker do resto do projeto termina em "USDT", então essa
    checagem não tem ambiguidade com os outros mercados já suportados."""
    return symbol.upper().endswith("USDT")


def fetch_binance_klines(
    symbol: str,
    interval: str = "1d",
    period: str = "1y",
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Baixa candles históricos da Binance e devolve um DataFrame no mesmo
    formato usado no resto do projeto (colunas open/high/low/close/volume,
    índice de datas) — compatível com `tradebot.data.fetch_ohlcv`.

    `interval` usa a mesma convenção da Binance (1m, 5m, 15m, 30m, 1h, 4h,
    1d, 1w, 1M — os mesmos códigos já usados em `--interval` no resto do
    projeto). Pagina automaticamente em blocos de 1000 candles (limite da
    API por chamada) até cobrir o intervalo pedido. Sem `start`, usa
    `period` (mesmo formato do yfinance: "6mo", "1y", "5d") convertido pra
    uma data fixa, já que a API da Binance só trabalha com datas."""
    if not start:
        start = _period_to_start_date(period)

    start_ms = _to_millis(start)
    end_ms = _to_millis(end) if end else int(time.time() * 1000)

    logger.info("Baixando %s via Binance (interval=%s, start=%s, end=%s)...", symbol, interval, start, end)

    rows: list[list] = []
    cursor = start_ms
    while cursor < end_ms:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": MAX_KLINES_PER_REQUEST,
        }
        response = requests.get(BASE_URL + KLINES_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        last_close_time = batch[-1][6]
        if last_close_time <= cursor:
            break  # segurança: evita loop infinito se a API devolver algo inesperado
        cursor = last_close_time + 1
        if len(batch) < MAX_KLINES_PER_REQUEST:
            break  # última página
        time.sleep(PAGINATION_SLEEP_SECONDS)

    if not rows:
        raise ValueError(f"Nenhum dado retornado pela Binance para o símbolo '{symbol}'.")

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "num_trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("timestamp")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df[["open", "high", "low", "close", "volume"]]
