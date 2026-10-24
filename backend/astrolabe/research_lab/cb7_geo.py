# ruff: noqa: E501
"""CB7-G fetch side: the ``h8_geo`` census (q0143) (docs/research_lab/CREATIVE_BATCH_7.md CB7-G "Data", "Population", "Origins").

Order, declared in section CB7-G: (1) walk the geopolitics tag in monthly ``end_date`` windows (halved while capped), the FULL
walked frame is kept (``frame.csv.gz``: all tag ids, event title, ``fee_category``, ``closed_time`` as a status field);
(2) the filters; (3) the exclusion id / key drop; (4) the per-event cap (8); (5) origins ``end_at - {30, 14, 7} d``
(``origins.csv.gz`` is written before any request); (6) ONE windowed taker-print request per origin (price and eligibility;
no CLOB history); (7) tables and manifest. Seal drops (h8_tail, h7) come after, at seal.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as cm
from . import cb7_text as ct
from . import history_backfill as hb

Refused, NotNow, DAY = cm.Refused, cm.NotNow, cm.DAY

STATUS_QUO_PATTERNS = (r"\bnot\b", r"\bremain\w*", r"\bstill\b", r"\bstay\w*", r"\bsurviv\w*", r"\bcontinu\w*", r"\bwithout\b")
THEME_PATTERNS = (
    ("ru-ua", r"\b(?:russia|russian|ukrain\w*|putin|zelensky|kyiv|kremlin|crimea|donbas)\b"),
    ("il-ps", r"\b(?:israel\w*|gaza|hamas|netanyahu|west bank|hostage\w*)\b"),
    ("iran", r"\b(?:iran\w*|khamenei|tehran|hormuz)\b"),
    ("lb-sy-ye", r"\b(?:hezbollah|lebanon|syria\w*|assad|houthi\w*|yemen\w*)\b"),
    ("cn-tw", r"\b(?:china|chinese|taiwan\w*|xi jinping|beijing)\b"),
    ("kp", r"\b(?:north korea\w*|kim jong)\b"),
    ("ve", r"\b(?:venezuela\w*|maduro)\b"),
    ("in-pk", r"\b(?:india\w*|pakistan\w*|kashmir)\b"),
)
GEO_FILTER_ORDER = ("no_created_or_end", "end_outside_window", "not_yes_no", "life_lt_9d", "other_placeholder", "continuous_class",
                    "status_quo", "exclusion_id", "exclusion_key", "event_cap")
_STATUS_QUO_RX = [re.compile(p) for p in STATUS_QUO_PATTERNS]
_THEME_RX = [(n, re.compile(p)) for n, p in THEME_PATTERNS]
SAMPLE_COLUMNS = cm.MAIN_COLUMNS
CAPPED_COLUMNS = ["market_id", "event_key"]


# ---- deterministic rules (SOURCE hashed into the rules file) -------------------------------------------------------------------


def geo_filter_reason(r: dict, cutoff_epoch: float, end_lo: float) -> str | None:
    """First declared filter that rejects a frame row (before the exclusion id / key tests and the cap), else ``None``."""
    created = cm._parse_ts(r.get("created_at"))
    try:
        end = float(r.get("end_epoch"))
    except (TypeError, ValueError):
        end = float("nan")
    if created is None or end != end:
        return "no_created_or_end"
    if not (end_lo <= end <= cutoff_epoch):
        return "end_outside_window"
    if not cm.binary_yes_no(r.get("outcomes")):
        return "not_yes_no"
    if end - created < cm.GEO_MIN_LIFE_DAYS * DAY:
        return "life_lt_9d"
    if cm.is_other_placeholder(r):
        return "other_placeholder"
    if cm.is_continuous_question(r.get("question", "")):
        return "continuous_class"
    q = (r.get("question") or "").lower()
    if any(rx.search(q) for rx in _STATUS_QUO_RX):
        return "status_quo"
    return None


def geo_origins(created_epoch: float, end_epoch: float) -> list[tuple[int, int]]:
    """``(k, t_k)`` for k in {30, 14, 7} with ``t_k = end - k d``, kept iff ``t_k >= created + 2 d``. Uses dates only."""
    out = []
    for k in cm.GEO_ORIGIN_DAYS:
        t = end_epoch - k * DAY
        if t >= created_epoch + cm.GEO_MIN_AGE_AT_ORIGIN_DAYS * DAY:
            out.append((k, int(t)))
    return out


def theme_of(question: str, event_title: str) -> str:
    """First matching theme over the lower-cased question and event title; no match -> empty (its own cluster)."""
    text = f"{question or ''} {event_title or ''}".lower()
    for name, rx in _THEME_RX:
        if rx.search(text):
            return name
    return ""


def split_window(a: int, b: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Halve ``[a, b)`` (epoch seconds) at the integer midpoint."""
    mid = a + (b - a) // 2
    return (a, mid), (mid, b)


# ---- tag walk -----------------------------------------------------------------------------------------------------------------------


def month_windows(end_from: float, cutoff: float) -> list[tuple[str, int, int]]:
    """Monthly ``end_date`` windows ``[start, next start)`` from ``end_from`` to ``cutoff`` (the last one truncated)."""
    d = datetime.fromtimestamp(end_from, UTC)
    out = []
    while d.timestamp() <= cutoff:
        nxt = datetime(d.year + (d.month == 12), d.month % 12 + 1, 1, tzinfo=UTC)
        out.append((f"{d:%Y-%m}", int(d.timestamp()), int(min(nxt.timestamp(), cutoff + 1))))
        d = nxt
    return out


def _walk_window(lim: hb.Limiter, tag_id: str, closed: bool, a: int, b: int, acc: dict) -> None:
    """One ``[a, b)`` window for one mode; halved while capped; capped at one day -> excluded and counted."""
    f = "%Y-%m-%dT%H:%M:%SZ"
    p = {"tag_id": tag_id, "order": "id", "ascending": "true", "closed": "true" if closed else "false",
         "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f)}
    batch, capped, failed = c4._paged_strict(lim, p, hb.GAMMA_OFFSET_CAP)
    kind = "closed" if closed else "active"
    if failed:
        acc["failed_windows"] += 1
        return
    if capped and b - a > DAY:
        acc["splits"] += 1
        for lo, hi in split_window(a, b):
            _walk_window(lim, tag_id, closed, lo, hi, acc)
        return
    acc["windows"][kind] += 1
    if capped:
        acc["excluded_capped_at_one_day"][kind] += 1
        acc["rows_in_excluded_windows"] += len(batch)
        return
    acc["batches"].extend(batch)


def walk_geo_frame(fr: cm.Cb7Run, windows: list[tuple[str, int, int]], tag_id: str, *, should_stop: Callable[[], bool] | None = None
                   ) -> str | None:
    """Per monthly window, ``closed=true`` then ``closed=false`` (ended-unclosed, censored). One gzip member per month in
    ``frame_partial.jsonl.gz``; a month with a failed request is retried by the next chunk (at most ``MAX_DAY_ATTEMPTS``)."""
    rdir = fr.rdir
    pp, pf = rdir / "frame_partial.jsonl.gz", rdir / "frame_fail.jsonl"
    done: set[str] = set()
    seen: set[str] = set()
    for rec in c6.iter_partial(pp):
        done.add(rec["day"])
        seen.update(r["market_id"] for r in rec["rows"])
    fails = cm.walk_failed_days(pf)
    for label, a, b in windows:
        if label in done:
            continue
        if should_stop is not None and should_stop():
            return "frame_paused"
        acc = {"batches": [], "windows": {"closed": 0, "active": 0}, "excluded_capped_at_one_day": {"closed": 0, "active": 0},
               "rows_in_excluded_windows": 0, "splits": 0, "failed_windows": 0}
        for closed in (True, False):
            _walk_window(fr.lim, tag_id, closed, a, b, acc)
        if acc["failed_windows"] and fails.get(label, 0) + 1 < cm.MAX_DAY_ATTEMPTS:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": label, "failed_windows": acc["failed_windows"]}) + "\n")
            return f"walk_failed_window: {label}"
        rows, outs = [], []
        raw = invalid = dups = 0
        month_seen: set[str] = set()
        for m in acc["batches"]:
            raw += 1
            pr = cm.market_row(m, fr.cap_epoch)
            if pr is None:
                invalid += 1
                continue
            mid = pr[0]["market_id"]
            if mid in seen or mid in month_seen:
                dups += 1
                continue
            month_seen.add(mid)
            pr[0]["query_tag_id"] = tag_id
            rows.append(pr[0])
            outs.append(pr[1])
        cm.append_member(fr, pp, {"day": label, "rows": rows, "outs": outs, "windows": acc["windows"],
                                  "dropped": acc["excluded_capped_at_one_day"], "dropped_rows": acc["rows_in_excluded_windows"],
                                  "splits": acc["splits"], "raw": raw, "invalid": invalid, "dups": dups,
                                  "failed_windows": acc["failed_windows"]})
        seen.update(month_seen)
    return None


def build_geo_outputs(fr: cm.Cb7Run, *, cutoff_epoch: float, end_from_epoch: float, excl_ids: set[str],
                      excl_keys: dict[str, set[str]], t_fetch: float) -> dict:
    """Stream ``frame_partial.jsonl.gz``: ``frame.csv.gz`` (every walked row, unfiltered) -> filters -> exclusion id / key drop ->
    per-event cap (8) -> origins. ``origins.csv.gz`` is written before ``sample.csv.gz`` and before any print request; outcome
    columns go only to ``outcomes_guarded.csv.gz``; ``frame_report.json`` is written last."""
    rdir = fr.rdir
    pp = rdir / "frame_partial.jsonl.gz"
    counts: dict = {"frame_rows": 0, "filter_dropped": {}, "exclusion_id_dropped": 0, "exclusion_key_dropped": 0,
                    "kept_before_cap": 0, "capped_out": 0, "closed_after_cap_in_frame": 0}
    key_drops = {"by_type_any_match": dict.fromkeys(cm.KEY_TYPES, 0), "by_type_combo": {}, "rows": 0}
    walk = {"windows": {"closed": 0, "active": 0}, "excluded_capped_at_one_day": {"closed": 0, "active": 0}, "splits": 0,
            "rows_in_excluded_windows": 0, "windows_failed": 0, "months": 0, "raw": 0, "non_binary_or_invalid": 0,
            "duplicates": 0, "months_with_failed_windows": []}
    kept: list[dict] = []

    def rows_pass1() -> Iterator[list]:
        for rec in c6.iter_partial(pp):
            walk["months"] += 1
            for k in ("closed", "active"):
                walk["windows"][k] += rec["windows"][k]
                walk["excluded_capped_at_one_day"][k] += rec["dropped"][k]
            walk["rows_in_excluded_windows"] += rec["dropped_rows"]
            walk["splits"] += rec.get("splits", 0)
            if rec.get("failed_windows"):
                walk["windows_failed"] += rec["failed_windows"]
                walk["months_with_failed_windows"].append(rec["day"])
            walk["raw"] += rec["raw"]
            walk["non_binary_or_invalid"] += rec["invalid"]
            walk["duplicates"] += rec["dups"]
            for r in rec["rows"]:
                counts["frame_rows"] += 1
                counts["closed_after_cap_in_frame"] += int(int(r["closed_after_cap"]) == 1)
                yield [r.get(c, "") for c in cm.MAIN_COLUMNS]
                why = geo_filter_reason(r, cutoff_epoch, end_from_epoch)
                if why:
                    counts["filter_dropped"][why] = counts["filter_dropped"].get(why, 0) + 1
                    continue
                if r["market_id"] in excl_ids:
                    counts["exclusion_id_dropped"] += 1
                    continue
                kt = cm.key_types_matched(r, excl_keys)
                if kt:
                    counts["exclusion_key_dropped"] += 1
                    key_drops["rows"] += 1
                    for t in kt:
                        key_drops["by_type_any_match"][t] += 1
                    combo = "+".join(kt)
                    key_drops["by_type_combo"][combo] = key_drops["by_type_combo"].get(combo, 0) + 1
                    continue
                kept.append({"market_id": r["market_id"], "event_ids": r["event_ids"], "event_id": r["event_id"],
                             "created": cm._parse_ts(r["created_at"]), "end_epoch": float(r["end_epoch"])})

    fr.budget.write_gz_csv(rdir / "frame.csv.gz", cm.MAIN_COLUMNS, rows_pass1())
    counts["kept_before_cap"] = len(kept)
    keep_ids, capped_ids = cm.draw_geo_cap(kept)  # AFTER the filters and the key drop
    counts["capped_out"] = len(capped_ids)
    ev_key = {r["market_id"]: ((str(r["event_ids"]).split(";")[0] or str(r["event_id"])) or f"m{r['market_id']}") for r in kept}
    fr.budget.write_gz_csv(rdir / "capped.csv.gz", CAPPED_COLUMNS, ([m, ev_key[m]] for m in sorted(capped_ids)))
    origins: list[list] = []
    no_origin = 0
    for r in sorted(kept, key=lambda x: x["market_id"]):
        if r["market_id"] not in keep_ids:
            continue
        os_ = geo_origins(r["created"], r["end_epoch"])
        if not os_:
            no_origin += 1
        origins.extend([r["market_id"], t, cm._iso(t), k] for k, t in os_)
    fr.budget.write_gz_csv(rdir / "origins.csv.gz", cm.ORIGIN_COLUMNS, origins)  # before sample.csv.gz and any print request
    kept.clear()
    final_ids = set(keep_ids)
    picked: dict[str, tuple[dict, dict]] = {}
    for rec in c6.iter_partial(pp):
        outs = {o["market_id"]: o for o in rec["outs"]}
        for r in rec["rows"]:
            if r["market_id"] in final_ids:
                picked[r["market_id"]] = (r, outs[r["market_id"]])
    ids = sorted(picked)
    fr.budget.write_gz_csv(rdir / cm.OUTCOME_FILE, cm.GUARDED_COLUMNS, ([picked[m][1].get(c, "") for c in cm.GUARDED_COLUMNS] for m in ids))
    fr.budget.write_gz_csv(rdir / "sample.csv.gz", SAMPLE_COLUMNS, ([picked[m][0].get(c, "") for c in SAMPLE_COLUMNS] for m in ids))
    kd = {"exclusion_key_types": list(cm.KEY_TYPES), **key_drops}
    fr.budget.write(rdir / "key_drops.json", json.dumps(kd, indent=1, sort_keys=True).encode())
    report = {"frame_version": hb.FRAME_VERSION, "t_fetch_geo": cm._iso(t_fetch), "end_cutoff": cm._iso(cutoff_epoch),
              "cap_utc": cm._iso(fr.cap_epoch), "tag_id": cm.GEO_TAG_ID, **walk, **counts, "n_markets": len(ids),
              "n_markets_without_origin": no_origin, "n_origins": len(origins), "max_per_event": cm.MAX_PER_EVENT, "key_drops": kd,
              "outcomes_censored_post_cap": sum(1 for m in ids if int(picked[m][0]["closed_after_cap"]) == 1)}
    fr.budget.write(rdir / "frame_report.json", json.dumps(report, indent=1, sort_keys=True, default=float).encode())
    for tmp in (pp, rdir / "frame_fail.jsonl"):
        tmp.unlink(missing_ok=True)
    return report


def fetch_geo_origin(fr: cm.Cb7Run, it: dict) -> dict:
    """One origin: ONE windowed taker-print request before ``t_k``; YES-terms prints (no wallet) go to ``prints_partial.jsonl.gz``
    before the progress record."""
    t = float(it["origin_ts"])
    prints, info = cm.origin_prints(fr.lim, it["condition_id"], t, cap_epoch=fr.cap_epoch)
    price = cm.origin_price(prints, t, cm.GEO_BAND, info)
    cm.append_member(fr, fr.rdir / "prints_partial.jsonl.gz", {"item_id": it["item_id"], "prints": prints})
    return {"item_id": it["item_id"], "market_id": it["market_id"], "k": int(it["k"]), "origin_ts": int(t), "status": "done", **price}


def geo_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, history_root: Path | None = None, seals_dir: Path | None = None,
    seal_paths: dict[str, Path] | None = None, rules_path: Path = cm.RULES_FILE, smoke_path: Path = cm.SMOKE_DEFAULT,
    exclusion_keys_path: Path = cm.EXCLUSION_KEYS_DEFAULT, pins=None, seed: str = cm.GEO_SEED, tag_id: str = cm.GEO_TAG_ID,
    end_from: str = cm.GEO_END_FROM, end_before_fetch_days: int = cm.END_BEFORE_FETCH_DAYS,
    max_failed_origin_share: float = cm.MAX_FAILED_ORIGIN_SHARE, cap_at: str = cm.T_SEAL, rps: float = 4.0,
    disk_cap: int = int(cm.GEO_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, key: bytes | None = None,
    now: float | None = None, sleep: Callable[[float], None] = time.sleep,
    live_check: Callable[[], bool] | None = hb.live_pass_or_lock, should_stop: Callable[[], bool] | None = None,
    wall_clock: Callable[[], float] = time.time, t_seal_epoch: float = cm.T_SEAL_EPOCH, snapshot_root: Path | None = None,
    health_every_s: float = 600.0, health_check: Callable[[float], tuple[bool, str]] | None = None,
    require_committed: bool = True, require_smoke: bool = True, data_dumps: Path | None = None,
    data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB,
) -> dict:
    """One resumable chunk of the ``h8_geo`` fetch (module docstring for the stage order). No chunk starts at or after
    ``t_seal_epoch``; a full output cap is the declared end state ``disk_budget``; more than 2% failed origin requests is
    ``source_unverified``."""
    params = {"seed": seed, "tag_id": tag_id, "end_from": end_from, "end_before_fetch_days": end_before_fetch_days,
              "min_life_days": cm.GEO_MIN_LIFE_DAYS, "max_per_event": cm.MAX_PER_EVENT, "origin_days": list(cm.GEO_ORIGIN_DAYS),
              "band": list(cm.GEO_BAND), "print_limit": cm.PRINT_LIMIT, "max_failed_origin_share": max_failed_origin_share}
    fr, early, ctx = cm.open_run(
        root, run_id, transport, allowed_run_id=cm.GEO_RUN_ID, kind="geo", label="CB7-G h8_geo", complete_token=cm.GEO_COMPLETE,
        params=params, smoke_need=("a", "b", "c"), history_root=history_root, seals_dir=seals_dir, seal_paths=seal_paths,
        rules_path=rules_path, smoke_path=smoke_path, exclusion_keys_path=exclusion_keys_path, pins=pins,
        require_committed=require_committed, require_smoke=require_smoke, data_dumps=data_dumps,
        data_dumps_cap_gb=data_dumps_cap_gb, disk_cap=disk_cap, rps=rps, budget_min=budget_min, key=key, now=now, sleep=sleep,
        live_check=live_check, wall_clock=wall_clock, t_seal_epoch=t_seal_epoch, snapshot_root=snapshot_root,
        health_every_s=health_every_s, health_check=health_check, cap_at=cap_at)
    if early is not None:
        return early
    assert fr is not None
    t_fetch = fr.now
    cutoff = t_fetch - end_before_fetch_days * DAY
    rdir = fr.rdir
    why = fr.unhealthy()
    if why:
        return fr.manifest(why, {"transient": True})
    if ctx["key_report"].get("disjointness") == cm.UNVERIFIED_TOKEN:
        return cm.unverified_end(fr, ctx["key_report"], run_id)
    try:
        if not (rdir / "frame_report.json").exists():
            why_stop: list[str] = []

            def walk_stop() -> bool:
                r = fr.stop_reason(should_stop)
                if r:
                    why_stop.append(r)
                return bool(r)

            stopped = walk_geo_frame(fr, month_windows(c4._ep(end_from), cutoff), tag_id, should_stop=walk_stop)
            if stopped:
                return cm.transient(fr, why_stop[-1] if why_stop else stopped)
            build_geo_outputs(fr, cutoff_epoch=cutoff, end_from_epoch=c4._ep(end_from), excl_ids=ctx["excl_ids"],
                              excl_keys=ctx["excl_keys"], t_fetch=t_fetch)
    except Refused:
        raise
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    except RuntimeError as exc:
        return fr.manifest(f"stage_failed: {exc}"[:200], {"transient": True, "status": "in_progress"})
    frame_rep = json.loads((rdir / "frame_report.json").read_text())
    cond = {r["market_id"]: r["condition_id"] for r in cm.read_csv_gz(rdir / "sample.csv.gz")}
    items = [{"item_id": f"{o['market_id']}|{o['k']}", "market_id": o["market_id"], "k": o["k"], "origin_ts": o["origin_ts"],
              "condition_id": cond[o["market_id"]]} for o in cm.read_csv_gz(rdir / "origins.csv.gz") if o["market_id"] in cond]
    items.sort(key=lambda r: (hb._rank(seed, r["market_id"]), int(r["k"])))
    extra = {"frame_report": frame_rep, "exclusion_report": ctx["key_report"], "n_markets": frame_rep["n_markets"],
             "n_items": len(items)}
    stopped, pending = c4._fetch_items(fr, items, "item_id", lambda it: fetch_geo_origin(fr, it), ct.tally_origin(fr.counts),
                                       should_stop, extra)
    if stopped is None and pending == 0:
        try:
            fin = cm.stream_origin_tables(fr, "item_id")
        except OSError as exc:
            return cm.disk_budget_end(fr, exc, extra)
        extra.update(fin)
        fr.counts["print_request_failed"] = fin["items_failed_final"]
        share = fin["items_failed_final"] / len(items) if items else 0.0
        extra["failed_origin_share"] = share
        extra["file_sha256"] = cm.file_hashes(rdir)
        if share > max_failed_origin_share:
            (rdir / cm.SOURCE_UNVERIFIED_FILE).write_text(json.dumps(
                {"run_id": run_id, "status": cm.SOURCE_UNVERIFIED_TOKEN, "failed_origin_share": share,
                 "rule": "CREATIVE_BATCH_7.md CB7-G: more than 2% of origin requests failed after retries -> G1 not testable "
                         "(source), counted"}, indent=1, sort_keys=True))
            m = fr.manifest(cm.SOURCE_UNVERIFIED_TOKEN, {**extra, "status": cm.SOURCE_UNVERIFIED_TOKEN})
            m["status"] = cm.SOURCE_UNVERIFIED_TOKEN
            return m
        extra.update(complete=True, status=cm.GEO_COMPLETE)
        m = fr.manifest(None, extra)
        m["status"] = cm.GEO_COMPLETE
        return m
    if stopped == "t_seal_passed":
        return cm.transient(fr, "t_seal_passed")
    if stopped and stopped.startswith("disk_budget"):
        return cm.disk_budget_end(fr, stopped[len("disk_budget: "):], extra)
    m = fr.manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})
    m["status"] = "in_progress"
    return m

