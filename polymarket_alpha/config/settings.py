"""Carrega config/settings.yaml."""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_SETTINGS_PATH = Path(__file__).parent / "settings.yaml"


@dataclass
class ApiSettings:
    gamma_base_url: str
    clob_base_url: str
    request_timeout_seconds: int
    verified_against_docs: bool


def load_api_settings(path: Path | str = DEFAULT_SETTINGS_PATH) -> ApiSettings:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    api = raw.get("api", {})
    return ApiSettings(
        gamma_base_url=api.get("gamma_base_url", ""),
        clob_base_url=api.get("clob_base_url", ""),
        request_timeout_seconds=api.get("request_timeout_seconds", 15),
        verified_against_docs=api.get("verified_against_docs", False),
    )
