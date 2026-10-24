"""Book sweep CLI: ``sweep_books.py --snapshot latest|<dir> [--repeat N] [--keep-raw]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from astrolabe.research_lab import book_sweep, forecast

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", required=True, help="'latest' or a snapshot directory")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--keep-raw", action="store_true", help="retain gzip raw response bodies")
    ap.add_argument("--dry-run", action="store_true", help="count tokens only, no network")
    args = ap.parse_args()
    if args.snapshot == "latest":
        caps = forecast.list_complete_captures()
        if not caps:
            print("no complete snapshot found")
            return 1
        snap = Path(caps[-1]["dir"])
    else:
        snap = Path(args.snapshot)
    if args.dry_run:
        tokens, _, _ = book_sweep.load_tokens(snap)
        print(f"{snap.name}: {len(tokens)} tokens, {-(-len(tokens) // book_sweep.BATCH_SIZE)} "
              "batches")
        return 0
    results = book_sweep.run_series(
        snap, book_sweep.httpx_transport(), repeat=max(1, args.repeat), keep_raw=args.keep_raw
    )
    for m in results:
        print(f"{m['sweep_id']} {m['state']} requested={m['tokens_requested']} "
              f"returned={m['tokens_returned']} requests={m['request_count']}")
    return 0 if all(m["state"] == "complete" for m in results) else 2


if __name__ == "__main__":
    sys.exit(main())
