"""fastapi-users UserManager: registration, email verification and password reset hooks.

Password hashing and token signing are handled entirely by fastapi-users (argon2 via pwdlib,
JWT via PyJWT); this module only wires the lifecycle callbacks to our provider-neutral email
sender and stamps the consent timestamp at registration.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin

from ..config import get_settings
from ..domain.models import utcnow
from ..observability.logging import get_logger
from . import email as account_email
from .db import get_user_db
from .models import User

logger = get_logger("astrolabe.accounts")


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    @property
    def reset_password_token_secret(self) -> str:  # type: ignore[override]
        return get_settings().auth_secret

    @property
    def verification_token_secret(self) -> str:  # type: ignore[override]
        return get_settings().auth_secret

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        # Stamp consent at registration; sign-up requires accepting the terms (spec §10).
        if user.consent_at is None:
            await self.user_db.update(user, {"consent_at": utcnow()})
        logger.info("account registered", extra={"ctx_user": str(user.id)})
        # Kick off email verification immediately.
        if get_settings().require_email_verification and not user.is_verified:
            try:
                await self.request_verify(user, request)
            except Exception as exc:  # noqa: BLE001 - never fail registration on mail issues
                logger.warning("verify request failed", extra={"ctx_err": str(exc)})

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        await account_email.send_verification_email(
            user.email, token, user_name=_supported_user_name(user)
        )

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        await account_email.send_reset_email(
            user.email, token, user_name=_supported_user_name(user)
        )


def _supported_user_name(user: User) -> str | None:
    """Use a real model-backed name when available; the current User has no name column."""
    for field in ("display_name", "name", "first_name"):
        value = getattr(user, field, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
