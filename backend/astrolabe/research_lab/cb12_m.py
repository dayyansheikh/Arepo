# ruff: noqa: E501
"""CB12-M: mention-basket overpricing (docs/research_lab/CREATIVE_BATCH_12.md CB12-M, section 10 items 4-8, 23). Rules part ``M``.

Frame (q0242), prices and prints (q0243), census (q0249, counts only), screen (q0252: M1, M2 on SCREEN events) and rep (q0256: sealed HOLDOUT). EXPLORATORY: every
line carries "L1, hindsight start time". No edge, calibration or profitability claim. This module imports ``cb12_common`` and nothing from the other families, so its
rules hash is independent of E / F / X / O code.

M1: ``D_e = S_e - N_e`` (sum of member YES prices two hours before the scheduled start minus the number of members that resolve YES); floor ``D-bar >= 0.3`` words AND
``D-bar / mean S >= 5%``. M2: a resting maker ask at ``ceil_tick(p + 1.5c)`` on every source-available member, filled only by a transaction in ``[t, startTime)`` whose YES-terms
price is >= ask + 1c. Outcomes are read only from the guarded SCREEN / HOLDOUT outcome files (separate; the HOLDOUT sha256 is in the seal).
"""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.stats import norm

from . import cb8_common as cm
from . import cb12_common as c12
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow

HOUR = 3600.0
DAY = 86400.0
TAG_ID = 100343  # Gamma tag "mention-markets"
M_SCREEN = ("2025-06-01", "2026-03-01")
M_HOLD = ("2026-03-01", "2026-10-01")
MIN_MEMBERS = 8
OCCASION_MAX_S = 36 * HOUR
ORIGIN_S = 2 * HOUR  # t = startTime - 2 h (primary)
ORIGIN_ALT_S = 24 * HOUR  # t24 = startTime - 24 h (robustness)
LIST_BUFFER_S = HOUR  # a member is listed by t if created at or before t - 1 h
FETCH_BEFORE_S = 26 * HOUR
FIDELITY = 10
AVAIL_MIN_SHARE = 0.90
ASK_OFFSET = 0.015
ASK_OFFSET_ROBUST = 0.010
TRADE_THROUGH = 0.01
TRADE_THROUGH_ROBUST = 0.02
FILL_CAP = 100.0
BID_PROXY = 0.015
TAKER_FEE = 0.04
M1_FLOOR_WORDS = 0.3
M1_FLOOR_SHARE = 0.05
M2_FLOOR = 0.005
COPULA_LOADINGS = (0.15, 0.30, 0.55)  # speaker factor, event factor, idiosyncratic (variances)
GM_MIN = {"events": 150, "speakers": 15, "weeks": 30}
GMP_MDE_MAX = 1.0
COVER_MIN = 0.90
START_EDIT_LATE_S = 6 * HOUR
START_EDIT_CREATED_S = 26 * HOUR
PRICE_BANDS = (0.3, 0.6)
LONGSHOT_SHARE = 0.80
FRAME_RUN = "h12_say"
FRAME_STATUS = "say_frame_complete"
PRICES_STATUS = "say_prices_complete"
FRAME_OUTPUT_CAP_GB = 0.005
PRICES_OUTPUT_CAP_GB = 0.08
LABEL_M = "L1, hindsight start time"
# Sports exclusion (section 0.4, frozen BEFORE q0241 from out-of-window events; the ids are filled by the coordinator from the tag listing of events that end before
# 2025-06-01 and regenerate part M): the slug list below is the conservative generic set, the broadcast regex is the declared one.
SPORTS_TAG_SLUGS = ("sports", "nfl", "nba", "wnba", "mlb", "nhl", "ufc", "mma", "soccer", "football", "basketball", "baseball", "hockey", "tennis", "golf", "f1", "formula-1",
                    "college-football", "college-basketball", "epl", "premier-league", "champions-league", "mls", "boxing", "olympics", "world-cup", "super-bowl", "cricket", "rugby")
SPORTS_TAG_IDS = ("1",)  # Gamma tag id 1 = "Sports"; extended by the coordinator
BROADCAST_RE = re.compile(r"(?i)\b(announcers?|commentators?|broadcast|halftime|pre-?game|post-?game|game|Super Bowl|World Series|NFL|NBA|WNBA|MLB|NHL|UFC|F1|Formula 1|Premier League|Champions League)\b")
SPEAKER_RE = re.compile(r"(?i)^\s*what (?:will|did|would)\s+(.+?)\s+(?:say|mention)\b")  # frozen speaker key when the event has no series id
EVENT_COLUMNS = ["event_id", "series_id", "speaker_key", "start_epoch", "end_epoch", "created_epoch", "neg_risk", "n_members", "split", "status", "sports_tag", "sports_re",
                 "occasion", "start_edit_a", "start_edit_b", "title_sha256"]
MEMBER_COLUMNS = ["event_id", "market_id", "condition_id", "token_yes", "yes_index", "created_epoch"]
OUTCOME_COLUMNS = ["market_id", "event_id", "yes_index", "outcome_prices", "uma_status"]
PRICE_COLUMNS = ["market_id", "ts", "p"]
TX_COLUMNS = ["market_id", "ts", "price", "size", "notional", "n_fills", "max_fill_notional", "post"]
MARKET_COLUMNS = ["market_id", "event_id", "status", "n_points", "oldest_ts", "truncated", "reach_t24", "n_prints", "n_tx", "first_post_ts"]
FORBIDDEN_COLUMNS = ("outcome_prices", "uma_status", "closedTime", "y", "wallet", "proxyWallet", "transactionHash", "side", "pnl", "net")
SMOKE_NEEDS = ("guards_fixture_M", "m_gamma_paging", "m_prices_history", "m_data_api_reach")
SMOKE_WEEKS = (("2025-05-05T00:00:00Z", "2025-05-12T00:00:00Z"), ("2025-05-12T00:00:00Z", "2025-05-19T00:00:00Z"))


def _ep(d: str) -> float:
    return cm.ep(d + "T00:00:00Z") if "T" not in d else cm.ep(d)


def split_of(end_epoch: float) -> str | None:
    if _ep(M_SCREEN[0]) <= end_epoch < _ep(M_SCREEN[1]):
        return "screen"
    if _ep(M_HOLD[0]) <= end_epoch < _ep(M_HOLD[1]):
        return "holdout"
    return None


# =====================================================================================================================================================
# Event parsing and the frame rules
# =====================================================================================================================================================


def is_sports(tags: Iterable[dict], title: str) -> tuple[bool, bool]:
    """(by tag, by broadcast regex). A tag counts if its id is in ``SPORTS_TAG_IDS`` or its slug in ``SPORTS_TAG_SLUGS``."""
    by_tag = any(str(t.get("id")) in SPORTS_TAG_IDS or str(t.get("slug") or "").lower() in SPORTS_TAG_SLUGS for t in tags if isinstance(t, dict))
    return by_tag, bool(BROADCAST_RE.search(title or ""))


def speaker_key(series_id: str, title: str, event_id: str) -> str:
    if series_id:
        return f"series:{series_id}"
    m = SPEAKER_RE.search(title or "")
    if m:
        return "who:" + re.sub(r"\s+", " ", m.group(1).strip().lower())
    return f"event:{event_id}"


def parse_member(m: dict, event_id: str) -> dict | None:
    """Whitelisted member fields; a non Yes/No market is not a binary member (None). ``outcomePrices`` and status go to the guarded file via ``parse_outcome``."""
    labels = [str(x).strip().lower() for x in c12.listish(m.get("outcomes"))]
    toks = [str(x) for x in c12.listish(m.get("clobTokenIds"))]
    if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2 or m.get("id") is None:
        return None
    yi = labels.index("yes")
    return {"event_id": event_id, "market_id": str(m["id"]), "condition_id": str(m.get("conditionId") or ""), "token_yes": toks[yi], "yes_index": yi,
            "created_epoch": c12.parse_iso(m.get("createdAt"))}


def parse_outcome(m: dict, event_id: str, yes_index: int) -> dict:
    statuses = m.get("umaResolutionStatuses")
    status = str(m.get("umaResolutionStatus") or (statuses if statuses else ""))
    return {"market_id": str(m["id"]), "event_id": event_id, "yes_index": yes_index, "outcome_prices": json.dumps(c12.listish(m.get("outcomePrices"))), "uma_status": status}


def parse_event(ev: dict) -> tuple[dict, list[dict], list[dict]] | None:
    """(event row, member rows, guarded outcome rows). Only whitelisted fields leave this function: the title is hashed and used for flags, never stored."""
    if not isinstance(ev, dict) or ev.get("id") is None:
        return None
    eid = str(ev["id"])
    title = str(ev.get("title") or "")
    tags = ev.get("tags") if isinstance(ev.get("tags"), list) else []
    ser = [s for s in (ev.get("series") if isinstance(ev.get("series"), list) else []) if isinstance(s, dict) and s.get("id") is not None]
    series_id = str(ser[0]["id"]) if ser else ""
    by_tag, by_re = is_sports(tags, title)
    start, end = c12.parse_iso(ev.get("startTime")), c12.parse_iso(ev.get("endDate"))
    created = c12.parse_iso(ev.get("createdAt"))
    members, outs = [], []
    for m in ev.get("markets") if isinstance(ev.get("markets"), list) else []:
        if not isinstance(m, dict):
            continue
        pm = parse_member(m, eid)
        if pm:
            members.append(pm)
            outs.append(parse_outcome(m, eid, pm["yes_index"]))
    occ = bool(math.isfinite(start) and math.isfinite(end) and (end - start) <= OCCASION_MAX_S)
    sp = split_of(end) if math.isfinite(end) else None
    row = {"event_id": eid, "series_id": series_id, "speaker_key": speaker_key(series_id, title, eid), "start_epoch": start, "end_epoch": end, "created_epoch": created,
           "neg_risk": int(bool(ev.get("negRisk"))), "n_members": len(members), "split": sp or "", "status": "", "sports_tag": int(by_tag), "sports_re": int(by_re),
           "occasion": int(occ),
           "start_edit_a": int(bool(math.isfinite(start) and math.isfinite(end) and start > end)),
           "start_edit_b": int(bool(math.isfinite(created) and math.isfinite(start) and created > start - START_EDIT_CREATED_S)),
           "title_sha256": c12.rank("arepo-cb12-title", title)}
    return row, members, outs


def event_status(row: dict, member_markets: list[str], excl_ids: set[str], excl_event: set[str], excl_series: set[str], series_dates: dict[str, list[float]] | None) -> tuple[str, str]:
    """(status, source). Order: no start / outside windows -> sports -> period basket -> key drop -> too few binary members. Key drops: market id, event id and the
    series-date key (same series, ``startTime`` within +-1 day of an excluded event of that series; needs ``series_dates``, else only the full-series counterfactual is counted)."""
    if not math.isfinite(row["start_epoch"]) or not math.isfinite(row["end_epoch"]) or not row["split"]:
        return "dropped:no_start_or_window", "frame"
    if row["sports_tag"] or row["sports_re"]:
        return "dropped:sports", "tag" if row["sports_tag"] else "regex"
    if not row["occasion"]:
        return "period", "occasion_rule"
    if str(row["event_id"]) in excl_event:
        return "dropped:key", "event"
    if any(m in excl_ids for m in member_markets):
        return "dropped:key", "market"
    if series_dates is not None and row["series_id"] in series_dates and any(abs(row["start_epoch"] - d) <= DAY for d in series_dates[row["series_id"]]):
        return "dropped:key", "series_date"
    if row["n_members"] < MIN_MEMBERS:
        return "dropped:members", "n_members"
    return "kept", ""


def full_series_counterfactual(row: dict, excl_series: set[str]) -> bool:
    """The drop the FULL series rule would have made (reported by the census, not applied)."""
    return bool(row["series_id"] and row["series_id"] in excl_series)


def walk_window(lim, a: float, b: float, *, tag_id: int = TAG_ID, page: int = c12.GAMMA_PAGE, offset_cap: int = c12.GAMMA_OFFSET_CAP, depth: int = 0, stats: dict | None = None) -> list[dict]:
    """Closed Gamma events with ``tag_id`` and ``endDate`` in ``[a, b)``, paged to the offset cap; a window that is still full at the cap is split in half until uncapped
    (``stats['splits']`` counts the splits; a window of < 1 h that is still capped raises ``Refused``)."""
    out: list[dict] = []
    capped = True
    for off in range(0, offset_cap + page, page):
        st, data = lim.get(c12.GAMMA_EVENTS, {"closed": "true", "tag_id": tag_id, "end_date_min": cm.iso(a), "end_date_max": cm.iso(b), "order": "id", "ascending": "true",
                                              "limit": page, "offset": off})
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma events status {st}")
        out.extend(x for x in data if isinstance(x, dict))
        if len(data) < page:
            capped = False
            break
    if not capped:
        return out
    if b - a < HOUR:
        raise Refused(f"gamma events window {cm.iso(a)}..{cm.iso(b)} is capped even below 1 h")
    if stats is not None:
        stats["splits"] = stats.get("splits", 0) + 1
    mid = a + (b - a) / 2
    return walk_window(lim, a, mid, tag_id=tag_id, page=page, offset_cap=offset_cap, depth=depth + 1, stats=stats) + \
        walk_window(lim, mid, b, tag_id=tag_id, page=page, offset_cap=offset_cap, depth=depth + 1, stats=stats)


def month_windows(a: str, b: str) -> list[tuple[float, float]]:
    y, m = int(a[:4]), int(a[5:7])
    ye, me = int(b[:4]), int(b[5:7])
    out = []
    while (y, m) < (ye, me):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append((datetime(y, m, 1, tzinfo=UTC).timestamp(), datetime(ny, nm, 1, tzinfo=UTC).timestamp()))
        y, m = ny, nm
    return out


def frame_done(rdir: Path) -> dict | None:
    """The frame (q0242) and the prices job (q0243) share the run directory ``h12_say`` and its manifest: the frame's completion is a ``state.frame_complete`` flag that the prices
    job's own manifests carry forward (a frame re-run after prices started never refetches)."""
    mp = Path(rdir) / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if man.get("status") == FRAME_STATUS and man.get("complete") is True and not man.get("stopped"):
        return man
    if (man.get("state") or {}).get("frame_complete") is True:
        return man
    return None


def _wcsv(fr, path: Path, header: list[str], rows: Iterable[list]) -> None:
    fr.budget.write_gz_csv(path, header, rows)
    fr.record_file(path)


def say_frame(hist_root: Path, transport, *, rules_sha: str, smoke_paths, exclusion_keys_path: Path, now: float, rps: float = 2.0, disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3),
              budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None,
              health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c12.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0242. Tag-100343 events ending in ``[2025-06-01, 2026-10-01)`` (monthly windows, split until uncapped), whitelisted fields only, the sports / occasion / key
    rules applied as a ``status`` column (every fetched event is kept in the file so the census can report each rule), HOLDOUT rows in ``holdout/``, outcomes in the two
    guarded files. No price or print is read."""
    from . import cb12_smoke as sm  # noqa: PLC0415

    rdir = c12.require_output_root(Path(hist_root) / FRAME_RUN)
    st = c12.stall_of(rdir)
    if st:
        return st
    done = frame_done(rdir)
    if done:
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": done.get("counts")}
    bad = sm.smoke_failures(smoke_paths, SMOKE_NEEDS)
    if bad:
        return c12.write_stall(rdir, c12.c9.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c12.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c12.UNVERIFIED:
        return c12.write_stall(rdir, c12.c9.STALL_DISJOINTNESS, "exclusion keys: more than 2% of ids without metadata")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c12.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    series_dates = None
    sd_path = Path(exclusion_keys_path).with_name("exclusion_series_dates.csv.gz")
    if sd_path.exists():
        series_dates = {}
        for r in c12.read_csv_gz(sd_path):
            series_dates.setdefault(str(r["series_id"]), []).append(float(r["start_epoch"]))
    rdir.mkdir(parents=True, exist_ok=True)
    fr = cm.open_run(Path(hist_root), FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb12_say_frame", label="CB12-M frame",
                     params={"evidence_role": c12.EVIDENCE_ROLE_HIST, "tag_id": TAG_ID, "windows": [list(M_SCREEN), list(M_HOLD)], "exclusion_keys_sha256": ksha},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    stats: dict = {}
    seen: set[str] = set()
    ev_rows: list[dict] = []
    mem_rows: dict[str, list[dict]] = {}
    out_rows: dict[str, list[dict]] = {}
    try:
        for a, b in month_windows(M_SCREEN[0], M_HOLD[1]):
            why = fr.stop_reason(should_stop)
            if why:
                mm = fr.manifest(why, {"transient": True})
                mm["status"] = "in_progress"
                return mm
            for ev in walk_window(fr.lim, a, b, stats=stats):
                p = parse_event(ev)
                if p is None or p[0]["event_id"] in seen:
                    continue
                row, mems, outs = p
                seen.add(row["event_id"])
                if not row["split"]:  # a boundary event outside both windows by the parsed endDate
                    continue
                row["status"], src = event_status(row, [m["market_id"] for m in mems], ids, keys["event"], keys["series"], series_dates)
                row["_src"] = src
                row["_series_cf"] = int(full_series_counterfactual(row, keys["series"]))
                ev_rows.append(row)
                mem_rows[row["event_id"]] = mems
                out_rows[row["event_id"]] = outs
    except (cm.ApiError, RuntimeError) as exc:
        mm = fr.manifest(f"gamma_failed: {exc}"[:200], {"transient": True})
        mm["status"] = "in_progress"
        return mm
    try:
        counts: dict = {}
        report: dict = {"splits_of_capped_windows": stats.get("splits", 0), "series_date_key": "available" if series_dates is not None else "unavailable (no exclusion_series_dates.csv.gz); "
                        "only market-id and event-id drops applied; the full-series counterfactual is counted"}
        for split in ("screen", "holdout"):
            sub = sorted((r for r in ev_rows if r["split"] == split), key=lambda r: r["event_id"])
            base = rdir / "holdout" if split == "holdout" else rdir
            _wcsv(fr, base / "events.csv.gz", EVENT_COLUMNS, ([r[c] for c in EVENT_COLUMNS] for r in sub))
            _wcsv(fr, base / "members.csv.gz", MEMBER_COLUMNS, ([m[c] for c in MEMBER_COLUMNS] for r in sub for m in sorted(mem_rows[r["event_id"]], key=lambda x: x["market_id"])))
            oname = "outcomes_guarded_holdout.csv.gz" if split == "holdout" else "outcomes_guarded_screen.csv.gz"
            _wcsv(fr, base / oname, OUTCOME_COLUMNS, ([o[c] for c in OUTCOME_COLUMNS] for r in sub if r["status"] == "kept" for o in out_rows[r["event_id"]]))
            report[split] = {"events_fetched": len(sub), "by_status": dict(Counter(r["status"] for r in sub)), "key_drop_source": dict(Counter(r["_src"] for r in sub if r["status"] == "dropped:key")),
                             "sports_by": {"tag": sum(r["sports_tag"] for r in sub), "regex": sum(r["sports_re"] for r in sub)},
                             "full_series_counterfactual_drops": sum(r["_series_cf"] for r in sub if r["status"] in ("kept", "dropped:key")),
                             "n_kept_members": sum(len(mem_rows[r["event_id"]]) for r in sub if r["status"] == "kept")}
            counts[f"events_{split}"] = len(sub)
        (rdir / "frame_report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
        fr.record_file(rdir / "frame_report.json")
        (rdir / "split.json").write_text(json.dumps({"windows": {"screen": list(M_SCREEN), "holdout": list(M_HOLD)}, "rule": "event endDate", "counts": counts}, indent=1, sort_keys=True))
        fr.record_file(rdir / "split.json")
        fr.counts.update(counts)
        fr.extra_state["frame_complete"] = True
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m["status"] = FRAME_STATUS
    return m


# =====================================================================================================================================================
# q0243: prices-history and prints (resumable, one member in memory at a time)
# =====================================================================================================================================================


def kept_members(frame_dir: Path, split: str) -> list[dict]:
    """Members to fetch: kept events' members listed by ``t = start - 2 h`` (created at or before ``t - 1 h``)."""
    base = Path(frame_dir) / "holdout" if split == "holdout" else Path(frame_dir)
    evs = {r["event_id"]: r for r in c12.read_csv_gz(base / "events.csv.gz") if r["status"] == "kept"}
    out = []
    for r in c12.read_csv_gz(base / "members.csv.gz"):
        e = evs.get(r["event_id"])
        if e is None:
            continue
        t = float(e["start_epoch"]) - ORIGIN_S
        if float(r["created_epoch"]) <= t - LIST_BUFFER_S:
            out.append({**r, "split": split, "start": float(e["start_epoch"])})
    return sorted(out, key=lambda x: (x["split"], x["market_id"]))


def tx_rows_for(prints: list[dict], yes_index: int, start: float) -> tuple[list[list], dict]:
    """Aggregate prints and keep the transactions in ``[start - 26 h, start)`` plus the first transaction at or after ``start`` (``post`` = 1)."""
    rows, info = c12.aggregate_transactions(prints, yes_index)
    keep = [[r["ts"], r["price"], r["size"], r["notional"], r["n_fills"], r["max_fill_notional"], 0] for r in rows if start - FETCH_BEFORE_S <= r["ts"] < start]
    post = [r for r in rows if r["ts"] >= start]
    first_post = None
    if post:
        r = min(post, key=lambda x: x["ts"])
        first_post = r["ts"]
        keep.append([r["ts"], r["price"], r["size"], r["notional"], r["n_fills"], r["max_fill_notional"], 1])
    info["first_post_ts"] = first_post
    return keep, info


def say_prices(hist_root: Path, frame_dir: Path, transport, *, rules_sha: str, now: float, rps: float = 2.0, disk_cap: int = int(PRICES_OUTPUT_CAP_GB * 1024**3),
               budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None,
               data_dumps: Path | None = None, data_dumps_cap_gb: float = c12.DATA_DUMPS_CAP_GB, free_fn=None, page_limit: int = c12.DATA_PAGE_LIMIT, pages: int = c12.DATA_PAGES) -> dict:
    """q0243, one resumable chunk: per listed member of a kept event (SCREEN then HOLDOUT) the ``prices-history`` points over ``[start - 26 h, start]`` at fidelity 10 and the
    newest-first transactions (<= 2 pages of 10,000; the second only if the first is full and its oldest print is after ``t24``). A member whose prints do not reach back to
    ``t24`` is "unavailable (source)". HOLDOUT rows go to ``holdout/``. No outcome is read."""
    rdir = c12.require_output_root(Path(hist_root) / FRAME_RUN)
    fdir = Path(frame_dir)
    st = c12.stall_of(fdir)
    if st:
        return st
    if not frame_done(fdir):
        raise NotNow("q0243 waits for q0242 (say_frame) to finish")
    done = c12.manifest_complete(rdir, (PRICES_STATUS,))
    if done:
        return {"stopped": None, "status": PRICES_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c12.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(Path(hist_root), FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb12_say_prices", label="CB12-M prices",
                     params={"evidence_role": c12.EVIDENCE_ROLE_HIST, "fidelity": FIDELITY, "pages": pages, "limit": page_limit}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap,
                     rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    members = kept_members(rdir, "screen") + kept_members(rdir, "holdout")
    part = rdir / "markets_partial.jsonl"
    have: dict[str, dict] = {}
    if part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                have[rec["market_id"]] = rec
    try:
        for m in members:
            mid = m["market_id"]
            if mid in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                mm = fr.manifest(why, {"transient": True})
                mm["status"] = "in_progress"
                return mm
            start = m["start"]
            t24 = start - ORIGIN_ALT_S
            try:
                stp, data = fr.lim.get(hb.CLOB_PRICES, {"market": m["token_yes"], "startTs": int(start - FETCH_BEFORE_S), "endTs": int(start), "fidelity": FIDELITY})
                if stp != 200:
                    raise cm.ApiError(f"prices-history status {stp}")
                pts = [[int(h["t"]), float(h["p"])] for h in ((data or {}).get("history") or []) if isinstance(h, dict) and "t" in h and "p" in h]
                prints, info = c12.fetch_prints_paged(fr.lim, m["condition_id"], t24, limit=page_limit, pages=pages)
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[mid] = fails.get(mid, 0) + 1
                if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                    mm = fr.manifest(f"fetch_failed {mid}: {exc}"[:200], {"transient": True})
                    mm["status"] = "in_progress"
                    return mm
                rec = {"market_id": mid, "event_id": m["event_id"], "split": m["split"], "status": "unavailable (source)", "points": [], "tx": [], "n_points": 0,
                       "oldest_ts": None, "truncated": 1, "reach_t24": 0, "n_prints": 0, "n_tx": 0, "first_post_ts": None}
            else:
                tx, tinfo = tx_rows_for(prints, int(m["yes_index"]), start)
                del prints
                ok = c12.reach_ok(info, t24)
                rec = {"market_id": mid, "event_id": m["event_id"], "split": m["split"], "status": "ok" if ok else "unavailable (source)", "points": pts, "tx": tx,
                       "n_points": len(pts), "oldest_ts": None if not math.isfinite(info["oldest_ts"]) else info["oldest_ts"], "truncated": int(bool(info["truncated"])),
                       "reach_t24": int(ok), "n_prints": info["n_prints"], "n_tx": len(tx), "first_post_ts": tinfo["first_post_ts"]}
            with part.open("a") as fh:
                fh.write(json.dumps(rec, default=float) + "\n")
            have[mid] = rec
        for split in ("screen", "holdout"):
            recs = [have[m["market_id"]] for m in members if m["split"] == split]
            base = rdir / split
            _wcsv(fr, base / "prices.csv.gz", PRICE_COLUMNS, ([x["market_id"], a, b] for x in recs for a, b in x["points"]))
            _wcsv(fr, base / "tx.csv.gz", TX_COLUMNS, ([x["market_id"], *row] for x in recs for row in x["tx"]))
            _wcsv(fr, base / "markets.csv.gz", MARKET_COLUMNS, ([x[c] if x[c] is not None else "" for c in MARKET_COLUMNS] for x in sorted(recs, key=lambda y: y["market_id"])))
        for rel in ("events.csv.gz", "members.csv.gz", "outcomes_guarded_screen.csv.gz", "holdout/events.csv.gz", "holdout/members.csv.gz", "holdout/outcomes_guarded_holdout.csv.gz"):
            if (rdir / rel).exists():
                fr.record_file(rdir / rel)
        part.unlink(missing_ok=True)
        fr.counts.update(members=len(have), unavailable_source=sum(1 for x in have.values() if x["status"] != "ok"))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m_ = fr.manifest(None, {"complete": True, "status": PRICES_STATUS})
    m_["status"] = PRICES_STATUS
    return m_


# =====================================================================================================================================================
# Loaders (a census / screen job never receives an outcome; a screen job never opens holdout/)
# =====================================================================================================================================================


def load_split(rdir: Path, split: str, *, job: str) -> dict:
    """Events (status kept), members, prices, transactions and market records of one split. ``holdout`` only for ``rep-M``; census and screen refuse every holdout path.
    No outcome column is read here (outcomes come from ``open_guarded`` in screen / rep only)."""
    rdir = Path(rdir)
    if split == "holdout":
        if job != "rep-M":
            raise Refused(f"the HOLDOUT is read only by rep-M, not {job!r}")
        base = rdir / "holdout"
    elif split == "screen":
        base = rdir
        c12.guard_screen_path(base / "events.csv.gz")
    else:
        raise Refused(f"unknown split {split!r}")
    pdir = rdir / ("holdout" if split == "holdout" else "screen")
    events = {r["event_id"]: r for r in c12.read_csv_gz(base / "events.csv.gz")}
    members: dict[str, list[dict]] = {}
    for r in c12.read_csv_gz(base / "members.csv.gz"):
        members.setdefault(r["event_id"], []).append(r)
    prices: dict[str, list[tuple[float, float]]] = {}
    for r in c12.read_csv_gz(pdir / "prices.csv.gz"):
        prices.setdefault(r["market_id"], []).append((float(r["ts"]), float(r["p"])))
    tx: dict[str, list[tuple[float, float, float, int]]] = {}
    for r in c12.read_csv_gz(pdir / "tx.csv.gz"):
        tx.setdefault(r["market_id"], []).append((float(r["ts"]), float(r["price"]), float(r["size"]), int(r["post"])))
    for v in tx.values():
        v.sort()
    markets = {r["market_id"]: r for r in c12.read_csv_gz(pdir / "markets.csv.gz")}
    return {"events": events, "members": members, "prices": prices, "tx": tx, "markets": markets, "split": split}


# =====================================================================================================================================================
# Units, outcomes, statistics
# =====================================================================================================================================================


def outcome_y(outcome_prices: str, uma_status: str, yes_index: int) -> tuple[float, str]:
    """(Y, kind). A clean resolved vector -> 1 or 0 (``clean``); 50-50 -> 0.5 (``5050``); anything else (unresolved, voided, malformed) -> 0.5 (``unclean``)."""
    v = [c12.num(x) for x in c12.listish(outcome_prices)]
    st = str(uma_status or "").lower()
    if len(v) != 2 or not all(math.isfinite(x) for x in v):
        return 0.5, "unclean"
    yes, other = v[yes_index], v[1 - yes_index]
    if "resolved" in st and abs(yes - 0.5) < 1e-9 and abs(other - 0.5) < 1e-9:
        return 0.5, "5050"
    if "resolved" in st and ((abs(yes - 1) < 1e-9 and abs(other) < 1e-9) or (abs(yes) < 1e-9 and abs(other - 1) < 1e-9)):
        return float(yes > 0.5), "clean"
    return 0.5, "unclean"


def build_units(data: dict, *, origin_s: float = ORIGIN_S) -> list[dict]:
    """One unit per kept event at ``t = start - origin_s``. A member counts if listed (created at or before ``t - 1 h``); an event with < 8 listed members is
    ``excluded (<8 listed)``; a member's price is ``price_at`` (usable from stamp + 600 s, strictly before ``t``, age <= 24 h); the event is available iff >= 90% of its
    listed members have a price. ``S``-side arrays cover the available members only. ``src_ok`` is the print-reach flag of the q0243 market record."""
    units = []
    for eid, e in sorted(data["events"].items()):
        if e["status"] != "kept":
            continue
        start = float(e["start_epoch"])
        t = start - origin_s
        mems = data["members"].get(eid, [])
        listed = [m for m in mems if float(m["created_epoch"]) <= t - LIST_BUFFER_S]
        u = {"event_id": eid, "t": t, "start": start, "speaker": e["speaker_key"], "week": c12.iso_week_of(start), "n_members": len(mems), "n_listed": len(listed),
             "n_late": len(mems) - len(listed), "start_edit_a": int(e["start_edit_a"]), "start_edit_b": int(e["start_edit_b"])}
        if len(listed) < MIN_MEMBERS:
            units.append({**u, "status": "excluded (<8 listed)"})
            continue
        pairs = [(m, c12.price_at(data["prices"].get(m["market_id"], []), t, FIDELITY)) for m in listed]
        have = [(m, p) for m, p in pairs if p is not None]
        if len(have) / len(listed) < AVAIL_MIN_SHARE:
            units.append({**u, "status": "unavailable (no price)", "n_with_price": len(have)})
            continue
        mids = [m["market_id"] for m, _ in have]
        first_post = [c12.num(data["markets"].get(m, {}).get("first_post_ts")) for m in mids]
        first_post = [x for x in first_post if math.isfinite(x)]
        src = np.array([bool(int(data["markets"].get(m, {}).get("reach_t24") or 0)) for m in mids], bool)
        n_src = sum(1 for m, _ in pairs if int(data["markets"].get(m["market_id"], {}).get("reach_t24") or 0))
        units.append({**u, "status": "ok", "mids": mids, "p": np.array([p for _, p in have], float), "yes_index": [int(m["yes_index"]) for m, _ in have], "src_ok": src,
                      "n_src_listed": n_src, "n_with_price": len(have),
                      "start_edit_c": int(bool(first_post) and min(first_post) - start > START_EDIT_LATE_S)})
    return units


def attach_outcomes(units: list[dict], outcomes: list[dict]) -> list[dict]:
    """Add ``y`` (clean / 5050 / unclean scored 0.5), ``y_wc`` (unclean -> 1) and ``kinds`` to every ``ok`` unit. A member without an outcome row is ``unclean``."""
    by = {r["market_id"]: r for r in outcomes}
    for u in units:
        if u["status"] != "ok":
            continue
        ys, kinds = [], []
        for mid, yi in zip(u["mids"], u["yes_index"], strict=True):
            r = by.get(mid)
            y, k = outcome_y(r["outcome_prices"], r["uma_status"], yi) if r is not None else (0.5, "unclean")
            ys.append(y)
            kinds.append(k)
        u["y"] = np.array(ys, float)
        u["kinds"] = kinds
        u["y_wc"] = np.where(np.array([k == "unclean" for k in kinds]), 1.0, u["y"])
    return units


def ok_units(units: list[dict]) -> list[dict]:
    return [u for u in units if u["status"] == "ok"]


def clusters_of(units: list[dict]) -> dict:
    return {"speaker": [u["speaker"] for u in units], "week": [u["week"] for u in units]}


def d_values(units: list[dict], *, p_fn=None, y_key: str = "y") -> tuple[np.ndarray, np.ndarray]:
    """(D_e, S_e) over the units: ``S = sum p`` (``p_fn`` maps the price vector, e.g. the bid proxy), ``D = S - sum Y``."""
    S = np.array([float((p_fn(u["p"]) if p_fn else u["p"]).sum()) for u in units], float)
    N = np.array([float(u[y_key].sum()) for u in units], float)
    return S - N, S


def bid_proxy(p: np.ndarray) -> np.ndarray:
    return np.maximum(p - BID_PROXY, 0.0)


def m1_floor_ok(D: np.ndarray, S: np.ndarray) -> bool:
    if len(D) == 0:
        return False
    dbar, sbar = float(D.mean()), float(S.mean())
    return bool(dbar >= M1_FLOOR_WORDS and sbar > 0 and dbar / sbar >= M1_FLOOR_SHARE)


def copula_flat(p: np.ndarray, ev_idx: np.ndarray, sp_idx: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """``Y*_i = 1{Phi(Z_i) < p_i}``, ``Z_i = sqrt(.15) W_s + sqrt(.3) V_e + sqrt(.55) eps_i`` (speaker factor ``W_s``, event factor ``V_e``)."""
    a, b, c = (math.sqrt(x) for x in COPULA_LOADINGS)
    W = rng.standard_normal(int(sp_idx.max()) + 1) if len(p) else np.zeros(0)
    V = rng.standard_normal(int(ev_idx.max()) + 1) if len(p) else np.zeros(0)
    Z = a * W[sp_idx] + b * V[ev_idx] + c * rng.standard_normal(len(p))
    return (norm.cdf(Z) < p).astype(float)


def flat_index(units: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(concatenated prices, event index, speaker index) of the units' members."""
    sp: dict[str, int] = {}
    p, ev, spi = [], [], []
    for i, u in enumerate(units):
        n = len(u["p"])
        p.append(u["p"])
        ev.append(np.full(n, i, int))
        spi.append(np.full(n, sp.setdefault(u["speaker"], len(sp)), int))
    if not p:
        return np.zeros(0), np.zeros(0, int), np.zeros(0, int)
    return np.concatenate(p), np.concatenate(ev), np.concatenate(spi)


def m1_placebo(units: list[dict], *, n_draws: int = c12.PLACEBO_DRAWS, seed: int = c12.PLACEBO_SEEDS["M1_copula"]) -> dict:
    """Binding calibration placebo: outcomes drawn calibrated to the same prices with the copula; the advance rate is judged on the p threshold alone (floors off)."""
    p, ev, sp = flat_index(units)
    rng = np.random.default_rng(seed)
    cl = clusters_of(units)
    ps = []
    for _ in range(n_draws):
        y = copula_flat(p, ev, sp, rng)
        D = np.bincount(ev, weights=p - y, minlength=len(units))
        ps.append(c12.cluster_p(D, cl, alpha=c12.GATE_P)["p"])
    return {**c12.placebo_advance_rate(ps), "note": "M1 calibrated-outcome copula placebo", "seed": seed}


def drop_top(units: list[dict], D: np.ndarray, way: str, k: int = c12.TOP_DROP) -> list[dict]:
    keep = c12.top_k_drop_mask(D, [u[way] for u in units], k)
    return [u for u, kp in zip(units, keep, strict=True) if kp]


def holds(units: list[dict], D: np.ndarray, S: np.ndarray) -> dict:
    cp = c12.cluster_p(D, clusters_of(units))
    return {"p": cp["p"], "testable": cp["testable"], "p_ok": bool(cp["testable"] and cp["p"] < c12.GATE_P), "floor_ok": m1_floor_ok(D, S), "n": cp["n"]}


def m1_test(units: list[dict], data: dict, *, units_t24: list[dict] | None = None, placebo: bool = True, n_draws: int = c12.PLACEBO_DRAWS) -> dict:
    """M1 on attached ``ok`` units. ``data`` carries the print table for the print-sum robustness; ``units_t24`` the same events at ``start - 24 h``."""
    us = ok_units(units)
    D, S = d_values(us)
    cp = c12.cluster_p(D, clusters_of(us))
    res: dict = {"test": "M1", "label": LABEL_M, "n": len(us), "D_bar": float(D.mean()) if len(D) else math.nan, "S_bar": float(S.mean()) if len(S) else math.nan,
                 "D_bar_share": float(D.mean() / S.mean()) if len(D) and S.mean() > 0 else math.nan, "floor_ok": m1_floor_ok(D, S), "p": cp["p"], "testable": cp["testable"],
                 "ways": cp["ways"], "effect": float(D.mean()) if len(D) else math.nan}
    if len(us) < c12.MIN_UNITS or not cp["testable"]:
        return {**res, "advance": False, "verdict": "not testable (units / clusters)"}
    rob: dict = {}
    Db, _ = d_values(us, p_fn=bid_proxy)
    rob["bid_proxy_sign"] = bool(Db.mean() > 0)
    if units_t24 is not None:
        u24 = ok_units(units_t24)
        if u24:
            D24 = np.array([float(u["p"].sum() - u["y"].sum()) for u in u24])
            rob["t24_sign"] = bool(D24.mean() > 0)
        else:
            rob["t24_sign"] = False
    else:
        rob["t24_sign"] = None
    rob["print_sum"] = print_sum_check(us, data, float(D.mean()))
    order = np.argsort([u["start"] for u in us], kind="stable")
    half = len(us) // 2
    rob["halves_sign"] = bool(D[order[:half]].mean() > 0 and D[order[half:]].mean() > 0)
    nu = [u for u in us if not (u["start_edit_a"] or u["start_edit_b"] or u.get("start_edit_c"))]
    if len(nu) >= c12.MIN_UNITS:
        Dn, Sn = d_values(nu)
        h = holds(nu, Dn, Sn)
        rob["start_edit_excluded"] = bool(h["p_ok"] and h["floor_ok"])
    else:
        rob["start_edit_excluded"] = False
    Dw, _ = d_values(us, y_key="y_wc")
    rob["worst_case_unclean_sign"] = bool(Dw.mean() > 0)
    for way in ("speaker", "week"):
        sub = drop_top(us, D, way)
        if len(sub) >= c12.MIN_UNITS:
            Ds, Ss = d_values(sub)
            h = holds(sub, Ds, Ss)
            rob[f"top5_{way}_drop"] = bool(h["p_ok"] and h["floor_ok"])
        else:
            rob[f"top5_{way}_drop"] = False
    plc = m1_placebo(us, n_draws=n_draws) if placebo else None
    rob_ok = all(v is True for v in rob.values())
    res.update(robustness=rob, robustness_ok=rob_ok, placebo=plc)
    res["reported"] = m1_reported(us)
    ok = bool(cp["p"] < c12.GATE_P and res["floor_ok"] and rob_ok and (plc is None or plc["holds"]))
    res.update(stage1_pass=ok, early_holm_ok=c12.early_stage1_ok(cp["p"]), advance=bool(ok and c12.early_stage1_ok(cp["p"])),
               holm_pending=bool(ok and not c12.early_stage1_ok(cp["p"])))
    res["verdict"] = "advance (early Holm)" if res["advance"] else ("pending the full step-down (p in [0.005, 0.01))" if res["holm_pending"] else "no advance")
    return res


def print_sum_check(us: list[dict], data: dict, dbar: float) -> bool | None:
    """Print-based sum: each source-available member's last transaction in ``[t - 24 h, t)`` (fallback ``p``), N over the same members; keeps the sign and >= half of D-bar."""
    vals = []
    fb = n = 0
    for u in us:
        s = nn = 0.0
        cnt = 0
        for j, mid in enumerate(u["mids"]):
            if not u["src_ok"][j]:
                continue
            rows = [r for r in data["tx"].get(mid, []) if not r[3] and u["t"] - 24 * HOUR <= r[0] < u["t"]]
            if rows:
                s += rows[-1][1]
            else:
                s += float(u["p"][j])
                fb += 1
            n += 1
            nn += float(u["y"][j])
            cnt += 1
        if cnt:
            vals.append(s - nn)
    if not vals:
        return None
    v = float(np.mean(vals))
    return bool(v > 0 and v >= 0.5 * dbar)


def m1_reported(us: list[dict]) -> dict:
    """Uncounted: the per-word calibration slope of ``Y - p`` on ``p`` and ``D-bar`` by member price band."""
    p = np.concatenate([u["p"] for u in us])
    y = np.concatenate([u["y"] for u in us])
    slope = float(np.polyfit(p, y - p, 1)[0]) if len(p) > 2 and p.std() > 0 else math.nan
    bands = {"lt_0.3": p < PRICE_BANDS[0], "0.3_0.6": (p >= PRICE_BANDS[0]) & (p <= PRICE_BANDS[1]), "gt_0.6": p > PRICE_BANDS[1]}
    tot = float((p - y).sum())
    band = {k: float((p[mk] - y[mk]).sum()) for k, mk in bands.items()}
    D = np.array([float(u["p"].sum() - u["y"].sum()) for u in us])
    size = np.array([len(u["p"]) for u in us])
    cuts = np.quantile(size, [1 / 3, 2 / 3]) if len(size) else np.zeros(2)
    tercile = np.where(size <= cuts[0], 0, np.where(size <= cuts[1], 1, 2))
    by_size = {f"size_tercile_{k}": (float(D[tercile == k].mean()) if (tercile == k).any() else None) for k in range(3)}
    sp: dict[str, list[float]] = {}
    for u, d in zip(us, D, strict=True):
        sp.setdefault(u["speaker"], []).append(float(d))
    top = sorted(((k, sum(v)) for k, v in sp.items()), key=lambda kv: -abs(kv[1]))[:5]
    return {"per_word_slope": slope, "D_by_band_sum": band, "longshot_carried": bool(tot > 0 and band["lt_0.3"] / tot >= LONGSHOT_SHARE), "D_bar_by_basket_size": by_size,
            "D_sum_top5_speakers": {k: v for k, v in top}, "series_age_split": "not reported (series age is not defined in the design)"}


# ---- M2 ------------------------------------------------------------------------------------------------------------------------------------


def fill_member(ask: float, rows: list[tuple[float, float, float, int]], t: float, start: float, trade_through: float) -> tuple[float, float] | None:
    """The first transaction in ``[t, start)`` (never the post-start row) with YES-terms price >= ``ask + trade_through`` fills the ask: (fill price, filled size)."""
    for ts, price, size, post in rows:
        if post or ts < t or ts >= start:
            continue
        if price >= ask + trade_through - 1e-9:
            return price, min(FILL_CAP, size)
    return None


def m2_quotes(u: dict, data: dict, *, offset: float = ASK_OFFSET, trade_through: float = TRADE_THROUGH) -> list[dict]:
    q = []
    for j, mid in enumerate(u["mids"]):
        a = min(c12.ceil_tick(float(u["p"][j]) + offset), c12.PRICE_CAP)
        f = fill_member(a, data["tx"].get(mid, []), u["t"], u["start"], trade_through) if u["src_ok"][j] else None
        q.append({"j": j, "mid": mid, "ask": a, "src_ok": bool(u["src_ok"][j]), "fill": f})
    return q


def event_values(units: list[dict], data: dict, *, offset: float = ASK_OFFSET, trade_through: float = TRADE_THROUGH, y_key: str = "y", reach_worst: bool = False,
                 fill_price_override: dict | None = None) -> dict:
    """Per-event M2 values. An event with < 90% of its listed members source-available is excluded (counted) unless ``reach_worst`` (those events are kept and every
    source-unavailable member gets the maker's worst-case fill: 100 shares at the ask iff Y > 0). Returns the units with fills, the event values (net per filled share,
    share-weighted), and the route sums."""
    vals, kept, n_excl = [], [], 0
    fills_total = intended = 0
    route_num = 0.0
    no_fill = 0
    for u in units:
        if u["status"] != "ok":
            continue
        if not reach_worst and u["n_listed"] and u["n_src_listed"] / u["n_listed"] < AVAIL_MIN_SHARE:
            n_excl += 1
            continue
        q = m2_quotes(u, data, offset=offset, trade_through=trade_through)
        num_, den_ = 0.0, 0.0
        for k in q:
            y = float(u[y_key][k["j"]])
            if k["src_ok"]:
                intended += 1
                if k["fill"] is not None:
                    size = k["fill"][1]
                    net = k["ask"] - y
                    num_ += size * net
                    den_ += size
                    route_num += size * net
                    fills_total += 1
            elif reach_worst and y > 0:
                intended += 1
                num_ += FILL_CAP * (k["ask"] - 1.0)
                den_ += FILL_CAP
                route_num += FILL_CAP * (k["ask"] - 1.0)
                fills_total += 1
            elif reach_worst:
                intended += 1
        if den_ > 0:
            vals.append(num_ / den_)
            kept.append(u)
        else:
            no_fill += 1
    return {"units": kept, "values": np.array(vals, float), "excluded_source": n_excl, "no_fill_events": no_fill, "fills": fills_total, "intended": intended,
            "route": route_num / (FILL_CAP * intended) if intended else math.nan}


def m2_fill_placebo(units: list[dict], data: dict, *, n_draws: int = c12.PLACEBO_DRAWS, seed: int = c12.PLACEBO_SEEDS["M2_fill_calibrated"]) -> dict:
    """Binding placebo: Y* calibrated to the FILL-TIME price of the filling transaction (copula), same fills; judged on p < 0.01 alone."""
    recs = []
    for i, u in enumerate(units):
        if u["status"] != "ok":
            continue
        if u["n_listed"] and u["n_src_listed"] / u["n_listed"] < AVAIL_MIN_SHARE:
            continue
        for k in m2_quotes(u, data):
            if k["fill"] is not None:
                recs.append((i, u["speaker"], k["ask"], k["fill"][0], k["fill"][1]))
    if not recs:
        return {"n_draws": 0, "n_advance": 0, "advance_rate": 1.0, "holds": False, "note": "no fills"}
    ev_ids = sorted({r[0] for r in recs})
    ev_map = {e: j for j, e in enumerate(ev_ids)}
    sp_map: dict[str, int] = {}
    ev_idx = np.array([ev_map[r[0]] for r in recs])
    sp_idx = np.array([sp_map.setdefault(r[1], len(sp_map)) for r in recs])
    ask = np.array([r[2] for r in recs])
    fp = np.array([r[3] for r in recs])
    sz = np.array([r[4] for r in recs])
    cl = {"speaker": [units[e]["speaker"] for e in ev_ids], "week": [units[e]["week"] for e in ev_ids]}
    rng = np.random.default_rng(seed)
    ps = []
    for _ in range(n_draws):
        y = copula_flat(np.clip(fp, 0.0, 1.0), ev_idx, sp_idx, rng)
        num_ = np.bincount(ev_idx, weights=sz * (ask - y), minlength=len(ev_ids))
        den_ = np.bincount(ev_idx, weights=sz, minlength=len(ev_ids))
        ps.append(c12.cluster_p(num_ / den_, cl, alpha=c12.GATE_P)["p"])
    return {**c12.placebo_advance_rate(ps), "note": "M2 fill-time calibrated copula placebo", "seed": seed}


def m2_reported(units: list[dict], base: dict, v: np.ndarray, *, taker_fee: float = TAKER_FEE) -> dict:
    """Uncounted: capacity (filled shares per event), the event-level loss distribution (the risk is a long speech) and the taker version (buy NO on each member at
    ``1 - p + 1.5c`` plus fee ``0.04 a (1 - a)``, held to resolution, mean of the events' member means)."""
    cap = [sum(k["fill"][1] for k in m2_quotes(u, base["data"]) if k["fill"] is not None) for u in base["units"]] if "data" in base else []
    taker = []
    for u in units:
        if u["status"] != "ok":
            continue
        a = np.minimum(1.0 - u["p"] + ASK_OFFSET, c12.PRICE_CAP)
        taker.append(float(np.mean((1.0 - u["y"]) - a - taker_fee * a * (1.0 - a))))
    return {"capacity_filled_shares_per_event_mean": float(np.mean(cap)) if cap else None, "loss_quantiles": [float(x) for x in np.quantile(v, [0.01, 0.05, 0.5])] if len(v) else [],
            "taker_basket_net_per_share_mean": float(np.mean(taker)) if taker else None}


def m2_test(units: list[dict], data: dict, *, placebo: bool = True, n_draws: int = c12.PLACEBO_DRAWS) -> dict:
    base = event_values(units, data)
    base["data"] = data
    v, us = base["values"], base["units"]
    res: dict = {"test": "M2", "label": LABEL_M, "n": int(len(v)), "n_events_with_fill": int(len(v)), "no_fill_events": base["no_fill_events"], "excluded_source": base["excluded_source"],
                 "fills": base["fills"], "intended_quotes": base["intended"], "net_per_filled_share": float(v.mean()) if len(v) else math.nan, "route_net_per_intended_share": base["route"],
                 "effect": float(v.mean()) if len(v) else math.nan}
    if len(v) < c12.MIN_UNITS:
        return {**res, "p": 1.0, "testable": False, "advance": False, "verdict": "not testable (units)"}
    cl = {"speaker": [u["speaker"] for u in us], "week": [u["week"] for u in us]}
    cp = c12.cluster_p(v, cl)
    floor_ok = bool(v.mean() >= M2_FLOOR and base["route"] > 0)
    res.update(p=cp["p"], testable=cp["testable"], ways=cp["ways"], floor_ok=floor_ok)
    if not cp["testable"]:
        return {**res, "advance": False, "verdict": "not testable (clusters)"}
    rob: dict = {}
    q10 = event_values(units, data, offset=ASK_OFFSET_ROBUST)
    rob["quote_plus_1.0c_net_positive"] = bool(len(q10["values"]) and q10["values"].mean() > 0)
    t2 = event_values(units, data, trade_through=TRADE_THROUGH_ROBUST)
    rob["trade_through_2c_net_positive"] = bool(len(t2["values"]) and t2["values"].mean() > 0)
    for way in ("speaker", "week"):
        keep = c12.top_k_drop_mask(v, [u[way] for u in us], c12.TOP_DROP)
        sub = v[keep]
        if len(sub) >= c12.MIN_UNITS:
            c2 = c12.cluster_p(sub, {"speaker": [u["speaker"] for u, k in zip(us, keep, strict=True) if k], "week": [u["week"] for u, k in zip(us, keep, strict=True) if k]})
            rob[f"top5_{way}_drop"] = bool(c2["testable"] and c2["p"] < c12.GATE_P and sub.mean() >= M2_FLOOR)
        else:
            rob[f"top5_{way}_drop"] = False
    ne = [u for u in units if not (u["start_edit_a"] or u["start_edit_b"] or u.get("start_edit_c"))]
    ev_ne = event_values(ne, data)
    if len(ev_ne["values"]) >= c12.MIN_UNITS:
        c3 = c12.cluster_p(ev_ne["values"], {"speaker": [u["speaker"] for u in ev_ne["units"]], "week": [u["week"] for u in ev_ne["units"]]})
        rob["start_edit_excluded"] = bool(c3["testable"] and c3["p"] < c12.GATE_P and ev_ne["values"].mean() >= M2_FLOOR)
    else:
        rob["start_edit_excluded"] = False
    wc = event_values(units, data, y_key="y_wc")
    rob["worst_case_unclean_net_positive"] = bool(len(wc["values"]) and wc["values"].mean() > 0)
    rw = event_values(units, data, y_key="y_wc", reach_worst=True)
    if len(rw["values"]) >= c12.MIN_UNITS:
        c4 = c12.cluster_p(rw["values"], {"speaker": [u["speaker"] for u in rw["units"]], "week": [u["week"] for u in rw["units"]]})
        rob["worst_case_reach"] = bool(c4["testable"] and c4["p"] < c12.GATE_P and rw["values"].mean() >= M2_FLOOR and rw["route"] > 0)
    else:
        rob["worst_case_reach"] = False
    plc = m2_fill_placebo(units, data, n_draws=n_draws) if placebo else None
    rob_ok = all(x is True for x in rob.values())
    res.update(robustness=rob, robustness_ok=rob_ok, placebo=plc)
    res["reported"] = m2_reported(units, base, v)
    ok = bool(cp["p"] < c12.GATE_P and floor_ok and rob_ok and (plc is None or plc["holds"]))
    res.update(stage1_pass=ok, early_holm_ok=c12.early_stage1_ok(cp["p"]), advance=bool(ok and c12.early_stage1_ok(cp["p"])), holm_pending=bool(ok and not c12.early_stage1_ok(cp["p"])))
    res["verdict"] = "advance (early Holm)" if res["advance"] else ("pending the full step-down (p in [0.005, 0.01))" if res["holm_pending"] else "no advance")
    return res


# =====================================================================================================================================================
# Census (counts and features only; no outcome, D, fill or net)
# =====================================================================================================================================================


def census_m(rdir: Path, *, frame_dir: Path | None = None, n_draws: int = c12.GMP_DRAWS, seed: int = c12.SEED_GMP) -> dict:
    """q0249 (M part). SCREEN files only (HOLDOUT counts come from the frame report). The prices at ``t`` and the member counts are features; the outcome files are never
    opened and no D, fill or net is computed here."""
    rdir = Path(rdir)
    data = load_split(rdir, "screen", job="census")
    evs = list(data["events"].values())
    report = json.loads((rdir / "frame_report.json").read_text())
    by_status = Counter(e["status"] for e in evs)
    per_month = Counter(datetime.fromtimestamp(float(e["end_epoch"]), UTC).strftime("%Y-%m") for e in evs)
    dur = np.array([float(e["end_epoch"]) - float(e["start_epoch"]) for e in evs if e["start_epoch"] not in ("", "nan")], float)
    deciles = [float(x) for x in np.quantile(dur, np.linspace(0, 1, 11))] if len(dur) else []
    units = build_units(data)
    ok = ok_units(units)
    status = Counter(u["status"] for u in units)
    listed_members = sum(u["n_listed"] for u in units)
    with_price = sum(u.get("n_with_price", 0) for u in units if u["status"] in ("ok", "unavailable (no price)"))
    cover_price = with_price / listed_members if listed_members else 0.0
    src_listed = sum(u.get("n_src_listed", 0) for u in ok)
    ok_listed = sum(u["n_listed"] for u in ok)
    cover_reach = src_listed / ok_listed if ok_listed else 0.0
    speakers = {u["speaker"] for u in ok}
    weeks = {u["week"] for u in ok}
    gm = {"events": len(ok), "speakers": len(speakers), "weeks": len(weeks), "min": GM_MIN, "pass": bool(len(ok) >= GM_MIN["events"] and len(speakers) >= GM_MIN["speakers"] and len(weeks) >= GM_MIN["weeks"])}
    cov = {"price_at_t_share": cover_price, "print_reach_share": cover_reach, "min": COVER_MIN, "pass": bool(cover_price >= COVER_MIN and cover_reach >= COVER_MIN)}
    s_vals = [float(u["p"].sum()) for u in ok]
    out = {"version": "cb12-census-M-v1", "counts_only": True, "label": LABEL_M, "events_by_status": dict(by_status), "events_by_month": dict(sorted(per_month.items())),
           "duration_deciles_s": deciles, "unit_status": dict(status), "frame_report": report, "n_members_listed": listed_members, "speaker_keys": len(speakers), "iso_weeks": len(weeks),
           "S_t_quantiles": [float(x) for x in np.quantile(s_vals, [0.1, 0.5, 0.9])] if s_vals else [], "late_members_dropped": sum(u["n_late"] for u in units),
           "GM": gm, "coverage_audit": cov}
    mde = gmp(ok, n_draws=n_draws, seed=seed) if gm["pass"] and cov["pass"] and len(ok) >= 2 else {"pass": False, "note": "not computed (GM or coverage failed)"}
    out["GMP"] = mde
    if not gm["pass"]:
        out["label_M"] = "not testable (events)"
    elif not cov["pass"]:
        out["label_M"] = "not testable (coverage)"
    elif not mde["pass"]:
        out["label_M"] = "not run (power)"
    else:
        out["label_M"] = None
    return out


def gmp(us: list[dict], *, n_draws: int = c12.GMP_DRAWS, seed: int = c12.SEED_GMP) -> dict:
    """Feature-only power gate: simulated outcomes from the prices with the copula; ``MDE_M1 = (z_.99 + z_.80) x 1.2 x max(SD(D-bar*), mean speaker-way SE, mean week-way SE)``."""
    p, ev, sp = flat_index(us)
    rng = np.random.default_rng(seed)
    sp_cl = [u["speaker"] for u in us]
    wk_cl = [u["week"] for u in us]
    dbars, se_sp, se_wk = [], [], []
    for _ in range(n_draws):
        y = copula_flat(p, ev, sp, rng)
        D = np.bincount(ev, weights=p - y, minlength=len(us))
        dbars.append(float(D.mean()))
        se_sp.append(c12.cluster_se_mean(D, sp_cl))
        se_wk.append(c12.cluster_se_mean(D, wk_cl))
    m = c12.mde(max(float(np.std(dbars, ddof=1)), float(np.nanmean(se_sp)), float(np.nanmean(se_wk))))
    return {"MDE_M1_words": m, "sd_dbar": float(np.std(dbars, ddof=1)), "mean_se_speaker": float(np.nanmean(se_sp)), "mean_se_week": float(np.nanmean(se_wk)), "max_mde": GMP_MDE_MAX,
            "draws": n_draws, "seed": seed, "pass": bool(m <= GMP_MDE_MAX)}


# =====================================================================================================================================================
# Screen and rep
# =====================================================================================================================================================


def not_run_result(label: str) -> dict:
    return {"p": 1.0, "testable": False, "advance": False, "verdict": label, "label": LABEL_M, "effect": None, "n": 0}


def screen_m(rdir: Path, census: dict) -> dict:
    """q0252: M1 and M2 on SCREEN events. Opens only ``outcomes_guarded_screen.csv.gz`` (every holdout path is refused)."""
    lab = census.get("label_M")
    if lab:
        return {"M1": not_run_result(lab), "M2": not_run_result(lab), "label": LABEL_M, "census_label": lab}
    data = load_split(rdir, "screen", job="screen-M")
    outs = c12.open_guarded(Path(rdir) / "outcomes_guarded_screen.csv.gz", "screen-M")
    units = attach_outcomes(build_units(data), outs)
    u24 = attach_outcomes(build_units(data, origin_s=ORIGIN_ALT_S), outs)
    return {"M1": m1_test(units, data, units_t24=u24), "M2": m2_test(units, data), "label": LABEL_M, "census_label": None}


def rep_m(rdir: Path, census: dict, tests: tuple[str, ...], seal: dict, *, k2: int | None = None) -> dict:
    """q0256: the advanced test(s) on the sealed HOLDOUT, same rules. Judged against alpha / 10 while k2 is unknown (``early_stage2_ok``)."""
    data = load_split(rdir, "holdout", job="rep-M")
    outs = c12.open_guarded(Path(rdir) / "holdout" / "outcomes_guarded_holdout.csv.gz", "rep-M", seal)
    units = attach_outcomes(build_units(data), outs)
    out: dict = {"label": LABEL_M, "k2": k2}
    for t in tests:
        r = m1_test(units, data) if t == "M1" else m2_test(units, data)
        r["stage2_early_alpha_over_10"] = c12.early_stage2_ok(r.get("p"))
        r["stage2_pass_alpha_over_k"] = bool(r.get("p", 1.0) <= (c12.STAGE_ALPHA / k2 if k2 else c12.STAGE_ALPHA / c12.STAGE2_K_MAX) and r.get("floor_ok") and r.get("robustness_ok")
                                             and (r.get("placebo") or {}).get("holds", False))
        out[f"{t}_rep"] = r
    return out


# =====================================================================================================================================================
# Smoke (family checks), seal rows, declared
# =====================================================================================================================================================


def smoke_offline(ctx: dict) -> dict:
    """Guard fixtures (no network): HOLDOUT path refusals, the SCREEN job refusing the HOLDOUT outcome file, cross_venue_live, sports exclusion, occasion rule."""
    import tempfile  # noqa: PLC0415

    res = []
    for fn in (lambda: c12.guard_screen_path(Path("x/h12_say/holdout/events.csv.gz")), lambda: c12.refuse_path(Path("x/cross_venue_live/a.npz")),
               lambda: c12.require_output_root(Path("x/creative_batch11/a"))):
        try:
            fn()
            res.append(False)
        except Refused:
            res.append(True)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "holdout" / "outcomes_guarded_holdout.csv.gz"
        p.parent.mkdir(parents=True)
        p.write_bytes(hb._gz_csv_bytes(OUTCOME_COLUMNS, []))
        try:
            c12.open_guarded(p, "screen-M")
            res.append(False)
        except Refused:
            res.append(True)
    sp1 = is_sports([{"id": 1, "slug": "x"}], "What will A say?") == (True, False)
    sp2 = is_sports([], "What will the announcers say during the game?") == (False, True)
    sp3 = is_sports([{"id": 5, "slug": "politics"}], "What will Trump say at the rally?") == (False, False)
    ev = parse_event({"id": "1", "title": "t", "startTime": "2026-01-01T12:00:00Z", "endDate": "2026-01-03T00:00:00Z", "markets": []})
    ev2 = parse_event({"id": "2", "title": "t", "startTime": "2026-01-01T12:00:00Z", "endDate": "2026-01-03T00:00:01Z", "markets": []})
    occ = bool(ev and ev[0]["occasion"] == 1 and ev2 and ev2[0]["occasion"] == 0)
    ok = bool(all(res) and sp1 and sp2 and sp3 and occ)
    return {"guards_fixture_M": {"pass": ok, "refusals": res, "sports_fixtures": [sp1, sp2, sp3], "occasion_boundary": occ}}


def smoke_online(lim, ctx: dict) -> dict:
    """Tag 100343 paging on two out-of-window weeks (2025-05) stable on repeat with ``startTime``; ``prices-history`` with explicit bounds and the Data API newest-first reach
    on two out-of-window members. Counts and booleans only."""
    per, picks = {}, []
    ok_paging = True
    for a, b in SMOKE_WEEKS:
        pages = []
        for _ in range(2):
            st, data = lim.get(c12.GAMMA_EVENTS, {"closed": "true", "tag_id": TAG_ID, "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true", "limit": 100, "offset": 0})
            pages.append((st, data if isinstance(data, list) else []))
        ids1 = [str(e.get("id")) for e in pages[0][1] if isinstance(e, dict)]
        ids2 = [str(e.get("id")) for e in pages[1][1] if isinstance(e, dict)]
        with_start = sum(1 for e in pages[0][1] if isinstance(e, dict) and e.get("startTime"))
        good = bool(pages[0][0] == 200 and pages[1][0] == 200 and 0 < len(ids1) <= 100 and ids1 == ids2 and with_start > 0)
        per[a[:10]] = {"n_first": len(ids1), "n_repeat": len(ids2), "stable": ids1 == ids2, "n_with_startTime": with_start, "ok": good}
        ok_paging = ok_paging and good
        for e in pages[0][1]:
            if not isinstance(e, dict) or len(picks) >= 2:
                continue
            row = parse_event(e)
            if row and row[1] and math.isfinite(row[0]["start_epoch"]) and row[1][0]["condition_id"]:
                picks.append({"token": row[1][0]["token_yes"], "cid": row[1][0]["condition_id"], "start": row[0]["start_epoch"], "yes_index": row[1][0]["yes_index"]})
    ph, da = {}, {}
    for i, pk in enumerate(picks):
        st, data = lim.get(hb.CLOB_PRICES, {"market": pk["token"], "startTs": int(pk["start"] - FETCH_BEFORE_S), "endTs": int(pk["start"]), "fidelity": FIDELITY})
        pts = (data or {}).get("history") if st == 200 and isinstance(data, dict) else None
        ph[f"m{i}"] = {"status": st, "n_points": len(pts or []), "ok": bool(st == 200 and pts)}
        rows, info = c12.fetch_prints_paged(lim, pk["cid"], pk["start"] - ORIGIN_ALT_S)
        da[f"m{i}"] = {"pages": info["pages"], "n_prints": info["n_prints"], "truncated": bool(info["truncated"]), "reach_t24": c12.reach_ok(info, pk["start"] - ORIGIN_ALT_S), "ok": True}
    return {"m_gamma_paging": {"pass": bool(ok_paging and len(picks) >= 2), "per": per, "picked": len(picks)},
            "m_prices_history": {"pass": bool(len(ph) >= 2 and all(v["ok"] for v in ph.values())), "per": ph},
            "m_data_api_reach": {"pass": bool(len(da) >= 2 and all(v["ok"] for v in da.values())), "per": da, "note": "reach recorded; the census coverage audit decides"}}


def seal_rows(rdir: Path) -> list[dict]:
    """Rows (market_id, event_ids) of the HOLDOUT members of kept events, for the seal-time drops."""
    base = Path(rdir) / "holdout"
    kept = {r["event_id"] for r in c12.read_csv_gz(base / "events.csv.gz") if r["status"] == "kept"}
    return [{"market_id": r["market_id"], "event_ids": r["event_id"]} for r in c12.read_csv_gz(base / "members.csv.gz") if r["event_id"] in kept]


def declared() -> dict:
    return {"tag_id": TAG_ID, "windows": {"screen": list(M_SCREEN), "holdout": list(M_HOLD)}, "origins_s": [ORIGIN_S, ORIGIN_ALT_S], "occasion_max_h": OCCASION_MAX_S / HOUR,
            "min_members": MIN_MEMBERS, "availability_min": AVAIL_MIN_SHARE, "listing_buffer_h": LIST_BUFFER_S / HOUR, "fidelity": FIDELITY,
            "m1": {"floor_words": M1_FLOOR_WORDS, "floor_share": M1_FLOOR_SHARE, "bid_proxy": BID_PROXY, "placebo": "copula, seed 12101, 200 draws"},
            "m2": {"ask": "ceil_tick(p + 1.5c) at 1c, cap 0.99", "fill": "first transaction in [t, startTime) with YES-terms price >= ask + 1c; size min(100, tx size)",
                   "floor": "net >= 0.5c per filled share and route net > 0", "robustness": "quote +1.0c; trade-through 2c; top-5; start_edit; worst-case unclean; worst-case reach",
                   "placebo": "fill-time calibrated copula, seed 12102"},
            "copula": {"loadings": list(COPULA_LOADINGS), "gmp_seed": c12.SEED_GMP, "gmp_draws": c12.GMP_DRAWS, "mde_max_words": GMP_MDE_MAX},
            "gates": {"GM": GM_MIN, "coverage_min": COVER_MIN}, "sports": {"in_primary": c12.CB12_SPORTS_IN_PRIMARY, "tag_slugs": list(SPORTS_TAG_SLUGS), "tag_ids": list(SPORTS_TAG_IDS),
                                                                         "broadcast_regex": BROADCAST_RE.pattern},
            "key_rule": "market id, event id, series-date key (needs exclusion_series_dates.csv.gz; else the full-series counterfactual is only counted)",
            "stage1": "p < 0.01, floors, binding placebo, robustness, early Holm at alpha / 10 = 0.005 (full step-down at the batch end can add advances)",
            "outcomes": "guarded SCREEN and HOLDOUT files (separate); unclean members 0.5 (worst case 1)", "label": LABEL_M}
