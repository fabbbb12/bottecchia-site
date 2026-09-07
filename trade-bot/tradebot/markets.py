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

# Cripto de maior capitalização de mercado negociadas na Binance
# (tickers yfinance no formato "-USD", sem precisar de conta/API da
# corretora). AVISO IMPORTANTE, diferente do aviso da US_DIVERSIFIED_
# WATCHLIST: aqui o viés de sobrevivência é ESTRUTURAL e não dá pra
# neutralizar do mesmo jeito. "Top 5 por capitalização de mercado HOJE"
# é, quase por definição, "as 5 que mais valorizaram desde que foram
# lançadas" — a esmagadora maioria das milhares de criptomoedas que
# existiram (era ICO 2017-2018 principalmente) já não existe mais ou
# vale perto de zero, e não tem como reconstruir "o top 5 por
# capitalização em cada ano" de graça/sem dado pago. Esse teste mostra
# como a C1 se comporta num mercado de altíssima volatilidade e giro
# 24/7 — não é um teste livre de viés de sobrevivência, e deve ser lido
# com essa ressalva.
#
# Histórico disponível no yfinance é desigual: BTC-USD desde ~2014,
# ETH-USD/BNB-USD/XRP-USD desde ~2017, SOL-USD só desde ~2020 (a rede
# Solana foi lançada em 2020) — para períodos anteriores a 2020-04, tire
# SOL-USD da lista ou use --start a partir dessa data.
CRYPTO_WATCHLIST = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"]

# Extensão direta da US_DIVERSIFIED_WATCHLIST: a C1 mostrou edge real
# de Sharpe sobre a V1 e sobre buy-and-hold no universo diversificado
# de 5 ativos (ver reports/C1_report.md) — hipótese de que correlação
# mais baixa entre ativos ajuda o ranking de momentum cross-sectional.
# Esta lista testa se isso se sustenta (ou fica ainda melhor) num
# universo bem maior: 2 ações grandes e líquidas por setor GICS (11
# setores x 2 = 22), escolhidas ANTES de rodar qualquer teste, pela
# mesma regra de sempre (nome grande e conhecido do setor, não retorno
# passado). Evita deliberadamente as 5 mega caps de tecnologia já
# excluídas da US_DIVERSIFIED_WATCHLIST (AAPL, MSFT, NVDA, AMZN, GOOGL)
# — MSFT aqui é o único repetido, como representante de Tecnologia.
US_BROAD_WATCHLIST = [
    "MSFT", "CSCO",   # Tecnologia
    "JPM", "BAC",     # Financeiro
    "JNJ", "UNH",     # Saúde
    "HD", "MCD",      # Consumo discricionário
    "PG", "KO",       # Consumo básico
    "XOM", "CVX",     # Energia
    "CAT", "HON",     # Industrial
    "NEE", "DUK",     # Utilidades
    "LIN", "SHW",     # Materiais
    "PLD", "AMT",     # Imobiliário
    "VZ", "DIS",      # Comunicação
]

# TOP_K proporcional ao tamanho do universo, pra manter o mesmo nível
# de concentração da C1 original (3 de 11 = ~27%): 7 de 22 = ~32%,
# decidido agora, antes de qualquer resultado — não depois de ver o
# que "funcionaria melhor".
BROAD_TOP_K = 7


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
        elif market == "crypto":
            symbols.extend(CRYPTO_WATCHLIST)
        elif market == "broad":
            symbols.extend(US_BROAD_WATCHLIST + BR_WATCHLIST)
        else:
            raise ValueError(f"Mercado desconhecido: '{market}' (use us, br, all, diversified, crypto ou broad)")

    # remove duplicatas preservando ordem
    seen = set()
    unique_symbols = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            unique_symbols.append(s)
    return unique_symbols
