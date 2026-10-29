"""Canonical Arepo transactional-email service.

``fastapi-users`` remains solely responsible for verification/reset token creation and validation.
This module owns only server-side email concerns: canonical links, sender identity, stable Resend
template aliases, template variables and delivery through the existing provider abstraction.

Digest selection/history live in ``astrolabe.digest``; this module owns the published-template
contract and provider handoff only.
"""
from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from ..alerts.config import AlertConfig
from ..alerts.provider import EmailMessage, EmailProvider, SendResult, provider_for
from ..config import get_settings
from ..observability.logging import get_logger

logger = get_logger("astrolabe.accounts.email")

CANONICAL_AREPO_BASE_URL = "https://www.arepolabs.com"
DEFAULT_TRANSACTIONAL_SENDER = "Arepo <no-reply@arepolabs.com>"
DEFAULT_DIGEST_SENDER = "Arepo Alerts <alerts@arepolabs.com>"


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
    """Published digest template contract and canonical market URL helper."""

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
    """Small service for auth and personalised digest email delivery."""

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
        # Keep legacy nameless accounts natural without deriving a name from an email address.
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
        """Return the stable published-template contract."""
        return SignalDigestPreparation(template_id=self.templates.signals_digest)

    async def send_signal_digest(
        self,
        email: str,
        *,
        user_name: str | None,
        summary: str,
        signals_html: str,
        signals_text: str,
        preferences_url: str,
        unsubscribe_url: str,
        idempotency_key: str,
    ) -> SendResult:
        """Send one digest using the published shell and trusted server-built repeated cards.

        Resend template string variables are capped at 2,000 characters, so the provider fetches
        the published shell and expands it server-side. ``SIGNALS_CONTENT`` is the only trusted HTML
        variable; its builder escapes every market/upstream value before this method is called.
        """
        sender = os.environ.get("DIGEST_EMAIL_SENDER", "").strip() or DEFAULT_DIGEST_SENDER
        message = EmailMessage(
            to=email,
            sender=sender,
            subject="Your Arepo signals",
            text=(
                f"Hi {self._user_name(user_name)},\n\n{summary}\n\n{signals_text}\n\n"
                f"Manage preferences: {preferences_url}\nUnsubscribe: {unsubscribe_url}"
            ),
            template_id=self.templates.signals_digest,
            template_variables={
                "USER_NAME": self._user_name(user_name),
                "DIGEST_SUMMARY": summary,
                "SIGNALS_CONTENT": signals_html,
                "PREFERENCES_URL": preferences_url,
                "AREPO_UNSUBSCRIBE_LINK": unsubscribe_url,
            },
            server_render_template=True,
            trusted_html_variables={"SIGNALS_CONTENT"},
            idempotency_key=idempotency_key,
        )
        return await self._provider.send(message)


# Test seam and compatibility wrappers used by the existing fastapi-users callbacks.
_provider_override: EmailProvider | None = None


def set_provider_override(provider: EmailProvider | None) -> None:
    global _provider_override
    _provider_override = provider


def _service() -> AccountEmailService:
    return AccountEmailService(provider=_provider_override)


# --- Per-recipient caps on auth emails (audit R2-07) -------------------------------------------
# Stops the register / forgot-password endpoints being used to mail-bomb a third party's address.
# Process-local and in-memory (bounded), so each API instance enforces its own cap; the per-IP
# limiter and Resend's own limits remain the outer bound across instances. A restart resets it.
# Trade-off: someone who spams a victim's address can exhaust the victim's hourly allowance, which
# delays (not blocks) their own reset email by at most an hour.
HOURLY_CAP = 3
DAILY_CAP = 10
_MAX_RECIPIENTS = 20_000
_sent: dict[str, deque[float]] = {}


def reset_recipient_caps() -> None:
    """Clear the counters (tests)."""
    _sent.clear()


def _allow_recipient(email: str, now: float | None = None) -> bool:
    """Record one send to ``email`` if under both caps; return False (and record nothing) if not."""
    now = time.time() if now is None else now
    key = email.strip().lower()
    if key not in _sent and len(_sent) >= _MAX_RECIPIENTS:
        for k in [k for k, q in _sent.items() if not q or q[-1] < now - 86400]:
            del _sent[k]
        if len(_sent) >= _MAX_RECIPIENTS:
            del _sent[next(iter(_sent))]
    q = _sent.setdefault(key, deque())
    while q and q[0] < now - 86400:
        q.popleft()
    if len(q) >= DAILY_CAP or sum(1 for t in q if t >= now - 3600) >= HOURLY_CAP:
        return False
    q.append(now)
    return True


_CAPPED = SendResult(ok=False, detail="recipient_rate_limited")


async def send_verification_email(
    email: str, token: str, *, user_name: str | None = None
) -> SendResult:
    if not _allow_recipient(email):
        logger.warning("verification email suppressed: per-recipient cap")
        return _CAPPED
    return await _service().send_verification(email, token, user_name=user_name)


async def send_reset_email(
    email: str, token: str, *, user_name: str | None = None
) -> SendResult:
    if not _allow_recipient(email):
        logger.warning("reset email suppressed: per-recipient cap")
        return _CAPPED
    return await _service().send_password_reset(email, token, user_name=user_name)
