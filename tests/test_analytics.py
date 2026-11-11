from datetime import date, timedelta

from finserve.db import connect
from finserve.modules.analytics.seed import INJECTED_ANOMALIES

END = date(2026, 11, 10)


def test_dashboard_shape_and_funnel_invariants(client):
    d = client.get("/api/analytics/dashboard", params={"days": 30, "segment": "credito"}).json()
    s = d["summary"]
    assert s["impressions"] > 0 and s["approvals"] <= s["leads"] <= s["clicks"] <= s["impressions"]
    assert len(d["daily"]) == 30 and d["kind"] == "synthetic"
    assert all(c["audience"] in ("credito", "all") for c in d["campaigns"])
    assert d["window"]["end"] == END.isoformat()


def test_invalid_filters_rejected(client):
    assert client.get("/api/analytics/dashboard?days=500").status_code == 422
    assert client.get("/api/analytics/dashboard?segment=x").status_code == 422


def test_previous_window_delta_only_when_complete(client):
    d30 = client.get("/api/analytics/dashboard?days=30").json()
    assert d30["previous_window_available"] and d30["delta"]["leads"] is not None
    d90 = client.get("/api/analytics/dashboard?days=90").json()
    assert not d90["previous_window_available"] and d90["delta"] == {}  # 180 dias não existem: nunca inventar delta


def test_web_vitals_p75_and_status(client):
    v = {x["id"]: x for x in client.get("/api/analytics/dashboard?days=30").json()["web_vitals"]}
    assert set(v) == {"lcp", "inp", "cls"}
    assert v["lcp"]["status"] in ("good", "needs-improvement", "poor") and v["cls"]["p75"] < 1


def test_detector_finds_every_injected_anomaly(client):
    items = client.get("/api/analytics/anomalies?days=30").json()["items"]
    found = {(a["campaign_id"], a["date"], a["metric"]) for a in items if a["impact"] == "bad"}
    for cid, idx, metric, _ in INJECTED_ANOMALIES:
        day = (END - timedelta(days=119 - idx)).isoformat()
        assert (cid, day, metric) in found, f"anomalia injetada não detectada: {cid} {day} {metric}"


def test_detector_has_low_false_positive_rate(client):
    items = client.get("/api/analytics/anomalies?days=30").json()["items"]
    injected = {(c, (END - timedelta(days=119 - i)).isoformat()) for c, i, *_ in INJECTED_ANOMALIES}
    spurious = [a for a in items if (a["campaign_id"], a["date"]) not in injected]
    assert len(spurious) <= 3, spurious


def test_pacing_statuses(client):
    items = {i["id"]: i for i in client.get("/api/analytics/pacing").json()["items"]}
    assert items[8]["status"] == "paused"
    assert items[3]["status"] == "over"   # orçamento 20% abaixo do ritmo (+ pico de custo injetado)
    assert items[6]["status"] == "under"  # orçamento 25% acima do ritmo
    assert all(0 <= i["budget_used_pct"] for i in items.values())


def test_experiments_verdicts(client):
    e = {x["key"]: x for x in client.get("/api/analytics/experiments").json()["items"]}
    assert e["hero-cta-copy"]["verdict"] == "winner" and e["hero-cta-copy"]["significant"]
    assert e["banner-layout"]["verdict"] == "inconclusive"
    assert e["form-curto"]["verdict"] == "inconclusive" and not e["form-curto"]["enough_traffic"]
    assert client.get("/api/analytics/experiments/nope").status_code == 404


def test_csv_export(client):
    r = client.get("/api/analytics/export.csv?days=30")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.lstrip("﻿").strip().splitlines()
    assert lines[0].startswith('"name";"channel"') and len(lines) == 9


def test_data_quality_and_determinism(client):
    with connect() as con:
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute("SELECT COUNT(*) FROM fact_experience_daily").fetchone()[0] == 960
        assert con.execute("SELECT COUNT(*) FROM fact_experience_daily WHERE approvals>leads OR leads>clicks OR clicks>impressions").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM campaigns WHERE monthly_budget_brl<=0").fetchone()[0] == 0
        total = con.execute("SELECT SUM(impressions) FROM fact_experience_daily").fetchone()[0]
    from finserve.modules.analytics.seed import reset_and_seed
    with connect() as con:
        reset_and_seed(con)
        assert con.execute("SELECT SUM(impressions) FROM fact_experience_daily").fetchone()[0] == total  # seed fixa
