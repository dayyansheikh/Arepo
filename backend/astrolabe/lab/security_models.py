"""ORM tables for Lab hardware-security-key (WebAuthn) step-up authentication.

Additive and private (owner-only API, RLS enabled on Postgres). No secrets are stored in plain
form: a credential row holds only the authenticator's PUBLIC key; challenges are random and
single-use; step-up sessions and recovery codes are stored as SHA-256 / Argon2 hashes.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..domain.models import utcnow
from ..storage.db import Base


class AdminWebAuthnCredential(Base):
    __tablename__ = "admin_webauthn_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    credential_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # base64url
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # base64url COSE public key
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transports: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    aaguid: Mapped[str | None] = mapped_column(String, nullable=True)
    device_type: Mapped[str | None] = mapped_column(String, nullable=True)  # single/multi_device
    backed_up: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminWebAuthnChallenge(Base):
    """A single-use WebAuthn challenge (consumed on the first verify attempt; minutes TTL)."""

    __tablename__ = "admin_webauthn_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purpose: Mapped[str] = mapped_column(String, nullable=False)  # register | authenticate
    challenge: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # base64url
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminStepUpSession(Base):
    """A revocable step-up bound to one user; the cookie holds the token, we keep its hash."""

    __tablename__ = "admin_stepup_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_sha256: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)  # key | recovery | register
    credential_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminRecoveryCode(Base):
    """One-time recovery code (Argon2 hash); ``used_at`` set when spent."""

    __tablename__ = "admin_recovery_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminTrustedDevice(Base):
    """One browser/device a key holder has used, identified by an HttpOnly device cookie.

    The cookie holds a random token; only its SHA-256 is stored. ``trusted_until`` in the future
    means the owner chose "don't ask for my key on this device" (set only after a fresh key tap on
    that device, capped at 30 days); NULL or past means the normal step-up rule applies.
    """

    __tablename__ = "admin_trusted_devices"
    __table_args__ = (UniqueConstraint("user_id", "device_sha256",
                                       name="uq_admin_trusted_devices_user_device"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    device_sha256: Mapped[str] = mapped_column(String, index=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)  # truncated
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trusted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trusted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
