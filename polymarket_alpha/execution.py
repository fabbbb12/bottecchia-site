"""Preço executável real, considerando profundidade do book — Seção 6.

Regra fundamental que este módulo existe para impor: nunca tratar o
melhor preço (best bid/ask) como se toda a ordem pudesse ser executada
ali. Uma ordem de N contratos consome os níveis do book em sequência,
e o preço médio de execução (VWAP) piora conforme o tamanho aumenta.
"""

from dataclasses import dataclass

Level = tuple[float, float]  # (price, size)


@dataclass
class ExecutionResult:
    requested_size: float
    executed_size: float
    vwap_price: float | None   # None se nada pôde ser executado
    best_price: float | None
    slippage_pct: float | None  # (vwap - best) / best — sinal depende do lado (ver docstring)
    fully_filled: bool
    depth_available: float


def compute_vwap_execution(levels: list[Level], target_size: float) -> ExecutionResult:
    """Caminha pelos níveis do book (do melhor para o pior) e calcula o
    preço médio (VWAP) real de executar `target_size` unidades.

    `slippage_pct` é `(vwap - best_price) / best_price`, sem ajuste de
    sinal por lado: ao consumir mais profundidade do lado de venda (ask),
    o VWAP sobe (slippage positivo = pior pra quem compra); ao consumir
    mais profundidade do lado de compra (bid), o VWAP desce (slippage
    negativo = pior pra quem vende). Isso é o comportamento econômico
    correto — não inverter o sinal na leitura do resultado.
    """
    depth_available = sum(size for _, size in levels) if levels else 0.0

    if not levels or target_size <= 0:
        return ExecutionResult(target_size, 0.0, None, None, None, False, depth_available)

    best_price = levels[0][0]
    remaining = target_size
    cost = 0.0
    executed = 0.0

    for price, size in levels:
        if remaining <= 0:
            break
        take = min(remaining, size)
        cost += take * price
        executed += take
        remaining -= take

    if executed <= 0:
        return ExecutionResult(target_size, 0.0, None, best_price, None, False, depth_available)

    vwap = cost / executed
    slippage_pct = (vwap - best_price) / best_price if best_price else None
    fully_filled = remaining <= 1e-9

    return ExecutionResult(target_size, executed, vwap, best_price, slippage_pct, fully_filled, depth_available)


def _cumulative_levels(levels: list[Level]) -> list[tuple[float, float]]:
    """Devolve [(profundidade acumulada, preço daquele nível), ...]."""
    cumulative = 0.0
    out = []
    for price, size in levels:
        cumulative += size
        out.append((cumulative, price))
    return out


def _price_at_depth(cumulative_levels: list[tuple[float, float]], depth: float) -> float | None:
    for cum_size, price in cumulative_levels:
        if depth <= cum_size + 1e-9:
            return price
    return None  # profundidade solicitada excede o book disponível
