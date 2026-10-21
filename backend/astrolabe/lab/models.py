"""ORM tables for the Lab dashboard (additive; one snapshot row per source, bounded command and
message logs)."""
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
    # queue | autopilot | autopilot-<name>
    target: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # pause | resume | start (start: autopilot targets only)
    action: Mapped[str] = mapped_column(String, nullable=False)
    # pending -> delivered -> done | failed ; pending -> expired
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)


class LabMessage(Base):
    """Owner -> Claude autopilot message (Lab > Claude board). Additive table, SCHEMA_VERSION 17.

    Lifecycle: pending -> fetched (the Mac took it) -> delivered (appended to the instance's
    INBOX.md) -> read (the session moved INBOX.md away); pending -> cancelled (owner);
    pending|fetched -> failed (the Mac could not write it).
    Private: owner-only API, RLS enabled on Postgres. Bounded (latest 500 rows).
    """

    __tablename__ = "lab_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # autopilot | autopilot-<name>
    target: Mapped[str] = mapped_column(String, nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # <= 4,000 characters
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)


class LabAdminAudit(Base):
    """Append-only record of every owner action on a member account (Lab > Members).

    Private: owner-only API, RLS enabled on Postgres. When a member is deleted, every row naming
    them is rewritten to a masked email ("d***@gmail.com") and the delete row keeps only that mask
    plus the account_deletions SHA-256; no passwords, password hashes or tokens are stored.
    """

    __tablename__ = "lab_admin_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    actor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    target_email: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
