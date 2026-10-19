# ruff: noqa: E501
"""Single registered analysis of the live tests E012-E014 (docs/research_lab/LIVE_TESTS_2.md). DRAFT until registered.

Runs ONCE, after ``live_tests2.ANALYSIS_NOT_BEFORE``, on the write-once files of ``live_tests2``. Four primaries in one
Holm family (one-sided, familywise alpha 0.05): E012 (1-day change x liquidity), E013-F4 (6 h flow x volatility),
E013-F5 (6 h flow x spread), E014 (near-end gain of the frozen E007 flow model). A primary that is unavailable, void or
placebo-biased enters Holm with p = 1. Economics are separate and never change a primary verdict.

Estimators (J4-R lessons, SCREENING_BATCH_2.md): E012 and E013 use the expanding-past demeaned OLS (every regressor
minus the market's mean over its strictly earlier rows; target raw), event-clustered and two-way event x UTC-day SEs
(``battery.beta_test``; one-sided p = the larger of the two), with a placebo matched to the estimator and the J4-R
reading rule (``bounce_decomp.placebo_reading``). E014 is a difference of mean per-row squared-error gains between two
as-of time-to-end regimes (the slope of the gain on the regime-A indicator, same SEs), with a within-market flow-shift
placebo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import battery, economics
from . import bounce_decomp as bd
from . import live_tests2 as lt

SEEDS = {"E012": 20261022, "E013_F4": 20261023, "E013_F5": 20261024, "E014": 20261025}
N_BOOT = 2000
PLACEBO_DRAWS = 20  # E012: J4-R increment-bootstrap placebo (regenerates x and y), J4-R reading rule
PERM_DRAWS = {"E013": 200, "E014": 1000}  # E013/E014: within-market flow-shift permutation gate
PERM_ALPHA = 0.05
FLOORS = {"E012": {"rows": 20000, "events": 200, "days": 10},
          "E013": {"rows": 10000, "events": 500, "days": 10},
          "E014": {"rows_regime": 1000, "events_regime": 100, "days": 10}}
CONTROLS_E012 = ["logit_mid", "abs_dev", "chg_1h", "chg_1h_missing", "chg_1w", "chg_1w_missing", "dprev0",
                 "dprev_missing"]
CONTROLS_FLOW = ["logit_mid", "abs_dev", "chg_1h", "chg_1h_missing", "chg_1d_g", "chg_1d_missing", "chg_1w",
                 "chg_1w_missing", "dprev0", "dprev_missing"]


# --- loading ------------------------------------------------------------------------------------------------------


def _load_pairs(root: Path, kind: str, start: float, end: float, roles: tuple[str, ...],
                spec_sha: str | None = None) -> pd.DataFrame:
    """Frozen lines of origins in [start, end) with an allowed role (and, when given, written under the registered
    spec: ``spec_sha`` = its first 16 hex digits; other lines are dropped), merged with their outcome file."""
    fdir, odir = Path(root) / kind / "frozen", Path(root) / kind / "outcomes"
    parts = []
    for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
        if p.name.endswith(".late.csv.gz"):
            continue
        fr = pd.read_csv(p, dtype={"market_id": str, "event_id": str})
        if not len(fr) or not (start <= float(fr["capture_t"].iloc[0]) < end):
            continue
        fr = fr[fr["role"].isin(roles)]
        if spec_sha is not None:
            fr = fr[fr["spec_sha"].astype(str) == spec_sha]
        op = odir / p.name
        if op.exists():
            out = pd.read_csv(op, dtype={"market_id": str})
            fr = fr.merge(out, on="market_id", how="left")
        else:
            fr["pending"] = 1
        fr["file"] = p.name
        parts.append(fr)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _day(t: pd.Series) -> np.ndarray:
    return pd.to_datetime(t, unit="s", utc=True).dt.strftime("%Y-%m-%d").to_numpy()


def _late(df: pd.DataFrame, tag: str) -> np.ndarray:
    fz = lt.panel._epoch(df["frozen_utc"])
    cs = df[f"cap_start_{tag}"].to_numpy(float) if f"cap_start_{tag}" in df else np.full(len(df), np.nan)
    with np.errstate(invalid="ignore"):
        return np.isfinite(cs) & ~(fz < cs)


def _mid(df: pd.DataFrame, tag: str) -> np.ndarray:
    return (df[f"bid_{tag}"].to_numpy(float) + df[f"ask_{tag}"].to_numpy(float)) / 2.0


# --- estimator, placebo, tests --------------------------------------------------------------------------------------


def demeaned_fit(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], order: str, *,
                 estimator: str = "expanding", seed: int, n_boot: int = N_BOOT, w=None) -> dict:
    """Slope of ``term`` given ``controls`` (one-sided, + sign). ``expanding``: J4-R demeaning of every regressor;
    ``pooled``: raw; ``fe``: full-sample market demeaning (descriptive within-market slope only)."""
    cols = [term, *controls]
    X = df[cols].astype(float)
    if estimator == "expanding":
        X = bd.expanding_demean(pd.concat([X, df[["market_id", order]]], axis=1), cols, "market_id", order)[cols]
    elif estimator == "fe":
        X = X - X.groupby(df["market_id"].to_numpy()).transform("mean")
    ok = np.isfinite(y) & np.all(np.isfinite(X.to_numpy()), axis=1)
    if w is not None:
        ok &= np.isfinite(w)
    if ok.sum() < 10:
        return {"testable": False, "reason": "fewer than 10 rows", "n": int(ok.sum()), "p": 1.0}
    Xo = X.to_numpy()[ok]
    r = battery.beta_test(y[ok], Xo[:, 0], Xo[:, 1:], df["event_id"].to_numpy()[ok], df["day"].to_numpy()[ok],
                          sign=+1, n_boot=n_boot, seed=seed, w=None if w is None else np.asarray(w)[ok])
    if not r.get("testable"):
        return {"testable": False, "reason": r.get("reason"), "n": int(ok.sum()), "p": 1.0}
    r["se"] = max(r["se_event"], r["se_twoway"])
    r["mde_80"] = 2.8 * r["se"]
    r["n_market"] = int(pd.unique(df["market_id"].to_numpy()[ok]).size)
    r["estimator"] = estimator
    r["_mask"] = ok
    return r


def _strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.startswith("_")}


def cyclic_shift_within(codes: np.ndarray, order: np.ndarray, values: np.ndarray, seed: int) -> np.ndarray:
    """Each market's values (rows in time order) rotated by a random non-zero offset; markets with one row get NaN
    (no row keeps its own value, so the placebo carries no real timing)."""
    rng = np.random.default_rng(seed)
    out = np.full(len(values), np.nan)
    o = np.lexsort((order, codes))
    cs = codes[o]
    starts = np.flatnonzero(np.r_[True, cs[1:] != cs[:-1]])
    ends = np.r_[starts[1:], len(cs)]
    vs = np.asarray(values, float)[o]
    for a, b in zip(starts, ends, strict=True):
        n = b - a
        if n < 2:
            continue
        s = int(rng.integers(1, n))
        out[o[a:b]] = np.roll(vs[a:b], s)
    return out


def rebuild_series(codes: np.ndarray, slots: np.ndarray, mids: np.ndarray, seed: int) -> np.ndarray:
    """J4-R placebo series: per market, consecutive-slot increments drawn WITH replacement from the market's pooled
    valid increments; each contiguous run of observed slots is rebuilt from its first observed level."""
    rng = np.random.default_rng(seed)
    o = np.lexsort((slots, codes))
    c, s, m = codes[o], slots[o], np.asarray(mids, float)[o]
    newm = np.r_[True, c[1:] != c[:-1]]
    begin = newm | np.r_[True, s[1:] != s[:-1] + 1]
    inc = np.where(begin, np.nan, np.r_[np.nan, np.diff(m)])
    out = m.copy()
    starts = np.flatnonzero(newm)
    ends = np.r_[starts[1:], len(c)]
    for a, b in zip(starts, ends, strict=True):
        pool = inc[a:b][np.isfinite(inc[a:b])]
        if not len(pool):
            continue
        draws = pool[rng.integers(0, len(pool), b - a)]
        seg = np.where(begin[a:b], 0.0, draws)
        run = np.cumsum(begin[a:b]) - 1
        cum = np.cumsum(seg)
        run_start = np.flatnonzero(begin[a:b])
        base = cum[run_start][run] - seg[run_start][run]
        out[a:b] = m[a:b][run_start][run] + (cum - base) - seg[run_start][run]
    res = np.empty(len(out))
    res[o] = out
    return res


def _read_rule(real: dict, betas: list[float], ses: list[float], ns: list[int], name: str) -> dict:
    draws = [{"tests": {name: {"testable": True, "beta": b, "se": s, "n": n, "mde_80": 2.8 * s}}}
             for b, s, n in zip(betas, ses, ns, strict=True)]
    summ = bd._summarise_placebo(draws, [name], "matched", 0)
    rd = bd.placebo_reading(summ, {"tests": {name: {"testable": real.get("testable", False),
                                                     "se": real.get("se"), "n": real.get("n")}}})
    return {"summary": bd._clean(summ), "reading": bd._clean(rd)}


def perm_gate(real_stat: float, stats: list[float]) -> dict:
    """Within-market timing gate for E013/E014. Each draw rotates every market's flow series by a random non-zero
    offset (markets with one row lose their flow), so a draw keeps each market's flow multiset and its link to the
    market's level, and breaks only the timing. ``p_perm`` = (1 + #{draw >= real}) / (1 + draws); the gate passes
    if p_perm < PERM_ALPHA. ``between_share`` = mean draw / real (descriptive within/between breakdown)."""
    a = np.asarray([v for v in stats if v is not None and np.isfinite(v)], float)
    if not len(a) or real_stat is None or not np.isfinite(real_stat):
        return {"testable": False, "passes": False, "draws": int(len(a))}
    p = float((1 + (a >= real_stat).sum()) / (1 + len(a)))
    return {"testable": True, "draws": int(len(a)), "real_on_gate_rows": float(real_stat), "mean": float(a.mean()),
            "sd": float(a.std(ddof=1)) if len(a) > 1 else None, "p_perm": p, "passes": bool(p < PERM_ALPHA),
            "between_share": float(a.mean() / real_stat) if real_stat else None}


def verdict(name: str, r: dict, placebo: dict | None, available: bool, holm_p: float | None) -> dict:
    if not available:
        return {"verdict": "Unavailable", "p_for_holm": 1.0}
    if not r.get("testable"):
        return {"verdict": "Unavailable (untestable)", "p_for_holm": 1.0}
    if placebo is not None and "gate" in placebo:
        g = placebo["gate"]
        status = "OK" if g.get("passes") else "GATE: within-market timing not shown (p_perm >= 0.05)"
    else:
        status = (placebo or {}).get("reading", {}).get("family_status", "OK")
    ci = r.get("ci_event_boot") or [None, None]
    lo_ci = min(v for v in (ci[0], r["beta"] - bd.Z95 * r["se"]) if v is not None)
    hi_ci = max(v for v in (ci[1], r["beta"] + bd.Z95 * r["se"]) if v is not None)
    out = {"ci95_cons": [lo_ci, hi_ci], "family_status": status}
    if status.startswith("VOID"):
        return {**out, "verdict": "Void (placebo range excludes 0)", "p_for_holm": 1.0}
    if status.startswith("PLACEBO BIAS"):
        return {**out, "verdict": "Inconclusive (placebo bias)", "p_for_holm": 1.0}
    if status.startswith("GATE"):
        hi_ci = out["ci95_cons"][1]
        return {**out, "verdict": "Contradicted" if hi_ci < 0 else "Inconclusive (within-market timing not shown)",
                "p_for_holm": 1.0}
    out["p_for_holm"] = float(r["p"])
    if holm_p is None:
        return out
    if holm_p < 0.05 and r["beta"] > 0:
        out["verdict"] = "Supported (exploratory, prospective)"
    elif hi_ci < 0:
        out["verdict"] = "Contradicted"
    else:
        out["verdict"] = "Inconclusive"
    return out


# --- economics ----------------------------------------------------------------------------------------------------


def paper_taker(df: pd.DataFrame, direction: np.ndarray, tag: str) -> np.ndarray:
    """Per-share net P&L of a taker round trip: enter at the origin touch, exit at the ``tag`` touch, fee both legs.
    Long outcome 0 (direction +1): bid_j - ask_i; short (buy outcome 1): bid_i - ask_j, fees at the outcome-1
    prices."""
    bi, ai = df["bid_i"].to_numpy(float), df["ask_i"].to_numpy(float)
    bj, aj = df[f"bid_{tag}"].to_numpy(float), df[f"ask_{tag}"].to_numpy(float)
    rate, ex = df["fee_rate"].to_numpy(float), df["fee_exp"].to_numpy(float)
    d = np.asarray(direction, float)
    p_in = np.where(d > 0, ai, 1.0 - bi)
    p_out = np.where(d > 0, bj, 1.0 - aj)

    def fee(p):
        q = np.clip(p, 0.0, 1.0)
        return rate * (q * (1.0 - q)) ** ex

    gross = np.where(d > 0, bj - ai, bi - aj)
    return gross - fee(p_in) - fee(p_out)


def econ_summary(pnl: np.ndarray, ev: np.ndarray, day: np.ndarray, seed: int) -> dict:
    ok = np.isfinite(pnl)
    n, ne = int(ok.sum()), int(pd.unique(ev[ok]).size) if ok.any() else 0
    if n < economics.MIN_TRADES or ne < economics.MIN_CLUSTERS:
        return {"trades": n, "events": ne, "verdict": "not shown (below 30 trades / 10 events)"}
    r = battery.mean_test(pnl[ok], ev[ok], day[ok], sign=+1, n_boot=N_BOOT, seed=seed)
    covers = r["mean"] > 0 and r["p"] < 0.05
    return {**bd._clean(r), "trades": n, "events": ne,
            "verdict": "covers taker costs (paper)" if covers else "not shown"}


# --- per-experiment analyses ----------------------------------------------------------------------------------------


def e012(root: Path, start: float, end: float, roles: tuple[str, ...], spec: dict, placebo_draws: int) -> dict:
    df = _load_pairs(root, "e012", start, end, roles, spec["_sha256"][:16] if spec.get("_pinned") else None)
    if df.empty:
        return {"available": False, "reason": "no lines"}
    acc = {"lines": len(df), "pending": int(df.get("pending", pd.Series(0, index=df.index)).fillna(0).sum())}
    df = df[df.get("status_j", pd.Series(index=df.index, dtype=object)).notna()].copy()
    df["late"] = _late(df, "j")
    acc.update(late=int(df["late"].sum()), missing_capture=int((df["status_j"] == "missing_capture").sum()),
               unavailable=int((df["status_j"] == "unavailable").sum()), h_not_tight=int((df["tight_h"] != 1).sum()))
    df = df[(~df["late"]) & (df["status_j"] == "evaluated") & (df["tight_h"] == 1) & np.isfinite(df["x"])].copy()
    df["day"] = _day(df["capture_t"])
    df["dprev0"] = df["dprev"].fillna(0.0)
    df["ix"] = df["x"] * df["zL"]
    y = _mid(df, "j") - df["mid_i"].to_numpy(float)
    seed = SEEDS["E012"]
    r = demeaned_fit(df, y, "ix", ["x", "zL", *CONTROLS_E012], "capture_t", seed=seed)
    fl = FLOORS["E012"]
    used = df[r["_mask"]] if r.get("testable") else df.iloc[0:0]
    available = (len(used) >= fl["rows"] and used["event_id"].nunique() >= fl["events"]
                 and used["day"].nunique() >= fl["days"])
    out = {"accounting": acc, "primary": _strip(r), "available": bool(available),
           "rows": len(used), "events": int(used["event_id"].nunique()), "days": int(used["day"].nunique())}
    if r.get("testable"):
        Xd = bd.expanding_demean(df[["market_id", "capture_t", "ix", "x", "zL", *CONTROLS_E012]],
                                 ["ix", "x", "zL", *CONTROLS_E012], "market_id", "capture_t")
        m = r["_mask"]
        out["lodo"] = bd._clean(bd.lodo(y[m], Xd["ix"].to_numpy()[m],
                                        Xd[["x", "zL", *CONTROLS_E012]].to_numpy()[m], df["day"].to_numpy()[m],
                                        r["beta"]))
        out["placebo"] = e012_placebo(root, df, y, r, placebo_draws, seed + 100)
        sens = {}
        sens["pooled"] = _strip(demeaned_fit(df, y, "ix", ["x", "zL", *CONTROLS_E012], "capture_t",
                                             estimator="pooled", seed=seed, n_boot=200))
        sens["fe_within"] = _strip(demeaned_fit(df, y, "ix", ["x", "zL", *CONTROLS_E012], "capture_t",
                                                estimator="fe", seed=seed, n_boot=200))
        jt = df["tight_j"] == 1
        sens["j_tight"] = _strip(demeaned_fit(df[jt].reset_index(drop=True), y[jt.to_numpy()], "ix",
                                              ["x", "zL", *CONTROLS_E012], "capture_t", seed=seed, n_boot=200))
        big = df.groupby("market_id")["market_id"].transform("size") >= 20
        sens["markets_ge_20_rows"] = _strip(demeaned_fit(df[big].reset_index(drop=True), y[big.to_numpy()], "ix",
                                                         ["x", "zL", *CONTROLS_E012], "capture_t", seed=seed,
                                                         n_boot=200))
        g = df.copy()
        g["ixg"] = g["chg_1d_g"] * g["zL"]
        sens["gamma_chg_1d"] = _strip(demeaned_fit(g, y, "ixg", ["chg_1d_g", "chg_1d_missing", "zL",
                                                                   *CONTROLS_E012], "capture_t", seed=seed, n_boot=200))
        out["sensitivities"] = bd._clean(sens)
        fire = (df["L"] == 0) & (df["x"].abs() >= spec["e012"]["econ"]["min_abs_x"])
        f = df[fire.to_numpy()]
        pnl = paper_taker(f, -np.sign(f["x"].to_numpy(float)), "j")
        out["economics"] = econ_summary(pnl, f["event_id"].to_numpy(), f["day"].to_numpy(), seed + 7)
        top = (df["L"] >= spec["e012"]["econ"]["liquid_cut"]) & (df["x"].abs() >= spec["e012"]["econ"]["min_abs_x"])
        t = df[top.to_numpy()]
        out["economics_descriptive_follow_liquid"] = econ_summary(
            paper_taker(t, np.sign(t["x"].to_numpy(float)), "j"), t["event_id"].to_numpy(), t["day"].to_numpy(),
            seed + 8)
    return out


def _series_long(root: Path, market_ids: set[str], slot_lo: int, slot_hi: int, spec: dict) -> pd.DataFrame:
    st = lt.State(Path(root))
    parts = []
    for cid, c in st.d["captures"].items():
        if c["slot"] is None or not (slot_lo <= c["slot"] <= slot_hi):
            continue
        ser = lt.read_series(root, cid)
        if ser is None:
            continue
        ser = ser[ser.index.isin(market_ids)]
        parts.append(pd.DataFrame({"market_id": ser.index, "slot": c["slot"],
                                   "mid": ((ser["bid"] + ser["ask"]) / 2.0).to_numpy()}))
    if not parts:
        return pd.DataFrame(columns=["market_id", "slot", "mid"])
    return pd.concat(parts, ignore_index=True).drop_duplicates(["market_id", "slot"])


def e012_placebo(root: Path, df: pd.DataFrame, y: np.ndarray, real: dict, draws: int, seed: int) -> dict:
    """J4-R increment-bootstrap placebo on the full 2 h series: x, y, dprev and the mid-level controls are rebuilt
    from the resampled levels; tightness flags, volume and Gamma change fields stay as observed."""
    h = 12
    sl = pd.DataFrame({"market_id": df["market_id"].astype(str).to_numpy(), "slot": df["slot"].to_numpy(int)})
    S = _series_long(root, set(sl["market_id"]), int(sl["slot"].min()) - h, int(sl["slot"].max()) + h, {})
    if S.empty:
        return {"testable": False, "reason": "no series"}
    codes_map = {m: i for i, m in enumerate(pd.unique(S["market_id"]))}
    sc = S["market_id"].map(codes_map).to_numpy(np.int64)
    betas, ses, ns = [], [], []
    for d in range(draws):
        rb = rebuild_series(sc, S["slot"].to_numpy(np.int64), S["mid"].to_numpy(float), seed + d)
        lev = pd.Series(rb, index=pd.MultiIndex.from_arrays([S["market_id"].to_numpy(), S["slot"].to_numpy()]))

        def at(off, lev=lev):
            idx = pd.MultiIndex.from_arrays([sl["market_id"].to_numpy(), sl["slot"].to_numpy() + off])
            return lev.reindex(idx).to_numpy(float)

        mi, mh, mj, mp = at(0), at(-h), at(h), at(-1)
        p = df.copy()
        p["x"] = mi - mh
        p["ix"] = p["x"] * p["zL"]
        p["dprev0"] = np.where(np.isfinite(mi - mp), mi - mp, 0.0)
        p["dprev_missing"] = (~np.isfinite(mi - mp)).astype(int)
        with np.errstate(divide="ignore", invalid="ignore"):
            p["logit_mid"] = np.log(mi / (1 - mi))
        p["abs_dev"] = np.abs(mi - 0.5)
        r = demeaned_fit(p, mj - mi, "ix", ["x", "zL", *CONTROLS_E012], "capture_t", seed=seed, n_boot=20)
        if r.get("testable"):
            betas.append(r["beta"])
            ses.append(r["se"])
            ns.append(r["n"])
    return _read_rule(real, betas, ses, ns, "E012")


def flow(root: Path, start: float, end: float, roles: tuple[str, ...], spec: dict, placebo_draws: int | None) -> dict:
    df = _load_pairs(root, "flow", start, end, roles, spec["_sha256"][:16] if spec.get("_pinned") else None)
    if df.empty:
        return {"E013_F4": {"available": False, "reason": "no lines"}, "E013_F5": {"available": False},
                "E014": {"available": False, "reason": "no lines"}}
    df = df[df.get("status_j2", pd.Series(index=df.index, dtype=object)).notna()].copy()
    df["day"] = _day(df["capture_t"])
    df["dprev0"] = df["dprev"].fillna(0.0)
    out = {}
    # E013 (F4, F5)
    d = df.copy()
    d["late"] = _late(d, "j6")
    acc = {"lines": len(d), "late": int(d["late"].sum()), "unavailable_j6": int((d["status_j6"] != "evaluated").sum()),
           "not_tight": int((d["tight_i"] != 1).sum()), "no_6h_flow_or_truncated": int((~np.isfinite(d["x6"])).sum())}
    d = d[(~d["late"]) & (d["status_j6"] == "evaluated") & (d["tight_i"] == 1) & (d["end_ok_6h"] == 1)
          & (d["n6"] > 0) & np.isfinite(d["x6"])].reset_index(drop=True)
    y6 = _mid(d, "j6") - d["mid_i"].to_numpy(float)
    for name, mod, cutkey in (("E013_F4", "zRV", "lrv_upper_tercile_cut"),
                              ("E013_F5", "zSPR", "spr_upper_tercile_cut")):
        dd = d[np.isfinite(d[mod])].reset_index(drop=True)
        yy = y6[np.isfinite(d[mod]).to_numpy()]
        dd["ix"] = dd["x6"] * dd[mod]
        seed = SEEDS[name]
        r = demeaned_fit(dd, yy, "ix", ["x6", mod, *CONTROLS_FLOW], "t_row", seed=seed)
        fl = FLOORS["E013"]
        used = dd[r["_mask"]] if r.get("testable") else dd.iloc[0:0]
        res = {"accounting": acc, "primary": _strip(r), "rows": len(used), "events": int(used["event_id"].nunique()),
               "days": int(used["day"].nunique())}
        res["available"] = bool(res["rows"] >= fl["rows"] and res["events"] >= fl["events"]
                                and res["days"] >= fl["days"])
        if r.get("testable"):
            codes = pd.factorize(dd["market_id"])[0]
            draws = []
            for k in range(placebo_draws if placebo_draws is not None else PERM_DRAWS["E013"]):
                p = dd.copy()
                p["x6"] = cyclic_shift_within(codes, dd["t_row"].to_numpy(float), dd["x6"].to_numpy(float),
                                              seed + 100 + k)
                p["ix"] = p["x6"] * p[mod]
                rp = demeaned_fit(p, yy, "ix", ["x6", mod, *CONTROLS_FLOW], "t_row", seed=seed, n_boot=1)
                draws.append(rp["beta"] if rp.get("testable") else None)
            res["placebo"] = {"gate": perm_gate(r["beta"], draws)}
            sens = {"pooled": _strip(demeaned_fit(dd, yy, "ix", ["x6", mod, *CONTROLS_FLOW], "t_row",
                                                  estimator="pooled", seed=seed, n_boot=200)),
                    "fe_within": _strip(demeaned_fit(dd, yy, "ix", ["x6", mod, *CONTROLS_FLOW], "t_row",
                                                     estimator="fe", seed=seed, n_boot=200)),
                    "weighted": _strip(demeaned_fit(dd, yy, "ix", ["x6", mod, *CONTROLS_FLOW], "t_row", seed=seed,
                                                    n_boot=200, w=1.0 / dd["p_incl"].to_numpy(float)))}
            lg = dd[np.isfinite(dd["x6_lag30"])].reset_index(drop=True)
            lg["ixl"] = lg["x6_lag30"] * lg[mod]
            sens["flow_ends_30min_early"] = _strip(demeaned_fit(lg, yy[np.isfinite(dd["x6_lag30"]).to_numpy()], "ixl",
                                                                ["x6_lag30", mod, *CONTROLS_FLOW], "t_row", seed=seed,
                                                                n_boot=200))
            jt = (dd["tight_j6"] == 1).to_numpy()
            sens["j6_tight"] = _strip(demeaned_fit(dd[jt].reset_index(drop=True), yy[jt], "ix",
                                                   ["x6", mod, *CONTROLS_FLOW], "t_row", seed=seed, n_boot=200))
            res["sensitivities"] = bd._clean(sens)
            lmod = np.log(dd["rv"].to_numpy(float) + 1e-4) if mod == "zRV" else dd["spread_i"].to_numpy(float)
            fire = (lmod >= spec["flow"]["econ"][cutkey] - 1e-9) & (dd["imb6"].abs().to_numpy() >= spec["flow"]["econ"][
                "min_abs_imb"])
            f = dd[fire]
            dirn = np.sign(f["imb6"].to_numpy(float))
            res["economics"] = econ_summary(paper_taker(f, dirn, "j6"), f["event_id"].to_numpy(), f["day"].to_numpy(),
                                            seed + 7)
            gross = dirn * (_mid(f, "j6") - f["mid_i"].to_numpy(float))
            res["economics_descriptive"] = {
                "gross_mid_to_mid_mean": float(np.nanmean(gross)) if len(f) else None,
                "maker_upper_bound_mean": float(np.nanmean(gross + f["spread_i"].to_numpy(float) / 2.0))
                if len(f) else None,
                "note": "maker bound = enter at own-side touch with certain fill, exit at the target mid, no fee; no "
                        "fill model, an upper bound only, never a claim"}
        out[name] = res
    # E014
    e = df.copy()
    e["late"] = _late(e, "j2")
    acc14 = {"lines": len(e), "late": int(e["late"].sum()), "unavailable_j2": int((e["status_j2"] != "evaluated").sum()),
             "regime_counts_flow_rows": e.loc[e["ss"] != 0, "regime"].value_counts().to_dict()}
    e = e[(~e["late"]) & (e["status_j2"] == "evaluated") & (e["tight_i"] == 1) & (e["ss"] != 0)
          & e["regime"].isin(["A", "B"])].reset_index(drop=True)
    out["E014"] = e014_tests(e, acc14, spec, placebo_draws)
    return out


def _gain(y: np.ndarray, pb: np.ndarray, pa: np.ndarray) -> np.ndarray:
    return (y - pb) ** 2 - (y - pa) ** 2


def e014_tests(e: pd.DataFrame, acc: dict, spec: dict, placebo_draws: int | None = None) -> dict:
    seed = SEEDS["E014"]
    res: dict = {"accounting": acc}
    if e.empty:
        return {**res, "available": False, "reason": "no rows"}
    y = _mid(e, "j2") - e["mid_i"].to_numpy(float)
    g = _gain(y, e["p_base"].to_numpy(float), e["p_aug"].to_numpy(float))
    A = (e["regime"] == "A").to_numpy(float)
    ev, day = e["event_id"].to_numpy(), e["day"].to_numpy()
    r = battery.beta_test(g, A, np.empty((len(g), 0)), ev, day, sign=+1, n_boot=4000, seed=seed)
    if r.get("testable"):
        r["se"] = max(r["se_event"], r["se_twoway"])
        r["mde_80"] = 2.8 * r["se"]
    fl = FLOORS["E014"]
    nA, nB = int(A.sum()), int((1 - A).sum())
    evA, evB = int(pd.unique(ev[A == 1]).size), int(pd.unique(ev[A == 0]).size)
    res.update(primary=bd._clean(r), rows_A=nA, rows_B=nB, events_A=evA, events_B=evB, days=int(pd.unique(day).size),
               mean_gain_A=float(g[A == 1].mean()) if nA else None, mean_gain_B=float(g[A == 0].mean()) if nB else None)
    res["available"] = bool(min(nA, nB) >= fl["rows_regime"] and min(evA, evB) >= fl["events_regime"]
                            and res["days"] >= fl["days"])
    if not r.get("testable"):
        return res
    codes = pd.factorize(e["market_id"])[0]
    multi = np.bincount(codes)[codes] >= 2
    c = spec["e014"]["augmented"]
    pb = e["p_base"].to_numpy(float)
    chg = e["chg_1h"].to_numpy(float)

    def contrast(gv: np.ndarray, m: np.ndarray) -> float:
        a_, b_ = m & (A == 1), m & (A == 0)
        return float(gv[a_].mean() - gv[b_].mean()) if a_.any() and b_.any() else float("nan")

    draws = []
    for k in range(placebo_draws if placebo_draws is not None else PERM_DRAWS["E014"]):
        ssp = cyclic_shift_within(codes, e["t_row"].to_numpy(float), e["ss"].to_numpy(float), seed + 100 + k)
        pa = c["intercept"] + c["chg_1h"] * chg + c["signed_share"] * np.where(np.isfinite(ssp), ssp, 0.0)
        draws.append(contrast(_gain(y, pb, pa), multi))
    res["placebo"] = {"gate": perm_gate(contrast(g, multi), draws), "gate_rows": int(multi.sum())}
    w = 1.0 / e["p_incl"].to_numpy(float)
    sens = {"weighted": battery.beta_test(g, A, np.empty((len(g), 0)), ev, day, sign=+1, n_boot=200, seed=seed, w=w)}
    rel = {}
    for lab, m in (("A", A == 1), ("B", A == 0)):
        sb = float(((y[m] - e["p_base"].to_numpy(float)[m]) ** 2).sum())
        sa = float(((y[m] - e["p_aug"].to_numpy(float)[m]) ** 2).sum())
        rel[lab] = 1.0 - sa / sb if sb > 0 else None
    sens["relative_gain"] = {**rel, "contrast": (rel["A"] - rel["B"]) if None not in rel.values() else None}
    rr = y - e["p_base"].to_numpy(float)
    ss = e["ss"].to_numpy(float)
    sens["slope_contrast"] = battery.beta_test(rr, ss * A, np.column_stack([ss, A]), ev, day, sign=+1, n_boot=200,
                                               seed=seed)
    res["sensitivities"] = bd._clean(sens)
    ec = spec["e014"]["econ"]
    fire = (A == 1) & (np.abs(ss) >= ec["abs_ss"]) & (e["n_trades_1h"].to_numpy(float) >= ec["min_trades_1h"])
    f = e[fire]
    res["economics"] = econ_summary(paper_taker(f, np.sign(f["ss"].to_numpy(float)), "j2"), f["event_id"].to_numpy(),
                                    f["day"].to_numpy(), seed + 7)
    return res


def analyze(root: Path = lt.OUT_ROOT, *, start_utc: str = lt.REGISTERED_UTC, end_utc: str = lt.END_UTC,
            spec: dict | None = None, roles: tuple[str, ...] = (lt.ROLE_CONF,), placebo_draws: int = PLACEBO_DRAWS,
            perm_draws: int | None = None, force: bool = False) -> dict:
    """The single registered analysis. Refuses before ANALYSIS_NOT_BEFORE unless ``force`` (tests only)."""
    if not force and lt.now_ts() < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise RuntimeError(f"analysis refused before {lt.ANALYSIS_NOT_BEFORE}")
    spec = spec or lt.load_spec()
    s, e = lt.epoch(start_utc), lt.epoch(end_utc)
    res = {"E012": e012(root, s, e, roles, spec, placebo_draws)}
    res.update(flow(root, s, e, roles, spec, perm_draws))
    pv = {}
    for k in ("E012", "E013_F4", "E013_F5", "E014"):
        r = res[k]
        v = verdict(k, r.get("primary", {}), r.get("placebo"), r.get("available", False), None)
        pv[k] = v["p_for_holm"]
    hp = bd.holm(pv)
    for k in pv:
        r = res[k]
        res[k]["holm_p"] = hp[k]
        res[k]["verdict"] = verdict(k, r.get("primary", {}), r.get("placebo"), r.get("available", False), hp[k])
    res["holm"] = {"m": 4, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True}
    res["spec_sha"] = spec["_sha256"]
    res["window"] = [start_utc, end_utc]
    res["roles"] = list(roles)
    return bd._clean(res) if isinstance(res, dict) else res

