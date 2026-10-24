"""Actual synthetic origin/target interleaving and immutable dispatch recovery."""

import asyncio
import heapq
from datetime import UTC, datetime

import httpx
import pytest

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.research_panel import runtime
from astrolabe.research_panel.panel_declaration import declare_panel
from astrolabe.research_panel.panel_selection import create_panel_selection
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


async def setup(tmp_path, original_code):
    source = await frame(tmp_path, [market(1)])
    panel = tmp_path / 'fs2_panel_runtime'
    declare_panel(source, implementation_commit=original_code[1], output_root=panel,
        protocol=protocol(cycles=2, target_attempts=1, scheduled_slots=1, triggered_slots=0,
            cadence_seconds=10, max_origin_delay_seconds=5, max_origin_save_seconds=1,
            horizon_seconds=3, tolerance_seconds=2, source_response_bytes=65536,
            source_run_retained_bytes=1048576), storage_profile='compact-v1')
    create_panel_selection(panel, repository=original_code[0])
    return panel


def transport(calls, cancel=False, slow=False):
    async def handler(request):
        calls.append(request.url.path)
        if cancel:
            raise asyncio.CancelledError()
        if request.url.path == '/markets/1':
            if slow:
                await asyncio.sleep(4.1)
            body = market(1, active=True, closed=False, archived=False, acceptingOrders=True)
        elif request.url.path == '/book':
            body = {'asset_id': '2', 'market': '0x' + f'{1:064x}',
                    'bids': [{'price': '0.4', 'size': '1'}],
                    'asks': [{'price': '0.6', 'size': '1'}]}
        else:
            body = {'data': [], 'pagination': {'has_more': False, 'next_cursor': None}}
        return httpx.Response(200, stream=Stream([_json_bytes(body)]))
    return httpx.MockTransport(handler)


async def test_two_cycles_interleave_targets_and_replay_rejects_reordered_events(
        tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    calls = []
    result = await runtime.exercise_panel(panel, transport=transport(calls))
    assert [e['kind'] for e in result['events']] == ['origin', 'target', 'origin', 'target']
    assert calls == ['/markets/1', '/book', '/v2/trades', '/markets/1', '/book'] * 2
    assert len(result['origins']) == len(result['outcomes']) == 2
    assert {o['state'] for o in result['outcomes']} == {'observed'}
    assert {o['midpoint_change'] for o in result['outcomes']} == {'0.0'}
    root = runtime.run_root(panel)
    before = snapshot(root)
    assert runtime.read_runtime(panel) == result and snapshot(root) == before
    amend(root, 'runtime_report', lambda p: p['events'].reverse())
    with pytest.raises(ValueError, match='dispatch'):
        runtime.read_runtime(panel)


def test_queue_ties_and_ineligible_targets_use_actual_plan_availability():
    at = datetime(2026, 9, 23, tzinfo=UTC)
    origin = (at, 1, 'z', 'origin', {})
    job = {'attempt_id': 'a', 'scheduled_at': at.isoformat()}
    queue = [origin]
    runtime._enqueue(queue, [job], {'durable_ack': {'utc': at.isoformat()}}, True)
    assert heapq.heappop(queue)[3] == 'target'
    future = datetime(2026, 9, 24, tzinfo=UTC)
    runtime._enqueue(queue, [{**job, 'scheduled_at': future.isoformat()}],
                     {'durable_ack': {'utc': at.isoformat()}}, False)
    assert heapq.heappop(queue)[0] == at


async def test_slow_origin_retains_expiration_and_no_target_requests(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    calls = []
    result = await runtime.exercise_panel(panel, transport=transport(calls, slow=True))
    assert calls == ['/markets/1'] * 2
    assert {r['state'] for r in result['origins']} == {'expired_during_requests'}
    assert {a['state'] for a in result['attempts']} == {'origin_ineligible'}
    assert runtime.read_runtime(panel) == result


async def test_cancel_and_duplicate_ownership_are_terminal(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    calls = []
    result = await asyncio.gather(
        runtime.exercise_panel(panel, transport=transport(calls, cancel=True)),
        runtime.exercise_panel(panel, transport=transport(calls)), return_exceptions=True)
    assert any(isinstance(r, asyncio.CancelledError) for r in result)
    assert any(isinstance(r, FileExistsError) for r in result)
    root = runtime.run_root(panel)
    assert (root / 'runtime_failure_ack.json').exists()
    assert not (root / 'runtime_report.json').exists()
    with pytest.raises(FileExistsError):
        await runtime.exercise_panel(panel, transport=transport(calls))
    assert len(calls) == 1


async def test_no_live_or_clock_override_and_no_capacity_side_effect(
        tmp_path, original_code, monkeypatch):
    import shutil
    panel = await setup(tmp_path, original_code)
    with pytest.raises(ValueError, match='synthetic'):
        await runtime.exercise_panel(panel, transport=None)
    with pytest.raises(TypeError):
        await runtime.exercise_panel(panel, transport=transport([]), clock=None)
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(1, 1, 0))
    with pytest.raises(ValueError, match='reservation'):
        await runtime.exercise_panel(panel, transport=transport([]))
    assert not runtime.run_root(panel).exists()
