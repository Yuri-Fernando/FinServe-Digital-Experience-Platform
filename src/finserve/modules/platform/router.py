from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ... import __version__
from ...audit import utcnow
from ...db import connect, rows

router = APIRouter()


@router.get("/health")
def health(request: Request):
    with connect() as con:
        con.execute("SELECT 1").fetchone()
    return {
        "status": "ok",
        "version": __version__,
        "modules": [m.name for m in request.app.state.modules],
        "database": "ok",
        "time": utcnow(),
        "mode": "demo-local",
    }


@router.get("/modules")
def modules(request: Request):
    return [m.manifest() for m in request.app.state.modules]


@router.get("/provenance")
def provenance(request: Request):
    """Cada dataset declara se é real, sintético ou derivado — e de onde veio."""
    out = []
    with connect() as con:
        for m in request.app.state.modules:
            if m.datasets:
                out.extend(d.as_dict() for d in m.datasets(con))
    return {"datasets": out, "kinds": {"real": "dado público oficial", "synthetic": "gerado por código, seed fixa", "derived": "calculado a partir de dados reais"}}


@router.get("/dictionary")
def dictionary(request: Request):
    with connect() as con:
        result = {}
        for m in request.app.state.modules:
            for table in m.tables:
                result[table] = {"module": m.name, "columns": rows(con, f"PRAGMA table_info({table})")}
        return result


@router.get("/audit")
def audit(limit: int = Query(30, ge=1, le=200), module: str | None = None):
    sql = "SELECT * FROM audit_events"
    args: tuple = ()
    if module:
        sql += " WHERE module=?"
        args = (module,)
    sql += " ORDER BY id DESC LIMIT ?"
    with connect() as con:
        return rows(con, sql, (*args, limit))


@router.get("/dashboards")
def dashboards(request: Request):
    out = []
    for m in request.app.state.modules:
        for d in m.dashboards:
            out.append({"id": d["id"], "module": m.name, "title": d["title"], "nav": d.get("nav", {})})
    return sorted(out, key=lambda d: d["nav"].get("order", 99))


@router.get("/dashboards/{dashboard_id}")
def dashboard_spec(dashboard_id: str, request: Request):
    for m in request.app.state.modules:
        for d in m.dashboards:
            if d["id"] == dashboard_id:
                return d
    raise HTTPException(404, "Dashboard não encontrado")
