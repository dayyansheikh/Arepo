# ruff: noqa: E501
"""CB5-K: hour-of-day moderation of the Kalshi lead (CH58), docs/research_lab/CREATIVE_BATCH_5.md section CB5-K and 4.1.

``K1 = [A_O(10) + A_O(20)] - [A_R(10) + A_R(20)]`` with ``A_b(L) = r(dK_t, dP_{t+L}) - r(dP_t, dK_{t+L})`` pooled over the
10-minute steps of New York hour bucket ``b`` (R = [09:30, 23:00), O = [23:00, 09:30); the bucket is that of the grid time ``t`` of
the first mover). Inference by event-cluster and UTC-date-cluster bootstraps on per-step sufficient statistics. Controls
(activity-matched, within-pair), the pseudo-split size calibration, the reported +12h contrast and the census counts are here.

No P&L, no fetch. ``cross_venue_live/`` is refused unless a committed K1-R spec and a sign-off file exist. The C1 pair set is
rebuilt from ``scripts/run_cross_venue.py`` (``load_pair_series`` and ``audit_sets``) by :func:`c1_pairs`; every statistic takes
neutral :class:`KPair` inputs so it can be tested on fixtures.
"""

from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import cross_venue as cv
from . import provenance

ET = ZoneInfo("America/New_York")
LAGS = (1, 2)  # steps of 10 minutes: 10 and 20 minutes
R_START_MIN, R_END_MIN = 9 * 60 + 30, 23 * 60
K1_FLOOR = 0.10
N_BOOT, SEED_BOOT = 4000, 5163
PSEUDO_DRAWS, SEED_PSEUDO = 200, 5164
PSEUDO_MAX_REJECT = 0.065
P_TWO_SIDED = 0.05
MIN_PAIR_STEPS = 30
G_NORMAL, G_MIN = 30, 15
ACT_DECILES, ACT_TERCILES = 10, 3
HALF_SPREAD_J4 = 0.10
J4_MID = (0.02, 0.98)
J4_DIFF_LABEL = 0.02
T_J4R = "2026-10-20T03:00:00Z"
C1_EXPECTED = (316, 183)
SE20_C1 = 0.036
LIVE_ROOT_NAME = "cross_venue_live"
K1R_SPEC = provenance.REPO_ROOT / "docs" / "research_lab" / "queue" / "jobs" / "q0114_cb5_K_rep_live.json"
K1R_SIGNOFF = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb5_k1r_signoff.json"
K1R_NOT_BEFORE = "2026-11-03"
CV_SCRIPT = provenance.REPO_ROOT / "backend" / "scripts" / "run_cross_venue.py"
CV_ROOT = provenance.REPO_ROOT / "data-dumps" / "research_lab" / "cross_venue"


class RefusedPath(RuntimeError):
    """A sealed or reserved data path."""


def refuse_path(path: Path | str, *, now: datetime | None = None, spec: Path | None = None, signoff: Path | None = None) -> None:
    """Refuse any path under ``cross_venue_live/`` unless a committed K1-R spec and the owner sign-off exist and it is on or after
    2026-11-03 (E009/E010 unseal)."""
    if LIVE_ROOT_NAME not in Path(path).parts and LIVE_ROOT_NAME not in str(path):
        return
    now = now or datetime.now(UTC)
    spec, signoff = Path(spec or K1R_SPEC), Path(signoff or K1R_SIGNOFF)
    if now.strftime("%Y-%m-%d") < K1R_NOT_BEFORE:
        raise RefusedPath(f"{path}: cross_venue_live/ is sealed until {K1R_NOT_BEFORE} (E009/E010)")
    if not spec.exists() or not signoff.exists():
        raise RefusedPath(f"{path}: no committed K1-R spec and E009/E010 owner sign-off")


# ---- buckets and pair inputs -------------------------------------------------------------------------------------------


def buckets_of(t_utc: np.ndarray, shift_s: float = 0.0) -> np.ndarray:
    """1 = O (US overnight [23:00, 09:30)), 0 = R (day and evening [09:30, 23:00)); America/New_York, DST-aware; the epoch
    times are shifted by ``shift_s`` first (the reported +12h contrast)."""
    if not len(t_utc):
        return np.empty(0, dtype=np.int8)
    idx = pd.to_datetime(np.asarray(t_utc, float) + shift_s, unit="s", utc=True).tz_convert(ET)
    mins = idx.hour.to_numpy() * 60 + idx.minute.to_numpy()
    return (~((mins >= R_START_MIN) & (mins < R_END_MIN))).astype(np.int8)


def bucket_of(t_utc: float) -> str:
    return "O" if int(buckets_of(np.array([t_utc]))[0]) else "R"


@dataclass
class KPair:
    pair_id: str
    event: str
    cat: str
    t: np.ndarray
    p: np.ndarray
    k: np.ndarray
    kspr: np.ndarray
    kvol: np.ndarray | None = None

    @property
    def sports(self) -> bool:
        return self.cat.strip().lower() == "sports"

    @property
    def ok(self) -> np.ndarray:
        return cv.usable({"p": self.p, "k": self.k})


def c1_pairs(expected: tuple[int, int] | None = C1_EXPECTED, root: Path | None = None) -> list[KPair]:
    """The audited C1 set: ``run_cross_venue.load_pair_series(POINT_LAG_S)`` minus ``audit_sets(...)['rule']`` (the r1 title/rule
    drops). Asserts the declared counts (316 pairs, 183 events) when ``expected`` is given. Reads ``cross_venue/`` only."""
    root = Path(root) if root is not None else CV_ROOT
    refuse_path(root)
    spec = importlib.util.spec_from_file_location("run_cross_venue_cb5", CV_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.ROOT = root
    pairs, kept = mod.load_pair_series(cv.POINT_LAG_S)
    rule = mod.audit_sets(pairs, kept)["rule"]
    out = []
    for ps, row in zip(pairs, kept, strict=True):
        if row["k_ticker"] in rule:
            continue
        z = np.load(root / "series" / f"{row['k_ticker']}.npz")
        kvol = _grid_volume(z["kc"], ps.g["t"])
        out.append(KPair(ps.pair_id, str(ps.cluster), ps.cat, ps.g["t"], ps.g["p"], ps.g["k"], ps.g["kspr"], kvol))
    assert_c1_counts(out, expected)
    return out


def assert_c1_counts(pairs: list[KPair], expected: tuple[int, int] | None = C1_EXPECTED) -> None:
    """The declared C1 reproduction: 316 pairs and 183 events (skipped when ``expected`` is None)."""
    if expected is not None:
        got = (len(pairs), len({p.event for p in pairs}))
        assert got == tuple(expected), f"C1 reproduction failed: {got} != {tuple(expected)}"


def _grid_volume(kc: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Kalshi candle volume summed over the 10 minutes ending at each grid time (a descriptive activity proxy)."""
    v = np.zeros(len(t))
    if len(kc) and len(t):
        j = np.searchsorted(t, kc[:, 0], side="left")
        m = (j < len(t)) & np.isfinite(kc[:, 4])
        np.add.at(v, j[m], kc[m, 4])
    return v


# ---- per-step sufficient statistics ------------------------------------------------------------------------------------

# columns per step: for lag index li in (0, 1) and direction d in (0 = K->P, 1 = P->K): [xy, xx, yy, n] at base li*8 + d*4
NCOL = 16


@dataclass
class StepTable:
    X: np.ndarray  # (n, 16) per-step contributions
    pair: np.ndarray
    event: np.ndarray
    udate: np.ndarray
    block: np.ndarray
    bucket: np.ndarray
    cell: np.ndarray
    sports: np.ndarray
    kvol: np.ndarray
    kspr: np.ndarray
    pair_ids: list[str]
    def sub(self, m: np.ndarray) -> StepTable:
        return StepTable(self.X[m], self.pair[m], self.event[m], self.udate[m], self.block[m], self.bucket[m], self.cell[m], self.sports[m], self.kvol[m], self.kspr[m], self.pair_ids)


def step_table(pairs: list[KPair], *, shift_s: float = 0.0) -> StepTable:
    """One row per usable grid step ``t`` carrying the demeaned cross-products of ``(x_t, y_{t+L})`` for lags 1 and 2 and both
    directions. ``dK`` and ``dP`` are the 10-minute changes over usable endpoints (study section 5.1); each pair is centred on its
    own mean within the bucket of the first mover (``t``). A step's activity cell is set later (:func:`attach_cells`)."""
    cols = {k: [] for k in ("X", "pair", "event", "udate", "block", "bucket", "sports", "dk_abs", "kspr", "kvol")}
    for pi, ps in enumerate(pairs):
        ok = ps.ok
        n = len(ps.t)
        dp = cv.lagged_diff(ps.p, ok, 1)
        dk = cv.lagged_diff(ps.k, ok, 1)
        bk = buckets_of(ps.t, shift_s)
        X = np.zeros((n, NCOL))
        for li, L in enumerate(LAGS):
            for d, (a, b) in enumerate(((dk, dp), (dp, dk))):
                x = a[: n - L]
                y = b[L:]
                v = np.isfinite(x) & np.isfinite(y)
                base = li * 8 + d * 4
                xv, yv = np.full(n, np.nan), np.full(n, np.nan)
                xv[: n - L], yv[: n - L] = np.where(v, x, np.nan), np.where(v, y, np.nan)
                for bb in (0, 1):
                    m = np.isfinite(xv) & (bk == bb)
                    if m.sum() < 2:
                        continue
                    xc, yc = xv[m] - xv[m].mean(), yv[m] - yv[m].mean()
                    X[m, base], X[m, base + 1], X[m, base + 2], X[m, base + 3] = xc * yc, xc * xc, yc * yc, 1.0
        keep = X[:, 3] + X[:, 7] + X[:, 11] + X[:, 15] > 0
        if not keep.any():
            continue
        t = ps.t[keep]
        ny = pd.to_datetime(t, unit="s", utc=True).tz_convert(ET)
        blk = [f"{pi}|{d}|{h}{'a' if m < 30 else 'b'}" for d, h, m in zip(ny.strftime("%Y-%m-%d"), ny.hour, ny.minute, strict=True)]
        cols["X"].append(X[keep])
        cols["pair"].append(np.full(int(keep.sum()), pi))
        cols["event"].append(np.full(int(keep.sum()), ps.event, dtype=object))
        cols["udate"].append(pd.to_datetime(t, unit="s", utc=True).strftime("%Y-%m-%d").to_numpy().astype(object))
        cols["block"].append(np.array(blk, dtype=object))
        cols["bucket"].append(bk[keep])
        cols["sports"].append(np.full(int(keep.sum()), ps.sports))
        cols["dk_abs"].append(np.abs(np.nan_to_num(dk[keep], nan=0.0)))
        cols["kspr"].append(ps.kspr[keep])
        cols["kvol"].append((ps.kvol if ps.kvol is not None else np.zeros(n))[keep])
    if not cols["X"]:
        return StepTable(np.zeros((0, NCOL)), *(np.array([]) for _ in range(9)), [p.pair_id for p in pairs])
    cat = lambda k: np.concatenate(cols[k])  # noqa: E731
    tbl = StepTable(cat("X"), cat("pair"), cat("event"), cat("udate"), pd.factorize(cat("block"))[0], cat("bucket"), np.zeros(len(cat("pair")), int),
                    cat("sports"), cat("kvol"), cat("kspr"), [p.pair_id for p in pairs])
    tbl.cell = _cells(cat("dk_abs"), cat("kspr"))
    return tbl


def _cells(dk_abs: np.ndarray, kspr: np.ndarray) -> np.ndarray:
    """Joint cell of |dK| decile and Kalshi-spread tercile (declared activity-matching cells)."""
    q1 = np.quantile(dk_abs, np.linspace(0, 1, ACT_DECILES + 1)[1:-1]) if len(dk_abs) else np.array([])
    ks = np.nan_to_num(kspr, nan=0.0)
    q2 = np.quantile(ks, np.linspace(0, 1, ACT_TERCILES + 1)[1:-1]) if len(ks) else np.array([])
    return np.searchsorted(q1, dk_abs, side="right") * ACT_TERCILES + np.searchsorted(q2, ks, side="right")


def primary_mask(t: StepTable) -> np.ndarray:
    return ~t.sports.astype(bool)


def _sum_by(t: StepTable, codes: np.ndarray, ncodes: int, mask: np.ndarray, w: np.ndarray | None = None, bucket_col: np.ndarray | None = None) -> np.ndarray:
    """(ncodes, 32) cluster sums: bucket R columns 0-15, bucket O columns 16-31."""
    bk = t.bucket if bucket_col is None else bucket_col
    out = np.zeros((ncodes, 2 * NCOL))
    ww = np.ones(len(codes)) if w is None else w
    for b in (0, 1):
        m = mask & (bk == b)
        for j in range(NCOL):
            out[:, b * NCOL + j] = np.bincount(codes[m], weights=(t.X[m, j] * ww[m]), minlength=ncodes)
    return out


def _corr(xy, xx, yy):
    with np.errstate(all="ignore"):
        return np.where((xx > 0) & (yy > 0), xy / np.sqrt(xx * yy), np.nan)


def asym_cols(M: np.ndarray, b: int, li: int) -> np.ndarray:
    """``A_b(L)`` per row of ``M`` (rows of 32-vectors): corr(K->P) - corr(P->K) for bucket b, lag index li."""
    o = b * NCOL + li * 8
    return _corr(M[:, o], M[:, o + 1], M[:, o + 2]) - _corr(M[:, o + 4], M[:, o + 5], M[:, o + 6])


def k1_rows(M: np.ndarray) -> np.ndarray:
    """``K1 = [A_O(10) + A_O(20)] - [A_R(10) + A_R(20)]`` per row."""
    return sum(asym_cols(M, 1, li) for li in range(2)) - sum(asym_cols(M, 0, li) for li in range(2))


def asymmetry(M: np.ndarray, bucket: str, lag_steps: int) -> float:
    """``A_b(L)`` of a total vector (study formula; lag in 10-minute steps, 1 or 2)."""
    return float(asym_cols(np.atleast_2d(M), 1 if bucket == "O" else 0, LAGS.index(lag_steps))[0])


def k1(t: StepTable, mask: np.ndarray | None = None, w: np.ndarray | None = None) -> float:
    m = primary_mask(t) if mask is None else mask
    return float(k1_rows(_sum_by(t, np.zeros(len(t.pair), int), 1, m, w))[0])


def _codes(a: np.ndarray) -> tuple[np.ndarray, int]:
    c, u = pd.factorize(np.asarray(a).astype(str))
    return c, len(u)


def boot_k1(S: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Cluster bootstrap of K1 from per-cluster 32-vector sums (multinomial resampling, as ``cross_venue.boot_stat``)."""
    n = len(S)
    if n == 0:
        return np.full(n_boot, np.nan)
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for a in range(0, n_boot, 500):
        b = min(a + 500, n_boot)
        W = rng.multinomial(n, np.full(n, 1.0 / n), size=b - a).astype(float)
        out[a:b] = k1_rows(W @ S)
    return out


def _p_two(boots: np.ndarray) -> float:
    return cv.p_two_sided(boots)


def k1_bootstrap(t: StepTable, mask: np.ndarray | None = None, w: np.ndarray | None = None, ways=("event", "utc_date"), n_boot: int = N_BOOT,
                 seed: int = SEED_BOOT) -> dict:
    """K1 with two-sided p = max over the event-cluster and UTC-date-cluster bootstraps (percentile), small-G rule per way: G < 15
    not testable (p = 1); 15 <= G < 30 the larger of the bootstrap p and a t(G - 1) p from the bootstrap SE."""
    m = primary_mask(t) if mask is None else mask
    est = float(k1_rows(_sum_by(t, np.zeros(len(t.pair), int), 1, m, w))[0]) if m.any() else math.nan
    out: dict = {"k1": est, "n_steps": int(m.sum()), "by_way": {}}
    ps = []
    for way in ways:
        codes, g = _codes((t.event if way == "event" else t.udate)[m]) if m.any() else (np.array([], int), 0)
        if g < G_MIN:
            out["by_way"][way] = {"G": int(g), "p": 1.0, "testable": False}
            ps.append(1.0)
            continue
        sub = t.sub(m)
        S = _sum_by(sub, codes, g, np.ones(len(codes), bool), None if w is None else w[m])
        b = boot_k1(S, n_boot, seed)
        p = _p_two(b)
        info = {"G": int(g), "p_boot": p, "testable": True, "ci95": [float(np.nanpercentile(b, 2.5)), float(np.nanpercentile(b, 97.5))]}
        if g < G_NORMAL:
            se = float(np.nanstd(b, ddof=1))
            p_t = float(2 * t_dist.sf(abs(est) / se, g - 1)) if se > 0 else 1.0
            info["p_t"] = p_t
            p = max(p, p_t)
        info["p"] = float(p)
        out["by_way"][way] = info
        ps.append(float(p))
    out["p"] = float(max(ps)) if ps else 1.0
    out["testable"] = all(v.get("testable") for v in out["by_way"].values())
    return out


# ---- controls ---------------------------------------------------------------------------------------------------------


def activity_weights(t: StepTable, mask: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
    """Inverse-probability cell weights re-weighting R steps to O's joint |dK|-decile x Kalshi-spread-tercile distribution
    (O steps keep weight 1). Cells empty in R are dropped (weight 0) and counted."""
    m = primary_mask(t) if mask is None else mask
    w = np.ones(len(t.pair))
    ncell = ACT_DECILES * ACT_TERCILES
    o = np.bincount(t.cell[m & (t.bucket == 1)], minlength=ncell).astype(float)
    r = np.bincount(t.cell[m & (t.bucket == 0)], minlength=ncell).astype(float)
    po, pr = o / max(o.sum(), 1), r / max(r.sum(), 1)
    ratio = np.where(pr > 0, po / np.where(pr > 0, pr, 1), 0.0)
    rm = t.bucket == 0
    w[rm] = ratio[t.cell[rm]]
    return w, {"cells_dropped_empty_in_R": int(((pr == 0) & (po > 0)).sum()), "o_share_dropped_cells": float(po[pr == 0].sum()),
               "cells_empty_in_O": int(((po == 0) & (pr > 0)).sum())}


def activity_matched_k1(t: StepTable, mask: np.ndarray | None = None) -> dict:
    """K1 with R re-weighted to O's activity/spread distribution; adoption needs K1's sign and at least half its magnitude."""
    m = primary_mask(t) if mask is None else mask
    w, info = activity_weights(t, m)
    plain, matched = k1(t, m), k1(t, m, w)
    ok = bool(math.isfinite(plain) and math.isfinite(matched) and plain != 0 and np.sign(matched) == np.sign(plain) and abs(matched) >= abs(plain) / 2.0)
    return {"k1": plain, "k1_matched": matched, "ok": ok, **info}


def _pair_k1(t: StepTable, mask: np.ndarray, extra_mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    npair = len(t.pair_ids)
    m = mask if extra_mask is None else mask & extra_mask
    S = _sum_by(t, t.pair, npair, m)
    n_r, n_o = S[:, 3], S[:, NCOL + 3]
    elig = (n_r >= MIN_PAIR_STEPS) & (n_o >= MIN_PAIR_STEPS)
    return k1_rows(S), elig


def within_pair_k1(t: StepTable, mask: np.ndarray | None = None, *, n_boot: int = N_BOOT, seed: int = SEED_BOOT) -> dict:
    """Pair-equal-weight mean over pairs with >= 30 usable steps in each bucket of the pair's own ``K1_p``; event-cluster and
    UTC-date-cluster bootstraps (the date bootstrap recomputes each pair's statistics from the resampled dates). Adoption needs
    K1's sign and at least half its magnitude (the comparison is made by the caller with :func:`pair_contrast_ok`)."""
    m = primary_mask(t) if mask is None else mask
    kp, elig = _pair_k1(t, m)
    ok = elig & np.isfinite(kp)
    out = {"n_pairs_eligible": int(ok.sum()), "n_pairs_below_minimum": int((~elig).sum()), "k1_pair": float(kp[ok].mean()) if ok.any() else math.nan, "by_way": {}}
    if not ok.any():
        return {**out, "p": 1.0, "testable": False}
    pair_event = np.array([None] * len(t.pair_ids), dtype=object)
    pair_event[t.pair] = t.event
    ev_codes, ng = _codes(pair_event[ok].astype(str))
    rng = np.random.default_rng(seed)
    # event way
    vals = kp[ok]
    boots = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, ng, ng)
        cnt = np.bincount(pick, minlength=ng)[ev_codes]
        boots[i] = (cnt * vals).sum() / max(cnt.sum(), 1)
    ps = {"event": {"G": int(ng), "p": _p_two(boots) if ng >= G_MIN else 1.0, "testable": ng >= G_MIN}}
    # date way: per (pair, date) sums, pairs fixed to the eligible set
    dcodes, nd = _codes(t.udate[m])
    pair_pos = np.full(len(t.pair_ids), -1)
    pair_pos[np.where(ok)[0]] = np.arange(int(ok.sum()))
    pp = pair_pos[t.pair[m]]
    keep = pp >= 0
    if nd >= G_MIN and keep.any():
        npairs = int(ok.sum())
        flat = pp[keep] * nd + dcodes[keep]
        sub = t.sub(m).sub(keep)
        V = _sum_by(sub, flat, npairs * nd, np.ones(int(keep.sum()), bool)).reshape(npairs, nd, 2 * NCOL)
        db = np.empty(n_boot)
        for a in range(0, n_boot, 200):
            b = min(a + 200, n_boot)
            W = rng.multinomial(nd, np.full(nd, 1.0 / nd), size=b - a).astype(float)  # (draws, nd)
            tot = np.einsum("dn,pnc->dpc", W, V)  # (draws, pairs, 32)
            kk = k1_rows(tot.reshape(-1, 2 * NCOL)).reshape(b - a, npairs)
            db[a:b] = np.nanmean(kk, axis=1)
        ps["utc_date"] = {"G": int(nd), "p": _p_two(db), "testable": True}
    else:
        ps["utc_date"] = {"G": int(nd), "p": 1.0, "testable": False}
    out["by_way"] = ps
    out["p"] = float(max(v["p"] for v in ps.values()))
    out["testable"] = all(v["testable"] for v in ps.values())
    return out


def pair_contrast_ok(k1_pooled: float, k1_pair: float) -> bool:
    """Same sign and at least half the magnitude of the pooled K1."""
    return bool(math.isfinite(k1_pooled) and math.isfinite(k1_pair) and k1_pooled != 0 and np.sign(k1_pair) == np.sign(k1_pooled) and abs(k1_pair) >= abs(k1_pooled) / 2.0)


def event_fe_k1(t: StepTable, mask: np.ndarray | None = None) -> dict:
    """Reported: the mean over events (>= 30 steps per bucket) of the event's own ``K1`` (event fixed effects)."""
    m = primary_mask(t) if mask is None else mask
    codes, g = _codes(t.event[m])
    S = _sum_by(t.sub(m), codes, g, np.ones(len(codes), bool))
    ok = (S[:, 3] >= MIN_PAIR_STEPS) & (S[:, NCOL + 3] >= MIN_PAIR_STEPS)
    kk = k1_rows(S)
    use = ok & np.isfinite(kk)
    return {"n_events": int(use.sum()), "k1_event_fe": float(kk[use].mean()) if use.any() else math.nan}


def shift_12h_contrast(pairs: list[KPair]) -> dict:
    """Reported: K1 recomputed with the hour label shifted by +12h (no inference)."""
    t = step_table(pairs, shift_s=12 * 3600.0)
    return {"k1_shift_12h": k1(t), "n_steps": int(primary_mask(t).sum())}


def reverse_direction_by_bucket(t: StepTable, mask: np.ndarray | None = None) -> dict:
    """Reported: the study's reverse-direction correlation ``r(dP_t, dK_{t+L})`` by bucket and lag."""
    m = primary_mask(t) if mask is None else mask
    S = _sum_by(t, np.zeros(len(t.pair), int), 1, m)
    out = {}
    for b, nm in ((0, "R"), (1, "O")):
        for li, L in enumerate(LAGS):
            o = b * NCOL + li * 8 + 4
            out[f"{nm}{L * 10}"] = float(_corr(S[:, o], S[:, o + 1], S[:, o + 2])[0])
    return out


# ---- pseudo-split size calibration ------------------------------------------------------------------------------------


def pseudo_split_calibration(t: StepTable, mask: np.ndarray | None = None, *, n_draws: int = PSEUDO_DRAWS, seed: int = SEED_PSEUDO, n_boot: int = N_BOOT) -> dict:
    """Within one real bucket, whole (pair, New York date, half-hour) blocks are assigned at random to two pseudo-buckets with the
    real O : R step ratio; K1 is recomputed with the full two-sided test (event and UTC-date bootstraps, small-G rule) on
    ``n_draws`` splits within R and ``n_draws`` within O. The pooled rejection rate at p < 0.05 must be at most 6.5%; each bucket's
    rate is reported."""
    m0 = primary_mask(t) if mask is None else mask
    n_o, n_r = int((m0 & (t.bucket == 1)).sum()), int((m0 & (t.bucket == 0)).sum())
    q = n_o / max(n_o + n_r, 1)
    rng = np.random.default_rng(seed)
    rej = {"R": 0, "O": 0}
    tests = {"R": 0, "O": 0}
    ev_c, n_ev = _codes(t.event[m0])
    ud_c, n_ud = _codes(t.udate[m0])
    base = np.where(m0)[0]
    for nm, rb in (("R", 0), ("O", 1)):
        sel = np.where(m0 & (t.bucket == rb))[0]
        if not len(sel):
            continue
        blk_codes, nblk = _codes(t.block[sel])
        for _ in range(n_draws):
            pseudo = pseudo_assignment(len(t.pair), sel, blk_codes, nblk, q, rng)
            use = pseudo >= 0
            ps = []
            testable = True
            for codes_all, ng in ((ev_c, n_ev), (ud_c, n_ud)):
                if ng < G_MIN:
                    ps.append(1.0)
                    testable = False
                    continue
                c = np.full(len(t.pair), 0)
                c[base] = codes_all
                S = _sum_sub(t, use, c, ng, pseudo)
                b = boot_k1(S, n_boot, int(rng.integers(1, 2**31 - 1)))
                est = float(k1_rows(S.sum(axis=0, keepdims=True))[0])
                p = _p_two(b)
                if ng < G_NORMAL:
                    se = float(np.nanstd(b, ddof=1))
                    p = max(p, float(2 * t_dist.sf(abs(est) / se, ng - 1)) if se > 0 else 1.0)
                ps.append(p)
            tests[nm] += 1
            rej[nm] += int(testable and max(ps) < P_TWO_SIDED)
    tot, n = rej["R"] + rej["O"], tests["R"] + tests["O"]
    rate = tot / n if n else math.nan
    return {"n_tests": n, "rate_pooled": rate, "rate_R": rej["R"] / tests["R"] if tests["R"] else math.nan, "rate_O": rej["O"] / tests["O"] if tests["O"] else math.nan,
            "max_rate": PSEUDO_MAX_REJECT, "ok": bool(n and rate <= PSEUDO_MAX_REJECT), "o_to_r_ratio": q}


def pseudo_assignment(n: int, sel: np.ndarray, blk_codes: np.ndarray, nblk: int, q: float, rng: np.random.Generator) -> np.ndarray:
    """Pseudo-bucket label (1 = pseudo-O, 0 = pseudo-R, -1 = not in the real bucket) per step: whole (pair, New York date,
    half-hour) blocks are assigned at random with probability ``q`` of pseudo-O (the real O : R step ratio)."""
    assign = (rng.random(nblk) < q).astype(np.int8)
    pseudo = np.full(n, -1, dtype=np.int8)
    pseudo[sel] = assign[blk_codes]
    return pseudo


def _sum_sub(t: StepTable, use: np.ndarray, codes: np.ndarray, ng: int, pseudo: np.ndarray) -> np.ndarray:
    out = np.zeros((ng, 2 * NCOL))
    for b in (0, 1):
        m = use & (pseudo == b)
        for j in range(NCOL):
            out[:, b * NCOL + j] = np.bincount(codes[m], weights=t.X[m, j], minlength=ng)
    return out


# ---- census -----------------------------------------------------------------------------------------------------------


def k1_mde(share_pairs: float, share_r: float, se20: float = SE20_C1) -> dict:
    """Two-sided MDE of K1 (z 1.96 + 0.84) from the C1 20-minute SE scaled by the primary share of pairs and the bucket step
    shares (declared formula; never used to change a threshold)."""
    se_r = se20 / math.sqrt(max(share_pairs * share_r, 1e-9))
    se_o = se20 / math.sqrt(max(share_pairs * (1 - share_r), 1e-9))
    se = math.sqrt(se_r**2 + se_o**2) * 0.9  # event pairing helps a little (declared 10%)
    return {"se": se, "mde": 2.8 * se, "se_R": se_r, "se_O": se_o}


def k_census(pairs: list[KPair]) -> dict:
    """K-i / K-ii counts (no lead statistic): pairs, events and usable steps per bucket in the primary and the sports stratum,
    clusters per way, pairs with >= 30 usable steps in both buckets, Kalshi spread and flat-step shares by bucket, the MDE."""
    t = step_table(pairs)
    out: dict = {"n_pairs": len(pairs), "n_events": len({p.event for p in pairs}), "by_category": pd.Series([p.cat for p in pairs]).value_counts().to_dict()}
    for nm, m in (("primary", primary_mask(t)), ("sports", ~primary_mask(t))):
        d: dict = {}
        for b, bn in ((0, "R"), (1, "O")):
            mb = m & (t.bucket == b)
            d[f"steps_{bn}"] = int(mb.sum())
            d[f"events_{bn}"] = int(len(set(t.event[mb])))
            d[f"dates_{bn}"] = int(len(set(t.udate[mb])))
        _, elig = _pair_k1(t, m)
        d["pairs_ge30_both"] = int(elig.sum())
        out[nm] = d
    prim = out["primary"]
    tot = prim["steps_R"] + prim["steps_O"]
    sp = float(np.mean([not p.sports for p in pairs])) if pairs else math.nan
    out["mde"] = k1_mde(sp, prim["steps_R"] / tot if tot else 0.5) if tot else None
    out["kalshi_spread_by_bucket"] = {}
    m = primary_mask(t)
    for b, bn in ((0, "R"), (1, "O")):
        mb = m & (t.bucket == b)
        out["kalshi_spread_by_bucket"][bn] = {"median": float(np.nanmedian(t.kspr[mb])) if mb.any() else None,
                                              "kvol_mean": float(t.kvol[mb].mean()) if mb.any() else None}
    return out


def j4_wide_by_hour(capture_root: Path, *, before: str = T_J4R, list_captures=None) -> dict:
    """J4 context: from complete captures with ``capture_start_utc < before``, the share of rows with a two-sided quote and mid in
    [0.02, 0.98] whose spread exceeds 0.10, by capture hour mapped to R/O in New York time (spread and mid only). Captures at or
    after ``before`` are never read. If R and O differ by more than 2 percentage points the verdict carries a label."""
    from . import forecast

    caps = (list_captures or forecast.list_complete_captures)(Path(capture_root))
    lim = datetime.fromisoformat(before.replace("Z", "+00:00"))
    acc = {0: [0, 0], 1: [0, 0]}
    n_cap = n_missing = 0
    for c in caps:
        if c["_start"] >= lim:
            continue
        p = Path(c["dir"]) / "rows.csv.gz"
        if not p.exists():
            n_missing += 1
            continue
        df = pd.read_csv(p, usecols=["best_bid", "best_ask"], dtype=float)
        bid, ask = df["best_bid"].to_numpy(), df["best_ask"].to_numpy()
        two = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask < 1) & (ask > bid)
        mid = (bid + ask) / 2
        sel = two & (mid >= J4_MID[0]) & (mid <= J4_MID[1])
        wide = sel & ((ask - bid) > HALF_SPREAD_J4)
        b = int(buckets_of(np.array([c["_start"].timestamp()]))[0])
        acc[b][0] += int(wide.sum())
        acc[b][1] += int(sel.sum())
        n_cap += 1
    rate = {nm: (acc[b][0] / acc[b][1] if acc[b][1] else math.nan) for b, nm in ((0, "R"), (1, "O"))}
    diff = abs(rate["R"] - rate["O"]) if all(math.isfinite(v) for v in rate.values()) else math.nan
    return {"rate": rate, "n_rows": {"R": acc[0][1], "O": acc[1][1]}, "n_captures": n_cap, "n_missing_raw": n_missing, "diff_pp": diff * 100 if math.isfinite(diff) else None,
            "label": "Polymarket quote state differs by hour (J4 confound possible)" if math.isfinite(diff) and diff > J4_DIFF_LABEL else None}


def adoption(res: dict) -> dict:
    """K1 adoption (one-directional): two-sided p < 0.05, ``|K1| >= 0.10``, the pseudo-split calibration holds, activity matching
    and the within-pair contrast hold, and robustness (ii)-(iii). An unknown or untestable item blocks."""
    reasons = []
    if not (res.get("testable") and res["p"] < P_TWO_SIDED):
        reasons.append("p")
    if not (math.isfinite(res.get("k1", math.nan)) and abs(res["k1"]) >= K1_FLOOR):
        reasons.append("floor")
    for key, why in (("calibration_ok", "pseudo_split"), ("matched_ok", "activity_matched"), ("pair_ok", "within_pair"), ("robust_ok", "robustness")):
        if res.get(key) is not True:
            reasons.append(why)
    return {"adopted": not reasons, "blockers": reasons}
