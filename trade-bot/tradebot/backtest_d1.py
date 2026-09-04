"""D1 — Reversão à Média Pura por Faixa (Bandas de Bollinger). Primeira
hipótese da família D, focada em capturar o zigue-zague do preço
(comprar perto de mínimas locais, vender perto de máximas locais) em vez
de tentar pegar a tendência (famílias B/C) ou só reduzir exposição (V1).
Estruturalmente diferente das três: opera com muito mais frequência,
sem votar múltiplos indicadores (V1), sem seguir rompimento (B1) e sem
comparar ativos entre si (C1) — é reversão à média pura, um ativo por
vez, só com a banda de Bollinger como sinal.

Hipótese testada:

H0: comprar quando o preço toca a banda inferior de Bollinger (proxy
    objetivo e sem look-ahead pra "perto de uma mínima local") e vender
    quando toca a banda superior (proxy pra "perto de uma máxima
    local") não produz vantagem de retorno ajustado ao risco sobre
    buy-and-hold, mesmo operando com muito mais frequência que V1/B1/C1.
H1: produz vantagem — o zigue-zague de preço dentro de uma faixa é
    capturável de forma consistente e lucrativa depois de custos.

Regras de execução (decididas ANTES de rodar qualquer teste, mesma
disciplina anti-look-ahead de B1/C1: decide no fechamento de t, executa
no open de t+1 — nunca no mesmo candle da decisão):

- Entrada: `close[t] <= banda_inferior[t]`, só quando sem posição.
- Saída (alvo — "zigue-zague completo"): `close[t] >= banda_superior[t]`.
- Stop-loss: `close[t] <= preço_de_entrada * (1 - STOP_LOSS_PCT)` —
  protege contra um rompimento de baixa real (nem toda "mínima local"
  vira alta; sem isso o sistema ficaria comprando fundo de poço numa
  queda contínua).
- Sem trailing stop, sem RSI/MACD/Volume/Fibonacci/ADX/filtro de
  tendência — só a banda de Bollinger, testada isolada.

Parâmetros CONGELADOS antes de rodar qualquer teste:
- `BB_PERIOD = 20`, `BB_STD = 2.0` — mesmos padrões de
  `indicators.bollinger_bands`, já usados (e validados) como parte do
  voto da V1.
- `STOP_LOSS_PCT = 0.06` — mesmo valor congelado da V1, reaproveitado
  por consistência, não um número novo escolhido ad-hoc.

Sizing, custos e universo: idênticos à V1/B1 (fração fixa do caixa por
compra, mesma taxa/slippage, mesmos 11 ativos de US_WATCHLIST +
BR_WATCHLIST). Arquitetura: uma carteira independente por ativo, como
V1/B1 — não uma carteira cross-sectional como a C1.

RESULTADO: EXPERIMENTO REJEITADO (IS 2021-2023, OOS 2018-2020, walk-
forward 2012-2024 em 6 janelas). Melhora forte no IS (bate a V1 em 7/11
ativos em quase toda métrica), mas essa vantagem se INVERTE no OOS
(perde de V1 em retorno e Sharpe) — o mesmo padrão que já reprovou
V3/V5/V6, agora confirmado pela quarta vez com um mecanismo totalmente
diferente (banda de Bollinger em vez de Fibonacci/Volume), o que reforça
o achado consolidado em vez de ser um caso isolado. No agregado de 66
combinações janela×ativo do walk-forward, a D1 tem o melhor recorde de
drawdown do projeto (66/66, nunca perde do buy-and-hold) e edge marginal
de Sharpe/Calmar médio sobre a V1 — mas só bate a V1 em Sharpe em 3 das
6 janelas, sem um padrão de regime que explique a divisão. Ver
reports/D1_report.md para a análise completa.
"""

import logging

import numpy as np
import pandas as pd

from tradebot import indicators as ind
from tradebot.backtest import BacktestResult, _max_drawdown_pct, _return_metrics
from tradebot.comparison import print_v1_challenger_comparison
from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio, compute_round_trip_pnls, profit_factor

logger = logging.getLogger("tradebot.backtest_d1")

BB_PERIOD = 20
BB_STD = 2.0
STOP_LOSS_PCT = 0.06


def generate_d1_signals(
    df: pd.DataFrame,
    bb_period: int = BB_PERIOD,
    bb_std: float = BB_STD,
) -> pd.DataFrame:
    """OHLC + bandas de Bollinger + sinal de entrada (`close <= banda
    inferior`) e de saída-alvo (`close >= banda superior`). As bandas já
    são calculadas com janela móvel causal (`indicators.bollinger_bands`),
    sem usar informação futura."""
    out = df[["open", "high", "low", "close"]].copy()
    bb = ind.bollinger_bands(df["close"], period=bb_period, num_std=bb_std)
    out["lower_band"] = bb["lower"]
    out["mid_band"] = bb["mid"]
    out["upper_band"] = bb["upper"]
    out["entry_signal"] = out["close"] <= out["lower_band"]
    out["exit_signal"] = out["close"] >= out["upper_band"]
    return out


def run_backtest_d1(
    df: pd.DataFrame,
    symbol: str,
    strategy_cfg=None,  # não usado pela D1; aceito só para a mesma assinatura de compare()/run_walk_forward()
    bb_period: int = BB_PERIOD,
    bb_std: float = BB_STD,
    stop_loss_pct: float = STOP_LOSS_PCT,
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    signals = generate_d1_signals(df, bb_period=bb_period, bb_std=bb_std)
    portfolio = Portfolio(starting_cash, fee_rate=fee_rate, slippage_rate=slippage_rate)

    equity_curve = []
    exposed_days = []

    pending_action: str | None = None  # decidido no fechamento de t, executado no open de t+1
    entry_price: float | None = None

    for i in range(len(signals)):
        row = signals.iloc[i]
        timestamp = signals.index[i]
        open_price = float(row["open"])
        close_price = float(row["close"])
        pos = portfolio.position(symbol)

        # 1) Executa, no OPEN de hoje, a decisão tomada no FECHAMENTO de ontem.
        if pending_action == "BUY" and pos.quantity == 0:
            fill = portfolio.buy(timestamp, symbol, open_price, cash_fraction)
            if fill:
                entry_price = fill.price
        elif pending_action == "SELL" and pos.quantity > 0:
            portfolio.sell(timestamp, symbol, open_price, position_fraction=1.0)
            entry_price = None
        pending_action = None

        pos = portfolio.position(symbol)

        # 2) Decide, com informação disponível até o FECHAMENTO de hoje, o
        #    que fazer no open de amanhã — nunca no mesmo candle da decisão.
        if pos.quantity == 0:
            if bool(row["entry_signal"]):
                pending_action = "BUY"
        else:
            hit_target = bool(row["exit_signal"])
            hit_stop = entry_price is not None and close_price <= entry_price * (1 - stop_loss_pct)
            if hit_target or hit_stop:
                pending_action = "SELL"

        equity_curve.append(portfolio.equity({symbol: close_price}))
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


def run_multi_backtest_d1(
    symbols: list[str],
    strategy_cfg=None,  # não usado pela D1; aceito só para a mesma assinatura das outras run_multi_backtest_*
    bb_period: int = BB_PERIOD,
    bb_std: float = BB_STD,
    stop_loss_pct: float = STOP_LOSS_PCT,
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
            results[symbol] = run_backtest_d1(
                df,
                symbol,
                strategy_cfg,
                bb_period=bb_period,
                bb_std=bb_std,
                stop_loss_pct=stop_loss_pct,
                starting_cash=starting_cash,
                cash_fraction=cash_fraction,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
            )
        except Exception:
            logger.exception("Falha ao rodar backtest D1 para %s, pulando", symbol)
    return results


def print_v1_d1_comparison(v1_results: dict[str, BacktestResult], d1_results: dict[str, BacktestResult]) -> None:
    print_v1_challenger_comparison(v1_results, d1_results, challenger_label="D1")
