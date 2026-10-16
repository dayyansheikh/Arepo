# ruff: noqa: E501
"""CB5 extractor tables (docs/research_lab/CREATIVE_BATCH_5.md section 4.3, CB5-F).

Two tables from complete live captures, own root ``data-dumps/research_lab/cb5_extract/`` (own manifest, own lock):

* ``listings/<capture_id>.csv.gz``: first sightings of new markets (absent from the previous complete capture's
  listing, ``created_at >= capture_start - 6h``) with ids, listing-time fields, touch, last trade, volume and the
  first sweep's touch and sizes. Never contains an outcome field.
* ``cdf/<capture_id>.csv.gz``: the touch of every market id in the frozen CDF family list whose ``listed_utc``
  precedes the capture (prospective versioning: a family listed after a capture is absent from that capture's rows).

Design notes (differences from the doc's "extractor v4 inside creative_batch1.py"): a separate module and root keep
the CB1/CB2 extractor and its tables byte-identical (they are not touched, imported only for helpers), and the pass
step is ``scripts/run_cb5.py extract --all-new``. Data-only: copies fields exactly as stored, computes no statistic.
Read-only on snapshots and sweeps. A capture whose raw files are gone from the host is read from the verified release
copy (``cb4_data.ReleaseCopies``, one capture's scratch at a time); a capture with no usable copy is recorded as
missing and never reconstructed. The run refuses to start when ``data-dumps`` is above the headroom cap.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forecast
from .cb4_data import (  # noqa: PLC2701 - helpers reused on purpose
    Catalogue,
    ReleaseCopies,
    ReleaseUnavailable,
    _git_commit,
    _read_str,
)
from .creative_batch1 import (  # noqa: PLC2701
    ExtractLocked,
    _atomic_write_json,
    _dir_gb,
    _lock,
    _ts,
    sha256_stream,
    sweep_index,
    utc_now,
    write_csv_gz,
)

__all__ = ["ExtractLocked", "VersionMismatch", "run_tables", "read_table", "load_family_list", "family_list_sha256"]

EXTRACTOR_VERSION = "cb5-extract-v1"
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
DATA_DUMPS = forecast.ROOT / "data-dumps"
CB5_ROOT = DATA_DUMPS / "research_lab" / "cb5_extract"
T5_DEV_START = "2026-10-11T12:00:00Z"
DEFAULT_BUDGET_S = 420.0
TABLES = ("listings", "cdf")
NEW_LISTING_LOOKBACK_H = 6
DATA_DUMPS_MAX_GB = 12.0  # hard cap; the CB5 data jobs refuse above 10 (headroom precondition, section 2.8)
JOB_REFUSE_GB = 10.0
TABLE_CAP_GB = {"listings": 0.05, "cdf": 0.05}
SCRATCH_CAP_GB = 0.2

TOUCH = ["best_bid", "best_ask", "spread", "last_trade_price", "volume_num", "accepting_orders"]
LISTINGS_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "clob_token_id_0",
    "clob_token_id_1", "created_at", "start_date", "end_date", "fee_category", "neg_risk", "neg_risk_market_id",
    "event_neg_risk_augmented", *TOUCH, "order_price_min_tick_size", "first_seen_certain",
    "sweep_best_bid", "sweep_best_ask", "sweep_bid_size_1", "sweep_ask_size_1",
]
CDF_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "clob_token_id_0",
    "clob_token_id_1", "end_date", "fee_category", "neg_risk", "neg_risk_market_id", "event_neg_risk_augmented",
    "closed", "active", *TOUCH, "family_ids",
    "sweep_best_bid", "sweep_best_ask", "sweep_bid_size_1", "sweep_ask_size_1",
]
_ROWS_WANT = ["received_utc", "market_id", "condition_id", "event_id", "best_bid", "best_ask", "spread",
              "last_trade_price", "neg_risk", "neg_risk_market_id", "event_neg_risk_augmented", "clob_token_id_0",
              "closed", "active", "end_date"]
_EXT_WANT = ["market_id", "clob_token_id_0", "clob_token_id_1", "accepting_orders", "created_at", "start_date",
             "volume_num", "fee_category", "neg_risk_market_id", "order_price_min_tick_size", "neg_risk"]
_SWEEP_FIELDS = ["best_bid", "best_ask", "bid_size_1", "ask_size_1"]
_OUTCOME_LIKE = ("outcome", "winner", "resolved", "payout")  # a stored column may never carry these


class VersionMismatch(RuntimeError):
    """The cb5_extract manifest was written by another extractor version (a new version needs a new root)."""


def _dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.replace("", np.nan), utc=True, errors="coerce", format="ISO8601")


def assert_no_outcome_columns(columns: list[str]) -> None:
    bad = [c for c in columns if any(t in c.lower() for t in _OUTCOME_LIKE)]
    if bad:
        raise AssertionError(f"CB5 extract tables may not carry outcome columns: {bad}")


assert_no_outcome_columns(LISTINGS_COLUMNS + CDF_COLUMNS)


# ---- family list (frozen by run_cb5.py cdf-audit-apply) -----------------------------------------------------------


def family_list_sha256(doc: dict) -> str:
    import hashlib

    body = {k: v for k, v in doc.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def load_family_list(path: Path) -> dict[str, dict]:
    """``{market_id: {"listed_utc": str, "family_ids": [str]}}`` from a frozen family list. The list's own ``sha256``
    must equal the hash of its content (a hand-edited list is refused). Families: ``{"family_id", "listed_utc",
    "market_ids": [...]}``."""
    doc = json.loads(Path(path).read_text())
    if doc.get("sha256") != family_list_sha256(doc):
        raise ValueError(f"{path}: family list sha256 does not match its content")
    out: dict[str, dict] = {}
    for f in doc.get("families", []):
        for m in f["market_ids"]:
            e = out.setdefault(str(m), {"listed_utc": f["listed_utc"], "family_ids": []})
            if f["listed_utc"] < e["listed_utc"]:
                e["listed_utc"] = f["listed_utc"]
            e["family_ids"].append(str(f["family_id"]))
    return out


# ---- per-capture tables -------------------------------------------------------------------------------------------


def _read_capture(rows_path: Path, ext_path: Path) -> pd.DataFrame:
    forecast.require_local(rows_path)
    forecast.require_local(ext_path)
    rows = _read_str(Path(rows_path), _ROWS_WANT).drop_duplicates("market_id").reset_index(drop=True)
    ext = _read_str(Path(ext_path), _EXT_WANT).drop_duplicates("market_id").set_index("market_id")
    df = rows.join(ext.add_suffix("_ext"), on="market_id")
    for c in ("clob_token_id_0", "neg_risk_market_id", "neg_risk"):
        df[c] = np.where(df[c].astype(str) != "", df[c], df[f"{c}_ext"].fillna(""))
    for c in ("clob_token_id_1", "created_at", "start_date", "volume_num", "fee_category", "accepting_orders",
              "order_price_min_tick_size"):
        df[c] = df[f"{c}_ext"].fillna("")
    return df


def _join_sweep(out: pd.DataFrame, sweep_path: Path | None) -> bool:
    for f in _SWEEP_FIELDS:
        out[f"sweep_{f}"] = ""
    if sweep_path is None or not Path(sweep_path).exists() or not len(out):
        return sweep_path is not None and Path(sweep_path).exists()
    sw = _read_str(Path(sweep_path), ["market_id", *_SWEEP_FIELDS]).drop_duplicates("market_id").set_index("market_id")
    sw = sw[sw.index.isin(out["market_id"])]
    pos = out.set_index("market_id")
    for f in _SWEEP_FIELDS:
        pos.loc[sw.index, f"sweep_{f}"] = sw[f]
    for f in _SWEEP_FIELDS:
        out[f"sweep_{f}"] = pos[f"sweep_{f}"].to_numpy()
    return True


def build_listings(df: pd.DataFrame, prev_ids: set[str] | None, capture_id: str, capture_start: str,
                   sweep_path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """First sightings in one capture. ``prev_ids`` = the previous complete capture's listing (None: chain broken,
    then only the ``created_at`` rule applies and ``first_seen_certain`` = 0)."""
    start = _ts(capture_start)
    created = _dt(df["created_at"])
    recent = (created >= pd.Timestamp(start - timedelta(hours=NEW_LISTING_LOOKBACK_H))).to_numpy()
    new = np.ones(len(df), bool) if prev_ids is None else (~df["market_id"].isin(prev_ids)).to_numpy()
    out = df[recent & new].copy()
    out["capture_id"], out["capture_start_utc"] = capture_id, capture_start
    out["first_seen_certain"] = "1" if prev_ids is not None else "0"
    swept = _join_sweep(out, sweep_path)
    out = out.sort_values("market_id").reset_index(drop=True)
    facts = {"n_listing": int(len(df)), "n_new": int(len(out)), "prev_chain": "ok" if prev_ids is not None else "broken",
             "n_created_unparseable": int(created.isna().sum()), "sweep_found": bool(swept)}
    return out.reindex(columns=LISTINGS_COLUMNS), facts


def build_cdf(df: pd.DataFrame, families: dict[str, dict], capture_id: str, capture_start: str,
              sweep_path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Touch rows of every family market listed before the capture (prospective versioning)."""
    start = _ts(capture_start)
    visible = {m for m, e in families.items() if _ts(e["listed_utc"]) < start}
    out = df[df["market_id"].isin(visible)].copy()
    out["capture_id"], out["capture_start_utc"] = capture_id, capture_start
    out["family_ids"] = out["market_id"].map(lambda m: ";".join(sorted(families[m]["family_ids"])))
    swept = _join_sweep(out, sweep_path)
    out = out.sort_values("market_id").reset_index(drop=True)
    facts = {"n_listed_visible": len(visible), "n_found": int(len(out)),
             "missing": sorted(visible - set(out["market_id"]))[:50], "sweep_found": bool(swept)}
    return out.reindex(columns=CDF_COLUMNS), facts


# ---- driver --------------------------------------------------------------------------------------------------------


def _load_manifest(root: Path) -> dict:
    p = Path(root) / "manifest.json"
    if p.exists():
        man = json.loads(p.read_text())
        if man.get("extractor_version") != EXTRACTOR_VERSION:
            raise VersionMismatch(f"{p}: {man.get('extractor_version')!r} != {EXTRACTOR_VERSION!r}; use a new root")
        return man
    return {"extractor_version": EXTRACTOR_VERSION, "captures": {}, "chain": None}


def _used_gb(root: Path, tables: tuple[str, ...], dir_gb: Callable[[Path], float]) -> float:
    return sum(dir_gb(Path(root) / t) for t in tables)


def _is_local(cap: dict) -> bool:
    d = Path(cap["dir"])
    return (d / "rows.csv.gz").exists() and (d / "rows_ext.csv.gz").exists()


def run_tables(
    snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT, root: Path = CB5_ROOT, *,
    tables: tuple[str, ...] = ("listings",), mode: str, since: str = T5_DEV_START, before: str | None = None,
    family_list: Path | None = None, budget_s: float = DEFAULT_BUDGET_S,
    clock: Callable[[], float] = time.monotonic, now: Callable[[], str] = utc_now,
    disk_cap_gb: float | None = None, data_dumps: Path | None = None, data_dumps_max_gb: float | None = None,
    retry_missing: bool = False, dir_gb: Callable[[Path], float] = _dir_gb, git_commit: str | None = None,
    release: ReleaseCopies | None = None, catalogue: Catalogue | None = None,
) -> dict:
    """Extract ``tables`` for every complete capture in ``[since, before)`` that still needs them, oldest first
    (the listings chain needs the previous capture). Idempotent by (capture_id, table). Stops at the budget and at
    ``disk_cap_gb`` of the written tables; refuses (``stopped='refused_data_dumps_over_cap'``) when ``data_dumps``
    plus the output still allowed plus the scratch would pass ``data_dumps_max_gb``; repeated between captures.
    ``cdf`` needs ``family_list``. A capture with no usable raw copy is recorded ``missing`` with the reason and the
    run continues; a transient restore failure stops the run and leaves the capture pending."""
    bad = [t for t in tables if t not in TABLES]
    if bad or mode not in ("backfill", "all-new"):
        raise ValueError((bad, mode))
    if "cdf" in tables and family_list is None:
        raise ValueError("cdf needs a frozen family list")
    snapshot_root, sweep_root, root = Path(snapshot_root), Path(sweep_root), Path(root)
    res: dict[str, Any] = {"cb5_extract": EXTRACTOR_VERSION, "mode": mode, "tables": list(tables), "written": 0,
                           "missing": 0, "from_release": 0, "stopped": None}
    out_allow = disk_cap_gb if disk_cap_gb is not None else sum(TABLE_CAP_GB[t] for t in tables)

    def over_dumps(written_gb: float = 0.0) -> bool:
        if data_dumps_max_gb is None or data_dumps is None:
            return False
        need = dir_gb(Path(data_dumps)) + max(0.0, out_allow - written_gb) + (SCRATCH_CAP_GB if release is not None else 0.0)
        return need > data_dumps_max_gb

    if over_dumps():
        res.update(stopped="refused_data_dumps_over_cap", remaining=None, backfill_complete=False)
        return res
    families = load_family_list(Path(family_list)) if "cdf" in tables and family_list is not None else {}
    gc = git_commit if git_commit is not None else _git_commit()
    with _lock(root):
        man = _load_manifest(root)
        caps = forecast.list_complete_captures(snapshot_root)
        if catalogue is not None:
            have = {c["capture_id"] for c in caps} | {Path(c["dir"]).name for c in caps}
            for name, st in catalogue.snapshot_dirs().items():
                if name not in have:
                    caps.append({"capture_id": name, "started_utc": st, "_start": _ts(st), "dir": str(snapshot_root / name),
                                 "release_only": True, "state": "complete"})
            caps.sort(key=lambda c: c["_start"])
        lo = _ts(since)
        hi = _ts(before) if before else None
        window = [(i, c) for i, c in enumerate(caps) if c["_start"] >= lo and (hi is None or c["_start"] < hi)]

        def needs(c: dict) -> set[str]:
            ent = man["captures"].get(c["capture_id"], {})
            out = set()
            for t in tables:
                st = ent.get("tables", {}).get(t)
                if st is None or (st.get("status") == "missing" and (retry_missing or mode == "all-new")):
                    out.add(t)
            return out

        todo = [(i, c) for i, c in window if needs(c)]
        sidx = sweep_index(sweep_root) if todo else {}
        used = _used_gb(root, tables, dir_gb) if disk_cap_gb is not None else 0.0
        slowest, t0 = 0.0, clock()
        deadline = t0 + budget_s

        def first_sweep(cid: str) -> Path | None:
            d = sidx.get(cid) or {}
            return Path(d[min(d)]) if d else None

        def chain_ids(prev_cap: dict | None) -> set[str] | None:
            ch = man.get("chain")
            if prev_cap is None or not ch or ch.get("capture_id") != prev_cap["capture_id"]:
                return None
            p = Path(root) / "_chain" / "prev_ids.csv.gz"
            if not p.exists() or sha256_stream(p) != ch.get("sha256"):
                return None
            return set(_read_str(p, ["market_id"])["market_id"])

        try:
            for n, (i, cap) in enumerate(todo):
                if clock() + 1.3 * slowest > deadline:
                    res["stopped"] = "budget"
                    break
                if disk_cap_gb is not None and used >= disk_cap_gb:
                    res["stopped"] = "disk_cap"
                    break
                if over_dumps(used):
                    res["stopped"] = "data_dumps_over_cap"
                    break
                c0 = clock()
                cid, start = cap["capture_id"], cap["started_utc"]
                cdir = Path(cap["dir"])
                sw_dir = first_sweep(cid)
                source, reason = "host", None
                rows_p, ext_p = cdir / "rows.csv.gz", cdir / "rows_ext.csv.gz"
                sw_p = (sw_dir / "rows.csv.gz") if sw_dir is not None else None
                if not _is_local(cap):
                    files = None
                    if release is not None:
                        upcoming = [(c2, first_sweep(c2["capture_id"])) for _j, c2 in todo[n + 1:] if not _is_local(c2)]
                        try:
                            files, reason = release.ensure(cap, sw_dir, upcoming)
                        except ReleaseUnavailable:
                            res["stopped"] = "release_unavailable"
                            break
                    if files is None:
                        reason = reason or ("no_host_manifest" if cap.get("release_only") else "archived_no_release_copy")
                    else:
                        rows_p, ext_p, sw_p = files["rows"], files["ext"], files.get("sweep")
                        source = "release"
                nd = needs(cap)
                ent = dict(man["captures"].get(cid, {}))
                ent_tables = dict(ent.get("tables", {}))
                try:
                    if reason is not None:
                        raise forecast.ArchivedDataError(reason)
                    df = _read_capture(rows_p, ext_p)
                    src_hash = {"rows": sha256_stream(rows_p), "rows_ext": sha256_stream(ext_p)}
                except forecast.ArchivedDataError:
                    for t in nd:
                        ent_tables[t] = {"status": "missing", "reason": reason or "archived_no_release_copy"}
                    res["missing"] += 1
                    if "listings" in nd:
                        man["chain"] = None  # the chain is broken at a missing capture
                else:
                    if "listings" in nd:
                        prev = caps[i - 1] if i > 0 else None
                        prev_ids = chain_ids(prev)
                        out, facts = build_listings(df, prev_ids, cid, start, sw_p)
                        f_out = root / "listings" / f"{cid}.csv.gz"
                        write_csv_gz(f_out, out, LISTINGS_COLUMNS)
                        ent_tables["listings"] = {"status": "extracted", "sha256": sha256_stream(f_out), **facts}
                        ids_df = pd.DataFrame({"market_id": sorted(df["market_id"])})
                        cp = root / "_chain" / "prev_ids.csv.gz"
                        write_csv_gz(cp, ids_df, ["market_id"])
                        man["chain"] = {"capture_id": cid, "sha256": sha256_stream(cp)}
                    if "cdf" in nd:
                        out, facts = build_cdf(df, families, cid, start, sw_p)
                        f_out = root / "cdf" / f"{cid}.csv.gz"
                        write_csv_gz(f_out, out, CDF_COLUMNS)
                        ent_tables["cdf"] = {"status": "extracted", "sha256": sha256_stream(f_out), **facts}
                    ent["source_sha256"] = src_hash
                    res["written"] += 1
                    res["from_release"] += int(source == "release")
                    if disk_cap_gb is not None:
                        used = _used_gb(root, tables, dir_gb)
                ent.update(capture_id=cid, capture_start_utc=start, source=source, tables=ent_tables,
                           extractor_version=EXTRACTOR_VERSION, git_commit=gc, written_utc=now(), mode=mode)
                man["captures"][cid] = ent
                _atomic_write_json(root / "manifest.json", man)  # manifest last, after the table files exist
                slowest = max(slowest, clock() - c0)
        finally:
            if release is not None:
                release.cleanup()
        res["remaining"] = len([1 for _i, c in window if needs(c) and not all(
            man["captures"].get(c["capture_id"], {}).get("tables", {}).get(t, {}).get("status") == "missing" for t in needs(c))])
        res["n_missing_total"] = sum(1 for e in man["captures"].values()
                                     for s in e.get("tables", {}).values() if s.get("status") == "missing")
        res["max_capture_s"] = round(slowest, 2)
        res["backfill_complete"] = bool(mode == "backfill" and res["remaining"] == 0 and res["stopped"] is None)
        res["elapsed_s"] = round(clock() - t0, 2)
    return res


def read_table(root: Path, table: str, capture_id: str) -> pd.DataFrame:
    """Raw-string frame of one capture's table file."""
    return pd.read_csv(Path(root) / table / f"{capture_id}.csv.gz", dtype=str, keep_default_na=False)
