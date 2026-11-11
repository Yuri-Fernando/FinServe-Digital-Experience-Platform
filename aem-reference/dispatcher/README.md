# Dispatcher — política de referência, NÃO configuração de produção

Para integrar o projeto ao AEM as a Cloud Service, gere um projeto com módulo `dispatcher` pelo AEM Maven Archetype e edite a configuração gerada pelo SDK. Não substitua os filtros do projeto gerado por um snippet descontextualizado.

Regras de projeto:

- Negar acesso anônimo a `*.model.json` que contenha informações não públicas e a endpoints internos de authoring.
- Permitir apenas URLs específicas de entrega pública e persisted GraphQL queries aprovadas.
- Definir cache explícito para fragmentos públicos; evitar cache compartilhado de qualquer payload personalizado ou dependente de sessão.
- Preservar autenticação/autorização e ACL JCR no Publish; filtros Dispatcher não substituem ACL.
- Validar sintaxe e regras com `dispatcher validator` do SDK, regras Cloud Manager e testes de integração reais.
- Evitar dados financeiros, dados pessoais e tokens nas páginas AEM e caches.

Referência Adobe: https://experienceleague.adobe.com/en/docs/experience-manager-cloud-service/content/headless/deployment/dispatcher
