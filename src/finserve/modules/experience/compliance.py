"""Motor de compliance editorial: regras YAML versionadas, reason codes e fail-safe (erro => bloqueia)."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).with_name("compliance_rules.yaml")
SEVERITIES = ("block", "warn")
RULE_TYPES = ("forbidden", "requires")


class ComplianceError(Exception):
    """Definição de regra inválida (detectada no carregamento)."""


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


@lru_cache(maxsize=4)
def load_rules(path: str | None = None) -> dict:
    data = yaml.safe_load(Path(path or RULES_PATH).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "rules" not in data:
        raise ComplianceError("arquivo de regras sem 'rules'")
    seen = set()
    for r in data["rules"]:
        for key in ("id", "name", "type", "severity", "reason_code", "fields", "message"):
            if key not in r:
                raise ComplianceError(f"regra {r.get('id', '?')}: falta '{key}'")
        if r["id"] in seen:
            raise ComplianceError(f"id duplicado: {r['id']}")
        seen.add(r["id"])
        if r["severity"] not in SEVERITIES or r["type"] not in RULE_TYPES:
            raise ComplianceError(f"regra {r['id']}: tipo/severidade inválidos")
        pats = r.get("patterns", []) + r.get("when_any", []) + r.get("unless_any", [])
        if not pats:
            raise ComplianceError(f"regra {r['id']}: sem padrões")
        for p in pats:
            try:
                re.compile(p)
            except re.error as exc:
                raise ComplianceError(f"regra {r['id']}: regex inválida {p!r}: {exc}") from exc
    return data


def public_rules(path: str | None = None) -> list[dict]:
    data = load_rules(path)
    return [{k: r[k] for k in ("id", "name", "severity", "reason_code", "message", "suggestion") if k in r}
            for r in data["rules"]]


def _issue(rule, field, match):
    return {"rule_id": rule["id"], "name": rule["name"], "severity": rule["severity"],
            "reason_code": rule["reason_code"], "field": field, "match": match,
            "message": rule["message"], "suggestion": rule.get("suggestion", "")}


def check(content: dict, path: str | None = None) -> dict:
    """Avalia um conteúdo (campos de texto). Qualquer erro interno vira bloqueio ENGINE_ERROR."""
    try:
        data = load_rules(path)
        issues: list[dict] = []
        for rule in data["rules"]:
            texts = {f: normalize(str(content.get(f, ""))) for f in rule["fields"]}
            if rule["type"] == "forbidden":
                for field, text in texts.items():
                    for pat in rule["patterns"]:
                        m = re.search(pat, text)
                        if m:
                            issues.append(_issue(rule, field, m.group(0)))
                            break
            else:
                joined = " ".join(texts.values())
                trig = next((m for p in rule["when_any"] if (m := re.search(p, joined))), None)
                if trig and not any(re.search(p, joined) for p in rule["unless_any"]):
                    issues.append(_issue(rule, "+".join(rule["fields"]), trig.group(0)))
        blocking = sum(1 for i in issues if i["severity"] == "block")
        return {"passed": blocking == 0, "blocking": blocking, "warnings": len(issues) - blocking,
                "issues": issues, "rules_version": data.get("version", "?")}
    except Exception as exc:  # fail-safe: nunca aprovar em silêncio
        issue = {"rule_id": "ENGINE_ERROR", "name": "Falha do motor de compliance", "severity": "block",
                 "reason_code": "ENGINE_ERROR", "field": "-", "match": type(exc).__name__,
                 "message": "O motor de compliance falhou; conteúdo bloqueado por segurança.", "suggestion": str(exc)[:200]}
        return {"passed": False, "blocking": 1, "warnings": 0, "issues": [issue], "rules_version": "?"}
