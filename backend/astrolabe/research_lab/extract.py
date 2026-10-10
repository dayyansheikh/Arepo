"""E001 extraction: stream Gamma full-universe capture pages into a compact gzip CSV.

Reads ``data-dumps/fs2_capture_*`` strictly read-only. The observation clock of a row is the
page-level ``receipt.json: first_received.utc`` (the client receipt of the first response bytes),
not the session start. Exact decimal strings are parsed to float only here.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import multiprocessing as mp
import os
import subprocess
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

FULL_CAPTURE_MIN_PAGES = 2000
EXTRACTOR_VERSION = "e001-extract-v1"

COLUMNS = [
    "capture_id",
    "capture_start_utc",
    "received_utc",
    "market_id",
    "condition_id",
    "event_id",
    "closed",
    "active",
    "binary",
    "best_bid",
    "best_ask",
    "spread",
    "last_trade_price",
    "chg_1h",
    "chg_1d",
    "chg_1w",
    "liquidity",
    "volume24hr",
    "end_date",
    "updated_at",
    "dup_count",
    "clob_token_id_0",
    "neg_risk",
    "neg_risk_market_id",
    "neg_risk_other",
    "event_neg_risk_augmented",
]


def parse_num(v: Any) -> float | None:
    """Parse a Gamma numeric (``{"$decimal": "0.96"}``, string, int, float) to float or None."""
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("$decimal")
        if v is None:
            return None
    if isinstance(v, bool):
        return None
    try:
        if isinstance(v, str):
            if v.strip() == "":
                return None
            f = float(Decimal(v.strip()))
        else:
            f = float(v)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return f if math.isfinite(f) else None


def _json_list(v: Any) -> list | None:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            out = json.loads(v)
        except ValueError:
            return None
        return out if isinstance(out, list) else None
    return None


def _event_id(m: dict) -> str | None:
    ev = m.get("events")
    if isinstance(ev, list) and ev and isinstance(ev[0], dict) and ev[0].get("id") is not None:
        return str(ev[0]["id"])
    return None


def _flag(v: Any) -> int | None:
    """Gamma boolean (bool or 'true'/'false' string) to 1/0, else None."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return int(v.strip().lower() == "true")
    return None


def _event_flag(m: dict, key: str) -> int | None:
    ev = m.get("events")
    if isinstance(ev, list) and ev and isinstance(ev[0], dict):
        return _flag(ev[0].get(key))
    return None


def _token0(m: dict) -> str | None:
    """Outcome-0 CLOB token id (``clobTokenIds[0]``), or None if absent."""
    ids = _json_list(m.get("clobTokenIds"))
    if ids and ids[0] not in (None, ""):
        return str(ids[0])
    return None


def market_row(m: dict, capture_id: str, capture_start: str, received: str) -> dict | None:
    """Compact row for one Gamma market dict (None if it has no market id)."""
    if m.get("id") is None:
        return None
    outcomes = _json_list(m.get("outcomes"))
    return {
        "capture_id": capture_id,
        "capture_start_utc": capture_start,
        "received_utc": received,
        "market_id": str(m["id"]),
        "condition_id": m.get("conditionId"),
        "event_id": _event_id(m),
        "closed": m.get("closed"),
        "active": m.get("active"),
        "binary": int(outcomes is not None and len(outcomes) == 2),
        "best_bid": parse_num(m.get("bestBid")),
        "best_ask": parse_num(m.get("bestAsk")),
        "spread": parse_num(m.get("spread")),
        "last_trade_price": parse_num(m.get("lastTradePrice")),
        "chg_1h": parse_num(m.get("oneHourPriceChange")),
        "chg_1d": parse_num(m.get("oneDayPriceChange")),
        "chg_1w": parse_num(m.get("oneWeekPriceChange")),
        "liquidity": parse_num(m.get("liquidity")),
        "volume24hr": parse_num(m.get("volume24hr")),
        "end_date": m.get("endDate"),
        "updated_at": m.get("updatedAt"),
        "dup_count": 0,
        "clob_token_id_0": _token0(m),
        "neg_risk": _flag(m.get("negRisk")),
        "neg_risk_market_id": m.get("negRiskMarketID") or None,
        "neg_risk_other": _flag(m.get("negRiskOther")),
        "event_neg_risk_augmented": _event_flag(m, "negRiskAugmented"),
    }


def dedup_rows(rows: list[dict]) -> tuple[list[dict], int]:
    """Keep the first receipt per market_id; count the dropped repeats. Returns (rows, n_dups)."""
    kept: dict[str, dict] = {}
    n_dup = 0
    for r in rows:
        k = r["market_id"]
        cur = kept.get(k)
        if cur is None:
            kept[k] = r
            continue
        n_dup += 1
        if r["received_utc"] < cur["received_utc"]:  # fixed-width ISO UTC sorts chronologically
            r["dup_count"] = cur["dup_count"] + 1
            kept[k] = r
        else:
            cur["dup_count"] += 1
    return list(kept.values()), n_dup


def _read_page(page_dir: str) -> tuple[str, str | None, list[dict] | None, str | None]:
    """Worker: returns (page_dir, receipt_utc, market dict rows, skip_reason)."""
    p = Path(page_dir)
    try:
        receipt = json.loads((p / "receipt.json").read_text())
        parsed = json.loads((p / "parsed.json").read_text())
    except (OSError, ValueError):
        return page_dir, None, None, "unreadable"
    if receipt.get("status") != 200 or receipt.get("transport_error"):
        return page_dir, None, None, "bad_status"
    if parsed.get("parse_error"):
        return page_dir, None, None, "parse_error"
    fr = receipt.get("first_received") or {}
    utc = fr.get("utc")
    markets = (parsed.get("value") or {}).get("markets")
    if not utc or not isinstance(markets, list):
        return page_dir, None, None, "no_receipt_or_markets"
    return page_dir, utc, markets, None


def _page_rows(args: tuple[str, str, str]) -> tuple[str | None, list[dict], str | None]:
    page_dir, capture_id, start = args
    _, utc, markets, reason = _read_page(page_dir)
    if reason or utc is None or markets is None:
        return None, [], reason
    rows = [r for m in markets if (r := market_row(m, capture_id, start, utc)) is not None]
    return utc, rows, None


def discover_full_captures(dump_root: Path) -> list[dict]:
    """Return full captures (>= FULL_CAPTURE_MIN_PAGES parsed pages), ordered by start time."""
    out = []
    for d in sorted(dump_root.glob("fs2_capture_*")):
        sj = d / "session.json"
        if not d.is_dir() or not sj.exists():
            continue
        started = json.loads(sj.read_text())["started"]["utc"]
        pages = [
            e.path
            for e in os.scandir(d)
            if e.is_dir() and os.path.exists(os.path.join(e.path, "parsed.json"))
        ]
        if len(pages) >= FULL_CAPTURE_MIN_PAGES:
            out.append(
                {
                    "capture_id": d.name.removeprefix("fs2_capture_"),
                    "start_utc": started,
                    "pages": sorted(pages),
                }
            )
    out.sort(key=lambda c: c["start_utc"])
    return out


def _git_commit() -> str:
    try:
        root = Path(__file__).resolve().parents[3]
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
        ).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except OSError:
        return "unknown"


def manifest_matches(out_dir: Path, captures: list[dict]) -> bool:
    mf = out_dir / "manifest.json"
    if not mf.exists() or not (out_dir / "snapshots.csv.gz").exists():
        return False
    m = json.loads(mf.read_text())
    return (
        m.get("extractor_version") == EXTRACTOR_VERSION
        and [c["capture_id"] for c in m.get("captures", [])] == [c["capture_id"] for c in captures]
        and [c["source_pages"] for c in m.get("captures", [])]
        == [len(c["pages"]) for c in captures]
    )


def extract(dump_root: Path, out_dir: Path, workers: int | None = None) -> dict:
    captures = discover_full_captures(dump_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    workers = workers or max(1, min(6, (os.cpu_count() or 2) - 1))
    cap_stats = []
    tmp = out_dir / "snapshots.csv.gz.tmp"
    with (
        gzip.open(tmp, "wt", newline="", compresslevel=6) as fh,
        mp.get_context("fork").Pool(workers) as pool,
    ):
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for c in captures:
            tasks = [(p, c["capture_id"], c["start_utc"]) for p in c["pages"]]
            all_rows: list[dict] = []
            skipped: dict[str, int] = {}
            n_pages_ok = 0
            for _utc, rows, reason in pool.imap_unordered(_page_rows, tasks, chunksize=8):
                if reason:
                    skipped[reason] = skipped.get(reason, 0) + 1
                    continue
                n_pages_ok += 1
                all_rows.extend(rows)
            kept, n_dup = dedup_rows(all_rows)
            kept.sort(key=lambda r: (r["received_utc"], r["market_id"]))
            for r in kept:
                w.writerow({k: ("" if v is None else v) for k, v in r.items()})
            rec = [r["received_utc"] for r in kept]
            cap_stats.append(
                {
                    "capture_id": c["capture_id"],
                    "start_utc": c["start_utc"],
                    "source_pages": len(c["pages"]),
                    "pages_used": n_pages_ok,
                    "pages_skipped": skipped,
                    "raw_market_rows": len(all_rows),
                    "rows_kept": len(kept),
                    "duplicate_rows_dropped": n_dup,
                    "first_receipt_utc": rec[0] if rec else None,
                    "last_receipt_utc": rec[-1] if rec else None,
                }
            )
    os.replace(tmp, out_dir / "snapshots.csv.gz")
    manifest = {
        "experiment": "E001",
        "extractor_version": EXTRACTOR_VERSION,
        "observation_clock": "page receipt.json first_received.utc (per page)",
        "full_capture_min_pages": FULL_CAPTURE_MIN_PAGES,
        "captures": cap_stats,
        "source_file_count": sum(c["source_pages"] for c in cap_stats),
        "total_rows": sum(c["rows_kept"] for c in cap_stats),
        "total_duplicates_dropped": sum(c["duplicate_rows_dropped"] for c in cap_stats),
        "code_commit": _git_commit(),
        "extracted_at_utc": datetime.now(UTC).isoformat(),
        "extraction_seconds": round(time.time() - t0, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest
