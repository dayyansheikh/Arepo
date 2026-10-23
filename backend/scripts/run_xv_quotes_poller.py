# ruff: noqa: E501
"""LT10 route 1 (LIVE_TESTS_10.md 8.2, D-LT10-1): the quotes-only successor of E009's poller. Research only; never trades.

NOT INSTALLED, NOT STARTED by the code commit. At the handover (8.2; after both E009's and E010's analysis commits, the successor's code freeze
check and the engine's second read root are recorded in the ledger) the orchestrator, at a 120 s boundary:
  1. disables E009's poller (``run/cross-venue-live.disabled``; last cycle recorded);
  2. copies E009's last ``pairs/pairs_*.json`` byte for byte (``cp -p``, sha256 recorded) to ``xv_quotes/pairs/`` and to
     ``xv_quotes/pairs_current.json`` (the pair list is continuous and the age rule fires the first own refresh at E009's time of day);
  3. adds the supervise.sh entry  ``[xv-quotes]="scripts/run_xv_quotes_poller.py"``  (a host change under the standing collection
     authorisation, with a ledger line; this commit does NOT edit supervise.sh).

  python scripts/run_xv_quotes_poller.py                  poll every 120 s (+ the daily refresh child)
  python scripts/run_xv_quotes_poller.py --max-cycles 30  stop after 30 cycles (dry run)
  python scripts/run_xv_quotes_poller.py --refresh        refresh the matched-pair list (E009's rule), then exit

Writes under data-dumps/research_lab/xv_quotes/ (quotes/, pairs/, pairs_current.json, runs.jsonl, refresh.log). Stops at its 3.0 GB cap (exit 3).
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import xv_quotes_poller as xq  # noqa: E402
from astrolabe.research_lab import xv_quotes_poller_base as xb  # noqa: E402


def limiters(rps: float):
    t = xb.http_transport()
    return hb.Limiter(t, rps=rps), hb.Limiter(t, rps=rps)


def refresh(root: Path, rps: float) -> int:
    # Network-only, but it yields to the live collector pass (heavy_lock.md convention), as E009's refresh.
    waited = hb.yield_to_live(hb.live_pass_running_anchored)
    k_lim, p_lim = limiters(rps)
    s = xq.refresh(k_lim, p_lim, root)
    s.update({"yielded_s": waited, "k_requests": k_lim.requests, "p_requests": p_lim.requests, "http_429": k_lim.throttled + p_lim.throttled})
    print(json.dumps(s), flush=True)
    return 0


def spawn_refresh(script: Path, root: Path, log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = log_path.open("a")
    return subprocess.Popen([sys.executable, str(script), "--refresh", "--root", str(root)], stdout=fh, stderr=fh)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=xq.ROOT)
    ap.add_argument("--max-cycles", type=int, default=0)
    ap.add_argument("--rps", type=float, default=0.9, help="per venue, poll loop (<= 1); E009's default")
    ap.add_argument("--refresh-rps", type=float, default=0.5, help="per venue, refresh process; E009's default")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
    if not xq.verified_ok():
        print("refusing: cross_venue_live_verified.json differs from E009's frozen file (sha256 1d6f942a...)")
        return 2
    a.root.mkdir(parents=True, exist_ok=True)
    if a.refresh:
        return refresh(a.root, min(a.refresh_rps, 0.95))
    k_lim, p_lim = limiters(min(a.rps, 0.95))
    poller = xq.XVQuotesPoller(k_lim, p_lim, root=a.root)
    code_commit = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1]).stdout.strip()
    logging.info("start %s src=%s code=%s root=%s", xb.VERSION, xq.SRC, code_commit, a.root)
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
        if xq.refresh_due(now, cur, child is not None and child.poll() is None, last_refresh_try):
            child = spawn_refresh(script, a.root, a.root / "refresh.log")
            last_refresh_try = now
            logging.info("refresh spawned pid=%s", child.pid)
        if not cur.exists():
            time.sleep(5)
            continue
        t_sched = (int(time.time()) // xb.CYCLE_S + 1) * xb.CYCLE_S
        while not stop["flag"] and time.time() < t_sched:
            time.sleep(min(1.0, max(0.0, t_sched - time.time())))
        if stop["flag"]:
            break
        try:
            s = poller.cycle(t_sched)
        except xq.CapReached:
            code = 3
            break
        except Exception as exc:  # keep the loop alive; the supervisor restarts on a real crash
            logging.warning("cycle failed: %s", type(exc).__name__)
            continue
        n += 1
        if s["rss_mb"] > xq.RSS_BUDGET_MB:
            logging.warning("rss %.0f MB above budget", s["rss_mb"])
        logging.info("cycle %d: %s", n, json.dumps(s))
        day = datetime.fromtimestamp(t_sched, UTC).strftime("%Y%m%d")
        if n % 30 == 1:
            xb.gzip_old_quotes(a.root, day)
        if a.max_cycles and n >= a.max_cycles:
            break
    if child is not None and child.poll() is None:
        child.terminate()
    print(json.dumps({"totals": poller.totals, "k_requests": k_lim.requests, "p_requests": p_lim.requests, "http_429": k_lim.throttled + p_lim.throttled,
                      "rss_mb": xb.rss_mb()}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
