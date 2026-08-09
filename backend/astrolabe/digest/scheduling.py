"""Pure deterministic digest due-window calculations (all boundaries are UTC)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

FREQUENCIES = ("off", "every_6h", "daily", "twice_daily", "weekly")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def window_start(frequency: str, now: datetime) -> datetime | None:
    """Most recent fixed UTC boundary for a frequency; ``None`` means delivery is off."""
    now = _utc(now).astimezone(UTC)
    if frequency == "off":
        return None
    if frequency == "every_6h":
        return now.replace(hour=(now.hour // 6) * 6, minute=0, second=0, microsecond=0)
    if frequency == "twice_daily":
        return now.replace(hour=(now.hour // 12) * 12, minute=0, second=0, microsecond=0)
    if frequency == "daily":
        boundary = now.replace(hour=6, minute=0, second=0, microsecond=0)
        return boundary if now >= boundary else boundary - timedelta(days=1)
    if frequency == "weekly":
        boundary = (now - timedelta(days=now.weekday())).replace(
            hour=6, minute=0, second=0, microsecond=0
        )
        return boundary if now >= boundary else boundary - timedelta(days=7)
    raise ValueError(f"unsupported digest frequency: {frequency}")


def due_window_key(frequency: str, now: datetime) -> str | None:
    start = window_start(frequency, now)
    # Deliberately frequency-independent: switching preferences inside an already-consumed boundary
    # cannot cause a second send for that same window.
    return start.strftime("%Y-%m-%dT%H:%M:%SZ") if start is not None else None


def evaluation_horizon(frequency: str) -> str:
    return {
        "every_6h": "6h",
        "twice_daily": "6h",
        "daily": "24h",
        "weekly": "7d",
    }.get(frequency, "24h")


def horizon_due_at(captured_at: datetime, horizon: str) -> datetime:
    hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 24 * 7}.get(horizon, 24)
    return _utc(captured_at) + timedelta(hours=hours)
