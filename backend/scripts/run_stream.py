# ruff: noqa: E501
"""One poll of a prospective public-data stream (docs/research_lab/NEW_STREAMS_2026-10-19.md). Read-only; never trades.

  python scripts/run_stream.py predictit                 PredictIt all markets (1-minute slot)
  python scripts/run_stream.py smarkets                  Smarkets politics + current affairs (5-minute slot)
  python scripts/run_stream.py espn_odds                 ESPN-published sportsbook lines (10-minute slot)
  python scripts/run_stream.py gamma_rules [--top N]     Polymarket rule text (hourly; full frame at 00/06/12/18Z)

Writes ``<data-dumps>/research_lab/stream_<name>/YYYYMMDD.jsonl`` (change-only, receipt-timed, append + fsync).
Idempotent per slot (a second call in the same slot does nothing). Exit 0 = committed / nothing to do / busy;
75 = headroom refusal (free disk < --free-min-gb, data-dumps > --data-dumps-cap-gb, or the stream's own cap),
nothing written; 1 = the poll failed (an ``ok: false`` poll line records the gap). One JSON line on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab.streams import (  # noqa: E402
    common,
    espn_odds,
    gamma_rules,
    predictit,
    smarkets,
)

SPECS = {s.name: s for s in (predictit.SPEC, smarkets.SPEC, espn_odds.SPEC, gamma_rules.SPEC)}
DEFAULT_DATA_DUMPS = Path(__file__).resolve().parents[2] / "data-dumps"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stream", choices=sorted(SPECS))
    ap.add_argument("--data-dumps", type=Path, default=DEFAULT_DATA_DUMPS)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=40.0)
    ap.add_argument("--free-min-gb", type=float, default=4.0)
    ap.add_argument("--stream-cap-gb", type=float, default=None)
    ap.add_argument("--rps", type=float, default=None, help="override the stream's polite default")
    ap.add_argument("--budget-s", type=float, default=None)
    ap.add_argument("--top", type=int, default=None, help="gamma_rules: frame head on non-full hours")
    ap.add_argument("--full", choices=["auto", "yes", "no"], default="auto", help="gamma_rules: full frame")
    ap.add_argument("--snapshots", type=Path, default=None,
                    help="gamma_rules: snapshot root for the frame (default <data-dumps>/research_lab/snapshots; read only)")
    a = ap.parse_args(argv)
    spec = SPECS[a.stream]
    kw: dict = {}
    if a.stream == "gamma_rules":
        kw["full"] = {"auto": None, "yes": True, "no": False}[a.full]
        if a.top is not None:
            kw["top"] = a.top
        if a.snapshots is not None:
            kw["snapshots"] = a.snapshots
    code, summary = common.run_stream(spec, a.data_dumps, cap_gb=a.data_dumps_cap_gb, free_min_gb=a.free_min_gb,
                                      stream_cap_gb=a.stream_cap_gb, rps=a.rps, budget_s=a.budget_s,
                                      poll_kwargs=kw)
    print(json.dumps({"t": common.utc_iso(time.time()), "exit": code, **summary},
                     sort_keys=True, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
