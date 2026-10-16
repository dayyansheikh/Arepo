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
    the committed ``model_specs/cb2_v1.json`` (key ``weather_sha256``, written by ``run_cb2.py declare``)
    must equal."""
    return {
        "version": VERSION,
        "temp_re": {"pattern": TEMP_RE, "flags": TEMP_RE_FLAGS, "sha256": TEMP_RE_SHA256},
        "tz_table": {"table": TZ_TABLE, "sha256": TZ_TABLE_SHA256},
        "text_funcs_sha256": text_funcs_sha256(),
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


def text_funcs_sha256() -> str:
    """Hash of the SOURCE of the functions that turn question text into city / direction / date (freeze-check
    fix 11): changing how a title is parsed changes this hash and so the committed text rules."""
    import inspect

    src = "\n".join(inspect.getsource(f) for f in (city_slug, parse_title, parse_title_date))
    return hashlib.sha256(src.encode()).hexdigest()


def text_rules_doc() -> dict:
    return {"temp_re_sha256": TEMP_RE_SHA256, "tz_table_sha256": TZ_TABLE_SHA256,
            "text_funcs_sha256": text_funcs_sha256()}


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
    got = spec.get("weather_sha256") or spec.get("weather_declaration_sha256")
    if got != want:
        raise Refused(f"declaration hash mismatch: committed {got} != code {want}")
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
           "closed_true_events": 0, "windows_failed": 0, "failed_windows": [],
           "modes": [bool(m) for m in sorted(set(modes), key=bool)]}
    # closed=false is walked BEFORE closed=true: an event that closes between the two walks is then seen by
    # the second one (walking true first could miss it in both).
    for mode in sorted(set(modes), key=bool):
        stack = []
        t = start
        while t < end:
            stack.append((t, min(t + timedelta(days=step_days), end)))
            t += timedelta(days=step_days)
        while stack:
            a, b = stack.pop(0)
            rows, capped, off, failed = [], False, 0, False
            while True:
                params = [("tag_slug", "weather"), ("closed", "true" if mode else "false"),
                          ("end_date_min", a.strftime("%Y-%m-%dT%H:%M:%SZ")),
                          ("end_date_max", b.strftime("%Y-%m-%dT%H:%M:%SZ")),
                          ("limit", 100), ("offset", off)]
                status, data = lim.get(GAMMA_EVENTS, params)
                rep["requests"] += 1
                if status != 200 or not isinstance(data, list):
                    failed = True  # a failed page is NOT the end of the window
                    break
                rows.extend(data)
                if len(data) < 100:
                    break
                off += 100
                if off >= hb.GAMMA_OFFSET_CAP:
                    capped = True
                    break
            if failed:
                rep["windows_failed"] += 1
                rep["failed_windows"].append([bool(mode), a.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              b.strftime("%Y-%m-%dT%H:%M:%SZ")])
                continue
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


def rank_order(events: list[dict], seed: str) -> list[dict]:
    """Fetch order: ascending ``sha256(seed|event_id)``, the sampling rank. Independent of end date and of any
    outcome, so an incomplete fetch is a random subset in time, not the latest (HOLDOUT) block."""
    return sorted(events, key=lambda e: hashlib.sha256(f"{seed}|{e['event_id']}".encode()).hexdigest())


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
    if (root / run_id / h5_seal.SEAL_NAME).exists():  # a rerun would rewrite manifest.json and break the seal
        raise Refused(f"{run_id} is sealed; weather-fetch never touches a sealed run")
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
            if walk_rep["windows_failed"]:  # an incomplete frame is never written (and so never sampled)
                return manifest(f"walk_failed_windows: {walk_rep['windows_failed']}",
                                {"transient": True, "walk_report": walk_rep})
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
    for ev in rank_order(events, seed):  # seeded-rank order: a cut at T_seal leaves a random prefix
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
    if half == "holdout":  # one read: a crash after the first open must not allow a second look
        log = run_dir / h5_seal.ACCESS_LOG_NAME
        if log.exists() and any(":holdout" in json.loads(x).get("job", "")
                                for x in log.read_text().splitlines() if x.strip()):
            raise Refused("the HOLDOUT was already opened (ACCESS_LOG.jsonl); it is read once")
    u = load_universe(run_dir)
    events = u["events"]
    sp = split_h6(events)
    view = HalfView(run_dir, half, job, seal, sp, events, seal["declaration_sha256"])
    view.failed_ids = set(u["failed_ids"]) & set(view.event_ids)
    view._log([f"events.jsonl.gz[{half}]"])
    return view


# ---------------------------------------------------------------------------------------------
# Commands: weather-fetch, seal, verify-seal
# ---------------------------------------------------------------------------------------------


def _csv(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _print(obj) -> None:
    print(json.dumps(obj, sort_keys=True, default=float))


def cmd_weather_fetch(args, *, require_committed: bool = True, allow_nondeclared: bool = False) -> int:
    """``run_cb2.py weather-fetch``. Reads: ``run_id`` (h6_weather), ``seed``, ``n_events``, ``end_from``,
    ``end_before``, ``exclude_end`` ("a,b"), ``exclude_runs`` (csv), ``exclude_seal_ids`` (csv of committed
    seal copies), ``walk_closed`` ("true,false"), ``cap_at``, ``rps``, ``disk_cap_gb``, ``budget_min``,
    ``root``, ``data_dumps`` and ``data_dumps_cap_gb`` (10), ``snapshot_root``, ``text_rules_file``,
    ``max_trades``. Function parameters (tests only, not CLI flags): ``require_committed``,
    ``allow_nondeclared``. Optional namespace hooks (tests): ``transport``, ``now``,
    ``wall_clock``, ``sleep``, ``live_check``, ``health_check``, ``key``.

    Refuses (exit 2) unless: the run id is allowed; the committed text-rule file matches TEMP_RE and the
    timezone table; every ``exclude_seal_ids`` seal copy exists (h5_cb1_SEAL.json is required); the declared
    seed, sample size, window start, census range and cap are unchanged; ``data-dumps`` is under the disk cap;
    and the wall clock is before ``T_seal``. Prints one JSON line (``weather_fetch_complete`` token when
    done); a budget or transient stop exits 0 and a re-run resumes."""
    prep_args(args)
    committed = require_committed
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
        if not allow_nondeclared:
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


def load_universe(rdir: Path) -> dict:
    """The analysis universe of a finished (or T_seal-cut) fetch: the longest prefix, in seeded-rank order, of
    events with a terminal progress record (done, or failed 3 times). Events beyond the first unfinished one are
    outside the universe (the fetch is sequential in rank order, so this is a random subset of the sample,
    not a time block). Reads ``events.jsonl.gz``, ``progress.jsonl`` and ``manifest.json`` only."""
    rdir = Path(rdir)
    events = load_jsonl_gz(rdir / "events.jsonl.gz")
    man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
    seed = (man.get("params") or {}).get("seed", SAMPLE_SEED)
    term: dict[str, str] = {}
    fails: dict[str, int] = {}
    prog = rdir / "progress.jsonl"
    if prog.exists():
        for line in prog.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") == "done":
                term[r["event_id"]] = "done"
            else:
                fails[r["event_id"]] = fails.get(r["event_id"], 0) + 1
                if fails[r["event_id"]] >= MAX_EVENT_ATTEMPTS and term.get(r["event_id"]) != "done":
                    term[r["event_id"]] = "failed"
    prefix = []
    for e in rank_order(events, seed):
        if e["event_id"] not in term:
            break
        prefix.append(e)
    ids = {e["event_id"] for e in prefix}
    return {"events": sorted(prefix, key=lambda e: e["event_id"]), "n_total": len(events),
            "n_prefix": len(prefix), "complete": len(prefix) == len(events),
            "failed_ids": sorted(i for i in ids if term[i] == "failed"), "prefix_ids_sha256": ids_sha256(ids),
            "stopped": man.get("stopped"), "manifest_complete": man.get("complete"),
            "events_sha256": h5_seal.sha256_file(rdir / "events.jsonl.gz")}


def _events_for_split(rdir: Path) -> tuple[list[dict], str]:
    """The prefix universe's events (never the outcome file) and the events-file hash."""
    u = load_universe(rdir)
    return u["events"], u["events_sha256"]


def _prefix_record(u: dict) -> dict:
    return {"n_total_sample": u["n_total"], "n_universe": u["n_prefix"], "complete": u["complete"],
            "universe_ids_sha256": u["prefix_ids_sha256"], "n_fetch_failed": len(u["failed_ids"]),
            "rule": "seeded-rank prefix of terminal events; an incomplete fetch is sealed only when cut by "
            "T_seal"}


def cmd_seal(args) -> int:
    """``run_cb2.py seal``. Reads: ``run_id`` (h6_weather), ``root``, ``seals_dir`` (optional),
    ``trials_path`` (optional). Computes the time-ordered split from ``events.jsonl.gz`` alone (end_at, city,
    title date; the outcome file is not opened), records ``D_split`` and the SCREEN/HOLDOUT/embargo id-list
    hashes in ``SEAL.json`` (key ``split``), writes the committed copy
    ``docs/research_lab/seals/h6_weather_SEAL.json`` and appends one ``history_seal_declaration`` trial."""
    prep_args(args)
    try:
        rid = h5_seal.check_run_id(refuse_run_id(args.run_id), h5_seal.H6_RUN_IDS)
        rdir = Path(getattr(args, "root", None) or HIST_ROOT) / rid
        u = load_universe(rdir)
        incomplete_ok = (not u["complete"]) and str(u["stopped"] or "").startswith("t_seal_passed")
        if not u["complete"] and not incomplete_ok:
            raise h5_seal.SealError("refusing to seal an unfinished run that T_seal has not cut "
                                    f"({u['n_prefix']}/{u['n_total']} events done, stopped={u['stopped']!r})")
        sp = split_h6(u["events"])
        rec = {**split_record(sp, u["events_sha256"]), "universe": _prefix_record(u)}
        kw = {}
        if getattr(args, "trials_path", None):
            kw["trials_path"] = Path(args.trials_path)
        seal = h5_seal.seal_run(rdir, declaration_base=h5_seal.DECLARATION_H6, extra={"split": rec},
                                source="creative_batch_2:cb2_f_seal", allow_incomplete=incomplete_ok, **kw)
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
    u = load_universe(rdir)
    rec = {**split_record(split_h6(u["events"]), u["events_sha256"]), "universe": _prefix_record(u)}
    got = seal.get("split") or {}
    if (got.get("universe") or {}).get("universe_ids_sha256") != rec["universe"]["universe_ids_sha256"]:
        raise h5_seal.SealError(f"{rdir.name}: recorded universe differs from the recomputed prefix")
    for k in ("d_split", "screen_ids_sha256", "holdout_ids_sha256", "embargo_ids_sha256", "events_file_sha256"):
        if got.get(k) != rec[k]:
            raise h5_seal.SealError(f"{rdir.name}: recorded split differs from the recomputed split at {k}")
    return seal


def cmd_verify_seal(args) -> int:
    """``run_cb2.py verify-seal``. Reads: ``run_id`` (csv allowed), ``root``, ``seals_dir`` (optional)."""
    prep_args(args)
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


# =============================================================================================
# Part 2: units, statistics, gates, census / screen / replicate / stage P
# =============================================================================================

from scipy.stats import norm  # noqa: E402
from scipy.stats import t as t_dist  # noqa: E402

from . import battery as B  # noqa: E402
from . import cb1_structural as c1  # noqa: E402

# ---- costs ----------------------------------------------------------------------------------


def h_w(p: float) -> float:
    """Weather historical half-spread: the CB1 band table, floored at 2.0c."""
    return max(c1.half_spread(p), H_W_FLOOR)


def weather_ask(p_exec: float) -> tuple[float, float]:
    """(a, f(a)) for history: ``a = min(p_exec + h_W(p_exec), 0.999)``, weather fee rate 0.05."""
    a = min(p_exec + h_w(p_exec), A_CAP)
    return a, c1.leg_fee(a, WEATHER_FEE_RATE, 1.0)


def week_label(end_epoch: float) -> str:
    d = datetime.fromtimestamp(end_epoch, UTC).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def band_of(p: float) -> str:
    return "0.30-0.45" if p < 0.45 else ("0.45-0.60" if p < 0.60 else "0.60-0.95")


# ---- pre-outcome units (no outcome column is touched) ---------------------------------------


def build_units(events: list[dict], series: dict[str, tuple[np.ndarray, np.ndarray]],
                trades: dict[str, dict | None], origin_h: float,
                failed_ids: frozenset | set = frozenset()) -> pd.DataFrame:
    """One row per event at the origin ``t = end_at - origin_h``. The favourite is chosen from prices usable
    at ``t`` only (stamp + 600 s < t, at most 2h old; ties to the lower market id; more than one bucket
    without a usable point excludes the event). Execution uses the favourite's as-of price at ``t + 2h``.
    ``pre`` is the pre-outcome status: ``eligible`` / ``unavailable`` (truncated trades, oldest at or after
    t) / ``excl_multi_missing`` / ``excl_band`` / ``excl_no_trade``. No outcome field is read here."""
    rows = []
    for e in events:
        end = float(e["end_epoch"])
        t = end - origin_h * HOUR
        te = t + EXEC_LAG_H * HOUR
        mids = [m["market_id"] for m in e["markets"]]
        ser = {m: series[m] for m in mids if m in series}
        ranked = rank_buckets(ser, t)
        base = {"event_id": str(e["event_id"]), "city": e["city"], "direction": e["direction"],
                "title_date_iso": e.get("title_date_iso"), "end_epoch": end, "t": t, "origin_h": origin_h,
                "day": datetime.fromtimestamp(end, UTC).strftime("%Y-%m-%d"), "week": week_label(end),
                "n_members": len(mids), "n_missing": len(mids) - len(ranked), "fav_id": None,
                "p_fav_t": math.nan, "second_id": None, "p2_exec": math.nan, "p_exec": math.nan,
                "executed": False, "a": math.nan, "f": math.nan, "K": math.nan, "pre": "",
                "trade_cond": "", "band": "",
                "local_class": local_class(e["city"], e["direction"], e.get("title_date_iso"), te)}
        if str(e["event_id"]) in failed_ids:  # the fetch failed: not a genuine missing-price exclusion
            rows.append({**base, "pre": "excl_fetch_failed"})
            continue
        if len(mids) - len(ranked) > 1 or not ranked:
            rows.append({**base, "pre": "excl_multi_missing"})
            continue
        fav, p_fav = ranked[0]
        base.update(fav_id=fav, p_fav_t=p_fav, band=band_of(p_fav))
        if len(ranked) > 1:
            sec = ranked[1][0]
            base["second_id"] = sec
            base["p2_exec"] = asof_price(*ser[sec], te)
        if not (BAND[0] <= p_fav < BAND[1]):
            rows.append({**base, "pre": "excl_band"})
            continue
        tr = trades.get(fav)
        ts = None if tr is None else tr.get("ts")
        cond = c1.trade_before(ts, bool(tr and tr.get("truncated")), t) if tr is not None else None
        base["trade_cond"] = {True: "true", False: "false", None: "unavailable"}[cond]
        pe = asof_price(*ser[fav], te)
        if not math.isnan(pe):
            a, f = weather_ask(pe)
            base.update(p_exec=pe, executed=True, a=a, f=f, K=a + f)
        base["pre"] = {True: "eligible", False: "excl_no_trade", None: "unavailable"}[cond]
        rows.append(base)
    return pd.DataFrame(rows)


def parse_event_outcomes(df: pd.DataFrame) -> dict[str, dict]:
    """{event_id: {yes: {market_id: 0/1/other}, status resolved|anomalous|open, closed_time}} from the guarded
    outcome rows. ``resolved`` = every bucket closed with a payout in {0, 1} and exactly one winner."""
    out: dict[str, dict] = {}
    for eid, g in df.groupby("event_id"):
        yes, closed_all, cts = {}, True, []
        for r in g.itertuples():
            try:
                y = float(json.loads(r.outcome_prices)[0])
            except (ValueError, TypeError, IndexError):
                y = math.nan
            yes[str(r.market_id)] = y
            closed_all = closed_all and str(r.closed).lower() in ("true", "1", "1.0")
            ct = _parse_end(r.closed_time) if getattr(r, "closed_time", "") else None
            if ct is not None:
                cts.append(ct)
        vals = list(yes.values())
        if not closed_all:
            status = "open"
        elif all(v in (0.0, 1.0) for v in vals) and sum(vals) == 1.0:
            status = "resolved"
        else:
            status = "anomalous"
        out[str(eid)] = {"yes": yes, "status": status, "closed_time": max(cts) if cts else math.nan}
    return out


def attach_outcomes(units: pd.DataFrame, outs: dict[str, dict]) -> pd.DataFrame:
    """Add ``ostatus``, ``Y`` (favourite pays), ``Y2``, ``d`` (hold days), ``net`` and ``w3`` per unit."""
    u = units.copy()
    n = len(u)
    ostatus, Y, Y2, dd = [""] * n, np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    for i, r in enumerate(u.itertuples()):
        o = outs.get(r.event_id)
        if o is None:
            ostatus[i] = "no_outcome"
            continue
        ostatus[i] = o["status"]
        if o["status"] == "resolved" and r.fav_id is not None:
            Y[i] = o["yes"].get(r.fav_id, math.nan)
            if r.second_id is not None:
                Y2[i] = o["yes"].get(r.second_id, math.nan)
            if not math.isnan(o["closed_time"]):
                dd[i] = (o["closed_time"] - (r.t + EXEC_LAG_H * HOUR)) / DAY
    u["ostatus"], u["Y"], u["Y2"], u["d"] = ostatus, Y, Y2, dd
    ex = u["executed"].to_numpy(bool)
    u["net"] = np.where(ex, u["Y"] - u["K"], 0.0)
    u["w3"] = np.where(ex, u["Y"] - u["p_exec"], 0.0)
    return u


def primary_frame(u: pd.DataFrame) -> pd.DataFrame:
    return u[(u["pre"] == "eligible") & (u["ostatus"] == "resolved")].reset_index(drop=True)


def worst_case_extra(u: pd.DataFrame, col: str) -> np.ndarray:
    """Values added back as losers in the worst case: eligible units with an anomalous or unresolved event,
    and favourites whose trade condition is unavailable (truncated). An unexecuted unit contributes 0."""
    m = ((u["pre"] == "eligible") & (u["ostatus"].isin(["anomalous", "open", "no_outcome"]))) | (
        u["pre"] == "unavailable")
    x = u[m]
    ex = x["executed"].to_numpy(bool)
    loss = -x["K"].to_numpy(float) if col == "net" else -x["p_exec"].to_numpy(float)
    return np.where(ex, loss, 0.0)


# ---- cluster tests --------------------------------------------------------------------------

_WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])


def _cluster_sums(v: np.ndarray, cl: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    codes, uniq = pd.factorize(np.asarray(cl).astype(str))
    return (np.bincount(codes, weights=v, minlength=len(uniq)),
            np.bincount(codes, minlength=len(uniq)).astype(float))


def small_g_pvalue(v, cl, *, sign: int = 1, n_wild: int = N_WILD, seed: int = SEED,
                   alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0 (sign=1) under the declared small-G rule, for one cluster way:
    G >= 30 CR1 with the normal reference; 15 <= G < 30 CR2 (Bell-McCaffrey adjustment) with t(G - 1), and the
    larger of that p and the Webb six-point restricted wild-cluster bootstrap p (``n_wild`` draws); G < 15
    'not testable' (p = 1). ``alpha`` (placebo speed-up only) skips the wild bootstrap when the CR2 p already
    fails alpha, because the larger p would fail too."""
    v = np.asarray(v, float)
    n = len(v)
    S, C = _cluster_sums(v, cl)
    G = len(S)
    mu = float(v.mean()) if n else math.nan
    if G < G_MIN or n < 2:
        return {"G": int(G), "p": 1.0, "method": "not_testable", "testable": False, "mean": mu}
    sc = (v - mu) / n
    var1 = B._cr_var_of_sum(sc, np.asarray(cl).astype(str))
    se1 = math.sqrt(var1)
    z = mu / se1 if se1 > 0 else 0.0
    if G >= G_NORMAL:
        return {"G": int(G), "p": float(norm.sf(sign * z)), "method": "cr1_normal", "testable": True,
                "mean": mu, "z": z}
    s_g = S - mu * C  # cluster sums of centred values
    lev = 1.0 - C / n
    se2 = math.sqrt(float(((s_g**2) / np.maximum(lev, 1e-12)).sum())) / n
    t2 = mu / se2 if se2 > 0 else 0.0
    p_t = float(t_dist.sf(sign * t2, G - 1))
    out = {"G": int(G), "method": "cr2_t_and_wild", "testable": True, "mean": mu, "t_cr2": t2,
           "p_cr2_t": p_t}
    if alpha is not None and p_t >= alpha:
        out.update(p=p_t, p_wild=None)
        return out
    rng = np.random.default_rng(seed)
    W = _WEBB[rng.integers(0, 6, size=(n_wild, G))]
    m_star = (W @ S) / n
    s_star = W * S[None, :] - m_star[:, None] * C[None, :]
    se_star = np.sqrt((s_star**2 / np.maximum(lev, 1e-12)[None, :]).sum(1)) / n
    t_star = np.where(se_star > 0, m_star / np.where(se_star > 0, se_star, 1.0), 0.0)
    p_w = float((1 + np.sum(sign * t_star >= sign * t2)) / (n_wild + 1))
    out.update(p=max(p_t, p_w), p_wild=p_w)
    return out


def cluster_test_w(v, day, city, week, *, sign: int = 1, n_boot: int = N_BOOT, n_wild: int = N_WILD,
                   seed: int = SEED, alpha: float | None = None) -> dict:
    """W test statistic: mean(v) with p = max(day-clustered, city-clustered) under the small-G rule, and a
    weekly block bootstrap 95% CI (resampling whole end-date weeks)."""
    v = np.asarray(v, float)
    n = len(v)
    if n < 2:
        return {"testable": False, "p": 1.0, "n": int(n), "mean": float(v.mean()) if n else math.nan}
    pd_ = small_g_pvalue(v, day, sign=sign, n_wild=n_wild, seed=seed, alpha=alpha)
    pc = small_g_pvalue(v, city, sign=sign, n_wild=n_wild, seed=seed, alpha=alpha)
    out = {"n": int(n), "mean": float(v.mean()), "G_day": pd_["G"], "G_city": pc["G"],
           "p_day": pd_["p"], "p_city": pc["p"], "method_day": pd_["method"], "method_city": pc["method"],
           "testable": bool(pd_["testable"] and pc["testable"] and n >= MIN_UNITS),
           "p": 1.0 if not (pd_["testable"] and pc["testable"] and n >= MIN_UNITS)
           else max(pd_["p"], pc["p"]), "detail_day": pd_, "detail_city": pc}
    if n_boot:
        S, C = _cluster_sums(v, week)
        g = len(S)
        rng = np.random.default_rng(seed)
        bs = np.empty(n_boot)
        for i in range(n_boot):
            m = np.bincount(rng.integers(0, g, g), minlength=g)
            bs[i] = (m @ S) / max(m @ C, 1e-12)
        out["ci95_week_boot"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
        out["n_week"] = int(g)
    return out


def _drop_top(v: np.ndarray, cl: np.ndarray, k: int = 5) -> np.ndarray:
    s = pd.Series(v).groupby(np.asarray(cl).astype(str)).sum()
    drop = set(s.abs().sort_values(ascending=False).index[:k])
    return ~np.isin(np.asarray(cl).astype(str), list(drop))


def city_equal_mean(v, city) -> float:
    return float(pd.Series(np.asarray(v, float)).groupby(np.asarray(city).astype(str)).mean().mean())


def w_gate(u: pd.DataFrame, spec: dict, wc: np.ndarray, *, alpha: float, n_boot: int, n_wild: int,
           seed: int = SEED, col: str, short: bool = False) -> dict:
    """Stage gate for one W test on its primary frame ``u`` (columns ``col``, day, city, week, K, d,
    executed). Conditions: testable (>= 100 units, G >= 15 in both ways), p < alpha, point >= floor, R_ann
    >= 10% (economic), and the binding robustness: (i) +0.75c on every bought leg keeps the mean > 0
    (economic), (ii) p and floor hold without the top 5 days and without the top 5 cities, (iii) the
    city-equal-weighted mean has the same sign, (iv) the truncation/anomaly worst case keeps the mean > 0.
    ``short`` stops at the first failed condition (placebo draws)."""
    v = u[col].to_numpy(float)
    day, city, week = u["day"].to_numpy(), u["city"].to_numpy(), u["week"].to_numpy()
    ct = cluster_test_w(v, day, city, week, n_boot=0 if short else n_boot, n_wild=n_wild, seed=seed,
                        alpha=alpha if short else None)
    out = {k: ct.get(k) for k in ("n", "mean", "p", "p_day", "p_city", "G_day", "G_city", "method_day",
                                  "method_city", "testable", "ci95_week_boot", "n_week")}
    out.update(alpha=alpha, floor=spec["floor"])
    fail: list[str] = []
    if not ct["testable"]:
        out.update(advance_core=False, fail=["not_testable"])
        return out
    if not ct["p"] < alpha:
        fail.append("p")
    if not ct["mean"] >= spec["floor"]:
        fail.append("floor")
    if short and fail:
        return {**out, "advance_core": False, "fail": fail}
    ex = u["executed"].to_numpy(bool)
    if spec["rann_floor"] is not None:
        ra = c1.r_ann_of(v[ex], u["K"].to_numpy(float)[ex], u["d"].to_numpy(float)[ex]) if ex.any() \
            else math.nan
        out["r_ann"] = ra
        if not (not math.isnan(ra) and ra >= spec["rann_floor"]):
            fail.append("r_ann")
    rob: dict = {}
    if spec["kind"] == "economic":
        rob["cost_0.75c_positive"] = bool((v - COST_SENS * ex).mean() > 0)
        if not rob["cost_0.75c_positive"]:
            fail.append("cost_0.75c")
    if not (short and fail):
        for way, cl in (("day", day), ("city", city)):
            keep = _drop_top(v, cl)
            t5 = cluster_test_w(v[keep], day[keep], city[keep], week[keep], n_boot=0, n_wild=n_wild,
                                seed=seed, alpha=alpha if short else None) if keep.sum() >= 2 else {
                "p": 1.0, "mean": math.nan, "testable": False}
            ok = bool(t5["testable"] and t5["p"] < alpha and t5["mean"] >= spec["floor"])
            rob[f"without_top5_{way}s"] = {"p": t5["p"], "mean": t5["mean"], "ok": ok}
            if not ok:
                fail.append(f"without_top5_{way}s")
        eq = city_equal_mean(v, city)
        rob["city_equal_mean"] = eq
        rob["city_equal_sign_agrees"] = bool(np.sign(eq) == np.sign(ct["mean"]) and eq != 0)
        if not rob["city_equal_sign_agrees"]:
            fail.append("city_equal_sign")
        allv = np.concatenate([v, wc]) if len(wc) else v
        rob["worst_case_mean"] = float(allv.mean())
        rob["worst_case_n_added"] = int(len(wc))
        if not rob["worst_case_mean"] > 0:
            fail.append("worst_case")
    out.update(robustness=rob, fail=fail, advance_core=not fail)
    return out


def breakeven_placebo_w(u: pd.DataFrame, spec: dict, wc: np.ndarray, *, alpha: float, test: str,
                        draws: int = PLACEBO_DRAWS, seed: int = SEED + 2, n_wild: int = N_WILD) -> dict:
    """W2: ``Y ~ Bern(min(a + f, 1))`` on executed units (expected net exactly 0); W3: ``Y ~ Bern(p_fav(t+2h))``.
    The full gate (cluster p-values under the small-G rule, floor, R_ann, robustness) is rerun on each draw; the
    advance rate must be <= 1.5%. (CI bootstrap is not part of the gate and is skipped.)"""
    if len(u) == 0:
        return {"draws": 0, "n_advance": 0, "advance_rate": None, "calibrated": True, "note": "empty"}
    rng = np.random.default_rng(seed)
    ex = u["executed"].to_numpy(bool)
    pb = np.minimum(u["K"].to_numpy(float), 1.0) if test == "W2" else u["p_exec"].to_numpy(float)
    pb = np.where(ex, pb, 0.0)
    adv = 0
    for _ in range(draws):
        y = (rng.random(len(u)) < pb).astype(float)
        d = u.copy()
        d["Y"] = y
        d["net"] = np.where(ex, y - d["K"], 0.0)
        d["w3"] = np.where(ex, y - d["p_exec"], 0.0)
        r = w_gate(d, spec, wc, alpha=alpha, n_boot=0, n_wild=n_wild, seed=int(rng.integers(1, 10**6)),
                   col="net" if test == "W2" else "w3", short=True)
        adv += int(r["advance_core"])
    rate = adv / draws
    return {"draws": draws, "n_advance": adv, "advance_rate": rate, "max_rate": PLACEBO_MAX_ADVANCE_RATE,
            "calibrated": bool(rate <= PLACEBO_MAX_ADVANCE_RATE)}


def class_breakdown(u: pd.DataFrame, col: str) -> dict:
    out = {}
    for cls, g in u.groupby("local_class"):
        out[str(cls)] = {"n": int(len(g)), "mean": float(g[col].mean()) if len(g) else None}
    return out


def credit_rule(u: pd.DataFrame, col: str, full_mean: float) -> dict:
    """CH27 may be credited only if the pre-extreme subset estimate is positive and at least half the
    full-sample estimate; otherwise a pass is 'decided-but-unresolved carry (resolution lag), not CH27'."""
    pre = u[u["local_class"] == "pre"]
    m = float(pre[col].mean()) if len(pre) else math.nan
    ok = bool(len(pre) and m > 0 and m >= 0.5 * full_mean)
    return {"rule": CREDIT_RULE, "pre_n": int(len(pre)), "pre_mean": None if math.isnan(m) else m,
            "full_mean": full_mean, "credits_ch27": ok,
            "label_if_pass": "CH27 weather-favourite carry" if ok else
            "decided-but-unresolved carry (resolution lag), not CH27"}


def by_label(ps: dict[str, float], m_total: int) -> dict:
    """Benjamini-Yekutieli label at q = 0.10 over the cumulative count (triage only)."""
    try:
        return B.benjamini_yekutieli(ps, int(m_total))
    except Exception as exc:  # noqa: BLE001 - label only
        return {"error": f"{type(exc).__name__}: {exc}"}


def descriptives(u24: pd.DataFrame, u6: pd.DataFrame) -> dict:
    """Reported-only comparators (kind cb2_descriptive, not counted)."""
    out: dict = {}
    for name, u in (("W1", u24), ("origin6", u6)):
        if not len(u):
            continue
        p = primary_frame(u) if "ostatus" in u else u
        ex = p[p["executed"]]
        d: dict = {"n_units": int(len(p)), "n_executed": int(len(ex)),
                   "execution_rate": float(len(ex) / len(p)) if len(p) else None}
        if "net" in p:
            d["mean_net"] = float(p["net"].mean()) if len(p) else None
            d["mean_w3"] = float(p["w3"].mean()) if len(p) else None
            d["by_direction"] = {k: float(g["net"].mean()) for k, g in p.groupby("direction")}
            d["by_band"] = {k: float(g["net"].mean()) for k, g in p.groupby("band")}
            sec = p[p["Y2"].notna() & p["p2_exec"].notna()]
            d["second_ranked_excess"] = float((sec["Y2"] - sec["p2_exec"]).mean()) if len(sec) else None
            d["second_ranked_n"] = int(len(sec))
        out[name] = d
    return out


def payout_report(all_units: pd.DataFrame, outs: dict[str, dict]) -> dict:
    ev = list(outs.values())
    n = len(ev)
    an = sum(1 for o in ev if o["status"] == "anomalous")
    op = sum(1 for o in ev if o["status"] == "open")
    share = (an + op) / n if n else 0.0
    return {"n_events": n, "anomalous": an, "open_at_fetch": op, "share": share,
            "payout_anomaly_sensitive": bool(share > MAX_PAYOUT_ANOMALY)}


def truncation_report(u: pd.DataFrame) -> dict:
    un = u[u["pre"] == "unavailable"]
    by = {"Y1": int((un["Y"] == 1.0).sum()), "Y0": int((un["Y"] == 0.0).sum()),
          "Y_unknown": int(un["Y"].isna().sum())}
    return {"unavailable": int(len(un)), "by_Y": by}


# ---- the whole W family on one set of frames --------------------------------------------------


def run_w_family(u24: pd.DataFrame, u6: pd.DataFrame, outs: dict[str, dict], *, tests=("W2", "W3"),
                 alpha: dict[str, float] | float = ALPHA_STAGE1, n_boot: int = N_BOOT,
                 n_wild: int = N_WILD, placebo_draws: int = PLACEBO_DRAWS, seed: int = SEED) -> dict:
    """W2 (origin 6h, column ``net``) and W3 (origin 24h, column ``w3``) with gates and placebos; W1 and the
    comparators are descriptive only. ``u24`` / ``u6`` carry outcomes (:func:`attach_outcomes`)."""
    res: dict = {"tests": {}, "placebo": {}, "credit": {}, "classes": {}}
    for tid in tests:
        spec = HYPOTHESES_CB2_W[tid]
        u = u6 if tid == "W2" else u24
        col = "net" if tid == "W2" else "w3"
        p = primary_frame(u)
        wc = worst_case_extra(u, col)
        a = alpha[tid] if isinstance(alpha, dict) else alpha
        g = w_gate(p, spec, wc, alpha=a, n_boot=n_boot, n_wild=n_wild, seed=seed, col=col)
        pl = breakeven_placebo_w(p, spec, wc, alpha=a, test=tid, draws=placebo_draws, n_wild=n_wild) \
            if g.get("testable") else {"draws": 0, "advance_rate": None, "calibrated": False,
                                       "note": "not testable"}
        res["placebo"][tid] = pl
        res["tests"][tid] = {**g, "advance": bool(g["advance_core"] and pl["calibrated"]), "test_id": tid,
                             "kind": spec["kind"], "origin_h": spec["origin_h"],
                             "units_total": int(len(u)),
                             "r_ann": g.get("r_ann")}
        res["credit"][tid] = credit_rule(p, col, float(g["mean"])) if g.get("mean") is not None and len(p) \
            else None
        res["classes"][tid] = class_breakdown(p, col)
    res["descriptive"] = descriptives(u24, u6)
    res["truncation"] = {"W2": truncation_report(u6), "W3": truncation_report(u24)}
    res["payout"] = payout_report(pd.concat([u24, u6]), outs)
    res["pre_status_counts"] = {"origin24": u24["pre"].value_counts().to_dict(),
                                "origin6": u6["pre"].value_counts().to_dict()}
    return res


# ---- result files and trial lines -------------------------------------------------------------


def _clean_json(o):
    return B._clean(o) if hasattr(B, "_clean") else o


def write_results(path: Path, doc: dict) -> str:
    """Never overwrites; refuses a path inside a sealed run directory is the caller's check."""
    return c1.write_json(path, doc)


def log_trials_w(tests: dict, *, kind: str, role: str, dataset: str, family: str, results_path: str,
                 results_sha256: str, run_id: str, decl_sha: str, placebo: dict | None = None,
                 descriptive: dict | None = None, prov: dict | None = None,
                 path: Path = provenance.TRIALS_PATH) -> list[dict]:
    """One line per counted test (``kind``), one ``cb2_descriptive`` line per descriptive (W1; count 0), one
    placebo line per placebo (count 0) and one ``ml_explain`` count line (source ``creative_batch_2:<family>``)."""
    prov = prov if prov is not None else provenance.run_provenance()
    out = []
    for name, t in tests.items():
        out.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": name, "run_id": run_id, "label": LABEL,
            "kind": kind, "evidence_role": role, "revision": VERSION, "result_path": results_path,
            "results_sha256": results_sha256, "declaration_sha256": decl_sha,
            "summary": {k: t.get(k) for k in ("mean", "p", "n", "r_ann", "advance", "replicated", "testable",
                                              "G_day", "G_city")}, "provenance": prov}, path))
    for name, d in (descriptive or {}).items():
        out.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": name, "run_id": run_id, "label": LABEL,
            "kind": KIND_DESC, "evidence_role": role, "revision": VERSION, "result_path": results_path,
            "results_sha256": results_sha256, "declaration_sha256": decl_sha, "n_tests": 0,
            "summary": d, "provenance": prov}, path))
    for name, pl in (placebo or {}).items():
        out.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": f"{name}:placebo", "run_id": run_id, "label": LABEL,
            "kind": kind, "evidence_role": "placebo", "revision": VERSION, "result_path": results_path,
            "results_sha256": results_sha256, "declaration_sha256": decl_sha,
            "summary": {k: pl.get(k) for k in ("draws", "n_advance", "advance_rate", "calibrated")},
            "provenance": prov}, path))
    out.append(provenance.append_trial({
        "dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY",
        "n_tests": len(tests), "revision": VERSION, "run_id": run_id, "source": f"creative_batch_2:{family}",
        "results_sha256": results_sha256,
        "note": "CB2-W count line; per-test cb2_* lines are EXCLUDEd in battery2.KIND_RULES"}, path))
    return out


# ---- argument handling for the lazily called commands -----------------------------------------


def _weather_parser():
    import argparse

    ap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    for name, typ, default in (
            ("--seed", str, SAMPLE_SEED), ("--n-events", int, SAMPLE_N), ("--end-from", str, "2025-06-01"),
            ("--end-before", str, T_SEAL), ("--exclude-end", str, ",".join(T_CENSUS_EX)),
            ("--exclude-runs", str, ""), ("--exclude-seal-ids", str, ""), ("--walk-closed", str, "true,false"),
            ("--cap-at", str, T_SEAL), ("--disk-cap-gb", float, 0.30), ("--budget-min", float, None),
            ("--root", str, None), ("--seals-dir", str, None), ("--out-root", str, None),
            ("--n-wild", int, N_WILD), ("--placebo-draws", int, PLACEBO_DRAWS), ("--spec-path", str, None),
            ("--trials-path", str, None), ("--max-trades", int, MAX_TRADES), ("--data-dumps", str, None),
            ("--data-dumps-cap-gb", float, 10.0), ("--text-rules-file", str, None),
            ("--screen-results", str, None), ("--holdout-results", str, None)):
        ap.add_argument(name, type=typ, default=default)
    # No bypass flags exist on the command line: commit checks, the T2_W_out gate and the pinned rep
    # start can only be overridden by the keyword parameters of the functions below (tests).
    return ap


def prep_args(args):
    """Fill attributes the runner did not parse (``args.extra`` holds the weather-only flags) with the
    declared defaults. Attributes already set (tests, the runner's own flags) are never overwritten."""
    extra = list(getattr(args, "extra", None) or [])
    ns, _ = _weather_parser().parse_known_args(extra)
    for k, v in vars(ns).items():
        if getattr(args, k, None) is None:
            setattr(args, k, v)
    if getattr(args, "run_id", None) is None:
        args.run_id = RUN_ID
    if getattr(args, "n_boot", None) is None:
        args.n_boot = N_BOOT
    return args


def _paths(args):
    root = Path(args.root) if getattr(args, "root", None) else HIST_ROOT
    seals = Path(args.seals_dir) if getattr(args, "seals_dir", None) else None
    out = Path(args.out_root) if getattr(args, "out_root", None) else OUT_ROOT
    return root, seals, out


def _trials_kw(args) -> dict:
    return {"path": Path(args.trials_path)} if getattr(args, "trials_path", None) else {}


def _require_decl(args, require_committed: bool = True) -> str:
    spec = Path(args.spec_path) if getattr(args, "spec_path", None) else SPEC_PATH
    return require_declaration_weather(spec, require_committed=require_committed)


def _half_frames(view: HalfView) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    series, trades = view.read_series()
    failed = getattr(view, "failed_ids", set())
    u24 = build_units(view.events, series, trades, ORIGIN_H["W3"], failed)
    u6 = build_units(view.events, series, trades, ORIGIN_H["W2"], failed)
    return u24, u6, series, trades


def assert_no_outcomes(u: pd.DataFrame) -> None:
    bad = [c for c in (*OUTCOME_COLUMNS, "Y", "Y2", "net", "w3", "ostatus") if c in u.columns]
    if bad:
        raise ValueError(f"census mode must not see outcome columns: {bad}")


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


# ---- census (q0042, counts only) --------------------------------------------------------------


def _g_counts(u: pd.DataFrame) -> dict:
    e = u[u["pre"] == "eligible"]
    gd, gc = int(e["day"].nunique()), int(e["city"].nunique())
    return {"n_eligible": int(len(e)), "G_day": gd, "G_city": gc,
            "testable": bool(len(e) >= MIN_UNITS and gd >= G_MIN and gc >= G_MIN),
            "city_method": "cr1_normal" if gc >= G_NORMAL else ("cr2_t_and_wild" if gc >= G_MIN else "not_testable"),
            "day_method": "cr1_normal" if gd >= G_NORMAL else ("cr2_t_and_wild" if gd >= G_MIN else "not_testable")}


def halfspread_descriptive(extract_root: Path, t_end: float) -> dict:
    """Recorded weather favourite half-spreads by band over captures before ``t_end`` (CB1 extract
    ``negrisk/`` tables; two-sided quotes only; no outcome column exists there). Descriptive, never used to
    change ``h_W``."""
    root = Path(extract_root)
    mpath = root / "manifest.json"
    if not mpath.exists():
        return {"available": False, "reason": f"no extract manifest at {mpath}"}
    caps = json.loads(mpath.read_text()).get("captures", {})
    vals: dict[str, list[float]] = {"0.30-0.45": [], "0.45-0.60": [], "0.60-0.95": []}
    n_cap = 0
    for cid, ent in sorted(caps.items()):
        st = _parse_end(ent.get("started_utc"))
        f = root / "negrisk" / f"{cid}.csv.gz"
        if st is None or st >= t_end or not f.exists():
            continue
        d = pd.read_csv(f, dtype={"neg_risk_market_id": str, "market_id": str})
        d = d[d["fee_category"].astype(str).str.startswith("weather")]
        d = d.dropna(subset=["best_bid", "best_ask"])
        if not len(d):
            continue
        n_cap += 1
        d = d.assign(mid=(d["best_bid"] + d["best_ask"]) / 2.0)
        for _, g in d.groupby("neg_risk_market_id"):
            top = g.sort_values("mid", ascending=False).iloc[0]
            if BAND[0] <= top["mid"] < BAND[1]:
                vals[band_of(float(top["mid"]))].append(float(top["best_ask"] - top["best_bid"]) / 2.0)
    return {"available": True, "captures": n_cap,
            "by_band": {k: {"n": len(v), "mean": float(np.mean(v)) if v else None,
                            "median": float(np.median(v)) if v else None} for k, v in vals.items()}}


def cmd_census_w(args) -> int:
    """``run_cb2.py census --family W`` (q0042 weather part; counts only, no outcome is opened). Reads:
    ``run_id`` (h6_weather), ``root``, ``seals_dir``, ``out_root``, ``cb1_extract_root`` (optional, for the
    recorded half-spread descriptive), ``spec_path`` is not needed (census precedes the freeze). Reads the
    SCREEN block's prices and trades only (logged); the outcome file is never opened. Writes
    ``<out_root>/census_W.json`` (a timestamped sibling if it exists) and prints a summary."""
    prep_args(args)
    root, seals, out = _paths(args)
    try:
        rid = refuse_run_id(args.run_id)
        view = open_half(root / rid, "screen", job="q0042_census", seals_dir=seals)
        u24, u6, _, _ = _half_frames(view)
        for u in (u24, u6):
            assert_no_outcomes(u)
        man = json.loads((root / rid / "manifest.json").read_text())
        doc = {
            "version": VERSION, "counts_only": True, "reads_outcomes": False, "run_id": rid,
            "d_split": view.seal["split"]["d_split"], "split": {k: view.seal["split"][k] for k in (
                "n_sample", "n_screen", "n_holdout", "n_embargo")},
            "frame_report": man.get("frame_report"), "manifest_counts": man.get("counts"),
            "screen_events": len(view.events),
            "origins": {str(int(h)): {"pre_status": u["pre"].value_counts().to_dict(), **_g_counts(u),
                                      "by_band": u[u["pre"] == "eligible"]["band"].value_counts().to_dict(),
                                      "local_class_eligible": u[u["pre"] == "eligible"]["local_class"]
                                      .value_counts().to_dict(),
                                      "unavailable_truncated": int((u["pre"] == "unavailable").sum()),
                                      "execution_rate": float(u[u["pre"] == "eligible"]["executed"].mean())
                                      if (u["pre"] == "eligible").any() else None}
                        for h, u in ((24, u24), (6, u6))},
            "w3_not_pre_extreme_share": float((u24[u24["pre"] == "eligible"]["local_class"] != "pre").mean())
            if (u24["pre"] == "eligible").any() else None,
            "tz_unknown_cities": sorted(set(view_city for view_city in
                                            {e["city"] for e in view.events} - set(TZ_TABLE))),
            "floors_note": FLOORS_NOTE}
        ext = getattr(args, "cb1_extract_root", None)
        if ext:
            doc["recorded_halfspread"] = halfspread_descriptive(Path(ext), _ep("2026-10-24T00:00:00Z"))
        path = out / "census_W.json"
        if path.exists():
            path = out / f"census_W.{_stamp()}.json"
        assert_outside_run_dir(path, root / rid)
        sha = write_results(path, doc)
    except (Cb2Error, h5_seal.SealError, FileNotFoundError) as exc:
        _print({"cb2_weather": VERSION, "refused": str(exc)[:400]})
        return 2
    _print({"cb2_weather": VERSION, "census_W": str(path), "sha256": sha,
            "origins": {k: {x: v[x] for x in ("n_eligible", "G_day", "G_city", "testable")}
                        for k, v in doc["origins"].items()}})
    return 0


# ---- screen / replicate -----------------------------------------------------------------------


def _header(view: HalfView, stage: str, decl: str, args) -> dict:
    return {"cb2_weather": VERSION, "stage": stage, "half": view.half, "run_id": view.run_dir.name,
            "label": LABEL, "declaration_sha256_weather": decl,
            "seal_listing_sha256": view.seal["listing_sha256"], "d_split": view.seal["split"]["d_split"],
            "n_events_half": len(view.events), "n_boot": int(args.n_boot),
            "n_wild": int(args.n_wild), "placebo_draws": int(args.placebo_draws),
            "cumulative_count": c1.cumulative_total(), "run_utc": _stamp(),
            "evidence_role": "exploratory_historical",
            "note": "development evidence only; not prospective, not an edge claim"}


def _evaluate_half(args, half: str, job: str, tests, alpha, stage: str, out_name: str,
                   require_committed: bool = True) -> tuple[int, dict | None]:
    root, seals, out = _paths(args)
    rid = refuse_run_id(args.run_id)
    decl = _require_decl(args, require_committed)
    path = out / out_name / "results.json"
    assert_outside_run_dir(path, root / rid)
    if path.exists():
        raise Refused(f"{path} exists; results files are never overwritten")
    view = open_half(root / rid, half, job=job, seals_dir=seals)
    u24, u6, _, _ = _half_frames(view)
    outs = parse_event_outcomes(view.read_outcomes())
    u24, u6 = attach_outcomes(u24, outs), attach_outcomes(u6, outs)
    res = run_w_family(u24, u6, outs, tests=tests, alpha=alpha, n_boot=int(args.n_boot),
                       n_wild=int(args.n_wild), placebo_draws=int(args.placebo_draws))
    doc = {**_header(view, stage, decl, args), **res}
    ps = {k: v["p"] for k, v in res["tests"].items() if v.get("p") is not None}
    doc["by_label"] = by_label(ps, int((doc["cumulative_count"] or {}).get("total") or len(ps)) or len(ps))
    return 0, {"doc": doc, "path": path, "decl": decl, "res": res, "view": view}


def cmd_screen_w(args, *, require_committed: bool = True) -> int:
    """``run_cb2.py screen --family W`` (q0045). Reads: ``run_id``, ``root``, ``seals_dir``, ``out_root``,
    ``n_boot``, ``n_wild``, ``placebo_draws``, ``spec_path`` (committed ``cb2_v1.json`` with
    ``weather_sha256``), ``trials_path`` (optional); ``require_committed`` is a test-only function parameter. Refuses without the
    committed declaration. Opens the sealed SCREEN block only (HOLDOUT and embargo ids are refused, every
    read logged), tests W2 and W3 at Stage 1 (alpha 0.01, floors, R_ann, placebos, binding robustness),
    records W1 as descriptive, and writes ``<out_root>/W_screen/results.json`` (outside the sealed run)."""
    prep_args(args)
    try:
        _, st = _evaluate_half(args, "screen", "q0045_cb2_screen_W", ("W2", "W3"), ALPHA_STAGE1,
                               "screen", "W_screen", require_committed)
    except (Cb2Error, h5_seal.SealError, FileNotFoundError) as exc:
        _print({"cb2_weather": VERSION, "refused": str(exc)[:400]})
        return 2
    doc, res, path = st["doc"], st["res"], st["path"]
    sha = write_results(path, doc)
    w1 = res["descriptive"].get("W1", {})
    log_trials_w(res["tests"], kind=KIND_TEST, role="exploratory_historical", family="W",
                 dataset="history:h6_weather:screen", results_path=str(path), results_sha256=sha,
                 run_id="cb2_W_screen", decl_sha=st["decl"], placebo=res["placebo"],
                 descriptive={"W1": w1}, **_trials_kw(args))
    _print({"cb2_weather": VERSION, "results": str(path), "results_sha256": sha,
            "tests": {k: {"p": v.get("p"), "mean": v.get("mean"), "n": v.get("n"), "advance": v["advance"],
                          "fail": v.get("fail")} for k, v in res["tests"].items()}})
    return 0


def stage2_k(out_root: Path, adv_w: list[str]) -> dict:
    """Stage-2 family size k, fixed when Stage 1 ends: the W tests that advanced plus the L/X tests that
    advanced in ``<out_root>/L_dev/results.json``. If the L/X Stage-1 results do not exist yet, k assumes the
    declared maximum for them (L1, X1, X2 = 3), the conservative choice. Never taken from a command-line flag."""
    lp = Path(out_root) / "L_dev" / "results.json"
    if lp.exists():
        adv_l = [k for k, v in json.loads(lp.read_text()).get("tests", {}).items() if v.get("advance")]
        return {"k": len(adv_w) + len(adv_l), "source": str(lp), "adv_w": adv_w, "adv_lx": adv_l}
    return {"k": len(adv_w) + 3, "source": "L/X Stage 1 not yet available: declared maximum 3 assumed",
            "adv_w": adv_w, "adv_lx": None}


def cmd_replicate_w(args, *, require_committed: bool = True) -> int:
    """``run_cb2.py replicate --family W`` (q0047). Reads, besides the screen flags: ``screen_results``
    (default ``<out_root>/W_screen/results.json``). The Stage-2 family size k comes from the Stage-1
    results (:func:`stage2_k`), never from a flag. Exits 0 'nothing advanced' WITHOUT opening the HOLDOUT when no W test advanced.
    Otherwise opens the sealed HOLDOUT block once (logged), tests only the advanced tests at
    alpha = 0.05 / k (Bonferroni; the batch Holm can only add passes), writes
    ``<out_root>/W_holdout/results.json`` and logs ``cb2_replication`` lines."""
    prep_args(args)
    root, seals, out = _paths(args)
    try:
        refuse_run_id(args.run_id)
        decl = _require_decl(args, require_committed)
        sp = Path(args.screen_results) if getattr(args, "screen_results", None) else out / "W_screen" / "results.json"
        if not sp.exists():
            raise Refused(f"no screen results at {sp}; run the screen first")
        scr = json.loads(sp.read_text())
        if scr.get("declaration_sha256_weather") != decl:
            raise Refused("screen results carry a different declaration hash")
        adv = [k for k, v in scr["tests"].items() if v.get("advance")]
        if not adv:
            _print({"cb2_weather": VERSION, "status": "nothing advanced", "holdout_opened": False})
            return 0
        kinfo = stage2_k(out, adv)
        k = max(kinfo["k"], len(adv))
        alpha = ALPHA_STAGE2 / k
        _, st = _evaluate_half(args, "holdout", "q0047_cb2_holdout_W", tuple(adv), alpha, "holdout",
                               "W_holdout", require_committed)
    except (Cb2Error, h5_seal.SealError, FileNotFoundError) as exc:
        _print({"cb2_weather": VERSION, "refused": str(exc)[:400]})
        return 2
    doc, res, path = st["doc"], st["res"], st["path"]
    for tid, t in res["tests"].items():
        t["replicated"] = bool(t["advance"])
        res["credit"][tid] = res["credit"].get(tid)
    doc.update(advanced_at_stage1=adv, k_stage2=k, k_source=kinfo, alpha_bonferroni=alpha, evidence_role="exploratory_historical",
               holm_w_only=_holm({t: res["tests"][t]["p"] for t in adv}, ALPHA_STAGE2),
               ceiling="development-replicated (L2-dev); out-of-time, not out-of-season; stage P confirms")
    sha = write_results(path, doc)
    log_trials_w(res["tests"], kind=KIND_REP, role="exploratory_historical", family="W_holdout",
                 dataset="history:h6_weather:holdout", results_path=str(path), results_sha256=sha,
                 run_id="cb2_W_holdout", decl_sha=decl, placebo=res["placebo"],
                 descriptive={"W1": res["descriptive"].get("W1", {})}, **_trials_kw(args))
    _print({"cb2_weather": VERSION, "results": str(path), "results_sha256": sha, "alpha": alpha,
            "tests": {t: {"p": v.get("p"), "mean": v.get("mean"), "replicated": v["replicated"],
                          "fail": v.get("fail")} for t, v in res["tests"].items()}})
    return 0


def _holm(ps: dict[str, float], alpha: float) -> dict:
    order = sorted(ps, key=lambda k: ps[k])
    m = len(order)
    out, still = {}, True
    for i, k in enumerate(order):
        thr = alpha / (m - i)
        still = still and ps[k] < thr
        out[k] = {"p": ps[k], "threshold": thr, "reject": bool(still)}
    return out


# The runner's lazy hook looks for cmd_<command> (e.g. cmd_screen); the explicit names are the family-suffixed ones.
cmd_census = cmd_census_w
cmd_screen = cmd_screen_w
cmd_replicate = cmd_replicate_w


# ---- stage P: weather events on live extract captures at recorded next-capture asks -----------

REP_START_FILE = SEALS_DIR / "cb2_t_rep_start.json"
GAP_H = (1.5, 3.0)
ORIGIN_WINDOW_H = 2.0
DEPTH_MIN_SIZE = 5.0


def pinned_rep_start(path: Path | None = None) -> float:
    p = Path(path) if path else REP_START_FILE
    if not p.exists():
        raise Refused(f"no pinned T2_rep_start at {p}")
    return parse_when(json.loads(p.read_text())["t2_rep_start"])


def _flag(s: pd.Series) -> np.ndarray:
    return s.astype(str).str.lower().isin(["true", "1", "1.0"]).to_numpy()


def stagep_events(extract_root: Path) -> dict[str, dict]:
    """neg_risk_market_id -> {event_id, direction, city, title_date} for temperature events, from the FIRST
    ``event_text`` row of each event (text is read at first extraction)."""
    p = Path(extract_root) / "event_text.csv.gz"
    if not p.exists():
        raise Refused(f"{p} missing: stage P needs event_text (cb1-extract-v2, live captures only)")
    d = pd.read_csv(p, dtype=str, keep_default_na=False).sort_values(
        ["neg_risk_market_id", "fetched_utc"], kind="stable").drop_duplicates("neg_risk_market_id")
    out = {}
    for r in d.itertuples():
        t = parse_title(r.title)
        if t:
            out[str(r.neg_risk_market_id)] = {"event_id": str(r.event_id), **t}
    return out


def stagep_units(extract_root: Path, t_rep_start: float, *, w_len_d: int = T2_W_END_DAYS) -> tuple[
        pd.DataFrame, dict]:
    """Pre-outcome stage-P units for both origins. For each weather event with ``end_at - 24h >= t_rep_start``
    and ``end_at < t_rep_start + 56 d``: origin capture = the last extracted capture with start in
    ``(t - 2h, t]``; the event must be member-complete (as-of ``event_members``, 4-25 members) with every
    member open, active and accepting orders; favourite = highest two-sided mid (ties to the lower id);
    ``0.30 <= mid < 0.95`` and ``volume_num > 0`` with a ``last_trade_price``. Execution uses the favourite's
    ``best_ask`` at the next capture whose gap lies in [1.5, 3] h; no ask there means no trade (net 0, kept)."""
    root = Path(extract_root)
    ev_map = stagep_events(root)
    starts = c1.load_manifest_starts(root)
    cs_by = {cid: st for cid, st in starts.items() if st >= t_rep_start - 3 * HOUR}
    order = sorted(cs_by, key=lambda c: cs_by[c])
    nxt, gap_cnt = c1.next_capture_pairs(cs_by, GAP_H)
    members = c1.members_asof_loader(root)
    tables: dict[str, pd.DataFrame] = {}
    for cid in order:
        f = root / "negrisk" / f"{cid}.csv.gz"
        if f.exists():
            d = pd.read_csv(f, dtype={"neg_risk_market_id": str, "market_id": str, "event_id": str})
            tables[cid] = d[d["neg_risk_market_id"].isin(ev_map)]
    end_of: dict[str, float] = {}
    for d in tables.values():
        for gid, g in d.groupby("neg_risk_market_id"):
            if gid not in end_of:
                ends = [x for x in (_parse_end(v) for v in g["end_date"].dropna().astype(str)) if x is not None]
                if ends:
                    end_of[gid] = float(np.median(ends))
    t_end = t_rep_start + w_len_d * DAY
    cnt = {"events_seen": len(end_of), "in_window": 0, "no_origin_capture": 0, "not_member_complete": 0,
           "not_open_accepting": 0, "no_two_sided": 0, "excl_band": 0, "excl_no_trade": 0, "eligible": 0,
           "gap_pairs": gap_cnt}
    rows = []
    last_bid: dict[str, float] = {}
    for cid in order:  # last extracted bid per market (censoring value), in time order
        d = tables.get(cid)
        if d is not None:
            for r in d.itertuples():
                if not pd.isna(r.best_bid):
                    last_bid[str(r.market_id)] = float(r.best_bid)
    for gid, end in sorted(end_of.items()):
        if not (end - 24 * HOUR >= t_rep_start and end < t_end):
            continue
        cnt["in_window"] += 1
        info = ev_map[gid]
        for h in (24.0, 6.0):
            t = end - h * HOUR
            cands = [c for c in order if t - ORIGIN_WINDOW_H * HOUR < cs_by[c] <= t and c in tables]
            base = {"event_id": info["event_id"], "gid": gid, "city": info["city"],
                    "direction": info["direction"], "end_epoch": end, "t": t, "origin_h": h,
                    "day": datetime.fromtimestamp(end, UTC).strftime("%Y-%m-%d"), "week": week_label(end),
                    "fav_id": None, "p_fav_t": math.nan, "p_exec": math.nan, "executed": False,
                    "a": math.nan, "f": math.nan, "K": math.nan, "pre": "", "exec_cap": None,
                    "depth_ok": False, "last_bid": math.nan, "second_id": None, "p2_exec": math.nan,
                    "band": "", "title_date_iso": parse_title_date(info["title_date"], end),
                    "local_class": "date_unknown"}
            if not cands:
                cnt["no_origin_capture"] += h == 24.0
                rows.append({**base, "pre": "excl_no_origin_capture"})
                continue
            c = cands[-1]
            g = tables[c][tables[c]["neg_risk_market_id"] == gid]
            n_mem = members(cs_by[c]).get(gid)
            if n_mem is None or len(g) != n_mem or not (MEMBER_RANGE[0] <= n_mem <= MEMBER_RANGE[1]):
                cnt["not_member_complete"] += h == 24.0
                rows.append({**base, "pre": "excl_not_member_complete"})
                continue
            if not (_flag(g["accepting_orders"]).all() and _flag(g["active"]).all()
                    and not _flag(g["closed"]).any()):
                cnt["not_open_accepting"] += h == 24.0
                rows.append({**base, "pre": "excl_not_open_accepting"})
                continue
            g2 = g.dropna(subset=["best_bid", "best_ask"]).copy()
            if not len(g2):
                cnt["no_two_sided"] += h == 24.0
                rows.append({**base, "pre": "excl_no_two_sided"})
                continue
            g2["mid"] = (g2["best_bid"] + g2["best_ask"]) / 2.0
            g2["_k"] = g2["market_id"].map(_mid_key)
            g2 = g2.sort_values(["mid", "_k"], ascending=[False, True])
            top = g2.iloc[0]
            fav = str(top["market_id"])
            mid = float(top["mid"])
            base.update(fav_id=fav, p_fav_t=mid, band=band_of(mid), last_bid=last_bid.get(fav, math.nan))
            if len(g2) > 1:
                base["second_id"] = str(g2.iloc[1]["market_id"])
            if not (BAND[0] <= mid < BAND[1]):
                cnt["excl_band"] += h == 24.0
                rows.append({**base, "pre": "excl_band"})
                continue
            traded = (not pd.isna(top["volume_num"]) and float(top["volume_num"]) > 0
                      and not pd.isna(top["last_trade_price"]))
            if not traded:
                cnt["excl_no_trade"] += h == 24.0
                rows.append({**base, "pre": "excl_no_trade"})
                continue
            cnt["eligible"] += h == 24.0
            c2 = nxt.get(c)
            row = {**base, "pre": "eligible", "exec_cap": c2}
            if c2 is not None and c2 in tables:
                r2 = tables[c2][tables[c2]["market_id"] == fav]
                if len(r2):
                    r2 = r2.iloc[0]
                    row["local_class"] = local_class(info["city"], info["direction"], row["title_date_iso"],
                                                     cs_by[c2])
                    ok = (str(r2["accepting_orders"]).lower() in ("true", "1", "1.0")
                          and str(r2["closed"]).lower() not in ("true", "1", "1.0"))
                    ask, bid = r2["best_ask"], r2["best_bid"]
                    if ok and not pd.isna(ask) and not pd.isna(bid):
                        rate, ex = c1.leg_rate(r2["fee_schedule"], r2["fee_category"])
                        a = float(ask)
                        row.update(executed=True, a=a, f=c1.leg_fee(a, rate, ex), K=a + c1.leg_fee(a, rate, ex),
                                   p_exec=(float(ask) + float(bid)) / 2.0, exec_start=cs_by[c2],
                                   depth_ok=bool(not pd.isna(r2.get("sw1_ask_size_1"))
                                                 and float(r2.get("sw1_ask_size_1")) >= DEPTH_MIN_SIZE))
            rows.append(row)
    return pd.DataFrame(rows), cnt


def fetch_event_outcomes(lim, event_ids: list[str]) -> dict[str, dict]:
    """One Gamma ``/events?id=`` request per event; returns the same structure as
    :func:`parse_event_outcomes`. A missing or unparsable event is absent (kept as unresolved)."""
    rows = []
    for eid in event_ids:
        status, data = lim.get(GAMMA_EVENTS, [("id", eid)])
        if status != 200 or not isinstance(data, list) or not data:
            continue
        for m in data[0].get("markets") or []:
            rows.append({"market_id": str(m.get("id")), "event_id": str(eid),
                         "outcome_prices": m.get("outcomePrices"), "closed": m.get("closed"),
                         "closed_time": m.get("closedTime") or ""})
    return parse_event_outcomes(pd.DataFrame(rows, columns=["market_id", "event_id", "outcome_prices",
                                                            "closed", "closed_time"])) if rows else {}


def attach_stagep_outcomes(u: pd.DataFrame, outs: dict[str, dict]) -> tuple[pd.DataFrame, dict]:
    """Outcomes for stage-P units. Unresolved events are CENSORED: the favourite is valued at its last
    extracted bid (flagged); sensitivities at 0 and 1 are returned. Closed events without a valid single
    winner are anomalous (excluded from the primary, counted, losers in the worst case)."""
    u = u.copy()
    n = len(u)
    ostatus, Y, dd = [""] * n, np.full(n, np.nan), np.full(n, np.nan)
    for i, r in enumerate(u.itertuples()):
        o = outs.get(r.event_id)
        if o is None or o["status"] == "open":
            ostatus[i] = "censored"
            Y[i] = r.last_bid
        elif o["status"] == "resolved" and r.fav_id is not None:
            ostatus[i] = "resolved"
            Y[i] = o["yes"].get(r.fav_id, math.nan)
            if r.executed and not math.isnan(o["closed_time"]) and not math.isnan(getattr(r, "exec_start", math.nan)):
                dd[i] = (o["closed_time"] - r.exec_start) / DAY
        else:
            ostatus[i] = "anomalous"
    u["ostatus"], u["Y"], u["d"] = ostatus, Y, dd
    ex = u["executed"].to_numpy(bool)
    u["net"] = np.where(ex, u["Y"] - u["K"], 0.0)
    u["w3"] = np.where(ex, u["Y"] - u["p_exec"], 0.0)
    cens = u["ostatus"].to_numpy() == "censored"
    share = {"n_events": int(len(u)), "censored": int(cens.sum()),
             "share": float(cens.mean()) if n else 0.0,
             "resolution_lag_sensitive": bool(n and cens.mean() > MAX_CENSORED_STAGEP)}
    return u, share


def stagep_primary(u: pd.DataFrame) -> pd.DataFrame:
    return u[(u["pre"] == "eligible") & (u["ostatus"].isin(["resolved", "censored"]))
             & u["Y"].notna()].reset_index(drop=True)


def stagep_family(u24: pd.DataFrame, u6: pd.DataFrame, *, tests, alpha: float, n_boot: int, n_wild: int,
                  placebo_draws: int, seed: int = SEED) -> dict:
    res: dict = {"tests": {}, "placebo": {}, "credit": {}, "classes": {}, "sensitivity": {}}
    for tid in tests:
        spec = HYPOTHESES_CB2_W[tid]
        u = u6 if tid == "W2" else u24
        col = "net" if tid == "W2" else "w3"
        p = stagep_primary(u)
        anom = u[(u["pre"] == "eligible") & (u["ostatus"] == "anomalous") & u["executed"]]
        wc = (-anom["K"].to_numpy(float)) if col == "net" else (-anom["p_exec"].to_numpy(float))
        g = w_gate(p, spec, wc, alpha=alpha, n_boot=n_boot, n_wild=n_wild, seed=seed, col=col)
        pl = breakeven_placebo_w(p, spec, wc, alpha=alpha, test=tid, draws=placebo_draws, n_wild=n_wild) \
            if g.get("testable") else {"draws": 0, "advance_rate": None, "calibrated": False}
        exe = p["executed"].to_numpy(bool)
        sens = {}
        for lab, val in (("censored_at_0", 0.0), ("censored_at_1", 1.0)):
            y = np.where(p["ostatus"].to_numpy() == "censored", val, p["Y"].to_numpy(float))
            v = np.where(exe, (y - p["K"].to_numpy(float)) if col == "net" else (y - p["p_exec"].to_numpy(float)), 0.0)
            sens[lab] = float(v.mean()) if len(v) else None
        dep = p[p["depth_ok"]] if "depth_ok" in p else p.iloc[0:0]
        sens["depth_checked"] = {"n": int(len(dep)), "mean": float(dep[col].mean()) if len(dep) else None}
        sens["execution_rate"] = float(exe.mean()) if len(p) else None
        res["placebo"][tid] = pl
        res["tests"][tid] = {**g, "test_id": tid, "kind": spec["kind"],
                             "advance": bool(g["advance_core"] and pl["calibrated"]),
                             "replicated": bool(g["advance_core"] and pl["calibrated"])}
        res["sensitivity"][tid] = sens
        res["credit"][tid] = credit_rule(p, col, float(g["mean"])) if len(p) and g.get("mean") is not None else None
        res["classes"][tid] = class_breakdown(p, col)
    return res


def cmd_stagep(args, *, require_committed: bool = True, t_rep_start: float | None = None,
               now: float | None = None) -> int:
    """``run_cb2.py stagep --family W`` (q0049). Reads: ``extract_root`` (the CB1 extract with
    ``negrisk/``, ``event_members.csv.gz`` and ``event_text.csv.gz``), ``out_root``, ``rps``, ``n_boot``,
    ``n_wild``, ``placebo_draws``, ``spec_path``, ``holdout_results``, ``snapshot_root``,
    ``trials_path``; the rep start is always the pinned ``seals/cb2_t_rep_start.json`` and the clock is the
    wall clock (``t_rep_start``/``now`` are test-only function parameters, not flags); optional test hooks ``transport``, ``wall_clock``, ``sleep``, ``live_check``,
    ``health_check``. Refuses before ``T2_W_out`` (= T2_rep_start + 56 d + 7 d) and without the committed
    declaration; exits 0 'nothing replicated' when the HOLDOUT replicated no W test."""
    prep_args(args)
    root, _, out = _paths(args)
    try:
        refuse_run_id(args.run_id)
        decl = _require_decl(args, require_committed)
        t0 = t_rep_start if t_rep_start is not None else pinned_rep_start()
        t_out = t0 + (T2_W_END_DAYS + T2_W_OUT_DAYS) * DAY
        now = now if now is not None else time.time()
        if now < t_out:
            raise Refused(f"stage P is read at T2_W_out ({_iso(t_out)}); now is {_iso(now)}")
        hp = Path(args.holdout_results) if getattr(args, "holdout_results", None) \
            else out / "W_holdout" / "results.json"
        if not hp.exists():
            raise Refused(f"no holdout results at {hp}")
        hold = json.loads(hp.read_text())
        rep = [k for k, v in hold["tests"].items() if v.get("replicated")]
        if not rep:
            _print({"cb2_weather": VERSION, "status": "nothing replicated"})
            return 0
        path = out / "W_stageP" / "results.json"
        if path.exists():
            raise Refused(f"{path} exists; results files are never overwritten")
        ext = Path(args.extract_root)
        u_all, cnt = stagep_units(ext, t0)
        u24, u6 = (u_all[u_all["origin_h"] == 24.0].reset_index(drop=True),
                   u_all[u_all["origin_h"] == 6.0].reset_index(drop=True))
        health = getattr(args, "health_check", None)
        if health is not None or getattr(args, "snapshot_root", None):
            ok, why = health(now) if health else collector_healthy(Path(args.snapshot_root), now)
            if not ok:
                _print({"cb2_weather": VERSION, "stopped": f"paused_collector_health: {why}", "transient": True})
                return 0
        pol = RatePolicy(getattr(args, "transport", None) or hb.httpx_transport(),
                         clock=getattr(args, "wall_clock", None) or time.time)
        lim = hb.Limiter(pol, rps=min(float(getattr(args, "rps", 4.0) or 4.0), 4.0),
                         sleep=getattr(args, "sleep", None) or time.sleep,
                         live_check=getattr(args, "live_check", hb.live_pass_or_lock))
        pol.limiter = lim
        eids = sorted(set(u_all.loc[u_all["pre"] == "eligible", "event_id"]))
        outs = fetch_event_outcomes(lim, eids)
        u24, cens24 = attach_stagep_outcomes(u24, outs)
        u6, cens6 = attach_stagep_outcomes(u6, outs)
        k = len(rep)
        alpha = ALPHA_STAGEP / k
        res = stagep_family(u24, u6, tests=tuple(rep), alpha=alpha, n_boot=int(args.n_boot),
                            n_wild=int(args.n_wild), placebo_draws=int(args.placebo_draws))
        # TODO(batch_holm, freeze-check fix 17): stage P must use the batch-wide Holm that the structural side adds
        # (cb2_structural.batch_holm / run_cb2.py). Until it exists the local W-only Holm below is reported and
        # the Bonferroni alpha above stays binding. Replace `batch_holm_w` with the shared call once available.
        batch_holm_w = _holm({t: res["tests"][t]["p"] for t in res["tests"]}, ALPHA_STAGEP)
        doc = {"cb2_weather": VERSION, "stage": "P", "label": LABEL, "declaration_sha256_weather": decl,
               "t_rep_start": _iso(t0), "T2_W_out": _iso(t_out), "alpha": alpha, "k_stage_p": k,
               "replicated_at_holdout": rep, "counts": cnt, "censoring": {"origin24": cens24, "origin6": cens6},
               "requests": {"total": lim.requests, "http_429": pol.n429}, "run_utc": _stamp(),
               "evidence_role": "prospective_confirmation", "cumulative_count": c1.cumulative_total(),
               "execution_rate": {t: res["sensitivity"][t]["execution_rate"] for t in res["tests"]},
               "mde_note": "stage-P MDEs are divided by the execution rate",
               "batch_holm_TODO": "shared batch_holm not yet available; local W-only Holm reported",
               "holm_w_only": batch_holm_w, **res}
        assert_outside_run_dir(path, root / RUN_ID)
        sha = write_results(path, doc)
    except (Cb2Error, h5_seal.SealError, FileNotFoundError, KeyError) as exc:
        _print({"cb2_weather": VERSION, "refused": str(exc)[:400]})
        return 2
    log_trials_w(res["tests"], kind=KIND_PROSP, role="prospective_confirmation", family="W_stageP",
                 dataset="cb1_extract:negrisk:stageP", results_path=str(path), results_sha256=sha,
                 run_id="cb2_W_stageP", decl_sha=decl, placebo=res["placebo"], **_trials_kw(args))
    _print({"cb2_weather": VERSION, "results": str(path), "results_sha256": sha,
            "tests": {t: {"p": v.get("p"), "mean": v.get("mean"), "replicated": v["replicated"],
                          "fail": v.get("fail")} for t, v in res["tests"].items()}})
    return 0
