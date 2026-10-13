"""Post-pass scorer for the frozen ungated surprise-move detector on complete-universe snapshots.

``score`` (default): bootstrap the rolling mid series from the captures on disk if needed, score the
newest complete capture (stage 1 + bounded stage-2 fetch), write ``alerts.jsonl`` (alerts + matched
controls) before any outcome, then write due outcomes. ``outcomes``: outcomes only. ``analyze``:
the single registered analysis (E011) after the end date. Research only; never trades.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import forecast  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import surprise_snapshot as ss  # noqa: E402

log = logging.getLogger("surprise_snapshot")


def bootstrap_series(scorer: ss.Scorer, caps: list[dict]) -> int:
    """Fill the rolling mid series from captures on disk that it does not yet hold."""
    have = set(scorer.series.captures().tolist())
    n = 0
    for c in caps:
        t = float(ss._epoch(c["started_utc"]))
        if t in have or t < scorer.clock() - ss.SERIES_KEEP_S:
            continue
        rows, _ = ss.load_capture(Path(c["dir"]))
        scorer.series.add(ss.eligible(rows, scorer.cfg))
        n += 1
    if n:
        scorer.series.save()
    return n


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="score", choices=["score", "outcomes", "analyze"])
    ap.add_argument("--capture", default="latest")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--no-outcomes", action="store_true")
    ap.add_argument("--start", default=ss.REGISTERED_UTC)
    ap.add_argument("--end", default=ss.END_UTC)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    lim = hb.Limiter(hb.httpx_transport(), rps=min(args.rps, 5.0))
    if args.cmd == "analyze":
        print(json.dumps(ss.analyze(start_utc=args.start, end_utc=args.end), indent=1))
        return
    scorer = ss.Scorer(lim)
    if args.cmd == "score":
        caps = forecast.list_complete_captures()
        if not caps:
            print("no complete capture")
            return
        cap = caps[-1] if args.capture == "latest" else next(
            c for c in caps if c["capture_id"] == args.capture)
        n_boot = bootstrap_series(scorer, caps)
        stats = scorer.run_pass(Path(cap["dir"]))
        stats["series_bootstrapped_captures"] = n_boot
        print(json.dumps(stats, default=str))
        if args.no_outcomes:
            return
    print(json.dumps({"outcomes": ss.write_outcomes(lim)}))


if __name__ == "__main__":
    main()
