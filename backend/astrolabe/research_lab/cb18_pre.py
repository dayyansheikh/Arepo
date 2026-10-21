# ruff: noqa: E501
"""CB18 pre-censuses q0502 (CB18-S, CH177), q0503 (CB18-P, CH172), q0505 (CB18-F, CH176) and the routing writer (docs/research_lab/CREATIVE_BATCH_18.md section 3).

Counts only, on worn pre-window data named in seals/cb18_census_inputs.json. Every census reads origin-side fields at or before each unit's decision time (captures k - 12 .. k, sweep 1
of pass k, trade rows with ts at or before the pass k + 1 origin) and writes counts, shares, standard errors and planning MDEs; no forward price, target, mark or outcome is read or
written (J4R_DISCLOSURE). Gates and routes are part ``pre``'s (``cb18_rules_pre``); this module only counts.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import cb17_census as cc
from . import cb18_common as c
from . import cb18_rules_pre as r
from . import live_tests3 as l3

Refused = r.Refused

S_CAP_FIELDS = ("market_id", "condition_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "liquidity", "volume24hr",
                "end_date", "updated_at", "neg_risk", "clob_token_id_0")
S_EXT_FIELDS = ("market_id", "clob_token_id_1", "fee_type", "fee_category", "fees_enabled", "fee_schedule", "taker_base_fee", "order_price_min_tick_size", "order_min_size",
                "rewards_min_size", "rewards_max_spread", "clob_rewards", "series_slugs")
PASS1_FIELDS = ("market_id", "condition_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "spread")
WATERFALL = ("noprev", "open_binary", "two_sided", "spread", "mid_range", "end_27h", "sidecar_missing", "changed", "nosweep", "stamp_missing", "clock_anomaly", "book_touched",
             "uma", "upd_missing", "upd_earlier", "upd_after_receipt", "burst")


def _f(x) -> float | None:
    return float(x) if r.finite(x) else None


def _share(num, den) -> float | None:
    return (float(num) / float(den)) if den else None


def _hash_text(df: pd.DataFrame, cols: tuple[str, ...]) -> np.ndarray:
    """Row digest of raw text columns (bytes as written; equality only)."""
    if not len(df):
        return np.zeros(0, np.uint64)
    return pd.util.hash_pandas_object(df[list(cols)].astype(str), index=False).to_numpy()


# =====================================================================================================================================================
# compact capture frames (S)
# =====================================================================================================================================================


def open_quote_ok(df: pd.DataFrame) -> np.ndarray:
    """Pass-1 candidate rule: open, active, binary, two-sided and spread <= 0.10 at this capture (a superset of every unit's state at k - 1 or k)."""
    bid, ask, spr = c.to_f64(df["best_bid"]), c.to_f64(df["best_ask"]), c.to_f64(df["spread"])
    spr = np.where(np.isfinite(spr), spr, ask - bid)
    with np.errstate(invalid="ignore"):
        ts = (bid > 0) & (bid < ask) & (ask <= 1.0) & (spr <= r.S_SPREAD_MAX + r.QUOTE_TOL)
    op = ~df["closed"].map(cc.is_true).to_numpy(bool) & df["active"].map(cc.is_true).to_numpy(bool) & (df["binary"].astype(str).str.strip() == "1").to_numpy()
    return ts & op


class Frame:
    """One capture reduced to the S census fields of the candidate markets (index sorted by market id) plus its byte flags."""

    def __init__(self, cap_id: str, slot: int, t: float, F: pd.DataFrame, flags: dict, ext_ok: bool):
        self.cap_id, self.slot, self.t, self.F, self.flags, self.ext_ok = cap_id, slot, t, F, flags, ext_ok


def load_frame(tree: c.PinnedTree, cap_id: str, cand: set) -> Frame:
    def keep(ch: pd.DataFrame) -> np.ndarray:
        return ch["market_id"].isin(cand).to_numpy()

    rows, rfl, meta = c.read_capture(tree, cap_id, S_CAP_FIELDS, r.BYTE_FLAG_CAPTURE_FIELDS, keep=keep)
    ext, efl, emeta = c.read_sidecar(tree, cap_id, S_EXT_FIELDS, r.BYTE_FLAG_SIDECAR_FIELDS, market_ids=set(rows["market_id"]))
    order = np.argsort(rows["market_id"].to_numpy(dtype=object), kind="stable")
    rows = rows.iloc[order].reset_index(drop=True)
    rfl = {k: v.take(order) for k, v in rfl.items()}
    F = pd.DataFrame(index=pd.Index(rows["market_id"].astype(str).to_numpy(), name="market_id"))
    for col in r.EQ_CAPTURE_NUMERIC:
        F[col] = c.to_f64(rows[col])
    spr = F["spread"].to_numpy()
    F["spread_eff"] = np.where(np.isfinite(spr), spr, F["best_ask"].to_numpy() - F["best_bid"].to_numpy())
    F["d_txt"] = _hash_text(rows, r.EQ_CAPTURE_TEXT)
    F["d_end"] = _hash_text(rows, (r.EQ_END_FIELD,))
    F["end_s"] = c.epoch_s(rows["end_date"].to_numpy())
    F["upd_ms"] = c.epoch_ms(rows["updated_at"].to_numpy())
    F["rec_ms"] = c.epoch_ms(rows["received_utc"].to_numpy())
    F["open"] = ~rows["closed"].map(cc.is_true).to_numpy(bool) & rows["active"].map(cc.is_true).to_numpy(bool) & (rows["binary"].astype(str).str.strip() == "1").to_numpy()
    F["event"] = np.where(rows["event_id"].astype(str).to_numpy() != "", rows["event_id"].astype(str).to_numpy(), rows["market_id"].astype(str).to_numpy())
    F["tok0"] = rows["clob_token_id_0"].astype(str).to_numpy()
    ext_ok = emeta.get("status") == "complete"
    eidx = pd.Index(ext["market_id"].astype(str)).get_indexer(F.index) if ext_ok and len(ext) else np.full(len(F), -1)
    F["ext_present"] = eidx >= 0
    take = np.where(eidx >= 0, eidx, 0)
    if ext_ok and len(ext):
        ex = ext.iloc[take].reset_index(drop=True)
        for col in r.EQ_SIDECAR_NUMERIC:
            F[col] = np.where(eidx >= 0, c.to_f64(ex[col]), np.nan)
        F["d_ext"] = np.where(eidx >= 0, _hash_text(ex, r.EQ_SIDECAR_TEXT), np.uint64(0))
        F["sports"] = np.where(eidx >= 0, c.sports_flags(ex["fee_type"], ex["fee_category"], ex["series_slugs"]), False)
        F["tok1"] = np.where(eidx >= 0, ex["clob_token_id_1"].astype(str).to_numpy(), "")
        flags = {**rfl, **{k: v.take(take) for k, v in efl.items()}}
    else:
        for col in r.EQ_SIDECAR_NUMERIC:
            F[col] = np.nan
        F["d_ext"] = np.uint64(0)
        F["sports"] = False
        F["tok1"] = ""
        n = len(F)
        flags = {**rfl, **{k: c.ByteFlag(k, [""] * n) for k in r.BYTE_FLAG_SIDECAR_FIELDS}}
    return Frame(cap_id, meta["slot"], meta["t"], F, flags, ext_ok)


def compare(a: Frame | None, b: Frame) -> dict:
    """Interval (a -> b) state for b's markets: presence, the (8) equalities, the chg_* byte flags, (10) and the comment-count flag. Unknown (a missing capture) -> None."""
    if a is None:
        return None
    idx = a.F.index.get_indexer(b.F.index)
    pres = idx >= 0
    ti = np.where(pres, idx, 0)
    A = a.F.iloc[ti]
    B = b.F
    num = np.ones(len(B), bool)
    for col in r.EQ_CAPTURE_NUMERIC:
        num &= c.eq_f64(A[col].to_numpy(), B[col].to_numpy())
    txt = A["d_txt"].to_numpy() == B["d_txt"].to_numpy()
    end = A["d_end"].to_numpy() == B["d_end"].to_numpy()
    ext_both = A["ext_present"].to_numpy(bool) & B["ext_present"].to_numpy(bool)
    ext = ext_both.copy()
    for col in r.EQ_SIDECAR_NUMERIC:
        ext &= c.eq_f64(A[col].to_numpy(), B[col].to_numpy())
    ext &= A["d_ext"].to_numpy() == B["d_ext"].to_numpy()
    fa = {k: v.take(ti) for k, v in a.flags.items()}
    chg = {k: c.bytes_equal(fa[k], b.flags[k]) & pres for k in r.BYTE_FLAG_CAPTURE_FIELDS}
    uma_eq = c.bytes_equal(fa["uma_resolution_statuses"], b.flags["uma_resolution_statuses"]) & ext_both
    uma_empty_b = c.is_empty_literal(b.flags["uma_resolution_statuses"]) & B["ext_present"].to_numpy(bool)
    uma_missing_b = c.is_missing(b.flags["uma_resolution_statuses"]) | ~B["ext_present"].to_numpy(bool)
    ecc_eq = c.bytes_equal(fa["event_comment_count"], b.flags["event_comment_count"]) & ext_both
    return {"pres": pres, "open_a": A["open"].to_numpy(bool) & pres, "num": num & pres, "txt": txt & pres, "end": end & pres, "ext": ext & pres, "ext_both": ext_both & pres,
            "chg": chg, "uma_eq": uma_eq & pres, "uma_empty_b": uma_empty_b, "uma_missing_b": uma_missing_b, "ecc_eq": ecc_eq & pres,
            "upd_a": np.where(pres, A["upd_ms"].to_numpy(), np.nan), "rec_a": np.where(pres, A["rec_ms"].to_numpy(), np.nan), "A": A}


def capture_quiet(cmp: dict | None, b: Frame) -> np.ndarray | None:
    """PRIOR_QUIET_RULE for interval (a -> b) on b's markets; None if capture a is missing (unknown)."""
    if cmp is None:
        return None
    chg_all = cmp["chg"]["chg_1h"] & cmp["chg"]["chg_1d"] & cmp["chg"]["chg_1w"]
    upd_b = b.F["upd_ms"].to_numpy()
    with np.errstate(invalid="ignore"):
        upd_eq = np.isfinite(upd_b) & np.isfinite(cmp["upd_a"]) & (upd_b == cmp["upd_a"])
    return (cmp["open_a"] & b.F["open"].to_numpy(bool) & cmp["num"] & cmp["txt"] & cmp["end"] & cmp["ext"] & chg_all & cmp["uma_eq"] & cmp["uma_empty_b"] & upd_eq)


# =====================================================================================================================================================
# q0502: CB18-S census
# =====================================================================================================================================================


def census_slots(tree: c.PinnedTree) -> dict[int, str]:
    by: dict[int, str] = {}
    for cid in tree.ids("snapshots"):
        k = c.slot_of(c.stamp_epoch(cid))
        if k is not None:
            by.setdefault(k, cid)
    return by


def _lookback(k: int, j: int, frames: dict, mids: pd.Index, unavail: set) -> tuple[np.ndarray, np.ndarray]:
    """(mid at slot k - j aligned to ``mids``, status code per market: 0 ok, 1 unavailable (declared gap), 2 missing / not two-sided)."""
    kk = k - j
    n = len(mids)
    if kk in unavail:
        return np.full(n, np.nan), np.ones(n, np.int8)
    fr = frames.get(kk)
    if fr is None:
        return np.full(n, np.nan), np.full(n, 2, np.int8)
    idx = fr.F.index.get_indexer(mids)
    pres = idx >= 0
    ti = np.where(pres, idx, 0)
    bid, ask = fr.F["best_bid"].to_numpy()[ti], fr.F["best_ask"].to_numpy()[ti]
    with np.errstate(invalid="ignore"):
        ok = pres & (bid > 0) & (bid < ask) & (ask <= 1.0)
    return np.where(ok, (bid + ask) / 2.0, np.nan), np.where(ok, 0, 2).astype(np.int8)


def _prior_quiet(k: int, cq: dict, mids: pd.Index, unavail: set) -> tuple[np.ndarray, np.ndarray]:
    """Consecutive capture-quiet prior intervals (k - j - 1, k - j), j = 1 .. 11; status 0 known, 1 unknown at the declared gap, 2 unknown otherwise."""
    n = len(mids)
    count = np.zeros(n, np.int16)
    alive = np.ones(n, bool)
    status = np.zeros(n, np.int8)
    for j in range(1, r.PRIOR_QUIET_CAP + 1):
        b = k - j
        ent = cq.get(b)
        if ent is None:
            gap = (b in unavail) or (b - 1 in unavail)
            status = np.where(alive & (status == 0), 1 if gap else 2, status).astype(np.int8)
            break
        idx_b, q = ent
        ii = idx_b.get_indexer(mids)
        qq = np.where(ii >= 0, q[np.where(ii >= 0, ii, 0)], False)
        count = np.where(alive & qq, count + 1, count)
        alive &= qq
        if not alive.any():
            break
    return count, status


def census_s(tree: c.PinnedTree) -> dict:
    """q0502 (section 3.1). Counts, shares, the proxy SE (SE only) and both routing MDEs."""
    by_slot = census_slots(tree)
    unavail = c.unavailable_slots()
    days = r.CENSUS_DAYS_SF
    k_units = sorted(k for k in by_slot if r.utc_day(c.slot_time(k)) in days)
    lo = c.slot_of(r.ep(r.S_LOOKBACK_START))
    for k in k_units:
        if k - 1 not in by_slot:
            raise Refused(f"census S: slot k - 1 of {c.slot_iso(k)} is not pinned")
    sweep1 = c.sweep1_by_capture(tree)
    # pass 1: candidate markets (open, binary, two-sided, spread <= 0.10 at some k - 1 or k)
    cand: set = set()
    pass1 = sorted({k for k in k_units} | {k - 1 for k in k_units})
    for k in pass1:
        rows, _, _ = c.read_capture(tree, by_slot[k], PASS1_FIELDS, keep=open_quote_ok)
        cand.update(rows["market_id"].astype(str))
        del rows
    # pass 2: frames from the look-back start, one capture at a time; frames older than k - 12 are dropped
    frames: dict[int, Frame] = {}
    cq: dict[int, tuple] = {}
    unit_parts: list[pd.DataFrame] = []
    wf = {sp: Counter() for sp in ("non_sports", "sports")}
    cnt = Counter()
    per_cap: list[dict] = []
    flag_split = {cls: {sp: Counter() for sp in ("non_sports", "sports")} for cls in ("silent_pre_r1", "quiet_pre_r1", "chg_only")}
    uma_cls = {sp: Counter() for sp in ("non_sports", "sports")}
    all_slots = sorted(k for k in by_slot if lo <= k <= max(k_units))
    for k in all_slots:
        fr = load_frame(tree, by_slot[k], cand)
        frames[k] = fr
        cmp_prev = compare(frames.get(k - 1), fr)
        q = capture_quiet(cmp_prev, fr)
        if q is not None:
            cq[k] = (fr.F.index, q)
        for old in [s for s in frames if s < k - 12]:
            frames.pop(old)
        for old in [s for s in cq if s < k - 12]:
            cq.pop(old)
        if k not in k_units:
            continue
        sid = sweep1.get(fr.cap_id)
        units, pc = s_units(k, fr, frames[k - 1], cmp_prev, sid and c.read_sweep1(tree, sid), frames, cq, unavail, wf, cnt, flag_split, uma_cls)
        per_cap.append(pc)
        if len(units):
            unit_parts.append(units)
    U = pd.concat(unit_parts, ignore_index=True) if unit_parts else pd.DataFrame()
    return summarize_s(U, per_cap, wf, cnt, flag_split, uma_cls, len(cand))


def s_units(k: int, fr: Frame, prev: Frame, cmp: dict, sw: pd.DataFrame | None, frames: dict, cq: dict, unavail: set, wf: dict, cnt: Counter, flag_split: dict, uma_cls: dict) -> tuple[pd.DataFrame, dict]:
    """Units of interval (k - 1, k): the eligibility waterfall (counted in order), the classes, GS1-GS3 inputs and the frame rows (silent, quiet, chg_only)."""
    F = fr.F
    n = len(F)
    t_k, t_prev = fr.t, prev.t
    pres = cmp["pres"]
    bid, ask, spr = F["best_bid"].to_numpy(), F["best_ask"].to_numpy(), F["spread_eff"].to_numpy()
    A = cmp["A"]
    bid_p, ask_p, spr_p = A["best_bid"].to_numpy(), A["best_ask"].to_numpy(), A["spread_eff"].to_numpy()
    mid = (bid + ask) / 2.0
    with np.errstate(invalid="ignore"):
        e1 = F["open"].to_numpy(bool) & cmp["open_a"]
        e2 = (bid > 0) & (bid < ask) & (ask <= 1) & (bid_p > 0) & (bid_p < ask_p) & (ask_p <= 1)
        e3 = (spr <= r.S_SPREAD_MAX + r.QUOTE_TOL) & (spr_p <= r.S_SPREAD_MAX + r.QUOTE_TOL)
        e4 = (mid >= r.S_MID_RANGE[0] - r.QUOTE_TOL) & (mid <= r.S_MID_RANGE[1] + r.QUOTE_TOL)
        end = F["end_s"].to_numpy()
        e5 = ~np.isfinite(end) | (end > t_k + r.S_END_MIN_H * 3600.0)
    e6 = F["ext_present"].to_numpy(bool) & cmp["ext_both"]
    sports = F["sports"].to_numpy(bool)
    eq8_nochg = cmp["num"] & cmp["txt"] & cmp["end"] & cmp["ext"]
    chg_all = cmp["chg"]["chg_1h"] & cmp["chg"]["chg_1d"] & cmp["chg"]["chg_1w"]
    eq8 = eq8_nochg & chg_all
    # (9) sweep 1 of pass k
    st0 = np.full(n, np.nan)
    st1 = np.full(n, np.nan)
    rec = np.full(n, np.nan)
    has_sweep = sw is not None and len(sw) > 0
    if has_sweep:
        si = pd.Index(sw["token_id"].astype(str))
        i0 = si.get_indexer(F["tok0"].astype(str).to_numpy())
        i1 = si.get_indexer(F["tok1"].astype(str).to_numpy())
        ok0 = i0 >= 0
        st0 = np.where(ok0, sw["stamp_ms"].to_numpy()[np.where(ok0, i0, 0)], np.nan)
        rec = np.where(ok0, sw["receipt"].to_numpy()[np.where(ok0, i0, 0)], np.nan)
        ok1 = i1 >= 0
        st1 = np.where(ok1, sw["stamp_ms"].to_numpy()[np.where(ok1, i1, 0)], np.nan)
    else:
        ok0 = np.zeros(n, bool)
        ok1 = np.zeros(n, bool)
    with np.errstate(invalid="ignore"):
        age = rec - st0 / 1000.0
        anomaly = np.isfinite(age) & (age < r.CLOCK_ANOMALY_S)
        b0 = np.isfinite(st0) & (st0 / 1000.0 <= t_prev)
        b1 = ~np.isfinite(st1) | (st1 / 1000.0 <= t_prev)
    book = b0 & b1
    uma_ok = cmp["uma_eq"] & cmp["uma_empty_b"]
    upd_k, upd_p, rec_k = F["upd_ms"].to_numpy(), cmp["upd_a"], F["rec_ms"].to_numpy()
    cls = np.array([r.s_class(a, b, rr) for a, b, rr in zip(upd_p, upd_k, rec_k, strict=True)], dtype=object)
    # waterfall (first failing step; each exclusion counted once)
    steps = [("noprev", pres), ("open_binary", e1), ("two_sided", e2), ("spread", e3), ("mid_range", e4), ("end_27h", e5), ("sidecar_missing", e6), ("changed", eq8),
             ("nosweep", ok0), ("stamp_missing", np.isfinite(st0)), ("clock_anomaly", ~anomaly), ("book_touched", book), ("uma", uma_ok)]
    alive = np.ones(n, bool)
    first_fail = np.full(n, "", dtype=object)
    for name, ok in steps:
        fail = alive & ~ok
        first_fail[fail] = name
        alive &= ok
    elig7 = pres & e1 & e2 & e3 & e4 & e5 & e6
    p10 = elig7 & eq8 & ok0 & np.isfinite(st0) & ~anomaly & book & uma_ok
    for nm in ("upd_missing", "upd_earlier", "upd_after_receipt"):
        first_fail[p10 & (cls == nm)] = nm
    sq = p10 & np.isin(cls, ["silent", "quiet"])
    ns = ~sports
    den = int((sq & ns).sum())
    sil = int((sq & ns & (cls == "silent")).sum())
    burst = den > 0 and sil > r.BURST_SHARE * den
    if burst:
        first_fail[sq] = "burst"
    for sp_name, sp_mask in (("non_sports", ns), ("sports", sports)):
        for nm in WATERFALL:
            wf[sp_name][nm] += int(((first_fail == nm) & sp_mask).sum())
        wf[sp_name]["candidates"] += int(sp_mask.sum())
        wf[sp_name]["eligible_1_7"] += int((elig7 & sp_mask).sum())
        wf[sp_name]["silent_1_11"] += int((sq & sp_mask & (cls == "silent")).sum()) if not burst else 0
        wf[sp_name]["quiet_1_11"] += int((sq & sp_mask & (cls == "quiet")).sum()) if not burst else 0
    # GS1-GS3 inputs
    upd_both = np.isfinite(upd_k) & np.isfinite(upd_p)
    with np.errstate(invalid="ignore"):
        changed = upd_both & (upd_k != upd_p)
        anom_k = np.isfinite(upd_k) & np.isfinite(rec_k) & (upd_k > rec_k + r.UPDATED_AT_RECEIPT_TOL_S * 1000.0)
        anom_p = np.isfinite(upd_p) & np.isfinite(cmp["rec_a"]) & (upd_p > cmp["rec_a"] + r.UPDATED_AT_RECEIPT_TOL_S * 1000.0)
    unusable = ~upd_both | anom_k | anom_p
    g1 = elig7 & eq8 & ok0 & np.isfinite(st0) & ~anomaly & book & ns & upd_both
    g2 = elig7 & ns & upd_both
    cnt["gs1_den"] += int(g1.sum())
    cnt["gs1_num"] += int((g1 & changed).sum())
    cnt["gs2_den"] += int(g2.sum())
    cnt["gs2_num"] += int((g2 & changed).sum())
    cnt["gs3_den"] += int(elig7.sum())
    cnt["gs3_num"] += int((elig7 & unusable).sum())
    cnt["outcome1_row_missing_in_sweep"] += int((p10 & ~ok1).sum())
    cnt["sweep_missing_capture"] += 0 if has_sweep else 1
    # reported classes
    p9 = elig7 & ok0 & np.isfinite(st0) & ~anomaly & book
    for sp_name, sp_mask in (("non_sports", ns), ("sports", sports)):
        m = elig7 & sp_mask
        cnt[f"{sp_name}_upd_changed_all_eligible"] += int((m & changed).sum())
        cnt[f"{sp_name}_uma_change_flag"] += int((m & cmp["ext_both"] & ~cmp["uma_eq"]).sum())
        cnt[f"{sp_name}_comment_change_flag"] += int((m & cmp["ext_both"] & ~cmp["ecc_eq"]).sum())
        cnt[f"{sp_name}_sidecar_only_change"] += int((m & cmp["num"] & cmp["txt"] & cmp["end"] & chg_all & ~cmp["ext"]).sum())
        cnt[f"{sp_name}_end_date_change"] += int((m & ~cmp["end"]).sum())
        cnt[f"{sp_name}_end_date_change_otherwise_unchanged_book_untouched"] += int((p9 & sp_mask & ~cmp["end"] & cmp["num"] & cmp["txt"] & cmp["ext"] & chg_all).sum())
        um = p9 & sp_mask & eq8
        uma_cls[sp_name]["empty_literal"] += int((um & cmp["uma_empty_b"]).sum())
        uma_cls[sp_name]["missing"] += int((um & cmp["uma_missing_b"]).sum())
        uma_cls[sp_name]["non_empty"] += int((um & ~cmp["uma_empty_b"] & ~cmp["uma_missing_b"]).sum())
        base = p9 & sp_mask & eq8_nochg & uma_ok & (not burst)
        fs = np.array([r.chg_flag_status(a, b, cc_) for a, b, cc_ in zip(cmp["chg"]["chg_1h"], cmp["chg"]["chg_1d"], cmp["chg"]["chg_1w"], strict=True)], dtype=object)
        for st in r.CHG_FLAG_STATUS:
            flag_split["silent_pre_r1"][sp_name][st] += int((base & (cls == "silent") & (fs == st)).sum())
            flag_split["quiet_pre_r1"][sp_name][st] += int((base & (cls == "quiet") & (fs == st)).sum())
        co = base & ~chg_all
        for cl in r.S_CLASSES:
            flag_split["chg_only"][sp_name][cl] += int((co & (cls == cl)).sum())
    pc = {"slot": c.slot_iso(k), "day": r.utc_day(c.slot_time(k)), "sweep1": bool(has_sweep), "eligible_ns": int((elig7 & ns).sum()), "silent_ns": sil, "quiet_ns": den - sil, "burst": bool(burst),
          "silent_share_ns": _share(sil, den)}
    keep = (sq | (p9 & eq8_nochg & ~chg_all & uma_ok)) & (not burst)
    if not keep.any():
        return pd.DataFrame(), pc
    ii = np.flatnonzero(keep)
    mids = F.index[ii]
    m3, s3 = _lookback(k, 3, frames, mids, unavail)
    m12, s12 = _lookback(k, 12, frames, mids, unavail)
    pq, sq_status = _prior_quiet(k, cq, mids, unavail)
    lb = np.where((s3 == 1) | (s12 == 1) | (sq_status == 1), 1, np.where((s3 == 2) | (s12 == 2) | (sq_status == 2), 2, 0))
    with np.errstate(invalid="ignore", divide="ignore"):
        age_i = np.clip(age[ii], 0.0, r.DORMANCY_CAP_S)
        hte = (end[ii] - t_k) / 3600.0
    U = pd.DataFrame({"market_id": mids.to_numpy(), "event": F["event"].to_numpy()[ii], "slot": k, "slot_iso": c.slot_iso(k), "t": t_k, "sports": sports[ii],
                      "cls": cls[ii], "unit": sq[ii], "chg_only": (~chg_all)[ii], "lb": lb, "mid": mid[ii], "m3": m3, "m12": m12, "pq": pq, "spread": spr[ii],
                      "vol": F["volume24hr"].to_numpy()[ii], "hte": hte, "dorm": np.log1p(age_i), "ecc_changed": (~cmp["ecc_eq"])[ii].astype(float)})
    return U, pc


def summarize_s(U: pd.DataFrame, per_cap: list[dict], wf: dict, cnt: Counter, flag_split: dict, uma_cls: dict, n_cand: int) -> dict:
    days = float(len(r.CENSUS_DAYS_SF))
    out: dict = {"family": "S", "idea": "CH177", "job": "q0502", "candidates_pass1": n_cand, "waterfall": {k: dict(v) for k, v in wf.items()}, "per_capture": per_cap,
                 "uma_status_at_k_numerically_unchanged_book_untouched": {k: dict(v) for k, v in uma_cls.items()},
                 "chg_flag_split": {k: {sp: dict(v) for sp, v in d.items()} for k, d in flag_split.items()},
                 "reported_counts": {k: v for k, v in cnt.items() if not k.startswith("gs")}}
    gs = {"gs1_share": _share(cnt["gs1_num"], cnt["gs1_den"]), "gs1_n": cnt["gs1_den"], "gs2_share": _share(cnt["gs2_num"], cnt["gs2_den"]), "gs2_n": cnt["gs2_den"],
          "gs3_share": _share(cnt["gs3_num"], cnt["gs3_den"]), "gs3_n": cnt["gs3_den"]}
    burst_caps = [p for p in per_cap if p["burst"]]
    sil_tot = sum(p["silent_ns"] for p in per_cap)
    out["burst"] = {"captures_over_line": len(burst_caps), "captures": len(per_cap), "top_capture_share_of_silent": _share(max((p["silent_ns"] for p in per_cap), default=0), sil_tot),
                    "line": r.BURST_SHARE}
    if U.empty:
        units = U
    else:
        units = U[U["unit"] & ~U["sports"]]
    sil = units[units["cls"] == "silent"] if len(units) else units
    qui = units[units["cls"] == "quiet"] if len(units) else units
    gs["gs4_silent_per_day"] = len(sil) / days
    out["per_day"] = {d: {"silent_ns": int(sum(p["silent_ns"] for p in per_cap if p["day"] == d and not p["burst"])), "quiet_ns": int(sum(p["quiet_ns"] for p in per_cap if p["day"] == d and not p["burst"]))} for d in r.CENSUS_DAYS_SF}
    out["lookback"] = {"lookback_unavailable": int((units["lb"] == 1).sum()) if len(units) else 0, "lookback_missing": int((units["lb"] == 2).sum()) if len(units) else 0}
    out["chg_only_units"] = {"non_sports": int((U["chg_only"] & ~U["sports"] & ~U["unit"]).sum()) if len(U) else 0}
    m = r.m_by_event(sil.groupby("event").size().to_numpy()) if len(sil) else math.nan
    out["silent_per_event"] = {"events": int(sil["event"].nunique()) if len(sil) else 0, "m": _f(m),
                               "quantiles": ({str(q): float(v) for q, v in sil.groupby("event").size().quantile([0.5, 0.9, 0.99, 1.0]).items()} if len(sil) else {})}
    out["quiet_to_silent"] = _share(len(qui), len(sil))
    frame = units[units["lb"] != 2] if len(units) else units
    arm0 = frame["event"].map(r.arm_of).to_numpy() == 0 if len(frame) else np.zeros(0, bool)
    is_sil = (frame["cls"] == "silent").to_numpy() if len(frame) else np.zeros(0, bool)
    s_arm0, q_arm0 = int((is_sil & arm0).sum()), int((~is_sil & arm0).sum())
    s_all, q_all = int(is_sil.sum()), int((~is_sil).sum())
    q_cb = r.thin_rate(s_arm0, q_arm0, days, r.W_ARM_DAYS)
    q_lt = r.thin_rate(s_all, q_all, days, r.W_LT_DAYS)
    out["frame"] = {"silent": s_all, "quiet": q_all, "silent_arm0": s_arm0, "quiet_arm0": q_arm0, "q_cb": q_cb, "q_lt": q_lt,
                    "projected_arm0_14d_rows_at_q_cb": None if q_cb is None else (s_arm0 + q_cb * q_arm0) * r.W_ARM_DAYS / days,
                    "projected_28d_rows_at_q_lt": None if q_lt is None else (s_all + q_lt * q_all) * r.W_LT_DAYS / days}
    dcuts = None
    if len(frame):
        v = frame["dorm"].to_numpy(float)
        v = v[np.isfinite(v)]
        if v.size >= 3:
            lo_, hi_ = np.quantile(v, (1 / 3, 2 / 3))
            dcuts = (float(lo_), float(hi_))
    out["dormancy_tercile_cuts_log1p_s"] = list(dcuts) if dcuts else None
    levels = {}
    for name, q in (("q_cb", q_cb), ("q_lt", q_lt)):
        sub = _thinned(frame, q)
        shares = {}
        for lv in r.PERM_LADDER:
            shares[lv] = r.permutable_share(((r.perm_stratum(lv, mk, t), int(cl == "silent")) for mk, t, cl in zip(sub["market_id"], sub["t"], sub["cls"], strict=True)))["share"] if len(sub) else None
        comp = {}
        if dcuts and len(sub):
            for lv in r.COMP_LADDER:
                comp[lv] = r.informative_share(((r.comp_stratum(lv, t, r.tercile_of(d, dcuts), s), int(cl == "silent")) for t, d, s, cl in zip(sub["t"], sub["dorm"], sub["spread"], sub["cls"], strict=True)))["share"]
        levels[name] = {"units": len(sub), "permutable_share_by_level": shares, "selected_level": r.select_level(shares), "composition_share_by_level": comp,
                        "composition_level": r.select_level(comp) if comp else None}
    out["strata"] = levels
    gs["gs5_level_cb"] = levels["q_cb"]["selected_level"]
    gs["gs5_level_lt"] = levels["q_lt"]["selected_level"]
    se = {name: s_proxy_se(_thinned(frame[frame["lb"] == 0] if len(frame) else frame, q)) for name, q in (("q_cb", q_cb), ("q_lt", q_lt))}
    out["proxy_se"] = se
    de_c = r.de_computed(m, days, days)
    de14 = r.de_computed(m, r.W_ARM_DAYS, days)
    de28 = r.de_computed(m, r.W_LT_DAYS, days)
    mde1 = r.mde_rs1(se["q_cb"]["se_c"], days, de14, de_c)
    mde2 = r.mde_rs2(se["q_lt"]["se_c"], days, de28, de_c)
    fb1 = fb2 = None
    if not r.finite(mde1):
        fb1 = r.mde_formula(r.M_CB, r.SD_S_FALLBACK_C, s_arm0 * r.W_ARM_DAYS / days, (q_cb or math.nan) * q_arm0 * r.W_ARM_DAYS / days, r.de_gate(m, r.W_ARM_DAYS, days))
        mde1 = fb1
    if not r.finite(mde2):
        fb2 = r.mde_formula(r.M_LT, r.SD_S_FALLBACK_C, s_all * r.W_LT_DAYS / days, (q_lt or math.nan) * q_all * r.W_LT_DAYS / days, r.de_gate(m, r.W_LT_DAYS, days))
        mde2 = fb2
    out["design_effect"] = {"m": _f(m), "de_census": _f(de_c), "de_w14": _f(de14), "de_w28": _f(de28), "de_gate_14": _f(r.de_gate(m, r.W_ARM_DAYS, days)), "de_gate_28": _f(r.de_gate(m, r.W_LT_DAYS, days)),
                            "inflation_14": _f(r.de_inflation(de14, de_c)), "inflation_28": _f(r.de_inflation(de28, de_c))}
    out["mde"] = {"mde_rs1_c": _f(mde1), "mde_rs2_c": _f(mde2), "rs1_from_formula_fallback": fb1 is not None, "rs2_from_formula_fallback": fb2 is not None}
    out["gate_inputs"] = gs
    g = r.gs_gates(gs)
    out["gates"] = g
    out["route"] = r.route_s(g, mde1, mde2)
    out["census_to_spec"] = {"strata_level": levels["q_cb" if out["route"]["route"] == "RS-1" else "q_lt"]["selected_level"], "q_cb": q_cb, "q_lt": q_lt,
                             "dormancy_tercile_cuts_log1p_s": out["dormancy_tercile_cuts_log1p_s"], "composition_level": levels["q_cb" if out["route"]["route"] == "RS-1" else "q_lt"]["composition_level"]}
    return out


def _thinned(frame: pd.DataFrame, q: float | None) -> pd.DataFrame:
    if frame is None or not len(frame):
        return frame if frame is not None else pd.DataFrame()
    keep = (frame["cls"] == "silent").to_numpy() | np.array([r.thin_keep(mk, si, q) for mk, si in zip(frame["market_id"], frame["slot_iso"], strict=True)], dtype=bool)
    return frame[keep]


def s_design(sub: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(y in cents, X) for the S proxy SE: label first, then the declared controls (the two |mid| controls left out)."""
    hte = sub["hte"].to_numpy(float)
    known = np.isfinite(hte)
    lhte = np.where(known, np.log(np.clip(hte, 1.0, r.HOURS_TO_END_CAP_H)), 0.0)
    b6 = np.array([r.band6(t) for t in sub["t"]], dtype=int)
    X = np.column_stack([(sub["cls"] == "silent").to_numpy(float), np.log1p(sub["vol"].to_numpy(float)), sub["spread"].to_numpy(float), np.abs(sub["mid"].to_numpy(float) - 0.5),
                         lhte, (~known).astype(float), sub["dorm"].to_numpy(float), sub["pq"].to_numpy(float), sub["ecc_changed"].to_numpy(float),
                         (b6 == 1).astype(float), (b6 == 2).astype(float), (b6 == 3).astype(float)])
    y = np.abs(sub["mid"].to_numpy(float) - sub["m12"].to_numpy(float)) * 100.0
    return y, X


def s_proxy_se(sub: pd.DataFrame) -> dict:
    if sub is None or not len(sub):
        return {"n": 0, "se_c": None, "note": "no units"}
    y, X = s_design(sub)
    res = c.proxy_se(y, X, list(sub["market_id"]), {"event": list(sub["event"]), "block6": [r.block6(t) for t in sub["t"]]})
    res["se_c"] = _f(res["se_c"])
    res["units"] = int(len(sub))
    res["silent"] = int((sub["cls"] == "silent").sum())
    return res


# =====================================================================================================================================================
# q0505: CB18-F census (no price read)
# =====================================================================================================================================================

F_CAP_FIELDS = ("market_id", "condition_id", "received_utc", "event_id", "closed", "active", "volume24hr")
F_EXT_FIELDS = ("market_id", "fee_type", "fee_category", "series_slugs")


def f_capture(tree: c.PinnedTree, cap_id: str) -> dict | None:
    """Non-sports, open, active markets of a capture with their event, fee_type, category and volume24hr (no price); per fee_type the events ranked by summed volume24hr."""
    rows, _, meta = c.read_capture(tree, cap_id, F_CAP_FIELDS, keep=lambda ch: (~ch["closed"].map(cc.is_true) & ch["active"].map(cc.is_true)).to_numpy(bool))
    ext, _, em = c.read_sidecar(tree, cap_id, F_EXT_FIELDS, market_ids=set(rows["market_id"]))
    if em.get("status") != "complete":
        return None
    e = ext.set_index("market_id").reindex(rows["market_id"].astype(str))
    have = e["fee_type"].notna().to_numpy()
    sp = c.sports_flags(e["fee_type"].fillna(""), e["fee_category"].fillna(""), e["series_slugs"].fillna(""))
    mid_ = rows["market_id"].astype(str).to_numpy()
    ev = rows["event_id"].astype(str).to_numpy()
    d = pd.DataFrame({"market_id": mid_, "event": np.where(ev != "", ev, mid_), "vol": c.to_f64(rows["volume24hr"]), "fee_type": e["fee_type"].fillna("").to_numpy(),
                      "cat": e["fee_category"].fillna("").to_numpy()})
    d = d[have & ~sp].reset_index(drop=True)
    g = d.assign(v0=np.nan_to_num(d["vol"].to_numpy(float), nan=0.0)).groupby(["fee_type", "event"], sort=False).agg(vol=("v0", "sum"), cat=("cat", "first")).reset_index()
    ranks = {}
    for ft, sub in g.groupby("fee_type", sort=True):
        sub = sub.sort_values(["vol", "event"], ascending=[False, True], kind="mergesort")
        ranks[ft] = {"order": sub["event"].tolist(), "cat": dict(zip(sub["event"], sub["cat"], strict=True))}
    return {"t": meta["t"], "ranks": ranks, "d": d, "sidecar_missing_rows": int((~have).sum())}


def f_surge(cur: dict, prev: dict) -> tuple[dict, dict]:
    """E017's S label per (fee_type, event) at capture k: any member True; unknown iff every member's label is unknown (vol unknown or vol_{k-1} <= 0)."""
    d = cur["d"]
    vp = prev["d"].drop_duplicates("market_id").set_index("market_id")["vol"].reindex(d["market_id"]).to_numpy(float)
    vk = d["vol"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        known = np.isfinite(vk) & np.isfinite(vp) & (vp > 0)
        lab = known & (vk >= r.F_SURGE["ratio"] * vp) & (vk - vp >= r.F_SURGE["min_abs"])
    key = [d["fee_type"].to_numpy(dtype=object), d["event"].to_numpy(dtype=object)]
    s_any = pd.Series(lab).groupby(key).any().to_dict() if len(d) else {}
    k_any = pd.Series(known).groupby(key).any().to_dict() if len(d) else {}
    return s_any, k_any


def census_f(tree: c.PinnedTree) -> dict:
    """q0505 (section 3.4): rank churn at the candidate breakpoints, entries and exits across B per day, crossings with E017's surge label. Counts only; B is never chosen here."""
    by_slot = census_slots(tree)
    k_units = sorted(k for k in by_slot if r.utc_day(c.slot_time(k)) in r.CENSUS_DAYS_SF)
    res = {B: Counter() for B in r.F_BREAKPOINTS}
    per_day = {B: {d: Counter() for d in r.CENSUS_DAYS_SF} for B in r.F_BREAKPOINTS}
    cat_cross = {B: defaultdict(set) for B in r.F_BREAKPOINTS}
    per_ft = {B: defaultdict(Counter) for B in r.F_BREAKPOINTS}
    cnt = Counter()
    prev = f_capture(tree, by_slot[k_units[0] - 1]) if k_units and k_units[0] - 1 in by_slot else None
    for k in k_units:
        cur = f_capture(tree, by_slot[k])
        if cur is None or prev is None:
            cnt["pairs_sidecar_missing"] += 1
            prev = cur
            continue
        cnt["pairs"] += 1
        s_any, k_any = f_surge(cur, prev)
        day = r.utc_day(c.slot_time(k))
        for ft, rk in cur["ranks"].items():
            pk = prev["ranks"].get(ft)
            if pk is None:
                cnt["fee_type_new_at_k"] += 1
                continue
            ok_, op_ = rk["order"], pk["order"]
            pos_k = {e: i + 1 for i, e in enumerate(ok_)}
            pos_p = {e: i + 1 for i, e in enumerate(op_)}
            for B in r.F_BREAKPOINTS:
                lo, hi = max(1, B - r.F_HALF_WIDTH), B + r.F_HALF_WIDTH
                for p in range(lo, hi + 1):
                    a = ok_[p - 1] if p <= len(ok_) else None
                    b = op_[p - 1] if p <= len(op_) else None
                    if a is None and b is None:
                        continue
                    res[B]["positions"] += 1
                    per_ft[B][ft]["positions"] += 1
                    if a != b:
                        res[B]["changed"] += 1
                        per_ft[B][ft]["changed"] += 1
                entries = [e for e in ok_[:B] if pos_p.get(e, 10**9) > B]
                exits = [e for e in op_[:B] if pos_k.get(e, 10**9) > B]
                for kind, evs in (("entries", entries), ("exits", exits)):
                    res[B][kind] += len(evs)
                    per_day[B][day][kind] += len(evs)
                    per_ft[B][ft][kind] += len(evs)
                    for e in evs:
                        if s_any.get((ft, e)) is True:
                            res[B]["crossings_surge"] += 1
                        elif not k_any.get((ft, e), False):
                            res[B]["crossings_surge_unknown"] += 1
                        cat_cross[B][rk["cat"].get(e) or pk["cat"].get(e) or ""].add(e)
        prev = cur
    out = {"family": "F", "idea": "CH176", "job": "q0505", "counts": dict(cnt), "note": "B is never chosen, suggested or tie-broken from these shares (R1 finding 11)", "breakpoints": {}}
    nd = float(len(r.CENSUS_DAYS_SF))
    for B in r.F_BREAKPOINTS:
        c_ = res[B]
        cross = c_["entries"] + c_["exits"]
        out["breakpoints"][str(B)] = {"positions": c_["positions"], "changed": c_["changed"], "churn_share": _share(c_["changed"], c_["positions"]),
                                      "entries_per_day": c_["entries"] / nd, "exits_per_day": c_["exits"] / nd, "crossings": cross,
                                      "crossing_surge_share": _share(c_["crossings_surge"], cross), "crossings_surge_unknown": c_["crossings_surge_unknown"],
                                      "per_day": {d: dict(v) for d, v in per_day[B].items()}, "events_with_crossing_by_category": {k: len(v) for k, v in sorted(cat_cross[B].items())},
                                      "per_fee_type": {ft: {**dict(v), "churn_share": _share(v["changed"], v["positions"])} for ft, v in sorted(per_ft[B].items())}}
    return out


# =====================================================================================================================================================
# q0503: CB18-P census
# =====================================================================================================================================================

P_CAP_FIELDS = ("market_id", "condition_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "volume24hr", "end_date",
                "clob_token_id_0")
P_EXT_FIELDS = ("market_id", "fee_type", "fee_category", "series_slugs")


def p_quotes(tree: c.PinnedTree, cap_id: str, mids: set | None = None) -> tuple[pd.DataFrame, float]:
    keep = None if mids is None else (lambda ch: ch["market_id"].isin(mids).to_numpy())
    rows, _, meta = c.read_capture(tree, cap_id, P_CAP_FIELDS, keep=keep)
    d = pd.DataFrame(index=pd.Index(rows["market_id"].astype(str).to_numpy()))
    for col in ("best_bid", "best_ask", "spread", "last_trade_price", "volume24hr"):
        d[col] = c.to_f64(rows[col])
    d["spread_eff"] = np.where(np.isfinite(d["spread"]), d["spread"], d["best_ask"] - d["best_bid"])
    d["open"] = ~rows["closed"].map(cc.is_true).to_numpy(bool) & rows["active"].map(cc.is_true).to_numpy(bool) & (rows["binary"].astype(str).str.strip() == "1").to_numpy()
    d["end_s"] = c.epoch_s(rows["end_date"].to_numpy())
    d["event"] = np.where(rows["event_id"].astype(str).to_numpy() != "", rows["event_id"].astype(str).to_numpy(), rows["market_id"].astype(str).to_numpy())
    d["tok0"] = rows["clob_token_id_0"].astype(str).to_numpy()
    return d, meta["t"]


def census_p(tree: c.PinnedTree) -> dict:
    """q0503 (section 3.2): parallel quote-only re-centerings at k (LT3 classify, |x| >= 1c) among markets in both pass k's and pass k + 1's samples, coverage of (t_k, t_{k+1}],
    fade / follow / none / balanced by pass k + 1 sampling stratum, side usability, DE, series family share, permutable shares and the c_pre proxy SE. Reads no price after capture k
    (capture k + 1 only for its receipt time, through the sample's origin)."""
    by_slot = census_slots(tree)
    slot_by_cap = {cid: k for k, cid in by_slot.items()}
    samples = {}
    for sid in tree.ids("trade_samples"):
        man = json.loads(tree.path("trade_samples", sid, "manifest.json").read_text())
        k = slot_by_cap.get(str(man.get("snapshot_id")))
        if k is None or man.get("frame") != "active":
            raise Refused(f"sample {sid}: capture {man.get('snapshot_id')} not pinned or frame {man.get('frame')!r}")
        samples[k] = sid
    pairs = [(k, k + 1) for k in sorted(samples) if k + 1 in samples]
    day_slots = sorted(k for k in by_slot if r.utc_day(c.slot_time(k)) in r.PR_SAMPLE_DAYS)
    cnt = Counter()
    cnt["pass_pairs_usable"] = len(pairs)
    cnt["pass_pairs_unavailable_unsealed"] = sum(1 for k in day_slots if k + 1 in day_slots) - len(pairs)
    if len(pairs) != r.P_USABLE_PASS_PAIRS:
        raise Refused(f"census P: {len(pairs)} usable pass pairs != {r.P_USABLE_PASS_PAIRS} declared")
    spec = {"move": r.P_MOVE}
    units = []
    for k, k1 in pairs:
        smp_k = c.read_sample(tree, samples[k], r.TRADE_FIELDS_P)
        smp_1 = c.read_sample(tree, samples[k1], r.TRADE_FIELDS_P)
        both = set(smp_k["members"]) & set(smp_1["members"])
        cnt["members_k1"] += len(smp_1["members"])
        cnt["members_both"] += len(both)
        Q = {}
        for j in (k - 4, k - 2, k - 1, k):
            if j not in by_slot:
                Q[j] = None
                continue
            Q[j] = p_quotes(tree, by_slot[j], set(smp_1["members"]) if j in (k - 1, k) else both)
        qk, t_k = Q[k]
        if Q[k - 1] is None:
            cnt["no_capture_k_minus_1"] += 1
            continue
        qp, t_p = Q[k - 1]
        feat1 = smp_1["features"].drop_duplicates("market_id").set_index("market_id")
        org1 = pd.Series(c.epoch_s(feat1["origin_utc"].to_numpy()), index=feat1.index)  # each market's pass k + 1 origin (its capture k + 1 page receipt); no capture k + 1 price is read
        ext, _, em = c.read_sidecar(tree, by_slot[k], P_EXT_FIELDS, market_ids=set(qk.index))
        mk = sorted(set(qk.index) & set(qp.index))
        a, b = qp.reindex(mk), qk.reindex(mk)
        cls, geom = l3.classify(a["best_bid"], a["best_ask"], b["best_bid"], b["best_ask"], a["last_trade_price"], b["last_trade_price"], a["volume24hr"], b["volume24hr"], spec)
        x = ((b["best_bid"] + b["best_ask"]) / 2.0 - (a["best_bid"] + a["best_ask"]) / 2.0).to_numpy(float)
        with np.errstate(invalid="ignore"):
            elig = (a["open"].to_numpy(bool) & b["open"].to_numpy(bool) & (a["best_bid"] > 0).to_numpy() & (a["best_bid"] < a["best_ask"]).to_numpy() & (a["best_ask"] <= 1).to_numpy()
                    & (b["best_bid"] > 0).to_numpy() & (b["best_bid"] < b["best_ask"]).to_numpy() & (b["best_ask"] <= 1).to_numpy()
                    & (a["spread_eff"] <= r.P_SPREAD_MAX + r.QUOTE_TOL).to_numpy() & (b["spread_eff"] <= r.P_SPREAD_MAX + r.QUOTE_TOL).to_numpy())
            midk = ((b["best_bid"] + b["best_ask"]) / 2.0).to_numpy(float)
            elig &= (midk >= r.P_MID_RANGE[0] - r.QUOTE_TOL) & (midk <= r.P_MID_RANGE[1] + r.QUOTE_TOL)
            endk = b["end_s"].to_numpy(float)
            t1 = org1.reindex(mk).to_numpy(float)
            elig &= np.isfinite(t1) & (~np.isfinite(endk) | (endk > t1 + r.P_END_AFTER_NEXT_H * 3600.0))
        mover = elig & (cls == "quote_only") & (geom == "parallel") & (np.abs(x) >= r.P_MOVE["min_abs_x"] - 1e-12)
        mk_arr = np.asarray(mk, dtype=object)
        in_both = np.isin(mk_arr, list(both))
        in_k1 = np.isin(mk_arr, list(smp_1["members"]))
        cnt["recenterings_all"] += int(mover.sum())
        cnt["recenterings_in_k1_frame"] += int((mover & in_k1).sum())
        cnt["recenterings_dropped_by_both_frames"] += int((mover & in_k1 & ~in_both).sum())
        sel = mover & in_both
        if not sel.any():
            continue
        ms = mk_arr[sel]
        s = np.sign(x[sel])
        ex = ext.set_index("market_id").reindex(ms) if em.get("status") == "complete" else None
        sports = c.sports_flags(ex["fee_type"].fillna(""), ex["fee_category"].fillna(""), ex["series_slugs"].fillna("")) if ex is not None else np.zeros(len(ms), bool)
        fam = ex["series_slugs"].fillna("").to_numpy() if ex is not None else np.full(len(ms), "")
        f1 = feat1.reindex(ms)
        t_k1 = org1.reindex(ms).to_numpy(float)
        status_ok = (f1["status"] == "ok").to_numpy()
        n_ret = pd.to_numeric(f1["n_returned"], errors="coerce").to_numpy(float)
        tr = smp_1["trades"]
        tr = tr[tr["market_id"].astype(str).isin(set(ms))].copy()
        tr["tsv"] = pd.to_numeric(tr["ts"], errors="coerce").to_numpy(float)
        tr["market_id"] = tr["market_id"].astype(str)
        tr["sg"] = l3.signs(tr, pd.Series(qk["tok0"].to_numpy(), index=qk.index))
        tr["t1"] = pd.Series(t_k1, index=ms).reindex(tr["market_id"]).to_numpy(float)
        tr["nt"] = pd.to_numeric(tr["size"], errors="coerce").to_numpy(float) * pd.to_numeric(tr["price"], errors="coerce").to_numpy(float)
        oldest = tr.groupby("market_id")["tsv"].min().reindex(ms).to_numpy(float)
        with np.errstate(invalid="ignore"):
            covered = status_ok & ((n_ret < 500) | (np.isfinite(oldest) & (oldest <= t_k)))
        with np.errstate(invalid="ignore"):
            win = tr[(tr["tsv"] > t_k) & (tr["tsv"] <= tr["t1"])]
        cnt["state_window_rows"] += len(win)
        cnt["state_window_rows_side_unusable"] += int((win["sg"] == 0).sum())
        fsum = (win["sg"] * win["nt"]).groupby(win["market_id"]).sum()
        nrows = win.groupby("market_id").size().reindex(ms).fillna(0).to_numpy(int)
        fv = fsum.reindex(ms).fillna(0.0).to_numpy(float)
        state = np.array([r.p_state(f_, n_, int(s_)) for f_, n_, s_ in zip(fv, nrows, s, strict=True)], dtype=object)
        m2, ok2 = _p_mid(Q.get(k - 2), ms)
        m4, ok4 = _p_mid(Q.get(k - 4), ms)
        strat = np.array([smp_1["members"].get(m_) for m_ in ms], dtype=object)
        for i, m_ in enumerate(ms):
            units.append({"market_id": m_, "event": b.loc[m_, "event"], "k": k, "t": t_k, "s": int(s[i]), "absx": abs(float(x[sel][i])), "spread": float(b.loc[m_, "spread_eff"]),
                          "vol": float(b.loc[m_, "volume24hr"]), "sports": bool(sports[i]), "family": str(fam[i])[:80], "covered": bool(covered[i]), "status_ok": bool(status_ok[i]),
                          "state": state[i], "rows": int(nrows[i]), "stratum": strat[i], "c_pre": float(s[i]) * (m2[i] - m4[i]) * 100.0 if (ok2[i] and ok4[i]) else math.nan})
    U = pd.DataFrame(units)
    return summarize_p(U, cnt)


def _p_mid(q: tuple | None, ms) -> tuple[np.ndarray, np.ndarray]:
    if q is None:
        return np.full(len(ms), np.nan), np.zeros(len(ms), bool)
    d = q[0].reindex(ms)
    bid, ask = d["best_bid"].to_numpy(float), d["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        ok = (bid > 0) & (bid < ask) & (ask <= 1)
    return np.where(ok, (bid + ask) / 2.0, np.nan), ok


def p_population(U: pd.DataFrame, nonsports: bool) -> dict:
    if U.empty:
        return {"units": 0}
    P = U[~U["sports"]] if nonsports else U
    cov = P[P["status_ok"]]
    trunc = int((~cov["covered"]).sum())
    E = cov[cov["covered"]]
    st = E["state"].value_counts().to_dict()
    fade, follow = st.get("fade", 0), st.get("follow", 0)
    pop = E[E["state"].isin(["fade", "none"])]
    per_m = pop.groupby("market_id").size()
    eff = pop[pop["market_id"].map(per_m).to_numpy() >= 2]
    n_fade_eff = int((eff["state"] == "fade").sum())
    n_none_eff = int((eff["state"] == "none").sum())
    proj = r.P_PROJECTION_PAIRS / r.P_USABLE_PASS_PAIRS
    fades_ev = E[E["state"] == "fade"].groupby("event").size().to_numpy()
    m = r.m_by_event(fades_ev) if len(fades_ev) else math.nan
    days = r.P_USABLE_PASS_PAIRS / 12.0
    de_c, de28 = r.de_computed(m, days, days), r.de_computed(m, r.W_LT_DAYS, days)
    mf = r.mde_formula(r.M_LT, r.SD_P_C, n_fade_eff * proj, n_none_eff * proj, r.de_gate(m, r.W_LT_DAYS, days))
    S = E[E["state"].isin(["fade", "follow", "none"])]
    se = p_proxy_se(S)
    mp = r.mde_gp5_proxy(se["se_c"], de28, de_c) if se.get("se_c") is not None else math.nan
    shares = {lv: r.permutable_share(((r.perm_stratum(lv, mk, t), int(st_ == "fade")) for mk, t, st_ in zip(pop["market_id"], pop["t"], pop["state"], strict=True)))["share"] if len(pop) else None for lv in r.PERM_LADDER}
    fam = E[E["state"] == "fade"]["family"].value_counts()
    by_strat = {str(k): v for k, v in E.groupby(["stratum", "state"]).size().unstack(fill_value=0).to_dict(orient="index").items()} if len(E) else {}
    gi = {"fades_28d_projected": fade * proj, "fade_share_of_reacted": _share(fade, fade + follow), "truncated_share": _share(trunc, len(cov)), "mde_gp5_c": r.mde_gp5(mf, mp),
          "gp6_level": r.select_level(shares)}
    return {"units": int(len(P)), "status_not_ok": int((~P["status_ok"]).sum()), "truncated": trunc, "covered": int(len(E)), "states": {k: int(v) for k, v in st.items()},
            "fades_per_day": fade / days, "fade_eff": n_fade_eff, "none_eff": n_none_eff, "m": _f(m), "de_census": _f(de_c), "de_w28": _f(de28), "mde_formula_c": _f(mf), "mde_proxy_c": _f(mp),
            "proxy_se": se, "permutable_share_by_level": shares, "top_family_share_of_fades": _share(int(fam.iloc[0]) if len(fam) else 0, fade), "by_k1_stratum": by_strat, "gate_inputs": gi}


def p_proxy_se(S: pd.DataFrame) -> dict:
    S = S[np.isfinite(S["c_pre"].to_numpy(float))] if len(S) else S
    if not len(S):
        return {"n": 0, "se_c": None}
    strata = sorted({str(x) for x in S["stratum"]})
    dums = [(S["stratum"].astype(str) == st_).to_numpy(float) for st_ in strata[1:]]
    X = np.column_stack([(S["state"] == "fade").to_numpy(float), (S["state"] == "follow").to_numpy(float), np.log(S["absx"].to_numpy(float)), S["spread"].to_numpy(float),
                         np.log1p(S["vol"].to_numpy(float)), *dums])
    res = c.proxy_se(S["c_pre"].to_numpy(float), X, list(S["market_id"]), {"event": list(S["event"]), "block6": [r.block6(t) for t in S["t"]]})
    res["se_c"] = _f(res["se_c"])
    return res


def summarize_p(U: pd.DataFrame, cnt: Counter) -> dict:
    out = {"family": "P", "idea": "CH172", "job": "q0503", "counts": dict(cnt)}
    ns, al = p_population(U, True), p_population(U, False)
    side_share = _share(cnt["state_window_rows_side_unusable"], cnt["state_window_rows"])
    for d in (ns, al):
        if "gate_inputs" in d:
            d["gate_inputs"]["side_unusable_share"] = side_share
    gns = r.gp_gates(ns["gate_inputs"]) if "gate_inputs" in ns else {}
    gal = r.gp_gates(al["gate_inputs"]) if "gate_inputs" in al else {}
    out.update({"non_sports": ns, "all_categories": al, "side_unusable_share": side_share, "gates_non_sports": gns, "gates_all": gal, "route": r.route_p(gns, gal)})
    pop = out["route"].get("population")
    lvl = (ns if pop == "non-sports" else al).get("gate_inputs", {}).get("gp6_level") if pop else None
    out["census_to_spec"] = {"population": pop, "strata_level": lvl}
    return out


# =====================================================================================================================================================
# routing record (section 3; orchestrator, after q0502-q0506)
# =====================================================================================================================================================


def routing_record(results: dict[str, Path], rules_sha256: str) -> dict:
    """seals/cb18_routing.json content: each idea's route by section 3's rules only, both S MDEs, P's GP5 values, the census files' sha256. Counts 0 (cb18_descriptive)."""
    rec: dict = {"rules_version": r.RULES_VERSION, "rules_pre_sha256": rules_sha256, "inputs": {}, "routes": {}}
    for fam, p in results.items():
        if p is None or not Path(p).exists():
            rec["routes"][fam] = {"route": "not run", "reason": "census output absent"}
            continue
        rec["inputs"][fam] = {"file": Path(p).name, "sha256": c.sha256_file(Path(p))}
        doc = json.loads(Path(p).read_text())
        if fam == "S":
            rec["routes"]["S"] = {**doc["route"], "census_to_spec": doc.get("census_to_spec")}
        elif fam == "P":
            rec["routes"]["P"] = {**doc["route"], "mde_formula_c": (doc.get("non_sports") or {}).get("mde_formula_c"), "mde_proxy_c": (doc.get("non_sports") or {}).get("mde_proxy_c"),
                                  "gates_non_sports": doc.get("gates_non_sports"), "gates_all": doc.get("gates_all"), "census_to_spec": doc.get("census_to_spec")}
        elif fam == "R":
            rec["routes"]["R"] = {"route": "map only (k = 0)", "quantised_label": doc.get("ts_quantised")}
        elif fam == "F":
            rec["routes"]["F"] = {"route": "census only (k = 0); re-entry rule section 4.4"}
        elif fam == "M":
            rec["routes"]["M"] = {"route": "map (k = 0); its days are worn for every resolution arm"}
    r.assert_clean_result(rec)
    return rec
