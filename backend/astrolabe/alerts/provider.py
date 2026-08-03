"""Provider-neutral email delivery.

The default is a console sink that never sends anything externally. An in-memory outbox is
used by tests. The SMTP provider is a real sender that stays disabled until host and
credentials are supplied via environment variables. All providers share one async ``send``
interface so the alert service is provider-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..observability.logging import get_logger
from .config import AlertConfig

logger = get_logger("astrolabe.alerts")


@dataclass
class EmailMessage:
    to: str
    sender: str
    subject: str
    text: str


@dataclass
class SendResult:
    ok: bool
    detail: str


class EmailProvider(Protocol):
    name: str

    async def send(self, message: EmailMessage) -> SendResult: ...


class ConsoleProvider:
    """Default sink: logs the message and records success without sending externally."""

    name = "console"

    async def send(self, message: EmailMessage) -> SendResult:
        logger.info(
            "alert (console sink, not sent externally)",
            extra={"ctx_to": message.to or "<unset>", "ctx_subject": message.subject},
        )
        return SendResult(True, "logged to console sink (not sent externally)")


@dataclass
class OutboxProvider:
    """Captures messages in memory for local development and tests. Never sends externally."""

    name: str = "outbox"
    sent: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> SendResult:
        self.sent.append(message)
        return SendResult(True, "captured in local outbox")


@dataclass
class FailingProvider:
    """Test double that always fails, to exercise retry and failure logging."""

    name: str = "failing"
    attempts: int = 0

    async def send(self, message: EmailMessage) -> SendResult:
        self.attempts += 1
        return SendResult(False, "simulated provider failure")


class SmtpProvider:
    """Real SMTP sender, only usable when host + credentials are configured (from env)."""

    name = "smtp"

    def __init__(self, config: AlertConfig):
        self._config = config

    async def send(self, message: EmailMessage) -> SendResult:
        cfg = self._config
        if not (cfg.smtp_host and message.to):
            return SendResult(False, "SMTP not configured (host/recipient missing)")
        try:
            import smtplib
            from email.message import EmailMessage as MimeMessage

            mime = MimeMessage()
            mime["From"] = message.sender
            mime["To"] = message.to
            mime["Subject"] = message.subject
            mime.set_content(message.text)
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                if cfg.smtp_user:
                    smtp.login(cfg.smtp_user, cfg.smtp_password)
                smtp.send_message(mime)
            return SendResult(True, "sent via SMTP")
        except Exception as exc:  # noqa: BLE001 - never crash the caller on a send failure
            logger.warning("SMTP send failed", extra={"ctx_error": str(exc)})
            return SendResult(False, f"SMTP send failed: {exc}")


def provider_for(config: AlertConfig) -> EmailProvider:
    """Choose a provider from config. Defaults to the console sink; SMTP only when enabled."""
    if config.provider == "smtp" and config.enabled and not config.test_mode:
        return SmtpProvider(config)
    return ConsoleProvider()
