from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from ... import audit
from ...db import connect, rows
from . import compliance, seed, service

router = APIRouter()
Segment = Literal["all", "investidor", "credito", "jovem"]
CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=300"


class ContentCreate(BaseModel):
    key: str = Field(min_length=4, max_length=60, pattern=r"^[a-z][a-z0-9-]+$")
    component: Literal["campaignhero", "promobanner", "ratecard"] = "promobanner"
    eyebrow: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=4, max_length=500)
    cta_label: str = Field(min_length=1, max_length=60)
    cta_url: str = Field(min_length=1, max_length=120)
    segment: Segment = "all"


class ContentEdit(BaseModel):
    version: int = Field(ge=1)
    eyebrow: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=4, max_length=500)
    cta_label: str = Field(min_length=1, max_length=60)
    cta_url: str = Field(min_length=1, max_length=120)
    segment: Segment


class Transition(BaseModel):
    action: Literal["submit", "approve", "reject", "publish", "archive"]
    notes: str = Field(default="", max_length=240)


class ComplianceIn(BaseModel):
    eyebrow: str = ""
    title: str = ""
    body: str = ""
    cta_label: str = ""
    cta_url: str = ""


def _http(exc: service.ContentError) -> HTTPException:
    return HTTPException(exc.status, exc.detail)


def _role(role: str, allowed: set[str]) -> None:
    if role not in allowed:
        raise HTTPException(403, f"Papel demo insuficiente. Permitidos: {', '.join(sorted(allowed))}")


def _market_tokens(request: Request, con) -> dict:
    """Integração opcional: sem o módulo market, os tokens resolvem para '—'."""
    if not any(m.name == "market" for m in request.app.state.modules):
        return {"values": {}, "as_of": None}
    from ..market import service as market_service

    return market_service.tokens(con)


@router.get("/content")
def content_list(status: str | None = None):
    with connect() as con:
        if status:
            return rows(con, "SELECT * FROM content_items WHERE status=? ORDER BY updated_at DESC,id DESC", (status,))
        return rows(con, "SELECT * FROM content_items ORDER BY id")


@router.get("/content/{item_id}")
def content_detail(item_id: int):
    with connect() as con:
        item = rows(con, "SELECT * FROM content_items WHERE id=?", (item_id,))
        if not item:
            raise HTTPException(404, "Conteúdo não encontrado")
        return {
            "content": item[0],
            "revisions": rows(con, "SELECT version,actor,reason,created_at FROM content_revisions WHERE content_id=? "
                                   "ORDER BY version DESC", (item_id,)),
            "audit": rows(con, "SELECT actor,action,from_status,to_status,notes,occurred_at FROM audit_events "
                               "WHERE module='experience' AND entity='content' AND entity_id=? ORDER BY id DESC", (item_id,)),
            "compliance": compliance.check(item[0]),
        }


@router.get("/content/{item_id}/diff")
def content_diff(item_id: int, from_version: int = Query(ge=1), to_version: int = Query(ge=1)):
    with connect() as con:
        try:
            return service.diff_versions(con, item_id, from_version, to_version)
        except service.ContentError as exc:
            raise _http(exc) from exc


@router.post("/content", status_code=201)
def create_content(body: ContentCreate, x_demo_role: str = Header("author")):
    _role(x_demo_role, {"author"})
    data = body.model_dump()
    try:
        service.validate_item(data)
    except service.ContentError as exc:
        raise _http(exc) from exc
    now = audit.utcnow()
    with connect() as con:
        if con.execute("SELECT 1 FROM content_items WHERE key=?", (body.key,)).fetchone():
            raise HTTPException(409, "Chave já existe")
        cur = con.execute(
            """INSERT INTO content_items(key,component,eyebrow,title,body,cta_label,cta_url,segment,status,version,owner,updated_at)
               VALUES(?,?,?,?,?,?,?,?,'DRAFT',1,?,?)""", (*data.values(), x_demo_role, now))
        item = service.snapshot(con, cur.lastrowid)
        service.add_revision(con, item, x_demo_role, "Criação", now)
        service.record(con, item["id"], x_demo_role, "create", None, "DRAFT", "Novo conteúdo", now)
        return item


@router.put("/content/{item_id}")
def update_content(item_id: int, body: ContentEdit, x_demo_role: str = Header("author")):
    _role(x_demo_role, {"author"})
    try:
        service.validate_item(body.model_dump())
    except service.ContentError as exc:
        raise _http(exc) from exc
    now = audit.utcnow()
    with connect() as con:
        item = con.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(404, "Conteúdo não encontrado")
        if item["status"] != "DRAFT":
            raise HTTPException(409, "Somente conteúdos DRAFT podem ser editados")
        if item["version"] != body.version:
            raise HTTPException(409, "Conflito de versão: recarregue antes de salvar")
        con.execute("UPDATE content_items SET eyebrow=?,title=?,body=?,cta_label=?,cta_url=?,segment=?,version=version+1,"
                    "updated_at=? WHERE id=?", (body.eyebrow, body.title, body.body, body.cta_label, body.cta_url,
                                                body.segment, now, item_id))
        new = service.snapshot(con, item_id)
        service.add_revision(con, new, x_demo_role, "Edição de conteúdo", now)
        service.record(con, item_id, x_demo_role, "edit", "DRAFT", "DRAFT", "Edição versionada", now)
        return new


@router.post("/content/{item_id}/transition")
def transition(item_id: int, body: Transition, x_demo_role: str = Header("author")):
    frm, to, allowed = service.TRANSITIONS[body.action]
    _role(x_demo_role, allowed)
    now = audit.utcnow()
    with connect() as con:
        item = con.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(404, "Conteúdo não encontrado")
        if item["status"] != frm:
            raise HTTPException(409, f"Transição inválida: {item['status']} → {to}; esperado {frm}")
        notes = body.notes
        if body.action in ("submit", "publish"):
            result = compliance.check(dict(item))
            if not result["passed"]:
                raise HTTPException(422, {"message": "Bloqueado pelo compliance editorial", "compliance": result})
            if result["warnings"]:
                ids = ",".join(sorted({i["rule_id"] for i in result["issues"]}))
                notes = f"{notes} [avisos de compliance: {ids}]".strip()
        published_at = now if to == "PUBLISHED" else item["published_at"]
        con.execute("UPDATE content_items SET status=?,updated_at=?,published_at=? WHERE id=?", (to, now, published_at, item_id))
        service.record(con, item_id, x_demo_role, body.action, frm, to, notes, now)
        return service.snapshot(con, item_id)


@router.post("/compliance/check")
def compliance_check(body: ComplianceIn):
    return compliance.check(body.model_dump())


@router.get("/compliance/rules")
def compliance_rules():
    return {"version": compliance.load_rules()["version"], "rules": compliance.public_rules()}


@router.get("/stats")
def stats():
    with connect() as con:
        return service.stats(con)


def _delivery(request: Request, response: Response, segment: str, shape: str):
    with connect() as con:
        items = service.published(con, segment)
        tok = _market_tokens(request, con)
    resolved = [service.resolve_item(i, tok["values"]) for i in items]
    payload = (service.aem_model(segment, resolved, tok["as_of"]) if shape == "model" else
               {"segment": segment, "content": resolved, "data_as_of": tok["as_of"],
                "source": "local editorial simulator; AEM Headless adapter provided separately"})
    etag = service.etag_of(payload)
    headers = {"ETag": etag, "Cache-Control": CACHE_CONTROL}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return payload


@router.get("/delivery")
def delivery(request: Request, response: Response, segment: Segment = "all"):
    """Camada Publish: somente PUBLISHED, tokens de mercado resolvidos, ETag + Cache-Control (como no Dispatcher)."""
    return _delivery(request, response, segment, "plain")


@router.get("/model/{segment}.model.json")
def model_json(segment: Segment, request: Request, response: Response):
    return _delivery(request, response, segment, "model")


@router.post("/reset")
def reset(x_demo_role: str = Header("admin")):
    _role(x_demo_role, {"admin"})
    with connect() as con:
        n = seed.reset_and_seed(con)
    return {"reset": True, "content_items": n, "notice": "recriou o conteúdo editorial de demonstração"}
