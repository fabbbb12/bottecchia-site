"""C1 — Momentum Duplo (cross-sectional). Primeira hipótese da família C,
estruturalmente diferente das famílias V (voto/reversão à média, um ativo
por vez) e B (rompimento/tendência, um ativo por vez).

Por que mudar de família depois de 7 experimentos rejeitados (V2-V6, B1):
todos tentaram temporizar UM ativo isolado contra o buy-and-hold DESSE
MESMO ativo, numa cesta de 11 ações de alta qualidade (mega caps
americanas + blue chips brasileiras) durante um dos mercados de alta
seculares mais fortes da história recente (2012-2024, liderado por big
tech). Nesse cenário, timing de ativo único quase nunca bate
buy-and-hold — não é falha das estratégias testadas, é a troca
estrutural esperada (menos dor, menos retorno). Mais uma variante de
filtro em cima do mesmo desenho (comprar/vender um ativo por vez) ia
just confirmar esse padrão de novo, sem ensinar nada novo.

C1 muda o desenho de forma estrutural: em vez de decidir comprar/vender
UM ativo isolado, decide QUAIS ativos da cesta segurar, comparando-os
ENTRE SI (momentum cross-sectional / relativo) — uma das poucas classes
de estratégia sistemática com evidência acadêmica e prática de edge
persistente e replicado em múltiplos mercados e períodos (Jegadeesh &
Titman, 1993; Antonacci, "Dual Momentum", 2014), o que justifica gastar
mais uma rodada de teste rigoroso em vez de mais uma variante de V ou B.

Hipótese testada:

H0: selecionar mensalmente os ativos com maior retorno acumulado dos
    últimos 12 meses (exigindo retorno absoluto positivo, senão a vaga
    fica em caixa) não produz vantagem de retorno ajustado ao risco
    sobre manter a cesta inteira igualmente ponderada (buy-and-hold da
    cesta, sem rotação).
H1: produz vantagem — momentum cross-sectional é um efeito real nesse
    universo, não um artefato do período.

Regras de execução (decididas ANTES de rodar qualquer teste):

- Decisão de rebalanceamento no ÚLTIMO pregão de cada mês-calendário,
  usando o retorno acumulado até o FECHAMENTO desse dia (nunca usa
  informação do dia seguinte). Execução das trocas no OPEN do primeiro
  pregão do mês seguinte — nunca no mesmo candle da decisão (mesma
  disciplina de timing da B1).
- Momentum absoluto (filtro de caixa): só é candidato quem tiver retorno
  acumulado do período > 0%. Se sobrarem vagas depois desse filtro, elas
  ficam em caixa — não são preenchidas por um ativo com momentum
  negativo só para "completar o time".
- Momentum relativo: dentre os candidatos (retorno > 0%), entram os
  TOP_K com maior retorno acumulado, igualmente ponderados (fração fixa
  de `1/TOP_K` do caixa disponível em cada entrada — mesma filosofia de
  sizing simples da V1/B1, não é rebalanceamento para peso exato: um
  ativo que já estava na carteira e continua entre os TOP_K não é
  vendido e recomprado, só é mantido).

Parâmetros CONGELADOS antes de rodar qualquer teste:
- `MOMENTUM_LOOKBACK_DAYS = 252` (~12 meses de pregão — a janela mais
  citada e replicada na literatura de momentum e usada no "Dual
  Momentum" clássico de Antonacci).
- Rebalanceamento mensal, ancorado no calendário (não é um nº fixo de
  dias de pregão).
- `TOP_K = 3` (de até 11 ativos do universo).

Custos e universo: idênticos aos das famílias V e B (mesma
`fee_rate`/`slippage_rate`, mesmos 11 ativos de US_WATCHLIST +
BR_WATCHLIST) — só o desenho da estratégia muda, não o resto do
experimento.

Diferença de arquitetura (importante): C1 não roda uma carteira
independente por ativo como V1-V6/B1 — é UMA carteira só, alocada entre
os ativos do universo ao longo do tempo. O benchmark correspondente não
é o buy-and-hold de um ativo isolado: é o buy-and-hold da CESTA inteira
igualmente ponderada desde o primeiro dia, sem nunca rebalancear —
comparação justa para uma estratégia de rotação. Os calendários de
pregão dos EUA e da Bovespa não coincidem exatamente (feriados
diferentes); os painéis de preço são alinhados pela união das datas com
forward-fill (nunca com dado futuro) para cobrir esses poucos dias de
descompasso — uma simplificação deliberada, documentada aqui.

RESULTADO: PROMISSORA (walk-forward 2012-2024, 6 janelas de 2 anos). Não
bate o buy-and-hold da cesta de forma robusta (perde em CAGR/Sortino/
Calmar na maioria das janelas), mas é o melhor resultado do projeto até
agora: bate a V1 em Sharpe em 5/6 janelas e em CAGR em 4/6, mantendo a
mesma vantagem de drawdown (6/6 janelas). O padrão de quando ganha/perde
do B&H é explicável (perde em janelas de alta forte e em linha reta,
onde ficar de fora prejudica; ganha em janelas com correções relevantes
no meio do caminho) — diferente da inversão sem explicação de regime
vista em V3/V5/V6/B1. Ver reports/C1_report.md para a análise completa
e a recomendação de próximo passo (testar TOP_K maior como C2, ainda
não implementado, pendente de confirmação).
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from tradebot.backtest import _max_drawdown_pct, _return_metrics
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor

logger = logging.getLogger("tradebot.backtest_c1")

MOMENTUM_LOOKBACK_DAYS = 252
TOP_K = 3


@dataclass
class PortfolioBacktestResult:
    equity_curve: pd.Series
    benchmark_curve: pd.Series
    final_summary: dict
    metrics: dict
    benchmark_metrics: dict
    symbols: list[str]


def _build_panels(
    symbols: list[str],
    period: str = "1y",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baixa OHLCV de cada símbolo e monta dois painéis alinhados no mesmo
    calendário (união de datas, forward-fill só com dado passado — nunca
    futuro — pra cobrir feriados que não coincidem entre EUA e Bovespa):
    `closes` (fechamento, usado no ranking de momentum) e `opens`
    (abertura, usada pra executar as trocas no dia seguinte à decisão)."""
    close_series = {}
    open_series = {}
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, period=period, interval=interval, start=start, end=end)
        except Exception:
            logger.exception("Falha ao baixar %s pra C1, excluindo do universo desta rodada", symbol)
            continue
        close_series[symbol] = df["close"]
        open_series[symbol] = df["open"]

    closes = pd.DataFrame(close_series).sort_index().ffill()
    opens = pd.DataFrame(open_series).sort_index().ffill()
    return closes, opens


def _rebalance_dates(index: pd.DatetimeIndex) -> set:
    """Último pregão de cada mês-calendário: dia em que a decisão de
    rebalanceamento é tomada (com o fechamento desse dia), executada no
    open do primeiro pregão do mês seguinte. Descobrir que um dia é "o
    último pregão do mês" olhando a data do próximo pregão no índice não
    vaza nenhum preço futuro — é só estrutura de calendário, conhecida de
    antemão."""
    dates = set()
    for i in range(len(index) - 1):
        if (index[i].year, index[i].month) != (index[i + 1].year, index[i + 1].month):
            dates.add(index[i])
    if len(index):
        dates.add(index[-1])
    return dates


def _target_holdings(
    closes: pd.DataFrame,
    decision_idx: int,
    symbols: list[str],
    momentum_lookback_days: int,
    top_k: int,
) -> list[str]:
    """Ranking de momentum decidido com informação até o FECHAMENTO do
    próprio dia da decisão (`decision_idx`) — a execução é que só acontece
    no dia seguinte, não a informação usada pra decidir. Só entram ativos
    com retorno acumulado do período > 0% (filtro de momentum absoluto);
    os `top_k` melhores dentre esses formam a carteira-alvo."""
    if decision_idx - momentum_lookback_days < 0:
        return []
    momentum = {}
    for symbol in symbols:
        past = closes[symbol].iloc[decision_idx - momentum_lookback_days]
        current = closes[symbol].iloc[decision_idx]
        if pd.isna(past) or pd.isna(current) or past <= 0:
            continue
        ret = current / past - 1
        if ret > 0:
            momentum[symbol] = ret
    ranked = sorted(momentum, key=momentum.get, reverse=True)
    return ranked[:top_k]


def run_backtest_c1_from_panels(
    closes: pd.DataFrame,
    opens: pd.DataFrame,
    starting_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    momentum_lookback_days: int = MOMENTUM_LOOKBACK_DAYS,
    top_k: int = TOP_K,
) -> PortfolioBacktestResult:
    """Motor da C1 operando direto sobre painéis de preço já alinhados
    (`closes`/`opens`, mesmo índice, uma coluna por símbolo) — separado de
    `run_backtest_c1` pra ser testável com dados sintéticos, sem rede."""
    if closes.empty:
        raise ValueError("Painel de preços vazio — nenhum dado disponível pra C1.")
    symbols = list(closes.columns)

    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)
    entry_cash_fraction = 1.0 / top_k
    rebalance_dates = _rebalance_dates(closes.index)

    pending_target: list[str] | None = None
    equity_curve = []
    exposed_days = []

    for i, timestamp in enumerate(closes.index):
        # 1) Executa, no OPEN de hoje, o rebalanceamento decidido no fechamento de ontem.
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

        # 2) Decide, com informação até o FECHAMENTO de hoje, o rebalanceamento
        #    a executar amanhã — nunca no mesmo candle da decisão.
        if timestamp in rebalance_dates:
            pending_target = _target_holdings(closes, i, symbols, momentum_lookback_days, top_k)

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


def run_backtest_c1(
    symbols: list[str],
    period: str = "1y",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    momentum_lookback_days: int = MOMENTUM_LOOKBACK_DAYS,
    top_k: int = TOP_K,
) -> PortfolioBacktestResult:
    closes, opens = _build_panels(symbols, period=period, interval=interval, start=start, end=end)
    return run_backtest_c1_from_panels(
        closes,
        opens,
        starting_cash=starting_cash,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
        momentum_lookback_days=momentum_lookback_days,
        top_k=top_k,
    )


def print_c1_report(result: PortfolioBacktestResult) -> None:
    s = result.final_summary
    m = result.metrics
    bm = result.benchmark_metrics

    bench_start = result.benchmark_curve.iloc[0]
    bench_end = result.benchmark_curve.iloc[-1]
    bench_pnl_pct = (bench_end - bench_start) / bench_start * 100 if bench_start else 0.0

    print(f"\n=== C1 (Momentum Duplo) — carteira rotativa entre {len(result.symbols)} ativos (SIMULADO / PAPER) ===")
    print(f"Ativos: {', '.join(result.symbols)}")
    print(f"Caixa final:          {s['cash']:.2f}")
    print(f"Patrimônio final:     {s['equity']:.2f}")
    print(f"Resultado (PnL):      {s['pnl']:.2f} ({s['pnl_pct']:.2f}%)")
    print(f"Buy-and-hold da cesta (igual peso, sem rebalancear): {bench_pnl_pct:.2f}%")
    diff = s["pnl_pct"] - bench_pnl_pct
    comparativo = "supera" if diff > 0 else "fica atrás d" if diff < 0 else "empata com"
    print(f"=> C1 {comparativo}o buy-and-hold da cesta em {diff:+.2f} pontos percentuais")

    print(f"\n{'Métrica':<22}{'C1':>14}{'B&H cesta':>14}")
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
    print(f"% do tempo com pelo menos 1 posição aberta: {m['time_exposed_pct']:.1f}%")
    print(f"Turnover (volume negociado / caixa inicial): {m['turnover']:.2f}x")
    print(f"Custos totais (taxas):               {m['total_fees']:.2f}")
    print(f"Posições em aberto:                  {s['positions']}")
