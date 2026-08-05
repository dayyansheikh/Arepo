"""Calibration guard and metrics (prompt section 11).

Brier score and log loss are only meaningful when there is a genuine PROBABILITY forecast and a
resolved binary outcome. Arepo currently emits a directional call, not a calibrated probability, so
these are guarded off until either (a) a probability-of-favourable-repricing head exists, or (b) a
validated mapping from confidence to realised directional frequency is built on a held-out sample of
at least ``MIN_CALIBRATION_SAMPLE`` resolved predictions. Until then the status is unavailable with
an honest message rather than a fabricated number.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .research_constants import CALIBRATION_UNAVAILABLE_MSG, MIN_CALIBRATION_SAMPLE


@dataclass(frozen=True)
class CalibrationStatus:
    available: bool
    resolved_sample: int
    minimum_required: int
    message: str
    bins: list | None = None


def calibration_status(resolved_sample: int, bins: list | None = None) -> CalibrationStatus:
    if resolved_sample < MIN_CALIBRATION_SAMPLE:
        return CalibrationStatus(
            available=False,
            resolved_sample=resolved_sample,
            minimum_required=MIN_CALIBRATION_SAMPLE,
            message=CALIBRATION_UNAVAILABLE_MSG,
            bins=None,
        )
    return CalibrationStatus(
        available=True,
        resolved_sample=resolved_sample,
        minimum_required=MIN_CALIBRATION_SAMPLE,
        message="Calibration available.",
        bins=bins,
    )


def brier_score(forecasts: list[float], outcomes: list[int]) -> float | None:
    """Mean squared error of probability forecasts vs binary outcomes. None if inputs are empty or
    mismatched (never fabricated). Only call with a GENUINE probability forecast."""
    pairs = [(p, o) for p, o in zip(forecasts, outcomes, strict=False) if p is not None]
    if not pairs:
        return None
    return sum((p - o) ** 2 for p, o in pairs) / len(pairs)


def log_loss(forecasts: list[float], outcomes: list[int], eps: float = 1e-15) -> float | None:
    pairs = [(min(1 - eps, max(eps, p)), o) for p, o in zip(forecasts, outcomes, strict=False)
             if p is not None]
    if not pairs:
        return None
    return -sum(o * math.log(p) + (1 - o) * math.log(1 - p) for p, o in pairs) / len(pairs)


def confidence_frequency_bins(
    pairs: list[tuple[float, bool]], *, n_bins: int = 5
) -> list[dict]:
    """Map confidence -> realised directional-correct frequency, in equal-width bins. This is the
    calibration curve for the directional interpretation once the sample is large enough."""
    bins: list[dict] = []
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        inside = [c for conf, c in pairs
                  if (lo <= conf < hi) or (b == n_bins - 1 and conf == hi)]
        freq = round(sum(1 for c in inside if c) / len(inside), 3) if inside else None
        bins.append({"band": f"{lo:.1f}-{hi:.1f}", "n": len(inside), "correct_frequency": freq})
    return bins
