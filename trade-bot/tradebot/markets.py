"""Listas padrão de ativos líquidos para teste de swing trade.

São apenas pontos de partida razoáveis — o usuário pode sempre passar seus
próprios símbolos via `--symbols`.
"""

US_WATCHLIST = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

BR_WATCHLIST = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "WEGE3.SA", "ABEV3.SA"]


def resolve_symbols(market: str | None, symbols_arg: str | None) -> list[str]:
    """Resolve a lista final de símbolos a partir de `--symbols` e/ou `--market`."""
    symbols: list[str] = []
    if symbols_arg:
        symbols.extend(s.strip() for s in symbols_arg.split(",") if s.strip())

    if market:
        market = market.lower()
        if market == "us":
            symbols.extend(US_WATCHLIST)
        elif market == "br":
            symbols.extend(BR_WATCHLIST)
        elif market == "all":
            symbols.extend(US_WATCHLIST + BR_WATCHLIST)
        else:
            raise ValueError(f"Mercado desconhecido: '{market}' (use us, br ou all)")

    # remove duplicatas preservando ordem
    seen = set()
    unique_symbols = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            unique_symbols.append(s)
    return unique_symbols
