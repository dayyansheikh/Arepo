# ruff: noqa: E501
"""CB10-B: round-level break reversals (docs/research_lab/CREATIVE_BATCH_10.md CB10-B, 1.2, 1.3, 1.4, 2.1-2.7, CB10-F q0204 / q0205 / q0206 /
q0207 B / q0209 / q0212).

Frame (whitelisted Gamma fields; no outcome field at all; ``vol_ok`` and the category labels computed in memory and only the derived values kept),
seeded 1,400-market sample (sports a reported stratum <= 15%), event split SCREEN / HOLDOUT before any print read; newest-first Data API prints
aggregated to transactions at fetch (YES-terms VWAP, size, time; no side, wallet or hash stored), kept only inside ``[2026-04-01, 2026-10-01)``, with
the covered span; HOLDOUT written to ``holdout/`` and sealed. Episodes: first print-confirmed crossings in 24 h of the real levels and their
``L +- 0.03`` pseudo-levels (side-free: transaction price, size and time only), 2-h same-arm spacing, 60-minute real/pseudo mutual exclusion,
``VWAP10``, the 2-h mark, ``R_e``; B1 per-pair contrast with census-frozen weights; B2 paper maker (not-posted rule, size-capped trade-through fills,
exit cost). Marks and fill P&L are attached only by the screen / rep jobs; the census receives counts. EXPLORATORY; no edge or profitability claim.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np

from . import cb8_common as cm
from . import cb10_common as c10
from . import history_backfill as hb

Refused = c10.Refused
NotNow = c10.NotNow
DAY = 86400.0
HOUR = 3600.0

# ---- frame (q0204) ---------------------------------------------------------------------------------------------------------------------------------
TX_WINDOW = ("2026-04-01", "2026-10-01")
END_WINDOW = ("2026-04-08", "2026-10-01")
MIN_OVERLAP_DAYS = 3.0
MIN_VOLUME = 10000.0
MAX_PER_EVENT = 3
N_SAMPLE = 1400
SPORTS_MAX_SHARE = 0.15
SPORTS_IN_PRIMARY = False
B_CATEGORIES: tuple[str, ...] | None = None  # CB10_B_CATEGORIES: None = every category not excluded below
SEED_SAMPLE = "arepo-cb10-brk-sample"
SEED_SPLIT = "arepo-cb10-brk-split"
SCREEN, HOLDOUT = "screen", "holdout"
PYTH_HOST = "pythdata.app"
CRYPTO_STRIKE_RE = r"\$\s?[\d,]+(?:\.\d+)?\s?[kKmM]?\b"
FRAME_RUN = "brk_frame"
PRINTS_RUN = "brk_prints"
FRAME_OUTPUT_CAP_GB = 0.005
PRINTS_OUTPUT_CAP_GB = 0.06
GAMMA_RPS = 2.0
DATA_LIMIT = 10000
DATA_PAGES = 2
TAKER_ONLY = "true"
SEAL_NAME = "holdout_SEAL.json"
SEAL_COPY_NAME = "cb10_brk_holdout_SEAL.json"
DROPS_FILE = "drops.csv.gz"
ACCESS_LOG = "ACCESS_LOG.jsonl"

# ---- episodes ---------------------------------------------------------------------------------------------------------------------------------------
LEVELS = (0.10, 0.25, 0.50, 0.75, 0.90)
PSEUDO_OFFSET = 0.03
MEMORY_S = 24 * HOUR
MIN_PRIOR_TX = 3
SPACING_S = 2 * HOUR
MUTEX_S = 3600.0
FOLLOW_S = 600.0
MARK_S = 2 * HOUR
MARK_MIN_S = 90 * 60.0
MARK30_S = 1800.0
MARK30_MIN_S = 1350.0  # 30-min robustness mark: last transaction at or before t_b + 30 min with time >= t_b + 22.5 min (the 2-h rule's 3/4; open item)
EPS = 1e-9

# ---- maker (B2) -------------------------------------------------------------------------------------------------------------------------------------
POST_S = 60.0
LATENCY_POST_S = 120.0
QUOTE_END_S = 600.0
QUOTE_SHARES = 100.0
QUOTE_OFFSET = 0.01
HALF_SPREAD = 0.015
HALF_SPREAD_ROBUST = 0.020
FEE_RATE_DEFAULT = 0.05
REBATE_SHARE = 0.2

# ---- tests, gates -----------------------------------------------------------------------------------------------------------------------------------
B1_FLOOR_C = 0.5
B2_FLOOR_C = 1.0
WORST_REAL_C = -1.0
WORST_PSEUDO_C = 1.0
WORST_B2_GROSS_C = -1.0
GB = {"real": 1000, "pseudo": 1000, "events": 100, "days": 60, "pair_min_each": 30}
GB2_FILLED = 300
AUDIT_PASS = 0.90
MONTH_MIN_EPISODES = 200
MONTH_SHARE = 2 / 3
CASCADE_RATIO_MIN = 1.2

FRAME_COLUMNS = ["market_id", "condition_id", "token_yes", "token_no", "yes_idx", "start_epoch", "end_epoch", "neg_risk", "neg_risk_market_id", "event_id", "event_ids",
                 "series_ids", "series_slugs", "fee_rate", "order_min_size", "desc_sha256", "topic", "fee_category", "vol_ok", "exclusion_class"]
SAMPLE_COLUMNS = [*FRAME_COLUMNS, "group", "stratum", "stratum_size", "stratum_alloc", "sample_weight", "split", "event_key"]
TX_COLUMNS = ["ts", "price", "size"]
MARKET_COLUMNS = ["market_id", "split", "event_key", "status", "oldest_ts", "truncated", "n_prints", "n_nohash", "n_tx_window", "span_start", "span_end", "covered"]
CENSUS_FORBIDDEN = ("m2h", "m30", "r_e", "r30", "vwap10", "net", "net_c", "pnl", "gross")


def pairs() -> dict[float, tuple[float, float]]:
    return {L: (round(L - PSEUDO_OFFSET, 2), round(L + PSEUDO_OFFSET, 2)) for L in LEVELS}


def level_table() -> list[tuple[float, str, float]]:
    """(level, arm, pair L) for every real and pseudo level."""
    out = [(L, "real", L) for L in LEVELS]
    for L, (a, b) in pairs().items():
        out += [(a, "pseudo", L), (b, "pseudo", L)]
    return sorted(out)


# =====================================================================================================================================
# Frame (q0204)
# =====================================================================================================================================


def brk_row(m: dict) -> dict | None:
    """Whitelisted B row (no outcome field at all). ``vol_ok`` (volumeNum >= 10,000), ``topic``, ``fee_category`` and the exclusion class are computed
    in memory from listing fields (``volumeNum``, ``feeType``, the first event title, the question, the slug and the resolution source) and only the
    derived values are kept."""
    from astrolabe.research_panel.pairing import fee_category  # noqa: PLC0415

    from . import cb7_common as c7  # noqa: PLC0415
    from . import history_topics  # noqa: PLC0415

    w = c10.whitelist_market(m)
    if w is None:
        return None
    ev = m.get("events") if isinstance(m.get("events"), list) else []
    title = str(ev[0].get("title") or "")[:300] if ev and isinstance(ev[0], dict) else ""
    fc = fee_category(m.get("feeType"))
    topic = history_topics.topic_of(w["question"], title, w["slug"], fc)
    vol = c10._num(m.get("volumeNum"))
    host = ""
    try:
        host = (urlparse(w["resolution_source"]).hostname or "").lower() if w["resolution_source"] else ""
    except ValueError:
        host = ""
    text = f"{w['question']} {title} {w['slug']}"
    cls = ""
    if c7.is_weather(fc or "", w["question"], title):
        cls = "weather"
    elif hb.CB1_UPDOWN_RE.search(text):
        cls = "crypto_updown"
    elif "multi-strikes" in w["series_slugs"] or (topic == "crypto" and re.search(CRYPTO_STRIKE_RE, w["question"])):
        cls = "crypto_strike_ladder"
    elif host == PYTH_HOST or host.endswith("." + PYTH_HOST):
        cls = "pyth"
    out = {**{k: w[k] for k in FRAME_COLUMNS if k in w}, "topic": topic, "fee_category": fc or "", "vol_ok": int(math.isfinite(vol) and vol >= MIN_VOLUME),
           "exclusion_class": cls}
    return {c: out.get(c, "") for c in FRAME_COLUMNS}


def overlap_days(r: dict) -> float:
    se, ee = c10._num(r.get("start_epoch")), c10._num(r.get("end_epoch"))
    if not (math.isfinite(se) and math.isfinite(ee)):
        return math.nan
    w0, w1 = cm.ep(TX_WINDOW[0] + "T00:00:00Z"), cm.ep(TX_WINDOW[1] + "T00:00:00Z")
    return max(0.0, min(ee, w1) - max(se, w0)) / DAY


def frame_reason(r: dict) -> str | None:
    ee = c10._num(r.get("end_epoch"))
    if not math.isfinite(ee) or not (cm.ep(END_WINDOW[0] + "T00:00:00Z") <= ee < cm.ep(END_WINDOW[1] + "T00:00:00Z")):
        return "end_outside_window"
    ov = overlap_days(r)
    if not math.isfinite(ov):
        return "no_dates"
    if ov < MIN_OVERLAP_DAYS:
        return "overlap_below_min"
    if str(r.get("vol_ok")) not in ("1", "True"):
        return "volume_below_min"
    if r.get("exclusion_class"):
        return str(r["exclusion_class"])
    if B_CATEGORIES is not None and r.get("topic") not in B_CATEGORIES and r.get("topic") != "sports":
        return "category_not_in_scope"
    return None


def _walk_window(lim: hb.Limiter, a: int, b: int, acc: dict) -> None:
    from . import cb4_data as c4  # noqa: PLC0415

    f = "%Y-%m-%dT%H:%M:%SZ"
    p = {"closed": "true", "volume_num_min": int(MIN_VOLUME), "order": "id", "ascending": "true",
         "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f)}
    batch, capped, failed = c4._paged_strict(lim, p, hb.GAMMA_OFFSET_CAP)
    if failed:
        acc["failed_windows"] += 1
        return
    if capped and b - a > 3600:
        acc["splits"] += 1
        mid = a + (b - a) // 2
        _walk_window(lim, a, mid, acc)
        _walk_window(lim, mid, b, acc)
        return
    acc["windows"] += 1
    if capped:
        acc["excluded_capped_window"] += 1
        return
    acc["batches"].extend(batch)


def assemble(frame: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], n: int = N_SAMPLE) -> tuple[list[dict], dict]:
    """Filters, id / key drops (the usual rule incl. series), <= 3 per event, seeded sample (sports stratum <= 15%), event split. Before any print."""
    from . import cb8_flow as fl  # noqa: PLC0415

    rep: dict = {"n_frame_in": len(frame), "filtered": {}}
    kept = []
    for r in frame:
        why = frame_reason(r)
        if why:
            rep["filtered"][why] = rep["filtered"].get(why, 0) + 1
        else:
            kept.append(r)
    after, drops = c10.drop_by_keys(kept, excl_ids, excl_keys)
    rep["drops"] = drops
    capped, n_cap = fl.per_event_cap(after, SEED_SAMPLE, MAX_PER_EVENT)
    rep["capped_out_per_event"] = n_cap
    pool_sports = sum(1 for r in capped if r.get("topic") == "sports")
    n_eff = min(n, len(capped))
    n_sports = min(pool_sports, int(math.floor(SPORTS_MAX_SHARE * n)), int(round(n_eff * pool_sports / len(capped)))) if capped else 0
    n_main = min(n_eff - n_sports, len(capped) - pool_sports)
    sample, srep = fl.flow_sample(capped, n_main, n_sports, SEED_SAMPLE)
    rep["sample"] = {**srep, "n_main": n_main, "n_sports": n_sports, "pool_sports": pool_sports}
    out = [{**r, "split": fl.event_split(r, SEED_SPLIT), "event_key": fl.event_key(r)} for r in sample]
    out.sort(key=lambda x: x["market_id"])
    rep.update(n_sample=len(out), n_screen=sum(1 for r in out if r["split"] == SCREEN), n_holdout=sum(1 for r in out if r["split"] == HOLDOUT),
               events={s: len({r["event_key"] for r in out if r["split"] == s}) for s in (SCREEN, HOLDOUT)})
    return out, rep


def _done(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
    mp = Path(rdir) / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None and prior.get("status") in statuses:
        return prior
    return None


def _in_progress(fr: cm.Cb8Run, why: str) -> dict:
    m = fr.manifest(why, {"transient": True})
    m["status"] = "in_progress"
    return m


def brk_frame(root: Path, transport, *, rules_sha: str, smoke_path: Path, exclusion_keys_path: Path, now: float, n: int = N_SAMPLE, rps: float = GAMMA_RPS,
                    disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None,
                    wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                    data_dumps_cap_gb: float = c10.DATA_DUMPS_CAP_GB, free_fn=None, t_seal_epoch: float = c10.T_SEAL_EPOCH) -> dict:
    """q0204, one resumable chunk: one-day endDate windows (capped windows split down to one hour; a 1-hour capped window is excluded and counted),
    the whitelisted rows, then the filters, key drops, cap, sample and split (``split.json`` / ``sample.csv.gz``) before any print request."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb10_dlad as dl  # noqa: PLC0415

    c10.require_after_t_seal(now, "brk-frame", t_seal_epoch)
    root = c10.refuse_path(Path(root))
    rdir = root / FRAME_RUN
    st = c10.stall_of(rdir)
    if st:
        return st
    done = _done(rdir, ("brk_frame_complete",))
    if done:
        return {"stopped": None, "status": done["status"], "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    bad = dl.smoke_failures(smoke_path, ("data_api_paging", "tx_aggregation", "whitelist"))
    if bad:
        return c10.write_stall(rdir, c10.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c10.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c10.UNVERIFIED:
        return c10.write_stall(rdir, c10.STALL_DISJOINTNESS, "q0201: > 2% of exclusion ids without metadata (design 1.3)")
    c10.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(root, FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb10_brk_frame", label="CB10-B frame",
                     params={"n": n, "exclusion_keys_sha256": ksha, "evidence_role": c10.EVIDENCE_ROLE_HIST}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap,
                     rps=min(rps, GAMMA_RPS), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    try:
        pp, pf = rdir / "frame_partial.jsonl.gz", rdir / "frame_fail.jsonl"
        have = {rec["day"] for rec in c6.iter_partial(pp)}
        fails = c7.walk_failed_days(pf)
        days = c10.days_between(*END_WINDOW)
        for d in days:
            if d in have or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return _in_progress(fr, why)
            a = int(cm.ep(d + "T00:00:00Z"))
            acc = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "excluded_capped_window": 0}
            _walk_window(fr.lim, a, a + int(DAY), acc)
            if acc["failed_windows"]:
                with pf.open("a") as fh:
                    fh.write(json.dumps({"day": d}) + "\n")
                continue
            raw = [m for m in acc["batches"] if isinstance(m, dict)]
            rows = [x for x in (brk_row(m) for m in raw) if x is not None]
            c7.append_member(fr, pp, {"day": d, "rows": rows, "n_raw": len(raw), "excluded_capped_window": acc["excluded_capped_window"], "splits": acc["splits"]})
        fails = c7.walk_failed_days(pf)
        recs = list(c6.iter_partial(pp))
        if not all(d in {r["day"] for r in recs} or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS for d in days):
            return _in_progress(fr, "frame_paused")
        frame = [r for rec in recs for r in rec["rows"]]
        sample, rep = assemble(frame, ids, keys, n)
        rep["walk"] = {"days": len(days), "frame_rows": len(frame), "excluded_capped_window": sum(r["excluded_capped_window"] for r in recs),
                       "failed_days": sorted(d for d, k in fails.items() if k >= cm.MAX_ITEM_ATTEMPTS)}
        fr.budget.write_gz_csv(rdir / "frame.csv.gz", FRAME_COLUMNS, ([r.get(c, "") for c in FRAME_COLUMNS] for r in frame))
        fr.budget.write(rdir / "split.json", json.dumps({"seeds": {"sample": SEED_SAMPLE, "split": SEED_SPLIT}, "report": rep,
                                                         "events": {r["event_key"]: r["split"] for r in sample}}, indent=1, sort_keys=True, default=float).encode())
        fr.budget.write_gz_csv(rdir / "sample.csv.gz", SAMPLE_COLUMNS, ([r.get(c, "") for c in SAMPLE_COLUMNS] for r in sample))
        for name in ("frame.csv.gz", "split.json", "sample.csv.gz"):
            fr.record_file(rdir / name)
        pp.unlink(missing_ok=True)
        pf.unlink(missing_ok=True)
        fr.counts.update(n_sample=rep["n_sample"], n_screen=rep["n_screen"], n_holdout=rep["n_holdout"])
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": "brk_frame_complete"})
    m["status"] = "brk_frame_complete"
    return m



def read_sample(frame_dir: Path) -> list[dict]:
    from . import cb7_common as c7  # noqa: PLC0415

    return [dict(r) for r in c7.read_csv_gz(Path(frame_dir) / "sample.csv.gz")]


# =====================================================================================================================================
# Prints (q0205): transactions per market; HOLDOUT to holdout/
# =====================================================================================================================================


def market_span(r: dict, oldest_ts: float, truncated: bool) -> tuple[float, float, bool]:
    """Covered span inside the window: ``[max(W0, oldest reachable if truncated), W1)``; ``covered`` iff the whole in-window life is reachable."""
    w0, w1 = cm.ep(TX_WINDOW[0] + "T00:00:00Z"), cm.ep(TX_WINDOW[1] + "T00:00:00Z")
    start = max(w0, oldest_ts) if (truncated and math.isfinite(oldest_ts)) else w0
    life0 = max(w0, c10._num(r.get("start_epoch")) if math.isfinite(c10._num(r.get("start_epoch"))) else w0)
    covered = (not truncated) or (math.isfinite(oldest_ts) and oldest_ts <= life0)
    return start, w1, bool(covered)


def brk_prints(root: Path, transport, *, rules_sha: str, frame_dir: Path, now: float, rps: float = 2.0, disk_cap: int = int(PRINTS_OUTPUT_CAP_GB * 1024**3),
               budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None,
               health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c10.DATA_DUMPS_CAP_GB, free_fn=None,
               t_seal_epoch: float = c10.T_SEAL_EPOCH) -> dict:
    """q0205, one resumable chunk: per sampled market (one in memory at a time) the newest-first prints -> transactions (YES terms) inside the window,
    written to ``screen/<id>.tx.csv.gz`` or ``holdout/<id>.tx.csv.gz``; ``markets.csv.gz`` holds the covered span and truncation flags."""
    from . import cb10_dlad as dl  # noqa: PLC0415

    c10.require_after_t_seal(now, "brk-prints", t_seal_epoch)
    root = c10.refuse_path(Path(root))
    rdir = root / PRINTS_RUN
    st = c10.stall_of(rdir)
    if st:
        return st
    up = c10.upstream_stall(rdir, Path(frame_dir))
    if up:
        return up
    if not _done(Path(frame_dir), ("brk_frame_complete",)):
        raise NotNow("q0205 waits for q0204 (brk_frame) to finish")
    done = _done(rdir, ("brk_prints_complete",))
    if done:
        return {"stopped": None, "status": "brk_prints_complete", "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c10.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(root, PRINTS_RUN, transport, allowed_run_id=PRINTS_RUN, kind="cb10_brk_prints", label="CB10-B prints",
                     params={"window": list(TX_WINDOW), "evidence_role": c10.EVIDENCE_ROLE_HIST}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap,
                     rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    w0, w1 = cm.ep(TX_WINDOW[0] + "T00:00:00Z"), cm.ep(TX_WINDOW[1] + "T00:00:00Z")
    try:
        mp = rdir / "markets_partial.jsonl"
        have = {}
        if mp.exists():
            for line in mp.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    have[rec["market_id"]] = rec
        for r in read_sample(frame_dir):
            if r["market_id"] in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return _in_progress(fr, why)
            try:
                prints, info = dl.fetch_market_prints(fr.lim, r["condition_id"], limit=DATA_LIMIT, pages=DATA_PAGES)
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[r["market_id"]] = fails.get(r["market_id"], 0) + 1
                if fails[r["market_id"]] < cm.MAX_ITEM_ATTEMPTS:
                    return _in_progress(fr, f"prints_failed {r['market_id']}: {exc}"[:200])
                rec = {"market_id": r["market_id"], "split": r["split"], "event_key": r["event_key"], "status": "fetch_failed", "oldest_ts": math.nan, "truncated": 1,
                       "n_prints": 0, "n_nohash": 0, "n_tx_window": 0, "span_start": math.nan, "span_end": math.nan, "covered": 0}
                with mp.open("a") as fh:
                    fh.write(json.dumps(rec, default=float) + "\n")
                continue
            tx = [x for x in dl.aggregate_transactions(prints, int(r["yes_idx"])) if w0 <= x[0] < w1]
            del prints
            s0, s1, cov = market_span(r, info["oldest_ts"], info["truncated"])
            sub = HOLDOUT if r["split"] == HOLDOUT else SCREEN
            p = rdir / sub / f"{r['market_id']}.tx.csv.gz"
            fr.budget.write_gz_csv(p, TX_COLUMNS, ([x[0], x[1], x[2]] for x in tx))
            fr.record_file(p)
            rec = {"market_id": r["market_id"], "split": r["split"], "event_key": r["event_key"], "status": "ok", "oldest_ts": info["oldest_ts"],
                   "truncated": int(info["truncated"]), "n_prints": info["n_prints"], "n_nohash": info["n_nohash"], "n_tx_window": len(tx), "span_start": s0,
                   "span_end": s1, "covered": int(cov)}
            with mp.open("a") as fh:
                fh.write(json.dumps(rec, default=float) + "\n")
            have[r["market_id"]] = rec
        recs = [json.loads(line) for line in mp.read_text().splitlines() if line.strip()] if mp.exists() else []
        fr.budget.write_gz_csv(rdir / "markets.csv.gz", MARKET_COLUMNS, ([rec[c] for c in MARKET_COLUMNS] for rec in sorted(recs, key=lambda x: x["market_id"])))
        fr.record_file(rdir / "markets.csv.gz")
        mp.unlink(missing_ok=True)
        fr.counts.update(markets=len(recs), truncated=sum(int(x["truncated"]) for x in recs))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": "brk_prints_complete"})
    m["status"] = "brk_prints_complete"
    return m


# =====================================================================================================================================
# Seal (q0206)
# =====================================================================================================================================


def brk_seal(root: Path, *, rules_sha: str, frame_dir: Path, transport=None, seals_dir: Path | None = None, rps: float = 2.0, sleep=time.sleep, live_check=None,
             is_committed: Callable[[Path], bool] | None = None) -> dict:
    """q0206. Refuses unless brk-prints finished and every file matches its manifest. Seal-time drops (id and key, light Gamma lookup) against every
    seal copy committed by now except CB10's own, recorded as ``DROPPED_SEAL_COPIES`` rows (sealed files never edited); ``holdout_SEAL.json`` with the
    HOLDOUT listing sha256 and the committed copy ``seals/cb10_brk_holdout_SEAL.json`` (never rewritten)."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    root = c10.refuse_path(Path(root))
    rdir = root / PRINTS_RUN
    seals_dir = Path(seals_dir or c10.SEALS_DIR)
    st = c10.stall_of(rdir)
    if st:  # the prints run stalled (upstream): nothing to seal; the label passes on to the census
        return {**st, "status": st["status"], "sealed": False}
    sp = rdir / SEAL_NAME
    if sp.exists():
        doc = json.loads(sp.read_text())
        return {"status": "brk_sealed", "listing_sha256": doc["listing_sha256"], "already_sealed": True}
    man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
    if not (man.get("complete") is True and not man.get("stopped") and man.get("status") == "brk_prints_complete"):
        raise NotNow(f"{PRINTS_RUN} is not finished yet (status {man.get('status')})")
    n_checked = cm.verify_manifest_files(rdir, man)
    ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=c10.OWN_SEAL_COPIES, is_committed=is_committed)
    keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    missing = 0
    if ids:
        if transport is None:
            raise Refused("seal copies exist but no transport was given for the key lookup")
        lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = c6.lookup_keys(lim, sorted(ids))
        missing = len(ids) - len(found)
        for k in found.values():
            keys["event"].update(e for e in str(k.get("event_ids") or "").split(";") if e)
            if k.get("neg_risk_market_id"):
                keys["neg_risk_market"].add(k["neg_risk_market_id"])
            keys["series"].update(s for s in str(k.get("series_ids") or "").split(";") if s)
    unverified = bool(ids) and missing / len(ids) > c10.MAX_UNVERIFIED_KEY_SHARE
    sample = read_sample(frame_dir)
    rows, n = [], {"KEPT": 0, "DROPPED_SEAL_COPIES": 0}
    for r in sample:
        why = (["id"] if r["market_id"] in ids else []) + c7.key_types_matched(r, keys)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            rows.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        else:
            n["KEPT"] += 1
    rows.sort()
    (rdir / DROPS_FILE).write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], rows))
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(HOLDOUT + "/")}
    doc = {"seal_version": "cb10-brk-holdout-seal-v1", "run_id": PRINTS_RUN, "sealed_utc": cm.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": rules_sha,
           "prints_rules_sha256": man.get("rules_sha256"), "listing_sha256": h5_seal.listing_sha256(holdout), "n_holdout_files": len(holdout),
           "files": dict(sorted(holdout.items())), "fetched_files_rehashed": n_checked,
           "drops": {"counts": n, "seal_copies_read": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "drop_ids": len(ids),
                     "drop_ids_without_metadata": missing, "disjointness": c10.UNVERIFIED if unverified else "verified", "drops_sha256": h5_seal.sha256_file(rdir / DROPS_FILE)},
           "frame_market_ids": {s: sorted(r["market_id"] for r in sample if r["split"] == s) for s in (SCREEN, HOLDOUT)},
           "frame_manifest_sha256": h5_seal.sha256_file(Path(frame_dir) / "manifest.json"),
           "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; holdout/ is not opened before B1 or B2 advanced and its Stage-1 result is "
                         "committed; markets in DROPPED_* rows of drops.csv.gz are never analysed; the census reads HOLDOUT file and event counts only"}
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    dest = seals_dir / SEAL_COPY_NAME
    if dest.exists() and dest.read_bytes() != data:
        raise Refused(f"{dest} exists with different content; a seal is never rewritten")
    sp.write_bytes(data)
    (rdir / ACCESS_LOG).touch()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"status": "brk_sealed", "listing_sha256": doc["listing_sha256"], "committed_copy": str(dest), "drop_counts": n, "disjointness": doc["drops"]["disjointness"],
            "n_holdout_files": len(holdout)}


def verify_holdout_seal(rdir: Path, seals_dir: Path | None = None) -> dict:
    from . import h5_seal  # noqa: PLC0415

    rdir = Path(rdir)
    sp = rdir / SEAL_NAME
    if not sp.exists():
        raise Refused(f"{rdir.name} has no {SEAL_NAME}; run brk-seal first")
    copy = Path(seals_dir or c10.SEALS_DIR) / SEAL_COPY_NAME
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise Refused(f"seal copy {copy} missing or different from {sp}")
    doc = json.loads(sp.read_text())
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(HOLDOUT + "/")}
    if h5_seal.listing_sha256(holdout) != doc["listing_sha256"]:
        raise Refused("HOLDOUT listing sha256 differs from the seal; refusing")
    return doc


def _guard_split(split: str, job: str) -> None:
    if split not in (SCREEN, HOLDOUT):
        raise Refused(f"unknown split {split!r}")
    if split == HOLDOUT and job != "rep-B":
        raise Refused("HOLDOUT is sealed: only rep-B opens it, after B1 or B2 advanced and its Stage-1 result is committed")


def holdout_counts(rdir: Path) -> dict:
    """Census access to HOLDOUT: file and event counts only (the files are listed, never opened)."""
    from . import cb7_common as c7  # noqa: PLC0415

    files = sorted((Path(rdir) / HOLDOUT).glob("*.tx.csv.gz"))
    mk = [r for r in c7.read_csv_gz(Path(rdir) / "markets.csv.gz") if r["split"] == HOLDOUT]
    return {"n_files": len(files), "n_markets": len(mk), "n_events": len({r["event_key"] for r in mk})}


def load_market_tx(rdir: Path, split: str, market_id: str, *, job: str) -> dict[str, np.ndarray]:
    _guard_split(split, job)
    p = Path(rdir) / split / f"{market_id}.tx.csv.gz"
    ts, pr, sz = [], [], []
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ts.append(float(r["ts"]))
            pr.append(float(r["price"]))
            sz.append(float(r["size"]))
    o = np.argsort(np.array(ts), kind="stable")
    return {"ts": np.array(ts)[o], "price": np.array(pr)[o], "size": np.array(sz)[o]}


def log_access(rdir: Path, job: str, files: list[str]) -> None:
    with (Path(rdir) / ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "files": files}) + "\n")


# =====================================================================================================================================
# Episodes (side-free; transaction price, size and time only)
# =====================================================================================================================================


def detect_episodes(tx: dict[str, np.ndarray], span: tuple[float, float]) -> tuple[list[dict], dict]:
    """First print-confirmed crossings. A down-break of level ``L`` at transaction ``j``: previous price >= L and ``p_j < L``; an up-break: previous
    <= L and ``p_j > L`` (equality at the level is not a crossing). Eligible iff no earlier crossing of ``L`` (either direction) at a time in
    ``[t_j - 24 h, t_j]`` (earlier transactions at the same second count as earlier), >= 3 transactions in ``[t_j - 24 h, t_j)``, ``[t_j - 24 h, t_j
    + 2 h]`` inside the covered span, and no earlier eligible episode of the same arm (real / pseudo, any level) in the market at ``t_j - 2 h`` or
    later. Then the 60-minute mutual exclusion drops both members of every real/pseudo pair within 60 minutes. Returns episodes WITHOUT any value
    after the break (marks and fills are attached by ``attach_*``)."""
    ts, pr = tx["ts"], tx["price"]
    n = len(ts)
    cnt = {"crossings": 0, "not_first_24h": 0, "few_prior_tx": 0, "outside_span": 0, "spacing": 0, "mutual_exclusion": 0}
    cands = []
    for L, arm, pair in level_table():
        for j in range(1, n):
            a, b = pr[j - 1], pr[j]
            if a >= L - EPS and b < L - EPS:
                s = 1
            elif a <= L + EPS and b > L + EPS:
                s = -1
            else:
                continue
            cands.append((j, L, arm, pair, s))
    cands.sort(key=lambda x: (x[0], x[1]))
    last_cross: dict[float, list[int]] = {}
    last_elig: dict[str, float] = {}
    elig = []
    for j, L, arm, pair, s in cands:
        cnt["crossings"] += 1
        t = ts[j]
        prior = last_cross.setdefault(L, [])
        first = not any(ts[i] >= t - MEMORY_S for i in prior)
        prior.append(j)
        if not first:
            cnt["not_first_24h"] += 1
            continue
        k0 = int(np.searchsorted(ts, t - MEMORY_S, side="left"))
        k1 = int(np.searchsorted(ts, t, side="left"))
        if k1 - k0 < MIN_PRIOR_TX:
            cnt["few_prior_tx"] += 1
            continue
        if t - MEMORY_S < span[0] or t + MARK_S > span[1]:
            cnt["outside_span"] += 1
            continue
        if arm in last_elig and t - last_elig[arm] <= SPACING_S:
            cnt["spacing"] += 1
            continue
        last_elig[arm] = t
        elig.append({"j": j, "t_b": float(t), "level": L, "arm": arm, "pair": pair, "s": s})
    real = [e for e in elig if e["arm"] == "real"]
    pseu = [e for e in elig if e["arm"] == "pseudo"]
    drop = set()
    for i, r in enumerate(real):
        for k, q in enumerate(pseu):
            if abs(r["t_b"] - q["t_b"]) <= MUTEX_S:
                drop.add(("r", i))
                drop.add(("q", k))
    out = [e for i, e in enumerate(real) if ("r", i) not in drop] + [e for k, e in enumerate(pseu) if ("q", k) not in drop]
    cnt["mutual_exclusion"] = len(drop)
    out.sort(key=lambda e: (e["t_b"], e["level"]))
    for e in out:
        e["day"] = c10.utc_day(e["t_b"])
        e["month"] = e["day"][:7]
    return out, cnt


def _after(ts: np.ndarray, t: float) -> int:
    return int(np.searchsorted(ts, t, side="right"))


def follow_through(tx: dict[str, np.ndarray], e: dict) -> bool:
    ts = tx["ts"]
    a, b = _after(ts, e["t_b"]), _after(ts, e["t_b"] + FOLLOW_S)
    return b > a


def _mark_avail(tx: dict[str, np.ndarray], e: dict, horizon: float, min_s: float) -> int | None:
    ts = tx["ts"]
    k = _after(ts, e["t_b"] + horizon) - 1
    return k if k >= 0 and ts[k] >= e["t_b"] + min_s else None


def maker_fills(tx: dict[str, np.ndarray], e: dict, *, post_s: float = POST_S, quote_off: float = QUOTE_OFFSET) -> dict:
    """B2 paper quote at ``t_b + post_s``: down-break -> bid at ``L - 0.01``, up-break -> ask at ``L + 0.01``, 100 shares, live until ``t_b + 10 min``.
    Not posted if the last transaction at or before the post time is at or through the quote. Fills: each transaction strictly through the quote in
    ``(post, t_b + 10 min]`` fills ``min(remaining, its size)``; a transaction at the quote fills nothing."""
    ts, pr, sz = tx["ts"], tx["price"], tx["size"]
    tp = e["t_b"] + post_s
    k = _after(ts, tp) - 1
    if e["s"] == 1:
        q = round(e["level"] - quote_off, 6)
        through = (lambda p: p < q - EPS)  # noqa: E731
        at_or_through = pr[k] <= q + EPS if k >= 0 else False
    else:
        q = round(e["level"] + quote_off, 6)
        through = (lambda p: p > q + EPS)  # noqa: E731
        at_or_through = pr[k] >= q - EPS if k >= 0 else False
    if at_or_through:
        return {"posted": False, "quote": q, "filled": 0.0}
    rem = QUOTE_SHARES
    for i in range(_after(ts, tp), _after(ts, e["t_b"] + QUOTE_END_S)):
        if rem <= 0:
            break
        if through(pr[i]):
            rem -= min(rem, sz[i])
    return {"posted": True, "quote": q, "filled": QUOTE_SHARES - rem}


def attach_counts(tx: dict[str, np.ndarray], e: dict) -> dict:
    """Census view of one episode: follow-through, mark availability (booleans) and maker counts. No price after the break leaves here."""
    out = {k: e[k] for k in ("t_b", "level", "arm", "pair", "s", "day", "month")}
    out["follow"] = follow_through(tx, e)
    out["has_m2h"] = _mark_avail(tx, e, MARK_S, MARK_MIN_S) is not None
    if e["arm"] == "real" and out["follow"]:
        f = maker_fills(tx, e)
        out.update(posted=f["posted"], filled_shares=f["filled"])
    return out


def exit_cost(m: float, rate: float, half_spread: float = HALF_SPREAD) -> float:
    return rate * m * (1.0 - m) + half_spread


def attach_marks(tx: dict[str, np.ndarray], e: dict, fee_rate_b: float) -> dict:
    """Screen / rep view: VWAP10, M2h, M30, R_e and R30 (cents), the 10-minute cascade counts, and for real episodes the maker P&L per filled share
    (primary, 2.0c half-spread robustness, +120 s latency, rebate version)."""
    ts, pr, sz = tx["ts"], tx["price"], tx["size"]
    out = attach_counts(tx, e)
    a, b = _after(ts, e["t_b"]), _after(ts, e["t_b"] + FOLLOW_S)
    out["n_tx10"], out["vol10"] = b - a, float(sz[a:b].sum())
    if b <= a:
        return out
    out["vwap10"] = float((pr[a:b] * sz[a:b]).sum() / sz[a:b].sum())
    k = _mark_avail(tx, e, MARK_S, MARK_MIN_S)
    out["m2h"] = float(pr[k]) if k is not None else None
    k30 = _mark_avail(tx, e, MARK30_S, MARK30_MIN_S)
    out["m30"] = float(pr[k30]) if k30 is not None else None
    out["r_e"] = 100 * e["s"] * (out["m2h"] - out["vwap10"]) if out["m2h"] is not None else None
    out["r30"] = 100 * e["s"] * (out["m30"] - out["vwap10"]) if out["m30"] is not None else None
    rate = fee_rate_b if math.isfinite(fee_rate_b) else FEE_RATE_DEFAULT
    rec_rate = fee_rate_b if math.isfinite(fee_rate_b) else 0.0

    def pnl(f: dict, mark: float | None, hs: float) -> float | None:
        if not f["posted"] or f["filled"] <= 0 or mark is None:
            return None
        gross = (mark - f["quote"]) if e["s"] == 1 else (f["quote"] - mark)
        return 100 * (gross - exit_cost(mark, rate, hs))

    f = maker_fills(tx, e)
    out["maker"] = {"posted": f["posted"], "quote": f["quote"], "filled": f["filled"], "net_c": pnl(f, out["m2h"], HALF_SPREAD),
                    "net_c_hs20": pnl(f, out["m2h"], HALF_SPREAD_ROBUST), "net_c_m30": pnl(f, out["m30"], HALF_SPREAD),
                    "rebate_c": 100 * REBATE_SHARE * rec_rate * f["quote"] * (1 - f["quote"]) if f["filled"] > 0 else 0.0,
                    "gross_c": (100 * ((out["m2h"] - f["quote"]) if e["s"] == 1 else (f["quote"] - out["m2h"]))) if (f["filled"] > 0 and out["m2h"] is not None) else None,
                    "worst_c": 100 * (WORST_B2_GROSS_C / 100 - exit_cost(0.5, rate, HALF_SPREAD)) if f["filled"] > 0 else None}
    fl = maker_fills(tx, e, post_s=LATENCY_POST_S)
    out["maker_latency"] = {"posted": fl["posted"], "filled": fl["filled"], "net_c": pnl(fl, out["m2h"], HALF_SPREAD)}
    return out


# =====================================================================================================================================
# Census (q0207 B)
# =====================================================================================================================================


def census_b(eps: list[dict], markets: list[dict], holdout: dict) -> dict:
    """Counts only (no mark, reversal or fill P&L): SCREEN episodes by arm and pair, follow-through, mark availability, B2 posted / filled / filled
    shares, the frozen B1 weights ``w_L = n_L / sum n`` (n_L = eligible real episodes with follow-through; a pair with < 30 real or < 30 pseudo
    episodes gets w_L = 0, counted; no renormalisation), gates GB, GB2 and the coverage audit (>= 90%)."""
    for e in eps:
        if any(k in e for k in CENSUS_FORBIDDEN) or "maker" in e:
            raise Refused("census received a mark, reversal or fill P&L field")
    units = [e for e in eps if e["follow"]]
    by: dict[str, dict[str, int]] = {}
    for e in eps:
        k = f"{e['arm']}|{e['pair']}"
        d = by.setdefault(k, {"episodes": 0, "follow": 0, "has_m2h": 0})
        d["episodes"] += 1
        d["follow"] += int(e["follow"])
        d["has_m2h"] += int(e["follow"] and e["has_m2h"])
    n_real = {L: sum(1 for e in units if e["arm"] == "real" and e["pair"] == L) for L in LEVELS}
    n_pseu = {L: sum(1 for e in units if e["arm"] == "pseudo" and e["pair"] == L) for L in LEVELS}
    tot = sum(n_real.values())
    w = {}
    zeroed = []
    for L in LEVELS:
        ok = n_real[L] >= GB["pair_min_each"] and n_pseu[L] >= GB["pair_min_each"]
        w[L] = (n_real[L] / tot) if (tot and ok) else 0.0
        if not ok:
            zeroed.append(L)
    real_follow = [e for e in units if e["arm"] == "real"]
    posted = sum(1 for e in real_follow if e.get("posted"))
    filled = [e for e in real_follow if (e.get("filled_shares") or 0) > 0]
    gb = {"real": sum(n_real.values()), "pseudo": sum(n_pseu.values()), "events": len({e["event_key"] for e in units}), "days": len({e["day"] for e in units})}
    gb_ok = gb["real"] >= GB["real"] and gb["pseudo"] >= GB["pseudo"] and gb["events"] >= GB["events"] and gb["days"] >= GB["days"] and any(w.values())
    gb2_ok = len(filled) >= GB2_FILLED
    scr = [m for m in markets if m["split"] == SCREEN]
    cov = sum(1 for m in scr if str(m.get("covered")) in ("1", "True"))
    audit_share = cov / len(scr) if scr else 0.0
    audit = {"screen_markets": len(scr), "covered": cov, "share": audit_share, "pass": bool(scr) and audit_share >= AUDIT_PASS, "threshold": AUDIT_PASS,
             "truncated": sum(1 for m in scr if str(m.get("truncated")) in ("1", "True"))}

    def lab(ok: bool) -> str | None:
        if not audit["pass"]:
            return "not testable (source limited)"
        return None if ok else "not testable (no opportunity: round-level breaks are rare)"

    return {"by_arm_pair": by, "n_real_by_pair": {str(k): v for k, v in n_real.items()}, "n_pseudo_by_pair": {str(k): v for k, v in n_pseu.items()},
            "weights_frozen": {str(k): v for k, v in w.items()}, "pairs_zeroed": zeroed, "gate_GB": gb, "gate_GB_pass": gb_ok,
            "b2": {"eligible": len(real_follow), "not_posted": len(real_follow) - posted, "posted": posted, "filled_episodes": len(filled),
                   "filled_shares": float(sum(e["filled_shares"] for e in filled))}, "gate_GB2_pass": gb2_ok, "coverage_audit": audit, "holdout": holdout,
            "label_B1": lab(gb_ok), "label_B2": lab(gb_ok and gb2_ok)}


# =====================================================================================================================================
# Screen (q0209) / rep (q0212)
# =====================================================================================================================================


def _ways(us: list[dict]) -> dict[str, np.ndarray]:
    return {"event": np.array([u["event_key"] for u in us]), "day": np.array([u["day"] for u in us])}


def b1_estimate(us: list[dict], w: dict[float, float], *, vals: np.ndarray | None = None, arms: list[str] | None = None) -> tuple[np.ndarray, float, dict]:
    v = np.array([u["r_e"] for u in us], float) if vals is None else vals
    return c10.contrast_pseudo(v, arms or [u["arm"] for u in us], [u["pair"] for u in us], w)


def _months_ok(us: list[dict], fn: Callable[[list[dict]], float], sign: float) -> dict:
    res = {}
    for mth in sorted({u["month"] for u in us}):
        sub = [u for u in us if u["month"] == mth]
        if len(sub) >= MONTH_MIN_EPISODES:
            res[mth] = fn(sub)
    agree = sum(1 for x in res.values() if math.isfinite(x) and np.sign(x) == np.sign(sign))
    return {"months": res, "holds": bool(res) and agree >= MONTH_SHARE * len(res)}


def b1_stat(eps: list[dict], w: dict[float, float], *, n_draws: int = c10.PLACEBO_DRAWS) -> dict:
    """B1 = sum_L w_L C_L (cents), census-frozen weights; p = max over the event and UTC-day ways; floor +0.5c; binding: the label-swap calibration
    (one coin per event, and per day), the worst-case missing marks (real -1c, pseudo +1c), the 30-min mark, top-5 drops, 10-min-volume weighting
    and month signs. Cascade descriptive labels only."""
    pos = {L: x for L, x in w.items() if x > 0}
    base_units = [e for e in eps if e["follow"] and e["pair"] in pos]
    us = [e for e in base_units if e.get("r_e") is not None]
    miss = [e for e in base_units if e.get("r_e") is None]
    res: dict[str, Any] = {"n_units": len(us), "n_missing_mark": {a: sum(1 for e in miss if e["arm"] == a) for a in ("real", "pseudo")}}
    if len(us) < 2:
        return {**res, "testable": False, "p": 1.0, "advance": False, "verdict": "not testable"}
    v, est, C = b1_estimate(us, pos)
    cl = _ways(us)
    base = c10.cluster_p(v, cl)
    res.update(b1_cents=est, per_pair_cents={str(k): x for k, x in C.items()}, p=base["p"], testable=base["testable"], ways=base.get("ways"))
    if not base["testable"]:
        return {**res, "advance": False, "verdict": "not testable"}
    pls = {}
    for name, key in (("event", "event_key"), ("day", "day")):
        rng = np.random.default_rng(c10.PLACEBO_SEEDS[f"B1_swap_{name}"])
        groups = sorted({u[key] for u in us})
        gi = np.array([groups.index(u[key]) for u in us])
        ps = []
        for _ in range(n_draws):
            flip = rng.random(len(groups)) < 0.5
            arms = ["pseudo" if (flip[g] and u["arm"] == "real") else ("real" if (flip[g] and u["arm"] == "pseudo") else u["arm"]) for u, g in zip(us, gi, strict=True)]
            vv, _, _ = b1_estimate(us, pos, arms=arms)
            ps.append(c10.cluster_p(vv, cl, alpha=c10.GATE_P)["p"])
        pls[name] = c10.placebo_advance_rate(ps)
    allu = us + miss
    vals = np.array([e["r_e"] if e.get("r_e") is not None else (WORST_REAL_C if e["arm"] == "real" else WORST_PSEUDO_C) for e in allu], float)
    vw, ew, _ = b1_estimate(allu, pos, vals=vals)
    rw = c10.cluster_p(vw, _ways(allu))
    worst = {"b1_cents": ew, "p": rw["p"], "holds": bool(np.sign(ew) == np.sign(est) and rw["p"] < c10.GATE_P), "n_scored": len(miss)}
    u30 = [e for e in us if e.get("r30") is not None]
    e30 = b1_estimate(u30, pos, vals=np.array([e["r30"] for e in u30], float))[1] if u30 else math.nan
    rob_i = bool(math.isfinite(e30) and np.sign(e30) == np.sign(est) and abs(e30) >= abs(est) / 2)
    drops = {}
    for way, c in cl.items():
        keep = c10.c9.top_k_drop_mask(v - est, c)
        ku = [u for u, k in zip(us, keep, strict=True) if k]
        vk, ek, _ = b1_estimate(ku, pos)
        rk = c10.cluster_p(vk, _ways(ku))
        drops[way] = {"b1_cents": ek, "p": rk["p"], "holds": bool(rk["testable"] and rk["p"] < c10.GATE_P and ek >= B1_FLOOR_C)}
    rob_ii = all(d["holds"] for d in drops.values())
    ew_ = 0.0
    for L, wl in pos.items():
        r = [u for u in us if u["pair"] == L and u["arm"] == "real"]
        q = [u for u in us if u["pair"] == L and u["arm"] == "pseudo"]
        sr, sq = sum(u["vol10"] for u in r), sum(u["vol10"] for u in q)
        if sr > 0 and sq > 0:
            ew_ += wl * (sum(u["r_e"] * u["vol10"] for u in r) / sr - sum(u["r_e"] * u["vol10"] for u in q) / sq)
    rob_iii = bool(np.sign(ew_) == np.sign(est))
    rob_iv = _months_ok(us, lambda sub: b1_estimate(sub, pos)[1], est)
    rv = [u for u in us if u["arm"] == "real"]
    pv = [u for u in us if u["arm"] == "pseudo"]
    vr, vp = (float(np.mean([u["vol10"] for u in rv])) if rv else math.nan), (float(np.mean([u["vol10"] for u in pv])) if pv else math.nan)
    ratio = vr / vp if vp and math.isfinite(vp) and vp > 0 else math.nan
    robust = rob_i and rob_ii and rob_iii and rob_iv["holds"] and worst["holds"]
    placebo_ok = all(x["holds"] for x in pls.values())
    adv = bool(base["p"] < c10.GATE_P and est >= B1_FLOOR_C and placebo_ok and robust)
    return {**res, "floor_cents": B1_FLOOR_C, "placebo_label_swap": pls, "worst_case_missing_marks": worst,
            "robustness": {"i_m30_cents": e30, "i_holds": rob_i, "ii_top5": drops, "iii_vol_weighted_cents": ew_, "iii_holds": rob_iii, "iv_months": rob_iv},
            "cascade": {"real_vol10": vr, "pseudo_vol10": vp, "ratio": ratio, "real_tx10": float(np.mean([u["n_tx10"] for u in rv])) if rv else None,
                        "pseudo_tx10": float(np.mean([u["n_tx10"] for u in pv])) if pv else None},
            "advance": adv, "label": ("round-level reversal without a measurable cascade" if adv and not (math.isfinite(ratio) and ratio >= CASCADE_RATIO_MIN) else None),
            "verdict": "advance" if adv else ("not detected at MDE" if base["p"] >= c10.GATE_P else "fails floor / placebo / robustness"),
            "reported": {"r_by_level_dir": _r_by_level(us), "unweighted_pooled_cents": float(np.mean([u["r_e"] for u in rv]) - np.mean([u["r_e"] for u in pv])) if rv and pv else None}}


def _r_by_level(us: list[dict]) -> dict:
    out: dict[str, list[float]] = {}
    for u in us:
        out.setdefault(f"{u['level']}|{'down' if u['s'] == 1 else 'up'}", []).append(u["r_e"])
    return {k: {"n": len(v), "mean_cents": float(np.mean(v))} for k, v in sorted(out.items())}


def b2_values(eps: list[dict], *, arm: str = "real", field: str = "net_c", maker_key: str = "maker") -> tuple[list[dict], np.ndarray, int, int]:
    """(filled episodes with a value, their net per filled share in cents, eligible episodes, filled episodes without a mark)."""
    elig = [e for e in eps if e["arm"] == arm and e["follow"] and maker_key in e]
    filled = [e for e in elig if e[maker_key]["posted"] and e[maker_key]["filled"] > 0]
    us = [e for e in filled if e[maker_key].get(field) is not None]
    return us, np.array([e[maker_key][field] for e in us], float), len(elig), len(filled) - len(us)


def b2_stat(eps: list[dict]) -> dict:
    """B2 = mean net per filled share (cents) over filled real-level episodes after the exit cost; floor +1.0c; route gate = mean over eligible
    episodes of total net / 100 intended shares (not posted, unfilled = 0; filled without a mark excluded, counted) > 0. Binding: 2.0c half-spread net
    > 0, the 30-min mark, top-5 drops, filled-share weighting, months, worst case for missing marks, +120 s latency. Pseudo attribution: credit
    'stop-cascade route' iff B2 - B2_pseudo >= B2 / 2."""
    us, net, n_elig, n_nomark = b2_values(eps)
    res: dict[str, Any] = {"n_filled": len(us), "n_eligible": n_elig, "n_filled_without_mark": n_nomark,
                           "not_posted": sum(1 for e in eps if e["arm"] == "real" and e["follow"] and "maker" in e and not e["maker"]["posted"])}
    if len(us) < 2:
        return {**res, "testable": False, "p": 1.0, "advance": False, "verdict": "not testable"}
    cl = _ways(us)
    base = c10.cluster_p(net, cl)
    mean = float(net.mean())
    elig = [e for e in eps if e["arm"] == "real" and e["follow"] and "maker" in e]
    route_vals = [(e["maker"]["filled"] * e["maker"]["net_c"] / QUOTE_SHARES) if (e["maker"]["posted"] and e["maker"]["filled"] > 0) else 0.0
                  for e in elig if not (e["maker"]["posted"] and e["maker"]["filled"] > 0 and e["maker"]["net_c"] is None)]
    route = float(np.mean(route_vals)) if route_vals else math.nan
    res.update(b2_cents=mean, p=base["p"], testable=base["testable"], ways=base.get("ways"), route_gate={"mean_per_eligible_cents": route, "holds": bool(route > 0)})
    if not base["testable"]:
        return {**res, "advance": False, "verdict": "not testable"}
    _, hs20, _, _ = b2_values(eps, field="net_c_hs20")
    rob_cost = bool(len(hs20) and hs20.mean() > 0)
    u30, n30, _, _ = b2_values(eps, field="net_c_m30")
    rob_i = bool(len(n30) and np.sign(n30.mean()) == np.sign(mean) and abs(n30.mean()) >= abs(mean) / 2)
    drops = {}
    for way, c in cl.items():
        keep = c10.c9.top_k_drop_mask(net - mean, c)
        ku = [u for u, k in zip(us, keep, strict=True) if k]
        r = c10.cluster_p(net[keep], _ways(ku))
        drops[way] = {"mean_cents": r["mean"], "p": r["p"], "holds": bool(r["testable"] and r["p"] < c10.GATE_P and r["mean"] >= B2_FLOOR_C)}
    rob_ii = all(d["holds"] for d in drops.values())
    wts = np.array([u["maker"]["filled"] for u in us], float)
    wmean = float((net * wts).sum() / wts.sum())
    rob_iii = bool(np.sign(wmean) == np.sign(mean))
    rob_iv = _months_ok(us, lambda sub: float(np.mean([u["maker"]["net_c"] for u in sub])), mean)
    nomark = [e for e in elig if e["maker"]["posted"] and e["maker"]["filled"] > 0 and e["maker"]["net_c"] is None]
    if nomark:
        vv = np.concatenate([net, np.array([e["maker"]["worst_c"] for e in nomark], float)])
        rv = c10.cluster_p(vv, _ways(us + nomark))
        worst = {"mean_cents": rv["mean"], "p": rv["p"], "holds": bool(np.sign(rv["mean"]) == np.sign(mean) and rv["p"] < c10.GATE_P), "n_scored": len(nomark)}
    else:
        worst = {"n_scored": 0, "holds": True}
    ul, nl, _, _ = b2_values(eps, maker_key="maker_latency")
    rob_vi = bool(len(nl) and np.sign(nl.mean()) == np.sign(mean) and abs(nl.mean()) >= abs(mean) / 2)
    _, npse, _, _ = b2_values(eps, arm="pseudo")
    b2p = float(npse.mean()) if len(npse) else math.nan
    credit = bool(math.isfinite(b2p) and (mean - b2p) >= mean / 2)
    robust = rob_cost and rob_i and rob_ii and rob_iii and rob_iv["holds"] and worst["holds"] and rob_vi
    adv = bool(base["p"] < c10.GATE_P and mean >= B2_FLOOR_C and route > 0 and robust)
    gross = [e["maker"]["gross_c"] for e in us if e["maker"].get("gross_c") is not None]
    return {**res, "floor_cents": B2_FLOOR_C,
            "robustness": {"cost_hs20_cents": float(hs20.mean()) if len(hs20) else None, "cost_holds": rob_cost, "i_m30_cents": float(n30.mean()) if len(n30) else None,
                           "i_holds": rob_i, "ii_top5": drops, "iii_filled_weighted_cents": wmean, "iii_holds": rob_iii, "iv_months": rob_iv, "v_worst_case": worst,
                           "vi_latency_cents": float(nl.mean()) if len(nl) else None, "vi_holds": rob_vi},
            "pseudo_attribution": {"b2_pseudo_cents": b2p, "n_pseudo_filled": len(npse), "credit_stop_cascade_route": credit},
            "advance": adv, "label": None if (not adv or credit) else "a generic post-crossing maker, not a round-level route",
            "verdict": "advance" if adv else ("reversal exists but the maker still loses: no route" if not route > 0 else ("not detected at MDE" if base["p"] >= c10.GATE_P else "fails floor / robustness")),
            "reported": {"gross_cents": float(np.mean(gross)) if gross else None, "rebate_version_cents": float(np.mean([u["maker"]["net_c"] + u["maker"]["rebate_c"] for u in us])),
                         "fill_rate_posted": len([e for e in elig if e["maker"]["posted"] and e["maker"]["filled"] > 0]) / max(1, sum(1 for e in elig if e["maker"]["posted"])),
                         "per_level_cents": {str(L): float(np.mean([u["maker"]["net_c"] for u in us if u["level"] == L])) for L in LEVELS if any(u["level"] == L for u in us)}}}


def load_episodes(rdir: Path, frame_dir: Path, split: str, *, job: str, census: bool = False) -> tuple[list[dict], list[dict]]:
    """Episodes of every market of ``split`` (markets in seal-time DROPPED rows excluded). ``census`` -> counts view (``attach_counts``); else the
    marks view (``attach_marks``). Returns (episodes, market rows)."""
    from . import cb7_common as c7  # noqa: PLC0415

    _guard_split(split, job)
    rdir = Path(rdir)
    dp = rdir / DROPS_FILE
    dropped = {r["market_id"] for r in c7.read_csv_gz(dp) if str(r.get("block", "")).startswith("DROPPED")} if dp.exists() else set()
    sample = {r["market_id"]: r for r in read_sample(frame_dir)}
    markets = [r for r in c7.read_csv_gz(rdir / "markets.csv.gz")]
    out = []
    used = []
    for m in markets:
        if m["split"] != split or m["status"] != "ok" or m["market_id"] in dropped:
            continue
        if split == SCREEN and sample.get(m["market_id"], {}).get("topic") == "sports" and not SPORTS_IN_PRIMARY:
            continue
        tx = load_market_tx(rdir, split, m["market_id"], job=job)
        used.append(f"{split}/{m['market_id']}.tx.csv.gz")
        eps, _ = detect_episodes(tx, (float(m["span_start"]), float(m["span_end"])))
        rate = c10._num(sample.get(m["market_id"], {}).get("fee_rate"))
        for e in eps:
            v = attach_counts(tx, e) if census else attach_marks(tx, e, rate)
            v.update(market_id=m["market_id"], event_key=m["event_key"])
            out.append(v)
    if split == HOLDOUT:
        log_access(rdir, job, used)
    return out, markets


# =====================================================================================================================================
# Rules
# =====================================================================================================================================


def declared() -> dict:
    return {
        "family": "CB10-B (CH93), CREATIVE_BATCH_10.md CB10-B",
        "population": {"tx_window": list(TX_WINDOW), "end_window": list(END_WINDOW), "min_overlap_days": MIN_OVERLAP_DAYS, "min_volume": MIN_VOLUME,
                       "walk": "one-day endDate windows, closed=true, volume_num_min=10000; capped windows split down to one hour; a capped one-hour window is excluded and counted",
                       "whitelist": "cb10_common.whitelist_market; vol_ok, topic, fee_category and the exclusion class derived in memory (volumeNum, feeType, first event title, question, slug, resolutionSource); no outcome field",
                       "exclusions": {"weather": "cb7_common.is_weather", "crypto_updown": "history_backfill.CB1_UPDOWN_RE on question + event title + slug",
                                      "crypto_strike_ladder": f"series slug contains 'multi-strikes' or (topic crypto and question matches {CRYPTO_STRIKE_RE!r})",
                                      "pyth": f"resolution host {PYTH_HOST}"},
                       "keys": "id, event, neg-risk and series keys (the usual rule)", "max_per_event": MAX_PER_EVENT, "n_sample": N_SAMPLE,
                       "sports": {"in_primary": SPORTS_IN_PRIMARY, "max_share": SPORTS_MAX_SHARE}, "categories": B_CATEGORIES or "every category not excluded",
                       "seeds": {"sample": SEED_SAMPLE, "split": SEED_SPLIT}, "split": "Gamma event 50/50 by sha256(seed|event key), before any print read"},
        "prints": {"data_api": {"limit": DATA_LIMIT, "pages": DATA_PAGES, "takerOnly": TAKER_ONLY}, "aggregation": "cb10_dlad.aggregate_transactions (YES terms; hash discarded)",
                   "kept": "transactions with time in the window", "span": "[max(W0, oldest reachable print if truncated), W1)",
                   "covered": "not truncated, or the oldest reachable print at or before max(W0, the market's start)", "holdout_dir": HOLDOUT},
        "episodes": {"levels": list(LEVELS), "pseudo_offset": PSEUDO_OFFSET, "pairs": {str(k): list(v) for k, v in pairs().items()},
                     "crossing": "down: previous >= L and p_j < L; up: previous <= L and p_j > L; equality is not a crossing",
                     "memory_s": MEMORY_S, "min_prior_tx": MIN_PRIOR_TX, "spacing_s": SPACING_S, "spacing": "no earlier eligible episode of the same arm (any level) at t_j - 2 h or later",
                     "mutual_exclusion_s": MUTEX_S, "follow_s": FOLLOW_S, "mark": {"horizon_s": MARK_S, "min_s": MARK_MIN_S}, "mark30": {"horizon_s": MARK30_S, "min_s": MARK30_MIN_S},
                     "reversal": "R_e = s (M2h - VWAP10), cents; s = +1 down-break, -1 up-break"},
        "b1": {"statistic": "sum_L w_L (mean R_e real L - mean R_e pseudo L+-0.03 pooled); weights frozen in the census, n_L / sum n over all pairs, pairs < 30/30 -> 0, no renormalisation",
               "floor_cents": B1_FLOOR_C, "ways": ["event", "day"], "placebo": "real/pseudo label swap, one coin per event and per UTC day, 200 draws each, both must hold",
               "worst_case": {"real_c": WORST_REAL_C, "pseudo_c": WORST_PSEUDO_C}, "cascade_ratio_min": CASCADE_RATIO_MIN},
        "b2": {"post_s": POST_S, "latency_post_s": LATENCY_POST_S, "quote_end_s": QUOTE_END_S, "shares": QUOTE_SHARES, "offset": QUOTE_OFFSET,
               "not_posted": "the last transaction at or before the post time is at or through the quote", "fills": "transactions strictly through the quote, min(remaining, size)",
               "exit_cost": f"r_B M2h (1 - M2h) + {HALF_SPREAD}; r_B = feeSchedule.rate at frame time, {FEE_RATE_DEFAULT} if absent", "half_spread_robust": HALF_SPREAD_ROBUST,
               "floor_cents": B2_FLOOR_C, "route_gate": "mean over eligible episodes of filled x net / 100 (not posted, unfilled = 0; filled without a mark excluded, counted) > 0",
               "worst_case": f"filled without a mark: gross {WORST_B2_GROSS_C}c minus the exit cost at M = 0.5", "rebate": f"{REBATE_SHARE} r p (1 - p) per filled share at the recorded rate (reported)",
               "pseudo_attribution": "credit iff B2 - B2_pseudo >= B2 / 2"},
        "robustness": {"months": {"min_episodes": MONTH_MIN_EPISODES, "share": MONTH_SHARE}},
        "census": {"gate_GB": GB, "gate_GB2_filled": GB2_FILLED, "audit_pass": AUDIT_PASS, "forbidden": list(CENSUS_FORBIDDEN)},
        "seal": {"name": SEAL_NAME, "copy": SEAL_COPY_NAME, "drops": DROPS_FILE, "access_log": ACCESS_LOG},
    }


def rule_funcs() -> tuple:
    from . import cb8_flow as fl  # noqa: PLC0415

    return (declared, pairs, level_table, brk_row, overlap_days, frame_reason, _walk_window, assemble, brk_frame, read_sample, market_span, brk_prints, brk_seal,
            verify_holdout_seal, _guard_split, holdout_counts, load_market_tx, detect_episodes, _after, follow_through, _mark_avail, maker_fills, attach_counts, exit_cost,
            attach_marks, census_b, _ways, b1_estimate, _months_ok, b1_stat, _r_by_level, b2_values, b2_stat, load_episodes, fl.per_event_cap, fl.flow_sample,
            fl.event_split, fl.event_key)
