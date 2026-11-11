from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config


@contextmanager
def connect():
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=10000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def rows(con: sqlite3.Connection, sql: str, params=()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def one(con: sqlite3.Connection, sql: str, params=()) -> dict | None:
    r = con.execute(sql, params).fetchone()
    return dict(r) if r else None


def apply_schema(con: sqlite3.Connection, sql_path: Path) -> None:
    con.executescript(Path(sql_path).read_text(encoding="utf-8"))
