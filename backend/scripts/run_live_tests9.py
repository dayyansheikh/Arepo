# ruff: noqa: E501
"""Live tests LT9 (docs/research_lab/LIVE_TESTS_9.md, design text frozen at 098aa3fb...; DRAFT until registered). Research only; never trades;
makes no network request. CODE PHASE 1: the fresh seal, the counts-only censuses, the header pre-check and ``ops-stats``. (``run``,
``backfill-series``, ``size-check`` and ``analyze`` come in code phase 2 and refuse here.)

    python scripts/run_live_tests9.py header-precheck --capture-dir C --sweep-dir S --feed-dir F                      # headers only, no rows
    python scripts/run_live_tests9.py seal --snapshot-root R --sweep-root R --feed-root R --work W --out lt9_census_inputs.json   # q0641
    python scripts/run_live_tests9.py census-feed --seal S --work W --out cr9.json                       # CR9: CH215  # q0642
    python scripts/run_live_tests9.py census-captures --seal S --work W --out cc9.json                   # CC9: CH213, CH212  # q0643
    python scripts/run_live_tests9.py census-sweeps --seal S --work W --out cs9.json                     # CS9: CH214 (after T_E022)  # q0644
    python scripts/run_live_tests9.py ops-stats [--root R]

Every subcommand refuses to overwrite ``--out``; the censuses accept ``--data-dumps-cap-gb`` (exit 75 when data-dumps is above the cap, the
queue's "not now") and run only on a seal tracked by git and identical to HEAD (exit 2 otherwise); ``census-sweeps`` refuses before the spec's
``cs9_not_before_utc`` (E022's proposed analysis time; the orchestrator confirms T_E022). Each output carries the normalised ``code_sha256`` of
every hashed module.
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

from astrolabe.research_lab import live_tests9 as lt  # noqa: E402
from astrolabe.research_lab import live_tests9_base as b  # noqa: E402

SEALS = lt.ROOT / "docs" / "research_lab" / "seals"
PHASE2 = ("run", "backfill-series", "size-check", "analyze")
CENSUS = ("census-feed", "census-captures", "census-sweeps")


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
    h = sub.add_parser("header-precheck", help="field names of one capture, sweep and feed capture (headers only, no rows)")
    h.add_argument("--capture-dir", type=Path)
    h.add_argument("--sweep-dir", type=Path)
    h.add_argument("--feed-dir", type=Path)
    h.add_argument("--out", type=Path, default=None)
    q = sub.add_parser("seal", help="hash every capture, sweep 1 and reward_params capture of the sealed windows into the LT9 seal")
    q.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals first, then restore trees")
    q.add_argument("--sweep-root", type=Path, action="append")
    q.add_argument("--feed-root", type=Path, action="append")
    q.add_argument("--unavailable", action="append", default=[], help="repeatable: a q0640 restore report (JSON) or an archive path that NO release holds")
    q.add_argument("--work", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    for name, help_ in (("census-feed", "CR9: CH215 on the sealed feed captures and captures"), ("census-captures", "CC9: CH213 and CH212 on the sealed captures and feed captures"),
                        ("census-sweeps", "CS9: CH214 on the sealed sweeps and captures (after T_E022)")):
        c = sub.add_parser(name, help=help_)
        c.add_argument("--seal", type=Path, default=SEALS / "lt9_census_inputs.json")
        c.add_argument("--work", type=Path, required=True)
        c.add_argument("--snapshot-root", type=Path, action="append")
        c.add_argument("--feed-root", type=Path, action="append")
        if name == "census-sweeps":
            c.add_argument("--sweep-root", type=Path, action="append")
        c.add_argument("--out", type=Path, default=None)
        c.add_argument("--keep-work", action="store_true")
        c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    o = sub.add_parser("ops-stats", help="file, line, role, panel, route and status counts of live_tests9/ (reads no price column)")
    o.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    o.add_argument("--out", type=Path, default=None)
    for name in PHASE2:
        sub.add_parser(name, help="code phase 2 (not written yet): refuses")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd in PHASE2:
        print(f"refusing: '{args.cmd}' is code phase 2 and is not written yet")
        return 2
    if getattr(args, "out", None) is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd == "ops-stats":
        return _write_out(args.out, json.dumps(lt.ops_stats(args.root), sort_keys=True, indent=1))
    if args.cmd == "header-precheck":
        res = lt.header_precheck(capture_dir=args.capture_dir, sweep_dir=args.sweep_dir, feed_dir=args.feed_dir)
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1))
    if args.cmd in CENSUS and _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return lt.TEMPFAIL
    spec = lt.load_spec(sha=None)
    if args.cmd == "seal":
        res = lt.seal_inputs(snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], sweep_root=args.sweep_root or [lt.SWEEP_ROOT], feed_root=args.feed_root or [lt.FEED_ROOT],
                             work=args.work, spec=spec, unavailable=args.unavailable)
        lt.cleanup_census(args.work)
        if "error" in res:
            print(res["error"])
            return 3
        res["code_sha256"] = lt.code_hashes()
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    if args.cmd == "census-sweeps" and _now() < lt.epoch(spec["census_inputs"]["cs9_not_before_utc"]):
        print(f"refusing: CS9 runs only after T_E022 (not before {spec['census_inputs']['cs9_not_before_utc']}; LIVE_TESTS_9.md 7)")
        return 2
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    roots = {"snapshot_root": args.snapshot_root or [lt.SNAPSHOT_ROOT], "feed_root": args.feed_root or [lt.FEED_ROOT]}
    if args.cmd == "census-feed":
        res = lt.census_feed(seal=args.seal, work=args.work, spec=spec, **roots)
    elif args.cmd == "census-captures":
        res = lt.census_captures(seal=args.seal, work=args.work, spec=spec, **roots)
    else:
        res = lt.census_sweeps(seal=args.seal, sweep_root=args.sweep_root or [lt.SWEEP_ROOT], work=args.work, spec=spec, **roots)
    res["code_sha256"] = lt.code_hashes()
    res["spec_sha256"], res["design_text_sha256"] = spec["_sha256"], lt.design_text_sha()
    res["seal_file"] = {"path": str(args.seal), "sha256": lt.sha256_file(args.seal), "commit": commit}
    if not args.keep_work:
        lt.cleanup_census(args.work)
    rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    return 3 if "error" in res else rc


if __name__ == "__main__":
    raise SystemExit(main())
