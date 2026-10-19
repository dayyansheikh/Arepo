# ruff: noqa: E501
"""CB12-O: option-chain digital anchor for equity "close above $K" markets (docs/research_lab/CREATIVE_BATCH_12.md CB12-O, section 10 items 11-13). Rules part ``O``.

Prospective only. The collector (q0261, ``opt-live``, cron outside the queue lanes) reads, at 11:00, 13:00 and 15:00 America/New_York on regular US trading days,
the Gamma strike frame (both frozen templates), the keyless CBOE delayed chain per underlying (read FIRST), then two receipt-timed CLOB ``/book`` reads per member
>= 60 s apart. Once a trading day it stores Yahoo daily bars before the day (realised-vol attribution), the Nasdaq earnings calendar (earnings flag) and the
Nasdaq dividend list (amendment O3: the declared ex-dividend rule reads the PREVIOUS session's Nasdaq file, never a fetch made after t). After each settlement date it writes the Yahoo settlement
close (O1's outcome) and the Gamma resolution (O2's payoff) ONLY to ``outcomes_guarded/<settlement date>/``. Windows are defined by settlement date and close
on counts only (clusters and dates with a tight unit), never on results. The smoke (q0260, ``opt-smoke``) checks the sources live and chooses the chain's iv time
convention from two pre-declared candidates by a pre-declared criterion; the choice is written into the O freeze declaration (``model_specs/cb12_v1.json``
part ``O``, key ``iv_convention``) before the freeze. Census (q0262, counts only, gate GO), screen (q0263: O1, O2 on window 1) and rep (q0264: window 2).

EXPLORATORY. No edge, calibration or profitability claim; AREPO never trades (O2 is a paper rule at recorded asks). O shares underlyings and sessions with
CB9-P: an O result and a CB9-P result are not independent evidence. This module imports ``cb12_common`` and nothing from the other CB12 families.
"""

from __future__ import annotations

import fcntl
import gzip
import json
import math
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import norm

from . import cb8_common as cm
from . import cb12_common as c12
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow

HOUR = 3600.0
DAY = 86400.0
RUN = "h12_opt_live"
# ---- frame (frozen) -------------------------------------------------------------------------------------------------------------------------------
SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
SEARCH_QUERIES = ("closes above", "close above")  # Gamma public search, active events; <= 2 pages each (<= 4 of the <= 5 Gamma requests per checkpoint)
SEARCH_LIMIT = 100
SEARCH_MAX_PAGES = 2
MONTH_END_RE = re.compile(r"^Will .+ \(([A-Z.]{1,6})\) close above ___ (on .+|end of [A-Z][a-z]+)\?$")
DAILY_RE = re.compile(r"^.+ \(([A-Z.]{1,6})\) closes above ___ on [A-Z][a-z]+ \d{1,2}\?$")
WEEKLY_RE = re.compile(r"(?i)\bfinish(?:es)?\s+(?:the\s+)?week\b")  # weekly "finish week of ... above" events: excluded, counted
ON_DATE_RE = re.compile(r" on ([A-Z][a-z]+) (\d{1,2})(?:, (\d{4}))?\?$")
END_OF_RE = re.compile(r"end of ([A-Z][a-z]+)\?$")
STRIKE_RE = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)")
STRIKE_Q_RE = re.compile(r"(?i)above \$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
SETTLEMENT_TOL_DAYS = 3  # parsed settlement date vs the market endDate's ET date: a larger gap is "settlement date ambiguous" (excluded, counted)
# rule-text flags, frozen before the smoke's live read (booleans + the description sha256 are stored, never the text)
FLAG_RES = {"pyth": re.compile(r"(?i)\bpyth\b"), "official_close": re.compile(r"(?i)\bofficial\b[^.]{0,40}\bclos"), "exchange_close": re.compile(r"(?i)\b(nasdaq|nyse|exchange)\b[^.]{0,60}\bclos"),
            "final_close": re.compile(r"(?i)\b(final|closing)\b[^.]{0,30}\b(price|close)\b"), "regular_session": re.compile(r"(?i)\bregular\s+(trading\s+)?(session|hours)\b"),
            "equal_clause": re.compile(r"(?i)\b(exactly\s+equal|equal\s+to|or\s+equal|at\s+or\s+above)\b")}
# underlying map (frozen): equities and equity ETFs by ticker, the named indices by their CBOE index symbol and PM-settled root; commodities, crypto and volatility excluded
EXCLUDED_UNDERLYINGS = ("WTI", "CL", "BRENT", "BZ", "GC", "GOLD", "XAU", "SI", "SILVER", "XAG", "NG", "HG", "COPPER", "BTC", "ETH", "SOL", "XRP", "DOGE", "VIX", "DXY")
INDEX_CBOE = {"SPX": "_SPX", "NDX": "_NDX", "RUT": "_RUT"}
INDEX_ROOT = {"SPX": "SPXW", "NDX": "NDXP", "RUT": "RUTW"}  # PM-settled (16:00 ET close) roots
INDEX_YAHOO = {"SPX": "^GSPC", "NDX": "^NDX", "RUT": "^RUT"}
# ---- sources --------------------------------------------------------------------------------------------------------------------------------------
CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{}.json"
CBOE_TS_FORMAT = "%Y-%m-%d %H:%M:%S"  # the top-level ``timestamp``, read as UTC (the smoke checks it is older than the receipt and < 1 h old in session)
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
NASDAQ_EARNINGS = "https://api.nasdaq.com/api/calendar/earnings"
NASDAQ_DIVIDENDS = "https://api.nasdaq.com/api/quote/{}/dividends"
CLOB_BOOK = "https://clob.polymarket.com/book"
EXT_UA = "Mozilla/5.0 (arepo-research-lab/1)"
PM_RPS = 2.0
EXT_RPS = 1.0
# ---- collection (frozen) ----------------------------------------------------------------------------------------------------------------------------
CHECKPOINTS_ET = ((11, 0), (13, 0), (15, 0))  # regular sessions only (half sessions and holidays have none)
CHECKPOINT_WINDOW_S = 20 * 60  # a checkpoint runs at the first collector call in [t_c, t_c + 20 min); a missed one is "unavailable (collection)", never back-filled
DAILY_FROM_ET = (10, 0)
BOOK_GAP_S = 60.0
BOOK_LEVELS = 5
MAX_MEMBERS = 200  # members beyond (by the seeded rank) are "unavailable (collection cap)", counted
CAP_SEED = "arepo-cb12-opt-cap"
MAX_CHAINS = 20
CHAIN_STRIKES_EACH_SIDE = 3
EARNINGS_MAX_DAYS = 45
YAHOO_FEATURE_DAYS = 45
OUTCOME_MAX_DAYS = 7
OUTCOME_EVERY_S = 3 * HOUR
HOLIDAYS = ("2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
            "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24")
HALF_SESSIONS = ("2026-11-27", "2026-12-24", "2027-11-26")
OPEN_ET = (9, 30)
CLOSE_ET = (16, 0)
HALF_CLOSE_ET = (13, 0)
SMOKE_SESSION_ET = ((10, 0), (15, 45))  # the smoke must run inside a regular session (chains and books live)
# ---- units, anchor, tests (frozen) ------------------------------------------------------------------------------------------------------------------
TIGHT_SPREAD = 0.045
EDGE = 0.04
Q_MIN, Q_MAX = 0.05, 0.95
OPT_SPREAD_MAX = 0.10
FEE_FLOOR = 0.04
O1_FLOOR = 0.30
O2_FLOOR = 0.01
O2_COST_ROBUST = 0.005
RV_DAYS = 20
DIVIDEND_RULE = "nasdaq_previous_session"  # section 11 amendment O3: ex-dividend date in (ET date of t, d] from the Nasdaq list stored by the PREVIOUS session's daily step; unknown -> excluded; cash-settled indices exempt
DIV_KEY_RE = re.compile(r"(?i)div")  # informational only (smoke: does the CBOE chain carry a dividend field; it does not, 2026-10-19); no rule reads it
# equity ETFs queried with the Nasdaq assetclass "etf" (frozen list); any other equity ticker is tried as "stocks" first and as "etf" if that reply carries no dividend section
ETF_TICKERS = ("SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "IVV", "EEM", "EFA", "TLT", "HYG", "LQD", "GLD", "SLV", "USO", "XLE", "XLF", "XLK", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB",
               "XLRE", "XLC", "SMH", "SOXX", "ARKK", "TQQQ", "SQQQ", "SOXL", "SPXL", "IBIT", "BITO", "ETHA", "FXI", "KWEB", "GDX", "XBI", "IYR", "VNQ", "MDY")
CONVENTIONS = ("act365", "trading_hours")  # (a) calendar time to the expiry's 16:00 ET close / 365 d; (b) remaining regular-session hours / (252 x 6.5)
CONVENTION_N = 20
CONVENTION_TOL = 0.01
CONVENTION_SHARE = 0.80
CONV_MONEYNESS = 0.03
CONV_DAYS = (2, 60)
CONV_MIN_THEO = 0.05
CONV_PER_UNDERLYING = 4
WINDOW1_CAP = "2027-01-31"
WINDOW2_CAP = "2027-05-31"
WINDOW_MIN_CLUSTERS = 60
WINDOW_MIN_DATES = 30
GO_MIN = {"tight_units": 1000, "clusters": 40, "dates": 30, "per_session": 10}
COR_MAX = 0.9
AGREE_MIN = 0.97
SEED_SIGNFLIP = 12109
LABEL_O = "prospective (window 1 Stage 1; window 2 L2); not independent of CB9-P"
SMOKE_FAMILY_VERSION = "cb12-smoke-O-v1"
SMOKE_V2_DEFAULT = c12.CB12_DIR / "opt_smoke.json"
SMOKE_NEEDS = ("guards_fixture_O", "o_frame_regex", "o_chain", "o_chain_timestamp", "o_books", "o_iv_convention_checked", "o_yahoo_keyless", "o_gamma_closed_lookup", "o_dividends_keyless")
YAHOO_PROBES = ("SPY", "^GSPC")  # an ETF and an index: the O1 outcome source and the q_RV bar source
DIV_PROBES = ("SPY", "AAPL")  # an ETF (assetclass etf) and a stock (assetclass stocks): the amended ex-dividend source
UNIT_LABELS = ("available", "unavailable (first read)", "crossed", "not tight", "unavailable (chain)", "unavailable (chain timestamp)", "excluded: no anchor",
               "excluded: option spread", "excluded: q range", "excluded: ex-dividend", "excluded: ex-dividend unknown", "excluded: phi(d2) without convention",
               "unavailable (second read)")
OUTCOME_COLUMNS = ["market_id", "settle", "yes_index", "outcome_prices", "uma_status"]
CLOSE_COLUMNS = ["symbol", "settle", "close"]


# =====================================================================================================================================================
# Calendar (America/New_York; regular sessions; DST by the zone)
# =====================================================================================================================================================


def _d(s: str) -> date:
    return date.fromisoformat(s)


def is_session(day: str) -> bool:
    return _d(day).weekday() < 5 and day not in HOLIDAYS


def is_regular(day: str) -> bool:
    return is_session(day) and day not in HALF_SESSIONS


def close_hm(day: str) -> tuple[int, int]:
    return HALF_CLOSE_ET if day in HALF_SESSIONS else CLOSE_ET


def et_epoch(day: str, hh: int, mm: int = 0) -> float:
    y, m, d = map(int, day.split("-"))
    return datetime(y, m, d, hh, mm, tzinfo=c12.NY).timestamp()


def et_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, c12.NY).date().isoformat()


def day_add(day: str, n: int) -> str:
    return (_d(day) + timedelta(days=n)).isoformat()


def next_session(day: str) -> str:
    d = day_add(day, 1)
    while not is_session(d):
        d = day_add(d, 1)
    return d


def prev_session(day: str) -> str:
    d = day_add(day, -1)
    while not is_session(d):
        d = day_add(d, -1)
    return d


def sessions_between(a: str, b: str) -> list[str]:
    """Sessions in ``[a, b]``."""
    out, d = [], a
    while d <= b:
        if is_session(d):
            out.append(d)
        d = day_add(d, 1)
    return out


def checkpoint_epochs(day: str) -> list[tuple[str, float]]:
    """(label HHMM, epoch) of the three checkpoints of a REGULAR session (none on half sessions, weekends, holidays)."""
    if not is_regular(day):
        return []
    return [(f"{hh:02d}{mm:02d}", et_epoch(day, hh, mm)) for hh, mm in CHECKPOINTS_ET]


def last_session_of_month(y: int, m: int) -> str:
    d = date(y + (m == 12), 1 if m == 12 else m + 1, 1) - timedelta(days=1)
    while not is_session(d.isoformat()):
        d -= timedelta(days=1)
    return d.isoformat()


def window1_start(frozen_epoch: float) -> str:
    """The first trading session at least one calendar day after the O freeze (ET dates)."""
    d = day_add(et_day(frozen_epoch), 1)
    while not is_session(d):
        d = day_add(d, 1)
    return d


# =====================================================================================================================================================
# Frame parsing (whitelisted fields only)
# =====================================================================================================================================================


def classify_title(title: str) -> tuple[str | None, str]:
    """(template, ticker): ``daily`` / ``month_end`` for the frozen templates, ``weekly`` (excluded, counted), None otherwise."""
    t = (title or "").strip()
    m = DAILY_RE.match(t)
    if m:
        return "daily", m.group(1)
    m = MONTH_END_RE.match(t)
    if m:
        return "month_end", m.group(1)
    if WEEKLY_RE.search(t) and "above" in t.lower():
        return "weekly", ""
    return None, ""


def underlying_of(ticker: str) -> dict:
    """CBOE chain symbol, option root, Yahoo symbol, or the exclusion reason (commodity / crypto / volatility underlyings)."""
    tk = (ticker or "").upper()
    if not tk:
        return {"excluded": "no ticker"}
    if tk in EXCLUDED_UNDERLYINGS:
        return {"excluded": "commodity / crypto / volatility underlying"}
    if tk in INDEX_CBOE:
        return {"excluded": "", "cboe": INDEX_CBOE[tk], "root": INDEX_ROOT[tk], "yahoo": INDEX_YAHOO[tk], "kind": "index"}
    return {"excluded": "", "cboe": tk, "root": tk.replace(".", ""), "yahoo": tk.replace(".", "-"), "kind": "equity"}


def _closest_year(month: int, day: int, ref: str) -> str | None:
    best = None
    for y in (int(ref[:4]) - 1, int(ref[:4]), int(ref[:4]) + 1):
        try:
            cand = date(y, month, day)
        except ValueError:
            continue
        if best is None or abs((cand - _d(ref)).days) < abs((best - _d(ref)).days):
            best = cand
    return best.isoformat() if best else None


def settlement_date(title: str, end_epoch: float) -> str | None:
    """The settlement date from the title (``on <Month> <day>[, <year>]`` or ``end of <Month>`` = the month's last session), the year closest to the market's
    endDate (ET date). None if unparseable."""
    if not math.isfinite(end_epoch):
        return None
    ref = et_day(end_epoch)
    m = ON_DATE_RE.search(title or "")
    if m and m.group(1) in MONTHS:
        mo, dd = MONTHS.index(m.group(1)) + 1, int(m.group(2))
        if m.group(3):
            try:
                return date(int(m.group(3)), mo, dd).isoformat()
            except ValueError:
                return None
        return _closest_year(mo, dd, ref)
    m = END_OF_RE.search(title or "")
    if m and m.group(1) in MONTHS:
        mo = MONTHS.index(m.group(1)) + 1
        cands = [last_session_of_month(y, mo) for y in (int(ref[:4]) - 1, int(ref[:4]), int(ref[:4]) + 1)]
        return min(cands, key=lambda s: abs((_d(s) - _d(ref)).days))
    return None


def parse_strike(group_title: str, question: str) -> float:
    for txt, rx in ((group_title or "", STRIKE_RE), (question or "", STRIKE_Q_RE)):
        m = rx.search(txt)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return math.nan


def rule_flags(description: str) -> dict:
    return {k: bool(rx.search(description or "")) for k, rx in FLAG_RES.items()}


def parse_event(ev: dict) -> tuple[dict, list[dict]] | None:
    """(event row, member rows) of a frame event; only whitelisted fields leave this function (the description is hashed, prices and outcomes are never read)."""
    if not isinstance(ev, dict) or ev.get("id") is None:
        return None
    title = str(ev.get("title") or "")
    tmpl, ticker = classify_title(title)
    row = {"event_id": str(ev["id"]), "template": tmpl or "", "ticker": ticker, "title_sha256": c12.rank("arepo-cb12-title", title)}
    if tmpl not in ("daily", "month_end"):
        return row, []
    und = underlying_of(ticker)
    members = []
    for m in ev.get("markets") if isinstance(ev.get("markets"), list) else []:
        if not isinstance(m, dict) or m.get("id") is None:
            continue
        labels = [str(x).strip().lower() for x in c12.listish(m.get("outcomes"))]
        toks = [str(x) for x in c12.listish(m.get("clobTokenIds"))]
        if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2:
            continue
        yi = labels.index("yes")
        end = c12.parse_iso(m.get("endDate"))
        d = settlement_date(title, end)
        fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
        desc = str(m.get("description") or ev.get("description") or "")
        members.append({"event_id": row["event_id"], "market_id": str(m["id"]), "condition_id": str(m.get("conditionId") or ""), "token_yes": toks[yi], "yes_index": yi,
                        "K": parse_strike(str(m.get("groupItemTitle") or ""), str(m.get("question") or "")), "settle": d or "", "template": tmpl, "ticker": ticker,
                        "cboe": und.get("cboe", ""), "root": und.get("root", ""), "yahoo": und.get("yahoo", ""), "underlying_excluded": und.get("excluded", ""),
                        "end_epoch": end, "created_epoch": c12.parse_iso(m.get("createdAt")), "closed": bool(m.get("closed")), "neg_risk": bool(m.get("negRisk")),
                        "fee_rate": c12.num(fs.get("rate")), "desc_sha256": c12.rank("arepo-cb12-desc", desc), "flags": rule_flags(desc)})
    return row, members


def member_status(mem: dict, day: str, t: float) -> str:
    """'' if the member enters the checkpoint (books read), else the counted reason."""
    if mem["underlying_excluded"]:
        return f"excluded: {mem['underlying_excluded']}"
    if mem["closed"]:
        return "closed"
    if not math.isfinite(mem["K"]) or mem["K"] <= 0:
        return "excluded: strike unparsed"
    if not mem["settle"]:
        return "excluded: settlement unparsed"
    if not is_session(mem["settle"]):
        return "excluded: settlement not a session"
    if math.isfinite(mem["end_epoch"]) and abs((_d(mem["settle"]) - _d(et_day(mem["end_epoch"]))).days) > SETTLEMENT_TOL_DAYS:
        return "excluded: settlement date ambiguous"
    if mem["settle"] < day or t >= et_epoch(mem["settle"], *close_hm(mem["settle"])):
        return "past settlement"
    if math.isfinite(mem["created_epoch"]) and mem["created_epoch"] > t - HOUR:
        return "not listed"
    return ""


def discover(src, stats: dict) -> list[dict]:
    """Frame events from the frozen public-search queries (active), <= SEARCH_MAX_PAGES pages per query, union by event id."""
    seen: dict[str, dict] = {}
    for q in SEARCH_QUERIES:
        for page in range(1, SEARCH_MAX_PAGES + 1):
            data = src.search(q, page)
            evs = data.get("events") if isinstance(data, dict) else None
            for e in evs or []:
                if isinstance(e, dict) and e.get("id") is not None:
                    seen.setdefault(str(e["id"]), e)
            more = bool(((data or {}).get("pagination") or {}).get("hasMore")) if isinstance(data, dict) else False
            if not more:
                break
            if page == SEARCH_MAX_PAGES:
                stats["search_capped"] = stats.get("search_capped", 0) + 1
    return [seen[k] for k in sorted(seen)]


# =====================================================================================================================================================
# Chain and book parsing
# =====================================================================================================================================================


OPT_SYM_RE = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def parse_option(sym: str) -> tuple[str, str, str, float] | None:
    """(root, expiry YYYY-MM-DD, C/P, strike) of an OCC-style symbol such as ``NVDA261019C00120000``."""
    m = OPT_SYM_RE.match(str(sym or ""))
    if not m:
        return None
    yymmdd = m.group(2)
    return m.group(1), f"20{yymmdd[:2]}-{yymmdd[2:4]}-{yymmdd[4:]}", m.group(3), int(m.group(4)) / 1000.0


def chain_ts(doc: Any) -> float:
    try:
        return datetime.strptime(str(doc.get("timestamp")), CBOE_TS_FORMAT).replace(tzinfo=UTC).timestamp()
    except (AttributeError, TypeError, ValueError):
        return math.nan


def chain_subset(doc: Any, root: str, needs: Iterable[tuple[float, str]], receipt_t: float) -> dict:
    """The stored part of a CBOE chain: timestamp, underlying quote fields, every listed expiry of ``root``, and for each needed (K, d) the calls AND puts of the
    target expiry (d if listed, else the nearest listed expiry >= d) at the listed strikes from 3 below to 3 at-or-above K. Any underlying field whose name contains
    "div" is kept (the declared ex-dividend rule reads the chain's own data)."""
    data = doc.get("data") if isinstance(doc, dict) else None
    if not isinstance(data, dict):
        return {"status": "no data", "receipt_t": receipt_t}
    und_keys = ("current_price", "bid", "ask", "close", "prev_day_close", "iv30", "last_trade_time")
    und = {k: data.get(k) for k in und_keys}
    und.update({k: v for k, v in data.items() if DIV_KEY_RE.search(str(k)) and k != "options"})
    by_exp: dict[str, dict[float, dict[str, list]]] = {}
    for o in data.get("options") or []:
        if not isinstance(o, dict):
            continue
        p = parse_option(o.get("option"))
        if p is None or p[0] != root:
            continue
        rec = [o.get("option"), p[2], p[1], p[3], o.get("bid"), o.get("ask"), o.get("bid_size"), o.get("ask_size"), o.get("iv"), o.get("theo"), o.get("delta"),
               o.get("open_interest"), o.get("volume"), o.get("last_trade_time")]
        by_exp.setdefault(p[1], {}).setdefault(p[3], {})[p[2]] = rec
    expiries = sorted(by_exp)
    keep: dict[str, list] = {}
    for K, d in needs:
        tgt = d if d in by_exp else next((e for e in expiries if e >= d), None)
        if tgt is None:
            continue
        strikes = sorted(by_exp[tgt])
        lo = sum(1 for s in strikes if s < K)
        for s in strikes[max(0, lo - CHAIN_STRIKES_EACH_SIDE):lo + CHAIN_STRIKES_EACH_SIDE]:
            for rec in by_exp[tgt][s].values():
                keep[rec[0]] = rec
    return {"status": "ok", "timestamp": doc.get("timestamp"), "ts_epoch": chain_ts(doc), "receipt_t": receipt_t, "underlying": und, "expiries": expiries,
            "options": [keep[k] for k in sorted(keep)]}


def book_state(doc: Any, receipt_t: float) -> dict:
    """Touch, sizes, the top 5 levels per side, the book's own timestamp and the receipt time of a CLOB ``/book`` reply. Crossed books are flagged, never repaired."""
    if not isinstance(doc, dict):
        return {"ok": False, "receipt_t": receipt_t}

    def lv(key: str) -> list[tuple[float, float]]:
        out = []
        for x in doc.get(key) or []:
            try:
                p, s = float(x["price"]), float(x["size"])
            except (KeyError, TypeError, ValueError):
                continue
            if s > 0:
                out.append((p, s))
        return out

    bids = sorted(lv("bids"), key=lambda z: -z[0])
    asks = sorted(lv("asks"), key=lambda z: z[0])
    bb, ba = (bids[0] if bids else None), (asks[0] if asks else None)
    return {"ok": True, "receipt_t": receipt_t, "book_ts": doc.get("timestamp"), "bid": bb[0] if bb else None, "bid_size": bb[1] if bb else None, "ask": ba[0] if ba else None,
            "ask_size": ba[1] if ba else None, "crossed": bool(bb and ba and bb[0] >= ba[0]), "bids": bids[:BOOK_LEVELS], "asks": asks[:BOOK_LEVELS], "tick": c12.num(doc.get("tick_size"))}


# =====================================================================================================================================================
# Sources (injectable) and transports
# =====================================================================================================================================================


def ext_transport(timeout: float = 60.0):
    """Keyless GET with a browser-like user agent, JSON accept header and redirects followed (CBOE's CDN answers 307 to its API host)."""
    import httpx  # noqa: PLC0415

    client = httpx.Client(timeout=timeout, headers={"User-Agent": EXT_UA, "Accept": "application/json"}, follow_redirects=True)

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


class Sources:
    """Polymarket requests through ``pm`` (<= 2 rps), CBOE / Yahoo / Nasdaq through ``ext`` (<= 1 rps). Receipt times are taken after each reply."""

    def __init__(self, pm, ext, clock: Callable[[], float] = time.time):
        self.pm, self.ext, self.clock = pm, ext, clock

    def search(self, q: str, page: int) -> Any:
        st, data = self.pm.get(SEARCH_URL, {"q": q, "events_status": "active", "limit_per_type": SEARCH_LIMIT, "page": page})
        if st != 200:
            raise cm.ApiError(f"public-search status {st}")
        return data

    def book(self, token: str) -> tuple[Any, float]:
        st, doc = self.pm.get(CLOB_BOOK, {"token_id": token}, max_retries=2)
        rt = self.clock()
        return (doc if st == 200 else None), rt

    def chain(self, sym: str) -> tuple[int, Any, float]:
        st, doc = self.ext.get(CBOE_URL.format(sym), {}, max_retries=1)
        return st, doc, self.clock()

    def yahoo_daily(self, sym: str, p1: float, p2: float) -> Any:
        st, doc = self.ext.get(YAHOO_CHART + sym, {"interval": "1d", "period1": int(p1), "period2": int(p2), "includePrePost": "false"}, max_retries=2)
        if st != 200:
            raise cm.ApiError(f"yahoo {sym} status {st}")
        return doc

    def earnings(self, day: str) -> Any:
        st, doc = self.ext.get(NASDAQ_EARNINGS, {"date": day}, max_retries=2)
        if st != 200:
            raise cm.ApiError(f"nasdaq earnings status {st}")
        return doc

    def dividends(self, sym: str, kind: str) -> Any:
        st, doc = self.ext.get(NASDAQ_DIVIDENDS.format(sym), {"assetclass": "stocks" if kind == "equity" else "etf"}, max_retries=2)
        if st != 200:
            raise cm.ApiError(f"nasdaq dividends status {st}")
        return doc

    def gamma_markets(self, ids: list[str]) -> list[dict]:
        st, rows = self.pm.get(hb.GAMMA_MARKETS, {"id": list(ids), "closed": "true", "limit": c12.LOOKUP_PER_REQUEST})
        if st != 200 or not isinstance(rows, list):
            raise cm.ApiError(f"gamma markets status {st}")
        return rows


def yahoo_closes(doc: Any) -> list[tuple[str, float]]:
    """(ET date, close) of a Yahoo chart reply (daily bars), finite closes only."""
    try:
        r = doc["chart"]["result"][0]
        ts, cl = r.get("timestamp") or [], r["indicators"]["quote"][0].get("close") or []
    except (KeyError, IndexError, TypeError):
        return []
    out = []
    for t, c in zip(ts, cl, strict=False):
        v = c12.num(c)
        if math.isfinite(v) and t is not None:
            out.append((et_day(float(t)), v))
    return sorted(dict(out).items())


def earnings_rows(doc: Any, day: str, symbols: set[str]) -> list[list]:
    """(date, symbol, time) of the Nasdaq earnings calendar rows of the frame's symbols (nothing else of the reply is kept)."""
    rows = ((doc or {}).get("data") or {}).get("rows") if isinstance(doc, dict) else None
    return sorted([day, str(r.get("symbol")), str(r.get("time") or "")] for r in rows or [] if isinstance(r, dict) and str(r.get("symbol")) in symbols)


def dividend_dates(doc: Any) -> list[str]:
    """Ex-dividend dates (ISO) of the Nasdaq dividend list (raw public data, kept; the declared ex-dividend rule reads the chain)."""
    rows = (((doc or {}).get("data") or {}).get("dividends") or {}).get("rows") if isinstance(doc, dict) else None
    out = []
    for r in rows or []:
        try:
            out.append(datetime.strptime(str(r.get("exOrEffDate")), "%m/%d/%Y").date().isoformat())
        except (TypeError, ValueError, AttributeError):
            continue
    return sorted(set(out))


def dividend_reply_ok(doc: Any) -> bool:
    """True iff a Nasdaq dividend reply carries a ``data.dividends`` section (an empty / null ``rows`` is a valid "no dividend announced"); a wrong asset class or an
    error reply has ``data`` null and is NOT a valid reply (the ticker stays unknown)."""
    data = doc.get("data") if isinstance(doc, dict) else None
    return bool(isinstance(data, dict) and isinstance(data.get("dividends"), dict))


def dividend_kind(ticker: str) -> str:
    return "etf" if ticker.upper() in ETF_TICKERS else "equity"


def fetch_dividends(src, ticker: str) -> list[str]:
    """Ex-dividend dates of one ticker (Nasdaq, keyless): the frozen ETF list is asked as ``etf``, everything else as ``stocks`` and, if that reply carries no
    dividend section, once more as ``etf`` (amendment O3). Raises ``cm.ApiError`` if neither reply is valid (the ticker is then unknown, never "none")."""
    kinds = ("etf",) if dividend_kind(ticker) == "etf" else ("equity", "etf")
    for kind in kinds:
        doc = src.dividends(ticker, kind)
        if dividend_reply_ok(doc):
            return dividend_dates(doc)
    raise cm.ApiError(f"nasdaq dividends {ticker}: no dividend section")


# =====================================================================================================================================================
# The collector (q0261): one idempotent call
# =====================================================================================================================================================


def _wjson_gz(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(doc, sort_keys=True, default=float).encode(), mtime=0))
    tmp.replace(path)


def _rjson_gz(path: Path) -> Any:
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def _record(root: Path, man: dict, path: Path) -> None:
    from . import h5_seal  # noqa: PLC0415

    man.setdefault("file_sha256", {})[Path(path).relative_to(root).as_posix()] = h5_seal.sha256_file(path)


def run_checkpoint(root: Path, day: str, label: str, t_sched: float, src: Sources, *, rules_sha: str, sleep=time.sleep) -> dict:
    """One checkpoint: frame -> chains (first) -> book read 1 for every member -> book read 2 (each >= 60 s after that member's first read). Written to
    ``raw/<day>/<HHMM>.json.gz``. Members beyond MAX_MEMBERS (seeded rank) and underlyings beyond MAX_CHAINS are counted, not read."""
    t0 = src.clock()
    stats: dict = {}
    events = discover(src, stats)
    ev_rows, members, reasons = [], [], Counter()
    for ev in events:
        p = parse_event(ev)
        if p is None:
            continue
        row, mems = p
        ev_rows.append(row)
        if row["template"] == "weekly":
            reasons["event excluded: weekly"] += 1
        for m in mems:
            why = member_status(m, day, t0)
            if why:
                reasons[why] += 1
                continue
            members.append(m)
    members.sort(key=lambda m: c12.rank(CAP_SEED, m["market_id"]))
    if len(members) > MAX_MEMBERS:
        reasons["unavailable (collection cap)"] += len(members) - MAX_MEMBERS
        members = members[:MAX_MEMBERS]
    syms = sorted({m["cboe"] for m in members})
    if len(syms) > MAX_CHAINS:
        drop = set(syms[MAX_CHAINS:])
        reasons["unavailable (chain cap)"] += sum(1 for m in members if m["cboe"] in drop)
        members = [m for m in members if m["cboe"] not in drop]
        syms = syms[:MAX_CHAINS]
    chains = {}
    for s in syms:
        root_ = next(m["root"] for m in members if m["cboe"] == s)
        needs = sorted({(m["K"], m["settle"]) for m in members if m["cboe"] == s})
        try:
            st, doc, rt = src.chain(s)
        except RuntimeError:
            st, doc, rt = None, None, src.clock()
        chains[s] = chain_subset(doc, root_, needs, rt) if st == 200 else {"status": f"http {st}", "receipt_t": rt}
    books: dict[str, list] = {m["market_id"]: [] for m in members}
    first_rt: dict[str, float] = {}
    for rnd in (0, 1):
        for m in members:
            if rnd == 1:
                wait = first_rt.get(m["market_id"], 0.0) + BOOK_GAP_S - src.clock()
                if wait > 0:
                    sleep(wait)
            try:
                doc, rt = src.book(m["token_yes"])
            except RuntimeError:
                doc, rt = None, src.clock()
            if rnd == 0:
                first_rt[m["market_id"]] = rt
            books[m["market_id"]].append(book_state(doc, rt))
    rec = {"version": "cb12-opt-ckpt-v1", "rules_sha256": rules_sha, "day": day, "checkpoint": label, "t_sched": t_sched, "t_start": t0, "t_end": src.clock(),
           "events": ev_rows, "members": members, "member_reasons": dict(reasons), "search": stats, "chains": chains, "books": books}
    path = root / "raw" / day / f"{label}.json.gz"
    _wjson_gz(path, rec)
    return {"path": path, "n_members": len(members), "n_chains": len(chains), "reasons": dict(reasons)}


def run_daily(root: Path, day: str, src: Sources) -> dict:
    """Once per session: Yahoo daily bars BEFORE the day (features), Nasdaq earnings rows for the frame symbols over [day, max settlement] (<= 45 days), Nasdaq
    ex-dividend dates per equity / ETF underlying (indices are cash-settled and exempt). Symbols = the underlyings of the day's checkpoint files. The file of session S is
    what the units of the NEXT session read for earnings and ex-dividend dates (amendment O3: nothing fetched after t is used for a unit at t)."""
    mems = []
    for p in sorted((root / "raw" / day).glob("*.json.gz")):
        mems += _rjson_gz(p).get("members") or []
    unds = {(m["yahoo"], m["ticker"], m["cboe"]) for m in mems}
    out: dict = {"day": day, "yahoo": {}, "earnings": [], "dividends": {}, "errors": [], "fetched_t_start": src.clock(), "earnings_symbols": []}
    d0 = et_epoch(day, 0, 0)
    for ysym, _tk, _cb in sorted(unds):
        try:
            out["yahoo"][ysym] = yahoo_closes(src.yahoo_daily(ysym, d0 - YAHOO_FEATURE_DAYS * DAY, d0))
        except (cm.ApiError, RuntimeError) as exc:
            out["errors"].append(f"yahoo {ysym}: {exc}"[:120])
    symbols = {tk for _y, tk, _c in unds}
    out["earnings_symbols"] = sorted(symbols)
    last = max((m["settle"] for m in mems), default=day)
    last = min(last, day_add(day, EARNINGS_MAX_DAYS))
    d = day
    while d <= last:
        if is_session(d):
            try:
                out["earnings"] += earnings_rows(src.earnings(d), d, symbols)
            except (cm.ApiError, RuntimeError) as exc:
                out["errors"].append(f"earnings {d}: {exc}"[:120])
        d = day_add(d, 1)
    for _ysym, tk, cb in sorted(unds):
        if cb.startswith("_"):
            continue
        try:
            out["dividends"][tk] = fetch_dividends(src, tk)
        except (cm.ApiError, RuntimeError) as exc:
            out["errors"].append(f"dividends {tk}: {exc}"[:120])
    out["fetched_t_end"] = src.clock()
    path = root / "daily" / f"{day}.json.gz"
    _wjson_gz(path, out)
    return {"path": path, "n_yahoo": len(out["yahoo"]), "n_earnings_rows": len(out["earnings"]), "errors": len(out["errors"])}


def settled_members(root: Path, today: str) -> dict[str, dict[str, dict]]:
    """{settlement date: {market id: member row}} over every checkpoint file, for settlement dates before ``today`` (ET)."""
    out: dict[str, dict[str, dict]] = {}
    for p in sorted((root / "raw").glob("*/*.json.gz")):
        for m in _rjson_gz(p).get("members") or []:
            if m["settle"] and m["settle"] < today:
                out.setdefault(m["settle"], {})[m["market_id"]] = m
    return out


def run_outcomes(root: Path, now: float, src: Sources, state: dict) -> list[str]:
    """Guarded post-settlement step: per settlement date d < today (ET), the Yahoo close of d (implemented as "fetched on a later ET date than d", disclosed) and the Gamma resolution of every
    member, written ONLY to ``outcomes_guarded/<d>/{yahoo_close,gamma}.csv.gz`` (rewritten whole as rows accumulate). Final when complete or 7 days after d
    (the rest unresolved, counted). Nothing of the replies is kept elsewhere."""
    today = et_day(now)
    done = []
    for d, mems in sorted(settled_members(root, today).items()):
        st = state.setdefault("outcomes", {}).setdefault(d, {})
        if st.get("final"):
            continue
        gdir = root / "outcomes_guarded" / d
        gdir.mkdir(parents=True, exist_ok=True)
        cp = gdir / "yahoo_close.csv.gz"
        closes = {r["symbol"]: r for r in c12.read_csv_gz(cp)} if cp.exists() else {}
        for ysym in sorted({m["yahoo"] for m in mems.values()} - set(closes)):
            try:
                bars = dict(yahoo_closes(src.yahoo_daily(ysym, et_epoch(d, 0, 0) - 5 * DAY, now)))
            except (cm.ApiError, RuntimeError):
                continue
            if d in bars and today > d:
                closes[ysym] = {"symbol": ysym, "settle": d, "close": bars[d]}
        if closes:
            cp.write_bytes(hb._gz_csv_bytes(CLOSE_COLUMNS, [[closes[k][c] for c in CLOSE_COLUMNS] for k in sorted(closes)]))
        gp = gdir / "gamma.csv.gz"
        have = {r["market_id"]: r for r in c12.read_csv_gz(gp)} if gp.exists() else {}
        todo = sorted(k for k in mems if gamma_yes(have.get(k)) is None)  # not yet resolved (or unclean): asked again at every outcome step until final (amendment O3)
        for i in range(0, len(todo), c12.LOOKUP_PER_REQUEST):
            try:
                rows = src.gamma_markets(todo[i:i + c12.LOOKUP_PER_REQUEST])
            except (cm.ApiError, RuntimeError):
                break
            for g in rows:
                gid = str(g.get("id")) if isinstance(g, dict) else ""
                if gid not in todo or not g.get("closed"):
                    continue
                statuses = g.get("umaResolutionStatuses")
                have[gid] = {"market_id": gid, "settle": d, "yes_index": mems[gid]["yes_index"], "outcome_prices": json.dumps(c12.listish(g.get("outcomePrices"))),
                             "uma_status": str(g.get("umaResolutionStatus") or (statuses if statuses else ""))}
        if have:
            gp.write_bytes(hb._gz_csv_bytes(OUTCOME_COLUMNS, [[have[k][c] for c in OUTCOME_COLUMNS] for k in sorted(have)]))
        ysyms = {m["yahoo"] for m in mems.values()}
        complete = set(closes) >= ysyms and all(gamma_yes(have.get(k)) is not None for k in mems)
        late = now >= et_epoch(d, 0, 0) + OUTCOME_MAX_DAYS * DAY
        st.update(t=now, n_closes=len(closes), n_symbols=len(ysyms), n_resolved=sum(1 for k in mems if gamma_yes(have.get(k)) is not None), n_members=len(mems), final=bool(complete or late),
                  unresolved=0 if complete else (len(ysyms - set(closes)) + sum(1 for k in mems if gamma_yes(have.get(k)) is None)))
        done.append(d)
    return done


def root_size_bytes(root: Path) -> int:
    return sum(f.stat().st_size for f in Path(root).rglob("*") if f.is_file())


def opt_live_tick(root: Path, *, now: float, src: Sources, rules_sha: str, frozen_epoch: float, disk_check: Callable[[], None] | None = None, root_cap_bytes: int | None = None,
                  sleep=time.sleep) -> dict:
    """One idempotent collector call (cron every 5 minutes on weekdays). Order: a due checkpoint; else the daily step; else (at most every 3 h) the outcome step.
    A disk refusal at a due checkpoint is recorded as "unavailable (host disk)" (time-critical), elsewhere it is ``NotNow`` (exit 75). Concurrent calls: the second
    one returns ``busy``. ``root_cap_bytes`` (the declared 0.3 GB) is enforced on the collector root's own size and refuses exactly like a full host disk."""
    root = c12.require_output_root(Path(root))
    root.mkdir(parents=True, exist_ok=True)
    lock = open(root / ".lock", "w")  # noqa: SIM115
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return {"status": "busy"}
    try:
        sp, mp = root / "state.json", root / "manifest.json"
        state = json.loads(sp.read_text()) if sp.exists() else {"days": {}, "outcomes": {}}
        man = json.loads(mp.read_text()) if mp.exists() else {"run_id": RUN, "kind": "cb12_opt_live", "evidence_role": "prospective", "file_sha256": {}}
        day = et_day(now)
        dst = state["days"].setdefault(day, {"ckpt": {}})
        out: dict = {"status": "idle", "day": day}

        def _check() -> None:  # host disk check + the collector root's own cap
            if disk_check is not None:
                disk_check()
            if root_cap_bytes is not None and root_size_bytes(root) > root_cap_bytes:
                raise NotNow(f"collector root exceeds its {root_cap_bytes} byte cap")

        if now < frozen_epoch:
            raise Refused("opt-live runs only after the O freeze")
        due = [(lab, t) for lab, t in checkpoint_epochs(day) if t <= now < t + CHECKPOINT_WINDOW_S and lab not in dst["ckpt"]]
        if due:
            lab, t = due[0]
            try:
                _check()
            except NotNow as exc:
                dst["ckpt"][lab] = {"status": "unavailable (host disk)", "t": now, "why": str(exc)[:200]}
                out = {"status": "checkpoint_unavailable_disk", "checkpoint": lab}
            else:
                r = run_checkpoint(root, day, lab, t, src, rules_sha=rules_sha, sleep=sleep)
                _record(root, man, r["path"])
                dst["ckpt"][lab] = {"status": "ok", "t": now, "n_members": r["n_members"], "n_chains": r["n_chains"]}
                out = {"status": "checkpoint", "checkpoint": lab, "n_members": r["n_members"], "n_chains": r["n_chains"]}
        elif is_session(day) and now >= et_epoch(day, *DAILY_FROM_ET) and "daily" not in dst and any((root / "raw" / day).glob("*.json.gz")):
            _check()
            r = run_daily(root, day, src)
            _record(root, man, r["path"])
            dst["daily"] = {"t": now, "n_yahoo": r["n_yahoo"], "n_earnings_rows": r["n_earnings_rows"], "errors": r["errors"]}
            out = {"status": "daily", **dst["daily"]}
        elif now - float(state.get("outcomes_t", 0.0)) >= OUTCOME_EVERY_S:
            _check()
            done = run_outcomes(root, now, src, state)
            state["outcomes_t"] = now
            for d in done:
                for f in ("yahoo_close.csv.gz", "gamma.csv.gz"):
                    p = root / "outcomes_guarded" / d / f
                    if p.exists():
                        _record(root, man, p)
            out = {"status": "outcomes", "dates": done}
        for lab, t in checkpoint_epochs(day):  # missed checkpoints are recorded once their window has passed (never back-filled)
            if lab not in dst["ckpt"] and now >= t + CHECKPOINT_WINDOW_S:
                dst["ckpt"][lab] = {"status": "unavailable (collection)", "t": now}
        man.update(updated_utc=cm.iso(now), rules_sha256=rules_sha, requests=man.get("requests", 0) + src.pm.requests + src.ext.requests, status="collecting")
        src.pm.requests = src.ext.requests = 0
        cm.write_json_atomic(sp, state)
        cm.write_json_atomic(mp, man)
        return out
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


# =====================================================================================================================================================
# Anchor (frozen; challenger item 13)
# =====================================================================================================================================================


def _mid(bid, ask) -> float | None:
    b, a = c12.num(bid), c12.num(ask)
    if not (math.isfinite(b) and math.isfinite(a)) or b <= 0 or a <= 0 or a < b:
        return None
    return (a + b) / 2.0


def _spread_ok(bid, ask) -> bool:
    m = _mid(bid, ask)
    return m is not None and m > 0 and (c12.num(ask) - c12.num(bid)) <= OPT_SPREAD_MAX * m


def chain_calls(chain: dict) -> dict[str, dict[float, list]]:
    out: dict[str, dict[float, list]] = {}
    for rec in chain.get("options") or []:
        if rec[1] == "C":
            out.setdefault(rec[2], {})[float(rec[3])] = rec
    return out


def bracket(strikes: list[float], K: float) -> tuple[float, float] | None:
    """Listed ``K``: the listed strikes immediately below and above (a central difference at K); otherwise the nearest listed strikes with K_lo < K < K_hi."""
    below = [s for s in strikes if s < K]
    above = [s for s in strikes if s > K]
    if not below or not above:
        return None
    return max(below), min(above)


def bs_call(S: float, K: float, sigma: float, T: float) -> float:
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)
    v = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * v * v) / v
    return S * norm.cdf(d1) - K * norm.cdf(d1 - v)


def phi_d2(S: float, K: float, sigma: float, T: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return math.nan
    v = sigma * math.sqrt(T)
    return float(norm.cdf((math.log(S / K) - 0.5 * v * v) / v))


def session_hours(t0: float, expiry: str) -> float:
    """Regular-session hours remaining from ``t0`` to the expiry's close (half sessions count to 13:00 ET)."""
    tot, d = 0.0, et_day(t0)
    while d <= expiry:
        if is_session(d):
            o, c = et_epoch(d, *OPEN_ET), et_epoch(d, *close_hm(d))
            tot += max(0.0, c - max(o, t0)) / HOUR
        d = day_add(d, 1)
    return tot


def time_to_expiry(t0: float, expiry: str, convention: str) -> float:
    if convention == "act365":
        return (et_epoch(expiry, *CLOSE_ET) - t0) / (365.0 * DAY)
    if convention == "trading_hours":
        return session_hours(t0, expiry) / (252.0 * 6.5)
    raise Refused(f"unknown iv time convention {convention!r}")


def anchor(chain: dict, K: float, d: str, convention: str | None) -> dict:
    """q for one (K, d): the direct call-spread digital if a listed expiry equals d (both call mids two-sided), else Phi(d2) with the iv interpolated linearly in
    strike at K from the nearest expiry >= d (spot = the chain's underlying price, r = 0, T under the declared convention; no convention -> excluded). Returns
    {q, type, spread_ok, reason}."""
    calls = chain_calls(chain)
    exps = sorted(chain.get("expiries") or calls)
    t0 = c12.num(chain.get("ts_epoch"))
    if d in exps and d in calls:
        strikes = sorted(calls[d])
        br = bracket(strikes, K)
        if br is None:
            return {"q": None, "type": "direct", "reason": "excluded: no anchor"}
        lo, hi = calls[d][br[0]], calls[d][br[1]]
        mlo, mhi = _mid(lo[4], lo[5]), _mid(hi[4], hi[5])
        if mlo is None or mhi is None:
            return {"q": None, "type": "direct", "reason": "excluded: no anchor"}
        q = min(1.0, max(0.0, (mlo - mhi) / (br[1] - br[0])))
        return {"q": q, "type": "direct", "spread_ok": _spread_ok(lo[4], lo[5]) and _spread_ok(hi[4], hi[5]), "reason": ""}
    tgt = next((e for e in exps if e >= d), None)
    if tgt is None or tgt not in calls:
        return {"q": None, "type": "phi_d2", "reason": "excluded: no anchor"}
    if not convention or convention not in CONVENTIONS:
        return {"q": None, "type": "phi_d2", "reason": "excluded: phi(d2) without convention"}
    strikes = sorted(calls[tgt])
    if K in calls[tgt]:
        legs = [calls[tgt][K]]
        iv = c12.num(legs[0][8])
    else:
        br = bracket(strikes, K)
        if br is None:
            return {"q": None, "type": "phi_d2", "reason": "excluded: no anchor"}
        legs = [calls[tgt][br[0]], calls[tgt][br[1]]]
        i0, i1 = c12.num(legs[0][8]), c12.num(legs[1][8])
        iv = i0 + (i1 - i0) * (K - br[0]) / (br[1] - br[0])
    S = c12.num((chain.get("underlying") or {}).get("current_price"))
    if not (math.isfinite(iv) and iv > 0 and math.isfinite(S) and S > 0 and math.isfinite(t0)):
        return {"q": None, "type": "phi_d2", "reason": "excluded: no anchor"}
    q = phi_d2(S, K, iv, time_to_expiry(t0, tgt, convention))
    if not math.isfinite(q):
        return {"q": None, "type": "phi_d2", "reason": "excluded: no anchor"}
    return {"q": q, "type": "phi_d2", "spread_ok": all(_spread_ok(x[4], x[5]) for x in legs), "reason": ""}


def previous_daily(daily: dict[str, dict], day: str) -> dict | None:
    """The daily file of the session before ``day`` (None if absent)."""
    return daily.get(prev_session(day))


def exdiv_status(prev: dict | None, ticker: str, cboe: str, t: float, d: str) -> str:
    """Amended rule (section 11, O3): cash-settled indices (CBOE symbol ``_...``) are exempt (''); otherwise the ex-dividend dates are those of the PREVIOUS session's
    Nasdaq file (fetched and stored before t); a ticker without a valid entry there is unknown (excluded). An ex-date in (ET date of t, d] -> 'excluded: ex-dividend'.
    Returns '' (no ex-dividend in (t, d] or exempt), 'excluded: ex-dividend' or 'excluded: ex-dividend unknown'."""
    if cboe.startswith("_"):
        return ""
    fetched = c12.num((prev or {}).get("fetched_t_end"))
    divs = ((prev or {}).get("dividends") or {}).get(ticker)
    if prev is None or divs is None or not (math.isfinite(fetched) and fetched < t):
        return "excluded: ex-dividend unknown"
    return "excluded: ex-dividend" if any(et_day(t) < x <= d for x in divs) else ""


def realised_vol(closes: list[tuple[str, float]], before: str, n: int = RV_DAYS) -> float:
    """Annualised 20-day realised vol of daily log closes dated strictly before ``before`` (sqrt 252); NaN without 21 closes."""
    c = [v for dd, v in closes if dd < before and v > 0][-(n + 1):]
    if len(c) < n + 1:
        return math.nan
    r = np.diff(np.log(np.array(c, float)))
    return float(np.std(r, ddof=1) * math.sqrt(252.0))


def earnings_flag(rows: list[list] | None, ticker: str, t: float, d: str) -> bool | None:
    """True if an earnings release of ``ticker`` falls in (t, close of d]. The unit's day is D = ET date of t (t is at or after 11:00 ET). A pre-market report dated
    dd counts iff D < dd <= d; an after-hours report iff D <= dd < d; a report of unknown time iff D <= dd <= d (conservative). None when the unit-day calendar was
    not collected."""
    if rows is None:
        return None
    day = et_day(t)
    for dd, sym, tm in rows:
        if sym != ticker:
            continue
        tml = str(tm).lower()
        if "pre" in tml:
            hit = day < dd <= d
        elif "after" in tml:
            hit = day <= dd < d
        else:
            hit = day <= dd <= d
        if hit:
            return True
    return False


# =====================================================================================================================================================
# Windows (counts only: clusters and dates with a tight unit; never results)
# =====================================================================================================================================================


def is_tight(b1: dict) -> bool:
    return bool(b1 and b1.get("ok") and b1.get("bid") is not None and b1.get("ask") is not None and not b1.get("crossed") and b1["ask"] - b1["bid"] <= TIGHT_SPREAD + 1e-12)


def iter_checkpoints(root: Path) -> Iterable[dict]:
    for p in sorted((Path(root) / "raw").glob("*/*.json.gz")):
        yield _rjson_gz(p)


def tight_by_date(root: Path) -> dict[str, set[str]]:
    """{settlement date: tickers with >= 1 tight unit (first read two-sided, uncrossed, spread <= 4.5c)}."""
    out: dict[str, set[str]] = {}
    for rec in iter_checkpoints(root):
        for m in rec.get("members") or []:
            bl = (rec.get("books") or {}).get(m["market_id"]) or []
            if bl and is_tight(bl[0]):
                out.setdefault(m["settle"], set()).add(m["ticker"])
    return out


def window_bounds(tight: dict[str, set[str]], start: str, today: str, cap: str) -> dict:
    """The window from ``start``: closes at the first settled date D at which the clusters (ticker, d) with a tight unit over [start, D] reach 60 AND the distinct
    dates with a tight unit reach 30; else at ``cap`` once settled (power: fewer than 30 dates -> O "not run (power)")."""
    clusters = dates = 0
    last = None
    for d in sessions_between(start, cap):
        if d >= today:
            return {"start": start, "end": None, "closed": False, "clusters": clusters, "dates": dates, "last_settled": last}
        last = d
        n = len(tight.get(d, set()))
        clusters += n
        dates += int(n > 0)
        if clusters >= WINDOW_MIN_CLUSTERS and dates >= WINDOW_MIN_DATES:
            return {"start": start, "end": d, "closed": True, "clusters": clusters, "dates": dates, "power_ok": True, "by": "counts"}
    return {"start": start, "end": last, "closed": True, "clusters": clusters, "dates": dates, "power_ok": bool(dates >= WINDOW_MIN_DATES), "by": "cap"}


def windows(root: Path, frozen_epoch: float, now: float) -> dict:
    tight = tight_by_date(root)
    today = et_day(now)
    w1 = window_bounds(tight, window1_start(frozen_epoch), today, WINDOW1_CAP)
    w2 = window_bounds(tight, next_session(w1["end"]), today, WINDOW2_CAP) if w1["closed"] and w1["end"] else {"closed": False, "start": None}
    return {"w1": w1, "w2": w2, "counts_only": True}


def window_dates(win: dict) -> list[str]:
    if not win.get("closed") or not win.get("end"):
        raise NotNow("the window has not closed yet (pending)")
    return sessions_between(win["start"], win["end"])


# =====================================================================================================================================================
# Units (features only; outcomes are attached by screen / rep through the guarded accessor)
# =====================================================================================================================================================


def load_daily(root: Path) -> dict[str, dict]:
    out = {}
    for p in sorted((Path(root) / "daily").glob("*.json.gz")):
        out[p.name.split(".")[0]] = _rjson_gz(p)
    return out


def build_units(root: Path, dates: list[str], convention: str | None) -> tuple[list[dict], dict]:
    """(units, checkpoint counts) for members whose settlement date is in ``dates``. Label order: first read missing -> crossed -> not tight -> chain missing ->
    chain timestamp not before the first receipt -> anchor exclusions (no anchor, phi(d2) without convention, option spread, q range, ex-dividend) -> second read.
    ``o2_ok`` marks every unit that passed all of these up to the anchor exclusions (first-read tight + valid anchor): O2 does not depend on the second read (taken
    >= 60 s after the decision), which only O1 needs. ``m2_raw`` = the raw second-read mid whenever that read is two-sided and uncrossed (any label; for the m_prev
    placebo). Features only: the anchor, mids, touch, realised vol from bars dated before the unit's day, and the earnings flag and ex-dividend dates from the PREVIOUS
    session's daily file (amendment O3)."""
    dset = set(dates)
    daily = load_daily(root)
    units: list[dict] = []
    ck = Counter()
    for rec in iter_checkpoints(root):
        ck["files"] += 1
        dly = daily.get(rec["day"]) or {}
        prev = previous_daily(daily, rec["day"])
        for m in rec.get("members") or []:
            if m["settle"] not in dset:
                continue
            bl = (rec.get("books") or {}).get(m["market_id"]) or []
            b1 = bl[0] if bl else {}
            b2 = bl[1] if len(bl) > 1 else {}
            t = c12.num(b1.get("receipt_t"))
            m2_raw = (b2["bid"] + b2["ask"]) / 2.0 if (b2.get("ok") and b2.get("bid") is not None and b2.get("ask") is not None and not b2.get("crossed")) else None
            u = {"market_id": m["market_id"], "event_id": m["event_id"], "ticker": m["ticker"], "settle": m["settle"], "day": rec["day"], "ckpt": rec["checkpoint"], "t": t,
                 "K": m["K"], "yes_index": m["yes_index"], "template": m["template"], "fee_rate": m["fee_rate"], "yahoo": m["yahoo"], "cluster": f"{m['ticker']}|{m['settle']}", "m2_raw": m2_raw, "o2_ok": False}
            if not b1.get("ok") or not math.isfinite(t):
                units.append({**u, "label": "unavailable (first read)"})
                continue
            if b1.get("crossed"):
                units.append({**u, "label": "crossed"})
                continue
            if not is_tight(b1):
                units.append({**u, "label": "not tight"})
                continue
            u.update(m1=(b1["bid"] + b1["ask"]) / 2.0, a_yes=b1["ask"], b_yes=b1["bid"], ask_size=b1["ask_size"], bid_size=b1["bid_size"])
            ch = (rec.get("chains") or {}).get(m["cboe"]) or {}
            if ch.get("status") != "ok":
                units.append({**u, "label": "unavailable (chain)"})
                continue
            if not (math.isfinite(c12.num(ch.get("ts_epoch"))) and ch["ts_epoch"] < t):
                units.append({**u, "label": "unavailable (chain timestamp)"})
                continue
            an = anchor(ch, m["K"], m["settle"], convention)
            u["anchor_type"] = an["type"]
            if an["q"] is None:
                units.append({**u, "label": an["reason"]})
                continue
            if not an.get("spread_ok"):
                units.append({**u, "label": "excluded: option spread", "q": an["q"]})
                continue
            if not (Q_MIN <= an["q"] <= Q_MAX):
                units.append({**u, "label": "excluded: q range", "q": an["q"]})
                continue
            ex = exdiv_status(prev, m["ticker"], m["cboe"], t, m["settle"])
            if ex:
                units.append({**u, "label": ex, "q": an["q"]})
                continue
            u["o2_ok"] = True
            if m2_raw is None:
                units.append({**u, "label": "unavailable (second read)", "q": an["q"]})
                continue
            S = c12.num((ch.get("underlying") or {}).get("current_price"))
            sig = realised_vol([tuple(x) for x in (dly.get("yahoo") or {}).get(m["yahoo"], [])], rec["day"])
            T = time_to_expiry(ch["ts_epoch"], m["settle"], convention) if convention in CONVENTIONS else time_to_expiry(ch["ts_epoch"], m["settle"], "act365")
            units.append({**u, "label": "available", "q": an["q"], "m2": m2_raw, "q_rv": phi_d2(S, m["K"], sig, T) if math.isfinite(sig) else math.nan,
                          "earnings": earnings_flag(prev.get("earnings") if prev and m["ticker"] in (prev.get("earnings_symbols") or []) else None, m["ticker"], t, m["settle"])})
    return units, dict(ck)


def attach_mprev(units: list[dict]) -> None:
    """``m_prev`` = the RAW second-read mid (two-sided, uncrossed) of the same market at the previous checkpoint, whatever that unit's label (13:00 -> 11:00, 15:00 -> 13:00,
    11:00 -> the previous session's 15:00); None when that checkpoint has no such read (those units drop from the placebo only, counted)."""
    by = {(u["market_id"], u["day"], u["ckpt"]): u for u in units if u.get("m2_raw") is not None}
    for u in units:
        if u["ckpt"] == "1300":
            key = (u["market_id"], u["day"], "1100")
        elif u["ckpt"] == "1500":
            key = (u["market_id"], u["day"], "1300")
        else:
            key = (u["market_id"], prev_session(u["day"]), "1500")
        p = by.get(key)
        u["m_prev"] = p["m2_raw"] if p is not None else None


# =====================================================================================================================================================
# Guarded outcomes (screen-O: window 1 dates only; rep-O: window 2 dates only)
# =====================================================================================================================================================


def open_outcomes(root: Path, dates: list[str], job: str, window: str, *, frozen_epoch: float | None = None, now: float | None = None) -> tuple[dict, dict]:
    """({(symbol, d): close}, {market id: gamma row}) for the given settlement dates. Only ``screen-O`` (window ``w1``) and ``rep-O`` (window ``w2``) may open them;
    the window is recomputed HERE from the collected files (``frozen_epoch``) and the requested dates must be a subset of its settlement dates (a closed window is
    required); every read is appended to ACCESS_LOG.jsonl."""
    if (job, window) not in (("screen-O", "w1"), ("rep-O", "w2")):
        raise Refused(f"O outcomes of {window} may not be opened by {job!r}")
    if frozen_epoch is None:
        raise Refused("O outcomes need the freeze epoch to recompute the window")
    win = windows(Path(root), frozen_epoch, time.time() if now is None else now)[window]
    allowed = set(window_dates(win))
    extra = sorted(set(dates) - allowed)
    if extra:
        raise Refused(f"requested settlement dates outside {window} (first {extra[0]}); refused")
    closes, gam = {}, {}
    for d in dates:
        gdir = Path(root) / "outcomes_guarded" / d
        for name in ("yahoo_close.csv.gz", "gamma.csv.gz"):
            p = gdir / name
            if not p.exists():
                continue
            c12.log_access(Path(root), job, f"outcomes_guarded/{d}/{name}")
            for r in c12.read_csv_gz(p):
                if name == "yahoo_close.csv.gz":
                    closes[(r["symbol"], r["settle"])] = c12.num(r["close"])
                else:
                    gam[r["market_id"]] = r
    return closes, gam


def gamma_yes(row: dict | None) -> float | None:
    """Venue resolution of YES: 1 / 0 (clean), 0.5 (50-50), None (unresolved or unclean; excluded from O2, counted)."""
    if not row:
        return None
    v = [c12.num(x) for x in c12.listish(row.get("outcome_prices"))]
    yi = int(row.get("yes_index") or 0)
    st = str(row.get("uma_status") or "").lower()
    if len(v) != 2 or not all(math.isfinite(x) for x in v) or "resolved" not in st:
        return None
    if abs(v[yi] - 1) < 1e-9 and abs(v[1 - yi]) < 1e-9:
        return 1.0
    if abs(v[yi]) < 1e-9 and abs(v[1 - yi] - 1) < 1e-9:
        return 0.0
    if abs(v[yi] - 0.5) < 1e-9 and abs(v[1 - yi] - 0.5) < 1e-9:
        return 0.5
    return None


def attach_outcomes(units: list[dict], closes: dict, gam: dict) -> None:
    for u in units:
        c = closes.get((u["yahoo"], u["settle"]))
        u["y"] = None if c is None or not math.isfinite(c) else (1.0 if c > u["K"] else (0.0 if c < u["K"] else 0.5))
        u["y_gamma"] = gamma_yes(gam.get(u["market_id"]))


# =====================================================================================================================================================
# Statistics
# =====================================================================================================================================================


def slope_pseudo(y, x, w=None) -> tuple[np.ndarray, float]:
    """(pseudo-values, slope) of the (W)LS slope of ``y`` on ``x`` with intercept: v_i = b + n w_i (x_i - x_w) e_i / S_xx (mean(v) = b; the clustered variance of v
    is the cluster sandwich of b)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    wt = np.ones_like(x) if w is None else np.asarray(w, float)
    n = len(x)
    if n < 3 or wt.sum() <= 0:
        return np.full(n, math.nan), math.nan
    xm, ym = (wt * x).sum() / wt.sum(), (wt * y).sum() / wt.sum()
    xc = x - xm
    sxx = float((wt * xc * xc).sum())
    if sxx <= 0:
        return np.full(n, math.nan), math.nan
    b = float((wt * xc * (y - ym)).sum() / sxx)
    e = (y - ym) - b * xc
    return b + n * wt * xc * e / sxx, b


def ways(us: list[dict]) -> dict:
    return {"settle": [u["settle"] for u in us], "ticker_settle": [u["cluster"] for u in us]}


def cluster_weights(us: list[dict]) -> np.ndarray:
    n = Counter(u["cluster"] for u in us)
    return np.array([1.0 / n[u["cluster"]] for u in us], float)


def o1_slope(us: list[dict], *, x_override: np.ndarray | None = None) -> dict:
    """O1: WLS slope of ``Y - m2`` on ``q - m1`` (each (ticker, settlement) cluster weight 1); one-sided p = max over the settlement-date and (ticker, settlement)
    ways (small-G rule; >= 100 units and >= 30 clusters)."""
    if len(us) < 3:
        return {"beta": math.nan, "p": 1.0, "testable": False, "n": len(us)}
    y = np.array([u["y"] - u["m2"] for u in us], float)
    x = np.array([u["q"] - u["m1"] for u in us], float) if x_override is None else x_override
    v, b = slope_pseudo(y, x, cluster_weights(us))
    if not math.isfinite(b):
        return {"beta": b, "p": 1.0, "testable": False, "n": len(us)}
    cp = c12.cluster_p(v, ways(us))
    return {"beta": b, "p": cp["p"], "testable": cp["testable"], "n": cp["n"], "ways": cp["ways"], "pseudo": v}


def o1_signflip(us: list[dict], *, n_draws: int = c12.PLACEBO_DRAWS, seed: int = SEED_SIGNFLIP) -> dict:
    """Binding calibration placebo: one coin per settlement date flips ``q - m1``; judged on the p threshold alone (advance rate <= 1.5%)."""
    rng = np.random.default_rng(seed)
    dates = sorted({u["settle"] for u in us})
    gi = np.array([dates.index(u["settle"]) for u in us])
    x = np.array([u["q"] - u["m1"] for u in us], float)
    ps = []
    for _ in range(n_draws):
        coin = rng.choice([-1.0, 1.0], size=len(dates))
        ps.append(o1_slope(us, x_override=x * coin[gi])["p"])
    return {**c12.placebo_advance_rate(ps), "note": "O1 settlement-date sign-flip calibration", "seed": seed}


def o1_attribution(us: list[dict], census_cor: float | None = None, use_census_cor: bool = False) -> dict:
    """Joint WLS of ``Y - m2`` on ``q - m1`` and ``q_RV - m1`` (units with a realised-vol digital); credit "option-implied" only if the ``q - m1`` coefficient keeps
    >= half its solo value on the same units; cor > 0.9 -> "not identifiable". The screen passes the CENSUS value of cor(q - m1, q_RV - m1) (the label is decided on it, as
    section CB12-O says "at the census"; ``use_census_cor``); without it (rep, window 2) the correlation of the tested units is used (declared)."""
    sub = [u for u in us if math.isfinite(c12.num(u.get("q_rv")))]
    if len(sub) < 10:
        return {"label": "not identifiable", "reason": "too few units with a realised-vol digital", "n": len(sub)}
    y = np.array([u["y"] - u["m2"] for u in sub])
    x1 = np.array([u["q"] - u["m1"] for u in sub])
    x2 = np.array([u["q_rv"] - u["m1"] for u in sub])
    w = cluster_weights(sub)
    cor = float(np.corrcoef(x1, x2)[0, 1]) if x1.std() > 0 and x2.std() > 0 else math.nan
    src = "tested units"
    if use_census_cor:
        cor, src = (math.nan if census_cor is None else float(census_cor)), "census"
    if not math.isfinite(cor) or cor > COR_MAX:
        return {"label": "not identifiable", "cor": cor, "cor_source": src, "n": len(sub)}
    X = np.column_stack([np.ones(len(sub)), x1, x2])
    W = np.sqrt(w)
    coef = np.linalg.lstsq(X * W[:, None], y * W, rcond=None)[0]
    solo = slope_pseudo(y, x1, w)[1]
    ok = bool(math.isfinite(solo) and solo > 0 and coef[1] >= 0.5 * solo)
    return {"label": "option-implied" if ok else "not option-implied", "cor": cor, "joint_beta_q": float(coef[1]), "joint_beta_rv": float(coef[2]), "solo_beta_q": solo, "cor_source": src, "n": len(sub)}


def availability(units: list[dict], need_outcome: str | None = None, *, o2: bool = False) -> float:
    """Available share of eligible units (section 2.6 iv). O1: available = label "available" (needs the second read); O2 (``o2``): available = ``o2_ok`` (first-read tight
    + valid anchor; no second read). Eligible = the available units + every "unavailable (...)" unit that is not available (+ units without the needed outcome)."""
    def good(u: dict) -> bool:
        return bool(u.get("o2_ok")) if o2 else u["label"] == "available"

    ok = [u for u in units if good(u)]
    avail = [u for u in ok if need_outcome is None or u.get(need_outcome) is not None]
    elig = len(ok) + sum(1 for u in units if u["label"].startswith("unavailable") and not good(u))
    return len(avail) / elig if elig else 0.0


def _holds(us: list[dict], floor: float) -> bool:
    r = o1_slope(us)
    return bool(r["testable"] and r["p"] < c12.GATE_P and r["beta"] >= floor)


def o1_test(units: list[dict], *, earnings_identified: bool, placebo: bool = True, n_draws: int = c12.PLACEBO_DRAWS, ckpt_share: float = 1.0, census_cor: float | None = None,
            use_census_cor: bool = False) -> dict:
    """``ckpt_share`` = the share of scheduled checkpoints actually collected (missed ones are "unavailable (collection)" / "(host disk)"); it multiplies the unit
    availability so a missed checkpoint counts against the 60% rule (amendment O3)."""
    av = availability(units, "y") * ckpt_share
    us = [u for u in units if u["label"] == "available" and u.get("y") is not None]
    res: dict = {"test": "O1", "label": LABEL_O, "n": len(us), "availability_share": av, "checkpoint_share": ckpt_share, "unit_labels": dict(Counter(u["label"] for u in units))}
    if av < c12.AVAIL_MIN:
        return {**res, "p": 1.0, "testable": False, "advance": False, "effect": None, "verdict": "not testable (availability)"}
    base = o1_slope(us)
    res.update(beta=base["beta"], effect=base["beta"], p=base["p"], testable=base["testable"], ways=base.get("ways"), floor_ok=bool(math.isfinite(base["beta"]) and base["beta"] >= O1_FLOOR))
    if not base["testable"] or len(us) < c12.MIN_UNITS:
        return {**res, "advance": False, "verdict": "not testable (units / clusters)"}
    rob: dict = {}
    direct = [u for u in us if u.get("anchor_type") == "direct"]
    rob["direct_digital_sign"] = bool(len(direct) >= 3 and o1_slope(direct)["beta"] > 0)
    for ck in ("1100", "1300", "1500"):
        sub = [u for u in us if u["ckpt"] == ck]
        rob[f"checkpoint_{ck}_sign"] = bool(len(sub) >= 3 and o1_slope(sub)["beta"] > 0)
    dates = sorted({u["settle"] for u in us})
    half = set(dates[:len(dates) // 2])
    h1, h2 = [u for u in us if u["settle"] in half], [u for u in us if u["settle"] not in half]
    rob["halves_sign"] = bool(len(h1) >= 3 and len(h2) >= 3 and o1_slope(h1)["beta"] > 0 and o1_slope(h2)["beta"] > 0)
    for way, key in (("settle", "settle"), ("ticker_settle", "cluster")):
        keep = c12.top_k_drop_mask(base["pseudo"], [u[key] for u in us], c12.TOP_DROP)
        sub = [u for u, k in zip(us, keep, strict=True) if k]
        rob[f"top5_{way}_drop"] = _holds(sub, O1_FLOOR) if len(sub) >= c12.MIN_UNITS else False
    if earnings_identified:
        ne = [u for u in us if u.get("earnings") is False]
        rob["earnings_excluded_sign"] = bool(len(ne) >= 3 and o1_slope(ne)["beta"] > 0)
    else:
        res["earnings"] = "earnings not identified (the primary includes all units; the earnings robustness is not applicable)"
    plc = o1_signflip(us, n_draws=n_draws) if placebo else None
    rob_ok = all(v is True for v in rob.values())
    per_mkt = {u["market_id"]: (u["y"], u["y_gamma"]) for u in us if u.get("y_gamma") is not None}  # agreement counted per market, not per unit
    agree = list(per_mkt.values())
    share = float(np.mean([a == b for a, b in agree])) if agree else None
    res.update(robustness=rob, robustness_ok=rob_ok, placebo=plc, attribution=o1_attribution(us, census_cor, use_census_cor), gamma_agreement={"share": share, "n": len(agree), "min": AGREE_MIN,
               "label": "settlement basis" if share is not None and share < AGREE_MIN else None})
    ok = bool(base["p"] < c12.GATE_P and res["floor_ok"] and rob_ok and (plc is None or plc["holds"]))
    res.update(stage1_pass=ok, early_holm_ok=c12.early_stage1_ok(base["p"]), advance=bool(ok and c12.early_stage1_ok(base["p"])), holm_pending=bool(ok and not c12.early_stage1_ok(base["p"])))
    res["verdict"] = "advance (early Holm)" if res["advance"] else ("pending the full step-down (p in [0.005, 0.01))" if res["holm_pending"] else "no advance")
    return res


def o2_trades(units: list[dict], *, signal: str = "q", cost: float = 0.0) -> list[dict]:
    """Each market's FIRST tight checkpoint with a valid anchor (``o2_ok``: no second read needed) with ``signal - a_YES >= 4c`` (buy YES at the first-read ask) or ``(1 - signal) - a_NO >= 4c`` (buy NO at
    ``a_NO = 1 - b_YES``); fee ``r a (1 - a)``, ``r = max(feeSchedule.rate, 0.04)``; paid on the Gamma resolution (unresolved -> excluded, counted)."""
    out, seen = [], set()
    for u in sorted((u for u in units if u.get("o2_ok")), key=lambda z: (z["market_id"], z["t"])):
        if u["market_id"] in seen:
            continue
        s = u.get(signal)
        if s is None or not math.isfinite(c12.num(s)):
            continue
        a_no = 1.0 - u["b_yes"]
        side = "yes" if s - u["a_yes"] >= EDGE - 1e-12 else ("no" if (1.0 - s) - a_no >= EDGE - 1e-12 else None)
        if side is None:
            continue
        seen.add(u["market_id"])
        a = (u["a_yes"] if side == "yes" else a_no) + cost
        r = max(c12.num(u["fee_rate"]) if math.isfinite(c12.num(u["fee_rate"])) else 0.0, FEE_FLOOR)
        yg = u.get("y_gamma")
        pay = None if yg is None else (yg if side == "yes" else 1.0 - yg)
        size = u["ask_size"] if side == "yes" else u["bid_size"]
        out.append({**u, "side": side, "a": a, "size": size, "net": None if pay is None else pay - a - r * a * (1.0 - a)})
    return out


def o2_test(units: list[dict], *, placebo: bool = True, ckpt_share: float = 1.0) -> dict:
    av = availability(units, "y_gamma", o2=True) * ckpt_share
    tr = o2_trades(units)
    paid = [t for t in tr if t["net"] is not None]
    res: dict = {"test": "O2", "label": LABEL_O, "n": len(paid), "n_trades": len(tr), "unresolved_trades": len(tr) - len(paid), "availability_share": av, "checkpoint_share": ckpt_share}
    if av < c12.AVAIL_MIN:
        return {**res, "p": 1.0, "testable": False, "advance": False, "effect": None, "verdict": "not testable (availability)"}
    v = np.array([t["net"] for t in paid], float)
    res.update(net_per_share=float(v.mean()) if len(v) else math.nan, effect=float(v.mean()) if len(v) else math.nan,
               capacity_shares_mean=float(np.mean([c12.num(t["size"]) for t in paid])) if paid else None)
    if len(v) < c12.MIN_UNITS:
        return {**res, "p": 1.0, "testable": False, "advance": False, "verdict": "not testable (units)"}
    cp = c12.cluster_p(v, ways(paid))
    floor_ok = bool(v.mean() >= O2_FLOOR)
    res.update(p=cp["p"], testable=cp["testable"], ways=cp["ways"], floor_ok=floor_ok)
    if not cp["testable"]:
        return {**res, "advance": False, "verdict": "not testable (clusters)"}
    rob: dict = {}
    c5 = [t["net"] for t in o2_trades(units, cost=O2_COST_ROBUST) if t["net"] is not None]
    rob["ask_plus_0.5c_net_positive"] = bool(c5 and float(np.mean(c5)) > 0)
    for way, key in (("settle", "settle"), ("ticker_settle", "cluster")):
        keep = c12.top_k_drop_mask(v, [t[key] for t in paid], c12.TOP_DROP)
        sub = [t for t, k in zip(paid, keep, strict=True) if k]
        if len(sub) >= c12.MIN_UNITS:
            c2 = c12.cluster_p(np.array([t["net"] for t in sub]), ways(sub))
            rob[f"top5_{way}_drop"] = bool(c2["testable"] and c2["p"] < c12.GATE_P and np.mean([t["net"] for t in sub]) >= O2_FLOOR)
        else:
            rob[f"top5_{way}_drop"] = False
    dates = sorted({t["settle"] for t in paid})
    half = set(dates[:len(dates) // 2])
    h1, h2 = [t["net"] for t in paid if t["settle"] in half], [t["net"] for t in paid if t["settle"] not in half]
    rob["halves_sign"] = bool(h1 and h2 and np.mean(h1) > 0 and np.mean(h2) > 0)
    plc = None
    if placebo:
        pt = [t for t in o2_trades([u for u in units if u.get("m_prev") is not None], signal="m_prev") if t["net"] is not None]
        pv = np.array([t["net"] for t in pt], float)
        pp = c12.cluster_p(pv, ways(pt))["p"] if len(pv) >= 2 else 1.0
        plc = {"note": "O2 previous-checkpoint m_prev placebo (must not pass p < 0.01)", "p": pp, "n": len(pv), "holds": bool(pp >= c12.GATE_P), "advance_rate": None, "n_draws": 1,
               "dropped_without_m_prev": sum(1 for u in units if u.get("o2_ok") and u.get("m_prev") is None)}
    rob_ok = all(x is True for x in rob.values())
    res.update(robustness=rob, robustness_ok=rob_ok, placebo=plc)
    ok = bool(cp["p"] < c12.GATE_P and floor_ok and rob_ok and (plc is None or plc["holds"]))
    res.update(stage1_pass=ok, early_holm_ok=c12.early_stage1_ok(cp["p"]), advance=bool(ok and c12.early_stage1_ok(cp["p"])), holm_pending=bool(ok and not c12.early_stage1_ok(cp["p"])))
    res["verdict"] = "advance (early Holm)" if res["advance"] else ("pending the full step-down (p in [0.005, 0.01))" if res["holm_pending"] else "no advance")
    return res


# =====================================================================================================================================================
# Census (q0262, counts only), screen (q0263), rep (q0264)
# =====================================================================================================================================================


def _strip(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("y", "y_gamma")}


def collection_counts(root: Path, win: dict) -> dict:
    """Scheduled vs collected checkpoints over the window's collection days (regular sessions from the window start to its end), from ``state.json``: ``ok``,
    "unavailable (collection)", "unavailable (host disk)" and "not recorded". Counts only; ``share`` = ok / scheduled (1.0 with nothing scheduled)."""
    sp = Path(root) / "state.json"
    days = (json.loads(sp.read_text()) if sp.exists() else {}).get("days") or {}
    c: Counter = Counter()
    for d in sessions_between(win["start"], win["end"]):
        for lab, _t in checkpoint_epochs(d):
            c["scheduled"] += 1
            st = ((days.get(d) or {}).get("ckpt") or {}).get(lab) or {}
            c[str(st.get("status") or "not recorded")] += 1
    out = dict(c)
    out["share"] = c["ok"] / c["scheduled"] if c["scheduled"] else 1.0
    return out


def census_o(root: Path, win: dict, convention: str | None) -> dict:
    """Window-1 census: counts by ticker, settlement date, checkpoint, template, anchor type, tightness and exclusion label; GO; cor(q - m1, q_RV - m1). Opens no
    outcome file (unit-tested); refuses before window 1 closed."""
    dates = window_dates(win)
    require_outcomes_final(root, dates)
    units, ck = build_units(root, dates, convention)
    coll = collection_counts(root, win)
    avail = [u for u in units if u["label"] == "available"]
    sessions = sorted({u["day"] for u in units})
    clusters = {u["cluster"] for u in avail}
    sdates = {u["settle"] for u in avail}
    go = {"tight_units": len(avail), "clusters": len(clusters), "dates": len(sdates), "sessions": len(sessions), "per_session": len(avail) / len(sessions) if sessions else 0.0,
          "min": GO_MIN}
    go["pass"] = bool(go["tight_units"] >= GO_MIN["tight_units"] and go["clusters"] >= GO_MIN["clusters"] and go["dates"] >= GO_MIN["dates"] and go["per_session"] >= GO_MIN["per_session"])
    x1 = np.array([u["q"] - u["m1"] for u in avail if math.isfinite(c12.num(u.get("q_rv")))])
    x2 = np.array([u["q_rv"] - u["m1"] for u in avail if math.isfinite(c12.num(u.get("q_rv")))])
    cor = float(np.corrcoef(x1, x2)[0, 1]) if len(x1) > 2 and x1.std() > 0 and x2.std() > 0 else None
    out = {"version": "cb12-census-O-v1", "counts_only": True, "label": LABEL_O, "window": win, "iv_convention": convention, "checkpoint_files": ck,
           "unit_labels": dict(Counter(u["label"] for u in units)), "by_ticker": dict(Counter(u["ticker"] for u in avail)), "by_settlement": dict(sorted(Counter(u["settle"] for u in avail).items())),
           "by_checkpoint": dict(Counter(u["ckpt"] for u in avail)), "by_template": dict(Counter(u["template"] for u in avail)), "by_anchor": dict(Counter(u.get("anchor_type") for u in avail)),
           "availability_share": availability(units), "availability_share_o2": availability(units, o2=True), "collection": coll,
           "availability_share_incl_missed_checkpoints": availability(units) * coll["share"], "availability_share_o2_incl_missed_checkpoints": availability(units, o2=True) * coll["share"],
           "O2_eligible_units": sum(1 for u in units if u.get("o2_ok")), "GO": go, "cor_q_qrv": cor, "attribution_identifiable": bool(cor is not None and cor <= COR_MAX)}
    if not win.get("power_ok", True) or go["dates"] < GO_MIN["dates"]:
        out["label_O"] = "not run (power)"
    elif not go["pass"]:
        out["label_O"] = "not testable (GO)"
    else:
        out["label_O"] = None
    return out


def require_outcomes_final(root: Path, dates: list[str]) -> None:
    """Census, screen and rep wait (``NotNow``) until the outcome step is final for every settlement date of the window that has members (reads the state's flags,
    never the outcome files)."""
    sp = Path(root) / "state.json"
    st = (json.loads(sp.read_text()) if sp.exists() else {}).get("outcomes") or {}
    have = set(settled_members(Path(root), "9999-12-31"))
    pending = [d for d in dates if d in have and not (st.get(d) or {}).get("final")]
    if pending:
        raise NotNow(f"outcome step not final for {len(pending)} settlement date(s) of the window (first {pending[0]}); pending")


def not_run_result(label: str) -> dict:
    return {"p": 1.0, "testable": False, "advance": False, "verdict": label, "label": LABEL_O, "effect": None, "n": 0}


def screen_o(root: Path, census: dict, convention: str | None, *, earnings_identified: bool, frozen_epoch: float, now: float | None = None) -> dict:
    lab = census.get("label_O")
    if lab:
        return {"O1": not_run_result(lab), "O2": not_run_result(lab), "label": LABEL_O, "census_label": lab}
    win = census["window"]  # the census' ``window`` IS the window-1 dict
    dates = window_dates(win)
    units, _ = build_units(root, dates, convention)
    attach_mprev(units)
    closes, gam = open_outcomes(root, dates, "screen-O", "w1", frozen_epoch=frozen_epoch, now=now)
    attach_outcomes(units, closes, gam)
    share = (census.get("collection") or {}).get("share", 1.0)
    return {"O1": o1_test(units, earnings_identified=earnings_identified, ckpt_share=share, census_cor=census.get("cor_q_qrv"), use_census_cor=True),
            "O2": o2_test(units, ckpt_share=share), "label": LABEL_O, "census_label": None}


def rep_o(root: Path, win2: dict, convention: str | None, tests: tuple[str, ...], *, earnings_identified: bool, k2: int | None = None, frozen_epoch: float, now: float | None = None) -> dict:
    dates = window_dates(win2)
    units, _ = build_units(root, dates, convention)
    attach_mprev(units)
    closes, gam = open_outcomes(root, dates, "rep-O", "w2", frozen_epoch=frozen_epoch, now=now)
    attach_outcomes(units, closes, gam)
    share = collection_counts(root, win2)["share"]
    out: dict = {"label": LABEL_O, "k2": k2, "window": win2, "collection": collection_counts(root, win2)}
    for t in tests:
        r = o1_test(units, earnings_identified=earnings_identified, ckpt_share=share) if t == "O1" else o2_test(units, ckpt_share=share)
        r["stage2_early_alpha_over_10"] = c12.early_stage2_ok(r.get("p"))
        r["stage2_pass_alpha_over_k"] = bool(r.get("p", 1.0) < (c12.STAGE_ALPHA / k2 if k2 else c12.STAGE_ALPHA / c12.STAGE2_K_MAX) and r.get("floor_ok") and r.get("robustness_ok")
                                             and (r.get("placebo") or {}).get("holds", False))
        out[f"{t}_rep"] = r
    return out


# =====================================================================================================================================================
# Smoke (q0260): guard fixtures offline; live checkpoint dry run online (no unit kept); the iv time-convention choice
# =====================================================================================================================================================


def convention_check(chains: dict[str, dict]) -> dict:
    """Recompute ``theo`` from ``iv`` for 20 near-the-money calls (2-60 calendar days to expiry, |K/S - 1| <= 3%, theo >= 0.05, <= 4 per underlying; nearest the
    money first) under (a) ACT/365 to the expiry's 16:00 ET close and (b) remaining regular-session hours / (252 x 6.5), Black-Scholes with r = 0 and the chain's
    underlying price. A convention matches if |model - theo| <= 1% of theo for >= 80% of them; (a) if both match; "none" if neither (Phi(d2) units excluded)."""
    cands = []
    for sym, ch in sorted(chains.items()):
        S, t0 = c12.num((ch.get("underlying") or {}).get("current_price")), c12.num(ch.get("ts_epoch"))
        if not (math.isfinite(S) and S > 0 and math.isfinite(t0)):
            continue
        rows = []
        for rec in ch.get("all_calls") or []:
            K, iv, theo = float(rec[3]), c12.num(rec[8]), c12.num(rec[9])
            days = (_d(rec[2]) - _d(et_day(t0))).days
            if CONV_DAYS[0] <= days <= CONV_DAYS[1] and abs(K / S - 1) <= CONV_MONEYNESS and math.isfinite(iv) and iv > 0 and math.isfinite(theo) and theo >= CONV_MIN_THEO:
                rows.append((abs(K / S - 1), sym, rec[2], K, iv, theo, S, t0))
        cands += sorted(rows)[:CONV_PER_UNDERLYING]
    pick = sorted(cands)[:CONVENTION_N]
    share = {}
    for conv in CONVENTIONS:
        ok = [abs(bs_call(S, K, iv, time_to_expiry(t0, e, conv)) - theo) <= CONVENTION_TOL * theo for _m, _s, e, K, iv, theo, S, t0 in pick]
        share[conv] = float(np.mean(ok)) if ok else 0.0
    if len(pick) < CONVENTION_N:
        choice = "none"
    elif share["act365"] >= CONVENTION_SHARE:
        choice = "act365"
    elif share["trading_hours"] >= CONVENTION_SHARE:
        choice = "trading_hours"
    else:
        choice = "none"
    return {"n_options": len(pick), "match_share": share, "tolerance": CONVENTION_TOL, "share_min": CONVENTION_SHARE, "choice": choice}


def smoke_offline(ctx: dict) -> dict:
    """Guard fixtures (no network): census refusing the outcome accessor, window-2 outcomes refused to the screen, cross_venue_live, both templates, the weekly
    exclusion, the listed-K central difference, DST of the checkpoints across 2026-11-01, and m_prev at 11:00 ET."""
    res = []
    for fn in (lambda: open_outcomes(Path("x/h12_opt_live"), [], "census", "w1"), lambda: open_outcomes(Path("x/h12_opt_live"), [], "screen-O", "w2"),
               lambda: c12.refuse_path(Path("x/cross_venue_live/a.npz")), lambda: c12.require_output_root(Path("x/creative_batch11/a"))):
        try:
            fn()
            res.append(False)
        except Refused:
            res.append(True)
    t1 = classify_title("NVIDIA (NVDA) closes above ___ on October 21?") == ("daily", "NVDA")
    t2 = classify_title("Will Tesla (TSLA) close above ___ end of October?") == ("month_end", "TSLA")
    t3 = classify_title("Will Apple (AAPL) finish week of October 23 above ___?")[0] == "weekly"
    ch = {"options": [["X", "C", "2026-10-21", k, 0.9 * c, 1.1 * c, 1, 1, 0.3, c, 0.5, 1, 1, ""] for k, c in ((95.0, 6.0), (100.0, 3.0), (105.0, 1.0))], "expiries": ["2026-10-21"],
          "ts_epoch": 0.0, "underlying": {"current_price": 100.0}}
    cd = anchor(ch, 100.0, "2026-10-21", None)
    central = bool(cd["type"] == "direct" and abs(cd["q"] - 0.5) < 1e-9)
    dst = bool(datetime.fromtimestamp(checkpoint_epochs("2026-10-30")[0][1], UTC).hour == 15 and datetime.fromtimestamp(checkpoint_epochs("2026-11-02")[0][1], UTC).hour == 16)
    us = [{"market_id": "m", "day": "2026-10-19", "ckpt": "1500", "m2_raw": 0.4}, {"market_id": "m", "day": "2026-10-20", "ckpt": "1100", "m2_raw": 0.5}]
    attach_mprev(us)
    mp = bool(us[1]["m_prev"] == 0.4)
    ok = bool(all(res) and t1 and t2 and t3 and central and dst and mp)
    return {"guards_fixture_O": {"pass": ok, "refusals": res, "templates": [t1, t2, t3], "central_difference": central, "dst": dst, "m_prev_1100": mp}}


def smoke_online(lim, ctx: dict) -> dict:
    """One live checkpoint dry run (no unit kept): both frame regexes on the frozen searches, rule flags, the CBOE chain per underlying (timestamp older than the
    receipt and < 1 h old), the iv time-convention check, two book reads on up to 4 members, Yahoo daily bars keyless (O1 outcome and q_RV source), the Gamma closed=true
    lookup, Nasdaq ex-dividend lists keyless (ETF and stock), Nasdaq earnings keyless, and whether the chain carries any dividend field (informational). Counts and booleans only."""
    src = ctx.get("o_sources") or Sources(lim, lim)
    stats: dict = {}
    events = discover(src, stats)
    tmpl = Counter()
    members = []
    flags = Counter()
    now = src.clock()
    day = et_day(now)
    for ev in events:
        p = parse_event(ev)
        if p is None:
            continue
        tmpl[p[0]["template"] or "other"] += 1
        for m in p[1]:
            for k, v in m["flags"].items():
                flags[k] += int(v)
            if not member_status(m, day, now):
                members.append(m)
    syms = sorted({m["cboe"] for m in members})[:MAX_CHAINS]
    chains, chk = {}, {}
    for s in syms:
        root_ = next(m["root"] for m in members if m["cboe"] == s)
        try:
            st, doc, rt = src.chain(s)
        except RuntimeError:
            st, doc, rt = None, None, src.clock()
        if st != 200:
            chk[s] = {"status": st, "ok": False}
            continue
        sub = chain_subset(doc, root_, [(m["K"], m["settle"]) for m in members if m["cboe"] == s], rt)
        sub["all_calls"] = [[o.get("option"), "C", p_[1], p_[3], o.get("bid"), o.get("ask"), None, None, o.get("iv"), o.get("theo")] for o in (doc.get("data") or {}).get("options") or []
                            if isinstance(o, dict) and (p_ := parse_option(o.get("option"))) and p_[0] == root_ and p_[2] == "C"]
        chains[s] = sub
        age = rt - c12.num(sub.get("ts_epoch"))
        chk[s] = {"status": 200, "n_options_kept": len(sub["options"]), "age_s": age, "ts_ok": bool(math.isfinite(age) and 0 < age < HOUR),
                  "dividend_field": any(DIV_KEY_RE.search(str(k)) for k in (doc.get("data") or {})), "ok": True}
    conv = convention_check(chains)
    for ch in chains.values():
        ch.pop("all_calls", None)
    bk = {}
    for m in members[:4]:
        reads = []
        for _ in range(2):
            doc, rt = src.book(m["token_yes"])
            reads.append(book_state(doc, rt))
        bk[m["market_id"][-4:]] = {"ok": all(r["ok"] for r in reads), "two_sided": all(r.get("bid") is not None and r.get("ask") is not None for r in reads)}
    yh = {}
    for sym in YAHOO_PROBES:
        try:
            bars = yahoo_closes(src.yahoo_daily(sym, now - 45 * DAY, now))
            yh[sym] = {"n_bars": len(bars), "last": bars[-1][0] if bars else None, "ok": bool(len([b for b in bars if b[0] < day]) >= RV_DAYS + 1 and bars and bars[-1][0] >= prev_session(day))}
        except (cm.ApiError, RuntimeError):
            yh[sym] = {"ok": False}
    try:  # the closed=true Gamma lookup the outcome step uses: the request must be accepted (a list; open markets are not returned by design)
        rows = src.gamma_markets([m["market_id"] for m in members[:3]]) if members else None
        gm_ok = isinstance(rows, list)
    except (cm.ApiError, RuntimeError):
        gm_ok = False
    dv = {}
    for sym in DIV_PROBES:
        try:
            dv[sym] = {"n_dates": len(fetch_dividends(src, sym)), "ok": True}
        except (cm.ApiError, RuntimeError):
            dv[sym] = {"ok": False}
    try:
        e = src.earnings(next_session(day))
        earn_ok = bool(isinstance(e, dict) and isinstance((e.get("data") or {}).get("rows"), list))
    except (cm.ApiError, RuntimeError):
        earn_ok = False
    return {"o_frame_regex": {"pass": bool(tmpl.get("daily", 0) >= 1), "templates": dict(tmpl), "n_events": len(events), "search_capped": stats.get("search_capped", 0),
                              "rule_flags_true": dict(flags), "n_members_in_frame": len(members), "rule": "daily template >= 1 hit (O rests on it); month-end hits recorded"},
            "o_chain": {"pass": bool(chk and all(v["ok"] for v in chk.values())), "per": {k: {kk: vv for kk, vv in v.items() if kk != "age_s"} for k, v in chk.items()}},
            "o_chain_timestamp": {"pass": bool(chk and all(v.get("ts_ok") for v in chk.values() if v["ok"])), "ages_s": sorted(v["age_s"] for v in chk.values() if v["ok"]),
                                  "rule": "chain timestamp read as UTC must be older than the receipt and < 1 h old during the session"},
            "o_iv_convention_checked": {"pass": bool(conv["n_options"] >= CONVENTION_N), **conv},
            "o_yahoo_keyless": {"pass": bool(yh and all(v["ok"] for v in yh.values())), "per": yh, "rule": "daily bars keyless: >= 21 bars before today and the latest bar >= the previous session (O1 outcome and q_RV source)"},
            "o_gamma_closed_lookup": {"pass": gm_ok, "rule": "the Gamma /markets?id=...&closed=true outcome lookup is accepted (status 200, a list); open markets are not returned by design"},
            "o_dividends_keyless": {"pass": bool(dv and all(v["ok"] for v in dv.values())), "per": dv, "rule": "Nasdaq ex-dividend list keyless with a dividend section for an ETF (assetclass etf) and a stock (stocks); the amended ex-dividend rule reads it"},
            "o_books": {"pass": bool(bk and all(v["ok"] for v in bk.values())), "per": bk},
            "o_earnings_keyless": {"pass": earn_ok, "note": "informational: earnings flagged only if this is true, else 'earnings not identified'"},
            "o_chain_dividend_field": {"pass": bool(chk and any(v.get("dividend_field") for v in chk.values() if v["ok"])),
                                       "note": "informational only (amendment O3: the ex-dividend rule no longer reads the chain; the CBOE delayed chain has no dividend field)"}}


def in_smoke_session(now: float) -> bool:
    day = et_day(now)
    return bool(is_regular(day) and et_epoch(day, *SMOKE_SESSION_ET[0]) <= now <= et_epoch(day, *SMOKE_SESSION_ET[1]))


def declared() -> dict:
    return {"frame": {"search": {"url": SEARCH_URL, "queries": list(SEARCH_QUERIES), "limit": SEARCH_LIMIT, "max_pages": SEARCH_MAX_PAGES, "events_status": "active"},
                      "month_end_re": MONTH_END_RE.pattern, "daily_re": DAILY_RE.pattern, "weekly_excluded_re": WEEKLY_RE.pattern,
                      "settlement": "title date (on <Month> <day>) or the month's last session (end of <Month>), year closest to endDate; > 3 days from endDate's ET date -> ambiguous (excluded)",
                      "listing": "createdAt <= t - 1 h", "underlyings": {"excluded": list(EXCLUDED_UNDERLYINGS), "index_cboe": INDEX_CBOE, "index_root": INDEX_ROOT, "index_yahoo": INDEX_YAHOO,
                                                                         "equity": "CBOE <TICKER>.json, option root = ticker"},
                      "rule_flags": {k: v.pattern for k, v in FLAG_RES.items()},
                      "rule_flags_use": "DESCRIPTIVE ONLY: stored booleans and the description sha256; no flag includes, excludes or weights a unit or enters a test (amendment O3)"},
            "collection": {"checkpoints_et": [f"{h:02d}:{m:02d}" for h, m in CHECKPOINTS_ET], "regular_sessions_only": True, "window_s": CHECKPOINT_WINDOW_S, "order": "frame -> chain -> book read 1 -> book read 2 (>= 60 s)",
                           "max_members": MAX_MEMBERS, "max_chains": MAX_CHAINS, "cap_rank_seed": CAP_SEED, "book_levels": BOOK_LEVELS, "chain_strikes_each_side": CHAIN_STRIKES_EACH_SIDE,
                           "daily": "Yahoo daily bars before the day; Nasdaq earnings rows of the frame symbols over [day, max settlement] (<= 45 d); Nasdaq ex-dividend dates per equity / ETF (ETF list frozen, else stocks then etf); the file of session S feeds the units of the NEXT session only",
                           "root_cap": "the collector root's own size is capped at --disk-cap-gb (0.3); beyond it a due checkpoint is 'unavailable (host disk)'",
                           "outcomes": "outcomes_guarded/<d>/ only: Yahoo close of d (implemented as fetched on a later ET date than d) and Gamma resolution (unresolved rows asked again every outcome step); final when complete or 7 days after d",
                           "missed": "unavailable (collection), never back-filled; host disk refusal at a due checkpoint -> unavailable (host disk)", "holidays": list(HOLIDAYS), "half_sessions": list(HALF_SESSIONS)},
            "anchor": {"direct": "listed expiry == d: (C(K_lo) - C(K_hi)) / (K_hi - K_lo) from two-sided call mids, clipped [0, 1]; listed K -> the strikes immediately below and above",
                       "phi_d2": "else Phi(d2), iv linear in strike at K from the nearest expiry >= d, spot = chain underlying price, r = 0, T under the smoke-chosen convention (none -> excluded)",
                       "conventions": list(CONVENTIONS), "convention_rule": {"n": CONVENTION_N, "tol": CONVENTION_TOL, "share": CONVENTION_SHARE, "moneyness": CONV_MONEYNESS, "days": list(CONV_DAYS),
                                                                             "min_theo": CONV_MIN_THEO, "per_underlying": CONV_PER_UNDERLYING, "tie": "act365"},
                       "exclusions": {"q_range": [Q_MIN, Q_MAX], "option_spread_max_share_of_mid": OPT_SPREAD_MAX, "ex_dividend": f"source {DIVIDEND_RULE}: an ex-date in (ET date of t, d] in the PREVIOUS session's Nasdaq file, or no valid entry there -> excluded; cash-settled indices (CBOE _SPX/_NDX/_RUT) exempt",
                                      "earnings": "flag only (primary includes all); robustness excludes flagged units if the smoke verified the calendar keyless"},
                       "chain_clock": "chain timestamp (UTC) < first book receipt"},
            "units": {"tight": f"both touches and spread <= {TIGHT_SPREAD} in the first read", "m1_m2": "mids of the first and second reads", "y_o1": "Yahoo close of d vs K (equal 0.5)",
                      "y_o2": "Gamma resolution (what the venue paid)", "availability_min": c12.AVAIL_MIN,
                      "q_rv": "Phi(d2) with the 20-day realised vol of Yahoo closes dated before the unit's day, T under the chosen convention (act365 if none was chosen)"},
            "o1": {"stat": "WLS slope of Y - m2 on q - m1, cluster (ticker, d) weight 1", "floor": O1_FLOOR, "ways": ["settle", "ticker_settle"], "placebo": f"settlement-date sign flip, seed {SEED_SIGNFLIP}",
                   "attribution": f"q_RV (20-day realised vol); joint coefficient >= half solo; cor > {COR_MAX} -> not identifiable (screen: the census value of cor(q - m1, q_RV - m1); rep: the tested units')",
                   "agreement": "Yahoo vs Gamma outcome agreement counted per market", "checkpoint_share": "scheduled checkpoints missed (unavailable (collection) / (host disk)) multiply the unit availability share", "robustness": "direct-digital; each checkpoint; earnings excluded (if identified); halves; top-5 per way"},
            "o2": {"eligibility": "first-read tight + valid anchor (o2_ok); the second read (>= 60 s after the decision) is for O1 only", "availability": "o2_ok units over o2_ok + unavailable units",
                   "rule": f"first tight checkpoint with q - a_YES >= {EDGE} or (1 - q) - a_NO >= {EDGE}", "fee": f"r a (1 - a), r = max(feeSchedule.rate, {FEE_FLOOR})", "floor": O2_FLOOR,
                   "robustness": f"+{O2_COST_ROBUST} on the ask; halves; top-5 per way", "placebo": "m_prev = the raw second-read mid (two-sided, uncrossed) of the same market at the previous checkpoint (13->11, 15->13, 11->previous session 15:00), whatever that unit's label; must not pass p < 0.01"},
            "windows": {"start": "first session >= 1 day after the O freeze (frozen_utc of the freeze entry)", "close": f">= {WINDOW_MIN_CLUSTERS} (ticker, d) clusters and >= {WINDOW_MIN_DATES} dates with a tight unit, settled",
                        "caps": [WINDOW1_CAP, WINDOW2_CAP], "power": "fewer than 30 dates by the cap -> not run (power), counted"},
            "gates": {"GO": GO_MIN, "agreement_min": AGREE_MIN}, "smoke": {"version": SMOKE_FAMILY_VERSION, "needs": list(SMOKE_NEEDS), "session_et": [list(x) for x in SMOKE_SESSION_ET]},
            "label": LABEL_O, "stage1": "p < 0.01, floor, binding placebo, robustness, early Holm at alpha / 10 (full step-down when O is final)",
            "rules_file_note": "the design's seals/cb12_opt_rules.json is part O of seals/cb12_rules.json (per-part hashing)"}
