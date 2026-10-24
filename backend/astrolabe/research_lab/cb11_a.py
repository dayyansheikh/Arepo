# ruff: noqa: E501
"""CB11-A: attention without news (docs/research_lab/CREATIVE_BATCH_11.md CB11-A, 1.2-1.4, 2.1-2.7, CB11-F q0227 / q0229 / q0239 / q0234 / q0237; round-1 revision).

Frame (Gamma walk, no volume filter, ``vol_ok`` stored as a boolean), the frozen entity rule (``derive_query`` first entity, stop list, Wikipedia summary
``type == standard``), the seeded vol_ok sample and the non-vol_ok robustness stratum, the event-hash SCREEN / HOLDOUT split before any pageview or print read, the
200-pair audit file; pageviews (daily, 2026-01-01 on, absent days stay absent) and aggregated transactions; market-day units with the 48-hour publication rule,
A1 (quiet minus spike continuation, three cluster ways), A2 (taker follow in quiet big moves) and the round-1 robustness checks. EXPLORATORY; no edge claim.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import numpy as np

from . import cb8_common as cm
from . import cb11_common as c11
from . import cb11_pa as pa
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow
DAY, HOUR = pa.DAY, pa.HOUR

END_WINDOW = ("2026-04-20", "2026-10-01")
LIFE_WINDOW = ("2026-04-10", "2026-09-28")
MIN_OVERLAP_D = 10.0
X_WINDOW = ("2026-04-10", "2026-09-24")  # inclusive
TX_WINDOW = ("2026-04-01", "2026-10-01")
PV_START, PV_END = "2026-01-01", "2026-09-30"
BLOCK_ORIGIN = "2026-04-13"
LISTED_BEFORE_D = 8
PV_LAG_DAYS = 3  # origin t = X + 3 d 00:00Z: day X usable 48 h after it ends
PV_BASE_MIN = 50.0
PV_HISTORY_D = 30
SPIKE, QUIET = 2.0, 1.25
SPIKE_ROBUST = (1.5, 3.0)
BIG, BIG_ROBUST = 0.03, 0.05
END_AHEAD_S = 72 * HOUR
TARGET_S = 48 * HOUR
TARGET_ROBUST_S = 24 * HOUR
HALF_SPREAD, HALF_SPREAD_ROBUST = 0.015, 0.020
FEE_R_MIN = 0.05
A1_FLOOR, A2_FLOOR = 0.01, 0.01
ATTR_MIN = 0.005
NOTIONAL_MIN = 2000.0
N_SAMPLE, N_NOVOL = 3000, 1000
MAX_PER_EVENT = 3
N_AUDIT = 200
AUDIT_PASS = 0.80
GA = {"quiet": 1000, "spike": 200, "events": 150, "days": 60, "entity_share": 0.5}
COVER_MIN = 0.90
AVAIL_MIN = 0.60
WIKI_MAX_REQ = 3000
WIKI_STUCK_RESUMES = 3  # c2: consecutive Wikipedia-error resumes without a new cached summary before the terminal "not testable (source)"
MDE_SD = 0.08
MDE_DEFF = 1.3
SEED_SAMPLE = "arepo-cb11-attn-sample"
SEED_NOVOL = "arepo-cb11-attn-novol"
SEED_SPLIT = "arepo-cb11-attn-split"
SEED_AUDIT = "arepo-cb11-attn-audit"
DATA_LIMIT, DATA_PAGES, TAKER_ONLY = 10000, 2, "true"
FRAME_OUTPUT_CAP_GB, DATA_OUTPUT_CAP_GB = 0.01, 0.12
FRAME_STATUS, DATA_STATUS = "attn_frame_complete", "attn_data_complete"
RUN = c11.H11_ATTN
HOLD_DIR = "holdout"
SEAL_COPY_NAME = "cb11_attn_holdout_SEAL.json"
AUDIT_LABELS_NAME = "cb11_attn_audit_labels.csv"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
EXCLUDED_TOPICS = ("sports", "crypto")
EXCLUDED_CLASSES = None  # any non-empty exclusion_class (weather, crypto up/down, strike ladder, pyth) is excluded
MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul",
               "aug", "sep", "sept", "oct", "nov", "dec")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
GENERIC_CAP = ("Will", "Who", "What", "When", "Which", "How", "Does", "Is", "Are", "Can", "Do", "Did", "Yes", "No", "The", "A", "An", "By", "In", "On", "Before", "After", "Over", "Under",
               "Bitcoin Up", "Up", "Down", "Above", "Below")  # the existing external_news._GENERIC_CAP, frozen here
GENERIC_NOUNS = ("ipo", "invasion", "election", "elections", "ceasefire", "recession", "inflation", "shutdown", "primary", "debate", "referendum", "treaty", "summit", "war", "peace")
STOP_LIST = tuple(sorted({s.lower() for s in (*MONTH_NAMES, *WEEKDAYS, *GENERIC_CAP, *GENERIC_NOUNS)}))

FRAME_COLUMNS = [*pa.PA_COLUMNS, "vol_ok", "topic", "entity", "question", "stratum", "split", "event_key", "w_inv", "title", "description"]
CLOSE_COLUMNS = ["market_id", "close_epoch"]  # closedTime is outcome-adjacent: kept out of the frame file, merged in only by read_frame for the open-at-t condition and the close mark
ENTITY_COLUMNS = ["entity", "status", "type", "canonical", "description"]
PV_COLUMNS = ["title", "day", "views"]
MARKET_COLUMNS = ["market_id", "split", "status", "oldest_ts", "truncated", "n_prints", "n_nohash", "n_tx", "covered"]
AUDIT_COLUMNS = ["market_id", "question", "canonical_title", "description"]
CENSUS_FORBIDDEN = ("P_t", "P_t48", "P_t24", "C", "continuation", "net", "pnl", "mark")


def _ep(d: str) -> float:
    return pa.ep(d)


def day_int(epoch: float) -> int:
    return int(epoch // DAY)


def day_epoch(d: int) -> float:
    return d * DAY


# =====================================================================================================================================
# Entity rule
# =====================================================================================================================================


def entity_candidate(question: str, event_title: str) -> str:
    """``derive_query(question, event_title)['entities'][0]`` unless it is in the frozen stop list (case-insensitive); '' when there is none."""
    from . import external_news as en  # noqa: PLC0415

    ents = en.derive_query(question, event_title or None).get("entities") or []
    if not ents:
        return ""
    e = str(ents[0]).strip()
    return "" if e.lower() in STOP_LIST else e


def wiki_title(entity: str) -> str:
    from . import external_news as en  # noqa: PLC0415

    return en.wiki_article_title(entity)


def wiki_summary(limw: hb.Limiter, entity: str) -> dict:
    """Wikipedia REST summary (redirects followed). Returns status / type / canonical title / short description. A non-200 is 'unavailable' (404) and an
    exhausted retry raises (``RuntimeError``)."""
    st, doc = limw.get(WIKI_SUMMARY + quote(wiki_title(entity), safe="_"), {})
    if st != 200 or not isinstance(doc, dict):
        return {"entity": entity, "status": st, "type": "", "canonical": "", "description": ""}
    canon = str((doc.get("titles") or {}).get("canonical") or doc.get("title") or "").replace(" ", "_")
    return {"entity": entity, "status": 200, "type": str(doc.get("type") or ""), "canonical": canon, "description": str(doc.get("description") or "")[:200]}


# =====================================================================================================================================
# Frame (q0227)
# =====================================================================================================================================


def overlap_days(start: float, end: float) -> float:
    if not (math.isfinite(start) and math.isfinite(end)):
        return math.nan
    return max(0.0, min(end, _ep(LIFE_WINDOW[1])) - max(start, _ep(LIFE_WINDOW[0]))) / DAY


def attn_record(m: dict) -> dict | None:
    """The stored candidate of one raw market, or None if a static filter drops it (not binary, end outside the window, life overlap below 10 d, sports / crypto /
    weather / Pyth / strike ladder / Up-Down, no entity or a stop-listed one). ``vol_ok`` (volumeNum >= 10,000) is the only volume-derived value kept."""
    from . import cb10_brk as brk  # noqa: PLC0415

    r = pa.pa_row(m)
    if r is None:
        return None
    end, start = r["end_epoch"], r["start_epoch"]
    if not (math.isfinite(end) and _ep(END_WINDOW[0]) <= end < _ep(END_WINDOW[1])):
        return None
    ov = overlap_days(start, end)
    if not (math.isfinite(ov) and ov >= MIN_OVERLAP_D):
        return None
    b = brk.brk_row(m)
    if b is None or b.get("exclusion_class") or b.get("topic") in EXCLUDED_TOPICS:
        return None
    aux = pa.pa_aux(m)
    ent = entity_candidate(aux["question"], aux["event_title"])
    if not ent:
        return None
    return {**{k: pa.blank(v) for k, v in r.items()}, "vol_ok": int(b["vol_ok"]), "topic": b["topic"], "entity": ent, "question": aux["question"][:140],
            "close_epoch": pa.blank(pa.pa_guarded(m)["closed_epoch"])}


def walk_day(lim: hb.Limiter, a: int, b: int, acc: dict) -> None:
    """One end-date window (no volume filter); a capped window is split down to one hour, a capped one-hour window is excluded and counted.
    Bounded memory (q0227b): each uncapped window's raw markets are reduced to their ``attn_record`` rows at once (same markets, same order) and only the rows
    and the raw count are kept in ``acc``; a whole day of raw Gamma objects (~10-13k at ~10 KB each) is never held (q0227 MemoryError under the 2 x mem_mb cap)."""
    from . import cb4_data as c4  # noqa: PLC0415

    f = "%Y-%m-%dT%H:%M:%SZ"
    p = {"closed": "true", "order": "id", "ascending": "true", "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f)}
    batch, capped, failed = c4._paged_strict(lim, p, hb.GAMMA_OFFSET_CAP)
    if failed:
        acc["failed_windows"] += 1
        return
    if capped and b - a > 3600:
        del batch  # a capped window's rows are never used: release them before recursing (no raw batch held per recursion level)
        acc["splits"] += 1
        mid = a + (b - a) // 2
        walk_day(lim, a, mid, acc)
        walk_day(lim, mid, b, acc)
        return
    acc["windows"] += 1
    if capped:
        acc["excluded_capped_window"] += 1
        return
    raw = [m for m in batch if isinstance(m, dict)]
    del batch
    acc["n_raw"] += len(raw)
    acc["rows"].extend(x for x in (attn_record(m) for m in raw) if x is not None)


def accept_sequential(cands: list[dict], seed: str, n: int, event_count: Counter, resolve: Callable[[str], dict | None], stats: dict) -> tuple[list[dict], str | None]:
    """Walk ``cands`` in seeded rank order, apply the per-event cap (<= 3 accepted per event, shared across strata) and the Wikipedia rule (``resolve`` returns the
    cached / fetched summary, or None to stop), accept until ``n``. Equivalent to filtering, capping and sampling by seeded rank, with lazy summaries."""
    out: list[dict] = []
    for r in sorted(cands, key=lambda x: c11.rank(seed, str(x["market_id"]))):
        if len(out) >= n:
            break
        ek = pa.event_key(r)
        if event_count[ek] >= MAX_PER_EVENT:
            continue
        s = resolve(r["entity"])
        if s is None:
            return out, "wikipedia_paused"
        stats["processed"] += 1
        if s["status"] == 200 and s["type"] == "standard" and s["canonical"]:
            stats["passed"] += 1
            event_count[ek] += 1
            out.append({**r, "title": s["canonical"], "description": s["description"]})
    return out, None


def attn_frame(hist_root: Path, transport, wiki_transport, *, rules_sha: str, smoke_path: Path, exclusion_keys_path: Path, now: float, rps: float = 2.0, wiki_rps: float = 1.0,
               disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time,
               snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, free_fn=None,
               days: list[str] | None = None, n_sample: int = N_SAMPLE, n_novol: int = N_NOVOL) -> dict:
    """q0227, one resumable chunk: the daily Gamma walk, key drops, the vol_ok / non-vol_ok strata, the sequential entity rule with Wikipedia summaries (cached,
    <= 3,000 requests), the event-hash split and the audit file, all before any pageview or print request."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_flow as fl  # noqa: PLC0415
    from . import cb10_common as c10  # noqa: PLC0415
    from . import cb11_smoke as sm  # noqa: PLC0415

    hist_root = Path(hist_root)
    rdir = c11.require_output_root(hist_root / RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    if c11.manifest_complete(rdir, (FRAME_STATUS, DATA_STATUS)) or pa.state_flag(rdir, "frame_complete"):
        done = json.loads((rdir / "manifest.json").read_text())
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    bad = sm.smoke_failures(smoke_path, sm.FAMILY_NEEDS["A"])
    if bad:
        return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c11.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c11.UNVERIFIED:
        return c11.write_stall(rdir, c11.STALL_DISJOINTNESS, "q0221: > 2% of exclusion ids without metadata (design 1.3)")
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(hist_root, RUN, transport, allowed_run_id=RUN, kind="cb11_attn_frame", label="CB11-A frame", params={"exclusion_keys_sha256": ksha, "evidence_role": c11.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    limw = hb.Limiter(wiki_transport, rps=min(wiki_rps, 1.0), sleep=sleep, live_check=None)
    try:
        pp, pf = rdir / "frame_partial.jsonl.gz", rdir / "frame_fail.jsonl"
        have = {rec["day"] for rec in c6.iter_partial(pp)}
        fails = c7.walk_failed_days(pf)
        dlist = days if days is not None else c10.days_between(*[END_WINDOW[0], END_WINDOW[1]])
        for d in dlist:
            if d in have or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return pa.in_progress(fr, why)
            a = int(cm.ep(d + "T00:00:00Z"))
            acc = {"rows": [], "n_raw": 0, "splits": 0, "windows": 0, "failed_windows": 0, "excluded_capped_window": 0}
            walk_day(fr.lim, a, a + int(DAY), acc)
            if acc["failed_windows"]:
                with pf.open("a") as fh:
                    fh.write(json.dumps({"day": d}) + "\n")
                continue
            c7.append_member(fr, pp, {"day": d, "rows": acc["rows"], "n_raw": acc["n_raw"], "excluded_capped_window": acc["excluded_capped_window"], "splits": acc["splits"]})
            del acc
        fails = c7.walk_failed_days(pf)
        # one streaming pass over the per-day records (never a list of all of them): recorded days, capped-window count, first row per market id
        rec_days: set[str] = set()
        n_capped = 0
        uniq: dict[str, dict] = {}
        for rec in c6.iter_partial(pp):
            rec_days.add(rec["day"])
            n_capped += int(rec["excluded_capped_window"])
            for r in rec["rows"]:
                uniq.setdefault(str(r["market_id"]), r)
        if not all(d in rec_days or fails.get(d, 0) >= cm.MAX_ITEM_ATTEMPTS for d in dlist):
            return pa.in_progress(fr, "frame_paused")
        kept, drops = c10.drop_by_keys(list(uniq.values()), ids, keys)
        # entity cache (resumable) and the sequential acceptance
        ep_path = rdir / "entities_partial.jsonl"
        cache = pa.read_jsonl_by(ep_path, "entity")

        pause: dict = {"why": None}

        def resolve(ent: str) -> dict | None:
            k = ent.lower()
            if k in cache:
                return cache[k]
            if len(cache) >= WIKI_MAX_REQ:
                pause["why"] = "budget"
                return None
            if fr.stop_reason(should_stop):
                pause["why"] = "stop"
                return None
            try:
                s = wiki_summary(limw, ent)
            except (cm.ApiError, RuntimeError) as exc:
                pause["why"], pause["detail"] = "error", f"{type(exc).__name__}: {exc}"[:120]
                return None
            rec = {**s, "entity": k}
            pa.append_jsonl(ep_path, rec)
            cache[k] = rec
            return rec

        vol = [r for r in kept if int(r["vol_ok"]) == 1]
        nov = [r for r in kept if int(r["vol_ok"]) == 0]
        ev_count: Counter = Counter()
        st_v = {"processed": 0, "passed": 0}
        st_n = {"processed": 0, "passed": 0}
        def paused(why: str) -> dict:
            """c2: a Wikipedia pause is transient only while the budget holds and the error is not stuck; a used-up request cap, or WIKI_STUCK_RESUMES resumes that all
            ended on a Wikipedia error with no new summary cached in between, is the terminal counted 'not testable (source)' (design 2.8 stop rules)."""
            cause = pause.get("why")
            if cause == "budget":
                return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"Wikipedia request budget ({WIKI_MAX_REQ}) used up before the sample filled: {len(cache)} summaries cached")
            if cause == "error":
                pp_ = rdir / "wiki_pauses.jsonl"
                pa.append_jsonl(pp_, {"cache": len(cache), "detail": pause.get("detail")})
                recs_ = [json.loads(x) for x in pp_.read_text().splitlines() if x.strip()]
                if len(recs_) >= WIKI_STUCK_RESUMES and len({r_["cache"] for r_ in recs_[-WIKI_STUCK_RESUMES:]}) == 1:
                    return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"Wikipedia errors on {WIKI_STUCK_RESUMES} consecutive resumes without progress ({pause.get('detail')})")
            return pa.in_progress(fr, why)

        s_vol, why = accept_sequential(vol, SEED_SAMPLE, n_sample, ev_count, resolve, st_v)
        if why:
            return paused(why)
        s_nov, why = accept_sequential(nov, SEED_NOVOL, n_novol, ev_count, resolve, st_n)
        if why:
            return paused(why)
        strata = {}
        for name, pool, sample, stt in (("vol", vol, s_vol, st_v), ("novol", nov, s_nov, st_n)):
            share = stt["passed"] / stt["processed"] if stt["processed"] else math.nan
            w_inv = len(pool) * share / len(sample) if sample and math.isfinite(share) else math.nan
            strata[name] = {"pool": len(pool), "processed": stt["processed"], "passed": stt["passed"], "entity_pass_share": share, "sampled": len(sample), "w_inv": w_inv}
        rows_out = []
        for name, sample in (("vol", s_vol), ("novol", s_nov)):
            for r in sample:
                rows_out.append({**r, "stratum": name, "split": fl.event_split(r, SEED_SPLIT), "event_key": pa.event_key(r), "w_inv": strata[name]["w_inv"]})
        rows_out.sort(key=lambda r: str(r["market_id"]))
        for sp in ("screen", "holdout"):
            prefix = "" if sp == "screen" else HOLD_DIR + "/"
            sfx = "" if sp == "screen" else "_hold"
            sub = [r for r in rows_out if r["split"] == sp]
            fr.budget.write_gz_csv(rdir / f"{prefix}frame{sfx}.csv.gz", FRAME_COLUMNS, ([pa.blank(r.get(c, "")) for c in FRAME_COLUMNS] for r in sub))
            fr.budget.write_gz_csv(rdir / f"{prefix}closes{sfx}.csv.gz", CLOSE_COLUMNS, ([pa.blank(r.get(c, "")) for c in CLOSE_COLUMNS] for r in sub))
            fr.record_file(rdir / f"{prefix}closes{sfx}.csv.gz")
            ents = {r["entity"].lower(): cache[r["entity"].lower()] for r in sub}
            fr.budget.write_gz_csv(rdir / f"{prefix}entities{sfx}.csv.gz", ENTITY_COLUMNS, ([e["entity"], e["status"], e["type"], e["canonical"], e["description"]] for e in ents.values()))
            fr.record_file(rdir / f"{prefix}frame{sfx}.csv.gz")
            fr.record_file(rdir / f"{prefix}entities{sfx}.csv.gz")
        audit = sorted([r for r in rows_out if r["split"] == "screen" and r["stratum"] == "vol"], key=lambda r: c11.rank(SEED_AUDIT, str(r["market_id"])))[:N_AUDIT]
        ap = rdir / "audit_sample.csv"
        import csv as _csv  # noqa: PLC0415

        fr.budget.charge(1)
        with ap.open("w", newline="") as fh:
            w = _csv.writer(fh)
            w.writerow(AUDIT_COLUMNS)
            for r in sorted(audit, key=lambda r: str(r["market_id"])):
                w.writerow([r["market_id"], r["question"], r["title"], r["description"]])
        fr.record_file(ap)
        rep = {"drops": drops, "n_frame_rows": len(uniq), "strata": strata, "walk": {"days": len(dlist), "failed_days": sorted(d for d, k in fails.items() if k >= cm.MAX_ITEM_ATTEMPTS),
                                                                                          "excluded_capped_window": n_capped, "wiki_requests": len(cache)},
               "n_sample": len(rows_out), "n_audit": len(audit), "counts_by_split": dict(Counter(f"{r['stratum']}|{r['split']}" for r in rows_out)),
               "events": {sp: len({r["event_key"] for r in rows_out if r["split"] == sp}) for sp in ("screen", "holdout")}}
        fr.budget.write(rdir / "split.json", json.dumps({"seeds": {"sample": SEED_SAMPLE, "novol": SEED_NOVOL, "split": SEED_SPLIT, "audit": SEED_AUDIT}, "origin_lag_days": sm.smoke_origin_lag_days(smoke_path), "report": rep,
                                                         "events": {r["event_key"]: r["split"] for r in rows_out}}, indent=1, sort_keys=True, default=float).encode())
        fr.record_file(rdir / "split.json")
        pp.unlink(missing_ok=True)
        pf.unlink(missing_ok=True)
        ep_path.unlink(missing_ok=True)
        fr.counts.update(n_sample=len(rows_out), n_screen=sum(1 for r in rows_out if r["split"] == "screen"), n_holdout=sum(1 for r in rows_out if r["split"] == "holdout"))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    fr.extra_state["frame_complete"] = True
    m = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m["status"] = FRAME_STATUS
    return m


# =====================================================================================================================================
# Data (q0229): pageviews and transactions
# =====================================================================================================================================


def read_audit_labels(path: Path, audit_ids: set[str], *, is_committed: Callable[[Path], bool] | None = None) -> dict:
    """The committed audit labels (columns ``market_id,label``; label in 1 / subject / yes = the article is the market's subject, else not). Must cover exactly the
    audit sample. Raises ``NotNow`` when the file is absent (the audit is a repo step), ``Refused`` when it is uncommitted or inconsistent."""
    import csv as _csv  # noqa: PLC0415

    p = Path(path)
    if not p.exists():
        raise NotNow(f"audit labels {p} not committed yet (science-reviewer blind labels); pending")
    if is_committed is not None and not is_committed(p):
        raise Refused(f"audit labels {p} are not committed (or differ from HEAD)")
    with p.open(newline="") as fh:
        rows = list(_csv.DictReader(fh))
    lab = {str(r["market_id"]): str(r["label"]).strip().lower() in ("1", "subject", "yes", "true") for r in rows}
    if set(lab) != set(audit_ids):
        raise Refused("audit labels do not cover exactly the audit sample ids")
    prec = sum(lab.values()) / len(lab) if lab else 0.0
    return {"n": len(lab), "precision": prec, "pass": bool(len(lab) and prec >= AUDIT_PASS), "min": AUDIT_PASS}


def audit_ids_of(rdir: Path) -> set[str]:
    import csv as _csv  # noqa: PLC0415

    with (Path(rdir) / "audit_sample.csv").open(newline="") as fh:
        return {str(r["market_id"]) for r in _csv.DictReader(fh)}


def parse_pageviews(doc) -> list[tuple[str, int]]:
    items = doc.get("items") if isinstance(doc, dict) else None
    out = []
    for i in items or []:
        try:
            out.append((str(i["timestamp"])[:8], int(i["views"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def pageview_url(title: str) -> str:
    return f"{WIKI_PAGEVIEWS}{quote(title, safe='_')}/daily/{PV_START.replace('-', '')}00/{PV_END.replace('-', '')}00"


def read_frame_for_fetch(rdir: Path) -> list[dict]:
    rdir = Path(rdir)
    out = []
    for sp, p in (("screen", rdir / "frame.csv.gz"), ("holdout", rdir / HOLD_DIR / "frame_hold.csv.gz")):
        out += [{**dict(r), "split": sp} for r in c11.read_csv_gz(p)]
    return out


def attn_data(hist_root: Path, transport, wiki_transport, *, rules_sha: str, now: float, labels_path: Path, is_committed: Callable[[Path], bool] | None = None, smoke_path: Path | None = None,
              rps: float = 2.0, wiki_rps: float = 1.0, disk_cap: int = int(DATA_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None,
              should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
              data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, free_fn=None, pages: int = DATA_PAGES) -> dict:
    """q0229, one resumable chunk: daily pageviews per canonical title (missing days stay absent; 404 = no series), then newest-first Data API prints (<= 2 pages) of
    every sampled market aggregated to transactions in ``[2026-04-01, 2026-10-01)`` with the covered span. HOLDOUT files go to ``holdout/``. Refuses (pending, with the
    idle heartbeat) until the committed audit labels exist."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb10_brk as brk  # noqa: PLC0415
    from . import cb10_dlad as dl  # noqa: PLC0415
    from . import cb11_smoke as sm  # noqa: PLC0415

    hist_root = Path(hist_root)
    rdir = c11.require_output_root(hist_root / RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    if smoke_path is not None:
        bad = sm.smoke_failures(smoke_path, sm.FAMILY_NEEDS["A"])
        if bad:
            return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    if not (c11.manifest_complete(rdir, (FRAME_STATUS, DATA_STATUS)) or pa.state_flag(rdir, "frame_complete")):
        raise NotNow("q0229 waits for q0227 (attn_frame) to finish")
    done = c11.manifest_complete(rdir, (DATA_STATUS,))
    if done:
        return {"stopped": None, "status": DATA_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    try:
        read_audit_labels(labels_path, audit_ids_of(rdir), is_committed=is_committed)
    except NotNow as exc:
        return cm.idle(rdir, str(exc), now, kind="audit_labels")
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(hist_root, RUN, transport, allowed_run_id=RUN, kind="cb11_attn_data", label="CB11-A data", params={"evidence_role": c11.EVIDENCE_ROLE_HIST, "pages": pages},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    limw = hb.Limiter(wiki_transport, rps=min(wiki_rps, 1.0), sleep=sleep, live_check=None)
    frame = read_frame_for_fetch(rdir)
    try:
        # pageviews, once per canonical title
        pvp = rdir / "pageviews_partial.jsonl"
        pv = pa.read_jsonl_by(pvp, "title")
        for title in sorted({r["title"] for r in frame}):
            if title in pv:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return pa.in_progress(fr, why)
            try:
                s, doc = limw.get(pageview_url(title), {})
            except RuntimeError as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[title] = fails.get(title, 0) + 1
                if fails[title] < cm.MAX_ITEM_ATTEMPTS:
                    return pa.in_progress(fr, f"pageviews_failed {title}: {exc}"[:200])
                rec = {"title": title, "status": "unavailable (source)", "days": []}
            else:
                rec = {"title": title, "status": int(s), "days": parse_pageviews(doc) if s == 200 else []}
            fr.budget.charge(len(json.dumps(rec)))
            pa.append_jsonl(pvp, rec)
            pv[title] = rec
        for sp in ("screen", "holdout"):
            prefix = Path(sp)
            titles = sorted({r["title"] for r in frame if r["split"] == sp})
            fr.budget.write_gz_csv(rdir / prefix / "pageviews.csv.gz", PV_COLUMNS, ([t, d, v] for t in titles for d, v in pv[t]["days"]))
            fr.record_file(rdir / prefix / "pageviews.csv.gz")
        # prints
        mp = rdir / "markets_partial.jsonl"
        have = pa.read_jsonl_by(mp, "market_id")
        for r in frame:
            mid = str(r["market_id"])
            if mid in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return pa.in_progress(fr, why)
            try:
                prints, info = dl.fetch_market_prints(fr.lim, r["condition_id"], limit=DATA_LIMIT, pages=pages)
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[mid] = fails.get(mid, 0) + 1
                if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                    return pa.in_progress(fr, f"prints_failed {mid}: {exc}"[:200])
                rec = {"market_id": mid, "split": r["split"], "status": "fetch_failed", "oldest_ts": "", "truncated": 1, "n_prints": 0, "n_nohash": 0, "n_tx": 0, "covered": 0}
            else:
                w0, w1 = _ep(TX_WINDOW[0]), _ep(TX_WINDOW[1])
                tx = [x for x in dl.aggregate_transactions(prints, 0) if w0 <= x[0] < w1]
                del prints
                _, _, cov = brk.market_span({"start_epoch": r["start_epoch"]}, info["oldest_ts"], info["truncated"])
                pa.write_tx_file(fr, rdir / r["split"] / f"{mid}.tx.csv.gz", tx)
                rec = {"market_id": mid, "split": r["split"], "status": "ok", "oldest_ts": pa.blank(info["oldest_ts"]), "truncated": int(info["truncated"]), "n_prints": info["n_prints"],
                       "n_nohash": info["n_nohash"], "n_tx": len(tx), "covered": int(cov)}
            pa.append_jsonl(mp, rec)
            have[mid] = rec
        recs = sorted(have.values(), key=lambda x: x["market_id"])
        fr.budget.write_gz_csv(rdir / "markets.csv.gz", MARKET_COLUMNS, ([x[c] for c in MARKET_COLUMNS] for x in recs))
        fr.record_file(rdir / "markets.csv.gz")
        mp.unlink(missing_ok=True)
        pvp.unlink(missing_ok=True)
        fr.counts.update(markets=len(recs), titles=len(pv), pageview_absent=sum(1 for t in pv.values() if not t["days"]), truncated=sum(int(x["truncated"]) for x in recs))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    _ = c6, c7
    fr.extra_state["frame_complete"] = True
    m = fr.manifest(None, {"complete": True, "status": DATA_STATUS})
    m["status"] = DATA_STATUS
    return m


# =====================================================================================================================================
# Loaders (guards)
# =====================================================================================================================================


def read_frame(rdir: Path, split: str, *, job: str) -> list[dict]:
    rdir = Path(rdir)
    if split == "holdout":
        if job != "rep-A":
            raise Refused("A HOLDOUT is sealed: only rep-A loads it (after verify_holdout_seal)")
        path, cpath = rdir / HOLD_DIR / "frame_hold.csv.gz", rdir / HOLD_DIR / "closes_hold.csv.gz"
        dropped = c11.dropped_market_ids(rdir)  # d2: seal-time drops are never analysed
    elif split == "screen":
        path, cpath = rdir / "frame.csv.gz", rdir / "closes.csv.gz"
        dropped = set()
    else:
        raise Refused(f"unknown split {split!r}")
    if not cpath.exists():
        raise Refused(f"{cpath} is missing; the open-at-t condition and the close mark cannot be evaluated (no silent fallback)")
    closes = {str(r["market_id"]): r["close_epoch"] for r in c11.read_csv_gz(cpath)}
    return [{**dict(r), "close_epoch": closes.get(str(r["market_id"]), "")} for r in c11.read_csv_gz(path) if str(r["market_id"]) not in dropped]


def load_pageviews(rdir: Path, split: str, *, job: str) -> dict[str, dict[int, int]]:
    if split == "holdout" and job != "rep-A":
        raise Refused("A HOLDOUT pageviews are sealed: only rep-A loads them")
    p = Path(rdir) / (HOLD_DIR if split == "holdout" else "screen") / "pageviews.csv.gz"
    out: dict[str, dict[int, int]] = {}
    for r in c11.read_csv_gz(p):
        d = datetime.strptime(r["day"], "%Y%m%d").replace(tzinfo=UTC)
        out.setdefault(r["title"], {})[day_int(d.timestamp())] = int(r["views"])
    return out


def tx_loader(rdir: Path, split: str, *, job: str) -> Callable[[str], tuple | None]:
    if split == "holdout" and job != "rep-A":
        raise Refused("A HOLDOUT transactions are sealed: only rep-A loads them")
    sub = Path(rdir) / (HOLD_DIR if split == "holdout" else "screen")

    def load(mid: str):
        p = sub / f"{mid}.tx.csv.gz"
        return pa.read_tx_file(p) if p.exists() else None

    return load


def log_access(rdir: Path, job: str, files: list[str]) -> None:
    with (Path(rdir) / c11.ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "files": files}) + "\n")


def load_markets(rdir: Path) -> dict[str, dict]:
    p = Path(rdir) / "markets.csv.gz"
    return {str(r["market_id"]): dict(r) for r in c11.read_csv_gz(p)} if p.exists() else {}


# =====================================================================================================================================
# Pageview rules and units
# =====================================================================================================================================


def pageview_usable(x_day: int, t: float, lag_days: int = PV_LAG_DAYS) -> bool:
    """Day X (UTC day number) is usable at ``t >= X + 1 d + 48 h`` (``lag_days`` 3), or ``X + 1 d + 72 h`` if the smoke's ``wiki_lag`` failed (``lag_days`` 4; design 2.2)."""
    return bool(t >= day_epoch(x_day) + DAY + (lag_days - 1) * DAY)


def rdir_lag_days(rdir: Path) -> int:
    """The origin lag recorded by q0227 from the smoke (3, or 4 after a ``wiki_lag`` fail); 3 for a split file without the key."""
    return int(json.loads((Path(rdir) / "split.json").read_text()).get("origin_lag_days", PV_LAG_DAYS))


def pv_attention(series: dict[int, int], x_day: int, first_nz: int | None) -> dict | None:
    """Attention ratio of day ``x_day`` under the round-1 rules: all of ``X-8 .. X`` present, baseline ``median(views(X-8 .. X-1)) >= 50``, the series' first non-zero
    day at least 30 days before X. Returns {A, base} or None (unavailable (pageviews), never filled)."""
    days = range(x_day - 8, x_day + 1)
    if any(d not in series for d in days):
        return None
    base = float(np.median([series[d] for d in range(x_day - 8, x_day)]))
    if base < PV_BASE_MIN or first_nz is None or first_nz > x_day - PV_HISTORY_D:
        return None
    return {"A": series[x_day] / base, "base": base}


def lag_attention(series: dict[int, int], x_day: int, first_nz: int | None) -> float:
    """Lagged attention ``views(X-7) / median(views(X-15 .. X-8))`` under the same rules applied to days ``X-15 .. X-7`` (history measured from X-7); NaN if unavailable."""
    days = range(x_day - 15, x_day - 6)
    if any(d not in series for d in days):
        return math.nan
    base = float(np.median([series[d] for d in range(x_day - 15, x_day - 7)]))
    if base < PV_BASE_MIN or first_nz is None or first_nz > (x_day - 7) - PV_HISTORY_D:
        return math.nan
    return series[x_day - 7] / base


def cell_of(a: float, spike: float = SPIKE, quiet: float = QUIET) -> str:
    return "spike" if a >= spike else ("quiet" if a <= quiet else "middle")


def block_of(t: float) -> int:
    return int(math.floor((t - _ep(BLOCK_ORIGIN)) / (3 * DAY)))


def candidate_units(frame: list[dict], pv: dict[str, dict[int, int]], txl: Callable[[str], tuple | None], lag_days: int = PV_LAG_DAYS) -> tuple[list[dict], dict]:
    """Market-day candidates WITHOUT any forward value: pageview rules, listing, P_end(X), P_end(X-1), the move M, the attention cell, the origin, the end / open
    conditions. The targets are attached only by :func:`attach_targets` (never called by the census)."""
    units, c = [], Counter()
    for r in frame:
        series = pv.get(r["title"])
        mid = str(r["market_id"])
        tx = txl(mid)
        start, end = pa.fnum(r["start_epoch"]), pa.fnum(r["end_epoch"])
        close = pa.fnum(r["close_epoch"])
        first_nz = min((d for d, v in (series or {}).items() if v > 0), default=None)
        for x in range(day_int(_ep(X_WINDOW[0])), day_int(_ep(X_WINDOW[1])) + 1):
            xs = day_epoch(x)
            t = xs + lag_days * DAY
            if not (math.isfinite(start) and start <= xs - LISTED_BEFORE_D * DAY):
                c["not_listed"] += 1
                continue
            att = pv_attention(series, x, first_nz) if series else None
            if att is None:
                c["pageviews_unavailable"] += 1
                continue
            if not (math.isfinite(end) and end >= t + END_AHEAD_S and (not math.isfinite(close) or close > t)):
                c["end_or_open_condition"] += 1
                continue
            p1, p0 = pa.vwap_before(tx, xs + DAY), pa.vwap_before(tx, xs)
            cell = cell_of(att["A"])
            if not (math.isfinite(p1) and math.isfinite(p0)):
                c[f"p_end_unavailable|{cell}"] += 1
                continue
            m = p1 - p0
            u = {"market_id": mid, "event": r["event_key"], "stratum": r["stratum"], "w_inv": pa.fnum(r["w_inv"]), "x_day": x, "x_date": pa.day_of(xs), "month": pa.month_of(xs), "t": t,
                 "A": att["A"], "cell": cell, "M": m, "big": abs(m) >= BIG, "A_lag": lag_attention(series, x, first_nz), "fee_rate": pa.fnum(r["fee_rate"]), "close": close, "end": end,
                 "block": block_of(t), "tx": None}
            units.append(u)
    return units, dict(c)


def attach_targets(units: list[dict], txl: Callable[[str], tuple | None]) -> list[dict]:
    """Forward values: P(t), P(t + 48 h), P(t + 24 h), the early-close flag and the pre-X traded-notional lower bound. Called only by the screen / rep jobs."""
    cache: dict[str, tuple | None] = {}
    out = []
    for u in units:
        mid = u["market_id"]
        if mid not in cache:
            cache.clear()
            cache[mid] = txl(mid)
        tx = cache[mid]
        t, close = u["t"], u["close"]
        pt = pa.vwap_before(tx, t)
        marks = {}
        for name, h in (("p48", TARGET_S), ("p24", TARGET_ROBUST_S)):
            s = t + h
            if math.isfinite(close) and close < s:
                marks[name] = _last_in(tx, t, close)
            else:
                marks[name] = pa.vwap_before(tx, s)
        early = bool(math.isfinite(close) and close < t + TARGET_S)
        xs = day_epoch(u["x_day"])
        notional = 0.0
        if tx is not None and len(tx[0]):
            lo, hi = np.searchsorted(tx[0], xs - 7 * DAY, side="left"), np.searchsorted(tx[0], xs, side="left")
            p = tx[1][lo:hi]
            notional = float((tx[2][lo:hi] * np.minimum(p, 1 - p)).sum())
        s_ = 1.0 if u["M"] > 0 else -1.0
        out.append({**u, "p_t": pt, "p48": marks["p48"], "p24": marks["p24"], "early": early, "notional": notional, "dir": s_,
                    "C": s_ * (marks["p48"] - pt) if math.isfinite(marks["p48"]) and math.isfinite(pt) else math.nan,
                    "C24": s_ * (marks["p24"] - pt) if math.isfinite(marks["p24"]) and math.isfinite(pt) else math.nan})
    return out


def _last_in(tx, lo: float, hi: float) -> float:
    if tx is None or len(tx[0]) == 0:
        return math.nan
    i = int(np.searchsorted(tx[0], hi, side="left")) - 1
    return float(tx[1][i]) if i >= 0 and tx[0][i] >= lo else math.nan


# =====================================================================================================================================
# A1, A2
# =====================================================================================================================================


def ways_of(us: list[dict]) -> dict[str, np.ndarray]:
    return {"event": np.array([u["event"] for u in us]), "day": np.array([u["x_date"] for u in us]), "block": np.array([str(u["block"]) for u in us])}


def delta_core(C: np.ndarray, cell: np.ndarray, ways: dict[str, np.ndarray], *, alpha: float | None = None) -> dict:
    """Δ = mean C(quiet) - mean C(spike), its pseudo-values and the one-sided p as the max over the three cluster ways."""
    C, cell = np.asarray(C, float), np.asarray(cell)
    nq, ns = int((cell == "quiet").sum()), int((cell == "spike").sum())
    if nq < 2 or ns < 2:
        return {"n": len(C), "n_quiet": nq, "n_spike": ns, "delta": math.nan, "p": 1.0, "testable": False, "v": np.full(len(C), math.nan)}
    arm = np.where(cell == "quiet", "real", "pseudo")
    v, est, _ = c11.c10.contrast_pseudo(C, list(arm), [1] * len(C), {1: 1.0})
    cp = c11.cluster_p(v, ways, alpha=alpha)
    return {"n": len(C), "n_quiet": nq, "n_spike": ns, "delta": float(est), "p": float(cp["p"]), "testable": bool(cp["testable"]), "ways": cp.get("ways"), "v": v}


def sel(us: list[dict], *, big: float = BIG, spike: float = SPIKE, mark_key: str = "C", strata=("vol",), drop_early: bool = False) -> list[dict]:
    out = []
    for u in us:
        if u["stratum"] not in strata or abs(u["M"]) < big or (drop_early and u.get("early")):
            continue
        cell = cell_of(u["A"], spike)
        if cell == "middle" or not math.isfinite(u.get(mark_key, math.nan)):
            continue
        out.append({**u, "cell": cell, "val": u[mark_key]})
    return out


def label_swap_placebo(us: list[dict], *, n_draws: int = c11.PLACEBO_DRAWS, seed: int = c11.PLACEBO_SEEDS["A1_labelswap"]) -> dict:
    """Binding placebo: permute the spike / quiet labels of the big-move units within each day X; a draw advances iff its p < 0.01 (floors off)."""
    rng = np.random.default_rng(seed)
    days_all = np.array([u["x_date"] for u in us])
    cells_all = np.array([u["cell"] for u in us])
    both = {d for d in set(days_all.tolist()) if {"quiet", "spike"} <= set(cells_all[days_all == d].tolist())}
    us = [u for u in us if u["x_date"] in both]  # a day with one arm only carries no within-day contrast; swapping its labels is a no-op that would bias the null
    C = np.array([u["val"] for u in us], float)
    cell = np.array([u["cell"] for u in us])
    ways = ways_of(us)
    days = np.array([u["x_date"] for u in us])
    groups = [np.where(days == d)[0] for d in sorted(set(days.tolist()))]
    for g in groups:
        C[g] = C[g] - C[g].mean()  # net of the day-X mean: arm shares differ by day, which would otherwise bias the pooled null contrast away from zero
    ps = []
    for _ in range(n_draws):
        c2 = cell.copy()
        for g in groups:
            c2[g] = cell[g][rng.permutation(len(g))]
        r = delta_core(C, c2, ways, alpha=c11.GATE_P)
        ps.append(r["p"] if r["testable"] else 1.0)
    out = c11.placebo_advance_rate(ps)
    out["note"] = "A1 spike / quiet label swap within day X (days with both arms, C net of its day mean); advance iff p < 0.01 (floors off)"
    out["n_units"] = len(us)
    return out


def _delta_only(us: list[dict]) -> float:
    q = [u["val"] for u in us if u["cell"] == "quiet"]
    s = [u["val"] for u in us if u["cell"] == "spike"]
    return float(np.mean(q) - np.mean(s)) if q and s else math.nan


def a1_stat(units: list[dict], *, n_draws: int = c11.PLACEBO_DRAWS, alpha: float = c11.GATE_P, placebo: bool = True, inclusive: bool = False) -> dict:
    """A1 on units that carry targets (``attach_targets``)."""
    us = sel(units)
    C = np.array([u["val"] for u in us], float)
    cell = np.array([u["cell"] for u in us])
    core = delta_core(C, cell, ways_of(us)) if us else {"testable": False, "p": 1.0, "delta": math.nan, "n": 0, "n_quiet": 0, "n_spike": 0}
    out: dict = {k: core[k] for k in ("n", "n_quiet", "n_spike", "delta", "p", "testable")} | {"ways": core.get("ways"), "floor": A1_FLOOR, "label": "mechanism contrast, modelled (L1)", "effect": core["delta"]}
    out["core_ok"] = bool(core["testable"] and c11.p_ok(core["p"], alpha, inclusive) and core["delta"] >= A1_FLOOR)
    if not core["testable"]:
        return {**out, "advance": False, "p": 1.0, "verdict": "not testable (units or clusters)"}
    out["placebo"] = label_swap_placebo(us, n_draws=n_draws) if placebo else {"n_draws": 0, "holds": True, "advance_rate": None, "note": "skipped"}
    # attribution (label only): lagged attention
    lag = [u for u in us if math.isfinite(u["A_lag"])]
    lc = np.array([cell_of(u["A_lag"]) for u in lag])
    keep = lc != "middle"
    lag2 = [{**u, "cell": c} for u, c, k in zip(lag, lc, keep, strict=True) if k]
    d_lag = _delta_only(lag2)
    out["attribution_lag"] = {"n_units_with_lag": len(lag2), "n_dropped": len(us) - len(lag2), "delta_lag": d_lag, "gap": out["delta"] - d_lag if math.isfinite(d_lag) else math.nan,
                              "credit_same_day_attention": bool(math.isfinite(d_lag) and out["delta"] - d_lag >= ATTR_MIN), "label_if_not": "an entity-type trait (spiky entities), not day attention"}
    rob: dict = {}
    for thr in SPIKE_ROBUST:
        d = _delta_only(sel(units, spike=thr))
        rob[f"spike_{thr}"] = {"delta": d, "ok": bool(math.isfinite(d) and d > 0)}
    d = _delta_only(sel(units, big=BIG_ROBUST))
    rob["big_0_05"] = {"delta": d, "ok": bool(math.isfinite(d) and d > 0)}
    d = _delta_only(sel(units, mark_key="C24"))
    rob["mark_24h"] = {"delta": d, "ok": bool(math.isfinite(d) and d > 0 and d >= 0.5 * out["delta"])}
    d = _delta_only(sel(units, drop_early=True))
    rob["early_excluded"] = {"delta": d, "ok": bool(math.isfinite(d) and d > 0)}
    top = {}
    for way, cl in ways_of(us).items():
        keepm = c11.c9.top_k_drop_mask(np.nan_to_num(core["v"]), cl, c11.TOP_DROP)
        sub = [u for u, k in zip(us, keepm, strict=True) if k]
        r = delta_core(np.array([u["val"] for u in sub], float), np.array([u["cell"] for u in sub]), ways_of(sub))
        top[way] = {"n": r["n"], "delta": r["delta"], "p": r["p"], "ok": bool(r["testable"] and c11.p_ok(r["p"], alpha, inclusive) and r["delta"] >= A1_FLOOR)}
    rob["without_top5"] = top
    rob["months"] = pa.months_ok(np.array([u["month"] for u in us]), lambda mo: (sum(1 for u in us if u["month"] == mo), _delta_only([u for u in us if u["month"] == mo])))
    both = sel(units, strata=("vol", "novol"))
    cv = [u for u in both if u["notional"] >= NOTIONAL_MIN and math.isfinite(u["w_inv"])]
    q = [u for u in cv if u["cell"] == "quiet"]
    s = [u for u in cv if u["cell"] == "spike"]
    if q and s:
        dw = float(np.average([u["val"] for u in q], weights=[u["w_inv"] for u in q]) - np.average([u["val"] for u in s], weights=[u["w_inv"] for u in s]))
    else:
        dw = math.nan
    rob["causal_volume"] = {"n_units": len(cv), "delta_weighted": dw, "note": "traded notional lower bound (shares x min(p, 1 - p)) >= $2,000 in [X-7 d, X); inverse sampling fraction weights",
                            "ok": bool(math.isfinite(dw) and dw > 0 and dw >= 0.5 * out["delta"])}
    rob["ok"] = bool(all(rob[k]["ok"] for k in ("big_0_05", "mark_24h", "early_excluded", "causal_volume") if k in rob) and all(rob[f"spike_{t}"]["ok"] for t in SPIKE_ROBUST)
                     and all(v["ok"] for v in top.values()) and rob["months"]["ok"])
    out["robustness"] = rob
    out["advance"] = bool(out["core_ok"] and out["placebo"].get("holds") and rob["ok"])
    out["verdict"] = "advance" if out["advance"] else ("floor / p not met" if not out["core_ok"] else "placebo or robustness failed")
    return out


def fee_a(rate: float) -> float:
    return max(rate if math.isfinite(rate) else 0.0, FEE_R_MIN)


def a2_net(u: dict, *, half_spread: float, fade: bool = False) -> float:
    """Net per share after both legs' costs, token terms: follow the move (buy the token in the move's direction at P(t) + hs, sell at P(t + 48 h) - hs) or, for the
    reported fade, take the opposite token."""
    s = u["dir"] * (-1.0 if fade else 1.0)
    pt, px = u["p_t"], u["p48"]
    e = (pt if s > 0 else 1 - pt) + half_spread
    x = (px if s > 0 else 1 - px) - half_spread
    e, x = min(max(e, 0.0), 1.0), min(max(x, 0.0), 1.0)
    r = fee_a(u["fee_rate"])
    return x - e - r * e * (1 - e) - r * x * (1 - x)


def a2_stat(units: list[dict], *, alpha: float = c11.GATE_P, inclusive: bool = False) -> dict:
    us = [u for u in sel(units) if u["cell"] == "quiet" and math.isfinite(u["p48"])]
    v = np.array([a2_net(u, half_spread=HALF_SPREAD) for u in us], float)
    ways = ways_of(us)
    cp = c11.cluster_p(v, ways) if len(us) >= 2 else {"testable": False, "p": 1.0}
    out: dict = {"n": len(us), "net_mean": float(v.mean()) if len(v) else math.nan, "p": float(cp["p"]), "testable": bool(cp["testable"]), "floor": A2_FLOOR, "effect": float(v.mean()) if len(v) else math.nan,
                 "label": "modelled-cost economic check (L1); declared half-spread 1.5c per side"}
    spikes = [u for u in sel(units) if u["cell"] == "spike" and math.isfinite(u["p48"])]
    out["reported_fade_spike"] = {"n": len(spikes), "net_mean": float(np.mean([a2_net(u, half_spread=HALF_SPREAD, fade=True) for u in spikes])) if spikes else math.nan}
    if not cp["testable"]:
        return {**out, "advance": False, "p": 1.0, "verdict": "not testable (units or clusters)"}
    out["core_ok"] = bool(c11.p_ok(out["p"], alpha, inclusive) and out["net_mean"] >= A2_FLOOR)
    v2 = np.array([a2_net(u, half_spread=HALF_SPREAD_ROBUST) for u in us], float)
    rob: dict = {"half_spread_2c": {"net_mean": float(v2.mean()), "ok": bool(v2.mean() > 0)}}
    top = {}
    for way, cl in ways.items():
        keep = c11.c9.top_k_drop_mask(v, cl, c11.TOP_DROP)
        r = c11.cluster_p(v[keep], {k: w[keep] for k, w in ways.items()})
        top[way] = {"n": int(keep.sum()), "net_mean": float(v[keep].mean()), "p": r["p"], "ok": bool(r["testable"] and c11.p_ok(r["p"], alpha, inclusive) and v[keep].mean() >= A2_FLOOR)}
    rob["without_top5"] = top
    months = np.array([u["month"] for u in us])
    rob["months"] = pa.months_ok(months, lambda mo: (int((months == mo).sum()), float(v[months == mo].mean()) if (months == mo).any() else math.nan))
    rob["ok"] = bool(rob["half_spread_2c"]["ok"] and all(x["ok"] for x in top.values()) and rob["months"]["ok"])
    out["robustness"] = rob
    out["advance"] = bool(out["core_ok"] and rob["ok"])
    out["verdict"] = "advance" if out["advance"] else "floors or robustness not met"
    return out


# =====================================================================================================================================
# Census (q0239, A part): counts only
# =====================================================================================================================================


def mde(n_quiet: int, n_spike: int | None = None) -> float:
    base = pa.MDE_Z * MDE_SD * MDE_DEFF
    if n_quiet <= 0:
        return math.nan
    if n_spike is None:
        return float(base * math.sqrt(1.0 / n_quiet))
    return float(base * math.sqrt(1.0 / n_spike + 1.0 / n_quiet)) if n_spike > 0 else math.nan


def _holdout_counts(rdir: Path) -> dict:
    """HOLDOUT market count for the census. Sealed run: seal-time drops excluded (n_dropped reported). Pre-seal: an upper bound, labelled as such."""
    p = Path(rdir) / HOLD_DIR / "frame_hold.csv.gz"
    if not p.exists():
        return {"n_markets": 0, "basis": "no holdout file"}
    ids = [str(r["market_id"]) for r in c11.read_csv_gz(p)]
    if not (Path(rdir) / c11.SEAL_NAME).exists():
        return {"n_markets": len(ids), "basis": "UPPER BOUND: before the seal, seal-time drops not yet applied"}
    dropped = c11.dropped_market_ids(rdir)
    return {"n_markets": sum(1 for i in ids if i not in dropped), "n_dropped": sum(1 for i in ids if i in dropped), "basis": "sealed run, seal-time drops excluded"}


def census_a(rdir: Path, labels_path: Path, *, is_committed: Callable[[Path], bool] | None = None) -> dict:
    """Counts only (design 2.7 A). Builds the candidate units WITHOUT forward values (no P(t), P(t + 48 h), continuation or net exists in this path), applies GA0 from
    the committed audit labels, GA and the coverage audit. HOLDOUT is counted from its frame file only."""
    rdir = Path(rdir)
    frame = read_frame(rdir, "screen", job="census")
    split = json.loads((rdir / "split.json").read_text())
    rep = split["report"]
    pv = load_pageviews(rdir, "screen", job="census")
    txl = tx_loader(rdir, "screen", job="census")
    mk = load_markets(rdir)
    units, cnt = candidate_units([r for r in frame if r["stratum"] == "vol"], pv, txl, rdir_lag_days(rdir))
    big = [u for u in units if u["big"]]
    cells = {c: {"big": sum(1 for u in units if u["cell"] == c and u["big"]), "small": sum(1 for u in units if u["cell"] == c and not u["big"])} for c in ("spike", "middle", "quiet")}
    nq = [u for u in big if u["cell"] == "quiet"]
    ns = [u for u in big if u["cell"] == "spike"]
    ev = {u["event"] for u in big if u["cell"] in ("quiet", "spike")}
    days = {u["x_date"] for u in big if u["cell"] in ("quiet", "spike")}
    vol_markets = [r for r in frame if r["stratum"] == "vol"]
    qualifying = {u["market_id"] for u in units}
    sv = rep["strata"]["vol"]
    pass_share = sv["entity_pass_share"] if sv["entity_pass_share"] == sv["entity_pass_share"] else 0.0
    q_share = len(qualifying) / len(vol_markets) if vol_markets else 0.0
    entity_share = pass_share * q_share
    doc: dict = {"version": "cb11-a-census-v1", "counts_only": True, "frame": {"n_screen": len(frame), "n_vol_screen": len(vol_markets), "report": rep}, "units_by_cell": cells,
                 "n_big_quiet": len(nq), "n_big_spike": len(ns), "events": len(ev), "days": len(days), "unavailable_counts": cnt, "markets_with_unit": len(qualifying),
                 "holdout": _holdout_counts(rdir)}
    try:
        aud = read_audit_labels(labels_path, audit_ids_of(rdir), is_committed=is_committed)
    except (NotNow, Refused) as exc:
        aud = {"pass": False, "error": str(exc)[:150], "precision": None}
    doc["GA0"] = aud
    ga = {"quiet": len(nq), "spike": len(ns), "events": len(ev), "days": len(days), "entity_share": entity_share, "need": GA,
          "pass": bool(len(nq) >= GA["quiet"] and len(ns) >= GA["spike"] and len(ev) >= GA["events"] and len(days) >= GA["days"] and entity_share >= GA["entity_share"])}
    doc["GA"] = ga
    scr = [r for r in frame]
    cov = sum(1 for r in scr if str(mk.get(str(r["market_id"]), {}).get("covered")) in ("1", "True"))
    audit = {"n_screen": len(scr), "covered": cov, "share": cov / len(scr) if scr else 0.0, "min": COVER_MIN, "pass": bool(scr and cov / len(scr) >= COVER_MIN),
             "failures_by_arm": {k.split("|")[1]: v for k, v in cnt.items() if k.startswith("p_end_unavailable|")}, "pageview_unavailable": cnt.get("pageviews_unavailable", 0)}
    doc["coverage_audit"] = audit
    doc["mde"] = {"A1": mde(len(nq), len(ns)), "A2": mde(len(nq)), "note": "SD 8c, design effect 1.3 (declared); never used to change a floor"}
    label = None
    if not aud.get("pass"):
        label = "not testable (entity map)"
    elif not ga["pass"]:
        label = "not testable (GA: units, events, days or entity share)"
    elif not audit["pass"]:
        label = "not testable (source limited)"
    doc["label_A1"] = doc["label_A2"] = label
    doc["a_runs"] = label is None
    return doc


# =====================================================================================================================================
# Screen / rep
# =====================================================================================================================================


def _units(rdir: Path, split: str, job: str) -> tuple[list[dict], dict]:
    frame = read_frame(rdir, split, job=job)
    pv = load_pageviews(rdir, split, job=job)
    txl = tx_loader(rdir, split, job=job)
    cand, cnt = candidate_units(frame, pv, txl, rdir_lag_days(rdir))
    elig = [u for u in cand if u["big"]]
    full = attach_targets(elig, txl)
    return full, {"candidate_units": len(cand), "big_units": len(elig), "unavailable_counts": cnt}


def _availability(units: list[dict]) -> dict:
    e = [u for u in units if cell_of(u["A"]) != "middle" and u["stratum"] == "vol"]
    a = [u for u in e if math.isfinite(u["C"])]
    return {"eligible": len(e), "available": len(a), "share": len(a) / len(e) if e else 0.0, "min": AVAIL_MIN, "ok": bool(e and len(a) / len(e) >= AVAIL_MIN),
            "by_arm": {c: {"eligible": sum(1 for u in e if cell_of(u["A"]) == c), "available": sum(1 for u in a if cell_of(u["A"]) == c)} for c in ("spike", "quiet")}}


def screen_a(rdir: Path, census: dict, *, n_draws: int = c11.PLACEBO_DRAWS) -> dict:
    ca = census.get("A") or {}
    lab = ca.get("label_A1")
    if lab:
        return {t: {"testable": False, "p": 1.0, "advance": False, "verdict": lab} for t in ("A1", "A2")}
    units, info = _units(Path(rdir), "screen", "screen-A")
    av = _availability(units)
    if not av["ok"]:
        v = "not testable (availability)"
        return {t: {"testable": False, "p": 1.0, "advance": False, "verdict": v, "availability": av} for t in ("A1", "A2")}
    a1 = a1_stat(units, n_draws=n_draws)
    a2 = a2_stat(units)
    a1["availability"] = a2["availability"] = av
    a1["unit_info"] = info
    return {"A1": a1, "A2": a2}


def rep_a(rdir: Path, census: dict, advanced: tuple[str, ...], k: int, *, n_draws: int = c11.PLACEBO_DRAWS, seals_dir: Path | None = None, committed_seals: bool = True) -> dict:
    rdir = Path(rdir)
    c11.verify_holdout_seal(rdir, SEAL_COPY_NAME, seals_dir, require_committed=committed_seals)
    log_access(rdir, "rep-A", ["holdout/frame_hold.csv.gz", "holdout/pageviews.csv.gz", "holdout/<market>.tx.csv.gz"])
    thr = c11.STAGE2_ALPHA / k
    out: dict = {"label": "sealed same-calendar holdout replication (L2)", "stage2_alpha_over_k": thr, "k": k}
    units, info = _units(rdir, "holdout", "rep-A")
    av = _availability(units)
    for t in ("A1", "A2"):
        if t not in advanced:
            continue
        if not av["ok"]:
            out[f"{t}_rep"] = {"testable": False, "p": 1.0, "advance": False, "verdict": "not testable (availability)", "availability": av, "stage2_pass_alpha_over_k": False}
            continue
        r = a1_stat(units, n_draws=n_draws, alpha=thr, inclusive=True) if t == "A1" else a2_stat(units, alpha=thr, inclusive=True)
        r["stage2_pass_alpha_over_k"] = bool(r.get("testable") and r.get("p", 1.0) <= thr and r.get("advance"))
        out[f"{t}_rep"] = r
    out["unit_info"] = info
    return out


def seal_rows(rdir: Path) -> list[dict]:
    p = Path(rdir) / HOLD_DIR / "frame_hold.csv.gz"
    return [{"market_id": r["market_id"], "event_ids": r["event_ids"], "neg_risk_market_id": r["neg_risk_market_id"], "series_ids": r["series_ids"]} for r in c11.read_csv_gz(p)] if p.exists() else []


def declared() -> dict:
    return {"windows": {"end": list(END_WINDOW), "life": list(LIFE_WINDOW), "x": list(X_WINDOW), "tx": list(TX_WINDOW), "pageviews": [PV_START, PV_END], "block_origin": BLOCK_ORIGIN},
            "min_overlap_d": MIN_OVERLAP_D, "listed_before_d": LISTED_BEFORE_D, "origin_lag_days": PV_LAG_DAYS, "origin_lag_days_if_wiki_lag_failed": 4, "pageview_rules": {"baseline_min": PV_BASE_MIN, "history_d": PV_HISTORY_D, "days_present": "X-8..X"},
            "thresholds": {"spike": SPIKE, "quiet": QUIET, "spike_robust": list(SPIKE_ROBUST), "big": BIG, "big_robust": BIG_ROBUST}, "target_s": [TARGET_S, TARGET_ROBUST_S],
            "end_ahead_s": END_AHEAD_S, "costs": {"half_spread": HALF_SPREAD, "half_spread_robust": HALF_SPREAD_ROBUST, "fee_r_min": FEE_R_MIN},
            "floors": {"a1": A1_FLOOR, "a2": A2_FLOOR, "attr": ATTR_MIN, "notional_min": NOTIONAL_MIN}, "sample": {"n": N_SAMPLE, "novol": N_NOVOL, "per_event": MAX_PER_EVENT, "audit": N_AUDIT,
                                                                                                                   "seeds": [SEED_SAMPLE, SEED_NOVOL, SEED_SPLIT, SEED_AUDIT]},
            "gates": {"GA": GA, "GA0_precision": AUDIT_PASS, "coverage_min": COVER_MIN, "availability_min": AVAIL_MIN, "wiki_max_requests": WIKI_MAX_REQ, "wiki_stuck_resumes": WIKI_STUCK_RESUMES},
            "mde": {"sd": MDE_SD, "deff": MDE_DEFF}, "stop_list": list(STOP_LIST), "excluded_topics": list(EXCLUDED_TOPICS), "prints": {"limit": DATA_LIMIT, "pages": DATA_PAGES, "taker_only": TAKER_ONLY},
            "placebo": {"seed": c11.PLACEBO_SEEDS["A1_labelswap"], "draws": c11.PLACEBO_DRAWS}, "census_forbidden": list(CENSUS_FORBIDDEN), "columns": {"frame": FRAME_COLUMNS, "closes": CLOSE_COLUMNS}}


def rule_funcs() -> tuple:
    return (day_int, entity_candidate, wiki_title, wiki_summary, overlap_days, attn_record, walk_day, accept_sequential, attn_frame, read_audit_labels, audit_ids_of, parse_pageviews,
            pageview_url, attn_data, read_frame, load_pageviews, tx_loader, pageview_usable, rdir_lag_days, pv_attention, lag_attention, cell_of, block_of, candidate_units, attach_targets, _last_in,
            ways_of, delta_core, sel, label_swap_placebo, _delta_only, a1_stat, fee_a, a2_net, a2_stat, mde, census_a, _units, _availability, screen_a, rep_a, seal_rows, declared)
