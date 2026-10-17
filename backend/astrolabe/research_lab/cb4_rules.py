# ruff: noqa: E501
"""CB4 route rules (docs/research_lab/CREATIVE_BATCH_4.md section 4.1): CH46 / CB4-C (pre-close dump) and CH50 / CB4-S (series roll).

Pure functions over DataFrames / arrays; no network and no outcome access except through arguments the caller passes after the
declaration guard (``cb4_analysis``). Every constant comes from ``cb4_declaration`` (hashed); the source of every function here is
part of the declaration hash, so an edit changes the hash and the runner refuses to count until ``model_specs/cb4_v1.json`` is
re-committed. Nothing here is an edge, calibration or profitability claim: all P&L is paper at modelled or recorded prices.

Conservative readings taken where the document is silent are listed in ``INTERPRETATIONS`` and written into every results file.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import cb1_history as H1
from . import cb3_common as CC
from . import cb4_data, cost_regimes
from . import cb4_declaration as D

HOUR, DAY = 3600.0, 86400.0

INTERPRETATIONS = (
    "A flip that is not UMA-clear at c_k+1 is stratum P before E or L is considered (a flip can match E/L and P; P takes it, so S is never contaminated).",
    "UMA 'unknown' = the capture row has no sidecar entry (ext_present = 0); empty UMA status with a sidecar entry is clear.",
    "A closed flag that is blank is unknown and never makes a flip.",
    "Amendment A-C1 (2026-10-17, data-blind): C1 and C2 cluster by event (CR1, >= 30) and by UTC day (C1: date of e; C2: date of closed_time or the censoring mark), not ISO week. The day way enters the p max under the section 2.3 small-G rule iff G_day >= 15; with G_day < 15 it does not enter and the leave-one-day-out sign rule is binding at that stage instead. Top-5 robustness drops 5 events and 5 days. Sign by ISO week is reported only.",
    "C2 'size-weighted' check weights a filled bid by the size of the filling print, capped at the paper size.",
    "S3 posts q from the CB1 band-table half-spread (not the cost-regime one: a larger half-spread in q is not conservative for a seller); the exit uses cost_regimes.",
    "The truncation worst case is declared for S2 only; S3 has none (not declared).",
    "S2 truncation worst case adds back only units whose prints were truncated away (prints unavailable at an S2 time) and that have a history-price v; units with no print in a window but complete trade history are not added (they are not unavailable).",
    "The successor-resolution hold-to-resolution variant of S3 is not computed: the series fetch stores only predecessor outcomes.",
    "A unit with a missing check input (alt origin, publicity, side audit) has that check None, which blocks an advance (unverified is not a pass).",
)

# ---- statistics ---------------------------------------------------------------------------------------------------------------


def mean_gate(v, ways: dict[str, np.ndarray], *, floor: float, alpha: float, small_g_ways: tuple[str, ...] = (), n_boot: int = 0,
              seed: int = D.SEED_BOOT, w=None, sign: int = 1) -> dict:
    """One-sided mean test (p = max over cluster ways, CB2 small-G rule for ``small_g_ways``) plus the core gate: testable, p < alpha, and the
    point estimate on the declared side by at least ``floor``."""
    v = np.asarray(v, float)
    t = CC.mean_test(v, ways, sign=sign, w=w, small_g_ways=small_g_ways, n_boot=n_boot, seed=seed, min_units=D.MIN_UNITS, min_clusters=D.MIN_CLUSTERS)
    mean = float(t.get("mean", math.nan))
    core = bool(t.get("testable") and t["p"] < alpha and np.isfinite(mean) and sign * mean >= floor)
    return {**t, "pass_core": core, "floor": floor, "alpha": alpha, "effect": mean, "sign_tested": sign}


def cluster_equal_mean(v, cl) -> float:
    """Mean of cluster means (every cluster weighs the same)."""
    v = np.asarray(v, float)
    if not len(v):
        return math.nan
    return float(pd.Series(v).groupby(np.asarray(cl).astype(str)).mean().mean())


def top_clusters_dropped(v, ways: dict[str, np.ndarray], *, floor: float, alpha: float, small_g_ways: tuple[str, ...], sign: int = 1, pways=None) -> dict[str, bool]:
    """Section 2.6 (ii): for each declared way, the test still meets its p threshold and floor without the 5 clusters of that way with the
    largest absolute contribution. ``pways`` (A-C1) maps the remaining declared ways to the ways that enter the p max."""
    v = np.asarray(v, float)
    out: dict[str, bool] = {}
    for k, cl in ways.items():
        keep = CC.top_clusters_mask(v, cl, D.TOP_CLUSTERS_DROPPED)
        sub = {a: np.asarray(b)[keep] for a, b in ways.items()}
        out[k] = bool(mean_gate(v[keep], pways(sub) if pways else sub, floor=floor, alpha=alpha, small_g_ways=small_g_ways, sign=sign)["pass_core"])
    return out


def lodo_sign(v, day, sign: int = 1) -> dict:
    """Leave-one-day-out sign rule (CB1 section 2.3, binding at Stage 1 for CH46 dev): the mean keeps the declared sign after dropping any
    single day."""
    v = np.asarray(v, float)
    d = np.asarray(day).astype(str)
    days = sorted(set(d))
    if len(days) < 2:
        return {"ok": False, "n_days": len(days), "reason": "fewer than 2 days"}
    worst = min(sign * float(v[d != x].mean()) if (d != x).any() else math.nan for x in days)
    return {"ok": bool(np.isfinite(worst) and worst > 0), "n_days": len(days), "worst_leave_out": sign * worst}


def placebo_advance_rate(draw, ways: dict[str, np.ndarray], *, floor: float, alpha: float, small_g_ways: tuple[str, ...], draws: int, seed: int,
                         sign: int = 1) -> dict:
    """Section 2.6: run the core gate on ``draws`` placebo value vectors (``draw(rng) -> values``) and report the advance rate; calibrated iff
    the rate is at most 1.5%."""
    rng = np.random.default_rng(seed)
    adv = 0
    for _ in range(draws):
        adv += int(mean_gate(draw(rng), ways, floor=floor, alpha=alpha, small_g_ways=small_g_ways, sign=sign)["pass_core"])
    rate = adv / max(draws, 1)
    return {"n_draws": draws, "n_advanced": adv, "advance_rate": rate, "max_rate": D.PLACEBO_MAX_ADVANCE_RATE, "calibrated": bool(rate <= D.PLACEBO_MAX_ADVANCE_RATE)}


def decide(core: dict, checks: dict[str, bool | None]) -> dict:
    """Advance iff the core gate passes and every check is True. A check that is None (could not be evaluated) blocks: unverified is not a pass."""
    failed = sorted(k for k, v in checks.items() if v is False)
    unverified = sorted(k for k, v in checks.items() if v is None)
    return {"advance": bool(core.get("pass_core") and not failed and not unverified), "failed_checks": failed, "unverified_checks": unverified, "checks": dict(checks)}


def r_ann(net, K, d) -> float:
    """Capital-time ratio 365 sum(net) / sum(K max(d, 1))."""
    net, K, d = np.asarray(net, float), np.asarray(K, float), np.asarray(d, float)
    den = float((K * np.maximum(d, 1.0)).sum())
    return float(365.0 * net.sum() / den) if den > 0 else math.nan


def holm(pvals: dict[str, float], alpha: float) -> dict:
    return CC.holm(pvals, alpha)


# ---- CB4-C: parsing ----------------------------------------------------------------------------------------------------------


def _ep(v) -> float:
    x = cb4_data._parse_ts(v) if v not in ("", None) else None
    return float("nan") if x is None else float(x)


def _flag3(v) -> float:
    """1.0 / 0.0 / nan (blank = unknown)."""
    t = str(v).strip().lower()
    if cb4_data.flag_off(t):
        return 0.0
    return 1.0 if t in ("1", "1.0", "true", "t", "yes") else math.nan


def uma_tokens(v) -> frozenset:
    import re

    return frozenset(re.findall(r"[a-z_]+", str(v or "").lower()))


def parse_closewin(raw: pd.DataFrame) -> pd.DataFrame:
    """Typed copy of a raw-string closewin frame (``cb4_data.read_closewin``) with epochs, tri-state flags and UMA token sets."""
    d = raw.copy()
    for src, dst in (("capture_start_utc", "cap_start"), ("received_utc", "recv"), ("end_date", "e"), ("created_at", "created")):
        d[dst] = [_ep(x) for x in d[src]]
    for c in ("best_bid", "best_ask", "sweep_bid_size_1", "sweep_ask_size_1"):
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d else math.nan
    d["acc"] = d["accepting_orders"].map(_flag3)
    d["closed_f"] = d["closed"].map(_flag3)
    d["ext_ok"] = (d["ext_present"].astype(str) != "0") if "ext_present" in d else True
    d["uma_set"] = d["uma_resolution_statuses"].map(uma_tokens)
    d["market_id"] = d["market_id"].astype(str)
    d["event_id"] = d["event_id"].astype(str)
    return d


def uma_clear(tokens, ext_ok: bool, extra: tuple[str, ...] = ()) -> bool | None:
    """True / False / None (unknown: no sidecar entry for the row)."""
    if not ext_ok:
        return None
    return not (set(tokens) & (set(D.C["uma_block_tokens"]) | set(extra)))


def _is_weather(cat) -> bool:
    return bool(cb4_data.is_weather_market(str(cat or "")))


# ---- CB4-C: C2 population fixed at tau0 -------------------------------------------------------------------------------------


def c2_units_at_tau0(cw: pd.DataFrame, *, uma_extra: tuple[str, ...] = ()) -> tuple[pd.DataFrame, dict]:
    """C2 units (market, token) from capture c alone: ``tau0 = received_utc + 10 min``, ``e`` = end_date recorded at c; accepting true, closed false,
    scheduled life >= 1 day, UMA-clear (known), ``e in (tau0, tau0 + 2h]``, and the token has a recorded bid. A market enters at the first capture
    that qualifies. Nothing after tau0 is read. Weather is excluded and counted; sports are kept with ``sports = True`` (reported stratum)."""
    d = cw.sort_values(["cap_start", "market_id"], kind="stable").copy()
    rep = {"rows": int(len(d)), "weather": 0, "not_accepting": 0, "closed": 0, "life": 0, "uma_not_clear": 0, "uma_unknown": 0, "end_window": 0,
           "no_bid_either": 0, "markets_qualifying": 0, "qualifying_capture_missing": 0}
    d["tau0"] = d["recv"] + D.C["tau0_delay_min"] * 60.0
    wx = d["fee_category"].map(_is_weather).to_numpy()
    rep["weather"] = int(wx.sum())
    d = d[~wx]
    ok = (d["acc"] == 1).to_numpy()
    rep["not_accepting"] = int((~ok).sum())
    cl = (d["closed_f"] == 0).to_numpy()
    rep["closed"] = int((ok & ~cl).sum())
    life = (d["created"] <= d["e"] - D.C["min_life_h"] * HOUR).to_numpy()
    rep["life"] = int((ok & cl & ~life).sum())
    uc = [uma_clear(t, x, uma_extra) for t, x in zip(d["uma_set"], d["ext_ok"], strict=True)]
    rep["uma_not_clear"] = int(sum(1 for a, u in zip(ok & cl & life, uc, strict=True) if a and u is False))
    rep["uma_unknown"] = int(sum(1 for a, u in zip(ok & cl & life, uc, strict=True) if a and u is None))
    umaok = np.array([u is True for u in uc], bool)
    win = ((d["e"] > d["tau0"]) & (d["e"] <= d["tau0"] + D.C["end_within_h"] * HOUR)).to_numpy()
    rep["end_window"] = int((ok & cl & life & umaok & ~win).sum())
    base = d[ok & cl & life & umaok & win]
    rows = []
    for _, r in base.iterrows():
        yes_q, no_q = r["best_bid"], (1.0 - r["best_ask"]) if np.isfinite(r["best_ask"]) else math.nan
        for tok, q in ((0, yes_q), (1, no_q)):
            if np.isfinite(q) and 0.0 < q < 1.0:
                rows.append({"market_id": r["market_id"], "event_id": r["event_id"], "token": tok, "capture_id": r["capture_id"], "cap_start": r["cap_start"],
                             "tau0": r["tau0"], "e": r["e"], "q": float(q), "fee_category": r["fee_category"], "sports": bool(H1.is_sports(r["fee_category"])),
                             "bid_size_1": float(r["sweep_bid_size_1"]) if tok == 0 else float(r["sweep_ask_size_1"])})
    out = pd.DataFrame(rows, columns=["market_id", "event_id", "token", "capture_id", "cap_start", "tau0", "e", "q", "fee_category", "sports", "bid_size_1"])
    if len(out):
        out = out.sort_values(["market_id", "tau0", "token"], kind="stable")
        first = out.groupby("market_id")["tau0"].transform("min")
        out = out[out["tau0"] == first].reset_index(drop=True)
    rep["markets_qualifying"] = int(out["market_id"].nunique()) if len(out) else 0
    # a market whose recorded end fell inside the observed capture span but that never had a qualifying capture
    if len(cw):
        last = cw.sort_values("cap_start").groupby("market_id").tail(1)
        t_lo, t_hi = float(cw["recv"].min()), float(cw["recv"].max())
        inside = last[(last["e"] > t_lo) & (last["e"] <= t_hi)]
        rep["qualifying_capture_missing"] = int((~inside["market_id"].isin(set(out["market_id"])) & (inside["acc"] == 1) & ~inside["fee_category"].map(_is_weather)).sum())
    return out, rep


# ---- CB4-C: flip strata (after the fact) ---------------------------------------------------------------------------------------


def capture_pairs(captures: list[pd.DataFrame]) -> tuple[list[tuple[pd.DataFrame, pd.DataFrame]], dict]:
    """Consecutive complete captures with a start gap in [1.5, 3] h; others are excluded and counted."""
    caps = sorted((c for c in captures if len(c)), key=lambda c: float(c["cap_start"].iloc[0]))
    lo, hi = D.C["gap_h"][0] * HOUR, D.C["gap_h"][1] * HOUR
    pairs, bad = [], 0
    for a, b in zip(caps, caps[1:], strict=False):
        gap = float(b["cap_start"].iloc[0]) - float(a["cap_start"].iloc[0])
        if lo <= gap <= hi:
            pairs.append((a, b))
        else:
            bad += 1
    return pairs, {"n_captures": len(caps), "n_pairs": len(pairs), "pairs_gap_excluded": bad}


def flip_stratum(a_row: pd.Series, b_row: pd.Series | None, in_departures: bool, start_a: float, start_b: float, *, uma_extra: tuple[str, ...] = ()) -> str | None:
    """Stratum of one market over the pair (c_k, c_k+1): S, E, L, P, N, unknown, or None (no event). ``e`` is the end_date recorded at c_k."""
    if a_row["acc"] != 1:
        return None
    e = a_row["e"]
    if b_row is not None:
        flip = bool(b_row["acc"] == 0 and b_row["closed_f"] == 0)
        if not flip:
            return None
        if not np.isfinite(e):
            return "unknown"
        clear_b = uma_clear(b_row["uma_set"], bool(b_row["ext_ok"]), uma_extra)
        if clear_b is None:
            return "unknown"
        if clear_b is False:
            return "P"
        if e > start_b:
            return "E"
        if e <= start_a - D.C["end_within_h"] * HOUR:
            return "L"
        return "S"
    if not in_departures or not np.isfinite(e):
        return None
    clear_a = uma_clear(a_row["uma_set"], bool(a_row["ext_ok"]), uma_extra)
    if clear_a is None:
        return "unknown"
    if clear_a and (start_a - D.C["end_within_h"] * HOUR < e <= start_b):
        return "N"
    return None


def assign_strata(captures: list[pd.DataFrame], departures: dict[str, set[str]], *, uma_extra: tuple[str, ...] = ()) -> tuple[pd.DataFrame, dict]:
    """First stratum per market over all valid pairs (strata are assigned after the fact and never select C2 units). A market that flips more
    than once keeps its first stratum; reopenings are counted. U = no stratum by e + 6h within the observed span."""
    pairs, rep = capture_pairs(captures)
    rep.update({"reopenings": 0, "weather_excluded": 0})
    got: dict[str, dict] = {}
    flipped_at: dict[str, float] = {}
    last_start = max((float(c["cap_start"].iloc[0]) for c in captures if len(c)), default=math.nan)
    seen_e: dict[str, tuple[float, str, str]] = {}
    for a, b in pairs:
        sa, sb = float(a["cap_start"].iloc[0]), float(b["cap_start"].iloc[0])
        dep = departures.get(str(b["capture_id"].iloc[0]), set())
        bidx = b.drop_duplicates("market_id").set_index("market_id", drop=False)
        for _, ar in a.drop_duplicates("market_id").iterrows():
            mid = ar["market_id"]
            if _is_weather(ar["fee_category"]):
                continue
            seen_e[mid] = (ar["e"], ar["event_id"], ar["fee_category"])
            br = bidx.loc[mid] if mid in bidx.index else None
            if mid in got:
                if ar["acc"] == 1 and flipped_at.get(mid, math.inf) < sa:
                    rep["reopenings"] += 1
                continue
            st = flip_stratum(ar, br, mid in dep, sa, sb, uma_extra=uma_extra)
            if st is not None:
                got[mid] = {"market_id": mid, "event_id": ar["event_id"], "stratum": st, "e": ar["e"], "fee_category": ar["fee_category"],
                            "pair_a": ar["capture_id"], "pair_b": b["capture_id"].iloc[0], "start_a": sa, "start_b": sb}
                if st in ("S", "E", "L", "P"):
                    flipped_at[mid] = sb
    for mid, (e, ev, cat) in seen_e.items():
        if mid not in got and np.isfinite(e) and np.isfinite(last_start) and e + 6 * HOUR <= last_start:
            got[mid] = {"market_id": mid, "event_id": ev, "stratum": "U", "e": e, "fee_category": cat, "pair_a": None, "pair_b": None, "start_a": math.nan, "start_b": math.nan}
    out = pd.DataFrame(list(got.values()), columns=["market_id", "event_id", "stratum", "e", "fee_category", "pair_a", "pair_b", "start_a", "start_b"])
    rep["by_stratum"] = {k: int(v) for k, v in out["stratum"].value_counts().items()} if len(out) else {}
    return out, rep


# ---- CB4-C: prints ------------------------------------------------------------------------------------------------------------


@dataclass
class Trades:
    """A market's stored Data API trades and truncation facts (``trades_truncated``, ``trades_oldest_ts``)."""

    df: pd.DataFrame
    truncated: bool = False
    oldest_ts: float | None = None

    def window_available(self, a: float) -> bool:
        """A window starting at ``a`` is fully covered iff the market is not truncated or ``a`` is not before the oldest stored trade."""
        return (not self.truncated) or (a >= H1.oldest_or_inf(self.oldest_ts))


def window_prints(tr: Trades, token: int, side: str, a: float, b: float) -> dict:
    """Same-token taker prints of ``side`` with ``a <= ts < b``: prices and sizes, and availability (truncation rule)."""
    df = tr.df
    if df is None or not len(df):
        px = np.array([])
        sz = np.array([])
    else:
        m = (df["side"].astype(str).str.upper() == side) & (df["outcome_index"].astype(int) == int(token)) & (df["ts"] >= a) & (df["ts"] < b)
        px, sz = df.loc[m, "price"].to_numpy(float), df.loc[m, "size"].to_numpy(float)
    return {"price": px, "size": sz, "n": int(len(px)), "available": tr.window_available(a)}


def _wmean(px: np.ndarray, sz: np.ndarray) -> float:
    return float((px * sz).sum() / sz.sum()) if len(px) and sz.sum() > 0 else math.nan


def c1_units(strata_s: pd.DataFrame, trades: dict[str, Trades], *, side: str = "SELL") -> tuple[pd.DataFrame, dict]:
    """C1 units: (market, token) of stratum S with same-token ``side`` prints in both windows. ``delta = p_B - p_F`` (print-equal mean prices; Y cancels).
    Windows are scheduled, from ``e``: W_F = [e - 2h, e), W_B = [e - 26h, e - 24h). Truncated windows are unavailable and reported; baseline-unavailable
    candidates are returned for the truncation worst case."""
    rows, rep = [], {"markets": int(len(strata_s)), "no_trades_file": 0, "no_final_prints": 0, "no_baseline_prints": 0, "final_unavailable": 0,
                     "baseline_unavailable": 0, "units": 0}
    cand_bu = 0
    for _, r in strata_s.iterrows():
        tr = trades.get(r["market_id"])
        if tr is None:
            rep["no_trades_file"] += 1
            continue
        e = float(r["e"])
        for tok in (0, 1):
            f = window_prints(tr, tok, side, e - D.C["W_F_h"][0] * HOUR, e - D.C["W_F_h"][1] * HOUR)
            b = window_prints(tr, tok, side, e - D.C["W_B_h"][0] * HOUR, e - D.C["W_B_h"][1] * HOUR)
            if not f["available"]:
                rep["final_unavailable"] += 1
                continue
            if f["n"] == 0:
                rep["no_final_prints"] += 1
                continue
            if not b["available"]:
                rep["baseline_unavailable"] += 1
                cand_bu += 1
                continue
            if b["n"] == 0:
                rep["no_baseline_prints"] += 1
                continue
            pf, pb = float(f["price"].mean()), float(b["price"].mean())
            pfw, pbw = _wmean(f["price"], f["size"]), _wmean(b["price"], b["size"])
            rows.append({"market_id": r["market_id"], "event_id": r["event_id"], "token": tok, "e": e, "fee_category": r["fee_category"],
                         "p_f": pf, "p_b": pb, "delta": pb - pf, "delta_w": pbw - pfw, "n_f": f["n"], "n_b": b["n"],
                         "e_day": datetime.fromtimestamp(e, UTC).date().isoformat(), "week_e": H1.iso_week(e),
                         "cell": f"{r['fee_category']}|{datetime.fromtimestamp(e, UTC).date().isoformat()}|{int((e % DAY) // (6 * HOUR))}"})
    out = pd.DataFrame(rows, columns=["market_id", "event_id", "token", "e", "fee_category", "p_f", "p_b", "delta", "delta_w", "n_f", "n_b", "e_day", "week_e", "cell"])
    rep["units"] = int(len(out))
    rep["baseline_unavailable_candidates"] = cand_bu
    return out, rep


def token_balanced(units: pd.DataFrame) -> pd.DataFrame:
    """Markets with same-token prints on BOTH tokens in both windows: the mean of the two token deltas (YES and NO drifts cancel)."""
    if not len(units):
        return units
    g = units.groupby("market_id")
    both = g["token"].nunique() == 2
    ids = set(both[both].index)
    sub = units[units["market_id"].isin(ids)]
    return sub.groupby("market_id").agg(delta=("delta", "mean"), event_id=("event_id", "first"), week_e=("week_e", "first"), e_day=("e_day", "first")).reset_index()


def matched_sn_contrast(s_units: pd.DataFrame, n_units: pd.DataFrame, *, n_boot: int = D.N_BOOT, seed: int = D.SEED_BOOT) -> dict:
    """``Delta_SN = sum_c w_c (mean_{S,c} - mean_{N,c})`` over cells (fee_category x UTC date of e x 6h block of e); w_c = the cell's share of S units;
    cells lacking either class are dropped and counted. 90% CI from a bootstrap that resamples S units by event and N units by exact end timestamp within
    cells (instant closes resolve in batches)."""
    cells = sorted(set(s_units["cell"]) & set(n_units["cell"])) if len(s_units) and len(n_units) else []
    dropped = (sorted(set(s_units["cell"]) - set(cells)) if len(s_units) else [])
    if not cells:
        return {"delta_sn": math.nan, "ci90": [math.nan, math.nan], "n_cells": 0, "cells_dropped": len(dropped), "credit_stage1": False, "credit_stage2": False}
    w_tot = float(s_units["cell"].isin(cells).sum())
    parts = []
    for c in cells:
        s = s_units[s_units["cell"] == c]
        n = n_units[n_units["cell"] == c]
        sg = s.groupby("event_id")["delta"].agg(["sum", "count"]).to_numpy(float)
        ng = n.groupby(n["e"].round(0))["delta"].agg(["sum", "count"]).to_numpy(float)
        parts.append((len(s) / w_tot, sg, ng))
    est = float(sum(w * (sg[:, 0].sum() / sg[:, 1].sum() - ng[:, 0].sum() / ng[:, 1].sum()) for w, sg, ng in parts))
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        tot = 0.0
        for w, sg, ng in parts:
            si, ni = rng.integers(0, len(sg), len(sg)), rng.integers(0, len(ng), len(ng))
            ds, dn = sg[si, 1].sum(), ng[ni, 1].sum()
            tot += w * ((sg[si, 0].sum() / ds if ds > 0 else 0.0) - (ng[ni, 0].sum() / dn if dn > 0 else 0.0))
        bs[i] = tot
    lo, hi = (float(x) for x in np.percentile(bs, [5, 95]))
    return {"delta_sn": est, "ci90": [lo, hi], "n_cells": len(cells), "cells_dropped": len(dropped), "credit_stage1": bool(est > 0), "credit_stage2": bool(lo > 0)}


def side_audit_two_sided(prints: pd.DataFrame, quotes: pd.DataFrame) -> dict:
    """Pre-freeze two-sided trade-side audit per token (census). ``prints``: market_id, ts, side, price, outcome_index. ``quotes``: parsed closewin
    rows (market_id, recv, best_bid, best_ask). A print is matched to the market's capture received within 10 minutes (the nearest) with a two-sided
    touch; the reference is the token's mid (YES mid, or 1 - YES mid for NO). Four shares: SELL at or below mid and BUY at or above mid, for YES and NO.
    Passes iff all four have prints and are >= 80%."""
    q = quotes[np.isfinite(quotes["best_bid"]) & np.isfinite(quotes["best_ask"])]
    qm = {m: g.sort_values("recv") for m, g in q.groupby("market_id")}
    cnt = {(t, s): [0, 0] for t in (0, 1) for s in ("SELL", "BUY")}
    win = D.C["side_audit_window_min"] * 60.0
    for m, g in prints.groupby("market_id"):
        qq = qm.get(str(m))
        if qq is None:
            continue
        rv = qq["recv"].to_numpy(float)
        mid_yes = ((qq["best_bid"] + qq["best_ask"]) / 2.0).to_numpy(float)
        for ts, side, px, oi in zip(g["ts"].to_numpy(float), g["side"].astype(str).str.upper(), g["price"].to_numpy(float), g["outcome_index"].astype(int), strict=True):
            j = int(np.argmin(np.abs(rv - ts)))
            if abs(rv[j] - ts) > win or side not in ("SELL", "BUY"):
                continue
            ref = mid_yes[j] if oi == 0 else 1.0 - mid_yes[j]
            ok = (px <= ref + 1e-12) if side == "SELL" else (px >= ref - 1e-12)
            c = cnt[(oi, side)]
            c[0] += int(ok)
            c[1] += 1
    shares = {f"{'YES' if t == 0 else 'NO'}_{s}": (c[0] / c[1] if c[1] else math.nan) for (t, s), c in cnt.items()}
    ns = {f"{'YES' if t == 0 else 'NO'}_{s}": c[1] for (t, s), c in cnt.items()}
    ok = all(ns[k] > 0 and shares[k] >= D.C["side_audit_min_share"] for k in shares)
    return {"shares": shares, "n": ns, "min_share": D.C["side_audit_min_share"], "ok": bool(ok)}


def g46_gate(c1: pd.DataFrame, c2: pd.DataFrame, dev_days: float) -> dict:
    """Gate G46 (census): >= 50 C1 units per week from >= 30 events, averaged over the dev window, and >= 100 C2 units per week."""
    weeks = max(dev_days / 7.0, 1e-9)
    n1, ne = len(c1), (int(c1["event_id"].nunique()) if len(c1) else 0)
    n2 = len(c2)
    ok = (n1 / weeks >= D.C["g46_c1_units_per_week"]) and ne >= D.C["g46_c1_events"] and (n2 / weeks >= D.C["g46_c2_units_per_week"])
    return {"c1_units_per_week": n1 / weeks, "c1_events": ne, "c2_units_per_week": n2 / weeks, "ok": bool(ok), "weeks": weeks}


# ---- CB4-C: C2 paper bids ---------------------------------------------------------------------------------------------------


def c2_paper_bids(units: pd.DataFrame, trades: dict[str, Trades], *, optimistic: bool = False) -> pd.DataFrame:
    """Paper bid of 10 shares at the recorded touch ``q`` posted at tau0. Filled at q only on a trade-through: the first taker-sell print on the token at a
    price strictly below q in [tau0, e) (optimistic variant: at or below q). ``fill_state``: 1 filled, 0 known not filled, -1 final window unavailable."""
    rows = []
    for _, u in units.iterrows():
        tr = trades.get(u["market_id"])
        st, tf, pf, sf = -1, math.nan, math.nan, math.nan
        if tr is not None:
            wp = tr.df
            if wp is not None and len(wp):
                m = (wp["side"].astype(str).str.upper() == "SELL") & (wp["outcome_index"].astype(int) == int(u["token"])) & (wp["ts"] >= u["tau0"]) & (wp["ts"] < u["e"])
                m &= (wp["price"] <= u["q"] + 1e-12) if optimistic else (wp["price"] < u["q"] - 1e-12)
                hit = wp[m].sort_values("ts")
            else:
                hit = pd.DataFrame()
            if len(hit):
                st, tf, pf, sf = 1, float(hit["ts"].iloc[0]), float(hit["price"].iloc[0]), float(hit["size"].iloc[0])
            else:
                st = 0 if tr.window_available(float(u["tau0"])) else -1
        rows.append({**u.to_dict(), "fill_state": st, "t_fill": tf, "fill_price": pf, "fill_size": sf})
    return pd.DataFrame(rows)


def attach_c2_outcomes(bids: pd.DataFrame, outcomes: dict[str, dict], last_bid: dict[tuple[str, int], float], censor_mark: float) -> pd.DataFrame:
    """Filled bids with ``Y_j`` (50-50 pays 0.5). ``outcomes[market_id] = {"y0": float|None, "closed_time": epoch|nan}``. Unresolved or undecided:
    censored, valued at the last recorded bid of the side held (``last_bid``), flagged. ``net = Y_j - q`` per filled share, ``K = q``, hold to closed_time
    (or the censoring mark); ``week`` is the ISO week (reported) and ``close_day`` the UTC date (A-C1 cluster way) of closed_time or the mark."""
    f = bids[bids["fill_state"] == 1].copy()
    ys, cens, ct = [], [], []
    for _, r in f.iterrows():
        o = outcomes.get(r["market_id"]) or {}
        y0 = o.get("y0")
        if y0 is None or not np.isfinite(y0 if y0 is not None else math.nan):
            ys.append(last_bid.get((r["market_id"], int(r["token"])), math.nan))
            cens.append(True)
            ct.append(censor_mark)
        else:
            ys.append(float(y0) if int(r["token"]) == 0 else 1.0 - float(y0))
            cens.append(False)
            c = o.get("closed_time", math.nan)
            ct.append(float(c) if c is not None and np.isfinite(c) else censor_mark)
    f["Y"], f["censored"], f["close_t"] = ys, cens, ct
    # a censored fill with no recorded bid of the side held cannot be valued: it is counted unavailable (c2_test drops it from the estimate and adds
    # it back as a filled loser in the truncation worst case), never carried as a silent NaN
    f["unavailable_censored"] = f["censored"] & ~np.isfinite(f["Y"].astype(float))
    f["net"] = f["Y"] - f["q"]
    f["K"] = f["q"]
    f["d"] = np.maximum((f["close_t"] - f["t_fill"]) / DAY, 0.0)
    f["week"] = [H1.iso_week(x) for x in f["close_t"]] if len(f) else []
    f["close_day"] = [datetime.fromtimestamp(x, UTC).date().isoformat() for x in f["close_t"]] if len(f) else []
    f["w_size"] = np.minimum(f["fill_size"], D.C["paper_size"])
    return f


def censored_sensitivity(f: pd.DataFrame) -> dict:
    """Censored fills valued at 0 and at 1; above 5% censored the verdict carries 'resolution-lag sensitive'."""
    if not len(f):
        return {"censored_share": 0.0, "resolution_lag_sensitive": False}
    sh = float(f["censored"].mean())
    sens = {f"censored_at_{int(cv)}": float(np.where(f["censored"], cv - f["q"], f["net"]).mean()) for cv in (0.0, 1.0)}
    return {"censored_share": sh, "resolution_lag_sensitive": bool(sh > D.C["censored_sensitive_share"]), **sens}


def truncation_worst_case_c(c1: pd.DataFrame, n_c1_baseline_unavailable: int, c2_filled: pd.DataFrame, bids: pd.DataFrame) -> dict:
    """Binding (2.6 (v)): C1 units with an unavailable baseline are added back with delta = the 10th percentile of observed delta; C2 tokens whose final
    window is unavailable are added as filled losers (net = -q). Returns the worst-case means; both must stay > 0."""
    out: dict = {}
    if len(c1):
        p10 = float(np.percentile(c1["delta"], 10))
        v = np.concatenate([c1["delta"].to_numpy(float), np.full(int(n_c1_baseline_unavailable), p10)])
        out["C1"] = {"mean": float(v.mean()), "added": int(n_c1_baseline_unavailable), "ok": bool(v.mean() > 0)}
    un = bids[bids["fill_state"] == -1]
    if len(c2_filled) or len(un):
        v = np.concatenate([c2_filled["net"].to_numpy(float), -un["q"].to_numpy(float)]) if len(un) else c2_filled["net"].to_numpy(float)
        out["C2"] = {"mean": float(v.mean()) if len(v) else math.nan, "added": int(len(un)), "ok": bool(len(v) and v.mean() > 0)}
    return out


# ---- CB4-C: tests -----------------------------------------------------------------------------------------------------------


C_SMALL_G = ("day",)
C_TIME_WAY = "day"


def c_pways(ways: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Amendment A-C1: the ways that enter the C1/C2 p max. The event way always; the UTC-day way under the section 2.3 small-G rule iff it has
    >= G_MIN (15) clusters. With fewer days no cluster-robust p is valid for that way, so it does not enter and the caller makes the leave-one-day-out
    sign rule binding instead (never 'not testable' for the whole test because of the calendar length)."""
    g = CC.n_clusters({C_TIME_WAY: ways[C_TIME_WAY]})[C_TIME_WAY]
    return dict(ways) if g >= D.G_MIN else {k: x for k, x in ways.items() if k != C_TIME_WAY}


def sign_by_week(v, week) -> dict[str, int]:
    """Reported only (A-C1): sign of the mean per ISO week."""
    s = pd.Series(np.asarray(v, float)).groupby(np.asarray(week).astype(str)).mean()
    return {str(k): int(np.sign(x)) for k, x in s.items()}


def _ways_c1(u: pd.DataFrame) -> dict[str, np.ndarray]:
    return {"event": u["event_id"].to_numpy(str), "day": u["e_day"].to_numpy(str)}


def c1_test(c1: pd.DataFrame, n_units: pd.DataFrame, *, stage: int, n_boot: int, placebo_draws: int, wb_added: int, seed: int = D.SEED_BOOT,
            lodo: bool = True, c1_buy: pd.DataFrame | None = None) -> dict:
    """C1 (mechanism): mean of ``delta`` (cents as price units) > 0; p = max over event and (A-C1) the UTC day of e when G_day >= 15. Binding: floor 1.0c,
    S - N attribution, top-5 clusters (events, days), cluster-equal and size-weighted sign agreement, truncation worst case, placebo (sign flip), LODO at Stage 1
    and at any stage where the day way does not enter."""
    alpha = D.ALPHA_STAGE1_ROUTE if stage == 1 else D.ALPHA_STAGE2
    if not len(c1):
        return {"testable": False, "p": 1.0, "n": 0, "advance": False, "effect": math.nan, "reason": ["no units"]}
    ways = _ways_c1(c1)
    pw = c_pways(ways)
    v = c1["delta"].to_numpy(float)
    core = mean_gate(v, pw, floor=D.FLOORS["C1"], alpha=alpha, small_g_ways=C_SMALL_G, n_boot=n_boot, seed=seed)
    sn = matched_sn_contrast(c1, n_units, n_boot=n_boot or 200, seed=seed + 1) if len(n_units) else matched_sn_contrast(c1.iloc[:0], n_units, n_boot=1)
    checks: dict[str, bool | None] = {}
    tc = top_clusters_dropped(v, ways, floor=D.FLOORS["C1"], alpha=alpha, small_g_ways=C_SMALL_G, pways=c_pways)
    checks.update({f"top5_dropped_{k}": x for k, x in tc.items()})
    checks["cluster_equal_sign"] = CC.sign_agree(core["effect"], cluster_equal_mean(v, ways["event"]))
    checks["size_weighted_sign"] = CC.sign_agree(core["effect"], float(c1["delta_w"].mean()))
    wc = np.concatenate([v, np.full(int(wb_added), float(np.percentile(v, 10)))])
    checks["truncation_worst_case"] = bool(wc.mean() > 0)
    checks["attribution_S_minus_N"] = bool(sn["credit_stage1"] if stage == 1 else sn["credit_stage2"])
    day_in = C_TIME_WAY in pw
    if (stage == 1 and lodo) or not day_in:
        checks["lodo_sign"] = lodo_sign(v, c1["e_day"].to_numpy(str))["ok"]
    pl = placebo_advance_rate(lambda rng: v * rng.choice([-1.0, 1.0], len(v)), pw, floor=D.FLOORS["C1"], alpha=alpha, small_g_ways=C_SMALL_G, draws=D.PLACEBO_DRAWS, seed=seed + 2) if placebo_draws else {"calibrated": False, "n_draws": 0}
    checks["placebo_calibrated"] = bool(pl["calibrated"]) if pl.get("n_draws") else None
    dec = decide(core, checks)
    buy = None
    if c1_buy is not None and len(c1_buy):
        buy = float(c1_buy["delta"].mean())
    return {**{k: core.get(k) for k in ("p", "n", "testable", "effect", "ci95", "p_by_way", "clusters", "reason")}, **dec, "floor": D.FLOORS["C1"], "alpha": alpha, "stage": stage,
            "matched_sn": sn, "placebo": pl, "placebo_status": "calibrated" if pl.get("calibrated") else "miscalibrated", "reported": {"buy_print_delta": buy,
            "token_balanced_mean": (lambda t: float(t["delta"].mean()) if len(t) else None)(token_balanced(c1)), "sign_by_iso_week": sign_by_week(v, c1["week_e"])},
            "time_way": "utc_day_small_g" if day_in else "lodo_binding (G_day < 15)", "g_day": CC.n_clusters({"d": ways[C_TIME_WAY]})["d"],
            "label": "late-life seller discount, not the order stop" if (core["pass_core"] and not checks["attribution_S_minus_N"]) else None}


def c2_test(filled: pd.DataFrame, all_bids: pd.DataFrame, *, stage: int, n_boot: int, placebo_draws: int, seed: int = D.SEED_BOOT, lodo: bool = True) -> dict:
    """C2 (economic): mean ``net = Y_j - q`` per filled share > 0; p = max over event and (A-C1) the UTC day of closed_time (or the censoring mark)
    when G_day >= 15. Binding: floor 1.0c and R_ann >= 10%, +0.75c on q, top-5 clusters, cluster-equal and size-weighted sign, truncation worst case, break-even placebo Y ~ Bern(q), LODO."""
    alpha = D.ALPHA_STAGE1_ROUTE if stage == 1 else D.ALPHA_STAGE2
    n_unavail_cens = 0
    if len(filled) and "unavailable_censored" in filled.columns and filled["unavailable_censored"].any():
        bad = filled[filled["unavailable_censored"]]
        n_unavail_cens = int(len(bad))
        keys = set(zip(bad["market_id"], bad["token"].astype(int), strict=True))
        all_bids = all_bids.copy()
        mark = [(m, int(t)) in keys and st == 1 for m, t, st in zip(all_bids["market_id"], all_bids["token"], all_bids["fill_state"], strict=True)]
        all_bids.loc[mark, "fill_state"] = -1
        filled = filled[~filled["unavailable_censored"]]
    if not len(filled):
        return {"testable": False, "p": 1.0, "n": 0, "advance": False, "effect": math.nan, "reason": ["no filled bids"], "fill_rate": 0.0,
                "censored_unavailable": n_unavail_cens}
    ways = {"event": filled["event_id"].to_numpy(str), "day": filled["close_day"].to_numpy(str)}
    pw = c_pways(ways)
    v = filled["net"].to_numpy(float)
    core = mean_gate(v, pw, floor=D.FLOORS["C2"], alpha=alpha, small_g_ways=C_SMALL_G, n_boot=n_boot, seed=seed)
    ra = r_ann(v, filled["K"], filled["d"])
    checks: dict[str, bool | None] = {"r_ann_min": bool(np.isfinite(ra) and ra >= D.R_ANN_MIN)}
    checks["cost_plus_0.75c"] = bool((v - D.COST_SENS_C).mean() > 0)
    tc = top_clusters_dropped(v, ways, floor=D.FLOORS["C2"], alpha=alpha, small_g_ways=C_SMALL_G, pways=c_pways)
    checks.update({f"top5_dropped_{k}": x for k, x in tc.items()})
    checks["cluster_equal_sign"] = CC.sign_agree(core["effect"], cluster_equal_mean(v, ways["event"]))
    checks["size_weighted_sign"] = CC.sign_agree(core["effect"], _wmean(v, filled["w_size"].to_numpy(float)))
    wc = truncation_worst_case_c(pd.DataFrame(), 0, filled, all_bids)
    checks["truncation_worst_case"] = bool(wc.get("C2", {}).get("ok"))
    day_in = C_TIME_WAY in pw
    if (stage == 1 and lodo) or not day_in:
        e_day = pd.to_datetime(filled["e"], unit="s", utc=True).dt.strftime("%Y-%m-%d").to_numpy(str)
        checks["lodo_sign"] = lodo_sign(v, e_day)["ok"]
    q = filled["q"].to_numpy(float)
    pl = placebo_advance_rate(lambda rng: (rng.random(len(q)) < q).astype(float) - q, pw, floor=D.FLOORS["C2"], alpha=alpha, small_g_ways=C_SMALL_G, draws=D.PLACEBO_DRAWS, seed=seed + 3) if placebo_draws else {"calibrated": False, "n_draws": 0}
    checks["placebo_calibrated"] = bool(pl["calibrated"]) if pl.get("n_draws") else None
    dec = decide(core, checks)
    n_all = int((all_bids["fill_state"] >= 0).sum()) if len(all_bids) else 0
    return {**{k: core.get(k) for k in ("p", "n", "testable", "effect", "ci95", "p_by_way", "clusters", "reason")}, **dec, "floor": D.FLOORS["C2"], "alpha": alpha, "stage": stage,
            "r_ann": ra, "fill_rate": float(len(filled) / n_all) if n_all else math.nan, "placebo": pl, "placebo_status": "calibrated" if pl.get("calibrated") else "miscalibrated",
            "truncation_worst_case": wc.get("C2"), "censoring": censored_sensitivity(filled), "censored_unavailable": n_unavail_cens,
            "time_way": "utc_day_small_g" if day_in else "lodo_binding (G_day < 15)", "g_day": CC.n_clusters({"d": ways[C_TIME_WAY]})["d"],
            "reported": {"sign_by_iso_week": sign_by_week(v, filled["week"]) if "week" in filled.columns else {}}}


# ---- CB4-S: wrappers for the data-module rules --------------------------------------------------------------------------------


def cadence_class(end_dates: list[float]) -> str | None:
    return cb4_data.cadence_class(end_dates)


def rolled_into_side(succ: dict, pred: dict, key: str):
    return cb4_data.match_side(succ, pred, key)


def split_h7s(units: list[dict]) -> dict:
    """SEALED-H7S: uses ``t0`` dates only; no price, trade or outcome file is opened."""
    return cb4_data.split_h7s(units)


def drop_era_overlap(units: list[dict], era_market_ids: set[str]):
    return cb4_data.drop_era_overlap(units, era_market_ids)


# ---- CB4-S: successor data and print series ----------------------------------------------------------------------------------


@dataclass
class SuccData:
    """One roll unit's successor data in the rolled-into token's terms (trades already mapped; see ``map_trades_to_token``)."""

    unit_id: str
    series_id: str
    cadence: str
    category: str
    sports: bool
    t0: float
    pred_end: float
    succ_created: float
    succ_end: float
    M: float  # seconds after the origin
    V: float
    ts: np.ndarray  # history price stamps
    vals: np.ndarray
    tr_ts: np.ndarray
    tr_buy: np.ndarray  # True = taker buys the rolled-into token
    tr_px: np.ndarray  # price in rolled-into token terms
    tr_size: np.ndarray
    truncated: bool = False
    oldest_ts: float | None = None
    covers_t0: bool = True
    covers_alt: bool = True
    extra: dict = field(default_factory=dict)

    @property
    def t0_alt(self) -> float:
        return self.pred_end + HOUR

    @property
    def prints_available(self) -> bool:
        """CREATIVE_BATCH_4.md section CB4-S: a successor truncated with its oldest stored trade after ``t0' - 3h`` (``t0'`` = the pseudo-origin) has unavailable
        prints for the whole unit (counted; the history-price series still exists and feeds the truncation worst case)."""
        return (not self.truncated) or (H1.oldest_or_inf(self.oldest_ts) <= pseudo_origin(self.t0, self.V) - cb4_data.PRICE_PRE_H * HOUR)

    def trunc_ok(self, origin: float) -> bool:  # noqa: ARG002 - kept for callers; the rule is unit-level
        return self.prints_available


def map_trades_to_token(trades: pd.DataFrame, k: int) -> tuple[np.ndarray, ...]:
    """Map a market's trades to the rolled-into token ``k`` (0 or 1): a BUY of outcome k or a SELL of the other outcome buys it; price p if the print is
    on outcome k else 1 - p. Returns (ts, buy, px, size) sorted by ts."""
    if trades is None or not len(trades):
        e = np.array([])
        return e, e.astype(bool), e, e
    oi = trades["outcome_index"].astype(int).to_numpy()
    buy_raw = trades["side"].astype(str).str.upper().to_numpy() == "BUY"
    on = oi == int(k)
    buy = np.where(on, buy_raw, ~buy_raw)
    px = np.where(on, trades["price"].to_numpy(float), 1.0 - trades["price"].to_numpy(float))
    ts, sz = trades["ts"].to_numpy(float), trades["size"].to_numpy(float)
    o = np.argsort(ts, kind="stable")
    return ts[o], buy[o], px[o], sz[o]


def print_price(sd: SuccData, tau: float, buy: bool = True) -> float:
    """VWAP of taker-buy (or taker-sell) prints on the rolled-into token in [tau - 60 min, tau); NaN if none or unavailable (truncation)."""
    a = tau - 60 * 60.0
    if not sd.prints_available or (sd.truncated and a < H1.oldest_or_inf(sd.oldest_ts)):
        return math.nan
    m = (sd.tr_ts >= a) & (sd.tr_ts < tau) & (sd.tr_buy == buy)
    return _wmean(sd.tr_px[m], sd.tr_size[m])


def hist_price(sd: SuccData, tau: float) -> float:
    """History price of the rolled-into token usable at tau (stamp + 600 s < tau, at most 2h old)."""
    if not len(sd.ts):
        return math.nan
    return float(H1.asof_quote(sd.ts, sd.vals, np.array([tau]))[0])


def pseudo_origin(t0: float, V: float) -> float:
    """``t0' = t0 - (V_end - t0) - 6h``: the placebo origin whose own V window ends 6h before the roll."""
    return t0 - V - cb4_data.PSEUDO_GAP_H * HOUR


def prints_truncated_away(sd: SuccData, origin: float) -> bool:
    """The rolled-into prints needed by S2 at ``origin`` (windows ending at ``origin + |M|`` and ``origin + V_end``) are unavailable because the trade history
    was truncated (unit-level rule, or a window starting before the oldest stored trade). Not the same as 'no print in the window'."""
    if not sd.prints_available:
        return True
    return bool(sd.truncated and (origin + sd.M - 60 * 60.0) < H1.oldest_or_inf(sd.oldest_ts))


def s2_value(sd: SuccData, origin: float, kind: str = "ask") -> dict:
    """``-v`` at an origin, where ``v = X(V_end) - X(origin + |M|)`` for X = P_A (ask), P_B (bid prints) or the history price; plus S1 = X(origin + |M|) - X(origin)."""
    tm, tv = origin + sd.M, origin + sd.V
    if kind == "hist":
        x0, xm, xv = hist_price(sd, origin), hist_price(sd, tm), hist_price(sd, tv)
    else:
        buy = kind == "ask"
        x0, xm, xv = print_price(sd, origin, buy), print_price(sd, tm, buy), print_price(sd, tv, buy)
    return {"neg_v": -(xv - xm) if np.isfinite(xv) and np.isfinite(xm) else math.nan, "s1": (xm - x0) if np.isfinite(xm) and np.isfinite(x0) else math.nan}


def unit_eligible(sd: SuccData, origin: float, *, alt: bool = False) -> tuple[bool, str]:
    """Horizon rule (successor endDate >= V_end + 2h), creation lag and history coverage. Truncation is not an exclusion (see ``prints_available``)."""
    if sd.succ_end < origin + sd.V + 2 * HOUR:
        return False, "succ_end_before_horizon"
    if sd.succ_created > origin - cb4_data.SUCC_CREATED_LAG_H * HOUR:
        return False, "succ_created_too_late"
    if not (sd.covers_alt if alt else sd.covers_t0):
        return False, "history_not_covering_window"
    return True, "ok"  # truncation does not drop the unit: P_A is missing and the unit is added back in the worst case (section 2.6 (v))


def s3_at_origin(sd: SuccData, origin: float, *, cost_add: float = 0.0) -> dict:
    """Paper maker ask posted at origin + 10 min at ``q = min(p(origin) + h(p(origin)) + 1c, 0.99)`` (CB1 band-table h); filled at q only on a
    trade-through (a taker-buy print strictly above q in (origin + 10 min, origin + |M|]); exit buys back at V_end at ``a_x = min(p_x + h(p_x), 0.999)``
    with the cost-regime half-spread and fee; ``net = q - a_x - f(a_x) - a_AS`` (pre-rollout fills) ``- cost_add``; ``K = 1 - q``; hold ``max((V_end - fill)/1d, 1)``."""
    p0 = hist_price(sd, origin)
    if not np.isfinite(p0):
        return {"state": "no_quote"}
    q = min(p0 + H1.half_spread(p0) + 0.01, 0.99)
    a = origin + D.S["S3"]["post_min"] * 60.0
    b = origin + sd.M
    if not sd.prints_available or (sd.truncated and a < H1.oldest_or_inf(sd.oldest_ts)):
        return {"state": "unavailable", "q": q}
    m = (sd.tr_ts > a) & (sd.tr_ts <= b) & sd.tr_buy & (sd.tr_px > q + 1e-12)
    if not m.any():
        return {"state": "not_filled", "q": q}
    t_fill = float(sd.tr_ts[m][0])
    tv = origin + sd.V
    px = hist_price(sd, tv)
    if not np.isfinite(px):
        return {"state": "no_exit_price", "q": q, "t_fill": t_fill}
    day = datetime.fromtimestamp(origin, UTC).date()
    reg = cost_regimes.cost_regime(day, sd.category, price=px)
    ax = min(px + reg["half_spread"], 0.999)
    fee = H1.taker_fee_ps(ax, reg["fee_rate"])
    a_as = reg["a_as_cents"] / 100.0  # R2: nonzero only for fills before the category's rollout date, and only if the register adopted E2
    net = q - ax - fee - a_as - cost_add
    return {"state": "filled", "q": q, "t_fill": t_fill, "a_x": ax, "fee": fee, "net": net, "K": 1.0 - q, "d": max((tv - t_fill) / DAY, 1.0), "a_as": a_as}


# ---- CB4-S: census checks (shares only) -------------------------------------------------------------------------------------


def t0_publicity_check(pred_trades_ts: dict[str, np.ndarray], pred_prices: dict[str, tuple[np.ndarray, np.ndarray]], t0: dict[str, float],
                       truncated: dict[str, bool] | None = None) -> dict:
    """Pre-freeze census: share of SCREEN predecessors with (a) no trade after ``t0`` and (b) a history price usable at ``t0 + 10 min`` within 0.02 of 0 or
    1 (the winning token's price converges). Reads trades and prices only, never ``outcomePrices``; shares only. Either share below 95% stops CB4-S."""
    n = len(t0)
    no_trade = conv = 0
    for u, t in t0.items():
        tr = pred_trades_ts.get(u)
        no_trade += int(tr is not None and not (np.asarray(tr, float) > t).any())
        pp = pred_prices.get(u)
        if pp is not None and len(pp[0]):
            x = float(H1.asof_quote(pp[0], pp[1], np.array([t + D.S["publicity_after_min"] * 60.0]))[0])
            conv += int(np.isfinite(x) and (x <= D.S["publicity_converged_within"] or x >= 1.0 - D.S["publicity_converged_within"]))
    s_a, s_b = (no_trade / n if n else math.nan), (conv / n if n else math.nan)
    ok = bool(n > 0 and s_a >= D.S["publicity_min_share"] and s_b >= D.S["publicity_min_share"])
    return {"n": n, "share_no_trade_after_t0": s_a, "share_price_converged": s_b, "min_share": D.S["publicity_min_share"], "ok": ok}


def side_audit_history(units: list[SuccData], raw_trades: dict[str, pd.DataFrame], k_by_unit: dict[str, int]) -> dict:
    """h7 side audit (census): per print outcome (YES = 0, NO = 1) the share of BUY prints at or above and SELL prints at or below the as-of history price
    (usable at the trade time, <= 2h old) of that outcome's token. Each of the four shares must be >= 75%."""
    cnt = {(o, s): [0, 0] for o in (0, 1) for s in ("BUY", "SELL")}
    for sd in units:
        tr = raw_trades.get(sd.unit_id)
        if tr is None or not len(tr):
            continue
        k = k_by_unit[sd.unit_id]
        ref_k = H1.asof_quote(sd.ts, sd.vals, tr["ts"].to_numpy(float)) if len(sd.ts) else np.full(len(tr), np.nan)
        for oi, side, px, rk in zip(tr["outcome_index"].astype(int), tr["side"].astype(str).str.upper(), tr["price"].to_numpy(float), ref_k, strict=True):
            if not np.isfinite(rk) or side not in ("BUY", "SELL"):
                continue
            ref = rk if oi == k else 1.0 - rk
            c = cnt[(oi, side)]
            c[0] += int(px >= ref - 1e-12) if side == "BUY" else int(px <= ref + 1e-12)
            c[1] += 1
    shares = {f"{'YES' if o == 0 else 'NO'}_{s}": (c[0] / c[1] if c[1] else math.nan) for (o, s), c in cnt.items()}
    ns = {f"{'YES' if o == 0 else 'NO'}_{s}": c[1] for (o, s), c in cnt.items()}
    ok = all(ns[x] > 0 and shares[x] >= D.S["h7_side_audit_min_share"] for x in shares)
    return {"shares": shares, "n": ns, "min_share": D.S["h7_side_audit_min_share"], "ok": bool(ok)}


def print_available(sd: SuccData, tau: float, buy: bool = True) -> bool:
    """Census availability: at least one taker-buy (or sell) print on the rolled-into token in ``[tau - 60 min, tau)`` and the unit's prints are not
    truncated away. A count helper: no price is computed."""
    a = tau - 60 * 60.0
    if not sd.prints_available or (sd.truncated and a < H1.oldest_or_inf(sd.oldest_ts)):
        return False
    return bool(((sd.tr_ts >= a) & (sd.tr_ts < tau) & (sd.tr_buy == buy)).any())


def s2_computable(sd: SuccData, origin: float) -> bool:
    """P_A exists at both declared times of an origin (``origin + |M|`` and ``origin + V_end``), i.e. S2 would be defined; counts only."""
    return print_available(sd, origin + sd.M) and print_available(sd, origin + sd.V)


def g50_gate(units: list[SuccData]) -> dict:
    """Gate G50 (census): >= 30 non-sports series and >= 300 SCREEN units with P_A at both times (t0 + |M| and V_end). Counts only."""
    ok_units = [u for u in units if not u.sports and unit_eligible(u, u.t0)[0] and s2_computable(u, u.t0)]
    ns = len({u.series_id for u in ok_units})
    return {"series": ns, "units": len(ok_units), "ok": bool(ns >= D.S["g50_series"] and len(ok_units) >= D.S["g50_units"])}


def s_census_counts(units: list[SuccData]) -> dict:
    """Pre-freeze census counts for family S (section 2.7): series by cadence and category, roll units, availability of P_A at each declared time (t0,
    t0 + |M|, V_end), units with and without a pseudo-roll origin by cadence, G per way (series, series x ISO week), truncated units, ineligibility
    drops. No S1/S2/S3 value is computed."""
    by_cad: dict[str, dict] = {}
    series_cat: dict[str, set] = {}
    drops: dict[str, int] = {}
    g_series, g_sw = set(), set()
    for sd in units:
        c = by_cad.setdefault(sd.cadence, {"units": 0, "non_sports_units": 0, "eligible": 0, "pa_at_t0": 0, "pa_at_M": 0, "pa_at_V": 0, "pa_both": 0,
                                           "pseudo_origin_available": 0, "pseudo_origin_missing": 0, "truncated": 0})
        series_cat.setdefault(f"{sd.cadence}|{sd.category}", set()).add(sd.series_id)
        c["units"] += 1
        c["non_sports_units"] += int(not sd.sports)
        c["truncated"] += int(not sd.prints_available)
        ok, why = unit_eligible(sd, sd.t0)
        if not ok:
            drops[why] = drops.get(why, 0) + 1
            continue
        c["eligible"] += 1
        c["pa_at_t0"] += int(print_available(sd, sd.t0))
        c["pa_at_M"] += int(print_available(sd, sd.t0 + sd.M))
        c["pa_at_V"] += int(print_available(sd, sd.t0 + sd.V))
        if s2_computable(sd, sd.t0):
            c["pa_both"] += 1
            if not sd.sports:
                g_series.add(sd.series_id)
                g_sw.add(f"{sd.series_id}|{_week_t0(sd)}")
            o2 = pseudo_origin(sd.t0, sd.V)
            if unit_eligible(sd, o2)[0] and s2_computable(sd, o2):
                c["pseudo_origin_available"] += 1
            else:
                c["pseudo_origin_missing"] += 1
    return {"by_cadence": by_cad, "series_by_cadence_category": {k: len(v) for k, v in sorted(series_cat.items())}, "ineligible_by_reason": drops,
            "G_series": len(g_series), "G_series_x_week": len(g_sw), "units": len(units)}


# ---- CB4-S: tests ----------------------------------------------------------------------------------------------------------


S_SMALL_G = ("series",)


def _week_t0(sd: SuccData) -> str:
    return H1.iso_week(sd.t0)


def s_values(units: list[SuccData], origin_of=None, *, alt: bool = False, s3_only: bool = False) -> dict:
    """Per-unit S2 (ask-side print series), history/sell-side companions, and S3 results at ``origin_of(sd)`` (default ``t0``; ``alt`` uses
    ``endDate + 1h``). Only eligible units contribute; drops are counted by reason."""
    rows, drops = [], {}
    for sd in units:
        o = origin_of(sd) if origin_of else (sd.t0_alt if alt else sd.t0)
        ok, why = unit_eligible(sd, o, alt=alt)
        if not ok:
            drops[why] = drops.get(why, 0) + 1
            continue
        nan2 = {"neg_v": math.nan, "s1": math.nan}
        a, h, bsell = (nan2, nan2, nan2) if s3_only else (s2_value(sd, o, "ask"), s2_value(sd, o, "hist"), s2_value(sd, o, "bid"))
        s3 = s3_at_origin(sd, o)
        s3b = s3_at_origin(sd, o, cost_add=D.COST_SENS_C) if s3.get("state") == "filled" else {}
        reg = cost_regimes.cost_regime(datetime.fromtimestamp(sd.t0, UTC).date(), sd.category)
        rows.append({"unit_id": sd.unit_id, "series": sd.series_id, "week": _week_t0(sd), "cadence": sd.cadence, "t0": sd.t0, "neg_v": a["neg_v"], "s1": a["s1"],
                     "prints_truncated": prints_truncated_away(sd, o),
                     "neg_v_hist": h["neg_v"], "neg_v_bid": bsell["neg_v"], "s3_state": s3.get("state"), "s3_net": s3.get("net", math.nan), "s3_net_sens": s3b.get("net", math.nan),
                     "s3_K": s3.get("K", math.nan), "s3_d": s3.get("d", math.nan), "s3_t_fill": s3.get("t_fill", math.nan), "post_rollout": bool(reg["post_rollout"]),
                     "era_rule": reg["era_rule"]})
    cols = ["unit_id", "series", "week", "cadence", "t0", "neg_v", "s1", "prints_truncated", "neg_v_hist", "neg_v_bid", "s3_state", "s3_net", "s3_net_sens", "s3_K", "s3_d", "s3_t_fill", "post_rollout", "era_rule"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ("t0", "neg_v", "s1", "neg_v_hist", "neg_v_bid", "s3_net", "s3_net_sens", "s3_K", "s3_d", "s3_t_fill"):
        df[c] = pd.to_numeric(df[c])
    df["post_rollout"] = df["post_rollout"].astype(bool)
    df["prints_truncated"] = df["prints_truncated"].astype(bool)
    return {"df": df, "drops": drops}


def pseudo_roll_attribution(units: list[SuccData], vals: pd.DataFrame) -> dict:
    """Attribution (binding for crediting CH50): on units with both origins (P_A at both times of both origins, successor created by t0' - 1h) CH50 is credited
    only if ``mean(-v_r) - mean(-v_t0') >= 0.5 mean(-v_r)``. Fewer than 100 units or 30 series with both: 'unverified' and no credit. Missing pseudo-origins
    are counted by cadence."""
    by_id = {u.unit_id: u for u in units}
    rows, miss = [], {}
    for _, r in vals[np.isfinite(vals["neg_v"])].iterrows():
        sd = by_id[r["unit_id"]]
        o2 = pseudo_origin(sd.t0, sd.V)
        ok, _why = unit_eligible(sd, o2)
        pv = s2_value(sd, o2, "ask")["neg_v"] if ok else math.nan
        if not np.isfinite(pv):
            miss[sd.cadence] = miss.get(sd.cadence, 0) + 1
            continue
        rows.append({"series": sd.series_id, "neg_v": r["neg_v"], "neg_v_pseudo": pv})
    d = pd.DataFrame(rows, columns=["series", "neg_v", "neg_v_pseudo"])
    n, ns = len(d), (int(d["series"].nunique()) if len(d) else 0)
    out = {"n_both": n, "n_series_both": ns, "missing_pseudo_by_cadence": miss, "verified": bool(n >= D.S["pseudo_min_units"] and ns >= D.S["pseudo_min_series"])}
    if n:
        m_real, m_ps = float(d["neg_v"].mean()), float(d["neg_v_pseudo"].mean())
        out.update({"s2_on_subset": m_real, "pseudo_mean": m_ps, "credit": bool(out["verified"] and (m_real - m_ps) >= 0.5 * m_real and m_real > 0)})
    else:
        out["credit"] = False
    return out


def era_subset_rule(df: pd.DataFrame, col: str) -> bool | None:
    """If the register's ``era_rule`` is ``post_rollout_or_interaction``: the post-rollout subset (rolls after the category's rollout + 7 d) must have the
    declared sign (mean > 0). Otherwise the rule is off (True). A required subset with no rows is unverified (None)."""
    if not len(df) or df["era_rule"].iloc[0] != cost_regimes.ERA_RULE_POST:
        return True
    sub = df[df["post_rollout"] & np.isfinite(df[col])]
    if not len(sub):
        return None
    return bool(sub[col].mean() > 0)


def s_tests(units: list[SuccData], *, stage: int, n_boot: int, placebo_draws: int, seed: int = D.SEED_BOOT, attribution: bool = True) -> dict:
    """S2 (mechanism) and S3 (economic) on the given units. S2: mean(-v) > 0, p = max over series (small-G rule) and series x ISO week of t0; floor 0.5c.
    S3: mean net per filled ask > 0; floor 0.5c and R_ann >= 10%. Binding: top-5 clusters per way, cluster-equal sign, print-series and alternative-origin
    sign agreement, truncation worst case (S2), +0.75c on the exit (S3), pseudo-roll attribution (S2), era rule, placebos."""
    alpha = D.ALPHA_STAGE1_ROUTE if stage == 1 else D.ALPHA_STAGE2
    main = s_values(units)
    df = main["df"]
    tests: dict = {}
    placebo: dict = {}
    descriptive = {"S1": {"n": int(np.isfinite(df["s1"]).sum()), "mean_s1": float(np.nanmean(df["s1"])) if np.isfinite(df["s1"]).any() else None}, "drops": main["drops"]}
    alt = s_values(units, alt=True)["df"]
    d2 = df[np.isfinite(df["neg_v"])]
    if len(d2) == 0:
        tests["S2"] = {"testable": False, "p": 1.0, "n": 0, "advance": False, "effect": math.nan, "reason": ["no S2 units"]}
    else:
        ways = {"series": d2["series"].to_numpy(str), "series_week": (d2["series"] + "|" + d2["week"]).to_numpy(str)}
        v = d2["neg_v"].to_numpy(float)
        core = mean_gate(v, ways, floor=D.FLOORS["S2"], alpha=alpha, small_g_ways=S_SMALL_G, n_boot=n_boot, seed=seed)
        ch: dict[str, bool | None] = {}
        ch.update({f"top5_dropped_{k}": x for k, x in top_clusters_dropped(v, ways, floor=D.FLOORS["S2"], alpha=alpha, small_g_ways=S_SMALL_G).items()})
        ch["cluster_equal_sign"] = CC.sign_agree(core["effect"], cluster_equal_mean(v, ways["series"]))
        for nm, col in (("print_series_sell_sign", "neg_v_bid"), ("history_series_sign", "neg_v_hist")):
            x = d2[col].to_numpy(float)
            x = x[np.isfinite(x)]
            ch[nm] = CC.sign_agree(core["effect"], float(x.mean())) if len(x) else None
        a2 = alt[np.isfinite(alt["neg_v"])]
        ch["alt_origin_sign"] = CC.sign_agree(core["effect"], float(a2["neg_v"].mean())) if len(a2) >= D.MIN_UNITS else None
        wc = _s2_worst_case(units, df)
        ch["truncation_worst_case"] = wc["ok"]
        att = pseudo_roll_attribution(units, d2)
        ch["attribution_pseudo_roll"] = bool(att["credit"]) if attribution else True
        ch["era_rule"] = era_subset_rule(d2, "neg_v")
        pl = placebo_advance_rate(lambda rng: v * rng.choice([-1.0, 1.0], len(v)), ways, floor=D.FLOORS["S2"], alpha=alpha, small_g_ways=S_SMALL_G, draws=D.PLACEBO_DRAWS, seed=seed + 4) if placebo_draws else {"calibrated": False, "n_draws": 0}
        ch["placebo_calibrated"] = bool(pl["calibrated"]) if pl.get("n_draws") else None
        dec = decide(core, ch)
        placebo["S2"] = pl
        tests["S2"] = {**{k: core.get(k) for k in ("p", "n", "testable", "effect", "ci95", "p_by_way", "clusters", "reason")}, **dec, "floor": D.FLOORS["S2"], "alpha": alpha, "stage": stage,
                       "attribution": att, "truncation_worst_case": wc, "placebo": pl, "placebo_status": "calibrated" if pl.get("calibrated") else "miscalibrated",
                       "label": "generic drift of the winning side, not the roll" if (core["pass_core"] and not ch["attribution_pseudo_roll"]) else None}
    d3 = df[df["s3_state"] == "filled"]
    if len(d3) == 0:
        tests["S3"] = {"testable": False, "p": 1.0, "n": 0, "advance": False, "effect": math.nan, "reason": ["no filled asks"]}
    else:
        ways3 = {"series": d3["series"].to_numpy(str), "series_week": (d3["series"] + "|" + d3["week"]).to_numpy(str)}
        v3 = d3["s3_net"].to_numpy(float)
        core3 = mean_gate(v3, ways3, floor=D.FLOORS["S3"], alpha=alpha, small_g_ways=S_SMALL_G, n_boot=n_boot, seed=seed)
        ra = r_ann(v3, d3["s3_K"], d3["s3_d"])
        ch3: dict[str, bool | None] = {"r_ann_min": bool(np.isfinite(ra) and ra >= D.R_ANN_MIN), "cost_plus_0.75c": bool(np.nanmean(d3["s3_net_sens"]) > 0)}
        ch3.update({f"top5_dropped_{k}": x for k, x in top_clusters_dropped(v3, ways3, floor=D.FLOORS["S3"], alpha=alpha, small_g_ways=S_SMALL_G).items()})
        ch3["cluster_equal_sign"] = CC.sign_agree(core3["effect"], cluster_equal_mean(v3, ways3["series"]))
        a3 = alt[alt["s3_state"] == "filled"]
        ch3["alt_origin_sign"] = CC.sign_agree(core3["effect"], float(a3["s3_net"].mean())) if len(a3) >= D.MIN_UNITS else None
        ch3["era_rule"] = era_subset_rule(d3, "s3_net")
        pl3 = _s3_random_origin_placebo(units, d3, alpha=alpha, draws=placebo_draws, seed=seed + 5) if placebo_draws else {"calibrated": False, "n_draws": 0}
        ch3["placebo_calibrated"] = bool(pl3["calibrated"]) if pl3.get("n_draws") else None
        dec3 = decide(core3, ch3)
        placebo["S3"] = pl3
        n_all = int(df["s3_state"].isin(["filled", "not_filled"]).sum())
        tests["S3"] = {**{k: core3.get(k) for k in ("p", "n", "testable", "effect", "ci95", "p_by_way", "clusters", "reason")}, **dec3, "floor": D.FLOORS["S3"], "alpha": alpha, "stage": stage,
                       "r_ann": ra, "fill_rate": float(len(d3) / n_all) if n_all else math.nan, "placebo": pl3, "placebo_status": "calibrated" if pl3.get("calibrated") else "miscalibrated"}
    return {"tests": tests, "placebo": placebo, "descriptive": descriptive}


def _s2_worst_case(units: list[SuccData], df: pd.DataFrame) -> dict:
    """Section CB4-S: units with unavailable prints (truncated away, ``prints_truncated``) are added back using the history-price series for v; the
    estimate must stay > 0. A unit whose window simply holds no print (history complete) is not 'unavailable' and is not added (freeze-check fix 7)."""
    have = df[np.isfinite(df["neg_v"])]["neg_v"].to_numpy(float)
    add = df[~np.isfinite(df["neg_v"]) & df["prints_truncated"].astype(bool) & np.isfinite(df["neg_v_hist"])]["neg_v_hist"].to_numpy(float)
    allv = np.concatenate([have, add])
    return {"mean": float(allv.mean()) if len(allv) else math.nan, "added": int(len(add)), "ok": bool(len(allv) and allv.mean() > 0)}


def _s3_random_origin_placebo(units: list[SuccData], d3: pd.DataFrame, *, alpha: float, draws: int, seed: int) -> dict:
    """S3 placebo: t0 replaced by a seeded uniform time in the successor's covered life outside [t0 - 6h, t0 + V_end + 6h]; 200 draws; advance rate <= 1.5%."""
    rng = np.random.default_rng(seed)
    adv = 0
    for _ in range(draws):
        origins = {}
        for sd in units:
            lo = (sd.ts[0] if len(sd.ts) else sd.t0) + 24 * HOUR
            hi = min(sd.succ_end - sd.V - 2 * HOUR, sd.ts[-1] - sd.V if len(sd.ts) else sd.t0)
            ban = (sd.t0 - 6 * HOUR, sd.t0 + sd.V + 6 * HOUR)
            for _try in range(20):
                if hi <= lo:
                    break
                o = float(rng.uniform(lo, hi))
                if not (ban[0] <= o <= ban[1]):
                    origins[sd.unit_id] = o
                    break
        sv = s_values([u for u in units if u.unit_id in origins], origin_of=lambda s, o=origins: o[s.unit_id], s3_only=True)["df"]
        d = sv[sv["s3_state"] == "filled"]
        if len(d) < D.MIN_UNITS:
            continue
        ways = {"series": d["series"].to_numpy(str), "series_week": (d["series"] + "|" + d["week"]).to_numpy(str)}
        adv += int(mean_gate(d["s3_net"].to_numpy(float), ways, floor=D.FLOORS["S3"], alpha=alpha, small_g_ways=S_SMALL_G)["pass_core"])
    rate = adv / max(draws, 1)
    return {"n_draws": draws, "n_advanced": adv, "advance_rate": rate, "max_rate": D.PLACEBO_MAX_ADVANCE_RATE, "calibrated": bool(rate <= D.PLACEBO_MAX_ADVANCE_RATE)}
