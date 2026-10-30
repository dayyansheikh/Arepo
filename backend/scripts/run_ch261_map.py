# ruff: noqa: E501
"""CH261 LT13 population map runner (counts only, k = 0, uncounted; docs/research_lab/CREATIVE_HYPOTHESES_2026-11-01.md CH261). Research only; no network.

    python scripts/run_ch261_map.py --snapshot-root R --start-utc 2026-10-13T00:00:00Z --end-utc 2026-10-28T00:00:00Z \\
        --out ../data-dumps/research_lab/ch261_map/CH261_map.json --data-dumps-cap-gb 40
    (or --last-days 14 instead of --start-utc / --end-utc: the span is the latest complete capture's slot minus N days, declared in the output)

Refuses snapshot roots that are not a ``research_lab/snapshots`` directory and outputs outside a ``research_lab`` directory (exit 2), refuses to
overwrite ``--out`` (exit 1), exits 75 (the queue's "not now") when data-dumps is above ``--data-dumps-cap-gb`` or the output disk is short of ``--min-free-gb``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import boundary_map_ch240 as c240  # noqa: E402
from astrolabe.research_lab import live_tests8_base as b  # noqa: E402
from astrolabe.research_lab import population_map_ch261 as m  # noqa: E402

TEMPFAIL = 75
DATA_DUMPS = b.ROOT / "data-dumps"
FMT = "%Y-%m-%dT%H:%M:%SZ"


def _above_cap(gb: float | None) -> bool:
    return gb is not None and DATA_DUMPS.exists() and b.du_bytes(DATA_DUMPS) > gb * 2**30


def root_ok(p: Path) -> bool:
    r = Path(p).resolve()
    return r.name == "snapshots" and r.parent.name == "research_lab"


def out_ok(p: Path) -> bool:
    return "research_lab" in Path(p).resolve().parts


def last_days_span(roots: list[Path], days: int) -> tuple[str, str]:
    caps = c240.discover(roots, "2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z")
    if not caps:
        raise SystemExit("no complete captures found for --last-days")
    end = datetime.fromtimestamp(caps[-1]["start"], UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
    end = end.replace(hour=end.hour - end.hour % 2)
    return (end - timedelta(days=days)).strftime(FMT), end.strftime(FMT)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot-root", type=Path, action="append", required=True)
    ap.add_argument("--start-utc")
    ap.add_argument("--end-utc")
    ap.add_argument("--last-days", type=int, default=None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not all(root_ok(r) for r in args.snapshot_root) or not out_ok(args.out):
        print("refusing: snapshot roots must be research_lab/snapshots and --out must lie under a research_lab directory")
        return 2
    if args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if _above_cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return TEMPFAIL
    probe = args.out.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if shutil.disk_usage(probe).free < args.min_free_gb * 2**30:
        print(f"less than {args.min_free_gb} GiB free at the output: not now")
        return TEMPFAIL
    if args.last_days:
        start, end = last_days_span(args.snapshot_root, args.last_days)
        mode = f"last_days={args.last_days}"
    elif args.start_utc and args.end_utc:
        start, end, mode = args.start_utc, args.end_utc, "explicit"
    else:
        print("give --start-utc and --end-utc, or --last-days")
        return 2
    res = m.run_map(args.snapshot_root, start, end)
    res["span"]["mode"] = mode
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True, indent=1))
    os.replace(tmp, args.out)
    print(f"wrote {args.out} captures={res['captures']['covered']} peak_rss_mb={res['peak_rss_mb']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
