"""V2 — experimento de reentrada, isolado da V1.

A V1 (tradebot/strategy.py + tradebot/backtest.py) permanece 100%
intocada; ela é o benchmark interno congelado. A V2 reaproveita
integralmente o mesmo sistema de votos (SMA/RSI/MACD/Bollinger) e o
mesmo stop-loss/trailing-stop da V1 — a ÚNICA diferença é a regra de
reentrada depois de uma venda.

Hipótese testada: o problema da V1 não é a entrada, é que ela sai para
se proteger (stop-loss ou trailing) e demora a recomprar — perdendo parte
da recuperação em ativos que caem e voltam dentro do período (o padrão
visto em MSFT/NVDA/GOOGL no teste 2021-2023). A V2 permite reentrar assim
que a tendência de curto prazo (SMA rápida > SMA lenta) voltar a
confirmar, em vez de esperar o sinal de compra completo da V1 (que exige
RSI e/ou MACD também alinharem). Nenhum indicador novo, nenhum parâmetro
novo — é uma mudança estrutural na regra de reentrada, não um ajuste de
tuning.
"""

import logging
import statistics
from typing import Callable

import numpy as np
import pandas as pd

from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor
from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals

logger = logging.getLogger("tradebot.backtest_v2")


def run_backtest_v2(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg: StrategyConfig,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    signals = generate_signals(df, strategy_cfg)  # idêntico à V1, nada mudou aqui
    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)

    equity_curve = []
    exposed_days = []
    awaiting_reentry = False  # True logo após uma venda, até a V2 recomprar

    for timestamp, row in signals.iterrows():
        price = float(row["close"])
        pos = portfolio.position(symbol)
        if pos.quantity > 0:
            pos.peak_price = max(pos.peak_price, price)
        action = apply_risk_management(
            row["action"], pos.quantity, pos.avg_price, pos.peak_price, price, row["atr"], strategy_cfg
        )

        if pos.quantity == 0 and awaiting_reentry and action != "BUY":
            # regra exclusiva da V2: dispensa o sinal completo da V1 se a
            # tendência de curto prazo já confirmou de novo
            if row["sma_fast"] > row["sma_slow"]:
                action = "BUY"

        if action == "BUY":
            fill = portfolio.buy(timestamp, symbol, price, cash_fraction)
            if fill:
                pos.peak_price = fill.price
                awaiting_reentry = False
        elif action == "SELL":
            fill = portfolio.sell(timestamp, symbol, price, position_fraction=1.0)
            if fill:
                awaiting_reentry = True

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


def run_multi_backtest_v2(
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
            results[symbol] = run_backtest_v2(
                df,
                symbol,
                strategy_cfg,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest V2 para %s, pulando", symbol)
    return results


def _bench_pnl_pct(result: BacktestResult) -> float:
    b0 = result.benchmark_curve.iloc[0]
    b1 = result.benchmark_curve.iloc[-1]
    return (b1 - b0) / b0 * 100


_METRIC_EXTRACTORS: list[tuple[str, Callable[[BacktestResult], float], Callable[[BacktestResult], float]]] = [
    ("Retorno", lambda r: r.final_summary["pnl_pct"], _bench_pnl_pct),
    ("CAGR", lambda r: r.metrics["cagr_pct"], lambda r: r.benchmark_metrics["cagr_pct"]),
    (
        "Máx. drawdown",
        lambda r: r.metrics["max_drawdown_pct"],
        lambda r: r.benchmark_metrics["max_drawdown_pct"],
    ),
    ("Sharpe", lambda r: r.metrics["sharpe"], lambda r: r.benchmark_metrics["sharpe"]),
    ("Sortino", lambda r: r.metrics["sortino"], lambda r: r.benchmark_metrics["sortino"]),
    ("Calmar", lambda r: r.metrics["calmar"], lambda r: r.benchmark_metrics["calmar"]),
]


def print_v1_v2_comparison(v1_results: dict[str, BacktestResult], v2_results: dict[str, BacktestResult]) -> None:
    """V1 vs V2 vs Buy&Hold lado a lado — média, mediana e contagem de
    vitórias (V2 supera V1, V2 supera B&H, V1 supera B&H) por métrica.
    Critério de aprovação da V2 (não é "bater tudo"): drawdown não piorar
    muito frente à V1, retorno melhorar claramente frente à V1, Sharpe/
    Sortino saírem da zona claramente negativa — e tudo isso robusto na
    mediana e nas vitórias, não só na média."""
    symbols = [s for s in v1_results if s in v2_results]
    if not symbols:
        print("Nenhum símbolo em comum entre V1 e V2 para comparar.")
        return
    n = len(symbols)

    print(f"\n=== V1 vs V2 vs Buy&Hold entre {n} ativos ===")
    header = (
        f"{'Métrica':<15}{'Méd V1':>9}{'Méd V2':>9}{'Méd B&H':>9}"
        f"{'Med V1':>9}{'Med V2':>9}{'Med B&H':>9}{'V2>V1':>8}{'V2>B&H':>8}{'V1>B&H':>8}"
    )
    print(header)
    print("-" * len(header))
    for name, extractor, bench_extractor in _METRIC_EXTRACTORS:
        v1_vals = [extractor(v1_results[s]) for s in symbols]
        v2_vals = [extractor(v2_results[s]) for s in symbols]
        bench_vals = [bench_extractor(v1_results[s]) for s in symbols]
        unit = "" if name in ("Sharpe", "Sortino", "Calmar") else "%"

        mean_v1, mean_v2, mean_b = statistics.mean(v1_vals), statistics.mean(v2_vals), statistics.mean(bench_vals)
        median_v1 = statistics.median(v1_vals)
        median_v2 = statistics.median(v2_vals)
        median_b = statistics.median(bench_vals)
        v2_beats_v1 = sum(1 for a, b in zip(v2_vals, v1_vals) if a > b)
        v2_beats_b = sum(1 for a, b in zip(v2_vals, bench_vals) if a > b)
        v1_beats_b = sum(1 for a, b in zip(v1_vals, bench_vals) if a > b)
        print(
            f"{name:<15}{mean_v1:>8.2f}{unit}{mean_v2:>8.2f}{unit}{mean_b:>8.2f}{unit}"
            f"{median_v1:>8.2f}{unit}{median_v2:>8.2f}{unit}{median_b:>8.2f}{unit}"
            f"{v2_beats_v1:>5}/{n}{v2_beats_b:>5}/{n}{v1_beats_b:>5}/{n}"
        )

    v1_trades = [v1_results[s].metrics["num_trades"] for s in symbols]
    v2_trades = [v2_results[s].metrics["num_trades"] for s in symbols]
    v1_exposed = [v1_results[s].metrics["time_exposed_pct"] for s in symbols]
    v2_exposed = [v2_results[s].metrics["time_exposed_pct"] for s in symbols]
    print(
        f"\nNº de trades (mediana):        V1={statistics.median(v1_trades):.0f}"
        f"   V2={statistics.median(v2_trades):.0f}"
    )
    print(
        f"% tempo exposto (mediana):     V1={statistics.median(v1_exposed):.1f}%"
        f"   V2={statistics.median(v2_exposed):.1f}%"
    )
    print(
        "\nColunas: 'Méd/Med X' = média/mediana daquele valor entre os ativos; "
        "'A>B' = em quantos ativos A superou B naquela métrica."
    )
