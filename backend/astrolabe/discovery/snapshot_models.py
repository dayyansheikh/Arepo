"""Append-only ORM for complete-scan runs and per-market signal snapshots (prompt sections 7, 8).

Additive to the existing schema (created idempotently by the metadata-diff migrator). Nothing here
overwrites an earlier snapshot: a later refresh only INSERTS new ``signal_snapshots`` rows, keyed
uniquely by (scan_id, market_id, token_id). ``scan_runs`` is the immutable per-scan header carrying
the pagination-completeness proof and the discovery funnel, so a browser can read stored history and
never has to perform a scan itself. Only portable column types are used so Postgres runs the same
schema as SQLite.
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


class ScanRunRow(Base):
    """One complete (or attempted) discovery + analysis scan. Immutable once written."""

    __tablename__ = "discovery_scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Pagination completeness proof (prompt sections 2, 19).
    pagination_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pagination_reason: Mapped[str | None] = mapped_column(String)
    pages_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_markets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Discovery funnel + bucket counts (JSON blobs; also mirrored in columns for querying).
    funnel: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    eligible_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    directional: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bucket_counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    top_ten_counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Status (prompt section 7).
    # ok | partial | incomplete | failed
    status: Mapped[str] = mapped_column(String, nullable=False, default="ok")
    failure_reason: Mapped[str | None] = mapped_column(String)
    # Bounded-discovery completeness proof + reconciliation (prompt A5) and the public selection
    # policy in force for this scan (prompt B2).
    discovery: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    selection_policy: Mapped[str] = mapped_column(String, nullable=False, default="")
    public_selection_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    model_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    calculation_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    provenance: Mapped[str] = mapped_column(String, nullable=False, default="live_scan")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignalSnapshotRow(Base):
    """One analysed market/token at one scan. Append-only, unique per (scan, market, token)."""

    __tablename__ = "discovery_signal_snapshots"
    __table_args__ = (
        UniqueConstraint("scan_id", "market_id", "token_id", name="uq_signal_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(
        String, ForeignKey("discovery_scan_runs.scan_id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Identity.
    market_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    condition_id: Mapped[str | None] = mapped_column(String)
    event_id: Mapped[str | None] = mapped_column(String)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    market_question: Mapped[str] = mapped_column(String, nullable=False, default="")
    outcome_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    # Primary category classified once from point-in-time scan metadata. NULL means an older row
    # predating category preservation; it must never be backfilled from later live state.
    primary_category: Mapped[str | None] = mapped_column(String)

    # Timing + eligibility (point-in-time).
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_remaining_hours: Mapped[float | None] = mapped_column(Float)
    bucket: Mapped[str | None] = mapped_column(String, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String)

    # Signal (the existing model, unchanged; this is a history layer).
    direction: Mapped[str | None] = mapped_column(String)
    # Per-family frozen directions, so a cohort frozen FROM this scan can run the existing baselines
    # and ablations without re-deriving them (prompt C1 "frozen signal fields").
    momentum_direction: Mapped[str | None] = mapped_column(String)
    orderbook_direction: Mapped[str | None] = mapped_column(String)
    tradeflow_direction: Mapped[str | None] = mapped_column(String)
    signal_classification: Mapped[str] = mapped_column(String, nullable=False, default="")
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank_in_bucket: Mapped[int | None] = mapped_column(Integer)
    overall_rank_30d: Mapped[int | None] = mapped_column(Integer)
    # ``public_top_ten`` is the public-shortlist membership flag. Under selection policy
    # short-horizon-public-20-v1 the shortlist is the top 20; the column name is retained for
    # backward compatibility with earlier rows (prompt B2, no old-cohort rewrite).
    public_top_ten: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shadow_directional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selection_policy: Mapped[str] = mapped_column(String, nullable=False, default="")
    n_families: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_families: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    component_scores: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    component_availability: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data_quality: Mapped[str] = mapped_column(String, nullable=False, default="good")

    # Microstructure + execution inputs at the snapshot.
    midpoint: Mapped[float | None] = mapped_column(Float)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    near_mid_depth: Mapped[float | None] = mapped_column(Float)
    liquidity: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    data_age_seconds: Mapped[float | None] = mapped_column(Float)

    model_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    calculation_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    provenance: Mapped[str] = mapped_column(String, nullable=False, default="live_scan")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScanLockRow(Base):
    """A single-row advisory lease preventing overlapping scans (prompt section 7).

    One logical lock per ``name``. ``held_until`` is a lease expiry so a crashed scan's stale lock
    recoverable without manual intervention.
    """

    __tablename__ = "discovery_scan_locks"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    holder: Mapped[str] = mapped_column(String, nullable=False, default="")
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    held_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
