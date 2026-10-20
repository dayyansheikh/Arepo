# ruff: noqa: E501
"""Single registered analysis of the live tests E015-E019 (docs/research_lab/LIVE_TESTS_3.md, sections 1-9 as amended
by section 13). DRAFT until registered.

Runs ONCE, after ``live_tests3.ANALYSIS_NOT_BEFORE``, on the write-once files of ``live_tests3``. One Holm family over
the k primaries that survived their census gates (spec ``k_tests``), one-sided, familywise alpha 0.05. A primary that is
unavailable or fails its gate enters Holm with p = 1. Mechanism readings, secondaries, labels and economics never change
a verdict (labels are attached) and count 0.

Estimators: expanding-past demeaning (J4-R; every regressor minus the mean of the market's, E019 the event's, strictly
earlier units; the target raw) for E015, E016, E018, E019; the full-sample market fixed-effects estimator for E017.
Inference: CR1 on the event (E019: series-or-event family) and on the UTC day of the origin (E017: two-day blocks from
the window start); primary one-sided p = max(p_event with a normal reference (E019: t on G_series - 1 df), p_time with a
t reference on G - 1 df).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import battery
from . import bounce_decomp as bd
from . import live_tests3 as lt

TESTS = ("E015", "E016", "E017", "E018", "E019")
DIRECTION = {"E015": +1, "E016": +1, "E017": +1, "E018": -1, "E019": +1}
N_BOOT = 2000
BLOCK_S = 2 * 86400.0
CONTROLS_E015 = ["log_abs_x", "spread_k", "abs_dev", "logit_mid", "log1p_vol"]
CONTROLS_E017 = ["SM", "logit_mid", "abs_dev", "log_hte", "hte_missing", "log1p_vol_p", "chg_1d", "chg_1d_missing", "x_km1", "x_km1_missing"]
CONTROLS_E019 = ["log_n_elig", "mean_log_abs_x", "mean_spread", "sh_os", "sh_sc"]
FLOW_BASE = ["logit_mid", "abs_dev", "chg_1h", "chg_1h_missing", "chg_1d", "chg_1d_missing", "chg_1w", "chg_1w_missing",
             "dprev", "dprev_missing", "hte_missing", "rv_missing"]


# --- pins -----------------------------------------------------------------------------------------------------------


def code_check(spec: dict) -> dict:
    """Compare the modules on disk with the spec's ``code_sha256`` map; a pinned spec refuses on any mismatch, an
    unfilled map, null ``k_tests``, an unfilled V* or unfilled census scales; a DRAFT spec only labels the result."""
    pins = spec.get("code_sha256") or {}
    cur = lt.code_hashes()
    status = {n: ("not pinned" if pins.get(n) is None else ("match" if pins.get(n) == h else "MISMATCH")) for n, h in cur.items()}
    if spec.get("_pinned"):
        bad = {n: s for n, s in status.items() if s != "match"}
        if bad:
            raise RuntimeError(f"live_tests3 code sha256 does not match the registered pins: {bad}")
        if spec.get("k_tests") is None:
            raise RuntimeError("live_tests3 spec pinned with null k_tests")
        if any(t in spec["k_tests"] for t in ("E016", "E018")):
            f = spec["flow"]
            cap = f.get("vol24_cap")
            if cap is None or (isinstance(cap, float) and np.isnan(cap)) or any(f[z].get("scale") is None for z in ("zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE")):
                raise RuntimeError("live_tests3 spec pinned with unfilled flow census values")
        if "E019" in spec["k_tests"] and spec["e019"].get("exclude_crypto") is None:
            raise RuntimeError("live_tests3 spec pinned with unfilled e019.exclude_crypto")
    return {"current": cur, "pinned": {n: pins.get(n) for n in cur}, "status": status,
            "label": None if all(s == "match" for s in status.values()) else "DRAFT: code hashes not verified"}


# --- loading --------------------------------------------------------------------------------------------------------


def load_kind(root: Path, kind: str, start: float, end: float, roles: tuple[str, ...], spec: dict | None,
              tags: tuple[str, ...]) -> tuple[pd.DataFrame, dict]:
    """Frozen lines of origins in [start, end) with an allowed role (and, with a pinned spec, the pinned spec and code
    hashes), merged with their outcome files (columns suffixed ``_<tag>``). Counts dropped lines, late markers and
    no-previous-slot markers."""
    fdir, odir = Path(root) / kind / "frozen", Path(root) / kind / "outcomes"
    pinned = bool(spec and spec.get("_pinned"))
    want_spec = spec["_sha256"][:16] if pinned else None
    want_code = ((spec.get("code_sha256") or {}).get("live_tests3.py") or "")[:16] if pinned else None
    acc = {"files": 0, "late_files": 0, "noprev_files": 0, "dropped_role": 0, "dropped_spec_sha": 0, "dropped_code_sha": 0}
    parts = []
    for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
        if p.name.endswith(".late.csv.gz"):
            acc["late_files"] += 1
            continue
        if p.name.endswith(".noprev.csv.gz"):
            acc["noprev_files"] += 1
            continue
        fr = pd.read_csv(p, dtype={"market_id": str, "event_id": str, "spec_sha": str, "code_sha": str, "skey": str})
        if not len(fr) or not (start <= float(fr["capture_t"].iloc[0]) < end):
            continue
        acc["files"] += 1
        keep = fr["role"].isin(roles)
        acc["dropped_role"] += int((~keep).sum())
        fr = fr[keep]
        if pinned:
            ok = fr["spec_sha"].astype(str) == want_spec
            acc["dropped_spec_sha"] += int((~ok).sum())
            fr = fr[ok]
            ok = fr["code_sha"].astype(str) == want_code
            acc["dropped_code_sha"] += int((~ok).sum())
            fr = fr[ok]
        fid = p.name[:-7]
        for tag in tags:
            op = odir / f"{fid}.{tag}.csv.gz"
            if op.exists():
                out = pd.read_csv(op, dtype={"market_id": str, "status": str, "cap_id": str}).drop_duplicates("market_id")
                out = out.rename(columns={c: f"{c}_{tag}" for c in out.columns if c != "market_id"})
                fr = fr.merge(out, on="market_id", how="left")
            else:
                fr[f"status_{tag}"] = "pending"
        fr["file"] = fid
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    tot = acc["files"] + acc["late_files"]
    acc["late_loss_share"] = acc["late_files"] / tot if tot else 0.0
    return df, acc


def day_of(t) -> np.ndarray:
    return pd.to_datetime(np.asarray(t, float), unit="s", utc=True).strftime("%Y-%m-%d").to_numpy()


def block_of(t, start: float) -> np.ndarray:
    return np.floor((np.asarray(t, float) - start) / BLOCK_S).astype(int).astype(str)


def late_mask(df: pd.DataFrame, tag: str) -> np.ndarray:
    """True where the line was frozen at or after the start of its ``tag`` target capture (excluded, counted)."""
    if f"cap_start_{tag}" not in df:
        return np.zeros(len(df), bool)
    fz = lt.panel._epoch(df["frozen_utc"])
    cs = df[f"cap_start_{tag}"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        return np.isfinite(cs) & ~(fz < cs)


def mid_at(df: pd.DataFrame, tag: str) -> np.ndarray:
    two = df.get(f"status_{tag}", pd.Series("", index=df.index)).astype(str).to_numpy() == "two_sided"
    if f"bid_{tag}" in df:
        m = (df[f"bid_{tag}"].to_numpy(float) + df[f"ask_{tag}"].to_numpy(float)) / 2.0
    else:
        m = (df[f"sbid_{tag}"].to_numpy(float) + df[f"sask_{tag}"].to_numpy(float)) / 2.0
    return np.where(two, m, np.nan)


# --- estimator and inference ----------------------------------------------------------------------------------------


def demean(df: pd.DataFrame, cols: list[str], group: str, order: str, estimator: str) -> pd.DataFrame:
    X = df[cols].astype(float)
    if estimator == "expanding":
        return bd.expanding_demean(pd.concat([X, df[[group, order]]], axis=1), cols, group, order)[cols]
    if estimator == "fe":
        return X - X.groupby(df[group].to_numpy()).transform("mean")
    return X


def fit(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, sign: int, group: str = "market_id",
        order: str = "t_row", estimator: str = "expanding", ev: str = "event_id", time: str = "day",
        ev_t_ref: bool = False, seed: int = 0, n_boot: int = N_BOOT) -> dict:
    """Slope of ``term`` given ``controls`` with the section 1.7 inference. ``sign`` = predicted direction. FE also
    demeans the target (within estimator). ``ev_t_ref``: the event-family p uses t on G_ev - 1 df (E019, finding 2)."""
    cols = [term, *controls]
    if len(df) < 10:
        return {"testable": False, "reason": "fewer than 10 rows", "n": len(df), "p": 1.0}
    X = demean(df, cols, group, order, estimator)
    yy = np.asarray(y, float)
    if estimator == "fe":
        yy = yy - pd.Series(yy).groupby(df[group].to_numpy()).transform("mean").to_numpy()
    ok = np.isfinite(yy) & np.all(np.isfinite(X.to_numpy()), axis=1)
    if ok.sum() < 10:
        return {"testable": False, "reason": "fewer than 10 rows", "n": int(ok.sum()), "p": 1.0}
    Xo = X.to_numpy()[ok]
    evv, tv = df[ev].astype(str).to_numpy()[ok], df[time].astype(str).to_numpy()[ok]
    r = battery.beta_test(yy[ok], Xo[:, 0], Xo[:, 1:], evv, tv, sign=sign, n_boot=n_boot, seed=seed)
    if not r.get("testable"):
        return {"testable": False, "reason": r.get("reason"), "n": int(ok.sum()), "p": 1.0}
    g_t, g_e = int(r["n_day"]), int(r["n_event"])
    z_t = r["beta"] / r["se_day"] if r["se_day"] > 0 else 0.0
    r["z_time"] = z_t
    r["p_time_t"] = float(t_dist.sf(sign * z_t, df=g_t - 1)) if g_t >= 2 else 1.0
    if ev_t_ref:
        r["p_event"] = float(t_dist.sf(sign * r["z_event"], df=g_e - 1)) if g_e >= 2 else 1.0
        r["p_event_ref"] = f"t on {g_e - 1} df"
    r["p"] = max(float(r["p_event"]), r["p_time_t"])
    tq = float(t_dist.ppf(0.975, g_t - 1)) if g_t >= 2 else float("inf")
    te = float(t_dist.ppf(0.975, g_e - 1)) if (ev_t_ref and g_e >= 2) else bd.Z95
    ci = r.get("ci_event_boot") or [None, None]
    lo = [v for v in (ci[0], r["beta"] - te * r["se_event"], r["beta"] - tq * r["se_day"]) if v is not None]
    hi = [v for v in (ci[1], r["beta"] + te * r["se_event"], r["beta"] + tq * r["se_day"]) if v is not None]
    r.update(ci95_cons=[min(lo), max(hi)], t_df=g_t - 1, estimator=estimator, time_cluster=time, event_cluster=ev,
             n_group=int(pd.unique(df[group].to_numpy()[ok]).size), _mask=ok)
    return r


def strip(r: dict | None) -> dict | None:
    return None if r is None else {k: v for k, v in r.items() if not k.startswith("_")}


def _partial(Z: np.ndarray, v: np.ndarray) -> np.ndarray:
    Z1 = np.column_stack([np.ones(len(v)), Z]) if Z.size else np.ones((len(v), 1))
    c, *_ = np.linalg.lstsq(Z1, v, rcond=None)
    return v - Z1 @ c


def fast_beta(x: np.ndarray, Zt: np.ndarray, yt: np.ndarray) -> float:
    xt = _partial(Zt, x)
    s = float(xt @ xt)
    return float(xt @ yt / s) if s > 1e-18 else float("nan")


def perm_gate(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, sign: int, group: str, order: str,
              strata: np.ndarray, draws: int, seed: int, min_stratum: int) -> dict:
    """Label-permutation gate (section 1.8): the class label is permuted within strata (market or event x UTC day)
    with >= ``min_stratum`` contrasted units, target and controls attached; the estimator (demeaning included) is re-run.
    p_perm = (1 + #{sign * draw >= sign * real}) / (1 + draws) < alpha passes."""
    Xc = demean(df, controls, group, order, "expanding").to_numpy() if controls else np.zeros((len(df), 0))
    xr = demean(df, [term], group, order, "expanding")[term].to_numpy()
    ok = np.isfinite(y) & np.isfinite(xr) & np.all(np.isfinite(Xc), axis=1)
    if ok.sum() < 10:
        return {"testable": False, "passes": False, "reason": "fewer than 10 rows"}
    yt = _partial(Xc[ok], np.asarray(y, float)[ok])
    real = fast_beta(xr[ok], Xc[ok], yt)
    codes = pd.factorize(pd.Series(strata).astype(str))[0]
    sz = np.bincount(codes)
    perm_rows = sz[codes] >= min_stratum
    rng = np.random.default_rng(seed)
    raw = df[term].to_numpy(float)
    by_code = np.argsort(codes, kind="mergesort")
    ge = 0
    for _ in range(draws):
        shuf = np.lexsort((rng.random(len(codes)), codes))  # within-stratum random order, strata in the same order
        lab = raw.copy()
        lab[by_code] = raw[shuf]
        lab[~perm_rows] = raw[~perm_rows]
        d = df[[group, order]].copy()
        d[term] = lab
        xd = demean(d, [term], group, order, "expanding")[term].to_numpy()
        b = fast_beta(xd[ok], Xc[ok], yt)
        ge += int(np.isfinite(b) and sign * b >= sign * real)
    p = (1 + ge) / (1 + draws)
    return {"testable": True, "real": real, "p_perm": p, "passes": bool(p < 0.05), "draws": draws,
            "share_rows_permuted": float(perm_rows[ok].mean())}


def donor_plan(codes: np.ndarray, t: np.ndarray, min_sep_s: float) -> dict:
    """Eligible distant donors of every unit: units of the same market whose origin is at least ``min_sep_s`` away
    (two contiguous ranges of the market's time-sorted units). Computed once; draws only add randomness."""
    n = len(t)
    o = np.lexsort((t, codes))
    c, ts = codes[o], np.asarray(t, float)[o]
    starts = np.r_[0, np.flatnonzero(c[1:] != c[:-1]) + 1] if n else np.zeros(0, int)
    ends = np.r_[starts[1:], n] if n else np.zeros(0, int)
    gs = np.repeat(starts, ends - starts)
    ge_ = np.repeat(ends, ends - starts)
    # offset by market so one global searchsorted works: markets are far apart on the shifted axis
    span = (np.nanmax(ts) - np.nanmin(ts) + 10 * min_sep_s + 1.0) if n else 1.0
    key = c.astype(float) * span + (ts - (np.nanmin(ts) if n else 0.0))
    lo = np.searchsorted(key, key - min_sep_s, side="right")
    hi = np.searchsorted(key, key + min_sep_s, side="left")
    n_left = lo - gs
    n_right = ge_ - hi
    return {"o": o, "gs": gs, "hi": hi, "n_left": n_left, "cnt": n_left + n_right}


def donor_indices(plan: dict, rng: np.random.Generator, min_donors: int) -> tuple[np.ndarray, np.ndarray]:
    """One distant-donor draw (uniform with replacement among the eligible donors); units with fewer than
    ``min_donors`` eligible donors keep their own index. Returns (donor index, has_donors flag) in input order."""
    o, gs, hi, n_left, cnt = (plan[k] for k in ("o", "gs", "hi", "n_left", "cnt"))
    n = len(o)
    has = cnt >= min_donors
    u = np.floor(rng.random(n) * np.maximum(cnt, 1)).astype(int)
    pick = np.where(u < n_left, gs + u, hi + (u - n_left))
    pick = np.where(has, pick, np.arange(n))
    out = np.empty(n, int)
    out[o] = o[pick]
    hflag = np.empty(n, bool)
    hflag[o] = has
    return out, hflag


def donor_gate(df: pd.DataFrame, y: np.ndarray, flow: str, mod: str, others: list[str], *, sign: int, draws: int, seed: int,
               min_units: int, min_sep_s: float, min_donors: int) -> dict:
    """Distant-donor gate (section 1.8, LT2 finding 1): only markets with >= ``min_units`` usable units; in each draw
    every unit's moderator is replaced by a distant donor's (same market, >= ``min_sep_s`` away) in both the
    interaction and the main effect; everything else unchanged; the estimator is re-run."""
    d = df.reset_index(drop=True)
    yv = np.asarray(y, float)
    use = np.isfinite(yv) & np.isfinite(d[flow].to_numpy(float)) & np.isfinite(d[mod].to_numpy(float))
    nmk = d.loc[use].groupby("market_id").size()
    keep = use & d["market_id"].isin(nmk[nmk >= min_units].index).to_numpy()
    d, yv = d[keep].reset_index(drop=True), yv[keep]
    if len(d) < 10:
        return {"testable": False, "passes": False, "reason": "fewer than 10 gate rows", "rows": len(d)}
    term = "__int"
    d[term] = d[flow].to_numpy(float) * d[mod].to_numpy(float)
    ctrl = [mod, *others]
    X = demean(d, [term, *ctrl], "market_id", "t_row", "expanding")
    ok = np.all(np.isfinite(X.to_numpy()), axis=1)
    rest = X[others].to_numpy()[ok] if others else np.zeros((int(ok.sum()), 0))
    Z = np.column_stack([X[mod].to_numpy()[ok], rest])
    yt = _partial(Z, yv[ok])
    real = fast_beta(X[term].to_numpy()[ok], Z, yt)
    codes = pd.factorize(d["market_id"])[0]
    tt = d["t_row"].to_numpy(float)
    rng = np.random.default_rng(seed)
    ge, kept = 0, 0
    fl, mv = d[flow].to_numpy(float), d[mod].to_numpy(float)
    plan = donor_plan(codes, tt, min_sep_s)
    for _ in range(draws):
        idx, has = donor_indices(plan, rng, min_donors)
        kept = int((~has).sum())
        dd = d[["market_id", "t_row"]].copy()
        dd["__m"] = mv[idx]
        dd["__i"] = fl * mv[idx]
        Xd = demean(dd, ["__i", "__m"], "market_id", "t_row", "expanding").to_numpy()
        okd = ok & np.all(np.isfinite(Xd), axis=1)
        if okd.sum() != ok.sum():
            continue
        Zd = np.column_stack([Xd[ok, 1], rest])
        ytd = _partial(Zd, yv[ok])
        b = fast_beta(Xd[ok, 0], Zd, ytd)
        ge += int(np.isfinite(b) and sign * b >= sign * real)
    p = (1 + ge) / (1 + draws)
    return {"testable": True, "real": real, "p_perm": p, "passes": bool(p < 0.05), "draws": draws, "rows": int(ok.sum()),
            "markets": int(d["market_id"].nunique()), "units_without_donors": kept}


# --- verdicts, labels, attrition, economics --------------------------------------------------------------------------


def verdict(r: dict, gate: dict | None, available: bool, holm_p: float | None, sign: int, gate_label: str) -> dict:
    if not available:
        return {"verdict": "Unavailable", "p_for_holm": 1.0}
    if not r.get("testable"):
        return {"verdict": "Unavailable (untestable)", "p_for_holm": 1.0}
    lo, hi = r["ci95_cons"]
    contra = (hi < 0) if sign > 0 else (lo > 0)
    out = {"ci95_cons": [lo, hi]}
    if gate is not None and not gate.get("passes"):
        return {**out, "verdict": "Contradicted" if contra else f"Inconclusive ({gate_label})", "p_for_holm": 1.0, "gate_failed": True}
    out["p_for_holm"] = float(r["p"])
    if holm_p is None:
        return out
    if holm_p < 0.05 and sign * r["beta"] > 0:
        out["verdict"] = "Supported (exploratory, prospective)"
    elif contra:
        out["verdict"] = "Contradicted"
    else:
        out["verdict"] = "Inconclusive"
    return out


def check_fraction(primary_beta, chk: dict | None, sign: int, need_p: bool, frac: float) -> bool:
    """True if the check reaches ``frac`` x the primary (sign-adjusted) and, with ``need_p``, has one-sided p < 0.05."""
    chk = chk or {}
    if not chk.get("testable") or primary_beta is None or chk.get("beta") is None:
        return False
    ok = sign * chk["beta"] >= frac * sign * primary_beta
    if need_p:
        ok = ok and (chk.get("p") if chk.get("p") is not None else 1.0) < 0.05
    return bool(ok)


def attach(v: dict, labels: list[str | None]) -> dict:
    labels = [x for x in labels if x]
    if not labels or str(v.get("verdict", "")).startswith("Unavailable"):
        return v
    return {**v, "verdict": v.get("verdict", "") + "; " + "; ".join(labels), "labels": labels}


def underpowered(r: dict, k: int, ref: float) -> bool:
    if not r.get("testable"):
        return False
    g = int(r.get("n_day") or 0)
    if g < 2:
        return True
    mde = (float(t_dist.ppf(1 - 0.05 / max(k, 1), g - 1)) + float(t_dist.ppf(0.8, g - 1))) * float(r["se_day"])
    r["mde_realised"] = mde
    return bool(mde > ref)


def attrition(status: np.ndarray, cls: np.ndarray, pair: tuple, pp: float) -> dict:
    """Non-two_sided share (capture_missing and pending excluded) by contrasted class; ``triggered`` if the absolute
    difference exceeds ``pp``. Also the absent share by class."""
    s = pd.Series(np.asarray(status, object)).astype(str)
    c = np.asarray(cls, object)
    keep = ~s.isin(["capture_missing", "pending"]).to_numpy()
    out, sh = {}, {}
    for lab in pair:
        m = keep & (c == lab)
        sub = s[m]
        sh[lab] = float((sub != "two_sided").mean()) if len(sub) else None
        out[str(lab)] = {"units": int(len(sub)), "lost": int((sub != "two_sided").sum()),
                         "absent_share": float((sub == "absent").mean()) if len(sub) else None,
                         "by_status": {str(k): int(v) for k, v in sub.value_counts().items()}}
    diff = None if None in sh.values() else sh[pair[0]] - sh[pair[1]]
    out.update(share={str(k): v for k, v in sh.items()}, diff=diff, triggered=bool(diff is not None and abs(diff) > pp))
    return out


def lee_bounds(df: pd.DataFrame, y: np.ndarray, cls: np.ndarray, pair: tuple, att: dict, refit) -> dict:
    """Lee-type trimming: the class with less attrition is trimmed by p = (a_hi - a_lo) / (1 - a_lo) of its observed
    units from the top and from the bottom of its target; the primary is re-estimated at both ends."""
    sh = att.get("share") or {}
    a0, a1 = sh.get(str(pair[0])), sh.get(str(pair[1]))
    if a0 is None or a1 is None:
        return {"computed": False}
    low = pair[0] if a0 < a1 else pair[1]
    a_lo, a_hi = min(a0, a1), max(a0, a1)
    p = (a_hi - a_lo) / (1 - a_lo) if a_lo < 1 else 0.0
    yv = np.asarray(y, float)
    m = (np.asarray(cls, object) == low) & np.isfinite(yv)
    if m.sum() < 10 or p <= 0:
        return {"computed": False, "trim_share": p}
    qlo, qhi = np.quantile(yv[m], [p, 1 - p])
    res = {"computed": True, "trimmed_class": str(low), "trim_share": p}
    for name, drop in (("trim_top", m & (yv > qhi)), ("trim_bottom", m & (yv < qlo))):
        r = refit(df[~drop].reset_index(drop=True), yv[~drop])
        res[name] = {"beta": r.get("beta"), "p": r.get("p"), "testable": bool(r.get("testable"))}
    return res


def paper_taker(bi, ai, bj, aj, rate, ex, direction) -> np.ndarray:
    """Per-share net P&L of a taker round trip (section 1.10): long outcome 0 = bid_j - ask_i, short (buy outcome 1)
    = bid_i - ask_j; taker fee rate * (p(1-p))^exponent on both legs."""
    bi, ai, bj, aj, rate, ex, d = (np.asarray(v, float) for v in (bi, ai, bj, aj, rate, ex, direction))
    p_in = np.where(d > 0, ai, 1.0 - bi)
    p_out = np.where(d > 0, bj, 1.0 - aj)

    def fee(p):
        q = np.clip(p, 0.0, 1.0)
        return rate * (q * (1.0 - q)) ** ex

    return np.where(d > 0, bj - ai, bi - aj) - fee(p_in) - fee(p_out)


def econ(pnl: np.ndarray, ev: np.ndarray, day: np.ndarray, seed: int) -> dict:
    """Paper economics (section 1.10; counted 0): event-clustered mean, one-sided p, >= 30 trades in >= 10 events."""
    pnl = np.asarray(pnl, float)
    ok = np.isfinite(pnl)
    n, ne = int(ok.sum()), int(pd.unique(np.asarray(ev)[ok]).size) if ok.any() else 0
    if n < lt.economics.MIN_TRADES or ne < lt.economics.MIN_CLUSTERS:
        return {"trades": n, "events": ne, "verdict": "not shown (below 30 trades / 10 events)"}
    r = battery.mean_test(pnl[ok], np.asarray(ev)[ok], np.asarray(day)[ok], sign=+1, n_boot=N_BOOT, seed=seed)
    covers = r["mean"] > 0 and r["p"] < 0.05
    return {**bd._clean(r), "trades": n, "events": ne, "verdict": "covers taker costs (paper)" if covers else "not shown"}


def gross(v, ev) -> dict:
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    return {"n": int(ok.sum()), "events": int(pd.unique(np.asarray(ev)[ok]).size) if ok.any() else 0,
            "mean": float(v[ok].mean()) if ok.any() else None, "note": "gross, no fills"}


def floors_ok(counts: dict, floors: dict) -> bool:
    return all(counts.get(k, 0) >= v for k, v in floors.items())


# --- E015 and E019 ----------------------------------------------------------------------------------------------------


def move_frame(root: Path, start: float, end: float, roles, spec) -> tuple[pd.DataFrame, dict]:
    df, acc = load_kind(root, "move", start, end, roles, spec, ("h1", "h3", "s0", "s1"))
    if df.empty:
        return df, acc
    sx = np.sign(df["x"].to_numpy(float))
    m1, m3 = mid_at(df, "h1"), mid_at(df, "h3")
    s0, s1 = mid_at(df, "s0"), mid_at(df, "s1")
    late = late_mask(df, "h1")
    acc["late_lines_h1"] = int(late.sum())
    df["c"] = np.where(late, np.nan, sx * (m1 - df["mid_k"].to_numpy(float)))
    df["c_sw"] = np.where(late, np.nan, sx * (s1 - s0))
    df["c_skip6"] = np.where(late_mask(df, "h3"), np.nan, sx * (m3 - m1))
    df["status_h1"] = np.where(late, "late", df["status_h1"].astype(str))
    df["day"] = day_of(df["t_row"])
    return df, acc


def e015(df: pd.DataFrame, acc: dict, spec: dict, k: int) -> dict:
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd = spec["seeds"]
    lab = spec["labels"]
    ns = df[df["sports"] == 0].copy()
    ns["P"] = ((ns["cls"] == "quote_only") & (ns["geom"] == "parallel")).astype(int)
    ns["T"] = (ns["cls"] == "traded").astype(int)
    pop = ns[(ns["P"] == 1) | (ns["T"] == 1)].reset_index(drop=True)
    res: dict = {"load": acc, "counts": {"lines": len(df), "sidecar_missing": int((df["sports"] == -1).sum()),
                                         "by_class": {f"{a}|{b}": int(v) for (a, b), v in ns.groupby(["cls", "geom"]).size().items()}}}
    res["attrition"] = attrition(pop["status_h1"].to_numpy(), pop["P"].to_numpy(), (1, 0), lab["attrition_pp"])
    y = pop["c"].to_numpy(float)
    prim = fit(pop, y, "P", CONTROLS_E015, sign=+1, seed=sd["E015"])
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    cnt = {"parallel": int((pop["P"].to_numpy()[ok] == 1).sum()) if len(ok) else 0,
           "traded": int((pop["T"].to_numpy()[ok] == 1).sum()) if len(ok) else 0,
           "events": int(pop.loc[ok, "event_id"].nunique()) if len(ok) else 0, "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["available"] = floors_ok(cnt, spec["e015"]["floors"])
    res["primary"] = strip(prim)
    g = spec["gates"]
    res["gate"] = perm_gate(pop, y, "P", CONTROLS_E015, sign=+1, group="market_id", order="t_row",
                            strata=(pop["market_id"].astype(str) + "|" + pop["day"].astype(str)).to_numpy(),
                            draws=g["draws"], seed=sd["E015_gate"], min_stratum=g["perm_min_stratum"]) if prim.get("testable") else {"testable": False, "passes": False}
    res["M1_sweep"] = strip(fit(pop, pop["c_sw"].to_numpy(float), "P", CONTROLS_E015, sign=+1, seed=sd["E015"] + 1, n_boot=200))
    res["M2_skip6"] = strip(fit(pop, pop["c_skip6"].to_numpy(float), "P", CONTROLS_E015, sign=+1, seed=sd["E015"] + 2, n_boot=200))
    m3 = ns[(ns["P"] == 1) | ((ns["T"] == 1) & (ns["geom"] == "parallel"))].reset_index(drop=True)
    res["M3_traded_parallel"] = strip(fit(m3, m3["c"].to_numpy(float), "P", CONTROLS_E015, sign=+1, seed=sd["E015"] + 3, n_boot=200))
    s1 = ns[((ns["cls"] == "quote_only") & (ns["geom"] == "one_sided")) | (ns["T"] == 1)].reset_index(drop=True)
    s1["OS"] = (s1["cls"] == "quote_only").astype(int)
    res["S1_one_sided_minus_traded"] = strip(fit(s1, s1["c"].to_numpy(float), "OS", CONTROLS_E015, sign=-1, seed=sd["E015"] + 4, n_boot=200))
    nt = ns[ns["cls"] == "never_traded"]
    res["S2_never_traded_mean_c"] = gross(nt["c"], nt["event_id"])
    res["S3_bands"] = {}
    for name, m in (("mid_lt_0.2", pop["mid_k"] < 0.2), ("mid_0.2_0.8", (pop["mid_k"] >= 0.2) & (pop["mid_k"] <= 0.8)), ("mid_gt_0.8", pop["mid_k"] > 0.8),
                    ("absx_1_2c", pop["x"].abs() < 0.02), ("absx_2_5c", (pop["x"].abs() >= 0.02) & (pop["x"].abs() < 0.05)), ("absx_ge_5c", pop["x"].abs() >= 0.05)):
        sub = pop[m.to_numpy()].reset_index(drop=True)
        r = fit(sub, sub["c"].to_numpy(float), "P", CONTROLS_E015, sign=+1, seed=sd["E015"] + 5, n_boot=200)
        res["S3_bands"][name] = {"beta": r.get("beta"), "p": r.get("p"), "n": r.get("n")}
    res["S4_full_sample_fe"] = strip(fit(pop, y, "P", CONTROLS_E015, sign=+1, estimator="fe", seed=sd["E015"] + 6, n_boot=200))
    sp = df[df["sports"] == 1].copy()
    sp["P"] = ((sp["cls"] == "quote_only") & (sp["geom"] == "parallel")).astype(int)
    sp = sp[(sp["P"] == 1) | (sp["cls"] == "traded")].reset_index(drop=True)
    res["S5_sports_arm"] = strip(fit(sp, sp["c"].to_numpy(float), "P", CONTROLS_E015, sign=+1, seed=sd["E015"] + 7, n_boot=200))
    with np.errstate(invalid="ignore"):
        jt = (pop["ask_h1"].to_numpy(float) - pop["bid_h1"].to_numpy(float)) <= spec["eligibility"]["spread_max"] + 1e-12
    res["sensitivity_j_tight"] = strip(fit(pop, np.where(jt, y, np.nan), "P", CONTROLS_E015, sign=+1, seed=sd["E015"] + 10, n_boot=200))
    if res["attrition"]["triggered"]:
        res["attrition"]["bounds"] = lee_bounds(pop, y, pop["P"].to_numpy(), (1, 0), res["attrition"],
                                                lambda d, yy: fit(d, yy, "P", CONTROLS_E015, sign=+1, seed=sd["E015"], n_boot=200))
    par = pop[(pop["P"] == 1) & (pop["x"].abs() >= 0.03)]
    res["economics"] = {"follow_parallel_ge3c": econ(paper_taker(par["bid_k"], par["ask_k"], par["bid_h1"], par["ask_h1"], par["fee_rate"], par["fee_exp"],
                                                                np.sign(par["x"])), par["event_id"].to_numpy(), par["day"].to_numpy(), sd["E015"] + 8)}
    os_ = ns[(ns["cls"] == "quote_only") & (ns["geom"] == "one_sided") & (ns["x"].abs() >= 0.03)]
    res["economics"]["fade_one_sided_ge3c_reported"] = econ(paper_taker(os_["bid_k"], os_["ask_k"], os_["bid_h1"], os_["ask_h1"], os_["fee_rate"], os_["fee_exp"],
                                                                        -np.sign(os_["x"])), os_["event_id"].to_numpy(), os_["day"].to_numpy(), sd["E015"] + 9)
    res["economics"]["maker_gross_by_class"] = {f"{a}|{b}": gross(g_["c"], g_["event_id"]) for (a, b), g_ in ns.groupby(["cls", "geom"])}
    res["late_loss_share"] = acc.get("late_loss_share", 0.0)
    return res


def e015_labels(res: dict, verdict_: dict, spec: dict, k: int) -> list:
    lab = spec["labels"]
    b = (res.get("primary") or {}).get("beta")
    out = []
    if str(verdict_.get("verdict", "")).startswith("Supported"):
        if not check_fraction(b, res.get("M1_sweep"), +1, True, lab["fraction"]):
            out.append("Gamma-quote mechanics")
        if not check_fraction(b, res.get("M3_traded_parallel"), +1, False, lab["fraction"]):
            out.append("impact/anatomy mechanics")
    return out


def e019(df_mv: pd.DataFrame, root: Path, start: float, end: float, roles, spec: dict) -> dict:
    ev, acc = load_kind(root, "events", start, end, roles, spec, ())
    if ev.empty or df_mv.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd, e = spec["seeds"], spec["e019"]
    mv = df_mv[(df_mv["cls"] == "quote_only") & (df_mv["sports"] == 0) & (df_mv["neg_risk"] == 1)].copy()
    mv["par"] = (mv["geom"] == "parallel").astype(int)
    mv["par_ss"] = mv["geom"].isin(["parallel", "same_side_unequal"]).astype(int)
    agg = mv.groupby(["capture_id", "event_id"]).agg(C=("c", "mean"), C_sw=("c_sw", "mean"), n_c=("c", "count"), n_mv=("c", "size"))
    ps = mv[mv["par"] == 1].groupby(["capture_id", "event_id"])["c"].mean().rename("C_par")  # binding: parallel only (freeze ruling 1)
    pss = mv[mv["par_ss"] == 1].groupby(["capture_id", "event_id"])["c"].mean().rename("C_par_ss")  # reported only
    ev = (ev.merge(agg.reset_index(), on=["capture_id", "event_id"], how="left").merge(ps.reset_index(), on=["capture_id", "event_id"], how="left")
          .merge(pss.reset_index(), on=["capture_id", "event_id"], how="left"))
    ev["day"] = day_of(ev["t_row"])
    un = ev[(ev["untraded"] == 1) & (ev["n_qo_mov"] > 0)].copy()
    un["high"] = np.where(un["b"] >= e["high_b"] - 1e-12, 1, np.where(un["b"] < e["low_b"], 0, -1))
    res: dict = {"load": acc, "counts": {"event_intervals": len(ev), "untraded_with_mover": len(un),
                                         "high": int((un["high"] == 1).sum()), "middle": int((un["high"] == -1).sum()), "low": int((un["high"] == 0).sum()),
                                         "traded_intervals": int((ev["untraded"] == 0).sum())}}
    pop = un[un["high"] >= 0]
    excl = bool(e.get("exclude_crypto"))
    if excl:
        fam = e.get("exclude_family")
        pop_x = pop[(pop["crypto"] != 1) & (pop["skey"].astype(str) != str(fam))]
    else:
        pop_x = pop
    pop_x = pop_x.reset_index(drop=True)
    res["population"] = "ex-crypto" + (f" and ex-{e.get('exclude_family')}" if e.get("exclude_family") else "") if excl else "all non-sports neg-risk"
    y = pop_x["C"].to_numpy(float)
    prim = fit(pop_x, y, "high", CONTROLS_E019, sign=+1, group="event_id", ev="skey", ev_t_ref=True, seed=sd["E019"])
    ok = prim.get("_mask", np.zeros(len(pop_x), bool))
    h = pop_x[ok & (pop_x["high"].to_numpy() == 1)] if len(ok) else pop_x.iloc[:0]
    lo = pop_x[ok & (pop_x["high"].to_numpy() == 0)] if len(ok) else pop_x.iloc[:0]
    cnt = {"events_both": len(set(h["event_id"]) & set(lo["event_id"])), "clusters_high": int(h["skey"].nunique()), "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    fam_share = h["skey"].value_counts(normalize=True)
    res["counts"]["top_family_share_high"] = float(fam_share.iloc[0]) if len(fam_share) else None
    res["available"] = floors_ok(cnt, e["floors"])
    res["primary"] = strip(prim)
    g = spec["gates"]
    res["gate"] = perm_gate(pop_x, y, "high", CONTROLS_E019, sign=+1, group="event_id", order="t_row",
                            strata=(pop_x["event_id"].astype(str) + "|" + pop_x["day"].astype(str)).to_numpy(),
                            draws=g["draws"], seed=sd["E019_gate"], min_stratum=g["perm_min_stratum"]) if prim.get("testable") else {"testable": False, "passes": False}
    res["attrition"] = attrition(np.where(pop_x["n_c"].fillna(0).to_numpy() > 0, "two_sided", "lost"), pop_x["high"].to_numpy(), (1, 0),
                                 spec["labels"]["attrition_pp"])
    res["anatomy_par"] = strip(fit(pop_x, pop_x["C_par"].to_numpy(float), "high", CONTROLS_E019, sign=+1, group="event_id", ev="skey", ev_t_ref=True, seed=sd["E019"] + 1, n_boot=200))
    res["anatomy_par_ss_reported"] = strip(fit(pop_x, pop_x["C_par_ss"].to_numpy(float), "high", CONTROLS_E019, sign=+1, group="event_id", ev="skey", ev_t_ref=True, seed=sd["E019"] + 9, n_boot=200))
    res["M1_sweep"] = strip(fit(pop_x, pop_x["C_sw"].to_numpy(float), "high", CONTROLS_E019, sign=+1, group="event_id", ev="skey", ev_t_ref=True, seed=sd["E019"] + 2, n_boot=200))
    cr = pop[pop["crypto"] == 1].reset_index(drop=True)
    res["M2_crypto"] = strip(fit(cr, cr["C"].to_numpy(float), "high", CONTROLS_E019, sign=+1, group="event_id", ev="skey", ev_t_ref=True, seed=sd["E019"] + 3, n_boot=200))
    res["middle_mean_C"] = gross(un.loc[un["high"] == -1, "C"], un.loc[un["high"] == -1, "event_id"])
    res["traded_intervals_mean_C"] = gross(ev.loc[ev["untraded"] == 0, "C"], ev.loc[ev["untraded"] == 0, "event_id"])
    hm = mv.merge(pop_x[pop_x["high"] == 1][["capture_id", "event_id"]], on=["capture_id", "event_id"])
    hm = hm[hm["x"].abs() >= 0.02]
    lm = mv.merge(pop_x[(pop_x["high"] == 0) & (pop_x["n_qo_mov"] == 1)][["capture_id", "event_id"]], on=["capture_id", "event_id"])
    lm = lm[lm["x"].abs() >= 0.03]
    res["economics"] = {"follow_high_ge2c": econ(paper_taker(hm["bid_k"], hm["ask_k"], hm["bid_h1"], hm["ask_h1"], hm["fee_rate"], hm["fee_exp"], np.sign(hm["x"])),
                                                 hm["event_id"].to_numpy(), hm["day"].to_numpy(), sd["E019"] + 4),
                        "fade_low_lone_ge3c": econ(paper_taker(lm["bid_k"], lm["ask_k"], lm["bid_h1"], lm["ask_h1"], lm["fee_rate"], lm["fee_exp"], -np.sign(lm["x"])),
                                                   lm["event_id"].to_numpy(), lm["day"].to_numpy(), sd["E019"] + 5),
                        "maker_gross_high_low": {"high": gross(pop_x.loc[pop_x["high"] == 1, "C"], pop_x.loc[pop_x["high"] == 1, "event_id"]),
                                                 "low": gross(pop_x.loc[pop_x["high"] == 0, "C"], pop_x.loc[pop_x["high"] == 0, "event_id"])}}
    res["late_loss_share"] = max(acc.get("late_loss_share", 0.0), 0.0)
    return res


def e019_labels(res: dict, verdict_: dict, spec: dict) -> list:
    lab = spec["labels"]
    b = (res.get("primary") or {}).get("beta")
    out = []
    if str(verdict_.get("verdict", "")).startswith("Supported"):
        if not check_fraction(b, res.get("anatomy_par"), +1, True, lab["fraction"]):
            out.append("quote-anatomy composition")
        if not check_fraction(b, res.get("M1_sweep"), +1, True, lab["fraction"]):
            out.append("Gamma-quote mechanics")
    ts = (res.get("counts") or {}).get("top_family_share_high")
    if ts is not None and ts > lab["series_concentration"]:
        out.append(f"series-concentrated (top family {ts:.0%} of high units)")
    return out


# --- E017 ------------------------------------------------------------------------------------------------------------


def e017(root: Path, start: float, end: float, roles, spec: dict) -> dict:
    df, acc = load_kind(root, "surge", start, end, roles, spec, ("h3", "h12"))
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd = spec["seeds"]
    late = late_mask(df, "h12")
    acc["late_lines_h12"] = int(late.sum())
    df["y24"] = np.where(late, np.nan, mid_at(df, "h12") - df["mid_k"].to_numpy(float))
    df["y6"] = np.where(late_mask(df, "h3"), np.nan, mid_at(df, "h3") - df["mid_k"].to_numpy(float))
    df["status_h12"] = np.where(late, "late", df["status_h12"].astype(str))
    df["block"] = block_of(df["t_row"], start)
    df["day"] = day_of(df["t_row"])
    base = df[df["lag_unknown"] == 0]
    pop = base[(base["neg_risk"] == 1) & (base["sports"] == 0)].reset_index(drop=True)
    res: dict = {"load": acc, "counts": {"lines": len(df), "lag_unknown": int((df["lag_unknown"] == 1).sum()), "primary_units": len(pop),
                                         "A": int(pop["A"].sum()), "SM": int(pop["SM"].sum()), "sidecar_missing": int((df["sports"] == -1).sum())}}
    y = pop["y24"].to_numpy(float)
    kw = {"sign": +1, "estimator": "fe", "time": "block"}
    prim = fit(pop, y, "A", CONTROLS_E017, seed=sd["E017"], **kw)
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    a_ok = ok & (pop["A"].to_numpy() == 1) if len(ok) else np.zeros(0, bool)
    cnt = {"A_units": int(a_ok.sum()), "events": int(pop.loc[a_ok, "event_id"].nunique()) if len(ok) else 0, "blocks": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["available"] = floors_ok(cnt, spec["e017"]["floors"])
    res["primary"] = strip(prim)
    res["pretrend"] = strip(fit(pop, pop["pre24"].to_numpy(float), "A", CONTROLS_E017, seed=sd["E017"] + 1, n_boot=200, **kw))
    ctrl_sm = ["A" if c == "SM" else c for c in CONTROLS_E017]
    res["SM_coefficient"] = strip(fit(pop, y, "SM", ctrl_sm, seed=sd["E017"] + 2, n_boot=200, **kw))
    grp = np.where(pop["A"] == 1, "A", np.where(pop["S"] == 0, "baseline", "SM"))
    res["attrition"] = attrition(pop["status_h12"].to_numpy(), grp, ("A", "baseline"), spec["labels"]["attrition_pp"])
    res["attrition"]["bounds"] = lee_bounds(pop, y, grp, ("A", "baseline"), res["attrition"],
                                            lambda d, yy: fit(d, yy, "A", CONTROLS_E017, seed=sd["E017"], n_boot=200, **kw))  # always reported for 24 h (ruling 9)
    st = base[(base["neg_risk"] == 0) & (base["sports"] == 0)].reset_index(drop=True)
    res["S2_standalone"] = strip(fit(st, st["y24"].to_numpy(float), "A", CONTROLS_E017, seed=sd["E017"] + 3, n_boot=200, **kw))
    res["S3_dose"] = {}
    for r_ in (5.0, 10.0):
        d = pop.copy()
        d["A"] = ((d["A"] == 1) & (d["vol_ratio"] >= r_)).astype(int)
        r = fit(d, y, "A", CONTROLS_E017, seed=sd["E017"] + 4, n_boot=200, **kw)
        res["S3_dose"][f"ratio_ge_{r_:g}"] = {"beta": r.get("beta"), "p": r.get("p"), "n": r.get("n")}
    res["S4_6h"] = strip(fit(pop, pop["y6"].to_numpy(float), "A", CONTROLS_E017, seed=sd["E017"] + 5, n_boot=200, **kw))
    res["S5_expanding"] = strip(fit(pop, y, "A", CONTROLS_E017, sign=+1, estimator="expanding", time="block", seed=sd["E017"] + 6, n_boot=200))
    sp = base[base["sports"] == 1].reset_index(drop=True)
    res["S6_sports_arm"] = strip(fit(sp, sp["y24"].to_numpy(float), "A", CONTROLS_E017, seed=sd["E017"] + 7, n_boot=200, **kw))
    a = pop[pop["A"] == 1]
    res["economics"] = {"buy_yes_on_A": econ(paper_taker(a["bid_k"], a["ask_k"], a["bid_h12"], a["ask_h12"], a["fee_rate"], a["fee_exp"], np.ones(len(a))),
                                             a["event_id"].to_numpy(), a["day"].to_numpy(), sd["E017"] + 8)}
    res["late_loss_share"] = acc.get("late_loss_share", 0.0)
    return res


def e017_labels(res: dict, verdict_: dict, spec: dict) -> list:
    out = []
    b = (res.get("primary") or {}).get("beta")
    pt = res.get("pretrend") or {}
    if pt.get("testable") and b is not None and (pt.get("p") or 1.0) < 0.05 and pt.get("beta", 0) >= spec["labels"]["fraction"] * b:
        out.append("pre-existing trend")
    sm = res.get("SM_coefficient") or {}
    if str(verdict_.get("verdict", "")).startswith("Supported") and sm.get("testable") and sm.get("beta", 0) > 0:
        lo, hi = sm.get("ci95_cons") or [None, None]
        if lo is not None and lo <= b <= hi:
            out.append("volume, not attention-without-news")
    return out


# --- E016 and E018 ----------------------------------------------------------------------------------------------------


def flow_frame(root: Path, start: float, end: float, roles, spec: dict) -> tuple[pd.DataFrame, dict]:
    df, acc = load_kind(root, "flow", start, end, roles, spec, ("h3", "s0", "s3"))
    if df.empty:
        return df, acc
    late = late_mask(df, "h3")
    acc["late_lines_h3"] = int(late.sum())
    df["y6"] = np.where(late, np.nan, mid_at(df, "h3") - df["mid_i"].to_numpy(float))
    df["y6_sw"] = np.where(late, np.nan, mid_at(df, "s3") - mid_at(df, "s0"))
    df["status_h3"] = np.where(late, "late", df["status_h3"].astype(str))
    df["day"] = day_of(df["t_row"])
    df["block"] = block_of(df["t_row"], start)
    df["rv_missing"] = (~np.isfinite(df["zRV"].to_numpy(float))).astype(int)
    df["zRV"] = np.nan_to_num(df["zRV"].to_numpy(float))
    return df, acc


def flow_controls(mod: str, lag: bool = False) -> tuple[str, str, list[str]]:
    sfx = "_l30" if lag else ""
    x = f"x6{sfx}"
    return x, f"{mod}{sfx}", [f"{x}*zN{sfx}", f"zN{sfx}", f"{x}*zSPR", "zSPR", f"{x}*zSize{sfx}", f"zSize{sfx}", f"{x}*zHTE", "zHTE",
                              f"{x}*zRV", "zRV", x, *FLOW_BASE]


def add_products(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if "*" in c and c not in df:
            a, b = c.split("*")
            df[c] = df[a].to_numpy(float) * df[b].to_numpy(float)
    return df


def flow_test(df: pd.DataFrame, acc: dict, spec: dict, name: str, mod: str) -> dict:
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd, f, g = spec["seeds"], spec["flow"], spec["gates"]
    sign = DIRECTION[name]
    cap = f.get("vol24_cap")
    cap = float("inf") if cap is None else float(cap)
    base = df[(df["tight_i"] == 1) & (df["end_ok_7h"] == 1)]
    vpop = base[np.isfinite(base["vol24_i"].to_numpy(float)) & (base["vol24_i"].to_numpy(float) <= cap)]
    trunc = (vpop["cov6"] == 0)
    res: dict = {"load": acc, "counts": {"lines": len(df), "V*_population": len(vpop), "truncated": int(trunc.sum()),
                                         "truncated_share": float(trunc.mean()) if len(vpop) else None}}
    pop = vpop[(vpop["cov6"] == 1) & (np.nan_to_num(vpop["N6"].to_numpy(float)) > 0) & np.isfinite(vpop[f"z{mod}"].to_numpy(float))].copy()
    res["counts"]["moderator_missing"] = int(((vpop["cov6"] == 1) & (np.nan_to_num(vpop["N6"].to_numpy(float)) > 0)).sum() - len(pop))
    x, m, ctrl = flow_controls(f"z{mod}")
    term = f"{x}*{m}"
    pop = add_products(pop, [term, *ctrl]).reset_index(drop=True)
    y = pop["y6"].to_numpy(float)
    prim = fit(pop, y, term, [m, *ctrl], sign=sign, seed=sd[name])
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    cnt = {"units": int(ok.sum()), "events": int(pop.loc[ok, "event_id"].nunique()) if len(ok) else 0, "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["counts"]["by_category"] = {str(k): int(v) for k, v in pop.loc[ok, "sports"].value_counts().items()} if len(ok) else {}
    res["available"] = floors_ok(cnt, spec[name.lower()]["floors"])
    res["primary"] = strip(prim)
    res["gate"] = donor_gate(pop, y, x, m, ctrl, sign=sign, draws=g["draws"], seed=sd[f"{name}_gate"] if f"{name}_gate" in sd else sd[name] + 100,
                             min_units=g["donor_min_units"], min_sep_s=g["donor_min_sep_s"], min_donors=g["donor_min_donors"]) if prim.get("testable") else {"testable": False, "passes": False}
    xl, ml, cl = flow_controls(f"z{mod}", lag=True)
    pl = add_products(pop.copy(), [f"{xl}*{ml}", *cl])
    res["M1_lag30"] = strip(fit(pl, y, f"{xl}*{ml}", [ml, *cl], sign=sign, seed=sd[name] + 1, n_boot=200))
    res["M2_sweep"] = strip(fit(pop, pop["y6_sw"].to_numpy(float), term, [m, *ctrl], sign=sign, seed=sd[name] + 2, n_boot=200))
    res["sensitivity_two_day_blocks"] = strip(fit(pop, y, term, [m, *ctrl], sign=sign, time="block", seed=sd[name] + 3, n_boot=200))
    res["S_fe"] = strip(fit(pop, y, term, [m, *ctrl], sign=sign, estimator="fe", seed=sd[name] + 4, n_boot=200))
    if mod == "W":
        pr = pop.copy()
        pr["zWr"] = (pr["Wr"] - f["zW"]["centre"]) / f["zW"]["scale"] if f["zW"].get("scale") else np.nan
        pr = add_products(pr, ["x6*zWr"])
        res["S_W_row_counts"] = strip(fit(pr, y, "x6*zWr", ["zWr", *ctrl], sign=sign, seed=sd[name] + 5, n_boot=200))
    else:
        pr = pop.copy()
        pr["zHu"] = (pr["Hu"] - f["zH"]["centre"]) / f["zH"]["scale"] if f["zH"].get("scale") else np.nan
        pr = add_products(pr, ["x6*zHu"])
        res["M3_unsigned_trains"] = strip(fit(pr, y, "x6*zHu", ["zHu", *ctrl], sign=sign, seed=sd[name] + 5, n_boot=200))
    res["by_category"] = {}
    for cat in (0, 1):
        sub = pop[pop["sports"] == cat].reset_index(drop=True)
        r = fit(sub, sub["y6"].to_numpy(float), term, [m, *ctrl], sign=sign, seed=sd[name] + 6, n_boot=200)
        res["by_category"]["sports" if cat else "non_sports"] = {"beta": r.get("beta"), "p": r.get("p"), "n": r.get("n")}
    if res["counts"]["truncated_share"] is not None and res["counts"]["truncated_share"] > f["trunc_label_share"]:
        half = pop[pop["vol24_i"] <= cap / 2.0].reset_index(drop=True)
        res["sensitivity_half_cap"] = strip(fit(half, half["y6"].to_numpy(float), term, [m, *ctrl], sign=sign, seed=sd[name] + 7, n_boot=200))
    med = np.nanmedian(pop[m].to_numpy(float)) if len(pop) else np.nan
    half_cls = np.where(pop[m].to_numpy(float) >= med, "upper", "lower")
    res["attrition"] = attrition(pop["status_h3"].to_numpy(), half_cls, ("upper", "lower"), spec["labels"]["attrition_pp"])
    if res["attrition"]["triggered"]:
        res["attrition"]["bounds"] = lee_bounds(pop, y, half_cls, ("upper", "lower"), res["attrition"],
                                                lambda d, yy: fit(d, yy, term, [m, *ctrl], sign=sign, seed=sd[name], n_boot=200))
    ec = f["econ"]
    cut = ec["W_upper_cut"] if mod == "W" else ec["H_lower_cut"]
    if cut is not None:
        cell = pop[((pop[mod] >= cut) if mod == "W" else (pop[mod] <= cut)) & (pop["imb6"].abs() >= ec["min_abs_imb"])]
        d = np.sign(cell["imb6"].to_numpy(float))
        gm = d * (mid_at(cell, "h3") - cell["mid_i"].to_numpy(float))
        res["economics"] = {"follow_cell": econ(paper_taker(cell["bid_i"], cell["ask_i"], cell["bid_h3"], cell["ask_h3"], cell["fee_rate"], cell["fee_exp"], d),
                                                cell["event_id"].to_numpy(), cell["day"].to_numpy(), sd[name] + 8),
                            "gross_cell": gross(gm, cell["event_id"])}
    else:
        res["economics"] = {"verdict": "not computed (census cut not filled)"}
    res["late_loss_share"] = acc.get("late_loss_share", 0.0)
    return res


def flow_labels(res: dict, verdict_: dict, spec: dict, name: str) -> list:
    out = []
    b = (res.get("primary") or {}).get("beta")
    if str(verdict_.get("verdict", "")).startswith("Supported") and not check_fraction(b, res.get("M1_lag30"), DIRECTION[name], True, spec["labels"]["fraction"]):
        out.append("possibly mechanical (stale-mid catch-up)")
    ts = (res.get("counts") or {}).get("truncated_share")
    if ts is not None and ts > spec["flow"]["trunc_label_share"]:
        out.append("coverage-limited")
    return out


# --- the single analysis -----------------------------------------------------------------------------------------------


TRIAL_KIND = "live_tests3"


def trial_record(res: dict) -> dict:
    """The single counted trials line (battery2 KIND_RULES 'live_tests3', rule n_tests = k): one per Holm primary.
    Placebo / gate draws, secondaries, mechanism readings, economics and the censuses are not counted (section 1.11)."""
    ks = (res.get("holm") or {}).get("tests") or []
    return {"kind": TRIAL_KIND, "label": "PROSPECTIVE", "evidence_role": lt.ROLE_CONF, "experiments": list(ks),
            "n_tests": len(ks), "n_primary": len(ks), "holm": res.get("holm"),
            "verdicts": {k: (res.get(k) or {}).get("verdict") for k in ks},
            "spec_sha256": res.get("spec_sha"), "code_sha256": res.get("code_sha256"), "window": res.get("window")}


def analyze(root: Path = lt.OUT_ROOT, *, start_utc: str = lt.REGISTERED_UTC, end_utc: str = lt.END_UTC, spec: dict | None = None,
            roles: tuple[str, ...] = (lt.ROLE_CONF,), force: bool = False) -> dict:
    """The single registered analysis. Refuses before ANALYSIS_NOT_BEFORE unless ``force`` (tests only) and refuses a
    pinned spec whose code hashes or census values are not filled / do not match."""
    if not force and lt.now_ts() < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise RuntimeError(f"analysis refused before {lt.ANALYSIS_NOT_BEFORE}")
    spec = spec or lt.load_spec()
    cc = code_check(spec)
    s, e = lt.epoch(start_utc), lt.epoch(end_utc)
    ktests = list(spec.get("k_tests") or TESTS)
    k = len(ktests)
    mv, macc = move_frame(root, s, e, roles, spec)
    fl, facc = flow_frame(root, s, e, roles, spec)
    res = {"E015": e015(mv, macc, spec, k), "E019": e019(mv, root, s, e, roles, spec), "E017": e017(root, s, e, roles, spec),
           "E016": flow_test(fl, facc, spec, "E016", "W"), "E018": flow_test(fl, facc, spec, "E018", "H")}
    gate_label = {"E015": "SE check failed", "E019": "SE check failed", "E016": "within-unit timing not shown",
                  "E018": "within-unit timing not shown", "E017": "placebo"}
    pv = {}
    for t in ktests:
        r = res[t]
        g = None if t == "E017" else r.get("gate")
        pv[t] = verdict(r.get("primary") or {}, g, r.get("available", False), None, DIRECTION[t], gate_label[t])["p_for_holm"]
    hp = bd.holm(pv)
    floors = {"E015": spec["e015"]["floor_c"], "E019": spec["e019"]["floor_c"], "E017": spec["e017"]["floor_c"]}
    for t in TESTS:
        r = res[t]
        if t not in ktests:
            r["verdict"] = {"verdict": "dropped before registration (census gate); not in the Holm family"}
            continue
        g = None if t == "E017" else r.get("gate")
        v = verdict(r.get("primary") or {}, g, r.get("available", False), hp[t], DIRECTION[t], gate_label[t])
        r["holm_p"] = hp[t]
        labels: list = []
        if t == "E015":
            labels += e015_labels(r, v, spec, k)
        elif t == "E019":
            labels += e019_labels(r, v, spec)
        elif t == "E017":
            labels += e017_labels(r, v, spec)
        else:
            labels += flow_labels(r, v, spec, t)
        prim = r.get("primary") or {}
        if t in floors and prim.get("beta") is not None and DIRECTION[t] * prim["beta"] >= floors[t]:
            labels.append("material")
        if t in ("E016", "E018"):
            gm = ((r.get("economics") or {}).get("gross_cell") or {}).get("mean")
            if gm is not None and gm >= spec[t.lower()]["floor_gross_c"]:
                labels.append("material")
        ref = floors.get(t) if t in floors else spec[t.lower()]["underpowered_ref"]
        if str(v.get("verdict", "")) == "Inconclusive" and underpowered(prim, k, ref):
            labels.append("underpowered")
        att = r.get("attrition") or {}
        if att.get("triggered"):
            labels.append(f"attrition-differential ({att['diff'] * 100:+.1f} pp)")
        if (r.get("late_loss_share") or 0.0) > spec["labels"]["late_loss_share"]:
            labels.append(f"late-loss ({r['late_loss_share']:.1%} of origin files refused late)")
        labels.append(cc["label"])
        r["verdict"] = attach(v, labels)
    res["holm"] = {"tests": ktests, "m": k, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True}
    res["spec_sha"] = spec["_sha256"]
    res["code_sha256"] = cc["current"]
    res["code_check"] = cc
    res["window"] = [start_utc, end_utc]
    res["roles"] = list(roles)
    return bd._clean(res)


# --- simulated-null size of the two gates (section 1.8; run on the code to be pinned, section 13) ------------------------


def sim_flow_world(rng: np.random.Generator, *, n_mkt: int = 40, n_t: int = 30, ar: float = 0.0, lifecycle: bool = False,
                   effect: float = 0.0) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """A flow panel with NO moderation (``effect`` = 0): persistent market level of the moderator, iid or AR(1) flow,
    optionally a life-cycle world (moderator and flow continuation both rise towards the end; the x6 * zHTE control is
    then included, as in the registered model)."""
    rows = []
    for m in range(n_mkt):
        x, lvl = 0.0, rng.normal(0, 0.5)
        for i in range(n_t):
            x = ar * x + rng.normal(0, 1)
            tau = i / max(n_t - 1, 1)
            z = lvl + (1.5 * tau if lifecycle else 0.0) + rng.normal(0, 1)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 2}", "t_row": i * 7200.0, "day": str(i // 12), "x6": x,
                         "zM": z, "zHTE": (tau - 0.5) * 2.0, "c1": rng.normal()})
    df = pd.DataFrame(rows)
    slope = 0.003 * (1.0 + (2.0 * df["zHTE"].to_numpy() if lifecycle else 0.0))
    y = slope * df["x6"].to_numpy() + effect * df["x6"].to_numpy() * df["zM"].to_numpy() + rng.normal(0, 0.01, len(df))
    df["x6*zHTE"] = df["x6"] * df["zHTE"]
    others = ["x6", "c1"] + (["x6*zHTE", "zHTE"] if lifecycle else [])
    return df, y, others


def sim_move_world(rng: np.random.Generator, *, n_mkt: int = 60, n_t: int = 40, persistent: bool = False,
                   effect: float = 0.0) -> tuple[pd.DataFrame, np.ndarray]:
    """A class-contrast panel with NO class effect (``effect`` = 0): market-specific class rates and target levels when
    ``persistent`` (the case expanding-past demeaning must absorb)."""
    rows = []
    for m in range(n_mkt):
        pr = rng.uniform(0.1, 0.6) if persistent else 0.3
        lvl = rng.normal(0, 0.01) if persistent else 0.0
        for i in range(n_t):
            P = int(rng.random() < pr)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "P": P,
                         "c1": rng.normal(), "y": lvl + effect * P + rng.normal(0, 0.04)})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def size_check(*, worlds: int, draws: int, seed: int, nominal: float = 0.05) -> dict:
    """Pass rate of the distant-donor gate (iid, AR(1), life-cycle) and of the label-permutation gate (iid, persistent)
    under simulated nulls, with the declared criterion rate <= nominal + 1.645 * sqrt(nominal (1 - nominal) / worlds)."""
    rng = np.random.default_rng(seed)
    lim = nominal + 1.645 * float(np.sqrt(nominal * (1 - nominal) / worlds))
    out: dict = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": {}}
    for name, kw in (("donor_iid", {}), ("donor_ar0.6", {"ar": 0.6}), ("donor_lifecycle", {"lifecycle": True})):
        rej = 0
        for _ in range(worlds):
            df, y, others = sim_flow_world(rng, **kw)
            g = donor_gate(df, y, "x6", "zM", others, sign=+1, draws=draws, seed=int(rng.integers(1 << 31)), min_units=4,
                           min_sep_s=43200.0, min_donors=2)
            rej += int(bool(g.get("passes")))
        out["scenarios"][name] = {"rate": rej / worlds, "ok": rej / worlds <= lim}
    for name, kw in (("perm_iid", {}), ("perm_persistent", {"persistent": True})):
        rej = 0
        for _ in range(worlds):
            df, y = sim_move_world(rng, **kw)
            strata = (df["market_id"] + "|" + df["day"]).to_numpy()
            g = perm_gate(df, y, "P", ["c1"], sign=+1, group="market_id", order="t_row", strata=strata, draws=draws,
                          seed=int(rng.integers(1 << 31)), min_stratum=4)
            rej += int(bool(g.get("passes")))
        out["scenarios"][name] = {"rate": rej / worlds, "ok": rej / worlds <= lim}
    out["pass"] = all(v["ok"] for v in out["scenarios"].values())
    out["code_sha256"] = lt.code_hashes()
    return out
