import sys
import textwrap

import pytest
from fastapi.testclient import TestClient

from finserve import cli, dashkit, registry
from finserve.app import create_app


def test_health_and_modules(client):
    h = client.get("/api/platform/health").json()
    assert h["status"] == "ok" and set(h["modules"]) >= {"platform", "experience", "analytics", "market"}
    mods = {m["name"]: m for m in client.get("/api/platform/modules").json()}
    assert mods["experience"]["requires"] == ["platform"] and "market" in mods["experience"]["optional"]


def test_provenance_separates_real_synthetic_derived(client):
    ds = client.get("/api/platform/provenance").json()["datasets"]
    kinds = {d["kind"] for d in ds}
    assert kinds == {"real", "synthetic", "derived"}
    real = [d for d in ds if d["kind"] == "real"]
    assert real and all(d["source_url"] and d["retrieved_at"] and d["rows"] for d in real)
    assert all(d["source"] for d in ds)


def test_dictionary_covers_declared_tables(client):
    d = client.get("/api/platform/dictionary").json()
    assert {"audit_events", "content_items", "fact_experience_daily", "market_observations"} <= set(d)
    assert d["market_observations"]["module"] == "market"


def test_all_dashboard_specs_are_valid(client):
    for item in client.get("/api/platform/dashboards").json():
        spec = client.get(f"/api/platform/dashboards/{item['id']}").json()
        dashkit.validate_spec(spec)
    assert client.get("/api/platform/dashboards/nope").status_code == 404


def test_dashboards_sorted_for_nav(client):
    orders = [d["nav"].get("order", 99) for d in client.get("/api/platform/dashboards").json()]
    assert orders == sorted(orders)


@pytest.mark.parametrize("mutate,msg", [
    (lambda s: s["widgets"].append({"type": "magic"}), "tipo desconhecido"),
    (lambda s: s["widgets"].append({"type": "table", "path": "x"}), "faltam campos"),
    (lambda s: s["widgets"].append({"type": "list", "path": "x", "primary": "y", "source": "zzz"}), "inexistente"),
    (lambda s: s["sources"].__setitem__("main", {"url": "http://x"}), "/api/"),
    (lambda s: s["sources"]["main"].__setitem__("params", ["nofilter"]), "sem filtro"),
    (lambda s: s["widgets"].append({"type": "calculator", "calc": "bitcoin"}), "calculadora"),
    (lambda s: s["widgets"].append({"type": "bars", "path": "x", "label": "a", "value": "b", "format": "xx"}), "formato"),
])
def test_spec_validator_rejects_bad_specs(mutate, msg):
    spec = {"id": "t", "title": "T", "sources": {"main": {"url": "/api/x"}}, "filters": [], "widgets": []}
    mutate(spec)
    with pytest.raises(dashkit.SpecError, match=msg):
        dashkit.validate_spec(spec)


def test_module_subset_does_not_expose_disabled_routes():
    with TestClient(create_app(["market"])) as c:  # platform entra sozinho
        assert c.get("/api/platform/health").json()["modules"] == ["platform", "market"]
        assert c.get("/api/experience/content").status_code == 404
        assert c.get("/api/market/overview").status_code == 200


def test_missing_dependency_and_cycle_errors():
    broken = registry.Module("x", "X", "0", "d", requires=("ausente",))
    assert broken.manifest()["requires"] == ["ausente"]
    a = registry.Module("a", "A", "0", "d", requires=("b",))
    b = registry.Module("b", "B", "0", "d", requires=("a",))
    mods = {"a": a, "b": b}
    import types
    for name, m in mods.items():
        sys.modules[f"_fake_{name}"] = types.SimpleNamespace(MODULE=m)
    try:
        with pytest.raises(registry.ModuleError, match="circular"):
            registry.load(["_fake_a", "_fake_b"])
        with pytest.raises(registry.ModuleError, match="requer"):
            registry.load(["_fake_a"])
    finally:
        sys.modules.pop("_fake_a"); sys.modules.pop("_fake_b")


def test_external_module_via_env(tmp_path, monkeypatch):
    pkg = tmp_path / "ext_mod_demo.py"
    pkg.write_text(textwrap.dedent('''
        from fastapi import APIRouter
        from finserve.registry import Module
        r = APIRouter()
        @r.get("/ping")
        def ping(): return {"pong": True}
        MODULE = Module("extdemo", "Ext", "1.0", "módulo externo de teste", router=r, requires=("platform",))
    '''), encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("FINSERVE_EXTRA_MODULES", "ext_mod_demo")
    with TestClient(create_app(["platform"])) as c:
        assert c.get("/api/extdemo/ping").json() == {"pong": True}
        assert "extdemo" in c.get("/api/platform/health").json()["modules"]


def test_invalid_module_object_rejected(tmp_path, monkeypatch):
    (tmp_path / "bad_mod_demo.py").write_text("MODULE = 42\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("FINSERVE_EXTRA_MODULES", "bad_mod_demo")
    with pytest.raises(registry.ModuleError, match="não expõe MODULE"):
        registry.load(["platform"])


def test_cli_new_module_scaffold_and_guards(tmp_path, monkeypatch, capsys):
    (tmp_path / "finserve").mkdir()
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "finserve" / "cli.py"))
    monkeypatch.setattr(cli.config, "ROOT", tmp_path)
    assert cli.new_module("Bad Name") == 2
    assert cli.new_module("cartoes") == 0
    base = tmp_path / "finserve" / "modules" / "cartoes"
    assert {p.name for p in base.iterdir()} == {"__init__.py", "router.py", "schema.sql"}
    assert (tmp_path / "tests" / "test_module_cartoes.py").exists()
    for f in ("__init__.py", "router.py"):
        compile((base / f).read_text(encoding="utf-8"), f, "exec")  # gera Python válido
    assert cli.new_module("cartoes") == 1  # nunca sobrescreve


def test_cli_check_passes(capsys):
    assert cli.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "[ok] dashboard market" in out and "[ok] compliance" in out


def test_static_front_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "FinServe" in r.text
    assert client.get("/assets/dashkit/kit.js").status_code == 200


def test_reference_report_is_reproducible(tmp_path):
    import json
    from finserve.report import build_report

    info = build_report(tmp_path, "2026-11-10")
    m = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert (tmp_path / "report.md").exists() and info["datasets"] == len(m["datasets"])
    assert {d["kind"] for d in m["datasets"]} == {"real", "synthetic", "derived"}
    assert len(m["anomalies"]) >= 3 and m["simulations"]["loan"]["summary"]["first_payment"] > 0
    assert m["reference_date"] == "2026-11-10"
