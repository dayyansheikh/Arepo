# ruff: noqa: E501
"""Per-capture feature store: slim quotes (labels, look-backs) and origin-side feature rows.

For every complete capture (oldest first) this writes, write-once:

* ``quotes/<capture>.parquet``   every binary market of the listing: market_id, receipt offset, bid, ask (float32,
  only for open two-sided rows) and a status code (0 open two-sided, 1 closed, 2 inactive, 3 one-sided). Direction
  labels and own-price look-backs come from these files, so the engine does not depend on the 8-day snapshot retention.
* ``features/<capture>.parquet`` one row per ELIGIBLE market (float32 features, NaN = missing, never filled here).
* ``meta/<capture>.json``        slot, clocks, counts, exclusions, which family sources were present, file sha256.

Causality: every feature uses the origin capture, earlier captures (own look-backs) or inputs received before the
prediction is written (trade sample: trades strictly before the market's origin row receipt; book sweep: the first sweep
of this pass, received minutes after the capture and long before any target capture; Kalshi quotes received before
the capture start). No later capture is ever read here. The book sweep is AFTER the label origin (the origin capture's
Gamma mid), so book inputs overlap the label window by ~7 min: DESIGN_V1 section 21 (se7 promotion-ineligible).
"""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv

from . import config as C
from . import store as S

TS = pa.timestamp("us", tz="UTC")
ROW_COLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "spread",
            "last_trade_price", "chg_1h", "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date", "updated_at",
            "neg_risk"]
EXT_COLS = ["market_id", "fee_category", "created_at", "uma_resolution_statuses", "order_price_min_tick_size"]

KEY_COLUMNS = ["market_id", "event_id", "category", "t_row", "end_ts"]
FAMILY_COLUMNS: dict[str, list[str]] = {
    "market_state": ["ms_mid", "ms_spread", "ms_log_liq", "ms_log_vol24", "ms_hours_to_end", "ms_ltp_minus_mid",
                     "ms_stale_s", "ms_age_h", "ms_tick", "ms_neg_risk", "ms_rv24", "ms_nobs24"],
    "momentum": ["mo_chg_1h", "mo_chg_1d", "mo_chg_1w", "mo_d2h", "mo_d6h", "mo_d24h"],
    "flow": ["fl_sampled", "fl_n1h", "fl_notional1h", "fl_signed", "fl_maxliq", "fl_since_last"],
    "book": ["bk_has", "bk_imb1", "bk_imb1c", "bk_imb5c", "bk_depth5c", "bk_micro", "bk_age_s", "bk_levels"],
    "xvenue": ["xv_has", "xv_gap", "xv_kspread", "xv_age_s"],
    "wallet": ["wl_has", "wl_n24", "wl_top1", "wl_hhi"],
}
FAMILIES = tuple(FAMILY_COLUMNS)
SOURCE_FAMILIES = ("flow", "book", "xvenue", "wallet")  # families fed by a separate collector stream
ALL_FEATURES = [c for cols in FAMILY_COLUMNS.values() for c in cols]
LOOKBACK_SLOTS = 12  # own realised volatility and 24 h change use the previous 12 slots (24 h)


# ---------------------------------------------------------------------------------------------- readers


def _epoch_col(s: pd.Series) -> np.ndarray:
    """Epoch seconds from a tz-aware datetime column (any unit); NaN where missing."""
    v = pd.to_datetime(s, utc=True)
    ns = v.astype("datetime64[ns, UTC]")
    out = ns.astype("int64").to_numpy().astype(float) / 1e9
    out[ns.isna().to_numpy()] = np.nan
    return out


def read_rows(cap_dir: Path) -> pd.DataFrame:
    p = Path(cap_dir) / "rows.csv.gz"
    types = {"market_id": pa.int64(), "event_id": pa.string(), "received_utc": TS, "closed": pa.string(),
             "active": pa.string(), "binary": pa.int64(), "end_date": TS, "updated_at": TS, "neg_risk": pa.float64()}
    for c in ("best_bid", "best_ask", "spread", "last_trade_price", "chg_1h", "chg_1d", "chg_1w", "liquidity",
              "volume24hr"):
        types[c] = pa.float64()
    t = pacsv.read_csv(p, convert_options=pacsv.ConvertOptions(include_columns=ROW_COLS, column_types=types))
    df = t.to_pandas()
    df = df.drop_duplicates("market_id").reset_index(drop=True)
    return df


def read_ext(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    types = {"market_id": pa.int64(), "fee_category": pa.string(), "created_at": TS,
             "uma_resolution_statuses": pa.string(), "order_price_min_tick_size": pa.float64()}
    t = pacsv.read_csv(p, convert_options=pacsv.ConvertOptions(include_columns=EXT_COLS, column_types=types))
    return t.to_pandas().drop_duplicates("market_id").set_index("market_id")


def _truthy(s: pd.Series) -> np.ndarray:
    return s.astype(str).str.lower().isin(("true", "1")).to_numpy()


# ---------------------------------------------------------------------------------------------- quotes


def quotes_frame(rows: pd.DataFrame, cap_start: float) -> pd.DataFrame:
    """Every binary market of the listing with its status; bid/ask only for open two-sided rows."""
    b = rows[rows["binary"] == 1]
    bid, ask = b["best_bid"].to_numpy(float), b["best_ask"].to_numpy(float)
    closed, active = _truthy(b["closed"]), _truthy(b["active"])
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask)
    st = np.where(closed, 1, np.where(~active, 2, np.where(two, 0, 3))).astype(np.int8)
    t_row = _epoch_col(b["received_utc"])
    ok = st == 0
    return pd.DataFrame({"market_id": b["market_id"].to_numpy(np.int64),
                         "t_off": (t_row - cap_start).astype(np.float32),
                         "bid": np.where(ok, bid, np.nan).astype(np.float32),
                         "ask": np.where(ok, ask, np.nan).astype(np.float32), "st": st})


def mid_series(q: pd.DataFrame) -> pd.Series:
    """market_id -> float64 mid of the open two-sided rows of a quotes frame."""
    o = q[q["st"] == 0]
    return pd.Series((o["bid"].to_numpy(np.float64) + o["ask"].to_numpy(np.float64)) / 2.0,
                     index=o["market_id"].to_numpy(np.int64))


class MidCache:
    """Bounded cache of mid series per slot (look-backs during a backfill read each quotes file once)."""

    def __init__(self, paths: S.Paths, index: dict[int, dict], keep: int = LOOKBACK_SLOTS + 4) -> None:
        self.paths, self.index, self.keep, self.d = paths, index, keep, {}

    def get(self, slot: int) -> pd.Series | None:
        if slot in self.d:
            return self.d[slot]
        m = self.index.get(slot)
        s = None
        if m is not None:
            p = self.paths.quotes(m["capture_id"])
            if p.exists():
                s = mid_series(S.read_parquet(p, ["market_id", "bid", "ask", "st"]))
        self.d[slot] = s
        while len(self.d) > self.keep:
            self.d.pop(min(self.d))
        return s


# ---------------------------------------------------------------------------------------------- eligibility


def has_proposal(s: pd.Series) -> np.ndarray:
    v = s.fillna("").astype(str).str.strip()
    return ~v.isin(("", "[]", "nan", "None", "null"))


def eligibility(rows: pd.DataFrame, ext: pd.DataFrame | None, cap_start: float) -> tuple[np.ndarray, dict]:
    """Origin-only eligibility (panel.eligibility_mask rules + no UMA proposal). Returns mask and exclusion counts."""
    bid, ask = rows["best_bid"].to_numpy(float), rows["best_ask"].to_numpy(float)
    spread = rows["spread"].to_numpy(float)
    spread = np.where(np.isnan(spread), ask - bid, spread)
    mid = (bid + ask) / 2.0
    end = _epoch_col(rows["end_date"])
    closed, active = _truthy(rows["closed"]), _truthy(rows["active"])
    binary = rows["binary"].to_numpy() == 1
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (bid < ask) & (ask < 1)
        base = binary & ~closed & active & two
        quote_ok = base & (spread <= C.SPREAD_MAX) & (mid >= C.MID_LO) & (mid <= C.MID_HI)
        live = quote_ok & (np.isnan(end) | (end > cap_start))
    if ext is not None:
        prop = np.asarray(has_proposal(ext["uma_resolution_statuses"].reindex(rows["market_id"].to_numpy())))
    else:
        prop = np.zeros(len(rows), bool)
    ok = live & ~prop
    counts = {"rows": int(len(rows)), "binary": int(binary.sum()), "open_two_sided": int(base.sum()),
              "quote_filter": int(quote_ok.sum()), "end_after_origin": int(live.sum()),
              "excluded_uma_proposal": int((live & prop).sum()), "eligible": int(ok.sum()),
              "ext_present": ext is not None}
    return ok, counts


# ---------------------------------------------------------------------------------------------- families


def base_features(o: pd.DataFrame, ext: pd.DataFrame | None, cap_start: float, slot: int,
                  mids: MidCache) -> pd.DataFrame:
    bid, ask = o["best_bid"].to_numpy(float), o["best_ask"].to_numpy(float)
    mid = (bid + ask) / 2.0
    spread = o["spread"].to_numpy(float)
    spread = np.where(np.isnan(spread), ask - bid, spread)
    t_row = _epoch_col(o["received_utc"])
    end = _epoch_col(o["end_date"])
    ids = o["market_id"].to_numpy(np.int64)
    ev = pd.to_numeric(o["event_id"], errors="coerce").fillna(-1).to_numpy(np.int64)
    f = pd.DataFrame({"market_id": ids, "event_id": ev})
    if ext is not None:
        e = ext.reindex(ids)
        f["category"] = e["fee_category"].fillna("unknown").astype(str).to_numpy()
        created = _epoch_col(e["created_at"])
        tick = e["order_price_min_tick_size"].to_numpy(float)
    else:
        f["category"] = "unknown"
        created = np.full(len(o), np.nan)
        tick = np.full(len(o), np.nan)
    f["t_row"] = t_row
    f["end_ts"] = end
    liq = o["liquidity"].to_numpy(float)
    vol = o["volume24hr"].to_numpy(float)
    ltp = o["last_trade_price"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["ms_mid"] = mid
        f["ms_spread"] = spread
        f["ms_log_liq"] = np.log1p(np.clip(liq, 0, None))
        f["ms_log_vol24"] = np.log1p(np.clip(vol, 0, None))
        f["ms_hours_to_end"] = np.clip((end - t_row) / 3600.0, 0, None)
        f["ms_ltp_minus_mid"] = ltp - mid
        f["ms_stale_s"] = np.clip(t_row - _epoch_col(o["updated_at"]), 0, None)
        f["ms_age_h"] = np.clip((t_row - created) / 3600.0, 0, None)
    f["ms_tick"] = tick
    f["ms_neg_risk"] = o["neg_risk"].to_numpy(float)
    for src in ("chg_1h", "chg_1d", "chg_1w"):
        f[f"mo_{src}"] = o[src].to_numpy(float)
    # own look-backs from earlier quotes files (slots strictly before this one)
    hist = []
    for j in range(slot - LOOKBACK_SLOTS, slot):
        s = mids.get(j)
        hist.append(np.full(len(ids), np.nan) if s is None else s.reindex(ids).to_numpy(float))
    hist.append(mid)
    H = np.column_stack(hist)  # columns: slot-12 .. slot-1, slot
    f["mo_d2h"] = mid - H[:, -2]
    f["mo_d6h"] = mid - H[:, -4]
    f["mo_d24h"] = mid - H[:, 0]
    d = np.diff(H, axis=1)
    n = np.isfinite(d).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = np.sqrt(np.nansum(np.where(np.isfinite(d), d, 0.0) ** 2, axis=1) / n)
    f["ms_rv24"] = np.where(n >= 3, rv, np.nan)
    f["ms_nobs24"] = np.isfinite(H[:, :-1]).sum(axis=1).astype(float)
    return f


def _nan_frame(n: int, cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: np.full(n, np.nan) for c in cols})


def find_sample(paths: S.Paths, cap_id: str, state: dict) -> Path | None:
    """The complete active-frame trade sample drawn from this capture (manifest heads cached in ``state``)."""
    cache = state.setdefault("samples", {})
    for mp in sorted(Path(paths.samples).glob("*/manifest.json")):
        sid = mp.parent.name
        if sid in cache:
            continue
        m = S._manifest_head(mp)
        if not m or m.get("state") != "complete":
            continue
        cache[sid] = {"snapshot_id": m.get("snapshot_id"), "frame": m.get("frame")}
    for sid, m in sorted(cache.items()):
        d = Path(paths.samples) / sid
        if m.get("snapshot_id") == cap_id and m.get("frame") == "active" and (d / "features.csv.gz").exists():
            return d
    return None


def flow_features(sample_dir: Path | None, f: pd.DataFrame, o: pd.DataFrame) -> pd.DataFrame:
    cols = FAMILY_COLUMNS["flow"]
    out = _nan_frame(len(f), cols)
    if sample_dir is None:
        return out
    t = pacsv.read_csv(Path(sample_dir) / "features.csv.gz", convert_options=pacsv.ConvertOptions(
        include_columns=["market_id", "status", "n_trades_1h", "volume_1h", "notional_1h", "signed_volume_1h",
                         "max_trade_size_1h", "time_since_last_trade_s"],
        column_types={"market_id": pa.int64(), "status": pa.string()})).to_pandas()
    t = t[t["status"] == "ok"].drop_duplicates("market_id").set_index("market_id").reindex(f["market_id"].to_numpy())
    sampled = t["status"].notna().to_numpy()
    out["fl_sampled"] = sampled.astype(float)
    liq = np.clip(o["liquidity"].to_numpy(float), 0, None)
    with np.errstate(invalid="ignore", divide="ignore"):
        vol = t["volume_1h"].to_numpy(float)
        out["fl_n1h"] = np.log1p(t["n_trades_1h"].to_numpy(float))
        out["fl_notional1h"] = np.log1p(np.clip(t["notional_1h"].to_numpy(float), 0, None))
        out["fl_signed"] = np.where(sampled, np.where(vol > 0, t["signed_volume_1h"].to_numpy(float) / vol, 0.0), np.nan)
        out["fl_maxliq"] = np.log1p(np.clip(t["max_trade_size_1h"].to_numpy(float) * f["ms_mid"].to_numpy(float), 0, None)) - np.log1p(liq)
        out["fl_since_last"] = np.log1p(np.clip(t["time_since_last_trade_s"].to_numpy(float), 0, None))
    return out


def wallet_features(sample_dir: Path | None, f: pd.DataFrame) -> pd.DataFrame:
    """Distinct wallets, top-1 notional share and HHI over trades in [row receipt - 24 h, row receipt)."""
    cols = FAMILY_COLUMNS["wallet"]
    out = _nan_frame(len(f), cols)
    if sample_dir is None:
        return out
    wp, mp = Path(sample_dir) / "wallets.csv.gz", Path(sample_dir) / "wallets_manifest.json"
    try:
        man = json.loads(mp.read_text())
    except (OSError, ValueError):
        return out
    if not wp.exists() or man.get("sidecar_status") != "complete":
        return out
    fe = pacsv.read_csv(Path(sample_dir) / "features.csv.gz", convert_options=pacsv.ConvertOptions(
        include_columns=["market_id", "status", "origin_utc"],
        column_types={"market_id": pa.int64(), "status": pa.string(), "origin_utc": TS})).to_pandas()
    fe = fe[fe["status"] == "ok"].drop_duplicates("market_id")
    origin = pd.Series(_epoch_col(fe["origin_utc"]), index=fe["market_id"].to_numpy(np.int64))
    w = pacsv.read_csv(wp, convert_options=pacsv.ConvertOptions(
        include_columns=["market_id", "ts", "size", "price", "wallet_hash"],
        column_types={"market_id": pa.int64(), "ts": pa.float64(), "size": pa.float64(), "price": pa.float64(),
                      "wallet_hash": pa.dictionary(pa.int32(), pa.string())})).to_pandas()
    t0 = origin.reindex(w["market_id"].to_numpy()).to_numpy(float)
    ts = w["ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        keep = (ts < t0) & (ts >= t0 - 86400.0)
    w = w[keep]
    w = w.assign(notional=w["size"].to_numpy(float) * w["price"].to_numpy(float),
                 wcode=w["wallet_hash"].cat.codes.to_numpy())
    g = w.groupby(["market_id", "wcode"], sort=False)["notional"].sum().reset_index()
    tot = g.groupby("market_id")["notional"].transform("sum").to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        g["share"] = np.where(tot > 0, g["notional"].to_numpy(float) / tot, np.nan)
    agg = g.groupby("market_id").agg(n=("wcode", "size"), top1=("share", "max"),
                                     hhi=("share", lambda s: float(np.nansum(np.square(s)))))
    ids = f["market_id"].to_numpy(np.int64)
    has = origin.reindex(ids).notna().to_numpy()
    a = agg.reindex(ids)
    out["wl_has"] = has.astype(float)
    out["wl_n24"] = np.where(has, np.log1p(a["n"].fillna(0).to_numpy(float)), np.nan)
    out["wl_top1"] = np.where(has, a["top1"].to_numpy(float), np.nan)
    out["wl_hhi"] = np.where(has, a["hhi"].to_numpy(float), np.nan)
    return out


def find_sweep(paths: S.Paths, cap_id: str, state: dict) -> Path | None:
    """The first complete book sweep of this capture's pass (lowest series_index)."""
    cache = state.setdefault("sweeps", {})
    for mp in sorted(Path(paths.sweeps).glob("*/manifest.json")):
        sid = mp.parent.name
        if sid in cache:
            continue
        m = S._manifest_head(mp)
        if not m or m.get("state") != "complete":
            continue
        cache[sid] = {"snapshot_id": m.get("snapshot_id"), "series_index": m.get("series_index") or 0}
    best = None
    for sid, m in cache.items():
        d = Path(paths.sweeps) / sid
        if m.get("snapshot_id") == cap_id and (d / "rows.csv.gz").exists():
            if best is None or (m["series_index"], sid) < best[0]:
                best = ((m["series_index"], sid), d)
    return None if best is None else best[1]


def book_features(sweep_dir: Path | None, f: pd.DataFrame) -> pd.DataFrame:
    cols = FAMILY_COLUMNS["book"]
    out = _nan_frame(len(f), cols)
    if sweep_dir is None:
        return out
    num = ["best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c",
           "depth_ask_5c", "n_bid_levels", "n_ask_levels", "book_timestamp"]
    t = pacsv.read_csv(Path(sweep_dir) / "rows.csv.gz", convert_options=pacsv.ConvertOptions(
        include_columns=["market_id", "state", "batch_receipt_utc", *num],
        column_types={"market_id": pa.int64(), "state": pa.string(), "batch_receipt_utc": TS,
                      **{c: pa.float64() for c in num}})).to_pandas()
    t = t[t["state"] == "two_sided"].drop_duplicates("market_id").set_index("market_id")
    b = t.reindex(f["market_id"].to_numpy())
    has = b["state"].notna().to_numpy()
    out["bk_has"] = has.astype(float)

    def imb(x, y):
        with np.errstate(invalid="ignore", divide="ignore"):
            s = x + y
            return np.where(s > 0, (x - y) / s, np.nan)

    bs, as_ = b["bid_size_1"].to_numpy(float), b["ask_size_1"].to_numpy(float)
    bb, ba = b["best_bid"].to_numpy(float), b["best_ask"].to_numpy(float)
    out["bk_imb1"] = imb(bs, as_)
    out["bk_imb1c"] = imb(b["depth_bid_1c"].to_numpy(float), b["depth_ask_1c"].to_numpy(float))
    out["bk_imb5c"] = imb(b["depth_bid_5c"].to_numpy(float), b["depth_ask_5c"].to_numpy(float))
    with np.errstate(invalid="ignore", divide="ignore"):
        out["bk_depth5c"] = np.log1p(np.clip(b["depth_bid_5c"].to_numpy(float) + b["depth_ask_5c"].to_numpy(float), 0, None))
        micro = (ba * bs + bb * as_) / (bs + as_)
        out["bk_micro"] = micro - (bb + ba) / 2.0  # relative to the SWEEP mid (no sweep-Gamma gap)
        out["bk_age_s"] = np.clip(_epoch_col(b["batch_receipt_utc"]) - b["book_timestamp"].to_numpy(float) / 1000.0, 0, None)
        out["bk_levels"] = np.log1p(b["n_bid_levels"].to_numpy(float) + b["n_ask_levels"].to_numpy(float))
    for c in cols[1:]:
        out[c] = np.where(has, out[c].to_numpy(float), np.nan)
    return out


def _xv_files(xv_root: Path, t0: float) -> list[Path]:
    days = sorted({S.day_of(t0 - 3600.0).replace("-", ""), S.day_of(t0).replace("-", "")})
    out = []
    for d in days:
        for name in (f"{d}.jsonl", f"{d}.jsonl.gz"):
            p = Path(xv_root) / name
            if p.exists():
                out.append(p)
    return out


def xvenue_features(xv_root: Path, cap_start: float, f: pd.DataFrame, max_age_s: float = 1800.0) -> tuple[pd.DataFrame, str | None]:
    """Last Kalshi/Polymarket pair quote received before the capture start (cross_venue_live quotes only)."""
    cols = FAMILY_COLUMNS["xvenue"]
    out = _nan_frame(len(f), cols)
    files = _xv_files(xv_root, cap_start)
    if not files:
        return out, None
    last: dict[int, dict] = {}
    lo = cap_start - max_age_s - 600.0
    for p in files:
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                if not line.startswith('{"t":'):
                    continue
                try:
                    t = float(line[5:line.index(",", 5)])
                except ValueError:
                    continue
                if t < lo or t >= cap_start:
                    continue
                try:
                    q = json.loads(line)
                except ValueError:
                    continue
                kr, pr = q.get("k_recv"), q.get("p_recv")
                if not isinstance(kr, (int, float)) or kr >= cap_start or (isinstance(pr, (int, float)) and pr >= cap_start):
                    continue
                try:
                    mid = int(str(q.get("pid", "")).rsplit("|", 1)[1])
                except (IndexError, ValueError):
                    continue
                if mid not in last or kr >= last[mid]["k_recv"]:
                    last[mid] = q
    out["xv_has"] = 0.0
    if not last:
        return out, ",".join(p.name for p in files)
    ids = f["market_id"].to_numpy(np.int64)
    pos = {m: i for i, m in enumerate(ids)}
    gm = f["ms_mid"].to_numpy(float)
    for mid, q in last.items():
        i = pos.get(mid)
        kb, ka, kr = q.get("k_bid"), q.get("k_ask"), q.get("k_recv")
        if i is None or not all(isinstance(v, (int, float)) for v in (kb, ka)):
            continue
        age = cap_start - kr
        if age > max_age_s or not (0 <= kb < ka <= 1):
            continue
        out.loc[i, "xv_has"] = 1.0
        out.loc[i, "xv_gap"] = (kb + ka) / 2.0 - gm[i]
        out.loc[i, "xv_kspread"] = ka - kb
        out.loc[i, "xv_age_s"] = age
    return out, ",".join(p.name for p in files)


# ---------------------------------------------------------------------------------------------- one capture


def build_capture(paths: S.Paths, cap: dict, index: dict[int, dict], mids: MidCache, state: dict) -> dict:
    """Write quotes, features and meta for one capture (each write-once). Returns the meta dict."""
    cid, slot, start = cap["id"], cap["slot"], cap["start"]
    rows = read_rows(cap["dir"])
    ext = read_ext(cap["dir"])
    q = quotes_frame(rows, start)
    ok, counts = eligibility(rows, ext, start)
    o = rows[ok].reset_index(drop=True)
    f = base_features(o, ext, start, slot, mids)
    sample = find_sample(paths, cid, state)
    sweep = find_sweep(paths, cid, state)
    fl = flow_features(sample, f, o)
    wl = wallet_features(sample, f)
    bk = book_features(sweep, f)
    xv, xv_src = xvenue_features(paths.xv_quotes, start, f)
    feats = pd.concat([f, fl, bk, xv, wl], axis=1)
    for c in ALL_FEATURES:
        feats[c] = feats[c].astype(np.float32)
    feats = feats[KEY_COLUMNS + ALL_FEATURES]
    sources = {"flow": None if sample is None else sample.name,
               "wallet": None if sample is None or not np.isfinite(wl["wl_has"].to_numpy(float)).any() else sample.name,
               "book": None if sweep is None else sweep.name, "xvenue": xv_src}
    md = {"capture_id": cid, "slot": slot, "features_version": C.FEATURES_VERSION}
    S.write_once_parquet(paths.quotes(cid), q, md)
    S.write_once_parquet(paths.features(cid), feats, md)
    meta = {"capture_id": cid, "slot": slot, "slot_utc": S.iso_s(S.slot_time(slot)), "started_utc": S.iso(start),
            "finished_utc": S.iso(cap["finished"]) if math.isfinite(cap.get("finished", math.nan)) else None,
            "features_version": C.FEATURES_VERSION, "engine_version": C.ENGINE_VERSION, "counts": counts,
            "n_quotes": int(len(q)), "n_quotes_two_sided": int((q["st"] == 0).sum()), "n_features": int(len(feats)),
            "sources": sources, "coverage": {fam: float(np.nanmean(feats[FAMILY_COLUMNS[fam][0]].to_numpy(float) > 0))
                                             if np.isfinite(feats[FAMILY_COLUMNS[fam][0]].to_numpy(float)).any() else None
                                             for fam in SOURCE_FAMILIES},
            "quotes_sha256": S.sha256_file(paths.quotes(cid)), "features_sha256": S.sha256_file(paths.features(cid)),
            "written_utc": S.iso(S.now_ts()), "code_commit": S.git_commit()}
    S.write_once_json(paths.meta(cid), meta)
    return meta


def run_features(paths: S.Paths, max_items: int = 4, now: float | None = None) -> dict:
    """Process new complete captures oldest first (at most ``max_items``)."""
    state = S.load_state(paths)
    caps = S.discover_captures(paths, state)
    index = S.load_index(paths)
    done_ids = {m["capture_id"] for m in index.values()}
    todo = [c for c in caps if c["id"] not in done_ids and c["slot"] not in index]
    mids = MidCache(paths, index)
    written, skipped = [], 0
    for cap in todo:
        if len(written) >= max_items:
            break
        if not (cap["dir"] / "rows.csv.gz").exists():
            # rows archived and deleted: the capture is skipped (missing stays missing) without using the budget,
            # so a backlog of archived captures can never starve the newest ones
            skipped += 1
            continue
        meta = build_capture(paths, cap, index, mids, state)
        index[cap["slot"]] = meta
        written.append({"capture_id": cap["id"], "n_features": meta["n_features"], "sources": meta["sources"]})
    S.save_state(paths, state)
    unbuildable = sum(1 for c in todo if not (c["dir"] / "rows.csv.gz").exists())
    return {"pending": max(0, len(todo) - len(written) - unbuildable), "skipped_no_rows": unbuildable,
            "written": written}
