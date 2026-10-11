"""Free historical data sources for exploratory ML (research lab, ``exploratory_historical``).

(a) pmxt v2 hourly order-book archive -> ``book_sweep``-shaped rows (``load_book_snapshots``).
(b) Polymarket Data API ``/activity?user=`` -> as-of wallet history (``WalletHistory.lookup``).

Causality: a book snapshot at ``t`` uses only events with BOTH receipt clock and venue clock
<= t; a wallet lookup at ``t`` uses only activity with timestamp < t. Wallet history is
left-censored at the Data API's coverage and capped at ``max_events`` (``truncated`` flag).

Privacy: raw addresses live only inside ``WalletHistory.lookup`` (as a request parameter). Results
and the on-disk cache carry only the HMAC hash from ``wallet_sidecar.hash_wallet``; error
messages never include request URLs. Nothing here labels any wallet as informed or insider.
Read-only public endpoints, no keys. Not point-in-time metadata: this is exploratory data.
"""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import io
import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import book_sweep, forecast, wallet_sidecar

log = logging.getLogger(__name__)

HISTORY_VERSION = "history-sources-v1"
EVIDENCE_ROLE = "exploratory_historical"
ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "history_sources"
DISK_CAP_BYTES = 1_000_000_000
PMXT_BASE = "https://r2v2.pmxt.dev"
PMXT_LAST_HOUR = datetime(2026, 8, 10, 0, tzinfo=UTC)  # archive stopped publishing here
DATA_API = "https://data-api.polymarket.com"
USER_AGENT = "arepo-research-lab/1"

BOOK_COLUMNS = [*book_sweep.ROW_COLUMNS, "condition_id", "receipt_ts_ms", "venue_ts_ms",
                "crossed", "source"]


class SourceError(Exception):
    """Transport or protocol failure. Messages never contain URLs or addresses."""


def du_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) if root.exists() else 0


def check_disk_cap(root: Path = ROOT, cap: int = DISK_CAP_BYTES) -> None:
    if du_bytes(root) > cap:
        raise SourceError("history_sources disk cap exceeded")


# --- (a) pmxt order books -------------------------------------------------------------------

RangeFetch = Callable[[str, int, int], bytes]  # (url, first_byte, last_byte_inclusive)


def pmxt_url(hour: datetime) -> str:
    h = hour.astimezone(UTC)
    return f"{PMXT_BASE}/polymarket_orderbook_{h:%Y-%m-%dT%H}.parquet"


def httpx_range_fetch(timeout: float = 120.0) -> RangeFetch:
    import httpx

    client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True)

    def fetch(url: str, a: int, b: int) -> bytes:
        for attempt in range(4):
            try:
                r = client.get(url, headers={"Range": f"bytes={a}-{b}"})
            except httpx.HTTPError as exc:
                if attempt == 3:
                    raise SourceError(f"range fetch failed: {type(exc).__name__}") from None
                time.sleep(2.0 ** attempt)
                continue
            if r.status_code in (200, 206):
                return r.content
            if r.status_code == 404:
                raise FileNotFoundError("pmxt hour not published")
            if attempt == 3:
                raise SourceError(f"range fetch status {r.status_code}")
            time.sleep(2.0 ** attempt)
        raise SourceError("unreachable")

    return fetch


class RangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests, with a read-ahead block cache."""

    def __init__(self, url: str, size: int, fetch: RangeFetch, block: int = 1 << 20) -> None:
        self.url, self.size, self._fetch, self._block = url, size, fetch, block
        self._pos = 0
        self._cache, self._cache_start = b"", 0
        self.n_requests = 0
        self.bytes_fetched = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self._pos = offset if whence == 0 else self._pos + offset if whence == 1 else self.size + offset
        return self._pos

    def readinto(self, buf) -> int:
        n = len(buf)
        if n == 0 or self._pos >= self.size:
            return 0
        n = min(n, self.size - self._pos)
        if not (self._cache_start <= self._pos and self._pos + n <= self._cache_start + len(self._cache)):
            end = min(self.size, self._pos + max(n, self._block)) - 1
            self._cache = self._fetch(self.url, self._pos, end)
            self._cache_start = self._pos
            self.n_requests += 1
            self.bytes_fetched += len(self._cache)
        off = self._pos - self._cache_start
        data = self._cache[off: off + n]
        buf[: len(data)] = data
        self._pos += len(data)
        return len(data)


def httpx_size(url: str, timeout: float = 60.0) -> int:
    import httpx

    r = httpx.head(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    if r.status_code == 404:
        raise FileNotFoundError("pmxt hour not published")
    r.raise_for_status()
    return int(r.headers["content-length"])


def _levels(raw: Any) -> dict[Decimal, Decimal]:
    out: dict[Decimal, Decimal] = {}
    for p, s in json.loads(raw) if isinstance(raw, str) and raw else []:
        out[Decimal(str(p))] = Decimal(str(s))
    return out


def rebuild_book(events: Iterable[dict]) -> dict | None:
    """Rebuild one asset's book from time-ordered events (dicts with event_type, bids, asks, price,
    size, side, receipt_ms, venue_ms): last ``book`` then ``price_change`` (size is the new absolute
    level total, 0 removes). Events before the first ``book`` are ignored (no basis).
    Returns None when there is no ``book`` event."""
    bids: dict[Decimal, Decimal] | None = None
    asks: dict[Decimal, Decimal] = {}
    tick = None
    last_r = last_v = None
    for e in events:
        et = e["event_type"]
        if et == "book":
            bids, asks = _levels(e.get("bids")), _levels(e.get("asks"))
        elif et == "price_change" and bids is not None and e.get("price") is not None:
            side = bids if str(e.get("side")).upper() == "BUY" else asks
            p, s = Decimal(str(e["price"])), Decimal(str(e["size"]))
            if s <= 0:
                side.pop(p, None)
            else:
                side[p] = s
        elif et == "tick_size_change" and e.get("new_tick_size") is not None:
            tick = str(e["new_tick_size"])
            continue
        else:
            continue
        last_r, last_v = e["receipt_ms"], e["venue_ms"]
    if bids is None:
        return None
    mk = lambda d, rev: [{"price": str(p), "size": str(s)}  # noqa: E731
                         for p, s in sorted(d.items(), reverse=rev)]
    return {"bids": mk(bids, True), "asks": mk(asks, False), "tick_size": tick,
            "receipt_ms": last_r, "venue_ms": last_v}


def _iso_ms(ms: int | None) -> str | None:
    return None if ms is None else datetime.fromtimestamp(ms / 1000, UTC).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ")


def book_row(snapshot_id: str, condition_id: str, token_id: str, book: dict | None) -> dict:
    """One ``book_sweep.ROW_COLUMNS``-shaped row (plus extras). ``batch_receipt_utc`` is the receipt
    clock of the last applied event; ``book_timestamp`` the venue clock (ms epoch string)."""
    row = {c: None for c in BOOK_COLUMNS}
    row.update(sweep_id=snapshot_id, token_id=token_id, condition_id=condition_id,
               source="pmxt_v2", batch_index=0)
    if book is None:
        row["state"] = "no_book"
        return row
    row.update(book_sweep.parse_book({"bids": book["bids"], "asks": book["asks"],
                                      "timestamp": book["venue_ms"]}))
    row.update(batch_receipt_utc=_iso_ms(book["receipt_ms"]), receipt_ts_ms=book["receipt_ms"],
               venue_ts_ms=book["venue_ms"], tick_size=book["tick_size"])
    bb, ba = row["best_bid"], row["best_ask"]
    row["crossed"] = bool(bb is not None and ba is not None and bb >= ba)
    if row["crossed"]:
        row["state"] = "crossed"
    return row


def load_book_snapshots(t: datetime, token_ids: Iterable[str], *, fetch: RangeFetch | None = None,
                        size_fn: Callable[[str], int] | None = None,
                        lookback_hours: int = 1, stats: dict | None = None,
                        condition_ids: dict[str, str] | None = None) -> list[dict]:
    """Book snapshot per token as of ``t`` (UTC) from the hourly pmxt file containing ``t``.

    Rows with ``receipt > t`` or ``venue > t`` are excluded. If a token has no ``book`` event in
    that hour, up to ``lookback_hours`` earlier files are tried (state ``no_book`` otherwise).
    Row groups are pruned with the ``market`` min/max statistics (files are market-sorted) when
    ``condition_ids`` (token -> condition id) is given, which cuts transfer to a few MB per market;
    otherwise only the weak ``asset_id`` statistics are available and nearly the whole hour
    (~0.5 GB) is read. Pruning is a superset filter and never drops matching rows. ``stats`` receives request/byte counts.
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    t = t.astimezone(UTC)
    if t >= PMXT_LAST_HOUR:
        raise ValueError("pmxt v2 archive ends 2026-08-10T00")
    fetch = fetch or httpx_range_fetch()
    size_fn = size_fn or httpx_size
    wanted = {str(x) for x in token_ids}
    t_ms = int(t.timestamp() * 1000)
    rows: dict[str, dict] = {}
    cond: dict[str, str] = {}
    pending = set(wanted)
    st = stats if stats is not None else {}
    st.update(requests=0, bytes=0, row_groups_read=0, row_groups_total=0, hours=[])
    for back in range(lookback_hours + 1):
        if not pending:
            break
        hour = t.replace(minute=0, second=0, microsecond=0) - timedelta(hours=back)
        url = pmxt_url(hour)
        try:
            rf = RangeFile(url, size_fn(url), fetch)
        except FileNotFoundError:
            continue
        pf = pq.ParquetFile(rf)
        st["hours"].append(f"{hour:%Y-%m-%dT%H}")
        st["row_groups_total"] += pf.num_row_groups
        idx = pf.schema_arrow.get_field_index("asset_id")
        midx = pf.schema_arrow.get_field_index("market")
        ev: dict[str, list[dict]] = {a: [] for a in pending}
        cols = ["timestamp_received", "timestamp", "market", "event_type", "asset_id", "bids",
                "asks", "price", "size", "side", "new_tick_size"]
        for rg in range(pf.num_row_groups):
            rgm = pf.metadata.row_group(rg)
            if condition_ids:  # files are market-sorted: prune on market min/max (tight)
                ms = rgm.column(midx).statistics
                if ms is not None and ms.has_min_max:
                    lo, hi = _b(ms.min), _b(ms.max)
                    if not any(lo <= condition_ids[a].lower() <= hi for a in pending
                               if a in condition_ids):
                        continue
            else:  # asset_id order is not sorted within market-sorted files: weak pruning
                s = rgm.column(idx).statistics
                if s is not None and s.has_min_max and not any(s.min <= a <= s.max for a in pending):
                    continue
            tbl = pf.read_row_group(rg, columns=cols)
            st["row_groups_read"] += 1
            tbl = tbl.filter(pc.is_in(tbl["asset_id"], value_set=_arr(sorted(pending))))
            for r in tbl.to_pylist():
                rec = int(r["timestamp_received"].timestamp() * 1000)
                ven = int(r["timestamp"].timestamp() * 1000)
                if rec > t_ms or ven > t_ms:
                    continue
                m = r["market"]
                cond[r["asset_id"]] = m.decode() if isinstance(m, bytes) else str(m)
                ev[r["asset_id"]].append({**r, "receipt_ms": rec, "venue_ms": ven})
        st["requests"] += rf.n_requests
        st["bytes"] += rf.bytes_fetched
        for a in list(pending):
            lst = sorted(ev[a], key=lambda e: (e["venue_ms"], e["receipt_ms"]))
            book = rebuild_book(lst)
            if book is not None:
                rows[a] = book_row(f"pmxt:{t:%Y%m%dT%H%M%SZ}", cond.get(a, ""), a, book)
                pending.discard(a)
    for a in pending:
        rows[a] = book_row(f"pmxt:{t:%Y%m%dT%H%M%SZ}", cond.get(a, ""), a, None)
    return [rows[a] for a in sorted(rows)]


def _b(x) -> str:
    return (x.decode() if isinstance(x, bytes) else str(x)).lower()


def _arr(values: list[str]):
    import pyarrow as pa

    return pa.array(values, type=pa.string())


# --- (b) wallet history ---------------------------------------------------------------------

Get = Callable[[str, dict], tuple[int, Any, dict]]  # (path, params) -> (status, json, headers)


def httpx_get(timeout: float = 30.0) -> Get:
    import httpx

    client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def get(path: str, params: dict) -> tuple[int, Any, dict]:
        try:
            r = client.get(DATA_API + path, params=params)
        except httpx.HTTPError as exc:
            raise SourceError(f"transport error: {type(exc).__name__}") from None  # no URL
        try:
            body = r.json()
        except ValueError:
            body = None
        return r.status_code, body, dict(r.headers)

    return get


@dataclass
class RateLimiter:
    min_interval: float = 0.25  # <= 4 req/s
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    gate: Callable[[], None] | None = None  # called before every request (e.g. yield to live jobs)
    _last: float = field(default=0.0, init=False)

    def wait(self) -> None:
        if self.gate is not None:
            self.gate()
        d = self._last + self.min_interval - self.clock()
        if d > 0:
            self.sleep(d)
        self._last = self.clock()


def _event_key(it: dict) -> str:
    raw = f"{it.get('transactionHash')}|{it.get('asset')}|{it.get('type')}|{it.get('side')}|{it.get('size')}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]  # noqa: S324 - dedup fingerprint only


class WalletHistory:
    """As-of wallet history from ``/activity`` with a local cache keyed by wallet hash.

    Cache entry per hash: compact events ``[ts, type, side, usdc, key]`` ascending, and
    ``complete_through`` (all activity with ts <= it is present), ``truncated``.
    """

    PAGE = 500
    MAX_OFFSET = 4500  # API rejects offset > 5000 ("max historical activity offset")

    def __init__(self, cache_dir: Path | None = None, *, key: bytes | None = None,
                 get: Get | None = None, limiter: RateLimiter | None = None,
                 sleep: Callable[[float], None] = time.sleep, max_events: int = 20000,
                 max_retries: int = 5, max_requests: int = 60) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else ROOT / "wallet_cache"
        self._key = key if key is not None else wallet_sidecar.load_or_create_key()
        self._get = get or httpx_get()
        self._limiter = limiter or RateLimiter()
        self._sleep = sleep
        self.max_events, self.max_retries, self.max_requests = max_events, max_retries, max_requests
        self.n_requests = 0
        self.latencies: list[float] = []

    # cache -----------------------------------------------------------------------------
    def _path(self, h: str) -> Path:
        return self.cache_dir / f"{h}.json"

    def _load(self, h: str) -> dict:
        p = self._path(h)
        if p.exists():
            return json.loads(p.read_text())
        return {"events": [], "complete_through": None, "truncated": False}

    def _save(self, h: str, entry: dict) -> None:
        check_disk_cap(self.cache_dir.parent)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._path(h).with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, separators=(",", ":")))
        tmp.replace(self._path(h))

    # fetch -----------------------------------------------------------------------------
    def _page(self, params: dict) -> list[dict]:
        for attempt in range(self.max_retries):
            self._limiter.wait()
            t0 = time.monotonic()
            status, body, headers = self._get("/activity", params)
            self.latencies.append(time.monotonic() - t0)
            self.n_requests += 1
            if status == 200 and isinstance(body, list):
                return body
            if status in (429, 500, 502, 503, 504):
                ra = headers.get("retry-after") or headers.get("Retry-After")
                try:
                    delay = float(ra) if ra else min(30.0, 2.0 ** attempt)
                except ValueError:
                    delay = min(30.0, 2.0 ** attempt)
                self._sleep(delay)
                continue
            raise SourceError(f"activity status {status}")
        raise SourceError("activity retries exhausted")

    def _fetch(self, address: str, start: int | None, end: int, known: set[str]) -> tuple[list, bool]:
        """Ascending TRADE+REDEEM... activity in [start, end]; returns (events, truncated)."""
        out: list[list] = []
        cursor, offset, n_req = start, 0, 0
        while True:
            params = {"user": address, "limit": self.PAGE, "offset": offset, "end": end,
                      "sortBy": "TIMESTAMP", "sortDirection": "ASC"}
            if cursor is not None:
                params["start"] = cursor
            page = self._page(params)
            n_req += 1
            added = 0
            for it in page:
                k = _event_key(it)
                if k in known:
                    continue
                known.add(k)
                added += 1
                out.append([int(it["timestamp"]), str(it.get("type")), str(it.get("side") or ""),
                            round(float(it.get("usdcSize") or 0.0), 6), k])
            if len(page) < self.PAGE:
                return out, False
            # truncated: event cap, request cap, or a window that cannot advance (>5000 events
            # in one second), so counts are lower bounds
            if len(out) >= self.max_events or n_req >= self.max_requests or (
                    added == 0 and offset + self.PAGE > self.MAX_OFFSET):
                return out, True
            offset += self.PAGE
            if offset > self.MAX_OFFSET:  # slide the window: restart at the last timestamp
                cursor, offset = int(page[-1]["timestamp"]), 0

    # public ----------------------------------------------------------------------------
    def lookup(self, address: str, as_of_ts: int) -> dict:
        """History using only activity with ts < ``as_of_ts``. The address is never stored."""
        h = wallet_sidecar.hash_wallet(self._key, address)
        if h is None:
            raise ValueError("blank address")
        entry = self._load(h)
        through = entry["complete_through"]
        need_to = as_of_ts - 1
        if not entry["truncated"] and (through is None or through < need_to):
            known = {e[4] for e in entry["events"]}
            new, trunc = self._fetch(address, through, need_to, known)
            entry["events"].extend(new)
            entry["events"].sort(key=lambda e: (e[0], e[4]))
            entry["complete_through"] = need_to if not trunc else entry["events"][-1][0] - 1
            entry["truncated"] = trunc
            self._save(h, entry)
        return summarize(h, entry, as_of_ts)


def summarize(wallet_hash: str, entry: dict, as_of_ts: int) -> dict:
    ev = [e for e in entry["events"] if e[0] < as_of_ts]
    trades = [e for e in ev if e[1] == "TRADE"]
    buy = sum(e[3] for e in trades if e[2] == "BUY")
    sell = sum(e[3] for e in trades if e[2] == "SELL")
    redeem = sum(e[3] for e in ev if e[1] == "REDEEM")
    covered = entry["complete_through"] is not None and entry["complete_through"] >= as_of_ts - 1
    return {
        "wallet_hash": wallet_hash, "as_of_ts": as_of_ts,
        "first_activity_ts": ev[0][0] if ev else None,
        "first_trade_ts": trades[0][0] if trades else None,
        "n_prior_trades": len(trades), "prior_volume_usdc": round(buy + sell, 6),
        "prior_buy_usdc": round(buy, 6), "prior_sell_usdc": round(sell, 6),
        "prior_redeem_usdc": round(redeem, 6),
        # Cash-flow proxy, NOT PnL: open positions' cost is counted as a loss.
        "prior_net_cashflow_usdc": round(sell + redeem - buy, 6),
        "n_prior_events": len(ev),
        # truncated: only the earliest max_events are held, so counts/volume are lower bounds
        # (first_trade_ts is still exact); covered: cache fully spans (-inf, as_of).
        "truncated": bool(entry["truncated"]), "covered": bool(covered),
    }


def write_manifest(root: Path, name: str, payload: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    doc = {"history_version": HISTORY_VERSION, "evidence_role": EVIDENCE_ROLE,
           "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), **payload}
    p = root / f"{name}.manifest.json"
    p.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str))
    return p
