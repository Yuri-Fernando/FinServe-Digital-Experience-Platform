# Roadmap de integração real Adobe AEM — critérios de aceite

Este roadmap explicita as lacunas remanescentes para ser um projeto demonstrativo **realmente AEM**, em vez de uma cópia visual de CMS. A versão v2 é uma plataforma modular FastAPI/SQLite funcional localmente (com camada de entrega headless que espelha o contrato do Publish), mais **referências** Java/HTL em `aem-reference/` para aprendizado — nada disso foi executado em AEM.

## M1 — AEM SDK e Maven (não iniciado)
- [ ] Obter licença/acesso ao AEM as a Cloud Service SDK e artifacts conforme Adobe.
- [ ] Criar projeto Maven pelo AEM Project Archetype atualizado, usando package `br.com.finserve.aem`.
- [ ] Executar Author/Publish locais e Dispatcher Tools, salvar logs e evidências.
- [ ] Compilar e instalar `core`, `ui.apps`, `ui.content` no SDK real.

**Aceite:** `mvn clean verify` válido para o SDK selecionado, componentes disponíveis em Author e renderizados em Publish. Sem SDK, não marcar como feito.

## M2 — Componentes editoriais e modelos (não iniciado)
- [ ] Transferir Sling Model e HTL para o arquétipo gerado.
- [ ] Criar editable template e template policies, incluir Core Components, estilos responsivos e acessibilidade.
- [ ] Criar Content Fragment Model de campanha, persistida no JCR, com persisted GraphQL query.
- [ ] Validar Granite/Coral UI, autor/preview, XSS, restrições de CTA, links internos.
- [ ] Criar JUnit + AEM Mocks, testes de HTL e authoring.

**Aceite:** editor cria e publica campanha no Author, componente entregue via Publish e via GraphQL, com validação de campos.

## M3 — Workflow e governança (não iniciado)
- [ ] Definir grupos Author, Marketing Reviewer e Publisher no AEM real e ACL JCR.
- [ ] Aprovação editorial via AEM Workflows com trilha de revisão e bloqueio de publicação prematura.
- [ ] Testar separação de funções com contas reais de teste e auditoria.

**Aceite:** usuário autor sem privilégio de publicação não consegue publicar por API/UI; revisão vinculada à identidade autenticada.

## M4 — Dispatcher, cache, SEO e analytics (não iniciado)
- [ ] Configurar Dispatcher com deny-by-default, persisted queries aprovadas, invalidation e teste de cache.
- [ ] Medir Web Vitals com Lighthouse e/ou RUM real, remover estatísticas simuladas dos relatórios de produção.
- [ ] Integrar Adobe Analytics/Tags e, se houver licença e necessidade, Target; validar consentimento LGPD.
- [ ] Criar indicadores reais e documentação de medição da jornada.

**Aceite:** cabeçalhos e cache verificados com testes, métricas reais rastreáveis e autorização efetiva.

## M5 — CI/CD e operação (não iniciado)
- [ ] Configurar Cloud Manager conforme conta e ambientes disponíveis.
- [ ] Criar pipeline build/test/scan e deployment, observabilidade, rollback e testes de carga.
- [ ] Documentar OpenAPI/GraphQL schema, DRIs, runbooks, incidentes e mudanças.

**Aceite:** pipeline Cloud Manager e ambiente autorizados com evidência de execução e controle de mudanças.

## Por que não marquei essas tarefas como prontas?
Criar Java de referência ou um frontend parecido com CMS **não equivale** a programar e operar AEM. Sem o SDK e sem validação, afirmar experiência com AEM Cloud Manager seria impreciso; este roadmap existe para deixar a lacuna explícita.

## Correspondência entre a camada local e o AEM (conceitual, não validada)

| Camada local (v2) | Equivalente conceitual no AEM |
|---|---|
| Content Studio (DRAFT → IN_REVIEW → APPROVED → PUBLISHED) | Author + Workflows + ACL |
| `/api/experience/delivery` (só PUBLISHED) | Publish |
| `ETag` + `Cache-Control` + 304 | Dispatcher / CDN (persisted queries via GET) |
| `/api/experience/model/{segmento}.model.json` | Sling Model Exporter (`.model.json`) |
| Tokens `{{selic_meta}}` resolvidos na entrega | Content Fragment + dados externos via API |
| Compliance YAML no submit/publish | Regra de workflow / revisão editorial |
