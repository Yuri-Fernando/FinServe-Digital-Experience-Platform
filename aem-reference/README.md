# AEM Reference Module — **NOT a deployable AEM Maven project**

Esses arquivos são exemplos de como mapear o laboratório para Adobe Experience Manager. **Não foram compilados nem testados em AEM**, porque o AEM Cloud SDK/Cloud Manager e suas dependências não estão disponíveis neste ambiente. **Não há `pom.xml` aqui de propósito**: copiar pedaços de um arquétipo e apresentar como build válido seria enganoso.

## Para transformar em projeto AEM real

1. Obtenha acesso licenciado ao AEM as a Cloud Service SDK e seu Java API Jar.
2. Gere um projeto no **AEM Project Maven Archetype** atualizado e mantenha os módulos gerados (`core`, `ui.apps`, `ui.content`, `ui.config`, `ui.frontend`, `all`, `dispatcher`).
3. Transfira `core/src` para o módulo `core`, `ui.apps/src` para `ui.apps`, `ui.content/src` para `ui.content`. O frontend TypeScript é um adaptador demonstrativo independente do frontend JS executável local.
4. Corrija dependências e padrões conforme a versão do SDK, escreva testes unitários de Sling Models e valide o diálogo no Author; defina templates e permissões JCR reais.
5. Crie Content Fragment Model + persisted GraphQL query no Author; libere só conteúdo público via Publish/Dispatcher.
6. Configure OSGi, CORS, saneamento de URL, ACL e cache conforme a implantação real. Os dados financeiros do laboratório não devem ser publicados em AEM.
7. Valide build Maven e deployment pelo Cloud Manager; registre métricas Lighthouse e resultados reais.

## Mapeamento de capacidades AEM

| Capacidade AEM | Exemplo neste diretório |
|---|---|
| Java / OSGi / Apache Sling | Sling Model + Servlet de referência |
| HTL/Sightly | `campaignhero.html` |
| Granite UI | `_cq_dialog/.content.xml` |
| Componentes editáveis | `campaignhero/.content.xml` + autor no AEM |
| Headless | `ui.frontend/src/aemContentClient.ts` |
| Dispatcher / cache | `dispatcher/README.md` com política de segurança |
| React/Angular | **Não implementado no runtime da demo**; requisito permanece parcial |
| Cloud Manager | **Não utilizado**; requer ambiente real |

Consulte: https://experienceleague.adobe.com/en/docs/experience-manager-core-components/using/developing/archetype/using

## Relação com a camada local (v2)

O módulo `experience` da plataforma entrega localmente o que o Publish entregaria: `/api/experience/delivery` e `/api/experience/model/{segmento}.model.json` (forma `:type/:items/:itemsOrder`), com `ETag`/`Cache-Control`. O cliente TypeScript acima consome GraphQL de Content Fragments — um contrato **diferente** do JSON local; ele continua sendo apenas referência, sem execução em AEM.
