"""Fault-gated finite expansion: actual original decoder, synthetic source fixtures only."""

import json

import httpx
import pytest

from astrolabe.research_panel.frame import FrameBudget, GammaFrameRun, _request_capacity_basis
from tests.unit.test_research_panel_frame import body, market, measured_cost, run
from tests.unit.test_research_panel_original_reader import original_code as _original_code


@pytest.fixture
def original_code(tmp_path):
    return _original_code.__wrapped__(tmp_path)


def proof(root, original_code, tmp_path, *, synthetic=True):
    repo, commit = original_code
    return _request_capacity_basis(
        root, commit, repository=repo, synthetic=synthetic,
        read_root=tmp_path.resolve() / 'fs2_frame_read_capacity',
    )


async def test_request_capacity_proof_uses_original_decoder_and_keeps_failed_frame(
    tmp_path, original_code,
):
    root = await measured_cost(tmp_path)  # one full continuing page; synthetic request ceiling
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = proof(root, original_code, tmp_path)
    assert result['original_budget']['requests'] == 1
    assert result['read_receipt_hash']
    assert result['report_hash'] == json.loads((root / 'frame_report_ack.json').read_bytes())[
        'payload_hash']
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert json.loads((root / 'frame_report.json').read_bytes())['state'] == 'incomplete'


async def test_synthetic_request_proof_never_authorizes_live_expansion(tmp_path, original_code):
    root = await measured_cost(tmp_path)
    with pytest.raises(ValueError, match='prior request-ceiling'):
        proof(root, original_code, tmp_path, synthetic=False)


async def test_complete_frame_cannot_masquerade_as_request_ceiling(tmp_path, original_code):
    item, _ = run(tmp_path, [body([market()])], limit=100)
    await item.collect()
    with pytest.raises(ValueError, match='prior request-ceiling'):
        proof(item.journal.root, original_code, tmp_path)


async def test_byte_ceiling_cannot_authorize_request_expansion(tmp_path, original_code):
    basis = await measured_cost(tmp_path)
    prior_path = tmp_path / 'prior'
    prior_path.mkdir()
    prior, _ = run(prior_path, [body([market()])], limit=100,
                   budget=FrameBudget(requests=1, total_bytes=20), measurement_root=basis)
    await prior.collect()
    with pytest.raises(ValueError, match='prior request-ceiling'):
        proof(prior.journal.root, original_code, tmp_path)


async def test_corrupted_raw_capacity_evidence_is_rejected(tmp_path, original_code):
    root = await measured_cost(tmp_path)
    folder = next(p for p in root.iterdir() if p.is_dir())
    (folder / 'raw.bin').write_bytes(b'broken synthetic fixture')
    with pytest.raises(ValueError, match='original-build verification refused'):
        proof(root, original_code, tmp_path)


@pytest.mark.parametrize('budget', [
    FrameBudget(requests=1001), FrameBudget(total_bytes=1073741825),
    FrameBudget(retained_bytes=3221225473),
])
async def test_each_old_ceiling_requires_new_proof_before_a_run(tmp_path, budget):
    basis = await measured_cost(tmp_path)
    root = tmp_path.resolve() / 'fs2_capture_refused'
    with pytest.raises(ValueError, match='request-ceiling journal and commit required'):
        GammaFrameRun(root, budget=budget, measurement_root=basis,
                      transport=httpx.MockTransport(lambda r: None))
    assert not root.exists()


def test_original_defaults_unchanged_and_larger_absolute_limits_finite():
    default = FrameBudget()
    assert default.requests == 1000 and default.total_bytes == 268435456
    assert default.retained_bytes == 1073741824
    expanded = FrameBudget(requests=4000, total_bytes=3221225472, retained_bytes=8589934592)
    assert expanded.total_seconds == 900 and expanded.minimum_free_bytes == 2147483648


async def test_missing_original_code_cannot_fall_back_to_current_parser(tmp_path):
    root = await measured_cost(tmp_path)
    with pytest.raises(ValueError, match='unavailable in local Git'):
        _request_capacity_basis(root, '0' * 40, synthetic=True,
                                read_root=tmp_path.resolve() / 'fs2_frame_read_missing')


async def test_unused_request_proof_is_not_silently_ignored(tmp_path):
    with pytest.raises(ValueError, match='only to explicitly larger'):
        GammaFrameRun(tmp_path.resolve() / 'fs2_capture_refused',
                      request_capacity_root=tmp_path, request_capacity_commit='0' * 40)
