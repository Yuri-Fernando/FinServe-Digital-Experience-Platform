# ADR 0001 — Registry de módulos em vez de monólito

**Status:** aceito · **Contexto:** a v1 era um único `main.py` com dashboard, CMS e dados misturados; reaproveitar qualquer parte exigia copiar código.

**Decisão:** núcleo mínimo (`registry`, `db`, `audit`, `app`) + módulos plugáveis que declaram rotas, schema, seed, proveniência e dashboards em um objeto `Module`. A descoberta é automática (subpacotes de `finserve/modules/`), com subconjunto por `FINSERVE_MODULES`, módulos externos por `FINSERVE_EXTRA_MODULES` ou entry point.

**Consequências:** (+) módulos testáveis isoladamente (`create_app(["market"])`), `finserve new-module` gera o esqueleto; (+) dependências duras (`requires`) e opcionais (`optional`) explícitas, com detecção de ausência e de ciclo. (−) o `Module` é um contrato novo a manter; a dependência opcional é verificada em runtime, não em import.

**Alternativas descartadas:** blueprints soltos sem manifesto (sem validação de dependências); plugin system só por entry points (atrito para uso local).
