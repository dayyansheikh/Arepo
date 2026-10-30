# ruff: noqa: E501
"""LT14 census runner (docs/research_lab/LIVE_TESTS_14.md section 3 and 6; design text FROZEN at sha256 f047c000...). Research only; never trades; makes no network request.

    python scripts/run_live_tests14.py schema-precheck --engine-root E --snapshot-root R [--out H]      # schema and registry only, no value (6 job 1)
    python scripts/run_live_tests14.py seal --engine-root E --snapshot-root R --out S                    # 6 job 2 (once, after the 04:31Z capture of 2026-11-17)
    python scripts/run_live_tests14.py census --seal S --engine-root E --snapshot-root R --out cc14.json  # 6 job 3 (CC14: CH262 only; once)

NOT in this runner: the size check, the placebo / F, the analysis, the window reader and ops-stats (written only if the primary survives the census).

Every subcommand that writes refuses to overwrite ``--out`` (exit 1); the census runs ONCE (a marker beside the seal; a second run exits 2), only on a seal tracked by git and identical to
HEAD (exit 2 otherwise), exits 75 ("not now") above ``--data-dumps-cap-gb`` and exits 2 on any Refused (including peak RSS above 800 MB). It writes nothing to ``trials.jsonl`` (counts 0).
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
from astrolabe.research_lab import live_tests14 as lt  # noqa: E402
from astrolabe.research_lab import live_tests14_base as t  # noqa: E402


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
    for name, hlp in (("schema-precheck", "schema, registry and P's input-clock audit; no value is read"), ("seal", "hash every census input into the LT14 seal"), ("census", "CC14: the CH262 gate block on the sealed inputs (counts only; once)")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--engine-root", type=Path, default=t.ENGINE_ROOT)
        p.add_argument("--snapshot-root", type=Path, action="append")
        p.add_argument("--spec-dir", type=Path, default=t.SPEC_DIR)
        p.add_argument("--out", type=Path, default=None)
        if name == "census":
            p.add_argument("--seal", type=Path, default=t.SEALS / "lt14_census_inputs.json")
            p.add_argument("--data-dumps-cap-gb", type=float, default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "out", None) is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    roots = args.snapshot_root or [t.SNAPSHOT_ROOT]
    if args.cmd == "schema-precheck":
        return _write_out(args.out, json.dumps(lt.schema_precheck(engine_root=args.engine_root, snapshot_root=roots, spec_dir=args.spec_dir), sort_keys=True, indent=1, default=b._json))
    if args.cmd == "seal":
        res = lt.seal_inputs(engine_root=args.engine_root, snapshot_root=roots, spec_dir=args.spec_dir)
        if "error" in res:
            print(res["error"])
            return t.TEMPFAIL if res.get("retry") else 3
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=b._json))
    if _cap(args.data_dumps_cap_gb):
        print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
        return t.TEMPFAIL
    err, commit = _committed(args.seal)
    if err:
        print(f"refusing: {err}")
        return 2
    if lt.run_marker(args.seal).exists():
        print(f"refusing: the LT14 census already ran on this seal ({lt.run_marker(args.seal)}): a second run is refused")
        return 2
    try:
        res = lt.census_captures(seal=args.seal, engine_root=args.engine_root, snapshot_root=roots, spec_dir=args.spec_dir)
    except t.Refused as e:
        print(f"refusing: {e}")
        return 2
    res["seal_file"] = {"path": str(args.seal), "sha256": b.sha256_file(args.seal), "commit": commit}
    if "error" in res:
        print(res["error"])
        return 3
    if (msg := lt.claim_run(args.seal, args.out, {"seal_sha256": res["seal_file"]["sha256"], "status": res.get("statuses", {})})):
        print(f"refusing: {msg}")
        return 2
    return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=b._json))


if __name__ == "__main__":
    raise SystemExit(main())
