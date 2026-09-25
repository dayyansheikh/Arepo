"""Endpoint diagnostics require actual post-window request starts and frozen identity."""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store.capture import Budget
from astrolabe.feature_store.source_run import SourceRun, _ordered_clocks, _pair
from astrolabe.research_panel import window_reconciliation as module
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.bound_window import WindowBindingPolicy, capture_bound_window
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.window_capture import SyntheticWindowFeed
from astrolabe.research_panel.window_reconciliation import (
    WindowReconciliationPolicy,
    read_window_reconciliation,
    record_window_reconciliation,
)
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_bound_window import output as bound_output
from tests.unit.test_research_panel_bound_window import pre
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_window_coverage import CONDITION, book


async def capture(computation, tmp_path, *, feed=None):
    return await capture_bound_window(computation, output_root=bound_output(tmp_path),
        feed=feed or SyntheticWindowFeed(((0, json.dumps(book())),)),
        policy=WindowBindingPolicy(60000, 60000), duration_ms=500)


async def post(tmp_path, *, closed=False, rules='Rules', token='1', market='10',
               gamma_status=200, book_status=200, bid='2', omit_book=False, gamma_gate=None):
    gamma = {'id': market, 'conditionId': CONDITION, 'outcomes': ['Yes', 'No'],
             'clobTokenIds': [token, '2'], 'description': rules, 'active': True,
             'closed': closed, 'archived': False, 'acceptingOrders': not closed}
    async def handler(request):
        is_gamma = request.url.path.startswith('/markets/')
        if is_gamma and gamma_gate:
            gamma_gate[0].set()
            await gamma_gate[1].wait()
        payload = gamma if is_gamma else book(bid, asset_id=token)
        return httpx.Response(gamma_status if is_gamma else book_status,
                              stream=Stream([json.dumps(payload).encode()]))
    root = tmp_path.resolve() / 'fs2_capture_post'
    run = SourceRun(root, transport=httpx.MockTransport(handler),
        policy_version='receipt-time-selected-market-v1', budget=Budget(requests=2),
        retained_bytes=4 * 1048576)
    await run.fetch('gamma.market', {'market_id': market})
    if not omit_book:
        await run.fetch('clob.book', {'token_id': token})
    computation = tmp_path.resolve() / 'fs2_book_computation_post'
    record_book_computation(root, output_root=computation, policy=QuoteInputPolicy(60, 60))
    return root, computation


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_window_reconciliation_test'


def record(tmp_path, post_root, *, policy=None, target=None):
    return record_window_reconciliation(bound_output(tmp_path), post_root,
        output_root=target or output(tmp_path),
        policy=policy or WindowReconciliationPolicy(60000, 60000, 1000))


async def prepare(tmp_path, **kwargs):
    source, computation = await pre(tmp_path)
    await capture(computation, tmp_path)
    post_source, post_root = await post(tmp_path, **kwargs)
    return source, computation, post_source, post_root


async def test_actual_order_and_exact_endpoint_values(tmp_path, monkeypatch):
    deps = await prepare(tmp_path)
    before = tuple(snapshot(p) for p in (*deps, bound_output(tmp_path)))
    result = record(tmp_path, deps[-1])
    root = output(tmp_path)
    policy, pa = _pair(root, 'window_reconciliation_policy')
    inputs, ia = _pair(root, 'window_reconciliation_input')
    facts, fa = _pair(root, 'window_reconciliation_report')
    assert result['state'] == 'comparable'
    assert result['start_comparison']['state'] == result['end_comparison']['state'] == 'agreement'
    assert _ordered_clocks(policy['declared_at'], pa['durable_ack'], inputs['read_started_at'],
        inputs['read_completed_at'], ia['durable_ack'], facts['computation_started_at'],
        facts['computed_at'], fa['durable_ack'])
    for receipt in inputs['inputs']['post_receipts']:
        assert _ordered_clocks(result['post_request_boundary'], receipt['request_started'],
                               receipt['first_received'], inputs['read_started_at'])
    assert result['end_comparison']['left']['bid'] == {
        'numerator': '2', 'denominator': '5', 'decimal': '0.4', 'decimal_state': 'exact'}
    assert int(result['uncovered_duration_ns']) > 0  # initial receipt delay is never repaired
    assert not result['continuous_sequence_proven'] and not result['full_book_equivalence']
    assert not result['origin_admitted'] and not result['feature_store_admitted']
    saved = snapshot(root)
    monkeypatch.setattr(module, '_clock', lambda: (_ for _ in ()).throw(AssertionError('clock')))
    assert read_window_reconciliation(root) == result
    assert saved == snapshot(root)
    assert before == tuple(snapshot(p) for p in (*deps, bound_output(tmp_path)))
    with pytest.raises(FileExistsError):
        record(tmp_path, deps[-1])


@pytest.mark.parametrize('kwargs,reason', [
    ({'rules': 'Changed resolution'}, 'post_identity_or_rules_changed_or_unavailable'),
    ({'closed': True}, 'post_market_closed'),
    ({'token': '3'}, 'post_requested_token_changed'),
    ({'market': '11'}, 'post_requested_market_changed'),
    ({'gamma_status': 503}, 'post_gamma.market_source_error'),
    ({'book_status': 429}, 'post_clob.book_rate_limited'),
    ({'omit_book': True}, 'post_source_pair_unavailable'),
])
async def test_changed_identity_closed_and_failed_sources(tmp_path, kwargs, reason):
    deps = await prepare(tmp_path, **kwargs)
    result = record(tmp_path, deps[-1])
    assert result['state'] == 'unavailable' and reason in result['reasons']
    assert result['end_comparison']['right'] is None
    assert result['original_identity']['market_id'] == '10'


async def test_endpoint_disagreement_preserves_exact_difference(tmp_path):
    deps = await prepare(tmp_path, bid='3.000')
    result = record(tmp_path, deps[-1])
    assert result['state'] == 'comparable'
    assert result['end_comparison']['state'] == 'disagreement'
    assert result['end_comparison']['right_minus_left']['bid_size']['numerator'] == '1'
    assert result['post_quote']['bid_size'] == '3.000'


@pytest.mark.parametrize('policy,reason', [
    (WindowReconciliationPolicy(0, 60000, 1000), 'post_source_stale_at_computation'),
    (WindowReconciliationPolicy(60000, 0, 1000), 'post_endpoint_separation_exceeded'),
    (WindowReconciliationPolicy(60000, 60000, 1), 'window_end_unavailable'),
])
async def test_frozen_receipt_and_endpoint_age_limits(tmp_path, policy, reason):
    deps = await prepare(tmp_path)
    assert reason in record(tmp_path, deps[-1], policy=policy)['reasons']


async def test_request_started_before_window_but_received_after_is_not_post_window(tmp_path):
    _, computation = await pre(tmp_path)
    entered, release = asyncio.Event(), asyncio.Event()
    task = asyncio.create_task(post(tmp_path, gamma_gate=(entered, release)))
    await entered.wait()
    await capture(computation, tmp_path)
    release.set()
    _, post_root = await task
    result = record(tmp_path, post_root)
    inputs, _ = _pair(output(tmp_path), 'window_reconciliation_input')
    gamma = next(v for v in inputs['inputs']['post_receipts'] if v['source_id'] == 'gamma.market')
    assert _ordered_clocks(gamma['request_started'], result['post_request_boundary'],
                           gamma['first_received'])
    assert 'post_request_not_after_bound_ack' in result['reasons']
    assert result['state'] == 'unavailable' and result['end_comparison']['right'] is None


async def test_invalid_tail_and_early_disconnect_never_use_last_good_quote(tmp_path):
    _, computation = await pre(tmp_path)
    await capture(computation, tmp_path, feed=SyntheticWindowFeed(
        ((0, json.dumps(book())), (1, 'bad json')), True))
    _, post_root = await post(tmp_path)
    result = record(tmp_path, post_root)
    assert result['start_comparison']['state'] == 'agreement'
    assert 'window_end_unavailable' in result['reasons']
    assert result['end_comparison']['left'] is None


@pytest.mark.parametrize('change', ['source', 'clock', 'value', 'receipt', 'origin'])
async def test_resealed_changes_and_dependency_corruption_refused(tmp_path, change):
    deps = await prepare(tmp_path)
    record(tmp_path, deps[-1])
    root = output(tmp_path)
    if change == 'source':
        next(deps[2].glob('*/raw.bin')).write_bytes(b'bad')
    elif change == 'clock':
        policy, _ = _pair(root, 'window_reconciliation_policy')
        rewrite(root, 'window_reconciliation_report', lambda p:
                p.update(computed_at=policy['declared_at']))
    elif change == 'receipt':
        rewrite(root, 'window_reconciliation_input', lambda p:
                p['inputs']['post_receipts'][0].update(receipt_hash='0' * 64))
    elif change == 'origin':
        rewrite(root, 'window_reconciliation_report', lambda p: p.update(origin_admitted=True))
    else:
        rewrite(root, 'window_reconciliation_report', lambda p:
                p['end_comparison']['right_minus_left']['bid'].update(numerator='7'))
    before = tuple(snapshot(p) for p in (*deps, root, bound_output(tmp_path)))
    with pytest.raises(ValueError):
        read_window_reconciliation(root)
    assert before == tuple(snapshot(p) for p in (*deps, root, bound_output(tmp_path)))


async def test_transitive_paths_and_payload_clock_overrides_refused(tmp_path):
    deps = await prepare(tmp_path)
    for parent in (*deps, bound_output(tmp_path)):
        with pytest.raises(ValueError, match='separate'):
            record(tmp_path, deps[-1], target=parent / 'fs2_window_reconciliation_nested')
    for key in ('clock', 'payload', 'provenance'):
        with pytest.raises(TypeError):
            record_window_reconciliation(bound_output(tmp_path), deps[-1],
                output_root=output(tmp_path), policy=WindowReconciliationPolicy(60000, 60000, 1000),
                **{key: None})


async def test_partial_acknowledgement_and_cancellation_preserve_evidence(tmp_path, monkeypatch):
    deps = await prepare(tmp_path)
    before = tuple(snapshot(p) for p in deps)
    original = Path.open
    def fail(path, *args, **kwargs):
        if path.name == 'window_reconciliation_input_ack.json':
            raise OSError('synthetic disk failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        record(tmp_path, deps[-1])
    monkeypatch.undo()
    assert (output(tmp_path) / 'window_reconciliation_input.json').exists()
    assert (output(tmp_path) / 'window_reconciliation_failure_ack.json').exists()
    with pytest.raises(ValueError, match='closure'):
        read_window_reconciliation(output(tmp_path))
    def cancel(path, *args, **kwargs):
        if path.name == 'window_reconciliation_input_ack.json':
            raise asyncio.CancelledError()
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', cancel)
    target = tmp_path / 'fs2_window_reconciliation_cancel'
    with pytest.raises(asyncio.CancelledError):
        record(tmp_path, deps[-1], target=target)
    assert (target / 'window_reconciliation_failure_ack.json').exists()
    assert before == tuple(snapshot(p) for p in deps)


async def test_concurrent_writer_and_finite_limits(tmp_path, monkeypatch):
    deps = await prepare(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(record, tmp_path, deps[-1]) for _ in range(2)]
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except FileExistsError:
                results.append('lost')
    assert sum(v == 'lost' for v in results) == 1
    assert sum(isinstance(v, dict) for v in results) == 1
    disk = module.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda p:
                        disk._replace(free=module.LIMITS['free_reserve_bytes']))
    with pytest.raises(ValueError, match='storage reserve'):
        record(tmp_path, deps[-1], target=tmp_path / 'fs2_window_reconciliation_full')
    with pytest.raises(ValueError, match='deadline'):
        module._check(output(tmp_path), time.monotonic() - 181)
    with pytest.raises(ValueError, match='retained'):
        module._check(output(tmp_path), time.monotonic(), module.LIMITS['max_output_bytes'])
