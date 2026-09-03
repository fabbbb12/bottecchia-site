"""Backtest: roda a estratégia sobre dados históricos e mede o desempenho
da carteira simulada, sem nenhuma conexão com corretora real."""

from dataclasses import dataclass

import pandas as pd

from tradebot.portfolio import Portfolio
from tradebot.strategy import StrategyConfig, generate_signals


@dataclass
class BacktestResult:
    equity_curve: pd.Series
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
        action = row["action"]

        if action == "BUY":
            portfolio.buy(timestamp, symbol, price, cash_fraction)
        elif action == "SELL":
            portfolio.sell(timestamp, symbol, price, position_fraction=1.0)

        equity_curve.append(portfolio.equity({symbol: price}))

    equity_series = pd.Series(equity_curve, index=signals.index, name="equity")
    last_price = float(signals["close"].iloc[-1])
    summary = portfolio.summary({symbol: last_price})

    return BacktestResult(equity_curve=equity_series, signals=signals, final_summary=summary)


def print_report(result: BacktestResult, symbol: str) -> None:
    s = result.final_summary
    equity = result.equity_curve
    max_drawdown = ((equity / equity.cummax()) - 1).min() * 100 if len(equity) else 0.0

    print(f"\n=== Relatório de backtest — {symbol} (SIMULADO / PAPER) ===")
    print(f"Caixa final:        {s['cash']:.2f}")
    print(f"Patrimônio final:    {s['equity']:.2f}")
    print(f"Resultado (PnL):     {s['pnl']:.2f} ({s['pnl_pct']:.2f}%)")
    print(f"Máx. drawdown:       {max_drawdown:.2f}%")
    print(f"Ordens executadas:   {s['num_fills']}")
    print(f"Posições em aberto:  {s['positions']}")
