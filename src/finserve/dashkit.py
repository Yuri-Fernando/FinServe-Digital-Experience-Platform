"""Contrato de especificação de dashboard (lado servidor do `dashkit`).

Qualquer módulo descreve um dashboard como um dicionário JSON; o front (`web/assets/dashkit/`) o renderiza sem
código específico. Este arquivo define o vocabulário de widgets e o validador usado nos testes.
"""
from __future__ import annotations

WIDGET_TYPES: dict[str, set[str]] = {
    # tipo -> campos obrigatórios
    "kpis": {"items"},
    "line": {"path", "x", "series"},
    "bars": {"path", "label", "value"},
    "donut": {"path", "label", "value"},
    "funnel": {"path", "stages"},
    "vitals": {"path"},
    "table": {"path", "columns"},
    "list": {"path", "primary"},
    "notes": {"items"},
    "calculator": {"calc"},
}
FORMATS = {"int", "compact", "pct", "pct1", "money", "money2", "num2", "num4", "text", "date", "ms", "badge", "bool", "month"}
CALCULATORS = {"investment", "loan"}


class SpecError(ValueError):
    pass


def validate_spec(spec: dict) -> None:
    for key in ("id", "title", "sources", "widgets"):
        if key not in spec:
            raise SpecError(f"dashboard sem '{key}'")
    sources = spec["sources"]
    if not isinstance(sources, dict) or "main" not in sources:
        raise SpecError("sources precisa conter 'main'")
    for name, src in sources.items():
        if not str(src.get("url", "")).startswith("/api/"):
            raise SpecError(f"fonte '{name}' precisa de url iniciando em /api/")
    filter_ids = {f["id"] for f in spec.get("filters", [])}
    for name, src in sources.items():
        unknown = set(src.get("params", [])) - filter_ids
        if unknown:
            raise SpecError(f"fonte '{name}' usa parâmetros sem filtro: {sorted(unknown)}")
    for i, w in enumerate(spec["widgets"]):
        t = w.get("type")
        if t not in WIDGET_TYPES:
            raise SpecError(f"widget #{i}: tipo desconhecido '{t}'")
        missing = WIDGET_TYPES[t] - set(w)
        if missing:
            raise SpecError(f"widget #{i} ({t}): faltam campos {sorted(missing)}")
        if w.get("source", "main") not in sources:
            raise SpecError(f"widget #{i} ({t}): fonte '{w.get('source')}' inexistente")
        if t == "calculator" and w["calc"] not in CALCULATORS:
            raise SpecError(f"widget #{i}: calculadora desconhecida '{w['calc']}'")
        fmts = [w.get("format")] + [it.get("format") for it in w.get("items", []) if isinstance(it, dict)]
        fmts += [c.get("format") for c in w.get("columns", [])]
        for f in filter(None, fmts):
            if f not in FORMATS:
                raise SpecError(f"widget #{i} ({t}): formato desconhecido '{f}'")
