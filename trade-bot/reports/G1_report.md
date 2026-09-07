# G1 — Swing Trade via IBS + Filtro de Tendência

**Status: EXPERIMENTO REJEITADO.** Testado em SPY, 10 anos completos:
CAGR -1.48% (contra +15.25% do buy-and-hold), Sharpe -0.16, profit
factor 0.86 (perde mais nos trades ruins do que ganha nos bons), 202
trades. Rejeição limpa — não precisa de IS/OOS pra confirmar, o
resultado já é negativo no teste completo.

## Resultado

| Métrica | G1 | Buy&Hold |
|---|---|---|
| CAGR % | -1.48 | 15.25 |
| Máx. drawdown % | -24.44 | -33.72 |
| Sharpe | -0.16 | 0.88 |
| Sortino | -0.12 | 1.06 |
| Calmar | -0.06 | 0.45 |

## Leitura

O único ponto a favor de G1 é o drawdown menor que o buy-and-hold
(-24.44% vs -33.72%) — mas isso não compensa retorno negativo. Com 202
trades em 10 anos, a estratégia teve atividade suficiente pra um teste
estatisticamente informativo (não é caso de poucos trades e ruído) —
o profit factor abaixo de 1 mostra que a taxa de acerto ou o tamanho
médio do ganho não compensam as perdas, mesmo com o filtro de
tendência (só operar a favor da SMA200) que deveria, em teoria,
eliminar boa parte do risco de comprar quedas que continuam caindo.

Possíveis explicações (não testadas, ficam como hipótese pra quem
quiser continuar): o limiar de saída (IBS > 0.8) pode estar saindo
cedo demais, perdendo parte do movimento de reversão; ou o efeito
documentado na literatura (Connors/Alvarez, anos 1990-2008) já foi
arbitrado nesse período mais recente em um ETF tão líquido quanto o
SPY — consistente com a ressalva que a própria pesquisa já levantou
("candidata forte a ter sido arbitrada away em ações líquidas").

## Classificação: REJEITADA
