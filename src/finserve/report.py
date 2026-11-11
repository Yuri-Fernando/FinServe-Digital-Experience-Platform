"""Relatório de referência reproduzível: `python -m finserve report`.

Roda em um banco TEMPORÁRIO (nunca toca no banco do usuário), com a data de referência fixa e os snapshots
reais versionados. Gera `reports/metrics.json` (máquina) e `reports/report.md` (leitura) — são a fonte dos
números citados no README.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, registry


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return f"{v:,}".replace(",", ".")
    if isinstance(v, float):
        return f"{v:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(v)


def build_report(out_dir: Path, today: str) -> dict:
    tmp = tempfile.mkdtemp(prefix="finserve-report-")
    old = {k: os.environ.get(k) for k in ("FINSERVE_DB", "FINSERVE_TODAY")}
    os.environ["FINSERVE_DB"] = str(Path(tmp) / "report.sqlite3")
    os.environ["FINSERVE_TODAY"] = today
    try:
        from .app import bootstrap
        from .db import connect
        from .modules.analytics import service as an
        from .modules.experience import compliance
        from .modules.market import calculators as calc
        from .modules.market import service as mk

        mods = registry.load()
        bootstrap(mods)
        with connect() as con:
            datasets = [d.as_dict() for m in mods if m.datasets for d in m.datasets(con)]
            overview = mk.overview(con)
            focus = mk.focus(con)
            mi = mk.market_inputs(con)
            dash = an.dashboard(con, 30, "all")
            anomalies = an.anomalies(con, 30)
            pacing = an.pacing(con)
            experiments = an.experiments(con)
        inv = calc.simulate_investment(10000, 12, cdi_aa=mi["cdi_aa"], selic_meta=mi["selic_meta"], ipca_12m=mi["ipca_12m"])
        loan = calc.simulate_loan(10000, 24, 2.5, system="price")
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    metrics = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "version": __version__, "reference_date": today,
        "modules": [m.name for m in mods],
        "compliance_rules": len(compliance.public_rules()),
        "datasets": datasets,
        "market": {"cards": {k: {kk: v[kk] for kk in ("label", "value", "unit", "as_of", "change", "kind")}
                             for k, v in overview["cards"].items()},
                   "data_retrieved_at": overview["meta"]["data_retrieved_at"], "focus": focus["items"]},
        "simulations": {
            "investment": {"inputs": inv["inputs"], "products": [{k: p[k] for k in ("label", "net_final", "net_gain",
                           "net_annual_pct", "ir", "real_return_pct")} for p in inv["products"]]},
            "loan": {"inputs": loan["inputs"], "summary": loan["summary"]},
        },
        "analytics_30d": {"summary": dash["summary"], "delta_pct": dash["delta"], "web_vitals": dash["web_vitals"]},
        "anomalies": anomalies["items"],
        "pacing": pacing["items"],
        "experiments": [{k: e[k] for k in ("key", "name", "control", "variant", "lift_pct", "p_value", "ci95_pp",
                                          "verdict", "required_per_variant", "enough_traffic")} for e in experiments],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(metrics), encoding="utf-8")
    return {"out": str(out_dir), "datasets": len(datasets), "anomalies": len(anomalies["items"])}


def _markdown(m: dict) -> str:
    L = [f"# Relatório de referência — FinServe Platform v{m['version']}", "",
         f"Gerado por `python -m finserve report` em banco temporário · data de referência **{m['reference_date']}** · "
         f"dados de mercado coletados em **{m['market']['data_retrieved_at']}**. Arquivo-fonte: [`metrics.json`](metrics.json).", "",
         "> Mercado = dados públicos **reais** do Banco Central. Campanhas, A/B e Core Web Vitals = **sintéticos** (seed fixa).", "",
         "## 1. Proveniência", "", "| Dataset | Tipo | Fonte | Linhas | Coleta |", "|---|---|---|---|---|"]
    for d in m["datasets"]:
        L.append(f"| {d['title']} | {d['kind']} | {d['source']} | {_fmt(d['rows'])} | {d['retrieved_at'] or '—'} |")
    L += ["", "## 2. Mercado (real)", "", "| Indicador | Valor | Unidade | Referência | Variação | Tipo |", "|---|---|---|---|---|---|"]
    for c in m["market"]["cards"].values():
        L.append(f"| {c['label']} | {_fmt(c['value'], 4 if c['unit'] == 'R$' else 2)} | {c['unit']} | {c['as_of']} | {_fmt(c['change'])} | {c['kind']} |")
    L += ["", "**Focus (mediana)**", "", "| Indicador | Ano | Mediana | Mín. | Máx. | Respondentes | Data |", "|---|---|---|---|---|---|---|"]
    for f in m["market"]["focus"]:
        L.append(f"| {f['indicator']} | {f['reference_year']} | {_fmt(f['median'])} | {_fmt(f['min'])} | {_fmt(f['max'])} | {_fmt(f['respondents'])} | {f['obs_date']} |")
    inv, loan = m["simulations"]["investment"], m["simulations"]["loan"]
    i = inv["inputs"]
    L += ["", "## 3. Simulações (insumos reais)", "",
          f"**Investimento** — R$ {_fmt(float(i['amount']))}, {i['months']} meses, CDI {_fmt(i['cdi_aa'])}% a.a., Selic {_fmt(i['selic_meta'])}% a.a., IPCA 12m {_fmt(i['ipca_12m'])}%.", "",
          "| Produto | Valor líquido | Ganho líquido | % a.a. líquido | IR | Retorno real |", "|---|---|---|---|---|---|"]
    for p in inv["products"]:
        L.append(f"| {p['label']} | R$ {_fmt(p['net_final'])} | R$ {_fmt(p['net_gain'])} | {_fmt(p['net_annual_pct'])}% | R$ {_fmt(p['ir'])} | {_fmt(p['real_return_pct'])}% |")
    s = loan["summary"]
    L += ["", f"**Crédito** — R$ 10.000, 24 meses, 2,5% a.m., Price: 1ª parcela R$ {_fmt(s['first_payment'])} · total pago R$ {_fmt(s['total_paid'])} · "
          f"juros R$ {_fmt(s['total_interest'])} · CET {_fmt(s['cet_annual_pct'])}% a.a. (sem IOF/seguros).", "",
          "## 4. Analytics — últimos 30 dias (sintético)", "", "| KPI | Valor | Δ vs. 30 dias anteriores |", "|---|---|---|"]
    su, de = m["analytics_30d"]["summary"], m["analytics_30d"]["delta_pct"]
    for k, lbl in (("sessions", "Sessões"), ("leads", "Leads"), ("ctr_pct", "CTR (%)"), ("cpl", "CPL (R$)"), ("roas", "ROAS"), ("revenue", "Receita atribuída (R$)")):
        L.append(f"| {lbl} | {_fmt(su[k])} | {_fmt(de.get(k), 1)}% |")
    L += ["", "**Core Web Vitals (p75)**", "", "| Métrica | p75 | Status |", "|---|---|---|"]
    for v in m["analytics_30d"]["web_vitals"]:
        L.append(f"| {v['name']} | {_fmt(v['p75'])} {v['unit']} | {v['status']} |")
    L += ["", "## 5. Anomalias detectadas (z modificado ≥ 3,5)", "", "| Campanha | Data | Métrica | Valor | Mediana | z | Severidade |", "|---|---|---|---|---|---|---|"]
    for a in m["anomalies"]:
        L.append(f"| {a['campaign']} | {a['date']} | {a['metric_label']} | {_fmt(a['value'], 4)} | {_fmt(a['baseline_median'], 4)} | {_fmt(a['z'])} | {a['severity']} |")
    L += ["", "## 6. Experimentos A/B (sintético)", "", "| Experimento | Controle | Variante | Lift | p-valor | IC 95% (p.p.) | Veredito | Amostra necessária/variante | Suficiente? |", "|---|---|---|---|---|---|---|---|---|"]
    for e in m["experiments"]:
        L.append(f"| {e['name']} | {_fmt(e['control']['rate_pct'])}% | {_fmt(e['variant']['rate_pct'])}% | {_fmt(e['lift_pct'], 1)}% | {_fmt(e['p_value'], 4)} | "
                 f"{_fmt(e['ci95_pp'][0])} a {_fmt(e['ci95_pp'][1])} | {e['verdict']} | {_fmt(e['required_per_variant'])} | {'sim' if e['enough_traffic'] else 'não'} |")
    L += ["", "## 7. Pacing de orçamento (sintético)", "", "| Campanha | Gasto no mês | Orçamento | Usado | Esperado | Status |", "|---|---|---|---|---|---|"]
    for p in m["pacing"]:
        L.append(f"| {p['name']} | R$ {_fmt(p['spent_mtd'])} | R$ {_fmt(p['budget'])} | {_fmt(p['budget_used_pct'], 1)}% | {_fmt(p['expected_pct'], 1)}% | {p['status']} |")
    L.append("")
    return "\n".join(L)
