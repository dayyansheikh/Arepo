# ruff: noqa: E501
"""Screening Batch 2 jobs J4 (snapshot bounce decomposition) and J3 (pmxt book decomposition).

Spec: docs/research_lab/SCREENING_BATCH_2.md sections J3 and J4 (and section 2, common rules).
Exploratory development screens, NOT evidence; no edge claim. Nothing here fits on or reads a
target capture as a feature: every feature column comes from the origin capture ``i`` (or the
previous capture ``h`` for the J4 quote changes); capture ``j`` supplies target columns only.

J4 triples ``(h, i, j)`` are consecutive complete captures with gap(h,i) and gap(i,j) in
[1.5, 3] h (by manifest start time). At most three captures are in memory at once.

Conventions / readings of the spec (also listed in the run report):
* "rejects" = Holm-adjusted two-sided p < 0.05 with p = max(event-clustered, two-way event x
  period). Labels that name a *reversal* (P1, P1x, P3, B1, B2, B4) additionally need a negative
  estimate; a positive rejection is reported as anomalous and not as the labelled mechanism.
* "equivalent to 0 within band" = the 90% normal CI (SE = max of the two SEs) lies inside the band.
* "95% CI" for the verdict map is the 2,000-draw event-cluster bootstrap CI of ``battery.beta_test``.
* Missing ``b_pos`` / ``chg_1h`` as controls are 0-filled with a missing flag (rows are kept).
* Gamma ``last_trade_price <= 0`` is treated as "no last trade".
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import battery2, forecast, panel, provenance

SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
HIST_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "history"
OUT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "bounce_decomp"
LABEL = "DEVELOPMENT bounce decomposition (SB2)"
KIND_J4, KIND_J3 = "bounce_decomp", "book_decomp"
GAP_LO_H, GAP_HI_H = 1.5, 3.0
SWEEP_MAX_LAG_MIN = 20.0
ALPHA = 0.05
TOST_SLOPE_BAND = 0.05
TOST_BPOS_HS_FRAC = 0.1
MIN_BOOK_ROWS, MIN_BOOK_EVENTS = 2000, 100
H6 = 6 * 3600.0
Z90 = 1.6448536269514722

SNAP_USECOLS = [
    "market_id", "event_id", "received_utc", "best_bid", "best_ask", "spread", "last_trade_price",
    "chg_1h", "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date", "closed", "active",
    "binary",
]  # chg_1d / chg_1w are read only because panel.build_pair's registered B3 set needs them
_FLOAT_COLS = ["best_bid", "best_ask", "spread", "last_trade_price", "chg_1h", "chg_1d", "chg_1w",
               "liquidity", "volume24hr"]

# Columns that are features/controls (origin side) versus targets (capture j / book at t+6h).
J4_FEATURES = ("mid_i", "mid_h", "spread", "chg_1h", "chg_1h_missing", "b_pos", "b_pos0",
               "b_pos_missing", "d_bm", "d_bid", "d_ask", "w", "d_bm_x_w", "volume24hr_i",
               "volume24hr_h", "volume_up", "liquidity_i", "B_i", "sweep_lag_min", "ltp_i",
               "ltp_h", "bid_h", "ask_h")
J4_TARGETS = ("mid_j", "bid_j", "ask_j", "dmid", "y_p1x", "y_far_bid", "y_far_ask")


def assert_origin_only(feature_names) -> None:
    bad = set(feature_names) & set(J4_TARGETS)
    if bad:
        raise ValueError(f"target-side columns refused as features: {sorted(bad)}")


assert_origin_only(J4_FEATURES)


# =============================================================================================
# Statistics
# =============================================================================================


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (monotone, capped at 1). NaN counts as 1."""
    items = sorted(((k, 1.0 if v is None or not np.isfinite(v) else float(v))
                    for k, v in pvals.items()), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, float] = {}
    run = 0.0
    for r, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - r) * p))
        out[k] = run
    return {k: out[k] for k in pvals}


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


Z95 = 1.959963984540054


def _hull(ci_boot, beta, se, z) -> tuple[tuple[float, float], tuple[str, str]]:
    """Conservative interval for bound/absence clauses: hull of the bootstrap CI and
    beta +/- z * se (se = max(se_event, se_twoway)). Returns ((lo, hi), (binding_lo, binding_hi))."""
    nlo, nhi = (beta - z * se, beta + z * se) if se is not None and beta is not None else (None, None)
    blo, bhi = (ci_boot if ci_boot else (None, None))
    lo_c = [(v, k) for v, k in ((blo, "bootstrap"), (nlo, "normal_max_se")) if v is not None]
    hi_c = [(v, k) for v, k in ((bhi, "bootstrap"), (nhi, "normal_max_se")) if v is not None]
    lo, klo = min(lo_c)
    hi, khi = max(hi_c)
    return (lo, hi), (klo, khi)


def cons_ci(t: dict, level: int = 95) -> tuple[tuple[float, float], tuple[str, str]]:
    """Conservative interval of a ``fit_test`` result (95: hull of bootstrap and normal max-SE;
    90: normal with max(se_event, se_twoway), already the conservative one)."""
    if level == 90:
        return (t["ci90"][0], t["ci90"][1]), ("normal_max_se", "normal_max_se")
    return _hull(t.get("ci95"), t.get("beta"), t.get("se"), Z95)


def fit_test(y, x, Z, ev, per, n_boot: int, seed: int) -> dict:
    """OLS slope of x given Z with event-clustered and two-way (event x period) SEs.

    p (two-sided) = max over the two clusterings (normal z). CI95 = event-cluster bootstrap of
    ``battery.beta_test``; ``ci95_cons`` = hull of that and beta +/- 1.96 max-SE (used for every
    bound/absence clause); CI90 (TOST) is normal with SE = max(se_event, se_twoway)."""
    from . import battery

    y, x = np.asarray(y, float), np.asarray(x, float)
    if len(y) == 0:
        return {"testable": False, "p": 1.0, "n": 0, "reason": "no rows"}
    Z = np.asarray(Z, float).reshape(len(y), -1) if Z is not None else np.empty((len(y), 0))
    r = battery.beta_test(y, x, Z, np.asarray(ev), np.asarray(per).astype(str), None,
                          n_boot=n_boot, seed=seed)
    if not r.get("testable"):
        return {"testable": False, "p": 1.0, "n": int(len(y)), "reason": r.get("reason")}
    b = r["beta"]
    se = max(r["se_event"], r["se_twoway"])
    p2 = max(r["p_two_sided_event"], float(2 * norm.sf(abs(r["z_twoway"]))))
    return {
        "testable": True, "beta": b, "se_event": r["se_event"], "se_twoway": r["se_twoway"],
        "se": se, "p": p2, "n": r["n"], "n_event": r["n_event"], "n_period": r["n_day"],
        "ci95": r["ci_event_boot"], "ci90": [b - Z90 * se, b + Z90 * se],
        "ci95_cons": list(_hull(r["ci_event_boot"], b, se, Z95)[0]),
        "mde_80": 2.8 * se,
    }


def _design(x, Z) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x, Z]) if Z.size else np.column_stack([np.ones(len(x)), x])


def lodo(y, x, Z, day, full_beta: float) -> dict:
    """Leave-one-UTC-day-out slope of x given Z (exact, via per-day normal-equation sums)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    Z = np.asarray(Z, float).reshape(len(y), -1) if Z is not None else np.empty((len(y), 0))
    days = pd.unique(day)
    if len(days) < 2:
        return {"days": [str(d) for d in days], "betas": {}, "sign_stable": False,
                "note": "fewer than 2 UTC days: leave-one-day-out impossible"}
    X = _design(x, Z)
    k = X.shape[1]
    codes, uniq = pd.factorize(pd.Series(day))
    xtx = np.zeros((len(uniq), k, k))
    xty = np.zeros((len(uniq), k))
    for g in range(len(uniq)):
        m = codes == g
        Xg = X[m]
        xtx[g] = Xg.T @ Xg
        xty[g] = Xg.T @ y[m]
    tot_a, tot_b = xtx.sum(0), xty.sum(0)
    betas = {}
    for g, d in enumerate(uniq):
        coef, *_ = np.linalg.lstsq(tot_a - xtx[g], tot_b - xty[g], rcond=None)
        betas[str(d)] = float(coef[1])
    sgn = np.sign(full_beta)
    stable = bool(sgn != 0 and all(np.sign(b) == sgn for b in betas.values()))
    return {"days": list(betas), "betas": betas, "sign_stable": stable,
            "min": min(betas.values()), "max": max(betas.values())}


def _plain_ols(y, x, Z) -> dict:
    X = _design(np.asarray(x, float), np.asarray(Z, float).reshape(len(y), -1))
    coef, *_ = np.linalg.lstsq(X, np.asarray(y, float), rcond=None)
    res = np.asarray(y, float) - X @ coef
    tss = float(((y - np.mean(y)) ** 2).sum())
    return {"coef": [float(c) for c in coef], "r2": float(1 - (res**2).sum() / tss) if tss > 0 else None,
            "n": int(len(y))}


# =============================================================================================
# Expanding-past estimator and increment-shuffle placebo (J4-R, J3)
# =============================================================================================

ESTIMATORS = ("pooled", "expanding")


def _expanding_resid(codes: np.ndarray, order: np.ndarray, x: np.ndarray) -> np.ndarray:
    """``x`` minus the mean of the same group's finite values at strictly earlier ``order`` positions.

    NaN where the group has no earlier finite value (so the first row of each market is NaN, and is
    dropped by the finite-row masks) or where ``x`` itself is NaN. Causal: row t uses only rows < t."""
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return x.copy()
    o = np.lexsort((np.asarray(order, float), np.asarray(codes)))
    cs, xs = np.asarray(codes)[o], x[o]
    fin = np.isfinite(xs)
    v = np.where(fin, xs, 0.0)
    csum, ccnt = np.cumsum(v), np.cumsum(fin)
    first = np.r_[True, cs[1:] != cs[:-1]]
    gstart = np.maximum.accumulate(np.where(first, np.arange(n), 0))
    prev_s = csum - v - (csum[gstart] - v[gstart])
    prev_c = ccnt - fin - (ccnt[gstart] - fin[gstart])
    mean = np.where(prev_c > 0, prev_s / np.maximum(prev_c, 1), np.nan)
    out = np.empty(n)
    out[o] = xs - mean
    return out


def expanding_demean(df: pd.DataFrame, cols, by: str = "market_id", order: str = "period") -> pd.DataFrame:
    """Copy of ``df`` in which each column in ``cols`` is replaced by its value minus the market's
    expanding mean over that market's strictly earlier rows (rows ordered by ``order``). The first row
    of each market becomes NaN (rows are kept; the fit masks drop them). Never pass the target."""
    out = df.copy()
    codes = pd.factorize(df[by])[0]
    ordv = df[order].to_numpy(float)
    for c in cols:
        out[c] = _expanding_resid(codes, ordv, df[c].to_numpy(float))
    return out


PLACEBO_SCHEMES = ("permute", "bootstrap")


def _rebuild_shuffled_levels(codes: np.ndarray, p: np.ndarray, levels, seed: int,
                             scheme: str = "permute"):
    """Rebuild per-market level series from a within-market shuffle of their increments.

    ``levels`` = three (n, K) float arrays: the level(s) at capture index ``p``, ``p + 1``, ``p + 2`` of
    each row (a triple (h, i, j) overlaps its neighbours: row t's (i, j) is row t+1's (h, i)). An
    increment c -> c+1 is *valid* only if some row observes both of its ends (so it is a genuine
    consecutive-capture change with an in-range gap). Valid increments of a market form contiguous runs
    (a missing capture or a gap breaks a run); within each run they are shuffled (one permutation for all K
    columns) and the run is rebuilt from its first observed level, so a capture shared by two
    overlapping rows gets one level. Returns three (n, K) arrays of rebuilt levels (NaN where the
    original level was unobserved or lies outside every run).

    ``scheme="permute"`` (declared J4-R placebo) permutes a run's increments. That fixes the run's total
    change, so the rebuilt level is a *bridge*: a regressor that is a LEVEL (J3's e_t, bm, mid-level
    controls) is then mechanically mean-reverting towards the run's end, which an increment regressor (J4)
    is not. ``scheme="bootstrap"`` instead draws the increments with replacement from the same run (no
    fixed total, no bridge); offered for level regressors, not used by default."""
    if scheme not in PLACEBO_SCHEMES:
        raise ValueError(f"unknown placebo scheme {scheme!r}")
    L0, L1, L2 = (np.asarray(L, float) for L in levels)
    n, K = L0.shape
    codes = np.asarray(codes, np.int64)
    p = np.asarray(p, np.int64)
    known = [np.all(np.isfinite(L), axis=1) for L in (L0, L1, L2)]
    a, b = known[0] & known[1], known[1] & known[2]
    e_code = np.r_[codes[a], codes[b]]
    e_c = np.r_[p[a], p[b] + 1]
    e_kind = np.r_[np.zeros(a.sum(), np.int8), np.ones(b.sum(), np.int8)]
    e_inc = np.vstack([(L1 - L0)[a], (L2 - L1)[b]])
    e_lvl = np.vstack([L0[a], L1[b]])
    nan = np.full((n, K), np.nan)
    if not len(e_code):
        return nan, nan.copy(), nan.copy()
    o = np.lexsort((e_kind, e_c, e_code))
    e_code, e_c, e_inc, e_lvl = e_code[o], e_c[o], e_inc[o], e_lvl[o]
    keep = np.r_[True, (e_code[1:] != e_code[:-1]) | (e_c[1:] != e_c[:-1])]  # dedupe, 'a' first
    e_code, e_c, e_inc, e_lvl = e_code[keep], e_c[keep], e_inc[keep], e_lvl[keep]
    m = len(e_code)
    begin = np.r_[True, (e_code[1:] != e_code[:-1]) | (e_c[1:] != e_c[:-1] + 1)]
    run_id = np.cumsum(begin) - 1
    first = np.flatnonzero(begin)[run_id]
    rng = np.random.default_rng(seed)
    if scheme == "permute":
        inc_sh = e_inc[np.lexsort((rng.random(m), run_id))]
    else:
        rlen = np.bincount(run_id)[run_id]
        inc_sh = e_inc[first + np.minimum((rng.random(m) * rlen).astype(np.int64), rlen - 1)]
    cs = np.cumsum(inc_sh, axis=0)
    base = cs[first] - inc_sh[first]
    start = e_lvl[first]
    before, after = start + (cs - inc_sh - base), start + (cs - base)
    pmin = int(p.min())
    M = int(p.max()) - pmin + 4
    kb = e_code * M + (e_c - pmin)
    keys = np.r_[kb, kb + 1]
    vals = np.vstack([before, after])
    ukeys, ui = np.unique(keys, return_index=True)
    uvals = vals[ui]
    res = []
    for j, kn in enumerate(known):
        rk = codes * M + (p + j - pmin)
        pos = np.minimum(np.searchsorted(ukeys, rk), len(ukeys) - 1)
        hit = (ukeys[pos] == rk) & kn
        res.append(np.where(hit[:, None], uvals[pos], np.nan))
    return tuple(res)


def shuffle_increments_placebo(df: pd.DataFrame, seed: int, scheme: str = "permute") -> pd.DataFrame:
    """J4-R placebo, matched to the expanding estimator. Per market, the Gamma-mid level series is
    rebuilt from a within-market random shuffle of its capture-to-capture increments (start level
    kept); shuffling happens only inside contiguous runs of observed consecutive-capture increments
    (a capture the market skipped, or an out-of-range gap, ends a run). ``d_bm``, ``dmid``, ``mid_h/i/j``,
    ``y_p1x`` (sweep ``B_i`` shifted by the level change of ``mid_i``), ``d_bm_x_w``, the h/j quote
    columns (shifted by their mid's level change) and the far-touch targets are recomputed; ``spread``,
    ``b_pos``, ``w``, ``chg_1h``, volume and liquidity stay as observed. Row t's (i, j) levels are row
    t+1's (h, i) levels in the rebuilt series (the series is rebuilt once per market, not per row).
    ``mid_h`` stays NaN where h was not two-sided (so ``d_bm`` keeps its missingness)."""
    codes = pd.factorize(df["market_id"])[0]
    p = df["period"].to_numpy(np.int64)
    g = lambda c: df[c].to_numpy(float)  # noqa: E731
    mh, mi, mj = g("mid_h"), g("mid_i"), g("mid_j")
    n0, n1, n2 = (x[:, 0] for x in _rebuild_shuffled_levels(
        codes, p, (mh[:, None], mi[:, None], mj[:, None]), seed, scheme))
    out = df.copy()
    sh_i, sh_j, sh_h = n1 - mi, n2 - mj, n0 - mh
    out["mid_h"], out["mid_i"], out["mid_j"] = n0, n1, n2
    out["d_bm"] = n1 - n0
    out["dmid"] = n2 - n1
    out["d_bm_x_w"] = out["d_bm"].to_numpy(float) * g("w")
    out["B_i"] = g("B_i") + sh_i
    out["y_p1x"] = n2 - out["B_i"].to_numpy(float)
    for c, sh in (("bid_h", sh_h), ("ask_h", sh_h), ("bid_j", sh_j), ("ask_j", sh_j)):
        if c in df:
            out[c] = g(c) + sh
    for c in ("y_far_bid", "y_far_ask"):
        if c in df:
            out[c] = g(c) + sh_j - sh_i
    for c in out.columns:
        if df[c].dtype == np.float32:
            out[c] = out[c].astype(np.float32)
    return out


def _summarise_placebo(draws: list[dict], names, estimator: str, seed: int) -> dict:
    """Per test: the betas of every placebo draw, their mean/SD, the 2.5-97.5% range, whether it covers 0
    (``placebo_null`` = covers 0 for every test), the mean SE and MDE. ``z_mean`` is descriptive."""
    tests: dict = {}
    for nme in names:
        rs = [d["tests"][nme] for d in draws if nme in d.get("tests", {}) and d["tests"][nme].get("testable")]
        if not rs:
            tests[nme] = {"testable": False, "covers_zero": False, "betas": [], "p": 1.0}
            continue
        b = np.array([r["beta"] for r in rs])
        lo, hi = (float(v) for v in np.percentile(b, [2.5, 97.5]))
        sd = float(b.std(ddof=1)) if len(b) > 1 else float("nan")
        tests[nme] = {
            "testable": True, "betas": [float(x) for x in b], "beta": float(b.mean()), "beta_sd": sd,
            "range_2_5_97_5": [lo, hi], "ci95": [lo, hi], "covers_zero": bool(lo <= 0.0 <= hi),
            "reject": not bool(lo <= 0.0 <= hi), "se": float(np.mean([r["se"] for r in rs])),
            "mde_80": float(np.mean([r["mde_80"] for r in rs])), "n": int(np.mean([r["n"] for r in rs])),
            "z_mean": float(b.mean() / (sd / np.sqrt(len(b)))) if sd and sd > 0 else None,
            "p": None}
    return {"estimator": estimator, "draws": len(draws), "seed": seed, "tests": tests,
            "placebo_null": bool(all(t["covers_zero"] for t in tests.values()))}


def placebo_family(df: pd.DataFrame, draws: int = 20, seed: int = 117, estimator: str = "expanding",
                   n_boot: int = 20, scheme: str = "permute") -> dict:
    """Run the J4 estimator on ``draws`` increment-shuffle placebos (seeds ``seed + k``). Reports per
    test the betas and whether their 2.5-97.5% range covers 0; ``placebo_null`` is True only if it does
    for every test (otherwise the family is void). Bootstrap CIs are not used (``n_boot`` is small)."""
    out = []
    for k in range(draws):
        out.append(snapshot_tests(shuffle_increments_placebo(df, seed + k, scheme), n_boot, seed, estimator,
                                  descriptive=False))
    return {**_summarise_placebo(out, list(J4_SPEC), estimator, seed), "scheme": scheme}


# =============================================================================================
# J4: snapshot triples
# =============================================================================================


def _read_capture(cap: dict) -> pd.DataFrame:
    path = forecast.require_local(Path(cap["dir"]) / "rows.csv.gz")
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in SNAP_USECOLS if c in header]
    df = pd.read_csv(path, usecols=use, dtype={"market_id": str, "event_id": str})
    for c in SNAP_USECOLS:
        if c not in df.columns:
            df[c] = np.nan
    for c in _FLOAT_COLS:
        df[c] = df[c].astype(np.float32)
    return df.drop_duplicates("market_id").reset_index(drop=True)


def iter_captures(snapshot_root: Path = SNAPSHOT_ROOT, until_utc: str | None = None,
                  since_utc: str | None = None, before_utc: str | None = None
                  ) -> Iterator[tuple[dict, pd.DataFrame]]:
    """Complete captures in start order, one frame at a time (``until_utc``: started <= that;
    ``before_utc``: started < that; ``since_utc``: started >= that)."""
    caps = forecast.list_complete_captures(snapshot_root)
    if until_utc is not None:
        cut = forecast._parse_ts(until_utc)
        caps = [c for c in caps if c["_start"] <= cut]
    if before_utc is not None:
        cut = forecast._parse_ts(before_utc)
        caps = [c for c in caps if c["_start"] < cut]
    if since_utc is not None:
        cut = forecast._parse_ts(since_utc)
        caps = [c for c in caps if c["_start"] >= cut]
    for cap in caps:
        yield {"capture_id": cap["capture_id"], "start_utc": cap["started_utc"],
               "start": cap["_start"], "dir": cap["dir"]}, _read_capture(cap)


def load_sweep_mid(sweep_root: Path, snapshot_id: str) -> pd.DataFrame | None:
    """B_i (two-sided, non-crossed CLOB book mid) per market for the sweep of capture ``snapshot_id``
    (the earliest complete sweep of that snapshot); ``batch_receipt_epoch`` for the lag."""
    best = None
    for m in sorted(Path(sweep_root).glob("*/manifest.json")):
        man = json.loads(m.read_text())
        if man.get("snapshot_id") != snapshot_id or man.get("state") != "complete":
            continue
        key = (man.get("series_index", 0), man.get("started_utc", ""))
        if best is None or key < best[0]:
            best = (key, m.parent)
    if best is None:
        return None
    df = pd.read_csv(forecast.require_local(best[1] / "rows.csv.gz"),
                     usecols=["market_id", "batch_receipt_utc", "best_bid", "best_ask", "state"],
                     dtype={"market_id": str})
    bid, ask = df["best_bid"].to_numpy(float), df["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        ok = (df["state"] == "two_sided").to_numpy() & (bid > 0) & (ask > 0) & (bid < ask)
    out = pd.DataFrame({"market_id": df["market_id"], "B_i": np.where(ok, (bid + ask) / 2, np.nan),
                        "sweep_epoch": panel._epoch(df["batch_receipt_utc"])})
    return out.drop_duplicates("market_id").set_index("market_id")


def _two_sided(bid, ask) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask)


def h_tight_mask(bid_h, ask_h, spread_h) -> np.ndarray:
    """The E001 tightness rule applied to the previous capture h: two-sided (bid > 0, bid < ask,
    ask < 1), spread <= panel.SPREAD_MAX and mid in [panel.MID_LO, panel.MID_HI]."""
    spread = np.where(np.isnan(spread_h), ask_h - bid_h, spread_h)
    mid = (bid_h + ask_h) / 2
    with np.errstate(invalid="ignore"):
        return ((bid_h > 0) & (bid_h < ask_h) & (ask_h < 1) & (spread <= panel.SPREAD_MAX)
                & (mid >= panel.MID_LO) & (mid <= panel.MID_HI))


def build_triple(snap_h: pd.DataFrame, snap_i: pd.DataFrame, snap_j: pd.DataFrame, i_start: str,
                 j_start: str, period: int, sweep: pd.DataFrame | None, h_tight: bool = False
                 ) -> tuple[pd.DataFrame, dict]:
    """One triple. Eligibility/target from ``panel.build_pair(i, j)`` (E001 semantics); features
    from capture i, the quote changes from h; capture j only supplies target columns. ``h_tight``
    additionally drops rows whose h quote fails the E001 tightness rule (counted in the result)."""
    j_sched = panel._epoch(pd.Series([j_start]))[0]
    pairs, cnt = panel.build_pair(snap_i, snap_j, j_sched, period)
    pairs = pairs[pairs["dmid"].notna()].reset_index(drop=True)
    mids = pairs["market_id"].astype(str)
    ii = snap_i.set_index("market_id").reindex(mids)
    hh = snap_h.set_index("market_id").reindex(mids)
    jj = snap_j.set_index("market_id").reindex(mids)
    f = lambda s: s.to_numpy(float)  # noqa: E731
    mid_i = f(pairs["mid"])
    spread = f(pairs["spread"])
    ltp = f(ii["last_trade_price"])
    ltp = np.where(ltp > 0, ltp, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        b_pos = np.clip((ltp - mid_i) / (spread / 2.0), -1.0, 1.0)
    b_pos = np.where((spread > 0) & np.isfinite(ltp), b_pos, np.nan)
    bid_i, ask_i = f(ii["best_bid"]), f(ii["best_ask"])
    bid_h, ask_h = f(hh["best_bid"]), f(hh["best_ask"])
    h_ok = _two_sided(bid_h, ask_h)
    d_bid = np.where(h_ok, bid_i - bid_h, np.nan)
    d_ask = np.where(h_ok, ask_i - ask_h, np.nan)
    d_bm = np.where(h_ok, mid_i - (bid_h + ask_h) / 2, np.nan)
    den = np.abs(d_ask) + np.abs(d_bid)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where(den > 0, np.abs(d_ask - d_bid) / den, 0.0)
    w = np.where(np.isfinite(d_bm), w, np.nan)
    vol_i, vol_h = f(ii["volume24hr"]), f(hh["volume24hr"])
    with np.errstate(invalid="ignore"):
        vol_up = (vol_i > vol_h)
    t_i = pairs["t_i"].to_numpy(float)
    if sweep is not None:
        sw = sweep.reindex(mids)
        B_i = f(sw["B_i"])
        lag = (f(sw["sweep_epoch"]) - t_i) / 60.0
    else:
        B_i, lag = np.full(len(pairs), np.nan), np.full(len(pairs), np.nan)
    ev = pairs["event_id"]
    bad = ev.isna() | ev.astype(str).isin(["", "nan", "None"])
    mid_j = f(pairs["mid_j"])
    bid_j, ask_j = f(jj["best_bid"]), f(jj["best_ask"])
    out = pd.DataFrame({
        "market_id": mids.to_numpy(),
        "cluster": np.where(bad, "m:" + mids, ev.astype(str)).astype(object),
        "period": np.int32(period),
        "day": pd.to_datetime(i_start, utc=True).strftime("%Y-%m-%d"),
        "mid_i": mid_i, "mid_h": np.where(h_ok, (bid_h + ask_h) / 2, np.nan), "spread": spread,
        "chg_1h": f(pairs["chg_1h"]), "chg_1h_missing": f(pairs["chg_1h_missing"]),
        "b_pos": b_pos, "b_pos0": np.nan_to_num(b_pos, nan=0.0),
        "b_pos_missing": np.isnan(b_pos).astype(float),
        "d_bm": d_bm, "d_bid": d_bid, "d_ask": d_ask, "w": w, "d_bm_x_w": d_bm * w,
        "volume24hr_i": vol_i, "volume24hr_h": vol_h, "volume_up": vol_up,
        "liquidity_i": f(ii["liquidity"]), "B_i": B_i, "sweep_lag_min": lag,
        "ltp_i": ltp, "ltp_h": np.where(f(hh["last_trade_price"]) > 0, f(hh["last_trade_price"]),
                                         np.nan),
        "bid_h": bid_h, "ask_h": ask_h,
        "mid_j": mid_j, "bid_j": bid_j, "ask_j": ask_j, "dmid": mid_j - mid_i,
    })
    out["y_p1x"] = out["mid_j"] - out["B_i"]
    out["y_far_bid"] = out["bid_j"] - bid_i
    out["y_far_ask"] = out["ask_j"] - ask_i
    h_excl = 0
    if h_tight:
        keep = h_tight_mask(bid_h, ask_h, f(hh["spread"]))
        h_excl = int((~keep).sum())
        out = out[keep].reset_index(drop=True)
    for c in out.columns:
        if out[c].dtype == np.float64:
            out[c] = out[c].astype(np.float32)
    if h_tight:
        cnt["h_tight_excluded"] = h_excl
    cnt.update({"triple_rows": int(len(out)), "h_quote_ok": int(np.isfinite(d_bm).sum()),
                "ltp_missing_or_nonpositive": int(np.isnan(b_pos).sum()),
                "sweep_available": int(np.isfinite(B_i).sum()),
                "sweep_lag_gt_20min": int((lag > SWEEP_MAX_LAG_MIN).sum()),
                "sweep_lag_negative": int((lag < 0).sum())})
    return out, cnt


def build_snapshot_triples(snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT,
                           until_utc: str | None = None, log: Callable[[str], None] | None = None,
                           since_utc: str | None = None, h_tight: bool = False,
                           before_utc: str | None = None
                           ) -> tuple[pd.DataFrame, list[dict]]:
    """All triples ``(h, i, j)`` of consecutive complete captures with gap(h,i), gap(i,j) in
    [1.5, 3] h; three captures in memory at most, only the needed columns.

    ``since_utc``: only captures started >= since are read, so h, i and j all start >= since
    (fresh-capture rule); ``before_utc``: only captures started < that (exclusive end); ``h_tight``:
    drop rows whose h quote fails the E001 tightness rule. Exclusions are counted: a trailing
    ``{"filters": ...}`` entry carries the captures excluded by the time window and, per triple,
    ``h_tight_excluded``. Defaults (all None / False) reproduce the original behaviour exactly."""
    window: list[tuple[dict, pd.DataFrame]] = []
    frames: list[pd.DataFrame] = []
    counts: list[dict] = []
    k = 0
    for meta, df in iter_captures(snapshot_root, until_utc, since_utc, before_utc):
        window.append((meta, df))
        if len(window) > 3:
            window.pop(0)
        if len(window) < 3:
            continue
        (mh, sh), (mi, si), (mj, sj) = window
        g_hi = (mi["start"] - mh["start"]).total_seconds() / 3600.0
        g_ij = (mj["start"] - mi["start"]).total_seconds() / 3600.0
        base = {"capture_h": mh["capture_id"], "capture_i": mi["capture_id"],
                "capture_j": mj["capture_id"], "gap_hi_h": g_hi, "gap_ij_h": g_ij}
        if not (GAP_LO_H <= g_hi <= GAP_HI_H and GAP_LO_H <= g_ij <= GAP_HI_H):
            base["skipped"] = "gap_outside_1.5_3h"
            counts.append(base)
            k += 1
            continue
        sweep = load_sweep_mid(sweep_root, mi["capture_id"]) if Path(sweep_root).exists() else None
        trip, cnt = build_triple(sh, si, sj, mi["start_utc"], mj["start_utc"], k, sweep, h_tight)
        cnt.update(base)
        cnt["sweep_found"] = sweep is not None
        frames.append(trip)
        counts.append(cnt)
        if log:
            log(json.dumps(_clean(cnt)))
        k += 1
    if since_utc is not None or before_utc is not None or h_tight:
        allc = forecast.list_complete_captures(snapshot_root)
        if until_utc is not None:
            cut = forecast._parse_ts(until_utc)
            allc = [c for c in allc if c["_start"] <= cut]
        n_all = len(allc)
        n_used = sum(1 for c in allc
                     if (since_utc is None or c["_start"] >= forecast._parse_ts(since_utc))
                     and (before_utc is None or c["_start"] < forecast._parse_ts(before_utc)))
        counts.append({"filters": {
            "since_utc": since_utc, "before_utc": before_utc, "h_tight": h_tight,
            "captures_complete_total": n_all, "captures_read": n_used,
            "captures_excluded_by_time_window": n_all - n_used,
            "rows_excluded_h_not_tight": int(sum(c.get("h_tight_excluded", 0) for c in counts))}})
    if not frames:
        return pd.DataFrame(), counts
    return pd.concat(frames, ignore_index=True), counts


# --- permutation placebo ------------------------------------------------------------------------


def _within_perm(codes: np.ndarray, seed: int) -> np.ndarray:
    """Index array: position k receives the row ``idx[k]``, shuffled within market groups."""
    rng = np.random.default_rng(seed)
    order = np.lexsort((rng.random(len(codes)), codes))  # rows grouped by market, random order
    base = np.argsort(codes, kind="stable")  # rows grouped by market, original order
    idx = np.empty(len(codes), np.int64)
    idx[base] = order
    return idx


def permute_snapshot_targets(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Placebo: the target VALUES (dmid, y_p1x, y_far_*, and the j-side quote columns) are permuted
    across captures within market with ONE shared index; features are untouched. (Permuting levels
    and rebuilding dmid = mid_j' - mid_i would put -mid_i in the target and +mid_i in d_bm: a
    reversal by construction.)"""
    out = df.copy()
    idx = _within_perm(pd.factorize(df["market_id"])[0], seed)
    for c in J4_TARGETS:
        if c in df.columns:
            out[c] = df[c].to_numpy()[idx]
    return out


# --- the five tests -----------------------------------------------------------------------------

J4_SPEC = {
    "P1": dict(target="dmid", term="d_bm", controls=("spread", "b_pos0", "b_pos_missing"),
               label="Gamma-mid reversal"),
    "P1x": dict(target="y_p1x", term="d_bm", controls=("spread",),
                label="reversal after an independent mid measurement at i (sweep B_i)"),
    "P2": dict(target="dmid", term="b_pos", controls=("d_bm", "chg_1h", "chg_1h_missing", "spread"),
               label="last-trade position (rows with volume24hr_i > volume24hr_h)"),
    "P3": dict(target="dmid", term="d_bm_x_w", controls=("d_bm", "w"),
               label="one-sided quote moves revert more (refill)"),
    "P4": dict(target="dmid", term="chg_1h", controls=("d_bm", "b_pos0", "b_pos_missing",
                                                       "chg_1h_missing", "spread"),
               label="E004 reversal after controlling mid change and bounce position"),
}


def _tercile(x: np.ndarray) -> np.ndarray:
    q = np.nanpercentile(x[np.isfinite(x)], [100 / 3, 200 / 3]) if np.isfinite(x).any() else [0, 0]
    return np.where(np.isnan(x), -1, np.digitize(x, q))


def _rows_for(df: pd.DataFrame, name: str, arr: dict | None = None) -> np.ndarray:
    """Finite-row mask of test ``name``; ``arr`` (column -> array) overrides ``df`` columns (the
    expanding-demeaned regressors)."""
    sp = J4_SPEC[name]
    cols = [sp["target"], sp["term"], *sp["controls"]]
    m = np.ones(len(df), bool)
    for c in cols:
        m &= np.isfinite(arr[c] if arr is not None and c in arr else df[c].to_numpy(float))
    if name == "P1x":
        lag = df["sweep_lag_min"].to_numpy(float)
        with np.errstate(invalid="ignore"):
            m &= (lag >= 0) & (lag <= SWEEP_MAX_LAG_MIN)  # sweep before Gamma receipt: excluded too
    if name == "P2":
        m &= df["volume_up"].to_numpy(bool)
    return m


def snapshot_regressors() -> list[str]:
    """Every term and control column of the five tests (never a target)."""
    cols: list[str] = []
    for sp in J4_SPEC.values():
        for c in (sp["term"], *sp["controls"]):
            if c not in cols:
                cols.append(c)
    return cols


def snapshot_tests(df: pd.DataFrame, n_boot: int = 2000, seed: int = 116,
                   estimator: str = "pooled", descriptive: bool = True) -> dict:
    """P1, P1x, P2, P3, P4 (Holm over the 5), LODO sign rule, descriptive extras.

    ``estimator="pooled"`` (default) is the original pooled OLS with an intercept. ``"expanding"`` (J4-R)
    replaces each regressor (term and controls) by its value minus the market's expanding mean over
    strictly earlier rows (ordered by ``period``; the first row of a market is dropped), keeps the target
    raw and the intercept, and is otherwise identical (same rows rules, SEs, Holm, LODO, verdicts).
    Row filters that use raw columns (volume rule, sweep lag, median half-spread) stay on the raw frame."""
    if estimator not in ESTIMATORS:
        raise ValueError(f"unknown estimator {estimator!r}")
    res: dict = {"tests": {}, "descriptive": {}, "estimator": estimator}
    ev, per, day = df["cluster"].to_numpy(), df["period"].to_numpy(), df["day"].to_numpy()
    if estimator == "expanding":
        codes, ordv = pd.factorize(df["market_id"])[0], df["period"].to_numpy(float)
        arr = {c: _expanding_resid(codes, ordv, df[c].to_numpy(float)) for c in snapshot_regressors()}
    else:
        arr = {c: df[c].to_numpy(float) for c in snapshot_regressors()}
    for name, sp in J4_SPEC.items():
        m = _rows_for(df, name, arr)
        scale = 100.0 if name == "P2" else 1.0  # P2 in cents per unit b_pos
        y = df[sp["target"]].to_numpy(float)[m] * scale
        x = arr[sp["term"]][m]
        Z = np.column_stack([arr[c][m] for c in sp["controls"]])
        r = fit_test(y, x, Z, ev[m], per[m], n_boot, seed)
        r.update(label=sp["label"], rows_used=int(m.sum()), rows_candidate=int(len(df)))
        if r["testable"]:
            r["lodo"] = lodo(y, x, Z, day[m], r["beta"])
        if name == "P2":
            m_raw = _rows_for(df, name) if estimator == "expanding" else m
            vm = np.isfinite(df["b_pos"].to_numpy(float)) & np.isfinite(df["dmid"].to_numpy(float))
            share = {"all": float(1 - (vm & m_raw).sum() / max(vm.sum(), 1))}
            ter = _tercile(df["liquidity_i"].to_numpy(float))
            share["by_liquidity_tercile"] = {
                str(t): float(1 - (vm & m_raw & (ter == t)).sum() / max((vm & (ter == t)).sum(), 1))
                for t in (0, 1, 2)}
            r["share_dropped_volume_rule"] = share
            r["half_spread_cents_median"] = float(
                np.median(df["spread"].to_numpy(float)[m] / 2 * 100)) if m.any() else None
        if name == "P1x":
            r["sweep_rows_lag_gt_20min"] = int((df["sweep_lag_min"] > SWEEP_MAX_LAG_MIN).sum())
            r["sweep_rows_lag_negative"] = int((df["sweep_lag_min"] < 0).sum())
        res["tests"][name] = r
    adj = holm({n: t["p"] for n, t in res["tests"].items()})
    for n, t in res["tests"].items():
        t["p_holm"] = adj[n]
        t["reject"] = bool(adj[n] < ALPHA)
    if descriptive:
        res["descriptive"] = _snapshot_descriptive(df, n_boot, seed)
        if estimator == "expanding":
            res["descriptive_note"] = "descriptive extras are pooled/raw (not demeaned)"
    res["n_triples"] = int(len(df))
    res["n_clusters"] = int(len(pd.unique(ev)))
    res["n_periods"] = int(len(pd.unique(per)))
    res["utc_days"] = sorted(str(d) for d in pd.unique(day))
    res["verdicts"] = verdicts(res)
    return _clean(res)


def _brief(res: dict) -> dict:
    return {n: {k: t.get(k) for k in ("beta", "se", "p", "n", "testable")}
            for n, t in res.get("tests", {}).items()}


def _slope(y, x, Z) -> float | None:
    X = _design(np.asarray(x, float), np.asarray(Z, float).reshape(len(y), -1))
    if len(y) < X.shape[1] + 2:
        return None
    coef, *_ = np.linalg.lstsq(X, np.asarray(y, float), rcond=None)
    return float(coef[1])


def within_between(df: pd.DataFrame) -> dict:
    """Descriptive decomposition per test (raw regressors): pooled slope, within-market slope (all
    variables demeaned by market mean over the whole sample; contains the mechanical dynamic-panel
    bias) and between-market slope (regression of market means)."""
    out: dict = {}
    codes_all = pd.factorize(df["market_id"])[0]
    for name, sp in J4_SPEC.items():
        m = _rows_for(df, name)
        scale = 100.0 if name == "P2" else 1.0
        y = df[sp["target"]].to_numpy(float)[m] * scale
        x = df[sp["term"]].to_numpy(float)[m]
        Z = df[list(sp["controls"])].to_numpy(float)[m]
        cm = pd.factorize(codes_all[m])[0]
        cnt = np.bincount(cm)

        def mean_by(v, cm=cm, cnt=cnt):
            return np.bincount(cm, weights=v, minlength=len(cnt)) / cnt

        my, mx = mean_by(y), mean_by(x)
        mZ = np.column_stack([mean_by(Z[:, k]) for k in range(Z.shape[1])]) if Z.shape[1] else Z[:0]
        out[name] = {
            "pooled": _slope(y, x, Z),
            "within": _slope(y - my[cm], x - mx[cm], Z - mZ[cm] if Z.shape[1] else Z),
            "between": _slope(my, mx, mZ) if len(cnt) > 3 else None,
            "n_rows": int(m.sum()), "n_markets": int(len(cnt))}
    return out


def snapshot_sensitivities(df: pd.DataFrame, n_boot: int = 200, seed: int = 116,
                           estimator: str = "expanding", min_rows: int = 20) -> dict:
    """Descriptive sensitivities (never counted, never part of a verdict): markets with >= ``min_rows``
    rows; rows whose j quote is also tight (outcome-side filter, applied before demeaning); the pooled
    estimator on all rows; and the within/between decomposition."""
    out: dict = {"note": "descriptive only; filters are applied before the expanding demeaning"}
    per_mkt = df.groupby("market_id")["period"].transform("size").to_numpy()
    sel = per_mkt >= min_rows
    out[f"markets_ge_{min_rows}_rows"] = {
        "n_rows": int(sel.sum()), "n_markets": int(df.loc[sel, "market_id"].nunique()),
        **(_brief(snapshot_tests(df[sel].reset_index(drop=True), n_boot, seed, estimator, False))
           if sel.any() else {})}
    bj, aj = df["bid_j"].to_numpy(float), df["ask_j"].to_numpy(float)
    mj = df["mid_j"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        jt = (aj - bj <= panel.SPREAD_MAX) & (mj >= panel.MID_LO) & (mj <= panel.MID_HI)
    out["j_tight_rows"] = {"n_rows": int(jt.sum()),
                           **(_brief(snapshot_tests(df[jt].reset_index(drop=True), n_boot, seed,
                                                    estimator, False)) if jt.any() else {})}
    out["pooled_all_rows"] = _brief(snapshot_tests(df, n_boot, seed, "pooled", False))
    out["within_between"] = within_between(df)
    return out


def _snapshot_descriptive(df: pd.DataFrame, n_boot: int, seed: int) -> dict:
    out: dict = {}
    ev, per = df["cluster"].to_numpy(), df["period"].to_numpy()
    sp = J4_SPEC["P4"]
    m = _rows_for(df, "P4")
    y = df["dmid"].to_numpy(float)[m]
    x = df["chg_1h"].to_numpy(float)[m]
    full = fit_test(y, x, df[list(sp["controls"])].to_numpy(float)[m], ev[m], per[m], 200, seed)
    alone = fit_test(y, x, np.empty((m.sum(), 0)), ev[m], per[m], 200, seed)
    if full.get("testable") and alone.get("testable") and alone["beta"] != 0:
        out["attenuation"] = {"gamma_full": full["beta"], "gamma_alone": alone["beta"],
                              "attenuation_1_minus_full_over_alone": 1 - full["beta"] / alone["beta"]}
    m2 = (np.isfinite(df["chg_1h"].to_numpy(float)) & np.isfinite(df["ltp_i"].to_numpy(float))
          & np.isfinite(df["ltp_h"].to_numpy(float)) & np.isfinite(df["d_bm"].to_numpy(float))
          & (df["chg_1h_missing"].to_numpy(float) == 0))
    if m2.sum() > 10:
        X = np.column_stack([df["ltp_i"].to_numpy(float)[m2] - df["ltp_h"].to_numpy(float)[m2],
                             df["d_bm"].to_numpy(float)[m2]])
        out["chg_1h_basis_regression"] = {
            "terms": ["ltp_i - ltp_h", "mid_i - mid_h"],
            **_plain_ols(df["chg_1h"].to_numpy(float)[m2], X[:, 0], X[:, 1:])}
    # far-touch version of P1: bid change after a past ask-led move (and the mirror)
    for nm, y_col, term, ctrl in (("far_touch_bid_after_ask_move", "y_far_bid", "d_ask", "d_bid"),
                                  ("far_touch_ask_after_bid_move", "y_far_ask", "d_bid", "d_ask")):
        cols = [y_col, term, ctrl, "spread"]
        mm = np.all([np.isfinite(df[c].to_numpy(float)) for c in cols], axis=0)
        if mm.sum() > 100:
            r = fit_test(df[y_col].to_numpy(float)[mm], df[term].to_numpy(float)[mm],
                         df[[ctrl, "spread"]].to_numpy(float)[mm], ev[mm], per[mm], 200, seed)
            out[nm] = {k: r.get(k) for k in ("testable", "beta", "se", "p", "n", "ci95")}
    return out


# --- J4 verdict map -----------------------------------------------------------------------------


def _equiv(t: dict, band: float) -> bool:
    return bool(t.get("testable") and t["ci90"][0] > -band and t["ci90"][1] < band)


def _rej(t: dict, sign: int | None = None) -> bool:
    if not t.get("testable") or not t.get("reject"):
        return False
    return True if sign is None else bool(np.sign(t["beta"]) == sign)


def _stable(*ts: dict) -> bool:
    return all(t.get("testable") and t.get("lodo", {}).get("sign_stable") for t in ts)


def _lodo_within(t: dict, lo: float, hi: float) -> bool:
    """Equivalence/bound verdicts (pre-freeze amendment): every leave-one-day-out estimate in (lo, hi)."""
    b = t.get("lodo", {}).get("betas") or {}
    return bool(t.get("testable") and b and all(lo < x < hi for x in b.values()))


def verdicts(res: dict) -> dict:
    """The declared J4 verdict map (SCREENING_BATCH_2 J4), TOST bands as written, then the binding
    leave-one-day-out rule (sign stability for directional verdicts; every day's estimate inside the
    band for equivalence/bound verdicts, per the pre-freeze amendment)."""
    T = res["tests"]
    p1, p1x, p2, p3, p4 = (T[k] for k in ("P1", "P1x", "P2", "P3", "P4"))
    mde = {k: t.get("mde_80") for k, t in T.items()}
    v: dict = {}
    gm = _rej(p1, -1)
    v["gamma_mid_reversal"] = ("present" if gm else
                               "anomalous (positive P1)" if _rej(p1, 1) else "inconclusive")
    # genuine reversion vs quote noise
    genuine = gm and _rej(p1x, -1) and p1x["beta"] <= p1["beta"] / 2
    bi: dict = {}  # per bound clause: which interval was used and which end bound
    noise_ci = cons_ci(p1x) if p1x.get("testable") else None
    if noise_ci:
        bi["reversion_nature.quote_noise_route"] = {
            "interval": list(noise_ci[0]), "binding": noise_ci[1][0], "rule": "lo95_cons > P1/2"}
        bi["reversion_nature.equivalence_tost"] = {
            "interval": list(p1x["ci90"]), "binding": "normal_max_se", "rule": "ci90 inside +/-0.05"}
    noise = gm and p1x.get("testable") and (_equiv(p1x, TOST_SLOPE_BAND)
                                            or noise_ci[0][0] > p1["beta"] / 2)
    v["reversion_nature"] = ("genuine reversion" if genuine else "quote noise" if noise
                             else "inconclusive")
    hs = p2.get("half_spread_cents_median")
    if p2.get("testable") and hs:
        bi["last_trade.pure_bounce_tost"] = {"interval": list(p2["ci90"]), "binding": "normal_max_se",
                                             "rule": "ci90 inside +/-0.1 half-spread"}
    if p2.get("testable") and hs and _equiv(p2, TOST_BPOS_HS_FRAC * hs):
        v["last_trade"] = "pure bounce (no information in the last trade)"
    elif _rej(p2, 1):
        v["last_trade"] = "informed last trade"
    elif _rej(p2, -1):
        v["last_trade"] = "anomalous (negative P2; no mechanism claim)"
    else:
        v["last_trade"] = "inconclusive"
    v["quote_refill"] = ("supporting: refill" if _rej(p3, -1) and genuine else "inconclusive")
    if p4.get("testable"):
        c4 = cons_ci(p4)
        bi["e004_reversal.explained"] = {"interval": list(c4[0]), "binding": c4[1][0],
                                         "rule": "lo95_cons > -0.05"}
    if p4.get("testable") and not p4["reject"] and cons_ci(p4)[0][0] > -0.05:
        v["e004_reversal"] = "explained"
    elif _rej(p4):
        v["e004_reversal"] = "not explained"
    else:
        v["e004_reversal"] = "inconclusive"
    # binding leave-one-day-out rule: directional verdicts need sign stability on every day;
    # equivalence/bound verdicts need every day's estimate inside the band (pre-freeze amendment)
    band_bpos = TOST_BPOS_HS_FRAC * hs if hs else 0.0
    stable = {
        "gamma_mid_reversal": lambda: _stable(p1),
        "reversion_nature": lambda: (_stable(p1, p1x) if genuine else _stable(p1) and (
            _lodo_within(p1x, -TOST_SLOPE_BAND, TOST_SLOPE_BAND)
            or _lodo_within(p1x, p1["beta"] / 2, np.inf))),
        "last_trade": lambda: (_lodo_within(p2, -band_bpos, band_bpos)
                               if v["last_trade"].startswith("pure bounce") else _stable(p2)),
        "quote_refill": lambda: _stable(p3, p1, p1x),
        "e004_reversal": lambda: (_lodo_within(p4, -0.05, np.inf)
                                  if v["e004_reversal"] == "explained" else _stable(p4)),
    }
    out = {}
    for k, label in v.items():
        if label != "inconclusive" and not stable[k]():
            label = "inconclusive (day-unstable)"
        out[k] = label
    out["mde_80_by_test"] = mde
    out["bound_intervals"] = bi
    out["note"] = "J4 does not close Q5; supporting evidence for J3 only"
    return out


# =============================================================================================
# J3: book triples
# =============================================================================================

C0_COLS = ("ml_logit_mid", "ml_abs_mid_dev", "c_chg_1h", "c_chg_1d", "c_chg_1w", "ml_chg_1h_missing",
           "ml_chg_1d_missing", "ml_chg_1w_missing", "c_dprev", "c_dprev_missing")
FEATURE_READ = ["market_id", "event_c", "day_c", "t_i", "split", "mid_i", "d_6", "ok_6", *C0_COLS,
                "f_imb_6h", "f_n_6h", "bk_sw_best_bid", "bk_sw_best_ask", "bk_sw_depth_bid_5c",
                "bk_sw_depth_ask_5c", "bp_sw_best_bid", "bp_sw_best_ask"]


def signed_notional_6h(run_dir: Path, markets_t: pd.DataFrame) -> np.ndarray:
    """Signed 6h trade notional S (USDC, token-0 sign convention) on the price-aligned window used by
    ``battery.flow_features`` (window ends at the last usable price stamp, else t - LAG; NaN where the
    truncated trade history does not cover the window). Same ``battery.Trades`` cumulative sums, so
    ``f_imb_6h == S / N`` of the stored features. ``markets_t``: columns market_id, t_i."""
    from . import battery
    from . import history_backfill as hb

    run_dir = Path(run_dir)
    prog = {}
    pf_ = run_dir / "progress.jsonl"
    if pf_.exists():
        for line in pf_.read_text().splitlines():
            if line.strip():
                dd = json.loads(line)
                prog[str(dd["market_id"])] = dd
    out = np.full(len(markets_t), np.nan)
    pos = np.arange(len(markets_t))
    for mid, g in markets_t.assign(_pos=pos).groupby("market_id", sort=False):
        tf = run_dir / "trades" / f"{mid}.csv.gz"
        if not tf.exists():
            continue
        tr = hb.load_trades(tf)
        if not len(tr):
            continue
        pfile = run_dir / "prices" / f"{mid}.csv.gz"
        ts, v = hb.load_prices(pfile) if pfile.exists() else (np.array([]), np.array([]))
        p = prog.get(str(mid), {})
        cov_from = (float(p["trades_oldest_ts"]) if p.get("trades_truncated")
                    and p.get("trades_oldest_ts") is not None else -np.inf)
        T = battery.Trades(tr, (ts, v), {}, None, cov_from)
        t = g["t_i"].to_numpy(float)
        u = battery._last_idx(ts, t) if len(ts) else np.full(len(t), -1)
        s_last = np.where(u >= 0, ts[np.maximum(u, 0)] if len(ts) else np.nan, np.nan)
        e = np.where(np.isfinite(s_last), s_last, t - battery.LAG)
        S = np.where(T.covered(e - H6), T.win("S", e - H6, e), np.nan)
        out[g["_pos"].to_numpy()] = S
    return out


def build_book_triples(features_path: Path, book_table: Path, panel_6h: Path,
                       log: Callable[[str], None] | None = None, run_dir: Path | None = None
                       ) -> tuple[pd.DataFrame, dict]:
    """h2_main primary 6h rows with two-sided, non-crossed books at t-6h, t and t+6h.

    ``features_path``: battery features.parquet (origin features; targets d_6/ok_6 carried);
    ``book_table``: history_sources book_features.csv.gz (book at t+6h is the target side);
    ``panel_6h``: panel_H6h.csv.gz (series mid at t-6h)."""
    import pyarrow.parquet as pq

    from . import battery

    have = set(pq.read_schema(Path(features_path)).names)
    extra = [c for c in ("f_N_6h",) if c in have]
    d = battery.read_features(Path(features_path), FEATURE_READ + extra)
    n0 = len(d)
    # D2 numerator: signed 6h notional S (USDC). Stored 6h notional N if present (S = f_imb_6h * N),
    # else recomputed from the trade files with the battery's own price-aligned window.
    if "f_N_6h" in d.columns:
        sn6 = d["f_imb_6h"].to_numpy(float) * d["f_N_6h"].to_numpy(float)
        sn6_src = "f_imb_6h * f_N_6h (stored)"
    elif run_dir is not None:
        sn6 = signed_notional_6h(Path(run_dir), d[["market_id", "t_i"]])
        sn6_src = "recomputed from trades via battery.Trades (price-aligned 6h window)"
    else:
        sn6, sn6_src = np.full(len(d), np.nan), "unavailable (no f_N_6h, no run_dir): D2 untestable"
    pn = pd.read_csv(panel_6h, usecols=["market_id", "t_i", "mid_i"], dtype={"market_id": str})
    prev = pn.rename(columns={"mid_i": "mid_prev"})
    prev["t_i"] = prev["t_i"] + H6
    d = d.merge(prev.drop_duplicates(["market_id", "t_i"]), on=["market_id", "t_i"], how="left")
    bt = pd.read_csv(book_table, usecols=["market_id", "origin_ts", "state", "sw_best_bid", "sw_best_ask"],
                     dtype={"market_id": str})
    bt = bt[bt["state"] == "two_sided"].drop_duplicates(["market_id", "origin_ts"])
    tgt = bt[["market_id", "origin_ts", "sw_best_bid", "sw_best_ask"]].rename(
        columns={"sw_best_bid": "bn_bid", "sw_best_ask": "bn_ask"})
    tgt["t_i"] = tgt["origin_ts"].astype(float) - H6
    d = d.merge(tgt.drop(columns="origin_ts"), on=["market_id", "t_i"], how="left")
    g = lambda c: d[c].to_numpy(float)  # noqa: E731
    cur_ok = _two_sided(g("bk_sw_best_bid"), g("bk_sw_best_ask"))
    prv_ok = _two_sided(g("bp_sw_best_bid"), g("bp_sw_best_ask"))
    tgt_ok = _two_sided(g("bn_bid"), g("bn_ask"))
    bm = np.where(cur_ok, (g("bk_sw_best_bid") + g("bk_sw_best_ask")) / 2, np.nan)
    bm_prev = np.where(prv_ok, (g("bp_sw_best_bid") + g("bp_sw_best_ask")) / 2, np.nan)
    bm_next = np.where(tgt_ok, (g("bn_bid") + g("bn_ask")) / 2, np.nan)
    d_bid = np.where(prv_ok & cur_ok, g("bk_sw_best_bid") - g("bp_sw_best_bid"), np.nan)
    d_ask = np.where(prv_ok & cur_ok, g("bk_sw_best_ask") - g("bp_sw_best_ask"), np.nan)
    den = np.abs(d_ask) + np.abs(d_bid)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where(den > 0, np.abs(d_ask - d_bid) / den, 0.0)
    # depth5c: sum of CLOB level SIZES within 5c of the touch (book_sweep._depth) = outcome SHARES, not
    # USDC. D2 converts to USDC at the book mid (shares x price; a +-5c band error, documented).
    depth = g("bk_sw_depth_bid_5c") + g("bk_sw_depth_ask_5c")
    depth_usdc = depth * bm
    out = pd.DataFrame({
        "market_id": d["market_id"].to_numpy(), "cluster": d["event_c"].to_numpy(),
        "day": d["day_c"].to_numpy(), "period": g("t_i"), "t_i": g("t_i"),
        "split": d["split"].to_numpy(), "series_mid": g("mid_i"), "bm": bm,
        "e_t": g("mid_i") - bm, "d_bm_prev": bm - bm_prev,
        "d_series_prev": g("mid_i") - g("mid_prev"), "w": np.where(np.isfinite(d_bid), w, np.nan),
        "depth5c": depth, "depth5c_usdc": depth_usdc, "log_depth": np.log1p(depth),
        "x6": g("f_imb_6h"), "n6": g("f_n_6h"), "sn6": sn6,
        "y_series": g("d_6"), "ok_series": d["ok_6"].to_numpy(bool),
        "y_bm": bm_next - bm, "bm_next": bm_next,
    })
    out["d_bm_x_w"] = out["d_bm_prev"] * out["w"]
    # D2 term: signed 6h notional (USDC) over book depth within 5c (USDC) + 100
    out["flow_pressure"] = out["sn6"] / (out["depth5c_usdc"] + 100.0)
    for c in C0_COLS:
        out[c] = d[c].to_numpy(float)
    base = cur_ok & prv_ok & out["ok_series"].to_numpy(bool) & np.isfinite(out["d_series_prev"])
    ter = _tercile(np.where(base, depth, np.nan))
    counts = {
        "panel_rows": int(n0), "rows_with_book_t": int(cur_ok.sum()),
        "rows_with_books_t_and_prev": int((cur_ok & prv_ok).sum()),
        "rows_base_series_target_ok": int(base.sum()),
        "rows_target_book_unavailable": int((base & ~tgt_ok).sum()),
        "rows_complete": int((base & tgt_ok).sum()),
        "d2_notional_source": sn6_src,
        "units": {"depth5c": "outcome shares (sum of level sizes within 5c; book_sweep._depth)",
                  "depth5c_usdc": "depth5c x book mid (approx USDC)", "sn6": "signed 6h USDC notional",
                  "flow_pressure": "sn6 / (depth5c_usdc + 100)"},
        "rows_sn6_finite": int(np.isfinite(sn6).sum()),
        "target_unavailable_by_liquidity_tercile": {
            str(t): {"base": int((base & (ter == t)).sum()),
                     "target_book_unavailable": int((base & (ter == t) & ~tgt_ok).sum())}
            for t in (0, 1, 2)},
    }
    out = out[base & tgt_ok].reset_index(drop=True)
    for c in out.columns:
        if out[c].dtype == np.float64 and c not in ("t_i", "period"):
            out[c] = out[c].astype(np.float32)
    if log:
        log(json.dumps(_clean(counts)))
    return out, counts


def permute_book_targets(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Placebo: series and book targets permuted together across origins within market."""
    out = df.copy()
    idx = _within_perm(pd.factorize(df["market_id"])[0], seed)
    out["y_series"] = df["y_series"].to_numpy()[idx]
    out["y_bm"] = df["y_bm"].to_numpy()[idx]
    return out


J3_IDS = ("B1", "B2", "B3", "B4", "D1", "D2")


def shuffle_book_increments_placebo(df: pd.DataFrame, seed: int, scheme: str = "permute") -> pd.DataFrame:
    """J3 placebo matched to the expanding estimator. Per market on the 6h grid, the book-mid and the
    panel-series-mid level series are rebuilt from ONE within-market shuffle (same permutation for both)
    of their joint 6h increments, inside contiguous runs of consecutive grid steps (start levels kept;
    pairing the two keeps their contemporaneous co-movement but removes temporal dependence).
    Recomputed from the rebuilt levels: ``bm``, ``bm_next``, ``d_bm_prev``, ``y_bm``, ``series_mid``,
    ``d_series_prev``, ``y_series``, ``e_t``, ``d_bm_x_w``, ``depth5c_usdc``, ``flow_pressure`` and the
    two mid-level controls ``ml_logit_mid`` / ``ml_abs_mid_dev``. NOT recomputable from the 6h grid and
    left as observed: ``c_chg_1h/1d/1w`` and ``c_dprev`` (2h/1h/1d/1w own-history momentum),
    ``x6``, ``n6``, ``sn6``, ``w``, depth."""
    t = df["t_i"].to_numpy(float) if "t_i" in df else df["period"].to_numpy(float) * H6
    step = (t - np.nanmin(t)) / H6
    if not np.allclose(step, np.rint(step), atol=1e-6):
        raise ValueError("book rows are not on a common 6h grid")
    p = np.rint(step).astype(np.int64) - 1  # level index of the t-6h book
    codes = pd.factorize(df["market_id"])[0]
    g = lambda c: df[c].to_numpy(float)  # noqa: E731
    bm, sm = g("bm"), g("series_mid")
    lv = (np.column_stack([bm - g("d_bm_prev"), sm - g("d_series_prev")]),
          np.column_stack([bm, sm]),
          np.column_stack([g("bm_next"), sm + g("y_series")]))
    n0, n1, n2 = _rebuild_shuffled_levels(codes, p, lv, seed, scheme)
    out = df.copy()
    out["bm"], out["bm_next"] = n1[:, 0], n2[:, 0]
    out["d_bm_prev"], out["y_bm"] = n1[:, 0] - n0[:, 0], n2[:, 0] - n1[:, 0]
    out["series_mid"] = n1[:, 1]
    out["d_series_prev"], out["y_series"] = n1[:, 1] - n0[:, 1], n2[:, 1] - n1[:, 1]
    out["e_t"] = out["series_mid"] - out["bm"]
    out["d_bm_x_w"] = out["d_bm_prev"] * g("w")
    out["depth5c_usdc"] = g("depth5c") * out["bm"]
    out["flow_pressure"] = g("sn6") / (out["depth5c_usdc"].to_numpy(float) + 100.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        out["ml_logit_mid"] = np.log(n1[:, 1] / (1 - n1[:, 1]))
    out["ml_abs_mid_dev"] = np.abs(n1[:, 1] - 0.5)
    for c in out.columns:
        if df[c].dtype == np.float32:
            out[c] = out[c].astype(np.float32)
    return out


def book_placebo_family(df: pd.DataFrame, draws: int = 20, seed: int = 117, estimator: str = "expanding",
                        n_boot: int = 20, scheme: str = "permute") -> dict:
    """Run ``book_tests`` on ``draws`` increment-shuffle placebos; same reporting as ``placebo_family``.
    NOTE: B2/B3 regress on e_t, a LEVEL (series minus book), so the permutation scheme's fixed run total
    makes it a bridge that mean-reverts mechanically; see ``_rebuild_shuffled_levels``."""
    out = [book_tests(shuffle_book_increments_placebo(df, seed + k, scheme), {}, n_boot, seed, estimator)
           for k in range(draws)]
    return {**_summarise_placebo(out, list(J3_IDS), estimator, seed), "scheme": scheme}


def book_tests(df: pd.DataFrame, spec: dict | None = None, n_boot: int = 2000, seed: int = 116,
               estimator: str = "pooled") -> dict:
    """B1-B4 (Holm over four, judgement rows), D1/D2 (discovery sign, Stage-1 gate p < 0.01),
    descriptive rho_s, verdict map. ``spec`` may override the minimum-size gates.

    ``estimator="expanding"`` (J3 adoption of J4-R): every regressor (term and control, including C0 and
    the rho_s benchmark's regressor) is replaced by its value minus the market's expanding mean over
    strictly earlier rows (ordered by ``period``), targets stay raw, intercept kept. Default pooled."""
    if estimator not in ESTIMATORS:
        raise ValueError(f"unknown estimator {estimator!r}")
    spec = spec or {}
    min_rows, min_events = spec.get("min_rows", MIN_BOOK_ROWS), spec.get("min_events", MIN_BOOK_EVENTS)
    judge = (df["split"] == "judge").to_numpy()
    disc = (df["split"] == "disc").to_numpy()
    ev = df["cluster"].to_numpy()
    n_j, n_ev = int(judge.sum()), int(len(pd.unique(ev[judge])))
    res: dict = {"n_rows": int(len(df)), "n_judge_rows": n_j, "n_judge_events": n_ev,
                 "n_disc_rows": int(disc.sum()), "tests": {}, "estimator": estimator}
    if n_j < min_rows or n_ev < min_events:
        res["verdicts"] = {"overall": "unavailable",
                           "reason": f"judgement rows {n_j} < {min_rows} or events {n_ev} < {min_events}"}
        return _clean(res)
    per = df["day"].to_numpy()  # J3 second clustering axis = UTC day (not the origin time)
    C0 = list(C0_COLS)
    cols = {c: df[c].to_numpy(float) for c in set(C0) | {
        "bm", "e_t", "d_bm_prev", "w", "d_bm_x_w", "log_depth", "x6", "flow_pressure", "y_series",
        "y_bm", "d_series_prev"}}
    # D1 scaling from discovery only
    ld_mean = float(np.nanmean(cols["log_depth"][disc])) if disc.any() else 0.0
    ld_sd = float(np.nanstd(cols["log_depth"][disc])) if disc.any() else 1.0
    zdepth = (cols["log_depth"] - ld_mean) / (ld_sd if ld_sd > 0 else 1.0)
    d1_term = cols["x6"] * zdepth
    fp = cols["flow_pressure"]
    fp_sd = float(np.nanstd(fp[disc])) if disc.any() else 1.0
    fp_s = fp / (fp_sd if fp_sd > 0 else 1.0)
    if estimator == "expanding":
        codes, ordv = pd.factorize(df["market_id"])[0], df["period"].to_numpy(float)
        ex = lambda a: _expanding_resid(codes, ordv, a)  # noqa: E731
        R = {c: ex(cols[c]) for c in (*C0, "bm", "e_t", "d_bm_prev", "w", "d_bm_x_w", "x6",
                                       "d_series_prev")}
        R.update(zdepth=ex(zdepth), d1_term=ex(d1_term), fp_s=ex(fp_s))
    else:
        R = {c: cols[c] for c in (*C0, "bm", "e_t", "d_bm_prev", "w", "d_bm_x_w", "x6", "d_series_prev")}
        R.update(zdepth=zdepth, d1_term=d1_term, fp_s=fp_s)
    c0 = np.column_stack([R[c] for c in C0])
    defs = {
        "B1": (cols["y_bm"], R["d_bm_prev"], np.column_stack([c0, R["bm"]]), 0),
        "B2": (cols["y_series"], R["e_t"], np.column_stack([c0, R["bm"], R["d_bm_prev"]]), 0),
        "B3": (cols["y_bm"], R["e_t"], np.column_stack([c0, R["bm"], R["d_bm_prev"]]), 0),
        "B4": (cols["y_bm"], R["d_bm_x_w"], np.column_stack([c0, R["d_bm_prev"], R["w"]]), 0),
        "D1": (cols["y_series"], R["d1_term"], np.column_stack([c0, R["x6"], R["zdepth"]]), None),
        "D2": (cols["y_bm"], R["fp_s"], np.column_stack([c0, R["x6"]]), 1),
    }
    for name, (y, x, Z, fixed_sign) in defs.items():
        ok = np.isfinite(y) & np.isfinite(x) & np.all(np.isfinite(Z), axis=1)
        mj, md = ok & judge, ok & disc
        r: dict = {"n_judge": int(mj.sum()), "n_disc": int(md.sum())}
        if mj.sum() < 30:
            r.update(testable=False, p=1.0, reason="fewer than 30 complete judgement rows")
            res["tests"][name] = r
            continue
        sign = fixed_sign
        if name == "D1":
            sign = None
            if md.sum() >= 300:
                rd = fit_test(y[md], x[md], Z[md], ev[md], per[md], 200, seed)
                if rd.get("testable") and rd["beta"] != 0:
                    sign = int(np.sign(rd["beta"]))
                    r["discovery_beta"] = rd["beta"]
            r["sign_source"] = "discovery" if sign else "none (discovery untestable)"
        t = fit_test(y[mj], x[mj], Z[mj], ev[mj], per[mj], n_boot, seed)
        r.update(t)
        if t.get("testable") and sign is not None and name in ("D1", "D2"):
            # one-sided p in the tested direction, max over the two clusterings
            pe = float(norm.sf(sign * t["beta"] / t["se_event"]))
            p2 = float(norm.sf(sign * t["beta"] / t["se_twoway"]))
            r["sign_tested"] = sign
            r["p_one_sided"] = max(pe, p2)
            r["advance_stage1"] = bool(r["p_one_sided"] < 0.01)
        res["tests"][name] = r
    b_adj = holm({k: res["tests"][k]["p"] for k in ("B1", "B2", "B3", "B4")})
    for k, p in b_adj.items():
        res["tests"][k]["p_holm"] = p
        res["tests"][k]["reject"] = bool(p < ALPHA)
    # horizon-matched benchmark rho_s (descriptive, not counted)
    ok = (np.isfinite(cols["y_series"]) & np.isfinite(R["d_series_prev"]) & np.all(np.isfinite(c0), axis=1)
          & judge)
    rho = fit_test(cols["y_series"][ok], R["d_series_prev"][ok], c0[ok], ev[ok], per[ok], n_boot, seed)
    res["rho_s"] = {k: rho.get(k) for k in ("testable", "beta", "se", "ci95", "n")}
    res["flow_pressure_units"] = "signed 6h USDC notional / (depth5c shares x book mid + 100)"
    res["second_clustering"] = "UTC day (day_c)"
    res["verdicts"] = book_verdicts(res)
    return _clean(res)


def book_verdicts(res: dict) -> dict:
    T = res["tests"]
    b1, b2, b4 = T["B1"], T["B2"], T["B4"]
    rho = res.get("rho_s", {})
    out: dict = {"mde_80_by_test": {k: t.get("mde_80") for k, t in T.items()}}
    if not (b1.get("testable") and b4.get("testable") and rho.get("testable")):
        out["overall"] = "inconclusive (a required test is not testable)"
        return out
    half = rho["beta"] / 2
    b1_rej_neg = _rej(b1, -1)
    c1 = cons_ci(b1)
    out["bound_intervals"] = {"B1.measurement_bounce": {
        "interval": list(c1[0]), "binding": c1[1][0], "rule": "lo95_cons > rho_s/2"}}
    if b2.get("testable") and _rej(b2, -1) and not b1["reject"] and c1[0][0] > half:
        out["overall"] = "measurement/bounce"
    elif b1_rej_neg and _rej(b4, -1):
        out["overall"] = "quote refill"
    elif b1_rej_neg and not b4["reject"]:
        out["overall"] = "book-mid mean reversion"
    else:
        out["overall"] = "inconclusive"
    out["rho_s_half"] = half
    out["ceiling"] = "L1 (h2 only; no replication data)"
    return out


# =============================================================================================
# Trial logging
# =============================================================================================


def log_trials(job: str, results: dict, results_path: str, results_sha256: str, run_id: str,
               prov: dict, placebo: dict | None = None, path: Path = provenance.TRIALS_PATH,
               dataset: str | None = None, revision: str | None = None) -> list[dict]:
    """One trial line per test (kind bounce_decomp / book_decomp), one ml_explain count line, and
    one placebo line (count 0) per test. ``job`` is "J4" or "J3". Appends to ``path``."""
    kind = KIND_J4 if job == "J4" else KIND_J3
    role = "exploratory_dev" if job == "J4" else "exploratory_historical"
    dataset = dataset or ("snapshots" if job == "J4" else "history:h2_main")
    names = list(J4_SPEC) if job == "J4" else list(J3_IDS)
    written = []

    def line(name: str, t: dict, role_: str, tag: str) -> None:
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": f"{name}{tag}", "run_id": run_id,
            "label": LABEL, "kind": kind, "evidence_role": role_, "revision": revision or f"sb2_{job.lower()}",
            "result_path": results_path, "results_sha256": results_sha256,
            "summary": _clean({**{k: t.get(k) for k in ("beta", "se", "p", "p_holm", "reject", "n",
                                                        "ci95", "mde_80", "p_one_sided",
                                                        "advance_stage1")},
                               **{k: t[k] for k in ("covers_zero", "betas", "beta_sd") if k in t}}),
            "provenance": prov}, path))

    for n in names:
        if n in results.get("tests", {}):
            line(n, results["tests"][n], role, "")
    for n in names:
        if placebo and n in placebo.get("tests", {}):
            line(n, placebo["tests"][n], "placebo", ":placebo")
    written.append(provenance.append_trial({
        "dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY",
        "n_tests": len(names), "revision": revision or f"sb2_{job.lower()}", "run_id": run_id,
        "source": f"screening_batch_2:{job}", "results_sha256": results_sha256,
        "note": "SB2 bounce decomposition count line; the per-test bounce/book_decomp lines are "
                "excluded in battery2.KIND_RULES to avoid double counting",
        "prior_tests": results.get("prior_tests"),
    }, path))
    return written


def prior_tests(path: Path = provenance.TRIALS_PATH) -> dict:
    return battery2.cumulative_count(path)

