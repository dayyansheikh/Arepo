"""Historical computation reads use original code and preserve every old clock and value."""

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.original_reader import read_original_quote_computation
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import git
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_quote_computation import output, record, source

original_code = _original_code


def read(tmp_path, code, root=None):
    return read_original_quote_computation(
        root or output(tmp_path), implementation_commit=code[1], repository=code[0],
        output_root=tmp_path / 'fs2_quote_computation_read_test')


async def test_exact_original_computation_and_source_clocks_remain_unchanged(
        tmp_path, original_code):
    root, _ = await source(tmp_path)
    summary = record(root, tmp_path)
    facts, _ = _pair(output(tmp_path), 'quote_facts')
    before, source_before = snapshot(output(tmp_path)), snapshot(root)
    result = read(tmp_path, original_code)
    assert result['report'] == {'facts': facts, 'summary': summary}
    receipt = result['read_receipt']
    assert receipt['schema_version'] == 'fs2-original-quote-computation-read-v1'
    assert receipt['original_provenance_class'] == 'synthetic'
    assert receipt['original_state'] == 'verified_quote_computation'
    assert not receipt['origin_admitted'] and not receipt['observation_clocks_changed']
    assert (summary['computation_available_at']['utc'] <= receipt['metadata_read_started_at']['utc']
            <= receipt['completed_at']['utc'] <= result['read_available_at']['utc'])
    assert snapshot(output(tmp_path)) == before and snapshot(root) == source_before
    assert not git(original_code[0], 'status', '--porcelain')
    with pytest.raises(FileExistsError):
        read(tmp_path, original_code)


@pytest.mark.parametrize('corruption', ['source', 'child', 'midpoint', 'provenance', 'failure'])
async def test_original_decoder_refuses_corruption_without_repair(
        tmp_path, original_code, corruption):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    computation = output(tmp_path)
    if corruption == 'source':
        next(root.glob('*/raw.bin')).write_bytes(b'corrupt fixture')
    elif corruption == 'child':
        (computation / 'fs2_input_read_source' / 'read_facts.json').write_bytes(b'{}')
    elif corruption in {'midpoint', 'provenance'}:
        def alter(facts):
            if corruption == 'midpoint':
                facts['projection']['quotes'][0]['midpoint'] = '0.9'
            else:
                facts['projection']['provenance_class'] = 'prospective'
        rewrite(computation, 'quote_facts', alter)
    else:
        (computation / 'quote_failure.json').write_bytes(b'{}')
    before, source_before = snapshot(computation), snapshot(root)
    with pytest.raises(ValueError, match='original-build verification refused'):
        read(tmp_path, original_code)
    assert snapshot(computation) == before and snapshot(root) == source_before
    assert (tmp_path / 'fs2_quote_computation_read_test' / 'read_failure_ack.json').exists()


@pytest.mark.parametrize('where', ['source', 'computation', 'child'])
async def test_read_output_cannot_nest_in_original_evidence(tmp_path, original_code, where):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    parent = {'source': root, 'computation': output(tmp_path),
              'child': output(tmp_path) / 'fs2_input_read_source'}[where]
    target = parent / 'fs2_quote_computation_read_nested'
    with pytest.raises(ValueError, match='separate'):
        read_original_quote_computation(output(tmp_path), implementation_commit=original_code[1],
            repository=original_code[0], output_root=target)
    assert not target.exists()


async def test_changed_original_code_or_mutable_revision_refused(tmp_path, original_code):
    root, _ = await source(tmp_path)
    record(root, tmp_path)
    with pytest.raises(ValueError, match='immutable Git commit'):
        read(tmp_path, (original_code[0], 'HEAD'))
    path = original_code[0] / 'backend/astrolabe/research_panel/quote_computation.py'
    path.write_text(path.read_text() + '\n# altered fixture\n')
    git(original_code[0], 'add', 'backend')
    git(original_code[0], '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Alter quote build')
    with pytest.raises(ValueError, match='hash differs'):
        read(tmp_path, (original_code[0], git(original_code[0], 'rev-parse', 'HEAD')))
    assert not (tmp_path / 'fs2_quote_computation_read_test').exists()
