"""Backtest: roda a estratégia sobre dados históricos e mede o desempenho
da carteira simulada, sem nenhuma conexão com corretora real."""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor
from tradebot.strategy import StrategyConfig, apply_risk_management, generate_signals

logger = logging.getLogger("tradebot.backtest")

TRADING_DAYS_PER_YEAR = 252


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    benchmark_curve: pd.Series
    signals: pd.DataFrame
    final_summary: dict
    metrics: dict
    benchmark_metrics: dict


def _max_drawdown_pct(equity: pd.Series) -> float:
    return ((equity / equity.cummax()) - 1).min() * 100 if len(equity) else 0.0


def _return_metrics(equity: pd.Series) -> dict:
    """CAGR, Sharpe, Sortino e Calmar a partir de uma curva de patrimônio
    diária. Assume taxa livre de risco = 0 (simplificação razoável para
    comparar estratégia vs buy-and-hold no mesmo período)."""
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return {"cagr_pct": 0.0, "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0}

    returns = equity.pct_change().dropna()
    total_days = (equity.index[-1] - equity.index[0]).days
    years = total_days / 365.25 if total_days > 0 else len(equity) / TRADING_DAYS_PER_YEAR
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    mean_return = returns.mean()
    std = returns.std()
    sharpe = (mean_return / std * np.sqrt(TRADING_DAYS_PER_YEAR)) if std and std > 0 else 0.0

    downside = returns[returns < 0]
    if len(downside) == 0:
        downside_std = 0.0
    elif len(downside) == 1:
        downside_std = abs(downside.iloc[0])  # desvio-padrão de 1 amostra é indefinido
    else:
        downside_std = downside.std()
    if downside_std and downside_std > 0:
        sortino = float(mean_return / downside_std * np.sqrt(TRADING_DAYS_PER_YEAR))
    else:
        # sem nenhum retorno negativo: risco de queda nulo -> "infinitamente bom"
        # se o retorno médio for positivo, sem risco pra penalizar se for zero
        sortino = float("inf") if mean_return > 0 else 0.0

    max_dd = _max_drawdown_pct(equity)
    if max_dd != 0:
        calmar = (cagr * 100) / abs(max_dd)
    else:
        # nunca caiu do pico: sem drawdown pra penalizar o retorno
        calmar = float("inf") if cagr > 0 else 0.0

    return {
        "cagr_pct": cagr * 100,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": calmar,
    }


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


def print_report(result: BacktestResult, symbol: str) -> None:
    s = result.final_summary
    m = result.metrics
    bm = result.benchmark_metrics

    bench_start = result.benchmark_curve.iloc[0]
    bench_end = result.benchmark_curve.iloc[-1]
    bench_pnl_pct = (bench_end - bench_start) / bench_start * 100

    print(f"\n=== Relatório de backtest — {symbol} (SIMULADO / PAPER) ===")
    print(f"Caixa final:          {s['cash']:.2f}")
    print(f"Patrimônio final:     {s['equity']:.2f}")
    print(f"Resultado (PnL):      {s['pnl']:.2f} ({s['pnl_pct']:.2f}%)")
    print(f"Buy-and-hold no período: {bench_pnl_pct:.2f}%")
    diff = s["pnl_pct"] - bench_pnl_pct
    comparativo = "supera" if diff > 0 else "fica atrás d" if diff < 0 else "empata com"
    print(f"=> Estratégia {comparativo}o buy-and-hold em {diff:+.2f} pontos percentuais")

    print(f"\n{'Métrica':<22}{'Estratégia':>14}{'Buy&Hold':>14}")
    print("-" * 50)
    print(f"{'CAGR':<22}{m['cagr_pct']:>13.2f}%{bm['cagr_pct']:>13.2f}%")
    print(f"{'Máx. drawdown':<22}{m['max_drawdown_pct']:>13.2f}%{bm['max_drawdown_pct']:>13.2f}%")
    print(f"{'Sharpe':<22}{m['sharpe']:>14.2f}{bm['sharpe']:>14.2f}")
    print(f"{'Sortino':<22}{m['sortino']:>14.2f}{bm['sortino']:>14.2f}")
    print(f"{'Calmar':<22}{m['calmar']:>14.2f}{bm['calmar']:>14.2f}")

    pf_str = "inf" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:.2f}"
    print(f"\nProfit factor:        {pf_str}")
    print(f"Nº de operações (trades completos): {m['num_trades']}")
    print(f"Nº de ordens (compras/vendas):      {s['num_fills']}")
    print(f"% do tempo com posição aberta:      {m['time_exposed_pct']:.1f}%")
    print(f"Turnover (volume negociado / caixa inicial): {m['turnover']:.2f}x")
    print(f"Custos totais (taxas):               {m['total_fees']:.2f}")
    print(f"Posições em aberto:                  {s['positions']}")

    dd_diff = m["max_drawdown_pct"] - bm["max_drawdown_pct"]
    protecao = "protegeu capital melhor" if dd_diff > 0 else "teve queda pior" if dd_diff < 0 else "teve a mesma queda"
    print(f"\n=> No pior momento, a estratégia {protecao} que o buy-and-hold em {abs(dd_diff):.2f} pontos percentuais")


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
        f"{'Símbolo':<12}{'PnL %':>9}{'B&H %':>9}"
        f"{'DD Estr':>10}{'DD B&H':>10}{'Sharpe':>9}{'Sharpe B&H':>12}{'Ordens':>8}"
    )
    print(header)
    print("-" * len(header))
    for symbol, result in results.items():
        s = result.final_summary
        m = result.metrics
        bm = result.benchmark_metrics
        bench_start = result.benchmark_curve.iloc[0]
        bench_end = result.benchmark_curve.iloc[-1]
        bench_pnl_pct = (bench_end - bench_start) / bench_start * 100
        print(
            f"{symbol:<12}{s['pnl_pct']:>8.2f}%{bench_pnl_pct:>8.2f}%"
            f"{m['max_drawdown_pct']:>9.2f}%{bm['max_drawdown_pct']:>9.2f}%"
            f"{m['sharpe']:>9.2f}{bm['sharpe']:>12.2f}{s['num_fills']:>8}"
        )

    print_aggregate_comparison(results)


def print_aggregate_comparison(results: dict[str, BacktestResult]) -> None:
    """Média das métricas em todos os símbolos, estratégia vs buy-and-hold
    lado a lado — a visão que realmente importa para decidir se a troca de
    risco por retorno compensa, em vez de olhar ativo por ativo."""
    if not results:
        return

    def avg(key: str, source: str) -> float:
        values = [
            (r.metrics if source == "strategy" else r.benchmark_metrics)[key] for r in results.values()
        ]
        return sum(values) / len(values)

    def avg_field(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    pnl_pcts = [r.final_summary["pnl_pct"] for r in results.values()]
    bench_pnl_pcts = [
        (r.benchmark_curve.iloc[-1] - r.benchmark_curve.iloc[0]) / r.benchmark_curve.iloc[0] * 100
        for r in results.values()
    ]
    max_dds = [r.metrics["max_drawdown_pct"] for r in results.values()]
    bench_max_dds = [r.benchmark_metrics["max_drawdown_pct"] for r in results.values()]

    print(f"\n=== Média entre {len(results)} ativos: Estratégia vs Buy&Hold ===")
    print(f"{'Métrica':<15}{'Estratégia':>14}{'Buy&Hold':>14}")
    print("-" * 43)
    print(f"{'Retorno':<15}{avg_field(pnl_pcts):>13.2f}%{avg_field(bench_pnl_pcts):>13.2f}%")
    print(f"{'CAGR':<15}{avg('cagr_pct', 'strategy'):>13.2f}%{avg('cagr_pct', 'benchmark'):>13.2f}%")
    print(f"{'Máx. drawdown':<15}{avg_field(max_dds):>13.2f}%{avg_field(bench_max_dds):>13.2f}%")
    print(f"{'Sharpe':<15}{avg('sharpe', 'strategy'):>14.2f}{avg('sharpe', 'benchmark'):>14.2f}")
    print(f"{'Sortino':<15}{avg('sortino', 'strategy'):>14.2f}{avg('sortino', 'benchmark'):>14.2f}")
    print(f"{'Calmar':<15}{avg('calmar', 'strategy'):>14.2f}{avg('calmar', 'benchmark'):>14.2f}")
