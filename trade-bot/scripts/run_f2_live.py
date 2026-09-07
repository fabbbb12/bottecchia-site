"""Roda um ciclo do paper trading ao vivo de F2 pra um símbolo -- busca
os eventos de funding novos desde a última chamada, decide/aplica o
sinal, e salva o estado. Chame isso periodicamente (ideal: a cada ~8h,
alinhado com o ciclo de funding da Binance -- ex. via Agendador de
Tarefas do Windows) -- rodar com menos frequência também funciona, só
processa todos os eventos acumulados de uma vez.

Uso: python scripts/run_f2_live.py SYMBOL
Ex.:  python scripts/run_f2_live.py BTCUSDT
"""

import logging
import sys

from tradebot.live_f2 import print_status, run_once

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    symbol = sys.argv[1]
    result = run_once(symbol)
    print_status(symbol, result)


if __name__ == "__main__":
    main()
