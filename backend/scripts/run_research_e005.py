"""E005 runner: ``fit-dev`` (development data only) then ``score`` / ``score --status``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import e005, forecast

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["fit-dev", "score"])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--snapshot-root", type=Path, default=forecast.SNAPSHOT_ROOT)
    ap.add_argument("--dev-dir", type=Path, default=e005.DEV_DIR)
    ap.add_argument("--out-dir", type=Path, default=e005.E005_DIR)
    ap.add_argument("--registration-time", default=None, help="ISO time (testing only)")
    a = ap.parse_args(argv)
    if a.command == "fit-dev":
        fit = e005.fit_dev(a.dev_dir, a.out_dir)
        print("DEVELOPMENT FIT (not evidence)")
        print(json.dumps({k: v for k, v in fit.items() if k != "capture_counts"}, indent=1))
        return 0
    reg = datetime.fromisoformat(a.registration_time) if a.registration_time else None
    st = e005.status(a.snapshot_root, a.out_dir, reg)
    if a.status or not st["ready"]:
        print(f"E005: {st['qualifying']} of {st['required']} qualifying snapshots exist")
        if a.status:
            print(json.dumps(st, indent=1))
        return 0
    res = e005.score(a.snapshot_root, a.out_dir, reg)
    print(json.dumps(res["primary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
