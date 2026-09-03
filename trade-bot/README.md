# Trade Bot — Análise Técnica e Execução Simulada (Paper Trading)

> ⚠️ **Este bot NÃO executa ordens reais em nenhuma corretora ou exchange.**
> Todo "dinheiro" e todas as "ordens" são simulados localmente (paper
> trading). Não há chaves de API de corretora, não há risco de perda real.
> Este projeto é independente do site institucional — vive apenas na pasta
> `trade-bot/` e não afeta o site de forma alguma.

## O que ele faz

1. **Coleta dados de mercado** públicos via [`yfinance`](https://pypi.org/project/yfinance/)
   — funciona com ações (`PETR4.SA`, `AAPL`), índices e criptomoedas
   (`BTC-USD`, `ETH-USD`), sem precisar de conta ou API key.
2. **Analisa** o preço com uma combinação de indicadores técnicos clássicos:
   - Cruzamento de médias móveis (tendência)
   - RSI (sobrecompra/sobrevenda)
   - MACD (momentum)
   - Bandas de Bollinger (reversão à média)

   Cada indicador "vota" (compra/venda/neutro); os votos são somados com
   pesos configuráveis e comparados a limiares para decidir `BUY`, `SELL`
   ou `HOLD`. Isso evita depender de um único indicador isolado.
3. **"Executa"** a decisão em uma carteira simulada (`Portfolio`): desconta
   taxa e slippage, atualiza caixa/posição e guarda o histórico de ordens.
4. Pode rodar em dois modos:
   - `backtest`: aplica a estratégia sobre um histórico e mostra o resultado.
   - `live`: repete o ciclo (buscar preço → decidir → simular ordem) em
     intervalos configuráveis, salvando o estado da carteira em disco entre
     execuções — ainda 100% simulado.

## Instalação

```bash
cd trade-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

O foco atual é **swing trade em ações (EUA e Bovespa)**, com candles diários
— dados mais estáveis e confiáveis para backtest do que cripto (24/7, sem
circuit breaker) ou intraday (histórico curto e de qualidade inferior no
`yfinance`).

Backtest de um único ativo (histórico de 1 ano, candles diários):

```bash
python -m tradebot backtest --symbol AAPL --period 1y --interval 1d --cash 10000
python -m tradebot backtest --symbol PETR4.SA --period 1y --interval 1d
```

Backtest comparativo usando as watchlists prontas (EUA, Bovespa ou ambas):

```bash
python -m tradebot backtest --market us --period 1y
python -m tradebot backtest --market br --period 1y
python -m tradebot backtest --market all --period 1y
```

Ou uma lista própria de símbolos, separada por vírgula:

```bash
python -m tradebot backtest --symbols AAPL,MSFT,PETR4.SA,VALE3.SA --period 1y
```

Modo "ao vivo" simulado — ainda um único símbolo por vez (verifica a cada
hora, salva estado em `state/`):

```bash
python -m tradebot live --symbol PETR4.SA --interval 1d --poll-seconds 3600
```

Use `--iterations N` no modo `live` para limitar o número de ciclos (útil
para testar sem rodar indefinidamente).

## Rodando os testes

```bash
PYTHONPATH=. python -m pytest tests/ -q
```

## Estrutura

```
trade-bot/
  tradebot/
    data.py        Coleta de dados (yfinance)
    indicators.py  SMA, EMA, RSI, MACD, Bandas de Bollinger
    strategy.py     Combina indicadores em um sinal (BUY/SELL/HOLD)
    portfolio.py    Carteira simulada (caixa, posições, taxas, slippage)
    backtest.py     Roda a estratégia sobre histórico e gera relatório
    live.py         Loop de paper trading com persistência de estado
    cli.py          Interface de linha de comando
  tests/            Testes unitários (indicadores, estratégia, carteira)
```

## Ajustando a estratégia

Os parâmetros ficam em `tradebot/strategy.py`, na classe `StrategyConfig`
(períodos das médias, RSI, MACD, Bandas de Bollinger, pesos de cada voto e
limiares de compra/venda). Ajuste esses valores e rode o backtest de novo
para comparar resultados antes de mudar o comportamento do modo `live`.

## Caminho para execução real (fora do escopo atual)

Se um dia decidir conectar a uma corretora/exchange de verdade, isso exige,
no mínimo:

- Um módulo de execução específico da corretora escolhida (API própria),
  com chaves de API armazenadas de forma segura (nunca no código-fonte).
- Controles de risco explícitos (limite de perda diária, tamanho máximo de
  posição, circuit breaker).
- Testes extensivos em paper trading e/ou conta demo antes de qualquer
  execução com dinheiro real.
- Aviso legal: isto não é recomendação de investimento; resultados
  passados (inclusive em backtest) não garantem resultados futuros.
