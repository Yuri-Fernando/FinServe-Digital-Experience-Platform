"""CLI: `finserve <comando>` (ou `python -m finserve <comando>`)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import __version__, config, registry
from .app import bootstrap
from .db import connect

TEMPLATE_INIT = '''from pathlib import Path

from ...registry import Dataset, Module
from .router import router

DASHBOARD = {{
    "id": "{name}",
    "title": "{title}",
    "eyebrow": "MÓDULO · {upper}",
    "subtitle": "Dashboard declarativo do módulo {name}.",
    "nav": {{"label": "{title}", "icon": "◆", "order": 50}},
    "filters": [],
    "sources": {{"main": {{"url": "/api/{name}/summary"}}}},
    "widgets": [
        {{"type": "kpis", "items": [{{"label": "Itens", "path": "total", "format": "int"}}]}},
    ],
}}


def _datasets(con):
    return [Dataset("{name}.example", "{name}", "Dataset de exemplo", "synthetic", "gerado no scaffold")]


MODULE = Module(
    name="{name}",
    title="{title}",
    version="0.1.0",
    description="Descreva o módulo {name}.",
    router=router,
    schema=Path(__file__).with_name("schema.sql"),
    tables=("{name}_items",),
    datasets=_datasets,
    dashboards=[DASHBOARD],
    requires=("platform",),
)
'''
TEMPLATE_ROUTER = '''from fastapi import APIRouter

from ...db import connect

router = APIRouter()


@router.get("/summary")
def summary():
    with connect() as con:
        return {{"total": con.execute("SELECT COUNT(*) FROM {name}_items").fetchone()[0]}}
'''
TEMPLATE_SCHEMA = """CREATE TABLE IF NOT EXISTS {name}_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 label TEXT NOT NULL
);
"""
TEMPLATE_TEST = '''from fastapi.testclient import TestClient

from finserve.app import create_app


def test_{name}_module_loads(tmp_path, monkeypatch):
    monkeypatch.setenv("FINSERVE_DB", str(tmp_path / "t.sqlite3"))
    with TestClient(create_app(["platform", "{name}"])) as c:
        assert c.get("/api/{name}/summary").json() == {{"total": 0}}
        assert "{name}" in [m["name"] for m in c.get("/api/platform/modules").json()]
'''


def new_module(name: str) -> int:
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,30}", name):
        print("Nome inválido: use minúsculas, dígitos e _, 3–31 caracteres.", file=sys.stderr)
        return 2
    base = Path(__file__).parent / "modules" / name
    if base.exists():
        print(f"O módulo '{name}' já existe — nada foi sobrescrito.", file=sys.stderr)
        return 1
    ctx = {"name": name, "title": name.replace("_", " ").title(), "upper": name.upper()}
    base.mkdir(parents=True)
    (base / "__init__.py").write_text(TEMPLATE_INIT.format(**ctx), encoding="utf-8")
    (base / "router.py").write_text(TEMPLATE_ROUTER.format(**ctx), encoding="utf-8")
    (base / "schema.sql").write_text(TEMPLATE_SCHEMA.format(**ctx), encoding="utf-8")
    tests = config.ROOT / "tests"
    if tests.is_dir():
        (tests / f"test_module_{name}.py").write_text(TEMPLATE_TEST.format(**ctx), encoding="utf-8")
    print(f"Módulo criado em {base}. Ele é carregado automaticamente; rode `finserve modules` para conferir.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="finserve", description="FinServe Platform — CLI")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="inicia a API e o front (127.0.0.1)")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--host", default="127.0.0.1")
    sub.add_parser("modules", help="lista módulos habilitados")
    sd = sub.add_parser("seed", help="aplica schemas e seeds")
    sd.add_argument("--reset", action="store_true", help="recria dados sintéticos (analytics e experience)")
    sub.add_parser("market-sync", help="consulta o Banco Central agora (rede)")
    sub.add_parser("market-snapshot", help="regrava data/snapshots/ com dados reais (rede)")
    sub.add_parser("check", help="valida specs de dashboard, regras de compliance e integridade dos dados")
    sub.add_parser("dictionary", help="imprime o dicionário de dados (Markdown) lido do banco")
    rp = sub.add_parser("report", help="gera reports/metrics.json e reports/report.md em banco temporário (reproduzível)")
    rp.add_argument("--today", default="2026-11-10", help="data de referência (padrão: data de coleta do snapshot)")
    rp.add_argument("--out", default=str(config.ROOT / "reports"))
    nm = sub.add_parser("new-module", help="gera o esqueleto de um módulo novo")
    nm.add_argument("name")
    args = p.parse_args(argv)

    if args.cmd == "new-module":
        return new_module(args.name)
    if args.cmd == "report":
        from .report import build_report

        info = build_report(Path(args.out), args.today)
        print(json.dumps(info, ensure_ascii=False))
        return 0
    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("finserve.app:app", host=args.host, port=args.port, reload=False)
        return 0

    mods = registry.load()
    if args.cmd == "modules":
        for m in mods:
            print(f"{m.name:<12} v{m.version:<7} {m.description}")
        return 0
    if args.cmd == "seed":
        bootstrap(mods)
        if args.reset:
            from .modules.analytics.seed import reset_and_seed as reset_analytics
            from .modules.experience.seed import reset_and_seed as reset_experience

            with connect() as con:
                names = {m.name for m in mods}
                if "analytics" in names:
                    print("analytics:", reset_analytics(con))
                if "experience" in names:
                    print("experience:", reset_experience(con))
        print("ok")
        return 0
    if args.cmd == "market-sync":
        from .modules.market import store

        bootstrap(mods)
        with connect() as con:
            print(json.dumps(store.sync(con), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "market-snapshot":
        from .modules.market import store

        print(json.dumps(store.write_snapshot(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "dictionary":
        from .db import rows

        bootstrap(mods)
        out = ["# Dicionário de dados", "",
               "Gerado por `python -m finserve dictionary` a partir do schema real (PRAGMA table_info). Não editar à mão.", ""]
        with connect() as con:
            for m in mods:
                for table in m.tables:
                    out += [f"## `{table}` — módulo `{m.name}`", "", "| Coluna | Tipo | Obrigatória | PK |", "|---|---|---|---|"]
                    out += [f"| `{c['name']}` | {c['type'] or '—'} | {'sim' if c['notnull'] else 'não'} | {'sim' if c['pk'] else ''} |"
                            for c in rows(con, f"PRAGMA table_info({table})")]
                    out.append("")
        sys.stdout.reconfigure(encoding="utf-8")
        print("\n".join(out))
        return 0
    if args.cmd == "check":
        from . import dashkit
        from .modules.experience import compliance

        problems = 0
        for m in mods:
            for d in m.dashboards:
                try:
                    dashkit.validate_spec(d)
                    print(f"[ok] dashboard {d['id']}")
                except dashkit.SpecError as exc:
                    problems += 1
                    print(f"[ERRO] dashboard {d['id']}: {exc}")
        try:
            print(f"[ok] compliance v{compliance.load_rules()['version']} ({len(compliance.public_rules())} regras)")
        except compliance.ComplianceError as exc:
            problems += 1
            print(f"[ERRO] compliance: {exc}")
        return 1 if problems else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
