"""Trade sample CLI: ``sample_trades.py --snapshot latest|<dir> [--n 2000] [--dry-run]``."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from astrolabe.research_lab import forecast, trade_sample

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", required=True, help="'latest' or a snapshot directory")
    ap.add_argument("--n", type=int, default=trade_sample.N_TOTAL)
    ap.add_argument("--frame", choices=trade_sample.FRAMES, default="eligible",
                    help="eligible (default) or active (eligible with volume24hr > 0)")
    ap.add_argument("--keep-raw", action="store_true", help="retain gzip raw response bodies")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no network, no writes")
    args = ap.parse_args()
    if args.snapshot == "latest":
        caps = forecast.list_complete_captures()
        if not caps:
            print("no complete snapshot found")
            return 1
        snap = Path(caps[-1]["dir"])
    else:
        snap = Path(args.snapshot)
    if args.dry_run:
        rows, man = forecast.load_snapshot(snap)
        plan, _ = trade_sample.build_plan(rows, man, "", "", args.n, secrets.token_hex(16),
                                          args.frame)
        print(f"{snap.name}: {plan['frame']} {plan['frame_exclusions']}")
        print(f"{snap.name}: frame={plan['frame_size']} sampled={plan['n_sampled']} "
              f"sum_pi_over_frame={plan['sum_inclusion_over_frame']:.3f} "
              "(ephemeral seed, no writes)")
        cuts = plan["cuts"]
        first = cuts.get("volume24hr_quartile_cuts", cuts.get("liquidity_quartile_cuts"))
        print("cuts:", first, cuts["spread_tercile_cuts"])
        for s in plan["strata"]:
            print(f"  {s['stratum']}: N={s['N_h']} n={s['n_h']} p={s['inclusion_prob']}")
        return 0
    m = trade_sample.run(snap, trade_sample.httpx_transport(), n_total=args.n,
                         keep_raw=args.keep_raw, frame=args.frame)
    print(f"{m['sample_id']} {m['state']} requests={m['request_count']} "
          f"statuses={m['status_counts']}")
    return 0 if m["state"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
