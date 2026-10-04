"""Owned pre-t0 subscriptions, real loopback clocks, missing members and original recovery."""

import asyncio
import json
from dataclasses import asdict

import httpx
import pytest
from websockets.asyncio.server import serve

from astrolabe.feature_store.source_run import _pair, _time
from astrolabe.research_panel import concurrent_runtime, origin_worker, screening_worker
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.owned_windows import OwnedWindowPolicy, reservation
from astrolabe.research_panel.panel_declaration import read_panel_declaration
from astrolabe.research_panel.runtime import run_root
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_owned_pilot import transport
from tests.unit.test_research_panel_screening_worker import prepared

original_code = _original_code


def config():
    return OwnedWindowPolicy(1000, WindowBindingPolicy(120000, 120000),
        WindowReconciliationPolicy(120000, 120000, 100), OriginWindowPolicy(120000, 60000))


async def setup(tmp_path, code):
    return await prepared(tmp_path, code, event_ids=True, max_origin_delay_seconds=45,
        horizon_seconds=8, tolerance_seconds=5, max_origin_save_seconds=2,
        max_quote_age_seconds=120)


async def execute(panel, code, source, port):
    return await screening_worker.run_synthetic_window_pilot(panel,
        implementation_commit=code[1], repository=code[0], transport=source, port=port,
        rule=SnapshotTriggerPolicy(1, 3, 120000), freshness=ScreeningPolicy(120, 120),
        window_policy=config(), concurrency=2, runtime_concurrency=3)


async def test_owned_window_runtime_original_recovery_and_dependency_tamper(
    tmp_path, original_code
):
    _, panel, rows = await setup(tmp_path, original_code)
    source, calls = transport(rows)
    by_token = {json.loads(r['clobTokenIds'])[0]: r for r in rows}
    active = set()
    peak = 0

    async def handle(socket):
        nonlocal peak
        token = json.loads(await socket.recv())['assets_ids'][0]
        active.add(token)
        peak = max(peak, len(active))
        await socket.send(json.dumps({'event_type': 'book', 'asset_id': token,
            'market': by_token[token]['conditionId'], 'bids': [{'price': '0.4', 'size': '2'}],
            'asks': [{'price': '0.6', 'size': '1'}]}))
        await socket.wait_closed()
        active.remove(token)

    async with serve(handle, '127.0.0.1', 0) as server:
        result = await execute(panel, original_code, source, server.sockets[0].getsockname()[1])
    assert peak == 2 and not active
    assert len(calls) == 14
    assert len(result['recovery']) == 1
    assert result['runtime']['schema_version'] == concurrent_runtime.WINDOW_VERSION
    assert {o['state'] for o in result['runtime']['origins']} == {'observed'}
    assert {o['state'] for o in result['runtime']['outcomes']} == {'observed'}
    worker, runtime = screening_worker.worker_root(panel), run_root(panel)
    wp, _ = _pair(worker, 'worker_policy')
    old = screening_worker.allocation(read_panel_declaration(panel))
    assert wp['reservation']['window_bytes'] == reservation(old['screen_slots'])
    assert wp['reservation']['required_free_bytes'] == old['required_free_bytes'] + reservation(2)
    assert not wp['reservation']['overlap_discount_applied']
    rp, _ = _pair(runtime, 'runtime_policy')
    assert rp['window_inputs']['policy'] == asdict(config())
    for child in (runtime / 'origins').iterdir():
        intent, _ = _pair(child, 'origin_intent')
        facts, _ = _pair(child, 'origin_facts')
        assert intent['schema_version'] == origin_worker.WINDOW_VERSION
        window = facts['projection']['pre_origin_window']
        assert window['eligible_at_freeze']
        assert _time(window['window_ended_at']) < _time(facts['read_started_at'])
        assert int(window['coverage']['uncovered_duration_ns']) > 0
        assert not window['continuous_window_eligible']
    before = snapshot(runtime), snapshot(worker)
    assert concurrent_runtime.read_runtime(panel) == result['runtime']
    assert before == (snapshot(runtime), snapshot(worker))
    rewrite(worker, 'window_000', lambda p: p.update(missing_reason='invented'))
    with pytest.raises(ValueError, match='replay'):
        concurrent_runtime.read_runtime(panel)


async def test_unavailable_pre_book_keeps_sample_and_snapshot_origin(tmp_path, original_code):
    _, panel, rows = await setup(tmp_path, original_code)
    source, _ = transport(rows)
    first = True
    missing_token = None

    async def handle_http(request):
        nonlocal first, missing_token
        if request.url.path == '/book' and first:
            first = False
            missing_token = request.url.params['token_id']
            return httpx.Response(404, stream=Stream([b'{"error":"no book"}']))
        return await source.handle_async_request(request)

    async def handle(socket):
        await socket.recv()
        await socket.close()

    async with serve(handle, '127.0.0.1', 0) as server:
        result = await execute(panel, original_code, httpx.MockTransport(handle_http),
                               server.sockets[0].getsockname()[1])
    assert len(result['runtime']['origins']) == 2
    assert len(result['recovery']) == 1
    root = run_root(panel)
    for child in (root / 'origins').iterdir():
        intent, _ = _pair(child, 'origin_intent')
        if intent['member']['token_id'] == missing_token:
            assert intent['schema_version'] == origin_worker.OWNED_VERSION
            assert 'window_dependency' not in intent
        else:
            assert intent['schema_version'] == origin_worker.WINDOW_VERSION
            facts, _ = _pair(child, 'origin_facts')
            assert not facts['projection']['pre_origin_window']['continuous_window_eligible']
    rp, _ = _pair(root, 'runtime_policy')
    assert sum(v['missing_reason'] == 'pre_snapshot_unavailable'
               for v in rp['window_inputs']['members'].values()) == 1


@pytest.mark.parametrize('extra', [{'port': 1}, {'transport': None}, {'window_root': '/tmp'},
                                  {'provenance': 'prospective'}, {'clock': 1}])
async def test_public_window_pilot_has_no_injected_history_transport_clock(tmp_path, extra):
    with pytest.raises(TypeError):
        await screening_worker.run_public_window_pilot(tmp_path / 'fs2_panel_test',
            implementation_commit='a'*40, rule=SnapshotTriggerPolicy(1, 3, 60000),
            freshness=ScreeningPolicy(60, 60), window_policy=config(), **extra)
    assert not list(tmp_path.iterdir())


async def test_window_reservation_refuses_before_first_screen_request(
    tmp_path, original_code, monkeypatch
):
    from collections import namedtuple

    _, panel, rows = await setup(tmp_path, original_code)
    source, calls = transport(rows)
    old = screening_worker.allocation(read_panel_declaration(panel))
    usage = namedtuple('Usage', 'total used free')
    monkeypatch.setattr(screening_worker.shutil, 'disk_usage',
                        lambda _: usage(10**12, 0, old['required_free_bytes']))
    with pytest.raises(ValueError, match='capacity'):
        await execute(panel, original_code, source, 1)
    assert not calls and not screening_worker.worker_root(panel).exists()


async def test_window_cancellation_drains_observers_and_preserves_failed_run(
    tmp_path, original_code
):
    _, panel, rows = await setup(tmp_path, original_code)
    source, _ = transport(rows)
    opened = asyncio.Event()
    active = set()

    async def handle(socket):
        token = json.loads(await socket.recv())['assets_ids'][0]
        active.add(token)
        opened.set()
        await socket.wait_closed()
        active.remove(token)

    async with serve(handle, '127.0.0.1', 0) as server:
        task = asyncio.create_task(execute(panel, original_code, source,
                                         server.sockets[0].getsockname()[1]))
        await asyncio.wait_for(opened.wait(), 60)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not active
    root = screening_worker.worker_root(panel)
    failure, _ = _pair(root, 'worker_failure')
    assert failure['stage'] == 'acquisition'
    assert not (root / 'worker_report.json').exists()
    assert list(root.glob('fs2_socket_window_*'))
    assert not run_root(panel).exists()
    before = snapshot(root)
    await asyncio.sleep(0.05)
    assert snapshot(root) == before  # no detached durable thread writes after cancellation
