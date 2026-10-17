# ruff: noqa: E501
"""CB9-P: hourly-anchored Pyth equity dailies (docs/research_lab/CREATIVE_BATCH_9.md CB9-P, 1.2, 1.3 outcome guard, 2.1, 2.2, 2.6, 2.7 P,
CB9-F q0180 Yahoo part / q0183 / q0184 / q0189 P / q0191 / q0195 / q0196 / q0198).

Frame regexes and rule-text flags, the Yahoo hourly-bar parser with the pinned clock (timestamp = bar START ``o``; end ``e = min(o + 60 min,
16:00 ET)`` (13:00 ET on half sessions); rows starting before 09:30 ET or at/after the close, and zero-length rows, are dropped; a full session
has exactly 7 bars, a half session 4; any other count -> "bars unavailable", counted, never repaired; a bar is usable at ``t`` iff
``e + 120 s <= t``), the smoke open/close check, sigma, the frozen lognormal digital, P1 units (taker, held to settlement), P2 quotes (resting
maker around the model value vs around the book mid; fills by ``cb3_maker.quote_fills``, queue rule), guarded outcome files (opened only by the
screen / rep jobs), the Stage-2 receipt-timed collection rules and the Yahoo partial-failure rule.

Outcome guard: Gamma ``outcomePrices`` go only to ``outcomes_guarded.csv.gz``; the settlement-day daily closes and the last (15:30-16:00) bar of every
session go only to ``closes_settle_guarded.csv.gz``. ``strikes.csv.gz`` holds ``K_d`` (the prior session's close); consecutive ``K_d`` determine an
outcome (disclosed, section 1.3), so no code path outside the screen compares them. EXPLORATORY; no edge, calibration or profitability claim.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import history_backfill as hb

Refused = c9.Refused
NotNow = c9.NotNow
ET = ZoneInfo("America/New_York")

# ---- population (q0183) --------------------------------------------------------------------------------------------------------------------

QUESTION_RE = r"^(.+) \(([A-Z]{1,5})\) Up or Down on [A-Z][a-z]+ \d{1,2}\??$"
SOURCE_RE = r"^https?://(?:www\.)?pythdata\.app/explore/Equity\.US\.([A-Z]{1,5})(?:/|%2F|%2f)USD/?(?:\?.*)?$"
# Rule-text flags (CB9-P population 3). Written from the probe-5 summary of the out-of-window 2026-09-15 NVIDIA text and the committed Pyth
# monthly-close text (PHASE_03 evidence). OPEN ITEM for the freeze check: verify every flag against the full 2026-09-15 text before the rules
# file is committed (CREATIVE_HYPOTHESES_2026-10-18 says "exactly equal resolves Down" while probe 5 says "equal -> 50-50"; the design freezes the
# 50-50 equality clause, so a Down-on-equal text fails the flag and the market leaves the frame, counted).
FLAG_RES = {
    "close_final_minute": r'(?is)"Close".{0,250}?final minute',
    "prior_trading_day": r"(?i)most recent prior trading day",
    "equality_50_50": r"(?i)\bequal\b[^.]{0,200}?50-50",  # same sentence (M4): an "equal -> Down" sentence followed by the no-trade 50-50 sentence fails
    "no_trade_50_50": r"(?i)(?:does not|doesn't|do not|no)\s+trade[^.]{0,250}?50-50",
}
EXCLUDE_RES = {"opens": r"(?i)\bopens?\b", "strike": r"(?i)close (?:above|below)|above \$|below \$"}
# Older (2025) Up/Down text versions (official exchange close vs the open or vs the prior close, rounded to the cent): a different settlement rule,
# excluded with their own reason (the frozen flags would usually fail as well). The current text says "used exactly as published by Pyth, without rounding".
OLD_VERSION_RES = {"old_version_rounded": r"(?i)\brounded\s+to\b", "old_version_vs_open": r"(?i)\b(?:opening|open)\s+price\b"}
OUTCOME_LABELS = ("Up", "Down")
TICKER_MAP_RULE = "Yahoo symbol = Pyth ticker (identity); a ticker without 7 bars on every window session is unavailable (counted)"
GAMMA_END_WINDOW_EDT = ("19:59:00", "20:01:00")
WINDOW = ("2026-04-13", "2026-08-10")
GAP = ("2026-06-12", "2026-06-18")
BARS_FROM = "2026-02-01"
HOLIDAYS_2026 = ("2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25")
HALF_SESSIONS_2026 = ("2026-11-27", "2026-12-24")
OPEN_ET = (9, 30)
CLOSE_ET = (16, 0)
HALF_CLOSE_ET = (13, 0)
FULL_BARS = 7
HALF_BARS = 4

# ---- clocks and features -------------------------------------------------------------------------------------------------------------------

BAR_S = 3600
USABLE_LAG_S = 120
LATENCY_LAG_S = 300  # robustness (vi)
CHECKPOINT_BARS_ET = ((9, 30), (11, 30), (14, 30))  # checkpoints 10:32, 12:32, 15:32 ET = bar end + 120 s
SIGMA_SESSIONS = 20
SIGMA_MIN_RETURNS = 100
SIGMA_RULE = ("per session: the six one-hour log returns ln(c0/o0), ln(c1/c0), ..., ln(c5/c4) of bars 09:30..14:30 (the 30-minute 15:30 bar is not an hourly "
              "return and is never read); overnight gaps excluded; SD (ddof 1) over the prior 20 full NYSE sessions; >= 100 returns else unavailable; per hour")
STALE_RULE = "P1_stale: S from the bar before the latest usable bar in the ticker's bar sequence (for the 10:32 checkpoint: the prior session's 14:30 bar)"

# ---- book, P1, P2 ------------------------------------------------------------------------------------------------------------------------

FRESH_S = 120
PMXT_HOURS_Z = (14, 16, 19)  # EDT checkpoints 14:32Z, 16:32Z, 19:32Z
EDGE = 0.05
MIN_ASK_SIZE = 5.0
FEE_RATE_FLOOR = 0.04
COST_ROBUST = 0.005
SIZE_WEIGHT_CAP = 2000.0
QUOTE_HALF_WIDTH = 0.01
QUOTE_SIZE = 20.0
QUOTE_LIFE_S = 300
REBATE_SHARE = 0.25
DEFAULT_TICK = 0.01
PRINT_WINDOW_S = (USABLE_LAG_S, LATENCY_LAG_S + QUOTE_LIFE_S)  # prints in [e + 120, e + 600] cover both quote windows
PRINT_PAGES = 3
FLOOR_P1 = 0.01
FLOOR_P2 = 0.003
SOURCE_MIN_ABS_RET = 0.001
SOURCE_DISAGREE_MAX = 0.02
MONTH_MIN_UNITS = 30
MONTH_SHARE = 2 / 3

# ---- census gates -------------------------------------------------------------------------------------------------------------------------

GP = {"min_p1_units": 300, "min_sessions": 40, "min_tickers": 15, "min_p2_origins": 1500, "min_p2_fills_each_quote": 100}
P2_MIN_FILL_RATE = 0.02
AUDIT_PASS = 0.90
AVAILABLE_MIN = 0.80
INGRESS_CAP_GB = 40.0
OUTPUT_CAP_BOOKS_GB = 0.02
OUTPUT_CAP_FRAME_GB = 0.01

# ---- Stage 2 --------------------------------------------------------------------------------------------------------------------------------

STAGE2_SESSIONS = 30
STAGE2_COLLECT_MAX_DAYS = 63
STAGE2_UNAVAILABLE_MAX = 0.20
YAHOO_RPS = 1.0
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
CLOB_BOOK = "https://clob.polymarket.com/book"

# ---- smoke (Yahoo, Gamma paging, pmxt heads) ----------------------------------------------------------------------------------------------

SMOKE_TICKER = "NVDA"
SMOKE_SESSIONS = ("2026-09-15", "2026-09-16")
SMOKE_TOL = 0.002
SMOKE_GAMMA_DAYS = ("2026-09-15", "2026-09-16")
SMOKE_PMXT_SEED = "arepo-cb9-smoke-pmxt"
SMOKE_PMXT_N = 3

FRAME_COLUMNS = ["market_id", "condition_id", "token_up", "token_down", "up_idx", "ticker", "day", "event_id", "event_ids", "neg_risk_market_id", "series_ids",
                 "end_at", "question", "desc_sha256", "resolution_source"]
OUTCOME_COLUMNS = ["market_id", "day", "outcome_labels", "outcome_prices"]
BAR_COLUMNS = ["ticker", "day", "o", "e", "open", "close"]
STRIKE_COLUMNS = ["ticker", "day", "k_d", "k_day"]
SETTLE_COLUMNS = ["ticker", "day", "kind", "o", "close"]
STATE_COLUMNS = ["market_id", "day", "ckpt", "lag_s", "t", "token", "fresh", "crossed", "book_status", "best_bid", "best_ask", "ask_size", "bid_size", "fee_bps",
                 "tick", "bids_top", "asks_top", "n_events_window"]
PRINT_COLUMNS = ["market_id", "day", "ckpt", "ts", "idx", "side", "price", "size"]
GUARDED_FILES = ("outcomes_guarded.csv.gz", "closes_settle_guarded.csv.gz")
GUARDED_ALLOWED_JOBS = ("screen-P", "rep-P")


# =====================================================================================================================================
# Calendar and clocks
# =====================================================================================================================================


def _d(s: str) -> date:
    return date.fromisoformat(s)


def is_full_session(day: str) -> bool:
    d = _d(day)
    return d.weekday() < 5 and day not in HOLIDAYS_2026 and day not in HALF_SESSIONS_2026


def full_sessions(first: str, end: str) -> list[str]:
    out, d = [], _d(first)
    while d < _d(end):
        s = d.isoformat()
        if is_full_session(s):
            out.append(s)
        d += timedelta(days=1)
    return out


def p_days(window: tuple[str, str] = WINDOW, gap: tuple[str, str] = GAP) -> list[str]:
    """Full NYSE sessions in the P window minus the pmxt gap [06-12, 06-18)."""
    return [d for d in full_sessions(*window) if not (gap[0] <= d < gap[1])]


def et_epoch(day: str, hh: int, mm: int = 0) -> float:
    return datetime(*map(int, day.split("-")), hh, mm, tzinfo=ET).timestamp()


def close_et(day: str) -> tuple[int, int]:
    return HALF_CLOSE_ET if day in HALF_SESSIONS_2026 else CLOSE_ET


def expected_bars(day: str) -> int:
    return HALF_BARS if day in HALF_SESSIONS_2026 else FULL_BARS


def et_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, ET).date().isoformat()


def checkpoints(day: str, lag_s: int = USABLE_LAG_S) -> list[tuple[int, float, float]]:
    """(index, bar end e, checkpoint t = e + lag) of the three checkpoints of a session (EDT or EST by the zone)."""
    out = []
    for i, (hh, mm) in enumerate(CHECKPOINT_BARS_ET):
        e = et_epoch(day, hh, mm) + BAR_S
        out.append((i, e, e + lag_s))
    return out


# =====================================================================================================================================
# Yahoo chart parsing and the pinned bar clock
# =====================================================================================================================================


def parse_chart(doc: Any) -> list[dict]:
    """Rows of a Yahoo v8 chart reply: ``o`` (timestamp = bar START), open, high, low, close (``None`` kept as NaN). A malformed reply -> []."""
    try:
        res = doc["chart"]["result"][0]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        return []
    out = []
    for i, t in enumerate(ts):
        def g(k: str, i: int = i) -> float:
            v = (q.get(k) or [None] * len(ts))[i] if i < len(q.get(k) or []) else None
            return float(v) if v is not None else math.nan
        out.append({"o": int(t), "open": g("open"), "high": g("high"), "low": g("low"), "close": g("close")})
    return out


def session_bars(rows: list[dict], day: str) -> tuple[list[dict] | None, dict]:
    """The pinned clock for one session: rows whose start ``o`` falls on ``day`` (ET); ``e = min(o + 60 min, close)``; drop rows with
    ``o < 09:30 ET`` or ``o >= close`` (a closing row stamped at the close included), zero-length rows (``e <= o``) and rows with a missing open or
    close. Exactly 7 bars (4 on a half session) must remain, else ``None`` ("bars unavailable"). Info records the dropped rows by reason."""
    t_open = et_epoch(day, *OPEN_ET)
    ch, cm_ = close_et(day)
    t_close = et_epoch(day, ch, cm_)
    info = {"n_rows": 0, "dropped_pre_open": 0, "dropped_at_or_after_close": 0, "dropped_zero_length": 0, "dropped_missing": 0}
    bars = []
    for r in sorted(rows, key=lambda r: r["o"]):
        if et_day(r["o"]) != day:
            continue
        info["n_rows"] += 1
        o = float(r["o"])
        if o < t_open:
            info["dropped_pre_open"] += 1
            continue
        if o >= t_close:
            info["dropped_at_or_after_close"] += 1
            continue
        e = min(o + BAR_S, t_close)
        if e <= o:
            info["dropped_zero_length"] += 1
            continue
        if not (math.isfinite(r["open"]) and math.isfinite(r["close"])):
            info["dropped_missing"] += 1
            continue
        bars.append({"o": o, "e": e, "open": r["open"], "close": r["close"]})
    info["n_bars"] = len(bars)
    info["expected"] = expected_bars(day)
    info["first_start_0930"] = bool(bars and bars[0]["o"] == t_open)
    if len(bars) != expected_bars(day):
        info["status"] = "bars_unavailable"
        return None, info
    info["status"] = "ok"
    return bars, info


def usable(bar: dict, t: float, lag_s: int = USABLE_LAG_S) -> bool:
    return bar["e"] + lag_s <= t


def latest_usable(bars: list[dict], t: float, lag_s: int = USABLE_LAG_S) -> dict | None:
    ok = [b for b in bars if usable(b, t, lag_s)]
    return max(ok, key=lambda b: b["e"]) if ok else None


def daily_rows(doc: Any) -> dict[str, dict]:
    """{ET day: {"open", "close"}} of a Yahoo 1d reply (the row's timestamp is the session start)."""
    return {et_day(r["o"]): {"open": r["open"], "close": r["close"]} for r in parse_chart(doc) if math.isfinite(r["close"])}


def smoke_yahoo_check(hourly_doc: Any, daily_doc: Any, sessions: tuple[str, ...] = SMOKE_SESSIONS, tol: float = SMOKE_TOL) -> dict:
    """q0180 Yahoo bar clock: for each out-of-window session, after the drop exactly 7 bars remain, the first starts at 09:30 ET, its open equals
    the daily open within 0.2%, the last bar's close equals the daily close within 0.2%; dropped rows recorded by count. Any failure -> P
    'not testable (source)', counted; the bar rule is never re-fitted."""
    rows = parse_chart(hourly_doc)
    daily = daily_rows(daily_doc)
    per = {}
    for day in sessions:
        bars, info = session_bars(rows, day)
        dd = daily.get(day)
        ok_open = ok_close = False
        if bars and dd and dd["open"] and dd["close"]:
            ok_open = abs(bars[0]["open"] / dd["open"] - 1.0) <= tol
            ok_close = abs(bars[-1]["close"] / dd["close"] - 1.0) <= tol
        per[day] = {**info, "daily_found": dd is not None, "open_ok": bool(ok_open), "close_ok": bool(ok_close),
                    "pass": bool(bars is not None and info["first_start_0930"] and ok_open and ok_close)}
    return {"sessions": per, "pass": all(v["pass"] for v in per.values()) and len(per) == len(sessions)}


# =====================================================================================================================================
# Sigma, model value, fees
# =====================================================================================================================================


def hourly_returns(bars: list[dict]) -> list[float]:
    """Six one-hour log returns of a full session from its bars 09:30..14:30 (the stored feature bars, 6, or a full parsed session, 7); the
    30-minute last bar is never read."""
    if len(bars) not in (FULL_BARS - 1, FULL_BARS):
        return []
    c = [b["close"] for b in bars[:6]]
    r = [math.log(c[0] / bars[0]["open"])] + [math.log(c[i] / c[i - 1]) for i in range(1, 6)]
    return [x for x in r if math.isfinite(x)]


def sigma_for(day: str, bars_by_day: dict[str, list[dict] | None], sessions: list[str]) -> float | None:
    """SD of the hourly returns over the 20 full sessions before ``day`` (calendar); sessions with unavailable bars contribute nothing; < 100
    returns -> None (unavailable)."""
    prior = [s for s in sessions if s < day][-SIGMA_SESSIONS:]
    rets = [x for s in prior for x in hourly_returns(bars_by_day.get(s) or [])]
    if len(rets) < SIGMA_MIN_RETURNS:
        return None
    return float(np.std(np.asarray(rets), ddof=1))


def tau_hours(day: str, t: float) -> float:
    return (et_epoch(day, *close_et(day)) - t) / 3600.0


def fair_up(s_t: float, k_d: float, sigma: float, tau_h: float) -> float | None:
    """Frozen lognormal digital: Phi(ln(S/K) / (sigma sqrt(tau))); no drift, no fitting."""
    from scipy.stats import norm  # noqa: PLC0415

    if not (s_t > 0 and k_d > 0 and sigma and sigma > 0 and tau_h > 0):
        return None
    return float(norm.cdf(math.log(s_t / k_d) / (sigma * math.sqrt(tau_h))))


def fee_rate(recorded_bps: float | None) -> float:
    r = (float(recorded_bps) / 1e4) if recorded_bps is not None and math.isfinite(float(recorded_bps)) else 0.0
    return max(r, FEE_RATE_FLOOR)


def taker_fee(a: float, rate: float) -> float:
    return rate * a * (1.0 - a)


def floor_tick(x: float, tick: float) -> float:
    return round(math.floor(x / tick + 1e-9) * tick, 6)


def ceil_tick(x: float, tick: float) -> float:
    return round(math.ceil(x / tick - 1e-9) * tick, 6)


# =====================================================================================================================================
# P1 units and P2 quotes (pure)
# =====================================================================================================================================


def p1_unit(fair: float, books: dict[str, dict], *, cost_add: float = 0.0) -> dict | None:
    """Traded iff on some token ``fair_token - a - f(a) >= 0.05`` with >= 5 shares at ``a`` on a fresh, uncrossed book (if both, the larger edge).
    ``books`` maps "up"/"down" to state dicts (best_ask, ask_size, fee_bps, fresh, crossed). Returns the trade or None."""
    best = None
    for side, fv in (("up", fair), ("down", 1.0 - fair)):
        b = books.get(side) or {}
        a = b.get("best_ask")
        if a is None or not b.get("fresh") or b.get("crossed") or not (b.get("ask_size") or 0) >= MIN_ASK_SIZE:
            continue
        a = float(a) + cost_add
        r = fee_rate(b.get("fee_bps"))
        edge = fv - a - taker_fee(a, r)
        if edge >= EDGE - 1e-12 and (best is None or edge > best["edge"]):
            best = {"token": side, "a": a, "rate": r, "fee": taker_fee(a, r), "edge": edge, "ask_size": float(b.get("ask_size") or 0.0)}
    return best


def p1_net(trade: dict, y_token: float) -> float:
    return float(y_token) - trade["a"] - trade["fee"]


def p2_quotes(fair: float, best_bid: float, best_ask: float, tick: float) -> dict:
    """Model-centred and mid-centred quote pairs on the Up token (bid floor_tick(c - 1c), ask ceil_tick(c + 1c)), each capped passive
    (bid <= best ask - tick, ask >= best bid + tick)."""
    def pair(c: float) -> tuple[float, float]:
        bid = min(floor_tick(c - QUOTE_HALF_WIDTH, tick), round(best_ask - tick, 6))
        ask = max(ceil_tick(c + QUOTE_HALF_WIDTH, tick), round(best_bid + tick, 6))
        return max(bid, tick), min(ask, 1.0 - tick)

    mid = (best_bid + best_ask) / 2.0
    return {"model": pair(fair), "mid": pair(mid), "mid_price": mid}


def up_prints(rows: list[dict], up_idx: int) -> dict[str, np.ndarray]:
    """Prints in Up terms for ``cb3_maker.quote_fills``: ``p0`` = Up price, ``buy`` = taker buys Up (BUY Up or SELL Down), sorted by ts."""
    rows = sorted(rows, key=lambda r: (float(r["ts"]), float(r["price"])))
    ts = np.array([float(r["ts"]) for r in rows], float)
    up = np.array([int(r["idx"]) == up_idx for r in rows], bool)
    price = np.array([float(r["price"]) for r in rows], float)
    side_buy = np.array([str(r["side"]).upper() in ("BUY", "1") for r in rows], bool)
    return {"ts": ts, "p0": np.where(up, price, 1.0 - price), "buy": np.where(up, side_buy, ~side_buy), "size": np.array([float(r["size"]) for r in rows], float)}


def depth_at(levels: dict[float, float], price: float) -> float:
    return float(next((s for p, s in levels.items() if abs(p - price) < 1e-9), 0.0))


def through_fill(pr: dict[str, np.ndarray], t: float, side: str, price: float, life: float = QUOTE_LIFE_S, own: float = QUOTE_SIZE) -> bool:
    """Trade-through rule (binding cost robustness, worst-case queue): filled iff the cumulative size of prints STRICTLY through the quote in
    (t, t + life) reaches ``own``."""
    lo, hi = np.searchsorted(pr["ts"], t, side="right"), np.searchsorted(pr["ts"], t + life, side="left")
    if side == "bid":
        sel = (~pr["buy"][lo:hi]) & (pr["p0"][lo:hi] < price - 1e-9)
    else:
        sel = pr["buy"][lo:hi] & (pr["p0"][lo:hi] > price + 1e-9)
    return bool(pr["size"][lo:hi][sel].sum() >= own - 1e-12)


def quote_pair_pnl(pr: dict[str, np.ndarray], t: float, bid: float, ask: float, bid_depth: float, ask_depth: float, y_up: float | None, *, rule: str = "queue") -> dict:
    """Fills of one quote pair (20 shares each side, life 300 s) and its P&L held to settlement: bid fill ``20 (Y - bid)``, ask fill ``20 (ask - Y)``.
    ``y_up`` None -> fills only (census). ``rule`` queue (primary, ``cb3_maker.quote_fills``) or through (robustness)."""
    from . import cb3_maker as c3  # noqa: PLC0415

    if rule == "queue":
        fb = c3.quote_fills(pr, t, "bid", bid, bid_depth, life=QUOTE_LIFE_S, own=QUOTE_SIZE)["queue"][0] == 1
        fa = c3.quote_fills(pr, t, "ask", ask, ask_depth, life=QUOTE_LIFE_S, own=QUOTE_SIZE)["queue"][0] == 1
    else:
        fb, fa = through_fill(pr, t, "bid", bid), through_fill(pr, t, "ask", ask)
    out = {"bid_filled": bool(fb), "ask_filled": bool(fa), "filled_shares": QUOTE_SIZE * (int(fb) + int(fa))}
    if y_up is not None:
        pnl = (QUOTE_SIZE * (y_up - bid) if fb else 0.0) + (QUOTE_SIZE * (ask - y_up) if fa else 0.0)
        reb = REBATE_SHARE * FEE_RATE_FLOOR * ((QUOTE_SIZE * bid * (1 - bid)) if fb else 0.0) + REBATE_SHARE * FEE_RATE_FLOOR * ((QUOTE_SIZE * ask * (1 - ask)) if fa else 0.0)
        out.update(pnl=pnl, pnl_rebate=pnl + reb)
    return out


def outcome_y(labels: list[str], prices: list[float], token: str) -> float | None:
    """Settlement value of the Up / Down token from the guarded Gamma outcome (0.5 on a 50-50 resolution); None if unresolved / malformed."""
    try:
        i = [str(x).strip().lower() for x in labels].index(token)
        y = float(prices[i])
    except (ValueError, IndexError, TypeError):
        return None
    if y in (0.0, 1.0, 0.5):
        return y
    return None


# =====================================================================================================================================
# Frame parsing (q0183)
# =====================================================================================================================================


def parse_market(m: dict, day: str) -> tuple[dict | None, str]:
    """(frame row, reason). Primary population: question regex with ticker group, resolution source ``pythdata.app/explore/Equity.US.<T>/USD`` with
    the same ticker, outcomes exactly Up/Down, two tokens, not neg-risk, not 'Opens' / strike, every rule-text flag present."""
    from . import cb6_tail as c6  # noqa: PLC0415

    q = str(m.get("question") or "")
    src = str(m.get("resolutionSource") or "")
    desc = str(m.get("description") or "")
    if re.search(EXCLUDE_RES["opens"], q):
        return None, "opens_market"
    if re.search(EXCLUDE_RES["strike"], q):
        return None, "strike_market"
    mq = re.match(QUESTION_RE, q)
    if not mq:
        return None, "question_re"
    ms = re.match(SOURCE_RE, src)
    if not ms or ms.group(1) != mq.group(2):
        return None, "source_re"
    if bool(m.get("negRisk")):
        return None, "neg_risk"
    try:
        labels = json.loads(m["outcomes"]) if isinstance(m.get("outcomes"), str) else list(m.get("outcomes") or [])
        toks = json.loads(m["clobTokenIds"]) if isinstance(m.get("clobTokenIds"), str) else list(m.get("clobTokenIds") or [])
    except (ValueError, KeyError):
        return None, "outcomes_malformed"
    if sorted(str(x) for x in labels) != sorted(OUTCOME_LABELS) or len(toks) != 2:
        return None, "outcomes"
    for reason, rx in OLD_VERSION_RES.items():
        if re.search(rx, desc):
            return None, reason
    missing = [k for k, rx in FLAG_RES.items() if not re.search(rx, desc)]
    if missing:
        return None, "flags:" + "+".join(missing)
    up_idx = [str(x) for x in labels].index("Up")
    k = c6.key_fields(m)
    ev = m.get("events") if isinstance(m.get("events"), list) else []
    return {"market_id": str(m.get("id")), "condition_id": str(m.get("conditionId") or ""), "token_up": str(toks[up_idx]), "token_down": str(toks[1 - up_idx]),
            "up_idx": up_idx, "ticker": mq.group(2), "day": day, "event_id": str(ev[0].get("id")) if ev and isinstance(ev[0], dict) and ev[0].get("id") is not None else "",
            "event_ids": k["event_ids"], "neg_risk_market_id": k["neg_risk_market_id"], "series_ids": k["series_ids"], "end_at": str(m.get("endDate") or ""),
            "question": q[:200], "desc_sha256": hashlib.sha256(desc.encode()).hexdigest(), "resolution_source": src[:200]}, "ok"


def gamma_end_window(day: str) -> tuple[str, str]:
    """endDate window ``[d 19:59Z, d 20:01Z]`` in EDT; the EST equivalent (an hour later) for Stage-2 sessions after 2026-11-01."""
    off = (datetime(*map(int, day.split("-")), 16, 0, tzinfo=ET).utcoffset() or timedelta(0)).total_seconds()
    hh = int(16 - off / 3600)
    return f"{day}T{hh - 1:02d}:59:00Z", f"{day}T{hh:02d}:01:00Z"


def frame_day(lim: hb.Limiter, day: str) -> tuple[list[dict], list[dict], dict]:
    """Gamma closed markets with endDate in the day's window (paged); returns (frame rows, guarded outcome rows, reason counts)."""
    a, b = gamma_end_window(day)
    rows, capped = hb._paged(lim, {"closed": "true", "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true"}, error_is_capped=True)
    if capped:
        raise cm.ApiError(f"Gamma frame {day} capped or failed part-way")
    out, outc, why = [], [], {}
    for m in rows:
        if not isinstance(m, dict):
            continue
        r, reason = parse_market(m, day)
        why[reason] = why.get(reason, 0) + 1
        if r is None:
            continue
        out.append(r)
        outc.append({"market_id": r["market_id"], "day": day, "outcome_labels": str(m.get("outcomes") or ""), "outcome_prices": str(m.get("outcomePrices") or "")})
    return out, outc, why


# =====================================================================================================================================
# Yahoo fetch (injectable; <= 1 rps)
# =====================================================================================================================================


def yahoo_transport(timeout: float = 60.0):
    """A ``history_backfill`` transport with a browser-like user agent (Yahoo refuses empty agents). Keyless GET."""
    import httpx  # noqa: PLC0415

    client = httpx.Client(timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (arepo-research-lab/1)"})

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


def yahoo_chart(lim: hb.Limiter, symbol: str, interval: str, p1: float, p2: float) -> Any:
    st, doc = lim.get(YAHOO_CHART + symbol, {"interval": interval, "period1": int(p1), "period2": int(p2), "includePrePost": "false"})
    if st != 200:
        raise cm.ApiError(f"yahoo {symbol} {interval} status {st}")
    return doc


# =====================================================================================================================================
# Guarded files
# =====================================================================================================================================


def open_guarded(path: Path, job: str) -> list[dict]:
    """Guarded files (outcomes, settlement closes) are opened ONLY by the screen / rep jobs, after the freeze (the caller checked it)."""
    from . import cb7_common as c7  # noqa: PLC0415

    p = Path(path)
    if p.name not in GUARDED_FILES:
        raise Refused(f"{p.name} is not a guarded file")
    if job not in GUARDED_ALLOWED_JOBS:
        raise Refused(f"guarded file {p.name} may be opened only by {GUARDED_ALLOWED_JOBS}, not {job!r}")
    return list(c7.read_csv_gz(p))


def write_rows(fr: cm.Cb8Run, name: str, header: list[str], rows: Iterable[list]) -> Path:
    p = fr.rdir / name
    fr.budget.write_gz_csv(p, header, list(rows))
    fr.record_file(p)
    return p


# =====================================================================================================================================
# q0183: frame + Yahoo bars
# =====================================================================================================================================


def pyth_frame(root: Path, transport, *, rules_sha: str, smoke_path: Path, exclusion_keys_path: Path, now: float, yahoo_transport_=None,
               rps: float = 2.0, disk_cap: int = int(OUTPUT_CAP_FRAME_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None,
               should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
               data_dumps_cap_gb: float = c9.DATA_DUMPS_CAP_GB) -> dict:
    """q0183. Frame per P day (resumable by day), key drops (q0182 file; unverified disjointness -> P not testable, recorded), Yahoo hourly and daily
    bars per ticker 2026-02-01..08-10 (one request each at <= 1 rps), the pinned clock per session, the feature / guarded split."""
    from . import cb9_sign as sg  # noqa: PLC0415

    c9.require_after_t_seal(now, "pyth-frame")
    root = c9.refuse_path(Path(root))
    bad = [k for k in ("yahoo_clock", "gamma_paging") if not sg.smoke_criterion(smoke_path, k)]
    if bad:  # M5: terminal stall, exit 0, labelled
        return c9.write_stall(root / "pyth_frame", c9.STALL_NOT_RUN_SOURCE, f"smoke criteria {bad} failed")
    ids, keys, rep, keys_sha = c9.load_exclusion_keys(Path(exclusion_keys_path))
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    fr = cm.open_run(root, "pyth_frame", transport, allowed_run_id="pyth_frame", kind="cb9_pyth_frame", label="CB9 P frame",
                     params={"days": list(WINDOW), "gap": list(GAP), "exclusion_keys_sha256": keys_sha, "evidence_role": c9.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    if (fr.rdir / "frame.csv.gz").exists():
        m = fr.manifest(None, {"status": "pyth_frame_complete", "complete": True})
        m["status"] = "pyth_frame_complete"
        return m
    pf = fr.rdir / "frame_partial.jsonl"
    done = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["day"]] = rec
    for day in p_days():
        if day in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            m = fr.manifest(why, {"transient": True})
            m["status"] = "in_progress"
            return m
        try:
            rows, outc, reasons = frame_day(fr.lim, day)
        except (cm.ApiError, RuntimeError) as exc:
            m = fr.manifest(f"frame_day_failed {day}: {exc}"[:200], {"transient": True})
            m["status"] = "in_progress"
            return m
        rec = {"day": day, "rows": rows, "outcomes": outc, "reasons": reasons}
        with pf.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        done[day] = rec
    frame = [r for d in sorted(done) for r in done[d]["rows"]]
    outcomes = [o for d in sorted(done) for o in done[d]["outcomes"]]
    reasons: dict[str, int] = {}
    for d in done.values():
        for k, v in d["reasons"].items():
            reasons[k] = reasons.get(k, 0) + v
    kept, drops = c9.drop_by_keys(frame, ids, keys)
    tickers = sorted({r["ticker"] for r in kept})
    ylim = hb.Limiter(yahoo_transport_ or yahoo_transport(), rps=min(YAHOO_RPS, rps), sleep=sleep, live_check=live_check)
    p1, p2 = et_epoch(BARS_FROM, 0, 0), et_epoch(WINDOW[1], 23, 59)
    bars_rows, settle_rows, strike_rows, avail = [], [], [], {}
    sessions = full_sessions(BARS_FROM, WINDOW[1])
    for tk in tickers:
        try:
            hdoc = yahoo_chart(ylim, tk, "1h", p1, p2)
            ddoc = yahoo_chart(ylim, tk, "1d", p1, p2)
        except (cm.ApiError, RuntimeError):
            avail[tk] = {"status": "yahoo_failed"}
            continue
        rows = parse_chart(hdoc)
        daily = daily_rows(ddoc)
        n_unavail = 0
        for s in sessions:
            bars, info = session_bars(rows, s)
            if bars is None:
                n_unavail += 1
                continue
            for b in bars[:-1]:  # the 15:30-16:00 bar's close is the settlement close: guarded
                bars_rows.append([tk, s, int(b["o"]), int(b["e"]), b["open"], b["close"]])
            settle_rows.append([tk, s, "last_bar", int(bars[-1]["o"]), bars[-1]["close"]])
        for i, s in enumerate(sessions):
            if s in daily:
                settle_rows.append([tk, s, "daily_close", "", daily[s]["close"]])
            if i and sessions[i - 1] in daily:
                strike_rows.append([tk, s, daily[sessions[i - 1]]["close"], sessions[i - 1]])
        missing_p = [s for s in p_days() if not any(r[0] == tk and r[1] == s for r in bars_rows)]
        avail[tk] = {"status": "ok" if not missing_p else "ticker_unavailable", "sessions_bars_unavailable": n_unavail, "window_sessions_missing": len(missing_p)}
    write_rows(fr, "frame_all.csv.gz", FRAME_COLUMNS, [[r[c] for c in FRAME_COLUMNS] for r in frame])
    write_rows(fr, "frame.csv.gz", FRAME_COLUMNS + ["ticker_status"], [[r[c] for c in FRAME_COLUMNS] + [avail.get(r["ticker"], {}).get("status", "")] for r in kept])
    write_rows(fr, "outcomes_guarded.csv.gz", OUTCOME_COLUMNS, [[o[c] for c in OUTCOME_COLUMNS] for o in outcomes])
    write_rows(fr, "bars_pre.csv.gz", BAR_COLUMNS, bars_rows)
    write_rows(fr, "strikes.csv.gz", STRIKE_COLUMNS, strike_rows)
    write_rows(fr, "closes_settle_guarded.csv.gz", SETTLE_COLUMNS, settle_rows)
    fr.counts.update({"frame": len(frame), "kept": len(kept), "tickers": len(tickers), "yahoo_requests": ylim.requests})
    status = "pyth_frame_complete" if rep.get("disjointness") != c9.UNVERIFIED else c9.STALL_DISJOINTNESS
    extra = {"label": c9.STALL_LABELS[c9.STALL_DISJOINTNESS], "terminal": True} if status == c9.STALL_DISJOINTNESS else {}
    m = fr.manifest(None, {"status": status, "complete": True, "reasons": reasons, "drops": drops, "tickers": avail, **extra})
    m["status"] = status
    return m


# =====================================================================================================================================
# q0184: pmxt states and quote-window prints
# =====================================================================================================================================


def levels_at(events: list[dict], t_ms: int) -> tuple[dict[float, float], dict[float, float], bool]:
    """(bids, asks, has_book) at ``t_ms`` from events with BOTH clocks <= t (last ``book`` snapshot, then ``price_change`` levels)."""
    from . import cb8_books as bk  # noqa: PLC0415

    elig = [e for e in events if e["v"] <= t_ms and e["r"] <= t_ms]
    bi = max((i for i, e in enumerate(elig) if e["et"] == "book"), default=None)
    if bi is None:
        return {}, {}, False
    bids, asks = bk._levels(elig[bi]["bids"]), bk._levels(elig[bi]["asks"])
    for e in elig[bi + 1:]:
        if e["et"] == "price_change" and e["price"] is not None:
            side = bids if str(e["side"]).upper() == "BUY" else asks
            p, s = float(e["price"]), float(e["size"])
            if s <= 0:
                side.pop(p, None)
            else:
                side[p] = s
    return {p: s for p, s in bids.items() if s > 0}, {p: s for p, s in asks.items() if s > 0}, True


def state_row(market: dict, day: str, ck: int, lag: int, t: float, token: str, events: list[dict], window_end: float) -> list:
    from . import cb8_books as bk  # noqa: PLC0415

    t_ms = int(t * 1000)
    st = bk.state_at(events, t_ms, t_ms)
    bids, asks, _ = levels_at(events, t_ms)
    bb = max(bids) if bids else None
    n_win = sum(1 for e in events if t_ms < e["v"] <= int(window_end * 1000))
    return [market["market_id"], day, ck, lag, t, token, int(st["fresh"]), int(st["crossed"]), st["book_status"], st["best_bid"], st["best_ask"], st["ask_size"],
            bids.get(bb) if bb is not None else None, st["fee_bps"], st["tick"], json.dumps(sorted(bids.items(), reverse=True)[:10]),
            json.dumps(sorted(asks.items())[:10]), n_win]


def pyth_books(root: Path, transport, *, rules_sha: str, smoke_path: Path, frame_dir: Path, fetch, size_fn, now: float, ingress_cap_gb: float = INGRESS_CAP_GB,
               rps: float = 2.0, disk_cap: int = int(OUTPUT_CAP_BOOKS_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None,
               should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
               data_dumps_cap_gb: float = c9.DATA_DUMPS_CAP_GB) -> dict:
    """q0184. Per P day (resumable): pmxt hours 14Z, 16Z, 19Z for the day's frame tokens (row-group streaming; the previous hour only for tokens without
    a ``book`` snapshot by the checkpoint), states of both tokens at ``e + 120 s`` and ``e + 300 s``, event counts in the quote windows (coverage audit),
    Data API prints in ``[e + 120, e + 600]`` (no wallet stored). Ingress metered against the 40 GB cap (``ingress_cap_reached`` ends the job)."""
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import cb9_sign as sg  # noqa: PLC0415

    c9.require_after_t_seal(now, "pyth-books")
    root = c9.refuse_path(Path(root))
    if not sg.smoke_criterion(smoke_path, "pmxt_heads"):  # M5
        return c9.write_stall(root / "pyth", c9.STALL_NOT_RUN_SOURCE, "smoke criterion pmxt_heads failed")
    fman = json.loads((Path(frame_dir) / "manifest.json").read_text())
    if fman.get("status") in c9.STALL_STATUSES:  # M5: the upstream label is carried, terminal, exit 0
        return c9.write_stall(root / "pyth", c9.STALL_UPSTREAM, f"pyth_frame ended {fman.get('status')}", label=fman.get("label") or c9.STALL_LABELS.get(fman.get("status")))
    if fman.get("status") != "pyth_frame_complete":
        raise NotNow(f"P frame status {fman.get('status')}: not finished yet")
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    cm.verify_manifest_files(Path(frame_dir), fman)
    frame = [r for r in c7.read_csv_gz(Path(frame_dir) / "frame.csv.gz") if r.get("ticker_status") == "ok"]
    fr = cm.open_run(root, "pyth", transport, allowed_run_id="pyth", kind="cb9_pyth_books", label="CB9 P books",
                     params={"hours_z": list(PMXT_HOURS_Z), "lags_s": [USABLE_LAG_S, LATENCY_LAG_S], "print_window_s": list(PRINT_WINDOW_S),
                             "ingress_cap_gb": ingress_cap_gb, "frame_manifest_sha256": cm.sha_obj(fman.get("file_sha256")), "evidence_role": c9.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    if (fr.rdir / "states.csv.gz").exists():
        m = fr.manifest(None, {"status": "pyth_books_complete", "complete": True})
        m["status"] = "pyth_books_complete"
        return m
    by_day: dict[str, list[dict]] = {}
    for r in frame:
        by_day.setdefault(r["day"], []).append(r)
    pf = fr.rdir / "days.jsonl"
    done = {json.loads(x)["day"] for x in pf.read_text().splitlines() if x.strip()} if pf.exists() else set()
    cap = int(ingress_cap_gb * 1024**3)
    status = None
    for day in sorted(by_day):
        if day in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            m = fr.manifest(why, {"transient": True})
            m["status"] = "in_progress"
            return m
        if bk.ingress_used(fr.rdir) >= cap:
            status = "ingress_cap_reached"
            break
        mk = by_day[day]
        tokens = {r[f"token_{s}"]: r["condition_id"] for r in mk for s in ("up", "down")}
        srows, prow, info = [], [], {"day": day, "hours": {}}
        for ci, hz in enumerate(PMXT_HOURS_Z):
            ck = checkpoints(day)[ci]
            cut = ck[1] + PRINT_WINDOW_S[1]
            hour = datetime.fromisoformat(f"{day}T{hz:02d}:00:00+00:00")
            try:
                ev, hinfo = bk.read_hour_events(hour, tokens, fetch=fetch, size_fn=size_fn, cut_ms=int(cut * 1000),
                                                meter=lambda n, d=day, h=hz: bk.ingress_add(fr.rdir, n, f"{d}T{h}"))
                need = {t: c for t, c in tokens.items() if not any(e["et"] == "book" and e["v"] <= int(ck[2] * 1000) for e in ev[t])}
                if need:
                    try:
                        ev0, _ = bk.read_hour_events(hour - timedelta(hours=1), need, fetch=fetch, size_fn=size_fn, cut_ms=int(cut * 1000),
                                                     meter=lambda n, d=day, h=hz: bk.ingress_add(fr.rdir, n, f"{d}T{h - 1}"))
                        for t in need:
                            ev[t] = sorted(ev0.get(t, []) + ev[t], key=lambda e: (e["v"], e["r"]))
                    except (bk.HourMissing, bk.HourCorrupt):
                        info["hours"][f"{hz - 1}_lookback"] = "unavailable"
                info["hours"][str(hz)] = "ok"
            except (bk.HourMissing, bk.HourCorrupt) as exc:
                info["hours"][str(hz)] = f"unavailable:{type(exc).__name__}"
                continue
            for r in mk:
                for lag in (USABLE_LAG_S, LATENCY_LAG_S):
                    t = ck[1] + lag
                    for side in ("up", "down"):
                        srows.append(state_row(r, day, ci, lag, t, side, ev[r[f"token_{side}"]], t + QUOTE_LIFE_S))
                try:
                    got = cm.windowed_prints(fr.lim, r["condition_id"], int(ck[1] + PRINT_WINDOW_S[0]), int(ck[1] + PRINT_WINDOW_S[1]), PRINT_PAGES, b"cb9-no-wallets")[0]
                except cm.ApiError:
                    got = None
                except RuntimeError:
                    m = fr.manifest("network", {"transient": True})
                    m["status"] = "in_progress"
                    return m
                if got is None:
                    info.setdefault("prints_failed", []).append(f"{r['market_id']}:{ci}")
                    continue
                prow += [[r["market_id"], day, ci, p["ts"], p["idx"], "BUY" if p["side"] == 1 else "SELL", p["price"], p["size"]] for p in got]
        fr.budget.write_append(fr.rdir / "states_partial.jsonl", "".join(json.dumps(x, default=float) + "\n" for x in srows))
        fr.budget.write_append(fr.rdir / "prints_partial.jsonl", "".join(json.dumps(x, default=float) + "\n" for x in prow))
        with pf.open("a") as fh:
            fh.write(json.dumps(info, sort_keys=True) + "\n")
        done.add(day)
    srows = [json.loads(x) for x in (fr.rdir / "states_partial.jsonl").read_text().splitlines()] if (fr.rdir / "states_partial.jsonl").exists() else []
    prow = [json.loads(x) for x in (fr.rdir / "prints_partial.jsonl").read_text().splitlines()] if (fr.rdir / "prints_partial.jsonl").exists() else []
    write_rows(fr, "states.csv.gz", STATE_COLUMNS, srows)
    write_rows(fr, "prints.csv.gz", PRINT_COLUMNS, prow)
    status = status or "pyth_books_complete"
    fr.counts.update({"days_done": len(done), "days_total": len(by_day), "state_rows": len(srows), "print_rows": len(prow), "ingress_bytes": bk.ingress_used(fr.rdir)})
    m = fr.manifest(None, {"status": status, "complete": True})
    m["status"] = status
    return m


# =====================================================================================================================================
# Units from the stored files (census: features only; screen: + guarded outcomes)
# =====================================================================================================================================


def load_bars(path: Path) -> dict[tuple[str, str], list[dict]]:
    from . import cb7_common as c7  # noqa: PLC0415

    out: dict[tuple[str, str], list[dict]] = {}
    for r in c7.read_csv_gz(Path(path)):
        out.setdefault((r["ticker"], r["day"]), []).append({"o": float(r["o"]), "e": float(r["e"]), "open": float(r["open"]), "close": float(r["close"])})
    for v in out.values():
        v.sort(key=lambda b: b["o"])
    return out


def build_units(frame: list[dict], bars_pre: dict[tuple[str, str], list[dict]], strikes: dict[tuple[str, str], float], states: list[dict],
                prints: list[dict], *, lag_s: int = USABLE_LAG_S, stale: bool = False) -> list[dict]:
    """One record per (market-day, checkpoint) of the frame: features (S_t, K_d, sigma, tau, fair_up; S from the stale bar if ``stale``), both tokens'
    states at ``e + lag``, the P1 trade (or None), the P2 quotes and their fills (no outcome), the availability label. Uses only feature files.
    ``bars_pre`` holds bars 09:30..14:30 (the guarded 15:30 bar never enters a feature)."""
    sessions = full_sessions(BARS_FROM, WINDOW[1])
    by_tk: dict[str, dict[str, list[dict]]] = {}
    for (tk, d), bars in bars_pre.items():
        by_tk.setdefault(tk, {})[d] = bars
    seq_tk = {tk: sorted((b for v in dd.values() for b in v), key=lambda b: b["e"]) for tk, dd in by_tk.items()}
    st_idx: dict[tuple, dict] = {(s["market_id"], s["day"], int(s["ckpt"]), int(s["lag_s"]), s["token"]): s for s in states}
    pr_idx: dict[tuple, list[dict]] = {}
    for p in prints:
        pr_idx.setdefault((p["market_id"], p["day"], int(p["ckpt"])), []).append(p)
    sig_cache: dict[tuple[str, str], float | None] = {}
    out = []
    for r in frame:
        tk, day = r["ticker"], r["day"]
        bars = bars_pre.get((tk, day)) or []
        if (tk, day) not in sig_cache:
            sig_cache[(tk, day)] = sigma_for(day, by_tk.get(tk, {}), sessions)
        sig = sig_cache[(tk, day)]
        k_d = strikes.get((tk, day))
        for ci, e, t in checkpoints(day, lag_s):
            u = {"market_id": r["market_id"], "ticker": tk, "day": day, "month": day[:7], "ckpt": ci, "t": t, "e": e, "up_idx": int(r["up_idx"])}
            b = latest_usable(bars, t)
            if stale and b is not None:
                seq = seq_tk.get(tk, [])
                j = [i for i, x in enumerate(seq) if x["e"] == b["e"]]
                b = seq[j[0] - 1] if j and j[0] > 0 else None
            books = {s: st_idx.get((r["market_id"], day, ci, lag_s, s)) for s in ("up", "down")}
            books = {s: _state_dict(v) for s, v in books.items() if v is not None}
            fv = fair_up(b["close"], k_d, sig, tau_hours(day, t)) if (b is not None and k_d and sig) else None
            u.update(s_t=b["close"] if b else None, k_d=k_d, sigma=sig, fair_up=fv)
            avail = fv is not None and any(v.get("fresh") and not v.get("crossed") for v in books.values())
            if not books:
                u["label"] = "source unavailable"
            elif fv is None:
                u["label"] = "features unavailable"
            elif not avail:
                u["label"] = "no fresh book"
            else:
                u["label"] = "ok"
            u["trade"] = p1_unit(fv, books) if u["label"] == "ok" else None
            u["trade_cost"] = p1_unit(fv, books, cost_add=COST_ROBUST) if u["trade"] else None
            upb = books.get("up") or {}
            u["n_prints_window"] = sum(1 for p in pr_idx.get((r["market_id"], day, ci), []) if t < float(p["ts"]) <= t + QUOTE_LIFE_S)
            u["pmxt_events_window"] = int(upb.get("n_events_window") or 0) + int((books.get("down") or {}).get("n_events_window") or 0)
            if u["label"] == "ok" and upb.get("fresh") and not upb.get("crossed") and upb.get("best_bid") is not None and upb.get("best_ask") is not None:
                tick = float(upb.get("tick") or DEFAULT_TICK)
                q = p2_quotes(fv, upb["best_bid"], upb["best_ask"], tick)
                pr = up_prints(pr_idx.get((r["market_id"], day, ci), []), int(r["up_idx"]))
                fills = {}
                for name in ("model", "mid"):
                    bid, ask = q[name]
                    for rule in ("queue", "through"):
                        fills[f"{name}_{rule}"] = quote_pair_pnl(pr, t, bid, ask, depth_at(upb["bids"], bid), depth_at(upb["asks"], ask), None, rule=rule)
                u["p2"] = {"quotes": q, "fills": fills}
            else:
                u["p2"] = None
            out.append(u)
    return out


def _state_dict(s: dict) -> dict:
    def f(k: str):
        v = s.get(k)
        return None if v in (None, "", "None") else float(v)

    return {"fresh": str(s.get("fresh")) in ("1", "True"), "crossed": str(s.get("crossed")) in ("1", "True"), "best_bid": f("best_bid"), "best_ask": f("best_ask"),
            "ask_size": f("ask_size"), "fee_bps": f("fee_bps"), "tick": f("tick"), "n_events_window": int(float(s.get("n_events_window") or 0)),
            "bids": {float(p): float(z) for p, z in json.loads(s.get("bids_top") or "[]")}, "asks": {float(p): float(z) for p, z in json.loads(s.get("asks_top") or "[]")}}


def census_p(units: list[dict], frame_info: dict) -> dict:
    """P census, counts only (no outcome, no net, no contrast): units by label, traded units (edge >= 5c, feature-only), sessions and tickers with
    traded units, P2 quote-origins and fills by quote type, the coverage audit (units with >= 1 print in the quote window: share with any pmxt event in
    the same span; PASS >= 90%), gate GP and the label rule."""
    for u in units:
        if any(k in u for k in ("y", "net", "pnl", "outcome")):
            raise Refused("census received an outcome field")
    traded = [u for u in units if u.get("trade")]
    p2 = [u for u in units if u.get("p2")]
    fills_model = sum(int(u["p2"]["fills"]["model_queue"]["bid_filled"]) + int(u["p2"]["fills"]["model_queue"]["ask_filled"]) for u in p2)
    fills_mid = sum(int(u["p2"]["fills"]["mid_queue"]["bid_filled"]) + int(u["p2"]["fills"]["mid_queue"]["ask_filled"]) for u in p2)
    aud = [u for u in units if u["n_prints_window"] >= 1]
    aud_ok = sum(1 for u in aud if u["pmxt_events_window"] >= 1)
    audit_share = aud_ok / len(aud) if aud else 0.0
    labels: dict[str, int] = {}
    for u in units:
        labels[u["label"]] = labels.get(u["label"], 0) + 1
    avail_share = (len(units) - labels.get("source unavailable", 0)) / len(units) if units else 0.0
    gp = {"p1_units": len(traded), "sessions": len({u["day"] for u in traded}), "tickers": len({u["ticker"] for u in traded}), "p2_origins": len(p2),
          "p2_fills_model": fills_model, "p2_fills_mid": fills_mid}
    gp_ok = (gp["p1_units"] >= GP["min_p1_units"] and gp["sessions"] >= GP["min_sessions"] and gp["tickers"] >= GP["min_tickers"])
    gp2_ok = gp["p2_origins"] >= GP["min_p2_origins"] and fills_model >= GP["min_p2_fills_each_quote"] and fills_mid >= GP["min_p2_fills_each_quote"]
    audit_pass = bool(aud) and audit_share >= AUDIT_PASS
    lab = lambda ok: "ok" if ok else ("no opportunity (no mispricing at the hourly scale)" if audit_pass and avail_share >= AVAILABLE_MIN else "not testable (source unavailable)")  # noqa: E731
    return {"frame": frame_info, "units": len(units), "labels": labels, "gate_GP": gp, "gate_GP_P1": gp_ok, "gate_GP_P2": gp2_ok,
            "coverage_audit": {"n_units_with_print": len(aud), "n_with_pmxt_event": aud_ok, "share": audit_share, "pass": audit_pass},
            "source_available_share": avail_share, "label_P1": lab(gp_ok) if audit_pass else "not testable (source unavailable)",
            "label_P2": lab(gp2_ok) if audit_pass else "not testable (source unavailable)",
            "p2_fill_rate_model": fills_model / (2 * len(p2)) if p2 else 0.0, "p2_fill_rate_mid": fills_mid / (2 * len(p2)) if p2 else 0.0}


# =====================================================================================================================================
# Screen (q0191) and rep (q0196): statistics with placebos and binding robustness
# =====================================================================================================================================


def _cl(units: list[dict]) -> dict[str, np.ndarray]:
    return {"day": np.array([u["day"] for u in units]), "ticker": np.array([u["ticker"] for u in units])}


def _months_ok(v: np.ndarray, months: np.ndarray, sign: float) -> dict:
    res = {}
    for mth in sorted(set(months.tolist())):
        sel = months == mth
        if sel.sum() >= MONTH_MIN_UNITS:
            res[mth] = float(v[sel].mean())
    agree = sum(1 for x in res.values() if np.sign(x) == np.sign(sign))
    return {"months": res, "holds": bool(res) and agree >= MONTH_SHARE * len(res)}


def _drop_ok(v: np.ndarray, cl: dict[str, np.ndarray], floor: float, gate_p: float = c9.GATE_P) -> dict:
    out = {}
    for way, c in cl.items():
        keep = c9.top_k_drop_mask(v, c)
        r = c9.cluster_p(v[keep], {k: x[keep] for k, x in cl.items()})
        out[way] = {"p": r["p"], "mean": r["mean"], "holds": bool(r["p"] < gate_p and r["mean"] >= floor)}
    return {"ways": out, "holds": all(x["holds"] for x in out.values())}


def p1_stat(units: list[dict], y_of: Callable[[dict, str], float | None], *, stale_units: list[dict] | None = None, latency_units: list[dict] | None = None,
            n_draws: int = c9.PLACEBO_DRAWS, gate_p: float = c9.GATE_P) -> dict:
    """P1: mean net per share (cents) over traded checkpoints; p = max over the day and ticker ways; floor +1.0c; break-even calibration placebo
    (``Y' = 1{U_d < a + f(a)}``, one uniform per session day, 200 draws, seed 9191); anchor attribution (P1 - P1_stale >= |P1|/2, credit only);
    binding robustness (i) +0.5c on a with net > 0, (ii) top-5 drops, (iii) size-weighted by ask depth capped at 2,000, (iv) month signs, (v) worst
    case for unavailable checkpoints, (vi) latency e + 300 s."""
    traded = [u for u in units if u.get("trade")]
    ys = [y_of(u, u["trade"]["token"]) for u in traded]
    keep = [i for i, y in enumerate(ys) if y is not None]
    tu = [traded[i] for i in keep]
    net = np.array([p1_net(traded[i]["trade"], ys[i]) for i in keep])
    cl = _cl(tu)
    base = c9.cluster_p(net, cl)
    mean = base["mean"] if len(net) else math.nan
    res: dict[str, Any] = {"n": len(net), "mean_cents": mean * 100 if math.isfinite(mean) else None, "p": base["p"], "testable": base["testable"], "ways": base.get("ways"),
                           "n_unresolved": len(traded) - len(keep)}
    if not base["testable"]:
        return {**res, "advance": False, "verdict": "not testable"}
    rng = np.random.default_rng(c9.PLACEBO_SEEDS["P1_breakeven"])
    days = sorted({u["day"] for u in tu})
    cost = np.array([u["trade"]["a"] + u["trade"]["fee"] for u in tu])
    dix = np.array([days.index(u["day"]) for u in tu])
    pl = []
    for _ in range(n_draws):
        ud = rng.random(len(days))
        yprime = (ud[dix] < cost).astype(float)
        pl.append(c9.cluster_p(yprime - cost, cl, alpha=gate_p)["p"])
    placebo = c9.placebo_advance_rate(pl, gate_p)
    cost_r = np.array([p1_net(u["trade_cost"], y) if u.get("trade_cost") else p1_net({**u["trade"], "a": u["trade"]["a"] + COST_ROBUST,
                                                                                        "fee": taker_fee(u["trade"]["a"] + COST_ROBUST, u["trade"]["rate"])}, y)
                       for u, y in zip(tu, [ys[i] for i in keep], strict=True)])
    rob_i = bool(cost_r.mean() > 0 and np.sign(cost_r.mean()) == np.sign(mean) and abs(cost_r.mean()) >= abs(mean) / 2)
    rob_ii = _drop_ok(net, cl, FLOOR_P1, gate_p)
    w = np.array([min(u["trade"]["ask_size"], SIZE_WEIGHT_CAP) for u in tu])
    wmean = float((net * w).sum() / w.sum()) if w.sum() > 0 else math.nan
    rob_iii = bool(np.sign(wmean) == np.sign(mean))
    rob_iv = _months_ok(net, np.array([u["month"] for u in tu]), mean)
    unav = [u for u in units if u["label"] != "ok"]
    worst_by_day: dict[str, float] = {}
    for u, x in zip(tu, net, strict=True):
        worst_by_day[u["day"]] = min(worst_by_day.get(u["day"], x), x)
    extra = [(u, worst_by_day[u["day"]]) for u in unav if u["day"] in worst_by_day]
    v5 = np.concatenate([net, np.array([x for _, x in extra])]) if extra else net
    cl5 = {k: np.concatenate([cl[k], np.array([u[k] for u, _ in extra])]) if extra else cl[k] for k in cl}
    r5 = c9.cluster_p(v5, cl5)
    rob_v = bool(np.sign(r5["mean"]) == np.sign(mean) and r5["p"] < gate_p)
    rob_vi = None
    if latency_units is not None:
        lt = [u for u in latency_units if u.get("trade") and y_of(u, u["trade"]["token"]) is not None]
        lnet = np.array([p1_net(u["trade"], y_of(u, u["trade"]["token"])) for u in lt])
        rob_vi = bool(len(lnet) and np.sign(lnet.mean()) == np.sign(mean) and abs(lnet.mean()) >= abs(mean) / 2)
    attribution = None
    if stale_units is not None:
        st = [u for u in stale_units if u.get("trade") and y_of(u, u["trade"]["token"]) is not None]
        snet = float(np.mean([p1_net(u["trade"], y_of(u, u["trade"]["token"])) for u in st])) if st else math.nan
        attribution = {"p1_stale_cents": snet * 100 if math.isfinite(snet) else None, "n_stale": len(st),
                       "credit_public_path_anchor": bool(math.isfinite(snet) and (mean - snet) >= abs(mean) / 2)}
    robust = rob_i and rob_ii["holds"] and rob_iii and rob_iv["holds"] and rob_v and (rob_vi is not False)
    adv = bool(base["p"] < gate_p and mean >= FLOOR_P1 and placebo["holds"] and robust)
    return {**res, "floor_cents": FLOOR_P1 * 100, "placebo_breakeven": placebo,
            "robustness": {"i_cost_plus_half_cent": rob_i, "i_mean_cents": float(cost_r.mean() * 100), "ii_top5": rob_ii, "iii_size_weighted_cents": wmean * 100,
                           "iii_holds": rob_iii, "iv_months": rob_iv, "v_worst_case": {"p": r5["p"], "mean_cents": r5["mean"] * 100, "holds": rob_v, "n_scored": len(extra)},
                           "vi_latency": rob_vi},
            "anchor_attribution": attribution, "advance": adv,
            "verdict": "advance" if adv else ("not detected at MDE" if base["p"] >= gate_p else "fails floor / placebo / robustness"),
            "label": None if not adv or (attribution or {}).get("credit_public_path_anchor") else "a favourite/longshot pattern the anchor's timing does not explain"}


def p2_stat(units: list[dict], y_of: Callable[[dict, str], float | None], *, latency_units: list[dict] | None = None, n_draws: int = c9.PLACEBO_DRAWS,
            gate_p: float = c9.GATE_P) -> dict:
    """P2: per quote-origin (model P&L - mid P&L) / 40 posted shares, cents; floor +0.3c; route gate model net per posted share > 0; kill if either quote's
    fill rate < 2% of origins; label-swap placebo (one draw per session day, seed 9192); binding robustness (trade-through fills, top-5 drops,
    filled-share weighting, months, worst case, latency). The latency-tail check is 'not measurable' (no minute path; labelled)."""
    orig = [u for u in units if u.get("p2")]
    rows = []
    for u in orig:
        y = y_of(u, "up")
        if y is None:
            continue
        q = u["p2"]["quotes"]
        pr = {}
        for name in ("model", "mid"):
            for rule in ("queue", "through"):
                f = u["p2"]["fills"][f"{name}_{rule}"]
                bid, ask = q[name]
                pnl = (QUOTE_SIZE * (y - bid) if f["bid_filled"] else 0.0) + (QUOTE_SIZE * (ask - y) if f["ask_filled"] else 0.0)
                reb = REBATE_SHARE * FEE_RATE_FLOOR * ((QUOTE_SIZE * bid * (1 - bid)) if f["bid_filled"] else 0.0) + REBATE_SHARE * FEE_RATE_FLOOR * ((QUOTE_SIZE * ask * (1 - ask)) if f["ask_filled"] else 0.0)
                pr[f"{name}_{rule}"] = (pnl, pnl + reb, f["filled_shares"])
        rows.append((u, pr))
    if not rows:
        return {"n": 0, "testable": False, "p": 1.0, "advance": False, "verdict": "not testable"}
    us = [u for u, _ in rows]
    contrast = np.array([(pr["model_queue"][0] - pr["mid_queue"][0]) / (2 * QUOTE_SIZE) for _, pr in rows])
    model_net = np.array([pr["model_queue"][0] / (2 * QUOTE_SIZE) for _, pr in rows])
    cl = _cl(us)
    base = c9.cluster_p(contrast, cl)
    mean = base["mean"]
    fr_model = float(np.mean([pr["model_queue"][2] > 0 for _, pr in rows]))
    fr_mid = float(np.mean([pr["mid_queue"][2] > 0 for _, pr in rows]))
    kill_fill = fr_model < P2_MIN_FILL_RATE or fr_mid < P2_MIN_FILL_RATE
    route = bool(model_net.mean() > 0)
    rng = np.random.default_rng(c9.PLACEBO_SEEDS["P2_label_swap"])
    days = sorted({u["day"] for u in us})
    dix = np.array([days.index(u["day"]) for u in us])
    pl = []
    for _ in range(n_draws):
        sgn = np.where(rng.random(len(days)) < 0.5, -1.0, 1.0)
        pl.append(c9.cluster_p(contrast * sgn[dix], cl, alpha=gate_p)["p"])
    placebo = c9.placebo_advance_rate(pl, gate_p)
    thr = np.array([(pr["model_through"][0] - pr["mid_through"][0]) / (2 * QUOTE_SIZE) for _, pr in rows])
    rob_i = bool(np.sign(thr.mean()) == np.sign(mean) and abs(thr.mean()) >= abs(mean) / 2)
    rob_ii = _drop_ok(contrast, cl, FLOOR_P2, gate_p)
    w = np.array([pr["model_queue"][2] + pr["mid_queue"][2] for _, pr in rows], float)
    wmean = float((contrast * w).sum() / w.sum()) if w.sum() > 0 else math.nan
    rob_iii = bool(np.sign(wmean) == np.sign(mean))
    rob_iv = _months_ok(contrast, np.array([u["month"] for u in us]), mean)
    worst: dict[str, float] = {}
    for u, x in zip(us, contrast, strict=True):
        worst[u["day"]] = min(worst.get(u["day"], x), x)
    unav = [u for u in units if u["label"] != "ok" and u["day"] in worst]
    v5 = np.concatenate([contrast, np.array([worst[u["day"]] for u in unav])]) if unav else contrast
    cl5 = {k: np.concatenate([cl[k], np.array([u[k] for u in unav])]) if unav else cl[k] for k in cl}
    r5 = c9.cluster_p(v5, cl5)
    rob_v = bool(np.sign(r5["mean"]) == np.sign(mean) and r5["p"] < gate_p)
    rob_vi = None
    if latency_units is not None:
        lt = [u for u in latency_units if u.get("p2") and y_of(u, "up") is not None]
        lc = []
        for u in lt:
            y = y_of(u, "up")
            q = u["p2"]["quotes"]
            vals = []
            for name in ("model", "mid"):
                f = u["p2"]["fills"][f"{name}_queue"]
                bid, ask = q[name]
                vals.append((QUOTE_SIZE * (y - bid) if f["bid_filled"] else 0.0) + (QUOTE_SIZE * (ask - y) if f["ask_filled"] else 0.0))
            lc.append((vals[0] - vals[1]) / (2 * QUOTE_SIZE))
        rob_vi = bool(lc and np.sign(np.mean(lc)) == np.sign(mean) and abs(np.mean(lc)) >= abs(mean) / 2)
    robust = rob_i and rob_ii["holds"] and rob_iii and rob_iv["holds"] and rob_v and (rob_vi is not False)
    adv = bool(base["testable"] and base["p"] < gate_p and mean >= FLOOR_P2 and route and not kill_fill and placebo["holds"] and robust)
    reb = np.array([(pr["model_queue"][1] - pr["mid_queue"][1]) / (2 * QUOTE_SIZE) for _, pr in rows])
    return {"n": len(rows), "mean_cents": mean * 100, "p": base["p"] if base["testable"] else 1.0, "testable": base["testable"], "ways": base.get("ways"),
            "floor_cents": FLOOR_P2 * 100, "route_gate": {"model_net_per_posted_share_cents": float(model_net.mean() * 100), "holds": route},
            "fill_rates": {"model": fr_model, "mid": fr_mid, "kill": kill_fill}, "placebo_label_swap": placebo,
            "robustness": {"i_trade_through_cents": float(thr.mean() * 100), "i_holds": rob_i, "ii_top5": rob_ii, "iii_filled_share_weighted_cents": wmean * 100,
                           "iii_holds": rob_iii, "iv_months": rob_iv, "v_worst_case": {"p": r5["p"], "mean_cents": r5["mean"] * 100, "holds": rob_v}, "vi_latency": rob_vi},
            "rebate_version_cents": float(reb.mean() * 100), "latency_tail": "latency tail not measurable (no minute path)", "advance": adv,
            "verdict": "advance" if adv else ("mid quoting loses less, no route" if not route else ("fill rate < 2%" if kill_fill else "not detected at MDE / fails gates"))}


def source_check(frame: list[dict], strikes: dict[tuple[str, str], float], settle: list[dict], outcomes: dict[str, dict]) -> dict:
    """Yahoo-implied direction (``close_d`` vs ``K_d``, guarded) vs the Gamma outcome on market-days with |return| > 0.1%: disagreement > 2% -> P
    'not testable (source)'. Disagreeing units stay in the P&L with the Gamma outcome. Screen / rep only (reads guarded rows)."""
    close = {(r["ticker"], r["day"]): float(r["close"]) for r in settle if r["kind"] == "daily_close"}
    n = dis = 0
    for r in frame:
        k = strikes.get((r["ticker"], r["day"]))
        c = close.get((r["ticker"], r["day"]))
        o = outcomes.get(r["market_id"])
        if not (k and c and o):
            continue
        if abs(c / k - 1.0) <= SOURCE_MIN_ABS_RET:
            continue
        y_up = outcome_y(json.loads(o["outcome_labels"]), json.loads(o["outcome_prices"]), "up")
        if y_up is None:
            continue
        n += 1
        dis += int((c > k) != (y_up == 1.0))
    share = dis / n if n else 1.0
    return {"n": n, "n_disagree": dis, "share": share, "pass": bool(n and share <= SOURCE_DISAGREE_MAX)}


# =====================================================================================================================================
# Stage 2 (q0195): receipt-timed collection rules and the Yahoo partial-failure rule
# =====================================================================================================================================


def live_s_t(bars_doc: Any, day: str, receipt_t: float) -> float | None:
    """Stage-2 anchor: the latest bar of the checkpoint-time Yahoo response that is usable at its RECEIPT time (pinned clock); None -> the
    checkpoint is 'unavailable (source)' (no substitute source). Post-session bars are never passed here (diagnostic only)."""
    rows = parse_chart(bars_doc)
    t_open = et_epoch(day, *OPEN_ET)
    t_close = et_epoch(day, *close_et(day))
    bars = []
    for r in rows:
        o = float(r["o"])
        if et_day(o) != day or o < t_open or o >= t_close or not math.isfinite(r["close"]):
            continue
        bars.append({"o": o, "e": min(o + BAR_S, t_close), "open": r["open"], "close": r["close"]})
    b = latest_usable(bars, receipt_t)
    return b["close"] if b else None


def stage2_sessions(start_day: str, n: int = STAGE2_SESSIONS) -> list[str]:
    """``T9_P2_start`` + the next full sessions (half sessions and holidays skipped), n in total."""
    out, d = [], _d(start_day)
    while len(out) < n:
        if is_full_session(d.isoformat()):
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def t9_p2_start(freeze_commit_epoch: float) -> str:
    """The first full NYSE session >= the CB9 freeze commit + 1 day."""
    d = (datetime.fromtimestamp(freeze_commit_epoch, UTC) + timedelta(days=1)).date()
    while not is_full_session(d.isoformat()):
        d += timedelta(days=1)
    return d.isoformat()


def stage2_availability(ckpt_status: dict[tuple[str, int], str], sessions: list[str]) -> dict:
    """Yahoo partial-failure rule: a checkpoint is 'unavailable (source)' when its Yahoo fetch failed or returned no usable bar (no substitute); a session
    whose sigma / K_d fetch failed has all three checkpoints unavailable; unavailable sessions COUNT toward the 30 (never replaced, never extended);
    more than 20% unavailable checkpoints -> P-rep 'not testable (source unavailable)', counted."""
    total = len(sessions) * len(CHECKPOINT_BARS_ET)
    unav = sum(1 for s in sessions for i in range(len(CHECKPOINT_BARS_ET)) if ckpt_status.get((s, i), "unavailable (source)") != "ok")
    share = unav / total if total else 1.0
    return {"sessions": len(sessions), "checkpoints": total, "unavailable": unav, "share": share,
            "testable": share <= STAGE2_UNAVAILABLE_MAX, "label": "ok" if share <= STAGE2_UNAVAILABLE_MAX else "not testable (source unavailable)"}


def checkpoint_status(yahoo_ok: bool, s_t: float | None, session_inputs_ok: bool) -> str:
    if not session_inputs_ok:
        return "unavailable (source): sigma/K_d fetch failed"
    if not yahoo_ok or s_t is None:
        return "unavailable (source)"
    return "ok"


def clob_book_state(doc: Any) -> dict | None:
    """Best bid / ask, sizes and levels of a CLOB ``/book`` reply (receipt clock only)."""
    if not isinstance(doc, dict):
        return None
    def lv(key: str) -> dict[float, float]:
        out = {}
        for x in doc.get(key) or []:
            try:
                out[float(x["price"])] = float(x["size"])
            except (KeyError, TypeError, ValueError):
                continue
        return {p: s for p, s in out.items() if s > 0}

    bids, asks = lv("bids"), lv("asks")
    bb, ba = (max(bids) if bids else None), (min(asks) if asks else None)
    return {"best_bid": bb, "best_ask": ba, "ask_size": asks.get(ba) if ba is not None else None, "bid_size": bids.get(bb) if bb is not None else None,
            "fresh": True, "crossed": bool(bb is not None and ba is not None and bb >= ba), "tick": float(doc.get("tick_size") or DEFAULT_TICK),
            "fee_bps": None, "bids": bids, "asks": asks, "n_events_window": 0}


OUTCOME_DUE_S = 6 * 3600  # first post-settlement outcome fetch: session close + 6 h
OUTCOME_MAX_DAYS = 7  # markets still unresolved this long after the close are recorded as unresolved (counted), never guessed


def fetch_outcomes(sdir: Path, day: str, now: float, markets: list[dict], outcome_get: Callable[[list[str]], list[dict]]) -> dict:
    """M9: guarded post-settlement outcome fetch for one Stage-2 session (Gamma by id, ``closed=true``). Resolved markets (Up/Down price 1/0 or
    0.5/0.5) go ONLY to ``<session>/outcomes_guarded.csv.gz`` (rewritten whole, ids accumulate); the step is final when every market is resolved or
    ``OUTCOME_MAX_DAYS`` passed (the rest unresolved, counted). Nothing else of the reply is kept."""
    from . import cb7_common as c7  # noqa: PLC0415

    gp = Path(sdir) / "outcomes_guarded.csv.gz"
    have = {r["market_id"]: r for r in c7.read_csv_gz(gp)} if gp.exists() else {}
    todo = [m["market_id"] for m in markets if m["market_id"] not in have]
    for i in range(0, len(todo), 50):
        for g in outcome_get(todo[i:i + 50]) or []:
            if not isinstance(g, dict) or str(g.get("id")) not in todo or not g.get("closed"):
                continue
            try:
                labels, prices = json.loads(g.get("outcomes") or "[]"), json.loads(g.get("outcomePrices") or "[]")
            except (TypeError, ValueError):
                continue
            if outcome_y(labels, prices, "up") is None:
                continue
            have[str(g["id"])] = {"market_id": str(g["id"]), "day": day, "outcome_labels": json.dumps(labels), "outcome_prices": json.dumps(prices)}
    if have:
        tmp = gp.with_name(gp.name + ".tmp")
        tmp.write_bytes(hb._gz_csv_bytes(OUTCOME_COLUMNS, [[have[k][c] for c in OUTCOME_COLUMNS] for k in sorted(have)]))
        tmp.replace(gp)
    missing = [m["market_id"] for m in markets if m["market_id"] not in have]
    final = not missing or now >= et_epoch(day, *close_et(day)) + OUTCOME_MAX_DAYS * cm.DAY
    return {"t": now, "n_resolved": len(have), "n_unresolved": len(missing), "final": final}


def pyth_live_tick(root: Path, *, now: float, start_day: str, frame_markets: Callable[[str], list[dict]], yahoo_get: Callable[[str, str, float, float], tuple[Any, float]],
                   book_get: Callable[[str], tuple[Any, float]], prints_get: Callable[[str, int, int], list[dict] | None], sessions: list[str] | None = None,
                   outcome_get: Callable[[list[str]], list[dict]] | None = None) -> dict:
    """One idempotent pass of the q0195 rolling collector: for the current session (ET) it performs whichever step is due and not yet done -
    pre-open sigma / K_d fetch (receipt-timed), each checkpoint (Yahoo hourly fetch + every frame-rule market's CLOB book, receipt-timed), and after
    the close the quote-window prints and the diagnostic post-session bars. Files under ``pyth_live/<session>/``. Returns what was done; the caller
    maps 'nothing due' to the idle heartbeat."""
    root = c9.refuse_path(Path(root))
    sessions = sessions or stage2_sessions(start_day)
    today = et_day(now)
    done_out = []
    if outcome_get is not None:  # M9: outcomes of every past session (guarded; never read here)
        for day in sessions:
            sd = root / day
            sp = sd / "state.json"
            if day >= today or not sp.exists():
                continue
            st0 = json.loads(sp.read_text())
            o = st0["steps"].get("outcomes") or {}
            if o.get("final") or now < et_epoch(day, *close_et(day)) + OUTCOME_DUE_S or now - float(o.get("t", 0)) < 3600:
                continue
            st0["steps"]["outcomes"] = fetch_outcomes(sd, day, now, frame_markets(day), outcome_get)
            sp.write_text(json.dumps(st0, sort_keys=True))
            done_out.append(f"outcomes:{day}")
    past_all = now > et_epoch(sessions[-1], 23, 59) + 2 * cm.DAY or (datetime.fromtimestamp(now, UTC).date() - _d(start_day)).days > STAGE2_COLLECT_MAX_DAYS
    if past_all:
        pending = [d for d in sessions if (root / d / "state.json").exists() and not (json.loads((root / d / "state.json").read_text())["steps"].get("outcomes") or {}).get("final")]
        if outcome_get is None or not pending:
            return {"status": "pyth_live_complete", "done": done_out}
        return {"status": "collected" if done_out else "idle", "done": done_out, "outcomes_pending": pending}
    if today not in sessions:
        return {"status": "collected" if done_out else "idle", "done": done_out}
    sdir = root / today
    sdir.mkdir(parents=True, exist_ok=True)
    state_p = sdir / "state.json"
    st = json.loads(state_p.read_text()) if state_p.exists() else {"steps": {}}
    done = []
    tickers = sorted({m["ticker"] for m in frame_markets(today)})
    if "pre" not in st["steps"] and now >= et_epoch(today, 8, 0) and now < et_epoch(today, *OPEN_ET):
        ok = True
        for tk in tickers:
            try:
                doc, rt = yahoo_get(tk, "1h", et_epoch(today, 0, 0) - 45 * cm.DAY, et_epoch(today, 0, 0))
                ddoc, rt2 = yahoo_get(tk, "1d", et_epoch(today, 0, 0) - 10 * cm.DAY, et_epoch(today, 0, 0))
                (sdir / f"pre_{tk}.json").write_text(json.dumps({"hourly": doc, "daily": ddoc, "receipt_t": [rt, rt2]}))
            except Exception:
                ok = False
        st["steps"]["pre"] = {"ok": ok, "t": now}
        done.append("pre")
    for ci, _e, t in checkpoints(today):
        key = f"ckpt{ci}"
        if key in st["steps"] or not (t <= now < t + 600):
            continue
        rec = {"t": now, "yahoo": {}, "books": {}}
        for tk in tickers:
            try:
                doc, rt = yahoo_get(tk, "1h", et_epoch(today, 0, 0), now)
                rec["yahoo"][tk] = {"s_t": live_s_t(doc, today, rt), "receipt_t": rt}
            except Exception:
                rec["yahoo"][tk] = {"s_t": None, "error": True}
        for m in frame_markets(today):
            for side in ("up", "down"):
                try:
                    doc, rt = book_get(m[f"token_{side}"])
                    rec["books"][f"{m['market_id']}|{side}"] = {"state": clob_book_state(doc), "receipt_t": rt}
                except Exception:
                    rec["books"][f"{m['market_id']}|{side}"] = {"state": None}
        (sdir / f"{key}.json").write_text(json.dumps(rec, default=float))
        st["steps"][key] = {"t": now}
        done.append(key)
    if "post" not in st["steps"] and now >= et_epoch(today, *close_et(today)) + 1800:
        out = {}
        for m in frame_markets(today):
            for ci, e, _t in checkpoints(today):
                out[f"{m['market_id']}|{ci}"] = prints_get(m["condition_id"], int(e + PRINT_WINDOW_S[0]), int(e + PRINT_WINDOW_S[1]))
        (sdir / "prints.json").write_text(json.dumps(out, default=float))
        diag = {}
        for tk in tickers:
            try:
                diag[tk] = yahoo_get(tk, "1h", et_epoch(today, 0, 0), now)[0]
            except Exception:
                diag[tk] = None
        (sdir / "bars_post_DIAGNOSTIC_ONLY.json").write_text(json.dumps(diag, default=float))
        st["steps"]["post"] = {"t": now}
        done.append("post")
    state_p.write_text(json.dumps(st, sort_keys=True))
    done += done_out
    return {"status": "collected" if done else "idle", "done": done, "session": today}


def live_frame_markets(lim: hb.Limiter, day: str, excl_ids: set[str], excl_keys: dict[str, set[str]]) -> list[dict]:
    """Stage-2 frame-rule markets of a session: Gamma markets (open or closed) with endDate in the session's window, the frozen regexes and flags, key drops."""
    a, b = gamma_end_window(day)
    rows: list[dict] = []
    for closed in ("false", "true"):
        got, capped = hb._paged(lim, {"closed": closed, "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true"}, error_is_capped=True)
        if capped:
            raise cm.ApiError(f"Gamma live frame {day} capped or failed")
        rows += [r for r in (parse_market(m, day)[0] for m in got if isinstance(m, dict)) if r is not None]
    uniq = {r["market_id"]: r for r in rows}
    kept, _ = c9.drop_by_keys(list(uniq.values()), excl_ids, excl_keys)
    return sorted(kept, key=lambda r: r["market_id"])


def live_units(live_root: Path, sessions: list[str], frames: dict[str, list[dict]], *, lag_s: int = USABLE_LAG_S) -> tuple[list[dict], dict]:
    """P units of the Stage-2 sessions from the q0195 files: S_t from each checkpoint's receipt-timed Yahoo response; sigma and K_d from the pre-open
    response (bars and the prior daily close, as Stage 1); CLOB books at the checkpoint (receipt clock); quote-window prints after the session. A
    missing / failed input makes the checkpoint 'unavailable (source)' (no substitute). Returns (units, checkpoint status map)."""
    status: dict[tuple[str, int], str] = {}
    units: list[dict] = []
    for day in sessions:
        sdir = Path(live_root) / day
        st = json.loads((sdir / "state.json").read_text()) if (sdir / "state.json").exists() else {"steps": {}}
        pre_ok = bool((st["steps"].get("pre") or {}).get("ok"))
        prints = json.loads((sdir / "prints.json").read_text()) if (sdir / "prints.json").exists() else {}
        sig, kd_ = {}, {}
        for m in frames.get(day, []):
            tk = m["ticker"]
            if tk in sig:
                continue
            pp = sdir / f"pre_{tk}.json"
            if not pp.exists():
                sig[tk], kd_[tk] = None, None
                continue
            pre = json.loads(pp.read_text())
            rows = parse_chart(pre["hourly"])
            sess = [x for x in full_sessions("2026-01-01", day) if x < day]
            bars = {x: session_bars(rows, x)[0] for x in sess[-SIGMA_SESSIONS:]}
            sig[tk] = sigma_for(day, {x: v for x, v in bars.items() if v}, sess)
            dly = daily_rows(pre["daily"])
            prev = [x for x in sorted(dly) if x < day]
            kd_[tk] = dly[prev[-1]]["close"] if prev else None
        for ci, e, t in checkpoints(day, lag_s):
            cp = sdir / f"ckpt{ci}.json"
            rec = json.loads(cp.read_text()) if cp.exists() else None
            for m in frames.get(day, []):
                tk = m["ticker"]
                y = (rec or {}).get("yahoo", {}).get(tk) or {}
                s_t = y.get("s_t")
                stt = checkpoint_status(bool(rec) and not y.get("error"), s_t, pre_ok and sig.get(tk) is not None and kd_.get(tk) is not None)
                status[(day, ci)] = stt if status.get((day, ci), "ok") == "ok" else status[(day, ci)]
                u = {"market_id": m["market_id"], "ticker": tk, "day": day, "month": day[:7], "ckpt": ci, "t": t, "e": e, "up_idx": int(m["up_idx"]), "label": "ok"}
                if stt != "ok":
                    u.update(label="source unavailable", trade=None, p2=None)
                    units.append(u)
                    continue
                books = {sd: ((rec.get("books") or {}).get(f"{m['market_id']}|{sd}") or {}).get("state") for sd in ("up", "down")}
                books = {k: v for k, v in books.items() if v}
                fv = fair_up(s_t, kd_[tk], sig[tk], tau_hours(day, t))
                u.update(s_t=s_t, k_d=kd_[tk], sigma=sig[tk], fair_up=fv)
                if fv is None or not books:
                    u.update(label="no fresh book" if fv is not None else "features unavailable", trade=None, p2=None)
                    units.append(u)
                    continue
                u["trade"] = p1_unit(fv, books)
                u["trade_cost"] = p1_unit(fv, books, cost_add=COST_ROBUST) if u["trade"] else None
                upb = books.get("up")
                u["p2"] = None
                if upb and not upb["crossed"] and upb["best_bid"] is not None and upb["best_ask"] is not None:
                    q = p2_quotes(fv, upb["best_bid"], upb["best_ask"], upb["tick"])
                    pr = up_prints(prints.get(f"{m['market_id']}|{ci}") or [], int(m["up_idx"]))
                    fills = {f"{name}_{rule}": quote_pair_pnl(pr, t, q[name][0], q[name][1], depth_at(upb["bids"], q[name][0]), depth_at(upb["asks"], q[name][1]), None, rule=rule)
                             for name in ("model", "mid") for rule in ("queue", "through")}
                    u["p2"] = {"quotes": q, "fills": fills}
                units.append(u)
    return units, status


# =====================================================================================================================================
# q0198 half-day poll (descriptive, uncounted)
# =====================================================================================================================================


HALFDAY_POLL_ET = ((13, 5), (16, 0))


def halfday_tick(root: Path, *, now: float, days: list[str], frame_markets: Callable[[str], list[dict]], book_get: Callable[[str], tuple[Any, float]]) -> dict:
    """One pass of the q0198 poller: on a declared half session between 13:05 and 16:00 ET, the book of each frame-rule market once per minute
    (idempotent per minute). Yahoo 1-minute bars are fetched after the close by the caller. Descriptive, uncounted."""
    root = c9.refuse_path(Path(root))
    today = et_day(now)
    if today not in days:
        return {"status": "idle"}
    a, b = et_epoch(today, *HALFDAY_POLL_ET[0]), et_epoch(today, *HALFDAY_POLL_ET[1])
    if not (a <= now <= b):
        return {"status": "idle"}
    minute = int((now - a) // 60)
    p = root / today / f"m{minute:03d}.json"
    if p.exists():
        return {"status": "idle"}
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {}
    for m in frame_markets(today):
        for side in ("up", "down"):
            try:
                doc, rt = book_get(m[f"token_{side}"])
                rec[f"{m['market_id']}|{side}"] = {"state": clob_book_state(doc), "receipt_t": rt}
            except Exception:
                rec[f"{m['market_id']}|{side}"] = {"state": None}
    p.write_text(json.dumps(rec, default=float))
    return {"status": "collected", "minute": minute}


# =====================================================================================================================================
# Smoke helpers (q0180; hashed into BOTH rules files: the sign rules fix the smoke criteria)
# =====================================================================================================================================


def smoke_pmxt_hours(seed: str = SMOKE_PMXT_SEED, n: int = SMOKE_PMXT_N) -> list[str]:
    days = sorted(p_days(), key=lambda d: c9.rank(seed, d))[:n]
    return [f"{d}T{PMXT_HOURS_Z[i % len(PMXT_HOURS_Z)]:02d}" for i, d in enumerate(days)]


def smoke_gamma_paging(lim: hb.Limiter, days: tuple[str, ...] = SMOKE_GAMMA_DAYS) -> dict:
    """Two walks of each out-of-window day's endDate window; stable iff the id sets are equal and the walk is not capped. Counts only."""
    per = {}
    for d in days:
        a, b = gamma_end_window(d)
        walks, reasons, excerpts = [], {}, set()
        for w in range(2):
            rows, capped = hb._paged(lim, {"closed": "true", "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true"}, error_is_capped=True)
            n_primary = 0
            for m in rows:
                if not isinstance(m, dict):
                    continue
                r, why = parse_market(m, d)
                n_primary += int(r is not None)
                if w == 0:
                    reasons[why] = reasons.get(why, 0) + 1
                    if r is not None:
                        excerpts.add(equality_excerpt(str(m.get("description") or "")))
            walks.append(({str(m.get("id")) for m in rows if isinstance(m, dict)}, capped, n_primary))
        per[d] = {"n_first": len(walks[0][0]), "n_second": len(walks[1][0]), "capped": walks[0][1] or walks[1][1], "n_primary_first": walks[0][2],
                  "parse_reasons_first": dict(sorted(reasons.items())), "equality_excerpts_primary": sorted(excerpts)[:5],
                  "stable": walks[0][0] == walks[1][0] and not (walks[0][1] or walks[1][1])}
    return {"days": per, "pass": all(v["stable"] for v in per.values())}


def equality_excerpt(desc: str) -> str:
    """The sentence of a rule text that contains "equal" (M3: recorded for out-of-window primary markets; text only, no price)."""
    for sent in re.split(r"(?<=[.!?])\s+", desc):
        if re.search(r"(?i)\bequal\b", sent):
            return sent.strip()[:300]
    return ""


def smoke_pmxt_heads(size_fn: Callable[[str], int]) -> dict:
    from . import history_sources as hs  # noqa: PLC0415

    out = []
    for h in smoke_pmxt_hours():
        try:
            out.append({"hour": h, "size": int(size_fn(hs.pmxt_url(datetime.fromisoformat(f"{h}:00:00+00:00"))))})
        except FileNotFoundError:
            out.append({"hour": h, "size": None})
    return {"heads": out, "pass": all(x["size"] for x in out)}


def smoke_declared() -> dict:
    return {"ticker": SMOKE_TICKER, "sessions": list(SMOKE_SESSIONS), "tol": SMOKE_TOL, "bar_clock": bar_clock_declared(),
            "check": "after the drop exactly 7 bars; first start 09:30 ET; first open vs daily open and last close vs daily close within 0.2%; dropped rows by count",
            "failure": "P not testable (source), counted; never re-fitted", "gamma_paging_days": list(SMOKE_GAMMA_DAYS),
            "gamma_paging": "two walks per day, equal id sets, not capped; parse_market reason counts and the equality-clause sentence of primary markets recorded (M3)", "pmxt_heads": smoke_pmxt_hours(), "pmxt_seed": SMOKE_PMXT_SEED}


def bar_clock_declared() -> dict:
    return {"timestamp": "bar start o", "end": "e = min(o + 60 min, 16:00 ET) (13:00 ET on half sessions)",
            "drop": "o < 09:30 ET, o >= close (closing rows), e <= o (zero length), missing open/close", "full_bars": FULL_BARS, "half_bars": HALF_BARS,
            "other_count": "bars unavailable for that ticker-day, counted, never repaired", "usable": f"e + {USABLE_LAG_S} s <= t",
            "checkpoints_et": ["10:32 (09:30 bar)", "12:32 (11:30 bar)", "15:32 (14:30 bar)"], "daily_close": "close of day d - 1 usable from d 00:00Z",
            "holidays_2026": list(HOLIDAYS_2026), "half_sessions_2026": list(HALF_SESSIONS_2026)}


def smoke_rule_funcs() -> tuple:
    return (parse_chart, session_bars, usable, latest_usable, daily_rows, smoke_yahoo_check, smoke_gamma_paging, equality_excerpt, smoke_pmxt_heads, smoke_pmxt_hours, smoke_declared,
            bar_clock_declared, et_epoch, et_day, close_et, expected_bars, is_full_session, full_sessions, p_days, gamma_end_window, parse_market, yahoo_chart,
            yahoo_transport)


# =====================================================================================================================================
# Rules
# =====================================================================================================================================


def declared() -> dict:
    from . import cb9_sign as sg  # noqa: PLC0415

    return {
        "family": "CB9-P (CH83a + CH84), CREATIVE_BATCH_9.md CB9-P; rules file also fixes the q0182 keys and the census gates",
        "population": {"days": f"full NYSE sessions in [{WINDOW[0]}, {WINDOW[1]}) minus the pmxt gap [{GAP[0]}, {GAP[1]})", "n_days": len(p_days()),
                       "gamma_end_window": "endDate in [d 19:59Z, d 20:01Z] (EDT; one hour later in EST)", "question_re": QUESTION_RE, "source_re": SOURCE_RE,
                       "flag_res": FLAG_RES, "exclude_res": EXCLUDE_RES, "old_version_res": OLD_VERSION_RES,
                       "flag_scope": "equality and no-trade flags must hold within one sentence (M4)", "outcome_labels": list(OUTCOME_LABELS), "neg_risk": "excluded",
                       "strike_markets": "excluded from the primary; counted (reported stratum)", "ticker_map": TICKER_MAP_RULE,
                       "keys": "q0182 exclusion ids and event / neg-risk / series keys dropped; unverified disjointness -> P not testable, counted"},
        "clock": bar_clock_declared(),
        "features": {"s_t": "close of the latest usable hourly bar", "k_d": "Yahoo daily close of the prior session", "sigma": SIGMA_RULE,
                     "sigma_sessions": SIGMA_SESSIONS, "sigma_min_returns": SIGMA_MIN_RETURNS, "tau": "hours to 16:00 ET", "fair_up": "Phi(ln(S/K)/(sigma sqrt(tau)))",
                     "stale": STALE_RULE, "bars_from": BARS_FROM, "guarded": list(GUARDED_FILES),
                     "feature_files": "bars_pre.csv.gz holds bars 09:30..14:30 of every session; the 15:30 bar and the daily closes go to closes_settle_guarded.csv.gz"},
        "book": {"source": "pmxt v2 hours 14Z, 16Z, 19Z (row-group streaming); the previous hour only for tokens without a book snapshot by the checkpoint",
                 "fresh_s": FRESH_S, "crossed": "ineligible, never repaired", "clock": "an event is used at t iff both clocks <= t", "lags_s": [USABLE_LAG_S, LATENCY_LAG_S],
                 "ingress_cap_gb": INGRESS_CAP_GB, "print_window_s": list(PRINT_WINDOW_S), "print_pages": PRINT_PAGES},
        "p1": {"edge": EDGE, "min_ask_size": MIN_ASK_SIZE, "fee": "r a (1 - a), r = max(recorded fee_rate_bps/1e4 at t, 0.04)", "fee_floor": FEE_RATE_FLOOR,
               "unit": "(market-day, checkpoint) with features and a fresh, uncrossed book on the traded token; both edges -> the larger",
               "net": "Y - a - f(a), Y from the guarded Gamma outcome (0.5 on 50-50)", "floor": FLOOR_P1, "cost_robustness": COST_ROBUST,
               "size_weight_cap": SIZE_WEIGHT_CAP, "clusters": ["day", "ticker"]},
        "p2": {"half_width": QUOTE_HALF_WIDTH, "size": QUOTE_SIZE, "life_s": QUOTE_LIFE_S, "token": "Up",
               "quotes": "bid floor_tick(c - 1c), ask ceil_tick(c + 1c); capped passive (bid <= best ask - tick, ask >= best bid + tick); c = fair_Up or the book mid",
               "fills": "cb3_maker.quote_fills queue rule; depth = resting size at the quote's own level at t; complementary prints in Up terms",
               "through_rule": "robustness: cumulative size of prints strictly through the quote >= 20 shares", "statistic": "(model P&L - mid P&L)/40 per origin",
               "floor": FLOOR_P2, "route_gate": "model-centred net per posted share > 0", "min_fill_rate": P2_MIN_FILL_RATE, "rebate_share": REBATE_SHARE,
               "size_weight": "filled shares of the origin (model + mid)"},
        "robustness": {"months": {"min_units": MONTH_MIN_UNITS, "share": MONTH_SHARE}, "worst_case": "unavailable checkpoints scored as the worst observed unit of that day",
                       "latency": "units and quotes at bar end + 300 s; sign and >= half the magnitude"},
        "source_check": {"min_abs_return": SOURCE_MIN_ABS_RET, "max_disagree": SOURCE_DISAGREE_MAX},
        "census": {"gate_GP": GP, "audit_pass": AUDIT_PASS, "available_min": AVAILABLE_MIN,
                   "audit": "every (market, quote window) with >= 1 Data API print: share with any pmxt event for the condition in the same span"},
        "stage2": {"sessions": STAGE2_SESSIONS, "collect_max_days": STAGE2_COLLECT_MAX_DAYS, "unavailable_max": STAGE2_UNAVAILABLE_MAX,
                   "yahoo": "fetched at each checkpoint, receipt-timed; S_t from that response; pre-open sigma/K_d fetch; post-session bars diagnostic only",
                   "partial_failure": "no substitute source; failed checkpoint unavailable (source); failed sigma/K_d -> the whole session; counts toward the 30",
                   "books": "CLOB /book, receipt clock only", "start": "first full NYSE session >= CB9 freeze commit + 1 day",
                   "outcomes": f"guarded post-settlement Gamma fetch from close + {OUTCOME_DUE_S // 3600} h, hourly, final when all resolved or after {OUTCOME_MAX_DAYS} d "
                               "(unresolved counted); <session>/outcomes_guarded.csv.gz, opened only by rep-P (M9)",
                   "rule": "Stage-2 rule: cb9_common.STAGE2_RULE (M10)"},
        "halfday": {"days": list(HALF_SESSIONS_2026), "poll_et": ["13:05", "16:00"], "every_s": 60, "counted": False},
        "rates": {"yahoo_rps": YAHOO_RPS, "gamma_data_rps_max": 2.0},
        "smoke": smoke_declared(),
        "kd_and_sign_rules": {"kd": "seals/cb9_kd_rules.json (cb9_kd)", "sign": "seals/cb9_sign_rules.json", "sign_s0_census_columns": list(sg.CENSUS_COLUMNS_S)},
    }


def rule_funcs() -> tuple:
    from . import cb3_maker as c3  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415

    return (declared, _d, checkpoints, hourly_returns, sigma_for, tau_hours, fair_up, fee_rate, taker_fee, floor_tick, ceil_tick, p1_unit, p1_net, p2_quotes, up_prints,
            depth_at, through_fill, quote_pair_pnl, outcome_y, frame_day, open_guarded, write_rows, pyth_frame, levels_at, state_row, pyth_books, load_bars, build_units,
            _state_dict, census_p, _cl, _months_ok, _drop_ok, p1_stat, p2_stat, source_check, live_s_t, stage2_sessions, t9_p2_start, stage2_availability,
            checkpoint_status, clob_book_state, fetch_outcomes, pyth_live_tick, live_frame_markets, live_units, halfday_tick, c3.quote_fills, c3._side_tuple, bk.read_hour_events, bk.state_at, bk._levels,
            c9.drop_by_keys, hb._paged, *smoke_rule_funcs())


def gz_rows(path: Path) -> list[dict]:
    import csv  # noqa: PLC0415

    with gzip.open(Path(path), "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
