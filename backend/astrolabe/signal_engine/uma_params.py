# ruff: noqa: E501
"""Desk-set dispute parameters from the ``gamma_rules`` stream (aux family ``umaparams``, DESIGN_V1 section 42; CH207).

Same stream and clock as ``rules_text`` (section 41): a ``m:<market id>`` row is **known at a capture** iff the same day
file holds a ``poll`` line of the row's slot with ``ok`` true and ``finished_utc`` at or before the capture start, and
the market's value at the capture is its last known row over all day files from ``RULES_FIRST_DAY``. Only the static UMA
fields are read (``umaBond``, ``umaReward``, ``customLiveness``, ``hasReviewedDates``, ``fallbackResolutionType``,
``resolvedBy``). The row's ``endDate`` / ``startDate`` are **not** read (hours-to-end belongs to the engine's
market_state and to the embargoed ``tte`` family). No price, outcome or wallet field exists in the stream.

``rules_text.py`` is left unchanged so se28's tables keep their pinned sha; this file has its own reader and sha.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .rules_text import RULES_FIRST_DAY, RulesGap

UMA_VERSION = "se-aux-umaparams-v1"
# up_unreviewed (hasReviewedDates false) was defined in section 42 and dropped by its census: 0 of 18,135 covered rows
UMA_COLUMNS = ["up_has", "up_log_bond", "up_log_reward", "up_live_custom", "up_fallback", "up_resolver_top"]
VALUE_COLUMNS = UMA_COLUMNS[1:]  # NaN for a market with no known row
# the resolvedBy address with the most covered rows in the section-42 census (9,096 of 18,135; counts only; pinned
# after that run, before any table existed)
RESOLVER_TOP = "0x69c47de9d4d3dad79590d61b9e05918e03775f24"
_ABSENT = {"", "null"}  # an empty string field is absent (NaN); the literal "none" is a value only for the fallback type


def _num(v) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) and x >= 0 else math.nan


def parse_uma(data: dict) -> list[float]:
    """The VALUE_COLUMNS of one ``m:`` row's data (pure). A missing or malformed field is NaN, never filled."""
    bond, reward, live = _num(data.get("umaBond")), _num(data.get("umaReward")), _num(data.get("customLiveness"))
    fb = data.get("fallbackResolutionType")
    rb = data.get("resolvedBy")
    return [math.log1p(bond), math.log1p(reward),
            float(live > 0) if math.isfinite(live) else math.nan,
            float(fb.strip().lower() != "none") if isinstance(fb, str) and fb.strip().lower() not in _ABSENT else math.nan,
            float(rb.lower() == RESOLVER_TOP.lower()) if isinstance(rb, str) and rb.strip().lower() not in _ABSENT | {"none"} else math.nan]


_MEMO: dict = {}  # path -> (size, mtime_ns, parsed); day files are append-only, so a same-size file is unchanged


def read_day_file(p: Path) -> dict:
    """{"rows": [(slot, market_id, cols)], "polls": {slot: finished_ts}} of one day file (memoised by size and mtime)."""
    st = p.stat()
    hit = _MEMO.get(str(p))
    if hit is not None and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
        return hit[2]
    from . import store as S

    rows, polls = [], {}
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if '"kind":"hash"' in line:  # checkpoint lines carry no fields
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
                rows.append((r.get("slot"), mid, parse_uma(r["data"])))
    out = {"rows": rows, "polls": polls}
    _MEMO[str(p)] = (st.st_size, st.st_mtime_ns, out)
    return out


def uma_at(root: Path, cap_start: float) -> dict:
    """{"known": {market_id: cols} known at ``cap_start``, "first_poll", "files", "last_slot"} (``rules_at``'s rule)."""
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
        if gaps and gaps != [cap_day]:
            raise RulesGap(f"gamma_rules day files missing: {gaps[:5]}{'...' if len(gaps) > 5 else ''}")
    for p in sorted(root.glob("*.jsonl")):
        if p.stem > cap_day:
            break
        day = read_day_file(p)
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
