# ruff: noqa: E501
"""CB14-W: Wikipedia edit-burst lead for personnel and status markets (docs/research_lab/CREATIVE_BATCH_14.md CB14-W, section 10 items 1-3, 7-12). Rules part ``W``.

Frame (q0303, listing-date frame by a frozen query list on Gamma ``public-search``), pre-fetch gate GWC (q0305, counts only), MediaWiki revision metadata (q0306), Data API
prints (q0307), census (q0308, counts only), screen (q0309: W1, W2), the live collector (q0310) and the Stage-2 replication (q0311). EXPLORATORY: every line carries "L1,
historical" (Stage 1) or "L2, prospective live window, recorded books" (Stage 2). No edge, calibration or profitability claim. This module imports ``cb14_common`` and nothing from
the S family, so its rules hash is independent of S code.

W1 (lead from the move's start): ``L_D = 1`` iff a burst lies in ``[D0 - 120 min, D0 - 5 min]`` with the market's state at the burst at most ``V_D + 5c`` and an entry print
exists; the statistic is the mean excess ``L_D - pi_hat_D`` over the same subject's hot-period placebo anchors. W2: a burst-triggered taker at recorded prints.
"""

from __future__ import annotations

import bisect
import csv
import hashlib
import inspect
import json
import math
import re
import time
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import numpy as np

from . import cb8_common as cm
from . import cb14_common as c14
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

HOUR = 3600.0
DAY = 86400.0
MINUTE = 60.0
RUN = "h14_wiki"
LIVE_RUN = "h14_wiki_live"
FRAME_STATUS = "w_frame_complete"
REVISIONS_STATUS = "w_revisions_complete"
PRINTS_STATUS = "w_prints_complete"
LIVE_STATUS_CLOSED = "w_live_window_closed"
FRAME_OUTPUT_CAP_GB = 0.01
REVISIONS_OUTPUT_CAP_GB = 0.03
PRINTS_OUTPUT_CAP_GB = 0.02
LIVE_OUTPUT_CAP_GB = 0.05
LABEL_W = "L1, historical (fresh frame; no historical holdout)"
LABEL_W_REP = "L2, prospective live window, recorded books"

# ---- dates (section 1.2) ----------------------------------------------------------------------------------------------------------------------
W_LISTED = ("2023-07-01T00:00:00Z", "2026-03-01T00:00:00Z")  # markets LISTED (createdAt) in this window; no status, closedTime or outcome condition
W_CALENDAR_START = "2024-01-01T00:00:00Z"
T14_W_END = "2026-04-01T00:00:00Z"  # no W revision used in a feature, print, burst, decisive move or unit at or after it
T14_W2_FLOOR = "2026-10-26T00:00:00Z"
T14_W2_CAP = "2027-04-30T00:00:00Z"
W2_START_AFTER_FREEZE_D = 1
W2_WINDOW_D = 90
W2_STOP_BURSTS = 300
W2_STOP_SUBJECTS = 30
REVISION_LEAD_D = 30  # revisions are fetched from max(createdAt, W_CALENDAR_START) - 30 d

# ---- frame rules (section 1.4, CB14-W population) ----------------------------------------------------------------------------------------------
QUERIES = ("resign", "resigns", "resignation", "out as", "out by", "fired", "step down", "steps down", "removed as", "removed from", "leave office", "ousted", "impeached", "indicted", "charged")
SEARCH_STATUSES = ("closed", "active")
SEARCH_LIMIT = 100  # limit_per_type; paged by ``page`` until ``hasMore`` is false
SEARCH_MAX_PAGES = 60
EVENT_LOOKUP_MAX_REQ = 600  # section 2.8 (q0303 budget): event lookups for search events whose fields are missing; more is a declared source stall
EVENT_LOOKUP_PER_REQUEST = 50
TITLE_RE = re.compile(r"(?i)\b(resign(s|ed|ation)?|out as|out by|fired|steps? down|removed (as|from)|leaves? office|ousted|impeach(ed|ment)?|indicted|charged)\b")
DEATH_RE = re.compile(r"(?i)\b(dies?|death|pass(es)? away)\b")  # a reported stratum only
MENTION_RE = re.compile(r"(?i)\b(say|says|mention|mentions)\b")
MENTION_TAG_ID = "100343"
ENTERTAINMENT_RE = re.compile(r"(?i)\bwho will die in\b")
COACH_RE = re.compile(r"(?i)\b(head coach|coach|manager|general manager|quarterback|goalkeeper|striker|pitcher|athlete|player)\b")
CLASS_ORDER = ("indicted", "fired", "removed", "out_as", "resign")
CLASS_RES = {"indicted": re.compile(r"(?i)\b(indicted|charged)\b"), "fired": re.compile(r"(?i)\bfired\b"), "removed": re.compile(r"(?i)\b(removed (as|from)|ousted|impeach(ed|ment)?)\b"),
             "out_as": re.compile(r"(?i)\bout (as|by)\b"), "resign": re.compile(r"(?i)\b(resign(s|ed|ation)?|steps? down|leaves? office)\b")}
SPORTS_REGISTRY_SHA256 = "b47b3d20c0bbf71a4e0dc912b0a32533fcd7e796e2c289a4b525774c8857bce6"
SPORTS_REGISTRY_REL = "docs/research_lab/evidence_cb12/sports_tag_registry_20261018.json"
COMPLETENESS_MONTHS = ("2025-03", "2025-11")
COMPLETENESS_TAG_ID = 2  # Gamma politics tag
COMPLETENESS_MIN = 0.95
MIN_MARKETS_GWC, MIN_EVENTS_GWC, MIN_SUBJECTS_GWC = 150, 60, 40
AUDIT_PRECISION_MIN = 0.90
AUDIT_VERSION = "cb14-w-audit-v1"
AUDIT_FILE = "w_map_audit.json"
AUDIT_SAMPLE_FILE = "w_map_audit_sample.csv"
GAMMA_SEARCH = "https://gamma-api.polymarket.com/public-search"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_API = "https://en.wikipedia.org/w/api.php"
CLOB_BOOK = "https://clob.polymarket.com/book"
WIKI_MAX_REQ = 3000
ARTICLE_MIN_AGE_D = 30
# The entity rule is CB11-A's (``derive_query`` first entity) with its stop list plus a frozen office-word list; the source of the rule is pinned by sha256 (a mismatch is a refusal).
ENTITY_SOURCE_SHA256 = "dd03ff8cc845481276a3311a8a97a7185287181c76d8371a35d54529d11d87f7"
OFFICE_WORDS = ("president", "prime minister", "chancellor", "ceo", "chairman", "chair", "governor", "senator", "secretary", "minister", "mayor", "speaker", "director", "leader", "king",
                "queen", "premier", "commissioner", "attorney general", "justice", "judge", "general", "administration", "government", "congress", "parliament", "cabinet", "party")
MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug",
               "sep", "sept", "oct", "nov", "dec")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
GENERIC_CAP = ("Will", "Who", "What", "When", "Which", "How", "Does", "Is", "Are", "Can", "Do", "Did", "Yes", "No", "The", "A", "An", "By", "In", "On", "Before", "After", "Over", "Under",
               "Bitcoin Up", "Up", "Down", "Above", "Below")
GENERIC_NOUNS = ("ipo", "invasion", "election", "elections", "ceasefire", "recession", "inflation", "shutdown", "primary", "debate", "referendum", "treaty", "summit", "war", "peace")
STOP_LIST = tuple(sorted({s.lower() for s in (*MONTH_NAMES, *WEEKDAYS, *GENERIC_CAP, *GENERIC_NOUNS, *OFFICE_WORDS)}))
# Frozen demonym / country-name map for the story-day cluster way (written before any revision or print is read): the first match in this order wins; no match -> a singleton country.
COUNTRY_MAP = (("american", "US"), ("united states", "US"), ("u.s.", "US"), ("british", "GB"), ("english", "GB"), ("scottish", "GB"), ("welsh", "GB"), ("united kingdom", "GB"),
               ("canadian", "CA"), ("australian", "AU"), ("new zealand", "NZ"), ("irish", "IE"), ("french", "FR"), ("german", "DE"), ("italian", "IT"), ("spanish", "ES"),
               ("portuguese", "PT"), ("dutch", "NL"), ("belgian", "BE"), ("swiss", "CH"), ("austrian", "AT"), ("swedish", "SE"), ("norwegian", "NO"), ("danish", "DK"), ("finnish", "FI"),
               ("polish", "PL"), ("czech", "CZ"), ("hungarian", "HU"), ("romanian", "RO"), ("bulgarian", "BG"), ("greek", "GR"), ("turkish", "TR"), ("ukrainian", "UA"), ("russian", "RU"),
               ("israeli", "IL"), ("palestinian", "PS"), ("iranian", "IR"), ("iraqi", "IQ"), ("syrian", "SY"), ("lebanese", "LB"), ("saudi", "SA"), ("egyptian", "EG"), ("south african", "ZA"),
               ("nigerian", "NG"), ("kenyan", "KE"), ("ethiopian", "ET"), ("indian", "IN"), ("pakistani", "PK"), ("bangladeshi", "BD"), ("chinese", "CN"), ("japanese", "JP"),
               ("south korean", "KR"), ("north korean", "KP"), ("taiwanese", "TW"), ("philippine", "PH"), ("filipino", "PH"), ("indonesian", "ID"), ("thai", "TH"), ("vietnamese", "VN"),
               ("malaysian", "MY"), ("singaporean", "SG"), ("mexican", "MX"), ("brazilian", "BR"), ("argentine", "AR"), ("argentinian", "AR"), ("chilean", "CL"), ("colombian", "CO"),
               ("venezuelan", "VE"), ("peruvian", "PE"), ("ecuadorian", "EC"), ("bolivian", "BO"), ("cuban", "CU"), ("haitian", "HT"), ("israel", "IL"), ("ukraine", "UA"), ("russia", "RU"))
HEAD_RE = re.compile(r"(?i)\b(prime minister|president|chancellor|head of government|head of state|monarch|king|queen|premier|supreme leader|emperor)\b")

# ---- columns (section 1.1 stored fields; nothing here is a forbidden column) ---------------------------------------------------------------------
FRAME_COLUMNS = ["market_id", "event_id", "series_id", "condition_id", "token_yes", "yes_index", "neg_risk_market_id", "created_epoch", "end_epoch", "fee_rate", "cls", "death", "sports_tag",
                 "sports_re", "mention", "entertainment", "fetched_as", "term", "entity", "status", "key_source", "series_cf", "question", "event_title"]
SUBJECT_COLUMNS = ["entity", "page_id", "canonical_title", "description", "type", "status", "country", "head", "n_markets"]
OUTCOME_COLUMNS = ["market_id", "event_id", "yes_index", "outcome_prices", "uma_status"]
PAGE_COLUMNS = ["page_id", "title", "fetch_start", "first_rev_ts", "n_rev", "status"]
REV_COLUMNS = ["page_id", "revid", "ts", "size", "delta", "uidx", "bot", "revert", "unknown_user"]
BOT_COLUMNS = ["bot_key"]
TX_COLUMNS = ["market_id", "ts", "price", "pmin", "pmax", "size"]
REACH_COLUMNS = ["market_id", "oldest_ts", "truncated", "n_prints", "n_tx", "pages"]

# ---- bursts (section CB14-W; frozen a priori) --------------------------------------------------------------------------------------------------
BURST_WINDOW_S = 600.0
BURST_MIN_REVS = 3
BURST_MIN_USERS = 2
BURST_MIN_BYTES = 100
BURST_PCT = 99.0
BURST_BASELINE_D = (30, 1)  # percentile over [b - 30 d, b - 1 d]
BURST_REFRACTORY_S = 6 * HOUR
BOT_NAME_RE = re.compile(r"(?i)bot\b")
REVERT_TAGS = ("mw-undo", "mw-rollback", "mw-manual-revert")
REVERT_COMMENT_RE = re.compile(r"(?i)^\s*(revert(ed|ing)?|undo|undid|rv|rvv|reverted edits?)\b|\b(undid revision|revert(ed|ing)? (edit|edits|to|vandal)|rollback)\b")
BURST_GRIDS = {"base": (3, 600.0, 99.0), "min4": (4, 600.0, 99.0), "pct95": (3, 600.0, 95.0), "win5": (3, 300.0, 99.0)}  # (min revisions, window s, percentile): reported, uncounted
MW_MAXLAG = 5
RV_LIMIT = 500

# ---- prints, decisive moves, W1 (section CB14-W) ----------------------------------------------------------------------------------------------
STATE_LOOKBACK_S = 6 * HOUR
DECISIVE_PRICE = 0.90
DECISIVE_CONFIRM_S = 30 * MINUTE
DECISIVE_V_MAX = 0.50
DECISIVE_V_WINDOW = (24 * HOUR, 2 * HOUR)  # [D - 24 h, D - 2 h]
DECISIVE_RISE = 0.20
DECISIVE_D0_WINDOW_S = 2 * HOUR
DECISIVE_DEDUP_S = 7 * DAY
W1_LEAD_WINDOW = (120 * MINUTE, 5 * MINUTE)  # a lead burst lies in [D0 - 120 min, D0 - 5 min]
W1_LEAD_WINDOW_ROBUST = (60 * MINUTE, 5 * MINUTE)
W1_STATE_CAP = 0.05
W1_STATE_CAP_ROBUST = 0.02
ENTRY_WINDOW = (60.0, 15 * MINUTE)  # [b + 60 s, b + 15 min]  (signed offsets from the anchor, seconds)
ENTRY_WINDOW_ROBUST = (3 * MINUTE, 15 * MINUTE)
PLACEBO_ANCHORS = 11
PLACEBO_STEP_S = 6 * HOUR
PLACEBO_MIN_ANCHORS = 3
W1_FLOOR = 0.25
W1_MIN_MOVES, W1_MIN_SUBJECTS, W1_MIN_WEEKS = 40, 30, 15
SHIFT_RANGE_D = (30, 60)  # calibration placebo: bursts shifted by U[-60, -30] days
W1_MIN_CLASS_MOVES = 15
FIXED_LAGS_D = (7, 14, 21, 28)  # reported (uncounted) fixed-lag comparators

# ---- W2 (section CB14-W; section 2.1) ----------------------------------------------------------------------------------------------------------
W2_STATE_BAND = (0.05, 0.60)
W2_STATE_BAND_ROBUST = (0.05, 0.40)
W2_END_AHEAD_S = 3 * HOUR
W2_COVER = (6 * HOUR, 2.5 * HOUR)  # prints cover [b - 6 h, b + 2 h 30 min]
EXIT_WINDOW = (2 * HOUR, 2.5 * HOUR)
EXIT_WINDOW_ROBUST = (1 * HOUR, 1.5 * HOUR)
PAPER_SIZE = 100.0
W2_FLOOR = 0.01
COST_ROBUST_PER_SIDE = 0.01
W2_MIN_UNITS, W2_MIN_SUBJECTS, W2_MIN_WEEKS = 500, 40, 30
W2_REACH_MIN = 0.60
W2_BEFORE_MOVE_S = 60 * MINUTE
W2_BEFORE_MOVE_MAX = 0.05
RISE_WINDOW_S = 2 * HOUR
PREBURST_SHIFT_S = 24 * HOUR
PRE_ENTRY_WINDOW = (-(2 * HOUR + 15 * MINUTE), -2 * HOUR)  # GWP proxy: entry at the max print in [b - 2 h 15 min, b - 2 h]
PRE_EXIT_WINDOW = (-15 * MINUTE, 0.0)  # exit at the min print in [b - 15 min, b) (the right end is excluded)
GWP_W1_MAX_MDE = 0.50
GWP_W2_MAX_MDE_C = 0.02
FIXED_FEE_FLOOR = c14.FEE_FLOOR
WORST_CASE_P90 = c14.P90_ROUND_TRIP
RISE_MIN = 0.20

# ---- live collector (Stage 2) ---------------------------------------------------------------------------------------------------------------
RC_POLL_S = 60.0
RC_OVERLAP_S = 120.0
RC_GAP_S = 300.0
RC_LIMIT = 500
BOOK_OFFSETS_S = (60.0, 300.0, 900.0, 7200.0)  # b + 60 s, 5, 15 and 120 min
LIVE_FRAME_REFRESH_S = DAY
LIVE_MAX_BOOKS_PER_RUN = 40
W2REP_MIN_BURSTS, W2REP_MIN_SUBJECTS = 300, 30
W1REP_MIN_MOVES, W1REP_MIN_SUBJECTS = 20, 15
SMOKE_NEEDS = ("guards_fixture_W", "w_part_hashes", "w_public_search_paging", "w_search_fields", "w_entity_summary", "w_revisions_bounds", "w_bot_list", "w_data_api_reach", "w_recentchanges")
SMOKE_RV_TITLE = "Donald Trump"
SMOKE_RV_RANGE = ("2026-09-15T00:00:00Z", "2026-10-15T00:00:00Z")  # out of every W window
SMOKE_RV_LIMIT = 1
SMOKE_MAX_REQUESTS = 30
SMOKE_SUBJECT_QUERY = "resign"
SMOKE_SUBJECTS = 5


def ep(s: str) -> float:
    return c14.ep(s)


def listed_window() -> tuple[float, float]:
    return ep(W_LISTED[0]), ep(W_LISTED[1])


def w_end() -> float:
    return ep(T14_W_END)


def calendar_window() -> tuple[float, float]:
    return ep(W_CALENDAR_START), ep(T14_W_END)


# =====================================================================================================================================================
# Guards: no W row at or after T14_W_end, the forbidden-field fixtures, the sports registry
# =====================================================================================================================================================


def require_before_w_end(ts: float, label: str = "row") -> float:
    """Every stored W row, print, burst, decisive move and unit lies before ``T14_W_END`` (section 1.2). ``T14_W_END - 1 s`` is accepted, ``T14_W_END`` is refused."""
    if not (math.isfinite(ts) and ts < w_end()):
        raise Refused(f"W {label} at {ts} is at or after T14_W_end {T14_W_END}")
    return ts


def keep_before_w_end(rows: Iterable[dict], key: str = "ts") -> list[dict]:
    """The rows strictly before ``T14_W_END`` (rows at or after it are dropped at the source, never stored)."""
    end = w_end()
    return [r for r in rows if math.isfinite(c14.num(r.get(key))) and c14.num(r.get(key)) < end]


FORBIDDEN_FIELD_KEYS = ("side", "proxyWallet", "name", "pseudonym", "user", "userid", "mw-reverted", "outcomePrices", "closedTime", "transactionHash")


def clean_revision_row(row: dict) -> dict:
    """The only form a revision leaves memory in: the declared ``REV_COLUMNS`` (no user name, no user id, no comment text, no tags, no ``mw-reverted``)."""
    out = {k: row.get(k) for k in REV_COLUMNS}
    c14.assert_clean_columns(out.keys())
    return out


def sports_registry_ids(root: Path | None = None) -> set[str]:
    """The CB12 frozen sports tag registry (venue metadata; sha256 pinned): a mismatch or a missing file is a refusal."""
    from . import provenance  # noqa: PLC0415

    p = (Path(root) if root is not None else provenance.REPO_ROOT) / SPORTS_REGISTRY_REL
    if not p.is_file():
        raise Refused(f"sports registry {p} not found")
    if hashlib.sha256(p.read_bytes()).hexdigest() != SPORTS_REGISTRY_SHA256:
        raise Refused(f"sports registry {p.name} sha256 differs from the pinned {SPORTS_REGISTRY_SHA256}")
    return {str(x) for x in json.loads(p.read_text()).get("tag_ids", [])}


# =====================================================================================================================================================
# Frame: search paging, market parse, classification, status
# =====================================================================================================================================================


def listish(v) -> list:
    return c14.c12.listish(v)


def search_all(lim, term: str, status: str, *, page_limit: int = SEARCH_LIMIT, max_pages: int = SEARCH_MAX_PAGES) -> tuple[list[dict], dict]:
    """Gamma ``public-search`` events for one term and status, paged until ``pagination.hasMore`` is false. Returns (events, info). More than ``max_pages`` pages is a refusal
    (the cap is a guard against a paging loop, never a silent truncation)."""
    out: list[dict] = []
    info = {"pages": 0, "total": None}
    for page in range(1, max_pages + 1):
        st, data = lim.get(GAMMA_SEARCH, {"q": term, "events_status": status, "limit_per_type": page_limit, "page": page})
        if st != 200 or not isinstance(data, dict):
            raise ApiError(f"public-search status {st}")
        info["pages"] += 1
        evs = [e for e in (data.get("events") or []) if isinstance(e, dict)]
        out.extend(evs)
        pg = data.get("pagination") or {}
        info["total"] = pg.get("totalResults", info["total"])
        if not pg.get("hasMore"):
            return out, info
    raise Refused(f"public-search q={term!r} {status} still has more pages after {max_pages}")


def event_needs_lookup(ev: dict, sports_ids: set[str]) -> bool:
    """A ``public-search`` event with at least one W-candidate market (binary; title or death regex) that lacks a field the frame rules read: the event's ``tags`` or ``series`` key, a
    market's ``createdAt``, or ``negRiskMarketID`` on a negRisk event. Such events are looked up on Gamma ``/events`` (section 6 budget: <= 600 requests) before parsing."""
    ms = [m for m in (ev.get("markets") or []) if isinstance(m, dict) and parse_market(m, ev, fetched_as="", term="", sports_ids=sports_ids) is not None]
    if not ms:
        return False
    if "tags" not in ev or "series" not in ev:
        return True
    return any("createdAt" not in m or (bool(ev.get("negRisk")) and "negRiskMarketID" not in m) for m in ms)


def lookup_events(lim, ids: list[str], *, per_request: int = EVENT_LOOKUP_PER_REQUEST) -> tuple[dict[str, dict], int]:
    """Full Gamma events by id (closed first, then without the filter; <= 50 ids per request). Returns ({id: event}, requests used)."""
    found: dict[str, dict] = {}
    n = 0
    for closed in (True, False):
        want = [str(i) for i in ids if str(i) not in found]
        if not want:
            break
        params: dict = {"id": want, "limit": per_request}
        if closed:
            params["closed"] = "true"
        st, data = lim.get(c14.GAMMA_EVENTS, params)
        n += 1
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"gamma events lookup status {st}")
        for e in data:
            if isinstance(e, dict) and str(e.get("id")) in want:
                found[str(e["id"])] = e
    return found, n


def market_class(question: str) -> str:
    """Death markets form a reported stratum; otherwise the first matching class of ``CLASS_ORDER`` ('' = no title match)."""
    if DEATH_RE.search(question or ""):
        return "death"
    for c in CLASS_ORDER:
        if CLASS_RES[c].search(question or ""):
            return c
    return ""


def parse_market(m: dict, ev: dict, *, fetched_as: str, term: str, sports_ids: set[str]) -> dict | None:
    """One frame row (whitelisted Gamma fields only) or None if the market is not a binary Yes/No market or its question matches neither the W title regex nor the death regex.
    ``outcomePrices``, ``umaResolutionStatus`` and ``closedTime`` are never read here (``parse_outcome`` reads the first two for the guarded file)."""
    labels = [str(x).strip().lower() for x in listish(m.get("outcomes"))]
    toks = [str(x) for x in listish(m.get("clobTokenIds"))]
    if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2 or m.get("id") is None:
        return None
    q = str(m.get("question") or "")
    cls = market_class(q)
    if not cls:
        return None
    tags = {str(t.get("id")) for t in (ev.get("tags") or []) if isinstance(t, dict) and t.get("id") is not None}
    title = str(ev.get("title") or "")
    ser = [s for s in (ev.get("series") or []) if isinstance(s, dict) and s.get("id") is not None]
    yi = labels.index("yes")
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    return {"market_id": str(m["id"]), "event_id": str(ev.get("id") or ""), "series_id": str(ser[0]["id"]) if ser else "", "condition_id": str(m.get("conditionId") or ""),
            "token_yes": toks[yi], "yes_index": yi, "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "created_epoch": c14.c12.parse_iso(m.get("createdAt")),
            "end_epoch": c14.c12.parse_iso(m.get("endDate")), "fee_rate": c14.num(fs.get("rate")), "cls": cls, "death": int(cls == "death"), "sports_tag": int(bool(tags & sports_ids)),
            "sports_re": int(bool(COACH_RE.search(q) or COACH_RE.search(title))), "mention": int(MENTION_TAG_ID in tags or bool(MENTION_RE.search(q))),
            "entertainment": int(bool(ENTERTAINMENT_RE.search(q) or ENTERTAINMENT_RE.search(title))), "fetched_as": fetched_as, "term": term, "entity": "", "status": "", "key_source": "",
            "series_cf": 0, "question": q[:200], "event_title": title[:200]}


def parse_outcome(m: dict, ev: dict, yes_index: int) -> dict:
    statuses = m.get("umaResolutionStatuses")
    return {"market_id": str(m["id"]), "event_id": str(ev.get("id") or ""), "yes_index": yes_index, "outcome_prices": json.dumps(listish(m.get("outcomePrices"))),
            "uma_status": str(m.get("umaResolutionStatus") or (statuses if statuses else ""))}


def listing_ok(created_epoch: float) -> bool:
    """The listing-date rule: ``createdAt`` in ``W_LISTED``; no status, close time or outcome enters."""
    a, b = listed_window()
    return bool(math.isfinite(created_epoch) and a <= created_epoch < b)


def key_status(row: dict, ids: set[str], keys: dict[str, set[str]]) -> tuple[bool, str]:
    """(dropped, source) under the FULL series rule (market id, event id, ``negRiskMarketID``, series id)."""
    if row["market_id"] in ids:
        return True, "market"
    if row["event_id"] in keys.get("event", set()):
        return True, "event"
    if row["neg_risk_market_id"] and row["neg_risk_market_id"] in keys.get("neg_risk_market", set()):
        return True, "neg_risk"
    if row["series_id"] and row["series_id"] in keys.get("series", set()):
        return True, "series"
    return False, ""


def frame_status(row: dict, ids: set[str], keys: dict[str, set[str]]) -> tuple[str, str]:
    """Order: listing window -> sports -> mention -> entertainment -> death stratum -> key drop. (Entity and summary stages follow, in ``subjects``.)"""
    if not listing_ok(row["created_epoch"]):
        return "dropped:window", ""
    if row["sports_tag"] or row["sports_re"]:
        return "dropped:sports", "tag" if row["sports_tag"] else "regex"
    if row["mention"]:
        return "dropped:mention", ""
    if row["entertainment"]:
        return "dropped:entertainment", ""
    if row["death"]:
        return "stratum:death", ""
    dropped, src = key_status(row, ids, keys)
    if dropped:
        return "dropped:key", src
    return "kept", ""


def full_series_counterfactual(row: dict, keys: dict[str, set[str]]) -> bool:
    return bool(row["series_id"] and row["series_id"] in keys.get("series", set()))


# =====================================================================================================================================================
# Entity rule, summary, country, audit
# =====================================================================================================================================================


def entity_source_sha256() -> str:
    """sha256 of the source of CB11-A's entity machinery (``external_news.derive_query``, ``_entities``, ``_nouns``, ``wiki_article_title`` and their tables)."""
    from . import external_news as en  # noqa: PLC0415

    parts = [inspect.getsource(en.derive_query), inspect.getsource(en._entities), inspect.getsource(en._nouns), inspect.getsource(en.wiki_article_title), json.dumps(sorted(en._STOP)),
             json.dumps(sorted(en._GENERIC_CAP)), en._CAP_RE.pattern, en._WORD_RE.pattern]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def check_entity_source() -> str:
    got = entity_source_sha256()
    if got != ENTITY_SOURCE_SHA256:
        raise Refused(f"entity rule source sha256 {got} differs from the pinned {ENTITY_SOURCE_SHA256}")
    return got


def entity_candidate(question: str, event_title: str) -> str:
    """``derive_query(question, event_title)['entities'][0]`` unless it is in the frozen stop list (case-insensitive; CB11-A's list plus the office words); '' when there is none."""
    from . import external_news as en  # noqa: PLC0415

    ents = en.derive_query(question, event_title or None).get("entities") or []
    if not ents:
        return ""
    e = str(ents[0]).strip()
    return "" if e.lower() in STOP_LIST else e


def wiki_summary(limw, entity: str) -> dict:
    """Wikipedia REST ``page/summary`` (redirects followed): type, page id, canonical title, short description. A non-200 is 'unavailable'; an exhausted retry raises."""
    from . import external_news as en  # noqa: PLC0415

    st, doc = limw.get(WIKI_SUMMARY + quote(en.wiki_article_title(entity), safe="_"), {})
    if st != 200 or not isinstance(doc, dict):
        return {"entity": entity, "status": st, "type": "", "page_id": "", "canonical": "", "description": ""}
    canon = str((doc.get("titles") or {}).get("canonical") or doc.get("title") or "").replace(" ", "_")
    return {"entity": entity, "status": 200, "type": str(doc.get("type") or ""), "page_id": str(doc.get("pageid") or ""), "canonical": canon,
            "description": str(doc.get("description") or "")[:200]}


def subject_ok(s: dict) -> bool:
    """A subject is mapped iff the summary is a ``standard`` article with a page id and a canonical title."""
    return bool(s.get("status") == 200 and s.get("type") == "standard" and s.get("page_id") and s.get("canonical"))


def country_of(description: str, entity: str = "") -> str:
    """The frozen description -> country map (first entry in ``COUNTRY_MAP`` order found in the lower-cased description wins); no match -> a singleton country of the subject."""
    d = (description or "").lower()
    for token, code in COUNTRY_MAP:
        if re.search(r"\b" + re.escape(token) + r"\b", d):
            return code
    return "single:" + hashlib.sha256((entity or description or "").encode()).hexdigest()[:12]


def is_head(description: str) -> bool:
    """Heads of government and state (frozen regex on the stored short description): the W1 robustness drop."""
    return bool(HEAD_RE.search(description or ""))


def audit_sample_rows(subjects: list[dict], frame_rows: list[dict]) -> list[list]:
    """Every mapped (entity, canonical title, description) pair plus one question of the subject, for the blind GW0 audit (no edit, price or outcome)."""
    q_by: dict[str, str] = {}
    for r in sorted(frame_rows, key=lambda x: x["market_id"]):
        q_by.setdefault(r["entity"], r["question"])
    return [[s["entity"], s["canonical_title"], s["description"], q_by.get(s["entity"], "")] for s in sorted(subjects, key=lambda x: x["entity"]) if s.get("status") == "mapped"]


AUDIT_SAMPLE_COLUMNS = ["entity", "canonical_title", "description", "question"]


def read_audit(path: Path, *, require_committed: bool = True) -> dict:
    """The GW0 audit file: ``{"version", "rule_revision", "labels": {entity: "match"|"not"}}`` committed before q0305. Returns the labels, the precision and the pairs to drop."""
    p = Path(path)
    if not p.is_file():
        raise NotNow(f"GW0 audit file {p.name} is missing (a blind science-reviewer labelling is committed first); pending")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"GW0 audit file {p} is not committed (or differs from HEAD)")
    doc = json.loads(p.read_text())
    if doc.get("version") != AUDIT_VERSION:
        raise Refused(f"GW0 audit version {doc.get('version')!r} != {AUDIT_VERSION!r}")
    labels = {str(k): str(v) for k, v in (doc.get("labels") or {}).items()}
    bad = [k for k, v in labels.items() if v not in ("match", "not")]
    if bad:
        raise Refused(f"GW0 audit has invalid labels for {bad[:3]}")
    n = len(labels)
    n_match = sum(1 for v in labels.values() if v == "match")
    prec = n_match / n if n else 0.0
    return {"labels": labels, "n": n, "n_match": n_match, "precision": prec, "pass": bool(n and prec >= AUDIT_PRECISION_MIN), "rule_revision": int(doc.get("rule_revision", 1)),
            "drop": sorted(k for k, v in labels.items() if v == "not")}


# =====================================================================================================================================================
# Revisions: parse, bot flag, revert-at-save, distinct-user index (user names are read in memory only)
# =====================================================================================================================================================


def bot_key(name: str) -> str:
    """Pseudonymised key of a bot-group account (the only account identifier ever written, and only for bots: the frozen Stage-1 bot list that the live poller reuses)."""
    return hashlib.sha256(f"arepo-cb14-bot|{name}".encode()).hexdigest()


def is_bot_name(name: str, bot_keys: set[str]) -> bool:
    return bool(name) and (bot_key(name) in bot_keys or bool(BOT_NAME_RE.search(name)))


def is_revert_at_save(tags: Iterable[str], comment: str) -> bool:
    """A revert known at save time: the saving revision's own ``mw-undo`` / ``mw-rollback`` / ``mw-manual-revert`` tag or a revert comment. ``mw-reverted`` (applied retroactively
    when a LATER edit reverts this one) is never used."""
    return bool(set(tags or ()) & set(REVERT_TAGS) or REVERT_COMMENT_RE.search(comment or ""))


def parse_ts(s) -> float:
    return c14.c12.parse_iso(s)


def rev_row(rev: dict, prev_size: float | None, users: dict, bot_keys: set[str], page_id: str) -> dict | None:
    """One stored revision row from a MediaWiki ``prop=revisions`` record: ``page_id, revid, ts, size, delta, uidx, bot, revert, unknown_user``. ``user`` / ``userid`` are used in
    memory (bot flag; a per-page distinct-user index in order of appearance, 0 = unknown) and are never returned. A revision-deleted user name is unknown, never a distinct user."""
    if not isinstance(rev, dict) or rev.get("revid") is None:
        return None
    ts = parse_ts(rev.get("timestamp"))
    size = c14.num(rev.get("size"))
    if not (math.isfinite(ts) and math.isfinite(size)):
        return None
    hidden = bool(rev.get("userhidden")) or rev.get("user") in (None, "")
    name = "" if hidden else str(rev.get("user"))
    key = None if hidden else (f"id:{rev['userid']}" if rev.get("userid") else f"name:{name}")
    if key is None:
        uidx = 0
    else:
        uidx = users.setdefault(key, len(users) + 1)
    delta = size - prev_size if prev_size is not None and math.isfinite(prev_size) else math.nan
    return {"page_id": str(page_id), "revid": int(rev["revid"]), "ts": ts, "size": size, "delta": delta, "uidx": int(uidx), "bot": int(is_bot_name(name, bot_keys)),
            "revert": int(is_revert_at_save(rev.get("tags") or [], str(rev.get("comment") or ""))), "unknown_user": int(hidden)}


def parse_revision_batch(revs: list[dict], page_id: str, users: dict, bot_keys: set[str], prev_size: float | None) -> tuple[list[dict], float | None]:
    """Rows of one API page of revisions in chronological order (the caller requests ``rvdir=newer``); returns (rows, size of the last revision, the next batch's parent size)."""
    rows: list[dict] = []
    ps = prev_size
    for rv in revs:
        if int(rv.get("parentid") or 0) == 0:
            ps = 0.0  # page creation: the parent size is 0
        row = rev_row(rv, ps, users, bot_keys, page_id)
        if row is None:
            continue
        rows.append(row)
        ps = row["size"]
    return rows, ps


# =====================================================================================================================================================
# Bursts (frozen a priori; features from revisions only)
# =====================================================================================================================================================


def eligible_revisions(revs: list[dict]) -> list[dict]:
    """Chronological non-bot, non-revert-at-save revisions (what a burst counts)."""
    return sorted((r for r in revs if not r["bot"] and not r["revert"]), key=lambda r: (r["ts"], r["revid"]))


def window_counts(t: np.ndarray, minutes: np.ndarray, window_s: float) -> np.ndarray:
    """Eligible-revision counts in ``(m - window_s, m]`` for each grid minute ``m``."""
    return np.searchsorted(t, minutes, side="right") - np.searchsorted(t, minutes - window_s, side="right")


def baseline_threshold(t: np.ndarray, b: float, window_s: float, pct: float, baseline_d: tuple[int, int] = BURST_BASELINE_D) -> float:
    """The ``pct`` percentile of the page's sliding-by-minute window counts over ``[b - 30 d, b - 1 d]`` (causal: nothing at or after ``b - 1 d`` enters)."""
    lo = math.floor((b - baseline_d[0] * DAY) / MINUTE) * MINUTE
    hi = math.floor((b - baseline_d[1] * DAY) / MINUTE) * MINUTE
    minutes = np.arange(lo, hi + MINUTE, MINUTE)
    return float(np.percentile(window_counts(t, minutes, window_s), pct))


def detect_bursts(revs: list[dict], *, hist_start: float, grid: tuple[int, float, float] = BURST_GRIDS["base"], min_users: int = BURST_MIN_USERS, min_bytes: float = BURST_MIN_BYTES,
                  refractory_s: float = BURST_REFRACTORY_S, since: float = -math.inf, until: float = math.inf) -> tuple[list[dict], dict]:
    """Bursts of one page. At the save time ``b`` of an eligible revision: >= ``grid[0]`` eligible revisions by >= 2 distinct known non-bot users in ``(b - window, b]`` with
    sum |delta size| >= 100 bytes, the count >= the ``grid[2]`` percentile of the page's own sliding window counts over ``[b - 30 d, b - 1 d]`` (a page whose history starts after
    ``b - 30 d`` has 'no baseline', counted), and ``b`` at least 6 h after the previous burst (one burst per 6 h). ``since`` / ``until`` bound the burst times returned (the history
    before ``since`` still feeds the window and the baseline). Revisions by unknown (revision-deleted) users count as revisions, never as distinct users."""
    min_revs, window_s, pct = grid
    el = eligible_revisions(revs)
    info = {"eligible": len(el), "candidates": 0, "no_baseline": 0, "below_percentile": 0, "refractory": 0}
    if not el:
        return [], info
    t = np.array([r["ts"] for r in el])
    u = [int(r["uidx"]) for r in el]
    d = np.nan_to_num(np.abs(np.array([c14.num(r["delta"]) for r in el])), nan=0.0)
    out: list[dict] = []
    last = -math.inf
    for i in range(len(el)):
        b = float(t[i])
        if b < since or b >= until:
            continue
        j0 = int(np.searchsorted(t, b - window_s, side="right"))
        count = i - j0 + 1
        if count < min_revs:
            continue
        users = {x for x in u[j0 : i + 1] if x != 0}
        if len(users) < min_users or float(d[j0 : i + 1].sum()) < min_bytes:
            continue
        info["candidates"] += 1
        if b < last + refractory_s:
            info["refractory"] += 1
            continue
        if hist_start > b - BURST_BASELINE_D[0] * DAY:
            info["no_baseline"] += 1
            continue
        thr = baseline_threshold(t, b, window_s, pct)
        if count < max(thr, min_revs):
            info["below_percentile"] += 1
            continue
        out.append({"b": b, "count": count, "users": len(users), "bytes": float(d[j0 : i + 1].sum()), "threshold": thr})
        last = b
    return out, info


# =====================================================================================================================================================
# Prints: transactions (VWAP, min, max in YES terms), state, coverage, decisive moves
# =====================================================================================================================================================


def build_transactions(prints: list[dict], yes_index: int) -> list[dict]:
    """Data API prints -> one row per transaction (the hash is discarded): the latest fill time, YES-terms VWAP, min and max YES-terms fill price and total size."""
    rows, _ = c14.c12.aggregate_transactions(prints, yes_index)
    out = []
    for r in rows:
        ys = [(f[1] if f[3] == yes_index else 1.0 - f[1]) for f in r["fills"]]
        out.append({"ts": r["ts"], "price": r["price"], "pmin": min(ys), "pmax": max(ys), "size": r["size"]})
    return out


class TxSeries:
    """The aggregated transactions of one market, sorted by time, with the newest-first print reach (``oldest_ts``, ``truncated``)."""

    def __init__(self, rows: list[dict], *, oldest_ts: float = math.nan, truncated: bool = False) -> None:
        rows = sorted(rows, key=lambda r: (r["ts"], r["price"], r["size"]))
        self.ts = np.array([float(r["ts"]) for r in rows])
        self.p = np.array([float(r["price"]) for r in rows])
        self.size = np.array([float(r["size"]) for r in rows])
        self.pmin = np.array([float(r.get("pmin", r["price"])) for r in rows])
        self.pmax = np.array([float(r.get("pmax", r["price"])) for r in rows])
        self.oldest_ts = float(oldest_ts)
        self.truncated = bool(truncated)

    def __len__(self) -> int:
        return len(self.ts)

    def span(self, a: float, b: float, *, right_closed: bool = True) -> tuple[int, int]:
        """Index range of transactions with time in ``[a, b]`` (or ``[a, b)``)."""
        return int(np.searchsorted(self.ts, a, side="left")), int(np.searchsorted(self.ts, b, side="right" if right_closed else "left"))

    def covered(self, t: float) -> bool:
        """A time is covered if the newest-first prints reach back past it (not truncated, or the oldest reachable print is at or before ``t``)."""
        return bool((not self.truncated) or (math.isfinite(self.oldest_ts) and self.oldest_ts <= t))

    def state(self, t: float) -> float | None:
        """The YES-terms price of the last transaction in ``[t - 6 h, t)``; None = 'no state'. An uncovered time has no state."""
        if not self.covered(t - STATE_LOOKBACK_S):
            return None
        lo, hi = self.span(t - STATE_LOOKBACK_S, t, right_closed=False)
        return float(self.p[hi - 1]) if hi > lo else None

    def vwap(self, a: float, b: float) -> float | None:
        lo, hi = self.span(a, b)
        if hi <= lo or self.size[lo:hi].sum() <= 0:
            return None
        return float((self.p[lo:hi] * self.size[lo:hi]).sum() / self.size[lo:hi].sum())

    def max_print(self, a: float, b: float, *, right_closed: bool = True) -> tuple[float, float, float] | None:
        """(price, time, size) of the transaction with the maximum YES-terms price in the window (earliest on ties)."""
        lo, hi = self.span(a, b, right_closed=right_closed)
        if hi <= lo:
            return None
        k = lo + int(np.argmax(self.p[lo:hi]))
        return float(self.p[k]), float(self.ts[k]), float(self.size[k])

    def min_print(self, a: float, b: float, *, right_closed: bool = True) -> tuple[float, float, float] | None:
        lo, hi = self.span(a, b, right_closed=right_closed)
        if hi <= lo:
            return None
        k = lo + int(np.argmin(self.p[lo:hi]))
        return float(self.p[k]), float(self.ts[k]), float(self.size[k])

    def last_after(self, t_after: float, until: float) -> tuple[float, float, float] | None:
        """The last transaction in ``(t_after, until)`` (the 'stale exit')."""
        lo = int(np.searchsorted(self.ts, t_after, side="right"))
        hi = int(np.searchsorted(self.ts, until, side="left"))
        return (float(self.p[hi - 1]), float(self.ts[hi - 1]), float(self.size[hi - 1])) if hi > lo else None


def decisive_move(tx: TxSeries, window: tuple[float, float] | None = None) -> dict | None:
    """The market's decisive move (price only; no outcome): ``D`` = the first transaction at >= 0.90 that a second transaction at >= 0.90 confirms within 30 min and whose
    YES-terms VWAP ``V_D`` over ``[D - 24 h, D - 2 h]`` (>= 1 transaction, covered) is <= 0.50; ``D0`` = the first transaction in ``[D - 2 h, D]`` at >= ``V_D + 20c``. Times are in
    the W calendar (or ``window``, used by W1-rep on the live window) and before ``T14_W_END`` for Stage 1. The 0.90 crossing ``D`` is reported only; every W1 lead is measured from ``D0``."""
    a, b = window if window is not None else calendar_window()
    for i in range(len(tx)):
        t = float(tx.ts[i])
        if t < a or t >= b or tx.p[i] < DECISIVE_PRICE:
            continue
        j_hi = int(np.searchsorted(tx.ts, t + DECISIVE_CONFIRM_S, side="right"))
        if not (j_hi > i + 1 and bool((tx.p[i + 1 : j_hi] >= DECISIVE_PRICE).any())):
            continue
        if not tx.covered(t - DECISIVE_V_WINDOW[0]):
            continue
        v = tx.vwap(t - DECISIVE_V_WINDOW[0], t - DECISIVE_V_WINDOW[1])
        if v is None or v > DECISIVE_V_MAX:
            continue
        lo, hi = tx.span(t - DECISIVE_D0_WINDOW_S, t)
        k0 = next((k for k in range(lo, hi) if tx.p[k] >= v + DECISIVE_RISE), None)
        if k0 is None:
            continue
        return {"D": t, "D0": float(tx.ts[k0]), "V": float(v)}
    return None


def dedupe_moves(moves: list[dict]) -> list[dict]:
    """One decisive move per subject per 7 days (the earliest over the subject's markets); ``moves`` carry ``subject`` and ``D``."""
    kept: list[dict] = []
    last: dict[str, float] = {}
    for mv in sorted(moves, key=lambda m: (m["D"], m["market_id"])):
        s = mv["subject"]
        if s in last and mv["D"] < last[s] + DECISIVE_DEDUP_S:
            continue
        last[s] = mv["D"]
        kept.append(mv)
    return kept


# =====================================================================================================================================================
# W1: lead from the move's start, excess over the subject's hot-period placebo
# =====================================================================================================================================================


def lead_indicator(bursts: list[float], tx: TxSeries, anchor: float, v: float, *, lead_window: tuple[float, float] = W1_LEAD_WINDOW, state_cap: float = W1_STATE_CAP,
                   entry_window: tuple[float, float] = ENTRY_WINDOW) -> int:
    """1 iff a burst ``b`` of the subject lies in ``[anchor - lead_window[0], anchor - lead_window[1]]`` with the market's state at ``b`` at most ``v + state_cap`` and an entry print
    in ``[b + entry_window[0], b + entry_window[1]]``. No state / no entry print -> that burst is no lead (conservative)."""
    i0 = bisect.bisect_left(bursts, anchor - lead_window[0])
    i1 = bisect.bisect_right(bursts, anchor - lead_window[1])
    for b in bursts[i0:i1]:
        s = tx.state(b)
        if s is None or s > v + state_cap:
            continue
        lo, hi = tx.span(b + entry_window[0], b + entry_window[1])
        if hi > lo:
            return 1
    return 0


def placebo_anchors(d0: float, tx: TxSeries, created: float) -> list[tuple[float, float]]:
    """(anchor, V(anchor)) for ``tau_k = D0 - 6 h k``, ``k = 1 .. 11``: after listing, covered at ``tau - 24 h``, with >= 1 transaction in ``[tau - 24 h, tau - 2 h]``."""
    out = []
    for k in range(1, PLACEBO_ANCHORS + 1):
        tau = d0 - PLACEBO_STEP_S * k
        if not (math.isfinite(created) and tau >= created and tx.covered(tau - DECISIVE_V_WINDOW[0])):
            continue
        v = tx.vwap(tau - DECISIVE_V_WINDOW[0], tau - DECISIVE_V_WINDOW[1])
        if v is not None:
            out.append((tau, v))
    return out


def w1_value(unit: dict, bursts: list[float], tx: TxSeries, *, lead_window: tuple[float, float] = W1_LEAD_WINDOW, state_cap: float = W1_STATE_CAP,
             entry_window: tuple[float, float] = ENTRY_WINDOW) -> tuple[float, dict]:
    """(L_D - pi_hat_D, detail). NaN (counted 'no placebo') when fewer than 3 hot-period anchors are valid."""
    kw = {"lead_window": lead_window, "state_cap": state_cap, "entry_window": entry_window}
    anchors = placebo_anchors(unit["D0"], tx, unit["created"])
    if len(anchors) < PLACEBO_MIN_ANCHORS:
        return math.nan, {"label": "no placebo", "anchors": len(anchors)}
    lead = lead_indicator(bursts, tx, unit["D0"], unit["V"], **kw)
    pi_hat = float(np.mean([lead_indicator(bursts, tx, tau, vv, **kw) for tau, vv in anchors]))
    return float(lead - pi_hat), {"L": lead, "pi_hat": pi_hat, "anchors": len(anchors)}


def w1_vector(units: list[dict], bursts_by_subject: dict[str, list[float]], tx_by_market: dict[str, TxSeries], **kw) -> np.ndarray:
    return np.array([w1_value(u, bursts_by_subject.get(u["subject"], []), tx_by_market[u["market_id"]], **kw)[0] for u in units], float)


def iso_week(ts: float) -> str:
    return c14.iso_week_of(ts)


def story_day(ts: float, country: str) -> str:
    return f"{c14.utc_day(ts)}|{country}"


def shifted_bursts(bursts_by_subject: dict[str, list[float]], rng: np.random.Generator) -> dict[str, list[float]]:
    """The subject time-shift calibration placebo: one uniform offset in ``[-60, -30]`` days per subject, applied to every burst of the subject."""
    out = {}
    for s in sorted(bursts_by_subject):
        off = -float(rng.uniform(SHIFT_RANGE_D[0], SHIFT_RANGE_D[1])) * DAY
        out[s] = sorted(b + off for b in bursts_by_subject[s])
    return out


# =====================================================================================================================================================
# W2: burst-triggered taker at recorded prints
# =====================================================================================================================================================


def market_rate(m: dict) -> float:
    return c14.taker_rate(m.get("fee_rate"))


def net_of(e: float, x: float, rate: float, extra_per_side: float = 0.0) -> float:
    """``x - e - r e (1 - e) - r x (1 - x)`` (minus ``extra_per_side`` on each side for the cost robustness)."""
    return float(x - e - c14.fee(rate, e) - c14.fee(rate, x) - 2.0 * extra_per_side)


def choose_market(markets: list[dict], txs: dict[str, TxSeries], t: float, *, band: tuple[float, float] = W2_STATE_BAND) -> tuple[dict | None, str, dict | None]:
    """(market, label, detail). The subject's listed market with the nearest scheduled end at or after ``t + 3 h`` whose state at ``t`` lies in ``band`` and whose prints cover
    ``[t - 6 h, t + 2 h 30 min]``. When none qualifies the label comes from the nearest-end candidate: 'no market', 'uncovered', 'no state' or 'state outside band'."""
    cands = sorted((m for m in markets if m["created_epoch"] <= t and math.isfinite(m["end_epoch"]) and m["end_epoch"] >= t + W2_END_AHEAD_S), key=lambda m: (m["end_epoch"], m["market_id"]))
    if not cands:
        return None, "no market", None
    first_label = None
    first_detail = None
    for m in cands:
        tx = txs.get(m["market_id"])
        if tx is None or not tx.covered(t - W2_COVER[0]):
            lab, st = "uncovered", (None if tx is None else tx.state(t))
        else:
            st = tx.state(t)
            if st is None:
                lab = "no state"
            elif not (band[0] <= st <= band[1]):
                lab = "state outside band"
            else:
                return m, "ok", {"state": st}
        if first_label is None:
            first_label, first_detail = lab, {"state": st, "market_id": m["market_id"]}
    return None, str(first_label), first_detail


def round_trip(tx: TxSeries, t: float, rate: float, *, entry_window: tuple[float, float] = ENTRY_WINDOW, exit_window: tuple[float, float] = EXIT_WINDOW, extra_per_side: float = 0.0,
               exit_right_closed: bool = True) -> dict:
    """Entry at the MAXIMUM YES-terms transaction price in ``[t + entry[0], t + entry[1]]`` (taker-adverse); exit at the MINIMUM price in ``[t + exit[0], t + exit[1]]``; if there is
    none, the last transaction AFTER the entry print and before ``t + exit[1]`` ('stale exit'); none after the entry print -> 'no exit'. Size = min(100, the entry print's size)."""
    ent = tx.max_print(t + entry_window[0], t + entry_window[1])
    if ent is None:
        return {"label": "no entry print"}
    e, t_e, e_size = ent
    stale = False
    ex = tx.min_print(t + exit_window[0], t + exit_window[1], right_closed=exit_right_closed)
    if ex is None:
        ex = tx.last_after(t_e, t + exit_window[1])
        stale = ex is not None
    if ex is None:
        return {"label": "no exit", "e": e, "t_e": t_e}
    x, t_x, _ = ex
    return {"label": "stale exit" if stale else "ok", "e": e, "t_e": t_e, "x": x, "t_x": t_x, "stale": stale, "size": min(PAPER_SIZE, e_size), "net": net_of(e, x, rate, extra_per_side)}


def w2_units(D: dict, *, shift_s: float = 0.0, entry_window: tuple[float, float] = ENTRY_WINDOW, exit_window: tuple[float, float] = EXIT_WINDOW, band: tuple[float, float] = W2_STATE_BAND,
             extra_per_side: float = 0.0, bursts: dict[str, list[float]] | None = None) -> dict:
    """The W2 units from the burst list: every burst ``b`` of a mapped subject whose rule time ``t = b - shift`` yields a trade market and an entry print. Returns ``units`` (with a
    net), ``labels`` (counts by label), ``would_be`` (bursts that would be units but for 'uncovered', 'no entry print' or 'no exit': the worst-case reach set) and the reached share."""
    a, bw = calendar_window()
    units: list[dict] = []
    would: list[dict] = []
    labels: Counter = Counter()
    for sid, bl in sorted((bursts if bursts is not None else D["bursts"]).items()):
        info = D["subjects"][sid]
        for b in bl:
            if not (a <= b and b + W2_COVER[1] < bw):
                labels["outside calendar"] += 1
                continue
            t = b - shift_s
            m, lab, det = choose_market(D["by_subject"].get(sid, []), D["txs"], t, band=band)
            base = {"subject": sid, "b": b, "t": t, "week": iso_week(b), "story": story_day(b, info["country"]), "quarter": quarter_of(b)}
            if m is None:
                labels[lab] += 1
                if lab == "uncovered" and not (det and det.get("state") is not None and not (band[0] <= det["state"] <= band[1])):
                    would.append({**base, "why": "uncovered"})
                continue
            tx = D["txs"][m["market_id"]]
            rt = round_trip(tx, t, market_rate(m), entry_window=entry_window, exit_window=exit_window, extra_per_side=extra_per_side)
            if rt["label"] in ("no entry print", "no exit"):
                labels[rt["label"]] += 1
                would.append({**base, "why": rt["label"]})
                continue
            st = det["state"]
            hi_lo, hi_hi = tx.span(t, t + RISE_WINDOW_S)
            rise = bool(hi_hi > hi_lo and float(tx.p[hi_lo:hi_hi].max()) >= st + RISE_MIN)
            prev = tx.state(t - W2_BEFORE_MOVE_S)
            labels["unit"] += 1
            if rt["stale"]:
                labels["stale exit"] += 1
            units.append({**base, "market_id": m["market_id"], "state": st, "state_prev": prev, "rise": rise, **{k: rt[k] for k in ("e", "t_e", "x", "t_x", "stale", "size", "net")}})
    return {"units": units, "labels": dict(labels), "would_be": would}


def quarter_of(ts: float) -> str:
    d = datetime.fromtimestamp(ts, tz=UTC)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"



def w2_clusters(units: list[dict]) -> dict[str, np.ndarray]:
    return {"subject": np.array([u["subject"] for u in units]), "week": np.array([u["week"] for u in units]), "story": np.array([u["story"] for u in units])}


def worst_case_net(units: list[dict]) -> float:
    """``w* = min(-9.3c, m0)`` with ``m0`` the mean net of covered units without a >= 20c rise within 2 h (what a false burst costs in this population)."""
    base = [u["net"] for u in units if not u["rise"]]
    m0 = float(np.mean(base)) if base else WORST_CASE_P90
    return float(min(WORST_CASE_P90, m0))


def proxy_units(D: dict) -> list[dict]:
    """GWP proxy units (no post-burst information): the pre-burst round trip at each burst: entry at the max print in ``[b - 2 h 15 min, b - 2 h]``, exit at the min print in
    ``[b - 15 min, b)``, fees as W2, on the market W2 would choose at ``b``."""
    a, bw = calendar_window()
    out = []
    for sid, bl in sorted(D["bursts"].items()):
        info = D["subjects"][sid]
        for b in bl:
            if not (a <= b and b + W2_COVER[1] < bw):
                continue
            m, lab, det = choose_market(D["by_subject"].get(sid, []), D["txs"], b)
            if m is None:
                continue
            rt = round_trip(D["txs"][m["market_id"]], b, market_rate(m), entry_window=PRE_ENTRY_WINDOW, exit_window=PRE_EXIT_WINDOW, exit_right_closed=False)
            if rt["label"] in ("ok", "stale exit"):
                out.append({"subject": sid, "week": iso_week(b), "story": story_day(b, info["country"]), "net": rt["net"]})
    return out


def proxy_se(units: list[dict]) -> dict:
    """Only clustered standard errors are written (never the proxy's point estimate): the largest CR1 SE over the three ways and the implied MDE."""
    if len(units) < 2:
        return {"n": len(units), "se_max_over_ways": None, "mde": None}
    v = np.array([u["net"] for u in units])
    se = c14.max_se_over_ways(v, {k: np.array([u[k] for u in units]) for k in ("subject", "week", "story")})
    return {"n": len(units), "se_max_over_ways": float(se), "mde": float(c14.mde(se))}


def mean_or_nan(v) -> float:
    v = np.asarray(v, float)
    return float(v.mean()) if len(v) else math.nan


def _p(v, clusters, **kw) -> dict:
    return c14.cluster_p(np.asarray(v, float), clusters, **kw)


def sub_clusters(clusters: dict[str, np.ndarray], mask) -> dict[str, np.ndarray]:
    return {k: np.asarray(v)[mask] for k, v in clusters.items()}


def sign_pass(est: float, ref: float) -> bool:
    return c14.sign_ok(est, ref)


def sub_check(v, clusters, ref_mean: float, *, mask=None, need_p: float | None = None) -> dict:
    """A binding sub-check: the estimate keeps the sign of ``ref_mean`` and, if ``need_p`` is given, is testable with a one-sided p < ``need_p`` (not testable = not met)."""
    v = np.asarray(v, float)
    cl = clusters if mask is None else sub_clusters(clusters, mask)
    vv = v if mask is None else v[mask]
    est = mean_or_nan(vv)
    out = {"n": int(len(vv)), "estimate": est, "sign_ok": bool(sign_pass(est, ref_mean))}
    if need_p is not None:
        r = _p(vv, cl, min_units=1, min_first_clusters=1) if len(vv) >= 2 else {"p": 1.0, "testable": False, "small_g_rules_hold": False}
        out.update(p=r["p"], testable=bool(r["testable"]), small_g_rules_hold=bool(r.get("small_g_rules_hold")), p_ok=c14.p_pass(r, need_p))
        out["met"] = bool(out["sign_ok"] and out["p_ok"])
    else:
        out["met"] = bool(out["sign_ok"])
    return out


def top_drop_check(v, clusters: dict[str, np.ndarray], way: str, floor: float, alpha: float = c14.GATE_P, **kw) -> dict:
    """Drop the 5 clusters of ``way`` with the largest absolute contribution; the p threshold (small-G rule included) and the floor must hold on what remains."""
    v = np.asarray(v, float)
    keep = c14.top_k_drop_mask(v, clusters[way])
    r = _p(v[keep], sub_clusters(clusters, keep), **kw)
    est = mean_or_nan(v[keep])
    return {"n": int(keep.sum()), "estimate": est, "p": r["p"], "met": bool(c14.p_pass(r, alpha) and est >= floor)}


def loqo_check(v, quarters, ref_mean: float) -> dict:
    """Leave-one-quarter-out sign: every leave-one-out mean keeps the sign of ``ref_mean``."""
    v = np.asarray(v, float)
    q = np.asarray(quarters).astype(str)
    res = {}
    for k in sorted(set(q)):
        res[k] = mean_or_nan(v[q != k])
    return {"by_quarter": res, "met": bool(res) and all(sign_pass(x, ref_mean) for x in res.values())}


def half_check(v, times, ref_mean: float) -> dict:
    v = np.asarray(v, float)
    halves, _ = c14.halves_and_quarters(times)
    h = np.asarray(halves)
    est = [mean_or_nan(v[h == i]) for i in (0, 1)]
    return {"by_half": est, "met": all(sign_pass(x, ref_mean) for x in est)}


def w2_test(D: dict, *, with_checks: bool = True) -> dict:
    """W2 on the historical W calendar. Returns p (max over subject, ISO week and story-day), the mean net per share, the floor, and the binding checks (pre-burst placebo at b - 24 h
    must not pass p < 0.01; 'before the move'; worst-case reach; cost, exit, band, entry-window, entity, stale-exit, top-5, quarter and half robustness)."""
    pk = w2_units(D)
    units = pk["units"]
    out: dict = {"test": "W2", "label": LABEL_W, "labels": pk["labels"], "n": len(units)}
    if len(units) < 2:
        out.update(testable=False, p=1.0, effect=None, advance=False, verdict="not testable (units)")
        return out
    v = np.array([u["net"] for u in units])
    cl = w2_clusters(units)
    res = _p(v, cl)
    est = float(v.mean())
    floor_ok = bool(est >= W2_FLOOR)
    out.update(testable=res["testable"], p=res["p"], effect=est, floor_ok=floor_ok, ways=res["ways"], small_g_rules_hold=res["small_g_rules_hold"],
               size_weighted=float(np.average(v, weights=[u["size"] for u in units])))
    if not with_checks:
        return out
    checks: dict = {}
    pre = w2_units(D, shift_s=PREBURST_SHIFT_S)["units"]
    if len(pre) >= 2:
        pv = np.array([u["net"] for u in pre])
        pr = _p(pv, w2_clusters(pre))
        checks["pre_burst_placebo"] = {"n": len(pre), "p": pr["p"], "estimate": float(pv.mean()), "met": bool(not c14.p_pass(pr, c14.GATE_P))}
    else:
        checks["pre_burst_placebo"] = {"n": len(pre), "met": True, "note": "too few shifted units to pass p < 0.01"}
    # before the move
    keep = np.array([(u["state_prev"] is not None and abs(u["state"] - u["state_prev"]) <= W2_BEFORE_MOVE_MAX) for u in units])
    sub = v[keep]
    sub_est = mean_or_nan(sub)
    checks["before_the_move"] = {"n": int(keep.sum()), "estimate": sub_est, "met": bool(keep.sum() > 0 and sign_pass(sub_est, est) and abs(sub_est) >= 0.5 * abs(est))}
    # worst-case reach
    w_star = worst_case_net(units)
    add = pk["would_be"]
    if add:
        v_all = np.concatenate([v, np.full(len(add), w_star)])
        cl_all = {k: np.concatenate([cl[k], np.array([a[k] for a in add])]) for k in cl}
        rw = _p(v_all, cl_all)
        checks["worst_case_reach"] = {"w_star": w_star, "n_added": len(add), "p": rw["p"], "estimate": float(v_all.mean()), "met": bool(c14.p_pass(rw, c14.GATE_P) and v_all.mean() >= W2_FLOOR)}
    else:
        checks["worst_case_reach"] = {"w_star": w_star, "n_added": 0, "p": res["p"], "met": bool(c14.p_pass(res, c14.GATE_P) and floor_ok)}
    # cost and variants (each re-derived from the same bursts)
    cost = [net_of(u["e"], u["x"], market_rate(D["markets"][u["market_id"]]), COST_ROBUST_PER_SIDE) for u in units]
    checks["cost_plus_1c_per_side"] = {"estimate": mean_or_nan(cost), "met": bool(mean_or_nan(cost) > 0)}
    ex1 = w2_units(D, exit_window=EXIT_WINDOW_ROBUST)["units"]
    checks["exit_1h"] = sub_check([u["net"] for u in ex1], w2_clusters(ex1), est) if ex1 else {"met": False, "n": 0}
    bd = w2_units(D, band=W2_STATE_BAND_ROBUST)["units"]
    checks["band_05_40"] = sub_check([u["net"] for u in bd], w2_clusters(bd), est) if bd else {"met": False, "n": 0}
    ew = w2_units(D, entry_window=ENTRY_WINDOW_ROBUST)["units"]
    checks["entry_window_3_15"] = sub_check([u["net"] for u in ew], w2_clusters(ew), est) if ew else {"met": False, "n": 0}  # W2: sign only (CB14-W W2 robustness; p < 0.05 is W1's rule)
    attn = np.array([D["subjects"][u["subject"]]["attn"] for u in units])
    checks["drop_cb11a_entities"] = {**sub_check(v, cl, est, mask=~attn), "n_dropped": int(attn.sum())}
    stale = np.array([u["stale"] for u in units])
    checks["drop_stale_exit"] = {**sub_check(v, cl, est, mask=~stale), "n_dropped": int(stale.sum())}
    for way in ("subject", "week", "story"):
        checks[f"top5_{way}"] = top_drop_check(v, cl, way, W2_FLOOR)
    checks["loqo_sign"] = loqo_check(v, [u["quarter"] for u in units], est)
    checks["halves_sign"] = half_check(v, [u["b"] for u in units], est)
    out["checks"] = checks
    out["checks_met"] = bool(all(c.get("met") for c in checks.values()))
    out["reported"] = w2_reported(units, pk)
    return out


def w2_reported(units: list[dict], pk: dict) -> dict:
    """Reported, uncounted: precision, false-burst rate, net by class and band, capacity (entry-print sizes), the taker NO fade."""
    rise = np.array([u["rise"] for u in units], bool)
    nets = np.array([u["net"] for u in units])
    bands = {"05_20": (0.05, 0.20), "20_40": (0.20, 0.40), "40_60": (0.40, 0.60)}
    return {"precision": float(rise.mean()) if len(rise) else None, "false_burst_rate": float(1 - rise.mean()) if len(rise) else None,
            "net_by_band": {k: mean_or_nan(nets[[lo <= u["state"] <= hi for u in units]]) for k, (lo, hi) in bands.items()},
            "capacity": {"median_entry_size": float(np.median([u["size"] for u in units])) if units else None}, "n_stale_exit": int(sum(u["stale"] for u in units)),
            "taker_no_fade_mean": mean_or_nan(-nets) if len(nets) else None, "labels": pk["labels"]}


# =====================================================================================================================================================
# W1 test
# =====================================================================================================================================================


def w1_units(D: dict) -> tuple[list[dict], dict]:
    """Decisive moves of the mapped markets, one per subject per 7 days (the earliest over the subject's markets), articles at least 30 days old at ``D0``."""
    info = Counter()
    raw: list[dict] = []
    for sid, ms in sorted(D["by_subject"].items()):
        s = D["subjects"][sid]
        for m in sorted(ms, key=lambda x: x["market_id"]):
            tx = D["txs"].get(m["market_id"])
            if tx is None:
                info["no prints"] += 1
                continue
            mv = decisive_move(tx)
            if mv is None:
                continue
            first_rev = D["pages"].get(sid, {}).get("first_rev_ts", math.nan)
            if not (math.isfinite(first_rev) and mv["D0"] - first_rev >= ARTICLE_MIN_AGE_D * DAY):
                info["article too new"] += 1
                continue
            raw.append({"subject": sid, "market_id": m["market_id"], "cls": m["cls"], "created": m["created_epoch"], "country": s["country"], "head": s["head"], "attn": s["attn"], **mv})
    kept = dedupe_moves(raw)
    info["moves_before_dedup"] = len(raw)
    info["dedup_dropped"] = len(raw) - len(kept)
    for u in kept:
        u["week"] = iso_week(u["D0"])
        u["quarter"] = quarter_of(u["D0"])
    return kept, dict(info)


def w1_clusters(units: list[dict]) -> dict[str, np.ndarray]:
    return {"subject": np.array([u["subject"] for u in units]), "week": np.array([u["week"] for u in units])}


W1_TEST_KW = {"min_units": W1_MIN_MOVES, "min_first_clusters": W1_MIN_SUBJECTS, "min_clusters_by_way": {"week": W1_MIN_WEEKS}}


def w1_p(v, units_ok: list[dict], *, alpha: float | None = None) -> dict:
    return c14.cluster_p(np.asarray(v, float), w1_clusters(units_ok), alpha=alpha, **W1_TEST_KW)


def w1_calibration(D: dict, units: list[dict], *, n_draws: int = c14.PLACEBO_DRAWS, seed: int = c14.PLACEBO_SEEDS["W1_shift"]) -> dict:
    """Binding calibration placebo: each subject's bursts shifted by one uniform offset in [-60, -30] days; the W1 statistic and its p are recomputed on each draw (floors off)."""
    rng = np.random.default_rng(seed)
    ps: list[float | None] = []
    for _ in range(n_draws):
        sb = shifted_bursts(D["bursts"], rng)
        v = w1_vector(units, sb, D["txs"])
        ok = np.isfinite(v)
        if ok.sum() < 2:
            ps.append(None)
            continue
        r = w1_p(v[ok], [u for u, k in zip(units, ok, strict=True) if k], alpha=c14.GATE_P)
        ps.append(r["p"] if r["testable"] else None)
    rate = c14.placebo_advance_rate(ps)
    return {"note": "subject time-shift: bursts shifted by U[-60,-30] days; alternative guarded: busy-article subjects look 'led' in any 2-hour window", "n_draws": n_draws,
            "advance_rate": rate["advance_rate"], "n_advance": rate["n_advance"], "ok": bool(rate["holds"])}


def w1_variant(D: dict, units: list[dict], est: float, **kw) -> dict:
    """One binding W1 robustness variant: the statistic recomputed with other rule parameters keeps the sign and one-sided p < 0.05 (testable)."""
    v = w1_vector(units, D["bursts"], D["txs"], **kw)
    ok = np.isfinite(v)
    if ok.sum() < 2:
        return {"n": int(ok.sum()), "met": False}
    uo = [u for u, k in zip(units, ok, strict=True) if k]
    r = w1_p(v[ok], uo)
    e = float(v[ok].mean())
    return {"n": int(ok.sum()), "estimate": e, "p": r["p"], "testable": r["testable"], "met": bool(sign_pass(e, est) and c14.p_pass(r, 0.05))}


def w1_subset(v: np.ndarray, units: list[dict], mask: np.ndarray, est: float) -> dict:
    """A binding W1 sub-sample check on the primary values (the small-G rule per way applies; a way that is not testable is not met)."""
    uo = [u for u, k in zip(units, mask, strict=True) if k]
    vv = v[mask]
    if len(vv) < 2:
        return {"n": int(len(vv)), "met": False}
    r = c14.cluster_p(vv, w1_clusters(uo), min_units=1, min_first_clusters=1)
    e = float(vv.mean())
    return {"n": int(len(vv)), "estimate": e, "p": r["p"], "testable": r["testable"], "small_g_rules_hold": r["small_g_rules_hold"], "met": bool(sign_pass(e, est) and c14.p_pass(r, 0.05))}


def lead_distribution(D: dict, units: list[dict]) -> dict:
    """Reported (uncounted): CH123's lead from the 0.90 crossing ``D`` to the first burst in ``[D - 6 h, D + 2 h]`` (negative = after), median and share > 5 min, by class."""
    out: dict = {}
    leads = []
    for u in units:
        bl = D["bursts"].get(u["subject"], [])
        i = bisect.bisect_left(bl, u["D"] - 6 * HOUR)
        if i < len(bl) and bl[i] <= u["D"] + 2 * HOUR:
            leads.append((u["cls"], u["D"] - bl[i]))
    for name, sel in [("all", leads), *[(c, [x for x in leads if x[0] == c]) for c in ("resign", "out_as", "fired", "removed", "indicted")]]:
        vals = np.array([x[1] for x in sel], float)
        out[name] = {"n_with_burst": int(len(vals)), "median_s": float(np.median(vals)) if len(vals) else None, "share_gt_5min": float((vals > 300).mean()) if len(vals) else None}
    out["n_moves"] = len(units)
    return out


def w1_reported(D: dict, units: list[dict]) -> dict:
    """Reported, uncounted: the fixed-lag comparator (windows shifted by -7, -14, -21, -28 days), a burst-only placebo (no prints), the 'no placebo' drops, the lead distribution."""
    fixed = {}
    for lag in FIXED_LAGS_D:
        vals = []
        for u in units:
            tx = D["txs"][u["market_id"]]
            tau = u["D0"] - lag * DAY
            if not (tx.covered(tau - DECISIVE_V_WINDOW[0]) and tau >= u["created"]):
                continue
            vv = tx.vwap(tau - DECISIVE_V_WINDOW[0], tau - DECISIVE_V_WINDOW[1])
            if vv is not None:
                vals.append(lead_indicator(D["bursts"].get(u["subject"], []), tx, tau, vv))
        fixed[f"lag_{lag}d"] = {"n": len(vals), "share": mean_or_nan(vals) if vals else None}
    burst_only = {"hot": [], "fixed": [], "move": []}
    for u in units:
        bl = D["bursts"].get(u["subject"], [])
        for k in range(1, PLACEBO_ANCHORS + 1):
            tau = u["D0"] - PLACEBO_STEP_S * k
            burst_only["hot"].append(int(bisect.bisect_right(bl, tau - W1_LEAD_WINDOW[1]) > bisect.bisect_left(bl, tau - W1_LEAD_WINDOW[0])))
        for lag in FIXED_LAGS_D:
            tau = u["D0"] - lag * DAY
            burst_only["fixed"].append(int(bisect.bisect_right(bl, tau - W1_LEAD_WINDOW[1]) > bisect.bisect_left(bl, tau - W1_LEAD_WINDOW[0])))
        burst_only["move"].append(int(bisect.bisect_right(bl, u["D0"] - W1_LEAD_WINDOW[1]) > bisect.bisect_left(bl, u["D0"] - W1_LEAD_WINDOW[0])))
    short_listed = sum(1 for u in units if len(placebo_anchors(u["D0"], D["txs"][u["market_id"]], u["created"])) < PLACEBO_MIN_ANCHORS)
    return {"fixed_lag_lead_share": fixed, "burst_only_share": {k: (mean_or_nan(x) if x else None) for k, x in burst_only.items()},
            "no_placebo_moves": short_listed, "lead_distribution_from_crossing": lead_distribution(D, units)}


def w1_test(D: dict, *, placebo: bool = True, n_draws: int = c14.PLACEBO_DRAWS) -> dict:
    """W1: ``Delta_W1 = mean_D (L_D - pi_hat_D)`` over the decisive moves; one-sided > 0, floor +0.25, p = max over the subject and ISO-week ways, with the binding calibration
    placebo and the binding robustness list."""
    units, uinfo = w1_units(D)
    out: dict = {"test": "W1", "label": LABEL_W, "n_moves": len(units), "unit_info": uinfo}
    v = w1_vector(units, D["bursts"], D["txs"])
    ok = np.isfinite(v)
    out["n_no_placebo"] = int((~ok).sum())
    if ok.sum() < 2:
        out.update(testable=False, p=1.0, effect=None, advance=False, n=int(ok.sum()), verdict="not testable (moves)")
        return out
    units_ok = [u for u, k in zip(units, ok, strict=True) if k]
    vo = v[ok]
    res = w1_p(vo, units_ok)
    est = float(vo.mean())
    out.update(testable=res["testable"], p=res["p"], effect=est, floor_ok=bool(est >= W1_FLOOR), ways=res["ways"], small_g_rules_hold=res["small_g_rules_hold"], n=int(ok.sum()))
    checks: dict = {}
    checks["lead_window_60_5"] = w1_variant(D, units_ok, est, lead_window=W1_LEAD_WINDOW_ROBUST)
    checks["state_cap_2c"] = w1_variant(D, units_ok, est, state_cap=W1_STATE_CAP_ROBUST)
    checks["entry_window_3_15"] = w1_variant(D, units_ok, est, entry_window=ENTRY_WINDOW_ROBUST)
    attn = np.array([u["attn"] for u in units_ok])
    checks["drop_cb11a_entities"] = {**w1_subset(vo, units_ok, ~attn, est), "n_dropped": int(attn.sum())}
    head = np.array([u["head"] for u in units_ok])
    checks["drop_heads_of_government"] = {**w1_subset(vo, units_ok, ~head, est), "n_dropped": int(head.sum())}
    for cls in ("resign", "out_as"):
        sel = np.array([u["cls"] == cls for u in units_ok])
        checks[f"class_{cls}"] = w1_subset(vo, units_ok, sel, est) if sel.sum() >= W1_MIN_CLASS_MOVES else {"n": int(sel.sum()), "met": True, "note": f"fewer than {W1_MIN_CLASS_MOVES} moves: not applicable"}
    halves, _ = c14.halves_and_quarters([u["D0"] for u in units_ok])
    h = np.asarray(halves)
    checks["half_first"] = w1_subset(vo, units_ok, h == 0, est)
    checks["half_second"] = w1_subset(vo, units_ok, h == 1, est)
    checks["loqo_sign"] = loqo_check(vo, [u["quarter"] for u in units_ok], est)  # section 2.6 (iii): leave-one-quarter-out sign
    cl = w1_clusters(units_ok)
    for way in ("subject", "week"):
        keep = c14.top_k_drop_mask(vo, cl[way])
        checks[f"top5_{way}"] = w1_subset(vo, units_ok, keep, est)
    out["checks"] = checks
    out["checks_met"] = bool(all(c.get("met") for c in checks.values()))
    pl = w1_calibration(D, units_ok, n_draws=n_draws) if placebo else {"note": "skipped", "advance_rate": None, "n_draws": 0, "ok": None}
    out["placebo"] = pl
    out["placebo_ok"] = bool(pl.get("ok")) if placebo else None
    out["reported"] = w1_reported(D, units_ok)
    return out


# =====================================================================================================================================================
# Loading the W data (a census or screen job reads only these files)
# =====================================================================================================================================================


def read_rows(path: Path) -> list[dict]:
    return list(c14.read_csv_gz(path)) if Path(path).is_file() else []


def f(x) -> float:
    return c14.num(x)


def attn_titles(path: Path | None) -> set[str]:
    if path is None or not Path(path).is_file():
        return set()
    return {str(r["canonical_title"]).replace(" ", "_") for r in c14.read_csv_gz(Path(path))}


def load_frame(rdir: Path, audit: dict | None = None, drop_markets: set[str] | None = None) -> dict:
    """The frame and the subject map. Only ``kept`` markets whose subject is mapped (summary type standard) and not dropped by the GW0 audit are returned."""
    frame = read_rows(Path(rdir) / "frame.csv.gz")
    subs = read_rows(Path(rdir) / "subjects.csv.gz")
    drop = set((audit or {}).get("drop", []))
    subjects: dict[str, dict] = {}
    by_entity: dict[str, str] = {}
    for s in sorted(subs, key=lambda x: x["entity"]):
        if s["status"] != "mapped" or s["entity"] in drop:
            continue
        by_entity[s["entity"]] = s["page_id"]
        subjects.setdefault(s["page_id"], {"entity": s["entity"], "canonical": s["canonical_title"], "description": s["description"], "country": s["country"], "head": bool(int(s["head"])),
                                           "n_markets": 0})
        subjects[s["page_id"]]["n_markets"] += int(s["n_markets"])
    markets: dict[str, dict] = {}
    by_subject: dict[str, list[dict]] = {}
    for r in frame:
        if r["status"] != "kept" or r["entity"] not in by_entity or (drop_markets and r["market_id"] in drop_markets):
            continue
        row = {**r, "created_epoch": f(r["created_epoch"]), "end_epoch": f(r["end_epoch"]), "fee_rate": f(r["fee_rate"]), "yes_index": int(r["yes_index"])}
        sid = by_entity[r["entity"]]
        row["subject"] = sid
        markets[row["market_id"]] = row
        by_subject.setdefault(sid, []).append(row)
    return {"frame_rows": frame, "subjects": subjects, "markets": markets, "by_subject": by_subject}


def late_overlap(hist_root: Path, keys_report: dict | None, frame_rows: list[dict]) -> dict:
    """The id sets that were 'absent at q0302' and exist now (field-restricted id readers only): W markets whose market id, event id, ``negRiskMarketID`` or series id they hold are
    dropped from the census and the screen (counted). Nothing else under those roots is opened."""
    absent = list((keys_report or {}).get("sets_absent_at_q0302") or [])
    drop: set[str] = set()
    by_set: dict[str, int] = {}
    for rel in absent:
        p = c14.id_source_path(rel, Path(hist_root))
        if not p.is_file():
            continue
        cols = c14.read_id_columns(p)
        m_ids, e_ids = cols.get("market_id", set()), cols.get("event_id", set())
        n_ids, s_ids = cols.get("neg_risk_market_id", set()) | cols.get("negRiskMarketID", set()), cols.get("series_id", set())
        hit = {r["market_id"] for r in frame_rows if r["market_id"] in m_ids or r["event_id"] in e_ids or (r["neg_risk_market_id"] and r["neg_risk_market_id"] in n_ids) or (r["series_id"] and r["series_id"] in s_ids)}
        by_set[rel] = len(hit)
        drop |= hit
    return {"drop_markets": drop, "by_set": by_set, "absent_at_q0302": absent}


def load_bursts(rdir: Path, subjects: dict, grid: tuple[int, float, float] = BURST_GRIDS["base"]) -> tuple[dict[str, list[float]], dict, dict]:
    """(bursts by subject, per-page info, aggregate rule counters) from ``revisions.csv.gz`` and ``pages.csv.gz``; bursts lie in the W calendar and before ``T14_W_END``."""
    pages = {p["page_id"]: {"fetch_start": f(p["fetch_start"]), "first_rev_ts": f(p["first_rev_ts"]), "n_rev": int(p["n_rev"]), "status": p["status"]} for p in read_rows(Path(rdir) / "pages.csv.gz")}
    revs: dict[str, list[dict]] = {}
    for r in c14.read_csv_gz(Path(rdir) / "revisions.csv.gz") if (Path(rdir) / "revisions.csv.gz").is_file() else []:
        if r["page_id"] not in subjects:
            continue
        ts = f(r["ts"])
        if ts >= w_end():
            continue
        revs.setdefault(r["page_id"], []).append({"page_id": r["page_id"], "revid": int(r["revid"]), "ts": ts, "size": f(r["size"]), "delta": f(r["delta"]), "uidx": int(r["uidx"]),
                                                  "bot": int(r["bot"]), "revert": int(r["revert"]), "unknown_user": int(r["unknown_user"])})
    a, bw = calendar_window()
    bursts: dict[str, list[float]] = {}
    agg: Counter = Counter()
    for sid, rs in sorted(revs.items()):
        pg = pages.get(sid, {})
        hs = max(pg.get("fetch_start", math.inf), pg.get("first_rev_ts", math.inf))
        bl, info = detect_bursts(rs, hist_start=hs, grid=grid, since=a, until=bw)
        bursts[sid] = [x["b"] for x in bl]
        agg.update({k: v for k, v in info.items()})
        agg["unknown_user_revisions"] += sum(r["unknown_user"] for r in rs)
        agg["revisions"] += len(rs)
    return bursts, pages, dict(agg)


def load_txs(rdir: Path, markets: dict) -> dict[str, TxSeries]:
    reach = {r["market_id"]: r for r in read_rows(Path(rdir) / "reach.csv.gz")}
    rows: dict[str, list[dict]] = {}
    p = Path(rdir) / "tx.csv.gz"
    for r in c14.read_csv_gz(p) if p.is_file() else []:
        if r["market_id"] in markets and f(r["ts"]) < w_end():
            rows.setdefault(r["market_id"], []).append({"ts": f(r["ts"]), "price": f(r["price"]), "pmin": f(r["pmin"]), "pmax": f(r["pmax"]), "size": f(r["size"])})
    out = {}
    for mid, rc in reach.items():
        if mid in markets:
            out[mid] = TxSeries(rows.get(mid, []), oldest_ts=f(rc["oldest_ts"]), truncated=bool(int(rc["truncated"])))
    return out


def load_data(rdir: Path, *, audit: dict | None, attn_path: Path | None = None, grid: tuple[int, float, float] = BURST_GRIDS["base"], drop_markets: set[str] | None = None) -> dict:
    """Everything the census and the screen need. No outcome file is read."""
    fr = load_frame(rdir, audit, drop_markets)
    attn = attn_titles(attn_path)
    for s in fr["subjects"].values():
        s["attn"] = s["canonical"].replace(" ", "_") in attn
    bursts, pages, agg = load_bursts(rdir, fr["subjects"], grid)
    for sid in fr["subjects"]:
        bursts.setdefault(sid, [])
    return {**fr, "bursts": bursts, "pages": pages, "burst_info": agg, "txs": load_txs(rdir, fr["markets"])}


# =====================================================================================================================================================
# Gates, census (counts only), screen
# =====================================================================================================================================================


def not_run(label: str) -> dict:
    """A test behind a failed gate / audit / smoke is still counted, with p = 1."""
    return {"p": 1.0, "advance": False, "testable": False, "effect": None, "n": 0, "verdict": label}


def mde_w1(g_min: int) -> float:
    """``MDE_W1 = (z_0.99 + z_0.80) x 1.2 x 0.5 / sqrt(G_min)`` (the binomial worst case over the smaller of the two ways' G), with 3.16 for the z sum."""
    return float(c14.MDE_MULT * c14.MDE_INFLATE * 0.5 / math.sqrt(g_min)) if g_min > 0 else math.inf


def gates_w(D: dict, moves: list[dict], pk: dict, proxy: dict) -> dict:
    """GW (population) and GWP (power). W1 needs >= 40 usable decisive moves (>= 3 valid hot-period anchors, a price-only condition) in >= 30 subjects and >= 15 ISO weeks. W2 needs >= 500
    units in >= 40 subjects and >= 30 ISO weeks and a reach coverage of W2-eligible burst times of >= 60%."""
    usable = [u for u in moves if len(placebo_anchors(u["D0"], D["txs"][u["market_id"]], u["created"])) >= PLACEBO_MIN_ANCHORS]
    subj1, wk1 = {u["subject"] for u in usable}, {u["week"] for u in usable}
    gw1 = bool(len(usable) >= W1_MIN_MOVES and len(subj1) >= W1_MIN_SUBJECTS and len(wk1) >= W1_MIN_WEEKS)
    units = pk["units"]
    subj2, wk2 = {u["subject"] for u in units}, {u["week"] for u in units}
    lab = pk["labels"]
    eligible = sum(v for k, v in lab.items() if k not in ("no market", "outside calendar"))
    reach = 1.0 - lab.get("uncovered", 0) / eligible if eligible else 0.0
    gw2 = bool(len(units) >= W2_MIN_UNITS and len(subj2) >= W2_MIN_SUBJECTS and len(wk2) >= W2_MIN_WEEKS and reach >= W2_REACH_MIN)
    g_min = min(len(subj1), len(wk1))
    m1 = mde_w1(g_min)
    gwp1 = bool(gw1 and m1 <= GWP_W1_MAX_MDE)
    gwp2 = bool(gw2 and proxy.get("mde") is not None and proxy["mde"] <= GWP_W2_MAX_MDE_C)
    return {"GW_W1": {"pass": gw1, "usable_moves": len(usable), "moves_before_placebo_filter": len(moves), "subjects": len(subj1), "weeks": len(wk1), "need": [W1_MIN_MOVES, W1_MIN_SUBJECTS, W1_MIN_WEEKS]},
            "GW_W2": {"pass": gw2, "units": len(units), "subjects": len(subj2), "weeks": len(wk2), "reach_coverage": reach, "need": [W2_MIN_UNITS, W2_MIN_SUBJECTS, W2_MIN_WEEKS, W2_REACH_MIN]},
            "GWP_W1": {"pass": gwp1, "g_min": g_min, "mde": m1, "max_mde": GWP_W1_MAX_MDE}, "GWP_W2": {"pass": gwp2, **proxy, "max_mde": GWP_W2_MAX_MDE_C}}


def burst_state_bands(D: dict) -> dict:
    """Bursts by the state band of the subject's nearest-end listed market (a price feature of the burst time; no lead, entry or exit)."""
    edges = [(0.0, 0.05, "<5c"), (0.05, 0.20, "5-20c"), (0.20, 0.40, "20-40c"), (0.40, 0.60, "40-60c"), (0.60, 1.01, ">60c")]
    out: Counter = Counter()
    for sid, bl in D["bursts"].items():
        ms = sorted(D["by_subject"].get(sid, []), key=lambda m: (m["end_epoch"], m["market_id"]))
        for b in bl:
            st = None
            for m in ms:
                tx = D["txs"].get(m["market_id"])
                if tx is not None and m["created_epoch"] <= b and m["end_epoch"] >= b:
                    st = tx.state(b)
                    break
            out["no state" if st is None else next(lbl for lo, hi, lbl in edges if lo <= st < hi)] += 1
    return dict(out)


def print_reach_report(D: dict) -> dict:
    """The share of each market's observed life (listing to scheduled end or ``T14_W_END``) that its newest-first prints cover."""
    shares = []
    for mid, m in D["markets"].items():
        tx = D["txs"].get(mid)
        if tx is None:
            continue
        end = min(m["end_epoch"], w_end()) if math.isfinite(m["end_epoch"]) else w_end()
        life = end - m["created_epoch"]
        if life <= 0:
            continue
        shares.append(1.0 if not tx.truncated else float(min(1.0, max(0.0, (end - tx.oldest_ts) / life))) if math.isfinite(tx.oldest_ts) else 0.0)
    return {"markets": len(shares), "mean_share": mean_or_nan(shares) if shares else None, "median_share": float(np.median(shares)) if shares else None,
            "fully_covered": int(sum(1 for s in shares if s >= 1.0))}


def no_resolved_audit(rdir: Path, moves: list[dict]) -> dict:
    """Audit count (reported): decisive moves on markets whose guarded outcome says NO. The census is the only job that opens ``outcomes_guarded.csv.gz`` and only for this count."""
    p = Path(rdir) / "outcomes_guarded.csv.gz"
    if not p.is_file():
        return {"available": False}
    rows = c14.open_guarded(p, "census", ("census",))
    no_ids = set()
    for r in rows:
        try:
            prices = json.loads(r["outcome_prices"])
            yi = int(r["yes_index"])
            if len(prices) == 2 and float(prices[yi]) == 0.0:
                no_ids.add(r["market_id"])
        except (ValueError, KeyError, IndexError, TypeError):
            continue
    return {"available": True, "moves_on_markets_resolved_no": sum(1 for u in moves if u["market_id"] in no_ids), "n_moves": len(moves)}


def census_w(rdir: Path, *, audit: dict | None, attn_path: Path | None = None, keys_report: dict | None = None, hist_root: Path | None = None) -> dict:
    """q0308, counts only. No lead, placebo share, entry-exit net, precision or burst-to-move relation is computed or returned."""
    late = late_overlap(hist_root, keys_report, read_rows(Path(rdir) / "frame.csv.gz")) if hist_root is not None else {"drop_markets": set(), "by_set": {}, "absent_at_q0302": []}
    D = load_data(rdir, audit=audit, attn_path=attn_path, drop_markets=late["drop_markets"])
    fr = D["frame_rows"]
    moves, minfo = w1_units(D)
    pk = w2_units(D)
    proxy = proxy_se(proxy_units(D))
    gates = gates_w(D, moves, pk, proxy)
    grids = {}
    for name, g in BURST_GRIDS.items():
        b = load_bursts(rdir, D["subjects"], g)[0]
        grids[name] = {"bursts": sum(len(x) for x in b.values()), "subjects_with_burst": sum(1 for x in b.values() if x)}
    yrs = Counter(datetime.fromtimestamp(f(r["created_epoch"]), tz=UTC).year for r in fr if math.isfinite(f(r["created_epoch"])))
    n_country = sum(1 for s in D["subjects"].values() if not s["country"].startswith("single:"))
    return {"label": LABEL_W, "counts_only": True,
            "frame": {"rows": len(fr), "by_term": dict(Counter(r["term"] for r in fr)), "by_class": dict(Counter(r["cls"] for r in fr)), "by_listing_year": {str(k): v for k, v in sorted(yrs.items())},
                      "by_fetched_as": dict(Counter(r["fetched_as"] for r in fr)), "by_status": dict(Counter(r["status"] for r in fr)),
                      "key_drops_by_source": dict(Counter(r["key_source"] for r in fr if r["status"] == "dropped:key")), "full_series_counterfactual_drops": sum(int(r["series_cf"]) for r in fr),
                      "deaths_stratum": sum(1 for r in fr if r["status"] == "stratum:death")},
            "exclusion_report": keys_report or {}, "late_overlap": {"dropped_markets": len(late["drop_markets"]), "by_set": late["by_set"], "absent_at_q0302": late["absent_at_q0302"]},
            "subjects": {"mapped": len(D["subjects"]), "markets": len(D["markets"]), "events": len({m["event_id"] for m in D["markets"].values()}), "cb11a_entity_overlap": sum(1 for s in D["subjects"].values() if s["attn"]),
                         "country_mapped_share": (n_country / len(D["subjects"])) if D["subjects"] else None, "heads": sum(1 for s in D["subjects"].values() if s["head"])},
            "audit": {k: (audit or {}).get(k) for k in ("n", "n_match", "precision", "pass", "rule_revision")},
            "revisions": {**{k: v for k, v in D["burst_info"].items()}, "pages": len(D["pages"]), "article_too_new_pages_for_baseline": D["burst_info"].get("no_baseline", 0)},
            "bursts": {"total": sum(len(x) for x in D["bursts"].values()), "subjects_with_burst": sum(1 for x in D["bursts"].values() if x), "by_state_band": burst_state_bands(D), "grid": grids},
            "print_reach": print_reach_report(D),
            "w2_units_by_label": pk["labels"],
            "decisive_moves": {"n": len(moves), "subjects": len({u["subject"] for u in moves}), "weeks": len({u["week"] for u in moves}), "by_class": dict(Counter(u["cls"] for u in moves)), "unit_info": minfo,
                               "no_placebo": sum(1 for u in moves if len(placebo_anchors(u["D0"], D["txs"][u["market_id"]], u["created"])) < PLACEBO_MIN_ANCHORS),
                               "no_resolved_audit": no_resolved_audit(rdir, moves)},
            "gates": gates, "frame_completeness": read_json(Path(rdir) / "completeness.json")}


def read_json(p: Path) -> dict:
    return json.loads(Path(p).read_text()) if Path(p).is_file() else {}


def screen_w(rdir: Path, census: dict, *, audit: dict | None, attn_path: Path | None = None, n_draws: int = c14.PLACEBO_DRAWS, hist_root: Path | None = None, keys_report: dict | None = None) -> dict:
    """q0309: W1 and W2 on the historical W calendar. A test behind a failed gate is 'not testable (population)' / 'not run (power)', p = 1, still counted."""
    g = census.get("gates") or {}
    comp = census.get("frame_completeness") or {}
    res: dict = {"label": LABEL_W}
    pop = (not audit or not audit.get("pass")) or comp.get("share", 0.0) < COMPLETENESS_MIN
    if pop:
        why = "not testable (map or frame completeness)"
        res["W1"], res["W2"] = not_run(why), not_run(why)
        res["gates"] = g
        return res
    late = late_overlap(hist_root, keys_report, read_rows(Path(rdir) / "frame.csv.gz")) if hist_root is not None else {"drop_markets": set()}
    D = load_data(rdir, audit=audit, attn_path=attn_path, drop_markets=late["drop_markets"])
    if not (g.get("GW_W1") or {}).get("pass"):
        res["W1"] = not_run("not testable (population)")
    elif not (g.get("GWP_W1") or {}).get("pass"):
        res["W1"] = not_run("not run (power)")
    else:
        res["W1"] = finish(w1_test(D, n_draws=n_draws), W1_FLOOR, placebo_key="placebo_ok")
    if not (g.get("GW_W2") or {}).get("pass"):
        res["W2"] = not_run("not testable (population)")
    elif not (g.get("GWP_W2") or {}).get("pass"):
        res["W2"] = not_run("not run (power)")
    else:
        res["W2"] = finish(w2_test(D), W2_FLOOR)
    res["gates"] = g
    return res


def finish(r: dict, floor: float, *, placebo_key: str | None = None) -> dict:
    """Attach the verdict: advance iff p < 0.01 (``p_ok``) AND ``checks_ok`` = the floor on the point estimate, every small-G leave-one-cluster-out sign rule, every binding check and
    (W1) the calibration placebo. ``checks_ok`` is every binding condition except the primary p gate (Stage 2 decides p by alpha / 4 early or the final Holm)."""
    floor_ok = r.get("effect") is not None and r["effect"] >= floor
    placebo_ok = True if placebo_key is None else bool(r.get(placebo_key))
    r["checks_ok"] = bool(r.get("testable") and floor_ok and r.get("small_g_rules_hold", False) and r.get("checks_met") and placebo_ok)
    r["p_ok"] = bool(r.get("testable") and c14.adv_label(r.get("p"), True))
    adv = bool(r["p_ok"] and r["checks_ok"])
    r["advance"] = adv
    r["floor"] = floor
    r["verdict"] = "advance to Stage 2" if adv else ("not detected" if r.get("testable") else r.get("verdict", "not testable"))
    if "placebo" in r:
        r["placebo"] = {k: r["placebo"].get(k) for k in ("note", "advance_rate", "n_draws")}
    return r


# =====================================================================================================================================================
# q0303: the frame (search by the frozen query list, status, entity rule, summaries, completeness walk)
# =====================================================================================================================================================


def frame_done(rdir: Path) -> dict | None:
    return c14.manifest_complete(Path(rdir), (FRAME_STATUS,))


def _jsonl_append(path: Path, rec: dict) -> None:
    with Path(path).open("a") as fh:
        fh.write(json.dumps(rec, default=float, sort_keys=True) + "\n")


def _jsonl_iter(path: Path):
    p = Path(path)
    if not p.is_file():
        return
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _repair_tail(path: Path) -> None:
    """A crash mid-line must not glue the next record onto the broken one."""
    p = Path(path)
    if p.is_file() and p.stat().st_size:
        with p.open("rb+") as fh:
            fh.seek(-1, 2)
            if fh.read(1) != b"\n":
                fh.write(b"\n")


def _transient(fr, why: str) -> dict:
    mm = fr.manifest(why[:200], {"transient": True})
    mm["status"] = "in_progress"
    return mm


def walk_day_windows(month: str) -> list[tuple[float, float]]:
    y, m = (int(x) for x in month.split("-"))
    start = datetime(y, m, 1, tzinfo=UTC)
    end = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1, tzinfo=UTC)
    days = int((end - start).total_seconds() // DAY)
    return [(start.timestamp() + i * DAY, start.timestamp() + (i + 1) * DAY) for i in range(days)]


def walk_politics_day(lim, a: float, b: float, *, page: int = c14.GAMMA_PAGE, offset_cap: int = c14.GAMMA_OFFSET_CAP) -> list[dict]:
    """Closed Gamma events of the politics tag ending in ``[a, b)`` (a one-day window), paged to the offset cap; a day that is still capped is a refusal (not silently truncated)."""
    out: list[dict] = []
    for off in range(0, offset_cap + page, page):
        st, data = lim.get(c14.GAMMA_EVENTS, {"closed": "true", "tag_id": COMPLETENESS_TAG_ID, "end_date_min": cm.iso(a), "end_date_max": cm.iso(b), "order": "id", "ascending": "true",
                                              "limit": page, "offset": off})
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"gamma events status {st}")
        out.extend(x for x in data if isinstance(x, dict))
        if len(data) < page:
            return out
    raise Refused(f"politics one-day walk {cm.iso(a)} is capped at the offset limit")


def walk_matches(events: list[dict], sports_ids: set[str]) -> set[str]:
    """Market ids of binary markets in ``events`` that match the W title regex under the same exclusions as the frame (sports, mention, entertainment, death, listing window)."""
    out = set()
    for ev in events:
        for m in ev.get("markets") or []:
            if not isinstance(m, dict):
                continue
            row = parse_market(m, ev, fetched_as="walk", term="walk", sports_ids=sports_ids)
            if row is None or row["death"] or not TITLE_RE.search(row["question"]) or not listing_ok(row["created_epoch"]):
                continue
            if row["sports_tag"] or row["sports_re"] or row["mention"] or row["entertainment"]:
                continue
            out.add(row["market_id"])
    return out


def build_subjects(rows: list[dict], summaries: dict[str, dict]) -> list[dict]:
    """Subject rows by entity (summary type, page id, canonical title, description, frozen country and head flags); ``mapped`` iff the summary is a standard article."""
    counts = Counter(r["entity"] for r in rows if r["status"] == "kept" and r["entity"])
    out = []
    for e in sorted(counts):
        s = summaries.get(e) or {"status": 0, "type": "", "page_id": "", "canonical": "", "description": ""}
        ok = subject_ok(s)
        out.append({"entity": e, "page_id": s.get("page_id", ""), "canonical_title": s.get("canonical", ""), "description": s.get("description", ""), "type": s.get("type", ""),
                    "status": "mapped" if ok else "dropped:summary", "country": country_of(s.get("description", ""), e) if ok else "", "head": int(is_head(s.get("description", ""))) if ok else 0,
                    "n_markets": counts[e]})
    return out


def w_frame(hist_root: Path, transport, *, rules_sha: str, keys_path: Path, smoke_path: Path | None = None, out_root: Path | None = None, repo_root: Path | None = None, now: float,
            rps: float = 2.0, wiki_rps: float = 1.0, disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None,
            should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
            data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None, queries: tuple[str, ...] = QUERIES, months: tuple[str, ...] = COMPLETENESS_MONTHS) -> dict:
    """q0303, resumable. Frozen query list on Gamma ``public-search`` (closed and active, paged to ``hasMore`` = false); W title regex and exclusions; listing-date rule; full key
    drops; entity rule + Wikipedia summary; politics one-day completeness walk; the GW0 audit sample. No revision or print is read; outcomes go only to ``outcomes_guarded.csv.gz``."""
    from . import cb14_smoke as sm  # noqa: PLC0415

    rdir = c14.require_output_root(Path(hist_root) / RUN)
    out_root = c14.require_output_root(Path(out_root) if out_root is not None else c14.CB14_DIR)
    st = c14.stall_of(rdir)
    if st:
        return st
    if frame_done(rdir):
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": frame_done(rdir).get("counts")}
    if smoke_path is not None:
        bad = sm.smoke_failures(smoke_path, SMOKE_NEEDS, "W")
        if bad:
            return c14.write_stall(rdir, "not_run_source", f"smoke criteria not met: {bad}")
    check_entity_source()
    sports = sports_registry_ids(repo_root)
    ids, keys, krep, ksha = c14.load_keys(Path(keys_path))
    if krep.get("disjointness") == c14.UNVERIFIED:
        return c14.write_stall(rdir, "not_testable_disjointness", "exclusion keys: more than 2% of ids without metadata")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c14.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    rdir.mkdir(parents=True, exist_ok=True)
    fr = cm.open_run(Path(hist_root), RUN, transport, allowed_run_id=RUN, kind="cb14_w_frame", label="CB14-W frame",
                     params={"evidence_role": c14.EVIDENCE_ROLE_HIST, "queries": list(queries), "listed": list(W_LISTED), "exclusion_keys_sha256": ksha}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    limw = hb.Limiter(fr.lim.transport, rps=min(wiki_rps, 1.0), sleep=sleep, live_check=live_check)
    part, opart, spart, wpart = rdir / "frame_partial.jsonl", rdir / "outcomes_guarded_partial.jsonl", rdir / "summaries_partial.jsonl", rdir / "walk_partial.jsonl"
    for p_ in (part, opart, spart, wpart):
        _repair_tail(p_)
    done_q = set(fr.extra_state.get("search_done") or [])
    pending: dict[str, list[str]] = dict(fr.extra_state.get("lookup_pending") or {})

    def _take(ev: dict, q: str, status: str, seen_before: set[str]) -> None:
        for m in ev.get("markets") or []:
            if not isinstance(m, dict):
                continue
            row = parse_market(m, ev, fetched_as=status, term=q, sports_ids=sports)
            if row is None or row["market_id"] in seen_before:
                continue
            seen_before.add(row["market_id"])
            _jsonl_append(part, row)
            _jsonl_append(opart, parse_outcome(m, ev, row["yes_index"]))

    try:
        for q in queries:
            for status in SEARCH_STATUSES:
                key = f"{q}|{status}"
                if key in done_q:
                    continue
                why = fr.stop_reason(should_stop)
                if why:
                    return _transient(fr, why)
                evs, info = search_all(fr.lim, q, status)
                seen_before = {r["market_id"] for r in _jsonl_iter(part)}
                for ev in evs:
                    if event_needs_lookup(ev, sports):  # a field the frame rules read is missing in the search payload: parse the full event after the lookup below
                        pending.setdefault(str(ev.get("id")), [q, status])
                        continue
                    _take(ev, q, status, seen_before)
                done_q.add(key)
                fr.extra_state["search_done"] = sorted(done_q)
                fr.extra_state["lookup_pending"] = pending
                fr.extra_state.setdefault("search_info", {})[key] = info
        done_l = set(fr.extra_state.get("lookup_done") or [])
        n_req = int(fr.extra_state.get("lookup_requests", 0))
        todo = sorted(e for e in pending if e not in done_l)
        seen_before = {r["market_id"] for r in _jsonl_iter(part)}
        for i in range(0, len(todo), EVENT_LOOKUP_PER_REQUEST):
            batch = todo[i:i + EVENT_LOOKUP_PER_REQUEST]
            if n_req + 2 > EVENT_LOOKUP_MAX_REQ:
                return c14.write_stall(rdir, "not_run_source", f"Gamma event lookups for search events with missing fields exceed the {EVENT_LOOKUP_MAX_REQ}-request budget ({len(pending)} events)")
            why = fr.stop_reason(should_stop)
            if why:
                return _transient(fr, why)
            got, used = lookup_events(fr.lim, batch)
            n_req += used
            for eid in batch:
                if eid in got:
                    _take(got[eid], pending[eid][0], pending[eid][1], seen_before)
            done_l.update(batch)
            fr.extra_state["lookup_done"] = sorted(done_l)
            fr.extra_state["lookup_requests"] = n_req
            fr.extra_state["lookup_not_found"] = int(fr.extra_state.get("lookup_not_found", 0)) + sum(1 for e in batch if e not in got)
    except (ApiError, RuntimeError) as exc:
        return _transient(fr, f"gamma_failed: {exc}")
    rows = list(_jsonl_iter(part))
    seen_ids: set[str] = set()
    rows = [r for r in rows if not (r["market_id"] in seen_ids or seen_ids.add(r["market_id"]))]
    rows.sort(key=lambda r: r["market_id"])
    for r in rows:
        r["status"], r["key_source"] = frame_status(r, ids, keys)
        r["series_cf"] = int(full_series_counterfactual(r, keys))
        if r["status"] == "kept":
            r["entity"] = entity_candidate(r["question"], r["event_title"])
            if not r["entity"]:
                r["status"] = "dropped:entity"
    entities = sorted({r["entity"] for r in rows if r["status"] == "kept"})
    summaries = {s["entity"]: s for s in _jsonl_iter(spart)}
    try:
        for e in entities:
            if e in summaries:
                continue
            if len(summaries) >= WIKI_MAX_REQ:
                return c14.write_stall(rdir, "not_run_source", f"Wikipedia request budget ({WIKI_MAX_REQ}) used up: {len(summaries)} summaries cached")
            why = fr.stop_reason(should_stop)
            if why:
                return _transient(fr, why)
            s = wiki_summary(limw, e)
            summaries[e] = s
            _jsonl_append(spart, s)
    except (ApiError, RuntimeError) as exc:
        return _transient(fr, f"wikipedia_failed: {exc}")
    walk_done = set(fr.extra_state.get("walk_done") or [])
    walk_ids = {r["market_id"] for r in _jsonl_iter(wpart)}
    try:
        for month in months:
            for a, b in walk_day_windows(month):
                key = cm.iso(a)
                if key in walk_done:
                    continue
                why = fr.stop_reason(should_stop)
                if why:
                    return _transient(fr, why)
                for mid in sorted(walk_matches(walk_politics_day(fr.lim, a, b), sports)):
                    if mid not in walk_ids:
                        walk_ids.add(mid)
                        _jsonl_append(wpart, {"market_id": mid})
                walk_done.add(key)
                fr.extra_state["walk_done"] = sorted(walk_done)
    except (ApiError, RuntimeError) as exc:
        return _transient(fr, f"gamma_walk_failed: {exc}")
    try:
        subs = build_subjects(rows, summaries)
        mapped = {s["entity"] for s in subs if s["status"] == "mapped"}
        for r in rows:
            if r["status"] == "kept" and r["entity"] not in mapped:
                r["status"] = "dropped:summary"
        by_status = Counter(r["status"] for r in rows)
        frame_ids_all = {r["market_id"] for r in rows}
        found = len(walk_ids & frame_ids_all)
        comp = {"months": list(months), "walk_markets": len(walk_ids), "found_in_frame": found, "share": (found / len(walk_ids)) if walk_ids else 1.0, "min": COMPLETENESS_MIN,
                "pass": bool((found / len(walk_ids) if walk_ids else 1.0) >= COMPLETENESS_MIN), "search_info": fr.extra_state.get("search_info", {}),
                "event_lookups": {"events": len(pending), "requests": int(fr.extra_state.get("lookup_requests", 0)), "not_found": int(fr.extra_state.get("lookup_not_found", 0))}}
        fr.budget.write_gz_csv(rdir / "frame.csv.gz", FRAME_COLUMNS, ([r[c] for c in FRAME_COLUMNS] for r in rows))
        fr.record_file(rdir / "frame.csv.gz")
        fr.budget.write_gz_csv(rdir / "subjects.csv.gz", SUBJECT_COLUMNS, ([s[c] for c in SUBJECT_COLUMNS] for s in subs))
        fr.record_file(rdir / "subjects.csv.gz")
        keep_out = [json.loads(json.dumps(o)) for o in _jsonl_iter(opart) if o["market_id"] in frame_ids_all]
        c14.assert_clean_columns(OUTCOME_COLUMNS, guarded=True)
        fr.budget.write_gz_csv(rdir / "outcomes_guarded.csv.gz", OUTCOME_COLUMNS, ([o[c] for c in OUTCOME_COLUMNS] for o in sorted(keep_out, key=lambda x: x["market_id"])))
        fr.record_file(rdir / "outcomes_guarded.csv.gz")
        (rdir / "completeness.json").write_text(json.dumps(comp, indent=1, sort_keys=True))
        fr.record_file(rdir / "completeness.json")
        out_root.mkdir(parents=True, exist_ok=True)
        sample = audit_sample_rows([{**s, "status": s["status"]} for s in subs], [r for r in rows if r["status"] == "kept"])
        with (out_root / AUDIT_SAMPLE_FILE).open("w", newline="", encoding="utf-8") as fh:
            w_ = csv.writer(fh)
            w_.writerow(AUDIT_SAMPLE_COLUMNS)
            w_.writerows(sample)
        for p_ in (part, opart, spart, wpart):
            p_.unlink(missing_ok=True)
        fr.counts.update(rows=len(rows), kept=by_status["kept"], subjects_mapped=len(mapped), walk_markets=len(walk_ids), **{f"status_{k}": v for k, v in by_status.items()})
        fr.extra_state["frame_complete"] = True
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m["status"] = FRAME_STATUS
    return m


# =====================================================================================================================================================
# q0305: pre-fetch gate GWC (counts only, no network)
# =====================================================================================================================================================


def audit_coverage(subs: list[dict], audit: dict) -> dict:
    """The audit must label every mapped entity of the frame (a blind labelling of every pair)."""
    mapped = {s["entity"] for s in subs if s["status"] == "mapped"}
    missing = sorted(mapped - set(audit["labels"]))
    return {"mapped_entities": len(mapped), "labelled": len(mapped) - len(missing), "missing": missing[:20], "n_missing": len(missing)}


def pregate_w(rdir: Path, audit: dict) -> dict:
    """GWC: >= 150 mapped markets in >= 60 events and >= 40 subjects after key drops and the GW0 drops, GW0 PASS (precision >= 90%, every pair labelled) and frame completeness
    >= 95%. Counts only. A failure means W1 and W2 are 'not testable (population)', counted, and q0306/q0307 are never committed."""
    subs = read_rows(Path(rdir) / "subjects.csv.gz")
    cov = audit_coverage(subs, audit)
    fr = load_frame(rdir, audit)
    comp = read_json(Path(rdir) / "completeness.json")
    n_markets, n_events, n_subjects = len(fr["markets"]), len({m["event_id"] for m in fr["markets"].values()}), len(fr["subjects"])
    checks = {"markets": n_markets >= MIN_MARKETS_GWC, "events": n_events >= MIN_EVENTS_GWC, "subjects": n_subjects >= MIN_SUBJECTS_GWC, "audit_pass": bool(audit["pass"]),
              "audit_complete": cov["n_missing"] == 0, "completeness": bool(comp.get("share", 0.0) >= COMPLETENESS_MIN)}
    return {"gate": "GWC", "pass": all(checks.values()), "checks": checks, "markets": n_markets, "events": n_events, "subjects": n_subjects, "need": [MIN_MARKETS_GWC, MIN_EVENTS_GWC, MIN_SUBJECTS_GWC],
            "audit": {k: audit.get(k) for k in ("n", "n_match", "precision", "rule_revision")}, "audit_coverage": cov, "completeness": {k: comp.get(k) for k in ("walk_markets", "found_in_frame", "share")},
            "counts_only": True}


# =====================================================================================================================================================
# q0306: revisions (MediaWiki), resumable per page
# =====================================================================================================================================================


def wiki_get(limw, params: dict) -> dict:
    """One MediaWiki action-API call (JSON). A ``maxlag`` / error payload is a transient ``ApiError`` (the caller backs off); the response is never parsed for ``mw-reverted``."""
    st, data = limw.get(WIKI_API, params)
    if st != 200 or not isinstance(data, dict):
        raise ApiError(f"mediawiki status {st}")
    if data.get("error"):
        raise ApiError(f"mediawiki error {str((data['error'] or {}).get('code'))[:40]}")
    return data


def fetch_bot_list(limw, *, max_batches: int = 20) -> set[str]:
    """The bot-group accounts (``list=allusers&augroup=bot``), as pseudonymised keys (``bot_key``); one page of up to 500 normally."""
    keys: set[str] = set()
    cont: dict = {}
    for _ in range(max_batches):
        data = wiki_get(limw, {"action": "query", "format": "json", "formatversion": 2, "list": "allusers", "augroup": "bot", "aulimit": "max", "maxlag": MW_MAXLAG, **cont})
        for u in (data.get("query") or {}).get("allusers") or []:
            if isinstance(u, dict) and u.get("name"):
                keys.add(bot_key(str(u["name"])))
        if not data.get("continue"):
            return keys
        cont = {k: v for k, v in data["continue"].items()}
    raise Refused("bot list still continues after the batch cap")


def fetch_first_revision(limw, title: str) -> float:
    data = wiki_get(limw, {"action": "query", "format": "json", "formatversion": 2, "prop": "revisions", "titles": title, "rvprop": "timestamp", "rvlimit": 1, "rvdir": "newer", "maxlag": MW_MAXLAG})
    pages = (data.get("query") or {}).get("pages") or []
    revs = (pages[0].get("revisions") if pages else None) or []
    return parse_ts(revs[0].get("timestamp")) if revs else math.nan


def fetch_page_revisions(limw, title: str, start: float, end: float, bot_keys: set[str], *, rv_limit: int = RV_LIMIT, max_batches: int = 400, historical: bool = True) -> tuple[list[dict], dict]:
    """Chronological revision rows of one page over ``[start, end]`` (``rvdir=newer`` with ``rvcontinue``). Historical (Stage 1, q0306): ``end`` is clamped below ``T14_W_END`` and rows at
    or after it are dropped. Live (``historical=False``, the Stage-2 baseline bootstrap after 2026-10-26): no clamp, the requested live window is kept."""
    if historical:
        end = min(end, w_end() - 1)
    params = {"action": "query", "format": "json", "formatversion": 2, "prop": "revisions", "titles": title, "rvprop": "ids|timestamp|user|userid|size|comment|tags|flags",
              "rvlimit": rv_limit, "rvdir": "newer", "rvstart": cm.iso(start), "rvend": cm.iso(end), "maxlag": MW_MAXLAG}
    rows: list[dict] = []
    users: dict = {}
    prev: float | None = None
    page_id = ""
    batches = 0
    cont: dict = {}
    while True:
        data = wiki_get(limw, {**params, **cont})
        batches += 1
        pages = (data.get("query") or {}).get("pages") or []
        pg = pages[0] if pages else {}
        if pg.get("missing"):
            return [], {"status": "missing", "batches": batches, "page_id": ""}
        page_id = str(pg.get("pageid") or page_id)
        got, prev = parse_revision_batch([r for r in (pg.get("revisions") or []) if isinstance(r, dict)], page_id, users, bot_keys, prev)
        rows.extend(got)
        if not data.get("continue"):
            break
        if batches >= max_batches:
            raise Refused(f"revisions of {title!r} still continue after {max_batches} batches")
        cont = {k: v for k, v in data["continue"].items()}
    if historical:
        rows = keep_before_w_end(rows)
    return rows, {"status": "ok", "batches": batches, "page_id": page_id, "n_users": len(users)}


def revisions_done(rdir: Path) -> dict | None:
    return c14.manifest_complete(Path(rdir), (REVISIONS_STATUS,))


def w_revisions(hist_root: Path, transport, *, rules_sha: str, audit: dict, now: float, rps: float = 2.0, wiki_rps: float = 1.0, disk_cap: int = int(REVISIONS_OUTPUT_CAP_GB * 1024**3),
                budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None,
                data_dumps: Path | None = None, data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0306, resumable per page. Bot-group list (as pseudonymised keys), the first-revision date of each mapped page, and the revision metadata from ``max(createdAt, 2024-01-01)
    - 30 d`` to ``T14_W_END``. User names are read in memory only (bot flag; per-page distinct-user index); ``mw-reverted`` is never parsed. Refuses unless q0305 passed (the caller
    checks the gate); it only reads the frame, subjects and the audit."""
    rdir = c14.require_output_root(Path(hist_root) / RUN)
    st = c14.stall_of(rdir)
    if st:
        return st
    if revisions_done(rdir):
        return {"stopped": None, "status": REVISIONS_STATUS, "complete": True, "counts": revisions_done(rdir).get("counts")}
    if not frame_done(rdir):
        raise NotNow("q0306 waits for q0303 (w_frame) to finish")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c14.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(Path(hist_root), RUN, transport, allowed_run_id=RUN, kind="cb14_w_revisions", label="CB14-W revisions",
                     params={"evidence_role": c14.EVIDENCE_ROLE_HIST, "rvlimit": RV_LIMIT, "maxlag": MW_MAXLAG}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(wiki_rps, 1.0),
                     budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    limw = fr.lim
    data = load_frame(rdir, audit)
    titles = {sid: s["canonical"] for sid, s in data["subjects"].items()}
    first_created = {sid: min(m["created_epoch"] for m in ms) for sid, ms in data["by_subject"].items() if ms}
    part, bpart = rdir / "revisions_partial.jsonl", rdir / "bots_partial.json"
    _repair_tail(part)
    try:
        if bpart.is_file():
            bots = set(json.loads(bpart.read_text()))
        else:
            why = fr.stop_reason(should_stop)
            if why:
                return _transient(fr, why)
            bots = fetch_bot_list(limw)
            bpart.write_text(json.dumps(sorted(bots)))
        have = {r["page_id_key"] for r in _jsonl_iter(part)}
        for sid in sorted(titles):
            if sid in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return _transient(fr, why)
            fstart = max(first_created.get(sid, ep(W_CALENDAR_START)), ep(W_CALENDAR_START)) - REVISION_LEAD_D * DAY
            try:
                first_rev = fetch_first_revision(limw, titles[sid])
                rows, info = fetch_page_revisions(limw, titles[sid], fstart, w_end() - 1, bots)
            except (ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[sid] = fails.get(sid, 0) + 1
                if fails[sid] < cm.MAX_ITEM_ATTEMPTS:
                    return _transient(fr, f"mediawiki_failed {sid}: {exc}")
                _jsonl_append(part, {"page_id_key": sid, "page_id": sid, "title": titles[sid], "fetch_start": fstart, "first_rev_ts": None, "status": "unavailable (network)", "rows": []})
                have.add(sid)
                continue
            _jsonl_append(part, {"page_id_key": sid, "page_id": info.get("page_id") or sid, "title": titles[sid], "fetch_start": fstart, "first_rev_ts": None if not math.isfinite(first_rev) else first_rev,
                                 "status": info["status"], "rows": [clean_revision_row({**r, "page_id": sid}) for r in rows]})
            have.add(sid)
    except (ApiError, RuntimeError) as exc:
        return _transient(fr, f"mediawiki_failed: {exc}")
    try:
        def _recs():
            yield from _jsonl_iter(part)

        fr.budget.write_gz_csv(rdir / "pages.csv.gz", PAGE_COLUMNS, ([r["page_id_key"], r["title"], r["fetch_start"], "" if r["first_rev_ts"] is None else r["first_rev_ts"], len(r["rows"]), r["status"]] for r in _recs()))
        fr.record_file(rdir / "pages.csv.gz")
        fr.budget.write_gz_csv(rdir / "revisions.csv.gz", REV_COLUMNS, ([row[c] for c in REV_COLUMNS] for r in _recs() for row in r["rows"]))
        fr.record_file(rdir / "revisions.csv.gz")
        fr.budget.write_gz_csv(rdir / "bots.csv.gz", BOT_COLUMNS, ([k] for k in sorted(bots)))
        fr.record_file(rdir / "bots.csv.gz")
        n_rev = sum(len(r["rows"]) for r in _recs())
        stat = Counter(r["status"] for r in _recs())
        part.unlink(missing_ok=True)
        bpart.unlink(missing_ok=True)
        fr.counts.update(pages=len(have), revisions=n_rev, bots=len(bots), **{f"pages_{k}": v for k, v in stat.items()})
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": REVISIONS_STATUS})
    m["status"] = REVISIONS_STATUS
    return m


# =====================================================================================================================================================
# q0307: Data API prints (newest first, <= 2 pages), aggregated to transactions
# =====================================================================================================================================================


def prints_done(rdir: Path) -> dict | None:
    return c14.manifest_complete(Path(rdir), (PRINTS_STATUS,))


def tx_rows_of(prints: list[dict], yes_index: int) -> list[dict]:
    """Transactions before ``T14_W_END`` only (later ones are dropped at the source and never stored)."""
    return keep_before_w_end(build_transactions(prints, yes_index))


def w_prints(hist_root: Path, transport, *, rules_sha: str, audit: dict, now: float, rps: float = 2.0, disk_cap: int = int(PRINTS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
             sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
             data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None, page_limit: int = c14.DATA_PAGE_LIMIT, pages: int = c14.DATA_PAGES) -> dict:
    """q0307, resumable per market. Newest-first prints (<= 2 pages of 10,000) for every kept market of a mapped subject, aggregated to transactions (time, YES-terms VWAP, min and max
    YES-terms price, size; the hash is discarded; no side, wallet or name is read into a row). ``reach.csv.gz`` records the newest-first reach per market."""
    rdir = c14.require_output_root(Path(hist_root) / RUN)
    st = c14.stall_of(rdir)
    if st:
        return st
    if prints_done(rdir):
        return {"stopped": None, "status": PRINTS_STATUS, "complete": True, "counts": prints_done(rdir).get("counts")}
    if not c14.manifest_complete(rdir, (REVISIONS_STATUS,)) and not (c14.manifest_complete(rdir, (FRAME_STATUS,)) and (rdir / "revisions.csv.gz").is_file()):
        raise NotNow("q0307 waits for q0306 (w_revisions) to finish")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c14.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(Path(hist_root), RUN, transport, allowed_run_id=RUN, kind="cb14_w_prints", label="CB14-W prints",
                     params={"evidence_role": c14.EVIDENCE_ROLE_HIST, "pages": pages, "limit": page_limit}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0),
                     budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    data = load_frame(rdir, audit)
    mlist = sorted(data["markets"].values(), key=lambda m: m["market_id"])
    part = rdir / "prints_partial.jsonl"
    _repair_tail(part)
    have = {r["market_id"] for r in _jsonl_iter(part)}
    try:
        for m in mlist:
            mid = m["market_id"]
            if mid in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return _transient(fr, why)
            try:
                prints, info = c14.c12.fetch_prints_paged(fr.lim, m["condition_id"], m["created_epoch"], limit=page_limit, pages=pages)
            except (ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[mid] = fails.get(mid, 0) + 1
                if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                    return _transient(fr, f"fetch_failed {mid}: {exc}")
                rec = {"market_id": mid, "oldest_ts": None, "truncated": 1, "n_prints": 0, "n_tx": 0, "pages": 0, "tx": [], "status": "unavailable (network)"}
            else:
                tx = tx_rows_of(prints, int(m["yes_index"]))
                del prints
                rec = {"market_id": mid, "oldest_ts": None if not math.isfinite(info["oldest_ts"]) else info["oldest_ts"], "truncated": int(bool(info["truncated"])), "n_prints": info["n_prints"],
                       "n_tx": len(tx), "pages": info["pages"], "tx": [[r["ts"], r["price"], r["pmin"], r["pmax"], r["size"]] for r in tx], "status": "ok"}
            _jsonl_append(part, rec)
            have.add(mid)
            del rec
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    try:
        fr.budget.write_gz_csv(rdir / "tx.csv.gz", TX_COLUMNS, ([r["market_id"], *row] for r in _jsonl_iter(part) for row in r["tx"]))
        fr.record_file(rdir / "tx.csv.gz")
        fr.budget.write_gz_csv(rdir / "reach.csv.gz", REACH_COLUMNS, ([r["market_id"], "" if r["oldest_ts"] is None else r["oldest_ts"], r["truncated"], r["n_prints"], r["n_tx"], r["pages"]] for r in _jsonl_iter(part)))
        fr.record_file(rdir / "reach.csv.gz")
        stat = Counter(r["status"] for r in _jsonl_iter(part))
        part.unlink(missing_ok=True)
        fr.counts.update(markets=len(have), **{f"markets_{k}": v for k, v in stat.items()})
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m_ = fr.manifest(None, {"complete": True, "status": PRINTS_STATUS})
    m_["status"] = PRINTS_STATUS
    return m_


# =====================================================================================================================================================
# q0310: the live collector (cron, outside the queue lanes; one invocation = one poll)
# =====================================================================================================================================================

RC_START_SLACK_S = 60.0  # a poll whose oldest change is more than 60 s newer than the requested start (overlap 120 s) left a hole in the overlap
LIVE_DAY_SALT_BYTES = 16
LIVE_FILES = {"frame": "frame_live.json", "state": "state.json", "baselines": "baselines.json", "bursts": "bursts.jsonl", "due": "books_due.jsonl", "books": "books.jsonl", "gaps": "gaps.jsonl",
              "polls": "polls.jsonl", "audit_dir": "audit_batches", "frames_dir": "frames", "seen": "markets_seen.json", "closed": "closed.json", "prints_final": "prints_final.json"}
LIVE_POST_CLOSE_D = 3  # prints of every market seen are refreshed until the window end + 3 d; q0311 waits for that final refresh
LIVE_PRINT_REFRESH_S = DAY
LIVE_WINDOW_DIRS = ("changes", "tx")


def rc_params(start_ts: float, cont: dict | None = None) -> dict:
    return {"action": "query", "format": "json", "formatversion": 2, "list": "recentchanges", "rcnamespace": 0, "rctype": "edit", "rcdir": "newer", "rclimit": RC_LIMIT, "rcstart": cm.iso(start_ts),
            "rcprop": "title|ids|sizes|timestamp|tags|user|userid|flags|comment", "maxlag": MW_MAXLAG, **(cont or {})}


def poll_recent_changes(limw, start_ts: float, *, max_batches: int = 20) -> dict:
    """One poll: ``list=recentchanges`` from ``start_ts`` following ``rccontinue`` to exhaustion. Never raises on a transport / maxlag failure: ``ok`` is false and the interval is logged
    as a gap by the caller. Returns ``changes`` (raw records), ``oldest`` / ``newest`` change times and the batch count."""
    out: list[dict] = []
    cont: dict = {}
    try:
        for _ in range(max_batches):
            data = wiki_get(limw, rc_params(start_ts, cont))
            out.extend(x for x in ((data.get("query") or {}).get("recentchanges") or []) if isinstance(x, dict))
            if not data.get("continue"):
                break
            cont = {k: v for k, v in data["continue"].items()}
        else:
            return {"ok": False, "error": "rccontinue did not end", "changes": out, "batches": max_batches}
    except (ApiError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)[:120], "changes": out, "batches": 0}
    ts = [parse_ts(x.get("timestamp")) for x in out]
    ts = [t for t in ts if math.isfinite(t)]
    return {"ok": True, "changes": out, "oldest": min(ts) if ts else math.nan, "newest": max(ts) if ts else math.nan}


def norm_change(rc: dict, bot_keys: set[str], salt: bytes) -> dict | None:
    """A tracked-page change in storable form. ``user`` / ``userid`` are used in memory (bot flag; an ephemeral per-day pseudonym ``uk`` for the 10-minute distinct-user test); the
    salt is rotated daily and never written, so the pseudonym does not link across days."""
    if rc.get("rcid") is None or rc.get("pageid") is None:
        return None
    ts = parse_ts(rc.get("timestamp"))
    if not math.isfinite(ts):
        return None
    hidden = bool(rc.get("userhidden")) or rc.get("user") in (None, "")
    name = "" if hidden else str(rc["user"])
    key = f"id:{rc['userid']}" if (not hidden and rc.get("userid")) else f"name:{name}"
    uk = "" if hidden else hashlib.sha256(salt + key.encode()).hexdigest()[:16]
    return {"rcid": int(rc["rcid"]), "revid": int(rc.get("revid") or 0), "page_id": str(rc["pageid"]), "rc_ts": ts, "delta": float(c14.num(rc.get("newlen")) - c14.num(rc.get("oldlen"))),
            "uk": uk, "bot": int(is_bot_name(name, bot_keys)), "revert": int(is_revert_at_save(rc.get("tags") or [], str(rc.get("comment") or ""))), "unknown_user": int(hidden)}


def live_burst_check(recent: list[dict], new: dict, thr: float | None, last_burst: float, gaps: list[tuple[float, float]]) -> dict | None:
    """The live burst rule at the arrival of ``new`` (same rule as Stage 1): >= 3 eligible revisions by >= 2 distinct known non-bot users in ``(b - 10 min, b]`` with sum |delta| >=
    100 bytes, count >= the baseline percentile, 6 h refractory. A window that touches a logged gap is 'unavailable (gap)'. ``recent`` are the page's changes incl. ``new``."""
    if new["bot"] or new["revert"]:
        return None
    b = new["rc_ts"]
    win = [r for r in recent if b - BURST_WINDOW_S < r["rc_ts"] <= b and not r["bot"] and not r["revert"]]
    users = {r["uk"] for r in win if r["uk"]}
    size = sum(abs(r["delta"]) for r in win)
    if len(win) < BURST_MIN_REVS or len(users) < BURST_MIN_USERS or size < BURST_MIN_BYTES:
        return None
    if b < last_burst + BURST_REFRACTORY_S:
        return None
    if thr is None or len(win) < max(thr, BURST_MIN_REVS):
        return None
    if any(g0 <= b and g1 >= b - BURST_WINDOW_S for g0, g1 in gaps):
        return {"b": b, "status": "unavailable (gap)", "count": len(win), "users": len(users), "bytes": size, "threshold": thr}
    return {"b": b, "status": "ok", "count": len(win), "users": len(users), "bytes": size, "threshold": thr}


def read_book(lim, token_id: str) -> dict:
    """CLOB ``/book`` best bid / best ask and displayed sizes, receipt-timed by the caller."""
    st, data = lim.get(CLOB_BOOK, {"token_id": token_id})
    if st != 200 or not isinstance(data, dict):
        raise ApiError(f"book status {st}")
    bids = [(c14.num(x.get("price")), c14.num(x.get("size"))) for x in (data.get("bids") or []) if isinstance(x, dict)]
    asks = [(c14.num(x.get("price")), c14.num(x.get("size"))) for x in (data.get("asks") or []) if isinstance(x, dict)]
    bids = [x for x in bids if math.isfinite(x[0]) and math.isfinite(x[1])]
    asks = [x for x in asks if math.isfinite(x[0]) and math.isfinite(x[1])]
    bb = max(bids, key=lambda x: x[0]) if bids else (math.nan, math.nan)
    ba = min(asks, key=lambda x: x[0]) if asks else (math.nan, math.nan)
    return {"best_bid": bb[0], "bid_size": bb[1], "best_ask": ba[0], "ask_size": ba[1]}


def live_window(freeze_ts: float | None, *, floor: str = T14_W2_FLOOR, cap: str = T14_W2_CAP) -> tuple[float, float]:
    """``(T14_W2_start, T14_W2_cap)``: start = max(W freeze + 1 d, 2026-10-26T00:00Z)."""
    start = ep(floor)
    if freeze_ts is not None:
        start = max(start, freeze_ts + W2_START_AFTER_FREEZE_D * DAY)
    return start, ep(cap)


def live_stop_reached(live_dir: Path, start: float, now: float) -> bool:
    """The stop counts bursts, never results: >= 300 bursts in >= 30 subjects whose 120-min book read exists, or ``T14_W2_start + 90 d`` has passed with that count met, or the cap."""
    bursts = list(_jsonl_iter(Path(live_dir) / LIVE_FILES["bursts"]))
    ok = [b for b in bursts if b.get("status") == "ok" and b["b"] + BOOK_OFFSETS_S[-1] <= now]
    enough = bool(len(ok) >= W2_STOP_BURSTS and len({b["page_id"] for b in ok}) >= W2_STOP_SUBJECTS)
    return bool(enough and now >= start + W2_WINDOW_D * DAY)


def ensure_dir(p: Path) -> Path:
    Path(p).mkdir(parents=True, exist_ok=True)
    return Path(p)


def refresh_live_frame(lim, limw, live_dir: Path, sports: set[str], now: float, *, queries: tuple[str, ...] = QUERIES) -> dict:
    """The daily refresh: the frozen queries on ACTIVE markets, the W title regex and exclusions, the entity rule and the Wikipedia summary (cached). New (entity, page) pairs go to a
    weekly blind audit batch file. Returns the live frame document (subjects with their open markets)."""
    cache_p = Path(live_dir) / "summaries_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.is_file() else {}
    rows: dict[str, dict] = {}
    for q in queries:
        evs, _ = search_all(lim, q, "active")
        for ev in evs:
            for m in ev.get("markets") or []:
                if not isinstance(m, dict):
                    continue
                r = parse_market(m, ev, fetched_as="active", term=q, sports_ids=sports)
                if r is None or r["death"] or r["sports_tag"] or r["sports_re"] or r["mention"] or r["entertainment"] or r["market_id"] in rows:
                    continue
                if not (math.isfinite(r["created_epoch"]) and math.isfinite(r["end_epoch"]) and r["end_epoch"] > now):
                    continue
                r["entity"] = entity_candidate(r["question"], r["event_title"])
                if r["entity"]:
                    rows[r["market_id"]] = r
    subjects: dict[str, dict] = {}
    new_pairs: list[list] = []
    for e in sorted({r["entity"] for r in rows.values()}):
        if e not in cache:
            cache[e] = wiki_summary(limw, e)
            new_pairs.append(e)
        s = cache[e]
        if not subject_ok(s):
            continue
        sub = subjects.setdefault(s["page_id"], {"entity": e, "title": s["canonical"], "description": s["description"], "country": country_of(s["description"], e), "markets": []})
        for r in rows.values():
            if r["entity"] == e:
                sub["markets"].append({k: r[k] for k in ("market_id", "condition_id", "token_yes", "yes_index", "created_epoch", "end_epoch", "fee_rate", "question")})
    cm.write_json_atomic(cache_p, cache)
    if new_pairs:
        wk = ensure_dir(Path(live_dir) / LIVE_FILES["audit_dir"]) / f"{c14.iso_week_of(now)}.csv"
        have = set(wk.read_text().splitlines()) if wk.is_file() else set()
        with wk.open("a", newline="", encoding="utf-8") as fh:
            if not have:
                fh.write(",".join(AUDIT_SAMPLE_COLUMNS) + "\n")
            w_ = csv.writer(fh)
            for e in new_pairs:
                s = cache[e]
                if subject_ok(s):
                    w_.writerow([e, s["canonical"], s["description"], next((r["question"] for r in rows.values() if r["entity"] == e), "")])
    doc = {"as_of": now, "subjects": subjects}
    cm.write_json_atomic(Path(live_dir) / LIVE_FILES["frame"], doc)
    snap = ensure_dir(Path(live_dir) / LIVE_FILES["frames_dir"]) / f"{c14.utc_day(now)}.json"  # the daily frames are kept (never overwritten by a later day): no subject drops out of the record
    if not snap.exists():
        cm.write_json_atomic(snap, doc)
    record_markets_seen(live_dir, doc, now)
    return doc


def record_markets_seen(live_dir: Path, frame: dict, now: float) -> dict:
    """The union of every mapped market ever seen by the live frame (with its subject, entity and country at first sight). Markets are never removed: a market that closes or resolves
    stays in the registry, so its prints are refreshed and W1-rep sees it (no selection on whether the event happened)."""
    p = Path(live_dir) / LIVE_FILES["seen"]
    seen = json.loads(p.read_text()) if p.is_file() else {}
    for sid, sub in (frame.get("subjects") or {}).items():
        for m in sub.get("markets") or []:
            if m["market_id"] not in seen:
                seen[m["market_id"]] = {**m, "subject": sid, "entity": sub.get("entity"), "country": sub.get("country"), "first_seen": now}
    cm.write_json_atomic(p, seen)
    return seen


def bootstrap_baseline(limw, title: str, bot_keys: set[str], now: float) -> dict:
    """A subject's 30-day causal baseline at entry (and daily): the percentile of its 10-minute window counts over the last 29 days from the revisions API, plus the first revision."""
    first = fetch_first_revision(limw, title)
    rows, info = fetch_page_revisions(limw, title, now - 31 * DAY, now, bot_keys, historical=False)  # live window: never clamped to T14_W_END
    el = eligible_revisions(rows)
    t = np.array([r["ts"] for r in el])
    ok = bool(info["status"] == "ok" and math.isfinite(first) and first <= now - BURST_BASELINE_D[0] * DAY and len(t) > 0)
    thr = baseline_threshold(t, now, BURST_WINDOW_S, BURST_PCT) if ok else None
    return {"as_of": now, "first_rev_ts": None if not math.isfinite(first) else first, "threshold": thr, "ok": ok, "n_eligible": len(el)}


def book_tasks(burst: dict, subject: dict) -> list[dict]:
    """Scheduled book reads for one ok burst: every mapped open market of the subject at ``receipt + 60 s, 5, 15, 120 min``."""
    bid = f"{burst['page_id']}|{int(burst['b'])}"
    return [{"task": f"{bid}|{m['market_id']}|{int(off)}", "burst": bid, "page_id": burst["page_id"], "market_id": m["market_id"], "token_yes": m["token_yes"], "offset_s": off,
             "due": burst["receipt"] + off} for m in subject["markets"] for off in BOOK_OFFSETS_S]


def w_live(hist_root: Path, transport, *, rules_sha: str, now: float, not_before: str = T14_W2_FLOOR, freeze_ts: float | None = None, bots_path: Path | None = None,
           rps: float = 2.0, wiki_rps: float = 1.0, disk_cap: int = int(LIVE_OUTPUT_CAP_GB * 1024**3), sleep=time.sleep, live_check=None, data_dumps: Path | None = None,
           data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None, repo_root: Path | None = None, max_books: int = LIVE_MAX_BOOKS_PER_RUN, refresh_s: float = LIVE_FRAME_REFRESH_S,
           salt_factory=None) -> dict:
    """q0310, ONE poll (a cron invocation every minute under flock). Before ``not_before`` / ``T14_W2_start`` it idles (heartbeat at least hourly, else exit 75); after the window it
    reports ``w_live_window_closed``. A poll: ``rcstart`` = newest change held - 120 s, follow ``rccontinue``, de-duplicate by ``rcid``, mark failed polls / holes / > 5 min silence as
    gaps; apply the Stage-1 burst rule (frozen bot list + name regex) to tracked pages; on a burst schedule ``/book`` reads at receipt + 60 s, 5, 15, 120 min for each mapped open market
    and execute the reads that are due. Reads no AREPO store."""
    live_dir = c14.require_output_root(Path(hist_root) / LIVE_RUN)
    start, cap = live_window(freeze_ts, floor=not_before)
    if now < start:
        return c14.wait_or_idle(live_dir, f"before T14_W2_start {cm.iso(start)}", now)
    closed = read_json(live_dir / LIVE_FILES["closed"]) or None
    stop = closed is None and live_stop_reached(live_dir, start, now)
    if closed is None and (stop or now >= cap):
        closed = {"closed_at": float(now if stop else cap), "by": "stop rule (bursts, never results)" if stop else "cap", "window": [cm.iso(start), cm.iso(cap)], "written_utc": cm.iso(now)}
        ensure_dir(live_dir)
        cm.write_once_json(live_dir / LIVE_FILES["closed"], closed)
    if closed is not None:
        return post_close_refresh(transport, live_dir, closed, now, rps=rps, sleep=sleep, live_check=live_check)
    c14.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    ensure_dir(live_dir)
    lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
    limw = hb.Limiter(transport, rps=min(wiki_rps, 1.0), sleep=sleep, live_check=live_check)
    sports = sports_registry_ids(repo_root)
    bot_keys = {r["bot_key"] for r in c14.read_csv_gz(Path(bots_path))} if bots_path and Path(bots_path).is_file() else set()
    sp, bp = live_dir / LIVE_FILES["state"], live_dir / LIVE_FILES["baselines"]
    state = json.loads(sp.read_text()) if sp.is_file() else {"newest_rc_ts": None, "last_ok_poll": None, "seen": [], "salt_day": None, "salt": None}
    day = c14.utc_day(now)
    if state.get("salt_day") != day:
        state["salt_day"] = day
        state["salt"] = (salt_factory() if salt_factory else hashlib.sha256(f"{now}|{id(state)}|{time.time_ns()}".encode()).hexdigest())
    salt = str(state["salt"]).encode()
    frame_p = live_dir / LIVE_FILES["frame"]
    frame = json.loads(frame_p.read_text()) if frame_p.is_file() else None
    refreshed = False
    try:
        if frame is None or now - float(frame.get("as_of", 0)) >= refresh_s:
            frame = refresh_live_frame(lim, limw, live_dir, sports, now)
            refreshed = True
    except (ApiError, RuntimeError):
        frame = frame or {"as_of": 0, "subjects": {}}
    if now - float(state.get("last_print_refresh") or 0.0) >= LIVE_PRINT_REFRESH_S:  # every market EVER seen (closed / resolved ones included), daily
        refresh_live_prints(lim, live_dir, seen_markets(live_dir))
        state["last_print_refresh"] = now
    base = json.loads(bp.read_text()) if bp.is_file() else {}
    try:
        for sid, sub in frame["subjects"].items():
            if sid not in base or (refreshed and now - float(base[sid].get("as_of", 0)) >= refresh_s):
                base[sid] = bootstrap_baseline(limw, sub["title"], bot_keys, now)
    except (ApiError, RuntimeError):
        pass
    cm.write_json_atomic(bp, base)
    tracked = {sid: sub for sid, sub in frame["subjects"].items() if (base.get(sid) or {}).get("ok")}
    # poll
    newest = state.get("newest_rc_ts")
    rcstart = (float(newest) - RC_OVERLAP_S) if newest else now - RC_OVERLAP_S
    poll = poll_recent_changes(limw, rcstart)
    gaps_p = live_dir / LIVE_FILES["gaps"]
    last_ok = state.get("last_ok_poll")
    seen = set(state.get("seen") or [])
    new_changes: list[dict] = []
    if poll["ok"]:
        if math.isfinite(poll.get("oldest", math.nan)) and poll["oldest"] > rcstart + RC_START_SLACK_S and newest:
            _jsonl_append(gaps_p, {"from": rcstart, "to": poll["oldest"], "why": "hole in the overlap", "receipt": now})
        if last_ok and now - float(last_ok) > RC_GAP_S and newest:
            _jsonl_append(gaps_p, {"from": float(newest), "to": now, "why": "no successful poll for more than 5 min", "receipt": now})
        for rc in poll["changes"]:
            if rc.get("rcid") in seen:
                continue
            seen.add(rc.get("rcid"))
            ch = norm_change(rc, bot_keys, salt)
            if ch and ch["page_id"] in tracked:
                ch["receipt"] = now
                new_changes.append(ch)
        if math.isfinite(poll.get("newest", math.nan)):
            state["newest_rc_ts"] = max(float(newest or 0), poll["newest"])
        state["last_ok_poll"] = now
    else:
        _jsonl_append(gaps_p, {"from": rcstart, "to": now, "why": f"failed poll: {poll.get('error')}", "receipt": now})
    state["seen"] = sorted(x for x in seen if x is not None)[-20000:]
    _jsonl_append(live_dir / LIVE_FILES["polls"], {"receipt": now, "ok": poll["ok"], "rcstart": rcstart, "n_changes": len(poll["changes"]), "n_tracked": len(new_changes), "error": poll.get("error")})
    # changes log and bursts
    ch_dir = ensure_dir(live_dir / "changes")
    ch_p = ch_dir / f"{day}.jsonl"
    for ch in sorted(new_changes, key=lambda c: (c["rc_ts"], c["rcid"])):
        _jsonl_append(ch_p, ch)
    gaps = [(g["from"], g["to"]) for g in _jsonl_iter(gaps_p)]
    existing = list(_jsonl_iter(live_dir / LIVE_FILES["bursts"]))
    due_p = live_dir / LIVE_FILES["due"]
    recent_all = [r for p in sorted(ch_dir.glob("*.jsonl"))[-2:] for r in _jsonl_iter(p)]
    n_bursts = 0
    for ch in sorted(new_changes, key=lambda c: (c["rc_ts"], c["rcid"])):
        recent = [r for r in recent_all if r["page_id"] == ch["page_id"]]
        last = max([b["b"] for b in existing if b["page_id"] == ch["page_id"] and b.get("status") == "ok"] or [-math.inf])
        res = live_burst_check(recent, ch, (base.get(ch["page_id"]) or {}).get("threshold"), last, gaps)
        if res is None:
            continue
        sub = tracked[ch["page_id"]]
        rec = {**res, "page_id": ch["page_id"], "receipt": ch["receipt"], "poll_latency_s": ch["receipt"] - ch["rc_ts"], "entity": sub.get("entity"), "country": sub.get("country"),
               "markets": [dict(m) for m in sub.get("markets") or []]}  # the subject's mapped markets AT the burst: W2-rep never depends on a later frame
        _jsonl_append(live_dir / LIVE_FILES["bursts"], rec)
        existing.append(rec)
        n_bursts += 1
        if rec["status"] == "ok":
            for t in book_tasks(rec, rec):
                _jsonl_append(due_p, t)
    # execute due book reads
    done_tasks = {b["task"] for b in _jsonl_iter(live_dir / LIVE_FILES["books"])}
    n_books = 0
    for t in _jsonl_iter(due_p):
        if n_books >= max_books:
            break
        if t["task"] in done_tasks or t["due"] > now:
            continue
        try:
            bk = read_book(lim, t["token_yes"])
        except (ApiError, RuntimeError) as exc:
            bk = {"best_bid": math.nan, "bid_size": math.nan, "best_ask": math.nan, "ask_size": math.nan, "error": str(exc)[:80]}
        _jsonl_append(live_dir / LIVE_FILES["books"], {**{k: t[k] for k in ("task", "burst", "page_id", "market_id", "offset_s")}, "receipt": now, **bk})
        done_tasks.add(t["task"])
        n_books += 1
    cm.write_json_atomic(sp, state)
    cm.write_json_atomic(live_dir / "heartbeat.json", {"epoch": now, "utc": cm.iso(now), "status": "polling", "tracked_subjects": len(tracked)})
    return {"status": "w_live_polled", "complete": False, "stopped": None, "poll_ok": poll["ok"], "changes": len(poll["changes"]), "tracked_changes": len(new_changes), "bursts": n_bursts,
            "books": n_books, "frame_refreshed": refreshed, "requests": lim.requests + limw.requests}


def seen_markets(live_dir: Path) -> list[dict]:
    """Every market of the ``markets_seen`` registry (market-id order)."""
    p = Path(live_dir) / LIVE_FILES["seen"]
    seen = json.loads(p.read_text()) if p.is_file() else {}
    return [seen[k] for k in sorted(seen)]


def refresh_live_prints(lim, live_dir: Path, markets: Iterable[dict], *, page_limit: int = c14.DATA_PAGE_LIMIT, pages: int = c14.DATA_PAGES) -> int:
    """The daily post-hoc Data API prints (<= 2 pages) of every market EVER seen by the live frame (open, closed and resolved alike, until the window end + 3 d), merged by (time, price,
    size) into ``tx/<market>.json`` for W1-rep. Nothing is written for a market whose first page fails (it is retried the next day)."""
    d = ensure_dir(Path(live_dir) / "tx")
    n = 0
    for m in markets:
        try:
            prints, info = c14.c12.fetch_prints_paged(lim, m["condition_id"], 0.0, limit=page_limit, pages=pages)
        except (ApiError, RuntimeError):
            continue
        rows = build_transactions(prints, int(m["yes_index"]))
        p = d / f"{m['market_id']}.json"
        old = json.loads(p.read_text()) if p.is_file() else {"tx": []}
        merged = {(r["ts"], r["price"], r["size"]): r for r in [*old["tx"], *rows]}
        cm.write_json_atomic(p, {"market_id": m["market_id"], "oldest_ts": info["oldest_ts"] if math.isfinite(info["oldest_ts"]) else None, "truncated": bool(info["truncated"]),
                                 "tx": [merged[k] for k in sorted(merged)]})
        n += 1
    return n


def post_close_refresh(transport, live_dir: Path, closed: dict, now: float, *, rps: float = 2.0, sleep=time.sleep, live_check=None) -> dict:
    """After the live window closed (``closed.json``): no polling; the prints of every market seen are refreshed daily until ``closed_at + 3 d``, and the first refresh at or after that
    time is the final one (``prints_final.json``, write-once): q0311 waits for it."""
    ld = Path(live_dir)
    end = float(closed["closed_at"]) + LIVE_POST_CLOSE_D * DAY
    fin = ld / LIVE_FILES["prints_final"]
    out = {"status": LIVE_STATUS_CLOSED, "complete": True, "stopped": None, "closed": closed, "prints_final": fin.exists()}
    if fin.exists():
        return out
    sp = ld / LIVE_FILES["state"]
    state = json.loads(sp.read_text()) if sp.is_file() else {}
    if now >= end or now - float(state.get("last_print_refresh") or 0.0) >= LIVE_PRINT_REFRESH_S:
        lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        n = refresh_live_prints(lim, ld, seen_markets(ld))
        state["last_print_refresh"] = now
        cm.write_json_atomic(sp, state)
        out["refreshed_markets"] = n
        if now >= end:
            cm.write_once_json(fin, {"refreshed_at": now, "closed_at": closed["closed_at"], "markets": n, "utc": cm.iso(now)})
            out["prints_final"] = True
    return out


# =====================================================================================================================================================
# q0311: Stage 2 on the live window (recorded books)
# =====================================================================================================================================================


def load_live(live_dir: Path) -> dict:
    """The live record for q0311: bursts (each carries its subject's market snapshot), books, the post-hoc transactions of every market seen, the markets-seen registry and the
    closure record. The rolling ``frame_live.json`` is NOT used by any statistic (a subject whose markets closed would drop out of it)."""
    ld = Path(live_dir)
    bursts = [b for b in _jsonl_iter(ld / LIVE_FILES["bursts"])]
    books: dict[tuple[str, str, int], dict] = {}
    for b in _jsonl_iter(ld / LIVE_FILES["books"]):
        books[(b["burst"], b["market_id"], int(b["offset_s"]))] = b
    txs = {}
    for p in sorted((ld / "tx").glob("*.json")) if (ld / "tx").is_dir() else []:
        doc = json.loads(p.read_text())
        txs[doc["market_id"]] = TxSeries(doc["tx"], oldest_ts=c14.num(doc.get("oldest_ts")), truncated=bool(doc.get("truncated")))
    latencies = [b.get("poll_latency_s") for b in bursts if b.get("poll_latency_s") is not None]
    return {"bursts": bursts, "books": books, "txs": txs, "latency": latencies, "seen": seen_markets(ld), "closed": read_json(ld / LIVE_FILES["closed"]) or None}


def w2rep_units(L: dict, *, now: float, dropped_entities: set[str] | None = None, extra_per_side: float = 0.0) -> dict:
    """W2-rep units: ok bursts whose 120-min read can exist; the market is, among the subject's mapped markets SNAPSHOTTED IN THE BURST RECORD, the one with the nearest end at or after
    ``b + 3 h`` whose 60-s book mid is in [0.05, 0.60]; entry at the recorded best ask of that book (size <= the displayed ask size, capped at 100), exit at the recorded best bid of the
    120-min book; fee as W2. Missing / one-sided books are 'unavailable' (counted), never filled."""
    units: list[dict] = []
    labels: Counter = Counter()
    for bu in L["bursts"]:
        if bu.get("status") != "ok":
            labels["unavailable (gap)"] += 1
            continue
        mkts = bu.get("markets")
        if mkts is None:
            labels["no market snapshot"] += 1
            continue
        if dropped_entities and bu.get("entity") in dropped_entities:
            labels["dropped (map audit)"] += 1
            continue
        if bu["receipt"] + BOOK_OFFSETS_S[-1] > now:
            labels["not matured"] += 1
            continue
        bid = f"{bu['page_id']}|{int(bu['b'])}"
        chosen = None
        for m in sorted((m for m in mkts if m["end_epoch"] >= bu["b"] + W2_END_AHEAD_S and m["created_epoch"] <= bu["b"]), key=lambda x: (x["end_epoch"], x["market_id"])):
            b60 = L["books"].get((bid, m["market_id"], int(BOOK_OFFSETS_S[0])))
            if not b60 or not (math.isfinite(c14.num(b60.get("best_bid"))) and math.isfinite(c14.num(b60.get("best_ask")))):
                continue
            mid = (b60["best_bid"] + b60["best_ask"]) / 2
            if W2_STATE_BAND[0] <= mid <= W2_STATE_BAND[1]:
                chosen = (m, b60, mid)
                break
        if chosen is None:
            labels["no qualifying book"] += 1
            continue
        m, b60, mid = chosen
        b120 = L["books"].get((bid, m["market_id"], int(BOOK_OFFSETS_S[-1])))
        if not b120 or not math.isfinite(c14.num(b120.get("best_bid"))):
            labels["no exit book"] += 1
            continue
        ask, bidp = float(b60["best_ask"]), float(b120["best_bid"])
        r = c14.taker_rate(m.get("fee_rate"))
        units.append({"subject": bu["page_id"], "b": bu["b"], "week": iso_week(bu["b"]), "story": story_day(bu["b"], bu.get("country") or country_of("", bu["page_id"])), "quarter": quarter_of(bu["b"]),
                      "market_id": m["market_id"], "state": mid, "e": ask, "x": bidp, "size": min(PAPER_SIZE, c14.num(b60.get("ask_size"))), "net": net_of(ask, bidp, r, extra_per_side),
                      "stale": False, "rise": False})
        labels["unit"] += 1
    return {"units": units, "labels": dict(labels)}


def w2_rep(L: dict, *, now: float, dropped_entities: set[str] | None = None) -> dict:
    """W2-rep on the closed live window (recorded books). 'Not run (power)' below 300 ok bursts in 30 subjects. ``checks_ok`` = floor, the +1c-per-side cost robustness and the small-G
    sign rules (every binding condition but the primary p gate)."""
    pk = w2rep_units(L, now=now, dropped_entities=dropped_entities)
    units = pk["units"]
    ok_bursts = [b for b in L["bursts"] if b.get("status") == "ok"]
    out: dict = {"test": "W2-rep", "label": LABEL_W_REP, "labels": pk["labels"], "n_bursts_ok": len(ok_bursts), "n_subjects": len({b["page_id"] for b in ok_bursts}),
                 "poll_latency_s": {"median": float(np.median(L["latency"])) if L["latency"] else None, "p90": float(np.percentile(L["latency"], 90)) if L["latency"] else None}}
    if len(ok_bursts) < W2REP_MIN_BURSTS or out["n_subjects"] < W2REP_MIN_SUBJECTS:
        out.update(not_run("not run (power)"), label=LABEL_W_REP, checks_ok=False)
        return out
    if len(units) < 2:
        out.update(not_run("not testable (units)"), label=LABEL_W_REP, checks_ok=False)
        return out
    v = np.array([u["net"] for u in units])
    cl = w2_clusters(units)
    res = _p(v, cl)
    est = float(v.mean())
    cost = w2rep_units(L, now=now, dropped_entities=dropped_entities, extra_per_side=COST_ROBUST_PER_SIDE)["units"]
    cost_ok = bool(cost and np.mean([u["net"] for u in cost]) > 0)
    out.update(testable=res["testable"], p=res["p"], effect=est, n=len(units), floor_ok=bool(est >= W2_FLOOR), ways=res["ways"], cost_robust_ok=cost_ok,
               small_g_rules_hold=res["small_g_rules_hold"], size_weighted=float(np.average(v, weights=[u["size"] for u in units])))
    out["robustness_ok"] = cost_ok
    out["checks_ok"] = bool(res["testable"] and out["floor_ok"] and cost_ok and res["small_g_rules_hold"])
    return out


def live_w1_units(L: dict, window_end: float) -> list[dict]:
    """Decisive moves in the live window (``D`` before the window end) of every market the live frame EVER mapped (the ``markets_seen`` registry: closed and resolved markets stay in),
    from the post-hoc Data API prints (same rule as Stage 1)."""
    out = []
    bursts_ok = [b for b in L["bursts"] if b.get("status") == "ok"]
    if not bursts_ok:
        return out
    lo = min(b["b"] for b in bursts_ok) - 3 * DAY
    for m in L["seen"]:
        tx = L["txs"].get(m["market_id"])
        if tx is None:
            continue
        mv = decisive_move(tx, (lo, window_end))
        if mv:
            out.append({"subject": m["subject"], "market_id": m["market_id"], "cls": "", "created": m["created_epoch"], "country": m.get("country"), "head": False, "attn": False, **mv})
    kept = dedupe_moves(out)
    for u in kept:
        u["week"] = iso_week(u["D0"])
    return kept


def w1_rep(L: dict, window_end: float) -> dict:
    """W1-rep: the Stage-1 statistic on live decisive moves with the live burst log (receipt time) as the lead clock; >= 20 moves in >= 15 subjects (the design's only minimum), else 'not
    run (power)'."""
    units = live_w1_units(L, window_end)
    out: dict = {"test": "W1-rep", "label": LABEL_W_REP, "n_moves": len(units)}
    if len(units) < W1REP_MIN_MOVES or len({u["subject"] for u in units}) < W1REP_MIN_SUBJECTS:
        out.update(not_run("not run (power)"), label=LABEL_W_REP, checks_ok=False)
        return out
    bursts: dict[str, list[float]] = {}
    for b in L["bursts"]:
        if b.get("status") == "ok":
            bursts.setdefault(b["page_id"], []).append(float(b["receipt"]))
    for k in bursts:
        bursts[k].sort()
    v = np.array([w1_value(u, bursts.get(u["subject"], []), L["txs"][u["market_id"]])[0] for u in units])
    ok = np.isfinite(v)
    if ok.sum() < 2:
        out.update(not_run("not testable (moves)"), label=LABEL_W_REP, checks_ok=False)
        return out
    uo = [u for u, k in zip(units, ok, strict=True) if k]
    res = c14.cluster_p(v[ok], w1_clusters(uo), min_units=W1REP_MIN_MOVES, min_first_clusters=W1REP_MIN_SUBJECTS)
    est = float(v[ok].mean())
    out.update(testable=res["testable"], p=res["p"], effect=est, n=int(ok.sum()), floor_ok=bool(est >= W1_FLOOR), ways=res["ways"], robustness_ok=True,
               small_g_rules_hold=res["small_g_rules_hold"], note="the binding Stage-1 placebo is not repeated on the live window (too few moves); the point estimate and p carry the verdict")
    out["checks_ok"] = bool(res["testable"] and out["floor_ok"] and res["small_g_rules_hold"])
    return out


def live_window_end(live_dir: Path, now: float, cap: str = T14_W2_CAP) -> float:
    """The closed live window's end (``closed.json``, written by q0310 when the stop rule or the cap closed the window). q0311 never analyses a partial window: before the closure, before
    the end + 3 d, or before the final post-close print refresh, it waits (``NotNow``, pending)."""
    ld = Path(live_dir)
    closed = read_json(ld / LIVE_FILES["closed"]) or None
    if closed is None:
        raise NotNow(f"the live window is not closed (no {LIVE_FILES['closed']}; cap {cap}): q0311 never analyses a partial window (pending)")
    end = float(closed["closed_at"])
    if now < end + LIVE_POST_CLOSE_D * DAY:
        raise NotNow(f"q0311 waits until the window end + {LIVE_POST_CLOSE_D} d ({cm.iso(end + LIVE_POST_CLOSE_D * DAY)}) (pending)")
    if not (ld / LIVE_FILES["prints_final"]).exists():
        raise NotNow("the final post-close print refresh (window end + 3 d) has not run yet (pending)")
    return end


def rep_w(live_dir: Path, tests: tuple[str, ...], *, now: float, k2: int | None = None, live_audit: dict | None = None) -> dict:
    """q0311: the triggered Stage-2 tests on the CLOSED live window. ``stage2_early_alpha_ok`` = p < alpha / 4 (strict); ``stage2_pass_alpha_over_k`` = ``checks_ok`` and p < alpha / k2
    (alpha / 4 while k2 is unknown); the CB14-wide ``stage2-final`` Holm can only add passes."""
    end = live_window_end(live_dir, now)
    L = load_live(live_dir)
    dropped = set((live_audit or {}).get("drop", [])) if live_audit else None
    out: dict = {"label": LABEL_W_REP, "k2": k2, "window_end": end, "closed": L["closed"]}
    for t in tests:
        r = w2_rep(L, now=now, dropped_entities=dropped) if t == "W2" else w1_rep(L, end)
        r["stage2_early_alpha_ok"] = c14.early_stage2_ok(r.get("p") if r.get("testable") else None)
        alpha_k = c14.STAGE_ALPHA / k2 if k2 else c14.EARLY_ALPHA2
        r["stage2_pass_alpha_over_k"] = bool(r.get("checks_ok") and r.get("testable") and r.get("p", 1.0) < alpha_k)
        out[f"{t}_rep"] = r
    out["holm_family_partial"] = c14.stage2_holm({t: out[f"{t}_rep"].get("p") if out[f"{t}_rep"].get("testable") else None for t in tests})  # information only: stage2-final decides
    return out


# =====================================================================================================================================================
# Smoke (family checks), declared
# =====================================================================================================================================================


def _chk(ok: bool, **detail) -> dict:
    return {"pass": bool(ok), **detail}


def smoke_offline(ctx: dict) -> dict:
    """Fixture checks, no network: refusals (every refused root, ``h12_say``, ``h11_attn/holdout``, pageview files), forbidden fields, the ``mw-reverted`` rule, ``T14_W_END``, the
    part hashes."""
    res: dict = {}
    refused = 0
    for bad in (Path("x/h12_say/events.csv.gz"), Path("x/h11_attn/holdout/tx.csv.gz"), Path("x/flow_screen/a"), Path("x/creative_batch13/a"), Path("x/cross_venue_live/a")):
        try:
            c14.guard_input_path(bad)
        except Refused:
            refused += 1
    try:
        c14.guard_id_file(Path("x/h11_attn/pageviews.csv.gz"))
    except Refused:
        refused += 1
    forb = 0
    for col in ("side", "proxyWallet", "user", "userid", "outcomePrices", "closedTime", "mw-reverted"):
        try:
            c14.assert_clean_columns([col])
        except Refused:
            forb += 1
    row = rev_row({"revid": 1, "parentid": 0, "timestamp": "2025-01-01T00:00:00Z", "user": "Alice", "userid": 5, "size": 10, "comment": "x", "tags": ["mw-reverted"]}, None, {}, set(), "9")
    clean = bool(row and not (set(row) - set(REV_COLUMNS)) and row["revert"] == 0)
    try:
        require_before_w_end(w_end())
        end_ok = False
    except Refused:
        end_ok = True
    end_ok = bool(end_ok and require_before_w_end(w_end() - 1) == w_end() - 1)
    parts = {p: c14.rules_part_file_doc(p).get("part_declared") is not False for p in ("common", "W")}
    res["guards_fixture_W"] = _chk(refused == 6 and forb == 7 and clean and end_ok, refused=refused, forbidden=forb, mw_reverted_ignored=clean, t14_w_end=end_ok)
    res["w_part_hashes"] = _chk(all(parts.values()), parts=parts)
    return res


def smoke_online(lim, ctx: dict) -> dict:
    """<= 30 requests, counts only: no price, outcome, volume or wallet is stored. Out-of-window / out-of-frame sources only."""
    res: dict = {}
    r0 = lim.requests
    # public-search paging on the thinnest query term
    evs, info = search_all(lim, "step down", "closed", max_pages=5)
    res["w_public_search_paging"] = _chk(info["pages"] >= 1 and info["total"] is not None, pages=info["pages"], events=len(evs), total=info["total"])
    # do public-search events carry the fields the frame rules read (tags, series, market createdAt, negRiskMarketID)? Reported; the criterion is that the /events lookup fallback
    # returns them (the frame looks up every event with a missing field, <= 600 requests)
    n_ev = len(evs)
    has = {"tags": sum(1 for e in evs if "tags" in e), "series": sum(1 for e in evs if "series" in e),
           "created_at_all_markets": sum(1 for e in evs if e.get("markets") and all(isinstance(m, dict) and "createdAt" in m for m in e["markets"])),
           "neg_risk_id_on_neg_risk": sum(1 for e in evs if e.get("negRisk") and all(isinstance(m, dict) and "negRiskMarketID" in m for m in e.get("markets") or []))}
    lk_ok, lk_detail = False, {}
    if evs:
        got, used = lookup_events(lim, [str(evs[0].get("id"))])
        full = got.get(str(evs[0].get("id")))
        lk_ok = bool(full and "tags" in full and full.get("markets") and all(isinstance(m, dict) and "createdAt" in m for m in full["markets"]))
        lk_detail = {"found": full is not None, "requests": used}
    res["w_search_fields"] = _chk(lk_ok, events=n_ev, present=has, lookup=lk_detail)
    # entity rule + summary type on up to 5 out-of-frame subjects (markets listed after the W listing window)
    sports = set()
    evs2, _ = search_all(lim, "resign", "active", max_pages=2)
    ents: list[str] = []
    _, post = listed_window()
    for ev in evs2:
        for m in ev.get("markets") or []:
            if not isinstance(m, dict):
                continue
            row = parse_market(m, ev, fetched_as="active", term="resign", sports_ids=sports)
            if row and row["created_epoch"] >= post and not row["death"]:
                e = entity_candidate(row["question"], row["event_title"])
                if e and e not in ents:
                    ents.append(e)
    ents = ents[:SMOKE_SUBJECTS]
    sums = [wiki_summary(lim, e) for e in ents]
    res["w_entity_summary"] = _chk(len(ents) >= 3 and sum(1 for s in sums if s["status"] == 200 and s["type"]) >= 3, candidates=len(ents), http200=sum(1 for s in sums if s["status"] == 200),
                                   standard=sum(1 for s in sums if subject_ok(s)))
    # revisions bounds and continuation on one busy page (an out-of-window 30-day range): rvlimit = SMOKE_RV_LIMIT (1), so ANY second revision in the range forces a continuation; the
    # criterion is robust to how busy the page was (a full first batch must continue, and the continued batch must be non-empty and in bounds)
    start, end = ep(SMOKE_RV_RANGE[0]), ep(SMOKE_RV_RANGE[1])
    d1 = wiki_get(lim, {"action": "query", "format": "json", "formatversion": 2, "prop": "revisions", "titles": SMOKE_RV_TITLE, "rvprop": "ids|timestamp|size|comment|tags|flags|user|userid",
                        "rvlimit": SMOKE_RV_LIMIT, "rvdir": "newer", "rvstart": cm.iso(start), "rvend": cm.iso(end), "maxlag": MW_MAXLAG})
    pg = ((d1.get("query") or {}).get("pages") or [{}])[0]
    revs = pg.get("revisions") or []
    cont = d1.get("continue") or {}
    d2 = wiki_get(lim, {"action": "query", "format": "json", "formatversion": 2, "prop": "revisions", "titles": SMOKE_RV_TITLE, "rvprop": "ids|timestamp|size|tags", "rvlimit": SMOKE_RV_LIMIT,
                        "rvdir": "newer", "rvstart": cm.iso(start), "rvend": cm.iso(end), "maxlag": MW_MAXLAG, **cont}) if cont else {}
    revs2 = (((d2.get("query") or {}).get("pages") or [{}])[0].get("revisions")) or []
    in_bounds = all(start <= parse_ts(r.get("timestamp")) <= end for r in [*revs, *revs2])
    keys_ok = bool(revs) and all(k in revs[0] for k in ("revid", "parentid", "timestamp", "size", "tags"))
    paging_ok = bool(len(revs) == SMOKE_RV_LIMIT and cont and len(revs2) > 0)
    res["w_revisions_bounds"] = _chk(keys_ok and in_bounds and paging_ok, first_batch=len(revs), second_batch=len(revs2), continued=bool(cont), rvlimit=SMOKE_RV_LIMIT)
    bots = fetch_bot_list(lim)
    res["w_bot_list"] = _chk(len(bots) >= 100, bots=len(bots))
    # Data API prints with 2-page reach on one 2024 and one 2025 out-of-frame market (row counts only)
    reach = {}
    for tag, day in (("2024", "2024-09-10"), ("2025", "2025-06-10")):
        st, mk = lim.get(c14.GAMMA_EVENTS.replace("/events", "/markets"), {"closed": "true", "end_date_min": f"{day}T00:00:00Z", "end_date_max": f"{day}T23:59:59Z", "order": "volumeNum", "ascending": "false", "limit": 1})
        cid = str(mk[0].get("conditionId")) if st == 200 and isinstance(mk, list) and mk and isinstance(mk[0], dict) else ""
        if cid:
            rows, inf = c14.c12.fetch_prints_paged(lim, cid, 0.0)
            reach[tag] = {"prints": len(rows), "pages": inf["pages"], "truncated": bool(inf["truncated"])}
        else:
            reach[tag] = {"prints": 0, "pages": 0, "truncated": False}
    res["w_data_api_reach"] = _chk(reach["2024"]["prints"] > 0 and reach["2025"]["prints"] > 0, reach=reach)
    rc = wiki_get(lim, {"action": "query", "format": "json", "formatversion": 2, "list": "recentchanges", "rcnamespace": 0, "rctype": "edit", "rclimit": 5, "rcprop": "title|ids|sizes|timestamp|tags|user",
                        "maxlag": MW_MAXLAG})
    chg = (rc.get("query") or {}).get("recentchanges") or []
    res["w_recentchanges"] = _chk(bool(chg) and all(k in chg[0] for k in ("timestamp", "title", "oldlen", "newlen", "tags")), n=len(chg))
    res["_requests"] = {"pass": (lim.requests - r0) <= SMOKE_MAX_REQUESTS, "requests": lim.requests - r0}
    return res


def declared() -> dict:
    return {"family": "W", "label": LABEL_W, "windows": {"listed": list(W_LISTED), "calendar_start": W_CALENDAR_START, "t14_w_end": T14_W_END, "w2_floor": T14_W2_FLOOR, "w2_cap": T14_W2_CAP},
            "frame": {"queries": list(QUERIES), "title_regex": TITLE_RE.pattern, "sports_registry_sha256": SPORTS_REGISTRY_SHA256, "coach_regex": COACH_RE.pattern, "mention_regex": MENTION_RE.pattern,
                      "completeness": {"tag": COMPLETENESS_TAG_ID, "months": list(COMPLETENESS_MONTHS), "min": COMPLETENESS_MIN}},
            "entity": {"source_sha256": ENTITY_SOURCE_SHA256, "stop_list_size": len(STOP_LIST), "article_min_age_d": ARTICLE_MIN_AGE_D, "audit_precision_min": AUDIT_PRECISION_MIN},
            "burst": {"window_s": BURST_WINDOW_S, "min_revs": BURST_MIN_REVS, "min_users": BURST_MIN_USERS, "min_bytes": BURST_MIN_BYTES, "pct": BURST_PCT, "baseline_d": list(BURST_BASELINE_D),
                      "refractory_s": BURST_REFRACTORY_S, "grids": {k: list(v) for k, v in BURST_GRIDS.items()}, "mw_reverted": "never parsed"},
            "decisive_move": {"price": DECISIVE_PRICE, "confirm_s": DECISIVE_CONFIRM_S, "v_max": DECISIVE_V_MAX, "rise": DECISIVE_RISE, "dedup_s": DECISIVE_DEDUP_S},
            "tests": {"W1": {"floor": W1_FLOOR, "lead_window_s": list(W1_LEAD_WINDOW), "state_cap": W1_STATE_CAP, "placebo_anchors": PLACEBO_ANCHORS, "min_anchors": PLACEBO_MIN_ANCHORS,
                             "min_moves": W1_MIN_MOVES, "min_subjects": W1_MIN_SUBJECTS, "min_weeks": W1_MIN_WEEKS, "ways": ["subject", "iso_week"]},
                      "W2": {"floor": W2_FLOOR, "state_band": list(W2_STATE_BAND), "entry_window_s": list(ENTRY_WINDOW), "exit_window_s": list(EXIT_WINDOW), "paper_size": PAPER_SIZE,
                             "fee_floor": FIXED_FEE_FLOOR, "ways": ["subject", "iso_week", "story_day"], "worst_case_p90": WORST_CASE_P90}},
            "gates": {"GWC": [MIN_MARKETS_GWC, MIN_EVENTS_GWC, MIN_SUBJECTS_GWC], "GW": {"W1": [W1_MIN_MOVES, W1_MIN_SUBJECTS, W1_MIN_WEEKS], "W2": [W2_MIN_UNITS, W2_MIN_SUBJECTS, W2_MIN_WEEKS, W2_REACH_MIN]},
                      "GWP": {"W1_max_mde": GWP_W1_MAX_MDE, "W2_max_mde": GWP_W2_MAX_MDE_C}},
            "live": {"poll_s": RC_POLL_S, "overlap_s": RC_OVERLAP_S, "gap_s": RC_GAP_S, "slack_s": RC_START_SLACK_S, "book_offsets_s": list(BOOK_OFFSETS_S), "stop": [W2_STOP_BURSTS, W2_STOP_SUBJECTS]},
            "placebo_seed": c14.PLACEBO_SEEDS["W1_shift"], "country_map_entries": len(COUNTRY_MAP), "smoke_needs": list(SMOKE_NEEDS)}
