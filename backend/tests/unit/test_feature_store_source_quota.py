"""Finite source retention writes preserve raw evidence and keep async quotas isolated."""

import asyncio
import base64
import json
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from astrolabe.feature_store import source_quota
from astrolabe.feature_store.admission import AdmissionError
from astrolabe.feature_store.capture import Budget, _json_bytes, _write_once
from astrolabe.feature_store.repository import index_source_run
from astrolabe.feature_store.source_quota import (
    MIB,
    SourceQuotaExceeded,
    quota_policy,
    retained_size,
    retention_scope,
)
from astrolabe.feature_store.source_run import (
    TARGETED_POLICY,
    SourceRun,
    _pair,
    read_source_run,
)
from astrolabe.research_panel.quote_computation import record_quote_computation
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from tests.unit.test_feature_store_targeted_market import market
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_quote_inputs import CONDITION, book


def transport(value=None, requests=None):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(0)
            yield _json_bytes(market() if value is None else value)
    def handler(request):
        if requests is not None:
            requests.append(request.url.path)
        return httpx.Response(200, stream=Stream())
    return httpx.MockTransport(handler)


def run(tmp_path, *, quota=2 * MIB, value=None, requests=None, budget=None, name='test'):
    return SourceRun(tmp_path / ('fs2_capture_' + name), transport=transport(value, requests),
                     retained_bytes=quota, policy_version=TARGETED_POLICY['version'],
                     budget=budget or Budget())


async def fetch(source):
    return await source.fetch('gamma.market', {'market_id': '123'})


@pytest.mark.parametrize('limit', [True, 0, MIB - 1, 256 * MIB + 1, '1048576', 1048576.0])
def test_invalid_quota_refused_before_creating_output(tmp_path, limit):
    with pytest.raises(ValueError):
        run(tmp_path, quota=limit)
    assert not list(tmp_path.iterdir())


async def test_guarded_full_source_read_computation_and_default_compatibility(tmp_path):
    source = run(tmp_path)
    rows = await fetch(source)
    root = source.journal.root
    declaration, _ = _pair(root, 'run')
    assert declaration['schema_version'] == 'fs2-source-run-v2'
    assert declaration['retention_quota'] == quota_policy(2 * MIB)
    assert any(kind == 'source_observation' for kind, _ in rows)
    before = snapshot(root)
    assert read_source_run(root) == rows
    result = record_quote_computation(root,
        output_root=tmp_path / 'fs2_quote_computation_quota', policy=QuoteInputPolicy(60, 60))
    assert result['source_provenance_class'] == 'synthetic'
    assert result['source_observation_count'] == 1
    assert snapshot(root) == before
    old = run(tmp_path, quota=None, name='old_default')
    await fetch(old)
    old_decl, _ = _pair(old.journal.root, 'run')
    assert old_decl['schema_version'] == 'fs2-source-run-v1'
    assert 'retention_quota' not in old_decl


async def test_raw_capacity_is_reserved_before_network_and_failure_is_terminal(tmp_path):
    requests = []
    source = run(tmp_path, quota=MIB, requests=requests,
                 budget=Budget(bytes_per_response=MIB, total_bytes=MIB))
    root = source.journal.root
    before = snapshot(root)
    with pytest.raises(SourceQuotaExceeded, match='before request'):
        await fetch(source)
    assert requests == []
    assert all(snapshot(root)[k] == v for k, v in before.items())
    assert (root / 'run_failure_ack.json').exists()
    assert retained_size(root, quota_policy(MIB)) <= MIB
    with pytest.raises(ValueError, match='terminal'):
        await fetch(source)
    with pytest.raises(ValueError, match='terminal'):
        read_source_run(root)


@pytest.mark.parametrize('description_size,parsed_exists', [(340000, True), (550000, False)])
async def test_parse_quota_stop_retains_exact_received_raw_before_failure(
        tmp_path, description_size, parsed_exists):
    body = market(description='x' * description_size)
    source = run(tmp_path, quota=MIB, value=body,
                 budget=Budget(bytes_per_response=600000, total_bytes=600000))
    with pytest.raises(SourceQuotaExceeded, match='quota would be exceeded'):
        await fetch(source)
    root = source.journal.root
    raw = next(root.glob('*/raw.bin'))
    assert raw.read_bytes() == _json_bytes(body)
    assert (raw.parent / 'raw_ack.json').exists()
    assert (raw.parent / 'parsed_ack.json').exists() == parsed_exists
    assert (root / 'run_failure_ack.json').exists()
    assert retained_size(root, quota_policy(MIB)) <= MIB
    before = snapshot(root)
    with pytest.raises(ValueError, match='terminal'):
        read_source_run(root)
    assert before == snapshot(root)


async def test_quota_guard_is_task_local_for_interleaved_runs(tmp_path):
    first = run(tmp_path, name='first')
    second = run(tmp_path, name='second', quota=3 * MIB)
    a, b = await asyncio.gather(fetch(first), fetch(second))
    assert a and b
    assert retained_size(first.journal.root, quota_policy(2 * MIB)) < 2 * MIB
    assert retained_size(second.journal.root, quota_policy(3 * MIB)) < 3 * MIB
    # The scope is reset in the caller, so unrelated exclusive writes keep their old behavior.
    _write_once(tmp_path / 'unrelated', b'outside any active quota')


def test_guard_rejects_outside_symlink_depth_and_file_overflow_before_writes(tmp_path):
    root = tmp_path / 'fs2_capture_guard'
    root.mkdir()
    policy = quota_policy(MIB)
    with retention_scope(root, policy):
        with pytest.raises(SourceQuotaExceeded, match='outside'):
            _write_once(tmp_path / 'outside', b'x')
        deep = root / 'a' / 'b' / 'c'
        deep.mkdir(parents=True)
        with pytest.raises(SourceQuotaExceeded, match='depth'):
            _write_once(deep / 'file', b'x')
    # Separate fixture tree: malformed evidence is retained, not repaired for this test.
    other = tmp_path / 'fs2_capture_files'
    other.mkdir()
    for index in range(126):
        (other / str(index)).write_bytes(b'x')
    with retention_scope(other, policy):
        with pytest.raises(SourceQuotaExceeded, match='file count'):
            _write_once(other / 'overflow', b'x')
    assert not (other / 'overflow').exists()
    (other / 'link').symlink_to(tmp_path / 'missing')
    with pytest.raises(SourceQuotaExceeded, match='symlink'):
        retained_size(other, policy)


def test_failure_reserve_allows_only_bounded_evidence_and_resets_after_error(tmp_path):
    root = tmp_path / 'fs2_capture_failure'
    root.mkdir()
    policy = quota_policy(MIB)
    with retention_scope(root, policy):
        _write_once(root / 'full', b'x' * (MIB - 65536))
        with pytest.raises(SourceQuotaExceeded):
            _write_once(root / 'extra', b'x')
    with retention_scope(root, policy, failure=True):
        _write_once(root / 'failure', b'failure facts')
        with pytest.raises(SourceQuotaExceeded, match='reserved artefact'):
            _write_once(root / 'too_large_failure', b'x' * 32769)
    assert retained_size(root, policy) <= MIB
    with retention_scope(root, policy):
        with pytest.raises(ValueError, match='nested'):
            with retention_scope(root, policy):
                pytest.fail('nested scope must refuse')


@pytest.mark.parametrize('change', ['quota', 'schema', 'overflow', 'symlink'])
async def test_read_rejects_policy_or_actual_usage_corruption_without_repair(tmp_path, change):
    source = run(tmp_path)
    await fetch(source)
    root = source.journal.root
    if change == 'quota':
        rewrite(root, 'run', lambda p: p['retention_quota'].update(failure_reserve_bytes=0))
    elif change == 'schema':
        rewrite(root, 'run', lambda p: p.update(schema_version='fs2-source-run-v1'))
    elif change == 'overflow':
        (root / 'unaccounted.bin').write_bytes(b'x' * (2 * MIB))
    else:
        (root / 'link').symlink_to(tmp_path / 'missing')
    with pytest.raises(ValueError):
        read_source_run(root)


def test_disk_preflight_and_existing_root_never_add_failure_to_another_run(tmp_path, monkeypatch):
    source = run(tmp_path)
    root = source.journal.root
    before = snapshot(root)
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert snapshot(root) == before
    usage = namedtuple('Usage', 'total used free')
    monkeypatch.setattr(source_quota.shutil, 'disk_usage', lambda p: usage(2**32, 0, 1))
    with pytest.raises(ValueError, match='insufficient'):
        run(tmp_path, name='low_disk')
    assert not (tmp_path / 'fs2_capture_low_disk').exists()


async def test_low_disk_during_admission_preserves_all_prior_source_records(tmp_path, monkeypatch):
    source = run(tmp_path)
    root = source.journal.root
    original = source_quota.shutil.disk_usage
    usage = namedtuple('Usage', 'total used free')
    refused = []
    def disk(path):
        if not refused and list(root.glob('*/source_parse_*/ack.json')):
            refused.append(True)
            return usage(2**32, 0, 1)
        return original(path)
    monkeypatch.setattr(source_quota.shutil, 'disk_usage', disk)
    with pytest.raises(SourceQuotaExceeded, match='free-space'):
        await fetch(source)
    assert list(root.glob('*/source_parse_*/ack.json'))
    assert not list(root.glob('*/admission.json'))
    failure, _ = _pair(root, 'run_failure')
    assert failure['exception_type'] == 'SourceQuotaExceeded'
    assert not source_quota._ACTIVE.get()


async def test_failed_http_response_is_preserved_within_quota_not_a_guard_failure(tmp_path):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"error":"synthetic rate limit"}'
    source = SourceRun(tmp_path / 'fs2_capture_http_error', retained_bytes=MIB,
        policy_version=TARGETED_POLICY['version'],
        transport=httpx.MockTransport(lambda r: httpx.Response(429, stream=Stream())))
    rows = await fetch(source)
    observation = next(r for k, r in rows if k == 'source_observation')
    assert observation['missing_reason'] == 'rate_limited'
    assert not (source.journal.root / 'run_failure.json').exists()
    assert json.loads((source.journal.root / 'run.json').read_bytes())['retention_quota']


def test_constructor_write_failure_preserves_attempt_and_refuses_reuse(tmp_path, monkeypatch):
    original = source_quota.shutil.disk_usage
    usage = namedtuple('Usage', 'total used free')
    root = tmp_path / 'fs2_capture_test'
    refused = []
    def disk(path):
        if root.is_dir() and not refused:
            refused.append(True)
            return usage(2**32, 0, 1)
        return original(path)
    monkeypatch.setattr(source_quota.shutil, 'disk_usage', disk)
    with pytest.raises(SourceQuotaExceeded):
        run(tmp_path)
    assert not (root / 'session.json').exists()
    assert (root / 'run_failure_ack.json').exists()
    before = snapshot(root)
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert snapshot(root) == before


def test_guarded_source_constructor_collision_cannot_mark_winner_failed(tmp_path):
    def attempt():
        try:
            return run(tmp_path)
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(lambda _: attempt(), range(2)))
    winners = [source for source in runs if source is not None]
    assert len(winners) == 1
    root = winners[0].journal.root
    assert not (root / 'run_failure.json').exists()
    assert read_source_run(root)


async def test_guarded_identity_book_trade_chain_preserves_all_primitives(tmp_path):
    class Stream(httpx.AsyncByteStream):
        def __init__(self, value):
            self.value = value
        async def __aiter__(self):
            yield _json_bytes(self.value)
    fixtures = {'/markets/123': market(),
                '/book': json.loads(base64.b64decode(book()['raw_payload_inline'])),
                '/v2/trades': {'data': [], 'pagination': {'has_more': False, 'next_cursor': None}}}
    source = SourceRun(tmp_path / 'fs2_capture_full', retained_bytes=4 * MIB,
        policy_version=TARGETED_POLICY['version'],
        transport=httpx.MockTransport(lambda r: httpx.Response(200,
                                      stream=Stream(fixtures[r.url.path]))))
    await fetch(source)
    await source.fetch('clob.book', {'token_id': '1'})
    await source.fetch('data.v2.trades', {'condition': CONDITION, 'limit': 1, 'taker_only': 'true'})
    result = record_quote_computation(source.journal.root,
        output_root=tmp_path / 'fs2_quote_computation_full', policy=QuoteInputPolicy(60, 60))
    assert result['quote_states'] == {'observed': 1}
    assert result['source_observation_count'] == 3
    assert result['origin_admitted'] is False


async def test_guarded_sources_do_not_allow_unbudgeted_index_receipts(tmp_path):
    source = run(tmp_path)
    await fetch(source)
    before = snapshot(source.journal.root)
    db = tmp_path / 'fs2_test_not_created.sqlite'
    with pytest.raises(AdmissionError, match='journal-only'):
        await index_source_run('sqlite+aiosqlite:///' + str(db), source.journal.root)
    assert not db.exists()
    assert snapshot(source.journal.root) == before
