# ruff: noqa: E501
"""LT10 collection route 1 (LIVE_TESTS_10.md 8.1, 8.2, D-LT10-1): a QUOTES-ONLY successor of E009's poller. Research only; never trades; keyless
public endpoints only (the same as E009's: Kalshi ``/markets``, Gamma ``/markets/keyset``, CLOB ``POST /books``).

NOT INSTALLED and NOT STARTED by this code commit. The orchestrator starts it at the handover (8.2: after both E009's and E010's analysis commits,
the successor's code freeze check and the engine's second read root), under a new ``supervise.sh`` entry ``xv-quotes``.

What is the same as E009's poller (``cross_venue_live.py`` eac14e68..., vendored unmodified into ``xv_quotes_poller_base.py``): the pair refresh
(``refresh_pairs`` -> ``select_live_pairs`` -> ``cross_venue.match_markets``, the hand verdicts ``cross_venue_live_verified.json`` at sha256
1d6f942a...c54c, ``LIVE_EXTRA_CONFLICT``), the endpoints, ``CYCLE_S`` 120 on the UTC grid, ``MAX_PAIRS`` 200, ``CHUNK`` 100, ``RETIRE_KEEP_S`` 6 h 20 min,
``REFRESH_EVERY_S`` 86,400, the parse rules and the quote line schema (key order included) plus ONE trailing key ``"src": "xv_quotes_v1"``.

What is different: no features, no predictions, no outcomes, no E010 writer; its own directory (``data-dumps/research_lab/xv_quotes/``) and cap
(3.0 GB, ``CapReached`` -> exit 3); and two RECORD lines that E009 never wrote (what is polled is unchanged):

* ``runs.jsonl`` ``{"kind": "cycle", "t": <scheduled poll>, "pairs_loaded_utc": <refreshed_utc of the record in use>, "load": <true on the cycle
  that loaded a new record>, ...}``, appended (fsync) AFTER the cycle's quote lines, so a reader that waits for the cycle-t line (LT10 1.2 window
  rule, re-check fix 1) never reads a partial cycle;
* ``runs.jsonl`` ``{"kind": "refresh_done", "refreshed_utc": <the refresh start>, "end_utc": <after the pair file was written>, ...}`` from the
  refresh process.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import xv_quotes_poller_base as xb

log = logging.getLogger(__name__)

SRC = "xv_quotes_v1"
ROOT = xb.ROOT
RUNS = "runs.jsonl"
TOTAL_CAP_BYTES = int(3.0 * 1024**3)  # 3.0 GB on the successor's own directory (8.1)
RSS_BUDGET_MB = 200
VERIFIED_SHA256 = "1d6f942a27c9ba1ba56b6514ecb0bad79bd06ce0236084683f722d71932ac54c"  # E009's frozen hand verdicts
REFRESH_RETRY_S = 3600  # run_cross_venue_live.py: a failed refresh is retried at most once an hour


class CapReached(RuntimeError):
    """The successor's hard disk cap was reached: the poller stops (exit 3; the supervisor does not restart it)."""


def verified_ok(path: Path = xb.VERIFIED_PATH) -> bool:
    import hashlib

    return Path(path).exists() and hashlib.sha256(Path(path).read_bytes()).hexdigest() == VERIFIED_SHA256


def append_line(path: Path, row: dict) -> None:
    """One JSON line, one write, fsync (record lines; quote lines use the vendored ``append_jsonl``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(xb._clean(row), separators=(",", ":"), allow_nan=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def refresh(k_lim, p_lim, root: Path = ROOT, *, now: float | None = None, clock: Callable[[], float] = time.time,
            verified_path: Path = xb.VERIFIED_PATH) -> dict:
    """The vendored E009 refresh, then a ``refresh_done`` record line with its end time (8.1)."""
    if not verified_ok(verified_path):
        raise RuntimeError("the hand verdicts file differs from E009's frozen cross_venue_live_verified.json (sha256 1d6f942a...): refused")
    s = xb.refresh_pairs(k_lim, p_lim, root, now=now, verified_path=verified_path)
    append_line(Path(root) / RUNS, {"kind": "refresh_done", "refreshed_utc": s["refreshed_utc"], "end_utc": xb.utc_iso(clock()), "n_pairs": s["n_pairs"],
                                    "kalshi": s["kalshi"], "poly": s["poly"], "k_requests": getattr(k_lim, "requests", None),
                                    "p_requests": getattr(p_lim, "requests", None), "src": SRC})
    return s


def refresh_due(now: float, current: Path, child_running: bool, last_try: float) -> bool:
    """``run_cross_venue_live.py``'s age rule, unchanged: a refresh is spawned when no refresh child runs, ``pairs_current.json`` is at least
    ``REFRESH_EVERY_S`` old by modification time and the last attempt is at least an hour old. With E009's last record copied by ``cp -p`` at the
    handover, the first own refresh therefore fires at E009's refresh time of day (8.2, R1 should-fix 7)."""
    age = now - current.stat().st_mtime if current.exists() else float("inf")
    return (not child_running) and age >= xb.REFRESH_EVERY_S and now - last_try >= REFRESH_RETRY_S


@dataclass
class PairState:
    pair: dict
    retired_at: float | None = None


class XVQuotesPoller:
    """One instance = one process. ``k_lim`` / ``p_lim``: ``get(url, params) -> (status, json)`` (``history_backfill.Limiter``), as E009's
    ``Poller``. Its ``load_pairs``, ``active_states``, ``fetch_kalshi``, ``fetch_books`` and the quote-line construction of ``cycle`` are E009's
    (``cross_venue_live.Poller``) without the feature history, the predictions, the outcomes and the extra writers."""

    def __init__(self, k_lim, p_lim, *, root: Path = ROOT, clock: Callable[[], float] = time.time, total_cap_bytes: int = TOTAL_CAP_BYTES) -> None:
        self.k_lim, self.p_lim, self.clock = k_lim, p_lim, clock
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cap = total_cap_bytes
        self.pairs: dict[str, PairState] = {}
        self.pairs_loaded_utc: str | None = None
        self.totals = {"cycles": 0, "quotes": 0}

    # pairs (E009's Poller.load_pairs: retire absent pairs at the load time; re-listed pairs come back)
    def load_pairs(self) -> bool:
        f = self.root / "pairs_current.json"
        if not f.exists():
            return False
        doc = json.loads(f.read_text())
        if doc.get("refreshed_utc") == self.pairs_loaded_utc:
            return False
        now = self.clock()
        new = {p["pid"]: p for p in doc.get("pairs", [])}
        for pid, st in self.pairs.items():
            if pid not in new and st.retired_at is None:
                st.retired_at = now
        for pid, p in new.items():
            if pid in self.pairs:
                self.pairs[pid].pair, self.pairs[pid].retired_at = p, None
            else:
                self.pairs[pid] = PairState(p)
        self.pairs_loaded_utc = doc.get("refreshed_utc")
        return True

    def active_states(self, now: float) -> list[PairState]:
        drop = [pid for pid, s in self.pairs.items() if s.retired_at is not None and now - s.retired_at > xb.RETIRE_KEEP_S]
        for pid in drop:
            del self.pairs[pid]
        return list(self.pairs.values())

    def fetch_kalshi(self, tickers: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(tickers), xb.CHUNK):
            chunk = tickers[i: i + xb.CHUNK]
            st, data = self.k_lim.get(f"{xb.KALSHI}/markets", {"tickers": ",".join(chunk), "limit": 1000})
            recv = self.clock()
            if st != 200 or not isinstance(data, dict):
                continue
            for m in data.get("markets") or []:
                out[m.get("ticker")] = {**xb.parse_kalshi_market(m), "k_recv": recv}
        return out

    def fetch_books(self, tokens: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(tokens), xb.CHUNK):
            chunk = tokens[i: i + xb.CHUNK]
            st, data = self.p_lim.get(f"{xb.CLOB}/books", [{"token_id": t} for t in chunk])
            recv = self.clock()
            if st != 200 or not isinstance(data, list):
                continue
            for b in data:
                out[str(b.get("asset_id"))] = {**xb.parse_book(b), "p_recv": recv}
        return out

    def cycle(self, t_sched: float) -> dict:
        t0 = self.clock()
        if xb.du_bytes(self.root) >= self.cap:
            raise CapReached(f"{self.root} >= {self.cap} bytes")
        loaded = self.load_pairs()
        states = self.active_states(t_sched)
        k = self.fetch_kalshi([s.pair["k_ticker"] for s in states])
        b = self.fetch_books([s.pair["token0"] for s in states])
        quotes = []
        n_valid = 0
        for s in states:
            p = s.pair
            kq = k.get(p["k_ticker"], {})
            bq = b.get(p["token0"], {})
            q = {**{f: xb.NAN for f in ("k_bid", "k_ask", "p_bid", "p_ask")}, **kq, **bq}
            q["k_mid"] = xb.two_sided_mid(q["k_bid"], q["k_ask"])
            q["p_mid"] = xb.two_sided_mid(q["p_bid"], q["p_ask"])
            quotes.append({"t": int(t_sched), "pid": p["pid"], **q, "src": SRC})
            if math.isfinite(q["k_mid"]) and math.isfinite(q["p_mid"]):
                n_valid += 1
        day = datetime.fromtimestamp(t_sched, UTC).strftime("%Y%m%d")
        xb.append_jsonl(self.root / "quotes" / f"{day}.jsonl", quotes)
        self.totals["cycles"] += 1
        self.totals["quotes"] += len(quotes)
        s = {"kind": "cycle", "t": int(t_sched), "pairs_loaded_utc": self.pairs_loaded_utc, "load": bool(loaded), "pairs": len(states),
             "retired_polled": sum(1 for x in states if x.retired_at is not None), "kalshi_ok": len(k), "books_ok": len(b), "both_valid": n_valid,
             "seconds": round(self.clock() - t0, 1), "rss_mb": xb.rss_mb(), "k_requests": getattr(self.k_lim, "requests", None),
             "p_requests": getattr(self.p_lim, "requests", None), "written_utc": xb.utc_iso(self.clock()), "src": SRC}
        append_line(self.root / RUNS, s)  # AFTER the quote lines (the reader's wait condition, LT10 1.2)
        return s


def read_runs(root: Path) -> list[dict]:
    """Complete ``runs.jsonl`` lines (an incomplete trailing line is skipped)."""
    p = Path(root) / RUNS
    if not p.exists():
        return []
    out = []
    with p.open("rb") as fh:
        for raw in fh:
            if not raw.endswith(b"\n"):
                break
            try:
                out.append(json.loads(raw))
            except ValueError:
                continue
    return out
