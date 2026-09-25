"""Original-code recovery of exact book components with immutable source clocks."""

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.original_reader import read_original_book_computation
from tests.unit.test_research_panel_book_computation import output, record
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import git
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_quote_computation import source

original_code = _original_code


def read(target, tmp_path, code):
    return read_original_book_computation(target, implementation_commit=code[1],
        repository=code[0], output_root=tmp_path / 'fs2_book_computation_read_test')


async def test_exact_original_book_facts_summary_clocks_and_path_protection(
        tmp_path, original_code):
    root, _ = await source(tmp_path)
    summary = record(root, tmp_path)
    target = output(tmp_path)
    facts, _ = _pair(target, 'book_facts')
    before = (snapshot(root), snapshot(target))
    result = read(target, tmp_path, original_code)
    assert result['report'] == {'facts': facts, 'summary': summary}
    assert result['read_receipt']['original_state'] == 'verified_book_computation'
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert result['read_receipt']['origin_admitted'] is False
    assert result['read_receipt']['observation_clocks_changed'] is False
    assert summary['computation_available_at']['utc'] <= result['read_available_at']['utc']
    assert before == (snapshot(root), snapshot(target))
    for parent in (root, target):
        nested = parent / 'fs2_book_computation_read_nested'
        with pytest.raises(ValueError, match='separate'):
            read_original_book_computation(target, implementation_commit=original_code[1],
                                           repository=original_code[0], output_root=nested)
        assert not nested.exists()
    assert not git(original_code[0], 'status', '--porcelain')
    with pytest.raises(FileExistsError):
        read(target, tmp_path, original_code)


@pytest.mark.parametrize('change', ['raw', 'component', 'clock'])
async def test_original_book_decoder_refuses_resealed_changes(tmp_path, original_code, change):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    target = output(tmp_path)
    if change == 'raw':
        next(root.glob('*/raw.bin')).write_bytes(b'changed synthetic fixture')
    elif change == 'component':
        rewrite(target, 'book_facts', lambda p:
            p['projection']['snapshots'][0]['components']['F09_snapshot'].update(numerator='99'))
    else:
        policy, _ = _pair(target, 'book_policy')
        rewrite(target, 'book_facts', lambda p: p.update(computed_at=policy['declared_at']))
    before = (snapshot(root), snapshot(target))
    with pytest.raises(ValueError, match='original-build verification refused'):
        read(target, tmp_path, original_code)
    assert (tmp_path / 'fs2_book_computation_read_test' / 'read_failure_ack.json').exists()
    assert before == (snapshot(root), snapshot(target))
