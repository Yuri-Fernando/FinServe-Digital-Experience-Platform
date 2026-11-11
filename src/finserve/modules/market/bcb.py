"""Cliente dos dados abertos do Banco Central (SGS e Expectativas/Focus) — só biblioteca padrão.

Códigos de série verificados contra a API em 2026-11-10 (ver docs/DATA_CARD.md). Séries cujo código ou
descrição não pôde ser confirmado NÃO entram no catálogo.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SGS_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
FOCUS_BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
USER_AGENT = "finserve-platform/2.0 (+estudo-portfolio)"

Fetcher = Callable[[str], Any]

SERIES = [
    {"id": "selic_meta", "sgs": 432, "name": "Meta Selic", "unit": "% a.a.", "frequency": "daily",
     "description": "Meta da taxa Selic definida pelo Copom.",
     "url": "https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom"},
    {"id": "cdi_anual", "sgs": 4389, "name": "CDI anualizado (base 252)", "unit": "% a.a.", "frequency": "daily",
     "description": "Taxa DI over anualizada em base 252 dias úteis.",
     "url": "https://dadosabertos.bcb.gov.br/dataset/4389-taxa-de-juros---cdi-anualizada-base-252"},
    {"id": "ipca_mensal", "sgs": 433, "name": "IPCA — variação mensal", "unit": "% a.m.", "frequency": "monthly",
     "description": "Índice Nacional de Preços ao Consumidor Amplo (IBGE), variação mensal.",
     "url": "https://dadosabertos.bcb.gov.br/dataset/433-indice-nacional-de-precos-ao-consumidor-amplo-ipca"},
    {"id": "igpm_mensal", "sgs": 189, "name": "IGP-M — variação mensal", "unit": "% a.m.", "frequency": "monthly",
     "description": "Índice Geral de Preços do Mercado (FGV), variação mensal.",
     "url": "https://dadosabertos.bcb.gov.br/dataset/189-indice-geral-de-precos-do-mercado-igp-m"},
    {"id": "usd_brl", "sgs": 1, "name": "Dólar comercial (venda)", "unit": "R$/US$", "frequency": "daily",
     "description": "Taxa de câmbio livre — dólar americano (venda), SGS 1.",
     "url": "https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario"},
    {"id": "inadimplencia_total", "sgs": 21082, "name": "Inadimplência da carteira de crédito — total", "unit": "%",
     "frequency": "monthly",
     "description": "% da carteira do SFN com atraso superior a 90 dias (crédito livre + direcionado).",
     "url": "https://dadosabertos.bcb.gov.br/dataset/21082-inadimplencia-da-carteira-de-credito---total"},
    {"id": "inadimplencia_pf", "sgs": 21084, "name": "Inadimplência da carteira — pessoas físicas", "unit": "%",
     "frequency": "monthly",
     "description": "% da carteira de pessoas físicas com atraso superior a 90 dias.",
     "url": "https://dadosabertos.bcb.gov.br/dataset/21084-inadimplencia-da-carteira-de-credito---pessoas-fisicas---total"},
]
SERIES_BY_ID = {s["id"]: s for s in SERIES}
FOCUS_INDICATORS = ("Selic", "IPCA", "Câmbio", "PIB Total")
LOOKBACK_DAYS = {"daily": 400, "monthly": 1830}


class BcbError(RuntimeError):
    pass


def fetch_json(url: str, timeout: int = 30, retries: int = 2) -> Any:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise BcbError(f"falha ao consultar {url}: {last}")


def sgs_url(code: int, start: date, end: date) -> str:
    return SGS_BASE.format(code=code) + f"?formato=json&dataInicial={start:%d/%m/%Y}&dataFinal={end:%d/%m/%Y}"


def parse_sgs(payload: Any, today: date) -> list[tuple[str, float]]:
    """Converte a resposta do SGS em [(AAAA-MM-DD, valor)] ordenado.

    Descarta observações com data posterior a `today`: o SGS devolve, em algumas séries, pontos datados no
    futuro (observado na meta Selic em 2026-11-10); tratá-los como realizados seria erro.
    """
    if not isinstance(payload, list):
        raise BcbError("payload SGS inesperado")
    out: dict[str, float] = {}
    for item in payload:
        try:
            d = datetime.strptime(item["data"], "%d/%m/%Y").date()
            v = float(str(item["valor"]).replace(",", "."))
        except (KeyError, ValueError, TypeError) as exc:
            raise BcbError(f"observação SGS inválida: {item!r}") from exc
        if d > today:
            continue
        out[d.isoformat()] = v
    return sorted(out.items())


def focus_url(indicator: str, since: date, top: int = 400) -> str:
    flt = f"Indicador eq '{indicator}' and Data ge '{since.isoformat()}' and baseCalculo eq 0"
    q = {"$filter": flt, "$orderby": "Data desc", "$top": str(top), "$format": "json"}
    return FOCUS_BASE + "?" + "&".join(f"{k}={quote(v, safe=chr(39) + '()=,')}" for k, v in q.items())


def parse_focus(payload: Any) -> list[dict]:
    vals = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(vals, list):
        raise BcbError("payload Focus inesperado")
    return [
        {
            "indicator": v["Indicador"], "reference_year": str(v["DataReferencia"]), "date": v["Data"],
            "median": v.get("Mediana"), "mean": v.get("Media"), "std": v.get("DesvioPadrao"),
            "min": v.get("Minimo"), "max": v.get("Maximo"), "respondents": v.get("numeroRespondentes"),
        }
        for v in vals
    ]


def lookback_start(frequency: str, today: date) -> date:
    return today - timedelta(days=LOOKBACK_DAYS[frequency])
