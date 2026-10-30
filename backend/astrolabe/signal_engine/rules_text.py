# ruff: noqa: E501
"""Rule-text columns from the ``gamma_rules`` stream (aux family ``rules``, DESIGN_V1 section 41; CH267 + CH239).

The stream (``research_lab/streams/gamma_rules.py``) is a change-only log: each UTC day file holds ``row`` lines (the
full rule-bearing fields of a key, written when new or edited), ``hash`` checkpoint lines (no text) and one ``poll`` line
per hourly slot, written after that slot's rows. A ``m:<market id>`` row is **known at a capture** iff the same file holds
a ``poll`` line of the row's slot with ``ok`` true and ``finished_utc`` at or before the capture start. The market's
text at the capture is its last known row (all day files from the stream's first, because unchanged text is not
rewritten). Event (``e:``) rows are not read. The text is parsed and dropped; no price, outcome or wallet field exists
in the stream.

Nothing here reads an outcome. The lexicons are pinned by this file's sha256 in each table's metadata.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

RULES_VERSION = "se-aux-rules-v1"
# CH269's placeholder lexicon (census_map_ch269.py), copied verbatim so the engine's class levels match the map's counts
SCHEDULED_RE = re.compile(r"\b(scheduled|fomc|federal reserve|cpi|consumer price index|jobs report|nonfarm|unemployment rate|gdp|earnings|box office|election|vote|referendum|certified|official (?:results?|data|release|figures?)|will be (?:released|published|announced)|press release)\b")
BARRIER_RE = re.compile(r"\b(at any point|at any time|any time|reach(?:es)?|hits?|touch(?:es)?|dips?|exceeds?|before|by (?:january|february|march|april|may|june|july|august|september|october|november|december|the end of))\b")
# CH267's third class (consensus of credible reporting); pinned here, not in the map
CONSENSUS_RE = re.compile(r"\b(consensus of credible reporting|credible report(?:ing|s)|credible sources?)\b")
# CH239's inclusive-threshold wording and a numeric strike in the question
INCLUSIVE_RE = re.compile(r"\b(or (?:more|higher|greater|above|less|lower|fewer|below)|at least|at most|or equal)\b")
NUMERIC_RE = re.compile(r"(\$\s?\d|\d\s?%|\d{1,3}(?:,\d{3})+)")
# added after the census's hand audit (texts only, no outcome): BARRIER_RE fires on boilerplate ("if at any point it
# becomes impossible"), "exceeds" and "before" in on-date and season rules (3 of 13 sampled barrier rows were deadline
# questions). The strict deadline wording: "by / before <month | year | quarter | the end of>" in the question, or an
# occurrence window "between (the) market creation / creation of this market and" in the description
_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
OCCUR_Q_RE = re.compile(rf"\b(?:by|before) (?:the end of |end of )?(?:{_MONTHS}|20\d\d|q[1-4]\b)")
OCCUR_D_RE = re.compile(r"\bbetween (?:the )?(?:market(?:'s)? creation|creation of (?:this|the) market)\b")
URL_HOST_RE = re.compile(r"https?://(?:www\.)?([a-z0-9.-]+)")
N_HOSTS_CAP = 5
# the stream's first day file on the host (2026-10-20). Every day file from it to the capture's day must be present: a
# missing file would silently turn known text into rc_has 0 or older text (review 2026-10-30), so the build refuses
RULES_FIRST_DAY = "20261020"
RULES_COLUMNS = ["rc_has", "cl_sched", "cl_barrier", "cl_consensus", "rc_inclusive", "rc_numeric", "rc_n_hosts", "rc_log_len",
                 "rc_occur_by"]
TEXT_COLUMNS = RULES_COLUMNS[1:]  # NaN for a market with no known row


def parse_rule(data: dict) -> list[float]:
    """The TEXT_COLUMNS of one ``m:`` row's data (pure)."""
    q = str(data.get("question") or "")
    d = str(data.get("description") or "")
    src = str(data.get("resolutionSource") or "")
    t = " ".join((q, d, src)).lower()
    hosts = {h.rstrip(".") for h in URL_HOST_RE.findall(" ".join((d, src)).lower())}
    return [float(bool(SCHEDULED_RE.search(t))), float(bool(BARRIER_RE.search(t))), float(bool(CONSENSUS_RE.search(t))),
            float(bool(INCLUSIVE_RE.search(t))), float(bool(NUMERIC_RE.search(q))), float(min(len(hosts), N_HOSTS_CAP)),
            math.log1p(len(d)), float(bool(OCCUR_Q_RE.search(q.lower()) or OCCUR_D_RE.search(d.lower())))]


class RulesGap(Exception):
    """A day file between the stream's first day and the capture's day is missing (restore it from the releases)."""


_MEMO: dict = {}  # path -> (size, mtime_ns, parsed); day files are append-only, so a same-size file is unchanged


def read_day_file(p: Path, cache_dir: Path | None = None) -> dict:
    """{"rows": [(slot, market_id, cols)], "polls": {slot: finished_ts}} of one day file (memoised by size and mtime)."""
    st = p.stat()
    hit = _MEMO.get(str(p))
    if hit is not None and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
        return hit[2]
    from . import stream_cache

    out = stream_cache.cached_parse(cache_dir, "rules", p, st, code_sha256(), _parse_day_file)
    _MEMO[str(p)] = (st.st_size, st.st_mtime_ns, out)
    return out


def _parse_day_file(p: Path) -> dict:
    from . import store as S

    rows, polls = [], {}
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if '"kind":"hash"' in line:  # checkpoint lines carry no text
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue  # a torn last line of a file being appended
            k = r.get("kind")
            if k == "poll":
                if r.get("ok") and r.get("slot"):
                    ts = S.epoch(r.get("finished_utc"))
                    if math.isfinite(ts):
                        polls[r["slot"]] = ts
            elif k == "row" and str(r.get("key", "")).startswith("m:") and isinstance(r.get("data"), dict):
                try:
                    mid = int(r["key"][2:])
                except ValueError:
                    continue
                rows.append((r.get("slot"), mid, parse_rule(r["data"])))
    return {"rows": rows, "polls": polls}


def rules_at(root: Path, cap_start: float, cache_dir: Path | None = None) -> dict:
    """{"known": {market_id: cols} known at ``cap_start``, "first_poll": ts or None, "files": [...], "last_slot": ...}."""
    root = Path(root)
    known: dict[int, list[float]] = {}
    first_poll, last_slot, files = None, None, []
    if not root.exists():
        return {"known": known, "first_poll": None, "files": files, "last_slot": None}
    from . import store as S

    cap_day = S.day_of(cap_start).replace("-", "")
    have = {p.stem for p in root.glob("*.jsonl")}
    if cap_day >= RULES_FIRST_DAY:
        from datetime import UTC, datetime, timedelta

        d, end = datetime.strptime(RULES_FIRST_DAY, "%Y%m%d").replace(tzinfo=UTC), datetime.strptime(cap_day, "%Y%m%d").replace(tzinfo=UTC)
        gaps = []
        while d <= end:
            if d.strftime("%Y%m%d") not in have:
                gaps.append(d.strftime("%Y%m%d"))
            d += timedelta(days=1)
        # the capture's own day may not have a file yet only if no poll of that day has run (before ~00:50Z)
        if gaps and gaps != [cap_day]:
            raise RulesGap(f"gamma_rules day files missing: {gaps[:5]}{'...' if len(gaps) > 5 else ''}")
    for p in sorted(root.glob("*.jsonl")):
        if p.stem > cap_day:
            break
        day = read_day_file(p, cache_dir)
        ok = {s for s, ts in day["polls"].items() if ts <= cap_start}
        if not ok:
            continue
        files.append(p.name)
        first_poll = min(first_poll or math.inf, min(day["polls"][s] for s in ok))
        last_slot = max(ok) if last_slot is None else max(last_slot, max(ok))
        for slot, mid, cols in day["rows"]:  # file order: a later row of the same market replaces the earlier one
            if slot in ok:
                known[mid] = cols
    return {"known": known, "first_poll": first_poll, "files": files, "last_slot": last_slot}


def code_sha256() -> str:
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
