"""F1 — Cash-and-Carry (arbitragem de taxa de financiamento). Primeira
hipótese da família F, estruturalmente diferente de tudo já testado
(V/B/C/D/E): não aposta em direção de preço nem em convergência entre
dois ativos — explora um mecanismo estrutural do próprio mercado de
derivativos cripto.

Contratos perpétuos (o produto mais negociado em cripto) não têm data
de vencimento — pra manter o preço do contrato colado no preço à vista,
a cada 8 horas quem está do lado "consenso" (normalmente comprado, em
mercado de cripto historicamente mais otimista) paga uma taxa de
financiamento pra quem está do lado oposto. Isso é o que sustenta o
"cash-and-carry": comprar o ativo à vista + vender o mesmo tamanho no
perpétuo (posição neutra em dólar, sem aposta de direção) e receber
essa taxa repetidamente, sempre que ela for positiva.

Diferente de V1-E1, aqui NÃO estamos testando se dá pra prever preço —
estamos testando se um mecanismo estrutural do mercado (o desequilíbrio
histórico entre compradores e vendedores em cripto) produziu, na
prática, uma taxa de financiamento positiva o bastante, com
consistência suficiente, pra compensar os custos.

Hipótese testada:

H0: a taxa de financiamento histórica do perpétuo não é positiva o
    bastante, nem consistente o bastante, pra produzir retorno líquido
    positivo depois de custos de entrada.
H1: produz retorno líquido positivo e com volatilidade baixa (já que a
    posição é neutra em dólar — o resultado não deveria vir do preço
    subir ou cair, e sim só do fluxo de pagamentos).

Regras (decididas ANTES de rodar qualquer teste):
- Entrada ÚNICA no início do período: compra o ativo à vista + vende o
  mesmo valor nocional do perpétuo (posição sempre neutra em dólar,
  100% do capital usado, sem alavancagem adicional). Não há reentrada
  nem giro — a posição fica montada o período inteiro.
- A cada eventos de funding (a cada 8h, conforme os dados reais da
  Binance Futures), aplica `PnL = nocional * taxa_de_financiamento`
  (recebe quando positiva, paga quando negativa — estamos do lado
  vendido no perpétuo).
- Nocional recalculado a cada evento como o capital atual (composto) —
  os pagamentos de financiamento reinvestem na mesma posição.

SIMPLIFICAÇÃO IMPORTANTE, documentada com honestidade: este modelo só
contabiliza o fluxo de pagamentos de financiamento — ignora o "risco de
base" (a diferença entre o preço do perpétuo e o preço à vista pode
variar e gerar ganho/perda adicional além do funding) e ignora risco de
liquidação da perna vendida no perpétuo (numa conta de margem real, um
movimento de preço brusco pode forçar o fechamento da posição vendida
antes da hora, mesmo com a perna comprada compensando no papel). Não é
"dinheiro sem risco" — é uma simplificação de primeira ordem pra testar
se o mecanismo de financiamento, isoladamente, tem sido positivo o
bastante historicamente.
"""

import logging

import numpy as np
import pandas as pd

from tradebot.backtest import _max_drawdown_pct, _return_metrics
from tradebot.binance_data import fetch_binance_funding_rates

logger = logging.getLogger("tradebot.backtest_f1")

ENTRY_FEE_RATE = 0.001  # aplicado uma vez, nas duas pernas (à vista + perpétuo), na entrada


def run_backtest_f1(
    funding: pd.DataFrame,
    starting_cash: float = 10_000.0,
    entry_fee_rate: float = ENTRY_FEE_RATE,
) -> dict:
    """`funding` é o DataFrame devolvido por `fetch_binance_funding_rates`
    (colunas `funding_rate`, `mark_price`, um evento a cada ~8h)."""
    if funding.empty:
        raise ValueError("Histórico de funding rate vazio — não dá pra rodar F1.")

    # custo de entrada único: comprar à vista + vender o perpétuo (duas pernas)
    capital = starting_cash * (1 - 2 * entry_fee_rate)

    equity_curve = [capital]
    total_funding_received = 0.0
    positive_events = 0
    negative_events = 0

    for rate in funding["funding_rate"]:
        payment = capital * rate  # recebido (rate>0) ou pago (rate<0), do lado vendido no perpétuo
        capital += payment
        total_funding_received += payment
        if rate > 0:
            positive_events += 1
        elif rate < 0:
            negative_events += 1
        equity_curve.append(capital)

    initial_timestamp = funding.index[0] - (funding.index[1] - funding.index[0] if len(funding) > 1 else pd.Timedelta(hours=8))
    equity_series = pd.Series(equity_curve, index=[initial_timestamp] + list(funding.index), name="equity")

    metrics = _return_metrics(equity_series)
    metrics["max_drawdown_pct"] = _max_drawdown_pct(equity_series)

    total_events = positive_events + negative_events
    positive_rate_pct = (positive_events / total_events * 100) if total_events else 0.0

    return {
        "equity_curve": equity_series,
        "metrics": metrics,
        "final_capital": capital,
        "pnl": capital - starting_cash,
        "pnl_pct": (capital - starting_cash) / starting_cash * 100 if starting_cash else 0.0,
        "num_funding_events": total_events,
        "positive_events": positive_events,
        "negative_events": negative_events,
        "positive_rate_pct": positive_rate_pct,
        "mean_funding_rate_pct": float(funding["funding_rate"].mean() * 100),
        "total_funding_received": total_funding_received,
    }


def run_backtest_f1_symbol(
    symbol: str,
    period: str = "1y",
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 10_000.0,
    entry_fee_rate: float = ENTRY_FEE_RATE,
) -> dict:
    funding = fetch_binance_funding_rates(symbol, period=period, start=start, end=end)
    return run_backtest_f1(funding, starting_cash=starting_cash, entry_fee_rate=entry_fee_rate)


def print_f1_report(symbol: str, result: dict) -> None:
    m = result["metrics"]
    print(f"\n=== F1 (Cash-and-Carry / Funding Rate) — {symbol} perpétuo (SIMULADO / PAPER) ===")
    print("Posição neutra em dólar (comprado à vista + vendido no perpétuo) — não aposta em direção de preço.")
    print(f"Capital final:        {result['final_capital']:.2f}")
    print(f"Resultado (PnL):      {result['pnl']:.2f} ({result['pnl_pct']:.2f}%)")
    print(f"Nº de eventos de funding (a cada ~8h): {result['num_funding_events']}")
    print(f"Eventos positivos/negativos: {result['positive_events']} / {result['negative_events']}")
    print(f"% de eventos com funding positivo: {result['positive_rate_pct']:.1f}%")
    print(f"Taxa de funding média por evento:  {result['mean_funding_rate_pct']:.4f}%")
    print(f"\nCAGR:                 {m['cagr_pct']:.2f}%")
    print(f"Máx. drawdown:        {m['max_drawdown_pct']:.2f}%")
    print(f"Sharpe:               {m['sharpe']:.2f}")
    print(f"Sortino:              {m['sortino']:.2f}")
    print(f"Calmar:               {m['calmar']:.2f}")
    print(
        "\nAVISO: modelo ignora risco de base (perpétuo vs à vista) e risco de liquidação "
        "da perna vendida — não é 'sem risco', é o fluxo de funding isolado."
    )
