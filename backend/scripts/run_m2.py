# ruff: noqa: E501
"""M2 (CH264) runner: ``j1`` (window extractor and blind follow-up recorder), ``j2`` (window close / follow-up close), ``j3`` (read-out fetch), ``analysis``.
See docs/research_lab/MEASUREMENT_M2_CH264.md section 9. Research only. Refusals exit 2 (declared refusal) or 3 (pin mismatch, values printed); every job exits 75
when data-dumps exceeds --data-dumps-cap-gb (and ``j1`` when the disk is short). The store must sit in a ``research_lab`` directory named ``m2_ch264`` (``m2_ch264_dryrun`` with ``--dry-run-last-days``, which derives
a short window from the newest captures, pads the rule ledger to its end-of-window size and writes a different spec_sha; it never writes the real store).

    python scripts/run_m2.py j1 --store S --snapshot-root R/snapshots --rules-root R/stream_gamma_rules --pins PINS.json
    python scripts/run_m2.py j2 --store S [--part units|followup] [--pins PINS.json]
    python scripts/run_m2.py j3 --store S [--pins PINS.json]
    python scripts/run_m2.py analysis --store S --pins PINS.json --out OUT.json [--engine-root R/signal_engine] [--m1-store S1]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import m2_analysis as an  # noqa: E402
from astrolabe.research_lab import m2_j1 as j1  # noqa: E402
from astrolabe.research_lab import m2_j2 as cl  # noqa: E402
from astrolabe.research_lab import m2_readout as ro  # noqa: E402
from astrolabe.research_lab import m2_spec as sp  # noqa: E402

TEMPFAIL = 75


def store_ok(p: Path, dry: bool) -> bool:
    r = Path(p).resolve()
    return r.name == ("m2_ch264_dryrun" if dry else "m2_ch264") and r.parent.name == "research_lab"


def dumps_bytes(root: Path) -> int:
    return sum(f.stat().st_size for f in Path(root).rglob("*") if f.is_file()) if Path(root).is_dir() else 0


def make_dry_spec(snap_root: Path, days: int) -> dict:
    caps, _ = j1.discover_captures(snap_root, 0.0, 4.1e9)
    if not caps:
        raise SystemExit("no complete captures")
    end = caps[-1]["start"] + 1.0
    return sp.dry_spec(end - days * 86400.0, end)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=("j1", "j2", "j3", "analysis"))
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--snapshot-root", type=Path)
    ap.add_argument("--rules-root", type=Path)
    ap.add_argument("--engine-root", type=Path)
    ap.add_argument("--m1-store", type=Path, help="analysis: M1's store, read at read-out for unit market ids only (m1_overlap); default <research_lab>/m1_ch263")
    ap.add_argument("--pins", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--part", choices=("units", "followup"), default=None, help="j2: the unit manifest (END_UTC + 6 h) or the follow-up manifest (READOUT_UTC)")
    ap.add_argument("--dry-run-last-days", type=int, default=None)
    ap.add_argument("--no-ledger-pad", action="store_true", help="dry run only: do not pad the rule ledger to its end-of-window size")
    ap.add_argument("--data-dumps", type=Path, default=None, help="the data-dumps directory the cap applies to (default: two levels above --store, i.e. data-dumps)")
    ap.add_argument("--data-dumps-cap-gb", type=float, default=50.0)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    a = ap.parse_args(argv)
    dry = a.dry_run_last_days is not None
    if not store_ok(a.store, dry):
        print("refuses: --store must be <...>/research_lab/m2_ch264 (m2_ch264_dryrun with --dry-run-last-days)", file=sys.stderr)
        return 2
    spec = sp.SPEC
    if dry:
        if a.job != "j1" or a.snapshot_root is None:
            print("refuses: --dry-run-last-days is for j1 with --snapshot-root", file=sys.stderr)
            return 2
        spec = make_dry_spec(a.snapshot_root, a.dry_run_last_days)
    if a.job in ("j2", "j3") and not dry and a.pins is None:
        print(f"refuses: {a.job} needs --pins on a real store", file=sys.stderr)
        return 2
    dumps = a.data_dumps if a.data_dumps is not None else a.store.resolve().parent.parent
    if dumps_bytes(dumps) > a.data_dumps_cap_gb * 2**30:
        print("not now: data-dumps exceeds --data-dumps-cap-gb", file=sys.stderr)
        return TEMPFAIL
    pins = json.loads(a.pins.read_text()) if a.pins is not None else None
    try:
        if a.job == "j1":
            if a.snapshot_root is None:
                print("refuses: j1 needs --snapshot-root", file=sys.stderr)
                return 2
            a.store.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(a.store).free < a.min_free_gb * 2**30:
                print("not now: the output disk is short of space", file=sys.stderr)
                return TEMPFAIL
            if not dry and pins is None:
                print("refuses: j1 needs --pins (the registered spec_sha / code_sha; the code is checked against them at every pass)", file=sys.stderr)
                return 2
            rules_root = a.rules_root if a.rules_root is not None else a.snapshot_root.parent / "stream_gamma_rules"
            now = time.time() if not dry else sp.ts(spec, "end_utc") + spec["missing_after_grid_s"] + 3600.0
            res = j1.run_pass(a.snapshot_root, rules_root, a.store, spec, now=now, pins=None if dry else pins, pad_ledger=sp.DRYRUN_LEDGER_PAD if dry and not a.no_ledger_pad else None)
        elif a.job == "j2":
            part = a.part or ("units" if not (a.store / "manifest.json").exists() else "followup")
            res = (cl.close_units if part == "units" else cl.close_followup)(a.store, spec, pins=pins)
        elif a.job == "j3":
            res = ro.run_j3(a.store, ro.default_get(), spec, pins=pins)
        else:
            if a.pins is None:
                print("refuses: analysis needs --pins", file=sys.stderr)
                return 2
            res = an.run_analysis(a.store, pins, a.out, spec, engine_root=a.engine_root, m1_store=a.m1_store if a.m1_store is not None else a.store.parent / "m1_ch263")
            print(res.get("ledger_line") or json.dumps({"void": res.get("void"), "void_reasons": res.get("void_reasons")}))
            nfv = res.get("no_favourite") or {}
            print(f"no_favourite: count {nfv.get('count')}, fetch coverage {nfv.get('fetch_coverage')} (beside, never in an estimand)")
            ov = res.get("m1_overlap")
            print(f"m1_overlap: {ov['count'] if isinstance(ov, dict) else ov}")
            return 0
    except sp.PinMismatch as e:
        print(json.dumps({"refuses": "pin mismatch", "record": e.record}, sort_keys=True), file=sys.stderr)
        return 3
    except (sp.M2Refusal, FileExistsError) as e:
        print(f"refuses: {e}", file=sys.stderr)
        return 2
    print(json.dumps(res, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
