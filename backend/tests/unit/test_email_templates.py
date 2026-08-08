"""Transactional email template contracts and Resend payload construction."""

import json

import httpx
import pytest

from astrolabe.accounts.email import (
    CANONICAL_AREPO_BASE_URL,
    AccountEmailService,
    EmailTemplateIds,
)
from astrolabe.alerts.config import AlertConfig
from astrolabe.alerts.provider import (
    ConsoleProvider,
    EmailMessage,
    OutboxProvider,
    ResendProvider,
)
from astrolabe.config import get_settings


@pytest.mark.asyncio
async def test_verification_uses_branded_template_and_canonical_cta_only():
    outbox = OutboxProvider()
    service = AccountEmailService(provider=outbox)

    result = await service.send_verification(
        "person@example.com", "secure.verify.token", user_name="Ada"
    )

    assert result.ok is True
    message = outbox.sent[0]
    assert message.sender == "Arepo <no-reply@arepolabs.com>"
    assert message.subject == "Confirm your Arepo email"
    assert message.template_id == "arepo-verify-email"
    assert message.template_variables == {
        "USER_NAME": "Ada",
        "VERIFY_URL": (
            "https://www.arepolabs.com/verify?token=secure.verify.token"
        ),
    }
    assert "http://" not in message.text
    assert "localhost" not in message.text.lower()
    assert "backend" not in message.text.lower()
    assert message.template_variables["VERIFY_URL"] not in message.text


@pytest.mark.asyncio
async def test_reset_uses_branded_template_and_neutral_name_fallback():
    outbox = OutboxProvider()
    service = AccountEmailService(provider=outbox)

    await service.send_password_reset("person@example.com", "token with symbols/+?")

    message = outbox.sent[0]
    assert message.subject == "Reset your Arepo password"
    assert message.template_id == "arepo-reset-password"
    assert message.template_variables["USER_NAME"] == "there"
    reset_url = message.template_variables["RESET_URL"]
    assert reset_url.startswith(f"{CANONICAL_AREPO_BASE_URL}/reset?token=")
    assert "token+with+symbols%2F%2B%3F" in reset_url
    assert reset_url not in message.text
    assert "localhost" not in message.text.lower()
    assert "backend" not in message.text.lower()


def test_template_ids_are_server_side_and_env_overridable(monkeypatch):
    monkeypatch.setenv("RESEND_TEMPLATE_VERIFY", "opaque-verify-id")
    monkeypatch.setenv("RESEND_TEMPLATE_RESET", "opaque-reset-id")
    monkeypatch.setenv("RESEND_TEMPLATE_SIGNALS", "opaque-signals-id")

    templates = EmailTemplateIds.from_env()

    assert templates == EmailTemplateIds(
        verify="opaque-verify-id",
        reset_password="opaque-reset-id",
        signals_digest="opaque-signals-id",
    )


def test_digest_preparation_preserves_exact_market_deep_links_without_sending():
    service = AccountEmailService(provider=OutboxProvider())
    prepared = service.prepare_signal_digest()

    assert prepared.template_id == "arepo-signals-digest"
    assert prepared.market_url("market/id with spaces") == (
        "https://www.arepolabs.com/markets/market%2Fid%20with%20spaces"
    )
    assert prepared.required_variables == (
        "USER_NAME",
        "DIGEST_SUMMARY",
        "SIGNALS_CONTENT",
        "PREFERENCES_URL",
        "AREPO_UNSUBSCRIBE_LINK",
    )


@pytest.mark.asyncio
async def test_production_console_fallback_never_logs_secure_action_token(monkeypatch, caplog):
    monkeypatch.setattr(get_settings(), "environment", "production")
    service = AccountEmailService(provider=ConsoleProvider())

    await service.send_verification("person@example.com", "must-not-appear-in-logs")

    assert "must-not-appear-in-logs" not in caplog.text


@pytest.mark.asyncio
async def test_resend_template_payload_excludes_rendered_content_and_secret(respx_mock):
    route = respx_mock.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "email-id"})
    )
    config = AlertConfig(
        enabled=True,
        provider="resend",
        sender="Arepo <no-reply@arepolabs.com>",
        resend_api_key="test-only-secret-key",
    )
    provider = ResendProvider(config)
    message = EmailMessage(
        to="person@example.com",
        sender=config.sender,
        subject="Confirm your Arepo email",
        text="Local non-Resend fallback",
        html="<p>Local fallback</p>",
        template_id="arepo-verify-email",
        template_variables={
            "USER_NAME": "Ada",
            "VERIFY_URL": "https://www.arepolabs.com/verify?token=signed-token",
        },
    )

    result = await provider.send(message)

    assert result.ok is True
    payload = json.loads(route.calls[0].request.content)
    assert payload["template"] == {
        "id": "arepo-verify-email",
        "variables": message.template_variables,
    }
    assert "html" not in payload and "text" not in payload
    assert "test-only-secret-key" not in json.dumps(payload)
    assert route.calls[0].request.headers["Authorization"] == (
        "Bearer test-only-secret-key"
    )
