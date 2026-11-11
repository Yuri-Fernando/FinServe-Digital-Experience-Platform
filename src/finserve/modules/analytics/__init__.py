from pathlib import Path

from ...registry import Dataset, Module
from .router import router
from .seed import seed

_DAYS = [{"value": v, "label": f"Últimos {v} dias"} for v in (7, 14, 30, 60, 90)]
_SEGMENTS = [{"value": "all", "label": "Todos"}, {"value": "investidor", "label": "Investidores"},
             {"value": "credito", "label": "Crédito"}, {"value": "jovem", "label": "Jovem"}]


def _datasets(con):
    facts = con.execute("SELECT COUNT(*) FROM fact_experience_daily").fetchone()[0]
    tests = con.execute("SELECT COUNT(*) FROM ab_tests").fetchone()[0]
    return [
        Dataset("analytics.campaign_facts", "analytics", "Fatos diários de campanhas (8 campanhas × 120 dias)",
                "synthetic", "Gerador determinístico (seed 32593) com 3 anomalias injetadas", None, None, facts,
                "Receita atribuída e Core Web Vitals são ilustrativos. Ver docs/DATA_CARD.md."),
        Dataset("analytics.ab_tests", "analytics", "Experimentos A/B", "synthetic",
                "Valores fixos no seed; estatística calculada em tempo de consulta", None, None, tests,
                "Um vencedor, um inconclusivo, um com amostra insuficiente."),
    ]


DASHBOARD = {
    "id": "analytics-overview",
    "title": "Visão geral",
    "eyebrow": "FINANCIAL EXPERIENCE ANALYTICS",
    "subtitle": "Jornada digital, campanhas e qualidade da experiência em um só lugar.",
    "nav": {"label": "Visão geral", "icon": "◫", "order": 1},
    "filters": [
        {"id": "days", "label": "Período", "type": "int", "default": 30, "options": _DAYS},
        {"id": "segment", "label": "Audiência", "type": "text", "default": "all", "options": _SEGMENTS},
    ],
    "sources": {
        "main": {"url": "/api/analytics/dashboard", "params": ["days", "segment"]},
        "anomalies": {"url": "/api/analytics/anomalies", "params": ["days"]},
        "pacing": {"url": "/api/analytics/pacing"},
        "experiments": {"url": "/api/analytics/experiments"},
    },
    "notice": "Dados 100% sintéticos (seed fixa). Receita atribuída e Core Web Vitals são ilustrativos.",
    "widgets": [
        {"type": "kpis", "items": [
            {"label": "Sessões digitais", "path": "summary.sessions", "format": "compact", "icon": "◉", "delta_path": "delta.sessions", "foot": "Volume agregado de visitas"},
            {"label": "Taxa de clique", "path": "summary.ctr_pct", "format": "pct", "icon": "↗", "delta_path": "delta.ctr_pct", "foot": "Cliques / impressões"},
            {"label": "Leads gerados", "path": "summary.leads", "format": "compact", "icon": "♧", "delta_path": "delta.leads", "foot_path": "summary.conversion_pct", "foot_prefix": "Conversão ", "foot_format": "pct"},
            {"label": "Receita atribuída*", "path": "summary.revenue", "format": "money", "icon": "◈", "delta_path": "delta.revenue", "foot_path": "summary.roas", "foot_prefix": "ROAS ", "foot_suffix": "x · simulado"},
        ]},
        {"type": "kpis", "compact": True, "items": [
            {"label": "Custo por lead", "path": "summary.cpl", "format": "money2", "delta_path": "delta.cpl", "delta_good": "down"},
            {"label": "ROAS", "path": "summary.roas", "format": "num2", "suffix": "x", "delta_path": "delta.roas"},
            {"label": "Aprovação de leads", "path": "summary.approval_pct", "format": "pct"},
            {"label": "Investimento em mídia", "path": "summary.spend", "format": "money", "delta_path": "delta.spend", "delta_good": "none"},
        ]},
        {"type": "line", "title": "Engajamento & conversão", "kicker": "JORNADA DIGITAL", "subtitle": "Sessões, cliques e leads por dia (séries normalizadas)",
         "path": "daily", "x": "date", "normalize": True, "span": 2,
         "series": [{"key": "sessions", "label": "Sessões"}, {"key": "clicks", "label": "Cliques"}, {"key": "leads", "label": "Leads"}]},
        {"type": "donut", "title": "Canais de entrada", "kicker": "AQUISIÇÃO", "subtitle": "Participação por leads",
         "path": "channels", "label": "name", "value": "leads", "center_label": "Leads"},
        {"type": "funnel", "title": "Funil de aquisição", "kicker": "PIPELINE", "subtitle": "Do alcance à aprovação simulada", "path": "summary",
         "stages": [{"key": "impressions", "label": "Impressões"}, {"key": "clicks", "label": "Cliques"},
                    {"key": "leads", "label": "Leads"}, {"key": "approvals", "label": "Aprovações"}]},
        {"type": "vitals", "title": "Core Web Vitals", "kicker": "EXPERIÊNCIA", "subtitle": "p75 do período vs. limiares do web.dev", "path": "web_vitals"},
        {"type": "list", "source": "anomalies", "title": "Anomalias detectadas", "kicker": "MONITORAMENTO",
         "subtitle": "z modificado (mediana/MAD) ≥ 3,5", "path": "items", "limit": 6, "badge": "severity",
         "primary": "{campaign} · {metric_label}", "secondary": "{date} · {value} vs mediana {baseline_median} (z={z})",
         "empty": "Nenhuma anomalia no período."},
        {"type": "table", "title": "Performance por campanha", "kicker": "CAMPANHAS", "path": "campaigns", "span": 3,
         "export": {"url": "/api/analytics/export.csv", "params": ["days", "segment"], "label": "Exportar CSV"},
         "columns": [{"key": "name", "label": "Campanha"}, {"key": "channel", "label": "Canal"}, {"key": "audience", "label": "Segmento"},
                     {"key": "impressions", "label": "Impressões", "format": "int"}, {"key": "leads", "label": "Leads", "format": "int"},
                     {"key": "ctr_pct", "label": "CTR", "format": "pct"}, {"key": "cpl", "label": "CPL", "format": "money2"},
                     {"key": "revenue", "label": "Receita atribuída*", "format": "money"}, {"key": "state", "label": "Status", "format": "badge"}],
         "footnote": "* Receita atribuída ilustrativa, calculada a partir de eventos sintéticos."},
        {"type": "table", "source": "pacing", "title": "Pacing de orçamento", "kicker": "MÍDIA", "path": "items", "span": 3,
         "columns": [{"key": "name", "label": "Campanha"}, {"key": "spent_mtd", "label": "Gasto no mês", "format": "money"},
                     {"key": "budget", "label": "Orçamento", "format": "money"}, {"key": "budget_used_pct", "label": "Usado", "format": "pct1"},
                     {"key": "expected_pct", "label": "Esperado", "format": "pct1"}, {"key": "projected_month_end", "label": "Projeção do mês", "format": "money"},
                     {"key": "status", "label": "Ritmo", "format": "badge"}]},
        {"type": "table", "source": "experiments", "title": "Experimentos A/B", "kicker": "OTIMIZAÇÃO", "path": "items", "span": 3,
         "columns": [{"key": "name", "label": "Experimento"}, {"key": "control.rate_pct", "label": "Controle", "format": "pct"},
                     {"key": "variant.rate_pct", "label": "Variante", "format": "pct"}, {"key": "lift_pct", "label": "Lift", "format": "pct1"},
                     {"key": "p_value", "label": "p-valor", "format": "num4"}, {"key": "verdict", "label": "Veredito", "format": "badge"},
                     {"key": "enough_traffic", "label": "Amostra suficiente?", "format": "bool"}],
         "footnote": "Teste z bicaudal (α=5%). Inconclusivo com tráfego insuficiente não prova ausência de efeito."},
    ],
}

MODULE = Module(
    name="analytics",
    title="Analytics de campanhas",
    version="2.0.0",
    description="KPIs, variação vs. período anterior, anomalias (z modificado), Core Web Vitals p75, pacing e testes A/B.",
    router=router,
    schema=Path(__file__).with_name("schema.sql"),
    tables=("campaigns", "dim_date", "fact_experience_daily", "ab_tests", "ab_variants"),
    seed=seed,
    datasets=_datasets,
    dashboards=[DASHBOARD],
)
