"""Persistência, sincronização e snapshots dos dados de mercado."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from ... import config
from ...db import one, rows
from . import bcb

SNAPSHOT_SGS = "bcb_sgs.json"
SNAPSHOT_FOCUS = "bcb_focus.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_catalog(con: sqlite3.Connection) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO market_series(id,sgs_code,name,unit,frequency,description,source_url) VALUES(?,?,?,?,?,?,?)",
        [(s["id"], s["sgs"], s["name"], s["unit"], s["frequency"], s["description"], s["url"]) for s in bcb.SERIES],
    )


def upsert_observations(con: sqlite3.Connection, series_id: str, obs: list[tuple[str, float]]) -> int:
    con.executemany(
        "INSERT OR REPLACE INTO market_observations(series_id,obs_date,value) VALUES(?,?,?)",
        [(series_id, d, v) for d, v in obs],
    )
    return len(obs)


def upsert_focus(con: sqlite3.Connection, items: list[dict]) -> int:
    con.executemany(
        """INSERT OR REPLACE INTO market_expectations
           (indicator,reference_year,obs_date,median,mean,std,min,max,respondents) VALUES(?,?,?,?,?,?,?,?,?)""",
        [(i["indicator"], i["reference_year"], i["date"], i["median"], i["mean"], i["std"], i["min"], i["max"],
          i["respondents"]) for i in items],
    )
    return len(items)


def log(con, source, series_id, n, status, detail=""):
    con.execute(
        "INSERT INTO market_sync_log(at,source,series_id,rows,status,detail) VALUES(?,?,?,?,?,?)",
        (_now(), source, series_id, n, status, detail[:300]),
    )


def collect(fetch: bcb.Fetcher, today: date, series_ids: list[str] | None = None, focus: bool = True):
    """Consulta a API (ou um `fetch` injetado) e devolve dados + erros, sem tocar no banco."""
    data: dict[str, list[tuple[str, float]]] = {}
    errors: dict[str, str] = {}
    for s in bcb.SERIES:
        if series_ids and s["id"] not in series_ids:
            continue
        try:
            url = bcb.sgs_url(s["sgs"], bcb.lookback_start(s["frequency"], today), today)
            data[s["id"]] = bcb.parse_sgs(fetch(url), today)
        except bcb.BcbError as exc:
            errors[s["id"]] = str(exc)
    focus_rows: list[dict] = []
    if focus:
        from datetime import timedelta

        for ind in bcb.FOCUS_INDICATORS:
            try:
                focus_rows += bcb.parse_focus(fetch(bcb.focus_url(ind, today - timedelta(days=45))))
            except bcb.BcbError as exc:
                errors[f"focus:{ind}"] = str(exc)
    return data, focus_rows, errors


def sync(con: sqlite3.Connection, fetch: bcb.Fetcher = bcb.fetch_json, today: date | None = None,
         series_ids: list[str] | None = None, focus: bool = True) -> dict:
    today = today or config.today()
    ensure_catalog(con)
    data, focus_rows, errors = collect(fetch, today, series_ids, focus)
    summary = {"series": {}, "focus_rows": 0, "errors": errors, "source": "bcb-live"}
    for sid, obs in data.items():
        n = upsert_observations(con, sid, obs)
        summary["series"][sid] = n
        log(con, "bcb-live", sid, n, "ok")
    if focus_rows:
        summary["focus_rows"] = upsert_focus(con, focus_rows)
        log(con, "bcb-live", "focus", summary["focus_rows"], "ok")
    for key, msg in errors.items():
        log(con, "bcb-live", key, 0, "error", msg)
    return summary


def write_snapshot(fetch: bcb.Fetcher = bcb.fetch_json, today: date | None = None, directory: Path | None = None) -> dict:
    """Baixa dados reais e grava snapshots versionáveis (permitem rodar offline)."""
    today = today or config.today()
    directory = directory or config.snapshot_dir()
    directory.mkdir(parents=True, exist_ok=True)
    data, focus_rows, errors = collect(fetch, today)
    if errors:
        raise bcb.BcbError(f"snapshot incompleto, nada gravado: {errors}")
    retrieved = _now()
    sgs = {
        "retrieved_at": retrieved,
        "source": "Banco Central do Brasil — SGS (api.bcb.gov.br)",
        "note": "Observações com data posterior à coleta foram descartadas.",
        "series": {
            sid: {"sgs": bcb.SERIES_BY_ID[sid]["sgs"], "name": bcb.SERIES_BY_ID[sid]["name"],
                  "unit": bcb.SERIES_BY_ID[sid]["unit"], "observations": [[d, v] for d, v in obs]}
            for sid, obs in data.items()
        },
    }
    (directory / SNAPSHOT_SGS).write_text(json.dumps(sgs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    foc = {"retrieved_at": retrieved, "source": "Banco Central do Brasil — Expectativas de Mercado (Focus/Olinda)",
           "rows": focus_rows}
    (directory / SNAPSHOT_FOCUS).write_text(json.dumps(foc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"retrieved_at": retrieved, "series": {k: len(v) for k, v in data.items()}, "focus_rows": len(focus_rows)}


def load_snapshot(con: sqlite3.Connection, directory: Path | None = None) -> dict | None:
    directory = directory or config.snapshot_dir()
    p = directory / SNAPSHOT_SGS
    if not p.exists():
        return None
    snap = json.loads(p.read_text(encoding="utf-8"))
    ensure_catalog(con)
    summary = {}
    for sid, s in snap["series"].items():
        n = upsert_observations(con, sid, [(d, float(v)) for d, v in s["observations"]])
        summary[sid] = n
        log(con, f"snapshot@{snap['retrieved_at']}", sid, n, "ok")
    fp = directory / SNAPSHOT_FOCUS
    if fp.exists():
        foc = json.loads(fp.read_text(encoding="utf-8"))
        upsert_focus(con, foc["rows"])
    return {"retrieved_at": snap["retrieved_at"], "series": summary}


def seed(con: sqlite3.Connection) -> None:
    ensure_catalog(con)
    n = con.execute("SELECT COUNT(*) FROM market_observations").fetchone()[0]
    if n == 0:
        load_snapshot(con)


def last_sync(con: sqlite3.Connection) -> dict | None:
    return one(con, "SELECT at,source FROM market_sync_log WHERE status='ok' ORDER BY id DESC LIMIT 1")


def snapshot_retrieved_at(con: sqlite3.Connection) -> str | None:
    r = one(con, "SELECT source FROM market_sync_log WHERE status='ok' ORDER BY id DESC LIMIT 1")
    if r and r["source"].startswith("snapshot@"):
        return r["source"].split("@", 1)[1]
    r = last_sync(con)
    return r["at"] if r else None


def latest(con: sqlite3.Connection, series_id: str, today: date | None = None) -> dict | None:
    today = today or config.today()
    return one(con, "SELECT obs_date AS date, value FROM market_observations WHERE series_id=? AND obs_date<=? "
                    "ORDER BY obs_date DESC LIMIT 1", (series_id, today.isoformat()))


def window(con: sqlite3.Connection, series_id: str, days: int, today: date | None = None) -> list[dict]:
    from datetime import timedelta

    today = today or config.today()
    start = (today - timedelta(days=days)).isoformat()
    return rows(con, "SELECT obs_date AS date, value FROM market_observations WHERE series_id=? AND obs_date>=? "
                     "AND obs_date<=? ORDER BY obs_date", (series_id, start, today.isoformat()))
