import pytest

from finserve.modules.experience import compliance


def _item(client, key):
    return next(x for x in client.get("/api/experience/content").json() if x["key"] == key)


def _edit_body(item, **over):
    body = {k: item[k] for k in ("eyebrow", "title", "body", "cta_label", "cta_url", "segment")}
    return {**body, **over, "version": item["version"]}


def test_published_only_in_delivery(client):
    r = client.get("/api/experience/delivery?segment=credito").json()
    keys = [c["key"] for c in r["content"]]
    assert "hero-credito" in keys and "banner-cartao" not in keys
    assert all(c["segment"] in ("credito", "all") for c in r["content"])


def test_workflow_roles_versioning_and_publication(client):
    old = _item(client, "banner-cartao")
    h = {"x-demo-role": "author"}
    put = client.put(f"/api/experience/content/{old['id']}", headers=h, json=_edit_body(old, title="Cartão com benefícios sob medida"))
    assert put.status_code == 200 and put.json()["version"] == 2
    assert client.put(f"/api/experience/content/{old['id']}", headers=h, json={**_edit_body(old), "version": 1}).status_code == 409
    url = f"/api/experience/content/{old['id']}/transition"
    assert client.post(url, headers={"x-demo-role": "publisher"}, json={"action": "publish"}).status_code == 409
    assert client.post(url, headers=h, json={"action": "submit"}).status_code == 200
    assert client.post(url, headers=h, json={"action": "approve"}).status_code == 403
    assert client.post(url, headers={"x-demo-role": "reviewer"}, json={"action": "approve"}).status_code == 200
    assert client.post(url, headers={"x-demo-role": "publisher"}, json={"action": "publish"}).status_code == 200
    assert "banner-cartao" in [c["key"] for c in client.get("/api/experience/delivery?segment=jovem").json()["content"]]
    detail = client.get(f"/api/experience/content/{old['id']}").json()
    assert len(detail["revisions"]) == 2 and detail["audit"][0]["action"] == "publish"


def test_unsafe_cta_denied(client):
    body = {"key": "test-external", "component": "promobanner", "eyebrow": "Test", "title": "Solução de crédito",
            "body": "Descrição para teste", "cta_label": "Ver", "cta_url": "https://evil.example", "segment": "all"}
    assert client.post("/api/experience/content", json=body).status_code == 422
    assert client.post("/api/experience/content", json={**body, "cta_url": "//evil.example"}).status_code == 422
    assert client.post("/api/experience/content", json={**body, "cta_url": "/educacao"}).status_code == 201


def test_unknown_token_rejected(client):
    body = {"key": "tok-bad", "component": "ratecard", "eyebrow": "x", "title": "Valor {{segredo}}", "body": "Texto qualquer",
            "cta_label": "Ver", "cta_url": "/x", "segment": "all"}
    r = client.post("/api/experience/content", json=body)
    assert r.status_code == 422 and "segredo" in r.json()["detail"]


def test_market_tokens_resolved_in_delivery(client):
    items = client.get("/api/experience/delivery").json()["content"]
    card = next(i for i in items if i["key"] == "ratecard-mercado")
    assert "{{" not in card["title"] and "% a.a." in card["title"]
    assert card["tokens_used"] == ["cdi_anual", "ipca_12m", "selic_meta"]


def test_tokens_degrade_when_market_disabled(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from finserve.app import create_app

    with TestClient(create_app(["platform", "experience"])) as c:
        card = next(i for i in c.get("/api/experience/delivery").json()["content"] if i["key"] == "ratecard-mercado")
        assert card["title"] == "Selic hoje: —"  # nunca mostra token cru nem valor inventado


def test_etag_and_304(client):
    r1 = client.get("/api/experience/delivery?segment=investidor")
    etag = r1.headers["etag"]
    assert "max-age" in r1.headers["cache-control"]
    r2 = client.get("/api/experience/delivery?segment=investidor", headers={"if-none-match": etag})
    assert r2.status_code == 304
    item = _item(client, "banner-invest")  # APPROVED -> publicar muda o payload
    client.post(f"/api/experience/content/{item['id']}/transition", headers={"x-demo-role": "publisher"}, json={"action": "publish"})
    r3 = client.get("/api/experience/delivery?segment=investidor", headers={"if-none-match": etag})
    assert r3.status_code == 200 and r3.headers["etag"] != etag


def test_aem_style_model_json(client):
    m = client.get("/api/experience/model/jovem.model.json").json()
    assert m[":type"] == "finserve/components/page" and m[":itemsOrder"]
    first = m[":items"][m[":itemsOrder"][0]]
    assert first[":type"].startswith("finserve/components/") and "ctaUrl" in first and "description" in first
    assert client.get("/api/experience/model/xx.model.json").status_code == 422


def test_revision_diff(client):
    old = _item(client, "banner-cartao")
    client.put(f"/api/experience/content/{old['id']}", headers={"x-demo-role": "author"}, json=_edit_body(old, title="Novo título aqui"))
    d = client.get(f"/api/experience/content/{old['id']}/diff?from_version=1&to_version=2").json()
    assert [c["field"] for c in d["changes"]] == ["title"] and d["changes"][0]["to"] == "Novo título aqui"
    assert client.get(f"/api/experience/content/{old['id']}/diff?from_version=1&to_version=9").status_code == 404


@pytest.mark.parametrize("text,rule", [
    ("Retorno garantido de 20% ao ano", "CMP001"), ("Aprovação imediata para todos", "CMP002"),
    ("Fale com joao@banco.com", "CMP003"), ("Corra, só hoje!", "CMP004"), ("O melhor banco do país", "CMP005"),
    ("Sua rentabilidade cresce todo mês", "CMP006"), ("Juros de 1,5% ao mês", "CMP007"),
])
def test_each_compliance_rule_fires(text, rule):
    r = compliance.check({"title": text, "body": "texto neutro aqui"})
    assert rule in {i["rule_id"] for i in r["issues"]}


def test_compliance_clean_and_disclaimer_suppression():
    assert compliance.check({"title": "Conheça nossas opções", "body": "Compare alternativas com clareza."})["issues"] == []
    ok = compliance.check({"title": "Rentabilidade em simulação", "body": "Rentabilidade passada não garante resultado futuro."})
    assert "CMP006" not in {i["rule_id"] for i in ok["issues"]}
    cet = compliance.check({"title": "Juros de 1,5% ao mês", "body": "Veja o CET na simulação."})
    assert "CMP007" not in {i["rule_id"] for i in cet["issues"]}


def test_compliance_is_accent_and_case_insensitive():
    assert not compliance.check({"title": "RETORNO GARANTIDO"})["passed"]
    assert not compliance.check({"title": "aprovação garantida"})["passed"]


def test_compliance_engine_fail_safe(tmp_path):
    bad = tmp_path / "rules.yaml"
    bad.write_text("rules:\n  - id: X\n    name: n\n", encoding="utf-8")
    r = compliance.check({"title": "qualquer coisa"}, path=str(bad))
    assert not r["passed"] and r["issues"][0]["rule_id"] == "ENGINE_ERROR"  # erro => bloqueia


def test_compliance_blocks_submit_and_records_warnings(client):
    h = {"x-demo-role": "author"}
    base = {"component": "promobanner", "eyebrow": "Novo", "cta_label": "Ver", "cta_url": "/x", "segment": "all"}
    bad = client.post("/api/experience/content", headers=h, json={**base, "key": "bad-copy", "title": "Retorno garantido hoje", "body": "texto qualquer"}).json()
    r = client.post(f"/api/experience/content/{bad['id']}/transition", headers=h, json={"action": "submit"})
    assert r.status_code == 422 and r.json()["detail"]["compliance"]["blocking"] >= 1
    assert client.get(f"/api/experience/content/{bad['id']}").json()["content"]["status"] == "DRAFT"
    warn = client.post("/api/experience/content", headers=h, json={**base, "key": "warn-copy", "title": "O melhor jeito de planejar", "body": "texto qualquer"}).json()
    assert client.post(f"/api/experience/content/{warn['id']}/transition", headers=h, json={"action": "submit"}).status_code == 200
    audit = client.get(f"/api/experience/content/{warn['id']}").json()["audit"]
    assert "CMP005" in audit[0]["notes"]


def test_compliance_endpoints(client):
    assert client.get("/api/experience/compliance/rules").json()["rules"]
    r = client.post("/api/experience/compliance/check", json={"title": "Sem risco algum"}).json()
    assert not r["passed"]


def test_seed_content_passes_compliance(client):
    for item in client.get("/api/experience/content").json():
        assert compliance.check(item)["passed"], item["key"]


def test_stats_and_reset(client):
    assert client.get("/api/experience/stats").json()["pending_review"] == 1
    assert client.post("/api/experience/reset", headers={"x-demo-role": "author"}).status_code == 403
    assert client.post("/api/experience/reset", headers={"x-demo-role": "admin"}).json()["reset"]
