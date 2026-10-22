# ruff: noqa: E501
"""Live tests LT7 (docs/research_lab/LIVE_TESTS_7.md, text-frozen; DRAFT until registered). Research only; never trades; makes no
network request. CODE PHASE 1: the seal and the counts-only censuses. (The reader, ``ops-stats``, ``size-check`` and ``analyze``
come in code phase 2.)

    python scripts/run_live_tests7.py seal --snapshot-root R --sweep-root R --sample-root R --work W --out lt7_census_inputs.json   # q0601
    python scripts/run_live_tests7.py census-volsem --seal S --sample-root R --work W --out cv7.json      # CV7 (CH193 semantics)  # q0602
    python scripts/run_live_tests7.py census-captures --seal S --work W --out cc7.json                  # CC7: CH191, CH193, CH192  # q0603
    python scripts/run_live_tests7.py census-sweeps --seal S --work W --out cs7.json                    # CS7: CH195, CH197  # q0604
    python scripts/run_live_tests7.py rewards-null-share --seal S --work W --out rns.json              # null shares of the sealed reward fields  # q0601b

``census-flow`` is an alias of ``census-volsem`` (CV7 reads the sealed active-frame trade samples). Every subcommand refuses to
overwrite ``--out``; the censuses accept ``--data-dumps-cap-gb`` (exit 75 when data-dumps is above the cap, the queue's "not now")
and run only on a seal that is tracked by git and identical to HEAD (exit 2 otherwise). Each output carries the normalised
``code_sha256`` of every hashed module.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):  # BLAS threads 1 (census-code check must-fix 4); the queue has no env field
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests7 as lt  # noqa: E402
from astrolabe.research_lab import live_tests7_base as b  # noqa: E402

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
    q = sub.add_parser("seal", help="hash exactly the census inputs (each named in a source seal with an equal sha256) into the LT7 seal")
    q.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals first, then restore trees")
    q.add_argument("--sweep-root", type=Path, action="append", help="repeatable (default: the host root)")
    q.add_argument("--sample-root", type=Path, action="append", help="repeatable: restored trade_samples dir(s)")
    q.add_argument("--source-seal", type=Path, action="append", help="repeatable (default: the LT5 capture, LT3 C2 sample and LT4 capture seals; all three must exist)")
    q.add_argument("--unavailable", action="append", default=[], help="repeatable: a q0600 restore report (JSON) or an archive path that NO release holds; a source-sealed file absent locally in a needed slot refuses the seal unless listed here")
    q.add_argument("--work", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    for name, help_ in (("census-volsem", "CV7: CH193's volume24hr semantic gate on the sealed active-frame samples"), ("census-flow", "alias of census-volsem")):
        f = sub.add_parser(name, help=help_)
        f.add_argument("--seal", type=Path, default=SEALS / "lt7_census_inputs.json")
        f.add_argument("--sample-root", type=Path, action="append", required=True, help="restored trade_samples dir(s), searched in order")
        f.add_argument("--snapshot-root", type=Path, action="append", help="repeatable (default: the host root)")
        f.add_argument("--work", type=Path, required=True)
        f.add_argument("--out", type=Path, default=None)
        f.add_argument("--keep-work", action="store_true")
        f.add_argument("--data-dumps-cap-gb", type=float, default=None)
    c = sub.add_parser("census-captures", help="CC7: CH191, CH193 (CC7's half) and CH192 on the sealed captures")
    c.add_argument("--seal", type=Path, default=SEALS / "lt7_census_inputs.json")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, action="append", help="repeatable: host originals and restore trees (default: the host root)")
    c.add_argument("--out", type=Path, default=None)
    c.add_argument("--keep-work", action="store_true")
    c.add_argument("--data-dumps-cap-gb", type=float, default=None)
    r = sub.add_parser("rewards-null-share", help="counts-only null shares of the sealed sidecars' clob_rewards / rewards_max_spread / rewards_min_size")
    r.add_argument("--seal", type=Path, default=SEALS / "lt7_census_inputs.json")
    r.add_argument("--work", type=Path, required=True)
    r.add_argument("--snapshot-root", type=Path, action="append", help="repeatable (default: the host root)")
    r.add_argument("--out", type=Path, default=None)
    r.add_argument("--keep-work", action="store_true")
    r.add_argument("--data-dumps-cap-gb", type=float, default=None)
    s = sub.add_parser("census-sweeps", help="CS7: CH195 and CH197 on the sealed sweeps and their captures")
    s.add_argument("--seal", type=Path, default=SEALS / "lt7_census_inputs.json")
    s.add_argument("--work", type=Path, required=True)
    s.add_argument("--snapshot-root", type=Path, action="append", help="repeatable (default: the host root)")
    s.add_argument("--sweep-root", type=Path, action="append", help="repeatable (default: the host root)")
    s.add_argument("--out", type=Path, default=None)
    s.add_argument("--keep-work", action="store_true")
    s.add_argument("--data-dumps-cap-gb", type=float, default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd != "seal" and _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return lt.TEMPFAIL
    if args.cmd == "seal":
        srcs = args.source_seal or list(SOURCE_SEALS)
        missing = [str(p) for p in srcs if not Path(p).exists()]
        if missing:
            print(f"refusing: source seal(s) missing: {missing}")
            return 2
        res = lt.seal_inputs(snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], sweep_root=args.sweep_root or [lt.SWEEP_ROOT],
                             sample_root=args.sample_root or [lt.SAMPLE_ROOT], work=args.work,
                             source_seals=srcs, unavailable=args.unavailable)
        lt.cleanup_census(args.work)
        if "error" in res:
            print(res["error"])
            return 3
        res["code_sha256"] = lt.code_hashes()
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    if args.cmd in ("census-volsem", "census-flow"):
        res = lt.census_volsem(seal=args.seal, sample_roots=args.sample_root, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], work=args.work)
    elif args.cmd == "rewards-null-share":
        res = lt.rewards_null_share(seal=args.seal, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], work=args.work)
    elif args.cmd == "census-captures":
        res = lt.census_captures(seal=args.seal, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], work=args.work)
    else:
        res = lt.census_sweeps(seal=args.seal, snapshot_root=args.snapshot_root or [lt.SNAPSHOT_ROOT], sweep_root=args.sweep_root or [lt.SWEEP_ROOT], work=args.work)
    spec = lt.load_spec(sha=None)
    res["code_sha256"] = lt.code_hashes()
    res["spec_sha256"], res["design_text_sha256"] = spec["_sha256"], spec.get("design_text_sha256")
    res["seal_file"] = {"path": str(args.seal), "sha256": lt.sha256_file(args.seal), "commit": commit}
    if not args.keep_work:
        lt.cleanup_census(args.work)
    rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    return 3 if "error" in res else rc


if __name__ == "__main__":
    raise SystemExit(main())
