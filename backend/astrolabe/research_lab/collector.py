"""Compact point-in-time complete-universe Gamma snapshot collector (research lab).

Mirrors the Phase 3 frame contract (``astrolabe/research_panel/frame.py`` ``parse_page`` and
``GammaFrameRun.collect``; endpoint/params from ``feature_store/sources.py``
``gamma.markets.keyset``): GET ``/markets/keyset`` with ``closed=false``, ``limit=100``,
``after_cursor`` for continuation, ``Accept-Encoding: gzip``. A page is terminal only when
``next_cursor`` is omitted AND it holds fewer than ``limit`` markets; a continuing page must carry a
non-empty string cursor and exactly ``limit`` markets; a repeated cursor is a cycle. Anything else
is recorded as an incomplete capture. The heavy evidence machinery is deliberately not imported.

Row fields come from ``extract.market_row`` unchanged, so E001 panel code reads the output as-is.
``received_utc`` is the clock taken immediately after the full response body was received
(E001 history used first-byte receipt; the difference is the body transfer time of one page).
Page hashes are sha256 of the decoded (post-gzip) body. Raw bodies are not retained by default.
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
from pathlib import Path
from typing import Any

from .extract import COLUMNS, dedup_rows, market_row

COLLECTOR_VERSION = "universe-snapshot-v1"
ENDPOINT = "https://gamma-api.polymarket.com/markets/keyset"
PARAMS = {"closed": "false", "limit": 100}
HEADERS = {"Accept-Encoding": "gzip", "User-Agent": "arepo-research-lab/1"}
ROW_COLUMNS = [*COLUMNS, "page_index"]
MAX_RETRIES = 5
MAX_REQUESTS = 5000
MAX_SECONDS = 30 * 60
DELAY_SECONDS = 0.1
BACKOFF_BASE = 1.0
MAX_CURSOR_LEN = 8192

Transport = Callable[[dict], tuple[int, bytes, dict]]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def httpx_transport(timeout: float = 60.0) -> Transport:
    """Default transport: one reused httpx client, gzip accepted, body read fully."""
    import httpx

    client = httpx.Client(timeout=timeout, headers=HEADERS)

    def fetch(params: dict) -> tuple[int, bytes, dict]:
        resp = client.get(ENDPOINT, params=params)
        return resp.status_code, resp.content, dict(resp.headers)

    return fetch


def parse_page(raw: bytes, limit: int) -> tuple[list[dict], str | None, bool]:
    """Return (markets, next_cursor, terminal); raise ValueError on a protocol violation.

    Mirrors ``research_panel.frame.parse_page`` envelope rules.
    """
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("markets"), list):
        raise ValueError("markets envelope required")
    markets = payload["markets"]
    if len(markets) > limit:
        raise ValueError("page exceeds requested limit")
    if "next_cursor" in payload:
        cursor = payload["next_cursor"]
        if not isinstance(cursor, str) or not 1 <= len(cursor) <= MAX_CURSOR_LEN:
            raise ValueError("explicit null/empty cursor is not documented exhaustion")
        if len(markets) != limit:
            raise ValueError("continuing page count contradicts source protocol")
        return markets, cursor, False
    if len(markets) == limit:
        raise ValueError("full page missing cursor is not proven exhaustion")
    return markets, None, True


def _git_commit() -> str:
    try:
        root = Path(__file__).resolve().parents[3]
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _write_rows(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ROW_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def collect(
    out_root: Path,
    *,
    transport: Transport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    now: Callable[[], str] = _utc_now,
    delay: float = DELAY_SECONDS,
    max_requests: int = MAX_REQUESTS,
    max_seconds: float = MAX_SECONDS,
    keep_raw: bool = False,
    commit: str | None = None,
) -> dict:
    """Run one sequential full enumeration; return the manifest (also written to disk)."""
    transport = transport or httpx_transport()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    started = now()
    capture_id = (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    )
    tmp = out_root / f".tmp_{capture_id}"
    final = out_root / capture_id
    tmp.mkdir()
    raw_dir = tmp / "raw"
    if keep_raw:
        raw_dir.mkdir()

    t0 = monotonic()
    pages: list[dict] = []
    rows: list[dict] = []
    requests = retries = skipped_no_id = 0
    cursor: str | None = None
    seen: set[str] = set()
    last_receipt = ""
    state = None
    try:
        while state is None:
            params: dict[str, Any] = dict(PARAMS)
            if cursor is not None:
                params["after_cursor"] = cursor
            attempt = 0
            body = b""
            while True:
                if requests >= max_requests:
                    state = "incomplete:request_cap"
                    break
                if monotonic() - t0 >= max_seconds:
                    state = "incomplete:time_cap"
                    break
                requests += 1
                status, err, headers = 0, None, {}
                try:
                    status, body, headers = transport(params)
                except Exception as exc:  # transport failures are retryable I/O
                    err = type(exc).__name__
                received = now()
                if received < last_receipt:  # keep the receipt clock monotonic
                    received = last_receipt
                if err is None and status == 200:
                    break
                retryable = err is not None or status == 429 or status >= 500
                if not retryable:
                    state = f"incomplete:http_{status}"
                    break
                if attempt >= MAX_RETRIES:
                    state = f"incomplete:retry_exhausted:{err or status}"
                    break
                retries += 1
                wait = BACKOFF_BASE * 2**attempt
                try:
                    wait = max(wait, min(60.0, float(headers.get("retry-after", 0))))
                except (TypeError, ValueError):
                    pass
                attempt += 1
                sleep(wait)
            if state is not None:
                break
            last_receipt = received
            digest = hashlib.sha256(body).hexdigest()
            try:
                markets, nxt, terminal = parse_page(body, PARAMS["limit"])
            except ValueError as exc:
                state = f"incomplete:protocol:{exc}"
                break
            idx = len(pages)
            pages.append({
                "index": idx, "sha256": digest, "bytes": len(body),
                "n_markets": len(markets), "received_utc": received,
                "cursor_requested": cursor,
            })
            if keep_raw:
                with gzip.open(raw_dir / f"page_{idx:05d}.json.gz", "wb") as fh:
                    fh.write(body)
            for m in markets:
                r = market_row(m, capture_id, started, received) if isinstance(m, dict) else None
                if r is None:
                    skipped_no_id += 1
                    continue
                r["page_index"] = idx
                rows.append(r)
            if terminal:
                state = "complete"
            elif nxt in seen:
                state = "incomplete:cursor_cycle"
            else:
                seen.add(nxt)
                cursor = nxt
                sleep(delay)
    except BaseException as exc:  # keep an incomplete manifest, then re-raise
        state = f"incomplete:exception:{type(exc).__name__}"
        _finish(tmp, final, capture_id, started, now(), state, requests, retries, pages, rows,
                skipped_no_id, commit)
        raise
    return _finish(tmp, final, capture_id, started, now(), state, requests, retries, pages,
                   rows, skipped_no_id, commit)


def _finish(tmp, final, capture_id, started, finished, state, requests, retries, pages, rows,
            skipped_no_id, commit) -> dict:
    kept, n_dup = dedup_rows(rows)
    _write_rows(tmp / "rows.csv.gz", kept)
    manifest = {
        "capture_id": capture_id,
        "collector_version": COLLECTOR_VERSION,
        "code_commit": commit or _git_commit(),
        "source": "gamma.markets.keyset",
        "endpoint": ENDPOINT,
        "params": PARAMS,
        "started_utc": started,
        "finished_utc": finished,
        "state": state,
        "request_count": requests,
        "retry_count": retries,
        "page_count": len(pages),
        "market_objects": sum(p["n_markets"] for p in pages),
        "row_count": len(kept),
        "duplicates": n_dup,
        "skipped_without_id": skipped_no_id,
        "hash_note": "sha256 of decoded (post-gzip) response body",
        "pages": pages,
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if final.exists():
        shutil.rmtree(final)
    os.rename(tmp, final)
    return manifest
