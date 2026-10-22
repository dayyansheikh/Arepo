# ruff: noqa: E501
"""Auxiliary feature families: new signal families added without touching the frozen v1 feature store.

The v1 store (``features/<capture>.parquet``, ``se-features-v1``) is write-once and pinned by every v1 spec, so a new
family cannot be added to it. An auxiliary family instead writes its own write-once table per capture,
``aux/<family>/<capture>.parquet``: one row per eligible market, in the same row order as the capture's features file
(``market_id`` is stored and checked on read), its own version string (``AUX_FAMILIES[family]["version"]``) and the
sha256 of the features file it was aligned to. Specs that use an aux family pin its version in ``aux_versions``;
specs without aux families are unchanged (same sha256).

Causality: an aux builder may read only the origin capture's own snapshot rows (or streams received before the
capture start), exactly like the base families. A capture whose rows were archived before its aux table was built
has no aux table (missing stays missing): its rows read as NaN and ``src_<family>`` is False, so a spec can
restrict training to captures that have the family (``train.require_sources``).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import store as S
from .features import (
    ALL_FEATURES,
    FAMILY_COLUMNS,
    KEY_COLUMNS,
    _epoch_col,
    _truthy,
    book_columns,
    mid_series,
    read_rows,
    read_sweep_book,
)


class SlotMids:
    """Bounded cache of quotes-file mids per slot for builders that walk captures newest first: it evicts the newest
    slots (no longer needed), so a backfill reads each quotes file about once. Stored as sorted numpy arrays (no
    pandas index hash tables, so ~1.6 MB per slot)."""

    def __init__(self, paths: S.Paths, index: dict[int, dict], keep: int) -> None:
        self.paths, self.index, self.keep, self.d = paths, index, keep, {}

    def get(self, slot: int, ids: np.ndarray) -> np.ndarray:
        """float64 mids of ``ids`` at ``slot`` (NaN where the market is not open and two-sided or the file is absent)."""
        if slot not in self.d:
            m = self.index.get(slot)
            p = self.paths.quotes(m["capture_id"]) if m is not None else None
            if p is not None and p.exists():
                ser = mid_series(S.read_parquet(p, ["market_id", "bid", "ask", "st"]))
                u, first = np.unique(ser.index.to_numpy(np.int64), return_index=True)  # first row per market
                self.d[slot] = (u, ser.to_numpy(np.float64)[first])
            else:
                self.d[slot] = None
        e = self.d[slot]
        while len(self.d) > self.keep:
            self.d.pop(max(self.d))
        if e is None or len(e[0]) == 0:
            return np.full(len(ids), np.nan)
        u, v = e
        pos = np.minimum(np.searchsorted(u, ids), len(u) - 1)
        return np.where(u[pos] == ids, v[pos], np.nan)

# ---------------------------------------------------------------------------------------------- event family
# Event-level context from the same capture's complete binary listing (every market of the event, including
# siblings that are not eligible themselves). Development history: E005 (neg-risk band deviation, closed 2026-10-11,
# not supported) and SB2-J5 (sibling reversal, development only). Embargo token `event` until 2026-11-22 (LT5 F,
# draft, CH184; added 2026-10-21 on the experiments track's request).
EVENT_MAX_SPREAD_S = 5.0  # siblings must be received within 5 s of each other (median 0 s, p90 0.2 s, p99 201 s on
# 2026-10-21): otherwise a sibling quote received minutes after a market's own row could carry part of that market's
# later move into its features, so the whole event is left missing (counted by the NaN rate, never filled)
EVENT_COLUMNS = ["ev_log_n", "ev_sum_mid_m1", "ev_quoted_share", "ev_norm_gap", "ev_rank", "ev_max_other",
                 "ev_sib_chg1h", "ev_sib_chg1d", "ev_sib_d2h"]
SIB_MIN_SHARE = 0.5  # a sibling mean needs a value for at least half of the siblings (own excluded)


def event_features(rows: pd.DataFrame, f: pd.DataFrame, prev_mid: pd.Series | None = None) -> pd.DataFrame:
    """Per eligible market (rows of ``f``): event size, neg-risk overround and sibling moves (NaN = not defined).

    ``prev_mid``: market_id -> two-sided mid of the previous slot's capture (the engine's own earlier quotes file).
    Sibling moves are means over the siblings that have a value (at least ``SIB_MIN_SHARE`` of them); the overround
    is NaN if nothing is quoted. A missing value is never read as zero."""
    b = rows[rows["binary"] == 1]
    b = b[(~_truthy(b["closed"])) & _truthy(b["active"])]
    b = b[b["event_id"].notna()].drop_duplicates("market_id")
    bid, ask = b["best_bid"].to_numpy(float), b["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask)
    g = pd.DataFrame({"event_id": b["event_id"].astype(str).to_numpy(), "market_id": b["market_id"].to_numpy(np.int64),
                      "mid": np.where(two, (bid + ask) / 2.0, np.nan), "two": two.astype(float),
                      "t": _epoch_col(b["received_utc"]),
                      "c1h": pd.to_numeric(b["chg_1h"], errors="coerce").to_numpy(float),
                      "c1d": pd.to_numeric(b["chg_1d"], errors="coerce").to_numpy(float),
                      "nr": (pd.to_numeric(b["neg_risk"], errors="coerce").fillna(0).to_numpy(float) > 0)})
    pm = prev_mid.reindex(g["market_id"].to_numpy()).to_numpy(float) if prev_mid is not None else np.full(len(g), np.nan)
    g["d2h"] = g["mid"].to_numpy(float) - pm
    n = len(f)
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in EVENT_COLUMNS})
    if n == 0 or g.empty:
        return out
    gb = g.groupby("event_id", sort=False)
    ev = pd.DataFrame({"n": gb["market_id"].size(), "sum_mid": gb["mid"].sum(min_count=1), "n_two": gb["two"].sum(),
                       "c1h": gb["c1h"].sum(min_count=1), "c1d": gb["c1d"].sum(min_count=1), "d2h": gb["d2h"].sum(min_count=1),
                       "n_c1h": gb["c1h"].count(), "n_c1d": gb["c1d"].count(), "n_d2h": gb["d2h"].count(),
                       "nr": gb["nr"].max(),
                       "t0": gb["t"].min(), "t1": gb["t"].max()})
    # quoted-mid rank (0 = lowest, 1 = highest) and the largest quoted sibling mid, own market excluded
    q = g[np.isfinite(g["mid"].to_numpy())].copy()
    q["nq"] = q.groupby("event_id", sort=False)["mid"].transform("size")
    q["rk"] = (q.groupby("event_id", sort=False)["mid"].rank(method="min") - 1) / (q["nq"] - 1).where(q["nq"] > 1)
    srt = q.sort_values(["event_id", "mid"], ascending=[True, False])
    top = srt.groupby("event_id", sort=False).head(2).copy()
    top["pos"] = top.groupby("event_id", sort=False).cumcount()
    first = top[top["pos"] == 0].set_index("event_id")
    second = top[top["pos"] == 1].set_index("event_id")["mid"]
    eid = f["event_id"].astype(str).to_numpy()
    mids_own = f["market_id"].to_numpy(np.int64)
    own = f["ms_mid"].to_numpy(float)
    e = ev.reindex(eid)
    me = g.set_index("market_id").reindex(mids_own)
    mq = q.set_index("market_id").reindex(mids_own)
    cnt = e["n"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        has = np.isfinite(cnt) & (cnt >= 1) & ((e["t1"].to_numpy(float) - e["t0"].to_numpy(float)) <= EVENT_MAX_SPREAD_S)
    multi = has & (cnt >= 2)
    out["ev_log_n"] = np.where(has, np.log(np.where(has, cnt, 1.0)), np.nan)
    for col, src in (("ev_sib_chg1h", "c1h"), ("ev_sib_chg1d", "c1d"), ("ev_sib_d2h", "d2h")):
        ov = me[src].to_numpy(float)
        own_has = np.isfinite(ov)
        n_sib = e[f"n_{src}"].to_numpy(float) - own_has  # siblings with a value, own excluded
        tot = np.nan_to_num(e[src].to_numpy(float)) - np.where(own_has, ov, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            enough = multi & (n_sib >= 1) & (n_sib >= SIB_MIN_SHARE * (cnt - 1))
            out[col] = np.where(enough, tot / np.where(n_sib > 0, n_sib, 1.0), np.nan)
    top_id = first["market_id"].reindex(eid).to_numpy(float)
    top_mid = first["mid"].reindex(eid).to_numpy(float)
    sec_mid = second.reindex(eid).to_numpy(float)
    other = np.where(top_id == mids_own, sec_mid, top_mid)
    quoted_multi = multi & np.isfinite(mq["rk"].to_numpy(float))
    out["ev_rank"] = np.where(quoted_multi, mq["rk"].to_numpy(float), np.nan)
    out["ev_max_other"] = np.where(multi, other, np.nan)
    # neg-risk overround: sum of quoted mids - 1 (NaN if nothing is quoted), its completeness and the own gap
    nr = multi & (e["nr"].to_numpy(float) > 0)
    sm = e["sum_mid"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["ev_sum_mid_m1"] = np.where(nr, sm - 1.0, np.nan)
        out["ev_quoted_share"] = np.where(nr, e["n_two"].to_numpy(float) / cnt, np.nan)
        out["ev_norm_gap"] = np.where(nr & (sm > 0), own / sm - own, np.nan)
    return out.astype(np.float32)


# ---------------------------------------------------------------------------------------------- rewards family
# Liquidity-reward programme of each market from the same capture's Gamma sidecar (`rows_ext.csv.gz`): CLOB reward
# settings and active daily rates. Embargo token `rewards` until 2026-11-18 (E020 draft uses the reward flag, LT4).
REWARDS_COLUMNS = ["rw_has", "rw_log_rate", "rw_max_spread", "rw_log_min_size", "rw_in_band", "rw_new"]


def _reward_rate(js, day: str) -> tuple[float, float]:
    """(sum of active daily rates, 1 if a programme started within 2 days of ``day``) from a clob_rewards JSON."""
    if not isinstance(js, str) or not js.startswith("["):
        return math.nan, math.nan
    try:
        items = json.loads(js)
    except ValueError:
        return math.nan, math.nan
    rate, new = 0.0, 0.0
    d0 = pd.Timestamp(day)
    for it in items if isinstance(items, list) else []:
        try:
            st, en = str(it.get("startDate") or "0000-01-01"), str(it.get("endDate") or "9999-12-31")
            if st <= day <= en:
                rate += float(it.get("rewardsDailyRate") or 0.0)
                if (d0 - pd.Timestamp(st)).days <= 2:
                    new = 1.0
        except (TypeError, ValueError, AttributeError):
            continue
    return rate, new


def rewards_features(ext: pd.DataFrame | None, f: pd.DataFrame, cap_start: float) -> pd.DataFrame:
    """Per eligible market: has an active reward programme, log daily rate, max spread (cents), log min size, current
    spread inside the reward band, programme started in the last 2 days. NaN when the sidecar lacks the market."""
    n = len(f)
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in REWARDS_COLUMNS})
    if ext is None or n == 0:
        return out
    e = ext.reindex(f["market_id"].to_numpy(np.int64))
    day = pd.Timestamp(cap_start, unit="s", tz="UTC").strftime("%Y-%m-%d")
    present = e["rewards_max_spread"].notna().to_numpy() if "rewards_max_spread" in e else np.zeros(n, bool)
    rr = [_reward_rate(v, day) if ok else (math.nan, math.nan)
          for v, ok in zip(e.get("clob_rewards", pd.Series([None] * n)).to_numpy(), present, strict=True)]
    rate = np.array([r[0] for r in rr], float)
    rate = np.where(present & np.isnan(rate), 0.0, rate)  # sidecar row present, no programme listed: rate 0
    new = np.array([r[1] for r in rr], float)
    new = np.where(present & np.isnan(new), 0.0, new)
    ms = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
    mn = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
    spread_c = f["ms_spread"].to_numpy(float) * 100.0 if "ms_spread" in f else np.full(n, np.nan)
    with np.errstate(invalid="ignore"):
        out["rw_has"] = np.where(present, (rate > 0).astype(float), np.nan)
        out["rw_log_rate"] = np.where(present, np.log1p(np.clip(rate, 0, None)), np.nan)
        out["rw_max_spread"] = np.where(present, ms, np.nan)
        out["rw_log_min_size"] = np.where(present, np.log1p(np.clip(mn, 0, None)), np.nan)
        out["rw_in_band"] = np.where(present & (rate > 0) & np.isfinite(spread_c) & np.isfinite(ms),
                                     (spread_c <= ms).astype(float), np.where(present, 0.0, np.nan))
        out["rw_new"] = np.where(present, new, np.nan)
    return out.astype(np.float32)


REWARD_EXT_COLS = ["market_id", "rewards_min_size", "rewards_max_spread", "clob_rewards"]


# ---------------------------------------------------------------------------------------------- movetype family
# How the last 2 h move happened (CANDIDATES.md C07, replicated in HB1-R; C12 move over spread): traded or quote-only,
# and for quote-only moves whether both quotes moved together (parallel re-centering), one quote moved (bounce) or the
# spread changed. Classes follow LIVE_TESTS_3.md section 2 (E015) on the engine's own float32 files, so the tolerances
# are wider than E015's (the engine's own definition, not E015's frozen one). Inputs: the quotes and features files of
# capture k and of the previous slot k - 1 only (engine-own files; no snapshot rows, so archived captures still get
# a table). Embargo token `movetype` (+ `book`) until 2026-11-22: shadows E015 (LT3, analysis 2026-11-15T12Z).
MOVETYPE_COLUMNS = ["mt_db", "mt_da", "mt_dltp", "mt_dlogvol", "mt_traded", "mt_never", "mt_ambig", "mt_q_still",
                    "mt_q_parallel", "mt_q_onesided", "mt_q_spread", "mt_x_spread", "mt_x_traded", "mt_x_parallel"]
MT_LTP_TOL = 1e-5  # ltp = (ltp - mid) + mid in float32: error ~1e-7, ticks >= 1e-4
MT_VOL_ABS, MT_VOL_REL = 0.01, 4e-6  # V+ / V-: |d volume24hr| beyond $0.01 and ~4 float32 ulps of log1p(volume)
MT_STILL, MT_PAR, MT_PAR_GAP = 0.0005, 0.005, 0.005  # E015 thresholds (quote unchanged, parallel size and gap)
MT_EPS = 1e-6  # float32 slack on the thresholds above


def movetype_features(f: pd.DataFrame, q: pd.DataFrame, prev_q: pd.DataFrame | None, prev_f: pd.DataFrame | None) -> pd.DataFrame:
    """Per eligible market (rows of ``f``; ms_mid, ms_spread, ms_ltp_minus_mid, ms_log_vol24): class of the move from
    k - 1 to k. ``q`` / ``prev_q``: quotes frames of k and k - 1 (market_id, bid, ask, st). ``prev_f``: features of
    k - 1 (only markets eligible there). Everything is NaN when the market is not two-sided at k - 1 or not in
    ``prev_f``; class indicators are 0/1 where the class is decidable and NaN where it is not."""
    n = len(f)
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in MOVETYPE_COLUMNS})
    if n == 0 or prev_q is None or prev_f is None:
        return out
    ids = f["market_id"].to_numpy(np.int64)
    cur = q[q["st"] == 0].drop_duplicates("market_id").set_index("market_id").reindex(ids)
    pq_ = prev_q[prev_q["st"] == 0].drop_duplicates("market_id").set_index("market_id").reindex(ids)
    pf = prev_f.drop_duplicates("market_id").set_index("market_id").reindex(ids)
    b1, a1 = cur["bid"].to_numpy(np.float64), cur["ask"].to_numpy(np.float64)
    b0, a0 = pq_["bid"].to_numpy(np.float64), pq_["ask"].to_numpy(np.float64)
    mid1, mid0 = f["ms_mid"].to_numpy(np.float64), pf["ms_mid"].to_numpy(np.float64)
    ltp1 = f["ms_ltp_minus_mid"].to_numpy(np.float64) + mid1
    ltp0 = pf["ms_ltp_minus_mid"].to_numpy(np.float64) + mid0
    v1, v0 = np.expm1(f["ms_log_vol24"].to_numpy(np.float64)), np.expm1(pf["ms_log_vol24"].to_numpy(np.float64))
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(b0) & np.isfinite(a0) & np.isfinite(b1) & np.isfinite(a1) & np.isfinite(mid0)
        db, da = b1 - b0, a1 - a0
        x = (b1 + a1) / 2.0 - (b0 + a0) / 2.0
        h0, h1 = np.isfinite(ltp0), np.isfinite(ltp1)
        dltp = ltp1 - ltp0
        lchg = (h0 & h1 & (np.abs(dltp) > MT_LTP_TOL)) | (~h0 & h1)
        dv = v1 - v0
        tol = np.maximum(MT_VOL_ABS, MT_VOL_REL * np.fmax(np.abs(v1), np.abs(v0)))
        vplus, vminus, vknown = dv > tol, dv < -tol, np.isfinite(dv)
        never = ok & ~h0 & ~h1
        traded = ok & ~never & (lchg | vplus)
        ambig = ok & ~never & ~traded & ((h0 & ~h1) | vminus)
        qonly = ok & ~never & ~traded & ~ambig & vknown
        decided = never | traded | ambig | qonly
        adb, ada = np.abs(db), np.abs(da)
        still = qonly & (adb <= MT_STILL + MT_EPS) & (ada <= MT_STILL + MT_EPS)
        par = (qonly & ~still & (np.sign(db) == np.sign(da)) & (np.sign(db) == np.sign(x)) & (adb >= MT_PAR - MT_EPS)
               & (ada >= MT_PAR - MT_EPS) & (np.abs(db - da) <= MT_PAR_GAP + MT_EPS))
        one = qonly & ~still & ~par & ((adb <= MT_STILL + MT_EPS) | (ada <= MT_STILL + MT_EPS))
        sprd = qonly & ~still & ~par & ~one & (np.sign(db) != np.sign(da))
        sp = f["ms_spread"].to_numpy(np.float64)
        out["mt_db"] = np.where(ok, db, np.nan)
        out["mt_da"] = np.where(ok, da, np.nan)
        out["mt_dltp"] = np.where(ok & h0 & h1, dltp, np.nan)
        out["mt_dlogvol"] = np.where(ok, f["ms_log_vol24"].to_numpy(np.float64) - pf["ms_log_vol24"].to_numpy(np.float64), np.nan)
        for col, m in (("mt_traded", traded), ("mt_never", never), ("mt_ambig", ambig), ("mt_q_still", still),
                       ("mt_q_parallel", par), ("mt_q_onesided", one), ("mt_q_spread", sprd)):
            out[col] = np.where(decided, m.astype(float), np.nan)
        out["mt_x_spread"] = np.where(ok & (sp > 0), x / np.where(sp > 0, sp, 1.0), np.nan)
        out["mt_x_traded"] = np.where(decided, x * traded, np.nan)
        out["mt_x_parallel"] = np.where(decided, x * par, np.nan)
    return out.astype(np.float32)


MT_FEATURE_COLS = ["market_id", "ms_mid", "ms_spread", "ms_ltp_minus_mid", "ms_log_vol24"]
MT_QUOTE_COLS = ["market_id", "bid", "ask", "st"]


def _movetype_builder(ctx: dict) -> pd.DataFrame:
    paths, meta, prev = ctx["paths"], ctx["meta"], ctx["prev"]
    f = S.read_parquet(paths.features(meta["capture_id"]), MT_FEATURE_COLS)
    q = S.read_parquet(paths.quotes(meta["capture_id"]), MT_QUOTE_COLS)
    prev_q = prev_f = None
    if prev is not None and paths.quotes(prev["capture_id"]).exists() and paths.features(prev["capture_id"]).exists():
        prev_q = S.read_parquet(paths.quotes(prev["capture_id"]), MT_QUOTE_COLS)
        prev_f = S.read_parquet(paths.features(prev["capture_id"]), MT_FEATURE_COLS)
    return movetype_features(f, q, prev_q, prev_f)


# ---------------------------------------------------------------------------------------------- surprise family
# Price-path context for sharp moves (CANDIDATES.md C06; SURPRISE_MOVE_DETECTOR.md section 3 primitives, not the frozen
# detector): own realised volatility over 6 h / 3 d / 7 d and its ratios to the 24 h one, the largest 2 h move of the
# last 24 h, UTC weekday and hour of the capture. Inputs: the engine's own quotes files of slots k - 84 .. k (earlier
# captures plus the origin's own mid); no snapshot rows. Embargo token `surprise` until 2026-11-19 (E011; config.EMBARGO).
SURPRISE_COLUMNS = ["sp_rv6h", "sp_rv3d", "sp_rv7d", "sp_r6h_24h", "sp_r24h_7d", "sp_r6h_7d", "sp_maxabs24", "sp_dow",
                    "sp_hour"]
SP_WINDOWS = {"6h": (3, 2), "24h": (12, 3), "3d": (36, 12), "7d": (84, 24)}  # name: (2 h steps, min finite diffs)
SP_LOOKBACK = max(w for w, _ in SP_WINDOWS.values())


def _rv(d: np.ndarray, steps: int, min_n: int) -> np.ndarray:
    """Root mean square of the last ``steps`` finite 2 h mid changes (same definition as ms_rv24); NaN below min_n."""
    w = d[:, -steps:]
    ok = np.isfinite(w)
    n = ok.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = np.sqrt((np.where(ok, w, 0.0) ** 2).sum(axis=1) / n)
    return np.where(n >= min_n, rv, np.nan)


def surprise_features(H: np.ndarray, cap_start: float) -> pd.DataFrame:
    """``H``: per eligible market, mids of slots k - SP_LOOKBACK .. k (NaN where not quoted), last column the origin."""
    n = H.shape[0]
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in SURPRISE_COLUMNS})
    ts = pd.Timestamp(cap_start, unit="s", tz="UTC")
    out["sp_dow"] = float(ts.dayofweek)
    out["sp_hour"] = float(ts.hour)
    if n == 0:
        return out.astype(np.float32)
    d = np.diff(H, axis=1)
    rv = {k: _rv(d, s, m) for k, (s, m) in SP_WINDOWS.items()}
    with np.errstate(invalid="ignore", divide="ignore"):
        out["sp_rv6h"], out["sp_rv3d"], out["sp_rv7d"] = rv["6h"], rv["3d"], rv["7d"]
        out["sp_r6h_24h"] = np.where(rv["24h"] > 0, rv["6h"] / rv["24h"], np.nan)
        out["sp_r24h_7d"] = np.where(rv["7d"] > 0, rv["24h"] / rv["7d"], np.nan)
        out["sp_r6h_7d"] = np.where(rv["7d"] > 0, rv["6h"] / rv["7d"], np.nan)
        last = d[:, -12:]
        out["sp_maxabs24"] = np.where(np.isfinite(last).sum(axis=1) >= 3, np.nanmax(np.where(np.isfinite(last), np.abs(last), -1.0), axis=1), np.nan)
    return out.astype(np.float32)


def _surprise_builder(ctx: dict) -> pd.DataFrame:
    paths, meta, index = ctx["paths"], ctx["meta"], ctx["index"]
    mids = ctx.get("mids") or SlotMids(paths, index, keep=SP_LOOKBACK + 4)
    f = ctx["f"]
    ids = f["market_id"].to_numpy(np.int64)
    slot = meta["slot"]
    cols = []
    for j in range(slot - SP_LOOKBACK, slot + 1):  # the origin's own quotes file last (same float32 grain as the rest)
        cols.append(mids.get(j, ids))
    return surprise_features(np.column_stack(cols), ctx["cap_start"])


# ---------------------------------------------------------------------------------------------- hwm family
# Own high-water marks (CANDIDATES CH181, development only; LT5 H was dropped at census, so no test is shadowed): the
# distance of the origin mid to the highest and lowest mid of the earlier captures in the last 3 d and 7 d, the hours
# since the 7 d extremes, the position in the 7 d range and the share of the 7 d slots quoted. Inputs: the engine's own
# quotes files of slots k - 84 .. k (earlier captures plus the origin's own mid, as `surprise`); no snapshot rows.
# Windows of 3 d and longer only, so the family carries no 6 h step path (LT7 `capath`) and no time-of-day schedule
# (LT8 `sched`). No embargo token.
HWM_COLUMNS = ["hw_dhi3d", "hw_dlo3d", "hw_dhi7d", "hw_dlo7d", "hw_agehi7d", "hw_agelo7d", "hw_pos7d", "hw_cov7d"]
HW_WINDOWS = {"3d": (36, 12), "7d": (84, 24)}  # name: (earlier 2 h slots, min quoted slots)
HW_LOOKBACK = max(w for w, _ in HW_WINDOWS.values())
HW_MIN_RANGE = 0.01  # the 7 d position needs a range of at least one cent


def hwm_features(H: np.ndarray) -> pd.DataFrame:
    """``H``: per eligible market, mids of slots k - HW_LOOKBACK .. k (NaN where not quoted), last column the origin.
    The extremes are taken over the earlier slots only, so a new high gives ``hw_dhi* < 0``."""
    n = H.shape[0]
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in HWM_COLUMNS})
    if n == 0:
        return out
    m = H[:, -1]
    for name, (w, min_n) in HW_WINDOWS.items():
        P = H[:, -1 - w:-1]
        ok = np.isfinite(P)
        cnt = ok.sum(axis=1)
        good = (cnt >= min_n) & np.isfinite(m)
        hi = np.where(ok, P, -np.inf).max(axis=1)
        lo = np.where(ok, P, np.inf).min(axis=1)
        out[f"hw_dhi{name}"] = np.where(good, hi - m, np.nan)
        out[f"hw_dlo{name}"] = np.where(good, m - lo, np.nan)
        if name == "7d":
            R = P[:, ::-1]  # newest earlier slot first, so argmax / argmin pick the most recent extreme on ties
            okr = ok[:, ::-1]
            out["hw_agehi7d"] = np.where(good, 2.0 * (np.argmax(np.where(okr, R, -np.inf), axis=1) + 1), np.nan)
            out["hw_agelo7d"] = np.where(good, 2.0 * (np.argmin(np.where(okr, R, np.inf), axis=1) + 1), np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                out["hw_pos7d"] = np.where(good & (hi - lo >= HW_MIN_RANGE), (m - lo) / (hi - lo), np.nan)
            out["hw_cov7d"] = np.where(np.isfinite(m), cnt / w, np.nan)
    return out.astype(np.float32)


def _hwm_builder(ctx: dict) -> pd.DataFrame:
    paths, meta, index = ctx["paths"], ctx["meta"], ctx["index"]
    mids = ctx.get("mids") or SlotMids(paths, index, keep=HW_LOOKBACK + 4)
    ids = ctx["f"]["market_id"].to_numpy(np.int64)
    slot = meta["slot"]
    return hwm_features(np.column_stack([mids.get(j, ids) for j in range(slot - HW_LOOKBACK, slot + 1)]))


def read_reward_ext(cap_dir) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    import pyarrow as pa
    import pyarrow.csv as pacsv

    types = {"market_id": pa.int64(), "rewards_min_size": pa.float64(), "rewards_max_spread": pa.float64(),
             "clob_rewards": pa.string()}
    try:
        t = pacsv.read_csv(p, convert_options=pacsv.ConvertOptions(include_columns=REWARD_EXT_COLS, column_types=types))
    except (pa.ArrowInvalid, KeyError):
        return None  # an older sidecar without the reward columns: the family is missing for this capture
    return t.to_pandas().drop_duplicates("market_id").set_index("market_id")


# ---------------------------------------------------------------------------------------------- participation family
# Event-level participation and attention breadth (CANDIDATES.md row 14): the event's lifetime volume and liquidity, the
# 2 h change of the event volume, the market's share of the event liquidity, Gamma's `competitive` score, the event's
# age and the market's lifetime volume. Not CB17-C's event open interest, not comment bursts (they died in the probes,
# CREATIVE_HYPOTHESES_2026-10-22.md section 3: 9 of 22,111 events changed comment count in 2 h) and not E017 (dropped
# uncounted). Inputs: the origin capture's own sidecar `rows_ext.csv.gz` and snapshot rows (the same Gamma response as
# the origin row, received at the row's receipt time, before the prediction) plus, for the 2 h change only, the previous
# slot's sidecar; nothing later is ever read, and an absent previous sidecar leaves the change columns NaN. Embargo
# token `participation` until 2026-11-25 (science review 2026-10-21): CB17-C (CH150, drafted) uses the 2 h event-volume
# change as its eligibility rule and log event liquidity as a control; REP_8 ends no earlier than 2026-11-23T08:00Z.
# Open interest (CB17-C's tested ratio) and comment counts are excluded; rewards_* and clob_rewards belong to `rewards`.
PARTICIPATION_COLUMNS = ["pp_log_ev_vol", "pp_d_ev_vol", "pp_ev_vol_fell", "pp_log_ev_liq", "pp_liq_share",
                         "pp_competitive", "pp_log_ev_age_h", "pp_log_vol_num"]
PA_EXT_COLS = ["market_id", "event_volume", "event_liquidity", "competitive", "event_created_at", "volume_num"]
PA_FELL_EPS = 1e-6


def read_participation_ext(cap_dir) -> pd.DataFrame | None:
    """The sidecar columns of PA_EXT_COLS that exist (an older sidecar lacks some: that column is NaN), by market_id."""
    if cap_dir is None:
        return None
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    import gzip

    import pyarrow as pa
    import pyarrow.csv as pacsv

    try:
        with gzip.open(p, "rt") as fh:
            header = fh.readline().strip().split(",")
        cols = [c for c in PA_EXT_COLS if c in header]
        if "market_id" not in cols:
            return None
        types = {"market_id": pa.int64(), "event_volume": pa.float64(), "event_liquidity": pa.float64(),
                 "competitive": pa.float64(), "event_created_at": pa.string(), "volume_num": pa.float64()}
        t = pacsv.read_csv(p, convert_options=pacsv.ConvertOptions(include_columns=cols, column_types=types))
    except (pa.ArrowInvalid, KeyError, OSError, EOFError):
        return None
    return t.to_pandas().drop_duplicates("market_id").set_index("market_id")


def _pa_col(e: pd.DataFrame, name: str) -> np.ndarray:
    return pd.to_numeric(e[name], errors="coerce").to_numpy(float) if name in e else np.full(len(e), np.nan)


def participation_features(ext: pd.DataFrame | None, prev_ext: pd.DataFrame | None, rows: pd.DataFrame | None,
                           f: pd.DataFrame, cap_start: float) -> pd.DataFrame:
    """Per eligible market (``f`` row order); NaN where the sidecar, the column or the previous capture lacks it."""
    n = len(f)
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in PARTICIPATION_COLUMNS})
    if ext is None or n == 0:
        return out
    ids = f["market_id"].to_numpy(np.int64)
    e = ext.reindex(ids)
    ev_vol, ev_liq = _pa_col(e, "event_volume"), _pa_col(e, "event_liquidity")
    with np.errstate(invalid="ignore", divide="ignore"):
        out["pp_log_ev_vol"] = np.log1p(np.clip(ev_vol, 0, None))
        out["pp_log_ev_liq"] = np.log1p(np.clip(ev_liq, 0, None))
        out["pp_competitive"] = _pa_col(e, "competitive")
        out["pp_log_vol_num"] = np.log1p(np.clip(_pa_col(e, "volume_num"), 0, None))
        if rows is not None and "liquidity" in rows:
            liq = pd.Series(pd.to_numeric(rows["liquidity"], errors="coerce").to_numpy(float),
                            index=rows["market_id"].to_numpy(np.int64))
            liq = liq[~liq.index.duplicated()].reindex(ids).to_numpy(float)
            out["pp_liq_share"] = np.where(ev_liq > 0, np.clip(liq / ev_liq, 0.0, 1.0), np.nan)
        if "event_created_at" in e:
            ca = pd.to_datetime(e["event_created_at"], utc=True, errors="coerce", format="ISO8601")  # with or without fractions
            sec = ca.astype("datetime64[ns, UTC]").astype("int64").to_numpy().astype(float) / 1e9
            sec[ca.isna().to_numpy()] = np.nan
            out["pp_log_ev_age_h"] = np.log1p(np.clip((cap_start - sec) / 3600.0, 0, None))
        if prev_ext is not None:
            pv = _pa_col(prev_ext.reindex(ids), "event_volume")
            ok = np.isfinite(ev_vol) & np.isfinite(pv)
            out["pp_d_ev_vol"] = np.where(ok, np.log1p(np.clip(ev_vol - pv, 0, None)), np.nan)
            out["pp_ev_vol_fell"] = np.where(ok, (ev_vol < pv - PA_FELL_EPS).astype(float), np.nan)
    return out.astype(np.float32)


def _participation_builder(ctx: dict) -> pd.DataFrame:
    prev, paths = ctx["prev"], ctx["paths"]
    prev_ext = read_participation_ext(Path(paths.snapshots) / prev["capture_id"]) if prev is not None else None
    return participation_features(read_participation_ext(ctx["cap_dir"]), prev_ext, ctx["rows"], ctx["f"], ctx["cap_start"])


# ---------------------------------------------------------------------------------------------- book0 family
# The order book strictly BEFORE the origin (DESIGN_V1 section 22). The v1 `book` family is read from sweep 1 of the
# origin's own pass, ~7 min after the capture, so it overlaps the direction label window (section 21). `book0` reads the
# newest complete pass sweep (of an earlier grid capture) that FINISHED before the origin capture started (normally the
# previous pass's last sweep, ~110 min earlier), at most B0_MAX_LAG_S old (else NaN); sweep rows received at or after the capture start are dropped
# (defensive; none expected). Columns: the `book` columns (b0_ prefix, same formulas), the sweep's lag to the capture
# start, its spread, and the origin Gamma mid minus the sweep mid. Embargoed under `book` (an isolating model declares
# both tokens). Inputs: the sweep files only; no snapshot rows.
B0_MAX_LAG_S = 3 * 3600.0
BOOK0_COLUMNS = [c.replace("bk_", "b0_") for c in FAMILY_COLUMNS["book"]] + ["b0_lag_s", "b0_spread", "b0_gap"]
_SWEEP_HEADS: dict[str, dict] = {}  # complete sweep manifests are immutable: cached per directory path


def prior_sweep(sweeps_root: Path, cap_start: float, captures: dict[str, float],
                max_lag_s: float = B0_MAX_LAG_S) -> Path | None:
    """The newest complete PASS sweep with ``cap_start - max_lag_s <= finished < cap_start`` (ties: higher
    series_index). A pass sweep belongs to a grid capture of ``captures`` (capture_id: start) that started before
    ``cap_start``; ad-hoc or subset sweeps and hidden temporary folders are never chosen."""
    best = None
    for mp in Path(sweeps_root).glob("*/manifest.json"):
        if mp.parent.name.startswith("."):
            continue
        key = str(mp.parent)
        h = _SWEEP_HEADS.get(key)
        if h is None:
            m = S._manifest_head(mp)
            if not m or m.get("state") != "complete":
                continue  # not cached: a sweep still in progress is read again next time
            h = _SWEEP_HEADS[key] = {"finished": S.epoch(m.get("finished_utc")), "series_index": m.get("series_index") or 0,
                                     "snapshot_id": m.get("snapshot_id"), "finished_utc": m.get("finished_utc")}
        fin = h["finished"]
        if not (math.isfinite(fin) and cap_start - max_lag_s <= fin < cap_start):
            continue
        if not captures.get(h["snapshot_id"], math.inf) < cap_start or not (mp.parent / "rows.csv.gz").exists():
            continue
        rank = (fin, h["series_index"], mp.parent.name)
        if best is None or rank > best[0]:
            best = (rank, mp.parent)
    return None if best is None else best[1]


def book0_features(sweep_dir: Path | None, f: pd.DataFrame, cap_start: float) -> pd.DataFrame:
    """Per eligible market (``f`` row order; needs market_id, ms_mid): the book0 columns (all NaN without a sweep)."""
    out = pd.DataFrame({c: np.full(len(f), np.nan) for c in BOOK0_COLUMNS})
    if sweep_dir is None:
        return out.astype(np.float32)
    t = read_sweep_book(sweep_dir)
    t = t[_epoch_col(t["batch_receipt_utc"]) < cap_start]
    b = t.reindex(f["market_id"].to_numpy())
    bk = book_columns(b)
    for c in FAMILY_COLUMNS["book"]:
        out[c.replace("bk_", "b0_")] = bk[c].to_numpy(float)
    has = bk["bk_has"].to_numpy(float) > 0
    bb, ba = b["best_bid"].to_numpy(float), b["best_ask"].to_numpy(float)
    out["b0_lag_s"] = np.where(has, cap_start - _epoch_col(b["batch_receipt_utc"]), np.nan)
    out["b0_spread"] = np.where(has, ba - bb, np.nan)
    out["b0_gap"] = np.where(has, f["ms_mid"].to_numpy(float) - (bb + ba) / 2.0, np.nan)
    return out.astype(np.float32)


def _book0_builder(ctx: dict) -> pd.DataFrame:
    captures = {m["capture_id"]: S.epoch(m["started_utc"]) for m in ctx["index"].values()}
    sweep = prior_sweep(ctx["paths"].sweeps, ctx["cap_start"], captures)
    h = _SWEEP_HEADS.get(str(sweep), {}) if sweep is not None else {}
    ctx["provenance"] = {"sweep_id": None if sweep is None else sweep.name, "sweep_snapshot_id": h.get("snapshot_id"),
                         "sweep_series_index": h.get("series_index"), "sweep_finished_utc": h.get("finished_utc"),
                         "sweep_manifest_sha256": None if sweep is None else S.sha256_file(sweep / "manifest.json"),
                         "sweep_rows_sha256": None if sweep is None else S.sha256_file(sweep / "rows.csv.gz")}
    return book0_features(sweep, ctx["f"], ctx["cap_start"])


# ---------------------------------------------------------------------------------------------- crypto family
# Spot reference for crypto template markets (DESIGN_V1 section 23; CANDIDATES builder row 20). A market is mapped when
# its sidecar fee_category is "crypto" and a series slug matches `<asset>-<kind>-<cadence>` (up-or-down, multi-strikes,
# neg-risk, hit-price); text is never parsed, so strikes are unknown and ladders are read through the market's own
# empirical beta to spot. Inputs: the origin capture's own sidecar (`series_slugs`, `fee_category`), its features
# (end_ts, ms_mid), the engine's own quotes files of earlier slots, and Binance spot klines that CLOSED before the
# capture start (venue-clocked, never revised; fetched at build time and kept write-once in aux_inputs/crypto/ with
# their fetch time). A capture with no mapped market fetches nothing.
CR_URL = "https://data-api.binance.vision/api/v3/klines"  # public market data mirror (reachable from the host)
CR_SOURCE = "binance-spot-klines-v3"
CR_ASSETS = {"btc": "BTCUSDT", "bitcoin": "BTCUSDT", "eth": "ETHUSDT", "ethereum": "ETHUSDT", "sol": "SOLUSDT",
             "solana": "SOLUSDT", "xrp": "XRPUSDT", "bnb": "BNBUSDT", "doge": "DOGEUSDT", "dogecoin": "DOGEUSDT",
             "zec": "ZECUSDT", "zcash": "ZECUSDT", "hype": "HYPEUSDT", "hyperliquid": "HYPEUSDT", "ethena": "ENAUSDT",
             "chainlink": "LINKUSDT", "link": "LINKUSDT"}
CR_KINDS = {"up-or-down": 1.0, "multi-strikes": 2.0, "neg-risk": 3.0, "hit-price": 4.0}
CR_UD_CADENCE_H = {"5m": 5 / 60, "15m": 0.25, "hourly": 1.0, "4h": 4.0, "daily": 24.0}  # up/down window length
_CR_SLUG = re.compile(r"^([a-z0-9]+)-(up-or-down|multi-strikes|neg-risk|hit-price)-([a-z0-9]+)$")
CR_INTERVALS = {"1m": 60_000, "5m": 300_000}
CR_LIMIT = 1000  # klines per request: 1m covers 16.7 h, 5m covers 83 h (>= the 3-day beta window)
CR_STALE_S = 300.0  # spot must have a closed 1m kline within 5 min of the capture start, else the asset is NaN
CR_BETA_SLOTS = 36  # beta from the previous 36 two-hour pairs (3 days), the latest pair excluded
CR_BETA_MIN = 4
CRYPTO_COLUMNS = ["cr_has", "cr_kind", "cr_cad_h", "cr_win_h", "cr_ud_z", "cr_ud_gap", "cr_r5m", "cr_r30m", "cr_r2h",
                  "cr_r24h", "cr_rv1h", "cr_rv24h", "cr_beta", "cr_lag", "cr_xs"]
CR_EXT_COLS = ["market_id", "fee_category", "series_slugs"]
CR_FETCH_BUDGET_S = 120.0  # all of one capture's requests; over it nothing is written (retried next tick), so a slow
# network never runs a pass's tick into its timeout before the predictions are written


class CrUnavailable(Exception):
    """Binance answered HTTP 400 for a symbol (not listed on spot): permanent, recorded, never retried."""


def cr_fetch(symbol: str, interval: str, end_ms: int, limit: int = CR_LIMIT, timeout: float = 20.0) -> list[list]:
    """Up to ``limit`` klines with open time <= end_ms as [open_ms, open, close]. Raises on any HTTP/network error."""
    import urllib.request

    url = f"{CR_URL}?symbol={symbol}&interval={interval}&endTime={int(end_ms)}&limit={int(limit)}"
    req = urllib.request.Request(url, headers={"User-Agent": "arepo-signal-engine"})
    import urllib.error

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https host
            data = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            raise CrUnavailable(symbol) from exc
        raise
    return [[int(k[0]), float(k[1]), float(k[4])] for k in data]


def read_crypto_ext(cap_dir) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz" if cap_dir is not None else None
    if p is None or not p.exists():
        return None
    import pyarrow as pa
    import pyarrow.csv as pacsv

    types = {"market_id": pa.int64(), "fee_category": pa.string(), "series_slugs": pa.string()}
    try:
        t = pacsv.read_csv(p, convert_options=pacsv.ConvertOptions(include_columns=CR_EXT_COLS, column_types=types))
    except (pa.ArrowInvalid, KeyError):
        return None  # an older sidecar without series_slugs: the family is NaN for this capture
    return t.to_pandas().drop_duplicates("market_id").set_index("market_id")


def cr_map(ext: pd.DataFrame, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per id: Binance symbol ('' unmapped), kind code (NaN unmapped), up/down window length in hours (NaN otherwise)."""
    e = ext.reindex(ids)
    sym = np.full(len(ids), "", dtype=object)  # a market absent from the sidecar is '' here and NaN in cr_has
    kind = np.full(len(ids), np.nan)
    cad = np.full(len(ids), np.nan)
    cat = e["fee_category"].to_numpy(object)
    slugs = e["series_slugs"].to_numpy(object)
    for i in range(len(ids)):
        if cat[i] != "crypto" or not isinstance(slugs[i], str):
            continue
        try:
            lst = json.loads(slugs[i])
        except ValueError:
            continue
        for s in lst if isinstance(lst, list) else []:
            m = _CR_SLUG.match(s) if isinstance(s, str) else None
            if m and m.group(1) in CR_ASSETS:
                sym[i], kind[i] = CR_ASSETS[m.group(1)], CR_KINDS[m.group(2)]
                if m.group(2) == "up-or-down":
                    cad[i] = CR_UD_CADENCE_H.get(m.group(3), np.nan)
                break
    return sym, kind, cad


class _Klines:
    """Closed klines of one symbol and interval: close times (s) and open / close prices, sorted."""

    def __init__(self, rows: list, interval_ms: int, cap_start: float) -> None:
        a = np.asarray(rows, dtype=float).reshape(-1, 3)
        a = a[(a[:, 0] + interval_ms) / 1000.0 <= cap_start]  # closed before the capture start (defensive re-check)
        a = a[np.argsort(a[:, 0], kind="stable")]
        self.open_s, self.close_s = a[:, 0] / 1000.0, (a[:, 0] + interval_ms) / 1000.0
        self.o, self.c = a[:, 1], a[:, 2]

    def price_at(self, t: np.ndarray, tol_s: float) -> np.ndarray:
        """Close of the last kline closed at or before t (NaN if none within tol_s)."""
        t = np.asarray(t, float)
        if len(self.c) == 0:
            return np.full(t.shape, np.nan)
        pos = np.searchsorted(self.close_s, t, side="right") - 1
        ok = (pos >= 0) & (t - self.close_s[np.maximum(pos, 0)] <= tol_s)
        return np.where(ok, self.c[np.maximum(pos, 0)], np.nan)

    def open_at(self, t: np.ndarray) -> np.ndarray:
        """Open of the kline that opened exactly at t (NaN if absent)."""
        t = np.asarray(t, float)
        if len(self.o) == 0:
            return np.full(t.shape, np.nan)
        pos = np.minimum(np.searchsorted(self.open_s, t), len(self.o) - 1)
        return np.where(np.abs(self.open_s[pos] - t) < 0.5, self.o[pos], np.nan)

    def rv(self, n: int, min_n: int) -> float:
        """sqrt of the sum of squared log returns of the last n closes (NaN below min_n finite returns)."""
        r = np.diff(np.log(self.c[-(n + 1):])) if len(self.c) > 1 else np.array([])
        r = r[np.isfinite(r)]
        return float(np.sqrt((r ** 2).sum())) if len(r) >= min_n else np.nan


def crypto_features(f: pd.DataFrame, ext: pd.DataFrame | None, klines: dict | None, cap_start: float,
                    hist_mids: np.ndarray | None = None, hist_starts: np.ndarray | None = None) -> pd.DataFrame:
    """Per eligible market (``f`` row order; market_id, end_ts, ms_mid): the crypto columns.

    ``klines``: symbol -> {"1m": rows, "5m": rows} ([open_ms, open, close]); ``hist_mids``: (n, J) mids of slots
    k - J + 1 .. k (origin last) and ``hist_starts`` their capture start times (J,)."""
    n = len(f)
    out = pd.DataFrame({c: np.full(n, np.nan) for c in CRYPTO_COLUMNS})
    if ext is None:
        return out.astype(np.float32)
    ids = f["market_id"].to_numpy(np.int64)
    sym, kind, cad = cr_map(ext, ids)
    mapped = sym != ""
    out["cr_has"] = np.where(np.isin(ids, ext.index.to_numpy()), mapped.astype(float), np.nan)  # absent: unknown
    out["cr_kind"] = kind
    out["cr_cad_h"] = cad
    if not mapped.any() or not klines:
        return out.astype(np.float32)
    end = f["end_ts"].to_numpy(float)
    mid = f["ms_mid"].to_numpy(float)
    win = end - cad * 3600.0
    out["cr_win_h"] = (win - cap_start) / 3600.0
    cols = {c: out[c].to_numpy(float).copy() for c in CRYPTO_COLUMNS}
    for s in sorted(set(sym[mapped])):
        rows = np.flatnonzero(sym == s)
        ks = klines.get(s) or {}  # None: the symbol is not on Binance spot (recorded as unavailable)
        k1 = _Klines(ks.get("1m", []), CR_INTERVALS["1m"], cap_start)
        k5 = _Klines(ks.get("5m", []), CR_INTERVALS["5m"], cap_start)
        S0 = float(k1.price_at(np.array([cap_start]), CR_STALE_S)[0])
        if not math.isfinite(S0) or S0 <= 0:
            continue  # no fresh spot: the asset's columns stay NaN
        lr = lambda p, s0=S0: math.log(s0 / p) if math.isfinite(p) and p > 0 else np.nan  # noqa: E731
        cols["cr_r5m"][rows] = lr(float(k1.price_at(np.array([cap_start - 300.0]), 120.0)[0]))
        cols["cr_r30m"][rows] = lr(float(k1.price_at(np.array([cap_start - 1800.0]), 120.0)[0]))
        cols["cr_r2h"][rows] = lr(float(k1.price_at(np.array([cap_start - 7200.0]), 120.0)[0]))
        cols["cr_r24h"][rows] = lr(float(k5.price_at(np.array([cap_start - 86400.0]), 600.0)[0]))
        rv1h = k1.rv(60, 50)
        cols["cr_rv1h"][rows] = rv1h
        cols["cr_rv24h"][rows] = k5.rv(288, 240) / math.sqrt(24.0)  # per-hour scale
        # up/down windows that started before the capture: z of spot against the window's opening price
        ud = rows[np.isfinite(win[rows]) & (win[rows] < cap_start)]
        if len(ud) and math.isfinite(rv1h) and rv1h > 0:
            K = k1.open_at(win[ud])
            K = np.where(np.isfinite(K), K, k5.open_at(win[ud]))
            tau_min = (end[ud] - cap_start) / 60.0
            with np.errstate(invalid="ignore", divide="ignore"):
                z = np.log(S0 / K) / ((rv1h / math.sqrt(60.0)) * np.sqrt(tau_min))
            z = np.where(np.isfinite(z) & (tau_min > 0), z, np.nan)
            cols["cr_ud_z"][ud] = z
            phi = 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0))) if len(z) else z
            cols["cr_ud_gap"][ud] = np.where(np.isfinite(z), phi - mid[ud], np.nan)
        # own empirical beta of the 2 h mid change to the 2 h spot log return (earlier pairs only), applied to the latest
        if hist_mids is not None and hist_starts is not None and hist_mids.shape[1] >= 3:
            sp = k5.price_at(hist_starts, 600.0)
            with np.errstate(invalid="ignore", divide="ignore"):
                ds = np.diff(np.log(sp))  # (J - 1,)
            dm = np.diff(hist_mids[rows], axis=1)  # (r, J - 1)
            dsb, dmb = ds[:-1][-CR_BETA_SLOTS:], dm[:, :-1][:, -CR_BETA_SLOTS:]
            ok = np.isfinite(dmb) & np.isfinite(dsb)[None, :] & (dsb != 0)[None, :]
            sxx = np.where(ok, dsb[None, :] ** 2, 0.0).sum(axis=1)
            sxy = np.where(ok, dmb * dsb[None, :], 0.0).sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                beta = np.where((ok.sum(axis=1) >= CR_BETA_MIN) & (sxx > 0), sxy / sxx, np.nan)
            cols["cr_beta"][rows] = beta
            cols["cr_lag"][rows] = beta * ds[-1] - dm[:, -1]
            cols["cr_xs"][rows] = np.abs(beta) * rv1h * math.sqrt(2.0)
    for c in CRYPTO_COLUMNS:
        out[c] = cols[c]
    return out.astype(np.float32)


def cr_inputs_path(paths: S.Paths, cid: str) -> Path:
    return paths.sub("aux_inputs", "crypto", f"{cid}.json.gz")


def cr_load_or_fetch(paths: S.Paths, cid: str, symbols: list[str], cap_start: float, fetch=None) -> tuple[dict, Path]:
    """The capture's write-once kline inputs: read if present, else fetched (every request must succeed) and written."""
    import gzip

    p = cr_inputs_path(paths, cid)
    if p.exists():
        return json.loads(gzip.decompress(p.read_bytes())), p
    import time

    fetch = fetch or cr_fetch
    end_ms = int(math.floor(cap_start * 1000.0)) - 1
    t0, kl, unavailable = time.monotonic(), {}, []
    for s in symbols:
        try:
            kl[s] = {}
            for iv, ms in CR_INTERVALS.items():
                if time.monotonic() - t0 > CR_FETCH_BUDGET_S:
                    raise TimeoutError(f"crypto fetch budget {CR_FETCH_BUDGET_S:.0f} s exceeded")
                kl[s][iv] = [r for r in fetch(s, iv, end_ms) if (r[0] + ms) / 1000.0 <= cap_start]
        except CrUnavailable:
            kl[s] = None
            unavailable.append(s)
    doc = {"source": CR_SOURCE, "url": CR_URL, "capture_id": cid, "cap_start_utc": S.iso(cap_start),
           "fetched_utc": S.iso(S.now_ts()), "end_ms": end_ms, "limit": CR_LIMIT, "fields": ["open_ms", "open", "close"],
           "unavailable": unavailable, "klines": kl}
    S.write_once_bytes(p, gzip.compress(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
    return json.loads(gzip.decompress(p.read_bytes())), p


def _crypto_builder(ctx: dict) -> pd.DataFrame:
    paths, meta, index = ctx["paths"], ctx["meta"], ctx["index"]
    cid = meta["capture_id"]
    f = S.read_parquet(paths.features(cid), ["market_id", "end_ts", "ms_mid"])
    if pd.api.types.is_datetime64_any_dtype(f["end_ts"]):
        f["end_ts"] = _epoch_col(f["end_ts"])
    ext = read_crypto_ext(ctx["cap_dir"])
    ext_p = Path(ctx["cap_dir"]) / "rows_ext.csv.gz" if ctx["cap_dir"] is not None else None
    ext_sha = S.sha256_file(ext_p) if ext_p is not None and ext_p.exists() else None
    ctx["provenance"] = {"cr_source": CR_SOURCE, "cr_inputs_sha256": None, "cr_fetched_utc": None, "cr_symbols": [],
                         "cr_unavailable": [], "rows_ext_sha256": ext_sha}
    if ext is None:
        return crypto_features(f, None, None, ctx["cap_start"])
    sym, _, _ = cr_map(ext, f["market_id"].to_numpy(np.int64))
    symbols = sorted(set(sym[sym != ""]))
    if not symbols:
        return crypto_features(f, ext, None, ctx["cap_start"])
    doc, p = cr_load_or_fetch(paths, cid, symbols, ctx["cap_start"], ctx.get("cr_fetch"))
    ctx["provenance"] = {"cr_source": CR_SOURCE, "cr_inputs_sha256": S.sha256_file(p), "cr_fetched_utc": doc.get("fetched_utc"),
                         "cr_symbols": symbols, "cr_unavailable": doc.get("unavailable", []), "rows_ext_sha256": ext_sha}
    mids = ctx.get("mids") or SlotMids(paths, index, keep=CR_BETA_SLOTS + 6)
    ids = f["market_id"].to_numpy(np.int64)
    slot = meta["slot"]
    js = list(range(slot - CR_BETA_SLOTS - 1, slot + 1))  # 38 slots: 37 pairs, the last (k-1 -> k) is the latest
    H = np.column_stack([mids.get(j, ids) for j in js])
    starts = np.array([S.epoch(index[j]["started_utc"]) if j in index else S.slot_time(j) for j in js], float)
    return crypto_features(f, ext, doc["klines"], ctx["cap_start"], H, starts)


# ---------------------------------------------------------------------------------------------- registry
# A builder takes a context dict: rows (snapshot rows; None for a family with needs_rows False), f (features key
# columns + ms_mid, ms_spread), prev_mid (previous slot's mids or None), cap_dir, cap_start, paths, meta, prev (the
# previous slot's index entry or None), index, mids (a shared SlotMids or None). It may set ctx["provenance"] (a dict
# merged into the table's parquet metadata).

AUX_FAMILIES: dict[str, dict] = {
    "event": {"version": "se-aux-event-v1", "columns": EVENT_COLUMNS,
              "builder": lambda ctx: event_features(ctx["rows"], ctx["f"], ctx["prev_mid"])},
    "rewards": {"version": "se-aux-rewards-v1", "columns": REWARDS_COLUMNS,
                "builder": lambda ctx: rewards_features(read_reward_ext(ctx["cap_dir"]), ctx["f"], ctx["cap_start"])},
    "movetype": {"version": "se-aux-movetype-v1", "columns": MOVETYPE_COLUMNS, "needs_rows": False,
                 "builder": _movetype_builder},
    "surprise": {"version": "se-aux-surprise-v1", "columns": SURPRISE_COLUMNS, "needs_rows": False,
                 "builder": _surprise_builder},
    "participation": {"version": "se-aux-participation-v1", "columns": PARTICIPATION_COLUMNS, "prev_sidecar": True,
                      "builder": _participation_builder},
    "book0": {"version": "se-aux-book0-v1", "columns": BOOK0_COLUMNS, "needs_rows": False, "builder": _book0_builder},
    # needs the capture's snapshot folder (its sidecar) but not the parsed rows
    "crypto": {"version": "se-aux-crypto-v1", "columns": CRYPTO_COLUMNS, "skip_rows_read": True, "builder": _crypto_builder},
    "hwm": {"version": "se-aux-hwm-v1", "columns": HWM_COLUMNS, "needs_rows": False, "builder": _hwm_builder},
}
AUX_COLUMNS: dict[str, list[str]] = {k: v["columns"] for k, v in AUX_FAMILIES.items()}
AUX_ALL: list[str] = [c for cols in AUX_COLUMNS.values() for c in cols]
MODEL_FAMILY_COLUMNS: dict[str, list[str]] = {**FAMILY_COLUMNS, **AUX_COLUMNS}


def aux_path(paths: S.Paths, family: str, cap: str):
    return paths.sub("aux", family, f"{cap}.parquet")


def build_aux(paths: S.Paths, family: str, meta: dict, cap_dir, index: dict | None = None, mids=None) -> dict | None:
    """Write one capture's aux table (write-once). None if the inputs are gone or it already exists."""
    cid = meta["capture_id"]
    out_p = aux_path(paths, family, cid)
    spec = AUX_FAMILIES[family]
    needs_rows = spec.get("needs_rows", True)
    if out_p.exists() or (needs_rows and (cap_dir is None or not (cap_dir / "rows.csv.gz").exists())):
        return None
    fp = paths.features(cid)
    f = S.read_parquet(fp, KEY_COLUMNS + ["ms_mid", "ms_spread"])
    rows = read_rows(cap_dir) if needs_rows and not spec.get("skip_rows_read") else None
    prev = (index or {}).get(meta["slot"] - 1)
    prev_mid = None
    if prev is not None and paths.quotes(prev["capture_id"]).exists():
        prev_mid = mid_series(S.read_parquet(paths.quotes(prev["capture_id"]), ["market_id", "bid", "ask", "st"]))
    ctx = {"rows": rows, "f": f, "prev_mid": prev_mid, "cap_dir": cap_dir, "cap_start": S.epoch(meta["started_utc"]),
           "paths": paths, "meta": meta, "prev": prev, "index": index or {}, "mids": mids}
    a = spec["builder"](ctx)
    tab = pd.concat([f[["market_id"]].reset_index(drop=True), a.reset_index(drop=True)], axis=1)
    md = {"capture_id": cid, "slot": meta["slot"], "aux_family": family, "aux_version": spec["version"],
          "features_sha256": S.sha256_file(fp), "rows_sha256": S.sha256_file(cap_dir / "rows.csv.gz") if needs_rows else None,
          "prev_capture_id": prev["capture_id"] if prev_mid is not None else None, "written_utc": S.iso(S.now_ts()), "code_commit": S.git_commit()}
    md.update(ctx.get("provenance") or {})  # a builder may record which inputs it read (book0: the sweep)
    if spec.get("prev_sidecar"):  # provenance of the previous slot's sidecar the builder actually read (or None)
        ps = Path(paths.snapshots) / prev["capture_id"] / "rows_ext.csv.gz" if prev is not None else None
        md["prev_sidecar_capture_id"] = prev["capture_id"] if ps is not None and ps.exists() else None
        md["prev_sidecar_sha256"] = S.sha256_file(ps) if ps is not None and ps.exists() else None
    if not S.write_once_parquet(out_p, tab, md):
        return None
    cov = {c: float(np.isfinite(a[c].to_numpy(float)).mean()) if len(a) else None for c in spec["columns"][:3]}
    line = {"capture_id": cid, "family": family, "aux_version": spec["version"], "n_rows": int(len(tab)),
            "sha256": S.sha256_file(out_p), "coverage": cov, "written_utc": md["written_utc"]}
    S.append_log(paths, "aux", [line])
    return line


def run_aux(paths: S.Paths, max_items: int = 4) -> dict:
    """Build missing aux tables for processed captures, newest first (no look-backs, so order is free)."""
    index = S.load_index(paths)
    state = S.load_state(paths)
    caps = {c["id"]: c for c in S.discover_captures(paths, state)}
    written, gone, errors = [], 0, []
    mids = SlotMids(paths, index, keep=max(SP_LOOKBACK, HW_LOOKBACK) + 4)  # shared across captures (newest first)
    for _slot, m in sorted(index.items(), reverse=True):
        cid = m["capture_id"]
        for fam in AUX_FAMILIES:
            if aux_path(paths, fam, cid).exists():
                continue
            cap = caps.get(cid)
            has_rows = cap is not None and (cap["dir"] / "rows.csv.gz").exists()
            if AUX_FAMILIES[fam].get("needs_rows", True) and not has_rows:
                gone += 1
                continue
            if len(written) + len(errors) >= max_items:  # a failed build uses budget too
                continue
            try:
                r = build_aux(paths, fam, m, cap["dir"] if cap is not None else None, index, mids)
            except Exception as e:  # noqa: BLE001 - one build's failure must not block the others or the predictions
                # no table is written (missing stays missing); this capture is retried at the next run, the others go on
                errors.append({"capture_id": cid, "family": fam, "error": f"{type(e).__name__}: {e}"[:300]})
                continue
            if r:
                written.append({k: r[k] for k in ("capture_id", "family", "n_rows")})
    S.save_state(paths, state)
    return {"written": written, "unbuildable_no_rows": gone, **({"errors": errors} if errors else {})}


# ---------------------------------------------------------------------------------------------- readers


def aux_sources(paths: S.Paths, cid: str) -> dict[str, bool]:
    """File existence only (cheap); training uses the join result ``read_features(...).attrs["aux_ok"]``."""
    return {fam: aux_path(paths, fam, cid).exists() for fam in AUX_FAMILIES}


def read_features(paths: S.Paths, cid: str, columns: list[str] | None = None) -> pd.DataFrame:
    """The capture's v1 features (``columns`` of them, default all) plus every aux family's columns (NaN if absent)."""
    base_cols = columns if columns is not None else KEY_COLUMNS + ALL_FEATURES
    base = [c for c in base_cols if c not in AUX_ALL]
    if "market_id" not in base:
        base = ["market_id"] + base
    f = S.read_parquet(paths.features(cid), base)
    ok: dict[str, bool] = {}
    want = AUX_ALL if columns is None else [c for c in columns if c in AUX_ALL]
    for fam, cols in AUX_COLUMNS.items():
        need = [c for c in cols if c in want]
        if not need:
            continue
        p = aux_path(paths, fam, cid)
        a = S.read_parquet(p, ["market_id"] + need) if p.exists() else None
        ok[fam] = a is not None and len(a) == len(f) and np.array_equal(a["market_id"].to_numpy(np.int64), f["market_id"].to_numpy(np.int64))
        if a is not None and not ok[fam]:
            f.attrs.setdefault("aux_misaligned", []).append(fam)  # treated as missing, counted by the callers
        for c in need:
            f[c] = a[c].to_numpy(np.float32) if ok[fam] else np.full(len(f), np.nan, np.float32)
    f.attrs["aux_ok"] = ok  # per family: the table exists and joined (row order and market ids checked)
    return f


def spec_aux_families(spec: dict) -> list[str]:
    return [fam for fam in spec["families"] if fam in AUX_FAMILIES]


def check_spec_aux(spec: dict) -> str | None:
    """None if every aux family of the spec is pinned at the current version."""
    pins = spec.get("aux_versions") or {}
    for fam in spec_aux_families(spec):
        if pins.get(fam) != AUX_FAMILIES[fam]["version"]:
            return f"aux family {fam}: pinned {pins.get(fam)!r} != {AUX_FAMILIES[fam]['version']}"
    extra = set(pins) - set(spec_aux_families(spec))
    if extra:
        return f"aux_versions pins unused families {sorted(extra)}"
    return None


__all__ = ["AUX_FAMILIES", "AUX_COLUMNS", "AUX_ALL", "MODEL_FAMILY_COLUMNS", "aux_path", "build_aux", "run_aux",
           "aux_sources", "read_features", "spec_aux_families", "check_spec_aux", "event_features", "movetype_features",
           "surprise_features", "participation_features", "crypto_features", "hwm_features"]
