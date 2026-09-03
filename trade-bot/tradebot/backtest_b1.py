"""B1 — Breakout puro. Primeira hipótese da família B (Trend Following /
Breakout), estruturalmente separada da família V (sistema de votos V1-V6).

A V1 (tradebot/strategy.py + tradebot/backtest.py) permanece 100% intocada
e continua sendo o benchmark congelado. A B1 NÃO reaproveita o sistema de
votos da V1 — é uma estratégia estruturalmente diferente: entra comprado
quando o preço rompe a máxima dos últimos N períodos (rompimento puro,
sem RSI, MACD, Bollinger, Fibonacci, Volume, ADX ou qualquer outro
filtro). O ATR é usado exclusivamente para stops, nunca como filtro de
entrada.

Hipótese testada:

H0: um rompimento puro de N períodos, sem nenhum filtro adicional, não
    produz vantagem de retorno ajustado ao risco consistente sobre
    buy-and-hold nem sobre a V1, depois de custos.
H1: capturar o início de tendências via rompimento de máxima de N
    períodos produz vantagem robusta, replicável em amostra, fora da
    amostra e em walk-forward.

Regras de execução (decididas ANTES de rodar qualquer teste, para não
deixar nenhuma ambiguidade de timing/look-ahead em aberto):

- Entrada: `close[t] > highest_high_N[t]`, onde `highest_high_N[t]` é a
  máxima das máximas dos `breakout_period` candles ANTERIORES a t (o
  candle t não entra nessa conta). O sinal é decidido com informação
  disponível no FECHAMENTO de t; a execução acontece no OPEN de t+1 —
  nunca se assume fill no próprio candle do rompimento, porque num
  candle diário o rompimento intrabar não é observável (só sabemos a
  máxima do dia depois que ele fechou).
- Stop inicial: `preço médio de entrada - INITIAL_ATR_MULT * ATR`, onde o
  ATR usado é o do candle de SINAL (o candle anterior ao candle em que a
  compra é executada) — fixo a partir da entrada, nunca recalculado.
- Trailing stop: `pico de FECHAMENTO desde a entrada - TRAILING_ATR_MULT
  * ATR[t]`, com ATR e pico sempre calculados com informação disponível
  até o fechamento de t. O stop efetivo em cada dia é o maior entre o
  inicial e o trailing (o trailing só pode apertar o stop, nunca
  afrouxar).
- Saída: violação decidida por `close[t] <= stop_price[t]` — mesma regra
  de "decide no fechamento, executa no candle seguinte"; execução no
  OPEN de t+1. Isso evita usar a máxima/mínima do PRÓPRIO candle em que
  a saída seria executada: o candle que gera a decisão nunca é o mesmo
  candle da execução.

Parâmetros CONGELADOS antes de rodar qualquer teste (não ajustados
depois de ver resultado):
- `BREAKOUT_PERIOD = 20`
- `INITIAL_ATR_MULT = 2.0`
- `TRAILING_ATR_MULT = 3.0`
- `ATR_PERIOD = 14`

Sizing e custos: idênticos à V1 (fração fixa do caixa por compra, mesma
taxa e slippage) — nenhum sizing sofisticado. Universo: o mesmo da
comparação principal da V1 (US_WATCHLIST + BR_WATCHLIST, ver
tradebot/markets.py) — sem escolher ativos depois de ver resultado.

Só depois do teste principal (IS + OOS + walk-forward) faz sentido rodar
o teste de sensibilidade (`breakout_period` em 10/20/40, todos reportados
lado a lado, sem escolher o melhor depois) e decidir se um teste de
placebo é metodologicamente válido para esta família — nenhum dos dois é
feito automaticamente aqui, de propósito: primeiro se descobre se a B1
funciona, só depois se discute variante.
"""

import logging

import numpy as np
import pandas as pd

from tradebot import indicators as ind
from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.comparison import print_v1_challenger_comparison
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor

logger = logging.getLogger("tradebot.backtest_b1")

BREAKOUT_PERIOD = 20
INITIAL_ATR_MULT = 2.0
TRAILING_ATR_MULT = 3.0
ATR_PERIOD = 14


def generate_b1_signals(
    df: pd.DataFrame,
    breakout_period: int = BREAKOUT_PERIOD,
    atr_period: int = ATR_PERIOD,
) -> pd.DataFrame:
    """OHLC + ATR + a máxima das máximas dos `breakout_period` candles
    ANTERIORES ao candle atual (`shift(1)` garante que o candle atual não
    entra na própria conta) + o sinal de entrada (`close atual > essa
    máxima anterior`). Nenhuma dessas colunas usa informação futura."""
    out = df[["open", "high", "low", "close"]].copy()
    out["atr"] = ind.atr(df["high"], df["low"], df["close"], period=atr_period)
    out["highest_high_n"] = (
        df["high"].shift(1).rolling(window=breakout_period, min_periods=breakout_period).max()
    )
    out["entry_signal"] = out["close"] > out["highest_high_n"]
    return out


def run_backtest_b1(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg=None,  # não usado pela B1; aceito só para a mesma assinatura de compare()/run_walk_forward()
    breakout_period: int = BREAKOUT_PERIOD,
    initial_atr_mult: float = INITIAL_ATR_MULT,
    trailing_atr_mult: float = TRAILING_ATR_MULT,
    atr_period: int = ATR_PERIOD,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    signals = generate_b1_signals(df, breakout_period=breakout_period, atr_period=atr_period)
    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)

    equity_curve = []
    exposed_days = []

    pending_action: str | None = None  # decidido no fechamento de t, executado no open de t+1
    entry_atr: float | None = None
    peak_close: float = 0.0

    for i in range(len(signals)):
        row = signals.iloc[i]
        timestamp = signals.index[i]
        open_price = float(row["open"])
        close_price = float(row["close"])
        pos = portfolio.position(symbol)

        # 1) Executa, no OPEN de hoje, a decisão tomada no FECHAMENTO de ontem.
        if pending_action == "BUY" and pos.quantity == 0:
            fill = portfolio.buy(timestamp, symbol, open_price, cash_fraction)
            if fill:
                entry_atr = float(signals["atr"].iloc[i - 1]) if i > 0 else None
                peak_close = fill.price
        elif pending_action == "SELL" and pos.quantity > 0:
            portfolio.sell(timestamp, symbol, open_price, position_fraction=1.0)
            entry_atr = None
            peak_close = 0.0
        pending_action = None

        pos = portfolio.position(symbol)
        if pos.quantity > 0:
            peak_close = max(peak_close, close_price)

        # 2) Decide, com informação disponível até o FECHAMENTO de hoje, o
        #    que fazer no open de amanhã — nunca no mesmo candle da decisão.
        if pos.quantity == 0:
            if bool(row["entry_signal"]):
                pending_action = "BUY"
        else:
            current_atr = row["atr"]
            if entry_atr is not None and not pd.isna(current_atr) and pos.avg_price > 0:
                initial_stop = pos.avg_price - initial_atr_mult * entry_atr
                trailing_stop = peak_close - trailing_atr_mult * float(current_atr)
                stop_price = max(initial_stop, trailing_stop)
                if close_price <= stop_price:
                    pending_action = "SELL"

        equity_curve.append(portfolio.equity({symbol: close_price}))
        exposed_days.append(pos.quantity > 0)

    equity_series = pd.Series(equity_curve, index=signals.index, name="equity")

    first_price = float(signals["close"].iloc[0])
    benchmark_qty = starting_cash / first_price
    benchmark_curve = signals["close"] * benchmark_qty
    benchmark_curve.name = "benchmark"

    last_price = float(signals["close"].iloc[-1])
    summary = portfolio.summary({symbol: last_price})

    trades = compute_round_trip_pnls(portfolio.fills)
    turnover = sum(fill.notional for fill in portfolio.fills) / starting_cash if starting_cash else 0.0
    total_fees = sum(fill.fee for fill in portfolio.fills)
    time_exposed_pct = float(np.mean(exposed_days)) * 100 if exposed_days else 0.0

    metrics = _return_metrics(equity_series)
    metrics.update(
        {
            "max_drawdown_pct": _max_drawdown_pct(equity_series),
            "profit_factor": profit_factor(trades),
            "num_trades": len(trades),
            "time_exposed_pct": time_exposed_pct,
            "turnover": turnover,
            "total_fees": total_fees,
        }
    )

    benchmark_metrics = _return_metrics(benchmark_curve)
    benchmark_metrics["max_drawdown_pct"] = _max_drawdown_pct(benchmark_curve)

    return BacktestResult(
        equity_curve=equity_series,
        benchmark_curve=benchmark_curve,
        signals=signals,
        final_summary=summary,
        metrics=metrics,
        benchmark_metrics=benchmark_metrics,
    )


def run_multi_backtest_b1(
    symbols: list[str],
    strategy_cfg=None,  # não usado pela B1; aceito só para a mesma assinatura das outras run_multi_backtest_*
    breakout_period: int = BREAKOUT_PERIOD,
    initial_atr_mult: float = INITIAL_ATR_MULT,
    trailing_atr_mult: float = TRAILING_ATR_MULT,
    atr_period: int = ATR_PERIOD,
    period: str = "1y",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> dict[str, BacktestResult]:
    results: dict[str, BacktestResult] = {}
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, period=period, interval=interval, start=start, end=end)
            results[symbol] = run_backtest_b1(
                df,
                symbol,
                strategy_cfg,
                breakout_period=breakout_period,
                initial_atr_mult=initial_atr_mult,
                trailing_atr_mult=trailing_atr_mult,
                atr_period=atr_period,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest B1 para %s, pulando", symbol)
    return results


def print_v1_b1_comparison(v1_results: dict[str, BacktestResult], b1_results: dict[str, BacktestResult]) -> None:
    print_v1_challenger_comparison(v1_results, b1_results, challenger_label="B1")
