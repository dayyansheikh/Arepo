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
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..domain.models import utcnow
from ..storage.db import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """A registered user. Inherits id/email/hashed_password/is_active/is_superuser/is_verified.

    Extra columns capture the consent timestamp and the authentication provider (spec §10), and
    a creation timestamp for audit.
    """

    __tablename__ = "users"

    # Nullable for safe additive migration of existing accounts. New registrations require both
    # fields at the API boundary; legacy users continue to authenticate and receive neutral email /
    # initials fallbacks until a name is supplied.
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
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
    # Digest-specific settings. These are deliberately separate from legacy immediate-alert flags:
    # an unsubscribe link must stop only personalised digests, never account/security email.
    digest_frequency: Mapped[str] = mapped_column(String, nullable=False, default="off")
    digest_top_n: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    digest_unsubscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    digest_categories: Mapped[str] = mapped_column(String, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class DigestDelivery(Base):
    """One immutable-content personalised digest attempt for one user and due window.

    Delivery bookkeeping may advance from created/failed to sending/sent, but the preference and
    signal snapshots are never rewritten. The unique due-window key prevents duplicate history and
    the provider idempotency key prevents a successful external send being repeated on retry.
    """

    __tablename__ = "digest_deliveries"
    __table_args__ = (
        UniqueConstraint("user_id", "due_window_key", name="uq_digest_user_window"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    due_window_key: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    top_n: Mapped[int] = mapped_column(Integer, nullable=False)
    categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scan_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluation_horizon: Mapped[str] = mapped_column(String, nullable=False, default="24h")
    status: Mapped[str] = mapped_column(String, nullable=False, default="created", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_detail: Mapped[str] = mapped_column(String, nullable=False, default="")
    unsubscribe_selector: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True, index=True
    )
    unsubscribe_secret_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class DigestEntry(Base):
    """Minimal point-in-time signal snapshot included in a specific user's digest."""

    __tablename__ = "digest_entries"
    __table_args__ = (
        UniqueConstraint("digest_id", "market_id", "token_id", name="uq_digest_entry"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("digest_deliveries.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    market_question: Mapped[str] = mapped_column(String, nullable=False)
    outcome_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    category: Mapped[str] = mapped_column(String, nullable=False, default="Other")
    direction: Mapped[str] = mapped_column(String, nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    research_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Optional exact prospective-row join. NULL is honest when the source scan was not frozen into a
    # cohort; read paths may discover a later-created exact scan join without mutating this
    # snapshot.
    research_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("research_entries.id"), nullable=True, index=True
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
