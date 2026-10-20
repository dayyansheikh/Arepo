"""Lab > Members: owner-only member administration (auth, guards, emails, delete scope, audit)."""
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from sqlalchemy import func, select

from astrolabe.accounts import db as accounts_db
from astrolabe.accounts import email as account_email
from astrolabe.accounts import ratelimit
from astrolabe.accounts.models import (
    AccountDeletionAudit,
    AlertDelivery,
    AlertPreference,
    DigestDelivery,
    DigestEntry,
    SavedMarket,
    User,
)
from astrolabe.alerts.provider import OutboxProvider
from astrolabe.api.app import create_app
from astrolabe.domain.models import utcnow
from astrolabe.lab import admin
from astrolabe.lab.models import LabAdminAudit, LabCommand, LabSnapshot
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

PW = "Sufficiently-Long-1"
NEW_PW = "Another-Long-Pass-2"
OWNER = "owner@example.com"
BASE = "/api/lab/admin"
_hasher = PasswordHelper()


@pytest.fixture
async def env():
    box = OutboxProvider()
    account_email.set_provider_override(box)
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)

    async def override_session():
        async with sm() as session:
            yield session

    app = create_app()
    app.dependency_overrides[accounts_db.get_async_session] = override_session
    ratelimit.reset()
    with TestClient(app) as c:
        yield c, sm, box
    await engine.dispose()
    account_email.set_provider_override(None)


async def _user(sm, email, *, verified=True, active=True, superuser=False, first="Ada"):
    async with sm() as s:
        u = User(
            id=uuid.uuid4(), email=email, hashed_password=_hasher.hash(PW),
            is_active=active, is_verified=verified, is_superuser=superuser,
            first_name=first, last_name="Member",
        )
        s.add(u)
        await s.commit()
        return u.id


def _login(client, email):
    ratelimit.reset()
    r = client.post("/api/auth/login", data={"username": email, "password": PW})
    assert r.status_code in (200, 204), r.text
    return client


async def _owner(env):
    client, sm, _ = env
    oid = await _user(sm, OWNER, superuser=True)
    _login(client, OWNER)
    return client, oid


async def _get(sm, uid):
    async with sm() as s:
        return await s.get(User, uid)


async def _audit_actions(sm):
    async with sm() as s:
        rows = await s.execute(select(LabAdminAudit).order_by(LabAdminAudit.id))
        return [r.action for r in rows.scalars()]


# ---- auth -----------------------------------------------------------------------------------
async def test_signed_out_is_401_everywhere(env):
    client, sm, _ = env
    uid = await _user(sm, "m@example.com")
    calls = [
        ("GET", f"{BASE}/users", None), ("GET", f"{BASE}/audit", None),
        ("POST", f"{BASE}/users/{uid}/password-reset", None),
        ("POST", f"{BASE}/users/{uid}/verification-email", None),
        ("POST", f"{BASE}/users/{uid}/verify", None),
        ("POST", f"{BASE}/users/{uid}/suspend", None),
        ("POST", f"{BASE}/users/{uid}/restore", None),
        ("POST", f"{BASE}/users/{uid}/admin", {"grant": True, "confirm_email": "m@example.com"}),
        ("DELETE", f"{BASE}/users/{uid}", {"confirm_email": "m@example.com"}),
    ]
    for method, path, body in calls:
        assert client.request(method, path, json=body).status_code == 401, path


async def test_non_superuser_gets_404(env):
    client, sm, _ = env
    uid = await _user(sm, "m@example.com")
    _login(client, "m@example.com")
    assert client.get(f"{BASE}/users").status_code == 404
    assert client.get(f"{BASE}/audit").status_code == 404
    assert client.post(f"{BASE}/users/{uid}/verify").status_code == 404
    r = client.request("DELETE", f"{BASE}/users/{uid}", json={"confirm_email": "m@example.com"})
    assert r.status_code == 404
    assert await _get(sm, uid) is not None


async def test_foreign_origin_rejected(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "m@example.com", verified=False)
    r = client.post(f"{BASE}/users/{uid}/verify", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert (await _get(sm, uid)).is_verified is False


# ---- list -----------------------------------------------------------------------------------
async def test_list_members_with_data_counts_and_no_secrets(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "m@example.com", verified=False)
    async with sm() as s:
        s.add(AlertPreference(user_id=str(uid)))
        s.add_all([SavedMarket(user_id=str(uid), market_id=f"m{i}") for i in range(2)])
        s.add(AlertDelivery(user_id=str(uid), market_id="m1", status="sent"))
        s.add(DigestDelivery(user_id=str(uid), due_window_key="w1", frequency="daily", top_n=5))
        await s.commit()
    r = client.get(f"{BASE}/users")
    assert r.status_code == 200
    assert "hashed_password" not in r.text and "$argon2" not in r.text
    assert r.json()["me"] == str(oid)
    users = {u["email"]: u for u in r.json()["users"]}
    m = users["m@example.com"]
    assert m["id"] == str(uid)
    assert m["is_verified"] is False and m["is_active"] is True and m["is_superuser"] is False
    assert m["created_at"]
    assert m["data"] == {"alert_preferences": 1, "saved_markets": 2, "alert_deliveries": 1,
                         "digest_deliveries": 1}
    assert users[OWNER]["is_superuser"] is True
    assert users[OWNER]["data"] == {"alert_preferences": 0, "saved_markets": 0,
                                    "alert_deliveries": 0, "digest_deliveries": 0}
    assert set(m) == {"id", "email", "first_name", "last_name", "is_active", "is_verified",
                      "is_superuser", "created_at", "data"}


async def test_unknown_member_is_404_and_bad_id_422(env):
    client, _ = await _owner(env)
    assert client.post(f"{BASE}/users/{uuid.uuid4()}/verify").status_code == 404
    assert client.post(f"{BASE}/users/not-a-uuid/verify").status_code == 422


# ---- emails (standard fastapi-users flows) --------------------------------------------------
async def test_password_reset_sends_standard_reset_email(env):
    client, _ = await _owner(env)
    _, sm, box = env
    uid = await _user(sm, "m@example.com")
    r = client.post(f"{BASE}/users/{uid}/password-reset")
    assert r.status_code == 200
    assert "token" not in r.text and "hashed_password" not in r.text
    msg = box.sent[-1]
    assert msg.to == "m@example.com" and msg.subject == "Reset your Arepo password"
    token = parse_qs(urlparse(msg.template_variables["RESET_URL"]).query)["token"][0]
    # The token is a genuine fastapi-users reset token: the member can use it themselves.
    ratelimit.reset()
    ok = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PW})
    assert ok.status_code == 200
    assert await _audit_actions(sm) == ["password_reset"]


async def test_password_reset_refused_for_suspended(env):
    client, _ = await _owner(env)
    _, sm, box = env
    uid = await _user(sm, "m@example.com", active=False)
    before = len(box.sent)
    assert client.post(f"{BASE}/users/{uid}/password-reset").status_code == 409
    assert len(box.sent) == before
    assert await _audit_actions(sm) == []


async def test_verification_email_and_already_verified(env):
    client, oid = await _owner(env)
    _, sm, box = env
    uid = await _user(sm, "new@example.com", verified=False)
    r = client.post(f"{BASE}/users/{uid}/verification-email")
    assert r.status_code == 200
    assert box.sent[-1].to == "new@example.com"
    assert "VERIFY_URL" in box.sent[-1].template_variables
    before = len(box.sent)
    assert client.post(f"{BASE}/users/{oid}/verification-email").status_code == 409
    assert len(box.sent) == before
    assert await _audit_actions(sm) == ["verification_email"]


# ---- verify / suspend / restore -------------------------------------------------------------
async def test_verify_marks_verified_once(env):
    client, _ = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "new@example.com", verified=False)
    r = client.post(f"{BASE}/users/{uid}/verify")
    assert r.status_code == 200 and r.json()["is_verified"] is True
    assert (await _get(sm, uid)).is_verified is True
    assert client.post(f"{BASE}/users/{uid}/verify").status_code == 409
    assert await _audit_actions(sm) == ["verify"]


async def test_suspend_and_restore(env):
    client, _ = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "m@example.com")
    r = client.post(f"{BASE}/users/{uid}/suspend")
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.post(f"{BASE}/users/{uid}/suspend").status_code == 409
    r = client.post(f"{BASE}/users/{uid}/restore")
    assert r.status_code == 200 and r.json()["is_active"] is True
    assert client.post(f"{BASE}/users/{uid}/restore").status_code == 409
    assert await _audit_actions(sm) == ["suspend", "restore"]


async def test_cannot_suspend_self_or_an_admin(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    other_admin = await _user(sm, "a2@example.com", superuser=True)
    assert client.post(f"{BASE}/users/{oid}/suspend").status_code == 409
    assert client.post(f"{BASE}/users/{other_admin}/suspend").status_code == 409
    assert (await _get(sm, oid)).is_active is True
    assert (await _get(sm, other_admin)).is_active is True
    assert await _audit_actions(sm) == []


# ---- admin grant / revoke -------------------------------------------------------------------
async def test_grant_and_revoke_admin(env):
    client, _ = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "m@example.com")
    bad = client.post(f"{BASE}/users/{uid}/admin",
                      json={"grant": True, "confirm_email": "other@example.com"})
    assert bad.status_code == 422
    r = client.post(f"{BASE}/users/{uid}/admin",
                    json={"grant": True, "confirm_email": " M@Example.com "})
    assert r.status_code == 200 and r.json()["is_superuser"] is True
    assert client.post(f"{BASE}/users/{uid}/admin",
                       json={"grant": True, "confirm_email": "m@example.com"}).status_code == 409
    r = client.post(f"{BASE}/users/{uid}/admin",
                    json={"grant": False, "confirm_email": "m@example.com"})
    assert r.status_code == 200 and r.json()["is_superuser"] is False
    assert await _audit_actions(sm) == ["admin_grant", "admin_revoke"]


async def test_grant_refused_for_unverified_or_suspended(env):
    client, _ = await _owner(env)
    _, sm, _ = env
    unverified = await _user(sm, "u@example.com", verified=False)
    suspended = await _user(sm, "s@example.com", active=False)
    for uid, email in ((unverified, "u@example.com"), (suspended, "s@example.com")):
        r = client.post(f"{BASE}/users/{uid}/admin", json={"grant": True, "confirm_email": email})
        assert r.status_code == 409
        assert (await _get(sm, uid)).is_superuser is False


async def test_cannot_revoke_self(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    await _user(sm, "a2@example.com", superuser=True)
    r = client.post(f"{BASE}/users/{oid}/admin", json={"grant": False, "confirm_email": OWNER})
    assert r.status_code == 409
    assert (await _get(sm, oid)).is_superuser is True


async def test_cannot_revoke_last_effective_admin(env):
    # Through the API the actor is always an effective admin, so this guard is defence in depth;
    # exercise it at the service layer with an actor that is no longer an effective admin.
    _, sm, _ = env
    actor_id = await _user(sm, "stale@example.com", superuser=True, verified=False)
    last_id = await _user(sm, "last@example.com", superuser=True)
    async with sm() as s:
        actor, target = await s.get(User, actor_id), await s.get(User, last_id)
        with pytest.raises(admin.AdminError) as exc:
            await admin.set_admin(s, actor, target, False, "last@example.com", utcnow())
        assert exc.value.status == 409 and "last remaining admin" in exc.value.message
    assert (await _get(sm, last_id)).is_superuser is True


# ---- delete ---------------------------------------------------------------------------------
async def _table_counts(sm) -> dict[str, int]:
    async with sm() as s:
        out = {}
        for table in Base.metadata.sorted_tables:
            n = await s.execute(select(func.count()).select_from(table))
            out[table.name] = n.scalar_one()
        return out


async def _seed_member_data(sm, uid, market_prefix):
    async with sm() as s:
        s.add(AlertPreference(user_id=str(uid)))
        s.add(SavedMarket(user_id=str(uid), market_id=f"{market_prefix}1"))
        s.add(AlertDelivery(user_id=str(uid), market_id=f"{market_prefix}1", status="sent"))
        d = DigestDelivery(user_id=str(uid), due_window_key="w1", frequency="daily", top_n=5)
        s.add(d)
        await s.flush()
        s.add(DigestEntry(digest_id=d.id, rank=1, market_id=f"{market_prefix}1", token_id="t",
                          market_question="q", direction="up", strength=0.5,
                          research_priority=50, signal_captured_at=utcnow()))
        await s.commit()


async def test_delete_removes_only_that_members_rows(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    victim = await _user(sm, "gone@example.com")
    keeper = await _user(sm, "keep@example.com")
    await _seed_member_data(sm, victim, "v")
    await _seed_member_data(sm, keeper, "k")
    async with sm() as s:  # non-account rows that must never be touched
        s.add(LabSnapshot(source="host", payload="{}", payload_sha256="x", size_bytes=2))
        s.add(LabCommand(target="queue", action="pause", created_by=str(victim)))
        await s.commit()
    before = await _table_counts(sm)

    r = client.request("DELETE", f"{BASE}/users/{victim}",
                       json={"confirm_email": "gone@example.com"})
    assert r.status_code == 200
    assert r.json() == {"deleted": str(victim), "removed": {
        "alert_preferences": 1, "saved_markets": 1, "alert_deliveries": 1,
        "digest_deliveries": 1}}

    after = await _table_counts(sm)
    expected = dict(before)
    for name in ("alert_preferences", "saved_markets", "alert_deliveries", "digest_deliveries",
                 "digest_entries", "users"):
        expected[name] -= 1
    expected["account_deletions"] += 1
    expected["lab_admin_audit"] += 1
    assert after == expected
    assert await _get(sm, victim) is None and await _get(sm, keeper) is not None
    async with sm() as s:
        assert (await s.execute(select(func.count()).select_from(SavedMarket)
                                .where(SavedMarket.user_id == str(keeper)))).scalar_one() == 1
        deletion = (await s.execute(select(AccountDeletionAudit))).scalar_one()
        assert deletion.reason == "owner_admin" and "gone@" not in deletion.email_hash
        row = (await s.execute(select(LabAdminAudit))).scalar_one()
        assert row.action == "delete" and row.target_email == "g***@example.com"
        assert row.actor_user_id == str(oid) and row.actor_email == OWNER
        assert '"saved_markets": 1' in row.detail
        assert f'"email_sha256": "{deletion.email_hash}"' in row.detail
        assert "gone@example.com" not in row.detail


async def test_delete_masks_every_audit_row_naming_the_member(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    victim = await _user(sm, "gone@example.com", verified=False)
    keeper = await _user(sm, "keep@example.com", verified=False)
    for uid in (victim, keeper):
        assert client.post(f"{BASE}/users/{uid}/verify").status_code == 200
    assert client.post(f"{BASE}/users/{victim}/suspend").status_code == 200
    assert client.post(f"{BASE}/users/{victim}/restore").status_code == 200
    async with sm() as s:  # an earlier row where the deleted member was the actor
        s.add(LabAdminAudit(at=utcnow(), actor_user_id=str(victim), actor_email="gone@example.com",
                            action="verify", target_user_id=str(keeper),
                            target_email="keep@example.com"))
        await s.commit()
    async with sm() as s:
        keeper_before = [
            (r.id, r.actor_email, r.target_email, r.detail)
            for r in (await s.execute(select(LabAdminAudit).where(
                LabAdminAudit.target_user_id == str(keeper),
                LabAdminAudit.actor_user_id != str(victim)))).scalars()
        ]

    r = client.request("DELETE", f"{BASE}/users/{victim}",
                       json={"confirm_email": "gone@example.com"})
    assert r.status_code == 200

    async with sm() as s:
        rows = list((await s.execute(select(LabAdminAudit))).scalars())
        for row in rows:
            text = " ".join(str(v) for v in (row.actor_email, row.target_email, row.detail))
            assert "gone@example.com" not in text.lower()
        about_victim = [x for x in rows if x.target_user_id == str(victim)]
        assert {x.action for x in about_victim} == {"verify", "suspend", "restore", "delete"}
        assert {x.target_email for x in about_victim} == {"g***@example.com"}
        assert all(x.actor_email == OWNER for x in about_victim)
        by_victim = [x for x in rows if x.actor_user_id == str(victim)]
        assert [(x.actor_email, x.target_email) for x in by_victim] == [
            ("g***@example.com", "keep@example.com")]
        keeper_after = [
            (x.id, x.actor_email, x.target_email, x.detail) for x in rows
            if x.target_user_id == str(keeper) and x.actor_user_id != str(victim)
        ]
        assert keeper_after == keeper_before and keeper_after


def test_mask_email():
    assert admin.mask_email("dayyan@gmail.com") == "d***@gmail.com"
    assert admin.mask_email(" A@b.co ") == "A***@b.co"
    assert admin.mask_email("no-at-sign") == "***"
    assert admin.mask_email(None) == "***"


async def test_delete_guards(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    member = await _user(sm, "m@example.com")
    other_admin = await _user(sm, "a2@example.com", superuser=True)

    def delete(uid, email):
        return client.request("DELETE", f"{BASE}/users/{uid}", json={"confirm_email": email})

    assert delete(member, "wrong@example.com").status_code == 422
    assert client.request("DELETE", f"{BASE}/users/{member}").status_code == 422  # no body
    assert delete(oid, OWNER).status_code == 409
    assert delete(other_admin, "a2@example.com").status_code == 409
    for uid in (member, oid, other_admin):
        assert await _get(sm, uid) is not None
    assert await _audit_actions(sm) == []


# ---- audit + rate limit ---------------------------------------------------------------------
async def test_audit_endpoint_lists_newest_first(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "m@example.com", verified=False)
    client.post(f"{BASE}/users/{uid}/verify")
    client.post(f"{BASE}/users/{uid}/suspend")
    r = client.get(f"{BASE}/audit")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert [e["action"] for e in entries] == ["suspend", "verify"]
    assert entries[0]["target_email"] == "m@example.com" and entries[0]["actor_email"] == OWNER
    assert entries[0]["actor_user_id"] == str(oid) and entries[0]["at"]


async def test_audit_endpoint_is_capped_at_50(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    async with sm() as s:
        s.add_all([LabAdminAudit(at=utcnow(), actor_user_id="x", actor_email="x@example.com",
                                 action="verify") for _ in range(60)])
        await s.commit()
    assert len(client.get(f"{BASE}/audit").json()["entries"]) == 50


async def test_email_actions_rate_limited(env):
    client, oid = await _owner(env)
    _, sm, box = env
    uid = await _user(sm, "m@example.com")
    async with sm() as s:
        s.add_all([LabAdminAudit(at=utcnow(), actor_user_id=str(oid), actor_email=OWNER,
                                 action="password_reset", target_user_id=str(uid))
                   for _ in range(admin.MAX_EMAIL_ACTIONS_PER_HOUR)])
        await s.commit()
    before = len(box.sent)
    r = client.post(f"{BASE}/users/{uid}/password-reset")
    assert r.status_code == 429
    assert len(box.sent) == before
    # Non-email actions still have headroom under the general cap.
    assert client.post(f"{BASE}/users/{uid}/suspend").status_code == 200


async def test_all_actions_rate_limited(env):
    client, oid = await _owner(env)
    _, sm, _ = env
    uid = await _user(sm, "m@example.com", verified=False)
    async with sm() as s:
        s.add_all([LabAdminAudit(at=utcnow(), actor_user_id=str(oid), actor_email=OWNER,
                                 action="restore") for _ in range(admin.MAX_ACTIONS_PER_HOUR)])
        await s.commit()
    assert client.post(f"{BASE}/users/{uid}/verify").status_code == 429
    assert (await _get(sm, uid)).is_verified is False


# ---- migration ------------------------------------------------------------------------------
async def test_migration_registers_audit_table_with_rls():
    from sqlalchemy import inspect

    from astrolabe.storage.migrate import _PRIVATE_ACCOUNT_TABLES, SCHEMA_VERSION, check, upgrade
    assert SCHEMA_VERSION >= 15
    assert "lab_admin_audit" in _PRIVATE_ACCOUNT_TABLES
    eng = make_engine("sqlite+aiosqlite:///:memory:")
    await upgrade(eng)
    assert (await check(eng))["current"] is True
    async with eng.connect() as conn:
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    assert "lab_admin_audit" in tables
    await eng.dispose()
