# Relatório de referência — FinServe Platform v2.0.0

Gerado por `python -m finserve report` em banco temporário · data de referência **2026-11-10** · dados de mercado coletados em **2026-11-10T20:34:11+00:00**. Arquivo-fonte: [`metrics.json`](metrics.json).

> Mercado = dados públicos **reais** do Banco Central. Campanhas, A/B e Core Web Vitals = **sintéticos** (seed fixa).

## 1. Proveniência

| Dataset | Tipo | Fonte | Linhas | Coleta |
|---|---|---|---|---|
| Componentes editoriais e revisões | synthetic | Texto institucional fictício escrito para a demonstração | 8 | — |
| Fatos diários de campanhas (8 campanhas × 120 dias) | synthetic | Gerador determinístico (seed 32593) com 3 anomalias injetadas | 960 | — |
| Experimentos A/B | synthetic | Valores fixos no seed; estatística calculada em tempo de consulta | 3 | — |
| Séries macro e crédito (SGS) | real | Banco Central do Brasil — SGS | 1.187 | 2026-11-10T20:34:11+00:00 |
| Expectativas de mercado (Focus) | real | Banco Central do Brasil — Olinda/Expectativas | 560 | 2026-11-10T20:34:11+00:00 |
| Simulações de investimento e crédito | derived | Calculadoras determinísticas sobre CDI/Selic/IPCA reais | — | 2026-11-10T20:34:11+00:00 |

## 2. Mercado (real)

| Indicador | Valor | Unidade | Referência | Variação | Tipo |
|---|---|---|---|---|---|
| Meta Selic | 13,75 | % a.a. | 2026-11-10 | -0,25 | real |
| CDI (a.a.) | 13,65 | % a.a. | 2026-11-09 | -0,25 | real |
| Dólar comercial | 5,5840 | R$ | 2026-11-10 | 11,92 | real |
| Inadimplência PF (>90d) | 5,99 | % | 2026-09-01 | -0,05 | real |
| IPCA 12 meses | 4,58 | % | 2026-09-01 | -0,06 | derived |

**Focus (mediana)**

| Indicador | Ano | Mediana | Mín. | Máx. | Respondentes | Data |
|---|---|---|---|---|---|---|
| Selic | 2026 | 13,75 | 13,25 | 14,00 | 144 | 2026-11-06 |
| Selic | 2027 | 12,50 | 10,25 | 15,00 | 144 | 2026-11-06 |
| IPCA | 2026 | 5,22 | 4,91 | 5,92 | 146 | 2026-11-06 |
| IPCA | 2027 | 4,90 | 3,25 | 6,46 | 146 | 2026-11-06 |
| Câmbio | 2026 | 5,35 | 4,90 | 6,00 | 122 | 2026-11-06 |
| Câmbio | 2027 | 5,40 | 4,70 | 6,00 | 121 | 2026-11-06 |
| PIB Total | 2026 | 1,75 | 1,00 | 2,28 | 118 | 2026-11-06 |
| PIB Total | 2027 | 1,15 | -0,22 | 2,38 | 117 | 2026-11-06 |

## 3. Simulações (insumos reais)

**Investimento** — R$ 10.000,00, 12 meses, CDI 13,65% a.a., Selic 13,75% a.a., IPCA 12m 4,58%.

| Produto | Valor líquido | Ganho líquido | % a.a. líquido | IR | Retorno real |
|---|---|---|---|---|---|
| LCI/LCA 90% do CDI | R$ 11.220,54 | R$ 1.220,54 | 12,21% | R$ 0,00 | 7,29% |
| CDB 100% do CDI | R$ 11.126,13 | R$ 1.126,13 | 11,26% | R$ 238,88 | 6,39% |
| Tesouro Selic | R$ 11.107,37 | R$ 1.107,37 | 11,07% | R$ 234,90 | 6,21% |
| Poupança | R$ 10.616,78 | R$ 616,78 | 6,17% | R$ 0,00 | 1,52% |

**Crédito** — R$ 10.000, 24 meses, 2,5% a.m., Price: 1ª parcela R$ 559,13 · total pago R$ 13.419,12 · juros R$ 3.419,09 · CET 34,49% a.a. (sem IOF/seguros).

## 4. Analytics — últimos 30 dias (sintético)

| KPI | Valor | Δ vs. 30 dias anteriores |
|---|---|---|
| Sessões | 50.398 | 14,7% |
| Leads | 4.010 | 13,2% |
| CTR (%) | 2,61 | 8,7% |
| CPL (R$) | 26,44 | 1,7% |
| ROAS | 3,83 | -0,5% |
| Receita atribuída (R$) | 406.340,76 | 14,5% |

**Core Web Vitals (p75)**

| Métrica | p75 | Status |
|---|---|---|
| Largest Contentful Paint | 2.590,00 ms | needs-improvement |
| Interaction to Next Paint | 274,00 ms | needs-improvement |
| Cumulative Layout Shift | 0,10  | needs-improvement |

## 5. Anomalias detectadas (z modificado ≥ 3,5)

| Campanha | Data | Métrica | Valor | Mediana | z | Severidade |
|---|---|---|---|---|---|---|
| Investir é Simples | 2026-11-03 | Custo por lead | 206,2325 | 23,2116 | 57,42 | critical |
| Conta Digital | 2026-11-01 | Custo por lead | 69,1407 | 25,6600 | 11,51 | critical |
| Investir é Simples | 2026-11-03 | Conversão clique→lead | 0,0132 | 0,1007 | -8,51 | critical |
| Conta Digital | 2026-11-01 | Conversão clique→lead | 0,1321 | 0,0787 | 7,47 | warning |
| Conta Digital | 2026-11-01 | Taxa de clique | 0,0187 | 0,0303 | -4,83 | warning |
| Crédito Mais | 2026-10-22 | LCP | 3.984,0000 | 2.254,0000 | 4,17 | warning |

## 6. Experimentos A/B (sintético)

| Experimento | Controle | Variante | Lift | p-valor | IC 95% (p.p.) | Veredito | Amostra necessária/variante | Suficiente? |
|---|---|---|---|---|---|---|---|---|
| Copy do CTA do hero — crédito | 4,00% | 4,80% | 20,0% | 0,0064 | 0,23 a 1,37 | winner | 39.475 | não |
| Layout do banner do cartão | 4,00% | 4,16% | 3,9% | 0,6895 | -0,61 a 0,92 | inconclusive | 39.475 | não |
| Formulário curto — investimentos | 5,00% | 5,89% | 17,7% | 0,2446 | -0,61 a 2,38 | inconclusive | 31.234 | não |

## 7. Pacing de orçamento (sintético)

| Campanha | Gasto no mês | Orçamento | Usado | Esperado | Status |
|---|---|---|---|---|---|
| Crédito Mais | R$ 1.707,50 | R$ 6.300,00 | 27,1% | 33,3% | under |
| Prime Invest | R$ 2.799,04 | R$ 8.100,00 | 34,6% | 33,3% | on_track |
| Conta Digital | R$ 5.151,03 | R$ 10.000,00 | 51,5% | 33,3% | over |
| Cartão Smart | R$ 3.828,34 | R$ 11.200,00 | 34,2% | 33,3% | on_track |
| Investir é Simples | R$ 5.587,84 | R$ 16.300,00 | 34,3% | 33,3% | on_track |
| Recomeço Financeiro | R$ 6.583,04 | R$ 27.200,00 | 24,2% | 33,3% | under |
| Pix para Negócios | R$ 6.723,13 | R$ 24.100,00 | 27,9% | 33,3% | under |
| Conquistas Planejadas | R$ 1.842,43 | R$ 6.100,00 | 30,2% | 33,3% | paused |
