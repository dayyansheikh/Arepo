"""Prospective-Replay read service (refinement prompt sections 1-11).

Serves the public, prospective-only Replay product: the list of real frozen cohorts a user can
choose, and, for a chosen cohort + evaluation horizon + closing-window filter + scope, the
market-by-market result table and the aggregate "did the market move as expected?" answer.

Every number comes from stored prospective rows. Nothing reconstructed or synthetic enters here.
The server computes the evaluation truth (result state per entry, aggregate counts, movement
coverage) so the frontend never derives an important result state from loose client assumptions
(prompt section 11).

Product movement semantics (prompt sections 3, 6, 7) are deliberately distinct from the edge-
research HIT-RATE math. Here "No price change" means the stored midpoint did not move at all between
the freeze and the horizon (a tiny float-guard epsilon, ``REPLAY_MOVE_EPS``), so the honest answer
to "did the market move in Arepo's stored direction?" counts every real change. The 0.01 materiality
floor used for the edge verdict is a different, stricter question and is never applied here.

Short-term repricing (1h/6h/24h/7d) and final resolution are kept conceptually separate (prompt
section 3): a favourable short-term move is never treated as a correct final-outcome forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..discovery.snapshot_models import SignalSnapshotRow
from .execution import evaluate_execution
from .models import MarketResolutionRow
from .research_constants import (
    MODEL_VERSION,
    REPLAY_MOVE_EPS,
    ROLE_PUBLIC,
    ROLE_SHADOW,
)
from .research_models import ResearchCohortRow, ResearchEntryRow, ResearchForwardRow
from .research_preclose import freeze_to_close_result, preclose_for_cohort
from .research_repository import ResearchRepository

# --- Product-facing labels -----------------------------------------------------------------------
# A cadence's human name and the honest description of WHICH scheduled job freezes it. A manually
# created six-hour cohort must never be described as a weekly cohort (prompt section 2), so the
# description is derived from the stored cadence string, never assumed.
CADENCE_LABELS: dict[str, str] = {"6h": "Six-hourly", "daily": "Daily", "weekly": "Weekly"}
CADENCE_DESCRIPTIONS: dict[str, str] = {
    "6h": "a cohort frozen by the six-hourly scheduled job",
    "daily": "a cohort frozen by the daily scheduled job",
    "weekly": "a cohort frozen by the weekly scheduled job",
}

# Evaluation horizons offered in the product, in order. Final resolution is handled separately.
REPLAY_HORIZONS: tuple[str, ...] = ("1h", "6h", "24h", "7d")

# Closing-window filters on the FROZEN time-to-close (prompt section 4). The value is the maximum
# ``time_remaining_hours`` recorded at the freeze; ``None`` means no filter. Never recomputed from a
# market's current time-to-close.
CLOSING_FILTERS: dict[str, float | None] = {
    "6h": 6.0,
    "24h": 24.0,
    "7d": 24.0 * 7,
    "30d": 24.0 * 30,
    "all": None,
}

# Scope of the directional table (prompt section 5).
SCOPE_PUBLIC = "public"          # top public selections only
SCOPE_DIRECTIONAL = "directional"  # all directional signals, including shadow (the default)

# Result states for one directional call at one horizon (product display; prompt sections 5, 7).
RESULT_EXPECTED = "moved_expected"
RESULT_AGAINST = "moved_against"
RESULT_NO_CHANGE = "no_change"
RESULT_PENDING = "pending"
RESULT_UNAVAILABLE = "unavailable"
RESULT_INVALID = "invalid"


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _iso(dt: datetime | None) -> str | None:
    dt = _utc(dt)
    return dt.isoformat() if dt is not None else None


def replay_result_state(
    direction: str | None,
    entry_midpoint: float | None,
    fwd: ResearchForwardRow | None,
) -> str:
    """Server-side result truth for one directional call at one horizon (prompt section 11).

    - ``invalid``: the entry carries no directional call (should not appear in the directional
      table, guarded for completeness).
    - ``pending``: no forward observation stored yet (horizon not due, or not yet collected).
    - ``unavailable``: an observation exists but has no usable midpoint (a stored unavailable row),
      or the frozen entry midpoint is missing.
    - ``moved_expected`` / ``moved_against`` / ``no_change``: the midpoint moved in / against the
      stored direction, or did not move at all (``|move| <= REPLAY_MOVE_EPS``).
    """
    if direction not in ("up", "down"):
        return RESULT_INVALID
    if fwd is None:
        return RESULT_PENDING
    if fwd.midpoint is None or entry_midpoint is None:
        return RESULT_UNAVAILABLE
    move = fwd.midpoint - entry_midpoint
    if abs(move) <= REPLAY_MOVE_EPS:
        return RESULT_NO_CHANGE
    return RESULT_EXPECTED if ((move > 0) == (direction == "up")) else RESULT_AGAINST


@dataclass
class _Counts:
    total: int = 0
    moved_expected: int = 0
    moved_against: int = 0
    no_change: int = 0
    pending: int = 0
    unavailable: int = 0
    invalid: int = 0

    def add(self, state: str) -> None:
        self.total += 1
        setattr(self, state, getattr(self, state) + 1)

    @property
    def moved(self) -> int:
        return self.moved_expected + self.moved_against

    @property
    def evaluated(self) -> int:
        """Observations with a usable midpoint (moved either way or explicitly flat)."""
        return self.moved_expected + self.moved_against + self.no_change

    def to_dict(self) -> dict:
        moved = self.moved
        return {
            "total": self.total,
            "moved_expected": self.moved_expected,
            "moved_against": self.moved_against,
            "no_change": self.no_change,
            "pending": self.pending,
            "unavailable": self.unavailable,
            "invalid": self.invalid,
            "moved": moved,
            "evaluated": self.evaluated,
            # Movement coverage: share of directional calls with a usable observation at this
            # horizon. NOT a hit rate.
            "movement_coverage": (self.evaluated / self.total) if self.total else None,
            # Hit rate is shown ONLY among markets that moved, and is labelled as such by the UI so
            # a flat market is never scored as a miss and never inflates or deflates the rate.
            "hit_rate_among_moved": (self.moved_expected / moved) if moved else None,
        }


class ResearchReplayService:
    """Read-only Replay queries over the real prospective research cohorts."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ResearchRepository(session)

    async def _selectable_cohorts(self) -> list[ResearchCohortRow]:
        """Real, frozen, prospective cohorts a user may select, newest first.

        Excessively-late cohorts are excluded (prompt section 10: keep excluding only cohorts that
        breach the existing excessive-lateness rule), matching the performance surface so the Replay
        product never shows a run that is not a genuine scheduled prediction.
        """
        cohorts = await self.repo.list_cohorts(provenance="prospective", frozen=True)
        return [c for c in cohorts if not c.excessively_late]

    async def _available_horizons(self, entries: list[ResearchEntryRow]) -> dict[str, bool]:
        """Which horizons have at least one stored forward observation with a usable midpoint."""
        available = {h: False for h in REPLAY_HORIZONS}
        for e in entries:
            fwd = await self.repo.get_forward(e.id)
            for h in REPLAY_HORIZONS:
                row = fwd.get(h)
                if row is not None and row.midpoint is not None:
                    available[h] = True
        return available

    async def _resolution_available(self, entries: list[ResearchEntryRow]) -> bool:
        ids = {e.market_id for e in entries}
        if not ids:
            return False
        res = await self.session.execute(
            select(MarketResolutionRow.market_id).where(
                MarketResolutionRow.market_id.in_(ids),
                MarketResolutionRow.resolved.is_(True),
            )
        )
        return res.first() is not None

    async def _cohort_summary(self, c: ResearchCohortRow, *, with_horizons: bool) -> dict:
        entries = await self.repo.get_entries(c.id) if with_horizons else []
        horizons = await self._available_horizons(entries) if with_horizons else {}
        resolution = await self._resolution_available(entries) if with_horizons else False
        return {
            "id": c.id,
            "cadence": c.cadence,
            "cadence_label": CADENCE_LABELS.get(c.cadence, c.cadence),
            "cadence_description": CADENCE_DESCRIPTIONS.get(
                c.cadence, f"a cohort frozen at the {c.cadence} cut-off"
            ),
            "scheduled_for": _iso(c.cutoff_at),
            "frozen_at": _iso(c.frozen_at),
            "evaluation_origin_at": _iso(c.evaluation_origin_at),
            "lateness_seconds": round(c.lateness_seconds, 1),
            "lateness_minutes": round(c.lateness_seconds / 60.0, 1),
            "late": c.late,
            "excessively_late": c.excessively_late,
            "degraded": c.degraded,
            "universe_size": c.universe_size,
            "directional_count": c.directional_count,
            "public_selection_count": c.public_selection_count,
            "shadow_count": c.shadow_count,
            "observation_count": c.observation_count,
            "abstention_count": c.abstention_count,
            "excluded_markets": c.excluded_markets,
            "available_horizons": horizons,
            "resolution_available": resolution,
            "model_version": c.model_version or MODEL_VERSION,
        }

    async def list_cohorts(self) -> dict:
        """Available real prospective cohorts + a per-cadence summary (prompt sections 2, 11)."""
        cohorts = await self._selectable_cohorts()
        summaries = [await self._cohort_summary(c, with_horizons=True) for c in cohorts]

        cadences: list[dict] = []
        for cad in ("6h", "daily", "weekly"):
            members = [s for s in summaries if s["cadence"] == cad]
            if not members:
                continue
            cadences.append({
                "cadence": cad,
                "label": CADENCE_LABELS.get(cad, cad),
                "description": CADENCE_DESCRIPTIONS.get(cad, ""),
                "count": len(members),
                "newest_cohort_id": members[0]["id"],  # summaries are newest-first
            })

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "model_version": MODEL_VERSION,
            "cohorts": summaries,
            "cadences": cadences,
            # The clearest default: the single newest real cohort (prompt section 2).
            "default_cohort_id": summaries[0]["id"] if summaries else None,
            "has_prospective": bool(summaries),
            "first_freeze": (
                min((s["frozen_at"] for s in summaries if s["frozen_at"]), default=None)
            ),
            "latest_freeze": (
                max((s["frozen_at"] for s in summaries if s["frozen_at"]), default=None)
            ),
            "note": (
                "Prospective cohorts contain real signals permanently recorded at a six-hourly, "
                "daily or weekly cut-off. Outcomes are measured from the actual freeze time. "
                "Replay grows when scheduled backend jobs freeze cohorts and collect later "
                "prices; leaving this page open does not collect additional evidence."
            ),
        }

    def _directional_entries(
        self, entries: list[ResearchEntryRow], scope: str, max_hours: float | None
    ) -> list[ResearchEntryRow]:
        """Directional entries for the scope + closing window, ordered by FROZEN rank.

        Filtering uses the frozen ``time_remaining_hours`` only (prompt section 4); the stored rank
        is never recomputed (prompt section 5).
        """
        roles = (ROLE_PUBLIC,) if scope == SCOPE_PUBLIC else (ROLE_PUBLIC, ROLE_SHADOW)
        out = [
            e for e in entries
            if e.role in roles and e.direction in ("up", "down")
        ]
        if max_hours is not None:
            out = [
                e for e in out
                if e.time_remaining_hours is not None and e.time_remaining_hours <= max_hours
            ]
        out.sort(key=lambda e: (e.rank is None, e.rank if e.rank is not None else 1 << 30, e.id))
        return out

    async def _resolution_map(
        self, entries: list[ResearchEntryRow]
    ) -> dict[str, MarketResolutionRow]:
        ids = {e.market_id for e in entries}
        if not ids:
            return {}
        res = await self.session.execute(
            select(MarketResolutionRow).where(MarketResolutionRow.market_id.in_(ids))
        )
        return {r.market_id: r for r in res.scalars().all()}

    def _row_resolution(
        self, e: ResearchEntryRow, resolutions: dict[str, MarketResolutionRow]
    ) -> dict:
        """Per-entry FINAL resolution, kept separate from short-term movement (prompt section 3)."""
        r = resolutions.get(e.market_id)
        if r is None or not r.resolved:
            return {"resolved": False, "resolved_outcome": None, "correct": None}
        correct = (
            (r.resolved_token_id == e.token_id) if r.resolved_token_id is not None else None
        )
        return {
            "resolved": True,
            "resolved_outcome": r.resolved_outcome,
            "correct": correct,
        }

    async def _evolution_for(self, e: ResearchEntryRow) -> dict:
        """Later signal evolution (prompt C8): the market's CURRENT stored signal vs its frozen
        signal, from the latest complete-scan snapshot. Diagnostic only; never rewrites frozen
        fields."""
        res = await self.session.execute(
            select(SignalSnapshotRow)
            .where(SignalSnapshotRow.market_id == e.market_id)
            .order_by(SignalSnapshotRow.captured_at.desc())
            .limit(1)
        )
        snap = res.scalar_one_or_none()
        if snap is None:
            return {"available": False, "state": "no later scan"}
        strength_change = round((snap.strength or 0.0) - (e.strength or 0.0), 4)
        reversed_dir = bool(
            e.direction in ("up", "down") and snap.direction in ("up", "down")
            and e.direction != snap.direction
        )
        if reversed_dir:
            label = "Direction reversed"
        elif strength_change > 0.02:
            label = "Strengthening"
        elif strength_change < -0.02:
            label = "Weakening"
        else:
            label = "Stable"
        return {
            "available": True,
            "label": label,
            "frozen_strength": e.strength,
            "later_strength": snap.strength,
            "strength_change": strength_change,
            "frozen_direction": e.direction,
            "later_direction": snap.direction,
            "direction_reversed": reversed_dir,
            "research_priority_change": (snap.research_priority or 0) - (e.research_priority or 0),
            "later_rank_in_bucket": snap.rank_in_bucket,
            "captured_at": snap.captured_at.isoformat() if snap.captured_at else None,
        }

    async def _entry_row(
        self, e: ResearchEntryRow, horizon: str,
        resolutions: dict[str, MarketResolutionRow] | None = None,
        preclose_map: dict | None = None,
    ) -> dict:
        fwd = (await self.repo.get_forward(e.id)).get(horizon)
        state = replay_result_state(e.direction, e.midpoint, fwd)
        forward_mid = fwd.midpoint if fwd is not None else None
        # Raw signed midpoint movement in percentage points (display in the market's own terms).
        movement_pp = None
        midpoint_move = None  # signed in the stored direction (probability points)
        if forward_mid is not None and e.midpoint is not None:
            raw = forward_mid - e.midpoint
            movement_pp = round(raw * 100.0, 2)
            sign = 1.0 if e.direction == "up" else -1.0
            midpoint_move = round(sign * raw, 4)

        # Executable result (after spread + depth-aware slippage + fees), shown SEPARATELY from the
        # midpoint move and never invented when depth/spread inputs are missing (prompt section 8).
        exe = evaluate_execution(
            direction=e.direction,
            entry_midpoint=e.midpoint,
            forward_midpoint=forward_mid,
            entry_spread=e.spread,
            entry_depth=e.near_mid_depth,
            forward_spread=(fwd.spread if fwd is not None else None),
            forward_depth=(fwd.near_mid_depth if fwd is not None else None),
        )
        executable = {
            "available": exe.executable_move is not None,
            "move": round(exe.executable_move, 4) if exe.executable_move is not None else None,
            "round_trip_cost": (
                round(exe.round_trip_cost, 4) if exe.round_trip_cost is not None else None
            ),
            "unavailable_reason": exe.unavailable_reason,
        }

        return {
            "rank": e.rank,
            "market_id": e.market_id,
            "condition_id": e.condition_id,
            "token_id": e.token_id,
            "market_question": e.market_question,
            "outcome_name": e.outcome_name,
            "role": e.role,
            "direction": e.direction,
            "frozen_midpoint": e.midpoint,
            "horizon_midpoint": forward_mid,
            "movement_pp": movement_pp,
            "midpoint_move": midpoint_move,
            "executable": executable,
            "time_remaining_hours": e.time_remaining_hours,
            "result_state": state,
            "resolution": self._row_resolution(e, resolutions or {}),
            # Separate panels (prompt C7): freeze-to-close and later signal evolution never mix into
            # the short-term movement result.
            "freeze_to_close": freeze_to_close_result(e, (preclose_map or {}).get(e.id)),
            "evolution": await self._evolution_for(e),
            "strength": e.strength,
            "confidence": e.confidence,
            "research_priority": e.research_priority,
        }

    async def _breakdown(
        self, entries: list[ResearchEntryRow], horizon: str
    ) -> _Counts:
        counts = _Counts()
        for e in entries:
            fwd = (await self.repo.get_forward(e.id)).get(horizon)
            counts.add(replay_result_state(e.direction, e.midpoint, fwd))
        return counts

    async def _resolution_summary(self, entries: list[ResearchEntryRow]) -> dict:
        """Final-resolution counts, kept strictly separate from short-term movement."""
        ids = {e.market_id for e in entries}
        rows: dict[str, MarketResolutionRow] = {}
        if ids:
            res = await self.session.execute(
                select(MarketResolutionRow).where(MarketResolutionRow.market_id.in_(ids))
            )
            rows = {r.market_id: r for r in res.scalars().all()}
        resolved_correct = resolved_incorrect = unresolved = 0
        for e in entries:
            r = rows.get(e.market_id)
            if r is None or not r.resolved:
                unresolved += 1
                continue
            # Correct only when the market finally resolved to the entry's selected outcome token.
            if r.resolved_token_id is not None and r.resolved_token_id == e.token_id:
                resolved_correct += 1
            else:
                resolved_incorrect += 1
        return {
            "resolved_correct": resolved_correct,
            "resolved_incorrect": resolved_incorrect,
            "unresolved": unresolved,
            "total": len(entries),
        }

    async def cohort_results(
        self, cohort_id: int, *, horizon: str = "6h",
        scope: str = SCOPE_DIRECTIONAL, closing: str = "all",
    ) -> dict:
        """Full Replay result set for one cohort + horizon + closing window + scope.

        Deterministic and idempotent: a read never mutates a frozen entry or its observations.
        """
        if horizon not in REPLAY_HORIZONS:
            horizon = "6h"
        if scope not in (SCOPE_PUBLIC, SCOPE_DIRECTIONAL):
            scope = SCOPE_DIRECTIONAL
        if closing not in CLOSING_FILTERS:
            closing = "all"
        max_hours = CLOSING_FILTERS[closing]

        cohort = await self.session.get(ResearchCohortRow, cohort_id)
        if (
            cohort is None or not cohort.frozen
            or cohort.provenance_class != "prospective" or cohort.excessively_late
        ):
            return {"found": False, "cohort_id": cohort_id}

        all_entries = await self.repo.get_entries(cohort.id)

        # Directional sets. Public and shadow breakdowns are computed over the closing-filtered set
        # (scope-independent) so the "did the market move as expected?" section always shows the
        # public, shadow and combined split (prompt section 6). The table and the headline follow
        # the selected scope (prompt section 5).
        all_directional = self._directional_entries(all_entries, SCOPE_DIRECTIONAL, max_hours)
        public_entries = [e for e in all_directional if e.role == ROLE_PUBLIC]
        shadow_entries = [e for e in all_directional if e.role == ROLE_SHADOW]
        scoped = public_entries if scope == SCOPE_PUBLIC else all_directional

        # Top twenty by frozen rank within the scoped + filtered subset. Never padded.
        shown = scoped[:20]
        resolutions = await self._resolution_map(shown)
        preclose_map = await preclose_for_cohort(self.session, cohort.id)
        rows = [
            await self._entry_row(e, horizon, resolutions, preclose_map) for e in shown
        ]

        # Freeze-to-close aggregate (prompt C4/C7), over the scoped directional set.
        f2c = {"moved_expected": 0, "moved_against": 0, "no_change": 0,
               "closed_final": 0, "pending": 0}
        for e in scoped:
            r = freeze_to_close_result(e, preclose_map.get(e.id))
            if r["result"] == "moved_expected":
                f2c["moved_expected"] += 1
            elif r["result"] == "moved_against":
                f2c["moved_against"] += 1
            elif r["result"] == "no_change":
                f2c["no_change"] += 1
            if r.get("closed"):
                f2c["closed_final"] += 1
            if r["state"] == "pending":
                f2c["pending"] += 1

        # Honest denominators (prompt C6): repeated 5-minute snapshots are not predictions; a market
        # can appear in several cohorts, so expose unique-market and unique-event counts.
        unique_markets = len({e.market_id for e in scoped})
        unique_events = len({e.event_id for e in scoped if e.event_id})
        repeated_markets = len(scoped) - unique_markets

        headline = (await self._breakdown(scoped, horizon)).to_dict()
        public = (await self._breakdown(public_entries, horizon)).to_dict()
        shadow = (await self._breakdown(shadow_entries, horizon)).to_dict()
        combined = (await self._breakdown(all_directional, horizon)).to_dict()

        # Non-directional role counts stay in the methodology summary, never in the result table.
        role_counts: dict[str, int] = {}
        for e in all_entries:
            role_counts[e.role] = role_counts.get(e.role, 0) + 1

        resolution = await self._resolution_summary(scoped)
        available_horizons = await self._available_horizons(all_entries)

        return {
            "found": True,
            "cohort": await self._cohort_summary(cohort, with_horizons=False),
            "horizon": horizon,
            "horizon_evaluable": available_horizons.get(horizon, False),
            "available_horizons": available_horizons,
            "resolution_available": await self._resolution_available(all_entries),
            "scope": scope,
            "closing": closing,
            "closing_max_hours": max_hours,
            "qualifying": len(scoped),
            "shown": len(shown),
            "rows": rows,
            "headline": headline,
            "public": public,
            "shadow": shadow,
            "combined": combined,
            "role_counts": role_counts,
            "resolution": resolution,
            "freeze_to_close": f2c,
            "denominators": {
                "observations": len(scoped),
                "unique_markets": unique_markets,
                "unique_events": unique_events,
                "repeated_markets": repeated_markets,
            },
            "selection_policy": cohort.selection_policy,
            "public_selection_limit": cohort.public_selection_limit,
            "note": (
                "Movement asks whether the selected outcome's midpoint moved in Arepo's stored "
                "direction over the horizon, measured from the actual freeze time. It is not a "
                "claim of profit and not a final-outcome forecast; flat markets stay in the "
                "denominator "
                "and are never scored as misses."
            ),
        }
