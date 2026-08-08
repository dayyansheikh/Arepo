"""Canonical Arepo transactional-email service.

``fastapi-users`` remains solely responsible for verification/reset token creation and validation.
This module owns only server-side email concerns: canonical links, sender identity, stable Resend
template aliases, template variables and delivery through the existing provider abstraction.

The future signals digest is deliberately represented only by template metadata and a canonical
market deep-link helper. Digest scheduling, preference logic and repeated-card rendering are out of
scope until their account architecture is designed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from ..alerts.config import AlertConfig
from ..alerts.provider import EmailMessage, EmailProvider, SendResult, provider_for
from ..config import get_settings
from ..observability.logging import get_logger

logger = get_logger("astrolabe.accounts.email")

CANONICAL_AREPO_BASE_URL = "https://www.arepolabs.com"
DEFAULT_TRANSACTIONAL_SENDER = "Arepo <no-reply@arepolabs.com>"


@dataclass(frozen=True)
class EmailTemplateIds:
    """Stable server-side Resend aliases (or operator-supplied opaque IDs)."""

    verify: str = "arepo-verify-email"
    reset_password: str = "arepo-reset-password"
    signals_digest: str = "arepo-signals-digest"

    @classmethod
    def from_env(cls) -> EmailTemplateIds:
        def value(name: str, default: str) -> str:
            return os.environ.get(name, "").strip() or default

        return cls(
            verify=value("RESEND_TEMPLATE_VERIFY", cls.verify),
            reset_password=value("RESEND_TEMPLATE_RESET", cls.reset_password),
            signals_digest=value("RESEND_TEMPLATE_SIGNALS", cls.signals_digest),
        )


@dataclass(frozen=True)
class SignalDigestPreparation:
    """Future digest contract only; no preference, rendering or scheduling behaviour."""

    template_id: str
    required_variables: tuple[str, ...] = (
        "USER_NAME",
        "DIGEST_SUMMARY",
        "SIGNALS_CONTENT",
        "PREFERENCES_URL",
        "AREPO_UNSUBSCRIBE_LINK",
    )

    @staticmethod
    def market_url(market_id: str) -> str:
        """Deep-link one future card to its exact canonical Arepo market page."""
        return f"{CANONICAL_AREPO_BASE_URL}/markets/{quote(market_id, safe='')}"


class AccountEmailService:
    """Small service for auth emails plus the future digest integration point."""

    def __init__(
        self,
        *,
        provider: EmailProvider | None = None,
        templates: EmailTemplateIds | None = None,
        sender: str | None = None,
    ) -> None:
        self._provider = provider or provider_for(AlertConfig.from_env())
        self.templates = templates or EmailTemplateIds.from_env()
        configured_sender = os.environ.get("AUTH_EMAIL_SENDER", "").strip()
        self.sender = sender or configured_sender or DEFAULT_TRANSACTIONAL_SENDER

    @staticmethod
    def _action_url(path: str, token: str) -> str:
        return f"{CANONICAL_AREPO_BASE_URL}/{path}?{urlencode({'token': token})}"

    @staticmethod
    def _user_name(user_name: str | None) -> str:
        # The current User model has no name field. Keep the greeting natural without deriving a
        # potentially incorrect name from an email address; a future model can pass a real name.
        return (user_name or "").strip() or "there"

    async def _send(self, message: EmailMessage, *, action_url: str) -> SendResult:
        result = await self._provider.send(message)
        # Keep local no-provider development usable, but never write a secure action token into
        # production logs if email is misconfigured and falls back to the console sink.
        if getattr(self._provider, "name", "") == "console" and (
            get_settings().environment != "production"
        ):
            logger.info(
                f"account email (local console sink, not sent externally) "
                f"to={message.to or '<unset>'} subject={message.subject!r} link={action_url}"
            )
        return result

    async def send_verification(
        self, email: str, token: str, *, user_name: str | None = None
    ) -> SendResult:
        verify_url = self._action_url("verify", token)
        message = EmailMessage(
            to=email,
            sender=self.sender,
            subject="Confirm your Arepo email",
            text=(
                "Confirm your email using the Verify email button in the branded Arepo message. "
                "If you did not create an Arepo account, you can safely ignore it."
            ),
            template_id=self.templates.verify,
            template_variables={
                "USER_NAME": self._user_name(user_name),
                "VERIFY_URL": verify_url,
            },
        )
        return await self._send(message, action_url=verify_url)

    async def send_password_reset(
        self, email: str, token: str, *, user_name: str | None = None
    ) -> SendResult:
        reset_url = self._action_url("reset", token)
        message = EmailMessage(
            to=email,
            sender=self.sender,
            subject="Reset your Arepo password",
            text=(
                "Use the Reset password button in the branded Arepo message to choose a new "
                "password. If you did not request this, you can safely ignore it."
            ),
            template_id=self.templates.reset_password,
            template_variables={
                "USER_NAME": self._user_name(user_name),
                "RESET_URL": reset_url,
            },
        )
        return await self._send(message, action_url=reset_url)

    def prepare_signal_digest(self) -> SignalDigestPreparation:
        """Return the future template contract without sending or inventing digest behaviour."""
        return SignalDigestPreparation(template_id=self.templates.signals_digest)


# Test seam and compatibility wrappers used by the existing fastapi-users callbacks.
_provider_override: EmailProvider | None = None


def set_provider_override(provider: EmailProvider | None) -> None:
    global _provider_override
    _provider_override = provider


def _service() -> AccountEmailService:
    return AccountEmailService(provider=_provider_override)


async def send_verification_email(
    email: str, token: str, *, user_name: str | None = None
) -> SendResult:
    return await _service().send_verification(email, token, user_name=user_name)


async def send_reset_email(
    email: str, token: str, *, user_name: str | None = None
) -> SendResult:
    return await _service().send_password_reset(email, token, user_name=user_name)
