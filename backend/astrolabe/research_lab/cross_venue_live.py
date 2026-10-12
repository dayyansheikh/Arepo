"""LIVE prospective test of the Kalshi -> Polymarket lead (research lab; read-only, never trades).

Background: ``cross_venue.py`` / ``docs/research_lab/CROSS_VENUE_STUDY.md``
(``exploratory_historical``) found Kalshi's latest 10-minute change predicting Polymarket's next
10-20 minutes. This module tests that prospectively with receipt-timed quotes from both venues
and a FROZEN, hash-pinned model (``model_specs/cross_venue_live_v1.json``, built once by
``freeze_spec`` from the historical series and never refitted).

Pipeline
--------
1. ``refresh_pairs`` (daily, separate process): keyless Kalshi ``/markets?status=open`` and
   Polymarket Gamma ``/events/keyset`` (closed=false), both filtered to currently two-sided
   quotable Yes/No contracts, then the conservative ``cross_venue.match_markets`` matcher unchanged.
   Hand-verified pairs (``model_specs/cross_venue_live_verified.json``) go first, ``different``
   verdicts are excluded, the rest are ranked by the smaller of the two venues' 24h volume (never
   by prices or outcomes). Cap ``MAX_PAIRS``. Refresh traffic yields to the live collector.
2. ``Poller.cycle`` (every ``CYCLE_S`` on the UTC grid): Kalshi ``/markets?tickers=`` (last price
   and touch) and Polymarket CLOB ``POST /books`` (executable touch), each stamped with its receipt
   time, appended to ``quotes/YYYYMMDD.jsonl``. Then the frozen features and predictions for every
   pair with complete features are appended (fsync) to ``predictions.jsonl`` BEFORE any outcome
   quote exists.
3. ``OutcomeWriter`` (reads predictions and quotes, never writes them): Polymarket mid and touch at
   +10/+20/+60 min from the poll at exactly ``t + h`` (else the nearest within ``OUTCOME_TOL_S``)
   and the paper taker P&L (enter at the touch, exit at the touch, ``economics.taker_fee``).
   Written to ``outcomes.jsonl``. ``unavailable`` when no usable quote exists; never filled.
4. ``analyze``: the registered E009 statistics (event-clustered bootstrap), run once at the end.

Evidence role: ``prospective_unregistered`` for every origin before ``REGISTERED_UTC`` (and for
everything while it is ``None``); ``prospective_confirmation`` afterwards. No edge claim.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import math
import os
import subprocess
import time
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import cross_venue as cv
from . import economics as econ
from . import forecast

log = logging.getLogger(__name__)
for _n in ("httpx", "httpcore"):
    logging.getLogger(_n).setLevel(logging.WARNING)

VERSION = "cross-venue-live-v1"
ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "cross_venue_live"
SPEC_DIR = Path(__file__).resolve().parent / "model_specs"
SPEC_PATH = SPEC_DIR / "cross_venue_live_v1.json"
VERIFIED_PATH = SPEC_DIR / "cross_venue_live_verified.json"
# sha256 of SPEC_PATH bytes, pinned when the spec was frozen; load_spec refuses anything else.
SPEC_SHA256 = "e63f20cc095ba88346155cabe0d2e4289981017cc48450ccc575bbc7d0d16e2b"
# Set in the E009 registration commit. Origins before it (the pilot) stay prospective_unregistered.
REGISTERED_UTC: str | None = "2026-10-13T00:00:00Z"  # E009 (EXPERIMENT_LEDGER.md)

KALSHI = cv.KALSHI_API
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

CYCLE_S = 120
MAX_PAIRS = 200
POLY_PAGE = 100  # Gamma markets per keyset page
CHUNK = 100  # tickers / token ids per batch request
LOOKBACK_TOL_S = 240  # a lagged value is the latest poll in [t-L-240, t-L]
OUTCOME_GRID_S = 600  # outcome lines are written for origins with t % 600 == 0 only
OUTCOME_TOL_S = 120  # outcome quote: poll at t+h, else nearest within +-120 s
MAX_RECV_LAG_S = 60  # analysis: receipt > 60 s after the poll time -> late / unavailable
HORIZONS_MIN = (10, 20, 60)
PRIMARY_H = 20
HISTORY_S = 3600 + LOOKBACK_TOL_S + 600
RETIRE_KEEP_S = 3600 + 600  # retired pairs keep being polled so pending outcomes can complete
REFRESH_EVERY_S = 86400
TOTAL_CAP_BYTES = 2 * 1024**3
RSS_BUDGET_MB = 200
MAX_SPREAD = cv.MAX_K_SPREAD  # same two-sided validity rule on both venues
MID_RANGE = cv.MID_RANGE
FEATURES = ("r1", "r6", "lvl", "lvl2", "gap", "dk1", "dk6")
M0_FEATURES = FEATURES[:4]
NAN = float("nan")


class CapReached(RuntimeError):
    """The hard total disk cap was reached: the poller stops."""


# --- small utilities ---------------------------------------------------------------------------


def utc_iso(ts: float | None = None) -> str:
    dt = datetime.now(UTC) if ts is None else datetime.fromtimestamp(ts, UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NAN
    return v if math.isfinite(v) else NAN


def _clean(v: Any) -> Any:
    if isinstance(v, (float, np.floating)):
        return round(float(v), 6) if math.isfinite(v) else None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def append_jsonl(path: Path, rows: Iterable[dict]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.writelines(
            json.dumps(_clean(r), separators=(",", ":"), allow_nan=False) + "\n" for r in rows
        )
        fh.flush()
        os.fsync(fh.fileno())
    return len(rows)


def read_jsonl(path: Path):
    path = Path(path)
    if not path.exists():
        return
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def du_bytes(root: Path) -> int:
    root = Path(root)
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) if root.exists() else 0


def rss_mb() -> float:
    import resource
    import sys

    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(v / (1024**2 if sys.platform == "darwin" else 1024), 1)


def evidence_role(t: float, registered_utc: str | None = REGISTERED_UTC) -> str:
    if registered_utc is None:
        return "prospective_unregistered"
    reg = datetime.fromisoformat(registered_utc.replace("Z", "+00:00")).timestamp()
    return "prospective_confirmation" if t >= reg else "prospective_unregistered"


# --- quotes ------------------------------------------------------------------------------------


def two_sided_mid(bid: float, ask: float) -> float:
    """Mid of a valid two-sided quote (0 < bid < ask < 1, spread <= MAX_SPREAD), else NaN.
    The same rule as ``cross_venue.k_mid_series``, applied to both venues."""
    if not (math.isfinite(bid) and math.isfinite(ask)):
        return NAN
    if bid <= 0 or ask >= 1 or ask <= bid or ask - bid > MAX_SPREAD + 1e-12:
        return NAN
    return (bid + ask) / 2.0


def in_range(x: float) -> bool:
    return math.isfinite(x) and MID_RANGE[0] <= x <= MID_RANGE[1]


def parse_kalshi_market(m: dict) -> dict:
    return {
        "k_bid": _num(m.get("yes_bid_dollars")),
        "k_ask": _num(m.get("yes_ask_dollars")),
        "k_last": _num(m.get("last_price_dollars")),
        "k_bid_sz": _num(m.get("yes_bid_size_fp")),
        "k_ask_sz": _num(m.get("yes_ask_size_fp")),
        "k_status": m.get("status"),
        "k_vol24": _num(m.get("volume_24h_fp")),
    }


def parse_book(b: dict) -> dict:
    """Executable touch of one CLOB book (best bid = highest bid, best ask = lowest ask)."""

    def levels(side):
        out = []
        for lv in b.get(side) or []:
            p, s = _num(lv.get("price")), _num(lv.get("size"))
            if math.isfinite(p) and math.isfinite(s) and s > 0:
                out.append((p, s))
        return out

    bids, asks = levels("bids"), levels("asks")
    bb = max(bids, default=(NAN, NAN))
    ba = min(asks, default=(NAN, NAN))
    return {
        "p_bid": bb[0],
        "p_ask": ba[0],
        "p_bid_sz": bb[1],
        "p_ask_sz": ba[1],
        "p_last": _num(b.get("last_trade_price")),
        "p_book_ts": _num(b.get("timestamp")) / 1000.0,
        "p_tick": _num(b.get("tick_size")),
        "p_min_size": _num(b.get("min_order_size")),
    }


# --- frozen spec -------------------------------------------------------------------------------


def spec_bytes(spec: dict) -> bytes:
    return (json.dumps(spec, indent=1, sort_keys=True) + "\n").encode()


def load_spec(path: Path = SPEC_PATH, sha: str = SPEC_SHA256) -> dict:
    raw = Path(path).read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if sha != got:
        raise RuntimeError(f"frozen spec hash mismatch: pinned {sha[:12]}, file {got[:12]}")
    spec = json.loads(raw)
    spec["_sha256"] = got
    return spec


def predict(coefs: dict, feats: dict, names: Sequence[str]) -> float:
    return coefs["intercept"] + sum(coefs[n] * feats[n] for n in names)


def ols_raw(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Unpenalised OLS with intercept in raw units; ``[intercept, *betas]``."""
    Z = np.column_stack([np.ones(len(X)), X])
    return np.linalg.lstsq(Z, y, rcond=None)[0]


def historical_design(ps: cv.PairSeries, h: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rows ``(t, X[FEATURES], y)`` from one aligned historical pair, the live feature definitions
    on the 10-minute grid (``cross_venue._design`` with ``gapk``), every usable origin."""
    t, X, y, valid = cv._design(ps, h, "gapk")
    # _design columns: r1, r6, lvl, lvl^2, gap, dk1, dk6 (same order as FEATURES)
    return t[valid], X[valid], y[valid]


def freeze_spec(
    pairs: Sequence[cv.PairSeries], provenance: dict, n_boot: int = 2000, seed: int = 20261012
) -> dict:
    """Fit the frozen M0 / M1 coefficients on ALL historical pairs (one fit per horizon), plus the
    descriptive numbers the registration needs (in-sample gain, per-cluster SE at 20 min on
    non-overlapping origins). Called once; the output is hash-pinned and never refitted."""
    steps = {10: 1, 20: 2, 60: 6}
    models: dict[str, Any] = {}
    for hmin, h in steps.items():
        rows = [(ps.cluster, *historical_design(ps, h)) for ps in pairs]
        X = np.vstack([r[2] for r in rows if len(r[2])])
        y = np.concatenate([r[3] for r in rows if len(r[3])])
        b1 = ols_raw(X, y)
        b0 = ols_raw(X[:, :4], y)
        bk = ols_raw(X[:, 5:6], y)  # Kalshi 10-min change alone (descriptive)
        e0 = y - (b0[0] + X[:, :4] @ b0[1:])
        e1 = y - (b1[0] + X @ b1[1:])
        models[str(hmin)] = {
            "m0": {
                "intercept": float(b0[0]),
                **{n: float(v) for n, v in zip(M0_FEATURES, b0[1:], strict=True)},
            },
            "m1": {
                "intercept": float(b1[0]),
                **{n: float(v) for n, v in zip(FEATURES, b1[1:], strict=True)},
            },
            "dk1_only_slope": float(bk[1]),
            "n_obs": int(len(y)),
            "target_sd": float(y.std()),
            "in_sample_rel_mse_gain": float(1 - (e1 @ e1) / (e0 @ e0)),
        }
    # Per-cluster sufficient statistics at the primary horizon on non-overlapping origins.
    h = steps[PRIMARY_H]
    m = models[str(PRIMARY_H)]
    per = []
    for ps in pairs:
        t, X, y = historical_design(ps, h)
        sel = (np.floor(t / cv.GRID_S).astype(np.int64) % h) == 0
        if not sel.any():
            continue
        X, y = X[sel], y[sel]
        f0 = m["m0"]["intercept"] + X[:, :4] @ np.array([m["m0"][n] for n in M0_FEATURES])
        f1 = m["m1"]["intercept"] + X @ np.array([m["m1"][n] for n in FEATURES])
        e0, e1 = y - f0, y - f1
        per.append((ps.cluster, float(e0 @ e0), float(e0 @ e0 - e1 @ e1), float(len(y))))
    clusters = sorted({c for c, *_ in per})
    S = np.zeros((len(clusters), 3))
    idx = {c: i for i, c in enumerate(clusters)}
    for c, a, b, n in per:
        S[idx[c]] += (a, b, n)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        s = S[rng.integers(0, len(S), len(S))].sum(0)
        boots.append(s[1] / s[0])
    hist = {
        "n_clusters": len(clusters),
        "n_origins": int(S[:, 2].sum()),
        "rel_mse_gain": float(S[:, 1].sum() / S[:, 0].sum()),
        "cluster_boot_se": float(np.std(boots)),
        "origins_per_cluster_median": float(np.median(S[:, 2])),
    }
    return {
        "spec_id": "cross_venue_live_v1",
        "version": VERSION,
        "frozen_utc": utc_iso(),
        "features": list(FEATURES),
        "feature_definitions": {
            "r1": "Polymarket mid(t) - mid(t-10m)",
            "r6": "Polymarket mid(t) - mid(t-60m)",
            "lvl": "Polymarket mid(t) - 0.5",
            "lvl2": "lvl^2",
            "gap": "Kalshi mid(t) - Polymarket mid(t)",
            "dk1": "Kalshi mid(t) - Kalshi mid(t-10m)",
            "dk6": "Kalshi mid(t) - Kalshi mid(t-60m)",
            "mid": "two-sided quote (0<bid<ask<1, ask-bid<=0.10), both mids in [0.03, 0.97] at "
            "every endpoint used; lagged value = latest poll in [t-L-240s, t-L]",
            "target": "Polymarket mid(t+h) - mid(t), h in {10, 20, 60} min",
        },
        "models": models,
        "historical_primary_h20_frozen": hist,
        "fit": {
            "method": "unpenalised OLS with intercept, raw units, all usable historical origins "
            "per horizon (no walk-forward; one fit, never refitted)",
            "alignment": "cross_venue.align_pair with pm_lag_s=0 (a Polymarket history point is "
            "usable at its own stamp), the closest analogue of a receipt-timed live "
            "quote; the conservative 600 s alignment is not used for coefficients",
        },
        "provenance": provenance,
        "evidence_role_of_fit_data": cv.EVIDENCE_ROLE,
    }


# --- pair refresh ------------------------------------------------------------------------------


def kalshi_candidate(m: dict) -> dict | None:
    """Minimal record of an open, currently two-sided Kalshi binary market, else None."""
    if m.get("market_type", "binary") != "binary" or m.get("status") not in ("active", "open"):
        return None
    q = parse_kalshi_market(m)
    if math.isnan(two_sided_mid(q["k_bid"], q["k_ask"])):
        return None
    close = m.get("expected_expiration_time") or m.get("close_time")
    return {
        "ticker": m["ticker"],
        "event_ticker": m.get("event_ticker", ""),
        "title": m.get("title") or "",
        "yes_sub": m.get("yes_sub_title") or "",
        "close_time": close,
        "vol24": q["k_vol24"],
    }


YES_NO = ["Yes", "No"]


def poly_candidate(m: dict, event_id: str) -> dict | None:
    """Minimal record of an open, order-book, two-sided Yes/No Polymarket market, else None."""
    try:
        outcomes = json.loads(m.get("outcomes") or "[]")
        toks = json.loads(m.get("clobTokenIds") or "[]")
    except (TypeError, ValueError):
        return None
    if outcomes != ["Yes", "No"] or len(toks) != 2:
        return None
    if (
        m.get("closed")
        or not m.get("active")
        or not m.get("acceptingOrders")
        or not m.get("enableOrderBook")
    ):
        return None
    if math.isnan(two_sided_mid(_num(m.get("bestBid")), _num(m.get("bestAsk")))):
        return None
    return {
        "market_id": str(m.get("id")),
        "event_id": str(event_id),
        # question already joined with groupItemTitle exactly as cross_venue.p_text does
        "question": cv.p_text(
            {"question": m.get("question") or "", "item": m.get("groupItemTitle") or ""}
        ),
        "outcomes": YES_NO,  # one shared list: tens of thousands of candidates, memory bound
        "token0": str(toks[0]),
        "end": m.get("endDate"),
        "vol24": _num(m.get("volume24hr")),
        "fee_type": m.get("feeType"),
        "fees_enabled": m.get("feesEnabled"),
    }


def poly_candidates(event: dict) -> list[dict]:
    """Candidates of one Gamma event payload (nested markets)."""
    out = (poly_candidate(m, str(event.get("id"))) for m in event.get("markets") or [])
    return [c for c in out if c]


class MatchPrefilter:
    """Necessary conditions of ``cross_venue.match_markets`` evaluated against the Polymarket
    candidates: identical number set present, >= MIN_SHARED word tokens in the Polymarket
    vocabulary, a Polymarket end within MAX_DATE_GAP_S. A Kalshi market failing any of them can
    never be a candidate for any Polymarket market, so dropping it early leaves the matcher's
    output unchanged; it only bounds memory."""

    def __init__(self, poly: Sequence[dict]) -> None:
        self.vocab: set[str] = set()
        self.numsets: set[frozenset] = set()
        ends = []
        for m in poly:
            w, n = cv.tokenize(cv.p_text(m))
            self.vocab |= w
            self.numsets.add(n)
            e = cv._p_end(m)
            if math.isfinite(e):
                ends.append(e)
        self.ends = np.sort(np.array(ends, dtype=float))

    def __call__(self, k: dict) -> bool:
        w, n = cv.tokenize(cv.k_text(k))
        if n not in self.numsets or len(w & self.vocab) < cv.MIN_SHARED:
            return False
        e = cv._epoch(k.get("close_time"))
        if not math.isfinite(e) or not len(self.ends):
            return False
        i = int(np.searchsorted(self.ends, e - cv.MAX_DATE_GAP_S))
        return i < len(self.ends) and self.ends[i] <= e + cv.MAX_DATE_GAP_S


def fetch_kalshi_open(
    lim, max_pages: int = 400, keep: Callable[[dict], bool] | None = None
) -> tuple[list[dict], dict]:
    out, cur, pages, seen = [], None, 0, 0
    while pages < max_pages:
        params = {"status": "open", "limit": 1000, "mve_filter": "exclude"}
        if cur:
            params["cursor"] = cur
        st, data = lim.get(f"{KALSHI}/markets", params)
        pages += 1
        if st != 200 or not isinstance(data, dict):
            return out, {"pages": pages, "seen": seen, "complete": False, "status": st}
        ms = data.get("markets") or []
        seen += len(ms)
        out.extend(c for c in map(kalshi_candidate, ms) if c and (keep is None or keep(c)))
        cur = data.get("cursor")
        last = not cur or not ms
        del data, ms
        if pages % 50 == 0:
            log.info("kalshi page %d kept %d rss %.0f MB", pages, len(out), rss_mb())
        if last:
            return out, {"pages": pages, "seen": seen, "complete": True}
    return out, {"pages": pages, "seen": seen, "complete": False, "status": "max_pages"}


def fetch_poly_open(lim, max_pages: int = 6000) -> tuple[list[dict], dict]:
    """Gamma ``/markets/keyset?closed=false`` (flat, 100 markets per page: bounded page size, unlike
    ``/events/keyset`` whose pages can hold events with thousands of markets)."""
    out, cur, pages, seen = [], None, 0, 0
    while pages < max_pages:
        params: dict = {"closed": "false", "limit": POLY_PAGE}
        if cur:
            params["after_cursor"] = cur
        st, data = lim.get(f"{GAMMA}/markets/keyset", params)
        pages += 1
        if st != 200 or not isinstance(data, dict):
            return out, {"pages": pages, "seen": seen, "complete": False, "status": st}
        ms = data.get("markets") or []
        seen += len(ms)
        for m in ms:
            evs = m.get("events") or [{}]
            c = poly_candidate(m, str(evs[0].get("id", "")))
            if c and c["event_id"]:
                out.append(c)
        cur = data.get("next_cursor")
        last = not cur or not ms
        del data, ms
        if pages % 500 == 0:
            log.info("poly page %d kept %d rss %.0f MB", pages, len(out), rss_mb())
        if last:
            return out, {"pages": pages, "seen": seen, "complete": True}
    return out, {"pages": pages, "seen": seen, "complete": False, "status": "max_pages"}


def load_verified(path: Path = VERIFIED_PATH) -> dict[tuple[str, str], dict]:
    if not Path(path).exists():
        return {}
    rows = json.loads(Path(path).read_text()).get("pairs", [])
    return {(r["k_ticker"], str(r["p_market_id"])): r for r in rows}


def fee_rate(fee_type: str | None, fees_enabled: Any) -> tuple[float, str]:
    """Taker rate from ``feesEnabled`` + the docs rate of the ``feeType`` category (the Gamma
    event payload carries no ``feeSchedule``). Unknown -> the highest docs rate (conservative)."""
    cat = str(fee_type or "").removesuffix("_fees") or None
    spec = econ.fee_spec(None, None if fees_enabled is None else int(bool(fees_enabled)), cat)
    if spec.flag == "disabled":
        return 0.0, "disabled"
    if math.isfinite(spec.docs_rate):
        return spec.docs_rate, f"docs:{cat}"
    return econ.MAX_DOCS_RATE, "unknown_max"


# Live-only tightening (never loosening) of the generic matcher, added 2026-10-12 after the first
# live refresh showed contract-changing words the historical conflict list lacks (president vs
# VICE-president, match vs HALFTIME, election vs SECOND ROUND, party vs candidate, ...). It applies
# to pairs without a hand verdict; ``cross_venue.CONFLICT`` itself is unchanged.
LIVE_EXTRA_CONFLICT = frozenset(
    {
        "vice",
        "halftime",
        "leading",
        "second",
        "runoff",
        "round",
        "group",
        "removed",
        "nominee",
        "nomination",
        "justice",
        "republican",
        "democrat",
        "quarter",
        "half",
        "period",
        "set",
        "map",
    }
)


def live_conflict(k: dict, m: dict) -> bool:
    kw, _ = cv.tokenize(cv.k_text(k))
    pw, _ = cv.tokenize(cv.p_text(m))
    return bool((kw ^ pw) & LIVE_EXTRA_CONFLICT)


def select_live_pairs(
    kalshi: list[dict], poly: list[dict], verified: dict, cap: int = MAX_PAIRS
) -> list[dict]:
    kb = {m["ticker"]: m for m in kalshi}
    pb = {m["market_id"]: m for m in poly}
    matches = cv.match_markets(kalshi, poly)
    rows = []
    for p in matches:
        v = verified.get((p.k_ticker, p.p_market_id))
        if v and v.get("verdict") == "different":
            continue
        k, m = kb[p.k_ticker], pb[p.p_market_id]
        if not (v and v.get("verdict") == "same") and live_conflict(k, m):
            continue
        rate, rate_src = fee_rate(m.get("fee_type"), m.get("fees_enabled"))
        rows.append(
            {
                "pid": f"{p.k_ticker}|{p.p_market_id}",
                "k_ticker": p.k_ticker,
                "p_market_id": p.p_market_id,
                "p_event_id": p.p_event_id,
                "k_event": p.k_event,
                "token0": m["token0"],
                "score": round(p.score, 4),
                "gap_days": round(p.gap_days, 3),
                "k_text": cv.k_text(k),
                "p_text": cv.p_text(m),
                "k_close": k["close_time"],
                "p_end": m.get("end"),
                "k_vol24": k["vol24"],
                "p_vol24": m["vol24"],
                "fee_rate": rate,
                "fee_src": rate_src,
                "hand_verified": bool(v and v.get("verdict") == "same"),
            }
        )

    def rank(r):
        vol = min(
            _num(r["k_vol24"]) if math.isfinite(_num(r["k_vol24"])) else 0.0,
            _num(r["p_vol24"]) if math.isfinite(_num(r["p_vol24"])) else 0.0,
        )
        return (not r["hand_verified"], -vol, r["pid"])

    rows.sort(key=rank)
    return rows[:cap]


def refresh_pairs(
    k_lim,
    p_lim,
    root: Path = ROOT,
    *,
    now: float | None = None,
    verified_path: Path = VERIFIED_PATH,
) -> dict:
    """Daily refresh (separate process). Writes ``pairs/pairs_<ts>.json`` and atomically replaces
    ``pairs_current.json``. Nothing is fetched by price history or outcome."""
    now = time.time() if now is None else now
    root = Path(root)
    poly, pst = fetch_poly_open(p_lim)
    kalshi, kst = fetch_kalshi_open(k_lim, keep=MatchPrefilter(poly))
    pairs = select_live_pairs(kalshi, poly, load_verified(verified_path))
    doc = {
        "refreshed_utc": utc_iso(now),
        "version": VERSION,
        "kalshi": kst,
        "poly": pst,
        "kalshi_candidates": len(kalshi),
        "poly_candidates": len(poly),
        "n_pairs": len(pairs),
        "cap": MAX_PAIRS,
        "pairs": pairs,
        "rss_mb": rss_mb(),
    }
    (root / "pairs").mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(now, UTC).strftime("%Y%m%dT%H%M%SZ")
    (root / "pairs" / f"pairs_{stamp}.json").write_text(json.dumps(_clean(doc)))
    tmp = root / "pairs_current.json.tmp"
    tmp.write_text(json.dumps(_clean(doc)))
    tmp.replace(root / "pairs_current.json")
    return {k: v for k, v in doc.items() if k != "pairs"}


# --- features and predictions (pure) -----------------------------------------------------------


def lookup(
    hist: Sequence[tuple[float, float, float]], t: float, lag_s: float
) -> tuple[float, float] | None:
    """Latest history entry ``(ts, k_mid, p_mid)`` with ``t-lag-TOL <= ts <= t-lag``."""
    lo, hi = t - lag_s - LOOKBACK_TOL_S, t - lag_s
    best = None
    for ts, k, p in hist:
        if lo <= ts <= hi and (best is None or ts > best[0]):
            best = (ts, k, p)
    return None if best is None else (best[1], best[2])


def features(
    hist: Sequence[tuple[float, float, float]], t: float, k: float, p: float
) -> dict | None:
    """Frozen live features at origin ``t`` from the current mids and the pair's quote history.
    None unless every endpoint is a valid two-sided mid inside MID_RANGE."""
    if not (in_range(k) and in_range(p)):
        return None
    a, b = lookup(hist, t, 600), lookup(hist, t, 3600)
    if a is None or b is None or not all(in_range(x) for x in (*a, *b)):
        return None
    lvl = p - 0.5
    return {
        "r1": p - a[1],
        "r6": p - b[1],
        "lvl": lvl,
        "lvl2": lvl * lvl,
        "gap": k - p,
        "dk1": k - a[0],
        "dk6": k - b[0],
    }


def round_trip_cost(bid: float, ask: float, rate: float) -> float:
    """Per-share cost of crossing the spread in and out at the current touch, with taker fees."""
    if not (math.isfinite(bid) and math.isfinite(ask)):
        return NAN
    return (ask - bid) + econ.taker_fee(1.0, ask, rate) + econ.taker_fee(1.0, bid, rate)


def make_prediction(pair: dict, t: float, q: dict, feats: dict, spec: dict) -> dict:
    preds0, preds1 = {}, {}
    for h in HORIZONS_MIN:
        m = spec["models"][str(h)]
        preds0[str(h)] = predict(m["m0"], feats, M0_FEATURES)
        preds1[str(h)] = predict(m["m1"], feats, FEATURES)
    y1 = preds1[str(PRIMARY_H)]
    side = 1 if y1 > 0 else (-1 if y1 < 0 else 0)
    cost = round_trip_cost(q["p_bid"], q["p_ask"], pair["fee_rate"])
    return {
        "id": f"{pair['pid']}|{int(t)}",
        "pid": pair["pid"],
        "ev": pair["p_event_id"],
        "t": int(t),
        "kr": q.get("k_recv"),
        "pr": q.get("p_recv"),
        "km": q["k_mid"],
        "pm": q["p_mid"],
        "pb": q["p_bid"],
        "pa": q["p_ask"],
        "pbs": q.get("p_bid_sz"),
        "pas": q.get("p_ask_sz"),
        "f": feats,
        "y0": preds0,
        "y1": preds1,
        "side": side,
        "cost": cost,
        "trade": bool(side != 0 and math.isfinite(cost) and abs(y1) > cost),
        "fee": pair["fee_rate"],
        "role": evidence_role(t),
        "spec": spec["_sha256"][:16],
        "code": spec.get("_code", ""),
        "v": VERSION,
    }


def taker_pnl(
    side: int, entry_bid: float, entry_ask: float, exit_bid: float, exit_ask: float, rate: float
) -> float:
    """Paper P&L per share: long Yes = buy at entry ask, sell at exit bid; short Yes (buy No) =
    sell at entry bid, buy back at exit ask. Taker fees on both legs (``economics.taker_fee``)."""
    if side > 0:
        gross = exit_bid - entry_ask
        legs = (entry_ask, exit_bid)
    elif side < 0:
        gross = entry_bid - exit_ask
        legs = (entry_bid, exit_ask)
    else:
        return NAN
    if not all(math.isfinite(x) for x in (gross, *legs)):
        return NAN
    return gross - econ.taker_fee(1.0, legs[0], rate) - econ.taker_fee(1.0, legs[1], rate)


# --- poller ------------------------------------------------------------------------------------


@dataclass
class PairState:
    pair: dict
    hist: deque = field(default_factory=deque)  # (ts, k_mid, p_mid) of valid polls
    retired_at: float | None = None


class Poller:
    """One instance = one process. ``k_lim`` / ``p_lim``: ``get(url, params) -> (status, json)``
    (``history_backfill.Limiter``); a list ``params`` means a JSON POST body."""

    def __init__(
        self,
        k_lim,
        p_lim,
        *,
        root: Path = ROOT,
        spec: dict | None = None,
        clock: Callable[[], float] = time.time,
        total_cap_bytes: int = TOTAL_CAP_BYTES,
    ) -> None:
        self.k_lim, self.p_lim, self.clock = k_lim, p_lim, clock
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.spec = spec or load_spec()
        self.cap = total_cap_bytes
        self.pairs: dict[str, PairState] = {}
        self.pairs_loaded_utc: str | None = None
        self.outcomes = OutcomeWriter(self.root)
        self.totals = {"cycles": 0, "quotes": 0, "predictions": 0, "outcomes": 0}

    # pairs ---------------------------------------------------------------------------------
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
                self.pairs[pid] = PairState(p, self._seed_hist(pid, now))
        self.pairs_loaded_utc = doc.get("refreshed_utc")
        return True

    def _seed_hist(self, pid: str, now: float) -> deque:
        """After a restart: valid mids of this pair's already-received quotes (recovered from disk
        by ``OutcomeWriter.recover``) within the feature lookback window."""
        out = []
        for t, q in sorted(self.outcomes.quotes.get(pid, {}).items()):
            k, p = _num(q.get("k_mid")), _num(q.get("p_mid"))
            if t >= now - HISTORY_S and t < now and math.isfinite(k) and math.isfinite(p):
                out.append((float(t), k, p))
        return deque(out)

    def active_states(self, now: float) -> list[PairState]:
        drop = [
            pid
            for pid, s in self.pairs.items()
            if s.retired_at is not None and now - s.retired_at > RETIRE_KEEP_S
        ]
        for pid in drop:
            del self.pairs[pid]
        return list(self.pairs.values())

    # fetch ---------------------------------------------------------------------------------
    def fetch_kalshi(self, tickers: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(tickers), CHUNK):
            chunk = tickers[i : i + CHUNK]
            st, data = self.k_lim.get(
                f"{KALSHI}/markets", {"tickers": ",".join(chunk), "limit": 1000}
            )
            recv = self.clock()
            if st != 200 or not isinstance(data, dict):
                continue
            for m in data.get("markets") or []:
                out[m.get("ticker")] = {**parse_kalshi_market(m), "k_recv": recv}
        return out

    def fetch_books(self, tokens: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(tokens), CHUNK):
            chunk = tokens[i : i + CHUNK]
            st, data = self.p_lim.get(f"{CLOB}/books", [{"token_id": t} for t in chunk])
            recv = self.clock()
            if st != 200 or not isinstance(data, list):
                continue
            for b in data:
                out[str(b.get("asset_id"))] = {**parse_book(b), "p_recv": recv}
        return out

    # cycle ---------------------------------------------------------------------------------
    def cycle(self, t_sched: float) -> dict:
        t0 = self.clock()
        if du_bytes(self.root) >= self.cap:
            raise CapReached(f"{self.root} >= {self.cap} bytes")
        self.load_pairs()
        states = self.active_states(t_sched)
        k = self.fetch_kalshi([s.pair["k_ticker"] for s in states])
        b = self.fetch_books([s.pair["token0"] for s in states])
        quotes, preds = [], []
        n_valid = 0
        for s in states:
            p = s.pair
            kq = k.get(p["k_ticker"], {})
            bq = b.get(p["token0"], {})
            q = {**{f: NAN for f in ("k_bid", "k_ask", "p_bid", "p_ask")}, **kq, **bq}
            q["k_mid"] = two_sided_mid(q["k_bid"], q["k_ask"])
            q["p_mid"] = two_sided_mid(q["p_bid"], q["p_ask"])
            quotes.append({"t": int(t_sched), "pid": p["pid"], **q})
            while s.hist and s.hist[0][0] < t_sched - HISTORY_S:
                s.hist.popleft()
            if s.retired_at is None:
                f = features(s.hist, t_sched, q["k_mid"], q["p_mid"])
                if f is not None:
                    preds.append(make_prediction(p, t_sched, q, f, self.spec))
            if math.isfinite(q["k_mid"]) and math.isfinite(q["p_mid"]):
                n_valid += 1
                s.hist.append((t_sched, q["k_mid"], q["p_mid"]))
        day = datetime.fromtimestamp(t_sched, UTC).strftime("%Y%m%d")
        append_jsonl(self.root / "quotes" / f"{day}.jsonl", quotes)
        append_jsonl(self.root / "predictions.jsonl", preds)  # before any outcome quote exists
        n_out = self.outcomes.update(t_sched, quotes, preds)
        self.totals["cycles"] += 1
        self.totals["quotes"] += len(quotes)
        self.totals["predictions"] += len(preds)
        self.totals["outcomes"] += n_out
        return {
            "t": utc_iso(t_sched),
            "pairs": len(states),
            "kalshi_ok": len(k),
            "books_ok": len(b),
            "both_valid": n_valid,
            "predictions": len(preds),
            "outcomes": n_out,
            "trades": sum(1 for r in preds if r["trade"]),
            "seconds": round(self.clock() - t0, 1),
            "rss_mb": rss_mb(),
            "k_requests": getattr(self.k_lim, "requests", None),
            "p_requests": getattr(self.p_lim, "requests", None),
        }


def gzip_old_quotes(root: Path, today: str) -> int:
    """Compress quote files older than yesterday (they are only read by recovery/analysis)."""
    n = 0
    for f in sorted((Path(root) / "quotes").glob("*.jsonl")):
        if f.stem < today and (int(today) - int(f.stem)) >= 2:
            with f.open("rb") as src, gzip.open(f.with_suffix(".jsonl.gz"), "wb") as dst:
                dst.write(src.read())
            f.unlink()
            n += 1
    return n


# --- outcomes ----------------------------------------------------------------------------------


class OutcomeWriter:
    """Outcome lines from quotes received AFTER the prediction was written. Keeps pending
    predictions and a quote window in memory; ``recover`` rebuilds both from disk after a
    restart. Only reads predictions and quotes; appends to ``outcomes.jsonl``."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.pending: dict[tuple[str, int], dict] = {}  # (pred id, h) -> prediction
        self.quotes: dict[str, dict[int, dict]] = {}  # pid -> t -> quote
        self.done: set[tuple[str, int]] = set()

    def _add_quote(self, q: dict) -> None:
        self.quotes.setdefault(q["pid"], {})[int(q["t"])] = q

    def _add_pred(self, r: dict) -> None:
        if r["t"] % OUTCOME_GRID_S:  # outcomes only for 10-minute-grid origins (disk budget)
            return
        for h in HORIZONS_MIN:
            key = (r["id"], h)
            if key not in self.done:
                self.pending[key] = r

    def recover(self, now: float, window_s: float = 3 * 3600) -> dict:
        lo = now - window_s
        for r in read_jsonl(self.root / "outcomes.jsonl"):
            if r.get("t0", 0) >= lo - 3600:
                self.done.add((r["id"], int(r["h"])))
        n_p = 0
        for r in read_jsonl(self.root / "predictions.jsonl"):
            if r["t"] >= lo:
                self._add_pred(r)
                n_p += 1
        n_q = 0
        days = {datetime.fromtimestamp(x, UTC).strftime("%Y%m%d") for x in (lo, now)}
        for d in sorted(days):
            for f in (self.root / "quotes" / f"{d}.jsonl", self.root / "quotes" / f"{d}.jsonl.gz"):
                for q in read_jsonl(f):
                    if q["t"] >= lo:
                        self._add_quote(q)
                        n_q += 1
        return {"predictions": n_p, "quotes": n_q, "done": len(self.done)}

    def _find(self, pid: str, due: int) -> dict | None:
        qs = self.quotes.get(pid, {})
        q = qs.get(due)
        if q is not None and math.isfinite(_num(q.get("p_mid"))):
            return q
        best = None
        for t, q in qs.items():
            if abs(t - due) <= OUTCOME_TOL_S and math.isfinite(_num(q.get("p_mid"))):
                if best is None or abs(t - due) < abs(best["t"] - due):
                    best = q
        return best

    def update(
        self,
        now: float,
        quotes: Sequence[dict] = (),
        preds: Sequence[dict] = (),
        write: bool = True,
    ) -> int:
        for q in quotes:
            self._add_quote(q)
        for r in preds:
            self._add_pred(r)
        rows = []
        for (pid_t, h), r in list(self.pending.items()):
            due = r["t"] + h * 60
            if now < due + OUTCOME_TOL_S:
                continue
            q = self._find(r["pid"], due)
            rows.append(outcome_row(r, h, q))
            del self.pending[(pid_t, h)]
            self.done.add((pid_t, h))
        # trim the quote window
        lo = now - HISTORY_S - 3600
        for pid in list(self.quotes):
            qs = self.quotes[pid]
            for t in [t for t in qs if t < lo]:
                del qs[t]
            if not qs:
                del self.quotes[pid]
        if write:
            append_jsonl(self.root / "outcomes.jsonl", rows)
        return len(rows)


def outcome_row(r: dict, h: int, q: dict | None) -> dict:
    base = {
        "id": r["id"],
        "pid": r["pid"],
        "ev": r["ev"],
        "h": h,
        "t0": r["t"],
        "due": r["t"] + h * 60,
        "role": r["role"],
        "written_utc": utc_iso(),
    }
    if q is None:
        return {**base, "status": "unavailable"}
    pnl = taker_pnl(
        r["side"], _num(r["pb"]), _num(r["pa"]), _num(q["p_bid"]), _num(q["p_ask"]), _num(r["fee"])
    )
    return {
        **base,
        "status": "evaluated",
        "t_obs": q["t"],
        "p_recv": q.get("p_recv"),
        "pm_h": q["p_mid"],
        "pb_h": q["p_bid"],
        "pa_h": q["p_ask"],
        "km_h": q.get("k_mid"),
        "dp": _num(q["p_mid"]) - _num(r["pm"]),
        "pnl_taker": pnl,
        "pnl_trade": pnl if r["trade"] else None,
    }


# --- registered analysis (E009) ----------------------------------------------------------------


def _boot(S: np.ndarray, stat: Callable[[np.ndarray], float], n_boot: int, seed: int):
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        out[i] = stat(S[rng.integers(0, len(S), len(S))].sum(0))
    return stat(S.sum(0)), out


def _pnl_stat(rows: Sequence[tuple[str, Any]], n_boot: int, seed: int) -> dict:
    per: dict[str, np.ndarray] = {}
    for ev, pnl in rows:
        if pnl is None or not math.isfinite(_num(pnl)):
            continue
        per[ev] = per.get(ev, np.zeros(2)) + np.array([float(pnl), 1.0])
    n = int(sum(v[1] for v in per.values()))
    if len(per) < 2:
        return {"n_trades": n, "n_clusters": len(per), "status": "insufficient"}
    S = np.vstack(list(per.values()))
    m, mb = _boot(S, lambda s: s[0] / s[1], n_boot, seed)
    ok = n >= econ.MIN_TRADES and len(per) >= econ.MIN_CLUSTERS
    return {
        "status": "ok" if ok else "below_minimum",
        "n_trades": n,
        "n_clusters": len(per),
        "mean_pnl_per_share": m,
        "ci": [float(np.percentile(mb, 2.5)), float(np.percentile(mb, 97.5))],
        "p_one_sided": float((np.sum(mb <= 0) + 1) / (len(mb) + 1)),
    }


def _partial_slope(s: np.ndarray) -> float:
    """OLS coefficient on dk1 in dp ~ 1 + y0 + dk1 from summed sufficient statistics
    ``[n, Sy0, Sdk, Sy0y0, Sy0dk, Sdkdk, Sdp, Sy0dp, Sdkdp]``."""
    n, a, b, aa, ab, bb, y, ay, by = s
    xtx = np.array([[n, a, b], [a, aa, ab], [b, ab, bb]])
    xty = np.array([y, ay, by])
    if not np.isfinite(xtx).all() or n < 3:
        return NAN
    return float(np.linalg.lstsq(xtx, xty, rcond=None)[0][2])  # min-norm if y0 is constant


def analyze(
    root: Path = ROOT,
    *,
    start_utc: str,
    end_utc: str,
    n_boot: int = 4000,
    seed: int = 20261012,
    role: str = "prospective_confirmation",
    now: float | None = None,
) -> dict:
    """E009 statistics over origins in ``[start, end)`` with the given role. Primary: relative
    MSE gain of frozen M1 over frozen M0 for the 20-min Polymarket mid change, non-overlapping
    origins (``t % 1200 == 0``), event-clustered bootstrap, one-sided p (percentile-bootstrap tail
    share, not a null-centred test). Secondary: the same at 10/60 min; the dk1 slope (simple and
    partial on the M0 prediction); executable taker P&L.

    Hygiene (E009 challenger review): duplicate outcome lines are de-duplicated on ``(id, h)``
    keeping the first; an origin whose Kalshi or Polymarket receipt is more than
    ``MAX_RECV_LAG_S`` after ``t`` is excluded (``origin_late``); an outcome quote received more
    than ``MAX_RECV_LAG_S`` after its own poll time counts as ``unavailable``; grid origins whose
    outcome is due but has no line are counted as ``missing_line``."""
    lo = datetime.fromisoformat(start_utc.replace("Z", "+00:00")).timestamp()
    hi = datetime.fromisoformat(end_utc.replace("Z", "+00:00")).timestamp()
    now = time.time() if now is None else now
    preds, late = {}, 0
    for r in read_jsonl(Path(root) / "predictions.jsonl"):
        if not (lo <= r["t"] < hi and r["role"] == role):
            continue
        lags = [_num(r.get(k)) - r["t"] for k in ("kr", "pr")]
        if not all(math.isfinite(x) and x <= MAX_RECV_LAG_S for x in lags):
            late += 1
            continue
        preds[r["id"]] = r
    outs: dict[int, list] = {h: [] for h in HORIZONS_MIN}
    n_unavail = {h: 0 for h in HORIZONS_MIN}
    n_late_out = {h: 0 for h in HORIZONS_MIN}
    seen: set[tuple[str, int]] = set()
    dups = 0
    for o in read_jsonl(Path(root) / "outcomes.jsonl"):
        h = int(o["h"])
        key = (o["id"], h)
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        r = preds.get(o["id"])
        if r is None or r["t"] % (h * 60) != 0:
            continue
        if o["status"] != "evaluated":
            n_unavail[h] += 1
            continue
        if not (_num(o.get("p_recv")) - _num(o.get("t_obs")) <= MAX_RECV_LAG_S):
            n_unavail[h] += 1
            n_late_out[h] += 1
            continue
        outs[h].append((r, o))
    missing = {
        h: sum(
            1
            for r in preds.values()
            if r["t"] % (h * 60) == 0
            and r["t"] + h * 60 + OUTCOME_TOL_S + 600 <= now
            and (r["id"], h) not in seen
        )
        for h in HORIZONS_MIN
    }
    res: dict[str, Any] = {
        "window": [start_utc, end_utc],
        "role": role,
        "n_boot": n_boot,
        "origin_late": late,
        "duplicate_outcome_lines": dups,
        "unavailable": n_unavail,
        "unavailable_late_receipt": n_late_out,
        "missing_line": missing,
        "horizons": {},
    }
    for h in HORIZONS_MIN:
        per: dict[str, np.ndarray] = {}
        for r, o in outs[h]:
            y = o["dp"]
            y0 = r["y0"][str(h)]
            e0, e1 = y - y0, y - r["y1"][str(h)]
            dk = r["f"]["dk1"]
            v = np.array(
                [
                    e0 * e0,
                    e0 * e0 - e1 * e1,
                    1.0,
                    dk * y,
                    dk * dk,
                    dk,
                    y,
                    y0,
                    y0 * y0,
                    y0 * dk,
                    y0 * y,
                ]
            )
            per[r["ev"]] = per.get(r["ev"], np.zeros(11)) + v
        if len(per) < 2:
            res["horizons"][str(h)] = {"status": "insufficient", "n_clusters": len(per)}
            continue
        names = list(per)
        S = np.vstack([per[c] for c in names])

        def gain(s):
            return s[1] / s[0] if s[0] > 0 else NAN

        def slope(s):
            n = s[2]
            var = s[4] - s[5] ** 2 / n
            return (s[3] - s[5] * s[6] / n) / var if var > 0 else NAN

        def pslope(s):
            return _partial_slope(np.array([s[2], s[7], s[5], s[8], s[9], s[4], s[6], s[10], s[3]]))

        g, gb = _boot(S, gain, n_boot, seed)
        b, bb = _boot(S, slope, n_boot, seed + 1)
        pb_, pbb = _boot(S, pslope, n_boot, seed + 4)
        tot = S.sum(0)
        loo = [gain(tot - S[i]) for i in range(len(S))]
        share = S[:, 0] / tot[0] if tot[0] > 0 else np.full(len(S), NAN)
        res["horizons"][str(h)] = {
            "status": "ok",
            "n_origins": int(S[:, 2].sum()),
            "n_clusters": len(per),
            "rel_mse_gain": g,
            "ci": [float(np.nanpercentile(gb, 2.5)), float(np.nanpercentile(gb, 97.5))],
            "p_one_sided": float((np.sum(gb <= 0) + 1) / (len(gb) + 1)),
            "slope_dp_on_dk1": b,
            "slope_ci": [float(np.nanpercentile(bb, 2.5)), float(np.nanpercentile(bb, 97.5))],
            "partial_slope_dk1_given_m0": pb_,
            "partial_slope_ci": [
                float(np.nanpercentile(pbb, 2.5)),
                float(np.nanpercentile(pbb, 97.5)),
            ],
            "largest_event_sse0_share": float(np.nanmax(share)),
            "leave_one_event_out_gain_range": [float(np.nanmin(loo)), float(np.nanmax(loo))],
        }
    # executable P&L at the primary horizon (trade rule frozen in make_prediction)
    res["executable_pnl"] = _pnl_stat(
        [(r["ev"], o.get("pnl_trade")) for r, o in outs[PRIMARY_H]], n_boot, seed + 2
    )
    # descriptive: every primary origin with |dk1| >= 2c, traded in the predicted direction
    res["pnl_all_dk1_ge_2c"] = _pnl_stat(
        [(r["ev"], o.get("pnl_taker")) for r, o in outs[PRIMARY_H] if abs(r["f"]["dk1"]) >= 0.02],
        n_boot,
        seed + 3,
    )
    return res


def ops_stats(root: Path = ROOT) -> dict:
    """Operational pilot statistics only (rates, coverage, feature spreads). Reads predictions and
    quotes, never outcomes."""
    preds = list(read_jsonl(Path(root) / "predictions.jsonl"))
    qrows = []
    for f in sorted((Path(root) / "quotes").glob("*.jsonl*")):
        qrows.extend(read_jsonl(f))
    ts = sorted({q["t"] for q in qrows})
    span_h = (ts[-1] - ts[0]) / 3600 if len(ts) > 1 else 0.0
    valid = [q for q in qrows if q.get("k_mid") is not None and q.get("p_mid") is not None]
    dk = np.array([r["f"]["dk1"] for r in preds]) if preds else np.empty(0)
    gap = np.array([r["f"]["gap"] for r in preds]) if preds else np.empty(0)
    spr = np.array([r["pa"] - r["pb"] for r in preds]) if preds else np.empty(0)
    prim = [r for r in preds if r["t"] % (PRIMARY_H * 60) == 0]
    return {
        "cycles": len(ts),
        "span_h": round(span_h, 2),
        "quote_rows": len(qrows),
        "both_valid_share": round(len(valid) / len(qrows), 3) if qrows else None,
        "pairs_seen": len({q["pid"] for q in qrows}),
        "predictions": len(preds),
        "predictions_per_hour": round(len(preds) / span_h, 1) if span_h else None,
        "primary_origins": len(prim),
        "primary_origins_per_hour": round(len(prim) / span_h, 1) if span_h else None,
        "pairs_with_predictions": len({r["pid"] for r in preds}),
        "events_with_predictions": len({r["ev"] for r in preds}),
        "trade_rule_fired": sum(1 for r in preds if r["trade"]),
        "dk1_abs_quantiles": {q: float(np.quantile(np.abs(dk), q)) for q in (0.5, 0.9, 0.99)}
        if len(dk)
        else None,
        "dk1_nonzero_share": float((dk != 0).mean()) if len(dk) else None,
        "gap_abs_median": float(np.median(np.abs(gap))) if len(gap) else None,
        "pm_spread_median": float(np.median(spr)) if len(spr) else None,
    }


# --- process helpers ---------------------------------------------------------------------------


def http_transport(timeout: float = 30.0):
    """Transport for ``history_backfill.Limiter``: dict params -> GET, list params -> JSON POST."""
    import httpx

    client = httpx.Client(
        timeout=timeout, headers={"User-Agent": "arepo-research-lab/1", "Accept-Encoding": "gzip"}
    )

    def fetch(url: str, params) -> tuple[int, bytes, dict]:
        r = (
            client.post(url, json=params)
            if isinstance(params, list)
            else client.get(url, params=params)
        )
        return r.status_code, r.content, dict(r.headers)

    return fetch


def spawn_refresh(script: Path, root: Path, log_path: Path) -> subprocess.Popen:
    import sys

    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = log_path.open("a")
    return subprocess.Popen(
        [sys.executable, str(script), "--refresh", "--root", str(root)], stdout=fh, stderr=fh
    )
