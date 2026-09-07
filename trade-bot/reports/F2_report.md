# F2 — Cash-and-Carry com Filtro de Intensidade Mínima de Funding

**Status: ACEITA.** Nasceu direto da conclusão de F1-realista (o edge do
cash-and-carry só sobrevive ao risco de base quando o funding está forte
o bastante). F2 testa se um filtro simples — só entrar quando a taxa de
funding recente está acima de um piso — resolve isso. Resultado: **sim,
resolve exatamente o problema que deveria resolver**, com uma
contrapartida honesta (deixa dinheiro na mesa em parte da janela boa).

## Resultados

| Janela | F1-realista (sem filtro) | F2 (com filtro) |
|---|---|---|
| BTCUSDT 2021-2023 (funding forte) | Sharpe 5.37, PnL +41.40%, DD -0.53% | Sharpe 4.48, PnL +25.61%, DD -0.50%, 33.9% do tempo posicionado |
| BTCUSDT 2025-2026 (funding fraco) | Sharpe 0.07, PnL +0.70%, DD **-6.18%** | Sharpe 0.00, PnL 0.00%, DD **0.00%**, 0% do tempo posicionado |
| ETHUSDT 2021-2023 (funding forte) | — (não testado) | Sharpe 3.77, PnL +30.50%, DD -0.68%, 34.6% do tempo posicionado |
| ETHUSDT 2025-2026 (funding fraco) | — (não testado) | Sharpe 0.00, PnL 0.00%, DD **0.00%**, 0% do tempo posicionado |

## F2 vs. buy-and-hold (a pergunta que realmente importa)

| Janela | Buy-and-hold | F2 | Vencedor |
|---|---|---|---|
| BTCUSDT 2021-2023 | -43.35% | +25.61% | **F2, por 69 pontos** |
| BTCUSDT 2025-2026 | -27.46% | 0.00% | **F2, por 27 pontos** |
| ETHUSDT 2021-2023 | +64.68% | +30.50% | **Buy-and-hold, por 34 pontos** |
| ETHUSDT 2025-2026 | -42.21% | 0.00% | **F2, por 42 pontos** |

F2 vence em 3 das 4 janelas, e vence por muito nas 3 — nunca é vitória
marginal. Mas o padrão por trás não é "F2 é melhor", é um **perfil de
risco diferente**: F2 é neutro em direção (a perna vendida no perpétuo
cancela de propósito o movimento de preço), então ganha disparado
quando o mercado cai ou fica de lado (buy-and-hold quebra a cara, F2
fica perto de zero ou positivo) e perde quando o mercado sobe forte
(ETH quase dobrou em 2021-2023 — um comprado puro captura isso, F2
não, por desenho). Não é incondicional: é proteção de capital em
baixa/lateralização, ao custo de abrir mão de upside em alta forte.

## Confirmação cross-asset

ETHUSDT reproduz o mesmo padrão do BTCUSDT
em ambas as janelas, com números muito próximos (34.6% vs 33.9% do
tempo posicionado na janela forte; zero entradas nos dois na janela
fraca). Não é coincidência de um ativo só — é o comportamento do
filtro funcionando como desenhado, em dois mercados diferentes.

## Leitura

**Na janela fraca, o filtro fez exatamente o que deveria: nunca entrou.**
A média móvel de 90 eventos nunca ficou acima do limiar de 0.01%/evento
no período inteiro — F2 ficou 100% em caixa, trocando um resultado quase
neutro mas arriscado (+0.70% com -6.18% de drawdown) por zero risco e
zero retorno. Pra quem está avaliando se vale a pena operar essa
estratégia numa janela específica, isso é a resposta certa: não é "ganhar
pouco arriscando muito", é "não jogar quando o jogo não compensa".

**Na janela forte, o filtro é conservador demais e deixa dinheiro na
mesa.** Só ficou posicionado 33.9% do tempo mesmo na janela "boa" —
o limiar de 0.01%/evento corta fora períodos que ainda eram
funding-positivos, só que abaixo do piso escolhido. O Sharpe caiu pouco
(5.37 → 4.48), mas o PnL caiu bastante (41.40% → 25.61%), porque parte
do tempo fora da posição era, na verdade, tempo que valia a pena estar
dentro.

## Trade-off, não veredito único

F2 não é estritamente "melhor" que F1-realista em todos os eixos — é
melhor no eixo que importava resolver (evitar o pior caso da janela
fraca) e pior no eixo de deixar retorno na mesa da janela forte. O
limiar de 0.01%/evento foi escolhido antes de rodar qualquer teste
(pré-registrado), então esse resultado não foi ajustado a dedo — mas um
limiar mais baixo provavelmente capturaria mais da janela forte sem
reabrir a porta pra janela fraca (ambas têm médias de funding
suficientemente distantes: ~0.02-0.03%/evento vs ~0.003%/evento) — isso
é uma otimização de parâmetro legítima pra próxima rodada, não algo pra
fazer agora só olhando pra esse resultado.

## Classificação: ACEITA — validada em 2 ativos

F2 resolve o problema real identificado em F1-realista: evita operar
justamente na janela onde o risco de base consumiria o retorno, e esse
comportamento se confirma em BTCUSDT e ETHUSDT, não é sorte de um único
ativo. A estratégia final recomendada da família F é F2, não F1 puro —
com a ressalva de que o limiar específico (0.01%/evento, lookback de 90
eventos) foi uma escolha razoável de primeira tentativa, não
necessariamente ótima.
