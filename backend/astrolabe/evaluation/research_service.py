"""Read + aggregation layer for the research status surface (prompt sections 13, 14).

Turns the stored research rows into the real numbers the status API reports: cohort counts by
cadence, role and horizon coverage, per-horizon baseline and ablation tables computed on the frozen
observations, the calibration status and the edge verdict. Every number comes from stored rows;
nothing is synthetic and nothing is fabricated. When no real prospective evidence exists yet the
status says so honestly rather than hiding behind reconstructed or synthetic numbers.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from ..ingest.microstructure_store import MicrostructureSnapshotRow
from .models import MarketResolutionRow
from .research_analysis import HorizonObs, ablation_table, baseline_table, edge_verdict
from .research_calibration import calibration_status
from .research_constants import (
    CADENCES,
    MODEL_VERSION,
    RESEARCH_HORIZONS,
)
from .research_models import ResearchCohortRow, ResearchEntryRow, ResearchForwardRow
from .research_predictors import EntryView
from .research_repository import ResearchRepository


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _entry_view(e: ResearchEntryRow) -> EntryView:
    return EntryView(
        direction=e.direction, momentum_direction=e.momentum_direction,
        orderbook_direction=e.orderbook_direction, tradeflow_direction=e.tradeflow_direction,
        entry_price=e.entry_price, evidence_families=tuple(e.evidence_families or ()),
    )


def _obs_for_horizon(e: ResearchEntryRow, fwd: ResearchForwardRow | None) -> HorizonObs:
    return HorizonObs(
        entry=_entry_view(e),
        entry_midpoint=e.midpoint, entry_spread=e.spread, entry_depth=e.near_mid_depth,
        forward_midpoint=(fwd.midpoint if fwd else None),
        forward_spread=(fwd.spread if fwd else None),
        forward_depth=(fwd.near_mid_depth if fwd else None),
    )


class ResearchReadService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ResearchRepository(session)

    async def _frozen_entries(self) -> list[tuple[ResearchCohortRow, ResearchEntryRow]]:
        out = []
        for cohort in await self.repo.list_cohorts(provenance="prospective", frozen=True):
            for e in await self.repo.get_entries(cohort.id):
                out.append((cohort, e))
        return out

    async def horizon_analysis(self, horizon: str) -> dict:
        """Baseline + ablation tables for one horizon over ALL frozen prospective entries that have
        a forward observation there. Directional entries only (role public/shadow)."""
        obs: list[HorizonObs] = []
        for _cohort, e in await self._frozen_entries():
            if e.direction not in ("up", "down"):
                continue
            fwd = (await self.repo.get_forward(e.id)).get(horizon)
            if fwd is None or fwd.midpoint is None:
                continue
            obs.append(_obs_for_horizon(e, fwd))
        bt = baseline_table(obs)
        return {
            "horizon": horizon,
            "evaluable": len(obs),
            "baselines": bt["baselines"],
            "arepo_momentum_agreement": bt["arepo_momentum_agreement"],
            "probabilistic_metrics_note": bt["probabilistic_metrics_note"],
            "ablation": ablation_table(obs),
        }

    async def status(self) -> dict:
        """The full research-status object (prompt section 13) from real stored rows."""
        now = utcnow()
        cadence_counts = await self.repo.count_cohorts_by_cadence()
        entries = await self._frozen_entries()
        total_universe = len(entries)
        by_role: dict[str, int] = {}
        for _c, e in entries:
            by_role[e.role] = by_role.get(e.role, 0) + 1

        # Horizon coverage: due, evaluable (have a midpoint), flat/pending.
        horizon_cov: dict[str, dict] = {}
        for horizon in RESEARCH_HORIZONS:
            evaluable = pending = 0
            for _c, e in entries:
                fwd = (await self.repo.get_forward(e.id)).get(horizon)
                if fwd is not None and fwd.midpoint is not None:
                    evaluable += 1
                else:
                    pending += 1
            horizon_cov[horizon] = {"evaluable": evaluable, "pending": pending}

        cohorts = await self.repo.list_cohorts(provenance="prospective", frozen=True)
        oldest = min((_utc(c.cutoff_at) for c in cohorts), default=None)
        newest = max((_utc(c.cutoff_at) for c in cohorts), default=None)
        last_freeze = max((_utc(c.frozen_at) for c in cohorts if c.frozen_at), default=None)

        # Collector health from the microstructure snapshot store.
        snap_count = await self.session.scalar(
            select(func.count(MicrostructureSnapshotRow.id))
        ) or 0
        last_snap = _utc(await self.session.scalar(
            select(func.max(MicrostructureSnapshotRow.captured_at))
        ))
        resolved = await self.session.scalar(
            select(func.count(MarketResolutionRow.market_id)).where(
                MarketResolutionRow.resolved.is_(True)
            )
        ) or 0

        # Edge verdict on the 24h horizon (the primary repricing horizon).
        h24 = await self.horizon_analysis("24h")
        bl = h24["baselines"]
        empty = {"hit_rate": None, "ci95": [0.0, 1.0], "mean_executable_move": None}
        verdict = edge_verdict(
            evaluable_sample=h24["evaluable"],
            arepo=bl.get("full_arepo", empty), momentum=bl.get("momentum", empty),
            price_only=bl.get("price_z_only", empty), implied=bl.get("current_implied", empty),
            all_prospective=True, walk_forward_stable=None, ablation_beats_momentum=None,
            adversarial_passed=None,
        )
        cal = calibration_status(int(resolved))

        return {
            "generated_at": now.isoformat(),
            "model_version": MODEL_VERSION,
            "cohort_counts_by_cadence": {c: cadence_counts.get(c, 0) for c in CADENCES},
            "total_frozen_markets": total_universe,
            "roles": by_role,
            "directional_signals": (
                by_role.get("public_selection", 0) + by_role.get("shadow_directional", 0)
            ),
            "public_selections": by_role.get("public_selection", 0),
            "shadow_signals": by_role.get("shadow_directional", 0),
            "observations": by_role.get("observation", 0),
            "abstentions": by_role.get("abstention_control", 0),
            "horizon_coverage": horizon_cov,
            "resolved_markets": int(resolved),
            "oldest_cohort": oldest.isoformat() if oldest else None,
            "newest_cohort": newest.isoformat() if newest else None,
            "last_successful_freeze": last_freeze.isoformat() if last_freeze else None,
            "microstructure_snapshots": int(snap_count),
            "last_microstructure_collection": last_snap.isoformat() if last_snap else None,
            "collector_recent": bool(
                last_snap is not None and (now - last_snap).total_seconds() < 1800
            ),
            "calibration": {
                "available": cal.available, "resolved_sample": cal.resolved_sample,
                "minimum_required": cal.minimum_required, "message": cal.message,
            },
            "edge": {
                "edge_supported": verdict.edge_supported,
                "message": verdict.message,
                "criteria": verdict.criteria,
                "evaluable_sample_24h": verdict.evaluable_sample,
            },
            "note": (
                "All numbers are from real stored prospective rows. Synthetic and reconstructed "
                "data are excluded. Leaving the site open does not grow the sample; the backend "
                "freeze and forward-collection jobs do, over days and weeks."
            ),
        }
