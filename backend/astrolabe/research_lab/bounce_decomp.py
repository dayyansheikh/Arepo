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
# J4: snapshot triples
# =============================================================================================


def _read_capture(cap: dict) -> pd.DataFrame:
    path = Path(cap["dir"]) / "rows.csv.gz"
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in SNAP_USECOLS if c in header]
    df = pd.read_csv(path, usecols=use, dtype={"market_id": str, "event_id": str})
    for c in SNAP_USECOLS:
        if c not in df.columns:
            df[c] = np.nan
    for c in _FLOAT_COLS:
        df[c] = df[c].astype(np.float32)
    return df.drop_duplicates("market_id").reset_index(drop=True)


def iter_captures(snapshot_root: Path = SNAPSHOT_ROOT, until_utc: str | None = None
                  ) -> Iterator[tuple[dict, pd.DataFrame]]:
    """Complete captures in start order, one frame at a time (``until_utc``: started <= that)."""
    caps = forecast.list_complete_captures(snapshot_root)
    if until_utc is not None:
        cut = forecast._parse_ts(until_utc)
        caps = [c for c in caps if c["_start"] <= cut]
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
    df = pd.read_csv(best[1] / "rows.csv.gz",
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


def build_triple(snap_h: pd.DataFrame, snap_i: pd.DataFrame, snap_j: pd.DataFrame, i_start: str,
                 j_start: str, period: int, sweep: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    """One triple. Eligibility/target from ``panel.build_pair(i, j)`` (E001 semantics); features
    from capture i, the quote changes from h; capture j only supplies target columns."""
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
    for c in out.columns:
        if out[c].dtype == np.float64:
            out[c] = out[c].astype(np.float32)
    cnt.update({"triple_rows": int(len(out)), "h_quote_ok": int(np.isfinite(d_bm).sum()),
                "ltp_missing_or_nonpositive": int(np.isnan(b_pos).sum()),
                "sweep_available": int(np.isfinite(B_i).sum()),
                "sweep_lag_gt_20min": int((lag > SWEEP_MAX_LAG_MIN).sum()),
                "sweep_lag_negative": int((lag < 0).sum())})
    return out, cnt


def build_snapshot_triples(snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT,
                           until_utc: str | None = None, log: Callable[[str], None] | None = None
                           ) -> tuple[pd.DataFrame, list[dict]]:
    """All triples ``(h, i, j)`` of consecutive complete captures with gap(h,i), gap(i,j) in
    [1.5, 3] h; three captures in memory at most, only the needed columns."""
    window: list[tuple[dict, pd.DataFrame]] = []
    frames: list[pd.DataFrame] = []
    counts: list[dict] = []
    k = 0
    for meta, df in iter_captures(snapshot_root, until_utc):
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
        trip, cnt = build_triple(sh, si, sj, mi["start_utc"], mj["start_utc"], k, sweep)
        cnt.update(base)
        cnt["sweep_found"] = sweep is not None
        frames.append(trip)
        counts.append(cnt)
        if log:
            log(json.dumps(_clean(cnt)))
        k += 1
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


def _rows_for(df: pd.DataFrame, name: str) -> np.ndarray:
    sp = J4_SPEC[name]
    cols = [sp["target"], sp["term"], *sp["controls"]]
    m = np.ones(len(df), bool)
    for c in cols:
        m &= np.isfinite(df[c].to_numpy(float))
    if name == "P1x":
        lag = df["sweep_lag_min"].to_numpy(float)
        with np.errstate(invalid="ignore"):
            m &= (lag >= 0) & (lag <= SWEEP_MAX_LAG_MIN)  # sweep before Gamma receipt: excluded too
    if name == "P2":
        m &= df["volume_up"].to_numpy(bool)
    return m


def snapshot_tests(df: pd.DataFrame, n_boot: int = 2000, seed: int = 116) -> dict:
    """P1, P1x, P2, P3, P4 (Holm over the 5), LODO sign rule, descriptive extras."""
    res: dict = {"tests": {}, "descriptive": {}}
    ev, per, day = df["cluster"].to_numpy(), df["period"].to_numpy(), df["day"].to_numpy()
    for name, sp in J4_SPEC.items():
        m = _rows_for(df, name)
        scale = 100.0 if name == "P2" else 1.0  # P2 in cents per unit b_pos
        y = df[sp["target"]].to_numpy(float)[m] * scale
        x = df[sp["term"]].to_numpy(float)[m]
        Z = df[list(sp["controls"])].to_numpy(float)[m]
        r = fit_test(y, x, Z, ev[m], per[m], n_boot, seed)
        r.update(label=sp["label"], rows_used=int(m.sum()), rows_candidate=int(len(df)))
        if r["testable"]:
            r["lodo"] = lodo(y, x, Z, day[m], r["beta"])
        if name == "P2":
            vm = np.isfinite(df["b_pos"].to_numpy(float)) & np.isfinite(df["dmid"].to_numpy(float))
            share = {"all": float(1 - (vm & m).sum() / max(vm.sum(), 1))}
            ter = _tercile(df["liquidity_i"].to_numpy(float))
            share["by_liquidity_tercile"] = {
                str(t): float(1 - (vm & m & (ter == t)).sum() / max((vm & (ter == t)).sum(), 1))
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
    res["descriptive"] = _snapshot_descriptive(df, n_boot, seed)
    res["n_triples"] = int(len(df))
    res["n_clusters"] = int(len(pd.unique(ev)))
    res["n_periods"] = int(len(pd.unique(per)))
    res["utc_days"] = sorted(str(d) for d in pd.unique(day))
    res["verdicts"] = verdicts(res)
    return _clean(res)


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


def book_tests(df: pd.DataFrame, spec: dict | None = None, n_boot: int = 2000, seed: int = 116) -> dict:
    """B1-B4 (Holm over four, judgement rows), D1/D2 (discovery sign, Stage-1 gate p < 0.01),
    descriptive rho_s, verdict map. ``spec`` may override the minimum-size gates."""
    spec = spec or {}
    min_rows, min_events = spec.get("min_rows", MIN_BOOK_ROWS), spec.get("min_events", MIN_BOOK_EVENTS)
    judge = (df["split"] == "judge").to_numpy()
    disc = (df["split"] == "disc").to_numpy()
    ev = df["cluster"].to_numpy()
    n_j, n_ev = int(judge.sum()), int(len(pd.unique(ev[judge])))
    res: dict = {"n_rows": int(len(df)), "n_judge_rows": n_j, "n_judge_events": n_ev,
                 "n_disc_rows": int(disc.sum()), "tests": {}}
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
    c0 = np.column_stack([cols[c] for c in C0])
    defs = {
        "B1": (cols["y_bm"], cols["d_bm_prev"], np.column_stack([c0, cols["bm"]]), 0),
        "B2": (cols["y_series"], cols["e_t"], np.column_stack([c0, cols["bm"], cols["d_bm_prev"]]), 0),
        "B3": (cols["y_bm"], cols["e_t"], np.column_stack([c0, cols["bm"], cols["d_bm_prev"]]), 0),
        "B4": (cols["y_bm"], cols["d_bm_x_w"], np.column_stack([c0, cols["d_bm_prev"], cols["w"]]), 0),
        "D1": (cols["y_series"], d1_term, np.column_stack([c0, cols["x6"], zdepth]), None),
        "D2": (cols["y_bm"], fp_s, np.column_stack([c0, cols["x6"]]), 1),
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
    ok = (np.isfinite(cols["y_series"]) & np.isfinite(cols["d_series_prev"]) & np.all(np.isfinite(c0), axis=1)
          & judge)
    rho = fit_test(cols["y_series"][ok], cols["d_series_prev"][ok], c0[ok], ev[ok], per[ok], n_boot, seed)
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
               dataset: str | None = None) -> list[dict]:
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
            "label": LABEL, "kind": kind, "evidence_role": role_, "revision": f"sb2_{job.lower()}",
            "result_path": results_path, "results_sha256": results_sha256,
            "summary": _clean({k: t.get(k) for k in ("beta", "se", "p", "p_holm", "reject", "n",
                                                     "ci95", "mde_80", "p_one_sided",
                                                     "advance_stage1")}),
            "provenance": prov}, path))

    for n in names:
        if n in results.get("tests", {}):
            line(n, results["tests"][n], role, "")
    for n in names:
        if placebo and n in placebo.get("tests", {}):
            line(n, placebo["tests"][n], "placebo", ":placebo")
    written.append(provenance.append_trial({
        "dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY",
        "n_tests": len(names), "revision": f"sb2_{job.lower()}", "run_id": run_id,
        "source": f"screening_batch_2:{job}", "results_sha256": results_sha256,
        "note": "SB2 bounce decomposition count line; the per-test bounce/book_decomp lines are "
                "excluded in battery2.KIND_RULES to avoid double counting",
        "prior_tests": results.get("prior_tests"),
    }, path))
    return written


def prior_tests(path: Path = provenance.TRIALS_PATH) -> dict:
    return battery2.cumulative_count(path)

