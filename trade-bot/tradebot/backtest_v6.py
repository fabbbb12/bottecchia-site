"""V6 — filtro de Volume Relativo na entrada, isolado da V1.

A V1 (tradebot/strategy.py + tradebot/backtest.py) permanece 100%
intocada; ela é o benchmark interno congelado. A V6 reaproveita
integralmente o mesmo sistema de votos e o mesmo stop-loss/trailing da
V1 — a ÚNICA diferença é uma condição extra na ENTRADA: a compra que a
V1 já geraria só é executada se o volume do dia do sinal estiver
significativamente acima da média (Volume Relativo alto) — "confirmação
por volume", uma hipótese diferente e independente da linha de
Fibonacci (V2/V3/V5), que já foi testada e rejeitada.

Hipótese testada:

H0: volume não acrescenta informação relevante à V1.
H1: Volume Relativo alto no dia do sinal de compra confirma rompimentos
    com maior probabilidade de continuação, melhorando a qualidade da
    entrada mesmo negociando com menos frequência.

Parâmetros CONGELADOS antes de rodar qualquer teste (não ajustados
depois de ver resultado):
- `RVOL_PERIOD = 20`: janela da média móvel de volume usada como
  referência (padrão comum de mercado).
- `RVOL_THRESHOLD = 1.5`: Volume Relativo mínimo no dia do sinal para a
  compra ser aceita — 1,5x a média é o valor mais citado na literatura
  de mercado como "volume confirmado"/"volume anômalo".
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

logger = logging.getLogger("tradebot.backtest_v6")

RVOL_PERIOD = 20
RVOL_THRESHOLD = 1.5


def run_backtest_v6(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg: StrategyConfig,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    signals = generate_signals(df, strategy_cfg)  # idêntico à V1, nada mudou aqui
    signals["rvol"] = ind.relative_volume(df["volume"], period=RVOL_PERIOD)

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

        if action == "BUY" and pos.quantity == 0:
            rvol = row["rvol"]
            if pd.isna(rvol) or rvol < RVOL_THRESHOLD:
                # regra exclusiva da V6: sem volume confirmando, não compra
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


def run_multi_backtest_v6(
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
            results[symbol] = run_backtest_v6(
                df,
                symbol,
                strategy_cfg,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest V6 para %s, pulando", symbol)
    return results


def print_v1_v6_comparison(v1_results: dict[str, BacktestResult], v6_results: dict[str, BacktestResult]) -> None:
    print_v1_challenger_comparison(v1_results, v6_results, challenger_label="V6")
