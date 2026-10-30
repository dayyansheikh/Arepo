"""Lab dashboard backend: Ed25519 request signing, snapshots, command lifecycle, owner auth."""
import base64
import json
import time
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from astrolabe.accounts import db as accounts_db
from astrolabe.accounts import email as account_email
from astrolabe.accounts import ratelimit
from astrolabe.accounts.models import User
from astrolabe.alerts.provider import OutboxProvider
from astrolabe.api.app import create_app
from astrolabe.domain.models import utcnow
from astrolabe.lab import signing
from astrolabe.lab.client_sign import sign
from astrolabe.lab.models import LabCommand
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

PW = "Sufficiently-Long-1"


def _pub_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw).decode()


@pytest.fixture
def keys():
    k = {"host": Ed25519PrivateKey.generate(), "mac": Ed25519PrivateKey.generate()}
    signing.set_public_keys_override({s: _pub_b64(v) for s, v in k.items()})
    yield k
    signing.set_public_keys_override(None)


@pytest.fixture
async def env(keys):
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


def _signed(client, keys, method, path, body=b"", source="host", ts=None, sign_path=None):
    ts = int(time.time()) if ts is None else ts
    headers = sign(keys[source], method, sign_path or path, body, ts, source=source)
    return client.request(method, path, content=body, headers=headers)


def snap(source="host", **extra):
    return json.dumps({"schema": "arepo-lab-v1", "source": source,
                       "generated_at": "2026-10-18T10:00:00Z", **extra}).encode()


def _login(client, box, sm_run, email, superuser):
    client.post("/api/auth/register", json={"first_name": "A", "last_name": "B",
                                            "email": email, "password": PW})
    from urllib.parse import parse_qs, urlparse
    url = box.sent[-1].template_variables["VERIFY_URL"]
    token = parse_qs(urlparse(url).query)["token"][0]
    assert client.post("/api/auth/verify", json={"token": token}).status_code == 200
    return token


async def _make_owner(env, email="o@example.com", superuser=True):
    client, sm, box = env
    _login(client, box, None, email, superuser)
    if superuser:
        async with sm() as s:
            await s.execute(update(User).where(User.email == email).values(is_superuser=True))
            await s.commit()
    r = client.post("/api/auth/login", data={"username": email, "password": PW})
    assert r.status_code in (200, 204)
    return client


# ---- signature ----------------------------------------------------------------------------
async def test_signed_snapshot_accepted(env, keys):
    client, _, _ = env
    assert _signed(client, keys, "POST", "/api/lab/agent/snapshot", snap()).status_code == 204


async def test_bad_signature_wrong_key(env, keys):
    client, _, _ = env
    other = {"host": Ed25519PrivateKey.generate()}
    body = snap()
    h = sign(other["host"], "POST", "/api/lab/agent/snapshot", body, int(time.time()),
             source="host")
    r = client.post("/api/lab/agent/snapshot", content=body, headers=h)
    assert r.status_code == 401


async def test_wrong_source_key(env, keys):
    client, _, _ = env
    body = snap("host")
    h = sign(keys["mac"], "POST", "/api/lab/agent/snapshot", body, int(time.time()),
             source="host")  # mac key, claims host
    assert client.post("/api/lab/agent/snapshot", content=body, headers=h).status_code == 401


async def test_unknown_source_and_missing_headers(env, keys):
    client, _, _ = env
    body = snap()
    h = sign(keys["host"], "POST", "/api/lab/agent/snapshot", body, int(time.time()),
             source="host")
    h["X-Lab-Source"] = "nobody"
    assert client.post("/api/lab/agent/snapshot", content=body, headers=h).status_code == 401
    assert client.post("/api/lab/agent/snapshot", content=body).status_code == 401


async def test_stale_and_future_timestamp(env, keys):
    client, _, _ = env
    for ts in (int(time.time()) - 301, int(time.time()) + 301):
        r = _signed(client, keys, "POST", "/api/lab/agent/snapshot", snap(), ts=ts)
        assert r.status_code == 401


async def test_body_tampering_and_path_mismatch(env, keys):
    client, _, _ = env
    body = snap()
    h = sign(keys["host"], "POST", "/api/lab/agent/snapshot", body, int(time.time()),
             source="host")
    tampered = body.replace(b"2026", b"2027")
    assert client.post("/api/lab/agent/snapshot", content=tampered, headers=h).status_code == 401
    # signature for another path must not work for this one
    r = _signed(client, keys, "GET", "/api/lab/agent/commands",
                sign_path="/api/lab/agent/snapshot")
    assert r.status_code == 401
    # method is part of the signed string
    h = sign(keys["host"], "GET", "/api/lab/agent/snapshot", body, int(time.time()),
             source="host")
    assert client.post("/api/lab/agent/snapshot", content=body, headers=h).status_code == 401


def test_client_sign_round_trip(keys):
    ts = 1_700_000_000
    h = sign(keys["mac"], "POST", "/x", b"hello", ts, source="mac")
    assert signing.verify_signature(
        source=h["X-Lab-Source"], timestamp=h["X-Lab-Timestamp"],
        signature=h["X-Lab-Signature"], method="POST", path="/x", body=b"hello", now=ts + 5
    ) == "mac"
    with pytest.raises(signing.SignatureError):
        signing.verify_signature(
            source="mac", timestamp=h["X-Lab-Timestamp"], signature=h["X-Lab-Signature"],
            method="POST", path="/x", body=b"hellO", now=ts
        )


def test_committed_public_keys_are_valid_ed25519():
    for b64 in signing.PUBLIC_KEYS_B64.values():
        assert len(base64.b64decode(b64)) == 32


# ---- snapshots ----------------------------------------------------------------------------
async def test_snapshot_validation(env, keys):
    client, _, _ = env
    p = "/api/lab/agent/snapshot"
    assert _signed(client, keys, "POST", p, b"not json").status_code == 422
    bad_schema = json.dumps({"schema": "v0", "source": "host", "generated_at": "x"}).encode()
    assert _signed(client, keys, "POST", p, bad_schema).status_code == 422
    assert _signed(client, keys, "POST", p, snap("mac"), source="host").status_code == 422
    no_gen = json.dumps({"schema": "arepo-lab-v1", "source": "host"}).encode()
    assert _signed(client, keys, "POST", p, no_gen).status_code == 422


async def test_snapshot_too_large_413(env, keys):
    client, _, _ = env
    big = snap(pad="x" * (2 * 1024 * 1024 + 10))
    assert _signed(client, keys, "POST", "/api/lab/agent/snapshot", big).status_code == 413


async def test_snapshot_upsert_one_row_per_source(env, keys):
    client, sm, _ = env
    p = "/api/lab/agent/snapshot"
    _signed(client, keys, "POST", p, snap(headline={"tests_run": 1}))
    _signed(client, keys, "POST", p, snap(headline={"tests_run": 2}))
    _signed(client, keys, "POST", p, snap("mac", autopilot={"paused": False}), source="mac")
    from astrolabe.lab.models import LabSnapshot
    async with sm() as s:
        rows = (await s.execute(select(LabSnapshot))).scalars().all()
    assert sorted(r.source for r in rows) == ["host", "mac"]
    host = next(r for r in rows if r.source == "host")
    assert json.loads(host.payload)["headline"]["tests_run"] == 2
    assert host.size_bytes == len(host.payload.encode()) and len(host.payload_sha256) == 64


# ---- owner auth + dashboard ---------------------------------------------------------------
async def test_owner_endpoints_401_unauthenticated(env):
    client, _, _ = env
    assert client.get("/api/lab/dashboard").status_code == 401
    r = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"})
    assert r.status_code == 401


async def test_non_superuser_gets_404(env):
    client = await _make_owner(env, "n@example.com", superuser=False)
    assert client.get("/api/lab/dashboard").status_code == 404
    r = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"})
    assert r.status_code == 404


async def test_superuser_dashboard_shape(env, keys):
    client = await _make_owner(env)
    empty = client.get("/api/lab/dashboard")
    assert empty.status_code == 200
    d = empty.json()
    assert d["host"] is None and d["mac"] is None and d["commands"] == [] and d["server_time"]
    _signed(client, keys, "POST", "/api/lab/agent/snapshot", snap(headline={"tests_run": 5}))
    d = client.get("/api/lab/dashboard").json()
    assert d["host"]["payload"]["headline"]["tests_run"] == 5
    assert d["host"]["received_at"] and d["mac"] is None


async def test_dashboard_passes_signal_engine_block_through(env, keys):
    """The optional `signal_engine` key (schema se-dash-v1) is stored and returned verbatim."""
    client = await _make_owner(env)
    se = {"schema": "se-dash-v1",
          "prospective": {"status": "bootstrapping", "days_scored": 0, "rows": []},
          "models": [{"model_id": "se8", "embargoed_until": "2026-11-01T00:00:00Z"}]}
    r = _signed(client, keys, "POST", "/api/lab/agent/snapshot", snap(signal_engine=se))
    assert r.status_code == 204
    assert client.get("/api/lab/dashboard").json()["host"]["payload"]["signal_engine"] == se


async def test_owner_post_rejects_foreign_origin(env):
    client = await _make_owner(env)
    r = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"},
                    headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    r = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"},
                    headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 201


async def test_command_validation(env):
    client = await _make_owner(env)
    for body in ({"target": "x", "action": "pause"}, {"target": "queue", "action": "kill"}):
        assert client.post("/api/lab/commands", json=body).status_code == 422


# ---- command lifecycle --------------------------------------------------------------------
async def test_command_lifecycle_and_routing(env, keys):
    client = await _make_owner(env)
    c1 = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"}).json()
    c2 = client.post("/api/lab/commands", json={"target": "autopilot", "action": "pause"}).json()
    assert c1["status"] == "pending" and c1["created_at"]
    # host sees only queue, mac only autopilot
    got = _signed(client, keys, "GET", "/api/lab/agent/commands").json()["commands"]
    assert [c["id"] for c in got] == [c1["id"]] and got[0]["action"] == "pause"
    got_mac = _signed(client, keys, "GET", "/api/lab/agent/commands", source="mac").json()
    assert [c["id"] for c in got_mac["commands"]] == [c2["id"]]
    # delivered commands are not re-delivered
    assert _signed(client, keys, "GET", "/api/lab/agent/commands").json()["commands"] == []
    dash = client.get("/api/lab/dashboard").json()["commands"]
    assert {c["id"]: c["status"] for c in dash} == {c1["id"]: "delivered", c2["id"]: "delivered"}
    # results; mac cannot answer host's command
    p = f"/api/lab/agent/commands/{c1['id']}/result"
    assert _signed(client, keys, "POST", p, json.dumps({"ok": True}).encode(),
                   source="mac").status_code == 404
    ok = json.dumps({"ok": True, "message": "paused"}).encode()
    assert _signed(client, keys, "POST", p, ok).status_code == 204
    assert _signed(client, keys, "POST", p, ok).status_code == 409  # already finished
    p2 = f"/api/lab/agent/commands/{c2['id']}/result"
    bad = json.dumps({"ok": False, "message": "boom"}).encode()
    assert _signed(client, keys, "POST", p2, bad, source="mac").status_code == 204
    dash = {c["id"]: c for c in client.get("/api/lab/dashboard").json()["commands"]}
    assert dash[c1["id"]]["status"] == "done" and dash[c1["id"]]["result"] == "paused"
    assert dash[c2["id"]]["status"] == "failed" and dash[c1["id"]]["finished_at"]


async def test_result_message_limit_and_unknown_id(env, keys):
    client, _, _ = env
    long = json.dumps({"ok": True, "message": "x" * 501}).encode()
    assert _signed(client, keys, "POST", "/api/lab/agent/commands/1/result",
                   long).status_code == 422
    ok = json.dumps({"ok": True}).encode()
    assert _signed(client, keys, "POST", "/api/lab/agent/commands/999/result",
                   ok).status_code == 404


async def test_result_requires_delivery(env, keys):
    client = await _make_owner(env)
    c = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"}).json()
    ok = json.dumps({"ok": True}).encode()
    r = _signed(client, keys, "POST", f"/api/lab/agent/commands/{c['id']}/result", ok)
    assert r.status_code == 409


async def test_newer_command_expires_older_pending(env, keys):
    client = await _make_owner(env)
    a = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"}).json()
    b = client.post("/api/lab/commands", json={"target": "queue", "action": "resume"}).json()
    other = client.post("/api/lab/commands", json={"target": "autopilot", "action": "pause"}).json()
    got = _signed(client, keys, "GET", "/api/lab/agent/commands").json()["commands"]
    assert [c["id"] for c in got] == [b["id"]]
    st = {c["id"]: c["status"] for c in client.get("/api/lab/dashboard").json()["commands"]}
    assert st[a["id"]] == "expired" and st[other["id"]] == "pending"


async def test_pending_expires_after_two_hours(env, keys):
    client = await _make_owner(env)
    _, sm, _ = env
    c = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"}).json()
    async with sm() as s:
        await s.execute(update(LabCommand).where(LabCommand.id == c["id"])
                        .values(created_at=utcnow() - timedelta(hours=2, minutes=1)))
        await s.commit()
    assert _signed(client, keys, "GET", "/api/lab/agent/commands").json()["commands"] == []
    cmd = client.get("/api/lab/dashboard").json()["commands"][0]
    assert cmd["status"] == "expired"


async def test_command_rate_limit_429(env):
    client = await _make_owner(env)
    for i in range(30):
        r = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"})
        assert r.status_code == 201, i
    r = client.post("/api/lab/commands", json={"target": "queue", "action": "pause"})
    assert r.status_code == 429


async def test_command_table_pruned_to_500(env):
    client = await _make_owner(env)
    _, sm, _ = env
    from astrolabe.lab import service
    async with sm() as s:
        s.add_all([LabCommand(target="queue", action="pause", status="expired",
                              created_at=utcnow() - timedelta(days=2)) for _ in range(505)])
        await s.commit()
    assert client.post("/api/lab/commands", json={"target": "queue", "action": "pause"}
                       ).status_code == 201
    async with sm() as s:
        n = len((await s.execute(select(LabCommand.id))).scalars().all())
    assert n == service.KEEP_COMMANDS


# ---- migration ----------------------------------------------------------------------------
async def test_migration_creates_lab_tables_and_marks_rls():
    from astrolabe.storage.migrate import (
        _PRIVATE_ACCOUNT_TABLES,
        SCHEMA_VERSION,
        check,
        upgrade,
    )
    assert SCHEMA_VERSION >= 14
    assert {"lab_snapshots", "lab_commands"}.issubset(set(_PRIVATE_ACCOUNT_TABLES))
    eng = make_engine("sqlite+aiosqlite:///:memory:")
    await upgrade(eng)
    status = await check(eng)
    assert status["current"] is True
    from sqlalchemy import inspect
    async with eng.connect() as conn:
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    assert {"lab_snapshots", "lab_commands"} <= tables
    await eng.dispose()
