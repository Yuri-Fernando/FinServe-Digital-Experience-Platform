# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Datas no fuso de Brasília.

## [2.0.0] — 2026-11-11

Reescrita modular. A v1 (aplicação única FastAPI + HTML/JS) foi preservada integralmente em arquivo local fora do repositório.

### Adicionado
- **Núcleo modular**: registry de módulos (`Module`), `create_app()` com subconjunto de módulos, descoberta automática, módulos externos por `FINSERVE_EXTRA_MODULES`/entry point, detecção de dependência ausente e de ciclo.
- **CLI** `finserve`: `serve`, `modules`, `seed`, `market-sync`, `market-snapshot`, `check`, `dictionary`, `new-module` (gera esqueleto + teste, nunca sobrescreve).
- **Módulo `market` (dados reais)**: 7 séries do BCB/SGS + expectativas Focus, snapshots versionados para uso offline, sincronização ao vivo, descarte de pontos futuros, IPCA 12 meses derivado, tokens formatados.
- **Simuladores**: investimento (CDB, LCI/LCA, Tesouro Selic, poupança; IR regressivo; retorno real) e crédito (Price/SAC, CET por TIR) com premissas explícitas.
- **Módulo `analytics`**: variação vs. período anterior (só com janela completa), Core Web Vitals p75 com limiares do web.dev, detecção de anomalias (z modificado) com gabarito injetado, pacing de orçamento, testes A/B (teste z, IC 95%, tamanho de amostra), exportação CSV no servidor.
- **Módulo `experience`**: compliance editorial em YAML (7 regras, fail-safe), tokens de mercado em conteúdo, diff entre versões, entrega headless com `ETag`/`Cache-Control`/304 e `.model.json` no estilo Sling Model Exporter.
- **Módulo `platform`**: proveniência de dados (real × sintético × derivado), dicionário, auditoria unificada, catálogo de specs de dashboard.
- **dashkit**: renderizador declarativo (KPI, linha, barras, donut, funil, vitals, tabela ordenável, lista, calculadoras) + validador de specs.
- **Relatório de referência** (`finserve report`): `reports/metrics.json` e `reports/report.md` gerados em banco temporário, fonte dos números do README.
- E2E de navegador opcional (`scripts/e2e_browser.py`, Playwright) com 17 verificações; capturas organizadas em `docs/images/`.
- 114 testes automatizados; CI (Python 3.10/3.12 em Linux e Windows + checagem de sintaxe do front); documentação (ADRs 0001–0007, Data Card, DASHKIT, MODULES, ROADMAP).

### Alterado
- Estrutura da raiz: `src/finserve/`, `web/`, `tests/`, `docs/`, `data/snapshots/`, `aem-reference/`. Material pessoal e de vaga movido para `_private/` (ignorado pelo git).
- Auditoria passou a ser genérica (`module/entity/entity_id`).
- Orçamento de campanha passou a ser **mensal** e calibrado ao gasto observado (antes não tinha relação com o gasto).

### Corrigido
- A série SGS 21082 estava descrita como inadimplência de pessoas físicas; é a do **total** da carteira (PF = 21084).
- Observações da meta Selic datadas no futuro não são mais tratadas como realizadas.

### Removido
- Adaptador `scripts/import_bcb_selic.py` e rota `/api/market/selic` da v1 (substituídos pelo módulo `market`); rotas `/api/*` passaram a viver sob `/api/<módulo>/`.
- `PORTFOLIO_PITCH.md` e `CAREER_FIT.md` saíram do repositório (material pessoal, agora em `_private/`).

## [1.0.0] — 2026-11-10
Primeira versão: dashboard sintético, Content Studio com workflow, portal e API REST em um único módulo FastAPI; 7 testes; código de referência AEM (não executado).
