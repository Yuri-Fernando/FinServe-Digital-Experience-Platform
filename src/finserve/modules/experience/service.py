from __future__ import annotations

import hashlib
import json
import re
import sqlite3

from ... import audit
from ...db import rows

SEGMENTS = ("all", "investidor", "credito", "jovem")
ALLOWED_TOKENS = {"selic_meta", "cdi_anual", "ipca_12m", "usd_brl"}
_TOKEN = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}")
TEXT_FIELDS = ("eyebrow", "title", "body", "cta_label", "cta_url")
EDITABLE = ("eyebrow", "title", "body", "cta_label", "cta_url", "segment")

TRANSITIONS = {
    "submit": ("DRAFT", "IN_REVIEW", {"author"}),
    "approve": ("IN_REVIEW", "APPROVED", {"reviewer"}),
    "reject": ("IN_REVIEW", "DRAFT", {"reviewer"}),
    "publish": ("APPROVED", "PUBLISHED", {"publisher"}),
    "archive": ("PUBLISHED", "ARCHIVED", {"publisher"}),
}


class ContentError(Exception):
    def __init__(self, status: int, detail):
        self.status, self.detail = status, detail


def tokens_in(item: dict) -> set[str]:
    return {t for f in TEXT_FIELDS for t in _TOKEN.findall(str(item.get(f, "")))}


def validate_item(item: dict) -> None:
    url = item["cta_url"]
    if not url.startswith("/") or url.startswith("//") or "\\" in url:
        raise ContentError(422, "A URL da CTA deve ser caminho interno relativo, começando com /")
    unknown = tokens_in(item) - ALLOWED_TOKENS
    if unknown:
        raise ContentError(422, f"Tokens desconhecidos: {sorted(unknown)}. Permitidos: {sorted(ALLOWED_TOKENS)}")


def resolve_text(text: str, values: dict[str, str]) -> str:
    return _TOKEN.sub(lambda m: values.get(m.group(1), "—"), text)


def resolve_item(item: dict, values: dict[str, str]) -> dict:
    out = dict(item)
    for f in TEXT_FIELDS:
        out[f] = resolve_text(str(item[f]), values)
    out["tokens_used"] = sorted(tokens_in(item))
    return out


def etag_of(payload) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return '"' + hashlib.sha256(raw).hexdigest()[:20] + '"'


def published(con: sqlite3.Connection, segment: str) -> list[dict]:
    return rows(con, "SELECT key,component,eyebrow,title,body,cta_label,cta_url,segment,version,published_at FROM content_items "
                     "WHERE status='PUBLISHED' AND segment IN ('all',?) ORDER BY CASE WHEN segment=? THEN 0 ELSE 1 END,id",
                (segment, segment))


def aem_model(segment: str, items: list[dict], data_as_of: str | None) -> dict:
    """Formato inspirado no Sling Model Exporter do AEM (`.model.json`): :type, :items, :itemsOrder."""
    return {
        ":type": "finserve/components/page", ":path": f"/content/finserve/{segment}",
        ":itemsOrder": [i["key"] for i in items],
        ":items": {i["key"]: {
            ":type": f"finserve/components/{i['component']}", "eyebrow": i["eyebrow"], "title": i["title"],
            "description": i["body"], "ctaLabel": i["cta_label"], "ctaUrl": i["cta_url"], "segment": i["segment"],
            "version": i["version"], "publishedAt": i["published_at"], "tokensUsed": i["tokens_used"]} for i in items},
        "dataAsOf": data_as_of,
        "note": "Exportação local inspirada no .model.json do AEM; não é gerada por uma instância AEM.",
    }


def snapshot(con, item_id: int) -> dict:
    return dict(con.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone())


def add_revision(con, item: dict, actor: str, reason: str, now: str) -> None:
    con.execute("INSERT INTO content_revisions(content_id,version,snapshot,actor,reason,created_at) VALUES(?,?,?,?,?,?)",
                (item["id"], item["version"], json.dumps(item, ensure_ascii=False), actor, reason, now))


def diff_versions(con, item_id: int, v_from: int, v_to: int) -> dict:
    snaps = {}
    for v in (v_from, v_to):
        r = con.execute("SELECT snapshot FROM content_revisions WHERE content_id=? AND version=?", (item_id, v)).fetchone()
        if not r:
            raise ContentError(404, f"Versão {v} não encontrada")
        snaps[v] = json.loads(r[0])
    changes = [{"field": f, "from": snaps[v_from].get(f), "to": snaps[v_to].get(f)}
               for f in EDITABLE if snaps[v_from].get(f) != snaps[v_to].get(f)]
    return {"content_id": item_id, "from_version": v_from, "to_version": v_to, "changes": changes}


def stats(con) -> dict:
    by = {r["status"]: r["n"] for r in rows(con, "SELECT status, COUNT(*) n FROM content_items GROUP BY status")}
    for s in ("DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", "ARCHIVED"):
        by.setdefault(s, 0)
    return {"total": sum(by.values()), "by_status": by, "pending_review": by["IN_REVIEW"]}


def record(con, item_id, actor, action, frm, to, notes, now):
    audit.record(con, module="experience", entity="content", entity_id=item_id, actor=actor, action=action,
                 from_status=frm, to_status=to, notes=notes, at=now)
