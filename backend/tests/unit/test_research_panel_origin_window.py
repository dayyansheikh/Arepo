"""Causal history is exact, identity-bound and separate from socket continuity."""

import json
from copy import deepcopy
from fractions import Fraction

import pytest

from astrolabe.feature_store.capture import _clock
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.origin_window import OriginWindowPolicy, project_origin_window
from tests.unit.test_research_panel_bound_window import pre
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_socket_analysis import output, record
from tests.unit.test_research_panel_socket_window import capture
from tests.unit.test_research_panel_window_coverage import book
from tests.unit.test_research_panel_window_reconciliation import post


async def prepared(tmp_path, *, silent=False, early_close=False, **kwargs):
    _, computation = await pre(tmp_path)

    async def handle(socket):
        await socket.recv()
        if not silent:
            await socket.send(json.dumps(book()))
        if early_close:
            await socket.close()
        else:
            await socket.wait_closed()

    await capture(computation, tmp_path, handle, duration=50)
    record(tmp_path)
    _, current = await post(tmp_path, **kwargs)
    facts, _ = _pair(current, 'book_facts')
    return facts['projection']['snapshots'][0]['quote']


def project(tmp_path, quote, **kwargs):
    return project_origin_window(output(tmp_path), quote, provenance='synthetic',
        cutoff=kwargs.pop('cutoff', _clock()),
        policy=kwargs.pop('policy', OriginWindowPolicy(60000, 60000)), **kwargs)


def fraction(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


async def test_exact_causal_history_and_baseline_recording_fixture(tmp_path):
    quote = await prepared(tmp_path, bid_price='0.5')
    before = snapshot(tmp_path)
    cutoff = _clock()
    result = project(tmp_path, quote, cutoff=cutoff)
    history = result['history']
    assert history['prior_midpoint']['decimal'] == '0.5'
    assert history['current_midpoint']['decimal'] == '0.55'
    assert fraction(history['midpoint_change']) == Fraction(1, 20)
    assert fraction(history['receipt_separation_ms']) > 0
    # Recording fixtures only; no baseline candidate lock/model fitting or prediction writer.
    fixtures = {'no_change': history['current_midpoint'],
                'momentum_input': history['midpoint_change']}
    assert json.loads(json.dumps(fixtures)) == fixtures
    assert not history['locked_baseline'] and not history['regular_cadence']
    assert not result['continuous_window_eligible'] and not result['origin_admitted']
    assert result['coverage']['uncovered_duration_ns'] != '0'
    assert project(tmp_path, quote, cutoff=cutoff) == result
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('kwargs', [{'rules': 'Changed'}, {'market': '20'}, {'token': '3'},
                                    {'closed': True}, {'book_status': 404}])
async def test_changed_or_unavailable_current_snapshot_is_not_history(tmp_path, kwargs):
    quote = await prepared(tmp_path, **kwargs)
    result = project(tmp_path, quote)
    assert result['history_state'] == 'unavailable' and result['history'] is None
    assert result['history_reasons']
    assert not result['registered_window_features_available']


@pytest.mark.parametrize('kwargs', [{'silent': True}, {'early_close': True}])
async def test_silence_or_disconnect_never_claims_continuity(tmp_path, kwargs):
    quote = await prepared(tmp_path, **kwargs)
    result = project(tmp_path, quote)
    assert int(result['coverage']['uncovered_duration_ns']) > 0
    assert not result['continuous_window_eligible']
    assert not result['native_clock_admitted']
    assert result['history_state'] == 'observed'  # two snapshots do not need continuous history


async def test_future_analysis_and_current_input_refused(tmp_path):
    early = _clock()
    quote = await prepared(tmp_path)
    with pytest.raises(ValueError, match='future'):
        project(tmp_path, quote, cutoff=early)
    changed = deepcopy(quote)
    changed['source_available_at'] = {'$utc': '2099-01-01T00:00:00Z'}
    with pytest.raises(ValueError, match='unavailable at'):
        project(tmp_path, changed)


async def test_staleness_and_reversed_observation_order_are_explicit(tmp_path):
    quote = await prepared(tmp_path)
    result = project(tmp_path, quote, policy=OriginWindowPolicy(0, 0))
    assert set(result['history_reasons']) == {'prior_quote_stale', 'window_stale'}
    quote['received_at'] = {'$utc': '2000-01-01T00:00:00Z'}
    assert 'current_quote_not_after_window' in project(tmp_path, quote)['history_reasons']


async def test_post_endpoint_and_provenance_mismatch_refused(tmp_path):
    quote = await prepared(tmp_path)
    with pytest.raises(ValueError, match='provenance'):
        project_origin_window(output(tmp_path), quote, provenance='prospective', cutoff=_clock(),
                              policy=OriginWindowPolicy(60000, 60000))
    from astrolabe.research_panel.socket_analysis import record_socket_analysis
    from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
    from tests.unit.test_research_panel_socket_window import output as socket_output
    with_post = tmp_path / 'fs2_socket_analysis_with_post'
    record_socket_analysis(socket_output(tmp_path), output_root=with_post,
        post_root=tmp_path / 'fs2_book_computation_post',
        policy=WindowReconciliationPolicy(60000, 60000, 1000))
    with pytest.raises(ValueError, match='post-window endpoint'):
        project_origin_window(with_post, quote, provenance='synthetic', cutoff=_clock(),
                              policy=OriginWindowPolicy(60000, 60000))
    # Mutating a declaration is not an allowed way to attach an endpoint or change lineage.
    rewrite(output(tmp_path), 'socket_analysis_policy', lambda p: p.update(post_root='/missing'))
    with pytest.raises((ValueError, FileNotFoundError)):
        project(tmp_path, quote)


async def test_corrupted_window_dependency_is_refused(tmp_path):
    quote = await prepared(tmp_path)
    from tests.unit.test_research_panel_socket_window import output as socket_output
    raw = next(socket_output(tmp_path).glob('event_*.bin'))
    raw.write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        project(tmp_path, quote)


@pytest.mark.parametrize('value', [-1, True, 300001, None])
def test_invalid_policy(value):
    with pytest.raises(ValueError):
        OriginWindowPolicy(value, 1000)


@pytest.mark.parametrize('price,change', [('0.3', Fraction(-1, 20)), ('0.4', Fraction(0))])
async def test_negative_and_unchanged_history_are_not_missing(tmp_path, price, change):
    quote = await prepared(tmp_path, bid_price=price)
    result = project(tmp_path, quote)
    assert result['history_state'] == 'observed'
    assert fraction(result['history']['midpoint_change']) == change
