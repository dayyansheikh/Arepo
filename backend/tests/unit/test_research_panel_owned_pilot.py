"""Complete owned pilot path with synthetic evidence and real clocks, never a live panel claim."""

import asyncio
import json
import sys
import threading
from collections import Counter

import httpx
import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import origin_worker, runtime, screening, screening_worker
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_screening_worker import prepared

original_code = _original_code


def transport(rows, *, changed_origin=False, enriched_target=False):
    by_id = {r['id']: r for r in rows}
    by_token = {json.loads(r['clobTokenIds'])[0]: r for r in rows}
    gamma = Counter()
    calls = []
    lock = threading.Lock()

    async def handle(request):
        with lock:
            calls.append(str(request.url))
            if request.url.path.startswith('/markets/'):
                mid = request.url.path.split('/')[-1]
                gamma[mid] += 1
                nth = gamma[mid]
            else:
                mid, nth = None, None
        if mid is not None:
            body = dict(by_id[mid])
            body.pop('events', None)
            if changed_origin and nth >= 2:
                body['description'] = 'Changed rules'
            if enriched_target and nth >= 3:
                body['events'] = [{'id': '42'}]
        elif request.url.path == '/book':
            token = request.url.params['token_id']
            row = by_token[token]
            body = {'asset_id': token, 'market': row['conditionId'],
                    'bids': [{'price': '0.4', 'size': '2' if row['id'] == '1' else '1'}],
                    'asks': [{'price': '0.6', 'size': '1'}]}
        else:
            assert request.url.path == '/v2/trades'
            body = {'data': [], 'pagination': {'has_more': False, 'next_cursor': None}}
        return httpx.Response(200, stream=Stream([json.dumps(body).encode()]))

    return httpx.MockTransport(handle), calls


async def execute(panel, code, source):
    return await screening_worker.run_synthetic_pilot(
        panel, implementation_commit=code[1], repository=code[0], transport=source,
        rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(60, 60),
        concurrency=2, runtime_concurrency=3)


async def setup(tmp_path, code):
    return await prepared(tmp_path, code, event_ids=True, max_origin_delay_seconds=30,
                          horizon_seconds=8, tolerance_seconds=5, max_origin_save_seconds=2,
                          max_quote_age_seconds=60)


async def test_owned_screen_origin_target_and_original_audit_in_causal_order(
    tmp_path, original_code
):
    _, panel, rows = await setup(tmp_path, original_code)
    source, calls = transport(rows)
    full_read_counts = []
    code = screening._selected.__code__

    def observe(frame, event, arg):
        if event == 'call' and frame.f_code is code:
            full_read_counts.append(len(calls))

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        result = await execute(panel, original_code, source)
    finally:
        sys.setprofile(previous)
    assert full_read_counts == [0, 14]  # 4 screen + 6 origin + 4 due; audit is last
    assert len(calls) == 14
    assert result['state'] == 'pilot_collected_unaccepted'
    assert result['runtime']['provenance_class'] == 'synthetic'
    assert {o['state'] for o in result['runtime']['origins']} == {'observed'}
    assert {a['state'] for a in result['runtime']['attempts']} == {'recorded'}
    assert len(result['recovery']) == 1
    assert result['recovery'][0]['schema_version'] == 'fs2-original-runtime-read-v1'
    assert result['role_capacity']['counts_per_cycle'] == {
        'scheduled': 2, 'triggered': 1, 'control': 1}
    assert not result['accepted_panel'] and not result['origin_admitted']
    root = runtime.run_root(panel)
    for child in (root / 'origins').iterdir():
        intent, _ = _pair(child, 'origin_intent')
        facts, _ = _pair(child, 'origin_facts')
        assert intent['schema_version'] == origin_worker.OWNED_VERSION
        assert intent['member']['frame_identity']['source_event_ids'] == ['42']
        comparison = facts['projection']['identity_comparison']
        assert comparison['core_identity_equal']
        assert comparison['current_event_membership'] == 'unavailable'
        assert comparison['frame_mapping_version'] != comparison['current_mapping_version']
        manifest = facts['projection']['feature_manifest']
        assert manifest['source_provenance_class'] == 'synthetic'
        assert not manifest['continuous_window_eligible']
    saved = len(calls)
    with pytest.raises(FileExistsError):
        await execute(panel, original_code, source)
    assert len(calls) == saved


async def test_owned_changed_rules_abstain_and_preserve_due_skips(tmp_path, original_code):
    _, panel, rows = await setup(tmp_path, original_code)
    source, calls = transport(rows, changed_origin=True)
    result = await execute(panel, original_code, source)
    assert len(calls) == 10  # screening and origins; no target for invalid origin
    assert {o['state'] for o in result['runtime']['origins']} == {
        'identity_changed_since_selection'}
    assert {a['state'] for a in result['runtime']['attempts']} == {'origin_ineligible'}
    assert not result['accepted_panel']


async def test_target_event_enrichment_is_not_silently_core_compared(tmp_path, original_code):
    _, panel, rows = await setup(tmp_path, original_code)
    source, calls = transport(rows, enriched_target=True)
    result = await execute(panel, original_code, source)
    assert len(calls) == 14
    assert {o['state'] for o in result['runtime']['origins']} == {'observed'}
    for child in (runtime.run_root(panel) / 'targets').iterdir():
        facts, _ = _pair(child, 'target_facts')
        adaptation = facts['projection']['adaptation']
        assert adaptation['quote']['source_status'] == 'identity_changed_since_origin'
    assert not result['accepted_panel']


async def test_public_pilot_refuses_payload_clock_transport_and_provenance_overrides(tmp_path):
    common = dict(implementation_commit='a' * 40, rule=SnapshotTriggerPolicy(1, 3, 60000),
                  freshness=ScreeningPolicy(60, 60))
    for extra in ({'transport': None}, {'provenance': 'prospective'},
                  {'clock': 1}, {'payload': {}}):
        with pytest.raises(TypeError):
            await screening_worker.run_public_pilot(tmp_path / 'fs2_panel_none', **common, **extra)
    assert not list(tmp_path.iterdir())


async def test_public_pilot_rejects_synthetic_selection_before_sources(tmp_path, original_code):
    _, panel, _ = await setup(tmp_path, original_code)
    with pytest.raises(ValueError, match='provenance'):
        await screening_worker.run_public_pilot(
            panel, implementation_commit=original_code[1], repository=original_code[0],
            rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(60, 60))
    assert not list(screening_worker.worker_root(panel).glob('fs2_capture_*'))
    assert not runtime.run_root(panel).exists()


async def test_cancellation_after_screening_drains_runtime_without_success(tmp_path, original_code):
    _, panel, rows = await setup(tmp_path, original_code)
    source, calls = transport(rows)

    async def cancel(request):
        if runtime.run_root(panel).exists():
            raise asyncio.CancelledError()
        return await source.handle_async_request(request)

    with pytest.raises(asyncio.CancelledError):
        await execute(panel, original_code, httpx.MockTransport(cancel))
    root = screening_worker.worker_root(panel)
    failure, _ = _pair(root, 'worker_failure')
    assert failure['stage'] == 'runtime'
    assert not (root / 'worker_report.json').exists()
    assert not (runtime.run_root(panel) / 'runtime_report.json').exists()
    assert len(calls) == 4


@pytest.mark.parametrize('value', [None, True, 0, 9])
@pytest.mark.parametrize('public', [True, False])
async def test_pilot_invalid_runtime_concurrency_refused_before_writes(tmp_path, value, public):
    calls = []

    def handle(request):
        calls.append(request)
        raise AssertionError('invalid input must not request sources')

    function = screening_worker.run_public_pilot if public else screening_worker.run_synthetic_pilot
    extra = {} if public else {'transport': httpx.MockTransport(handle)}
    with pytest.raises(ValueError, match='concurrency'):
        await function(
            tmp_path / 'fs2_panel_invalid', implementation_commit='a' * 40,
            rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(60, 60),
            runtime_concurrency=value, **extra)
    assert not calls
    assert not list(tmp_path.iterdir())
