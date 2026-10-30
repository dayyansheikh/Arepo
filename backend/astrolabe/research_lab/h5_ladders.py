"""CB1-B R1 data: the ``h5_cb1_ladders`` fetch (``docs/research_lab/CREATIVE_BATCH_1.md`` CB1-F).

Steps (resumable, request-paced, disk-capped, wall-clock budgeted, yields to the collector):

1. Gamma ``/events`` walk by start date (``if_h2.discover``: 7-day windows, split while capped,
   tag 102127 excluded). Saved once as ``events.jsonl.gz``.
2. ``ladder-grouper-v1`` (``if_h2.group_ladders``, unchanged).
3. Exclusion guards: drop a ladder whose event id or any rung id is in the IF-H2 universe, or any
   of whose rungs is in the sample of an excluded history run (h1/h2/h3). Counted in the manifest.
4. Probe (once): 20 seeded random rungs; fewer than 80 percent returning price points ends the run
   as ``probe_failed`` (B1/B2 not testable) with nothing more fetched.
5. Per rung: hourly prices over the rung's life (14-day windows), trades (<= 10,000, truncation
   flags) and the rung's Gamma outcome metadata (already inside ``ladders.jsonl.gz``; no job reads
   it before the CB1 freeze commit). Wallet addresses are stored as keyed hashes only.

Nothing here reads a CB1 result; all parameters are fixed by the document.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from . import history_backfill as hb
from . import if_h2

LADDERS_VERSION = "h5-cb1-ladders-v1"
PROBE_N = 20
PROBE_MIN_SHARE = 0.80
COMPLETE_TOKEN = "ladders_fetch_complete"
PROBE_FAILED_TOKEN = "probe_failed"


def _ids_from_ladders(ladders: list[dict]) -> tuple[set[str], set[str]]:
    ev, rg = set(), set()
    for lad in ladders:
        ev.add(str(lad.get("event_id")))
        rg.update(str(r.get("market_id")) for r in lad.get("rungs", []))
    return ev, rg


def apply_guards(ladders: list[dict], ifh2_event_ids: set[str], ifh2_rung_ids: set[str],
                 sample_ids: set[str]) -> tuple[list[dict], dict]:
    """Drop any ladder sharing an event id or rung id with IF-H2, or a rung with an h1/h2/h3
    sample. Metadata only."""
    kept, rep = [], {"ladders_in": len(ladders), "dropped_ifh2_event": 0, "dropped_ifh2_rung": 0,
                     "dropped_history_sample": 0}
    for lad in ladders:
        rungs = {str(r["market_id"]) for r in lad["rungs"]}
        if str(lad["event_id"]) in ifh2_event_ids:
            rep["dropped_ifh2_event"] += 1
        elif rungs & ifh2_rung_ids:
            rep["dropped_ifh2_rung"] += 1
        elif rungs & sample_ids:
            rep["dropped_history_sample"] += 1
        else:
            kept.append(lad)
    rep["ladders_kept"] = len(kept)
    rep["rungs_kept"] = sum(len(lad["rungs"]) for lad in kept)
    return kept, rep


def _utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ladders_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, start: datetime, end: datetime,
    exclude_runs: list[str], ifh2_ladder_file: Path | None, rps: float = 4.0,
    disk_cap: int = int(0.15 * 1024**3), budget_min: float | None = None,
    max_trades: int = 10000, seed: str = "arepo-h5-cb1-ladders", key: bytes | None = None,
    now: float | None = None, sleep: Callable[[float], None] = time.sleep,
    live_check: Callable[[], bool] | None = hb.live_pass_or_lock,
    should_stop: Callable[[], bool] | None = None,
    wall_clock: Callable[[], float] = time.time, t_seal_epoch: float = hb.T_SEAL_EPOCH,
) -> dict:
    root = Path(root)
    if wall_clock() >= t_seal_epoch:  # h5 must not grow after T_seal
        return {"stopped": "t_seal_passed", "counts": {}, "requests": 0}
    rdir = root / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    now = time.time() if now is None else now
    now = hb.pin_request_clock(rdir, now)  # one T_fetch across resumed chunks
    t_start = time.time()
    rps = min(rps, 4.0)
    budget_s = None if not budget_min else budget_min * 60.0
    budget = hb.DiskBudget(rdir, disk_cap)
    lim = hb.Limiter(transport, rps=rps, sleep=sleep, live_check=live_check)
    key = key if key is not None else hb.load_or_create_key()
    mpath = rdir / "manifest.json"
    prior = json.loads(mpath.read_text()) if mpath.exists() else {}
    state: dict = {"counts": {"rungs_done": 0, "rungs_failed": 0, "price_points": 0, "trades": 0,
                              "trades_truncated_rungs": 0}}

    def out_of_budget() -> bool:
        return budget_s is not None and time.time() - t_start >= budget_s

    def manifest(stopped: str | None, extra: dict | None = None) -> dict:
        m = {
            "provenance": hb.PROVENANCE, "evidence_role": hb.EVIDENCE_ROLE,
            "version": LADDERS_VERSION, "run_id": run_id, "grouper": if_h2.GROUPER_VERSION,
            "purpose": "CB1-B R1 replication data; frozen definitions only; never a screen",
            "git_commit": hb._git_commit(),
            "params": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"),
                       "exclude_runs": exclude_runs, "max_trades": max_trades, "max_rps": rps,
                       "disk_cap_bytes": disk_cap, "budget_min": budget_min, "seed": seed,
                       "price_fidelity_min": if_h2.FIDELITY_MIN},
            "started_utc": prior.get("started_utc", _utc(t_start)),
            "updated_utc": _utc(time.time()),
            "request_clock_now": prior.get("request_clock_now", _utc(now)),
            "requests": {"total_this_session": lim.requests, "retries": lim.retries,
                         "http_429": lim.throttled, "yielded_to_live_s": lim.yielded_s},
            "stopped": stopped, "disk_bytes": budget.scan(),
            "elapsed_s_this_session": round(time.time() - t_start, 1),
            **state, **(extra or {}),
        }
        budget.cap += 10**7
        budget.write(mpath, json.dumps(m, indent=1, sort_keys=True, default=float).encode())
        return m

    # 1-3: events -> ladders (once)
    lpath, epath = rdir / "ladders.jsonl.gz", rdir / "events.jsonl.gz"
    guard_rep = prior.get("guards")
    disc_rep = prior.get("discovery")
    if not lpath.exists():
        try:
            if not epath.exists():
                if should_stop is not None and should_stop():
                    return {"stopped": "should_stop before discovery; resumable"}
                events, disc_rep = if_h2.discover(lim, start, end, log=lambda *_: None,
                                                  extra_market_keys=("conditionId",))
                if out_of_budget():  # discover is not interruptible; keep its result
                    pass
                _save(budget, epath, events)
            else:
                events = if_h2.load_jsonl_gz(epath)
            ladders = if_h2.group_ladders(events)
            ev_ids, rg_ids = set(), set()
            if ifh2_ladder_file is not None:
                if not Path(ifh2_ladder_file).exists():
                    raise FileNotFoundError(f"IF-H2 ladder file missing: {ifh2_ladder_file}")
                ev_ids, rg_ids = _ids_from_ladders(if_h2.load_jsonl_gz(Path(ifh2_ladder_file)))
            samp: set[str] = set()
            for er in exclude_runs:
                sp = root / er / "sample.csv.gz"
                if not sp.exists():
                    raise FileNotFoundError(f"excluded run {er!r} has no {sp}")
                samp |= set(pd.read_csv(sp, usecols=["market_id"], dtype=str).market_id)
            ladders, guard_rep = apply_guards(ladders, ev_ids, rg_ids, samp)
            guard_rep.update({"ifh2_event_ids": len(ev_ids), "ifh2_rung_ids": len(rg_ids),
                              "history_sample_ids": len(samp)})
            _save(budget, lpath, ladders)
        except FileNotFoundError:
            raise  # a missing input is a loud failure, never a disk-budget stop
        except OSError as exc:
            return {"stopped": f"disk_budget: {exc}"}
    else:
        ladders = if_h2.load_jsonl_gz(lpath)
    extra = {"discovery": disc_rep, "guards": guard_rep, "n_ladders": len(ladders),
             "n_rungs": sum(len(lad["rungs"]) for lad in ladders)}
    rungs = [(lad["ladder_id"], r) for lad in ladders for r in lad["rungs"]]

    def span(r: dict) -> tuple[float, float] | None:
        return if_h2.rung_span(r, start.timestamp(), now)

    # 4: probe (once)
    ppath = rdir / "probe.json"
    if ppath.exists():
        probe = json.loads(ppath.read_text())
    else:
        rng = random.Random(f"{seed}|probe")
        pool = [r for _, r in rungs if span(r)]
        pick = rng.sample(pool, min(PROBE_N, len(pool))) if pool else []
        ok = 0
        for r in pick:
            a, b = span(r)  # type: ignore[misc]
            ok += int(bool(if_h2.fetch_ladder_prices(lim, r, a, min(b, a + if_h2.WINDOW_S))))
        probe = {"n": len(pick), "with_prices": ok,
                 "share": ok / len(pick) if pick else 0.0, "min_share": PROBE_MIN_SHARE,
                 "passed": bool(pick) and ok / len(pick) >= PROBE_MIN_SHARE,
                 "rung_ids": [r["market_id"] for r in pick]}
        budget.write(ppath, json.dumps(probe, indent=1).encode())
    extra["probe"] = probe
    if not probe["passed"]:
        m = manifest(None, {**extra, "probe_failed": True,
                            "note": "B1/B2 not testable; CB1-B rests on B3"})
        m["token"] = PROBE_FAILED_TOKEN
        return m

    # 5: per rung
    progress = rdir / "progress.jsonl"
    done: dict[str, dict] = {}
    if progress.exists():
        for line in progress.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["market_id"]] = rec
    for rec in done.values():
        if rec["status"] == "done":
            c = state["counts"]
            c["rungs_done"] += 1
            c["price_points"] += rec["price_points"]
            c["trades"] += rec["trades"]
            c["trades_truncated_rungs"] += int(rec["trades_truncated"])
    stopped = None
    since = 0
    for lid, r in rungs:
        mid = str(r["market_id"])
        if should_stop is not None and should_stop():
            stopped = "should_stop"
            break
        if done.get(mid, {}).get("status") == "done":
            continue
        if out_of_budget():
            stopped = "budget reached"
            break
        if wall_clock() >= t_seal_epoch:
            stopped = "t_seal_passed"
            break
        try:
            sp = span(r)
            pts = if_h2.fetch_ladder_prices(lim, r, *sp) if sp else []
            trades, tst = hb.fetch_trades(lim, _condition(r), key, max_trades, ts_cap=now)
            budget.write(rdir / "prices" / f"{mid}.csv.gz",
                         hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
            budget.write(rdir / "trades" / f"{mid}.csv.gz",
                         hb._gz_csv_bytes(hb.TRADE_COLUMNS, trades))
            rec = {"market_id": mid, "ladder_id": lid, "status": "done", "price_points": len(pts),
                   "span": list(sp) if sp else None, "trades": tst["n"],
                   "trades_truncated": tst["truncated"], "trades_oldest_ts": tst["oldest_ts"],
                   "trades_dropped_post_tfetch": tst["dropped_post_cap"],
                   "fetched_utc": _utc(time.time())}
            c = state["counts"]
            c["rungs_done"] += 1
            c["price_points"] += len(pts)
            c["trades"] += tst["n"]
            c["trades_truncated_rungs"] += int(tst["truncated"])
        except OSError as exc:
            stopped = f"disk_budget: {exc}"
            break
        except (RuntimeError, KeyError) as exc:
            rec = {"market_id": mid, "ladder_id": lid, "status": "failed", "error": str(exc)[:200]}
            state["counts"]["rungs_failed"] += 1
        with progress.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        since += 1
        if since >= 200:
            since = 0
            manifest("in_progress", extra)
    if stopped is None:
        extra["complete"] = True
        m = manifest(None, extra)
        m["token"] = COMPLETE_TOKEN
        return m
    return manifest(stopped, extra)


def _condition(r: dict) -> str:
    """Trades are keyed by condition id; the grouper keeps only the YES token and market id, so the
    rung dict carries ``condition_id`` when the walk stored it (``discover`` slim fields)."""
    cid = r.get("condition_id")
    if not cid:
        raise KeyError(f"rung {r.get('market_id')} has no condition_id")
    return cid


def _save(budget: hb.DiskBudget, path: Path, rows: list[dict]) -> None:
    import gzip
    import io

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in rows:
            gz.write((json.dumps(r, sort_keys=True) + "\n").encode())
    budget.write(path, buf.getvalue())
