# Trade Bot — Análise Técnica e Execução Simulada (Paper Trading)

> ⚠️ **Este bot NÃO executa ordens reais em nenhuma corretora ou exchange.**
> Todo "dinheiro" e todas as "ordens" são simulados localmente (paper
> trading). Não há chaves de API de corretora, não há risco de perda real.
> Este projeto é independente do site institucional — vive apenas na pasta
> `trade-bot/` e não afeta o site de forma alguma.

## Conclusão da fase de pesquisa (leia isto primeiro)

Depois de validar a estratégia em 3 períodos isolados, um walk-forward de
12 anos (6 janelas, 66 combinações janela×ativo) e um experimento de
reentrada (V2), a caracterização final é:

**A estratégia (V1, congelada em `tradebot/strategy.py`) é um sistema de
redução de drawdown, não um gerador de retorno superior ao buy-and-hold.**

- **Máx. drawdown: vitória robusta e consistente** — 6/6 janelas do
  walk-forward, 53/66 combinações janela×ativo. A estratégia perde menos
  no pior momento, de forma estável ao longo de 12 anos e regimes de
  mercado diferentes.
- **Retorno, CAGR, Sharpe, Sortino, Calmar: sem vantagem** — 0-1 das 6
  janelas, 13-21 das 66 combinações. Não é distorção de outlier (mediana e
  contagem de vitórias confirmam a mesma coisa que a média).
- **Quatro experimentos testados depois da V1, todos rejeitados:**
  - **V2** (reentrada antecipada após venda): piorou retorno e
    Sharpe/Sortino, com mais giro sem contrapartida.
  - **V3** (filtro de Fibonacci na entrada): reduz drawdown de forma
    real e confirmada contra um placebo aleatório, mas corta trade bom
    junto com trade ruim — retorno piora, perdeu até para o placebo.
  - **V5** (Fibonacci como tamanho de posição em vez de filtro):
    resultado inconsistente entre períodos — melhora num, piora no
    outro, na mesma métrica.
  - **V6** (filtro de Volume Relativo): mesmo padrão da V3 — melhora
    forte no período 2021-2023, reverte no OOS 2018-2020.
  - **Achado consolidado**, confirmado com um placebo (V4, corte
    aleatório de trades na mesma proporção): filtros "espertos"
    baseados em preço ou volume carregam um viés de seleção
    **dependente do regime de mercado** — ajudam a evitar trades ruins
    em mercado de vaivém e atrapalham ao evitar trades bons em
    tendência sustentada. Um corte aleatório de mesmo tamanho não tem
    esse viés, sendo paradoxalmente mais seguro que os filtros
    "inteligentes" se o objetivo é só reduzir drawdown. Detalhes em
    `tradebot/backtest_v2.py`, `backtest_v3.py`, `backtest_v5.py` e
    `backtest_v6.py` — mantidos no repositório como registro dos
    experimentos, não como algo a usar.
- **B1** (nova família B, trend following/rompimento puro, estruturalmente
  diferente da V1-V6): também rejeitada. Supera a V1 em retorno/Sharpe/
  Sortino/Calmar no período IS (2021-2023), mas essa vantagem se
  **inverte** no OOS (2018-2020) — mesma dependência de período que
  já reprovou V3/V5/V6, sem um padrão de regime limpo dessa vez. A
  única propriedade consistente é um corte de drawdown ainda mais
  agressivo que o da própria V1 (drawdown quase pela metade em valor
  absoluto, 65/66 combinações vencendo o buy-and-hold), mas isso não é
  novo — é a mesma característica da V1, só mais extrema, trocando
  ainda mais retorno por menos dor. Nunca bate o buy-and-hold. Detalhes
  completos em `reports/B1_report.md` e `tradebot/backtest_b1.py`.

Ou seja: útil para quem valoriza uma trajetória com menos dor no pior
momento e aceita abrir mão de retorno para isso; **não é** uma estratégia
que bate o mercado em retorno ajustado ao risco. Antes de considerar
paper trading com dinheiro (mesmo simulado) de verdade, essa é a
expectativa correta a ter sobre o que o bot entrega.

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
   Além do sinal dos indicadores, há gestão de risco por posição
   (`tradebot/strategy.py::apply_risk_management`): um **stop-loss fixo**
   (`stop_loss_pct`) corta perdas cedo, e um **trailing stop baseado em ATR**
   (volatilidade recente do próprio ativo, `trailing_atr_mult`) protege o
   lucro sem cortar tendências longas cedo demais nem vender por oscilação
   normal em ativos mais voláteis.
4. Pode rodar em dois modos:
   - `backtest`: aplica a estratégia sobre um histórico, mostra o resultado
     e compara contra **buy-and-hold** (comprar e segurar o ativo sem
     estratégia nenhuma) no mesmo período — se a estratégia não superar o
     buy-and-hold, ela não está agregando valor.
   - `live`: repete o ciclo (buscar preço → decidir → simular ordem) em
     intervalos configuráveis, salvando o estado da carteira em disco entre
     execuções — ainda 100% simulado.
5. **Gera gráficos** (`--chart`) com preço, médias móveis, Bandas de
   Bollinger, RSI e MACD, com marcadores de compra/venda sobre o preço —
   tanto no backtest quanto no modo `live` (nesse caso, o arquivo é
   sobrescrito a cada ciclo, funcionando como um acompanhamento "ao vivo").

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

Adicione `--chart` a qualquer um dos comandos acima para salvar gráficos PNG
em `charts/` (um por símbolo), com preço, médias, Bollinger, RSI, MACD e
marcadores de compra/venda:

```bash
python -m tradebot backtest --symbol AAPL --period 1y --chart
```

Modo "ao vivo" simulado — ainda um único símbolo por vez (verifica a cada
hora, salva estado em `state/`, e com `--chart` atualiza o gráfico a cada
ciclo — basta manter o arquivo aberto num visualizador de imagens):

```bash
python -m tradebot live --symbol PETR4.SA --interval 1d --poll-seconds 3600 --chart
```

Use `--iterations N` no modo `live` para limitar o número de ciclos (útil
para testar sem rodar indefinidamente).

## Validação fora da amostra (out-of-sample)

**Importante:** ajustar parâmetros olhando sempre o mesmo período histórico
e escolher a combinação que "deu mais lucro" é uma armadilha clássica
(overfitting) — o bot aprende a decorar o passado, não a lidar com o
futuro. Depois de qualquer ajuste na estratégia, valide numa janela de
tempo que **não** foi usada para ajustar nada, usando `--start`/`--end`
(datas fixas) em vez de `--period` (que é sempre relativo a hoje):

```bash
# Ajustou parâmetros olhando os últimos 2 anos? Teste numa janela anterior,
# nunca vista, antes de confiar no resultado:
python -m tradebot backtest --market all --start 2018-01-01 --end 2020-01-01 --chart
```

Se a estratégia só performa bem no período usado para ajustar e vai mal
fora dele, o resultado bom foi coincidência, não capacidade real.

O passo mais rigoroso é *walk-forward*: repetir esse teste em várias
janelas sequenciais e não sobrepostas, sem ajustar nenhum parâmetro em
nenhuma janela (não há etapa de "treino" — a estratégia já está congelada
antes de rodar):

```bash
python -m tradebot walkforward --market all --start 2012-01-01 --end 2024-01-01 --window-years 2
```

O relatório mostra três camadas: por janela, consistência entre janelas
(em quantas delas a estratégia superou o buy-and-hold, métrica por
métrica) e o agregado geral com todas as combinações janela×ativo juntas.

## Comparando versões da estratégia (V1 vs V2)

`tradebot/backtest_v2.py` guarda experimentos alternativos que reaproveitam
o mesmo motor da V1 mas mudam uma única regra por vez (nunca os parâmetros
já validados). Para comparar lado a lado com o buy-and-hold:

```bash
python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01
```

O relatório mostra média, mediana e contagem de vitórias (V2 supera V1, V2
supera B&H, V1 supera B&H) para cada métrica — critério de aprovação de
uma V2 nova: precisa melhorar retorno e/ou Sharpe/Sortino de forma clara e
robusta (mediana + vitórias, não só média) sem piorar muito o drawdown da
V1, confirmado depois em OOS e walk-forward antes de qualquer uso real.

## Família B — Trend Following / Breakout (B1, rejeitada)

A família V (V1-V6, acima) testou variações de um sistema de votos com
reversão à média. A família B testa uma ideia estruturalmente diferente:
seguir tendência via rompimento de máxima. A B1 (`tradebot/backtest_b1.py`)
é a primeira hipótese dessa família — **rejeitada** (ver
`reports/B1_report.md` para a análise completa: bate a V1 no IS mas
perde no OOS, sem padrão de regime que explique a inversão; único ponto
consistente é um corte de drawdown ainda maior que o da V1, não uma
vantagem de retorno ajustado ao risco). Regras testadas:

- Entrada: `close[t] > highest_high_N[t]` (máxima das máximas dos `N`
  candles ANTERIORES, `N = 20` congelado), execução no open de `t+1`.
- Saída: stop inicial `entrada - 2×ATR` e trailing `pico de fechamento -
  3×ATR` (o maior dos dois vale a cada dia), violação decidida no
  fechamento de `t`, execução no open de `t+1`. Nunca se usa o
  high/low do próprio candle da decisão para executar no mesmo candle.
- Sem RSI, MACD, Bollinger, Fibonacci, Volume ou qualquer outro filtro —
  ATR só é usado para stop, nunca como filtro de entrada.
- Mesmo sizing, custos e universo (US_WATCHLIST + BR_WATCHLIST) da V1.

```bash
python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01 --challenger b1
python -m tradebot walkforward --market all --start 2012-01-01 --end 2024-01-01 --window-years 2 --challenger b1
```

Teste de sensibilidade (`breakout_period` 10/20/40) e placebo ficaram
propositalmente de fora — o resultado principal (IS + OOS + walk-forward,
ver `reports/B1_report.md`) já foi negativo o bastante pra fechar o
experimento sem precisar deles. Comandos deixados aqui só como referência,
caso alguém queira reabrir a investigação:

```bash
python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01 --challenger b1 --breakout-period 10
python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01 --challenger b1 --breakout-period 20
python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01 --challenger b1 --breakout-period 40
```

**Resultado: EXPERIMENTO REJEITADO.** Ver `reports/B1_report.md` para a
análise completa (IS, OOS, walk-forward, respostas às perguntas A-I e
classificação).

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
    backtest.py     V1: roda a estratégia sobre histórico, métricas (Sharpe/
                    Sortino/Calmar/CAGR/Profit Factor) e relatório
    backtest_v2.py  Experimentos alternativos (V2 rejeitada) + comparação V1×V2
    backtest_b1.py  Família B: B1, rompimento puro (trend following)
    walkforward.py  Roda a estratégia congelada em janelas sequenciais (V1 ou outra, via backtest_fn)
    live.py         Loop de paper trading com persistência de estado
    charts.py       Gráficos PNG (preço, indicadores, sinais de compra/venda)
    markets.py      Watchlists prontas (EUA, Bovespa) e resolução de símbolos
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
