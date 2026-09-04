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
- **D1** (nova família D, reversão à média pura por banda de Bollinger,
  buscando capturar o zigue-zague do preço): também rejeitada, mesmo
  padrão de V3/V5/V6 — melhora forte no IS (2021-2023), reverte no OOS
  (2018-2020). É a quarta confirmação desse padrão, agora com um
  mecanismo totalmente diferente (Bollinger, não Fibonacci/Volume), o
  que reforça o achado consolidado em vez de ser um caso isolado. Tem o
  melhor recorde de drawdown do projeto (66/66 no walk-forward
  agregado), mas só bate a V1 em Sharpe em 3 das 6 janelas, sem padrão
  de regime que explique a divisão. Detalhes completos em
  `reports/D1_report.md`.

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

## Família C — Momentum Duplo / Rotação de carteira (C1, promissora)

Depois de 7 experimentos rejeitados (V2-V6, B1) — todos tentando
temporizar UM ativo isolado contra o buy-and-hold desse mesmo ativo,
numa cesta de mega caps/blue chips durante um mercado de alta secular —
a decisão foi mudar de família de forma estrutural, não incremental:
em vez de decidir comprar/vender um ativo por vez, a C1 decide **quais**
ativos da cesta segurar, comparando-os entre si (momentum
cross-sectional/relativo). É uma das poucas classes de estratégia
sistemática com evidência acadêmica e prática de edge persistente e
replicado em vários mercados e períodos (Jegadeesh & Titman, 1993;
"Dual Momentum" de Antonacci, 2014) — por isso justifica mais uma
rodada de teste rigoroso em vez de mais uma variante de V ou B.

Regras (`tradebot/backtest_c1.py`):

- Rebalanceamento no último pregão de cada mês-calendário, com o
  retorno acumulado dos últimos 252 pregões (~12 meses, janela clássica
  da literatura de momentum) de cada ativo, decidido no fechamento
  desse dia. Execução no open do primeiro pregão do mês seguinte —
  nunca no mesmo candle da decisão.
- Momentum absoluto: só é candidato quem tiver retorno acumulado do
  período > 0%; sem candidatos suficientes, a vaga fica em caixa (não é
  preenchida por um ativo com momentum negativo).
- Momentum relativo: dos candidatos, entram os 3 melhores (`TOP_K = 3`),
  igualmente ponderados (sizing simples, `1/TOP_K` do caixa disponível
  por entrada — sem rebalanceamento pra peso exato).
- Mesmos custos (`fee_rate`/`slippage_rate`) e universo (US_WATCHLIST +
  BR_WATCHLIST) das famílias V e B. Arquitetura diferente das
  anteriores: é UMA carteira só, alocada entre os ativos ao longo do
  tempo, não uma carteira independente por ativo — o benchmark é o
  buy-and-hold da cesta inteira igualmente ponderada, sem rebalancear.

```bash
python -m tradebot c1 --market all --start 2021-01-01 --end 2023-01-01
python -m tradebot c1 --market all --start 2018-01-01 --end 2020-01-01
python -m tradebot c1 --market all --start 2012-01-01 --end 2024-01-01
```

**Resultado: PROMISSORA** (walk-forward real, 6 janelas de 2 anos,
2012-2024). Não bate o buy-and-hold da cesta de forma robusta (perde em
CAGR/Sortino/Calmar na maioria das janelas), mas é o melhor resultado do
projeto até agora: bate a V1 em Sharpe em 5/6 janelas e em CAGR em 4/6,
mantendo a mesma vantagem de drawdown (6/6 janelas). O padrão de
vitória/derrota é explicável — perde em janelas de alta forte e em linha
reta (fica de fora prejudica), ganha em janelas com correções relevantes
no meio do caminho — ao contrário da inversão sem explicação de regime
vista em V3/V5/V6/B1. Análise completa e recomendação de próximo passo
(testar `TOP_K` maior como C2) em `reports/C1_report.md`.

**C2 (`TOP_K=5`) testada e a hipótese NÃO se confirmou** — diluir de 3
para 5 ativos não reduziu o "cash drag" de forma consistente (Sharpe
médio marginalmente melhor, 1.07 vs 1.03, mas CAGR médio pior, 10.12%
vs 11.87%, e piorou justamente numa das janelas que motivaram o teste).
**Decisão: `TOP_K=3` (configuração original da C1) fica como a
referência da família C.** Detalhes em `reports/C1_report.md`.

**Placebo (C3):** mesma dúvida que já resolvemos pra V3 (V3 vs V4) —
o Sharpe melhor da C1 vem de informação genuína no ranking de momentum,
ou só do mecanismo de girar entre um subconjunto menor da cesta? A C3
(`tradebot/backtest_c3.py`) reaproveita a mesma mecânica da C1
(rebalanceamento mensal, `TOP_K`, sizing, custos) trocando **apenas** a
seleção: em vez de rankear por momentum, sorteia `TOP_K` ativos
aleatoriamente a cada mês (`SEED=42`, mesmo valor já usado no placebo
da V1, sem filtro de momentum absoluto — sempre 100% alocada).

```bash
python -m tradebot c1-placebo --market all --start 2021-01-01 --end 2023-01-01
python -m tradebot c1-placebo --market all --start 2018-01-01 --end 2020-01-01
python -m tradebot c1-placebo --market all --start 2012-01-01 --end 2024-01-01
```

**Resultado: a C1 bate o placebo (C3) em 2 dos 3 testes** — inclusive
no período completo de 12 anos por margem clara (Sharpe 1.05 vs 0.76,
retorno 731.67% vs 304.95%). Só perde no período 2021-2023, a mesma
janela de reversão brusca que é o ponto fraco conhecido de qualquer
estratégia de momentum ("momentum crash"). Ao contrário da V3 (que
perdeu do próprio placebo), a C1 tem informação real no ranking, não é
só efeito de girar entre menos ativos. Análise completa em
`reports/C1_report.md`.

## Família D — Reversão à Média Pura por Faixa (D1, rejeitada)

Pedido do usuário: um sistema que opere com mais frequência, comprando
perto de mínimas locais e vendendo perto de máximas locais — capturando
o zigue-zague do preço dentro de uma faixa, em vez de tentar pegar a
tendência (B1/C1) ou só reduzir exposição (V1). Estruturalmente
diferente das três: é reversão à média pura, um ativo por vez, sem votar
múltiplos indicadores.

Regras (`tradebot/backtest_d1.py`):

- Entrada: `close[t] <= banda_inferior_bollinger[t]` (proxy objetivo e
  sem look-ahead pra "perto de uma mínima local"), execução no open de
  `t+1`.
- Saída-alvo: `close[t] >= banda_superior_bollinger[t]` ("perto de uma
  máxima local"), mesma disciplina de execução no dia seguinte.
- Stop-loss: 6% abaixo do preço de entrada (mesmo valor congelado da
  V1) — protege contra um rompimento de baixa real, já que nem toda
  "mínima local" vira alta.
- Bandas de Bollinger: período 20, 2 desvios-padrão (mesmos parâmetros
  já usados no voto da V1). Sem RSI, MACD, Volume, Fibonacci ou filtro
  de tendência — só a banda, isolada.
- Mesmo sizing, custos e universo (US_WATCHLIST + BR_WATCHLIST) da V1.

```bash
python -m tradebot compare --market all --start 2021-01-01 --end 2023-01-01 --challenger d1
python -m tradebot walkforward --market all --start 2012-01-01 --end 2024-01-01 --window-years 2 --challenger d1
```

**Resultado: EXPERIMENTO REJEITADO.** Melhora forte no IS (2021-2023),
mas a vantagem se inverte no OOS (2018-2020) — o mesmo padrão que já
reprovou V3/V5/V6, agora confirmado pela quarta vez com um mecanismo
totalmente diferente (Bollinger em vez de Fibonacci/Volume), reforçando
o achado consolidado em vez de ser um caso isolado. No walk-forward
completo tem o melhor recorde de drawdown do projeto (66/66), mas só
bate a V1 em Sharpe em 3 das 6 janelas, sem padrão de regime que
explique a divisão. Análise completa em `reports/D1_report.md`.

## Estado atual da pesquisa (decisão, não pergunta em aberto)

Depois de 4 famílias estruturalmente diferentes testadas com o mesmo
rigor (IS/OOS/walk-forward, sem cherry-picking) — V (voto multi-
indicador), B (rompimento de tendência), C (rotação por momentum
cross-sectional) e D (reversão à média por faixa) — a fase de
experimentação ativa está encerrada. Resumo:

- **Rejeitadas**: V2, V3, V5, V6, B1, D1. Todas mostraram o mesmo
  padrão — melhora aparente num recorte, sem sustentar fora da amostra
  — ou giro sem contrapartida.
- **C1 (`TOP_K=3`, `MOMENTUM_LOOKBACK_DAYS=252`) é a única linha com
  resultado favorável** e fica como a referência de qualquer uso futuro
  além do benchmark V1. Não bate o buy-and-hold de forma robusta, mas é
  a primeira estratégia do projeto a bater a V1 de forma consistente
  (Sharpe em 5/6 janelas, CAGR em 4/6) com uma explicação de mecanismo
  plausível (perde só quando o mercado sobe em linha reta sem correção).
  C2 (diluir pra `TOP_K=5`) foi testada e não melhorou o resultado — a
  configuração original é a que fica. O placebo (C3) confirmou que o
  ranking de momentum tem informação real (bate o sorteio aleatório em
  2 dos 3 testes, inclusive no período completo de 12 anos por margem
  clara) — só perde do placebo justamente no período de reversão
  brusca de 2022, o ponto fraco conhecido de qualquer momentum.
- Continuar gerando variante atrás de variante sem uma hipótese nova e
  bem fundamentada é o caminho pro overfitting/data-dredging que este
  projeto foi desenhado pra evitar. Por isso a decisão é parar aqui, não
  seguir "testando mais uma ideia" indefinidamente.

**Recomendação para uso real (ainda 100% simulado/paper):** se algum dia
fizer sentido acompanhar uma estratégia "ao vivo" (sempre em paper
trading), C1 com os parâmetros congelados acima é a candidata — com a
expectativa correta de que ela reduz drawdown de forma consistente e
tem uma leve vantagem de Sharpe sobre a V1, mas não deve ser esperada
para bater simplesmente comprar e segurar os mesmos ativos.

## Teste de robustez do universo (viés de sobrevivência)

Pergunta levantada depois da fase de pesquisa: será que "nada bate
buy-and-hold" é um achado sobre técnica de trading, ou um artefato de
testar contra uma cesta concentrada em 5 mega caps de tecnologia dos
EUA (AAPL, MSFT, NVDA, AMZN, GOOGL) — vencedoras conhecidas em
retrospecto, incluindo o rali de IA da NVDA, um dos maiores retornos de
ação única da história recente? Isso é diferente de "testar mais uma
variante de estratégia" — é testar um viés no próprio desenho do
experimento, por isso reabrir essa pergunta específica não contradiz a
decisão de fechar a fase de novas técnicas.

`US_DIVERSIFIED_WATCHLIST` (`tradebot/markets.py`) substitui as 5 mega
caps de tecnologia por 5 ações grandes e líquidas de setores
DIFERENTES — Financeiro (JPM), Saúde (JNJ), Consumo básico (PG),
Energia (XOM), Industrial (CAT) — escolhidas por representar setores
diferentes, não por terem tido retorno bom ou ruim (decidido antes de
rodar qualquer teste, mesma disciplina do resto do projeto). A cesta
brasileira (`BR_WATCHLIST`) já era razoavelmente diversificada e fica
igual. Novo `--market diversified` usa essa cesta.

```bash
python -m tradebot backtest --market diversified --start 2012-01-01 --end 2024-01-01
python -m tradebot c1 --market diversified --start 2012-01-01 --end 2024-01-01
python -m tradebot compare --market diversified --start 2021-01-01 --end 2023-01-01
```

**Resultado: a suspeita se confirma.** No universo diversificado, a C1
bate o Sharpe do buy-and-hold nos 3 testes (IS, OOS e período
completo) — a primeira vez em todo o projeto que isso acontece de
forma consistente:

| Período | Sharpe C1 | Sharpe B&H |
|---|---|---|
| IS 2021-2023 | **0.94** | 0.87 |
| OOS 2018-2020 | **1.42** | 1.02 |
| Completo 2012-2024 | **0.73** | 0.71 |

O buy-and-hold do período completo também caiu de +4011% (cesta de
tech) pra +798% (cesta diversificada) — a NVDA sozinha explicava a
maior parte da distância "impossível de bater" que víamos antes. CAGR/
Sortino/Calmar ainda não vencem de forma consistente, mas a distância
encolheu bastante. Boa parte do "nada bate buy-and-hold" das famílias
V/B/D era mesmo um artefato da cesta de teste, não uma verdade
universal sobre timing de mercado. Análise completa em
`reports/C1_report.md`.

## Teste de universo cripto (Binance, viés de sobrevivência estrutural)

Pedido do usuário. `CRYPTO_WATCHLIST` (`tradebot/markets.py`) traz as 5
criptomoedas de maior capitalização negociadas na Binance — BTC-USD,
ETH-USD, BNB-USD, SOL-USD, XRP-USD (tickers yfinance, sem precisar de
conta/API da corretora).

**Aviso importante, diferente do universo diversificado acima:** aqui
o viés de sobrevivência é estrutural e não dá pra neutralizar do mesmo
jeito. "Top 5 por capitalização hoje" é, quase por definição, "as 5 que
mais valorizaram desde que foram lançadas" — a esmagadora maioria das
milhares de criptomoedas que já existiram (era ICO 2017-2018,
principalmente) não existe mais ou vale perto de zero, e não há como
reconstruir de graça "o top 5 por capitalização em cada ano". Esse
teste mostra como a C1 se comporta num mercado de altíssima
volatilidade e giro 24/7 — não é um teste livre de viés, e deve ser
lido com essa ressalva.

Histórico disponível é desigual: BTC-USD desde ~2014, ETH/BNB/XRP desde
~2017, SOL-USD só desde ~2020 (rede lançada em 2020) — pra períodos
antes de abril/2020, tire `SOL-USD` da lista com `--symbols` em vez de
`--market crypto`.

```bash
python -m tradebot c1 --market crypto --start 2021-01-01 --end 2023-01-01
python -m tradebot c1 --market crypto --start 2020-05-01 --end 2024-01-01
```

**Resultado: oposto ao das ações — a C1 perde do buy-and-hold em
risco-ajustado nos dois testes**, não só em retorno bruto:

| Período | Sharpe C1 | Sharpe B&H |
|---|---|---|
| 2021-2023 (inclui colapsos de Terra/Luna e FTX) | -0.31 | **0.89** |
| 2020-05 a 2024-01 | 0.94 | **1.24** |

Diferente do universo diversificado de ações, aqui o edge não se
sustenta. Hipótese (não confirmada): as 5 criptos são fortemente
correlacionadas entre si, o que reduz o valor de um ranking
cross-sectional (que depende de dispersão real entre os ativos), e a
volatilidade extrema de cripto (drawdowns de -80% a -91%) machuca mais
uma estratégia de momentum. **Conclusão: o edge da C1 não é universal**
— funciona melhor em ações diversificadas com correlação mais baixa,
não em cripto. Análise completa em `reports/C1_report.md`.

## Dados intraday de cripto via Binance (sem chave de API)

O yfinance só guarda poucos dias de candle de minuto — não dá pra fazer
um backtest intraday sério com isso. `tradebot/binance_data.py` busca
candles direto da API pública da Binance (`/api/v3/klines`), que não
exige autenticação nem chave — só dado de mercado público, com anos de
histórico intraday de verdade.

**Roteamento automático**: qualquer símbolo terminado em `USDT` (ex:
`BTCUSDT`, `ETHUSDT`) é buscado na Binance em vez do yfinance — mesmo
formato de saída, então todas as famílias (V-E) já funcionam sem
nenhuma mudança:

```bash
python -m tradebot backtest --symbol BTCUSDT --interval 1h --period 3mo
python -m tradebot c1 --symbols BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT --interval 4h --period 6mo
```

**Sobre a chave de API**: este projeto só chama o endpoint público de
candles — nunca endpoint de conta, ordem, ou qualquer coisa que exija
autenticação, consistente com o resto do projeto (100% paper trading,
nenhuma ordem real é enviada a lugar nenhum). Uma chave de API não é
necessária pra nada do que este bot faz. Se algum dia for útil pra
limite de taxa mais alto, seria só a chave pública como header, lida de
variável de ambiente — **nunca cole chave nem secret no código ou no
histórico do repositório.**

Isso abre a porta pra testar estratégias de giro mais rápido (a família
D — reversão à média por faixa — nunca foi testada em candle de 1h/4h,
só diário) com histórico de verdade, não só os últimos dias.

## Venda a descoberto (short) — infraestrutura nova

Até aqui a carteira só suportava posição comprada (long-only), o que
eliminava de cara toda uma classe de estratégia (pairs trading, mercado
neutro) que não depende de o mercado subir pra dar lucro. Diferente das
outras limitações do projeto (rede bloqueada, sem dado intraday
histórico de qualidade, sem fundamentalista point-in-time sem viés de
look-ahead), essa era pura limitação de código, sem depender de nenhum
dado externo — por isso foi resolvida.

`Portfolio.short()`/`Portfolio.cover()` (`tradebot/portfolio.py`) abrem
e fecham posição vendida, com a mesma lógica de taxa/slippage do
`buy()`/`sell()`. **Simplificação documentada:** não modela chamada de
margem nem custo de aluguel de ação (borrow cost) — o caixa recebido na
venda a descoberto é tratado como caixa disponível pra uso, o que é
mais otimista que uma conta margem real. `compute_round_trip_pnls()`
já trata os dois lados (comprado e vendido) simetricamente.

## Família E — Pairs Trading / Mercado Neutro (E1, em teste)

Primeira estratégia do projeto que não depende do mercado subir pra dar
lucro: em vez de apostar na direção de um ativo, aposta na
**convergência** da relação de preço entre dois ativos do mesmo setor —
compra o que ficou relativamente barato e vende a descoberto o que
ficou relativamente caro, lucrando quando o spread volta ao normal.
Estruturalmente diferente de V/B/C/D, só possível agora que a carteira
suporta short.

Pares testados (`tradebot/backtest_e1.py`), escolhidos por lógica de
setor — concorrentes diretos, líquidos — **antes** de calcular qualquer
correlação ou rodar qualquer teste:

- `ITUB4.SA` / `BBDC4.SA` — os dois maiores bancos privados do Brasil
  (já presentes em `BR_WATCHLIST`).
- `XOM` / `CVX` — as duas maiores petroleiras integradas dos EUA.

Regras:

- Spread: `log(close_A) - log(close_B)`. Z-score móvel numa janela de
  60 pregões (causal, sem look-ahead).
- Entrada: `|z-score| >= 2.0` (vende o lado caro, compra o barato).
- Saída: `|z-score| <= 0.5` (convergência) ou `|z-score| >= 4.0` (stop —
  o par pode ter quebrado estruturalmente). Decisão sempre no
  fechamento de `t`, execução das duas pernas no open de `t+1`.
- Benchmark: caixa parado (0%), não buy-and-hold — a estratégia é
  desenhada pra ser neutra ao mercado, comparar com B&H mediria
  exposição direcional, não qualidade da convergência.

```bash
python -m tradebot e1 --start 2018-01-01 --end 2024-01-01
```

Resultado: em aberto — ainda não foi rodado contra dados reais.

## Rodando os testes

```bash
PYTHONPATH=. python -m pytest tests/ -q
```

## Estrutura

```
trade-bot/
  tradebot/
    data.py        Coleta de dados (yfinance; roteia pra Binance símbolos "USDT")
    binance_data.py Candles intraday via API pública da Binance (sem chave)
    indicators.py  SMA, EMA, RSI, MACD, Bandas de Bollinger
    strategy.py     Combina indicadores em um sinal (BUY/SELL/HOLD)
    portfolio.py    Carteira simulada (caixa, posições, taxas, slippage, compra e venda a descoberto)
    backtest.py     V1: roda a estratégia sobre histórico, métricas (Sharpe/
                    Sortino/Calmar/CAGR/Profit Factor) e relatório
    backtest_v2.py  Experimentos alternativos (V2 rejeitada) + comparação V1×V2
    backtest_b1.py  Família B: B1, rompimento puro (trend following)
    backtest_c1.py  Família C: C1, momentum duplo cross-sectional (rotação de carteira)
    backtest_c3.py  Placebo aleatório da C1 (mesma mecânica, seleção sorteada)
    backtest_d1.py  Família D: D1, reversão à média pura por banda de Bollinger (zigue-zague)
    backtest_e1.py  Família E: E1, pairs trading / mercado neutro (usa short)
    walkforward.py  Roda a estratégia congelada em janelas sequenciais (V1 ou outra, via backtest_fn)
    live.py         Loop de paper trading com persistência de estado
    charts.py       Gráficos PNG (preço, indicadores, sinais de compra/venda)
    markets.py      Watchlists prontas (EUA, Bovespa, EUA diversificado, cripto) e resolução de símbolos
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
