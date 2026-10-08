"""Actual journal reads keep observation identity separate from quote eligibility."""

import json

import httpx
import pytest

from astrolabe.feature_store.capture import Budget
from astrolabe.feature_store.source_run import SourceRun
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.bound_window import _pre
from astrolabe.research_panel.observation_binding import read_observation_binding
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_window_coverage import CONDITION, book

original_code = _original_code


async def prepare(tmp_path, state):
    gamma = {'id': '10', 'conditionId': CONDITION, 'outcomes': ['Yes', 'No'],
             'clobTokenIds': ['1', '2'], 'description': 'Rules', 'active': True,
             'closed': state == 'closed', 'archived': False, 'acceptingOrders': True}
    payload = book()
    if state in {'bid_only', 'empty'}:
        payload['asks'] = []
    if state in {'ask_only', 'empty'}:
        payload['bids'] = []
    if state == 'crossed':
        payload['bids'][0]['price'] = '0.9'
    if state == 'wrong_identity':
        gamma['clobTokenIds'] = ['3', '4']

    def handler(request):
        value = gamma if request.url.path.startswith('/markets/') else payload
        return httpx.Response(200, stream=Stream([json.dumps(value).encode()]))

    source = tmp_path.resolve() / 'fs2_capture_pre'
    run = SourceRun(source, transport=httpx.MockTransport(handler),
                    policy_version='receipt-time-selected-market-v1',
                    budget=Budget(requests=2), retained_bytes=4 * 1048576)
    await run.fetch('gamma.market', {'market_id': '10'})
    await run.fetch('clob.book', {'token_id': '1'})
    root = tmp_path.resolve() / 'fs2_book_computation_pre'
    record_book_computation(source, output_root=root, policy=QuoteInputPolicy(60, 60))
    return root


@pytest.mark.parametrize('state', ['observed', 'bid_only', 'ask_only', 'empty'])
async def test_actual_binding_preserves_missing_midpoint_and_legacy_refusal(tmp_path, state):
    root = await prepare(tmp_path, state)
    before = snapshot(tmp_path)
    result = read_observation_binding(root)
    assert result['identity']['token_id'] == '1'
    assert result['requires_actual_subscription_freshness_check']
    assert not any(result[k] for k in ('origin_admitted', 'history_admitted', 'socket_admitted'))
    if state == 'observed':
        assert result['pre_midpoint'] is not None
        assert _pre(root)['identity'] == result['identity']
    else:
        assert result['pre_midpoint'] is None
        assert result['pre_quote_state'] == 'one_sided_or_missing'
        with pytest.raises(ValueError, match='observed pre-window'):
            _pre(root)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('state', ['closed', 'crossed', 'wrong_identity'])
async def test_invalid_or_unbound_source_refused(tmp_path, state):
    root = await prepare(tmp_path, state)
    with pytest.raises(ValueError, match='source book|source identity'):
        read_observation_binding(root)


@pytest.mark.parametrize('early_close', [False, True])
async def test_one_sided_wire_and_original_recovery(tmp_path, original_code, early_close):
    from websockets.asyncio.server import serve

    from astrolabe.research_panel.bound_window import WindowBindingPolicy
    from astrolabe.research_panel.original_reader import read_original_socket_window
    from astrolabe.research_panel.socket_window import capture_loopback_socket
    from astrolabe.research_panel.socket_window_journal import OBSERVATION_VERSION

    pre = await prepare(tmp_path, 'bid_only')
    root = tmp_path / 'fs2_socket_window_observation'

    async def handler(socket):
        assert json.loads(await socket.recv()) == {'assets_ids': ['1'], 'type': 'market'}
        await socket.send(json.dumps(book()))
        if early_close:
            await socket.close()
        else:
            await socket.wait_closed()

    async with serve(handler, '127.0.0.1', 0, compression=None) as server:
        report = await capture_loopback_socket(pre, output_root=root,
            port=server.sockets[0].getsockname()[1], policy=WindowBindingPolicy(60000, 60000),
            duration_ms=100, binding_mode='observation')
    assert report['schema_version'] == OBSERVATION_VERSION
    assert report['frame_count'] == 1
    assert report['terminal'] == ('receive_error' if early_close else 'interval_ended')
    assert report['close_state'] == 'closed'
    assert not report['origin_admitted'] and not report['continuous_sequence_proven']
    before = snapshot(root)
    result = read_original_socket_window(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_socket_window_read_obs')
    assert result['report'] == report
    assert snapshot(root) == before
    from astrolabe.feature_store.capture import _clock
    from astrolabe.feature_store.source_run import _pair
    from astrolabe.research_panel.origin_window import OriginWindowPolicy, project_origin_window
    from astrolabe.research_panel.socket_analysis import record_socket_analysis
    from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy

    analysis = tmp_path / 'fs2_socket_analysis_obs'
    record_socket_analysis(root, output_root=analysis,
                           policy=WindowReconciliationPolicy(60000, 60000, 1000))
    facts, _ = _pair(pre, 'book_facts')
    result = project_origin_window(analysis, facts['projection']['snapshots'][0]['quote'],
        provenance='synthetic', cutoff=_clock(), policy=OriginWindowPolicy(60000, 60000))
    assert result['history'] is None
    assert 'snapshot_unavailable' in result['history_reasons']


async def test_stale_observation_binding_refuses_before_connect(tmp_path):
    from astrolabe.research_panel.bound_window import WindowBindingPolicy
    from astrolabe.research_panel.socket_window import capture_loopback_socket

    pre = await prepare(tmp_path, 'empty')
    result = await capture_loopback_socket(pre,
        output_root=tmp_path / 'fs2_socket_window_stale', port=1,
        policy=WindowBindingPolicy(0, 0), duration_ms=100, binding_mode='observation')
    assert result['terminal'] == 'refused'
    assert result['close_state'] == 'not_connected'
    assert result['subscription_sent_at'] is None

