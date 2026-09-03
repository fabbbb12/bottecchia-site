# Polymarket Alpha Lab — Fase 1

Infraestrutura de pesquisa quantitativa para responder uma pergunta
específica, com dados reais e sem look-ahead:

> **Existem oportunidades de arbitragem interna no Polymarket
> suficientemente frequentes, líquidas e grandes para produzir lucro
> líquido após custos?**

Este projeto **não** move dinheiro real e **não** é um bot de execução.
É a Fase 1: construir a infraestrutura, rodar o experimento, e responder
com honestidade se existe edge — inclusive se a resposta for "não".

## ⚠️ Aviso importante sobre os endpoints da API

Este projeto foi desenvolvido num ambiente cuja rede **bloqueia** acesso
a `docs.polymarket.com` e aos domínios da API (`gamma-api.polymarket.com`,
`clob.polymarket.com`). Isso significa que:

- Os endpoints e nomes de campo em `collectors/client.py` e
  `normalization/normalize.py` foram escritos com base em conhecimento
  geral sobre a API pública da Polymarket, **sem confirmação ao vivo**.
- `config/settings.yaml` tem `verified_against_docs: false` de propósito
  — o comando `scan` imprime um aviso enquanto isso não for corrigido.

**Antes de rodar `collect` de verdade:**
1. Abra https://docs.polymarket.com e confirme os caminhos da Gamma API
   (listar markets/events) e da CLOB API (order book, preços, trades).
2. Ajuste `config/settings.yaml` e `collectors/client.py` se os caminhos
   ou nomes de parâmetro tiverem mudado.
3. Rode `collect` para um punhado de mercados, compare um payload real
   com o mapeamento em `normalization/normalize.py` (campos como
   `conditionId`, `clobTokenIds`, `outcomes`) e ajuste se necessário.
4. Só depois disso marque `verified_against_docs: true`.

Toda a lógica que **não** depende da API real (matemática de
arbitragem, VWAP/execução, taxas, banco de dados, motor de backtest,
métricas, relatório) já está implementada e testada — 67 testes
cobrindo isso, incluindo o cenário explícito da Seção 19: *uma
oportunidade aparente no topo do book desaparece quando a profundidade
real é considerada* (`tests/test_yes_no.py::test_opportunity_disappears_when_real_depth_considered`).

## Instalação

```bash
cd polymarket_alpha
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python main.py collect                      # coleta mercados/eventos (Gamma API)
python main.py scan                          # varre o banco, registra TODAS as oportunidades candidatas
python main.py scan --oos-start 1717200000   # marca oportunidades depois desse epoch como out-of-sample
python main.py backtest                      # resolve oportunidades pendentes contra `resolutions`
python main.py report                        # gera reports/phase_1_report.md
```

`collect` só busca metadados de mercados/eventos (paginado, uma chamada
por página). Order book, preços e trades por token são coletados à
parte, chamando diretamente:

```python
from collectors.client import PolymarketClient
from collectors.orderbook import collect_order_book_snapshot
from collectors.prices import collect_price_history
from collectors.trades import collect_trades
from db import get_connection

conn = get_connection()
client = PolymarketClient()
collect_order_book_snapshot(conn, client, token_id="...")
```

Isso é proposital: coletar o book de milhares de tokens em toda rodada de
`collect` seria caro e provavelmente violaria rate limits — melhor
escolher os tokens de interesse (ex: mercados ativos e líquidos) e
agendar a coleta de book/trades separadamente, em intervalos frequentes,
enquanto `collect` (metadados) roda com menos frequência.

## Rodando os testes

```bash
PYTHONPATH=. python -m pytest tests/ -q
```

## Estrutura

```
polymarket_alpha/
  db.py                Schema SQLite (markets, tokens, price_history,
                        orderbook_snapshots, trades, resolutions, opportunities)
  execution.py          VWAP/slippage a partir da profundidade real do book (Seção 6)
  fees.py               Custos configuráveis (config/fees.yaml)
  config/
    settings.yaml       Base URLs da API + período IS/OOS (Seção 16)
    fees.yaml           Estrutura de taxas usada nos experimentos
  collectors/
    client.py           Cliente HTTP fino (endpoints NÃO verificados -- ver aviso acima)
    markets.py           Coleta markets/events + tokens
    orderbook.py          Coleta snapshot de order book de um token
    prices.py             Coleta histórico de preço de um token
    trades.py             Coleta trades de um token
  normalization/
    normalize.py         JSON bruto da API -> linhas de banco (100% testável sem rede)
  arbitrage/
    yes_no.py            Detecção + tamanho executável de arbitragem YES+NO (Seção 5)
    multi_outcome.py      Idem para N outcomes, com checagem de estrutura (Seção 7)
    relationships.py      Framework de relações declaradas manualmente (Seção 8)
    scan.py               Varre o banco e grava todas as oportunidades candidatas (Seção 9)
  backtest/
    engine.py            Resolução temporal sem look-ahead (Seções 10-11)
  analysis/
    metrics.py            Frequência, edge, execução, duração, resultado (Seção 13)
  reports/
    generator.py          Relatório Markdown final + classificação (Seções 17-18)
  main.py                CLI: collect / normalize / scan / backtest / report
  tests/                 67 testes, tudo que não depende de rede real
```

## O que este projeto NÃO faz (por design, Seção 1)

Market making, copy trading, wallets reais, ML, NLP, notícias, outros
prediction markets, execução real, otimização de parâmetros pra
maximizar lucro histórico. Isso é deliberado — o objetivo da Fase 1 é
só provar (ou refutar) que existe edge, não construir um produto.

## Sobre a classificação de mercados multi-outcome

`SUM(ASK_i) < 1` **não** é arbitragem automaticamente. `scan_multi_outcome`
só trata como oportunidade executável quando `markets.mutually_exclusive`
e `markets.collectively_exhaustive` estão **explicitamente** marcados
como `1` no banco — isso precisa ser preenchido manualmente depois de
olhar a estrutura real de cada evento (nunca inferido automaticamente,
nada de NLP nesta fase). Sem essa confirmação, a oportunidade é
registrada (para não gerar viés de sobrevivência) mas com
`capital_executable = 0`.

## Próximos passos depois da Fase 1

Só depois de rodar `collect` de verdade (endpoints verificados), coletar
book/trades de um conjunto relevante de mercados por um período
razoável, rodar `scan` + `backtest` + `report`, e ler a classificação
final de cada hipótese — decidir se vale a pena investir em Fase 2
(execução real, mais estratégias, mais dados). Não pular etapas.
