# Criando e reaproveitando módulos

Um módulo é um pacote Python que expõe `MODULE: finserve.registry.Module`.

```python
Module(
    name="cartoes", title="Cartões", version="0.1.0", description="...",
    router=router,                  # APIRouter; montado em /api/<name>
    schema=Path("schema.sql"),      # CREATE TABLE IF NOT EXISTS ... (idempotente)
    tables=("cartoes_items",),      # entram no dicionário de dados
    seed=seed_fn,                   # seed(con) idempotente, roda a cada start
    datasets=datasets_fn,           # datasets(con) -> [Dataset(... kind="real|synthetic|derived")]
    dashboards=[SPEC],              # specs do dashkit (ver DASHKIT.md)
    requires=("platform",),         # dependências duras (falha ao carregar se ausentes)
    optional=("market",),           # dependências opcionais (degradação segura)
)
```

## Fluxo rápido

```bash
python -m finserve new-module cartoes     # gera __init__.py, router.py, schema.sql e um teste
python -m finserve modules                # o módulo já aparece (descoberta automática)
python -m finserve check                  # valida specs de dashboard e regras de compliance
python -m pytest                          # o teste gerado deve passar
```

O `new-module` **nunca sobrescreve** um módulo existente.

## Habilitar um subconjunto

| Como | Efeito |
|---|---|
| `FINSERVE_MODULES=platform,market` | só esses módulos (o `platform` sempre entra) |
| `create_app(["market"])` | idem, em código/testes |
| `FINSERVE_EXTRA_MODULES=meu_pacote.modulo` | módulo externo (fora do repositório) |
| entry point `finserve.modules` | módulo distribuído como pacote pip |

Um módulo com `requires` ausente falha na inicialização com `ModuleError`; ciclos de dependência também são detectados.

## Convenções
- Rotas: `/api/<modulo>/...`; nada fora desse prefixo.
- Toda tabela nova entra em `tables`; todo dataset novo declara proveniência.
- Escritas relevantes chamam `finserve.audit.record(...)` (trilha única em `audit_events`).
- Dependência opcional entre módulos é checada em tempo de execução (`request.app.state.modules`), nunca por import direto.
- Cálculos (estatística, finanças) ficam em funções puras, testáveis sem banco nem rede.
