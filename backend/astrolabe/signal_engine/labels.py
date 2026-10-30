# ruff: noqa: E501
"""Labels, strictly after the origin, with explicit states (never filled).

Direction (``dir_{h}h``): the Gamma mid of the market in the complete capture of slot ``k + h/2`` minus its origin mid;
class 0 down (dmid < -DELTA), 1 flat (|dmid| <= DELTA), 2 up (dmid > DELTA). The label exists once that capture's quotes
file is written; its availability time is the target capture's finish time.

Resolution (``res_7d``): outcome 0 resolves YES (1) or NO (0), parsed with the C1 rules (``calibration.parse_outcome``)
from a Gamma ``/markets?id=`` fetch made after the scheduled end. Availability time = fetch receipt time. A market whose
close time precedes a prediction's write time makes that prediction late (scored as excluded).
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd

from . import config as C
from . import store as S

LABEL_STATES = ("labelled", "pending", "unavailable_missing_capture", "unavailable_absent", "unavailable_closed",
                "unavailable_inactive", "unavailable_one_sided", "unavailable_split", "unavailable_other",
                "unavailable_unresolved")
LABELLED, PENDING = 0, 1
_ST_REASON = {1: 4, 2: 5, 3: 6}  # quotes status -> label state
FINAL_RES = {"resolved", "split_50_50", "other_price_vector", "bad_prices"}


def horizon_slots(h: int) -> int:
    return int(h // 2)


def dir_eligible(end_ts: np.ndarray, slot: int, h: int) -> np.ndarray:
    """Known ex ante: the scheduled end lies after the target slot (or is unknown)."""
    tgt = S.slot_time(slot + horizon_slots(h))
    end_ts = np.asarray(end_ts, float)
    with np.errstate(invalid="ignore"):
        return np.isnan(end_ts) | (end_ts > tgt)


def res_eligible(end_ts: np.ndarray, cap_start: float) -> np.ndarray:
    end_ts = np.asarray(end_ts, float)
    with np.errstate(invalid="ignore"):
        return (end_ts > cap_start + C.RES_MIN_S) & (end_ts <= cap_start + C.RES_MAX_S)


def elig_mask(feats: pd.DataFrame, slot: int, cap_start: float) -> np.ndarray:
    """uint8 bit mask of the targets each row is eligible for (config.ELIG_BITS)."""
    end = feats["end_ts"].to_numpy(float)
    m = np.zeros(len(feats), np.uint8)
    for h, t in zip(C.HORIZONS_H, C.DIR_TARGETS, strict=True):
        m |= np.where(dir_eligible(end, slot, h), C.ELIG_BITS[t], 0).astype(np.uint8)
    m |= np.where(res_eligible(end, cap_start), C.ELIG_BITS[C.RES_TARGET], 0).astype(np.uint8)
    return m


def classify(dmid: np.ndarray) -> np.ndarray:
    d = np.asarray(dmid, float)
    return np.where(d < -C.DELTA - C.DELTA_TOL, 0, np.where(d > C.DELTA + C.DELTA_TOL, 2, 1)).astype(np.int8)


class QuoteCache:
    """Bounded cache of target quotes frames (market_id-indexed)."""

    def __init__(self, paths: S.Paths, index: dict[int, dict], keep: int = 16) -> None:
        self.paths, self.index, self.keep, self.d = paths, index, keep, {}

    def get(self, slot: int) -> pd.DataFrame | None:
        if slot in self.d:
            return self.d[slot]
        m = self.index.get(slot)
        q = None
        if m is not None:
            p = self.paths.quotes(m["capture_id"])
            if p.exists():
                q = S.read_parquet(p, ["market_id", "bid", "ask", "st"]).drop_duplicates("market_id").set_index("market_id")
        self.d[slot] = q
        while len(self.d) > self.keep:
            self.d.pop(next(iter(self.d)))
        return q


def target_time(index: dict[int, dict], slot: int) -> float:
    m = index.get(slot)
    if m is None:
        return math.nan
    t = S.epoch(m.get("finished_utc")) if m.get("finished_utc") else math.nan
    return t if math.isfinite(t) else S.epoch(m.get("started_utc"))


def direction_labels(qc: QuoteCache, index: dict[int, dict], slot: int, h: int, market_ids: np.ndarray,
                     mid_i: np.ndarray, now: float) -> tuple[np.ndarray, np.ndarray, float]:
    """(y int8 with -1 where not labelled, state int8, label availability time) for one origin capture."""
    n = len(market_ids)
    j = slot + horizon_slots(h)
    y = np.full(n, -1, np.int8)
    q = qc.get(j)
    if q is None:
        missing = now >= S.slot_time(j) + C.MISSING_AFTER_S and j not in index
        return y, np.full(n, 2 if missing else PENDING, np.int8), math.nan
    t = q.reindex(np.asarray(market_ids, np.int64))
    st = t["st"].to_numpy(float)
    state = np.full(n, 3, np.int8)  # absent from the listing
    for code, reason in _ST_REASON.items():
        state[st == code] = reason
    ok = st == 0
    state[ok] = LABELLED
    mid_j = (t["bid"].to_numpy(np.float64) + t["ask"].to_numpy(np.float64)) / 2.0
    y[ok] = classify(mid_j[ok] - np.asarray(mid_i, np.float64)[ok])
    return y, state, target_time(index, j)


# ---------------------------------------------------------------------------------------------- resolution


def load_resolutions(paths: S.Paths) -> pd.DataFrame:
    """Latest fetch record per market (columns state, y, closed_ts, fetched_ts)."""
    rows = S.read_logs(paths, "resolutions")
    if not rows:
        return pd.DataFrame(columns=["state", "y", "closed_ts", "fetched_ts"], index=pd.Index([], dtype=np.int64, name="market_id"))
    df = pd.DataFrame(rows)
    df["fetched_ts"] = df["fetched_utc"].map(S.epoch)
    df["closed_ts"] = df.get("closed_time", pd.Series([None] * len(df))).map(lambda v: S.epoch(v) if v else math.nan)
    df["market_id"] = df["market_id"].astype(np.int64)
    df = df.sort_values("fetched_ts").drop_duplicates("market_id", keep="last").set_index("market_id")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    return df[["state", "y", "closed_ts", "fetched_ts"]]


def resolution_labels(res: pd.DataFrame, market_ids: np.ndarray, end_ts: np.ndarray, now: float,
                      fit_time: float | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(y, state, label time, close time). With ``fit_time`` only records fetched strictly before it count."""
    n = len(market_ids)
    r = res.reindex(np.asarray(market_ids, np.int64))
    fetched = r["fetched_ts"].to_numpy(float)
    known = np.isfinite(fetched) if fit_time is None else (fetched < fit_time)
    st = r["state"].astype(object).to_numpy()
    yv = r["y"].to_numpy(float)
    y = np.full(n, -1, np.int8)
    state = np.full(n, PENDING, np.int8)
    is_res = known & (st == "resolved") & np.isfinite(yv)
    y[is_res] = yv[is_res].astype(np.int8)
    state[is_res] = LABELLED
    state[known & (st == "split_50_50")] = 7
    state[known & np.isin(st, ["other_price_vector", "bad_prices"])] = 8
    ref = now if fit_time is None else fit_time
    with np.errstate(invalid="ignore"):
        giveup = (state == PENDING) & (ref > np.asarray(end_ts, float) + C.RES_GIVEUP_S)
    state[giveup] = 9
    return y, state, np.where(is_res, fetched, np.nan), r["closed_ts"].to_numpy(float)


def resolution_candidates(paths: S.Paths, index: dict[int, dict], now: float, state: dict) -> dict[int, float]:
    """market_id -> scheduled end of every market with a res-eligible feature row (cached per capture)."""
    cand = {int(k): v for k, v in state.get("res_candidates", {}).items()}
    seen = set(state.get("res_seen", []))
    for _slot, m in sorted(index.items()):
        cid = m["capture_id"]
        if cid in seen:
            continue
        p = paths.features(cid)
        if not p.exists():
            continue
        f = S.read_parquet(p, ["market_id", "end_ts"])
        ok = res_eligible(f["end_ts"].to_numpy(float), S.epoch(m["started_utc"]))
        for mid, e in zip(f["market_id"].to_numpy()[ok], f["end_ts"].to_numpy(float)[ok], strict=True):
            cand[int(mid)] = float(e)
        seen.add(cid)
    state["res_candidates"] = {str(k): v for k, v in cand.items()}
    state["res_seen"] = sorted(seen)
    return cand


def due_for_fetch(cand: dict[int, float], res: pd.DataFrame, now: float) -> list[int]:
    out = []
    for mid, end in cand.items():
        if not (end < now - 3600.0 and now < end + C.RES_GIVEUP_S):
            continue
        if mid in res.index:
            r = res.loc[mid]
            if r["state"] in FINAL_RES or now - float(r["fetched_ts"]) < C.RES_REFETCH_S:
                continue
        out.append(mid)
    return sorted(out, key=lambda m: cand[m])


def fetch_resolutions(paths: S.Paths, ids: list[int], get, max_requests: int, batch: int = 50) -> Counter:
    """Fetch Gamma market records by id in batches; append one line per market. ``get(params) -> (json, reason)``."""
    from astrolabe.research_lab import calibration

    c: Counter = Counter()
    for i in range(0, len(ids), batch):
        if c["requests"] >= max_requests:
            break
        chunk = ids[i:i + batch]
        c["requests"] += 1
        data, reason = get([("id", str(x)) for x in chunk] + [("limit", str(batch)), ("closed", "true")])
        if not isinstance(data, list):
            c[f"error_{reason}"] += 1
            continue
        got = {int(m.get("id")): m for m in data if str(m.get("id", "")).isdigit()}
        rows = []
        t = S.now_ts()
        for mid in chunk:
            m = got.get(mid)
            if m is None:
                rows.append({"market_id": mid, "state": "not_found", "y": None, "fetched_utc": S.iso(t)})
                c["not_found"] += 1
                continue
            y, why = calibration.parse_outcome(m)
            st = "resolved" if y is not None else why
            rows.append({"market_id": mid, "state": st, "y": y, "closed": m.get("closed"),
                         "closed_time": m.get("closedTime") or None, "uma": m.get("umaResolutionStatus"),
                         "fetched_utc": S.iso(t), "labels_version": C.LABELS_VERSION})
            c[st] += 1
        S.append_log(paths, "resolutions", rows, at=t)
    return c
