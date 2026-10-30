# ruff: noqa: E501
"""CB3 family A: quote-vacuum recovery (CH35) (docs/research_lab/CREATIVE_BATCH_3.md §3 CB3-A, §4.1).

Mechanism tests A1 (recovery ratio) and A2 (unconditional re-quote value) on the ``quote_state/`` panel; A3 (filled re-quote,
Stage 2 / P only) on recorded sweeps and follow-up prints. Prices in price units (1c = 0.01). Paper rules only.

Reads ``cb3_extract/quote_state/`` through ``cb3_quote_state.read_quote_state``; never a capture in T_J4R (the loader refuses
the request), never a capture at or after T3_A_dev_end for the A screen.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import cb3_common as C
from . import cb3_declaration as D
from . import cb3_maker as M
from . import cb3_quote_state as qs

A = D.A
GAP_LO, GAP_HI = (x * 3600.0 for x in A["gap_h"])
HORIZON = tuple(A["recovery_horizon_captures"])  # (2, 3, 4)

ASOF_FIELDS = ("asof_end_date", "asof_created_at", "asof_fee_schedule", "asof_fee_category", "fees_enabled")
_NUM = ["best_bid", "best_ask", "spread", "last_trade_price", "volume_num", "chg_1d", "s1_depth_bid_1c", "s1_depth_ask_1c", "s1_best_bid", "s1_best_ask", "s2_best_bid", "s2_best_ask",
        "s1_bid_size_1", "s1_ask_size_1", "s2_bid_size_1", "s2_ask_size_1"]
_TRUTHY = {"1", "true", "True", "TRUE", "1.0"}
_FALSY = {"0", "false", "False", "FALSE", "0.0"}


def _flag(s: pd.Series) -> np.ndarray:
    """1.0 true, 0.0 false, NaN blank/unknown."""
    v = s.astype(str)
    return np.where(v.isin(_TRUTHY), 1.0, np.where(v.isin(_FALSY), 0.0, np.nan))


def _num(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s.where(s != "", np.nan), errors="coerce").to_numpy(float)


def _epoch_col(s: pd.Series) -> np.ndarray:
    t = pd.to_datetime(s.where(s != "", np.nan), utc=True, errors="coerce")
    return (t.astype("int64") / 1e9).where(t.notna(), np.nan).to_numpy(float) if len(t) else np.empty(0)


# =============================================================================================
# 1. Panel
# =============================================================================================


class Panel:
    """Market x capture matrices of the quote state (NaN = no row / blank)."""

    def __init__(self, cap_ids: list[str], starts: np.ndarray, markets: np.ndarray, mat: dict[str, np.ndarray], present: np.ndarray,
                 in_capture: np.ndarray, meta: pd.DataFrame, asof: dict[str, np.ndarray] | None = None, asof_cols: np.ndarray | None = None) -> None:
        self.cap_ids, self.starts, self.markets, self.mat, self.present, self.in_capture, self.meta = cap_ids, np.asarray(starts, float), markets, mat, present, in_capture, meta
        # as-of fields of each capture (look-ahead free, freeze-check fix 5); asof_cols[c] False = the capture lacks the columns
        self.asof, self.asof_cols = asof, asof_cols
        d = np.diff(self.starts)
        self.gap_ok = (d >= GAP_LO - 1e-6) & (d <= GAP_HI + 1e-6)
        b, a, s = mat["best_bid"], mat["best_ask"], mat["spread"]
        self.tight = bd.h_tight_mask(b, a, s) & present
        self.mid = np.where(bd._two_sided(b, a), (b + a) / 2.0, np.nan)
        self.n_caps = len(cap_ids)


def panel_from_frames(frames: list[tuple[str, float, pd.DataFrame, set[str] | None]], *, asof: bool = False) -> Panel:
    """Build a panel from ``(capture_id, start_epoch, rows_frame_raw_strings, ids_or_None)`` in start order. ``asof`` keeps the
    per-capture as-of end_date / created_at / fee fields (``asof_*``, ``fees_enabled``); a capture lacking any of those columns
    gets ``asof_cols[c] = False`` and its rows are ineligible for the prospective builders (counted there)."""
    frames = sorted(frames, key=lambda f: f[1])
    return _build_panel([f[0] for f in frames], [f[1] for f in frames], lambda j: frames[j][2]["market_id"].astype(str),
                        lambda j: frames[j][2], lambda j: frames[j][3], asof=asof)


_PANEL_COLS = {*_NUM, "market_id", "closed", "active", "accepting_orders", "s1_batch_receipt_utc", "s2_batch_receipt_utc", *ASOF_FIELDS,
               "condition_id", "event_id", "neg_risk_id", "parent_event_ids"}


# matrices the A census never reads (detect_onsets + census_a): not allocated on the census path to bound memory
CENSUS_A_DROP = ("chg_1d", "active", "s1_depth_bid_1c", "s1_depth_ask_1c", "s1_bid_size_1", "s1_ask_size_1", "s2_bid_size_1", "s2_ask_size_1", "s1_recv", "s2_recv")


def _build_panel(cap_ids: list[str], starts: list[float], market_ids_of, frame_of, ids_of, *, asof: bool, drop_mat: tuple[str, ...] = ()) -> Panel:
    """Core of the panel build; ``frame_of(j)`` may load capture j on demand so only one frame is alive at a time."""
    frames = [(cap_ids[j], starts[j]) for j in range(len(cap_ids))]
    universe: dict[str, int] = {}
    for j in range(len(frames)):
        for m in market_ids_of(j):
            universe.setdefault(m, len(universe))
    n, c = len(universe), len(frames)
    markets = np.array(list(universe), object)
    mat = {k: np.full((n, c), np.nan) for k in [*_NUM, "closed", "active", "accepting_orders", "s1_recv", "s2_recv"] if k not in drop_mat}
    present = np.zeros((n, c), bool)
    in_capture = np.zeros((n, c), bool)
    meta = pd.DataFrame({"market_id": markets, "condition_id": "", "event_id": "", "neg_risk_id": "", "parent_event_ids": ""})
    asof_m = {k: np.full((n, c), "", object) for k in ASOF_FIELDS} if asof else None
    asof_cols = np.zeros(c, bool)
    meta_idx = meta.set_index("market_id")
    for j in range(len(frames)):
        df, ids = frame_of(j), ids_of(j)
        df = df.drop_duplicates("market_id")
        idx = np.array([universe[m] for m in df["market_id"].astype(str)], int)
        present[idx, j] = True
        for k in _NUM:
            if k in df and k in mat:
                mat[k][idx, j] = _num(df[k])
        for k in ("closed", "active", "accepting_orders"):
            if k in df and k in mat:
                mat[k][idx, j] = _flag(df[k])
        for k, src in (("s1_recv", "s1_batch_receipt_utc"), ("s2_recv", "s2_batch_receipt_utc")):
            if src in df and k in mat:
                mat[k][idx, j] = _epoch_col(df[src])
        if asof:
            asof_cols[j] = all(k in df for k in ASOF_FIELDS)
            for k in ASOF_FIELDS:
                if k in df:
                    asof_m[k][idx, j] = df[k].astype(str).to_numpy()
        for k in ("condition_id", "event_id", "neg_risk_id", "parent_event_ids"):
            if k in df:
                vals = df[k].astype(str).to_numpy()
                nz = vals != ""
                meta_idx.iloc[idx[nz], meta_idx.columns.get_loc(k)] = vals[nz]
        if ids is None:
            in_capture[idx, j] = True
        else:
            hit = np.fromiter((universe[m] for m in ids if m in universe), int)  # dict lookup: same set as np.isin(markets, ids), without the object-array sort
            in_capture[hit, j] = True
            in_capture[idx, j] = True
    return Panel(list(cap_ids), np.array(list(starts)), markets, mat, present, in_capture, meta_idx.reset_index(), asof_m, asof_cols)


def load_quote_panel(root: Path, *, since: float | None, before: float | None, purpose: str, j4r: tuple[float, float] | None = None,
                     capture_ids: list[str] | None = None, asof: bool = False, drop_mat: tuple[str, ...] = ()) -> Panel:
    """Load ``quote_state/`` captures with ``since <= start < before`` (epoch seconds). A request that selects ANY capture in
    T_J4R is refused (analysis and census never read it); the A screen also refuses captures at/after T3_A_dev_end. The
    manifest decides which captures exist; ``missing`` captures are skipped and break the gap rule downstream."""
    root = Path(root)
    man = json.loads((root / "manifest.json").read_text())
    ents = [e for e in man["captures"].values() if e.get("status") == "extracted"]
    ents.sort(key=lambda e: D.epoch(e["capture_start_utc"]))
    sel = []
    for e in ents:
        st = D.epoch(e["capture_start_utc"])
        if since is not None and st < since:
            continue
        if before is not None and st >= before:
            continue
        if capture_ids is not None and e["capture_id"] not in capture_ids:
            continue
        D.check_capture_allowed(st, purpose=purpose, window=j4r)
        sel.append((e["capture_id"], st))
    # memory-bounded: one capture's frame is alive at a time (market_id column first for the universe, then the needed columns)
    return _build_panel([c for c, _ in sel], [st for _, st in sel],
                        lambda j: qs.read_quote_state(root, sel[j][0], usecols=["market_id"])["market_id"].astype(str),
                        lambda j: qs.read_quote_state(root, sel[j][0], usecols=lambda c: c in _PANEL_COLS and c not in drop_mat),
                        lambda j: set(qs.read_quote_state(root, sel[j][0], ids=True, usecols=["market_id"])["market_id"]), asof=asof,
                        drop_mat=drop_mat)


# =============================================================================================
# 2. Onsets
# =============================================================================================


def _traded(P: Panel, i: int, rows: np.ndarray) -> np.ndarray:
    """Traded before c_i: ``last_trade_price`` non-empty and ``volume_num`` > 0 where present (blank volume with a last trade counts)."""
    ltp = P.mat["last_trade_price"][rows, i]
    vol = P.mat["volume_num"][rows, i]
    return np.isfinite(ltp) & ~(np.isfinite(vol) & (vol <= 0))


def dep_labels(P: Panel) -> np.ndarray:
    """dep_group proxy: neg-risk id, else first parent event id, else event id (flag: share on the event fallback reported)."""
    m = P.meta
    nr = m["neg_risk_id"].astype(str)
    par = m["parent_event_ids"].astype(str).str.strip("[]\"' ").str.split(",").str[0].str.strip("\"' ")
    out = np.where(nr != "", "nr:" + nr, np.where(par != "", "pe:" + par, "ev:" + m["event_id"].astype(str)))
    return out.astype(object)


def detect_onsets(P: Panel) -> tuple[pd.DataFrame, Counter]:
    """One-sided quote vacuums: tight at i-1 and i (E001), two-sided at i+1 with the vacated side jumping >= 5c and the other
    side within 1c. Gaps must be in [1.5, 3] h. Exclusions are counted by reason in the order applied; a one-sided book at
    i+1 is counted, not tested."""
    b, a, mid = P.mat["best_bid"], P.mat["best_ask"], P.mid
    excl: Counter = Counter()
    rows = []
    for i in range(1, P.n_caps - 1):
        tp, ti = P.tight[:, i - 1], P.tight[:, i]
        excl["not_tight_prev"] += int((ti & ~tp).sum())
        cand = np.flatnonzero(tp & ti)
        if not len(cand):
            continue
        excl["candidates"] += len(cand)
        if not (P.gap_ok[i - 1] and P.gap_ok[i]):
            excl["gap_rule_break"] += len(cand)
            continue
        clos, acc = P.mat["closed"][cand, i], P.mat["accepting_orders"][cand, i]
        bad = (clos == 1.0) | (acc == 0.0)
        excl["closed_or_not_accepting"] += int(bad.sum())
        cand = cand[~bad]
        tr = _traded(P, i, cand)
        excl["no_trade_before_i"] += int((~tr).sum())
        cand = cand[tr]
        absent = ~P.present[cand, i + 1]
        excl["absent_at_i1"] += int(absent.sum())
        cand = cand[~absent]
        b1, a1 = b[cand, i + 1], a[cand, i + 1]
        two = bd._two_sided(b1, a1)
        excl["one_sided_at_i1"] += int((~two).sum())
        cand, b1, a1 = cand[two], b1[two], a1[two]
        bi, ai = b[cand, i], a[cand, i]
        ask_v = ((a1 - ai) >= A["onset_min"] - 1e-12) & (np.abs(b1 - bi) < A["onset_other_side_max"])
        bid_v = ((bi - b1) >= A["onset_min"] - 1e-12) & (np.abs(a1 - ai) < A["onset_other_side_max"])
        on = ask_v | bid_v
        excl["no_onset"] += int((~on).sum())
        excl["onsets"] += int(on.sum())
        for k in np.flatnonzero(on):
            m = int(cand[k])
            s = 1 if ask_v[k] else -1
            rows.append({"cap_i": i, "m_idx": m, "s": s, "b_i": bi[k], "a_i": ai[k], "m_i": mid[m, i], "m1": mid[m, i + 1],
                         "D": mid[m, i + 1] - mid[m, i], "q": ai[k] if s > 0 else bi[k], "hs_i": (ai[k] - bi[k]) / 2.0,
                         "b1": b1[k], "a1": a1[k]})
    u = pd.DataFrame(rows)
    return _annotate(P, u), excl


def _annotate(P: Panel, u: pd.DataFrame) -> pd.DataFrame:
    if not len(u):
        return u
    u = u.copy()
    m, i = u["m_idx"].to_numpy(int), u["cap_i"].to_numpy(int)
    u["market_id"] = P.markets[m]
    u["event"] = P.meta["event_id"].to_numpy()[m]
    u["dep"] = dep_labels(P)[m]
    u["cap_id"] = [P.cap_ids[x] for x in i]
    u["cap_start"] = P.starts[i]
    if P.asof is not None:  # as-of values at the onset capture i+1 (look-ahead free); absent -> unknown -> no rebate
        u["cat"] = P.asof["asof_fee_category"][m, i + 1]
        u["fee_schedule"] = P.asof["asof_fee_schedule"][m, i + 1]
        u["fees_enabled"] = P.asof["fees_enabled"][m, i + 1]
    else:
        u["cat"], u["fee_schedule"], u["fees_enabled"] = "", "", ""
    disp = np.abs(u["D"].to_numpy(float)) * 100.0
    lo = [x[0] for x in A["displacement_bands_c"]]
    u["disp_band"] = np.searchsorted(np.asarray(lo, float), disp, side="right") - 1
    u["price_band"] = np.searchsorted(np.array(D.B["price_bands"]), u["m_i"].to_numpy(float), side="right")
    sp1 = P.mat["spread"][m, i + 1]
    u["swept_i1"] = (np.nan_to_num(sp1, nan=np.inf) <= A["tight_spread_max"] + 1e-12) & np.isfinite(P.mat["s1_best_bid"][m, i + 1]) & np.isfinite(P.mat["s2_best_bid"][m, i + 1])
    s1b, s1a = P.mat["s1_best_bid"][m, i + 1], P.mat["s1_best_ask"][m, i + 1]
    s2b, s2a = P.mat["s2_best_bid"][m, i + 1], P.mat["s2_best_ask"][m, i + 1]
    s = u["s"].to_numpy(int)
    q, bi, ai = u["q"].to_numpy(float), u["b_i"].to_numpy(float), u["a_i"].to_numpy(float)
    far = A["sweep_confirm_min"] - 1e-12
    with np.errstate(invalid="ignore"):
        conf = np.where(s > 0, s1a - ai >= far, bi - s1b >= far)
        pers_far = np.where(s > 0, (s1a - q >= A["persist_far_min"] - 1e-12) & (s2a - q >= A["persist_far_min"] - 1e-12),
                            (q - s1b >= A["persist_far_min"] - 1e-12) & (q - s2b >= A["persist_far_min"] - 1e-12))
        other = np.where(s > 0, (np.abs(s1b - bi) <= A["persist_other_side_max"] + 1e-12) & (np.abs(s2b - bi) <= A["persist_other_side_max"] + 1e-12),
                         (np.abs(s1a - ai) <= A["persist_other_side_max"] + 1e-12) & (np.abs(s2a - ai) <= A["persist_other_side_max"] + 1e-12))
    u["sweep_confirmed"] = np.asarray(conf, bool) & np.isfinite(s1a) & np.isfinite(s1b)
    u["persistent"] = np.asarray(pers_far & other, bool) & u["swept_i1"].to_numpy(bool)
    return u


# =============================================================================================
# 3. Recovery mark
# =============================================================================================


def recovery_mark(P: Panel, u: pd.DataFrame, payouts: dict[str, float] | None = None) -> pd.DataFrame:
    """First E001-tight capture in {i+2, i+3, i+4} (gap rule throughout) -> ``m_T``. None tight -> unrecovered, ``m_T := m_(i+1)``.
    A gap-rule break before T, or a window running past the last capture, excludes the unit (``excluded`` column). Closed
    before T: a valid payout ``Y`` in ``payouts`` codes ``m_T := Y``; a market closed without a valid payout is unrecovered.
    Only captures up to i+4 are ever read (a planted change after i+4 cannot move the result)."""
    if not len(u):
        return u.assign(m_T=[], T_k=[], status=[], excluded=[])
    u = u.copy()
    m, i = u["m_idx"].to_numpy(int), u["cap_i"].to_numpy(int)
    n = len(u)
    mT = np.full(n, np.nan)
    Tk = np.zeros(n, int)
    status = np.full(n, "", object)
    open_ = np.ones(n, bool)
    for k in HORIZON:
        ci = i + k
        a = open_ & (ci >= P.n_caps)
        status[a] = "window_end"
        open_ &= ~a
        a = open_.copy()
        idx = np.flatnonzero(a)
        brk = np.zeros(n, bool)
        brk[idx] = ~P.gap_ok[ci[idx] - 1]
        status[brk] = "gap_break"
        open_ &= ~brk
        idx = np.flatnonzero(open_)
        clos = P.mat["closed"][m[idx], ci[idx]] == 1.0
        for j in idx[clos]:
            y = (payouts or {}).get(str(P.markets[m[j]]))
            if y is not None and np.isfinite(y) and y in (0.0, 1.0, 0.5):
                mT[j], status[j] = float(y), "closed_payout"
            else:
                mT[j], status[j] = u["m1"].to_numpy(float)[j], "closed_no_payout"
            Tk[j] = k
            open_[j] = False
        idx = np.flatnonzero(open_)
        tight = P.tight[m[idx], ci[idx]]
        for j in idx[tight]:
            mT[j], Tk[j], status[j] = P.mid[m[j], ci[j]], k, "recovered"
            open_[j] = False
    for j in np.flatnonzero(open_):
        mT[j], status[j] = u["m1"].to_numpy(float)[j], "unrecovered"
    u["m_T"], u["T_k"], u["status"] = mT, Tk, status
    u["excluded"] = np.isin(status, ["window_end", "gap_break"])
    return u


def finalize_units(u: pd.DataFrame) -> pd.DataFrame:
    """Drop excluded units; add the per-unit pieces of R and G (price units)."""
    u = u[~u["excluded"]].copy()
    if len(u):
        u["num"] = u["s"] * (u["m_T"] - u["m_i"])
        u["den"] = u["D"].abs()
        u["g"] = u["s"] * (u["q"] - u["m_T"])
        u = u[np.isfinite(u["num"]) & np.isfinite(u["g"]) & (u["den"] > 0)]
    return u


# =============================================================================================
# 4. A1 / A2
# =============================================================================================


def _ways(u: pd.DataFrame) -> dict[str, np.ndarray]:
    return {"event": u["event"].to_numpy(), "dep": u["dep"].to_numpy(), "onset_capture": u["cap_id"].to_numpy()}


def r_hat(u: pd.DataFrame) -> float:
    d = float(u["den"].sum())
    return float(1.0 - u["num"].sum() / d) if d > 0 else math.nan


def a_tests(u: pd.DataFrame, *, n_boot: int = D.N_BOOT, stage: int = 1) -> dict:
    """A1 (R, ratio of sums, H1 R > 0.50) and A2 (G = mean g, H1 G > 0). p = max over event / dep_group / onset-capture
    CR1 (>= 1,000 onsets and >= 30 clusters per way, else not testable). Direction-and-floor logic is in :func:`gate_a`."""
    w = _ways(u)
    # R > 0.5  <=>  r = 1 - R < 0.5: test r against 0.5 with H1 r < 0.5 (sign -1)
    rt = C.ratio_test(u["num"].to_numpy(float), u["den"].to_numpy(float), w, null=D.A1_NULL, sign=-1, n_boot=n_boot,
                      min_units=D.A_MIN_ONSETS, min_clusters=D.A_MIN_CAPTURE_CLUSTERS) if len(u) else {"testable": False, "p": 1.0, "n": 0}
    a1 = {"tid": "A1", "testable": rt["testable"], "p": rt["p"], "n": rt.get("n", 0), "effect": r_hat(u) if len(u) else None, "se": rt.get("se"),
          "ratio": rt.get("ratio"), "p_by_way": rt.get("p_by_way"), "clusters": rt.get("clusters"), "ci95_ratio": rt.get("ci95_ratio"), "reason": rt.get("reason")}
    mt = C.mean_test(u["g"].to_numpy(float), w, sign=1, n_boot=n_boot, min_units=D.A_MIN_ONSETS, min_clusters=D.A_MIN_CAPTURE_CLUSTERS) if len(u) else {"testable": False, "p": 1.0, "n": 0, "mean": math.nan}
    se2 = max([x for x in (mt.get("se_by_way") or {}).values() if x is not None and np.isfinite(x)] or [math.nan])
    a2 = {"tid": "A2", "testable": mt["testable"], "p": mt["p"], "n": mt.get("n", 0), "effect": mt.get("mean"), "se": se2, "p_by_way": mt.get("p_by_way"),
          "clusters": mt.get("clusters"), "ci95": mt.get("ci95"), "reason": mt.get("reason")}
    return {"A1": a1, "A2": a2}


def _drop_top5(u: pd.DataFrame, tid: str) -> dict[str, pd.DataFrame]:
    out = {}
    for k, cl in _ways(u).items():
        contrib = (D.A1_NULL * u["den"] - u["num"]).to_numpy(float) if tid == "A1" else u["g"].to_numpy(float)
        out[k] = u[C.top_clusters_mask(contrib, cl)]
    return out


def robustness_a(u: pd.DataFrame) -> dict:
    """(i) keeps sign and floor without the top 5 clusters in each way; (iv) sweep-confirmed onsets keep the declared side of
    0.5 (A1) / 0 (A2)."""
    out: dict = {}
    for tid in ("A1", "A2"):
        fl = D.A_FLOORS[tid]
        for k, sub in _drop_top5(u, tid).items():
            est = r_hat(sub) if tid == "A1" else float(sub["g"].mean()) if len(sub) else math.nan
            out[f"{tid}_top5_{k}"] = {"estimate": est, "ok": bool(np.isfinite(est) and est >= fl)}
        sc = u[u["sweep_confirmed"]]
        est = r_hat(sc) if tid == "A1" else float(sc["g"].mean()) if len(sc) else math.nan
        side = D.A1_NULL if tid == "A1" else 0.0
        out[f"{tid}_sweep_confirmed"] = {"estimate": est, "n": int(len(sc)), "ok": bool(np.isfinite(est) and est > side)}
    return out


def reported_a(u_all: pd.DataFrame, P: Panel, units_raw: pd.DataFrame) -> dict:
    """Reported, not binding: recovered-only R and G, the unrecovered share, R/G with the i+4 mid regardless of state, R/G on
    the A3-eligible stratum (swept at i+1 and persistent)."""
    out: dict = {"unrecovered_share": float((u_all["status"] != "recovered").mean()) if len(u_all) else None}
    rec = u_all[u_all["status"] == "recovered"]
    out["recovered_only"] = {"n": int(len(rec)), "R": r_hat(rec) if len(rec) else None, "G": float(rec["g"].mean()) if len(rec) else None}
    if len(u_all):
        m4 = P.mid[u_all["m_idx"].to_numpy(int), np.minimum(u_all["cap_i"].to_numpy(int) + 4, P.n_caps - 1)]
        ok = np.isfinite(m4) & (u_all["cap_i"].to_numpy(int) + 4 < P.n_caps)
        v = u_all[ok].copy()
        mm = m4[ok]
        v["num"] = v["s"] * (mm - v["m_i"])
        v["g"] = v["s"] * (v["q"] - mm)
        out["mid_i4_regardless"] = {"n": int(len(v)), "R": r_hat(v) if len(v) else None, "G": float(v["g"].mean()) if len(v) else None}
        el = u_all[u_all["persistent"]]
        out["a3_eligible_stratum"] = {"n": int(len(el)), "R": r_hat(el) if len(el) else None, "G": float(el["g"].mean()) if len(el) else None}
        out["by_side"] = {("ask" if s > 0 else "bid"): {"n": int(len(g)), "R": r_hat(g), "G": float(g["g"].mean())} for s, g in u_all.groupby("s")}
    out["status_counts"] = units_raw["status"].value_counts().to_dict() if len(units_raw) else {}
    return out


def quiet_units(P: Panel, seed: int = D.SEED_BOOT, max_n: int = 200000) -> pd.DataFrame:
    """Baseline (a), reported: a random side's touch quote at i in markets tight at i-1, i and i+1 with no onset; ``m1`` = the
    mid at i+1. Reuse :func:`recovery_mark` / :func:`finalize_units` on the result."""
    rng = np.random.default_rng(seed)
    b, a, mid = P.mat["best_bid"], P.mat["best_ask"], P.mid
    rows = []
    for i in range(1, P.n_caps - 1):
        if not (P.gap_ok[i - 1] and P.gap_ok[i]):
            continue
        cand = np.flatnonzero(P.tight[:, i - 1] & P.tight[:, i] & P.tight[:, i + 1])
        if not len(cand):
            continue
        on = ~(((a[cand, i + 1] - a[cand, i]) >= A["onset_min"]) | ((b[cand, i] - b[cand, i + 1]) >= A["onset_min"]))
        for m in cand[on]:
            s = 1 if rng.random() < 0.5 else -1
            rows.append({"cap_i": i, "m_idx": int(m), "s": s, "b_i": b[m, i], "a_i": a[m, i], "m_i": mid[m, i], "m1": mid[m, i + 1],
                         "D": mid[m, i + 1] - mid[m, i], "q": a[m, i] if s > 0 else b[m, i], "hs_i": (a[m, i] - b[m, i]) / 2.0,
                         "b1": b[m, i + 1], "a1": a[m, i + 1]})
        if len(rows) >= max_n:
            break
    return _annotate(P, pd.DataFrame(rows))


# =============================================================================================
# 5. Martingale placebo
# =============================================================================================


def _pools(P: Panel, markets: np.ndarray) -> dict[int, np.ndarray]:
    inc = P.mid[:, 1:] - P.mid[:, :-1]
    inc = np.where(P.gap_ok[None, :], inc, np.nan)
    return {int(m): inc[m][np.isfinite(inc[m])] for m in np.unique(markets)}


def martingale_placebo(P: Panel, units: pd.DataFrame, seed: int) -> dict:
    """Keep every real onset (real quotes at i-1, i, i+1). From i+1 on rebuild the mid as a martingale: m'_{i+1+k} = m_{i+1} +
    sum of increments drawn with replacement from the market's pooled valid mid increments (J4-R market-pooled bootstrap);
    the observed half-spread path is kept (bid/ask = m' -/+ hs, clipped to [0.001, 0.999]); the T rule is re-applied (observed
    two-sidedness and spread, rebuilt mid band, not closed); unrecovered is coded m_T := m_(i+1). Units whose real window ends
    or breaks the gap rule before the placebo T are dropped from the draw (counted)."""
    rng = np.random.default_rng(seed)
    n = len(units)
    if not n:
        return {"n_units": 0}
    m, i = units["m_idx"].to_numpy(int), units["cap_i"].to_numpy(int)
    pools = _pools(P, m)
    m1 = units["m1"].to_numpy(float)
    cur = m1.copy()
    mT = np.full(n, np.nan)
    open_ = np.ones(n, bool)
    dropped = np.zeros(n, bool)
    reached = np.zeros(n, bool)
    lo, hi = A["clip"]
    for k in HORIZON:
        ci = i + k
        pl = np.array([len(pools[int(x)]) for x in m])
        draw = np.array([pools[int(x)][rng.integers(0, len(pools[int(x)]))] if len(pools[int(x)]) else np.nan for x in m])
        cur = cur + np.where(open_, draw, 0.0)
        gone = open_ & ((ci >= P.n_caps) | (pl == 0))
        dropped |= gone
        open_ &= ~gone
        idx = np.flatnonzero(open_)
        brk = ~P.gap_ok[ci[idx] - 1]
        dropped[idx[brk]] = True
        open_[idx[brk]] = False
        idx = np.flatnonzero(open_)
        cl = P.mat["closed"][m[idx], ci[idx]] == 1.0
        for j in idx[cl]:
            mT[j] = m1[j]
            open_[j] = False
        idx = np.flatnonzero(open_)
        bo, ao = P.mat["best_bid"][m[idx], ci[idx]], P.mat["best_ask"][m[idx], ci[idx]]
        hs = (ao - bo) / 2.0
        mp = cur[idx]
        bp, ap = np.clip(mp - hs, lo, hi), np.clip(mp + hs, lo, hi)
        with np.errstate(invalid="ignore"):
            tight = bd._two_sided(bo, ao) & ((ao - bo) <= A["tight_spread_max"] + 1e-12) & (bp < ap) & (mp >= A["tight_mid_band"][0]) & (mp <= A["tight_mid_band"][1])
        for j, t in zip(idx, tight, strict=True):
            if t:
                mT[j] = cur[j]
                reached[j] = True
                open_[j] = False
    mT[open_] = m1[open_]
    keep = ~dropped
    v = units[keep].copy()
    v["m_T"] = mT[keep]
    v["num"] = v["s"] * (v["m_T"] - v["m_i"])
    v["den"] = v["D"].abs()
    v["g"] = v["s"] * (v["q"] - v["m_T"])
    v = v[np.isfinite(v["num"]) & (v["den"] > 0)]
    # centred A2 quantity: G_placebo - mean s (q - m_(i+1)) = - mean s (m_T' - m_(i+1)), zero in expectation under the martingale
    gc = float((v["g"] - v["s"] * (v["q"] - v["m1"])).mean()) if len(v) else math.nan
    return {"n_units": int(len(v)), "n_capture_clusters": int(v["cap_id"].nunique()), "R": r_hat(v) if len(v) else math.nan,
            "G": float(v["g"].mean()) if len(v) else math.nan, "G_centred": gc, "reaching_tight_T": int(reached[keep].sum()), "dropped": int(dropped.sum())}


def placebo_a(P: Panel, units_prefinal: pd.DataFrame, real_units: pd.DataFrame, real: dict, draws: int = D.PLACEBO_DRAWS) -> dict:
    """20 martingale draws (seed 317 + k) on the real onset set. Void / bias reading on A1 (R); A2's placebo G is a
    construction check (expected ~ mean(hs - |D|) < 0) and its status follows the A1 family status."""
    keep_ids = real_units.index
    base = units_prefinal.loc[units_prefinal.index.intersection(keep_ids)]
    ds = [martingale_placebo(P, base, D.SEED_PLACEBO + k) for k in range(draws)]
    r_s = C.placebo_summary([d.get("R", math.nan) for d in ds])
    g_s = C.placebo_summary([d.get("G", math.nan) for d in ds])
    gc_s = C.placebo_summary([d.get("G_centred", math.nan) for d in ds])
    rd = C.reading(r_s, real["A1"].get("se") or math.nan)
    r_s["status"] = rd["status"]
    rdc = C.reading(gc_s, real["A2"].get("se") or math.nan)  # binding centred A2 bias check (freeze-check ruling)
    gc_s["status"] = rdc["status"]
    g_s["status"] = "uncentred G is a construction check (expected negative); centred check " + rdc["status"] + "; family status " + rd["status"]
    per = [{"n_units": d.get("n_units"), "capture_clusters": d.get("n_capture_clusters"), "reaching_tight_T": d.get("reaching_tight_T")} for d in ds]
    ok_units = all((d.get("n_units") or 0) >= D.A_MIN_ONSETS and (d.get("n_capture_clusters") or 0) >= D.A_MIN_CAPTURE_CLUSTERS for d in ds)
    return {"A1": r_s, "A2": g_s, "A2_centred": gc_s, "per_draw": per, "family_void": bool(rd["family_void"]), "family_status": rd["status"], "placebo_units_ok": bool(ok_units)}


def gate_a(res: dict, rob: dict, plc: dict | None, alpha: float) -> dict:
    """Stage gate: testable, p < alpha, floor met by the point estimate, family not void (placebo), A1 not biased, binding
    robustness. Returns advance flags per test."""
    out = {}
    for tid in ("A1", "A2"):
        r = res[tid]
        fail = []
        if not r["testable"]:
            fail.append("not_testable")
        else:
            if not r["p"] < alpha:
                fail.append("p")
            if not (r["effect"] is not None and np.isfinite(r["effect"]) and r["effect"] >= D.A_FLOORS[tid]):
                fail.append("floor")
            for k, v in rob.items():
                if k.startswith(tid) and not v["ok"]:
                    fail.append(f"robust:{k}")
            if plc is None:
                fail.append("placebo:missing")
            else:
                if plc["family_void"]:
                    fail.append(f"placebo:{plc['family_status']}")
                elif tid == "A1" and plc["A1"]["status"] != "read":
                    fail.append(f"placebo:{plc['A1']['status']}")
                elif tid == "A2" and plc["A2_centred"]["status"] != "read":
                    fail.append(f"placebo_centred:{plc['A2_centred']['status']}")
                if not plc["placebo_units_ok"]:
                    fail.append("placebo:too_few_units_or_clusters")
        out[tid] = {"advance": not fail, "fail": fail}
    return out


def screen_a(P: Panel, *, n_boot: int = D.N_BOOT, draws: int = D.PLACEBO_DRAWS, payouts: dict[str, float] | None = None, stage: int = 1,
             onset_before: float | None = None) -> dict:
    """Stage 1 on the dev panel (or Stage 2 on the rep panel with ``stage=2``): onsets, recovery mark, A1/A2, placebo, gates.
    ``onset_before``: keep only onsets whose capture started before it (the later captures i+1..i+4 are still read for T)."""
    raw, excl = detect_onsets(P)
    if onset_before is not None and len(raw):
        raw = raw[raw["cap_start"] < onset_before].reset_index(drop=True)
    marked = recovery_mark(P, raw, payouts)
    units = finalize_units(marked)
    alpha = D.ALPHA_STAGE1 if stage == 1 else D.ALPHA_STAGE2
    res = a_tests(units, n_boot=n_boot, stage=stage) if len(units) else {"A1": {"tid": "A1", "testable": False, "p": 1.0, "n": 0, "effect": None}, "A2": {"tid": "A2", "testable": False, "p": 1.0, "n": 0, "effect": None}}
    out: dict = {"stage": stage, "exclusions": dict(excl), "n_onsets_raw": int(len(raw)), "n_units": int(len(units)), "tests": res}
    if len(units):
        rob = robustness_a(units)
        plc = placebo_a(P, marked, units, res, draws) if res["A1"]["testable"] and draws else None
        out.update(robustness=rob, placebo=plc, gates=gate_a(res, rob, plc, alpha), reported=reported_a(units, P, marked))
        q = finalize_units(recovery_mark(P, quiet_units(P)))
        out["baseline_quiet"] = {"n": int(len(q)), "G": float(q["g"].mean()) if len(q) else None, "R": r_hat(q) if len(q) else None}
    else:
        out["gates"] = {t: {"advance": False, "fail": ["not_testable"]} for t in ("A1", "A2")}
    for t in ("A1", "A2"):
        res[t]["advance"] = out["gates"][t]["advance"]
        res[t]["fail"] = out["gates"][t]["fail"]
        res[t]["placebo_status"] = (out.get("placebo") or {}).get("A2_centred" if t == "A2" else t, {}).get("status")
    return out


# =============================================================================================
# 6. A3 (Stage 2 / P)
# =============================================================================================


def a3_units(P: Panel, u: pd.DataFrame, trades_for: Callable[[pd.Series], tuple[dict[str, np.ndarray], bool]], *, inclusion_prob: Callable[[pd.Series], float] | None = None,
             request_time: Callable[[pd.Series], float | None] | None = None) -> tuple[pd.DataFrame, dict]:
    """Filled re-quotes. Eligible = vacuum-stratum onsets swept at pass i+1 and persistent in both sweeps. The re-quote (5 shares
    at q, queue ahead 0) is posted at the SECOND sweep's receipt s2 and lives to s2 + 2h; it fills on the windowed follow-up
    prints (``trades_for(unit)`` -> (prints, page_cap_hit), ts > s2). Mark = the B rule (first tight first-sweep mid at or after t_fill + 6h, next pass
    within 4h, else the worst case), never ``m_T``. Rows carry both fill rules; unavailable fill statuses carry their
    worst-case mark-out."""
    rows, nelig = [], 0
    for r in u.itertuples():
        row = u.loc[r.Index]
        if not bool(row["persistent"]):
            continue
        m, i = int(row["m_idx"]), int(row["cap_i"])
        s2 = P.mat["s2_recv"][m, i + 1]
        if not np.isfinite(s2):
            continue
        nelig += 1
        side = "ask" if row["s"] > 0 else "bid"
        post, trunc = trades_for(row)
        life = A["a3_life_s"]
        truncated_life = False
        rq = request_time(row) if request_time else None
        if rq is not None and rq < s2 + life:
            life, truncated_life = max(rq - s2, 0.0), True
        trunc = bool(trunc)
        oldest = float(post["ts"].min()) if trunc and len(post["ts"]) else None
        st = M.quote_fills(post, s2, side, float(row["q"]), A["a3_queue_ahead"], life=life, truncated=trunc, oldest_ts=oldest)
        later = np.arange(i + 1, P.n_caps)
        marks = M.SweepMarks(P.mat["s1_recv"][m, later], P.mat["s1_best_bid"][m, later], P.mat["s1_best_ask"][m, later])
        pi = inclusion_prob(row) if inclusion_prob else 1.0
        for rule in M.RULES:
            status, tf = st[rule]
            base = {"unit": f"{row['market_id']}@{row['cap_id']}", "rule": rule, "status": status, "side": side, "price": float(row["q"]), "t_post": float(s2),
                    "market_id": row["market_id"], "event": row["event"], "dep": row["dep"], "cap_id": row["cap_id"], "weight": 1.0 / pi, "life_truncated": truncated_life}
            if status == 0:
                rows.append({**base, "t_fill": math.nan})
                continue
            if status == -1:
                rows.append({**base, "t_fill": math.nan, "wc_mo": M.worst_case_mo(side, float(row["q"]), *marks.last_before(s2 + life, 0.0, s2))})
                continue
            m6, _b, _a = marks.mark(tf, M.MARK_S)
            reb = M.rebate_per_share(float(row["q"]), row["cat"], fee_schedule=row["fee_schedule"], fees_enabled=row["fees_enabled"], prospective=True)
            rebh = M.rebate_per_share(float(row["q"]), row["cat"], fee_schedule=row["fee_schedule"], fees_enabled=row["fees_enabled"], prospective=True, halved=True)
            mo = M.mark_out(side, float(row["q"]), m6) if np.isfinite(m6) else math.nan
            fb, fa = marks.last_before(tf + M.MARK_S, 0.0, tf)
            rows.append({**base, "t_fill": tf, "mark6": m6, "mo6": mo, "rebate": reb, "net6": mo + reb, "net6_half": mo + rebh, "mark_unavailable": not np.isfinite(m6),
                         "wc_mo": M.worst_case_mo(side, float(row["q"]), fb, fa)})
    df = pd.DataFrame(rows)
    return df, {"n_eligible_persistent": nelig}


def a3_test(a3: pd.DataFrame, n_eligible: int, *, stage: int, n_boot: int = D.N_BOOT) -> dict:
    """A3: mean net per filled share (> 0, floor 0.5c) and fill rate >= 2% of eligible persistent onsets; binding brackets: the
    touch-rule sign, rebate halved (floor and sign), residual-unavailable worst case, top-5 clusters, weighted sign, truncated life."""
    alpha = D.ALPHA_STAGE1 if stage == 1 else D.ALPHA_STAGE2
    out: dict = {"tid": "A3", "stage": stage, "n_eligible": int(n_eligible)}
    if not len(a3):
        return {**out, "testable": False, "p": 1.0, "advance": False, "fail": ["no_units"]}
    q = a3[a3["rule"] == "queue"]
    f = q[(q["status"] == 1) & np.isfinite(q.get("net6", pd.Series(dtype=float)))]
    fill_rate = float((q["status"] == 1).sum() / n_eligible) if n_eligible else 0.0
    ways = {"event": f["event"].to_numpy(), "dep": f["dep"].to_numpy(), "onset_capture": f["cap_id"].to_numpy()}
    mt = C.mean_test(f["net6"].to_numpy(float), ways, sign=1, n_boot=n_boot) if len(f) else {"testable": False, "p": 1.0, "n": 0, "mean": math.nan}
    out.update(testable=mt["testable"], p=mt["p"], effect=mt.get("mean"), n=mt["n"], fill_rate=fill_rate, ci95=mt.get("ci95"), clusters=mt.get("clusters"))
    if not mt["testable"]:
        return {**out, "advance": False, "fail": ["not_testable"]}
    fail = []
    if not mt["p"] < alpha:
        fail.append("p")
    if not mt["mean"] >= D.A_FLOORS["A3_net"]:
        fail.append("floor")
    if not fill_rate >= D.A_FLOORS["A3_fill_rate"]:
        fail.append("fill_rate")
    br: dict = {}
    for k, cl in ways.items():
        keep = C.top_clusters_mask(f["net6"].to_numpy(float) - mt["mean"], cl)
        v = f["net6"].to_numpy(float)[keep]
        br[f"top5_{k}"] = float(v.mean()) if len(v) else None
        if not (len(v) and v.mean() >= D.A_FLOORS["A3_net"]):
            fail.append(f"robust:top5_{k}")
    wv = f["weight"].to_numpy(float)
    br["weighted_mean"] = float((wv * f["net6"].to_numpy(float)).sum() / wv.sum())
    if not br["weighted_mean"] > 0:
        fail.append("robust:weighted_sign")
    t = a3[(a3["rule"] == "touch") & (a3["status"] == 1) & np.isfinite(a3.get("net6", pd.Series(dtype=float)))]
    br["touch_rule_mean"] = float(t["net6"].mean()) if len(t) else None
    if not (len(t) and t["net6"].mean() > 0):
        fail.append("robust:touch_rule_sign")
    hm = float(f["net6_half"].mean())
    br["rebate_half_mean"] = hm
    if not hm >= D.A_FLOORS["A3_net"]:
        fail.append("robust:rebate_halved")
    wc_unav = q[q["status"] == -1]["wc_mo"].to_numpy(float) if "wc_mo" in q else np.empty(0)
    wc_mark = q[(q["status"] == 1) & q["mark_unavailable"].fillna(False).astype(bool)]["wc_mo"].to_numpy(float) if "mark_unavailable" in q else np.empty(0)
    allv = np.r_[f["net6"].to_numpy(float), wc_unav[np.isfinite(wc_unav)], wc_mark[np.isfinite(wc_mark)]]
    br["worst_case_mean"], br["worst_case_added"] = float(allv.mean()), int(len(allv) - len(f))
    if not allv.mean() > 0:
        fail.append("robust:worst_case_unavailable")
    ft = f[~f["life_truncated"].astype(bool)]
    br["untruncated_life_mean"] = float(ft["net6"].mean()) if len(ft) else None
    if not (len(ft) and ft["net6"].mean() > 0):
        fail.append("robust:truncated_life_sign")
    out.update(brackets=br, advance=not fail, fail=fail)
    return out


# =============================================================================================
# 7. Census (counts only) and the follow-up A3 loader
# =============================================================================================


def census_a(P: Panel) -> dict:
    """q0061 A part: onset counts only. Reads no recovery mark, no T-capture mid, no price after i+1; the onset frame is reduced to
    counts before it is returned."""
    raw, excl = detect_onsets(P)
    out: dict = {"n_captures": P.n_caps, "n_markets": int(len(P.markets)), "gap_breaks": int((~P.gap_ok).sum()), "exclusions": dict(excl), "n_onsets": int(len(raw))}
    if not len(raw):
        return out
    lab = raw.assign(side=np.where(raw["s"] > 0, "ask", "bid"))
    out["by_side"] = lab["side"].value_counts().to_dict()
    out["by_displacement_band_c"] = {str(A["displacement_bands_c"][int(k)]): int(v) for k, v in lab["disp_band"].value_counts().items() if 0 <= int(k) < len(A["displacement_bands_c"])}
    out["by_price_band"] = {str(int(k)): int(v) for k, v in lab["price_band"].value_counts().items()}
    out["onsets_per_capture"] = {"min": int(lab.groupby("cap_id").size().min()), "median": float(lab.groupby("cap_id").size().median()), "max": int(lab.groupby("cap_id").size().max())}
    out["clusters"] = {"event": int(raw["event"].nunique()), "dep": int(raw["dep"].nunique()), "onset_capture": int(raw["cap_id"].nunique())}
    out["swept_at_i1_share"] = float(raw["swept_i1"].mean())
    out["sweep_confirmed_share"] = float(raw["sweep_confirmed"].mean())
    out["persistent_share"] = float(raw["persistent"].mean())
    out["dep_fallback_share"] = float(np.mean([str(x).startswith("ev:") for x in raw["dep"]]))
    out["testable_at_dev_rule"] = bool(len(raw) >= D.A_MIN_ONSETS and raw["cap_id"].nunique() >= D.A_MIN_CAPTURE_CLUSTERS)
    return out


def _pass_ok(reader: M.FollowupReader, pass_cap: str, previous_cap: str) -> bool:
    """The follow-up dir of ``pass_cap`` exists, is a recorded pass (complete/incomplete) and was built for ``previous_cap``."""
    d = reader.root / pass_cap
    try:
        man = json.loads((d / "manifest.json").read_text())
        plan = json.loads((d / "plan.json").read_text())
    except (OSError, ValueError):
        return False
    return man.get("state") in ("complete", "incomplete") and plan.get("previous_capture_id") == previous_cap


def a3_from_followup(P: Panel, u: pd.DataFrame, reader: M.FollowupReader) -> tuple[pd.DataFrame, dict]:
    """A3 inputs from ``cb3_followup``: only onsets in the vacuum stratum drawn at their own capture (``vacuum_plan.json`` of the
    onset capture i+1), windows fetched at the next pass (``vacuum/trades.csv.gz`` under capture i+2, whose plan must name the onset
    capture as its previous capture). Misaligned or missing passes drop the unit (counted); a window that was not reached, failed or
    hit the page cap is passed as truncated, so an empty file never reads as 'not filled'."""
    plans: dict[str, dict] = {}
    keep, n_misaligned = [], 0
    for k, r in u.iterrows():
        i = int(r["cap_i"])
        if i + 2 >= P.n_caps:
            continue
        onset_cap, nxt = P.cap_ids[i + 1], P.cap_ids[i + 2]
        if not _pass_ok(reader, nxt, onset_cap):
            n_misaligned += 1
            continue
        if onset_cap not in plans:
            pth = reader.root / onset_cap / "vacuum_plan.json"
            plans[onset_cap] = json.loads(pth.read_text()) if pth.exists() else {"onsets": []}
        if any(o["market_id"] == r["market_id"] for o in plans[onset_cap].get("onsets", [])):
            keep.append(k)
    uu = u.loc[keep]

    def trades_for(row):
        nxt = P.cap_ids[int(row["cap_i"]) + 2]
        meta = reader.meta(nxt).get("markets", {}).get(f"vacuum:{row['market_id']}", {})
        return reader.trades(nxt, "vacuum", row["market_id"]), bool(meta.get("page_cap", False)) or meta.get("status") != "ok"

    def pi(row):
        pl = plans.get(P.cap_ids[int(row["cap_i"]) + 1], {})
        return float(pl.get("inclusion_prob") or 1.0)

    def req(row):
        nxt = P.cap_ids[int(row["cap_i"]) + 2]
        return reader.meta(nxt).get("markets", {}).get(f"vacuum:{row['market_id']}", {}).get("request_epoch")

    a3, info = a3_units(P, uu, trades_for, inclusion_prob=pi, request_time=req)
    info["n_misaligned_or_missing_pass"] = n_misaligned
    return a3, info
