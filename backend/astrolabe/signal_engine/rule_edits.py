# ruff: noqa: E501
"""Rule-edit age from the ``gamma_rules`` stream (aux family ``ruleedit``, DESIGN_V1 section 43; CH228, CH187's end-date moves).

Same stream and clock as ``rules_text`` / ``uma_params`` (sections 41-42): a row is **known at a capture** iff the same
day file holds a ``poll`` line of the row's slot with ``ok`` true and ``finished_utc`` at or before the capture start.
An **edit** is a known row of a key whose watched fields differ from the key's previous known row (diff-based; the
stream's ``reason`` is not trusted, and a key's first known row is never an edit, so a market entering the frame
already edited has no known edit). The edit's time is its slot's poll ``finished_utc`` (when it became known; the
real edit lies between the key's previous poll and this one, up to 1 h earlier in the hourly top frame and up to 6 h
in the volume frame).

* text edit: ``m:`` ``question`` / ``description`` / ``resolutionSource`` / ``groupItemTitle`` / ``outcomes``, or the
  ``title`` / ``description`` / ``resolutionSource`` of an ``e:`` event in the market's latest known ``event_ids``;
* end edit: the ``m:`` row's ``endDate`` string. Only *that it moved*, *when* and *which way* are read; the new
  end value itself is never a column (hours-to-end is market_state's).

UMA fields, ``startDate``, ``negRiskOther``, the event ``endDate`` and ``event_ids`` membership are not edits here. No
price, outcome or wallet field exists in the stream. ``rules_text.py`` and ``uma_params.py`` are not edited (their
tables keep their pinned shas); this file has its own reader and sha.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .rules_text import RULES_FIRST_DAY, RulesGap

RE_VERSION = "se-aux-ruleedit-v1"
RE_COLUMNS = ["re_text_7d", "re_text_age", "re_end_7d", "re_end_age", "re_end_later"]
M_TEXT = ("question", "description", "resolutionSource", "groupItemTitle", "outcomes")
E_TEXT = ("title", "description", "resolutionSource")
WINDOW_H = 168.0


def _digest(data: dict, fields: tuple) -> bytes:
    return hashlib.blake2b(json.dumps([data.get(k) for k in fields], sort_keys=True).encode(), digest_size=8).digest()


def _end_ts(v) -> float:
    from . import store as S

    return S.epoch(v) if isinstance(v, str) and v.strip() else math.nan


_MEMO: dict = {}  # path -> (size, mtime_ns, parsed); day files are append-only, so a same-size file is unchanged


def read_day_file(p: Path) -> dict:
    """{"rows": [(slot, "m" | "e", id, text_digest, end_str, event_ids)], "polls": {slot: finished_ts}} (memoised)."""
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
            elif k == "row" and isinstance(r.get("data"), dict):
                key, d = str(r.get("key", "")), r["data"]
                try:
                    i = int(key[2:])
                except ValueError:
                    continue
                if key.startswith("m:"):
                    eids = d.get("event_ids")
                    eids = tuple(int(e) for e in eids if str(e).isdigit()) if isinstance(eids, list) else ()
                    rows.append((r.get("slot"), "m", i, _digest(d, M_TEXT), d.get("endDate"), eids))
                elif key.startswith("e:"):
                    rows.append((r.get("slot"), "e", i, _digest(d, E_TEXT), None, ()))
    out = {"rows": rows, "polls": polls}
    _MEMO[str(p)] = (st.st_size, st.st_mtime_ns, out)
    return out


def edits_at(root: Path, cap_start: float) -> dict:
    """The edit state known at ``cap_start`` (``rules_at``'s file, clock and gap rules).

    {"known": {market_id: (text_ts, end_ts, end_later)} for markets with a known ``m:`` row (NaN where no edit is
    known), "first_poll", "files", "last_slot", "n_text_m", "n_text_e", "n_end"} (edit counts over the files read)."""
    root = Path(root)
    empty = {"known": {}, "first_poll": None, "files": [], "last_slot": None, "n_text_m": 0, "n_text_e": 0, "n_end": 0}
    if not root.exists():
        return empty
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
    prev_m: dict[int, tuple] = {}  # market -> (text digest, endDate string)
    prev_e: dict[int, bytes] = {}
    events: dict[int, tuple] = {}
    text_m: dict[int, float] = {}
    text_e: dict[int, float] = {}
    end_m: dict[int, tuple] = {}  # market -> (ts, later flag)
    n_tm = n_te = n_end = 0
    first_poll, last_slot, files = None, None, []
    for p in sorted(root.glob("*.jsonl")):
        if p.stem > cap_day:
            break
        day = read_day_file(p)
        polls = day["polls"]
        ok = {s for s, ts in polls.items() if ts <= cap_start}
        if not ok:
            continue
        files.append(p.name)
        first_poll = min(first_poll or math.inf, min(polls[s] for s in ok))
        last_slot = max(ok) if last_slot is None else max(last_slot, max(ok))
        for slot, kind, i, dg, end_s, eids in day["rows"]:  # file order is time order
            if slot not in ok:
                continue
            ts = polls[slot]
            if kind == "m":
                old = prev_m.get(i)
                if old is not None:
                    if old[0] != dg:
                        text_m[i] = ts
                        n_tm += 1
                    if old[1] != end_s:
                        a, b = _end_ts(old[1]), _end_ts(end_s)
                        end_m[i] = (ts, float(b > a) if math.isfinite(a) and math.isfinite(b) and a != b else math.nan)
                        n_end += 1
                prev_m[i] = (dg, end_s)
                events[i] = eids
            else:
                if i in prev_e and prev_e[i] != dg:
                    text_e[i] = ts
                    n_te += 1
                prev_e[i] = dg
    known: dict[int, tuple] = {}
    for i in prev_m:
        tt = max([text_m.get(i, -math.inf)] + [text_e.get(e, -math.inf) for e in events.get(i, ())])
        e = end_m.get(i)
        known[i] = (tt if math.isfinite(tt) else math.nan, e[0] if e else math.nan, e[1] if e else math.nan)
    return {"known": known, "first_poll": first_poll, "files": files, "last_slot": last_slot,
            "n_text_m": n_tm, "n_text_e": n_te, "n_end": n_end}


def edit_columns(state: tuple, cap_start: float) -> list[float]:
    """RE_COLUMNS of one known market (pure): 7-day flags 1 / 0, log1p ages in hours (NaN with no known edit)."""
    text_ts, end_ts, later = state
    out = []
    for ts in (text_ts, end_ts):
        h = (cap_start - ts) / 3600.0 if math.isfinite(ts) else math.nan
        out += [float(math.isfinite(h) and h <= WINDOW_H), math.log1p(max(h, 0.0)) if math.isfinite(h) else math.nan]
    return out + [later]


def code_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
