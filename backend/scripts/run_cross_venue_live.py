"""LIVE cross-venue (Kalshi -> Polymarket lead) prospective test. Research only; never trades.

  python scripts/run_cross_venue_live.py                 poll every 120 s (+ daily refresh)
  python scripts/run_cross_venue_live.py --max-cycles 30 stop after 30 cycles (pilot)
  python scripts/run_cross_venue_live.py --refresh       refresh the matched-pair list, then exit
  python scripts/run_cross_venue_live.py --outcomes      recover pending outcomes, then exit
  python scripts/run_cross_venue_live.py --ops-stats     operational stats (never reads outcomes)
  python scripts/run_cross_venue_live.py --freeze        build the frozen spec from the historical
                                                         series (run once; prints the sha256 to pin)
  python scripts/run_cross_venue_live.py --analyze START END   registered E009 statistics

Writes under data-dumps/research_lab/cross_venue_live/. Stops at the 2 GB total cap (exit 3).
See docs/research_lab/CROSS_VENUE_LIVE.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import cross_venue as cv  # noqa: E402
from astrolabe.research_lab import cross_venue_live as cvl  # noqa: E402
from astrolabe.research_lab import cross_venue_live_e010 as e010  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402

HIST = cvl.forecast.ROOT / "data-dumps" / "research_lab" / "cross_venue"
MIN_USABLE_STEPS = 200  # as run_cross_venue.py


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def freeze() -> int:
    import numpy as np

    rows = json.load(open(HIST / "matches.json"))
    pairs = []
    for r in rows:
        f = HIST / "series" / f"{r['k_ticker']}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        pts = [(int(a), float(b)) for a, b in z["ps"]]
        g = cv.align_pair(pts, z["kc"], *map(int, z["win"]), pm_lag_s=0.0)
        g_cons = cv.align_pair(pts, z["kc"], *map(int, z["win"]))
        # pair set = the study's analysis set (>= 200 usable steps under its primary alignment)
        if int(cv.usable(g_cons).sum()) >= MIN_USABLE_STEPS:
            pairs.append(cv.PairSeries(r["k_ticker"], r["p_event_id"], g, r["k_cat"]))
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HIST.parents[2]
    ).stdout.strip()
    prov = {
        "source_study": "docs/research_lab/CROSS_VENUE_STUDY.md (cross-venue-v1)",
        "matches_json_sha256": _sha(HIST / "matches.json"),
        "results_json_sha256": _sha(HIST / "results.json"),
        "n_pairs": len(pairs),
        "n_clusters": len({p.cluster for p in pairs}),
        "code_commit": commit,
        "pair_rule": "study analysis set: >= 200 usable steps under "
        "the conservative alignment (341 pairs, 190 events)",
    }
    spec = cvl.freeze_spec(pairs, prov)
    raw = cvl.spec_bytes(spec)
    cvl.SPEC_PATH.write_bytes(raw)
    print(
        json.dumps(
            {
                "path": str(cvl.SPEC_PATH),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "n_pairs": len(pairs),
            }
        )
    )
    return 0


def freeze_e010() -> int:
    """E010 frozen spec: refit once on the revision-r1 cleaned set C1 (316 pairs)."""
    import numpy as np

    r1 = json.load(open(HIST / "results_r1.json"))
    drop = set(r1["audit"]["rule"])
    rows = json.load(open(HIST / "matches.json"))
    pairs = []
    for r in rows:
        f = HIST / "series" / f"{r['k_ticker']}.npz"
        if not f.exists() or r["k_ticker"] in drop:
            continue
        z = np.load(f)
        pts = [(int(a), float(b)) for a, b in z["ps"]]
        g = cv.align_pair(pts, z["kc"], *map(int, z["win"]), pm_lag_s=0.0)
        g_cons = cv.align_pair(pts, z["kc"], *map(int, z["win"]))
        if int(cv.usable(g_cons).sum()) >= MIN_USABLE_STEPS:
            pairs.append(cv.PairSeries(r["k_ticker"], r["p_event_id"], g, r["k_cat"]))
    gr = r1["C1_title_based_primary"]["granger"]
    hist = {
        k: {x: gr[k][x] for x in ("rel_mse_gain", "ci", "n_obs", "n_clusters")}
        for k in ("gap_6", "gapk_6", "gap_36", "gapk_36")
    }
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HIST.parents[2]
    ).stdout.strip()
    prov = {
        "source_study": "docs/research_lab/CROSS_VENUE_STUDY.md section 10 (revision r1, C1)",
        "matches_json_sha256": _sha(HIST / "matches.json"),
        "results_r1_json_sha256": _sha(HIST / "results_r1.json"),
        "dropped_tickers": sorted(drop),
        "n_pairs": len(pairs),
        "n_clusters": len({p.cluster for p in pairs}),
        "code_commit": commit,
    }
    spec = e010.freeze_spec(pairs, prov, hist)
    raw = cvl.spec_bytes(spec)
    e010.SPEC_PATH.write_bytes(raw)
    print(
        json.dumps(
            {
                "path": str(e010.SPEC_PATH),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "n_pairs": len(pairs),
                "n_clusters": prov["n_clusters"],
            }
        )
    )
    return 0


def limiters(rps: float):
    t = cvl.http_transport()
    return hb.Limiter(t, rps=rps), hb.Limiter(t, rps=rps)


def refresh(root: Path, rps: float) -> int:
    # Network-only, but it yields to the live collector pass (heavy_lock.md convention).
    waited = hb.yield_to_live(hb.live_pass_running_anchored)
    k_lim, p_lim = limiters(rps)
    s = cvl.refresh_pairs(k_lim, p_lim, root)
    s.update(
        {
            "yielded_s": waited,
            "k_requests": k_lim.requests,
            "p_requests": p_lim.requests,
            "http_429": k_lim.throttled + p_lim.throttled,
        }
    )
    print(json.dumps(s), flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=cvl.ROOT)
    ap.add_argument("--max-cycles", type=int, default=0)
    ap.add_argument("--rps", type=float, default=0.9, help="per venue, poll loop (<= 1)")
    ap.add_argument("--refresh-rps", type=float, default=0.5, help="per venue, refresh process")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--outcomes", action="store_true")
    ap.add_argument("--ops-stats", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--freeze-e010", action="store_true")
    ap.add_argument("--analyze-e010", nargs=2, metavar=("START_UTC", "END_UTC"))
    ap.add_argument("--analyze", nargs=2, metavar=("START_UTC", "END_UTC"))
    ap.add_argument("--role", default="prospective_confirmation")
    a = ap.parse_args()
    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s"
    )
    a.root.mkdir(parents=True, exist_ok=True)
    if a.freeze:
        return freeze()
    if a.freeze_e010:
        return freeze_e010()
    if a.analyze_e010:
        print(
            e010.dump(
                e010.analyze(
                    a.root, start_utc=a.analyze_e010[0], end_utc=a.analyze_e010[1], role=a.role
                )
            )
        )
        return 0
    if a.refresh:
        return refresh(a.root, min(a.refresh_rps, 0.95))
    if a.ops_stats:
        print(json.dumps(cvl.ops_stats(a.root), indent=1))
        return 0
    if a.analyze:
        print(
            json.dumps(
                cvl.analyze(a.root, start_utc=a.analyze[0], end_utc=a.analyze[1], role=a.role),
                indent=1,
                default=float,
            )
        )
        return 0
    if a.outcomes:
        w = cvl.OutcomeWriter(a.root)
        rec = w.recover(time.time(), window_s=6 * 3600)
        print(json.dumps({"recovered": rec, "written": w.update(time.time())}))
        return 0

    k_lim, p_lim = limiters(min(a.rps, 0.95))
    poller = cvl.Poller(k_lim, p_lim, root=a.root)
    poller.spec["_code"] = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    ).stdout.strip()
    try:  # E010 never blocks E009: a spec or recovery problem disables only the E010 writer
        w = e010.E010Writer(a.root)
        w.spec["_code"] = poller.spec["_code"]
        logging.info(
            "E010 writer on: spec=%s registered=%s recovered=%s",
            w.spec["_sha256"][:12],
            e010.REGISTERED_UTC,
            json.dumps(w.recover(time.time())),
        )
        poller.extras.append(w)
    except Exception as exc:
        logging.warning("E010 writer disabled: %s", type(exc).__name__)
    rec = poller.outcomes.recover(time.time())
    logging.info(
        "start %s spec=%s code=%s registered=%s recovered=%s",
        cvl.VERSION,
        poller.spec["_sha256"][:12],
        poller.spec["_code"],
        cvl.REGISTERED_UTC,
        json.dumps(rec),
    )
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    script = Path(__file__).resolve()
    child: subprocess.Popen | None = None
    last_refresh_try = 0.0
    n, code = 0, 0
    while not stop["flag"]:
        now = time.time()
        cur = a.root / "pairs_current.json"
        age = now - cur.stat().st_mtime if cur.exists() else float("inf")
        if (
            (child is None or child.poll() is not None)
            and age >= cvl.REFRESH_EVERY_S
            and now - last_refresh_try >= 3600
        ):
            child = cvl.spawn_refresh(script, a.root, a.root / "refresh.log")
            last_refresh_try = now
            logging.info("refresh spawned pid=%s", child.pid)
        if not cur.exists():
            time.sleep(5)
            continue
        t_sched = (int(time.time()) // cvl.CYCLE_S + 1) * cvl.CYCLE_S
        while not stop["flag"] and time.time() < t_sched:
            time.sleep(min(1.0, max(0.0, t_sched - time.time())))
        if stop["flag"]:
            break
        try:
            s = poller.cycle(t_sched)
        except cvl.CapReached:
            code = 3
            break
        except Exception as exc:  # keep the loop alive; launchd restarts on a real crash
            logging.warning("cycle failed: %s", type(exc).__name__)
            continue
        n += 1
        if s["rss_mb"] > cvl.RSS_BUDGET_MB:
            logging.warning("rss %.0f MB above budget", s["rss_mb"])
        logging.info("cycle %d: %s", n, json.dumps(s))
        day = datetime.fromtimestamp(t_sched, UTC).strftime("%Y%m%d")
        if n % 30 == 1:
            cvl.gzip_old_quotes(a.root, day)
        if a.max_cycles and n >= a.max_cycles:
            break
    if child is not None and child.poll() is None:
        child.terminate()
    print(
        json.dumps(
            {
                "totals": poller.totals,
                "k_requests": k_lim.requests,
                "p_requests": p_lim.requests,
                "http_429": k_lim.throttled + p_lim.throttled,
                "rss_mb": cvl.rss_mb(),
            }
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
