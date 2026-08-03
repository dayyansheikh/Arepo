"""Build a clearly-labelled SYNTHETIC demonstration cohort.

Purpose: give the Replay page a complete worked example (frozen entries, forward prices,
a resolution, a portfolio) before real prospective cohorts have had time to accrue. It is
provenance ``synthetic`` and is NEVER mixed into prospective statistics (the read service
reports each cohort separately and labels its provenance).

The market questions and entry prices come from the offline replay dataset; the signal
strengths, directions, forward prices and resolutions are illustrative values assigned
deterministically here (real replay signals are naturally weak). Everything is obviously
a demonstration, not real performance, and is labelled as such.
"""
from __future__ import annotations

from datetime import UTC, datetime

from ..domain.models import utcnow
from .constants import CALCULATION_VERSION, PROVENANCE_SYNTHETIC
from .engine import freeze_week, update_rankings
from .repository import EvaluationRepository
from .snapshots import build_snapshot_input

# A fixed past Monday so the synthetic cohort lands in a stable ISO week (2026-W28) and
# never collides with a real prospective week. A literal, not a wall-clock read.
_SEED_AT = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)

_NOTE = (
    "Synthetic demonstration cohort. Market questions and entry prices come from the "
    "offline replay dataset; strengths, directions, forward prices and resolutions are "
    "illustrative. It shows how the weekly process reads, not real market performance, "
    "and is never mixed into prospective statistics."
)

# Illustrative, deterministic strengths/directions for the demo entries.
_STRENGTHS = [0.91, 0.83, 0.76, 0.68, 0.61, 0.55, 0.49, 0.44, 0.39, 0.34]
_DIRECTIONS = ["up", "down", "up", "down", "up", "down", "up", "down", "up", "down"]


async def seed_synthetic_demo(session, market_service) -> int:
    """Create (idempotently) the synthetic demo cohort. Returns its id."""
    repo = EvaluationRepository(session)

    pairs, _ = await market_service.enrich_markets(requested_mode="replay")
    snaps = []
    for i, (market, analytics) in enumerate(pairs):
        # Represent each market by its leading outcome (highest implied probability).
        ta = max(
            analytics,
            key=lambda a: (a.implied if a.implied is not None else -1.0),
            default=None,
        )
        if ta is None:
            continue
        si = build_snapshot_input(
            market, ta, captured_at=_SEED_AT, calculation_version=CALCULATION_VERSION
        )
        si.strength = _STRENGTHS[i % len(_STRENGTHS)]
        si.confidence = max(0.3, 0.85 - i * 0.05)
        si.direction = _DIRECTIONS[i % len(_DIRECTIONS)]
        snaps.append(si)

    await update_rankings(
        session, snapshots=snaps, at=_SEED_AT, provenance_class=PROVENANCE_SYNTHETIC
    )
    cohort = await freeze_week(session, at=_SEED_AT, note=_NOTE)

    entries = await repo.get_entries(cohort.id)
    for e in entries:
        base = e.entry_price if e.entry_price is not None else 0.5
        drift = 0.06 if e.direction == "up" else -0.06
        for horizon, mult in (("1h", 0.3), ("24h", 1.0), ("7d", 1.4)):
            price = min(0.99, max(0.01, base + drift * mult))
            await repo.add_forward(
                e.id, horizon, observed_at=_SEED_AT, price=price, source_timestamp=_SEED_AT
            )

    # One entry resolves in its favour, one against, the rest remain pending, so the demo
    # shows correct / incorrect / pending side by side.
    if entries:
        e0 = entries[0]
        await repo.upsert_resolution(
            e0.market_id, condition_id=e0.condition_id, resolved=True,
            resolved_outcome=e0.outcome_name, resolved_token_id=e0.token_id,
            resolved_at=utcnow(), source="synthetic-demo",
        )
    if len(entries) > 1:
        e1 = entries[1]
        await repo.upsert_resolution(
            e1.market_id, condition_id=e1.condition_id, resolved=True,
            resolved_outcome="A different outcome", resolved_token_id=f"{e1.token_id}_other",
            resolved_at=utcnow(), source="synthetic-demo",
        )
    await session.commit()

    from .tracking import evaluate_all

    await evaluate_all(session)
    return cohort.id
