"""Configuração lida em tempo de chamada (variáveis de ambiente), para facilitar testes."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT = PACKAGE_DIR.parents[1]  # raiz do repositório quando executado a partir do código-fonte


def data_dir() -> Path:
    return Path(os.environ.get("FINSERVE_DATA_DIR", ROOT / "data"))


def db_path() -> Path:
    return Path(os.environ.get("FINSERVE_DB", data_dir() / "finserve.sqlite3"))


def snapshot_dir() -> Path:
    return Path(os.environ.get("FINSERVE_SNAPSHOT_DIR", ROOT / "data" / "snapshots"))


def web_dir() -> Path:
    return Path(os.environ.get("FINSERVE_WEB_DIR", ROOT / "web"))


def today() -> date:
    """Data de referência. `FINSERVE_TODAY=AAAA-MM-DD` torna seeds e testes determinísticos."""
    raw = os.environ.get("FINSERVE_TODAY")
    return date.fromisoformat(raw) if raw else date.today()
