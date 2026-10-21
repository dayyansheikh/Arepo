# ruff: noqa: E501
"""Live tests LT6 (docs/research_lab/LIVE_TESTS_6.md; DRAFT until registered). Research only; never trades; makes no network
request. This unit has the sealed counts-only censuses; the reader (``run``, ``backfill-series``, ``ops-stats``), the
size check and ``analyze`` come in later units.

    python scripts/run_live_tests6.py seal --snapshot-root R --sweep-root R --sample-root R --work W --out lt6_census_inputs.json  # q0581
    python scripts/run_live_tests6.py census-captures --seal S --work W --out cd_cb_cv.json   # CD (D), CB (B), CV (V)  # q0582
    python scripts/run_live_tests6.py census-flow --seal S --sample-root R --work W --out ck.json                    # CK (K)  # q0583

Every subcommand refuses to overwrite ``--out``; the censuses accept ``--data-dumps-cap-gb`` (exit 75 when data-dumps is above
the cap, the queue's "not now") and run only on a seal that is tracked by git and identical to HEAD.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests5_base as b  # noqa: E402
from astrolabe.research_lab import live_tests6 as lt  # noqa: E402

SEALS = lt.ROOT / "docs" / "research_lab" / "seals"
SOURCE_SEALS = (SEALS / "lt5_census_inputs_captures.json", SEALS / "lt3_census_inputs_C2.json", SEALS / "lt4_census_inputs_captures.json")


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


def _committed(path: Path) -> tuple[str | None, str | None]:
    """(error, commit): the seal must be tracked by git and identical to HEAD (the censuses run only on the COMMITTED seal)."""
    path = Path(path).resolve()
    if not path.exists():
        return f"seal {path} does not exist", None

    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(path.parent), *a], capture_output=True, text=True)

    if git("ls-files", "--error-unmatch", "--", path.name).returncode != 0:
        return f"seal {path} is not tracked by git: commit it first", None
    if git("status", "--porcelain", "--", path.name).stdout.strip():
        return f"seal {path} differs from its committed copy", None
    return None, git("log", "-1", "--format=%H", "--", path.name).stdout.strip() or None


def _cap(gb: float | None) -> bool:
    if gb is None:
        return False
    dd = lt.ROOT / "data-dumps"
    return bool(dd.exists() and b.du_bytes(dd) > gb * 2**30)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("seal", help="hash exactly the census inputs (each named in a source seal with an equal sha256) into the LT6 seal")
    q.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals first, then the restore tree")
    q.add_argument("--sweep-root", type=Path, action="append", help="repeatable (default: the host root)")
    q.add_argument("--sample-root", type=Path, action="append", help="repeatable: restored trade_samples dir(s)")
    q.add_argument("--source-seal", type=Path, action="append", help="repeatable (default: the LT5 capture, LT3 C2 sample and LT4 capture seals)")
    q.add_argument("--work", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("census-captures", help="CD (D), CB (B) and CV (V) on the sealed capture span")
    c.add_argument("--seal", type=Path, default=SEALS / "lt6_census_inputs.json")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals and a restore tree (default: the host root)")
    c.add_argument("--sweep-root", type=Path, action="append", help="repeatable (default: the host root)")
    c.add_argument("--out", type=Path, default=None)
    c.add_argument("--keep-work", action="store_true")
    c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    f = sub.add_parser("census-flow", help="CK (K) on the sealed active-frame samples")
    f.add_argument("--seal", type=Path, default=SEALS / "lt6_census_inputs.json")
    f.add_argument("--sample-root", type=Path, action="append", required=True, help="restored trade_samples dir(s), searched in order")
    f.add_argument("--snapshot-root", type=Path, action="append", help="repeatable (default: the host root)")
    f.add_argument("--work", type=Path, required=True)
    f.add_argument("--out", type=Path, default=None)
    f.add_argument("--keep-work", action="store_true")
    f.add_argument("--data-dumps-cap-gb", type=float, default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.out is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd in ("census-captures", "census-flow") and _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return lt.TEMPFAIL
    if args.cmd == "seal":
        res = lt.seal_inputs(snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], sweep_root=args.sweep_root or [lt.SWEEP_ROOT],
                             sample_root=args.sample_root or [lt.SAMPLE_ROOT], work=args.work,
                             source_seals=args.source_seal or [p for p in SOURCE_SEALS if p.exists()])
        lt.cleanup_census(args.work)
        if "error" in res:
            print(res["error"])
            return 3
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    if args.cmd == "census-captures":
        res = lt.census_captures(seal=args.seal, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], sweep_root=args.sweep_root or [lt.SWEEP_ROOT], work=args.work)
    else:
        res = lt.census_flow(seal=args.seal, sample_roots=args.sample_root, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], work=args.work)
    res["code_sha256"] = lt.code_hashes()
    res["seal"] = {"path": str(args.seal), "sha256": lt.sha256_file(args.seal), "commit": commit}
    if not args.keep_work:
        lt.cleanup_census(args.work)
    rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    return 3 if "error" in res else rc


if __name__ == "__main__":
    raise SystemExit(main())
