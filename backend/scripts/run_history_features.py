# ruff: noqa: E501
"""Historical feature extraction from free sources (research lab, exploratory_historical).

  python scripts/run_history_features.py books   --budget-min 75
  python scripts/run_history_features.py wallets --budget-min 60 --max-wallets 20000
  python scripts/run_history_features.py finalize

Heavy steps wait for the live collector (arepo_pass.sh) and for swap headroom. One step at a time.
Inputs: data-dumps/research_lab/history/<run>/{panel_H6h.csv.gz, frame.csv.gz, trades/}.
Outputs: data-dumps/research_lab/history_sources/{book_features,new_wallets}/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from astrolabe.research_lab import history_sources as hs

HIST = hs.forecast.ROOT / "data-dumps" / "research_lab" / "history"
RUNS = ("h1_first", "h2_main")


def runs_with(name: str) -> list[Path]:
    return [HIST / r / name for r in RUNS if (HIST / r / name).exists()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["books", "wallets", "finalize"])
    ap.add_argument("--budget-min", type=float, default=75)
    ap.add_argument("--max-wallets", type=int, default=20000)
    a = ap.parse_args()
    if a.step in ("books", "finalize"):
        out = hs.ROOT / "book_features"
        if a.step == "books":
            pairs = hs.panel_pairs(runs_with("panel_H6h.csv.gz"))
            tokens = hs.load_frame_tokens(runs_with("frame.csv.gz"))
            run = hs.BookFeatureRun(out, pairs, tokens, gate=hs.heavy_gate)
            hs.heavy_gate()
            print(json.dumps(run.run(a.budget_min * 60)), flush=True)
        print(hs.finalize_book_features(out))
    else:
        hs.run_wallet_step(HIST, RUNS, hs.ROOT / "new_wallets", a.budget_min * 60, a.max_wallets)


if __name__ == "__main__":
    main()
