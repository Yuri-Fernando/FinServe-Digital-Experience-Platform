"""Calculadoras financeiras puras (sem I/O): fáceis de testar e reutilizar fora da plataforma.

Simplificações documentadas (exibidas ao usuário em `assumptions`):
- 21 dias úteis por mês e base 252 para produtos indexados ao CDI.
- IR regressivo sobre o rendimento no resgate (22,5% / 20% / 17,5% / 15%); IOF ignorado (horizonte ≥ 1 mês).
- Poupança: regra vigente — 0,5% a.m. + TR se Selic meta > 8,5% a.a.; senão 70% da Selic + TR. TR informada pelo usuário.
- Inflação futura assumida igual ao IPCA acumulado em 12 meses (apenas para o retorno real ilustrativo).
Isto é uma simulação educacional, não recomendação de investimento nem proposta de crédito.
"""
from __future__ import annotations

from math import prod

DU_PER_MONTH = 21
DU_PER_YEAR = 252
IR_TABLE = ((180, 0.225), (360, 0.20), (720, 0.175), (10**9, 0.15))


class CalcError(ValueError):
    pass


def accumulate_pct(monthly_pct: list[float]) -> float:
    """Acumula variações percentuais mensais compostas. [1, 1] -> 2.01."""
    return (prod(1 + v / 100 for v in monthly_pct) - 1) * 100


def annual_to_monthly_pct(annual_pct: float) -> float:
    return ((1 + annual_pct / 100) ** (1 / 12) - 1) * 100


def monthly_to_annual_pct(monthly_pct: float) -> float:
    return ((1 + monthly_pct / 100) ** 12 - 1) * 100


def ir_rate(days: int) -> float:
    for limit, rate in IR_TABLE:
        if days <= limit:
            return rate
    return IR_TABLE[-1][1]


def _cdi_daily(cdi_aa_pct: float) -> float:
    return (1 + cdi_aa_pct / 100) ** (1 / DU_PER_YEAR) - 1


def _indexed_factor(cdi_aa_pct: float, pct_cdi: float, months: int, custody_aa_pct: float = 0.0) -> float:
    daily = _cdi_daily(cdi_aa_pct) * pct_cdi / 100
    factor = (1 + daily) ** (DU_PER_MONTH * months)
    if custody_aa_pct:
        factor *= (1 - custody_aa_pct / 100) ** (months / 12)
    return factor


def _poupanca_monthly(selic_meta_aa: float, tr_monthly_pct: float) -> float:
    if selic_meta_aa > 8.5:
        base = 0.5
    else:
        base = 0.7 * annual_to_monthly_pct(selic_meta_aa)
    return ((1 + base / 100) * (1 + tr_monthly_pct / 100) - 1) * 100


def _calendar_days(months: int) -> int:
    return round(months * 365 / 12)


def _product_row(key, label, amount, months, factor_fn, taxable, ipca_12m, note):
    gross_final = amount * factor_fn(months)
    gain = gross_final - amount
    rate = ir_rate(_calendar_days(months)) if taxable else 0.0
    ir = max(gain, 0.0) * rate
    net_final = gross_final - ir
    net_ret = net_final / amount - 1
    net_aa = ((1 + net_ret) ** (12 / months) - 1) * 100
    real = None
    if ipca_12m is not None:
        infl = (1 + ipca_12m / 100) ** (months / 12) - 1
        real = ((1 + net_ret) / (1 + infl) - 1) * 100
    schedule = []
    for m in range(1, months + 1):
        g = amount * factor_fn(m)
        t = (max(g - amount, 0.0) * ir_rate(_calendar_days(m))) if taxable else 0.0
        schedule.append(round(g - t, 2))
    return {
        "product": key,
        "label": label,
        "gross_final": round(gross_final, 2),
        "ir": round(ir, 2),
        "ir_rate_pct": round(rate * 100, 1),
        "net_final": round(net_final, 2),
        "net_gain": round(net_final - amount, 2),
        "net_return_pct": round(net_ret * 100, 3),
        "net_annual_pct": round(net_aa, 3),
        "real_return_pct": None if real is None else round(real, 3),
        "note": note,
        "schedule": schedule,
    }


def simulate_investment(
    amount: float,
    months: int,
    *,
    cdi_aa: float,
    selic_meta: float,
    pct_cdb: float = 100.0,
    pct_lci: float = 90.0,
    tesouro_custody_aa: float = 0.20,
    tr_monthly: float = 0.0,
    ipca_12m: float | None = None,
) -> dict:
    if not (amount > 0):
        raise CalcError("O valor aplicado deve ser positivo")
    if not (1 <= months <= 120):
        raise CalcError("O prazo deve estar entre 1 e 120 meses")
    if not (0 < cdi_aa < 100 and 0 < selic_meta < 100):
        raise CalcError("Taxas de mercado fora de faixa plausível")
    rows = [
        _product_row("cdb", f"CDB {pct_cdb:g}% do CDI", amount, months,
                     lambda m: _indexed_factor(cdi_aa, pct_cdb, m), True, ipca_12m,
                     "Tributado por IR regressivo no resgate."),
        _product_row("lci_lca", f"LCI/LCA {pct_lci:g}% do CDI", amount, months,
                     lambda m: _indexed_factor(cdi_aa, pct_lci, m), False, ipca_12m,
                     "Isento de IR para pessoa física; percentual do CDI é hipótese do usuário."),
        _product_row("tesouro_selic", "Tesouro Selic", amount, months,
                     lambda m: _indexed_factor(cdi_aa, 100.0, m, tesouro_custody_aa), True, ipca_12m,
                     f"≈100% do CDI com taxa de custódia B3 de {tesouro_custody_aa:g}% a.a.; sem ágio/deságio."),
        _product_row("poupanca", "Poupança", amount, months,
                     lambda m: (1 + _poupanca_monthly(selic_meta, tr_monthly) / 100) ** m, False, ipca_12m,
                     "Regra vigente da poupança; isenta de IR."),
    ]
    rows.sort(key=lambda r: r["net_final"], reverse=True)
    return {
        "inputs": {"amount": amount, "months": months, "cdi_aa": cdi_aa, "selic_meta": selic_meta,
                   "pct_cdb": pct_cdb, "pct_lci": pct_lci, "ipca_12m": ipca_12m},
        "products": rows,
        "assumptions": [
            f"{DU_PER_MONTH} dias úteis por mês, base {DU_PER_YEAR}; CDI constante no período.",
            "IR regressivo sobre o rendimento no resgate; IOF ignorado.",
            "Retorno real usa o IPCA de 12 meses como inflação futura (ilustrativo).",
            "Simulação educacional. Rentabilidade passada não garante rentabilidade futura.",
        ],
    }


def _irr_monthly(flows: list[float]) -> float:
    """Taxa interna de retorno mensal por bisseção (fluxo inicial negativo, demais positivos)."""

    def npv(rate: float) -> float:
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))

    lo, hi = 0.0, 1.0
    if npv(lo) < 0:
        raise CalcError("Fluxo inválido: soma das parcelas menor que o valor líquido recebido")
    while npv(hi) > 0:
        hi *= 2
        if hi > 1e3:
            raise CalcError("CET não converge")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def simulate_loan(
    principal: float,
    months: int,
    rate_monthly_pct: float,
    *,
    system: str = "price",
    upfront_fee: float = 0.0,
) -> dict:
    if not (principal > 0):
        raise CalcError("O valor financiado deve ser positivo")
    if not (1 <= months <= 480):
        raise CalcError("O prazo deve estar entre 1 e 480 meses")
    if not (0 <= rate_monthly_pct <= 30):
        raise CalcError("Taxa mensal fora da faixa 0–30%")
    if system not in ("price", "sac"):
        raise CalcError("Sistema deve ser 'price' ou 'sac'")
    if not (0 <= upfront_fee < principal):
        raise CalcError("Tarifa inicial deve ser ≥ 0 e menor que o valor financiado")
    i = rate_monthly_pct / 100
    balance = principal
    schedule = []
    if system == "price":
        pmt = principal / months if i == 0 else principal * i / (1 - (1 + i) ** -months)
    for n in range(1, months + 1):
        interest = balance * i
        if system == "price":
            amort = pmt - interest
            payment = pmt
        else:
            amort = principal / months
            payment = amort + interest
        balance = max(balance - amort, 0.0)
        schedule.append({"n": n, "payment": round(payment, 2), "interest": round(interest, 2),
                         "amortization": round(amort, 2), "balance": round(balance, 2)})
    total_paid = sum(r["payment"] for r in schedule)
    total_interest = sum(r["interest"] for r in schedule)
    flows = [-(principal - upfront_fee)] + [r["payment"] for r in schedule]
    cet_m = _irr_monthly(flows)
    return {
        "inputs": {"principal": principal, "months": months, "rate_monthly_pct": rate_monthly_pct,
                   "rate_annual_pct": round(monthly_to_annual_pct(rate_monthly_pct), 3),
                   "system": system, "upfront_fee": upfront_fee},
        "summary": {
            "first_payment": schedule[0]["payment"],
            "last_payment": schedule[-1]["payment"],
            "total_paid": round(total_paid, 2),
            "total_interest": round(total_interest, 2),
            "cost_over_principal_pct": round((total_paid / principal - 1) * 100, 2),
            "cet_monthly_pct": round(cet_m * 100, 4),
            "cet_annual_pct": round(monthly_to_annual_pct(cet_m * 100), 3),
        },
        "schedule": schedule,
        "assumptions": [
            "CET calculado como TIR do fluxo (valor líquido recebido × parcelas); inclui apenas a tarifa informada.",
            "IOF, seguros e demais encargos NÃO estão incluídos — o CET real de uma proposta é maior.",
            "Simulação educacional; não é proposta de crédito.",
        ],
    }
