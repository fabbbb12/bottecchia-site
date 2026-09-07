"""Varre uma lista de perpétuos e mostra a média móvel de funding
(mesma janela/lookback do filtro de F2) de cada um -- pra achar
rapidamente se algum já está acima do limiar de entrada, sem esperar
o bootstrap normal de 30 dias em cada símbolo um por um.

Uso: python scripts/scan_funding.py SYMBOL1 SYMBOL2 ...
Ex.:  python scripts/scan_funding.py DOGEUSDT 1000PEPEUSDT WIFUSDT SUIUSDT
"""

import sys

from tradebot.backtest_f2 import LOOKBACK_EVENTS, MIN_FUNDING_RATE_THRESHOLD
from tradebot.binance_data import fetch_binance_funding_rates


def main():
    symbols = sys.argv[1:]
    print(f"Limiar de entrada do F2: {MIN_FUNDING_RATE_THRESHOLD*100:.5f}% por evento (media movel de {LOOKBACK_EVENTS} eventos)\n")
    for symbol in symbols:
        try:
            df = fetch_binance_funding_rates(symbol, period="35d")
            trailing = df["funding_rate"].tail(LOOKBACK_EVENTS)
            avg = trailing.mean()
            status = "ACIMA DO LIMIAR -- entraria" if avg >= MIN_FUNDING_RATE_THRESHOLD else "abaixo -- ficaria de fora"
            print(f"{symbol}: media movel = {avg*100:+.5f}%/evento -> {status}")
        except Exception as e:
            print(f"{symbol}: erro -> {e}")


if __name__ == "__main__":
    main()
