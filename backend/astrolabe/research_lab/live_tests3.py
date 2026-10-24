# ruff: noqa: E501
"""LIVE prospective tests E015-E019 (docs/research_lab/LIVE_TESTS_3.md, sections 1-9 as amended by section 13).
DRAFT until the ledger registration.

Research tooling only: a PURE READER of streams the Oracle collector already writes every 2 hours. It never trades and
makes no network request:

* complete-universe captures ``research_lab/snapshots/<capture>/rows.csv.gz`` and the sidecar ``rows_ext.csv.gz``;
* book sweep 1 of each pass ``research_lab/book_sweeps/<sweep>/`` (``series_index`` 0, same ``snapshot_id``), for the
  E015 / E016 / E019 mechanism readings only;
* the active-frame trade sample of each pass ``research_lab/trade_samples/<sample>/`` (E016, E018). Wallet files are
  never opened. Samples are consumed online, well inside the host's 3-day trade-sample retention.

Outputs (``research_lab/live_tests3/``; every data file is WRITE-ONCE, atomic, never edited; no retention rule
covers this directory, so it is never deleted on the host):

* ``series/<capture>.csv.gz`` + ``status/<capture>.csv.gz``: slim two-sided quotes (plus last trade price, 24 h
  volume, end / created dates, sidecar category, tick, fee) of every open binary market of each complete capture, and
  the status (one_sided / closed_flag) of the other binary rows. Every look-back and every target comes from these
  files, so the analysis does not depend on capture retention.
* ``sweeps/<capture>.csv.gz``: the outcome-0 book bid / ask of sweep 1 of the pass (mechanism readings only).
* ``move/frozen/<capture>.csv.gz``: E015 mover lines (every eligible market with |x| >= 1c, all categories, with class
  and geometry) and ``events/frozen/<capture>.csv.gz``: E019 event-interval lines (non-sports neg-risk events with
  >= 3 eligible members).
* ``surge/frozen/<capture>.csv.gz``: E017 lines (every eligible market, labels S / A / SM / baseline); written only if E017 is in ``k_tests``.
* ``flow/frozen/<sample>.csv.gz``: E016 / E018 lines (one per sampled market); written only if E016 or E018 is in ``k_tests``.
* ``<kind>/outcomes/<id>.h<j>.csv.gz`` (status and quote at slot k + j) and ``<kind>/outcomes/<id>.s<j>.csv.gz``
  (sweep-1 quote of the pass at slot k + j). Never imputed; statuses two_sided / one_sided / closed_flag / absent /
  capture_missing (section 1.5).
* ``passes.jsonl`` (append-only log) and ``state.json`` (processed-id cache only).

Causality: every origin feature uses the origin capture and earlier captures only, or trades strictly before the
origin row's receipt time. A frozen file is refused (``.late`` marker, counted) once its earliest target slot may
have started. Every frozen line carries ``spec_sha`` and ``code_sha``; the analysis keeps only lines whose values equal
the registered pins. ``ops_stats`` counts files, lines, roles and statuses and never reads a price column.
"""

from __future__ import annotations

import fcntl
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

from . import cb13_label as lab
from . import cb17_census, economics, forecast, panel, trade_sample

VERSION = "live-tests3-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = ROOT / "data-dumps" / "research_lab" / "trade_samples"
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests3"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests3_v1.json"
SPEC_SHA256 = "72a174eb85a08ef68b279e67af224a7acced9535f9329dc8eb0d75853af22a26"  # pinned at registration 2026-10-21 (LIVE_TESTS_3.md 9.3, 13.18)

REGISTERED_UTC = "2026-10-24T00:00:00Z"
END_UTC = "2026-11-14T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-11-15T12:00:00Z"
TEMPFAIL = 75
DISK_CAP_BYTES = int(1.5e9)
GRID_S = 7200.0
SLOT_TOL_S = 1800.0
SERIES_LOOKBACK_S = 28 * 3600.0  # E017 pre-trend needs slot k - 13 (26 h), the flow RV slots k - 12 .. k
MISSING_AFTER_S = 3 * 3600.0  # a target capture absent 3 h after its slot is "capture_missing"
ROLE_CONF, ROLE_UNREG = "prospective_confirmation", "prospective_unregistered"
CODE_FILES = ("live_tests3.py", "live_tests3_analysis.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)
STATUSES = ("two_sided", "one_sided", "closed_flag", "absent", "capture_missing")

SNAP_COLS = ["market_id", "condition_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid",
             "best_ask", "spread", "last_trade_price", "chg_1h", "chg_1d", "chg_1w", "volume24hr", "end_date",
             "neg_risk"]
EXT_COLS = ["market_id", "fee_type", "fee_category", "fees_enabled", "fee_schedule", "order_price_min_tick_size",
            "created_at", "series_slugs"]
SWEEP_COLS = ["token_id", "market_id", "batch_receipt_utc", "best_bid", "best_ask", "state"]
# columns ops_stats may read (never a price, a move or a target; enforced by a unit test)
OPS_COLS = frozenset({"role", "cls", "geom", "S", "A", "SM", "sports", "neg_risk", "untraded", "late", "checked_utc", "status"})


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
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised: the spec JSON pins the code hashes and the
    code pins the spec hash, so the pin line itself is kept outside the code hash (LIVE_TESTS_3.md 9.3)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: code_sha256(here / n) for n in CODE_FILES}


def reader_sha() -> str:
    """First 16 hex digits of the normalised sha256 of this module, written into every frozen line."""
    return code_sha256(Path(__file__).resolve())[:16]


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"live_tests3 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"] = got
    spec["_pinned"] = sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests3 spec {key} {spec.get(key)!r} != module constant {val!r} (freeze fix 5)")
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
    """Write ``df`` (gzip CSV) to ``path`` only if it does not exist; atomic (tmp + hard link). False if it existed
    (the existing file is never touched)."""
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_csv(tmp, index=False, compression="gzip")  # shortest round-trip repr: epoch seconds and volumes survive exactly (freeze fix 1)
    with open(tmp, "rb") as fh:
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def dir_bytes(path: Path) -> int:
    tot = 0
    for p in Path(path).rglob("*"):
        if p.is_file():
            tot += p.stat().st_size
    return tot


def du_bytes(path: Path) -> int:
    try:
        out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=300)
        return int(out.stdout.split()[0]) * 1024
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return dir_bytes(path)


def _truthy(v: pd.Series) -> np.ndarray:
    return v.astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "t"]).to_numpy()


# --- grid, windows and the processed-id cache -----------------------------------------------------------------------


def grid0(spec: dict) -> float:
    return epoch(spec["grid"]["grid0_utc"])


def slot_of(t: float, spec: dict) -> int | None:
    g0 = grid0(spec)
    k = int(round((t - g0) / GRID_S))
    return k if abs(t - (g0 + k * GRID_S)) <= SLOT_TOL_S else None


def slot_time(k: int, spec: dict) -> float:
    return grid0(spec) + k * GRID_S


def role_of(capture_start: float, registered_utc: str, end_utc: str, pinned: bool) -> str:
    ok = pinned and epoch(registered_utc) <= capture_start < epoch(end_utc)
    return ROLE_CONF if ok else ROLE_UNREG


def _manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text())


class State:
    """Processed-id cache (``state.json``). Only a speed-up: the write-once files are the ground truth."""

    def __init__(self, root: Path) -> None:
        self.path = Path(root) / "state.json"
        self.d = json.loads(self.path.read_text()) if self.path.exists() else {}
        for k in ("captures", "samples", "sweeps"):
            self.d.setdefault(k, {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, sort_keys=True))
        os.replace(tmp, self.path)


def scan_captures(snapshot_root: Path, st: State, spec: dict) -> dict[int, dict]:
    """Complete captures by slot ({slot: {"id", "start", "dir"}}); the first complete capture of a slot wins. Only a
    manifest that says ``state=complete`` counts (the collector renames it into place when the capture is done)."""
    for p in sorted(Path(snapshot_root).glob("*/manifest.json")):
        cid = p.parent.name
        if cid in st.d["captures"]:
            continue
        try:
            m = _manifest(p)
        except (OSError, ValueError):
            continue
        if m.get("state") != "complete" or not (p.parent / "rows.csv.gz").exists():
            continue
        t = epoch(m.get("started_utc"))
        st.d["captures"][cid] = {"start": t, "slot": slot_of(t, spec)}
    by_slot: dict[int, dict] = {}
    for cid, c in sorted(st.d["captures"].items(), key=lambda kv: kv[1]["start"]):
        if c["slot"] is None:
            continue
        by_slot.setdefault(c["slot"], {"id": cid, "start": c["start"], "dir": Path(snapshot_root) / cid})
    return by_slot


def scan_samples(sample_root: Path, st: State) -> dict[str, dict]:
    """Complete active-frame trade samples ({sample_id: {"snapshot_id", "dir"}})."""
    out = {}
    for p in sorted(Path(sample_root).glob("*/manifest.json")):
        sid = p.parent.name
        if sid not in st.d["samples"]:
            try:
                m = _manifest(p)
            except (OSError, ValueError):
                continue
            if m.get("state") != "complete" or not (p.parent / "features.csv.gz").exists():
                continue
            st.d["samples"][sid] = {"snapshot_id": m.get("snapshot_id"), "frame": m.get("frame")}
        s = st.d["samples"][sid]
        if s.get("frame") == "active":
            out[sid] = {"snapshot_id": s["snapshot_id"], "dir": p.parent}
    return out


def scan_sweeps(sweep_root: Path, st: State) -> dict[str, dict]:
    """Sweep 1 (``series_index`` 0, state complete) by snapshot id ({snapshot_id: {"id", "dir"}})."""
    for p in sorted(Path(sweep_root).glob("*/manifest.json")):
        sid = p.parent.name
        if sid in st.d["sweeps"]:
            continue
        try:
            m = _manifest(p)
        except (OSError, ValueError):
            continue
        if m.get("state") != "complete" or not (p.parent / "rows.csv.gz").exists():
            continue
        st.d["sweeps"][sid] = {"snapshot_id": m.get("snapshot_id"), "series_index": m.get("series_index")}
    out: dict[str, dict] = {}
    for sid, s in sorted(st.d["sweeps"].items()):
        if s.get("series_index") == 0 and s.get("snapshot_id"):
            out.setdefault(s["snapshot_id"], {"id": sid, "dir": Path(sweep_root) / sid})
    return out


# --- capture readers and the series --------------------------------------------------------------------------------


def load_rows(cap_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Origin-side capture columns: one row per market_id and per condition_id (first in page order; counted)."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=SNAP_COLS,
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category",
                              "end_date": "category", "closed": str, "active": str, "neg_risk": str})
    n0 = len(rows)
    rows = rows.drop_duplicates("market_id")
    n1 = len(rows)
    cond = rows["condition_id"].fillna("")
    dup_c = cond.ne("") & cond.duplicated()
    rows = rows[~dup_c.to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows, {"rows": n0, "dup_market_id": n0 - n1, "dup_condition_id": int(dup_c.sum())}


def load_ext(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=EXT_COLS, dtype={c: str for c in EXT_COLS})
    return ext.drop_duplicates("market_id").set_index("market_id")


def fee_rates(ext: pd.DataFrame | None, market_ids: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """(taker fee rate, exponent) per market (``economics.fee_spec`` / ``resolve_rate``, policy max_if_unknown); an
    absent sidecar row resolves as unknown (the maximum documented rate)."""
    if ext is not None:
        e = ext.reindex(market_ids.astype(str))
    else:
        e = pd.DataFrame(index=market_ids.astype(str), columns=EXT_COLS[1:])
    key = e[["fee_schedule", "fees_enabled", "fee_category"]].astype(str)
    cache: dict = {}
    rate, expo = np.empty(len(key)), np.empty(len(key))
    for i, k in enumerate(key.itertuples(index=False)):
        k = tuple(k)
        if k not in cache:
            fs, fe, fc = (None if v in ("nan", "None", "") else v for v in k)
            s = economics.fee_spec(fs, fe, fc)
            cache[k] = (economics.resolve_rate(s, "max_if_unknown"), s.exponent)
        rate[i], expo[i] = cache[k]
    return rate, expo


def category_cols(ext: pd.DataFrame | None, market_ids: pd.Series, event_ids: pd.Series, spec: dict) -> dict:
    """sports (1/0, -1 = sidecar missing), crypto (1/0, -1), series-or-event key ``skey``, tick, created_ts."""
    n = len(market_ids)
    ev = event_ids.astype(str).to_numpy()
    if ext is None:
        return {"sports": np.full(n, -1), "crypto": np.full(n, -1), "skey": np.array(["event:" + e for e in ev], dtype=object),
                "tick": np.full(n, np.nan), "created_ts": np.full(n, np.nan)}
    e = ext.reindex(market_ids.astype(str))
    present = e["fee_type"].notna().to_numpy() | e["series_slugs"].notna().to_numpy() | e["created_at"].notna().to_numpy()
    ft, fc, ss = (e[c].where(e[c].notna(), None).tolist() for c in ("fee_type", "fee_category", "series_slugs"))
    cr = spec["crypto_rule"]
    rx = re.compile(cr["slug_regex"])
    sports, crypto, skey = np.empty(n, int), np.empty(n, int), np.empty(n, dtype=object)
    cache: dict = {}
    for i in range(n):
        key = (ft[i], fc[i], ss[i])
        if key not in cache:
            slug = lab.first_series_slug(ss[i])
            is_sp = cb17_census.is_sports_sidecar(ft[i], fc[i], ss[i])
            is_cr = str(ft[i] or "").lower().startswith(cr["fee_type_prefix"]) or bool(slug and rx.search(slug))
            cache[key] = (int(is_sp), int(is_cr), slug)
        sp, c, slug = cache[key]
        if not present[i]:
            sports[i], crypto[i], skey[i] = -1, -1, "event:" + ev[i]
            continue
        sports[i], crypto[i] = sp, c
        skey[i] = slug if slug else ("crypto:noslug" if c else "event:" + ev[i])
    tick = pd.to_numeric(e["order_price_min_tick_size"], errors="coerce").to_numpy(float)
    return {"sports": sports, "crypto": crypto, "skey": skey, "tick": tick, "created_ts": panel._epoch(e["created_at"])}


def series_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(series, status): two-sided quotes of open active binary markets, and the status of every other binary row
    (``closed_flag`` = closed true or active false; ``one_sided`` = open and active but not two-sided)."""
    b = rows[rows["binary"] == 1]
    closed = _truthy(b["closed"])
    active = _truthy(b["active"])
    two = panel.target_valid(b)
    ok = two & ~closed & active
    s = b[ok].reset_index(drop=True)
    bid, ask = s["best_bid"].to_numpy(float), s["best_ask"].to_numpy(float)
    spread = s["spread"].to_numpy(float)
    ltp = s["last_trade_price"].to_numpy(float)
    mids = s["market_id"].astype(str)
    cat = category_cols(ext, mids, s["event_id"], spec)
    rate, expo = fee_rates(ext, mids)
    ser = pd.DataFrame({
        "market_id": mids.to_numpy(), "event_id": s["event_id"].astype(str).to_numpy(), "t_row": s["t_row"].to_numpy(float),
        "bid": bid, "ask": ask, "spread": np.where(np.isnan(spread), ask - bid, spread),
        "ltp": np.where(ltp > 0, ltp, np.nan), "vol24": s["volume24hr"].to_numpy(float),
        "end_ts": panel._epoch(s["end_date"]), "created_ts": cat["created_ts"],
        "chg_1h": s["chg_1h"].to_numpy(float), "chg_1d": s["chg_1d"].to_numpy(float), "chg_1w": s["chg_1w"].to_numpy(float),
        "neg_risk": _truthy(s["neg_risk"]).astype(int), "sports": cat["sports"], "crypto": cat["crypto"], "skey": cat["skey"],
        "tick": cat["tick"], "fee_rate": rate, "fee_exp": expo,
    })
    nb = b[~ok]
    st = np.where(closed[~ok] | ~active[~ok], "closed_flag", "one_sided")
    status = pd.DataFrame({"market_id": nb["market_id"].astype(str).to_numpy(), "st": st})
    return ser, status


def read_series(root: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / "series" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "event_id": str, "skey": str}).set_index("market_id")


def read_status(root: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / "status" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "st": str}).drop_duplicates("market_id").set_index("market_id")


def read_sweep(root: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / "sweeps" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str}).drop_duplicates("market_id").set_index("market_id")


def sweep_frame(sweep_dir: Path, cap_dir: Path) -> pd.DataFrame:
    """Outcome-0 token book quote of sweep 1: market_id, sbid, sask, s_t (batch receipt), s_two (two-sided flag)."""
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=["market_id", "clob_token_id_0"],
                      dtype=str).drop_duplicates("market_id")
    sw = pd.read_csv(Path(sweep_dir) / "rows.csv.gz", usecols=SWEEP_COLS, dtype={"token_id": str, "market_id": str})
    sw = sw.merge(tok, on="market_id", how="inner")
    sw = sw[sw["token_id"] == sw["clob_token_id_0"]].drop_duplicates("market_id")
    bid, ask = sw["best_bid"].to_numpy(float), sw["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask)
    return pd.DataFrame({"market_id": sw["market_id"].to_numpy(), "sbid": bid, "sask": ask,
                         "s_t": panel._epoch(sw["batch_receipt_utc"]), "s_two": two.astype(int)})


def _look(ser: pd.DataFrame | None, mids, col: str) -> np.ndarray:
    if ser is None:
        return np.full(len(mids), np.nan)
    return ser[col].reindex(pd.Index(np.asarray(mids, dtype=str))).to_numpy(float)


def _mid(ser: pd.DataFrame | None, mids) -> np.ndarray:
    return (_look(ser, mids, "bid") + _look(ser, mids, "ask")) / 2.0


def tight_arr(bid, ask, spread, spread_max: float) -> np.ndarray:
    bid, ask, spread = (np.asarray(v, float) for v in (bid, ask, spread))
    with np.errstate(invalid="ignore"):
        return np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (bid < ask) & (ask <= 1) & (spread <= spread_max + 1e-12)


def grid_rv(root: Path, by_slot: dict, k: int, mids, steps: int, min_diffs: int, cache: dict | None = None) -> np.ndarray:
    """rms of consecutive-slot two-sided mid differences over slots k - steps .. k (series files; origin slot and
    earlier only); NaN with fewer than ``min_diffs`` valid differences."""
    cols = []
    for j in range(k - steps, k + 1):
        cid = by_slot.get(j, {}).get("id")
        if cache is not None and cid in cache:
            m = cache[cid]
        else:
            ser = read_series(root, cid)
            m = None if ser is None else (ser["bid"] + ser["ask"]) / 2.0
            if cache is not None and cid is not None:
                cache[cid] = m
                while len(cache) > steps + 4:
                    cache.pop(next(iter(cache)))
        cols.append(np.full(len(mids), np.nan) if m is None else m.reindex(pd.Index(np.asarray(mids, dtype=str))).to_numpy(float))
    d = np.diff(np.column_stack(cols), axis=1)
    n = np.isfinite(d).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = np.sqrt(np.nansum(np.where(np.isfinite(d), d, 0.0) ** 2, axis=1) / n)
    return np.where(n >= min_diffs, rv, np.nan)


def _stamp(df: pd.DataFrame, spec: dict, commit: str) -> pd.DataFrame:
    df["frozen_utc"] = iso(now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"] = commit, spec["_sha256"][:16], reader_sha()
    return df


# --- E015 / E019: move classes ---------------------------------------------------------------------------------------


def classify(bid_p, ask_p, bid_k, ask_k, ltp_p, ltp_k, vol_p, vol_k, spec: dict) -> tuple[np.ndarray, np.ndarray]:
    """(class, geometry) of a k-1 -> k quote change (section 2 class rule; spec ``move``). Class: never_traded,
    traded, ambiguous, quote_only. Geometry (for every unit, traded ones included, for M3): parallel, one_sided,
    spread_change, same_side_unequal. Uses captures k - 1 and k only."""
    m = spec["move"]
    bid_p, ask_p, bid_k, ask_k, ltp_p, ltp_k, vol_p, vol_k = (np.asarray(v, float) for v in
                                                              (bid_p, ask_p, bid_k, ask_k, ltp_p, ltp_k, vol_p, vol_k))
    x = (bid_k + ask_k) / 2.0 - (bid_p + ask_p) / 2.0
    db, da = bid_k - bid_p, ask_k - ask_p
    hp, hk = np.isfinite(ltp_p), np.isfinite(ltp_k)
    with np.errstate(invalid="ignore"):
        L = (hp & hk & (np.abs(ltp_k - ltp_p) > m["ltp_tol"])) | (~hp & hk)
        dv = vol_k - vol_p
        vknown = np.isfinite(dv)
        vplus = vknown & (dv > m["vol_tol"])
        vzero = vknown & (np.abs(dv) <= m["vol_tol"])
    cls = np.where(~hp & ~hk, "never_traded",
                   np.where(L | vplus, "traded",
                            np.where(vzero & ~(hp & ~hk), "quote_only", "ambiguous")))
    sx, sb, sa = np.sign(x), np.sign(db), np.sign(da)
    adb, ada = np.abs(db), np.abs(da)
    with np.errstate(invalid="ignore"):
        par = (sb == sx) & (sa == sx) & (sx != 0) & (adb >= m["parallel_min"] - 1e-12) & (ada >= m["parallel_min"] - 1e-12) & (np.abs(db - da) <= m["parallel_max_diff"] + 1e-12)
        one = np.minimum(adb, ada) <= m["one_sided_max"] + 1e-12
        sprc = (sb * sa < 0) & (adb > m["one_sided_max"]) & (ada > m["one_sided_max"])
    geom = np.where(par, "parallel", np.where(one, "one_sided", np.where(sprc, "spread_change", "same_side_unequal")))
    return cls.astype(object), geom.astype(object)


def move_join(ser_k: pd.DataFrame, ser_p: pd.DataFrame, cap: dict, spec: dict, mid_lo: float, mid_hi: float,
              end_margin_h: float) -> tuple[pd.DataFrame, dict]:
    """Markets two-sided at k - 1 and k with the section 1.4 filters applied in order (each exclusion counted)."""
    sm = spec["eligibility"]["spread_max"]
    cnt = {"series_k": len(ser_k)}
    j = ser_k.join(ser_p[["bid", "ask", "spread", "ltp", "vol24"]].rename(columns=lambda c: c + "_p"), how="inner")
    cnt["not_two_sided_at_k_1"] = cnt["series_k"] - len(j)
    t = tight_arr(j["bid"], j["ask"], j["spread"], sm) & tight_arr(j["bid_p"], j["ask_p"], j["spread_p"], sm)
    cnt["not_tight"] = int((~t).sum())
    j = j[t]
    mid = (j["bid"].to_numpy(float) + j["ask"].to_numpy(float)) / 2.0
    band = (mid >= mid_lo) & (mid <= mid_hi)
    cnt["mid_band"] = int((~band).sum())
    j = j[band]
    end = j["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        eok = np.isnan(end) | (end > j["t_row"].to_numpy(float) + end_margin_h * 3600.0)
    cnt["end_date"] = int((~eok).sum())
    j = j[eok].copy()
    cnt["eligible"] = len(j)
    j.index.name = "market_id"
    return j.reset_index(), cnt


def freeze_move(ser_k: pd.DataFrame, ser_p: pd.DataFrame, cap: dict, k: int, spec: dict, role: str, commit: str
                ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(E015 mover lines, E019 event-interval lines, counts) for origin capture k (captures k - 1 and k only)."""
    m = spec["move"]
    j, cnt = move_join(ser_k, ser_p, cap, spec, m["mid_lo"], m["mid_hi"], m["end_margin_h"])
    bid, ask, bid_p, ask_p = (j[c].to_numpy(float) for c in ("bid", "ask", "bid_p", "ask_p"))
    mid, mid_p = (bid + ask) / 2.0, (bid_p + ask_p) / 2.0
    x = mid - mid_p
    cls, geom = classify(bid_p, ask_p, bid, ask, j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    with np.errstate(divide="ignore", invalid="ignore"):
        logit = np.log(mid / (1.0 - mid))
        lax = np.log(np.abs(x))
    mover = np.abs(x) >= m["min_abs_x"] - 1e-12
    base = {"capture_id": cap["id"], "capture_t": cap["start"], "slot": k, "role": role}
    u = j[mover]
    units = pd.DataFrame({
        **base, "market_id": u["market_id"].to_numpy(), "event_id": u["event_id"].to_numpy(),
        "t_row": u["t_row"].to_numpy(float), "sports": u["sports"].to_numpy(int), "neg_risk": u["neg_risk"].to_numpy(int),
        "crypto": u["crypto"].to_numpy(int), "skey": u["skey"].to_numpy(),
        "bid_k": bid[mover], "ask_k": ask[mover], "mid_k": mid[mover], "spread_k": u["spread"].to_numpy(float),
        "bid_p": bid_p[mover], "ask_p": ask_p[mover], "x": x[mover], "db": (bid - bid_p)[mover], "da": (ask - ask_p)[mover],
        "cls": cls[mover], "geom": geom[mover], "ltp_k": u["ltp"].to_numpy(float), "ltp_p": u["ltp_p"].to_numpy(float),
        "dvol": (u["vol24"] - u["vol24_p"]).to_numpy(float), "log_abs_x": lax[mover], "abs_dev": np.abs(mid - 0.5)[mover],
        "logit_mid": logit[mover], "log1p_vol": np.log1p(np.nan_to_num(u["vol24"].to_numpy(float), nan=0.0).clip(min=0)),
        "fee_rate": u["fee_rate"].to_numpy(float), "fee_exp": u["fee_exp"].to_numpy(float),
    })
    cnt.update(movers=int(mover.sum()), by_class={str(a): int(b) for a, b in units["cls"].value_counts().items()})
    # E019: non-sports neg-risk events with >= min_members eligible members (members of every |x|)
    e = spec["e019"]
    sel = (j["neg_risk"].to_numpy(int) == 1) & (j["sports"].to_numpy(int) == 0)
    g = pd.DataFrame({"event_id": j["event_id"].to_numpy()[sel], "skey": j["skey"].to_numpy()[sel],
                      "crypto": j["crypto"].to_numpy(int)[sel], "t_row": j["t_row"].to_numpy(float)[sel],
                      "trad_amb": np.isin(cls[sel], ("traded", "ambiguous")).astype(int),
                      "qo_mov": ((cls[sel] == "quote_only") & mover[sel]).astype(int),
                      "os_mov": ((cls[sel] == "quote_only") & mover[sel] & (geom[sel] == "one_sided")).astype(int),
                      "sc_mov": ((cls[sel] == "quote_only") & mover[sel] & (geom[sel] == "spread_change")).astype(int),
                      "lax_mov": np.where((cls[sel] == "quote_only") & mover[sel], lax[sel], np.nan),
                      "spr_mov": np.where((cls[sel] == "quote_only") & mover[sel], j["spread"].to_numpy(float)[sel], np.nan)})
    if len(g):
        a = g.groupby("event_id", sort=True).agg(skey=("skey", "first"), crypto=("crypto", "max"), t_row=("t_row", "min"),
                                                 n_elig=("t_row", "size"), n_trad_amb=("trad_amb", "sum"),
                                                 n_qo_mov=("qo_mov", "sum"), n_os=("os_mov", "sum"), n_sc=("sc_mov", "sum"),
                                                 mean_log_abs_x=("lax_mov", "mean"), mean_spread=("spr_mov", "mean")).reset_index()
        a = a[a["n_elig"] >= e["min_members"]].reset_index(drop=True)
    else:
        a = pd.DataFrame(columns=["event_id", "skey", "crypto", "t_row", "n_elig", "n_trad_amb", "n_qo_mov", "n_os", "n_sc",
                                  "mean_log_abs_x", "mean_spread"])
    with np.errstate(invalid="ignore", divide="ignore"):
        b = a["n_qo_mov"].to_numpy(float) / a["n_elig"].to_numpy(float)
        nq = a["n_qo_mov"].to_numpy(float)
        events = pd.DataFrame({**base, "event_id": a["event_id"].astype(str).to_numpy(), "skey": a["skey"].to_numpy(),
                               "crypto": a["crypto"].to_numpy(int), "t_row": a["t_row"].to_numpy(float),
                               "n_elig": a["n_elig"].to_numpy(int), "n_trad_amb": a["n_trad_amb"].to_numpy(int),
                               "untraded": (a["n_trad_amb"].to_numpy(int) == 0).astype(int), "n_qo_mov": a["n_qo_mov"].to_numpy(int),
                               "b": b, "sh_os": np.where(nq > 0, a["n_os"].to_numpy(float) / nq, np.nan),
                               "sh_sc": np.where(nq > 0, a["n_sc"].to_numpy(float) / nq, np.nan),
                               "log_n_elig": np.log(a["n_elig"].to_numpy(float)),
                               "mean_log_abs_x": a["mean_log_abs_x"].to_numpy(float), "mean_spread": a["mean_spread"].to_numpy(float)})
    cnt["event_intervals"] = len(events)
    return _stamp(units, spec, commit), _stamp(events, spec, commit), cnt


# --- E017: surges --------------------------------------------------------------------------------------------------


def freeze_surge(ser_k: pd.DataFrame, ser_p: pd.DataFrame, ser_p2: pd.DataFrame | None, ser_p13: pd.DataFrame | None,
                 cap: dict, k: int, spec: dict, role: str, commit: str) -> tuple[pd.DataFrame, dict]:
    """E017 lines for origin capture k: every eligible market (section 4 filters plus finding 7 / 8), labels from
    captures k - 2 .. k, the pre-trend placebo target mid_{k-1} - mid_{k-13} (all pre-origin)."""
    s = spec["surge"]
    j, cnt = move_join(ser_k, ser_p, cap, spec, s["mid_lo"], s["mid_hi"], s["end_margin_h"])
    t = j["t_row"].to_numpy(float)
    cr = j["created_ts"].to_numpy(float)
    known = np.isfinite(cr)
    cnt["created_unknown"] = int((~known).sum())
    with np.errstate(invalid="ignore"):
        old = known & (cr <= t - s["min_age_h"] * 3600.0)
    cnt["too_new"] = int((known & ~old).sum())
    j = j[old]
    vp = j["vol24_p"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        vok = np.isfinite(vp) & (vp > 0)
    cnt["vol_prev_not_positive"] = int((~vok).sum())
    j = j[vok].reset_index(drop=True)
    mids = j["market_id"].to_numpy()
    bid, ask, bid_p, ask_p = (j[c].to_numpy(float) for c in ("bid", "ask", "bid_p", "ask_p"))
    mid, mid_p = (bid + ask) / 2.0, (bid_p + ask_p) / 2.0
    x = mid - mid_p
    mid_p2 = _mid(ser_p2, mids)
    x1 = mid_p - mid_p2
    pre = mid_p - _mid(ser_p13, mids)
    vk, vp = j["vol24"].to_numpy(float), j["vol24_p"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        S = np.isfinite(vk) & (vk >= s["surge_ratio"] * vp) & (vk - vp >= s["surge_min_abs"])
        mx = np.fmax(np.abs(x), np.abs(x1))
        lag_unknown = S & ~np.isfinite(x1)
        A = S & np.isfinite(x1) & (mx < s["move_max"] - 1e-12)
        SM = S & np.isfinite(x1) & (mx >= s["move_max"] - 1e-12)
    hte = (j["end_ts"].to_numpy(float) - j["t_row"].to_numpy(float)) / 3600.0
    with np.errstate(divide="ignore", invalid="ignore"):
        logit = np.log(mid / (1.0 - mid))
        lhte = np.log(np.clip(hte, 1.0, None))
        ratio = vk / vp
    c1d = j["chg_1d"].to_numpy(float)
    df = pd.DataFrame({
        "capture_id": cap["id"], "capture_t": cap["start"], "slot": k, "role": role,
        "market_id": mids, "event_id": j["event_id"].to_numpy(), "t_row": j["t_row"].to_numpy(float),
        "sports": j["sports"].to_numpy(int), "neg_risk": j["neg_risk"].to_numpy(int), "crypto": j["crypto"].to_numpy(int),
        "skey": j["skey"].to_numpy(), "bid_k": bid, "ask_k": ask, "mid_k": mid, "x": x,
        "x_km1": np.nan_to_num(x1, nan=0.0), "x_km1_missing": (~np.isfinite(x1)).astype(int),
        "S": S.astype(int), "A": A.astype(int), "SM": SM.astype(int), "lag_unknown": lag_unknown.astype(int),
        "vol_ratio": ratio, "pre24": pre, "logit_mid": logit, "abs_dev": np.abs(mid - 0.5),
        "log_hte": np.where(np.isfinite(lhte), lhte, 0.0), "hte_missing": (~np.isfinite(lhte)).astype(int),
        "log1p_vol_p": np.log1p(vp), "chg_1d": np.nan_to_num(c1d, nan=0.0), "chg_1d_missing": (~np.isfinite(c1d)).astype(int),
        "fee_rate": j["fee_rate"].to_numpy(float), "fee_exp": j["fee_exp"].to_numpy(float),
    })
    cnt.update(units=len(df), S=int(S.sum()), A=int(A.sum()), SM=int(SM.sum()), lag_unknown=int(lag_unknown.sum()))
    return _stamp(df, spec, commit), cnt


# --- E016 / E018: flow features ------------------------------------------------------------------------------------


def signs(tr: pd.DataFrame, token0: pd.Series | None) -> np.ndarray:
    """``trade_sample._sign`` convention on outcome 0 (+ for BUY outcome 0 or SELL outcome 1); outcome from
    ``outcome_index``, else asset == token 0; neither, or a side other than BUY / SELL -> 0 (unsigned)."""
    oi = pd.to_numeric(tr["outcome_index"], errors="coerce").to_numpy(float)
    if token0 is not None:
        t0 = tr["market_id"].astype(str).map(token0).astype(str).to_numpy()
        fb = np.where(tr["asset"].astype(str).to_numpy() == t0, 0.0, np.nan)
        oi = np.where(np.isin(oi, (0.0, 1.0)), oi, fb)
    side = tr["side"].astype(str).to_numpy()
    s = np.where(side == "BUY", 1.0, np.where(side == "SELL", -1.0, 0.0))
    return np.where(oi == 0, s, np.where(oi == 1, -s, 0.0))


def grid_distance(price, tick) -> np.ndarray:
    """|p - tick * round(p / tick)| (NaN where the tick is unknown or not positive)."""
    p, t = np.asarray(price, float), np.asarray(tick, float)
    ok = np.isfinite(t) & (t > 0)
    tt = np.where(ok, t, 1.0)
    return np.where(ok, np.abs(p - np.round(p / tt) * tt), np.nan)


def train_flags(codes: np.ndarray, ts: np.ndarray, sg: np.ndarray, gap_s: float, same_sign: bool = True) -> np.ndarray:
    """True for a row with another row of the same market (and, with ``same_sign``, the same sign) within ``gap_s``
    seconds. The caller passes only the rows of one window, so no row outside it (and no row at or after the
    origin) can make a row a train member."""
    n = len(ts)
    if n == 0:
        return np.zeros(0, bool)
    grp = codes.astype(np.int64) * 3 + ((np.sign(sg).astype(np.int64) + 1) if same_sign else 0)
    o = np.lexsort((ts, grp))
    g, t = grp[o], np.asarray(ts, float)[o]
    same_prev = np.r_[False, g[1:] == g[:-1]]
    dprev = np.r_[np.inf, t[1:] - t[:-1]]
    near_prev = same_prev & (dprev <= gap_s)
    near_next = np.r_[near_prev[1:], False]
    out = np.empty(n, bool)
    out[o] = near_prev | near_next
    return out


def flow_rows(tr: pd.DataFrame, origin_by_mkt: pd.Series, tick_by_mkt: pd.Series, token0: pd.Series | None,
              spec: dict) -> pd.DataFrame:
    """Trade rows with sign, notional, origin, grid distance and walked flag (no window applied)."""
    f = spec["flow"]
    tr = tr.copy()
    tr["sg"] = signs(tr, token0)
    tr["o"] = tr["market_id"].astype(str).map(origin_by_mkt).astype(float)
    tr["p"] = pd.to_numeric(tr["price"], errors="coerce").astype(float)
    tr["nt"] = pd.to_numeric(tr["size"], errors="coerce").astype(float) * tr["p"]
    tr["dist"] = grid_distance(tr["p"].to_numpy(), tr["market_id"].astype(str).map(tick_by_mkt).to_numpy(float))
    tr["walk_known"] = np.isfinite(tr["dist"].to_numpy()).astype(int)
    tr["walked"] = (tr["walk_known"].to_numpy() == 1) & (np.nan_to_num(tr["dist"].to_numpy(), nan=0.0) >= f["walk_min_dist"] - 1e-12)
    return tr


def window_features(tr: pd.DataFrame, mkt: pd.Series, lo_s: float, hi_s: float, gap_s: float) -> dict:
    """Per-market features over signed rows with o - lo_s <= ts < o - hi_s: imb (signed notional share), N (rows),
    NT (notional), W (walked notional share among tick-known rows), H (same-signed train notional share), Hu
    (any-sign train share, E018 M3), Wr (walked row share), Size (mean notional per signed row)."""
    with np.errstate(invalid="ignore"):
        m = (tr["ts"].to_numpy(float) >= tr["o"].to_numpy(float) - lo_s) & (tr["ts"].to_numpy(float) < tr["o"].to_numpy(float) - hi_s) & (tr["sg"].to_numpy() != 0)
    w = tr[m]
    codes, uniq = pd.factorize(w["market_id"].astype(str))
    ts, sg = w["ts"].to_numpy(float), w["sg"].to_numpy(float)
    train = train_flags(codes, ts, sg, gap_s, True)
    trainu = train_flags(codes, ts, sg, gap_s, False)
    nt = w["nt"].to_numpy(float)
    wk = w["walk_known"].to_numpy(int) == 1
    wd = w["walked"].to_numpy(bool)
    d = pd.DataFrame({"m": w["market_id"].astype(str).to_numpy(), "sn": sg * nt, "nt": nt, "one": 1.0,
                      "tn": np.where(train, nt, 0.0), "tun": np.where(trainu, nt, 0.0),
                      "wn": np.where(wd, nt, 0.0), "kn": np.where(wk, nt, 0.0), "wr": wd.astype(float), "kr": wk.astype(float)})
    g = d.groupby("m").sum().reindex(mkt.astype(str))
    with np.errstate(invalid="ignore", divide="ignore"):
        N = g["one"].fillna(0.0).to_numpy(float)
        NT = g["nt"].fillna(0.0).to_numpy(float)
        return {"imb": np.where(NT > 0, g["sn"].to_numpy(float) / NT, np.nan), "N": N, "NT": NT,
                "W": np.where(g["kn"].fillna(0.0).to_numpy(float) > 0, g["wn"].to_numpy(float) / g["kn"].to_numpy(float), np.nan),
                "H": np.where(NT > 0, g["tn"].to_numpy(float) / NT, np.nan),
                "Hu": np.where(NT > 0, g["tun"].to_numpy(float) / NT, np.nan),
                "Wr": np.where(g["kr"].fillna(0.0).to_numpy(float) > 0, g["wr"].to_numpy(float) / g["kr"].to_numpy(float), np.nan),
                "Size": np.where(N > 0, NT / N, np.nan)}


def _z(v, sc: dict) -> np.ndarray:
    c, s = sc.get("centre"), sc.get("scale")
    v = np.asarray(v, float)
    if c is None or s is None or not s:
        return np.full(len(v), np.nan)
    return (v - c) / s


def load_sample(sdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    feat = pd.read_csv(Path(sdir) / "features.csv.gz", dtype={"market_id": str, "condition_id": str})
    feat = feat[feat["status"] == "ok"].drop_duplicates("market_id").reset_index(drop=True)
    tr = pd.read_csv(Path(sdir) / "trades.csv.gz", usecols=["market_id", "ts", "side", "price", "size", "outcome_index", "asset"],
                     dtype={"market_id": str, "asset": str, "price": str})
    return feat, tr


def token0_map(cap_dir: Path, mids: pd.Series) -> pd.Series:
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=["market_id", "clob_token_id_0"],
                      dtype=str).drop_duplicates("market_id").set_index("market_id")["clob_token_id_0"]
    return tok.reindex(mids.astype(str))


def freeze_flow(sample: dict, cap: dict, k: int, by_slot: dict, root: Path, spec: dict, role: str, commit: str,
                cache: dict | None = None, feat_tr: tuple | None = None) -> tuple[pd.DataFrame, dict]:
    """E016 / E018 lines for one active trade sample (one line per sampled market present two-sided at capture k)."""
    f = spec["flow"]
    sdir = Path(sample["dir"])
    feat, tr = feat_tr if feat_tr is not None else load_sample(sdir)
    ser = read_series(root, cap["id"])
    cnt = {"sampled_ok": len(feat)}
    feat = feat[feat["market_id"].astype(str).isin(ser.index)].reset_index(drop=True)
    cnt["not_two_sided_at_k"] = cnt["sampled_ok"] - len(feat)
    mkt = feat["market_id"].astype(str)
    s = ser.reindex(mkt)
    origin = panel._epoch(feat["origin_utc"])
    token0 = token0_map(cap["dir"], mkt)
    token0.index = mkt.to_numpy()
    rows = flow_rows(tr, pd.Series(origin, index=mkt.to_numpy()), pd.Series(s["tick"].to_numpy(float), index=mkt.to_numpy()), token0, spec)
    W6, lag = float(f["window_s"]), float(f["lag_s"])
    n_ret = feat["n_returned"].to_numpy(float)
    oldest = rows.groupby("market_id")["ts"].min().reindex(mkt).to_numpy(float)
    full = n_ret < trade_sample.TRADE_LIMIT
    with np.errstate(invalid="ignore"):
        cov6 = full | (np.isfinite(oldest) & (oldest <= origin - W6))
        cov6l = full | (np.isfinite(oldest) & (oldest <= origin - W6 - lag))
    w6 = window_features(rows, mkt, W6, 0.0, f["train_s"])
    wl = window_features(rows, mkt, W6 + lag, lag, f["train_s"])
    with np.errstate(invalid="ignore"):
        n_post = rows[rows["ts"].to_numpy(float) >= rows["o"].to_numpy(float)].groupby("market_id").size().reindex(mkt).fillna(0).to_numpy(float)
    bid, ask, spr = s["bid"].to_numpy(float), s["ask"].to_numpy(float), s["spread"].to_numpy(float)
    mid = (bid + ask) / 2.0
    mid_p = _mid(read_series(root, by_slot.get(k - 1, {}).get("id")), mkt)
    rv = grid_rv(root, by_slot, k, mkt, int(f["rv_steps"]), int(f["rv_min_diffs"]), cache)
    end = s["end_ts"].to_numpy(float)
    hte = (end - origin) / 3600.0
    with np.errstate(divide="ignore", invalid="ignore"):
        logit = np.log(mid / (1.0 - mid))
        lhte = np.log(np.clip(hte, 1.0, None))
        x6 = np.clip(np.where(cov6, w6["imb"], np.nan), -f["x6_clip"], f["x6_clip"]) / f["x6_sd"]
        x6l = np.clip(np.where(cov6l, wl["imb"], np.nan), -f["x6_clip"], f["x6_clip"]) / f["x6_sd"]
        lN, lNl = np.log(w6["N"]), np.log(wl["N"])
        lS, lSl = np.log(w6["Size"]), np.log(wl["Size"])
    tight = tight_arr(bid, ask, spr, spec["eligibility"]["spread_max"])
    cap24 = f.get("vol24_cap")
    vol24 = s["vol24"].to_numpy(float)
    df = pd.DataFrame({
        "sample_id": sdir.name, "capture_id": cap["id"], "capture_t": cap["start"], "slot": k, "role": role,
        "market_id": mkt.to_numpy(), "event_id": s["event_id"].astype(str).to_numpy(), "t_row": origin,
        "sports": s["sports"].to_numpy(int), "neg_risk": s["neg_risk"].to_numpy(int), "stratum": feat["stratum"].to_numpy(),
        "bid_i": bid, "ask_i": ask, "mid_i": mid, "spread_i": spr, "tight_i": tight.astype(int),
        "end_ok_7h": (np.isnan(end) | (end > origin + f["end_margin_h"] * 3600.0)).astype(int),
        "vol24_i": vol24, "under_cap": (np.isfinite(vol24) & (vol24 <= (np.inf if cap24 is None else float(cap24)))).astype(int),
        "n_returned": n_ret, "n_post_origin": n_post, "cov6": cov6.astype(int), "cov6_l30": cov6l.astype(int),
        "imb6": np.where(cov6, w6["imb"], np.nan), "x6": x6, "N6": np.where(cov6, w6["N"], np.nan),
        "W": np.where(cov6, w6["W"], np.nan), "H": np.where(cov6, w6["H"], np.nan), "Hu": np.where(cov6, w6["Hu"], np.nan),
        "Wr": np.where(cov6, w6["Wr"], np.nan), "Size": np.where(cov6, w6["Size"], np.nan),
        "x6_l30": x6l, "W_l30": np.where(cov6l, wl["W"], np.nan), "H_l30": np.where(cov6l, wl["H"], np.nan),
        "N_l30": np.where(cov6l, wl["N"], np.nan), "Size_l30": np.where(cov6l, wl["Size"], np.nan),
        "zW": _z(np.where(cov6, w6["W"], np.nan), f["zW"]), "zH": _z(np.where(cov6, w6["H"], np.nan), f["zH"]),
        "zN": _z(np.where(cov6, lN, np.nan), f["zN"]), "zSize": _z(np.where(cov6, lS, np.nan), f["zSize"]),
        "zW_l30": _z(np.where(cov6l, wl["W"], np.nan), f["zW"]), "zH_l30": _z(np.where(cov6l, wl["H"], np.nan), f["zH"]),
        "zN_l30": _z(np.where(cov6l, lNl, np.nan), f["zN"]), "zSize_l30": _z(np.where(cov6l, lSl, np.nan), f["zSize"]),
        "zSPR": _z(spr, f["zSPR"]), "rv": rv, "zRV": _z(np.log(rv + 1e-4), f["zRV"]),
        "zHTE": np.nan_to_num(_z(lhte, f["zHTE"]), nan=0.0), "hte_missing": (~np.isfinite(lhte)).astype(int), "log_hte": lhte,
        "logit_mid": logit, "abs_dev": np.abs(mid - 0.5),
        "chg_1h": np.nan_to_num(s["chg_1h"].to_numpy(float)), "chg_1h_missing": (~np.isfinite(s["chg_1h"].to_numpy(float))).astype(int),
        "chg_1d": np.nan_to_num(s["chg_1d"].to_numpy(float)), "chg_1d_missing": (~np.isfinite(s["chg_1d"].to_numpy(float))).astype(int),
        "chg_1w": np.nan_to_num(s["chg_1w"].to_numpy(float)), "chg_1w_missing": (~np.isfinite(s["chg_1w"].to_numpy(float))).astype(int),
        "dprev": np.nan_to_num(mid - mid_p), "dprev_missing": (~np.isfinite(mid_p)).astype(int),
        "fee_rate": s["fee_rate"].to_numpy(float), "fee_exp": s["fee_exp"].to_numpy(float),
    })
    cnt.update(lines=len(df), covered=int(cov6.sum()), with_flow=int(np.isfinite(df["x6"]).sum()))
    return _stamp(df, spec, commit), cnt


# --- outcomes -------------------------------------------------------------------------------------------------------


def status_codes(ser: pd.DataFrame | None, st: pd.DataFrame | None, mids, capture_missing: bool) -> np.ndarray:
    """One status per unit at a target slot (section 1.5)."""
    n = len(mids)
    if capture_missing:
        return np.full(n, "capture_missing", dtype=object)
    idx = pd.Index(np.asarray(mids, dtype=str))
    in_ser = idx.isin(ser.index) if ser is not None else np.zeros(n, bool)
    code = st["st"].reindex(idx).to_numpy(object) if st is not None else np.full(n, None, dtype=object)
    return np.array(["two_sided" if a else ("absent" if (c is None or (isinstance(c, float) and np.isnan(c))) else c)
                     for a, c in zip(in_ser, code, strict=True)], dtype=object)


def target_state(by_slot: dict, j: int, now: float, spec: dict) -> str:
    """"ready" (capture exists), "missing" (absent MISSING_AFTER_S after its slot), else "pending"."""
    if j in by_slot:
        return "ready"
    return "missing" if now > slot_time(j, spec) + MISSING_AFTER_S else "pending"


def is_late(j: int, now: float, spec: dict) -> bool:
    """A freeze is refused once its earliest target slot's capture may have started (slot time - 60 s)."""
    return now >= slot_time(j, spec) - 60.0


def series_ready(root: Path, by_slot: dict, slots) -> bool:
    """Every listed slot with a complete capture already has its series file (a missing series file must never be
    read as a missing capture)."""
    return all((Path(root) / "series" / f"{by_slot[j]['id']}.csv.gz").exists() for j in slots if j in by_slot)


def _first_slot(p: Path) -> int | None:
    fr = pd.read_csv(p, usecols=["slot"], nrows=1)
    return int(fr["slot"].iloc[0]) if len(fr) else None


def outcome_h(mids, by_slot: dict, j: int, root: Path, missing: bool) -> pd.DataFrame:
    cap = by_slot.get(j)
    ser = None if missing else read_series(root, cap["id"])
    st = None if missing else read_status(root, cap["id"])
    out = pd.DataFrame({"market_id": np.asarray(mids, dtype=str)})
    out["status"] = status_codes(ser, st, mids, missing)
    out["bid"], out["ask"], out["t"] = _look(ser, mids, "bid"), _look(ser, mids, "ask"), _look(ser, mids, "t_row")
    out["cap_start"] = np.nan if missing else cap["start"]
    out["cap_id"] = None if missing else cap["id"]
    return out


def outcome_s(mids, sw: pd.DataFrame | None, missing: bool) -> pd.DataFrame:
    out = pd.DataFrame({"market_id": np.asarray(mids, dtype=str)})
    if missing or sw is None:
        out["status"] = "capture_missing" if missing else "absent"
        out["sbid"] = out["sask"] = out["s_t"] = np.nan
        return out
    two = _look(sw, mids, "s_two")
    out["status"] = np.where(two == 1, "two_sided", np.where(np.isfinite(two), "one_sided", "absent"))
    out["sbid"], out["sask"], out["s_t"] = _look(sw, mids, "sbid"), _look(sw, mids, "sask"), _look(sw, mids, "s_t")
    return out


def sweep_state(by_slot: dict, sweeps: dict, j: int, root: Path, now: float, spec: dict) -> str:
    ts = target_state(by_slot, j, now, spec)
    if ts != "ready":
        return ts
    cid = by_slot[j]["id"]
    if (Path(root) / "sweeps" / f"{cid}.csv.gz").exists():
        return "ready"
    if cid in sweeps:
        return "pending"  # complete sweep, file not written yet (next run)
    return "missing" if now > slot_time(j, spec) + MISSING_AFTER_S else "pending"


# --- the pass -------------------------------------------------------------------------------------------------------


FREEZE_KINDS = {"move": "move", "surge": "surge", "flow": "flow"}


def enabled_kinds(spec: dict) -> dict[str, bool]:
    """Which freeze kinds the pass collects (pre-pin verification finding 2). Move freezes always run (E015, E019);
    surge freezes only if E017 is in ``k_tests``; flow freezes only if E016 or E018 is. Null ``k_tests`` (DRAFT, k not
    filled) collects every kind (development only). A switched-off kind writes no frozen file and no outcome."""
    ks = spec.get("k_tests")
    if ks is None:
        return {"move": True, "surge": True, "flow": True}
    return {"move": True, "surge": "E017" in ks, "flow": "E016" in ks or "E018" in ks}


def run_once(*, snapshot_root: Path = SNAPSHOT_ROOT, sample_root: Path = SAMPLE_ROOT, sweep_root: Path = SWEEP_ROOT,
             root: Path = OUT_ROOT, spec: dict | None = None, registered_utc: str = REGISTERED_UTC, end_utc: str = END_UTC,
             now: float | None = None, max_items: int = 40, allow_late: bool = False) -> dict:
    """Series, sweeps, freezes and due outcomes for everything new. Idempotent: every file is write-once. Returns counts
    (``written`` = files written this run). ``allow_late`` is for DRY RUNS on past captures with an unpinned spec only;
    such lines are never confirmation lines and the analysis excludes late lines anyway."""
    if allow_late and spec is not None and spec.get("_pinned"):
        raise ValueError("allow_late is for dry runs with an unpinned spec only")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "run.lock", "a") as lk:
        try:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:  # another reader (cron or queue) holds the root: never race (freeze ruling 6)
            return {"status": "locked", "written": 0, "run_utc": iso(now_ts() if now is None else now)}
        return _run_locked(snapshot_root=snapshot_root, sample_root=sample_root, sweep_root=sweep_root, root=root, spec=spec,
                           registered_utc=registered_utc, end_utc=end_utc, now=now, max_items=max_items, allow_late=allow_late)


def _run_locked(*, snapshot_root: Path, sample_root: Path, sweep_root: Path, root: Path, spec: dict | None, registered_utc: str,
                end_utc: str, now: float | None, max_items: int, allow_late: bool) -> dict:
    spec = spec or load_spec()
    now = now_ts() if now is None else now
    root = Path(root)
    commit = git_commit()
    st = State(root)
    stats = {"run_utc": iso(now), "code_commit": commit, "spec_sha": spec["_sha256"][:16], "pinned": spec["_pinned"],
             "written": 0, "series": 0, "sweeps": 0, "move": 0, "surge": 0, "flow": 0, "outcomes": 0, "refused_late": 0}
    if root.exists() and dir_bytes(root) > DISK_CAP_BYTES:
        stats["status"] = "disk_cap"
        append_jsonl(root / "passes.jsonl", [{"kind": "disk_cap", **stats}])
        return stats
    t_reg, t_end = epoch(registered_utc), epoch(end_utc)
    kinds = enabled_kinds(spec)
    stats["kinds_off"] = sorted(n for n, on in kinds.items() if not on)
    by_slot = scan_captures(snapshot_root, st, spec)
    samples = scan_samples(sample_root, st) if kinds["flow"] else {}  # trade samples are read only by flow freezes
    sweeps = scan_sweeps(sweep_root, st)
    st.save()
    log: list[dict] = []
    budget = max_items
    pinned = spec["_pinned"]
    hi = t_end + SERIES_LOOKBACK_S + 13 * GRID_S
    # 1. series + status of every complete capture in [registered - 28 h, end + 28 h + 13 slots)
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg - SERIES_LOOKBACK_S <= c["start"] < hi) or budget <= 0:
            continue
        p, ps = root / "series" / f"{c['id']}.csv.gz", root / "status" / f"{c['id']}.csv.gz"
        if p.exists() and ps.exists():
            continue
        rows, dup = load_rows(c["dir"])
        ser, sta = series_frame(rows, load_ext(c["dir"]), spec)
        del rows
        w1 = write_once_csv(p, ser)
        w2 = write_once_csv(ps, sta)
        if w1 or w2:
            stats["series"] += 1
            budget -= 1
            log.append({"kind": "series", "id": c["id"], "slot": k, "rows": len(ser), "status_rows": len(sta), **dup,
                        "sidecar": bool((ser["sports"] != -1).any()) if len(ser) else None, "written_utc": iso(now_ts())})
    # 2. sweep-1 quotes of the same passes
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg - SERIES_LOOKBACK_S <= c["start"] < hi) or budget <= 0 or c["id"] not in sweeps:
            continue
        p = root / "sweeps" / f"{c['id']}.csv.gz"
        if p.exists():
            continue
        sw = sweep_frame(sweeps[c["id"]]["dir"], c["dir"])
        if write_once_csv(p, sw):
            stats["sweeps"] += 1
            budget -= 1
            log.append({"kind": "sweep", "id": c["id"], "sweep_id": sweeps[c["id"]]["id"], "rows": len(sw), "written_utc": iso(now_ts())})
    # 3. capture freezes (origins in [registered, end))
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        role = role_of(c["start"], registered_utc, end_utc, pinned)
        for kind, first_h, need in (("move", min(spec["move"]["horizons"]), (k - 1, k)),
                                    ("surge", min(spec["surge"]["horizons"]), (k - 13, k - 2, k - 1, k))):
            if not kinds[kind]:
                continue
            p = root / kind / "frozen" / f"{c['id']}.csv.gz"
            late_p = p.with_name(p.name.replace(".csv.gz", ".late.csv.gz"))
            if p.exists() or late_p.exists() or budget <= 0:
                continue
            if not allow_late and is_late(k + first_h, now, spec):
                stats["refused_late"] += 1
                write_once_csv(late_p, pd.DataFrame({"late": [1], "checked_utc": [iso(now)]}))
                log.append({"kind": f"{kind}_refused_late", "id": c["id"], "slot": k, "written_utc": iso(now_ts())})
                continue
            if k - 1 not in by_slot:
                if target_state(by_slot, k - 1, now, spec) == "pending":
                    continue
                write_once_csv(p.with_name(p.name.replace(".csv.gz", ".noprev.csv.gz")), pd.DataFrame({"noprev": [1]}))
                log.append({"kind": f"{kind}_no_previous_slot", "id": c["id"], "slot": k})
                continue
            if not series_ready(root, by_slot, need):
                continue
            ser_k, ser_p = read_series(root, c["id"]), read_series(root, by_slot[k - 1]["id"])
            if kind == "move":
                units, events, cnt = freeze_move(ser_k, ser_p, c, k, spec, role, commit)
                pe = root / "events" / "frozen" / f"{c['id']}.csv.gz"
                ok = write_once_csv(p, units)
                write_once_csv(pe, events)
            else:
                ser_p2 = read_series(root, by_slot.get(k - 2, {}).get("id"))
                ser_p13 = read_series(root, by_slot.get(k - 13, {}).get("id"))
                units, cnt = freeze_surge(ser_k, ser_p, ser_p2, ser_p13, c, k, spec, role, commit)
                ok = write_once_csv(p, units)
            if ok:
                stats[kind] += 1
                budget -= 1
                log.append({"kind": f"{kind}_frozen", "id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
    # 4. flow freezes (every active sample of an in-window capture; none when flow is switched off: samples is empty)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    rv_cache: dict = {}
    for sid in sorted(samples):
        k = slot_by_id.get(samples[sid]["snapshot_id"])
        if k is None:
            continue
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        p = root / "flow" / "frozen" / f"{sid}.csv.gz"
        late_p = p.with_name(p.name.replace(".csv.gz", ".late.csv.gz"))
        if p.exists() or late_p.exists() or budget <= 0:
            continue
        if not allow_late and is_late(k + spec["flow"]["horizon_slots"], now, spec):
            stats["refused_late"] += 1
            write_once_csv(late_p, pd.DataFrame({"late": [1], "checked_utc": [iso(now)]}))
            log.append({"kind": "flow_refused_late", "id": sid, "slot": k, "written_utc": iso(now_ts())})
            continue
        if not series_ready(root, by_slot, range(k - int(spec["flow"]["rv_steps"]), k + 1)) or not (root / "series" / f"{c['id']}.csv.gz").exists():
            continue
        fr, cnt = freeze_flow(samples[sid], c, k, by_slot, root, spec, role_of(c["start"], registered_utc, end_utc, pinned), commit, rv_cache)
        if write_once_csv(p, fr):
            stats["flow"] += 1
            budget -= 1
            log.append({"kind": "flow_frozen", "id": sid, "capture_id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
    # 5. outcomes: status + quote at k + h (series files) and the sweep-1 quote at k + s
    plan = {"move": (spec["move"]["horizons"], spec["move"]["sweep_tags"]), "surge": (spec["surge"]["horizons"], []),
            "flow": ([spec["flow"]["horizon_slots"]], spec["flow"]["sweep_tags"])}
    for kind, (hs, ss) in plan.items():
        if not kinds[kind]:
            continue  # a switched-off kind writes no outcome
        fdir = root / kind / "frozen"
        for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
            if p.name.endswith((".late.csv.gz", ".noprev.csv.gz")) or budget <= 0:
                continue
            fid = p.name[:-7]
            todo = [("h", h) for h in hs if not (root / kind / "outcomes" / f"{fid}.h{h}.csv.gz").exists()]
            todo += [("s", s) for s in ss if not (root / kind / "outcomes" / f"{fid}.s{s}.csv.gz").exists()]
            if not todo:
                continue
            k = _first_slot(p)
            if k is None:
                continue
            mids = None
            for typ, h in todo:
                if budget <= 0:
                    break
                j = k + h
                state = target_state(by_slot, j, now, spec) if typ == "h" else sweep_state(by_slot, sweeps, j, root, now, spec)
                if state == "pending" or (typ == "h" and state == "ready" and not series_ready(root, by_slot, (j,))):
                    continue
                if mids is None:
                    mids = pd.read_csv(p, usecols=["market_id"], dtype={"market_id": str})["market_id"].to_numpy()
                if typ == "h":
                    out = outcome_h(mids, by_slot, j, root, state == "missing")
                else:
                    out = outcome_s(mids, None if state == "missing" else read_sweep(root, by_slot[j]["id"]), state == "missing")
                if write_once_csv(root / kind / "outcomes" / f"{fid}.{typ}{h}.csv.gz", out):
                    stats["outcomes"] += 1
                    budget -= 1
                    log.append({"kind": f"{kind}_outcome", "id": fid, "tag": f"{typ}{h}", "target_slot": j, "target": state,
                                "rows": len(out), "written_utc": iso(now_ts())})
    stats["written"] = sum(stats[k] for k in ("series", "sweeps", "move", "surge", "flow", "outcomes"))
    stats["status"] = "wrote" if stats["written"] else "nothing_new"
    for r in log:
        r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
    append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
    return stats


# --- operational counts (never reads a price, a move or a target) -----------------------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def ops_stats(root: Path = OUT_ROOT) -> dict:
    root = Path(root)
    out: dict = {"root": str(root), "bytes": dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "sweeps", "move/frozen", "events/frozen", "surge/frozen", "flow/frozen",
                "move/outcomes", "surge/outcomes", "flow/outcomes"):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith((".late.csv.gz", ".noprev.csv.gz"))]),
                    "late": len([f for f in files if f.name.endswith(".late.csv.gz")]),
                    "noprev": len([f for f in files if f.name.endswith(".noprev.csv.gz")])}
    roles, classes, status = {}, {}, {}
    for sub, cols in (("move/frozen", ["role", "cls", "geom", "sports"]), ("events/frozen", ["role", "untraded"]),
                      ("surge/frozen", ["role", "S", "A", "SM", "neg_risk"]), ("flow/frozen", ["role", "sports"])):
        d = root / sub
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith((".late.csv.gz", ".noprev.csv.gz")):
                continue
            s = _read_ops(f, cols)
            for c in s.columns:
                tgt = roles if c == "role" else classes
                for k, v in s[c].value_counts().items():
                    tgt[f"{sub}:{c}:{k}"] = tgt.get(f"{sub}:{c}:{k}", 0) + int(v)
    for sub in ("move/outcomes", "surge/outcomes", "flow/outcomes"):
        d = root / sub
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            tag = f.name[:-7].rsplit(".", 1)[-1]
            s = _read_ops(f, ["status"])  # status only (never a quote)
            for k, v in s["status"].value_counts().items():
                status[f"{sub}:{tag}:{k}"] = status.get(f"{sub}:{tag}:{k}", 0) + int(v)
    out.update(line_roles=roles, line_classes=classes, outcome_status_counts=status)
    return out


# --- censuses C1-C4 (counts only; pre-window data; no target, no capture after the one classified) -------------------


def _days_of(by_slot: dict, days: list[str]) -> list[int]:
    return [k for k, c in sorted(by_slot.items()) if datetime.fromtimestamp(c["start"], UTC).strftime("%Y-%m-%d") in days]


def project_events(ids_day1: set, ids_all: set, n_days: int = 2, horizon_days: int = 21) -> float:
    """Distinct-event projection to 21 days (an estimate): E_2d + (E_2d - E_day1) x 19, the day-2 new-event rate carried
    forward (spec census_inputs.projection)."""
    e1, e2 = len(ids_day1), len(ids_all)
    return float(e2 + (e2 - e1) * (horizon_days - n_days))


def mde_eff(n_p: float, n_t: float, a: dict) -> float:
    """Planning MDE of E015 from the effective counts (units in markets holding both classes), in price units."""
    if n_p <= 0 or n_t <= 0:
        return float("inf")
    return a["t_sum"] * a["sd_c"] * math.sqrt(1.0 / n_p + 1.0 / n_t) * math.sqrt(a["deff_event"]) * a["day_factor"]


def census_captures(*, snapshot_root: Path = SNAPSHOT_ROOT, work: Path, days: list[str] | None = None,
                    spec: dict | None = None) -> dict:
    """C1 (E015 classes), C3 (E017 surges), C4 (E019 breadth): counts of origin-side classes and labels on the captures
    of ``days`` (default spec census days), written under ``work`` only. Reads captures k - 13 .. k of each census
    capture k, never a capture after it; no target, no P&L."""
    spec = spec or load_spec(sha=None)
    days = days or spec["census_inputs"]["C1_C3_C4_days_utc"]
    work = Path(work)
    st = State(work)
    by_slot = scan_captures(snapshot_root, st, spec)
    ks = _days_of(by_slot, days)
    if not ks:
        return {"error": "no census captures", "days": days}
    need = sorted({j for k in ks for j in (k - 13, k - 2, k - 1, k) if j in by_slot})
    for j in need:
        p = work / "series" / f"{by_slot[j]['id']}.csv.gz"
        if not p.exists():
            rows, _ = load_rows(by_slot[j]["dir"])
            ser, sta = series_frame(rows, load_ext(by_slot[j]["dir"]), spec)
            write_once_csv(p, ser)
            write_once_csv(work / "status" / f"{by_slot[j]['id']}.csv.gz", sta)
            del rows
    U, E, S, per_cap = [], [], [], []
    for k in ks:
        c = by_slot[k]
        if k - 1 not in by_slot:
            per_cap.append({"capture": c["id"], "skipped": "no previous slot"})
            continue
        ser_k, ser_p = read_series(work, c["id"]), read_series(work, by_slot[k - 1]["id"])
        u, e, cm = freeze_move(ser_k, ser_p, c, k, spec, ROLE_UNREG, "census")
        s, cs = freeze_surge(ser_k, ser_p, read_series(work, by_slot.get(k - 2, {}).get("id")),
                             read_series(work, by_slot.get(k - 13, {}).get("id")), c, k, spec, ROLE_UNREG, "census")
        u["day"] = e["day"] = s["day"] = datetime.fromtimestamp(c["start"], UTC).strftime("%Y-%m-%d")
        U.append(u.drop(columns=["bid_k", "ask_k", "bid_p", "ask_p"]))
        E.append(e)
        S.append(s[["market_id", "event_id", "day", "sports", "neg_risk", "crypto", "S", "A", "SM", "lag_unknown", "x_km1_missing"]])
        per_cap.append({"capture": c["id"], "move": cm, "surge": cs})
    U, E, S = (pd.concat(v, ignore_index=True) if v else pd.DataFrame() for v in (U, E, S))
    nd = len(days)
    scale = 21.0 / nd
    out = {"days": days, "captures": [by_slot[k]["id"] for k in ks], "per_capture": per_cap,
           "C1": census_c1(U, spec, scale, days), "C3": census_c3(S, spec, scale, days), "C4": census_c4(E, spec, scale, days)}
    return out


def census_c1(U: pd.DataFrame, spec: dict, scale: float, days: list[str]) -> dict:
    g = spec["census_gates"]["C1_E015"]
    ns = U[U["sports"] == 0]
    P = (ns["cls"] == "quote_only") & (ns["geom"] == "parallel")
    T = ns["cls"] == "traded"
    both = ns.assign(P=P.astype(int), T=T.astype(int)).groupby("market_id")[["P", "T"]].sum()
    bm = both[(both["P"] > 0) & (both["T"] > 0)].index
    in_b = ns["market_id"].isin(bm)
    n_p_eff, n_t_eff = float((P & in_b).sum() * scale), float((T & in_b).sum() * scale)
    # permutation strata (market x UTC day, >= 4 contrasted units): share of contrasted units permuted (finding 12)
    con = ns[P | T]
    sz = con.groupby(["market_id", "day"]).size()
    permuted = float(sz[sz >= spec["gates"]["perm_min_stratum"]].sum() / max(len(con), 1))
    # u per pass (descriptive, 7.1): up share of non-sports movers per capture
    up = ns.groupby("capture_id")["x"].apply(lambda v: float((v > 0).mean())) if len(ns) else pd.Series(dtype=float)
    traded_share = float(T.mean()) if len(ns) else float("nan")
    ltp_absent = float((ns["ltp_k"].isna() & ns["ltp_p"].isna()).mean()) if len(ns) else float("nan")
    res = {
        "movers": {"all": len(U), "non_sports": len(ns), "sports": int((U["sports"] == 1).sum()), "sidecar_missing": int((U["sports"] == -1).sum())},
        "by_class_geom_non_sports": {f"{a}|{b}": int(v) for (a, b), v in ns.groupby(["cls", "geom"]).size().items()},
        "by_class_sports": {str(a): int(v) for a, v in U[U["sports"] == 1]["cls"].value_counts().items()},
        "V_minus_share_non_sports": float((ns["dvol"] < -spec["move"]["vol_tol"]).mean()) if len(ns) else None,
        "never_traded_share_non_sports": float((ns["cls"] == "never_traded").mean()) if len(ns) else None,
        "ltp_absent_both_share_non_sports": ltp_absent, "traded_share_non_sports": traded_share,
        "parallel": int(P.sum()), "traded": int(T.sum()), "parallel_21d": float(P.sum() * scale), "traded_21d": float(T.sum() * scale),
        "markets_both": len(bm), "parallel_eff_21d": n_p_eff, "traded_eff_21d": n_t_eff,
        "mde_eff_c": mde_eff(n_p_eff, n_t_eff, g["mde_assumptions"]) * 100.0,
        "perm_strata_share_permuted": permuted,
        "up_share_per_pass": {"n": int(len(up)), "min": float(up.min()) if len(up) else None, "max": float(up.max()) if len(up) else None,
                              "iqr": float(up.quantile(0.75) - up.quantile(0.25)) if len(up) else None},
    }
    lo, hi = g["traded_share"]
    res["gate_E015"] = {"parallel_21d": res["parallel_21d"] >= g["parallel_21d"], "traded_21d": res["traded_21d"] >= g["traded_21d"],
                        "traded_share": bool(lo <= traded_share <= hi), "ltp_absent": bool(ltp_absent <= g["ltp_absent_max"]),
                        "mde_eff": bool(res["mde_eff_c"] <= g["mde_eff_max_c"] * 100.0)}
    res["gate_E015"]["pass"] = all(res["gate_E015"].values())
    return res


def census_c3(S: pd.DataFrame, spec: dict, scale: float, days: list[str]) -> dict:
    g = spec["census_gates"]["C3_E017"]
    pop = S[(S["neg_risk"] == 1) & (S["sports"] == 0)]
    std = S[(S["neg_risk"] == 0) & (S["sports"] == 0)]
    a = pop[pop["A"] == 1]
    ev1 = set(a.loc[a["day"] == days[0], "event_id"])
    res = {"units": {"all": len(S), "primary_neg_risk_non_sports": len(pop), "standalone_non_sports": len(std),
                     "sports": int((S["sports"] == 1).sum()), "sidecar_missing": int((S["sports"] == -1).sum())},
           "primary": {"S": int(pop["S"].sum()), "A": int(pop["A"].sum()), "SM": int(pop["SM"].sum()),
                       "lag_unknown": int(pop["lag_unknown"].sum()), "baseline": int((pop["S"] == 0).sum()),
                       "A_events": int(a["event_id"].nunique()), "x_km1_missing_share": float(pop["x_km1_missing"].mean()) if len(pop) else None},
           "standalone": {"A": int(std["A"].sum()), "SM": int(std["SM"].sum())},
           "neg_risk_share_of_non_sports_A": float(pop["A"].sum() / max(int(S[(S["sports"] == 0)]["A"].sum()), 1))}
    res["A_21d"] = float(pop["A"].sum() * scale)
    res["A_events_21d"] = project_events(ev1, set(a["event_id"]), len(days))
    a_ = g["mde_assumptions"]
    ne = res["A_events_21d"]
    res["mde_plan_c"] = (a_["t_sum"] * a_["sd_c"] / math.sqrt(ne) * a_["within"] * a_["block_factor"] * 100.0) if ne > 0 else float("inf")
    res["gate_E017"] = {"A_21d": res["A_21d"] >= g["A_21d"], "events_21d": res["A_events_21d"] >= g["events_21d"],
                        "mde_plan": bool(res["mde_plan_c"] <= g["mde_max"] * 100.0)}  # pessimistic planning MDE <= floor (freeze fix 4)
    res["gate_E017"]["pass"] = all(res["gate_E017"].values())
    return res


def census_c4(E: pd.DataFrame, spec: dict, scale: float, days: list[str]) -> dict:
    g = spec["census_gates"]["C4_E019"]
    e = spec["e019"]
    un = E[(E["untraded"] == 1) & (E["n_qo_mov"] > 0)]
    hi_m = un["b"] >= e["high_b"] - 1e-12
    high = un[hi_m]
    fam = high["skey"].value_counts()
    top_share = float(fam.iloc[0] / fam.sum()) if len(fam) else 0.0
    top_family = str(fam.index[0]) if len(fam) else None
    excl = top_share > spec["labels"]["series_concentration"]
    top_is_crypto = bool(len(fam) and int(high.loc[high["skey"] == top_family, "crypto"].max()) == 1)

    def gate_on(pop: pd.DataFrame) -> dict:
        h = pop[pop["b"] >= e["high_b"] - 1e-12]
        lo = pop[pop["b"] < e["low_b"]]
        both_ev = set(h["event_id"]) & set(lo["event_id"])
        d1 = pop[pop["day"] == days[0]]
        both1 = set(d1.loc[d1["b"] >= e["high_b"] - 1e-12, "event_id"]) & set(d1.loc[d1["b"] < e["low_b"], "event_id"])
        return {"high": len(h), "low": len(lo), "middle": len(pop) - len(h) - len(lo), "high_21d": float(len(h) * scale),
                "events_both": len(both_ev), "events_both_21d": project_events(both1, both_ev, len(days)),
                "clusters_all": int(pop["skey"].nunique()), "clusters_high": int(h["skey"].nunique())}

    prim = un
    if excl:
        prim = un[(un["crypto"] != 1) & (un["skey"] != (None if top_is_crypto else top_family))]
    res = {"event_intervals": len(E), "untraded_with_mover": len(un), "traded_intervals": int((E["untraded"] == 0).sum()),
           "all": gate_on(un), "top_family_high": top_family, "top_family_high_share": top_share, "top_family_is_crypto": top_is_crypto,
           "crypto_share_high": float((high["crypto"] == 1).mean()) if len(high) else None,
           "empty_slug_event_share": float(E["skey"].astype(str).str.startswith("event:").groupby(E["event_id"]).first().mean()) if len(E) else None,
           "top_families_high": [{"skey": str(k), "n": int(v), "crypto": int(high.loc[high["skey"] == k, "crypto"].max())} for k, v in fam.head(20).items()],
           "exclude_crypto": bool(excl), "exclude_family": (None if (not excl or top_is_crypto) else top_family),
           "primary": gate_on(prim)}
    p = res["primary"]
    res["gate_E019"] = {"high_21d": p["high_21d"] >= g["high_21d"], "events_both_21d": p["events_both_21d"] >= g["events_both_21d"],
                        "clusters_high_census": p["clusters_high"] >= g["clusters_high_census"]}  # the analysis floor, unprojected
    a_ = g["mde_assumptions"]
    nh = p["high_21d"]
    res["mde_plan_c"] = (a_["t_sum"] * a_["sd_c"] / math.sqrt(nh) * a_["within"] * math.sqrt(a_["deff_series"]) * a_["day_factor"] * 100.0) if nh > 0 else float("inf")
    res["gate_E019"]["mde_plan"] = bool(res["mde_plan_c"] <= g["mde_max"] * 100.0)  # pessimistic planning MDE <= floor (freeze fix 4)
    res["gate_E019"]["pass"] = all(res["gate_E019"].values())
    return res


def census_flow(*, seal: Path, sample_roots: list[Path], snapshot_root: Path = SNAPSHOT_ROOT, work: Path,
                spec: dict | None = None, verify: bool = True) -> dict:
    """C2 (E016 / E018): on the sealed trade samples only (sha256-verified), with the series of their captures and of
    slots k - 12 .. k written under ``work``. Pre-origin rows only; prints distributions, truncation by volume24hr (fixes
    V*), the walked construct (grid distance, the >= 4 decimal rows), side / touch agreement and the gates."""
    spec = spec or load_spec(sha=None)
    sl = json.loads(Path(seal).read_text())
    work = Path(work)
    st = State(work)
    by_slot = scan_captures(snapshot_root, st, spec)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    f = spec["flow"]
    zero = {k: {"centre": 0.0, "scale": 1.0} for k in ("zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE")}
    spec_c = json.loads(json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}))
    spec_c["flow"].update(zero)
    spec_c["flow"]["vol24_cap"] = None
    spec_c["_sha256"] = spec["_sha256"]
    frames, rowstats, bad = [], [], []
    hist_bins = [0.0, 1e-9, 1e-6, 1e-5, 1e-4, 1e-3, 1.0]
    hist = np.zeros(len(hist_bins) - 1, int)
    agree = {"walked": [0, 0], "on_grid": [0, 0]}
    tot = {"rows_pre_origin": 0, "signed": 0, "ge4dec": 0, "ge4dec_tick_known": 0, "ge4dec_within_1e-4": 0, "tick_known": 0,
           "walked": 0, "size_lt_0.02": 0}
    cache: dict = {}
    for sid in sl["samples"]:
        sdir = next((Path(r) / sid for r in sample_roots if (Path(r) / sid / "trades.csv.gz").exists()), None)
        if sdir is None:
            bad.append({"sample": sid, "error": "not found"})
            continue
        if verify:
            for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz"):
                want = (sl["files"].get(f"data-dumps/research_lab/trade_samples/{sid}/{fn}") or {}).get("sha256")
                if want is None or sha256_file(sdir / fn) != want:
                    bad.append({"sample": sid, "file": fn, "error": "sha256 mismatch or not sealed"})
        if any(b.get("sample") == sid for b in bad):
            continue
        m = _manifest(sdir / "manifest.json")
        k = slot_by_id.get(m.get("snapshot_id"))
        if k is None:
            bad.append({"sample": sid, "error": "capture not found"})
            continue
        for j in range(k - int(f["rv_steps"]), k + 1):
            if j in by_slot and not (work / "series" / f"{by_slot[j]['id']}.csv.gz").exists():
                rows, _ = load_rows(by_slot[j]["dir"])
                ser, sta = series_frame(rows, load_ext(by_slot[j]["dir"]), spec)
                write_once_csv(work / "series" / f"{by_slot[j]['id']}.csv.gz", ser)
                write_once_csv(work / "status" / f"{by_slot[j]['id']}.csv.gz", sta)
                del rows
        feat, tr = load_sample(sdir)
        fr, _ = freeze_flow({"dir": sdir}, by_slot[k], k, by_slot, work, spec_c, ROLE_UNREG, "census", cache, (feat, tr))
        frames.append(fr)
        # row-level construct checks (pre-origin signed rows, price read as text)
        ser = read_series(work, by_slot[k]["id"])
        ok = feat[feat["market_id"].astype(str).isin(ser.index)]
        mk = ok["market_id"].astype(str)
        org = pd.Series(panel._epoch(ok["origin_utc"]), index=mk.to_numpy())
        tok = token0_map(by_slot[k]["dir"], mk)
        tok.index = mk.to_numpy()
        rr = flow_rows(tr[tr["market_id"].astype(str).isin(mk)], org, ser["tick"], tok, spec)
        pre = rr[rr["ts"].to_numpy(float) < rr["o"].to_numpy(float)]
        tot["rows_pre_origin"] += len(pre)
        sg = pre[pre["sg"] != 0]
        tot["signed"] += len(sg)
        frac = sg["price"].astype(str).str.strip().str.split(".").str[1].fillna("").str.rstrip("0")
        ge4 = frac.str.len().to_numpy() >= 4
        known = sg["walk_known"].to_numpy() == 1
        dist = sg["dist"].to_numpy(float)
        tot["ge4dec"] += int(ge4.sum())
        tot["ge4dec_tick_known"] += int((ge4 & known).sum())
        tot["ge4dec_within_1e-4"] += int((ge4 & known & (dist < f["walk_min_dist"])).sum())
        tot["tick_known"] += int(known.sum())
        tot["walked"] += int(sg["walked"].sum())
        tot["size_lt_0.02"] += int((pd.to_numeric(sg["size"], errors="coerce").to_numpy(float) < 0.02).sum())
        hist += np.histogram(dist[ge4 & known], bins=hist_bins)[0]
        # side / touch agreement (finding 11): quote of the most recent capture row at most 300 s before the fill
        imp = np.zeros(len(sg))
        for jj in range(k - 3, k + 1):
            sj = read_series(work, by_slot.get(jj, {}).get("id"))
            if sj is None:
                continue
            mm = sg["market_id"].astype(str).to_numpy()
            tq, bq, aq = _look(sj, mm, "t_row"), _look(sj, mm, "bid"), _look(sj, mm, "ask")
            oi = pd.to_numeric(sg["outcome_index"], errors="coerce").to_numpy(float)
            p0 = np.where(oi == 1, 1.0 - sg["p"].to_numpy(float), sg["p"].to_numpy(float))
            ts = sg["ts"].to_numpy(float)
            with np.errstate(invalid="ignore"):
                near = np.isfinite(tq) & (ts >= tq) & (ts - tq <= 300.0) & np.isin(oi, (0.0, 1.0))
                v = np.where(p0 >= aq - 1e-6, 1.0, np.where(p0 <= bq + 1e-6, -1.0, 0.0))
            imp = np.where(near & (v != 0), v, imp)
        has = imp != 0
        wk = sg["walked"].to_numpy(bool)
        same = sg["sg"].to_numpy(float) == imp
        for lab_, msk in (("walked", has & wk & known), ("on_grid", has & ~wk & known)):
            agree[lab_][0] += int((same & msk).sum())
            agree[lab_][1] += int(msk.sum())
        rowstats.append({"sample": sid, "capture": by_slot[k]["id"], "rows_pre_origin": len(pre), "signed": len(sg)})
    if not frames:
        return {"error": "no usable sample", "bad": bad}
    F = pd.concat(frames, ignore_index=True)
    base = F[(F["tight_i"] == 1) & (F["end_ok_7h"] == 1)]
    cand = base[(base["cov6"] == 0) | (np.nan_to_num(base["N6"].to_numpy(float)) > 0)]
    trunc = pd.DataFrame({"vol24_i": cand["vol24_i"].to_numpy(float), "trunc6": (cand["cov6"].to_numpy(int) == 0).astype(int)})
    vstar = vol24_cap_rule(trunc, float(f["vol24_cap_max_trunc_share"]))
    cov = base[(base["cov6"] == 1) & (np.nan_to_num(base["N6"].to_numpy(float)) > 0)]
    cov = cov[cov["vol24_i"] <= vstar] if np.isfinite(vstar) else cov

    def ms(v) -> dict:
        v = np.asarray(v, float)
        v = v[np.isfinite(v)]
        if not len(v):
            return {"centre": None, "scale": None, "n": 0}
        return {"centre": float(np.mean(v)), "scale": float(np.std(v, ddof=1)) if len(v) > 1 else None, "n": int(len(v)),
                "terciles": [float(x) for x in np.quantile(v, [1 / 3, 2 / 3])]}

    with np.errstate(divide="ignore", invalid="ignore"):
        scales = {"zW": ms(cov["W"]), "zH": ms(cov["H"]), "zN": ms(np.log(cov["N6"])), "zSize": ms(np.log(cov["Size"])),
                  "zSPR": ms(cov["spread_i"]), "zRV": ms(np.log(cov["rv"] + 1e-4)),
                  "zHTE": ms(np.where(cov["hte_missing"] == 0, cov["log_hte"], np.nan))}
    Wv, Hv = cov["W"].to_numpy(float), cov["H"].to_numpy(float)
    w_int = np.isfinite(Wv) & (Wv > 0) & (Wv < 1)
    h_int = np.isfinite(Hv) & (Hv > 0) & (Hv < 1)
    zz = np.isfinite(Wv) & np.isfinite(Hv)
    corr = float(np.corrcoef(Wv[zz], Hv[zz])[0, 1]) if zz.sum() > 2 else float("nan")
    r2_w, r2_h = within_market_r2(cov, "zW"), within_market_r2(cov, "zH")  # donor ruling 2026-10-20 (c): reported, not a gate
    n_days = len({str(s)[:8] for s in sl["samples"]})
    scale21 = 21.0 / max(n_days, 1)
    ag = {k: (v[0] / v[1] if v[1] else None) for k, v in agree.items()}
    gap = (ag["on_grid"] - ag["walked"]) if None not in ag.values() else None
    g6, g8 = spec["census_gates"]["C2_E016"], spec["census_gates"]["C2_E018"]
    ge4_on = tot["ge4dec_within_1e-4"] / tot["ge4dec_tick_known"] if tot["ge4dec_tick_known"] else None
    walked_share = tot["walked"] / tot["tick_known"] if tot["tick_known"] else None
    res = {"seal": str(seal), "samples_used": [r["sample"] for r in rowstats], "bad": bad, "rows": rowstats, "totals": tot,
           "ge4dec_distance_hist": {"bins": ["[0,1e-9)", "[1e-9,1e-6)", "[1e-6,1e-5)", "[1e-5,1e-4)", "[1e-4,1e-3)", "[1e-3,1)"],
                                    "counts": hist.tolist()},
           "ge4dec_on_grid_share": ge4_on, "walked_row_share": walked_share,
           "agreement": {"walked": ag["walked"], "on_grid": ag["on_grid"], "n_walked": agree["walked"][1], "n_on_grid": agree["on_grid"][1],
                         "gap_on_grid_minus_walked": gap},
           "trunc6": {"rows": len(trunc), "truncated": int(trunc["trunc6"].sum()), "share": float(trunc["trunc6"].mean()) if len(trunc) else None},
           "vol24_cap": vstar, "covered_units": len(cov), "covered_units_21d": float(len(cov) * scale21),
           "W_interior_units_21d": float(w_int.sum() * scale21), "H_interior_share": float(h_int.mean()) if len(cov) else None,
           "corr_W_H": corr, "r2_x6zW_on_controlled": r2_w, "r2_x6zH_on_controlled": r2_h, "scales": scales, "events": int(cov["event_id"].nunique())}
    n_min = int(g6["agreement_min_rows"])
    ag_ok = agree["walked"][1] >= n_min and agree["on_grid"][1] >= n_min  # fail closed below 500 rows per arm (freeze ruling 3)
    res["agreement"]["min_rows_per_arm"], res["agreement"]["enough_rows"] = n_min, bool(ag_ok)
    res["gate_E016"] = {"vol24_cap_defined": bool(not math.isnan(vstar)),  # NaN V* fails closed (freeze fix 2)
                        "covered_W_interior_21d": res["W_interior_units_21d"] >= g6["covered_W_interior_21d"],
                        "walked_share": bool(walked_share is not None and walked_share >= g6["walked_share_min"]),
                        "ge4dec_on_grid": bool(ge4_on is not None and ge4_on <= g6["ge4dec_on_grid_max"]),
                        "agreement_gap": bool(ag_ok and gap is not None and gap <= g6["agreement_gap_max"])}
    res["gate_E016"]["pass"] = all(res["gate_E016"].values())
    res["gate_E018"] = {"H_interior": bool(res["H_interior_share"] is not None and res["H_interior_share"] >= g8["H_interior_share_min"]),
                        "corr": bool(np.isfinite(corr) and abs(corr) <= g8["corr_zW_zH_max"]),
                        "agreement_gap": bool(ag_ok and gap is not None and gap <= g8["agreement_gap_max"])}
    res["gate_E018"]["pass"] = all(res["gate_E018"].values())
    return res


def within_market_r2(cov: pd.DataFrame, mod: str) -> float | None:
    """Within-market R^2 of the tested interaction ``x6 * mod`` on the interactions (with main effects) and ``x6`` that
    the E016 / E018 model controls for (x6*zN, zN, x6*zSPR, zSPR, x6*zSize, zSize, x6*zHTE, zHTE, x6*zRV, zRV, x6): all
    variables demeaned by market first (donor ruling 2026-10-20, c). None if fewer than 20 finite rows.

    Disclosure (section 13.13, reported only): this demeans by the FULL-sample market mean, whereas the model uses
    expanding-past demeaning; and it runs on the census sample, not on the gate sample. It is a descriptive collinearity
    figure, not a gate input."""
    d = cov.reset_index(drop=True)
    x6 = d["x6"].to_numpy(float)
    ctl = {"x6": x6}
    for z in ("zN", "zSPR", "zSize", "zHTE", "zRV"):
        zv = d[z].to_numpy(float)
        ctl[z], ctl[f"x6*{z}"] = zv, x6 * zv
    cols = pd.DataFrame({**ctl, "_y": x6 * d[mod].to_numpy(float)})
    cols = cols[np.all(np.isfinite(cols.to_numpy()), axis=1)]
    if len(cols) < 20:
        return None
    mk = d.loc[cols.index, "market_id"].to_numpy()
    c = cols - cols.groupby(mk).transform("mean")
    y = c.pop("_y").to_numpy(float)
    tss = float(y @ y)
    if tss <= 1e-18:
        return None
    X = c.to_numpy(float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    return float(1.0 - (r @ r) / tss)


def vol24_cap_rule(trunc: pd.DataFrame, max_share: float) -> float:
    """V*: the largest origin volume24hr v such that, among census rows with volume24hr <= v, the share of truncated
    6 h windows is <= ``max_share`` (+inf if the whole census meets it; unknown volume24hr rows unused)."""
    t = trunc[np.isfinite(trunc["vol24_i"])].sort_values("vol24_i", kind="mergesort")
    if t.empty:
        return float("nan")
    v = t["vol24_i"].to_numpy(float)
    share = np.cumsum(t["trunc6"].to_numpy(float)) / np.arange(1, len(t) + 1)
    last = np.r_[v[1:] != v[:-1], True]
    ok = last & (share <= max_share)
    if ok[-1]:
        return float("inf")
    return float(v[ok].max()) if ok.any() else float("nan")


def cleanup_census(work: Path) -> None:
    shutil.rmtree(work, ignore_errors=True)
