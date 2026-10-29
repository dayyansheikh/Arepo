"""Security hardening of the account surface (audit run 1)."""
# ruff: noqa: F811  (pytest fixtures imported from test_accounts)
from __future__ import annotations

from tests.unit.test_accounts import (  # noqa: F401 - fixtures + helpers
    _verify_and_login,
    client,
    outbox,
)


async def test_password_change_requires_current_password_and_invalidates_old_session(
    client, outbox
):
    _verify_and_login(client, outbox)
    old_cookie = client.cookies.get("arepo_auth")
    assert client.get("/api/users/me").status_code == 200

    new = {"password": "Brand-New-Long-Pass-3"}
    assert client.patch("/api/users/me", json=new).status_code == 400
    assert client.patch(
        "/api/users/me", json={**new, "current_password": "nope"}
    ).status_code == 400
    assert client.patch("/api/users/me", json={"email": "evil@example.com"}).status_code == 400
    # harmless fields need no current password
    assert client.patch("/api/users/me", json={"first_name": "Grace"}).status_code == 200

    ok = client.patch(
        "/api/users/me", json={**new, "current_password": "Sufficiently-Long-1"}
    )
    assert ok.status_code == 200
    # the pre-change session token no longer authenticates
    client.cookies.clear()
    client.cookies.set("arepo_auth", old_cookie)
    assert client.get("/api/users/me").status_code == 401


async def test_users_id_routes_not_mounted(client, outbox):
    _verify_and_login(client, outbox)
    me_id = client.get("/api/users/me").json()["id"]
    assert client.get(f"/api/users/{me_id}").status_code == 404
    assert client.delete(f"/api/users/{me_id}").status_code in (404, 405)


async def test_saved_market_field_limits_cap_and_rate_limit(client, outbox, monkeypatch):
    from astrolabe.accounts import ratelimit, service
    from astrolabe.config import get_settings

    _verify_and_login(client, outbox)
    ratelimit.reset()
    url = "/api/account/saved"
    assert client.post(url, json={"market_id": "m" * 129, "question": "q"}).status_code == 422
    assert client.post(url, json={"market_id": "m1", "question": "q" * 501}).status_code == 422
    assert client.post(url, json={"market_id": "", "question": "q"}).status_code == 422

    monkeypatch.setattr(service, "MAX_SAVED_PER_USER", 2)
    assert client.post(url, json={"market_id": "a"}).status_code == 201
    assert client.post(url, json={"market_id": "b"}).status_code == 201
    assert client.post(url, json={"market_id": "a"}).status_code == 201  # idempotent, not counted
    assert client.post(url, json={"market_id": "c"}).status_code == 409

    monkeypatch.setattr(get_settings(), "account_rate_limit_per_minute", 2)
    ratelimit.reset()
    codes = [client.post(url, json={"market_id": "a"}).status_code for _ in range(4)]
    assert 429 in codes, codes
