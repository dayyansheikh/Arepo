"""Alert history table (deduplication, per-market cooldown, audit)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..storage.db import Base


class AlertHistoryRow(Base):
    """One row per alert decision, kept for dedup/cooldown and as an audit trail."""

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    subject: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False)  # sent | test | failed | skipped_*
    detail: Mapped[str] = mapped_column(String, nullable=False, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
