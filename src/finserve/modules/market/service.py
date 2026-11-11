from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from ... import config
from ...db import rows
from . import store
from .calculators import accumulate_pct

STALE_AFTER_DAYS = {"daily": 7, "monthly": 75}


def _month_index(iso: str) -> int:
    return int(iso[:4]) * 12 + int(iso[5:7])


def ipca_12m(con: sqlite3.Connection, today: date, back_months: int = 0) -> dict | None:
    """IPCA acumulado em 12 meses (composto), exigindo 12 meses consecutivos; senão None (nunca estima)."""
    obs = rows(con, "SELECT obs_date AS date, value FROM market_observations WHERE series_id='ipca_mensal' "
                    "AND obs_date<=? ORDER BY obs_date DESC LIMIT ?", (today.isoformat(), 12 + back_months))
    obs = obs[back_months:]
    if len(obs) < 12:
        return None
    idx = [_month_index(o["date"]) for o in obs]
    if any(idx[i] - idx[i + 1] != 1 for i in range(11)):
        return None
    return {"date": obs[0]["date"], "value": round(accumulate_pct([o["value"] for o in obs]), 2)}


def _spark(con, sid, days, today):
    return store.window(con, sid, days, today)


def _stale(freq: str, as_of: str, today: date) -> bool:
    return (today - date.fromisoformat(as_of)).days > STALE_AFTER_DAYS[freq]


def _change_abs(con, sid, today, days_back):
    cur = store.latest(con, sid, today)
    if not cur:
        return None, None
    ref_day = (date.fromisoformat(cur["date"]) - timedelta(days=days_back)).isoformat()
    ref = con.execute("SELECT value FROM market_observations WHERE series_id=? AND obs_date<=? "
                      "ORDER BY obs_date DESC LIMIT 1", (sid, ref_day)).fetchone()
    return cur, (None if ref is None else ref[0])


def overview(con: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or config.today()
    cards: dict[str, dict] = {}

    def add(card_id, label, sid, unit, freq, change_days, change_kind, spark_days):
        cur, ref = _change_abs(con, sid, today, change_days)
        if not cur:
            return
        change = None
        if ref is not None:
            change = round(cur["value"] - ref, 4) if change_kind == "pp" else round((cur["value"] / ref - 1) * 100, 2)
        cards[card_id] = {
            "id": card_id, "label": label, "series": sid, "value": cur["value"], "unit": unit, "as_of": cur["date"],
            "change": change, "change_kind": change_kind,
            "change_label": f"vs {change_days} dias" if change_days < 60 or change_days == 90 else "vs mês anterior",
            "spark": _spark(con, sid, spark_days, today), "kind": "real", "stale": _stale(freq, cur["date"], today),
        }

    add("selic_meta", "Meta Selic", "selic_meta", "% a.a.", "daily", 90, "pp", 365)
    add("cdi_anual", "CDI (a.a.)", "cdi_anual", "% a.a.", "daily", 90, "pp", 365)
    add("usd_brl", "Dólar comercial", "usd_brl", "R$", "daily", 30, "pct", 365)
    add("inadimplencia_pf", "Inadimplência PF (>90d)", "inadimplencia_pf", "%", "monthly", 31, "pp", 1100)

    now12 = ipca_12m(con, today)
    if now12:
        prev = ipca_12m(con, today, back_months=3)
        cards["ipca_12m"] = {
            "id": "ipca_12m", "label": "IPCA 12 meses", "series": "ipca_mensal", "value": now12["value"], "unit": "%",
            "as_of": now12["date"], "change": None if not prev else round(now12["value"] - prev["value"], 2),
            "change_kind": "pp", "change_label": "vs 3 meses antes", "spark": [], "kind": "derived",
            "stale": _stale("monthly", now12["date"], today),
        }
    return {
        "cards": cards,
        "meta": {"today": today.isoformat(), "data_retrieved_at": store.snapshot_retrieved_at(con),
                 "source": "Banco Central do Brasil (SGS)", "kind": "real",
                 "notice": "Dados oficiais; podem estar defasados se a última coleta não for recente. Use Sincronizar."},
    }


def series(con: sqlite3.Connection, series_id: str, days: int, today: date | None = None) -> dict | None:
    meta = con.execute("SELECT id,sgs_code,name,unit,frequency,description,source_url FROM market_series WHERE id=?",
                       (series_id,)).fetchone()
    if not meta:
        return None
    pts = store.window(con, series_id, days, today)
    return {**dict(meta), "points": pts, "kind": "real", "count": len(pts)}


def catalog(con: sqlite3.Connection, today: date | None = None) -> list[dict]:
    out = []
    for m in rows(con, "SELECT id,sgs_code,name,unit,frequency,description,source_url FROM market_series ORDER BY id"):
        out.append({**m, "latest": store.latest(con, m["id"], today)})
    return out


def focus(con: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or config.today()
    years = [str(today.year), str(today.year + 1)]
    items = []
    for ind in ("Selic", "IPCA", "Câmbio", "PIB Total"):
        r = con.execute("SELECT MAX(obs_date) FROM market_expectations WHERE indicator=? AND obs_date<=?",
                        (ind, today.isoformat())).fetchone()
        if not r or not r[0]:
            continue
        for row in rows(con, "SELECT indicator,reference_year,obs_date,median,mean,min,max,respondents "
                             "FROM market_expectations WHERE indicator=? AND obs_date=? AND reference_year IN (?,?) "
                             "ORDER BY reference_year", (ind, r[0], *years)):
            items.append(row)
    as_of = max((i["obs_date"] for i in items), default=None)
    return {"as_of": as_of, "items": items, "kind": "real",
            "source": "BCB — Expectativas de Mercado (Focus)",
            "note": "Mediana das expectativas do mercado, não projeção do Banco Central."}


def market_inputs(con: sqlite3.Connection, today: date | None = None) -> dict | None:
    today = today or config.today()
    cdi, selic = store.latest(con, "cdi_anual", today), store.latest(con, "selic_meta", today)
    if not cdi or not selic:
        return None
    ip = ipca_12m(con, today)
    return {"cdi_aa": cdi["value"], "selic_meta": selic["value"], "ipca_12m": ip["value"] if ip else None,
            "as_of": cdi["date"], "kind": "real"}


def _pt(v: float, suffix: str) -> str:
    return f"{v:.2f}".replace(".", ",") + suffix


def tokens(con: sqlite3.Connection, today: date | None = None) -> dict:
    """Tokens usados pelo módulo experience (ex.: {{selic_meta}}) — valores reais já formatados em pt-BR."""
    today = today or config.today()
    mi = market_inputs(con, today)
    ip = ipca_12m(con, today)
    usd = store.latest(con, "usd_brl", today)
    out: dict[str, str] = {}
    if mi:
        out["selic_meta"] = _pt(mi["selic_meta"], "% a.a.")
        out["cdi_anual"] = _pt(mi["cdi_aa"], "% a.a.")
    if ip:
        out["ipca_12m"] = _pt(ip["value"], "%")
    if usd:
        out["usd_brl"] = "R$ " + f"{usd['value']:.2f}".replace(".", ",")
    return {"values": out, "as_of": mi["as_of"] if mi else None}
