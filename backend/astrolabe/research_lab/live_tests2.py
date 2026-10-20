# ruff: noqa: E501
"""LIVE prospective tests E012-E014 (docs/research_lab/LIVE_TESTS_2.md; DRAFT until the ledger registration).

Research tooling only: read-only on the collector's streams, never trades, no network requests. Everything is built
from data the Oracle collector already writes every 2 hours:

* complete-universe snapshots (``research_lab/snapshots/<capture>/rows.csv.gz`` and ``rows_ext.csv.gz``);
* the active-frame trade samples (``research_lab/trade_samples/<sample>/{plan,manifest}.json``, ``features.csv.gz``,
  ``trades.csv.gz``), one per pass, drawn from that pass's snapshot.

Outputs (``research_lab/live_tests2/``; every data file is WRITE-ONCE, written atomically, never edited):

* ``series/<capture>.csv.gz`` - slim two-sided quotes (market, event, receipt time, bid, ask, spread) of every open
  binary market of each complete capture from ``REGISTERED_UTC - 26 h`` on. Feature look-backs (24 h change, 2 h
  previous change, 24 h realised volatility) and every outcome mid come from these files, so the analysis does not
  depend on snapshot retention on the host.
* ``status/<capture>.csv.gz`` - written with the series file: every binary market of the listing that is not in the
  series, with its status (closed / inactive / one_sided); a market in neither file was absent. Outcome files carry
  the detailed reason (``unavailable_closed`` ...), so attrition by resolution can be measured (section 1.3).
* ``e012/frozen/<capture>.csv.gz`` - E012 origin lines (6-hourly grid captures), written before the 24 h target exists.
* ``flow/frozen/<sample>.csv.gz`` - E013 and E014 origin lines (one per trade-sample market), written before the 2 h
  and 6 h targets exist; E014's two frozen E007 predictions are in the line.
* ``e012/outcomes/<capture>.csv.gz`` and ``flow/outcomes/<sample>.csv.gz`` - target quotes copied from the target
  capture's series file once it exists (or ``missing_capture`` once it is certainly missing). Never imputed.
* ``passes.jsonl`` - one line per file written or refused (append-only), ``state.json`` - processed-id cache only.

Causality: every origin feature uses only the origin capture and earlier captures (or trades strictly before the
origin row's receipt time). A frozen file whose write time is not strictly before the start of its target capture is
excluded at analysis (``late``) and counted. Every frozen line carries ``spec_sha`` and ``code_sha`` (normalised
sha256 of this module); the analysis keeps only lines whose both values equal the registered pins. ``analyze`` runs the registered tests once, after
``ANALYSIS_NOT_BEFORE``; ``ops_stats`` only counts files, lines and statuses and never reads a mid.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import economics, forecast, panel, trade_sample

VERSION = "live-tests2-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = ROOT / "data-dumps" / "research_lab" / "trade_samples"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests2"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests2_v1.json"
SPEC_SHA256 = None  # pinned at registration (LIVE_TESTS_2.md); None = DRAFT, every line is prospective_unregistered

REGISTERED_UTC = "2026-10-22T00:00:00Z"
END_UTC = "2026-11-12T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-11-13T12:00:00Z"
TEMPFAIL = 75
DISK_CAP_BYTES = int(1.5e9)
GRID_S = 7200.0
SLOT_TOL_S = 1800.0
SERIES_LOOKBACK_S = 26 * 3600.0
MISSING_AFTER_S = 3 * 3600.0  # a target capture absent 3 h after its slot is "missing_capture"
ROLE_CONF, ROLE_UNREG = "prospective_confirmation", "prospective_unregistered"
CODE_FILES = ("live_tests2.py", "live_tests2_analysis.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)

SNAP_COLS = ["market_id", "event_id", "clob_token_id_0", "received_utc", "closed", "active", "binary", "best_bid", "best_ask",
             "spread", "last_trade_price", "chg_1h", "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date"]
EXT_COLS = ["market_id", "fee_category", "fees_enabled", "fee_schedule"]
SERIES_COLS = ["market_id", "event_id", "t_row", "bid", "ask", "spread", "end_ts"]


# --- small utilities ----------------------------------------------------------------------------------------------


def epoch(v) -> float:
    try:
        return float(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return math.nan


def iso(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def now_ts() -> float:
    return datetime.now(UTC).timestamp()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=15)
        return out.stdout.strip()[:12] or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LIVE_TESTS_2.md section 1.1): the spec JSON
    pins the code hashes and the code pins the spec hash, so the pin line itself is kept outside the code hash."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    """Normalised sha256 of the collector and analysis modules as present on disk."""
    here = Path(__file__).resolve().parent
    return {n: code_sha256(here / n) for n in CODE_FILES}


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"live_tests2 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"] = got
    spec["_pinned"] = sha is not None
    return spec


def _json(o):
    if isinstance(o, (np.floating, np.integer)):
        v = o.item()
        return None if isinstance(v, float) and not math.isfinite(v) else v
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def append_jsonl(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, default=_json) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def write_once_csv(path: Path, df: pd.DataFrame) -> bool:
    """Write ``df`` to ``path`` (gzip CSV) only if ``path`` does not exist. Atomic (tmp + hard link). False if it
    already existed (the existing file is never touched)."""
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_csv(tmp, index=False, compression="gzip", float_format="%.17g")
    with open(tmp, "rb") as fh:
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def du_bytes(path: Path) -> int:
    """``du -sk`` (fast) with a Python walk as the fallback."""
    try:
        out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=300)
        return int(out.stdout.split()[0]) * 1024
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return dir_bytes(path)


def dir_bytes(path: Path) -> int:
    tot = 0
    for p in Path(path).rglob("*"):
        if p.is_file():
            tot += p.stat().st_size
    return tot


# --- grid, windows and captures -------------------------------------------------------------------------------------


def grid0(spec: dict) -> float:
    return epoch(spec["grid"]["grid0_utc"])


def slot_of(t: float, spec: dict) -> int | None:
    """2-hour collector slot of a capture start (None if the start is more than SLOT_TOL_S off the grid)."""
    g0 = grid0(spec)
    k = int(round((t - g0) / GRID_S))
    return k if abs(t - (g0 + k * GRID_S)) <= SLOT_TOL_S else None


def slot_time(k: int, spec: dict) -> float:
    return grid0(spec) + k * GRID_S


def role_of(capture_start: float, registered_utc: str, end_utc: str, pinned: bool) -> str:
    ok = pinned and epoch(registered_utc) <= capture_start < epoch(end_utc)
    return ROLE_CONF if ok else ROLE_UNREG


def _manifest_head(path: Path) -> dict:
    m = json.loads(Path(path).read_text())
    return {k: m.get(k) for k in ("state", "started_utc", "capture_id", "sample_id", "snapshot_id", "frame")}


class State:
    """Processed-id cache (``state.json``). Only a speed-up: write-once files are the ground truth."""

    def __init__(self, root: Path) -> None:
        self.path = Path(root) / "state.json"
        self.d = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.d.setdefault("captures", {})  # capture_id -> {"start": epoch, "slot": k}
        self.d.setdefault("samples", {})  # sample_id -> {"snapshot_id": .., "frame": ..}
        self.d.setdefault("not_complete", [])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, sort_keys=True))
        os.replace(tmp, self.path)


def scan_captures(snapshot_root: Path, st: State, spec: dict) -> dict[int, dict]:
    """Complete captures by slot ({slot: {"id", "start", "dir"}}); the first complete capture of a slot wins."""
    for d in sorted(Path(snapshot_root).glob("*/manifest.json")):
        cid = d.parent.name
        if cid in st.d["captures"]:
            continue
        try:
            m = _manifest_head(d)
        except (OSError, ValueError):
            continue
        if m.get("state") != "complete":
            continue
        t = epoch(m["started_utc"])
        st.d["captures"][cid] = {"start": t, "slot": slot_of(t, spec)}
    by_slot: dict[int, dict] = {}
    for cid, c in sorted(st.d["captures"].items(), key=lambda kv: kv[1]["start"]):
        if c["slot"] is None or not (Path(snapshot_root) / cid).exists():
            continue
        by_slot.setdefault(c["slot"], {"id": cid, "start": c["start"], "dir": Path(snapshot_root) / cid})
    return by_slot


def scan_samples(sample_root: Path, st: State) -> dict[str, dict]:
    """Complete active-frame trade samples ({sample_id: {"snapshot_id", "dir"}})."""
    out = {}
    for d in sorted(Path(sample_root).glob("*/manifest.json")):
        sid = d.parent.name
        if sid not in st.d["samples"]:
            try:
                m = _manifest_head(d)
            except (OSError, ValueError):
                continue
            if m.get("state") != "complete" or not (d.parent / "features.csv.gz").exists():
                continue
            st.d["samples"][sid] = {"snapshot_id": m.get("snapshot_id"), "frame": m.get("frame")}
        s = st.d["samples"][sid]
        if s.get("frame") == "active":
            out[sid] = {"snapshot_id": s["snapshot_id"], "dir": d.parent}
    return out


def is_e012_origin(start: float, spec: dict) -> bool:
    """E012 grid: the capture whose start lies in [HH:00, HH:00 + 2 h) UTC for HH in the declared hours."""
    dt = datetime.fromtimestamp(start, UTC)
    return any(dt.hour == h or dt.hour == h + 1 for h in spec["e012"]["origin_hours_utc"])


# --- capture readers ------------------------------------------------------------------------------------------------


def load_rows(cap_dir: Path, token: bool = False) -> pd.DataFrame:
    """Origin-side snapshot columns (first row per market). Repeated strings are categorical to keep RSS low."""
    cols = SNAP_COLS if token else [c for c in SNAP_COLS if c != "clob_token_id_0"]
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=cols,
                       dtype={"market_id": str, "event_id": str, "clob_token_id_0": str, "received_utc": "category",
                              "end_date": "category"})
    rows = rows.drop_duplicates("market_id").reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows


def load_fee_rates(cap_dir: Path, market_ids: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """(taker fee rate, exponent) per market from the capture's extension sidecar (``economics.fee_spec`` /
    ``resolve_rate``, policy max_if_unknown). An absent sidecar row resolves as unknown (max docs rate)."""
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if p.exists():
        ext = pd.read_csv(p, usecols=EXT_COLS, dtype={"market_id": str}).drop_duplicates("market_id")
        ext = ext.set_index("market_id").reindex(market_ids.astype(str))
    else:
        ext = pd.DataFrame(index=market_ids.astype(str), columns=EXT_COLS[1:])
    key = ext[["fee_schedule", "fees_enabled", "fee_category"]].astype(str)
    cache: dict = {}
    rate, expo = np.empty(len(key)), np.empty(len(key))
    for i, k in enumerate(key.itertuples(index=False)):
        k = tuple(k)
        if k not in cache:
            fs, fe, fc = (None if v in ("nan", "None", "") else v for v in k)
            spec = economics.fee_spec(fs, fe, fc)
            cache[k] = (economics.resolve_rate(spec, "max_if_unknown"), spec.exponent)
        rate[i], expo[i] = cache[k]
    return rate, expo


def series_frame(rows: pd.DataFrame) -> pd.DataFrame:
    """Two-sided quotes (``panel.target_valid``) of open binary markets: the slim series of one capture."""
    b = rows[rows["binary"] == 1]
    ok = panel.target_valid(b) & b["active"].astype(str).str.lower().eq("true").to_numpy()
    s = b[ok]
    spread = s["spread"].to_numpy(float)
    bid, ask = s["best_bid"].to_numpy(float), s["best_ask"].to_numpy(float)
    return pd.DataFrame({"market_id": s["market_id"].astype(str).to_numpy(), "event_id": s["event_id"].astype(str),
                         "t_row": s["t_row"].to_numpy(float), "bid": bid, "ask": ask,
                         "spread": np.where(np.isnan(spread), ask - bid, spread),
                         "end_ts": panel._epoch(s["end_date"])})


def status_frame(rows: pd.DataFrame) -> pd.DataFrame:
    """Per-capture status of every binary market of the listing that is NOT in the series (challenger R1 finding 3):
    ``closed`` (closed flag true), ``inactive`` (not closed, active false) or ``one_sided`` (open and active but not
    two-sided). A market in neither the series nor this file was absent from the listing (``absent``)."""
    b = rows[rows["binary"] == 1]
    closed = b["closed"].astype(str).str.lower().eq("true").to_numpy()
    active = b["active"].astype(str).str.lower().eq("true").to_numpy()
    present = panel.target_valid(b) & active
    st = np.where(closed, "closed", np.where(~active, "inactive", "one_sided"))
    return pd.DataFrame({"market_id": b["market_id"].astype(str).to_numpy()[~present], "st": st[~present]})


def read_status(root: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / "status" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "st": str}).drop_duplicates("market_id").set_index("market_id")


def read_series(root: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / "series" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "event_id": str}).set_index("market_id")


def tight(bid, ask, spread, spec: dict) -> np.ndarray:
    e = spec["eligibility"]
    bid, ask, spread = (np.asarray(v, float) for v in (bid, ask, spread))
    mid = (bid + ask) / 2.0
    with np.errstate(invalid="ignore"):
        return (np.isfinite(mid) & (bid > 0) & (bid < ask) & (ask < 1) & (spread <= e["spread_max"])
                & (mid >= e["mid_lo"]) & (mid <= e["mid_hi"]))


def _lookup(ser: pd.DataFrame | None, mids: pd.Series, col: str) -> np.ndarray:
    if ser is None:
        return np.full(len(mids), np.nan)
    return ser[col].reindex(mids.astype(str)).to_numpy(float)


def grid_rv(root: Path, by_slot: dict[int, dict], k: int, market_ids: pd.Series, steps: int, min_diffs: int,
            cache: dict | None = None) -> np.ndarray:
    """rms of consecutive-slot two-sided mid differences over slots k-steps .. k (series files); NaN with fewer than
    ``min_diffs`` valid differences. Uses only the origin slot and earlier slots."""
    mids = []
    for j in range(k - steps, k + 1):
        cid = by_slot.get(j, {}).get("id")
        if cache is not None and cid in cache:
            m = cache[cid]
        else:
            ser = read_series(root, cid)
            m = None if ser is None else (ser["bid"] + ser["ask"]) / 2.0
            if cache is not None and cid is not None:
                cache[cid] = m
                while len(cache) > steps + 4:  # bounded: only the most recent slots are reused
                    cache.pop(next(iter(cache)))
        if m is None:
            mids.append(np.full(len(market_ids), np.nan))
        else:
            mids.append(m.reindex(market_ids.astype(str)).to_numpy(float))
    d = np.diff(np.column_stack(mids), axis=1)
    n = np.isfinite(d).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = np.sqrt(np.nansum(np.where(np.isfinite(d), d, 0.0) ** 2, axis=1) / n)
    return np.where(n >= min_diffs, rv, np.nan)


# --- freezers -----------------------------------------------------------------------------------------------------


def _base_controls(o: pd.DataFrame, feats: pd.DataFrame) -> dict:
    mid = feats["mid"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        logit = np.log(mid / (1.0 - mid))
    return {"logit_mid": logit, "abs_dev": np.abs(mid - 0.5), "chg_1h": feats["chg_1h"].to_numpy(),
            "chg_1h_missing": feats["chg_1h_missing"].to_numpy(), "chg_1d_g": feats["chg_1d"].to_numpy(),
            "chg_1d_missing": feats["chg_1d_missing"].to_numpy(), "chg_1w": feats["chg_1w"].to_numpy(),
            "chg_1w_missing": feats["chg_1w_missing"].to_numpy()}


def freeze_e012(cap: dict, k: int, by_slot: dict, root: Path, spec: dict, role: str, commit: str) -> pd.DataFrame:
    """E012 origin lines for one grid capture: eligible at i (``panel.eligibility_mask``, end > i + end margin)."""
    e = spec["e012"]
    rows = load_rows(cap["dir"])
    b = rows[rows["binary"] == 1].reset_index(drop=True)
    ok = panel.eligibility_mask(b, cap["start"] + e["end_margin_h"] * 3600.0)
    o = b[ok].reset_index(drop=True)
    feats = panel.compute_features(o, o["t_row"].to_numpy(float))
    mids = o["market_id"].astype(str)
    ser_h = read_series(root, by_slot.get(k - e["horizon_slots"], {}).get("id"))
    ser_p = read_series(root, by_slot.get(k - 1, {}).get("id"))
    ser_s = read_series(root, by_slot.get(k - e["skip_slots"], {}).get("id"))
    bid_h, ask_h, spr_h = (_lookup(ser_h, mids, c) for c in ("bid", "ask", "spread"))
    tight_h = tight(bid_h, ask_h, spr_h, spec)
    mid_h = np.where(tight_h, (bid_h + ask_h) / 2.0, np.nan)
    mid_p = (_lookup(ser_p, mids, "bid") + _lookup(ser_p, mids, "ask")) / 2.0
    # 6 h skip slot (challenger R1 finding 2): x_skip6 = mid_{i-3} - mid_h never contains mid_i
    bid_s, ask_s, spr_s = (_lookup(ser_s, mids, c) for c in ("bid", "ask", "spread"))
    tight_s = tight(bid_s, ask_s, spr_s, spec)
    mid_s = np.where(tight_s, (bid_s + ask_s) / 2.0, np.nan)
    mid = feats["mid"].to_numpy(float)
    L = np.log1p(np.nan_to_num(o["volume24hr"].to_numpy(float), nan=0.0).clip(min=0))
    zc = e["zL"]
    df = pd.DataFrame({
        "capture_id": cap["id"], "capture_t": cap["start"], "slot": k, "market_id": mids.to_numpy(),
        "event_id": o["event_id"].astype(str).to_numpy(), "t_row": o["t_row"].to_numpy(float), "role": role,
        "bid_i": o["best_bid"].to_numpy(float), "ask_i": o["best_ask"].to_numpy(float), "mid_i": mid,
        "spread_i": feats["spread"].to_numpy(float), "h_capture_id": by_slot.get(k - e["horizon_slots"], {}).get("id"),
        "tight_h": tight_h.astype(int), "mid_h": mid_h, "x": mid - mid_h,
        "tight_s3": tight_s.astype(int), "mid_s3": mid_s, "x_skip6": mid_s - mid_h,
        "dprev": mid - mid_p, "dprev_missing": np.isnan(mid_p).astype(int),
        "L": L, "zL": (L - zc["centre"]) / zc["scale"],
        **_base_controls(o, feats),
        "hte_h": (panel._epoch(o["end_date"]) - o["t_row"].to_numpy(float)) / 3600.0,
    })
    df["fee_rate"], df["fee_exp"] = load_fee_rates(cap["dir"], mids)
    df["frozen_utc"] = iso(now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"] = commit, spec["_sha256"][:16], collector_sha()
    return df


def collector_sha() -> str:
    """First 16 hex digits of the normalised sha256 of this module, written into every frozen line (section 1.1)."""
    return code_sha256(Path(__file__).resolve())[:16]


def _truthy(v: pd.Series) -> np.ndarray:
    return v.astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy()


def _signs(tr: pd.DataFrame, token0: pd.Series | None) -> np.ndarray:
    """Dev / ``trade_sample._sign`` convention on outcome 0; outcome from ``outcome_index``, else asset == token 0
    (``token0``: market_id -> clob_token_id_0 of the origin capture); neither -> 0 (unsigned, excluded)."""
    oi = pd.to_numeric(tr["outcome_index"], errors="coerce").to_numpy(float)
    if token0 is not None:
        t0 = tr["market_id"].astype(str).map(token0).astype(str).to_numpy()
        fb = np.where(tr["asset"].astype(str).to_numpy() == t0, 0.0, np.nan)
        oi = np.where(np.isin(oi, (0.0, 1.0)), oi, fb)
    side = tr["side"].astype(str).to_numpy()
    s = np.where(side == "BUY", 1.0, np.where(side == "SELL", -1.0, 0.0))
    return np.where(oi == 0, s, np.where(oi == 1, -s, 0.0))


def freeze_flow(sample: dict, cap: dict, k: int, by_slot: dict, root: Path, spec: dict, role: str, commit: str,
                cache: dict | None = None) -> pd.DataFrame:
    """E013/E014 origin lines for one active trade sample (one line per sampled market with status ok)."""
    f = spec["flow"]
    sdir = Path(sample["dir"])
    plan = json.loads((sdir / "plan.json").read_text())
    incl = {s["stratum"]: float(s["inclusion_float"]) for s in plan.get("strata", [])}
    feat = pd.read_csv(sdir / "features.csv.gz", dtype={"market_id": str, "condition_id": str})
    feat = feat[feat["status"] == "ok"].drop_duplicates("market_id").reset_index(drop=True)
    tr = pd.read_csv(sdir / "trades.csv.gz", usecols=["market_id", "ts", "side", "price", "size", "outcome_index",
                                                      "asset"], dtype={"market_id": str, "asset": str})
    rows = load_rows(cap["dir"], token=True).set_index("market_id")
    o = rows.reindex(feat["market_id"].astype(str)).reset_index()
    del rows
    token0 = pd.Series(o["clob_token_id_0"].astype(str).to_numpy(), index=o["market_id"].astype(str))
    tr["sg"] = _signs(tr, token0)
    origin = panel._epoch(feat["origin_utc"])
    W, lag = float(f["window_s"]), float(f["lag_s"])
    mkt = feat["market_id"].astype(str)
    n_ret = feat["n_returned"].to_numpy(float)
    oldest = tr.groupby("market_id")["ts"].min().reindex(mkt).to_numpy(float)
    full = n_ret < trade_sample.TRADE_LIMIT
    with np.errstate(invalid="ignore"):
        cov6 = full | (np.isfinite(oldest) & (oldest <= origin - W))
        cov6l = full | (np.isfinite(oldest) & (oldest <= origin - W - lag))
    tr["o"] = tr["market_id"].astype(str).map(pd.Series(origin, index=mkt))
    tr["nt"] = tr["size"].astype(float) * tr["price"].astype(float)
    tr["sn"] = tr["sg"] * tr["nt"]

    def window(lo_s: float, hi_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        m = (tr["ts"] >= tr["o"] - lo_s) & (tr["ts"] < tr["o"] - hi_s) & (tr["sg"] != 0)
        g = tr[m].groupby("market_id")
        S = g["sn"].sum().reindex(mkt).fillna(0.0).to_numpy(float)
        N = g["nt"].sum().reindex(mkt).fillna(0.0).to_numpy(float)
        C = g.size().reindex(mkt).fillna(0).to_numpy(float)
        return S, N, C

    s6, n6, c6 = window(W, 0.0)
    s6l, n6l, _ = window(W + lag, lag)
    s6, n6, c6 = (np.where(cov6, v, np.nan) for v in (s6, n6, c6))
    s6l, n6l = (np.where(cov6l, v, np.nan) for v in (s6l, n6l))
    # trades stamped at or after the origin that sit on the page (the sample requests up to ~20 min after the origin;
    # they never enter a feature but they fill the 500-trade page, so coverage depends on them: counts only)
    n_post = tr[tr["ts"] >= tr["o"]].groupby("market_id").size().reindex(mkt).fillna(0).to_numpy(float)
    # E014's 1 h window: trade_sample's own flag (full page whose oldest trade is after origin - 1 h); a truncated
    # 1 h window makes ss NaN, never a partial value (challenger R1 finding 4); an absent flag column is unknown (NaN)
    if "trades_truncated" in feat:
        trunc1h = _truthy(feat["trades_truncated"]).astype(float)
    else:
        trunc1h = np.full(len(feat), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        imb6 = np.where(n6 > 0, s6 / n6, np.nan)
        imb6l = np.where(n6l > 0, s6l / n6l, np.nan)
        vol1 = feat["volume_1h"].to_numpy(float)
        ss = np.where(vol1 > 0, feat["signed_volume_1h"].to_numpy(float) / vol1, 0.0)
        ss = np.where(trunc1h == 1, np.nan, ss)
    feats = panel.compute_features(o, origin)
    mids = feat["market_id"].astype(str)
    ser_p = read_series(root, by_slot.get(k - 1, {}).get("id"))
    mid_p = (_lookup(ser_p, mids, "bid") + _lookup(ser_p, mids, "ask")) / 2.0
    mid = feats["mid"].to_numpy(float)
    rv = grid_rv(root, by_slot, k, mids, int(f["rv_steps"]), int(f["rv_min_diffs"]), cache)
    lrv = np.log(rv + 1e-4)
    spr = feats["spread"].to_numpy(float)
    end_ts = panel._epoch(o["end_date"])
    hte = (end_ts - origin) / 3600.0
    b14 = spec["e014"]
    chg1h = feats["chg_1h"].to_numpy(float)
    p_base = b14["base"]["intercept"] + b14["base"]["chg_1h"] * chg1h
    p_aug = (b14["augmented"]["intercept"] + b14["augmented"]["chg_1h"] * chg1h
             + b14["augmented"]["signed_share"] * ss)
    A_lo, A_hi = b14["regime_A_h"]
    regime = np.where(~np.isfinite(hte), "U", np.where(hte <= A_lo, "P", np.where(hte <= A_hi, "A", np.where(
        hte > b14["regime_B_min_h"], "B", "M"))))
    tight_i = tight(o["best_bid"], o["best_ask"], spr, spec)
    df = pd.DataFrame({
        "sample_id": sdir.name, "capture_id": cap["id"], "capture_t": cap["start"], "slot": k,
        "market_id": mids.to_numpy(), "event_id": o["event_id"].astype(str).to_numpy(), "t_row": origin,
        "role": role, "stratum": feat["stratum"].to_numpy(),
        "p_incl": feat["stratum"].map(incl).to_numpy(float),
        "bid_i": o["best_bid"].to_numpy(float), "ask_i": o["best_ask"].to_numpy(float), "mid_i": mid,
        "spread_i": spr, "tight_i": tight_i.astype(int),
        "end_ok_6h": (np.isnan(end_ts) | (end_ts > cap["start"] + f["end_margin_h"] * 3600.0)).astype(int),
        "imb6": imb6, "n6": c6, "N6": n6, "imb6_lag30": imb6l, "cov6": cov6.astype(int),
        "n_returned": n_ret, "n_post_origin": n_post, "trunc1h": trunc1h,
        # origin-side activity (Gamma volume24hr of the origin capture): the E013 population cut (section 3)
        "vol24_i": o["volume24hr"].to_numpy(float),
        "x6": np.clip(imb6, -f["x6_clip"], f["x6_clip"]) / f["x6_sd"],
        "x6_lag30": np.clip(imb6l, -f["x6_clip"], f["x6_clip"]) / f["x6_sd"],
        "rv": rv, "zRV": (lrv - f["zRV"]["centre"]) / f["zRV"]["scale"],
        "zSPR": (spr - f["zSPR"]["centre"]) / f["zSPR"]["scale"],
        "ss": ss, "n_trades_1h": feat["n_trades_1h"].to_numpy(float), "volume_1h": vol1,
        "dprev": mid - mid_p, "dprev_missing": np.isnan(mid_p).astype(int),
        **_base_controls(o, feats),
        "hte_h": hte, "regime": regime, "p_base": p_base, "p_aug": p_aug,
    })
    df["fee_rate"], df["fee_exp"] = load_fee_rates(cap["dir"], mids)
    df["frozen_utc"] = iso(now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"] = commit, spec["_sha256"][:16], collector_sha()
    return df


# --- outcomes -----------------------------------------------------------------------------------------------------


def unavailable_status(st: pd.DataFrame | None, mids: pd.Series) -> np.ndarray:
    """Detailed reason for a market with no two-sided quote at the target capture (challenger R1 finding 3):
    ``unavailable_closed`` / ``unavailable_inactive`` / ``unavailable_one_sided`` from the capture's status file,
    ``unavailable_absent`` if the market is in neither file, plain ``unavailable`` if no status file exists."""
    if st is None:
        return np.full(len(mids), "unavailable", dtype=object)
    code = st["st"].reindex(mids.astype(str)).to_numpy(object)
    return np.array(["unavailable_absent" if pd.isna(c) else f"unavailable_{c}" for c in code], dtype=object)


def outcome_cols(fr: pd.DataFrame, ser: pd.DataFrame | None, tag: str, cap: dict | None, status_missing: str,
                 spec: dict, st: pd.DataFrame | None = None) -> dict:
    mids = fr["market_id"].astype(str)
    if ser is None:
        nan = np.full(len(fr), np.nan)
        return {f"bid_{tag}": nan, f"ask_{tag}": nan, f"t_{tag}": nan, f"tight_{tag}": np.zeros(len(fr), int),
                f"cap_{tag}": None, f"cap_start_{tag}": np.nan, f"status_{tag}": status_missing}
    bid, ask, spr, t = (_lookup(ser, mids, c) for c in ("bid", "ask", "spread", "t_row"))
    return {f"bid_{tag}": bid, f"ask_{tag}": ask, f"t_{tag}": t, f"tight_{tag}": tight(bid, ask, spr, spec).astype(int),
            f"cap_{tag}": cap["id"], f"cap_start_{tag}": cap["start"],
            f"status_{tag}": np.where(np.isfinite(bid) & np.isfinite(ask), "evaluated", unavailable_status(st, mids))}


def series_ready(root: Path, by_slot: dict, slots) -> bool:
    """True if every listed slot that has a complete capture already has its series file (else wait a run: a
    missing series file must never be read as a missing capture)."""
    return all((Path(root) / "series" / f"{by_slot[j]['id']}.csv.gz").exists() for j in slots if j in by_slot)


def is_late(j: int, now: float, spec: dict) -> bool:
    """A freeze is refused once the earliest target slot's capture may have started (slot time - 60 s)."""
    return now >= slot_time(j, spec) - 60.0


def target_state(by_slot: dict, j: int, now: float, spec: dict) -> str:
    """"ready" (capture exists), "missing" (absent MISSING_AFTER_S after its slot), else "pending"."""
    if j in by_slot:
        return "ready"
    return "missing" if now > slot_time(j, spec) + MISSING_AFTER_S else "pending"


# --- the pass -----------------------------------------------------------------------------------------------------


def run_once(*, snapshot_root: Path = SNAPSHOT_ROOT, sample_root: Path = SAMPLE_ROOT, root: Path = OUT_ROOT,
             spec: dict | None = None, registered_utc: str = REGISTERED_UTC, end_utc: str = END_UTC,
             now: float | None = None, max_items: int = 40, allow_late: bool = False) -> dict:
    """Series, freezes and due outcomes for everything new. Idempotent: every file is write-once and an existing
    file is never rewritten. Returns counts (``written`` = files written this run). ``allow_late`` is for DRY RUNS on
    past captures only (the CLI allows it only with an unpinned spec and --dry-run-start); such lines are never
    confirmation lines and the analysis excludes late lines anyway (frozen_utc >= target capture start)."""
    if allow_late and spec is not None and spec.get("_pinned"):
        raise ValueError("allow_late is for dry runs with an unpinned spec only")
    spec = spec or load_spec()
    now = now_ts() if now is None else now
    root = Path(root)
    commit = git_commit()
    st = State(root)
    stats = {"run_utc": iso(now), "code_commit": commit, "spec_sha": spec["_sha256"][:16], "pinned": spec["_pinned"],
             "written": 0, "series": 0, "e012": 0, "flow": 0, "e012_out": 0, "flow_out": 0, "refused_late": 0}
    if dir_bytes(root) > DISK_CAP_BYTES:
        stats["status"] = "disk_cap"
        append_jsonl(root / "passes.jsonl", [{"kind": "disk_cap", **stats}])
        return stats
    t_reg, t_end = epoch(registered_utc), epoch(end_utc)
    by_slot = scan_captures(snapshot_root, st, spec)
    samples = scan_samples(sample_root, st)
    st.save()
    log: list[dict] = []
    budget = max_items
    # 1. series: every complete capture in [registered - 26 h, end + 26 h + slack]
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg - SERIES_LOOKBACK_S <= c["start"] < t_end + SERIES_LOOKBACK_S + 2 * GRID_S):
            continue
        p = root / "series" / f"{c['id']}.csv.gz"
        ps = root / "status" / f"{c['id']}.csv.gz"
        if (p.exists() and ps.exists()) or budget <= 0:
            continue
        rows = load_rows(c["dir"])
        wrote = False
        if not p.exists():
            ser = series_frame(rows)
            if write_once_csv(p, ser):
                wrote = True
                log.append({"kind": "series", "id": c["id"], "slot": k, "rows": len(ser), "written_utc": iso(now_ts())})
        if not ps.exists():
            sf = status_frame(rows)
            if write_once_csv(ps, sf):
                wrote = True
                log.append({"kind": "status", "id": c["id"], "slot": k, "rows": len(sf),
                            "counts": {str(a): int(b) for a, b in sf["st"].value_counts().items()},
                            "written_utc": iso(now_ts())})
        del rows
        if wrote:
            stats["series"] += 1
            budget -= 1
    # 2. freezes (origins in [registered, end); unregistered dry runs pass explicit dates)
    pinned = spec["_pinned"]
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end) or not is_e012_origin(c["start"], spec):
            continue
        p = root / "e012" / "frozen" / f"{c['id']}.csv.gz"
        late_p = p.with_name(p.name.replace(".csv.gz", ".late.csv.gz"))
        if p.exists() or late_p.exists() or budget <= 0:
            continue
        if not allow_late and is_late(k + spec["e012"]["horizon_slots"], now, spec):
            stats["refused_late"] += 1
            log.append({"kind": "e012_refused_late", "id": c["id"], "written_utc": iso(now_ts())})
            write_once_csv(late_p, pd.DataFrame({"late": [1], "checked_utc": [iso(now)]}))
            continue
        if not series_ready(root, by_slot, (k - spec["e012"]["horizon_slots"], k - spec["e012"]["skip_slots"], k - 1)):
            continue
        fr = freeze_e012(c, k, by_slot, root, spec, role_of(c["start"], registered_utc, end_utc, pinned), commit)
        if write_once_csv(p, fr):
            stats["e012"] += 1
            budget -= 1
            log.append({"kind": "e012_frozen", "id": c["id"], "slot": k, "rows": len(fr),
                        "rows_x": int(np.isfinite(fr["x"]).sum()), "written_utc": iso(now_ts())})
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    rv_cache: dict = {}
    for sid in sorted(samples):
        s = samples[sid]
        k = slot_by_id.get(s["snapshot_id"])
        if k is None:
            continue
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        p = root / "flow" / "frozen" / f"{sid}.csv.gz"
        late_p = p.with_name(p.name.replace(".csv.gz", ".late.csv.gz"))
        if p.exists() or late_p.exists() or budget <= 0:
            continue
        # refused only once the LAST target (6 h, E013) may have started; E014 rows frozen after their 2 h target
        # started are excluded per test at analysis (frozen_utc vs the target capture start)
        if not allow_late and is_late(k + spec["flow"]["horizon_slots"], now, spec):
            stats["refused_late"] += 1
            log.append({"kind": "flow_refused_late", "id": sid, "written_utc": iso(now_ts())})
            write_once_csv(late_p, pd.DataFrame({"late": [1], "checked_utc": [iso(now)]}))
            continue
        if not series_ready(root, by_slot, range(k - int(spec["flow"]["rv_steps"]), k + 1)):
            continue
        fr = freeze_flow(s, c, k, by_slot, root, spec, role_of(c["start"], registered_utc, end_utc, pinned),
                         commit, rv_cache)
        if write_once_csv(p, fr):
            stats["flow"] += 1
            budget -= 1
            log.append({"kind": "flow_frozen", "id": sid, "capture_id": c["id"], "slot": k, "rows": len(fr),
                        "rows_x6": int(np.isfinite(fr["x6"]).sum()), "rows_ss": int((fr["ss"] != 0).sum()),
                        "written_utc": iso(now_ts())})
    # 3. outcomes (copied from the target capture's series file)
    for p in sorted((root / "e012" / "frozen").glob("*.csv.gz")) if (root / "e012" / "frozen").exists() else []:
        if p.name.endswith(".late.csv.gz"):
            continue
        op = root / "e012" / "outcomes" / p.name
        if op.exists() or budget <= 0:
            continue
        fr = pd.read_csv(p, usecols=["market_id", "slot"], dtype={"market_id": str})
        j = int(fr["slot"].iloc[0]) + spec["e012"]["horizon_slots"] if len(fr) else None
        if j is None:
            continue
        ts = target_state(by_slot, j, now, spec)
        if ts == "pending":
            continue
        ser = read_series(root, by_slot[j]["id"]) if ts == "ready" else None
        if ts == "ready" and ser is None:
            continue  # target series not written yet (next run)
        stj = read_status(root, by_slot[j]["id"]) if ts == "ready" else None
        out = pd.DataFrame({"market_id": fr["market_id"],
                            **outcome_cols(fr, ser, "j", by_slot.get(j), "missing_capture", spec, stj)})
        if write_once_csv(op, out):
            stats["e012_out"] += 1
            budget -= 1
            log.append({"kind": "e012_outcomes", "id": p.name[:-7], "target_slot": j, "target": ts,
                        "rows": len(out), "written_utc": iso(now_ts())})
    for p in sorted((root / "flow" / "frozen").glob("*.csv.gz")) if (root / "flow" / "frozen").exists() else []:
        if p.name.endswith(".late.csv.gz"):
            continue
        op = root / "flow" / "outcomes" / p.name
        if op.exists() or budget <= 0:
            continue
        fr = pd.read_csv(p, usecols=["market_id", "slot"], dtype={"market_id": str})
        if not len(fr):
            continue
        k = int(fr["slot"].iloc[0])
        hs = (k + spec["e014"]["horizon_slots"], k + spec["flow"]["horizon_slots"])
        states = [target_state(by_slot, j, now, spec) for j in hs]
        if "pending" in states:
            continue
        sers = [read_series(root, by_slot[j]["id"]) if s == "ready" else None for j, s in zip(hs, states, strict=True)]
        if any(s == "ready" and ser is None for s, ser in zip(states, sers, strict=True)):
            continue
        sts = [read_status(root, by_slot[j]["id"]) if s == "ready" else None for j, s in zip(hs, states, strict=True)]
        out = pd.DataFrame({"market_id": fr["market_id"],
                            **outcome_cols(fr, sers[0], "j2", by_slot.get(hs[0]), "missing_capture", spec, sts[0]),
                            **outcome_cols(fr, sers[1], "j6", by_slot.get(hs[1]), "missing_capture", spec, sts[1])})
        if write_once_csv(op, out):
            stats["flow_out"] += 1
            budget -= 1
            log.append({"kind": "flow_outcomes", "id": p.name[:-7], "targets": list(states), "rows": len(out),
                        "written_utc": iso(now_ts())})
    stats["written"] = sum(stats[k] for k in ("series", "e012", "flow", "e012_out", "flow_out"))
    stats["status"] = "wrote" if stats["written"] else "nothing_new"
    for r in log:
        r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
    append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
    return stats


# --- operational counts (never reads a mid, a move or an outcome value) ---------------------------------------------


def ops_stats(root: Path = OUT_ROOT) -> dict:
    root = Path(root)
    out: dict = {"root": str(root), "bytes": dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "e012/frozen", "e012/outcomes", "flow/frozen", "flow/outcomes"):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(".late.csv.gz")]),
                    "late": len([f for f in files if f.name.endswith(".late.csv.gz")])}
    status = {}
    for sub, cols in (("e012/outcomes", ["status_j"]), ("flow/outcomes", ["status_j2", "status_j6"])):
        d = root / sub
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            s = pd.read_csv(f, usecols=cols)
            for c in cols:
                for k, v in s[c].value_counts().items():
                    status[f"{sub}:{c}:{k}"] = status.get(f"{sub}:{c}:{k}", 0) + int(v)
    out["outcome_status_counts"] = status
    roles = {}
    for sub in ("e012/frozen", "flow/frozen"):
        d = root / sub
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith(".late.csv.gz"):
                continue
            s = pd.read_csv(f, usecols=["role"])
            for k, v in s["role"].value_counts().items():
                roles[f"{sub}:{k}"] = roles.get(f"{sub}:{k}", 0) + int(v)
    out["line_roles"] = roles
    return out


# --- census (pre-window moderator scales; reads no target and no capture after ``until``) ----------------------------


def check_census_inputs(spec: dict, what: str, got: list[str]) -> None:
    """Refuse unless the captures / samples the census selected are exactly the ids registered in the spec's
    ``census.captures`` / ``census.samples`` (R1 re-check: "newest 4 before ``until``" is not an identity)."""
    want = list((spec.get("census") or {}).get(what) or [])
    if list(got) != want:
        raise RuntimeError(f"live_tests2 census refused: selected {what} {list(got)} != the spec's census.{what} {want}")


def census(*, snapshot_root: Path = SNAPSHOT_ROOT, sample_root: Path = SAMPLE_ROOT, until_utc: str,
           n_caps: int = 4, n_samples: int = 4, spec: dict | None = None, work: Path | None = None) -> dict:
    """Moderator distributions (log volume, log RV proxy, spread) and line counts on the newest ``n_caps`` captures
    and ``n_samples`` active samples whose capture started before ``until_utc``. Origin-side fields only; used once to
    freeze the z-centres/scales and economics cuts into the spec (they change effect units and the economics
    tercile, never the sign or the p-value of an interaction test)."""
    spec = spec or load_spec(sha=None)
    work = Path(work or (OUT_ROOT / "_census"))
    st = State(work)
    by_slot = {k: c for k, c in scan_captures(snapshot_root, st, spec).items() if c["start"] < epoch(until_utc)}
    ks = sorted(by_slot)
    check_census_inputs(spec, "captures", [by_slot[k]["id"] for k in ks[-n_caps:]])
    # series for the newest n_caps + 12 captures (needed by the RV proxy), written under ``work`` only
    need = ks[-(n_caps + spec["flow"]["rv_steps"] + 1):]
    for k in need:
        p = work / "series" / f"{by_slot[k]['id']}.csv.gz"
        if not p.exists():
            write_once_csv(p, series_frame(load_rows(by_slot[k]["dir"])))
    Ls, nel = [], []
    for k in ks[-n_caps:]:
        rows = load_rows(by_slot[k]["dir"])
        b = rows[rows["binary"] == 1].reset_index(drop=True)
        ok = panel.eligibility_mask(b, by_slot[k]["start"] + spec["e012"]["end_margin_h"] * 3600.0)
        o = b[ok]
        Ls.append(np.log1p(np.nan_to_num(o["volume24hr"].to_numpy(float), nan=0.0).clip(min=0)))
        nel.append({"capture": by_slot[k]["id"], "eligible": int(ok.sum()), "events": int(o["event_id"].nunique()),
                    "chg_1d_nonzero": int((np.nan_to_num(o["chg_1d"].to_numpy(float)) != 0).sum())})
    L = np.concatenate(Ls)
    samples = scan_samples(sample_root, st)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    use = [s for s in sorted(samples) if samples[s]["snapshot_id"] in slot_by_id][-n_samples:]
    check_census_inputs(spec, "samples", use)
    frames, cnt = [], []
    cache: dict = {}
    spec_c = json.loads(json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}))
    for key in ("zRV", "zSPR"):
        spec_c["flow"][key] = {"centre": 0.0, "scale": 1.0}
    spec_c["_sha256"] = spec["_sha256"]
    for sid in use:
        k = slot_by_id[samples[sid]["snapshot_id"]]
        fr = freeze_flow(samples[sid], by_slot[k], k, by_slot, work, spec_c, ROLE_UNREG, "census", cache)
        frames.append(fr)
        f6 = fr[(fr["tight_i"] == 1) & (fr["n6"] > 0) & np.isfinite(fr["x6"])]
        ss = fr[(fr["tight_i"] == 1) & np.isfinite(fr["ss"]) & (fr["ss"] != 0)]
        cnt.append({"sample": sid, "rows": len(fr), "tight": int(fr["tight_i"].sum()), "flow6_rows": len(f6),
                    "flow6_events": int(f6["event_id"].nunique()), "flow6_rv_finite": int(np.isfinite(f6["zRV"]).sum()),
                    "ss_rows": len(ss), "ss_A": int((ss["regime"] == "A").sum()),
                    "ss_B": int((ss["regime"] == "B").sum()), "ss_P": int((ss["regime"] == "P").sum()),
                    "ss_A_events": int(ss.loc[ss["regime"] == "A", "event_id"].nunique()),
                    "ss_B_events": int(ss.loc[ss["regime"] == "B", "event_id"].nunique())})
    F = pd.concat(frames, ignore_index=True)
    f6 = F[(F["tight_i"] == 1) & (F["n6"] > 0) & np.isfinite(F["x6"])]
    lrv = f6["zRV"].to_numpy(float)  # = log(rv + 1e-4) with centre 0, scale 1
    lrv = lrv[np.isfinite(lrv)]
    spr = f6["zSPR"].to_numpy(float)
    spr = spr[np.isfinite(spr)]

    def ms(v):
        return {"centre": float(np.mean(v)), "scale": float(np.std(v, ddof=1)), "n": int(len(v))}

    return {"until_utc": until_utc, "captures": [by_slot[k]["id"] for k in ks[-n_caps:]], "samples": use,
            "zL": ms(L), "zRV": ms(lrv), "zSPR": ms(spr), **truncation_census(F, spec),
            "L_tercile_cuts": [float(x) for x in np.quantile(L, [1 / 3, 2 / 3])],
            "L_zero_share": float((L == 0).mean()),
            "L_pos_tercile_cuts": [float(x) for x in np.quantile(L[L > 0], [1 / 3, 2 / 3])],
            "lrv_tercile_cuts": [float(x) for x in np.quantile(lrv, [1 / 3, 2 / 3])],
            "spr_tercile_cuts": [float(x) for x in np.quantile(spr, [1 / 3, 2 / 3])],
            "e012_counts": nel, "flow_counts": cnt,
            "bytes": {"series_per_capture": int(np.mean([(work / "series" / f"{by_slot[k]['id']}.csv.gz").stat().st_size
                                                           for k in need]))}}


def flow_trunc_frame(F: pd.DataFrame) -> pd.DataFrame:
    """Rows that would carry 6 h flow if covered (tight, at least one trade in the window or a truncated window),
    with ``trunc6`` = 1 for a truncated window. Origin-side and page fields only (no target)."""
    cov = F["cov6"].to_numpy(int) == 1
    n6 = F["n6"].to_numpy(float)
    cand = (F["tight_i"].to_numpy(int) == 1) & ((~cov) | (np.nan_to_num(n6) > 0))
    out = F.loc[cand, ["vol24_i"]].copy()
    out["trunc6"] = (~cov[cand]).astype(int)
    return out


def vol24_cap_rule(F: pd.DataFrame, max_share: float) -> float:
    """E013 population cut (challenger R1 finding 4), fixed once from the pre-window census: the largest origin
    ``volume24hr`` value v such that, among census flow rows with volume24hr <= v, the share of truncated 6 h windows
    is <= ``max_share``. +inf if the whole census meets it. Rows with unknown volume24hr are not used."""
    t = flow_trunc_frame(F)
    t = t[np.isfinite(t["vol24_i"])].sort_values("vol24_i", kind="mergesort")
    if t.empty:
        return float("nan")
    v = t["vol24_i"].to_numpy(float)
    share = np.cumsum(t["trunc6"].to_numpy(float)) / np.arange(1, len(t) + 1)
    last = np.r_[v[1:] != v[:-1], True]  # evaluate each distinct value once (all its ties included)
    ok = last & (share <= max_share)
    if ok[-1]:
        return float("inf")
    return float(v[ok].max()) if ok.any() else float("nan")


def truncation_census(F: pd.DataFrame, spec: dict) -> dict:
    t = flow_trunc_frame(F)
    cap = vol24_cap_rule(F, float(spec["flow"]["vol24_cap_max_trunc_share"]))
    under = t[t["vol24_i"] <= cap] if np.isfinite(cap) else t[np.isfinite(t["vol24_i"])]
    tr1 = F["trunc1h"].to_numpy(float)
    return {"trunc6": {"rows": len(t), "truncated": int(t["trunc6"].sum()),
                       "share": float(t["trunc6"].mean()) if len(t) else None},
            "vol24_cap": cap, "vol24_cap_rows_kept_share": float(len(under) / len(t)) if len(t) else None,
            "trunc6_share_under_cap": float(under["trunc6"].mean()) if len(under) else None,
            "trunc1h": {"rows": int(np.isfinite(tr1).sum()), "truncated": int(np.nansum(tr1 == 1))}}


def cleanup_census(work: Path) -> None:
    shutil.rmtree(work, ignore_errors=True)
