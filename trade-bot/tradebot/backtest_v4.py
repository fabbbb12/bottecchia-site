"""V4 — placebo/controle para a V3, isolado da V1.

A V3 testou um filtro de Fibonacci na entrada e reduziu drawdown de forma
consistente (in-sample e OOS), mas o retorno/Sharpe/Sortino/Calmar que
pareciam melhores no primeiro teste não se confirmaram fora da amostra.
Como a V3 também opera bem menos que a V1 (menos tempo exposto ao
mercado), fica a dúvida: a redução de drawdown vem de algo específico
sobre níveis de Fibonacci, ou só do fato de operar menos, mecanicamente
reduzindo a exposição ao pior momento do mercado?

A V4 responde isso: reaproveita o mesmo sistema de votos e o mesmo
stop-loss/trailing da V1 — a ÚNICA diferença é que a compra que a V1 já
geraria só é aceita com probabilidade `ACCEPTANCE_PROB` (sorteio
aleatório, SEM olhar preço, Fibonacci ou qualquer indicador). Se a V4
reduzir o drawdown tanto quanto a V3 reduziu, isso prova que Fibonacci
não acrescentou informação nenhuma — só "operar menos" já fazia todo o
trabalho. Se a V3 continuar reduzindo o drawdown MAIS que a V4, aí sim a
Fibonacci está fazendo algo específico, não só filtrando por acaso.

Parâmetros CONGELADOS antes de rodar qualquer teste:
- `ACCEPTANCE_PROB = 0.5`: escolhido porque a V3 cortou aproximadamente
  metade das operações da V1 nos dois períodos já testados (6→3, 4→3) —
  não foi ajustado depois de ver o resultado da V4.
- `SEED = 42`: fixo para o resultado ser reprodutível (mesma sequência de
  sorteios sempre que rodar de novo com os mesmos dados).
"""

import logging

import numpy as np
import pandas as pd

from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.comparison import print_v1_challenger_comparison
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor
from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals

logger = logging.getLogger("tradebot.backtest_v4")

ACCEPTANCE_PROB = 0.5
SEED = 42


def run_backtest_v4(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg: StrategyConfig,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    seed: int = SEED,
) -> BacktestResult:
    signals = generate_signals(df, strategy_cfg)  # idêntico à V1, nada mudou aqui
    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)
    rng = np.random.default_rng(seed)

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
            # regra exclusiva da V4: aceita a compra só com probabilidade
            # fixa, por sorteio — sem olhar preço, Fibonacci ou indicador
            if rng.random() > ACCEPTANCE_PROB:
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


def run_multi_backtest_v4(
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
            results[symbol] = run_backtest_v4(
                df,
                symbol,
                strategy_cfg,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest V4 para %s, pulando", symbol)
    return results


def print_v1_v4_comparison(v1_results: dict[str, BacktestResult], v4_results: dict[str, BacktestResult]) -> None:
    print_v1_challenger_comparison(v1_results, v4_results, challenger_label="V4")
