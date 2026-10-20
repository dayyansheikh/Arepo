# ruff: noqa: E501
"""Single registered analysis of the live tests E012-E014 (docs/research_lab/LIVE_TESTS_2.md). DRAFT until registered.

Runs ONCE, after ``live_tests2.ANALYSIS_NOT_BEFORE``, on the write-once files of ``live_tests2``. Four primaries in one
Holm family (one-sided, familywise alpha 0.05): E012 (1-day change x liquidity), E013-F4 (6 h flow x volatility),
E013-F5 (6 h flow x spread), E014 (near-end gain of the frozen E007 flow model). A primary that is unavailable, void,
placebo-biased or fails its timing gate enters Holm with p = 1. Economics are separate and never change a primary
verdict.

Estimators (J4-R lessons, SCREENING_BATCH_2.md): E012 and E013 use the expanding-past demeaned OLS (every regressor
minus the market's mean over its strictly earlier rows; target raw), event-clustered and two-way event x time-cluster
SEs (``battery.beta_test``). Primary one-sided p (challenger R1 finding 5) = max(p_event, p_twoway, p_t), p_t = the
two-way z referred to Student t with G - 1 df (G = time clusters: two-day blocks for E012, UTC days for E013/E014).
E012 has a placebo matched to the estimator with the J4-R reading rule (``bounce_decomp.placebo_reading``). E013 and
E014 have a within-market timing gate (far-future control target from later rows of the same market at least flow
window + horizon away; challenger R1 finding 1). E014 is a difference of mean per-row squared-error gains between two as-of time-to-end regimes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import battery, economics
from . import bounce_decomp as bd
from . import live_tests2 as lt

SEEDS = {"E012": 20261022, "E013_F4": 20261023, "E013_F5": 20261024, "E014": 20261025}
N_BOOT = 2000
PLACEBO_DRAWS = 20  # E012: J4-R increment-bootstrap placebo (regenerates x and y), J4-R reading rule
GATE_ALPHA = 0.05
# Timing gate (LIVE_TESTS_2.md section 1.5; challenger R1 finding 1): far-future control target. A row's sources are
# LATER test rows of the same market (E014: market and regime) whose origin is at least min_sep_s later (flow window +
# target horizon: E013 6 h + 6 h, E014 1 h + 2 h); only rows with >= min_sources sources enter the gate.
GATE = {"E013": {"min_sep_s": 12 * 3600.0, "min_sources": 4, "min_rows": 1000, "min_markets": 100},
        "E014": {"min_sep_s": 3 * 3600.0, "min_sources": 4, "min_rows_regime": 50}}
FLOORS = {"E012": {"rows": 20000, "events": 200, "days": 10},
          "E013": {"rows": 10000, "events": 500, "days": 10},
          "E014": {"rows_regime": 1000, "events_regime": 100, "days": 10}}
ATTRITION_PP = 0.05  # differential attrition label threshold (absolute difference of unavailable shares)
LABEL_FRACTION = 0.5  # E012 skip-slot and E013 lag-30 mechanism labels: the check slope must reach 0.5 x the primary
BLOCK_S = 2 * 86400.0  # E012 time clusters: two-day blocks anchored at the window start
CONTROLS_E012 = ["logit_mid", "abs_dev", "chg_1h", "chg_1h_missing", "chg_1w", "chg_1w_missing", "dprev0",
                 "dprev_missing"]
CONTROLS_SKIP = [c for c in CONTROLS_E012 if not c.startswith("dprev")]
CONTROLS_FLOW = ["logit_mid", "abs_dev", "chg_1h", "chg_1h_missing", "chg_1d_g", "chg_1d_missing", "chg_1w",
                 "chg_1w_missing", "dprev0", "dprev_missing"]


# --- code and spec pins ---------------------------------------------------------------------------------------------


def code_hashes() -> dict:
    """Normalised sha256 of the collector and analysis modules as run (``live_tests2.code_sha256``)."""
    return lt.code_hashes()


def code_check(spec: dict) -> dict:
    """Compare the modules on disk with the spec's ``code_sha256`` map. A pinned spec refuses to run on any mismatch
    (or an unfilled map / an unfilled E013 volume cap); an unpinned (DRAFT) spec only labels the result."""
    pins = spec.get("code_sha256") or {}
    cur = code_hashes()
    status = {n: ("not pinned" if pins.get(n) is None else ("match" if pins.get(n) == h else "MISMATCH"))
              for n, h in cur.items()}
    if spec.get("_pinned"):
        bad = {n: s for n, s in status.items() if s != "match"}
        if bad:
            raise RuntimeError(f"live_tests2 code sha256 does not match the registered pins: {bad}")
        if spec["flow"].get("vol24_cap") is None:
            raise RuntimeError("live_tests2 spec pinned with an unfilled flow.vol24_cap")
    return {"current": cur, "pinned": {n: pins.get(n) for n in cur}, "status": status,
            "label": None if all(s == "match" for s in status.values()) else "DRAFT: code hashes not verified"}


# --- loading ------------------------------------------------------------------------------------------------------


def _load_pairs(root: Path, kind: str, start: float, end: float, roles: tuple[str, ...],
                spec: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Frozen lines of origins in [start, end) with an allowed role, merged with their outcome file. With a pinned
    spec, only lines whose ``spec_sha`` and ``code_sha`` equal the registered pins are kept (section 1.1: the
    effective start is enforced by these checks); dropped lines are counted."""
    fdir, odir = Path(root) / kind / "frozen", Path(root) / kind / "outcomes"
    pinned = bool(spec and spec.get("_pinned"))
    want_spec = spec["_sha256"][:16] if pinned else None
    want_code = ((spec.get("code_sha256") or {}).get("live_tests2.py") or "")[:16] if pinned else None
    acc = {"dropped_role": 0, "dropped_spec_sha": 0, "dropped_code_sha": 0}
    parts = []
    for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
        if p.name.endswith(".late.csv.gz"):
            continue
        fr = pd.read_csv(p, dtype={"market_id": str, "event_id": str, "spec_sha": str, "code_sha": str})
        if not len(fr) or not (start <= float(fr["capture_t"].iloc[0]) < end):
            continue
        keep = fr["role"].isin(roles)
        acc["dropped_role"] += int((~keep).sum())
        fr = fr[keep]
        if pinned:
            ok = fr["spec_sha"].astype(str) == want_spec
            acc["dropped_spec_sha"] += int((~ok).sum())
            fr = fr[ok]
            code = fr["code_sha"].astype(str) if "code_sha" in fr else pd.Series("", index=fr.index)
            ok = code == want_code
            acc["dropped_code_sha"] += int((~ok).sum())
            fr = fr[ok]
        op = odir / p.name
        if op.exists():
            out = pd.read_csv(op, dtype={"market_id": str})
            fr = fr.merge(out, on="market_id", how="left")
        else:
            fr["pending"] = 1
        fr["file"] = p.name
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(df):
        acc["first_origin_capture_utc"] = lt.iso(float(df["capture_t"].min()))
        acc["code_commits"] = sorted({str(c) for c in df.get("code_commit", pd.Series(dtype=str)).dropna()})
    return df, acc


def _day(t: pd.Series) -> np.ndarray:
    return pd.to_datetime(t, unit="s", utc=True).dt.strftime("%Y-%m-%d").to_numpy()


def _tblock(t: pd.Series, start: float) -> np.ndarray:
    """Two-day block index anchored at the window start (E012 time clusters)."""
    return np.floor((np.asarray(t, float) - start) / BLOCK_S).astype(int).astype(str)


def _late(df: pd.DataFrame, tag: str) -> np.ndarray:
    fz = lt.panel._epoch(df["frozen_utc"])
    cs = df[f"cap_start_{tag}"].to_numpy(float) if f"cap_start_{tag}" in df else np.full(len(df), np.nan)
    with np.errstate(invalid="ignore"):
        return np.isfinite(cs) & ~(fz < cs)


def _mid(df: pd.DataFrame, tag: str) -> np.ndarray:
    return (df[f"bid_{tag}"].to_numpy(float) + df[f"ask_{tag}"].to_numpy(float)) / 2.0


def _unavail(status) -> np.ndarray:
    return pd.Series(np.asarray(status, object)).astype(str).str.startswith("unavailable").to_numpy()


# --- estimator, inference, placebo, gate ----------------------------------------------------------------------------


def p_primary(r: dict) -> dict:
    """Primary one-sided p and conservative 95% CI (challenger R1 finding 5): p = max(p_event, p_twoway, p_t) with
    p_t = sf of the two-way z under Student t with G - 1 df (G = time clusters in the fit; G < 2 gives p = 1). The
    conservative CI is the hull of the event bootstrap CI, beta +/- 1.96 se_event and beta +/- t(0.975, G-1) se_twoway."""
    g = int(r.get("n_day") or 0)
    r["n_time_clusters"] = g
    if g < 2:
        r["p_t_time"], r["p"] = 1.0, 1.0
        tq = float("inf")
    else:
        r["p_t_time"] = float(t_dist.sf(r["z_twoway"], df=g - 1))
        r["p"] = max(float(r["p_event"]), float(r["p_twoway"]), r["p_t_time"])
        r["t_df"] = g - 1
        tq = float(t_dist.ppf(0.975, g - 1))
    ci = r.get("ci_event_boot") or [None, None]
    lo = [v for v in (ci[0], r["beta"] - bd.Z95 * r["se_event"], r["beta"] - tq * r["se_twoway"]) if v is not None]
    hi = [v for v in (ci[1], r["beta"] + bd.Z95 * r["se_event"], r["beta"] + tq * r["se_twoway"]) if v is not None]
    r["ci95_cons"] = [min(lo), max(hi)]
    return r


def demeaned_fit(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], order: str, *,
                 estimator: str = "expanding", seed: int, n_boot: int = N_BOOT, w=None, cluster: str = "day") -> dict:
    """Slope of ``term`` given ``controls`` (one-sided, + sign). ``expanding``: J4-R demeaning of every regressor;
    ``pooled``: raw; ``fe``: full-sample market demeaning (descriptive within-market slope only). ``cluster`` = the
    time-cluster column of the two-way SE and of the t reference."""
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
    r = battery.beta_test(y[ok], Xo[:, 0], Xo[:, 1:], df["event_id"].to_numpy()[ok], df[cluster].to_numpy()[ok],
                          sign=+1, n_boot=n_boot, seed=seed, w=None if w is None else np.asarray(w)[ok])
    if not r.get("testable"):
        return {"testable": False, "reason": r.get("reason"), "n": int(ok.sum()), "p": 1.0}
    r["se"] = max(r["se_event"], r["se_twoway"])
    r["mde_80"] = 2.8 * r["se"]
    p_primary(r)
    r["time_cluster"] = cluster
    r["n_market"] = int(pd.unique(df["market_id"].to_numpy()[ok]).size)
    r["estimator"] = estimator
    r["_mask"] = ok
    return r


def _strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.startswith("_")}


def gate_sources(codes: np.ndarray, t: np.ndarray, is_src: np.ndarray, min_sep_s: float) -> dict:
    """Candidate source rows per row: rows of the same group with ``is_src`` and |t_s - t_i| >= ``min_sep_s``
    (``n_left`` earlier, ``n_right`` later). Sources of a group sit contiguously in ``sidx`` in time order; the later
    ones of row i are ``sidx[hi[i] : hi[i] + n_right[i]]``."""
    codes = np.asarray(codes, np.int64)
    t = np.asarray(t, float)
    is_src = np.asarray(is_src, bool) & np.isfinite(t)
    t0 = float(np.nanmin(t)) if len(t) else 0.0
    trel = np.nan_to_num(t - t0, nan=0.0)
    span = float(trel.max() if len(t) else 0.0) + min_sep_s + 1.0
    big = 4.0 * span
    src = np.flatnonzero(is_src)
    key = codes[src] * big + trel[src]
    o = np.argsort(key, kind="mergesort")
    skey, sidx = key[o], src[o]
    base = codes * big
    gstart = np.searchsorted(skey, base - 0.5, "left")
    gend = np.searchsorted(skey, base + span, "left")
    lo = np.maximum(np.searchsorted(skey, base + trel - min_sep_s, "right"), gstart)
    hi = np.minimum(np.searchsorted(skey, base + trel + min_sep_s, "left"), gend)
    fin = np.isfinite(t)
    n_left, n_right = np.where(fin, lo - gstart, 0), np.where(fin, np.maximum(gend - hi, 0), 0)
    return {"sidx": sidx, "gstart": gstart, "hi": hi, "n_left": n_left, "n_right": n_right, "n": n_left + n_right}


def forward_sources(groups, t, test_rows, min_sep_s: float, min_sources: int) -> dict:
    """Timing-gate sources (LIVE_TESTS_2.md section 1.5; challenger R1 finding 1): the sources of a test row are the
    LATER test rows of the same group (E013: market; E014: market x regime) whose origin is at least ``min_sep_s``
    (flow window + target horizon) after it, so a source's target never overlaps the row's flow window or target.
    Earlier rows are never sources: the expanding-past demeaning puts earlier rows' flow windows into every row's
    regressors. Gate rows = test rows with >= ``min_sources`` sources."""
    codes = pd.factorize(pd.Series(np.asarray(groups)).astype(str))[0].astype(np.int64)
    test_rows = np.asarray(test_rows, np.int64)
    is_src = np.zeros(len(codes), bool)
    is_src[test_rows] = True
    gs = gate_sources(codes, t, is_src, min_sep_s)
    g = test_rows[gs["n_right"][test_rows] >= min_sources]
    return {"gs": gs, "rows": g, "n_src": gs["n_right"][g]}


def source_mean(fs: dict, v) -> np.ndarray:
    """Mean of ``v`` (aligned with all rows) over each gate row's sources (the far-future control target)."""
    gs, g = fs["gs"], fs["rows"]
    cs = np.r_[0.0, np.cumsum(np.asarray(v, float)[gs["sidx"]])]
    a, n = gs["hi"][g], gs["n_right"][g]
    return (cs[a + n] - cs[a]) / n


def _cluster_t(b: float, rx: np.ndarray, e: np.ndarray, evc: np.ndarray, n_ev: int) -> float:
    """t of a slope from its FWL-residualised regressor ``rx`` and the model residual ``e``, event-clustered (CR1
    factor G / (G - 1))."""
    sxx = float(rx @ rx)
    if sxx <= 1e-15 or n_ev < 2:
        return float("nan")
    sc = np.bincount(evc, weights=rx * e, minlength=n_ev)
    v = float((sc ** 2).sum()) / sxx ** 2 * n_ev / (n_ev - 1)
    return b / np.sqrt(v) if v > 0 else float("nan")


def _basis(M: np.ndarray) -> np.ndarray:
    U, s, _ = np.linalg.svd(M, full_matrices=False)
    return U[:, s > 1e-10 * s.max()] if len(s) and s.max() > 0 else U[:, :0]


class _ClusterJack:
    """Delete-one-cluster jackknife of one OLS coefficient (CR3-equivalent, conservative with few or unequal
    clusters) for a fixed design ``X`` (intercept included) and any target vector."""

    def __init__(self, X: np.ndarray, evc: np.ndarray, n_ev: int):
        self.X, self.evc, self.G = X, evc, n_ev
        k = X.shape[1]
        xtx = X.T @ X
        xg = np.zeros((n_ev, k, k))
        for a in range(k):
            for b in range(a, k):
                v = np.bincount(evc, weights=X[:, a] * X[:, b], minlength=n_ev)
                xg[:, a, b] = v
                xg[:, b, a] = v
        self.full = np.linalg.pinv(xtx)
        self.drop = np.linalg.pinv(xtx[None] - xg)

    def t(self, y: np.ndarray, j: int) -> float:
        if self.G < 2:
            return float("nan")
        xty = self.X.T @ y
        xtyg = np.column_stack([np.bincount(self.evc, weights=self.X[:, a] * y, minlength=self.G)
                                for a in range(self.X.shape[1])])
        b = float((self.full @ xty)[j])
        bg = np.einsum("gij,gj->gi", self.drop, xty[None] - xtyg)[:, j]
        v = (self.G - 1) / self.G * float(((bg - bg.mean()) ** 2).sum())
        return b / np.sqrt(v) if v > 0 else float("nan")


class _FixedXSlope:
    """Slope of the tested column (``cols[0]``) given the others, every regressor expanding-past demeaned within the
    gate rows (the primary's estimator), event-clustered t, for any target vector aligned with the gate rows."""

    def __init__(self, codes, t, cols: list, ev):
        Xd = np.column_stack([bd._expanding_resid(np.asarray(codes), np.asarray(t, float), np.asarray(c, float))
                              for c in cols])
        self.ok = np.isfinite(Xd).all(axis=1)
        X = Xd[self.ok]
        one = np.ones((len(X), 1))
        self.Qf = _basis(np.column_stack([one, X]))
        Qo = _basis(np.column_stack([one, X[:, 1:]]))
        self.rx = X[:, 0] - Qo @ (Qo.T @ X[:, 0])
        self.evc, ev_u = pd.factorize(np.asarray(ev)[self.ok])
        self.n_ev = len(ev_u)
        self._X = np.column_stack([one, X])
        self._jack: _ClusterJack | None = None

    def stat(self, y, jack: bool = False) -> tuple:
        """(t, beta) of the tested term for target ``y`` (event-clustered CR1 t); with ``jack`` also the
        delete-one-event jackknife t: (t, beta, t_jack)."""
        yo = np.asarray(y, float)[self.ok]
        sxx = float(self.rx @ self.rx)
        if len(yo) < 10 or sxx <= 1e-15 or not np.isfinite(yo).all():
            return (float("nan"), float("nan"), float("nan")) if jack else (float("nan"), float("nan"))
        b = float(self.rx @ yo) / sxx
        e = yo - self.Qf @ (self.Qf.T @ yo)
        t = _cluster_t(b, self.rx, e, self.evc, self.n_ev)
        if not jack:
            return t, b
        if self._jack is None:
            self._jack = _ClusterJack(self._X, self.evc, self.n_ev)
        return t, b, self._jack.t(yo, 1)


def gate_p(t_delta: float, n_clusters: int) -> float:
    """One-sided p of a gate t: Student t with G - 1 df (G = event clusters of the gate rows); 1 if untestable."""
    if t_delta is None or not np.isfinite(t_delta) or n_clusters < 2:
        return 1.0
    return float(t_dist.sf(t_delta, df=n_clusters - 1))


def _gate_result(info: dict, real: tuple, far: tuple, diff: tuple, n_ev: int) -> dict:
    """``diff`` = (CR1 t, delta, jackknife t). p_gate = max of the two one-sided t(G - 1) p values."""
    p_cr1, p_jack = gate_p(diff[0], n_ev), gate_p(diff[2], n_ev)
    p = max(p_cr1, p_jack)
    return {**info, "testable": bool(np.isfinite(diff[0]) and np.isfinite(diff[2])), "real_on_gate_rows": real[1],
            "far_control": far[1], "delta": diff[1], "t_delta": diff[0], "t_delta_jack": diff[2], "df": n_ev - 1,
            "p_cr1": p_cr1, "p_jack": p_jack, "p_gate": p, "passes": bool(p < GATE_ALPHA),
            "between_share": (far[1] / real[1]) if real[1] and np.isfinite(far[1]) else None}


def slope_gate(codes, t, x_all, test_rows, y_all, mod_all, C_all, *, ev_all=None,
               min_sep_s: float = GATE["E013"]["min_sep_s"], min_sources: int = GATE["E013"]["min_sources"],
               min_rows: int = GATE["E013"]["min_rows"], min_markets: int = GATE["E013"]["min_markets"]) -> dict:
    """E013 timing gate (far-future control target): on the gate rows, the interaction slope (expanding-past
    demeaned regressors, as the primary) for the real 6 h target minus the slope for the mean target of the row's
    sources (same market, origin >= 12 h later), i.e. one regression of ``y - y_far``; one-sided p = the larger of
    the event-clustered (CR1) and the delete-one-event jackknife p, each under Student t with G - 1 df. A market-level (between-market) link moves both
    targets alike and cancels; only timing survives. Passes if p_gate < GATE_ALPHA."""
    codes = np.asarray(codes)
    fs = forward_sources(codes, t, test_rows, min_sep_s, min_sources)
    g = fs["rows"]
    info = {"gate_rows": int(len(g)), "gate_markets": int(pd.unique(codes[g]).size), "test_rows": int(len(test_rows)),
            "min_sep_h": min_sep_s / 3600.0, "min_sources": min_sources,
            "mean_sources": float(fs["n_src"].mean()) if len(g) else None,
            "design": "far-future control target (forward sources); max(CR1, jackknife) p, t(G-1)"}
    if info["gate_rows"] < min_rows or info["gate_markets"] < min_markets:
        return {**info, "testable": False, "passes": False, "p_gate": 1.0,
                "reason": f"gate floor: < {min_rows} rows or < {min_markets} markets"}
    ev = codes if ev_all is None else np.asarray(ev_all)
    x, m = np.asarray(x_all, float)[g], np.asarray(mod_all, float)[g]
    C = np.asarray(C_all, float)[g]
    C = C.reshape(len(g), -1) if C.size else np.empty((len(g), 0))
    fit = _FixedXSlope(codes[g], np.asarray(t, float)[g], [x * m, x, m, *C.T], ev[g])
    y = np.asarray(y_all, float)[g]
    yf = source_mean(fs, y_all)
    return _gate_result(info, fit.stat(y), fit.stat(yf), fit.stat(y - yf, jack=True), fit.n_ev)


def _gain(y: np.ndarray, pb: np.ndarray, pa: np.ndarray) -> np.ndarray:
    """Per-row squared-error gain; linear in y: 2 y (pa - pb) + pb^2 - pa^2."""
    return (y - pb) ** 2 - (y - pa) ** 2


def contrast_gate(codes, t, ss_all, test_rows, y_all, chg_all, A_all, coef: dict, base: dict, *, ev_all=None,
                  min_sep_s: float = GATE["E014"]["min_sep_s"], min_sources: int = GATE["E014"]["min_sources"],
                  min_rows_regime: int = GATE["E014"]["min_rows_regime"]) -> dict:
    """E014 timing gate (far-future control target): per gate row, d = gain(real 2 h target) - gain(mean target of
    the row's sources: same market and regime, origin >= 3 h later), both with the row's own frozen predictions
    (the gain is linear in y, so this equals the mean of the sources' gains); statistic = mean_A d - mean_B d,
    one-sided p = the larger of the CR1 and jackknife p (event clusters), each under Student t with G - 1 df."""
    codes = np.asarray(codes)
    A_all = np.asarray(A_all, float)
    grp = pd.Series(codes).astype(str).to_numpy() + "|" + A_all.astype(int).astype(str)
    fs = forward_sources(grp, t, test_rows, min_sep_s, min_sources)
    g = fs["rows"]
    A = A_all[g] == 1
    info = {"gate_rows": int(len(g)), "gate_rows_A": int(A.sum()), "gate_rows_B": int((~A).sum()),
            "gate_markets": int(pd.unique(codes[g]).size), "test_rows": int(len(test_rows)),
            "min_sep_h": min_sep_s / 3600.0, "min_sources": min_sources,
            "mean_sources": float(fs["n_src"].mean()) if len(g) else None,
            "design": "far-future control target (forward sources, same regime); max(CR1, jackknife) p, t(G-1)"}
    if min(info["gate_rows_A"], info["gate_rows_B"]) < min_rows_regime:
        return {**info, "testable": False, "passes": False, "p_gate": 1.0,
                "reason": f"gate floor: < {min_rows_regime} rows in a regime"}
    chg, ss = np.asarray(chg_all, float)[g], np.asarray(ss_all, float)[g]
    pb = base["intercept"] + base["chg_1h"] * chg
    pa = coef["intercept"] + coef["chg_1h"] * chg + coef["signed_share"] * ss
    evc, ev_u = pd.factorize((codes if ev_all is None else np.asarray(ev_all))[g])
    rx = A.astype(float) - A.mean()
    y = np.asarray(y_all, float)[g]
    yf = source_mean(fs, y_all)

    jk = _ClusterJack(np.column_stack([np.ones(len(g)), A.astype(float)]), evc, len(ev_u))

    def stat(v: np.ndarray) -> tuple[float, float, float]:
        mA, mB = float(v[A].mean()), float(v[~A].mean())
        return _cluster_t(mA - mB, rx, v - np.where(A, mA, mB), evc, len(ev_u)), mA - mB, jk.t(v, 1)

    gr, gf = _gain(y, pb, pa), _gain(yf, pb, pa)
    return _gate_result(info, stat(gr), stat(gf), stat(gr - gf), len(ev_u))


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


def verdict(name: str, r: dict, placebo: dict | None, available: bool, holm_p: float | None) -> dict:
    if not available:
        return {"verdict": "Unavailable", "p_for_holm": 1.0}
    if not r.get("testable"):
        return {"verdict": "Unavailable (untestable)", "p_for_holm": 1.0}
    if placebo is not None and "gate" in placebo:
        g = placebo["gate"]
        status = "OK" if g.get("passes") else "GATE: within-market timing not shown (p_gate >= 0.05 or gate untestable)"
    else:
        status = (placebo or {}).get("reading", {}).get("family_status", "OK")
    if r.get("ci95_cons") is not None:
        lo_ci, hi_ci = r["ci95_cons"]
    else:
        ci = r.get("ci_event_boot") or [None, None]
        lo_ci = min(v for v in (ci[0], r["beta"] - bd.Z95 * r["se"]) if v is not None)
        hi_ci = max(v for v in (ci[1], r["beta"] + bd.Z95 * r["se"]) if v is not None)
    out = {"ci95_cons": [lo_ci, hi_ci], "family_status": status}
    if status.startswith("VOID"):
        return {**out, "verdict": "Void (placebo range excludes 0)", "p_for_holm": 1.0}
    if status.startswith("PLACEBO BIAS"):
        return {**out, "verdict": "Inconclusive (placebo bias)", "p_for_holm": 1.0}
    if status.startswith("GATE"):
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


def check_slope_label(primary_beta: float | None, chk: dict | None, label: str, need_ci: bool = False) -> str | None:
    """Declared mechanism-label rule (E012 6 h skip slot, E013 flow window ending 30 min early): the check passes only
    if it is testable, its slope is > 0 and >= LABEL_FRACTION x the primary slope, and its one-sided primary-rule p
    is < 0.05; with ``need_ci`` (E012) its conservative 95% CI must also lie above 0. Otherwise returns ``label``
    (for E013 this is the definition of the lagged check being "null")."""
    chk = chk or {}
    ok = bool(chk.get("testable") and primary_beta is not None and chk.get("beta") is not None and chk["beta"] > 0
              and chk["beta"] >= LABEL_FRACTION * primary_beta and (chk.get("p") if chk.get("p") is not None else 1.0) < 0.05)
    if ok and need_ci:
        ci = chk.get("ci95_cons")
        ok = ci is not None and ci[0] is not None and ci[0] > 0
    return None if ok else label


E012_LABEL = "possibly bounce (quote noise); mechanical not excluded"
E013_LABEL = "flow-quote continuation moderation, possibly mechanical"


def e012_label(v: dict, skip: dict | None, primary_beta: float | None = None) -> dict:
    """A Supported E012 carries E012_LABEL unless the 6 h skip-slot check passes (``check_slope_label``)."""
    if not str(v.get("verdict", "")).startswith("Supported"):
        return v
    lab = check_slope_label(primary_beta, skip, E012_LABEL, need_ci=True)
    return {**v, "verdict": v["verdict"] + "; " + lab} if lab else v


def with_labels(v: dict, labels: list[str]) -> dict:
    """Disclosure labels (attrition, truncation, code check) are attached to every non-Unavailable verdict."""
    labels = [x for x in labels if x]
    if not labels or str(v.get("verdict", "")).startswith("Unavailable"):
        return v
    return {**v, "verdict": v["verdict"] + "; " + "; ".join(labels), "labels": labels}


# --- attrition (challenger R1 finding 3) -----------------------------------------------------------------------------


def attrition_summary(status, groups, pair: tuple[str, str]) -> dict:
    """Unavailable share by group among rows whose target capture exists (missing captures and pending excluded
    by the caller). ``triggered`` if |share_0 - share_1| > ATTRITION_PP."""
    s = pd.Series(np.asarray(status, object)).astype(str)
    g = np.asarray(groups, object)
    out: dict = {"rule": f"|unavailable share {pair[0]} - {pair[1]}| > {ATTRITION_PP:.2f}: labelled and bounded"}
    shares = {}
    for lab in pair:
        m = g == lab
        sub = s[m]
        un = sub.str.startswith("unavailable")
        shares[lab] = float(un.mean()) if len(sub) else None
        out[lab] = {"rows": int(len(sub)), "unavailable": int(un.sum()),
                    "by_reason": {str(k): int(v) for k, v in sub[un].value_counts().items()}}
    diff = None if None in shares.values() else shares[pair[0]] - shares[pair[1]]
    out.update(share=shares, diff=diff, triggered=bool(diff is not None and abs(diff) > ATTRITION_PP))
    return out


def pessimistic_refit(frame: pd.DataFrame, y: np.ndarray, avail: np.ndarray, term: str, controls: list[str],
                      order: str, cluster: str, seed: int) -> dict:
    """Declared pessimistic imputation for a slope (E012, E013): every unavailable row gets
    y = -sign(raw tested term) x the 95th percentile of the observed |y|, then the primary estimator is refit."""
    q = float(np.nanquantile(np.abs(y[avail]), 0.95)) if avail.any() else float("nan")
    yi = np.where(avail, y, -np.sign(frame[term].to_numpy(float)) * q)
    r = demeaned_fit(frame, yi, term, controls, order, seed=seed, n_boot=200, cluster=cluster)
    return {"q95_abs_y": q, "imputed_rows": int((~avail).sum()), "beta": r.get("beta"), "p": r.get("p"),
            "testable": bool(r.get("testable"))}


def _attrition_label(att: dict, bound_beta: float | None) -> str | None:
    if not att.get("triggered"):
        return None
    lab = f"differential attrition ({att['diff'] * 100:+.1f} pp)"
    if bound_beta is None or not np.isfinite(bound_beta) or bound_beta <= 0:
        lab += ", attrition-sensitive (pessimistic bound <= 0)"
    return lab


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


def econ_summary(pnl: np.ndarray, ev: np.ndarray, day: np.ndarray, seed: int, descriptive: bool = False) -> dict:
    """Declared economics test (counted, battery2 KIND_RULES 'live_tests2'), or, with ``descriptive``, the mean and
    counts only (no p-value, not counted)."""
    ok = np.isfinite(pnl)
    n, ne = int(ok.sum()), int(pd.unique(ev[ok]).size) if ok.any() else 0
    if descriptive:
        return {"trades": n, "events": ne, "mean": float(pnl[ok].mean()) if n else None,
                "note": "descriptive companion: mean only, no test"}
    if n < economics.MIN_TRADES or ne < economics.MIN_CLUSTERS:
        return {"trades": n, "events": ne, "verdict": "not shown (below 30 trades / 10 events)"}
    r = battery.mean_test(pnl[ok], ev[ok], day[ok], sign=+1, n_boot=N_BOOT, seed=seed)
    covers = r["mean"] > 0 and r["p"] < 0.05
    return {**bd._clean(r), "trades": n, "events": ne,
            "verdict": "covers taker costs (paper)" if covers else "not shown"}


# --- per-experiment analyses ----------------------------------------------------------------------------------------


def e012(root: Path, start: float, end: float, roles: tuple[str, ...], spec: dict, placebo_draws: int) -> dict:
    df, load_acc = _load_pairs(root, "e012", start, end, roles, spec)
    if df.empty:
        return {"available": False, "reason": "no lines", "accounting": load_acc}
    if "status_j" not in df:
        df["status_j"] = np.nan
    acc = {"lines": len(df), "pending": int(df["status_j"].isna().sum()), **load_acc}
    df = df[df["status_j"].notna()].copy()
    df["late"] = _late(df, "j")
    un = _unavail(df["status_j"])
    acc.update(late=int(df["late"].sum()), missing_capture=int((df["status_j"] == "missing_capture").sum()),
               unavailable=int(un.sum()),
               unavailable_by_reason={str(k): int(v) for k, v in df.loc[un, "status_j"].value_counts().items()},
               h_not_tight=int((df["tight_h"] != 1).sum()))
    base = df[(~df["late"]) & (df["status_j"] != "missing_capture") & (df["tight_h"] == 1)
              & np.isfinite(df["x"])].reset_index(drop=True)
    base["day"] = _day(base["capture_t"])
    base["tblock"] = _tblock(base["capture_t"], start)
    base["dprev0"] = base["dprev"].fillna(0.0)
    base["ix"] = base["x"] * base["zL"]
    avail = (base["status_j"] == "evaluated").to_numpy()
    ybase = _mid(base, "j") - base["mid_i"].to_numpy(float)
    att = attrition_summary(base["status_j"], np.where(base["L"].to_numpy(float) == 0, "L0", "Lpos"), ("L0", "Lpos"))
    df = base[avail].reset_index(drop=True)
    y = ybase[avail]
    seed = SEEDS["E012"]
    ctl = ["x", "zL", *CONTROLS_E012]
    r = demeaned_fit(df, y, "ix", ctl, "capture_t", seed=seed, cluster="tblock")
    fl = FLOORS["E012"]
    used = df[r["_mask"]] if r.get("testable") else df.iloc[0:0]
    available = (len(used) >= fl["rows"] and used["event_id"].nunique() >= fl["events"]
                 and used["day"].nunique() >= fl["days"])
    out = {"accounting": acc, "primary": _strip(r), "available": bool(available),
           "rows": len(used), "events": int(used["event_id"].nunique()), "days": int(used["day"].nunique())}
    if att["triggered"] and r.get("testable"):
        att["pessimistic"] = pessimistic_refit(base, ybase, avail, "ix", ctl, "capture_t", "tblock", seed + 9)
    out["attrition"] = att
    out["labels"] = [_attrition_label(att, (att.get("pessimistic") or {}).get("beta"))]
    if r.get("testable"):
        Xd = bd.expanding_demean(df[["market_id", "capture_t", "ix", *ctl]], ["ix", *ctl], "market_id", "capture_t")
        m = r["_mask"]
        out["lodo"] = bd._clean(bd.lodo(y[m], Xd["ix"].to_numpy()[m], Xd[ctl].to_numpy()[m], df["day"].to_numpy()[m],
                                        r["beta"]))
        out["placebo"] = e012_placebo(root, df, y, r, placebo_draws, seed + 100)
        sens = {}
        sens["pooled"] = _strip(demeaned_fit(df, y, "ix", ctl, "capture_t", estimator="pooled", seed=seed, n_boot=200,
                                             cluster="tblock"))
        sens["fe_within"] = _strip(demeaned_fit(df, y, "ix", ctl, "capture_t", estimator="fe", seed=seed, n_boot=200,
                                                cluster="tblock"))
        jt = df["tight_j"] == 1
        sens["j_tight"] = _strip(demeaned_fit(df[jt].reset_index(drop=True), y[jt.to_numpy()], "ix", ctl, "capture_t",
                                              seed=seed, n_boot=200, cluster="tblock"))
        big = df.groupby("market_id")["market_id"].transform("size") >= 20
        sens["markets_ge_20_rows"] = _strip(demeaned_fit(df[big].reset_index(drop=True), y[big.to_numpy()], "ix", ctl,
                                                         "capture_t", seed=seed, n_boot=200, cluster="tblock"))
        g = df.copy()
        g["ixg"] = g["chg_1d_g"] * g["zL"]
        sens["gamma_chg_1d"] = _strip(demeaned_fit(g, y, "ixg", ["chg_1d_g", "chg_1d_missing", "zL", *CONTROLS_E012],
                                                   "capture_t", seed=seed, n_boot=200, cluster="tblock"))
        sens["utc_day_clusters"] = _strip(demeaned_fit(df, y, "ix", ctl, "capture_t", seed=seed, n_boot=200,
                                                       cluster="day"))
        out["sensitivities"] = bd._clean(sens)
        # declared 6 h skip-slot check (mechanism label; challenger R1 finding 2): x_skip6 = mid_{i-3} - mid_h never
        # contains mid_i, so the bid/ask bounce at i that the target shares with x is absent from the tested term
        if "x_skip6" in df:
            skm = ((df["tight_s3"] == 1) & np.isfinite(df["x_skip6"])).to_numpy()
            sk = df[skm].reset_index(drop=True)
            sk["ix_skip"] = sk["x_skip6"] * sk["zL"]
            rs = demeaned_fit(sk, y[skm], "ix_skip", ["x_skip6", "zL", *CONTROLS_SKIP], "capture_t", seed=seed,
                              n_boot=N_BOOT, cluster="tblock")
        else:
            rs = {"testable": False, "reason": "x_skip6 not in the frozen lines"}
        out["skip_slot_6h"] = _strip(rs)
        fire = (df["L"] == 0) & (df["x"].abs() >= spec["e012"]["econ"]["min_abs_x"])
        f = df[fire.to_numpy()]
        pnl = paper_taker(f, -np.sign(f["x"].to_numpy(float)), "j")
        out["economics"] = econ_summary(pnl, f["event_id"].to_numpy(), f["day"].to_numpy(), seed + 7)
        top = (df["L"] >= spec["e012"]["econ"]["liquid_cut"]) & (df["x"].abs() >= spec["e012"]["econ"]["min_abs_x"])
        t = df[top.to_numpy()]
        out["economics_descriptive_follow_liquid"] = econ_summary(
            paper_taker(t, np.sign(t["x"].to_numpy(float)), "j"), t["event_id"].to_numpy(), t["day"].to_numpy(),
            seed + 8, descriptive=True)
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
        r = demeaned_fit(p, mj - mi, "ix", ["x", "zL", *CONTROLS_E012], "capture_t", seed=seed, n_boot=20,
                         cluster="tblock")
        if r.get("testable"):
            betas.append(r["beta"])
            ses.append(r["se"])
            ns.append(r["n"])
    return _read_rule(real, betas, ses, ns, "E012")


def _col(df: pd.DataFrame, c: str, fill=np.nan) -> np.ndarray:
    return df[c].to_numpy(float) if c in df else np.full(len(df), fill, float)


def flow(root: Path, start: float, end: float, roles: tuple[str, ...], spec: dict) -> dict:
    df, load_acc = _load_pairs(root, "flow", start, end, roles, spec)
    if df.empty:
        return {"E013_F4": {"available": False, "reason": "no lines"}, "E013_F5": {"available": False},
                "E014": {"available": False, "reason": "no lines"}}
    df = df.reset_index(drop=True)
    for c in ("status_j2", "status_j6"):
        df[c] = df[c].fillna("pending") if c in df else "pending"
    for c in ("bid_j2", "ask_j2", "bid_j6", "ask_j6", "cap_start_j2", "cap_start_j6", "tight_j6"):
        if c not in df:
            df[c] = np.nan
    df["day"] = _day(df["capture_t"])
    df["dprev0"] = df["dprev"].fillna(0.0)
    codes_all = pd.factorize(df["market_id"])[0]
    ev_all = pd.factorize(df["event_id"])[0]
    t_all = df["t_row"].to_numpy(float)
    out = {}
    # --- E013 (F4, F5): late is judged against the 6 h target only, so rows whose 2 h target had started stay in
    late6 = _late(df, "j6")
    n6 = df["n6"].to_numpy(float)
    cov6 = df["cov6"].to_numpy(float) == 1
    x6 = df["x6"].to_numpy(float)
    cap = spec["flow"].get("vol24_cap")
    vol = _col(df, "vol24_i")
    with np.errstate(invalid="ignore"):
        in_cap = np.ones(len(df), bool) if cap is None else (np.isfinite(vol) & (vol <= float(cap)))
    origin6 = (df["tight_i"].to_numpy() == 1) & (df["end_ok_6h"].to_numpy() == 1) & in_cap
    src6 = origin6 & (np.nan_to_num(n6) > 0) & np.isfinite(x6)  # the origin-side population
    cand = origin6 & ((~cov6) | (np.nan_to_num(n6) > 0))
    trunc_share = float(((~cov6) & cand).sum() / cand.sum()) if cand.any() else None
    post = _col(df, "n_post_origin")
    st6 = df["status_j6"].astype(str)
    acc = {"lines": len(df), **load_acc, "late": int(late6.sum()),
           "status_j6": {k: int(v) for k, v in st6.value_counts().items()},
           "not_tight": int((df["tight_i"] != 1).sum()), "end_within_7h": int((df["end_ok_6h"] != 1).sum()),
           "vol24_cap": cap, "above_vol24_cap": int((~in_cap).sum()),
           "vol24_cap_note": None if cap is not None else "DRAFT: vol24_cap not filled, no population cut applied",
           "flow_window_truncated": int((~cov6).sum()), "flow_window_no_trades": int((n6 == 0).sum()),
           "residual_trunc6": {"candidates": int(cand.sum()), "truncated": int(((~cov6) & cand).sum()),
                               "share": trunc_share, "label_above": spec["flow"]["trunc_label_share"]},
           "post_origin_trades_on_page": {
               "rows_with_any": int(np.nansum(post > 0)), "trades_total": float(np.nansum(post)),
               "truncated_rows_with_any": int(np.nansum((post > 0) & ~cov6)),
               "note": "counts only; post-origin trades never enter a feature but fill the 500-trade page"}}
    trunc_label = (f"truncation-sensitive (residual 6 h-window truncation {trunc_share * 100:.1f}%)"
                   if trunc_share is not None and trunc_share > spec["flow"]["trunc_label_share"] else None)
    y6_all = _mid(df, "j6") - df["mid_i"].to_numpy(float)
    C_all = df[CONTROLS_FLOW].to_numpy(float)
    lrv_all = np.log(_col(df, "rv") + 1e-4)
    spr_all = _col(df, "spread_i")
    for name, mod, cutkey, gvals, gcuts in (
            ("E013_F4", "zRV", "lrv_upper_tercile_cut", lrv_all, spec["census"]["lrv_tercile_cuts"]),
            ("E013_F5", "zSPR", "spr_upper_tercile_cut", spr_all, spec["census"]["spr_tercile_cuts"])):
        modv = df[mod].to_numpy(float)
        popn = src6 & np.isfinite(modv) & ~late6 & ~st6.isin(["missing_capture", "pending"]).to_numpy()
        test = popn & (st6 == "evaluated").to_numpy()
        dd = df[test].reset_index(drop=True)
        yy = y6_all[test]
        dd["ix"] = dd["x6"] * dd[mod]
        seed = SEEDS[name]
        ctl = ["x6", mod, *CONTROLS_FLOW]
        r = demeaned_fit(dd, yy, "ix", ctl, "t_row", seed=seed, cluster="day")
        fl = FLOORS["E013"]
        used = dd[r["_mask"]] if r.get("testable") else dd.iloc[0:0]
        res = {"accounting": acc, "primary": _strip(r), "rows": len(used), "events": int(used["event_id"].nunique()),
               "days": int(used["day"].nunique())}
        res["available"] = bool(res["rows"] >= fl["rows"] and res["events"] >= fl["events"]
                                and res["days"] >= fl["days"])
        with np.errstate(invalid="ignore"):
            grp = np.where(gvals >= gcuts[1] - 1e-12, "upper", np.where(gvals <= gcuts[0] + 1e-12, "lower", "middle"))
        att = attrition_summary(st6[popn], grp[popn], ("upper", "lower"))
        labels = [trunc_label]
        if r.get("testable"):
            base = df[popn].reset_index(drop=True)
            base["ix"] = base["x6"] * base[mod]
            if att["triggered"]:
                att["pessimistic"] = pessimistic_refit(base, y6_all[popn], (st6[popn] == "evaluated").to_numpy(), "ix",
                                                       ctl, "t_row", "day", seed + 9)
            labels.append(_attrition_label(att, (att.get("pessimistic") or {}).get("beta")))
            gate = slope_gate(codes_all, t_all, x6, np.flatnonzero(test), y6_all, modv, C_all, ev_all=ev_all)
            res["placebo"] = {"gate": gate}
            sens = {"pooled": _strip(demeaned_fit(dd, yy, "ix", ctl, "t_row", estimator="pooled", seed=seed,
                                                  n_boot=200)),
                    "fe_within": _strip(demeaned_fit(dd, yy, "ix", ctl, "t_row", estimator="fe", seed=seed,
                                                     n_boot=200)),
                    "weighted": _strip(demeaned_fit(dd, yy, "ix", ctl, "t_row", seed=seed, n_boot=200,
                                                    w=1.0 / dd["p_incl"].to_numpy(float)))}
            lgm = np.isfinite(dd["x6_lag30"]).to_numpy()
            lg = dd[lgm].reset_index(drop=True)
            lg["ixl"] = lg["x6_lag30"] * lg[mod]
            sens["flow_ends_30min_early"] = _strip(demeaned_fit(lg, yy[lgm], "ixl", ["x6_lag30", mod, *CONTROLS_FLOW],
                                                                "t_row", seed=seed, n_boot=200))
            jt = (dd["tight_j6"] == 1).to_numpy()
            sens["j6_tight"] = _strip(demeaned_fit(dd[jt].reset_index(drop=True), yy[jt], "ix", ctl, "t_row",
                                                   seed=seed, n_boot=200))
            res["sensitivities"] = bd._clean(sens)
            res["mechanism_check"] = {"secondary": "flow_ends_30min_early",
                                      "label_if_null": E013_LABEL, "fraction": LABEL_FRACTION}
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
        res["attrition"] = att
        res["labels"] = labels
        out[name] = res
    # --- E014
    late2 = _late(df, "j2")
    ss_all = df["ss"].to_numpy(float)
    reg = df["regime"].astype(str).to_numpy()
    tight_i = df["tight_i"].to_numpy() == 1
    src14 = tight_i & np.isfinite(ss_all) & (ss_all != 0)
    tr1 = _col(df, "trunc1h")
    st2 = df["status_j2"].astype(str)
    fr = df[src14]
    trunc14 = {}
    for lab in ("A", "B"):
        m = tight_i & (reg == lab) & ((tr1 == 1) | src14)
        trunc14[lab] = {"rows": int(m.sum()), "truncated": int((m & (tr1 == 1)).sum()),
                        "share": float((m & (tr1 == 1)).sum() / m.sum()) if m.any() else None}
    acc14 = {"lines": len(df), **load_acc, "late": int(late2.sum()),
             "status_j2": {k: int(v) for k, v in st2.value_counts().items()},
             "regime_counts_flow_rows": fr["regime"].value_counts().to_dict(),
             "status_j2_by_regime_flow_rows": {str(k): {str(c): int(v) for c, v in row.items() if v}
                                               for k, row in pd.crosstab(fr["regime"], fr["status_j2"]).iterrows()},
             "trunc1h_by_regime": trunc14, "trunc1h_unknown": int(np.isnan(tr1).sum()),
             "label_above": spec["e014"]["trunc_label_share"]}
    tl = [f"{k} {v['share'] * 100:.1f}%" for k, v in trunc14.items()
          if v["share"] is not None and v["share"] > spec["e014"]["trunc_label_share"]]
    popn14 = src14 & np.isin(reg, ["A", "B"]) & ~late2 & ~st2.isin(["missing_capture", "pending"]).to_numpy()
    test14 = popn14 & (st2 == "evaluated").to_numpy()
    e = df[test14].reset_index(drop=True)
    y2_all = _mid(df, "j2") - df["mid_i"].to_numpy(float)
    gate_ctx = {"codes": codes_all, "ev": ev_all, "t": t_all, "ss": ss_all, "rows": np.flatnonzero(test14),
                "y": y2_all, "chg": df["chg_1h"].to_numpy(float), "A": (reg == "A").astype(float)}
    res14 = e014_tests(e, acc14, spec, gate_ctx=gate_ctx)
    att14 = attrition_summary(st2[popn14], reg[popn14], ("A", "B"))
    if att14["triggered"]:
        att14["bounds"] = e014_attrition_bounds(df[popn14].reset_index(drop=True), y2_all[popn14],
                                                (st2[popn14] == "evaluated").to_numpy())
    res14["attrition"] = att14
    res14["labels"] = [("truncation-sensitive (1 h window truncated: " + ", ".join(tl) + ")") if tl else None,
                       _attrition_label(att14, (att14.get("bounds") or {}).get("pessimistic_contrast"))]
    out["E014"] = res14
    return out


def e014_attrition_bounds(b: pd.DataFrame, y: np.ndarray, avail: np.ndarray) -> dict:
    """Declared bounds of the E014 contrast under differential attrition: (i) pessimistic: unavailable A rows get the
    5th percentile of the observed A gains, unavailable B rows the 95th percentile of the observed B gains; (ii) worst
    case (Manski): each unavailable row's gain at the end of its feasible target range y in [-mid_i, 1 - mid_i]
    least favourable to A - B (the gain is linear in y)."""
    A = (b["regime"].astype(str) == "A").to_numpy()
    pb, pa = b["p_base"].to_numpy(float), b["p_aug"].to_numpy(float)
    g = _gain(y, pb, pa)
    if not (avail & A).any() or not (avail & ~A).any():
        return {"pessimistic_contrast": None, "worst_case_contrast": None}
    qa, qb = float(np.quantile(g[avail & A], 0.05)), float(np.quantile(g[avail & ~A], 0.95))
    gp = np.where(avail, g, np.where(A, qa, qb))
    mid = b["mid_i"].to_numpy(float)
    g_lo, g_hi = _gain(-mid, pb, pa), _gain(1.0 - mid, pb, pa)
    gw = np.where(avail, g, np.where(A, np.minimum(g_lo, g_hi), np.maximum(g_lo, g_hi)))
    return {"pessimistic_contrast": float(gp[A].mean() - gp[~A].mean()),
            "worst_case_contrast": float(gw[A].mean() - gw[~A].mean()), "q05_A": qa, "q95_B": qb,
            "imputed_A": int((~avail & A).sum()), "imputed_B": int((~avail & ~A).sum())}


def e014_tests(e: pd.DataFrame, acc: dict, spec: dict, gate_ctx: dict | None = None) -> dict:
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
        p_primary(r)
    fl = FLOORS["E014"]
    nA, nB = int(A.sum()), int((1 - A).sum())
    evA, evB = int(pd.unique(ev[A == 1]).size), int(pd.unique(ev[A == 0]).size)
    res.update(primary=bd._clean(r), rows_A=nA, rows_B=nB, events_A=evA, events_B=evB, days=int(pd.unique(day).size),
               mean_gain_A=float(g[A == 1].mean()) if nA else None, mean_gain_B=float(g[A == 0].mean()) if nB else None)
    res["available"] = bool(min(nA, nB) >= fl["rows_regime"] and min(evA, evB) >= fl["events_regime"]
                            and res["days"] >= fl["days"])
    if not r.get("testable"):
        return res
    if gate_ctx is None:  # direct use (unit tests): the rows themselves are the source pool
        gate_ctx = {"codes": pd.factorize(e["market_id"])[0], "ev": pd.factorize(e["event_id"])[0],
                    "t": e["t_row"].to_numpy(float),
                    "ss": e["ss"].to_numpy(float), "rows": np.arange(len(e)),
                    "y": y, "chg": e["chg_1h"].to_numpy(float), "A": A}
    res["placebo"] = {"gate": contrast_gate(gate_ctx["codes"], gate_ctx["t"], gate_ctx["ss"],
                                            gate_ctx["rows"], gate_ctx["y"], gate_ctx["chg"], gate_ctx["A"],
                                            spec["e014"]["augmented"], spec["e014"]["base"], ev_all=gate_ctx["ev"])}
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
    # declared mechanism reading (challenger R1 finding 8): the gain contrast mixes 2c ss y and c^2 ss^2 terms; the
    # slope contrast (residual on ss, A, ss x A) is the reading of "the flow slope is larger near the end"
    sc = sens["slope_contrast"]
    res["mechanism_reading"] = {"secondary": "slope_contrast", "beta_ssxA": sc.get("beta"), "p": sc.get("p"),
                                "note": "descriptive; never changes the verdict"}
    ec = spec["e014"]["econ"]
    fire = (A == 1) & (np.abs(ss) >= ec["abs_ss"]) & (e["n_trades_1h"].to_numpy(float) >= ec["min_trades_1h"])
    f = e[fire]
    res["economics"] = econ_summary(paper_taker(f, np.sign(f["ss"].to_numpy(float)), "j2"), f["event_id"].to_numpy(),
                                    f["day"].to_numpy(), seed + 7)
    return res


TRIAL_KIND = "live_tests2"


def trial_record(res: dict) -> dict:
    """The single counted trials line (battery2 KIND_RULES 'live_tests2', rule n_tests): 4 primaries + the 4
    declared economics tests = 8 (precedent: economics lines are counted). Descriptive companions, sensitivities,
    labels, the E012 skip-slot check, the E013 lag check, the E012 placebo and the E013/E014 timing gates are
    verdict conditions, not counted tests."""
    econ = {k: (res.get(k) or {}).get("economics", {}).get("p") for k in ("E012", "E013_F4", "E013_F5", "E014")}
    return {"kind": TRIAL_KIND, "label": "PROSPECTIVE", "evidence_role": lt.ROLE_CONF, "experiments": ["E012", "E013", "E014"],
            "n_tests": 8, "n_primary": 4, "n_economics": 4, "holm": res.get("holm"),
            "verdicts": {k: (res.get(k) or {}).get("verdict") for k in ("E012", "E013_F4", "E013_F5", "E014")},
            "economics_p": econ, "spec_sha256": res.get("spec_sha"), "code_sha256": res.get("code_sha256"),
            "window": res.get("window")}


def analyze(root: Path = lt.OUT_ROOT, *, start_utc: str = lt.REGISTERED_UTC, end_utc: str = lt.END_UTC,
            spec: dict | None = None, roles: tuple[str, ...] = (lt.ROLE_CONF,), placebo_draws: int = PLACEBO_DRAWS,
            force: bool = False) -> dict:
    """The single registered analysis. Refuses before ANALYSIS_NOT_BEFORE unless ``force`` (tests only), and refuses
    a pinned spec whose code hashes do not match the modules on disk."""
    if not force and lt.now_ts() < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise RuntimeError(f"analysis refused before {lt.ANALYSIS_NOT_BEFORE}")
    spec = spec or lt.load_spec()
    cc = code_check(spec)
    s, e = lt.epoch(start_utc), lt.epoch(end_utc)
    res = {"E012": e012(root, s, e, roles, spec, placebo_draws)}
    res.update(flow(root, s, e, roles, spec))
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
    res["E012"]["verdict"] = e012_label(res["E012"]["verdict"], res["E012"].get("skip_slot_6h"),
                                        (res["E012"].get("primary") or {}).get("beta"))
    for k in ("E013_F4", "E013_F5"):
        v = res[k]["verdict"]
        if str(v.get("verdict", "")).startswith("Supported"):
            lag = (res[k].get("sensitivities") or {}).get("flow_ends_30min_early")
            lab = check_slope_label((res[k].get("primary") or {}).get("beta"), lag, E013_LABEL)
            if lab:
                res[k]["verdict"] = {**v, "verdict": v["verdict"] + "; " + lab}
    for k in pv:
        res[k]["verdict"] = with_labels(res[k]["verdict"], [*(res[k].get("labels") or []), cc["label"]])
    res["holm"] = {"m": 4, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True}
    res["spec_sha"] = spec["_sha256"]
    res["code_sha256"] = cc["current"]
    res["code_check"] = cc
    res["window"] = [start_utc, end_utc]
    res["roles"] = list(roles)
    return bd._clean(res) if isinstance(res, dict) else res
