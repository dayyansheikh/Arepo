"""Security-key (WebAuthn) step-up: real py_webauthn verification against a software authenticator.

Covers registration, authentication, multiple credentials, sign-count regression, single-use
challenges, step-up expiry, site-wide enforcement (auto-on after the first key, 403
``hardware_key_required``), exemptions (sign-out, unlock endpoints, machine-signed agent
endpoints), last-key protection, recovery codes (single use, rate limited) and the migration.
"""
import base64
import hashlib
import json
import os
import time
import uuid
from datetime import timedelta

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from sqlalchemy import delete, func, select, update

from astrolabe.accounts import db as accounts_db
from astrolabe.accounts import email as account_email
from astrolabe.accounts import ratelimit
from astrolabe.accounts.models import User
from astrolabe.accounts.service import delete_account
from astrolabe.alerts.provider import OutboxProvider
from astrolabe.api.app import create_app
from astrolabe.config import Settings, get_settings
from astrolabe.domain.models import utcnow
from astrolabe.lab import security_keys as sk
from astrolabe.lab import signing
from astrolabe.lab.client_sign import sign
from astrolabe.lab.models import LabAdminAudit
from astrolabe.lab.security_models import (
    AdminRecoveryCode,
    AdminStepUpSession,
    AdminTrustedDevice,
    AdminWebAuthnChallenge,
    AdminWebAuthnCredential,
)
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

PW = "Sufficiently-Long-1"
OWNER = "owner@example.com"
ORIGIN = "http://localhost:3000"
W = "/api/lab/webauthn"
_hasher = PasswordHelper()


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class SoftKey:
    """Minimal FIDO2 software authenticator (ES256, "none" attestation)."""

    def __init__(self, transports=("usb",), backed_up=False):
        self.priv = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = os.urandom(32)
        self.count = 0
        self.transports = list(transports)
        self.backed_up = backed_up

    def _cose(self) -> bytes:
        n = self.priv.public_key().public_numbers()
        return cbor2.dumps({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"),
                            -3: n.y.to_bytes(32, "big")})

    @staticmethod
    def _cd(kind: str, challenge: str, origin: str) -> bytes:
        return json.dumps({"type": kind, "challenge": challenge, "origin": origin,
                           "crossOrigin": False}).encode()

    def _flags(self, extra: int) -> int:
        f = 0x01 | 0x04 | extra  # UP | UV
        if self.backed_up:
            f |= 0x08 | 0x10  # BE | BS
        return f

    def register(self, options: dict, origin: str = ORIGIN) -> dict:
        pk = options["publicKey"]
        cd = self._cd("webauthn.create", pk["challenge"], origin)
        auth = (hashlib.sha256(pk["rp"]["id"].encode()).digest()
                + bytes([self._flags(0x40)]) + self.count.to_bytes(4, "big")
                + b"\x00" * 16 + len(self.cred_id).to_bytes(2, "big") + self.cred_id
                + self._cose())
        att = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth})
        return {"id": b64u(self.cred_id), "rawId": b64u(self.cred_id), "type": "public-key",
                "response": {"clientDataJSON": b64u(cd), "attestationObject": b64u(att),
                             "transports": self.transports},
                "clientExtensionResults": {}}

    def assertion(self, options: dict, origin: str = ORIGIN, count: int | None = None,
                  user_handle: bytes | None = None) -> dict:
        pk = options["publicKey"]
        if count is None:
            self.count += 1
            count = self.count
        cd = self._cd("webauthn.get", pk["challenge"], origin)
        auth = (hashlib.sha256(pk["rpId"].encode()).digest() + bytes([self._flags(0)])
                + count.to_bytes(4, "big"))
        sig = self.priv.sign(auth + hashlib.sha256(cd).digest(), ec.ECDSA(hashes.SHA256()))
        resp = {"clientDataJSON": b64u(cd), "authenticatorData": b64u(auth),
                "signature": b64u(sig)}
        if user_handle is not None:
            resp["userHandle"] = b64u(user_handle)
        return {"id": b64u(self.cred_id), "rawId": b64u(self.cred_id), "type": "public-key",
                "response": resp, "clientExtensionResults": {}}


@pytest.fixture
def machine_keys():
    k = {"host": Ed25519PrivateKey.generate()}
    raw = k["host"].public_key().public_bytes(serialization.Encoding.Raw,
                                              serialization.PublicFormat.Raw)
    signing.set_public_keys_override({"host": base64.b64encode(raw).decode()})
    yield k
    signing.set_public_keys_override(None)


@pytest.fixture
async def env(machine_keys):
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
        yield c, sm, machine_keys
    await engine.dispose()
    account_email.set_provider_override(None)


@pytest.fixture
def mode(monkeypatch):
    def _set(value: str):
        monkeypatch.setattr(get_settings(), "lab_require_hardware_key", value)
    return _set


async def _user(sm, email, *, superuser=False):
    async with sm() as s:
        u = User(id=uuid.uuid4(), email=email, hashed_password=_hasher.hash(PW),
                 is_active=True, is_verified=True, is_superuser=superuser,
                 first_name="Ada", last_name="Owner")
        s.add(u)
        await s.commit()
        return u.id


def _login(client, email):
    ratelimit.reset()
    r = client.post("/api/auth/login", data={"username": email, "password": PW})
    assert r.status_code in (200, 204), r.text


async def _owner(env):
    client, sm, _ = env
    oid = await _user(sm, OWNER, superuser=True)
    _login(client, OWNER)
    return client, sm, oid


def _register(client, key: SoftKey, nickname="YubiKey"):
    opts = client.post(f"{W}/registration/options")
    assert opts.status_code == 200, opts.text
    return client.post(f"{W}/registration/verify",
                       json={"credential": key.register(opts.json()), "nickname": nickname})


def _unlock(client, key: SoftKey, **kw):
    opts = client.post(f"{W}/authentication/options")
    assert opts.status_code == 200, opts.text
    return client.post(f"{W}/authentication/verify",
                       json={"credential": key.assertion(opts.json(), **kw)})


def _drop_stepup(client):
    for c in list(client.cookies.jar):
        if c.name == sk.STEPUP_COOKIE:
            client.cookies.jar.clear(c.domain, c.path, c.name)


def _locked(r) -> bool:
    return r.status_code == 403 and r.json()["detail"]["code"] == "hardware_key_required"


# ---- registration + enforcement ---------------------------------------------------------------
async def test_first_key_registers_with_password_and_turns_enforcement_on(env):
    client, sm, oid = await _owner(env)
    assert client.get("/api/lab/dashboard").status_code == 200  # no key yet: not enforced
    st = client.get(f"{W}/status").json()
    assert st["keys"] == 0 and st["required"] is False and st["enforcement"] == "auto"

    r = _register(client, SoftKey(), "MacBook Touch ID")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["key"]["nickname"] == "MacBook Touch ID"
    codes = body["recovery_codes"]
    assert len(codes) == sk.RECOVERY_CODE_COUNT and len(set(codes)) == len(codes)
    # Registering the first key proved possession, so this browser is unlocked.
    assert client.get("/api/lab/dashboard").status_code == 200
    st = client.get(f"{W}/status").json()
    assert st["required"] is True and st["step_up"]["active"] is True

    async with sm() as s:
        stored = (await s.execute(select(AdminRecoveryCode.code_hash))).scalars().all()
        audit = (await s.execute(select(LabAdminAudit.action))).scalars().all()
    assert len(stored) == len(codes)
    assert all(c not in h for c in codes for h in stored)  # hashed, never plain
    assert all(h.startswith("$argon2") for h in stored)
    assert "security_key_registered" in audit

    _drop_stepup(client)
    for path in ("/api/lab/dashboard", "/api/lab/admin/users", "/api/lab/admin/audit",
                 "/api/users/me", "/api/account/preferences", "/api/account/saved",
                 f"{W}/keys"):
        r = client.get(path)
        assert _locked(r), (path, r.status_code, r.text)
        assert r.json()["detail"]["keys"] == 1
    assert _locked(client.post("/api/lab/commands", json={"target": "queue", "action": "pause"}))


async def test_unlock_with_key_sets_stepup_and_updates_sign_count(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    _drop_stepup(client)
    assert _locked(client.get("/api/users/me"))

    r = _unlock(client, key)
    assert r.status_code == 200, r.text
    assert r.json()["step_up"]["active"] is True
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie and "samesite=strict" in set_cookie
    assert "path=/api" in set_cookie
    assert client.get("/api/users/me").status_code == 200
    assert client.get("/api/lab/dashboard").status_code == 200
    assert client.get("/api/lab/admin/users").status_code == 200
    async with sm() as s:
        row = (await s.execute(select(AdminWebAuthnCredential))).scalar_one()
        stepup = (await s.execute(select(AdminStepUpSession).where(
            AdminStepUpSession.method == "key"))).scalar_one()
    assert row.sign_count == 1 and row.last_used_at is not None
    # Default validity is 4 hours.
    exp = stepup.expires_at.replace(tzinfo=None) - stepup.created_at.replace(tzinfo=None)
    assert exp == timedelta(hours=4)


async def test_multiple_credentials_each_unlock(env):
    client, sm, _ = await _owner(env)
    touch_id = SoftKey(transports=("internal", "hybrid"), backed_up=True)
    iphone = SoftKey(transports=("hybrid",), backed_up=True)
    yubikey = SoftKey(transports=("usb", "nfc"))
    assert _register(client, touch_id, "MacBook Touch ID").status_code == 201
    r = _register(client, iphone, "iPhone")  # unlocked by the first registration
    assert r.status_code == 201 and r.json()["recovery_codes"] is None
    assert _register(client, yubikey, "YubiKey").status_code == 201

    keys = client.get(f"{W}/keys").json()["keys"]
    assert [k["nickname"] for k in keys] == ["MacBook Touch ID", "iPhone", "YubiKey"]
    assert keys[0]["synced"] is True and keys[2]["synced"] is False
    assert keys[2]["transports"] == ["usb", "nfc"]

    for key in (touch_id, iphone, yubikey):
        _drop_stepup(client)
        assert _locked(client.get("/api/lab/dashboard"))
        assert _unlock(client, key).status_code == 200
        assert client.get("/api/lab/dashboard").status_code == 200
    # Allow-list in the options names every registered credential.
    opts = client.post(f"{W}/authentication/options").json()["publicKey"]
    assert len(opts["allowCredentials"]) == 3
    assert opts["userVerification"] == "preferred"


async def test_registration_options_are_unrestricted_and_exclude_existing(env):
    client, _, _ = await _owner(env)
    opts = client.post(f"{W}/registration/options").json()["publicKey"]
    sel = opts["authenticatorSelection"]
    assert "authenticatorAttachment" not in sel  # USB keys AND platform passkeys
    assert sel["residentKey"] == "preferred" and sel["userVerification"] == "preferred"
    assert opts["rp"]["id"] == "localhost"
    assert opts["attestation"] == "none"
    key = SoftKey()
    client.post(f"{W}/registration/verify", json={"credential": key.register({"publicKey": opts})})
    opts2 = client.post(f"{W}/registration/options").json()["publicKey"]
    assert [c["id"] for c in opts2["excludeCredentials"]] == [b64u(key.cred_id)]


async def test_additional_key_requires_stepup(env):
    client, _, _ = await _owner(env)
    first = SoftKey()
    assert _register(client, first).status_code == 201
    _drop_stepup(client)
    assert _locked(client.post(f"{W}/registration/options"))
    assert _unlock(client, first).status_code == 200
    assert _register(client, SoftKey(), "Spare").status_code == 201


async def test_duplicate_credential_rejected(env):
    client, _, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    assert _register(client, key).status_code == 409


# ---- verification failures --------------------------------------------------------------------
async def test_sign_count_regression_rejected(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    _drop_stepup(client)
    assert _unlock(client, key, count=5).status_code == 200
    _drop_stepup(client)
    r = _unlock(client, key, count=3)  # a cloned authenticator would lag behind
    assert r.status_code == 400 and r.json()["detail"]["code"] == "verification_failed"
    assert _locked(client.get("/api/lab/dashboard"))
    async with sm() as s:
        assert (await s.execute(select(AdminWebAuthnCredential.sign_count))).scalar_one() == 5


async def test_challenge_is_single_use(env):
    client, _, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    _drop_stepup(client)
    opts = client.post(f"{W}/authentication/options").json()
    cred = key.assertion(opts)
    assert client.post(f"{W}/authentication/verify", json={"credential": cred}).status_code == 200
    _drop_stepup(client)
    replay = client.post(f"{W}/authentication/verify", json={"credential": cred})
    assert replay.status_code == 400 and replay.json()["detail"]["code"] == "challenge_invalid"


async def test_expired_challenge_rejected(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    _drop_stepup(client)
    opts = client.post(f"{W}/authentication/options").json()
    async with sm() as s:
        await s.execute(update(AdminWebAuthnChallenge).values(
            expires_at=utcnow() - timedelta(seconds=1)))
        await s.commit()
    r = client.post(f"{W}/authentication/verify", json={"credential": key.assertion(opts)})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "challenge_invalid"


async def test_wrong_origin_and_unknown_key_rejected(env):
    client, _, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    _drop_stepup(client)
    assert _unlock(client, key, origin="https://evil.example").status_code == 400
    stranger = SoftKey()
    r = _unlock(client, stranger)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "unknown_key"
    assert _locked(client.get("/api/lab/dashboard"))


async def test_registration_with_wrong_origin_rejected(env):
    client, sm, _ = await _owner(env)
    opts = client.post(f"{W}/registration/options").json()
    r = client.post(f"{W}/registration/verify",
                    json={"credential": SoftKey().register(opts, origin="https://evil.example")})
    assert r.status_code == 400
    async with sm() as s:
        assert (await s.execute(select(func.count()).select_from(AdminWebAuthnCredential))
                ).scalar_one() == 0


async def test_user_handle_mismatch_rejected(env):
    client, _, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    _drop_stepup(client)
    r = _unlock(client, key, user_handle=uuid.uuid4().bytes)
    assert r.status_code == 400


# ---- step-up lifetime -------------------------------------------------------------------------
async def test_stepup_expires(env):
    client, sm, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    assert client.get("/api/lab/dashboard").status_code == 200
    async with sm() as s:
        await s.execute(update(AdminStepUpSession).values(
            expires_at=utcnow() - timedelta(seconds=1)))
        await s.commit()
    assert _locked(client.get("/api/lab/dashboard"))
    assert _locked(client.get("/api/users/me"))


async def test_lock_now_revokes_stepup(env):
    client, _, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    assert client.get("/api/lab/dashboard").status_code == 200
    cookie = client.cookies.get(sk.STEPUP_COOKIE)
    assert client.post(f"{W}/lock").status_code == 204
    # Even replaying the old token is refused: it is revoked server-side.
    client.cookies.set(sk.STEPUP_COOKIE, cookie, path="/api")
    assert _locked(client.get("/api/lab/dashboard"))


async def test_stepup_is_bound_to_its_user(env):
    client, sm, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    token = client.cookies.get(sk.STEPUP_COOKIE)
    async with sm() as s:
        other = User(id=uuid.uuid4(), email="o2@example.com", hashed_password=_hasher.hash(PW),
                     is_active=True, is_verified=True, is_superuser=True)
        s.add(other)
        await s.commit()
        assert await sk.active_stepup(s, other, token, utcnow()) is None


# ---- exemptions + scope -----------------------------------------------------------------------
async def test_logout_and_unlock_endpoints_reachable_while_locked(env):
    client, _, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    _drop_stepup(client)
    assert client.get(f"{W}/status").status_code == 200
    assert client.post(f"{W}/authentication/options").status_code == 200
    assert client.post("/api/auth/logout").status_code in (200, 204)
    assert client.get("/api/users/me").status_code == 401  # now simply signed out
    # Login itself still works with the password; the unlock prompt follows.
    _login(client, OWNER)
    assert _locked(client.get("/api/users/me"))


async def test_machine_signed_endpoints_unaffected(env):
    client, _, machine = env
    oid = await _user(env[1], OWNER, superuser=True)
    _login(client, OWNER)
    assert _register(client, SoftKey()).status_code == 201
    _drop_stepup(client)
    assert _locked(client.get("/api/lab/dashboard"))
    body = json.dumps({"schema": "arepo-lab-v1", "source": "host",
                       "generated_at": "2026-10-18T10:00:00Z"}).encode()
    headers = sign(machine["host"], "POST", "/api/lab/agent/snapshot", body, int(time.time()),
                   source="host")
    assert client.post("/api/lab/agent/snapshot", content=body,
                       headers=headers).status_code == 204
    headers = sign(machine["host"], "GET", "/api/lab/agent/commands", b"", int(time.time()),
                   source="host")
    assert client.get("/api/lab/agent/commands", headers=headers).status_code == 200
    assert oid


async def test_users_without_keys_unaffected(env):
    client, sm, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    member = await _user(sm, "member@example.com")
    _login(client, "member@example.com")
    assert client.get("/api/users/me").status_code == 200
    assert client.get("/api/account/preferences").status_code == 200
    # The key endpoints do not reveal themselves to an ordinary member.
    assert client.get(f"{W}/status").status_code == 404
    assert client.post(f"{W}/registration/options").status_code == 404
    assert member


async def test_signed_out_and_non_owner(env):
    client, sm, _ = env
    assert client.get(f"{W}/status").status_code == 401
    assert client.post(f"{W}/registration/options").status_code == 401
    await _user(sm, "m@example.com")
    _login(client, "m@example.com")
    assert client.get(f"{W}/keys").status_code == 404


async def test_foreign_origin_rejected(env):
    client, _, _ = await _owner(env)
    r = client.post(f"{W}/registration/options", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


# ---- key management ---------------------------------------------------------------------------
async def test_rename_and_delete_with_last_key_protection(env, mode):
    client, sm, _ = await _owner(env)
    a, b = SoftKey(), SoftKey()
    assert _register(client, a, "Touch ID").status_code == 201
    assert _register(client, b, "YubiKey").status_code == 201
    keys = client.get(f"{W}/keys").json()["keys"]
    r = client.patch(f"{W}/keys/{keys[1]['id']}", json={"nickname": "  YubiKey 5C  "})
    assert r.status_code == 200 and r.json()["nickname"] == "YubiKey 5C"

    assert client.delete(f"{W}/keys/{keys[1]['id']}").json()["remaining"] == 1
    r = client.delete(f"{W}/keys/{keys[0]['id']}")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "last_key"
    assert client.delete(f"{W}/keys/999").status_code == 404

    # Management needs a step-up.
    _drop_stepup(client)
    assert _locked(client.get(f"{W}/keys"))
    assert _locked(client.delete(f"{W}/keys/{keys[0]['id']}"))

    # Operator escape hatch: with enforcement off, the last key may go.
    mode("off")
    assert client.get("/api/lab/dashboard").status_code == 200
    assert client.delete(f"{W}/keys/{keys[0]['id']}").status_code == 200
    async with sm() as s:
        actions = (await s.execute(select(LabAdminAudit.action))).scalars().all()
    assert actions.count("security_key_removed") == 2
    assert "security_key_renamed" in actions


async def test_cannot_touch_another_users_key(env):
    client, sm, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    other = await _user(sm, "o2@example.com", superuser=True)
    async with sm() as s:
        s.add(AdminWebAuthnCredential(user_id=other, credential_id="x", public_key="y",
                                      nickname="theirs"))
        await s.commit()
        theirs = (await s.execute(select(AdminWebAuthnCredential.id).where(
            AdminWebAuthnCredential.nickname == "theirs"))).scalar_one()
    assert client.delete(f"{W}/keys/{theirs}").status_code == 404
    assert client.patch(f"{W}/keys/{theirs}", json={"nickname": "mine"}).status_code == 404


# ---- recovery codes ---------------------------------------------------------------------------
async def test_recovery_code_single_use(env):
    client, sm, _ = await _owner(env)
    codes = _register(client, SoftKey()).json()["recovery_codes"]
    _drop_stepup(client)
    r = client.post(f"{W}/recovery", json={"code": codes[0].upper().replace("-", " ")})
    assert r.status_code == 200, r.text
    assert r.json()["recovery_codes_remaining"] == len(codes) - 1
    assert client.get("/api/lab/dashboard").status_code == 200
    _drop_stepup(client)
    again = client.post(f"{W}/recovery", json={"code": codes[0]})
    assert again.status_code == 400 and again.json()["detail"]["code"] == "recovery_invalid"
    assert _locked(client.get("/api/lab/dashboard"))
    async with sm() as s:
        actions = (await s.execute(select(LabAdminAudit.action))).scalars().all()
    assert "recovery_code_used" in actions and "recovery_code_failed" in actions


async def test_recovery_failures_rate_limited(env):
    client, _, _ = await _owner(env)
    codes = _register(client, SoftKey()).json()["recovery_codes"]
    _drop_stepup(client)
    for _ in range(sk.MAX_RECOVERY_FAILURES_PER_HOUR):
        assert client.post(f"{W}/recovery", json={"code": "aaaaa-bbbbb"}).status_code == 400
    # Even a correct code is refused while the limit holds.
    assert client.post(f"{W}/recovery", json={"code": codes[1]}).status_code == 429


async def test_regenerate_recovery_codes_replaces_old_set(env):
    client, _, _ = await _owner(env)
    old = _register(client, SoftKey()).json()["recovery_codes"]
    new = client.post(f"{W}/recovery-codes").json()["recovery_codes"]
    assert len(new) == sk.RECOVERY_CODE_COUNT and not set(old) & set(new)
    _drop_stepup(client)
    assert client.post(f"{W}/recovery", json={"code": old[0]}).status_code == 400
    assert client.post(f"{W}/recovery", json={"code": new[0]}).status_code == 200


# ---- modes ------------------------------------------------------------------------------------
async def test_always_mode_locks_keyless_owner_but_allows_first_registration(env, mode):
    mode("always")
    client, _, _ = await _owner(env)
    r = client.get("/api/lab/dashboard")
    assert _locked(r) and r.json()["detail"]["keys"] == 0
    assert client.get(f"{W}/status").json()["required"] is True
    assert _register(client, SoftKey()).status_code == 201
    assert client.get("/api/lab/dashboard").status_code == 200


async def test_off_mode_never_requires_stepup(env, mode):
    client, _, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    _drop_stepup(client)
    mode("off")
    assert client.get("/api/lab/dashboard").status_code == 200
    assert client.get("/api/users/me").status_code == 200


def test_unknown_mode_fails_safe_to_auto():
    assert Settings(lab_require_hardware_key="disabled").lab_hardware_key_mode == "auto"
    assert Settings(lab_require_hardware_key="OFF").lab_hardware_key_mode == "off"


def test_rp_id_and_origins_defaults():
    prod = Settings(environment="production", cors_origins="https://www.arepolabs.com,"
                    "https://arepo.vercel.app")
    assert prod.webauthn_rp_id == "arepolabs.com"
    assert prod.webauthn_origin_list == ["https://www.arepolabs.com", "https://arepolabs.com"]
    dev = Settings()
    assert dev.webauthn_rp_id == "localhost"
    assert dev.webauthn_origin_list == ["http://localhost:3000"]
    custom = Settings(lab_webauthn_rp_id="www.arepolabs.com",
                      lab_webauthn_origins="https://www.arepolabs.com/")
    assert custom.webauthn_rp_id == "www.arepolabs.com"
    assert custom.webauthn_origin_list == ["https://www.arepolabs.com"]


# ---- data lifecycle ---------------------------------------------------------------------------
async def test_account_deletion_removes_key_rows(env):
    client, sm, oid = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    async with sm() as s:
        await delete_account(s, await s.get(User, oid))
    async with sm() as s:
        for model in (AdminWebAuthnCredential, AdminStepUpSession, AdminRecoveryCode,
                      AdminWebAuthnChallenge, AdminTrustedDevice):
            n = (await s.execute(select(func.count()).select_from(model))).scalar_one()
            assert n == 0, model.__tablename__


async def test_migration_creates_key_tables_with_rls():
    from sqlalchemy import inspect

    from astrolabe.storage.migrate import _PRIVATE_ACCOUNT_TABLES, SCHEMA_VERSION, check, upgrade
    names = {"admin_webauthn_credentials", "admin_webauthn_challenges", "admin_stepup_sessions",
             "admin_recovery_codes", "admin_trusted_devices"}
    assert SCHEMA_VERSION >= 18
    assert names <= set(_PRIVATE_ACCOUNT_TABLES)
    eng = make_engine("sqlite+aiosqlite:///:memory:")
    await upgrade(eng)
    assert (await check(eng))["current"] is True
    async with eng.connect() as conn:
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    assert names <= tables
    await eng.dispose()


async def test_claude_board_messages_and_commands_require_stepup(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    msg = {"target": "autopilot-signal", "body": "hello"}
    assert client.post("/api/lab/messages", json=msg).status_code == 201  # unlocked
    _drop_stepup(client)
    assert _locked(client.post("/api/lab/messages", json=msg))
    assert _locked(client.post("/api/lab/messages/1/cancel"))
    assert _locked(client.post("/api/lab/commands", json={"target": "autopilot-signal",
                                                          "action": "start"}))
    assert _unlock(client, key).status_code == 200
    assert client.post("/api/lab/messages/1/cancel").status_code == 200


# ---- method steering (hints / transports / attachment) ----------------------------------------
async def test_authentication_options_steer_by_method(env):
    client, _, _ = await _owner(env)
    passkey = SoftKey(transports=("hybrid", "internal"), backed_up=True)
    yubikey = SoftKey(transports=("usb", "nfc"))
    assert _register(client, passkey, "Dayyan's MacBook Touch ID").status_code == 201
    assert _register(client, yubikey, "YubiKey").status_code == 201
    ids = sorted([b64u(passkey.cred_id), b64u(yubikey.cred_id)])

    def opts(body=None):
        r = client.post(f"{W}/authentication/options", json=body)
        assert r.status_code == 200, r.text
        return r.json()["publicKey"]

    # No body / "any": unchanged behaviour (stored transports, no hints).
    for pk in (opts(), opts({"method": "any"})):
        assert "hints" not in pk
        assert {c["id"]: c.get("transports") for c in pk["allowCredentials"]} == {
            b64u(passkey.cred_id): ["hybrid", "internal"], b64u(yubikey.cred_id): ["usb", "nfc"]}
    expected = {
        "device": (["client-device"], ["internal"]),
        "phone": (["hybrid"], ["hybrid"]),
        "security_key": (["security-key"], ["usb", "nfc", "ble"]),
    }
    for method, (hints, transports) in expected.items():
        pk = opts({"method": method})
        assert pk["hints"] == hints, method
        # Every credential id is kept (a synced passkey must stay usable from the phone).
        assert sorted(c["id"] for c in pk["allowCredentials"]) == ids, method
        assert all(c["transports"] == transports for c in pk["allowCredentials"]), method
        assert pk["userVerification"] == "preferred"
    assert client.post(f"{W}/authentication/options",
                       json={"method": "carrier-pigeon"}).status_code == 422

    # A "phone" assertion from the synced passkey verifies like any other.
    _drop_stepup(client)
    phone_opts = {"publicKey": opts({"method": "phone"})}
    r = client.post(f"{W}/authentication/verify",
                    json={"credential": passkey.assertion(phone_opts)})
    assert r.status_code == 200, r.text


async def test_registration_options_steer_by_method(env):
    client, _, _ = await _owner(env)
    existing = SoftKey()
    assert _register(client, existing).status_code == 201
    expected = {
        "device": ("platform", ["client-device"]),
        "phone": ("cross-platform", ["hybrid"]),
        "security_key": ("cross-platform", ["security-key"]),
    }
    for method, (attachment, hints) in expected.items():
        r = client.post(f"{W}/registration/options", json={"method": method})
        assert r.status_code == 200, r.text
        pk = r.json()["publicKey"]
        sel = pk["authenticatorSelection"]
        assert sel["authenticatorAttachment"] == attachment, method
        assert sel["residentKey"] == "preferred" and sel["userVerification"] == "preferred"
        assert pk["hints"] == hints
        assert [c["id"] for c in pk["excludeCredentials"]] == [b64u(existing.cred_id)]
    pk = client.post(f"{W}/registration/options", json={"method": "any"}).json()["publicKey"]
    assert "authenticatorAttachment" not in pk["authenticatorSelection"] and "hints" not in pk
    # The steered options still register a working key.
    r = client.post(f"{W}/registration/options", json={"method": "security_key"})
    v = client.post(f"{W}/registration/verify",
                    json={"credential": SoftKey(transports=("usb",)).register(r.json()),
                          "nickname": "YubiKey"})
    assert v.status_code == 201, v.text


# ---- devices + per-device trust ---------------------------------------------------------------
SAFARI_MAC = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/18.0 Safari/605.1.15")


def _drop_device(client):
    for c in list(client.cookies.jar):
        if c.name == sk.DEVICE_COOKIE:
            client.cookies.jar.clear(c.domain, c.path, c.name)


def _trust(client, key: SoftKey, **kw):
    opts = client.post(f"{W}/authentication/options", json={"method": "device"})
    assert opts.status_code == 200, opts.text
    return client.post(f"{W}/devices/current/trust",
                       json={"credential": key.assertion(opts.json(), **kw)},
                       headers={"User-Agent": SAFARI_MAC})


async def _audit_actions(sm):
    async with sm() as s:
        return (await s.execute(select(LabAdminAudit.action))).scalars().all()


def test_device_label_from_user_agent():
    assert sk.device_label(SAFARI_MAC) == "Mac · Safari"
    assert sk.device_label("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/130.0 Safari/537.36") == "Mac · Chrome"
    assert sk.device_label("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                           "AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"
                           ) == "iPhone · Safari"
    assert sk.device_label("Mozilla/5.0 (Windows NT 10.0) Chrome/130.0 Safari/537.36 Edg/130.0"
                           ) == "Windows · Edge"
    assert sk.device_label(None) == "Device · Browser"


async def test_device_cookie_is_httponly_and_only_its_hash_is_stored(env):
    client, sm, _ = await _owner(env)
    assert _register(client, SoftKey()).status_code == 201
    async with sm() as s:  # the registering browser was recorded already; start afresh
        await s.execute(delete(AdminTrustedDevice))
        await s.commit()
    _drop_device(client)
    r = client.get(f"{W}/status", headers={"User-Agent": SAFARI_MAC})
    token = client.cookies.get(sk.DEVICE_COOKIE)
    assert token
    st = r.json()
    assert st["device"]["nickname"] == "Mac · Safari"
    assert st["device"]["trusted"] is False and st["device"]["current"] is True
    assert st["trusted_device_days"] == 30
    async with sm() as s:
        rows = (await s.execute(select(AdminTrustedDevice))).scalars().all()
    assert len(rows) == 1 and rows[0].device_sha256 == sk.token_hash(token)
    assert token not in rows[0].device_sha256
    # Seeing the same browser again does not create another row.
    client.get(f"{W}/status")
    devices = client.get(f"{W}/devices").json()["devices"]
    assert len(devices) == 1 and devices[0]["current"] is True


async def test_trusted_device_skips_key_until_expiry(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    r = _trust(client, key)
    assert r.status_code == 200, r.text
    dev = r.json()["device"]
    assert dev["trusted"] is True and dev["current"] is True
    _drop_stepup(client)
    # No step-up cookie, but this device is trusted: everything is open.
    for path in ("/api/lab/dashboard", "/api/users/me", "/api/account/preferences", f"{W}/keys"):
        assert client.get(path).status_code == 200, path
    st = client.get(f"{W}/status").json()
    assert st["unlocked"] is True and st["step_up"]["active"] is False
    assert st["device"]["trusted"] is True
    async with sm() as s:
        row = (await s.execute(select(AdminTrustedDevice))).scalar_one()
        span = row.trusted_until.replace(tzinfo=None) - row.trusted_at.replace(tzinfo=None)
    assert span == timedelta(days=30)
    # Another browser (no device cookie) is still locked.
    saved = client.cookies.get(sk.DEVICE_COOKIE)
    _drop_device(client)
    assert _locked(client.get("/api/lab/dashboard"))
    client.cookies.set(sk.DEVICE_COOKIE, saved, path="/api")
    assert client.get("/api/lab/dashboard").status_code == 200
    # Expiry: after 30 days it asks again.
    async with sm() as s:
        await s.execute(update(AdminTrustedDevice).values(
            trusted_until=utcnow() - timedelta(seconds=1)))
        await s.commit()
    assert _locked(client.get("/api/lab/dashboard"))
    assert _locked(client.get("/api/users/me"))
    assert client.get(f"{W}/status").json()["unlocked"] is False
    assert "device_trusted" in await _audit_actions(sm)


async def test_trust_needs_a_fresh_key_assertion(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    codes = _register(client, key).json()["recovery_codes"]
    _drop_stepup(client)
    # A recovery-code unlock is not a key tap; trust still needs an assertion.
    assert client.post(f"{W}/recovery", json={"code": codes[0]}).status_code == 200
    r = client.post(f"{W}/devices/current/trust", json={"credential": {}})
    assert r.status_code == 400
    # A replayed / foreign assertion is refused.
    opts = client.post(f"{W}/authentication/options").json()
    cred = key.assertion(opts)
    assert client.post(f"{W}/authentication/verify", json={"credential": cred}).status_code == 200
    replay = client.post(f"{W}/devices/current/trust", json={"credential": cred})
    assert replay.status_code == 400 and replay.json()["detail"]["code"] == "challenge_invalid"
    assert _trust(client, SoftKey()).json()["detail"]["code"] == "unknown_key"
    assert _trust(client, key, origin="https://evil.example").status_code == 400
    async with sm() as s:
        assert (await s.execute(select(func.count()).select_from(AdminTrustedDevice).where(
            AdminTrustedDevice.trusted_until.is_not(None)))).scalar_one() == 0
    # A members-only account (no key, not owner) cannot reach it at all.
    await _user(sm, "member@example.com")
    _login(client, "member@example.com")
    assert client.post(f"{W}/devices/current/trust", json={"credential": {}}).status_code == 404


async def test_trust_lifetime_is_capped_and_can_be_disabled(env, monkeypatch):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    monkeypatch.setattr(get_settings(), "lab_trusted_device_days", 365)
    assert _trust(client, key).status_code == 200
    async with sm() as s:
        row = (await s.execute(select(AdminTrustedDevice))).scalar_one()
        span = row.trusted_until.replace(tzinfo=None) - row.trusted_at.replace(tzinfo=None)
    assert span == timedelta(days=30)
    _drop_stepup(client)
    assert client.get("/api/lab/dashboard").status_code == 200
    monkeypatch.setattr(get_settings(), "lab_trusted_device_days", 0)
    # Switching the feature off ends existing trust at once.
    assert _locked(client.get("/api/lab/dashboard"))
    assert _unlock(client, key).status_code == 200
    r = _trust(client, key)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "trust_disabled"
    assert Settings(lab_trusted_device_days=7).trusted_device_days == 7


async def test_revoking_trust_asks_for_the_key_again(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    dev = _trust(client, key).json()["device"]
    devices = client.get(f"{W}/devices").json()["devices"]
    assert devices[0]["trusted"] is True and devices[0]["trusted_until"]
    r = client.delete(f"{W}/devices/{dev['id']}/trust")
    assert r.status_code == 200 and r.json()["device"]["trusted"] is False
    _drop_stepup(client)
    assert _locked(client.get("/api/lab/dashboard"))
    actions = await _audit_actions(sm)
    assert "device_trusted" in actions and "device_trust_revoked" in actions
    async with sm() as s:
        detail = (await s.execute(select(LabAdminAudit.detail).where(
            LabAdminAudit.action == "device_trust_revoked"))).scalar_one()
    assert json.loads(detail)["reason"] == "owner"
    # Trust management needs an unlock, and only touches the owner's own devices.
    assert _locked(client.delete(f"{W}/devices/{dev['id']}/trust"))
    assert _unlock(client, key).status_code == 200
    assert client.delete(f"{W}/devices/999/trust").status_code == 404
    r = client.patch(f"{W}/devices/{dev['id']}", json={"nickname": "Dayyan's MacBook"})
    assert r.status_code == 200 and r.json()["device"]["nickname"] == "Dayyan's MacBook"
    assert client.delete(f"{W}/devices/{dev['id']}").json() == {"deleted": dev["id"]}


async def test_trust_is_bound_to_its_user(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    assert _trust(client, key).status_code == 200
    device_token = client.cookies.get(sk.DEVICE_COOKIE)
    other = await _user(sm, "o2@example.com", superuser=True)
    async with sm() as s:
        s.add(AdminWebAuthnCredential(user_id=other, credential_id="zz", public_key="y",
                                      nickname="theirs"))
        await s.commit()
        o = await s.get(User, other)
        assert await sk.trusted_device(s, o, device_token, utcnow()) is None
        assert await sk.user_locked(s, o, None, utcnow(), device_token=device_token) == 1


async def test_lock_now_ends_trust_on_this_device(env):
    client, sm, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    assert _trust(client, key).status_code == 200
    assert client.post(f"{W}/lock").status_code == 204
    assert _locked(client.get("/api/lab/dashboard"))
    async with sm() as s:
        detail = (await s.execute(select(LabAdminAudit.detail).where(
            LabAdminAudit.action == "device_trust_revoked"))).scalar_one()
    assert json.loads(detail)["reason"] == "lock_now"


async def test_trusted_device_alone_cannot_replace_keys(env):
    client, _, _ = await _owner(env)
    key = SoftKey()
    assert _register(client, key).status_code == 201
    assert _register(client, SoftKey(), "Spare").status_code == 201
    assert _trust(client, key).status_code == 200
    _drop_stepup(client)
    keys = client.get(f"{W}/keys").json()["keys"]  # viewing is fine on a trusted device
    assert _locked(client.delete(f"{W}/keys/{keys[1]['id']}"))
    assert _locked(client.post(f"{W}/recovery-codes"))
    assert _locked(client.post(f"{W}/registration/options"))
    assert _unlock(client, key).status_code == 200
    assert client.delete(f"{W}/keys/{keys[1]['id']}").status_code == 200
