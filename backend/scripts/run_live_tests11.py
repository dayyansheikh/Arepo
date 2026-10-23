# ruff: noqa: E501
"""Live tests LT11 (docs/research_lab/LIVE_TESTS_11.md, design text frozen at 991100db...; DRAFT until registered). Research only; never trades;
makes no network request.

    python scripts/run_live_tests11.py header-precheck --capture-dir C [--out H]                       # headers only, no rows
    python scripts/run_live_tests11.py seal --snapshot-root R --work W --out lt11_census_inputs.json   # q0691
    python scripts/run_live_tests11.py census --seal S --work W --out cc11.json                        # q0692 (CC11: CH234, CH233, CH232)
    python scripts/run_live_tests11.py size-check --out sc11.json [--dev --worlds N --draws N]         # q0693
    python scripts/run_live_tests11.py size-timing --out t11.json [--worlds 20 --draws 200]            # q0696: wall-clock per world only (8.4 step 3)
    python scripts/run_live_tests11.py reader [--out-root O]                                           # q0694 (host cron); exit 75 when nothing is new
    python scripts/run_live_tests11.py backfill-series [--out-root O]                                  # look-back series files before the window
    python scripts/run_live_tests11.py ops-stats [--root O]                                            # counts only; reads no price, spread or size column
    python scripts/run_live_tests11.py analyze --out a11.json                                          # q0695, not before the analysis date

LT11 ambiguity A1: the design (section 8) names ``scripts/research_lab/run_live_tests11.py``; the LT9 / LT10 runners live in ``backend/scripts/``, so this one does too.

Every subcommand that writes refuses to overwrite ``--out``; the census and the size check accept ``--data-dumps-cap-gb`` (exit 75 above it, the queue's "not
now"); the census runs only on a seal tracked by git and identical to HEAD (exit 2 otherwise). ``size-check`` refuses ``--worlds`` / ``--draws`` without ``--dev``.
``analyze`` refuses before the analysis date and on an unpinned, null or NaN spec or a code-hash mismatch (exit 2).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests11 as lt  # noqa: E402
from astrolabe.research_lab import live_tests11_base as b  # noqa: E402

SEALS = lt.ROOT / "docs" / "research_lab" / "seals"


def _now() -> float:
    return time.time()


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
    """(error, commit): the seal must be tracked by git and identical to HEAD (the census runs only on the COMMITTED seal)."""
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
    dd = lt.ROOT / "data-dumps"
    return bool(dd.exists() and b.du_bytes(dd) > gb * 2**30)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("header-precheck", help="field names of one capture (headers only, no rows)")
    h.add_argument("--capture-dir", type=Path)
    h.add_argument("--out", type=Path, default=None)
    q = sub.add_parser("seal", help="hash every sealed capture of the census span into the LT11 seal")
    q.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals first, then restore trees")
    q.add_argument("--unavailable", action="append", default=[], help="repeatable: a restore report (JSON) or an archive path that NO release holds")
    q.add_argument("--work", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("census", help="CC11: the three gate blocks on the sealed captures (counts only)")
    c.add_argument("--seal", type=Path, default=SEALS / "lt11_census_inputs.json")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, action="append")
    c.add_argument("--out", type=Path, default=None)
    c.add_argument("--keep-work", action="store_true")
    c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    s = sub.add_parser("size-check", help="the size check (1.8, 1.8.1)")
    s.add_argument("--out", type=Path, default=None)
    s.add_argument("--dev", action="store_true", help="development run at seed 20261497 x 100 + 99 (never the registered seed)")
    s.add_argument("--worlds", type=int, default=None)
    s.add_argument("--draws", type=int, default=None)
    s.add_argument("--power-worlds", type=int, default=0, help="--dev only: power-run worlds (the registered run uses 500)")
    s.add_argument("--data-dumps-cap-gb", type=float, default=None)
    tm = sub.add_parser("size-timing", help="8.4 step 3: wall-clock seconds per world of each of the 16 scenarios at a timing seed; no result of the worlds is written")
    tm.add_argument("--out", type=Path, default=None)
    tm.add_argument("--worlds", type=int, default=20)
    tm.add_argument("--draws", type=int, default=200)
    tm.add_argument("--seed", type=int, default=20261497 * 100 + 98, help="never 20261497 or the development seed 20261497 x 100 + 99 (refused)")
    tm.add_argument("--data-dumps-cap-gb", type=float, default=None)
    for name, help_ in (("reader", "the window reader (series, frozen units, due outcomes and twins; write-once; exit 75 when nothing is new)"),
                        ("backfill-series", "only the look-back series files before the window")):
        r = sub.add_parser(name, help=help_)
        r.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
        r.add_argument("--sweep-root", type=Path, default=lt.SWEEP_ROOT)
        r.add_argument("--out-root", type=Path, default=lt.OUT_ROOT)
        r.add_argument("--max-items", type=int, default=80)
        r.add_argument("--data-dumps-cap-gb", type=float, default=None)
    o = sub.add_parser("ops-stats", help="file, line, role, arm and status counts of live_tests11/ (reads no price column)")
    o.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    o.add_argument("--out", type=Path, default=None)
    a = sub.add_parser("analyze", help="the single analysis (not before the analysis date)")
    a.add_argument("--out-root", type=Path, default=lt.OUT_ROOT)
    a.add_argument("--out", type=Path, default=None)
    return ap


def _spec() -> dict:
    return lt.load_spec(sha=lt.SPEC_SHA256)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd in ("reader", "backfill-series"):
        if _cap(args.data_dumps_cap_gb):
            print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
            return lt.TEMPFAIL
        res = lt.run_once(snapshot_root=args.snapshot_root, sweep_root=args.sweep_root, root=args.out_root, spec=_spec(), max_items=args.max_items, series_only=args.cmd == "backfill-series")
        print(json.dumps(res, sort_keys=True, default=str))
        return lt.TEMPFAIL if res.get("status") in ("nothing_new", "locked") else 0
    if args.cmd == "ops-stats":
        return _write_out(args.out, json.dumps(lt.ops_stats(args.root), sort_keys=True, indent=1, default=str))
    if args.cmd == "header-precheck":
        return _write_out(args.out, json.dumps(lt.header_precheck(capture_dir=args.capture_dir), sort_keys=True, indent=1, default=str))
    if args.cmd == "size-check":
        if (args.worlds is not None or args.draws is not None) and not args.dev:
            print("refusing: --worlds / --draws need --dev (the registered size check is 2,000 worlds x 200 draws, seed 20261497)")
            return 2
        if _cap(args.data_dumps_cap_gb):
            return lt.TEMPFAIL
        from astrolabe.research_lab import live_tests11_worlds as wd

        return wd.size_check_cli(args, _write_out)
    if args.cmd == "size-timing":
        if _cap(args.data_dumps_cap_gb):
            return lt.TEMPFAIL
        from astrolabe.research_lab import live_tests11_worlds as wd

        return wd.size_timing_cli(args, _write_out)
    if args.cmd == "analyze":
        from astrolabe.research_lab import live_tests11_analysis as an

        return an.analyze_cli(args, _write_out, _now())
    if args.cmd == "census" and _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return lt.TEMPFAIL
    spec = lt.load_spec(sha=None)
    if args.cmd == "seal":
        res = lt.seal_inputs(snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], work=args.work, spec=spec, unavailable=args.unavailable)
        b.cleanup_census(args.work)
        if "error" in res:
            print(res["error"])
            return 3
        res["code_sha256"] = lt.code_hashes()
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=b._json))
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    res = lt.census_captures(seal=args.seal, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], work=args.work, spec=spec)
    res["code_sha256"] = lt.code_hashes()
    res["spec_sha256"], res["design_text_sha256"] = spec["_sha256"], lt.design_text_sha()
    res["seal_file"] = {"path": str(args.seal), "sha256": b.sha256_file(args.seal), "commit": commit}
    if not args.keep_work:
        b.cleanup_census(args.work)
    if "error" in res:
        print(res["error"])
        return 3
    return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=b._json))


if __name__ == "__main__":
    raise SystemExit(main())
