"""Account emails (verification, password reset) over the provider-neutral engine.

These always send through the same abstraction as alerts. In local development the provider is
the console sink, so the verification/reset link is printed to the server log and the whole flow
works with no external email account configured. British English; no em dashes.
"""
from __future__ import annotations

from ..alerts.config import AlertConfig
from ..alerts.provider import EmailMessage, EmailProvider, SendResult, provider_for
from ..config import get_settings

# Test seam: set to an OutboxProvider in tests to capture links without sending.
_provider_override: EmailProvider | None = None


def set_provider_override(provider: EmailProvider | None) -> None:
    global _provider_override
    _provider_override = provider


def _provider() -> EmailProvider:
    return _provider_override or provider_for(AlertConfig.from_env())


def _sender() -> str:
    return AlertConfig.from_env().sender or "no-reply@arepo.local"


async def _send(to: str, subject: str, text: str) -> SendResult:
    return await _provider().send(
        EmailMessage(to=to, sender=_sender(), subject=subject, text=text)
    )


async def send_verification_email(email: str, token: str) -> SendResult:
    base = get_settings().app_base_url.rstrip("/")
    link = f"{base}/verify?token={token}"
    text = (
        "Welcome to Arepo.\n\n"
        "Please confirm your email address to activate your free account and receive the "
        "research alerts you choose:\n\n"
        f"{link}\n\n"
        "If you did not create an Arepo account you can ignore this email.\n\n"
        "Arepo sends statistical research signals, not financial advice."
    )
    return await _send(email, "Confirm your Arepo email", text)


async def send_reset_email(email: str, token: str) -> SendResult:
    base = get_settings().app_base_url.rstrip("/")
    link = f"{base}/reset?token={token}"
    text = (
        "We received a request to reset your Arepo password.\n\n"
        f"Use this link to choose a new password:\n\n{link}\n\n"
        "If you did not request this, you can ignore this email and your password will not "
        "change."
    )
    return await _send(email, "Reset your Arepo password", text)
