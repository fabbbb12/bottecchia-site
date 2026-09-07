"""F1-realista — mesma estratégia de F1 (cash-and-carry), mas marcando a
posição a mercado a cada evento de funding em vez de só contabilizar o
fluxo de funding isoladamente. `backtest_f1.py` documenta desde o início
que ignora risco de base (descolamento entre o preço à vista e o do
perpétuo) — este módulo fecha essa lacuna, usando dado medido de verdade
(ver `scripts/measure_basis_risk.py`) em vez de deixar como suposição.
Usa o preço do próprio contrato perpétuo (`/fapi/v1/klines`), não o
`mark_price` de `fetch_binance_funding_rates` -- esse campo vem vazio
(NaN) em boa parte do histórico mais antigo da Binance.

Modelo: entrada única (comprar à vista + vender o mesmo nocional no
perpétuo), sem giro depois — igual ao F1 original. A cada evento de
funding, o retorno do período agora tem DOIS componentes, não um:

1. `r_funding` = taxa de financiamento do evento (igual ao F1 original).
2. `r_basis`   = variação do descolamento perpétuo-vs-à-vista desde o
   evento anterior, com sinal invertido (estamos vendidos no perpétuo —
   se o perpétuo sobe mais que o à vista, a perna vendida perde essa
   diferença, mesmo que o funding tenha sido positivo no mesmo período).

Isso é uma aproximação de primeira ordem (ignora efeitos de segunda
ordem entre os dois componentes, e ainda não modela risco de
liquidação/margem — só o risco de base), mas já é estritamente mais
realista que o F1 original, que tratava a posição como perfeitamente
neutra o tempo todo.
"""

import pandas as pd

from tradebot.backtest import _max_drawdown_pct, _return_metrics
from tradebot.binance_data import fetch_binance_futures_klines, fetch_binance_funding_rates
from tradebot.data import fetch_ohlcv

ENTRY_FEE_RATE = 0.001


def run_backtest_f1_realistic(
    funding: pd.DataFrame,
    spot: pd.DataFrame,
    perp: pd.DataFrame,
    starting_cash: float = 10_000.0,
    entry_fee_rate: float = ENTRY_FEE_RATE,
) -> dict:
    """`perp` é o preço do próprio contrato perpétuo (`fetch_binance_futures_klines`)
    -- usado em vez do `mark_price` de `fetch_binance_funding_rates`, que
    vem vazio (NaN) em boa parte do histórico mais antigo."""
    if funding.empty:
        raise ValueError("Histórico de funding rate vazio — não dá pra rodar F1-realista.")

    spot_aligned = spot["close"].reindex(funding.index, method="ffill")
    perp_aligned = perp["close"].reindex(funding.index, method="ffill")
    basis_pct = (perp_aligned - spot_aligned) / spot_aligned  # fração, não %
    basis_pct = basis_pct.dropna()
    funding = funding.loc[basis_pct.index]

    capital = starting_cash * (1 - 2 * entry_fee_rate)
    equity_curve = [capital]
    prev_basis = basis_pct.iloc[0]

    for ts, rate in funding["funding_rate"].items():
        r_funding = rate
        r_basis = -(basis_pct.loc[ts] - prev_basis)  # vendido no perpétuo: alta do basis = perda
        prev_basis = basis_pct.loc[ts]
        capital *= (1 + r_funding + r_basis)
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
        "num_events": len(funding),
    }


def run_backtest_f1_realistic_symbol(
    symbol: str,
    start: str,
    end: str,
    starting_cash: float = 10_000.0,
    entry_fee_rate: float = ENTRY_FEE_RATE,
) -> dict:
    funding = fetch_binance_funding_rates(symbol, start=start, end=end)
    spot = fetch_ohlcv(symbol, interval="1h", start=start, end=end)
    perp = fetch_binance_futures_klines(symbol, interval="1h", start=start, end=end)
    return run_backtest_f1_realistic(funding, spot, perp, starting_cash=starting_cash, entry_fee_rate=entry_fee_rate)


def print_f1_realistic_report(symbol: str, result: dict) -> None:
    m = result["metrics"]
    print(f"\n=== F1-realista (funding + marcação do risco de base) — {symbol} ===")
    print(f"Capital final:        {result['final_capital']:.2f}")
    print(f"Resultado (PnL):      {result['pnl']:.2f} ({result['pnl_pct']:.2f}%)")
    print(f"Nº de eventos:        {result['num_events']}")
    print(f"\nCAGR:                 {m['cagr_pct']:.2f}%")
    print(f"Máx. drawdown:        {m['max_drawdown_pct']:.2f}%")
    print(f"Sharpe:               {m['sharpe']:.2f}")
    print(f"Sortino:              {m['sortino']:.2f}")
    print(f"Calmar:               {m['calmar']:.2f}")
    print("\nAinda ignora risco de liquidação/margem — só fecha a lacuna do risco de base.")
