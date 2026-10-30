# ruff: noqa: E501
"""q0717 LT13 fee-reading probe runner (counts only, k = 0, uncounted; docs/research_lab/LIVE_TESTS_13.md 1.4.3, 7.5). Research only; no network.

    python scripts/run_lt13_fee_probe.py --snapshot-root R --start-utc 2026-10-13T00:00:00Z --end-utc 2026-10-28T00:00:00Z \\
        --out ../data-dumps/research_lab/lt13_fee_probe/LT13_fee_probe.json --data-dumps-cap-gb 50

Prints the covered span (first and last covered capture, covered / expected slots, captures whose rows file is gone, gaps) and the
per-date means of the headline cells. Refuses snapshot roots that are not a ``research_lab/snapshots`` directory and outputs outside a
``research_lab`` directory (exit 2), refuses to overwrite ``--out`` (exit 1), exits 75 (the queue's "not now") when data-dumps is above
``--data-dumps-cap-gb`` or the output disk is short of ``--min-free-gb``. Never restores a capture.
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

from astrolabe.research_lab import live_tests8_base as b  # noqa: E402
from astrolabe.research_lab import lt13_fee_probe as m  # noqa: E402

TEMPFAIL = 75
DATA_DUMPS = b.ROOT / "data-dumps"


def _above_cap(gb: float | None) -> bool:
    return gb is not None and DATA_DUMPS.exists() and b.du_bytes(DATA_DUMPS) > gb * 2**30


def root_ok(p: Path) -> bool:
    r = Path(p).resolve()
    return r.name == "snapshots" and r.parent.name == "research_lab"


def out_ok(p: Path) -> bool:
    return "research_lab" in Path(p).resolve().parts


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot-root", type=Path, action="append", required=True)
    ap.add_argument("--start-utc", default="2026-10-13T00:00:00Z")
    ap.add_argument("--end-utc", default="2026-10-28T00:00:00Z")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    return ap


def summary_lines(res: dict) -> list[str]:
    c = res["captures"]
    cs = c["covered_span"]
    out = [f"span [{res['span']['start_utc']}, {res['span']['end_utc']}): covered {c['covered']} of {res['span']['expected_2h_slots']} slots "
           f"({c['covered_days']:.2f} days), first {cs['first_start_utc']}, last {cs['last_start_utc']}; rows gone (missing, not restored) "
           f"{len(c['rows_gone_counted_missing_never_restored'])}; non-complete {len(c['non_complete_state'])}; gaps > 2h30 {len(c['gaps_over_2h30'])}"]
    for g in c["gaps_over_2h30"]:
        out.append(f"  gap {g['after']} .. {g['before']} ({g['hours']} h)")
    for name, blk in res["headline_nonsports_excrypto_unrewarded"].items():
        a = blk["all_covered"]
        if a.get("n_captures"):
            out.append(f"{name}: mean {a['mean']:.1f} median {a['median']:.1f} (n {a['n_captures']}); by date " + ", ".join(f"{d[5:]} {v:.0f}" for d, v in blk["by_date_mean"].items() if v is not None))
        else:
            out.append(f"{name}: no captures")
    return out


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
    res = m.run_probe(args.snapshot_root, args.start_utc, args.end_utc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True, indent=1))
    os.replace(tmp, args.out)
    for line in summary_lines(res):
        print(line)
    print(f"wrote {args.out} captures={res['captures']['covered']} peak_rss_mb={res['peak_rss_mb']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
