"""C3 — Placebo aleatório para a C1, isolado da C1.

A C1 (momentum cross-sectional) mostrou uma vantagem real de Sharpe
sobre a V1, mas fica a mesma dúvida que já apareceu antes no projeto
(V3 vs V4): esse ganho vem de informação genuína no ranking de momentum,
ou só do mecanismo em si — rotação mensal entre um subconjunto menor da
cesta (menos concentração, giro periódico), não importa qual critério
escolhe os ativos?

A C3 responde isso: reaproveita a MESMA mecânica de rebalanceamento
mensal, `TOP_K`, sizing e custos da C1 — a ÚNICA diferença é que, em vez
de rankear por retorno acumulado de 12 meses, sorteia aleatoriamente
`TOP_K` ativos da cesta a cada rebalanceamento (sem olhar preço, retorno
ou qualquer indicador). Sem filtro de momentum absoluto — o sorteio não
tem como "saber" se um ativo teria retorno positivo, então fica sempre
100% alocado nos `TOP_K` sorteados (a C1, por comparação, às vezes deixa
vaga em caixa quando menos de `TOP_K` ativos passam no filtro).

Se a C3 chegar perto do resultado da C1, o ranking de momentum não
acrescenta informação — só girar entre um subconjunto menor da cesta já
faz o trabalho. Se a C1 continuar batendo a C3 de forma clara e
consistente, o momentum está fazendo algo específico, não é só efeito
de concentração/rotação.

Parâmetros CONGELADOS antes de rodar qualquer teste:
- `SEED = 42` — mesmo valor usado no placebo da V1 (V4), reaproveitado
  por consistência, decidido antes de ver qualquer resultado.
- Mesmo `TOP_K = 3`, mesmo calendário de rebalanceamento (último pregão
  do mês, execução no open do mês seguinte), mesmo sizing (`1/TOP_K` do
  caixa por entrada), mesmos custos e universo da C1.
"""

import logging

import numpy as np
import pandas as pd

from tradebot.backtest import _max_drawdown_pct, _return_metrics
from tradebot.backtest_c1 import TOP_K, PortfolioBacktestResult, _build_panels, _rebalance_dates
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor

logger = logging.getLogger("tradebot.backtest_c3")

SEED = 42


def run_backtest_c3_from_panels(
    closes: pd.DataFrame,
    opens: pd.DataFrame,
    starting_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    top_k: int = TOP_K,
    seed: int = SEED,
) -> PortfolioBacktestResult:
    """Motor da C3 operando direto sobre painéis de preço já alinhados —
    separado de `run_backtest_c3` pra ser testável com dados sintéticos,
    sem rede (mesmo padrão de `backtest_c1.run_backtest_c1_from_panels`)."""
    if closes.empty:
        raise ValueError("Painel de preços vazio — nenhum dado disponível pra C3.")
    symbols = list(closes.columns)

    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)
    entry_cash_fraction = 1.0 / top_k
    rebalance_dates = _rebalance_dates(closes.index)
    rng = np.random.default_rng(seed)

    pending_target: list[str] | None = None
    equity_curve = []
    exposed_days = []

    for i, timestamp in enumerate(closes.index):
        # 1) Executa, no OPEN de hoje, o rebalanceamento sorteado no fechamento de ontem.
        if pending_target is not None:
            held = [s for s, pos in portfolio.positions.items() if pos.quantity > 0]
            for symbol in held:
                if symbol not in pending_target:
                    open_price = opens[symbol].iloc[i]
                    if not pd.isna(open_price):
                        portfolio.sell(timestamp, symbol, float(open_price), position_fraction=1.0)
            for symbol in pending_target:
                pos = portfolio.position(symbol)
                if pos.quantity == 0:
                    open_price = opens[symbol].iloc[i]
                    if not pd.isna(open_price):
                        portfolio.buy(timestamp, symbol, float(open_price), entry_cash_fraction)
            pending_target = None

        # 2) No dia de rebalanceamento, sorteia (sem olhar preço/retorno) os
        #    TOP_K ativos que serão comprados no open de amanhã.
        if timestamp in rebalance_dates:
            available = [s for s in symbols if not pd.isna(closes[s].iloc[i])]
            k = min(top_k, len(available))
            pending_target = list(rng.choice(available, size=k, replace=False)) if k > 0 else []

        prices_today = {s: float(closes[s].iloc[i]) for s in symbols if not pd.isna(closes[s].iloc[i])}
        equity_curve.append(portfolio.equity(prices_today))
        exposed_days.append(any(pos.quantity > 0 for pos in portfolio.positions.values()))

    equity_series = pd.Series(equity_curve, index=closes.index, name="equity")

    first_valid = {s: closes[s].dropna().iloc[0] for s in symbols if closes[s].notna().any()}
    bh_qty = {s: (starting_cash / len(first_valid)) / first_valid[s] for s in first_valid} if first_valid else {}
    benchmark_values = []
    for i in range(len(closes)):
        total = sum(qty * float(closes[s].iloc[i]) for s, qty in bh_qty.items() if not pd.isna(closes[s].iloc[i]))
        benchmark_values.append(total)
    benchmark_curve = pd.Series(benchmark_values, index=closes.index, name="benchmark")

    last_prices = {s: float(closes[s].iloc[-1]) for s in symbols if not pd.isna(closes[s].iloc[-1])}
    summary = portfolio.summary(last_prices)

    trades = []
    for symbol in symbols:
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
        symbols=symbols,
    )


def run_backtest_c3(
    symbols: list[str],
    period: str = "1y",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    top_k: int = TOP_K,
    seed: int = SEED,
) -> PortfolioBacktestResult:
    closes, opens = _build_panels(symbols, period=period, interval=interval, start=start, end=end)
    return run_backtest_c3_from_panels(
        closes,
        opens,
        starting_cash=starting_cash,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
        top_k=top_k,
        seed=seed,
    )


def print_c1_c3_comparison(c1_result: PortfolioBacktestResult, c3_result: PortfolioBacktestResult) -> None:
    """C1 (momentum) vs C3 (placebo aleatório) — mesmo espírito da
    comparação V3 vs V4, adaptada pra estratégia de carteira única
    (não dá pra reaproveitar `comparison.py`, que espera um dicionário
    por símbolo)."""
    c1_pnl = c1_result.final_summary["pnl_pct"]
    c3_pnl = c3_result.final_summary["pnl_pct"]
    m1, m3 = c1_result.metrics, c3_result.metrics

    print("\n=== C1 (momentum) vs C3 (placebo aleatório) ===")
    header = f"{'Métrica':<20}{'C1 (momentum)':>16}{'C3 (aleatório)':>16}"
    print(header)
    print("-" * len(header))
    print(f"{'Retorno':<20}{c1_pnl:>15.2f}%{c3_pnl:>15.2f}%")
    print(f"{'CAGR':<20}{m1['cagr_pct']:>15.2f}%{m3['cagr_pct']:>15.2f}%")
    print(f"{'Máx. drawdown':<20}{m1['max_drawdown_pct']:>15.2f}%{m3['max_drawdown_pct']:>15.2f}%")
    print(f"{'Sharpe':<20}{m1['sharpe']:>16.2f}{m3['sharpe']:>16.2f}")
    print(f"{'Sortino':<20}{m1['sortino']:>16.2f}{m3['sortino']:>16.2f}")
    print(f"{'Calmar':<20}{m1['calmar']:>16.2f}{m3['calmar']:>16.2f}")
    print(
        "\nSe a C1 não vencer a C3 (o placebo) claramente, a vantagem de momentum "
        "não tem relação com o ranking — é só efeito de girar entre um subconjunto "
        "menor da cesta."
    )
