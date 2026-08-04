"""Prospective cohort evaluation endpoints.

Typed, backend-computed responses so the frontend never derives evaluation truth from
client state. Read-only: the weekly ranking/freeze/forward/resolve operations run via the
scheduler CLI (see astrolabe.evaluation.cli), not through the API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...evaluation.schemas import CohortDetail, CohortWeek, ProvenanceOut
from ...evaluation.service import CohortReadService
from ...storage.db import get_session

router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])


@router.get("/weeks", response_model=list[CohortWeek])
async def weeks(session: AsyncSession = Depends(get_session)) -> list[CohortWeek]:
    """Available cohort weeks, newest first."""
    return await CohortReadService(session).available_weeks()


@router.get("/provenance", response_model=ProvenanceOut)
async def provenance(session: AsyncSession = Depends(get_session)) -> ProvenanceOut:
    """Data provenance: when prospective tracking began and how classes are separated."""
    return await CohortReadService(session).provenance()


@router.get("/latest", response_model=CohortDetail)
async def latest(session: AsyncSession = Depends(get_session)) -> CohortDetail:
    """The most recent REAL cohort's summary, entries and portfolio simulation.

    Synthetic demonstration cohorts are never served here: "latest" must never surface demo data
    as if it were the current prospective record (spec §8, adversarial review F#6). Only prospective
    (and, if ever stored, reconstructed) cohorts qualify; when none exist yet this 404s honestly.
    """
    svc = CohortReadService(session)
    weeks_list = await svc.available_weeks()
    real = [w for w in weeks_list if w.provenance_class != "synthetic"]
    if not real:
        raise HTTPException(
            status_code=404,
            detail="No real cohorts recorded yet. Prospective tracking begins at the first "
            "weekly freeze; only a synthetic demonstration cohort exists so far.",
        )
    w = real[0]
    detail = await svc.cohort_detail(w.iso_year, w.iso_week)
    if detail is None:
        raise HTTPException(status_code=404, detail="Cohort not found.")
    return detail


@router.get("/{iso_year}/{iso_week}", response_model=CohortDetail)
async def cohort(
    iso_year: int, iso_week: int, session: AsyncSession = Depends(get_session)
) -> CohortDetail:
    """One week's summary, entries (frozen selection + forward tracking) and portfolio."""
    detail = await CohortReadService(session).cohort_detail(iso_year, iso_week)
    if detail is None:
        raise HTTPException(status_code=404, detail="Cohort not found.")
    return detail
