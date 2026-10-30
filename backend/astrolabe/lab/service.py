"""Lab dashboard persistence logic (snapshots, command lifecycle, owner -> Claude messages)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import LabAdminAudit, LabCommand, LabMessage, LabSnapshot

SNAPSHOT_SCHEMA = "arepo-lab-v1"
# Command targets: the research queue (host) and each Claude autopilot instance on the Mac, named
# by its home directory (`autopilot` = ~/.arepo/autopilot, the experiments instance;
# `autopilot-signal` = ~/.arepo/autopilot-signal, ...).
AUTOPILOT_TARGET_RE = re.compile(r"^autopilot(?:-[a-z0-9]{1,24})?$")
TARGET_ACTIONS = {"queue": ("pause", "resume"), "autopilot": ("pause", "resume", "start")}
COMMAND_TTL = timedelta(hours=2)
MAX_COMMANDS_PER_HOUR = 30
KEEP_COMMANDS = 500
MESSAGE_MAX_CHARS = 4000
MAX_MESSAGES_PER_DAY = 20
KEEP_MESSAGES = 500
MESSAGE_REFETCH_AFTER = timedelta(minutes=30)
AWAIT_READ_WINDOW = timedelta(days=30)
DASHBOARD_MESSAGES = 30
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class SnapshotInvalid(ValueError):
    pass


class RateLimited(Exception):
    pass


class CommandNotFound(Exception):
    pass


class CommandConflict(Exception):
    pass


class CommandInvalid(ValueError):
    pass


def target_source(target: str | None) -> str | None:
    """Which machine executes a target: host (queue), mac (autopilot instances) or None."""
    if target == "queue":
        return "host"
    if isinstance(target, str) and AUTOPILOT_TARGET_RE.match(target):
        return "mac"
    return None


def validate_command(target: str, action: str) -> None:
    src = target_source(target)
    if src is None:
        raise CommandInvalid("unknown target")
    allowed = TARGET_ACTIONS["queue" if src == "host" else "autopilot"]
    if action not in allowed:
        raise CommandInvalid(f"{action!r} is not available for {target}")


def _audit(session: AsyncSession, user_id: str, email: str | None, action: str, now: datetime,
           detail: dict) -> None:
    session.add(LabAdminAudit(at=now, actor_user_id=user_id, actor_email=email or "",
                              action=action, detail=json.dumps(detail, sort_keys=True)))


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _iso(dt: datetime | None) -> str | None:
    dt = _aware(dt)
    return dt.isoformat() if dt else None


def validate_snapshot(body: bytes, source: str) -> dict:
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SnapshotInvalid("body is not valid JSON") from exc
    if not isinstance(data, dict):
        raise SnapshotInvalid("snapshot must be a JSON object")
    if data.get("schema") != SNAPSHOT_SCHEMA:
        raise SnapshotInvalid(f"schema must be {SNAPSHOT_SCHEMA}")
    if data.get("source") != source:
        raise SnapshotInvalid("snapshot source does not match signing source")
    if not isinstance(data.get("generated_at"), str) or not data["generated_at"]:
        raise SnapshotInvalid("generated_at is required")
    return data


async def upsert_snapshot(
    session: AsyncSession, source: str, body: bytes, now: datetime
) -> None:
    validate_snapshot(body, source)
    row = await session.get(LabSnapshot, source)
    text = body.decode("utf-8")
    sha = hashlib.sha256(body).hexdigest()
    if row is None:
        session.add(LabSnapshot(source=source, received_at=now, payload=text,
                                payload_sha256=sha, size_bytes=len(body)))
    else:
        row.received_at, row.payload = now, text
        row.payload_sha256, row.size_bytes = sha, len(body)
    await session.commit()


async def expire_stale(session: AsyncSession, now: datetime) -> None:
    await session.execute(
        update(LabCommand)
        .where(LabCommand.status == "pending", LabCommand.created_at < now - COMMAND_TTL)
        .values(status="expired", finished_at=now)
    )


async def fetch_commands(session: AsyncSession, source: str, now: datetime) -> list[dict]:
    await expire_stale(session, now)
    rows = (await session.execute(
        select(LabCommand).where(LabCommand.status == "pending").order_by(LabCommand.id)
    )).scalars().all()
    out = []
    for r in rows:
        if target_source(r.target) != source:
            continue
        r.status, r.delivered_at = "delivered", now
        out.append({"id": r.id, "target": r.target, "action": r.action,
                    "created_at": _iso(r.created_at)})
    await session.commit()
    return out


async def record_result(
    session: AsyncSession, source: str, command_id: int, ok: bool, message: str, now: datetime
) -> None:
    row = await session.get(LabCommand, command_id)
    if row is None or target_source(row.target) != source:
        raise CommandNotFound
    if row.status != "delivered":
        raise CommandConflict(f"command is {row.status}")
    row.status = "done" if ok else "failed"
    row.finished_at, row.result = now, message
    await session.commit()


async def create_command(
    session: AsyncSession, target: str, action: str, user_id: str, now: datetime,
    actor_email: str | None = None,
) -> dict:
    validate_command(target, action)
    recent = (await session.execute(
        select(func.count()).select_from(LabCommand)
        .where(LabCommand.created_at >= now - timedelta(hours=1))
    )).scalar_one()
    if recent >= MAX_COMMANDS_PER_HOUR:
        raise RateLimited
    await expire_stale(session, now)
    await session.execute(
        update(LabCommand)
        .where(LabCommand.target == target, LabCommand.status == "pending")
        .values(status="expired", finished_at=now)
    )
    row = LabCommand(target=target, action=action, status="pending", created_at=now,
                     created_by=user_id)
    session.add(row)
    await session.flush()
    await session.execute(delete(LabCommand).where(LabCommand.id <= row.id - KEEP_COMMANDS))
    if actor_email is not None:
        _audit(session, user_id, actor_email, "claude_command", now,
               {"id": row.id, "target": target, "action": action})
    await session.commit()
    return command_dict(row)


def command_dict(r: LabCommand) -> dict:
    return {
        "id": r.id, "target": r.target, "action": r.action, "status": r.status,
        "created_at": _iso(r.created_at), "delivered_at": _iso(r.delivered_at),
        "finished_at": _iso(r.finished_at), "result": r.result,
    }


async def dashboard(session: AsyncSession, now: datetime) -> dict:
    await expire_stale(session, now)
    await session.commit()
    out: dict = {"host": None, "mac": None}
    for snap in (await session.execute(select(LabSnapshot))).scalars():
        try:
            payload = json.loads(snap.payload)
        except ValueError:
            continue
        out[snap.source] = {"received_at": _iso(snap.received_at), "payload": payload}
    cmds = (await session.execute(
        select(LabCommand).order_by(LabCommand.id.desc()).limit(20)
    )).scalars().all()
    out["commands"] = [command_dict(c) for c in cmds]
    msgs = (await session.execute(
        select(LabMessage).order_by(LabMessage.id.desc()).limit(DASHBOARD_MESSAGES)
    )).scalars().all()
    out["messages"] = [message_dict(m) for m in msgs]
    out["limits"] = {"message_max_chars": MESSAGE_MAX_CHARS,
                     "messages_per_day": MAX_MESSAGES_PER_DAY,
                     "messages_last_24h": await _messages_last_day(session, now)}
    out["server_time"] = now.isoformat()
    return out


# ---- owner -> Claude messages -------------------------------------------------------------
class MessageInvalid(ValueError):
    pass


class MessageNotFound(Exception):
    pass


class MessageConflict(Exception):
    pass


def clean_message(body: str) -> str:
    text = _CTRL.sub("", body or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise MessageInvalid("message is empty")
    if len(text) > MESSAGE_MAX_CHARS:
        raise MessageInvalid(f"message is longer than {MESSAGE_MAX_CHARS} characters")
    return text


def message_dict(r: LabMessage) -> dict:
    return {
        "id": r.id, "target": r.target, "body": r.body, "status": r.status,
        "created_at": _iso(r.created_at), "fetched_at": _iso(r.fetched_at),
        "delivered_at": _iso(r.delivered_at), "read_at": _iso(r.read_at),
        "finished_at": _iso(r.finished_at), "result": r.result,
    }


async def _messages_last_day(session: AsyncSession, now: datetime) -> int:
    return int((await session.execute(
        select(func.count()).select_from(LabMessage)
        .where(LabMessage.created_at >= now - timedelta(days=1))
    )).scalar_one())


async def create_message(
    session: AsyncSession, target: str, body: str, user_id: str, actor_email: str | None,
    now: datetime,
) -> dict:
    if target_source(target) != "mac":
        raise MessageInvalid("messages go to an autopilot instance")
    text = clean_message(body)
    if await _messages_last_day(session, now) >= MAX_MESSAGES_PER_DAY:
        raise RateLimited
    row = LabMessage(target=target, body=text, status="pending", created_at=now,
                     created_by=user_id)
    session.add(row)
    await session.flush()
    await session.execute(delete(LabMessage).where(LabMessage.id <= row.id - KEEP_MESSAGES))
    _audit(session, user_id, actor_email, "claude_message_sent", now,
           {"id": row.id, "target": target, "chars": len(text)})
    await session.commit()
    return message_dict(row)


async def cancel_message(
    session: AsyncSession, message_id: int, user_id: str, actor_email: str | None, now: datetime
) -> dict:
    row = await session.get(LabMessage, message_id)
    if row is None:
        raise MessageNotFound
    if row.status != "pending":
        raise MessageConflict(f"message is {row.status}")
    row.status, row.finished_at = "cancelled", now
    _audit(session, user_id, actor_email, "claude_message_cancelled", now,
           {"id": row.id, "target": row.target})
    await session.commit()
    return message_dict(row)


async def fetch_messages(session: AsyncSession, source: str, now: datetime) -> dict:
    """New messages for the Mac (pending, or fetched > 30 min ago without a report: the Mac writes
    idempotently) plus delivered ones it should check for `read`."""
    if source != "mac":
        return {"messages": [], "awaiting_read": []}
    rows = (await session.execute(
        select(LabMessage)
        .where(LabMessage.status.in_(("pending", "fetched")))
        .order_by(LabMessage.id)
    )).scalars().all()
    out = []
    for r in rows:
        fetched = _aware(r.fetched_at)
        if r.status == "fetched" and fetched and fetched > now - MESSAGE_REFETCH_AFTER:
            continue
        r.status, r.fetched_at = "fetched", now
        out.append({"id": r.id, "target": r.target, "body": r.body,
                    "created_at": _iso(r.created_at)})
    waiting = (await session.execute(
        select(LabMessage.id, LabMessage.target)
        .where(LabMessage.status == "delivered",
               LabMessage.created_at >= now - AWAIT_READ_WINDOW)
        .order_by(LabMessage.id).limit(50)
    )).all()
    await session.commit()
    return {"messages": out, "awaiting_read": [{"id": i, "target": t} for i, t in waiting]}


# state -> (statuses it may move from, statuses where the report is a harmless repeat)
_MESSAGE_MOVES = {
    "delivered": ({"pending", "fetched"}, {"delivered", "read"}),
    "read": ({"pending", "fetched", "delivered"}, {"read"}),
    "failed": ({"pending", "fetched"}, {"failed"}),
}


async def record_message_state(
    session: AsyncSession, source: str, message_id: int, state: str, message: str, now: datetime
) -> None:
    row = await session.get(LabMessage, message_id)
    if row is None or source != "mac":
        raise MessageNotFound
    allowed, repeat = _MESSAGE_MOVES[state]
    if row.status in repeat:
        return
    if row.status not in allowed:
        raise MessageConflict(f"message is {row.status}")
    row.status = state
    if state in ("delivered", "read") and row.delivered_at is None:
        row.delivered_at = now
    if state == "read":
        row.read_at = row.finished_at = now
    if state == "failed":
        row.finished_at = now
    if message:
        row.result = message
    await session.commit()
