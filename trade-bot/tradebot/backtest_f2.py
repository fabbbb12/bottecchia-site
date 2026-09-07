"""F2 — F1 com filtro de intensidade mínima de funding. Nasce direto da
conclusão de F1-realista: o edge do cash-and-carry não é constante, ele
só sobrevive ao risco de base quando a taxa de funding está forte o
bastante (Sharpe realista caiu de 5.37, na janela de funding forte, pra
0.07, na janela de funding fraco — mesmo modelo, mesma disciplina,
resultado completamente diferente conforme o regime).

Hipótese: se a gente só entra na posição quando o funding recente está
acima de um piso mínimo (e fica em caixa, sem risco, quando não está),
o Sharpe deveria ficar mais estável entre janelas fortes e fracas, em
vez de depender de sorte do regime vigente.

Regras decididas ANTES de rodar qualquer teste (mesma disciplina de
V1-F1):
- Sinal calculado a cada evento de funding: média móvel da taxa de
  funding das últimas `LOOKBACK_EVENTS` janelas (90 eventos, ~30 dias
  em candles de 8h) — só usando dado já conhecido até o evento atual,
  sem olhar o futuro (decide no evento N, aplica a partir do evento
  N+1, mesmo padrão anti-lookahead do resto do projeto).
- Entra/mantém a posição (cash-and-carry, marcado a mercado como em
  F1-realista) se essa média móvel estiver `>= MIN_FUNDING_RATE_THRESHOLD`
  (0.01% por evento — ordem de grandeza que separou a janela forte
  (~0.02-0.03%/evento) da fraca (~0.003%/evento) em F1, escolhido antes
  de ver qualquer resultado de F2, não ajustado depois).
- Abaixo do limiar, fica 100% em caixa (sem funding, sem risco de
  base) até a média voltar a subir.
- Toda transição de estado (caixa->posição ou posição->caixa) paga a
  taxa de entrada/saída de novo (0.1% por perna) — trocar de estado tem
  custo real, não é de graça.
"""

import pandas as pd

from tradebot.backtest import _max_drawdown_pct, _return_metrics
from tradebot.binance_data import fetch_binance_funding_rates, fetch_binance_futures_klines
from tradebot.data import fetch_ohlcv

ENTRY_FEE_RATE = 0.001
LOOKBACK_EVENTS = 90
MIN_FUNDING_RATE_THRESHOLD = 0.0001  # 0.01% por evento de 8h


def run_backtest_f2(
    funding: pd.DataFrame,
    spot: pd.DataFrame,
    perp: pd.DataFrame,
    starting_cash: float = 10_000.0,
    entry_fee_rate: float = ENTRY_FEE_RATE,
    lookback_events: int = LOOKBACK_EVENTS,
    min_funding_rate_threshold: float = MIN_FUNDING_RATE_THRESHOLD,
) -> dict:
    if funding.empty:
        raise ValueError("Histórico de funding rate vazio — não dá pra rodar F2.")

    spot_aligned = spot["close"].reindex(funding.index, method="ffill")
    perp_aligned = perp["close"].reindex(funding.index, method="ffill")
    basis_pct = (perp_aligned - spot_aligned) / spot_aligned
    basis_pct = basis_pct.dropna()
    funding = funding.loc[basis_pct.index]

    trailing_avg_funding = funding["funding_rate"].rolling(lookback_events, min_periods=lookback_events).mean()
    # decide no evento N usando a média até N, aplica a partir do evento N+1 (sem lookahead)
    signal = (trailing_avg_funding >= min_funding_rate_threshold).shift(1).fillna(False)

    capital = starting_cash
    in_position = False
    equity_curve = [capital]
    prev_basis = None
    num_entries = 0
    events_in_position = 0

    for ts in funding.index:
        want_in = bool(signal.loc[ts])

        if want_in and not in_position:
            capital *= (1 - 2 * entry_fee_rate)
            in_position = True
            num_entries += 1
            prev_basis = basis_pct.loc[ts]
        elif not want_in and in_position:
            capital *= (1 - 2 * entry_fee_rate)
            in_position = False
            prev_basis = None

        if in_position:
            r_funding = funding["funding_rate"].loc[ts]
            r_basis = -(basis_pct.loc[ts] - prev_basis)
            prev_basis = basis_pct.loc[ts]
            capital *= (1 + r_funding + r_basis)
            events_in_position += 1

        equity_curve.append(capital)

    initial_timestamp = funding.index[0] - (
        funding.index[1] - funding.index[0] if len(funding) > 1 else pd.Timedelta(hours=8)
    )
    equity_series = pd.Series(equity_curve, index=[initial_timestamp] + list(funding.index), name="equity")

    metrics = _return_metrics(equity_series)
    metrics["max_drawdown_pct"] = _max_drawdown_pct(equity_series)

    return {
        "equity_curve": equity_series,
        "metrics": metrics,
        "final_capital": capital,
        "pnl": capital - starting_cash,
        "pnl_pct": (capital - starting_cash) / starting_cash * 100 if starting_cash else 0.0,
        "num_entries": num_entries,
        "events_in_position": events_in_position,
        "num_events": len(funding),
        "pct_time_in_position": events_in_position / len(funding) * 100 if len(funding) else 0.0,
    }


def run_backtest_f2_symbol(
    symbol: str,
    start: str,
    end: str,
    starting_cash: float = 10_000.0,
    entry_fee_rate: float = ENTRY_FEE_RATE,
    lookback_events: int = LOOKBACK_EVENTS,
    min_funding_rate_threshold: float = MIN_FUNDING_RATE_THRESHOLD,
) -> dict:
    funding = fetch_binance_funding_rates(symbol, start=start, end=end)
    spot = fetch_ohlcv(symbol, interval="1h", start=start, end=end)
    perp = fetch_binance_futures_klines(symbol, interval="1h", start=start, end=end)
    return run_backtest_f2(
        funding,
        spot,
        perp,
        starting_cash=starting_cash,
        entry_fee_rate=entry_fee_rate,
        lookback_events=lookback_events,
        min_funding_rate_threshold=min_funding_rate_threshold,
    )


def print_f2_report(symbol: str, result: dict) -> None:
    m = result["metrics"]
    print(f"\n=== F2 (cash-and-carry com filtro de funding mínimo) — {symbol} ===")
    print(f"Capital final:        {result['final_capital']:.2f}")
    print(f"Resultado (PnL):      {result['pnl']:.2f} ({result['pnl_pct']:.2f}%)")
    print(f"Nº de eventos:        {result['num_events']}")
    print(f"Nº de entradas (transições caixa->posição): {result['num_entries']}")
    print(f"% do tempo com posição montada: {result['pct_time_in_position']:.1f}%")
    print(f"\nCAGR:                 {m['cagr_pct']:.2f}%")
    print(f"Máx. drawdown:        {m['max_drawdown_pct']:.2f}%")
    print(f"Sharpe:               {m['sharpe']:.2f}")
    print(f"Sortino:              {m['sortino']:.2f}")
    print(f"Calmar:               {m['calmar']:.2f}")
