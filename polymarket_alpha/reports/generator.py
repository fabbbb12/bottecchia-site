"""Relatório final em Markdown — Seção 17, com classificação de cada
hipótese pelo critério de sucesso da Seção 18."""

import sqlite3
from datetime import datetime, timezone

from analysis.metrics import StrategyMetrics, compute_strategy_metrics

STRATEGIES = [("yes_no", "Arbitragem YES + NO"), ("multi_outcome", "Multi-outcome"), ("relationship", "Relações matemáticas")]

# Critério de sucesso (Seção 18) -- limiares mínimos para "promissora".
# Não são garantia de lucro real, só o piso para não descartar de cara.
MIN_OPPORTUNITIES_FOR_SIGNAL = 30
MIN_CAPITAL_EXECUTABLE_USD = 50.0


def _fmt(value, suffix: str = "", decimals: int = 4) -> str:
    if value is None:
        return "n/d"
    if value == float("inf"):
        return "inf"
    return f"{value:.{decimals}f}{suffix}"


def classify_hypothesis(is_metrics: StrategyMetrics, oos_metrics: StrategyMetrics | None) -> str:
    """Classifica a hipótese conforme a Seção 18: REJEITADA, INCONCLUSIVA,
    PROMISSORA ou VALIDADA. Nunca "VALIDADA" só por ter dado lucro
    histórico -- exige também nº de oportunidades, execução OOS positiva
    e capacidade financeira mínima."""
    if is_metrics.num_opportunities == 0:
        return "INCONCLUSIVA (nenhuma oportunidade candidata detectada no dataset coletado)"

    if is_metrics.num_executable == 0:
        return "REJEITADA (oportunidades existem no topo do book, mas nenhuma sobrevive à profundidade real)"

    if is_metrics.num_opportunities < MIN_OPPORTUNITIES_FOR_SIGNAL:
        return f"INCONCLUSIVA (apenas {is_metrics.num_opportunities} oportunidades -- amostra pequena demais para conclusão)"

    if is_metrics.net_profit is None or is_metrics.net_profit <= 0:
        return "REJEITADA (lucro líquido não positivo mesmo dentro da amostra)"

    if is_metrics.capital_executable_median is not None and is_metrics.capital_executable_median < MIN_CAPITAL_EXECUTABLE_USD:
        return "REJEITADA (capital executável mediano irrelevante -- edge existe mas sem tamanho para importar)"

    if oos_metrics is None or oos_metrics.num_opportunities == 0:
        return "PROMISSORA (passou nos critérios in-sample, mas ainda sem confirmação fora da amostra)"

    if oos_metrics.net_profit is None or oos_metrics.net_profit <= 0:
        return "REJEITADA (resultado positivo in-sample não se confirmou fora da amostra)"

    return "VALIDADA (edge líquido positivo, amostra suficiente, capacidade mínima e confirmado fora da amostra)"


def _dataset_summary(conn: sqlite3.Connection) -> dict:
    def count(table):
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]

    span = conn.execute(
        "SELECT MIN(timestamp_detected) AS start, MAX(timestamp_detected) AS end FROM opportunities"
    ).fetchone()
    return {
        "markets": count("markets"),
        "tokens": count("tokens"),
        "trades": count("trades"),
        "snapshots": count("orderbook_snapshots"),
        "start": span["start"],
        "end": span["end"],
    }


def _metrics_table(is_metrics: StrategyMetrics, oos_metrics: StrategyMetrics | None) -> str:
    rows = [
        ("Oportunidades (candidatas)", is_metrics.num_candidates, oos_metrics.num_candidates if oos_metrics else None),
        ("Executáveis", is_metrics.num_executable, oos_metrics.num_executable if oos_metrics else None),
        ("Edge líquido médio", _fmt(is_metrics.net_edge_mean), _fmt(oos_metrics.net_edge_mean) if oos_metrics else "n/d"),
        ("Edge líquido mediano", _fmt(is_metrics.net_edge_median), _fmt(oos_metrics.net_edge_median) if oos_metrics else "n/d"),
        (
            "Capital executável mediano (USD)",
            _fmt(is_metrics.capital_executable_median, decimals=2),
            _fmt(oos_metrics.capital_executable_median, decimals=2) if oos_metrics else "n/d",
        ),
        (
            "Duração mediana (s)",
            _fmt(is_metrics.duration_median, decimals=0),
            _fmt(oos_metrics.duration_median, decimals=0) if oos_metrics else "n/d",
        ),
        ("Lucro líquido total (USD)", _fmt(is_metrics.net_profit, decimals=2), _fmt(oos_metrics.net_profit, decimals=2) if oos_metrics else "n/d"),
        (
            "Máx. drawdown (USD)",
            _fmt(is_metrics.max_drawdown, decimals=2),
            _fmt(oos_metrics.max_drawdown, decimals=2) if oos_metrics else "n/d",
        ),
    ]
    lines = ["| Métrica | In-sample | OOS |", "|---|---:|---:|"]
    for name, is_val, oos_val in rows:
        lines.append(f"| {name} | {is_val} | {oos_val} |")
    return "\n".join(lines)


def generate_report(conn: sqlite3.Connection) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dataset = _dataset_summary(conn)

    sections = [
        "# Polymarket Alpha Lab — Relatório da Fase 1",
        f"\n_Gerado em {generated_at}._",
        "\n## 1. Dataset",
        f"- Mercados: {dataset['markets']}",
        f"- Tokens: {dataset['tokens']}",
        f"- Trades registrados: {dataset['trades']}",
        f"- Snapshots de order book: {dataset['snapshots']}",
        f"- Cobertura temporal (detecção de oportunidades): {dataset['start']} a {dataset['end']} (epoch UTC)",
    ]

    conclusions = []
    for strategy_type, title in STRATEGIES:
        is_metrics = compute_strategy_metrics(conn, strategy_type, is_oos=False)
        oos_metrics = compute_strategy_metrics(conn, strategy_type, is_oos=True)
        classification = classify_hypothesis(is_metrics, oos_metrics)
        conclusions.append((title, classification))

        sections.append(f"\n## {title}")
        sections.append(_metrics_table(is_metrics, oos_metrics))
        sections.append(f"\n**Classificação:** {classification}")

    sections.append("\n## Limitações")
    sections.append(
        "- Este relatório reflete apenas o que estava no banco de dados local no momento da geração; "
        "cobertura incompleta de mercados/eventos não é distinguível de ausência real de oportunidades.\n"
        "- Custos (taxas, gas) usam a configuração em `config/fees.yaml`, que precisa ser verificada contra "
        "a documentação oficial atual da Polymarket antes de qualquer conclusão forte.\n"
        "- A classificação de relações (Seção 8) e de estrutura multi-outcome (mutuamente exclusivo/exaustivo) "
        "depende de `classification_notes` registradas manualmente — nunca inferidas automaticamente."
    )

    sections.append("\n## Conclusão")
    for title, classification in conclusions:
        sections.append(f"- **{title}**: {classification}")

    return "\n".join(sections) + "\n"


def write_report(conn: sqlite3.Connection, output_path: str) -> None:
    report = generate_report(conn)
    with open(output_path, "w") as f:
        f.write(report)
