# ruff: noqa: E501
"""CB3 post-window trade follow-up (docs/research_lab/CREATIVE_BATCH_3.md §4.3.2). Data-only; NOT wired into arepo_pass.sh yet.

    python scripts/sample_trades_followup.py --snapshot latest --frac 0.5 --vacuum-max 300 --rps 4 --budget-s 540

Reads the previous pass's trade sample (never modifies it), fetches the post windows with windowed /trades paging and writes only
under data-dumps/research_lab/cb3_followup/<capture_id>/. Exit 0 on any network trouble (the pass must never fail); exit 1 only when
data-dumps is over the cap.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import cb3_followup as f
    from astrolabe.research_lab import trade_sample

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", default="latest", help="only 'latest' is supported")
    ap.add_argument("--frac", type=float, default=f.DEFAULT_FRAC)
    ap.add_argument("--vacuum-max", type=int, default=f.DEFAULT_VACUUM_MAX)
    ap.add_argument("--rps", type=float, default=f.DEFAULT_RPS)
    ap.add_argument("--budget-s", type=float, default=f.DEFAULT_BUDGET_S)
    ap.add_argument("--seed", default=None, help="test only; default: a fresh random seed, recorded in plan.json")
    ap.add_argument("--data-dumps-max-gb", type=float, default=None)
    ap.add_argument("--root", type=Path, default=f.FOLLOWUP_ROOT)
    a = ap.parse_args(argv)
    if a.snapshot != "latest":
        print("only --snapshot latest is supported", file=sys.stderr)
        return 1
    try:
        res = f.run(transport=trade_sample.httpx_transport(), out_root=a.root, frac=a.frac, vacuum_max=a.vacuum_max, rps=a.rps,
                    budget_s=a.budget_s, seed=a.seed, data_dumps=f.DATA_DUMPS, data_dumps_max_gb=a.data_dumps_max_gb)
    except Exception as exc:  # never fail the pass
        print(json.dumps({"cb3_followup": f.VERSION, "error": type(exc).__name__}))
        return 0
    print(json.dumps(res, sort_keys=True, default=str))
    return 1 if res.get("stopped") == "refused_data_dumps_over_cap" else 0


if __name__ == "__main__":
    sys.exit(main())
