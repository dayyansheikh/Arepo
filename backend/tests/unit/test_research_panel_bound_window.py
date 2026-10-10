"""Actual source identity must be consumed and durably bound before subscription."""

import asyncio
import json
import time
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store.capture import Budget
from astrolabe.feature_store.source_run import SourceRun, _ordered_clocks, _pair
from astrolabe.research_panel import bound_window as module
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.bound_window import (
    CHILD,
    WindowBindingPolicy,
    capture_bound_window,
    read_bound_window,
)
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.window_capture import SyntheticWindowFeed
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_window_coverage import CONDITION, book


async def pre(tmp_path, *, closed=False, rules='Rules', market='10'):
    gamma = {'id': market, 'conditionId': CONDITION, 'outcomes': ['Yes', 'No'],
             'clobTokenIds': ['1', '2'], 'description': rules, 'active': True,
             'closed': closed, 'archived': False, 'acceptingOrders': not closed}
    def handler(request):
        payload = gamma if request.url.path.startswith('/markets/') else book()
        return httpx.Response(200, stream=Stream([json.dumps(payload).encode()]))
    root = tmp_path.resolve() / 'fs2_capture_pre'
    run = SourceRun(root, transport=httpx.MockTransport(handler),
                    policy_version='receipt-time-selected-market-v1',
                    budget=Budget(requests=2), retained_bytes=4 * 1048576)
    await run.fetch('gamma.market', {'market_id': market})
    await run.fetch('clob.book', {'token_id': '1'})
    computation = tmp_path.resolve() / 'fs2_book_computation_pre'
    record_book_computation(root, output_root=computation, policy=QuoteInputPolicy(60, 60))
    return root, computation


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_bound_window_test'


async def capture(pre_root, tmp_path, *, policy=None, feed=None):
    return await capture_bound_window(pre_root, output_root=output(tmp_path),
        feed=feed or SyntheticWindowFeed(((0, json.dumps(book())),), True),
        policy=policy or WindowBindingPolicy(60000, 60000), duration_ms=50)


async def test_actual_read_binding_precedes_exact_derived_subscription(tmp_path, monkeypatch):
    source, computation = await pre(tmp_path)
    before = (snapshot(source), snapshot(computation))
    report = await capture(computation, tmp_path)
    root = output(tmp_path)
    policy, pa = _pair(root, 'bound_window_policy')
    binding, ba = _pair(root, 'bound_window_binding')
    child, ca = _pair(root / CHILD, 'window_policy')
    assert _ordered_clocks(policy['declared_at'], pa['durable_ack'], binding['read_started_at'],
        binding['read_completed_at'], ba['durable_ack'], child['declared_at'], ca['durable_ack'],
        report['window']['subscription_sent_at'], report['bound_window_available_at'])
    assert child['policy']['subscription'] == {'assets_ids': ['1'], 'type': 'market'}
    assert child['policy']['condition_id'] == CONDITION
    assert report['state'] == 'fresh_at_subscription'
    assert report['identity']['market_id'] == '10'
    assert not report['origin_admitted'] and not report['continuous_sequence_proven']
    saved = snapshot(root)
    monkeypatch.setattr(module, '_clock', lambda: (_ for _ in ()).throw(
        AssertionError('new clock')))
    assert read_bound_window(root) == report
    assert snapshot(root) == saved and before == (snapshot(source), snapshot(computation))
    with pytest.raises(FileExistsError):
        await capture(computation, tmp_path)


@pytest.mark.parametrize('closed,policy', [(True, WindowBindingPolicy(60000, 60000)),
                                         (False, WindowBindingPolicy(0, 0))])
async def test_closed_or_stale_pre_evidence_never_starts_window(tmp_path, closed, policy):
    source, computation = await pre(tmp_path, closed=closed)
    before = snapshot(source)
    with pytest.raises(ValueError, match='observed|stale'):
        await capture(computation, tmp_path, policy=policy)
    assert not (output(tmp_path) / CHILD).exists()
    assert (output(tmp_path) / 'bound_window_failure_ack.json').exists()
    assert snapshot(source) == before


async def test_subscription_delay_is_explicit_without_rewriting_binding(tmp_path, monkeypatch):
    _, computation = await pre(tmp_path)
    original = module.capture_window
    async def slow(*args, **kwargs):
        await asyncio.sleep(10.2)
        return await original(*args, **kwargs)
    monkeypatch.setattr(module, 'capture_window', slow)
    report = await capture(computation, tmp_path, policy=WindowBindingPolicy(10000, 10000))
    assert report['state'] == 'identity_expired_before_subscription'
    binding, ba = _pair(output(tmp_path), 'bound_window_binding')
    assert binding['identity'] == report['identity']
    assert ba['durable_ack'] == report['binding_available_at']
    assert not report['origin_admitted']


@pytest.mark.parametrize('change', ['identity', 'clock', 'window', 'raw', 'admission'])
async def test_resealed_identity_time_and_source_mutation_refused(tmp_path, change):
    source, computation = await pre(tmp_path)
    await capture(computation, tmp_path)
    root = output(tmp_path)
    if change == 'identity':
        rewrite(root, 'bound_window_binding', lambda p: p['identity'].update(token_id='2'))
    elif change == 'clock':
        policy, _ = _pair(root, 'bound_window_policy')
        rewrite(root, 'bound_window_binding', lambda p:
                p.update(read_completed_at=policy['declared_at']))
    elif change == 'window':
        rewrite(root / CHILD, 'window_policy', lambda p: p['policy'].update(token_id='2'))
    elif change == 'raw':
        next(source.glob('*/raw.bin')).write_bytes(b'bad')
    else:
        rewrite(root, 'bound_window_report', lambda p: p.update(origin_admitted=True))
    before = (snapshot(root), snapshot(source), snapshot(computation))
    with pytest.raises(ValueError):
        read_bound_window(root)
    assert before == (snapshot(root), snapshot(source), snapshot(computation))


async def test_dependency_paths_and_arbitrary_identity_or_live_feed_refused(tmp_path):
    source, computation = await pre(tmp_path)
    for parent in (source, computation):
        with pytest.raises(ValueError, match='separate'):
            await capture_bound_window(computation, output_root=parent / 'fs2_bound_window_nested',
                feed=SyntheticWindowFeed(()), policy=WindowBindingPolicy(60000, 60000))
    for key in ('token_id', 'condition_id', 'clock', 'payload', 'provenance'):
        with pytest.raises(TypeError):
            await capture_bound_window(computation, output_root=output(tmp_path),
                feed=SyntheticWindowFeed(()), policy=WindowBindingPolicy(60000, 60000),
                **{key: None})
    with pytest.raises(ValueError, match='synthetic'):
        await capture_bound_window(computation, output_root=output(tmp_path), feed=None,
                                    policy=WindowBindingPolicy(60000, 60000))


async def test_partial_binding_ack_stops_before_capture(tmp_path, monkeypatch):
    _, computation = await pre(tmp_path)
    original = Path.open
    def fail(path, *args, **kwargs):
        if path.name == 'bound_window_binding_ack.json':
            raise OSError('synthetic disk failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        await capture(computation, tmp_path)
    assert (output(tmp_path) / 'bound_window_binding.json').exists()
    assert not (output(tmp_path) / CHILD).exists()
    assert (output(tmp_path) / 'bound_window_failure_ack.json').exists()


async def test_concurrent_capture_single_owner_and_cancellation_preserves_child(tmp_path):
    _, computation = await pre(tmp_path)
    results = await asyncio.gather(capture(computation, tmp_path), capture(computation, tmp_path),
                                    return_exceptions=True)
    assert sum(isinstance(r, FileExistsError) for r in results) == 1
    assert sum(isinstance(r, dict) for r in results) == 1
    target = tmp_path.resolve() / 'fs2_bound_window_cancel'
    task = asyncio.create_task(capture_bound_window(computation, output_root=target,
        feed=SyntheticWindowFeed(()), policy=WindowBindingPolicy(60000, 60000), duration_ms=60000))
    for _ in range(500):
        if (target / CHILD / 'event_000003_ack.json').exists():
            break
        await asyncio.sleep(.005)
    assert (target / CHILD / 'event_000003_ack.json').exists()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (target / CHILD / 'window_failure_ack.json').exists()
    assert (target / 'bound_window_failure_ack.json').exists()
    assert not (target / 'bound_window_report.json').exists()


async def test_whole_reserve_and_finite_checks_prevent_unbudgeted_child(tmp_path, monkeypatch):
    _, computation = await pre(tmp_path)
    disk = module.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda p:
                        disk._replace(free=module.LIMITS['free_reserve_bytes']))
    with pytest.raises(ValueError, match='storage reserve'):
        await capture(computation, tmp_path)
    assert not output(tmp_path).exists()
    monkeypatch.undo()
    output(tmp_path).mkdir()
    with pytest.raises(ValueError, match='deadline'):
        module._check(output(tmp_path), time.monotonic() - 181)
    with pytest.raises(ValueError, match='retained'):
        module._check(output(tmp_path), time.monotonic(), module.LIMITS['max_output_bytes'])
    (output(tmp_path) / 'link').symlink_to(computation / 'book_facts.json')
    with pytest.raises(ValueError, match='symlink'):
        module._check(output(tmp_path), time.monotonic())
