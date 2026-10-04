"""Synthetic durable quote computations; no live sources, database or origin admission."""

import base64
import time
from collections import namedtuple
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import SourceRun, _ordered_clocks, _pair
from astrolabe.research_panel import _PACKAGE_FILES, quote_computation
from astrolabe.research_panel.quote_computation import (
    CHILD,
    LIMITS,
    read_quote_computation,
    record_quote_computation,
)
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_quote_inputs import book, gamma


async def source(tmp_path, *, gamma_status=200, book_status=200, late_identity=False):
    class Stream(httpx.AsyncByteStream):
        def __init__(self, raw):
            self.raw = raw

        async def __aiter__(self):
            yield self.raw

    def handler(request):
        is_gamma = request.url.path == '/markets'
        fixture = gamma() if is_gamma else book()
        return httpx.Response(gamma_status if is_gamma else book_status,
                              stream=Stream(base64.b64decode(fixture['raw_payload_inline'])))

    root = tmp_path.resolve() / 'fs2_capture_quote_computation'
    run = SourceRun(root, transport=httpx.MockTransport(handler))
    calls = [('gamma.markets', {'limit': 1, 'active': 'true', 'closed': 'false'}),
             ('clob.book', {'token_id': '1'})]
    for source_id, params in reversed(calls) if late_identity else calls:
        await run.fetch(source_id, params)
    return root, run


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_quote_computation_test'


def record(root, tmp_path, policy=None):
    return record_quote_computation(root, output_root=output(tmp_path),
                                    policy=policy or QuoteInputPolicy(60, 60))


@pytest.mark.asyncio
async def test_complete_source_read_compute_durable_chain_and_exact_replay(tmp_path):
    root, _ = await source(tmp_path)
    before = snapshot(root)
    report = record(root, tmp_path)
    target = output(tmp_path)
    policy, policy_ack = _pair(target, 'quote_policy')
    child_policy, child_ack = _pair(target / CHILD, 'read_policy')
    facts, ack = _pair(target, 'quote_facts')
    assert _ordered_clocks(policy['declared_at'], policy_ack['durable_ack'],
                           child_policy['declared_at'], child_ack['durable_ack'],
                           facts['input_read']['read_started_at'],
                           facts['input_read']['read_available_at'],
                           facts['computation_started_at'], facts['computed_at'],
                           ack['durable_ack'])
    quote = facts['projection']['quotes'][0]
    assert (quote['bid'], quote['ask'], quote['midpoint']) == ('0.400', '0.600', '0.500')
    assert report['quote_states'] == {'observed': 1}
    assert report['source_provenance_class'] == 'synthetic'
    assert report['source_observation_count'] == 2
    assert report['origin_admitted'] is report['feature_store_admitted'] is False
    assert 'source_projection' not in report  # compact summary never leaks raw source fields
    recorded = snapshot(target)
    assert read_quote_computation(target) == report
    assert snapshot(root) == before and snapshot(target) == recorded
    with pytest.raises(FileExistsError):
        record(root, tmp_path)
    assert snapshot(target) == recorded


@pytest.mark.asyncio
@pytest.mark.parametrize('kwargs,state', [
    ({'gamma_status': 503}, 'identity_unresolved_at_receipt'),
    ({'book_status': 429}, 'rate_limited'),
    ({'late_identity': True}, 'identity_unresolved_at_receipt'),
])
async def test_failed_or_late_identity_preserves_all_input_observations(tmp_path, kwargs, state):
    root, _ = await source(tmp_path, **kwargs)
    result = record(root, tmp_path)
    assert result['source_observation_count'] == 2
    assert result['quote_states'] == {state: 1}
    facts, _ = _pair(output(tmp_path), 'quote_facts')
    assert facts['projection']['quotes'][0]['midpoint'] is None


@pytest.mark.asyncio
async def test_zero_age_is_stale_and_replay_uses_original_computation_cutoff(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    result = record(root, tmp_path, QuoteInputPolicy(0, 0))
    assert result['quote_states'] == {'identity_stale': 1}
    monkeypatch.setattr(quote_computation, '_clock', lambda: (_ for _ in ()).throw(
        AssertionError('replay must not stamp or use a new computation cutoff')))
    assert read_quote_computation(output(tmp_path)) == result


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [
    {'origin_admitted': True}, {'feature_store_admitted': True}, {'policy_hash': '0' * 64},
    {'computed_at': {'utc': '2000-01-01T00:00:00Z', 'monotonic_ns': '0',
                     'clock_session_id': 'fixture'}},
])
async def test_rehashed_false_computation_clocks_and_claims_refused(tmp_path, changes):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    rewrite(output(tmp_path), 'quote_facts', lambda p: p.update(changes))
    with pytest.raises(ValueError, match='chronology/input lineage'):
        read_quote_computation(output(tmp_path))


@pytest.mark.asyncio
async def test_rehashed_wrong_midpoint_refused(tmp_path):
    root, _ = await source(tmp_path)
    record(root, tmp_path)

    def corrupt(p):
        p['projection']['quotes'][0]['midpoint'] = '0.9'

    rewrite(output(tmp_path), 'quote_facts', corrupt)
    with pytest.raises(ValueError, match='exact replay'):
        read_quote_computation(output(tmp_path))


@pytest.mark.asyncio
async def test_appended_source_or_torn_child_invalidates_parent_without_repair(tmp_path):
    root, run = await source(tmp_path)
    record(root, tmp_path)
    before = snapshot(output(tmp_path))
    await run.fetch('clob.book', {'token_id': '1'})
    with pytest.raises(ValueError, match='closure/projection'):
        read_quote_computation(output(tmp_path))
    assert snapshot(output(tmp_path)) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['quote_policy_ack.json', 'read_facts_ack.json',
                                 'quote_facts_ack.json'])
async def test_crash_preserves_partial_files_without_resume(tmp_path, monkeypatch, name):
    root, _ = await source(tmp_path)
    before, original = snapshot(root), Path.open

    def fail(path, *args, **kwargs):
        if path.name == name:
            raise OSError('synthetic acknowledgement failure')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        record(root, tmp_path)
    monkeypatch.undo()
    assert (output(tmp_path) / 'quote_failure_ack.json').exists()
    with pytest.raises(ValueError, match='closure'):
        read_quote_computation(output(tmp_path))
    with pytest.raises(FileExistsError):
        record(root, tmp_path)
    assert snapshot(root) == before


@pytest.mark.asyncio
async def test_clock_regression_and_changed_build_refuse_admission(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    original = quote_computation._clock
    monkeypatch.setattr(quote_computation, '_clock', lambda: {**original(), 'monotonic_ns': '0'})
    with pytest.raises(ValueError, match='chronology regressed'):
        record(root, tmp_path)
    assert (output(tmp_path) / 'quote_failure_ack.json').exists()
    monkeypatch.undo()
    monkeypatch.setitem(_PACKAGE_FILES, 'quote_computation.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        record_quote_computation(root, output_root=tmp_path / 'fs2_quote_computation_changed',
                                 policy=QuoteInputPolicy(60, 60))


@pytest.mark.asyncio
async def test_transitive_paths_and_injected_caller_inputs_refused(tmp_path):
    root, _ = await source(tmp_path)
    for target in (root, root / 'fs2_quote_computation_nested'):
        with pytest.raises(ValueError, match='separate'):
            record_quote_computation(root, output_root=target, policy=QuoteInputPolicy(60, 60))
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match='canonical'):
        record_quote_computation(alias, output_root=output(tmp_path),
                                 policy=QuoteInputPolicy(60, 60))
    for override in ('payload', 'clock', 'provenance', 'capture_id', 'origin_admitted'):
        with pytest.raises(TypeError):
            record_quote_computation(root, output_root=output(tmp_path),
                                     policy=QuoteInputPolicy(60, 60), **{override: None})
    assert not output(tmp_path).exists()


@pytest.mark.asyncio
async def test_parent_storage_preflight_includes_child_plus_parent(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    usage = namedtuple('usage', 'total used free')
    free = LIMITS['free_reserve_bytes'] + 48 * 1048576  # enough for child, not full parent
    monkeypatch.setattr(quote_computation.shutil, 'disk_usage', lambda p: usage(free, 0, free))
    with pytest.raises(ValueError, match='storage reserve'):
        record(root, tmp_path)
    assert not output(tmp_path).exists()


def test_recursive_budget_counts_child_and_refuses_symlinks_depth_and_deadlines(tmp_path):
    root = output(tmp_path)
    child = root / CHILD
    child.mkdir(parents=True)
    (root / 'policy.json').write_bytes(b'a' * 20)
    (child / 'facts.json').write_bytes(b'b' * 30)
    assert quote_computation._size(root) == 50
    with pytest.raises(ValueError, match='total retained'):
        quote_computation._check(root, time.monotonic(), LIMITS['max_output_bytes'] - 65550)
    with pytest.raises(ValueError, match='deadline'):
        quote_computation._check(root, time.monotonic() - 181)
    alias = child / 'alias'
    alias.symlink_to(root / 'policy.json')
    with pytest.raises(ValueError, match='nested'):
        quote_computation._size(root)
    alias.unlink()  # disposable synthetic fixture only
    (child / 'deep').mkdir()
    with pytest.raises(ValueError, match='nested'):
        quote_computation._size(root)


@pytest.mark.asyncio
async def test_parent_policy_must_precede_child_declaration(tmp_path):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    facts, _ = _pair(output(tmp_path), 'quote_facts')
    later = facts['computed_at']
    rewrite(output(tmp_path), 'quote_policy', lambda p: p.update(declared_at=later))
    with pytest.raises(ValueError, match='child lineage/declaration'):
        read_quote_computation(output(tmp_path))


@pytest.mark.asyncio
async def test_read_only_clock_and_canonical_projection_preservation(tmp_path):
    root, _ = await source(tmp_path)
    result = record(root, tmp_path)
    facts, _ = _pair(output(tmp_path), 'quote_facts')
    assert facts['projection']['cutoff'] == {'$utc': result['computation_started_at']['utc']}
    assert _time(result['computed_at']) <= _time(result['computation_available_at'])
    assert _json_bytes(read_quote_computation(output(tmp_path))) == _json_bytes(result)


@pytest.mark.asyncio
async def test_concurrent_output_claim_has_one_winner_and_no_failure_marker(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    root, _ = await source(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(record, root, tmp_path) for _ in range(2)]
        successes, failures = [], []
        for future in futures:
            try:
                successes.append(future.result())
            except FileExistsError as exc:
                failures.append(exc)
    assert len(successes) == len(failures) == 1
    assert read_quote_computation(output(tmp_path)) == successes[0]
    assert not (output(tmp_path) / 'quote_failure.json').exists()


@pytest.mark.asyncio
async def test_child_source_rebinding_refused_before_consumption(tmp_path):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    rewrite(output(tmp_path) / CHILD, 'read_policy',
            lambda p: p.update(source_root=str(tmp_path / 'fs2_capture_other')))
    with pytest.raises(ValueError, match='child lineage/declaration'):
        read_quote_computation(output(tmp_path))
