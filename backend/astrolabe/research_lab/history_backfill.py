"""EXPLORATORY historical backfill for ML development (research lab).

Provenance ``EXPLORATORY_HISTORICAL``: data fetched after the fact from public no-key endpoints
(CLOB ``prices-history``, Data API ``trades``, Gamma ``markets``). It is for developing and
debugging the ML pipeline only. It is NOT prospective, NOT point-in-time snapshots, and must never
be counted as prospective confirmation, pooled with prospective panels, or used for any edge claim.

Probe findings (2026-10-11, see ``PROBE_FINDINGS``) drive the design:

* ``prices-history`` with ``interval=max`` returns nothing at fine fidelity for closed markets; an
  explicit ``startTs``/``endTs`` window of at most 14 days works at any fidelity, so series are
  fetched in 14-day windows at ``fidelity=10`` minutes (nominal spacing ~594-600 s).
* Data API ``trades`` is newest-first, ``limit`` up to 10000 and ``offset`` up to 10000 (HTTP 400
  beyond), so deep history of very liquid markets is unreachable; truncation is recorded per market
  and trade-flow features are NaN wherever a lookback window is not fully covered.
* Gamma ``/markets`` offset is capped near 2100 (HTTP 422), so the closed universe is walked in
  one-day ``end_date`` windows and the active universe in liquidity slices.

Wallet addresses are never stored: only ``HMAC-SHA256(local key, lowercase address)``. The key lives
in ``~/.arepo/wallet_hash_key`` (mode 600), is generated once and is never printed or committed.

Panel (``build_panel``): fixed 2h UTC grid; origin features use the price series at or before ``t``
and trades strictly before ``t``; targets are the last series price at or before ``t + H`` (no
interpolation, no imputation). Book/liquidity features stay NaN. Static Gamma fields (current
liquidity, volume) are used for stratification only, never as features, because for closed markets
they are end-of-life values (look-ahead).
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import hmac
import json
import math
import os
import time
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from astrolabe.research_panel.pairing import fee_category

from . import ml_panel
from .wallet_sidecar import hash_wallet, load_or_create_key

PROVENANCE = "EXPLORATORY_HISTORICAL"
EVIDENCE_ROLE = "exploratory_historical"
HISTORY_VERSION = "history-backfill-v1"
GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
CLOB_PRICES = "https://clob.polymarket.com/prices-history"
DATA_TRADES = "https://data-api.polymarket.com/trades"
HEADERS = {"User-Agent": "arepo-research-lab/1", "Accept-Encoding": "gzip"}

FIDELITY_MIN = 10
WINDOW_DAYS = 14  # 30-day windows were rejected (HTTP 400) in the probe
TRADE_PAGE = 1000
TRADE_OFFSET_CAP = 10000
GAMMA_PAGE = 100
GAMMA_OFFSET_CAP = 2000
MAX_RPS = 5.0
MAX_RETRIES = 6
DISK_CAP_BYTES = int(1.5 * 1024**3)
GRID_S = 7200
HORIZONS_H = (2, 6, 24)
POINT_LAG_S = 600  # a point stamped t' is usable only if t' + lag < t (interval-start safe)
MAX_QUOTE_AGE_S = 7200  # series point older than this at the origin: no quote, row dropped
MID_RANGE = (0.02, 0.98)  # exploratory eligibility on the origin price
KEY_PATH = Path.home() / ".arepo" / "wallet_hash_key"
DEFAULT_ROOT = Path("data-dumps/research_lab/history")

PROBE_FINDINGS = {
    "date": "2026-10-11",
    "prices_history": {
        "closed_markets": "available; interval=max at fidelity 10/60 returned [] for a resolved "
        "market, fidelity 1440 returned 29 daily points; startTs/endTs windows work",
        "window_limit_days": "14 ok, 30 -> HTTP 400",
        "granularity": "fidelity=N minutes, point spacing ~594-600 s at 10 min",
        "active_interval_max": "fidelity 1/10 gave 4313 points (~10 min), fidelity 60 gave 718",
        "timestamps": "venue-stamped unix seconds (t), no receipt time",
        "price_semantics": "p is a single price per point; whether last-trade or mid is NOT "
        "stated by the API (recorded as 'unverified'); treat as a price proxy",
    },
    "trades": {
        "order": "newest first",
        "limit_max": "10000 accepted",
        "offset_cap": "offset 10000 ok, 20000 -> HTTP 400 'max historical trades offset of 10000'",
        "fields": "proxyWallet, side, size, price, timestamp (venue unix s), outcomeIndex, "
        "transactionHash (plus name/pseudonym/bio which are NOT stored)",
        "closed_markets": "available (trades after closedTime also returned)",
    },
    "rate_limit": "clob prices-history: 40 requests in 3.6 s all 200; data-api trades: 40 requests "
    "in 8.5 s produced some HTTP 429 -> shared 5 rps limiter with exponential backoff",
    "gamma": "closed=true with end_date_min/end_date_max and volume_num_min works; offset > ~2100 "
    "-> HTTP 422",
}

Transport = Callable[[str, dict], tuple[int, bytes, dict]]


def utc_iso(ts: float | None = None) -> str:
    dt = datetime.now(UTC) if ts is None else datetime.fromtimestamp(ts, UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------------------------
# Transport, limiter
# ---------------------------------------------------------------------------------------------


def httpx_transport(timeout: float = 60.0) -> Transport:
    import httpx

    client = httpx.Client(timeout=timeout, headers=HEADERS)

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


LIVE_PASS_PATTERN = "arepo_pass.sh"
LIVE_POLL_S = 30.0


def live_pass_running() -> bool:
    """True while the live prospective collector pass is running (pgrep -f arepo_pass.sh)."""
    import subprocess

    try:
        return subprocess.run(["pgrep", "-f", LIVE_PASS_PATTERN], capture_output=True,
                              timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def yield_to_live(is_running: Callable[[], bool] = live_pass_running,
                  sleep: Callable[[float], None] = time.sleep) -> float:
    """Exploratory API traffic always yields to the live collector: while the pass runs, sleep
    30 s and re-check. Returns the seconds waited."""
    waited = 0.0
    while is_running():
        sleep(LIVE_POLL_S)
        waited += LIVE_POLL_S
    return waited


class Limiter:
    """Global request pacing (<= ``rps``) and exponential backoff on 429/5xx/transport errors."""

    def __init__(self, transport: Transport, rps: float = MAX_RPS,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic,
                 live_check: Callable[[], bool] | None = None) -> None:
        self.transport, self.min_gap = transport, 1.0 / rps
        self.live_check, self.yielded_s, self._last_live = live_check, 0.0, -1e9
        self.sleep, self.clock = sleep, clock
        self.last = -1e9
        self.requests = 0
        self.retries = 0
        self.throttled = 0
        self.log: list[dict] = []

    def get(self, url: str, params: dict) -> tuple[int, Any]:
        """Returns (status, parsed JSON) for 200/400/404/422; raises after MAX_RETRIES."""
        for attempt in range(MAX_RETRIES + 1):
            if self.live_check is not None and self.clock() - self._last_live >= 2.0:
                self.yielded_s += yield_to_live(self.live_check, self.sleep)
                self._last_live = self.clock()
            wait = self.min_gap - (self.clock() - self.last)
            if wait > 0:
                self.sleep(wait)
            self.last = self.clock()
            self.requests += 1
            try:
                status, body, headers = self.transport(url, params)
            except Exception as exc:  # network error: back off and retry
                status, body, headers = 599, b"", {"error": type(exc).__name__}
            if status in (200, 400, 404, 422):
                try:
                    return status, json.loads(body) if body else None
                except ValueError:
                    status = 599
            if attempt == MAX_RETRIES:
                break
            self.retries += 1
            if status == 429:
                self.throttled += 1
            ra = next((v for k, v in headers.items() if str(k).lower() == "retry-after"), None)
            delay = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else 2.0**attempt
            self.sleep(min(delay, 60.0))
        raise RuntimeError(f"giving up after {MAX_RETRIES} retries ({url})")


# ---------------------------------------------------------------------------------------------
# Wallet hashing
# ---------------------------------------------------------------------------------------------


def wallet_hash(key: bytes, address: str) -> str:
    """Identical to the live wallet sidecar's hash (lower-cased, HMAC-SHA256, raw key verbatim)."""
    h = hash_wallet(key, address)
    return h if h is not None else hash_wallet(key, "__blank__")  # type: ignore[return-value]


def key_id(key: bytes) -> str:
    """Public, non-reversible label of the key (HMAC of a constant), for manifest consistency."""
    return hmac.new(key, b"arepo-key-id", hashlib.sha256).hexdigest()[:8]


# ---------------------------------------------------------------------------------------------
# Disk budget
# ---------------------------------------------------------------------------------------------


class DiskBudget:
    """Hard cap on bytes under ``root`` (the whole history tree, all runs)."""

    def __init__(self, root: Path, cap: int = DISK_CAP_BYTES) -> None:
        self.root, self.cap = Path(root), cap
        self.used = self.scan()

    def scan(self) -> int:
        if not self.root.exists():
            return 0
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    def charge(self, nbytes: int) -> None:
        if self.used + nbytes > self.cap:
            raise OSError(f"disk budget exceeded: {self.used + nbytes} > {self.cap} bytes")
        self.used += nbytes

    def write(self, path: Path, data: bytes) -> None:
        """Atomic write that is refused (before writing) if it would pass the cap."""
        self.charge(len(data))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)


def _gz_csv_bytes(header: list[str], rows: Iterable[list]) -> bytes:
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return gzip.compress(buf.getvalue().encode(), compresslevel=6, mtime=0)


# ---------------------------------------------------------------------------------------------
# Market universe (Gamma) and stratified sample
# ---------------------------------------------------------------------------------------------

FRAME_COLUMNS = [
    "market_id", "condition_id", "token0", "token1", "event_id", "fee_category", "status",
    "liquidity", "volume", "created_at", "start_at", "end_at", "closed_time", "closed",
    "uma_status", "outcome_prices", "neg_risk", "start_epoch", "end_epoch", "close_epoch",
]


def _epoch(v: Any) -> float:
    if v in (None, ""):
        return float("nan")
    try:
        ts = pd.Timestamp(str(v).replace(" ", "T") if "T" not in str(v) else str(v))
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        return float(ts.timestamp())
    except (ValueError, TypeError):
        return float("nan")


def frame_row(m: dict) -> dict | None:
    """Slim record of a Gamma market, or None unless it is a binary market with token ids."""
    try:
        toks = json.loads(m["clobTokenIds"]) if isinstance(m.get("clobTokenIds"), str) else None
    except ValueError:
        toks = None
    if m.get("id") is None or not m.get("conditionId") or not toks or len(toks) != 2:
        return None
    ev = m.get("events") if isinstance(m.get("events"), list) else []
    ev0 = ev[0] if ev and isinstance(ev[0], dict) else {}

    def num(k: str) -> float:
        try:
            return float(m.get(k))
        except (TypeError, ValueError):
            return float("nan")

    closed = bool(m.get("closed"))
    start = m.get("startDate") or m.get("createdAt")
    r = {
        "market_id": str(m["id"]), "condition_id": m["conditionId"], "token0": str(toks[0]),
        "token1": str(toks[1]), "event_id": str(ev0["id"]) if ev0.get("id") is not None else "",
        "fee_category": fee_category(m.get("feeType")), "status": "closed" if closed else "active",
        "liquidity": num("liquidityNum"), "volume": num("volumeNum"),
        "created_at": m.get("createdAt") or "", "start_at": start or "",
        "end_at": m.get("endDate") or "", "closed_time": m.get("closedTime") or "",
        "closed": int(closed), "uma_status": m.get("umaResolutionStatus") or "",
        "outcome_prices": m.get("outcomePrices") or "",
        "neg_risk": int(bool(m.get("negRisk"))),
        "start_epoch": _epoch(start), "end_epoch": _epoch(m.get("endDate")),
        "close_epoch": _epoch(m.get("closedTime")),
    }
    return r


def _paged(lim: Limiter, params: dict, max_rows: int = GAMMA_OFFSET_CAP) -> tuple[list[dict], bool]:
    """Walk one /markets query by offset; returns (rows, capped)."""
    out: list[dict] = []
    off = 0
    while True:
        status, data = lim.get(GAMMA_MARKETS, {**params, "limit": GAMMA_PAGE, "offset": off})
        if status != 200 or not isinstance(data, list):
            return out, off >= max_rows
        out.extend(data)
        if len(data) < GAMMA_PAGE:
            return out, False
        off += GAMMA_PAGE
        if off >= max_rows:
            return out, True


FRAME_VERSION = "frame-v2-random-windows"


class FrameInterrupted(RuntimeError):
    """Frame fetch stopped between days (collection window); partial days are kept on disk."""


def fetch_frame(
    lim: Limiter, now: float, lookback_days: int = 270, min_volume: float = 0.0,
    include_active: bool = True, windows_per_day: int = 6, window_minutes: int = 15,
    pages_per_window: int = 3, seed: str = "arepo-h1", partial_path: Path | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[list[dict], dict]:
    """Market universe, sampled by time window (the full closed universe is far too large: one day
    can hold more than 20000 closed markets, mostly short crypto markets, and Gamma offset depth is
    capped near 2100).

    For every day of ``lookback_days`` a seeded set of ``windows_per_day`` random
    ``window_minutes`` windows is drawn independently of any market attribute. Closed markets are
    selected by ``end_date`` in the window, active markets by ``startDate`` in the window; each
    window is read in id order up to ``pages_per_window`` pages. A window that still has rows after
    that is "capped" and only its lowest ids enter the frame (documented bias). Nothing is
    filtered on final volume unless ``min_volume > 0`` (a separate, labelled sub-frame).
    Binary markets only. Returns (rows, report) with the exclusions spelled out.
    """
    import random

    rows: dict[str, dict] = {}
    rep: dict = {
        "frame_version": FRAME_VERSION, "lookback_days": lookback_days,
        "windows_per_day": windows_per_day, "window_minutes": window_minutes,
        "pages_per_window": pages_per_window, "windows": {"closed": 0, "active": 0},
        "windows_capped": {"closed": 0, "active": 0}, "raw": 0, "non_binary_or_invalid": 0,
        "volume_floor": min_volume if min_volume > 0 else None,
        "volume_floor_label": "SEPARATE SUB-FRAME" if min_volume > 0 else None,
        "excludes": [
            "non-binary markets and markets without two CLOB token ids",
            f"closed markets whose endDate is outside the last {lookback_days} days",
            f"active markets whose startDate is outside the last {lookback_days} days",
            "all markets outside the randomly drawn windows (about "
            f"{windows_per_day * window_minutes / 1440:.1%} of each day's time axis)",
            f"markets beyond page {pages_per_window} of a capped window (highest ids)",
        ] + ([f"markets with final volume < {min_volume}"] if min_volume > 0 else []),
    }

    def take(batch: list[dict]) -> None:
        for m in batch:
            rep["raw"] += 1
            r = frame_row(m)
            if r is None:
                rep["non_binary_or_invalid"] += 1
            else:
                rows[r["market_id"]] = r

    day0 = datetime.fromtimestamp(now, UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    slots = 1440 // window_minutes
    done_days: set[str] = set()
    if partial_path is not None and Path(partial_path).exists():  # resume: whole days only
        for line in Path(partial_path).read_text().splitlines():
            rec = json.loads(line)
            done_days.add(rec["day"])
            for r in rec["rows"]:
                rows[r["market_id"]] = r
            for key in ("closed", "active"):
                rep["windows"][key] += rec["windows"][key]
                rep["windows_capped"][key] += rec["capped"][key]
            rep["raw"] += rec["raw"]
            rep["non_binary_or_invalid"] += rec["invalid"]
    for d in range(lookback_days, -1, -1):
        day = day0 - timedelta(days=d)
        if f"{day:%Y-%m-%d}" in done_days:
            continue
        if should_stop is not None and should_stop():
            raise FrameInterrupted("collection window")
        before = (dict(rep["windows"]), dict(rep["windows_capped"]), rep["raw"],
                  rep["non_binary_or_invalid"], set(rows))
        rng = random.Random(f"{seed}|{day:%Y-%m-%d}")
        picks = sorted(rng.sample(range(slots), min(windows_per_day, slots)))
        for kind in (("closed", "active") if include_active else ("closed",)):
            for k in picks:
                a = day + timedelta(minutes=k * window_minutes)
                b = a + timedelta(minutes=window_minutes)
                if b.timestamp() > now:
                    continue
                f = "%Y-%m-%dT%H:%M:%SZ"
                p: dict = {"order": "id", "ascending": "true"}
                if kind == "closed":
                    p.update(closed="true", end_date_min=a.strftime(f), end_date_max=b.strftime(f))
                else:
                    p.update(closed="false", start_date_min=a.strftime(f),
                             start_date_max=b.strftime(f))
                if min_volume > 0:
                    p["volume_num_min"] = min_volume
                batch, capped = _paged(lim, p, max_rows=pages_per_window * GAMMA_PAGE)
                rep["windows"][kind] += 1
                rep["windows_capped"][kind] += int(capped)
                take(batch)
        if partial_path is not None:
            new = [r for k, r in rows.items() if k not in before[4]]
            rec = {"day": f"{day:%Y-%m-%d}", "rows": new,
                   "windows": {k: rep["windows"][k] - before[0][k] for k in before[0]},
                   "capped": {k: rep["windows_capped"][k] - before[1][k] for k in before[1]},
                   "raw": rep["raw"] - before[2],
                   "invalid": rep["non_binary_or_invalid"] - before[3]}
            with Path(partial_path).open("a") as fh:
                fh.write(json.dumps(rec, default=float) + "\n")
    return list(rows.values()), rep


def liquidity_band(volume: float) -> str:
    v = 0.0 if (volume is None or math.isnan(volume)) else volume
    return "vol_lt_1e4" if v < 1e4 else "vol_1e4_1e5" if v < 1e5 else "vol_ge_1e5"


def lifetime_band(start_epoch: float, end_epoch: float) -> str:
    if math.isnan(start_epoch) or math.isnan(end_epoch) or end_epoch <= start_epoch:
        return "life_unknown"
    d = (end_epoch - start_epoch) / 86400
    return "life_lt_7d" if d < 7 else "life_7_60d" if d < 60 else "life_ge_60d"


def stratum(r: dict, by_category: bool = True) -> str:
    """status x fee_category x creation month. All known when the market is created (status is
    the closed/active design mix, not a creation attribute); no volume or liquidity."""
    cat = r["fee_category"] if by_category else "all"
    return "|".join([r["status"], str(cat), str(r["created_at"])[:7] or "unknown"])


def _rank(seed: str, market_id: str) -> str:
    return hashlib.sha256(f"{seed}|{market_id}".encode()).hexdigest()


def allocate(sizes: dict[str, int], n_total: int) -> dict[str, int]:
    """Square-root allocation (flattens dominant strata, keeps small ones present), largest
    remainder, never above a stratum's size."""
    n_total = min(n_total, sum(sizes.values()))
    alloc = dict.fromkeys(sizes, 0)
    while sum(alloc.values()) < n_total:
        room = {k: v - alloc[k] for k, v in sizes.items() if alloc[k] < v}
        if not room:
            break
        need = n_total - sum(alloc.values())
        w = {k: math.sqrt(sizes[k]) for k in room}
        tot = sum(w.values())
        share = {k: min(room[k], need * w[k] / tot) for k in room}
        add = {k: int(math.floor(v)) for k, v in share.items()}
        rem = need - sum(add.values())
        if rem and sum(add.values()) == 0:
            order = sorted(room, key=lambda k: (-(share[k] - add[k]), k))
            for k in order[:rem]:
                add[k] += 1
        elif rem:
            order = sorted(room, key=lambda k: (-(share[k] - add[k]), k))
            for k in order[: min(rem, len(order))]:
                if add[k] < room[k]:
                    add[k] += 1
        for k, v in add.items():
            alloc[k] += v
    return alloc


def draw_sample(frame: list[dict], n_total: int, seed: str, by_category: bool = True,
                categories: Iterable[str] | None = None,
                category_mode: str = "all") -> tuple[list[dict], dict]:
    """Seeded stratified sample. ``category_mode``: all | include | exclude over ``categories``
    (fee_category values). Within a stratum, markets are ordered by sha256(seed|market_id)."""
    cats = set(categories or ())
    if category_mode not in ("all", "include", "exclude"):
        raise ValueError("category_mode must be all|include|exclude")
    if category_mode != "all" and not cats:
        raise ValueError("category list required for include/exclude")
    pool = [r for r in frame
            if category_mode == "all"
            or (category_mode == "include") == (r["fee_category"] in cats)]
    strata: dict[str, list[dict]] = {}
    for r in pool:
        strata.setdefault(stratum(r, by_category), []).append(r)
    sizes = {k: len(v) for k, v in strata.items()}
    alloc = allocate(sizes, n_total)
    chosen: list[dict] = []
    for k in sorted(strata):
        pick = sorted(strata[k], key=lambda r: _rank(seed, r["market_id"]))[: alloc[k]]
        chosen.extend({**r, "stratum": k} for r in pick)
    return chosen, {"pool": len(pool), "strata": sizes, "allocation": alloc,
                    "n": len(chosen), "seed": seed, "category_mode": category_mode,
                    "categories": sorted(cats)}


# ---------------------------------------------------------------------------------------------
# Per-market fetch (prices, trades)
# ---------------------------------------------------------------------------------------------


def price_window(r: dict, now: float, max_days: int) -> tuple[int, int] | None:
    """[start, end] epoch seconds to fetch. End = close (closed) or now, plus a day of slack."""
    start = r["start_epoch"]
    if math.isnan(start):
        return None
    if r["closed"]:
        cand = [x for x in (r["close_epoch"], r["end_epoch"]) if not math.isnan(x)]
        end = min(cand) if cand else now
        end = min(end + 86400, now)
    else:
        end = now
    start = max(start, end - max_days * 86400)
    if end <= start:
        return None
    return int(start), int(end)


def fetch_prices(
    lim: Limiter, token: str, start: int, end: int
) -> tuple[list[tuple[int, float]], int]:
    """Series in <=14 day windows at 10-minute fidelity; (sorted unique points, requests)."""
    pts: dict[int, float] = {}
    n = 0
    a = start
    step = WINDOW_DAYS * 86400
    while a < end:
        b = min(a + step, end)
        status, data = lim.get(CLOB_PRICES, {"market": token, "startTs": a, "endTs": b,
                                             "fidelity": FIDELITY_MIN})
        n += 1
        if status == 200 and isinstance(data, dict):
            for h in data.get("history") or []:
                pts[int(h["t"])] = float(h["p"])
        a = b
    return sorted(pts.items()), n


TRADE_COLUMNS = ["ts", "side", "size", "price", "outcome_index", "wallet_hash", "trade_key"]


def trade_key(t: dict) -> str:
    s = f"{t.get('transactionHash')}|{t.get('asset')}|{t.get('side')}|{t.get('size')}|"
    s += f"{t.get('price')}|{t.get('timestamp')}|{t.get('proxyWallet')}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def fetch_trades(lim: Limiter, condition_id: str, key: bytes, max_trades: int
                 ) -> tuple[list[list], dict]:
    """Newest-first pages up to ``max_trades`` (and the API offset cap). Wallets become keyed
    hashes immediately; no raw address, name or pseudonym is kept. Returns rows + stats."""
    rows: dict[str, list] = {}
    off, pages, truncated = 0, 0, False
    cap = min(max_trades, TRADE_OFFSET_CAP + TRADE_PAGE)
    while off < cap:
        status, data = lim.get(DATA_TRADES, {"market": condition_id, "limit": TRADE_PAGE,
                                             "offset": off})
        pages += 1
        if status != 200 or not isinstance(data, list):
            truncated = status != 200 or truncated
            break
        for t in data:
            try:
                rows[trade_key(t)] = [
                    int(t["timestamp"]), str(t["side"]), float(t["size"]), float(t["price"]),
                    int(t["outcomeIndex"]), wallet_hash(key, str(t.get("proxyWallet", ""))),
                    trade_key(t),
                ]
            except (KeyError, TypeError, ValueError):
                continue
        if len(data) < TRADE_PAGE:
            break
        off += TRADE_PAGE
    else:
        truncated = True  # stopped by our own / the API cap with pages still full
    out = sorted(rows.values(), key=lambda x: (x[0], x[6]))
    return out, {"pages": pages, "n": len(out), "truncated": truncated,
                 "oldest_ts": out[0][0] if out else None}


# ---------------------------------------------------------------------------------------------
# Run (resumable)
# ---------------------------------------------------------------------------------------------


def _git_commit() -> str:
    import subprocess

    try:
        o = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           timeout=10, cwd=Path(__file__).resolve().parent)
        return o.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _read_progress(path: Path) -> dict[str, dict]:
    done: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["market_id"]] = rec
    return done


def run(
    root: Path, run_id: str, transport: Transport, *, n_markets: int = 500, seed: str = "arepo-h1",
    lookback_days: int = 270, min_volume: float = 0.0, max_days: int = 120,
    max_trades: int = 5000, category_mode: str = "all", categories: Iterable[str] = (),
    key: bytes | None = None, rps: float = MAX_RPS, disk_cap: int = DISK_CAP_BYTES,
    now: float | None = None, sleep: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] | None = None,
    live_check: Callable[[], bool] | None = live_pass_running,
) -> dict:
    """Fetch universe, draw the seeded sample, fetch prices and trades per market. Resumable:
    re-running with the same ``run_id`` reuses ``sample.csv.gz`` and skips finished markets."""
    root = Path(root)
    if "snapshots" in root.parts or "snapshots" in run_id:
        raise ValueError("historical data must never be written under snapshots/")
    rdir = root / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    budget = DiskBudget(root, disk_cap)
    lim = Limiter(transport, rps=rps, sleep=sleep, live_check=live_check)
    key = key if key is not None else load_or_create_key()
    now = time.time() if now is None else now
    t_start = time.time()
    sample_path = rdir / "sample.csv.gz"
    manifest_path = rdir / "manifest.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    if sample_path.exists():
        sample = pd.read_csv(sample_path, dtype={"market_id": str, "token0": str, "token1": str,
                                                 "event_id": str}, keep_default_na=False
                             ).to_dict("records")
        for r in sample:
            for k in ("liquidity", "volume", "start_epoch", "end_epoch", "close_epoch"):
                r[k] = float("nan") if r[k] == "" else float(r[k])
        frame_rep, samp_rep = prior.get("frame_report", {}), prior.get("sample_report", {})
    else:
        frame_path = rdir / "frame.csv.gz"
        if frame_path.exists():
            fr = pd.read_csv(frame_path, dtype={"market_id": str, "token0": str, "token1": str,
                                                "event_id": str}, keep_default_na=False)
            frame = fr.to_dict("records")
            for r in frame:
                for k in ("liquidity", "volume", "start_epoch", "end_epoch", "close_epoch"):
                    r[k] = float("nan") if r[k] == "" else float(r[k])
            frame_rep = prior.get("frame_report", {})
        else:
            try:
                frame, frame_rep = fetch_frame(
                    lim, now, lookback_days, min_volume, seed=seed,
                    partial_path=rdir / "frame_partial.jsonl", should_stop=should_stop)
            except FrameInterrupted:
                return {"stopped": "frame fetch paused (collection window); resumable",
                        "counts": {"markets_done": 0}}
            budget.write(frame_path, _gz_csv_bytes(
                FRAME_COLUMNS, ([r[c] for c in FRAME_COLUMNS] for r in frame)))
        sample, samp_rep = draw_sample(frame, n_markets, seed, True, categories, category_mode)
        frame_rep["frame_size"] = len(frame)
        header = [*FRAME_COLUMNS, "stratum"]
        budget.write(sample_path, _gz_csv_bytes(
            header, ([r[c] for c in header] for r in sample)))

    progress_path = rdir / "progress.jsonl"
    done = _read_progress(progress_path)
    stats = {"markets_done": 0, "markets_failed": 0, "price_points": 0, "trades": 0,
             "trades_truncated_markets": 0}
    for rec in done.values():
        if rec["status"] == "done":
            stats["markets_done"] += 1
            stats["price_points"] += rec["price_points"]
            stats["trades"] += rec["trades"]
            stats["trades_truncated_markets"] += int(rec["trades_truncated"])
    stopped = None
    for r in sample:
        mid = r["market_id"]
        if should_stop is not None and should_stop():
            stopped = "should_stop (collection window)"
            break
        if mid in done and done[mid]["status"] == "done":
            continue
        try:
            win = price_window(r, now, max_days)
            pts, np_req = fetch_prices(lim, r["token0"], *win) if win else ([], 0)
            trades, tst = fetch_trades(lim, r["condition_id"], key, max_trades)
            budget.write(rdir / "prices" / f"{mid}.csv.gz",
                         _gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
            budget.write(rdir / "trades" / f"{mid}.csv.gz", _gz_csv_bytes(TRADE_COLUMNS, trades))
            rec = {"market_id": mid, "status": "done", "price_points": len(pts),
                   "price_requests": np_req, "window": list(win) if win else None,
                   "trades": tst["n"], "trades_truncated": tst["truncated"],
                   "trades_oldest_ts": tst["oldest_ts"], "fetched_utc": utc_iso()}
            stats["markets_done"] += 1
            stats["price_points"] += len(pts)
            stats["trades"] += tst["n"]
            stats["trades_truncated_markets"] += int(tst["truncated"])
        except OSError as exc:  # disk cap: stop cleanly, resumable
            stopped = f"disk_budget: {exc}"
            break
        except RuntimeError as exc:  # persistent API failure for this market
            rec = {"market_id": mid, "status": "failed", "error": str(exc)[:200]}
            stats["markets_failed"] += 1
        with progress_path.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")

    manifest = {
        "provenance": PROVENANCE,
        "evidence_role": EVIDENCE_ROLE, "version": HISTORY_VERSION, "run_id": run_id,
        "purpose": "exploratory ML development only; never prospective confirmation",
        "git_commit": _git_commit(),
        "endpoints": {"gamma_markets": GAMMA_MARKETS, "prices_history": CLOB_PRICES,
                      "trades": DATA_TRADES},
        "params": {"fidelity_min": FIDELITY_MIN, "window_days": WINDOW_DAYS,
                   "lookback_days": lookback_days, "min_volume": min_volume,
                   "max_days": max_days, "max_trades": max_trades, "seed": seed,
                   "n_markets": n_markets, "category_mode": category_mode,
                   "categories": sorted(categories), "max_rps": rps},
        "started_utc": prior.get("started_utc", utc_iso(t_start)), "updated_utc": utc_iso(),
        "request_clock_now": utc_iso(now),
        "price_semantics": "unverified (last-trade vs mid not stated by API)",
        "timestamps": "venue-stamped unix seconds; no receipt time",
        "wallet_hash": {"method": "wallet_sidecar.hash_wallet (HMAC-SHA256, lowercase)",
                        "key_id": key_id(key), "raw_addresses_stored": False},
        "stratification": {
            "attributes": ["status", "fee_category", "created_month"],
            "known_at_creation": ["fee_category", "created_month"],
            "design_mix": ["status (closed vs active)"],
            "end_of_life_attributes_used": [],
            "frame_exclusions": frame_rep.get("excludes"),
            "survivorship_note": "no volume/liquidity/outcome attribute enters the frame or the "
            "stratification unless frame_report.volume_floor is set (then it is a separate "
            "labelled sub-frame). Closed markets are those that closed inside the lookback; "
            "active markets are those still open at the request time, so older still-open "
            "markets and markets that lived entirely outside the lookback are absent.",
            "frame_min_volume": min_volume},
        "evidence_notes": {
            "origin_features": "price points with stamp + POINT_LAG_S < t, trades with ts < t",
            "point_lag_s": POINT_LAG_S,
            "membership": "createdAt <= t < closedTime (active: no upper bound)",
            "static_gamma_metadata_as_features": False,
            "price_series_nature": "p rarely equals any trade price (mean abs diff ~0.01): "
            "mid-like/derived, interval stamp convention not verifiable -> conservative lag"},
        "frame_report": frame_rep, "sample_report": samp_rep,
        "requests": {"total_this_session": lim.requests, "retries": lim.retries,
                     "http_429": lim.throttled, "yielded_to_live_s": lim.yielded_s},
        "counts": stats, "stopped": stopped,
        "disk_bytes": budget.scan(), "disk_cap_bytes": disk_cap,
        "elapsed_s_this_session": round(time.time() - t_start, 1),
        "probe_findings": PROBE_FINDINGS,
    }
    budget.cap += 10**7  # manifest bookkeeping must still be writable at the cap
    budget.write(manifest_path, json.dumps(manifest, indent=1, sort_keys=True,
                                           default=float).encode())
    return manifest


# ---------------------------------------------------------------------------------------------
# Panel builder
# ---------------------------------------------------------------------------------------------

_TF_WINDOWS = ((2, "2h"), (24, "24h"))
TF_NAMES = (
    *(f"ml_tf_{k}_{w}" for w in ("2h", "24h")
      for k in ("n", "signed_vol", "buy_share", "log_notional")),
    "ml_tf_last_age_h", "ml_tf_ltp_minus_mid", "ml_tf_burst_2h", "ml_tf_large_2h",
)
WLT_NAMES = (
    "ml_tf_n_wallets_2h", "ml_tf_n_wallets_24h", "ml_wlt_hhi_24h", "ml_wlt_top1_24h",
    "ml_wlt_new_n_2h", "ml_wlt_new_n_24h", "ml_wlt_new_share_24h",
)
HIST_STEPS = 6  # prior 2h grid steps for ml_own_vol
FIRST_SEEN_BURN_IN_S = 14 * 86400  # first-seen index is censored at the sample start


def _asof(ts: np.ndarray, vals: np.ndarray, t: np.ndarray, max_age: float
          ) -> tuple[np.ndarray, np.ndarray]:
    """Last observation usable strictly before each ``t``: stamp + ``POINT_LAG_S`` < t. The API
    does not say whether a prices-history stamp marks the start or the end of its 10-minute
    interval (p is not the last trade price either), so the point is only treated as known one
    fidelity step after its stamp. NaN when older than ``max_age`` or before the first point."""
    idx = np.searchsorted(ts + POINT_LAG_S, t, side="left") - 1
    ok = idx >= 0
    safe = np.where(ok, idx, 0)
    age = np.where(ok, t - ts[safe], np.inf)
    good = ok & (age <= max_age)
    return np.where(good, vals[safe], np.nan), np.where(good, age, np.nan)


def load_prices(path: Path) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    return df["t"].to_numpy(float), df["p"].to_numpy(float)


def load_trades(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"wallet_hash": str, "trade_key": str})


class FirstSeen:
    """Causal first-seen index of hashed wallets inside the history data: wallet -> earliest trade
    timestamp over every fetched market. At origin ``t`` only wallets whose first trade is before
    ``t`` can appear in a window, so the index never carries future information; it is left-
    censored at the start of the sample and by per-market trade truncation, hence the burn-in."""

    def __init__(self, keys: np.ndarray, vals: np.ndarray, g0: float) -> None:
        self.keys, self.vals, self.g0 = keys, vals, g0

    @staticmethod
    def key(h: str) -> int:
        return int(h[:15], 16)

    @classmethod
    def build(cls, files: Iterable[Path]) -> FirstSeen:
        acc = None
        buf: list[pd.Series] = []
        for f in files:
            tr = pd.read_csv(f, usecols=["ts", "wallet_hash"], dtype={"wallet_hash": str})
            if not len(tr):
                continue
            k = tr["wallet_hash"].str[:15].map(lambda x: int(x, 16))
            buf.append(tr["ts"].groupby(k).min())
            if len(buf) >= 200:
                acc = pd.concat([acc, *buf]) if acc is not None else pd.concat(buf)
                acc = acc.groupby(level=0).min()
                buf = []
        if buf:
            acc = pd.concat([acc, *buf]) if acc is not None else pd.concat(buf)
            acc = acc.groupby(level=0).min()
        if acc is None:
            return cls(np.array([], dtype=np.int64), np.array([]), float("nan"))
        acc = acc.sort_index()
        return cls(acc.index.to_numpy(np.int64), acc.to_numpy(float), float(acc.min()))

    @classmethod
    def from_trades(cls, tr: pd.DataFrame) -> FirstSeen:
        k = tr["wallet_hash"].str[:15].map(lambda x: int(x, 16))
        acc = tr["ts"].groupby(k).min().sort_index()
        return cls(acc.index.to_numpy(np.int64), acc.to_numpy(float), float(acc.min()))

    def lookup(self, hashes: np.ndarray) -> np.ndarray:
        ks = np.array([self.key(h) for h in hashes], dtype=np.int64)
        idx = np.searchsorted(self.keys, ks)
        ok = (idx < len(self.keys)) & (self.keys[np.minimum(idx, len(self.keys) - 1)] == ks)
        return np.where(ok, self.vals[np.minimum(idx, len(self.vals) - 1)], np.nan)


def _trade_flow(tr: pd.DataFrame, t: np.ndarray, mid: np.ndarray, covered_from: float,
                first_seen: FirstSeen | None = None) -> dict[str, np.ndarray]:
    """Flow and wallet features at grid times ``t`` from trades with ts strictly < t (token-0
    terms: BUY outcome 0 / SELL outcome 1 count as buying the token). A window not fully inside
    the fetched trade history (``covered_from``) is NaN, never 0. Wallet metrics use hashed ids
    only; "new" wallets are those whose first trade in the sample falls inside the window."""
    n = len(t)
    names = (*TF_NAMES, *WLT_NAMES)
    out = {k: np.full(n, np.nan) for k in names}
    if tr is None:
        return out
    ts = tr["ts"].to_numpy(float)
    oi = tr["outcome_index"].to_numpy()
    px = np.where(oi == 0, tr["price"].to_numpy(float), 1 - tr["price"].to_numpy(float))
    sgn = np.where((tr["side"].to_numpy() == "BUY") == (oi == 0), 1, -1)
    sz = tr["size"].to_numpy(float)
    codes, uniq = pd.factorize(tr["wallet_hash"].to_numpy())
    fs = first_seen.lookup(uniq)[codes] if first_seen is not None and len(uniq) else (
        np.full(len(ts), np.nan))
    order = np.argsort(ts, kind="stable")
    ts, px, sgn, sz = ts[order], px[order], sgn[order], sz[order]
    codes, fs = codes[order], fs[order]
    hi = np.searchsorted(ts, t, side="left")  # first index with ts >= t -> strictly before t
    cum_sz = np.concatenate([[0.0], np.cumsum(sz)])
    cum_sg = np.concatenate([[0.0], np.cumsum(sgn * sz)])
    cum_buy = np.concatenate([[0.0], np.cumsum(np.where(sgn > 0, sz, 0.0))])
    cum_notional = np.concatenate([[0.0], np.cumsum(sz * px)])
    lo_w, full_w = {}, {}
    for hrs, tag in _TF_WINDOWS:
        lo = np.searchsorted(ts, t - hrs * 3600, side="left")
        full = (t - hrs * 3600) >= covered_from
        lo_w[tag], full_w[tag] = lo, full
        cnt = (hi - lo).astype(float)
        vol = cum_sz[hi] - cum_sz[lo]
        with np.errstate(divide="ignore", invalid="ignore"):
            share = np.where(vol > 0, (cum_buy[hi] - cum_buy[lo]) / vol, np.nan)
        for name, v in (("n", cnt), ("signed_vol", cum_sg[hi] - cum_sg[lo]), ("buy_share", share),
                        ("log_notional", np.log1p(cum_notional[hi] - cum_notional[lo]))):
            out[f"ml_tf_{name}_{tag}"] = np.where(full, v, np.nan)
    # burst: 2h count against the trailing 24h average per 2h; large: biggest 2h trade against the
    # mean trade size of the trailing 24h (book depth is unavailable historically)
    n2, n24 = out["ml_tf_n_2h"], out["ml_tf_n_24h"]
    with np.errstate(divide="ignore", invalid="ignore"):
        out["ml_tf_burst_2h"] = np.where(n24 > 0, n2 / (n24 / 12.0), np.nan)
    both = full_w["2h"] & full_w["24h"]
    max2 = np.full(n, np.nan)
    wal = {tag: np.full(n, np.nan) for tag in ("hhi", "top1", "dist2", "dist24", "new2", "new24",
                                                "newshare24")}
    burn_ok = np.zeros(n, bool)
    if first_seen is not None and not math.isnan(first_seen.g0):
        burn_ok = (t - 24 * 3600) >= first_seen.g0 + FIRST_SEEN_BURN_IN_S
    for i in range(n):
        a24, b = lo_w["24h"][i], hi[i]
        a2 = lo_w["2h"][i]
        if b > a2 and full_w["2h"][i]:
            max2[i] = sz[a2:b].max()
        if full_w["2h"][i]:
            c2 = codes[a2:b]
            wal["dist2"][i] = len(np.unique(c2)) if b > a2 else 0.0
            if burn_ok[i]:
                nw = fs[a2:b] >= t[i] - 2 * 3600
                wal["new2"][i] = len(np.unique(c2[nw])) if b > a2 else 0.0
        if full_w["24h"][i]:
            if b > a24:
                c = codes[a24:b]
                v = np.bincount(c, weights=sz[a24:b])
                v = v[v > 0]
                tot = v.sum()
                wal["dist24"][i] = float(len(v))
                if tot > 0:
                    wal["hhi"][i] = float(((v / tot) ** 2).sum())
                    wal["top1"][i] = float(v.max() / tot)
                if burn_ok[i]:
                    nw = fs[a24:b] >= t[i] - 24 * 3600
                    wal["new24"][i] = float(len(np.unique(c[nw])))
                    wal["newshare24"][i] = wal["new24"][i] / len(v)
            else:
                wal["dist24"][i] = 0.0
                if burn_ok[i]:
                    wal["new24"][i] = 0.0
    mean24 = np.where(n24 > 0, (cum_sz[hi] - cum_sz[lo_w["24h"]]) / np.maximum(n24, 1), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        out["ml_tf_large_2h"] = np.where(both & (mean24 > 0), max2 / mean24, np.nan)
    out["ml_tf_n_wallets_2h"], out["ml_tf_n_wallets_24h"] = wal["dist2"], wal["dist24"]
    out["ml_wlt_hhi_24h"], out["ml_wlt_top1_24h"] = wal["hhi"], wal["top1"]
    out["ml_wlt_new_n_2h"], out["ml_wlt_new_n_24h"] = wal["new2"], wal["new24"]
    out["ml_wlt_new_share_24h"] = wal["newshare24"]
    last = hi - 1
    has = last >= 0
    safe = np.where(has, last, 0)
    out["ml_tf_last_age_h"] = np.where(has, (t - ts[safe]) / 3600.0, np.nan)
    out["ml_tf_ltp_minus_mid"] = np.where(has, px[safe] - mid, np.nan)
    return out


def origin_frame(
    r: dict, ts: np.ndarray, vals: np.ndarray, trades: pd.DataFrame | None,
    trades_truncated: bool, run_id: str, first_seen: FirstSeen | None = None,
) -> pd.DataFrame:
    """Horizon-independent origin rows and features of one market on the fixed 2h UTC grid.
    Empty frame if the market has no eligible origin."""
    if len(ts) < 2:
        return pd.DataFrame()
    first = math.ceil((ts[0] + 24 * 3600) / GRID_S) * GRID_S  # one day of history for lags
    last = ts[-1]
    t = np.arange(first, last + 1, GRID_S, dtype=float)
    # universe membership: the market existed (createdAt <= t) and was still open at t
    created = _epoch(r.get("created_at"))
    created = r["start_epoch"] if math.isnan(created) else created
    close = r["close_epoch"] if r["closed"] else float("inf")
    if r["closed"] and math.isnan(close):
        close = last  # closed without a closedTime: last observed point bounds the open period
    if math.isnan(created):
        return pd.DataFrame()
    t = t[(t >= created) & (t < close)]
    if len(t) == 0:
        return pd.DataFrame()
    mid, age_i = _asof(ts, vals, t, MAX_QUOTE_AGE_S)
    keep = ~np.isnan(mid) & (mid >= MID_RANGE[0]) & (mid <= MID_RANGE[1])
    t, mid, age_i = t[keep], mid[keep], age_i[keep]
    if len(t) == 0:
        return pd.DataFrame()
    lag = {k: _asof(ts, vals, t - s, MAX_QUOTE_AGE_S)[0]
           for k, s in (("1h", 3600), ("1d", 86400), ("1w", 7 * 86400))}
    steps = np.column_stack([mid] + [_asof(ts, vals, t - GRID_S * k, MAX_QUOTE_AGE_S)[0]
                                     for k in range(1, HIST_STEPS + 1)])
    d = np.diff(steps, axis=1)
    okd = ~np.isnan(d)
    cnt = okd.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        vol = np.sqrt((np.where(okd, d, 0.0) ** 2).sum(1) / cnt)
    n = len(t)
    nan = np.full(n, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        logit = np.log(mid / (1 - mid))
    feats: dict[str, np.ndarray] = {
        "ml_logit_mid": logit, "ml_abs_mid_dev": np.abs(mid - 0.5),
        "ml_chg_1h": mid - lag["1h"], "ml_chg_1d": mid - lag["1d"], "ml_chg_1w": mid - lag["1w"],
        "ml_chg_1h_missing": np.isnan(lag["1h"]).astype(float),
        "ml_chg_1d_missing": np.isnan(lag["1d"]).astype(float),
        "ml_chg_1w_missing": np.isnan(lag["1w"]).astype(float),
        "ml_own_dmid_prev": mid - steps[:, 1],
        "ml_own_prev_age_h": np.where(np.isnan(steps[:, 1]), np.nan, GRID_S / 3600.0),
        "ml_own_vol": np.where(cnt >= 2, vol, np.nan),
        "ml_own_n_prior": (~np.isnan(steps[:, 1:])).sum(1).astype(float),
        "ml_market_age_h": np.clip((t - created) / 3600.0, 0, None),  # createdAt timestamp
    }
    covered_from = (float(trades["ts"].min()) if (trades is not None and len(trades)) else np.inf)
    if trades is not None and not trades_truncated:
        covered_from = -np.inf  # complete history: every window is covered
    tf = _trade_flow(trades if trades is not None and len(trades) else None, t, mid, covered_from,
                     first_seen)
    if trades is not None and not len(trades) and not trades_truncated:
        zero = ("ml_tf_n", "ml_tf_signed", "ml_tf_log", "ml_tf_n_wallets")
        for k in tf:  # fully fetched market with no trades: zero flow, not missing
            if k.startswith(zero):
                tf[k] = np.zeros(n)
    feats.update(tf)
    out = pd.DataFrame({
        "market_id": r["market_id"], "event_id": r["event_id"] or "",
        "period": (t // GRID_S).astype(int), "capture_i": run_id, "capture_j": run_id,
        "t_i": t, "t0": t, "mid_i": mid, "fee_category": r["fee_category"],
        "status": r["status"], "stratum": r.get("stratum", ""), "quote_age_s": age_i,
    })
    for name in ml_panel.EXTENDED_NAMES:  # book / liquidity / sweep / sibling: absent, stay NaN
        out[name] = feats.get(name, nan)
    for name in (*TF_NAMES, *WLT_NAMES):
        out[name] = feats[name]
    out["dep_group"] = ("e:" + r["event_id"]) if r["event_id"] else "m:" + r["market_id"]
    out["provenance"] = PROVENANCE
    out["evidence_role"] = EVIDENCE_ROLE
    return out.reset_index(drop=True)


def attach_labels(
    of: pd.DataFrame, ts: np.ndarray, vals: np.ndarray, horizon_h: int,
    delta: float = ml_panel.DELTA_PRIMARY, delta_sens: float = ml_panel.DELTA_SENSITIVITY,
) -> pd.DataFrame:
    """Labels for one horizon: the last series price usable strictly before ``t + H``."""
    t = of["t_i"].to_numpy(float)
    mid = of["mid_i"].to_numpy(float)
    last = ts[-1]
    t_j = t + horizon_h * 3600
    mid_j, age_j = _asof(ts, vals, t_j, MAX_QUOTE_AGE_S)
    mid_j = np.where(t_j <= last + MAX_QUOTE_AGE_S, mid_j, np.nan)  # no extrapolation past data
    dmid = mid_j - mid
    cls = ml_panel.assign_class(dmid, delta)
    lab = pd.DataFrame({
        "t_j": np.where(np.isnan(mid_j), np.nan, t_j), "mid_j": mid_j, "dmid": dmid,
        "horizon_h": np.where(np.isnan(mid_j), np.nan, float(horizon_h)),
        "horizon_target_h": float(horizon_h),
        "y_class": cls, "y_class_sens": ml_panel.assign_class(dmid, delta_sens),
        "y_dmid": dmid, "y_absmove": np.where(np.isnan(cls), np.nan,
                                              (cls != ml_panel.CLASS_FLAT).astype(float)),
        "target_available": ~np.isnan(dmid), "target_quote_age_s": age_j,
    })
    return pd.concat([of.reset_index(drop=True), lab], axis=1)


def market_panel(
    r: dict, ts: np.ndarray, vals: np.ndarray, trades: pd.DataFrame | None,
    trades_truncated: bool, horizon_h: int, run_id: str, delta: float = ml_panel.DELTA_PRIMARY,
    delta_sens: float = ml_panel.DELTA_SENSITIVITY, first_seen: FirstSeen | None = None,
) -> pd.DataFrame:
    """Rows of one market for one horizon (origin features plus labels)."""
    of = origin_frame(r, ts, vals, trades, trades_truncated, run_id, first_seen)
    if not len(of):
        return of
    return attach_labels(of, ts, vals, horizon_h, delta, delta_sens)


def build_panel(run_dir: Path, horizons: Iterable[int] = HORIZONS_H) -> dict:
    """Stream every finished market of ``run_dir`` into ``panel_H<h>h.csv.gz`` (one per horizon).
    One market in memory at a time (plus the wallet first-seen index). Every row carries
    ``provenance=EXPLORATORY_HISTORICAL`` and ``evidence_role=exploratory_historical``."""
    run_dir = Path(run_dir)
    sample = pd.read_csv(run_dir / "sample.csv.gz", dtype={"market_id": str, "token0": str,
                                                          "token1": str, "event_id": str},
                         keep_default_na=False)
    prog = _read_progress(run_dir / "progress.jsonl")
    horizons = tuple(horizons)
    done = [m for m in sample["market_id"] if m in prog and prog[m]["status"] == "done"]
    fsi = FirstSeen.build(run_dir / "trades" / f"{m}.csv.gz" for m in done)
    writers: dict[int, Any] = {}
    files: dict[int, Any] = {}
    counts = {h: {"rows": 0, "target_available": 0, "markets": 0} for h in horizons}
    try:
        for rec in sample.to_dict("records"):
            mid = rec["market_id"]
            if mid not in prog or prog[mid]["status"] != "done":
                continue
            for k in ("liquidity", "volume", "start_epoch", "end_epoch", "close_epoch"):
                rec[k] = float("nan") if rec[k] == "" else float(rec[k])
            ts, vals = load_prices(run_dir / "prices" / f"{mid}.csv.gz")
            tr = load_trades(run_dir / "trades" / f"{mid}.csv.gz")
            of = origin_frame(rec, ts, vals, tr, bool(prog[mid]["trades_truncated"]),
                              run_dir.name, fsi)
            if not len(of):
                continue
            for h in horizons:
                df = attach_labels(of, ts, vals, h)
                if h not in writers:
                    f = gzip.open(run_dir / f"panel_H{h}h.csv.gz", "wt", newline="")
                    files[h] = f
                    writers[h] = csv.writer(f)
                    writers[h].writerow(df.columns)
                writers[h].writerows(df.itertuples(index=False, name=None))
                counts[h]["rows"] += len(df)
                counts[h]["target_available"] += int(df["target_available"].sum())
                counts[h]["markets"] += 1
    finally:
        for f in files.values():
            f.close()
    summary = {"provenance": PROVENANCE, "evidence_role": EVIDENCE_ROLE, "grid_s": GRID_S,
               "horizons_h": list(horizons),
               "counts": {str(h): c for h, c in counts.items()}, "built_utc": utc_iso(),
               "max_quote_age_s": MAX_QUOTE_AGE_S, "mid_range": list(MID_RANGE),
               "point_lag_s": POINT_LAG_S, "book_features": "absent (NaN)",
               "price_semantics": "unverified",
               "wallet_first_seen": {"burn_in_s": FIRST_SEEN_BURN_IN_S,
                                     "g0": None if math.isnan(fsi.g0) else fsi.g0,
                                     "n_wallets": int(len(fsi.keys)),
                                     "note": "left-censored at sample start and by trade "
                                     "truncation; features NaN during burn-in"}}
    (run_dir / "panel_manifest.json").write_text(json.dumps(summary, indent=1))
    return summary


def iter_ids(run_dir: Path) -> Iterator[str]:
    yield from _read_progress(Path(run_dir) / "progress.jsonl")
