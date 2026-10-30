"""Versioned origin persistence binds an already verified pre-origin window."""

import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.feature_store.capture import _clock
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import origin_features, origin_worker, screening
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.panel_selection import selection_root
from astrolabe.research_panel.scheduling import wait_until
from astrolabe.research_panel.socket_analysis import record_socket_analysis
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_origin_window import prepared as history_prepared
from tests.unit.test_research_panel_origin_window import project
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_owned_pilot import transport
from tests.unit.test_research_panel_screening import assessed
from tests.unit.test_research_panel_screening_worker import prepared
from tests.unit.test_research_panel_socket_window import capture
from tests.unit.test_research_panel_socket_window import output as socket_output

original_code = _original_code


async def ready(tmp_path, code):
    _, panel, rows = await prepared(tmp_path, code, event_ids=True,
        max_origin_delay_seconds=45, horizon_seconds=8, tolerance_seconds=5,
        max_origin_save_seconds=2)
    frozen, finish = screening._prepare_owned_screening(selection_root(panel),
        output_root=tmp_path / 'fs2_screening_window', rule=SnapshotTriggerPolicy(1, 3, 60000),
        policy=screening.ScreeningPolicy(120, 120))
    await assessed(tmp_path, frozen, [{k: v for k, v in r.items() if k != 'events'} for r in rows])
    item = frozen['selected'][0]
    book_root = Path(item['book_root'])
    facts, _ = _pair(book_root, 'book_facts')
    quote = facts['projection']['snapshots'][0]['quote']

    async def handle(socket):
        await socket.recv()
        await socket.send(json.dumps({'event_type': 'book', 'asset_id': quote['token_id'],
            'market': quote['condition_id'], 'bids': [{'price': '0.4', 'size': '2'}],
            'asks': [{'price': '0.6', 'size': '1'}]}))
        await socket.wait_closed()

    await capture(book_root, tmp_path, handle, duration=50)
    window = tmp_path / 'fs2_socket_analysis_origin'
    record_socket_analysis(socket_output(tmp_path), output_root=window,
                           policy=WindowReconciliationPolicy(60000, 60000, 1000))
    _, active = finish(activate=True)
    member = next(m for m in active['selected'] if m['market_id'] == item['member']['market_id'])
    slot = next(s for s in active['slots'] if s['market_id'] == member['market_id'])
    policy, _ = _pair(panel, 'panel_policy')
    await wait_until(datetime.fromisoformat(slot['scheduled_at']))
    return active, member, slot, policy, window, rows


async def test_window_origin_preserves_actual_read_freeze_and_cold_replay(tmp_path, original_code):
    active, member, slot, policy, window, rows = await ready(tmp_path, original_code)
    source, _ = transport(rows)
    root = tmp_path / 'origin_window_test'
    before = snapshot(window)
    result = await origin_worker._collect_one(root, slot, member, policy, active, source,
        features=True, window_root=window, window_policy=OriginWindowPolicy(120000, 60000))
    assert result['state'] == 'observed'
    intent, _ = _pair(root, 'origin_intent')
    facts, _ = _pair(root, 'origin_facts')
    projection = facts['projection']
    assert intent['schema_version'] == origin_worker.WINDOW_VERSION
    assert projection['pre_origin_window']['eligible_at_freeze']
    assert projection['pre_origin_window']['cutoff'] == facts['read_started_at']
    assert projection['pre_origin_window']['frozen_at'] == facts['origin_at']
    assert projection['feature_manifest']['schema_version'] == origin_features.WINDOW_VERSION
    assert 'price_history' not in projection['feature_manifest']['unavailable_families']
    assert not projection['feature_manifest']['continuous_window_eligible']
    stored = snapshot(root)
    assert origin_worker._read_one(root, slot, member, policy, active) == result
    assert snapshot(root) == stored and snapshot(window) == before
    rewrite(window, 'socket_analysis_facts',
            lambda p: p['projection'].update(continuous_sequence_proven=True))
    with pytest.raises(ValueError):
        origin_worker._read_one(root, slot, member, policy, active)


async def test_freeze_rechecks_staleness_without_erasing_historical_values(tmp_path, monkeypatch):
    quote = await history_prepared(tmp_path)
    cutoff = _clock()
    window = project(tmp_path, quote, cutoff=cutoff)
    projection = {'state_at_freeze': 'observed', 'feature_manifest': {
        'snapshot_state': 'observed', 'unavailable_families': {}}}
    origin_features.attach_window(projection, window)
    frozen = deepcopy(cutoff)
    frozen['utc'] = (datetime.fromisoformat(cutoff['utc'].replace('Z', '+00:00'))
                     + timedelta(seconds=61)).isoformat()
    frozen['monotonic_ns'] = str(int(cutoff['monotonic_ns']) + 61000000000)
    historical = deepcopy(window['history'])
    origin_features.freeze_eligibility(projection, freeze=frozen)
    assert window['history'] == historical
    assert not window['eligible_at_freeze']
    assert set(window['freeze_reasons']) == {
        'prior_quote_stale_at_freeze', 'window_stale_at_freeze'}
    assert 'price_history' not in projection['feature_manifest']
    missing = projection['feature_manifest']['unavailable_families']['price_history']
    assert missing['state'] == 'unavailable'
    monkeypatch.setattr(origin_features, 'WINDOW_MAX_BYTES', 0)
    with pytest.raises(ValueError, match='byte budget'):
        origin_features.freeze_eligibility(projection, freeze=frozen)


async def test_window_arguments_fail_before_origin_creation(tmp_path):
    root = tmp_path / 'must_not_exist'
    activation = {'schema_version': 'legacy'}
    with pytest.raises(ValueError, match='explicit owned'):
        await origin_worker._collect_one(root, {}, {}, {}, activation, None, features=True,
            window_root=tmp_path / 'window', window_policy=OriginWindowPolicy(1000, 1000))
    assert not root.exists()
