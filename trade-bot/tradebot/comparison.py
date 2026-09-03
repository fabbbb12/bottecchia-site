"""Comparação genérica V1 vs uma versão experimental (V2, V3, ...) vs
Buy&Hold — usada por todos os experimentos em backtest_v2.py, backtest_v3.py
etc., para manter o mesmo formato de relatório em todos eles."""

import statistics
from typing import Callable

from tradebot.backtest import BacktestResult


def _bench_pnl_pct(result: BacktestResult) -> float:
    b0 = result.benchmark_curve.iloc[0]
    b1 = result.benchmark_curve.iloc[-1]
    return (b1 - b0) / b0 * 100


METRIC_EXTRACTORS: list[tuple[str, Callable[[BacktestResult], float], Callable[[BacktestResult], float]]] = [
    ("Retorno", lambda r: r.final_summary["pnl_pct"], _bench_pnl_pct),
    ("CAGR", lambda r: r.metrics["cagr_pct"], lambda r: r.benchmark_metrics["cagr_pct"]),
    (
        "Máx. drawdown",
        lambda r: r.metrics["max_drawdown_pct"],
        lambda r: r.benchmark_metrics["max_drawdown_pct"],
    ),
    ("Sharpe", lambda r: r.metrics["sharpe"], lambda r: r.benchmark_metrics["sharpe"]),
    ("Sortino", lambda r: r.metrics["sortino"], lambda r: r.benchmark_metrics["sortino"]),
    ("Calmar", lambda r: r.metrics["calmar"], lambda r: r.benchmark_metrics["calmar"]),
]


def print_v1_challenger_comparison(
    v1_results: dict[str, BacktestResult],
    challenger_results: dict[str, BacktestResult],
    challenger_label: str = "V2",
) -> None:
    """V1 vs `challenger_label` vs Buy&Hold lado a lado — média, mediana e
    contagem de vitórias (challenger supera V1, challenger supera B&H, V1
    supera B&H) por métrica. Critério de aprovação de qualquer experimento
    (não é "bater tudo"): drawdown não piorar muito frente à V1, retorno
    melhorar claramente frente à V1, Sharpe/Sortino saírem da zona
    claramente negativa — e tudo isso robusto na mediana e nas vitórias,
    não só na média."""
    symbols = [s for s in v1_results if s in challenger_results]
    if not symbols:
        print(f"Nenhum símbolo em comum entre V1 e {challenger_label} para comparar.")
        return
    n = len(symbols)
    c = challenger_label

    print(f"\n=== V1 vs {c} vs Buy&Hold entre {n} ativos ===")
    header = (
        f"{'Métrica':<15}{'Méd V1':>9}{f'Méd {c}':>9}{'Méd B&H':>9}"
        f"{'Med V1':>9}{f'Med {c}':>9}{'Med B&H':>9}{f'{c}>V1':>8}{f'{c}>B&H':>8}{'V1>B&H':>8}"
    )
    print(header)
    print("-" * len(header))
    for name, extractor, bench_extractor in METRIC_EXTRACTORS:
        v1_vals = [extractor(v1_results[s]) for s in symbols]
        c_vals = [extractor(challenger_results[s]) for s in symbols]
        bench_vals = [bench_extractor(v1_results[s]) for s in symbols]
        unit = "" if name in ("Sharpe", "Sortino", "Calmar") else "%"

        mean_v1, mean_c, mean_b = statistics.mean(v1_vals), statistics.mean(c_vals), statistics.mean(bench_vals)
        median_v1 = statistics.median(v1_vals)
        median_c = statistics.median(c_vals)
        median_b = statistics.median(bench_vals)
        c_beats_v1 = sum(1 for a, b in zip(c_vals, v1_vals) if a > b)
        c_beats_b = sum(1 for a, b in zip(c_vals, bench_vals) if a > b)
        v1_beats_b = sum(1 for a, b in zip(v1_vals, bench_vals) if a > b)
        print(
            f"{name:<15}{mean_v1:>8.2f}{unit}{mean_c:>8.2f}{unit}{mean_b:>8.2f}{unit}"
            f"{median_v1:>8.2f}{unit}{median_c:>8.2f}{unit}{median_b:>8.2f}{unit}"
            f"{c_beats_v1:>5}/{n}{c_beats_b:>5}/{n}{v1_beats_b:>5}/{n}"
        )

    v1_trades = [v1_results[s].metrics["num_trades"] for s in symbols]
    c_trades = [challenger_results[s].metrics["num_trades"] for s in symbols]
    v1_exposed = [v1_results[s].metrics["time_exposed_pct"] for s in symbols]
    c_exposed = [challenger_results[s].metrics["time_exposed_pct"] for s in symbols]
    print(
        f"\nNº de trades (mediana):        V1={statistics.median(v1_trades):.0f}"
        f"   {c}={statistics.median(c_trades):.0f}"
    )
    print(
        f"% tempo exposto (mediana):     V1={statistics.median(v1_exposed):.1f}%"
        f"   {c}={statistics.median(c_exposed):.1f}%"
    )
    print(
        "\nColunas: 'Méd/Med X' = média/mediana daquele valor entre os ativos; "
        "'A>B' = em quantos ativos A superou B naquela métrica."
    )
