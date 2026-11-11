from __future__ import annotations

import csv
import io
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...db import connect, rows
from . import service

router = APIRouter()
Segment = Literal["all", "investidor", "credito", "jovem"]


@router.get("/filters")
def filters():
    with connect() as con:
        return {"campaigns": rows(con, "SELECT id,slug,name,channel,product,audience,state FROM campaigns ORDER BY id"),
                "segments": list(service.SEGMENTS), "date_range": [7, 14, 30, 60, 90, 120]}


@router.get("/dashboard")
def dashboard(days: int = Query(30, ge=7, le=120), segment: Segment = "all"):
    with connect() as con:
        return service.dashboard(con, days, segment)


@router.get("/anomalies")
def anomalies(days: int = Query(30, ge=7, le=90), lookback: int = Query(90, ge=30, le=120),
              threshold: float = Query(3.5, ge=2.0, le=10.0)):
    with connect() as con:
        return service.anomalies(con, days, lookback, threshold)


@router.get("/pacing")
def pacing():
    with connect() as con:
        return service.pacing(con)


@router.get("/experiments")
def experiments():
    with connect() as con:
        return {"items": service.experiments(con), "kind": "synthetic"}


@router.get("/experiments/{key}")
def experiment(key: str, mde: float = Query(0.10, gt=0, le=1)):
    with connect() as con:
        e = service.experiment(con, key, mde)
    if not e:
        raise HTTPException(404, "Experimento não encontrado")
    return e


@router.get("/export.csv")
def export_csv(days: int = Query(30, ge=7, le=120), segment: Segment = "all"):
    with connect() as con:
        data = service.dashboard(con, days, segment)["campaigns"]
    cols = ["name", "channel", "product", "audience", "state", "impressions", "clicks", "leads", "approvals",
            "spend", "revenue", "ctr_pct", "cpl", "roas"]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    w.writerow(cols)
    for r in data:
        w.writerow([r[c] for c in cols])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="finserve-campanhas-sinteticas.csv"'})
