"""CLI for the EXPLORATORY_HISTORICAL backfill (see astrolabe.research_lab.history_backfill).

    python scripts/backfill_history.py run --run-id h1 --n-markets 500
    python scripts/backfill_history.py panel --run-id h1

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
    return now.hour % 2 == 0 and 25 <= now.minute < 55


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["run", "panel"])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--root", default=str(hb.DEFAULT_ROOT))
    ap.add_argument("--n-markets", type=int, default=500)
    ap.add_argument("--seed", default="arepo-h1")
    ap.add_argument("--lookback-days", type=int, default=270)
    ap.add_argument("--min-volume", type=float, default=1000.0)
    ap.add_argument("--max-days", type=int, default=120)
    ap.add_argument("--max-trades", type=int, default=5000)
    ap.add_argument("--category-mode", default="all", choices=["all", "include", "exclude"])
    ap.add_argument("--categories", default="", help="comma-separated fee_category values")
    ap.add_argument("--allow-collection-window", action="store_true")
    a = ap.parse_args(argv)
    if collection_window(datetime.now(UTC)) and not a.allow_collection_window:
        print("refusing: inside the launchd collection window (:25-:55 after even UTC hours)")
        return 2
    root = Path(a.root)
    if a.cmd == "run":
        m = hb.run(root, a.run_id, hb.httpx_transport(), n_markets=a.n_markets, seed=a.seed,
                   lookback_days=a.lookback_days, min_volume=a.min_volume, max_days=a.max_days,
                   max_trades=a.max_trades, category_mode=a.category_mode,
                   categories=[c for c in a.categories.split(",") if c])
        print(json.dumps({k: m[k] for k in ("counts", "requests", "disk_bytes", "stopped",
                                           "elapsed_s_this_session")}, indent=1))
    else:
        print(json.dumps(hb.build_panel(root / a.run_id), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
