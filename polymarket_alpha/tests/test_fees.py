from fees import FeeConfig, compute_fee_cost, load_fee_config
from db import DEFAULT_DB_PATH  # noqa: F401 - garante que db.py importa sem erro no mesmo teste run


def test_load_fee_config_reads_defaults():
    cfg = load_fee_config()
    assert isinstance(cfg, FeeConfig)
    assert cfg.trading_fee_bps == 0
    assert cfg.slippage_model == "orderbook_vwap"


def test_compute_fee_cost_applies_bps_and_gas():
    cfg = FeeConfig(trading_fee_bps=100, gas_cost_usd=0.10, slippage_model="x", verified_against=None, verified_at=None)
    # 100 bps = 1% sobre notional de 1000 = 10, mais 2 pernas * 0.10 = 0.20
    cost = compute_fee_cost(notional=1000.0, fee_config=cfg, num_legs=2)
    assert round(cost, 4) == 10.20


def test_compute_fee_cost_zero_fee_config():
    cfg = FeeConfig(trading_fee_bps=0, gas_cost_usd=0.0, slippage_model="x", verified_against=None, verified_at=None)
    assert compute_fee_cost(1000.0, cfg, num_legs=2) == 0.0
