from pathlib import Path

from ...registry import Dataset, Module
from . import store
from .router import router

_DAYS = [{"value": 180, "label": "6 meses"}, {"value": 365, "label": "12 meses"},
         {"value": 730, "label": "2 anos"}, {"value": 1825, "label": "5 anos"}]


def _datasets(con):
    obs = con.execute("SELECT COUNT(*) FROM market_observations").fetchone()[0]
    foc = con.execute("SELECT COUNT(*) FROM market_expectations").fetchone()[0]
    when = store.snapshot_retrieved_at(con)
    return [
        Dataset("market.sgs", "market", "Séries macro e crédito (SGS)", "real", "Banco Central do Brasil — SGS",
                "https://dadosabertos.bcb.gov.br/", when, obs,
                "Meta Selic, CDI, IPCA, IGP-M, dólar e inadimplência. Pontos futuros são descartados."),
        Dataset("market.focus", "market", "Expectativas de mercado (Focus)", "real",
                "Banco Central do Brasil — Olinda/Expectativas",
                "https://dadosabertos.bcb.gov.br/dataset/expectativas-mercado", when, foc,
                "Mediana de Selic, IPCA, câmbio e PIB para o ano corrente e o seguinte."),
        Dataset("market.simulations", "market", "Simulações de investimento e crédito", "derived",
                "Calculadoras determinísticas sobre CDI/Selic/IPCA reais", None, when, None,
                "Educacional. Premissas listadas em cada resposta (campo assumptions)."),
    ]


DASHBOARD = {
    "id": "market",
    "title": "Mercado",
    "eyebrow": "DADOS OFICIAIS · BANCO CENTRAL",
    "subtitle": "Juros, inflação, câmbio e inadimplência reais — a base das simulações do portal.",
    "nav": {"label": "Mercado", "icon": "◐", "order": 2},
    "filters": [{"id": "days", "label": "Janela", "type": "int", "default": 365, "options": _DAYS}],
    "sources": {
        "main": {"url": "/api/market/overview"},
        "focus": {"url": "/api/market/focus"},
        "selic": {"url": "/api/market/series/selic_meta", "params": ["days"]},
        "cdi": {"url": "/api/market/series/cdi_anual", "params": ["days"]},
        "usd": {"url": "/api/market/series/usd_brl", "params": ["days"]},
        "ipca": {"url": "/api/market/series/ipca_mensal", "params": ["days"]},
        "inad": {"url": "/api/market/series/inadimplencia_pf", "params": ["days"]},
    },
    "notice": "Dados reais e públicos do Banco Central. Simulações são educacionais e não constituem recomendação.",
    "widgets": [
        {"type": "kpis", "items": [
            {"label": "Meta Selic", "path": "cards.selic_meta.value", "format": "num2", "suffix": "% a.a.", "icon": "◐",
             "delta_path": "cards.selic_meta.change", "delta_unit": "p.p.", "foot_path": "cards.selic_meta.as_of", "foot_prefix": "Em "},
            {"label": "CDI", "path": "cards.cdi_anual.value", "format": "num2", "suffix": "% a.a.", "icon": "↗",
             "delta_path": "cards.cdi_anual.change", "delta_unit": "p.p.", "foot_path": "cards.cdi_anual.as_of", "foot_prefix": "Em "},
            {"label": "IPCA 12 meses", "path": "cards.ipca_12m.value", "format": "num2", "suffix": "%", "icon": "♧",
             "delta_path": "cards.ipca_12m.change", "delta_unit": "p.p.", "foot_path": "cards.ipca_12m.as_of", "foot_prefix": "Ref. ", "foot_format": "month"},
            {"label": "Dólar comercial", "path": "cards.usd_brl.value", "format": "num4", "prefix": "R$ ", "icon": "◈",
             "delta_path": "cards.usd_brl.change", "delta_unit": "%", "foot_path": "cards.usd_brl.as_of", "foot_prefix": "Em "},
        ]},
        {"type": "line", "source": "selic", "title": "Meta Selic", "kicker": "JUROS", "subtitle": "% ao ano — fonte BCB/SGS 432",
         "path": "points", "x": "date", "series": [{"key": "value", "label": "Meta Selic"}], "format": "num2", "span": 2},
        {"type": "line", "source": "usd", "title": "Dólar comercial", "kicker": "CÂMBIO", "subtitle": "R$ por US$ — BCB/SGS 1",
         "path": "points", "x": "date", "series": [{"key": "value", "label": "US$ (venda)"}], "format": "num4"},
        {"type": "bars", "source": "ipca", "title": "IPCA mensal", "kicker": "INFLAÇÃO", "subtitle": "variação % mensal — BCB/SGS 433",
         "path": "points", "label": "date", "value": "value", "format": "num2", "label_format": "month", "span": 2},
        {"type": "line", "source": "inad", "title": "Inadimplência — pessoas físicas", "kicker": "CRÉDITO",
         "subtitle": "% da carteira com atraso > 90 dias — BCB/SGS 21084", "path": "points", "x": "date",
         "series": [{"key": "value", "label": "Inadimplência PF"}], "format": "num2"},
        {"type": "table", "source": "focus", "title": "Expectativas Focus", "kicker": "MERCADO", "path": "items",
         "columns": [{"key": "indicator", "label": "Indicador"}, {"key": "reference_year", "label": "Ano"},
                     {"key": "median", "label": "Mediana", "format": "num2"}, {"key": "min", "label": "Mín.", "format": "num2"},
                     {"key": "max", "label": "Máx.", "format": "num2"}, {"key": "respondents", "label": "Resp.", "format": "int"},
                     {"key": "obs_date", "label": "Data", "format": "date"}], "span": 3},
        {"type": "calculator", "calc": "investment", "title": "Onde rende mais?", "kicker": "SIMULADOR", "span": 3},
        {"type": "calculator", "calc": "loan", "title": "Quanto custa o crédito?", "kicker": "SIMULADOR", "span": 3},
    ],
}

MODULE = Module(
    name="market",
    title="Mercado",
    version="2.0.0",
    description="Dados reais do Banco Central (SGS e Focus), simulador de investimentos e de crédito (Price/SAC, CET).",
    router=router,
    schema=Path(__file__).with_name("schema.sql"),
    tables=("market_series", "market_observations", "market_expectations", "market_sync_log"),
    seed=store.seed,
    datasets=_datasets,
    dashboards=[DASHBOARD],
)
