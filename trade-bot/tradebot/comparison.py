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


def print_fibonacci_placebo_test(
    v1_results: dict[str, BacktestResult],
    v3_results: dict[str, BacktestResult],
    v4_results: dict[str, BacktestResult],
) -> None:
    """Teste decisivo pra V3 (filtro de Fibonacci): compara a redução de
    drawdown da V3 contra a V4 (placebo — pula a mesma proporção de
    entradas, mas por sorteio aleatório, sem olhar preço nem Fibonacci).
    Se a V4 reduzir o drawdown tanto quanto a V3, o efeito é só "operar
    menos", não algo específico de Fibonacci."""
    symbols = [s for s in v1_results if s in v3_results and s in v4_results]
    if not symbols:
        print("Nenhum símbolo em comum entre V1, V3 e V4 para comparar.")
        return
    n = len(symbols)

    def dd(results):
        return [results[s].metrics["max_drawdown_pct"] for s in symbols]

    def exposed(results):
        return [results[s].metrics["time_exposed_pct"] for s in symbols]

    def ret(results):
        return [results[s].final_summary["pnl_pct"] for s in symbols]

    dd_v1, dd_v3, dd_v4 = dd(v1_results), dd(v3_results), dd(v4_results)
    exp_v1, exp_v3, exp_v4 = exposed(v1_results), exposed(v3_results), exposed(v4_results)
    ret_v1, ret_v3, ret_v4 = ret(v1_results), ret(v3_results), ret(v4_results)

    v3_beats_v4_dd = sum(1 for a, b in zip(dd_v3, dd_v4) if a > b)  # V3 tem drawdown MENOS negativo que V4
    v3_beats_v4_ret = sum(1 for a, b in zip(ret_v3, ret_v4) if a > b)

    print(f"\n=== Teste de placebo: V3 (Fibonacci) vs V4 (aleatório) — {n} ativos ===")
    header = f"{'Métrica':<20}{'V1':>10}{'V3 (Fibo)':>12}{'V4 (aleatório)':>16}"
    print(header)
    print("-" * len(header))
    print(
        f"{'Máx DD (mediana)':<20}{statistics.median(dd_v1):>9.2f}%"
        f"{statistics.median(dd_v3):>11.2f}%{statistics.median(dd_v4):>15.2f}%"
    )
    print(
        f"{'Máx DD (média)':<20}{statistics.mean(dd_v1):>9.2f}%"
        f"{statistics.mean(dd_v3):>11.2f}%{statistics.mean(dd_v4):>15.2f}%"
    )
    print(
        f"{'% exposto (mediana)':<20}{statistics.median(exp_v1):>9.1f}%"
        f"{statistics.median(exp_v3):>11.1f}%{statistics.median(exp_v4):>15.1f}%"
    )
    print(
        f"{'Retorno (mediana)':<20}{statistics.median(ret_v1):>9.2f}%"
        f"{statistics.median(ret_v3):>11.2f}%{statistics.median(ret_v4):>15.2f}%"
    )
    print(f"\nV3 tem drawdown melhor que V4 (o placebo) em: {v3_beats_v4_dd}/{n} ativos")
    print(f"V3 tem retorno melhor que V4 (o placebo) em:   {v3_beats_v4_ret}/{n} ativos")
    print(
        "\nSe V3 não vencer o placebo (V4) claramente na maioria dos ativos, a redução de "
        "drawdown da V3 não tem relação com Fibonacci — é só efeito de operar menos."
    )
