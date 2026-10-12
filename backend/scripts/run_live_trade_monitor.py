"""Foreground LIVE large-trade monitor (research only, read-only, never trades).

  python scripts/run_live_trade_monitor.py            loop every --interval seconds
  python scripts/run_live_trade_monitor.py --once     one cycle
  python scripts/run_live_trade_monitor.py --outcomes one outcome pass (separate later process)

Writes under data-dumps/research_lab/live_trades/. Stops at the 3 GB total cap (exit 3).
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import live_trade_monitor as ltm  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--max-cycles", type=int, default=0, help="stop after N cycles (0 = forever)")
    ap.add_argument("--interval", type=float, default=300.0)
    ap.add_argument("--min-cash", type=float, default=1000.0)
    ap.add_argument("--rps", type=float, default=0.8)
    ap.add_argument("--root", type=Path, default=ltm.ROOT)
    ap.add_argument("--no-profile", action="store_true")
    ap.add_argument("--outcomes", action="store_true", help="run the outcome writer, then exit")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(message)s")
    for n in ("httpx", "httpcore"):  # their INFO lines contain raw wallet addresses in URLs
        logging.getLogger(n).setLevel(logging.WARNING)
    lim = hb.Limiter(hb.httpx_transport(timeout=30.0), rps=min(a.rps, 0.95))
    if a.outcomes:
        print(json.dumps(ltm.write_outcomes(lim, a.root).__dict__))
        return 0
    cfg = ltm.MonitorConfig(min_cash=a.min_cash, interval_s=a.interval, rps=a.rps,
                            profile=not a.no_profile)
    mon = ltm.Monitor(lim, root=a.root, cfg=cfg)
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    n, code = 0, 0
    while not stop["flag"]:
        t0 = time.time()
        try:
            s = mon.run_cycle()
        except ltm.CapReached:
            code = 3
            break
        n += 1
        logging.info("cycle %d: %s", n, json.dumps({k: s.get(k) for k in (
            "status", "new_trades", "wallets_looked_up", "alerts", "controls", "requests",
            "http_429", "seconds", "rss_mb")}))
        if a.once or (a.max_cycles and n >= a.max_cycles):
            break
        end = t0 + a.interval
        while not stop["flag"] and time.time() < end:
            time.sleep(min(1.0, max(0.0, end - time.time())))
    print(json.dumps({"totals": mon.totals, "requests": lim.requests, "http_429": lim.throttled,
                      "rss_mb": ltm.rss_mb()}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
