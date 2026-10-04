"""Actual read/compute/save and exact cold replay of synthetic snapshot components."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel import _PACKAGE_FILES
from astrolabe.research_panel import book_computation as module
from astrolabe.research_panel.book_computation import (
    CHILD,
    LIMITS,
    read_book_computation,
    record_book_computation,
)
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_quote_computation import source


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_book_computation_test'


def record(root, tmp_path, policy=None):
    return record_book_computation(root, output_root=output(tmp_path),
                                   policy=policy or QuoteInputPolicy(60, 60))


async def test_actual_read_compute_save_order_and_exact_replay(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    original = snapshot(root)
    report = record(root, tmp_path)
    target = output(tmp_path)
    policy, p_ack = _pair(target, 'book_policy')
    child, c_ack = _pair(target / CHILD, 'read_policy')
    facts, ack = _pair(target, 'book_facts')
    assert _ordered_clocks(policy['declared_at'], p_ack['durable_ack'], child['declared_at'],
        c_ack['durable_ack'], facts['input_read']['read_started_at'],
        facts['input_read']['read_available_at'], facts['computation_started_at'],
        facts['computed_at'], ack['durable_ack'])
    component = facts['projection']['snapshots'][0]['components']['F08_snapshot']
    assert component['numerator'] == '-3' and component['denominator'] == '7'
    assert component['decimal'] is None
    assert report['snapshot_states'] == {'observed': 1}
    assert report['source_provenance_class'] == 'synthetic'
    assert report['origin_admitted'] is report['feature_store_admitted'] is False
    assert report['source_observation_count'] == 2 and 'projection' not in report
    saved = snapshot(target)
    monkeypatch.setattr(module, '_clock', lambda: (_ for _ in ()).throw(
        AssertionError('new clock')))
    assert read_book_computation(target) == report
    assert snapshot(root) == original and snapshot(target) == saved
    with pytest.raises(FileExistsError):
        record(root, tmp_path)


@pytest.mark.parametrize('kwargs,state', [
    ({'gamma_status': 503}, 'identity_unresolved_at_receipt'),
    ({'book_status': 429}, 'rate_limited'),
    ({'late_identity': True}, 'identity_unresolved_at_receipt'),
])
async def test_failed_sources_and_late_identity_stay_unavailable(tmp_path, kwargs, state):
    root, _ = await source(tmp_path, **kwargs)
    assert record(root, tmp_path)['snapshot_states'] == {state: 1}
    facts, _ = _pair(output(tmp_path), 'book_facts')
    assert facts['projection']['snapshots'][0]['components'] is None
    assert len(facts['projection']['source_inventory']) == 2


@pytest.mark.parametrize('change', ['value', 'origin', 'clock', 'source', 'limits'])
async def test_resealed_semantic_tampering_is_refused_without_repair(tmp_path, change):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    target = output(tmp_path)
    if change == 'value':
        rewrite(target, 'book_facts', lambda p:
            p['projection']['snapshots'][0]['components']['F08_snapshot'].update(numerator='9'))
    elif change == 'origin':
        rewrite(target, 'book_facts', lambda p: p.update(origin_admitted=True))
    elif change == 'clock':
        policy, _ = _pair(target, 'book_policy')
        rewrite(target, 'book_facts', lambda p: p.update(computed_at=policy['declared_at']))
    elif change == 'source':
        rewrite(target / CHILD, 'read_policy', lambda p:
            p.update(source_root=str(tmp_path / 'fs2_capture_different')))
    else:
        rewrite(target, 'book_policy', lambda p: p['limits'].update(max_output_bytes=2**40))
    before = snapshot(target)
    with pytest.raises(ValueError):
        read_book_computation(target)
    assert snapshot(target) == before


@pytest.mark.parametrize('name', ['book_policy_ack.json', 'read_facts_ack.json',
                                 'book_facts_ack.json'])
async def test_partial_acknowledgement_failures_are_preserved_and_terminal(
        tmp_path, monkeypatch, name):
    root, _ = await source(tmp_path)
    before, original = snapshot(root), Path.open
    def fail(path, *args, **kwargs):
        if path.name == name:
            raise OSError('synthetic write failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        record(root, tmp_path)
    monkeypatch.undo()
    assert (output(tmp_path) / 'book_failure_ack.json').exists()
    with pytest.raises(ValueError, match='closure'):
        read_book_computation(output(tmp_path))
    with pytest.raises(FileExistsError):
        record(root, tmp_path)
    assert snapshot(root) == before


async def test_cancellation_preserves_partial_input_read_and_raw(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    before, original = snapshot(root), module.record_input_read
    def cancel(*args, **kwargs):
        original(*args, **kwargs)
        raise asyncio.CancelledError()
    monkeypatch.setattr(module, 'record_input_read', cancel)
    with pytest.raises(asyncio.CancelledError):
        record(root, tmp_path)
    assert (output(tmp_path) / CHILD / 'read_facts_ack.json').exists()
    assert (output(tmp_path) / 'book_failure_ack.json').exists()
    assert snapshot(root) == before


async def test_concurrent_claim_has_one_winner(tmp_path):
    root, _ = await source(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(record, root, tmp_path) for _ in range(2)]
        successes, failures = [], []
        for future in futures:
            try:
                successes.append(future.result())
            except FileExistsError:
                failures.append(True)
    assert len(successes) == len(failures) == 1
    assert read_book_computation(output(tmp_path)) == successes[0]
    assert not (output(tmp_path) / 'book_failure.json').exists()


async def test_source_append_is_not_silently_ignored(tmp_path):
    root, run = await source(tmp_path)
    record(root, tmp_path)
    before = snapshot(output(tmp_path))
    await run.fetch('clob.book', {'token_id': '1'})
    with pytest.raises(ValueError, match='closure/projection'):
        read_book_computation(output(tmp_path))
    assert snapshot(output(tmp_path)) == before


async def test_transitive_paths_overrides_and_changed_build_refused(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    for target in (root, root / 'fs2_book_computation_nested'):
        with pytest.raises(ValueError, match='separate'):
            record_book_computation(root, output_root=target, policy=QuoteInputPolicy(60, 60))
    for key in ('clock', 'payload', 'origin_admitted', 'provenance'):
        with pytest.raises(TypeError):
            record_book_computation(root, output_root=output(tmp_path),
                                     policy=QuoteInputPolicy(60, 60), **{key: None})
    monkeypatch.setitem(_PACKAGE_FILES, 'book_computation.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        record(root, tmp_path)
    assert not output(tmp_path).exists()


async def test_storage_preflight_and_actual_computation_staleness(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    usage = module.shutil.disk_usage(root)
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda p:
                        usage._replace(free=LIMITS['free_reserve_bytes'] + 8 * 1048576))
    with pytest.raises(ValueError, match='storage reserve'):
        record(root, tmp_path)
    assert not output(tmp_path).exists()
    monkeypatch.undo()
    result = record(root, tmp_path, QuoteInputPolicy(0, 0))
    assert result['snapshot_states'] == {'identity_stale': 1}


def test_output_accounting_and_processing_deadline(tmp_path):
    target = output(tmp_path)
    child = target / CHILD
    child.mkdir(parents=True)
    (child / 'fixture').write_bytes(b'a' * 100)
    with pytest.raises(ValueError, match='total retained'):
        module._check(target, time.monotonic(), LIMITS['max_output_bytes'])
    with pytest.raises(ValueError, match='deadline'):
        module._check(target, time.monotonic() - 181)
    (child / 'link').symlink_to(child / 'fixture')
    with pytest.raises(ValueError, match='nested'):
        module._check(target, time.monotonic())
