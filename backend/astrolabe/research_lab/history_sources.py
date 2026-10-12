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
                        condition_ids: dict[str, str] | None = None,
                        gate: Callable[[], None] | None = None) -> list[dict]:
    """Book snapshot per token as of ``t`` (UTC) from the hourly pmxt file containing ``t``.

    Rows with ``receipt > t`` or ``venue > t`` are excluded. If a token has no ``book`` event in
    that hour, up to ``lookback_hours`` earlier files are tried (state ``no_book`` otherwise).
    Row groups are pruned with the ``market`` min/max statistics (files are market-sorted) when
    ``condition_ids`` (token -> condition id) is given, which cuts transfer to a few MB per market;
    otherwise only the weak ``asset_id`` statistics are available and nearly the whole hour
    (~0.5 GB) is read. Pruning is a superset filter and never drops matching rows. ``stats`` receives request/byte counts.
    """
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    t = t.astimezone(UTC)
    if t >= PMXT_LAST_HOUR:
        raise ValueError("pmxt v2 archive ends 2026-08-10T00")
    fetch = fetch or httpx_range_fetch()
    size_fn = size_fn or httpx_size
    wanted = {str(x) for x in token_ids}
    t_ms = int(t.timestamp() * 1000)
    t_ts = pa.scalar(t_ms, pa.timestamp("ms", "UTC"))
    rows: dict[str, dict] = {}
    cond: dict[str, str] = {}
    pending = set(wanted)
    st = stats if stats is not None else {}
    st.update(requests=0, bytes=0, row_groups_read=0, row_groups_total=0, hours=[])
    for back in range(lookback_hours + 1):
        if not pending:
            break
        # an origin exactly on the hour has no usable events in its own hour file (receipt >= t)
        hour = (t - timedelta(milliseconds=1)).replace(minute=0, second=0, microsecond=0) \
            - timedelta(hours=back)
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
            if gate is not None:
                gate()
            light = pf.read_row_group(rg, columns=_LIGHT)
            keep = pc.and_(pc.is_in(light["asset_id"], value_set=_arr(sorted(pending))),
                           pc.and_(pc.less_equal(light["timestamp_received"], t_ts),
                                   pc.less_equal(light["timestamp"], t_ts)))
            if not pc.any(keep).as_py():
                continue  # heavy columns (bids/asks) are never fetched for this row group
            st["row_groups_read"] += 1
            tbl = pf.read_row_group(rg, columns=cols).filter(keep)
            for r in tbl.to_pylist():
                rec = int(r["timestamp_received"].timestamp() * 1000)
                ven = int(r["timestamp"].timestamp() * 1000)
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


_LIGHT = ["timestamp_received", "timestamp", "asset_id"]


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
    def first_trade(self, address: str, end_ts: int) -> dict:
        """Earliest TRADE activity at or before ``end_ts`` (1 request; exact; address not stored).
        ``first_trade_ts`` None means the API holds no trade for the wallet up to ``end_ts``."""
        h = wallet_sidecar.hash_wallet(self._key, address)
        if h is None:
            raise ValueError("blank address")
        page = self._page({"user": address, "type": "TRADE", "limit": 1, "offset": 0,
                           "end": int(end_ts), "sortBy": "TIMESTAMP", "sortDirection": "ASC"})
        return {"wallet_hash": h, "first_trade_ts": int(page[0]["timestamp"]) if page else None,
                "end_ts": int(end_ts)}

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


# --- historical book features (pmxt) for the history ML panels -------------------------------

PMXT_V2_START = datetime(2026, 4, 13, 19, tzinfo=UTC)
PMXT_GAP = (datetime(2026, 6, 12, tzinfo=UTC), datetime(2026, 6, 18, tzinfo=UTC))  # absent days
ORIGIN_STEP_S = 6 * 3600
SW_KEYS = ("sw_best_bid", "sw_best_ask", "sw_bid_size_1", "sw_ask_size_1", "sw_depth_bid_1c",
           "sw_depth_ask_1c", "sw_depth_bid_5c", "sw_depth_ask_5c", "sw_n_bid_levels",
           "sw_n_ask_levels", "sw_book_age_s")
JOIN_KEYS = ("market_id", "origin_ts")  # market_id str (Gamma id), origin_ts = panel ``t_i`` epoch s


def swap_free_mb() -> float | None:
    import re
    import subprocess

    try:
        out = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True,
                             timeout=10).stdout
        m = re.search(r"free = ([\d.]+)M", out)
        return float(m.group(1)) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def heavy_gate(min_swap_free_mb: float = 250.0, sleep: Callable[[float], None] = time.sleep) -> float:
    """Wait while the live collector pass runs or swap headroom is below ``min_swap_free_mb``."""
    from . import history_backfill as hb

    waited = 0.0
    while True:
        free = swap_free_mb()
        if hb.live_pass_running() or (free is not None and free < min_swap_free_mb):
            sleep(30.0)
            waited += 30.0
            continue
        return waited


def origin_in_window(ts: float) -> bool:
    t = datetime.fromtimestamp(ts, UTC)
    return PMXT_V2_START <= t < PMXT_LAST_HOUR and not (PMXT_GAP[0] <= t < PMXT_GAP[1])


def panel_pairs(panel_paths: Iterable[Path]) -> dict[float, set[str]]:
    """{origin_ts: {market_id}} for 6h-aligned panel origins inside the pmxt window."""
    import pandas as pd

    out: dict[float, set[str]] = {}
    for p in panel_paths:
        df = pd.read_csv(p, usecols=["market_id", "t_i"], dtype={"market_id": str})
        df = df[(df.t_i % ORIGIN_STEP_S == 0)].drop_duplicates()
        for t, m in zip(df.t_i.astype(float), df.market_id, strict=True):
            if origin_in_window(t):
                out.setdefault(t, set()).add(m)
    return out


def load_frame_tokens(frame_paths: Iterable[Path]) -> dict[str, tuple[str, str]]:
    """{market_id: (condition_id, outcome-0 token id)} from backfill ``frame.csv.gz`` files."""
    import pandas as pd

    out: dict[str, tuple[str, str]] = {}
    for p in frame_paths:
        df = pd.read_csv(p, usecols=["market_id", "condition_id", "token0"], dtype=str)
        for m, c, t0 in zip(df.market_id, df.condition_id, df.token0, strict=True):
            if isinstance(c, str) and isinstance(t0, str):
                out.setdefault(m, (c.lower(), t0))
    return out


def spread_origin_order(origins: list[float]) -> list[float]:
    """Deterministic order that spreads partial coverage over the whole window (stride 7 passes)."""
    o = sorted(origins)
    return [x for k in range(7) for x in o[k::7]]


def sw_row(book_row_: dict, t: float) -> dict:
    """``sw_*`` columns (same meaning as ``ml_panel.sweep_columns``) from one pmxt book row.
    ``sw_book_age_s`` = origin minus the last applied event's venue clock (not a sweep batch lag)."""
    nan = float("nan")
    r = book_row_

    def f(k, scale=1.0):
        v = r.get(k)
        return nan if v is None else float(v) * scale

    ok = r.get("state") in ("two_sided", "one_sided", "empty")  # crossed books are noise: NaN
    out = {k: nan for k in SW_KEYS}
    if ok:
        out.update(sw_best_bid=f("best_bid"), sw_best_ask=f("best_ask"),
                   sw_bid_size_1=f("bid_size_1"), sw_ask_size_1=f("ask_size_1"),
                   sw_depth_bid_1c=f("depth_bid_1c"), sw_depth_ask_1c=f("depth_ask_1c"),
                   sw_depth_bid_5c=f("depth_bid_5c"), sw_depth_ask_5c=f("depth_ask_5c"),
                   sw_n_bid_levels=f("n_bid_levels"), sw_n_ask_levels=f("n_ask_levels"))
        v = r.get("venue_ts_ms")
        out["sw_book_age_s"] = nan if v is None or t - v / 1000 < 0 else t - v / 1000
    return out


def ml_sw_columns(df):
    """``ml_sw_*`` features computed by ml_panel's own registered functions (read-only reuse)."""
    import pandas as pd

    from . import ml_panel

    out = pd.DataFrame(index=df.index)
    for name, _fam, _req, fn in ml_panel._EXT:
        if name.startswith("ml_sw_"):
            out[name] = fn(df).to_numpy(float)
    return out


class BookFeatureRun:
    """Resumable origin-by-origin pmxt book feature extraction. Raw hours are never stored: each
    origin appends compact rows to ``rows.jsonl`` and its timestamp to ``progress.jsonl``."""

    def __init__(self, out_dir: Path, pairs: dict[float, set[str]], tokens: dict, *,
                 fetch: RangeFetch | None = None, size_fn=None, gate=None,
                 lookback_hours: int = 1) -> None:
        self.dir, self.pairs, self.tokens = Path(out_dir), pairs, tokens
        self.fetch, self.size_fn, self.gate, self.lookback = fetch, size_fn, gate, lookback_hours
        self.dir.mkdir(parents=True, exist_ok=True)
        self.done = self._done()

    def _done(self) -> set[float]:
        p = self.dir / "progress.jsonl"
        return {json.loads(x)["origin_ts"] for x in p.read_text().splitlines() if x} if p.exists() else set()

    def run(self, budget_s: float, max_origins: int | None = None,
            clock: Callable[[], float] = time.monotonic) -> dict:
        t0, n_done, n_rows, total_bytes = clock(), 0, 0, 0
        for ot in spread_origin_order([o for o in self.pairs if o not in self.done]):
            if clock() - t0 > budget_s or (max_origins is not None and n_done >= max_origins):
                break
            check_disk_cap(self.dir.parent)
            mk = sorted(m for m in self.pairs[ot] if m in self.tokens)
            toks = {self.tokens[m][1]: m for m in mk}
            cond = {self.tokens[m][1]: self.tokens[m][0] for m in mk}
            st: dict = {}
            tt = clock()
            rows = load_book_snapshots(
                datetime.fromtimestamp(ot, UTC), list(toks), fetch=self.fetch, size_fn=self.size_fn,
                lookback_hours=self.lookback, stats=st, condition_ids=cond, gate=self.gate) if toks else []
            with (self.dir / "rows.jsonl").open("a") as fh:
                for r in rows:
                    rec = {"market_id": toks[r["token_id"]], "origin_ts": ot,
                           "token_id": r["token_id"], "condition_id": cond[r["token_id"]],
                           "state": r["state"], "crossed": r.get("crossed"),
                           "receipt_ts_ms": r.get("receipt_ts_ms"), "venue_ts_ms": r.get("venue_ts_ms"),
                           **sw_row(r, ot)}
                    fh.write(json.dumps(rec, allow_nan=True) + "\n")
            with (self.dir / "progress.jsonl").open("a") as fh:
                fh.write(json.dumps({"origin_ts": ot, "n_markets": len(rows), "bytes": st.get("bytes", 0),
                                     "requests": st.get("requests", 0), "seconds": round(clock() - tt, 1),
                                     "hours": st.get("hours", [])}) + "\n")
            self.done.add(ot)
            n_done += 1
            n_rows += len(rows)
            total_bytes += st.get("bytes", 0)
        return {"origins_done_this_run": n_done, "rows_this_run": n_rows, "bytes_this_run": total_bytes,
                "origins_done_total": len(self.done), "origins_total": len(self.pairs),
                "seconds": round(clock() - t0, 1)}


def finalize_book_features(out_dir: Path) -> Path:
    """Write ``book_features.csv.gz`` (+ manifest): one row per (market_id, origin_ts)."""
    import pandas as pd

    out_dir = Path(out_dir)
    df = pd.read_json(out_dir / "rows.jsonl", lines=True, dtype={"market_id": str, "token_id": str})
    df["market_id"] = df["market_id"].astype(str)
    df = df.drop_duplicates(list(JOIN_KEYS), keep="last").sort_values(list(JOIN_KEYS))
    df = pd.concat([df.reset_index(drop=True), ml_sw_columns(df.reset_index(drop=True))], axis=1)
    df["evidence_role"] = EVIDENCE_ROLE
    path = out_dir / "book_features.csv.gz"
    df.to_csv(path, index=False)
    prog = [json.loads(x) for x in (out_dir / "progress.jsonl").read_text().splitlines() if x]
    write_manifest(out_dir, "book_features", {
        "join_keys": list(JOIN_KEYS), "rows": len(df), "markets": int(df.market_id.nunique()),
        "origins": int(df.origin_ts.nunique()), "state_counts": df.state.value_counts().to_dict(),
        "bytes_streamed": sum(p["bytes"] for p in prog), "requests": sum(p["requests"] for p in prog),
        "fetch_seconds": round(sum(p["seconds"] for p in prog), 1),
        "clock_rule": "events used only if receipt and venue clocks <= origin_ts",
        "source": "pmxt v2 hourly parquet", "window": "2026-04-13T19 to 2026-08-10 minus 06-12..06-17",
        "origin_grid": "6h (00,06,12,18 UTC), panel t_i", "outcome": "token 0 (clob_token_id_0)"})
    return path


def load_book_features(path: Path):
    """Join table for the history ML run: ``merge(on=['market_id','origin_ts'])`` with panel
    ``market_id`` (str) and ``t_i``. Columns: sw_* raw, ml_sw_* features, state, receipt/venue ms."""
    import pandas as pd

    df = pd.read_csv(path, dtype={"market_id": str, "token_id": str, "condition_id": str})
    df["origin_ts"] = df["origin_ts"].astype(float)
    return df



# --- new-wallet features for the backfill trades ---------------------------------------------

NW_WINDOW_S = 86400
NW_DAYS = (1, 7, 30)
NW_COLS = ["nw_n_trades_24h", "nw_cov_vol_24h",
           *[f"nw_share_new{n}d" for n in NW_DAYS], *[f"nw_n_new{n}d" for n in NW_DAYS]]


def fetch_market_wallets(lim, condition_id: str, key: bytes, known: set[str],
                         max_trades: int = 11000) -> dict[str, list]:
    """Transient: {hash: [raw_address, notional]} for stored wallets, from the public trades
    endpoint (same paging as the backfill). The caller must never persist the addresses."""
    from . import history_backfill as hb

    out: dict[str, list] = {}
    off = 0
    while off < max_trades:
        status, data = lim.get(hb.DATA_TRADES, {"market": condition_id, "limit": hb.TRADE_PAGE,
                                                "offset": off})
        if status != 200 or not isinstance(data, list):
            break
        for t in data:
            try:
                addr = str(t["proxyWallet"])
                h = wallet_sidecar.hash_wallet(key, addr)
                if h in known:
                    e = out.setdefault(h, [addr, 0.0])
                    e[1] += float(t["size"]) * float(t["price"])
            except (KeyError, TypeError, ValueError):
                continue
        if len(data) < hb.TRADE_PAGE:
            break
        off += hb.TRADE_PAGE
    return out


def _read_first_trades(path: Path) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line:
                d = json.loads(line)
                out[d["wallet_hash"]] = d["first_trade_ts"]
    return out


def run_wallet_step(hist: Path, runs: Iterable[str], out_dir: Path, budget_s: float,
                    max_wallets: int = 20000, gate: Callable[[], None] | None = None) -> dict:
    """Phase 1 (transient): re-read trades of the panel markets to recover addresses, rank wallets
    by notional (panel markets first). Phase 2: one /activity request per wallet (first TRADE at or
    before the wallet's earliest stored trade). Output ``first_trade.jsonl`` (hashes only)."""
    import pandas as pd

    from . import history_backfill as hb

    out_dir.mkdir(parents=True, exist_ok=True)
    ft_path = out_dir / "first_trade.jsonl"
    done = _read_first_trades(ft_path)
    key = wallet_sidecar.load_or_create_key()
    lim = hb.Limiter(hb.httpx_transport(), rps=4.0, live_check=hb.live_pass_running)
    markets: list[tuple[int, str, str, dict, int]] = []  # (priority, market_id, condition, hashes->(first_ts))
    for r in runs:
        rd = Path(hist) / r
        if not (rd / "frame.csv.gz").exists():
            continue
        panel = rd / "panel_H6h.csv.gz"
        in_panel = set(pd.read_csv(panel, usecols=["market_id"], dtype=str).market_id) if panel.exists() else set()
        fr = pd.read_csv(rd / "frame.csv.gz", usecols=["market_id", "condition_id"], dtype=str)
        cond = dict(zip(fr.market_id, fr.condition_id, strict=True))
        for f in sorted((rd / "trades").glob("*.csv.gz")):
            mid = f.name.split(".")[0]
            if mid in cond:
                markets.append((0 if mid in in_panel else 1, mid, cond[mid], f, 0))
    markets.sort(key=lambda x: (x[0], x[1]))
    t0 = time.monotonic()
    wallets: dict[str, list] = {}  # hash -> [addr, notional, earliest stored ts, priority]
    n_markets = 0
    for pri, _mid, cid, f, _ in markets:
        if time.monotonic() - t0 > budget_s * 0.4:
            break
        if gate:
            gate()
        tr = pd.read_csv(f, usecols=["ts", "wallet_hash"], dtype={"wallet_hash": str})
        first_ts = tr.groupby("wallet_hash").ts.min().to_dict()
        known = {h for h in first_ts if h not in done}
        if not known:
            continue
        for h, (addr, notional) in fetch_market_wallets(lim, cid, key, known).items():
            e = wallets.setdefault(h, [addr, 0.0, first_ts[h], pri])
            e[1] += notional
            e[2] = min(e[2], first_ts[h])
            e[3] = min(e[3], pri)
        n_markets += 1
    order = sorted(wallets.items(), key=lambda kv: (kv[1][3], -kv[1][1]))[:max_wallets]
    wh = WalletHistory(out_dir / "unused_cache", key=key,
                       limiter=RateLimiter(0.25, gate=gate or hb.yield_to_live))
    n_ok = n_err = 0
    with ft_path.open("a") as fh:
        for _h, (addr, _n, ets, _p) in order:
            if time.monotonic() - t0 > budget_s:
                break
            check_disk_cap(out_dir.parent)
            try:
                res = wh.first_trade(addr, int(ets))
            except SourceError:
                n_err += 1
                continue
            fh.write(json.dumps({"wallet_hash": res["wallet_hash"], "first_trade_ts": res["first_trade_ts"],
                                 "end_ts": res["end_ts"]}) + "\n")
            n_ok += 1
    wallets.clear()  # drop raw addresses
    lat = sorted(wh.latencies)
    summ = {"markets_scanned": n_markets, "markets_total": len(markets), "candidates": len(order),
            "lookups_ok": n_ok, "lookups_err": n_err, "lookup_requests": wh.n_requests,
            "trade_requests": lim.requests, "seconds": round(time.monotonic() - t0, 1),
            "latency_p50": round(lat[len(lat) // 2], 3) if lat else None,
            "first_trade_known_total": len(_read_first_trades(ft_path))}
    write_manifest(out_dir, "first_trade_run", summ)
    return summ


def new_wallet_features(panel_path: Path, trades_dir: Path, progress_path: Path,
                        first_trade_path: Path):
    """Per (market_id, origin_ts=t_i): new-wallet shares and counts over trades in [t-24h, t).

    A trade is "new at N days" when ``trade_ts - first_trade_ts < N*86400``. Shares use only
    volume (size*price) of wallets with a known first trade (``nw_cov_vol_24h`` is that coverage);
    NaN when there is no covered volume, or when a truncated trade history does not reach back to
    the window start."""
    import numpy as np
    import pandas as pd

    ft = _read_first_trades(first_trade_path)
    prog = {}
    if Path(progress_path).exists():
        for line in Path(progress_path).read_text().splitlines():
            if line:
                d = json.loads(line)
                prog[str(d["market_id"])] = d
    pan = pd.read_csv(panel_path, usecols=["market_id", "t_i"], dtype={"market_id": str}).drop_duplicates()
    out = []
    for mid, g in pan.groupby("market_id"):
        t = np.sort(g.t_i.to_numpy(float))
        f = Path(trades_dir) / f"{mid}.csv.gz"
        base = {c: np.full(len(t), np.nan) for c in NW_COLS}
        if f.exists():
            tr = pd.read_csv(f, usecols=["ts", "size", "price", "wallet_hash"],
                             dtype={"wallet_hash": str}).sort_values("ts")
            ts = tr.ts.to_numpy(float)
            vol = (tr["size"] * tr["price"]).to_numpy(float)
            fts = tr.wallet_hash.map(lambda h: ft.get(h)).astype(float).to_numpy()
            known = ~np.isnan(fts)
            age = np.where(known, ts - fts, np.nan)
            wh_ = tr.wallet_hash.to_numpy()
            lo = np.searchsorted(ts, t - NW_WINDOW_S, side="left")
            hi = np.searchsorted(ts, t, side="left")  # strictly before the origin
            p = prog.get(str(mid), {})
            covered_from = p.get("trades_oldest_ts") if p.get("trades_truncated") else -np.inf
            base["nw_n_trades_24h"] = (hi - lo).astype(float)
            for i in range(len(t)):
                a, b = lo[i], hi[i]
                if covered_from is not None and t[i] - NW_WINDOW_S < covered_from:
                    base["nw_n_trades_24h"][i] = np.nan
                    continue
                if b <= a:
                    continue
                tot = vol[a:b].sum()
                kv = vol[a:b][known[a:b]].sum()
                base["nw_cov_vol_24h"][i] = kv / tot if tot > 0 else np.nan
                if kv <= 0:
                    continue
                for n in NW_DAYS:
                    new = known[a:b] & (age[a:b] < n * 86400)
                    base[f"nw_share_new{n}d"][i] = vol[a:b][new].sum() / kv
                    base[f"nw_n_new{n}d"][i] = len(set(wh_[a:b][new]))
        df = pd.DataFrame(base)
        df.insert(0, "origin_ts", t)
        df.insert(0, "market_id", str(mid))
        out.append(df)
    res = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["market_id", "origin_ts", *NW_COLS])
    res["evidence_role"] = EVIDENCE_ROLE
    return res


def load_new_wallet_features(path: Path):
    """Join on ``market_id`` (str) and ``origin_ts`` (= panel ``t_i``, float epoch seconds)."""
    import pandas as pd

    df = pd.read_csv(path, dtype={"market_id": str})
    df["origin_ts"] = df["origin_ts"].astype(float)
    return df
