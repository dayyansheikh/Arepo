"""Research Priority score, evidence families and tags (pure, testable, no network).

The score combines independent evidence families with fixed, documented weights and a bonus
for the *number* of independent families that fired, then scales the result down for poor data
quality, thin liquidity, wide spreads and stale data (spec section 5). It is deliberately not
called expected profit; it ranks how much a market deserves a closer look.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..analytics.anomaly import PRICE_CONTEXT_FLOOR, PRICE_FEATURES
from ..analytics.flow import (
    FAMILY_BOOK,
    FAMILY_FLOW,
    FAMILY_PRICE,
    FAMILY_TIMING,
    FAMILY_WALLET,
    FlowIndicator,
)
from ..domain.models import Signal

# Relative importance of each evidence family in the combined evidence score. Fixed and
# documented, not fitted to outcomes.
FAMILY_WEIGHTS: dict[str, float] = {
    FAMILY_PRICE: 0.24,
    FAMILY_FLOW: 0.26,
    FAMILY_WALLET: 0.20,
    FAMILY_TIMING: 0.15,
    FAMILY_BOOK: 0.15,
}
# More independent families firing is stronger evidence; this many saturates the bonus.
TARGET_FAMILIES = 3
# A high-priority opportunity normally needs at least this many independent families (spec 5.5).
MIN_FAMILIES_HIGH_PRIORITY = 2

# Liquidity / spread shaping (market-relative gates on the final score, never hard filters).
LIQUIDITY_FULL = 50_000.0     # >= this much liquidity => no liquidity penalty
LIQUIDITY_THIN = 2_000.0      # <= this is a thin market
SPREAD_WIDE = 0.08            # relative spread at/above which the score is fully penalised
STALE_SECONDS = 3600.0        # data older than this starts to reduce the score

# Methodology anchors for tags (page: docs/methodology.md sections rendered on /methodology).
TAG_METHODOLOGY: dict[str, str] = {
    "Rapid repricing": "signal-strength",
    "One-sided book": "order-book-imbalance",
    "Large relative trade": "trade-flow",
    "Contrarian flow": "trade-flow",
    "Concentrated flow": "wallet-concentration",
    "Clustered trades": "trade-flow",
    "Late large trade": "trade-timing",
    "Limited activity history": "wallet-concentration",
    "Thin market": "liquidity",
    "Liquidity weakening": "liquidity",
    "Limited data": "confidence",
}


@dataclass
class Tag:
    label: str
    family: str
    explanation: str
    methodology_anchor: str
    data_quality: str
    timestamp: datetime


@dataclass
class ScoredOpportunity:
    research_priority: float                 # [0, 1]; display as x100
    signal_strength: float
    confidence: float
    data_quality: str
    families: list[str]                      # distinct families that fired
    n_families: int
    tags: list[Tag]
    explanation: str
    liquidity_quality: str                   # good | moderate | thin
    breakdown: dict = field(default_factory=dict)

    @property
    def high_priority(self) -> bool:
        return self.n_families >= MIN_FAMILIES_HIGH_PRIORITY and self.research_priority >= 0.5


def _price_family(signal: Signal) -> tuple[bool, float]:
    """Price family fires when a price-behaviour feature is materially present (rapid repricing)."""
    best = 0.0
    for c in signal.components:
        if c.name in PRICE_FEATURES and c.normalized_value is not None:
            best = max(best, c.normalized_value)
    return best > PRICE_CONTEXT_FLOOR, best


def _book_family(signal: Signal) -> tuple[bool, float]:
    """Order-book family from the imbalance component (never a strong signal on its own)."""
    for c in signal.components:
        if c.name == "book_imbalance" and c.normalized_value is not None:
            return c.normalized_value >= 0.5, c.normalized_value
    return False, 0.0


# Confidence as an estimated-reliability score (spec §6; research report lines 774, 1087-1089).
# It is NOT signal size and NOT mere data completeness. It combines the data-quality term with a
# corroboration term: a single, uncorroborated evidence family is capped well below 1.0, and only
# genuinely multi-family, high-data-quality readings approach full confidence. This gives
# meaningful variation and removes the old spike at 100%.
RELIABILITY_BASE = 0.45          # reliability of a single-family reading before data quality
RELIABILITY_SPAN = 0.55          # extra reliability earned by full family corroboration
# Microstructure components that must be present for the reading to be considered complete. When
# they are missing (no snapshot series yet, or none available historically) confidence is reduced
# rather than pretending the reading is fully informed (spec §8.5, §9).
COMPLETENESS_FLOOR = 0.80        # confidence multiplier when ALL microstructure components missing


def reliability_confidence(
    data_quality_confidence: float,
    n_families: int,
    component_completeness: float = 1.0,
) -> float:
    """Estimated reliability in [0, 1] = data quality x corroboration x component completeness.

    ``data_quality_confidence`` is the freshness/coverage term from ``assess_quality``.
    Corroboration rises with the number of *distinct* evidence families that fired (saturating at
    ``TARGET_FAMILIES``). With one family the reliability factor is ``RELIABILITY_BASE`` (so even
    perfect data quality yields well under 100%); with ``TARGET_FAMILIES`` agreeing families it
    reaches 1.0. ``component_completeness`` in [0, 1] is the fraction of the microstructure change
    components actually present; when they are missing, confidence is scaled down (never below
    ``COMPLETENESS_FLOOR`` of its otherwise-value) so a reading built on incomplete microstructure
    history cannot display full confidence.
    """
    dq = max(0.0, min(1.0, data_quality_confidence))
    corroboration = min(1.0, max(0, n_families) / TARGET_FAMILIES)
    reliability_factor = RELIABILITY_BASE + RELIABILITY_SPAN * corroboration
    completeness = max(0.0, min(1.0, component_completeness))
    completeness_factor = COMPLETENESS_FLOOR + (1.0 - COMPLETENESS_FLOOR) * completeness
    return float(max(0.0, min(1.0, dq * reliability_factor * completeness_factor)))


# Microstructure change components used to judge how *complete* a reading is. Only components that
# the read-only live path can actually obtain count here: spread and depth change come from the
# persisted order-book snapshot series (present ~60-67% of the time). `volume_acceleration` is
# deliberately excluded: the live path never stores a volume series, so it is present 0% of the
# time and including it would permanently drag every live confidence down for a reason unrelated to
# data quality (spec §4, §6). It remains defined for the replay/backtest paths that do have volumes.
COMPLETENESS_COMPONENTS = ("spread_change", "depth_change")


def _component_completeness(signal: Signal) -> float:
    present = sum(
        1 for c in signal.components
        if c.name in COMPLETENESS_COMPONENTS and c.raw_value is not None
    )
    return present / len(COMPLETENESS_COMPONENTS)


def signal_reliability(signal: Signal) -> tuple[float, int]:
    """Displayed reliability confidence + evidence-family count from the signal ALONE.

    This is the number every surface that shows a signal without live trade flow (Signal Lab,
    Market Detail) must display, so the same signal never shows two different confidences (spec
    §6, §17). It counts only the families the signal itself carries (price behaviour and order
    book); the Opportunity Board may add trade-flow / wallet / timing families when live trades
    are available, which is the one documented, legitimate reason its confidence can be higher.
    """
    families: list[str] = []
    if _price_family(signal)[0]:
        families.append(FAMILY_PRICE)
    if _book_family(signal)[0]:
        families.append(FAMILY_BOOK)
    n = len(families)
    conf = reliability_confidence(signal.confidence, n, _component_completeness(signal))
    return conf, n


def _liquidity_factor(liquidity: float | None) -> tuple[float, str]:
    if liquidity is None:
        return 0.7, "moderate"
    if liquidity >= LIQUIDITY_FULL:
        return 1.0, "good"
    if liquidity <= LIQUIDITY_THIN:
        return 0.4, "thin"
    # linear between thin and full
    frac = (liquidity - LIQUIDITY_THIN) / (LIQUIDITY_FULL - LIQUIDITY_THIN)
    return 0.4 + 0.6 * frac, "moderate"


def _spread_factor(rel_spread: float | None) -> float:
    if rel_spread is None:
        return 0.85
    if rel_spread <= 0.0:
        return 1.0
    return max(0.3, 1.0 - min(1.0, rel_spread / SPREAD_WIDE))


def _freshness_factor(data_age_seconds: float | None) -> float:
    if data_age_seconds is None:
        return 1.0
    if data_age_seconds <= STALE_SECONDS:
        return 1.0
    # decay to 0.5 over a day past the stale threshold
    over = (data_age_seconds - STALE_SECONDS) / 86_400.0
    return max(0.5, 1.0 - 0.5 * min(1.0, over))


def score_opportunity(
    signal: Signal,
    flow_indicators: list[FlowIndicator],
    *,
    liquidity: float | None,
    relative_spread: float | None,
    data_age_seconds: float | None,
    now: datetime,
) -> ScoredOpportunity:
    """Combine the composite signal and trade-flow indicators into a Research Priority score."""
    # Family magnitudes: max over the indicators/components in each family that fired.
    family_mag: dict[str, float] = {}
    tags: list[Tag] = []

    price_fired, price_mag = _price_family(signal)
    if price_fired:
        family_mag[FAMILY_PRICE] = price_mag
        tags.append(
            Tag("Rapid repricing", FAMILY_PRICE,
                "The price has moved unusually relative to this market's own recent behaviour.",
                TAG_METHODOLOGY["Rapid repricing"], signal.data_quality.value, now)
        )
    book_fired, book_mag = _book_family(signal)
    if book_fired:
        family_mag[FAMILY_BOOK] = book_mag
        tags.append(
            Tag("One-sided book", FAMILY_BOOK,
                "Resting size is lopsided between the bid and ask sides of the order book.",
                TAG_METHODOLOGY["One-sided book"], signal.data_quality.value, now)
        )

    for ind in flow_indicators:
        if not ind.fired:
            continue
        family_mag[ind.family] = max(family_mag.get(ind.family, 0.0), ind.magnitude)
        if ind.tag:
            tags.append(
                Tag(ind.tag, ind.family, ind.explanation,
                    TAG_METHODOLOGY.get(ind.tag, "signal-strength"),
                    signal.data_quality.value, now)
            )

    families = sorted(family_mag)
    n_families = len(families)

    # Weighted evidence score over families that fired (renormalised); fall back to the base
    # composite strength when nothing extra fired.
    if family_mag:
        wsum = sum(FAMILY_WEIGHTS.get(f, 0.1) for f in family_mag)
        evidence = sum(FAMILY_WEIGHTS.get(f, 0.1) * m for f, m in family_mag.items()) / wsum
    else:
        evidence = signal.strength

    family_bonus = min(1.0, n_families / TARGET_FAMILIES)

    # Shaping factors (spec 5.6: reduce for poor data quality, wide spread, poor liquidity, stale).
    liq_factor, liq_quality = _liquidity_factor(liquidity)
    spread_f = _spread_factor(relative_spread)
    fresh_f = _freshness_factor(data_age_seconds)
    # signal.confidence is now a pure data-quality term in [0, 1] (independent of strength),
    # so it is a genuine quality gate here rather than a hidden second strength multiplier.
    quality_factor = max(0.05, min(1.0, signal.confidence))

    raw = 0.55 * evidence + 0.45 * family_bonus
    priority = raw * quality_factor * liq_factor * spread_f * fresh_f
    priority = float(max(0.0, min(1.0, priority)))

    # Data-quality tags.
    if signal.data_quality.value == "poor":
        tags.append(
            Tag("Limited data", "price",
                "Data coverage for this reading is limited, so treat it cautiously.",
                TAG_METHODOLOGY["Limited data"], signal.data_quality.value, now)
        )
    if liq_quality == "thin":
        tags.append(
            Tag("Thin market", FAMILY_BOOK,
                "Liquidity is thin, so prices and signals here are easier to move and noisier.",
                TAG_METHODOLOGY["Thin market"], signal.data_quality.value, now)
        )

    # Confidence displayed to the user is the estimated reliability, not the raw data-quality
    # term (which is kept as `data_quality` band). signal.confidence is the data-quality input.
    # Component completeness = fraction of the obtainable microstructure change components present
    # (spread/depth change from the snapshot series); see COMPLETENESS_COMPONENTS for why volume
    # acceleration is excluded. Here n_families includes the live trade-flow families too, so a
    # board card can show higher confidence than Signal Lab for the same market (spec §17).
    component_completeness = _component_completeness(signal)
    confidence = reliability_confidence(signal.confidence, n_families, component_completeness)

    explanation = _explain(families, tags, evidence)
    return ScoredOpportunity(
        research_priority=priority,
        signal_strength=signal.strength,
        confidence=confidence,
        data_quality=signal.data_quality.value,
        families=families,
        n_families=n_families,
        tags=tags,
        explanation=explanation,
        liquidity_quality=liq_quality,
        breakdown={
            "evidence": round(evidence, 3),
            "family_bonus": round(family_bonus, 3),
            "quality_factor": round(quality_factor, 3),
            "liquidity_factor": round(liq_factor, 3),
            "spread_factor": round(spread_f, 3),
            "freshness_factor": round(fresh_f, 3),
            "family_magnitudes": {k: round(v, 3) for k, v in family_mag.items()},
        },
    )


_FAMILY_WORDS = {
    FAMILY_PRICE: "price behaviour",
    FAMILY_FLOW: "trade flow",
    FAMILY_BOOK: "order book",
    FAMILY_WALLET: "wallet concentration",
    FAMILY_TIMING: "trade timing",
}


def _explain(families: list[str], tags: list[Tag], evidence: float) -> str:
    if not families:
        return (
            "Flagged mainly on its composite anomaly score; no additional independent evidence "
            "fired, so treat it as a lead to read, not a strong signal."
        )
    words = [_FAMILY_WORDS.get(f, f) for f in families]
    joined = words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    n = len(families)
    lead = (
        f"{n} independent lines of evidence agree here ({joined})."
        if n >= 2
        else f"One line of evidence stands out here ({joined})."
    )
    return lead + " Open the analysis to see each one and check the market before acting."
