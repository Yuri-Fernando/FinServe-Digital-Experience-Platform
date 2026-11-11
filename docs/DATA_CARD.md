# Data Card — FinServe Platform

Documenta **o que é real, o que é sintético e como cada dado foi obtido**. Fonte única de verdade em tempo de execução: `GET /api/platform/provenance`.

## 1. Dados reais (módulo `market`)

| Série | Código | Unidade | Freq. | Observações no snapshot |
|---|---|---|---|---|
| Meta Selic | SGS 432 | % a.a. | diária | 401 |
| CDI anualizado (base 252) | SGS 4389 | % a.a. | diária (úteis) | 274 |
| IPCA — variação mensal | SGS 433 | % a.m. | mensal | 59 |
| IGP-M — variação mensal | SGS 189 | % a.m. | mensal | 60 |
| Dólar comercial (venda) | SGS 1 | R$/US$ | diária (úteis) | 275 |
| Inadimplência da carteira — **total** | SGS 21082 | % | mensal | 59 |
| Inadimplência da carteira — **pessoas físicas** | SGS 21084 | % | mensal | 59 |
| Expectativas Focus (Selic, IPCA, Câmbio, PIB Total) | Olinda `ExpectativasMercadoAnuais` | var. | semanal | 560 linhas |

- **Origem:** API de dados abertos do Banco Central do Brasil. **Coleta do snapshot:** 2026-11-10T20:34:11Z (`data/snapshots/bcb_sgs.json`, `bcb_focus.json`).
- **Verificação:** os códigos acima foram consultados na API antes de entrarem no catálogo. A série 21082 é a inadimplência do **total** da carteira (crédito livre + direcionado); a de pessoas físicas é a 21084 — são rotuladas separadamente. Séries de taxas médias de juros de crédito cujo código/descrição não pôde ser confirmado **não foram incluídas**.
- **Pontos futuros:** a meta Selic devolveu observações datadas após a data de coleta; elas são **descartadas** pelo parser.
- **IPCA 12 meses** é *derivado*: composição de 12 variações mensais consecutivas; se faltar um mês, o valor não é calculado.
- **Focus:** mediana das expectativas do mercado, filtro `baseCalculo = 0`, janela de 45 dias, anos de referência corrente e seguinte na UI. Não é projeção do Banco Central.
- **Licença/uso:** dados públicos do BCB; o Focus/Olinda segue a licença ODbL declarada no portal de dados abertos. Atribuição mantida em cada widget.
- **Defasagem:** o snapshot envelhece; a UI exibe a data de coleta e marca `stale` (diárias > 7 dias, mensais > 75). Atualize com `python -m finserve market-sync`.
- **Não integrado:** estatísticas Pix (Olinda `Pix_DadosAbertos`) — a consulta de teste expirou em 2026-11-10.

## 2. Dados sintéticos

### 2.1 Campanhas (módulo `analytics`)
- 8 campanhas × 120 dias = **960 linhas** de fatos diários; gerador determinístico (`random.Random(32593)`), data final = `FINSERVE_TODAY` ou hoje.
- Estrutura: sazonalidade senoidal, tendência leve de alta, fator dia útil/fim de semana (1,12/0,82), ruído uniforme. Restrições no banco: `approvals ≤ leads ≤ clicks ≤ impressions`, `UNIQUE(data, campanha)`.
- **Receita atribuída, custo, Core Web Vitals e orçamentos são ilustrativos.** Não representam nenhuma empresa.
- Orçamento mensal por campanha = gasto dos últimos 30 dias × fator fixo (0,80–1,25), para produzir histórias distintas de pacing.

### 2.2 Anomalias injetadas (gabarito do detector)
O gabarito vive só em `analytics/seed.py` — **nunca no banco** —, e o teste `test_detector_finds_every_injected_anomaly` exige que o detector as encontre.

| Campanha | Dia (0 = mais antigo, 119 = hoje) | Efeito |
|---|---|---|
| 3 · Conta Digital | 110 | gasto ×3,2 e cliques ×0,6 (pico de custo) |
| 1 · Crédito Mais | 100 | LCP ×1,9 (regressão de performance) |
| 5 · Investir é Simples | 112 | leads ×0,15 (quebra de tracking) |

### 2.3 Experimentos A/B
Três experimentos com contagens fixas no seed: vencedor (4,00% × 4,80%, p ≈ 0,006), inconclusivo (4,00% × 4,16%) e inconclusivo com amostra insuficiente (5,00% × 5,89%). A estatística é calculada na consulta.

### 2.4 Conteúdo editorial
8 componentes de texto institucional fictício. O `ratecard-mercado` usa tokens `{{selic_meta}}`, `{{cdi_anual}}`, `{{ipca_12m}}` resolvidos com os dados reais acima na entrega.

## 3. Uso e limites
- Educacional/portfólio. Nada aqui é recomendação de investimento, proposta de crédito ou parecer jurídico.
- Nenhum dado pessoal; conteúdo público com CPF/e-mail/telefone é bloqueado pelo motor de compliance.
- Resultados de simulação dependem das premissas listadas em cada resposta (`assumptions`).
