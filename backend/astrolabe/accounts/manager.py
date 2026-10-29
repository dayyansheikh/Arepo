"""fastapi-users UserManager: registration, email verification and password reset hooks.

Password hashing and token signing are handled entirely by fastapi-users (argon2 via pwdlib,
JWT via PyJWT); this module only wires the lifecycle callbacks to our provider-neutral email
sender and stamps the consent timestamp at registration.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.exceptions import InvalidPasswordException

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

    async def update(self, user_update, user, safe: bool = False, request=None):  # type: ignore[override]
        """Self-service changes of the password or email must re-prove the current password, so a
        stolen session cookie cannot take over the account."""
        if safe:
            data = user_update.model_dump(exclude_unset=True)
            email_change = "email" in data and data["email"] != user.email
            if data.get("password") is not None or email_change:
                current = data.get("current_password")
                ok = False
                if current:
                    ok, _ = self.password_helper.verify_and_update(current, user.hashed_password)
                if not ok:
                    raise InvalidPasswordException(
                        reason="Current password is required to change password or email."
                    )
        return await super().update(user_update, user, safe=safe, request=request)

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
    """Use only the private first-name field; legacy nameless users get the email fallback.

    Until the address is verified the name is attacker-chosen text going to a possibly third-party
    inbox, so a neutral greeting is used (audit R2-07)."""
    if not getattr(user, "is_verified", False):
        return None
    value = getattr(user, "first_name", None)
    return value.strip() if isinstance(value, str) and value.strip() else None


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
