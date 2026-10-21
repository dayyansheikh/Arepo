"""Lab > Claude board v2: per-instance commands (pause/resume/start), owner -> Claude messages
(sent -> fetched -> delivered -> read, cancel, failed), rate limits, audit rows, migration v17."""

import json
from datetime import timedelta

from sqlalchemy import select, update

from astrolabe.domain.models import utcnow
from astrolabe.lab import service
from astrolabe.lab.models import LabAdminAudit, LabMessage

from .test_lab import _make_owner, _signed, env, keys  # noqa: F401  (pytest fixtures)

M = "/api/lab/messages"


def _send(client, target="autopilot-signal", body="Please look at CB18 first."):
    return client.post(M, json={"target": target, "body": body})


# ---- per-instance commands --------------------------------------------------------------------
async def test_commands_per_instance_and_start_validation(env, keys):  # noqa: F811
    client = await _make_owner(env)
    ok = [
        ("autopilot", "pause"),
        ("autopilot-signal", "resume"),
        ("autopilot-signal", "start"),
        ("queue", "pause"),
    ]
    ids = {}
    for target, action in ok:
        r = client.post("/api/lab/commands", json={"target": target, "action": action})
        assert r.status_code == 201, (target, action, r.text)
        ids[(target, action)] = r.json()["id"]
    for body in (
        {"target": "queue", "action": "start"},
        {"target": "autopilot-", "action": "pause"},
        {"target": "autopilot-UPPER", "action": "pause"},
        {"target": "autopilot", "action": "stop"},
        {"target": "autopilot-signal/../x", "action": "pause"},
    ):
        assert client.post("/api/lab/commands", json=body).status_code == 422, body
    # the newer signal command expired the older pending one for the same target
    mac = _signed(client, keys, "GET", "/api/lab/agent/commands", source="mac").json()["commands"]
    assert [(c["target"], c["action"]) for c in mac] == [
        ("autopilot", "pause"),
        ("autopilot-signal", "start"),
    ]
    host = _signed(client, keys, "GET", "/api/lab/agent/commands").json()["commands"]
    assert [c["target"] for c in host] == ["queue"]
    # the host cannot answer a mac command, the mac can
    p = f"/api/lab/agent/commands/{ids[('autopilot-signal', 'start')]}/result"
    body = json.dumps({"ok": False, "message": "refused: this instance is paused"}).encode()
    assert _signed(client, keys, "POST", p, body).status_code == 404
    assert _signed(client, keys, "POST", p, body, source="mac").status_code == 204
    _, sm, _ = env
    async with sm() as s:
        audit = (await s.execute(select(LabAdminAudit.action, LabAdminAudit.detail))).all()
    assert sum(1 for a, _ in audit if a == "claude_command") == 4


# ---- messages ---------------------------------------------------------------------------------
async def test_message_lifecycle_sent_delivered_read(env, keys):  # noqa: F811
    client = await _make_owner(env)
    r = _send(client, body="  Look at CB18 first.\x07\r\nThen LT3.  ")
    assert r.status_code == 201
    m = r.json()
    assert m["status"] == "pending" and m["body"] == "Look at CB18 first.\nThen LT3."
    # the host never receives messages
    assert _signed(client, keys, "GET", "/api/lab/agent/messages").json() == {
        "messages": [],
        "awaiting_read": [],
    }
    got = _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac").json()
    assert [x["id"] for x in got["messages"]] == [m["id"]] and got["messages"][0][
        "body"
    ].startswith("Look")
    assert got["messages"][0]["target"] == "autopilot-signal" and got["awaiting_read"] == []
    # fetched: not handed out again straight away
    again = _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac").json()
    assert again["messages"] == []
    st = f"/api/lab/agent/messages/{m['id']}/status"
    delivered = json.dumps(
        {"state": "delivered", "message": "in autopilot-signal/INBOX.md"}
    ).encode()
    assert _signed(client, keys, "POST", st, delivered).status_code == 404  # host cannot report
    assert _signed(client, keys, "POST", st, delivered, source="mac").status_code == 204
    assert _signed(client, keys, "POST", st, delivered, source="mac").status_code == 204  # repeat
    dash = client.get("/api/lab/dashboard").json()
    assert dash["messages"][0]["status"] == "delivered" and dash["messages"][0]["delivered_at"]
    assert dash["limits"] == {
        "message_max_chars": 4000,
        "messages_per_day": 20,
        "messages_last_24h": 1,
    }
    waiting = _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac").json()
    assert waiting["awaiting_read"] == [{"id": m["id"], "target": "autopilot-signal"}]
    read = json.dumps({"state": "read", "message": "moved out of INBOX.md"}).encode()
    assert _signed(client, keys, "POST", st, read, source="mac").status_code == 204
    msg = client.get("/api/lab/dashboard").json()["messages"][0]
    assert msg["status"] == "read" and msg["read_at"] and msg["result"] == "moved out of INBOX.md"
    # read is final
    failed = json.dumps({"state": "failed"}).encode()
    assert _signed(client, keys, "POST", st, failed, source="mac").status_code == 409
    assert _signed(client, keys, "POST", st, delivered, source="mac").status_code == 204  # late
    assert client.get("/api/lab/dashboard").json()["messages"][0]["status"] == "read"
    bad = json.dumps({"state": "eaten"}).encode()
    assert _signed(client, keys, "POST", st, bad, source="mac").status_code == 422
    assert (
        _signed(
            client, keys, "POST", "/api/lab/agent/messages/999/status", read, source="mac"
        ).status_code
        == 404
    )


async def test_stale_fetch_is_redelivered_and_failed_is_final(env, keys):  # noqa: F811
    client = await _make_owner(env)
    _, sm, _ = env
    m = _send(client).json()
    assert (
        len(
            _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac").json()["messages"]
        )
        == 1
    )
    async with sm() as s:
        await s.execute(
            update(LabMessage)
            .where(LabMessage.id == m["id"])
            .values(fetched_at=utcnow() - timedelta(minutes=31))
        )
        await s.commit()
    assert [
        x["id"]
        for x in _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac").json()[
            "messages"
        ]
    ] == [m["id"]]
    st = f"/api/lab/agent/messages/{m['id']}/status"
    fail = json.dumps({"state": "failed", "message": "no instance"}).encode()
    assert _signed(client, keys, "POST", st, fail, source="mac").status_code == 204
    msg = client.get("/api/lab/dashboard").json()["messages"][0]
    assert msg["status"] == "failed" and msg["result"] == "no instance" and msg["finished_at"]
    assert client.post(f"{M}/{m['id']}/cancel").status_code == 409


async def test_cancel_only_while_pending(env, keys):  # noqa: F811
    client = await _make_owner(env)
    a = _send(client, body="first").json()
    r = client.post(f"{M}/{a['id']}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert (
        _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac").json()["messages"]
        == []
    )
    b = _send(client, body="second").json()
    _signed(client, keys, "GET", "/api/lab/agent/messages", source="mac")
    assert client.post(f"{M}/{b['id']}/cancel").status_code == 409  # already on its way
    assert client.post(f"{M}/9999/cancel").status_code == 404
    _, sm, _ = env
    async with sm() as s:
        acts = (await s.execute(select(LabAdminAudit.action))).scalars().all()
    assert acts.count("claude_message_sent") == 2 and acts.count("claude_message_cancelled") == 1


async def test_message_validation(env):  # noqa: F811
    client = await _make_owner(env)
    for body in (
        {"target": "queue", "body": "x"},
        {"target": "autopilot-signal", "body": ""},
        {"target": "autopilot-signal", "body": "   \n "},
        {"target": "autopilot-signal", "body": "x" * 4001},
        {"target": "nope", "body": "x"},
    ):
        assert client.post(M, json=body).status_code == 422, body
    assert _send(client, body="x" * 4000).status_code == 201
    assert _send(client, target="autopilot", body="experiments").status_code == 201


async def test_message_rate_limit_20_per_day(env):  # noqa: F811
    client = await _make_owner(env)
    _, sm, _ = env
    for i in range(service.MAX_MESSAGES_PER_DAY):
        assert _send(client, body=f"m{i}").status_code == 201, i
    assert _send(client, body="one too many").status_code == 429
    async with sm() as s:  # a day later the window has moved on
        await s.execute(update(LabMessage).values(created_at=utcnow() - timedelta(hours=25)))
        await s.commit()
    assert _send(client, body="tomorrow").status_code == 201


async def test_claude_audit_rows_do_not_use_member_action_budget(env):  # noqa: F811
    from types import SimpleNamespace

    import pytest

    from astrolabe.lab import admin

    _, sm, _ = env
    actor = SimpleNamespace(id="x")
    async with sm() as s:
        s.add_all(
            [
                LabAdminAudit(
                    at=utcnow(),
                    actor_user_id="x",
                    actor_email="o@example.com",
                    action="claude_message_sent",
                )
                for _ in range(admin.MAX_ACTIONS_PER_HOUR)
            ]
        )
        await s.commit()
        await admin._check_rate(s, actor, utcnow(), email=False)  # not counted
        s.add_all(
            [
                LabAdminAudit(
                    at=utcnow(), actor_user_id="x", actor_email="o@example.com", action="verify"
                )
                for _ in range(admin.MAX_ACTIONS_PER_HOUR)
            ]
        )
        await s.commit()
        with pytest.raises(admin.AdminError):
            await admin._check_rate(s, actor, utcnow(), email=False)


async def test_message_endpoints_owner_only(env):  # noqa: F811
    client, _, _ = env
    assert client.post(M, json={"target": "autopilot", "body": "x"}).status_code == 401
    assert client.post(f"{M}/1/cancel").status_code == 401
    other = await _make_owner(env, email="m@example.com", superuser=False)
    assert other.post(M, json={"target": "autopilot", "body": "x"}).status_code == 404
    assert other.post(f"{M}/1/cancel").status_code == 404


async def test_agent_message_endpoints_require_signature(env, keys):  # noqa: F811
    client, _, _ = env
    assert client.get("/api/lab/agent/messages").status_code == 401
    assert (
        client.post("/api/lab/agent/messages/1/status", content=b'{"state":"read"}').status_code
        == 401
    )


async def test_migration_v17_creates_lab_messages():
    from sqlalchemy import inspect

    from astrolabe.storage.db import make_engine
    from astrolabe.storage.migrate import _PRIVATE_ACCOUNT_TABLES, SCHEMA_VERSION, check, upgrade

    assert SCHEMA_VERSION >= 17 and "lab_messages" in _PRIVATE_ACCOUNT_TABLES
    eng = make_engine("sqlite+aiosqlite:///:memory:")
    await upgrade(eng)
    assert (await check(eng))["current"] is True
    async with eng.connect() as conn:
        cols = await conn.run_sync(
            lambda c: {x["name"] for x in inspect(c).get_columns("lab_messages")}
        )
    assert {
        "id",
        "target",
        "body",
        "status",
        "created_at",
        "fetched_at",
        "delivered_at",
        "read_at",
        "finished_at",
        "result",
        "created_by",
    } <= cols
    await eng.dispose()
