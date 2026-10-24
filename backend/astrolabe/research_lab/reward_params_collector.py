# ruff: noqa: E501
"""Keyless, write-once snapshot of Polymarket liquidity-reward parameters for every rewarded market.

Why: Gamma's ``clobRewards`` is null once a market closes and the CLOB rewards endpoints serve only
current (and future) configurations, so per-market reward rates cannot be recovered after the fact. The
2h snapshot sidecar keeps Gamma's native ``clobRewards`` but not the sponsored pool, the sponsor count or
the CLOB's computed daily totals. This collector keeps those, as served, at each capture.

Endpoints (docs.polymarket.com/api-reference/rewards, fetched 2026-10-19; ``security: []``):
  GET https://clob.polymarket.com/rewards/markets/current                 (500 per page, cursor)
  GET https://clob.polymarket.com/rewards/markets/current?sponsored=true  (sponsored configurations)
A full walk was about 28 + 1 requests, 17 s and 5 MB of JSON on 2026-10-20 (13,661 rewarded markets).

Output, one directory per capture, never overwritten (``capture_id`` = UTC stamp + random suffix):
  <out_root>/<capture_id>/rows.jsonl.gz   one line per (feed, market) record, verbatim plus ``feed``
  <out_root>/<capture_id>/manifest.json   endpoints, pages, counts, sha256 of rows, timings, state
The directory is written under a temporary name and renamed at the end; a failed capture leaves
``state: "failed"`` with whatever was received and is never completed later. Missing stays missing.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VERSION = "reward-params-v1"
BASE = "https://clob.polymarket.com/rewards/markets/current"
FEEDS = {"native": {}, "sponsored": {"sponsored": "true"}}
LAST_CURSOR = "LTE="
USER_AGENT = "arepo-research/1.0 (read-only research; keyless)"

Fetch = Callable[[str, dict], tuple[int, Any]]


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_capture_id(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(4)


def httpx_fetch(timeout: float = 30.0) -> Fetch:  # pragma: no cover - network
    import httpx

    client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def f(url: str, params: dict) -> tuple[int, Any]:
        r = client.get(url, params=params)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None

    return f


def walk_feed(fetch: Fetch, params: dict, max_pages: int = 200, min_interval_s: float = 0.5,
              max_retries: int = 4, sleep: Callable[[float], None] = time.sleep) -> tuple[list[dict], dict]:
    """All pages of one feed. Returns ``(records, stats)``; ``stats['complete']`` is False if a page
    failed after retries or the page cap was hit (the records received so far are still returned)."""
    recs: list[dict] = []
    cursor: str | None = None
    pages = requests = 0
    complete = False
    error = None
    while pages < max_pages:
        q = dict(params)
        if cursor:
            q["next_cursor"] = cursor
        status, body = 0, None
        for attempt in range(max_retries + 1):
            requests += 1
            status, body = fetch(BASE, q)
            if status == 200 and isinstance(body, dict):
                break
            sleep(min(30.0, 2.0 ** attempt))
        if status != 200 or not isinstance(body, dict):
            error = f"HTTP {status} on page {pages}"
            break
        data = body.get("data")
        if not isinstance(data, list):
            error = f"no data list on page {pages}"
            break
        recs.extend(x for x in data if isinstance(x, dict))
        pages += 1
        cursor = body.get("next_cursor")
        if not cursor or cursor == LAST_CURSOR:
            complete = True
            break
        sleep(min_interval_s)
    if not complete and error is None:
        error = f"page cap {max_pages} reached"
    return recs, {"pages": pages, "requests": requests, "records": len(recs), "complete": complete, "error": error}


def _rows_bytes(lines: list[dict]) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in lines:
            gz.write((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return buf.getvalue()


def capture(out_root: Path, fetch: Fetch, capture_id: str | None = None, max_pages: int = 200,
            min_interval_s: float = 0.5, sleep: Callable[[float], None] = time.sleep,
            code_commit: str | None = None) -> dict:
    """One write-once capture. Refuses (raises FileExistsError) if the capture directory exists."""
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    cid = capture_id or new_capture_id()
    final = out_root / cid
    if final.exists():
        raise FileExistsError(f"capture {cid} exists; captures are write-once")
    tmp = out_root / f".{cid}.partial"
    tmp.mkdir(parents=False, exist_ok=False)
    started = utc_now()
    lines: list[dict] = []
    feeds: dict = {}
    for name, params in FEEDS.items():
        t0 = time.time()
        recs, st = walk_feed(fetch, params, max_pages=max_pages, min_interval_s=min_interval_s, sleep=sleep)
        st["started_utc"], st["seconds"] = utc_now(), round(time.time() - t0, 2)
        feeds[name] = st
        lines.extend({"feed": name, **r} for r in recs)
    data = _rows_bytes(lines)
    (tmp / "rows.jsonl.gz").write_bytes(data)
    complete = all(f["complete"] for f in feeds.values())
    man = {"capture_id": cid, "version": VERSION, "endpoint": BASE, "feeds": feeds,
           "started_utc": started, "finished_utc": utc_now(),
           "state": "complete" if complete else "failed",
           "rows": len(lines), "markets_native": feeds["native"]["records"],
           "markets_sponsored": feeds["sponsored"]["records"],
           "rows_sha256": hashlib.sha256(data).hexdigest(), "rows_bytes": len(data),
           "code_commit": code_commit, "user_agent": USER_AGENT,
           "semantics": "verbatim CLOB records plus 'feed'; rate fields as served (USDC per day per docs); "
                        "start_date values roll forward, so a capture is the only record of the rate in force"}
    (tmp / "manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    os.replace(tmp, final)
    return man
