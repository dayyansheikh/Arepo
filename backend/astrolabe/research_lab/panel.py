"""E001 panel: (market, capture i, next full capture j) pairs.

Eligibility and every feature are computed from the origin (capture i) row only. The only
information about j used in eligibility is j's *scheduled* capture start (known from the capture
list, not from any j market row); j's rows define the target and target-unavailability only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SPREAD_MAX = 0.10
MID_LO, MID_HI = 0.02, 0.98

FEATURES_B2 = ["mid", "chg_1h", "chg_1d", "chg_1w"]
FEATURES_B3 = [
    "mid",
    "spread",
    "chg_1h",
    "chg_1d",
    "chg_1w",
    "chg_1h_missing",
    "chg_1d_missing",
    "chg_1w_missing",
    "log_liq",
    "log_vol",
    "log_hours_to_end",
    "end_unknown",
    "ltp_minus_mid",
    "ltp_missing",
    "chg1d_x_logliq",
]


def _epoch(s: pd.Series) -> np.ndarray:
    dt = pd.to_datetime(s, utc=True, errors="coerce", format="ISO8601")
    out = dt.astype("int64").to_numpy().astype(float) / 1e9
    out[dt.isna().to_numpy()] = np.nan
    return out


def eligibility_mask(o: pd.DataFrame, j_scheduled_epoch: float) -> np.ndarray:
    """Registered eligibility, using only columns of the origin rows ``o`` (plus j's schedule)."""
    bid, ask = o["best_bid"].to_numpy(float), o["best_ask"].to_numpy(float)
    spread = o["spread"].to_numpy(float)
    spread = np.where(np.isnan(spread), ask - bid, spread)
    mid = (bid + ask) / 2
    end = _epoch(o["end_date"])
    closed = o["closed"].astype(str).str.lower().eq("true").to_numpy()
    active = o["active"].astype(str).str.lower().eq("true").to_numpy()
    with np.errstate(invalid="ignore"):
        ok = (
            (o["binary"].to_numpy() == 1)
            & ~closed
            & active
            & (bid > 0)
            & (bid < ask)
            & (ask < 1)
            & (spread <= SPREAD_MAX)
            & (mid >= MID_LO)
            & (mid <= MID_HI)
            & (np.isnan(end) | (end > j_scheduled_epoch))
        )
    return ok


def compute_features(o: pd.DataFrame, t_i: np.ndarray) -> pd.DataFrame:
    """Features from origin rows only (``o`` row-aligned with ``t_i`` epoch seconds)."""
    bid, ask = o["best_bid"].to_numpy(float), o["best_ask"].to_numpy(float)
    mid = (bid + ask) / 2
    f = pd.DataFrame(index=o.index)
    f["mid"] = mid
    f["spread"] = np.where(
        np.isnan(o["spread"].to_numpy(float)), ask - bid, o["spread"].to_numpy(float)
    )
    for src, name in (("chg_1h", "chg_1h"), ("chg_1d", "chg_1d"), ("chg_1w", "chg_1w")):
        v = o[src].to_numpy(float)
        f[f"{name}_missing"] = np.isnan(v).astype(float)
        f[name] = np.where(np.isnan(v), 0.0, v)
    liq = np.nan_to_num(o["liquidity"].to_numpy(float), nan=0.0).clip(min=0)
    vol = np.nan_to_num(o["volume24hr"].to_numpy(float), nan=0.0).clip(min=0)
    f["log_liq"] = np.log1p(liq)
    f["log_vol"] = np.log1p(vol)
    end = _epoch(o["end_date"])
    unknown = np.isnan(end)
    hours = np.where(unknown, 0.0, np.clip((end - t_i) / 3600.0, 0, None))
    f["log_hours_to_end"] = np.log1p(hours)
    f["end_unknown"] = unknown.astype(float)
    ltp = o["last_trade_price"].to_numpy(float)
    f["ltp_missing"] = np.isnan(ltp).astype(float)
    f["ltp_minus_mid"] = np.where(np.isnan(ltp), 0.0, ltp - mid)
    f["chg1d_x_logliq"] = f["chg_1d"].to_numpy() * f["log_liq"].to_numpy()
    return f[FEATURES_B3]


def target_valid(j: pd.DataFrame) -> np.ndarray:
    """Two-sided quote at j: bid>0, ask>0, ask<=1, bid<ask, and not closed."""
    bid, ask = j["best_bid"].to_numpy(float), j["best_ask"].to_numpy(float)
    closed = j["closed"].astype(str).str.lower().eq("true").to_numpy()
    with np.errstate(invalid="ignore"):
        return (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask) & ~closed


def build_pair(
    snap_i: pd.DataFrame, snap_j: pd.DataFrame, j_scheduled_epoch: float, period: int
) -> tuple[pd.DataFrame, dict]:
    """Pairs for one consecutive full-capture couple. ``snap_*`` are deduplicated capture slices."""
    n_rows_i = len(snap_i)
    binary = snap_i[snap_i["binary"] == 1]
    ok = eligibility_mask(binary, j_scheduled_epoch)
    o = binary[ok].reset_index(drop=True)
    t_i = _epoch(o["received_utc"])
    feats = compute_features(o, t_i)
    jj = snap_j.drop_duplicates("market_id").set_index("market_id")
    jm = jj.reindex(o["market_id"])
    present = (
        jm["best_bid"].notna().to_numpy()
        | jm["best_ask"].notna().to_numpy()
        | jm["received_utc"].notna().to_numpy()
    )
    valid = np.zeros(len(o), bool)
    if present.any():
        valid[present] = target_valid(jm[present])
    t_j = _epoch(jm["received_utc"].reset_index(drop=True))
    mid_j = ((jm["best_bid"] + jm["best_ask"]) / 2).to_numpy(float)
    out = feats.copy()
    out.insert(0, "market_id", o["market_id"].to_numpy())
    out.insert(1, "event_id", o["event_id"].to_numpy())
    out.insert(2, "period", period)
    out.insert(3, "t_i", t_i)
    out["t_j"] = np.where(valid, t_j, np.nan)
    out["mid_j"] = np.where(valid, mid_j, np.nan)
    out["dmid"] = out["mid_j"] - out["mid"]
    out["horizon_h"] = (out["t_j"] - out["t_i"]) / 3600.0
    counts = {
        "period": period,
        "origin_rows": n_rows_i,
        "binary_rows": len(binary),
        "eligible": int(ok.sum()),
        "target_available": int(valid.sum()),
        "target_unavailable": int((~valid).sum()),
        "missing_at_j": int((~present).sum()),
        "one_sided_or_closed_at_j": int((present & ~valid).sum()),
        "spread_field_vs_ask_minus_bid_mismatch": int(
            (
                np.abs(
                    o["spread"].to_numpy(float)
                    - (o["best_ask"].to_numpy(float) - o["best_bid"].to_numpy(float))
                )
                > 1e-6
            ).sum()
        ),
    }
    return out, counts


def build_panel(snap: pd.DataFrame, captures: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    """All consecutive full-capture pairs; ``captures`` ordered by start (capture_id, start_utc)."""
    frames, counts = [], []
    by_cap = {cid: g for cid, g in snap.groupby("capture_id")}
    for k in range(len(captures) - 1):
        ci, cj = captures[k], captures[k + 1]
        j_sched = _epoch(pd.Series([cj["start_utc"]]))[0]
        pairs, c = build_pair(by_cap[ci["capture_id"]], by_cap[cj["capture_id"]], j_sched, k)
        c.update({"capture_i": ci["capture_id"], "capture_j": cj["capture_id"]})
        frames.append(pairs)
        counts.append(c)
    return pd.concat(frames, ignore_index=True), counts


def usable(panel: pd.DataFrame) -> pd.DataFrame:
    """Pairs with an available target."""
    return panel[panel["dmid"].notna()].reset_index(drop=True)
