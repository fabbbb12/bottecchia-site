# F1 — Cash-and-Carry / Arbitragem de Funding Rate (família F)

**Status: ACEITA COM RESSALVA.** É o único experimento do projeto todo
com edge consistente em 6 de 6 janelas testadas — histórico completo do
perpétuo (desde set/2019) em 2 ativos (BTCUSDT e ETHUSDT). Mas o Sharpe
mostrado aqui (7 a 13) **não é o Sharpe real de uma implementação
verdadeira** — o modelo ignora risco de base e risco de liquidação da
perna vendida (ver seção final). A ressalva não é decoração: é o motivo
pelo qual isso não vira operação real neste projeto.

## Resultados — 6 janelas, 2 ativos, histórico completo do perpétuo

| Ativo | Janela | Eventos +/- | % positivo | PnL | Sharpe | Máx. DD |
|---|---|---|---|---|---|---|
| BTCUSDT | 2019-09 a 2021-09 | 1874/292 | 86.5% | +54.91% | 9.46 | -1.51% |
| BTCUSDT | 2021-09 a 2023-09 | 1882/309 | 85.9% | +16.04% | 11.13 | -0.39% |
| BTCUSDT | 2023-09 a 2025-09 | 1962/232 | 89.4% | +20.25% | 13.50 | -0.09% |
| BTCUSDT | 2025-09 a 2026-09 | 852/261 | 76.5% | +3.31% | 10.62 | -0.41% |
| ETHUSDT | 2021-01 a 2023-01 | 1772/419 | 80.9% | +46.39% | 6.94 | -1.78% |
| ETHUSDT | 2020-01 a 2022-01 | 2119/74 | 96.6% | +91.17% | 11.15 | -0.36% |

Isso cobre **toda a história do perpétuo BTCUSDT desde o lançamento**
(set/2019) em 4 janelas não sobrepostas, mais 2 janelas do ETHUSDT pra
checar se o padrão é do mercado cripto como um todo ou só do BTC.

## Leitura

**O padrão se sustenta em todas as janelas, nos dois ativos.** Funding
positivo em 76.5%-96.6% dos eventos, sem exceção, em qualquer recorte
temporal ou ativo testado — incluindo o bear market de 2022 (janela
2021-09/2023-09, ainda 85.9% positivo) e o período mais recente
(2025-09 até hoje, o mais fraco das 6, mas ainda 76.5% positivo). Isso
não é coincidência de uma janela sortuda: é a mesma assmetria estrutural
(mercado cripto historicamente mais comprado do que vendido) aparecendo
de forma consistente há mais de 6 anos, em ativos diferentes.

**Mas a intensidade está caindo com o tempo.** A taxa de funding média
por evento cai de ~0.02-0.03% (janelas mais antigas) pra 0.0031% na
janela mais recente (2025-09/2026-09) — quase 10x menor. Isso é
esperado: à medida que mais capital institucional entra nesse tipo de
arbitragem, o funding tende a comprimir (mais gente vendendo o
perpétuo pra capturar a taxa, o que empurra a taxa pra baixo). A leitura
honesta é que o edge é real, mas provavelmente **decrescente** — não dá
pra assumir que os próximos anos repetem o Sharpe de 9-13 das janelas
mais antigas.

## Por que o Sharpe mostrado aqui não é o Sharpe real

Dois riscos ficam de fora do modelo, documentados desde a criação de F1
(`tradebot/backtest_f1.py`) e reafirmados aqui porque são o motivo de
não tratar isso como "dinheiro fácil":

1. **Risco de base.** O modelo assume que a perna comprada (à vista) e
   a perna vendida (perpétuo) sempre se cancelam perfeitamente. Na
   prática o preço do perpétuo pode se descolar do preço à vista por
   períodos curtos — esse descolamento gera ganho ou perda adicional
   que este backtest não captura.
2. **Risco de liquidação.** A perna vendida no perpétuo fica numa conta
   de margem separada da perna comprada à vista. Um movimento de preço
   brusco pra cima pode forçar liquidação da perna vendida por falta de
   margem, mesmo que a perna comprada esteja ganhando dinheiro "no
   papel" ao mesmo tempo — é exatamente assim que operações de
   cash-and-carry reais quebram, mesmo sendo "neutras em direção" na
   teoria.

Nenhum dos dois é hipotético: são os dois motivos clássicos pelos quais
mesas de cash-and-carry profissionais usam alavancagem baixa, margem de
sobra e monitoramento ativo — nenhum desses controles está neste
backtest. Um Sharpe realista, depois de modelar isso, seria bem mais
baixo que 7-13 (mas provavelmente ainda positivo, dado o quão consistente
foi o sinal de funding em si).

## Risco quantificado (dado real, não suposição)

Medido em `scripts/measure_basis_risk.py` sobre BTCUSDT, janela mais
recente (2025-09 a 2026-09):

**Risco de liquidação.** Pior movimento de `mark_price` em uma única
janela de 8h: **-6.77% / +6.66%**. Sem alavancagem extra na perna
vendida (o que o backtest já assume — nocional = capital, 1:1, sem
tentar ser eficiente em capital), um movimento desse tamanho isolado
não quebra a posição. O risco real é **cumulativo**: crashes/pumps de
cripto já emendaram vários candles na mesma direção em sequência (ex:
o crash de mar/2020 caiu ~50% num único dia). Isso é a diferença entre
"seguro no backtest" e "seguro na prática" — a conta de margem da
perna vendida precisa ter colchão suficiente pra um evento de vários
dias, não só pra um candle de 8h.

**Risco de base.** Descolamento perpétuo vs. à vista: média **-0.04%**
(perto de zero, como esperado — o próprio funding existe pra puxar o
perpétuo de volta pro à vista), desvio-padrão **0.47%**, picos de até
**+3.82% / -3.71%**. É ruído que reverte, não um viés que se acumula
— mas ao marcar a posição a mercado diariamente (não só na saída), essa
volatilidade extra entraria na série de retornos e reduziria o Sharpe
mostrado, que hoje é artificialmente suave (drawdown de -0.09% a
-1.78%) por só contar o funding, ignorando essa marcação.

**Estimativa honesta:** juntando as duas fontes de risco à série de
retornos, um Sharpe realista fica na faixa de **2 a 4** — bem abaixo
dos 7-13 do backtest puro, mas ainda seria, se confirmado num modelo
mais completo, um resultado melhor que buy-and-hold com uma fração do
drawdown. Não é o número final (exigiria simular a marcação diária
completa, fora do escopo deste teste), mas é a correção de ordem de
grandeza mais honesta que dá pra fazer com o dado que já temos.

## Classificação: ACEITA COM RESSALVA

Diferente de V1-E1 (todos rejeitados ou triviais), F1 é o primeiro
experimento do projeto com evidência forte e consistente de edge real —
mas o edge é de um tipo diferente (carry estrutural do mercado de
derivativos, não previsão de preço) e o resultado numérico mostrado
superestima o que seria alcançável numa implementação real, por ignorar
risco de base e de liquidação. Fica registrado como aceito pro mecanismo
em si (a taxa de financiamento histórica é, de fato, positiva o
suficiente e consistente o suficiente pra compensar custos de entrada),
não pro número de Sharpe específico mostrado aqui.
