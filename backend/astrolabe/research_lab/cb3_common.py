# ruff: noqa: E501
"""CB3 shared statistics (docs/research_lab/CREATIVE_BATCH_3.md §2.3): multi-way CR1 mean / ratio / slope tests with
p = max over the declared cluster ways, the CB2 small-G rule for the UTC-day way, cluster bootstrap CIs, the
top-clusters-dropped helper, and results/trial writing. Pure functions; no data access."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import battery as B
from . import cb3_declaration as D
from . import provenance
from .cb2_weather import small_g_pvalue


def _codes(cl) -> tuple[np.ndarray, int]:
    codes, uniq = pd.factorize(np.asarray(cl).astype(str))
    return codes, len(uniq)


def n_clusters(ways: dict[str, np.ndarray]) -> dict[str, int]:
    return {k: _codes(v)[1] for k, v in ways.items()}


def testable(n_units: int, ways: dict[str, np.ndarray], *, min_units: int = D.MIN_UNITS, min_clusters: int = D.MIN_CLUSTERS,
             small_g_ways: tuple[str, ...] = ()) -> tuple[bool, list[str]]:
    """>= ``min_units`` units; >= ``min_clusters`` clusters in each event-type way; the UTC-day way only needs the CB2
    small-G minimum (G >= 15), never the >= 30 rule (challenger item 9)."""
    why = []
    if n_units < min_units:
        why.append(f"units {n_units} < {min_units}")
    for k, g in n_clusters(ways).items():
        need = D.G_MIN if k in small_g_ways else min_clusters
        if g < need:
            why.append(f"{k} clusters {g} < {need}")
    return (not why), why


def _p_from_z(z: float, sign: int) -> float:
    return float(norm.sf(sign * z))


def mean_test(v, ways: dict[str, np.ndarray], *, sign: int = 1, w=None, small_g_ways: tuple[str, ...] = (),
              n_boot: int = D.N_BOOT, seed: int = D.SEED_BOOT, min_units: int = D.MIN_UNITS, min_clusters: int = D.MIN_CLUSTERS) -> dict:
    """Mean of per-unit values; one-sided p in ``sign`` = max over ways of CR1 (normal z); the small-G ways use the CB2
    rule (``cb2_weather.small_g_pvalue``). Not testable -> p = 1. CI by a cluster bootstrap over the first way."""
    v = np.asarray(v, float)
    n = len(v)
    ok, why = testable(n, ways, min_units=min_units, min_clusters=min_clusters, small_g_ways=small_g_ways)
    base = {"n": int(n), "mean": float(np.mean(v)) if n else math.nan, "clusters": n_clusters(ways)}
    if not ok:
        return {**base, "testable": False, "p": 1.0, "reason": why}
    wt = np.ones(n) if w is None else np.asarray(w, float)
    mu = float((wt * v).sum() / wt.sum())
    sc = wt * (v - mu) / wt.sum()
    ps: dict[str, float] = {}
    ses: dict[str, float] = {}
    for k, cl in ways.items():
        if k in small_g_ways and w is None:
            ps[k] = small_g_pvalue(v, cl, sign=sign)["p"]
            ses[k] = math.nan
            continue
        se = math.sqrt(B._cr_var_of_sum(sc, np.asarray(cl).astype(str)))
        ses[k] = se
        ps[k] = _p_from_z(mu / se if se > 0 else 0.0, sign)
    out = {**base, "testable": True, "mean": mu, "p": float(max(ps.values())), "p_by_way": ps, "se_by_way": ses, "weighted": w is not None}
    if n_boot:
        first = next(iter(ways.values()))
        out["ci95"] = boot_ci_mean(v, first, wt, n_boot, seed)
    return out


def boot_ci_mean(v, cl, wt, n_boot: int, seed: int) -> list[float]:
    codes, g = _codes(cl)
    S = np.bincount(codes, weights=wt * np.asarray(v, float), minlength=g)
    C = np.bincount(codes, weights=wt, minlength=g)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ S) / max(m @ C, 1e-12)
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def ratio_test(num, den, ways: dict[str, np.ndarray], *, null: float, sign: int = -1, n_boot: int = D.N_BOOT, seed: int = D.SEED_BOOT,
               min_units: int = D.A_MIN_ONSETS, min_clusters: int = D.MIN_CLUSTERS) -> dict:
    """Ratio of sums r = sum(num) / sum(den) with the delta-method CR1 SE per way (cluster-linearised). ``sign`` is the
    direction of H1 relative to ``null`` on r (-1: r < null). One-sided p = max over ways; CI by ``economics.boot_ratio``."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    n = len(num)
    ok, why = testable(n, ways, min_units=min_units, min_clusters=min_clusters)
    sd = float(den.sum())
    r = float(num.sum() / sd) if sd > 0 else math.nan
    base = {"n": int(n), "ratio": r, "clusters": n_clusters(ways)}
    if not ok or not sd > 0:
        return {**base, "testable": False, "p": 1.0, "reason": why or ["zero denominator"]}
    ps, ses = {}, {}
    lin = (num - r * den) / sd
    for k, cl in ways.items():
        se = math.sqrt(B._cr_var_of_sum(lin, np.asarray(cl).astype(str)))
        ses[k] = se
        z = (r - null) / se if se > 0 else 0.0
        ps[k] = float(norm.sf(sign * z))
    out = {**base, "testable": True, "p": float(max(ps.values())), "p_by_way": ps, "se_by_way": ses, "se": float(max(ses.values())), "sign_tested": sign}
    if n_boot:
        from . import economics

        first = np.asarray(next(iter(ways.values()))).astype(str)
        bb = economics.boot_ratio(first, num, den, n_boot=n_boot, seed=seed)
        out["ci95_ratio"] = bb["ci95_two_sided"]
        out["n_clusters_first_way"] = bb["n_clusters"]
    return out


def _partial(y: np.ndarray, Z1: np.ndarray, wt: np.ndarray | None) -> np.ndarray:
    if wt is None:
        c, *_ = np.linalg.lstsq(Z1, y, rcond=None)
        return y - Z1 @ c
    s = np.sqrt(wt)
    c, *_ = np.linalg.lstsq(Z1 * s[:, None], y * s, rcond=None)
    return y - Z1 @ c


def slope_test(y, x, Z, ways: dict[str, np.ndarray], *, sign: int, w=None, small_g_ways: tuple[str, ...] = (),
               n_boot: int = D.N_BOOT, seed: int = D.SEED_BOOT, min_units: int = D.MIN_UNITS, min_clusters: int = D.MIN_CLUSTERS) -> dict:
    """OLS slope of ``x`` on ``y`` given ``Z`` (intercept added; FWL), one-sided p in ``sign`` = max over ways of CR1
    (``bounce_decomp.fit_test`` generalised to arbitrary cluster ways). Non-finite rows are dropped. The small-G way uses
    the score-mean form of the CB2 rule (mean of w x~ y~ against 0). Reports ``se`` (max over ways) and ``mde_80``."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    Z = np.empty((len(y), 0)) if Z is None else np.asarray(Z, float).reshape(len(y), -1)
    fin = np.isfinite(y) & np.isfinite(x) & np.isfinite(Z).all(axis=1)
    if w is not None:
        fin &= np.isfinite(np.asarray(w, float))
    y, x, Z = y[fin], x[fin], Z[fin]
    wt = None if w is None else np.asarray(w, float)[fin]
    cl_f = {k: np.asarray(v)[fin] for k, v in ways.items()}
    n = len(y)
    ok, why = testable(n, cl_f, min_units=min_units, min_clusters=min_clusters, small_g_ways=small_g_ways)
    if not ok:
        return {"testable": False, "p": 1.0, "n": int(n), "reason": why, "clusters": n_clusters(cl_f)}
    Z1 = np.column_stack([np.ones(n), Z]) if Z.size else np.ones((n, 1))
    xt, yt = _partial(x, Z1, wt), _partial(y, Z1, wt)
    ww = np.ones(n) if wt is None else wt
    sxx = float((ww * xt**2).sum())
    if sxx <= 1e-12 * max(1, n):
        return {"testable": False, "p": 1.0, "n": int(n), "reason": ["no residual variation in x"]}
    b = float((ww * xt * yt).sum() / sxx)
    e = yt - b * xt
    sc = ww * xt * e / sxx
    k = Z1.shape[1] + 1
    adj = (n - 1) / max(n - k, 1)
    ps, ses = {}, {}
    for kway, cl in cl_f.items():
        cs = np.asarray(cl).astype(str)
        se = math.sqrt(B._cr_var_of_sum(sc, cs) * adj)
        ses[kway] = se
        if kway in small_g_ways and wt is None:
            ps[kway] = small_g_pvalue(xt * yt, cs, sign=sign)["p"]
        else:
            ps[kway] = _p_from_z(b / se if se > 0 else 0.0, sign)
    se_max = float(max(ses.values()))
    out = {"testable": True, "beta": b, "se": se_max, "se_by_way": ses, "p": float(max(ps.values())), "p_by_way": ps, "n": int(n),
           "mde_80": 2.8 * se_max, "clusters": n_clusters(cl_f), "weighted": wt is not None, "sign_tested": sign}
    if n_boot:
        codes, g = _codes(next(iter(cl_f.values())))
        A = np.bincount(codes, weights=ww * xt * yt, minlength=g)
        Bq = np.bincount(codes, weights=ww * xt * xt, minlength=g)
        rng = np.random.default_rng(seed)
        bs = np.empty(n_boot)
        for i in range(n_boot):
            m = np.bincount(rng.integers(0, g, g), minlength=g)
            bs[i] = (m @ A) / max(m @ Bq, 1e-18)
        out["ci95"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    return out


def top_clusters_mask(contrib, cl, k: int = D.TOP_CLUSTERS_DROPPED) -> np.ndarray:
    """True for rows NOT in the ``k`` clusters with the largest |sum of contrib| (robustness (i), per declared way)."""
    s = pd.Series(np.asarray(contrib, float)).groupby(np.asarray(cl).astype(str)).sum()
    drop = set(s.abs().sort_values(ascending=False).index[:k])
    return ~np.isin(np.asarray(cl).astype(str), list(drop))


def sign_agree(a: float, b: float) -> bool:
    return bool(np.isfinite(a) and np.isfinite(b) and a != 0 and np.sign(a) == np.sign(b))


def placebo_summary(vals: list[float]) -> dict:
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    if not len(v):
        return {"n_draws": 0, "testable": False}
    lo, hi = (float(x) for x in np.percentile(v, [2.5, 97.5]))
    return {"n_draws": int(len(v)), "testable": True, "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else math.nan,
            "range_2_5_97_5": [lo, hi], "covers_zero": bool(lo <= 0.0 <= hi), "draws": [float(x) for x in v]}


def reading(placebo: dict, real_se: float, *, void_applies: bool = True) -> dict:
    """J4-R reading rule: void if the 2.5-97.5% range does not cover 0; inconclusive (placebo bias) if
    |mean placebo| > 0.5 x the real max-SE; else read."""
    if not placebo.get("testable"):
        return {"status": "VOID (placebo untestable)", "family_void": True}
    if void_applies and not placebo["covers_zero"]:
        return {"status": "VOID (placebo range does not cover 0)", "family_void": True}
    if real_se is None or not np.isfinite(real_se) or real_se <= 0:
        return {"status": "inconclusive (real SE unavailable)", "family_void": False}
    if void_applies and abs(placebo["mean"]) > D.PLACEBO_BIAS_FRAC * real_se:
        return {"status": "inconclusive (placebo bias)", "family_void": False, "bias_ratio": abs(placebo["mean"]) / real_se}
    return {"status": "read", "family_void": False}


# ---- results and trials ----------------------------------------------------------------------------------------


def _jsonable(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, set | tuple):
        return list(o)
    if isinstance(o, float) and not math.isfinite(o):
        return None
    raise TypeError(type(o))


def write_new(path: Path, obj) -> str:
    """Results are never overwritten (exclusive create). Returns the file sha256."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, default=_jsonable)
        fh.write("\n")
    return provenance.sha256_file(path)


def log_trials(job: str, tests: dict[str, dict], *, kind: str, role: str, dataset: str, results_path: str, results_sha256: str,
               decl_sha: str, cumulative: dict | None = None, placebo: dict[str, dict] | None = None,
               descriptive: dict[str, dict] | None = None, trials_path: Path = provenance.TRIALS_PATH, cuts_sha256: str | None = None) -> list[dict]:
    """One line per counted test (``cb3_test`` / ``cb3_replication`` / ``cb3_prospective``), one summary placebo line per
    test (count 0), one ``cb3_descriptive`` line per descriptive item, and one ``ml_explain`` count line
    (``creative_batch_3:<job>``, ``n_tests``)."""
    if kind not in D.TRIAL_KINDS[:3]:
        raise ValueError(kind)
    prov = provenance.run_provenance()
    written = []
    for name, t in tests.items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": name, "label": D.LABEL, "kind": kind, "evidence_role": role,
            "revision": D.VERSION, "result_path": results_path, "results_sha256": results_sha256, "declaration_sha256": decl_sha, "frozen_cuts_sha256": cuts_sha256,
            "cumulative_count_at_run": cumulative,
            "summary": {k: t.get(k) for k in ("effect", "p", "n", "advance", "testable", "placebo_status", "replicated", "family_status")},
            "provenance": prov}, trials_path))
    for name, p in (placebo or {}).items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": f"{name}:placebo", "label": D.LABEL, "kind": kind, "evidence_role": "placebo",
            "revision": D.VERSION, "result_path": results_path, "results_sha256": results_sha256, "declaration_sha256": decl_sha, "frozen_cuts_sha256": cuts_sha256,
            "summary": {k: p.get(k) for k in ("n_draws", "mean", "sd", "range_2_5_97_5", "covers_zero", "status")}}, trials_path))
    for name, d in (descriptive or {}).items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": name, "label": D.LABEL, "kind": D.KIND_DESCRIPTIVE, "evidence_role": role,
            "revision": D.VERSION, "result_path": results_path, "results_sha256": results_sha256, "declaration_sha256": decl_sha, "frozen_cuts_sha256": cuts_sha256,
            "summary": d}, trials_path))
    written.append(provenance.append_trial({
        "dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY", "n_tests": len(tests),
        "revision": D.VERSION, "source": f"creative_batch_3:{job}", "results_sha256": results_sha256, "declaration_sha256": decl_sha, "frozen_cuts_sha256": cuts_sha256,
        "note": "CB3 count line; per-test cb3_* lines are EXCLUDEd in battery2.KIND_RULES"}, trials_path))
    return written


# ---- Stage-2 family and batch Holm ---------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict] = {}
    running, rejecting = 0.0, True
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        rejecting = rejecting and (p <= alpha / (m - i))
        out[k] = {"p": p, "p_holm": running, "reject": bool(rejecting)}
    return out


def stage2_expected(s1_a: dict | None, s1_b: dict | None) -> list[str]:
    """Tests that reach Stage 2: A1 / A2 if they advanced, A3 iff A1 advanced; every B test that advanced or entered by the
    entry exception (not testable on h2 by counts)."""
    if s1_a is None or s1_b is None:
        raise D.Cb3Error("both Stage-1 result files (S1_A and S1_B) are required: a missing file would silently lower k")
    out: list[str] = []
    if s1_a:
        t = s1_a.get("tests", {})
        out += [k for k in ("A1", "A2") if t.get(k, {}).get("advance")]
        if t.get("A1", {}).get("advance"):
            out.append("A3")
    if s1_b:
        t = s1_b.get("tests", {})
        out += [k for k in D.FAMILY_TESTS["B"] if t.get(k, {}).get("advance") or t.get(k, {}).get("entry_exception_stage2")]
    return out


def batch_holm(stage2_docs: list[tuple[str, dict]], expected: list[str], alpha: float = D.ALPHA_STAGE2) -> dict:
    """Holm over every CB3 test that reached Stage 2 (k <= 9). A test with no Stage-2 result counts as p = 1. A test is
    ``replicated`` only if its own Stage-2 gate passed (``advance``) AND the batch Holm rejects. A test id may appear once."""
    pv: dict[str, dict] = {}
    for name, doc in stage2_docs:
        for tid, t in doc.get("tests", {}).items():
            if tid not in expected:
                raise D.Cb3Error(f"{name}: test {tid} is not in the Stage-2 family {sorted(expected)}")
            if tid in pv:
                raise D.Cb3Error(f"test {tid} appears in both {pv[tid]['source']} and {name}")
            pv[tid] = {"p": float(t.get("p", 1.0)), "advance": bool(t.get("advance")), "source": name}
    missing = sorted(set(expected) - set(pv))
    for tid in missing:
        pv[tid] = {"p": 1.0, "advance": False, "source": "missing_stage2_p=1"}
    hm = holm({k: v["p"] for k, v in pv.items()}, alpha) if pv else {}
    tests = {k: {**pv[k], **hm[k], "replicated": bool(pv[k]["advance"] and hm[k]["reject"])} for k in sorted(pv)}
    return {"m": len(pv), "alpha": alpha, "tests": tests, "replicated": sorted(k for k, v in tests.items() if v["replicated"]),
            "expected_family": sorted(expected), "missing_stage2_counted_p1": missing}
