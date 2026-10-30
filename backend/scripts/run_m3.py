# ruff: noqa: E501
"""M3 (CH274, "the wait") runner: ``j0`` (counts-only pre-freeze check, the J1 extractor in dry mode) and ``j1`` (window extractor and blind follow-up recorder).
See docs/research_lab/MEASUREMENT_M3_CH274.md sections 10.1 and 10.2. Research only; no network. Refusals exit 2 (declared refusal, or an unusable argument), 1 (``j0``: the
output exists), 3 (pin mismatch, expected and actual values printed); ``j0`` and ``j1`` exit 75 when the dumps guard trips or the output disk is short of space.

    python scripts/run_m3.py j0 --snapshot-root R/snapshots --rules-root R/stream_gamma_rules --last-days 8 --lookback-slots 12 --out R/m3_ch274_j0/M3_J0.json --data-dumps-cap-gb 50
    python scripts/run_m3.py j1 --store R/m3_ch274 --snapshot-root R/snapshots --rules-root R/stream_gamma_rules --pins PINS.json
    python scripts/run_m3.py j1 --store R/m3_ch274_dryrun --snapshot-root R/snapshots --rules-root R/stream_gamma_rules --dry-run-last-days 3

The J1 store must sit in a ``research_lab`` directory named ``m3_ch274`` (``m3_ch274_dryrun`` with ``--dry-run-last-days``, which derives a short window from the newest
captures, pads the state to its end-of-window size and writes a different spec_sha; it never writes the real store). ``j0`` writes only ``--out`` (write-once, under a
``research_lab`` directory). J2, J3 and the analysis are not in this file yet.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import boundary_map_ch240 as c240  # noqa: E402
from astrolabe.research_lab import m3_j1 as j1  # noqa: E402
from astrolabe.research_lab import m3_spec as sp  # noqa: E402

TEMPFAIL = 75
DUMPS = Path(__file__).resolve().parents[2] / ("data" + "-dumps")


def _du_bytes(p: Path) -> int:
    tot = 0
    for dp, _dn, fn in os.walk(p):
        for f in fn:
            try:
                tot += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return tot


def store_ok(p: Path, dry: bool) -> bool:
    r = Path(p).resolve()
    return r.name == ("m3_ch274_dryrun" if dry else "m3_ch274") and r.parent.name == "research_lab"


def root_ok(p: Path | None, name: str) -> bool:
    if p is None:
        return True
    r = Path(p).resolve()
    return r.name == name and r.parent.name == "research_lab"


def out_ok(p: Path) -> bool:
    return "research_lab" in Path(p).resolve().parts


def guards(out_probe: Path, cap_gb: float | None, min_free_gb: float) -> int | None:
    """None when the run may go ahead; ``TEMPFAIL`` when the bulk directory is above the cap or the output disk is short of space."""
    if cap_gb is not None and DUMPS.exists() and _du_bytes(DUMPS) > cap_gb * 2**30:
        print(f"bulk directory above {cap_gb} GiB: not now", file=sys.stderr)
        return TEMPFAIL
    probe = out_probe
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if shutil.disk_usage(probe).free < min_free_gb * 2**30:
        print(f"less than {min_free_gb} GiB free at the output: not now", file=sys.stderr)
        return TEMPFAIL
    return None


def newest_end(snap_root: Path) -> float:
    caps, _ = j1.discover_captures(snap_root, 0.0, 4.1e9)
    if not caps:
        raise SystemExit("no complete captures found")
    return caps[-1]["start"] + 1.0


def run_j0_cmd(a) -> int:
    if not (root_ok(a.snapshot_root, "snapshots") and root_ok(a.rules_root, "stream_gamma_rules") and out_ok(a.out)):
        print("refuses: roots must be research_lab/snapshots and (optional) research_lab/stream_gamma_rules, and --out must lie under a research_lab directory", file=sys.stderr)
        return 2
    missing = [str(r) for r in (a.snapshot_root, a.rules_root) if r is not None and not Path(r).is_dir()]
    if missing:
        print(f"refuses: root(s) missing: {missing}", file=sys.stderr)
        return 2
    if a.out.exists():
        print(f"refuses to overwrite {a.out}", file=sys.stderr)
        return 1
    g = guards(a.out.parent, a.data_dumps_cap_gb, a.min_free_gb)
    if g is not None:
        return g
    if a.last_days:
        end = newest_end(a.snapshot_root)
        start, mode = end - a.last_days * 86400.0, f"last_days={a.last_days}"
    elif a.start_utc and a.end_utc:
        start, end, mode = c240.parse_utc(a.start_utc), c240.parse_utc(a.end_utc), "explicit"
    else:
        print("refuses: give --start-utc and --end-utc, or --last-days", file=sys.stderr)
        return 2
    sp.check_pins(sp.SPEC)  # the imported readers and the lexicon must match the spec's pins (the design text is a draft: recorded, not pinned)
    res = j1.run_j0(a.snapshot_root, a.rules_root, start, end, lookback_slots=a.lookback_slots)
    res["span"]["mode"] = mode
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, sort_keys=True, indent=1, default=str))
    try:
        os.link(tmp, a.out)  # write-once
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote {a.out} units={res['eligible_units']['total']} captures={res['span']['classified_captures']} peak_rss_mb={res['peak_rss_mb']} rule_a_extend_to_42_days={res['decisions']['rule_a_extend_to_42_days']}")
    return 0


def run_j1_cmd(a) -> int:
    dry = a.dry_run_last_days is not None
    if not store_ok(a.store, dry):
        print("refuses: --store must be <...>/research_lab/m3_ch274 (m3_ch274_dryrun with --dry-run-last-days)", file=sys.stderr)
        return 2
    if a.snapshot_root is None:
        print("refuses: j1 needs --snapshot-root", file=sys.stderr)
        return 2
    spec = sp.SPEC
    if dry:
        end = newest_end(a.snapshot_root)
        spec = sp.dry_spec(end - a.dry_run_last_days * 86400.0, end)
    pins = json.loads(a.pins.read_text()) if a.pins is not None else None
    if not dry and pins is None:
        print("refuses: j1 needs --pins (the registered spec_sha / code_sha; the code is checked against them at every pass)", file=sys.stderr)
        return 2
    a.store.mkdir(parents=True, exist_ok=True)
    g = guards(a.store, a.data_dumps_cap_gb, a.min_free_gb)
    if g is not None:
        return g
    rules_root = a.rules_root if a.rules_root is not None else a.snapshot_root.parent / "stream_gamma_rules"
    now = j1.time.time() if not dry else sp.ts(spec, "end_utc") + spec["missing_after_grid_s"] + 3600.0  # a dry run simulates window time so that every slot is decidable
    pad = (sp.DRYRUN_LEDGER_PAD, sp.DRYRUN_SET_PAD) if dry and not a.no_pad else None
    try:
        res = j1.run_pass(a.snapshot_root, rules_root, a.store, spec, now=now, pins=None if dry else pins, pad=pad)
    except sp.PinMismatch as e:
        print(json.dumps({"refuses": "pin mismatch", "record": e.record}, sort_keys=True), file=sys.stderr)
        return 3
    except (sp.M3Refusal, FileExistsError) as e:
        print(f"refuses: {e}", file=sys.stderr)
        return 2
    print(json.dumps(res, sort_keys=True, default=str))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=("j0", "j1"))
    ap.add_argument("--store", type=Path)
    ap.add_argument("--snapshot-root", type=Path)
    ap.add_argument("--rules-root", type=Path)
    ap.add_argument("--pins", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--start-utc")
    ap.add_argument("--end-utc")
    ap.add_argument("--last-days", type=int, default=None, help="j0: the span, counted back from the newest complete capture")
    ap.add_argument("--lookback-slots", type=int, default=sp.SPEC["j0"]["fold_captures"], help="j0: captures that only fold before the first classified k (J0's one-day fold, fixed in 10.1)")
    ap.add_argument("--dry-run-last-days", type=int, default=None, help="j1: derive a short window from the newest captures (store m3_ch274_dryrun)")
    ap.add_argument("--no-pad", action="store_true", help="j1 dry run only: do not pad the state to its end-of-window size")
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None)
    ap.add_argument("--min-free-gb", type=float, default=1.0)
    a = ap.parse_args(argv)
    try:
        if a.job == "j0":
            if a.snapshot_root is None or a.out is None:
                print("refuses: j0 needs --snapshot-root and --out", file=sys.stderr)
                return 2
            return run_j0_cmd(a)
        if a.store is None:
            print("refuses: j1 needs --store", file=sys.stderr)
            return 2
        return run_j1_cmd(a)
    except sp.PinMismatch as e:
        print(json.dumps({"refuses": "pin mismatch", "record": e.record}, sort_keys=True), file=sys.stderr)
        return 3
    except sp.M3Refusal as e:
        print(f"refuses: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
