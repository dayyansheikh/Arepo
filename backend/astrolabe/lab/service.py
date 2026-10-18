"""Lab dashboard persistence logic (snapshots + command lifecycle)."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import LabCommand, LabSnapshot

SNAPSHOT_SCHEMA = "arepo-lab-v1"
SOURCE_TARGETS = {"host": "queue", "mac": "autopilot"}
COMMAND_TTL = timedelta(hours=2)
MAX_COMMANDS_PER_HOUR = 30
KEEP_COMMANDS = 500


class SnapshotInvalid(ValueError):
    pass


class RateLimited(Exception):
    pass


class CommandNotFound(Exception):
    pass


class CommandConflict(Exception):
    pass


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
    target = SOURCE_TARGETS[source]
    rows = (await session.execute(
        select(LabCommand)
        .where(LabCommand.target == target, LabCommand.status == "pending")
        .order_by(LabCommand.id)
    )).scalars().all()
    out = []
    for r in rows:
        r.status, r.delivered_at = "delivered", now
        out.append({"id": r.id, "target": r.target, "action": r.action,
                    "created_at": _iso(r.created_at)})
    await session.commit()
    return out


async def record_result(
    session: AsyncSession, source: str, command_id: int, ok: bool, message: str, now: datetime
) -> None:
    row = await session.get(LabCommand, command_id)
    if row is None or row.target != SOURCE_TARGETS[source]:
        raise CommandNotFound
    if row.status != "delivered":
        raise CommandConflict(f"command is {row.status}")
    row.status = "done" if ok else "failed"
    row.finished_at, row.result = now, message
    await session.commit()


async def create_command(
    session: AsyncSession, target: str, action: str, user_id: str, now: datetime
) -> dict:
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
    out["server_time"] = now.isoformat()
    return out
