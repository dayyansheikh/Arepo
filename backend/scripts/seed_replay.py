#!/usr/bin/env python
"""Generate the deterministic replay dataset committed to the repository.

Reproducible (fixed seed). Produces a small, realistic scenario across a few markets, one of
which contains a *planted* anomaly (a sharp repricing accompanied by a volume spike and a
book-imbalance shift) so the Signal Lab and backtest have genuine content to show. The output
is a single small JSON file that the deterministic replay player and backtest consume.

Run:  python scripts/seed_replay.py
Output: astrolabe/replay/dataset/scenario.json
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

SEED = 42
STEP_SECONDS = 60
N_FRAMES = 48
# Anchor time is FIXED (not "now") so the dataset is byte-stable across regenerations.
ANCHOR = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
OUT = Path(__file__).resolve().parent.parent / "astrolabe" / "replay" / "dataset" / "scenario.json"


def _book_from_mid(mid: float, tick: float, rng: np.random.Generator, depth_scale: float,
                   imbalance: float = 0.0) -> dict:
    """Build a plausible two-sided book around a midpoint.

    ``imbalance`` in [-1, 1] skews resting size toward bids (positive) or asks (negative).
    """
    mid = float(np.clip(mid, 0.02, 0.98))
    half = max(tick, tick * 2)
    best_bid = round(mid - half, 3)
    best_ask = round(mid + half, 3)
    bids, asks = [], []
    bid_mult = 1.0 + max(0.0, imbalance)
    ask_mult = 1.0 + max(0.0, -imbalance)
    for i in range(5):
        bp = round(max(0.001, best_bid - i * tick), 3)
        ap = round(min(0.999, best_ask + i * tick), 3)
        bs = round(depth_scale * bid_mult * float(rng.uniform(0.6, 1.4)) * (1.0 - 0.12 * i), 2)
        as_ = round(depth_scale * ask_mult * float(rng.uniform(0.6, 1.4)) * (1.0 - 0.12 * i), 2)
        bids.append([bp, max(1.0, bs)])
        asks.append([ap, max(1.0, as_)])
    return {"bids": bids, "asks": asks}


def _episode_overrides(episodes: list[dict]) -> dict[int, dict]:
    """Expand episode specs into per-frame overrides {frame: {step, imbalance, vol_mult}}.

    Supported episode ``kind``s:
    - "momentum": a sustained directional run (jump followed by continued drift the same way)
      that a follow-through backtest should partly reward.
    - "spike_revert": a sharp jump that then reverts — a signal that should mostly fail
      follow-through (a realistic false positive).
    """
    ov: dict[int, dict] = {}
    for ep in episodes:
        start, length, kind = ep["start"], ep["length"], ep["kind"]
        mag = ep["magnitude"]
        for j in range(length):
            f = start + j
            if kind == "momentum":
                # Big first step, then smaller continuation steps the same direction.
                step = mag if j == 0 else mag * 0.35
                ov[f] = {"step": step, "imbalance": 0.7, "vol_mult": 3.0 if j == 0 else 1.8}
            elif kind == "spike_revert":
                if j == 0:
                    ov[f] = {"step": mag, "imbalance": 0.75, "vol_mult": 3.2}
                else:
                    ov[f] = {"step": -mag * 0.45, "imbalance": -0.3, "vol_mult": 1.4}
    return ov


def _market(rng: np.random.Generator, *, mid_id: str, question: str, slug: str,
            category: str, tags: list[str], start_mid: float, drift: float,
            vol: float, depth: float, episodes: list[dict] | None = None) -> dict:
    tick = 0.001
    yes_token = f"{mid_id}01"
    no_token = f"{mid_id}02"
    frames = []
    mid = start_mid
    base_volume = float(rng.uniform(50_000, 500_000))
    overrides = _episode_overrides(episodes or [])
    for k in range(N_FRAMES):
        t = int(ANCHOR.timestamp()) + k * STEP_SECONDS
        step = drift + float(rng.normal(0.0, vol))
        imbalance = float(np.clip(rng.normal(0.0, 0.12), -0.5, 0.5))
        vol_bump = 0.0
        ov = overrides.get(k)
        if ov is not None:
            step += ov["step"]
            imbalance = ov["imbalance"]
            vol_bump = base_volume * (ov["vol_mult"] - 1.0)
        mid = float(np.clip(mid + step, 0.03, 0.97))
        yes_book = _book_from_mid(mid, tick, rng, depth, imbalance)
        no_book = _book_from_mid(1.0 - mid, tick, rng, depth, -imbalance)
        vnow = round(base_volume * (1.0 + 0.02 * k) + vol_bump, 2)
        frames.append({
            "t": t,
            "tokens": {
                yes_token: {**yes_book, "last_trade_price": round(mid, 3), "volume": vnow},
                no_token: {**no_book, "last_trade_price": round(1.0 - mid, 3), "volume": vnow},
            },
        })
    return {
        "id": mid_id,
        "question": question,
        "slug": slug,
        "condition_id": f"0x{mid_id}deadbeef",
        "category": category,
        "tags": tags,
        "tick_size": tick,
        "outcomes": [
            {"name": "Yes", "token_id": yes_token},
            {"name": "No", "token_id": no_token},
        ],
        "frames": frames,
    }


def build() -> dict:
    rng = np.random.default_rng(SEED)
    markets = [
        # Momentum episode (frame 18, ~5-frame run): sharp move that keeps going one way.
        _market(rng, mid_id="90001", question="Will Team Aurora win the championship?",
                slug="aurora-championship", category="Sports", tags=["Sports", "Basketball"],
                start_mid=0.42, drift=0.0008, vol=0.005, depth=800,
                episodes=[{"start": 18, "length": 5, "kind": "momentum", "magnitude": 0.06}]),
        # Spike-and-revert (frame 25, 4-frame): sharp jump that then unwinds.
        _market(rng, mid_id="90002", question="Will the reference rate be cut at the next meeting?",
                slug="rate-cut-next-meeting", category="Economics", tags=["Economics", "Rates"],
                start_mid=0.63, drift=-0.0004, vol=0.004, depth=1500,
                episodes=[{"start": 25, "length": 4, "kind": "spike_revert", "magnitude": 0.07}]),
        # Two smaller episodes: an early momentum run and a later spike-revert.
        _market(rng, mid_id="90003",
                question="Will Candidate X lead the national poll on election eve?",
                slug="candidate-x-poll-lead", category="Politics", tags=["Politics", "Elections"],
                start_mid=0.51, drift=0.0, vol=0.006, depth=400,
                episodes=[{"start": 14, "length": 4, "kind": "momentum", "magnitude": 0.05},
                          {"start": 34, "length": 3, "kind": "spike_revert", "magnitude": 0.06}]),
    ]
    return {
        "meta": {
            "generated_anchor": ANCHOR.isoformat(),
            "seed": SEED,
            "step_seconds": STEP_SECONDS,
            "n_frames": N_FRAMES,
            "description": (
                "Deterministic demo scenario for Astrolabe replay/backtest. Fictional markets "
                "with planted anomaly episodes: momentum runs that follow through (90001@18, "
                "90003@14) and spike-and-revert moves that do not (90002@25, 90003@34)."
            ),
            "disclaimer": "Synthetic data. Not real Polymarket data. For demonstration only.",
        },
        "markets": markets,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, sort_keys=True))
    size = OUT.stat().st_size
    n_frames = sum(len(m["frames"]) for m in data["markets"])
    print(f"wrote {OUT} ({size/1024:.1f} KiB, {len(data['markets'])} markets, {n_frames} frames)")


if __name__ == "__main__":
    main()
