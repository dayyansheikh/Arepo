"""ORM tables for the Lab dashboard (additive; one snapshot row per source, bounded command log)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..domain.models import utcnow
from ..storage.db import Base


class LabSnapshot(Base):
    __tablename__ = "lab_snapshots"

    source: Mapped[str] = mapped_column(String, primary_key=True)  # "host" | "mac"
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON text
    payload_sha256: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)


class LabCommand(Base):
    __tablename__ = "lab_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String, nullable=False, index=True)  # queue | autopilot
    action: Mapped[str] = mapped_column(String, nullable=False)  # pause | resume
    # pending -> delivered -> done | failed ; pending -> expired
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
