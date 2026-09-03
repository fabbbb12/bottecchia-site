"""Métricas por estratégia — Seção 13. Sempre a partir da tabela
`opportunities`, que registra TODAS as candidatas (não só as lucrativas),
para não gerar viés de sobrevivência (Seção 9)."""

import sqlite3
import statistics
from dataclasses import dataclass, field


@dataclass
class StrategyMetrics:
    strategy_type: str
    num_opportunities: int
    num_candidates: int          # gross_edge > 0
    num_executable: int          # capital_executable > 0
    num_resolved: int
    days_covered: float | None

    # Edge (sobre as executáveis, líquido de custos)
    net_edge_mean: float | None = None
    net_edge_median: float | None = None
    net_edge_p25: float | None = None
    net_edge_p75: float | None = None
    net_edge_max: float | None = None
    net_edge_min: float | None = None

    # Execução
    capital_executable_mean: float | None = None
    capital_executable_median: float | None = None
    capital_executable_p25: float | None = None
    capital_executable_p75: float | None = None
    capital_executable_max: float | None = None

    # Duração (segundos)
    duration_mean: float | None = None
    duration_median: float | None = None
    duration_p25: float | None = None
    duration_p75: float | None = None
    duration_min: float | None = None
    duration_max: float | None = None

    # Resultado (sobre as resolvidas)
    gross_profit: float | None = None
    net_profit: float | None = None
    win_rate: float | None = None
    profit_factor: float | None = None
    max_drawdown: float | None = None


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def _max_drawdown(cumulative_pnl: list[float]) -> float:
    if not cumulative_pnl:
        return 0.0
    peak = cumulative_pnl[0]
    max_dd = 0.0
    for value in cumulative_pnl:
        peak = max(peak, value)
        max_dd = min(max_dd, value - peak)
    return max_dd


def compute_strategy_metrics(
    conn: sqlite3.Connection, strategy_type: str, is_oos: bool | None = None
) -> StrategyMetrics:
    where = "WHERE strategy_type = ?"
    params: list = [strategy_type]
    if is_oos is not None:
        where += " AND is_oos = ?"
        params.append(1 if is_oos else 0)

    rows = conn.execute(f"SELECT * FROM opportunities {where} ORDER BY timestamp_detected", params).fetchall()

    num_opportunities = len(rows)
    candidates = [r for r in rows if (r["gross_edge"] or 0) > 0]
    executable = [r for r in rows if (r["capital_executable"] or 0) > 0]
    resolved = [r for r in rows if r["realized_pnl"] is not None]

    days_covered = None
    if rows:
        span_seconds = rows[-1]["timestamp_detected"] - rows[0]["timestamp_detected"]
        days_covered = span_seconds / 86_400 if span_seconds > 0 else 0.0

    metrics = StrategyMetrics(
        strategy_type=strategy_type,
        num_opportunities=num_opportunities,
        num_candidates=len(candidates),
        num_executable=len(executable),
        num_resolved=len(resolved),
        days_covered=days_covered,
    )

    net_edges = [r["net_edge"] for r in executable if r["net_edge"] is not None]
    if net_edges:
        metrics.net_edge_mean = statistics.mean(net_edges)
        metrics.net_edge_median = statistics.median(net_edges)
        metrics.net_edge_p25 = _percentile(net_edges, 0.25)
        metrics.net_edge_p75 = _percentile(net_edges, 0.75)
        metrics.net_edge_max = max(net_edges)
        metrics.net_edge_min = min(net_edges)

    capitals = [r["capital_executable"] for r in executable if r["capital_executable"] is not None]
    if capitals:
        metrics.capital_executable_mean = statistics.mean(capitals)
        metrics.capital_executable_median = statistics.median(capitals)
        metrics.capital_executable_p25 = _percentile(capitals, 0.25)
        metrics.capital_executable_p75 = _percentile(capitals, 0.75)
        metrics.capital_executable_max = max(capitals)

    durations = [r["duration"] for r in resolved if r["duration"] is not None]
    if durations:
        metrics.duration_mean = statistics.mean(durations)
        metrics.duration_median = statistics.median(durations)
        metrics.duration_p25 = _percentile(durations, 0.25)
        metrics.duration_p75 = _percentile(durations, 0.75)
        metrics.duration_min = min(durations)
        metrics.duration_max = max(durations)

    pnls = [r["realized_pnl"] for r in resolved if r["realized_pnl"] is not None]
    if pnls:
        metrics.gross_profit = sum(p + (r["fees"] or 0.0) for p, r in zip(pnls, resolved) if r["realized_pnl"] is not None)
        metrics.net_profit = sum(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        metrics.win_rate = len(wins) / len(pnls) if pnls else None
        gross_win = sum(wins)
        gross_loss = -sum(losses)
        metrics.profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)

        cumulative = []
        running = 0.0
        for pnl in pnls:
            running += pnl
            cumulative.append(running)
        metrics.max_drawdown = _max_drawdown(cumulative)

    return metrics
