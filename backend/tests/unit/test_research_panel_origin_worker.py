"""End-to-end synthetic origin collection, actual clocks and immutable abstentions."""

import asyncio
import shutil
import time
from datetime import timedelta

import httpx
import pytest

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import origin_worker
from astrolabe.research_panel.activation import activation_root
from astrolabe.research_panel.origin_worker import (
    COMPUTATION,
    SOURCE,
    exercise_origins,
    read_origin_run,
    run_root,
)
from astrolabe.research_panel.panel_declaration import declare_panel
from astrolabe.research_panel.panel_selection import create_panel_selection
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


async def setup(tmp_path, original_code, **changes):
    source = await frame(tmp_path, [market(1)])
    panel = tmp_path / 'fs2_panel_origins'
    declare_panel(source, implementation_commit=original_code[1], output_root=panel,
        protocol=protocol(cycles=1, target_attempts=1, scheduled_slots=1, triggered_slots=0,
            max_origin_save_seconds=1, source_response_bytes=65536,
            source_run_retained_bytes=1048576, **changes), storage_profile='compact-v1')
    create_panel_selection(panel, repository=original_code[0])
    return panel


def transport(panel, calls, *, changed_rules=False, book_status=200, closed=False,
              delay=0, cancel=False, large=False):
    async def handler(request):
        roots = [p for p in run_root(panel).iterdir() if p.is_dir()]
        assert len(roots) == 1
        assert (roots[0] / 'origin_intent_ack.json').exists()
        calls.append((request.url.path, dict(request.url.params)))
        status = 200
        if request.url.path == '/markets/1':
            if cancel:
                raise asyncio.CancelledError()
            if delay:
                await asyncio.sleep(delay)
            body = market(1, active=True, closed=closed, archived=False, acceptingOrders=True)
            if changed_rules:
                body['description'] = 'changed rules'
            if large:
                body['description'] = 'x' * 70000
        elif request.url.path == '/book':
            status = book_status
            body = {'asset_id': '2', 'market': '0x' + f'{1:064x}',
                    'bids': [{'price': '0.400', 'size': '2.00'}],
                    'asks': [{'price': '0.600', 'size': '5.00'}]}
        else:
            assert request.url.path == '/v2/trades'
            body = {'data': [], 'pagination': {'has_more': False, 'next_cursor': None}}
        return httpx.Response(status, stream=Stream([_json_bytes(body)]))
    return httpx.MockTransport(handler)


def only_origin(panel):
    return next(p for p in run_root(panel).iterdir() if p.is_dir())


async def test_fixed_requests_source_quotas_actual_freeze_and_exact_replay(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    calls = []
    result = await exercise_origins(panel, transport=transport(panel, calls))
    assert [path for path, _ in calls] == ['/markets/1', '/book', '/v2/trades']
    assert calls[1][1] == {'token_id': '2'}
    assert calls[2][1] == {'condition': '0x' + f'{1:064x}', 'limit': '10', 'taker_only': 'true'}
    assert result['results'][0]['state'] == 'observed'
    assert result['provenance_class'] == 'synthetic'
    assert result['targets_collected'] is result['origin_admitted'] is False
    root = only_origin(panel)
    intent, intent_ack = _pair(root, 'origin_intent')
    facts, ack = _pair(root, 'origin_facts')
    source, _ = _pair(root / SOURCE, 'run')
    computation, _ = _pair(root / COMPUTATION, 'quote_policy')
    assert source['budget'] == intent['source_budget']
    assert source['retention_quota']['retained_bytes'] == 1048576
    assert computation['limits']['storage_profile'] == 'compact-v1'
    quote = facts['projection']['quote']
    assert quote['midpoint'] == '0.500'
    assert facts['projection']['flow_window_complete'] is False
    assert intent_ack['durable_ack']['utc'] < facts['read_started_at']['utc']
    assert facts['read_started_at']['utc'] <= facts['origin_at']['utc'] <= ack['durable_ack']['utc']
    assert _time(ack['durable_ack']) < _time(facts['origin_at']) + timedelta(seconds=60)
    saved = snapshot(run_root(panel)), snapshot(activation_root(panel))
    assert read_origin_run(panel) == result
    assert saved == (snapshot(run_root(panel)), snapshot(activation_root(panel)))
    with pytest.raises(FileExistsError):
        await exercise_origins(panel, transport=transport(panel, calls))
    assert len(calls) == 3


@pytest.mark.parametrize('kwargs,state', [
    ({'changed_rules': True}, 'identity_changed_since_selection'),
    ({'book_status': 429}, 'rate_limited'),
    ({'closed': True}, 'market_closed'),
])
async def test_abstentions_preserve_all_assigned_source_records(
        tmp_path, original_code, kwargs, state):
    panel = await setup(tmp_path, original_code)
    calls = []
    result = await exercise_origins(panel, transport=transport(panel, calls, **kwargs))
    assert len(calls) == 3 and result['results'][0]['state'] == state
    facts, _ = _pair(only_origin(panel), 'origin_facts')
    assert len(facts['projection']['source_statuses']) == 3
    assert facts['origin_admitted'] is False


async def test_actual_late_save_keeps_original_freeze_and_is_ineligible(
        tmp_path, original_code, monkeypatch):
    panel = await setup(tmp_path, original_code)
    persist = origin_worker._persist
    def delayed(root, name, payload):
        if name == 'origin_facts':
            time.sleep(1.1)
        return persist(root, name, payload)
    monkeypatch.setattr(origin_worker, '_persist', delayed)
    result = await exercise_origins(panel, transport=transport(panel, []))
    assert result['results'][0]['state'] == 'late_persistence'
    facts, _ = _pair(only_origin(panel), 'origin_facts')
    assert facts['projection']['state_at_freeze'] == 'observed'
    assert read_origin_run(panel) == result


async def test_expired_slot_makes_no_source_requests(tmp_path, original_code):
    panel = await setup(tmp_path, original_code, max_origin_delay_seconds=0)
    calls = []
    result = await exercise_origins(panel, transport=transport(panel, calls))
    assert not calls and result['results'][0]['state'] == 'expired_before_request'
    assert not (only_origin(panel) / SOURCE).exists()


async def test_expiry_between_requests_preserves_partial_source(tmp_path, original_code):
    panel = await setup(tmp_path, original_code, max_origin_delay_seconds=3)
    calls = []
    result = await exercise_origins(panel, transport=transport(panel, calls, delay=2.1))
    assert len(calls) == 1
    assert result['results'][0]['state'] == 'expired_during_requests'
    assert list((only_origin(panel) / SOURCE).glob('*/raw.bin'))
    assert not (only_origin(panel) / 'origin_facts.json').exists()
    assert read_origin_run(panel) == result


async def test_oversized_response_keeps_partial_raw_and_abstaining_slot(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    result = await exercise_origins(panel, transport=transport(panel, [], large=True))
    assert result['results'][0]['state'] == 'identity_unresolved_at_receipt'
    root = only_origin(panel)
    raw = list((root / SOURCE).glob('*/raw.bin'))
    assert raw and any(p.stat().st_size == 65536 for p in raw)
    facts, _ = _pair(root, 'origin_facts')
    assert facts['projection']['source_statuses'][0]['state'] == 'transport_gap'
    before = snapshot(root)
    assert read_origin_run(panel) == result
    assert snapshot(root) == before


async def test_cancelled_intent_is_preserved_and_not_resumed(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    calls = []
    with pytest.raises(asyncio.CancelledError):
        await exercise_origins(panel, transport=transport(panel, calls, cancel=True))
    assert (run_root(panel) / 'worker_failure_ack.json').exists()
    assert (only_origin(panel) / 'origin_intent_ack.json').exists()
    with pytest.raises(FileExistsError):
        await exercise_origins(panel, transport=transport(panel, calls))
    assert len(calls) == 1


@pytest.mark.parametrize('change', ['raw', 'intent', 'price', 'claim', 'extra',
                                   'price_resealed', 'intent_resealed'])
async def test_tampered_origin_source_or_metadata_refused(tmp_path, original_code, change):
    panel = await setup(tmp_path, original_code)
    await exercise_origins(panel, transport=transport(panel, []))
    root = only_origin(panel)
    if change == 'raw':
        next((root / SOURCE).glob('*/raw.bin')).write_bytes(b'changed')
    elif change in {'intent', 'intent_resealed'}:
        amend(root, 'origin_intent', lambda p: p['member'].update(token_id='3'))
    elif change in {'price', 'price_resealed'}:
        amend(root, 'origin_facts', lambda p: p['projection']['quote'].update(midpoint='0.999'))
    elif change == 'claim':
        amend(run_root(panel), 'worker_report', lambda p: p.update(origin_admitted=True))
    else:
        (run_root(panel) / 'unexpected').write_text('{}')
    if change.endswith('resealed'):
        inventory = origin_worker._snapshot(root, 10 * 1048576)
        amend(root, 'origin_receipt', lambda p: p.update(inventory=inventory))
    with pytest.raises(ValueError):
        read_origin_run(panel)


async def test_concurrent_workers_have_one_exclusive_owner(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    calls = []
    results = await asyncio.gather(
        exercise_origins(panel, transport=transport(panel, calls)),
        exercise_origins(panel, transport=transport(panel, calls)), return_exceptions=True)
    assert sum(isinstance(r, FileExistsError) for r in results) == 1
    assert sum(isinstance(r, dict) for r in results) == 1
    assert not (run_root(panel) / 'worker_failure.json').exists()
    assert len(calls) == 3


async def test_no_live_transport_and_no_caller_clock_or_payload(tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    with pytest.raises(ValueError, match='synthetic MockTransport'):
        await exercise_origins(panel, transport=None)
    with pytest.raises(TypeError):
        await exercise_origins(panel, transport=transport(panel, []), clock=None)
    assert not run_root(panel).exists()


async def test_low_disk_preflight_and_read_only_recovery(tmp_path, original_code, monkeypatch):
    panel = await setup(tmp_path, original_code)
    normal = shutil.disk_usage
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(1, 1, 0))
    with pytest.raises(ValueError, match='complete origin-worker reservation'):
        await exercise_origins(panel, transport=transport(panel, []))
    assert not run_root(panel).exists()
    monkeypatch.setattr(shutil, 'disk_usage', normal)
    result = await exercise_origins(panel, transport=transport(panel, []))
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(1, 1, 0))
    assert read_origin_run(panel) == result
