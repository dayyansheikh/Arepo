"""ORM tables for the edge-research infrastructure (prompt sections 2-5, 10).

Additive to the existing weekly-cohort tables so no prior data or test is disturbed. Only portable
column types are used (String/Integer/Float/Boolean/JSON/DateTime(timezone=True)) so PostgreSQL runs
the same schema as local SQLite. Immutability of frozen cohorts is enforced in
``research_repository.py``; the unique constraints below make freezing idempotent and prevent
duplicate cohorts, entries and forward observations.

Design notes
- ``research_cohorts`` is keyed by (cadence, cutoff_at): one immutable cohort per cadence boundary.
- ``research_entries`` stores the FULL screened universe with an explicit role, not only the public
  top-N (prompt section 2), plus every field required at the cut-off (prompt section 4) including
  Research Priority, evidence families, component availability and the walk-forward partition.
- ``research_forward_observations`` stores rich forward repricing per (entry, horizon) including
  bid/ask/spread/depth, whether the observation was exact or nearest, the delay and any
  unavailable reason (prompt section 5). Final resolution reuses ``market_resolutions``.
- ``research_revisions`` is an append-only correction log so a frozen cohort is never silently
  mutated (prompt section 4).
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


class ResearchCohortRow(Base):
    """One immutable research cohort for a cadence boundary. Unique per (cadence, cutoff_at)."""

    __tablename__ = "research_cohorts"
    __table_args__ = (UniqueConstraint("cadence", "cutoff_at", name="uq_research_cohort"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cadence: Mapped[str] = mapped_column(String, nullable=False, index=True)  # 6h | daily | weekly
    # ``cutoff_at`` is the SCHEDULED cadence-boundary LABEL (the bucket key), NOT the causal origin.
    # Exposed to callers as ``scheduled_for``. The causal origin is ``evaluation_origin_at`` below.
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    model_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    calculation_version: Mapped[str] = mapped_column(String, nullable=False, default="")
    provenance_class: Mapped[str] = mapped_column(String, nullable=False, default="prospective")

    frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The CAUSAL ORIGIN of the prediction: equals frozen_at. Every forward horizon (1h/6h/24h/7d),
    # entry timestamp and time-to-close is measured from THIS, never from cutoff_at. Stored
    # explicitly so the meaning is unambiguous and a query cannot accidentally use the label.
    evaluation_origin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Lateness = frozen_at - cutoff_at (seconds). ``late`` flags a delay past the warn threshold;
    # ``excessively_late`` marks a run so far past its boundary that it is excluded from comparable
    # performance (still causally valid, just not a genuine scheduled prediction).
    lateness_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excessively_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Counts recorded at freeze so status queries are O(1) and match the stored entries.
    universe_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    directional_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    public_selection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shadow_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    abstention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Universe degradation (prompt section 5): how many discovered markets were excluded for lack of
    # usable point-in-time data, and whether the run was degraded (a high but sub-reject exclusion
    # rate). A rejected run creates NO cohort, so these describe only cohorts that did freeze.
    excluded_markets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Source complete-scan provenance + public selection policy (final-completion prompt C1/B2).
    # NULL on the pre-existing historical cohort (it predates complete scans); never rewritten.
    scan_id: Mapped[str | None] = mapped_column(String)
    scan_complete: Mapped[bool | None] = mapped_column(Boolean)
    selection_policy: Mapped[str | None] = mapped_column(String)
    public_selection_limit: Mapped[int | None] = mapped_column(Integer)

    note: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchEntryRow(Base):
    """One screened market/token frozen at the cut-off, with its role and full cut-off snapshot.

    Denormalised on purpose: a later snapshot re-ingest or price change can never alter a frozen
    entry's scores or prices. Unique per (cohort, market, token) so freezing is idempotent.
    """

    __tablename__ = "research_entries"
    __table_args__ = (
        UniqueConstraint("cohort_id", "market_id", "token_id", name="uq_research_entry"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_cohorts.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rank: Mapped[int | None] = mapped_column(Integer)  # among directional entries; None otherwise
    walk_forward_partition: Mapped[str] = mapped_column(String, nullable=False, default="live")

    # Canonical identity (prompt section 4, section 18 identifier integrity).
    market_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    condition_id: Mapped[str | None] = mapped_column(String)
    event_id: Mapped[str | None] = mapped_column(String)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    market_question: Mapped[str] = mapped_column(String, nullable=False, default="")
    outcome_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    # Causally copied from the source complete scan. NULL is retained for historical cohorts that
    # predate category preservation rather than reconstructing a category with future metadata.
    primary_category: Mapped[str | None] = mapped_column(String)

    # Model view at the cut-off.
    direction: Mapped[str | None] = mapped_column(String)
    # Per-family directional calls FROZEN at the cut-off so the baselines and feature ablation are
    # genuinely computable on prospective cohorts (prompt sections 8, 9): momentum = sign of the
    # latest-return z-score (Arepo's price signal), order book = sign of near-touch imbalance, trade
    # flow = sign of net aggressive flow. Each is up | down | None.
    momentum_direction: Mapped[str | None] = mapped_column(String)
    orderbook_direction: Mapped[str | None] = mapped_column(String)
    tradeflow_direction: Mapped[str | None] = mapped_column(String)
    signal_classification: Mapped[str] = mapped_column(String, nullable=False, default="")
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # reliability
    research_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
    n_families: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_families: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    component_scores: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    component_availability: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data_quality: Mapped[str] = mapped_column(String, nullable=False, default="good")

    # Microstructure + execution inputs at the cut-off.
    entry_price: Mapped[float | None] = mapped_column(Float)   # midpoint entry
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    midpoint: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    near_mid_depth: Mapped[float | None] = mapped_column(Float)
    liquidity: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    data_age_seconds: Mapped[float | None] = mapped_column(Float)

    # Timing.
    expected_close: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_remaining_hours: Mapped[float | None] = mapped_column(Float)
    intended_horizons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Short-horizon universe membership frozen at the cut-off (final-completion prompt C1).
    # NULL on the pre-existing historical cohort; never rewritten.
    bucket: Mapped[str | None] = mapped_column(String, index=True)
    overall_rank_30d: Mapped[int | None] = mapped_column(Integer)
    public_selected: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchForwardRow(Base):
    """Rich forward repricing observation per (entry, horizon). Unique per (entry, horizon)."""

    __tablename__ = "research_forward_observations"
    __table_args__ = (
        UniqueConstraint("entry_id", "horizon", name="uq_research_forward"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_entries.id"), index=True, nullable=False
    )
    horizon: Mapped[str] = mapped_column(String, nullable=False)  # 1h | 6h | 24h | 7d
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    midpoint: Mapped[float | None] = mapped_column(Float)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    near_mid_depth: Mapped[float | None] = mapped_column(Float)

    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observation_delay_seconds: Mapped[float | None] = mapped_column(Float)
    unavailable_reason: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchPreCloseRow(Base):
    """Freeze-to-close tracking for one entry (final-completion prompt C4).

    One mutable row per entry that accumulates valid quotes over the market's REMAINING lifetime:
    the first valid post-freeze observation and the latest valid quote at or before close. Once the
    close time passes the row is marked ``closed`` and the last valid quote becomes the final
    pre-close price; quotes observed at or after close are rejected and never overwrite it. Final
    resolution is never inferred from price here.
    """

    __tablename__ = "research_preclose_observations"
    __table_args__ = (UniqueConstraint("entry_id", name="uq_research_preclose"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_entries.id"), index=True, nullable=False
    )
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    first_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_midpoint: Mapped[float | None] = mapped_column(Float)

    last_valid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_midpoint: Mapped[float | None] = mapped_column(Float)
    last_best_bid: Mapped[float | None] = mapped_column(Float)
    last_best_ask: Mapped[float | None] = mapped_column(Float)
    last_spread: Mapped[float | None] = mapped_column(Float)
    last_near_mid_depth: Mapped[float | None] = mapped_column(Float)
    last_source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    closed_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unavailable_reason: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchRevisionRow(Base):
    """Append-only correction log: a frozen cohort is never silently mutated (prompt section 4)."""

    __tablename__ = "research_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_cohorts.id"), index=True, nullable=False
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False, default="")
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
