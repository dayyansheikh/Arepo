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
    mid_series,
    read_rows,
)

# ---------------------------------------------------------------------------------------------- event family
# Event-level context from the same capture's complete binary listing (every market of the event, including
# siblings that are not eligible themselves). Development history: E005 (neg-risk band deviation, closed 2026-10-11,
# not supported) and SB2-J5 (sibling reversal, development only); no registered live test isolates it (checked
# 2026-10-21), so no embargo token.
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


# ---------------------------------------------------------------------------------------------- registry
# A builder takes a context dict: rows (snapshot rows; None for a family with needs_rows False), f (features key
# columns + ms_mid, ms_spread), prev_mid (previous slot's mids or None), cap_dir, cap_start, paths, meta, prev (the
# previous slot's index entry or None).

AUX_FAMILIES: dict[str, dict] = {
    "event": {"version": "se-aux-event-v1", "columns": EVENT_COLUMNS,
              "builder": lambda ctx: event_features(ctx["rows"], ctx["f"], ctx["prev_mid"])},
    "rewards": {"version": "se-aux-rewards-v1", "columns": REWARDS_COLUMNS,
                "builder": lambda ctx: rewards_features(read_reward_ext(ctx["cap_dir"]), ctx["f"], ctx["cap_start"])},
    "movetype": {"version": "se-aux-movetype-v1", "columns": MOVETYPE_COLUMNS, "needs_rows": False,
                 "builder": _movetype_builder},
}
AUX_COLUMNS: dict[str, list[str]] = {k: v["columns"] for k, v in AUX_FAMILIES.items()}
AUX_ALL: list[str] = [c for cols in AUX_COLUMNS.values() for c in cols]
MODEL_FAMILY_COLUMNS: dict[str, list[str]] = {**FAMILY_COLUMNS, **AUX_COLUMNS}


def aux_path(paths: S.Paths, family: str, cap: str):
    return paths.sub("aux", family, f"{cap}.parquet")


def build_aux(paths: S.Paths, family: str, meta: dict, cap_dir, index: dict | None = None) -> dict | None:
    """Write one capture's aux table (write-once). None if the inputs are gone or it already exists."""
    cid = meta["capture_id"]
    out_p = aux_path(paths, family, cid)
    spec = AUX_FAMILIES[family]
    needs_rows = spec.get("needs_rows", True)
    if out_p.exists() or (needs_rows and (cap_dir is None or not (cap_dir / "rows.csv.gz").exists())):
        return None
    fp = paths.features(cid)
    f = S.read_parquet(fp, KEY_COLUMNS + ["ms_mid", "ms_spread"])
    rows = read_rows(cap_dir) if needs_rows else None
    prev = (index or {}).get(meta["slot"] - 1)
    prev_mid = None
    if prev is not None and paths.quotes(prev["capture_id"]).exists():
        prev_mid = mid_series(S.read_parquet(paths.quotes(prev["capture_id"]), ["market_id", "bid", "ask", "st"]))
    a = spec["builder"]({"rows": rows, "f": f, "prev_mid": prev_mid, "cap_dir": cap_dir,
                         "cap_start": S.epoch(meta["started_utc"]), "paths": paths, "meta": meta, "prev": prev})
    tab = pd.concat([f[["market_id"]].reset_index(drop=True), a.reset_index(drop=True)], axis=1)
    md = {"capture_id": cid, "slot": meta["slot"], "aux_family": family, "aux_version": spec["version"],
          "features_sha256": S.sha256_file(fp), "rows_sha256": S.sha256_file(cap_dir / "rows.csv.gz") if needs_rows else None,
          "prev_capture_id": prev["capture_id"] if prev_mid is not None else None, "written_utc": S.iso(S.now_ts()), "code_commit": S.git_commit()}
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
    written, gone = [], 0
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
            if len(written) >= max_items:
                continue
            r = build_aux(paths, fam, m, cap["dir"] if cap is not None else None, index)
            if r:
                written.append({k: r[k] for k in ("capture_id", "family", "n_rows")})
    S.save_state(paths, state)
    return {"written": written, "unbuildable_no_rows": gone}


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
           "aux_sources", "read_features", "spec_aux_families", "check_spec_aux", "event_features", "movetype_features"]
