import pandas as pd

from tradebot.live_f2 import _default_state, process_new_events


def _series(values, freq_hours=8):
    n = len(values)
    idx = pd.date_range("2023-01-01", periods=n, freq=f"{freq_hours}h")
    return pd.Series(values, index=idx)


def test_bootstrap_state_has_no_position_and_empty_history():
    state = _default_state(10_000.0)
    assert state["in_position"] is False
    assert state["funding_history"] == []
    assert state["capital"] == 10_000.0


def test_stays_out_until_history_reaches_lookback_size():
    state = _default_state(10_000.0)
    state["funding_history"] = [0.0005] * 50  # abaixo do lookback (90) -> ainda sem sinal
    funding = _series([0.0005] * 5)
    basis = _series([0.0] * 5)
    state, events = process_new_events(state, funding, basis, lookback_events=90)
    assert state["in_position"] is False
    assert all(e["trailing_avg"] is None for e in events)


def test_enters_once_history_full_and_average_above_threshold():
    state = _default_state(10_000.0)
    state["funding_history"] = [0.0005] * 90  # historico ja cheio, media bem acima do limiar
    funding = _series([0.0005] * 3)
    basis = _series([0.0] * 3)
    state, events = process_new_events(
        state, funding, basis, entry_fee_rate=0.0, lookback_events=90, min_funding_rate_threshold=0.0001
    )
    assert state["in_position"] is True
    assert state["num_entries"] == 1
    assert events[0]["transitioned"] == "ENTROU"
    assert state["capital"] > 10_000.0


def test_exits_when_average_drops_below_threshold():
    state = _default_state(10_000.0)
    state["in_position"] = True
    state["prev_basis"] = 0.0
    state["funding_history"] = [0.0] * 90  # media zero -> abaixo do limiar
    funding = _series([0.0])
    basis = _series([0.0])
    state, events = process_new_events(
        state, funding, basis, entry_fee_rate=0.001, lookback_events=90, min_funding_rate_threshold=0.0001
    )
    assert state["in_position"] is False
    assert events[0]["transitioned"] == "SAIU"
    assert state["capital"] < 10_000.0  # pagou taxa de saida


def test_history_window_stays_bounded():
    state = _default_state(10_000.0)
    state["funding_history"] = [0.0001] * 90
    funding = _series([0.0002] * 10)
    basis = _series([0.0] * 10)
    state, _ = process_new_events(state, funding, basis, lookback_events=90)
    assert len(state["funding_history"]) == 90
