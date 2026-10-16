# ruff: noqa: E501
"""Creative batch 1 (CB1): snapshot extractor and capture-id lists (docs/research_lab/CREATIVE_BATCH_1.md).

Sections
    1. constants and small helpers
    2. per-capture filtering (neg-risk members, post-end favourites), sidecar and sweep joins
    3. extractor driver (``extract``): idempotent by ``capture_id``, wall-clock self-limiting, locked
    4. Gamma ``/events/{id}`` member counts (``event_members.csv.gz``)
    5. frozen capture-id lists with sha256 (``freeze_list``, ``load_capture_list``)
    (CB1 analysis code is added below section 5 later.)

Operational contract (§2.11, host owner): the extractor runs inside the live 2-hourly collector pass.
It is read-only on snapshots, sweeps and everything E011 reads; it writes only under ``extract_root``;
every file is written tmp + rename and the manifest is rewritten last for each capture; one capture is
read at a time in chunks (peak RSS well under 500 MB); it stops cleanly at its wall-clock budget and
leaves the remaining captures for the next run. ``cb1_extract`` is not a trial kind: no trials logged.
"""

from __future__ import annotations

import contextlib
import fcntl
import gzip
import hashlib
import io
import json
import os
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forecast
from . import history_backfill as hb

# --- 1. constants and helpers ------------------------------------------------------------------

EXTRACTOR_VERSION = "cb1-extract-v2"  # v2 = CB2 additions (cb2_extract tables, event_text); CB1 tables unchanged
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
EXTRACT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "cb1_extract"
CB2_EXTRACT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "cb2_extract"
DATA_DUMPS = forecast.ROOT / "data-dumps"
T2_DEV_START = "2026-10-11T12:00:00Z"
T2_DEV_END = "2026-10-24T00:00:00Z"

CB1_START = "2026-10-11T12:00:00Z"  # first sidecar capture; floor of every CB1 snapshot read
T_DEV_END = "2026-10-17T00:00:00Z"
T_REP_END = "2026-11-09T00:00:00Z"
LIST_WINDOW_END = {"dev": T_DEV_END, "rep": T_REP_END}
POSTEND_MIN_TOUCH = 0.95
CHUNK_ROWS = 50_000
EVENT_REFRESH_DAYS = 7
DEFAULT_BUDGET_S = 420.0  # all-new: well inside the pass line's `timeout 600`
GAMMA_EVENT_URL = "https://gamma-api.polymarket.com/events/{event_id}"

NEGRISK_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "neg_risk_market_id", "event_id", "market_id",
    "clob_token_id_0", "best_bid", "best_ask", "spread", "last_trade_price", "closed", "active",
    "accepting_orders", "neg_risk_other", "event_neg_risk_augmented", "volume_num", "fee_schedule",
    "fee_category", "end_date", "fees_enabled",
    "sw1_best_ask", "sw1_ask_size_1", "sw2_best_ask", "sw2_ask_size_1",
]
POSTEND_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "event_id", "clob_token_id_0",
    "fav_token", "best_bid", "best_ask", "touch", "last_trade_price", "end_date", "closed", "active",
    "accepting_orders", "volume_num", "fees_enabled", "fee_schedule", "fee_category",
]
RUNG_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "event_id", "clob_token_id_0",
    "best_bid", "best_ask", "spread", "last_trade_price", "closed", "active", "accepting_orders", "end_date",
]
RUNG_LIST_NAME = "rung_list.json"  # B3 rung list (q0029 output) copied into the extract root
RUNG_SEAL = forecast.ROOT / "docs" / "research_lab" / "seals" / "cb1_b3_rung_list.json"
EVENT_COLUMNS = ["neg_risk_market_id", "event_id", "member_count", "n_open", "n_closed",
                 "fetched_utc", "http_status"]
# CB2 (CREATIVE_BATCH_2.md section 4.3). event_text lives beside event_members in the CB1 root.
EVENT_TEXT_COLUMNS = ["neg_risk_market_id", "event_id", "fetched_utc", "title", "slug",
                      "member_market_ids", "group_item_titles"]
CB2_SWEEP_COLUMNS = ["sw1_best_bid", "sw1_best_ask", "sw1_bid_size_1", "sw1_ask_size_1"]
LADDER_COLUMNS = [  # shared by ladder_candidates/ (text-free) and ladders/
    "capture_id", "capture_start_utc", "received_utc", "market_id", "event_id", "best_bid", "best_ask",
    "last_trade_price", "closed", "active", "accepting_orders", "end_date", "volume_num", "fee_schedule",
    "fee_category", *CB2_SWEEP_COLUMNS,
]
REWARD_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "event_id", "clob_rewards",
    "rewards_daily_rate", "rewards_start", "rewards_end", "rewards_max_spread", "rewards_min_size",
    "competitive", "best_bid", "best_ask", "spread", "last_trade_price", "volume_num", "fee_category",
    "accepting_orders", *CB2_SWEEP_COLUMNS,
]
CB2_TABLES = ("ladder_candidates", "ladders", "rewards")
CB2_EXCLUDED_CATEGORIES = frozenset({"sports", "weather"})
LADDER_LIST_NAME = "ladder_list.json"

_ROW_STR = ["capture_id", "capture_start_utc", "received_utc", "market_id", "event_id",
            "clob_token_id_0", "neg_risk_market_id", "closed", "active", "end_date"]
_ROW_NUM = ["best_bid", "best_ask", "spread", "last_trade_price", "binary", "neg_risk_other",
            "event_neg_risk_augmented"]
_EXT_STR = ["market_id", "fee_schedule", "fee_category"]
_EXT_NUM = ["accepting_orders", "fees_enabled", "volume_num"]
_SWEEP_NUM = ["best_ask", "ask_size_1"]


class ExtractLocked(RuntimeError):
    """Another extractor run holds the extract-root lock."""


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(s: str) -> datetime:
    return forecast._parse_ts(s)


def sha256_stream(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".tmp_{os.getpid()}_{path.name}")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def _atomic_write_json(path: Path, obj: Any) -> None:
    _atomic_write_bytes(path, json.dumps(obj, indent=1, sort_keys=True).encode())


def write_csv_gz(path: Path, df: pd.DataFrame, columns: list[str]) -> None:
    """Deterministic gzip (mtime 0), tmp + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.reindex(columns=columns)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz, \
            io.TextIOWrapper(gz, encoding="utf-8", newline="") as tw:
        out.to_csv(tw, index=False)
    _atomic_write_bytes(path, buf.getvalue())


def _is_false(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower() == "false"


# --- 2. per-capture filtering and joins ----------------------------------------------------------


def _header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def _chunks(path: Path, want_str: list[str], want_num: list[str]) -> Iterator[pd.DataFrame]:
    head = _header(path)
    use = [c for c in [*want_str, *want_num] if c in head]
    dtype: dict[str, Any] = {c: str for c in want_str if c in head}
    dtype.update({c: "float64" for c in want_num if c in head})
    for ch in pd.read_csv(path, usecols=use, dtype=dtype, chunksize=CHUNK_ROWS):
        for c in [*want_str, *want_num]:
            if c not in ch.columns:
                ch[c] = np.nan
        yield ch


def filter_rows(path: Path, capture_id: str, capture_start: str
                ) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Stream ``rows.csv.gz``: neg-risk members and post-end favourites only. Returns
    ``(negrisk, postend, n_rows)``; first receipt per market_id kept (as the collector's dedup)."""
    neg: list[pd.DataFrame] = []
    post: list[pd.DataFrame] = []
    n = 0
    for ch in _chunks(path, _ROW_STR, _ROW_NUM):
        n += len(ch)
        nrm = ch["neg_risk_market_id"].fillna("").astype(str).str.strip()
        sel = ch[nrm != ""]
        if len(sel):
            neg.append(sel.assign(capture_id=capture_id, capture_start_utc=capture_start))
        bid, ask = ch["best_bid"], ch["best_ask"]
        mid = (bid + ask) / 2.0
        fav1 = mid >= 0.5  # favourite = YES (token 0) when mid >= 0.5, else the NO side (token 1)
        touch = np.where(fav1, ask, 1.0 - bid)
        ok = ((ch["binary"] == 1) & _is_false(ch["closed"]) & bid.notna() & ask.notna()
              & (touch >= POSTEND_MIN_TOUCH))
        cand = ch[ok.to_numpy()].copy()
        if len(cand):
            cand["touch"] = touch[ok.to_numpy()]
            cand["fav_token"] = np.where(fav1[ok.to_numpy()], 0, 1)
            end = pd.to_datetime(cand["end_date"], utc=True, errors="coerce", format="ISO8601")
            rec = pd.to_datetime(cand["received_utc"], utc=True, errors="coerce", format="ISO8601")
            keep = (end <= rec).to_numpy()
            cand = cand[keep]
            if len(cand):
                post.append(cand.assign(capture_id=capture_id, capture_start_utc=capture_start))

    def _cat(parts: list[pd.DataFrame]) -> pd.DataFrame:
        if not parts:
            return pd.DataFrame(columns=[*_ROW_STR, *_ROW_NUM, "touch", "fav_token"])
        return pd.concat(parts, ignore_index=True).drop_duplicates("market_id")

    return _cat(neg), _cat(post), n


def read_sidecar(path: Path, market_ids: set[str]) -> pd.DataFrame:
    """Needed sidecar fields for ``market_ids`` only (chunked, first row per market_id)."""
    parts = []
    for ch in _chunks(path, _EXT_STR, _EXT_NUM):
        sub = ch[ch["market_id"].isin(market_ids)]
        if len(sub):
            parts.append(sub)
    if not parts:
        return pd.DataFrame(columns=[*_EXT_STR, *_EXT_NUM])
    return pd.concat(parts, ignore_index=True).drop_duplicates("market_id")


def sweep_index(sweep_root: Path) -> dict[str, dict[int, Path]]:
    """``snapshot_id -> {series_index: sweep dir}`` over complete sweeps (earliest start per index),
    the same pass-join rule as ``bounce_decomp.load_sweep_mid`` (manifest ``snapshot_id``)."""
    idx: dict[str, dict[int, tuple[str, Path]]] = {}
    root = Path(sweep_root)
    if not root.exists():
        return {}
    for m in sorted(root.glob("*/manifest.json")):
        try:
            man = json.loads(m.read_text())
        except (OSError, ValueError):
            continue
        if man.get("state") != "complete" or not man.get("snapshot_id"):
            continue
        k = int(man.get("series_index", 0))
        started = str(man.get("started_utc", ""))
        cur = idx.setdefault(man["snapshot_id"], {})
        if k not in cur or started < cur[k][0]:
            cur[k] = (started, m.parent)
    return {sid: {k: v[1] for k, v in d.items()} for sid, d in idx.items()}


def read_sweep(sweep_dir: Path, market_ids: set[str]) -> pd.DataFrame | None:
    """``market_id -> best_ask, ask_size_1`` for ``market_ids``; None if the rows file is gone."""
    p = Path(sweep_dir) / "rows.csv.gz"
    if not p.exists():
        return None
    parts = []
    for ch in _chunks(p, ["market_id"], _SWEEP_NUM):
        sub = ch[ch["market_id"].isin(market_ids)]
        if len(sub):
            parts.append(sub)
    if not parts:
        return pd.DataFrame(columns=["market_id", *_SWEEP_NUM]).set_index("market_id")
    return pd.concat(parts, ignore_index=True).drop_duplicates("market_id").set_index("market_id")


def join_sweeps(neg: pd.DataFrame, sweeps: dict[int, Path] | None) -> tuple[pd.DataFrame, dict]:
    """Add ``sw1_*``/``sw2_*`` (blank if not swept). Returns the frame and a per-sweep status."""
    status: dict[str, str] = {}
    ids = set(neg["market_id"]) if len(neg) else set()
    for name, k in (("sw1", 0), ("sw2", 1)):
        for c in _SWEEP_NUM:
            neg[f"{name}_{c}"] = np.nan
        d = (sweeps or {}).get(k)
        if d is None:
            status[name] = "absent"
            continue
        sw = read_sweep(d, ids) if ids else pd.DataFrame()
        if sw is None:
            status[name] = "file_missing"  # archived/rotated: blank, counted (not an error)
            continue
        status[name] = Path(d).name
        for c in _SWEEP_NUM:
            neg[f"{name}_{c}"] = neg["market_id"].map(sw[c]) if len(sw) else np.nan
    return neg, status


def rung_gate(extract_root: Path, seal_path: Path = RUNG_SEAL) -> dict:
    """Fail-closed gate for the B3 ``rungs/`` tables. Open only if the rung list is in ``extract_root``,
    the committed seal exists and its sha256 equals the list file's sha256. Never raises.
    Returns ``{open, reason, sha256, as_of_utc, ids}``."""
    g: dict[str, Any] = {"open": False, "reason": None, "sha256": None, "as_of_utc": None, "ids": set()}
    lp = Path(extract_root) / RUNG_LIST_NAME
    try:
        if not lp.exists():
            g["reason"] = "no_rung_list"
            return g
        sp = Path(seal_path)
        if not sp.exists():
            g["reason"] = "no_committed_seal"
            return g
        want = str(json.loads(sp.read_text()).get("sha256", "")).strip().lower()
        got = sha256_stream(lp)
        g["sha256"] = got
        if not want or want != got:
            g["reason"] = "sha_mismatch"
            g["error"] = True
            return g
        doc = json.loads(lp.read_text())
        g["as_of_utc"] = str(doc["as_of_utc"])
        g["ids"] = {str(r["market_id"]) for L in doc["ladders"] for r in L["rungs"]}
        _ts(g["as_of_utc"])
        g["open"] = True
        g["reason"] = "ok"
    except Exception as exc:  # fail closed, never fail the pass
        g.update(open=False, reason=f"gate_error:{type(exc).__name__}", error=True, ids=set())
    return g


def extract_rungs(cap: dict, gate: dict, extract_root: Path) -> dict | None:
    """Write ``rungs/<capture_id>.csv.gz`` for one capture if the gate is open and the capture starts at
    or after the list's as-of time; returns the manifest ``rungs`` entry, else None (nothing written)."""
    if not gate.get("open") or _ts(cap["started_utc"]) < _ts(gate["as_of_utc"]):
        return None
    cdir = Path(cap["dir"])
    cid, start = cap["capture_id"], cap["started_utc"]
    ids = gate["ids"]
    rows_p = forecast.require_local(cdir / "rows.csv.gz")
    parts = []
    for ch in _chunks(rows_p, ["market_id", "received_utc", "event_id", "clob_token_id_0", "closed", "active",
                               "end_date"], ["best_bid", "best_ask", "spread", "last_trade_price"]):
        sub = ch[ch["market_id"].isin(ids)]
        if len(sub):
            parts.append(sub)
    df = (pd.concat(parts, ignore_index=True).drop_duplicates("market_id") if parts
          else pd.DataFrame(columns=RUNG_COLUMNS))
    ext_p = cdir / "rows_ext.csv.gz"
    df["accepting_orders"] = np.nan
    if len(df) and ext_p.exists():
        ext = read_sidecar(ext_p, set(df["market_id"]))
        if len(ext):
            df["accepting_orders"] = df["market_id"].map(ext.set_index("market_id")["accepting_orders"])
    df["capture_id"], df["capture_start_utc"] = cid, start
    write_csv_gz(extract_root / "rungs" / f"{cid}.csv.gz", df, RUNG_COLUMNS)
    found = set(df["market_id"])
    return {"status": "written", "list_sha256": gate["sha256"], "n_listed": len(ids),
            "n_found": len(found), "missing": sorted(ids - found), "extracted_utc": utc_now()}


def _note_gate(manifest: dict, gate: dict) -> None:
    """Record the gate state in the manifest (rewritten only when it changes)."""
    note = {"reason": gate["reason"], "error": bool(gate.get("error")), "sha256": gate.get("sha256")}
    if manifest.get("rungs_gate") != note:
        manifest["rungs_gate"] = note


def extract_capture(cap: dict, sweeps: dict[int, Path] | None, extract_root: Path,
                    gate: dict | None = None) -> dict:
    """Extract one complete capture into ``negrisk/`` and ``postend/``. Raises ArchivedDataError if
    the rows file (or a listed sidecar) is not on this host. Returns the manifest entry."""
    cdir = Path(cap["dir"])
    cid = cap["capture_id"]
    start = cap["started_utc"]
    rows_p = forecast.require_local(cdir / "rows.csv.gz")
    ext_p = cdir / "rows_ext.csv.gz"
    if ext_p.exists():
        ext_status = "ok"
    elif (cdir / "ext_manifest.json").exists():
        forecast.require_local(ext_p)  # sidecar existed: archived, not "absent"
        ext_status = "ok"
    else:
        ext_status = "none"  # pre-sidecar capture: sidecar fields blank
    neg, post, n_rows = filter_rows(rows_p, cid, start)
    need = set(neg["market_id"]) | set(post["market_id"]) if (len(neg) or len(post)) else set()
    ext = read_sidecar(ext_p, need) if (ext_status == "ok" and need) else pd.DataFrame()
    for df in (neg, post):
        for c in [*_EXT_NUM, "fee_schedule", "fee_category"]:
            if len(df):
                df[c] = df["market_id"].map(ext.set_index("market_id")[c]) if len(ext) else np.nan
    sw_status: dict[str, str] = {}
    if len(neg):
        neg, sw_status = join_sweeps(neg, sweeps)
    else:
        neg = pd.DataFrame(columns=NEGRISK_COLUMNS)
        sw_status = dict.fromkeys(("sw1", "sw2"), "n/a")
    if not len(post):
        post = pd.DataFrame(columns=POSTEND_COLUMNS)
    write_csv_gz(extract_root / "negrisk" / f"{cid}.csv.gz", neg, NEGRISK_COLUMNS)
    write_csv_gz(extract_root / "postend" / f"{cid}.csv.gz", post, POSTEND_COLUMNS)
    rungs = extract_rungs(cap, gate, extract_root) if gate else None
    return {
        **({"rungs": rungs} if rungs else {}),
        "status": "extracted", "started_utc": start, "rows_sha256": sha256_stream(rows_p),
        "rows_ext_sha256": sha256_stream(ext_p) if ext_status == "ok" else None,
        "ext_status": ext_status, "n_rows": n_rows, "n_negrisk": int(len(neg)),
        "n_postend": int(len(post)), "sweeps": sw_status,
        "extractor_version": EXTRACTOR_VERSION, "git_commit": forecast._git("rev-parse", "HEAD"),
        "extracted_utc": utc_now(),
    }


# --- 3. driver ------------------------------------------------------------------------------------


def _load_manifest(extract_root: Path) -> dict:
    p = Path(extract_root) / "manifest.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"extractor_version": EXTRACTOR_VERSION, "captures": {}}


@contextlib.contextmanager
def _lock(extract_root: Path):
    extract_root.mkdir(parents=True, exist_ok=True)
    fh = open(extract_root / ".lock", "w")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ExtractLocked(str(extract_root)) from exc
        yield
    finally:
        fh.close()


def candidates(snapshot_root: Path, manifest: dict, *, since: str, mode: str) -> list[dict]:
    """Complete captures with start >= ``since`` not yet extracted. all-new: newest first (the
    current pass is never starved by a backlog); backfill: oldest first."""
    lo = _ts(since)
    caps = [c for c in forecast.list_complete_captures(snapshot_root) if c["_start"] >= lo]
    done = manifest["captures"]
    todo = [c for c in caps if done.get(c["capture_id"], {}).get("status") != "extracted"]
    return todo[::-1] if mode == "all-new" else todo


def extract(
    snapshot_root: Path = SNAPSHOT_ROOT,
    sweep_root: Path = SWEEP_ROOT,
    extract_root: Path = EXTRACT_ROOT,
    *,
    mode: str = "all-new",
    backfill_from: str | None = None,
    rps: float = 2.0,
    max_requests: int = 300,
    budget_s: float = DEFAULT_BUDGET_S,
    transport: hb.Transport | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], str] = utc_now,
    write_dev_list: bool = False,
    rung_seal: Path = RUNG_SEAL,
    cb2_root: Path | None = None,
    cb2_tables: tuple[str, ...] = ("ladder_candidates", "ladders", "rewards"),
) -> dict:
    """Extract every complete capture not yet extracted (idempotent by ``capture_id``).

    ``mode='all-new'``: a listed-but-missing rows file is recorded ``missing`` and the run continues.
    ``mode='backfill'``: it raises ``ArchivedDataError`` (loud). Stops cleanly when the next capture
    would not fit in ``budget_s`` (estimated from the slowest capture so far)."""
    if mode not in ("all-new", "backfill"):
        raise ValueError(mode)
    since = backfill_from if mode == "backfill" else CB1_START
    if mode == "backfill" and not backfill_from:
        raise ValueError("backfill needs backfill_from")
    snapshot_root, sweep_root, extract_root = Path(snapshot_root), Path(sweep_root), Path(extract_root)
    t0 = clock()
    summary: dict[str, Any] = {"cb1_extract": EXTRACTOR_VERSION, "mode": mode, "extracted": 0,
                               "missing": 0, "stopped": None}
    with _lock(extract_root):
        manifest = _load_manifest(extract_root)
        man0 = json.dumps(manifest, sort_keys=True)
        gate = rung_gate(extract_root, rung_seal)
        _note_gate(manifest, gate)
        summary["rungs_gate"] = gate["reason"]
        todo = candidates(snapshot_root, manifest, since=since, mode=mode)
        sidx = sweep_index(sweep_root) if todo else {}
        slowest = 0.0
        newly: list[str] = []
        for cap in todo:
            if clock() - t0 + 1.3 * slowest > budget_s:
                summary["stopped"] = "budget"
                break
            c0 = clock()
            cid = cap["capture_id"]
            try:
                entry = extract_capture(cap, sidx.get(cid), extract_root, gate)
            except forecast.ArchivedDataError:
                if mode == "backfill":
                    raise
                entry = {"status": "missing", "started_utc": cap["started_utc"],
                         "extractor_version": EXTRACTOR_VERSION, "extracted_utc": now()}
                summary["missing"] += 1
            else:
                summary["extracted"] += 1
                newly.append(cid)
            manifest["captures"][cid] = entry
            manifest["extractor_version"] = EXTRACTOR_VERSION
            _atomic_write_json(extract_root / "manifest.json", manifest)  # manifest last
            slowest = max(slowest, clock() - c0)
        if mode == "backfill" and gate["open"]:  # (re)extract rungs for already-extracted captures
            n_r = 0
            for cap in forecast.list_complete_captures(snapshot_root):
                ent = manifest["captures"].get(cap["capture_id"], {})
                if (ent.get("status") != "extracted" or ent.get("rungs", {}).get("status") == "written"
                        or cap["_start"] < _ts(gate["as_of_utc"]) or cap["_start"] < _ts(since)):
                    continue
                if clock() - t0 + 1.3 * slowest > budget_s:
                    summary["stopped"] = "budget"
                    break
                c0 = clock()
                ent["rungs"] = extract_rungs(cap, gate, extract_root)
                n_r += 1
                manifest["captures"][cap["capture_id"]] = ent
                _atomic_write_json(extract_root / "manifest.json", manifest)
                slowest = max(slowest, clock() - c0)
            summary["rungs_backfilled"] = n_r
        if json.dumps(manifest, sort_keys=True) != man0:
            _atomic_write_json(extract_root / "manifest.json", manifest)
        summary["remaining"] = len(candidates(snapshot_root, manifest, since=since, mode=mode)) \
            - summary["missing"]
        summary["remaining"] = max(summary["remaining"], 0)
        summary["max_capture_s"] = round(slowest, 2)
        if cb2_root is not None and mode == "all-new":  # CB2 tables (v2): never fails the pass
            try:
                summary["cb2"] = run_cb2_tables(
                    snapshot_root, sweep_root, Path(cb2_root), tables=cb2_tables, mode="all-new",
                    since=T2_DEV_START, deadline=t0 + 0.7 * budget_s, clock=clock, now=now)
            except Exception as exc:
                summary["cb2"] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
        # event member counts: after the captures, within the same wall-clock budget
        scan = None if mode == "backfill" else 6
        try:
            summary["events"] = fetch_event_members(
                extract_root, rps=rps, max_requests=max_requests, deadline=t0 + budget_s,
                transport=transport, clock=clock, sleep=sleep, now=now, scan_last=scan,
                write_text=bool(cb2_root is not None and mode == "all-new"))
        except Exception as exc:  # never fail the pass for the metadata fetch
            summary["events"] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
        summary["backfill_complete"] = bool(mode == "backfill" and summary["remaining"] == 0
                                            and summary["stopped"] is None)
        if write_dev_list and summary["backfill_complete"]:
            until = min(_ts(now()), _ts(T_DEV_END)).strftime("%Y-%m-%dT%H:%M:%SZ")
            summary["dev_list"] = freeze_list("dev", extract_root, snapshot_root=snapshot_root,
                                              from_utc=backfill_from, until=until, now=now,
                                              _locked=True)["sha256"]
    summary["elapsed_s"] = round(clock() - t0, 2)
    return summary


# --- 4. Gamma event member counts -----------------------------------------------------------------


def _read_event_members(extract_root: Path) -> pd.DataFrame:
    p = extract_root / "event_members.csv.gz"
    if not p.exists():
        return pd.DataFrame(columns=EVENT_COLUMNS)
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def event_members_asof(extract_root: Path, asof_utc: str | None = None) -> pd.DataFrame:
    """Latest ``event_members`` row per ``neg_risk_market_id`` with ``fetched_utc <= asof_utc``
    (all rows when ``asof_utc`` is None). The file is append-only, so the member count that applied
    at a capture time is the last refresh at or before it; ids first fetched after ``asof_utc``
    are absent (missing stays missing). ISO-8601 UTC strings of equal format sort lexically."""
    df = _read_event_members(extract_root)
    if asof_utc is not None:
        df = df[df["fetched_utc"] <= asof_utc]
    return (df.sort_values(["neg_risk_market_id", "fetched_utc"], kind="stable")
            .drop_duplicates("neg_risk_market_id", keep="last").reset_index(drop=True))


def _targets(extract_root: Path, scan_last: int | None) -> dict[str, str]:
    """``neg_risk_market_id -> event_id`` over the last ``scan_last`` negrisk tables (all if None)."""
    files = sorted((extract_root / "negrisk").glob("*.csv.gz"))
    if scan_last is not None:
        files = files[-scan_last:]
    out: dict[str, str] = {}
    for f in files:
        df = pd.read_csv(f, usecols=["neg_risk_market_id", "event_id"], dtype=str).dropna()
        for nrm, ev in zip(df["neg_risk_market_id"], df["event_id"], strict=True):
            out.setdefault(nrm, ev)
    return out


def fetch_event_members(
    extract_root: Path, *, rps: float, max_requests: int, deadline: float,
    transport: hb.Transport | None, clock: Callable[[], float], sleep: Callable[[float], None],
    now: Callable[[], str], scan_last: int | None, write_text: bool = False,
) -> dict:
    """Fetch Gamma ``/events/{id}`` once per new ``neg_risk_market_id`` (stale after 7 days;
    new ids first) within ``max_requests`` and the wall-clock ``deadline``. Metadata only."""
    targets = _targets(extract_root, scan_last)
    cached = event_members_asof(extract_root)  # latest row per id; history stays in the file
    have = dict(zip(cached["neg_risk_market_id"], cached["fetched_utc"], strict=True))
    cutoff = _ts(now()) - timedelta(days=EVENT_REFRESH_DAYS)
    new = sorted(k for k in targets if k not in have)
    stale = sorted(k for k in targets if k in have and _ts(have[k]) < cutoff)
    todo = [*new, *stale]
    res = {"targets": len(targets), "to_fetch": len(todo), "fetched": 0, "requests": 0}
    if not todo or max_requests <= 0:
        return res
    lim = hb.Limiter(transport or hb.httpx_transport(), rps=rps, sleep=sleep, clock=clock)
    fresh: dict[str, dict] = {}
    texts: list[dict] = []
    fails = 0
    for nrm in todo:
        if res["requests"] >= max_requests or clock() + 1.0 / rps + 5.0 > deadline:
            res["stopped"] = "budget"
            break
        ev = targets[nrm]
        try:
            status, data = lim.get(GAMMA_EVENT_URL.format(event_id=ev), {})
        except RuntimeError:
            res["requests"] = lim.requests
            fails += 1
            if fails >= 3:
                res["stopped"] = "repeated_errors"
                break
            continue
        res["requests"] = lim.requests
        row = {"neg_risk_market_id": nrm, "event_id": ev, "fetched_utc": now(),
               "http_status": str(status), "member_count": "", "n_open": "", "n_closed": ""}
        if status == 200 and isinstance(data, dict) and isinstance(data.get("markets"), list):
            ms = [m for m in data["markets"] if isinstance(m, dict)]
            row.update(member_count=str(len(ms)),
                       n_closed=str(sum(1 for m in ms if m.get("closed") is True)),
                       n_open=str(sum(1 for m in ms if m.get("closed") is not True)))
            if write_text:  # same response, no extra request (CB2 4.3); text as first seen, disclosed
                texts.append({
                    "neg_risk_market_id": nrm, "event_id": ev, "fetched_utc": row["fetched_utc"],
                    "title": str(data.get("title") or ""), "slug": str(data.get("slug") or ""),
                    "member_market_ids": json.dumps([str(m.get("id", "")) for m in ms]),
                    "group_item_titles": json.dumps([str(m.get("groupItemTitle") or "") for m in ms])})
        fresh[nrm] = row
        res["fetched"] += 1
    if fresh:
        # append-only: earlier refresh rows are never overwritten (each row carries fetched_utc)
        merged = pd.concat([_read_event_members(extract_root), pd.DataFrame(list(fresh.values()))],
                           ignore_index=True)
        write_csv_gz(extract_root / "event_members.csv.gz",
                     merged.sort_values(["neg_risk_market_id", "fetched_utc"], kind="stable"),
                     EVENT_COLUMNS)
    if texts:  # append-only, like event_members; never rewrites an earlier row
        p = extract_root / "event_text.csv.gz"
        old = (pd.read_csv(p, dtype=str, keep_default_na=False) if p.exists()
               else pd.DataFrame(columns=EVENT_TEXT_COLUMNS))
        write_csv_gz(p, pd.concat([old, pd.DataFrame(texts)], ignore_index=True)
                     .sort_values(["neg_risk_market_id", "fetched_utc"], kind="stable"), EVENT_TEXT_COLUMNS)
        res["event_text_rows"] = len(texts)
    return res


# --- 5. frozen capture-id lists --------------------------------------------------------------------


def ids_sha256(ids: list[str]) -> str:
    """sha256 of the sorted ids joined by newline (independent of status and creation time)."""
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def freeze_list(kind: str, extract_root: Path = EXTRACT_ROOT, *,
                snapshot_root: Path = SNAPSHOT_ROOT, from_utc: str | None, until: str,
                now: Callable[[], str] = utc_now, _locked: bool = False) -> dict:
    """Write ``capture_lists/<kind>.json``: ids of captures with ``from <= started < until`` that the
    extract knows (extracted or missing) or that are complete in the snapshot root. An existing list
    may only be extended (all its ids must remain), never rewritten with fewer or different ids."""
    if kind not in LIST_WINDOW_END:
        raise ValueError(kind)
    if from_utc is None:
        if kind != "dev":
            raise ValueError("rep list needs --from (T_rep_start)")
        from_utc = CB1_START
    extract_root = Path(extract_root)
    lo, hi = _ts(from_utc), _ts(until)
    ctx = contextlib.nullcontext() if _locked else _lock(extract_root)
    with ctx:
        man = _load_manifest(extract_root)["captures"]
        known: dict[str, str] = {cid: e["started_utc"] for cid, e in man.items()
                                 if e.get("started_utc")}
        for c in forecast.list_complete_captures(snapshot_root):
            known.setdefault(c["capture_id"], c["started_utc"])
        ids = sorted(cid for cid, st in known.items() if lo <= _ts(st) < hi)
        path = extract_root / "capture_lists" / f"{kind}.json"
        prev = None
        if path.exists():
            prev = json.loads(path.read_text())
            gone = set(prev["capture_ids"]) - set(ids)
            if gone or prev["from_utc"] != from_utc:
                raise ValueError(f"{path.name}: an existing list can only be extended "
                                 f"(missing {sorted(gone)[:3]}, from {prev['from_utc']})")
            if ids == prev["capture_ids"] and prev["until"] == until:
                return prev
        out = {
            "kind": kind, "from_utc": from_utc, "until": until,
            "final": bool(hi >= _ts(LIST_WINDOW_END[kind])), "capture_ids": ids, "n": len(ids),
            "sha256": ids_sha256(ids), "sha256_rule": "sha256('\\n'.join(sorted(capture_ids)))",
            "missing_ids": sorted(i for i in ids if man.get(i, {}).get("status") != "extracted"),
            "previous_sha256": prev["sha256"] if prev else None, "created_utc": now(),
            "extractor_version": EXTRACTOR_VERSION,
        }
        _atomic_write_json(path, out)
        return out


def load_capture_list(extract_root: Path, kind: str) -> dict:
    """Read a frozen list and verify its sha256; the list's ``missing_ids`` are to be counted by the
    caller, never silently dropped."""
    d = json.loads((Path(extract_root) / "capture_lists" / f"{kind}.json").read_text())
    if ids_sha256(d["capture_ids"]) != d["sha256"]:
        raise ValueError(f"capture list {kind}: sha256 mismatch")
    return d


def read_extract_table(extract_root: Path, table: str, capture_id: str) -> pd.DataFrame:
    """One capture's ``negrisk``/``postend`` table; fails loudly if the listed file is missing."""
    p = forecast.require_local(Path(extract_root) / table / f"{capture_id}.csv.gz")
    return pd.read_csv(p, dtype={"market_id": str, "event_id": str, "neg_risk_market_id": str,
                                 "clob_token_id_0": str, "capture_id": str})


def ladder_gate(cb2_root: Path) -> dict:
    """Gate for ``ladders/``. Opens iff ``<cb2_root>/ladder_list.json`` loads and its sha256 matches its
    ``.sha256`` file. ``visible`` maps market_id -> (visible_from epoch, strict) from the list's own version rule
    (v1: captures >= T2_DEV_START; a rung added by v>=2: captures strictly after that version's listed_utc).
    Any failure keeps the gate closed with ``error`` set (the pass never crashes)."""
    closed = {"open": False, "visible": {}, "as_of_utc": None}
    p = Path(cb2_root) / LADDER_LIST_NAME
    if not p.exists():
        return {**closed, "reason": "no_ladder_list"}
    try:
        from . import cb2_structural as cs  # lazy: cb2_structural imports this module
        shap = p.with_name(LADDER_LIST_NAME + ".sha256")
        if not shap.exists():
            raise cs.LadderListError(f"{shap.name} missing")
        doc = cs.load_ladder_list(p, expected_sha256=shap.read_text().strip())
        vis: dict[str, tuple[float, bool]] = {}
        for r in doc["rungs"]:
            v = (cs._ep(r["visible_from_utc"]), bool(r["strict"]))
            vis[str(r["market_id"])] = min(vis.get(str(r["market_id"]), v), v)
        return {"open": True, "reason": f"ladder_list_v{doc['version']}", "visible": vis,
                "as_of_utc": T2_DEV_START, "sha256": doc["sha256"]}
    except Exception as e:  # noqa: BLE001 - malformed/mismatched list must close the gate, not crash
        return {**closed, "reason": f"ladder_list_error: {type(e).__name__}: {e}", "error": True}


# --- 6. CB2 extractor v2 tables (docs/research_lab/CREATIVE_BATCH_2.md section 4.3) -----------------
#
# Own root (``cb2_extract``) and manifest; CB1 tables are never touched. ``ladder_candidates/`` is
# text-free (no question, slug or description) and needs no ladder list: every non-sports,
# non-weather, non-neg-risk market of captures with start < T2_DEV_END. ``rewards/<date>`` is data
# only (CH16 preservation). Everything is idempotent by capture_id and table.


def _dir_gb(path: Path) -> float:
    path = Path(path)
    if not path.exists():
        return 0.0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e9


def _load_cb2_manifest(cb2_root: Path) -> dict:
    p = Path(cb2_root) / "manifest.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"extractor_version": EXTRACTOR_VERSION, "captures": {}}


def rewards_capture_ids(caps: list[dict]) -> set[str]:
    """First complete capture at or after 12:00Z of each UTC day (caps sorted by start)."""
    first: dict[str, str] = {}
    for c in caps:
        st = c["_start"]
        if st.hour >= 12:
            first.setdefault(st.strftime("%Y-%m-%d"), c["capture_id"])
    return set(first.values())


def _parse_rewards(txt: Any) -> tuple[float, str, str]:
    """(sum of rewardsDailyRate, earliest startDate, latest endDate) from the raw ``clobRewards`` JSON;
    NaN / blank when absent or unparseable. The raw text is kept beside these in the table."""
    try:
        arr = json.loads(str(txt))
        if isinstance(arr, dict):
            arr = [arr]
        rates = [float(a["rewardsDailyRate"]) for a in arr if a.get("rewardsDailyRate") not in (None, "")]
        starts = sorted(str(a["startDate"]) for a in arr if a.get("startDate"))
        ends = sorted(str(a["endDate"]) for a in arr if a.get("endDate"))
        return (sum(rates) if rates else float("nan"), starts[0] if starts else "",
                ends[-1] if ends else "")
    except Exception:
        return float("nan"), "", ""


def read_sweep_book(sweep_dir: Path, market_ids: set[str]) -> pd.DataFrame | None:
    """First-sweep touch and size-1 fields for ``market_ids`` (index market_id); None if rotated."""
    p = Path(sweep_dir) / "rows.csv.gz"
    if not p.exists():
        return None
    want = ["best_bid", "best_ask", "bid_size_1", "ask_size_1"]
    parts = []
    for ch in _chunks(p, ["market_id"], want):
        sub = ch[ch["market_id"].isin(market_ids)]
        if len(sub):
            parts.append(sub)
    if not parts:
        return pd.DataFrame(columns=["market_id", *want]).set_index("market_id")
    return pd.concat(parts, ignore_index=True).drop_duplicates("market_id").set_index("market_id")


def _read_ext_cols(path: Path, want_str: list[str], want_num: list[str]) -> pd.DataFrame:
    parts = [ch[[*want_str, *want_num]] for ch in _chunks(path, want_str, want_num)]
    if not parts:
        return pd.DataFrame(columns=[*want_str, *want_num]).set_index("market_id")
    return pd.concat(parts, ignore_index=True).drop_duplicates("market_id").set_index("market_id")


def extract_cb2_capture(cap: dict, sweeps: dict[int, Path] | None, cb2_root: Path, need: set[str],
                        *, ladder_visible: dict[str, Any] | None = None) -> dict:
    """Write the requested CB2 tables for one capture. Raises ArchivedDataError if the rows file (or an
    existing sidecar) is not on this host. Returns ``{table: manifest entry}`` plus shared fields."""
    cdir = Path(cap["dir"])
    cid, start = cap["capture_id"], cap["started_utc"]
    rows_p = forecast.require_local(cdir / "rows.csv.gz")
    ext_p = cdir / "rows_ext.csv.gz"
    if ext_p.exists():
        ext_status = "ok"
    elif (cdir / "ext_manifest.json").exists():
        forecast.require_local(ext_p)
        ext_status = "ok"
    else:
        ext_status = "none"
    e_str = ["market_id", "fee_schedule", "fee_category"]
    e_num = ["accepting_orders", "volume_num"]
    if "rewards" in need:
        e_str += ["clob_rewards"]
        e_num += ["rewards_max_spread", "rewards_min_size", "competitive"]
    ext = _read_ext_cols(ext_p, e_str, e_num) if ext_status == "ok" else pd.DataFrame(columns=e_str[1:] + e_num)
    if ext.index.name != "market_id" and len(ext) == 0:
        ext.index.name = "market_id"
    cat = ext["fee_category"].astype(str).str.strip().str.lower() if len(ext) else pd.Series(dtype=str)
    reward_ids: set[str] = set()
    if "rewards" in need and len(ext):
        cr = ext["clob_rewards"].fillna("").astype(str).str.strip()
        reward_ids = set(cr.index[~cr.isin(["", "[]", "null", "{}", "nan"])])
    lad_ids = set(ladder_visible) if (ladder_visible is not None and "ladders" in need) else set()
    kept: list[pd.DataFrame] = []
    n_rows = 0
    for ch in _chunks(rows_p, _ROW_STR, _ROW_NUM):
        n_rows += len(ch)
        mid = ch["market_id"]
        flags = pd.DataFrame(index=ch.index)
        nrm = ch["neg_risk_market_id"].fillna("").astype(str).str.strip()
        c = mid.map(cat).fillna("") if len(cat) else pd.Series("", index=ch.index)
        flags["_cand"] = ((nrm == "") & ~c.isin(CB2_EXCLUDED_CATEGORIES)) if "ladder_candidates" in need else False
        flags["_lad"] = mid.isin(lad_ids) if lad_ids else False
        flags["_rew"] = mid.isin(reward_ids) if reward_ids else False
        k = flags.any(axis=1).to_numpy()
        if k.any():
            kept.append(pd.concat([ch[k], flags[k]], axis=1))
    df = (pd.concat(kept, ignore_index=True).drop_duplicates("market_id") if kept
          else pd.DataFrame(columns=[*_ROW_STR, *_ROW_NUM, "_cand", "_lad", "_rew"]))
    for col in ("fee_schedule", "fee_category", "accepting_orders", "volume_num", "clob_rewards",
                "rewards_max_spread", "rewards_min_size", "competitive"):
        df[col] = df["market_id"].map(ext[col]) if (len(df) and len(ext) and col in ext.columns) else np.nan
    for c4 in CB2_SWEEP_COLUMNS:
        df[c4] = np.nan
    sw_status = "absent"
    d0 = (sweeps or {}).get(0)
    if d0 is not None and len(df):
        sw = read_sweep_book(d0, set(df["market_id"]))
        if sw is None:
            sw_status = "file_missing"
        else:
            sw_status = Path(d0).name
            for src in ("best_bid", "best_ask", "bid_size_1", "ask_size_1"):
                if len(sw):
                    df[f"sw1_{src}"] = df["market_id"].map(sw[src])
    df["capture_id"], df["capture_start_utc"] = cid, start
    sha = sha256_stream(rows_p)
    common = {"status": "written", "rows_sha256": sha, "n_rows": n_rows, "ext_status": ext_status,
              "sweep1": sw_status, "extractor_version": EXTRACTOR_VERSION, "extracted_utc": utc_now()}
    out: dict[str, dict] = {}
    if "ladder_candidates" in need:
        sub = df[df["_cand"].astype(bool)]
        write_csv_gz(Path(cb2_root) / "ladder_candidates" / f"{cid}.csv.gz", sub, LADDER_COLUMNS)
        out["ladder_candidates"] = {**common, "n_out": int(len(sub))}
    if "rewards" in need:
        sub = df[df["_rew"].astype(bool)].copy()
        parsed = [_parse_rewards(t) for t in sub["clob_rewards"]]
        sub["rewards_daily_rate"] = [p[0] for p in parsed]
        sub["rewards_start"] = [p[1] for p in parsed]
        sub["rewards_end"] = [p[2] for p in parsed]
        day = _ts(start).strftime("%Y-%m-%d")
        write_csv_gz(Path(cb2_root) / "rewards" / f"{day}.csv.gz", sub, REWARD_COLUMNS)
        out["rewards"] = {**common, "n_out": int(len(sub)), "date": day}
    if "ladders" in need:
        st = _ts(start)
        sub = df[df["_lad"].astype(bool)]
        vis = ladder_visible or {}
        st_e = st.timestamp()

        def _seen(m: str) -> bool:
            v = vis.get(m)
            if v is None:
                return True
            return st_e > v[0] if v[1] else st_e >= v[0]

        sub = sub[[_seen(m) for m in sub["market_id"]]]
        write_csv_gz(Path(cb2_root) / "ladders" / f"{cid}.csv.gz", sub, LADDER_COLUMNS)
        out["ladders"] = {**common, "n_out": int(len(sub)), "n_listed": len(lad_ids),
                          "missing": sorted(lad_ids - set(sub["market_id"]))}
    return out


def _cb2_needs(cap: dict, ent: dict, tables: tuple[str, ...], rew_ids: set[str],
               gate: dict | None) -> set[str]:
    need: set[str] = set()
    st = cap["_start"]
    if ("ladder_candidates" in tables and _ts(T2_DEV_START) <= st < _ts(T2_DEV_END)
            and ent.get("ladder_candidates", {}).get("status") != "written"):
        need.add("ladder_candidates")
    if "rewards" in tables and cap["capture_id"] in rew_ids and ent.get("rewards", {}).get("status") != "written":
        need.add("rewards")
    if ("ladders" in tables and gate and gate.get("open") and st >= _ts(gate["as_of_utc"])
            and ent.get("ladders", {}).get("status") != "written"):
        need.add("ladders")
    return need


def run_cb2_tables(
    snapshot_root: Path, sweep_root: Path, cb2_root: Path, *, tables: tuple[str, ...], mode: str,
    since: str, deadline: float, clock: Callable[[], float] = time.monotonic,
    now: Callable[[], str] = utc_now, disk_cap_gb: float | None = None,
    data_dumps: Path | None = None, data_dumps_max_gb: float | None = None, _locked_by_caller: bool = False,
) -> dict:
    """Extract the CB2 tables for every complete capture that still needs them (idempotent). Stops
    cleanly at ``deadline`` (a ``clock()`` value), at ``disk_cap_gb`` of ``cb2_root``, and refuses to start
    while ``data_dumps`` exceeds ``data_dumps_max_gb``. all-new: newest first, a missing rows file is
    recorded and the run continues; backfill: oldest first, ``ArchivedDataError`` is raised."""
    bad = [t for t in tables if t not in CB2_TABLES]
    if bad or mode not in ("all-new", "backfill"):
        raise ValueError((bad, mode))
    snapshot_root, sweep_root, cb2_root = Path(snapshot_root), Path(sweep_root), Path(cb2_root)
    res: dict[str, Any] = {"tables": list(tables), "mode": mode, "written": 0, "missing": 0, "stopped": None}
    if data_dumps_max_gb is not None and data_dumps is not None and _dir_gb(data_dumps) > data_dumps_max_gb:
        res["stopped"] = "refused_data_dumps_over_cap"
        res["remaining"] = None
        return res
    with _lock(cb2_root):
        man = _load_cb2_manifest(cb2_root)
        man0 = json.dumps(man, sort_keys=True)
        gate = ladder_gate(cb2_root) if "ladders" in tables else None
        if gate is not None:
            res["ladders_gate"] = gate["reason"]
            if gate.get("error") and man.get("ladders_gate") != gate["reason"]:
                man["ladders_gate"] = gate["reason"]
        vis = gate["visible"] if gate and gate.get("open") else None
        lo = _ts(since)
        caps = forecast.list_complete_captures(snapshot_root)
        rew = rewards_capture_ids(caps) if "rewards" in tables else set()

        def todo_now() -> list[tuple[dict, set[str]]]:
            out = []
            for c in caps:
                if c["_start"] < lo:
                    continue
                nd = _cb2_needs(c, man["captures"].get(c["capture_id"], {}), tables, rew, gate)
                if nd:
                    out.append((c, nd))
            return out[::-1] if mode == "all-new" else out

        todo = todo_now()
        sidx = sweep_index(sweep_root) if todo else {}
        used = _dir_gb(cb2_root) if disk_cap_gb is not None else 0.0
        slowest = 0.0
        t0 = clock()
        for cap, nd in todo:
            if clock() + 1.3 * slowest > deadline:
                res["stopped"] = "budget"
                break
            if disk_cap_gb is not None and used >= disk_cap_gb:
                res["stopped"] = "disk_cap"
                break
            c0 = clock()
            cid = cap["capture_id"]
            ent = dict(man["captures"].get(cid, {}))
            try:
                got = extract_cb2_capture(cap, sidx.get(cid), cb2_root, nd, ladder_visible=vis)
            except forecast.ArchivedDataError:
                if mode == "backfill":
                    raise
                ent.update(started_utc=cap["started_utc"], status="missing", extracted_utc=now())
                res["missing"] += 1
            else:
                ent.update(got)
                ent["started_utc"] = cap["started_utc"]
                if ent.get("status") == "missing":
                    ent.pop("status")
                res["written"] += 1
                if disk_cap_gb is not None:
                    used = _dir_gb(cb2_root)
            man["captures"][cid] = ent
            man["extractor_version"] = EXTRACTOR_VERSION
            _atomic_write_json(cb2_root / "manifest.json", man)  # manifest last
            slowest = max(slowest, clock() - c0)
        if json.dumps(man, sort_keys=True) != man0:
            _atomic_write_json(cb2_root / "manifest.json", man)
        res["remaining"] = max(len(todo_now()) - res["missing"], 0)
        res["max_capture_s"] = round(slowest, 2)
        res["backfill_complete"] = bool(mode == "backfill" and res["remaining"] == 0 and res["stopped"] is None)
        res["elapsed_s"] = round(clock() - t0, 2)
    return res


__all__ = ["extract", "freeze_list", "load_capture_list", "read_extract_table", "run_cb2_tables"]
