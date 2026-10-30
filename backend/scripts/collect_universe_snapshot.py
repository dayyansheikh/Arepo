"""Collect one complete-universe Gamma snapshot (open markets) into data-dumps/research_lab."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from astrolabe.research_lab.collector import collect

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "data-dumps/research_lab/snapshots")
    ap.add_argument("--keep-raw", action="store_true", help="also write gzip raw pages (debug)")
    args = ap.parse_args()
    t = time.monotonic()
    m = collect(args.out, keep_raw=args.keep_raw)
    print(
        f"{m['capture_id']} state={m['state']} requests={m['request_count']} "
        f"pages={m['page_count']} rows={m['row_count']} dups={m['duplicates']} "
        f"secs={time.monotonic() - t:.1f}"
    )
    return 0 if m["state"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
