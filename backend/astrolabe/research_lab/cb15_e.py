# ruff: noqa: E501
"""CB15-E: election-night reporting-order drift, 3 November 2026 (CH129; docs/research_lab/CREATIVE_BATCH_15.md CB15-E, sections 1.2, 2.1-2.8, 9-10). Rules part ``E``.

One-night case study; the night is one cluster; no claim beyond that night. Census (q0341, counts only), GE0 tables (the archived sign table, poll-close table, party map, sign x
closing-hour cross-table and source manifest; a repo step, compiled by two network-enabled passes and audited read-only; this module reads and validates them and refuses if any is
absent), smoke helpers (q0343), the pre-gate (q0344: race map, two-party rule, control markets, band counts, GEI / GEC / GEP), the election-night collector (q0345: ``POST /books``
on the :00/:10 grid, every minute in the night window, receipt-timed, gap log, storage projection with degradation to the top level, NO exit-75 path in the window), the committed
cron pause / resume lines for the ``cpu`` lane hold, and the screen (q0346: E1 stratified balanced drift within closing-hour strata with the within-stratum state-label
permutation, sign share, net-of-control logits, pre-night placebo and robustness; E2 at recorded books). This module imports ``cb15_common`` and nothing from the P family.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
import socket
import struct
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb15_common as c15

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

MINUTE = 60.0
HOUR = 3600.0
DAY = 86400.0
RUN = "h15_elect_live"
LABEL_E = "one-night case study (2026-11-03 US general election); the night is one cluster; L2 prospective, recorded books; no claim beyond that night"
# ---- dates (section 1.2; UTC; ET = UTC-5 on 2026-11-03) ----------------------------------------------------------------------------------------------
T15_E_FREEZE = "2026-11-01T12:00:00Z"  # hard: part E frozen (rules, GE0 files, race map, collector cap); else E1, E2 "not run (calendar)", counted
T15_E_PRE = "2026-11-02T12:00:00Z"  # first collector pass (tier snapshot)
T15_E_ON = "2026-11-03T22:00:00Z"  # passes every minute from here ...
T15_E_OFF = "2026-11-04T21:00:00Z"  # ... to here
T15_E_END = "2026-11-06T00:00:00Z"  # collector stops; q0346 runs
T15_CPU_HOLD = ("2026-11-03T21:00:00Z", "2026-11-04T22:00:00Z")
T15_CPU_DRY_RUN = ("2026-11-02T12:00:00Z", "2026-11-02T12:10:00Z")
T15_CPU_HOLD_PLACE = "2026-11-03T15:00:00Z"  # the hold blocks promotion only: it is placed 6 h before T15_cpu_hold so a heavy job promoted late cannot run into the night (round 2)
WATCHDOG_MAX_AGE_S = 180.0  # heartbeat older than 3 min inside [T15_E_pre, T15_E_end) -> alert
DEPLOY_FREEZE = ("from the part-E freeze to 2026-11-06T00:00Z: no deploy that changes backend/astrolabe/research_lab/{cb15_common,cb15_e}.py or any SHARED_HELPERS module "
                 "(cb2_weather, cb6_tail, cb8_books, cb8_common, cb9_common, cb10_common, cb12_common); e-live re-verifies these hashes every minute and refuses on a change")
T15_DISK_CHECK_DAY = "2026-11-02"
ELECTION_DAY = "2026-11-03"
GRID_S = 600.0
NIGHT_GRID_S = 60.0
POLL_CLOSE_RANGE = ("2026-11-03T23:00:00Z", "2026-11-04T07:30:00Z")
T_A_OFFSET_S = 90 * MINUTE
T_B_OFFSET_S = 12 * HOUR
T_A_ROBUST_S = (60 * MINUTE, 150 * MINUTE)
T_B_ROBUST_S = (6 * HOUR, 24 * HOUR)
PLACEBO_WINDOW_S = (-36 * HOUR, -24 * HOUR)  # [t_a - 36 h, t_a - 24 h]
READ_LAG_A_S = 120.0  # a read "at t_a": first successful read with receipt >= t within 2 min
READ_LAG_B_S = 300.0  # at t_b: within 5 min
# ---- frame (q0341; frozen query list, section 1.4) ----------------------------------------------------------------------------------------------------
QUERIES = ("Senate 2026", "Governor 2026", "House 2026", "congressional district 2026", "midterm 2026")
SEARCH_STATUS = "active"
SEARCH_LIMIT = 50
SEARCH_MAX_PAGES = 24
EVENT_LOOKUP_MAX_REQ = 400
WALK_TAG_ID = 2  # Gamma politics tag
WALK_END_WINDOW = ("2026-11-03T00:00:00Z", "2027-02-01T00:00:00Z")  # active events ending [2026-11-03, 2027-01-31]
WALK_STEP_D = 7
WALK_MAX_REQ = 100
COMPLETENESS_MIN = 0.95
CENSUS_MAX_REQ = 620
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
          "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
          "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
          "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
          "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
          "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
SENATE_RE = re.compile(r"(?i)\bsenate\b")
GOVERNOR_RE = re.compile(r"(?i)\b(governor|gubernatorial)\b")
HOUSE_RE = re.compile(r"(?i)(\bhouse\b|\bcongressional district\b|\b[A-Z]{2}-(\d{1,2}|AL)\b|\bat-large\b)")
DISTRICT_RE = re.compile(r"\b([A-Z]{2})-(\d{1,2}|AL)\b")
DISTRICT_ORD_RE = re.compile(r"(?i)\b(\d{1,2})(st|nd|rd|th)\s+(congressional\s+)?district\b")
RACE_EXCLUDE_RE = re.compile(r"(?i)\b(primary|primaries|runoff|run-off|nominee|nomination|caucus|margin|turnout|popular vote|recount|by how much|vote share|percentage)\b")
GENERAL_DATE_RE = re.compile(r"(?i)(november\s+3(rd)?,?\s+2026|3(rd)?\s+november,?\s+2026|nov\.?\s+3(rd)?,?\s+2026|2026-11-03|11/0?3/2026)")
CONTROL_RE = re.compile(r"(?i)\b(control|majority|balance of power|which party will win)\b")
DEM_RE = re.compile(r"(?i)\b(democrat|democrats|democratic)\b")
REP_RE = re.compile(r"(?i)\b(republican|republicans|gop)\b")
# ---- GE0 (section CB15-E; committed before the freeze) --------------------------------------------------------------------------------------------------
GE0_DIR_REL = "docs/research_lab/seals/cb15_ge0"
GE0_FILES = {"sign_table": "sign_table.json", "poll_close": "poll_close.json", "party_map": "party_map.json", "cross_table": "cross_table.json", "source_manifest": "source_manifest.json"}
GE0_VERSIONS = {"sign_table": "cb15-ge0-sign-v1", "poll_close": "cb15-ge0-pollclose-v1", "party_map": "cb15-ge0-party-v1", "cross_table": "cb15-ge0-cross-v1",
                "source_manifest": "cb15-ge0-sources-v1"}
GE0_ARCHIVE_REL = "research_lab/creative_batch15/ge0_sources"  # under data-dumps: the archived files themselves (URL, fetch time, sha256, file)
GE0_PASSES = ("A", "B")
GE0_AUDIT_VALUES = ("supported", "unsupported")
GE0_FORBIDDEN_SOURCE_KINDS = ("2026_poll", "2026_forecast", "market_page", "2026_news")
GE0_SIGNS = (-1, 0, 1)
SIGN_YEARS = ("2022", "2024")
GE0_SCHEMAS = {
    "sign_table": {"version": "cb15-ge0-sign-v1", "kappa": "Cohen's kappa of passes A and B (reported)",
                   "states": {"<XX>": {"s": "+1 / -1 / 0", "pass_a": "+1 / -1 / 0", "pass_b": "+1 / -1 / 0", "mode_order": "+1 / -1 / 0 (2026 counting order of vote modes)",
                                       "dir_2022": "+1 / -1 / 0", "dir_2024": "+1 / -1 / 0", "audit": "supported / unsupported (science-reviewer, read-only)",
                                       "mode_order_citations": "[archive sha256]", "dir_2022_citations": "[archive sha256]", "dir_2024_citations": "[archive sha256]"}}},
    "poll_close": {"version": "cb15-ge0-pollclose-v1", "states": {"<XX>": {"t_close_utc": "YYYY-MM-DDTHH:MM:SSZ (the latest official close across its time zones)", "citations": "[archive sha256]"}}},
    "party_map": {"version": "cb15-ge0-party-v1", "races": {"<XX>|<senate|governor|house>|<district or ''>": {"candidates": {"<candidate name>": "D / R"}, "citations": "[archive sha256]"}}},
    "cross_table": {"version": "cb15-ge0-cross-v1", "all_51": "generated by `run_cb15.py ge0-cross-table` (counts of effective signs by closing-hour stratum)"},
    "source_manifest": {"version": "cb15-ge0-sources-v1", "files": [{"sha256": "hex", "url": "source URL", "fetched_utc": "ISO UTC", "file": "path under ge0_sources/",
                                                                      "kind": "state_law / election_office / ncsl / results_2022 / results_2024 / poll_close / candidate_list / other"}]},
}
# ---- units, strata, gates ---------------------------------------------------------------------------------------------------------------------------
BAND = (0.10, 0.90)
SPREAD_MAX = 0.10
LOGIT_CLAMP = (0.01, 0.99)
E1_FLOOR = 0.05
E1_SIGN_SHARE_MIN = 0.60
E2_FLOOR = 0.01
NET_CONTROL_P = 0.05
PLACEBO_P_FAIL = 0.01
ROBUST_P = 0.05
NO_DEPTH_SIZE = 10.0
TOP_STATES_PER_SIGN = 2
SENATE_GOV_MIN_PER_SIGN = 4
GEC_MIN_RACES = 25
GEC_MIN_STATES = 16
GEC_MIN_PER_SIGN = 9
GE_MIN_STATES = 16
GE_MIN_PER_SIGN = 7
GEP_SIGMA_D = 0.20  # declared (round 6: gaps of 10-30c during the count); no night data enters it
GEP_Z = 2.3263478740408408 + 0.8416212335729143  # z_0.99 + z_0.80
GEP_MAX_MDE = 0.15  # 3x the floor: a declared deviation from CB14's 2x, accepted only for a one-night case study (round 1 item 6)
TIER_LIQUID_SHARE = 1.0 / 3.0
NOT_RUN_CALENDAR = "not run (calendar)"
NOT_RUN_IDENT = "not run (identifiability)"
NOT_RUN_POWER = "not run (power)"
NOT_TESTABLE_POP = "not testable (population)"
NOT_TESTABLE_FRAME = "not testable (frame completeness)"
NOT_TESTABLE_SOURCE = "not testable (source)"
NOT_TESTABLE_AVAIL = "not testable (availability)"
# ---- collector (q0345; section 2.8) ----------------------------------------------------------------------------------------------------------------
CLOB_BOOKS = "https://clob.polymarket.com/books"
BOOKS_BATCH = 100
BOOK_LEVELS = 5
BOOK_LEVELS_DEGRADED = 1
BATCH_RETRY_S = 2.0
BOOKS_RPS = 2.0
COLLECTOR_MEM_MB = 200
COLLECTOR_NICE = 5
MAP_REFRESH_S = 6 * HOUR
CAP_MARGIN = 3.0
CAP_MIN_GB = 1.0
HOST_PROTECT_FREE_GB = 2.0
PRE_NIGHT_FREE_MARGIN_GB = 10.0
PROJECTION_WINDOW = 10
BOOK_FIELDS = ("asset_id", "market", "timestamp", "bids", "asks", "tick_size", "neg_risk", "last_trade_price")
LIVE_FILES = {"state": "state.json", "gaps": "gaps.jsonl", "storage": "storage.jsonl", "passes": "passes.jsonl", "tier": "tier.json", "refresh_dir": "refresh", "books_dir": "books",
              "manifest": "manifest.json", "heartbeat": "heartbeat.json"}
LIVE_STATUS_CLOSED = "e_live_window_closed"
ABSENT_WHY = "token absent from the response"
GAMMA_TIMEOUT_S = 10.0  # the collector's Gamma calls: no retries, short timeout (round 2 fix 2)
TIER_RETRY_S = 600.0
CLOSED_STATUS = "closed before t_b (last read)"
CLOSED_BEFORE_TA = "closed before t_a (pre-entry)"
CENSUS_STATUS = "e_census_complete"
RACE_MAP_NAME = "race_map.csv"
RACE_MAP_COLUMNS = ["race_id", "kind", "state", "office", "district", "event_id", "market_id", "token_d_yes", "token_d_no", "party_source", "two_party", "band_q0344", "sign", "stratum",
                    "t_close", "chamber", "fee_rate", "neg_risk_market_id", "series_id", "key_overlap"]
CENSUS_COLUMNS = ["event_id", "kind", "office", "state", "district", "general_ok", "excluded", "n_members", "trade_type", "chamber", "neg_risk_market_id", "series_id", "market_ids"]
# ---- the cpu-lane hold (section 2.8; round 1 items 4, 8) -------------------------------------------------------------------------------------------------
QUEUE_WORKER = "/home/opc/arepo/scripts/oracle/queue_worker.py"
HOST_PY = "/home/opc/arepo/.venv/bin/python"
HOLD_LANE = "cpu"
HOLD_MIN_MEM_MB = 500
CRON_FILE_REL = "scripts/oracle/cb15_e_crontab.txt"
COLLECTOR_LOCK = "/tmp/arepo_cb15_e_live.lock"
LOG_DIR = "/home/opc/arepo_collector/logs"
NTP_SERVER = "pool.ntp.org"
NTP_MAX_OFFSET_S = 1.0
# ---- smoke (q0343) ------------------------------------------------------------------------------------------------------------------------------
SMOKE_NEEDS = ("guards_fixture_E", "e_part_hashes", "e_ge0_schema_fixture", "e_collector_before_pre", "e_gap_logging", "e_degradation", "e_lane_hold_flag", "e_gamma_paging", "e_books_100",
               "e_full_pass_bytes", "e_ntp_offset")
SMOKE_MAX_REQUESTS = 30
SMOKE_FULL_PASS_TOKENS = 1000
SMOKE_QUERY = "Governor 2026"


# =====================================================================================================================================================
# Clocks, grid, windows
# =====================================================================================================================================================


def ep(s: str) -> float:
    return c15.ep(s)


def is_night(t: float) -> bool:
    return ep(T15_E_ON) <= t < ep(T15_E_OFF)


def grid_due(t: float) -> float | None:
    """The scheduled pass slot of the minute containing ``t`` (UTC), or None: the 10-minute grid (hh:00, :10, ...) in ``[T15_E_PRE, T15_E_ON)`` and ``[T15_E_OFF, T15_E_END)``,
    every minute in ``[T15_E_ON, T15_E_OFF)``; nothing outside ``[T15_E_PRE, T15_E_END)``."""
    m = math.floor(t / MINUTE) * MINUTE
    if m < ep(T15_E_PRE) or m >= ep(T15_E_END):
        return None
    if is_night(m):
        return float(m)
    return float(m) if (m % GRID_S) == 0 else None


def scheduled_slots(lo: str = T15_E_PRE, hi: str = T15_E_END) -> list[float]:
    out = []
    t = ep(lo)
    while t < ep(hi):
        if grid_due(t) is not None:
            out.append(t)
        t += MINUTE
    return out


def t_a_of(t_close: float, offset_s: float = T_A_OFFSET_S) -> float:
    return float(t_close + offset_s)


def stratum_of(t_close: float) -> str:
    """The closing-hour stratum: the UTC hour of ``t_close`` (floor)."""
    return datetime.fromtimestamp(math.floor(t_close / HOUR) * HOUR, UTC).strftime("%Y-%m-%dT%HZ")


def offsets_on_grid(t_close: float) -> dict:
    """Every declared offset of ``t_a`` falls on a scheduled pass (poll closes are on the hour or half hour): t_a, t_a - 36 h, t_a - 24 h, t_a + 6 h, t_a + 12 h, t_a + 24 h."""
    ta = t_a_of(t_close)
    want = {"t_a": ta, "t_a-36h": ta - 36 * HOUR, "t_a-24h": ta - 24 * HOUR, "t_a+6h": ta + 6 * HOUR, "t_a+12h": ta + 12 * HOUR, "t_a+24h": ta + 24 * HOUR}
    return {k: grid_due(v) == v for k, v in want.items()}


# =====================================================================================================================================================
# Parsing (outcome fields discarded at parse), race classification
# =====================================================================================================================================================


def listish(v) -> list:
    return c15.c12.listish(v)


def state_of(title: str) -> str:
    """The state code named in a race title (full name first, longest first so "West Virginia" beats "Virginia"; then a ``XX-nn`` district code); '' = none or ambiguous."""
    t = str(title or "")
    hits = []
    for code, name in sorted(STATES.items(), key=lambda kv: -len(kv[1])):
        if re.search(rf"(?i)\b{re.escape(name)}\b", t):
            if not any(name.lower() in h[1].lower() for h in hits):
                hits.append((code, name))
    m = DISTRICT_RE.search(t)
    if m and m.group(1) in STATES:
        hits.append((m.group(1), STATES[m.group(1)]))
    codes = {c for c, _ in hits}
    return codes.pop() if len(codes) == 1 else ""


def district_of(title: str, state: str) -> str:
    m = DISTRICT_RE.search(str(title or ""))
    if m and m.group(1) == state:
        return "AL" if m.group(2) == "AL" else str(int(m.group(2)))
    m = DISTRICT_ORD_RE.search(str(title or ""))
    if m:
        return str(int(m.group(1)))
    if re.search(r"(?i)\bat-large\b", str(title or "")):
        return "AL"
    return ""


def office_of(title: str) -> str:
    t = str(title or "")
    if GOVERNOR_RE.search(t):
        return "governor"
    if SENATE_RE.search(t):
        return "senate"
    if HOUSE_RE.search(t):
        return "house"
    return ""


def parse_market(m: dict) -> dict | None:
    """Whitelisted Gamma market fields of a binary Yes/No member (``outcomePrices``, ``umaResolutionStatus(es)``, ``closedTime`` are never copied: the outcome guard at parse).
    ``liquidity`` is not kept here (it is read only by the tier snapshot at ``T15_E_pre``)."""
    m = c15.strip_forbidden(m)
    labels = [str(x).strip().lower() for x in listish(m.get("outcomes"))]
    toks = [str(x) for x in listish(m.get("clobTokenIds"))]
    if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2 or m.get("id") is None:
        return None
    yi = labels.index("yes")
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    return {"market_id": str(m["id"]), "question": str(m.get("question") or "")[:300], "item": str(m.get("groupItemTitle") or "")[:120], "condition_id": str(m.get("conditionId") or ""),
            "token_yes": toks[yi], "token_no": toks[1 - yi], "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "created_epoch": c15.parse_iso(m.get("createdAt")),
            "fee_rate": c15.num(fs.get("rate")), "active": bool(m.get("active", True))}


def parse_event(ev: dict) -> dict:
    """Whitelisted event fields: id, title, the general-election date FLAG of the description (the text is not stored), tags, series, negRisk, end date and parsed members."""
    ev = c15.strip_forbidden(ev)
    ser = [s for s in (ev.get("series") or []) if isinstance(s, dict) and s.get("id") is not None]
    return {"event_id": str(ev.get("id") or ""), "title": str(ev.get("title") or "")[:300], "general_date": bool(GENERAL_DATE_RE.search(str(ev.get("description") or ""))),
            "has_description": "description" in ev, "tags": sorted({str(t.get("id")) for t in (ev.get("tags") or []) if isinstance(t, dict) and t.get("id") is not None}),
            "series_id": str(ser[0]["id"]) if ser else "", "neg_risk": bool(ev.get("negRisk")), "end_epoch": c15.parse_iso(ev.get("endDate")),
            "members": [x for x in (parse_market(m) for m in (ev.get("markets") or []) if isinstance(m, dict)) if x is not None]}


def party_of_text(text: str) -> str:
    d, r = bool(DEM_RE.search(text or "")), bool(REP_RE.search(text or ""))
    return "D" if d and not r else ("R" if r and not d else "")


def classify_event(pe: dict) -> dict:
    """``kind``: ``race`` (a 2026 general-election Senate / Governor / House race of one state, description naming 3 November 2026; primaries, runoffs, nominee, margin and other-date
    events excluded), ``control`` (the national party-control market of the Senate or the House) or ``other``."""
    title = pe["title"]
    office = office_of(title)
    state = state_of(title)
    if CONTROL_RE.search(title) and not state and office in ("senate", "house") and re.search(r"2026", title):
        return {"kind": "control", "office": office, "state": "", "district": "", "excluded": ""}
    if not office or not state:
        return {"kind": "other", "office": office, "state": state, "district": "", "excluded": "no office/state"}
    if RACE_EXCLUDE_RE.search(title):
        return {"kind": "other", "office": office, "state": state, "district": "", "excluded": "primary/runoff/other object"}
    if not pe["general_date"]:
        return {"kind": "other", "office": office, "state": state, "district": "", "excluded": "description does not name 3 November 2026"}
    district = district_of(title, state) if office == "house" else ""
    if office == "house" and not district:
        return {"kind": "other", "office": office, "state": state, "district": "", "excluded": "house race without a district"}
    return {"kind": "race", "office": office, "state": state, "district": district, "excluded": ""}


def race_id_of(state: str, office: str, district: str) -> str:
    return f"{state}|{office}|{district}"


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z ]", "", re.sub(r"\s+", " ", str(s or "").lower())).strip()


def member_party(member: dict, race_id: str, party_map: dict | None) -> tuple[str, str]:
    """(party, source) of a member: a party member / market by its text ("Democrat", "Democratic" / "Republican", "GOP"), else a candidate member by the GE0 party map."""
    p = party_of_text(member["item"] or member["question"])
    if p:
        return p, "party_text"
    cands = ((party_map or {}).get("races") or {}).get(race_id, {}).get("candidates") or {}
    nm = norm_name(member["item"] or "")
    if nm and nm in cands:
        return str(cands[nm]), "party_map"
    return "", ""


def trade_market(pe: dict, race_id: str, party_map: dict | None) -> dict:
    """The frozen trade-market rule: (a) a party member / market naming "Democrat" / "Democratic"; else (b) the candidate member whose party is D in the GE0 party map. D-terms
    price = the D YES token's mid; the predicted-side tokens are the D YES (s = +1) and the D NO (s = -1) tokens. Returns ``{"market", "source", "members_party"}``."""
    members = pe["members"]
    parties = {m["market_id"]: member_party(m, race_id, party_map) for m in members}
    d_text = [m for m in members if parties[m["market_id"]] == ("D", "party_text")]
    if len(d_text) == 1:
        return {"market": d_text[0], "source": "party_market" if len(members) == 1 else "party_member", "members_party": {k: v[0] for k, v in parties.items()}}
    if len(d_text) > 1:  # several members name Democrat(ic): ambiguous, excluded and counted (round 2 fix 6)
        return {"market": None, "source": "ambiguous D party members", "members_party": {k: v[0] for k, v in parties.items()}}
    d_map = [m for m in members if parties[m["market_id"]] == ("D", "party_map")]
    if len(d_map) == 1:
        return {"market": d_map[0], "source": "party_map", "members_party": {k: v[0] for k, v in parties.items()}}
    return {"market": None, "source": "no D trade market" if not d_map else "ambiguous D candidates", "members_party": {k: v[0] for k, v in parties.items()}}


def two_party(members: list[dict], members_party: dict, mids: dict[str, float]) -> tuple[bool, str]:
    """The two highest-priced members (YES mid at the q0344 read) are one D and one R. A single-member party market (YES = D) has no second member: it passes with the label
    ``single_party_market`` (reported). A member without a read ranks last."""
    if len(members) == 1:
        return True, "single_party_market"
    ranked = sorted(members, key=lambda m: -(mids.get(m["token_yes"]) if math.isfinite(mids.get(m["token_yes"], math.nan)) else -1.0))
    top = {members_party.get(m["market_id"], "") for m in ranked[:2]}
    return (top == {"D", "R"}), ("two_party" if top == {"D", "R"} else "not two-party")


def control_member(pe: dict) -> dict | None:
    """The D member of a national control event (or a single D market)."""
    ds = [m for m in pe["members"] if party_of_text(m["item"] or m["question"]) == "D"]
    return ds[0] if len(ds) == 1 else None


# =====================================================================================================================================================
# Gamma frame (q0341): search paging, event lookups, politics-tag completeness walk
# =====================================================================================================================================================


def search_all(lim, term: str, *, status: str = SEARCH_STATUS, page_limit: int = SEARCH_LIMIT, max_pages: int = SEARCH_MAX_PAGES) -> tuple[list[dict], dict]:
    """Gamma ``public-search`` events for one term, active, paged until ``pagination.hasMore`` is false. More pages than ``max_pages`` is a refusal (never a silent truncation)."""
    out: list[dict] = []
    info = {"pages": 0, "total": None}
    for page in range(1, max_pages + 1):
        st, data = lim.get(c15.GAMMA_SEARCH, {"q": term, "events_status": status, "limit_per_type": page_limit, "page": page})
        if st != 200 or not isinstance(data, dict):
            raise ApiError(f"public-search status {st}")
        info["pages"] += 1
        out.extend(e for e in (data.get("events") or []) if isinstance(e, dict))
        pg = data.get("pagination") or {}
        info["total"] = pg.get("totalResults", info["total"])
        if not pg.get("hasMore"):
            return out, info
    raise Refused(f"public-search q={term!r} still has more pages after {max_pages}")


def lookup_events(lim, ids: list[str], *, per_request: int = c15.LOOKUP_PER_REQUEST) -> tuple[dict[str, dict], int]:
    """Full Gamma events by id (<= 50 ids per request; active ones, then without the filter)."""
    found: dict[str, dict] = {}
    n = 0
    want_all = [str(i) for i in ids]
    for i in range(0, len(want_all), per_request):
        chunk = want_all[i:i + per_request]
        st, data = lim.get(c15.GAMMA_EVENTS, {"id": chunk, "limit": per_request})
        n += 1
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"gamma events lookup status {st}")
        for e in data:
            if isinstance(e, dict) and str(e.get("id")) in chunk:
                found[str(e["id"])] = e
    return found, n


def walk_windows(lo: str = WALK_END_WINDOW[0], hi: str = WALK_END_WINDOW[1], step_d: int = WALK_STEP_D) -> list[tuple[float, float]]:
    a, b = ep(lo), ep(hi)
    out = []
    while a < b:
        out.append((a, min(a + step_d * DAY, b)))
        a += step_d * DAY
    return out


def walk_politics(lim, *, page: int = c15.GAMMA_PAGE, offset_cap: int = c15.GAMMA_OFFSET_CAP, max_req: int = WALK_MAX_REQ) -> tuple[list[dict], int]:
    """Active Gamma events of the politics tag (id 2) ending in ``[2026-11-03, 2027-01-31]``, in weekly end-date windows, each paged to the offset cap; a capped window or more than
    ``max_req`` requests is a refusal (not a silent truncation)."""
    out: list[dict] = []
    n = 0
    for a, b in walk_windows():
        for off in range(0, offset_cap + page, page):
            if n >= max_req:
                raise Refused(f"politics-tag walk exceeds {max_req} requests")
            st, data = lim.get(c15.GAMMA_EVENTS, {"tag_id": WALK_TAG_ID, "active": "true", "closed": "false", "end_date_min": cm.iso(a), "end_date_max": cm.iso(b - 1),
                                                  "order": "id", "ascending": "true", "limit": page, "offset": off})
            n += 1
            if st != 200 or not isinstance(data, list):
                raise ApiError(f"gamma events status {st}")
            out.extend(x for x in data if isinstance(x, dict))
            if len(data) < page:
                break
        else:
            raise Refused(f"politics walk window {cm.iso(a)} is capped at the offset limit")
    return out, n


def census_e(lim) -> tuple[list[list], dict]:
    """q0341, counts only: the frozen queries (active, to ``hasMore = false``), event lookups for events missing the description or members, race classification, member structure,
    party / candidate market type, national control markets, the politics-tag completeness walk. No price, no outcome, no liquidity."""
    r0 = lim.requests
    evs: dict[str, dict] = {}
    per_query = {}
    for q in QUERIES:
        got, info = search_all(lim, q)
        per_query[q] = {"pages": info["pages"], "total": info["total"], "events": len(got)}
        for e in got:
            if e.get("id") is not None:
                evs.setdefault(str(e["id"]), e)
    need = [i for i, e in evs.items() if "description" not in e or not e.get("markets")]
    if need:
        if len(need) > EVENT_LOOKUP_MAX_REQ * c15.LOOKUP_PER_REQUEST:
            raise Refused("event lookups exceed the declared budget")
        found, _ = lookup_events(lim, need)
        evs.update(found)
    rows: list[list] = []
    frame_races: set[str] = set()
    controls: dict[str, list[str]] = {"senate": [], "house": []}
    counts: dict[str, dict] = {}
    by_state: dict[str, int] = {}
    excluded: dict[str, int] = {}
    for eid in sorted(evs):
        pe = parse_event(evs[eid])
        cl = classify_event(pe)
        trade = trade_market(pe, race_id_of(cl["state"], cl["office"], cl["district"]), None) if cl["kind"] == "race" else {"source": "", "market": None}
        ttype = trade["source"] if cl["kind"] == "race" else ""
        if cl["kind"] == "race" and trade["market"] is None and len(pe["members"]) > 1:
            ttype = "candidate (party map needed)"
        chamber = ""
        if cl["kind"] == "control":
            cm_ = control_member(pe)
            chamber = cl["office"]
            if cm_ is not None:
                controls[chamber].append(cm_["market_id"])
        if cl["kind"] == "race":
            frame_races.add(eid)
            c = counts.setdefault(cl["office"], {"events": 0, "members": 0})
            c["events"] += 1
            c["members"] += len(pe["members"])
            by_state[cl["state"]] = by_state.get(cl["state"], 0) + 1
        elif cl["excluded"]:
            excluded[cl["excluded"]] = excluded.get(cl["excluded"], 0) + 1
        rows.append([eid, cl["kind"], cl["office"], cl["state"], cl["district"], int(pe["general_date"]), cl["excluded"], len(pe["members"]), ttype, chamber,
                     ";".join(sorted({m["neg_risk_market_id"] for m in pe["members"] if m["neg_risk_market_id"]})), pe["series_id"], ";".join(m["market_id"] for m in pe["members"])])
    walk, n_walk = walk_politics(lim)
    walk_races = set()
    for e in walk:
        pe = parse_event(e)
        if classify_event(pe)["kind"] == "race":
            walk_races.add(pe["event_id"])
    inside = len(walk_races & frame_races)
    share = inside / len(walk_races) if walk_races else 1.0
    rep = {"counts_only": True, "queries": per_query, "events_seen": len(evs), "race_events": len(frame_races), "by_office": counts, "by_state": dict(sorted(by_state.items())),
           "excluded": excluded, "controls": {k: len(v) for k, v in controls.items()}, "control_market_ids": controls,
           "completeness": {"walk_requests": n_walk, "walk_events": len(walk), "walk_race_events": len(walk_races), "inside_frame": inside, "share": share, "min": COMPLETENESS_MIN,
                            "pass": bool(share >= COMPLETENESS_MIN)},
           "requests": lim.requests - r0}
    if rep["requests"] > CENSUS_MAX_REQ:
        rep["over_budget"] = True
    return rows, rep


# =====================================================================================================================================================
# GE0: committed tables (schemas, archive manifest, effective signs, cross-table)
# =====================================================================================================================================================


def ge0_dir(repo_root: Path | None = None) -> Path:
    from . import provenance  # noqa: PLC0415

    return (Path(repo_root) if repo_root is not None else provenance.REPO_ROOT) / GE0_DIR_REL


def manifest_shas(manifest: dict) -> set[str]:
    return {str(f.get("sha256")) for f in (manifest.get("files") or []) if isinstance(f, dict) and f.get("sha256")}


def validate_manifest(manifest: dict) -> list[str]:
    """Every archived source has a URL, a UTC fetch time, a sha256 and a file name, and none is a 2026 poll, forecast, market page or 2026 news item."""
    errs = []
    if manifest.get("version") != GE0_VERSIONS["source_manifest"]:
        errs.append("source_manifest version")
    for f in manifest.get("files") or []:
        if not isinstance(f, dict) or not all(f.get(k) for k in ("sha256", "url", "fetched_utc", "file")):
            errs.append(f"manifest entry incomplete: {str(f)[:80]}")
        elif str(f.get("kind") or "") in GE0_FORBIDDEN_SOURCE_KINDS:
            errs.append(f"forbidden source kind {f.get('kind')} ({f.get('file')})")
    return errs


def cited(entry: dict, shas: set[str]) -> bool:
    c = [str(x) for x in (entry.get("citations") or [])]
    return bool(c) and all(x in shas for x in c)


def effective_sign(entry: dict | None, shas: set[str]) -> int:
    """The sign E uses: +1 / -1 only if both compiler passes agree on it, the vote-mode order and BOTH archived years agree (``dir_2022``, ``dir_2024`` equal the sign), every input
    cites an archived source (sha256 in the manifest) and the read-only audit did not mark it unsupported; else 0 (a state without an archived source for every input gets s = 0)."""
    if not isinstance(entry, dict):
        return 0
    s = entry.get("s")
    if s not in (1, -1):
        return 0
    if entry.get("pass_a") != s or entry.get("pass_b") != s:
        return 0
    if entry.get("mode_order") != s or any(entry.get(f"dir_{y}") != s for y in SIGN_YEARS):
        return 0
    if entry.get("audit") != "supported":
        return 0
    for part in ("mode_order_citations", *(f"dir_{y}_citations" for y in SIGN_YEARS)):
        if not cited({"citations": entry.get(part)}, shas):
            return 0
    return int(s)


def validate_poll_close(doc: dict, shas: set[str]) -> tuple[dict[str, float], list[str]]:
    """``t_close`` per state: the latest official poll-closing time (UTC), on the hour or half hour, in the declared range, citing an archived source; else the state is unusable."""
    lo, hi = ep(POLL_CLOSE_RANGE[0]), ep(POLL_CLOSE_RANGE[1])
    out, errs = {}, []
    if doc.get("version") != GE0_VERSIONS["poll_close"]:
        errs.append("poll_close version")
    for st, e in sorted((doc.get("states") or {}).items()):
        t = c15.parse_iso((e or {}).get("t_close_utc"))
        ok = math.isfinite(t) and lo <= t <= hi and (t % 1800) == 0 and cited(e or {}, shas)
        if ok:
            out[st] = t
        else:
            errs.append(f"poll close {st} unusable")
    return out, errs


def ge0_bundle_sha256(shas: dict[str, str]) -> str:
    """ONE pin for the five GE0 files: sha256 of the sorted JSON of their per-file sha256s (``ge0-check`` prints it; the queue drafts carry it as ``--ge0-sha256``)."""
    if set(shas) != set(GE0_FILES):
        raise Refused(f"GE0 bundle needs exactly the files {sorted(GE0_FILES)}")
    return hashlib.sha256(json.dumps({k: shas[k] for k in sorted(shas)}, sort_keys=True).encode()).hexdigest()


def require_ge0_pin(pin: str | None, bundle: str) -> None:
    """The GE0 bundle sha256 is a MANDATORY pin (the coordinator fills it in the queue draft from ``ge0-check`` once GE0 is committed and audited)."""
    if not pin or pin == c15.PIN_UNSET:
        raise Refused(f"the GE0 bundle sha256 pin (--ge0-sha256) is unset ({c15.PIN_UNSET}); GE0 is committed and audited before this job")
    if pin != bundle:
        raise Refused(f"GE0 bundle sha256 {bundle[:12]} != pinned {str(pin)[:12]}: the GE0 files changed since the pin")


def ge0_file_docs(d: Path, *, require_committed: bool = True, names: Iterable[str] = tuple(GE0_FILES)) -> tuple[dict, dict]:
    docs, shas = {}, {}
    for k in names:
        name = GE0_FILES[k]
        p = Path(d) / name
        if not p.is_file():
            raise Refused(f"GE0 file {p} is absent: GE0 is committed before the pre-gate and the freeze")
        if require_committed:
            from . import cb1_history  # noqa: PLC0415

            if not cb1_history.spec_committed(p):
                raise Refused(f"GE0 file {p} is not committed (or differs from HEAD)")
        try:
            docs[k] = json.loads(p.read_text())
        except ValueError as exc:
            raise Refused(f"GE0 file {p} unreadable") from exc
        if docs[k].get("version") != GE0_VERSIONS[k]:
            raise Refused(f"GE0 file {name} version {docs[k].get('version')!r} != {GE0_VERSIONS[k]!r}")
        shas[k] = c15.sha256_file(p)
    return docs, shas


def cited_party_map(pmap: dict, shas: set[str]) -> tuple[dict, list[str]]:
    """The party map E uses: only race entries citing archived sources (every citation's sha256 in the manifest); candidate names normalised. Uncited races are dropped (listed)."""
    races, dropped = {}, []
    for rid, e in sorted((pmap.get("races") or {}).items()):
        if not isinstance(e, dict) or not cited(e, shas):
            dropped.append(rid)
            continue
        races[rid] = {"candidates": {norm_name(k): str(v) for k, v in (e.get("candidates") or {}).items() if str(v) in ("D", "R")}}
    return {"version": pmap.get("version"), "races": races}, dropped


def build_cross_table(gdir: Path, *, require_committed: bool = False) -> dict:
    """Repo step (``ge0-cross-table``): the cross-table document of the sign and poll-close tables in ``gdir`` (no prices)."""
    docs, _ = ge0_file_docs(gdir, require_committed=require_committed, names=("sign_table", "poll_close", "source_manifest"))
    msh = manifest_shas(docs["source_manifest"])
    states = docs["sign_table"].get("states") or {}
    signs = {st: effective_sign(states.get(st), msh) for st in STATES}
    closes, _ = validate_poll_close(docs["poll_close"], msh)
    return cross_table_doc(signs, closes)


def load_ge0(repo_root: Path | None = None, *, require_committed: bool = True, gdir: Path | None = None, pin_sha256: str | None = None, require_pin: bool = True) -> dict:
    """The committed GE0 files (refused if any is absent or not committed, or if the bundle sha256 differs from the MANDATORY pin). Returns the tables, the effective signs, the poll
    closes, the cited party map, the cross-table, each file's sha256, the bundle sha256 and validation notes. Never fetches."""
    d = Path(gdir) if gdir is not None else ge0_dir(repo_root)
    docs, shas = ge0_file_docs(d, require_committed=require_committed)
    bundle = ge0_bundle_sha256(shas)
    if require_pin:
        require_ge0_pin(pin_sha256, bundle)
    errs = validate_manifest(docs["source_manifest"])
    if errs:
        raise Refused(f"GE0 source manifest invalid: {errs[:5]}")
    msh = manifest_shas(docs["source_manifest"])
    states = docs["sign_table"].get("states") or {}
    missing = sorted(set(STATES) - set(states))
    if missing:
        raise Refused(f"GE0 sign table lacks jurisdictions {missing} (all 50 states + DC are compiled)")
    signs = {st: effective_sign(states.get(st), msh) for st in STATES}
    closes, cerrs = validate_poll_close(docs["poll_close"], msh)
    cross = cross_table(signs, closes)
    if (docs["cross_table"].get("all_51") or {}) != cross:
        raise Refused("GE0 cross_table.json differs from the cross-table of the committed sign and poll-close tables (regenerate with `ge0-cross-table`)")
    pmap, pdropped = cited_party_map(docs["party_map"], msh)
    return {"signs": signs, "closes": closes, "party_map": pmap, "party_map_uncited": pdropped, "cross_table": cross, "sha256": shas, "bundle_sha256": bundle, "notes": cerrs,
            "kappa": docs["sign_table"].get("kappa"), "dir": str(d)}


def cross_table(signs: dict[str, int], closes: dict[str, float], states: Iterable[str] | None = None) -> dict:
    """Counts of s = +1, -1, 0 by closing-hour stratum (no prices), for the given states (default all 51); a state without a usable poll close is under ``no_close``."""
    out: dict[str, dict[str, int]] = {}
    for st in sorted(states if states is not None else STATES):
        h = stratum_of(closes[st]) if st in closes else "no_close"
        c = out.setdefault(h, {"+1": 0, "-1": 0, "0": 0})
        c[{1: "+1", -1: "-1"}.get(int(signs.get(st, 0)), "0")] += 1
    return dict(sorted(out.items()))


def cross_table_doc(signs: dict[str, int], closes: dict[str, float]) -> dict:
    return {"version": GE0_VERSIONS["cross_table"], "all_51": cross_table(signs, closes), "rule": "counts of effective signs by the UTC hour of the last poll close; no prices"}


def verify_archive(manifest: dict, archive_root: Path) -> dict:
    """Repo step (``ge0-check``, where the archive lives): every manifest file exists under the archive and hashes to its sha256."""
    bad = []
    for f in manifest.get("files") or []:
        p = Path(archive_root) / str(f.get("file"))
        if not p.is_file() or c15.sha256_file(p) != f.get("sha256"):
            bad.append(str(f.get("file")))
    return {"n_files": len(manifest.get("files") or []), "bad": bad, "pass": not bad}


# =====================================================================================================================================================
# Books: POST /books, parse, passes, storage, gaps
# =====================================================================================================================================================


def books_poster(timeout: float = 20.0):
    """``post(body) -> (status, bytes, headers)`` for the keyless CLOB ``POST /books``; a transport error is status 599."""
    import httpx  # noqa: PLC0415

    client = httpx.Client(timeout=timeout, headers={"User-Agent": c15.USER_AGENT, "Content-Type": "application/json"})

    def post(body: list[dict]) -> tuple[int, bytes, dict]:
        try:
            r = client.post(CLOB_BOOKS, json=body)
        except httpx.HTTPError as exc:
            return 599, b"", {"error": type(exc).__name__}
        return r.status_code, r.content, dict(r.headers)

    return post


def _levels(side, n: int, *, reverse: bool) -> list[list[float]]:
    out = []
    for x in side or []:
        if isinstance(x, dict):
            p, s = c15.num(x.get("price")), c15.num(x.get("size"))
            if math.isfinite(p) and math.isfinite(s) and s > 0:
                out.append([p, s])
    out.sort(key=lambda v: -v[0] if reverse else v[0])
    return out[:n]


def parse_book(b: dict, levels: int = BOOK_LEVELS) -> dict | None:
    """Whitelisted fields of one ``/books`` entry: asset id, market, venue timestamp, top ``levels`` per side (price, size; bids high to low, asks low to high), tick size, neg risk,
    last trade price. ``hash`` is discarded."""
    if not isinstance(b, dict) or not b.get("asset_id"):
        return None
    ts = c15.num(b.get("timestamp"))
    return {"asset_id": str(b["asset_id"]), "market": str(b.get("market") or ""), "ts_venue": ts / 1000.0 if ts > 1e12 else ts, "bids": _levels(b.get("bids"), levels, reverse=True),
            "asks": _levels(b.get("asks"), levels, reverse=False), "tick": c15.num(b.get("tick_size")), "neg_risk": bool(b.get("neg_risk")), "ltp": c15.num(b.get("last_trade_price"))}


def books_batch(post, tokens: list[str], *, sleep=time.sleep, retry_s: float = BATCH_RETRY_S) -> tuple[list[dict] | None, str]:
    """One ``POST /books`` of <= 100 tokens with ONE quick retry; (raw list, '') or (None, error). Never raises (the caller logs a gap)."""
    if len(tokens) > BOOKS_BATCH:
        raise Refused(f"a /books batch holds at most {BOOKS_BATCH} tokens")
    body = [{"token_id": t} for t in tokens]
    err = ""
    for attempt in range(2):
        try:
            st, raw, _ = post(body)
        except Exception as exc:  # noqa: BLE001  (a transport failure is a gap, never a crash on the night)
            st, raw, err = 599, b"", type(exc).__name__
        if st == 200:
            try:
                data = json.loads(raw)
            except ValueError:
                data, err = None, "unparseable"
            if isinstance(data, list):
                return data, ""
        err = err or f"status {st}"
        if attempt == 0:
            sleep(retry_s)
    return None, err


def run_pass(post, tokens: list[str], slot: float, *, levels: int = BOOK_LEVELS, clock=time.time, sleep=time.sleep, rps: float = BOOKS_RPS) -> tuple[list[dict], list[dict]]:
    """One pass: batches of <= 100 tokens; each parsed book is stamped with the slot and its batch's RECEIPT time (host clock after the response). Returns (records, gaps);
    a failed batch is a gap (its tokens are 'unavailable (gap)' for that slot), a token absent from a successful response is a gap too."""
    recs, gaps = [], []
    gap_s = 1.0 / rps
    toks = sorted(set(tokens))
    for i in range(0, len(toks), BOOKS_BATCH):
        if i:
            sleep(gap_s)
        batch = toks[i:i + BOOKS_BATCH]
        data, err = books_batch(post, batch, sleep=sleep)
        receipt = clock()
        if data is None:
            gaps.append({"slot": slot, "batch": i // BOOKS_BATCH, "n_tokens": len(batch), "why": err, "receipt": receipt})
            continue
        got = set()
        for b in data:
            r = parse_book(b, levels)
            if r is not None and r["asset_id"] in batch:
                got.add(r["asset_id"])
                recs.append({**r, "slot": slot, "receipt": receipt, "batch": i // BOOKS_BATCH})
        miss = [t for t in batch if t not in got]
        if miss:
            gaps.append({"slot": slot, "batch": i // BOOKS_BATCH, "n_tokens": len(miss), "why": ABSENT_WHY, "receipt": receipt, "tokens": miss})  # every token: closure evidence
    return recs, gaps


def pass_bytes(recs: list[dict]) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in recs:
            gz.write((json.dumps(r, sort_keys=True, default=float) + "\n").encode())
    return buf.getvalue()


def pass_file(live_dir: Path, slot: float) -> Path:
    return Path(live_dir) / LIVE_FILES["books_dir"] / f"{datetime.fromtimestamp(slot, UTC):%Y%m%dT%H%M}.jsonl.gz"


def collector_cap_gb(bytes_per_pass: float, n_passes: int | None = None) -> float:
    """q0345's cap (round 1 item 8): 3 x (smoke-measured stored bytes per pass x scheduled passes), at least 1.0 GB."""
    n = len(scheduled_slots()) if n_passes is None else int(n_passes)
    return float(max(CAP_MIN_GB, CAP_MARGIN * float(bytes_per_pass) * n / 1024**3))


def storage_decision(used_bytes: float, recent_pass_bytes: list[float], remaining_passes: int, cap_bytes: float, free_bytes: float) -> dict:
    """Inside the window there is no exit 75: if ``used + mean(recent) x remaining > cap`` the collector DEGRADES to the top level per side (logged); it STOPS only if root free disk
    falls below 2 GB (host protection; the remaining units are 'unavailable', counted)."""
    per = float(np.mean(recent_pass_bytes[-PROJECTION_WINDOW:])) if recent_pass_bytes else 0.0
    proj = float(used_bytes + per * remaining_passes)
    stop = bool(free_bytes < HOST_PROTECT_FREE_GB * 1024**3)
    return {"projected_bytes": proj, "cap_bytes": float(cap_bytes), "degrade": bool(proj > cap_bytes), "stop": stop, "free_bytes": float(free_bytes)}


def dir_bytes(d: Path) -> int:
    return sum(f.stat().st_size for f in Path(d).rglob("*") if f.is_file()) if Path(d).exists() else 0


def pre_night_disk_check(data_dumps_bytes: float, cap_gb: float, free_bytes: float, *, data_dumps_cap_gb: float = c15.DATA_DUMPS_CAP_GB) -> dict:
    """The 2026-11-02 pre-night check: data-dumps + cap <= 40 GiB and root free >= cap + 10 GB; a failure is resolved by the coordinator before ``T15_E_on`` without deleting data."""
    a = data_dumps_bytes / 1024**3 + cap_gb <= data_dumps_cap_gb
    b = free_bytes / 1024**3 >= cap_gb + PRE_NIGHT_FREE_MARGIN_GB
    return {"data_dumps_ok": bool(a), "free_ok": bool(b), "pass": bool(a and b), "cap_gb": cap_gb}


# =====================================================================================================================================================
# The cpu-lane hold: committed cron lines (pause / resume) and the collector line
# =====================================================================================================================================================


def _cron_at(iso_: str) -> str:
    d = datetime.fromisoformat(iso_.replace("Z", "+00:00"))
    return f"{d.minute} {d.hour} {d.day} {d.month} *"


def cron_lines() -> list[str]:
    """The committed crontab block (``scripts/oracle/cb15_e_crontab.txt``): the minute collector under flock (nice 5; it idles before ``T15_E_pre`` and closes after
    ``T15_E_end``), the dry-run hold / release on 2026-11-02 12:00Z / 12:10Z and the ``cpu`` hold for ``[2026-11-03T21:00Z, 2026-11-04T22:00Z)``. Year-guarded (cron has no year)."""
    guard = '[ "$(date -u +\\%Y)" = 2026 ] &&'
    q = f"{HOST_PY} {QUEUE_WORKER}"
    log = f">> {LOG_DIR}/cb15-e-hold.log 2>&1"
    return [
        "# --- CB15-E election night (docs/research_lab/CREATIVE_BATCH_15.md sections 1.2, 2.8, 11; q0345). Install after the part-E freeze, by 2026-11-02T00:00Z; remove after 2026-11-06T00:00Z. ---",
        f"# DEPLOY FREEZE {DEPLOY_FREEZE}.",
        f"* * * * * cd /home/opc/arepo/backend && flock -n {COLLECTOR_LOCK} nice -n {COLLECTOR_NICE} {HOST_PY} scripts/run_cb15.py e-live --rules ../docs/research_lab/seals/cb15_rules.json --not-before {T15_E_PRE} --until {T15_E_END} --disk-cap-gb freeze --data-dumps-cap-gb 40 --no-exit75-in-window >> {LOG_DIR}/cb15-e-live.log 2>&1",
        f"{_cron_at(T15_CPU_DRY_RUN[0])} {guard} {q} hold-lane {HOLD_LANE} {HOLD_MIN_MEM_MB} {log}  # dry run (verify a held job is not promoted)",
        f"{_cron_at(T15_CPU_DRY_RUN[1])} {guard} {q} release-lane {log}  # dry run (verify promotion)",
        f"{_cron_at(T15_CPU_HOLD_PLACE)} {guard} {q} hold-lane {HOLD_LANE} {HOLD_MIN_MEM_MB} {log}  # placed 6 h before {T15_CPU_HOLD[0]}",
        f"*/5 * * * * cd /home/opc/arepo/backend && {HOST_PY} scripts/run_cb15.py e-watchdog >> {LOG_DIR}/cb15-e-watchdog.log 2>&1  # heartbeat age + heavy cpu job alert (notify)",
        f"{_cron_at(T15_CPU_HOLD[1])} {guard} {q} release-lane {log}",
        "# --- end CB15-E ---",
    ]


def cron_text() -> str:
    return "\n".join(cron_lines()) + "\n"


# =====================================================================================================================================================
# NTP offset (smoke)
# =====================================================================================================================================================


def ntp_offset(server: str = NTP_SERVER, timeout: float = 3.0, clock=time.time) -> float:
    """SNTP clock offset (server - host) in seconds."""
    pkt = b"\x1b" + 47 * b"\0"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        t0 = clock()
        s.sendto(pkt, (server, 123))
        data, _ = s.recvfrom(48)
        t3 = clock()
    secs, frac = struct.unpack("!II", data[40:48])
    t_srv = secs - 2208988800 + frac / 2**32
    return float(t_srv - (t0 + t3) / 2.0)


# =====================================================================================================================================================
# Collector (q0345)
# =====================================================================================================================================================


def read_race_map(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def collector_tokens(race_map: list[dict]) -> list[str]:
    """The D YES and D NO tokens of every frozen trade and control market."""
    return sorted({t for r in race_map for t in (r["token_d_yes"], r["token_d_no"]) if t})


def e_live(hist_root: Path, *, race_map_path: Path, post, lim, now: float, cap_gb: float, rules_sha: str, clock=time.time, sleep=time.sleep, free_fn=None,
           data_dumps: Path | None = None) -> dict:
    """q0345, ONE invocation (cron every minute under flock). Before ``T15_E_pre``: idle (exit 0, heartbeat). At or after ``T15_E_end``: ``e_live_window_closed``. Inside: if this
    minute is a scheduled slot not yet done, run one pass (all tokens; degraded to the top level if the storage projection exceeds the cap; stop writing only below 2 GB root free),
    log gaps (failed batches, missing tokens, missed slots), take the tier snapshot (Gamma ``liquidity``) at the first pass and refresh the Gamma map every 6 h. NEVER exit 75 here."""
    import shutil  # noqa: PLC0415

    live_dir = c15.require_output_root(Path(hist_root) / RUN)
    live_dir.mkdir(parents=True, exist_ok=True)
    if now < ep(T15_E_PRE):
        cm.write_json_atomic(live_dir / LIVE_FILES["heartbeat"], {"epoch": now, "utc": cm.iso(now), "status": "before T15_E_pre"})
        return {"status": "e_live_idle", "complete": False, "reason": f"before T15_E_pre {T15_E_PRE}"}
    if now >= ep(T15_E_END):
        return {"status": LIVE_STATUS_CLOSED, "complete": True}
    sp = live_dir / LIVE_FILES["state"]
    state = json.loads(sp.read_text()) if sp.is_file() else {"done": [], "last_slot": None, "degraded": False, "stopped": False, "pass_bytes": [], "last_refresh": None}
    races = read_race_map(race_map_path)
    tokens = collector_tokens(races)
    slot = grid_due(now)
    out = {"status": "e_live_polled", "complete": False, "slot": None, "records": 0, "gaps": 0, "degraded": state["degraded"], "stopped": state["stopped"]}
    gp = live_dir / LIVE_FILES["gaps"]
    if slot is not None and slot not in set(state["done"]):
        last = state.get("last_slot")
        if last is not None:  # missed slots between the last done slot and this one are gaps (never back-filled)
            missed = [s for s in scheduled_slots(cm.iso(last + MINUTE), cm.iso(slot)) if s > last]
            for s in missed:
                c15.jsonl_append(gp, {"slot": s, "why": "missed slot (no invocation)", "receipt": now, "n_tokens": len(tokens)})
        free = (free_fn or (lambda q: shutil.disk_usage(q).free))(live_dir)
        used = dir_bytes(live_dir / LIVE_FILES["books_dir"])
        remaining = len([s for s in scheduled_slots() if s >= slot])
        dec = storage_decision(used, state["pass_bytes"], remaining, cap_gb * 1024**3, free)
        if dec["degrade"] and not state["degraded"]:
            state["degraded"] = True
            c15.jsonl_append(live_dir / LIVE_FILES["storage"], {"slot": slot, "event": "degrade to top level per side", **dec})
        if dec["stop"]:
            state["stopped"] = True
            c15.jsonl_append(live_dir / LIVE_FILES["storage"], {"slot": slot, "event": "stopped: root free below 2 GB (host protection)", **dec})
            c15.jsonl_append(gp, {"slot": slot, "why": "host protection stop", "receipt": now, "n_tokens": len(tokens)})
        else:
            if state["stopped"]:
                state["stopped"] = False
            recs, gaps = run_pass(post, tokens, slot, levels=BOOK_LEVELS_DEGRADED if state["degraded"] else BOOK_LEVELS, clock=clock, sleep=sleep)
            data = pass_bytes(recs)
            pf = pass_file(live_dir, slot)
            pf.parent.mkdir(parents=True, exist_ok=True)
            pf.write_bytes(data)
            state["pass_bytes"] = (state["pass_bytes"] + [len(data)])[-PROJECTION_WINDOW:]
            for g in gaps:
                c15.jsonl_append(gp, g)
            c15.jsonl_append(live_dir / LIVE_FILES["passes"], {"slot": slot, "n_records": len(recs), "n_gaps": len(gaps), "bytes": len(data), "levels": BOOK_LEVELS_DEGRADED if state["degraded"] else BOOK_LEVELS,
                                                              "receipt_end": clock()})
            out.update(records=len(recs), gaps=len(gaps))
        state["done"] = sorted(set(state["done"]) | {slot})
        state["last_slot"] = slot
        out["slot"] = cm.iso(slot)
    cm.write_json_atomic(sp, state)  # the pass is recorded before any Gamma call
    tp = live_dir / LIVE_FILES["tier"]
    if lim is not None and not tp.is_file() and now < ep(T15_E_ON) and (state.get("last_tier_try") is None or now - float(state["last_tier_try"]) >= TIER_RETRY_S):
        state["last_tier_try"] = now  # the attempt is marked first (round 2 fix 2); tiers only in [T15_E_pre, T15_E_on) (fix 5)
        cm.write_json_atomic(sp, state)
        try:
            cm.write_json_atomic(tp, tier_snapshot(lim, races, now))
        except (ApiError, RuntimeError) as exc:
            c15.jsonl_append(gp, {"slot": slot, "why": f"tier snapshot failed: {str(exc)[:80]}", "receipt": now, "n_tokens": 0})
    if lim is not None and (state.get("last_refresh") is None or now - float(state["last_refresh"]) >= MAP_REFRESH_S):
        state["last_refresh"] = now  # marked before the attempt: a failed refresh waits 6 h, never retried every minute
        cm.write_json_atomic(sp, state)
        try:
            refresh_map(lim, races, live_dir, now)
        except (ApiError, RuntimeError) as exc:
            c15.jsonl_append(gp, {"slot": slot, "why": f"map refresh failed: {str(exc)[:80]}", "receipt": now, "n_tokens": 0})
    cm.write_json_atomic(sp, state)
    cm.write_json_atomic(live_dir / LIVE_FILES["heartbeat"], {"epoch": now, "utc": cm.iso(now), "status": "collecting", "rules_sha256": rules_sha})
    out.update(degraded=state["degraded"], stopped=state["stopped"])
    return out


def gamma_markets(lim, ids: list[str], *, max_retries: int = 0) -> dict[str, dict]:
    """Gamma markets by id. The collector calls it with NO retries (a short-timeout transport is the runner's): an outage costs one failed call, never a stalled invocation."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), c15.LOOKUP_PER_REQUEST):
        chunk = ids[i:i + c15.LOOKUP_PER_REQUEST]
        st, data = lim.get(c15.GAMMA_MARKETS, {"id": chunk, "limit": len(chunk)}, max_retries=max_retries)
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"gamma markets status {st}")
        for m in data:
            if isinstance(m, dict) and str(m.get("id")) in chunk:
                out[str(m["id"])] = c15.strip_forbidden(m)
    return out


def tier_snapshot(lim, races: list[dict], now: float) -> dict:
    """At the first pass (``T15_E_pre``; retried every 10 min until ``T15_E_on``, never after): Gamma ``liquidity`` of every MAPPED trade market of the frozen race map (declared: the
    tier is over all mapped trade markets, not over the races eligible on the night); the top third by liquidity is "liquid", the rest "second tier"."""
    if now >= ep(T15_E_ON):
        raise Refused("the tier snapshot is taken in [T15_E_pre, T15_E_on) only")
    ids = sorted({r["market_id"] for r in races if r["kind"] == "race"})
    got = gamma_markets(lim, ids)
    liq = {i: c15.num((got.get(i) or {}).get("liquidity")) for i in ids}
    return {"as_of": cm.iso(now), "liquidity": liq, "tiers": tiers_of(liq)}


def tiers_of(liq: dict[str, float]) -> dict[str, str]:
    ok = sorted([(v, k) for k, v in liq.items() if math.isfinite(v)], reverse=True)
    n_liquid = int(math.ceil(len(ok) * TIER_LIQUID_SHARE)) if ok else 0
    top = {k for _, k in ok[:n_liquid]}
    return {k: ("liquid" if k in top else "second tier") for k in liq}


def refresh_map(lim, races: list[dict], live_dir: Path, now: float) -> dict:
    """The 6-hourly Gamma map refresh: whether each frozen market is still listed / active with the same tokens (recorded only; no market is ever added after the freeze)."""
    ids = sorted({r["market_id"] for r in races})
    got = gamma_markets(lim, ids)
    rec = {}
    for r in races:
        m = got.get(r["market_id"])
        toks = [str(x) for x in listish((m or {}).get("clobTokenIds"))]
        rec[r["market_id"]] = {"listed": m is not None, "active": bool((m or {}).get("active")), "tokens_same": bool(m) and {r["token_d_yes"], r["token_d_no"]} <= set(toks)}
    doc = {"as_of": cm.iso(now), "markets": rec}
    cm.write_json_atomic(Path(live_dir) / LIVE_FILES["refresh_dir"] / f"{datetime.fromtimestamp(now, UTC):%Y%m%dT%H%M}.json", doc)
    return doc


# =====================================================================================================================================================
# Pre-gate (q0344): race map, two-party rule, control markets, band counts, GEI / GEC / GEP
# =====================================================================================================================================================


def band_label(bb: float, ba: float) -> str:
    """At ``t_a`` (and for the q0344 counts): ``in_band`` iff both sides exist, spread <= 10c and the mid lies in [0.10, 0.90] (0.10 accepted, 0.0999 not); else ``decided``
    (mid outside the band) or ``wide`` (spread > 10c or a one-sided / empty book). Both are pre-entry states."""
    if not (math.isfinite(bb) and math.isfinite(ba)):
        return "wide"
    if ba - bb > SPREAD_MAX + 1e-9:
        return "wide"
    mid = (bb + ba) / 2.0
    return "in_band" if BAND[0] - 1e-9 <= mid <= BAND[1] + 1e-9 else "decided"


def best_of(rec: dict | None) -> tuple[float, float, float, float]:
    """(best bid, best ask, bid size, ask size) of a book record; NaN for a missing side."""
    if not rec:
        return math.nan, math.nan, math.nan, math.nan
    bids, asks = rec.get("bids") or [], rec.get("asks") or []
    bb, bs = (bids[0][0], bids[0][1]) if bids else (math.nan, math.nan)
    ba, as_ = (asks[0][0], asks[0][1]) if asks else (math.nan, math.nan)
    return float(bb), float(ba), float(bs), float(as_)


def mid_one_sided(bb: float, ba: float) -> float:
    """The mid at ``t_b`` whatever the spread; a one-sided book uses the missing side's bound (no ask -> 1, no bid -> 0). Never an exclusion (round 1 item 2)."""
    b = bb if math.isfinite(bb) else 0.0
    a = ba if math.isfinite(ba) else 1.0
    return (b + a) / 2.0


def mde_e1(strata_counts: dict[str, dict], sigma: float = GEP_SIGMA_D) -> float:
    """GEP: ``MDE_E1 = (z_0.99 + z_0.80) x 1/2 x sigma_d / sqrt(sum_h m_h)`` with the declared sigma_d = 20c and ``m_h = n+ n- / (n+ + n-)`` over identified strata."""
    sm = sum((c["n_plus"] * c["n_minus"] / (c["n_plus"] + c["n_minus"])) for c in strata_counts.values() if c["n_plus"] >= 1 and c["n_minus"] >= 1)
    return float(GEP_Z * 0.5 * sigma / math.sqrt(sm)) if sm > 0 else math.inf


def gates_pregate(state_rows: list[dict]) -> dict:
    """GEI / GEC / GEP from per-state rows ``{state, sign, stratum, n_races_in_band}`` (mapped states, s != 0, band counts at the q0344 read). GEI: identified strata (both signs)
    must carry GEC's counts: >= 25 in-band races in >= 16 states with >= 9 states per sign, counted within identified strata only. GEP: the stratified MDE <= 15c."""
    st = [r for r in state_rows if r["sign"] in (1, -1) and r["n_races_in_band"] > 0]
    strata: dict[str, dict] = {}
    for r in st:
        c = strata.setdefault(r["stratum"], {"n_plus": 0, "n_minus": 0, "races": 0})
        c["n_plus" if r["sign"] == 1 else "n_minus"] += 1
        c["races"] += r["n_races_in_band"]
    ident = {h: c for h, c in strata.items() if c["n_plus"] >= 1 and c["n_minus"] >= 1}
    races = sum(c["races"] for c in ident.values())
    npos, nneg = sum(c["n_plus"] for c in ident.values()), sum(c["n_minus"] for c in ident.values())
    gec = bool(races >= GEC_MIN_RACES and npos + nneg >= GEC_MIN_STATES and npos >= GEC_MIN_PER_SIGN and nneg >= GEC_MIN_PER_SIGN)
    mde = mde_e1(ident)
    return {"strata": dict(sorted(strata.items())), "identified": sorted(ident), "gec": {"races": races, "states": npos + nneg, "plus": npos, "minus": nneg, "pass": gec},
            "gei": {"pass": bool(ident) and gec}, "gep": {"mde_e1": mde, "max": GEP_MAX_MDE, "sigma_d": GEP_SIGMA_D, "pass": bool(mde <= GEP_MAX_MDE)}}


def pick_control(got: list[tuple[dict, dict]], override: str | None) -> tuple[tuple[dict, dict] | None, str]:
    """The frozen control market of one chamber: the single candidate of the automatic rule; with several (or none), the coordinator's pre-freeze override (a D member market id
    named from the q0341 census, no price read) when it matches exactly one candidate; else none (net-of-control unknown, E1 cannot advance)."""
    if override:
        hit = [g for g in got if g[1]["market_id"] == str(override)]
        return (hit[0], "override") if len(hit) == 1 else (None, "override matches no candidate")
    if len(got) == 1:
        return got[0], "auto"
    return None, f"{len(got)} candidates (no override)"


def pregate_e(lim, post, *, census_rows: list[dict], ge0: dict, keys_rows: list[dict] | None, now: float, sleep=time.sleep,
              control_overrides: dict[str, str] | None = None) -> tuple[list[list], dict]:
    """q0344: refresh the q0341 race and control events by id (<= 60 requests), apply the trade-market and two-party rules with the GE0 party map, identify the control markets,
    ONE ``/books`` pass over the members' YES tokens (two-party ranking and band LABELS only; no mid is stored), the key-overlap count, the mapped cross-table and the gates. Returns
    (race-map rows for identified strata, report)."""
    ids = sorted({r["event_id"] for r in census_rows if r["kind"] in ("race", "control")})
    evs, nreq = lookup_events(lim, ids)
    parsed = {i: parse_event(e) for i, e in evs.items()}
    signs, closes, pmap = ge0["signs"], ge0["closes"], ge0["party_map"]
    races, controls, labels = [], {}, {}
    for _eid, pe in sorted(parsed.items()):
        cl = classify_event(pe)
        if cl["kind"] == "control":
            cmm = control_member(pe)
            if cmm is not None and not cmm["created_epoch"] >= now:  # a missing createdAt does not drop it
                controls.setdefault(cl["office"], []).append((pe, cmm))
            continue
        if cl["kind"] != "race":
            continue
        rid = race_id_of(cl["state"], cl["office"], cl["district"])
        tr = trade_market(pe, rid, pmap)
        if tr["market"] is None:
            labels[tr["source"]] = labels.get(tr["source"], 0) + 1
            continue
        races.append({"pe": pe, "cl": cl, "rid": rid, "tr": tr})
    toks = sorted({m["token_yes"] for r in races for m in r["pe"]["members"]} | {r["tr"]["market"]["token_yes"] for r in races})
    recs, gaps = run_pass(post, toks, now, sleep=sleep)
    best = {r["asset_id"]: best_of(r) for r in recs}
    mids = {t: ((v[0] + v[1]) / 2.0 if math.isfinite(v[0]) and math.isfinite(v[1]) else math.nan) for t, v in best.items()}
    ksrc = c15.ksrc_of(keys_rows) if keys_rows else {}
    rows, state_rows = [], {}
    for r in races:
        pe, cl, tr = r["pe"], r["cl"], r["tr"]
        tp_ok, tp_label = two_party(pe["members"], tr["members_party"], mids)
        if not tp_ok:
            labels[tp_label] = labels.get(tp_label, 0) + 1
            continue
        s = int(signs.get(cl["state"], 0))
        if cl["state"] not in closes:
            labels["no poll close"] = labels.get("no poll close", 0) + 1
            continue
        m = tr["market"]
        bb, ba, _, _ = best.get(m["token_yes"], (math.nan,) * 4)
        band = band_label(bb, ba) if m["token_yes"] in best else "no_book"
        sr = state_rows.setdefault(cl["state"], {"state": cl["state"], "sign": s, "stratum": stratum_of(closes[cl["state"]]), "n_races_in_band": 0, "n_races": 0})
        sr["n_races"] += 1
        sr["n_races_in_band"] += int(band == "in_band")
        overlap = c15.drop_reason({"market_id": m["market_id"], "event_id": pe["event_id"], "neg_risk_market_id": m["neg_risk_market_id"], "series_id": pe["series_id"]}, ksrc, "E") if ksrc else ""
        chamber = {"senate": "senate", "house": "house", "governor": "both"}[cl["office"]]
        rows.append([r["rid"], "race", cl["state"], cl["office"], cl["district"], pe["event_id"], m["market_id"], m["token_yes"], m["token_no"], tr["source"], tp_label, band, s,
                     stratum_of(closes[cl["state"]]), cm.iso(closes[cl["state"]]), chamber, m["fee_rate"], m["neg_risk_market_id"], pe["series_id"], overlap])
    gates = gates_pregate(list(state_rows.values()))
    ident = set(gates["identified"])
    race_rows = [x for x in rows if x[12] in (1, -1) and x[13] in ident]
    ctrl_rows = []
    ctrl_how = {}
    for ch in ("senate", "house"):
        pick, how = pick_control(controls.get(ch) or [], (control_overrides or {}).get(ch))
        ctrl_how[ch] = {"rule": how, "candidates": [g[1]["market_id"] for g in controls.get(ch) or []]}
        if pick is not None:
            pe, cmm = pick
            ctrl_rows.append([f"CONTROL|{ch}|", "control", "", ch, "", pe["event_id"], cmm["market_id"], cmm["token_yes"], cmm["token_no"], "control", "", "", 0, "", "", ch, cmm["fee_rate"],
                              cmm["neg_risk_market_id"], pe["series_id"], ""])
    rep = {"counts_only": True, "requests": {"event_lookups": nreq, "books_batches": math.ceil(len(toks) / BOOKS_BATCH)}, "races_considered": len(races), "labels": labels,
           "two_party_races": len(rows), "race_map_races": len(race_rows), "controls_mapped": sorted(r[3] for r in ctrl_rows), "controls_rule": ctrl_how, "books_gaps": len(gaps),
           "bands": {b: sum(1 for x in rows if x[11] == b) for b in ("in_band", "decided", "wide", "no_book")},
           "key_overlap": sum(1 for x in race_rows if x[19]), "cross_table_mapped": cross_table(signs, closes, sorted(state_rows)), "gates": gates}
    return race_rows + ctrl_rows, rep


# =====================================================================================================================================================
# Screen (q0346): reads, units, E1, E2
# =====================================================================================================================================================


class BookIndex:
    """Successful reads per token, sorted by receipt: arrays of (receipt, best bid, best ask, bid size, ask size). Built from the pass files only (no other store)."""

    def __init__(self, recs: Iterable[dict], *, token_absent: dict[str, list[float]] | None = None, market_inactive: dict[str, list[float]] | None = None):
        per: dict[str, list[tuple[float, float, float, float, float]]] = {}
        for r in recs:
            bb, ba, bs, as_ = best_of(r)
            per.setdefault(r["asset_id"], []).append((float(r["receipt"]), bb, ba, bs, as_))
        self.idx = {k: np.array(sorted(v), float) for k, v in per.items()}
        self.token_absent = {k: sorted(v) for k, v in (token_absent or {}).items()}  # receipts of successful batches that did NOT return the token
        self.market_inactive = {k: sorted(v) for k, v in (market_inactive or {}).items()}  # map-refresh times showing the market unlisted or inactive

    def last_before(self, token: str, lo: float, hi: float) -> dict | None:
        """The last successful read with receipt in ``[lo, hi)``."""
        a = self.idx.get(token)
        if a is None or not len(a):
            return None
        i = int(np.searchsorted(a[:, 0], hi, side="left")) - 1
        if i < 0 or a[i, 0] < lo:
            return None
        return {"receipt": float(a[i, 0]), "bb": float(a[i, 1]), "ba": float(a[i, 2]), "bs": float(a[i, 3]), "as": float(a[i, 4])}

    def closed_after(self, token: str, market_id: str, after: float, by: float) -> float:
        """Closure evidence (round 2 fix 1): the first time in ``(after, by]`` at which a SUCCESSFUL batch omitted the token, or a map refresh showed its market unlisted / inactive;
        NaN if none (then a missing read is a collector gap, never a closure)."""
        ts = [t for t in self.token_absent.get(token, []) if after < t <= by] + [t for t in self.market_inactive.get(str(market_id), []) if after < t <= by]
        return float(min(ts)) if ts else math.nan

    def read_at(self, token: str, t: float, max_lag: float) -> dict | None:
        """The first successful read with receipt >= ``t`` and <= ``t + max_lag`` (2 min at ``t_a``, 5 min at ``t_b``; 2 min 1 s is too late)."""
        a = self.idx.get(token)
        if a is None or not len(a):
            return None
        i = int(np.searchsorted(a[:, 0], t, side="left"))
        if i >= len(a) or a[i, 0] > t + max_lag + 1e-9:
            return None
        return {"receipt": float(a[i, 0]), "bb": float(a[i, 1]), "ba": float(a[i, 2]), "bs": float(a[i, 3]), "as": float(a[i, 4])}


def closure_evidence(live_dir: Path) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """(token -> receipts of successful batches that omitted it, market id -> map-refresh times showing it unlisted or inactive), from the collector's own logs only."""
    absent: dict[str, list[float]] = {}
    for g in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["gaps"]):
        if g.get("why") == ABSENT_WHY:
            for t in g.get("tokens") or []:
                absent.setdefault(str(t), []).append(float(g["receipt"]))
    inactive: dict[str, list[float]] = {}
    for f in sorted((Path(live_dir) / LIVE_FILES["refresh_dir"]).glob("*.json")):
        d = json.loads(f.read_text())
        t = c15.parse_iso(d.get("as_of"))
        for mid, v in (d.get("markets") or {}).items():
            if not (v.get("listed") and v.get("active")):
                inactive.setdefault(str(mid), []).append(t)
    return absent, inactive


def load_books(live_dir: Path, tokens: set[str] | None = None) -> BookIndex:
    files = sorted((Path(live_dir) / LIVE_FILES["books_dir"]).glob("*.jsonl.gz"))
    absent, inactive = closure_evidence(live_dir)
    return BookIndex((r for f in files for r in c15.jsonl_iter(f) if tokens is None or r.get("asset_id") in tokens), token_absent=absent, market_inactive=inactive)


def read_or_closed(bi: BookIndex, token: str, market_id: str, t: float, lag: float, since: float) -> tuple[dict | None, bool]:
    """The read at ``t`` (within ``lag``); if none, the last read in ``[since, t)`` when closure evidence follows it by ``t + lag`` (the market closed / was called: its last book
    stands); else (None, False) = a collector gap."""
    r = bi.read_at(token, t, lag)
    if r is not None:
        return r, False
    last = bi.last_before(token, since, t)
    if last is None:
        return None, False
    c = bi.closed_after(token, market_id, last["receipt"], t + lag)
    return (last, True) if math.isfinite(c) else (None, False)


def logit(p: float) -> float:
    q = min(max(p, LOGIT_CLAMP[0]), LOGIT_CLAMP[1])
    return math.log(q / (1.0 - q))


def race_unit(race: dict, bi: BookIndex, *, ta: float, tb: float) -> dict:
    """One race on one window: entry eligibility at ``t_a`` (two-sided, spread <= 10c, mid in [0.10, 0.90]; 'decided' / 'wide' are pre-entry exclusions), reads at ``t_a`` (<= 2
    min) and ``t_b`` (<= 5 min), the D-terms drift (mid at ``t_b`` by the one-sided rule; NO exclusion uses the state at ``t_b``), and the E2 nets of buying the D YES (s = +1)
    and the D NO (s = -1) token at the recorded best ask and selling at the recorded best bid (no bid -> w*)."""
    mid_ = race.get("market_id", "")
    ya = bi.read_at(race["token_d_yes"], ta, READ_LAG_A_S)
    if ya is None:
        last = bi.last_before(race["token_d_yes"], -math.inf, ta)
        if last is not None and math.isfinite(bi.closed_after(race["token_d_yes"], mid_, last["receipt"], ta + READ_LAG_A_S)):
            return {"status": CLOSED_BEFORE_TA}  # called / closed before entry: a pre-entry state, excluded and counted
        return {"status": "unavailable (gap)"}
    yb, closed_b = read_or_closed(bi, race["token_d_yes"], mid_, tb, READ_LAG_B_S, ya["receipt"])
    if yb is None:
        return {"status": "unavailable (gap)"}
    lab = band_label(ya["bb"], ya["ba"])
    if lab != "in_band":
        return {"status": lab}
    m_a = (ya["bb"] + ya["ba"]) / 2.0
    m_b = mid_one_sided(yb["bb"], yb["ba"])
    rate = c15.taker_rate(race.get("fee_rate"))
    nets = {}
    for side, tok in ((1, race["token_d_yes"]), (-1, race["token_d_no"])):
        ea = bi.read_at(tok, ta, READ_LAG_A_S)
        eb, _cl = read_or_closed(bi, tok, mid_, tb, READ_LAG_B_S, ea["receipt"]) if ea is not None else (None, False)
        if ea is None or not math.isfinite(ea["ba"]) or eb is None:
            nets[side] = None
            continue
        x = eb["bb"]
        net = c15.W_STAR if not math.isfinite(x) else c15.round_trip_net(ea["ba"], x, rate)
        nets[side] = {"net": net, "entry": ea["ba"], "size": min(c15.PAPER_SIZE, ea["as"]) if math.isfinite(ea["as"]) else math.nan, "no_bid": not math.isfinite(x),
                      "no_depth": not (math.isfinite(ea["as"]) and ea["as"] >= NO_DEPTH_SIZE), "rate": rate}
    return {"status": "ok", "mid_a": m_a, "mid_b": m_b, "drift": m_b - m_a, "one_sided_b": not (math.isfinite(yb["bb"]) and math.isfinite(yb["ba"])), "nets": nets,
            "z_race": logit(m_b) - logit(m_a), "closed_b": bool(closed_b)}


def control_drift(controls: dict[str, dict], bi: BookIndex, chamber: str, ta: float, tb: float) -> float:
    """Logit drift of the chamber-control D mid over the same clock window (Governor races: the mean of the Senate and House drifts); NaN -> unknown."""
    chs = ("senate", "house") if chamber == "both" else (chamber,)
    out = []
    for ch in chs:
        c = controls.get(ch)
        if c is None:
            return math.nan
        a = bi.read_at(c["token_d_yes"], ta, READ_LAG_A_S)
        b = read_or_closed(bi, c["token_d_yes"], c.get("market_id", ""), tb, READ_LAG_B_S, a["receipt"])[0] if a is not None else None
        if a is None or b is None:
            return math.nan
        out.append(logit(mid_one_sided(b["bb"], b["ba"])) - logit(mid_one_sided(a["bb"], a["ba"])))
    return float(np.mean(out))


def state_table(races: list[dict], controls: dict[str, dict], bi: BookIndex, *, ta_off: float = T_A_OFFSET_S, tb_off: float = T_B_OFFSET_S, window: tuple[float, float] | None = None,
                net_exit_off: float | None = None) -> dict:
    """Per-state values (each state weight 1, the mean over its eligible races): ``d`` (D-terms drift), ``z`` (net-of-control logit drift; NaN if a control read is missing),
    ``net_plus`` / ``net_minus`` (E2 nets of the D YES / D NO side), plus per-race statuses. ``window`` overrides (t_a, t_b) offsets (the pre-night placebo); ``net_exit_off`` the E2
    exit offset."""
    per_state: dict[str, dict] = {}
    statuses: dict[str, int] = {}
    for r in races:
        tc = c15.parse_iso(r["t_close"])
        ta = t_a_of(tc, ta_off)
        tb = ta + tb_off
        if window is not None:
            ta, tb = t_a_of(tc) + window[0], t_a_of(tc) + window[1]
        u = race_unit(r, bi, ta=ta, tb=tb)
        if net_exit_off is not None and u["status"] == "ok":
            u2 = race_unit(r, bi, ta=ta, tb=ta + net_exit_off)
            u["nets"] = u2.get("nets", {1: None, -1: None}) if u2["status"] == "ok" else {1: None, -1: None}
        statuses[u["status"]] = statuses.get(u["status"], 0) + 1
        if u.get("closed_b"):
            statuses[CLOSED_STATUS] = statuses.get(CLOSED_STATUS, 0) + 1
        s = per_state.setdefault(r["state"], {"state": r["state"], "sign": int(r["sign"]), "stratum": r["stratum"], "d": [], "z": [], "np": [], "nm": [], "races": [], "nd_p": [], "nd_m": []})
        if u["status"] != "ok":
            continue
        cz = control_drift(controls, bi, r["chamber"], ta, tb)
        s["d"].append(u["drift"])
        s["z"].append(u["z_race"] - cz if math.isfinite(cz) else math.nan)
        s["races"].append({**{k: r[k] for k in ("race_id", "office", "market_id", "key_overlap")}, "drift": u["drift"], "one_sided_b": u["one_sided_b"]})
        for side, key, nd in ((1, "np", "nd_p"), (-1, "nm", "nd_m")):
            n = u["nets"].get(side)
            s[key].append(n["net"] if n else math.nan)
            s[nd].append(c15.W_STAR if (n and n["no_depth"]) else (n["net"] if n else math.nan))
    states = []
    for s in per_state.values():
        if not s["d"]:
            continue
        states.append({"state": s["state"], "sign": s["sign"], "stratum": s["stratum"], "d": float(np.mean(s["d"])), "z": float(np.mean(s["z"])) if all(math.isfinite(x) for x in s["z"]) else math.nan,
                       "net_plus": float(np.mean(s["np"])) if all(math.isfinite(x) for x in s["np"]) else math.nan,
                       "net_minus": float(np.mean(s["nm"])) if all(math.isfinite(x) for x in s["nm"]) else math.nan,
                       "nd_plus": float(np.mean(s["nd_p"])) if all(math.isfinite(x) for x in s["nd_p"]) else math.nan,
                       "nd_minus": float(np.mean(s["nd_m"])) if all(math.isfinite(x) for x in s["nd_m"]) else math.nan, "n_races": len(s["d"]), "races": s["races"]})
    return {"states": sorted(states, key=lambda x: x["state"]), "statuses": statuses}


def _arrays(states: list[dict], key_plus: str, key_minus: str | None = None, *, negate: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    vp = np.array([s[key_plus] for s in states], float)
    vm = -vp if negate else np.array([s[key_minus] for s in states], float)
    return vp, vm, np.array([s["sign"] for s in states], int), np.array([s["stratum"] for s in states]).astype(str)


def identified_only(states: list[dict]) -> list[dict]:
    W = c15.stratum_weights([s["sign"] for s in states], [s["stratum"] for s in states]) if states else {}
    return [s for s in states if W.get(s["stratum"], {}).get("identified")]


def contrast(states: list[dict], key: str = "d", *, e2: bool = False, draws: int = c15.PERM_DRAWS, seed: int = c15.SEED_PERM) -> dict:
    """The stratified balanced statistic and its within-stratum permutation p on identified strata. E1 (``key`` d or z): ``v_plus = x``, ``v_minus = -x``; E2: the state's net of
    the D YES side when labelled +1 and of the D NO side when labelled -1 (states lacking either net are outside the permutation's support and excluded, counted)."""
    if e2:
        kp, km = ("net_plus", "net_minus") if key == "net" else (key + "_plus", key + "_minus")
        ok = identified_only([s for s in states if math.isfinite(s[kp]) and math.isfinite(s[km])])
        vp, vm, lab, st = _arrays(ok, kp, km)
    else:
        ok = identified_only([s for s in states if math.isfinite(s[key])])
        vp, vm, lab, st = _arrays(ok, key, negate=True)
    if not ok:
        return {"T": math.nan, "p": 1.0, "testable": False, "n_states": 0, "share": math.nan}
    r = c15.perm_p_within_strata(vp, vm, lab, st, draws=draws, seed=seed)
    share = c15.stratified_sign_share(vp, vm, lab, st)
    return {**r, "n_states": len(ok), "n_plus": int((lab == 1).sum()), "n_minus": int((lab == -1).sum()), "share": share,
            "weights": c15.stratum_weights(lab, st)}


def gate_ge(states: list[dict]) -> dict:
    ok = identified_only(states)
    npos, nneg = sum(1 for s in ok if s["sign"] == 1), sum(1 for s in ok if s["sign"] == -1)
    return {"states": len(ok), "plus": npos, "minus": nneg, "pass": bool(len(ok) >= GE_MIN_STATES and npos >= GE_MIN_PER_SIGN and nneg >= GE_MIN_PER_SIGN)}


def predicted_value(s: dict, key: str, *, e2: bool = False) -> float:
    """A state's value in its predicted direction: ``s x value`` (E1), or the net of its predicted side (E2: ``net_plus`` for s = +1, ``net_minus`` for s = -1)."""
    if e2:
        return float(s["net_plus"] if s["sign"] == 1 else s["net_minus"])
    return float(s["sign"] * s[key])


def drop_top_per_sign(states: list[dict], key: str, k: int = TOP_STATES_PER_SIGN, *, e2: bool = False) -> list[dict]:
    """Drop the ``k`` states of each sign with the largest contribution in the predicted direction."""
    keep = []
    for sg in (1, -1):
        grp = sorted([s for s in states if s["sign"] == sg], key=lambda s: -predicted_value(s, key, e2=e2))
        keep += grp[k:]
    return keep


def loso(states: list[dict], key: str, *, e2: bool = False) -> dict:
    """Every leave-one-state-out statistic keeps the sign (estimate only; no permutation)."""
    ests = {}
    for s in states:
        rest = [x for x in states if x["state"] != s["state"]]
        if e2:
            ok = identified_only([x for x in rest if math.isfinite(x["net_plus"]) and math.isfinite(x["net_minus"])])
        else:
            ok = identified_only([x for x in rest if math.isfinite(x[key])])
        if not ok:
            ests[s["state"]] = math.nan
            continue
        vp, vm, lab, st = _arrays(ok, "net_plus", "net_minus") if e2 else _arrays(ok, key, negate=True)
        ests[s["state"]] = c15.stratified_balanced(vp, vm, lab, st)
    holds = bool(ests) and all(math.isfinite(v) and v > 0 for v in ests.values())
    return {"holds": holds, "min": min((v for v in ests.values() if math.isfinite(v)), default=math.nan), "n": len(ests)}


def tier_filter(races: list[dict], tiers: dict[str, str], tier: str) -> list[dict]:
    return [r for r in races if tiers.get(r["market_id"]) == tier]


def e1_test(races: list[dict], controls: dict[str, dict], bi: BookIndex, tiers: dict[str, str], *, draws: int = c15.PERM_DRAWS) -> dict:
    """E1 with its binding checks (section CB15-E) and reported quantities."""
    base = state_table(races, controls, bi)
    states = base["states"]
    ge = gate_ge(states)
    eligible = len(races)
    avail = sum(v for k, v in base["statuses"].items() if k != "unavailable (gap)")
    av = {"available": avail, "eligible": eligible, "share": avail / eligible if eligible else math.nan, "ok": bool(eligible and avail / eligible >= c15.AVAIL_MIN)}
    if not ge["pass"]:
        return {"testable": False, "p": 1.0, "advance": False, "verdict": NOT_TESTABLE_POP, "ge": ge, "statuses": base["statuses"], "availability": av, "n": len(states)}
    if not av["ok"]:
        return {"testable": False, "p": 1.0, "advance": False, "verdict": NOT_TESTABLE_AVAIL, "ge": ge, "statuses": base["statuses"], "availability": av, "n": len(states)}
    main = contrast(states, "d", draws=draws)
    netc = contrast(states, "z", draws=draws) if all(math.isfinite(s["z"]) for s in identified_only(states)) else {"T": math.nan, "p": 1.0, "testable": False, "unknown": True}
    pl = contrast(state_table(races, controls, bi, window=PLACEBO_WINDOW_S)["states"], "d", draws=draws)
    rob = {}
    for name, kw in (("t_a+60", {"ta_off": T_A_ROBUST_S[0]}), ("t_a+150", {"ta_off": T_A_ROBUST_S[1]}), ("t_b=t_a+6h", {"tb_off": T_B_ROBUST_S[0]}), ("t_b=t_a+24h", {"tb_off": T_B_ROBUST_S[1]})):
        rr = contrast(state_table(races, controls, bi, **kw)["states"], "d", draws=draws)
        need_p = name in ("t_a+60", "t_a+150")
        rob[name] = {"T": rr["T"], "p": rr["p"], "holds": bool(math.isfinite(rr["T"]) and rr["T"] > 0 and (rr["p"] < ROBUST_P if need_p else True))}
    sg = [r for r in races if r["office"] in ("senate", "governor")]
    sgs = identified_only(state_table(sg, controls, bi)["states"])
    if min(sum(1 for s in sgs if s["sign"] == 1), sum(1 for s in sgs if s["sign"] == -1)) >= SENATE_GOV_MIN_PER_SIGN:
        rr = contrast(sgs, "d", draws=0)
        rob["senate_governor"] = {"T": rr["T"], "holds": bool(math.isfinite(rr["T"]) and rr["T"] > 0)}
    else:
        rob["senate_governor"] = {"skipped": f"fewer than {SENATE_GOV_MIN_PER_SIGN} states per sign", "holds": True}
    rr = contrast(state_table(tier_filter(races, tiers, "second tier"), controls, bi)["states"], "d", draws=0)
    rob["second_tier"] = {"T": rr["T"], "holds": bool(math.isfinite(rr["T"]) and rr["T"] > 0)}
    rr = contrast(state_table([r for r in races if not r.get("key_overlap")], controls, bi)["states"], "d", draws=0)
    rob["key_overlap_dropped"] = {"T": rr["T"], "holds": bool(math.isfinite(rr["T"]) and rr["T"] > 0)}
    ident = identified_only(states)
    rob["leave_one_state_out"] = loso(ident, "d")
    rr = contrast(drop_top_per_sign(ident, "d"), "d", draws=0)
    rob["top2_per_sign_dropped"] = {"T": rr["T"], "holds": bool(math.isfinite(rr["T"]) and rr["T"] > 0)}
    floor_ok = bool(math.isfinite(main["T"]) and main["T"] >= E1_FLOOR)
    share_ok = bool(math.isfinite(main["share"]) and main["share"] >= E1_SIGN_SHARE_MIN)
    netc_ok = bool(netc.get("testable") and math.isfinite(netc["T"]) and netc["T"] > 0 and netc["p"] < NET_CONTROL_P)
    pl_ok = bool(pl.get("testable") and pl["p"] >= PLACEBO_P_FAIL)  # an untestable placebo is unknown and never counts as met (section 2.3; round 2 fix 7)
    rob_ok = all(v["holds"] for v in rob.values())
    checks = {"floor": floor_ok, "sign_share": share_ok, "net_of_control": netc_ok, "placebo": pl_ok, "robustness": rob_ok, "ge": ge["pass"], "availability": av["ok"]}
    checks_ok = all(checks.values())
    p = main["p"] if main.get("testable") else 1.0
    adv = c15.e_judged(p, checks_ok)
    reported = {"race_sign_share": race_share(states), "unbalanced_mean": float(np.mean([s["sign"] * s["d"] for s in states])) if states else math.nan,
                "unstratified_contrast": unstratified(states), "tiers": {t: contrast(state_table(tier_filter(races, tiers, t), controls, bi)["states"], "d", draws=0)["T"] for t in ("liquid", "second tier")},
                "one_sided_b_share": float(np.mean([x["one_sided_b"] for s in states for x in s["races"]])) if states else math.nan, "statuses": base["statuses"]}
    return {"testable": bool(main.get("testable")), "p": float(p), "est": main["T"], "share": main["share"], "n": main["n_states"], "advance": adv, "checks": checks, "checks_ok": checks_ok,
            "verdict": "advance (one-night case study)" if adv else "not detected at MDE", "net_of_control": netc, "placebo": pl, "robustness": rob, "ge": ge, "availability": av,
            "weights": main.get("weights"), "reported": reported, "label": LABEL_E}


def race_share(states: list[dict]) -> float:
    xs = [1.0 if (s["sign"] * x["drift"]) > 0 else 0.0 for s in states for x in s["races"]]
    return float(np.mean(xs)) if xs else math.nan


def unstratified(states: list[dict]) -> float:
    p = [s["d"] for s in states if s["sign"] == 1]
    m = [s["d"] for s in states if s["sign"] == -1]
    return float(0.5 * np.mean(p) - 0.5 * np.mean(m)) if p and m else math.nan


def e2_test(races: list[dict], controls: dict[str, dict], bi: BookIndex, *, draws: int = c15.PERM_DRAWS) -> dict:
    """E2: buy the predicted side at the recorded best ask at ``t_a`` and sell at the recorded best bid at ``t_b`` (no bid -> w*); state value = mean race net; the same strata,
    weights and permutation; floor +1.0c; binding +1c per side, no-depth races at w* and the exit at ``t_a + 6 h`` keep the sign."""
    base = state_table(races, controls, bi)
    states = base["states"]
    ge = gate_ge(states)
    if not ge["pass"]:
        return {"testable": False, "p": 1.0, "advance": False, "verdict": NOT_TESTABLE_POP, "ge": ge, "n": len(states)}
    main = contrast(states, "net", e2=True, draws=draws)
    support = main.get("n_states", 0)
    cost = [{**s, "net_plus": s["net_plus"] - 2 * c15.COST_ROBUST_PER_SIDE, "net_minus": s["net_minus"] - 2 * c15.COST_ROBUST_PER_SIDE} for s in states]
    rc = contrast(cost, "net", e2=True, draws=0)
    nd = [{**s, "net_plus": s["nd_plus"], "net_minus": s["nd_minus"]} for s in states]
    rn = contrast(nd, "net", e2=True, draws=0)
    rx = contrast(state_table(races, controls, bi, net_exit_off=T_B_ROBUST_S[0])["states"], "net", e2=True, draws=0)
    sup = identified_only([s for s in states if math.isfinite(s["net_plus"]) and math.isfinite(s["net_minus"])])
    rt = contrast(drop_top_per_sign(sup, "net", e2=True), "net", e2=True, draws=0)
    rob = {"cost_plus_1c_per_side": {"T": rc["T"], "holds": bool(math.isfinite(rc["T"]) and rc["T"] > 0)}, "no_depth_at_w_star": {"T": rn["T"], "holds": bool(math.isfinite(rn["T"]) and rn["T"] > 0)},
           "exit_t_a_plus_6h": {"T": rx["T"], "holds": bool(math.isfinite(rx["T"]) and rx["T"] > 0)}, "leave_one_state_out": loso(sup, "net", e2=True),
           "top2_per_sign_dropped": {"T": rt["T"], "holds": bool(math.isfinite(rt["T"]) and rt["T"] > 0)}}
    eligible = len(races)
    avail = sum(v for k, v in base["statuses"].items() if k != "unavailable (gap)")
    av = {"available": avail, "eligible": eligible, "share": avail / eligible if eligible else math.nan, "ok": bool(eligible and avail / eligible >= c15.AVAIL_MIN)}
    if not av["ok"]:
        return {"testable": False, "p": 1.0, "advance": False, "verdict": NOT_TESTABLE_AVAIL, "ge": ge, "availability": av, "n": support}
    floor_ok = bool(math.isfinite(main["T"]) and main["T"] >= E2_FLOOR)
    checks = {"floor": floor_ok, "robustness": all(v["holds"] for v in rob.values()), "ge": ge["pass"], "support": bool(support >= GE_MIN_STATES), "availability": av["ok"]}
    checks_ok = all(checks.values())
    p = main["p"] if main.get("testable") else 1.0
    adv = c15.e_judged(p, checks_ok)
    return {"testable": bool(main.get("testable")), "p": float(p), "est": main["T"], "n": support, "advance": adv, "checks": checks, "checks_ok": checks_ok,
            "verdict": "advance (one-night case study)" if adv else "not detected at MDE", "robustness": rob, "ge": ge, "availability": av, "weights": main.get("weights"), "label": LABEL_E,
            "reported": {"capacity_mean_size": capacity(races, bi), "statuses": base["statuses"],
                         "states_dropped_missing_side_net": sum(1 for s in states if not (math.isfinite(s["net_plus"]) and math.isfinite(s["net_minus"])))}}


def capacity(races: list[dict], bi: BookIndex) -> float:
    """Reported: the mean displayed best-ask size (capped at 100) of the predicted-side token at ``t_a`` over races with an entry read."""
    xs = []
    for r in races:
        ta = t_a_of(c15.parse_iso(r["t_close"]))
        tok = r["token_d_yes"] if int(r["sign"]) == 1 else r["token_d_no"]
        e = bi.read_at(tok, ta, READ_LAG_A_S)
        if e is not None and math.isfinite(e["as"]):
            xs.append(min(c15.PAPER_SIZE, e["as"]))
    return float(np.mean(xs)) if xs else math.nan


def load_screen_inputs(live_dir: Path, race_map_path: Path) -> tuple[list[dict], dict[str, dict], BookIndex, dict[str, str]]:
    rows = read_race_map(race_map_path)
    races = [{**r, "sign": int(r["sign"])} for r in rows if r["kind"] == "race"]
    controls = {r["office"]: r for r in rows if r["kind"] == "control"}
    tokens = set(collector_tokens(rows))
    bi = load_books(live_dir, tokens)
    tp = Path(live_dir) / LIVE_FILES["tier"]
    tdoc = json.loads(tp.read_text()) if tp.is_file() else {}
    ok = bool(tdoc) and c15.parse_iso(tdoc.get("as_of")) < ep(T15_E_ON)  # a snapshot taken at or after T15_E_on is never used (round 2 fix 5)
    tiers = (tdoc.get("tiers") or {}) if ok else {}
    return races, controls, bi, tiers


def screen_e(live_dir: Path, race_map_path: Path, *, draws: int = c15.PERM_DRAWS) -> dict:
    races, controls, bi, tiers = load_screen_inputs(live_dir, race_map_path)
    e1 = e1_test(races, controls, bi, tiers, draws=draws)
    e2 = e2_test(races, controls, bi, draws=draws)
    return {"E1": e1, "E2": e2, "labels": [LABEL_E], "controls_mapped": sorted(controls)}


# =====================================================================================================================================================
# Calendar: was part E frozen by T15_E_freeze?
# =====================================================================================================================================================


def e_freeze_commit_time(spec_path: Path, race_map_sha256: str, *, git: Callable[[list[str]], str | None] | None = None) -> float:
    """The commit time of the first commit of ``model_specs/cb15_v1.json`` that carries the PINNED race-map sha256 value (round 2 fix 8: the value, not the key name); NaN if none."""
    from . import provenance  # noqa: PLC0415

    run = git or (lambda args: provenance._git(args, provenance.REPO_ROOT))
    try:
        rel = str(Path(spec_path).resolve().relative_to(provenance.REPO_ROOT.resolve()))
    except ValueError:
        rel = str(spec_path)
    if not race_map_sha256 or len(str(race_map_sha256)) != 64:
        return math.nan
    out = run(["log", "--format=%ct", "--reverse", f"-S{race_map_sha256}", "--", rel])
    times = [t for t in (out or "").split() if t.isdigit()]
    return float(times[0]) if times else math.nan


def calendar_missed(commit_time: float) -> bool:
    return not (math.isfinite(commit_time) and commit_time <= ep(T15_E_FREEZE))


# =====================================================================================================================================================
# Smoke (family checks), declared
# =====================================================================================================================================================


def _chk(ok: bool, **detail) -> dict:
    return {"pass": bool(ok), **detail}


def ge0_fixture() -> dict:
    """A synthetic GE0 set (two states) used by the smoke and the tests: one fully cited agreeing state, one with a missing citation (s = 0)."""
    sha = "a" * 64
    man = {"version": GE0_VERSIONS["source_manifest"], "files": [{"sha256": sha, "url": "https://example.org/x", "fetched_utc": "2026-10-20T00:00:00Z", "file": "x.html", "kind": "state_law"}]}
    full = {"s": 1, "pass_a": 1, "pass_b": 1, "mode_order": 1, "dir_2022": 1, "dir_2024": 1, "audit": "supported", "mode_order_citations": [sha], "dir_2022_citations": [sha], "dir_2024_citations": [sha]}
    return {"manifest": man, "full": full, "uncited": {**full, "dir_2024_citations": []}}


def smoke_offline(ctx: dict) -> dict:
    """Fixture checks, no network: refusals (live stores, holdouts, refused roots, forbidden fields at parse), the GE0 schema rule (s = 0 without an archived source), the collector
    before ``T15_E_pre`` (idle, no request), the forced-failure gap log, the storage degradation path on a forced projection, the cpu-lane hold flag on a test queue dir."""
    import importlib.util  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    from . import provenance  # noqa: PLC0415

    res: dict = {}
    refused = 0
    for bad in (Path("x/cross_venue_live/a"), Path("x/surprise_live/a"), Path("x/h11_pol/holdout/frame.csv.gz"), Path("x/creative_batch14/a"), Path("x/live_trades/a")):
        try:
            c15.guard_input_path(bad)
        except Refused:
            refused += 1
    m = parse_market({"id": "1", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "outcomePrices": '["0","1"]', "closedTime": "x", "umaResolutionStatus": "resolved", "side": "BUY",
                      "proxyWallet": "0x"})
    clean = bool(m) and not ({"outcomePrices", "closedTime", "umaResolutionStatus", "side", "proxyWallet"} & set(m))
    forb = 0
    for col in ("side", "proxyWallet", "outcomePrices", "closedTime", "result"):
        try:
            c15.assert_clean_columns([col])
        except Refused:
            forb += 1
    res["guards_fixture_E"] = _chk(refused == 5 and clean and forb == 5, refused=refused, parse_clean=clean, forbidden=forb)
    res["e_part_hashes"] = _chk(all(c15.rules_part_file_doc(p).get("part_declared") is not False for p in ("common", "E")))
    fx = ge0_fixture()
    shas = manifest_shas(fx["manifest"])
    res["e_ge0_schema_fixture"] = _chk(effective_sign(fx["full"], shas) == 1 and effective_sign(fx["uncited"], shas) == 0 and not validate_manifest(fx["manifest"]))
    with tempfile.TemporaryDirectory() as td:
        hist = Path(td) / "history"
        rm = Path(td) / "race_map.csv"
        rm.write_text(",".join(RACE_MAP_COLUMNS) + "\n")

        def boom(body):
            raise AssertionError("no request before T15_E_pre")

        r = e_live(hist, race_map_path=rm, post=boom, lim=None, now=ep(T15_E_PRE) - 60, cap_gb=1.0, rules_sha="smoke")
        res["e_collector_before_pre"] = _chk(r["status"] == "e_live_idle")
        recs, gaps = run_pass(lambda body: (503, b"", {}), ["t1", "t2"], ep(T15_E_ON), sleep=lambda s: None)
        res["e_gap_logging"] = _chk(not recs and len(gaps) == 1 and gaps[0]["n_tokens"] == 2, gaps=len(gaps))
        dec = storage_decision(9e8, [1e6] * 5, 1000, 1e9, 50e9)
        stop = storage_decision(0, [], 10, 1e9, 1e9)
        res["e_degradation"] = _chk(dec["degrade"] and not dec["stop"] and stop["stop"])
        qroot = Path(td) / "queue"
        qroot.mkdir()
        lane_ok = False
        try:
            p = provenance.REPO_ROOT / "scripts" / "oracle" / "queue_worker.py"
            spec = importlib.util.spec_from_file_location("queue_worker_cb15_smoke", p)
            qw = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(qw)  # type: ignore[union-attr]
            qw.QROOT = qroot
            qw.hold_lane(HOLD_LANE, HOLD_MIN_MEM_MB)
            big, small, net = ({"resources": {"lane": "cpu", "mem_mb": 600}}, {"resources": {"lane": "cpu", "mem_mb": 400}}, {"resources": {"lane": "net", "mem_mb": 600}})
            held = qw.lane_held(big) and not qw.lane_held(small) and not qw.lane_held(net)
            qw.release_lane()
            lane_ok = bool(held and not qw.lane_held(big))
        except (AttributeError, OSError, AssertionError):
            lane_ok = False
        res["e_lane_hold_flag"] = _chk(lane_ok)
    return res


def is_transient(err: str) -> bool:
    """A transport error, 408, 429 or 5xx (after the one quick retry) is transient: the smoke is pending, not failed."""
    return bool(re.search(r"status (0|408|429|5\d\d)\b|unparseable|Error", str(err or "")))


def out_of_frame_tokens(lim, n: int = SMOKE_FULL_PASS_TOKENS) -> list[str]:
    """YES and NO tokens of active binary markets that are not election races or control markets (out of frame), from Gamma ``/markets`` pages (<= 3 requests)."""
    toks: list[str] = []
    for off in (0, 500, 1000):
        st, data = lim.get(c15.GAMMA_MARKETS, {"active": "true", "closed": "false", "limit": 500, "offset": off, "order": "id", "ascending": "false"})
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"gamma markets status {st}")
        for m in data:
            if not isinstance(m, dict):
                continue
            q = str(m.get("question") or "")
            if office_of(q) or CONTROL_RE.search(q) or GENERAL_DATE_RE.search(q):
                continue
            if not (m.get("enableOrderBook") and m.get("acceptingOrders")):  # order-book markets only (round 2 fix 3)
                continue
            pm = parse_market(m)
            if pm is not None:
                toks += [pm["token_yes"], pm["token_no"]]
        if len(toks) >= n:
            break
    return toks[:n]


def smoke_online(lim, ctx: dict) -> dict:
    """<= 30 requests, counts only: Gamma paging to ``hasMore = false`` on one query; ``POST /books`` with 100 out-of-frame tokens returns 100 books; one full-size pass of about 1,000
    out-of-frame tokens with its stored bytes measured (sets the q0345 cap); the receipt clock against NTP (<= 1 s). No price is stored."""
    import tempfile  # noqa: PLC0415

    res: dict = {}
    r0 = lim.requests
    evs, info = search_all(lim, SMOKE_QUERY)
    res["e_gamma_paging"] = _chk(info["pages"] >= 1 and info["total"] is not None, pages=info["pages"], events=len(evs), total=info["total"])
    toks = out_of_frame_tokens(lim)
    post = ctx.get("post") or books_poster()
    n_post = 0
    data, err = books_batch(post, toks[:BOOKS_BATCH])
    n_post += 1
    if data is None and is_transient(err):
        raise NotNow(f"smoke: POST /books transient failure ({err}); pending, nothing written")
    got = sum(1 for b in (data or []) if isinstance(b, dict) and b.get("asset_id") in set(toks[:BOOKS_BATCH]))
    res["e_books_100"] = _chk(got == BOOKS_BATCH, books=got, error=err)
    t0 = time.time()
    recs, gaps = run_pass(post, toks, t0)
    n_post += math.ceil(len(set(toks)) / BOOKS_BATCH)
    if any(is_transient(g.get("why", "")) for g in gaps):
        raise NotNow("smoke: a /books batch of the full pass failed transiently; pending, nothing written")
    nbytes = len(pass_bytes(recs))
    with tempfile.TemporaryDirectory() as td:  # the out-of-frame pass is measured, never kept
        (Path(td) / "pass.jsonl.gz").write_bytes(pass_bytes(recs))
    res["e_full_pass_bytes"] = _chk(len(toks) >= 0.9 * SMOKE_FULL_PASS_TOKENS and len(recs) >= 0.9 * len(set(toks)) and nbytes > 0, tokens=len(set(toks)), records=len(recs), gaps=len(gaps),
                                    bytes_per_pass=nbytes, cap_gb=collector_cap_gb(nbytes), scheduled_passes=len(scheduled_slots()), seconds=round(time.time() - t0, 2))
    try:
        off = (ctx.get("ntp") or ntp_offset)()
        res["e_ntp_offset"] = _chk(abs(off) <= NTP_MAX_OFFSET_S, offset_s=off)
    except OSError as exc:  # an unreachable NTP server is a transient fault: pending, never a counted FAIL (round 2 fix 3)
        raise NotNow(f"smoke: NTP query failed ({type(exc).__name__}); pending, nothing written") from None
    total = lim.requests - r0 + n_post
    res["_requests"] = {"pass": total <= SMOKE_MAX_REQUESTS, "requests": total}
    return res


def declared() -> dict:
    return {"family": "E", "label": LABEL_E,
            "dates": {"freeze": T15_E_FREEZE, "pre": T15_E_PRE, "on": T15_E_ON, "off": T15_E_OFF, "end": T15_E_END, "cpu_hold": list(T15_CPU_HOLD), "cpu_dry_run": list(T15_CPU_DRY_RUN),
                      "election_day": ELECTION_DAY, "poll_close_range": list(POLL_CLOSE_RANGE)},
            "frame": {"queries": list(QUERIES), "status": SEARCH_STATUS, "paging": "to hasMore = false", "walk": {"tag": WALK_TAG_ID, "end_window": list(WALK_END_WINDOW), "min": COMPLETENESS_MIN},
                      "race_rules": {"senate": SENATE_RE.pattern, "governor": GOVERNOR_RE.pattern, "house": HOUSE_RE.pattern, "exclude": RACE_EXCLUDE_RE.pattern, "general_date": GENERAL_DATE_RE.pattern,
                                     "control": CONTROL_RE.pattern},
                      "trade_market": "(a) a party member / market naming Democrat(ic); else (b) the D candidate member by the GE0 party map; D-terms = D YES mid",
                      "two_party": "the two highest-priced members at the q0344 read are one D and one R; a single-member D party market passes (single_party_market, reported)",
                      "control": "the D member of the national Senate / House control markets (single candidate, else the coordinator's pre-freeze override naming one candidate from the q0341 census); missing -> net-of-control unknown (E1 cannot advance)", "tier": f"top {TIER_LIQUID_SHARE:.4f} by Gamma liquidity at T15_E_pre"},
            "ge0": {"dir": GE0_DIR_REL, "files": GE0_FILES, "versions": GE0_VERSIONS, "archive": GE0_ARCHIVE_REL, "passes": list(GE0_PASSES), "years": list(SIGN_YEARS),
                    "sign_rule": "+1/-1 only if both passes, the vote-mode order and both years agree, every input cites an archived sha256 and the audit is 'supported'; else 0",
                    "forbidden_source_kinds": list(GE0_FORBIDDEN_SOURCE_KINDS), "pin": "ge0_bundle_sha256 = sha256 of the sorted JSON of the five per-file sha256s; MANDATORY --ge0-sha256",
                    "schemas": GE0_SCHEMAS},
            "units": {"band": list(BAND), "spread_max": SPREAD_MAX, "read_lag_a_s": READ_LAG_A_S, "read_lag_b_s": READ_LAG_B_S, "t_a_offset_s": T_A_OFFSET_S, "t_b_offset_s": T_B_OFFSET_S,
                      "t_b_rule": "mid whatever the spread; no ask -> 1, no bid -> 0; no exclusion at t_b", "state_weight": "1 per state"},
            "e1": {"stat": "sum_h w_h (1/2 mean_{+,h} d - 1/2 mean_{-,h} d); m_h = n+ n- / (n+ + n-)", "floor": E1_FLOOR, "sign_share_min": E1_SIGN_SHARE_MIN, "perm": {"draws": c15.PERM_DRAWS, "seed": c15.SEED_PERM},
                   "net_of_control_p": NET_CONTROL_P, "logit_clamp": list(LOGIT_CLAMP), "placebo_window_s": list(PLACEBO_WINDOW_S), "placebo_fail_p": PLACEBO_P_FAIL,
                   "robust": {"t_a_s": list(T_A_ROBUST_S), "t_b_s": list(T_B_ROBUST_S), "p": ROBUST_P, "senate_gov_min_per_sign": SENATE_GOV_MIN_PER_SIGN, "top_states_per_sign": TOP_STATES_PER_SIGN}},
            "e2": {"floor": E2_FLOOR, "w_star": c15.W_STAR, "no_depth_size": NO_DEPTH_SIZE, "fee_floor": c15.FEE_FLOOR, "exit_robust_s": T_B_ROBUST_S[0],
                   "support": "states with both side nets (the permutation's support)"},
            "gates": {"gec": {"races": GEC_MIN_RACES, "states": GEC_MIN_STATES, "per_sign": GEC_MIN_PER_SIGN}, "ge": {"states": GE_MIN_STATES, "per_sign": GE_MIN_PER_SIGN},
                      "gep": {"sigma_d": GEP_SIGMA_D, "max_mde": GEP_MAX_MDE, "z": GEP_Z}},
            "collector": {"grid_s": GRID_S, "night_grid_s": NIGHT_GRID_S, "batch": BOOKS_BATCH, "levels": BOOK_LEVELS, "degraded_levels": BOOK_LEVELS_DEGRADED, "rps": BOOKS_RPS,
                          "map_refresh_s": MAP_REFRESH_S, "cap": {"margin": CAP_MARGIN, "min_gb": CAP_MIN_GB}, "host_protect_free_gb": HOST_PROTECT_FREE_GB, "no_exit75_in_window": True,
                          "pre_night_free_margin_gb": PRE_NIGHT_FREE_MARGIN_GB, "book_fields": list(BOOK_FIELDS), "hash": "discarded", "nice": COLLECTOR_NICE, "mem_mb": COLLECTOR_MEM_MB},
            "cron": {"file": CRON_FILE_REL, "lines": cron_lines(), "hold": {"lane": HOLD_LANE, "min_mem_mb": HOLD_MIN_MEM_MB, "placed": T15_CPU_HOLD_PLACE}, "watchdog_max_age_s": WATCHDOG_MAX_AGE_S,
                     "deploy_freeze": DEPLOY_FREEZE},
            "round2": {"closure": "a missing t_b read after closure evidence (token omitted by a successful batch, or the market unlisted / inactive in a map refresh) uses the last read before closure (mid by the one-sided rule; E2 exit at its best bid, none -> w*), counted as 'closed before t_b (last read)'; closure before t_a is a counted pre-entry state; without evidence a missing read is a gap",
                       "gamma": "collector Gamma calls without retries, short timeout, attempt marked first; tier only in [T15_E_pre, T15_E_on); a snapshot at or after T15_E_on is never used",
                       "trade_market": "several members naming Democrat(ic) -> ambiguous, excluded and counted", "placebo": "an untestable pre-night placebo is unknown: E1 cannot advance",
                       "calendar": "first commit of model_specs/cb15_v1.json carrying the pinned race-map sha256 value", "smoke": "transient /books or NTP faults -> pending (exit 75), never a counted FAIL; out-of-frame tokens from order-book markets accepting orders"},
            "judgement": {"alpha": c15.E_JUDGE_ALPHA, "rule": "judged when it runs at p < min(0.01, alpha/k1), strict; never withdrawn; the final Holm only adds passes; no Stage 2 in CB15"},
            "smoke": {"needs": list(SMOKE_NEEDS), "max_requests": SMOKE_MAX_REQUESTS, "full_pass_tokens": SMOKE_FULL_PASS_TOKENS, "ntp_max_offset_s": NTP_MAX_OFFSET_S}}


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
