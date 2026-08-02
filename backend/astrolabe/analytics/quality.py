"""Data-quality assessment and confidence scoring.

Confidence is a multiplicative penalty model in [0, 1]. It starts at 1.0 and is reduced by
independent, transparent penalties whenever the inputs are weak. Every penalty applied is
recorded as a human-readable reason, so a low confidence is always explainable.

Penalties (per spec §9 "Confidence and data quality"): short history, wide spread, thin book,
stale data, incomplete (one-sided) book, partial API coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.enums import DataQuality


def squash(x: float, cap: float) -> float:
    """Map a non-negative magnitude to [0, 1] linearly, saturating at ``cap``."""
    if cap <= 0:
        raise ValueError("cap must be > 0")
    return float(min(1.0, max(0.0, abs(x) / cap)))


@dataclass
class QualityAssessment:
    confidence: float                    # [0, 1]
    band: DataQuality
    reasons: list[str] = field(default_factory=list)

    def penalise(self, factor: float, reason: str) -> None:
        """Apply a multiplicative penalty in [0, 1] and record why."""
        factor = float(max(0.0, min(1.0, factor)))
        if factor < 1.0:
            self.confidence *= factor
            self.reasons.append(reason)


def assess_quality(
    *,
    n_history: int,
    ideal_history: int = 20,
    relative_spread: float | None,
    wide_spread_threshold: float = 0.10,
    near_mid_depth: float | None,
    thin_depth_floor: float = 100.0,
    data_age_seconds: float | None,
    stale_after_seconds: float = 60.0,
    two_sided_book: bool,
    partial_coverage: bool = False,
) -> QualityAssessment:
    """Combine independent quality signals into a confidence in [0, 1] and a coarse band.

    All arguments are keyword-only and each may be ``None`` when unknown (an unknown input
    applies no penalty rather than guessing). See docs/methodology.md for the rationale and the
    exact thresholds, which are exposed here as assumptions.
    """
    q = QualityAssessment(confidence=1.0, band=DataQuality.GOOD)

    # 1. Short history — scale linearly with how much of the ideal window we have.
    if n_history < ideal_history:
        frac = max(0.2, n_history / ideal_history) if ideal_history > 0 else 0.2
        q.penalise(frac, f"short history ({n_history}/{ideal_history} obs)")

    # 2. Wide spread — a wide relative spread means the mid is a noisier probability estimate.
    if relative_spread is not None and relative_spread > wide_spread_threshold:
        # Penalty grows with how far past the threshold we are, floored at 0.4.
        over = relative_spread / wide_spread_threshold
        q.penalise(max(0.4, 1.0 / over), f"wide spread (rel={relative_spread:.3f})")

    # 3. Thin book near the mid.
    if near_mid_depth is not None and near_mid_depth < thin_depth_floor:
        frac = max(0.3, near_mid_depth / thin_depth_floor) if thin_depth_floor > 0 else 0.3
        q.penalise(frac, f"thin near-mid depth ({near_mid_depth:.0f})")

    # 4. Stale data — linear decay from 1.0 at stale_after to 0.1 at 5x stale_after.
    if data_age_seconds is not None and data_age_seconds > stale_after_seconds:
        span = 4.0 * stale_after_seconds
        over = data_age_seconds - stale_after_seconds
        frac = max(0.1, 1.0 - over / span) if span > 0 else 0.1
        q.penalise(frac, f"stale data ({data_age_seconds:.0f}s old)")

    # 5. Incomplete (one-sided) book — a hard, heavy penalty; mid/spread are undefined.
    if not two_sided_book:
        q.penalise(0.3, "incomplete order book (one-sided)")

    # 6. Partial API coverage (e.g. WS down, some fields unavailable).
    if partial_coverage:
        q.penalise(0.7, "partial API coverage")

    # Map final confidence to a coarse band.
    if q.confidence >= 0.75:
        q.band = DataQuality.GOOD
    elif q.confidence >= 0.45:
        q.band = DataQuality.LIMITED
    else:
        q.band = DataQuality.POOR
    return q
