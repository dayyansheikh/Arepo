# ruff: noqa: E501
"""Live tests LT6 (docs/research_lab/LIVE_TESTS_6.md; DRAFT until registered). Research only; never trades; makes no network
request. Subcommands: the sealed counts-only censuses, the size check, the reader (``run``, ``backfill-series``, ``ops-stats``) and the
single analysis (``analyze``).

    python scripts/run_live_tests6.py seal --snapshot-root R --sweep-root R --sample-root R --work W --out lt6_census_inputs.json  # q0581
    python scripts/run_live_tests6.py census-captures --seal S --work W --out cd_cb_cv.json   # CD (D), CB (B), CV (V)  # q0582
    python scripts/run_live_tests6.py census-flow --seal S --sample-root R --work W --out ck.json                    # CK (K)  # q0583
    python scripts/run_live_tests6.py size-check --out size.json                                   # 11 binding scenarios  # q0584
    python scripts/run_live_tests6.py run [--max-items N]        # the reader, once per pass (exit 75 = nothing new / locked / disk cap)  # q0585
    python scripts/run_live_tests6.py backfill-series            # look-back series / sweeps for the slots that started before the install
    python scripts/run_live_tests6.py ops-stats                  # counts only; reads no price column
    python scripts/run_live_tests6.py analyze --out result.json [--trials]   # the single analysis  # q0586

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
    z = sub.add_parser("size-check", help="the eleven binding size scenarios (1.8); the binding run uses the spec's worlds, draws and seed")
    z.add_argument("--dev", action="store_true", help="DEVELOPMENT ONLY: allow --worlds/--draws overrides; the output is marked dev and is never the registered statement")
    z.add_argument("--worlds", type=int, default=None)
    z.add_argument("--draws", type=int, default=None)
    z.add_argument("--nonbinding", action="store_true", help="also run scenario 12 and the planted-effect power runs on their own seeds (information only)")
    z.add_argument("--out", type=Path, default=None)
    r = sub.add_parser("run", help="the reader: one pass (series, sweeps, look-back labels, freezes, due outcomes)")
    r.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    r.add_argument("--sample-root", type=Path, default=lt.SAMPLE_ROOT)
    r.add_argument("--sweep-root", type=Path, default=lt.SWEEP_ROOT)
    r.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    r.add_argument("--max-items", type=int, default=40)
    r.add_argument("--dry-run-start", default=None, help="DRY RUN ONLY: window start instead of REGISTERED_UTC (lines stay unregistered; needs --root scratch)")
    r.add_argument("--dry-run-end", default=None)
    r.add_argument("--data-dumps-cap-gb", type=float, default=None, help="exit 75 (not now) if data-dumps exceeds this many GiB")
    k = sub.add_parser("backfill-series", help="write series / status / members / sweeps / look-back labels for the slots that started before the install (no freezes)")
    k.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    k.add_argument("--sweep-root", type=Path, default=lt.SWEEP_ROOT)
    k.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    k.add_argument("--max-items", type=int, default=400)
    k.add_argument("--dry-run-start", default=None)
    k.add_argument("--dry-run-end", default=None)
    o = sub.add_parser("ops-stats", help="counts only; reads no price column")
    o.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    a = sub.add_parser("analyze", help="the single registered analysis (refuses before the analysis date and on any pin mismatch)")
    a.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    a.add_argument("--out", type=Path, default=None)
    a.add_argument("--trials", action="store_true", help="append the counted trials line (kind live_tests6, n_tests = k) to the trials log")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is not None and args.out.exists():
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
    if args.cmd in ("run", "backfill-series"):
        if args.cmd == "run" and args.data_dumps_cap_gb is not None and _cap(args.data_dumps_cap_gb):
            print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
            return lt.TEMPFAIL
        dry = args.dry_run_start is not None
        if dry and args.root.resolve() == lt.OUT_ROOT.resolve():
            print("refusing a dry run into the live root: pass --root <scratch dir>")
            return 2
        spec = lt.load_spec(sha=None) if dry else lt.load_spec()
        if dry:
            spec["_pinned"] = False  # a dry run never writes confirmation lines
        st = lt.run_once(snapshot_root=args.snapshot_root, sample_root=getattr(args, "sample_root", lt.SAMPLE_ROOT), sweep_root=args.sweep_root, root=args.root,
                         spec=spec, registered_utc=args.dry_run_start or lt.REGISTERED_UTC, end_utc=args.dry_run_end or lt.END_UTC, max_items=args.max_items,
                         allow_late=dry, mode="run" if args.cmd == "run" else "backfill")
        print(json.dumps(st, sort_keys=True))
        if st.get("status") == "locked":
            print("another live_tests6 reader holds the lock: not now")
            return lt.TEMPFAIL
        if st.get("status") == "disk_cap":
            print("live_tests6 disk cap reached: collection stopped (window not extended)")
            return lt.TEMPFAIL
        return 0 if st["written"] else lt.TEMPFAIL
    if args.cmd == "ops-stats":
        spec = lt.load_spec(sha=None)
        print(json.dumps(lt.ops_stats(args.root, spec=spec, registered_utc=lt.REGISTERED_UTC), sort_keys=True, indent=1))
        return 0
    if args.cmd == "analyze":
        from astrolabe.research_lab import live_tests6_analysis as la

        if args.out is not None and args.out.exists():
            print(f"refusing to overwrite {args.out}")
            return 1
        res = la.analyze(args.root)
        txt = json.dumps(res, sort_keys=True, indent=1, default=str)
        if args.out:
            args.out.write_text(txt)
        if args.trials and res.get("tests"):
            from astrolabe.research_lab import provenance

            provenance.append_trial(la.trial_line(res))
        print(txt)
        return 0
    if args.cmd == "size-check":
        from astrolabe.research_lab import live_tests6_analysis as la

        spec = lt.load_spec(sha=None)
        sc = spec["size_check"]
        if (args.worlds is not None or args.draws is not None) and not args.dev:
            print("refusing --worlds/--draws without --dev: the binding run uses the spec values")
            return 2
        res = la.size_check(worlds=args.worlds or sc["worlds"], draws=args.draws or sc["draws"], seed=sc["seed"], nominal=sc["nominal"], binding=sc["scenarios"],
                            spec_sha256=spec["_sha256"], dev=args.dev, include_nonbinding=args.nonbinding, spec=spec)
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
