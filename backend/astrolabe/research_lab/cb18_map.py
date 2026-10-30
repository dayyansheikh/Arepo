# ruff: noqa: E501
"""CB18 maps: q0504 the race map (CB18-R, CH179; descriptive, no gates, no route) and q0506 the last-mid map (CB18-M, CH175) (docs/research_lab/CREATIVE_BATCH_18.md sections 3.3,
4.3, 4.5). k = 0; counts and shares only.

Race map: the 23 sealed samples' pre-origin rows in [t - 6 h, t) of covered markets (E016's rule) and the sidecar of each sample's own capture k (category only; no price). tx_hash is
used in memory for the partner test and never written. No target, no flow statistic, no later price.

Last-mid map: exits from the listing on the worn captures [2026-10-12T00:31Z, 2026-10-16T00:00Z) by the FOLDED band of the last two-sided mid (d = |mid - 0.5|; no side), with
gap_adjacent exits flagged. No comparison of an earlier price with the last mid, no return, no P&L.
"""

from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np
import pandas as pd

from . import cb17_census as cc
from . import cb18_common as c
from . import cb18_rules_pre as r
from . import live_tests3 as l3

Refused = r.Refused


def _share(num, den) -> float | None:
    return (float(num) / float(den)) if den else None


def price_band(p: float) -> str:
    if not r.finite(p):
        return "unknown"
    e = r.R_PRICE_BAND_EDGES
    return "lt0.10" if p < e[0] else "0.10-0.30" if p < e[1] else "0.30-0.70" if p <= e[2] else "0.70-0.90" if p <= e[3] else "gt0.90"


def raced_mask(ts: np.ndarray, tx: np.ndarray) -> np.ndarray:
    """R_RACE_RULE on ONE market's rows: raced iff another row has the same ts and a different, non-blank tx_hash."""
    n = len(ts)
    out = np.zeros(n, bool)
    if n < 2:
        return out
    d = pd.DataFrame({"ts": ts, "tx": tx})
    for _, g in d.groupby("ts", sort=False):
        if len(g) < 2:
            continue
        txs = g["tx"].to_numpy(dtype=object)
        for i, idx in enumerate(g.index):
            t = txs[i]
            if t in ("", None):
                continue
            if any((o not in ("", None)) and o != t for o in txs):
                out[idx] = True
    return out


def raced_pairs(rows: pd.DataFrame) -> tuple[int, int, int]:
    """(raced pairs, fingerprint-identical pairs: same side, outcome, size and price; same-side pairs) over one market's rows (pairs of rows with equal ts, different non-blank tx)."""
    n_pairs = n_fp = n_side = 0
    for _, g in rows.groupby("ts", sort=False):
        if len(g) < 2:
            continue
        v = g[["tx_hash", "side", "outcome_index", "size", "price"]].to_numpy(dtype=object)
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                if v[i][0] in ("", None) or v[j][0] in ("", None) or v[i][0] == v[j][0]:
                    continue
                n_pairs += 1
                same_side = v[i][1] == v[j][1]
                n_side += int(same_side)
                n_fp += int(same_side and v[i][2] == v[j][2] and v[i][3] == v[j][3] and v[i][4] == v[j][4])
    return n_pairs, n_fp, n_side


def quantised(gaps: Counter) -> bool | None:
    tot = sum(gaps.get(g, 0) for g in r.R_GAP_HIST_S)
    if tot < r.R_QUANTISED_MIN_GAPS:
        return None
    return gaps.get(1, 0) / tot < r.R_QUANTISED_ONE_S_MAX


def map_race(tree: c.PinnedTree) -> dict:
    """q0504 (section 3.3)."""
    by_cap = {cid: c.slot_of(c.stamp_epoch(cid)) for cid in tree.ids("snapshots")}
    cnt = Counter()
    units = []
    rowtab = []
    gaps: Counter = Counter()
    pair_tot = Counter()
    for sid in tree.ids("trade_samples"):
        smp = c.read_sample(tree, sid, r.TRADE_FIELDS_R)
        cap = str(smp["manifest"]["snapshot_id"])
        if cap not in by_cap or smp["manifest"]["frame"] != "active":
            raise Refused(f"sample {sid}: capture {cap} not pinned or not an active frame")
        plan = json.loads(tree.path("trade_samples", sid, "plan.json").read_text())
        tok0 = pd.Series({str(m["market_id"]): (m.get("token0") or "") for m in plan.get("sample", [])}, dtype=object)
        feat = smp["features"].drop_duplicates("market_id").set_index("market_id")
        ok = feat[feat["status"] == "ok"]
        cnt["sampled"] += len(feat)
        cnt["status_ok"] += len(ok)
        ext, _, em = c.read_sidecar(tree, cap, ("market_id", "fee_type", "fee_category", "series_slugs"), market_ids=set(ok.index))
        ex = ext.set_index("market_id").reindex(ok.index) if em.get("status") == "complete" else pd.DataFrame(index=ok.index, columns=["fee_type", "fee_category", "series_slugs"])
        sports = c.sports_flags(ex["fee_type"].fillna(""), ex["fee_category"].fillna(""), ex["series_slugs"].fillna(""))
        cat = np.where(ex["fee_category"].isna().to_numpy(), "sidecar_missing", ex["fee_category"].fillna("").astype(str).to_numpy())
        catd = dict(zip(ok.index, [f"{'sports' if s else 'non_sports'}:{k}" for s, k in zip(sports, cat, strict=True)], strict=True))
        org = pd.Series(c.epoch_s(ok["origin_utc"].to_numpy()), index=ok.index)
        n_ret = pd.to_numeric(ok["n_returned"], errors="coerce")
        tr = smp["trades"].copy()
        tr["market_id"] = tr["market_id"].astype(str)
        tr = tr[tr["market_id"].isin(set(ok.index))]
        tr["tsv"] = pd.to_numeric(tr["ts"], errors="coerce").to_numpy(float)
        oldest = tr.groupby("market_id")["tsv"].min().reindex(ok.index)
        covered = (n_ret < 500) | (oldest <= org - r.R_WINDOW_S)
        cnt["covered"] += int(covered.sum())
        tr["o"] = org.reindex(tr["market_id"]).to_numpy(float)
        tr["sg"] = l3.signs(tr, tok0)
        with np.errstate(invalid="ignore"):
            w = tr[(tr["tsv"] >= tr["o"] - r.R_WINDOW_S) & (tr["tsv"] < tr["o"]) & (tr["sg"] != 0) & tr["market_id"].map(covered).fillna(False).to_numpy(bool)]
        for mk, g in w.groupby("market_id", sort=False):
            if len(g) < r.R_MIN_SIGNED_ROWS:
                cnt["covered_lt3_rows"] += 1
                continue
            g = g.reset_index(drop=True)
            ts = g["tsv"].to_numpy(float)
            rm = raced_mask(ts, g["tx_hash"].astype(str).to_numpy(dtype=object))
            npair, nfp, nside = raced_pairs(g.assign(ts=ts))
            pair_tot["pairs"] += npair
            pair_tot["fingerprint_identical"] += nfp
            pair_tot["same_side"] += nside
            dts = np.unique(ts[np.isfinite(ts)])
            for gp in np.diff(dts).astype(int):
                gaps[int(gp) if gp <= 10 else 11] += 1
            cnt["rows"] += len(g)
            cnt["rows_raced"] += int(rm.sum())
            cnt["rows_ts_not_minute"] += int((np.mod(ts, 60) != 0).sum())
            units.append({"n": len(g), "raced": int(rm.sum()), "cat": catd.get(mk, "unknown")})
            rowtab.append(pd.DataFrame({"hour": ((ts % 86400) // 3600).astype(int), "band": [price_band(p) for p in pd.to_numeric(g["price"], errors="coerce").to_numpy(float)],
                                        "raced": rm, "cat": catd.get(mk, "unknown"), "unit": len(units) - 1}))
    U = pd.DataFrame(units)
    q = quantised(gaps)
    label = "same block" if q else "same second"
    out = {"family": "R", "idea": "CH179", "job": "q0504", "k": 0, "label_same_ts": label, "ts_quantised": q, "quantised_rule": r.R_QUANTISED_RULE, "counts": dict(cnt),
           "units": int(len(U)), "raced_row_share": _share(cnt["rows_raced"], cnt["rows"]), "ts_not_minute_share": _share(cnt["rows_ts_not_minute"], cnt["rows"]),
           "gap_hist_s": {("gt10" if k == 11 else str(k)): int(v) for k, v in sorted(gaps.items())}, "pairs": dict(pair_tot),
           "fingerprint_identical_share_of_pairs": _share(pair_tot["fingerprint_identical"], pair_tot["pairs"]), "same_side_share_of_pairs": _share(pair_tot["same_side"], pair_tot["pairs"])}
    if len(U):
        Rr = U["raced"] / U["n"]
        out["R_distribution"] = {"share_R_zero": float((Rr == 0).mean()), "quantiles": {str(k): float(v) for k, v in Rr.quantile([0.5, 0.75, 0.9, 0.99, 1.0]).items()}}
        rt = pd.concat(rowtab, ignore_index=True)
        dec = pd.qcut(U["n"].rank(method="first"), r.R_DECILES, labels=False) if len(U) >= r.R_DECILES else pd.Series(0, index=U.index)
        rt["decile"] = dec.reindex(rt["unit"]).to_numpy()
        out["race_map"] = {name: {str(k): {"rows": int(v["raced"].size), "raced_share": float(v["raced"].mean())} for k, v in rt.groupby(col)} for name, col in
                           (("by_category", "cat"), ("by_utc_hour", "hour"), ("by_row_count_decile", "decile"), ("by_price_band", "band"))}
    out["header"] = f"every 'same second' in this map reads '{label}' (R_QUANTISED_RULE); descriptive only, k = 0, no target, no moderator test (R1 finding 1)"
    return out


# =====================================================================================================================================================
# q0506: the last-mid map
# =====================================================================================================================================================

M_CAP_FIELDS = ["market_id", "condition_id", "received_utc", "event_id", "best_bid", "best_ask", "end_date", "neg_risk"]


def m_capture(tree: c.PinnedTree, cap_id: str) -> tuple[pd.DataFrame, float]:
    """Every listed market of a capture (compacted per chunk): mid if two-sided (else NaN), as-of end, neg-risk flag, event; one row per market id (first in page order)."""
    r.guard_census_time(c.stamp_epoch(cap_id), f"capture {cap_id}", r.MAP_CUTOFF)
    man = json.loads(tree.path("snapshots", cap_id, "manifest.json").read_text())
    if man.get("state") != "complete":
        raise Refused(f"capture {cap_id} is not complete")
    parts = []
    tmax = -math.inf
    for ch in c.iter_chunks(tree.path("snapshots", cap_id, "rows.csv.gz"), M_CAP_FIELDS):
        bid, ask = c.to_f64(ch["best_bid"]), c.to_f64(ch["best_ask"])
        with np.errstate(invalid="ignore"):
            ts2 = (bid > 0) & (bid < ask) & (ask <= 1)
        rec = c.epoch_s(ch["received_utc"].to_numpy())
        if np.isfinite(rec).any():
            tmax = max(tmax, float(np.nanmax(rec)))
        mid_ = ch["market_id"].astype(str).to_numpy(dtype=object)
        ev = ch["event_id"].astype(str).to_numpy(dtype=object)
        parts.append(pd.DataFrame({"market_id": mid_, "event": np.where(ev != "", ev, mid_), "mid": np.where(ts2, (bid + ask) / 2.0, np.nan),
                                   "end_s": c.epoch_s(ch["end_date"].to_numpy()), "neg_risk": ch["neg_risk"].map(cc.is_true).to_numpy(bool)}))
    d = pd.concat(parts, ignore_index=True)
    d = d[~d["market_id"].duplicated()].set_index("market_id")
    r.guard_census_time(tmax, f"capture {cap_id} last page", r.MAP_CUTOFF)
    size = d.groupby("event").size()
    d["structure"] = np.where(d["neg_risk"].to_numpy(bool), "neg_risk_member", np.where(d["event"].map(size).to_numpy() > 1, "other_multi", "standalone"))
    ext, _, em = c.read_sidecar(tree, cap_id, ("market_id", "fee_type", "fee_category", "series_slugs"))
    if em.get("status") == "complete":
        e = ext.set_index("market_id").reindex(d.index)
        sp = c.sports_flags(e["fee_type"].fillna(""), e["fee_category"].fillna(""), e["series_slugs"].fillna(""))
        d["sports"] = np.where(e["fee_type"].isna().to_numpy(), "unknown", np.where(sp, "sports", "non_sports"))
    else:
        d["sports"] = "unknown"
    return d, tmax


def horizon_bin(end_s: float, t: float) -> str:
    if not r.finite(end_s):
        return "unknown"
    h = (end_s - t) / 3600.0
    return "past_end" if h < 0 else "0-2h" if h <= 2 else "2-24h" if h <= 24 else "gt24h"


def lag_bin(h: float) -> str:
    if not r.finite(h):
        return "unknown_end"
    e = r.M_LAG_EDGES_H
    for i, x in enumerate(e):
        if h < x:
            return f"lt{x:g}h" if i == 0 else f"{e[i - 1]:g}..{x:g}h"
    return f"ge{e[-1]:g}h"


SPORTS_CODES = ("non_sports", "sports", "unknown")
STRUCT_CODES = ("standalone", "neg_risk_member", "other_multi")


class _Grow:
    """Per-market state arrays keyed by a growing id index (vectorised; no per-market Python objects)."""

    def __init__(self):
        self.ids = pd.Index([], dtype=object)
        self.a: dict[str, np.ndarray] = {}
        self.spec = {"last_j": (np.int32, -1), "t_last": (np.float64, np.nan), "mid_last": (np.float64, np.nan), "lts_mid": (np.float64, np.nan), "lts_t": (np.float64, np.nan),
                     "end_s": (np.float64, np.nan), "sports": (np.int8, 2), "structure": (np.int8, 0), "neg": (bool, False), "slot_last": (np.int32, -1), "event": (object, ""),
                     "exited": (bool, False), "band": (object, ""), "via": (object, ""), "lag_h": (np.float64, np.nan), "gap_adj": (bool, False), "reapp": (bool, False)}
        for k, (dt, fill) in self.spec.items():
            self.a[k] = np.full(0, fill, dtype=dt)

    def index_of(self, keys: pd.Index) -> np.ndarray:
        idx = self.ids.get_indexer(keys)
        new = keys[idx < 0]
        if len(new):
            self.ids = self.ids.append(pd.Index(new, dtype=object))
            for k, (dt, fill) in self.spec.items():
                self.a[k] = np.concatenate([self.a[k], np.full(len(new), fill, dtype=dt)])
            idx = self.ids.get_indexer(keys)
        return idx


def _bands(mid_last, lts_mid, t_last, lts_t) -> tuple[np.ndarray, np.ndarray]:
    band = np.array([r.fold_band(x) for x in mid_last], dtype=object)
    via = np.where(np.isfinite(mid_last), "at_last_presence", "none").astype(object)
    with np.errstate(invalid="ignore"):
        age = t_last - lts_t
    for w, name in zip(r.M_FALLBACK_WINDOWS_H, ("within_6h", "within_24h"), strict=True):
        m = ~np.isfinite(mid_last) & np.isfinite(lts_mid) & (via == "none") & (age <= w * 3600.0)
        band[m] = [r.fold_band(x) for x in lts_mid[m]]
        via[m] = name
    return band, via


def map_lastmid(tree: c.PinnedTree) -> dict:
    """q0506 (section 4.5)."""
    lo, hi = r.ep(r.MAP_START), r.ep(r.MAP_CUTOFF)
    caps = sorted(cid for cid in tree.ids("snapshots") if lo <= c.slot_time(c.slot_of(c.stamp_epoch(cid))) < hi)
    gap_prev_slot = min(c.unavailable_slots()) - 1
    G = _Grow()
    reappear = 0
    ts_by_j: list[float] = []
    for j, cid in enumerate(caps):
        d, t = m_capture(tree, cid)
        ts_by_j.append(t)
        slot = c.slot_of(c.stamp_epoch(cid))
        idx = G.index_of(d.index)
        a = G.a
        # an exit is judged on information up to its own time (confirmed at capture j): a later re-appearance is counted (flicker, once per market) and never undoes the exit nor
        # overwrites its record (2026-10-21 science-reviewer fix; the exit tables no longer depend on later captures)
        back = a["exited"][idx]
        reappear += int((back & ~a["reapp"][idx]).sum())
        a["reapp"][idx[back]] = True
        keep_rows = ~back
        d = d[keep_rows]
        idx = idx[keep_rows]
        mid = d["mid"].to_numpy(float)
        a["t_last"][idx] = t
        a["mid_last"][idx] = mid
        two = np.isfinite(mid)
        a["lts_mid"][idx[two]] = mid[two]
        a["lts_t"][idx[two]] = t
        a["end_s"][idx] = d["end_s"].to_numpy(float)
        a["sports"][idx] = pd.Series(d["sports"]).map({k: i for i, k in enumerate(SPORTS_CODES)}).fillna(2).to_numpy(np.int8)
        a["structure"][idx] = pd.Series(d["structure"]).map({k: i for i, k in enumerate(STRUCT_CODES)}).to_numpy(np.int8)
        a["neg"][idx] = d["neg_risk"].to_numpy(bool)
        a["event"][idx] = d["event"].to_numpy(dtype=object)
        a["slot_last"][idx] = slot
        a["last_j"][idx] = j
        if j >= 2:
            conf = np.flatnonzero((a["last_j"] == j - 2) & ~a["exited"])
            if len(conf):
                band, via = _bands(a["mid_last"][conf], a["lts_mid"][conf], a["t_last"][conf], a["lts_t"][conf])
                a["band"][conf], a["via"][conf] = band, via
                a["lag_h"][conf] = (ts_by_j[j - 1] - a["end_s"][conf]) / 3600.0
                a["gap_adj"][conf] = a["slot_last"][conf] == gap_prev_slot
                a["exited"][conf] = True
                a["last_j"][conf] = -10
        del d
    a = G.a
    J = len(caps) - 1
    ex = np.flatnonzero(a["exited"])
    det_caps = max(len(caps) - 2, 0)
    eff_days = det_caps * r.GRID_S / 86400.0
    out = {"family": "M", "idea": "CH175", "job": "q0506", "k": 0, "captures": len(caps), "effective_days": eff_days, "exit_rule": r.M_EXIT_RULE, "forbidden": r.M_FORBIDDEN,
           "undetermined": int((a["last_j"] == J - 1).sum()), "still_listed_at_end": int((a["last_j"] == J).sum()), "reappearances_after_exit": reappear,
           "gap_disclosure": {"gap_slots": list(r.UNAVAILABLE_CAPTURE_SLOTS), "last_slot_before_gap": c.slot_iso(gap_prev_slot)}, "exits": int(len(ex))}
    if not len(ex):
        return out
    E = pd.DataFrame({"t_last": a["t_last"][ex], "day": [r.utc_day(t) for t in a["t_last"][ex]], "band": a["band"][ex], "via": a["via"][ex],
                      "sports": [SPORTS_CODES[i] for i in a["sports"][ex]], "structure": [STRUCT_CODES[i] for i in a["structure"][ex]],
                      "horizon": [horizon_bin(e, t) for e, t in zip(a["end_s"][ex], a["t_last"][ex], strict=True)], "lag_h": a["lag_h"][ex], "gap_adjacent": a["gap_adj"][ex],
                      "event": a["event"][ex], "neg_risk": a["neg"][ex]})
    for tag, sub in (("all", E), ("without_gap_adjacent", E[~E["gap_adjacent"]])):
        o = {"exits": int(len(sub)), "gap_adjacent": int(sub["gap_adjacent"].sum())}
        o["per_day_by_band"] = {f"{d}|{b}": int(v) for (d, b), v in sub.groupby(["day", "band"]).size().items()}
        o["by_band_class"] = {f"{s}|{st}|{h}|{b}": int(v) for (s, st, h, b), v in sub.groupby(["sports", "structure", "horizon", "band"]).size().items()}
        o["no_two_sided_fallback"] = {str(k): int(v) for k, v in sub[sub["via"] != "at_last_presence"]["via"].value_counts().items()}
        o["lag_end_to_exit"] = {str(k): int(v) for k, v in sub["lag_h"].map(lag_bin).value_counts().sort_index().items()}
        o["middle_band_ids_per_day"] = {str(k): int(v) for k, v in sub[sub["band"] == "d_lt_0.45"].groupby("day").size().items()}
        tail = sub[sub["band"].isin(["d_gt_0.49", "d_0.45_0.49"]) & (sub["horizon"] != "unknown")]
        o["tail_band_exit_rate_per_day_known_end"] = {f"{s}|{st}": (float(v) / eff_days if eff_days else None) for (s, st), v in tail.groupby(["sports", "structure"]).size().items()}
        proj = {}
        for arm, desc in r.M_ARM_CLASSES.items():
            if arm == "CH163":
                m = (tail["sports"] == "non_sports") & tail["structure"].isin(["standalone", "neg_risk_member"])
            elif arm == "CH62":
                m = pd.Series(True, index=tail.index)
            else:
                m = tail["sports"] == "non_sports"
            per_day = float(m.sum()) / eff_days if eff_days else None
            proj[arm] = {"class": desc, "per_day": per_day, **{f"days_{w}": (per_day * w if per_day is not None else None) for w in r.M_PROJECTION_DAYS}}
        o["window_arithmetic"] = proj
        out[tag] = o
    # neg-risk events (members = markets whose last presence was a neg-risk member of that event) whose members all exit within 24 h
    allm = pd.DataFrame({"event": a["event"], "neg": a["neg"], "exited": a["exited"], "t_last": a["t_last"], "band": a["band"]})
    nr = allm[allm["neg"] & (allm["event"] != "")]
    full = all_tail = 0
    for _, g in nr.groupby("event"):
        if len(g) < 2 or not g["exited"].all():
            continue
        if g["t_last"].max() - g["t_last"].min() <= 86400.0:
            full += 1
            all_tail += int((g["band"] == "d_gt_0.49").all())
    out["negrisk_events_all_members_exit_within_24h"] = {"events": full, "all_members_d_gt_0.49": all_tail, "not_all": full - all_tail}
    return out
