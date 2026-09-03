"""Backtest: roda a estratégia sobre dados históricos e mede o desempenho
da carteira simulada, sem nenhuma conexão com corretora real."""

import logging
from dataclasses import dataclass

import pandas as pd

from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio
from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals

logger = logging.getLogger("tradebot.backtest")


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    benchmark_curve: pd.Series
    signals: pd.DataFrame
    final_summary: dict


def run_backtest(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg: StrategyConfig,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    signals = generate_signals(df, strategy_cfg)
    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)

    equity_curve = []
    for timestamp, row in signals.iterrows():
        price = float(row["close"])
        pos = portfolio.position(symbol)
        if pos.quantity > 0:
            pos.peak_price = max(pos.peak_price, price)
        action = apply_risk_management(
            row["action"], pos.quantity, pos.avg_price, pos.peak_price, price, row["atr"], strategy_cfg
        )

        if action == "BUY":
            fill = portfolio.buy(timestamp, symbol, price, cash_fraction)
            if fill:
                pos.peak_price = fill.price
        elif action == "SELL":
            portfolio.sell(timestamp, symbol, price, position_fraction=1.0)

        equity_curve.append(portfolio.equity({symbol: price}))

    equity_series = pd.Series(equity_curve, index=signals.index, name="equity")

    first_price = float(signals["close"].iloc[0])
    benchmark_qty = starting_cash / first_price
    benchmark_curve = signals["close"] * benchmark_qty
    benchmark_curve.name = "benchmark"

    last_price = float(signals["close"].iloc[-1])
    summary = portfolio.summary({symbol: last_price})

    return BacktestResult(
        equity_curve=equity_series,
        benchmark_curve=benchmark_curve,
        signals=signals,
        final_summary=summary,
    )


def _max_drawdown_pct(equity: pd.Series) -> float:
    return ((equity / equity.cummax()) - 1).min() * 100 if len(equity) else 0.0


def print_report(result: BacktestResult, symbol: str) -> None:
    s = result.final_summary
    max_drawdown = _max_drawdown_pct(result.equity_curve)
    bench_max_drawdown = _max_drawdown_pct(result.benchmark_curve)

    bench_start = result.benchmark_curve.iloc[0]
    bench_end = result.benchmark_curve.iloc[-1]
    bench_pnl_pct = (bench_end - bench_start) / bench_start * 100

    print(f"\n=== Relatório de backtest — {symbol} (SIMULADO / PAPER) ===")
    print(f"Caixa final:        {s['cash']:.2f}")
    print(f"Patrimônio final:    {s['equity']:.2f}")
    print(f"Resultado (PnL):     {s['pnl']:.2f} ({s['pnl_pct']:.2f}%)")
    print(f"Máx. drawdown (estratégia): {max_drawdown:.2f}%")
    print(f"Máx. drawdown (buy-and-hold): {bench_max_drawdown:.2f}%")
    print(f"Ordens executadas:   {s['num_fills']}")
    print(f"Posições em aberto:  {s['positions']}")
    print(f"Buy-and-hold no período: {bench_pnl_pct:.2f}% (comprar e segurar, sem estratégia)")
    diff = s["pnl_pct"] - bench_pnl_pct
    comparativo = "supera" if diff > 0 else "fica atrás d" if diff < 0 else "empata com"
    print(f"=> Estratégia {comparativo}o buy-and-hold em {diff:+.2f} pontos percentuais")
    # ambos são negativos (ex: -13.88); "menos negativo" = queda menor = melhor proteção
    dd_diff = max_drawdown - bench_max_drawdown
    protecao = "protegeu capital melhor" if dd_diff > 0 else "teve queda pior" if dd_diff < 0 else "teve a mesma queda"
    print(f"=> No pior momento, a estratégia {protecao} que o buy-and-hold em {abs(dd_diff):.2f} pontos percentuais")


def run_multi_backtest(
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
    """Roda o backtest para vários símbolos (cada um com sua própria carteira
    isolada) e devolve um dicionário {símbolo: resultado}. Símbolos que
    falharem ao baixar dados são pulados com um aviso, sem interromper os
    demais."""
    results: dict[str, BacktestResult] = {}
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, period=period, interval=interval, start=start, end=end)
            results[symbol] = run_backtest(
                df,
                symbol,
                strategy_cfg,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest para %s, pulando", symbol)
    return results


def print_summary_table(results: dict[str, BacktestResult]) -> None:
    if not results:
        print("Nenhum resultado para exibir.")
        return

    print("\n=== Resumo comparativo (SIMULADO / PAPER) ===")
    header = (
        f"{'Símbolo':<12}{'PnL':>12}{'PnL %':>10}{'Buy&Hold %':>12}"
        f"{'Máx DD':>10}{'DD B&H':>10}{'Ordens':>9}"
    )
    print(header)
    print("-" * len(header))
    for symbol, result in results.items():
        s = result.final_summary
        max_dd = _max_drawdown_pct(result.equity_curve)
        bench_max_dd = _max_drawdown_pct(result.benchmark_curve)
        bench_start = result.benchmark_curve.iloc[0]
        bench_end = result.benchmark_curve.iloc[-1]
        bench_pnl_pct = (bench_end - bench_start) / bench_start * 100
        print(
            f"{symbol:<12}{s['pnl']:>12.2f}{s['pnl_pct']:>9.2f}%{bench_pnl_pct:>11.2f}%"
            f"{max_dd:>9.2f}%{bench_max_dd:>9.2f}%{s['num_fills']:>9}"
        )
