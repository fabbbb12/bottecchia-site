"""Roda F2 (cash-and-carry com filtro de funding mínimo) pra um símbolo
e período — ver tradebot/backtest_f2.py pra detalhes do modelo e das
regras pré-registradas.

Uso: python scripts/run_f2.py SYMBOL START END
Ex.:  python scripts/run_f2.py BTCUSDT 2025-09-01 2026-09-07
"""

import sys

from tradebot.backtest_f2 import print_f2_report, run_backtest_f2_symbol


def main():
    symbol, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
    result = run_backtest_f2_symbol(symbol, start=start, end=end)
    print_f2_report(symbol, result)


if __name__ == "__main__":
    main()
