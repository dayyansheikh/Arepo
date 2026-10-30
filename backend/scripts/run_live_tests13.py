# ruff: noqa: E501
"""LT13 stage A runner (docs/research_lab/LIVE_TESTS_13.md section 6 and 7; design text FROZEN at ae594aa1...). Research only; never trades; makes no network request.

    python scripts/run_live_tests13.py header-precheck --capture-dir C [--out H]                       # headers only, no rows (committed before the seal)
    python scripts/lt13_restore_guard.py ...                                                           # q0720 (the restore; see that script)
    python scripts/run_live_tests13.py seal --snapshot-root R [--snapshot-root R2 ...] --work W --out S # q0721
    python scripts/run_live_tests13.py census --seal S --work W --out cc13.json                        # q0722 (CC13: CH253 only)

Stage B (target reader, worlds, size check, state-shift gate, analysis, ops-stats, reader) is NOT in this runner: it is written only for tests in ``k_tests`` after the census (7).

Every subcommand that writes refuses to overwrite ``--out`` (exit 1); the census runs ONCE (a marker beside the seal; a second run exits 2), only on a seal tracked by git and identical to
HEAD (exit 2 otherwise), and accepts ``--data-dumps-cap-gb`` (exit 75 above it, the queue's "not now"). It writes nothing to ``trials.jsonl`` (counts 0).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests12_base as b  # noqa: E402
from astrolabe.research_lab import live_tests13 as lt  # noqa: E402
from astrolabe.research_lab import live_tests13_base as t  # noqa: E402


def _write_out(path: Path | None, txt: str) -> int:
    if path is None:
        print(txt)
        return 0
    if path.exists():
        print(f"refusing to overwrite {path}")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt)
    print(f"wrote {path} sha256={b.sha256_file(path)}")
    return 0


def _git(path: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path.parent), *a], capture_output=True, text=True)


def _committed(path: Path) -> tuple[str | None, str | None]:
    path = Path(path).resolve()
    if not path.exists():
        return f"seal {path} does not exist", None
    if _git(path, "ls-files", "--error-unmatch", "--", path.name).returncode != 0:
        return f"seal {path} is not tracked by git: commit it first", None
    if _git(path, "status", "--porcelain", "--", path.name).stdout.strip():
        return f"seal {path} differs from its committed copy", None
    return None, _git(path, "log", "-1", "--format=%H", "--", path.name).stdout.strip() or None


def _cap(gb: float | None) -> bool:
    if gb is None:
        return False
    dd = t.ROOT / "data-dumps"
    return bool(dd.exists() and b.du_bytes(dd) > gb * 2**30)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("header-precheck", help="field names of one capture (headers only, no rows)")
    h.add_argument("--capture-dir", type=Path, required=True)
    h.add_argument("--out", type=Path, default=None)
    q = sub.add_parser("seal", help="hash every sealed capture of the census inputs into the LT13 seal")
    q.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals first, then restore trees (LT12's q0710 copies, LT13's q0720 copies)")
    q.add_argument("--unavailable", action="append", default=[], help="repeatable: a restore report (JSON) or an archive path that NO release holds")
    q.add_argument("--work", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("census", help="CC13: the CH253 gate block on the sealed captures (counts only; once)")
    c.add_argument("--seal", type=Path, default=t.SEALS / "lt13_census_inputs.json")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, action="append")
    c.add_argument("--out", type=Path, default=None)
    c.add_argument("--keep-work", action="store_true")
    c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd == "header-precheck":
        return _write_out(args.out, json.dumps(lt.header_precheck(capture_dir=args.capture_dir), sort_keys=True, indent=1, default=str))
    spec = t.load_spec()
    if args.cmd == "seal":
        res = lt.seal_inputs(snapshot_root=args.snapshot_root or [t.SNAPSHOT_ROOT], work=args.work, spec=spec, unavailable=args.unavailable)
        b.cleanup_census(args.work)
        if "error" in res:
            print(res["error"])
            return 3
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=b._json))
    if _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return t.TEMPFAIL
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    if lt.run_marker(args.seal).exists():
        print(f"refusing: the LT13 census already ran on this seal ({lt.run_marker(args.seal)}): a second run is refused")
        return 2
    try:
        res = lt.census_captures(seal=args.seal, snapshot_root=args.snapshot_root or [t.SNAPSHOT_ROOT], work=args.work, spec=spec, commit=commit or "unknown")
    except t.Refused as e:
        print(f"refusing: {e}")
        return 2
    res["seal_file"] = {"path": str(args.seal), "sha256": b.sha256_file(args.seal), "commit": commit}
    if not args.keep_work:
        b.cleanup_census(args.work)
    if "error" in res:
        print(res["error"])
        return 3
    if (msg := lt.claim_run(args.seal, args.out, {"seal_sha256": res["seal_file"]["sha256"], "status": res.get("statuses", {})})):
        print(f"refusing: {msg}")
        return 2
    return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=b._json))


if __name__ == "__main__":
    raise SystemExit(main())
