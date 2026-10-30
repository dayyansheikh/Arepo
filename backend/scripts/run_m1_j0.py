# ruff: noqa: E501
"""M1-J0 runner (CH263; counts only, k = 0, uncounted; docs/research_lab/MEASUREMENT_M1_CH263.md section 9.1). Research only; no network.

    python scripts/run_m1_j0.py --snapshot-root R/snapshots --sweep-root R/book_sweeps [--engine-root R/signal_engine] \\
        --last-days 8 --out OUT/M1_J0.json --data-dumps-cap-gb 50

Read-only on every store. Refuses (exit 2) a snapshot root that is not ``research_lab/snapshots``, a sweep root that is not
``research_lab/book_sweeps``, an engine root that is not ``research_lab/signal_engine``, a missing root and an output outside a
``research_lab`` directory; refuses to overwrite ``--out`` (exit 1); exits 75 (the queue's "not now") when the dumps directory is
above ``--data-dumps-cap-gb`` or the output disk is short of ``--min-free-gb``.
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import boundary_map_ch240 as c240  # noqa: E402
from astrolabe.research_lab import m1_j0 as j0  # noqa: E402

TEMPFAIL = 75
DUMPS = Path(__file__).resolve().parents[2] / ("data" + "-dumps")


def _du_bytes(p: Path) -> int:
    tot = 0
    for dp, _dn, fn in os.walk(p):
        for f in fn:
            try:
                tot += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return tot


def _root_ok(p: Path | None, name: str) -> bool:
    if p is None:
        return True
    r = Path(p).resolve()
    return r.name == name and r.parent.name == "research_lab"


def out_ok(p: Path) -> bool:
    return "research_lab" in Path(p).resolve().parts


def last_days_span(root: Path, days: int) -> tuple[float, float]:
    caps, _ = j0.discover_captures(root, 0.0, 4.1e9)
    if not caps:
        raise SystemExit("no complete captures found for --last-days")
    end = caps[-1]["start"] + 1.0
    return end - days * 86400.0, end


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot-root", type=Path, required=True)
    ap.add_argument("--sweep-root", type=Path, required=True)
    ap.add_argument("--engine-root", type=Path, default=None)
    ap.add_argument("--start-utc")
    ap.add_argument("--end-utc")
    ap.add_argument("--last-days", type=int, default=None)
    ap.add_argument("--warmup-captures", type=int, default=12, help="captures that only feed the E3 history and k - 1 state (not classified)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (_root_ok(args.snapshot_root, "snapshots") and _root_ok(args.sweep_root, "book_sweeps") and _root_ok(args.engine_root, "signal_engine") and out_ok(args.out)):
        print("refusing: roots must be research_lab/snapshots, research_lab/book_sweeps and (optional) research_lab/signal_engine, and --out must lie under a research_lab directory")
        return 2
    missing = [str(r) for r in (args.snapshot_root, args.sweep_root, args.engine_root) if r is not None and not Path(r).is_dir()]
    if missing:
        print(f"refusing: root(s) missing: {missing}")
        return 2
    if args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.data_dumps_cap_gb is not None and DUMPS.exists() and _du_bytes(DUMPS) > args.data_dumps_cap_gb * 2**30:
        print(f"dumps directory above {args.data_dumps_cap_gb} GiB: not now")
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
        start, end, mode = c240.parse_utc(args.start_utc), c240.parse_utc(args.end_utc), "explicit"
    else:
        print("give --start-utc and --end-utc, or --last-days")
        return 2
    res = j0.run_j0(args.snapshot_root, args.sweep_root, args.engine_root, start, end, args.warmup_captures)
    res["span"]["mode"] = mode
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True, indent=1, default=str))
    try:
        os.link(tmp, args.out)  # write-once: fails if --out appeared meanwhile
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote {args.out} units={res['eligible_units']['total']} captures={res['span']['processed_captures']} peak_rss_mb={res['peak_rss_mb']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
