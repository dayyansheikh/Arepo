"""Durable development selection through actual original-code child decoders."""

import shutil
import time

import httpx
import pytest

from astrolabe.feature_store.capture import Budget, _digest, _json_bytes
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import selection
from astrolabe.research_panel.frame import GammaFrameRun
from astrolabe.research_panel.selection import SelectionBudget, create_selection, read_selection
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_frame import body, market
from tests.unit.test_research_panel_original_reader import original_code as _original_code

original_code = _original_code


async def frame(tmp_path, rows=None, *, incomplete=False):
    root = tmp_path.resolve() / 'fs2_capture_selection_input'
    rows = [market()] if rows is None else rows
    run = GammaFrameRun(root, limit=len(rows) if incomplete else 100,
                        budget=Budget(requests=1), transport=httpx.MockTransport(
                            lambda r: httpx.Response(200, stream=Stream([
                                body(rows, 'next' if incomplete else None)]))))
    await run.collect()
    return root


def select(tmp_path, root, code, **kwargs):
    repo, commit = code
    return create_selection(root, implementation_commit=commit, repository=repo,
                            output_root=tmp_path.resolve() / 'fs2_selection_test', **kwargs)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def amend(root, name, fn):
    value, ack = _pair(root, name)
    fn(value)
    data = _json_bytes(value)
    (root / (name + '.json')).write_bytes(data)
    ack['payload_hash'] = _digest(data)
    (root / (name + '_ack.json')).write_bytes(_json_bytes(ack))
    return ack['payload_hash']


async def test_complete_inventory_exact_sampling_new_clocks_and_read_only_recovery(
        tmp_path, original_code):
    root = await frame(tmp_path, [market(1), market(1), market(2), market(3),
                                  market(4, clobTokenIds=None)])
    before = snapshot(root)
    result = select(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_test'
    assert result['provenance_class'] == 'synthetic'
    assert result['counts']['source_rows'] == 5
    assert result['counts']['eligible_row_count'] == 4
    assert result['counts']['sampling_members'] == 3
    assert result['counts']['excluded:identity_unresolved'] == 1
    assert result['unique_selected_markets'] == 1
    assignment = result['plan']['assignments'][0]
    assert assignment['inclusion_probability'] == {
        'numerator': '1', 'denominator': '3', 'decimal': None, 'decimal_state': 'nonterminating'}
    assert assignment['arm'] == 'scheduled' and not assignment['matched_trigger_ids']
    assert not result['origin_admitted'] and not result['population_inference_eligible']
    policy, policy_ack = _pair(output, 'selection_policy')
    read_policy, _ = _pair(output / selection.READ_FOLDER, 'read_policy')
    assert policy_ack['durable_ack']['utc'] <= read_policy['metadata_read_started_at']['utc']
    page_folder = next((output / 'pages').iterdir())
    projection, projection_ack = _pair(page_folder, 'projection')
    missing = projection['rows'][-1]
    assert missing['selected_token_id'] is None and missing['metadata'] is None
    assert projection['rows'][1]['duplicate_of'] == projection['rows'][0]['evidence_id']
    assert projection_ack['durable_ack']['utc'] <= result['sampling_cutoff']['utc']
    assert result['original_frame_available_at']['utc'] < result['selection_available_at']['utc']
    saved = snapshot(output)
    assert read_selection(output) == result
    assert saved == snapshot(output) and before == snapshot(root)
    with pytest.raises(FileExistsError, match='never resume or reseed'):
        select(tmp_path, root, original_code)
    assert saved == snapshot(output)
    cold = tmp_path / 'fs2_selection_cold_copy'
    shutil.copytree(output, cold)
    assert read_selection(cold) == result
    assert policy['sampling_protocol']['seed'] == result['plan']['protocol']['seed']


@pytest.mark.parametrize('kind', ['incomplete', 'conflicting', 'empty'])
async def test_unusable_frame_keeps_failed_declaration_and_never_selects(
        tmp_path, original_code, kind):
    rows = [] if kind == 'empty' else [market(1)]
    if kind == 'conflicting':
        rows.append(market(1, liquidity='5'))
    root = await frame(tmp_path, rows, incomplete=kind == 'incomplete')
    with pytest.raises(ValueError, match='complete consistent'):
        select(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_test'
    assert (output / 'selection_policy_ack.json').exists()
    assert (output / 'selection_failure_ack.json').exists()
    assert not (output / 'selection_report_ack.json').exists()


async def test_unknown_category_is_distinct_from_literal_source_unknown(tmp_path, original_code):
    root = await frame(tmp_path, [market(1), market(2, category='unknown')])
    result = select(tmp_path, root, original_code)
    assert {s['category'] for s in result['plan']['strata']} == {'unknown', 'source:unknown'}
    assert result['unique_selected_markets'] == 2


async def test_over_budget_sample_keeps_inventory_and_does_not_truncate(tmp_path, original_code):
    root = await frame(tmp_path, [market(1), market(2, category='Sports')])
    before = snapshot(root)
    with pytest.raises(ValueError, match='never truncate'):
        select(tmp_path, root, original_code, max_unique_markets=1)
    output = tmp_path / 'fs2_selection_test'
    assert (output / 'inventory_ack.json').exists()
    assert not (output / 'selection_plan.json').exists()
    assert before == snapshot(root)


async def test_row_ceiling_cannot_sample_prefix(tmp_path, original_code):
    root = await frame(tmp_path, [market(1), market(2)])
    with pytest.raises(ValueError, match='frame exceeds selection budget'):
        select(tmp_path, root, original_code, budget=SelectionBudget(rows=1))
    assert not (tmp_path / 'fs2_selection_test/pages').exists()


async def test_source_tampering_refused_before_or_after_selection(tmp_path, original_code):
    root = await frame(tmp_path)
    select(tmp_path, root, original_code)
    raw = next(root.glob('*/raw.bin'))
    raw.write_bytes(b'corrupt synthetic data')
    with pytest.raises(ValueError, match='raw capture integrity'):
        read_selection(tmp_path / 'fs2_selection_test')
    other = tmp_path / 'second'
    other.mkdir()
    with pytest.raises(ValueError, match='original-build verification refused'):
        select(other, root, original_code)
    assert (other / 'fs2_selection_test/selection_failure_ack.json').exists()
    assert raw.read_bytes() == b'corrupt synthetic data'


async def test_missing_projection_ack_and_extra_page_refuse_recovery(tmp_path, original_code):
    root = await frame(tmp_path)
    select(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_test'
    extra = output / 'pages/extra'
    extra.mkdir()
    with pytest.raises(ValueError, match='page closure differs'):
        read_selection(output)
    extra.rmdir()  # disposable synthetic fixture only
    next((output / 'pages').glob('*/projection_ack.json')).unlink()
    before = snapshot(output)
    with pytest.raises(FileNotFoundError):
        read_selection(output)
    assert before == snapshot(output)


async def test_rehashed_false_weight_cannot_replace_exact_replay(tmp_path, original_code):
    root = await frame(tmp_path, [market(1), market(2)])
    select(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_test'
    hash_ = amend(output, 'selection_plan', lambda p: p['assignments'][0][
        'inclusion_probability'].update(denominator='7'))
    amend(output, 'selection_report', lambda r: r.update(plan_hash=hash_))
    with pytest.raises(ValueError, match='plan/status differs'):
        read_selection(output)


async def test_rehashed_cutoff_before_projection_cannot_be_admitted(tmp_path, original_code):
    root = await frame(tmp_path)
    select(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_test'
    policy, _ = _pair(output, 'selection_policy')
    amend(output, 'selection_report', lambda r: r.update(sampling_cutoff=policy['declared_at']))
    with pytest.raises(ValueError, match='counts/cutoff/chronology differs'):
        read_selection(output)


async def test_changed_build_refuses_current_reader(tmp_path, original_code, monkeypatch):
    from astrolabe.research_panel import _PACKAGE_FILES

    root = await frame(tmp_path)
    select(tmp_path, root, original_code)
    monkeypatch.setitem(_PACKAGE_FILES, 'selection.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed on disk'):
        read_selection(tmp_path / 'fs2_selection_test')


async def test_insufficient_disk_refuses_before_declaration(tmp_path, original_code, monkeypatch):
    root = await frame(tmp_path)
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(100, 99, 1))
    with pytest.raises(ValueError, match='insufficient selection storage'):
        select(tmp_path, root, original_code)
    assert not (tmp_path / 'fs2_selection_test').exists()


async def test_child_read_consumes_processing_deadline(tmp_path, original_code, monkeypatch):
    from astrolabe.research_panel import original_reader

    root = await frame(tmp_path)
    original = original_reader.subprocess.run

    def delayed(*args, **kwargs):
        result = original(*args, **kwargs)
        if '-I' in args[0]:
            time.sleep(1.1)
        return result

    monkeypatch.setattr(original_reader.subprocess, 'run', delayed)
    with pytest.raises(ValueError, match='time budget exhausted'):
        select(tmp_path, root, original_code, budget=SelectionBudget(seconds=1))
    assert (tmp_path / 'fs2_selection_test/selection_failure_ack.json').exists()


async def test_child_output_reservation_is_part_of_frozen_budget(tmp_path, original_code):
    root = await frame(tmp_path)
    with pytest.raises(ValueError, match='output budget exhausted'):
        select(tmp_path, root, original_code, budget=SelectionBudget(output_bytes=1048576))
    output = tmp_path / 'fs2_selection_test'
    assert (output / 'selection_failure_ack.json').exists()
    assert not (output / selection.READ_FOLDER).exists()


@pytest.mark.parametrize('changed', ['source_policy', 'extra_capture', 'failed_read'])
async def test_original_evidence_closure_must_remain_intact(tmp_path, original_code, changed):
    root = await frame(tmp_path)
    select(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_test'
    if changed == 'source_policy':
        amend(root, 'frame_policy', lambda p: p['budget'].update(requests=2))
    elif changed == 'extra_capture':
        (root / 'unrecorded_attempt').mkdir()
    else:
        (output / selection.READ_FOLDER / 'read_failure.json').write_text('{}')
    pattern = '(evidence differs|page closure differs|failed original read)'
    with pytest.raises(ValueError, match=pattern):
        read_selection(output)


@pytest.mark.parametrize('kwargs', [{'rows': 400001}, {'pages': 4001}, {'seconds': 601},
                                   {'output_bytes': 1073741825}, {'rows': True}])
def test_selection_budget_cannot_be_unbounded(kwargs):
    with pytest.raises(ValueError, match='finite limits'):
        SelectionBudget(**kwargs)
