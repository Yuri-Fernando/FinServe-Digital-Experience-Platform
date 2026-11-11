def test_overview_comes_from_real_snapshot(client):
    d = client.get("/api/market/overview").json()
    cards = d["cards"]
    assert {"selic_meta", "cdi_anual", "usd_brl", "inadimplencia_pf", "ipca_12m"} <= set(cards)
    assert all(c["kind"] in ("real", "derived") for c in cards.values())
    assert cards["ipca_12m"]["kind"] == "derived"
    assert 0 < cards["selic_meta"]["value"] < 50 and cards["selic_meta"]["as_of"] <= "2026-11-10"
    assert d["meta"]["kind"] == "real" and d["meta"]["data_retrieved_at"]


def test_series_endpoints(client):
    cat = client.get("/api/market/series").json()
    assert {s["id"] for s in cat} >= {"selic_meta", "ipca_mensal", "inadimplencia_total"}
    s = client.get("/api/market/series/selic_meta?days=90").json()
    assert s["points"] and all(p["date"] <= "2026-11-10" for p in s["points"])
    assert client.get("/api/market/series/nao_existe").status_code == 404
    assert client.get("/api/market/series/selic_meta?days=1").status_code == 422


def test_focus_has_selic_and_ipca(client):
    f = client.get("/api/market/focus").json()
    inds = {i["indicator"] for i in f["items"]}
    assert {"Selic", "IPCA"} <= inds and f["kind"] == "real"


def test_simulate_investment_uses_market_inputs(client):
    r = client.post("/api/market/simulate/investment", json={"amount": 10000, "months": 12}).json()
    mi = r["market_inputs"]
    assert mi["kind"] == "real" and not mi["overridden"]
    assert {p["product"] for p in r["products"]} == {"cdb", "lci_lca", "tesouro_selic", "poupanca"}
    assert r["assumptions"]


def test_simulate_investment_override_and_validation(client):
    r = client.post("/api/market/simulate/investment", json={"amount": 1000, "months": 12, "cdi_aa": 10, "selic_meta": 10}).json()
    assert r["market_inputs"]["overridden"] and r["market_inputs"]["cdi_aa"] == 10
    assert client.post("/api/market/simulate/investment", json={"amount": -5, "months": 12}).status_code == 422
    assert client.post("/api/market/simulate/investment", json={"amount": 100, "months": 500}).status_code == 422


def test_simulate_loan(client):
    r = client.post("/api/market/simulate/loan", json={"principal": 10000, "months": 12, "rate_monthly_pct": 2, "system": "price"}).json()
    assert r["summary"]["first_payment"] == 945.6
    assert "market_context" in r and "não a taxa média" in r["market_context"]["note"]
    assert client.post("/api/market/simulate/loan", json={"principal": 10000, "months": 12, "rate_monthly_pct": 2, "system": "xx"}).status_code == 422


def test_sync_requires_admin(client):
    assert client.post("/api/market/sync", headers={"x-demo-role": "author"}).status_code == 403


def test_tokens_formatted_pt_br(client):
    t = client.get("/api/market/tokens").json()
    assert t["values"]["selic_meta"].endswith("% a.a.") and "," in t["values"]["selic_meta"]
    assert t["values"]["usd_brl"].startswith("R$ ")
