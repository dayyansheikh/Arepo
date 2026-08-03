"""SQLAlchemy tables for the immutable daily Opportunity Board snapshot (spec section 9).

One snapshot per calendar date (UTC), written once and never rewritten: re-running the
generator for a date returns the existing snapshot unchanged. Tables share
``storage.db.Base.metadata`` and use only portable column types.
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..storage.db import Base


class OpportunitySnapshotRow(Base):
    """A day's frozen top-N board. One row per date; immutable once written."""

    __tablename__ = "opportunity_snapshots"

    snapshot_date: Mapped[date_type] = mapped_column(Date, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    data_mode: Mapped[str] = mapped_column(String, nullable=False, default="live")
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str] = mapped_column(String, nullable=False, default="")


class OpportunityEntryRow(Base):
    """One ranked market inside a daily snapshot (a frozen copy of its card)."""

    __tablename__ = "opportunity_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date_type] = mapped_column(
        Date, ForeignKey("opportunity_snapshots.snapshot_date"), index=True, nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False, default="")
    outcome: Mapped[str | None] = mapped_column(String)

    research_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    n_families: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_priority: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    families: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    probability: Mapped[float | None] = mapped_column(Float)
    relative_spread: Mapped[float | None] = mapped_column(Float)
    liquidity: Mapped[float | None] = mapped_column(Float)
    data_quality: Mapped[str] = mapped_column(String, nullable=False, default="good")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
