"""Lightweight, idempotent schema bootstrap for the evaluation tables.

The project uses SQLAlchemy ``create_all`` rather than Alembic; this module is the single
documented entry point that (a) imports the evaluation ORM so the tables are registered on
the shared metadata, (b) creates any missing tables (``create_all`` skips existing ones),
and (c) records the current calculation version. Safe to run repeatedly.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from ..config import get_settings
from ..storage.db import make_engine, make_sessionmaker
from ..storage.migrate import preflight, upgrade
from . import models as _models  # noqa: F401  (registers tables on Base.metadata)
from . import research_models as _research_models  # noqa: F401  (registers research tables)
from .constants import CALCULATION_VERSION
from .repository import EvaluationRepository


async def bootstrap(engine: AsyncEngine | None = None) -> None:
    """Bring the schema fully up to date (create tables AND add any missing columns) and ensure the
    calculation-version row. Idempotent.

    This replaces the old bare ``create_all`` so an existing table that gained columns in code (the
    ``research_entries.momentum_direction`` failure) is actually ALTERed. With
    ``AUTO_MIGRATE=false``
    it instead runs the preflight, which fails fast with an actionable message rather than letting a
    missing-column error surface halfway through a cohort freeze.
    """
    eng = engine or make_engine()
    if get_settings().auto_migrate:
        await upgrade(eng)
    else:
        await preflight(eng, auto_migrate=False)
    sessionmaker = make_sessionmaker(eng)
    async with sessionmaker() as session:
        await EvaluationRepository(session).ensure_calculation_version(
            CALCULATION_VERSION, "Arepo composite anomaly v1"
        )
        await session.commit()
