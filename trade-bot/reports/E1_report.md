# E1 — Pairs Trading / Mercado Neutro (família E)

**Status: EXPERIMENTO REJEITADO.** Nenhum dos dois pares testados mostra
edge robusto depois de custos. Um par (ITUB4/BBDC4) perde dinheiro de
forma consistente nos 3 recortes testados — não é reversão de regime,
é ruim o tempo todo. O outro (XOM/CVX) é inconsistente: positivo nas
duas janelas de 2 anos testadas, negativo no período completo de 6
anos — o resultado tem magnitude pequena nos dois sentidos, compatível
com ruído em torno de zero, não com um sinal real de convergência.

## Resultados

| Par | Completo (2018-2024) | IS (2021-2023) | OOS (2018-2020) |
|---|---|---|---|
| ITUB4.SA/BBDC4.SA — Retorno | **-4.45%** | **-3.25%** | **-2.19%** |
| ITUB4.SA/BBDC4.SA — Sharpe | **-0.14** | **-0.26** | **-0.35** |
| XOM/CVX — Retorno | -1.13% | +2.50% | +0.76% |
| XOM/CVX — Sharpe | -0.05 | 0.53 | 0.21 |

Custos: turnover de 5.8x a 27.5x (giro alto pro tamanho da posição),
$58 a $275 em taxas por teste sobre $10.000 iniciais — relevante frente
aos resultados de poucos por cento.

## Leitura por par

**ITUB4.SA/BBDC4.SA — rejeitado de forma limpa.** Perde dinheiro nos 3
recortes, sem exceção, com Sharpe cada vez pior (-0.14 → -0.26 → -0.35
conforme a janela encolhe). Não há sinal de que o spread desses dois
bancos converge de forma lucrativa depois de custos — pelo contrário,
o giro alto (7-27x) sugere que o par cruza o limiar de entrada com
frequência sem que isso vire lucro.

**XOM/CVX — inconsistente, não confirmado.** Positivo nas duas janelas
de 2 anos (IS +2.50%/Sharpe 0.53, OOS +0.76%/Sharpe 0.21), mas negativo
no período completo de 6 anos (-1.13%/Sharpe -0.05) — os dois anos que
não foram testados isoladamente (2020, com o crash da Covid, e
2023-2024) claramente pesaram o suficiente pra virar o resultado
agregado negativo. Combinado com a magnitude pequena dos números nos
dois sentidos (poucos % de diferença, Sharpe perto de zero em todos os
casos), a leitura mais honesta é que isso é ruído estatístico em torno
de zero, não uma vantagem real — não há evidência forte o bastante pra
chamar de "promissor" precisando de mais teste.

## Por que a arbitragem estatística "de livro-texto" não funcionou aqui

Este é o desenho mais simples possível de pairs trading: par escolhido
por lógica de setor (não por correlação/cointegração testada
estatisticamente), hedge ratio fixo de 1:1 (não ajustado por regressão
móvel), limiares de z-score fixos (2.0/0.5/4.0). Versões mais
sofisticadas da literatura (seleção de pares por teste de cointegração
formal, hedge ratio dinâmico via regressão, universo maior de pares
com triagem estatística) poderiam ter resultado diferente — mas isso é
trabalho futuro, não algo a implementar sem confirmação, seguindo a
mesma disciplina do resto do projeto.

## Classificação: REJEITADA

Nenhum par mostrou edge consistente e robusto depois de custos. A
família E fica registrada como mais um experimento negativo, no mesmo
padrão de rigor das demais.
