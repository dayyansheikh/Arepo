# ruff: noqa: E501
"""CH240 boundary map runner (counts only, k = 0, uncounted; docs/research_lab/CREATIVE_HYPOTHESES_2026-10-30.md CH240). Research only; no network.

    python scripts/run_ch240_map.py --snapshot-root R [--snapshot-root R2] --start-utc 2026-10-16T00:00:00Z --end-utc 2026-10-23T00:00:00Z \\
        --out ../data-dumps/research_lab/ch240_map/CH240_map.json --data-dumps-cap-gb 44

Refuses to overwrite ``--out`` (exit 1); exits 75 (the queue's "not now") when data-dumps is above ``--data-dumps-cap-gb``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import boundary_map_ch240 as m  # noqa: E402
from astrolabe.research_lab import live_tests8_base as b  # noqa: E402

TEMPFAIL = 75
DATA_DUMPS = b.ROOT / "data-dumps"


def _above_cap(gb: float | None) -> bool:
    return gb is not None and DATA_DUMPS.exists() and b.du_bytes(DATA_DUMPS) > gb * 2**30


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot-root", type=Path, action="append", required=True)
    ap.add_argument("--start-utc", required=True)
    ap.add_argument("--end-utc", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if _above_cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return TEMPFAIL
    res = m.run_map(args.snapshot_root, args.start_utc, args.end_utc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True, indent=1))
    os.replace(tmp, args.out)
    print(f"wrote {args.out} captures={res['captures']['covered']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
