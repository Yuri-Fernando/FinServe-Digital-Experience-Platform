# Segurança — escopo do laboratório

## Ameaças e limites

**A aplicação de demonstração não deve ser exposta publicamente.** `run.py` faz bind em `127.0.0.1`; o header `X-Demo-Role` é totalmente controlado por quem chama e **não é autenticação**. O conteúdo e as métricas de campanha são sintéticos; as séries de mercado são dados públicos do Banco Central.

## Controles existentes

| Controle | Onde | Teste |
|---|---|---|
| SQL parametrizado; identificadores de tabela do dicionário vêm de lista fechada (`Module.tables`) | `db.py`, `platform/router.py` | — |
| Validação de campos, segmento, chave e CTA interna (`/…`, sem `//` nem `\`) | Pydantic + `experience/service.validate_item` | `test_unsafe_cta_denied` |
| Tokens de conteúdo restritos a uma lista (`selic_meta`, `cdi_anual`, `ipca_12m`, `usd_brl`) | `experience/service.py` | `test_unknown_token_rejected` |
| Compliance editorial bloqueia promessa de retorno/aprovação garantida e **dado pessoal** (CPF, e-mail, telefone) em conteúdo público; erro do motor bloqueia | `experience/compliance*` | `test_each_compliance_rule_fires`, `test_compliance_engine_fail_safe` |
| Escape de todo texto dinâmico antes de entrar no DOM | `dashkit/kit.js` (`esc`) | E2E manual no navegador |
| Entrega pública só de itens `PUBLISHED` | `experience/service.published` | `test_published_only_in_delivery` |
| Trilha de auditoria única (`audit_events`) e revisões versionadas | `audit.py` | `test_workflow_roles_versioning_and_publication` |
| Cliente do BCB só biblioteca padrão, URL fixa, payload validado, timeout e novas tentativas limitadas | `market/bcb.py` | `test_parse_sgs_rejects_malformed` |
| `POST /api/market/sync` e `/api/experience/reset` exigem papel `admin` demo | routers | `test_sync_requires_admin` |
| Nenhum CPF, telefone, conta, saldo, biometria ou cookie de rastreamento coletado | — | — |

## Não existe (obrigatório em ambiente real)
- SSO/IMS/OIDC, identidade verificável, ACL no JCR, proteção CSRF, CORS por origem, rate limiting, log central, gestão de segredos e criptografia em repouso.
- Revisão de compliance por pessoa habilitada: as regras YAML são **heurísticas educacionais**, não parecer jurídico.
- Consentimento (LGPD), DPO, antifraude e concessão de crédito reais.
- Restrições de Dispatcher, cache e headers validadas em AEM SDK real.

## Observações
- O cliente de sincronização faz **requisições de saída** para `api.bcb.gov.br` e `olinda.bcb.gov.br` apenas quando acionado (CLI ou `POST /api/market/sync`); o início da aplicação nunca acessa a rede.
- `POST /api/experience/reset` **apaga conteúdo e auditoria do módulo experience**. Deve ser desabilitado em qualquer serviço conectado à rede.
- Os testes não usam rede (o cliente do BCB é testado com um *fetch* injetado).
