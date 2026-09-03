import tempfile
from pathlib import Path

from analysis.metrics import StrategyMetrics
from db import get_connection, init_db
from reports.generator import classify_hypothesis, generate_report


def _empty_metrics(strategy_type="yes_no"):
    return StrategyMetrics(
        strategy_type=strategy_type, num_opportunities=0, num_candidates=0, num_executable=0,
        num_resolved=0, days_covered=None,
    )


def test_classify_inconclusive_when_no_opportunities():
    m = _empty_metrics()
    assert classify_hypothesis(m, None).startswith("INCONCLUSIVA")


def test_classify_rejected_when_never_executable():
    m = _empty_metrics()
    m.num_opportunities = 50
    m.num_candidates = 50
    m.num_executable = 0
    assert classify_hypothesis(m, None).startswith("REJEITADA")


def test_classify_inconclusive_when_sample_too_small():
    m = _empty_metrics()
    m.num_opportunities = 5
    m.num_candidates = 5
    m.num_executable = 3
    m.net_profit = 10.0
    m.capital_executable_median = 100.0
    assert "amostra pequena" in classify_hypothesis(m, None)


def test_classify_rejected_when_net_profit_not_positive():
    m = _empty_metrics()
    m.num_opportunities = 50
    m.num_executable = 40
    m.net_profit = -5.0
    assert classify_hypothesis(m, None).startswith("REJEITADA")


def test_classify_rejected_when_capital_negligible():
    m = _empty_metrics()
    m.num_opportunities = 50
    m.num_executable = 40
    m.net_profit = 10.0
    m.capital_executable_median = 1.0  # abaixo do limiar mínimo
    assert "capital executável mediano irrelevante" in classify_hypothesis(m, None)


def test_classify_promising_when_no_oos_data():
    m = _empty_metrics()
    m.num_opportunities = 50
    m.num_executable = 40
    m.net_profit = 10.0
    m.capital_executable_median = 100.0
    assert classify_hypothesis(m, None).startswith("PROMISSORA")


def test_classify_validated_when_positive_in_both_periods():
    is_m = _empty_metrics()
    is_m.num_opportunities = 50
    is_m.num_executable = 40
    is_m.net_profit = 10.0
    is_m.capital_executable_median = 100.0

    oos_m = _empty_metrics()
    oos_m.num_opportunities = 20
    oos_m.net_profit = 5.0

    assert classify_hypothesis(is_m, oos_m).startswith("VALIDADA")


def test_classify_rejected_when_oos_negative():
    is_m = _empty_metrics()
    is_m.num_opportunities = 50
    is_m.num_executable = 40
    is_m.net_profit = 10.0
    is_m.capital_executable_median = 100.0

    oos_m = _empty_metrics()
    oos_m.num_opportunities = 20
    oos_m.net_profit = -1.0

    assert classify_hypothesis(is_m, oos_m).startswith("REJEITADA")


def test_generate_report_runs_on_empty_database():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        try:
            report = generate_report(conn)
        finally:
            conn.close()
        assert "# Polymarket Alpha Lab" in report
        assert "Arbitragem YES + NO" in report
        assert "Conclusão" in report
