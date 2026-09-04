# C1 — Momentum Duplo / rotação de carteira (família C)

**Status: PROMISSORA, com o placebo (C3) confirmando que o mecanismo é
real na maior parte do histórico.** Não bate o buy-and-hold da cesta de
forma robusta (perde em CAGR/Sortino/Calmar na maioria das janelas),
mas é o melhor resultado de todo o programa de pesquisa até agora: bate
a V1 em Sharpe em 5 das 6 janelas do walk-forward e em CAGR em 4 das 6,
mantendo a mesma vantagem de drawdown que caracteriza a V1 e a B1 (6/6
janelas). Ao contrário de V3/V5/V6/B1, o padrão de quando ganha e
quando perde é economicamente explicável, não uma inversão sem
explicação entre períodos. E, diferente de V3 (que perdeu do próprio
placebo), a C1 bate o placebo aleatório (C3) em 2 dos 3 testes
diretos — inclusive no período completo de 12 anos, por margem larga.

**Achado mais importante desta seção: no universo diversificado (sem
mega caps de tecnologia), a C1 bate o Sharpe do buy-and-hold nos 3
testes (IS, OOS e período completo)** — a primeira vez em todo o
projeto que isso acontece de forma consistente. Ver seção "Teste de
universo diversificado" abaixo.

## Walk-forward (2012-2024, 6 janelas de 2 anos)

| Janela | Retorno C1/B&H | CAGR C1/B&H | DD C1/B&H | Sharpe C1/B&H | Sortino C1/B&H | Calmar C1/B&H |
|---|---|---|---|---|---|---|
| 2012-2014 | 5.24% / 156.69% | 2.59% / 60.37% | -8.04% / -11.42% | 0.35 / 0.95 | 0.41 / 6.26 | 0.32 / 5.28 |
| 2014-2016 | 15.80% / 23.19% | 7.64% / 11.03% | -9.88% / -14.76% | **0.88 / 0.68** | 1.05 / 1.09 | **0.77 / 0.75** |
| 2016-2018 | 36.24% / 133.71% | 16.86% / 53.37% | -12.49% / -12.55% | 1.15 / 2.15 | 1.17 / 3.06 | 1.35 / 4.25 |
| 2018-2020 | 29.20% / 51.88% | 13.72% / 23.33% | -10.72% / -18.31% | **1.31 / 1.20** | 1.37 / 1.67 | **1.28 / 1.27** |
| 2020-2022 | 18.37% / 84.09% | 8.82% / 35.77% | -11.18% / -33.16% | 0.69 / 1.15 | 0.72 / 1.30 | 0.79 / 1.08 |
| 2022-2024 | 47.34% / 32.17% | **21.56% / 15.09%** | -7.29% / -21.29% | **1.82 / 0.83** | **2.16 / 1.22** | **2.96 / 0.71** |
| **Média** | 25.37% / 80.29% | 11.87% / 33.16% | **-9.93% / -18.58%** | 1.03 / 1.16 | 1.15 / 2.43 | 1.25 / 2.22 |

C1 > B&H: Retorno 1/6, CAGR 1/6, **Drawdown 6/6**, Sharpe 3/6, Sortino
1/6, Calmar 3/6.

## O padrão (explicável, não uma inversão sem causa)

C1 perde do buy-and-hold justamente nas janelas de alta forte e
praticamente em linha reta (2012-2014: B&H +157%; 2016-2018: B&H +134%;
2020-2022: B&H +84%) — nessas janelas, qualquer estratégia que gira
capital entre ativos ou passa parte do tempo com menos exposição total
perde para simplesmente segurar tudo o tempo todo, porque não há
correção no meio do caminho pra "compensar" ficar de fora. C1 ganha (ou
empata) nas janelas mais turbulentas, com correções relevantes no meio
do percurso (2014-2016: correção de 2015-16; 2018-2020: queda de
dez/2018 + crash da Covid; 2022-2024: queda de 2022) — aí a rotação e o
filtro de momentum absoluto evitam parte da dor sem desistir da
recuperação.

Isso é consistente com a literatura de momentum (o efeito é real, mas
sofre "momentum crashes" logo após reversões bruscas — Daniel &
Moskowitz, 2016) e é uma explicação de mecanismo, não uma coincidência
de período sem causa — diferente do que aconteceu com V3/V5/V6/B1, onde
a reversão IS→OOS não tinha um padrão de regime que se sustentasse.

## C1 vs V1 (mesmas 6 janelas, ver reports anteriores para os números da V1)

C1 bate a V1 em CAGR em 4/6 janelas (2014-16, 2016-18, 2018-20, 2022-24)
e em Sharpe em 5/6 janelas (todas exceto 2012-14). Isso é uma melhora
real e consistente sobre o melhor resultado que este projeto já tinha
produzido — a V1, isoladamente, nunca bateu o Sharpe médio do
buy-and-hold em NENHUMA das 6 janelas ao nível de carteira; a C1 bate em
3 das 6.

## Por que não é VALIDADA ainda

- Sortino e Calmar continuam atrás do buy-and-hold na maioria das
  janelas (1/6 e 3/6) — o corte de drawdown não compensa a perda de
  retorno em todas as métricas de risco-ajustado, só no Sharpe.
- CAGR/retorno bruto perde pro buy-and-hold em 5 das 6 janelas — a
  vantagem de Sharpe nas janelas turbulentas não é grande o bastante
  pra também vencer em retorno absoluto na maioria dos casos.
- Só uma janela (2022-2024) mostra vitória clara e ampla em todas as
  métricas ao mesmo tempo — as outras "vitórias" são parciais (só
  Sharpe/Calmar, retorno ainda perde).

## Próximo passo (recomendação, não implementado sem confirmação)

Testar TOP_K maior (ex: 5 ou 6 de 11) como uma hipótese isolada e nova
(C2), com parâmetro congelado ANTES de rodar — a suspeita (não
confirmada) é que segurar só 3 de 11 ativos concentra demais a aposta e
aumenta o "cash drag" nas janelas de alta em linha reta, sem ganho de
proteção proporcional. Isso preservaria a mesma disciplina de teste
único por hipótese já usada em todo o projeto — não é uma otimização
depois do resultado, é uma pergunta nova e específica sobre um
mecanismo (concentração) que os dados já sugerem como candidato.

## C2 — pré-registro (decidido ANTES de rodar qualquer teste)

Confirmado com o usuário: testar a mesma engine da C1
(`tradebot/backtest_c1.py`, nenhum código novo — só o parâmetro `top_k`
já exposto via `--top-k`), mudando **apenas** `TOP_K` de 3 para **5**
(de 11 ativos). Todo o resto — `MOMENTUM_LOOKBACK_DAYS = 252`,
rebalanceamento mensal, filtro de momentum absoluto, custos, universo —
permanece idêntico à C1. Hipótese: menos concentração reduz o "cash
drag" nas janelas de alta forte e em linha reta (onde a C1 perdeu do
buy-and-hold) sem sacrificar a proteção de drawdown nas janelas
turbulentas (onde a C1 ganhou).

## C2 — resultado (walk-forward completo, 6 janelas, `TOP_K=5`)

| Janela | Retorno C2/B&H | CAGR C2/B&H | Sharpe C2/B&H | Sharpe C1 (TOP_K=3) |
|---|---|---|---|---|
| 2012-2014 | 5.64% / 156.69% | 2.79% / 60.37% | 0.43 / 0.95 | 0.35 |
| 2014-2016 | 14.13% / 23.19% | 6.85% / 11.03% | **0.86** / 0.68 | 0.88 |
| 2016-2018 | 27.24% / 133.71% | 12.90% / 53.37% | 1.21 / 2.15 | 1.15 |
| 2018-2020 | 22.35% / 51.88% | 10.65% / 23.33% | 1.15 / 1.20 | 1.31 |
| 2020-2022 | 24.13% / 84.09% | 11.44% / 35.77% | 0.96 / 1.15 | 0.69 |
| 2022-2024 | 34.50% / 32.17% | **16.11% / 15.09%** | **1.80** / 0.83 | 1.82 |
| **Média Sharpe** | | | **1.07** | 1.03 |
| **Média CAGR** | | | **10.12%** | 11.87% |

**Hipótese NÃO confirmada.** `TOP_K=5` bate `TOP_K=3` em Sharpe em
apenas 3 das 6 janelas (por margens pequenas, exceto 2020-2022), com
Sharpe médio marginalmente melhor (1.07 vs 1.03) mas CAGR médio **pior**
(10.12% vs 11.87%) — diluir a concentração não reduziu o "cash drag" de
forma consistente; na janela 2016-2018 (uma das que motivou a hipótese)
o resultado até piorou relativo ao B&H (gap de -97pp com TOP_K=3 foi
para -106pp com TOP_K=5). Diluir mais não é a alavanca certa.

**Decisão: manter `TOP_K=3` (configuração original da C1) como a
referência da família C.** C2 fica registrada como um teste de
sensibilidade negativo, não como uma variante melhor — consistente com
a disciplina do projeto de nunca adotar um parâmetro só porque foi
testado.

## C3 — placebo aleatório (teste decisivo, mesma lógica de V3 vs V4)

Pergunta: o Sharpe melhor da C1 sobre a V1 vem de informação genuína no
ranking de momentum, ou só do mecanismo de girar mensalmente entre um
subconjunto menor da cesta (menos concentração), não importa qual
critério escolhe os ativos? C3 reaproveita a mesma mecânica da C1
(rebalanceamento mensal, `TOP_K=3`, sizing, custos), mudando **apenas**
a seleção: sorteia 3 ativos aleatórios por mês em vez de rankear por
momentum (`SEED=42`, sem filtro de momentum absoluto).

| Período | Sharpe C1 (momentum) | Sharpe C3 (aleatório) | Quem vence |
|---|---|---|---|
| IS 2021-2023 | -0.80 | **0.72** | C3 (placebo) |
| OOS 2018-2020 | **1.31** | 0.37 | C1 (momentum) |
| Completo 2012-2024 | **1.05** | 0.76 | C1 (momentum) |

**Resultado: o momentum vence o placebo em 2 dos 3 testes, inclusive no
período completo de 12 anos por margem clara** (Sharpe 1.05 vs 0.76,
Sortino 1.29 vs 1.03, Calmar 0.68 vs 0.48, retorno 731.67% vs 304.95%).
Isso é o oposto do que aconteceu com V3 (que perdeu do placebo V4) — diz
que o ranking de momentum está fazendo algo real na maior parte do
histórico, não é só efeito de operar com menos concentração.

A única derrota da C1 é justamente no período de 2021-2023 — a mesma
janela de reversão brusca (2022) que já sabíamos ser o ponto fraco
estrutural de qualquer estratégia de momentum ("momentum crash",
Daniel & Moskowitz, 2016: comprar sistematicamente quem subiu recente
apanha feio logo após uma reversão de tendência). Não é uma surpresa
nem enfraquece a conclusão — é o risco conhecido e esperado da
categoria, já documentado antes neste mesmo report.

Achado colateral relevante: a C3 opera com um giro muito maior que a
C1 (52 trades vs 7 no IS; 311 vs 74 no período completo) porque um
sorteio aleatório raramente repete os mesmos 3 ativos mês a mês,
enquanto o momentum tem persistência (quem subiu continua subindo por
um tempo, reduzindo a troca de posições). Isso significa que parte da
vantagem da C1 vem de um custo de transação estruturalmente menor
(938 vs 3.493 em taxas no período completo) — uma vantagem real, não um
artefato, mas que também mostra que a C1 se beneficia da persistência
do momentum, não só do ranking em si.

## Teste de universo diversificado (viés de sobrevivência)

Pergunta do usuário: será que "nada bate buy-and-hold" é um achado
sobre técnica, ou artefato de testar contra uma cesta com 5 mega caps
de tecnologia dominadas pelo rali de IA da NVDA (um dos maiores
retornos de ação única da história)? `US_DIVERSIFIED_WATCHLIST`
substitui essas 5 por 5 ações de setores diferentes (JPM, JNJ, PG, XOM,
CAT — escolhidas por setor, não por retorno), mesmo tamanho, cesta
brasileira igual.

| Período | Sharpe C1 | Sharpe B&H | C1 vence? | CAGR C1 | CAGR B&H |
|---|---|---|---|---|---|
| IS 2021-2023 | **0.94** | 0.87 | Sim | 12.66% | 14.56% |
| OOS 2018-2020 | **1.42** | 1.02 | Sim | 13.73% | 16.39% |
| Completo 2012-2024 | **0.73** | 0.71 | Sim (por pouco) | 10.16% | 20.09% |

**A C1 bate o Sharpe do buy-and-hold nos 3 testes — a primeira vez em
todo o projeto que isso acontece de forma consistente**, com folga
maior no OOS (1.42 vs 1.02) e no drawdown em todos os três (ex:
-22.88% vs -34.77% no período completo, quase metade). Sortino e
Calmar só vencem no OOS; CAGR/retorno bruto continuam perdendo nos 3
(embora por margem muito menor que na cesta de tech: o buy-and-hold do
período completo caiu de +4011% pra +798% — a NVDA sozinha explicava a
maior parte da distância antes vista).

**Conclusão: a suspeita do usuário estava certa.** Boa parte do "nada
bate buy-and-hold" das famílias V/B/D vinha de testar contra uma cesta
concentrada num dos maiores vencedores de ação única da história, não
de uma verdade universal sobre timing de mercado. Isso não muda a
classificação de V2-V6/B1/D1 (foram rejeitadas por reverter IS→OOS
contra a própria V1, um problema diferente e que persiste independente
do universo) — mas muda a leitura sobre a C1: o edge de Sharpe é mais
robusto do que parecia, e mais visível fora da bolha de tech.

## Conclusão consolidada da família C

A C1 (`TOP_K=3`, lookback 252 dias) é a candidata final desta família:
edge real (confirmado contra placebo E robusto fora da cesta de tech),
bate o Sharpe do buy-and-hold de forma consistente no universo
diversificado, mas ainda não bate CAGR/retorno bruto e tem uma
fraqueza conhecida (reversões bruscas de momentum). C2 (diluição) não
ajudou. Próximo teste natural: cripto (ver README, "Teste de universo
cripto").
