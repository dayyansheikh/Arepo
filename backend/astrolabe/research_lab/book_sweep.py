"""Order-book sweeps over the E001-eligible markets of one complete universe snapshot.

Reads ``rows.csv.gz`` of a complete snapshot, selects the markets the E002 forecaster would
select (``endDate`` unknown or > origin receipt + 3h), and fetches the outcome-0 token book of
each via CLOB ``POST /books`` in sequential batches of 100 in a fixed order (sorted token id).
One output row per token; the batch receipt clock is the time the response body was fully read.
Read-only, public endpoint, no credentials. Output is written to a temp dir, then renamed.

Book fields follow ``astrolabe/clients/clob_rest.py`` (``get_books``) and
``astrolabe/ingest/normalize.py`` (``normalize_book``): ``asset_id``, ``bids``/``asks`` lists of
``{price, size}`` strings, ``timestamp``, ``hash``, ``tick_size``, ``min_order_size``.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from . import forecast, panel

SWEEP_VERSION = "book-sweep-v1"
CLOB_URL = "https://clob.polymarket.com/books"
HEADERS = {"User-Agent": "arepo-research-lab/1", "Content-Type": "application/json"}
BATCH_SIZE = 100
MAX_RETRIES = 5
MAX_REQUESTS = 2000
MAX_SECONDS = 20 * 60
DELAY_SECONDS = 0.1
BACKOFF_BASE = 1.0
BACKOFF_MAX = 30.0
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
TOKEN_COL = "clob_token_id_0"

ROW_COLUMNS = [
    "sweep_id", "token_id", "market_id", "batch_index", "batch_receipt_utc", "book_timestamp",
    "book_hash", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c",
    "depth_ask_1c", "depth_bid_5c", "depth_ask_5c", "n_bid_levels", "n_ask_levels",
    "tick_size", "min_order_size", "state",
]

# transport(body) -> (status, decoded body bytes, headers); may raise TransportError.
Transport = Callable[[list[dict]], tuple[int, bytes, dict]]


class TransportError(Exception):
    """Network-level failure (timeout, connection reset); retried like a 5xx."""


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def httpx_transport(timeout: float = 60.0) -> Transport:
    import httpx

    client = httpx.Client(timeout=timeout, headers=HEADERS)

    def post(body: list[dict]) -> tuple[int, bytes, dict]:
        try:
            r = client.post(CLOB_URL, json=body)
        except httpx.HTTPError as exc:
            raise TransportError(str(exc)) from exc
        return r.status_code, r.content, dict(r.headers)

    return post


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=forecast.ROOT, capture_output=True, text=True, timeout=15
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# --- token selection --------------------------------------------------------------------------


def select_tokens(rows: pd.DataFrame) -> list[tuple[str, str]]:
    """``(token_id, market_id)`` for eligible binary markets, sorted by token id, deduplicated."""
    if TOKEN_COL not in rows.columns:
        raise ValueError(f"snapshot rows have no {TOKEN_COL} column; re-collect the snapshot")
    binary = rows[rows["binary"] == 1].reset_index(drop=True)
    t_i = panel._epoch(binary["received_utc"])
    ok = panel.eligibility_mask(binary, t_i + forecast.FORECAST_END_MARGIN_H * 3600.0)
    o = binary[ok]
    o = o[o[TOKEN_COL].notna() & (o[TOKEN_COL].astype(str) != "")]
    pairs = sorted(zip(o[TOKEN_COL].astype(str), o["market_id"].astype(str), strict=True))
    seen: dict[str, str] = {}
    for tok, mid in pairs:
        seen.setdefault(tok, mid)
    return sorted(seen.items())


def load_tokens(snapshot_dir: Path) -> tuple[list[tuple[str, str]], dict, str]:
    snapshot_dir = Path(snapshot_dir)
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    if manifest.get("state") != "complete":
        raise ValueError(f"snapshot {snapshot_dir.name} is not complete: {manifest.get('state')}")
    # Token ids are ~77-digit integers: they must be read as strings, never as numbers.
    rows = pd.read_csv(
        snapshot_dir / "rows.csv.gz", dtype={**forecast.ID_DTYPES, TOKEN_COL: str}
    )
    return select_tokens(rows), manifest, forecast.sha256_file(snapshot_dir / "manifest.json")


# --- book parsing -----------------------------------------------------------------------------


def _dec(v: Any) -> Decimal | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _levels(raw: Any) -> list[tuple[Decimal, Decimal]]:
    """Valid (price, size) levels with size > 0; unsorted."""
    out = []
    for lvl in raw if isinstance(raw, list) else []:
        if not isinstance(lvl, dict):
            continue
        p, s = _dec(lvl.get("price")), _dec(lvl.get("size"))
        if p is not None and s is not None and s > 0:
            out.append((p, s))
    return out


def _depth(levels: list[tuple[Decimal, Decimal]], best: Decimal, width: Decimal, sign: int):
    """Sum of sizes within ``width`` of ``best`` (sign=+1 asks, -1 bids), inclusive."""
    return sum((s for p, s in levels if sign * (p - best) <= width), Decimal(0))


def _f(d: Decimal | None) -> float | None:
    return None if d is None else float(d)


def parse_book(book: dict) -> dict:
    """Compact fields for one raw book; bids sorted descending, asks ascending explicitly."""
    bids = sorted(_levels(book.get("bids")), key=lambda x: x[0], reverse=True)
    asks = sorted(_levels(book.get("asks")), key=lambda x: x[0])
    c1, c5 = Decimal("0.01"), Decimal("0.05")
    r: dict[str, Any] = {
        "best_bid": None, "best_ask": None, "bid_size_1": None, "ask_size_1": None,
        "depth_bid_1c": None, "depth_ask_1c": None, "depth_bid_5c": None, "depth_ask_5c": None,
        "n_bid_levels": len(bids), "n_ask_levels": len(asks),
    }
    if bids:
        b = bids[0][0]
        r.update(best_bid=_f(b), bid_size_1=_f(bids[0][1]),
                 depth_bid_1c=_f(_depth(bids, b, c1, -1)), depth_bid_5c=_f(_depth(bids, b, c5, -1)))
    if asks:
        a = asks[0][0]
        r.update(best_ask=_f(a), ask_size_1=_f(asks[0][1]),
                 depth_ask_1c=_f(_depth(asks, a, c1, 1)), depth_ask_5c=_f(_depth(asks, a, c5, 1)))
    r["state"] = ("two_sided" if bids and asks else "one_sided" if bids or asks else "empty")
    for src, dst in (("timestamp", "book_timestamp"), ("hash", "book_hash"),
                     ("tick_size", "tick_size"), ("min_order_size", "min_order_size")):
        v = book.get(src)
        r[dst] = None if v is None else str(v)
    return r


# --- sweep ------------------------------------------------------------------------------------


def _retry_after(headers: dict) -> float | None:
    for k, v in headers.items():
        if k.lower() == "retry-after":
            try:
                return min(max(0.0, float(v)), 60.0)
            except (TypeError, ValueError):
                return None
    return None


def _fetch_batch(chunk, transport, sleep, ctx) -> dict:
    """POST one batch with retry; returns the batch record (``body`` kept in memory only)."""
    body = [{"token_id": t} for t in chunk]
    rec: dict[str, Any] = {"attempts": 0, "status": None, "error": None}
    for attempt in range(MAX_RETRIES + 1):
        if ctx["requests"] >= MAX_REQUESTS:
            rec["error"] = "max_requests"
            return rec
        if ctx["clock"]() - ctx["t0"] > MAX_SECONDS:
            rec["error"] = "max_seconds"
            return rec
        ctx["requests"] += 1
        rec["attempts"] = attempt + 1
        rec["request_sent_utc"] = _utc_now()
        headers: dict = {}
        try:
            status, raw, headers = transport(body)
        except TransportError as exc:
            status, raw = 0, b""
            rec["error"] = f"transport: {exc}"[:200]
        rec["received_utc"] = _utc_now()
        rec["status"] = status
        if status == 200:
            rec["error"] = None
            rec["sha256"] = hashlib.sha256(raw).hexdigest()
            rec["bytes"] = len(raw)
            rec["body"] = raw
            return rec
        if status == 0 or status == 429 or status >= 500:
            if attempt >= MAX_RETRIES:
                rec["error"] = rec["error"] or f"retries_exhausted_http_{status}"
                return rec
            wait = _retry_after(headers) if status == 429 else None
            sleep(wait if wait is not None else min(BACKOFF_BASE * 2**attempt, BACKOFF_MAX))
            continue
        rec["error"] = f"http_{status}"
        return rec
    return rec


def run_sweep(
    tokens: list[tuple[str, str]],
    transport: Transport,
    *,
    out_root: Path = SWEEP_ROOT,
    series_id: str | None = None,
    series_index: int = 0,
    snapshot_id: str = "",
    snapshot_manifest_sha256: str = "",
    keep_raw: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    delay: float = DELAY_SECONDS,
    batch_size: int = BATCH_SIZE,
    extra_manifest: dict | None = None,
) -> dict:
    """Run one sweep over ``tokens`` (already sorted) and write the output atomically."""
    started = _utc_now()
    sweep_id = f"{started.replace('-', '').replace(':', '').replace('.', '')[:15]}Z_" \
               f"{uuid.uuid4().hex[:8]}"
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    tmp = out_root / f".tmp_{sweep_id}"
    tmp.mkdir()
    if keep_raw:
        (tmp / "raw").mkdir()
    ctx = {"requests": 0, "clock": clock, "t0": clock()}
    batches: list[dict] = []
    n_returned = 0
    state = "complete"
    rows_written = 0
    try:
        with gzip.open(tmp / "rows.csv.gz", "wt", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=ROW_COLUMNS)
            w.writeheader()
            for bi, i in enumerate(range(0, len(tokens), batch_size)):
                chunk = tokens[i:i + batch_size]
                mids = dict(chunk)
                if bi:
                    sleep(delay)
                rec = _fetch_batch([t for t, _ in chunk], transport, sleep, ctx)
                body = rec.pop("body", None)
                rec.update(index=bi, tokens_requested=len(chunk), tokens_returned=0)
                books: dict[str, dict] = {}
                if body is not None:
                    try:
                        data = json.loads(body)
                    except ValueError:
                        data = None
                    if not isinstance(data, list):
                        rec["error"] = "bad_body"
                    else:
                        for b in data:
                            if isinstance(b, dict):
                                tid = b.get("asset_id") or b.get("token_id")
                                if tid and str(tid) in mids:
                                    books[str(tid)] = b
                        rec["tokens_returned"] = len(books)
                        n_returned += len(books)
                    if keep_raw:
                        with gzip.open(tmp / "raw" / f"batch_{bi:05d}.json.gz", "wb") as rf:
                            rf.write(body)
                batches.append(rec)
                if rec["error"]:
                    state = f"incomplete:{rec['error']}@batch_{bi}"
                    break
                for tok, mid in chunk:
                    row = dict.fromkeys(ROW_COLUMNS)
                    row.update(sweep_id=sweep_id, token_id=tok, market_id=mid, batch_index=bi,
                               batch_receipt_utc=rec["received_utc"])
                    if tok in books:
                        row.update(parse_book(books[tok]))
                    else:
                        row["state"] = "missing_from_response"
                    w.writerow({k: ("" if v is None else v) for k, v in row.items()})
                    rows_written += 1
        manifest = {
            "sweep_id": sweep_id,
            "series_id": series_id or sweep_id,
            "series_index": series_index,
            "sweep_version": SWEEP_VERSION,
            "endpoint": CLOB_URL,
            "snapshot_id": snapshot_id,
            "snapshot_manifest_sha256": snapshot_manifest_sha256,
            "started_utc": started,
            "finished_utc": _utc_now(),
            "state": state,
            "request_count": ctx["requests"],
            "batch_size": batch_size,
            "tokens_requested": len(tokens),
            "tokens_attempted": rows_written,
            "tokens_returned": n_returned,
            "rows_written": rows_written,
            "caps": {"max_requests": MAX_REQUESTS, "max_seconds": MAX_SECONDS,
                     "max_retries": MAX_RETRIES},
            "keep_raw": keep_raw,
            "hash_note": "sha256 of decoded response body",
            "code_commit": _git("rev-parse", "HEAD") or "unknown",
            "batches": batches,
            **(extra_manifest or {}),
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=1))
        os.rename(tmp, out_root / sweep_id)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return manifest


def run_series(
    snapshot_dir: Path,
    transport: Transport,
    *,
    repeat: int = 1,
    out_root: Path = SWEEP_ROOT,
    **kwargs: Any,
) -> list[dict]:
    """``repeat`` back-to-back sweeps over the same token list, linked by ``series_id``."""
    tokens, snap_manifest, snap_sha = load_tokens(Path(snapshot_dir))
    series_id = f"series_{_utc_now().replace('-', '').replace(':', '').replace('.', '')[:15]}Z_" \
                f"{uuid.uuid4().hex[:8]}"
    out = []
    for k in range(repeat):
        m = run_sweep(
            tokens, transport, out_root=out_root, series_id=series_id, series_index=k,
            snapshot_id=snap_manifest["capture_id"], snapshot_manifest_sha256=snap_sha,
            extra_manifest={"series_length": repeat}, **kwargs,
        )
        out.append(m)
        if m["state"] != "complete":
            break
    return out
