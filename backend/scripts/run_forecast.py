"""E002 forecasting CLI: ``predict --snapshot <dir|latest>`` and ``score-e002``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import forecast  # noqa: E402


def cmd_predict(args: argparse.Namespace) -> int:
    if args.snapshot == "latest":
        caps = forecast.list_complete_captures()
        if not caps:
            print("no complete snapshot found")
            return 1
        snap = Path(caps[-1]["dir"])
    else:
        snap = Path(args.snapshot)
    out, man = forecast.predict(snap)
    d = out["dmid_hat"].describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99])
    print(f"snapshot {man['snapshot_capture_id']}: {man['n_forecasts']} forecasts logged")
    print(d.to_string())
    print(f"share dmid_hat == 0: {(out['dmid_hat'] == 0).mean():.3f}")
    return 0


def cmd_score(_: argparse.Namespace) -> int:
    pair = forecast.select_e002_pair(
        forecast.list_complete_captures(), forecast.registration_time()
    )
    if pair is None:
        print("E002: no qualifying pair yet (need two complete captures after the registration "
              f"commit, >= {forecast.MIN_GAP_H}h apart). Nothing scored.")
        return 2
    out_path = forecast.E002_DIR / "results.json"
    if out_path.exists():
        print(f"first-period E002 result already exists, not overwritten: {out_path}")
        return 1
    res = forecast.score(Path(pair[0]["dir"]), Path(pair[1]["dir"]))
    forecast.E002_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x") as fh:
        json.dump(res, fh, indent=1)
    p, c = res["primary"], res["counts"]
    print(f"captures {res['captures']['origin']} -> {res['captures']['target']} "
          f"(gap {res['captures']['gap_h']:.2f}h)")
    print(f"eligible {c['eligible']}, available {c['target_available']}, "
          f"markets {c['markets']}, events {c['events']}")
    print(f"R2_oos {p['r2_oos']:+.4f} CI {p['r2_ci']}; slope {p['slope_through_origin']:+.4f} "
          f"CI {p['slope_ci']}")
    print(f"VERDICT: {p['verdict']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("predict")
    sp.add_argument("--snapshot", required=True)
    sp.set_defaults(fn=cmd_predict)
    ss = sub.add_parser("score-e002")
    ss.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
