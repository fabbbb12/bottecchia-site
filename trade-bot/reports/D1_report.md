# D1 — Reversão à Média Pura por Faixa (família D)

**Status: EXPERIMENTO REJEITADO.** Mesmo padrão de V3/V5/V6: melhora
forte no IS (2021-2023), reverte no OOS (2018-2020) — a quarta vez que
esse padrão específico aparece no projeto, agora com um mecanismo
totalmente diferente (banda de Bollinger, não Fibonacci nem Volume),
o que reforça o achado consolidado em vez de ser um caso isolado.

## In-sample (2021-01-01 a 2023-01-01)

| Métrica | V1 (méd/med) | D1 (méd/med) | B&H (méd/med) | D1>V1 | D1>B&H |
|---|---|---|---|---|---|
| Retorno | -3.50% / -9.86% | **0.48% / 2.21%** | 3.93% / 3.08% | 7/11 | 5/11 |
| Máx. drawdown | -27.33% / -25.75% | **-17.16% / -15.83%** | -43.15% / -41.34% | 9/11 | 11/11 |
| Sharpe | -0.19 / -0.30 | 0.06 / 0.15 | 0.17 / 0.20 | 7/11 | 5/11 |
| Calmar | 0.07 / -0.17 | 0.09 / 0.05 | 0.04 / 0.05 | 7/11 | 6/11 |

Nº trades (mediana): V1=6, D1=9.

## Out-of-sample (2018-01-01 a 2020-01-01)

| Métrica | V1 (méd/med) | D1 (méd/med) | B&H (méd/med) | D1>V1 | D1>B&H |
|---|---|---|---|---|---|
| Retorno | 17.96% / 17.45% | **9.40% / 9.42%** | 51.88% / 49.96% | 3/11 | 0/11 |
| Máx. drawdown | -21.61% / -21.43% | **-11.33% / -10.00%** | -33.98% / -33.31% | 10/11 | 11/11 |
| Sharpe | 0.51 / 0.48 | 0.49 / 0.46 | 0.82 / 0.85 | 4/11 | 2/11 |
| Calmar | 0.62 / 0.37 | 0.57 / 0.41 | 0.77 / 0.73 | 6/11 | 3/11 |

Nº trades (mediana): V1=4, D1=7.

A vantagem do IS se inverte: D1 perde de V1 em retorno (3/11) e Sharpe
(4/11), com médias piores (9.40% vs 17.96% retorno; 0.49 vs 0.51
Sharpe).

## Walk-forward (2012-2024, 6 janelas)

Agregado geral (66 combinações janela×ativo):

| Métrica | V1 | D1 | B1 (referência) |
|---|---|---|---|
| Sharpe (méd) | 0.44 (18/66) | 0.47 (**21/66**) | 0.47 (16/66) |
| Sortino (méd) | 0.54 (13/66) | 0.47 (11/66) | 0.59 (12/66) |
| Calmar (méd) | 0.53 (21/66) | 0.63 (**23/66**) | 0.64 (20/66) |
| Máx. drawdown | 53/66 | **66/66** | 65/66 |

Curiosamente, no agregado completo a D1 tem o **melhor recorde de
drawdown do projeto até agora** (66/66 — nunca perdeu do buy-and-hold em
drawdown, em nenhuma das 66 combinações) e edge marginal sobre a V1 em
Sharpe/Calmar médios. Mas isso não se traduz em consistência
janela-a-janela: D1 bate a V1 em Sharpe em apenas 3 das 6 janelas
(2012-14, 2014-16, 2016-18), perde nas outras 3 (2018-20, 2020-22,
2022-24) — sem um padrão de regime limpo que separe as duas metades
(2016-18 e 2020-22 são as duas janelas de alta mais forte do
walk-forward, e D1 ganha numa e perde feio na outra).

## Por que REJEITADA, não PROMISSORA

O critério decisivo não é o agregado de 66 combinações (que pode
mascarar reversão de período) — é o teste direto IS/OOS, e ali o
padrão é claro e replica exatamente o que já reprovou V3/V5/V6: melhora
visível no mercado de vaivém (IS), reverte na tendência sustentada
(OOS). Isso não é coincidência de uma família específica de filtro —
já são 4 mecanismos diferentes (Fibonacci, Volume Relativo, Fibonacci
como sizing, e agora Bollinger) mostrando o mesmo comportamento. O
achado consolidado do projeto ganha mais uma confirmação: sistemas de
reversão à média — seja qual for o indicador usado pra defini-la —
carregam viés de seleção dependente de regime nesse universo/período.

A única propriedade nova e genuinamente boa da D1 é o recorde de
drawdown (66/66), o melhor do projeto — mas essa é a mesma categoria de
achado (redução de drawdown sem edge de retorno) que já caracteriza
V1/B1, não uma descoberta que justifique validar a estratégia.

## Classificação: REJEITADA
