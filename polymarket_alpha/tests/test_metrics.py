import tempfile
from pathlib import Path

from analysis.metrics import compute_strategy_metrics
from db import get_connection, init_db


def _make_db():
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    init_db(db_path)
    return tmp, get_connection(db_path)


def _insert_opp(conn, market_id, ts, gross_edge, capital_executable, net_edge, duration=None, realized_pnl=None, fees=0.0, is_oos=0):
    conn.execute("INSERT OR IGNORE INTO markets (market_id) VALUES (?)", (market_id,))
    conn.execute(
        "INSERT INTO opportunities (timestamp_detected, market_id, strategy_type, gross_edge, "
        "capital_executable, net_edge, duration, realized_pnl, fees, is_oos) "
        "VALUES (?, ?, 'yes_no', ?, ?, ?, ?, ?, ?, ?)",
        (ts, market_id, gross_edge, capital_executable, net_edge, duration, realized_pnl, fees, is_oos),
    )
    conn.commit()


def test_metrics_count_opportunities_candidates_and_executable():
    tmp, conn = _make_db()
    try:
        _insert_opp(conn, "M1", 1000, gross_edge=0.05, capital_executable=10.0, net_edge=0.04)
        _insert_opp(conn, "M2", 2000, gross_edge=-0.02, capital_executable=0.0, net_edge=None)  # não candidata
        _insert_opp(conn, "M3", 3000, gross_edge=0.03, capital_executable=0.0, net_edge=None)  # candidata mas não executável
        metrics = compute_strategy_metrics(conn, "yes_no")
        assert metrics.num_opportunities == 3
        assert metrics.num_candidates == 2
        assert metrics.num_executable == 1
    finally:
        conn.close()
        tmp.cleanup()


def test_metrics_edge_statistics():
    tmp, conn = _make_db()
    try:
        for i, edge in enumerate([0.01, 0.02, 0.03, 0.04, 0.05]):
            _insert_opp(conn, f"M{i}", 1000 + i, gross_edge=edge + 0.01, capital_executable=10.0, net_edge=edge)
        metrics = compute_strategy_metrics(conn, "yes_no")
        assert metrics.net_edge_mean == 0.03
        assert metrics.net_edge_median == 0.03
        assert metrics.net_edge_max == 0.05
        assert metrics.net_edge_min == 0.01
    finally:
        conn.close()
        tmp.cleanup()


def test_metrics_result_statistics_with_wins_and_losses():
    tmp, conn = _make_db()
    try:
        _insert_opp(conn, "M1", 1000, 0.05, 10.0, 0.04, duration=3600, realized_pnl=5.0, fees=0.5)
        _insert_opp(conn, "M2", 2000, 0.05, 10.0, 0.04, duration=7200, realized_pnl=-2.0, fees=0.5)
        metrics = compute_strategy_metrics(conn, "yes_no")
        assert metrics.num_resolved == 2
        assert metrics.net_profit == 3.0
        assert metrics.win_rate == 0.5
        assert metrics.profit_factor == 2.5  # 5 / 2
        assert metrics.duration_median == 5400
    finally:
        conn.close()
        tmp.cleanup()


def test_metrics_filters_by_oos_flag():
    tmp, conn = _make_db()
    try:
        _insert_opp(conn, "M1", 1000, 0.05, 10.0, 0.04, is_oos=0)
        _insert_opp(conn, "M2", 2000, 0.05, 10.0, 0.04, is_oos=1)
        in_sample = compute_strategy_metrics(conn, "yes_no", is_oos=False)
        oos = compute_strategy_metrics(conn, "yes_no", is_oos=True)
        assert in_sample.num_opportunities == 1
        assert oos.num_opportunities == 1
    finally:
        conn.close()
        tmp.cleanup()


def test_metrics_empty_table_returns_none_stats_not_crash():
    tmp, conn = _make_db()
    try:
        metrics = compute_strategy_metrics(conn, "yes_no")
        assert metrics.num_opportunities == 0
        assert metrics.net_edge_mean is None
        assert metrics.max_drawdown is None
    finally:
        conn.close()
        tmp.cleanup()


def test_max_drawdown_is_negative_when_pnl_dips_after_peak():
    tmp, conn = _make_db()
    try:
        # sobe pra 10, cai pra 4 (dd de -6), sobe pra 12
        pnls = [10.0, -6.0, 8.0]
        for i, pnl in enumerate(pnls):
            _insert_opp(conn, f"M{i}", 1000 + i, 0.05, 10.0, 0.04, duration=100, realized_pnl=pnl)
        metrics = compute_strategy_metrics(conn, "yes_no")
        assert metrics.max_drawdown == -6.0
    finally:
        conn.close()
        tmp.cleanup()
