from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ...db import connect
from . import calculators as calc
from . import service, store

router = APIRouter()


def _inputs_or_409(con, cdi_aa, selic_meta):
    mi = service.market_inputs(con) or {}
    cdi = cdi_aa if cdi_aa is not None else mi.get("cdi_aa")
    selic = selic_meta if selic_meta is not None else mi.get("selic_meta")
    if cdi is None or selic is None:
        raise HTTPException(409, "Sem dados de mercado. Execute a sincronização ou informe cdi_aa e selic_meta.")
    return cdi, selic, mi


@router.get("/overview")
def overview():
    with connect() as con:
        return service.overview(con)


@router.get("/series")
def series_catalog():
    with connect() as con:
        return service.catalog(con)


@router.get("/series/{series_id}")
def series_detail(series_id: str, days: int = Query(365, ge=7, le=3650)):
    with connect() as con:
        s = service.series(con, series_id, days)
    if not s:
        raise HTTPException(404, "Série não encontrada")
    return s


@router.get("/focus")
def focus():
    with connect() as con:
        return service.focus(con)


@router.get("/tokens")
def tokens():
    with connect() as con:
        return service.tokens(con)


class InvestmentIn(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    months: int = Field(ge=1, le=120)
    pct_cdb: float = Field(100, gt=0, le=200)
    pct_lci: float = Field(90, gt=0, le=200)
    tr_monthly: float = Field(0, ge=0, le=5)
    cdi_aa: float | None = Field(None, gt=0, lt=100)
    selic_meta: float | None = Field(None, gt=0, lt=100)


class LoanIn(BaseModel):
    principal: float = Field(gt=0, le=1_000_000_000)
    months: int = Field(ge=1, le=480)
    rate_monthly_pct: float = Field(ge=0, le=30)
    system: str = Field("price", pattern="^(price|sac)$")
    upfront_fee: float = Field(0, ge=0)


@router.post("/simulate/investment")
def simulate_investment(body: InvestmentIn):
    with connect() as con:
        cdi, selic, mi = _inputs_or_409(con, body.cdi_aa, body.selic_meta)
    try:
        result = calc.simulate_investment(
            body.amount, body.months, cdi_aa=cdi, selic_meta=selic, pct_cdb=body.pct_cdb, pct_lci=body.pct_lci,
            tr_monthly=body.tr_monthly, ipca_12m=mi.get("ipca_12m"))
    except calc.CalcError as exc:
        raise HTTPException(422, str(exc)) from exc
    result["market_inputs"] = {**mi, "cdi_aa": cdi, "selic_meta": selic,
                               "overridden": body.cdi_aa is not None or body.selic_meta is not None}
    return result


@router.post("/simulate/loan")
def simulate_loan(body: LoanIn):
    try:
        result = calc.simulate_loan(body.principal, body.months, body.rate_monthly_pct, system=body.system,
                                    upfront_fee=body.upfront_fee)
    except calc.CalcError as exc:
        raise HTTPException(422, str(exc)) from exc
    with connect() as con:
        mi = service.market_inputs(con)
    if mi:
        selic_m = calc.annual_to_monthly_pct(mi["selic_meta"])
        result["market_context"] = {
            "selic_meta_aa": mi["selic_meta"], "selic_meta_monthly_pct": round(selic_m, 4),
            "spread_vs_selic_monthly_pp": round(body.rate_monthly_pct - selic_m, 4), "as_of": mi["as_of"],
            "note": "A Selic é referência de custo de captação, não a taxa média de crédito ao consumidor.",
        }
    return result


@router.post("/sync")
def sync(x_demo_role: str = Header("admin")):
    if x_demo_role != "admin":
        raise HTTPException(403, "Papel demo insuficiente. Permitidos: admin")
    with connect() as con:
        summary = store.sync(con)
    if summary["errors"] and not summary["series"]:
        raise HTTPException(502, f"Banco Central indisponível: {summary['errors']}")
    return summary
