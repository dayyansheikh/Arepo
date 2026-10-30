# ruff: noqa: E501
"""CH276 surviving-side census runner (counts only, k = 0, uncounted; docs/research_lab/CREATIVE_HYPOTHESES_2026-11-03.md section 2 E). Research only; no network.

    python scripts/run_ch276_map.py --snapshot-root R --engine-root E --monitor-root M --start-utc 2026-10-22T00:00:00Z --end-utc 2026-10-30T00:00:00Z \\
        --out OUT/CH276_map.json --data-dumps-cap-gb 50

The span is explicit (no --last-days) so the run cannot drift into measurement M1's window. The rules class is read from the engine's point-in-time ``aux/rules`` tables
under --engine-root (there is no --rules-root).

Read-only on every store. Refuses (exit 2) a snapshot root that is not a ``research_lab/snapshots`` directory, an engine root that is not ``research_lab/signal_engine``,
a monitor root that is not ``research_lab/live_trades``, any root that does not exist, and an output outside a
``research_lab`` directory; refuses to overwrite ``--out`` (exit 1); exits 75 (the queue's "not now") when the dumps directory is above ``--data-dumps-cap-gb`` or the
output disk is short of ``--min-free-gb``. Refuses (exit 3) when the reader meets a forbidden field or path (resolution, outcome, payoff, label, wallet).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import boundary_map_ch240 as c240  # noqa: E402
from astrolabe.research_lab import ch276_map as m  # noqa: E402
from astrolabe.research_lab import live_tests8_base as b  # noqa: E402

TEMPFAIL = 75
DUMPS = b.ROOT / ("data" + "-dumps")


def _above_cap(gb: float | None) -> bool:
    return gb is not None and DUMPS.exists() and b.du_bytes(DUMPS) > gb * 2**30


def _root_ok(p: Path, name: str) -> bool:
    r = Path(p).resolve()
    return r.name == name and r.parent.name == "research_lab"


def out_ok(p: Path) -> bool:
    return "research_lab" in Path(p).resolve().parts


def _period(s: str) -> tuple[str, str]:
    a, _, z = s.partition(":")
    if not a or not z or c240.parse_utc(a + "T00:00:00Z") != c240.parse_utc(a + "T00:00:00Z") or c240.parse_utc(z + "T00:00:00Z") != c240.parse_utc(z + "T00:00:00Z"):
        raise argparse.ArgumentTypeError("a period is YYYY-MM-DD:YYYY-MM-DD")
    return a, z


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot-root", type=Path, action="append", required=True)
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--monitor-root", type=Path, default=None, help="research_lab/live_trades (line 5); without it line 5 is reported unavailable")
    ap.add_argument("--start-utc", required=True)
    ap.add_argument("--end-utc", required=True)
    ap.add_argument("--engine-days", type=int, default=8, help="days of quotes / features / predictions counted for lines 3 and 4 (ending at the span end)")
    ap.add_argument("--warmup", type=int, default=12, help="captures fed before the span start (state only, not counted)")
    ap.add_argument("--spread-before", type=_period, default=m.PERIODS_DEFAULT[0])
    ap.add_argument("--spread-after", type=_period, default=m.PERIODS_DEFAULT[1])
    ap.add_argument("--champion", default=m.CHAMPION)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    roots_ok = all(_root_ok(r, "snapshots") for r in args.snapshot_root) and _root_ok(args.engine_root, "signal_engine")
    if args.monitor_root is not None:
        roots_ok = roots_ok and _root_ok(args.monitor_root, "live_trades")
    if not roots_ok or not out_ok(args.out):
        print("refusing: roots must be research_lab/snapshots, research_lab/signal_engine and research_lab/live_trades, and --out must lie under a research_lab directory")
        return 2
    must = [*args.snapshot_root, args.engine_root] + ([args.monitor_root] if args.monitor_root else [])
    missing = [str(r) for r in must if not Path(r).is_dir()]
    if missing:
        print(f"refusing: root(s) missing: {missing}")
        return 2
    if args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if _above_cap(args.data_dumps_cap_gb):
        print(f"dumps directory above {args.data_dumps_cap_gb} GiB: not now")
        return TEMPFAIL
    probe = args.out.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if shutil.disk_usage(probe).free < args.min_free_gb * 2**30:
        print(f"less than {args.min_free_gb} GiB free at the output: not now")
        return TEMPFAIL
    start, end = c240.parse_utc(args.start_utc), c240.parse_utc(args.end_utc)
    if not (start == start and end == end and start < end):
        print("--start-utc / --end-utc must be ISO UTC times with start < end")
        return 2
    try:
        res = m.run_map(args.snapshot_root, args.engine_root, args.monitor_root, start, end, args.engine_days, args.warmup, (args.spread_before, args.spread_after), args.champion)
    except m.Refusal as exc:
        print(f"refusing: {exc}")
        return 3
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1, default=str))  # insertion order kept: the field-semantics line is first
    try:
        os.link(tmp, args.out)  # write-once: fails if --out appeared meanwhile
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote {args.out} captures={res['span']['counted_captures']} peak_rss_mb={res['peak_rss_mb']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
