# ruff: noqa: E501
"""CB8-W fetch side (docs/research_lab/CREATIVE_BATCH_8.md CB8-W "Data", CB8-F, 5.1): the ``h9_flow`` fresh sample of closed markets with
one seeded 72-h window each and every taker print with an HMAC wallet hash (q0167), and its seal (q0168).

Exploratory historical data (rows before 2026-10-01); NOT bound to T_seal. No outcome is fetched or stored: the frame query is on lifetime
volume and the end date only (an ex-post selection, disclosed in the design). Raw wallets exist only in memory. The event-level
SCREEN / HOLDOUT split is written before the first print request; HOLDOUT prints go to their own directory.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as c7
from . import cb8_common as cm
from . import h5_seal
from . import history_backfill as hb

RUN_ID = "h9_flow"
COMPLETE = "flow_fetch_complete"
UNVERIFIED = "disjointness_unverified"
SEED_WINDOW = "arepo-h9-window"
SEED_SAMPLE = "arepo-h9-sample"
SEED_SPLIT = "arepo-h9-split"
HIST_END = "2026-10-01T00:00:00Z"
END_FROM = "2026-05-08T00:00:00Z"
WINDOW_FLOOR = "2026-05-01T00:00:00Z"
WINDOW_LAST_END = "2026-09-27T00:00:00Z"
MIN_VOLUME = 50000.0
MIN_LIFE_DAYS = 10
MAX_PER_EVENT = 2
N_MAIN = 1500
N_SPORTS = 300
WINDOW_H = 72
FETCH_WINDOW_H = 74.5
DAY_PAGES = 10
PRINT_LIMIT = 1000
MAX_UNVERIFIED_KEY_SHARE = 0.02
OUTPUT_CAP_GB = 0.15
EXCLUSION_KEYS_DEFAULT = cm.CB8_DIR / "exclusion_keys.csv.gz"
SMOKE_DEFAULT = cm.CB8_DIR / "smoke.json"
FRAME_COLUMNS = ["market_id", "condition_id", "token0", "token1", "event_id", "event_ids", "neg_risk_market_id", "series_ids", "fee_category", "topic",
                 "created_at", "start_at", "end_at", "start_epoch", "end_epoch", "volume", "question", "event_title"]
SAMPLE_COLUMNS = [*FRAME_COLUMNS, "group", "stratum", "stratum_size", "stratum_alloc", "sample_weight", "split", "w0_epoch", "w0_utc", "window_end_epoch",
                  "gap_to_end_days"]
PRINT_COLUMNS = ["ts", "token_idx", "side", "price", "size", "yes_price", "yes_side", "wallet_hash"]
DAY_COLUMNS = ["market_id", "day", "status", "pages", "n_raw", "n_rows", "malformed", "duplicates", "out_of_window", "missing_wallet", "order_ok"]
DAY_TO_FRAME_WINDOW_S = cm.DAY


def declared() -> dict:
    return {
        "frame": {"query": f"closed=true, volume_num_min={MIN_VOLUME:g}, end_date in [{END_FROM}, {HIST_END}), order id, halved while capped (one day minimum: excluded, counted)",
                  "keeps": f"binary with token ids, scheduled life >= {MIN_LIFE_DAYS} d, not weather (fee_category or CB2-W text), not crypto Up/Down (CB1_UPDOWN_RE)",
                  "stored_fields": FRAME_COLUMNS, "outcome_fields_stored": False, "ex_post_selection": "closed and lifetime volume are known only after the window (disclosed)"},
        "exclusion": {"ids_and_keys": "creative_batch8/exclusion_keys.csv.gz + exclusion_report.json", "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
                      "refused_run_ids": list(cm.REFUSED_RUN_IDS), "refused_roots": list(cm.REFUSED_ROOTS)},
        "window": {"seed": SEED_WINDOW, "floor": WINDOW_FLOOR, "last_end": WINDOW_LAST_END, "hours": WINDOW_H, "fetch_hours": FETCH_WINDOW_H,
                   "w0": "uniform in [max(created_at + 1 d, floor), min(end_at - 4 d, last_end) - 72 h] by sha256(seed|market_id); empty range: dropped, counted",
                   "hist_end": HIST_END},
        "sample": {"seed": SEED_SAMPLE, "max_per_event": MAX_PER_EVENT, "cap_order": "sha256(seed|cap|market_id)", "n_main": N_MAIN, "n_sports": N_SPORTS,
                   "strata": "group x fee_category, proportional (hb.allocate_weighted); order sha256(seed|market_id)", "sports": "topic == 'sports'"},
        "split": {"seed": SEED_SPLIT, "unit": "Gamma event id (first event id; market id if none)", "rule": "int(sha256(seed|event) , 16) % 2: 0 SCREEN, 1 HOLDOUT",
                  "written_before_first_print_request": True},
        "prints": {"url": hb.DATA_TRADES, "per_utc_day_segment": True, "pages": DAY_PAGES, "limit": PRINT_LIMIT, "taker_only": True,
                   "capped_day": "unavailable (counted)", "stored": PRINT_COLUMNS, "wallet_hash_hex": cm.WALLET_HASH_HEX, "outcome_fetched": False},
        "disk": {"output_cap_gb": OUTPUT_CAP_GB},
        "seal": {"drops": "seal-time drops by id and key against every committed seal copy (excluding own); sealed files never edited",
                 "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "holdout_listing_sha256": True},
    }


# ---- frame ---------------------------------------------------------------------------------------------------------------------------


def flow_row(m: dict) -> dict | None:
    """Slim frame row of one Gamma market (no outcome price, no closing field). ``None`` unless binary with token ids."""
    r = hb.frame_row(m, with_text=True)
    if r is None:
        return None
    k = c6.key_fields(m)
    out = {c: r.get(c, "") for c in FRAME_COLUMNS if c in r}
    out.update(event_ids=k["event_ids"], neg_risk_market_id=k["neg_risk_market_id"], series_ids=k["series_ids"])
    return {c: out.get(c, "") for c in FRAME_COLUMNS}


def frame_reason(r: dict) -> str | None:
    """Why a frame row leaves the frame (``None`` = kept). Text and listing fields only."""
    ee, se = r["end_epoch"], r["start_epoch"]
    if not (isinstance(ee, float) and isinstance(se, float)) or ee != ee or se != se:
        return "no_dates"
    if not (cm.ep(END_FROM) <= ee < cm.ep(HIST_END)):
        return "end_outside_window"
    if ee - se < MIN_LIFE_DAYS * cm.DAY:
        return "life_below_min"
    vol = r.get("volume")
    if not (isinstance(vol, float) and vol >= MIN_VOLUME):
        return "volume_below_min"
    if c7.is_weather(str(r.get("fee_category") or ""), str(r.get("question") or ""), str(r.get("event_title") or "")):
        return "weather"
    if hb.CB1_UPDOWN_RE.search(f"{r.get('question', '')} {r.get('event_title', '')}"):
        return "crypto_updown"
    return None


def _walk_window(lim: hb.Limiter, a: int, b: int, acc: dict) -> None:
    f = "%Y-%m-%dT%H:%M:%SZ"
    p = {"closed": "true", "volume_num_min": int(MIN_VOLUME), "order": "id", "ascending": "true",
         "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f)}
    batch, capped, failed = c4._paged_strict(lim, p, hb.GAMMA_OFFSET_CAP)
    if failed:
        acc["failed_windows"] += 1
        return
    if capped and b - a > cm.DAY:
        acc["splits"] += 1
        mid = a + (b - a) // 2
        _walk_window(lim, a, mid, acc)
        _walk_window(lim, mid, b, acc)
        return
    acc["windows"] += 1
    if capped:
        acc["excluded_capped_at_one_day"] += 1
        return
    acc["batches"].extend(batch)


def walk_frame(fr: cm.Cb8Run, days: list[str], should_stop: Callable[[], bool] | None = None) -> str | None:
    """Per UTC day of ``end_date`` one gzip member in ``frame_partial.jsonl.gz`` (rows already reduced to the frame fields). A day with a
    failed request is retried by a later chunk (at most 3 attempts). Returns a stop reason or ``None`` when every day is done."""
    pp, pf = fr.rdir / "frame_partial.jsonl.gz", fr.rdir / "frame_fail.jsonl"
    done = {rec["day"] for rec in c6.iter_partial(pp)}
    fails = c7.walk_failed_days(pf)
    for d in days:
        if d in done or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return why
        a = int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())
        acc = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "excluded_capped_at_one_day": 0}
        _walk_window(fr.lim, a, a + int(cm.DAY), acc)
        if acc["failed_windows"]:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": d}) + "\n")
            fr.counts["frame_request_failures"] = fr.counts.get("frame_request_failures", 0) + 1
            continue
        rows = [x for x in (flow_row(m) for m in acc["batches"] if isinstance(m, dict)) if x is not None]
        c7.append_member(fr, pp, {"day": d, "rows": rows, "n_raw": len(acc["batches"]), "splits": acc["splits"], "excluded_capped_at_one_day": acc["excluded_capped_at_one_day"]})
    fails = c7.walk_failed_days(pf)
    return None if all(d in {r["day"] for r in c6.iter_partial(pp)} or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS for d in days) else "frame_paused"


def frame_days() -> list[str]:
    d0 = datetime.fromtimestamp(cm.ep(END_FROM), UTC).date()
    d1 = datetime.fromtimestamp(cm.ep(HIST_END) - 1, UTC).date()
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


# ---- window, cap, sample, split --------------------------------------------------------------------------------------------------------


def draw_window(r: dict, seed: str = SEED_WINDOW) -> tuple[int, int] | None:
    """``(w0, w_end)`` epochs of the market's 74.5-h print window, or ``None`` if the range is empty. ``w0`` is uniform in
    ``[max(created_at + 1 d, 2026-05-01), min(end_at - 4 d, 2026-09-27) - 72 h]`` by ``sha256(seed|market_id)``. Reads listing dates only."""
    created = c4._parse_ts(r.get("created_at")) or c4._parse_ts(r.get("start_at"))
    end = r.get("end_epoch")
    if created is None or not isinstance(end, float) or end != end:
        return None
    lo = max(created + cm.DAY, cm.ep(WINDOW_FLOOR))
    hi = min(end - 4 * cm.DAY, cm.ep(WINDOW_LAST_END)) - WINDOW_H * cm.HOUR
    if hi < lo:
        return None
    u = int(hb._rank(seed, r["market_id"])[:15], 16) / float(16**15)
    w0 = int(lo + u * (hi - lo))
    return w0, w0 + int(FETCH_WINDOW_H * cm.HOUR)


def event_key(r: dict) -> str:
    return (str(r.get("event_ids") or "").split(";")[0] or str(r.get("event_id") or "")) or f"m{r['market_id']}"


def per_event_cap(rows: list[dict], seed: str = SEED_SAMPLE, max_per_event: int = MAX_PER_EVENT) -> tuple[list[dict], int]:
    """At most ``max_per_event`` markets per event, the first ones in ``sha256(seed|cap|market_id)`` order. Seeded by market id only."""
    by_event: dict[str, list[dict]] = {}
    for r in rows:
        by_event.setdefault(event_key(r), []).append(r)
    kept: list[dict] = []
    for ev in by_event.values():
        kept.extend(sorted(ev, key=lambda x: hb._rank(f"{seed}|cap", x["market_id"]))[:max_per_event])
    return sorted(kept, key=lambda x: x["market_id"]), len(rows) - len(kept)


def event_split(r: dict, seed: str = SEED_SPLIT) -> str:
    """SCREEN / HOLDOUT, 50/50 by a seeded hash of the event id."""
    return "holdout" if int(hashlib.sha256(f"{seed}|{event_key(r)}".encode()).hexdigest(), 16) % 2 else "screen"


def flow_sample(rows: list[dict], n_main: int = N_MAIN, n_sports: int = N_SPORTS, seed: str = SEED_SAMPLE) -> tuple[list[dict], dict]:
    """``n_main`` non-sports and ``n_sports`` sports markets, strata ``group x fee_category``, proportional allocation, order by
    sha256(seed|market_id). Reads ids and listing categories only."""
    out: list[dict] = []
    rep: dict = {"seed": seed, "groups": {}}
    for group, n in (("main", n_main), ("sports", n_sports)):
        strata: dict[str, list[dict]] = {}
        for r in rows:
            if (r.get("topic") == "sports") == (group == "sports"):
                strata.setdefault(f"{group}|{r.get('fee_category') or 'unknown'}", []).append(r)
        sizes = {k: len(v) for k, v in strata.items()}
        alloc = hb.allocate_weighted(sizes, dict.fromkeys(sizes, 1.0), n) if sizes else {}
        for k in sorted(strata):
            for r in sorted(strata[k], key=lambda x: hb._rank(seed, x["market_id"]))[: alloc[k]]:
                out.append({**r, "group": group, "stratum": k, "stratum_size": sizes[k], "stratum_alloc": alloc[k],
                            "sample_weight": sizes[k] / alloc[k] if alloc[k] else ""})
        rep["groups"][group] = {"pool": sum(sizes.values()), "n": sum(alloc.values()), "strata": sizes, "alloc": alloc}
    return out, rep


def assemble_sample(frame: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], n_main: int = N_MAIN, n_sports: int = N_SPORTS) -> tuple[list[dict], dict]:
    """Stage order: filters, id / key drop, window draw, per-event cap, sample, split (the split is final before any print request)."""
    rep: dict = {"n_frame_in": len(frame), "filtered": {}, "dropped_id": 0, "dropped_keys": {}}
    kept = []
    for r in frame:
        why = frame_reason(r)
        if why:
            rep["filtered"][why] = rep["filtered"].get(why, 0) + 1
        else:
            kept.append(r)
    rep["n_after_filters"] = len(kept)
    after = []
    for r in kept:
        if r["market_id"] in excl_ids:
            rep["dropped_id"] += 1
            continue
        kt = c7.key_types_matched(r, excl_keys)
        if kt:
            for t in kt:
                rep["dropped_keys"][t] = rep["dropped_keys"].get(t, 0) + 1
            continue
        after.append(r)
    rep["n_after_drops"] = len(after)
    windowed = []
    rep["window_empty"] = 0
    for r in after:
        w = draw_window(r)
        if w is None:
            rep["window_empty"] += 1
        else:
            windowed.append({**r, "w0_epoch": w[0], "window_end_epoch": w[1]})
    capped, n_cap = per_event_cap(windowed)
    rep["capped_out_per_event"] = n_cap
    sample, srep = flow_sample(capped, n_main, n_sports)
    for r in sample:
        r["split"] = event_split(r)
        r["w0_utc"] = cm.iso(r["w0_epoch"])
        r["gap_to_end_days"] = round((r["end_epoch"] - r["window_end_epoch"]) / cm.DAY, 3)
    sample.sort(key=lambda x: x["market_id"])
    rep["sample"] = srep
    rep["n_sample"] = len(sample)
    rep["n_screen"] = sum(1 for r in sample if r["split"] == "screen")
    rep["n_holdout"] = len(sample) - rep["n_screen"]
    return sample, rep


# ---- the fetch ---------------------------------------------------------------------------------------------------------------------------


def day_segments(w0: int, w_end: int) -> list[tuple[str, int, int]]:
    """UTC-day segments ``(day, start, end_inclusive)`` of the half-open window ``[w0, w_end)``."""
    out = []
    t = w0
    while t < w_end:
        day0 = int(t // cm.DAY * cm.DAY)
        seg_end = min(w_end, day0 + int(cm.DAY))
        out.append((datetime.fromtimestamp(day0, UTC).strftime("%Y-%m-%d"), t, seg_end - 1))
        t = seg_end
    return out


def _read_sample(path: Path) -> list[dict]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            r["w0_epoch"], r["window_end_epoch"] = int(r["w0_epoch"]), int(r["window_end_epoch"])
            rows.append(r)
    return rows


def _exclusion(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    sets, rep, sha = c7.load_exclusion_keys(keys_path)
    ids: set[str] = set()
    with gzip.open(keys_path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ids.add(str(r["market_id"]))
    return ids, sets, rep, sha


def smoke_ok(path: Path) -> dict:
    """The q0161 gate: the Data API paging criterion (a) must have passed. The file is written by the CB8 smoke job (write-once)."""
    p = Path(path)
    if not p.exists():
        raise cm.Refused(f"smoke result {p} not found; run the CB8 smoke first")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise cm.Refused(f"smoke result {p} unreadable") from exc
    if d.get("criterion_a_data_api_paging") is not True:
        raise cm.Refused(f"smoke result {p}: Data API paging criterion (a) not met; W is 'not run (source)'")
    return d


def flow_fetch(root: Path, run_id: str, transport, *, key: bytes, fp: str, rules_sha: str, exclusion_keys_path: Path = EXCLUSION_KEYS_DEFAULT,
               smoke_path: Path = SMOKE_DEFAULT, require_smoke: bool = True, n_main: int = N_MAIN, n_sports: int = N_SPORTS, day_pages: int = DAY_PAGES,
               rps: float = 4.0, disk_cap: int = int(OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
               data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB, wall_clock: Callable[[], float] = time.time, sleep=time.sleep, live_check=None,
               health_check=None, snapshot_root: Path | None = None, should_stop: Callable[[], bool] | None = None, now: float | None = None,
               cap_at: str = HIST_END) -> dict:
    """One resumable chunk of q0167. Refusals first (run id, root, smoke, exclusion files), then headroom (exit 75), sticky end states, the
    frame walk (per UTC day), the sample (written, with the split, before the first print request), then prints per (market, UTC day)."""
    root = Path(root)
    cm.refuse_run_id(run_id, RUN_ID)
    cm.refuse_path(root)
    if require_smoke:
        smoke_ok(smoke_path)
    ids, ksets, krep, ksha = _exclusion(Path(exclusion_keys_path))
    rdir = root / run_id
    if (rdir / h5_seal.SEAL_NAME).exists():
        raise cm.Refused(f"{run_id} is sealed; the fetch never touches a sealed run")
    term = cm.prior_terminal(rdir)
    if term:
        return term
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None:
        return {"stopped": None, "status": COMPLETE, "complete": True, "counts": prior.get("counts")}
    if prior.get("status") == UNVERIFIED or (rdir / "DISJOINTNESS_UNVERIFIED.json").exists():
        return {"stopped": UNVERIFIED, "status": UNVERIFIED, "complete": False}
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    params = {"n_main": n_main, "n_sports": n_sports, "day_pages": day_pages, "cap_at": cap_at, "window_h": WINDOW_H, "evidence_role": "exploratory_historical"}
    fr = cm.open_run(root, run_id, transport, allowed_run_id=RUN_ID, kind="h9_flow", label="CB8-W h9_flow", params=params, rules_sha=rules_sha, key_fp=fp,
                     disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check, cap_at=cap_at)
    fr.extra_state["exclusion_keys_sha256"] = ksha
    why = fr.unhealthy()
    if why:
        m = fr.manifest(why, {"transient": True})
        m["status"] = "in_progress"
        return m
    sample_p, split_p = rdir / "sample.csv.gz", rdir / "split.json"
    try:
        if not sample_p.exists():
            stopped = walk_frame(fr, frame_days(), should_stop)
            if stopped:
                m = fr.manifest(stopped, {"transient": True})
                m["status"] = "in_progress"
                return m
            if krep.get("disjointness") == UNVERIFIED:
                (rdir / "DISJOINTNESS_UNVERIFIED.json").write_text(json.dumps({"run_id": run_id, "exclusion_report": krep, "rule": "design 1.3: > 2% of exclusion ids without metadata -> W1 not testable (p = 1, counted)"}, indent=1, sort_keys=True))
                m = fr.manifest(UNVERIFIED, {"status": UNVERIFIED})
                m["status"] = UNVERIFIED
                return m
            frame = [r for rec in c6.iter_partial(rdir / "frame_partial.jsonl.gz") for r in rec["rows"]]
            for r in frame:
                for k in ("start_epoch", "end_epoch", "volume"):
                    r[k] = float(r[k]) if r.get(k) not in ("", None) else float("nan")
            sample, rep = assemble_sample(frame, ids, ksets, n_main, n_sports)
            fr.budget.write_gz_csv(rdir / "frame.csv.gz", FRAME_COLUMNS, ([r.get(c, "") for c in FRAME_COLUMNS] for r in frame))
            rep["frame_walk"] = {"days": len(frame_days()), "frame_rows": len(frame)}
            fr.budget.write(split_p, json.dumps({"seeds": {"window": SEED_WINDOW, "sample": SEED_SAMPLE, "split": SEED_SPLIT}, "report": rep,
                                                 "events": {event_key(r): r["split"] for r in sample}}, indent=1, sort_keys=True, default=float).encode())
            fr.budget.write_gz_csv(sample_p, SAMPLE_COLUMNS, ([r.get(c, "") for c in SAMPLE_COLUMNS] for r in sample))  # last: marks the stage
            (rdir / "frame_partial.jsonl.gz").unlink(missing_ok=True)
            (rdir / "frame_fail.jsonl").unlink(missing_ok=True)
            fr.counts.update(n_sample=len(sample), n_screen=rep["n_screen"], n_holdout=rep["n_holdout"])
        sample = _read_sample(sample_p)
        stopped = _fetch_prints(fr, sample, key, day_pages, should_stop)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    try:
        _finish(fr, rdir, sample)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": COMPLETE})
    m["status"] = COMPLETE
    return m


def _fetch_prints(fr: cm.Cb8Run, sample: list[dict], key: bytes, day_pages: int, should_stop) -> str | None:
    rdir = fr.rdir
    part, pf = rdir / "days_partial.jsonl.gz", rdir / "days_fail.jsonl"
    done = {(r["market_id"], r["day"]) for r in c6.iter_partial(part)}
    fails: dict[tuple[str, str], int] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                j = json.loads(line)
                fails[(j["market_id"], j["day"])] = fails.get((j["market_id"], j["day"]), 0) + 1
    retry = False
    for r in sample:
        for day, a, b in day_segments(r["w0_epoch"], r["window_end_epoch"]):
            k = (r["market_id"], day)
            if k in done:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return why
            try:
                rows, info = cm.windowed_prints(fr.lim, r["condition_id"], a, b, day_pages, key, limit=PRINT_LIMIT)
                rec = {"market_id": r["market_id"], "day": day, "status": "capped" if info["capped"] else "ok", "info": info,
                       "rows": [] if info["capped"] else [[p["ts"], p["idx"], p["side"], p["price"], p["size"], p["yes_price"], p["yes_side"], p["wallet"] or ""] for p in rows]}
            except (cm.ApiError, RuntimeError) as exc:
                fails[k] = fails.get(k, 0) + 1
                with pf.open("a") as fh:
                    fh.write(json.dumps({"market_id": r["market_id"], "day": day, "error": str(exc)[:120]}) + "\n")
                if fails[k] < cm.MAX_ITEM_ATTEMPTS:
                    fr.counts["request_failures"] = fr.counts.get("request_failures", 0) + 1
                    retry = True
                    continue
                rec = {"market_id": r["market_id"], "day": day, "status": "failed", "info": {"error": str(exc)[:120]}, "rows": []}
            c7.append_member(fr, part, rec)
            done.add(k)
            n = "n_day_" + rec["status"] if rec["rows"] or rec["status"] != "ok" else "n_day_empty"
            fr.counts[n] = fr.counts.get(n, 0) + 1
    return "pending_retry" if retry else None


def _finish(fr: cm.Cb8Run, rdir: Path, sample: list[dict]) -> None:
    """Write one file per market under ``screen/`` or ``holdout/``, then ``days.csv.gz`` (last), hash everything, drop the partials."""
    part = rdir / "days_partial.jsonl.gz"
    split_of = {r["market_id"]: r["split"] for r in sample}
    by_mkt: dict[str, list[dict]] = {}
    for rec in c6.iter_partial(part):
        by_mkt.setdefault(rec["market_id"], []).append(rec)
    for mid in sorted(by_mkt):
        recs = sorted(by_mkt[mid], key=lambda x: x["day"])
        p = rdir / split_of[mid] / f"{mid}.csv.gz"
        rows = sorted((x for rec in recs for x in rec["rows"] if rec["status"] == "ok"), key=lambda x: (x[0], x[1], x[2], x[3], x[4], x[7]))
        fr.budget.write_gz_csv(p, PRINT_COLUMNS, rows)
        fr.record_file(p)
    drows = [[rec["market_id"], rec["day"], rec["status"], rec["info"].get("pages", ""), rec["info"].get("n_raw", ""), len(rec["rows"]), rec["info"].get("malformed", ""),
              rec["info"].get("duplicates", ""), rec["info"].get("out_of_window", ""), rec["info"].get("missing_wallet", ""), rec["info"].get("order_ok", "")]
             for mid in sorted(by_mkt) for rec in sorted(by_mkt[mid], key=lambda x: x["day"])]
    dp = rdir / "days.csv.gz"
    fr.budget.write_gz_csv(dp, DAY_COLUMNS, drows)
    for name in ("frame.csv.gz", "sample.csv.gz", "split.json", "days.csv.gz"):
        fr.record_file(rdir / name)
    part.unlink(missing_ok=True)
    (rdir / "days_fail.jsonl").unlink(missing_ok=True)


# ---- q0168: the seal ----------------------------------------------------------------------------------------------------------------------------


def seal_copy_ids(seals_dir: Path, own: tuple[str, ...] = ("h9_flow_SEAL.json", "cb8_updown_holdout_SEAL.json")) -> tuple[set[str], list[str]]:
    """Market ids named in every committed seal copy under ``seals_dir`` except CB8's own (ids only)."""
    w = c4._cb2w()
    ids: set[str] = set()
    used: list[str] = []
    for p in sorted(Path(seals_dir).glob("*_SEAL.json")):
        if p.name in own:
            continue
        try:
            found = w.seal_ids_from_copy(p)
        except Exception:  # a seal copy with another file layout contributes no market ids
            continue
        if found:
            ids |= found
            used.append(p.name)
    return ids, used


def flow_seal(root: Path, run_id: str = RUN_ID, *, fp: str, transport=None, seals_dir: Path | None = None, trials_path: Path | None = None, rps: float = 2.0,
              sleep=time.sleep, live_check=None) -> dict:
    """q0168. Refuses unless the fetch is complete and every file matches its manifest hash and the pinned fingerprint. Seal-time drops
    (by id and by key, light Gamma lookup) against every seal copy committed by now are recorded as DROPPED_* blocks in
    ``drops.csv.gz``; sealed files are never edited. More than 2% of drop ids without metadata -> disjointness unverified (recorded)."""
    root = Path(root)
    cm.refuse_run_id(run_id, RUN_ID)
    cm.refuse_path(root)
    rdir = root / run_id
    seals_dir = Path(seals_dir or cm.SEALS_DIR)
    if (rdir / h5_seal.SEAL_NAME).exists():
        raise cm.Refused(f"{run_id} is already sealed")
    mp = rdir / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if not (man.get("complete") is True and not man.get("stopped") and man.get("status") == COMPLETE):
        raise cm.NotNow(f"{run_id} is not {COMPLETE} yet")
    if man.get("wallet_key_fingerprint") != fp:
        raise cm.Refused("manifest wallet_key_fingerprint differs from the pinned one; refusing to seal")
    n_checked = cm.verify_manifest_files(rdir, man)
    ids, used = seal_copy_ids(seals_dir)
    keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    missing_meta = 0
    if ids:
        if transport is None:
            raise cm.Refused("seal copies exist but no transport was given for the key lookup")
        lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = c6.lookup_keys(lim, sorted(ids))
        missing_meta = len(ids) - len(found)
        for k in found.values():
            if k.get("event_ids"):
                keys["event"].update(e for e in str(k["event_ids"]).split(";") if e)
            if k.get("neg_risk_market_id"):
                keys["neg_risk_market"].add(k["neg_risk_market_id"])
            keys["series"].update(s for s in str(k.get("series_ids") or "").split(";") if s)
    unverified = bool(ids) and missing_meta / len(ids) > MAX_UNVERIFIED_KEY_SHARE
    rows, n = [], {"KEPT": 0, "DROPPED_SEAL_COPIES": 0}
    for r in _read_sample(rdir / "sample.csv.gz"):
        why = (["id"] if r["market_id"] in ids else []) + c7.key_types_matched(r, keys)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            rows.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        else:
            n["KEPT"] += 1
    rows.sort()
    (rdir / "drops.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], rows))
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith("holdout/")}
    report = {"n_sample": n["KEPT"] + n["DROPPED_SEAL_COPIES"], "counts": n, "seal_copies_read": used, "drop_ids": len(ids), "drop_ids_without_metadata": missing_meta,
              "disjointness": UNVERIFIED if unverified else "verified", "fetched_files_rehashed": n_checked, "holdout_listing_sha256": h5_seal.listing_sha256(holdout),
              "holdout_files": len(holdout)}
    (rdir / "drops_report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    decl = {"dataset_role": "CB8 h9_flow: fresh print fetch with hashed wallets for the CB8-W screen; exploratory_historical, not prospective, not an edge claim",
            "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; the holdout/ directory is not opened before W1 advanced "
                          "and its Stage-1 result is committed; DROPPED_* blocks of drops.csv.gz are never read",
            "information_end": "every print ts < 2026-10-01T00:00Z"}
    extra = {"drops": report, "wallet_key_fingerprint": fp, "rules_sha256": man.get("rules_sha256"), "t_fetch": man.get("request_clock_now"),
             "exclusion_keys_sha256": (man.get("state") or {}).get("exclusion_keys_sha256")}
    seal = h5_seal.seal_run(rdir, trials_path=trials_path, declaration_base=decl, extra=extra, source="creative_batch_8:cb8_w_seal")
    copy = h5_seal.write_committed_copy(rdir, seals_dir)
    return {"run_id": run_id, "sealed": True, "listing_sha256": seal["listing_sha256"], "committed_copy": str(copy), "drop_counts": n,
            "disjointness": report["disjointness"], "holdout_listing_sha256": report["holdout_listing_sha256"]}


def iter_screen_prints(root: Path, run_id: str = RUN_ID) -> Iterator[tuple[str, list[str]]]:
    """Analysis-side accessor: SCREEN market files only (never HOLDOUT)."""
    d = Path(root) / run_id / "screen"
    for p in sorted(d.glob("*.csv.gz")) if d.exists() else []:
        with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
            for row in list(csv.reader(fh))[1:]:
                yield p.name[: -len(".csv.gz")], row


def rule_funcs() -> tuple:
    return (declared, flow_row, frame_reason, _walk_window, walk_frame, frame_days, draw_window, event_key, per_event_cap, event_split, flow_sample,
            assemble_sample, day_segments, _exclusion, smoke_ok, flow_fetch, _fetch_prints, _finish, seal_copy_ids, flow_seal, c7.key_types_matched,
            c7.is_weather, hb._rank, hb.allocate_weighted)
