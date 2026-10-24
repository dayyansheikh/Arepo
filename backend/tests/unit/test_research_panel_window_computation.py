"""Durable consumption and exact replay of received-window diagnostics."""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel import _PACKAGE_FILES
from astrolabe.research_panel import window_computation as module
from astrolabe.research_panel.window_capture import SyntheticWindowFeed, capture_window
from astrolabe.research_panel.window_computation import (
    read_window_computation,
    record_window_computation,
)
from astrolabe.research_panel.window_coverage import WindowCoveragePolicy
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_window_coverage import CONDITION, book, delta


async def source(tmp_path):
    root = tmp_path.resolve() / 'fs2_window_source'
    await capture_window(root, token_id='1', condition_id=CONDITION,
        feed=SyntheticWindowFeed(((0, json.dumps(book())), (20, json.dumps(delta())), (0, 'PONG'))),
        duration_ms=150)
    return root


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_window_computation_test'


def record(root, tmp_path):
    return record_window_computation(root, output_root=output(tmp_path),
                                     policy=WindowCoveragePolicy(1000))


async def test_actual_read_compute_save_clocks_and_immutable_exact_replay(tmp_path, monkeypatch):
    root = await source(tmp_path)
    before = snapshot(root)
    report = record(root, tmp_path)
    target = output(tmp_path)
    policy, pa = _pair(target, 'window_policy')
    inputs, ia = _pair(target, 'window_input')
    facts, fa = _pair(target, 'window_facts')
    assert _ordered_clocks(policy['declared_at'], pa['durable_ack'], inputs['read_started_at'],
        inputs['read_completed_at'], ia['durable_ack'], facts['computation_started_at'],
        facts['computed_at'], fa['durable_ack'])
    assert (inputs['source_summary']['window_available_at']['utc']
            <= inputs['read_started_at']['utc'])
    assert facts['projection']['items'][0]['snapshot']['F08_snapshot']['denominator'] == '3'
    assert report['source_provenance_class'] == 'synthetic'
    assert not report['origin_admitted'] and not report['feature_store_admitted']
    saved = snapshot(target)
    monkeypatch.setattr(module, '_clock', lambda: (_ for _ in ()).throw(
        AssertionError('new clock')))
    assert read_window_computation(target) == report
    assert snapshot(target) == saved and snapshot(root) == before
    with pytest.raises(FileExistsError):
        record(root, tmp_path)


@pytest.mark.parametrize('change', ['raw', 'source_append', 'projection', 'clock',
                                   'input', 'admission', 'limits'])
async def test_changed_inputs_or_resealed_semantics_fail_without_repair(tmp_path, change):
    root = await source(tmp_path)
    record(root, tmp_path)
    target = output(tmp_path)
    if change == 'raw':
        (root / 'event_000004.bin').write_bytes(b'changed')
    elif change == 'source_append':
        (root / 'extra.json').write_text('{}')
    elif change == 'projection':
        rewrite(target, 'window_facts', lambda p:
                p['projection'].update(reconstructed_receipt_duration_ns='0'))
    elif change == 'clock':
        policy, _ = _pair(target, 'window_policy')
        rewrite(target, 'window_facts', lambda p: p.update(computed_at=policy['declared_at']))
    elif change == 'input':
        rewrite(target, 'window_input', lambda p: p.update(input_manifest_hash='f' * 64))
    elif change == 'admission':
        rewrite(target, 'window_facts', lambda p: p.update(origin_admitted=True))
    else:
        rewrite(target, 'window_policy', lambda p: p['limits'].update(max_output_bytes=2**40))
    before = (snapshot(root), snapshot(target))
    with pytest.raises(ValueError):
        read_window_computation(target)
    assert before == (snapshot(root), snapshot(target))


@pytest.mark.parametrize('name', ['window_policy_ack.json', 'window_input_ack.json',
                                 'window_facts_ack.json'])
async def test_partial_acknowledgement_failures_remain_terminal(tmp_path, monkeypatch, name):
    root = await source(tmp_path)
    before, original = snapshot(root), Path.open
    def fail(path, *args, **kwargs):
        if path.parent == output(tmp_path) and path.name == name:
            raise OSError('synthetic write failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        record(root, tmp_path)
    monkeypatch.undo()
    assert (output(tmp_path) / 'window_failure_ack.json').exists()
    with pytest.raises(ValueError, match='closure'):
        read_window_computation(output(tmp_path))
    assert snapshot(root) == before
    with pytest.raises(FileExistsError):
        record(root, tmp_path)


async def test_cancelled_calculation_preserves_actual_completed_input_read(tmp_path, monkeypatch):
    root = await source(tmp_path)
    def cancel(*args, **kwargs):
        raise asyncio.CancelledError()
    monkeypatch.setattr(module, 'project_window_coverage', cancel)
    with pytest.raises(asyncio.CancelledError):
        record(root, tmp_path)
    assert (output(tmp_path) / 'window_input_ack.json').exists()
    assert (output(tmp_path) / 'window_failure_ack.json').exists()
    assert not (output(tmp_path) / 'window_facts.json').exists()


async def test_concurrent_creation_has_one_owner(tmp_path):
    root = await source(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(record, root, tmp_path) for _ in range(2)]
        wins = failures = 0
        for future in futures:
            try:
                future.result()
                wins += 1
            except FileExistsError:
                failures += 1
    assert wins == failures == 1
    assert not (output(tmp_path) / 'window_failure.json').exists()


async def test_path_and_clock_payload_overrides_and_changed_build_refused(tmp_path, monkeypatch):
    root = await source(tmp_path)
    for target in (root, root / 'fs2_window_computation_nested'):
        with pytest.raises(ValueError, match='separate'):
            record_window_computation(root, output_root=target, policy=WindowCoveragePolicy(1000))
    for key in ('clock', 'payload', 'provenance', 'cutoff'):
        with pytest.raises(TypeError):
            record_window_computation(root, output_root=output(tmp_path),
                                      policy=WindowCoveragePolicy(1000), **{key: None})
    monkeypatch.setitem(_PACKAGE_FILES, 'window_computation.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        record(root, tmp_path)
    assert not output(tmp_path).exists()


async def test_storage_reserve_refusal_and_finite_checks(tmp_path, monkeypatch):
    root = await source(tmp_path)
    disk = module.shutil.disk_usage(root)
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda p:
        disk._replace(free=module.LIMITS['free_reserve_bytes']))
    with pytest.raises(ValueError, match='storage reserve'):
        record(root, tmp_path)
    assert not output(tmp_path).exists()
    monkeypatch.undo()
    output(tmp_path).mkdir()
    with pytest.raises(ValueError, match='deadline'):
        module._check(output(tmp_path), time.monotonic() - 181)
    with pytest.raises(ValueError, match='retained'):
        module._check(output(tmp_path), time.monotonic(), module.LIMITS['max_output_bytes'])
    (output(tmp_path) / 'link').symlink_to(root / 'window_report.json')
    with pytest.raises(ValueError, match='invalid'):
        module._check(output(tmp_path), time.monotonic())
