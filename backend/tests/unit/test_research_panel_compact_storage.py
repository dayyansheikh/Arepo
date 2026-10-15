"""Explicit smaller quotas, exact replay, and no evidence truncation or default changes."""

import base64
import shutil
import time

import httpx
import pytest

from astrolabe.feature_store.capture import Budget, _json_bytes
from astrolabe.feature_store.source_run import TARGETED_POLICY, SourceRun, _pair
from astrolabe.research_panel import input_read, quote_computation
from astrolabe.research_panel.input_read import read_input_read, record_input_read
from astrolabe.research_panel.original_reader import read_original_quote_computation
from astrolabe.research_panel.panel_declaration import (
    declare_panel,
    read_panel_declaration,
    reservation,
)
from astrolabe.research_panel.panel_selection import create_panel_selection, selection_root
from astrolabe.research_panel.quote_computation import (
    CHILD,
    read_quote_computation,
    record_quote_computation,
)
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.selection import read_selection
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_feature_store_source_quota import fetch, run
from tests.unit.test_feature_store_targeted_market import market
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_quote_computation import source
from tests.unit.test_research_panel_quote_inputs import CONDITION, book
from tests.unit.test_research_panel_selection import frame

original_code = _original_code
MIB = 1048576
PROFILE = 'compact-v1'


def compute(tmp_path, source_root, **changes):
    return record_quote_computation(source_root,
        output_root=tmp_path / 'fs2_quote_computation_compact', policy=QuoteInputPolicy(60, 60),
        storage_profile=PROFILE, **changes)


async def test_guarded_three_source_chain_exact_compact_replay(tmp_path):
    def handler(request):
        data = (_json_bytes(market()) if request.url.path.startswith('/markets/') else
                base64.b64decode(book()['raw_payload_inline']) if request.url.path == '/book'
                else b'{"data": [], "pagination": {"has_more": false, "next_cursor": null}}')
        return httpx.Response(200, stream=Stream([data]))
    root = tmp_path / 'fs2_capture_compact'
    source_run = SourceRun(root, transport=httpx.MockTransport(handler), retained_bytes=MIB,
        policy_version=TARGETED_POLICY['version'],
        budget=Budget(requests=3, bytes_per_response=65536, total_bytes=3 * 65536))
    await source_run.fetch('gamma.market', {'market_id': '123'})
    await source_run.fetch('clob.book', {'token_id': '1'})
    await source_run.fetch('data.v2.trades', {'limit': 1, 'condition': CONDITION,
                                           'taker_only': 'true'})
    before = snapshot(root)
    result = compute(tmp_path, root)
    output = tmp_path / 'fs2_quote_computation_compact'
    policy, _ = _pair(output, 'quote_policy')
    child, _ = _pair(output / CHILD, 'read_policy')
    assert policy['schema_version'] == 'fs2-quote-computation-v2'
    assert child['schema_version'] == 'fs2-panel-input-read-v2'
    assert policy['limits']['max_output_bytes'] == 8 * MIB
    assert child['policy']['max_output_bytes'] == 4 * MIB
    assert policy['child_limits'] == child['policy'] == input_read.COMPACT_POLICY
    assert result['source_observation_count'] == 3
    child_facts, _ = _pair(output / CHILD, 'read_facts')
    assert all(row['missing_reason'] == 'observed'
               for kind, row in child_facts['source_projection']['rows']
               if kind == 'source_observation')
    assert result['quote_states'] == {'observed': 1}
    assert result['source_provenance_class'] == 'synthetic'
    facts, _ = _pair(output, 'quote_facts')
    assert facts['projection']['quotes'][0]['midpoint'] == '0.500'
    saved = snapshot(output)
    assert read_quote_computation(output) == result
    assert snapshot(root) == before and snapshot(output) == saved


async def test_default_schema_and_caps_stay_unchanged(tmp_path):
    root, _ = await source(tmp_path)
    out = tmp_path / 'fs2_quote_computation_default'
    result = record_quote_computation(root, output_root=out, policy=QuoteInputPolicy(60, 60))
    parent, _ = _pair(out, 'quote_policy')
    child, _ = _pair(out / CHILD, 'read_policy')
    assert result['schema_version'] == quote_computation.VERSION
    assert parent['limits'] == quote_computation.LIMITS
    assert child['policy'] == input_read.POLICY
    assert parent['limits']['max_output_bytes'] == 64 * MIB
    assert child['policy']['max_output_bytes'] == 32 * MIB
    assert 'storage_profile' not in parent['limits'] and 'storage_profile' not in child['policy']


@pytest.mark.parametrize('value', ['automatic', True, 8 * MIB, {}, ''])
def test_unknown_profiles_refused_before_writes(tmp_path, value):
    source_root = tmp_path / 'fs2_capture_missing'
    for fn, path, kwargs in (
        (record_input_read, tmp_path / 'fs2_input_read_bad', {}),
        (record_quote_computation, tmp_path / 'fs2_quote_computation_bad',
         {'policy': QuoteInputPolicy(60, 60)}),
    ):
        with pytest.raises(ValueError, match='storage profile'):
            fn(source_root, output_root=path, storage_profile=value, **kwargs)
        assert not path.exists()
    with pytest.raises(ValueError, match='storage profile'):
        reservation(protocol(), storage_profile=value)


@pytest.mark.parametrize('target', ['parent_profile', 'parent_limit', 'child_binding',
                                   'child_profile', 'child_limit', 'schema'])
async def test_rehashed_quota_profile_or_child_mismatch_rejected(tmp_path, target):
    root, _ = await source(tmp_path)
    compute(tmp_path, root)
    out = tmp_path / 'fs2_quote_computation_compact'
    if target == 'parent_profile':
        rewrite(out, 'quote_policy', lambda p: p['limits'].update(storage_profile='unknown'))
    elif target == 'parent_limit':
        rewrite(out, 'quote_policy', lambda p: p['limits'].update(max_output_bytes=64 * MIB))
    elif target == 'child_binding':
        rewrite(out, 'quote_policy', lambda p: p.update(child_limits=input_read.POLICY))
    elif target == 'child_profile':
        rewrite(out / CHILD, 'read_policy', lambda p: p['policy'].update(storage_profile='unknown'))
    elif target == 'child_limit':
        rewrite(out / CHILD, 'read_policy', lambda p: p['policy'].update(max_output_bytes=32 * MIB))
    else:
        rewrite(out, 'quote_policy', lambda p: p.update(schema_version='fs2-quote-computation-v1'))
    saved = snapshot(out)
    with pytest.raises(ValueError):
        read_quote_computation(out)
    assert snapshot(out) == saved


async def test_low_disk_reserves_chosen_whole_parent_and_replay_needs_no_free_space(
        tmp_path, monkeypatch):
    root, _ = await source(tmp_path)
    free = 2 * 1024**3 + 8 * MIB
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(free, 0, free))
    result = compute(tmp_path, root)
    with pytest.raises(ValueError, match='insufficient quote computation'):
        record_quote_computation(root, output_root=tmp_path / 'fs2_quote_computation_default',
                                  policy=QuoteInputPolicy(60, 60))
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(free, free, 0))
    assert read_quote_computation(tmp_path / 'fs2_quote_computation_compact') == result
    with pytest.raises(ValueError, match='insufficient input-read'):
        record_input_read(root, output_root=tmp_path / 'fs2_input_read_full',
                          storage_profile=PROFILE)


@pytest.mark.parametrize('kind', ['input', 'computation'])
def test_actual_artifact_and_recursive_byte_checks_precede_writes(tmp_path, kind):
    module = input_read if kind == 'input' else quote_computation
    limits = input_read.COMPACT_POLICY if kind == 'input' else quote_computation.COMPACT_LIMITS
    root = tmp_path / kind
    root.mkdir()
    with pytest.raises(ValueError, match='artefact'):
        module._save(root, 'too_large', {'value': 'a' * (2 * MIB)}, time.monotonic(), limits=limits)
    assert not list(root.iterdir())
    for n in range(limits['max_output_bytes'] // MIB):
        (root / str(n)).write_bytes(b'x' * MIB)
    before = snapshot(root)
    with pytest.raises(ValueError, match='retained-byte'):
        module._save(root, 'beyond_total', {'value': 1}, time.monotonic(), limits=limits)
    assert snapshot(root) == before


async def test_large_actual_source_read_stops_without_truncating_raw_or_retrying(tmp_path):
    source_run = run(tmp_path, quota=32 * MIB, value=market(description='x' * 750000),
                     budget=Budget(requests=3, bytes_per_response=MIB, total_bytes=3 * MIB))
    for _ in range(3):
        await fetch(source_run)
    root = source_run.journal.root
    before = snapshot(root)
    out = tmp_path / 'fs2_quote_computation_compact'
    with pytest.raises(ValueError, match='artefact'):
        compute(tmp_path, root)
    assert (out / 'quote_failure_ack.json').exists()
    assert (out / CHILD / 'read_failure_ack.json').exists()
    assert not (out / CHILD / 'read_facts.json').exists()
    assert snapshot(root) == before
    with pytest.raises(FileExistsError):
        compute(tmp_path, root)


async def test_compact_original_code_recovery(tmp_path, original_code):
    root, _ = await source(tmp_path)
    expected = compute(tmp_path, root)
    result = read_original_quote_computation(tmp_path / 'fs2_quote_computation_compact',
        implementation_commit=original_code[1], repository=original_code[0],
        output_root=tmp_path / 'fs2_quote_computation_read_compact')
    assert result['report']['summary'] == expected
    facts, _ = _pair(tmp_path / 'fs2_quote_computation_compact', 'quote_facts')
    assert result['report']['facts'] == facts


async def test_declared_compact_cost_and_selection_binding(tmp_path, original_code):
    source_root = await frame(tmp_path)
    panel = tmp_path / 'fs2_panel_compact'
    p = protocol(cycles=1, target_attempts=1)
    default = reservation(p)
    compact = reservation(p, storage_profile=PROFILE)
    assert default['computation_retained_bytes'] == default['source_run_slots'] * 64 * MIB
    assert compact['computation_retained_bytes'] == compact['source_run_slots'] * 8 * MIB
    assert default['source_retained_bytes'] == compact['source_retained_bytes']
    result = declare_panel(source_root, implementation_commit=original_code[1], output_root=panel,
                            protocol=p, storage_profile=PROFILE)
    assert result['schema_version'] == 'fs2-panel-declaration-v2'
    assert read_panel_declaration(panel) == result
    selected = create_panel_selection(panel, repository=original_code[0])
    out = selection_root(panel)
    policy, _ = _pair(out, 'selection_policy')
    assert policy['computation_storage_profile'] == PROFILE
    assert not selected['collection_enabled']
    rewrite(out, 'selection_policy', lambda p: p.update(computation_storage_profile=None))
    with pytest.raises(ValueError, match='declaration/recipe'):
        read_selection(out)


async def test_standalone_compact_read_and_rehashed_limit_refusal(tmp_path):
    root, _ = await source(tmp_path)
    out = tmp_path / 'fs2_input_read_compact'
    result = record_input_read(root, output_root=out, storage_profile=PROFILE)
    assert read_input_read(out) == result
    rewrite(out, 'read_policy', lambda p: p['policy'].update(max_output_bytes=32 * MIB))
    with pytest.raises(ValueError, match='build/policy'):
        read_input_read(out)
