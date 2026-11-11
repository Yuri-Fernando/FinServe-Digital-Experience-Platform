import pytest

from finserve.modules.market import calculators as c


def test_accumulate_pct_compound():
    assert c.accumulate_pct([1, 1]) == pytest.approx(2.01)
    assert c.accumulate_pct([]) == pytest.approx(0.0)


def test_rate_conversions_roundtrip():
    assert c.monthly_to_annual_pct(c.annual_to_monthly_pct(13.65)) == pytest.approx(13.65)


@pytest.mark.parametrize("days,rate", [(1, .225), (180, .225), (181, .20), (360, .20), (361, .175), (720, .175), (721, .15), (5000, .15)])
def test_ir_regressive_table(days, rate):
    assert c.ir_rate(days) == rate


def _by(result):
    return {p["product"]: p for p in result["products"]}


def test_poupanca_uses_half_percent_per_month_when_selic_above_8_5():
    r = _by(c.simulate_investment(1000, 12, cdi_aa=13.65, selic_meta=13.75))
    assert r["poupanca"]["net_final"] == pytest.approx(1000 * 1.005 ** 12, abs=0.01)
    assert r["poupanca"]["ir"] == 0


def test_poupanca_uses_70_percent_selic_when_selic_low():
    r = _by(c.simulate_investment(1000, 12, cdi_aa=8.0, selic_meta=8.0))
    expected = 1000 * (1 + 0.7 * c.annual_to_monthly_pct(8.0) / 100) ** 12
    assert r["poupanca"]["net_final"] == pytest.approx(expected, abs=0.01)


def test_cdb_gross_matches_cdi_over_252_business_days():
    r = _by(c.simulate_investment(1000, 12, cdi_aa=13.65, selic_meta=13.75, pct_cdb=100))
    assert r["cdb"]["gross_final"] == pytest.approx(1000 * 1.1365, abs=0.01)  # 252 dias úteis ≈ 1 ano
    assert r["cdb"]["ir_rate_pct"] == 17.5  # 12 meses ≈ 365 dias
    assert r["cdb"]["net_final"] == pytest.approx(1000 + 136.5 * (1 - .175), abs=0.05)


def test_lci_is_tax_free_and_sorted_by_net_final():
    res = c.simulate_investment(10000, 24, cdi_aa=13.65, selic_meta=13.75, pct_lci=95)
    p = _by(res)
    assert p["lci_lca"]["ir"] == 0
    finals = [x["net_final"] for x in res["products"]]
    assert finals == sorted(finals, reverse=True)
    assert len(p["cdb"]["schedule"]) == 24


def test_real_return_negative_when_inflation_above_nominal():
    r = _by(c.simulate_investment(1000, 12, cdi_aa=5.0, selic_meta=5.0, ipca_12m=9.0))
    assert r["poupanca"]["real_return_pct"] < 0
    none = _by(c.simulate_investment(1000, 12, cdi_aa=5.0, selic_meta=5.0))
    assert none["cdb"]["real_return_pct"] is None


@pytest.mark.parametrize("kw", [dict(amount=0, months=12), dict(amount=1000, months=0), dict(amount=1000, months=121)])
def test_investment_validation(kw):
    with pytest.raises(c.CalcError):
        c.simulate_investment(**kw, cdi_aa=13, selic_meta=13)


def test_price_payment_matches_closed_form():
    r = c.simulate_loan(10000, 12, 2.0)
    assert r["summary"]["first_payment"] == pytest.approx(945.60, abs=0.01)
    assert r["summary"]["last_payment"] == r["summary"]["first_payment"]
    assert r["schedule"][-1]["balance"] == pytest.approx(0, abs=0.05)
    assert r["summary"]["total_paid"] == pytest.approx(945.596 * 12, abs=0.2)


def test_sac_first_payment_and_decreasing():
    r = c.simulate_loan(12000, 12, 2.0, system="sac")
    assert r["summary"]["first_payment"] == pytest.approx(1000 + 240, abs=0.01)
    pays = [x["payment"] for x in r["schedule"]]
    assert pays == sorted(pays, reverse=True)
    assert sum(x["amortization"] for x in r["schedule"]) == pytest.approx(12000, abs=0.1)


def test_cet_equals_rate_without_fee_and_higher_with_fee():
    base = c.simulate_loan(10000, 24, 2.0)
    assert base["summary"]["cet_monthly_pct"] == pytest.approx(2.0, abs=0.01)
    fee = c.simulate_loan(10000, 24, 2.0, upfront_fee=300)
    assert fee["summary"]["cet_monthly_pct"] > base["summary"]["cet_monthly_pct"]


def test_zero_rate_loan():
    r = c.simulate_loan(1200, 12, 0.0)
    assert r["summary"]["total_interest"] == 0 and r["summary"]["cet_monthly_pct"] == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("kw", [dict(principal=0, months=12, rate_monthly_pct=1), dict(principal=1000, months=12, rate_monthly_pct=31),
                                dict(principal=1000, months=12, rate_monthly_pct=1, system="x"),
                                dict(principal=1000, months=12, rate_monthly_pct=1, upfront_fee=1000)])
def test_loan_validation(kw):
    with pytest.raises(c.CalcError):
        c.simulate_loan(**kw)
