"""CLI for the EXPLORATORY_HISTORICAL backfill (see astrolabe.research_lab.history_backfill).

    python scripts/backfill_history.py run --run-id h1 --n-markets 500
    python scripts/backfill_history.py panel --run-id h1

Power run (weighted topic oversampling, causal wallet first-trade lookups, run-scoped disk cap):
    python scripts/backfill_history.py run --run-id h3_power --n-markets 10000 \\
        --lookback-days 365 --seed arepo-h3-power --oversample 3 \\
        --exclude-runs h1_first,h2_main --wallet-min-usd 500 \\
        --wallet-cap 60000 --disk-cap-gb 3 --budget-scope run --checkpoint-every 200 \\
        --anchored-live-check --allow-collection-window
    python scripts/backfill_history.py panel --run-id h3_power        # heavy lock required
    python scripts/backfill_history.py wallet-table --run-id h3_power # heavy lock required

CB1 disjoint replication run (CREATIVE_BATCH_1.md CB1-F; sealed afterwards by scripts/cb1_h5.py):
    python scripts/backfill_history.py run --run-id h5_cb1 --seed arepo-h5-cb1 \\
        --exclude-runs h1_first,h2_main,h3_power --n-markets 7000 --lookback-days 450 \\
        --closed-future-days 400 --pages-per-window 20 --strata-profile cb1 --max-days 120 \\
        --head-days 8 --price-end close_or_end_max --max-trades 10000 --rps 4 \\
        --collector-lock-check --allow-collection-window --disk-cap-gb 0.62 --budget-scope run \\
        --checkpoint-every 200 --budget-min 150

Never run during the launchd collection window (:25-:55 after even UTC hours).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from astrolabe.research_lab import history_backfill as hb


def collection_window(now: datetime) -> bool:
    return now.hour % 2 == 0 and 24 <= now.minute < 59


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["run", "panel", "wallet-table"])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--root", default=str(hb.DEFAULT_ROOT))
    ap.add_argument("--n-markets", type=int, default=500)
    ap.add_argument("--seed", default="arepo-h1")
    ap.add_argument("--lookback-days", type=int, default=270)
    ap.add_argument("--min-volume", type=float, default=0.0)
    ap.add_argument("--max-days", type=int, default=120)
    ap.add_argument("--max-trades", type=int, default=5000)
    ap.add_argument("--category-mode", default="all", choices=["all", "include", "exclude"])
    ap.add_argument("--categories", default="", help="comma-separated fee_category values")
    ap.add_argument("--oversample", type=float, default=None,
                    help="power mode: weight for decision-asymmetric topics (e.g. 3)")
    ap.add_argument("--exclude-runs", default="", help="comma-separated earlier run ids")
    ap.add_argument("--wallet-min-usd", type=float, default=None)
    ap.add_argument("--wallet-cap", type=int, default=60000)
    ap.add_argument("--wallet-cache", default="", help="read-only first_trade.jsonl paths")
    ap.add_argument("--rps", type=float, default=hb.MAX_RPS)
    ap.add_argument("--disk-cap-gb", type=float, default=None)
    ap.add_argument("--budget-scope", default="root", choices=["root", "run"])
    ap.add_argument("--checkpoint-every", type=int, default=0)
    ap.add_argument("--anchored-live-check", action="store_true")
    ap.add_argument("--allow-collection-window", action="store_true")
    ap.add_argument("--closed-future-days", type=int, default=0,
                    help="also walk closed markets whose endDate is in the next N days")
    ap.add_argument("--pages-per-window", type=int, default=3)
    ap.add_argument("--strata-profile", default="default", choices=["default", "cb1"])
    ap.add_argument("--head-days", type=int, default=0,
                    help="extra price window [start, start+N d] when the tail does not reach it")
    ap.add_argument("--price-end", default="min", choices=["min", "close_or_end_max"])
    ap.add_argument("--budget-min", type=float, default=None,
                    help="wall-clock budget; stops between markets/days, exit 0, resumable")
    ap.add_argument("--collector-lock-check", action="store_true",
                    help="yield to the collector pass: flock probe on /tmp/arepo_collector.lock "
                    "or the anchored pass command line")
    a = ap.parse_args(argv)
    if collection_window(datetime.now(UTC)) and not a.allow_collection_window:
        print("refusing: inside the launchd collection window (:25-:55 after even UTC hours)")
        return 2
    root = Path(a.root)
    if a.cmd == "run":
        extra: dict = {}
        if a.disk_cap_gb is not None:
            extra["disk_cap"] = int(a.disk_cap_gb * 1024**3)
        if a.collector_lock_check:
            extra["live_check"] = hb.live_pass_or_lock
        elif a.anchored_live_check:
            extra["live_check"] = hb.live_pass_running_anchored
        m = hb.run(root, a.run_id, hb.httpx_transport(), n_markets=a.n_markets, seed=a.seed,
                   lookback_days=a.lookback_days, min_volume=a.min_volume, max_days=a.max_days,
                   max_trades=a.max_trades, should_stop=lambda: collection_window(
                       datetime.now(UTC)) and not a.allow_collection_window,
                   category_mode=a.category_mode,
                   categories=[c for c in a.categories.split(",") if c],
                   oversample=a.oversample,
                   exclude_runs=[c for c in a.exclude_runs.split(",") if c],
                   wallet_min_usd=a.wallet_min_usd, wallet_cap=a.wallet_cap,
                   wallet_cache_paths=[Path(c) for c in a.wallet_cache.split(",") if c],
                   budget_scope=a.budget_scope, checkpoint_every=a.checkpoint_every,
                   closed_future_days=a.closed_future_days, pages_per_window=a.pages_per_window,
                   strata_profile=a.strata_profile, price_end=a.price_end,
                   head_days=a.head_days, budget_min=a.budget_min, rps=a.rps, **extra)
        print(json.dumps({k: m.get(k) for k in ("counts", "requests", "disk_bytes", "stopped",
                                                "elapsed_s_this_session")}, indent=1))
    elif a.cmd == "panel":
        print(json.dumps(hb.build_panel(root / a.run_id), indent=1))
    else:
        from astrolabe.research_lab import history_sources as hs

        print(json.dumps(hs.build_new_wallet_table(
            root / a.run_id, hs.ROOT / "new_wallets",
            [Path(c) for c in a.wallet_cache.split(",") if c]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
