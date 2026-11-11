# ADR 0006 — Entrega headless local, sem simular AEM

**Status:** aceito

**Decisão:** a camada Publish local (`/api/experience/delivery` e `/api/experience/model/{segmento}.model.json`) entrega somente conteúdo `PUBLISHED`, resolve tokens de mercado, envia `ETag` e `Cache-Control: public, max-age=60, stale-while-revalidate=300`, e responde 304 a `If-None-Match`. O `.model.json` imita a *forma* do Sling Model Exporter (`:type`, `:items`, `:itemsOrder`) e declara na própria resposta que **não** é gerado por AEM.

**Por quê:** demonstrar o raciocínio de cache/edge e o contrato headless sem fingir uma instância AEM. A documentação da Adobe recomenda persisted queries via GET para permitir cache no edge e a invalidação após publicação exige configuração própria (a pesquisa não encontrou orientação oficial única) — por isso o TTL é curto e o ETag, explícito.

**Limite:** o mapeamento real (Content Fragments, persisted queries, Dispatcher) está em `docs/ROADMAP_AEM.md` e **não foi validado** em SDK.
