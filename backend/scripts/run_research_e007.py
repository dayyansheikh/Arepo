"""E007 runner: ``fit-dev`` (development data only), ``score`` and ``--status``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import e007, forecast, provenance

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", nargs="?", choices=["fit-dev", "score"], default="score")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--sample-root", type=Path, default=e007.SAMPLE_ROOT)
    ap.add_argument("--snapshot-root", type=Path, default=e007.SNAPSHOT_ROOT)
    ap.add_argument("--out-dir", type=Path, default=e007.E007_DIR)
    ap.add_argument("--ledger", type=Path, default=e007.LEDGER_PATH)
    ap.add_argument("--trials-path", type=Path, default=provenance.TRIALS_PATH)
    a = ap.parse_args(argv)
    if a.command == "fit-dev" and not a.status:
        fit = e007.fit_dev(a.sample_root, a.snapshot_root, a.out_dir)
        path = a.out_dir / "dev_fit.json"
        sha = forecast.sha256_file(path)
        with open(a.ledger, "a", encoding="utf-8") as fh:
            fh.write("\n" + e007.ledger_line(fit, sha) + "\n")
        provenance.append_trial(
            {
                "kind": "dev_fit",
                "label": "E007 dev fit (frozen before confirmation)",
                "dataset": "trade_samples+snapshots",
                "result_path": str(path),
                "results_sha256": sha,
                "git_head": fit["provenance"]["git_head"],
                "summary": {"base": fit["base"], "augmented": fit["augmented"],
                            "n_total": fit["n_total"]},
            },
            a.trials_path,
        )
        print("DEVELOPMENT FIT (not evidence)")
        print(json.dumps({k: fit[k] for k in ("base", "augmented", "n_total", "per_period",
                                              "nonzero_signed_share_total",
                                              "excluded_dev_samples")}, indent=1))
        print(f"dev_fit.json sha256: {sha}")
        return 0
    st = e007.status(a.sample_root, a.snapshot_root, a.out_dir)
    if a.status:
        print(f"E007: Pending - {st['qualifying']} of {st['required']} qualifying periods")
        print(json.dumps(st, indent=1, default=str))
        return 0
    res = e007.score(a.sample_root, a.snapshot_root, a.out_dir, ledger_path=a.ledger)
    if res is None:
        print(f"E007: Pending - {st['qualifying']} of {st['required']} qualifying periods")
        return 0
    print(json.dumps({"verdict": res["verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
