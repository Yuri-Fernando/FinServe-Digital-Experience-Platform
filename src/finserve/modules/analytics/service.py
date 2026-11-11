from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta

from ... import config
from ...db import rows
from . import stats

SEGMENTS = ("all", "investidor", "credito", "jovem")

_WINDOW = """ FROM fact_experience_daily f JOIN dim_date d ON d.date_key=f.date_key JOIN campaigns c ON c.id=f.campaign_id
 WHERE d.day BETWEEN ? AND ? {seg}"""


def _seg_sql(segment: str):
    return ("", ()) if segment == "all" else (" AND c.audience IN (?,'all')", (segment,))


def _max_day(con) -> date:
    r = con.execute("SELECT MAX(day) FROM dim_date").fetchone()[0]
    return date.fromisoformat(r) if r else config.today()


def _summary(con, start: date, end: date, segment: str) -> dict:
    seg, sargs = _seg_sql(segment)
    r = rows(con, """SELECT SUM(impressions) impressions,SUM(clicks) clicks,SUM(leads) leads,SUM(approvals) approvals,
        SUM(sessions) sessions,ROUND(SUM(spend_brl),2) spend,ROUND(SUM(attributable_revenue_brl),2) revenue"""
             + _WINDOW.format(seg=seg), (start.isoformat(), end.isoformat(), *sargs))[0]
    s = {k: (v or 0) for k, v in r.items()}
    s["ctr_pct"] = round(s["clicks"] / max(s["impressions"], 1) * 100, 2)
    s["conversion_pct"] = round(s["leads"] / max(s["clicks"], 1) * 100, 2)
    s["approval_pct"] = round(s["approvals"] / max(s["leads"], 1) * 100, 2)
    s["cpl"] = round(s["spend"] / max(s["leads"], 1), 2)
    s["roas"] = round(s["revenue"] / max(s["spend"], 1), 2)
    return s


def _delta(cur: dict, prev: dict) -> dict:
    out = {}
    for k in ("sessions", "clicks", "leads", "revenue", "spend", "ctr_pct", "conversion_pct", "cpl", "roas"):
        out[k] = None if not prev.get(k) else round((cur[k] / prev[k] - 1) * 100, 1)
    return out


def web_vitals(con, start: date, end: date, segment: str) -> list[dict]:
    seg, sargs = _seg_sql(segment)
    data = rows(con, "SELECT f.lcp_ms lcp, f.inp_ms inp, f.cls_milli cls" + _WINDOW.format(seg=seg),
                (start.isoformat(), end.isoformat(), *sargs))
    out = []
    for key, name, unit, scale in (("lcp", "Largest Contentful Paint", "ms", 1), ("inp", "Interaction to Next Paint", "ms", 1),
                                   ("cls", "Cumulative Layout Shift", "", 1000)):
        vals = [r[key] / scale for r in data]
        if not vals:
            continue
        p75 = stats.percentile(vals, 75)
        good, poor = stats.CWV_THRESHOLDS[key]
        out.append({"id": key, "name": name, "unit": unit, "p75": round(p75, 3 if key == "cls" else 0),
                    "status": stats.cwv_status(key, p75), "good": good, "poor": poor, "samples": len(vals)})
    return out


def dashboard(con: sqlite3.Connection, days: int, segment: str) -> dict:
    end = _max_day(con)
    start = end - timedelta(days=days - 1)
    seg, sargs = _seg_sql(segment)
    args = (start.isoformat(), end.isoformat(), *sargs)
    summary = _summary(con, start, end, segment)
    prev_end, prev_start = start - timedelta(days=1), start - timedelta(days=days)
    has_prev = con.execute("SELECT COUNT(DISTINCT day) FROM dim_date WHERE day BETWEEN ? AND ?",
                           (prev_start.isoformat(), prev_end.isoformat())).fetchone()[0] == days
    delta = _delta(summary, _summary(con, prev_start, prev_end, segment)) if has_prev else {}
    daily = rows(con, """SELECT d.day date,SUM(f.impressions) impressions,SUM(f.clicks) clicks,SUM(f.leads) leads,
        SUM(f.approvals) approvals,SUM(f.sessions) sessions,ROUND(SUM(f.spend_brl),2) spend,
        ROUND(SUM(f.attributable_revenue_brl),2) revenue""" + _WINDOW.format(seg=seg) + " GROUP BY d.day ORDER BY d.day", args)
    channels = rows(con, """SELECT c.channel name,SUM(f.clicks) clicks,SUM(f.leads) leads,SUM(f.approvals) approvals,
        ROUND(SUM(f.spend_brl),2) spend""" + _WINDOW.format(seg=seg) + " GROUP BY c.channel ORDER BY leads DESC", args)
    campaigns = rows(con, """SELECT c.id,c.name,c.channel,c.product,c.audience,c.state,SUM(f.impressions) impressions,
        SUM(f.clicks) clicks,SUM(f.leads) leads,SUM(f.approvals) approvals,ROUND(SUM(f.spend_brl),2) spend,
        ROUND(SUM(f.attributable_revenue_brl),2) revenue""" + _WINDOW.format(seg=seg) + " GROUP BY c.id ORDER BY leads DESC", args)
    for c in campaigns:
        c["ctr_pct"] = round(c["clicks"] / max(c["impressions"], 1) * 100, 2)
        c["cpl"] = round(c["spend"] / max(c["leads"], 1), 2)
        c["roas"] = round(c["revenue"] / max(c["spend"], 1), 2)
    return {
        "days": days, "segment": segment, "window": {"start": start.isoformat(), "end": end.isoformat()},
        "summary": summary, "delta": delta, "previous_window_available": has_prev,
        "daily": daily, "channels": channels, "campaigns": campaigns,
        "web_vitals": web_vitals(con, start, end, segment),
        "kind": "synthetic",
        "disclaimer": "100% sintético: receita atribuída e Core Web Vitals são ilustrativos, não medições reais.",
    }


METRICS = {
    # métrica: (rótulo, direção ruim, função sobre a linha diária)
    "ctr": ("Taxa de clique", "down", lambda r: r["clicks"] / max(r["impressions"], 1)),
    "cpl": ("Custo por lead", "up", lambda r: r["spend"] / max(r["leads"], 1)),
    "lead_rate": ("Conversão clique→lead", "down", lambda r: r["leads"] / max(r["clicks"], 1)),
    "lcp_ms": ("LCP", "up", lambda r: float(r["lcp"])),
}


def anomalies(con: sqlite3.Connection, days: int = 30, lookback: int = 90, threshold: float = 3.5) -> dict:
    """Outliers robustos (z modificado) por campanha: os últimos `days` dias contra a mediana de `lookback` dias."""
    end = _max_day(con)
    base_start = end - timedelta(days=lookback - 1)
    flag_start = end - timedelta(days=days - 1)
    data = rows(con, """SELECT c.id cid,c.name campaign,d.day,f.impressions,f.clicks,f.leads,f.spend_brl spend,f.lcp_ms lcp
        FROM fact_experience_daily f JOIN dim_date d ON d.date_key=f.date_key JOIN campaigns c ON c.id=f.campaign_id
        WHERE d.day BETWEEN ? AND ? AND c.state!='paused' ORDER BY c.id,d.day""", (base_start.isoformat(), end.isoformat()))
    by_c: dict[int, list[dict]] = {}
    for r in data:
        by_c.setdefault(r["cid"], []).append(r)
    found = []
    for cid, series in by_c.items():
        for key, (label, bad, fn) in METRICS.items():
            vals = [fn(r) for r in series]
            zs = stats.modified_z(vals)
            med = sorted(vals)[len(vals) // 2]
            for r, v, z in zip(series, vals, zs):
                if r["day"] < flag_start.isoformat() or abs(z) < threshold:
                    continue
                direction = "up" if z > 0 else "down"
                found.append({
                    "campaign_id": cid, "campaign": r["campaign"], "date": r["day"], "metric": key, "metric_label": label,
                    "value": round(v, 4), "baseline_median": round(med, 4), "z": round(z, 2), "direction": direction,
                    "impact": "bad" if direction == bad else "good",
                    "severity": "critical" if abs(z) >= 6 and direction == bad else "warning",
                })
    found.sort(key=lambda a: -abs(a["z"]))
    return {"days": days, "lookback_days": lookback, "threshold": threshold, "method": "z modificado (mediana/MAD)",
            "items": found[:25], "kind": "derived"}


def pacing(con: sqlite3.Connection) -> dict:
    """Gasto do mês até agora × orçamento mensal; status por ritmo linear esperado."""
    end = _max_day(con)
    dim = calendar.monthrange(end.year, end.month)[1]
    month_start = end.replace(day=1)
    expected = end.day / dim
    out = []
    for c in rows(con, "SELECT id,name,channel,state,monthly_budget_brl budget FROM campaigns ORDER BY id"):
        spent = con.execute("SELECT COALESCE(SUM(f.spend_brl),0) FROM fact_experience_daily f JOIN dim_date d ON "
                            "d.date_key=f.date_key WHERE f.campaign_id=? AND d.day BETWEEN ? AND ?",
                            (c["id"], month_start.isoformat(), end.isoformat())).fetchone()[0]
        actual = spent / c["budget"] if c["budget"] else 0
        ratio = actual / expected if expected else 0
        status = "over" if ratio > 1.10 else "under" if ratio < 0.85 else "on_track"
        out.append({**c, "spent_mtd": round(spent, 2), "budget_used_pct": round(actual * 100, 1),
                    "expected_pct": round(expected * 100, 1), "projected_month_end": round(spent / end.day * dim, 2),
                    "status": status if c["state"] == "active" else "paused"})
    return {"as_of": end.isoformat(), "month_progress_pct": round(expected * 100, 1), "items": out, "kind": "synthetic"}


def experiment(con: sqlite3.Connection, key: str, mde_rel: float = 0.10) -> dict | None:
    t = rows(con, "SELECT t.*, c.name campaign FROM ab_tests t JOIN campaigns c ON c.id=t.campaign_id WHERE t.key=?", (key,))
    if not t:
        return None
    t = t[0]
    v = {r["variant"]: r for r in rows(con, "SELECT variant,visitors,conversions FROM ab_variants WHERE test_id=?", (t["id"],))}
    a, b = v["A"], v["B"]
    z = stats.two_proportion_ztest(a["conversions"], a["visitors"], b["conversions"], b["visitors"])
    need = stats.sample_size_per_variant(z["p_control"], mde_rel)
    enough = min(a["visitors"], b["visitors"]) >= need
    if z["significant"]:
        verdict = "winner" if z["diff"] > 0 else "loser"
    else:
        verdict = "inconclusive"
    return {
        "key": t["key"], "name": t["name"], "campaign": t["campaign"], "metric": t["metric"], "hypothesis": t["hypothesis"],
        "started_at": t["started_at"], "control": {**a, "rate_pct": round(z["p_control"] * 100, 2)},
        "variant": {**b, "rate_pct": round(z["p_variant"] * 100, 2)},
        "lift_pct": None if z["lift_pct"] is None else round(z["lift_pct"], 1), "z": round(z["z"], 3),
        "p_value": round(z["p_value"], 4), "ci95_pp": [round(z["ci95"][0] * 100, 2), round(z["ci95"][1] * 100, 2)],
        "significant": z["significant"], "verdict": verdict,
        "required_per_variant": need, "mde_rel_pct": mde_rel * 100, "enough_traffic": enough,
        "note": "Teste z bicaudal, α=5%. Resultado não significativo com tráfego insuficiente NÃO prova ausência de efeito.",
        "kind": "synthetic",
    }


def experiments(con: sqlite3.Connection) -> list[dict]:
    return [e for k in rows(con, "SELECT key FROM ab_tests ORDER BY id") if (e := experiment(con, k["key"]))]
