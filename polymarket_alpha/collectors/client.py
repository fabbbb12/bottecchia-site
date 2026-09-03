"""Cliente HTTP fino para as APIs da Polymarket.

Centraliza as chamadas de rede num único lugar para: (1) facilitar
mockar em teste, e (2) deixar claro que ENDPOINTS ABAIXO NÃO FORAM
VERIFICADOS AO VIVO nesta sessão de desenvolvimento — a rede deste
ambiente bloqueia domínios da Polymarket e a documentação oficial.
Confirme cada caminho em https://docs.polymarket.com antes de rodar
`collect` de verdade.
"""

import logging

import requests

from config.settings import ApiSettings, load_api_settings

logger = logging.getLogger("polymarket_alpha.collectors.client")


class PolymarketClient:
    def __init__(self, settings: ApiSettings | None = None):
        self.settings = settings or load_api_settings()
        if not self.settings.verified_against_docs:
            logger.warning(
                "config/settings.yaml: verified_against_docs=false -- os endpoints usados aqui "
                "NÃO foram confirmados contra a documentação oficial atual. Verifique antes de "
                "confiar nos dados coletados."
            )

    def _get(self, base_url: str, path: str, params: dict | None = None) -> dict | list:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        response = requests.get(url, params=params, timeout=self.settings.request_timeout_seconds)
        response.raise_for_status()
        return response.json()

    def get_markets(self, limit: int = 100, offset: int = 0, active: bool | None = None) -> list[dict]:
        """GAMMA API — lista mercados. Caminho e nomes de parâmetro
        (limit/offset/active) não verificados ao vivo nesta sessão."""
        params = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = str(active).lower()
        result = self._get(self.settings.gamma_base_url, "markets", params)
        return result if isinstance(result, list) else result.get("data", [])

    def get_events(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """GAMMA API — lista eventos (agrupam múltiplos mercados/outcomes)."""
        params = {"limit": limit, "offset": offset}
        result = self._get(self.settings.gamma_base_url, "events", params)
        return result if isinstance(result, list) else result.get("data", [])

    def get_order_book(self, token_id: str) -> dict:
        """CLOB API — order book (bids/asks) de um token específico."""
        return self._get(self.settings.clob_base_url, "book", {"token_id": token_id})

    def get_price_history(self, token_id: str, start_ts: int, end_ts: int, fidelity: int = 60) -> list[dict]:
        """CLOB API — histórico de preço (midpoint) de um token entre dois
        timestamps epoch UTC. `fidelity` em minutos entre pontos."""
        params = {"market": token_id, "startTs": start_ts, "endTs": end_ts, "fidelity": fidelity}
        result = self._get(self.settings.clob_base_url, "prices-history", params)
        return result.get("history", []) if isinstance(result, dict) else result

    def get_trades(self, token_id: str, limit: int = 100) -> list[dict]:
        """CLOB API — trades executados recentemente de um token."""
        params = {"market": token_id, "limit": limit}
        result = self._get(self.settings.clob_base_url, "trades", params)
        return result if isinstance(result, list) else result.get("data", [])
