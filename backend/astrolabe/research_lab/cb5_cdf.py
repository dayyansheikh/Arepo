# ruff: noqa: E501
"""CB5-L: ladder-versus-bucket CDF consistency (CH59), docs/research_lab/CREATIVE_BATCH_5.md section CB5-L and 4.1.

Part 1, the frame (metadata only; ``cdf-grouper-v1``; the grouper is hashed into the CB5 declaration before any title
is read): period table, bucket events, ladder rungs, subject match, mutual-best families, pair (f, D) construction,
the text-only audit and its one-revision rule, parse guard that drops ``outcomePrices`` / ``outcomes`` at parse.

Part 2, the screen: per-capture pair state (net_A / net_B at the touch, leg-timing rule), triggers, execution at the
next complete capture, L1 test, mismatched-family coherence placebo (can fail), family-level ``r_inc`` with a Wilson
bound, divergence / realised-payoff / depth gates ("unknown" and "inconclusive" never count as met), persistence.

Pure functions; no network and no data access except ``guarded_events``.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import cb3_common as C3
from . import cost_regimes, cross_venue, if_h2

GROUPER_VERSION = "cdf-grouper-v1"
ET = ZoneInfo("America/New_York")

# ---- declared constants (all hashed through cb5_declaration) -----------------------------------------------------------
MIN_JACCARD, MIN_SHARED, MARGIN = 0.6, 3, 0.10
EXTRA_CONFLICT = frozenset("announce confirm officially first again before after".split())
FRAME_START, FRAME_END = "2025-06-01", "2026-10-10"
TRIGGER_MIN = 0.005  # 0.5c
GAP_H = (1.5, 3.0)
LEG_SPREAD_S = 300
DEPTH_MIN_SIZE = 5.0
PLACEBO_DRAWS, SEED_PLACEBO = 200, 5162
PLACEBO_MAX_ADVANCE_RATE = 0.015
PLACEBO_MIN_FAMILIES = 20
G59_MIN_FAMILIES = 20
RINC_MIN_FAMILIES = 30
PAYOFF_MAX_SHORT, PAYOFF_MIN_DETERMINED = 0.02, 30
AUDIT_N, AUDIT_MAX_BAD = 50, 0.05
Z95 = 1.96  # Wilson 95% (z^2 = 3.84)
PERSIST_STEPS = (1, 2, 3, 6)  # captures after c (2h cadence) for the persistence curve
MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
          "september": 9, "october": 10, "november": 11, "december": 12,
          "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
_MON = "|".join(sorted(MONTHS, key=len, reverse=True))
RE_MONTH = re.compile(rf"^({_MON})\.?(?:\s+(\d{{4}}))?$", re.I)
RE_QUARTER = re.compile(r"^q([1-4])(?:\s+(\d{4}))?$", re.I)
RE_YEAR = re.compile(r"^(\d{4})$")
RE_BEFORE = re.compile(r"^before\s+(.+)$", re.I)
RE_BY = re.compile(r"^by\s+(.+)$", re.I)
RE_NOT_IN = re.compile(r"^not\s+in\s+(\d{4})$", re.I)
RE_AFTER = re.compile(r"^after\s+(.+)$", re.I)
RE_LATER = re.compile(r"^(\d{4})\s+or\s+later$", re.I)
RE_DEC_FORM = re.compile(r"\b(through|until|continue)\b", re.I)
RE_BEFORE_DATE = re.compile(r"\bbefore\s+(?:the\s+)?(?:end\s+of\s+)?" + if_h2.DATE_RE.pattern, re.I)
RE_BUCKET_PHRASE = re.compile(r"\b(?:in\s+which\s+(?:month|quarter|year)|which\s+(?:month|quarter|year)|when)\b", re.I)
RE_BUCKET_IN = re.compile(rf"\bin\s+(?:{_MON}|q[1-4]|\d{{4}})\b", re.I)
RE_URL = re.compile(r"https?://(?:www\.)?([^/\s)\"']+)", re.I)
RE_SOURCE = re.compile(r"resolution\s+source[s]?\s*(?:is|will be|are|:)?\s*:?\s*([^.\n]{3,80})", re.I)


class GrouperAuditFailed(RuntimeError):
    """The grouper audit failed twice: CB5-L stops."""


# ---- parse guard -------------------------------------------------------------------------------------------------------

_DROP_KEYS = ("outcomePrices", "outcomes", "lastTradePrice", "bestBid", "bestAsk")
_MKT_KEEP = ("id", "conditionId", "question", "groupItemTitle", "clobTokenIds", "negRisk", "negRiskOther", "createdAt",
             "endDate", "closed", "closedTime", "umaResolutionStatus", "feeType", "description")


def slim_event(e: dict) -> dict:
    """Keep only metadata. ``outcomePrices`` / ``outcomes`` (and any price field) are dropped here, at parse, before
    any record is kept. ``umaResolutionStatus`` survives only as a string."""
    ms = []
    for m in e.get("markets") or []:
        r = {k: m.get(k) for k in _MKT_KEEP if k in m}
        if r.get("description"):
            r["description"] = str(r["description"])[:1500]
        if r.get("umaResolutionStatus") is not None:
            r["umaResolutionStatus"] = str(r["umaResolutionStatus"])
        ms.append(r)
    out = {"id": str(e.get("id")), "title": e.get("title") or "", "negRisk": bool(e.get("negRisk")),
           "negRiskAugmented": e.get("negRiskAugmented"), "startDate": e.get("startDate") or e.get("startTime") or "",
           "description": str(e.get("description") or "")[:1500], "markets": ms}
    for k in _DROP_KEYS:
        assert k not in out
    return out


def guarded_events(path: Path) -> Iterator[dict]:
    """Stream an events ``.jsonl.gz`` (IF-H2 stores ``outcomePrices``) through :func:`slim_event`."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield slim_event(json.loads(line))


def assert_no_outcomes(records: Iterable[dict]) -> None:
    for e in records:
        for m in e.get("markets") or []:
            for k in _DROP_KEYS:
                if k in m:
                    raise AssertionError(f"outcome/price field {k} in a stored CB5-L frame record")


def walk_events(start: datetime, end: datetime, lim, step_days: int = 7, closed_values=(True, False), page: int = 100,
                offset_cap: int = 2000) -> tuple[list[dict], dict]:
    """Walk Gamma ``/events`` by event start-date windows (both ``closed`` states), splitting a window that reaches the
    offset cap. Every record passes :func:`slim_event` immediately."""
    events: dict[str, dict] = {}
    report = {"windows": 0, "split": 0, "capped": 0, "requests": 0, "failed": 0, "failed_windows": []}
    stack = []
    t = start
    while t < end:
        stack.append((t, min(t + timedelta(days=step_days), end)))
        t += timedelta(days=step_days)
    while stack:
        a, b = stack.pop(0)
        capped = False
        failed = False
        got: list[dict] = []
        for closed in closed_values:
            off = 0
            while True:
                params = [("start_date_min", a.strftime("%Y-%m-%dT%H:%M:%SZ")), ("start_date_max", b.strftime("%Y-%m-%dT%H:%M:%SZ")),
                          ("closed", "true" if closed else "false"), ("limit", page), ("offset", off),
                          *[("exclude_tag_id", x) for x in if_h2.EXCLUDE_TAGS]]
                status, data = lim.get(if_h2.GAMMA_EVENTS, params)
                report["requests"] += 1
                if status != 200 or not isinstance(data, list):
                    failed = True  # any non-200 (incl. 400/404/422) or non-list body: this window is not complete
                    break
                got.extend(data)
                if len(data) < page:
                    break
                off += page
                if off >= offset_cap:
                    capped = True
                    break
        if capped and (b - a) > timedelta(hours=3):
            mid = a + (b - a) / 2
            stack[:0] = [(a, mid), (mid, b)]
            report["split"] += 1
            continue
        if failed:
            report["failed"] += 1
            report["failed_windows"].append([a.strftime("%Y-%m-%dT%H:%M:%SZ"), b.strftime("%Y-%m-%dT%H:%M:%SZ")])
        else:
            report["windows"] += 1
        report["capped"] += int(capped)
        for e in got:
            events[str(e.get("id"))] = slim_event(e)
    return list(events.values()), report


# ---- periods -----------------------------------------------------------------------------------------------------------


def _created_date(created_at) -> date | None:
    try:
        ts = pd.Timestamp(created_at)
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        return ts.astimezone(ET).date()
    except (ValueError, TypeError):
        return None


def _last_day(y: int, m: int) -> date:
    return (date(y + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)


def _resolve_year(m: int, y: int | None, created: date | None) -> int | None:
    if y is not None:
        return y
    if created is None:
        return None
    return created.year if m >= created.month else created.year + 1


def parse_period(title: str, created_at=None) -> dict | None:
    """``{"kind", "start", "end"}`` (dates in New York time; ``start``/``end`` None when open) or None. Kinds: month,
    quarter, year (bounded); ``open`` (an opening bucket "Before <period>" / "By <date>": ``start`` None); ``close`` (a
    closing bucket "Not in YYYY", "After <period>", "YYYY or later", "Never": ``start`` and ``end`` None, never part of
    a ``B_D`` because its end is unbounded)."""
    t = " ".join(str(title or "").strip().split())
    created = _created_date(created_at)
    m = RE_MONTH.match(t)
    if m:
        mo = MONTHS[m.group(1).lower()]
        y = _resolve_year(mo, int(m.group(2)) if m.group(2) else None, created)
        return None if y is None else {"kind": "month", "start": date(y, mo, 1), "end": _last_day(y, mo)}
    m = RE_QUARTER.match(t)
    if m:
        q = int(m.group(1))
        mo = 3 * (q - 1) + 1
        y = _resolve_year(mo, int(m.group(2)) if m.group(2) else None, created)
        return None if y is None else {"kind": "quarter", "start": date(y, mo, 1), "end": _last_day(y, mo + 2)}
    m = RE_YEAR.match(t)
    if m:
        y = int(m.group(1))
        return {"kind": "year", "start": date(y, 1, 1), "end": date(y, 12, 31)}
    if t.lower() == "never" or RE_NOT_IN.match(t) or RE_LATER.match(t):
        return {"kind": "close", "start": None, "end": None}
    m = RE_AFTER.match(t)
    if m and parse_period(m.group(1), created_at) is not None:
        return {"kind": "close", "start": None, "end": None}
    m = RE_BEFORE.match(t)
    if m:
        inner = parse_period(m.group(1), created_at)
        if inner is not None and inner["start"] is not None:
            return {"kind": "open", "start": None, "end": inner["start"] - timedelta(days=1)}
        return None
    m = RE_BY.match(t)
    if m:
        d = if_h2.DATE_RE.search(m.group(1))
        if d:
            mo = MONTHS[d.group(1).lower()] if d.group(1).lower() in MONTHS else MONTHS[d.group(1)[:3].lower()]
            y = _resolve_year(mo, int(d.group(3)) if d.group(3) else None, created)
            try:
                return None if y is None else {"kind": "open", "start": None, "end": date(y, mo, int(d.group(2)))}
            except ValueError:
                return None
        inner = parse_period(m.group(1), created_at)
        if inner is not None and inner["end"] is not None:
            return {"kind": "open", "start": None, "end": inner["end"]}
    return None


def tiles(periods: list[dict]) -> bool:
    """The bounded and opening periods tile one contiguous range with no overlap (closing buckets sit outside)."""
    body = [p for p in periods if p["kind"] != "close"]
    if not body:
        return False
    opens = [p for p in body if p["kind"] == "open"]
    bounded = sorted((p for p in body if p["kind"] != "open"), key=lambda p: p["start"])
    if len(opens) > 1:
        return False
    chain = [*opens, *bounded]
    for prev, nxt in zip(chain, chain[1:], strict=False):
        if nxt["start"] is None or prev["end"] is None or nxt["start"] != prev["end"] + timedelta(days=1):
            return False
    return True


def period_end_epoch(d: date) -> float:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=ET).timestamp()


# ---- ladder rungs and bucket events -----------------------------------------------------------------------------------


def rung_deadline_date(question: str, group_item_title: str | None, created_at) -> date | None:
    """Deadline date (New York) of an INC rung: ``if_h2.parse_deadline``; "before D" means by D - 1 day. DEC forms
    ("through D", "until D", "continue ...") and questions without by/before are excluded."""
    q = question or ""
    if RE_DEC_FORM.search(q) or not re.search(r"\b(by|before)\b", q, re.I):
        return None
    ep = if_h2.parse_deadline(group_item_title, q, str(created_at) if created_at else None)
    if ep is None:
        return None
    d = datetime.fromtimestamp(ep, ET).date()
    if RE_BEFORE_DATE.search(q):
        d -= timedelta(days=1)
    return d


def _stem_words(text: str) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    words, nums = cross_venue.tokenize(text)
    raw = frozenset(re.findall(r"[a-z]+", text.lower()))
    return words, nums, raw


def stem_ladder(question: str) -> str:
    return if_h2.stem(question)


def stem_bucket(title: str) -> str:
    t = RE_BUCKET_PHRASE.sub(" ", title or "")
    t = RE_BUCKET_IN.sub(" ", t)
    return if_h2.stem(t)


def resolution_sources(description: str | None) -> frozenset[str]:
    d = description or ""
    out = {u.lower() for u in RE_URL.findall(d)}
    out |= {" ".join(re.findall(r"[a-z0-9]+", s.lower())[:6]) for s in RE_SOURCE.findall(d)}
    return frozenset(x for x in out if x)


def ladder_rungs(events: Iterable[dict]) -> list[dict]:
    """INC rungs: binary non-neg-risk markets with a parsed deadline. Grouped later by (event, stem)."""
    out = []
    for e in events:
        if e.get("negRisk"):
            continue
        for m in e.get("markets") or []:
            toks = if_h2._tokens(m)
            if toks is None or m.get("negRisk"):
                continue
            d = rung_deadline_date(m.get("question") or "", m.get("groupItemTitle"), m.get("createdAt"))
            if d is None:
                continue
            out.append({"market_id": str(m.get("id")), "condition_id": m.get("conditionId") or "", "event_id": str(e["id"]),
                        "question": m.get("question") or "", "D": d, "stem": stem_ladder(m.get("question") or ""),
                        "created_at": m.get("createdAt") or "", "end_date": m.get("endDate") or "", "closed": bool(m.get("closed")),
                        "closed_time": m.get("closedTime") or "", "fee_type": m.get("feeType") or "",
                        "sources": sorted(resolution_sources(m.get("description") or e.get("description")))})
    return out


def ladder_groups(rungs: list[dict]) -> list[dict]:
    """One group per (event, stem); duplicate deadlines keep the lowest numeric market id."""
    by: dict[tuple[str, str], dict[date, dict]] = {}
    for r in rungs:
        slot = by.setdefault((r["event_id"], r["stem"]), {})
        prev = slot.get(r["D"])
        if prev is None or _num_id(r["market_id"]) < _num_id(prev["market_id"]):
            slot[r["D"]] = r
    return [{"group_id": f"{ev}:{hashlib.sha256(st.encode()).hexdigest()[:8]}", "event_id": ev, "stem": st,
             "rungs": [slot[d] for d in sorted(slot)]} for (ev, st), slot in sorted(by.items())]


def _num_id(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        return 1 << 62


def bucket_events(events: Iterable[dict]) -> list[dict]:
    """Neg-risk events, not augmented, no "Other" placeholder, every member parsing to a period, periods tiling."""
    out = []
    for e in events:
        if not e.get("negRisk") or e.get("negRiskAugmented") is True:
            continue
        ms = e.get("markets") or []
        if len(ms) < 2 or any(m.get("negRiskOther") or str(m.get("groupItemTitle") or "").strip().lower() == "other" for m in ms):
            continue
        members, ok = [], True
        for m in ms:
            p = parse_period(m.get("groupItemTitle") or "", m.get("createdAt"))
            if p is None:
                ok = False
                break
            members.append({"market_id": str(m.get("id")), "condition_id": m.get("conditionId") or "", **p,
                            "created_at": m.get("createdAt") or "", "closed": bool(m.get("closed")),
                            "closed_time": m.get("closedTime") or "", "fee_type": m.get("feeType") or "", "end_date": m.get("endDate") or ""})
        if not ok or not tiles(members):
            continue
        kinds = {x["kind"] for x in members if x["kind"] in ("month", "quarter", "year")}
        out.append({"event_id": str(e["id"]), "title": e.get("title") or "", "stem": stem_bucket(e.get("title") or ""),
                    "granularity": next(iter(kinds)) if len(kinds) == 1 else "mixed", "members": members,
                    "sources": sorted(resolution_sources(e.get("description")))})
    return out


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def stems_match(ladder_stem: str, bucket_stem: str) -> float | None:
    """The Jaccard of the stems if rules (a)-(c) hold, else None: Jaccard >= 0.6 with >= 3 shared content tokens,
    identical numbers, no contract-changing word on one side only."""
    lw, ln, lraw = _stem_words(ladder_stem)
    bw, bn, braw = _stem_words(bucket_stem)
    j = jaccard(lw, bw)
    if j < MIN_JACCARD or len(lw & bw) < MIN_SHARED or ln != bn:
        return None
    if (lraw ^ braw) & (cross_venue.CONFLICT | cross_venue.AUDIT_CONFLICT | EXTRA_CONFLICT):
        return None
    return j


def sources_agree(a: Iterable[str], b: Iterable[str]) -> tuple[bool, str]:
    """Rule (d): sources named on both sides must intersect; named on neither is passed and flagged; named on one side
    only excludes (a mismatch)."""
    a, b = set(a), set(b)
    if not a and not b:
        return True, "source_unknown"
    if a and b:
        return bool(a & b), "source_ok" if a & b else "source_mismatch"
    return False, "source_one_sided"


def match_families(groups: list[dict], buckets: list[dict]) -> list[dict]:
    """Mutual-best families with a 0.10 Jaccard margin (ties dropped). A family = (ladder group, bucket event) with at
    least one pair (f, D)."""
    cand: dict[tuple[int, int], tuple[float, str]] = {}
    for gi, g in enumerate(groups):
        gsrc = set().union(*[set(r["sources"]) for r in g["rungs"]]) if g["rungs"] else set()
        for bi, b in enumerate(buckets):
            j = stems_match(g["stem"], b["stem"])
            if j is None:
                continue
            ok, flag = sources_agree(gsrc, b["sources"])
            if ok:
                cand[(gi, bi)] = (j, flag)
    by_g: dict[int, list[tuple[float, int]]] = {}
    by_b: dict[int, list[tuple[float, int]]] = {}
    for (gi, bi), (j, _f) in cand.items():
        by_g.setdefault(gi, []).append((j, bi))
        by_b.setdefault(bi, []).append((j, gi))

    def best(lst: list[tuple[float, int]]) -> int | None:
        lst = sorted(lst, reverse=True)
        if len(lst) > 1 and lst[0][0] - lst[1][0] < MARGIN:
            return None
        return lst[0][1]

    out = []
    for gi, lst in sorted(by_g.items()):
        bi = best(lst)
        if bi is None or best(by_b[bi]) != gi:
            continue
        fam = {"family_id": f"{groups[gi]['group_id']}|{buckets[bi]['event_id']}", "ladder": groups[gi], "bucket": buckets[bi],
               "jaccard": cand[(gi, bi)][0], "source_flag": cand[(gi, bi)][1]}
        if pairs(fam):
            out.append(fam)
    return out


def pairs(f: dict) -> list[dict]:
    """``(f, D)`` pairs: a rung whose D equals the end of a bucket period (New York calendar day) with ``B_D`` = the
    buckets whose period ends on or before D. Rungs with D off a boundary are excluded (counted by the caller)."""
    ends = {m["end"] for m in f["bucket"]["members"] if m["end"] is not None}
    out = []
    for r in f["ladder"]["rungs"]:
        if r["D"] not in ends:
            continue
        bd = [m for m in f["bucket"]["members"] if m["end"] is not None and m["end"] <= r["D"]]
        out.append({"family_id": f["family_id"], "D": r["D"], "rung": r["market_id"], "B": [m["market_id"] for m in bd], "K": len(bd),
                    "granularity": f["bucket"]["granularity"], "bucket_event": f["bucket"]["event_id"]})
    return out


def off_boundary_rungs(f: dict) -> int:
    ends = {m["end"] for m in f["bucket"]["members"] if m["end"] is not None}
    return sum(1 for r in f["ladder"]["rungs"] if r["D"] not in ends)


def grouper_declaration() -> dict:
    """The hashed rule text: tables, patterns, word lists, thresholds (the function sources are hashed separately)."""
    return {"version": GROUPER_VERSION, "months": MONTHS, "jaccard": MIN_JACCARD, "shared": MIN_SHARED, "margin": MARGIN,
            "extra_conflict": sorted(EXTRA_CONFLICT), "conflict": sorted(cross_venue.CONFLICT), "audit_conflict": sorted(cross_venue.AUDIT_CONFLICT),
            "patterns": [p.pattern for p in (RE_MONTH, RE_QUARTER, RE_YEAR, RE_BEFORE, RE_BY, RE_NOT_IN, RE_AFTER, RE_LATER, RE_DEC_FORM,
                                             RE_BEFORE_DATE, RE_BUCKET_PHRASE, RE_BUCKET_IN, RE_URL, RE_SOURCE)],
            "frame": [FRAME_START, FRAME_END], "source_rule": "both named: intersect; neither named: pass+flag; one side only: exclude",
            "inc_only": True, "before_means": "D - 1 day", "boundary_rule": "D equals a bucket period end (New York day)"}


# ---- audit -------------------------------------------------------------------------------------------------------------


def audit_sample(families: list[dict], is_live: dict[str, bool], seed: str, n_live: int = AUDIT_N, n_hist: int = AUDIT_N) -> list[dict]:
    """Seeded random live and historical families, printed with titles, member questions and group item titles (text
    only; no price or outcome field exists in a frame record)."""
    import random

    rng = random.Random(seed)
    live = sorted((f for f in families if is_live.get(f["family_id"])), key=lambda f: f["family_id"])
    hist = sorted((f for f in families if not is_live.get(f["family_id"])), key=lambda f: f["family_id"])
    pick = rng.sample(live, min(n_live, len(live))) + rng.sample(hist, min(n_hist, len(hist)))
    return [{"family_id": f["family_id"], "live": bool(is_live.get(f["family_id"])), "ladder_event": f["ladder"]["event_id"],
             "ladder_questions": [r["question"] for r in f["ladder"]["rungs"]], "ladder_deadlines": [r["D"].isoformat() for r in f["ladder"]["rungs"]],
             "bucket_event": f["bucket"]["event_id"], "bucket_title": f["bucket"]["title"],
             "bucket_members": [m.get("market_id") for m in f["bucket"]["members"]], "source_flag": f["source_flag"]} for f in pick]


def apply_audit(labels: list[bool], previous_failures: int = 0) -> dict:
    """``labels`` = True where the family is genuine (same question, same resolution source and time zone). More than 5%
    not genuine fails the audit. One revision is allowed (``previous_failures`` = 0 -> ``revise_once``); a second failure
    raises :class:`GrouperAuditFailed`."""
    n = len(labels)
    bad = sum(1 for x in labels if not x)
    share = bad / n if n else 1.0
    out = {"n": n, "n_not_genuine": bad, "share_not_genuine": share, "pass": bool(n and share <= AUDIT_MAX_BAD)}
    if out["pass"]:
        out["next"] = "freeze"
    elif previous_failures >= 1:
        raise GrouperAuditFailed(f"grouper audit failed twice ({bad}/{n} not genuine): CB5-L stops")
    else:
        out["next"] = "revise_once"
    return out


# ---- family list ------------------------------------------------------------------------------------------------------


def families_doc(families: list[dict], pool: list[dict], *, version: int, listed_utc: dict[str, str], extra: dict | None = None) -> dict:
    """The frozen family list (``cb5_extract.load_family_list`` format). ``pool`` = every grouper-valid bucket event, so the
    coherence placebo can price mismatched events (role ``pool``)."""
    from .cb5_extract import family_list_sha256

    entries = []
    for f in families:
        ids = sorted({r["market_id"] for r in f["ladder"]["rungs"]} | {m["market_id"] for m in f["bucket"]["members"]})
        entries.append({"family_id": f["family_id"], "role": "family", "listed_utc": listed_utc[f["family_id"]], "market_ids": ids,
                        "ladder_event": f["ladder"]["event_id"], "bucket_event": f["bucket"]["event_id"],
                        "pairs": [{**p, "D": p["D"].isoformat()} for p in pairs(f)]})
    for b in pool:
        entries.append({"family_id": f"P:{b['event_id']}", "role": "pool", "listed_utc": listed_utc[f"P:{b['event_id']}"],
                        "market_ids": sorted(m["market_id"] for m in b["members"]), "granularity": b["granularity"],
                        "periods": [{"market_id": m["market_id"], "kind": m["kind"], "end": m["end"].isoformat() if m["end"] else None}
                                    for m in b["members"]]})
    doc = {"version": version, "grouper": GROUPER_VERSION, "families": entries, **(extra or {})}
    doc["sha256"] = family_list_sha256(doc)
    return doc


# =====================================================================================================================
# Part 2: screen
# =====================================================================================================================


def _flag_on(v) -> bool:
    return str(v).strip().lower() in ("1", "1.0", "true", "t", "yes")


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def _epoch_utc(v) -> float:
    try:
        ts = pd.Timestamp(str(v))
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        return float(ts.timestamp())
    except (ValueError, TypeError):
        return math.nan


def leg_timing_ok(rows: pd.DataFrame, max_spread_s: float = LEG_SPREAD_S) -> bool:
    """The legs' ``received_utc`` span (max - min) is at most ``max_spread_s``; a missing stamp fails."""
    if not len(rows) or "received_utc" not in rows:
        return False
    ts = np.array([_epoch_utc(v) for v in rows["received_utc"]], float)
    return bool(np.isfinite(ts).all() and ts.max() - ts.min() <= max_spread_s)


def _fee(rate: float, a: float) -> float:
    return rate * a * (1.0 - a)


def pair_state(rows: pd.DataFrame, pair: dict, capture_date, regime=cost_regimes.cost_regime) -> dict:
    """The state of ``(f, D)`` at one capture. ``rows`` = the capture's ``cdf`` table indexed by ``market_id``. Eligible
    iff every leg is present, open, accepting orders, two-sided (0 < bid < ask < 1) with ``volume_num`` > 0 and the legs'
    receipt times span at most 5 minutes. ``net_A`` / ``net_B`` include one taker fee per leg."""
    ids = [pair["rung"], *pair["B"]]
    out = {"eligible": False, "reason": None}
    if any(i not in rows.index for i in ids):
        return {**out, "reason": "leg_absent"}
    sub = rows.loc[ids]
    bid = np.array([_num(v) for v in sub["best_bid"]], float)
    ask = np.array([_num(v) for v in sub["best_ask"]], float)
    vol = np.array([_num(v) for v in sub["volume_num"]], float)
    if not (np.isfinite(bid).all() and np.isfinite(ask).all() and (bid > 0).all() and (ask < 1).all() and (bid < ask).all()):
        return {**out, "reason": "not_two_sided"}
    if any(str(c).strip().lower() in ("true", "1") for c in sub.get("closed", [])) or not all(_flag_on(v) for v in sub["accepting_orders"]):
        return {**out, "reason": "not_open"}
    if not (np.isfinite(vol).all() and (vol > 0).all()):
        return {**out, "reason": "no_volume"}
    if not leg_timing_ok(sub):
        return {**out, "reason": "leg_timing"}
    rates = [regime(capture_date, sub["fee_category"].iloc[i] or "other", float(ask[i]))["fee_rate"] for i in range(len(ids))]
    bl, al = bid[0], ask[0]
    bb, ab = bid[1:], ask[1:]
    rb, rl = rates[1:], rates[0]
    fee_a = sum(_fee(rb[j], ab[j]) for j in range(len(ab))) + _fee(rl, 1.0 - bl)
    fee_b = _fee(rl, al) + sum(_fee(rb[j], 1.0 - bb[j]) for j in range(len(bb)))
    net_a = float(bl - ab.sum() - fee_a)
    net_b = float(bb.sum() - al - fee_b)
    mid = (bid + ask) / 2.0
    return {"eligible": True, "reason": None, "net_A": net_a, "net_B": net_b, "cap_A": float(ab.sum() + 1.0 - bl),
            "cap_B": float(al + len(bb) - bb.sum()), "gap_mid": float(mid[0] - mid[1:].sum()),
            "bid": bid, "ask": ask, "ask_size": np.array([_num(v) for v in sub.get("sweep_ask_size_1", [""] * len(ids))], float),
            "bid_size": np.array([_num(v) for v in sub.get("sweep_bid_size_1", [""] * len(ids))], float)}


def _dir_net(st: dict, direction: str) -> float:
    return st["net_A"] if direction == "A" else st["net_B"]


def triggers(captures: list[dict], pair_list: list[dict], regime=cost_regimes.cost_regime) -> pd.DataFrame:
    """Trigger units. ``captures`` = ordered ``{"capture_id", "start_epoch", "rows"}`` (rows indexed by market_id). A trigger at
    c is ``max(net_A, net_B) >= 0.5c``; execution at the next complete capture c' with a start gap in [1.5, 3] h in the same
    direction (ineligible at c' or a gap outside the range -> net 0, kept). A trigger at the last capture has no c' (the sample
    ends) and is censored, not counted. Ties go to direction A."""
    recs = []
    dates = [datetime.fromtimestamp(c["start_epoch"], UTC).date() for c in captures]
    for p in pair_list:
        for i, c in enumerate(captures):
            st = pair_state(c["rows"], p, dates[i], regime)
            if not st["eligible"]:
                continue
            direction = "A" if st["net_A"] >= st["net_B"] else "B"
            if _dir_net(st, direction) < TRIGGER_MIN:
                continue
            nxt = captures[i + 1] if i + 1 < len(captures) else None
            if nxt is None:
                continue  # the sample ends here: a censored trigger, not a trade that failed to execute
            gap_h = (nxt["start_epoch"] - c["start_epoch"]) / 3600.0 if nxt else math.nan
            ex = {"exec_state": "no_next_capture", "net_exec": 0.0, "persist_ok": 0}
            st2 = None
            if nxt is not None and GAP_H[0] <= gap_h <= GAP_H[1]:
                st2 = pair_state(nxt["rows"], p, dates[i + 1], regime)
                if st2["eligible"]:
                    ex = {"exec_state": "executed", "net_exec": float(_dir_net(st2, direction)), "persist_ok": int(_dir_net(st2, direction) > 0)}
                else:
                    ex["exec_state"] = f"ineligible:{st2['reason']}"
            elif nxt is not None:
                ex["exec_state"] = "gap_out_of_range"
            cap = st["cap_A"] if direction == "A" else st["cap_B"]
            d_end = period_end_epoch(p["D"])
            hold_d = max((d_end - (nxt["start_epoch"] if nxt else c["start_epoch"])) / 86400.0, 1.0)
            wk = datetime.fromtimestamp(c["start_epoch"], UTC).isocalendar()
            curve = {}
            for k in PERSIST_STEPS:
                if i + k < len(captures):
                    sk = pair_state(captures[i + k]["rows"], p, dates[i + k], regime)
                    curve[k] = int(sk["eligible"] and _dir_net(sk, direction) > 0)
            recs.append({"family_id": p["family_id"], "D": p["D"], "direction": direction, "K": p["K"], "capture_id": c["capture_id"],
                         "capture_epoch": c["start_epoch"], "net_trigger": float(_dir_net(st, direction)), "capital": float(cap),
                         "hold_days": float(hold_d), "family_week": f"{p['family_id']}|{wk[0]}-W{wk[1]:02d}", "iso_week": f"{wk[0]}-W{wk[1]:02d}",
                         "persist_curve": curve, "exec_capture_id": nxt["capture_id"] if st2 is not None else "", "rung": p["rung"],
                         "B": list(p["B"]), "exec_ask_size": st2["ask_size"] if st2 and st2["eligible"] else None,
                         "exec_bid_size": st2["bid_size"] if st2 and st2["eligible"] else None, **ex})
    return pd.DataFrame(recs)


def execute_next(units: pd.DataFrame) -> pd.DataFrame:
    """The L1 unit table: net after execution at the next capture (``net_exec``), executed or not (0)."""
    return units.assign(net=units["net_exec"].astype(float)) if len(units) else units.assign(net=[])


def persistence_curve(units: pd.DataFrame) -> dict:
    """Share of triggers with same-direction net > 0 at c + k (k in {1, 2, 3, 6} captures); descriptive."""
    out: dict[str, float | None] = {}
    for k in PERSIST_STEPS:
        v = [u.get(k) for u in units["persist_curve"] if k in u]
        out[str(k)] = float(np.mean(v)) if v else None
    return out


def pair_hours(units: pd.DataFrame) -> dict:
    """Each triggered pair-capture counts 2 h; per family-week (descriptive)."""
    if not len(units):
        return {"pair_hours": 0, "family_weeks": 0}
    g = units.groupby("family_week").size() * 2
    return {"pair_hours": int(g.sum()), "family_weeks": int(len(g)), "median_per_family_week": float(g.median())}


def r_ann(units: pd.DataFrame, col: str = "net") -> float:
    """365 * sum(net) / sum(capital * max(hold days, 1))  (CB1 capital-time ratio; hold from c' to D)."""
    den = float((units["capital"] * np.maximum(units["hold_days"], 1.0)).sum())
    return float(365.0 * units[col].sum() / den) if den > 0 else math.nan


def l1_test(units: pd.DataFrame, *, n_boot: int = 2000) -> dict:
    """One-sided mean of ``net`` > 0 per trigger, p = max over family and family x ISO week (small-G rule on both)."""
    if not len(units):
        return {"testable": False, "p": 1.0, "n": 0, "reason": ["no triggers"]}
    ways = {"family": units["family_id"].to_numpy(), "family_week": units["family_week"].to_numpy()}
    out = C3.mean_test(units["net"].to_numpy(float), ways, sign=1, small_g_ways=("family", "family_week"), n_boot=n_boot)
    out["r_ann"] = r_ann(units)
    return out


# ---- coherence placebo ------------------------------------------------------------------------------------------------


def gap_mid_series(captures: list[dict], pair: dict, regime=cost_regimes.cost_regime) -> list[float]:
    """|mid(L_D) - sum mid(B_D)| at every capture where the pair is eligible (descriptive coherence of the identity)."""
    out = []
    for c in captures:
        st = pair_state(c["rows"], pair, datetime.fromtimestamp(c["start_epoch"], UTC).date(), regime)
        if st["eligible"]:
            out.append(abs(st["gap_mid"]))
    return out


def coherence_statistic(per_pair: dict[str, list[float]]) -> float:
    """M = the median over (f, D) of the median over captures of |gap_mid|."""
    meds = [float(np.median(v)) for v in per_pair.values() if len(v)]
    return float(np.median(meds)) if meds else math.nan


def mismatch_pool(pair: dict, pool: list[dict]) -> list[dict]:
    """Non-matched audited bucket events of the same granularity with a period boundary on D (the pair's calendar day)."""
    d = pair["D"]
    out = []
    for b in pool:
        if b["event_id"] == pair["bucket_event"] or b["granularity"] != pair["granularity"]:
            continue
        if any(m["end"] == d for m in b["members"] if m["end"] is not None):
            out.append(b)
    return out


def coherence_placebo(captures: list[dict], pair_list: list[dict], pool: list[dict], *, n_draws: int = PLACEBO_DRAWS,
                      seed: int = SEED_PLACEBO, regime=cost_regimes.cost_regime) -> dict:
    """Mismatched-family coherence placebo. Each draw keeps every rung ``L_D`` and replaces its bucket event by a random
    non-matched bucket event of the same granularity with a boundary on D (buckets ending <= D), under the same eligibility
    and leg-timing rules. (f, D) with no eligible mismatch are excluded from both sides and counted. Fewer than 20 families
    with an eligible mismatch: ``testable`` False (L1 cannot advance). ``advance_ok`` iff at most 1.5% of draws have
    ``M_placebo <= M_matched`` (matched pairs must be more coherent than >= 98.5% of mismatched draws)."""
    rng = np.random.default_rng(seed)
    cand: dict[tuple[str, date], list[dict]] = {}
    matched: dict[tuple[str, date], list[float]] = {}
    cand_series: dict[tuple[str, date], list[list[float]]] = {}
    excluded = 0
    for p in pair_list:
        key = (p["family_id"], p["D"])
        mm = []
        for b in mismatch_pool(p, pool):
            bd = [m["market_id"] for m in b["members"] if m["end"] is not None and m["end"] <= p["D"]]
            if bd:
                mm.append({**p, "B": bd, "K": len(bd), "bucket_event": b["event_id"]})
        series = gap_mid_series(captures, p, regime)
        # only mismatches with an eligible (non-empty) series are candidates, so no draw ever drops a pair that M_matched keeps
        mm_ok = []
        for c in mm:
            ser = gap_mid_series(captures, c, regime)
            if ser:
                mm_ok.append((c, ser))
        if not mm_ok or not series:
            excluded += 1
            continue
        cand[key] = [c for c, _ in mm_ok]
        cand_series[key] = [ser for _, ser in mm_ok]
        matched[key] = series
    fams = {k[0] for k in cand}
    base = {"n_pairs_used": len(cand), "n_families_used": len(fams), "n_pairs_excluded_no_mismatch": excluded, "n_draws": n_draws}
    if len(fams) < PLACEBO_MIN_FAMILIES:
        return {**base, "testable": False, "advance_ok": False, "reason": f"fewer than {PLACEBO_MIN_FAMILIES} families with an eligible mismatch"}
    m_match = coherence_statistic(matched)
    draws = []
    for _ in range(n_draws):
        per = {}
        for key, mm in cand.items():
            per[key] = cand_series[key][int(rng.integers(0, len(mm)))]
        draws.append(coherence_statistic(per))
    dv = np.array([x for x in draws if np.isfinite(x)], float)
    rate = float(np.mean(dv <= m_match)) if len(dv) else 1.0
    return {**base, "testable": bool(len(dv)), "M_matched": m_match, "M_placebo_mean": float(dv.mean()) if len(dv) else math.nan,
            "rate_as_coherent": rate, "advance_ok": bool(len(dv) and rate <= PLACEBO_MAX_ADVANCE_RATE), "draws": [float(x) for x in dv]}


# ---- gates ------------------------------------------------------------------------------------------------------------


def wilson_upper(k: int, n: int, z: float = Z95) -> float:
    if n <= 0:
        return 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0))
    return float(min(1.0, (centre + half) / (1 + z * z / n)))


OUTCOME_FAILED = -1.0  # fetch sentinel: the outcome request failed (distinct from NaN = not closed / not decisive)


def r_inc(families: list[dict], outcomes: dict[str, float]) -> dict:
    """Family-level inconsistent-resolution rate. ``families`` = ``{"family_id", "pairs": [{"rung", "B": [...]}]}``;
    ``outcomes`` = YES payout (0/1, NaN unresolved) per market id. A pair is inconsistent when the rung outcome differs
    from the OR of the bucket outcomes over B_D. A family counts only when every leg of every pair is resolved. Fewer than
    30 resolved families: ``unknown`` (blocks any L1 advance)."""
    n_res = n_bad = pairs_n = pairs_bad = n_failed = 0
    for f in families:
        ok, bad = True, False
        for p in f["pairs"]:
            legs = [outcomes.get(p["rung"], math.nan), *[outcomes.get(b, math.nan) for b in p["B"]]]
            if any(x == OUTCOME_FAILED for x in legs):
                n_failed += 1
            if not all(x in (0.0, 1.0) for x in legs):
                ok = False
                break
            incons = (legs[0] == 1.0) != any(x == 1.0 for x in legs[1:])
            pairs_n += 1
            pairs_bad += int(incons)
            bad = bad or incons
        if ok and f["pairs"]:
            n_res += 1
            n_bad += int(bad)
    out = {"n_resolved_families": n_res, "n_inconsistent_families": n_bad, "pair_level": {"n": pairs_n, "n_inconsistent": pairs_bad}}
    if n_failed:
        return {**out, "status": "blocked_fetch_failed", "n_failed_pairs": n_failed, "r_inc": None, "r_inc_plus": None}
    if n_res < RINC_MIN_FAMILIES:
        return {**out, "status": "unknown", "r_inc": None, "r_inc_plus": None}
    return {**out, "status": "known", "r_inc": n_bad / n_res, "r_inc_plus": wilson_upper(n_bad, n_res)}


def divergence_gate(mean_net: float, rinc: dict) -> dict:
    """L1 may advance only if ``mean(net') - 1.0 * r_inc_plus > 0`` (every inconsistent resolution costed as a full
    one-unit loss). An unknown ``r_inc`` blocks."""
    if rinc.get("status") != "known":
        return {"status": "blocked_unknown", "ok": False}
    v = float(mean_net) - 1.0 * rinc["r_inc_plus"]
    return {"status": "pass" if v > 0 else "fail", "ok": bool(v > 0), "net_minus_cost": v}


def payoff_short(direction: str, K: int, rung_y: float, bucket_y: list[float]) -> bool:
    """True when the realised payoff of the paired position falls short of the promised one (1 for A, K for B)."""
    if direction == "A":
        pay, promised = sum(bucket_y) + (1.0 - rung_y), 1.0
    else:
        pay, promised = rung_y + sum(1.0 - y for y in bucket_y), float(K)
    return bool(pay < promised - 1e-9)


def realised_payoff_gate(units: pd.DataFrame, outcomes: dict[str, float]) -> dict:
    """Share of determined triggered pairs (all legs resolved) whose payoff is short, at most 2%. Fewer than 30 determined
    pairs: ``inconclusive`` (blocks crediting; never counts as met)."""
    det = short = 0
    for _, u in units.iterrows():
        legs = [outcomes.get(u["rung"], math.nan), *[outcomes.get(b, math.nan) for b in u["B"]]]
        if not all(x in (0.0, 1.0) for x in legs):
            continue
        det += 1
        short += int(payoff_short(u["direction"], int(u["K"]), legs[0], legs[1:]))
    if det < PAYOFF_MIN_DETERMINED:
        return {"status": "inconclusive", "ok": False, "n_determined": det, "n_short": short}
    share = short / det
    return {"status": "pass" if share <= PAYOFF_MAX_SHORT else "fail", "ok": bool(share <= PAYOFF_MAX_SHORT), "n_determined": det, "n_short": short, "share_short": share}


def depth_check(units: pd.DataFrame, min_size: float = DEPTH_MIN_SIZE) -> dict:
    """Recompute the L1 mean on triggers whose executed legs all show size >= 5 at the next pass; it must agree in sign with
    the full mean; fewer than 30 family clusters: ``inconclusive`` (blocks crediting)."""
    if not len(units):
        return {"status": "inconclusive", "ok": False, "n": 0, "n_families": 0}

    def deep(u) -> bool:
        a, b = u["exec_ask_size"], u["exec_bid_size"]
        if a is None or b is None or u["exec_state"] != "executed":
            return False
        need = [a[1:].min(), b[0]] if u["direction"] == "A" else [a[0], b[1:].min()]
        return bool(np.isfinite(need).all() and min(need) >= min_size)

    sub = units[[deep(u) for _, u in units.iterrows()]]
    fam = int(sub["family_id"].nunique()) if len(sub) else 0
    if fam < 30:
        return {"status": "inconclusive", "ok": False, "n": int(len(sub)), "n_families": fam}
    agree = C3.sign_agree(float(sub["net"].mean()), float(units["net"].mean()))
    return {"status": "pass" if agree else "fail", "ok": bool(agree), "n": int(len(sub)), "n_families": fam, "mean_deep": float(sub["net"].mean())}


def g59_gate(n_families_with_eligible: int) -> dict:
    ok = n_families_with_eligible >= G59_MIN_FAMILIES
    return {"ok": ok, "n_families": int(n_families_with_eligible), "status": "pass" if ok else f"not testable: {n_families_with_eligible} families"}


def credit_status(stage: str, *, advance_core: bool, placebo: dict, rinc: dict, divergence: dict, payoff: dict, depth: dict) -> dict:
    """Combine the L1 gates. Stage 1: an unknown r_inc or an untestable/failed placebo blocks the advance. Stage 2: an
    inconclusive payoff or depth gate leaves a pass 'pending, not credited'. An unknown or inconclusive gate is never met."""
    blockers = []
    if not placebo.get("advance_ok"):
        blockers.append("coherence_placebo")
    if rinc.get("status") != "known":
        blockers.append("r_inc_unknown")
    if not divergence.get("ok"):
        blockers.append("divergence")
    out = {"blockers": blockers}
    if stage == "stage1":
        out["advance"] = bool(advance_core and not blockers)
        return out
    pending = [n for n, g in (("payoff", payoff), ("depth", depth)) if g.get("status") == "inconclusive"]
    failed = [n for n, g in (("payoff", payoff), ("depth", depth)) if g.get("status") == "fail"]
    out["pending"], out["failed"] = pending, failed
    out["passed"] = bool(advance_core and not blockers and not failed)
    out["credited"] = bool(out["passed"] and not pending)
    out["family_status"] = "credited" if out["credited"] else ("passed, pending verification, not credited" if out["passed"] else "not passed")
    return out


def eligible_pair_captures(captures: list[dict], pair_list: list[dict], regime=cost_regimes.cost_regime) -> dict:
    """L-iii / G59 input (eligibility only; no gap, net or trigger is computed): eligible pair-captures per family."""
    per: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for p in pair_list:
        for c in captures:
            st = pair_state_eligibility(c["rows"], p)
            if st is None:
                per[p["family_id"]] = per.get(p["family_id"], 0) + 1
            else:
                reasons[st] = reasons.get(st, 0) + 1
    fams = {k: v for k, v in per.items() if v > 0}
    return {"per_family": fams, "n_families": len(fams), "n_pair_captures": int(sum(fams.values())), "ineligible_reasons": reasons}


def pair_state_eligibility(rows: pd.DataFrame, pair: dict) -> str | None:
    """None when every leg is present, open, accepting, two-sided with volume and the legs' receipt times span <= 5 min; else the
    reason. Reads no price level other than the two-sidedness test."""
    ids = [pair["rung"], *pair["B"]]
    if any(i not in rows.index for i in ids):
        return "leg_absent"
    sub = rows.loc[ids]
    bid = np.array([_num(v) for v in sub["best_bid"]], float)
    ask = np.array([_num(v) for v in sub["best_ask"]], float)
    vol = np.array([_num(v) for v in sub["volume_num"]], float)
    if not (np.isfinite(bid).all() and np.isfinite(ask).all() and (bid > 0).all() and (ask < 1).all() and (bid < ask).all()):
        return "not_two_sided"
    if any(str(c).strip().lower() in ("true", "1") for c in sub.get("closed", [])) or not all(_flag_on(v) for v in sub["accepting_orders"]):
        return "not_open"
    if not (np.isfinite(vol).all() and (vol > 0).all()):
        return "no_volume"
    return None if leg_timing_ok(sub) else "leg_timing"
