"""SQLAlchemy ORM tables for the storage layer.

These are deliberately distinct from ``astrolabe.domain.models`` (the Pydantic domain
contract): ORM rows are a persistence detail, converted to/from domain models exclusively
in ``storage/repository.py``. Nothing outside this package should import from here.

Portability: only ``sqlalchemy.JSON`` (portable JSON across SQLite/Postgres) and generic
``DateTime(timezone=True)`` / ``Float`` / ``String`` / ``Boolean`` types are used — no
SQLite-only column types — so a Postgres ``database_url`` works without schema changes.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class MarketRow(Base):
    """Cached, normalized market metadata (mirrors ``domain.models.Market``)."""

    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, default="")
    condition_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    enable_order_book: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    category: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_24hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float | None] = mapped_column(Float, nullable=True)

    tick_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_order_size: Mapped[float | None] = mapped_column(Float, nullable=True)

    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    description: Mapped[str | None] = mapped_column(String, nullable=True)
    image: Mapped[str | None] = mapped_column(String, nullable=True)

    # list of {"name": str, "token_id": str, "price": float | None}
    outcomes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SnapshotRow(Base):
    """A time-series point-in-time snapshot of one token (mirrors ``MarketSnapshot``)."""

    __tablename__ = "snapshots"
    __table_args__ = (
        Index("ix_snapshots_token_captured", "token_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    token_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    market_id: Mapped[str] = mapped_column(
        String, ForeignKey("markets.id"), index=True, nullable=False
    )

    midpoint: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_trade_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)

    # {"bids": [[price, size], ...], "asks": [[price, size], ...]}
    book: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )


class SourceHealthRow(Base):
    """Per-source health/last-success (mirrors ``domain.models.SourceHealth``)."""

    __tablename__ = "source_health"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
