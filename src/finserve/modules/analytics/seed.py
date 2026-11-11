"""Dados SINTÉTICOS de campanhas — determinísticos (seed fixa), com anomalias injetadas e documentadas.

As anomalias abaixo são o "gabarito" do detector: ficam só neste arquivo (e no DATA_CARD), nunca no banco,
para que nenhuma consulta a jusante consiga lê-las por engano.
"""
from __future__ import annotations

import math
import random
import sqlite3
from datetime import timedelta

from ... import config

DAYS = 120
RNG_SEED = 32593

# (id, slug, nome, canal, produto, audiência, estado, fator de orçamento mensal vs. gasto observado)
CAMPAIGNS = [
    (1, "credito-mais", "Crédito Mais", "Paid Search", "Crédito pessoal", "credito", "active", 1.05),
    (2, "prime-invest", "Prime Invest", "Organic", "Investimentos", "investidor", "active", 0.95),
    (3, "conta-nova", "Conta Digital", "Social", "Conta digital", "jovem", "active", 0.80),
    (4, "cartao-smart", "Cartão Smart", "Email", "Cartão", "all", "active", 1.10),
    (5, "tesouro-facil", "Investir é Simples", "Paid Search", "Investimentos", "investidor", "active", 1.00),
    (6, "renegocia", "Recomeço Financeiro", "Email", "Renegociação", "credito", "active", 1.25),
    (7, "pix-empresas", "Pix para Negócios", "Organic", "Conta PJ", "all", "active", 0.98),
    (8, "consorcio", "Conquistas Planejadas", "Social", "Consórcio", "all", "paused", 1.00),
]

# Gabarito: (campaign_id, índice do dia [0=mais antigo, 119=hoje], métrica afetada, descrição)
INJECTED_ANOMALIES = [
    (3, 110, "cpl", "gasto x3,2 e cliques x0,6 (pico de custo em mídia social)"),
    (1, 100, "lcp_ms", "LCP x1,9 (regressão de performance após deploy)"),
    (5, 112, "lead_rate", "leads x0,15 (quebra de tracking do formulário)"),
]

AB_TESTS = [
    ("hero-cta-copy", "Copy do CTA do hero — crédito", 1, "lead_conversion",
     "Um CTA com verbo de ação aumenta a conversão em lead.", 42, [("A", 9800, 392), ("B", 9750, 468)]),
    ("banner-layout", "Layout do banner do cartão", 4, "lead_conversion",
     "Layout com benefício em destaque converte mais.", 30, [("A", 5200, 208), ("B", 5150, 214)]),
    ("form-curto", "Formulário curto — investimentos", 2, "lead_conversion",
     "Menos campos reduzem abandono.", 14, [("A", 1800, 90), ("B", 1750, 103)]),
]


def reset_and_seed(con: sqlite3.Connection) -> tuple[int, int]:
    end = config.today()
    rng = random.Random(RNG_SEED)
    for t in ("ab_variants", "ab_tests", "fact_experience_daily", "dim_date", "campaigns"):
        con.execute(f"DELETE FROM {t}")
    con.executemany(
        "INSERT INTO campaigns(id,slug,name,channel,product,audience,monthly_budget_brl,state) VALUES(?,?,?,?,?,?,0,?)",
        [(c[0], c[1], c[2], c[3], c[4], c[5], c[6]) for c in CAMPAIGNS],
    )
    anomalies = {(a[0], a[1]): a[2] for a in INJECTED_ANOMALIES}
    for i in range(DAYS):
        day = end - timedelta(days=DAYS - 1 - i)
        key = int(day.strftime("%Y%m%d"))
        con.execute("INSERT INTO dim_date VALUES(?,?,?,?,?)", (key, day.isoformat(), day.weekday(), day.month, day.year))
        for cid, _slug, _name, _channel, _product, _aud, state, _bf in CAMPAIGNS:
            weekday = 1.12 if day.weekday() < 5 else 0.82
            season = 1 + 0.17 * math.sin(i / 12.0 + cid)
            trend = 0.84 + 0.0018 * i
            active = 0.38 if state == "paused" else 1
            impressions = max(100, int((4900 + cid * 560) * weekday * season * trend * active * rng.uniform(.87, 1.15)))
            ctr = 0.018 + 0.004 * (cid % 4) + 0.002 * math.sin(i / 13)
            clicks = max(1, int(impressions * ctr * rng.uniform(.89, 1.13)))
            lead_rate = (.08 + 0.013 * (cid % 3)) * rng.uniform(.86, 1.12)
            leads = max(0, int(clicks * lead_rate))
            approvals = min(leads, int(leads * (.24 + .045 * (cid % 4)) * rng.uniform(.83, 1.13)))
            sessions = int(clicks * rng.uniform(.94, 1.28))
            spend = round(clicks * (1.3 + cid * .21) * rng.uniform(.86, 1.18), 2)
            revenue = round(approvals * (145 + cid * 42) * rng.uniform(.86, 1.23), 2)
            lcp = int(rng.uniform(1680, 2650) + cid * 37)
            inp = int(rng.uniform(120, 290) + cid * 6)
            cls = int(rng.uniform(25, 130))
            hit = anomalies.get((cid, i))
            if hit == "cpl":
                spend = round(spend * 3.2, 2)
                clicks = max(1, int(clicks * 0.6))
                leads, approvals = min(leads, clicks), min(approvals, min(leads, clicks))
                sessions = min(sessions, int(clicks * 1.28))
                revenue = round(revenue * 0.6, 2)
            elif hit == "lcp_ms":
                lcp = int(lcp * 1.9)
            elif hit == "lead_rate":
                leads = int(leads * 0.15)
                approvals = min(approvals, leads)
                revenue = round(revenue * 0.15, 2)
            con.execute(
                """INSERT INTO fact_experience_daily(date_key,campaign_id,impressions,clicks,leads,approvals,sessions,
                   spend_brl,attributable_revenue_brl,lcp_ms,inp_ms,cls_milli) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (key, cid, impressions, clicks, leads, approvals, sessions, spend, revenue, lcp, inp, cls),
            )
    # Orçamento mensal calibrado ao gasto observado nos últimos 30 dias (fator por campanha → histórias de pacing)
    start30 = int((end - timedelta(days=29)).strftime("%Y%m%d"))
    for cid, *_rest, factor in CAMPAIGNS:
        spent = con.execute("SELECT COALESCE(SUM(spend_brl),0) FROM fact_experience_daily "
                            "WHERE campaign_id=? AND date_key>=?", (cid, start30)).fetchone()[0]
        con.execute("UPDATE campaigns SET monthly_budget_brl=? WHERE id=?", (round(spent * factor, -2), cid))
    for key, name, cid, metric, hyp, started_days_ago, variants in AB_TESTS:
        cur = con.execute("INSERT INTO ab_tests(key,name,campaign_id,metric,hypothesis,started_at) VALUES(?,?,?,?,?,?)",
                          (key, name, cid, metric, hyp, (end - timedelta(days=started_days_ago)).isoformat()))
        con.executemany("INSERT INTO ab_variants(test_id,variant,visitors,conversions) VALUES(?,?,?,?)",
                        [(cur.lastrowid, v, n, x) for v, n, x in variants])
    return len(CAMPAIGNS), DAYS * len(CAMPAIGNS)


def seed(con: sqlite3.Connection) -> None:
    if con.execute("SELECT COUNT(*) FROM fact_experience_daily").fetchone()[0] == 0:
        reset_and_seed(con)
