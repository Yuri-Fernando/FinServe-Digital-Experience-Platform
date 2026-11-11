from pathlib import Path

from ...registry import Module
from .router import router

GOVERNANCE = {
    "id": "governance",
    "title": "Governança",
    "eyebrow": "PLATAFORMA · PROVENIÊNCIA",
    "subtitle": "Quais módulos estão ativos, de onde vem cada dado (real × sintético) e quem fez o quê.",
    "nav": {"label": "Governança", "icon": "◇", "order": 10, "group": "ENGENHARIA"},
    "filters": [],
    "sources": {
        "main": {"url": "/api/platform/modules"},
        "prov": {"url": "/api/platform/provenance"},
        "audit": {"url": "/api/platform/audit?limit=12"},
    },
    "notice": "Regra da plataforma: todo dataset declara se é real, sintético ou derivado, com fonte e data de coleta.",
    "widgets": [
        {"type": "table", "source": "prov", "title": "Proveniência dos dados", "kicker": "DATASETS", "path": "datasets", "span": 3,
         "columns": [{"key": "title", "label": "Dataset"}, {"key": "kind", "label": "Tipo", "format": "badge"},
                     {"key": "source", "label": "Fonte"}, {"key": "rows", "label": "Linhas", "format": "int"},
                     {"key": "retrieved_at", "label": "Coletado em", "format": "date"}]},
        {"type": "table", "title": "Módulos ativos", "kicker": "REGISTRY", "path": "", "span": 2,
         "columns": [{"key": "name", "label": "Módulo"}, {"key": "version", "label": "Versão"},
                     {"key": "endpoints_prefix", "label": "Prefixo da API"}, {"key": "description", "label": "Descrição"}]},
        {"type": "list", "source": "audit", "title": "Auditoria recente", "kicker": "RASTREABILIDADE", "path": "",
         "primary": "{actor} · {action} · {entity}#{entity_id}", "secondary": "{module} · {occurred_at}", "limit": 8},
    ],
}

MODULE = Module(
    name="platform",
    title="Plataforma",
    version="2.0.0",
    description="Núcleo: saúde, catálogo de módulos, proveniência de dados, dicionário, auditoria e specs de dashboard.",
    router=router,
    schema=Path(__file__).with_name("schema.sql"),
    tables=("audit_events",),
    dashboards=[GOVERNANCE],
)
