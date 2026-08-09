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


@pytest.mark.asyncio
async def test_digest_safely_renders_published_shell_server_side_without_variable_limit(respx_mock):
    template = respx_mock.get(
        "https://api.resend.com/templates/arepo-signals-digest"
    ).mock(return_value=httpx.Response(200, json={
        "status": "published",
        "html": (
            "<p>Hi {{{USER_NAME}}}</p><div>{{{SIGNALS_CONTENT}}}</div>"
            "<a href=\"{{{PREFERENCES_URL}}}\">Preferences</a>"
            "<a href=\"{{{AREPO_UNSUBSCRIBE_LINK}}}\">Unsubscribe</a>"
            "<p>{{{DIGEST_SUMMARY}}}</p>"
        ),
        "text": (
            "Hi {{{USER_NAME}}}\n{{{SIGNALS_CONTENT}}}\n{{{PREFERENCES_URL}}}\n"
            "{{{AREPO_UNSUBSCRIBE_LINK}}}\n{{{DIGEST_SUMMARY}}}"
        ),
    }))
    send = respx_mock.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "digest-email-id"})
    )
    provider = ResendProvider(AlertConfig(
        enabled=True,
        provider="resend",
        sender="Arepo Alerts <alerts@arepolabs.com>",
        resend_api_key="test-only-secret-key",
        resend_template_api_key="test-only-template-read-key",
    ))
    cards = "<span>" + ("safe card " * 400) + "</span>"  # deliberately over 2,000 chars
    message = EmailMessage(
        to="person@example.com",
        sender="Arepo Alerts <alerts@arepolabs.com>",
        subject="Your Arepo signals",
        text="fallback",
        template_id="arepo-signals-digest",
        template_variables={
            "USER_NAME": "Ada & Grace",
            "DIGEST_SUMMARY": "Two < current",
            "SIGNALS_CONTENT": cards,
            "PREFERENCES_URL": "https://www.arepolabs.com/account?tab=preferences&x=1",
            "AREPO_UNSUBSCRIBE_LINK": "https://www.arepolabs.com/unsubscribe?token=opaque&x=1",
        },
        server_render_template=True,
        trusted_html_variables={"SIGNALS_CONTENT"},
        idempotency_key="arepo-digest-42-window",
    )

    result = await provider.send(message)
    assert result.ok is True and template.called
    payload = json.loads(send.calls[0].request.content)
    assert "template" not in payload
    assert cards in payload["html"]
    assert "Ada &amp; Grace" in payload["html"]
    assert "Two &lt; current" in payload["html"]
    assert "token=opaque&amp;x=1" in payload["html"]
    assert send.calls[0].request.headers["Idempotency-Key"] == "arepo-digest-42-window"
    assert template.calls[0].request.headers["Authorization"] == (
        "Bearer test-only-template-read-key"
    )
    assert send.calls[0].request.headers["Authorization"] == "Bearer test-only-secret-key"


def test_server_render_does_not_recursively_expand_placeholders_from_values():
    rendered = ResendProvider._render_template(
        "<p>{{{USER_NAME}}}</p><div>{{{SIGNALS_CONTENT}}}</div>",
        {
            "USER_NAME": "{{SIGNALS_CONTENT}}",
            "SIGNALS_CONTENT": "<strong>trusted card</strong>",
        },
        trusted_html={"SIGNALS_CONTENT"},
    )

    assert rendered == (
        "<p>{{SIGNALS_CONTENT}}</p><div><strong>trusted card</strong></div>"
    )
