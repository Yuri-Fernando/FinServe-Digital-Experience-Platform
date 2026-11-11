# ADR 0003 — Dados reais do Banco Central com snapshot versionado e proveniência

**Status:** aceito · **Contexto:** a v1 só tinha dados sintéticos e um adaptador opcional que nunca rodava. Um dashboard financeiro com dados reais convence mais — desde que o real nunca se confunda com o sintético.

**Decisão:**
1. Catálogo fixo de séries SGS **verificadas contra a API** (Selic 432, CDI 4389, IPCA 433, IGP-M 189, dólar 1, inadimplência total 21082 e PF 21084) e Focus (Selic, IPCA, câmbio, PIB).
2. `finserve market-snapshot` grava `data/snapshots/*.json` com `retrieved_at`; o seed carrega o snapshot, então o app funciona **offline**.
3. `finserve market-sync` e `POST /api/market/sync` atualizam ao vivo.
4. Cada dataset declara `kind`, fonte, URL e data em `/api/platform/provenance`.

**Achados que moldaram a decisão:**
- A série 21082 é inadimplência do **total** da carteira, não de pessoas físicas — o catálogo tem 21082 *e* 21084 com rótulos distintos.
- A meta Selic (432) devolveu pontos **datados no futuro** em 2026-11-10; o parser descarta qualquer observação posterior à data de referência (teste `test_parse_sgs_drops_future_points_and_sorts`).
- Séries de juros de crédito cujo código e descrição não puderam ser confirmados **não** entram no catálogo.

**Consequências:** (+) rastreabilidade e execução offline; (+) a falha de uma série não derruba as demais (`test_sync_isolates_per_series_failure_and_logs`); (+) snapshot incompleto nunca é gravado. (−) o snapshot envelhece: a UI mostra a data de coleta e a flag `stale`.

**Não integrado:** estatísticas Pix (Olinda `Pix_DadosAbertos`) — a consulta expirou (timeout) na verificação de 2026-11-10; fica no roadmap.
