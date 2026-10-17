# ruff: noqa: E501
"""CB7 fetch side, shared parts (docs/research_lab/CREATIVE_BATCH_7.md sections 1.3, 1.4, CB7-F and 5.1/5.2).

Rules file (``seals/cb7_text_geo_rules.json``), exclusion keys, smoke probe, the one-request print helpers
(``origin_prints``, ``origin_price``) and the resumable chunk machinery used by ``cb7_text.text_fetch`` and
``cb7_geo.geo_fetch``. Data only: copies fields as the API returns them and computes no statistic.

Reuses the CB6 / h7 fetch machinery (``cb4_data.FetchRun``, ``_fetch_items``, ``cb6_tail`` exclusion helpers).
Every stored row is capped at ``min(T_fetch, T_seal)`` and the drops are counted; no chunk starts at or after
``T_seal`` (``not_run_deadline``); a failed request is never read as "no data".
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import inspect
import json
import math
import platform
import random
import re
import socket
import sys
import time
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from . import cb4_data as c4
from . import cb6_tail as c6
from . import h5_seal
from . import history_backfill as hb

RULES_VERSION = "cb7-text-geo-rules-v1"
FETCH_VERSION = "h8-cb7-fetch-v1"
SMOKE_VERSION = "cb7-smoke-v1"
T_SEAL = c4.T_SEAL
T_SEAL_EPOCH = hb.T_SEAL_EPOCH
DAY = 86400.0
HOUR = 3600.0
HIST_ROOT = c4.HIST_ROOT
SEALS_DIR = h5_seal.SEALS_DIR
RULES_FILE = SEALS_DIR / "cb7_text_geo_rules.json"
CB7_DIR = c4.DATA_DUMPS / "research_lab" / "creative_batch7"
SMOKE_DEFAULT = CB7_DIR / "smoke.json"
EXCLUSION_KEYS_DEFAULT = CB7_DIR / "exclusion_keys.csv.gz"
EXCLUSION_REPORT_NAME = "exclusion_report.json"
KEYS_RUN_ID = "creative_batch7"  # exclusion keys live in <data-dumps>/research_lab/creative_batch7/

TEXT_RUN_ID = "h8_text"
GEO_RUN_ID = "h8_geo"
TEXT_COMPLETE = "text_fetch_complete"
GEO_COMPLETE = "geo_fetch_complete"
NOT_RUN_TOKEN = "not_run_deadline"
UNVERIFIED_TOKEN = "disjointness_unverified"
SOURCE_UNVERIFIED_TOKEN = "source_unverified"
DISK_BUDGET_TOKEN = "disk_budget"
KEYS_COMPLETE = "exclusion_keys_complete"
NOT_RUN_FILE = "NOT_RUN_DEADLINE.json"
UNVERIFIED_FILE = "DISJOINTNESS_UNVERIFIED.json"
SOURCE_UNVERIFIED_FILE = "SOURCE_UNVERIFIED.json"
OUTCOME_FILE = "outcomes_guarded.csv.gz"
DATA_DUMPS_FETCH_CAP_GB = 12.5
REFUSED_EXIT, DISK_BUDGET_EXIT, TEMPFAIL_EXIT = 2, 4, 75

Refused = c6.Refused
NotNow = c6.NotNow
ApiError = c4.ApiError
SealError = h5_seal.SealError

# ---- declared parameters (all of them are in the rules file) ------------------------------------------------------
TEXT_SEED = "arepo-h8-text"
GEO_SEED = "arepo-h8-geo"
SMOKE_SEED = "arepo-cb7-smoke"
AUDIT_SEED = "arepo-cb7-uma-audit"
GEO_TAG_SLUG = "geopolitics"
GEO_TAG_ID = "100265"
TAG_SLUG_URL = "https://gamma-api.polymarket.com/tags/slug/"
N_TEXT_MARKETS = 18000
TEXT_END_FROM = "2025-04-01"
GEO_END_FROM = "2025-06-01"
END_BEFORE_FETCH_DAYS = 7
WINDOWS_PER_DAY = 5
WINDOW_MINUTES = 15
PAGES_PER_WINDOW = 20
TEXT_MIN_LIFE_DAYS = 9
GEO_MIN_LIFE_DAYS = 9
SPORTS_WEIGHT = 0.25
OTHER_WEIGHT = 1.0
DESCRIPTION_CHARS = 4000
MAX_PER_EVENT = 8
GEO_CAP_PREFIX = "arepo-h8-geo|"
TEXT_ORIGIN_DAYS = 7
GEO_ORIGIN_DAYS = (30, 14, 7)
GEO_MIN_AGE_AT_ORIGIN_DAYS = 2
PRINT_LIMIT = 50
PRINT_LOOKBACK_DAYS = 7
VWAP_HOURS = 24
TEXT_BAND = (0.05, 0.95)
TEXT_CELL_BANDS = ((0.05, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 0.95))
GEO_BAND = (0.02, 0.10)
MAX_FAILED_ORIGIN_SHARE = 0.02
MAX_UNVERIFIED_KEY_SHARE = 0.02
KEY_TYPES = ("event", "neg_risk_market", "series")
GAMMA_IDS_PER_REQUEST = 50
MAX_DAY_ATTEMPTS = c4.MAX_DAY_ATTEMPTS
MAX_ITEM_ATTEMPTS = c4.MAX_ITEM_ATTEMPTS
TEXT_OUTPUT_CAP_GB = 0.15
GEO_OUTPUT_CAP_GB = 0.05
KEYS_OUTPUT_CAP_GB = 0.01
SMOKE_CANDIDATES = 200
SMOKE_N = 20
SMOKE_MIN_VOLUME = 10000.0
SMOKE_MIN_NONEMPTY = 10
SMOKE_MIN_COVERAGE = 14
SMOKE_WINDOW_DAYS = (14, 7)
CLARIFICATION_MARKERS = ("clarif", "update:", "updated", "additional context", "edit:")
NOTE_DATE_PATTERN = (r"note:\s*(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?|"
                     r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}|"
                     r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)")
CLASS_C_PATTERNS = (r"\bprice\w*", r"\btemperature\w*", r"\bscore\w*", r"\bpoll\w*")
PLACEHOLDER_TITLE_PATTERN = r"^(?:other|(?:person|candidate|option|team|player|party|company|country)\s+[a-z])$"
REFUSED_RUN_IDS = ("h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era",
                   "h7_cb4_series", "h8_tail")
REFUSED_ROOTS = ("cb1_extract", "cb2_extract", "cb3_extract", "cb4_extract", "cb5_extract", "cb6_extract", "cb3_followup",
                 "cb6_followup", "cross_venue_live", "surprise_live")

EXCLUSION_PINS = (  # identical to cb6_tail.EXCLUSION_PINS (test), as CB7 section 1.3
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

KEY_COLUMNS = c6.KEY_COLUMNS
GUARDED_COLUMNS = ["market_id", "outcome_prices", "uma_status", "liquidity", "volume"]
ORIGIN_COLUMNS = ["market_id", "origin_ts", "origin_utc", "k"]
PRICE_ROW_COLUMNS = ["item_id", "market_id", "k", "origin_ts", "price_status", "n_prints", "n_prints_24h", "m", "m_source",
                     "last_print_ts", "staleness_s", "in_band", "eligible", "full_page", "vwap_truncated", "dropped_cap",
                     "dropped_out_of_window", "malformed"]
PRINT_COLUMNS = ["item_id", "ts", "yes_price", "size", "yes_side"]
MAIN_COLUMNS = ["market_id", "condition_id", "token0", "token1", "event_id", "event_ids", "neg_risk_market_id", "series_ids",
                "fee_category", "status", "closed", "created_at", "start_at", "end_at", "closed_time", "start_epoch",
                "end_epoch", "close_epoch", "closed_after_cap", "neg_risk", "neg_risk_other", "group_item_title", "question",
                "event_title", "slug", "topic", "outcomes", "market_tag_ids", "event_tag_ids", "query_tag_id"]


# ---- small helpers -------------------------------------------------------------------------------------------------


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _parse_ts(v: Any) -> float | None:
    return c4._parse_ts(v)


def _ep(s: str) -> float:
    return c4._ep(s)


def read_csv_gz(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def file_hashes(rdir: Path, exclude: tuple[str, ...] = ("manifest.json",)) -> dict[str, str]:
    return {k: v for k, v in h5_seal.list_files(rdir).items() if k not in exclude}


def refuse_run_id(run_id: str, allowed: str) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB7 refuses it")
    if run_id != allowed:
        raise Refused(f"this command writes only {allowed!r}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    if any(part in REFUSED_ROOTS for part in Path(path).parts):
        raise Refused(f"path {path} is under a refused CB1-CB6 / live root; CB7 refuses it")
    return Path(path)


# ---- deterministic rules (their SOURCE is hashed into the rules file) ----------------------------------------------


_NOTE_RX = re.compile(NOTE_DATE_PATTERN)
_CLASS_C_RX = [re.compile(p) for p in CLASS_C_PATTERNS]
_PLACEHOLDER_RX = re.compile(PLACEHOLDER_TITLE_PATTERN)
_TEMP_RX: re.Pattern | None = None


def has_clarification(description: str) -> bool:
    """CB6's clarification rule (identical strings): applied to the FULL description."""
    t = (description or "").lower()
    return any(m in t for m in CLARIFICATION_MARKERS) or bool(_NOTE_RX.search(t))


def is_weather(fee_cat: str, question: str, event_title: str) -> bool:
    global _TEMP_RX
    if (fee_cat or "") == "weather":
        return True
    if _TEMP_RX is None:
        w = c4._cb2w()
        _TEMP_RX = re.compile(w.TEMP_RE, w.TEMP_RE_FLAGS)
    return bool(_TEMP_RX.match(question or "") or _TEMP_RX.match(event_title or ""))


def is_geopolitics(r: dict) -> bool:
    return (r.get("fee_category") or "") == "geopolitics" or (r.get("topic") or "") == "geopolitics"


def binary_yes_no(outcomes: Any) -> bool:
    """Outcome labels exactly ``["Yes", "No"]``."""
    try:
        return json.loads(outcomes) == ["Yes", "No"] if isinstance(outcomes, str) else list(outcomes) == ["Yes", "No"]
    except (TypeError, ValueError):
        return False


def is_continuous_question(question: str) -> bool:
    t = (question or "").lower()
    return any(rx.search(t) for rx in _CLASS_C_RX)


def is_other_placeholder(r: dict) -> bool:
    """A neg-risk member that is the venue's "Other" flag or a placeholder title."""
    if str(r.get("neg_risk_other") or "") in ("1", "True", "true"):
        return True
    return str(r.get("neg_risk") or "") in ("1", "True", "true") and bool(_PLACEHOLDER_RX.match(str(r.get("group_item_title") or "").strip().lower()))


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


def cap_status(closed: bool, close_epoch: float, cap_epoch: float) -> tuple[bool, bool]:
    """(closed as known at the cap, closed only after the cap). A market closed after ``min(T_fetch, T_seal)`` is
    "active" at the cap and its close time and outcome are not stored."""
    if not closed:
        return False, False
    if not math.isnan(close_epoch) and close_epoch > cap_epoch:
        return False, True
    return True, False


def _ids_of(items: Any) -> str:
    out = []
    for x in items if isinstance(items, list) else []:
        if isinstance(x, dict) and x.get("id") is not None and str(x["id"]) not in out:
            out.append(str(x["id"]))
    return ";".join(out)


def market_row(m: dict, cap_epoch: float, *, with_text: bool = True) -> tuple[dict, dict] | None:
    """(main row, guarded outcome row) of one Gamma market, or ``None`` unless binary with token ids. Keeps every tag id of
    the market and of its events, the first event title, ``fee_category``, ``closed_time`` as a status field (blank, with
    ``closed_after_cap`` = 1, when it lies after the cap) and the outcome columns only in the guarded row (blank after the
    cap). The description is not part of this row (see ``cb7_text``)."""
    r = hb.frame_row(m, with_text=with_text, with_outcomes=True)
    if r is None:
        return None
    evs = [e for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict)]
    eids, sids, etags = [], [], []
    for e in evs:
        if e.get("id") is not None and str(e["id"]) not in eids:
            eids.append(str(e["id"]))
        for s in (e.get("series") if isinstance(e.get("series"), list) else []):
            if isinstance(s, dict) and s.get("id") is not None and str(s["id"]) not in sids:
                sids.append(str(s["id"]))
        for tid in _ids_of(e.get("tags")).split(";"):
            if tid and tid not in etags:
                etags.append(tid)
    closed_known, after = cap_status(bool(m.get("closed")), r["close_epoch"], cap_epoch)
    main = {c: r.get(c, "") for c in MAIN_COLUMNS if c in r}
    main.update(event_ids=";".join(eids), neg_risk_market_id=str(m.get("negRiskMarketID") or ""), series_ids=";".join(sids),
                status="closed" if closed_known else "active", closed=int(closed_known),
                closed_time="" if after or not closed_known else r["closed_time"],
                close_epoch="" if after or not closed_known else r["close_epoch"], closed_after_cap=int(after),
                neg_risk_other=int(bool(m.get("negRiskOther"))), group_item_title=str(m.get("groupItemTitle") or "")[:200],
                market_tag_ids=_ids_of(m.get("tags")), event_tag_ids=";".join(etags), query_tag_id="")
    guarded = {c: r.get(c, "") for c in GUARDED_COLUMNS}
    if after:
        guarded.update(outcome_prices="", uma_status="")
    return {c: main.get(c, "") for c in MAIN_COLUMNS}, guarded


def key_fields(m: dict) -> dict:
    return c6.key_fields(m)


def draw_sample(strata: dict[str, list[str]], n_total: int, seed: str, weight_fn: Callable[[str], float] = sample_weight_of
                ) -> tuple[dict[str, dict], dict]:
    """Seeded sample over ``status | cb1_topic | end month`` strata, sports weight 0.25 and others 1.0
    (``hb.allocate_weighted``); inside a stratum the order is sha256(seed|market_id). Reads no price, volume or outcome."""
    sizes = {k: len(v) for k, v in strata.items()}
    w = {k: weight_fn(k.split("|")[1]) for k in strata}
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


def origin_prints(lim: hb.Limiter, condition_id: str, t: float, *, cap_epoch: float | None = None, limit: int = PRINT_LIMIT
                  ) -> tuple[list[list], dict]:
    """ONE ``/trades`` request, ``start = t - 7 d``, ``end = t - 1``, ``takerOnly=true``, newest first, ``limit`` 50, no paging.
    Rows are mapped to YES terms ``[ts, yes_price, size, yes_side]`` (outcome index 1 -> ``1 - price``; ``yes_side`` = +1 for
    a buy of YES or a sell of NO). No wallet is read or kept. Rows outside ``[t - 7 d, t)`` or after ``cap_epoch`` are dropped
    and counted. A non-200 reply raises :class:`ApiError` (a failed request is never "no prints")."""
    start, end = int(t - PRINT_LOOKBACK_DAYS * DAY), int(t) - 1
    status, data = lim.get(hb.DATA_TRADES, {"market": condition_id, "start": start, "end": end, "takerOnly": "true", "limit": limit})
    if status != 200 or not isinstance(data, list):
        raise ApiError(f"trades status {status}")
    rows: list[list] = []
    dropped_cap = dropped_window = malformed = 0
    for x in data:
        try:
            ts, idx = int(x["timestamp"]), int(x["outcomeIndex"])
            size, price = float(x["size"]), float(x["price"])
            side = str(x["side"]).upper()
            if idx not in (0, 1) or side not in ("BUY", "SELL"):
                raise ValueError("bad row")
        except (KeyError, TypeError, ValueError):
            malformed += 1
            continue
        if cap_epoch is not None and ts > cap_epoch:
            dropped_cap += 1
            continue
        if not (start <= ts < t):
            dropped_window += 1
            continue
        rows.append([ts, price if idx == 0 else 1.0 - price, size, 1 if (side == "BUY") == (idx == 0) else -1])
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    return rows, {"n_raw": len(data), "full_page": len(data) >= limit, "dropped_cap": dropped_cap,
                  "dropped_out_of_window": dropped_window, "malformed": malformed}


def origin_price(prints: list[list], t: float, band: tuple[float, float], info: dict | None = None) -> dict:
    """Price ``m`` at origin ``t`` from YES-terms prints with ``ts < t``: size-weighted VWAP of the prints in
    ``[t - 24 h, t)`` if any, else the size-weighted price of the prints at the latest timestamp in ``[t - 7 d, t)``
    (``staleness_s`` recorded). Eligible iff at least one print in the 7-day window and ``m`` inside ``band``."""
    info = info or {}
    use = [p for p in prints if t - PRINT_LOOKBACK_DAYS * DAY <= p[0] < t]
    out = {"n_prints": len(use), "n_prints_24h": 0, "m": "", "m_source": "", "last_print_ts": "", "staleness_s": "",
           "in_band": 0, "eligible": 0, "price_status": "no_print", "full_page": int(bool(info.get("full_page"))),
           "vwap_truncated": 0, "dropped_cap": info.get("dropped_cap", 0),
           "dropped_out_of_window": info.get("dropped_out_of_window", 0), "malformed": info.get("malformed", 0)}
    if not use:
        return out

    def vwap(rows: list[list]) -> float:
        tot = sum(r[2] for r in rows)
        return sum(r[1] * r[2] for r in rows) / tot if tot > 0 else sum(r[1] for r in rows) / len(rows)

    recent = [p for p in use if p[0] >= t - VWAP_HOURS * HOUR]
    out["n_prints_24h"] = len(recent)
    last_ts = max(p[0] for p in use)
    if recent:
        m, src = vwap(recent), "vwap24h"
        out["vwap_truncated"] = int(bool(info.get("full_page")) and min(p[0] for p in recent) > t - PRINT_LOOKBACK_DAYS * DAY)
    else:
        m, src = vwap([p for p in use if p[0] == last_ts]), "latest"
    ok = band[0] <= m <= band[1]
    out.update(m=m, m_source=src, last_print_ts=last_ts, staleness_s=t - last_ts, in_band=int(ok), eligible=int(ok),
               price_status="ok" if ok else "out_of_band")
    return out


def draw_geo_cap(rows: list[dict], max_per_event: int = MAX_PER_EVENT, prefix: str = GEO_CAP_PREFIX) -> tuple[set[str], set[str]]:
    """Per-event cap applied AFTER the filters and the key drop: at most ``max_per_event`` of an event's remaining markets
    (first event id; the market id when it has none), the first ones in ``sha256(prefix + market_id)`` order. Returns
    (kept ids, capped-out ids). Seeded by market id only: no price, volume or outcome."""
    by_event: dict[str, list[str]] = {}
    for r in rows:
        ek = (str(r.get("event_ids") or "").split(";")[0] or str(r.get("event_id") or "")) or f"m{r['market_id']}"
        by_event.setdefault(ek, []).append(r["market_id"])
    kept: set[str] = set()
    dropped: set[str] = set()
    for ids in by_event.values():
        order = sorted(ids, key=lambda x: hashlib.sha256((prefix + x).encode()).hexdigest())
        kept.update(order[:max_per_event])
        dropped.update(order[max_per_event:])
    return kept, dropped


# ---- rules file ------------------------------------------------------------------------------------------------------


def rule_funcs() -> tuple:
    from . import cb7_geo, cb7_text  # noqa: PLC0415

    return (has_clarification, is_weather, is_geopolitics, binary_yes_no, is_continuous_question, is_other_placeholder,
            key_types_matched, sample_weight_of, cap_status, market_row, draw_sample, origin_prints, origin_price,
            draw_geo_cap, hb._rank, hb.allocate_weighted, hb.cb1_topic,
            cb7_text.markers, cb7_text.condition_count, cb7_text.text_features, cb7_text.cut_points, cb7_text.text_filter_reason,
            cb7_text.text_row, cb7_geo.geo_filter_reason, cb7_geo.geo_origins, cb7_geo.theme_of, cb7_geo.split_window,
            smoke_pool, smoke_verdict)


def rules_doc(pins=None) -> dict:
    """Everything the two fetches and the S/G analyses could otherwise choose after seeing data (CB7 section 1.4), without
    its own hash. The functions' SOURCE is hashed, so a changed rule function invalidates the committed file."""
    from . import cb7_geo, cb7_text  # noqa: PLC0415

    pins = list(EXCLUSION_PINS if pins is None else pins)
    src = "\n".join(inspect.getsource(f) for f in rule_funcs())
    w = c4._cb2w()
    return {
        "rules_version": RULES_VERSION,
        "seeds": {"text_sample": TEXT_SEED, "geo": GEO_SEED, "geo_cap_prefix": GEO_CAP_PREFIX, "smoke": SMOKE_SEED,
                  "uma_audit": AUDIT_SEED, "placebos": [7171, 7172, 7173, 7174, 7175, 7176], "bootstrap": 717},
        "dates": {"t_seal": T_SEAL, "end_before_fetch_days": END_BEFORE_FETCH_DAYS, "text_end_from": TEXT_END_FROM,
                  "geo_end_from": GEO_END_FROM, "cap": "min(T_fetch, T_seal)",
                  "deadline": "no chunk starts at or after T_seal -> NOT_RUN_DEADLINE.json, status not_run_deadline"},
        "frame": {"frame_version": hb.FRAME_VERSION, "windows_per_day": WINDOWS_PER_DAY, "window_minutes": WINDOW_MINUTES,
                  "pages_per_window": PAGES_PER_WINDOW, "walk_order": ["closed=false", "closed=true"], "forward_walk": False,
                  "capped_windows": "dropped whole and counted", "description_chars": DESCRIPTION_CHARS,
                  "binary_labels": ["Yes", "No"], "closed_time": "kept as a status field (blank after the cap)",
                  "main_columns": MAIN_COLUMNS, "outcome_columns_guarded": GUARDED_COLUMNS[1:],
                  "exclude_weather": {"fee_category": "weather", "temp_re": w.TEMP_RE, "temp_re_flags": w.TEMP_RE_FLAGS},
                  "exclude_crypto_updown": hb.CB1_UPDOWN_RE.pattern,
                  "exclude_geopolitics": "fee_category == 'geopolitics' or history_topics.topic_of(...) == 'geopolitics'",
                  "other_placeholder": {"negRiskOther": True, "neg_risk_group_item_title_pattern": PLACEHOLDER_TITLE_PATTERN},
                  "text_filter_order": list(cb7_text.TEXT_FILTER_ORDER), "geo_filter_order": list(cb7_geo.GEO_FILTER_ORDER)},
        "exclusion": {"files": pins, "key_types": list(KEY_TYPES), "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
                      "ids_per_request": GAMMA_IDS_PER_REQUEST, "retry_missing_with_closed_true": True,
                      "series_ids_from": "all events of the market", "refused_run_ids": list(REFUSED_RUN_IDS),
                      "refused_roots": list(REFUSED_ROOTS)},
        "text": {"n_markets": N_TEXT_MARKETS, "end_from": TEXT_END_FROM, "min_life_days": TEXT_MIN_LIFE_DAYS,
                 "strata": ["status", "cb1_topic", "end_month"], "weights": {"sports": SPORTS_WEIGHT, "other": OTHER_WEIGHT},
                 "allocator": "hb.allocate_weighted", "order_within_stratum": "sha256(seed|market_id)",
                 "origin": {"days_before_end": TEXT_ORIGIN_DAYS, "one_request_per_market": True},
                 "markers": cb7_text.MARKER_DOC, "clarification_markers": list(CLARIFICATION_MARKERS),
                 "note_date_pattern": NOTE_DATE_PATTERN, "features_on_full_description": True,
                 "cut_rule": cb7_text.CUT_RULE, "band": list(TEXT_BAND), "cell_bands": [list(b) for b in TEXT_CELL_BANDS],
                 "cell_fixed_effects": "cb1_topic x band", "stored_description_chars": DESCRIPTION_CHARS,
                 "also_stored": ["description length", "description sha256"]},
        "geo": {"tag_slug": GEO_TAG_SLUG, "tag_id": GEO_TAG_ID, "end_from": GEO_END_FROM, "min_life_days": GEO_MIN_LIFE_DAYS,
                "window_split": "monthly end_date windows halved while capped; capped at one day -> excluded and counted",
                "walk_order": ["closed=true", "closed=false (ended-unclosed, censored)"],
                "order": ["filters", "exclusion key drop", f"cap {MAX_PER_EVENT} per event", "origins"],
                "max_per_event": MAX_PER_EVENT, "cap_hash": f"sha256('{GEO_CAP_PREFIX}' + market_id)",
                "class_c_patterns": list(CLASS_C_PATTERNS), "status_quo_patterns": list(cb7_geo.STATUS_QUO_PATTERNS),
                "origin_days_before_end": list(GEO_ORIGIN_DAYS), "origin_min_age_days": GEO_MIN_AGE_AT_ORIGIN_DAYS,
                "band": list(GEO_BAND), "max_failed_origin_share": MAX_FAILED_ORIGIN_SHARE,
                "themes": [[n, p] for n, p in cb7_geo.THEME_PATTERNS], "theme_order": "first match over question + event title",
                "stored": ["all tag ids (market, event)", "event title", "fee_category", "closed_time (status)"]},
        "prints": {"url": hb.DATA_TRADES, "start": "t - 7 d", "end": "t - 1", "taker_only": True, "limit": PRINT_LIMIT,
                   "paging": False, "order": "newest first (verified by the smoke)", "vwap_hours": VWAP_HOURS,
                   "lookback_days": PRINT_LOOKBACK_DAYS,
                   "price": "size-weighted VWAP in [t-24h, t) in YES terms, else latest print (size-weighted at the latest ts)",
                   "wallets_kept": False, "clob_history_used": False, "cap": "ts <= min(T_fetch, T_seal)"},
        "smoke": {"version": SMOKE_VERSION, "seed": SMOKE_SEED, "candidates": SMOKE_CANDIDATES, "n": SMOKE_N,
                  "min_volume": SMOKE_MIN_VOLUME, "min_nonempty": SMOKE_MIN_NONEMPTY, "min_coverage": SMOKE_MIN_COVERAGE,
                  "window_before_end_days": list(SMOKE_WINDOW_DAYS), "tag_slug": GEO_TAG_SLUG, "tag_id": GEO_TAG_ID,
                  "criteria": {"a": "slug resolves to the pinned tag id", "b": "every returned row inside [start, end], newest "
                                                                             "first, over >= min_nonempty non-empty responses",
                               "c": ">= min_coverage of n markets return >= 1 print"},
                  "needs": {"text_fetch": ["b", "c"], "geo_fetch": ["a", "b", "c"]}, "output": "counts only, write-once"},
        "disk": {"output_cap_gb": {"h8_text": TEXT_OUTPUT_CAP_GB, "h8_geo": GEO_OUTPUT_CAP_GB, "keys": KEYS_OUTPUT_CAP_GB},
                 "data_dumps_fetch_cap_gb": DATA_DUMPS_FETCH_CAP_GB, "headroom_exit": TEMPFAIL_EXIT,
                 "disk_budget_exit": DISK_BUDGET_EXIT},
        "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
        "func_sources_sha256": {f.__qualname__: hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in rule_funcs()},
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


# ---- smoke probe (counts only; write-once result) --------------------------------------------------------------------------


def smoke_pool(files: dict[str, Path], pins, n_candidates: int = SMOKE_CANDIDATES, seed: str = SMOKE_SEED) -> list[str]:
    """``n_candidates`` market ids drawn (seeded by sha256(seed|id)) from the h1/h2/h3 exclusion samples. Reads ids only."""
    ids: set[str] = set()
    for pin in pins:
        if pin["kind"] == "sample":
            ids.update(str(r["market_id"]) for r in read_csv_gz(files[pin["name"]]))
    return sorted(ids, key=lambda x: hb._rank(seed, x))[:n_candidates]


def smoke_verdict(a: bool, b_bounds_ok: bool, b_order_ok: bool, n_nonempty: int, n_covered: int, n_markets: int,
                  min_nonempty: int = SMOKE_MIN_NONEMPTY, min_coverage: int = SMOKE_MIN_COVERAGE, n: int = SMOKE_N) -> dict:
    """The a-priori criteria: (a) slug resolves to the pinned id; (b) every returned row inside the bounds and newest first
    over >= ``min_nonempty`` non-empty responses; (c) >= ``min_coverage`` of ``n`` markets return >= 1 print. A smoke with
    fewer than ``n`` markets fails (b) and (c)."""
    full = n_markets >= n
    b = bool(b_bounds_ok and b_order_ok and n_nonempty >= min_nonempty and full)
    c = bool(n_covered >= min_coverage and full)
    return {"a": bool(a), "b": b, "c": c, "pass": bool(a and b and c)}


def run_smoke(lim: hb.Limiter, files: dict[str, Path], pins, rules_sha: str) -> dict:
    """q0140. Counts only: no id, price, timestamp, question or text is kept."""
    a_ok, tag_error = False, False
    try:
        status, data = lim.get(TAG_SLUG_URL + GEO_TAG_SLUG, {})
        a_ok = status == 200 and isinstance(data, dict) and str(data.get("id")) == GEO_TAG_ID
    except RuntimeError:
        tag_error = True
        raise NotNow("smoke: tag request failed after retries (network); nothing written, retry later") from None
    cands = smoke_pool(files, pins)
    found: dict[str, dict] = {}
    n_gamma_failed = 0
    for i in range(0, len(cands), GAMMA_IDS_PER_REQUEST):  # parse guard keeps end_at, volumeNum and the condition id only
        batch = cands[i:i + GAMMA_IDS_PER_REQUEST]
        for closed in (True, False):
            todo = [x for x in batch if x not in found]
            if not todo:
                break
            params: dict = {"id": todo, "limit": GAMMA_IDS_PER_REQUEST}
            if closed:
                params["closed"] = "true"
            try:
                status, rows = lim.get(hb.GAMMA_MARKETS, params)
            except RuntimeError:
                raise NotNow("smoke: Gamma lookup failed after retries (network); nothing written, retry later") from None
            if status != 200 or not isinstance(rows, list):
                raise NotNow(f"smoke: Gamma lookup status {status}; nothing written, retry later")
            for m in rows:
                if isinstance(m, dict) and str(m.get("id")) in todo:
                    found[str(m["id"])] = {"end": _parse_ts(m.get("endDate")), "vol": _num(m.get("volumeNum")),
                                           "cid": m.get("conditionId")}
    y25 = (_ep("2025-01-01"), _ep("2026-01-01"))
    pool = [x for x in cands if x in found and found[x]["end"] is not None and y25[0] <= found[x]["end"] < y25[1]
            and found[x]["vol"] >= SMOKE_MIN_VOLUME and found[x]["cid"]]
    chosen = pool[:SMOKE_N]
    n_nonempty = n_covered = n_failed = 0
    bounds_ok = order_ok = True
    for x in chosen:
        end = found[x]["end"]
        a, b = int(end - SMOKE_WINDOW_DAYS[0] * DAY), int(end - SMOKE_WINDOW_DAYS[1] * DAY) - 1
        try:
            status, rows = lim.get(hb.DATA_TRADES, {"market": found[x]["cid"], "start": a, "end": b, "takerOnly": "true", "limit": PRINT_LIMIT})
        except RuntimeError:
            raise NotNow("smoke: trades request failed after retries (network); nothing written, retry later") from None
        if status != 200 or not isinstance(rows, list):
            raise NotNow(f"smoke: trades status {status}; nothing written, retry later")
        ts = []
        for r in rows:
            try:
                ts.append(int(r["timestamp"]))
            except (KeyError, TypeError, ValueError):
                bounds_ok = False
        if ts:
            n_nonempty += 1
            n_covered += 1
            bounds_ok = bounds_ok and all(a <= v <= b for v in ts)
            order_ok = order_ok and all(p >= q for p, q in zip(ts, ts[1:], strict=False))
    v = smoke_verdict(a_ok, bounds_ok, order_ok, n_nonempty, n_covered, len(chosen))
    return {"smoke_version": SMOKE_VERSION, "rules_sha256": rules_sha, "git_commit": hb._git_commit(), "run_utc": _iso(time.time()),
            "criterion_a_slug_resolves_to_pinned_id": v["a"], "criterion_b_bounds_and_order": v["b"],
            "criterion_c_coverage": v["c"], "pass": v["pass"], "counts_only": True,
            "n_candidates_drawn": len(cands), "n_candidates_found_on_gamma": len(found), "n_in_pool": len(pool),
            "n_requested": len(chosen), "n_nonempty": n_nonempty, "n_covered": n_covered, "n_failed_requests": n_failed,
            "n_gamma_failed_requests": n_gamma_failed, "tag_request_failed": tag_error, "bounds_ok": bounds_ok,
            "newest_first_ok": order_ok, "pass_thresholds": {"min_nonempty": SMOKE_MIN_NONEMPTY, "min_coverage": SMOKE_MIN_COVERAGE,
                                                              "n": SMOKE_N}}


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def smoke_ok(path: Path, rules_sha: str, need: tuple[str, ...]) -> dict:
    """The fetchers' smoke gate: the result exists, was made under the same rules hash and criteria ``need`` hold
    (text: b and c; geo: a, b and c)."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found; run smoke first")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"smoke result {p} unreadable") from exc
    if d.get("smoke_version") != SMOKE_VERSION:
        raise Refused(f"smoke result {p} is {d.get('smoke_version')}, not {SMOKE_VERSION}")
    if d.get("rules_sha256") != rules_sha:
        raise Refused(f"smoke result {p} was made under another rules hash")
    keys = {"a": "criterion_a_slug_resolves_to_pinned_id", "b": "criterion_b_bounds_and_order", "c": "criterion_c_coverage"}
    bad = [k for k in need if d.get(keys[k]) is not True]
    if bad:
        raise Refused(f"smoke result {p}: criteria {bad} not met")
    return d


# ---- the resumable fetch session -----------------------------------------------------------------------------------------------


class Cb7Run(c4.FetchRun):
    """``cb4_data.FetchRun`` with a CB7 manifest (rules hash, exclusion-key hash, run location)."""

    rules_sha256 = ""
    keys_sha256 = ""
    label = "CB7"

    def manifest(self, stopped: str | None, extra: dict | None = None) -> dict:
        m = {
            "provenance": hb.PROVENANCE, "evidence_role": hb.EVIDENCE_ROLE, "version": FETCH_VERSION,
            "run_id": self.run_id, "kind": self.kind,
            "purpose": f"{self.label} data (exploratory_historical); never prospective, not an edge claim",
            "git_commit": hb._git_commit(), "rules_sha256": self.rules_sha256, "exclusion_keys_sha256": self.keys_sha256,
            "run_location": {"host": socket.gethostname(), "platform": sys.platform, "python": platform.python_version()},
            "params": {**self.params, "cap_utc": _iso(self.cap_epoch), "max_rps": self.rps,
                       "disk_cap_bytes": self.disk_cap, "budget_min": self.budget_min},
            "started_utc": self.prior.get("started_utc", _iso(self.t_start)), "updated_utc": _iso(time.time()),
            "request_clock_now": self.prior.get("request_clock_now", _iso(self.now)),
            "requests": {"total_this_session": self.lim.requests, "retries": self.lim.retries,
                         "http_429": self.pol.n429, "yielded_to_live_s": self.lim.yielded_s, "rps_halved": self.pol.halved},
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
         "rule": "CREATIVE_BATCH_7.md 1.2: incomplete at T_seal -> not run, recorded; no seal, no analysis, no refetch; the "
                 "dependent CB7 test is recorded 'not run (deadline)' with p = 1 and counted"}, indent=1, sort_keys=True))
    return man


def guard_start(root: Path, run_id: str, wall_clock: Callable[[], float], t_seal_epoch: float, complete_token: str) -> dict | None:
    """Start gate: terminal states are sticky (a rerun reports them without work); at or after T_seal an incomplete run is
    ``not_run_deadline``. Returns a result dict when the call must not fetch, else ``None``."""
    rdir = Path(root) / run_id
    if (rdir / h5_seal.SEAL_NAME).exists():
        raise Refused(f"{run_id} is sealed; the fetch never touches a sealed run")
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if (rdir / NOT_RUN_FILE).exists() or prior.get("stopped") == NOT_RUN_TOKEN:
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    for tok, fname in ((UNVERIFIED_TOKEN, UNVERIFIED_FILE), (SOURCE_UNVERIFIED_TOKEN, SOURCE_UNVERIFIED_FILE)):
        if prior.get("status") == tok or (rdir / fname).exists():
            return {"stopped": tok, "status": tok, "complete": False}
    if prior.get("status") == DISK_BUDGET_TOKEN:  # a full output cap is a declared end state, never retried
        return {"stopped": prior.get("stopped"), "status": DISK_BUDGET_TOKEN, "complete": False, "counts": prior.get("counts")}
    if prior.get("complete") is True and prior.get("stopped") is None:
        return {"stopped": None, "status": complete_token, "complete": True, "counts": prior.get("counts")}
    if wall_clock() >= t_seal_epoch:
        mark_not_run(rdir, "incomplete at T_seal (no new chunk at or after 2026-10-22T00:00Z)")
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    return None


def load_exclusion_keys(keys_path: Path) -> tuple[dict[str, set[str]], dict, str]:
    """The shared key file (q0141), its report and its sha256. Refuses when the file or report is missing or the file does
    not match the report's hash."""
    keys_path = Path(keys_path)
    rep_path = keys_path.with_name(EXCLUSION_REPORT_NAME)
    if not keys_path.exists() or not rep_path.exists():
        raise Refused(f"exclusion key files {keys_path} / {rep_path.name} missing; run exclusion-keys first")
    rep = json.loads(rep_path.read_text())
    sha = h5_seal.sha256_file(keys_path)
    if rep.get("keys_sha256") != sha:
        raise Refused(f"{keys_path} sha256 {sha} != report {rep.get('keys_sha256')}; refusing")
    return c6.load_key_sets(keys_path), rep, sha


def open_run(root: Path, run_id: str, transport, *, allowed_run_id: str, kind: str, label: str, complete_token: str,
             params: dict, smoke_need: tuple[str, ...], history_root: Path | None, seals_dir: Path | None,
             seal_paths: dict[str, Path] | None, rules_path: Path, smoke_path: Path, exclusion_keys_path: Path, pins,
             require_committed: bool, require_smoke: bool, data_dumps: Path | None, data_dumps_cap_gb: float, disk_cap: int,
             rps: float, budget_min: float | None, key: bytes | None, now: float | None, sleep, live_check, wall_clock,
             t_seal_epoch: float, snapshot_root: Path | None, health_every_s: float, health_check, cap_at: str
             ) -> tuple[Cb7Run | None, dict | None, dict]:
    """Common chunk start: refusals (run id, root, rules hash, every exclusion file and its pin, smoke criteria, key file) ->
    terminal / deadline guard -> headroom (exit 75) -> run object. Returns (run, early result, context)."""
    root = Path(root)
    refuse_run_id(run_id, allowed_run_id)
    refuse_path(root)
    history_root = Path(history_root or root)
    seals_dir = Path(seals_dir or SEALS_DIR)
    pins = list(EXCLUSION_PINS if pins is None else pins)
    rules_sha = verify_rules(rules_path, require_committed=require_committed, pins=pins)
    files = c6.verify_exclusion_files(pins, history_root=history_root, seals_dir=seals_dir, seal_paths=seal_paths)
    if require_smoke:
        smoke_ok(smoke_path, rules_sha, smoke_need)
    key_sets, key_report, keys_sha = load_exclusion_keys(exclusion_keys_path)
    early = guard_start(root, run_id, wall_clock, t_seal_epoch, complete_token)
    if early is not None:
        return None, early, {}
    if data_dumps is not None:
        c6.require_data_dumps_room(Path(data_dumps), data_dumps_cap_gb, disk_cap / 1024**3)
    ids = c6.exclusion_ids(files, pins)
    fr = Cb7Run(root, run_id, transport, kind=kind, params=params, rps=rps, disk_cap=disk_cap, budget_min=budget_min, now=now,
                sleep=sleep, live_check=live_check, wall_clock=wall_clock, t_seal_epoch=t_seal_epoch,
                snapshot_root=snapshot_root, health_every_s=health_every_s, health_check=health_check, cap_at=cap_at,
                key=key if key is not None else b"cb7-no-wallets")  # CB7 reads no wallet
    fr.rules_sha256, fr.keys_sha256, fr.label = rules_sha, keys_sha, label
    return fr, None, {"excl_ids": ids, "excl_keys": key_sets, "key_report": key_report, "rules_sha256": rules_sha}


def transient(fr: Cb7Run, why: str) -> dict:
    if why == "t_seal_passed":
        mark_not_run(fr.rdir, "chunk reached T_seal before completion")
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    m = fr.manifest(why, {"transient": why.startswith("paused") or why.startswith("walk_failed") or why == "frame_paused"})
    m["status"] = "in_progress"
    return m


def disk_budget_end(fr: Cb7Run, exc_or_reason, extra: dict | None = None) -> dict:
    m = fr.manifest(f"disk_budget: {exc_or_reason}"[:200], {**(extra or {}), "status": DISK_BUDGET_TOKEN})
    m["status"] = DISK_BUDGET_TOKEN
    return m


def unverified_end(fr: Cb7Run, rep: dict, run_id: str) -> dict:
    (fr.rdir / UNVERIFIED_FILE).write_text(json.dumps({
        "run_id": run_id, "status": UNVERIFIED_TOKEN, "exclusion_report": rep,
        "rule": "CREATIVE_BATCH_7.md 1.3: more than 2% of exclusion ids without Gamma metadata -> disjointness unverified; the "
                "dependent test is not testable (p = 1, counted); no sample, no prints"}, indent=1, sort_keys=True))
    m = fr.manifest(UNVERIFIED_TOKEN, {"exclusion_report": rep, "status": UNVERIFIED_TOKEN})
    m["status"] = UNVERIFIED_TOKEN
    return m


def append_member(fr: Cb7Run, path: Path, rec: dict) -> None:
    """Append one gzip member (budget-checked first: a full output cap raises ``OSError`` before anything is written)."""
    data = c6._gz_jsonl_member(rec)
    fr.budget.charge(len(data))
    with Path(path).open("ab") as fh:
        fh.write(data)


def walk_failed_days(pf: Path) -> dict[str, int]:
    fails: dict[str, int] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                k = json.loads(line)["day"]
                fails[k] = fails.get(k, 0) + 1
    return fails


def frame_days(end_from: float, cutoff: float) -> list[date]:
    d0 = datetime.fromtimestamp(end_from, UTC).date()
    d1 = datetime.fromtimestamp(cutoff, UTC).date()
    return [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]


def pick_windows(day: date, seed: str, cutoff_epoch: float, windows_per_day: int, window_minutes: int) -> tuple[datetime, list[int]]:
    """The seeded windows of one day (windows ending after the cutoff are not valid: no forward walk)."""
    dkey = f"{day:%Y-%m-%d}"
    d0 = datetime(day.year, day.month, day.day, tzinfo=UTC)
    slots = 1440 // window_minutes
    valid = [k for k in range(slots) if (d0 + timedelta(minutes=(k + 1) * window_minutes)).timestamp() <= cutoff_epoch]
    rng = random.Random(f"{seed}|{dkey}")
    return d0, (sorted(rng.sample(valid, min(windows_per_day, len(valid)))) if valid else [])


def stream_origin_tables(fr: Cb7Run, key_name: str) -> dict:
    """At completion: ``origin_prices.csv.gz`` from the done progress records and ``origin_prints.csv.gz`` from the partial
    print members (first member per item wins); partial files are removed. Returns row counts and failure counts."""
    rdir = fr.rdir
    done = fr.read_progress(key_name)
    n_failed = sum(1 for r in done.values() if r["status"] != "done")
    price_rows = []
    for k in sorted(done):
        rec = done[k]
        if rec["status"] == "done":
            price_rows.append([rec.get(c, "") for c in PRICE_ROW_COLUMNS])
    fr.budget.write_gz_csv(rdir / "origin_prices.csv.gz", PRICE_ROW_COLUMNS, price_rows)
    seen: set[str] = set()
    part = rdir / "prints_partial.jsonl.gz"

    def prints_rows() -> Iterator[list]:
        for rec in c6.iter_partial(part):
            if rec["item_id"] in seen or done.get(rec["item_id"], {}).get("status") != "done":
                continue
            seen.add(rec["item_id"])
            for p in rec["prints"]:
                yield [rec["item_id"], *p]

    fr.budget.write_gz_csv(rdir / "origin_prints.csv.gz", PRINT_COLUMNS, prints_rows())
    part.unlink(missing_ok=True)
    return {"origin_price_rows": len(price_rows), "origin_print_items": len(seen), "items_failed_final": n_failed}


# ---- stage 1: the shared exclusion keys (q0141) ---------------------------------------------------------------------------------------


def exclusion_keys(out_root: Path, transport, *, history_root: Path, seals_dir: Path | None = None,
                   seal_paths: dict[str, Path] | None = None, rules_path: Path = RULES_FILE, pins=None,
                   require_committed: bool = True, rps: float = 4.0, disk_cap: int = int(KEYS_OUTPUT_CAP_GB * 1024**3),
                   budget_min: float | None = None, now: float | None = None, sleep=time.sleep, live_check=None,
                   should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time,
                   t_seal_epoch: float = T_SEAL_EPOCH, snapshot_root: Path | None = None, health_every_s: float = 600.0,
                   health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = DATA_DUMPS_FETCH_CAP_GB,
                   cap_at: str = T_SEAL) -> dict:
    """Gamma lookup by id (<= 50 per request, ``closed=true`` retry, parse guard ids and keys only) of every h1/h2/h3/h5/h5_ladders
    market id -> ``<out_root>/creative_batch7/exclusion_keys.csv.gz`` + ``exclusion_report.json`` (CB6's stage, reused).
    Resumable by batch. More than 2% of ids without metadata -> ``disjointness_unverified``."""
    out_root = Path(out_root)
    refuse_path(out_root)
    seals_dir = Path(seals_dir or SEALS_DIR)
    pins = list(EXCLUSION_PINS if pins is None else pins)
    rules_sha = verify_rules(rules_path, require_committed=require_committed, pins=pins)
    files = c6.verify_exclusion_files(pins, history_root=Path(history_root), seals_dir=seals_dir, seal_paths=seal_paths)
    if wall_clock() >= t_seal_epoch:
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    if data_dumps is not None:
        c6.require_data_dumps_room(Path(data_dumps), data_dumps_cap_gb, disk_cap / 1024**3)
    ids = c6.exclusion_ids(files, pins)
    fr = Cb7Run(out_root, KEYS_RUN_ID, transport, kind="exclusion_keys", params={"n_ids": len(ids), "key_types": list(KEY_TYPES)},
                rps=rps, disk_cap=disk_cap, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                wall_clock=wall_clock, t_seal_epoch=t_seal_epoch, snapshot_root=snapshot_root, health_every_s=health_every_s,
                health_check=health_check, cap_at=cap_at, key=b"unused")
    fr.rules_sha256, fr.label = rules_sha, "CB7 exclusion keys"
    why = fr.unhealthy()
    if why:
        return fr.manifest(why, {"transient": True, "status": "in_progress"})
    try:
        rep, stopped = c6.exclusion_stage(fr, ids, should_stop)  # duck-typed: uses rdir, lim, budget, stop_reason
    except OSError as exc:
        return disk_budget_end(fr, exc)
    except RuntimeError as exc:
        return fr.manifest(f"stage_failed: {exc}"[:200], {"transient": True, "status": "in_progress"})
    if stopped:
        if stopped == "t_seal_passed":
            return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep is not None
    status = UNVERIFIED_TOKEN if rep["disjointness"] == UNVERIFIED_TOKEN else KEYS_COMPLETE
    m = fr.manifest(None, {"exclusion_report": rep, "status": status, "complete": True})
    m["status"] = status
    return m
