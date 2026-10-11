"""E006 runner: ``fit-dev`` (development data only), ``score`` and ``--status``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import e006, forecast, provenance

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", nargs="?", choices=["fit-dev", "score"], default="score")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--snapshot-root", type=Path, default=forecast.SNAPSHOT_ROOT)
    ap.add_argument("--dev-dir", type=Path, default=e006.DEV_DIR)
    ap.add_argument("--e005-dir", type=Path, default=e006.E005_DIR)
    ap.add_argument("--out-dir", type=Path, default=e006.E006_DIR)
    ap.add_argument("--trials-path", type=Path, default=provenance.TRIALS_PATH)
    ap.add_argument("--registration-time", default=None, help="ISO time (testing only)")
    a = ap.parse_args(argv)
    if a.command == "fit-dev" and not a.status:
        fit = e006.fit_dev(a.dev_dir, a.out_dir, a.e005_dir)
        path = a.out_dir / "dev_fit.json"
        provenance.append_trial(
            {
                "kind": "dev_fit",
                "label": "E006 dev fit (frozen before confirmation)",
                "dataset": "dev_snapshots_v2",
                "result_path": str(path),
                "results_sha256": forecast.sha256_file(path),
                "git_head": fit["provenance"]["git_head"],
                "summary": {k: fit[k] for k in ("m_L", "m_H", "m_S", "b_2", "b_4")},
            },
            a.trials_path,
        )
        print("DEVELOPMENT FIT (not evidence)")
        print(json.dumps({k: v for k, v in fit.items() if k != "capture_counts"}, indent=1))
        return 0
    reg = datetime.fromisoformat(a.registration_time) if a.registration_time else None
    st = e006.status(a.snapshot_root, a.out_dir, reg)
    if a.status or not st["ready"]:
        print(f"E006: Pending - {st['qualifying']} of {st['required']} qualifying snapshots exist")
        if a.status:
            print(json.dumps(st, indent=1))
        return 0
    res = e006.score(a.snapshot_root, a.out_dir, reg)
    print(json.dumps({h: r["verdict"] for h, r in res["hypotheses"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
