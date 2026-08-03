"""Composite anomaly score.

Blends a small set of normalised, individually-visible components into one [0, 1] score. The
score is a *screening* tool: it flags markets whose recent behaviour is statistically unusual
and worth a closer look. It is **not** evidence of insider trading, and not a profit signal.

Each component is normalised to a [0, 1] magnitude via a transparent, saturating map (see
``quality.squash``) with a documented cap. The composite is the weighted mean over the
components that are actually available (weights renormalise across present components, so a
missing input neither inflates nor deflates the score). Default weights are exposed as
assumptions and justified in docs/methodology.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import DataQuality, SignalKind
from ..domain.models import Signal, SignalComponent
from .quality import QualityAssessment, squash

# Default component weights (sum to 1.0). Exposed and documented as assumptions, not claimed
# to be empirically optimal — a firm would re-derive these from labelled data. Rebalanced so
# the score is led by price-behaviour features and no single book feature can dominate: the
# three price features carry 0.60, order-book imbalance only 0.12. See docs/methodology.md.
DEFAULT_WEIGHTS: dict[str, float] = {
    "unusual_return": 0.24,        # |rolling z-score of the latest return|
    "movement_abnormality": 0.20,  # standardised magnitude of the recent multi-step move
    "volatility_regime": 0.16,     # short vs long return-volatility (spike)
    "volume_acceleration": 0.12,   # relative rise in recent volume (when available)
    "book_imbalance": 0.12,        # |near-touch bid/ask depth imbalance|
    "spread_change": 0.08,         # relative change in spread vs baseline (when available)
    "depth_change": 0.08,          # relative change in near-mid depth vs baseline (when available)
}

# Saturation caps for each raw component (the value at which the normalised magnitude hits 1.0).
DEFAULT_CAPS: dict[str, float] = {
    "unusual_return": 4.0,         # |z| of 4 => fully saturated
    "movement_abnormality": 4.0,   # a 4-sigma cumulative move => saturated
    "volatility_regime": 2.0,      # recent vol 3x the baseline => saturated
    "volume_acceleration": 3.0,    # 300% acceleration => saturated
    "book_imbalance": 1.0,         # already in [-1, 1]
    "spread_change": 1.0,          # relative spread change
    "depth_change": 1.0,           # relative depth change
}

# The price-behaviour features. The composite requires at least one of these to be present to
# award a full score; a reading built on order-book features alone is capped (see the
# BOOK_ONLY_CEILING safeguard) so imbalance can never drive a top signal by itself.
PRICE_FEATURES = frozenset({"unusual_return", "movement_abnormality", "volatility_regime"})
BOOK_ONLY_CEILING = 0.5
# A price feature must clear this normalised magnitude to count as genuine price context; a
# present-but-near-zero feature (a calm market) does not lift the book-only ceiling.
PRICE_CONTEXT_FLOOR = 0.05

# User-facing names for each raw component identifier. The raw identifiers above are internal
# and documented in docs/methodology.md; readers should never see them by default (see spec
# section 12, "Surface terminology").
COMPONENT_LABELS: dict[str, str] = {
    "unusual_return": "unusual price move",
    "movement_abnormality": "abnormal recent move",
    "volatility_regime": "volatility spike",
    "volume_acceleration": "faster trading activity",
    "book_imbalance": "order-book imbalance",
    "spread_change": "spread change",
    "depth_change": "available depth change",
}


@dataclass(frozen=True)
class RawComponents:
    """Raw (pre-normalisation) component inputs. Any may be None if unavailable."""

    zscore: float | None = None
    movement_abnormality: float | None = None    # standardised recent multi-step move magnitude
    volatility_regime: float | None = None       # short/long return-vol - 1 (elevated side only)
    volume_acceleration: float | None = None     # (recent - baseline)/baseline
    imbalance: float | None = None               # signed, [-1, 1]
    spread_change: float | None = None           # relative change vs baseline
    depth_change: float | None = None            # relative change vs baseline (drop => notable)


def _normalise(raw: RawComponents, caps: dict[str, float]) -> list[SignalComponent]:
    """Turn raw inputs into visible, normalised [0,1]-magnitude components."""
    specs = [
        ("unusual_return", raw.zscore, "|rolling z-score of the latest additive return|"),
        ("movement_abnormality", raw.movement_abnormality,
         "recent multi-step move standardised by its own return scale"),
        ("volatility_regime", raw.volatility_regime,
         "recent return-volatility relative to a longer baseline (spike)"),
        ("volume_acceleration", raw.volume_acceleration, "relative rise in recent volume"),
        ("book_imbalance", raw.imbalance, "|bid/ask depth imbalance| over first N levels"),
        ("spread_change", raw.spread_change, "relative change in spread vs baseline"),
        ("depth_change", raw.depth_change, "relative change in near-mid depth vs baseline"),
    ]
    components: list[SignalComponent] = []
    for name, value, explanation in specs:
        norm = None if value is None else squash(value, caps[name])
        components.append(
            SignalComponent(
                name=name,
                raw_value=None if value is None else float(value),
                normalized_value=norm,
                weight=DEFAULT_WEIGHTS[name],
                explanation=explanation,
            )
        )
    return components


def composite_anomaly_score(
    raw: RawComponents,
    weights: dict[str, float] | None = None,
    caps: dict[str, float] | None = None,
) -> tuple[float, list[SignalComponent]]:
    """Return ``(score in [0,1], visible components)``.

    The score is the weight-renormalised mean of available normalised components. If no
    component is available, the score is 0.0.
    """
    weights = weights or DEFAULT_WEIGHTS
    caps = caps or DEFAULT_CAPS
    components = _normalise(raw, caps)

    num = 0.0
    wsum = 0.0
    max_price_feature = 0.0
    for c in components:
        if c.normalized_value is None:
            continue
        w = weights.get(c.name, 0.0)
        num += w * c.normalized_value
        wsum += w
        if c.name in PRICE_FEATURES:
            max_price_feature = max(max_price_feature, c.normalized_value)
    score = (num / wsum) if wsum > 0 else 0.0

    # Safeguard: a reading with no *material* price-behaviour context cannot earn a top score.
    # We require a price feature whose normalised value clears a small floor, not merely one
    # that is present-but-zero (a calm market produces a present-but-zero volatility regime on
    # every tick). This stops order-book/flow features alone (imbalance, spread, depth) from
    # driving a strong signal, and keeps the composite honest when the price is not moving.
    if max_price_feature <= PRICE_CONTEXT_FLOOR and score > BOOK_ONLY_CEILING:
        score = BOOK_ONLY_CEILING
    return float(max(0.0, min(1.0, score))), components


def build_anomaly_signal(
    *,
    token_id: str,
    market_id: str,
    raw: RawComponents,
    quality: QualityAssessment,
    window_desc: str | None = None,
    weights: dict[str, float] | None = None,
    caps: dict[str, float] | None = None,
) -> Signal:
    """Assemble a fully-explained composite-anomaly ``Signal`` from raw inputs + quality.

    ``strength`` is the raw composite score; ``confidence`` folds in the data-quality penalty
    (strength * quality.confidence), so a strong-but-untrustworthy reading ranks below a
    strong-and-trustworthy one.
    """
    score, components = composite_anomaly_score(raw, weights=weights, caps=caps)
    direction = None
    if raw.zscore is not None:
        direction = "up" if raw.zscore > 0 else "down" if raw.zscore < 0 else None

    present = [c.name for c in components if c.normalized_value is not None]
    friendly_present = [COMPONENT_LABELS.get(name, name) for name in present]
    if friendly_present:
        detected = (
            "Recent behaviour is statistically unusual versus this market's own history, "
            f"driven mainly by: {', '.join(friendly_present)}."
        )
    else:
        detected = "Recent behaviour is statistically unusual versus this market's own history."
    return Signal(
        kind=SignalKind.COMPOSITE_ANOMALY,
        token_id=token_id,
        market_id=market_id,
        value=score,
        strength=score,
        direction=direction,
        detected=detected,
        method=(
            "Weighted mean of normalised components, led by price behaviour: the latest-return "
            "z-score, the standardised size of the recent multi-step move, and a volatility-regime "
            "shift, alongside volume acceleration, order-book imbalance, and spread and depth "
            "change when available. Each saturates at a documented cap; weights renormalise over "
            "the components actually present, and a reading with no price context is capped so "
            "order-book imbalance cannot drive a top score on its own. See docs/methodology.md."
        ),
        why_it_matters=(
            "When several independent measures move at once, an unusually large or sustained price "
            "move, a jump in volatility, heavier trading and a lopsided book, the market may be "
            "repricing. It is worth investigating, not proof of anything."
        ),
        limitations=(
            "Screening heuristic only. Not evidence of insider activity; not a profit signal. "
            "Sensitive to the chosen weights, caps and windows, which are assumptions. Spread and "
            "depth change need an order-book time series that the read-only live path does not "
            "capture, so they are usually absent and the score leans on price and imbalance."
        ),
        components=components,
        data_quality=quality.band if isinstance(quality.band, DataQuality) else DataQuality.GOOD,
        confidence=score * quality.confidence,
        window=window_desc,
    )
