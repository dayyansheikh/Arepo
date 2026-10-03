"""Owned selection reuse is pre-source authentication, never a persisted cache shortcut."""

import sys

import httpx
import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import screening
from astrolabe.research_panel import screening_worker as worker
from astrolabe.research_panel.panel_selection import selection_root
from tests.unit.test_research_panel_input_read import rewrite
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_screening import assessed
from tests.unit.test_research_panel_screening_worker import mock, prepared, run

original_code = _original_code


async def test_complete_selection_verified_once_before_sources_then_original_audit(
    tmp_path, original_code
):
    _, panel, rows = await prepared(tmp_path, original_code, event_ids=True)
    transport, calls = mock(rows, omit_events=True)
    events = []
    selected_code = screening._selected.__code__
    audit_code = worker.read_original_screening.__code__

    def observe(frame, event, arg):
        if event != 'call':
            return
        if frame.f_code is selected_code:
            events.append('complete_selection')
            assert not calls['requests']
        elif frame.f_code is audit_code:
            events.append('original_audit')
            assert len(calls['requests']) == 4

    # Observe real function calls without replacing authenticated implementation code.
    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        result = await run(panel, original_code, transport, identity_policy=worker.IDENTITY_POLICY)
    finally:
        sys.setprofile(previous)
    assert events == ['complete_selection', 'original_audit']
    assert result['role_capacity']['counts_per_cycle'] == {
        'scheduled': 2, 'triggered': 1, 'control': 1}
    assert result['screening']['schema_version'] == screening.OWNED_VERSION
    assert not result['accepted_panel'] and not result['origin_admitted']


async def test_modified_selection_after_read_fails_mandatory_cold_recovery(
    tmp_path, original_code
):
    _, panel, rows = await prepared(tmp_path, original_code, event_ids=True)
    transport, calls = mock(rows, omit_events=True)
    changed = False

    async def handle(request):
        nonlocal changed
        if not changed:
            changed = True
            rewrite(selection_root(panel), 'selection_report',
                    lambda p: p.update(unique_selected_markets=99))
        return await transport.handle_async_request(request)

    with pytest.raises(ValueError):
        await run(panel, original_code, httpx.MockTransport(handle),
                  identity_policy=worker.IDENTITY_POLICY)
    root = worker.worker_root(panel)
    failure, _ = _pair(root, 'worker_failure')
    assert failure['stage'] == 'recovery'
    assert len(calls['requests']) == 4
    assert not (root / 'worker_report.json').exists()
    assert (root / 'fs2_screening_batch/screening_report.json').exists()
    assert not list(tmp_path.glob('fs2_activation_*'))


async def test_mutated_policy_cannot_rebind_owned_selection(tmp_path, original_code):
    _, panel, rows = await prepared(tmp_path, original_code)
    root = tmp_path / 'fs2_screening_owned'
    frozen, finish = screening._prepare_owned_screening(
        selection_root(panel), output_root=root,
        rule=worker.SnapshotTriggerPolicy(1, 3, 60000), policy=screening.ScreeningPolicy(60, 60))
    await assessed(tmp_path, frozen, rows)
    rewrite(root, 'screening_policy', lambda p: p.update(seed='changed'))
    with pytest.raises(ValueError, match='changed after authentication'):
        finish()
    assert not (root / 'screening_completion_policy.json').exists()


async def test_returned_mutable_copy_cannot_change_owned_proof_or_repeat_cutoff(
    tmp_path, original_code
):
    _, panel, rows = await prepared(tmp_path, original_code)
    root = tmp_path / 'fs2_screening_owned'
    frozen, finish = screening._prepare_owned_screening(
        selection_root(panel), output_root=root,
        rule=worker.SnapshotTriggerPolicy(1, 3, 60000), policy=screening.ScreeningPolicy(60, 60))
    await assessed(tmp_path, frozen, rows)
    frozen['selected'][0]['member']['market_id'] = '999'
    result = finish()
    assert {r['market_id'] for r in result['states']} == {'1', '2'}
    assert screening.read_screening(root) == result
    with pytest.raises(FileExistsError, match='already attempted'):
        finish()
