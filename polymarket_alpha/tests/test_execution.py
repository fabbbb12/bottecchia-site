from execution import compute_vwap_execution


def test_full_fill_at_best_price_when_size_fits_first_level():
    levels = [(0.50, 100.0), (0.55, 200.0)]
    result = compute_vwap_execution(levels, 50.0)
    assert result.vwap_price == 0.50
    assert result.executed_size == 50.0
    assert result.fully_filled
    assert result.slippage_pct == 0.0


def test_vwap_worsens_when_order_walks_into_second_level():
    # 10 @ 0.50, 20 @ 0.51 -> pedir 20 unidades consome os 10 do primeiro
    # nível e 10 do segundo
    levels = [(0.50, 10.0), (0.51, 20.0)]
    result = compute_vwap_execution(levels, 20.0)
    expected_vwap = (10 * 0.50 + 10 * 0.51) / 20
    assert round(result.vwap_price, 6) == round(expected_vwap, 6)
    assert result.executed_size == 20.0
    assert result.fully_filled
    assert result.slippage_pct > 0  # pior que o melhor preço


def test_partial_fill_when_depth_insufficient():
    levels = [(0.50, 10.0), (0.51, 5.0)]
    result = compute_vwap_execution(levels, 100.0)
    assert result.executed_size == 15.0
    assert not result.fully_filled
    assert result.depth_available == 15.0


def test_empty_book_returns_no_execution():
    result = compute_vwap_execution([], 10.0)
    assert result.executed_size == 0.0
    assert result.vwap_price is None
    assert not result.fully_filled


def test_zero_or_negative_target_size_returns_no_execution():
    levels = [(0.50, 10.0)]
    result = compute_vwap_execution(levels, 0.0)
    assert result.executed_size == 0.0
    assert result.vwap_price is None
