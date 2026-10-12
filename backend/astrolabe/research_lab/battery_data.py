"""Hypothesis battery 1 (HB1) data helpers: event metadata, sibling price series, metadata rules.

EXPLORATORY_HISTORICAL, development only (``docs/research_lab/HYPOTHESIS_BATTERY_1.md``). Nothing
here is prospective evidence or an edge claim.

* ``fetch_event_meta``: public Gamma ``/events?id=..`` for the events of the h2_main sample. Only
  creation-time text and structure are kept (title, question, groupItemTitle, slug, tags, neg-risk
  flags, member list, scheduled dates, outcome-0 token). Sibling outcomes (``outcomePrices``) are
  deliberately NOT stored.
* ``sibling_targets`` / ``fetch_sibling_prices``: CLOB ``prices-history`` (10-minute fidelity,
  <= 14-day windows) for the other members of neg-risk events (<= ``NR_MAX_MEMBERS`` members) and
  of deadline ladders that contain a sampled, traded market, only over the span of that market's
  panel origins (plus 8 days of look-back). Paced by ``history_backfill.Limiter`` and yielding to
  the live collector.
* ``asym_class``: the creation-known topic rule of ``history_topics`` (no tuning, no outcomes).
* ``parse_deadline``: deterministic "by <date>" parser for ladder rungs (question / groupItemTitle).
"""

from __future__ import annotations

import gzip
import json
import math
import re
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import history_backfill as hb
from . import history_topics

GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
META_VERSION = "hb1-meta-v1"
EVENT_BATCH = 20
NR_MAX_MEMBERS = 25  # neg-risk events with more members are not fetched (declared cap)
LADDER_MAX_RUNGS = 12
LOOKBACK_S = 8 * 86400
SLACK_S = 86400

_MON = {
    m: i + 1
    for i, m in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    )
}
_DATE_RE = re.compile(
    r"\b(?:by|before)\s+(?:the\s+end\s+of\s+)?(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?(?:\s+(\d{1,2})(?:st|nd|rd|th)?)?(?:,?\s*(\d{4}))?",
    re.I,
)
_GIT_RE = re.compile(
    r"^\s*(?:by\s+|before\s+)?(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
    r"(?:\s+(\d{1,2})(?:st|nd|rd|th)?)?(?:,?\s*(\d{4}))?\s*\??\s*$",
    re.I,
)
_MONTH_DAYS = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _batches(xs: list, n: int) -> Iterable[list]:
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def _token0(raw) -> str | None:
    try:
        toks = json.loads(raw) if isinstance(raw, str) else raw
        return str(toks[0]) if toks else None
    except (TypeError, ValueError, IndexError):
        return None


def _epoch(v) -> float:
    return hb._epoch(v)


def slim_event(e: dict) -> dict:
    """Creation-time structure of one Gamma event (no outcomes, no end-of-life volumes)."""
    tags = [
        str(t.get("label") or t.get("slug") or "")
        for t in (e.get("tags") or [])
        if isinstance(t, dict)
    ]
    mk = []
    for m in e.get("markets") or []:
        mk.append(
            {
                "market_id": str(m.get("id")),
                "question": m.get("question") or "",
                "group_item_title": m.get("groupItemTitle") or "",
                "slug": m.get("slug") or "",
                "neg_risk": bool(m.get("negRisk")),
                "neg_risk_other": bool(m.get("negRiskOther")),
                "token0": _token0(m.get("clobTokenIds")),
                "created_epoch": _epoch(m.get("createdAt")),
                "start_epoch": _epoch(m.get("startDate")),
                "end_epoch": _epoch(m.get("endDate")),
                "close_epoch": _epoch(m.get("closedTime")),
                "closed": bool(m.get("closed")),
            }
        )
    return {
        "event_id": str(e.get("id")),
        "title": e.get("title") or "",
        "slug": e.get("slug") or "",
        "neg_risk": bool(e.get("negRisk")),
        "enable_neg_risk": bool(e.get("enableNegRisk")),
        "neg_risk_augmented": bool(e.get("negRiskAugmented")),
        "tags": tags,
        "series_slug": e.get("seriesSlug") or "",
        "n_markets": len(mk),
        "markets": mk,
        "meta_version": META_VERSION,
    }


def fetch_event_meta(lim: hb.Limiter, event_ids: list[str], out_path: Path) -> dict:
    """Resumable: appends slimmed events to ``out_path`` (jsonl.gz rewritten at the end)."""
    out_path = Path(out_path)
    have: dict[str, dict] = {}
    if out_path.exists():
        for e in load_jsonl_gz(out_path):
            have[e["event_id"]] = e
    todo = [e for e in dict.fromkeys(event_ids) if e and e not in have]
    missing = []
    for chunk in _batches(todo, EVENT_BATCH):
        status, data = lim.get(GAMMA_EVENTS, [("id", x) for x in chunk])
        if status != 200 or not isinstance(data, list):
            missing += chunk
            continue
        got = {str(e.get("id")) for e in data}
        for e in data:
            have[str(e.get("id"))] = slim_event(e)
        missing += [x for x in chunk if x not in got]
    save_jsonl_gz(out_path, have.values())
    return {
        "events": len(have),
        "requested": len(todo),
        "missing": missing,
        "requests": lim.requests,
    }


def save_jsonl_gz(path: Path, rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, default=float) + "\n")
    tmp.replace(path)


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# --- metadata rules (no prices, no outcomes) ----------------------------------------------------


def asym_class(question: str, event_title: str, slug: str, fee_category: str) -> str:
    """``asymmetric`` (decision-asymmetric topics: politics, geopolitics, awards, corporate,
    macro), ``public`` (sports, crypto, weather) or ``other`` (mentions and unmatched), using the
    creation-known rule of ``history_topics`` without modification."""
    topic = history_topics.topic_of(
        question or "", event_title or "", slug or "", str(fee_category or "").split(":")[0]
    )
    if history_topics.is_asymmetric(topic):
        return "asymmetric"
    if topic in ("sports", "crypto", "weather"):
        return "public"
    return "other"


def _year_for(month: int, ref_epoch: float) -> int:
    ref = datetime.fromtimestamp(ref_epoch, UTC) if not math.isnan(ref_epoch) else None
    return ref.year if ref is not None else 2026


def parse_deadline(question: str, group_item_title: str, ref_epoch: float) -> float:
    """Deadline (epoch, end of that UTC day) of a "by <month> [day][, year]" rung, else NaN.

    ``groupItemTitle`` (e.g. "March 31", "by June 30, 2026") is tried first, then the question
    ("... by March 31?"). A missing day means the month's last day; a missing year takes the year of
    the market's own scheduled end (``ref_epoch``), or of the year after when that would put the
    deadline more than 31 days after the scheduled end."""
    for text, rx in ((group_item_title, _GIT_RE), (question, _DATE_RE)):
        if not text:
            continue
        m = rx.search(text)
        if not m:
            continue
        mon = _MON[m.group(1)[:3].lower()]
        day = int(m.group(2)) if m.group(2) else _MONTH_DAYS[mon - 1]
        year = int(m.group(3)) if m.group(3) else _year_for(mon, ref_epoch)
        if mon == 2 and day == 29 and year % 4:
            day = 28
        try:
            d = datetime(year, mon, min(day, _MONTH_DAYS[mon - 1]), 23, 59, 59, tzinfo=UTC)
        except ValueError:
            return float("nan")
        ep = d.timestamp()
        if not m.group(3) and not math.isnan(ref_epoch) and ep > ref_epoch + 31 * 86400:
            try:
                ep = d.replace(year=year - 1).timestamp()
            except ValueError:
                pass
        return ep
    return float("nan")


def ladder_stem(question: str) -> str:
    """Question text with the deadline phrase removed (ladder rungs share a stem)."""
    q = _DATE_RE.sub(" ", question or "").lower()
    q = re.sub(r"[^a-z0-9 ]+", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def event_ladders(ev: dict) -> list[list[dict]]:
    """Deadline ladders inside one event: >= 2 markets with a parsed deadline and a common stem,
    ordered by deadline (distinct deadlines only). Neg-risk events are never ladders: their dated
    members are mutually exclusive buckets, not cumulative "by" contracts."""
    if ev.get("neg_risk"):
        return []
    groups: dict[str, list[dict]] = {}
    for m in ev["markets"]:
        if m.get("neg_risk_other") or not m.get("token0"):
            continue
        d = parse_deadline(m["question"], m["group_item_title"], m["end_epoch"])
        if math.isnan(d):
            continue
        groups.setdefault(ladder_stem(m["question"]), []).append({**m, "deadline": d})
    out = []
    for g in groups.values():
        g = sorted(g, key=lambda r: r["deadline"])
        dedup, seen = [], set()
        for r in g:
            if r["deadline"] in seen:
                continue
            seen.add(r["deadline"])
            dedup.append(r)
        if 2 <= len(dedup) <= LADDER_MAX_RUNGS:
            out.append(dedup)
    return out


def market_meta_table(sample: pd.DataFrame, events: dict[str, dict]) -> pd.DataFrame:
    """One row per sampled market: text, asymmetry class, neg-risk membership size, ladder rank."""
    rows = []
    for r in sample.to_dict("records"):
        ev = events.get(str(r["event_id"]))
        mk = None
        if ev is not None:
            mk = next((m for m in ev["markets"] if m["market_id"] == str(r["market_id"])), None)
        q = mk["question"] if mk else ""
        git = mk["group_item_title"] if mk else ""
        title = ev["title"] if ev else ""
        slug = mk["slug"] if mk else ""
        lad_pos, lad_n, lad_id = np.nan, 0, ""
        if ev is not None:
            for li, lad in enumerate(event_ladders(ev)):
                ids = [x["market_id"] for x in lad]
                if str(r["market_id"]) in ids:
                    lad_pos, lad_n = ids.index(str(r["market_id"])), len(ids)
                    lad_id = f"{ev['event_id']}:{li}"
        rows.append(
            {
                "market_id": str(r["market_id"]),
                "event_id": str(r["event_id"]),
                "has_meta": ev is not None and mk is not None,
                "asym_class": asym_class(q, title, slug, r.get("fee_category", "")),
                "topic": history_topics.topic_of(
                    q, title, slug, str(r.get("fee_category", "")).split(":")[0]
                ),
                "event_neg_risk": bool(ev and ev["neg_risk"]),
                "event_n_markets": ev["n_markets"] if ev else np.nan,
                "neg_risk_augmented": bool(ev and ev["neg_risk_augmented"]),
                "ladder_id": lad_id,
                "ladder_pos": lad_pos,
                "ladder_n": lad_n,
                "question_len": len(q),
                "group_item_title": git,
            }
        )
    return pd.DataFrame(rows)


# --- sibling price series -------------------------------------------------------------------------


def sibling_targets(
    meta: pd.DataFrame, events: dict[str, dict], spans: dict[str, tuple[float, float]]
) -> list[dict]:
    """Sibling tokens to fetch: every other member of (a) neg-risk events with 2..NR_MAX_MEMBERS
    members and (b) deadline ladders, that contain a sampled market with traded panel origins
    (``spans``: market_id -> (first, last) traded origin). One fetch span per sibling (union over
    the sampled markets of its event), clipped to the sibling's own listed life."""
    need: dict[str, dict] = {}
    for r in meta.to_dict("records"):
        mid = r["market_id"]
        if mid not in spans:
            continue
        ev = events.get(r["event_id"])
        if ev is None:
            continue
        members: list[dict] = []
        reason = []
        if ev["neg_risk"] and 2 <= ev["n_markets"] <= NR_MAX_MEMBERS:
            members += ev["markets"]
            reason.append("neg_risk")
        if r["ladder_id"]:
            li = int(r["ladder_id"].split(":")[1])
            members += event_ladders(ev)[li]
            reason.append("ladder")
        a, b = spans[mid]
        for m in members:
            if m["market_id"] == mid or not m.get("token0"):
                continue
            lo, hi = a - LOOKBACK_S, b + SLACK_S
            c0 = m["created_epoch"] if not math.isnan(m["created_epoch"]) else m["start_epoch"]
            if not math.isnan(c0):
                lo = max(lo, c0 - 3600)
            if not math.isnan(m["close_epoch"]):
                hi = min(hi, m["close_epoch"] + SLACK_S)
            if hi <= lo:
                continue
            cur = need.get(m["token0"])
            if cur is None:
                need[m["token0"]] = {
                    "token0": m["token0"],
                    "market_id": m["market_id"],
                    "event_id": ev["event_id"],
                    "lo": lo,
                    "hi": hi,
                    "reason": sorted(set(reason)),
                }
            else:
                cur["lo"], cur["hi"] = min(cur["lo"], lo), max(cur["hi"], hi)
                cur["reason"] = sorted(set(cur["reason"]) | set(reason))
    return sorted(need.values(), key=lambda d: (d["event_id"], d["market_id"]))


def fetch_sibling_prices(
    lim: hb.Limiter, targets: list[dict], out_dir: Path, max_requests: int, log=print
) -> dict:
    """Resumable: one ``<market_id>.csv.gz`` (t,p) per sibling under ``out_dir``; progress lines
    in ``out_dir/progress.jsonl``. Stops cleanly at ``max_requests``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prog_path = out_dir / "progress.jsonl"
    done = set()
    if prog_path.exists():
        for line in prog_path.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["market_id"])
    n_req0 = lim.requests
    stopped = False
    t0 = time.time()
    for i, tg in enumerate(targets):
        if tg["market_id"] in done:
            continue
        if lim.requests - n_req0 >= max_requests:
            stopped = True
            break
        pts, n = hb.fetch_prices(lim, tg["token0"], int(tg["lo"]), int(tg["hi"]))
        df = pd.DataFrame(pts, columns=["t", "p"])
        df.to_csv(out_dir / f"{tg['market_id']}.csv.gz", index=False, compression="gzip")
        with open(prog_path, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "market_id": tg["market_id"],
                        "event_id": tg["event_id"],
                        "points": len(df),
                        "requests": n,
                        "lo": tg["lo"],
                        "hi": tg["hi"],
                        "reason": tg["reason"],
                        "utc": hb.utc_iso(),
                    }
                )
                + "\n"
            )
        done.add(tg["market_id"])
        if i % 100 == 0:
            log(
                f"siblings {len(done)}/{len(targets)} requests {lim.requests - n_req0} "
                f"({time.time() - t0:.0f}s)"
            )
    return {
        "targets": len(targets),
        "done": len(done),
        "requests": lim.requests - n_req0,
        "stopped_at_cap": stopped,
        "yielded_s": lim.yielded_s,
    }
