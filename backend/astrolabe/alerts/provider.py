"""Provider-neutral email delivery.

The default is a console sink that never sends anything externally. An in-memory outbox is
used by tests. The SMTP provider is a real sender that stays disabled until host and
credentials are supplied via environment variables. All providers share one async ``send``
interface so the alert service is provider-agnostic. Messages may carry a Resend template alias
and variables alongside their plain-text/HTML fallbacks; only ``ResendProvider`` interprets that
metadata, while SMTP and local test providers continue to use the rendered fallbacks.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote

from ..observability.logging import get_logger
from .config import AlertConfig

logger = get_logger("astrolabe.alerts")


@dataclass
class EmailMessage:
    to: str
    sender: str
    subject: str
    text: str
    html: str | None = None
    template_id: str | None = None
    template_variables: dict[str, str | int] = field(default_factory=dict)
    # Digest cards can exceed Resend's 2,000-character limit for one template variable. In that
    # case the provider fetches the published template shell, safely expands it server-side, then
    # sends the rendered HTML. Only variables explicitly named here may contain trusted app-built
    # markup; every other value is escaped.
    server_render_template: bool = False
    trusted_html_variables: set[str] = field(default_factory=set)
    idempotency_key: str | None = None


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
            if message.html:
                mime.add_alternative(message.html, subtype="html")
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                if cfg.smtp_user:
                    smtp.login(cfg.smtp_user, cfg.smtp_password)
                smtp.send_message(mime)
            return SendResult(True, "sent via SMTP")
        except Exception as exc:  # noqa: BLE001 - never crash the caller on a send failure
            logger.warning("SMTP send failed", extra={"ctx_error": str(exc)})
            return SendResult(False, f"SMTP send failed: {exc}")


class ResendProvider:
    """Real sender via the Resend HTTPS API (spec §18). Key + verified sender from env only.

    Sends either a published Resend template by stable alias/ID or a rendered text/HTML message
    through ``api.resend.com/emails``. Resend forbids mixing ``template`` with ``html``/``text``,
    so payload construction deliberately chooses exactly one representation.
    Never raises: a failure returns an unsuccessful ``SendResult`` so the retry/failure-log path in
    the alert service handles it. A verified custom domain is required to send to arbitrary
    recipients; the test sender is limited by Resend to the account owner's address.
    """

    name = "resend"

    def __init__(self, config: AlertConfig):
        self._config = config
        self._template_cache: dict[str, tuple[str, str]] = {}

    async def _published_template(self, client, template_id: str) -> tuple[str, str]:
        cached = self._template_cache.get(template_id)
        if cached is not None:
            return cached
        template_key = self._config.resend_template_api_key or self._config.resend_api_key
        resp = await client.get(
            f"https://api.resend.com/templates/{quote(template_id, safe='')}",
            headers={"Authorization": f"Bearer {template_key}"},
        )
        if resp.status_code // 100 != 2:
            raise RuntimeError(f"Resend template HTTP {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        if body.get("status") != "published" or not isinstance(body.get("html"), str):
            raise RuntimeError("Resend digest template is not published or has no HTML")
        rendered = (body["html"], body.get("text") or "")
        self._template_cache[template_id] = rendered
        return rendered

    @staticmethod
    def _render_template(
        source: str, variables: dict[str, str | int], *, trusted_html: set[str], text: bool = False
    ) -> str:
        # Expand the original shell in one regex pass. Repeated ``str.replace`` calls would allow a
        # value containing another placeholder (for example a user's name of
        # ``{{SIGNALS_CONTENT}}``) to trigger a second substitution.
        pattern = re.compile(r"\{\{\{?([A-Z][A-Z0-9_]*)\}?\}\}")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                raise ValueError(f"unresolved template variable {match.group(0)}")
            raw = variables[key]
            value = str(raw)
            if text:
                return value
            elif key in trusted_html:
                return value
            return html.escape(value, quote=True)

        return pattern.sub(replace, source)

    async def send(self, message: EmailMessage) -> SendResult:
        cfg = self._config
        if not (cfg.resend_api_key and message.to and message.sender):
            return SendResult(False, "Resend not configured (api key / sender / recipient missing)")
        try:
            import httpx

            payload: dict = {
                "from": message.sender,
                "to": [message.to],
                "subject": message.subject,
            }
            async with httpx.AsyncClient(timeout=15) as client:
                if message.template_id and message.server_render_template:
                    shell_html, _shell_text = await self._published_template(
                        client, message.template_id
                    )
                    payload["html"] = self._render_template(
                        shell_html,
                        message.template_variables,
                        trusted_html=message.trusted_html_variables,
                    )
                    # The published text shell cannot safely distinguish the HTML-only repeated
                    # card variable. Use the app-built plain-text digest instead of leaking markup.
                    payload["text"] = message.text
                elif message.template_id:
                    payload["template"] = {
                        "id": message.template_id,
                        "variables": message.template_variables,
                    }
                else:
                    payload["text"] = message.text
                    payload["html"] = message.html or (
                        "<pre style=\"font:14px/1.5 system-ui\">"
                        + html.escape(message.text)
                        + "</pre>"
                    )
                headers = {"Authorization": f"Bearer {cfg.resend_api_key}"}
                if message.idempotency_key:
                    headers["Idempotency-Key"] = message.idempotency_key
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers=headers,
                    json=payload,
                )
            if resp.status_code // 100 == 2:
                return SendResult(True, "sent via Resend")
            return SendResult(False, f"Resend HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:  # noqa: BLE001 - never crash the caller on a send failure
            logger.warning("Resend send failed", extra={"ctx_error": str(exc)})
            return SendResult(False, f"Resend send failed: {exc}")


def provider_for(config: AlertConfig) -> EmailProvider:
    """Choose a provider from config. Console sink by default; real senders only when enabled."""
    if config.enabled and not config.test_mode:
        if config.provider == "resend":
            return ResendProvider(config)
        if config.provider == "smtp":
            return SmtpProvider(config)
    return ConsoleProvider()
