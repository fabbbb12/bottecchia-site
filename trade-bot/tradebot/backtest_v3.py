"""V3 — experimento de filtro de Fibonacci, isolado da V1.

A V1 (tradebot/strategy.py + tradebot/backtest.py) permanece 100%
intocada; ela é o benchmark interno congelado. A V3 reaproveita
integralmente o mesmo sistema de votos e o mesmo stop-loss/trailing da
V1 — a ÚNICA diferença é uma condição extra na ENTRADA: a compra que a
V1 já geraria só é executada se o preço estiver perto de um nível de
retração de Fibonacci do swing recente. Saída (stop-loss, trailing) é
idêntica à V1, sem a regra de reentrada da V2 — é um teste de uma única
variável por vez.

Hipótese testada: comprar apenas quando o preço está numa "zona de
Fibonacci" (suporte historicamente citado por operadores) filtra
entradas de pior qualidade que o sistema de votos sozinho aceitaria,
melhorando o resultado por operação mesmo negociando com menos
frequência.

Parâmetros CONGELADOS antes de rodar qualquer teste (não ajustados
depois de ver resultado):
- Swing: máxima/mínima dos últimos 50 dias (`FIB_PERIOD`).
- Zona considerada: retrações de 38,2% / 50% / 61,8% — a "zona áurea"
  clássica (`FIB_LEVELS`). 23,6% e 78,6% ficam de fora por serem mais
  extremos e menos citados como suporte relevante.
- Tolerância: preço a até 1,5% de algum desses níveis conta como "na
  zona" (`FIB_TOLERANCE_PCT`).

RESULTADO: EXPERIMENTO REJEITADO (2021-2023 e 2018-2020 OOS, 11 ativos).
Reduz drawdown de forma real e confirmada contra um placebo aleatório
(V4) — a zona de Fibonacci carrega informação genuína sobre risco, não
é ilusão. Mas como filtro de ENTRADA, corta tanto trade ruim quanto
trade bom: retorno piorou vs V1 e chegou a perder até para o próprio
placebo em retorno no período OOS. Levou à V5 (Fibonacci como position
sizing em vez de filtro) e, depois, ao achado mais amplo replicado com
Volume (V6): filtros "espertos" baseados em preço/volume carregam um
viés de seleção dependente do regime de mercado que um corte aleatório
de mesmo tamanho não tem — ver tradebot/backtest_v6.py para o
detalhamento desse achado.
"""

import logging

import numpy as np
import pandas as pd

from tradebot import indicators as ind
from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.comparison import print_v1_challenger_comparison
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor
from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals

logger = logging.getLogger("tradebot.backtest_v3")

FIB_PERIOD = 50
FIB_LEVELS = ("fib_382", "fib_500", "fib_618")
FIB_TOLERANCE_PCT = 0.015


def _near_fib_zone(price: float, fib_row: pd.Series) -> bool:
    for level_name in FIB_LEVELS:
        level = fib_row[level_name]
        if pd.isna(level) or level <= 0:
            continue
        if abs(price - level) / level <= FIB_TOLERANCE_PCT:
            return True
    return False


def run_backtest_v3(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg: StrategyConfig,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    signals = generate_signals(df, strategy_cfg)  # idêntico à V1, nada mudou aqui
    fib = ind.fibonacci_levels(df["high"], df["low"], period=FIB_PERIOD)
    signals = signals.join(fib)

    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)

    equity_curve = []
    exposed_days = []
    for timestamp, row in signals.iterrows():
        price = float(row["close"])
        pos = portfolio.position(symbol)
        if pos.quantity > 0:
            pos.peak_price = max(pos.peak_price, price)
        action = apply_risk_management(
            row["action"], pos.quantity, pos.avg_price, pos.peak_price, price, row["atr"], strategy_cfg
        )

        if action == "BUY" and pos.quantity == 0 and not _near_fib_zone(price, row):
            # regra exclusiva da V3: só compra se o preço estiver perto de
            # uma zona de Fibonacci do swing recente
            action = "HOLD"

        if action == "BUY":
            fill = portfolio.buy(timestamp, symbol, price, cash_fraction)
            if fill:
                pos.peak_price = fill.price
        elif action == "SELL":
            portfolio.sell(timestamp, symbol, price, position_fraction=1.0)

        equity_curve.append(portfolio.equity({symbol: price}))
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


def run_multi_backtest_v3(
    symbols: list[str],
    strategy_cfg: StrategyConfig,
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
            results[symbol] = run_backtest_v3(
                df,
                symbol,
                strategy_cfg,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest V3 para %s, pulando", symbol)
    return results


def print_v1_v3_comparison(v1_results: dict[str, BacktestResult], v3_results: dict[str, BacktestResult]) -> None:
    print_v1_challenger_comparison(v1_results, v3_results, challenger_label="V3")
