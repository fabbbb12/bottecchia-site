"""V5 — Fibonacci como position sizing (não como filtro de entrada),
isolado da V1.

A V3 provou (contra um placebo aleatório, V4) que a proximidade de uma
zona de Fibonacci carrega informação real sobre risco de drawdown — não
é ilusão. Mas usar isso como filtro de entrada (recusar o trade) cortou
tanto trade ruim quanto trade bom, custando mais retorno do que valia a
proteção (V3 até perdeu em retorno para o placebo). A V5 testa um jeito
mais inteligente de usar a mesma informação: em vez de recusar o trade,
reduz o TAMANHO da posição quando o preço está longe de uma zona de
Fibonacci, mantendo o tamanho normal quando está perto. Todo trade que a
V1 faria continua acontecendo — só varia quanto capital é alocado.

A V1 (tradebot/strategy.py + tradebot/backtest.py) permanece 100%
intocada; o sistema de votos, o stop-loss e o trailing são idênticos aos
da V1 e da V3 — a ÚNICA diferença é o tamanho da posição em cada compra.

Parâmetros CONGELADOS antes de rodar qualquer teste (reaproveitados da
V3, mais um novo):
- Zona de Fibonacci: idêntica à V3 (swing de 50 dias, níveis 38,2/50/
  61,8%, tolerância de 1,5% — ver tradebot/backtest_v3.py).
- `FAR_ZONE_SIZE_MULTIPLIER = 0.5`: metade do tamanho normal da posição
  quando o preço está longe de qualquer zona de Fibonacci no momento da
  compra. Perto de uma zona, o tamanho é o normal (100%, igual à V1).

RESULTADO: EXPERIMENTO REJEITADO (2021-2023 e 2018-2020 OOS, 11 ativos).
Resultado inconsistente entre os dois períodos (não só fraco — inverte
de sinal): melhora retorno/Sharpe/Sortino/Calmar em 2018-2020 mas piora
todos eles em 2021-2023, com redução de drawdown pequena (1-2pp) nos
dois. Ver tradebot/backtest_v6.py para o achado consolidado (via
placebo V4) de que filtros baseados em preço/volume carregam um viés de
seleção dependente do regime de mercado.
"""

import logging

import numpy as np
import pandas as pd

from tradebot import indicators as ind
from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.backtest_v3 import FIB_PERIOD, _near_fib_zone
from tradebot.comparison import print_v1_challenger_comparison
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor
from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals

logger = logging.getLogger("tradebot.backtest_v5")

FAR_ZONE_SIZE_MULTIPLIER = 0.5


def _position_size(price: float, fib_row: pd.Series, cash_fraction: float) -> float:
    """Tamanho da posição (fração do caixa) para esta compra: normal perto
    de uma zona de Fibonacci, reduzido quando longe de todas elas."""
    if _near_fib_zone(price, fib_row):
        return cash_fraction
    return cash_fraction * FAR_ZONE_SIZE_MULTIPLIER


def run_backtest_v5(
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

        if action == "BUY":
            size = _position_size(price, row, cash_fraction)
            fill = portfolio.buy(timestamp, symbol, price, size)
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


def run_multi_backtest_v5(
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
            results[symbol] = run_backtest_v5(
                df,
                symbol,
                strategy_cfg,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest V5 para %s, pulando", symbol)
    return results


def print_v1_v5_comparison(v1_results: dict[str, BacktestResult], v5_results: dict[str, BacktestResult]) -> None:
    print_v1_challenger_comparison(v1_results, v5_results, challenger_label="V5")
