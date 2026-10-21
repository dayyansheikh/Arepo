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


# ---------------------------------------------------------------------------------------------- registry

AUX_FAMILIES: dict[str, dict] = {
    "event": {"version": "se-aux-event-v1", "columns": EVENT_COLUMNS, "builder": event_features},
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
    if out_p.exists() or not (cap_dir / "rows.csv.gz").exists():
        return None
    fp = paths.features(cid)
    f = S.read_parquet(fp, KEY_COLUMNS + ["ms_mid"])
    rows = read_rows(cap_dir)
    spec = AUX_FAMILIES[family]
    prev = (index or {}).get(meta["slot"] - 1)
    prev_mid = None
    if prev is not None and paths.quotes(prev["capture_id"]).exists():
        prev_mid = mid_series(S.read_parquet(paths.quotes(prev["capture_id"]), ["market_id", "bid", "ask", "st"]))
    a = spec["builder"](rows, f, prev_mid)
    tab = pd.concat([f[["market_id"]].reset_index(drop=True), a.reset_index(drop=True)], axis=1)
    md = {"capture_id": cid, "slot": meta["slot"], "aux_family": family, "aux_version": spec["version"],
          "features_sha256": S.sha256_file(fp), "rows_sha256": S.sha256_file(cap_dir / "rows.csv.gz"),
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
            if cap is None or not (cap["dir"] / "rows.csv.gz").exists():
                gone += 1
                continue
            if len(written) >= max_items:
                continue
            r = build_aux(paths, fam, m, cap["dir"], index)
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
           "aux_sources", "read_features", "spec_aux_families", "check_spec_aux", "event_features"]
