# ruff: noqa: E501
"""CB12-E: earthquake running-count anchor (docs/research_lab/CREATIVE_BATCH_12.md CB12-E, section 10 items 1-3, 18-20). Rules part ``E``.

Frame and USGS catalogue (q0244), prices (q0245), census (q0266 per section 11 A2, counts only, gates GE and GEP), screen (q0253: E1 on Stage-1 units), the
prospective collector (q0257, ``quake-live``, cron at 10:00Z and 16:00Z outside the queue lanes) and the Stage-2 rep (q0258: E1-rep, E2). EXPLORATORY: no edge,
calibration or profitability claim. E1's primary outcome is computed from the USGS catalogue by the frozen rule parser, never read from Gamma; the Gamma outcome is in
``outcomes_guarded.csv.gz`` (opened only by the screen's agreement audit / Gamma-outcome robustness and by the rep's E2 payoff). A census path sees catalogue events
only before each unit's ``t - 72 h``. This module imports ``cb12_common`` and nothing from the other CB12 families.

Model (fitted only on catalogue events before 2024-09-01): for threshold m in {6.0, 6.5, 7.0, 7.5, 8.0}, monthly (30-day, non-overlapping) global counts from
1976-01-01 give lambda_m per day and a negative-binomial size k_m by the method of moments (variance <= mean -> Poisson). ``N_rem ~ NegBin(mean lambda tau, size
k tau / 30)``; ``c_t`` = events >= m inside the rule window and before ``t - 72 h``; ``tau`` = window end - max(window start, t - 72 h). E-a buckets:
``P(c_t + N_rem in bucket)``; E-b rungs: ``1 - P(N_rem = 0)`` (a rung already holding a usable event is "decided", excluded); E-c day maximum: the empirical share of
days 2000-01-01..2024-09-01 (M >= 4.5 catalogue, the rule's own day: UTC or ET) whose rounded maximum falls in the bucket.
"""

from __future__ import annotations

import fcntl
import gzip
import json
import math
import re
import time
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import nbinom, norm, poisson

from . import cb8_common as cm
from . import cb12_common as c12
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow

HOUR = 3600.0
DAY = 86400.0
TAG_IDS = (103038, 100184)  # Gamma "Earthquakes" and "earthquake"
E_WINDOW = ("2024-09-01", "2026-10-01")  # market endDate
FIT_START = "1976-01-01"
FIT_END = "2024-09-01"
ECDF_START = "2000-01-01"
CHECKPOINT_START = "2024-09-04T16:00:00Z"  # fit end + 72 h
CHECKPOINT_HOUR_UTC = 16
REG_LAG_S = 6 * HOUR
ALT_LAG_S = 48 * HOUR
LIST_BUFFER_S = HOUR
END_BUFFER_S = 6 * HOUR
FIDELITY = 60
CHUNK_DAYS = 14
PRICES_REQUEST_CAP = 15000
CAT_LAG_S = 72 * HOUR
CAT_LAG_ROBUST_S = 7 * DAY
AMBIG_BAND = 0.3
BIG_QUAKE = 7.5
BIG_QUAKE_DAYS = 30
THRESHOLDS = (6.0, 6.5, 7.0, 7.5, 8.0)
MONTH_DAYS = 30
E1_FLOOR = 0.25
E2_EDGE = 0.08
E2_FEE_FLOOR = 0.05
E2_FLOOR = 0.01
E2_COST_ROBUST = 0.005
GE_MIN = {"markets": 300, "events": 60, "weeks": 40, "components": 30}
PARSER_FAIL_MAX = 0.20
THIN_MAX = 0.30
GEP_LOADINGS = (0.3, 0.3, 0.4)  # ISO-week factor, window-component factor, idiosyncratic (variances)
GEP_MDE_MAX = 1.0
AGREE_MIN = 0.97
PLACEBO_SEED = 12107
SEED_GEP = 12122
LABEL_E = "L1 historical (E1); Stage 2 prospective (L2)"
FRAME_RUN = "h12_quake"
LIVE_RUN = "h12_quake_live"
FRAME_STATUS = "quake_frame_complete"
PRICES_STATUS = "quake_prices_complete"
FRAME_OUTPUT_CAP_GB = 0.03
PRICES_OUTPUT_CAP_GB = 0.01
LIVE_OUTPUT_CAP_GB = 0.01
# USGS FDSN (keyless; <= 1 rps): M >= 6.0 1976-2026 in 5 requests, M >= 4.5 2000-2026 in 2-year chunks with a count first (a chunk over 20,000 is halved)
USGS_QUERY = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_COUNT = "https://earthquake.usgs.gov/fdsnws/event/1/count"
USGS_MAX_ROWS = 20000
USGS_RPS = 1.0
CAT_M6_CHUNKS = (("1976-01-01", "1986-01-01"), ("1986-01-01", "1996-01-01"), ("1996-01-01", "2006-01-01"), ("2006-01-01", "2016-01-01"), ("2016-01-01", "2026-10-01"))
CAT_M45_FROM = ("2000-01-01", "2026-10-01")
CAT_M45_CHUNK_YEARS = 2
CAT_COLUMNS = ["time_ms", "lat", "lon", "mag", "mag_type", "status", "updated_ms"]
# ---- frozen parser (written from out-of-window events only: endDate >= 2026-10-01, read 2026-10-19; text only, no price or outcome) ---------------
USGS_RE = re.compile(r"(?i)\bUSGS\b|United States Geological Survey")
GLOBAL_RE = re.compile(r"(?i)anywhere on Earth|anywhere in the world|\bglobally\b|\bworldwide\b")
REGIONAL_RE = re.compile(r"\bWhere will\b|\b(?:in|near)\s+(?!\d{4}\b)(?!the\b)(?!(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)[A-Z][A-Za-z]+|\bCalifornia\b|\bLos Angeles\b|\bLA\b|\bJapan\b|\bAlaska\b")
EA_Q_RE = re.compile(r"(?i)^Will there be (.+?) earthquakes? of (?:magnitude )?(\d+(?:\.\d)?) or (?:above|higher)")
EB_Q_RE = re.compile(r"(?i)\b(?:another|an?)\s+(\d+(?:\.\d)?)\+?\s*(?:or above\s+|or higher\s+)?(?:magnitude\s+)?earthquake\b.*\b(?:by|before)\b")
EB_T_RE = re.compile(r"(?i)^(?:another\s+)?(\d+(?:\.\d)?)\+? or above earthquake (?:by|before)\b")
EC_Q_RE = re.compile(r"(?i)^Will the biggest earthquake on ([A-Z][a-z]+ \d{1,2}, \d{4}) be (.+?)\?$")
THRESH_DESC_RE = re.compile(r"(?i)magnitude of (\d+(?:\.\d)?) or (?:higher|above|greater)")
DT = r"([A-Z][a-z]+ \d{1,2}(?:, \d{4})?),?\s*(?:(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)\s*)?(?:ET|EST|EDT|Eastern(?: Time)?)?"
WIN_ET_RE = re.compile(r"between\s+" + DT + r",?\s+and\s+" + DT, re.I)
WIN_CREATION_RE = re.compile(r"between market creation and\s+([A-Z][a-z]+ \d{1,2}, \d{4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)\s*ET", re.I)
UTC_DAY_RE = re.compile(r"UTC calendar day[^.]*?on ([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)
ET_MENTION_RE = re.compile(r"\b(ET|EST|EDT|Eastern)\b")
BUCKET_RES = ((re.compile(r"^(\d+)$"), "eq"), (re.compile(r"^(?:≤|<=)\s*(\d+)$"), "le"), (re.compile(r"^<\s*(\d+)$"), "lt"), (re.compile(r"(?i)^more than (\d+)$"), "gt"),
              (re.compile(r"^(\d+)\s*\+$"), "ge"), (re.compile(r"(?i)^(\d+) or more$"), "ge"), (re.compile(r"(?i)^fewer than (\d+)$"), "lt"),
              (re.compile(r"^(\d+)\s*[–-]\s*(\d+)$"), "range"), (re.compile(r"(?i)^between (\d+) and (\d+)$"), "range"))
MAG_BUCKET_RES = ((re.compile(r"(?i)^under (\d+(?:\.\d)?)$"), "under"), (re.compile(r"(?i)^(\d+(?:\.\d)?) to (\d+(?:\.\d)?)$"), "range"),
                  (re.compile(r"(?i)^(\d+(?:\.\d)?) or more$"), "more"))
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
EVENT_COLUMNS = ["event_id", "klass", "status", "src", "win_start", "win_end", "n_members", "n_parsed", "neg_risk", "title_sha256", "tz", "nr_id"]
MEMBER_COLUMNS = ["event_id", "market_id", "condition_id", "token_yes", "yes_index", "created_epoch", "end_epoch", "klass", "threshold", "lo", "hi", "win_start", "win_end", "tz",
                  "parse", "fee_rate", "desc_sha256", "n_chunks"]
OUTCOME_COLUMNS = ["market_id", "event_id", "yes_index", "outcome_prices", "uma_status"]
PRICE_COLUMNS = ["market_id", "ts", "p"]
# ---- Stage 2 (prospective) -------------------------------------------------------------------------------------------------------------------------------
LIVE_PASSES_UTC = (10, 16)
LIVE_PASS_WINDOW_S = 30 * 60
LIVE_MAX_MEMBERS = 80
LIVE_BOOK_GAP_S = 60.0
LIVE_USGS_SPAN_CAP_DAYS = 400
LIVE_USGS_SPAN_MIN_DAYS = 30  # the span reaches back at least this far (E-c reads and the 7-day lag robustness never depend on a short span)
LIVE_PASS_MAX_ATTEMPTS = 3  # tries of one slot inside its 30-minute window
LIVE_OUTCOMES_FILE = "outcomes_guarded_E_live.csv.gz"  # not in cb12_common.GUARDED_NAMES: no other SCREEN / REP job can open it through open_guarded
LIVE_STORE_MIN_MAG = 5.5  # every stored pass keeps the served events >= 5.5 over the span (modelled thresholds 6.0+ minus the 0.3 ambiguity band, with margin)
LIVE_STORE_RECENT_DAYS = 10  # ... and every served event (>= 4.5) of the last 10 days (E-c day maxima)
E2_START_DELAY_DAYS = 1
E2_MIN_DAYS = 56
E2_MAX_DAYS = 90
E2_OUTCOME_AFTER_S = 72 * HOUR
SMOKE_FAMILY_VERSION = "cb12-smoke-E-v1"
SMOKE_V2_DEFAULT = c12.CB12_DIR / "smoke_E.json"
SMOKE_NEEDS = ("guards_fixture_E", "e_parser_out_of_window", "e_usgs")
SMOKE_OUT_OF_WINDOW = "2026-10-01T00:00:00Z"
SMOKE_N_EVENTS = 3


def _ep(d: str) -> float:
    return cm.ep(d + "T00:00:00Z") if "T" not in d else cm.ep(d)


# =====================================================================================================================================================
# Parser (frozen)
# =====================================================================================================================================================


def _date_of(s: str, year_hint: int | None) -> tuple[int, int, int] | None:
    m = re.match(r"([A-Z][a-z]+) (\d{1,2})(?:, (\d{4}))?$", (s or "").strip())
    if not m or m.group(1) not in MONTHS:
        return None
    y = int(m.group(3)) if m.group(3) else year_hint
    if y is None:
        return None
    return y, MONTHS.index(m.group(1)) + 1, int(m.group(2))


def _clock(s: str | None) -> tuple[int, int, int]:
    if not s:
        return 0, 0, 0
    m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AP]M)", s.strip(), re.I)
    if not m:
        return 0, 0, 0
    h = int(m.group(1)) % 12 + (12 if m.group(4).upper() == "PM" else 0)
    return h, int(m.group(2)), int(m.group(3) or 0)


def _et(y: int, mo: int, d: int, hh: int = 0, mm: int = 0, ss: int = 0) -> float:
    return datetime(y, mo, d, hh, mm, ss, tzinfo=c12.NY).timestamp()


def parse_window(desc: str, created_epoch: float) -> tuple[float, float, str] | None:
    """(start, end exclusive, tz) of the rule window. ``between <date>[, <time>] ET and <date>, <time> ET`` (a start without a time is 12:00 AM, a start without a year
    takes the end's year; an end at hh:mm is exclusive at +60 s, at hh:mm:ss at +1 s); ``between market creation and <date> <time> ET`` (start = the market's
    createdAt); ``UTC calendar day ... on <date>`` (UTC day). None = parser failure."""
    d = desc or ""
    m = UTC_DAY_RE.search(d)
    if m:
        dd = _date_of(m.group(1), None)
        if dd is None:
            return None
        s = datetime(*dd, tzinfo=UTC).timestamp()
        return s, s + DAY, "UTC"
    m = WIN_CREATION_RE.search(d)
    if m:
        dd = _date_of(m.group(1), None)
        if dd is None or not math.isfinite(created_epoch):
            return None
        hh, mi, ss = _clock(m.group(2))
        end = _et(*dd, hh, mi, ss) + (1 if ss or m.group(2).count(":") == 2 else 60)
        return created_epoch, end, "ET"
    m = WIN_ET_RE.search(d)
    if m and ET_MENTION_RE.search(d[m.start():m.end() + 4] if m else ""):
        e = _date_of(m.group(3), None)
        if e is None:
            return None
        s = _date_of(m.group(1), e[0])
        if s is None:
            return None
        sh = _clock(m.group(2))
        eh = _clock(m.group(4))
        start = _et(*s, *sh)
        if m.group(4):
            end = _et(*e, *eh) + (1 if m.group(4).count(":") == 2 else 60)
        else:
            end = _et(*e) + DAY
        return (start, end, "ET") if end > start else None
    return None


def parse_count_bucket(txt: str) -> tuple[float, float] | None:
    t = (txt or "").strip()
    for rx, kind in BUCKET_RES:
        m = rx.match(t)
        if not m:
            continue
        n = int(m.group(1))
        if kind == "eq":
            return n, n
        if kind == "le":
            return 0, n
        if kind == "lt":
            return 0, n - 1
        if kind == "gt":
            return n + 1, math.inf
        if kind == "ge":
            return n, math.inf
        return n, int(m.group(2))
    return None


def parse_mag_bucket(txt: str) -> tuple[float, float] | None:
    t = (txt or "").strip()
    for rx, kind in MAG_BUCKET_RES:
        m = rx.match(t)
        if not m:
            continue
        if kind == "under":
            return -math.inf, round(float(m.group(1)) - 0.1, 1)
        if kind == "range":
            return float(m.group(1)), float(m.group(2))
        return float(m.group(1)), math.inf
    return None


def classify(title: str, question: str) -> str | None:
    """E-a / E-b / E-c by the frozen member / title patterns; regional questions -> 'regional'; anything else None (not a frozen class)."""
    q, t = question or "", title or ""
    if REGIONAL_RE.search(q) or REGIONAL_RE.search(t):
        return "regional"
    if EC_Q_RE.match(q):
        return "E-c"
    if EA_Q_RE.match(q):
        return "E-a"
    if EB_Q_RE.search(q) or EB_T_RE.match(t) or EB_T_RE.match(q):
        return "E-b"
    return None


def parse_member(m: dict, ev: dict) -> dict:
    """Whitelisted member row with the parsed rule (class, threshold, bucket, window, tz) and a ``parse`` status ('ok' or the counted reason). The description is
    hashed, never stored; ``outcomePrices`` and status go only to the guarded file."""
    labels = [str(x).strip().lower() for x in c12.listish(m.get("outcomes"))]
    toks = [str(x) for x in c12.listish(m.get("clobTokenIds"))]
    title, q = str(ev.get("title") or ""), str(m.get("question") or "")
    desc = str(m.get("description") or ev.get("description") or "")
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    row = {"event_id": str(ev.get("id")), "market_id": str(m.get("id")), "condition_id": str(m.get("conditionId") or ""), "token_yes": "", "yes_index": 0,
           "created_epoch": c12.parse_iso(m.get("createdAt")), "end_epoch": c12.parse_iso(m.get("endDate")), "klass": "", "threshold": math.nan, "lo": math.nan, "hi": math.nan,
           "win_start": math.nan, "win_end": math.nan, "tz": "", "parse": "", "fee_rate": c12.num(fs.get("rate")), "desc_sha256": c12.rank("arepo-cb12-desc", desc), "n_chunks": 0}
    if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2:
        return {**row, "parse": "not binary"}
    yi = labels.index("yes")
    row.update(token_yes=toks[yi], yes_index=yi)
    k = classify(title, q)
    if k is None:
        return {**row, "parse": "not a frozen class"}
    if k == "regional":
        return {**row, "klass": "regional", "parse": "regional"}
    row["klass"] = k
    if not USGS_RE.search(desc):
        return {**row, "parse": "parser failure: USGS not named"}
    if not GLOBAL_RE.search(desc + " " + title + " " + q):
        return {**row, "parse": "parser failure: not global"}
    win = parse_window(desc, row["created_epoch"])
    if win is None:
        return {**row, "parse": "parser failure: window"}
    row.update(win_start=win[0], win_end=win[1], tz=win[2])
    if k == "E-c":
        mm = EC_Q_RE.match(q)
        b = parse_mag_bucket(mm.group(2)) if mm else None
        if b is None:
            b = parse_mag_bucket(str(m.get("groupItemTitle") or ""))
        if b is None:
            return {**row, "parse": "parser failure: bucket"}
        return {**row, "lo": b[0], "hi": b[1], "parse": "ok"}
    if k == "E-a":
        mm = EA_Q_RE.match(q)
        thr = float(mm.group(2)) if mm else math.nan
        b = parse_count_bucket(str(m.get("groupItemTitle") or "")) or (parse_count_bucket(mm.group(1)) if mm else None)
        if b is None:
            return {**row, "threshold": thr, "parse": "parser failure: bucket"}
        row.update(threshold=thr, lo=b[0], hi=b[1])
    else:
        mm = EB_Q_RE.search(q) or EB_T_RE.match(q) or EB_T_RE.match(title)
        dm = THRESH_DESC_RE.search(desc)
        thr = float(mm.group(1)) if mm else (float(dm.group(1)) if dm else math.nan)
        row.update(threshold=thr, lo=1, hi=math.inf)
    if not math.isfinite(row["threshold"]):
        return {**row, "parse": "parser failure: threshold"}
    if round(row["threshold"], 1) not in THRESHOLDS:
        return {**row, "parse": "threshold not modelled"}
    return {**row, "parse": "ok"}


def parse_event(ev: dict) -> tuple[dict, list[dict], list[dict]] | None:
    """(event row, member rows, guarded outcome rows)."""
    if not isinstance(ev, dict) or ev.get("id") is None:
        return None
    mems, outs = [], []
    for m in ev.get("markets") if isinstance(ev.get("markets"), list) else []:
        if not isinstance(m, dict) or m.get("id") is None:
            continue
        r = parse_member(m, ev)
        mems.append(r)
        if r["token_yes"]:
            statuses = m.get("umaResolutionStatuses")
            outs.append({"market_id": r["market_id"], "event_id": r["event_id"], "yes_index": r["yes_index"], "outcome_prices": json.dumps(c12.listish(m.get("outcomePrices"))),
                         "uma_status": str(m.get("umaResolutionStatus") or (statuses if statuses else ""))})
    ok = [r for r in mems if r["parse"] == "ok"]
    ks = Counter(r["klass"] for r in mems if r["klass"])
    row = {"event_id": str(ev["id"]), "klass": ks.most_common(1)[0][0] if ks else "", "status": "", "src": "", "win_start": min((r["win_start"] for r in ok), default=math.nan),
           "win_end": max((r["win_end"] for r in ok), default=math.nan), "n_members": len(mems), "n_parsed": len(ok), "neg_risk": int(bool(ev.get("negRisk"))),
           "title_sha256": c12.rank("arepo-cb12-title", str(ev.get("title") or "")), "tz": ok[0]["tz"] if ok else "",
           "nr_id": str(ev.get("negRiskMarketID") or next((m.get("negRiskMarketID") for m in (ev.get("markets") or []) if isinstance(m, dict) and m.get("negRiskMarketID")), "") or "")}
    return row, mems, outs


def in_window(end_epoch: float) -> bool:
    return bool(math.isfinite(end_epoch) and _ep(E_WINDOW[0]) <= end_epoch < _ep(E_WINDOW[1]))


def overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return bool(a[0] < b[1] and b[0] < a[1])


def apply_exclusions(events: list[dict], members: dict[str, list[dict]], ids: set[str], keys: dict[str, set[str]]) -> dict:
    """E key rule (section 1.3): an event is excluded by key if its id, a member market id or its negRiskMarketID is in the exclusion keys; then every frame event whose
    rule window OVERLAPS the window of any key-excluded earthquake event is dropped (stricter than the series rule). Sets ``status`` / ``src`` in place. Returns counts: a key-excluded earthquake event with no parsed window
    cannot define an overlap, so it is counted (``key_excluded_no_window``), never silently skipped."""
    excl = []
    n_nowin = 0
    for e in events:
        mids = [m["market_id"] for m in members.get(e["event_id"], [])]
        nr = bool(e.get("nr_id")) and e["nr_id"] in keys.get("neg_risk_market", set())
        if e["event_id"] in keys.get("event", set()) or any(x in ids for x in mids) or nr:
            e["status"], e["src"] = "dropped:key", "event" if e["event_id"] in keys.get("event", set()) else ("market" if any(x in ids for x in mids) else "negRiskMarketID")
            if math.isfinite(e["win_start"]):
                excl.append((e["win_start"], e["win_end"]))
            else:
                n_nowin += 1
    for e in events:
        if e["status"]:
            continue
        if not math.isfinite(e["win_start"]):
            e["status"], e["src"] = "dropped:parser", "no parsed member"
        elif any(overlaps((e["win_start"], e["win_end"]), w) for w in excl):
            e["status"], e["src"] = "dropped:overlap", "overlap"
        else:
            e["status"] = "kept"
    return {"key_excluded": sum(1 for e in events if e["status"] == "dropped:key"), "key_excluded_no_window": n_nowin}


def components(events: list[dict]) -> dict[str, str]:
    """Window components: connected components of the events whose rule windows overlap in time (interval-graph components = merged intervals)."""
    iv = sorted((e["win_start"], e["win_end"], e["event_id"]) for e in events if math.isfinite(c12.num(e.get("win_start"))))
    out, cid, cur_end = {}, -1, -math.inf
    for s, en, eid in iv:
        if s >= cur_end:
            cid += 1
            cur_end = en
        else:
            cur_end = max(cur_end, en)
        out[eid] = f"C{cid}"
    return out


# =====================================================================================================================================================
# Catalogue: USGS client, guarded accessor, model fit, outcome evaluator
# =====================================================================================================================================================


def usgs_rows(doc: Any) -> list[list]:
    """(time ms, lat, lon, mag, magType, status, updated ms) of a USGS geojson reply; type earthquake only; finite magnitudes only."""
    out = []
    for f in (doc or {}).get("features") or [] if isinstance(doc, dict) else []:
        p = f.get("properties") or {}
        g = (f.get("geometry") or {}).get("coordinates") or [None, None]
        mg = c12.num(p.get("mag"))
        if str(p.get("type") or "earthquake") != "earthquake" or not math.isfinite(mg) or p.get("time") is None:
            continue
        out.append([int(p["time"]), g[1], g[0], mg, str(p.get("magType") or ""), str(p.get("status") or ""), p.get("updated")])
    return sorted(out, key=lambda r: r[0])


def usgs_params(start: str, end: str, minmag: float) -> dict:
    return {"format": "geojson", "starttime": start, "endtime": end, "minmagnitude": minmag, "eventtype": "earthquake", "orderby": "time-asc"}


def fetch_catalogue(lim, chunks: Iterable[tuple[str, str]], minmag: float, *, counted: bool, stats: dict) -> list[list]:
    """Fetch each chunk; with ``counted`` a count request first and a chunk over 20,000 rows is halved until it fits."""
    rows: list[list] = []
    todo = list(chunks)
    while todo:
        a, b = todo.pop(0)
        if counted:
            st, doc = lim.get(USGS_COUNT, {**usgs_params(a, b, minmag), "format": "geojson"})
            if st != 200 or not isinstance(doc, dict):
                raise cm.ApiError(f"usgs count status {st}")
            stats["count_requests"] = stats.get("count_requests", 0) + 1
            if int(doc.get("count", 0)) > USGS_MAX_ROWS:
                mid = (datetime.fromisoformat(a) + (datetime.fromisoformat(b) - datetime.fromisoformat(a)) / 2).date().isoformat()
                todo[:0] = [(a, mid), (mid, b)]
                stats["halved"] = stats.get("halved", 0) + 1
                continue
        st, doc = lim.get(USGS_QUERY, usgs_params(a, b, minmag))
        if st != 200:
            raise cm.ApiError(f"usgs query status {st}")
        stats["query_requests"] = stats.get("query_requests", 0) + 1
        rows += usgs_rows(doc)
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (r[0], r[3])):
        key = (r[0], r[3], r[1], r[2])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def m45_chunks() -> list[tuple[str, str]]:
    a, b = CAT_M45_FROM
    out, y = [], int(a[:4])
    while f"{y}-01-01" < b:
        ny = y + CAT_M45_CHUNK_YEARS
        out.append((f"{y}-01-01", min(f"{ny}-01-01", b)))
        y = ny
    return out


def load_catalogue(path: Path) -> np.ndarray:
    """(n, 2) array of (origin epoch s, mag), time-sorted."""
    rows = [(float(r["time_ms"]) / 1000.0, float(r["mag"])) for r in c12.read_csv_gz(path)]
    return np.array(sorted(rows), float).reshape(-1, 2)


def usable(cat: np.ndarray, t: float, lag_s: float = CAT_LAG_S) -> np.ndarray:
    """THE guarded accessor: catalogue events with origin time < t - 72 h (a census path never receives a later event)."""
    if len(cat) == 0:
        return cat
    return cat[cat[:, 0] < t - lag_s]


def fit_model(cat_m6: np.ndarray, fit_start: str = FIT_START, fit_end: str = FIT_END) -> dict:
    """lambda_m (per day) and the negative-binomial size k_m (method of moments; Poisson if var <= mean) from 30-day non-overlapping global counts in
    [fit_start, fit_end). REFUSES rows at or after the fit end being passed in (the caller passes only fit-period rows; a unit test feeds a later row)."""
    a, b = _ep(fit_start), _ep(fit_end)
    if len(cat_m6) and float(cat_m6[:, 0].max()) >= b:
        raise Refused("model fit received catalogue rows at or after 2024-09-01; refusing")
    n_bins = int((b - a) // (MONTH_DAYS * DAY))
    edges = a + np.arange(n_bins + 1) * MONTH_DAYS * DAY
    out = {}
    for m in THRESHOLDS:
        sel = cat_m6[(cat_m6[:, 1] >= m - 1e-9) & (cat_m6[:, 0] >= a)] if len(cat_m6) else np.zeros((0, 2))
        counts = np.histogram(sel[:, 0], bins=edges)[0].astype(float) if len(sel) else np.zeros(n_bins)
        mu, var = float(counts.mean()), float(counts.var(ddof=1)) if n_bins > 1 else 0.0
        k = (mu * mu / (var - mu)) if var > mu and mu > 0 else math.inf
        out[f"{m:.1f}"] = {"lambda_per_day": mu / MONTH_DAYS, "k_month": k, "mean_month": mu, "var_month": var, "n_bins": n_bins}
    return out


def n_rem_pmf_range(model: dict, m: float, tau_days: float, lo: float, hi: float) -> float:
    """P(lo <= N_rem <= hi) with N_rem ~ NegBin(mean lambda tau, size k tau / 30) (Poisson if k infinite); lo < 0 -> 0, hi infinite allowed."""
    pr = model[f"{m:.1f}"]
    mu = pr["lambda_per_day"] * max(tau_days, 0.0)
    lo = max(0.0, lo)
    if hi < lo:
        return 0.0
    if mu <= 0:
        return 1.0 if lo <= 0 else 0.0
    if not math.isfinite(pr["k_month"]):
        dist = poisson(mu)
    else:
        r = pr["k_month"] * tau_days / MONTH_DAYS
        dist = nbinom(r, r / (r + mu))
    upper = 1.0 if not math.isfinite(hi) else float(dist.cdf(hi))
    lower = float(dist.cdf(lo - 1)) if lo >= 1 else 0.0
    return max(0.0, min(1.0, upper - lower))


def round_mag(x: float) -> float:
    """Nearest tenth, 0.05 rounds up (the rule text)."""
    return math.floor(x * 10 + 0.5 + 1e-9) / 10.0


def day_key(ts: float, tz: str) -> str:
    return datetime.fromtimestamp(ts, UTC if tz == "UTC" else c12.NY).date().isoformat()


def day_maxima(cat_m45: np.ndarray, tz: str, start: str = ECDF_START, end: str = FIT_END) -> np.ndarray:
    """Rounded daily maximum magnitudes of every day in [start, end) in the rule's day (UTC or ET); a day without an M >= 4.5 event is -inf (the lowest bucket)."""
    d0, d1 = datetime.fromisoformat(start).date(), datetime.fromisoformat(end).date()
    days = {(d0 + timedelta(days=i)).isoformat(): -math.inf for i in range((d1 - d0).days)}
    for ts, mg in cat_m45:
        k = day_key(float(ts), tz)
        if k in days:
            days[k] = max(days[k], round_mag(float(mg)))
    return np.array(list(days.values()), float)


def q_of(u: dict, model: dict, cat: np.ndarray, maxima: dict[str, np.ndarray], *, lag_s: float = CAT_LAG_S) -> tuple[float | None, str]:
    """(q, label) of one unit (``t``, class, threshold, bucket, window). Uses only catalogue events before ``t - lag``. Labels: '' / 'decided' (E-b)."""
    t = u["t"]
    if u["klass"] == "E-c":
        mx = maxima[u["tz"] or "ET"]
        return float(np.mean((mx >= u["lo"] - 1e-9) & (mx <= u["hi"] + 1e-9))), ""
    ev = usable(cat, t, lag_s)
    m = round(float(u["threshold"]), 1)
    c = int(np.sum((ev[:, 1] >= m - 1e-9) & (ev[:, 0] >= u["win_start"]) & (ev[:, 0] < u["win_end"]))) if len(ev) else 0
    tau = (u["win_end"] - max(u["win_start"], t - lag_s)) / DAY
    if u["klass"] == "E-b":
        if c >= 1:
            return None, "decided"
        return 1.0 - n_rem_pmf_range(model, m, tau, 0, 0), ""
    return n_rem_pmf_range(model, m, tau, u["lo"] - c, u["hi"] - c), ""


def outcome_of(u: dict, cat: np.ndarray) -> float:
    """The catalogue answer to the frozen rule (screen / rep only): E-a count in bucket, E-b >= 1 event, E-c rounded day maximum in bucket (no event -> lowest)."""
    sel = cat[(cat[:, 0] >= u["win_start"]) & (cat[:, 0] < u["win_end"])] if len(cat) else np.zeros((0, 2))
    if u["klass"] == "E-c":
        mx = max((round_mag(float(x)) for x in sel[:, 1]), default=-math.inf)
        return float(u["lo"] - 1e-9 <= mx <= u["hi"] + 1e-9)
    n = int(np.sum(sel[:, 1] >= round(float(u["threshold"]), 1) - 1e-9))
    return float(u["lo"] <= n <= u["hi"])


def ambiguous(u: dict, cat: np.ndarray) -> bool:
    """'ambiguous recent quake': an event within +-0.3 of the threshold in the 72 h BEFORE the accessor boundary, [t - 144 h, t - 72 h) (E-a / E-b; an E-c window starts
    after t). The model, and so this check, never sees an event at or after ``t - 72 h`` (sections 1.3 and 2.7). Computed from final revised magnitudes (disclosed)."""
    if u["klass"] == "E-c" or len(cat) == 0:
        return False
    t, m = u["t"], float(u["threshold"])
    sel = cat[(cat[:, 0] >= t - 2 * CAT_LAG_S) & (cat[:, 0] < t - CAT_LAG_S)]
    return bool(np.any(np.abs(sel[:, 1] - m) <= AMBIG_BAND + 1e-9))


# =====================================================================================================================================================
# q0244 frame + catalogue, q0245 prices
# =====================================================================================================================================================


def walk_tag(lim, tag_id: int, *, page: int = c12.GAMMA_PAGE, offset_cap: int = c12.GAMMA_OFFSET_CAP) -> list[dict]:
    out = []
    for off in range(0, offset_cap + page, page):
        st, data = lim.get(c12.GAMMA_EVENTS, {"closed": "true", "tag_id": tag_id, "order": "id", "ascending": "true", "limit": page, "offset": off})
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma events status {st}")
        out.extend(x for x in data if isinstance(x, dict))
        if len(data) < page:
            return out
    raise Refused(f"gamma tag {tag_id} is capped at the offset cap")


def n_chunks(created: float, end: float) -> int:
    a = max(created if math.isfinite(created) else _ep(E_WINDOW[0]), _ep(E_WINDOW[0]))
    return max(1, math.ceil((end - a) / (CHUNK_DAYS * DAY))) if math.isfinite(end) and end > a else 0


def _wcsv(fr, path: Path, header: list[str], rows: Iterable[list]) -> None:
    fr.budget.write_gz_csv(path, header, rows)
    fr.record_file(path)


def quake_frame(hist_root: Path, transport, *, rules_sha: str, smoke_paths, exclusion_keys_path: Path, now: float, usgs_transport=None, rps: float = 2.0, usgs_rps: float = USGS_RPS,
                disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time,
                snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c12.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0244. Closed events of tag 103038 or 100184 (union by id; every closed event is fetched so key-excluded earthquake events outside the window still define the
    overlap drops), members parsed by the frozen parser, kept if their endDate is in the E window; the E key / overlap rule; the USGS catalogue (M >= 6.0
    1976-2026, M >= 4.5 2000-2026). Gamma outcomes only to ``outcomes_guarded.csv.gz``. The manifest records the q0245 request sum (sum of ceil(span / 14 d))."""
    from . import cb12_smoke as sm  # noqa: PLC0415

    rdir = c12.require_output_root(Path(hist_root) / FRAME_RUN)
    st = c12.stall_of(rdir)
    if st:
        return st
    done = c12.manifest_complete(rdir, (FRAME_STATUS, PRICES_STATUS))
    if done or ((json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}).get("state") or {}).get("frame_complete"):
        return {"stopped": None, "status": FRAME_STATUS, "complete": True}
    bad = sm.smoke_failures(smoke_paths, SMOKE_NEEDS)
    if bad:
        return c12.write_stall(rdir, c12.c9.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c12.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c12.UNVERIFIED:
        return c12.write_stall(rdir, c12.c9.STALL_DISJOINTNESS, "exclusion keys: more than 2% of ids without metadata")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c12.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    rdir.mkdir(parents=True, exist_ok=True)
    fr = cm.open_run(Path(hist_root), FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb12_quake_frame", label="CB12-E frame",
                     params={"evidence_role": c12.EVIDENCE_ROLE_HIST, "tag_ids": list(TAG_IDS), "window": list(E_WINDOW), "exclusion_keys_sha256": ksha}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    ulim = hb.Limiter(usgs_transport or transport, rps=min(usgs_rps, USGS_RPS), sleep=sleep, live_check=live_check)
    stats: dict = {}
    try:
        evs: dict[str, dict] = {}
        for tag in TAG_IDS:
            for e in walk_tag(fr.lim, tag):
                evs.setdefault(str(e["id"]), e)
        cat6 = fetch_catalogue(ulim, CAT_M6_CHUNKS, 6.0, counted=False, stats=stats)
        cat45 = fetch_catalogue(ulim, m45_chunks(), 4.5, counted=True, stats=stats)
    except (cm.ApiError, RuntimeError) as exc:
        mm = fr.manifest(f"source_failed: {exc}"[:200], {"transient": True})
        mm["status"] = "in_progress"
        return mm
    ev_rows, mem_rows, out_rows = [], {}, {}
    for eid in sorted(evs):
        p = parse_event(evs[eid])
        if p is None:
            continue
        row, mems, outs = p
        ev_rows.append(row)
        mem_rows[eid] = mems
        out_rows[eid] = outs
    excl_counts = apply_exclusions(ev_rows, mem_rows, ids, keys)
    frame = [e for e in ev_rows if any(in_window(m["end_epoch"]) for m in mem_rows[e["event_id"]])]
    for e in frame:
        for m in mem_rows[e["event_id"]]:
            m["n_chunks"] = n_chunks(m["created_epoch"], m["end_epoch"]) if (e["status"] == "kept" and m["parse"] == "ok" and in_window(m["end_epoch"])) else 0
    req_sum = sum(m["n_chunks"] for e in frame for m in mem_rows[e["event_id"]])
    try:
        _wcsv(fr, rdir / "events.csv.gz", EVENT_COLUMNS, ([e[c] for c in EVENT_COLUMNS] for e in frame))
        _wcsv(fr, rdir / "members.csv.gz", MEMBER_COLUMNS, ([m[c] for c in MEMBER_COLUMNS] for e in frame for m in mem_rows[e["event_id"]]))
        _wcsv(fr, rdir / "outcomes_guarded.csv.gz", OUTCOME_COLUMNS, ([o[c] for c in OUTCOME_COLUMNS] for e in frame if e["status"] == "kept" for o in out_rows[e["event_id"]]))
        _wcsv(fr, rdir / "catalogue_m6.csv.gz", CAT_COLUMNS, cat6)
        _wcsv(fr, rdir / "catalogue_m45.csv.gz", CAT_COLUMNS, cat45)
        n_dropped = sum(1 for e in frame if e["status"] in ("dropped:key", "dropped:overlap"))
        report = {"events_fetched_all_dates": len(ev_rows), "events_in_window": len(frame), "by_status": dict(Counter(e["status"] for e in frame)),
                  "drop_source": dict(Counter(e["src"] for e in frame if e["status"].startswith("dropped"))), "member_parse": dict(Counter(m["parse"] for e in frame for m in mem_rows[e["event_id"]])),
                  "by_class": dict(Counter(e["klass"] for e in frame)), "thinned_share": n_dropped / len(frame) if frame else 0.0,
                  "label_thinned": "population thinned by exclusions" if frame and n_dropped / len(frame) > THIN_MAX else None, "usgs": stats, "n_cat_m6": len(cat6), "n_cat_m45": len(cat45),
                  "q0245_request_sum": req_sum, "q0245_request_cap": PRICES_REQUEST_CAP, **excl_counts}
        (rdir / "frame_report.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
        fr.record_file(rdir / "frame_report.json")
        fr.counts.update(events=len(frame), q0245_request_sum=req_sum, usgs_requests=ulim.requests)
        fr.extra_state["frame_complete"] = True
        fr.extra_state["q0245_request_sum"] = req_sum
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m["status"] = FRAME_STATUS
    return m


def frame_members(rdir: Path) -> list[dict]:
    """Members to price: parsed ('ok') members of kept events with endDate in the window."""
    evs = {r["event_id"]: r for r in c12.read_csv_gz(Path(rdir) / "events.csv.gz")}
    return sorted((r for r in c12.read_csv_gz(Path(rdir) / "members.csv.gz") if evs.get(r["event_id"], {}).get("status") == "kept" and r["parse"] == "ok" and int(r["n_chunks"] or 0) > 0),
                  key=lambda r: r["market_id"])


def _scan_partial(part: Path) -> dict[str, tuple[int, str]]:
    """market_id -> (byte offset of its last complete record, status) of ``prices_partial.jsonl``; one record in memory at a time."""
    out: dict[str, tuple[int, str]] = {}
    if not part.exists():
        return out
    with part.open("rb") as fh:
        off = 0
        for raw in fh:
            n = len(raw)
            if raw.strip():
                try:
                    r = json.loads(raw)
                    out[r["market_id"]] = (off, str(r.get("status") or ""))
                except (ValueError, KeyError):
                    pass
            off += n
    return out


def _partial_rows(part: Path, index: dict[str, tuple[int, str]]) -> Iterable[list]:
    with part.open("rb") as fh:
        for k in sorted(index):
            fh.seek(index[k][0])
            for t, p in json.loads(fh.readline())["points"]:
                yield [k, t, p]


def quake_prices(hist_root: Path, transport, *, rules_sha: str, now: float, rps: float = 2.0, disk_cap: int = int(PRICES_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
                 sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                 data_dumps_cap_gb: float = c12.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0245, one resumable chunk: per member ``ceil(span / 14 d)`` bounded ``prices-history`` requests at fidelity 60 over [max(createdAt, 2024-09-01), endDate]. Refuses if
    q0244's recorded request sum exceeds 15,000. No outcome read."""
    rdir = c12.require_output_root(Path(hist_root) / FRAME_RUN)
    st = c12.stall_of(rdir)
    if st:
        return st
    mp = rdir / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if not (man.get("state") or {}).get("frame_complete"):
        raise NotNow("q0245 waits for q0244 (quake_frame) to finish")
    done = c12.manifest_complete(rdir, (PRICES_STATUS,))
    if done:
        return {"stopped": None, "status": PRICES_STATUS, "complete": True, "counts": done.get("counts")}
    req_sum = int((man.get("state") or {}).get("q0245_request_sum") or 0)
    if req_sum > PRICES_REQUEST_CAP:
        raise Refused(f"q0244 recorded {req_sum} prices-history requests > the declared bound {PRICES_REQUEST_CAP}")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c12.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(Path(hist_root), FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb12_quake_prices", label="CB12-E prices",
                     params={"evidence_role": c12.EVIDENCE_ROLE_HIST, "fidelity": FIDELITY, "chunk_days": CHUNK_DAYS}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0),
                     budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    part = rdir / "prices_partial.jsonl"
    have = set(_scan_partial(part))
    try:
        for m in frame_members(rdir):
            mid = m["market_id"]
            if mid in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                mm = fr.manifest(why, {"transient": True})
                mm["status"] = "in_progress"
                return mm
            a = max(float(m["created_epoch"]) if m["created_epoch"] not in ("", "nan") else _ep(E_WINDOW[0]), _ep(E_WINDOW[0]))
            end = float(m["end_epoch"])
            pts: list[list] = []
            try:
                s = a
                while s < end:
                    e = min(s + CHUNK_DAYS * DAY, end)
                    stp, data = fr.lim.get(hb.CLOB_PRICES, {"market": m["token_yes"], "startTs": int(s), "endTs": int(e), "fidelity": FIDELITY})
                    if stp != 200:
                        raise cm.ApiError(f"prices-history status {stp}")
                    pts += [[int(h["t"]), float(h["p"])] for h in ((data or {}).get("history") or []) if isinstance(h, dict) and "t" in h and "p" in h]
                    s = e
                status = "ok"
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[mid] = fails.get(mid, 0) + 1
                if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                    mm = fr.manifest(f"fetch_failed {mid}: {exc}"[:200], {"transient": True})
                    mm["status"] = "in_progress"
                    return mm
                pts, status = [], "unavailable (network)"
            with part.open("a") as fh:
                fh.write(json.dumps({"market_id": mid, "status": status, "points": sorted({(p[0], p[1]) for p in pts})}) + "\n")
            have.add(mid)
        index = _scan_partial(part)  # market -> (byte offset of its last record, status): the points are streamed record by record, never held together
        _wcsv(fr, rdir / "prices.csv.gz", PRICE_COLUMNS, _partial_rows(part, index))
        for rel in ("events.csv.gz", "members.csv.gz", "outcomes_guarded.csv.gz", "catalogue_m6.csv.gz", "catalogue_m45.csv.gz", "frame_report.json"):
            if (rdir / rel).exists():
                fr.record_file(rdir / rel)
        part.unlink(missing_ok=True)
        fr.counts.update(markets_priced=len(index), unavailable_network=sum(1 for _o, st_ in index.values() if st_ != "ok"))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m_ = fr.manifest(None, {"complete": True, "status": PRICES_STATUS})
    m_["status"] = PRICES_STATUS
    return m_


# =====================================================================================================================================================
# Units (features only) and the E1 statistics
# =====================================================================================================================================================


def point_at(points: list[tuple[float, float]], t: float, fidelity: int = FIDELITY) -> tuple[float, float] | None:
    """(stamp, price) of the last point usable before ``t`` (stamp + max(600, 60 f) < t, age <= 24 h), else None. ``points`` ascending by stamp (bisect; of equal
    stamps the first finite one in list order)."""
    lag = c12.known_lag_s(fidelity)
    i = bisect_left(points, t, key=lambda z: z[0] + lag) - 1
    while i >= 0:
        ts = points[i][0]
        if t - ts > c12.PRICE_MAX_AGE_S:
            return None
        for k in range(bisect_left(points, ts, key=lambda z: z[0]), i + 1):
            if math.isfinite(points[k][1]):
                return points[k]
        i = bisect_left(points, ts, key=lambda z: z[0]) - 1
    return None


def checkpoints_for(m: dict) -> list[float]:
    """16:00Z checkpoints from the market's listing to its last eligible time (E-a / E-b: >= 6 h before the window end; E-c: before the day starts), also before
    the checkpoint start (labelled there)."""
    created, end = float(m["created_epoch"]), float(m["end_epoch"])
    last = float(m["win_start"]) - 1 if m["klass"] == "E-c" else float(m["win_end"]) - END_BUFFER_S
    last = min(last, end)
    d0 = datetime.fromtimestamp(created if math.isfinite(created) else _ep(E_WINDOW[0]), UTC).replace(hour=CHECKPOINT_HOUR_UTC, minute=0, second=0, microsecond=0)
    out, t = [], d0.timestamp()
    while t <= last:
        out.append(t)
        t += DAY
    return out


def load_frame(rdir: Path) -> dict:
    """Events, members (typed), prices, catalogue arrays. No outcome column is read here."""
    rdir = Path(rdir)
    events = {r["event_id"]: r for r in c12.read_csv_gz(rdir / "events.csv.gz")}
    members = []
    for r in c12.read_csv_gz(rdir / "members.csv.gz"):
        for k in ("created_epoch", "end_epoch", "threshold", "lo", "hi", "win_start", "win_end", "fee_rate"):
            r[k] = c12.num(r[k])
        r["yes_index"] = int(r["yes_index"] or 0)
        members.append(r)
    prices: dict[str, list[tuple[float, float]]] = {}
    if (rdir / "prices.csv.gz").exists():
        for r in c12.read_csv_gz(rdir / "prices.csv.gz"):
            prices.setdefault(r["market_id"], []).append((float(r["ts"]), float(r["p"])))
    for v in prices.values():
        v.sort()
    return {"events": events, "members": members, "prices": prices, "cat6": load_catalogue(rdir / "catalogue_m6.csv.gz"), "cat45": load_catalogue(rdir / "catalogue_m45.csv.gz")}


def model_inputs(data: dict) -> tuple[dict, dict[str, np.ndarray]]:
    fit = data["cat6"][data["cat6"][:, 0] < _ep(FIT_END)] if len(data["cat6"]) else data["cat6"]
    fit45 = data["cat45"][data["cat45"][:, 0] < _ep(FIT_END)] if len(data["cat45"]) else data["cat45"]
    return fit_model(fit), {tz: day_maxima(fit45, tz) for tz in ("UTC", "ET")}


def build_units(data: dict, *, lag_s: float = CAT_LAG_S, poisson: bool = False) -> tuple[list[dict], dict]:
    """(units, member-level counts) of one variant; see ``build_units_multi``."""
    res, mc = build_units_multi(data, {"v": {"lag_s": lag_s, "poisson": poisson}})
    return res["v"], mc


def build_units_multi(data: dict, variants: dict[str, dict]) -> tuple[dict[str, list[dict]], dict]:
    """({variant: units}, member-level counts). Unit labels: 'before checkpoint start', 'not listed', 'unavailable (no price)', 'no separate earlier point', 'ambiguous recent
    quake', 'decided', 'available'. Features only (q from catalogue events before t - lag; prices by the stamp + 3,600 s rule). A variant is ``{"lag_s", "poisson"}``
    (``poisson`` = the reported no-overdispersion variant: every k_m infinite, same lambda_m). The price lookups, the gates and the ambiguity check are computed once for
    all variants (they do not depend on the lag or the count model); only ``q`` is per variant."""
    model, maxima = model_inputs(data)
    models = {k: ({kk: {**v, "k_month": math.inf} for kk, v in model.items()} if var.get("poisson") else model) for k, var in variants.items()}
    cat = data["cat45"] if len(data["cat45"]) else data["cat6"]
    comp = components([dict(e, win_start=c12.num(e["win_start"]), win_end=c12.num(e["win_end"])) for e in data["events"].values() if e["status"] == "kept"])
    cstart = _ep(CHECKPOINT_START)
    out: dict[str, list[dict]] = {k: [] for k in variants}
    mc = Counter()
    for m in data["members"]:
        e = data["events"].get(m["event_id"]) or {}
        if e.get("status") != "kept" or not in_window(m["end_epoch"]):
            continue
        mc[f"member:{m['parse']}"] += 1
        if m["parse"] != "ok":
            continue
        pts = data["prices"].get(m["market_id"], [])
        for t in checkpoints_for(m):
            u = {"market_id": m["market_id"], "event_id": m["event_id"], "klass": m["klass"], "threshold": m["threshold"], "lo": m["lo"], "hi": m["hi"], "win_start": m["win_start"],
                 "win_end": m["win_end"], "tz": m["tz"], "t": t, "week": c12.iso_week_of(t), "component": comp.get(m["event_id"], f"E{m['event_id']}"), "yes_index": m["yes_index"]}
            pre = None
            pt = pr = pa = None
            if t < cstart:
                pre = "before checkpoint start"
            elif not (math.isfinite(m["created_epoch"]) and m["created_epoch"] <= t - LIST_BUFFER_S):
                pre = "not listed"
            else:
                pt, pr, pa = point_at(pts, t), point_at(pts, t - REG_LAG_S), point_at(pts, t - ALT_LAG_S)
                if pt is None or pr is None:
                    pre = "unavailable (no price)"
                elif pr[0] == pt[0]:
                    pre = "no separate earlier point"
                elif ambiguous(u, cat):
                    pre = "ambiguous recent quake"
            if pre:
                for k in out:
                    out[k].append({**u, "label": pre})
                continue
            for k, var in variants.items():
                q, lab = q_of(u, models[k], cat, maxima, lag_s=var.get("lag_s", CAT_LAG_S))
                if lab:
                    out[k].append({**u, "label": lab})
                else:
                    out[k].append({**u, "label": "available", "p_t": pt[1], "p_reg": pr[1], "p_alt": pa[1] if pa is not None else None, "q": q})
    return out, dict(mc)


def market_weights(us: list[dict]) -> np.ndarray:
    n = Counter(u["market_id"] for u in us)
    return np.array([1.0 / n[u["market_id"]] for u in us], float)


def slope_pseudo(y, x, w=None) -> tuple[np.ndarray, float]:
    """(pseudo-values, slope) of the (W)LS slope with intercept: v_i = b + n w_i (x_i - x_w) e_i / S_xx (mean(v) = b; clustered variance = the sandwich)."""
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
    return {"event": [u["event_id"] for u in us], "week": [u["week"] for u in us], "component": [u["component"] for u in us]}


def e1_slope(us: list[dict], *, x: np.ndarray | None = None, y_key: str = "y") -> dict:
    """E1: market-weighted slope of ``Y - p_t`` on ``q - p_reg``; one-sided p = max over the event, ISO-week and window-component ways (small-G rule)."""
    if len(us) < 3:
        return {"beta": math.nan, "p": 1.0, "testable": False, "n": len(us)}
    y = np.array([u[y_key] - u["p_t"] for u in us], float)
    xx = np.array([u["q"] - u["p_reg"] for u in us], float) if x is None else x
    v, b = slope_pseudo(y, xx, market_weights(us))
    if not math.isfinite(b):
        return {"beta": b, "p": 1.0, "testable": False, "n": len(us)}
    cp = c12.cluster_p(v, ways(us))
    return {"beta": b, "p": cp["p"], "testable": cp["testable"], "n": cp["n"], "ways": cp["ways"], "pseudo": v}


def e1_signflip(us: list[dict], *, n_draws: int = c12.PLACEBO_DRAWS, seed: int = PLACEBO_SEED) -> dict:
    """Binding sign-flip calibration: one coin per ISO week (shared by the week's units), per event and per window component; the advance-rate rule must hold under
    each way (p threshold alone)."""
    x = np.array([u["q"] - u["p_reg"] for u in us], float)
    out = {}
    for way, key in (("week", "week"), ("event", "event_id"), ("component", "component")):
        rng = np.random.default_rng(seed)
        groups = sorted({u[key] for u in us})
        gi = np.array([groups.index(u[key]) for u in us])
        ps = [e1_slope(us, x=x * rng.choice([-1.0, 1.0], size=len(groups))[gi])["p"] for _ in range(n_draws)]
        out[way] = c12.placebo_advance_rate(ps)
    return {"ways": out, "holds": all(v["holds"] for v in out.values()), "advance_rate": max(v["advance_rate"] for v in out.values()), "n_draws": n_draws,
            "note": "E1 sign-flip calibration (week, event, component coins)", "seed": seed}


def add_labels(res: dict, labels: Iterable[str | None]) -> dict:
    """Carry the declared labels ('rule ambiguity', 'population thinned by exclusions') into ``verdict``, the one free-text field the trial lines keep."""
    labs = sorted(set(res.get("labels") or []) | {x for x in labels if x})
    if labs:
        base = res.setdefault("verdict_base", res.get("verdict") or "")
        res["labels"], res["verdict"] = labs, f"{base} [{'; '.join(labs)}]"
    return res


def effective_label(u: dict) -> str:
    """The unit's label, with an 'available' unit that has no outcome counted as 'unavailable (outcome)' (never silently dropped)."""
    if u["label"] == "available" and u.get("y") is None:
        return u.get("outcome_label") or "unavailable (outcome read)"
    return u["label"]


def eligible_label(lab: str) -> bool:
    """Units that count in the availability denominator (section 2.6 iv): available, every 'unavailable (...)' label and 'no separate earlier point'. Ambiguous, decided, not
    listed, before-checkpoint-start and not-eligible units are excluded from the denominator by design (counted by label)."""
    return lab == "available" or lab.startswith("unavailable") or lab == "no separate earlier point"


def e1_test(units: list[dict], *, units_lag7: list[dict] | None = None, cat: np.ndarray | None = None, placebo: bool = True, n_draws: int = c12.PLACEBO_DRAWS,
            window: tuple[float, float] | None = None) -> dict:
    """E1 on the units. ``window`` = the calendar window whose two halves the sign check uses (Stage 1: the E window; Stage 2: [T12_E2_start, T12_E2_end))."""
    labs = [effective_label(u) for u in units]
    elig = [lb for lb in labs if eligible_label(lb)]
    av = sum(1 for lb in elig if lb == "available") / len(elig) if elig else 0.0
    us = [u for u, lb in zip(units, labs, strict=True) if lb == "available"]
    res: dict = {"test": "E1", "label": LABEL_E, "n": len(us), "n_markets": len({u["market_id"] for u in us}), "availability_share": av, "unit_labels": dict(Counter(labs))}
    if av < c12.AVAIL_MIN:
        return {**res, "p": 1.0, "testable": False, "advance": False, "effect": None, "verdict": "not testable (availability)"}
    base = e1_slope(us)
    res.update(beta=base["beta"], effect=base["beta"], p=base["p"], testable=base["testable"], ways=base.get("ways"), floor_ok=bool(math.isfinite(base["beta"]) and base["beta"] >= E1_FLOOR))
    if not base["testable"] or len(us) < c12.MIN_UNITS:
        return {**res, "advance": False, "verdict": "not testable (units / clusters)"}
    alt = [u for u in us if u.get("p_alt") is not None]
    xa = np.array([u["p_alt"] - u["p_reg"] for u in alt], float)
    pa = e1_slope(alt, x=xa) if len(alt) >= 3 else {"beta": math.nan, "p": 1.0, "testable": False}
    known = bool(pa.get("testable") and math.isfinite(pa["beta"]))  # an untestable or missing placebo is unknown, and unknown never counts as met (section 2.3)
    res["independent_price_placebo"] = {"beta_alt": pa["beta"], "p_alt": pa["p"], "known": known, "n": len(alt),
                                        "credit": bool(known and pa["p"] >= c12.GATE_P and base["beta"] - pa["beta"] >= E1_FLOOR)}
    rob: dict = {}
    for way, key in (("event", "event_id"), ("week", "week"), ("component", "component")):
        keep = c12.top_k_drop_mask(base["pseudo"], [u[key] for u in us], c12.TOP_DROP)
        sub = [u for u, k in zip(us, keep, strict=True) if k]
        r = e1_slope(sub) if len(sub) >= c12.MIN_UNITS else {"testable": False}
        rob[f"top5_{way}_drop"] = bool(r.get("testable") and r["p"] < c12.GATE_P and r["beta"] >= E1_FLOOR)
    ea = [u for u in us if u["klass"] == "E-a"]
    ebc = [u for u in us if u["klass"] in ("E-b", "E-c")]
    rob["class_E-a_sign"] = bool(len(ea) >= 3 and e1_slope(ea)["beta"] > 0)
    rob["class_E-bc_sign"] = bool(len(ebc) >= 3 and e1_slope(ebc)["beta"] > 0)
    if cat is not None and len(cat):
        big = cat[cat[:, 1] >= BIG_QUAKE - 1e-9, 0]
        nb = [u for u in us if not np.any((big < u["t"]) & (big >= u["t"] - BIG_QUAKE_DAYS * DAY))]
        rob["after_big_quake_excluded_sign"] = bool(len(nb) >= 3 and e1_slope(nb)["beta"] > 0)
    w0, w1 = window if window is not None else (_ep(E_WINDOW[0]), _ep(E_WINDOW[1]))
    mid = (w0 + w1) / 2.0  # calendar halves of the window (section 2.6 iii), not the median unit time
    h1, h2 = [u for u in us if u["t"] < mid], [u for u in us if u["t"] >= mid]
    rob["halves_sign"] = bool(len(h1) >= 3 and len(h2) >= 3 and e1_slope(h1)["beta"] > 0 and e1_slope(h2)["beta"] > 0)
    gam = [u for u in us if u.get("y_gamma") is not None]
    gb = e1_slope(gam, y_key="y_gamma")["beta"] if len(gam) >= 3 else math.nan
    rob["gamma_outcome_sign_half"] = bool(math.isfinite(gb) and gb > 0 and gb >= 0.5 * base["beta"])
    if units_lag7 is not None:
        u7 = [u for u in units_lag7 if u["label"] == "available" and u.get("y") is not None]
        rob["lag_7d_sign"] = bool(len(u7) >= 3 and e1_slope(u7)["beta"] > 0)
    plc = e1_signflip(us, n_draws=n_draws) if placebo else None
    rob_ok = all(v is True for v in rob.values())
    agree = [u for u in us if u.get("y_gamma") is not None]
    share = float(np.mean([u["y"] == u["y_gamma"] for u in agree])) if agree else None
    by_class = {k: e1_slope([u for u in us if u["klass"] == k])["beta"] for k in ("E-a", "E-b", "E-c") if sum(1 for u in us if u["klass"] == k) >= 3}
    res.update(robustness=rob, robustness_ok=rob_ok, placebo=plc, agreement={"share": share, "n": len(agree), "min": AGREE_MIN, "label": "rule ambiguity" if share is not None and share < AGREE_MIN else None},
               reported={"beta_by_class": by_class})
    ok = bool(base["p"] < c12.GATE_P and res["floor_ok"] and rob_ok and res["independent_price_placebo"]["credit"] and (plc is None or plc["holds"]))
    res.update(stage1_pass=ok, early_holm_ok=c12.early_stage1_ok(base["p"]), advance=bool(ok and c12.early_stage1_ok(base["p"])), holm_pending=bool(ok and not c12.early_stage1_ok(base["p"])))
    res["verdict"] = "advance (early Holm)" if res["advance"] else ("pending the full step-down (p in [0.005, 0.01))" if res["holm_pending"] else "no advance")
    return add_labels(res, [res["agreement"]["label"]])


# =====================================================================================================================================================
# Census (q0266, counts and features only) and the GEP power gate
# =====================================================================================================================================================


def gep(us: list[dict], *, n_draws: int = c12.GMP_DRAWS, seed: int = SEED_GEP) -> dict:
    """Feature-only power gate: per event one uniform U_e = Phi(sqrt(.3) W_week + sqrt(.3) C_comp + sqrt(.4) eps_e) selects the simulated winning bucket / first
    rung from the cumulative normalised prices at the event's first available checkpoint; ``MDE_E1 = (z_.99 + z_.80) x 1.2 x max(SD(beta*), mean event-, week-,
    component-way SE)``."""
    rng = np.random.default_rng(seed)
    a, b, c = (math.sqrt(x) for x in GEP_LOADINGS)
    first: dict[str, dict] = {}
    for u in sorted(us, key=lambda z: z["t"]):
        first.setdefault(u["event_id"], {})
        first[u["event_id"]].setdefault(u["market_id"], u)
    evs = sorted(first)
    wk = sorted({min(first[e].values(), key=lambda z: z["t"])["week"] for e in evs})
    cp = sorted({next(iter(first[e].values()))["component"] for e in evs})
    betas, se_e, se_w, se_c = [], [], [], []
    x = np.array([u["q"] - u["p_reg"] for u in us], float)
    w = market_weights(us)
    for _ in range(n_draws):
        W = dict(zip(wk, rng.standard_normal(len(wk)), strict=True))
        C = dict(zip(cp, rng.standard_normal(len(cp)), strict=True))
        ystar: dict[str, float] = {}
        for e in evs:
            ms = sorted(first[e].values(), key=lambda z: (z["hi"] if z["klass"] != "E-b" else z["win_end"], z["market_id"]))
            u0 = min(ms, key=lambda z: z["t"])
            U = float(norm.cdf(a * W[u0["week"]] + b * C[u0["component"]] + c * rng.standard_normal()))
            if ms[0]["klass"] == "E-b":  # nested rungs: the first rung whose price reaches U resolves YES, and every later rung with it
                hit = next((i for i, z in enumerate(ms) if z["p_t"] >= U), None)
                for i, z in enumerate(ms):
                    ystar[z["market_id"]] = float(hit is not None and i >= hit)
            else:
                p = np.array([max(z["p_t"], 0.0) for z in ms])
                cum = np.cumsum(p / p.sum()) if p.sum() > 0 else np.linspace(1 / len(ms), 1, len(ms))
                win = int(np.searchsorted(cum, U))
                for i, z in enumerate(ms):
                    ystar[z["market_id"]] = float(i == min(win, len(ms) - 1))
        yy = np.array([ystar.get(u["market_id"], 0.0) - u["p_t"] for u in us], float)
        v, bb = slope_pseudo(yy, x, w)
        betas.append(bb)
        se_e.append(c12.cluster_se_mean(v, [u["event_id"] for u in us]))
        se_w.append(c12.cluster_se_mean(v, [u["week"] for u in us]))
        se_c.append(c12.cluster_se_mean(v, [u["component"] for u in us]))
    sd = float(np.nanstd(betas, ddof=1)) if len(betas) > 1 else math.nan
    m = c12.mde(max(sd, float(np.nanmean(se_e)), float(np.nanmean(se_w)), float(np.nanmean(se_c))))
    return {"MDE_E1": m, "sd_beta": sd, "mean_se_event": float(np.nanmean(se_e)), "mean_se_week": float(np.nanmean(se_w)), "mean_se_component": float(np.nanmean(se_c)),
            "max_mde": GEP_MDE_MAX, "draws": n_draws, "seed": seed, "pass": bool(math.isfinite(m) and m <= GEP_MDE_MAX)}


def census_e(rdir: Path, *, n_draws: int = c12.GMP_DRAWS) -> dict:
    """q0266 (E census). Opens no outcome file and never evaluates a catalogue outcome (the catalogue reaches it only through ``usable`` at t - 72 h)."""
    data = load_frame(rdir)
    report = json.loads((Path(rdir) / "frame_report.json").read_text())
    units, mc = build_units(data)
    av = [u for u in units if u["label"] == "available"]
    mk = {u["market_id"] for u in av}
    ev = {u["event_id"] for u in av}
    wk = {u["week"] for u in av}
    cp = {u["component"] for u in av}
    n_mem_all = sum(v for k, v in mc.items() if k.startswith("member:"))
    n_fail = sum(v for k, v in mc.items() if k.startswith("member:parser failure"))
    # denominator = members of a frozen class (binary, non-regional): parsed, parser failures and "threshold not modelled" (not binary / regional / not a frozen class are not rule-parser targets)
    n_mem = sum(v for k, v in mc.items() if k == "member:ok" or k.startswith("member:parser failure") or k == "member:threshold not modelled")
    comp_sizes = Counter(Counter(u["component"] for u in av).values())
    ge = {"markets": len(mk), "events": len(ev), "weeks": len(wk), "components": len(cp), "min": GE_MIN, "parser_failure_share": n_fail / n_mem if n_mem else 0.0, "parser_failure_max": PARSER_FAIL_MAX,
          "parser_failure_denominator": "frozen-class binary non-regional members of kept in-window events", "n_frozen_class_members": n_mem, "n_members_all": n_mem_all,
          "parser_failure_share_all_members": n_fail / n_mem_all if n_mem_all else 0.0}
    ge["pass_dependence"] = bool(len(mk) >= GE_MIN["markets"] and len(ev) >= GE_MIN["events"] and len(wk) >= GE_MIN["weeks"] and len(cp) >= GE_MIN["components"])
    ge["pass_parser"] = bool(ge["parser_failure_share"] <= PARSER_FAIL_MAX)
    out = {"version": "cb12-census-E-v1", "counts_only": True, "label": LABEL_E, "frame_report": report, "member_counts": mc, "unit_labels": dict(Counter(u["label"] for u in units)),
           "events_by_class": dict(Counter(e["klass"] for e in data["events"].values())), "available_by_class": dict(Counter(u["klass"] for u in av)),
           "component_unit_sizes": {str(k): v for k, v in sorted(comp_sizes.items())}, "q_quantiles": [float(x) for x in np.quantile([u["q"] for u in av], [0.1, 0.5, 0.9])] if av else [],
           "q_minus_preg_quantiles": [float(x) for x in np.quantile([u["q"] - u["p_reg"] for u in av], [0.1, 0.5, 0.9])] if av else [], "GE": ge,
           "label_thinned": report.get("label_thinned")}
    if not ge["pass_parser"]:
        out["label_E"], out["GEP"] = "not testable (rule parser)", {"pass": False, "note": "not computed"}
    elif not ge["pass_dependence"]:
        out["label_E"], out["GEP"] = "not testable (dependence)", {"pass": False, "note": "not computed"}
    else:
        out["GEP"] = gep(av, n_draws=n_draws)
        out["label_E"] = None if out["GEP"]["pass"] else "not run (power)"
    return out


def not_run_result(label: str) -> dict:
    return {"p": 1.0, "testable": False, "advance": False, "verdict": label, "label": LABEL_E, "effect": None, "n": 0}


def attach_outcomes(units: list[dict], cat: np.ndarray, gamma_rows: list[dict] | None) -> None:
    gy = {}
    for r in gamma_rows or []:
        gy[r["market_id"]] = gamma_yes(r)
    for u in units:
        if u["label"] == "available":
            u["y"] = outcome_of(u, cat)
            u["y_gamma"] = gy.get(u["market_id"])


def gamma_yes(row: dict | None) -> float | None:
    if not row:
        return None
    v = [c12.num(x) for x in c12.listish(row.get("outcome_prices"))]
    yi = int(row.get("yes_index") or 0)
    if len(v) != 2 or not all(math.isfinite(x) for x in v) or "resolved" not in str(row.get("uma_status") or "").lower():
        return None
    if abs(v[yi] - 1) < 1e-9 and abs(v[1 - yi]) < 1e-9:
        return 1.0
    if abs(v[yi]) < 1e-9 and abs(v[1 - yi] - 1) < 1e-9:
        return 0.0
    if abs(v[yi] - 0.5) < 1e-9 and abs(v[1 - yi] - 0.5) < 1e-9:
        return 0.5
    return None


def screen_e(rdir: Path, census: dict) -> dict:
    """q0253: E1 on the Stage-1 units; the catalogue outcome is computed here; the Gamma outcome file is opened here (agreement audit and robustness only). The three unit
    sets (72 h lag, 7-day lag, Poisson) share one pass over the members."""
    lab = census.get("label_E")
    thin = census.get("label_thinned")
    if lab:
        return {"E1": add_labels(not_run_result(lab), [thin]), "label": LABEL_E, "census_label": lab}
    data = load_frame(rdir)
    sets, _ = build_units_multi(data, {"base": {"lag_s": CAT_LAG_S}, "lag7": {"lag_s": CAT_LAG_ROBUST_S}, "poisson": {"lag_s": CAT_LAG_S, "poisson": True}})
    cat = data["cat45"] if len(data["cat45"]) else data["cat6"]
    outs = c12.open_guarded(Path(rdir) / "outcomes_guarded.csv.gz", "screen-E")
    for v in sets.values():
        attach_outcomes(v, cat, outs)
    res = e1_test(sets["base"], units_lag7=sets["lag7"], cat=cat)
    po = [u for u in sets["poisson"] if u["label"] == "available" and u.get("y") is not None]
    pv = e1_slope(po) if len(po) >= 3 else {"beta": math.nan, "p": 1.0}
    res.setdefault("reported", {})["poisson_variant"] = {"beta": pv["beta"], "p": pv["p"], "n": len(po), "note": "reported only; k_m infinite, same lambda_m"}
    add_labels(res, [thin])
    return {"E1": res, "label": LABEL_E, "census_label": None, "label_thinned": thin}


# =====================================================================================================================================================
# Stage 2: the collector (q0257) and the rep (q0258)
# =====================================================================================================================================================


def book_state(doc: Any, receipt_t: float) -> dict:
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

    bids, asks = sorted(lv("bids"), key=lambda z: -z[0]), sorted(lv("asks"), key=lambda z: z[0])
    bb, ba = (bids[0] if bids else None), (asks[0] if asks else None)
    return {"ok": True, "receipt_t": receipt_t, "bid": bb[0] if bb else None, "bid_size": bb[1] if bb else None, "ask": ba[0] if ba else None, "ask_size": ba[1] if ba else None,
            "crossed": bool(bb and ba and bb[0] >= ba[0]), "bids": bids[:5], "asks": asks[:5]}


def _wjson_gz(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(doc, sort_keys=True, default=float).encode(), mtime=0))
    tmp.replace(path)


def _rjson_gz(path: Path) -> Any:
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def live_pass_label(now: float) -> str | None:
    h = datetime.fromtimestamp(now, UTC)
    for hh in LIVE_PASSES_UTC:
        t0 = h.replace(hour=hh, minute=0, second=0, microsecond=0).timestamp()
        if t0 <= now < t0 + LIVE_PASS_WINDOW_S:
            return f"{hh:02d}00"
    return None


def store_events(rows: list[list], now: float) -> list[list]:
    """The stored subset of a served USGS read: every event >= 5.5, plus every event of the last 10 days."""
    cut = (now - LIVE_STORE_RECENT_DAYS * DAY) * 1000.0
    return [r for r in rows if r[3] >= LIVE_STORE_MIN_MAG - 1e-9 or r[0] >= cut]


def live_pass(root: Path, now: float, src, *, rules_sha: str, sleep=time.sleep, pending_starts: Iterable[float] = ()) -> dict:
    """One collection pass: open earthquake events (both tags, closed=false), members parsed by the frozen parser, two receipt-timed /book reads per parsed member
    (<= 80) >= 60 s apart, one USGS read from min(earliest open rule-window start, the window starts still awaiting their outcome read (``pending_starts``), now - 30 d),
    capped at 400 days back (M >= 4.5, as served; stored subset). Written to ``<date>_<HHMM>.json.gz`` (atomically)."""
    lab = live_pass_label(now)
    day = datetime.fromtimestamp(now, UTC).date().isoformat()
    path = Path(root) / f"{day}_{lab}.json.gz"
    evs: dict[str, dict] = {}
    for tag in TAG_IDS:
        for e in src.open_events(tag):
            evs.setdefault(str(e.get("id")), e)
    members, reasons = [], Counter()
    for eid in sorted(evs):
        p = parse_event(evs[eid])
        if p is None:
            continue
        for m in p[1]:
            reasons[m["parse"]] += 1
            if m["parse"] == "ok":
                members.append(m)
    members.sort(key=lambda m: c12.rank("arepo-cb12-quake-cap", m["market_id"]))
    if len(members) > LIVE_MAX_MEMBERS:
        reasons["unavailable (collection cap)"] += len(members) - LIVE_MAX_MEMBERS
        members = members[:LIVE_MAX_MEMBERS]
    books: dict[str, list] = {m["market_id"]: [] for m in members}
    first: dict[str, float] = {}
    for rnd in (0, 1):
        for m in members:
            if rnd == 1:
                wait = first[m["market_id"]] + LIVE_BOOK_GAP_S - src.clock()
                if wait > 0:
                    sleep(wait)
            try:
                doc, rt = src.book(m["token_yes"])
            except RuntimeError:
                doc, rt = None, src.clock()
            if rnd == 0:
                first[m["market_id"]] = rt
            books[m["market_id"]].append(book_state(doc, rt))
    starts = [m["win_start"] for m in members if math.isfinite(m["win_start"])] + [x for x in pending_starts if math.isfinite(x)]
    want0 = min(min(starts, default=now), now - LIVE_USGS_SPAN_MIN_DAYS * DAY)
    span0 = max(want0, now - LIVE_USGS_SPAN_CAP_DAYS * DAY)
    cut = sum(1 for x in starts if x < span0)  # window starts the 400-day cap cut off: their count c_t is undercounted, so their units are labelled (never silently kept)
    try:
        rows, rt = src.usgs(span0, now)
        usgs = {"ok": True, "receipt_t": rt, "from": span0, "n_served": len(rows), "events": store_events(rows, now), "n_window_starts_cut_by_cap": cut}
    except (cm.ApiError, RuntimeError) as exc:
        usgs = {"ok": False, "error": str(exc)[:120]}
    rec = {"version": "cb12-quake-pass-v1", "rules_sha256": rules_sha, "day": day, "pass": lab, "t_start": now, "members": members, "member_parse": dict(reasons), "books": books, "usgs": usgs}
    _wjson_gz(path, rec)
    return {"path": path, "n_members": len(members), "usgs_ok": usgs["ok"], "windows": {m["market_id"]: [m["win_start"], m["win_end"]] for m in members}}


def live_outcomes(root: Path, now: float, src, state: dict) -> int:
    """Guarded: the Gamma resolution of every collected member whose window ended >= 72 h ago -> ``outcomes_guarded.csv.gz`` (rewritten as rows accumulate)."""
    gp = Path(root) / LIVE_OUTCOMES_FILE
    have = {r["market_id"]: r for r in c12.read_csv_gz(gp)} if gp.exists() else {}
    mem: dict[str, dict] = {}
    for p in sorted(Path(root).glob("*_*.json.gz")):
        for m in _rjson_gz(p).get("members") or []:
            if math.isfinite(c12.num(m.get("win_end"))) and now >= m["win_end"] + E2_OUTCOME_AFTER_S:
                mem[m["market_id"]] = m
    todo = sorted(set(mem) - set(have))
    for i in range(0, len(todo), c12.LOOKUP_PER_REQUEST):
        try:
            rows = src.gamma_markets(todo[i:i + c12.LOOKUP_PER_REQUEST])
        except (cm.ApiError, RuntimeError):
            break
        for g in rows:
            gid = str(g.get("id")) if isinstance(g, dict) else ""
            if gid in todo and g.get("closed"):
                statuses = g.get("umaResolutionStatuses")
                have[gid] = {"market_id": gid, "event_id": mem[gid]["event_id"], "yes_index": mem[gid]["yes_index"], "outcome_prices": json.dumps(c12.listish(g.get("outcomePrices"))),
                             "uma_status": str(g.get("umaResolutionStatus") or (statuses if statuses else ""))}
    if have:
        gp.write_bytes(hb._gz_csv_bytes(OUTCOME_COLUMNS, [[have[k][c] for c in OUTCOME_COLUMNS] for k in sorted(have)]))
    state["outcomes"] = {"t": now, "n_resolved": len(have), "n_due": len(mem)}
    return len(have)


def open_live_outcomes(root: Path, job: str) -> list[dict]:
    """The Stage-2 Gamma outcome file (guarded: written by the collector's outcome step, opened only by the rep job)."""
    if job != "rep-E":
        raise Refused(f"the Stage-2 outcome file may be opened only by rep-E, not {job!r}")
    p = Path(root) / LIVE_OUTCOMES_FILE
    return list(c12.read_csv_gz(p)) if p.exists() else []


def e2_start(root: Path, frozen_epoch: float) -> float | None:
    """T12_E2_start: the createdAt of the first earthquake market listed >= 1 day after the E freeze, among collected members (None until one is seen)."""
    best = None
    for p in sorted(Path(root).glob("*_*.json.gz")):
        for m in _rjson_gz(p).get("members") or []:
            c = c12.num(m.get("created_epoch"))
            if math.isfinite(c) and c >= frozen_epoch + E2_START_DELAY_DAYS * DAY and (best is None or c < best):
                best = c
    return best


def mark_missed_slots(state: dict, frozen_epoch: float, now: float) -> int:
    """Record every scheduled slot (10:00Z / 16:00Z) since the E freeze whose 30-minute window has closed and that has no pass record as 'unavailable (collection)'
    (counted, never back-filled). Returns the number newly recorded."""
    n = 0
    d = datetime.fromtimestamp(frozen_epoch, UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    while d.timestamp() <= now:
        for hh in LIVE_PASSES_UTC:
            t0 = d.timestamp() + hh * HOUR
            key = f"{d.date().isoformat()}_{hh:02d}00"
            if t0 >= frozen_epoch and t0 + LIVE_PASS_WINDOW_S <= now and key not in state["passes"]:
                state["passes"][key] = {"status": "unavailable (collection)"}
                n += 1
        d += timedelta(days=1)
    return n


def _pending_update(state: dict, windows: dict[str, list[float]], now: float) -> None:
    """Windows whose catalogue outcome read is still to come: the next pass's USGS span must reach back to their starts."""
    pend = state.setdefault("pending_windows", {})
    pend.update(windows)
    for k in [k for k, w in pend.items() if w[1] + E2_OUTCOME_AFTER_S + DAY <= now]:
        del pend[k]


def quake_live_tick(root: Path, *, now: float, src, rules_sha: str, frozen_epoch: float, disk_check: Callable[[], None] | None = None, sleep=time.sleep) -> dict:
    """One idempotent collector call (cron at 10:00Z and 16:00Z). A pass runs at the first call in [HH:00, HH:30) and is recorded in ``state.json``: 'ok', 'failed' (retried
    at the next call inside the window, at most 3 tries; a pass file already on disk is adopted, never re-read), 'unavailable (host disk)'. A slot with no record once its
    window has closed is 'unavailable (collection)' (counted, never back-filled). After T12_E2_collect_max (start + 90 d) no pass runs; the outcome step continues
    until every due market is resolved."""
    root = c12.require_output_root(Path(root))
    root.mkdir(parents=True, exist_ok=True)
    if now < frozen_epoch:
        raise Refused("quake-live runs only after the E freeze")
    lock = open(root / ".lock", "w")  # noqa: SIM115
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return {"status": "busy"}
    try:
        sp, mp = root / "state.json", root / "manifest.json"
        state = json.loads(sp.read_text()) if sp.exists() else {"passes": {}}
        state.setdefault("passes", {})
        man = json.loads(mp.read_text()) if mp.exists() else {"run_id": LIVE_RUN, "kind": "cb12_quake_live", "evidence_role": "prospective", "file_sha256": {}}
        start = e2_start(root, frozen_epoch)
        cmax = start + E2_MAX_DAYS * DAY if start is not None else None
        if start is not None:
            state["T12_E2_start"], state["T12_E2_collect_max"] = cm.iso(start), cm.iso(cmax)
        lab = live_pass_label(now)
        day = datetime.fromtimestamp(now, UTC).date().isoformat()
        key = f"{day}_{lab}"
        out: dict = {"status": "idle"}
        prev = state["passes"].get(key) or {}
        retry = prev.get("status") == "failed" and int(prev.get("attempts") or 0) < LIVE_PASS_MAX_ATTEMPTS
        if cmax is not None and now >= cmax:
            out = {"status": "quake_live_complete"}
        elif lab and (not prev or retry):
            path = root / f"{key}.json.gz"
            r = None
            try:
                if path.exists():  # written before a crash could record it: adopt (a second read would fork p_t)
                    rec0 = _rjson_gz(path)
                    r = {"path": path, "n_members": len(rec0.get("members") or []), "usgs_ok": bool((rec0.get("usgs") or {}).get("ok")),
                         "windows": {m["market_id"]: [m["win_start"], m["win_end"]] for m in rec0.get("members") or []}, "adopted": True}
                else:
                    if disk_check is not None:
                        disk_check()
                    pend = [w[0] for w in (state.get("pending_windows") or {}).values()]
                    r = live_pass(root, now, src, rules_sha=rules_sha, sleep=sleep, pending_starts=pend)
            except NotNow as exc:
                state["passes"][key] = {"status": "unavailable (host disk)", "why": str(exc)[:160]}
                out = {"status": "pass_unavailable_disk", "pass": key}
            except (cm.ApiError, RuntimeError, OSError, ValueError) as exc:
                state["passes"][key] = {"status": "failed", "attempts": int(prev.get("attempts") or 0) + 1, "why": f"{type(exc).__name__}: {exc}"[:160]}
                out = {"status": "pass_failed", "pass": key}
            if r is not None:
                from . import h5_seal  # noqa: PLC0415

                man.setdefault("file_sha256", {})[r["path"].name] = h5_seal.sha256_file(r["path"])
                state["passes"][key] = {"status": "ok", "n_members": r["n_members"], "usgs_ok": r["usgs_ok"], **({"adopted": True} if r.get("adopted") else {})}
                _pending_update(state, r["windows"], now)
                out = {"status": "pass", "pass": key, "n_members": r["n_members"]}
            cm.write_json_atomic(sp, state)  # the record of this attempt survives a crash in the steps below
        if lab == "1600" or out["status"] == "quake_live_complete":
            n = live_outcomes(root, now, src, state)
            gp = root / LIVE_OUTCOMES_FILE
            if gp.exists():
                from . import h5_seal  # noqa: PLC0415

                man["file_sha256"][gp.name] = h5_seal.sha256_file(gp)
            out["n_resolved"] = n
        mark_missed_slots(state, frozen_epoch, now if cmax is None else min(now, cmax))
        man.update(updated_utc=cm.iso(now), rules_sha256=rules_sha, status="collecting")
        cm.write_json_atomic(sp, state)
        cm.write_json_atomic(mp, man)
        return out
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


class LiveSources:
    """Polymarket through ``pm`` (<= 1 rps for this collector), USGS through ``ext`` (<= 1 rps)."""

    def __init__(self, pm, ext, clock: Callable[[], float] = time.time):
        self.pm, self.ext, self.clock = pm, ext, clock

    def open_events(self, tag: int) -> list[dict]:
        st, data = self.pm.get(c12.GAMMA_EVENTS, {"closed": "false", "tag_id": tag, "limit": c12.GAMMA_PAGE, "offset": 0})
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma events status {st}")
        return [x for x in data if isinstance(x, dict)]

    def book(self, token: str) -> tuple[Any, float]:
        st, doc = self.pm.get("https://clob.polymarket.com/book", {"token_id": token}, max_retries=2)
        return (doc if st == 200 else None), self.clock()

    def usgs(self, t0: float, t1: float) -> tuple[list[list], float]:
        st, doc = self.ext.get(USGS_QUERY, usgs_params(datetime.fromtimestamp(t0, UTC).strftime("%Y-%m-%dT%H:%M:%S"), datetime.fromtimestamp(t1, UTC).strftime("%Y-%m-%dT%H:%M:%S"), 4.5))
        if st != 200:
            raise cm.ApiError(f"usgs status {st}")
        return usgs_rows(doc), self.clock()

    def gamma_markets(self, ids: list[str]) -> list[dict]:
        st, rows = self.pm.get(hb.GAMMA_MARKETS, {"id": list(ids), "closed": "true", "limit": c12.LOOKUP_PER_REQUEST})
        if st != 200 or not isinstance(rows, list):
            raise cm.ApiError(f"gamma markets status {st}")
        return rows


def _mid(b: dict) -> float | None:
    if not b or not b.get("ok") or b.get("crossed") or b.get("bid") is None or b.get("ask") is None:
        return None
    return (b["bid"] + b["ask"]) / 2.0


def _live_unit(m: dict, t: float, rec_t: float) -> dict:
    return {"market_id": m["market_id"], "event_id": m["event_id"], "klass": m["klass"], "threshold": m["threshold"], "lo": m["lo"], "hi": m["hi"], "win_start": m["win_start"],
            "win_end": m["win_end"], "tz": m["tz"], "t": t if math.isfinite(t) else rec_t, "week": c12.iso_week_of(rec_t), "yes_index": m["yes_index"], "fee_rate": m["fee_rate"]}


def _outcome_catalogue(m: dict, reads: list) -> np.ndarray | None:
    """The catalogue for the outcome of market ``m``: the first valid pass read >= 72 h after the window end, used ONLY if its span reached back to the window start (a later
    span start would undercount) and, for E-c (day maxima need every M >= 4.5 event of the day), the day lies inside the read's stored last-10-days. Else None
    ('unavailable (outcome read)'); never taken from another read."""
    later = next((r for t_, r in reads if t_ >= m["win_end"] + E2_OUTCOME_AFTER_S), None)
    if later is None:
        return None
    us = later["usgs"]
    if not (us.get("from") is not None and us["from"] <= m["win_start"]):
        return None
    if m["klass"] == "E-c" and m["win_start"] < later["t_start"] - LIVE_STORE_RECENT_DAYS * DAY:
        return None
    return np.array(sorted((r[0] / 1000.0, r[3]) for r in us["events"]), float).reshape(-1, 2)


def live_units(root: Path, start: float, end: float, model: dict, maxima: dict, *, lag_s: float = CAT_LAG_S, now: float | None = None) -> tuple[list[dict], dict]:
    """Stage-2 units: 16:00Z checkpoints of markets whose windows end in [start, end): p_t = first 16:00Z read mid, p_reg = first 10:00Z read mid of the same day (a separate
    pass), p_alt = first 16:00Z read mid 48 h earlier; q from the 16:00Z pass's USGS read (events before t - 72 h); the outcome from the first pass read >= 72 h after
    the window end (``_outcome_catalogue``). A day with no 16:00Z pass file gives every member of the latest earlier pass a unit 'unavailable (collection)' (counted);
    a unit whose window start the 400-day span cap cut off is 'unavailable (span cap)'; an available unit without a valid outcome read carries
    ``outcome_label`` 'unavailable (outcome read)' (``effective_label``)."""
    passes = {}
    for p in sorted(Path(root).glob("*_*.json.gz")):
        rec = _rjson_gz(p)
        passes[(rec["day"], rec["pass"])] = rec
    reads = sorted(((r["t_start"], r) for r in passes.values() if r["usgs"].get("ok")), key=lambda z: z[0])
    ordered = sorted(passes.values(), key=lambda r: r["t_start"])
    units, lab = [], Counter()
    for (day, ps), rec in sorted(passes.items()):
        if ps != "1600":
            continue
        cat = np.array(sorted((r[0] / 1000.0, r[3]) for r in rec["usgs"].get("events") or []), float).reshape(-1, 2) if rec["usgs"].get("ok") else None
        reg = passes.get((day, "1000"))
        alt = passes.get(((datetime.fromisoformat(day) - timedelta(days=2)).date().isoformat(), "1600"))
        for m in rec["members"]:
            if not (start <= m["win_end"] < end):
                continue
            b1 = (rec["books"].get(m["market_id"]) or [{}])[0]
            u = _live_unit(m, c12.num(b1.get("receipt_t")), rec["t_start"])
            last = m["win_start"] - 1 if m["klass"] == "E-c" else m["win_end"] - END_BUFFER_S
            pt = _mid(b1)
            if u["t"] > last or not (math.isfinite(m["created_epoch"]) and m["created_epoch"] <= u["t"] - LIST_BUFFER_S):
                lab["not eligible (listing / end buffer)"] += 1
                continue
            if pt is None or cat is None:
                units.append({**u, "label": "unavailable (16:00Z read)"})
                continue
            if m["klass"] != "E-c" and not (rec["usgs"].get("from") is not None and rec["usgs"]["from"] <= m["win_start"]):
                units.append({**u, "label": "unavailable (span cap)"})
                continue
            pr = _mid(((reg or {}).get("books") or {}).get(m["market_id"], [{}])[0]) if reg else None
            if pr is None:
                units.append({**u, "label": "unavailable (no earlier read)"})
                continue
            if ambiguous(u, cat):
                units.append({**u, "label": "ambiguous recent quake"})
                continue
            q, why = q_of(u, model, cat, maxima, lag_s=lag_s)
            if why:
                units.append({**u, "label": why})
                continue
            pa = _mid(((alt or {}).get("books") or {}).get(m["market_id"], [{}])[0]) if alt else None
            ycat = _outcome_catalogue(m, reads)
            units.append({**u, "label": "available", "p_t": pt, "p_reg": pr, "p_alt": pa, "q": q, "a_yes": b1["ask"], "b_yes": b1["bid"], "ask_size": b1["ask_size"],
                          "bid_size": b1["bid_size"], "y": outcome_of(u, ycat) if ycat is not None else None,
                          **({} if ycat is not None else {"outcome_label": "unavailable (outcome read)"})})
    if ordered:  # days without a 16:00Z pass file: the earlier pass's members are the units that were not collected
        d0 = datetime.fromtimestamp(ordered[0]["t_start"], UTC).date()
        d1 = datetime.fromtimestamp(min(end, now if now is not None else ordered[-1]["t_start"]), UTC).date()
        for i in range((d1 - d0).days + 1):
            d = d0 + timedelta(days=i)
            if (d.isoformat(), "1600") in passes:
                continue
            t = datetime(d.year, d.month, d.day, CHECKPOINT_HOUR_UTC, tzinfo=UTC).timestamp()
            prior = [r for r in ordered if r["t_start"] < t]
            for m in (prior[-1]["members"] if prior else []):
                last = m["win_start"] - 1 if m["klass"] == "E-c" else m["win_end"] - END_BUFFER_S
                if start <= m["win_end"] < end and t <= last and math.isfinite(m["created_epoch"]) and m["created_epoch"] <= t - LIST_BUFFER_S:
                    units.append({**_live_unit(m, t, t), "label": "unavailable (collection)"})
    return units, dict(lab)


def live_big_events(root: Path) -> np.ndarray:
    """(origin epoch s, mag) of every stored M >= 7.5 event over all collection passes (deduplicated), for the 30-day big-quake robustness of E1-rep."""
    seen: dict[float, float] = {}
    for p in sorted(Path(root).glob("*_*.json.gz")):
        for r in (_rjson_gz(p).get("usgs") or {}).get("events") or []:
            if r[3] >= BIG_QUAKE - 1e-9:
                seen[r[0] / 1000.0] = r[3]
    return np.array(sorted(seen.items()), float).reshape(-1, 2)


def e2_end(units: list[dict], comp: dict[str, str], start: float, cmax: float) -> float:
    """T12_E2_end: the later of start + 56 days and the first date by which >= 30 window components with >= 1 Stage-2 unit have resolved (all windows ended);
    never after T12_E2_collect_max. Counts components, never results."""
    ends: dict[str, float] = {}
    for u in units:
        c = comp.get(u["event_id"], u["event_id"])
        ends[c] = max(ends.get(c, -math.inf), u["win_end"])
    lo = start + E2_MIN_DAYS * DAY
    ts = sorted(ends.values())
    if len(ts) >= c12.MIN_CLUSTERS:
        return min(max(lo, ts[c12.MIN_CLUSTERS - 1]), cmax)
    return cmax


def e2_trades(units: list[dict], *, cost: float = 0.0) -> list[dict]:
    out, seen = [], set()
    for u in sorted((u for u in units if u["label"] == "available"), key=lambda z: (z["market_id"], z["t"])):
        if u["market_id"] in seen:
            continue
        a_no = 1.0 - u["b_yes"] if u.get("b_yes") is not None else None
        side = "yes" if u.get("a_yes") is not None and u["q"] - u["a_yes"] >= E2_EDGE - 1e-12 else ("no" if a_no is not None and (1 - u["q"]) - a_no >= E2_EDGE - 1e-12 else None)
        if side is None:
            continue
        seen.add(u["market_id"])
        a = (u["a_yes"] if side == "yes" else a_no) + cost
        r = max(c12.num(u.get("fee_rate")) if math.isfinite(c12.num(u.get("fee_rate"))) else 0.0, E2_FEE_FLOOR)
        yg = u.get("y_gamma")
        pay = None if yg is None else (yg if side == "yes" else 1.0 - yg)
        out.append({**u, "side": side, "a": a, "net": None if pay is None else pay - a - r * a * (1 - a)})
    return out


def rep_e(root: Path, tests: tuple[str, ...], *, frozen_epoch: float, now: float, model: dict, maxima: dict, gamma_rows: list[dict], k2: int | None = None) -> dict:
    """q0258: E1-rep and E2 on Stage-2 units of windows ending in [T12_E2_start, T12_E2_end). Each needs >= 100 units and >= 30 window components, else "not run
    (power)", counted. Runs only after T12_E2_end + 2 days."""
    start = e2_start(root, frozen_epoch)
    if start is None:
        raise NotNow("T12_E2_start not reached (no earthquake market listed >= 1 day after the E freeze yet)")
    cmax = start + E2_MAX_DAYS * DAY
    pre, _ = live_units(root, start, cmax, model, maxima, now=now)
    evs = {}
    for u in pre:
        evs.setdefault(u["event_id"], {"event_id": u["event_id"], "win_start": u["win_start"], "win_end": u["win_end"]})
        evs[u["event_id"]]["win_start"] = min(evs[u["event_id"]]["win_start"], u["win_start"])
        evs[u["event_id"]]["win_end"] = max(evs[u["event_id"]]["win_end"], u["win_end"])
    comp = components(list(evs.values()))
    end = e2_end([u for u in pre if u["label"] == "available"], comp, start, cmax)
    if now < end + 2 * DAY:
        raise NotNow(f"q0258 runs after T12_E2_end + 2 d ({cm.iso(end + 2 * DAY)})")
    units, lab = live_units(root, start, end, model, maxima, now=now)
    gy = {r["market_id"]: gamma_yes(r) for r in gamma_rows}
    for u in units:
        u["component"] = comp.get(u["event_id"], f"E{u['event_id']}")
        u["y_gamma"] = gy.get(u["market_id"])
    units7, _ = live_units(root, start, end, model, maxima, lag_s=CAT_LAG_ROBUST_S, now=now)
    for u in units7:
        u["component"] = comp.get(u["event_id"], f"E{u['event_id']}")
    out: dict = {"label": LABEL_E, "T12_E2_start": cm.iso(start), "T12_E2_end": cm.iso(end), "T12_E2_collect_max": cm.iso(cmax), "k2": k2, "unit_labels": dict(Counter(effective_label(u) for u in units)), "skipped": lab,
           "collection_passes": dict(Counter((v.get("status") or "") for v in ((json.loads((Path(root) / "state.json").read_text()) if (Path(root) / "state.json").exists() else {}).get("passes") or {}).values()))}
    av = [u for u in units if u["label"] == "available"]
    ncomp = len({u["component"] for u in av})
    power_ok = bool(len(av) >= c12.MIN_UNITS and ncomp >= c12.MIN_CLUSTERS)
    for t in tests:
        if not power_ok:
            r = {**not_run_result("not run (power)"), "n_units": len(av), "n_components": ncomp}
        elif t == "E1":
            r = e1_test(units, units_lag7=units7, cat=live_big_events(root), window=(start, end))
        else:
            trades = e2_trades(units)
            tr = [x for x in trades if x["net"] is not None]
            n_unres = len(trades) - len(tr)  # taken at the first 16:00Z checkpoint but not yet resolved by the venue: counted, not dropped silently
            v = np.array([x["net"] for x in tr], float)
            if len(v) < c12.MIN_UNITS:
                r = {**not_run_result("not run (power)"), "n": len(v), "n_trades": len(trades), "n_unresolved": n_unres}
            else:
                cp = c12.cluster_p(v, ways(tr))
                c5 = [x["net"] for x in e2_trades(units, cost=E2_COST_ROBUST) if x["net"] is not None]
                rob = {"ask_plus_0.5c_net_positive": bool(c5 and float(np.mean(c5)) > 0)}
                r = {"test": "E2", "label": LABEL_E, "n": len(v), "net_per_share": float(v.mean()), "effect": float(v.mean()), "p": cp["p"], "testable": cp["testable"], "ways": cp["ways"],
                     "floor_ok": bool(v.mean() >= E2_FLOOR), "robustness": rob, "robustness_ok": all(rob.values()), "placebo_declared": False,
                     "n_trades": len(trades), "n_unresolved": n_unres}
                r["verdict"] = "computed"
        r["stage2_early_alpha_over_10"] = c12.early_stage2_ok(r.get("p"))
        r["stage2_pass_alpha_over_k"] = bool(r.get("testable") and r.get("p", 1.0) < (c12.STAGE_ALPHA / k2 if k2 else c12.STAGE_ALPHA / c12.STAGE2_K_MAX) and r.get("floor_ok")
                                             and r.get("robustness_ok") and (t == "E2" or ((r.get("placebo") or {}).get("holds", False) and (r.get("independent_price_placebo") or {}).get("credit", False))))
        out[f"{t}_rep"] = r
    return out


# =====================================================================================================================================================
# Smoke (family E checks)
# =====================================================================================================================================================


def smoke_offline(ctx: dict) -> dict:
    """Fixtures: the census accessor never returns an event at or after t - 72 h; checkpoints before 2024-09-04T16:00Z are labelled, not used; the model fit refuses a
    row at or after 2024-09-01; the rule parser on the three out-of-window templates; the window components of overlapping weekly and monthly events."""
    cat = np.array([[100.0, 6.5], [200.0, 7.0]])
    acc = bool(len(usable(cat, 200.0 + CAT_LAG_S)) == 1 and len(usable(cat, 200.0 + CAT_LAG_S + 1)) == 2)
    try:
        fit_model(np.array([[_ep(FIT_END), 6.5]]))
        fit_ok = False
    except Refused:
        fit_ok = True
    ec = parse_member({"id": "1", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "question": "Will the biggest earthquake on October 2, 2026 be 5.3 to 5.4?",
                       "description": "largest earthquake recorded globally ... USGS Earthquake Catalog. The observation period is the UTC calendar day: 00:00 UTC to 23:59 UTC on October 2, 2026."},
                      {"id": "e", "title": "What will the biggest earthquake be on October 2, 2026?"})
    ea = parse_member({"id": "2", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "question": "Will there be 5 earthquakes of 6.5 or above magnitude worldwide?", "groupItemTitle": "5",
                       "description": "magnitude of 6.5 or higher that occur anywhere on Earth between September 28, 2026, 12:00 AM ET and October 4, 2026, 11:59 PM ET. United States Geological Survey (USGS)"},
                      {"id": "e2", "title": "How many 6.5 or above earthquakes worldwide September 28 - October 4?"})
    eb = parse_member({"id": "3", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "question": "Will a 7.0+ earthquake occur worldwide by October 31?", "createdAt": "2026-09-30T14:01:10Z",
                       "description": "United States Geological Survey (USGS) reports an earthquake ... anywhere in the world, with an origin time between market creation and October 31, 2026 11:59:59 PM ET."},
                      {"id": "e3", "title": "How strong of an earthquake will occur worldwide by October 31?"})
    parse_ok = bool(ec["parse"] == "ok" and ec["tz"] == "UTC" and ea["parse"] == "ok" and (ea["lo"], ea["hi"]) == (5, 5) and eb["parse"] == "ok" and eb["threshold"] == 7.0)
    comp = components([{"event_id": "w1", "win_start": 0, "win_end": 7}, {"event_id": "w2", "win_start": 7, "win_end": 14}, {"event_id": "mo", "win_start": 0, "win_end": 30},
                       {"event_id": "x", "win_start": 40, "win_end": 41}])
    comp_ok = bool(comp["w1"] == comp["w2"] == comp["mo"] != comp["x"])
    ck = checkpoints_for({"klass": "E-a", "created_epoch": _ep("2024-09-01T00:00:00Z"), "end_epoch": _ep("2024-09-10T00:00:00Z"), "win_start": _ep("2024-09-01T04:00:00Z"),
                          "win_end": _ep("2024-09-09T04:00:00Z")})
    ck_ok = bool(ck and ck[0] < _ep(CHECKPOINT_START))
    ok = bool(acc and fit_ok and parse_ok and comp_ok and ck_ok)
    return {"guards_fixture_E": {"pass": ok, "accessor_t_minus_72h": acc, "fit_refuses_late_rows": fit_ok, "parser_templates": parse_ok, "components": comp_ok, "checkpoint_start_labelled": ck_ok}}


def smoke_online(lim, ctx: dict) -> dict:
    """The frozen classes and rule parser on 3 out-of-window earthquake events (endDate >= 2026-10-01; parse success recorded); USGS count and query (the 1976 rate
    chunk returns <= 20,000 rows). Counts and booleans only."""
    picked, per = [], {}
    for tag in TAG_IDS:
        st, data = lim.get(c12.GAMMA_EVENTS, {"closed": "true", "tag_id": tag, "end_date_min": SMOKE_OUT_OF_WINDOW, "order": "id", "ascending": "true", "limit": 100, "offset": 0})
        for e in data if st == 200 and isinstance(data, list) else []:
            p = parse_event(e)
            if p and p[0]["klass"] in ("E-a", "E-b", "E-c") and p[0]["klass"] not in {x[0]["klass"] for x in picked}:
                picked.append(p)
    for p in picked[:SMOKE_N_EVENTS]:
        n_ok = sum(1 for m in p[1] if m["parse"] == "ok")
        per[p[0]["klass"]] = {"n_members": len(p[1]), "n_parsed": n_ok, "parse_reasons": dict(Counter(m["parse"] for m in p[1]))}
    st1, cnt = lim.get(USGS_COUNT, {**usgs_params(*CAT_M6_CHUNKS[0], 6.0)})
    st2, doc = lim.get(USGS_QUERY, usgs_params(*CAT_M6_CHUNKS[0], 6.0))
    n = len(usgs_rows(doc)) if st2 == 200 else 0
    return {"e_parser_out_of_window": {"pass": bool(per and all(v["n_parsed"] > 0 for v in per.values())), "per_class": per, "n_examined": len(per),
                                       "rule": "every examined out-of-window event of a frozen class parses at least one member; classes found recorded"},
            "e_usgs": {"pass": bool(st1 == 200 and st2 == 200 and 0 < n <= USGS_MAX_ROWS), "count_status": st1, "query_status": st2, "rows_1976_chunk": n,
                       "count_reply": (cnt or {}).get("count") if isinstance(cnt, dict) else None}}


def declared() -> dict:
    return {"frame": {"tag_ids": list(TAG_IDS), "window_market_end": list(E_WINDOW), "fetch": "every closed event of both tags (union by id; no date bound, so key-excluded events define the overlap drops)",
                      "classes": {"E-a": EA_Q_RE.pattern, "E-b": [EB_Q_RE.pattern, EB_T_RE.pattern], "E-c": EC_Q_RE.pattern}, "regional": REGIONAL_RE.pattern,
                      "parser": {"usgs": USGS_RE.pattern, "global": GLOBAL_RE.pattern, "window_et": WIN_ET_RE.pattern, "window_creation": WIN_CREATION_RE.pattern, "utc_day": UTC_DAY_RE.pattern,
                                 "count_buckets": [r.pattern for r, _ in BUCKET_RES], "mag_buckets": [r.pattern for r, _ in MAG_BUCKET_RES], "threshold_desc": THRESH_DESC_RE.pattern,
                                 "written_from": "out-of-window events only (endDate >= 2026-10-01), text read 2026-10-19; no price or outcome"},
                      "key_rule": "event id / member market id key drop, then every event whose window overlaps a key-excluded earthquake event (counted by source); > 30% dropped -> 'population thinned by exclusions'"},
            "catalogue": {"m6": {"chunks": [list(c) for c in CAT_M6_CHUNKS], "minmag": 6.0}, "m45": {"from": list(CAT_M45_FROM), "chunk_years": CAT_M45_CHUNK_YEARS, "count_first": True, "max_rows": USGS_MAX_ROWS},
                          "fields": CAT_COLUMNS, "eventtype": "earthquake", "magnitude": "E-a / E-b: served magnitude >= threshold; E-c: rounded to the nearest tenth (0.05 up), inclusive brackets"},
            "model": {"thresholds": list(THRESHOLDS), "fit": [FIT_START, FIT_END], "bin_days": MONTH_DAYS, "k": "method of moments; var <= mean -> Poisson", "horizon": "NegBin(mean lambda tau, size k tau / 30)",
                      "e_c": f"empirical share of days {ECDF_START}..{FIT_END} in the rule's own day (UTC or ET) whose rounded maximum is in the bucket; no M >= 4.5 -> lowest bucket"},
            "units": {"checkpoint": f"{CHECKPOINT_HOUR_UTC}:00Z daily", "start": CHECKPOINT_START, "listing_buffer_s": LIST_BUFFER_S, "end_buffer_s": END_BUFFER_S, "p_reg_lag_s": REG_LAG_S, "p_alt_lag_s": ALT_LAG_S,
                      "fidelity": FIDELITY, "price_rule": "stamp + 3,600 s < t, age <= 24 h", "catalogue_lag_s": CAT_LAG_S, "ambiguous_band": AMBIG_BAND, "weights": "each market weight 1"},
            "e1": {"floor": E1_FLOOR, "ways": ["event", "week", "component"], "placebo": f"sign flip per week / event / component, seed {PLACEBO_SEED}", "independent_price": "p_alt (t - 48 h): fails p and beta(q) - beta(p_alt) >= 0.25",
                   "robustness": "top-5 per way; class E-a and E-b+E-c signs; 30 days after M >= 7.5 excluded; halves; Gamma outcome sign and >= half; 7-day catalogue lag sign"},
            "gates": {"GE": GE_MIN, "parser_failure_max": PARSER_FAIL_MAX, "GEP": {"loadings": list(GEP_LOADINGS), "seed": SEED_GEP, "draws": c12.GMP_DRAWS, "mde_max": GEP_MDE_MAX}, "agreement_min": AGREE_MIN},
            "stage2": {"passes_utc": list(LIVE_PASSES_UTC), "pass_window_s": LIVE_PASS_WINDOW_S, "max_members": LIVE_MAX_MEMBERS, "book_gap_s": LIVE_BOOK_GAP_S,
                       "usgs": f"one read from the earliest open window start (cap {LIVE_USGS_SPAN_CAP_DAYS} d), M >= 4.5; stored: >= {LIVE_STORE_MIN_MAG} over the span + every event of the last {LIVE_STORE_RECENT_DAYS} d",
                       "start": "first earthquake market listed >= 1 day after the E freeze", "end": f"later of start + {E2_MIN_DAYS} d and 30 resolved components, never after start + {E2_MAX_DAYS} d",
                       "e1_rep": "p_t = first 16:00Z read mid, p_reg = first 10:00Z read mid of the same day, p_alt = 16:00Z read 48 h earlier; outcome from the first read >= 72 h after the window end",
                       "e2": {"edge": E2_EDGE, "fee": f"r a (1 - a), r = max(feeSchedule.rate, {E2_FEE_FLOOR})", "floor": E2_FLOOR, "robustness": E2_COST_ROBUST, "payoff": "Gamma resolution"},
                       "power": ">= 100 units and >= 30 window components, else not run (power), counted"},
            "smoke": {"version": SMOKE_FAMILY_VERSION, "needs": list(SMOKE_NEEDS), "out_of_window": SMOKE_OUT_OF_WINDOW},
            "label": LABEL_E, "stage1": "p < 0.01, floor, both binding placebos, robustness, early Holm at alpha / 10"}
