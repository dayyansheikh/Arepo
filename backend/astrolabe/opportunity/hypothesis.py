"""Plain-English statistical hypothesis, generated from computed evidence only.

The product's central promise (spec §6) is that every important surface leads with a
*cautious* directional hypothesis derived from the actual computed signal, and that when the
evidence is insufficient it says so rather than forcing a prediction. Keeping this in one
place means the Opportunity Board card, the market-analysis page and the alert copy all state
the same hypothesis under the same rules, and it can be unit-tested in isolation.

Semantics of ``direction`` (from ``analytics.anomaly``): the sign of the anomaly z-score for
this outcome token. ``"up"`` means the outcome repriced upward (evidence of upward pressure on
that outcome), ``"down"`` downward. We phrase the hypothesis in terms of *repricing pressure*
on the named outcome, which is unambiguous and honest even when the complementary outcome name
is unknown. We never claim a probability of profit or expected return.
"""
from __future__ import annotations

# Strength bands (signal_strength is in [0, 1]); aligned with the 40 / 70 bands the UI already
# uses for "Medium (40-69)" / "High (70+)".
STRENGTH_MODERATE = 0.40
STRENGTH_STRONG = 0.70

# Below this, and with no corroborating evidence family, we do not assert a direction at all.
DIRECTIONAL_STRENGTH_FLOOR = 0.40


def has_directional_view(direction: str | None, n_families: int, signal_strength: float) -> bool:
    """Is there enough computed evidence to state a directional lean at all?

    Requires a resolved direction AND either at least one independent evidence family firing
    OR a signal at least as strong as the moderate floor. A bare, weak, single-measure anomaly
    is treated as "not enough evidence" rather than a prediction.
    """
    if direction not in ("up", "down"):
        return False
    return n_families >= 1 or signal_strength >= DIRECTIONAL_STRENGTH_FLOOR


def _strength_word(signal_strength: float) -> str:
    if signal_strength >= STRENGTH_STRONG:
        return "strong"
    if signal_strength >= STRENGTH_MODERATE:
        return "moderate"
    return "early"


def _horizon_phrase(time_remaining_hours: float | None) -> str:
    if time_remaining_hours is None or time_remaining_hours <= 0:
        return ""
    if time_remaining_hours <= 24:
        return " before it closes within a day"
    days = time_remaining_hours / 24.0
    if days <= 7:
        return f" over roughly the {round(days)} days before it closes"
    return ""


def build_hypothesis(
    *,
    direction: str | None,
    outcome: str | None,
    n_families: int,
    signal_strength: float,
    time_remaining_hours: float | None = None,
) -> str:
    """Return a single cautious sentence describing the current model view.

    Falls back to an explicit insufficient-evidence statement when no directional view is
    warranted, so callers never have to invent a direction.
    """
    if not has_directional_view(direction, n_families, signal_strength):
        return (
            "Arepo does not currently have enough independent evidence to favour a "
            "direction in this market."
        )
    strength = _strength_word(signal_strength)
    name = outcome or "this"
    pressure = "upward" if direction == "up" else "downward"
    horizon = _horizon_phrase(time_remaining_hours)
    return (
        f"Arepo currently sees {strength} evidence of {pressure} repricing pressure on "
        f"the {name} outcome{horizon}."
    )
