# ruff: noqa: E501
"""CH269 one-shot census and tails map runner (counts only, k = 0, uncounted; docs/research_lab/CREATIVE_HYPOTHESES_2026-11-02.md section 2 F). Research only; no network.

    python scripts/run_ch269_map.py --snapshot-root R --engine-root E --rules-root G --last-days 8 \\
        --out OUT/CH269_map.json --data-dumps-cap-gb 50

Read-only on every store. Refuses (exit 2) a snapshot root that is not a ``research_lab/snapshots`` directory, an engine root that is not ``research_lab/signal_engine``,
a rules root that is not ``research_lab/stream_gamma_rules``, any root that does not exist, and an output outside a ``research_lab`` directory; refuses to overwrite
``--out`` (exit 1); exits 75 (the queue's "not now") when the dumps directory is above ``--data-dumps-cap-gb`` or the output disk is short of ``--min-free-gb``.
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
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import boundary_map_ch240 as c240  # noqa: E402
from astrolabe.research_lab import census_map_ch269 as m  # noqa: E402
from astrolabe.research_lab import live_tests8_base as b  # noqa: E402

TEMPFAIL = 75
DUMPS = b.ROOT / ("data" + "-dumps")
FMT = "%Y-%m-%dT%H:%M:%SZ"


def _above_cap(gb: float | None) -> bool:
    return gb is not None and DUMPS.exists() and b.du_bytes(DUMPS) > gb * 2**30


def _root_ok(p: Path, name: str) -> bool:
    r = Path(p).resolve()
    return r.name == name and r.parent.name == "research_lab"


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
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--rules-root", type=Path, required=True)
    ap.add_argument("--start-utc")
    ap.add_argument("--end-utc")
    ap.add_argument("--last-days", type=int, default=None)
    ap.add_argument("--quote-days", type=int, default=45)
    ap.add_argument("--prediction-days", type=int, default=35)
    ap.add_argument("--champion", default="se0_champion_lr_mm")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not all(_root_ok(r, "snapshots") for r in args.snapshot_root) or not _root_ok(args.engine_root, "signal_engine") or not _root_ok(args.rules_root, "stream_gamma_rules") or not out_ok(args.out):
        print("refusing: roots must be research_lab/snapshots, research_lab/signal_engine and research_lab/stream_gamma_rules, and --out must lie under a research_lab directory")
        return 2
    missing = [str(r) for r in (*args.snapshot_root, args.engine_root, args.rules_root) if not Path(r).is_dir()]
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
    if args.last_days:
        start, end = last_days_span(args.snapshot_root, args.last_days)
        mode = f"last_days={args.last_days}"
    elif args.start_utc and args.end_utc:
        start, end, mode = args.start_utc, args.end_utc, "explicit"
    else:
        print("give --start-utc and --end-utc, or --last-days")
        return 2
    res = m.run_map(args.snapshot_root, args.engine_root, args.rules_root, start, end, args.quote_days, args.prediction_days, args.champion)
    res["span"]["mode"] = mode
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True, indent=1, default=str))
    try:
        os.link(tmp, args.out)  # write-once: fails if --out appeared meanwhile
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote {args.out} captures={res['sidecar_captures']['covered']} peak_rss_mb={res['peak_rss_mb']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
