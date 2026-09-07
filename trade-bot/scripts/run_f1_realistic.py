"""Roda F1-realista (funding + marcação do risco de base) pra um símbolo
e período — ver tradebot/backtest_f1_realistic.py pra detalhes do modelo.

Uso: python scripts/run_f1_realistic.py SYMBOL START END
Ex.:  python scripts/run_f1_realistic.py BTCUSDT 2025-09-01 2026-09-07
"""

import sys

from tradebot.backtest_f1_realistic import print_f1_realistic_report, run_backtest_f1_realistic_symbol


def main():
    symbol, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
    result = run_backtest_f1_realistic_symbol(symbol, start=start, end=end)
    print_f1_realistic_report(symbol, result)


if __name__ == "__main__":
    main()
