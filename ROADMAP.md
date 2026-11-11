# Roadmap — FinServe Platform

Planejamento por versões. Cada fase tem **entregáveis** e **critério de aceite verificável**; nada é marcado como concluído sem evidência (teste, relatório ou execução registrada). Estado atual: **v2.0.0 — MVP técnico funcional** (ver [`CHANGELOG.md`](CHANGELOG.md)).

Legenda: ✅ concluída · 🟡 parcial · ⏳ planejada · 🔒 depende de terceiros (licença, acesso, dados).

---

## ✅ v2.0 — Plataforma modular (concluída em 2026-11-11)

| Entrega | Evidência |
|---|---|
| Registry de módulos, CLI, scaffold `new-module` | `tests/test_platform.py` |
| Dados reais do BCB (7 séries SGS + Focus) com snapshot e proveniência | `tests/test_bcb.py`, `data/snapshots/`, `reports/report.md` §1–2 |
| Simuladores de investimento e crédito | `tests/test_calculators.py`, `reports/report.md` §3 |
| Analytics: deltas, CWV p75, anomalias com gabarito, pacing, A/B | `tests/test_analytics.py`, `reports/report.md` §4–7 |
| Content Studio com compliance YAML, diff e entrega headless | `tests/test_experience.py` |
| dashkit + front validado em navegador | `scripts/e2e_browser.py` (17/17, manual) |

---

## ⏳ v2.1 — Qualidade contínua e publicação

**Objetivo:** tudo o que hoje é verificado manualmente passa a rodar sozinho.

- CI do GitHub Actions executando em Ubuntu e Windows, Python 3.10 e 3.12 (workflow já escrito).
- Cobertura com `pytest-cov` publicada no CI; meta inicial ≥ 85% em `src/finserve`.
- Lint e formatação (`ruff`) + `pre-commit`.
- E2E de navegador (`scripts/e2e_browser.py`) em modo headless no CI, com banco temporário.
- `Dockerfile` mínimo (Python slim, usuário não-root, bind configurável) e `docker compose up`.
- Verificar `pip install -e .` e o comando `finserve` em ambiente limpo.

**Aceite:** badge de CI verde nos dois sistemas; relatório de cobertura anexado ao run; E2E passando no CI; imagem Docker sobe e responde em `/api/platform/health`.

---

## ⏳ v2.2 — Dados públicos ampliados

**Objetivo:** mais dado real, sempre verificado antes de rotular.

- **Pix Open Data** (Olinda `Pix_DadosAbertos`): volume e valor de transações por mês, com paginação, timeout generoso e cache; painel “Pix no Brasil”. Hoje a consulta expirou — reconfirmar endpoint e parâmetros.
- **Taxas médias de crédito** (pessoa física: pessoal não consignado, consignado, cartão rotativo): só entram após confirmar código **e descrição** pelos metadados oficiais do SGS. Permitirá comparar a taxa simulada com a média de mercado.
- **Histórico do Focus**: evolução semanal das medianas (Selic e IPCA do ano corrente) em gráfico.
- **Atualização agendada**: workflow semanal que roda `finserve market-snapshot` e abre PR com o diff dos snapshots (revisão humana antes de entrar).
- Alerta visual de dado defasado por série (já existe a flag `stale`; falta destacar na UI).

**Aceite:** cada série nova com teste de parsing e rótulo conferido; PR automático de snapshot gerado pelo menos uma vez; `/api/platform/provenance` listando as novas fontes.

---

## ⏳ v2.3 — Experiência e conteúdo

**Objetivo:** aproximar o Content Studio de uma operação editorial real.

- Agendamento de publicação e expiração (`publish_at`, `expire_at`) com job idempotente.
- **A/B de conteúdo integrado ao analytics**: uma variante editorial vira um experimento com o mesmo teste estatístico já existente.
- Prévia por persona e por dispositivo dentro do Studio.
- Regras de compliance por produto (crédito, investimento, cartão) e **fluxo de exceção** aprovado por revisor, registrado na auditoria.
- Acessibilidade automatizada (axe-core no E2E) e contraste verificado.
- Internacionalização pt-BR/en do front.

**Aceite:** testes para agendamento e exceção de compliance; experimento editorial aparecendo no painel de A/B; zero violações graves no axe nas páginas principais.

---

## ⏳ v2.4 — Analytics mais robusto

- Detector de anomalias com sazonalidade semanal (mediana por dia da semana ou decomposição STL) para reduzir alertas em fins de semana.
- **Poder estatístico explícito**: o relatório já mostra que o experimento “vencedor” tem ~9,8 mil visitantes/variante contra ~39,5 mil planejados para MDE de 10% — adicionar alerta de *underpowered* e testes sequenciais (ou correção para múltiplas comparações).
- Coortes de leads e funil por canal ao longo do tempo.
- Atribuição multi-toque **ilustrativa**, claramente rotulada como sintética.

**Aceite:** gabarito de anomalias continua 100% detectado com menos falsos positivos; experimentos *underpowered* sinalizados na UI e no relatório.

---

## ⏳ v3.0 — Plataforma de verdade

**Objetivo:** sair do modo laboratório.

- Autenticação OIDC e RBAC real no lugar do `X-Demo-Role`; trilha de auditoria ligada à identidade.
- PostgreSQL com migrações (Alembic); SQLite fica como modo local.
- Padrão *outbox* para eventos de publicação (invalidação de cache, webhooks).
- Observabilidade: OpenTelemetry (traces das rotas e do sync do BCB), logs estruturados.
- Rate limiting, CORS por origem, cabeçalhos de segurança.

**Aceite:** testes de autorização negativos (usuário sem papel não publica por API); suíte rodando contra PostgreSQL no CI; trace de uma publicação ponta a ponta.

---

## ⏳ v3.1 — Módulos de risco reaproveitando o portfólio

- **Módulo `risk`** como módulo externo (`FINSERVE_EXTRA_MODULES`), consumindo artefatos do projeto Risco de Crédito (scorecard/PD) — sem copiar código.
- **Decisão antifraude** consultiva via API do Pix-Fraud-Decisioning-Lab, exibida em um painel de casos.
- Dashboards de ambos declarados como specs do dashkit (nenhum JS novo).

**Aceite:** os dois módulos carregam e descarregam sem alterar o núcleo; specs validadas por `finserve check`.

---

## 🔒 v4.0 — Integração Adobe AEM

Depende de acesso licenciado ao AEM as a Cloud Service SDK. Critérios detalhados em [`docs/ROADMAP_AEM.md`](docs/ROADMAP_AEM.md):

- M1 — projeto Maven pelo AEM Project Archetype compilando (`mvn clean verify`).
- M2 — Content Fragment Model de campanha + persisted query GraphQL + componente HTL.
- M3 — workflow de aprovação e ACL no Author.
- M4 — Dispatcher com cache e invalidação testados; Web Vitals medidos de verdade.
- M5 — pipeline no Cloud Manager.

**Aceite:** evidência de execução em SDK (logs, prints, testes AEM Mocks). Sem isso, nada nesta fase é marcado como feito.

---

## Fora do escopo (decisão consciente)

- Operar dinheiro, contas ou crédito reais; coletar dados pessoais.
- Usar LLM como decisor de compliance (no máximo consultivo, como no Pix-Fraud-Decisioning-Lab).
- Afirmar experiência de produção em AEM sem a v4 concluída.
