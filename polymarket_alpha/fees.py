"""Custos de execução — Seção 12. Taxas ficam em config/fees.yaml, nunca
hardcoded, para que cada experimento registre explicitamente qual
estrutura de custos usou."""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_FEES_PATH = Path(__file__).parent / "config" / "fees.yaml"


@dataclass
class FeeConfig:
    trading_fee_bps: float
    gas_cost_usd: float
    slippage_model: str
    verified_against: str | None
    verified_at: str | None


def load_fee_config(path: Path | str = DEFAULT_FEES_PATH) -> FeeConfig:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return FeeConfig(
        trading_fee_bps=raw.get("trading_fee_bps", 0.0),
        gas_cost_usd=raw.get("gas_cost_usd", 0.0),
        slippage_model=raw.get("slippage_model", "orderbook_vwap"),
        verified_against=raw.get("verified_against"),
        verified_at=raw.get("verified_at"),
    )


def compute_fee_cost(notional: float, fee_config: FeeConfig, num_legs: int = 1) -> float:
    """Custo total de taxas para uma operação de determinado valor
    (notional, em USD) — taxa percentual sobre o notional + custo fixo de
    rede por perna executada (ex: comprar YES e NO = 2 pernas)."""
    return notional * (fee_config.trading_fee_bps / 10_000) + fee_config.gas_cost_usd * num_legs
