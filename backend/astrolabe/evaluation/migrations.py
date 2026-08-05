"""Lightweight, idempotent schema bootstrap for the evaluation tables.

The project uses SQLAlchemy ``create_all`` rather than Alembic; this module is the single
documented entry point that (a) imports the evaluation ORM so the tables are registered on
the shared metadata, (b) creates any missing tables (``create_all`` skips existing ones),
and (c) records the current calculation version. Safe to run repeatedly.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from ..storage.db import Base, make_engine, make_sessionmaker
from . import models as _models  # noqa: F401  (registers tables on Base.metadata)
from . import research_models as _research_models  # noqa: F401  (registers research tables)
from .constants import CALCULATION_VERSION
from .repository import EvaluationRepository


async def bootstrap(engine: AsyncEngine | None = None) -> None:
    """Create evaluation tables (idempotent) and ensure the calculation-version row."""
    eng = engine or make_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = make_sessionmaker(eng)
    async with sessionmaker() as session:
        await EvaluationRepository(session).ensure_calculation_version(
            CALCULATION_VERSION, "Arepo composite anomaly v1"
        )
        await session.commit()
