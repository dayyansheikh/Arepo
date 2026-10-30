# ruff: noqa: E501
"""Serial M1 + M2 + M3 host dry-run pass against the 2 h slot (MEASUREMENT_M3_CH274.md 10 and 20 step 8). Research only; no network.

Runs the three J1 DRY runs one after another (never concurrently), each as its own process on its own FRESH dry-run store, and writes the wall time, exit code and the last stdout
line (which carries the peak RSS) of each to a write-once JSON file. Every child is started with ``--dry-run-last-days``, which makes M1's, M2's and M3's runners refuse their real
stores, so this script cannot touch a registered store; it additionally refuses a ``--base`` that is not a directory named ``serial_dryrun`` under ``research_lab``. M3 is also given
``--dry-run-end-utc`` so that its second, steady-state pass can be timed on the same store. The M1 and M2 code is run, not edited.

    python scripts/serial_dryrun_m123.py --base R/m_serial_dryruns/q0782/research_lab/serial_dryrun --snapshot-root R/snapshots --rules-root R/stream_gamma_rules \
        --sweep-root R/book_sweeps --dumps-root R --out R/m_serial_dryruns/q0782/research_lab/SERIAL_TIMING.json [--print-plan]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from astrolabe.research_lab import m3_j1 as j1  # noqa: E402


def base_ok(p: Path) -> bool:
    r = Path(p).resolve()
    return r.name == "serial_dryrun" and r.parent.name == "research_lab"


def plan(a, end_utc: str | None) -> list[dict]:
    snap, rules = str(a.snapshot_root), str(a.rules_root)
    days = str(a.dry_run_last_days)
    s = Path(a.base)

    def st(name: str) -> str:
        return str(s / "research_lab" / name)

    m1 = [sys.executable, str(HERE / "run_m1.py"), "j1", "--store", st("m1_ch263_dryrun"), "--snapshot-root", snap, "--sweep-root", str(a.sweep_root), "--dry-run-last-days", days]
    m2 = [sys.executable, str(HERE / "run_m2.py"), "j1", "--store", st("m2_ch264_dryrun"), "--snapshot-root", snap, "--rules-root", rules, "--dry-run-last-days", days,
          "--data-dumps", str(a.dumps_root)]
    m3 = [sys.executable, str(HERE / "run_m3.py"), "j1", "--store", st("m3_ch274_dryrun"), "--snapshot-root", snap, "--rules-root", rules, "--dry-run-last-days", days,
          "--dry-run-end-utc", end_utc or "<newest capture + 1 s>"]
    return [{"name": "m1_catch_up", "argv": m1}, {"name": "m2_catch_up", "argv": m2}, {"name": "m3_catch_up", "argv": m3}, {"name": "m3_steady_state", "argv": m3}]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--snapshot-root", type=Path, required=True)
    ap.add_argument("--rules-root", type=Path, required=True)
    ap.add_argument("--sweep-root", type=Path, required=True)
    ap.add_argument("--dumps-root", type=Path, required=True, help="passed to run_m2.py as its bulk-directory argument")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run-last-days", type=int, default=3)
    ap.add_argument("--print-plan", action="store_true")
    a = ap.parse_args(argv)
    if not base_ok(a.base) or "research_lab" not in a.out.resolve().parts:
        print("refuses: --base must be <...>/research_lab/serial_dryrun and --out must lie under a research_lab directory", file=sys.stderr)
        return 2
    if a.out.exists() and not a.print_plan:
        print(f"refuses to overwrite {a.out}", file=sys.stderr)
        return 1
    caps, _ = j1.discover_captures(a.snapshot_root, 0.0, 4.1e9)
    end_utc = j1.iso(caps[-1]["start"] + 1.0) if caps else None
    steps = plan(a, end_utc)
    if a.print_plan:
        print(json.dumps(steps, indent=1))
        return 0
    if end_utc is None:
        print("refuses: no complete captures", file=sys.stderr)
        return 2
    rows = []
    t_all = time.perf_counter()
    for step in steps:  # strictly serial: one process at a time
        t0 = time.perf_counter()
        r = subprocess.run(step["argv"], capture_output=True, text=True, cwd=str(HERE.parent))
        tail = (r.stdout.strip().splitlines() or [""])[-1][:4000]
        rows.append({"name": step["name"], "rc": r.returncode, "wall_s": round(time.perf_counter() - t0, 2), "last_stdout_line": tail, "stderr_tail": r.stderr.strip()[-800:]})
        if r.returncode != 0:
            break
    doc = {"kind": "serial M1+M2+M3 J1 dry runs (never the real stores)", "dry_run_last_days": a.dry_run_last_days, "dry_run_end_utc_m3": end_utc, "steps": rows,
           "serial_catch_up_wall_s": round(sum(x["wall_s"] for x in rows if x["name"].endswith("catch_up")), 2),
           "note": "M1 and M2 per-pass steady-state time is not measured here (their dry spec follows the newest capture, so a second pass is refused); m3_steady_state is M3's second pass on the same store",
           "total_wall_s": round(time.perf_counter() - t_all, 2)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, sort_keys=True, indent=1))
    try:
        os.link(tmp, a.out)  # write-once
    finally:
        tmp.unlink(missing_ok=True)
    print(json.dumps(doc, sort_keys=True)[:4000])
    return 0 if all(x["rc"] == 0 for x in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
