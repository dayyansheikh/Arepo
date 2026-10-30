# ruff: noqa: E501
"""M1 (CH263) runner: ``j1`` (window extractor), ``j2`` (window close), ``j3`` (read-out fetch), ``analysis``.
See docs/research_lab/MEASUREMENT_M1_CH263.md section 9. Research only. Refusals exit 2 (declared refusal) or 3 (pin mismatch, values printed);
``j1`` exits 75 when the dumps guard trips. The store must sit in a ``research_lab`` directory named ``m1_ch263`` (``m1_ch263_dryrun`` with
``--dry-run-last-days``, which derives a short window from the newest captures and writes a different spec_sha; it never writes the real store).

    python scripts/run_m1.py j1 --store S --snapshot-root R/snapshots --sweep-root R/book_sweeps
    python scripts/run_m1.py j2 --store S
    python scripts/run_m1.py j3 --store S
    python scripts/run_m1.py analysis --store S --pins PINS.json --out OUT.json [--engine-root R/signal_engine]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import m1_analysis as an  # noqa: E402
from astrolabe.research_lab import m1_extract as ex  # noqa: E402
from astrolabe.research_lab import m1_readout as ro  # noqa: E402
from astrolabe.research_lab import m1_spec as sp  # noqa: E402

TEMPFAIL = 75


def store_ok(p: Path, dry: bool) -> bool:
    r = Path(p).resolve()
    return r.name == ("m1_ch263_dryrun" if dry else "m1_ch263") and r.parent.name == "research_lab"


def dry_spec(snap_root: Path, days: int) -> dict:
    caps = ex.list_complete(snap_root)
    if not caps:
        raise SystemExit("no complete captures")
    end = caps[-1]["start"] + 1.0
    spec = copy.deepcopy(sp.SPEC)
    spec["registered_utc"] = sp.iso(end - days * 86400.0)
    spec["end_utc"] = sp.iso(end)
    spec["measurement"] = "M1_CH263_DRYRUN"
    return spec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=("j1", "j2", "j3", "analysis"))
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--snapshot-root", type=Path)
    ap.add_argument("--sweep-root", type=Path)
    ap.add_argument("--engine-root", type=Path)
    ap.add_argument("--pins", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dry-run-last-days", type=int, default=None)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=50.0)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    a = ap.parse_args(argv)
    dry = a.dry_run_last_days is not None
    if not store_ok(a.store, dry):
        print("refuses: --store must be <...>/research_lab/m1_ch263 (m1_ch263_dryrun with --dry-run-last-days)", file=sys.stderr)
        return 2
    spec = sp.SPEC
    if dry:
        if a.job != "j1" or a.snapshot_root is None:
            print("refuses: --dry-run-last-days is for j1 with --snapshot-root", file=sys.stderr)
            return 2
        spec = dry_spec(a.snapshot_root, a.dry_run_last_days)
    try:
        if a.job == "j1":
            if a.snapshot_root is None:
                print("refuses: j1 needs --snapshot-root", file=sys.stderr)
                return 2
            a.store.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(a.store).free < a.min_free_gb * 2**30:
                print("not now: the output disk is short of space", file=sys.stderr)
                return TEMPFAIL
            now = ex.time.time() if not dry else spec_now(spec)
            res = ex.run_pass(a.store, a.snapshot_root, a.sweep_root, spec, now=now)
        elif a.job == "j2":
            res = ex.close_window(a.store, spec)
        elif a.job == "j3":
            res = ro.run_j3(a.store, ro.default_get(), spec)
        else:
            if a.pins is None:
                print("refuses: analysis needs --pins", file=sys.stderr)
                return 2
            res = an.run_analysis(a.store, json.loads(a.pins.read_text()), a.out, spec, engine_root=a.engine_root)
            print(res.get("ledger_line") or json.dumps({"void": res.get("void"), "void_reasons": res.get("void_reasons")}))
            ad = res.get("ask_f_at_1") or {}
            print(f"ask_f_at_1: {ad.get('units')} units, share {ad.get('share')} (beside theta)")
            return 0
    except sp.PinMismatch as e:
        print(json.dumps({"refuses": "pin mismatch", "record": e.record}, sort_keys=True), file=sys.stderr)
        return 3
    except ex.M1Refusal as e:
        print(f"refuses: {e}", file=sys.stderr)
        return 2
    print(json.dumps(res, sort_keys=True, default=str))
    return 0


def spec_now(spec: dict) -> float:
    return sp.ts(spec, "end_utc") + spec["missing_after_grid_s"] + 3600.0


if __name__ == "__main__":
    sys.exit(main())
