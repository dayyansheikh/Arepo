# ruff: noqa: E501
"""CB6 ``h8_tail`` data jobs: rules file, exclusion keys, smoke test, fetch (q0120) and seal (q0121)
(docs/research_lab/CREATIVE_BATCH_6.md sections 1.3, 1.4, CB6-F and 10.3).

Data only: copies fields as the API returns them and computes no statistic. Reuses the h7 fetch machinery of
``cb4_data`` (``FetchRun``, ``_fetch_items``, ``_paged_strict``) and ``history_backfill`` (``Limiter``,
``DiskBudget``, ``frame_row``, ``allocate_weighted``, wallet hashing).

Memory: the frame walk never holds raw events. Each day is appended to ``frame_partial.jsonl.gz`` as one gzip
member and the filtering passes stream it record by record; only market ids per stratum stay in memory.
"""

from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import inspect
import io
import json
import math
import platform
import random
import re
import socket
import statistics
import sys
import time
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from . import cb4_data as c4
from . import event_study, h5_seal
from . import history_backfill as hb

FETCH_VERSION = "h8-cb6-fetch-v1"
RULES_VERSION = "cb6-tail-rules-v1"
RUN_ID = "h8_tail"
T_SEAL = c4.T_SEAL
T_SEAL_EPOCH = hb.T_SEAL_EPOCH
DAY = 86400.0
HOUR = 3600.0
HIST_ROOT = c4.HIST_ROOT
SEALS_DIR = h5_seal.SEALS_DIR
RULES_FILE = SEALS_DIR / "cb6_tail_rules.json"
SMOKE_DEFAULT = c4.DATA_DUMPS / "research_lab" / "creative_batch6" / "tail_smoke.json"
COMPLETE_TOKEN = "tail_fetch_complete"
NOT_RUN_TOKEN = "not_run_deadline"
UNVERIFIED_TOKEN = "disjointness_unverified"
TERMINAL_TOKENS = (COMPLETE_TOKEN, NOT_RUN_TOKEN, UNVERIFIED_TOKEN)
NOT_RUN_FILE = "NOT_RUN_DEADLINE.json"
UNVERIFIED_FILE = "DISJOINTNESS_UNVERIFIED.json"
OUTCOME_FILE = "outcomes_guarded.csv.gz"
DATA_DUMPS_FETCH_CAP_GB = 12.5  # host data-dumps cap 13 GB (retention live); size + the 0.25 GB output cap must stay below it
TEMPFAIL = 75
DISK_BUDGET_TOKEN = "disk_budget"

REFUSED_RUN_IDS = ("h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series")
REFUSED_ROOTS = ("cb1_extract", "cb2_extract", "cb3_extract", "cb4_extract", "cb5_extract", "cb3_followup",
                 "cross_venue_live", "surprise_live")
H7_RUN_IDS = ("h7_cb4_era", "h7_cb4_series")

# ---- declared parameters (all of them are in the rules file) -----------------------------------------------------
SEED = "arepo-h8-tail"
ORIGIN_SEED = "arepo-h8-tail-origins"
SMOKE_SEED = "arepo-h8-smoke"
SPLIT_SEED = "arepo-cb6-tail-split"
N_MARKETS = 4500
CREATED_FROM = "2025-09-01"
CREATED_TO = "2026-07-31"  # inclusive day
END_FROM = "2025-09-01"
END_BEFORE_FETCH_DAYS = 7
WINDOWS_PER_DAY = 1
WINDOW_MINUTES = 15
PAGES_PER_WINDOW = 20
MIN_LIFE_DAYS = 14
DESCRIPTION_CHARS = 4000
SPORTS_WEIGHT = 0.5
OTHER_WEIGHT = 1.0
MAX_ORIGINS = 3
ORIGIN_START_OFFSET_DAYS = 7
ORIGIN_END_OFFSET_HOURS = 24
ORIGIN_LATEST_BEFORE_FETCH_DAYS = 60
PRICE_FIDELITY = 60
PRICE_BEFORE_DAYS = 8
PRICE_AFTER_DAYS = 2
PRINT_BEFORE_DAYS = 30
PRINT_AFTER_HOURS = 6
PRINT_PAGE = 1000
PRINT_PAGES = 3
GAMMA_IDS_PER_REQUEST = 50
MAX_UNVERIFIED_KEY_SHARE = 0.02
KEY_TYPES = ("event", "neg_risk_market", "series")
MAX_ITEM_ATTEMPTS = c4.MAX_ITEM_ATTEMPTS
MAX_DAY_ATTEMPTS = c4.MAX_DAY_ATTEMPTS
OUTPUT_CAP_GB = 0.25  # frame.csv.gz (4000-char descriptions) + frame_partial.jsonl.gz coexist; 0.12 was tight (freeze check 2026-10-17)
SMOKE_N = 20
SMOKE_MIN_PASS = 18
SMOKE_MIN_FRACTION = 0.8
SMOKE_SPACING = (3600.0, 300.0)
SMOKE_BEFORE_END_DAYS = (12, 2)
SPLIT_RULE = ("sha256(SPLIT_SEED + '|' + event_key), first byte even -> SCREEN else HOLDOUT; event_key = Gamma event id "
              "(market id if none), merged across negRiskMarketID (component minimum)")

# CB6-T feature rules (CREATIVE_BATCH_6.md CB6-T "Features"; fixed before any fetch)
CLASS_D_PATTERNS = (r"\bannounc\w*", r"\bcourt\w*", r"\border\w*", r"\baward\w*", r"\bnominat\w*", r"\bstrike\w*")
CLASS_C_PATTERNS = (r"\bprice\w*", r"\btemperature\w*", r"\bscore\w*", r"\bpoll\w*")
CLASS_DESCRIPTION_FALLBACK_CHARS = 500
CLARIFICATION_MARKERS = ("clarif", "update:", "updated", "additional context", "edit:")
NOTE_DATE_PATTERN = (r"note:\s*(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?|"
                     r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}|"
                     r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)")
LONGSHOT_BAND = (0.02, 0.10)
PRICE_BANDS = ((0.02, 0.04), (0.04, 0.07), (0.07, 0.10))
DRIFT_DAYS = 7
DRIFT_MIN = 0.01
LARGE_BUY_WINDOW_HOURS = 24
LARGE_BUY_MULTIPLE = 5.0
LARGE_BUY_MEDIAN_DAYS = 30
LARGE_BUY_MEDIAN_MIN_PRINTS = 10
YOUNG_WALLET_DAYS = 30
USABLE_POINT_LAG_S = 600  # a point stamped t' is usable at t only if t' <= t - 600
MAX_POINT_AGE_S = 7200
MIN_PRINTS_BEFORE_ORIGIN = 1
PRINT_LOOKBACK_FOR_ELIGIBILITY_DAYS = 7

EXCLUSION_PINS = (
    {"name": "h1_first", "kind": "sample", "path": "history/h1_first/sample.csv.gz",
     "sha256": "24bbda60714852679f8203f399c8852a6a97d99b01cebb2b19c7c8f8f2b53cf8"},
    {"name": "h2_main", "kind": "sample", "path": "history/h2_main/sample.csv.gz",
     "sha256": "77a15bd96bcd17c923e90e3e214874cad8df9ed4cd66eb6145cc8922c28954ec"},
    {"name": "h3_power", "kind": "sample", "path": "history/h3_power/sample.csv.gz",
     "sha256": "f8e1a7bbd16d57206fcd45c502263d2b7ceb40b22108e248c613d5148476004d"},
    {"name": "h5_cb1", "kind": "seal", "path": "docs/research_lab/seals/h5_cb1_SEAL.json",
     "sha256": "fbac4c8d2898447555a6e68de0d31fbc9b4efa5aec1fa58d62ce2373685fae85"},
    {"name": "h5_cb1_ladders", "kind": "seal", "path": "docs/research_lab/seals/h5_cb1_ladders_SEAL.json",
     "sha256": "d3e7b335c15ac5917d270f5a0cbb6ded84363408dcc6a54d47f20ba6aed28104"},
)

MAIN_COLUMNS = ["market_id", "condition_id", "token0", "token1", "event_id", "event_ids", "neg_risk_market_id",
                "series_ids", "fee_category", "status", "closed", "created_at", "start_at", "end_at", "start_epoch",
                "end_epoch", "neg_risk", "question", "event_title", "slug", "topic", "outcomes", "description"]
GUARDED_COLUMNS = ["market_id", "outcome_prices", "uma_status", "liquidity", "volume", "closed_time", "close_epoch"]
KEY_COLUMNS = ["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"]
SAMPLE_EXTRA = ["stratum", "stratum_size", "stratum_alloc", "inclusion_prob", "sample_weight"]
ORIGIN_COLUMNS = ["market_id", "origin_ts", "origin_utc", "k"]
PRICE_COLUMNS = ["origin_ts", "t", "p"]
TRADE_COLUMNS = hb.TRADE_COLUMNS
WINDOW_COLUMNS = ["market_id", "origin_ts", "price_points", "price_dropped_post_cap", "print_rows", "print_pages",
                  "window_truncated", "oldest_ts", "dropped_post_cap", "start", "end", "usable_point",
                  "qualifying_wallets", "wallet_status"]


class Cb6Error(RuntimeError):
    """Base class for refusals."""


class Refused(Cb6Error):
    """A guard refused to run (exit 2)."""


class NotNow(Cb6Error):
    """A precondition that will hold later (exit 75, queue tempfail)."""


ApiError = c4.ApiError
SealError = h5_seal.SealError


# ---- small helpers -----------------------------------------------------------------------------------------------


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _parse_ts(v: Any) -> float | None:
    return c4._parse_ts(v)


def _gz_jsonl_member(rec: dict) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write((json.dumps(rec, sort_keys=True, default=float) + "\n").encode())
    return buf.getvalue()


def iter_partial(path: Path) -> Iterator[dict]:
    """Stream the per-day records of ``frame_partial.jsonl.gz`` (one gzip member per day), one record at a time."""
    p = Path(path)
    if not p.exists():
        return
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def refuse_run_id(run_id: str) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB6 refuses it")
    if run_id != RUN_ID:
        raise Refused(f"this command writes only {RUN_ID!r}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    if any(part in REFUSED_ROOTS for part in Path(path).parts):
        raise Refused(f"path {path} is under a refused CB1-CB5 / live root; CB6 refuses it")
    return Path(path)


def _csv_list(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


# ---- deterministic rules (their SOURCE is hashed into the rules file) -----------------------------------------------


_D_RX = [re.compile(p) for p in CLASS_D_PATTERNS]
_C_RX = [re.compile(p) for p in CLASS_C_PATTERNS]
_NOTE_RX = re.compile(NOTE_DATE_PATTERN)


def class_d(question: str, description: str) -> bool:
    """Feature (i): class D iff the lower-cased question matches D and not C; if it matches neither, the same rule on the
    first 500 characters of the description; otherwise not D."""
    def verdict(text: str) -> bool | None:
        t = (text or "").lower()
        d = any(rx.search(t) for rx in _D_RX)
        c = any(rx.search(t) for rx in _C_RX)
        if not d and not c:
            return None
        return d and not c

    v = verdict(question)
    if v is None:
        v = verdict((description or "")[:CLASS_DESCRIPTION_FALLBACK_CHARS])
    return bool(v)


def has_clarification(description: str) -> bool:
    t = (description or "").lower()
    return any(m in t for m in CLARIFICATION_MARKERS) or bool(_NOTE_RX.search(t))


def monday_grid(lo: float, hi: float) -> list[int]:
    """Every Monday 00:00 UTC epoch ``t`` with ``lo <= t <= hi`` (1970-01-05 was a Monday)."""
    if hi < lo:
        return []
    first_day = math.ceil(lo / DAY)
    out = []
    d = first_day + ((4 - first_day) % 7)
    while d * DAY <= hi:
        out.append(int(d * DAY))
        d += 7
    return out


def draw_origins(market_id: str, created_epoch: float, end_epoch: float, t_fetch: float, *, max_origins: int = MAX_ORIGINS,
                 seed: str = ORIGIN_SEED) -> list[int]:
    """Up to ``max_origins`` Mondays 00:00 UTC in ``[created + 7 d, end - 24 h]`` and ``<= T_fetch8 - 60 d``, uniformly
    without replacement, seeded by market id. Uses ``created_at`` and ``end_at`` only: never a price or an outcome."""
    lo = created_epoch + ORIGIN_START_OFFSET_DAYS * DAY
    hi = min(end_epoch - ORIGIN_END_OFFSET_HOURS * HOUR, t_fetch - ORIGIN_LATEST_BEFORE_FETCH_DAYS * DAY)
    grid = monday_grid(lo, hi)
    if not grid:
        return []
    rng = random.Random(f"{seed}|{market_id}")
    return sorted(rng.sample(grid, min(max_origins, len(grid))))


_TEMP_RX: re.Pattern | None = None


def _is_weather(fee_cat: str, question: str, event_title: str) -> bool:
    global _TEMP_RX
    if (fee_cat or "") == "weather":
        return True
    if _TEMP_RX is None:
        w = c4._cb2w()
        _TEMP_RX = re.compile(w.TEMP_RE, w.TEMP_RE_FLAGS)
    return bool(_TEMP_RX.match(question or "") or _TEMP_RX.match(event_title or ""))


def frame_filter_reason(r: dict, cutoff_epoch: float, created_lo: float, created_hi: float) -> str | None:
    """First declared filter that rejects a frame row (before the exclusion id / key tests), else ``None``."""
    created = _parse_ts(r.get("created_at"))
    end = r.get("end_epoch")
    try:
        end = float(end)
    except (TypeError, ValueError):
        end = float("nan")
    if created is None or math.isnan(end):
        return "no_created_or_end"
    if not (created_lo <= created < created_hi):
        return "created_outside_window"
    if end > cutoff_epoch:
        return "end_after_cutoff"
    if _is_weather(r.get("fee_category", ""), r.get("question", ""), r.get("event_title", "")):
        return "weather"
    if hb.cb1_topic(r) == "crypto_updown":
        return "crypto_updown"
    if end - created < MIN_LIFE_DAYS * DAY:
        return "life_lt_14d"
    return None


def key_types_matched(r: dict, excl: dict[str, set[str]]) -> list[str]:
    out = []
    if any(e and e in excl["event"] for e in str(r.get("event_ids", "")).split(";")):
        out.append("event")
    if r.get("neg_risk_market_id") and r["neg_risk_market_id"] in excl["neg_risk_market"]:
        out.append("neg_risk_market")
    if any(s and s in excl["series"] for s in str(r.get("series_ids", "")).split(";")):
        out.append("series")
    return out


def sample_weight_of(topic: str) -> float:
    return SPORTS_WEIGHT if topic == "sports" else OTHER_WEIGHT


def usable_point(ts: list[float], vals: list[float], t: float) -> float | None:
    """The last hourly point stamped ``t' <= t - 600`` and not older than 7,200 s at ``t``."""
    i = bisect.bisect_right(ts, t - USABLE_POINT_LAG_S) - 1
    if i < 0 or t - ts[i] > MAX_POINT_AGE_S:
        return None
    return vals[i]


def qualifying_buyers(prints: list[list], t: float, c: int, truncated: bool) -> tuple[str, dict[str, tuple[float, str]]]:
    """Rule (iii) on stored prints (strictly before ``t``): a print buying side ``c`` (BUY of ``c``, or SELL of the other
    token at ``1 - price``) in ``[t - 24 h, t)`` with notional (size x price of ``c``) at least 5x the median print
    notional of the market over ``[t - 30 d, t)`` (median over >= 10 prints). Returns (status, {wallet_hash: (end_ts,
    trade_key of its latest qualifying print)}); status ``ok``, ``unavailable_truncated`` or ``unavailable_median``."""
    if truncated:
        return "unavailable_truncated", {}
    lo30 = t - PRINT_BEFORE_DAYS * DAY
    notional = []
    for ts, _side, size, price, oi, _wh, _tk in prints:
        if lo30 <= ts < t:
            notional.append(float(size) * (float(price) if int(oi) == c else 1.0 - float(price)))
    if len(notional) < LARGE_BUY_MEDIAN_MIN_PRINTS:
        return "unavailable_median", {}
    thr = LARGE_BUY_MULTIPLE * statistics.median(notional)
    lo24 = t - LARGE_BUY_WINDOW_HOURS * HOUR
    out: dict[str, tuple[float, str]] = {}
    for ts, side, size, price, oi, wh, tk in prints:
        if not (lo24 <= ts < t):
            continue
        buys_c = (side == "BUY" and int(oi) == c) or (side == "SELL" and int(oi) == 1 - c)
        if not buys_c:
            continue
        n = float(size) * (float(price) if int(oi) == c else 1.0 - float(price))
        if n >= thr and (wh not in out or ts >= out[wh][0]):
            out[wh] = (float(ts), tk)
    return "ok", out


def rules_doc(pins: tuple[dict, ...] | list[dict] | None = None) -> dict:
    """Everything the fetch or CB6-T could otherwise choose after seeing data (CREATIVE_BATCH_6.md 1.4), without its own
    hash. The functions' SOURCE is hashed, so a changed rule function invalidates the committed file."""
    pins = list(EXCLUSION_PINS if pins is None else pins)
    src = "\n".join(inspect.getsource(f) for f in RULE_FUNCS)
    w = c4._cb2w()
    return {
        "rules_version": RULES_VERSION,
        "seeds": {"sample": SEED, "origins": ORIGIN_SEED, "smoke": SMOKE_SEED, "split": SPLIT_SEED},
        "dates": {"t_seal": T_SEAL, "end_before_fetch_days": END_BEFORE_FETCH_DAYS, "end_from": END_FROM,
                  "created_from": CREATED_FROM, "created_to_inclusive": CREATED_TO,
                  "origin_latest_before_fetch_days": ORIGIN_LATEST_BEFORE_FETCH_DAYS},
        "frame": {"frame_version": hb.FRAME_VERSION, "windows_per_day": WINDOWS_PER_DAY, "window_minutes": WINDOW_MINUTES,
                  "pages_per_window": PAGES_PER_WINDOW, "walk_order": ["closed=false", "closed=true"],
                  "forward_walk": False, "capped_windows": "dropped whole and counted",
                  "min_life_days": MIN_LIFE_DAYS, "description_chars": DESCRIPTION_CHARS, "binary_only": True,
                  "exclude_weather": {"fee_category": "weather", "temp_re": w.TEMP_RE, "temp_re_flags": w.TEMP_RE_FLAGS},
                  "exclude_crypto_updown": hb.CB1_UPDOWN_RE.pattern,
                  "filter_order": ["no_created_or_end", "created_outside_window", "end_after_cutoff", "weather",
                                   "crypto_updown", "life_lt_14d", "exclusion_id", "exclusion_key"],
                  "outcome_columns_guarded": GUARDED_COLUMNS[1:], "main_columns": MAIN_COLUMNS},
        "sample": {"n_markets": N_MARKETS, "strata": ["status", "cb1_topic", "created_month"],
                   "weights": {"sports": SPORTS_WEIGHT, "other": OTHER_WEIGHT}, "allocator": "hb.allocate_weighted",
                   "order_within_stratum": "sha256(seed|market_id)", "stored": ["inclusion_prob", "sample_weight"]},
        "origins": {"grid": "Monday 00:00 UTC", "start_offset_days": ORIGIN_START_OFFSET_DAYS,
                    "end_offset_hours": ORIGIN_END_OFFSET_HOURS, "max_origins": MAX_ORIGINS,
                    "draw": "random.Random(seed|market_id).sample(sorted grid, k)"},
        "fetch": {"price_fidelity_min": PRICE_FIDELITY, "price_window_days": [PRICE_BEFORE_DAYS, PRICE_AFTER_DAYS],
                  "print_window": {"before_days": PRINT_BEFORE_DAYS, "after_hours": PRINT_AFTER_HOURS,
                                   "taker_only": True, "limit": PRINT_PAGE, "max_pages": PRINT_PAGES},
                  "cap": "ts <= min(T_fetch8, T_seal)",
                  "wallet_lookup": {"scope": "origins whose usable longshot price m_c is inside longshot_band; buyers "
                                             "qualifying under rule (iii) only; one cached /activity first-trade lookup each",
                                    "raw_addresses_written": False}},
        "exclusion": {"files": pins, "key_types": list(KEY_TYPES), "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
                      "ids_per_request": GAMMA_IDS_PER_REQUEST, "retry_missing_with_closed_true": True,
                      "series_ids_from": "all events of the market"},
        "smoke": {"n": SMOKE_N, "min_pass": SMOKE_MIN_PASS, "min_fraction_of_expected_points": SMOKE_MIN_FRACTION,
                  "median_spacing_s": list(SMOKE_SPACING), "window_before_end_days": list(SMOKE_BEFORE_END_DAYS),
                  "pool": "closed markets with end_at in 2025 from the h1/h2/h3 exclusion samples",
                  "output": "counts only"},
        "features": {"class_d": list(CLASS_D_PATTERNS), "class_c": list(CLASS_C_PATTERNS),
                     "description_fallback_chars": CLASS_DESCRIPTION_FALLBACK_CHARS,
                     "clarification_markers": list(CLARIFICATION_MARKERS), "note_date_pattern": NOTE_DATE_PATTERN,
                     "drift_days": DRIFT_DAYS, "drift_min": DRIFT_MIN,
                     "large_buy": {"window_hours": LARGE_BUY_WINDOW_HOURS, "multiple": LARGE_BUY_MULTIPLE,
                                   "median_days": LARGE_BUY_MEDIAN_DAYS, "median_min_prints": LARGE_BUY_MEDIAN_MIN_PRINTS},
                     "young_wallet_days": YOUNG_WALLET_DAYS},
        "units": {"longshot_band": list(LONGSHOT_BAND), "price_bands": [list(b) for b in PRICE_BANDS],
                  "usable_point_lag_s": USABLE_POINT_LAG_S, "max_point_age_s": MAX_POINT_AGE_S,
                  "min_prints_before_origin": MIN_PRINTS_BEFORE_ORIGIN,
                  "print_lookback_days": PRINT_LOOKBACK_FOR_ELIGIBILITY_DAYS},
        "split": {"seed": SPLIT_SEED, "rule": SPLIT_RULE},
        "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
    }


def rules_file_doc(pins=None) -> dict:
    d = rules_doc(pins)
    return {**d, "rules_sha256": _sha(d)}


def write_rules(path: Path = RULES_FILE) -> Path:
    path = Path(path)
    want = rules_file_doc()
    if path.exists() and json.loads(path.read_text()) != want:
        raise Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(path: Path = RULES_FILE, *, require_committed: bool = True, pins=None) -> str:
    """Refuse (exit 2) unless the committed rules file equals the code's. Returns ``rules_sha256``."""
    path = Path(path)
    if not path.exists():
        raise Refused(f"rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise Refused(f"rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"rules file {path} unreadable") from exc
    want = rules_file_doc(pins)
    if doc != want:
        raise Refused(f"rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


def resolve_pin(pin: dict, *, history_root: Path, seals_dir: Path, seal_paths: dict[str, Path] | None = None) -> Path:
    """Location of one pinned exclusion file: sample files under ``<history_root>/<run>/``, seal copies in ``seals_dir``
    (or at the path given by ``--exclude-seal-ids``, matched by file name)."""
    if pin["kind"] == "sample":
        return Path(history_root) / pin["name"] / "sample.csv.gz"
    name = Path(pin["path"]).name
    if seal_paths and name in seal_paths:
        return seal_paths[name]
    return Path(seals_dir) / name


def verify_exclusion_files(pins, *, history_root: Path, seals_dir: Path, seal_paths: dict[str, Path] | None = None) -> dict[str, Path]:
    """Every exclusion file must exist and match its pinned sha256: a missing or changed file is a refusal, never a
    silent skip (a skipped file would let worn markets into h8)."""
    out: dict[str, Path] = {}
    for pin in pins:
        p = resolve_pin(pin, history_root=history_root, seals_dir=seals_dir, seal_paths=seal_paths)
        if not p.exists():
            raise Refused(f"exclusion file {p} ({pin['name']}) is missing; refusing")
        got = h5_seal.sha256_file(p)
        if got != pin["sha256"]:
            raise Refused(f"exclusion file {p} ({pin['name']}) sha256 {got} != pinned {pin['sha256']}; refusing")
        out[pin["name"]] = p
    return out


def exclusion_ids(files: dict[str, Path], pins) -> set[str]:
    """Market ids: ``market_id`` column of each sample file and the ``prices|trades/<id>.csv.gz`` names of each seal copy."""
    ids: set[str] = set()
    w = c4._cb2w()
    for pin in pins:
        p = files[pin["name"]]
        if pin["kind"] == "sample":
            with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    ids.add(str(row["market_id"]))
        else:
            ids |= w.seal_ids_from_copy(p)
    return ids


def require_data_dumps_room(data_dumps: Path, cap_gb: float, allowance_gb: float) -> float:
    """Headroom refusal (exit 75): size + the job's output cap must stay within ``cap_gb``."""
    used = c4._cb2w().dir_size(Path(data_dumps)) / 1024**3
    if used + allowance_gb > cap_gb:
        raise NotNow(f"data-dumps is {used:.2f} GB; + {allowance_gb:.2f} GB would pass {cap_gb} GB (headroom)")
    return used


# ---- Gamma parsing --------------------------------------------------------------------------------------------------


def key_fields(m: dict) -> dict:
    """Parse guard for key lookups: id, all event ids, ``negRiskMarketID`` and all series ids. Nothing else is kept."""
    evs = [e for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict)]
    eids, sids = [], []
    for e in evs:
        if e.get("id") is not None and str(e["id"]) not in eids:
            eids.append(str(e["id"]))
        for s in (e.get("series") if isinstance(e.get("series"), list) else []):
            if isinstance(s, dict) and s.get("id") is not None and str(s["id"]) not in sids:
                sids.append(str(s["id"]))
    return {"market_id": str(m.get("id")), "event_ids": ";".join(eids),
            "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "series_ids": ";".join(sids)}


def tail_row(m: dict) -> tuple[dict, dict] | None:
    """(main row, guarded outcome row) of one Gamma market, or ``None`` unless binary with token ids."""
    r = hb.frame_row(m, with_text=True, with_outcomes=True)
    if r is None:
        return None
    k = key_fields(m)
    main = {c: r.get(c, "") for c in MAIN_COLUMNS if c not in ("event_ids", "neg_risk_market_id", "series_ids", "description")}
    main.update(event_ids=k["event_ids"], neg_risk_market_id=k["neg_risk_market_id"], series_ids=k["series_ids"],
                description=str(m.get("description") or "")[:DESCRIPTION_CHARS])
    guarded = {c: r.get(c, "") for c in GUARDED_COLUMNS}
    return main, guarded


def lookup_keys(lim: hb.Limiter, ids: list[str], *, per_request: int = GAMMA_IDS_PER_REQUEST) -> tuple[dict[str, dict], int]:
    """Gamma lookup by market id, ``<= 50`` ids per request; ids missing from the first reply are retried once with
    ``closed=true``. Returns ({id: key fields}, ids found only by the retry). A non-200 reply raises :class:`ApiError`
    (an API failure is never read as "no metadata")."""
    found: dict[str, dict] = {}
    retried = 0

    def ask(batch: list[str], closed: bool) -> None:
        params: dict = {"id": list(batch), "limit": per_request}
        if closed:
            params["closed"] = "true"
        status, data = lim.get(hb.GAMMA_MARKETS, params)
        if status != 200 or not isinstance(data, list):
            raise ApiError(f"gamma markets lookup status {status}")
        for m in data:
            if isinstance(m, dict) and m.get("id") is not None and str(m["id"]) in batch:
                found[str(m["id"])] = key_fields(m)

    for i in range(0, len(ids), per_request):
        batch = ids[i:i + per_request]
        ask(batch, False)
        missing = [x for x in batch if x not in found]
        if missing:
            ask(missing, True)
            retried += sum(1 for x in missing if x in found)
    return found, retried


# ---- the resumable fetch session --------------------------------------------------------------------------------------


class TailRun(c4.FetchRun):
    """``cb4_data.FetchRun`` with an h8 manifest (rules hash, run location)."""

    rules_sha256 = ""

    def manifest(self, stopped: str | None, extra: dict | None = None) -> dict:
        m = {
            "provenance": hb.PROVENANCE, "evidence_role": hb.EVIDENCE_ROLE, "version": FETCH_VERSION,
            "run_id": self.run_id, "kind": self.kind,
            "purpose": "CB6-T h8_tail data (exploratory_historical); never prospective, not an edge claim",
            "git_commit": hb._git_commit(), "rules_sha256": self.rules_sha256,
            "run_location": {"host": socket.gethostname(), "platform": sys.platform, "python": platform.python_version()},
            "params": {**self.params, "cap_utc": _iso(self.cap_epoch), "max_rps": self.rps,
                       "disk_cap_bytes": self.disk_cap, "budget_min": self.budget_min},
            "started_utc": self.prior.get("started_utc", _iso(self.t_start)), "updated_utc": _iso(time.time()),
            "request_clock_now": self.prior.get("request_clock_now", _iso(self.now)),
            "requests": {"total_this_session": self.lim.requests, "retries": self.lim.retries,
                         "http_429": self.pol.n429, "yielded_to_live_s": self.lim.yielded_s,
                         "rps_halved": self.pol.halved},
            "stopped": stopped, "disk_bytes": self.budget.scan(),
            "elapsed_s_this_session": round(time.time() - self.t_start, 1), "counts": dict(self.counts),
            **(extra or {}),
        }
        m.setdefault("complete", False)
        self.budget.cap += 10**7  # manifest bookkeeping must stay writable at the cap
        self.budget.write(self.mpath, json.dumps(m, indent=1, sort_keys=True, default=float).encode())
        return m


def mark_not_run(rdir: Path, reason: str, now: float | None = None) -> dict:
    rdir = Path(rdir)
    rdir.mkdir(parents=True, exist_ok=True)
    mp = rdir / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {"run_id": rdir.name}
    t = _iso(time.time() if now is None else now)
    man.update(stopped=NOT_RUN_TOKEN, complete=False, status=NOT_RUN_TOKEN, not_run_reason=reason, not_run_utc=t)
    mp.write_text(json.dumps(man, indent=1, sort_keys=True, default=float))
    (rdir / NOT_RUN_FILE).write_text(json.dumps(
        {"run_id": rdir.name, "status": NOT_RUN_TOKEN, "reason": reason, "utc": t,
         "rule": "CREATIVE_BATCH_6.md 1.2: incomplete at T_seal -> not run, recorded; no seal, no analysis, no refetch; "
                 "CB6-T tests are recorded 'not run (deadline)' with p = 1 and counted"}, indent=1, sort_keys=True))
    return man


def _guard_start(root: Path, run_id: str, wall_clock: Callable[[], float], t_seal_epoch: float) -> dict | None:
    rdir = Path(root) / run_id
    if (rdir / h5_seal.SEAL_NAME).exists():
        raise Refused(f"{run_id} is sealed; the fetch never touches a sealed run")
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if (rdir / NOT_RUN_FILE).exists() or prior.get("stopped") == NOT_RUN_TOKEN:
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    if prior.get("stopped") == UNVERIFIED_TOKEN or (rdir / UNVERIFIED_FILE).exists():
        return {"stopped": UNVERIFIED_TOKEN, "status": UNVERIFIED_TOKEN, "complete": False}
    if prior.get("complete") is True and prior.get("stopped") is None:
        return {"stopped": None, "status": COMPLETE_TOKEN, "complete": True, "counts": prior.get("counts")}
    if wall_clock() >= t_seal_epoch:
        mark_not_run(rdir, "incomplete at T_seal (no new chunk at or after 2026-10-22T00:00Z)")
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    return None


# ---- stage 1: exclusion keys --------------------------------------------------------------------------------------------


def exclusion_stage(fr: TailRun, ids: set[str], should_stop: Callable[[], bool] | None = None) -> tuple[dict | None, str | None]:
    """Gamma lookup of every exclusion id (resumable by batch) -> ``exclusion_keys.csv.gz`` + ``exclusion_report.json``.
    Returns (report, stop reason); report is ``None`` while unfinished."""
    rdir = fr.rdir
    rep_path, keys_path = rdir / "exclusion_report.json", rdir / "exclusion_keys.csv.gz"
    if rep_path.exists():
        return json.loads(rep_path.read_text()), None
    part = rdir / "exclusion_keys_partial.jsonl"
    todo = sorted(ids)
    done: dict[int, dict] = {}
    if part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["batch"]] = rec
    per = GAMMA_IDS_PER_REQUEST
    nb = math.ceil(len(todo) / per)
    for b in range(nb):
        if b in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return None, why
        batch = todo[b * per:(b + 1) * per]
        found, retried = lookup_keys(fr.lim, batch, per_request=per)
        rec = {"batch": b, "ids": len(batch), "retried_found": retried, "found": [found[x] for x in batch if x in found]}
        with part.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        done[b] = rec
    rows: dict[str, dict] = {}
    retried = 0
    for rec in done.values():
        retried += rec["retried_found"]
        for k in rec["found"]:
            rows[k["market_id"]] = k
    out = [[x, int(x in rows), rows[x]["event_ids"] if x in rows else "", rows[x]["neg_risk_market_id"] if x in rows else "",
            rows[x]["series_ids"] if x in rows else ""] for x in todo]
    fr.budget.write_gz_csv(keys_path, KEY_COLUMNS, out)
    n_missing = len(todo) - len(rows)
    share = n_missing / len(todo) if todo else 1.0
    sets = {"event": {e for r in rows.values() for e in r["event_ids"].split(";") if e},
            "neg_risk_market": {r["neg_risk_market_id"] for r in rows.values() if r["neg_risk_market_id"]},
            "series": {s for r in rows.values() for s in r["series_ids"].split(";") if s}}
    rep = {"n_ids": len(todo), "n_found": len(rows), "n_missing": n_missing, "missing_share": share,
           "found_only_with_closed_true": retried, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED_TOKEN if share > MAX_UNVERIFIED_KEY_SHARE else "verified",
           "keys": {k: len(v) for k, v in sets.items()}, "keys_sha256": h5_seal.sha256_file(keys_path)}
    fr.budget.write(rep_path, json.dumps(rep, indent=1, sort_keys=True).encode())  # last: marks the stage
    part.unlink(missing_ok=True)
    return rep, None


def load_key_sets(path: Path) -> dict[str, set[str]]:
    sets: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if str(row["found"]) != "1":
                continue
            sets["event"].update(e for e in row["event_ids"].split(";") if e)
            if row["neg_risk_market_id"]:
                sets["neg_risk_market"].add(row["neg_risk_market_id"])
            sets["series"].update(s for s in row["series_ids"].split(";") if s)
    return sets


# ---- stage 2: frame walk (streaming) -------------------------------------------------------------------------------------


def frame_days(end_from: float, cutoff: float) -> list[date]:
    d0 = datetime.fromtimestamp(end_from, UTC).date()
    d1 = datetime.fromtimestamp(cutoff, UTC).date()
    return [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]


def walk_tail_frame(lim: hb.Limiter, days: list[date], seed: str, *, rdir: Path, cutoff_epoch: float,
                    should_stop: Callable[[], bool] | None = None, windows_per_day: int = WINDOWS_PER_DAY,
                    window_minutes: int = WINDOW_MINUTES, pages_per_window: int = PAGES_PER_WINDOW) -> str | None:
    """Per day: ``windows_per_day`` seeded ``window_minutes`` windows on ``end_date`` (only windows ending at or before
    ``cutoff_epoch``: no forward walk), each walked ``closed=false`` then ``closed=true``; a window still capped after
    ``pages_per_window`` pages is dropped whole and counted. One gzip member per day in ``frame_partial.jsonl.gz``
    (rows, outcomes, counts): nothing is kept in memory. A window with a failed request keeps the day open (retried by
    the next chunk, at most ``MAX_DAY_ATTEMPTS`` times). Returns a stop reason or ``None`` when every day is done."""
    pp, pf = Path(rdir) / "frame_partial.jsonl.gz", Path(rdir) / "frame_fail.jsonl"
    done_days: set[str] = set()
    seen: set[str] = set()
    for rec in iter_partial(pp):
        done_days.add(rec["day"])
        seen.update(r["market_id"] for r in rec["rows"])
    fails: dict[str, int] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                k = json.loads(line)["day"]
                fails[k] = fails.get(k, 0) + 1
    slots_per_day = 1440 // window_minutes
    f = "%Y-%m-%dT%H:%M:%SZ"
    for day in days:
        dkey = f"{day:%Y-%m-%d}"
        if dkey in done_days:
            continue
        if should_stop is not None and should_stop():
            return "frame_paused"
        d0 = datetime(day.year, day.month, day.day, tzinfo=UTC)
        valid = [k for k in range(slots_per_day) if (d0 + timedelta(minutes=(k + 1) * window_minutes)).timestamp() <= cutoff_epoch]
        rng = random.Random(f"{seed}|{dkey}")
        picks = sorted(rng.sample(valid, min(windows_per_day, len(valid)))) if valid else []
        rows: list[dict] = []
        outs: list[dict] = []
        win = {"closed": 0, "active": 0}
        dropped = {"closed": 0, "active": 0}
        dropped_rows = raw = invalid = dups = failed_windows = 0
        day_seen: set[str] = set()
        for closed in (False, True):  # closed=false first: a market closing between the walks is seen by the second
            kind = "closed" if closed else "active"
            for k in picks:
                a = d0 + timedelta(minutes=k * window_minutes)
                b = a + timedelta(minutes=window_minutes)
                p = {"order": "id", "ascending": "true", "closed": "true" if closed else "false",
                     "end_date_min": a.strftime(f), "end_date_max": b.strftime(f)}
                batch, capped, failed = c4._paged_strict(lim, p, pages_per_window * hb.GAMMA_PAGE)
                if failed:
                    failed_windows += 1
                    continue
                win[kind] += 1
                if capped:
                    dropped[kind] += 1
                    dropped_rows += len(batch)
                    continue
                for m in batch:
                    raw += 1
                    pr = tail_row(m)
                    if pr is None:
                        invalid += 1
                        continue
                    mid = pr[0]["market_id"]
                    if mid in seen or mid in day_seen:
                        dups += 1
                        continue
                    day_seen.add(mid)
                    rows.append(pr[0])
                    outs.append(pr[1])
        if failed_windows and fails.get(dkey, 0) + 1 < MAX_DAY_ATTEMPTS:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": dkey, "failed_windows": failed_windows}) + "\n")
            return f"walk_failed_window: {dkey}"
        with pp.open("ab") as fh:
            fh.write(_gz_jsonl_member({"day": dkey, "rows": rows, "outs": outs, "windows": win, "dropped": dropped,
                                       "dropped_rows": dropped_rows, "raw": raw, "invalid": invalid, "dups": dups,
                                       "failed_windows": failed_windows}))
        seen.update(day_seen)
    return None


def draw_tail_sample(strata: dict[str, list[str]], n_total: int, seed: str) -> tuple[dict[str, dict], dict]:
    """Seeded sample over ``status | cb1_topic | creation month`` strata, sports weight 0.5 and every other topic 1.0
    (allocation proportional to weight x stratum size, ``hb.allocate_weighted``); inside a stratum the order is
    sha256(seed|market_id). Reads no price, volume or outcome. ``{market_id: row of sampling facts}``."""
    sizes = {k: len(v) for k, v in strata.items()}
    w = {k: sample_weight_of(k.split("|")[1]) for k in strata}
    alloc = hb.allocate_weighted(sizes, w, n_total)
    chosen: dict[str, dict] = {}
    for k in sorted(strata):
        if not alloc[k]:
            continue
        for mid in sorted(strata[k], key=lambda x: hb._rank(seed, x))[: alloc[k]]:
            chosen[mid] = {"stratum": k, "stratum_size": sizes[k], "stratum_alloc": alloc[k],
                           "inclusion_prob": alloc[k] / sizes[k], "sample_weight": sizes[k] / alloc[k]}
    return chosen, {"pool": sum(sizes.values()), "strata": len(sizes), "n": len(chosen), "seed": seed,
                    "taken_all": sum(sizes.values()) <= n_total}


def _outcome_after_cap(o: dict, t_fetch: float) -> bool:
    """True when the market's close_epoch is after the run clock ``T_fetch8`` (an outcome not yet knowable at the fixed
    information end, e.g. a market walked in a later chunk). Unparseable close_epoch is not censored here."""
    try:
        return float(o.get("close_epoch")) > float(t_fetch)
    except (TypeError, ValueError):
        return False


def build_frame_outputs(fr: TailRun, *, cutoff_epoch: float, excl_ids: set[str], excl_keys: dict[str, set[str]],
                        n_markets: int, seed: str, t_fetch: float, max_origins: int = MAX_ORIGINS,
                        created_from: str = CREATED_FROM, created_to: str = CREATED_TO) -> dict:
    """Stream ``frame_partial.jsonl.gz`` twice: pass 1 writes ``frame.csv.gz`` (every walked row) and applies the filters,
    the exclusion id test and the key-based drop (counted by reason / key type) keeping only ids per stratum; the sample
    is drawn; pass 2 gathers the sampled rows. ``origins.csv.gz`` is written BEFORE ``sample.csv.gz`` (and long before any
    price request); outcome columns go only to ``outcomes_guarded.csv.gz``. ``frame_report.json`` is written last."""
    rdir = fr.rdir
    pp = rdir / "frame_partial.jsonl.gz"
    lo = c4._ep(created_from)
    hi = c4._ep(created_to) + DAY
    counts = {"frame_rows": 0, "filter_dropped": {}, "exclusion_id_dropped": 0, "exclusion_key_dropped": 0,
              "kept_by_key_stage": 0}
    key_drops = {"by_type_any_match": dict.fromkeys(KEY_TYPES, 0), "by_type_combo": {}, "rows": 0}
    strata: dict[str, list[str]] = {}
    walk = {"windows": {"closed": 0, "active": 0}, "windows_dropped_capped": {"closed": 0, "active": 0},
            "windows_failed": 0, "rows_in_dropped_windows": 0, "dropped_capped_by_day": {}, "days": 0, "raw": 0,
            "non_binary_or_invalid": 0, "duplicates": 0, "days_with_failed_windows": []}

    def rows_pass1() -> Iterator[list]:
        for rec in iter_partial(pp):
            walk["days"] += 1
            for k in ("closed", "active"):
                walk["windows"][k] += rec["windows"][k]
                walk["windows_dropped_capped"][k] += rec["dropped"][k]
            walk["rows_in_dropped_windows"] += rec["dropped_rows"]
            if any(rec["dropped"].values()):
                walk["dropped_capped_by_day"][rec["day"]] = rec["dropped"]
            if rec.get("failed_windows"):
                walk["windows_failed"] += rec["failed_windows"]
                walk["days_with_failed_windows"].append(rec["day"])
            walk["raw"] += rec["raw"]
            walk["non_binary_or_invalid"] += rec["invalid"]
            walk["duplicates"] += rec["dups"]
            for r in rec["rows"]:
                counts["frame_rows"] += 1
                yield [r.get(c, "") for c in MAIN_COLUMNS]
                why = frame_filter_reason(r, cutoff_epoch, lo, hi)
                if why:
                    counts["filter_dropped"][why] = counts["filter_dropped"].get(why, 0) + 1
                    continue
                if r["market_id"] in excl_ids:
                    counts["exclusion_id_dropped"] += 1
                    continue
                kt = key_types_matched(r, excl_keys)
                if kt:
                    counts["exclusion_key_dropped"] += 1
                    key_drops["rows"] += 1
                    for t in kt:
                        key_drops["by_type_any_match"][t] += 1
                    combo = "+".join(kt)
                    key_drops["by_type_combo"][combo] = key_drops["by_type_combo"].get(combo, 0) + 1
                    continue
                counts["kept_by_key_stage"] += 1
                month = str(r.get("created_at") or "")[:7] or "unknown"
                strata.setdefault("|".join([str(r["status"]), hb.cb1_topic(r), month]), []).append(r["market_id"])

    fr.budget.write_gz_csv(rdir / "frame.csv.gz", MAIN_COLUMNS, rows_pass1())
    chosen, srep = draw_tail_sample(strata, n_markets, seed)
    strata.clear()
    picked: dict[str, tuple[dict, dict]] = {}
    for rec in iter_partial(pp):
        outs = {o["market_id"]: o for o in rec["outs"]}
        for r in rec["rows"]:
            if r["market_id"] in chosen:
                picked[r["market_id"]] = (r, outs[r["market_id"]])
    ids = sorted(picked)
    origins: list[list] = []
    no_origin = 0
    for mid in ids:
        r = picked[mid][0]
        os_ = draw_origins(mid, _parse_ts(r["created_at"]) or 0.0, float(r["end_epoch"]), t_fetch, max_origins=max_origins)
        if not os_:
            no_origin += 1
        origins.extend([mid, t, _iso(t), k] for k, t in enumerate(os_))
    fr.budget.write_gz_csv(rdir / "origins.csv.gz", ORIGIN_COLUMNS, origins)  # before sample.csv.gz and any price request
    censored_post_cap = 0

    def outcome_rows() -> Iterator[list]:
        nonlocal censored_post_cap
        for m in ids:
            o = picked[m][1]
            if _outcome_after_cap(o, t_fetch):  # resolved after the fixed run clock: stored as censored, no outcome
                censored_post_cap += 1
                yield [m] + [""] * (len(GUARDED_COLUMNS) - 1)
            else:
                yield [o.get(c, "") for c in GUARDED_COLUMNS]

    fr.budget.write_gz_csv(rdir / OUTCOME_FILE, GUARDED_COLUMNS, outcome_rows())
    fr.budget.write_gz_csv(rdir / "sample.csv.gz", [*MAIN_COLUMNS, *SAMPLE_EXTRA],
                           ([picked[m][0].get(c, "") for c in MAIN_COLUMNS] + [chosen[m][c] for c in SAMPLE_EXTRA] for m in ids))
    kd = {"exclusion_key_types": list(KEY_TYPES), **key_drops}
    fr.budget.write(rdir / "key_drops.json", json.dumps(kd, indent=1, sort_keys=True).encode())
    report = {"frame_version": hb.FRAME_VERSION, "t_fetch8": _iso(t_fetch), "end_cutoff": _iso(cutoff_epoch),
              "windows_per_day": WINDOWS_PER_DAY, "window_minutes": WINDOW_MINUTES, "pages_per_window": PAGES_PER_WINDOW,
              **walk, **counts, "sample": srep, "n_sample": len(ids), "n_sample_without_origin": no_origin,
              "n_origins": len(origins), "key_drops": kd, "outcomes_censored_post_cap": censored_post_cap}
    fr.budget.write(rdir / "frame_report.json", json.dumps(report, indent=1, sort_keys=True, default=float).encode())
    for tmp in (pp, rdir / "frame_fail.jsonl"):
        tmp.unlink(missing_ok=True)
    return report


# ---- stage 3: per-market prices, prints, wallets ------------------------------------------------------------------------------


def fetch_prices60(lim: hb.Limiter, token: str, a: int, b: int) -> list[tuple[int, float]]:
    """Hourly (fidelity 60) series over ``[a, b]`` (one request when ``b - a`` fits the 14-day window limit). A non-200
    reply raises :class:`ApiError`: a failed request is a failed item, never an empty price file."""
    pts: dict[int, float] = {}
    step = hb.WINDOW_DAYS * 86400
    lo = a
    while lo < b:
        hi = min(lo + step, b)
        status, data = lim.get(hb.CLOB_PRICES, {"market": token, "startTs": lo, "endTs": hi, "fidelity": PRICE_FIDELITY})
        if status != 200 or not isinstance(data, dict):
            raise ApiError(f"prices-history status {status}")
        for h in data.get("history") or []:
            pts[int(h["t"])] = float(h["p"])
        lo = hi
    return sorted(pts.items())


def fetch_prints(lim: hb.Limiter, condition_id: str, key: bytes, start: int, end: int, *, max_pages: int = PRINT_PAGES,
                 cap_epoch: float | None = None, addr_from: float | None = None, addr_to: float | None = None
                 ) -> tuple[list[list], dict, dict[str, str]]:
    """Windowed taker prints ``/trades?market=&start=&end=&takerOnly=true`` newest first, ``limit`` 1,000, ``<= max_pages``
    pages. Wallets are keyed-hashed immediately; raw addresses of prints with ``addr_from <= ts < addr_to`` are returned
    in memory only (``trade_key -> address``) for the first-trade lookups and are never written. Rows after ``cap_epoch``
    are dropped and counted. ``truncated`` means the last allowed page was still full."""
    rows: dict[str, list] = {}
    addr: dict[str, str] = {}
    dropped, pages, truncated = 0, 0, False
    for page in range(max_pages):
        status, data = lim.get(hb.DATA_TRADES, {"market": condition_id, "start": int(start), "end": int(end),
                                                "takerOnly": "true", "limit": PRINT_PAGE, "offset": page * PRINT_PAGE})
        pages += 1
        if status != 200 or not isinstance(data, list):
            raise ApiError(f"trades status {status} at page {page}")
        for t in data:
            try:
                ts = int(t["timestamp"])
                if cap_epoch is not None and ts > cap_epoch:
                    dropped += 1
                    continue
                tk = hb.trade_key(t)
                rows[tk] = [ts, str(t["side"]), float(t["size"]), float(t["price"]), int(t["outcomeIndex"]),
                            hb.wallet_hash(key, str(t.get("proxyWallet", ""))), tk]
                if addr_from is not None and addr_to is not None and addr_from <= ts < addr_to and t.get("proxyWallet"):
                    addr[tk] = str(t["proxyWallet"])
            except (KeyError, TypeError, ValueError):
                continue
        if len(data) < PRINT_PAGE:
            break
        if page == max_pages - 1:
            truncated = True
    out = sorted(rows.values(), key=lambda x: (x[0], x[6]))
    return out, {"pages": pages, "n": len(out), "truncated": truncated, "oldest_ts": out[0][0] if out else None,
                 "dropped_post_cap": dropped}, addr


def fetch_tail_market(lim: hb.Limiter, r: dict, origins: list[int], key: bytes, rdir: Path, budget: hb.DiskBudget, *,
                      cap_epoch: float) -> dict:
    """One sampled market: per origin the fidelity-60 YES-token series over ``[t - 8 d, t + 2 d]`` and the windowed taker
    prints over ``[t - 30 d, t + 6 h]``; rule (iii) on the stored prints and one cached ``/activity`` first-trade lookup
    per qualifying buyer (origins whose usable longshot price lies in the longshot band only). Files are written last."""
    mid = r["market_id"]
    price_rows: list[list] = []
    union: dict[str, list] = {}
    windows: list[dict] = []
    lookups = {"requested_wallets": 0, "ok": 0, "err": 0}
    for t in origins:
        a = int(t - PRICE_BEFORE_DAYS * DAY)
        b = int(min(t + PRICE_AFTER_DAYS * DAY, cap_epoch))
        pts_all = fetch_prices60(lim, r["token0"], a, b) if b > a else []
        pts = [(ts, p) for ts, p in pts_all if ts <= cap_epoch]
        ps, pe = int(t - PRINT_BEFORE_DAYS * DAY), int(min(t + PRINT_AFTER_HOURS * HOUR, cap_epoch))
        prints, info, addr = fetch_prints(lim, r["condition_id"], key, ps, pe, cap_epoch=cap_epoch,
                                          addr_from=t - LARGE_BUY_WINDOW_HOURS * HOUR, addr_to=t)
        price_rows.extend([t, ts, p] for ts, p in pts)
        for row in prints:
            union[row[6]] = row
        p0 = usable_point([x[0] for x in pts], [x[1] for x in pts], t)
        wstatus, nq = "no_usable_point", 0
        if p0 is not None:
            c = 0 if p0 <= 0.5 else 1
            m_c = p0 if c == 0 else 1.0 - p0
            if LONGSHOT_BAND[0] <= m_c <= LONGSHOT_BAND[1]:
                wstatus, quals = qualifying_buyers(prints, t, c, bool(info["truncated"]))
                nq = len(quals)
                if quals:
                    wallets = {}
                    by_hash_addr = {row[5]: addr.get(row[6]) for row in prints if row[6] in addr}
                    for wh, (end_ts, tk) in quals.items():
                        a_ = addr.get(tk) or by_hash_addr.get(wh)
                        if a_:
                            wallets[wh] = (a_, int(end_ts))
                    lookups["requested_wallets"] += len(wallets)
                    res = event_study.first_trade_lookups(lim, wallets, Path(rdir) / "wallet_first.jsonl")
                    lookups["ok"] += res["lookups_ok"]
                    lookups["err"] += res["lookups_err"]
            else:
                wstatus = "outside_longshot_band"
        windows.append({"origin_ts": t, "price_points": len(pts), "price_dropped_post_cap": len(pts_all) - len(pts),
                        "print_rows": info["n"], "print_pages": info["pages"], "window_truncated": int(info["truncated"]),
                        "oldest_ts": info["oldest_ts"], "dropped_post_cap": info["dropped_post_cap"], "start": ps, "end": pe,
                        "usable_point": p0 if p0 is not None else "", "qualifying_wallets": nq, "wallet_status": wstatus})
    budget.write_gz_csv(Path(rdir) / "prices" / f"{mid}.csv.gz", PRICE_COLUMNS, price_rows)
    budget.write_gz_csv(Path(rdir) / "trades" / f"{mid}.csv.gz", TRADE_COLUMNS, sorted(union.values(), key=lambda x: (x[0], x[6])))
    return {"market_id": mid, "status": "done", "origins": windows, "lookups": lookups,
            "price_points": sum(w["price_points"] for w in windows), "trade_rows": len(union)}


def _tally(counts: dict[str, int]) -> Callable[[dict], None]:
    def tally(rec: dict) -> None:
        if rec["status"] != "done":
            return
        counts["items_done"] = counts.get("items_done", 0) + 1
        counts["origins_fetched"] = counts.get("origins_fetched", 0) + len(rec["origins"])
        counts["price_rows"] = counts.get("price_rows", 0) + rec["price_points"]
        counts["trade_rows"] = counts.get("trade_rows", 0) + rec["trade_rows"]
        for w in rec["origins"]:
            counts["price_rows_dropped_post_cap"] = counts.get("price_rows_dropped_post_cap", 0) + w["price_dropped_post_cap"]
            counts["print_rows_dropped_post_cap"] = counts.get("print_rows_dropped_post_cap", 0) + (w["dropped_post_cap"] or 0)
            counts["print_windows_truncated"] = counts.get("print_windows_truncated", 0) + w["window_truncated"]
        counts["wallet_lookups_requested"] = counts.get("wallet_lookups_requested", 0) + rec["lookups"]["requested_wallets"]
        counts["wallet_lookups_err"] = counts.get("wallet_lookups_err", 0) + rec["lookups"]["err"]

    return tally


def _read_csv_gz(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def finalize_tables(fr: TailRun) -> dict:
    """At completion: ``origin_windows.csv.gz`` (per-origin fetch facts from the done progress records) and
    ``wallet_first.csv.gz`` (hashes and first-trade times, from the lookup cache); partial files are removed."""
    rdir = fr.rdir
    done = fr.read_progress("market_id")
    rows = []
    for mid in sorted(done):
        rec = done[mid]
        if rec["status"] == "done":
            rows.extend([mid, *[w[c] for c in WINDOW_COLUMNS[1:]]] for w in rec["origins"])
    fr.budget.write_gz_csv(rdir / "origin_windows.csv.gz", WINDOW_COLUMNS, rows)
    cache = event_study.read_first_trade_cache(rdir / "wallet_first.jsonl")
    fr.budget.write_gz_csv(rdir / "wallet_first.csv.gz", ["wallet_hash", "first_trade_ts", "end_ts"],
                           ([h, "" if c.get("first_trade_ts") is None else c["first_trade_ts"], c["end_ts"]] for h, c in sorted(cache.items())))
    (rdir / "wallet_first.jsonl").unlink(missing_ok=True)
    return {"origin_window_rows": len(rows), "wallet_first_rows": len(cache)}


def file_hashes(rdir: Path, exclude: tuple[str, ...] = ("manifest.json",)) -> dict[str, str]:
    return {k: v for k, v in h5_seal.list_files(rdir).items() if k not in exclude}


def tail_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, history_root: Path | None = None, seals_dir: Path | None = None,
    seal_paths: dict[str, Path] | None = None, rules_path: Path = RULES_FILE, smoke_path: Path = SMOKE_DEFAULT,
    pins=None, seed: str = SEED, n_markets: int = N_MARKETS, created_from: str = CREATED_FROM, created_to: str = CREATED_TO,
    end_from: str = END_FROM, end_before_fetch_days: int = END_BEFORE_FETCH_DAYS, windows_per_day: int = WINDOWS_PER_DAY,
    window_minutes: int = WINDOW_MINUTES, pages_per_window: int = PAGES_PER_WINDOW, max_origins: int = MAX_ORIGINS,
    cap_at: str = T_SEAL, rps: float = 4.0, disk_cap: int = int(OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
    key: bytes | None = None, now: float | None = None, sleep: Callable[[float], None] = time.sleep,
    live_check: Callable[[], bool] | None = hb.live_pass_or_lock, should_stop: Callable[[], bool] | None = None,
    wall_clock: Callable[[], float] = time.time, t_seal_epoch: float = T_SEAL_EPOCH, snapshot_root: Path | None = None,
    health_every_s: float = 600.0, health_check: Callable[[float], tuple[bool, str]] | None = None,
    require_committed: bool = True, require_smoke: bool = True, data_dumps: Path | None = None,
    data_dumps_cap_gb: float = DATA_DUMPS_FETCH_CAP_GB, stage: str = "all",
) -> dict:
    """One resumable chunk of the ``h8_tail`` fetch. Order (each stage idempotent, finished stages are skipped):
    refusals (rules hash, every exclusion file and its pin, smoke PASS, run id, root) -> terminal / deadline guard ->
    headroom (exit 75) -> exclusion keys (``> 2%`` ids without metadata: ``disjointness_unverified``, stop) -> frame walk
    -> filters, key drop, sample, origins, guarded outcomes -> per-market prices / prints / wallets -> tables and manifest.
    A chunk starts nothing at or after ``t_seal_epoch``; an incomplete run at T_seal is ``not_run_deadline``.
    ``stage='keys'`` stops after the exclusion keys."""
    root = Path(root)
    refuse_run_id(run_id)
    refuse_path(root)
    history_root = Path(history_root or root)
    seals_dir = Path(seals_dir or SEALS_DIR)
    pins = list(EXCLUSION_PINS if pins is None else pins)
    rules_sha = verify_rules(rules_path, require_committed=require_committed, pins=pins)
    files = verify_exclusion_files(pins, history_root=history_root, seals_dir=seals_dir, seal_paths=seal_paths)
    if require_smoke:
        smoke_ok(smoke_path, rules_sha)
    early = _guard_start(root, run_id, wall_clock, t_seal_epoch)
    if early is not None:
        return early
    if data_dumps is not None:
        require_data_dumps_room(Path(data_dumps), data_dumps_cap_gb, disk_cap / 1024**3)
    ids = exclusion_ids(files, pins)
    fr = TailRun(root, run_id, transport, kind="tail", params={
        "seed": seed, "n_markets": n_markets, "created_from": created_from, "created_to": created_to, "end_from": end_from,
        "end_before_fetch_days": end_before_fetch_days, "windows_per_day": windows_per_day, "window_minutes": window_minutes,
        "pages_per_window": pages_per_window, "max_origins": max_origins, "price_fidelity": PRICE_FIDELITY,
        "print_pages": PRINT_PAGES, "stage": stage}, rps=rps, disk_cap=disk_cap, budget_min=budget_min, now=now, sleep=sleep,
        live_check=live_check, wall_clock=wall_clock, t_seal_epoch=t_seal_epoch, snapshot_root=snapshot_root,
        health_every_s=health_every_s, health_check=health_check, cap_at=cap_at, key=key)
    fr.rules_sha256 = rules_sha
    t_fetch = fr.now
    cutoff = t_fetch - end_before_fetch_days * DAY
    rdir = fr.rdir

    def transient(why: str) -> dict:
        if why == "t_seal_passed":
            mark_not_run(rdir, "chunk reached T_seal before completion")
            return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
        return fr.manifest(why, {"transient": why.startswith("paused") or why.startswith("walk_failed")})

    why = fr.unhealthy()
    if why:
        return fr.manifest(why, {"transient": True})
    try:
        rep, stopped = exclusion_stage(fr, ids, should_stop)
        if stopped:
            return transient(stopped)
        assert rep is not None
        if rep["disjointness"] == UNVERIFIED_TOKEN:
            (rdir / UNVERIFIED_FILE).write_text(json.dumps({
                "run_id": run_id, "status": UNVERIFIED_TOKEN, "exclusion_report": rep,
                "rule": "CREATIVE_BATCH_6.md 1.3: more than 2% of exclusion ids without Gamma metadata -> disjointness "
                        "unverified; CB6-T T1/T2 not testable (p = 1, counted); no sample, no prices"}, indent=1, sort_keys=True))
            m = fr.manifest(UNVERIFIED_TOKEN, {"exclusion_report": rep, "status": UNVERIFIED_TOKEN})
            m["status"] = UNVERIFIED_TOKEN
            return m
        if stage == "keys":
            m = fr.manifest("keys_complete", {"exclusion_report": rep})
            m["status"] = "exclusion_keys_complete"
            return m
        if not (rdir / "frame_report.json").exists():
            why_stop: list[str] = []

            def walk_stop() -> bool:
                r = fr.stop_reason(should_stop)
                if r:
                    why_stop.append(r)
                return bool(r)

            stopped = walk_tail_frame(fr.lim, frame_days(c4._ep(end_from), cutoff), seed, rdir=rdir, cutoff_epoch=cutoff,
                                      should_stop=walk_stop, windows_per_day=windows_per_day, window_minutes=window_minutes,
                                      pages_per_window=pages_per_window)
            if stopped:
                return transient(why_stop[-1] if why_stop else stopped)
            build_frame_outputs(fr, cutoff_epoch=cutoff, excl_ids=ids, excl_keys=load_key_sets(rdir / "exclusion_keys.csv.gz"),
                                n_markets=n_markets, seed=seed, t_fetch=t_fetch, max_origins=max_origins,
                                created_from=created_from, created_to=created_to)
    except Refused:
        raise
    except OSError as exc:
        m = fr.manifest(f"disk_budget: {exc}"[:200], {"status": DISK_BUDGET_TOKEN})
        m["status"] = DISK_BUDGET_TOKEN
        return m
    except RuntimeError as exc:  # persistent API failure in a lookup or walk: transient, partial results are kept
        return fr.manifest(f"stage_failed: {exc}"[:200], {"transient": True})
    frame_rep = json.loads((rdir / "frame_report.json").read_text())
    origins: dict[str, list[int]] = {}
    for o in _read_csv_gz(rdir / "origins.csv.gz"):
        origins.setdefault(o["market_id"], []).append(int(o["origin_ts"]))
    sample = {r["market_id"]: {"market_id": r["market_id"], "token0": r["token0"], "condition_id": r["condition_id"]}
              for r in _read_csv_gz(rdir / "sample.csv.gz") if r["market_id"] in origins}
    items = sorted(sample.values(), key=lambda r: hb._rank(seed, r["market_id"]))
    extra = {"frame_report": frame_rep, "exclusion_report": json.loads((rdir / "exclusion_report.json").read_text()),
             "n_sample": frame_rep["n_sample"], "n_items": len(items)}
    stopped, pending = c4._fetch_items(
        fr, items, "market_id", lambda r: fetch_tail_market(fr.lim, r, origins[r["market_id"]], fr.key, rdir, fr.budget,
                                                             cap_epoch=fr.cap_epoch), _tally(fr.counts), should_stop, extra)
    if stopped is None and pending == 0:
        extra.update(finalize_tables(fr))
        extra["complete"] = True
        extra["status"] = COMPLETE_TOKEN
        extra["file_sha256"] = file_hashes(rdir)
        m = fr.manifest(None, extra)
        m["status"] = COMPLETE_TOKEN
        return m
    if stopped == "t_seal_passed":
        return transient("t_seal_passed")
    if stopped and stopped.startswith("disk_budget"):  # a full output cap is a declared end state, not a transient pause
        m = fr.manifest(stopped[:200], {**extra, "status": DISK_BUDGET_TOKEN})
        m["status"] = DISK_BUDGET_TOKEN
        return m
    m = fr.manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})
    m["status"] = "in_progress"
    return m


# ---- smoke test -----------------------------------------------------------------------------------------------------------


def smoke_candidates(files: dict[str, Path], pins) -> list[dict]:
    out = []
    for pin in pins:
        if pin["kind"] != "sample":
            continue
        for row in _read_csv_gz(files[pin["name"]]):
            try:
                end = float(row["end_epoch"])
            except (KeyError, TypeError, ValueError):
                continue
            if str(row.get("closed")) in ("1", "True", "true") and c4._ep("2025-01-01") <= end < c4._ep("2026-01-01"):
                out.append({"market_id": str(row["market_id"]), "token0": row["token0"], "end_epoch": end})
    return sorted({r["market_id"]: r for r in out}.values(), key=lambda r: hb._rank(SMOKE_SEED, r["market_id"]))


def run_smoke(lim: hb.Limiter, files: dict[str, Path], pins, rules_sha: str) -> dict:
    """20 seeded worn 2025 markets, one fidelity-60 request each over ``[end - 12 d, end - 2 d]``. PASS iff at least 18
    return at least 80% of the expected hourly points with median spacing 3,600 +/- 300 s. Counts only: no id, price or
    timestamp is kept."""
    cands = smoke_candidates(files, pins)[:SMOKE_N]
    n_ok_points = n_ok_spacing = n_pass = n_failed_requests = 0
    fractions = []
    for r in cands:
        a = int(r["end_epoch"] - SMOKE_BEFORE_END_DAYS[0] * DAY)
        b = int(r["end_epoch"] - SMOKE_BEFORE_END_DAYS[1] * DAY)
        expected = (b - a) // 3600
        try:
            pts = [t for t, _ in fetch_prices60(lim, r["token0"], a, b)]
        except (ApiError, RuntimeError):
            n_failed_requests += 1
            fractions.append(0.0)
            continue
        frac = len(pts) / expected if expected else 0.0
        fractions.append(frac)
        ok_pts = frac >= SMOKE_MIN_FRACTION
        gaps = [y - x for x, y in zip(pts, pts[1:], strict=False)]
        ok_sp = bool(gaps) and abs(statistics.median(gaps) - SMOKE_SPACING[0]) <= SMOKE_SPACING[1]
        n_ok_points += int(ok_pts)
        n_ok_spacing += int(ok_sp)
        n_pass += int(ok_pts and ok_sp)
    verdict = len(cands) == SMOKE_N and n_pass >= SMOKE_MIN_PASS
    bins = {"lt_0.5": sum(f < 0.5 for f in fractions), "0.5_to_0.8": sum(0.5 <= f < 0.8 for f in fractions),
            "0.8_to_1.1": sum(0.8 <= f < 1.1 for f in fractions), "ge_1.1": sum(f >= 1.1 for f in fractions)}
    return {"smoke_version": "h8-tail-smoke-v1", "rules_sha256": rules_sha, "git_commit": hb._git_commit(),
            "run_utc": _iso(time.time()), "n_candidates_available": len(smoke_candidates(files, pins)),
            "n_requested": len(cands), "n_failed_requests": n_failed_requests, "n_ge_80pct_points": n_ok_points,
            "n_spacing_ok": n_ok_spacing, "n_pass": n_pass, "pass_threshold": SMOKE_MIN_PASS,
            "fraction_of_expected_points_histogram": bins, "pass": bool(verdict), "counts_only": True}


def smoke_ok(path: Path, rules_sha: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found; run tail-smoke first")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"smoke result {p} unreadable") from exc
    if d.get("pass") is not True:
        raise Refused(f"smoke result {p} is not a PASS")
    if d.get("rules_sha256") != rules_sha:
        raise Refused(f"smoke result {p} was made under another rules hash")
    return d


# ---- seal (q0121) -----------------------------------------------------------------------------------------------------------


def event_key_split(rows: list[dict], seed: str = SPLIT_SEED) -> dict[str, tuple[str, str]]:
    """``{market_id: (event_key, block)}``. ``event_key`` is the Gamma event id (the market id when none), merged across
    ``negRiskMarketID`` so that all members of one neg-risk event share one key (the smallest key of the component);
    ``block`` is SCREEN when the first byte of ``sha256(seed|event_key)`` is even, else HOLDOUT."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    base: dict[str, str] = {}
    neg_first: dict[str, str] = {}
    for r in rows:
        ek = (str(r.get("event_ids") or "").split(";")[0] or str(r.get("event_id") or "")) or f"m{r['market_id']}"
        base[r["market_id"]] = ek
        find(ek)
        nr = str(r.get("neg_risk_market_id") or "")
        if nr:
            if nr in neg_first:
                union(ek, neg_first[nr])
            else:
                neg_first[nr] = ek
    out = {}
    for mid, ek in base.items():
        key = find(ek)
        first = hashlib.sha256(f"{seed}|{key}".encode()).digest()[0]
        out[mid] = (key, "SCREEN" if first % 2 == 0 else "HOLDOUT")
    return out


# hashed into the rules file (fetch rules and the split); defined after the functions it names
RULE_FUNCS = (class_d, has_clarification, monday_grid, draw_origins, frame_filter_reason, key_types_matched,
              sample_weight_of, usable_point, qualifying_buyers, hb._rank, hb.allocate_weighted, event_key_split,
              hb.cb1_topic, _is_weather, tail_row)


def read_location(data_root: Path) -> dict:
    used = c4._cb2w().dir_size(Path(data_root)) / 1024**3
    return {"host": socket.gethostname(), "platform": sys.platform,
            "location": "host" if sys.platform.startswith("linux") else "mac", "data_root": str(data_root),
            "run_dir_gb": round(used, 4),
            "note": "one read location for the life of h8; a change needs a committed note and the access log carried across"}


def h7_state(h7_run: str, seals_dir: Path) -> tuple[str, Path | None]:
    """``sealed`` (committed seal copy), ``not_run`` (committed NOT_RUN record) or ``pending``."""
    sp = Path(seals_dir) / f"{h7_run}_SEAL.json"
    if sp.exists():
        return "sealed", sp
    npath = Path(seals_dir) / f"{h7_run}_NOT_RUN.json"
    if npath.exists():
        return "not_run", npath
    return "pending", None


def h7_ids_from_copy(path: Path) -> set[str]:
    """Market ids from an h7 seal copy's ``prices|trades/<id>[__<event>].csv.gz`` file names (ids only)."""
    doc = json.loads(Path(path).read_text())
    ids = set()
    for rel in (doc.get("files") or {}):
        m = re.match(r"^(?:prices|trades)/([^/_]+)(?:__[^/]*)?\.csv\.gz$", rel)
        if m:
            ids.add(m.group(1))
    return ids


def seal_tail(root: Path, run_id: str, *, transport: hb.Transport | None = None, seals_dir: Path | None = None,
              h7_seals_dir: Path | None = None, trials_path: Path | None = None, rps: float = 2.0,
              recheck_keys: bool = True, sleep: Callable[[float], None] = time.sleep, location: dict | None = None,
              live_check: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time,
              t_seal_epoch: float = T_SEAL_EPOCH) -> dict:
    """q0121. Only a ``tail_fetch_complete`` run is sealed. Re-checks every sampled market against
    ``exclusion_keys.csv.gz`` (residual drops, expected 0); waits for both h7 runs to be terminal (``NotNow`` otherwise)
    and drops any h8 market whose id is in an h7 seal copy or that shares an event id, ``negRiskMarketID`` or series id with
    such a market (Gamma lookup by id, ``rps`` 2); writes ``split.csv.gz`` (market_id, event_key, block with SCREEN,
    HOLDOUT, DROPPED_KEY, DROPPED_H7), ``h7_drop.csv.gz``, ``key_recheck.json``; seals (listing hash over every file but
    SEAL.json and ACCESS_LOG.jsonl, one ``history_seal_declaration`` trial line) and writes the committed copy
    ``seals/h8_tail_SEAL.json``."""
    refuse_run_id(run_id)
    rdir = Path(root) / run_id
    mp = rdir / "manifest.json"
    if (rdir / NOT_RUN_FILE).exists() or (rdir / UNVERIFIED_FILE).exists():
        raise Refused(f"{run_id} is {NOT_RUN_TOKEN if (rdir / NOT_RUN_FILE).exists() else UNVERIFIED_TOKEN}; it is never sealed")
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if not (man.get("complete") is True and not man.get("stopped") and man.get("status") == COMPLETE_TOKEN):
        raise Refused(f"{run_id} is not {COMPLETE_TOKEN}; refusing to seal")
    want_hashes = man.get("file_sha256")
    if not isinstance(want_hashes, dict) or not want_hashes:
        raise Refused(f"{run_id} manifest has no file_sha256; refusing to seal")
    for rel, want in sorted(want_hashes.items()):
        fp = rdir / rel
        if not fp.is_file():
            raise Refused(f"fetched file missing at seal: {rel}")
        if h5_seal.sha256_file(fp) != want:
            raise Refused(f"fetched file sha256 differs from the fetch manifest: {rel}")
    h7dir = Path(h7_seals_dir or seals_dir or SEALS_DIR)
    states = {h: h7_state(h, h7dir) for h in H7_RUN_IDS}
    pending = [h for h, (s, _) in states.items() if s == "pending"]
    if pending:
        raise NotNow(f"h7 runs not terminal yet: {pending}")
    sample = list(_read_csv_gz(rdir / "sample.csv.gz"))
    sample_ids = {r["market_id"] for r in sample}
    excl = load_key_sets(rdir / "exclusion_keys.csv.gz")
    drop_key: dict[str, list[str]] = {}
    if recheck_keys:
        for r in sample:
            kt = key_types_matched(r, excl)
            if kt:
                drop_key[r["market_id"]] = kt
    h7_ids: set[str] = set()
    for _, (s, p) in states.items():
        if s == "sealed" and p is not None:
            h7_ids |= h7_ids_from_copy(p)
    h7_keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    h7_missing = 0
    if h7_ids:
        if transport is None:
            raise Refused("h7 seal copies exist but no transport was given for the key lookup")
        lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = lookup_keys(lim, sorted(h7_ids))
        h7_missing = len(h7_ids) - len(found)
        for k in found.values():
            h7_keys["event"].update(e for e in k["event_ids"].split(";") if e)
            if k["neg_risk_market_id"]:
                h7_keys["neg_risk_market"].add(k["neg_risk_market_id"])
            h7_keys["series"].update(s for s in k["series_ids"].split(";") if s)
    drop_h7: dict[str, list[str]] = {}
    for r in sample:
        why = (["id"] if r["market_id"] in h7_ids else []) + key_types_matched(r, h7_keys)
        if why:
            drop_h7[r["market_id"]] = why
    split = event_key_split(sample)
    rows = []
    n = {"SCREEN": 0, "HOLDOUT": 0, "DROPPED_KEY": 0, "DROPPED_H7": 0}
    for mid in sorted(sample_ids):
        ek, blk = split[mid]
        if mid in drop_key:
            blk = "DROPPED_KEY"
        elif mid in drop_h7:
            blk = "DROPPED_H7"
        n[blk] += 1
        rows.append([mid, ek, blk])
    gz = lambda path, header, body: path.write_bytes(hb._gz_csv_bytes(header, body))  # noqa: E731
    gz(rdir / "split.csv.gz", ["market_id", "event_key", "block"], rows)
    gz(rdir / "h7_drop.csv.gz", ["market_id", "reason"], [[m, "+".join(w)] for m, w in sorted(drop_h7.items())])
    recheck = {"n_sample": len(sample_ids), "residual_key_matches": len(drop_key),
               "by_type": {t: sum(t in v for v in drop_key.values()) for t in KEY_TYPES}, "expected": 0,
               "h7": {h: s for h, (s, _) in states.items()}, "h7_ids": len(h7_ids), "h7_ids_without_metadata": h7_missing,
               "h7_dropped": len(drop_h7), "recheck_keys": recheck_keys}
    (rdir / "key_recheck.json").write_text(json.dumps(recheck, indent=1, sort_keys=True))
    split_sha = h5_seal.sha256_file(rdir / "split.csv.gz")
    decl = {"dataset_role": "CB6-T h8_tail: SCREEN (Stage 1) and HOLDOUT (Stage 2, sealed) event-hash split; exploratory_historical, "
                            "not prospective, not an edge claim",
            "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; the runner refuses HOLDOUT until "
                          "Stage 1 of CB6-T is final and committed; outcomes only from outcomes_guarded.csv.gz; DROPPED_* blocks "
                          "are never read",
            "information_end": "manifest request_clock_now (T_fetch8) < T_seal of h4_seal"}
    extra = {"split": {"seed": SPLIT_SEED, "rule": SPLIT_RULE, "counts": n, "split_sha256": split_sha},
             "read_location": location or read_location(Path(root)), "key_recheck": recheck,
             "rules_sha256": man.get("rules_sha256"), "t_fetch8": man.get("request_clock_now")}
    seal = h5_seal.seal_run(rdir, trials_path=trials_path, declaration_base=decl, extra=extra, source="creative_batch_6:cb6_f_seal")
    copy = h5_seal.write_committed_copy(rdir, seals_dir)
    return {"run_id": run_id, "sealed": True, "listing_sha256": seal["listing_sha256"], "committed_copy": str(copy),
            "split_counts": n, "residual_key_matches": len(drop_key), "h7_dropped": len(drop_h7)}


def verify_tail(root: Path, run_id: str, seals_dir: Path | None = None) -> dict:
    rdir = Path(root) / run_id
    return h5_seal.require_sealed(rdir, h5_seal.committed_seal_path(run_id, seals_dir))


__all__ = ["RUN_ID", "Refused", "NotNow", "tail_fetch", "seal_tail", "verify_tail", "run_smoke", "write_rules", "verify_rules",
           "rules_file_doc", "exclusion_stage", "walk_tail_frame", "build_frame_outputs", "draw_origins", "qualifying_buyers"]
