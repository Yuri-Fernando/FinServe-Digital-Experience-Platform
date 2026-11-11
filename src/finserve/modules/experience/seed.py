from __future__ import annotations

import sqlite3

from ... import audit
from . import service

CONTENTS = [
    ("hero-home", "campaignhero", "Seu próximo passo começa aqui", "Seu dinheiro com mais possibilidades",
     "Conta digital, crédito e investimentos em uma experiência simples, transparente e feita para você.",
     "Conhecer soluções", "/solucoes", "all", "PUBLISHED", "marketing"),
    ("hero-invest", "campaignhero", "Planeje com confiança", "Investir bem é uma decisão informada",
     "Compare alternativas, entenda seu perfil e explore possibilidades de investimento com clareza.",
     "Explorar investimentos", "/investimentos", "investidor", "PUBLISHED", "investimentos"),
    ("hero-credito", "campaignhero", "Crédito com transparência", "Simule antes de decidir",
     "Conheça taxas ilustrativas e escolha um caminho compatível com seu planejamento.",
     "Simular crédito", "/credito", "credito", "PUBLISHED", "credito"),
    ("hero-jovem", "campaignhero", "Sua vida financeira, seu ritmo", "Uma conta que acompanha seus planos",
     "Controle seus gastos, defina objetivos e acompanhe suas conquistas.",
     "Abrir conta demo", "/conta", "jovem", "PUBLISHED", "marketing"),
    ("ratecard-mercado", "ratecard", "Taxas de referência · Banco Central", "Selic hoje: {{selic_meta}}",
     "CDI em {{cdi_anual}} e IPCA em 12 meses de {{ipca_12m}}. Fonte: Banco Central do Brasil. Referência de mercado, não é oferta.",
     "Simular investimento", "/investimentos", "all", "PUBLISHED", "investimentos"),
    ("banner-invest", "promobanner", "Planejamento", "Uma estratégia para cada objetivo",
     "Conteúdo educacional para você conhecer possibilidades.", "Saiba mais", "/educacao", "investidor", "APPROVED", "marketing"),
    ("banner-openfinance", "promobanner", "Em preparação", "Mais visão, melhores decisões",
     "Consolide informações em uma experiência de demonstração.", "Ver conceito", "/open-finance", "all", "IN_REVIEW", "produto"),
    ("banner-cartao", "promobanner", "Em elaboração", "Benefícios que combinam com sua rotina",
     "Ajuste benefícios de acordo com suas prioridades.", "Conhecer cartão", "/cartao", "jovem", "DRAFT", "marketing"),
]


def reset_and_seed(con: sqlite3.Connection) -> int:
    con.execute("DELETE FROM content_revisions")
    con.execute("DELETE FROM content_items")
    con.execute("DELETE FROM audit_events WHERE module='experience'")
    now = audit.utcnow()
    for key, comp, eyebrow, title, body, label, url, seg, status, owner in CONTENTS:
        pub = now if status == "PUBLISHED" else None
        cur = con.execute(
            """INSERT INTO content_items(key,component,eyebrow,title,body,cta_label,cta_url,segment,status,version,owner,
               updated_at,published_at) VALUES(?,?,?,?,?,?,?,?,?,1,?,?,?)""",
            (key, comp, eyebrow, title, body, label, url, seg, status, owner, now, pub))
        item = service.snapshot(con, cur.lastrowid)
        service.add_revision(con, item, owner, "Carga de demonstração", now)
        service.record(con, item["id"], owner, "seed", None, status, "Dados de demonstração", now)
    return len(CONTENTS)


def seed(con: sqlite3.Connection) -> None:
    if con.execute("SELECT COUNT(*) FROM content_items").fetchone()[0] == 0:
        reset_and_seed(con)
