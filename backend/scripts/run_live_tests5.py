# ruff: noqa: E501
"""Live tests LT5 (docs/research_lab/LIVE_TESTS_5.md; DRAFT until registered). Research only; never trades; makes no network
request. This unit has the counts-only censuses and the size check; the reader (``run``, ``backfill-series``,
``ops-stats``) and ``analyze`` come in a later unit.

    python scripts/run_live_tests5.py census-captures --seal S --work W --out cf5_chw_crw.json   # CF5 (F), CHW (H), CRW (R)
    python scripts/run_live_tests5.py census-flow --sample-root R --work W --out cj_co.json      # CJ (J), CO (O)
    python scripts/run_live_tests5.py size-check --out size.json                                 # 12 binding scenarios

Every subcommand refuses to overwrite ``--out``; the censuses accept ``--data-dumps-cap-gb`` (exit 75 when data-dumps is
above the cap, the queue's "not now").
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests5 as lt  # noqa: E402
from astrolabe.research_lab import live_tests5_base as b  # noqa: E402

SEALS = lt.ROOT / "docs" / "research_lab" / "seals"


def _write_out(path: Path | None, txt: str) -> int:
    if path is None:
        print(txt)
        return 0
    if path.exists():
        print(f"refusing to overwrite {path}")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt)
    print(f"wrote {path} sha256={lt.sha256_file(path)}")
    return 0


def _cap(gb: float | None) -> bool:
    if gb is None:
        return False
    dd = lt.ROOT / "data-dumps"
    return bool(dd.exists() and b.du_bytes(dd) > gb * 2**30)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census-captures")
    c.add_argument("--seal", type=Path, default=SEALS / "lt5_census_inputs_captures.json")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    c.add_argument("--sweep-root", type=Path, default=lt.SWEEP_ROOT)
    c.add_argument("--day", action="append", default=None, help="UTC day (default: the spec census days)")
    c.add_argument("--out", type=Path, default=None)
    c.add_argument("--keep-work", action="store_true")
    c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    f = sub.add_parser("census-flow")
    f.add_argument("--sample-seal", type=Path, default=SEALS / "lt3_census_inputs_C2.json")
    f.add_argument("--capture-seal", type=Path, default=SEALS / "lt4_census_inputs_captures.json")
    f.add_argument("--sample-root", type=Path, action="append", required=True, help="restored trade_samples dir(s), searched in order")
    f.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    f.add_argument("--work", type=Path, required=True)
    f.add_argument("--out", type=Path, default=None)
    f.add_argument("--keep-work", action="store_true")
    f.add_argument("--data-dumps-cap-gb", type=float, default=None)
    z = sub.add_parser("size-check")
    z.add_argument("--worlds", type=int, default=None)
    z.add_argument("--draws", type=int, default=None)
    z.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.out is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd in ("census-captures", "census-flow") and _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return lt.TEMPFAIL
    if args.cmd == "census-captures":
        res = lt.census_captures(seal=args.seal, snapshot_root=args.snapshot_root, sweep_root=args.sweep_root, work=args.work, days=args.day)
    elif args.cmd == "census-flow":
        res = lt.census_flow(seal=args.sample_seal, capture_seal=args.capture_seal, sample_roots=args.sample_root,
                             snapshot_root=args.snapshot_root, work=args.work)
    else:
        from astrolabe.research_lab import live_tests5_analysis as la

        sc = lt.load_spec(sha=None)["size_check"]
        res = la.size_check(worlds=args.worlds or sc["worlds"], draws=args.draws or sc["draws"], seed=sc["seed"], nominal=sc["nominal"],
                            binding=sc["scenarios"])
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    res["code_sha256"] = lt.code_hashes()
    if not args.keep_work:
        lt.cleanup_census(args.work)
    rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    return 3 if "error" in res else rc


if __name__ == "__main__":
    raise SystemExit(main())
