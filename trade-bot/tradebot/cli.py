"""Interface de linha de comando do bot.

    python -m tradebot backtest --symbol BTC-USD --period 1y --interval 1d
    python -m tradebot live --symbol BTC-USD --interval 1h --poll-seconds 3600

Tudo aqui é PAPER TRADING (simulado). Não há execução de ordens reais.
"""

import argparse
import logging
from pathlib import Path

from tradebot.backtest import print_report, run_backtest
from tradebot.data import fetch_ohlcv
from tradebot.live import run_loop
from tradebot.strategy import StrategyConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tradebot",
        description="Bot de análise técnica e execução simulada (paper trading).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--symbol", required=True, help="Ex: BTC-USD, PETR4.SA, AAPL")
    common.add_argument("--cash", type=float, default=10_000.0, help="Caixa inicial simulado")
    common.add_argument("--cash-fraction", type=float, default=0.5, help="Fração do caixa usada em cada compra")
    common.add_argument("--interval", default="1d", help="Ex: 1m, 5m, 1h, 1d")

    backtest_p = sub.add_parser("backtest", parents=[common], help="Roda a estratégia sobre dados históricos")
    backtest_p.add_argument("--period", default="1y", help="Ex: 1mo, 6mo, 1y, 5y")

    live_p = sub.add_parser("live", parents=[common], help="Loop de paper trading em quase-tempo-real")
    live_p.add_argument("--period", default="6mo", help="Janela de histórico usada para calcular indicadores")
    live_p.add_argument("--poll-seconds", type=int, default=3600, help="Intervalo entre checagens")
    live_p.add_argument("--iterations", type=int, default=None, help="Limite de ciclos (útil para testes)")
    live_p.add_argument("--state-dir", default="state", help="Pasta onde salvar o estado da carteira simulada")

    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    strategy_cfg = StrategyConfig()

    if args.command == "backtest":
        df = fetch_ohlcv(args.symbol, period=args.period, interval=args.interval)
        result = run_backtest(
            df,
            args.symbol,
            strategy_cfg,
            starting_cash=args.cash,
            cash_fraction=args.cash_fraction,
        )
        print_report(result, args.symbol)

    elif args.command == "live":
        print("AVISO: modo 'live' continua sendo simulado (paper trading). Nenhuma ordem real é enviada.")
        run_loop(
            args.symbol,
            strategy_cfg,
            starting_cash=args.cash,
            period=args.period,
            interval=args.interval,
            cash_fraction=args.cash_fraction,
            poll_seconds=args.poll_seconds,
            state_dir=Path(args.state_dir),
            max_iterations=args.iterations,
        )


if __name__ == "__main__":
    main()
