# B1 — Rompimento puro (família B, Trend Following/Breakout)

**Status: EXPERIMENTO REJEITADO.** Não há evidência robusta e consistente
de vantagem de retorno ajustado ao risco da B1 sobre a V1 nem sobre
buy-and-hold. A única propriedade que se mantém estável em todas as
janelas é a redução de drawdown — mas isso não é uma descoberta nova (a
V1 já tem essa característica), é apenas uma versão mais agressiva do
mesmo tipo de proteção, obtida abrindo mão de mais retorno.

## O que foi testado

Hipótese: comprar quando o preço rompe a máxima dos últimos 20 períodos
(`close[t] > highest_high_20[t]`, sem olhar RSI, MACD, Bollinger,
Fibonacci, Volume ou ADX) captura o início de tendências de forma
suficiente pra produzir vantagem de retorno ajustado ao risco robusta
sobre buy-and-hold e sobre a V1 (sistema de votos, benchmark congelado).

Execução: entrada decidida no fechamento de `t`, executada no open de
`t+1`; stop inicial `entrada - 2×ATR`; trailing `pico de fechamento -
3×ATR`; saída decidida no fechamento de `t`, executada no open de `t+1`
(nunca no mesmo candle da decisão — ver `tradebot/backtest_b1.py` para o
detalhamento). Parâmetros congelados: `breakout_period=20`,
`initial_atr_mult=2.0`, `trailing_atr_mult=3.0`, `atr_period=14`. Mesmo
sizing, custos (`fee_rate=0.001`, `slippage_rate=0.0005`,
`cash_fraction=0.5`) e universo (US_WATCHLIST + BR_WATCHLIST, 11 ativos)
da V1.

Nenhum parâmetro foi ajustado depois de ver qualquer resultado. O teste
de sensibilidade (`breakout_period` 10/20/40) e a discussão sobre um
placebo específico pra essa família ficam para depois desta conclusão,
conforme combinado — a prioridade era descobrir se a B1 funciona, não
fazer a B1 funcionar.

## In-sample (2021-01-01 a 2023-01-01) — mesmo período usado em V2-V6

| Métrica | V1 (méd/med) | B1 (méd/med) | B&H (méd/med) | B1>V1 | B1>B&H | V1>B&H |
|---|---|---|---|---|---|---|
| Retorno | -3.50% / -9.86% | **1.28% / -0.89%** | 3.93% / 3.08% | 8/11 | 4/11 | 4/11 |
| CAGR | -2.71% / -5.10% | 0.52% / -0.45% | 1.04% / 1.54% | 8/11 | 4/11 | 4/11 |
| Máx. drawdown | -27.33% / -25.75% | **-14.76% / -12.96%** | -43.15% / -41.34% | 10/11 | 11/11 | 11/11 |
| Sharpe | -0.19 / -0.30 | 0.05 / -0.01 | 0.17 / 0.20 | 6/11 | 4/11 | 4/11 |
| Sortino | -0.06 / -0.27 | 0.07 / -0.01 | 0.28 / 0.32 | 6/11 | 4/11 | 4/11 |
| Calmar | 0.07 / -0.17 | 0.11 / -0.03 | 0.04 / 0.05 | 6/11 | 6/11 | 4/11 |

Nº trades (mediana): V1=6, B1=7. % exposto (mediana): V1=36.6%, B1=40.6%.

Nesse período (queda de tech em 2022), a B1 supera a V1 na maioria dos
ativos em quase todas as métricas.

## Out-of-sample (2018-01-01 a 2020-01-01) — mesmo período usado em V2-V6

| Métrica | V1 (méd/med) | B1 (méd/med) | B&H (méd/med) | B1>V1 | B1>B&H | V1>B&H |
|---|---|---|---|---|---|---|
| Retorno | 17.96% / 17.45% | **6.10% / 1.14%** | 51.88% / 49.96% | 3/11 | 1/11 | 1/11 |
| CAGR | 8.10% / 8.41% | 2.90% / 0.57% | 22.64% / 22.58% | 3/11 | 1/11 | 1/11 |
| Máx. drawdown | -21.61% / -21.43% | **-12.01% / -10.92%** | -33.98% / -33.31% | 10/11 | 11/11 | 10/11 |
| Sharpe | 0.51 / 0.48 | 0.35 / 0.11 | 0.82 / 0.85 | 5/11 | 1/11 | 3/11 |
| Sortino | 0.55 / 0.50 | 0.38 / 0.12 | 1.18 / 1.37 | 5/11 | 0/11 | 2/11 |
| Calmar | 0.62 / 0.37 | 0.35 / 0.05 | 0.77 / 0.73 | 5/11 | 2/11 | 3/11 |

Nº trades (mediana): V1=4, B1=7. % exposto (mediana): V1=48.4%, B1=47.6%.

Nesse período, a vantagem observada no IS **se inverte**: a B1 fica
atrás da V1 em retorno/CAGR/Sharpe/Sortino/Calmar (médias piores, apesar
de 5/11 em Sharpe/Sortino/Calmar ser tecnicamente empate por contagem de
vitórias — a média mostra a diferença real). O drawdown continua melhor
que a V1 nos dois períodos — a única propriedade que não se inverteu.

## Walk-forward (2012-2024, 6 janelas de 2 anos, 66 combinações janela×ativo)

Agregado geral:

| Métrica | V1 (méd/med) | B1 (méd/med) | B1 > B&H |
|---|---|---|---|
| Retorno | 19.33% / 13.71% | 13.88% / 10.10% | 13/66 |
| CAGR | 8.48% / 6.66% | 6.26% / 4.96% | 13/66 |
| Máx. drawdown | -22.28% / -21.12% | **-12.16% / -10.68%** | 65/66 |
| Sharpe | 0.44 / 0.52 | 0.47 / 0.57 | 16/66 |
| Sortino | 0.54 / 0.51 | 0.59 / 0.59 | 12/66 |
| Calmar | 0.53 / 0.36 | 0.64 / 0.53 | 20/66 |

Por janela (médias; retorno em %; Sharpe/Sortino/Calmar sem unidade;
"B1 ganha de V1?" olha Sharpe médio, o resumo mais direto de risco×retorno):

| Janela | Retorno V1 / B1 | DD V1 / B1 | Sharpe V1 / B1 | B1 ganha de V1? |
|---|---|---|---|---|
| 2012-2014 | 14.33 / 7.11 | -18.43 / -11.27 | 0.45 / 0.39 | Não |
| 2014-2016 | -0.27 / 1.63 | -25.94 / -13.72 | -0.07 / 0.01 | Sim |
| 2016-2018 | 35.95 / 35.41 | -19.54 / -10.18 | 0.75 / 1.01 | Sim |
| 2018-2020 | 17.96 / 6.20 | -21.61 / -12.02 | 0.51 / 0.35 | Não |
| 2020-2022 | 35.53 / 23.02 | -22.65 / -13.43 | 0.67 / 0.72 | Sim (marginal) |
| 2022-2024 | 12.48 / 9.91 | -25.51 / -12.35 | 0.32 / 0.37 | Sim (marginal) |

B1 supera a V1 em Sharpe em 4 das 6 janelas, mas em retorno bruto a V1
supera a B1 em 4-5 das 6 janelas — a B1 abre mão de mais retorno do que
a V1 na maioria das janelas, e só "ganha" em risco-ajustado quando o
corte de drawdown compensa numericamente essa perda. Não há um padrão
claro de regime (ex: "B1 ganha em mercado de baixa, perde em alta") que
explique isso de forma limpa — 2016-2018 e 2018-2020 são as duas janelas
mais "em alta" do período e uma favorece a B1 (2016-2018) e a outra
favorece a V1 (2018-2020). Não vou forçar uma narrativa de regime que os
dados não sustentam claramente.

## Respostas às perguntas (A-I)

- **A. Bate o buy-and-hold?** Não. Em nenhum recorte (IS, OOS, walk-forward
  agregado) o retorno ou o risco-ajustado da B1 supera o B&H de forma
  consistente (4/11, 1/11, 13-20/66).
- **B. Bate a V1?** Inconsistente. Vence em retorno/Sharpe/Sortino/Calmar no
  IS (2021-2023), perde nesses mesmos itens no OOS (2018-2020). No
  walk-forward, vence em Sharpe em 4/6 janelas mas perde em retorno bruto
  em 4-5/6 janelas.
- **C. Vantagem ajustada ao risco?** Não robusta — depende do período, e o
  "ganho" de Sharpe/Sortino/Calmar quando existe vem quase todo do corte
  de drawdown, não de um retorno melhor.
- **D. Vale em IS e OOS?** Não — é o achado mais claro deste relatório: o
  que parece vantagem no IS se inverte no OOS.
- **E. Distribuído entre ativos ou concentrado em poucos?** Razoavelmente
  distribuído — vitórias de 8/11 (IS) e 3/11 (OOS), sem depender de 1-2
  ativos extremos; o corte de drawdown é quase unânime (10-11/11) nos dois
  períodos.
- **F. Distribuído entre janelas ou um período só?** Não é um período só,
  mas também não é uniforme — 4 janelas favorecem a B1 em Sharpe, 2
  favorecem a V1, sem um fator de regime identificável que explique a
  divisão.
- **G. Sobrevive a custos?** A comparação já usa os mesmos custos da V1
  (`fee_rate`/`slippage_rate` idênticos) em todos os testes — a conclusão
  acima já é líquida de custos, não é um efeito que desaparece com custos
  realistas.
- **H. Relevante economicamente ou só estatisticamente interessante?** O
  corte de drawdown é economicamente grande e real (drawdown quase metade
  do da V1 em valor absoluto), mas não é uma descoberta nova — é uma
  versão mais agressiva de uma propriedade que a V1 já tinha. Não há
  evidência de uma vantagem de retorno economicamente relevante.
  Também não é apenas "estatisticamente interessante": os números são
  grandes o bastante pra importar na prática, só que na direção errada
  (menos retorno) na maior parte das janelas.
- **I. Captura tendência real ou só algumas operações grandes?** Não há
  concentração óbvia em poucas operações — o número de trades da B1
  (7 no IS, 7 no OOS) é igual ou maior que o da V1 (6 e 4), não menor;
  não é "poucas entradas grandes bem escolhidas".

## Classificação: REJEITADA

Segundo o critério combinado (VALIDADA exige evidência forte e
consistente em OOS/walk-forward, sem depender de ativo/período/parâmetro
específico): a B1 não atende. A vantagem que aparece no IS reverte no
OOS e não há um padrão de regime limpo que explique isso — é
exatamente o tipo de dependência de período que desqualifica um
resultado positivo. A única propriedade genuinamente consistente
(redução de drawdown) não é nova: é uma versão mais agressiva do que a
V1 já demonstrava, obtida abrindo mão de mais retorno — não configura
"vantagem", é uma troca (trade-off) já conhecida.

**Resposta à pergunta final:** não há evidência robusta de alpha
ajustado ao risco que justifique continuar investindo na família B a
partir da B1 pura, tal como especificada. B1 fica registrada como
rejeitada (mantida no repositório como registro do experimento, igual
V2/V3/V5/V6), sem criar B2/B3 automaticamente. Se fizer sentido
continuar a família B, isso merece ser decidido e desenhado como uma
nova hipótese isolada — não como reação a este resultado.
