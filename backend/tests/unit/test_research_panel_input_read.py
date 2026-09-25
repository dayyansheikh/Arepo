"""Synthetic actual-read journals; no live collection, SQL or origin admission."""

import base64
import json
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store.capture import _digest, _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import SourceRun, _pair, read_source_run
from astrolabe.research_panel import _PACKAGE_FILES, input_read
from astrolabe.research_panel.input_read import read_input_read, record_input_read
from tests.unit.test_feature_store_source_bridge import BODY, captured
from tests.unit.test_feature_store_source_run import mock_transport


async def source(tmp_path, status=200):
    root = tmp_path.resolve() / 'fs2_capture_inputs'
    run = SourceRun(root, transport=mock_transport(root, status=status))
    await run.fetch('clob.book', {'token_id': '1'})
    return root, run


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_input_read_test'


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def rewrite(root, name, mutate):
    path = root / (name + '.json')
    payload = json.loads(path.read_bytes())
    mutate(payload)
    path.write_bytes(_json_bytes(payload))
    ack = root / (name + '_ack.json')
    receipt = json.loads(ack.read_bytes())
    receipt['payload_hash'] = _digest(path.read_bytes())
    ack.write_bytes(_json_bytes(receipt))


@pytest.mark.asyncio
async def test_actual_reads_preserve_source_bytes_clocks_exact_numbers_and_provenance(tmp_path):
    root, _ = await source(tmp_path)
    before = snapshot(root)
    result = record_input_read(root, output_root=output(tmp_path))
    facts, ack = _pair(output(tmp_path), 'read_facts')
    policy, policy_ack = _pair(output(tmp_path), 'read_policy')
    assert (_time(policy['declared_at']) <= _time(policy_ack['durable_ack'])
            <= _time(facts['read_started_at']) <= _time(facts['projection_completed_at'])
            <= _time(ack['durable_ack']))
    expected = read_source_run(root)
    assert _json_bytes(facts['source_projection']['rows']) == _json_bytes(expected)
    observation = next(r for kind, r in expected if kind == 'source_observation')
    assert observation['available_to_model_at'] <= _time(result['read_started_at'])
    assert base64.b64decode(observation['raw_payload_inline']) == BODY
    assert result['source_provenance_class'] == 'synthetic'
    assert result['origin_admitted'] is result['source_clocks_changed'] is False
    read_before = snapshot(output(tmp_path))
    assert read_input_read(output(tmp_path)) == result
    assert snapshot(root) == before and snapshot(output(tmp_path)) == read_before
    with pytest.raises(FileExistsError):
        record_input_read(root, output_root=output(tmp_path))
    assert snapshot(output(tmp_path)) == read_before


@pytest.mark.asyncio
async def test_failed_source_responses_are_preserved_as_missing_not_dropped(tmp_path):
    root, _ = await source(tmp_path, status=429)
    result = record_input_read(root, output_root=output(tmp_path))
    facts, _ = _pair(output(tmp_path), 'read_facts')
    obs = [r for k, r in facts['source_projection']['rows'] if k == 'source_observation']
    assert result['observation_count'] == 1
    assert obs[0]['missing_reason'] == 'rate_limited'


@pytest.mark.asyncio
async def test_source_appends_invalidate_completed_run_read_without_rewriting_history(tmp_path):
    root, run = await source(tmp_path)
    record_input_read(root, output_root=output(tmp_path))
    before = snapshot(output(tmp_path))
    await run.fetch('clob.book', {'token_id': '1'})
    with pytest.raises(ValueError, match='closure/projection differs'):
        read_input_read(output(tmp_path))
    assert snapshot(output(tmp_path)) == before


@pytest.mark.asyncio
async def test_source_raw_corruption_is_not_hidden_by_retained_projection(tmp_path):
    root, _ = await source(tmp_path)
    record_input_read(root, output_root=output(tmp_path))
    raw = next(root.glob('*/raw.bin'))
    raw.write_bytes(b'corrupted synthetic fixture')
    with pytest.raises(ValueError):
        read_input_read(output(tmp_path))


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [
    {'origin_admitted': True}, {'source_clocks_changed': True},
    {'projection_hash': '0' * 64}, {'policy_hash': '0' * 64},
    {'read_started_at': {'utc': '2000-01-01T00:00:00Z',
                         'monotonic_ns': '1', 'clock_session_id': 'fixture'}},
])
async def test_rehashed_false_read_facts_are_refused(tmp_path, changes):
    root, _ = await source(tmp_path)
    record_input_read(root, output_root=output(tmp_path))
    rewrite(output(tmp_path), 'read_facts', lambda payload: payload.update(changes))
    with pytest.raises(ValueError):
        read_input_read(output(tmp_path))


@pytest.mark.asyncio
async def test_false_source_closure_refused_even_when_rehashed(tmp_path):
    from astrolabe.feature_store.admission import content_hash

    root, _ = await source(tmp_path)
    record_input_read(root, output_root=output(tmp_path))

    def mutate(payload):
        payload['source_projection']['rows'].pop()
        payload['projection_hash'] = content_hash(payload['source_projection'])

    rewrite(output(tmp_path), 'read_facts', mutate)
    with pytest.raises(ValueError, match='closure/projection'):
        read_input_read(output(tmp_path))


@pytest.mark.asyncio
async def test_missing_ack_extra_file_and_changed_build_refuse_recovery(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    record_input_read(root, output_root=output(tmp_path))
    monkeypatch.setitem(_PACKAGE_FILES, 'input_read.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        read_input_read(output(tmp_path))
    monkeypatch.undo()
    (output(tmp_path) / 'unexpected.json').write_text('{}')
    with pytest.raises(ValueError, match='closure'):
        read_input_read(output(tmp_path))


@pytest.mark.asyncio
async def test_torn_ack_is_retained_and_cannot_be_resumed(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    before = snapshot(root)
    original = Path.open

    def fail(path, *args, **kwargs):
        if path.name == 'read_facts_ack.json':
            raise OSError('synthetic disk failure')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        record_input_read(root, output_root=output(tmp_path))
    monkeypatch.undo()
    assert (output(tmp_path) / 'read_facts.json').exists()
    assert (output(tmp_path) / 'read_failure_ack.json').exists()
    with pytest.raises(ValueError, match='closure'):
        read_input_read(output(tmp_path))
    with pytest.raises(FileExistsError):
        record_input_read(root, output_root=output(tmp_path))
    assert snapshot(root) == before


@pytest.mark.asyncio
async def test_paths_cannot_modify_source_or_hide_symlinks(tmp_path):
    root, _ = await source(tmp_path)
    before = snapshot(root)
    for target in (root, root / 'fs2_input_read_nested'):
        with pytest.raises(ValueError, match='separate'):
            record_input_read(root, output_root=target)
    alias = tmp_path / 'source_alias'
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match='canonical'):
        record_input_read(alias, output_root=output(tmp_path))
    assert snapshot(root) == before


@pytest.mark.asyncio
async def test_empty_and_diagnostic_source_cannot_be_adopted(tmp_path):
    root = tmp_path.resolve() / 'fs2_capture_empty'
    SourceRun(root, transport=httpx.MockTransport(lambda r: httpx.Response(200, content=BODY)))
    with pytest.raises(ValueError, match='nonempty'):
        record_input_read(root, output_root=output(tmp_path))
    diagnostic = await captured(tmp_path)
    with pytest.raises(FileNotFoundError):
        record_input_read(Path(diagnostic['folder']).parent,
                          output_root=tmp_path.resolve() / 'fs2_input_read_diagnostic')


@pytest.mark.asyncio
async def test_no_payload_clock_provenance_or_subset_override(tmp_path):
    root, _ = await source(tmp_path)
    for args in ({'payload': {}}, {'clock': {}}, {'provenance': 'prospective'},
                 {'capture_id': 'one'}):
        with pytest.raises(TypeError):
            record_input_read(root, output_root=output(tmp_path), **args)
    assert not output(tmp_path).exists()


@pytest.mark.asyncio
async def test_actual_read_clock_cannot_precede_source_availability(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    old_clock = {'utc': '2000-01-01T00:00:00Z', 'clock_session_id': 'old', 'monotonic_ns': '1'}
    monkeypatch.setattr(input_read, '_clock', lambda: old_clock)
    with pytest.raises(ValueError, match='unavailable when actual input read began'):
        record_input_read(root, output_root=output(tmp_path))
    assert (output(tmp_path) / 'read_failure_ack.json').exists()


@pytest.mark.asyncio
async def test_monotonic_regression_refused_even_with_valid_utc(tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    original = input_read._clock
    monkeypatch.setattr(input_read, '_clock', lambda: {**original(), 'monotonic_ns': '0'})
    with pytest.raises(ValueError, match='unavailable when actual input read began'):
        record_input_read(root, output_root=output(tmp_path))


@pytest.mark.asyncio
async def test_missing_source_ack_and_read_ack_are_never_reconstructed(tmp_path):
    root, _ = await source(tmp_path)
    record_input_read(root, output_root=output(tmp_path))
    ack = output(tmp_path) / 'read_facts_ack.json'
    ack.unlink()  # synthetic fixture corruption only
    with pytest.raises(ValueError, match='closure'):
        read_input_read(output(tmp_path))
    assert not ack.exists()
    next(root.glob('*/admission_ack.json')).unlink()
    with pytest.raises(FileNotFoundError):
        record_input_read(root, output_root=tmp_path.resolve() / 'fs2_input_read_torn_source')


@pytest.mark.asyncio
async def test_disk_preflight_is_before_any_output(tmp_path, monkeypatch):
    from collections import namedtuple

    root, _ = await source(tmp_path)
    usage = namedtuple('usage', 'total used free')
    monkeypatch.setattr(input_read.shutil, 'disk_usage', lambda p: usage(1, 1, 0))
    with pytest.raises(ValueError, match='storage reserve'):
        record_input_read(root, output_root=output(tmp_path))
    assert not output(tmp_path).exists()


def test_processing_and_output_budgets_refuse_without_mutation(tmp_path):
    import time

    root = output(tmp_path)
    root.mkdir()
    with pytest.raises(ValueError, match='deadline'):
        input_read._check(root, time.monotonic() - 61)
    with pytest.raises(ValueError, match='byte budget'):
        input_read._check(root, time.monotonic(), 32 * 1048576)
    with pytest.raises(ValueError, match='artefact'):
        input_read._save(root, 'large', {'value': 'a' * (16 * 1048576)}, time.monotonic())
    assert list(root.iterdir()) == []
