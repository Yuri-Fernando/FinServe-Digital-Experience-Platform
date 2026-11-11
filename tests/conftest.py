import pytest
from fastapi.testclient import TestClient

from finserve.app import create_app


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("FINSERVE_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("FINSERVE_TODAY", "2026-11-10")
    monkeypatch.delenv("FINSERVE_MODULES", raising=False)
    monkeypatch.delenv("FINSERVE_EXTRA_MODULES", raising=False)


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c
