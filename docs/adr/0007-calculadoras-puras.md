# ADR 0007 — Calculadoras financeiras puras com premissas explícitas

**Status:** aceito

**Decisão:** simuladores de investimento (CDB, LCI/LCA, Tesouro Selic, poupança) e de crédito (Price/SAC, CET por TIR) são funções puras em `market/calculators.py`. Toda resposta traz `assumptions` e os insumos de mercado usados (`market_inputs`, marcados como `real` ou `overridden`).

**Premissas assumidas e testadas:**
- 21 dias úteis por mês, base 252.
- IR regressivo 22,5/20/17,5/15% (até 180/360/720 dias e acima); 12 meses ≈ 365 dias.
- IOF ignorado (horizonte ≥ 1 mês).
- Poupança: 0,5% a.m. + TR se Selic > 8,5% a.a., senão 70% da Selic + TR (TR informada; padrão 0).
- Retorno real usa o IPCA de 12 meses como inflação futura.
- CET sem IOF/seguros. A Selic é exibida como contexto de custo de captação, **não** como taxa média de crédito ao consumidor.

**Validação:** valores conferidos à mão nos testes — PMT de R$ 10.000 em 12 meses a 2% = R$ 945,60; primeira parcela SAC; CET igual à taxa quando não há tarifa; bruto do CDB a 100% do CDI em 252 dias úteis ≈ CDI a.a.

**Limite:** resultado educacional — não é recomendação de investimento nem proposta de crédito.
