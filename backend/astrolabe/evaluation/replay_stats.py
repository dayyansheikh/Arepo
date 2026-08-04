"""Honest sample statistics and causal baselines for Replay (spec §5, §6).

The historical reconstruction produces very small samples. This module makes that honest: it
labels below-minimum samples as *inconclusive*, reports a Wilson confidence interval rather than a
bare hit rate, and compares Arepo's directional calls against simple causally-valid baselines so
any apparent edge must beat them on the same sample. It never claims an edge; it computes numbers
the UI can present transparently.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Below this many evaluated markets, a hit rate is not meaningful and must be labelled so. A 95%
# interval on a handful of Bernoulli trials spans almost all of [0, 1].
MIN_MEANINGFUL_SAMPLE = 20

# A 24h move smaller than this (probability points) is treated as flat for the no-change baseline.
FLAT_EPS = 0.01


def sample_verdict(n: int) -> str:
    """'inconclusive' below the minimum meaningful sample, else 'indicative'."""
    return "inconclusive" if n < MIN_MEANINGFUL_SAMPLE else "indicative"


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials. (0, 1) when n == 0."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class DirectionalResult:
    """One reconstructed market's directional inputs (all known at or after the cut-off, causal)."""

    arepo_direction: str | None       # up | down | None
    momentum_direction: str | None    # sign of the pre-cut-off move (up | down | None)
    move_24h: float | None            # real 24h forward move (probability points)


def _correct(direction: str | None, move: float | None) -> bool | None:
    if direction not in ("up", "down") or move is None:
        return None
    return (move > 0) if direction == "up" else (move < 0)


@dataclass(frozen=True)
class BaselineComparison:
    sample_size: int
    verdict: str
    arepo: dict
    baselines: dict


def _score(name: str, directions: list[str | None], moves: list[float | None]) -> dict:
    evaluated = [
        (_correct(d, m))
        for d, m in zip(directions, moves, strict=False)
        if _correct(d, m) is not None
    ]
    n = len(evaluated)
    k = sum(1 for c in evaluated if c)
    lo, hi = wilson_interval(k, n)
    return {
        "name": name,
        "evaluated": n,
        "correct": k,
        "incorrect": n - k,
        "hit_rate": (k / n) if n else None,
        "ci95": [round(lo, 3), round(hi, 3)],
        "verdict": sample_verdict(n),
    }


def compare_baselines(results: list[DirectionalResult]) -> BaselineComparison:
    """Score Arepo and each causal baseline over the same reconstructed sample.

    Baselines (all causally valid at the cut-off): no-change predicts flat (correct when the actual
    24h move is within FLAT_EPS); momentum predicts the sign of the trailing pre-cut-off move;
    always-up / always-down are naive references.
    """
    moves = [r.move_24h for r in results]
    arepo_dirs = [r.arepo_direction for r in results]
    momentum_dirs = [r.momentum_direction for r in results]

    # no-change: "correct" when the market was effectively flat over 24h.
    nc_eval = [m for m in moves if m is not None]
    nc_correct = sum(1 for m in nc_eval if abs(m) <= FLAT_EPS)
    nc_lo, nc_hi = wilson_interval(nc_correct, len(nc_eval))

    arepo = _score("Arepo", arepo_dirs, moves)
    baselines = {
        "no_change": {
            "name": "No change",
            "evaluated": len(nc_eval),
            "correct": nc_correct,
            "incorrect": len(nc_eval) - nc_correct,
            "hit_rate": (nc_correct / len(nc_eval)) if nc_eval else None,
            "ci95": [round(nc_lo, 3), round(nc_hi, 3)],
            "verdict": sample_verdict(len(nc_eval)),
        },
        "momentum": _score("Momentum", momentum_dirs, moves),
        "always_up": _score("Always up", ["up"] * len(moves), moves),
        "always_down": _score("Always down", ["down"] * len(moves), moves),
    }
    return BaselineComparison(
        sample_size=arepo["evaluated"],
        verdict=sample_verdict(arepo["evaluated"]),
        arepo=arepo,
        baselines=baselines,
    )
