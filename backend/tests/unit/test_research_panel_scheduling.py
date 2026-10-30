"""Deterministic timer/UTC divergence without loosening journal clock validation."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from astrolabe.research_panel import scheduling


@pytest.mark.parametrize('early_ms', [0.8, 1.1, 2.6])
async def test_early_timer_rechecks_actual_boundary(monkeypatch, early_ms):
    boundary = datetime(2026, 9, 27, tzinfo=UTC)
    clocks = iter([boundary - timedelta(seconds=1),
                   boundary - timedelta(milliseconds=early_ms), boundary])
    calls = []
    monkeypatch.setattr(scheduling, '_clock', lambda: {'utc': next(clocks).isoformat()})

    async def early_sleep(delay):
        calls.append(delay)

    monkeypatch.setattr(scheduling.asyncio, 'sleep', early_sleep)
    observed = await scheduling.wait_until(boundary)
    assert observed['utc'] == boundary.isoformat()
    assert calls == [1.0, max(0.001, early_ms / 1000)]


async def test_already_due_returns_actual_late_clock_without_sleep(monkeypatch):
    boundary = datetime(2026, 9, 27, tzinfo=UTC)
    observed = {'utc': (boundary + timedelta(seconds=10)).isoformat()}
    monkeypatch.setattr(scheduling, '_clock', lambda: observed)

    async def forbidden(delay):
        raise AssertionError('already due')

    monkeypatch.setattr(scheduling.asyncio, 'sleep', forbidden)
    assert await scheduling.wait_until(boundary) is observed


async def test_backward_wall_clock_cannot_extend_wait_forever(monkeypatch):
    boundary = datetime(2026, 9, 27, tzinfo=UTC)
    clocks = iter([boundary - timedelta(seconds=1), boundary - timedelta(hours=1)])
    elapsed = iter([0.0, 0.0, 2.1])
    monkeypatch.setattr(scheduling, '_clock', lambda: {'utc': next(clocks).isoformat()})
    monkeypatch.setattr(scheduling, 'time', SimpleNamespace(monotonic=lambda: next(elapsed)))

    async def sleep(delay):
        assert delay == 1

    monkeypatch.setattr(scheduling.asyncio, 'sleep', sleep)
    with pytest.raises(ValueError, match='bounded timer'):
        await scheduling.wait_until(boundary)


async def test_wait_cannot_exceed_declared_one_day_scope(monkeypatch):
    boundary = datetime(2026, 9, 27, tzinfo=UTC)
    monkeypatch.setattr(scheduling, '_clock',
                        lambda: {'utc': (boundary - timedelta(days=2)).isoformat()})
    with pytest.raises(ValueError, match='one-day'):
        await scheduling.wait_until(boundary)
