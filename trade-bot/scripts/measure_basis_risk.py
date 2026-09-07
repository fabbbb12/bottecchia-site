"""Mede o risco de base do F1: compara o preço do próprio contrato
perpétuo (via `/fapi/v1/klines`, cobertura histórica completa) com o
preço à vista no mesmo instante, pra quantificar quanto as duas pernas
realmente se descolam -- em vez de assumir que elas se cancelam
perfeitamente, como o backtest F1 original faz. Não usa o `mark_price`
de `fetch_binance_funding_rates` porque esse campo vem vazio (NaN) em
boa parte do histórico mais antigo.

Uso: python scripts/measure_basis_risk.py SYMBOL START END
Ex.:  python scripts/measure_basis_risk.py BTCUSDT 2025-09-01 2026-09-07
"""

import sys

from tradebot.binance_data import fetch_binance_funding_rates, fetch_binance_futures_klines
from tradebot.data import fetch_ohlcv


def main():
    symbol, start, end = sys.argv[1], sys.argv[2], sys.argv[3]

    funding = fetch_binance_funding_rates(symbol, start=start, end=end)
    spot = fetch_ohlcv(symbol, interval="1h", start=start, end=end)
    perp = fetch_binance_futures_klines(symbol, interval="1h", start=start, end=end)

    spot_aligned = spot["close"].reindex(funding.index, method="ffill")
    perp_aligned = perp["close"].reindex(funding.index, method="ffill")
    basis_pct = (perp_aligned - spot_aligned) / spot_aligned * 100

    print(f"\n=== Risco de base — {symbol} ({start} a {end}) ===")
    print(f"Eventos de funding com par válido (spot+perp alinhados): {basis_pct.notna().sum()} / {len(basis_pct)}")
    print(basis_pct.describe())
    print(f"\nMaior descolamento positivo (perpétuo acima do à vista): {basis_pct.max():.3f}%")
    print(f"Maior descolamento negativo (perpétuo abaixo do à vista): {basis_pct.min():.3f}%")
    print(f"Descolamento médio absoluto: {basis_pct.abs().mean():.3f}%")


if __name__ == "__main__":
    main()
