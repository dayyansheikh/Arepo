# ruff: noqa: E501
"""CB2-W: weather favourites (CH27). EXPLORATORY; nothing here is a calibration, edge or profitability claim.

Design: ``docs/research_lab/CREATIVE_BATCH_2.md`` (sections 0-2, CB2-W, 4.1, 4.2, 4.4, 5 and the challenger
round 1 response). Implementation notes (ambiguities resolved conservatively) are appended to that file.

Part 1 (this commit): constants and the weather declaration (TEMP_RE, city -> timezone table, bands, floors,
dates, split rule, small-G rule), the whole-event ``h6_weather`` Gamma walk with its frame rules, the
time-ordered SCREEN/HOLDOUT split, the resumable price/trade fetch (shared ``Limiter``, 429 policy,
collector-health stop, ``min(T_fetch6, T_seal)`` cap), and the ``weather-fetch`` / ``seal`` /
``verify-seal`` commands.

Part 2: units, tests, gates, small-G p-values, census, screen, replicate and stage P.

Command entry points (called lazily by ``scripts/run_cb2.py``); each takes an ``argparse.Namespace`` and
returns an int exit code: :func:`cmd_weather_fetch`, :func:`cmd_seal`, :func:`cmd_verify_seal`,
:func:`cmd_stagep`, :func:`cmd_census_w`, :func:`cmd_screen_w`, :func:`cmd_replicate_w`.

Shared code is imported, never copied: ``history_backfill`` (``Limiter``, transport, request clock, price
and trade fetch, as-of rule), ``cb1_structural`` (cost model, ``trade_before``, ``r_ann_of``, ``log_trials``,
``write_json``, ``fetch_outcomes``), ``cb1_history`` (declaration-spec commit check, census outcome guard)
and ``h5_seal`` (seal, verify, access log).
"""

from __future__ import annotations

import bisect
import gzip
import hashlib
import io
import json
import math
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import h5_seal, provenance
from . import history_backfill as hb

VERSION = "cb2-weather-v1"
LABEL = "EXPLORATORY CB2 weather favourites"
FAMILY = "creative_batch_2"
KIND_TEST = "cb2_test"
KIND_REP = "cb2_replication"
KIND_PROSP = "cb2_prospective"
KIND_DESC = "cb2_descriptive"
RUN_ID = "h6_weather"
REFUSED_RUN_IDS = ("h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders")
DAY = 86400.0
HOUR = 3600.0

# ---------------------------------------------------------------------------------------------
# Frozen text rules (hashed into the declaration; committed in seals/cb2_weather_text_rules.json)
# ---------------------------------------------------------------------------------------------

TEMP_RE = r"^(Highest|Lowest) temperature in (.+?) on (.+?)\?$"  # flags: none
TEMP_RE_FLAGS = 0

# Standard IANA zone by city slug (lowercase, spaces to hyphens). Extendable once, at the census, by city
# name only (CREATIVE_BATCH_2.md section 2.7); an extension changes TZ_TABLE_SHA256 and needs a new commit.
_TZ_BY_ZONE: dict[str, tuple[str, ...]] = {
    "America/New_York": ("atlanta", "miami", "nyc"),
    "America/Chicago": ("austin", "chicago", "dallas", "houston"),
    "America/Denver": ("denver",),
    "America/Los_Angeles": ("los-angeles", "san-francisco", "seattle"),
    "America/Toronto": ("toronto",),
    "America/Mexico_City": ("mexico-city",),
    "America/Panama": ("panama",),
    "America/Sao_Paulo": ("sao-paulo",),
    "America/Argentina/Buenos_Aires": ("buenos-aires",),
    "Europe/London": ("london",),
    "Europe/Amsterdam": ("amsterdam",),
    "Europe/Paris": ("paris",),
    "Europe/Madrid": ("madrid",),
    "Europe/Rome": ("milan",),
    "Europe/Berlin": ("munich",),
    "Europe/Warsaw": ("warsaw",),
    "Europe/Helsinki": ("helsinki",),
    "Europe/Istanbul": ("ankara", "istanbul"),
    "Europe/Moscow": ("moscow",),
    "Asia/Jerusalem": ("tel-aviv",),
    "Asia/Riyadh": ("jeddah",),
    "Asia/Karachi": ("karachi",),
    "Asia/Kolkata": ("lucknow",),
    "Asia/Shanghai": ("beijing", "chengdu", "chongqing", "guangzhou", "qingdao", "shanghai",
                      "shenzhen", "wuhan"),
    "Asia/Hong_Kong": ("hong-kong",),
    "Asia/Taipei": ("taipei",),
    "Asia/Seoul": ("busan", "seoul"),
    "Asia/Tokyo": ("tokyo",),
    "Asia/Manila": ("manila",),
    "Asia/Kuala_Lumpur": ("kuala-lumpur",),
    "Asia/Singapore": ("singapore",),
    "Africa/Johannesburg": ("cape-town",),
    "Pacific/Auckland": ("wellington",),
}
TZ_TABLE: dict[str, str] = dict(sorted((c, z) for z, cs in _TZ_BY_ZONE.items() for c in cs))


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


TEMP_RE_SHA256 = _sha({"pattern": TEMP_RE, "flags": TEMP_RE_FLAGS})
TZ_TABLE_SHA256 = _sha(TZ_TABLE)
TEXT_RULES_FILE = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb2_weather_text_rules.json"
SEALS_DIR = provenance.REPO_ROOT / "docs" / "research_lab" / "seals"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb2_v1.json"
OUT_ROOT = provenance.REPO_ROOT / "data-dumps" / "research_lab" / "creative_batch2"
HIST_ROOT = provenance.REPO_ROOT / "data-dumps" / "research_lab" / "history"
SNAPSHOT_ROOT = provenance.REPO_ROOT / "data-dumps" / "research_lab" / "snapshots"

# ---------------------------------------------------------------------------------------------
# Dates, bands, floors (declared)
# ---------------------------------------------------------------------------------------------


def _ep(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


T_SEAL = "2026-10-22T00:00:00Z"
T_SEAL_EPOCH = _ep(T_SEAL)  # == hb.T_SEAL_EPOCH
T_CENSUS_EX = ("2026-10-08T00:00:00Z", "2026-10-12T00:00:00Z")  # end_at in [a, b) excluded from h6
T2_REP_START_FLOOR = "2026-10-26T00:00:00Z"
T2_W_END_DAYS, T2_W_OUT_DAYS = 56, 7
T_FETCH_MARGIN_D = 3  # events must have end_at < T_fetch6 - 3d
END_FROM_DEFAULT = "2025-06-01T00:00:00Z"
SAMPLE_SEED = "arepo-h6-weather"
SAMPLE_N = 5000
MEMBER_RANGE = (4, 25)
BAND = (0.30, 0.95)  # p_fav(t) in [0.30, 0.95)
PRICE_WINDOW_H = (-72.0, 6.0)  # [end_at - 72h, end_at + 6h], fidelity 10
MAX_TRADES = 10000
TRADE_RANK = 2  # trades for the buckets ranked 1-2 at either origin
ORIGIN_H = {"W1": 24.0, "W2": 6.0, "W3": 24.0}
EXEC_LAG_H = 2.0
H_W_FLOOR = 0.02  # h_W(p) = max(h(p), 2.0c)
COST_SENS = 0.0075
WEATHER_FEE_RATE = 0.05
A_CAP = 0.999
SPLIT_HOLDOUT_FRAC = 0.40
SPLIT_EMBARGO_D = 2
ALPHA_STAGE1, ALPHA_STAGE2, ALPHA_STAGEP = 0.01, 0.05, 0.05
K_STAGE2_DECLARED = 5  # Stage-2 Holm family size upper bound (W2, W3, L1, X1, X2)
MIN_UNITS = 100
G_NORMAL, G_MIN = 30, 15  # small-G rule
N_BOOT, SEED = 2000, 216
N_WILD = 9999
PLACEBO_DRAWS, PLACEBO_MAX_ADVANCE_RATE = 200, 0.015
RANN_MIN = 0.10
FLOORS = {"W2": 0.010, "W3": 0.010}  # per share
MIN_REQ_429_WINDOW = 50  # 429 rate is evaluated only once the rolling window holds this many requests
FLOORS_NOTE = "floors are on the point estimate (dollars per share); never revised from the census"
LOCAL_CLASS_HOURS = {  # (end of pre-extreme, end of during) in local hours
    "Highest": (12.0, 16.0),
    "Lowest": (5.0, 9.0),
}
CREDIT_RULE = "pre-extreme subset estimate > 0 and >= 0.5 x full-sample estimate"
MAX_PAYOUT_ANOMALY = 0.02
MAX_CENSORED_STAGEP = 0.05

HYPOTHESES_CB2_W: dict[str, dict] = {
    "W1": {"kind": "descriptive", "counted": False, "origin_h": ORIGIN_H["W1"], "statistic":
           "mean(Y_fav - a - f(a)), cents/share", "floor": None, "gate": None,
           "trial_kind": KIND_DESC},
    "W2": {"kind": "economic", "counted": True, "origin_h": ORIGIN_H["W2"], "statistic":
           "mean(Y_fav - a - f(a)) with a = min(p_fav(t+2h) + h_W, 0.999)", "direction": 1,
           "floor": FLOORS["W2"], "rann_floor": RANN_MIN, "placebo": "breakeven Bern(min(a+f,1))",
           "trial_kind": KIND_TEST},
    "W3": {"kind": "mechanism", "counted": True, "origin_h": ORIGIN_H["W3"], "statistic":
           "mean(Y_fav - p_fav(t+2h))", "direction": 1, "floor": FLOORS["W3"], "rann_floor": None,
           "placebo": "Bern(p_fav(t+2h))", "trial_kind": KIND_TEST},
}


def declaration_weather() -> dict:
    """Every population, regex, band, floor, gate, date, the split rule, the small-G rule, the local-time
    classes and the city -> timezone table of CB2-W. Its sha256 (:func:`declaration_sha256_weather`) is what
    the committed ``model_specs/cb2_v1.json`` (key ``weather_declaration_sha256``) must equal."""
    return {
        "version": VERSION,
        "temp_re": {"pattern": TEMP_RE, "flags": TEMP_RE_FLAGS, "sha256": TEMP_RE_SHA256},
        "tz_table": {"table": TZ_TABLE, "sha256": TZ_TABLE_SHA256},
        "city_slug": "lowercase, spaces to hyphens",
        "population": {"neg_risk": True, "members": list(MEMBER_RANGE), "band": list(BAND),
                       "one_unit_per": "event and origin", "favourite": "highest as-of price, ties to "
                       "the lower market id; more than one bucket without a usable point excludes the "
                       "event", "trade_before_t": "known true if a stored trade is before t; "
                       "unavailable if truncated with oldest stored trade at or after t; false otherwise"},
        "dates": {"T_seal": T_SEAL, "census_ex": list(T_CENSUS_EX),
                  "t2_rep_start_floor": T2_REP_START_FLOOR, "T2_W_end_days": T2_W_END_DAYS,
                  "T2_W_out_days": T2_W_OUT_DAYS, "t_fetch_margin_d": T_FETCH_MARGIN_D,
                  "end_from": END_FROM_DEFAULT},
        "sample": {"seed": SAMPLE_SEED, "n": SAMPLE_N, "rank": "sha256(seed|event_id)"},
        "fetch": {"price_window_h": list(PRICE_WINDOW_H), "fidelity_min": hb.FIDELITY_MIN,
                  "max_trades": MAX_TRADES, "trades_for": f"buckets ranked 1-{TRADE_RANK} at either origin",
                  "cap": "every price and trade row at or after min(T_fetch6, T_seal) is dropped and counted",
                  "trade_order": "newest first (no deeper pagination exists)"},
        "frame_rules": ["end_at in [end_from, min(T_fetch6 - 3d, T_seal, end_before))", "census_ex",
                        "TEMP_RE title", "members 4-25 and neg-risk", "h1/h2/h3 sample ids",
                        "h5 seal-copy ids", "walk windows capped at 1 day dropped",
                        "closed=false events kept as censored"],
        "split": {"holdout_frac": SPLIT_HOLDOUT_FRAC, "embargo_days": SPLIT_EMBARGO_D,
                  "group_key": "UTC date of the earliest end_at among events of the same city and title "
                  "date", "d_split": "smallest UTC date d with |{k >= d}| <= 0.40 |S|",
                  "inputs": "end_at, city, title date only"},
        "tests": HYPOTHESES_CB2_W,
        "execution": {"lag_h": EXEC_LAG_H, "h_W_floor": H_W_FLOOR, "a_cap": A_CAP,
                      "fee_rate": WEATHER_FEE_RATE, "cost_sens": COST_SENS,
                      "no_usable_point": "no trade, net 0, kept in the denominator"},
        "local_class": {"hours": {k: list(v) for k, v in LOCAL_CLASS_HOURS.items()},
                        "rule": "class by local time at execution (t + 2h) on the title date; a later local "
                        "date is post-extreme", "credit_rule": CREDIT_RULE},
        "uncertainty": {"ways": ["end date (UTC day)", "city"], "p": "max over ways",
                        "bootstrap": "weekly block (end-date weeks)", "n_boot": N_BOOT, "seed": SEED,
                        "min_units": MIN_UNITS,
                        "small_g": {"normal_from": G_NORMAL, "cr2_t_from": G_MIN, "wild_draws": N_WILD,
                                    "wild": "Webb six-point, restricted", "below": "not testable (p=1)"}},
        "stages": {"alpha1": ALPHA_STAGE1, "alpha2": ALPHA_STAGE2, "alphaP": ALPHA_STAGEP,
                   "k_stage2": K_STAGE2_DECLARED, "rann_min": RANN_MIN,
                   "placebo": {"draws": PLACEBO_DRAWS, "max_advance": PLACEBO_MAX_ADVANCE_RATE},
                   "robustness": ["+0.75c keeps net > 0", "without top 5 clusters in each way",
                                  "cluster-equal-weighted sign agrees", "truncation/anomaly worst case > 0"]},
        "anomaly": {"max_share": MAX_PAYOUT_ANOMALY, "stagep_max_censored": MAX_CENSORED_STAGEP},
        "collector_health": {"max_age_h": 2.75, "429_rate": 0.01, "429_window_s": 600,
                             "429_chunk_limit": 50},
    }


def declaration_sha256_weather() -> str:
    return hashlib.sha256(json.dumps(declaration_weather(), sort_keys=True, default=str).encode()).hexdigest()


class Cb2Error(RuntimeError):
    """Base class for refusals."""


class Refused(Cb2Error):
    """A guard refused to run."""


def text_rules_doc() -> dict:
    return {"temp_re_sha256": TEMP_RE_SHA256, "tz_table_sha256": TZ_TABLE_SHA256}


def require_text_rules(path: Path = TEXT_RULES_FILE, *, require_committed: bool = True) -> None:
    """Refuse unless the committed text-rule file equals this code's TEMP_RE and timezone-table hashes. The
    rules are hashed before any h6 question text is read (CREATIVE_BATCH_2.md section 2.7)."""
    path = Path(path)
    if not path.exists():
        raise Refused(f"text-rule file {path} not found; refusing to read weather question text")
    if require_committed:
        from . import cb1_history

        if not cb1_history.spec_committed(path):
            raise Refused(f"text-rule file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"text-rule file {path} unreadable") from exc
    if doc != text_rules_doc():
        raise Refused(f"text-rule hash mismatch: file {doc} != code {text_rules_doc()}")


def require_declaration_weather(spec_path: Path = SPEC_PATH, *, require_committed: bool = True) -> str:
    """Refuse unless the committed CB2 freeze spec carries this code's weather declaration hash."""
    spec_path = Path(spec_path)
    if not spec_path.exists():
        raise Refused(f"declaration spec {spec_path} not found (CB2 freeze not committed)")
    if require_committed:
        from . import cb1_history

        if not cb1_history.spec_committed(spec_path):
            raise Refused(f"declaration spec {spec_path} is not committed (or differs from HEAD)")
    spec = json.loads(spec_path.read_text())
    want = declaration_sha256_weather()
    if spec.get("weather_declaration_sha256") != want:
        raise Refused("declaration hash mismatch: committed "
                      f"{spec.get('weather_declaration_sha256')} != code {want}")
    return want


def refuse_run_id(run_id: str) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is refused by CB2 (sealed or reserved: {REFUSED_RUN_IDS})")
    return run_id


# ---------------------------------------------------------------------------------------------
# Titles, cities, dates
# ---------------------------------------------------------------------------------------------

_TEMP = re.compile(TEMP_RE, TEMP_RE_FLAGS)


def city_slug(name: str) -> str:
    return re.sub(r"\s+", "-", name.strip().lower())


def parse_title(title: str | None) -> dict | None:
    """``{direction, city, title_date}`` for a temperature-event title, else None (snow, precipitation...)."""
    m = _TEMP.match(title or "")
    if not m:
        return None
    return {"direction": m.group(1), "city": city_slug(m.group(2)), "title_date": m.group(3).strip()}


def parse_title_date(text: str, end_epoch: float) -> str | None:
    """ISO local measurement date from the title date ("October 8", "October 8, 2026"). A missing year is
    taken from the candidate (end year - 1, end year, end year + 1) closest to the end date; None when
    unparseable."""
    t = re.sub(r"\s+", " ", text.strip().rstrip("."))
    end_d = datetime.fromtimestamp(end_epoch, UTC).date()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y"):
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            pass
    for fmt in ("%B %d", "%b %d"):
        try:
            md = datetime.strptime(t, fmt)
        except ValueError:
            continue
        best = None
        for y in (end_d.year - 1, end_d.year, end_d.year + 1):
            try:
                cand = date(y, md.month, md.day)
            except ValueError:
                continue
            if best is None or abs((cand - end_d).days) < abs((best - end_d).days):
                best = cand
        return best.isoformat() if best else None
    return None


def local_class(city: str, direction: str, title_date_iso: str | None, ts: float) -> str:
    """Local-time class of ``ts`` on the measurement date: ``pre`` / ``during`` / ``post`` (extreme), or
    ``tz_unknown`` (city not in the frozen table) / ``date_unknown`` (title date unparsed). Highest: pre
    before 12:00, during 12:00-16:00, post from 16:00; Lowest: 05:00 / 09:00. A time on a later local date
    is post-extreme; on an earlier local date it is pre-extreme."""
    zone = TZ_TABLE.get(city)
    if zone is None:
        return "tz_unknown"
    if not title_date_iso:
        return "date_unknown"
    loc = datetime.fromtimestamp(ts, UTC).astimezone(ZoneInfo(zone))
    d0 = date.fromisoformat(title_date_iso)
    if loc.date() > d0:
        return "post"
    if loc.date() < d0:
        return "pre"
    h = loc.hour + loc.minute / 60.0
    a, b = LOCAL_CLASS_HOURS[direction]
    return "pre" if h < a else ("during" if h < b else "post")


def parse_when(v: str) -> float:
    """UTC epoch from ``YYYY-MM-DD``, ``YYYY-MM-DDTHH:MMZ`` or ``YYYY-MM-DDTHH:MM:SSZ``."""
    v = str(v).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).replace(tzinfo=UTC).timestamp()
        except ValueError:
            pass
    raise ValueError(f"unparseable time {v!r}")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_end(v) -> float | None:
    if not v:
        return None
    try:
        s = str(v).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------------
# Time-ordered SCREEN / HOLDOUT split (section 1.3). Uses end_at, city and title date only.
# ---------------------------------------------------------------------------------------------


def group_keys(events: list[dict]) -> dict[str, date]:
    """event_id -> k(e): UTC date of the earliest ``end_at`` among the events of the same city and title date.
    The title date uses the parsed ISO date when available, otherwise its raw text and the end year."""
    first: dict[tuple, float] = {}
    keyof: dict[str, tuple] = {}
    for e in events:
        ep = float(e["end_epoch"])
        td = e.get("title_date_iso") or (e.get("title_date"), datetime.fromtimestamp(ep, UTC).year)
        k = (e["city"], td)
        keyof[str(e["event_id"])] = k
        first[k] = min(first.get(k, math.inf), ep)
    return {eid: datetime.fromtimestamp(first[k], UTC).date() for eid, k in keyof.items()}


def split_h6(events: list[dict]) -> dict:
    """The section 1.3 split. Returns ``d_split`` (ISO date), the id lists ``screen`` / ``holdout`` /
    ``embargo`` (sorted) and counts. Reads only ``event_id``, ``end_epoch``, ``city`` and the title date."""
    keys = group_keys(events)
    n = len(events)
    if n == 0:
        return {"d_split": None, "screen": [], "holdout": [], "embargo": [], "n": 0}
    ds = sorted(keys.values())
    lo, hi = ds[0], ds[-1] + timedelta(days=1)
    d_split, d = hi, lo
    while d <= hi:  # smallest calendar date with at most 40% of the sample at or after it
        if len(ds) - bisect.bisect_left(ds, d) <= SPLIT_HOLDOUT_FRAC * n + 1e-9:
            d_split = d
            break
        d += timedelta(days=1)
    emb_lo = d_split - timedelta(days=SPLIT_EMBARGO_D)
    screen, holdout, embargo = [], [], []
    for e in events:
        eid = str(e["event_id"])
        k = keys[eid]
        (holdout if k >= d_split else embargo if k >= emb_lo else screen).append(eid)
    return {"d_split": d_split.isoformat(), "screen": sorted(screen), "holdout": sorted(holdout),
            "embargo": sorted(embargo), "n": n}


def ids_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(str(i) for i in ids)).encode()).hexdigest()


def split_record(sp: dict, events_sha256: str | None = None) -> dict:
    """The record written into SEAL.json and the committed copy."""
    return {"rule": "time-ordered by end date (section 1.3); embargo dropped from both halves",
            "d_split": sp["d_split"], "embargo_days": SPLIT_EMBARGO_D,
            "holdout_frac_max": SPLIT_HOLDOUT_FRAC, "n_sample": sp["n"], "n_screen": len(sp["screen"]),
            "n_holdout": len(sp["holdout"]), "n_embargo": len(sp["embargo"]),
            "screen_ids_sha256": ids_sha256(sp["screen"]),
            "holdout_ids_sha256": ids_sha256(sp["holdout"]),
            "embargo_ids_sha256": ids_sha256(sp["embargo"]), "events_file_sha256": events_sha256,
            "inputs": "end_at, city, title date (events.jsonl.gz); the outcome file was not opened",
            "declaration_sha256_weather": declaration_sha256_weather()}


# ---------------------------------------------------------------------------------------------
# Gamma walk and frame rules (section 4.1)
# ---------------------------------------------------------------------------------------------

GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"


def walk_weather_events(lim, start: datetime, end: datetime, *, modes=(True, False), step_days: int = 7,
                        log: Callable[..., None] = lambda *_: None) -> tuple[dict[str, dict], dict]:
    """Walk Gamma ``/events?tag_slug=weather`` over ``end_date`` windows of ``step_days`` days, for each
    ``closed`` mode (true and false), splitting a window that reaches the offset cap (whole days) down to
    1 day. A window still capped at 1 day is dropped for that mode and counted. Returns
    ``({event_id: raw event with 'closed_mode'}, report)``. Raw events keep their market payload (outcome
    fields included); callers write those to the guarded file only."""
    events: dict[str, dict] = {}
    rep = {"requests": 0, "windows": 0, "split": 0, "windows_dropped_capped": 0,
           "rows_in_dropped_windows": 0, "dropped_capped_by_day": {}, "closed_false_events": 0,
           "closed_true_events": 0, "modes": [bool(m) for m in modes]}
    for mode in modes:
        stack = []
        t = start
        while t < end:
            stack.append((t, min(t + timedelta(days=step_days), end)))
            t += timedelta(days=step_days)
        while stack:
            a, b = stack.pop(0)
            rows, capped, off = [], False, 0
            while True:
                params = [("tag_slug", "weather"), ("closed", "true" if mode else "false"),
                          ("end_date_min", a.strftime("%Y-%m-%dT%H:%M:%SZ")),
                          ("end_date_max", b.strftime("%Y-%m-%dT%H:%M:%SZ")),
                          ("limit", 100), ("offset", off)]
                status, data = lim.get(GAMMA_EVENTS, params)
                rep["requests"] += 1
                if status != 200 or not isinstance(data, list):
                    break
                rows.extend(data)
                if len(data) < 100:
                    break
                off += 100
                if off >= hb.GAMMA_OFFSET_CAP:
                    capped = True
                    break
            if capped and (b - a) > timedelta(days=1):
                half = max(1, ((b - a).days) // 2)
                mid = a + timedelta(days=half)
                stack[:0] = [(a, mid), (mid, b)]
                rep["split"] += 1
                continue
            if capped:  # still capped at 1 day: the whole window is dropped and counted
                rep["windows_dropped_capped"] += 1
                rep["rows_in_dropped_windows"] += len(rows)
                day = a.strftime("%Y-%m-%d")
                rep["dropped_capped_by_day"][day] = rep["dropped_capped_by_day"].get(day, 0) + len(rows)
                continue
            rep["windows"] += 1
            for e in rows:
                eid = str(e.get("id"))
                if eid not in events:
                    events[eid] = {**e, "closed_mode": bool(mode)}
            log(f"  closed={mode} {a:%Y-%m-%d} .. {b:%Y-%m-%d}: {len(rows)} events")
    rep["closed_false_events"] = sum(1 for e in events.values() if not e["closed_mode"])
    rep["closed_true_events"] = len(events) - rep["closed_false_events"]
    return events, rep


def _json_list(v) -> list:
    if isinstance(v, list):
        return v
    try:
        out = json.loads(v) if isinstance(v, str) else []
        return out if isinstance(out, list) else []
    except ValueError:
        return []


def apply_frame_rules(raw: dict[str, dict], *, end_from: float, end_cap: float,
                      census_ex: tuple[float, float], history_ids: set[str], h5_ids: set[str]
                      ) -> tuple[list[dict], dict[str, list[dict]], dict]:
    """Frame exclusions, each counted (first rule that fires): ``no_end_date``, ``outside_end_window``
    (``end_at`` not in ``[end_from, end_cap)``), ``census_ex`` (``end_at`` in the drafting-census range),
    ``not_temperature_title`` (TEMP_RE), ``member_count`` (4-25), ``not_neg_risk``, ``history_sample_overlap``
    (any member in the h1/h2/h3 samples), ``h5_overlap`` (any member id in the h5 seal-copy file table).
    Returns (slim kept events sorted by id, {event_id: outcome records}, counts). Closed=false events are
    kept (censored). No outcome field is read by any rule."""
    counts = {"frame_in": len(raw), "no_end_date": 0, "outside_end_window": 0, "census_ex": 0,
              "not_temperature_title": 0, "member_count": 0, "not_neg_risk": 0,
              "history_sample_overlap": 0, "h5_overlap": 0, "kept": 0, "kept_closed_false": 0}
    kept: list[dict] = []
    outcomes: dict[str, list[dict]] = {}
    for eid in sorted(raw):
        e = raw[eid]
        end_ep = _parse_end(e.get("endDate"))
        if end_ep is None:
            counts["no_end_date"] += 1
            continue
        if not (end_from <= end_ep < end_cap):
            counts["outside_end_window"] += 1
            continue
        if census_ex[0] <= end_ep < census_ex[1]:
            counts["census_ex"] += 1
            continue
        parsed = parse_title(e.get("title"))
        if parsed is None:
            counts["not_temperature_title"] += 1
            continue
        ms = e.get("markets") or []
        if not (MEMBER_RANGE[0] <= len(ms) <= MEMBER_RANGE[1]):
            counts["member_count"] += 1
            continue
        if not (e.get("negRisk") or all(m.get("negRisk") for m in ms)):
            counts["not_neg_risk"] += 1
            continue
        mids = {str(m.get("id")) for m in ms}
        if mids & history_ids:
            counts["history_sample_overlap"] += 1
            continue
        if mids & h5_ids:
            counts["h5_overlap"] += 1
            continue
        markets = []
        for m in ms:
            toks = _json_list(m.get("clobTokenIds"))
            markets.append({"market_id": str(m.get("id")), "condition_id": m.get("conditionId"),
                            "token_yes": str(toks[0]) if toks else None,
                            "bucket": m.get("groupItemTitle")})
        kept.append({"event_id": str(eid), "title": e.get("title"), "direction": parsed["direction"],
                     "city": parsed["city"], "title_date": parsed["title_date"],
                     "title_date_iso": parse_title_date(parsed["title_date"], end_ep),
                     "end_at": _iso(end_ep), "end_epoch": end_ep, "n_members": len(ms),
                     "markets": markets})
        outcomes[str(eid)] = [{"market_id": str(m.get("id")), "event_id": str(eid),
                               "outcome_prices": m.get("outcomePrices"), "closed": m.get("closed"),
                               "closed_time": m.get("closedTime") or "",
                               "event_closed": e.get("closed")} for m in ms]
        counts["kept"] += 1
        counts["kept_closed_false"] += int(not e["closed_mode"])
    return kept, outcomes, counts


def draw_sample(events: list[dict], n: int, seed: str) -> list[dict]:
    """Seeded sample: rank by sha256(seed|event_id), first ``n``. Deterministic and order-independent."""
    ranked = sorted(events, key=lambda e: hashlib.sha256(f"{seed}|{e['event_id']}".encode()).hexdigest())
    return sorted(ranked[:n], key=lambda e: e["event_id"])


def seal_ids_from_copy(path: Path) -> set[str]:
    """Market ids from the file names (``prices/<id>.csv.gz`` / ``trades/<id>.csv.gz``) of a committed seal
    copy's file table. Ids only; nothing else of the sealed run is read."""
    doc = json.loads(Path(path).read_text())
    files = doc.get("files")
    if not isinstance(files, dict) or not files:
        raise Refused(f"{path}: no file table in the seal copy")
    ids = set()
    for rel in files:
        m = re.match(r"^(?:prices|trades)/([^/]+)\.csv\.gz$", rel)
        if m:
            ids.add(m.group(1))
    return ids


def history_sample_ids(root: Path, runs: list[str]) -> set[str]:
    """Market ids of the excluded history runs' samples (fail loudly if a sample is missing)."""
    out: set[str] = set()
    for r in runs:
        sp = Path(root) / r / "sample.csv.gz"
        if not sp.exists():
            raise FileNotFoundError(f"excluded run {r!r} has no {sp}")
        out |= set(pd.read_csv(sp, usecols=["market_id"], dtype=str).market_id)
    return out


# ---------------------------------------------------------------------------------------------
# Network policy: 429 back-off and collector health (section 2.8)
# ---------------------------------------------------------------------------------------------


class RatePolicy:
    """Transport wrapper. Counts requests and 429s in a rolling window; the first time more than ``max_rate`` of
    the requests in any rolling ``window_s`` are 429 (once the window holds ``min_requests``), halves the
    limiter's rate for the rest of the chunk; more than ``chunk_limit`` 429s in the chunk set ``over_limit``."""

    def __init__(self, transport, *, clock: Callable[[], float] = time.time, window_s: float = 600.0,
                 max_rate: float = 0.01, min_requests: int = MIN_REQ_429_WINDOW, chunk_limit: int = 50):
        self.transport, self.clock = transport, clock
        self.window_s, self.max_rate = window_s, max_rate
        self.min_requests, self.chunk_limit = min_requests, chunk_limit
        self.limiter = None
        self.recent: list[tuple[float, bool]] = []
        self.n429 = 0
        self.halved = False

    def __call__(self, url, params):
        status, body, headers = self.transport(url, params)
        now = self.clock()
        is429 = status == 429
        self.n429 += int(is429)
        self.recent.append((now, is429))
        cut = now - self.window_s
        while self.recent and self.recent[0][0] < cut:
            self.recent.pop(0)
        if (not self.halved and self.limiter is not None and len(self.recent) >= self.min_requests
                and sum(x for _, x in self.recent) / len(self.recent) > self.max_rate):
            self.limiter.min_gap *= 2.0
            self.halved = True
        return status, body, headers

    @property
    def over_limit(self) -> bool:
        return self.n429 > self.chunk_limit


def collector_healthy(snapshot_root: Path, now: float, *, lock_busy: Callable[[], bool] | None = None,
                      max_age_h: float = 2.75) -> tuple[bool, str]:
    """Read the newest capture manifest (metadata only). Unhealthy (transient pause) when the newest complete
    capture started more than ``max_age_h`` (2h45m) ago, or when the newest capture's manifest is
    incomplete while no pass holds the lock."""
    root = Path(snapshot_root)
    mans = []
    for m in sorted(root.glob("*/manifest.json")) if root.exists() else []:
        try:
            d = json.loads(m.read_text())
        except (OSError, ValueError):
            continue
        st = d.get("started_utc")
        if st:
            mans.append((str(st), d))
    if not mans:
        return False, f"no capture manifests under {root}"
    mans.sort(key=lambda x: x[0])
    newest = mans[-1][1]
    busy = (lock_busy or hb.live_pass_or_lock)()
    if str(newest.get("state")) != "complete" and not busy:
        return False, f"newest capture incomplete ({newest.get('state')}) and no pass holds the lock"
    complete = [st for st, d in mans if d.get("state") == "complete"]
    if not complete:
        return False, "no complete capture"
    started = _parse_end(complete[-1])
    if started is None:
        return False, f"unparseable capture start {complete[-1]!r}"
    age_h = (now - started) / HOUR
    if age_h > max_age_h:
        return False, f"newest complete capture started {age_h:.2f}h ago (> {max_age_h}h)"
    return True, "ok"


def dir_size(path: Path) -> int:
    total = 0
    stack = [Path(path)]
    while stack:
        p = stack.pop()
        try:
            with os.scandir(p) as it:
                for ent in it:
                    if ent.is_dir(follow_symlinks=False):
                        stack.append(Path(ent.path))
                    elif ent.is_file(follow_symlinks=False):
                        total += ent.stat(follow_symlinks=False).st_size
        except OSError:
            continue
    return total


# ---------------------------------------------------------------------------------------------
# Per-event fetch
# ---------------------------------------------------------------------------------------------


def _gz_jsonl_bytes(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in rows:
            gz.write((json.dumps(r, sort_keys=True) + "\n").encode())
    return buf.getvalue()


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _mid_key(market_id: str):
    return (0, int(market_id)) if str(market_id).isdigit() else (1, str(market_id))


def asof_price(ts: np.ndarray, vals: np.ndarray, t: float) -> float:
    """Price usable at ``t`` (stamp + 600 s < t, at most 2h old); NaN if none."""
    if len(ts) == 0:
        return math.nan
    v, _ = hb._asof(np.asarray(ts, float), np.asarray(vals, float), np.array([float(t)]), hb.MAX_QUOTE_AGE_S)
    return float(v[0])


def rank_buckets(series: dict[str, tuple[np.ndarray, np.ndarray]], t: float) -> list[tuple[str, float]]:
    """Buckets with a usable price at ``t``, highest price first, ties to the lower market id."""
    out = []
    for mid, (ts, vs) in series.items():
        p = asof_price(ts, vs, t)
        if not math.isnan(p):
            out.append((mid, p))
    out.sort(key=lambda x: (-x[1], _mid_key(x[0])))
    return out


def fetch_event(lim, ev: dict, key: bytes, rdir: Path, budget: hb.DiskBudget, *, cap_epoch: float,
                max_trades: int = MAX_TRADES) -> dict:
    """Prices for every bucket (``[end-72h, end+6h]``, fidelity 10), then trades for the buckets ranked 1-2 at
    either origin. Every price and trade row at or after ``cap_epoch`` is dropped and counted."""
    end = float(ev["end_epoch"])
    t0, t1 = int(end + PRICE_WINDOW_H[0] * HOUR), int(end + PRICE_WINDOW_H[1] * HOUR)
    rec: dict = {"event_id": ev["event_id"], "status": "done", "markets": {}}
    series: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for m in ev["markets"]:
        mid = m["market_id"]
        pts, _ = hb.fetch_prices(lim, m["token_yes"], t0, t1) if m.get("token_yes") else ([], 0)
        keep = [(t, p) for t, p in pts if t < cap_epoch]
        dropped = len(pts) - len(keep)
        budget.write(rdir / "prices" / f"{mid}.csv.gz",
                     hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in keep)))
        series[mid] = (np.array([t for t, _ in keep], float), np.array([p for _, p in keep], float))
        rec["markets"][mid] = {"price_points": len(keep), "dropped_price_rows_post_cap": dropped,
                               "trades": None}
    want: list[str] = []
    for h in (24.0, 6.0):
        for mid, _ in rank_buckets(series, end - h * HOUR)[:TRADE_RANK]:
            if mid not in want:
                want.append(mid)
    cond = {m["market_id"]: m.get("condition_id") for m in ev["markets"]}
    for mid in want:
        if not cond.get(mid):
            continue
        rows, st = hb.fetch_trades(lim, cond[mid], key, max_trades, ts_cap=cap_epoch - 1)
        budget.write(rdir / "trades" / f"{mid}.csv.gz", hb._gz_csv_bytes(hb.TRADE_COLUMNS, rows))
        rec["markets"][mid]["trades"] = {"n": st["n"], "truncated": bool(st["truncated"]),
                                         "oldest_ts": st["oldest_ts"],
                                         "dropped_post_cap": st["dropped_post_cap"]}
    return rec


# ---------------------------------------------------------------------------------------------
# The h6_weather fetch (resumable, budgeted)
# ---------------------------------------------------------------------------------------------

FETCH_VERSION = "h6-weather-fetch-v1"
COMPLETE_TOKEN = "weather_fetch_complete"
MAX_EVENT_ATTEMPTS = 3
OUTCOME_FILE = "outcomes_guarded.csv.gz"
OUTCOME_COLUMNS = ("outcome_prices", "closed", "closed_time", "event_closed", "final_yes", "uma_status")


def _gz_write_csv(budget: hb.DiskBudget, path: Path, header: list[str], rows: list[list]) -> None:
    budget.write(path, hb._gz_csv_bytes(header, rows))


def weather_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, n_events: int = SAMPLE_N,
    seed: str = SAMPLE_SEED, end_from: str = END_FROM_DEFAULT, end_before: str = T_SEAL,
    census_ex: tuple[str, str] = T_CENSUS_EX, exclude_runs: list[str] | None = None,
    h5_seal_copies: list[Path] | None = None, walk_closed: tuple[bool, ...] = (True, False),
    cap_at: str = T_SEAL, rps: float = 4.0, disk_cap: int = int(0.30 * 1024**3),
    budget_min: float | None = None, max_trades: int = MAX_TRADES, key: bytes | None = None,
    now: float | None = None, sleep: Callable[[float], None] = time.sleep,
    live_check: Callable[[], bool] | None = hb.live_pass_or_lock,
    should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time,
    t_seal_epoch: float = T_SEAL_EPOCH, snapshot_root: Path | None = None,
    health_every_s: float = 600.0, health_check: Callable[[float], tuple[bool, str]] | None = None,
    log: Callable[..., None] = lambda *_: None,
) -> dict:
    """Walk -> frame rules -> seeded sample (written once) -> per-event prices and top-2 trades.

    Refuses new chunks at or after ``t_seal_epoch``. Every price and trade row at or after
    ``min(T_fetch6, T_seal)`` is dropped and counted. Ends a chunk as transient ``paused_collector_health``
    when the live collector is unhealthy, and ``paused_429_chunk_limit`` after more than 50 HTTP 429s.
    Outcomes (Gamma ``outcomePrices``, closed flags) go only to ``outcomes_guarded.csv.gz``."""
    root = Path(root)
    refuse_run_id(run_id)
    if wall_clock() >= t_seal_epoch:
        return {"stopped": "t_seal_passed", "counts": {}, "requests": 0}
    rdir = root / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    now = time.time() if now is None else now
    now = hb.pin_request_clock(rdir, now)  # one T_fetch6 across resumed chunks
    cap_epoch = min(now, parse_when(cap_at), t_seal_epoch)
    end_cap = min(now - T_FETCH_MARGIN_D * DAY, parse_when(end_before), t_seal_epoch)
    t_start = time.time()
    rps = min(rps, 4.0)
    budget_s = None if not budget_min else budget_min * 60.0
    budget = hb.DiskBudget(rdir, disk_cap)
    pol = RatePolicy(transport, clock=wall_clock)
    lim = hb.Limiter(pol, rps=rps, sleep=sleep, live_check=live_check)
    pol.limiter = lim
    key = key if key is not None else hb.load_or_create_key()
    mpath = rdir / "manifest.json"
    prior = json.loads(mpath.read_text()) if mpath.exists() else {}
    state: dict = {"counts": {"events_done": 0, "events_failed": 0, "price_rows": 0,
                              "price_rows_dropped_post_cap": 0, "trade_rows": 0,
                              "trade_rows_dropped_post_cap": 0, "trades_truncated_buckets": 0}}
    last_health = [-1e18]

    def manifest(stopped: str | None, extra: dict | None = None) -> dict:
        m = {
            "provenance": hb.PROVENANCE, "evidence_role": hb.EVIDENCE_ROLE, "version": FETCH_VERSION,
            "run_id": run_id, "purpose": "CB2-W weather screen and holdout; never prospective",
            "git_commit": hb._git_commit(), "declaration_sha256_weather": declaration_sha256_weather(),
            "params": {"seed": seed, "n_events": n_events, "end_from": end_from, "end_before": end_before,
                       "end_cap_utc": _iso(end_cap), "cap_utc": _iso(cap_epoch), "census_ex": list(census_ex),
                       "exclude_runs": exclude_runs or [], "walk_closed": list(walk_closed),
                       "max_trades": max_trades, "max_rps": rps, "disk_cap_bytes": disk_cap,
                       "budget_min": budget_min},
            "started_utc": prior.get("started_utc", _iso(t_start)), "updated_utc": _iso(time.time()),
            "request_clock_now": prior.get("request_clock_now", _iso(now)),
            "requests": {"total_this_session": lim.requests, "retries": lim.retries,
                         "http_429": pol.n429, "yielded_to_live_s": lim.yielded_s,
                         "rps_halved": pol.halved},
            "stopped": stopped, "disk_bytes": budget.scan(),
            "elapsed_s_this_session": round(time.time() - t_start, 1), **state, **(extra or {}),
        }
        budget.cap += 10**7
        budget.write(mpath, json.dumps(m, indent=1, sort_keys=True, default=float).encode())
        return m

    def out_of_budget() -> bool:
        return budget_s is not None and time.time() - t_start >= budget_s

    def unhealthy() -> str | None:
        if health_check is None and snapshot_root is None:
            return None
        if wall_clock() - last_health[0] < health_every_s:
            return None
        last_health[0] = wall_clock()
        ok, why = health_check(wall_clock()) if health_check else collector_healthy(
            Path(snapshot_root), wall_clock())  # type: ignore[arg-type]
        return None if ok else f"paused_collector_health: {why}"

    why = unhealthy()
    if why:
        return manifest(why, {"transient": True})

    epath, opath = rdir / "events.jsonl.gz", rdir / OUTCOME_FILE
    frame_rep = prior.get("frame_report")
    if frame_rep is None and (rdir / "frame_report.json").exists():
        frame_rep = json.loads((rdir / "frame_report.json").read_text())
    try:
        if not epath.exists():
            hist = history_sample_ids(root, exclude_runs or [])
            h5 = set()
            for p in h5_seal_copies or []:
                h5 |= seal_ids_from_copy(Path(p))
            raw, walk_rep = walk_weather_events(
                lim, datetime.fromtimestamp(parse_when(end_from), UTC),
                datetime.fromtimestamp(end_cap, UTC), modes=walk_closed, log=log)
            kept, outs, fcounts = apply_frame_rules(
                raw, end_from=parse_when(end_from), end_cap=end_cap,
                census_ex=(parse_when(census_ex[0]), parse_when(census_ex[1])), history_ids=hist, h5_ids=h5)
            sample = draw_sample(kept, n_events, seed)
            frame_rep = {**walk_rep, **fcounts, "history_ids": len(hist), "h5_ids": len(h5),
                         "sample_n": len(sample), "sampled_closed_false": sum(
                             1 for e in sample if not raw[e["event_id"]]["closed_mode"])}
            rows = [[r["market_id"], r["event_id"], r["outcome_prices"], r["closed"],
                     r["closed_time"], r["event_closed"]]
                    for e in sample for r in outs[e["event_id"]]]
            # outcomes first, events last: the events file marks the frame as complete
            _gz_write_csv(budget, opath, ["market_id", "event_id", "outcome_prices", "closed",
                                          "closed_time", "event_closed"], rows)
            budget.write(epath, _gz_jsonl_bytes(sample))
            budget.write(rdir / "frame_report.json",
                         json.dumps(frame_rep, indent=1, sort_keys=True, default=float).encode())
    except OSError as exc:
        return {"stopped": f"disk_budget: {exc}"}
    events = load_jsonl_gz(epath)
    extra = {"frame_report": frame_rep, "n_events_sample": len(events)}
    if pol.over_limit:
        return manifest("paused_429_chunk_limit", {**extra, "transient": True})

    progress = rdir / "progress.jsonl"
    done: dict[str, dict] = {}
    if progress.exists():
        for line in progress.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                prev = done.get(rec["event_id"])
                if prev is not None and prev["status"] == "done":
                    continue
                rec["attempts"] = (prev or {}).get("attempts", 0) + (rec["status"] != "done")
                done[rec["event_id"]] = rec
    c = state["counts"]
    for rec in done.values():
        if rec["status"] == "done":
            c["events_done"] += 1
            for mm in rec["markets"].values():
                c["price_rows"] += mm["price_points"]
                c["price_rows_dropped_post_cap"] += mm["dropped_price_rows_post_cap"]
                if mm["trades"]:
                    c["trade_rows"] += mm["trades"]["n"]
                    c["trade_rows_dropped_post_cap"] += mm["trades"]["dropped_post_cap"] or 0
                    c["trades_truncated_buckets"] += int(mm["trades"]["truncated"])
    stopped = None
    since = 0
    for ev in events:
        eid = ev["event_id"]
        prev = done.get(eid)
        if prev and (prev["status"] == "done" or prev.get("attempts", 0) >= MAX_EVENT_ATTEMPTS):
            continue
        if should_stop is not None and should_stop():
            stopped = "should_stop"
            break
        if out_of_budget():
            stopped = "budget reached"
            break
        if wall_clock() >= t_seal_epoch:
            stopped = "t_seal_passed"
            break
        if pol.over_limit:
            stopped = "paused_429_chunk_limit"
            break
        why = unhealthy()
        if why:
            stopped = why
            break
        try:
            rec = fetch_event(lim, ev, key, rdir, budget, cap_epoch=cap_epoch, max_trades=max_trades)
            rec["fetched_utc"] = _iso(time.time())
            c["events_done"] += 1
            for mm in rec["markets"].values():
                c["price_rows"] += mm["price_points"]
                c["price_rows_dropped_post_cap"] += mm["dropped_price_rows_post_cap"]
                if mm["trades"]:
                    c["trade_rows"] += mm["trades"]["n"]
                    c["trade_rows_dropped_post_cap"] += mm["trades"]["dropped_post_cap"] or 0
                    c["trades_truncated_buckets"] += int(mm["trades"]["truncated"])
        except OSError as exc:
            stopped = f"disk_budget: {exc}"
            break
        except (RuntimeError, KeyError, TypeError, ValueError) as exc:
            rec = {"event_id": eid, "status": "failed", "error": str(exc)[:200],
                   "fetched_utc": _iso(time.time())}
        with progress.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        done[eid] = {**rec, "attempts": (prev or {}).get("attempts", 0) + (rec["status"] != "done")}
        since += 1
        if since >= 200:
            since = 0
            manifest("in_progress", extra)
    pending = [e for e in events if not (done.get(e["event_id"]) and (
        done[e["event_id"]]["status"] == "done" or done[e["event_id"]].get("attempts", 0) >= MAX_EVENT_ATTEMPTS))]
    c["events_failed"] = sum(1 for r in done.values() if r["status"] != "done")
    if stopped is None and not pending:
        extra["complete"] = True
        m = manifest(None, extra)
        m["token"] = COMPLETE_TOKEN
        return m
    return manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})


# ---------------------------------------------------------------------------------------------
# Sealed access: SCREEN / HOLDOUT views (reads are verified and logged; results go outside the run dir)
# ---------------------------------------------------------------------------------------------


def assert_outside_run_dir(out_path: Path, run_dir: Path) -> None:
    """A sealed run directory is never written to (``ACCESS_LOG.jsonl`` appends excepted)."""
    o, r = Path(out_path).resolve(), Path(run_dir).resolve()
    if o == r or r in o.parents:
        raise Refused(f"results path {out_path} is inside the sealed run directory {run_dir}; refused")


class HalfView:
    """One sealed half of ``h6_weather``. Reads of prices, trades and outcomes only for this half's events;
    an id of the other half or of the embargo is refused. Every read is appended to ``ACCESS_LOG.jsonl``."""

    def __init__(self, run_dir: Path, half: str, job: str, seal: dict, split: dict, events: list[dict],
                 decl_sha: str):
        self.run_dir, self.half, self.job, self.seal, self.decl_sha = Path(run_dir), half, job, seal, decl_sha
        self.split = split
        ids = set(split[half])
        self.events = [e for e in events if str(e["event_id"]) in ids]
        self.event_ids = sorted(ids)
        self.market_ids = {m["market_id"] for e in self.events for m in e["markets"]}
        self._outcomes = None

    def _log(self, files: list[str]) -> None:
        h5_seal.log_access(self.run_dir, f"{self.job}:{self.half}", files, declaration_sha=self.decl_sha)

    def check_ids(self, ids) -> None:
        bad = {str(i) for i in ids} - set(self.event_ids)
        if bad:
            raise Refused(f"{self.half} view refuses event ids outside the {self.half} block "
                          f"(holdout/embargo/unknown): {sorted(bad)[:3]}")

    def read_outcomes(self, event_ids=None) -> pd.DataFrame:
        """Outcome rows (guarded file) for this half's events, logged. Never reads other halves' rows."""
        ids = set(self.event_ids) if event_ids is None else {str(i) for i in event_ids}
        self.check_ids(ids)
        self._log([f"{OUTCOME_FILE}[{self.half}:{len(ids)} events]"])
        if self._outcomes is None:
            d = pd.read_csv(self.run_dir / OUTCOME_FILE, dtype=str, keep_default_na=False)
            self._outcomes = d[d["event_id"].isin(self.event_ids)]  # the other blocks are discarded at once
        return self._outcomes[self._outcomes["event_id"].isin(ids)].copy()

    def read_series(self) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], dict[str, dict | None]]:
        """({market_id: (t, p)}, {market_id: trade record or None}) for this half's markets."""
        self._log([f"prices/*[{self.half}]", f"trades/*[{self.half}]", "progress.jsonl"])
        series: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for mid in self.market_ids:
            f = self.run_dir / "prices" / f"{mid}.csv.gz"
            if f.exists():
                d = pd.read_csv(f)
                series[mid] = (d["t"].to_numpy(float), d["p"].to_numpy(float))
        trades: dict[str, dict | None] = {mid: None for mid in self.market_ids}
        prog = self.run_dir / "progress.jsonl"
        for line in prog.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("status") == "done" and rec["event_id"] in set(self.event_ids):
                for mid, mm in rec["markets"].items():
                    if mm.get("trades"):
                        f = self.run_dir / "trades" / f"{mid}.csv.gz"
                        ts = pd.read_csv(f, usecols=["ts"])["ts"].to_numpy(float) if f.exists() else np.array([])
                        trades[mid] = {**mm["trades"], "ts": ts}
        return series, trades


def open_half(run_dir: Path, half: str, job: str, seals_dir: Path | None = None) -> HalfView:
    """Verify the seal, the committed copy and the recorded split, then return the ``screen`` or ``holdout``
    view. The embargo is not selectable."""
    if half not in ("screen", "holdout"):
        raise Refused(f"half must be screen or holdout, not {half!r}")
    run_dir = Path(run_dir)
    seal = verify_h6(run_dir, seals_dir)
    events, _ = _events_for_split(run_dir)
    sp = split_h6(events)
    view = HalfView(run_dir, half, job, seal, sp, events, seal["declaration_sha256"])
    view._log([f"events.jsonl.gz[{half}]"])
    return view


# ---------------------------------------------------------------------------------------------
# Commands: weather-fetch, seal, verify-seal
# ---------------------------------------------------------------------------------------------


def _csv(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _print(obj) -> None:
    print(json.dumps(obj, sort_keys=True, default=float))


def cmd_weather_fetch(args) -> int:
    """``run_cb2.py weather-fetch``. Reads: ``run_id`` (h6_weather), ``seed``, ``n_events``, ``end_from``,
    ``end_before``, ``exclude_end`` ("a,b"), ``exclude_runs`` (csv), ``exclude_seal_ids`` (csv of committed
    seal copies), ``walk_closed`` ("true,false"), ``cap_at``, ``rps``, ``disk_cap_gb``, ``budget_min``,
    ``root``, ``data_dumps`` and ``data_dumps_cap_gb`` (10), ``snapshot_root``, ``text_rules_file``,
    ``max_trades``. Optional (tests): ``allow_uncommitted``, ``allow_nondeclared``, ``transport``, ``now``,
    ``wall_clock``, ``sleep``, ``live_check``, ``health_check``, ``key``.

    Refuses (exit 2) unless: the run id is allowed; the committed text-rule file matches TEMP_RE and the
    timezone table; every ``exclude_seal_ids`` seal copy exists (h5_cb1_SEAL.json is required); the declared
    seed, sample size, window start, census range and cap are unchanged; ``data-dumps`` is under the disk cap;
    and the wall clock is before ``T_seal``. Prints one JSON line (``weather_fetch_complete`` token when
    done); a budget or transient stop exits 0 and a re-run resumes."""
    committed = not getattr(args, "allow_uncommitted", False)
    try:
        rid = refuse_run_id(args.run_id)
        if rid != RUN_ID:
            raise Refused(f"weather-fetch writes only {RUN_ID!r}, not {rid!r}")
        tr_file = Path(getattr(args, "text_rules_file", None) or TEXT_RULES_FILE)
        require_text_rules(tr_file, require_committed=committed)
        seal_copies = [Path(p) for p in _csv(args.exclude_seal_ids)]
        if not any(Path(p).name == "h5_cb1_SEAL.json" for p in seal_copies):
            raise Refused("--exclude-seal-ids must include the committed h5_cb1_SEAL.json")
        for p in seal_copies:
            if not p.exists():
                raise Refused(f"committed seal copy {p} is missing; run q0018 and commit it first")
            if committed:
                from . import cb1_history

                if not cb1_history.spec_committed(p):
                    raise Refused(f"seal copy {p} is not committed (or differs from HEAD)")
        ex = _csv(args.exclude_end)
        if len(ex) != 2:
            raise Refused("--exclude-end needs 'start,end'")
        if not getattr(args, "allow_nondeclared", False):
            bad = []
            if args.seed != SAMPLE_SEED:
                bad.append("seed")
            if int(args.n_events) != SAMPLE_N:
                bad.append("n_events")
            if parse_when(args.end_from) != parse_when(END_FROM_DEFAULT):
                bad.append("end_from")
            if (parse_when(ex[0]), parse_when(ex[1])) != (parse_when(T_CENSUS_EX[0]), parse_when(T_CENSUS_EX[1])):
                bad.append("exclude_end")
            if parse_when(args.cap_at) != T_SEAL_EPOCH or parse_when(args.end_before) > T_SEAL_EPOCH:
                bad.append("cap_at/end_before")
            if bad:
                raise Refused(f"arguments differ from the declaration: {bad}")
        dd = Path(getattr(args, "data_dumps", None) or HIST_ROOT.parent.parent)
        cap_gb = float(getattr(args, "data_dumps_cap_gb", 10.0))
        used = dir_size(dd)
        if used > cap_gb * 1024**3:
            raise Refused(f"data-dumps is {used / 1024**3:.2f} GB (> {cap_gb} GB); refusing to start")
    except (Refused, FileNotFoundError) as exc:
        _print({"refused": str(exc)})
        return 2
    root = Path(getattr(args, "root", None) or HIST_ROOT)
    kw = {k: getattr(args, k) for k in ("now", "sleep", "wall_clock", "key") if getattr(args, k, None) is not None}
    if getattr(args, "live_check", None) is not None:
        kw["live_check"] = args.live_check
    if getattr(args, "health_check", None) is not None:
        kw["health_check"] = args.health_check
    transport = getattr(args, "transport", None) or hb.httpx_transport()
    m = weather_fetch(
        root, rid, transport, n_events=int(args.n_events), seed=args.seed, end_from=args.end_from,
        end_before=args.end_before, census_ex=(ex[0], ex[1]), exclude_runs=_csv(args.exclude_runs),
        h5_seal_copies=seal_copies, walk_closed=tuple(x.lower() == "true" for x in _csv(args.walk_closed)),
        cap_at=args.cap_at, rps=float(args.rps), disk_cap=int(float(args.disk_cap_gb) * 1024**3),
        budget_min=getattr(args, "budget_min", None), max_trades=int(getattr(args, "max_trades", MAX_TRADES)),
        snapshot_root=Path(getattr(args, "snapshot_root", None) or SNAPSHOT_ROOT), log=lambda *_: None, **kw)
    out = {k: m.get(k) for k in ("counts", "requests", "disk_bytes", "stopped", "complete", "transient",
                                 "n_events_sample", "elapsed_s_this_session")}
    out["frame_report"] = m.get("frame_report")
    if m.get("token"):
        out["status"] = m["token"]
    _print(out)
    return 0


def _events_for_split(rdir: Path) -> tuple[list[dict], str]:
    """events.jsonl.gz only (never the outcome file)."""
    p = Path(rdir) / "events.jsonl.gz"
    return load_jsonl_gz(p), h5_seal.sha256_file(p)


def cmd_seal(args) -> int:
    """``run_cb2.py seal``. Reads: ``run_id`` (h6_weather), ``root``, ``seals_dir`` (optional),
    ``trials_path`` (optional). Computes the time-ordered split from ``events.jsonl.gz`` alone (end_at, city,
    title date; the outcome file is not opened), records ``D_split`` and the SCREEN/HOLDOUT/embargo id-list
    hashes in ``SEAL.json`` (key ``split``), writes the committed copy
    ``docs/research_lab/seals/h6_weather_SEAL.json`` and appends one ``history_seal_declaration`` trial."""
    try:
        rid = h5_seal.check_run_id(refuse_run_id(args.run_id), h5_seal.H6_RUN_IDS)
        rdir = Path(getattr(args, "root", None) or HIST_ROOT) / rid
        events, esha = _events_for_split(rdir)
        sp = split_h6(events)
        rec = split_record(sp, esha)
        kw = {}
        if getattr(args, "trials_path", None):
            kw["trials_path"] = Path(args.trials_path)
        seal = h5_seal.seal_run(rdir, declaration_base=h5_seal.DECLARATION_H6, extra={"split": rec},
                                source="creative_batch_2:cb2_f_seal", **kw)
        copy = h5_seal.write_committed_copy(rdir, Path(args.seals_dir) if getattr(args, "seals_dir", None) else None)
    except (h5_seal.SealError, Cb2Error, FileNotFoundError) as exc:
        _print({"run_id": args.run_id, "error": str(exc)})
        return 1
    _print({"run_id": rid, "sealed": True, "committed_copy": str(copy), "d_split": rec["d_split"],
            "n_screen": rec["n_screen"], "n_holdout": rec["n_holdout"], "n_embargo": rec["n_embargo"],
            "listing_sha256": seal["listing_sha256"], "n_files": seal["n_files"]})
    return 0


def verify_h6(rdir: Path, seals_dir: Path | None = None) -> dict:
    """Seal verifies, the committed copy matches, and the recorded split recomputes from ``events.jsonl.gz``."""
    rdir = Path(rdir)
    copy = h5_seal.committed_seal_path(rdir.name, seals_dir)
    seal = h5_seal.require_sealed(rdir, copy)
    events, esha = _events_for_split(rdir)
    rec = split_record(split_h6(events), esha)
    got = seal.get("split") or {}
    for k in ("d_split", "screen_ids_sha256", "holdout_ids_sha256", "embargo_ids_sha256", "events_file_sha256"):
        if got.get(k) != rec[k]:
            raise h5_seal.SealError(f"{rdir.name}: recorded split differs from the recomputed split at {k}")
    return seal


def cmd_verify_seal(args) -> int:
    """``run_cb2.py verify-seal``. Reads: ``run_id`` (csv allowed), ``root``, ``seals_dir`` (optional)."""
    rc = 0
    for rid in _csv(args.run_id):
        try:
            rid = h5_seal.check_run_id(refuse_run_id(rid), h5_seal.H6_RUN_IDS)
            seal = verify_h6(Path(getattr(args, "root", None) or HIST_ROOT) / rid,
                             Path(args.seals_dir) if getattr(args, "seals_dir", None) else None)
            _print({"run_id": rid, "verified": True, "listing_sha256": seal["listing_sha256"],
                    "d_split": seal["split"]["d_split"]})
        except (h5_seal.SealError, Cb2Error, FileNotFoundError) as exc:
            _print({"run_id": rid, "error": str(exc)})
            rc = 1
    return rc
