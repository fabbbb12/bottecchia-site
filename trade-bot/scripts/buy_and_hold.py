"""Calcula o retorno de comprar-e-segurar (buy-and-hold) no mercado à
vista da Binance pra um símbolo/período -- pra comparar de forma justa
contra F2 (ou qualquer outra estratégia da família F), já que F2 usa
o à vista como uma das pernas mas nunca foi comparado contra ele
diretamente nos relatórios.

Uso: python scripts/buy_and_hold.py SYMBOL START END
Ex.:  python scripts/buy_and_hold.py BTCUSDT 2021-01-01 2023-01-01
"""

import sys

from tradebot.data import fetch_ohlcv


def main():
    symbol, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
    df = fetch_ohlcv(symbol, interval="1d", start=start, end=end)
    first = float(df["close"].iloc[0])
    last = float(df["close"].iloc[-1])
    ret_pct = (last - first) / first * 100

    print(f"\n=== Buy-and-hold — {symbol} ({start} a {end}) ===")
    print(f"Preço inicial: {first:.2f}")
    print(f"Preço final:   {last:.2f}")
    print(f"Retorno:       {ret_pct:+.2f}%")


if __name__ == "__main__":
    main()
