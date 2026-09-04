"""Interface de linha de comando do bot.

    python -m tradebot backtest --symbol AAPL --period 1y --interval 1d --chart
    python -m tradebot backtest --market br --period 1y
    python -m tradebot backtest --market all --period 1y
    python -m tradebot backtest --market all --start 2018-01-01 --end 2020-01-01  # fora da amostra
    python -m tradebot walkforward --market all --start 2012-01-01 --end 2024-01-01 --window-years 2
    python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01  # V1 vs V2 vs B&H
    python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01 --challenger v3  # V1 vs V3 (Fibo)
    python -m tradebot fib-placebo --market all --start 2018-01-01 --end 2020-01-01  # V3 (Fibo) vs V4 (placebo)
    python -m tradebot live --symbol PETR4.SA --interval 1d --poll-seconds 3600 --chart

Tudo aqui é PAPER TRADING (simulado). Não há execução de ordens reais.
"""

import argparse
import logging
from pathlib import Path

from tradebot.backtest import print_report, print_summary_table, run_backtest, run_multi_backtest
from tradebot.backtest_b1 import BREAKOUT_PERIOD, run_multi_backtest_b1
from tradebot.backtest_c1 import MOMENTUM_LOOKBACK_DAYS, TOP_K, print_c1_report, run_backtest_c1
from tradebot.backtest_c3 import SEED, print_c1_c3_comparison, run_backtest_c3
from tradebot.backtest_d1 import BB_PERIOD, BB_STD, STOP_LOSS_PCT, run_multi_backtest_d1
from tradebot.backtest_v2 import run_multi_backtest_v2
from tradebot.backtest_v3 import run_multi_backtest_v3
from tradebot.backtest_v4 import run_multi_backtest_v4
from tradebot.backtest_v5 import run_multi_backtest_v5
from tradebot.backtest_v6 import run_multi_backtest_v6
from tradebot.charts import plot_signals
from tradebot.comparison import print_fibonacci_placebo_test, print_v1_challenger_comparison
from tradebot.data import fetch_ohlcv
from tradebot.live import run_loop
from tradebot.markets import resolve_symbols
from tradebot.strategy import StrategyConfig
from tradebot.walkforward import print_walk_forward_report, run_walk_forward

logger = logging.getLogger("tradebot.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tradebot",
        description="Bot de análise técnica e execução simulada (paper trading).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cash", type=float, default=10_000.0, help="Caixa inicial simulado")
    common.add_argument("--cash-fraction", type=float, default=0.5, help="Fração do caixa usada em cada compra")
    common.add_argument("--interval", default="1d", help="Ex: 1m, 5m, 1h, 1d")
    common.add_argument("--chart", action="store_true", help="Salva gráfico(s) PNG com preço, indicadores e sinais")
    common.add_argument("--chart-dir", default="charts", help="Pasta onde salvar os gráficos")

    backtest_p = sub.add_parser("backtest", parents=[common], help="Roda a estratégia sobre dados históricos")
    backtest_p.add_argument("--symbol", help="Um único símbolo, ex: AAPL, PETR4.SA")
    backtest_p.add_argument("--symbols", help="Lista separada por vírgula, ex: AAPL,MSFT,PETR4.SA")
    backtest_p.add_argument("--market", choices=["us", "br", "all"], help="Usa uma watchlist pronta (EUA, Bovespa ou ambas)")
    backtest_p.add_argument("--period", default="1y", help="Ex: 1mo, 6mo, 1y, 5y (ignorado se --start for informado)")
    backtest_p.add_argument("--start", help="Data inicial fixa (AAAA-MM-DD) — use para testes fora da amostra")
    backtest_p.add_argument("--end", help="Data final fixa (AAAA-MM-DD), opcional — padrão é hoje")

    wf_p = sub.add_parser(
        "walkforward",
        parents=[common],
        help="Roda a estratégia congelada em várias janelas de tempo sequenciais (sem ajustar parâmetros)",
    )
    wf_p.add_argument("--symbol", help="Um único símbolo, ex: AAPL, PETR4.SA")
    wf_p.add_argument("--symbols", help="Lista separada por vírgula, ex: AAPL,MSFT,PETR4.SA")
    wf_p.add_argument("--market", choices=["us", "br", "all"], help="Usa uma watchlist pronta (EUA, Bovespa ou ambas)")
    wf_p.add_argument("--start", required=True, help="Início do período total (AAAA-MM-DD)")
    wf_p.add_argument("--end", required=True, help="Fim do período total (AAAA-MM-DD)")
    wf_p.add_argument("--window-years", type=float, default=2.0, help="Tamanho de cada janela, em anos")
    wf_p.add_argument(
        "--challenger",
        choices=["v2", "v3", "v4", "v5", "v6", "b1", "d1"],
        default=None,
        help="Opcional: também roda o walk-forward dessa versão/família, além da V1 (relatórios separados)",
    )
    wf_p.add_argument(
        "--breakout-period",
        type=int,
        default=BREAKOUT_PERIOD,
        help="Só usado com --challenger b1: janela do rompimento (padrão 20; teste de sensibilidade usa 10/20/40)",
    )

    compare_p = sub.add_parser(
        "compare",
        parents=[common],
        help="Compara V1 (congelada) vs uma versão experimental vs Buy&Hold no mesmo período",
    )
    compare_p.add_argument("--symbol", help="Um único símbolo, ex: AAPL, PETR4.SA")
    compare_p.add_argument("--symbols", help="Lista separada por vírgula, ex: AAPL,MSFT,PETR4.SA")
    compare_p.add_argument("--market", choices=["us", "br", "all"], help="Usa uma watchlist pronta (EUA, Bovespa ou ambas)")
    compare_p.add_argument("--period", default="1y", help="Ex: 1mo, 6mo, 1y, 5y (ignorado se --start for informado)")
    compare_p.add_argument("--start", help="Data inicial fixa (AAAA-MM-DD)")
    compare_p.add_argument("--end", help="Data final fixa (AAAA-MM-DD), opcional")
    compare_p.add_argument(
        "--challenger",
        choices=["v2", "v3", "v4", "v5", "v6", "b1", "d1"],
        default="v2",
        help=(
            "v2 = reentrada antecipada (rejeitada); v3 = filtro de Fibonacci (rejeitada); "
            "v4 = placebo aleatório; v5 = Fibonacci como position sizing (rejeitada); "
            "v6 = filtro de Volume Relativo; b1 = rompimento puro (família B, trend following); "
            "d1 = reversão à média pura por banda de Bollinger (família D, zigue-zague)"
        ),
    )
    compare_p.add_argument(
        "--breakout-period",
        type=int,
        default=BREAKOUT_PERIOD,
        help="Só usado com --challenger b1: janela do rompimento (padrão 20; teste de sensibilidade usa 10/20/40)",
    )

    placebo_p = sub.add_parser(
        "fib-placebo",
        parents=[common],
        help="Teste decisivo: V3 (filtro de Fibonacci) vs V4 (placebo aleatório) vs V1",
    )
    placebo_p.add_argument("--symbol", help="Um único símbolo, ex: AAPL, PETR4.SA")
    placebo_p.add_argument("--symbols", help="Lista separada por vírgula, ex: AAPL,MSFT,PETR4.SA")
    placebo_p.add_argument("--market", choices=["us", "br", "all"], help="Usa uma watchlist pronta (EUA, Bovespa ou ambas)")
    placebo_p.add_argument("--period", default="1y", help="Ex: 1mo, 6mo, 1y, 5y (ignorado se --start for informado)")
    placebo_p.add_argument("--start", help="Data inicial fixa (AAAA-MM-DD)")
    placebo_p.add_argument("--end", help="Data final fixa (AAAA-MM-DD), opcional")

    c1_p = sub.add_parser(
        "c1", parents=[common], help="Família C: C1, momentum duplo cross-sectional (rotação de carteira)"
    )
    c1_p.add_argument("--symbols", help="Lista separada por vírgula, ex: AAPL,MSFT,PETR4.SA")
    c1_p.add_argument("--market", choices=["us", "br", "all"], help="Usa uma watchlist pronta (EUA, Bovespa ou ambas)")
    c1_p.add_argument("--period", default="1y", help="Ex: 1mo, 6mo, 1y, 5y (ignorado se --start for informado)")
    c1_p.add_argument("--start", help="Data inicial fixa (AAAA-MM-DD)")
    c1_p.add_argument("--end", help="Data final fixa (AAAA-MM-DD), opcional")
    c1_p.add_argument(
        "--momentum-lookback",
        type=int,
        default=MOMENTUM_LOOKBACK_DAYS,
        help="Janela de retorno acumulado usada no ranking, em pregões (padrão 252, ~12 meses)",
    )
    c1_p.add_argument(
        "--top-k", type=int, default=TOP_K, help="Quantos ativos manter na carteira a cada rebalanceamento (padrão 3)"
    )

    c1_placebo_p = sub.add_parser(
        "c1-placebo",
        parents=[common],
        help="Teste decisivo: C1 (momentum) vs C3 (placebo aleatório) — mesma mecânica, seleção diferente",
    )
    c1_placebo_p.add_argument("--symbols", help="Lista separada por vírgula, ex: AAPL,MSFT,PETR4.SA")
    c1_placebo_p.add_argument(
        "--market", choices=["us", "br", "all"], help="Usa uma watchlist pronta (EUA, Bovespa ou ambas)"
    )
    c1_placebo_p.add_argument("--period", default="1y", help="Ex: 1mo, 6mo, 1y, 5y (ignorado se --start for informado)")
    c1_placebo_p.add_argument("--start", help="Data inicial fixa (AAAA-MM-DD)")
    c1_placebo_p.add_argument("--end", help="Data final fixa (AAAA-MM-DD), opcional")
    c1_placebo_p.add_argument("--top-k", type=int, default=TOP_K, help="Quantos ativos manter na carteira (padrão 3)")
    c1_placebo_p.add_argument(
        "--momentum-lookback",
        type=int,
        default=MOMENTUM_LOOKBACK_DAYS,
        help="Janela de retorno acumulado usada no ranking da C1, em pregões (padrão 252)",
    )
    c1_placebo_p.add_argument("--seed", type=int, default=SEED, help="Semente do sorteio aleatório da C3 (padrão 42)")

    live_p = sub.add_parser("live", parents=[common], help="Loop de paper trading em quase-tempo-real")
    live_p.add_argument("--symbol", required=True, help="Um único símbolo, ex: AAPL, PETR4.SA")
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
        symbols = resolve_symbols(args.market, args.symbols)
        if args.symbol:
            symbols = [args.symbol] + [s for s in symbols if s != args.symbol]
        if not symbols:
            parser.error("informe --symbol, --symbols ou --market (us/br/all)")

        chart_dir = Path(args.chart_dir) if args.chart else None

        if len(symbols) == 1:
            df = fetch_ohlcv(symbols[0], period=args.period, interval=args.interval, start=args.start, end=args.end)
            result = run_backtest(
                df,
                symbols[0],
                strategy_cfg,
                starting_cash=args.cash,
                cash_fraction=args.cash_fraction,
            )
            print_report(result, symbols[0])
            if chart_dir is not None:
                path = plot_signals(result.signals, symbols[0], chart_dir / f"{symbols[0]}.png", title_suffix="backtest")
                print(f"Gráfico salvo em: {path}")
        else:
            results = run_multi_backtest(
                symbols,
                strategy_cfg,
                period=args.period,
                interval=args.interval,
                start=args.start,
                end=args.end,
                starting_cash=args.cash,
                cash_fraction=args.cash_fraction,
            )
            print_summary_table(results)
            if chart_dir is not None:
                for symbol, result in results.items():
                    path = plot_signals(result.signals, symbol, chart_dir / f"{symbol}.png", title_suffix="backtest")
                    print(f"Gráfico salvo em: {path}")

    elif args.command == "walkforward":
        symbols = resolve_symbols(args.market, args.symbols)
        if args.symbol:
            symbols = [args.symbol] + [s for s in symbols if s != args.symbol]
        if not symbols:
            parser.error("informe --symbol, --symbols ou --market (us/br/all)")

        wf = run_walk_forward(
            symbols,
            strategy_cfg,
            start=args.start,
            end=args.end,
            window_years=args.window_years,
            interval=args.interval,
            starting_cash=args.cash,
            cash_fraction=args.cash_fraction,
        )
        print("\n" + "#" * 78)
        print("# V1 (congelada)")
        print("#" * 78)
        print_walk_forward_report(wf)

        if args.challenger:
            challenger_fns = {
                "v2": run_multi_backtest_v2,
                "v3": run_multi_backtest_v3,
                "v4": run_multi_backtest_v4,
                "v5": run_multi_backtest_v5,
                "v6": run_multi_backtest_v6,
                "b1": run_multi_backtest_b1,
                "d1": run_multi_backtest_d1,
            }
            challenger_kwargs = {"breakout_period": args.breakout_period} if args.challenger == "b1" else None
            logger.info("V1 concluída. Iniciando walk-forward de %s...", args.challenger.upper())
            wf_challenger = run_walk_forward(
                symbols,
                strategy_cfg,
                start=args.start,
                end=args.end,
                window_years=args.window_years,
                interval=args.interval,
                starting_cash=args.cash,
                cash_fraction=args.cash_fraction,
                backtest_fn=challenger_fns[args.challenger],
                backtest_kwargs=challenger_kwargs,
            )
            print("\n" + "#" * 78)
            print(f"# {args.challenger.upper()}")
            print("#" * 78)
            print_walk_forward_report(wf_challenger)

    elif args.command == "compare":
        symbols = resolve_symbols(args.market, args.symbols)
        if args.symbol:
            symbols = [args.symbol] + [s for s in symbols if s != args.symbol]
        if not symbols:
            parser.error("informe --symbol, --symbols ou --market (us/br/all)")

        v1_results = run_multi_backtest(
            symbols,
            strategy_cfg,
            period=args.period,
            interval=args.interval,
            start=args.start,
            end=args.end,
            starting_cash=args.cash,
            cash_fraction=args.cash_fraction,
        )
        challenger_fns = {
            "v2": run_multi_backtest_v2,
            "v3": run_multi_backtest_v3,
            "v4": run_multi_backtest_v4,
            "v5": run_multi_backtest_v5,
            "v6": run_multi_backtest_v6,
            "b1": run_multi_backtest_b1,
            "d1": run_multi_backtest_d1,
        }
        challenger_fn = challenger_fns[args.challenger]
        extra_kwargs = {"breakout_period": args.breakout_period} if args.challenger == "b1" else {}
        challenger_results = challenger_fn(
            symbols,
            strategy_cfg,
            period=args.period,
            interval=args.interval,
            start=args.start,
            end=args.end,
            starting_cash=args.cash,
            cash_fraction=args.cash_fraction,
            **extra_kwargs,
        )
        print_v1_challenger_comparison(v1_results, challenger_results, challenger_label=args.challenger.upper())

    elif args.command == "fib-placebo":
        symbols = resolve_symbols(args.market, args.symbols)
        if args.symbol:
            symbols = [args.symbol] + [s for s in symbols if s != args.symbol]
        if not symbols:
            parser.error("informe --symbol, --symbols ou --market (us/br/all)")

        common_kwargs = dict(
            period=args.period,
            interval=args.interval,
            start=args.start,
            end=args.end,
            starting_cash=args.cash,
            cash_fraction=args.cash_fraction,
        )
        v1_results = run_multi_backtest(symbols, strategy_cfg, **common_kwargs)
        v3_results = run_multi_backtest_v3(symbols, strategy_cfg, **common_kwargs)
        v4_results = run_multi_backtest_v4(symbols, strategy_cfg, **common_kwargs)
        print_fibonacci_placebo_test(v1_results, v3_results, v4_results)

    elif args.command == "c1":
        symbols = resolve_symbols(args.market, args.symbols)
        if not symbols:
            parser.error("informe --symbols ou --market (us/br/all)")
        result = run_backtest_c1(
            symbols,
            period=args.period,
            interval=args.interval,
            start=args.start,
            end=args.end,
            starting_cash=args.cash,
            momentum_lookback_days=args.momentum_lookback,
            top_k=args.top_k,
        )
        print_c1_report(result)

    elif args.command == "c1-placebo":
        symbols = resolve_symbols(args.market, args.symbols)
        if not symbols:
            parser.error("informe --symbols ou --market (us/br/all)")
        common_kwargs = dict(
            period=args.period,
            interval=args.interval,
            start=args.start,
            end=args.end,
            starting_cash=args.cash,
            top_k=args.top_k,
        )
        c1_result = run_backtest_c1(symbols, momentum_lookback_days=args.momentum_lookback, **common_kwargs)
        c3_result = run_backtest_c3(symbols, seed=args.seed, **common_kwargs)
        print_c1_report(c1_result, label="C1 (momentum)")
        print_c1_report(c3_result, label="C3 (placebo aleatório)")
        print_c1_c3_comparison(c1_result, c3_result)

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
            chart_dir=Path(args.chart_dir) if args.chart else None,
        )


if __name__ == "__main__":
    main()
