"""Original consumer verification must preserve the already frozen selection exactly."""

import pytest

from astrolabe.research_panel.original_reader import read_original_selection
from tests.unit.test_research_panel_original_reader import git
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, select, snapshot

original_code = _original_code


def read(tmp_path, source, code, **kwargs):
    return read_original_selection(
        source, implementation_commit=code[1], repository=code[0],
        output_root=tmp_path / 'fs2_selection_read_test', **kwargs,
    )


async def test_original_selection_preserves_seed_weights_clocks_status_and_all_evidence(
        tmp_path, original_code):
    source = await frame(tmp_path)
    selection = select(tmp_path, source, original_code)
    root = tmp_path / 'fs2_selection_test'
    before, source_before = snapshot(root), snapshot(source)
    result = read(tmp_path, root, original_code)
    assert result['report'] == selection
    assert result['read_receipt']['schema_version'] == 'fs2-original-selection-read-v1'
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert not result['read_receipt']['origin_admitted']
    assert not result['read_receipt']['observation_clocks_changed']
    assert (selection['selection_available_at']['utc']
            <= result['read_receipt']['metadata_read_started_at']['utc']
            <= result['read_receipt']['completed_at']['utc']
            <= result['read_available_at']['utc'])
    assert before == snapshot(root) and source_before == snapshot(source)
    assert not git(original_code[0], 'status', '--porcelain')
    with pytest.raises(FileExistsError):
        read(tmp_path, root, original_code)
    assert before == snapshot(root)


@pytest.mark.parametrize('corruption', ['source', 'inventory', 'plan', 'status'])
async def test_original_decoder_refuses_corrupted_selection_closure(
        tmp_path, original_code, corruption):
    source = await frame(tmp_path)
    select(tmp_path, source, original_code)
    root = tmp_path / 'fs2_selection_test'
    if corruption == 'source':
        next(source.glob('*/raw.bin')).write_bytes(b'corrupt synthetic source')
    elif corruption == 'inventory':
        amend(root, 'inventory', lambda p: p['counts'].update(source_rows=99))
    elif corruption == 'plan':
        hash_ = amend(root, 'selection_plan', lambda p: p.update(unique_selected_markets=99))
        amend(root, 'selection_report', lambda r: r.update(plan_hash=hash_))
    else:
        amend(root, 'selection_report', lambda r: r.update(provenance_class='prospective'))
    before, source_before = snapshot(root), snapshot(source)
    with pytest.raises(ValueError, match='original-build verification refused the selection'):
        read(tmp_path, root, original_code)
    output = tmp_path / 'fs2_selection_read_test'
    assert (output / 'read_failure_ack.json').exists()
    assert not (output / 'read_receipt_ack.json').exists()
    assert before == snapshot(root) and source_before == snapshot(source)


async def test_changed_original_code_cannot_reinterpret_selection(tmp_path, original_code):
    source = await frame(tmp_path)
    select(tmp_path, source, original_code)
    root = tmp_path / 'fs2_selection_test'
    repo, _ = original_code
    path = repo / 'backend/astrolabe/research_panel/selection.py'
    path.write_text(path.read_text() + '\n# changed synthetic build\n')
    git(repo, 'add', 'backend')
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Changed selection build')
    with pytest.raises(ValueError, match='hash differs'):
        read(tmp_path, root, (repo, git(repo, 'rev-parse', 'HEAD')))
    assert not (tmp_path / 'fs2_selection_read_test').exists()


@pytest.mark.parametrize('parent', ['selection', 'source'])
async def test_reader_output_cannot_mutate_any_original_evidence(
        tmp_path, original_code, parent):
    source = await frame(tmp_path)
    select(tmp_path, source, original_code)
    root = tmp_path / 'fs2_selection_test'
    target = (root if parent == 'selection' else source) / 'fs2_selection_read_nested'
    before, source_before = snapshot(root), snapshot(source)
    with pytest.raises(ValueError, match='separate'):
        read_original_selection(root, implementation_commit=original_code[1],
                                repository=original_code[0], output_root=target)
    assert not target.exists()
    assert before == snapshot(root) and source_before == snapshot(source)


async def test_selection_reader_refuses_mutable_original_revision(tmp_path, original_code):
    source = await frame(tmp_path)
    select(tmp_path, source, original_code)
    with pytest.raises(ValueError, match='immutable Git commit'):
        read(tmp_path, tmp_path / 'fs2_selection_test', (original_code[0], 'HEAD'))


async def test_transitive_source_path_must_be_canonical_before_any_output(tmp_path, original_code):
    source = await frame(tmp_path)
    select(tmp_path, source, original_code)
    root = tmp_path / 'fs2_selection_test'
    hash_ = amend(root, 'selection_policy', lambda p: p.update(frame_root=source.name))
    amend(root, 'selection_report', lambda r: r.update(policy_hash=hash_))
    before = snapshot(source)
    with pytest.raises(ValueError, match='canonical original source evidence'):
        read(tmp_path, root, original_code)
    assert not (tmp_path / 'fs2_selection_read_test').exists()
    assert before == snapshot(source)
