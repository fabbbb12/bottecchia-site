"""CLI da Fase 1 do Polymarket Alpha Lab — Seção 20.

    python main.py collect
    python main.py normalize
    python main.py scan
    python main.py backtest
    python main.py report

Nenhum comando aqui move dinheiro real. O objetivo é só responder se
existe edge de arbitragem interna, com dados reais e sem look-ahead.
"""

import argparse
import logging

from arbitrage.scan import scan_multi_outcome, scan_yes_no
from backtest.engine import resolve_all_pending
from collectors.client import PolymarketClient
from collectors.markets import collect_markets
from config.settings import load_api_settings
from db import DEFAULT_DB_PATH, get_connection, init_db
from fees import load_fee_config
from reports.generator import write_report

logger = logging.getLogger("polymarket_alpha")

DEFAULT_REPORT_PATH = "reports/phase_1_report.md"


def cmd_collect(args: argparse.Namespace) -> None:
    init_db(args.db)
    conn = get_connection(args.db)
    try:
        client = PolymarketClient(load_api_settings())
        total = collect_markets(conn, client, max_pages=args.max_pages)
        print(f"Mercados coletados/atualizados: {total}")
        print(
            "AVISO: order book, preços e trades por token não são coletados automaticamente "
            "por este comando (evita milhares de chamadas por rodada) — use "
            "collectors.orderbook/prices/trades diretamente para os tokens de interesse."
        )
    finally:
        conn.close()


def cmd_normalize(args: argparse.Namespace) -> None:
    print(
        "Não há etapa separada de normalização: os coletores já gravam dados normalizados "
        "diretamente nas tabelas finais (ver normalization/normalize.py e a nota de design em "
        "arbitrage/scan.py). Este comando existe só por completude da interface pedida na spec."
    )


def cmd_scan(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    try:
        fee_config = load_fee_config()
        settings = load_api_settings()
        if not settings.verified_against_docs:
            print(
                "AVISO: config/settings.yaml diz verified_against_docs=false -- os endpoints e "
                "o mapeamento de campos usados na coleta não foram confirmados contra a "
                "documentação oficial. Resultados do scan podem estar incorretos até isso ser revisado."
            )
        yes_no_count = scan_yes_no(conn, fee_config, args.oos_start, args.oos_end)
        multi_count = scan_multi_outcome(conn, fee_config, args.oos_start, args.oos_end)
        print(f"Oportunidades YES+NO registradas: {yes_no_count}")
        print(f"Oportunidades multi-outcome registradas: {multi_count}")
    finally:
        conn.close()


def cmd_backtest(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    try:
        resolved = resolve_all_pending(conn)
        print(f"Oportunidades resolvidas nesta rodada: {resolved}")
    finally:
        conn.close()


def cmd_report(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    try:
        write_report(conn, args.output)
        print(f"Relatório gerado em: {args.output}")
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="polymarket_alpha", description="Fase 1 — pesquisa de arbitragem interna")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Caminho do banco SQLite")
    sub = parser.add_subparsers(dest="command", required=True)

    collect_p = sub.add_parser("collect", help="Coleta mercados/eventos da Gamma API")
    collect_p.add_argument("--max-pages", type=int, default=50)
    collect_p.set_defaults(func=cmd_collect)

    normalize_p = sub.add_parser("normalize", help="(no-op — ver nota de design)")
    normalize_p.set_defaults(func=cmd_normalize)

    scan_p = sub.add_parser("scan", help="Varre o banco em busca de oportunidades e grava todas (Seção 9)")
    scan_p.add_argument("--oos-start", type=int, default=None, help="Epoch UTC de início do período OOS")
    scan_p.add_argument("--oos-end", type=int, default=None, help="Epoch UTC de fim do período OOS")
    scan_p.set_defaults(func=cmd_scan)

    backtest_p = sub.add_parser("backtest", help="Resolve oportunidades pendentes contra `resolutions`")
    backtest_p.set_defaults(func=cmd_backtest)

    report_p = sub.add_parser("report", help="Gera reports/phase_1_report.md")
    report_p.add_argument("--output", default=DEFAULT_REPORT_PATH)
    report_p.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
