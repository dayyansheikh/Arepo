"""Scheduler bookkeeping ORM (additive; portable SQLite + Postgres).

Two tiny, bounded tables:

* ``scheduler_state`` — one UPSERT row per job name holding its last attempt/success/detail. Bounded
  (one row per job), so it never becomes category-C history; it powers both the "is this due?"
  decision and the production health snapshot.
* ``scheduler_leases`` — a single named lease so two overlapping runner invocations cannot both run
  the heavy tick at once. The loser exits cleanly.

Only portable column types are used, so the same DDL compiles for both dialects (the metadata-diff
migrator in ``storage/migrate.py`` creates these idempotently).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..storage.db import Base


class SchedulerStateRow(Base):
    """Last-run bookkeeping for one scheduler job (UPSERT keyed by ``job``)."""

    __tablename__ = "scheduler_state"

    job: Mapped[str] = mapped_column(String, primary_key=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_duration_seconds: Mapped[float | None] = mapped_column(Float)
    last_detail: Mapped[dict | None] = mapped_column(JSON)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SchedulerLeaseRow(Base):
    """A single named lease serialising heavy ticks across overlapping runner invocations."""

    __tablename__ = "scheduler_leases"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    holder: Mapped[str] = mapped_column(String, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    held_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
