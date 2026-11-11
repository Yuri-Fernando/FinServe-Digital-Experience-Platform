# ADR 0004 — Compliance editorial em YAML com fail-safe

**Status:** aceito · **Origem:** padrão do repositório Pix-Fraud-Decisioning-Lab (do mesmo autor) — regras determinísticas, versionadas, com *reason code* e fail-safe: erro do motor nunca aprova em silêncio.

**Decisão:** `compliance_rules.yaml` define regras `forbidden` (padrões proibidos) e `requires` (gatilho sem ressalva). Texto e padrões são comparados sem acento e sem diferença de caixa. Severidade `block` impede *Enviar revisão* e *Publicar* (HTTP 422); `warn` é registrada na auditoria. Qualquer exceção do motor vira um bloqueio `ENGINE_ERROR`. Definições inválidas falham no carregamento (id duplicado, regex inválida, tipo desconhecido).

**Consequências:** (+) o editor vê motivo e sugestão ao digitar; (+) regras mudam sem tocar em código; (+) 7 regras com teste positivo e de supressão. (−) são **heurísticas educacionais**, não parecer jurídico — dito no YAML e na UI; regex gera falsos positivos e negativos que a revisão humana precisa cobrir.

**Alternativas descartadas:** LLM como decisor (não determinístico, não auditável); lista fixa em código (exige deploy para mudar texto).
