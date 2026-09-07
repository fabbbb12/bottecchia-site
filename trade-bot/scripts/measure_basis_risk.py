"""Mede o risco de base do F1: compara o mark_price do perpétuo (usado
no funding) com o preço à vista no mesmo instante, pra quantificar
quanto as duas pernas realmente se descolam -- em vez de assumir que
elas se cancelam perfeitamente, como o backtest atual faz.

Uso: python scripts/measure_basis_risk.py SYMBOL START END
Ex.:  python scripts/measure_basis_risk.py BTCUSDT 2025-09-01 2026-09-07
"""

import sys

from tradebot.binance_data import fetch_binance_funding_rates
from tradebot.data import fetch_ohlcv


def main():
    symbol, start, end = sys.argv[1], sys.argv[2], sys.argv[3]

    funding = fetch_binance_funding_rates(symbol, start=start, end=end)
    spot = fetch_ohlcv(symbol, interval="1h", start=start, end=end)

    spot_aligned = spot["close"].reindex(funding.index, method="ffill")
    basis_pct = (funding["mark_price"] - spot_aligned) / spot_aligned * 100

    print(f"\n=== Risco de base — {symbol} ({start} a {end}) ===")
    print(f"Eventos de funding com par válido (spot alinhado): {basis_pct.notna().sum()} / {len(basis_pct)}")
    print(basis_pct.describe())
    print(f"\nMaior descolamento positivo (perpétuo acima do à vista): {basis_pct.max():.3f}%")
    print(f"Maior descolamento negativo (perpétuo abaixo do à vista): {basis_pct.min():.3f}%")
    print(f"Descolamento médio absoluto: {basis_pct.abs().mean():.3f}%")


if __name__ == "__main__":
    main()
