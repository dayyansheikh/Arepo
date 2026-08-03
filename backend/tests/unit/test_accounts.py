"""Account system tests (spec §16): auth lifecycle, isolation, deletion, rate limiting, prefs.

Runs against the real FastAPI app with the account session bound to an isolated in-memory
database and the email provider swapped for an in-memory outbox (so verification tokens can be
read without sending anything). No network.
"""
import re

import pytest
from fastapi.testclient import TestClient

from astrolabe.accounts import db as accounts_db
from astrolabe.accounts import email as account_email
from astrolabe.accounts import ratelimit
from astrolabe.alerts.provider import OutboxProvider
from astrolabe.api.app import create_app
from astrolabe.config import get_settings
from astrolabe.storage.db import Base, make_engine, make_sessionmaker


@pytest.fixture
async def outbox():
    box = OutboxProvider()
    account_email.set_provider_override(box)
    yield box
    account_email.set_provider_override(None)


@pytest.fixture
async def client(outbox):
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = make_sessionmaker(engine)

    async def override_session():
        async with sessionmaker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[accounts_db.get_async_session] = override_session
    ratelimit.reset()
    with TestClient(app) as c:
        yield c
    await engine.dispose()


def _token_from_outbox(outbox, kind: str) -> str:
    text = outbox.sent[-1].text
    m = re.search(rf"/{kind}\?token=([^\s]+)", text)
    assert m, f"no {kind} token in outbox: {text!r}"
    return m.group(1)


def _register(client, email="a@example.com", password="Sufficiently-Long-1"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def _verify_and_login(client, outbox, email="a@example.com", password="Sufficiently-Long-1"):
    _register(client, email, password)
    token = _token_from_outbox(outbox, "verify")
    assert client.post("/api/auth/verify", json={"token": token}).status_code == 200
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code in (200, 204)
    return r


async def test_register_sends_verification_and_blocks_login_until_verified(client, outbox):
    r = _register(client)
    assert r.status_code == 201
    assert len(outbox.sent) == 1  # verification email queued
    # Login is refused before verification.
    r = client.post(
        "/api/auth/login",
        data={"username": "a@example.com", "password": "Sufficiently-Long-1"},
    )
    assert r.status_code == 400


async def test_verify_then_login_succeeds(client, outbox):
    _verify_and_login(client, outbox)
    me = client.get("/api/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"
    assert me.json()["is_verified"] is True


async def test_logout_clears_session(client, outbox):
    _verify_and_login(client, outbox)
    assert client.get("/api/users/me").status_code == 200
    client.post("/api/auth/logout")
    client.cookies.clear()
    assert client.get("/api/users/me").status_code == 401


async def test_protected_routes_require_auth(client):
    # No account: personalised endpoints are closed, public ones stay open.
    assert client.get("/api/account/preferences").status_code == 401
    assert client.get("/api/account/saved").status_code == 401
    assert client.get("/api/account/alerts").status_code == 401
    assert client.get("/api/overview", params={"mode": "replay"}).status_code == 200


async def test_preferences_defaults_and_update(client, outbox):
    _verify_and_login(client, outbox)
    pref = client.get("/api/account/preferences").json()
    assert pref["email_enabled"] is False       # quiet default
    assert pref["min_research_priority"] == 60
    r = client.patch(
        "/api/account/preferences",
        json={"email_enabled": True, "min_research_priority": 75, "short_term_only": True,
              "categories": ["Politics", "Sports"]},
    )
    assert r.status_code == 200
    got = r.json()
    assert got["email_enabled"] is True
    assert got["min_research_priority"] == 75
    assert got["short_term_only"] is True
    assert sorted(got["categories"]) == ["Politics", "Sports"]


async def test_preferences_reject_out_of_range(client, outbox):
    _verify_and_login(client, outbox)
    assert client.patch(
        "/api/account/preferences", json={"min_research_priority": 500}
    ).status_code == 422
    assert client.patch(
        "/api/account/preferences", json={"min_confidence": 2.0}
    ).status_code == 422


async def test_saved_markets_roundtrip(client, outbox):
    _verify_and_login(client, outbox)
    assert client.get("/api/account/saved").json() == []
    r = client.post("/api/account/saved", json={"market_id": "m1", "question": "Will X?"})
    assert r.status_code == 201
    # Idempotent: saving again does not duplicate.
    client.post("/api/account/saved", json={"market_id": "m1", "question": "Will X?"})
    assert len(client.get("/api/account/saved").json()) == 1
    assert client.delete("/api/account/saved/m1").status_code == 204
    assert client.get("/api/account/saved").json() == []


async def test_user_data_is_isolated_between_accounts(client, outbox):
    # User A saves a market and sets a preference.
    _verify_and_login(client, outbox, email="a@example.com")
    client.post("/api/account/saved", json={"market_id": "mA", "question": "A"})
    client.patch("/api/account/preferences", json={"min_research_priority": 90})
    client.post("/api/auth/logout")
    client.cookies.clear()
    # User B sees none of A's data.
    _verify_and_login(client, outbox, email="b@example.com")
    assert client.get("/api/account/saved").json() == []
    assert client.get("/api/account/preferences").json()["min_research_priority"] == 60


async def test_account_deletion_removes_access(client, outbox):
    _verify_and_login(client, outbox)
    assert client.delete("/api/account").status_code == 204
    client.cookies.clear()
    # The credentials no longer work.
    r = client.post(
        "/api/auth/login",
        data={"username": "a@example.com", "password": "Sufficiently-Long-1"},
    )
    assert r.status_code == 400


async def test_rate_limit_on_auth_endpoints(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "account_rate_limit_per_minute", 5)
    ratelimit.reset()
    statuses = [
        client.post("/api/auth/login", data={"username": "x@y.z", "password": "nope"}).status_code
        for _ in range(7)
    ]
    assert 429 in statuses, statuses
