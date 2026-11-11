"""Trilha de auditoria genérica, compartilhada por todos os módulos."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def record(
    con: sqlite3.Connection,
    *,
    module: str,
    entity: str,
    entity_id: int | None,
    actor: str,
    action: str,
    from_status: str | None = None,
    to_status: str | None = None,
    notes: str = "",
    at: str | None = None,
) -> None:
    con.execute(
        """INSERT INTO audit_events(module,entity,entity_id,actor,action,from_status,to_status,notes,occurred_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (module, entity, entity_id, actor, action, from_status, to_status, notes, at or utcnow()),
    )
