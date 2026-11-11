from datetime import date

import pytest

from finserve.app import bootstrap
from finserve import registry
from finserve.db import connect
from finserve.modules.market import bcb, store

TODAY = date(2026, 11, 10)


def test_parse_sgs_drops_future_points_and_sorts():
    payload = [{"data": "09/11/2026", "valor": "13,65"}, {"data": "08/12/2026", "valor": "13.75"},
               {"data": "05/11/2026", "valor": "14.00"}]
    assert bcb.parse_sgs(payload, TODAY) == [("2026-11-05", 14.0), ("2026-11-09", 13.65)]


@pytest.mark.parametrize("bad", [{"data": "x"}, "texto", [{"data": "32/13/2026", "valor": "1"}], [{"data": "01/01/2026", "valor": "abc"}]])
def test_parse_sgs_rejects_malformed(bad):
    with pytest.raises(bcb.BcbError):
        bcb.parse_sgs(bad, TODAY)


def test_focus_url_and_parse():
    url = bcb.focus_url("Câmbio", date(2026, 10, 1))
    assert "ExpectativasMercadoAnuais" in url and "%24" not in url and " " not in url and "C%C3%A2mbio" in url
    rows = bcb.parse_focus({"value": [{"Indicador": "Selic", "DataReferencia": "2026", "Data": "2026-11-06", "Mediana": 13.75,
                                       "Media": 13.6, "DesvioPadrao": .2, "Minimo": 13.25, "Maximo": 14, "numeroRespondentes": 144}]})
    assert rows[0]["median"] == 13.75 and rows[0]["respondents"] == 144
    with pytest.raises(bcb.BcbError):
        bcb.parse_focus({"oops": 1})


def test_catalog_has_unique_ids_and_codes():
    assert len({s["id"] for s in bcb.SERIES}) == len(bcb.SERIES) == len({s["sgs"] for s in bcb.SERIES})
    assert bcb.SERIES_BY_ID["inadimplencia_total"]["sgs"] == 21082  # total, não PF
    assert bcb.SERIES_BY_ID["inadimplencia_pf"]["sgs"] == 21084


def _stub(fail_code=None):
    def fetch(url):
        if "olinda" in url:
            return {"value": [{"Indicador": "Selic", "DataReferencia": "2026", "Data": "2026-11-06", "Mediana": 13.75,
                               "Media": 13.7, "DesvioPadrao": .1, "Minimo": 13.5, "Maximo": 14, "numeroRespondentes": 10}]}
        code = int(url.split("sgs.")[1].split("/")[0])
        if code == fail_code:
            raise bcb.BcbError("timeout simulado")
        return [{"data": "09/11/2026", "valor": "1.5"}, {"data": "01/12/2026", "valor": "9.9"}]
    return fetch


def _con_ctx():
    bootstrap(registry.load(["platform", "market"]))
    return connect()


def test_sync_isolates_per_series_failure_and_logs():
    with _con_ctx() as con:
        con.execute("DELETE FROM market_observations")
        con.execute("DELETE FROM market_expectations")
        s = store.sync(con, fetch=_stub(fail_code=433), today=TODAY)
        assert "ipca_mensal" in s["errors"] and "selic_meta" in s["series"]
        assert con.execute("SELECT COUNT(*) FROM market_observations WHERE series_id='ipca_mensal'").fetchone()[0] == 0
        assert con.execute("SELECT MAX(obs_date) FROM market_observations").fetchone()[0] == "2026-11-09"  # futuro descartado
        assert con.execute("SELECT COUNT(*) FROM market_sync_log WHERE status='error'").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM market_expectations").fetchone()[0] == 1


def test_sync_is_idempotent():
    with _con_ctx() as con:
        con.execute("DELETE FROM market_observations")
        store.sync(con, fetch=_stub(), today=TODAY)
        n1 = con.execute("SELECT COUNT(*) FROM market_observations").fetchone()[0]
        store.sync(con, fetch=_stub(), today=TODAY)
        assert con.execute("SELECT COUNT(*) FROM market_observations").fetchone()[0] == n1


def test_snapshot_not_written_when_incomplete(tmp_path):
    with pytest.raises(bcb.BcbError):
        store.write_snapshot(fetch=_stub(fail_code=432), today=TODAY, directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_snapshot_roundtrip(tmp_path):
    info = store.write_snapshot(fetch=_stub(), today=TODAY, directory=tmp_path)
    assert info["series"]["selic_meta"] == 1
    with _con_ctx() as con:
        con.execute("DELETE FROM market_observations")
        out = store.load_snapshot(con, tmp_path)
        assert out["series"]["cdi_anual"] == 1
