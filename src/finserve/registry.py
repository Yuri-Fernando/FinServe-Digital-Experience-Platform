"""Registry de módulos — o que torna a plataforma uma ferramenta modular.

Um módulo é um pacote Python que expõe `MODULE: Module`. Ele declara: rotas, schema SQL, seed idempotente,
proveniência dos datasets e especificações de dashboard (consumidas pelo `dashkit` no front).
Módulos externos entram por `FINSERVE_EXTRA_MODULES=pacote.modulo` ou pelo entry point `finserve.modules`.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Callable

from fastapi import APIRouter

BUILTIN = ("platform", "experience", "analytics", "market")


class ModuleError(RuntimeError):
    """Módulo ausente, inválido ou com dependência não satisfeita."""


@dataclass(frozen=True)
class Dataset:
    """Proveniência de um conjunto de dados: nunca misturar dado real com sintético sem rótulo."""

    id: str
    module: str
    title: str
    kind: str  # 'real' | 'synthetic' | 'derived'
    source: str
    source_url: str | None = None
    retrieved_at: str | None = None
    rows: int | None = None
    note: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Module:
    name: str
    title: str
    version: str
    description: str
    router: APIRouter | None = None
    schema: Path | None = None
    tables: tuple[str, ...] = ()
    seed: Callable[[sqlite3.Connection], None] | None = None
    datasets: Callable[[sqlite3.Connection], list[Dataset]] | None = None
    dashboards: list[dict] = field(default_factory=list)
    requires: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()

    def manifest(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "endpoints_prefix": f"/api/{self.name}",
            "tables": list(self.tables),
            "dashboards": [d["id"] for d in self.dashboards],
            "requires": list(self.requires),
            "optional": list(self.optional),
        }


def _import_module(dotted: str) -> Module:
    try:
        mod = importlib.import_module(dotted)
    except ImportError as exc:
        raise ModuleError(f"não foi possível importar o módulo '{dotted}': {exc}") from exc
    m = getattr(mod, "MODULE", None)
    if not isinstance(m, Module):
        raise ModuleError(f"'{dotted}' não expõe MODULE do tipo finserve.registry.Module")
    return m


def _available_local() -> list[str]:
    """Módulos nativos + qualquer subpacote novo em finserve/modules/ (ex.: criado por `finserve new-module`)."""
    import pkgutil

    from finserve import modules as pkg

    extra = sorted(m.name for m in pkgutil.iter_modules(pkg.__path__) if m.ispkg and m.name not in BUILTIN)
    return [*BUILTIN, *extra]


def _wanted(explicit: list[str] | None) -> list[str]:
    if explicit is not None:
        names = list(explicit)
    elif os.environ.get("FINSERVE_MODULES"):
        names = [n.strip() for n in os.environ["FINSERVE_MODULES"].split(",") if n.strip()]
    else:
        names = _available_local()
    if "platform" not in names:
        names.insert(0, "platform")  # o núcleo é sempre carregado
    return names


def load(explicit: list[str] | None = None) -> list[Module]:
    """Carrega módulos habilitados, valida dependências e devolve em ordem estável de dependência."""
    loaded: dict[str, Module] = {}
    local = set(_available_local())
    for name in _wanted(explicit):
        m = _import_module(f"finserve.modules.{name}" if name in local else name)
        loaded[m.name] = m
    for dotted in filter(None, (s.strip() for s in os.environ.get("FINSERVE_EXTRA_MODULES", "").split(","))):
        m = _import_module(dotted)
        loaded[m.name] = m
    try:
        for ep in metadata.entry_points(group="finserve.modules"):
            m = ep.load()
            if isinstance(m, Module):
                loaded.setdefault(m.name, m)
    except Exception:  # entry points quebrados não derrubam a plataforma
        pass

    for m in loaded.values():
        for dep in m.requires:
            if dep not in loaded:
                raise ModuleError(f"módulo '{m.name}' requer '{dep}', que não está habilitado")

    ordered: list[Module] = []
    pending = dict(loaded)
    while pending:
        progressed = False
        for name, m in list(pending.items()):
            if all(d in {x.name for x in ordered} for d in m.requires):
                ordered.append(m)
                del pending[name]
                progressed = True
        if not progressed:
            raise ModuleError(f"dependência circular entre módulos: {sorted(pending)}")
    return ordered
