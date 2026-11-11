"""Estatística pura (stdlib): detecção robusta de anomalias, teste A/B de duas proporções, tamanho de amostra."""
from __future__ import annotations

from math import sqrt
from statistics import NormalDist, median

_N = NormalDist()

# Core Web Vitals (web.dev): (bom até, ruim a partir de)
CWV_THRESHOLDS = {"lcp": (2500, 4000), "inp": (200, 500), "cls": (0.1, 0.25)}


def cwv_status(metric: str, value: float) -> str:
    good, poor = CWV_THRESHOLDS[metric]
    if value <= good:
        return "good"
    return "poor" if value > poor else "needs-improvement"


def percentile(values: list[float], p: float) -> float:
    """Percentil por interpolação linear (p em 0–100)."""
    if not values:
        raise ValueError("lista vazia")
    xs = sorted(values)
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def modified_z(values: list[float]) -> list[float]:
    """Escore z modificado de Iglewicz–Hoaglin: 0,6745·(x − mediana)/MAD. |z| ≥ 3,5 sugere outlier."""
    if len(values) < 3:
        return [0.0] * len(values)
    med = median(values)
    mad = median(abs(v - med) for v in values)
    if mad == 0:
        meanad = sum(abs(v - med) for v in values) / len(values)
        if meanad == 0:
            return [0.0] * len(values)
        return [(v - med) / (1.253314 * meanad) for v in values]
    return [0.6745 * (v - med) / mad for v in values]


def two_proportion_ztest(x1: int, n1: int, x2: int, n2: int, alpha: float = 0.05) -> dict:
    """Teste z bicaudal para diferença de proporções (controle=1, variante=2); IC 95% com erro padrão não agrupado."""
    if min(n1, n2) <= 0 or not (0 <= x1 <= n1) or not (0 <= x2 <= n2):
        raise ValueError("amostras inválidas")
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = 0.0 if se_pooled == 0 else (p2 - p1) / se_pooled
    p_value = 2 * (1 - _N.cdf(abs(z)))
    se = sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    zc = _N.inv_cdf(1 - alpha / 2)
    diff = p2 - p1
    return {
        "p_control": p1, "p_variant": p2, "diff": diff,
        "lift_pct": None if p1 == 0 else diff / p1 * 100,
        "z": z, "p_value": p_value,
        "ci95": (diff - zc * se, diff + zc * se),
        "significant": p_value < alpha,
    }


def sample_size_per_variant(p_base: float, mde_rel: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Visitantes necessários por variante para detectar um efeito relativo `mde_rel` (ex.: 0,10 = +10%)."""
    if not (0 < p_base < 1) or mde_rel <= 0:
        raise ValueError("parâmetros inválidos")
    p2 = p_base * (1 + mde_rel)
    if p2 >= 1:
        raise ValueError("efeito leva a proporção ≥ 1")
    zb = _N.inv_cdf(1 - alpha / 2)
    zp = _N.inv_cdf(power)
    pbar = (p_base + p2) / 2
    num = (zb * sqrt(2 * pbar * (1 - pbar)) + zp * sqrt(p_base * (1 - p_base) + p2 * (1 - p2))) ** 2
    return int(num / (p2 - p_base) ** 2) + 1
