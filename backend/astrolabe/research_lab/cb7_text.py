# ruff: noqa: E501
"""CB7-S fetch side: the ``h8_text`` backfill (q0142) and its seal (q0144)
(docs/research_lab/CREATIVE_BATCH_7.md CB7-S "Data", "Population", "Sample", "Origin and price", "Text features").

Stage order (each stage idempotent, finished stages are skipped): refusals -> terminal / deadline guard -> headroom (exit 75) ->
frame walk (5 random 15-minute ``end_date`` windows a day, ``closed=false`` then ``closed=true``) -> M1-M7 and the clarification
flag on the FULL description in memory, then the 4,000-character copy is stored -> filters -> exclusion id / key drop ->
stratified sample -> ``origins.csv.gz``, ``text_features.csv.gz`` and ``cut_points.json`` (text only) -> one windowed taker-print
request per market at ``t7 = end_at - 7 d`` -> tables and manifest. Memory: the frame walk never holds raw events (one gzip
member per day); the filters stream the partial file.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path

from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as cm
from . import h5_seal
from . import history_backfill as hb

Refused, NotNow, DAY = cm.Refused, cm.NotNow, cm.DAY

MARKER_PATTERNS = (  # (name, text, flags, pattern) -- CB7 section CB7-S "Text features"
    ("M1_must", "description", "i", r"\bmust\b"),
    ("M2_official", "description", "i", r"\bofficial(?:ly|s)?\b"),
    ("M3_named_source", "description", "i", r"\baccording to\b"),
    ("M4_conjunction", "question", "i", r"\band\b|&"),
    ("M5_time_of_day_deadline", "description", "i", r"\b(?:before|by|prior to|no later than)\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)"),
    ("M6_time_zone", "description", "", r"\b(?:ET|EST|EDT)\b"),
    ("M7_named_url", "description", "i", r"https?://|\bwww\."),
)
MARKER_DOC = [{"name": n, "text": t, "case_insensitive": f == "i", "pattern": p} for n, t, f, p in MARKER_PATTERNS]
_MARKER_RX = [(t, re.compile(p, re.IGNORECASE if f == "i" else 0)) for _, t, f, p in MARKER_PATTERNS]
CUT_RULE = ("per cb1_topic over the sampled markets' C: c_L = smallest integer with share(C <= c_L) >= 1/3; c_H = largest "
            "integer with share(C >= c_H) >= 1/3; c_H <= c_L -> no tercile contrast; text only, written before any print request")
TEXT_FILTER_ORDER = ("no_created_or_end", "end_outside_window", "not_yes_no", "life_lt_9d", "weather", "crypto_updown",
                     "geopolitics", "other_placeholder", "exclusion_id", "exclusion_key")
FEATURE_COLUMNS = ["desc_len", "desc_sha256", "m1", "m2", "m3", "m4", "m5", "m6", "m7", "c", "clarified"]
SAMPLE_EXTRA = ["stratum", "stratum_size", "stratum_alloc", "inclusion_prob", "sample_weight"]
FRAME_COLUMNS = [*cm.MAIN_COLUMNS, *FEATURE_COLUMNS]
SAMPLE_COLUMNS = [*FRAME_COLUMNS, "description", *SAMPLE_EXTRA]
FEATURE_FILE_COLUMNS = ["market_id", "cb1_topic", *FEATURE_COLUMNS]


# ---- deterministic rules (SOURCE hashed into the rules file) -------------------------------------------------------------------


def markers(question: str, description: str) -> list[int]:
    """M1-M7 as 0/1. M4 is read on the question only; every other marker on the description. Text is the full text passed in
    (the caller must not truncate it first); M6 is case-sensitive, the rest are not."""
    texts = {"question": question or "", "description": description or ""}
    return [int(bool(rx.search(texts[which]))) for which, rx in _MARKER_RX]


def condition_count(marks: list[int]) -> int:
    """C = number of marker TYPES present (0-7), never occurrences."""
    return int(sum(1 for x in marks if x))


def text_features(question: str, description: str) -> dict:
    """Features of the FULL description: its length and sha256, M1-M7, C and the clarification flag."""
    d = description or ""
    ms = markers(question, d)
    return {"desc_len": len(d), "desc_sha256": hashlib.sha256(d.encode()).hexdigest(), "m1": ms[0], "m2": ms[1], "m3": ms[2],
            "m4": ms[3], "m5": ms[4], "m6": ms[5], "m7": ms[6], "c": condition_count(ms),
            "clarified": int(cm.has_clarification(d))}


def cut_points(c_by_topic: dict[str, list[int]]) -> dict[str, dict]:
    """Per topic: ``c_L`` = smallest integer with share(C <= c_L) >= 1/3, ``c_H`` = largest integer with share(C >= c_H) >= 1/3;
    ``contrast`` is false when ``c_H <= c_L``. Reads C only (text)."""
    out = {}
    for topic in sorted(c_by_topic):
        cs = c_by_topic[topic]
        n = len(cs)
        c_l = next((x for x in range(0, 8) if 3 * sum(1 for c in cs if c <= x) >= n), 7)
        c_h = next((x for x in range(7, -1, -1) if 3 * sum(1 for c in cs if c >= x) >= n), 0)
        out[topic] = {"n": n, "c_L": c_l, "c_H": c_h, "contrast": bool(n and c_h > c_l)}
    return out


def text_filter_reason(r: dict, cutoff_epoch: float, end_lo: float) -> str | None:
    """First declared filter that rejects a frame row (before the exclusion id / key tests), else ``None``."""
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
    if end - created < cm.TEXT_MIN_LIFE_DAYS * DAY:
        return "life_lt_9d"
    if cm.is_weather(r.get("fee_category", ""), r.get("question", ""), r.get("event_title", "")):
        return "weather"
    if hb.cb1_topic(r) == "crypto_updown":
        return "crypto_updown"
    if cm.is_geopolitics(r):
        return "geopolitics"
    if cm.is_other_placeholder(r):
        return "other_placeholder"
    return None


def text_row(m: dict, cap_epoch: float) -> tuple[dict, dict] | None:
    """(frame row with features and the 4,000-character description, guarded outcome row) of one Gamma market. Features are
    computed on the FULL question and description BEFORE truncation."""
    pr = cm.market_row(m, cap_epoch)
    if pr is None:
        return None
    main, guarded = pr
    q, d = str(m.get("question") or ""), str(m.get("description") or "")
    main.update(text_features(q, d))
    main["description"] = d[:cm.DESCRIPTION_CHARS]
    return main, guarded


# ---- frame walk ------------------------------------------------------------------------------------------------------------------


def walk_text_frame(fr: cm.Cb7Run, days, seed: str, *, cutoff_epoch: float, should_stop: Callable[[], bool] | None = None,
                    windows_per_day: int = cm.WINDOWS_PER_DAY, window_minutes: int = cm.WINDOW_MINUTES,
                    pages_per_window: int = cm.PAGES_PER_WINDOW) -> str | None:
    """Per day: ``windows_per_day`` seeded windows on ``end_date`` (only windows ending at or before ``cutoff_epoch``), each walked
    ``closed=false`` then ``closed=true``; a window still capped after ``pages_per_window`` pages is dropped whole and counted. One
    gzip member per day in ``frame_partial.jsonl.gz``. A failed window keeps the day open (retried by the next chunk, at most
    ``MAX_DAY_ATTEMPTS`` times). Returns a stop reason or ``None`` when every day is done."""
    rdir = fr.rdir
    pp, pf = rdir / "frame_partial.jsonl.gz", rdir / "frame_fail.jsonl"
    done_days: set[str] = set()
    seen: set[str] = set()
    for rec in c6.iter_partial(pp):
        done_days.add(rec["day"])
        seen.update(r["market_id"] for r in rec["rows"])
    fails = cm.walk_failed_days(pf)
    f = "%Y-%m-%dT%H:%M:%SZ"
    for day in days:
        dkey = f"{day:%Y-%m-%d}"
        if dkey in done_days:
            continue
        if should_stop is not None and should_stop():
            return "frame_paused"
        d0, picks = cm.pick_windows(day, seed, cutoff_epoch, windows_per_day, window_minutes)
        rows: list[dict] = []
        outs: list[dict] = []
        win = {"closed": 0, "active": 0}
        dropped = {"closed": 0, "active": 0}
        dropped_rows = raw = invalid = dups = failed_windows = 0
        day_seen: set[str] = set()
        for closed in (False, True):
            kind = "closed" if closed else "active"
            for k in picks:
                a = d0 + timedelta(minutes=k * window_minutes)
                b = a + timedelta(minutes=window_minutes)
                p = {"order": "id", "ascending": "true", "closed": "true" if closed else "false",
                     "end_date_min": a.strftime(f), "end_date_max": b.strftime(f)}
                batch, capped, failed = c4._paged_strict(fr.lim, p, pages_per_window * hb.GAMMA_PAGE)
                if failed:
                    failed_windows += 1
                    continue
                win[kind] += 1
                if capped:
                    dropped[kind] += 1
                    dropped_rows += len(batch)
                    continue
                for m in batch:
                    raw += 1
                    pr = text_row(m, fr.cap_epoch)
                    if pr is None:
                        invalid += 1
                        continue
                    mid = pr[0]["market_id"]
                    if mid in seen or mid in day_seen:
                        dups += 1
                        continue
                    day_seen.add(mid)
                    rows.append(pr[0])
                    outs.append(pr[1])
        if failed_windows and fails.get(dkey, 0) + 1 < cm.MAX_DAY_ATTEMPTS:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": dkey, "failed_windows": failed_windows}) + "\n")
            return f"walk_failed_window: {dkey}"
        cm.append_member(fr, pp, {"day": dkey, "rows": rows, "outs": outs, "windows": win, "dropped": dropped,
                                  "dropped_rows": dropped_rows, "raw": raw, "invalid": invalid, "dups": dups,
                                  "failed_windows": failed_windows})
        seen.update(day_seen)
    return None


def build_text_outputs(fr: cm.Cb7Run, *, cutoff_epoch: float, end_from_epoch: float, excl_ids: set[str],
                       excl_keys: dict[str, set[str]], n_markets: int, seed: str, t_fetch: float) -> dict:
    """Stream ``frame_partial.jsonl.gz`` twice. Pass 1 writes ``frame.csv.gz`` (every walked row, features, no description), applies
    the filters, the exclusion id test and the key drop (counted by reason / key type) keeping only ids per stratum; the sample is
    drawn; pass 2 gathers the sampled rows. ``origins.csv.gz``, ``text_features.csv.gz`` and ``cut_points.json`` are written BEFORE
    ``sample.csv.gz`` and long before any print request; outcome columns go only to ``outcomes_guarded.csv.gz``;
    ``frame_report.json`` is written last."""
    rdir = fr.rdir
    pp = rdir / "frame_partial.jsonl.gz"
    counts: dict = {"frame_rows": 0, "filter_dropped": {}, "exclusion_id_dropped": 0, "exclusion_key_dropped": 0,
                    "kept_by_key_stage": 0, "descriptions_longer_than_stored": 0, "clarified_in_frame": 0,
                    "closed_after_cap_in_frame": 0}
    key_drops = {"by_type_any_match": dict.fromkeys(cm.KEY_TYPES, 0), "by_type_combo": {}, "rows": 0}
    strata: dict[str, list[str]] = {}
    walk = {"windows": {"closed": 0, "active": 0}, "windows_dropped_capped": {"closed": 0, "active": 0}, "windows_failed": 0,
            "rows_in_dropped_windows": 0, "dropped_capped_by_day": {}, "days": 0, "raw": 0, "non_binary_or_invalid": 0,
            "duplicates": 0, "days_with_failed_windows": []}

    def rows_pass1() -> Iterator[list]:
        for rec in c6.iter_partial(pp):
            walk["days"] += 1
            for k in ("closed", "active"):
                walk["windows"][k] += rec["windows"][k]
                walk["windows_dropped_capped"][k] += rec["dropped"][k]
            walk["rows_in_dropped_windows"] += rec["dropped_rows"]
            if any(rec["dropped"].values()):
                walk["dropped_capped_by_day"][rec["day"]] = rec["dropped"]
            if rec.get("failed_windows"):
                walk["windows_failed"] += rec["failed_windows"]
                walk["days_with_failed_windows"].append(rec["day"])
            walk["raw"] += rec["raw"]
            walk["non_binary_or_invalid"] += rec["invalid"]
            walk["duplicates"] += rec["dups"]
            for r in rec["rows"]:
                counts["frame_rows"] += 1
                counts["descriptions_longer_than_stored"] += int(int(r["desc_len"]) > cm.DESCRIPTION_CHARS)
                counts["clarified_in_frame"] += int(int(r["clarified"]) == 1)
                counts["closed_after_cap_in_frame"] += int(int(r["closed_after_cap"]) == 1)
                yield [r.get(c, "") for c in FRAME_COLUMNS]
                why = text_filter_reason(r, cutoff_epoch, end_from_epoch)
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
                counts["kept_by_key_stage"] += 1
                month = str(r.get("end_at") or "")[:7] or "unknown"
                strata.setdefault("|".join([str(r["status"]), hb.cb1_topic(r), month]), []).append(r["market_id"])

    fr.budget.write_gz_csv(rdir / "frame.csv.gz", FRAME_COLUMNS, rows_pass1())
    chosen, srep = cm.draw_sample(strata, n_markets, seed)
    strata.clear()
    picked: dict[str, tuple[dict, dict]] = {}
    for rec in c6.iter_partial(pp):
        outs = {o["market_id"]: o for o in rec["outs"]}
        for r in rec["rows"]:
            if r["market_id"] in chosen:
                picked[r["market_id"]] = (r, outs[r["market_id"]])
    ids = sorted(picked)
    fr.budget.write_gz_csv(rdir / "origins.csv.gz", cm.ORIGIN_COLUMNS,
                           ([m, int(float(picked[m][0]["end_epoch"]) - cm.TEXT_ORIGIN_DAYS * DAY),
                             cm._iso(float(picked[m][0]["end_epoch"]) - cm.TEXT_ORIGIN_DAYS * DAY), cm.TEXT_ORIGIN_DAYS] for m in ids))
    c_by_topic: dict[str, list[int]] = {}
    for m in ids:
        c_by_topic.setdefault(hb.cb1_topic(picked[m][0]), []).append(int(picked[m][0]["c"]))
    cuts = cut_points(c_by_topic)
    fr.budget.write_gz_csv(rdir / "text_features.csv.gz", FEATURE_FILE_COLUMNS,
                           ([m, hb.cb1_topic(picked[m][0]), *[picked[m][0][c] for c in FEATURE_COLUMNS]] for m in ids))
    fr.budget.write(rdir / "cut_points.json", json.dumps({"rule": CUT_RULE, "by_topic": cuts}, indent=1, sort_keys=True).encode())
    fr.budget.write_gz_csv(rdir / cm.OUTCOME_FILE, cm.GUARDED_COLUMNS, ([picked[m][1].get(c, "") for c in cm.GUARDED_COLUMNS] for m in ids))
    fr.budget.write_gz_csv(rdir / "sample.csv.gz", SAMPLE_COLUMNS,
                           ([picked[m][0].get(c, "") for c in FRAME_COLUMNS] + [picked[m][0].get("description", "")]
                            + [chosen[m][c] for c in SAMPLE_EXTRA] for m in ids))
    kd = {"exclusion_key_types": list(cm.KEY_TYPES), **key_drops}
    fr.budget.write(rdir / "key_drops.json", json.dumps(kd, indent=1, sort_keys=True).encode())
    sampled_long = sum(1 for m in ids if int(picked[m][0]["desc_len"]) > cm.DESCRIPTION_CHARS)
    report = {"frame_version": hb.FRAME_VERSION, "t_fetch_text": cm._iso(t_fetch), "end_cutoff": cm._iso(cutoff_epoch),
              "cap_utc": cm._iso(fr.cap_epoch), "windows_per_day": cm.WINDOWS_PER_DAY, "window_minutes": cm.WINDOW_MINUTES,
              "pages_per_window": cm.PAGES_PER_WINDOW, **walk, **counts, "sample": srep, "n_sample": len(ids),
              "sampled_descriptions_longer_than_stored": sampled_long, "key_drops": kd,
              "outcomes_censored_post_cap": sum(1 for m in ids if int(picked[m][0]["closed_after_cap"]) == 1)}
    fr.budget.write(rdir / "frame_report.json", json.dumps(report, indent=1, sort_keys=True, default=float).encode())
    for tmp in (pp, rdir / "frame_fail.jsonl"):
        tmp.unlink(missing_ok=True)
    return report


# ---- per-market print request ---------------------------------------------------------------------------------------------------


def fetch_text_market(fr: cm.Cb7Run, r: dict) -> dict:
    """One sampled market: ONE windowed taker-print request before ``t7 = end_at - 7 d``; the YES-terms prints (no wallet) go to
    ``prints_partial.jsonl.gz`` BEFORE the progress record, so a crash between the two only repeats the request."""
    t7 = float(r["end_epoch"]) - cm.TEXT_ORIGIN_DAYS * DAY
    prints, info = cm.origin_prints(fr.lim, r["condition_id"], t7, cap_epoch=fr.cap_epoch)
    price = cm.origin_price(prints, t7, cm.TEXT_BAND, info)
    cm.append_member(fr, fr.rdir / "prints_partial.jsonl.gz", {"item_id": r["market_id"], "prints": prints})
    return {"market_id": r["market_id"], "item_id": r["market_id"], "k": cm.TEXT_ORIGIN_DAYS, "origin_ts": int(t7),
            "status": "done", **price}


def tally_origin(counts: dict[str, int]) -> Callable[[dict], None]:
    def tally(rec: dict) -> None:
        if rec["status"] != "done":
            return
        counts["items_done"] = counts.get("items_done", 0) + 1
        k = "origin_" + str(rec["price_status"])
        counts[k] = counts.get(k, 0) + 1
        counts["eligible_origins"] = counts.get("eligible_origins", 0) + int(rec["eligible"])
        counts["print_rows"] = counts.get("print_rows", 0) + int(rec["n_prints"])
        counts["print_rows_dropped_post_cap"] = counts.get("print_rows_dropped_post_cap", 0) + int(rec["dropped_cap"])
        counts["print_rows_dropped_out_of_window"] = counts.get("print_rows_dropped_out_of_window", 0) + int(rec["dropped_out_of_window"])
        counts["print_pages_full"] = counts.get("print_pages_full", 0) + int(rec["full_page"])

    return tally


def finalize_counts(fr: cm.Cb7Run, extra: dict) -> None:
    fin = cm.stream_origin_tables(fr, "market_id")
    extra.update(fin)
    fr.counts["print_request_failed"] = fin["items_failed_final"]  # failures are counted apart from "no_print"


# ---- the fetch ------------------------------------------------------------------------------------------------------------------


def text_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, history_root: Path | None = None, seals_dir: Path | None = None,
    seal_paths: dict[str, Path] | None = None, rules_path: Path = cm.RULES_FILE, smoke_path: Path = cm.SMOKE_DEFAULT,
    exclusion_keys_path: Path = cm.EXCLUSION_KEYS_DEFAULT, pins=None, seed: str = cm.TEXT_SEED,
    n_markets: int = cm.N_TEXT_MARKETS, end_from: str = cm.TEXT_END_FROM, end_before_fetch_days: int = cm.END_BEFORE_FETCH_DAYS,
    windows_per_day: int = cm.WINDOWS_PER_DAY, window_minutes: int = cm.WINDOW_MINUTES, pages_per_window: int = cm.PAGES_PER_WINDOW,
    cap_at: str = cm.T_SEAL, rps: float = 4.0, disk_cap: int = int(cm.TEXT_OUTPUT_CAP_GB * 1024**3),
    budget_min: float | None = None, key: bytes | None = None, now: float | None = None,
    sleep: Callable[[float], None] = time.sleep, live_check: Callable[[], bool] | None = hb.live_pass_or_lock,
    should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time,
    t_seal_epoch: float = cm.T_SEAL_EPOCH, snapshot_root: Path | None = None, health_every_s: float = 600.0,
    health_check: Callable[[float], tuple[bool, str]] | None = None, require_committed: bool = True, require_smoke: bool = True,
    data_dumps: Path | None = None, data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB,
) -> dict:
    """One resumable chunk of the ``h8_text`` fetch (module docstring for the stage order). A chunk starts nothing at or after
    ``t_seal_epoch``; an incomplete run at T_seal is ``not_run_deadline``. A full output cap is the declared end state
    ``disk_budget``."""
    params = {"seed": seed, "n_markets": n_markets, "end_from": end_from, "end_before_fetch_days": end_before_fetch_days,
              "windows_per_day": windows_per_day, "window_minutes": window_minutes, "pages_per_window": pages_per_window,
              "min_life_days": cm.TEXT_MIN_LIFE_DAYS, "sports_weight": cm.SPORTS_WEIGHT, "print_limit": cm.PRINT_LIMIT}
    fr, early, ctx = cm.open_run(
        root, run_id, transport, allowed_run_id=cm.TEXT_RUN_ID, kind="text", label="CB7-S h8_text", complete_token=cm.TEXT_COMPLETE,
        params=params, smoke_need=("b", "c"), history_root=history_root, seals_dir=seals_dir, seal_paths=seal_paths,
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

            days = cm.frame_days(c4._ep(end_from), cutoff)
            stopped = walk_text_frame(fr, days, seed, cutoff_epoch=cutoff, should_stop=walk_stop, windows_per_day=windows_per_day,
                                      window_minutes=window_minutes, pages_per_window=pages_per_window)
            if stopped:
                return cm.transient(fr, why_stop[-1] if why_stop else stopped)
            build_text_outputs(fr, cutoff_epoch=cutoff, end_from_epoch=c4._ep(end_from), excl_ids=ctx["excl_ids"],
                               excl_keys=ctx["excl_keys"], n_markets=n_markets, seed=seed, t_fetch=t_fetch)
    except Refused:
        raise
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    except RuntimeError as exc:  # persistent API failure in the walk: transient, partial results are kept
        return fr.manifest(f"stage_failed: {exc}"[:200], {"transient": True, "status": "in_progress"})
    frame_rep = json.loads((rdir / "frame_report.json").read_text())
    items = [{"market_id": r["market_id"], "condition_id": r["condition_id"], "end_epoch": r["end_epoch"]}
             for r in cm.read_csv_gz(rdir / "sample.csv.gz")]
    items.sort(key=lambda r: hb._rank(seed, r["market_id"]))
    extra = {"frame_report": {k: v for k, v in frame_rep.items() if k not in ("dropped_capped_by_day",)},
             "exclusion_report": ctx["key_report"], "n_sample": frame_rep["n_sample"], "n_items": len(items)}
    stopped, pending = c4._fetch_items(fr, items, "market_id", lambda r: fetch_text_market(fr, r), tally_origin(fr.counts),
                                       should_stop, extra)
    if stopped is None and pending == 0:
        try:
            finalize_counts(fr, extra)
        except OSError as exc:
            return cm.disk_budget_end(fr, exc, extra)
        extra.update(complete=True, status=cm.TEXT_COMPLETE, file_sha256=cm.file_hashes(rdir),
                     text_features_sha256=h5_seal.sha256_file(rdir / "text_features.csv.gz"),
                     cut_points_sha256=h5_seal.sha256_file(rdir / "cut_points.json"))
        m = fr.manifest(None, extra)
        m["status"] = cm.TEXT_COMPLETE
        return m
    if stopped == "t_seal_passed":
        return cm.transient(fr, "t_seal_passed")
    if stopped and stopped.startswith("disk_budget"):
        return cm.disk_budget_end(fr, stopped[len("disk_budget: "):], extra)
    m = fr.manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})
    m["status"] = "in_progress"
    return m

