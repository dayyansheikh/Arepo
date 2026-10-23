# ruff: noqa: E501
"""Live tests LT10 (docs/research_lab/LIVE_TESTS_10.md, design text frozen at 1da6c075...; DRAFT until registered). Research only; never trades;
makes no network request.

    python scripts/run_live_tests10.py run [--xv-root R] [--out-root O]                       # the 5-minute reader (host cron 3-58/5); exit 75 when nothing is new
    python scripts/run_live_tests10.py ops-stats [--root O | --stream [--xv-root R]]          # counts only; reads no price, spread or size column
    python scripts/run_live_tests10.py seal --e009-root R --snapshot-root R --e009-commit H --e010-commit H [--scope-decision TEXT] --out lt10_census_inputs.json   # q0661
    python scripts/run_live_tests10.py census-family --seal S --out cf10.json                 # CF10   # q0662
    python scripts/run_live_tests10.py census-kalshi --seal S --cf10 cf10.json --out ck10.json        # CK10   # q0663
    python scripts/run_live_tests10.py census-design --seal S --cf10 cf10.json --ck10 ck10.json --out cd10.json   # CD10   # q0664
    python scripts/run_live_tests10.py size-check --out sc10.json [--dev --worlds N --draws N]     # q0665
    python scripts/run_live_tests10.py analyze --out a10.json                                  # q0667, not before the analysis date

Every subcommand that writes refuses to overwrite ``--out``; the censuses accept ``--data-dumps-cap-gb`` (exit 75 above it, the queue's "not now") and
run only on a seal tracked by git and identical to HEAD whose two analysis commits are ancestors of the seal's own commit (exit 2 otherwise).
``size-check`` refuses ``--worlds`` / ``--draws`` without ``--dev``. ``analyze`` refuses before the analysis date, an unpinned, null or NaN spec, a
``k_tests`` naming a dropped test, and a design text that differs from the frozen one. Each output carries the normalised ``code_sha256`` of every hashed
module.
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

from astrolabe.research_lab import live_tests10 as lt  # noqa: E402
from astrolabe.research_lab import live_tests10_base as b  # noqa: E402

SEALS = lt.ROOT / "docs" / "research_lab" / "seals"
CENSUS = ("census-family", "census-kalshi", "census-design")
E009_ROOT = lt.E009_ROOT


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
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(txt)
    os.link(tmp, path)  # write-once, atomic
    tmp.unlink()
    print(f"wrote {path} sha256={b.sha256_file(path)}")
    return 0


def _git(path: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path.parent), *a], capture_output=True, text=True)


def _committed(path: Path) -> tuple[str | None, str | None]:
    """(error, commit): the seal must be tracked by git and identical to HEAD; its two analysis commits must be ancestors of the seal's own commit."""
    path = Path(path).resolve()
    if not path.exists():
        return f"seal {path} does not exist", None
    if _git(path, "ls-files", "--error-unmatch", "--", path.name).returncode != 0:
        return f"seal {path} is not tracked by git: commit it first", None
    if _git(path, "status", "--porcelain", "--", path.name).stdout.strip():
        return f"seal {path} differs from its committed copy", None
    commit = _git(path, "log", "-1", "--format=%H", "--", path.name).stdout.strip() or None
    sd = json.loads(path.read_text())
    for k in ("e009_analysis_commit", "e010_analysis_commit"):
        h = sd.get(k)
        if not h or _git(path, "merge-base", "--is-ancestor", h, commit or "HEAD").returncode != 0:
            return f"the seal's {k} is missing or not an ancestor of the seal's own commit", None
    return None, commit


def _cap(gb: float | None) -> bool:
    if gb is None:
        return False
    dd = lt.ROOT / "data-dumps"
    return bool(dd.exists() and b.du_bytes(dd) > gb * 2**30)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="the window reader (statuses and frozen state lines; write-once)")
    r.add_argument("--xv-root", type=Path, default=lt.XV_ROOT)
    r.add_argument("--out-root", type=Path, default=lt.OUT_ROOT)
    r.add_argument("--snapshot-root", type=Path, action="append")
    r.add_argument("--max-origins", type=int, default=288)
    o = sub.add_parser("ops-stats", help="file, unit, class and status counts of live_tests10/, or --stream: the successor's burn-in counts (reads no price column)")
    o.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    o.add_argument("--stream", action="store_true")
    o.add_argument("--xv-root", type=Path, default=lt.XV_ROOT)
    o.add_argument("--out", type=Path, default=None)
    q = sub.add_parser("seal", help="hash every sealed census input into the LT10 seal")
    q.add_argument("--e009-root", type=Path, action="append")
    q.add_argument("--snapshot-root", type=Path, action="append")
    q.add_argument("--e009-commit", required=True)
    q.add_argument("--e010-commit", required=True)
    q.add_argument("--scope-decision", default=None)
    q.add_argument("--out", type=Path, required=True)
    for name, help_ in (("census-family", "CF10: the family gates"), ("census-kalshi", "CK10: the Kalshi-side state shares (after CF10)"),
                        ("census-design", "CD10: the design gates (after CK10)")):
        c = sub.add_parser(name, help=help_)
        c.add_argument("--seal", type=Path, default=SEALS / "lt10_census_inputs.json")
        c.add_argument("--e009-root", type=Path, action="append")
        c.add_argument("--snapshot-root", type=Path, action="append")
        if name != "census-family":
            c.add_argument("--cf10", type=Path, required=True)
        if name == "census-design":
            c.add_argument("--ck10", type=Path, required=True)
        c.add_argument("--out", type=Path, default=None)
        c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    s = sub.add_parser("size-check", help="the size check (1.8, 1.8.1)")
    s.add_argument("--out", type=Path, default=None)
    s.add_argument("--worlds", type=int, default=None)
    s.add_argument("--draws", type=int, default=None)
    s.add_argument("--dev", action="store_true")
    s.add_argument("--data-dumps-cap-gb", type=float, default=None)
    a = sub.add_parser("analyze", help="the single analysis (not before the analysis date)")
    a.add_argument("--out", type=Path, default=None)
    a.add_argument("--xv-root", type=Path, default=lt.XV_ROOT)
    a.add_argument("--out-root", type=Path, default=lt.OUT_ROOT)
    return ap


def _spec():
    return lt.load_spec(sha=lt.SPEC_SHA256)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd == "run":
        res = lt.run_once(xv_root=args.xv_root, out_root=args.out_root, snapshot_roots=args.snapshot_root or [lt.SNAPSHOT_ROOT], spec=_spec(), max_origins=args.max_origins)
        print(json.dumps(res, sort_keys=True, default=str))
        return int(res.get("exit", 0))
    if args.cmd == "ops-stats":
        res = lt.ops_stats_stream(args.xv_root) if args.stream else lt.ops_stats(args.root)
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=str))
    if args.cmd == "size-check":
        if (args.worlds is not None or args.draws is not None) and not args.dev:
            print("refusing: --worlds / --draws need --dev (the registered size check is 2,000 worlds x 200 draws, seed 20261397)")
            return 2
        if _cap(args.data_dumps_cap_gb):
            return lt.TEMPFAIL
        from astrolabe.research_lab import live_tests10_analysis as an

        return an.size_check_cli(args, _write_out)
    if args.cmd == "analyze":
        from astrolabe.research_lab import live_tests10_analysis as an

        return an.analyze_cli(args, _write_out, _now())
    if args.cmd in CENSUS and _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return lt.TEMPFAIL
    spec = lt.load_spec(sha=None)
    e9 = args.e009_root or [E009_ROOT]
    snaps = args.snapshot_root or [lt.SNAPSHOT_ROOT]
    if args.cmd == "seal":
        res = lt.seal_inputs(e009_roots=e9, snapshot_roots=snaps, spec=spec, e009_commit=args.e009_commit, e010_commit=args.e010_commit,
                             scope_decision=args.scope_decision)
        if "error" in res:
            print(res["error"])
            return 3
        res["code_sha256"] = lt.code_hashes()
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=str))
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    kw = {"seal": args.seal, "e009_roots": e9, "snapshot_roots": snaps, "spec": spec}
    if args.cmd == "census-family":
        res = lt.census_family(**kw)
    else:
        cf10 = json.loads(args.cf10.read_text())
        res = lt.census_kalshi(**kw, cf10=cf10) if args.cmd == "census-kalshi" else lt.census_design(**kw, cf10=cf10, ck10=json.loads(args.ck10.read_text()))
    res["code_sha256"] = lt.code_hashes()
    res["spec_sha256"], res["design_text_sha256"] = spec["_sha256"], lt.design_text_sha()
    res["seal_file"] = {"path": str(args.seal), "sha256": b.sha256_file(args.seal), "commit": commit}
    rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=str))
    return 3 if "error" in res else rc


if __name__ == "__main__":
    raise SystemExit(main())
