"""Walk-forward: roda a estratégia CONGELADA (nenhum parâmetro é ajustado
aqui) em várias janelas de tempo sequenciais e não sobrepostas.

Importante: não existe etapa de "treino" neste módulo — a estratégia já
está com todos os parâmetros fixados antes de chegar aqui. Cada janela é,
portanto, 100% fora da amostra em relação a qualquer ajuste feito nela
mesma. O objetivo é verificar se o comportamento observado nos testes
anteriores (proteção de drawdown, sem vantagem de retorno ajustado ao
risco) se mantém estável quando a janela de tempo muda, em vez de ser
coincidência de um período específico.
"""

import logging
import statistics
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from tradebot.backtest import BacktestResult, build_metric_pairs, print_aggregate_comparison, run_multi_backtest
from tradebot.strategy import StrategyConfig

logger = logging.getLogger("tradebot.walkforward")


def generate_windows(start: str, end: str, window_years: float, min_window_days: int = 90) -> list[tuple[str, str]]:
    """Divide [start, end] em janelas sequenciais e não sobrepostas de
    aproximadamente `window_years` anos cada. A última janela é descartada
    se sobrar um pedaço menor que `min_window_days` (janela residual
    pequena demais para dar um resultado confiável)."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    offset = pd.DateOffset(months=round(window_years * 12))

    windows: list[tuple[str, str]] = []
    current = start_ts
    while current < end_ts:
        window_end = min(current + offset, end_ts)
        if (window_end - current).days < min_window_days:
            break
        windows.append((current.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d")))
        current = window_end
    return windows


@dataclass
class WalkForwardResult:
    windows: list[tuple[str, str]]
    window_results: dict[str, dict[str, BacktestResult]] = field(default_factory=dict)


def run_walk_forward(
    symbols: list[str],
    strategy_cfg: StrategyConfig,
    start: str,
    end: str,
    window_years: float = 2.0,
    interval: str = "1d",
    starting_cash: float = 10_000.0,
    cash_fraction: float = 0.5,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    backtest_fn: Callable[..., dict[str, BacktestResult]] = run_multi_backtest,
    backtest_kwargs: dict | None = None,
) -> WalkForwardResult:
    """`backtest_fn` roda por padrão a V1 congelada (`run_multi_backtest`),
    mantendo compatibilidade com todo código existente. Para rodar
    walk-forward de uma versão/família diferente (ex: B1), passe a
    `run_multi_backtest_*` correspondente — ela só precisa aceitar
    `(symbols, strategy_cfg, interval=, start=, end=, starting_cash=,
    cash_fraction=, fee_rate=, slippage_rate=, **backtest_kwargs)`, mesmo
    que `strategy_cfg` não seja usado. Nenhum parâmetro é recalibrado por
    janela aqui — a estratégia já chega congelada."""
    windows = generate_windows(start, end, window_years)
    window_results: dict[str, dict[str, BacktestResult]] = {}
    extra_kwargs = backtest_kwargs or {}

    for idx, (w_start, w_end) in enumerate(windows, start=1):
        label = f"{w_start} a {w_end}"
        logger.info("Janela %d/%d: %s...", idx, len(windows), label)
        results = backtest_fn(
            symbols,
            strategy_cfg,
            interval=interval,
            start=w_start,
            end=w_end,
            starting_cash=starting_cash,
            cash_fraction=cash_fraction,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            **extra_kwargs,
        )
        if not results:
            logger.warning("Janela %s ficou sem nenhum resultado (todos os símbolos falharam), pulando", label)
            continue
        window_results[label] = results

    return WalkForwardResult(windows=windows, window_results=window_results)


def print_walk_forward_report(wf: WalkForwardResult) -> None:
    if not wf.window_results:
        print("Nenhuma janela produziu resultado.")
        return

    print("\n" + "=" * 78)
    print("WALK-FORWARD — estratégia congelada, nenhum parâmetro ajustado por janela")
    print(f"Janelas planejadas: {len(wf.windows)} | Janelas com resultado: {len(wf.window_results)}")
    print("=" * 78)

    # 1) Detalhe de cada janela (mesma visão de média/mediana/vitórias por ativo)
    for label, results in wf.window_results.items():
        print(f"\n\n########## Janela: {label} ##########")
        print_aggregate_comparison(results, label="ativos nesta janela")

    # 2) Consistência entre janelas: para cada métrica, a mediana dos ativos
    #    dentro de cada janela vira "o resultado daquela janela" — depois
    #    contamos em quantas janelas a estratégia superou o buy-and-hold.
    metric_names = ["Retorno", "CAGR", "Máx. drawdown", "Sharpe", "Sortino", "Calmar"]
    per_window_medians: dict[str, tuple[list[float], list[float]]] = {name: ([], []) for name in metric_names}

    for results in wf.window_results.values():
        for name, strategy_values, bench_values in build_metric_pairs(results):
            per_window_medians[name][0].append(statistics.median(strategy_values))
            per_window_medians[name][1].append(statistics.median(bench_values))

    num_windows = len(wf.window_results)
    print(f"\n\n{'=' * 78}")
    print(f"=== Consistência entre {num_windows} janelas (mediana dos ativos por janela) ===")
    header = f"{'Métrica':<15}{'Média janelas':>15}{'Média B&H':>12}{'Mediana':>12}{'Mediana B&H':>14}{'Janelas venc.':>15}"
    print(header)
    print("-" * len(header))
    for name in metric_names:
        s_values, b_values = per_window_medians[name]
        unit = "" if name in ("Sharpe", "Sortino", "Calmar") else "%"
        mean_s = statistics.mean(s_values)
        mean_b = statistics.mean(b_values)
        median_s = statistics.median(s_values)
        median_b = statistics.median(b_values)
        wins = sum(1 for s, b in zip(s_values, b_values) if s > b)
        print(
            f"{name:<15}{mean_s:>14.2f}{unit:<1}{mean_b:>11.2f}{unit:<1}"
            f"{median_s:>11.2f}{unit:<1}{median_b:>13.2f}{unit:<1}{wins:>10}/{num_windows}"
        )

    # 3) Agregado geral: todas as combinações (janela, ativo) juntas — a
    #    amostra mais completa que temos para julgar o comportamento típico.
    flat: dict[str, BacktestResult] = {}
    for label, results in wf.window_results.items():
        for symbol, result in results.items():
            flat[f"{symbol} [{label}]"] = result

    print(f"\n\n{'=' * 78}")
    print("=== Agregado geral: todas as combinações janela × ativo juntas ===")
    print_aggregate_comparison(flat, label="combinações janela×ativo")
