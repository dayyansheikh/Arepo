"""Frozen target identity and availability; synthetic evidence only."""

from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
from itertools import repeat

import pytest

from astrolabe.feature_store.sources import SOURCES
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy, project_quote_inputs
from astrolabe.research_panel.target_adapter import adapt_target_quote
from astrolabe.research_panel.targets import Quote, select_target
from tests.unit.test_research_panel_quote_inputs import AT, CONDITION, book, row

POLICY = QuoteInputPolicy(120, 200)


def identity(i, received, **changes):
    value = {'id': '1', 'conditionId': CONDITION, 'clobTokenIds': '["1","2"]',
             'outcomes': '["Yes","No"]', 'active': True, 'closed': False,
             'archived': False, 'acceptingOrders': True, **changes}
    return row(i, 'gamma.market', value, received, request_metadata={
        'request': SOURCES['gamma.market'].request({'market_id': '1'})})


def quote_row(i, received, **changes):
    return {**book(i, received, **changes), 'request_metadata': {
        'request': SOURCES['clob.book'].request({'token_id': '1'})}}


def origin():
    return project_quote_inputs([identity(1, -60), quote_row(2, -10)], policy=POLICY,
                                cutoff=AT)['quotes'][0]


def adapt(rows=None, *, available=64, policy=POLICY, frozen=None):
    rows = rows or [identity(3, 60), quote_row(4, 62)]
    projection = project_quote_inputs(rows, policy=policy, cutoff=AT + timedelta(seconds=63))
    return adapt_target_quote(frozen or origin(), origin_at=AT, source_rows=rows,
        projection=projection, computation_available_at=AT + timedelta(seconds=available))


def choose(adaptations, as_of=70):
    return select_target([Quote(**a['quote']) for a in adaptations], token_id='1',
        origin_at=AT, origin_persisted_at=AT + timedelta(seconds=1),
        horizon_seconds=60, tolerance_seconds=5, as_of=AT + timedelta(seconds=as_of))


def test_new_identity_clock_stays_separate_from_frozen_identity_and_computation_clock():
    result = adapt()
    q = result['quote']
    assert q['mapping_available_at'] == AT - timedelta(seconds=59)
    assert result['fresh_mapping']['available_at'] == AT + timedelta(seconds=61)
    assert q['received_at'] == AT + timedelta(seconds=62)
    assert q['available_at'] == AT + timedelta(seconds=64)
    assert q['source_status'] == result['original_state'] == 'observed'
    assert choose([result])['selected']['midpoint'] == '0.500'
    assert choose([result])['selected']['delay_seconds'] == '2'
    assert result['origin_admitted'] is result['economic_value_claim'] is False
    assert adapt() == result


@pytest.mark.parametrize('changes', [
    {'description': 'changed rules'}, {'outcomes': '["Changed","No"]'},
    {'clobTokenIds': '["2","1"]'}, {'conditionId': '0x' + 'b' * 64},
])
def test_changed_identity_cannot_become_a_price_or_censoring_event(changes):
    result = adapt([identity(3, 60, closed=True, **changes), quote_row(4, 62)])
    assert result['quote']['source_status'] in {
        'identity_changed_since_origin', 'identity_ambiguous_or_conflicting'}
    chosen = choose([result])
    assert chosen['status'] == 'unavailable' and chosen['censoring_observation_id'] is None
    assert chosen['exclusions'][0]['reason'] == result['quote']['source_status']


@pytest.mark.parametrize('changes,state', [
    ({'closed': True}, 'closed'), ({'archived': True}, 'market_archived'),
    ({'active': False}, 'market_not_accepting_orders'),
    ({'acceptingOrders': False}, 'market_not_accepting_orders'),
    ({'active': None}, 'market_lifecycle_unknown'),
])
def test_lifecycle_states_are_explicit(changes, state):
    result = adapt([identity(3, 60, **changes), quote_row(4, 62)])
    assert result['quote']['source_status'] == state
    assert choose([result])['status'] == ('closed' if state == 'closed' else 'unavailable')


@pytest.mark.parametrize('status', ['rate_limited', 'permission_denied', 'invalid',
                                   'transport_gap', 'source_error'])
def test_failed_book_uses_requested_token_and_keeps_quality(status):
    result = adapt([identity(3, 60), {**quote_row(4, 62), 'missing_reason': status}])
    assert result['fresh_mapping'] is None
    assert result['quote']['token_id'] == '1'
    assert result['quote']['source_status'] == status
    assert result['quote']['bid'] is None
    assert choose([result])['exclusions'] == [{'observation_id': f'{4:064x}', 'reason': status}]


def test_failed_identity_does_not_fall_back_to_old_mapping_as_current_confirmation():
    result = adapt([{**identity(3, 60), 'missing_reason': 'source_error'}, quote_row(4, 62)])
    assert result['quote']['source_status'] == 'identity_unresolved_at_receipt'
    assert choose([result])['status'] == 'unavailable'


@pytest.mark.parametrize('changes,state', [
    ({'bids': []}, 'one_sided_or_missing'),
    ({'bids': [{'price': '0.8', 'size': '1'}]}, 'invalid_or_crossed'),
    ({'bids': [{'price': '0.4', 'size': '1'}, {'price': '0.4', 'size': '1'}]},
     'duplicate_price_level'),
])
def test_bad_book_stays_excluded(changes, state):
    result = adapt([identity(3, 60), quote_row(4, 62, **changes)])
    assert result['quote']['source_status'] == state
    assert choose([result])['exclusions'][0]['reason'] == state


@pytest.mark.parametrize('policy,state', [
    (QuoteInputPolicy(2, 200), 'receipt_stale'),
    (QuoteInputPolicy(120, 4), 'identity_stale'),
])
def test_durable_availability_rechecks_freshness_including_closure(policy, state):
    result = adapt([identity(3, 60, closed=True), quote_row(4, 62)], available=65, policy=policy)
    assert result['original_state'] == 'market_closed'
    assert result['quote']['source_status'] == state
    assert choose([result])['status'] == 'unavailable'


def test_earlier_delayed_computation_blocks_later_price_and_never_rewrites_receipt():
    early = adapt(available=80)
    later = deepcopy(adapt())
    later['quote'].update(observation_id='5' * 64, received_at=AT + timedelta(seconds=64),
                           available_at=AT + timedelta(seconds=65), bid='0.8', ask='0.9')
    waiting = choose([early, later])
    assert waiting['status'] == 'pending' and waiting['selected'] is None
    assert waiting['blocking_observation_id'] == f'{4:064x}'
    completed = choose([early, later], as_of=81)
    assert completed['selected']['observation_id'] == f'{4:064x}'
    assert completed['selected']['midpoint'] == '0.500'


@pytest.mark.parametrize('change', ['projection', 'request', 'provenance', 'cutoff',
                                    'origin_state', 'origin_mapping', 'origin_midpoint'])
def test_unbound_changed_or_noncausal_inputs_refused(change):
    rows, frozen = [identity(3, 60), quote_row(4, 62)], origin()
    projection = project_quote_inputs(rows, policy=POLICY, cutoff=AT + timedelta(seconds=63))
    available = AT + timedelta(seconds=64)
    if change == 'projection':
        projection['quotes'][0]['midpoint'] = '0.99'
    elif change == 'request':
        rows[1]['request_metadata']['request']['params']['token_id'] = '2'
    elif change == 'provenance':
        rows[0]['provenance_class'] = 'prospective'
    elif change == 'cutoff':
        available = AT + timedelta(seconds=62)
    elif change == 'origin_state':
        frozen['state'] = 'late_persistence'
    elif change == 'origin_mapping':
        frozen['mapping']['available_at'] = AT + timedelta(seconds=1)
    else:
        frozen['midpoint'] = '0.99'
    with pytest.raises(ValueError):
        adapt_target_quote(frozen, origin_at=AT, source_rows=rows, projection=projection,
                           computation_available_at=available)


def test_bounded_inventory_and_no_mutation():
    rows, frozen = [identity(3, 60), quote_row(4, 62)], origin()
    projection = project_quote_inputs(rows, policy=POLICY, cutoff=AT + timedelta(seconds=63))
    before = deepcopy((rows, frozen, projection))
    adapt(rows, frozen=frozen)
    assert (rows, frozen, projection) == before
    with pytest.raises(ValueError, match='two-request'):
        adapt_target_quote(frozen, origin_at=AT, source_rows=repeat(rows[0]),
                           projection=projection,
                           computation_available_at=AT + timedelta(seconds=64))


def test_exact_small_decimal_survives_adapter_and_low_ambient_precision():
    from decimal import localcontext
    result = adapt([identity(3, 60), quote_row(4, 62,
        bids=[{'price': '0.000000000000000000000000000001', 'size': '1'}],
        asks=[{'price': '1', 'size': '1'}])])
    with localcontext() as ctx:
        ctx.prec = 2
        assert choose([result])['selected']['midpoint'] == '0.5000000000000000000000000000005'


async def test_adapter_consumes_actual_durable_source_and_computation_formats(tmp_path):
    import httpx

    from astrolabe.feature_store.capture import _clock, _json_bytes
    from astrolabe.feature_store.source_bridge import _time
    from astrolabe.feature_store.source_run import TARGETED_POLICY, SourceRun, _pair
    from astrolabe.research_panel.quote_computation import CHILD, record_quote_computation
    from tests.unit.test_feature_store_capture import Stream
    from tests.unit.test_research_panel_frame import market

    def handler(request):
        body = (market(1, active=True, closed=False, archived=False, acceptingOrders=True)
                if request.url.path == '/markets/1' else
                {'asset_id': '2', 'market': '0x' + f'{1:064x}',
                 'bids': [{'price': '0.400', 'size': '1'}],
                 'asks': [{'price': '0.600', 'size': '1'}]})
        return httpx.Response(200, stream=Stream([_json_bytes(body)]))

    async def compute(name):
        source = tmp_path / ('fs2_capture_' + name)
        run = SourceRun(source, transport=httpx.MockTransport(handler),
                        policy_version=TARGETED_POLICY['version'], retained_bytes=1048576)
        await run.fetch('gamma.market', {'market_id': '1'})
        await run.fetch('clob.book', {'token_id': '2'})
        output = tmp_path / ('fs2_quote_computation_' + name)
        summary = record_quote_computation(source, output_root=output,
            policy=QuoteInputPolicy(60, 60), storage_profile='compact-v1')
        facts, _ = _pair(output, 'quote_facts')
        inputs, _ = _pair(output / CHILD, 'read_facts')
        return summary, facts['projection'], [r for k, r in inputs['source_projection']['rows']
                                             if k == 'source_observation']
    _, first, _ = await compute('origin')
    frozen_at = _time(_clock())
    second, projection, rows = await compute('target')
    result = adapt_target_quote(first['quotes'][0], origin_at=frozen_at, source_rows=rows,
        projection=projection, computation_available_at=_time(second['computation_available_at']))
    assert result['quote']['source_status'] == 'observed'
    assert result['quote']['token_id'] == '2'
    assert result['quote']['mapping_available_at'] < frozen_at
    assert result['fresh_mapping'] != result['frozen_mapping']
    assert asdict(Quote(**result['quote'])) == result['quote']
