"""Learned "surprise move" detector: labels, pre-event features, matched negatives, walk-forward
learning and fixed-budget evaluation (``docs/research_lab/SURPRISE_MOVE_DETECTOR.md``).

Nothing here identifies, labels or implies insider or informed trading. The object of study is a
*sharp, unanticipated price move* (a label defined on the public price series alone) and the
public, HMAC-hashed taker-flow conditions that precede it. Every result is
``evidence_role: exploratory_historical`` until a registered live test is scored.

Order of operations (governance): ``LABEL_SPEC`` was written, hashed and logged BEFORE any
feature was computed or looked at (``label_spec_sha256``); a change to it is a new version and
spends budget. The feature list ``FEATURE_SPEC`` was fixed before any model was fit.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from . import history_backfill as hb
from . import provenance

VERSION = "surprise-moves-v1"
EVIDENCE_ROLE = "exploratory_historical"
TRIAL_KIND_LABELS = "surprise_labels"
TRIAL_KIND_DATASET = "surprise_dataset"
TRIAL_KIND_ARM = "surprise_detector"
GRID_S = hb.GRID_S
POINT_LAG_S = hb.POINT_LAG_S
MAX_QUOTE_AGE_S = hb.MAX_QUOTE_AGE_S
DAY_S = 86400.0
NEW_DAYS_S = 7 * DAY_S  # "new" wallet: first seen within 7 days (live flow_features.NEW_DAYS)

# --- 1. label specification (fixed before any feature was computed) --------------------------

LABEL_SPEC: dict = {
    "version": "surprise-labels-v1",
    "price_source": "CLOB prices-history, outcome-0 token, 10-minute fidelity (history_backfill "
                    "h2_main); a point stamped t' is usable only after t' + POINT_LAG_S",
    "point_lag_s": POINT_LAG_S,
    "max_quote_age_s": MAX_QUOTE_AGE_S,
    "grid_s": GRID_S,
    "move": {
        "arrival": "first 10-minute point j (outside any cooloff) with |p_j - p_ref_j| >= min_move, "  # noqa: E501
                   "p_ref_j = as-of price at t_j - window_s (age <= max_quote_age_s)",
        "departure": "latest point i in [t_j - window_s, t_j) with |p_i - p_ref_j| < min_move / 3 "
                     "(the last point at which the price was still at its pre-move level)",
        "direction": "sign(p_j - p_ref_j), +1 = outcome-0 price up",
        "cooloff_s": 86400,
    },
    "primary": {"id": "sharp15_6h", "min_move": 0.15, "window_s": 21600},
    "variants": {
        "extreme10_6h": {"min_move": 0.10, "window_s": 21600,
                         "departure_price_outside": [0.20, 0.80]},
        "to_resolution_6h": {"min_move": 0.15, "window_s": 21600,
                             "reaches_within_window_s": 21600, "reach_beyond": [0.02, 0.98]},
    },
    "surprise_filters": {
        "pre_drift_24h_max_abs": 0.05,
        "pre_range_24h_max": 0.10,
        "pre_window_min_points": 6,
        "pre_window_unknown": "excluded (counted as unknown, never treated as flat)",
        "exclude_last_s_before_end": 3600,
        "end_source": "Gamma endDate as listed at fetch time (end_epoch); gameStartTime when "
                      "present in the metadata pull takes precedence for sports",
    },
    "origin_rule": "positive row = the 2h grid origin t_o = floor(t_dep / grid_s) * grid_s "
                   "(t_o <= t_dep); features use data strictly before t_o; lead_dep = t_dep - t_o, "
                   "lead_arr = t_arr - t_o; an event whose grid row is ineligible (no usable "
                   "quote, mid outside [0.02, 0.98], or traded_before_t != 1) is counted as "
                   "unlabellable and dropped",
    "training_label": "y = 1 iff a surprise departure falls in (t, t + grid_s]",
    "evaluation_hit": {"primary_window_s": 21600, "secondary_window_s": 7200,
                       "definition": "an alert at grid t hits iff a surprise departure falls in "
                                     "(t, t + window_s]; undirected"},
    "negatives": {
        "k_per_positive": 5,
        "clean_before_s": 86400, "clean_after_s": 86400,
        "pool": "grid rows with traded_before_t == 1, no departure (any variant) within "
                "clean_before_s after the row or clean_after_s before it",
        "match_on": ["fee_category", "price_band(|mid-0.5| cut at 0.05/0.20/0.45)",
                     "liquidity tercile of log1p(24h notional), cut on the full panel",
                     "hour-of-day bucket (6h, UTC)"],
        "same_market_allowed": True,
        "seed": "surprise-v1",
    },
    "exclusions": {
        "untraded_placeholder": "rows with traded_before_t != 1 are excluded everywhere",
        "mid_range": list(hb.MID_RANGE),
        "maduro_venezuela": "excluded from every training, validation and test table; "
                            "reported separately (in-sample months)",
        "case_catalogue": "excluded from every table; reported as held-out case recall",
    },
}


def label_spec_sha256(spec: dict = LABEL_SPEC) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
                          ).hexdigest()


def _asof(ts: np.ndarray, vals: np.ndarray, t: np.ndarray, max_age: float) -> np.ndarray:
    """As-of price for label construction (venue stamps, no causal lag: labels are outcomes)."""
    idx = np.searchsorted(ts, t, side="right") - 1
    ok = idx >= 0
    safe = np.where(ok, idx, 0)
    good = ok & ((t - ts[safe]) <= max_age)
    return np.where(good, vals[safe], np.nan)


def detect_events(ts: np.ndarray, vals: np.ndarray, *, end_epoch: float = math.nan,
                  min_move: float, window_s: float, spec: dict = LABEL_SPEC) -> pd.DataFrame:
    """Sharp moves of one market under ``spec`` (one ``min_move``/``window_s`` pair). One row per
    arrival; ``surprise`` is True only when every surprise filter passes; ``reason`` says why not.
    """
    cols = ["t_arr", "t_dep", "p_ref", "p_dep", "p_arr", "direction", "move", "pre_drift_24h",
            "pre_range_24h", "pre_points_24h", "reach_max_6h", "reach_min_6h", "surprise",
            "reason"]
    if len(ts) < 2:
        return pd.DataFrame(columns=cols)
    ts = np.asarray(ts, float)
    vals = np.asarray(vals, float)
    f = spec["surprise_filters"]
    max_age = float(spec["max_quote_age_s"])
    cool = float(spec["move"]["cooloff_s"])
    band = min_move / 3.0
    p_ref = _asof(ts, vals, ts - window_s, max_age)
    m = vals - p_ref
    cand = np.flatnonzero(np.isfinite(m) & (np.abs(m) >= min_move))
    out = []
    next_ok = -np.inf
    end_cut = (end_epoch - float(f["exclude_last_s_before_end"])) if math.isfinite(end_epoch) else (
        np.inf)
    for j in cand:
        if ts[j] < next_ok:
            continue
        lo = np.searchsorted(ts, ts[j] - window_s, side="left")
        ref = p_ref[j]
        inside = np.flatnonzero(np.abs(vals[lo:j] - ref) < band)
        if len(inside) == 0:  # the lag point itself is within band; defensive
            continue
        i = lo + inside[-1]
        t_dep, t_arr = ts[i], ts[j]
        next_ok = t_arr + cool
        w0 = np.searchsorted(ts, t_dep - DAY_S, side="left")
        pre = vals[w0:i + 1]
        p24 = _asof(ts, vals, np.array([t_dep - DAY_S]), max_age)[0]
        drift = vals[i] - p24 if np.isfinite(p24) else np.nan
        rng = float(pre.max() - pre.min()) if len(pre) else np.nan
        r6 = np.searchsorted(ts, t_dep + window_s, side="right")
        reach = vals[i:r6]
        reason = "ok"
        if len(pre) < int(f["pre_window_min_points"]) or not np.isfinite(drift):
            reason = "pre_window_unknown"
        elif abs(drift) >= float(f["pre_drift_24h_max_abs"]):
            reason = "pre_drift"
        elif rng >= float(f["pre_range_24h_max"]):
            reason = "pre_range"
        elif t_dep >= end_cut:
            reason = "final_hour_before_end"
        out.append([t_arr, t_dep, ref, vals[i], vals[j], float(np.sign(m[j])), float(m[j]),
                    drift, rng, int(len(pre)), float(reach.max()), float(reach.min()),
                    reason == "ok", reason])
    return pd.DataFrame(out, columns=cols)


def events_all_variants(ts: np.ndarray, vals: np.ndarray, *, end_epoch: float = math.nan,
                        spec: dict = LABEL_SPEC) -> pd.DataFrame:
    """Primary and variant events of one market, stacked with a ``variant`` column."""
    frames = []
    p = spec["primary"]
    e = detect_events(ts, vals, end_epoch=end_epoch, min_move=p["min_move"],
                      window_s=p["window_s"], spec=spec)
    e["variant"] = p["id"]
    frames.append(e)
    v = spec["variants"]["extreme10_6h"]
    e2 = detect_events(ts, vals, end_epoch=end_epoch, min_move=v["min_move"],
                       window_s=v["window_s"], spec=spec)
    lo, hi = v["departure_price_outside"]
    e2 = e2[(e2["p_dep"] <= lo) | (e2["p_dep"] >= hi)].copy()
    e2["variant"] = "extreme10_6h"
    frames.append(e2)
    r = spec["variants"]["to_resolution_6h"]
    blo, bhi = r["reach_beyond"]
    e3 = e[(e["reach_min_6h"] <= blo) | (e["reach_max_6h"] >= bhi)].copy()
    e3["variant"] = "to_resolution_6h"
    frames.append(e3)
    keep = [f for f in frames if len(f)]
    if not keep:
        return e.iloc[:0].copy()
    return pd.concat(keep, ignore_index=True)


# --- 2. pre-event features (fixed before any model was fit) ----------------------------------

WINDOWS: tuple[tuple[str, float], ...] = (("15m", 900.0), ("1h", 3600.0), ("6h", 21600.0),
                                          ("24h", 86400.0))
WINDOW_STATS = ("n", "log_notional", "imb", "large_rel", "burst", "n_wallets", "top1", "hhi",
                "same_side_share", "n_same_side", "new_n", "new_vol_share", "resp", "convex",
                "covered")
FEATURE_SPEC: dict = {
    "version": "surprise-features-v1",
    "windows_s": dict(WINDOWS),
    "per_window": {
        "n": "taker trades in (t - w, t)",
        "log_notional": "log1p(sum size * price_token0)",
        "imb": "signed share volume / volume in [-1, 1] (+ = buying outcome 0)",
        "large_rel": "largest trade size in the window / mean trade size over the 24h window",
        "burst": "n_w / (n_24h * w / 24h); 24h window: n_24h / (n_7d / 7) when covered",
        "n_wallets": "distinct hashed wallets",
        "top1": "largest wallet share of volume", "hhi": "Herfindahl of wallet volume shares",
        "same_side_share": "max(#net buyers, #net sellers) / (#net buyers + #net sellers)",
        "n_same_side": "max(#net buyers, #net sellers)",
        "new_n": "wallets whose first trade in the sample is within 7 days before t "
                 "(left-censored first-seen index, burn-in guarded; NaN during burn-in)",
        "new_vol_share": "volume share of those wallets",
        "resp": "sign(imb_w) * (mid(t) - mid(t - w)): price response in the flow's direction",
        "convex": "|signed notional_w| * (1 - p_acq) / p_acq / max(notional_24h, 100), "
                  "p_acq = mid if imb_w > 0 else 1 - mid",
        "covered": "1 if the window lies inside the fetched trade history, else 0 (stats NaN)",
    },
    "context": ["mid", "abs_mid_dev", "logit_mid", "dist_01", "log_hours_to_end", "market_age_h",
                "chg_1h", "chg_1d", "chg_1w", "own_vol", "rv_2h", "rv_6h", "rv_1d", "rv_7d",
                "hour_sin", "hour_cos", "dow", "last_trade_age_h", "ltp_minus_mid",
                "fee_category (one-hot of the sample's categories)", "decision_class (A/B/C from "
                "the frozen if_h1 class-v2 keyword rule on the Gamma question; 'unclassified' "
                "when no question is on file)", "sib_max_abs_chg_2h (max |mid - mid(t-2h)| over "
                "other markets of the same event at the same grid t)", "sib_n",
                "ladder_max_abs_chg_2h (same over markets whose question stem matches after "
                "removing dates and numbers)", "ladder_n"],
    "strictly_before_t": "every trade has ts < t; every price point has stamp + point_lag_s < t",
}


def _window_stats(tr_sorted: dict, t: np.ndarray, mid: np.ndarray, mid_lag: dict[str, np.ndarray],
                  covered_from: float, first_seen: hb.FirstSeen | None) -> dict[str, np.ndarray]:
    """Multi-window flow and wallet statistics at origins ``t`` (trades strictly before t)."""
    n = len(t)
    out = {f"sm_{s}_{w}": np.full(n, np.nan) for w, _ in WINDOWS for s in WINDOW_STATS}
    ts, sz, px, sgn, codes, fs = (tr_sorted[k] for k in ("ts", "sz", "px", "sgn", "codes", "fs"))
    hi = np.searchsorted(ts, t, side="left")
    cum_sz = np.concatenate([[0.0], np.cumsum(sz)])
    cum_sg = np.concatenate([[0.0], np.cumsum(sgn * sz)])
    cum_not = np.concatenate([[0.0], np.cumsum(sz * px)])
    cum_sgn_not = np.concatenate([[0.0], np.cumsum(sgn * sz * px)])
    burn_ok = np.zeros(n, bool)
    if first_seen is not None and not math.isnan(first_seen.g0):
        burn_ok = (t - NEW_DAYS_S) >= first_seen.g0 + hb.FIRST_SEEN_BURN_IN_S
    lo_w = {w: np.searchsorted(ts, t - s, side="left") for w, s in WINDOWS}
    full_w = {w: (t - s) >= covered_from for w, s in WINDOWS}
    lo7 = np.searchsorted(ts, t - 7 * DAY_S, side="left")
    full7 = (t - 7 * DAY_S) >= covered_from
    n24 = (hi - lo_w["24h"]).astype(float)
    not24 = cum_not[hi] - cum_not[lo_w["24h"]]
    with np.errstate(divide="ignore", invalid="ignore"):
        mean24 = np.where(n24 > 0, (cum_sz[hi] - cum_sz[lo_w["24h"]]) / np.maximum(n24, 1), np.nan)
        n7 = (hi - lo7).astype(float)
    for w, s in WINDOWS:
        lo, full = lo_w[w], full_w[w]
        cnt = (hi - lo).astype(float)
        vol = cum_sz[hi] - cum_sz[lo]
        with np.errstate(divide="ignore", invalid="ignore"):
            imb = np.where(vol > 0, (cum_sg[hi] - cum_sg[lo]) / vol, np.nan)
            if w == "24h":
                burst = np.where(full7 & (n7 > 0), cnt / (n7 / 7.0), np.nan)
            else:
                burst = np.where(full_w["24h"] & (n24 > 0), cnt / (n24 * s / DAY_S), np.nan)
            snot = np.abs(cum_sgn_not[hi] - cum_sgn_not[lo])
            p_acq = np.where(imb > 0, mid, np.where(imb < 0, 1.0 - mid, np.nan))
            convex = snot * (1.0 - p_acq) / p_acq / np.maximum(not24, 100.0)
            resp = np.sign(imb) * (mid - mid_lag[w])
        out[f"sm_covered_{w}"] = full.astype(float)
        out[f"sm_n_{w}"] = np.where(full, cnt, np.nan)
        out[f"sm_log_notional_{w}"] = np.where(full, np.log1p(cum_not[hi] - cum_not[lo]), np.nan)
        out[f"sm_imb_{w}"] = np.where(full, imb, np.nan)
        out[f"sm_burst_{w}"] = np.where(full, burst, np.nan)
        out[f"sm_convex_{w}"] = np.where(full & full_w["24h"], convex, np.nan)
        out[f"sm_resp_{w}"] = np.where(full & np.isfinite(imb) & (imb != 0), resp, np.nan)
        large = np.full(n, np.nan)
        nw = np.full(n, np.nan)
        top1 = np.full(n, np.nan)
        hhi = np.full(n, np.nan)
        sss = np.full(n, np.nan)
        nss = np.full(n, np.nan)
        new_n = np.full(n, np.nan)
        new_vs = np.full(n, np.nan)
        for i in np.flatnonzero(full):
            a, b = lo[i], hi[i]
            if b <= a:
                nw[i] = 0.0
                nss[i] = 0.0
                if burn_ok[i]:
                    new_n[i] = 0.0
                continue
            if full_w["24h"][i] and mean24[i] > 0:
                large[i] = sz[a:b].max() / mean24[i]
            c = codes[a:b]
            v = np.bincount(c, weights=sz[a:b])
            net = np.bincount(c, weights=sgn[a:b] * sz[a:b])
            active = v > 0
            vv = v[active]
            tot = vv.sum()
            nw[i] = float(active.sum())
            if tot > 0:
                sh = vv / tot
                top1[i] = sh.max()
                hhi[i] = float((sh ** 2).sum())
            nb, ns_ = int((net[active] > 0).sum()), int((net[active] < 0).sum())
            nss[i] = float(max(nb, ns_))
            if nb + ns_ > 0:
                sss[i] = max(nb, ns_) / (nb + ns_)
            if burn_ok[i]:
                is_new = fs[a:b] >= t[i] - NEW_DAYS_S
                new_n[i] = float(len(np.unique(c[is_new])))
                new_vs[i] = float(sz[a:b][is_new].sum() / tot) if tot > 0 else np.nan
        out[f"sm_large_rel_{w}"] = large
        out[f"sm_n_wallets_{w}"] = nw
        out[f"sm_top1_{w}"] = top1
        out[f"sm_hhi_{w}"] = hhi
        out[f"sm_same_side_share_{w}"] = sss
        out[f"sm_n_same_side_{w}"] = nss
        out[f"sm_new_n_{w}"] = new_n
        out[f"sm_new_vol_share_{w}"] = new_vs
    return out


def sort_trades(tr: pd.DataFrame, first_seen: hb.FirstSeen | None) -> dict:
    """Arrays for ``_window_stats`` (token-0 terms: BUY outcome 0 / SELL outcome 1 = +1)."""
    ts = tr["ts"].to_numpy(float)
    oi = tr["outcome_index"].to_numpy()
    px = np.where(oi == 0, tr["price"].to_numpy(float), 1 - tr["price"].to_numpy(float))
    sgn = np.where((tr["side"].to_numpy() == "BUY") == (oi == 0), 1.0, -1.0)
    sz = tr["size"].to_numpy(float)
    codes, uniq = pd.factorize(tr["wallet_hash"].astype(str).to_numpy())
    fs = (first_seen.lookup(uniq)[codes] if first_seen is not None and len(uniq)
          else np.full(len(ts), np.nan))
    order = np.argsort(ts, kind="stable")
    return {"ts": ts[order], "sz": sz[order], "px": px[order], "sgn": sgn[order],
            "codes": codes[order], "fs": fs[order]}


def surprise_features(tr: pd.DataFrame | None, t: np.ndarray, mid: np.ndarray, ts: np.ndarray,
                      vals: np.ndarray, covered_from: float,
                      first_seen: hb.FirstSeen | None = None) -> dict[str, np.ndarray]:
    """Multi-window features at origins ``t`` from trades (ts < t) and the causal price series."""
    n = len(t)
    if tr is None or not len(tr):
        out = {f"sm_{s}_{w}": np.full(n, np.nan) for w, _ in WINDOWS for s in WINDOW_STATS}
        for w, _ in WINDOWS:
            out[f"sm_covered_{w}"] = np.zeros(n)
        return out
    ts = np.asarray(ts, float)
    vals = np.asarray(vals, float)
    if len(ts) >= 1:
        mid_lag = {w: hb._asof(ts, vals, t - s, MAX_QUOTE_AGE_S)[0] for w, s in WINDOWS}
    else:  # no price series (live market without history): response terms stay NaN
        mid_lag = {w: np.full(n, np.nan) for w, _ in WINDOWS}
    return _window_stats(sort_trades(tr, first_seen), t, mid, mid_lag, covered_from, first_seen)


def feature_names() -> list[str]:
    return [f"sm_{s}_{w}" for w, _ in WINDOWS for s in WINDOW_STATS]


# --- 3. dataset assembly ---------------------------------------------------------------------

CONTEXT_MAP = {  # origin_frame column -> dataset column
    "mid_i": "mid", "ml_abs_mid_dev": "abs_mid_dev", "ml_logit_mid": "logit_mid",
    "ml_dist_01": "dist_01", "ml_log_hours_to_end": "log_hours_to_end",
    "ml_market_age_h": "market_age_h", "ml_chg_1h": "chg_1h", "ml_chg_1d": "chg_1d",
    "ml_chg_1w": "chg_1w", "ml_own_vol": "own_vol", "ml_rv_2h": "rv_2h", "ml_rv_6h": "rv_6h",
    "ml_rv_1d": "rv_1d", "ml_rv_7d": "rv_7d", "ml_tf_last_age_h": "last_trade_age_h",
    "ml_tf_ltp_minus_mid": "ltp_minus_mid",
}
KEEP_HISTORY = (*hb.TF_NAMES, *hb.WLT_NAMES, "ml_own_dmid_prev")  # for the frozen hand rules


def market_rows(rec: dict, ts: np.ndarray, vals: np.ndarray, tr: pd.DataFrame | None,
                truncated: bool, run_id: str, first_seen: hb.FirstSeen | None,
                end_epoch_override: float = math.nan) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Grid rows (features + outcomes + labels) and events of one market."""
    of = hb.origin_frame(rec, ts, vals, tr, truncated, run_id, first_seen)
    end_e = end_epoch_override if math.isfinite(end_epoch_override) else float(rec["end_epoch"])
    ev = events_all_variants(ts, vals, end_epoch=end_e)
    ev.insert(0, "market_id", rec["market_id"])
    if not len(of):
        return pd.DataFrame(), ev
    t = of["t_i"].to_numpy(float)
    mid = of["mid_i"].to_numpy(float)
    covered_from = float(tr["ts"].min()) if (tr is not None and len(tr)) else np.inf
    if tr is not None and not truncated:
        covered_from = -np.inf
    feats = surprise_features(tr if tr is not None and len(tr) else None, t, mid, ts, vals,
                              covered_from, first_seen)
    n = len(t)
    cols: dict = {"market_id": np.full(n, rec["market_id"], dtype=object),
                  "event_id": np.full(n, rec["event_id"] or "", dtype=object),
                  "condition_id": np.full(n, rec["condition_id"], dtype=object), "t": t,
                  "fee_category": np.full(n, rec["fee_category"], dtype=object),
                  "traded_before_t": of["traded_before_t"].to_numpy(float),
                  "quote_age_s": of["quote_age_s"].to_numpy(float)}
    for src, dst in CONTEXT_MAP.items():
        cols[dst] = of[src].to_numpy(float)
    for k in KEEP_HISTORY:
        cols[k] = of[k].to_numpy(float)
    hour = (t % DAY_S) / 3600.0
    cols["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    cols["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    cols["dow"] = ((t // DAY_S) + 3) % 7  # 1970-01-01 was a Thursday; Monday = 0
    cols.update(feats)
    last = ts[-1]
    for h in (2, 6, 24):
        tj = t + h * 3600.0
        mj = hb._asof(ts, vals, tj, MAX_QUOTE_AGE_S)[0]
        mj = np.where(tj <= last + MAX_QUOTE_AGE_S, mj, np.nan)
        cols[f"fwd_move_{h}h"] = mj - mid
    # labels from the primary surprise events (and the union of variants for the clean pool)
    surp = ev["surprise"].astype(bool).to_numpy() if len(ev) else np.zeros(0, bool)
    var = ev["variant"].astype(str).to_numpy() if len(ev) else np.zeros(0, dtype=object)
    tdep = ev["t_dep"].to_numpy(float) if len(ev) else np.zeros(0)
    win6 = float(LABEL_SPEC["evaluation_hit"]["primary_window_s"])
    dep = np.sort(tdep[surp & (var == LABEL_SPEC["primary"]["id"])])
    cols["y_dep_2h"] = _count_in(dep, t, 0.0, GRID_S) > 0
    cols["y_dep_6h"] = _count_in(dep, t, 0.0, win6) > 0
    nb = LABEL_SPEC["negatives"]
    cols["near_any_dep"] = _count_in(np.sort(tdep[surp]), t, -float(nb["clean_after_s"]),
                                     float(nb["clean_before_s"])) > 0
    for vid in ("extreme10_6h", "to_resolution_6h"):
        cols[f"y_{vid}_6h"] = _count_in(np.sort(tdep[surp & (var == vid)]), t, 0.0, win6) > 0
    return pd.DataFrame(cols), ev


def _count_in(sorted_pts: np.ndarray, t: np.ndarray, lo_off: float, hi_off: float) -> np.ndarray:
    """Number of ``sorted_pts`` in (t + lo_off, t + hi_off] per t."""
    if not len(sorted_pts):
        return np.zeros(len(t), int)
    a = np.searchsorted(sorted_pts, t + lo_off, side="right")
    b = np.searchsorted(sorted_pts, t + hi_off, side="right")
    return b - a


def build_dataset(run_dir: Path, out_dir: Path, *, meta: dict[str, dict] | None = None,
                  exclude_condition_ids: Iterable[str] = (), log=print) -> dict:
    """Stream every finished market of ``run_dir`` into ``rows.csv.gz`` and ``events.csv.gz``.
    ``meta`` (condition_id -> {question, game_start_ts, ...}) adds the decision class and the
    game-start end cut. ``exclude_condition_ids`` (Maduro/Venezuela, catalogue) are skipped."""
    import csv
    import gzip

    run_dir, out_dir = Path(run_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(run_dir / "sample.csv.gz", dtype=str, keep_default_na=False)
    prog = hb._read_progress(run_dir / "progress.jsonl")
    done = [m for m in sample["market_id"] if m in prog and prog[m]["status"] == "done"]
    fsi = hb.FirstSeen.build(run_dir / "trades" / f"{m}.csv.gz" for m in done)
    excl = set(exclude_condition_ids)
    meta = meta or {}
    counts = {"markets": 0, "rows": 0, "events": 0, "excluded_markets": 0, "no_rows": 0}
    rows_f = gzip.open(out_dir / "rows.csv.gz", "wt", newline="")
    ev_f = gzip.open(out_dir / "events.csv.gz", "wt", newline="")
    rw = ew = None
    try:
        for k, rec in enumerate(sample.to_dict("records")):
            mid_ = rec["market_id"]
            if mid_ not in prog or prog[mid_]["status"] != "done":
                continue
            if rec["condition_id"] in excl:
                counts["excluded_markets"] += 1
                continue
            for c in ("liquidity", "volume", "start_epoch", "end_epoch", "close_epoch"):
                rec[c] = float("nan") if rec[c] in ("", "nan") else float(rec[c])
            ts, vals = hb.load_prices(run_dir / "prices" / f"{mid_}.csv.gz")
            tr = hb.load_trades(run_dir / "trades" / f"{mid_}.csv.gz")
            m = meta.get(rec["condition_id"], {})
            gs = float(m.get("game_start_ts") or "nan")
            rows, ev = market_rows(rec, ts, vals, tr, bool(prog[mid_]["trades_truncated"]),
                                   run_dir.name, fsi, end_epoch_override=gs)
            ev["decision_class"] = m.get("decision_class", "unclassified")
            if ew is None:
                ew = csv.writer(ev_f)
                ew.writerow(ev.columns)
            ew.writerows(ev.itertuples(index=False, name=None))
            counts["events"] += len(ev)
            if not len(rows):
                counts["no_rows"] += 1
                continue
            rows["decision_class"] = m.get("decision_class", "unclassified")
            rows["question_stem"] = m.get("question_stem", "")
            if rw is None:
                rw = csv.writer(rows_f)
                rw.writerow(rows.columns)
            rw.writerows(rows.itertuples(index=False, name=None))
            counts["markets"] += 1
            counts["rows"] += len(rows)
            if k % 200 == 0:
                log(f"{k}/{len(sample)} markets, rows {counts['rows']}, events {counts['events']}")
    finally:
        rows_f.close()
        ev_f.close()
    manifest = {"version": VERSION, "evidence_role": EVIDENCE_ROLE, "label_spec": LABEL_SPEC,
                "label_spec_sha256": label_spec_sha256(), "feature_spec": FEATURE_SPEC,
                "source_run": str(run_dir), "counts": counts, "built_utc": hb.utc_iso(),
                "first_seen": {"g0": None if math.isnan(fsi.g0) else fsi.g0,
                               "n_wallets": int(len(fsi.keys))},
                "excluded_condition_ids": len(excl), "meta_markets": len(meta)}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


# --- 4. post-assembly context: siblings, ladders, strata -------------------------------------

_DATE_WORDS = ("january", "february", "march", "april", "may", "june", "july", "august",
               "september", "october", "november", "december", "jan", "feb", "mar", "apr", "jun",
               "jul", "aug", "sep", "sept", "oct", "nov", "dec", "monday", "tuesday", "wednesday",
               "thursday", "friday", "saturday", "sunday")


def question_stem(q: str) -> str:
    """Question with dates, numbers and ordinal suffixes removed (deadline-ladder grouping)."""
    import re

    s = re.sub(r"[^a-z ]+", " ", (q or "").lower())
    toks = [w for w in s.split() if w not in _DATE_WORDS and not w.isdigit()
            and w not in ("st", "nd", "rd", "th", "by", "before", "on", "in", "of", "the")]
    return " ".join(toks)


def add_group_moves(rows: pd.DataFrame) -> pd.DataFrame:
    """Sibling (same event) and ladder (same question stem) moves at the same grid ``t``:
    max |mid - mid(t - 2h)| over the *other* markets of the group, and the group size."""
    chg = rows["ml_own_dmid_prev"].abs()
    for name, key in (("sib", "event_id"), ("ladder", "question_stem")):
        g = rows[key].astype(str)
        ok = g.str.len() > 0
        grp = pd.DataFrame({"g": g, "t": rows["t"], "c": chg, "m": rows["market_id"]})
        grp.loc[~ok, "g"] = np.nan
        size = grp.groupby(["g", "t"])["m"].transform("nunique")
        # max over others: take the top-2 per group; if this row holds the max use the second
        srt = grp.sort_values(["g", "t", "c"], ascending=[True, True, False])
        srt["rank"] = srt.groupby(["g", "t"]).cumcount()
        top = srt[srt["rank"] == 0].set_index(["g", "t"])["c"]
        second = srt[srt["rank"] == 1].set_index(["g", "t"])["c"]
        idx = pd.MultiIndex.from_arrays([grp["g"], grp["t"]])
        t1 = top.reindex(idx).to_numpy(float)
        t2 = second.reindex(idx).to_numpy(float)
        own = chg.to_numpy(float)
        other = np.where(np.isfinite(own) & (own >= t1), t2, t1)
        rows[f"{name}_n"] = np.where(ok, size.fillna(1).to_numpy(float) - 1.0, 0.0)
        rows[f"{name}_max_abs_chg_2h"] = np.where(ok & (rows[f"{name}_n"] > 0), other, np.nan)
    return rows


PRICE_BANDS = (0.05, 0.20, 0.45)


def strata(rows: pd.DataFrame, liq_cuts: tuple[float, float] | None = None
           ) -> tuple[pd.Series, tuple[float, float]]:
    """Matching strata: fee_category | price band | liquidity tercile | 6h hour bucket."""
    liq = rows["sm_log_notional_24h"].to_numpy(float)
    if liq_cuts is None:
        fin = liq[np.isfinite(liq)]
        liq_cuts = (float(np.percentile(fin, 100 / 3)), float(np.percentile(fin, 200 / 3)))
    lband = np.where(np.isfinite(liq), np.digitize(liq, liq_cuts), -1)
    pband = np.digitize(np.abs(rows["mid"].to_numpy(float) - 0.5), PRICE_BANDS)
    hb_ = ((rows["t"].to_numpy(float) % DAY_S) // 21600).astype(int)
    s = pd.Series([f"{c}|{p}|{b}|{h}" for c, p, b, h in zip(rows["fee_category"].astype(str),
                                                            pband, lband, hb_, strict=True)],
                  index=rows.index)
    return s, liq_cuts


def _hash_rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


def match_negatives(rows: pd.DataFrame, *, k: int | None = None, seed: str | None = None,
                    liq_cuts: tuple[float, float] | None = None) -> pd.DataFrame:
    """Case-control sample: every positive (``y_dep_2h``) plus ``k`` clean negatives from the
    same stratum chosen by seeded hash order (no replacement within a stratum)."""
    nb = LABEL_SPEC["negatives"]
    k = nb["k_per_positive"] if k is None else k
    seed = nb["seed"] if seed is None else seed
    elig = rows["traded_before_t"] == 1.0
    st, cuts = strata(rows, liq_cuts)
    rows = rows.assign(stratum=st)
    pos = rows[elig & rows["y_dep_2h"]]
    pool = rows[elig & ~rows["near_any_dep"] & ~rows["y_dep_2h"]]
    key = pool["market_id"].astype(str) + "|" + pool["t"].astype(int).astype(str)
    pool = pool.assign(_rk=[_hash_rank(seed, x) for x in key]).sort_values("_rk")
    by = {s: g for s, g in pool.groupby("stratum")}
    used: set = set()
    picks = []
    short = 0
    for s, g in pos.groupby("stratum"):
        cand = by.get(s)
        need = k * len(g)
        if cand is None:
            short += need
            continue
        c = cand[~cand.index.isin(used)].head(need)
        used.update(c.index)
        picks.append(c)
        short += max(0, need - len(c))
    neg = pd.concat(picks) if picks else pool.iloc[:0]
    out = pd.concat([pos.assign(y=1), neg.assign(y=0)]).drop(columns=["_rk"], errors="ignore")
    out.attrs.update({"k": k, "seed": seed, "liq_cuts": cuts, "negatives_short": int(short),
                      "n_pos": int(len(pos)), "n_neg": int(len(neg))})
    return out


def log_label_spec(path: Path = provenance.TRIALS_PATH, **extra) -> dict:
    rec = {"kind": TRIAL_KIND_LABELS, "label": "EXPLORATORY surprise-move label specification",
           "evidence_role": EVIDENCE_ROLE, "label_spec_version": LABEL_SPEC["version"],
           "label_spec_sha256": label_spec_sha256(),
           "feature_spec_version": FEATURE_SPEC["version"],
           "status": "fixed_before_features",
           "provenance": provenance.run_provenance([Path(__file__)]), **extra}
    return provenance.append_trial(rec, path)


__all__ = ["LABEL_SPEC", "FEATURE_SPEC", "VERSION", "detect_events", "events_all_variants",
           "surprise_features", "feature_names", "market_rows", "build_dataset",
           "add_group_moves", "match_negatives", "strata", "question_stem", "label_spec_sha256",
           "log_label_spec", "price_context"]


# --- 5. live price context (same formulas as history_backfill.origin_frame) ------------------


def price_context(ts: np.ndarray, vals: np.ndarray, t: float, *, mid: float | None = None,
                  created_ts: float = math.nan, end_ts: float = math.nan) -> dict[str, float]:
    """Context features at one origin ``t`` from a causal price series (points usable only after
    ``stamp + POINT_LAG_S``), mirroring ``history_backfill.origin_frame``. ``mid`` overrides the
    as-of series price (the live monitor passes the Gamma mid; recorded as a deviation)."""
    ts = np.asarray(ts, float)
    vals = np.asarray(vals, float)
    tt = np.array([float(t)])
    out: dict[str, float] = {}
    if len(ts) < 2:
        return out
    m = hb._asof(ts, vals, tt, MAX_QUOTE_AGE_S)[0][0] if mid is None else float(mid)
    out["mid"] = m
    if np.isfinite(m) and 0 < m < 1:
        out["logit_mid"] = float(np.log(m / (1 - m)))
        out["abs_mid_dev"] = abs(m - 0.5)
        out["dist_01"] = min(m, 1 - m)
    lag = {k: hb._asof(ts, vals, tt - s, MAX_QUOTE_AGE_S)[0][0]
           for k, s in (("1h", 3600), ("1d", 86400), ("1w", 7 * 86400))}
    for k, v in lag.items():
        out[f"chg_{k}"] = m - v
    steps = np.array([m] + [hb._asof(ts, vals, tt - GRID_S * k, MAX_QUOTE_AGE_S)[0][0]
                            for k in range(1, hb.HIST_STEPS + 1)])
    d = np.diff(steps)
    okd = np.isfinite(d)
    out["own_vol"] = float(np.sqrt((d[okd] ** 2).sum() / okd.sum())) if okd.sum() >= 2 else np.nan
    cs = np.concatenate([[0.0], np.cumsum(np.diff(vals) ** 2)])
    u = int(np.searchsorted(ts + POINT_LAG_S, t, side="left") - 1)
    for hrs, tag in hb.RV_WINDOWS:
        sidx = int(np.searchsorted(ts, t - POINT_LAG_S - hrs * 3600, side="left"))
        nd = u - sidx
        out[f"rv_{tag}"] = (float(np.sqrt((cs[max(u, 0)] - cs[min(sidx, u)]) / nd))
                            if nd >= 3 else np.nan)
    out["market_age_h"] = (max(0.0, (t - created_ts) / 3600.0) if math.isfinite(created_ts)
                           else np.nan)
    out["log_hours_to_end"] = (float(np.log1p(max(0.0, (end_ts - t) / 3600.0)))
                               if math.isfinite(end_ts) else np.nan)
    hour = (t % DAY_S) / 3600.0
    out["hour_sin"] = float(np.sin(2 * np.pi * hour / 24.0))
    out["hour_cos"] = float(np.cos(2 * np.pi * hour / 24.0))
    out["dow"] = float(((t // DAY_S) + 3) % 7)
    return out
