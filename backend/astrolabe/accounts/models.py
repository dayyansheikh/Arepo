"""Account ORM models (spec §10).

All tables live on the shared ``storage.db.Base`` metadata so they are created by the same
idempotent ``init_db`` / ``create_all`` bootstrap as the rest of the app, and so per-user data
can foreign-key to the same database the alert engine already uses. The ``User`` table is the
fastapi-users SQLAlchemy base (UUID primary key, hashed password, verification flags); we never
store plaintext passwords and never implement the hashing ourselves.

Per-user isolation is enforced in the API layer: every query for preferences, saved markets and
alert history is filtered by the authenticated user's id, so one user can never read another's
data. (There is no service-role bypass exposed to the browser.)
"""
from __future__ import annotations

from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..domain.models import utcnow
from ..storage.db import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """A registered user. Inherits id/email/hashed_password/is_active/is_superuser/is_verified.

    Extra columns capture the consent timestamp and the authentication provider (spec §10), and
    a creation timestamp for audit.
    """

    __tablename__ = "users"

    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String, nullable=False, default="local")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class AlertPreference(Base):
    """One row per user holding all alert preferences (spec §10). Sensible, quiet defaults."""

    __tablename__ = "alert_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    immediate_exceptional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    daily_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weekly_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_research_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    min_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.45)
    categories: Mapped[str] = mapped_column(String, nullable=False, default="")  # CSV, empty=all
    short_term_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_hours_to_close: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unsubscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class SavedMarket(Base):
    """A market a user has chosen to follow (spec §10)."""

    __tablename__ = "saved_markets"
    __table_args__ = (UniqueConstraint("user_id", "market_id", name="uq_saved_user_market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class AlertDelivery(Base):
    """Per-user record of an alert that was eligible/sent (spec §10, §12 delivery history)."""

    __tablename__ = "alert_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    subject: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False)  # sent | test | failed | skipped_*
    detail: Mapped[str] = mapped_column(String, nullable=False, default="")
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False, default=utcnow
    )


class AccountDeletionAudit(Base):
    """Minimal audit row written when an account is deleted (spec §10).

    Stores a non-reversible SHA-256 of the email plus timestamp, so we can evidence a deletion
    request without retaining the deleted user's personal data.
    """

    __tablename__ = "account_deletions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_hash: Mapped[str] = mapped_column(String, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    reason: Mapped[str] = mapped_column(String, nullable=False, default="user_request")
