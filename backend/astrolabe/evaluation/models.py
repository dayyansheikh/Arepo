"""SQLAlchemy ORM tables for the prospective cohort evaluation system.

They share ``storage.db.Base.metadata`` so a single ``create_all`` / migration builds
them alongside the cache tables, and only portable column types are used
(String/Integer/Float/Boolean/JSON/DateTime(timezone=True)) so Postgres works
unchanged. Immutability of frozen cohorts is enforced in ``repository.py`` (guards on
``weekly_cohorts.frozen``), and uniqueness constraints below make the scheduler
commands idempotent and prevent duplicate slots/observations.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..storage.db import Base


class CalculationVersionRow(Base):
    """The analytics version that produced a snapshot, kept for provenance."""

    __tablename__ = "calculation_versions"

    version: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignalSnapshotRow(Base):
    """An immutable record of one signal exactly as computed at ``captured_at``.

    This is the provenance layer: selection reads snapshots, never live analytics, so a
    frozen cohort can always be traced to the precise inputs that produced it.
    """

    __tablename__ = "signal_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_ref", name="uq_snapshot_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Stable hash of (market, token, captured_at, calculation_version): dedupes re-ingest.
    snapshot_ref: Mapped[str] = mapped_column(String, nullable=False)
    calculation_version: Mapped[str] = mapped_column(
        String, ForeignKey("calculation_versions.version"), nullable=False
    )

    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    market_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    condition_id: Mapped[str | None] = mapped_column(String)
    event_id: Mapped[str | None] = mapped_column(String)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    market_question: Mapped[str] = mapped_column(String, nullable=False, default="")
    outcome_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    direction: Mapped[str | None] = mapped_column(String)

    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    data_quality: Mapped[str] = mapped_column(String, nullable=False, default="good")
    value: Mapped[float | None] = mapped_column(Float)  # headline magnitude (e.g. z-score)

    entry_price: Mapped[float | None] = mapped_column(Float)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    midpoint: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    near_mid_depth: Mapped[float | None] = mapped_column(Float)
    lookback_size: Mapped[int | None] = mapped_column(Integer)

    component_scores: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_close: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WeeklyCohortRow(Base):
    """One calendar week's cohort. Immutable once ``frozen``."""

    __tablename__ = "weekly_cohorts"
    __table_args__ = (UniqueConstraint("iso_year", "iso_week", name="uq_cohort_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso_year: Mapped[int] = mapped_column(Integer, nullable=False)
    iso_week: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    calculation_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    provenance_class: Mapped[str] = mapped_column(
        String, nullable=False, default="prospective"
    )
    target_size: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    actual_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CohortEntryRow(Base):
    """A selected signal in a cohort. A denormalised, frozen copy of its snapshot so a
    later snapshot re-ingest can never alter an entry's original scores or prices."""

    __tablename__ = "cohort_entries"
    __table_args__ = (
        UniqueConstraint("cohort_id", "market_id", "token_id", name="uq_entry_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("weekly_cohorts.id"), index=True, nullable=False
    )
    snapshot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("signal_snapshots.id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    market_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    condition_id: Mapped[str | None] = mapped_column(String)
    event_id: Mapped[str | None] = mapped_column(String)
    market_question: Mapped[str] = mapped_column(String, nullable=False, default="")
    outcome_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    direction: Mapped[str | None] = mapped_column(String)

    entry_price: Mapped[float | None] = mapped_column(Float)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    midpoint: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    near_mid_depth: Mapped[float | None] = mapped_column(Float)
    lookback_size: Mapped[int | None] = mapped_column(Integer)

    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    data_quality: Mapped[str] = mapped_column(String, nullable=False, default="good")
    value: Mapped[float | None] = mapped_column(Float)
    component_scores: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    signal_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_close: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RankingAuditRow(Base):
    """Append-only log of every provisional change to a cohort before it froze."""

    __tablename__ = "ranking_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("weekly_cohorts.id"), index=True, nullable=False
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # enter | replace | skip
    snapshot_id: Mapped[int | None] = mapped_column(Integer)
    replaced_snapshot_id: Mapped[int | None] = mapped_column(Integer)
    rank: Mapped[int | None] = mapped_column(Integer)
    strength: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str] = mapped_column(String, nullable=False, default="")


class ForwardPriceObservationRow(Base):
    """A price captured a fixed horizon after freeze. Unique per (entry, horizon)."""

    __tablename__ = "forward_price_observations"
    __table_args__ = (
        UniqueConstraint("entry_id", "horizon", name="uq_forward_obs"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cohort_entries.id"), index=True, nullable=False
    )
    horizon: Mapped[str] = mapped_column(String, nullable=False)  # 1h | 24h | 7d | close
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[float | None] = mapped_column(Float)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketResolutionRow(Base):
    """Final resolution of a market. One row per market_id (upserted, never duplicated)."""

    __tablename__ = "market_resolutions"

    market_id: Mapped[str] = mapped_column(String, primary_key=True)
    condition_id: Mapped[str | None] = mapped_column(String)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_outcome: Mapped[str | None] = mapped_column(String)
    resolved_token_id: Mapped[str | None] = mapped_column(String)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationResultRow(Base):
    """Derived evaluation for one entry (recomputed idempotently). Keeps price-movement
    and final-resolution as distinct verdicts; never overwrites entry data."""

    __tablename__ = "evaluation_results"
    __table_args__ = (UniqueConstraint("entry_id", name="uq_eval_entry"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cohort_entries.id"), index=True, nullable=False
    )
    # Price-movement view (evaluated at 24h horizon when available).
    movement_horizon: Mapped[str | None] = mapped_column(String)
    raw_prob_movement: Mapped[float | None] = mapped_column(Float)
    movement_correct: Mapped[bool | None] = mapped_column(Boolean)
    # Final-resolution view.
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_correct: Mapped[bool | None] = mapped_column(Boolean)
    # Pending until at least one view can be decided.
    pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hypothetical_value: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
