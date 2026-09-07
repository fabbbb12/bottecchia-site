"""G1 — IBS (Internal Bar Strength) com filtro de tendência. Swing trade
de curto prazo (poucos dias), mecanicamente diferente de D1 (Bandas de
Bollinger, rejeitada): o gatilho aqui é a posição do fechamento dentro
do candle do dia (pânico intradiário), não a distância a uma banda de
volatilidade -- método de Connors/Alvarez ("Short-Term Trading
Strategies That Work").

Regras decididas ANTES de rodar qualquer teste:
- Universo: ETFs líquidos (SPY, QQQ) -- não ações individuais. A
  literatura de reversão de curto prazo é conhecida por ter parte do
  "edge" documentado como artefato de execução (bid-ask bounce) em
  ações menos líquidas; ETFs grandes minimizam esse risco.
- Filtro de tendência: só compra se close > SMA(200) (só opera a favor
  do regime de alta de longo prazo, nunca contra).
- Entrada: IBS < 0.2 (fechou perto da mínima do dia -- pânico de curto
  prazo) E dentro do filtro de tendência. Decide no fechamento, executa
  na abertura do dia seguinte (mesma disciplina anti-lookahead do
  resto do projeto).
- Saída: IBS > 0.8 (fechou perto da máxima -- reversão capturada) OU
  stop de -5% (reaproveita a mesma ordem de grandeza do STOP_LOSS_PCT
  usado em V1/D1), o que vier primeiro.
"""

import pandas as pd

from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.data import fetch_ohlcv
from tradebot.indicators import ibs, sma
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor

TREND_SMA_PERIOD = 200
ENTRY_IBS_THRESHOLD = 0.2
EXIT_IBS_THRESHOLD = 0.8
STOP_LOSS_PCT = 0.05
CASH_FRACTION = 0.95


def generate_g1_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ibs"] = ibs(out["high"], out["low"], out["close"])
    out["trend_sma"] = sma(out["close"], TREND_SMA_PERIOD)
    out["uptrend"] = out["close"] > out["trend_sma"]

    action = pd.Series("HOLD", index=out.index)
    action[(out["ibs"] < ENTRY_IBS_THRESHOLD) & out["uptrend"]] = "BUY"
    action[out["ibs"] > EXIT_IBS_THRESHOLD] = "SELL"
    out["action"] = action
    return out


def run_backtest_g1(
    symbol: str,
    period: str = "10y",
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 10_000.0,
) -> BacktestResult:
    df = fetch_ohlcv(symbol, period=period, interval="1d", start=start, end=end)
    signals = generate_g1_signals(df)

    portfolio = Portfolio(starting_cash)
    equity_curve = []

    for i in range(1, len(signals)):
        prev = signals.iloc[i - 1]
        row = signals.iloc[i]
        price = float(row["open"])
        pos = portfolio.position(symbol)

        if pos.quantity > 0 and pos.avg_price > 0:
            if price <= pos.avg_price * (1 - STOP_LOSS_PCT):
                portfolio.sell(row.name, symbol, price, position_fraction=1.0)
            elif prev["action"] == "SELL":
                portfolio.sell(row.name, symbol, price, position_fraction=1.0)
        elif prev["action"] == "BUY" and pos.quantity == 0:
            portfolio.buy(row.name, symbol, price, CASH_FRACTION)

        equity_curve.append(portfolio.summary({symbol: float(row["close"])})["equity"])

    equity_series = pd.Series(equity_curve, index=signals.index[1:], name="equity")
    benchmark = starting_cash * (signals["close"] / signals["close"].iloc[0])
    benchmark = benchmark.loc[equity_series.index]

    metrics = _return_metrics(equity_series)
    metrics["max_drawdown_pct"] = _max_drawdown_pct(equity_series)
    benchmark_metrics = _return_metrics(benchmark)
    benchmark_metrics["max_drawdown_pct"] = _max_drawdown_pct(benchmark)

    round_trips = compute_round_trip_pnls(portfolio.fills)
    final_summary = portfolio.summary({symbol: float(signals["close"].iloc[-1])})
    final_summary["profit_factor"] = profit_factor(round_trips)
    final_summary["num_trades"] = len(round_trips)

    return BacktestResult(
        equity_curve=equity_series,
        benchmark_curve=benchmark,
        signals=signals,
        final_summary=final_summary,
        metrics=metrics,
        benchmark_metrics=benchmark_metrics,
    )


def print_g1_report(symbol: str, result: BacktestResult) -> None:
    m, b, s = result.metrics, result.benchmark_metrics, result.final_summary
    print(f"\n=== G1 (IBS + filtro de tendência) — {symbol} ===")
    print(f"Equity final:     {result.equity_curve.iloc[-1]:.2f}")
    print(f"Nº de trades:     {s['num_trades']}")
    print(f"Profit factor:    {s['profit_factor']:.2f}")
    print(f"\n{'Métrica':<18}{'G1':>12}{'Buy&Hold':>12}")
    for key, label in [("cagr_pct", "CAGR %"), ("max_drawdown_pct", "Max DD %"), ("sharpe", "Sharpe"), ("sortino", "Sortino"), ("calmar", "Calmar")]:
        print(f"{label:<18}{m[key]:>12.2f}{b[key]:>12.2f}")
