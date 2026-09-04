"""Listas padrão de ativos líquidos para teste de swing trade.

São apenas pontos de partida razoáveis — o usuário pode sempre passar seus
próprios símbolos via `--symbols`.
"""

US_WATCHLIST = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

BR_WATCHLIST = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "WEGE3.SA", "ABEV3.SA"]

# Universo alternativo, criado DEPOIS de toda a pesquisa V/B/C/D já estar
# concluída, pra testar uma hipótese específica: será que "nada bate
# buy-and-hold" é um achado sobre técnica de trading, ou um artefato de
# testar contra uma cesta concentrada em 5 mega caps de tecnologia (viés
# de sobrevivência — são vencedoras conhecidas em retrospecto, incluindo
# o rali de IA da NVDA, um dos maiores retornos de ação única da
# história)? Mesmo tamanho (5 ativos) e mesma regra de escolha da
# US_WATCHLIST original (nomes grandes e líquidos, um por setor GICS
# diferente) — não foram escolhidos por terem tido retorno bom ou ruim,
# só por representar setores diferentes de tecnologia: Financeiro (JPM),
# Saúde (JNJ), Consumo básico (PG), Energia (XOM), Industrial (CAT).
US_DIVERSIFIED_WATCHLIST = ["JPM", "JNJ", "PG", "XOM", "CAT"]


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
        elif market == "diversified":
            symbols.extend(US_DIVERSIFIED_WATCHLIST + BR_WATCHLIST)
        else:
            raise ValueError(f"Mercado desconhecido: '{market}' (use us, br, all ou diversified)")

    # remove duplicatas preservando ordem
    seen = set()
    unique_symbols = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            unique_symbols.append(s)
    return unique_symbols
