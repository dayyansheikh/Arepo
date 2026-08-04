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

# A forward move at or below this magnitude (probability points) is treated as FLAT: the market did
# not meaningfully move, so a directional call is neither right nor wrong. This single tolerance is
# applied symmetrically to EVERY directional predictor (Arepo, momentum, price-only,
# current-implied, always-up/down) and to the prospective cohort pipeline, and it is the same
# threshold the no-change baseline uses. It is a predeclared rule (spec §10/§11, DECISIONS D-SR1),
# fixed on principle, not tuned to outcomes: flats are excluded from every directional hit-rate
# denominator and reported in their own column so a flat market is never booked as a miss.
FLAT_EPS = 0.01


def classify_directional(
    direction: str | None, move: float | None, flat_eps: float = FLAT_EPS
) -> str | None:
    """Ternary (plus abstain) outcome of a directional call against a realised forward move.

    Returns ``"flat"`` when ``|move| <= flat_eps`` (the market did not move, so the call is neither
    right nor wrong), ``"correct"`` / ``"incorrect"`` when it did move, or ``None`` when there is no
    forward move to evaluate (pending) or the predictor made no directional call (abstained). Flats
    are deliberately NOT ``correct`` and NOT ``incorrect`` so they are excluded from the hit-rate
    denominator for every directional predictor identically.
    """
    if move is None:
        return None
    if abs(move) <= flat_eps:
        return "flat"
    if direction not in ("up", "down"):
        return None
    return "correct" if ((move > 0) == (direction == "up")) else "incorrect"


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
    entry_price: float | None = None  # implied probability at the cut-off (for current-implied)
    price_only_direction: str | None = None  # sign of the trailing lookback trend (price-only)


def _correct(direction: str | None, move: float | None) -> bool | None:
    """True/False only when the market moved beyond FLAT_EPS; None when flat, pending or abstained.

    Flats return None (not False) so a directional call on a market that did not move is never
    scored as a miss. Callers count flats separately via ``classify_directional``.
    """
    outcome = classify_directional(direction, move)
    if outcome == "correct":
        return True
    if outcome == "incorrect":
        return False
    return None


@dataclass(frozen=True)
class BaselineComparison:
    sample_size: int
    verdict: str
    arepo: dict
    baselines: dict
    # Fraction of scored markets where Arepo's directional call equals the momentum baseline's.
    # Arepo's direction is the sign of the latest-return z-score, so it is close to momentum by
    # construction; a high agreement means "Arepo vs momentum" is near-self-referential and must
    # not be read as an independent win (quant review B#3). None when nothing was scored.
    arepo_momentum_agreement: float | None = None
    # Brier score / log loss are deliberately NOT reported for the reconstructed directional screen:
    # Arepo emits a directional call, not a calibrated probability, and reconstructed markets rarely
    # resolve within the window, so any Brier/log-loss here would be fabricated. They are reserved
    # for the prospective cohort's resolution view once enough markets resolve (spec §12, §13).
    probabilistic_metrics_note: str = (
        "Brier score and log loss are not applicable to a directional (non-probabilistic) call and "
        "are reserved for the prospective resolution view; they are not computed on this screen."
    )


def _score(name: str, directions: list[str | None], moves: list[float | None]) -> dict:
    outcomes = [
        classify_directional(d, m) for d, m in zip(directions, moves, strict=False)
    ]
    k = sum(1 for o in outcomes if o == "correct")
    incorrect = sum(1 for o in outcomes if o == "incorrect")
    flat = sum(1 for o in outcomes if o == "flat")
    n = k + incorrect            # flats and abstentions are excluded from the hit-rate denominator
    lo, hi = wilson_interval(k, n)
    return {
        "name": name,
        "evaluated": n,
        "correct": k,
        "incorrect": incorrect,
        "flat": flat,
        "hit_rate": (k / n) if n else None,
        "ci95": [round(lo, 3), round(hi, 3)],
        "verdict": sample_verdict(n),
    }


def compare_baselines(results: list[DirectionalResult]) -> BaselineComparison:
    """Score Arepo and each causal baseline over the same reconstructed sample.

    Baselines (all causally valid at the cut-off, using only cut-off information):
    - no-change: predicts flat (correct when the actual 24h move is within FLAT_EPS);
    - current-implied: predicts the outcome drifts toward its more-likely state (up if the entry
      implied probability > 0.5, else down) - the favourite-drift baseline;
    - price-only: the sign of the trailing lookback price trend (a pure price/trend predictor);
    - momentum: the sign of the short trailing pre-cut-off move;
    - always-up / always-down: naive references.

    Order-book-only is NOT included: Polymarket historical order books were never stored, so it
    cannot be reconstructed for a past cut-off (documented in docs/replay-report-reconciliation.md).
    """
    moves = [r.move_24h for r in results]
    arepo_dirs = [r.arepo_direction for r in results]
    momentum_dirs = [r.momentum_direction for r in results]
    price_only_dirs = [r.price_only_direction for r in results]
    implied_dirs = [
        ("up" if (r.entry_price is not None and r.entry_price > 0.5) else "down")
        if r.entry_price is not None else None
        for r in results
    ]

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
            # No change predicts flat, so a flat market is its win, not an excluded outcome; it has
            # no separate flat bucket. Shown for column parity with the directional predictors.
            "flat": 0,
            "hit_rate": (nc_correct / len(nc_eval)) if nc_eval else None,
            "ci95": [round(nc_lo, 3), round(nc_hi, 3)],
            "verdict": sample_verdict(len(nc_eval)),
        },
        "current_implied": _score("Current implied", implied_dirs, moves),
        "price_only": _score("Price only", price_only_dirs, moves),
        "momentum": _score("Momentum", momentum_dirs, moves),
        "always_up": _score("Always up", ["up"] * len(moves), moves),
        "always_down": _score("Always down", ["down"] * len(moves), moves),
    }
    # How often Arepo's call matches momentum, over markets where both made a call (diagnostic for
    # the near-self-referential "Arepo vs momentum" comparison, B#3).
    both = [
        (a, m)
        for a, m in zip(arepo_dirs, momentum_dirs, strict=False)
        if a in ("up", "down") and m in ("up", "down")
    ]
    agreement = (sum(1 for a, m in both if a == m) / len(both)) if both else None
    return BaselineComparison(
        sample_size=arepo["evaluated"],
        verdict=sample_verdict(arepo["evaluated"]),
        arepo=arepo,
        baselines=baselines,
        arepo_momentum_agreement=round(agreement, 3) if agreement is not None else None,
    )
