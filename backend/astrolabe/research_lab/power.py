"""Power, minimum-detectable-effect and design-effect helpers for research-lab comparisons.

Everything is planning arithmetic on summary quantities; none of it changes a result.

Statistic. ``compare.paired_bootstrap`` resamples clusters and recomputes
``DeltaR2 = (SSE_b - SSE_a) / SSE_baseline`` (sign aside). Write ``d_k`` for the SSE difference
summed inside cluster k and ``c_k = K * d_k / SSE_baseline``; then DeltaR2 = mean(c_k) and, treating
the baseline SSE as fixed (delta method, first order), ``SE = sd_c / sqrt(K)``. ``sd_c``
(``sd_cluster_contrib`` below) is the SD of the per-cluster contribution to DeltaR2 in R2 units.

Assumptions (all of them approximations, none is verified here):
* ``sd_c`` stays constant as K grows (the same kind of clusters keep arriving).
* The mean of K cluster contributions is approximately normal (large K).
* Clusters are independent; time dependence between clusters is NOT modelled. Use
  ``per_period_test`` (time blocks) for that.
* Two-sided test at level alpha; the multiple-testing correction divides alpha by ``n_tests``.
  For Holm, the first (smallest p-value) step uses alpha/m, so planning for the ability to reject
  one hypothesis with certainty is identical to Bonferroni; Holm only helps later steps.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_N = NormalDist()
CORRECTIONS = ("none", "bonferroni", "holm")


def _alpha_adj(alpha: float, n_tests: int, correction: str) -> float:
    if correction not in CORRECTIONS:
        raise ValueError(f"correction must be one of {CORRECTIONS}")
    if n_tests < 1:
        raise ValueError("n_tests must be >= 1")
    return alpha if correction == "none" else alpha / n_tests


def adjust_pvalues(pvalues, method: str = "holm") -> np.ndarray:
    """Bonferroni or Holm step-down adjusted p-values (capped at 1)."""
    p = np.asarray(pvalues, float)
    m = len(p)
    if method == "bonferroni":
        return np.minimum(1.0, p * m)
    if method != "holm":
        raise ValueError("method must be 'bonferroni' or 'holm'")
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for rank, idx in enumerate(order):
        run = max(run, (m - rank) * p[idx])
        adj[idx] = min(1.0, run)
    return adj


# ---------------------------------------------------------------- design effect
def design_effect(
    cluster_ids,
    values,
    method: str = "sandwich",
    n_boot: int = 500,
    seed: int = 0,
) -> dict:
    """Variance inflation of the mean of ``values`` caused by clustering.

    ``values`` are per-row quantities whose mean is the statistic (e.g. per-row SSE difference
    between two models, or a residual). ``method``:
    * ``sandwich`` (default, analytical): cluster-robust variance of the mean divided by the iid
      variance, ``deff = N * sum_k S_k^2 / (N^2 s^2)`` with ``S_k = sum_{i in k}(x_i - mean)``.
    * ``bootstrap``: ratio of the cluster-bootstrap variance of the mean to the row-bootstrap
      (iid) variance, ``n_boot`` resamples each.
    ``icc_implied`` solves ``deff = 1 + (m_eff - 1) * icc`` with ``m_eff = sum m_k^2 / N``.
    ``n_effective = N / deff``. Estimates are noisy when K is small.
    """
    x = np.asarray(values, float)
    codes, uniq = pd.factorize(np.asarray(cluster_ids))
    n, k = len(x), len(uniq)
    if n != len(codes) or n < 2:
        raise ValueError("need matching ids and values, n >= 2")
    m = np.bincount(codes, minlength=k).astype(float)
    s = np.bincount(codes, weights=x, minlength=k)
    xbar = x.mean()
    s2 = x.var(ddof=1)
    m_eff = float((m**2).sum() / n)
    if s2 == 0.0:
        return {"deff": 1.0, "icc_implied": 0.0, "n": n, "n_clusters": k, "m_eff": m_eff,
                "n_effective": float(n), "method": method}
    if method == "sandwich":
        dev = s - m * xbar
        deff = float(n * (dev**2).sum() / (n**2 * s2))
    elif method == "bootstrap":
        rng = np.random.default_rng(seed)
        cl = np.empty(n_boot)
        iid = np.empty(n_boot)
        for b in range(n_boot):
            pick = rng.integers(0, k, size=k)
            cl[b] = s[pick].sum() / m[pick].sum()
            iid[b] = x[rng.integers(0, n, size=n)].mean()
        deff = float(cl.var(ddof=1) / iid.var(ddof=1))
    else:
        raise ValueError("method must be 'sandwich' or 'bootstrap'")
    icc = (deff - 1.0) / (m_eff - 1.0) if m_eff > 1.0 else 0.0
    return {"deff": deff, "icc_implied": float(icc), "n": n, "n_clusters": k,
            "m_eff": m_eff, "n_effective": float(n / deff), "method": method}


def cluster_contrib_sd(cluster_ids, sse_diff, sse_baseline_total: float | None = None) -> float:
    """SD of ``c_k = K * d_k / SSE_baseline``; ``sse_diff`` is per-row SSE_b - SSE_a.

    If the baseline total is not given, ``mean(row sse_diff)`` scaling cannot be recovered, so it
    is required in practice; pass the baseline SSE total from the same rows.
    """
    d = np.asarray(sse_diff, float)
    codes, uniq = pd.factorize(np.asarray(cluster_ids))
    if sse_baseline_total is None or sse_baseline_total <= 0:
        raise ValueError("sse_baseline_total must be positive")
    dk = np.bincount(codes, weights=d, minlength=len(uniq))
    return float(np.std(len(uniq) * dk / sse_baseline_total, ddof=1))


def sd_from_ci(ci_lo: float, ci_hi: float, n_clusters: int, level: float = 0.95) -> float:
    """Back out ``sd_c`` from a bootstrap interval: SE = width / (2 z), sd_c = SE * sqrt(K)."""
    z = _N.inv_cdf(0.5 + level / 2)
    return float((ci_hi - ci_lo) / (2 * z) * math.sqrt(n_clusters))


# ------------------------------------------------------------------- MDE / sizing
def _zsum(alpha: float, power: float, n_tests: int, correction: str) -> float:
    a = _alpha_adj(alpha, n_tests, correction)
    return _N.inv_cdf(1 - a / 2) + _N.inv_cdf(power)


def mde_delta_r2(
    n_clusters: int,
    sd_cluster_contrib: float,
    alpha: float = 0.05,
    power: float = 0.8,
    n_tests: int = 1,
    correction: str = "bonferroni",
) -> float:
    """Smallest true DeltaR2 detected with probability ``power`` (two-sided, normal approx)."""
    if n_clusters < 1:
        raise ValueError("n_clusters must be >= 1")
    return _zsum(alpha, power, n_tests, correction) * sd_cluster_contrib / math.sqrt(n_clusters)


def required_clusters(
    delta_r2: float,
    sd_cluster_contrib: float,
    alpha: float = 0.05,
    power: float = 0.8,
    n_tests: int = 1,
    correction: str = "bonferroni",
) -> int:
    """Clusters needed so that ``mde_delta_r2(K) <= delta_r2`` (inverse of the MDE)."""
    if delta_r2 <= 0:
        raise ValueError("delta_r2 must be positive")
    z = _zsum(alpha, power, n_tests, correction)
    k = max(1, math.ceil((z * sd_cluster_contrib / delta_r2) ** 2))
    while mde_delta_r2(k, sd_cluster_contrib, alpha, power, n_tests, correction) > delta_r2:
        k += 1  # guard against floating point at the boundary
    return k


# ------------------------------------------------------------- Student t (no scipy)
def _betacf(a: float, b: float, x: float) -> float:
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for mm in range(1, 300):
        m2 = 2 * mm
        aa = mm * (b - mm) * x / ((a + m2 - 1) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + mm) * (a + b + mm) * x / ((a + m2) * (a + m2 + 1))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """Student t CDF."""
    tail = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t > 0 else tail


def t_ppf(q: float, df: float) -> float:
    """Student t quantile by bisection on ``t_cdf``."""
    if not 0.0 < q < 1.0:
        raise ValueError("q must be in (0, 1)")
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def sign_test_pvalue(n_pos: int, n_neg: int) -> float:
    """Exact two-sided binomial sign test (zeros dropped by the caller)."""
    n = n_pos + n_neg
    if n == 0:
        return 1.0
    k = min(n_pos, n_neg)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def periods_needed(
    effect: float, sd_per_period: float, alpha: float = 0.05, power: float = 0.8, max_n: int = 1000
) -> int | None:
    """Independent periods for a one-sample t-test to detect mean ``effect`` (t-quantiles)."""
    if effect <= 0 or sd_per_period < 0:
        raise ValueError("effect must be positive and sd non-negative")
    for n in range(2, max_n + 1):
        crit = t_ppf(1 - alpha / 2, n - 1) + t_ppf(power, n - 1)
        if crit * sd_per_period / math.sqrt(n) <= effect:
            return n
    return None


def min_periods_sign_test(alpha: float = 0.05) -> int:
    """Fewest periods at which an all-same-sign outcome reaches two-sided ``alpha``."""
    n = 1
    while sign_test_pvalue(n, 0) > alpha:
        n += 1
    return n


def per_period_test(
    per_period_values, target_effect: float | None = None, alpha: float = 0.05, power: float = 0.8
) -> dict:
    """Inference across time blocks (one value per period, e.g. per-period DeltaR2).

    Assumptions: period values are independent and roughly normal (t-test); the sign test needs
    only independence and a common median. With few periods both have very little power:
    ``min_periods_sign_test`` reports the floor for the sign test. If ``target_effect`` is given,
    ``periods_needed`` is the count for the t-test at the OBSERVED SD (itself very uncertain when
    n is small).
    """
    v = np.asarray(per_period_values, float)
    v = v[~np.isnan(v)]
    n = len(v)
    out: dict = {"n_periods": n, "df": n - 1, "min_periods_sign_test": min_periods_sign_test(alpha)}
    if n == 0:
        return out
    n_pos, n_neg = int((v > 0).sum()), int((v < 0).sum())
    out.update(mean=float(v.mean()), n_pos=n_pos, n_neg=n_neg,
               sign_p=sign_test_pvalue(n_pos, n_neg))
    if n < 2:
        return out
    sd = float(v.std(ddof=1))
    se = sd / math.sqrt(n)
    crit = t_ppf(1 - alpha / 2, n - 1)
    t_stat = float(v.mean() / se) if se > 0 else float("inf") * np.sign(v.mean())
    p = 2 * (1 - t_cdf(abs(t_stat), n - 1)) if se > 0 else 0.0
    out.update(sd=sd, se=se, t_crit=crit, t_stat=t_stat, t_p=float(p),
               ci_lo=float(v.mean() - crit * se), ci_hi=float(v.mean() + crit * se))
    if target_effect is not None:
        out["periods_needed"] = periods_needed(target_effect, sd, alpha, power)
    return out
