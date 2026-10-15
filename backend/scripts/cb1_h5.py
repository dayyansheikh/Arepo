"""CB1-F data jobs: the ``h5_cb1_ladders`` fetch, the h5 seal and the seal verifier
(docs/research_lab/CREATIVE_BATCH_1.md, CB1-F). The ``h5_cb1`` market backfill itself is
``scripts/backfill_history.py run --strata-profile cb1 ...``.

    python scripts/cb1_h5.py ladders-fetch --run-id h5_cb1_ladders --start 2024-01-01 \\
        --end 2025-05-31 --exclude-runs h1_first,h2_main,h3_power --rps 4 --disk-cap-gb 0.15 \\
        --budget-min 150
    python scripts/cb1_h5.py seal --run-id h5_cb1,h5_cb1_ladders
    python scripts/cb1_h5.py verify-seal --run-id h5_cb1,h5_cb1_ladders

``ladders-fetch`` prints one JSON line containing ``ladders_fetch_complete`` or ``probe_failed``
when finished (the queue's repeat regex); a budget stop exits 0 and a re-run resumes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from astrolabe.research_lab import h5_ladders, h5_seal
from astrolabe.research_lab import history_backfill as hb

DEFAULT_IFH2 = hb.DEFAULT_ROOT.parent / "if_h2" / "ladders.jsonl.gz"


def _day(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["ladders-fetch", "seal", "verify-seal"])
    ap.add_argument("--run-id", required=True, help="comma-separated for seal / verify-seal")
    ap.add_argument("--root", default=str(hb.DEFAULT_ROOT))
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-05-31")
    ap.add_argument("--exclude-runs", default="h1_first,h2_main,h3_power")
    ap.add_argument("--exclude-ifh2", default=str(DEFAULT_IFH2),
                    help="IF-H2 ladders.jsonl.gz (event and rung ids; exclusion only)")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--disk-cap-gb", type=float, default=0.15)
    ap.add_argument("--budget-min", type=float, default=None)
    ap.add_argument("--max-trades", type=int, default=10000)
    a = ap.parse_args(argv)
    root = Path(a.root)
    runs = [r for r in a.run_id.split(",") if r]
    if a.cmd == "ladders-fetch":
        if len(runs) != 1:
            print("ladders-fetch takes exactly one run id")
            return 2
        m = h5_ladders.ladders_fetch(
            root, runs[0], hb.httpx_transport(), start=_day(a.start), end=_day(a.end),
            exclude_runs=[r for r in a.exclude_runs.split(",") if r],
            ifh2_ladder_file=Path(a.exclude_ifh2), rps=a.rps,
            disk_cap=int(a.disk_cap_gb * 1024**3), budget_min=a.budget_min,
            max_trades=a.max_trades, live_check=hb.live_pass_or_lock)
        out = {k: m.get(k) for k in ("counts", "requests", "disk_bytes", "stopped", "probe",
                                     "n_ladders", "n_rungs", "token", "elapsed_s_this_session")}
        if m.get("token"):
            out["status"] = m["token"]
        print(json.dumps(out, default=float))
        return 0
    rc = 0
    for rid in runs:
        try:
            if a.cmd == "seal":
                seal = h5_seal.seal_run(root / rid)
                print(json.dumps({"run_id": rid, "sealed": True,
                                  "listing_sha256": seal["listing_sha256"],
                                  "n_files": seal["n_files"], "total_bytes": seal["total_bytes"]}))
            else:
                seal = h5_seal.verify_seal(root / rid)
                print(json.dumps({"run_id": rid, "verified": True,
                                  "listing_sha256": seal["listing_sha256"]}))
        except h5_seal.SealError as exc:
            print(json.dumps({"run_id": rid, "error": str(exc)}))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
