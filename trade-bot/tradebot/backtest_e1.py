"""E1 — Pairs Trading (arbitragem estatística, mercado neutro). Primeira
hipótese da família E, estruturalmente diferente de V/B/C/D: em vez de
apostar na direção de um ativo (comprado) ou de vários (rotação), aposta
na CONVERGÊNCIA da relação de preço entre DOIS ativos correlacionados —
compra o que ficou relativamente barato e vende a descoberto o que ficou
relativamente caro dentro do mesmo par, então não depende do mercado
subir pra dar lucro (mercado neutro). Só existe porque a carteira agora
suporta venda a descoberto (`Portfolio.short()`/`cover()`).

Hipótese testada:

H0: quando o spread de preço (log da razão) entre dois ativos do mesmo
    setor se afasta muito da média histórica recente, ele não tende a
    convergir de volta de forma lucrativa depois de custos.
H1: converge de forma consistente — arbitragem estatística clássica
    (Gatev, Goetzmann & Rouwenhorst, 2006) tem edge real nesse desenho.

Pares testados (escolhidos por lógica de setor — mesmo tipo de negócio,
concorrentes diretos, líquidos — ANTES de olhar qualquer correlação
calculada ou resultado de backtest, pra não cair em cherry-picking):
- `ITUB4.SA` / `BBDC4.SA` — os dois maiores bancos privados do Brasil,
  já presentes em `BR_WATCHLIST`.
- `XOM` / `CVX` — as duas maiores petroleiras integradas dos EUA
  (`CVX` é novo na lista; `XOM` já está em `US_DIVERSIFIED_WATCHLIST`).

Regras de execução (decididas ANTES de rodar qualquer teste, mesma
disciplina anti-look-ahead do resto do projeto: decide no fechamento de
`t`, executa as DUAS pernas no open de `t+1`):

- Spread: `log(close_A) - log(close_B)`. Z-score: `(spread -
  média_móvel) / desvio_padrão_móvel`, janela `LOOKBACK_DAYS = 60`
  (causal — só usa dados até o fechamento de `t`).
- Entrada: `|z-score| >= ENTRY_ZSCORE (2.0)`. Se z-score positivo (A
  caro em relação a B), vende A e compra B. Se negativo, o oposto.
- Saída (convergência): `|z-score| <= EXIT_ZSCORE (0.5)` — fecha as
  duas pernas.
- Stop (quebra estrutural do par): `|z-score| >= STOP_ZSCORE (4.0)` —
  fecha as duas pernas, o par pode ter deixado de fazer sentido
  economicamente.
- Sizing: cada perna usa uma fração fixa do caixa disponível no
  momento da entrada (`ENTRY_CASH_FRACTION_PER_LEG = 0.25` cada,
  aproximadamente neutro em dólar — não é exatamente 50/50 porque as
  duas pernas usam o caixa sequencialmente, mesma simplificação de
  sizing do resto do projeto). Mesmos custos (`fee_rate`/
  `slippage_rate`) do resto do projeto.

Benchmark: como a estratégia é desenhada pra ser neutra ao mercado, não
faz sentido compará-la a comprar-e-segurar os dois ativos (isso mediria
exposição direcional, não a qualidade da convergência) — o benchmark
aqui é uma referência de caixa parado (0%), deixado explícito no
relatório em vez de fingir uma comparação que não é justa.
"""

import logging

import numpy as np
import pandas as pd

from tradebot.backtest import _max_drawdown_pct, _return_metrics
from tradebot.backtest_c1 import PortfolioBacktestResult
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor

logger = logging.getLogger("tradebot.backtest_e1")

LOOKBACK_DAYS = 60
ENTRY_ZSCORE = 2.0
EXIT_ZSCORE = 0.5
STOP_ZSCORE = 4.0
ENTRY_CASH_FRACTION_PER_LEG = 0.25

PAIRS: list[tuple[str, str]] = [
    ("ITUB4.SA", "BBDC4.SA"),
    ("XOM", "CVX"),
]


def compute_spread_signals(
    df_a: pd.DataFrame, df_b: pd.DataFrame, lookback_days: int = LOOKBACK_DAYS
) -> pd.DataFrame:
    """Alinha os dois ativos pelas datas em comum e calcula o spread (log
    da razão) e o z-score móvel — tudo causal, sem usar dado futuro."""
    common_idx = df_a.index.intersection(df_b.index)
    out = pd.DataFrame(index=common_idx)
    out["open_a"] = df_a.loc[common_idx, "open"]
    out["close_a"] = df_a.loc[common_idx, "close"]
    out["open_b"] = df_b.loc[common_idx, "open"]
    out["close_b"] = df_b.loc[common_idx, "close"]
    spread = np.log(out["close_a"]) - np.log(out["close_b"])
    mean = spread.rolling(window=lookback_days, min_periods=lookback_days).mean()
    std = spread.rolling(window=lookback_days, min_periods=lookback_days).std()
    out["spread"] = spread
    out["zscore"] = (spread - mean) / std.replace(0, float("nan"))
    return out


def run_backtest_e1(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    symbol_a: str,
    symbol_b: str,
    lookback_days: int = LOOKBACK_DAYS,
    entry_zscore: float = ENTRY_ZSCORE,
    exit_zscore: float = EXIT_ZSCORE,
    stop_zscore: float = STOP_ZSCORE,
    entry_cash_fraction_per_leg: float = ENTRY_CASH_FRACTION_PER_LEG,
    starting_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> PortfolioBacktestResult:
    signals = compute_spread_signals(df_a, df_b, lookback_days=lookback_days)
    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)

    state: str | None = None  # None | "LONG_SPREAD" (comprado A, vendido B) | "SHORT_SPREAD" (vendido A, comprado B)
    pending: str | None = None  # ação decidida no fechamento de t, executada no open de t+1
    equity_curve = []
    exposed_days = []

    for i in range(len(signals)):
        row = signals.iloc[i]
        timestamp = signals.index[i]
        open_a, open_b = float(row["open_a"]), float(row["open_b"])

        # 1) Executa, no OPEN de hoje, a decisão tomada no fechamento de ontem.
        if pending == "ENTER_LONG_SPREAD":
            portfolio.buy(timestamp, symbol_a, open_a, entry_cash_fraction_per_leg)
            portfolio.short(timestamp, symbol_b, open_b, entry_cash_fraction_per_leg)
            state = "LONG_SPREAD"
        elif pending == "ENTER_SHORT_SPREAD":
            portfolio.short(timestamp, symbol_a, open_a, entry_cash_fraction_per_leg)
            portfolio.buy(timestamp, symbol_b, open_b, entry_cash_fraction_per_leg)
            state = "SHORT_SPREAD"
        elif pending == "EXIT":
            if state == "LONG_SPREAD":
                portfolio.sell(timestamp, symbol_a, open_a, position_fraction=1.0)
                portfolio.cover(timestamp, symbol_b, open_b, position_fraction=1.0)
            elif state == "SHORT_SPREAD":
                portfolio.cover(timestamp, symbol_a, open_a, position_fraction=1.0)
                portfolio.sell(timestamp, symbol_b, open_b, position_fraction=1.0)
            state = None
        pending = None

        # 2) Decide, com informação até o FECHAMENTO de hoje, o que fazer amanhã.
        z = row["zscore"]
        if not pd.isna(z):
            if state is None:
                if z >= entry_zscore:
                    pending = "ENTER_SHORT_SPREAD"  # A caro vs B -> vende A, compra B
                elif z <= -entry_zscore:
                    pending = "ENTER_LONG_SPREAD"  # A barato vs B -> compra A, vende B
            else:
                if abs(z) <= exit_zscore or abs(z) >= stop_zscore:
                    pending = "EXIT"

        prices = {symbol_a: float(row["close_a"]), symbol_b: float(row["close_b"])}
        equity_curve.append(portfolio.equity(prices))
        exposed_days.append(state is not None)

    equity_series = pd.Series(equity_curve, index=signals.index, name="equity")
    benchmark_curve = pd.Series([starting_cash] * len(signals), index=signals.index, name="benchmark")

    last_prices = {symbol_a: float(signals["close_a"].iloc[-1]), symbol_b: float(signals["close_b"].iloc[-1])}
    summary = portfolio.summary(last_prices)

    trades = []
    for symbol in (symbol_a, symbol_b):
        symbol_fills = [f for f in portfolio.fills if f.symbol == symbol]
        trades.extend(compute_round_trip_pnls(symbol_fills))

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

    return PortfolioBacktestResult(
        equity_curve=equity_series,
        benchmark_curve=benchmark_curve,
        final_summary=summary,
        metrics=metrics,
        benchmark_metrics=benchmark_metrics,
        symbols=[symbol_a, symbol_b],
    )


def run_multi_backtest_e1(
    pairs: list[tuple[str, str]] = PAIRS,
    period: str = "1y",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, PortfolioBacktestResult]:
    results: dict[str, PortfolioBacktestResult] = {}
    for symbol_a, symbol_b in pairs:
        label = f"{symbol_a}/{symbol_b}"
        try:
            df_a = fetch_ohlcv(symbol_a, period=period, interval=interval, start=start, end=end)
            df_b = fetch_ohlcv(symbol_b, period=period, interval=interval, start=start, end=end)
            results[label] = run_backtest_e1(
                df_a,
                df_b,
                symbol_a,
                symbol_b,
                lookback_days=lookback_days,
                starting_cash=starting_cash,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest E1 para o par %s, pulando", label)
    return results


def print_e1_report(pair_label: str, result: PortfolioBacktestResult) -> None:
    s = result.final_summary
    m = result.metrics

    print(f"\n=== E1 (Pairs Trading) — {pair_label} (SIMULADO / PAPER, mercado neutro) ===")
    print(f"Caixa final:          {s['cash']:.2f}")
    print(f"Patrimônio final:     {s['equity']:.2f}")
    print(f"Resultado (PnL):      {s['pnl']:.2f} ({s['pnl_pct']:.2f}%)")
    print("Benchmark: caixa parado (0%) — estratégia é desenhada pra ser neutra ao mercado,")
    print("comparar com buy-and-hold mediria exposição direcional, não qualidade da convergência.")

    print(f"\n{'Métrica':<22}{'E1':>14}")
    print("-" * 36)
    print(f"{'CAGR':<22}{m['cagr_pct']:>13.2f}%")
    print(f"{'Máx. drawdown':<22}{m['max_drawdown_pct']:>13.2f}%")
    print(f"{'Sharpe':<22}{m['sharpe']:>14.2f}")
    print(f"{'Sortino':<22}{m['sortino']:>14.2f}")
    print(f"{'Calmar':<22}{m['calmar']:>14.2f}")

    pf_str = "inf" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:.2f}"
    print(f"\nProfit factor:        {pf_str}")
    print(f"Nº de operações (trades completos): {m['num_trades']}")
    print(f"Nº de ordens (compras/vendas/shorts/covers): {s['num_fills']}")
    print(f"% do tempo com posição aberta:      {m['time_exposed_pct']:.1f}%")
    print(f"Turnover (volume negociado / caixa inicial): {m['turnover']:.2f}x")
    print(f"Custos totais (taxas):               {m['total_fees']:.2f}")
    print(f"Posições em aberto:                  {s['positions']}")


def print_multi_e1_report(results: dict[str, PortfolioBacktestResult]) -> None:
    for pair_label, result in results.items():
        print_e1_report(pair_label, result)
