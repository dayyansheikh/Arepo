"""Synthetic quote/identity projections; no actual source or origin evidence."""

import base64
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import localcontext
from itertools import repeat

import pytest

from astrolabe.feature_store.capture import _digest
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy, project_quote_inputs

AT = datetime(2026, 9, 22, 8, tzinfo=UTC)
CONDITION = '0x' + 'a' * 64
POLICY = QuoteInputPolicy(10, 60)


def row(i, source, payload, received, **changes):
    raw = json.dumps(payload).encode()
    return {'id': f'{i:064x}', 'source_id': source,
            'first_received_at': AT + timedelta(seconds=received),
            'available_to_model_at': AT + timedelta(seconds=received + 1),
            'payload_hash': _digest(raw), 'payload_encoding': 'base64',
            'raw_payload_inline': base64.b64encode(raw).decode(), 'missing_reason': 'observed',
            'provenance_class': 'synthetic',
            'request_metadata': {'request': {'params': {'token_id': '1'}}}, **changes}


def gamma(i=1, received=-60, **changes):
    body = {'id': 'market', 'conditionId': CONDITION, 'clobTokenIds': '["1","2"]',
            'outcomes': '["Yes","No"]', **changes}
    return row(i, 'gamma.markets', [body], received)


def book(i=2, received=-10, **changes):
    body = {'asset_id': '1', 'market': CONDITION,
            'bids': [{'price': '0.10', 'size': '0'}, {'price': '0.400', 'size': '2.00'},
                     {'price': '0.3', 'size': '3'}],
            'asks': [{'price': '0.9', 'size': '4'}, {'price': '0.600', 'size': '5.00'}],
            **changes}
    return row(i, 'clob.book', body, received)


def project(rows, policy=POLICY):
    return project_quote_inputs(rows, policy=policy, cutoff=AT)


def test_quote_exactness_unsorted_levels_and_known_identity():
    rows = [gamma(), book()]
    result = project(rows)
    assert result == project(reversed(rows))
    quote = result['quotes'][0]
    assert quote['state'] == 'observed'
    assert tuple(quote[k] for k in ('bid', 'ask', 'bid_size', 'ask_size', 'midpoint')) == (
        '0.400', '0.600', '2.00', '5.00', '0.500',
    )
    assert quote['mapping']['outcome_index'] == 0
    assert quote['mapping']['outcome_label'] == 'Yes'
    assert quote['mapping']['economic_group_status'] == 'unresolved'
    assert result['durable_computation_required'] is True
    assert result['runtime_source_verification_required'] is True
    assert result['origin_admitted'] is result['feature_store_admitted'] is False


def test_late_identity_never_repairs_an_earlier_book():
    result = project([gamma(received=-5), book()])
    assert result['quotes'][0]['state'] == 'identity_unresolved_at_receipt'
    assert result['quotes'][0]['midpoint'] is None
    assert len(result['source_inventory']) == 2


def test_future_mapping_revision_is_not_used_and_conflicting_known_mapping_is_ambiguous():
    later = gamma(i=3, received=-5, outcomes='["Changed","No"]')
    earlier = gamma(i=3, received=-20, outcomes='["Changed","No"]')
    assert project([gamma(), book(), later])['quotes'][0]['state'] == 'observed'
    assert project([gamma(), book(), earlier])['quotes'][0]['state'] == (
        'identity_ambiguous_or_conflicting'
    )
    assert project([gamma(conditionId='0x' + 'b' * 64), book()])['quotes'][0]['state'] == (
        'identity_ambiguous_or_conflicting'
    )


def test_repeated_identical_mapping_uses_latest_known_receipt_without_duplicating_quote():
    result = project([gamma(), gamma(i=3, received=-20), book()])
    assert len(result['quotes']) == 1
    assert result['quotes'][0]['mapping']['observation_id'] == f'{3:064x}'


@pytest.mark.parametrize('changes,state', [
    ({'bids': []}, 'one_sided_or_missing'),
    ({'asks': [{'price': '0.2', 'size': '1'}]}, 'invalid_or_crossed'),
    ({'bids': [{'price': '0.4', 'size': '1'}, {'price': '0.4', 'size': '2'}]},
     'duplicate_price_level'),
])
def test_invalid_books_are_preserved_without_midpoints(changes, state):
    result = project([gamma(), book(**changes)])
    assert result['quotes'][0]['state'] == state
    assert result['quotes'][0]['midpoint'] is None
    assert len(result['source_inventory']) == 2


def test_receipt_and_identity_freshness_have_exact_inclusive_boundaries():
    assert project([gamma(), book()])['quotes'][0]['state'] == 'observed'
    assert project([gamma(received=-60.000001), book()])['quotes'][0]['state'] == 'identity_stale'
    assert project([gamma(), book(received=-10.000001)])['quotes'][0]['state'] == 'receipt_stale'
    state = project([gamma(), book()], replace(POLICY, max_identity_age_seconds=59))
    assert state['quotes'][0]['midpoint'] is None


def test_exact_tiny_component_survives_ambient_decimal_precision():
    small = book(bids=[{'price': '0.000000000000000000000000000001', 'size': '1'}],
                 asks=[{'price': '1', 'size': '1'}])
    with localcontext() as context:
        context.prec = 2
        result = project([gamma(), small])
    assert result['quotes'][0]['midpoint'] == '0.5000000000000000000000000000005'


def test_failed_sources_and_trades_preserved_without_price_fallback():
    failed_gamma = {**gamma(), 'missing_reason': 'source_error'}
    failed_book = {**book(), 'missing_reason': 'rate_limited'}
    trade = row(3, 'data.v2.trades', {'price': '0.99'}, -5)
    result = project([failed_gamma, failed_book, trade])
    assert len(result['source_inventory']) == 3
    assert result['quotes'][0]['state'] == 'rate_limited'
    assert result['quotes'][0]['midpoint'] is None
    assert project([failed_gamma, book()])['quotes'][0]['state'] == 'identity_unresolved_at_receipt'


@pytest.mark.parametrize('changes', [
    {'available_to_model_at': AT + timedelta(seconds=1)},
    {'first_received_at': AT}, {'payload_hash': '0' * 64}, {'payload_encoding': 'wrong'},
    {'provenance_class': 'reconstructed'}, {'provenance_class': 'prospective'},
    {'source_id': 'coinbase.btc_usd.ticker'}, {'missing_reason': 'flat'},
    {'raw_payload_inline': 'bad-base64'},
])
def test_future_mixed_provenance_and_invalid_sources_refused(changes):
    with pytest.raises(ValueError):
        project([gamma(), {**book(), **changes}])


def test_duplicate_unbounded_empty_and_oversized_inputs_refused():
    with pytest.raises(ValueError, match='duplicate'):
        project([gamma(), gamma()])
    for rows in ([], repeat(book())):
        with pytest.raises(ValueError, match='at-most-ten'):
            project(rows)
    with pytest.raises(ValueError, match='bounded source payload'):
        project([{**book(), 'raw_payload_inline': 'a' * (2 * 1048576)}])


@pytest.mark.parametrize('changes', [
    {'max_receipt_age_seconds': True}, {'max_identity_age_seconds': -1},
    {'max_receipt_age_seconds': 604801}, {'version': 'unknown'},
])
def test_explicit_policy_bounds(changes):
    with pytest.raises(ValueError):
        replace(POLICY, **changes)


def test_projection_hash_binds_freshness_and_all_source_missingness():
    rows = [gamma(), book()]
    assert project(rows)['projection_hash'] != project(
        rows, replace(POLICY, max_receipt_age_seconds=11),
    )['projection_hash']
    assert project(rows)['projection_hash'] != project(
        rows + [row(3, 'data.v2.trades', {}, -5, missing_reason='source_error')],
    )['projection_hash']


@pytest.mark.asyncio
async def test_projection_consumes_exact_durable_source_read_format(tmp_path):
    import httpx

    from astrolabe.feature_store.source_run import SourceRun, _pair
    from astrolabe.research_panel.input_read import record_input_read

    class Stream(httpx.AsyncByteStream):
        def __init__(self, raw):
            self.raw = raw

        async def __aiter__(self):
            yield self.raw

    def handler(request):
        fixture = gamma() if request.url.path == '/markets' else book()
        return httpx.Response(200, stream=Stream(base64.b64decode(fixture['raw_payload_inline'])))

    source = tmp_path.resolve() / 'fs2_capture_quote_inputs'
    run = SourceRun(source, transport=httpx.MockTransport(handler))
    await run.fetch('gamma.markets', {'limit': 1, 'active': 'true', 'closed': 'false'})
    await run.fetch('clob.book', {'token_id': '1'})
    target = tmp_path.resolve() / 'fs2_input_read_quote_inputs'
    record_input_read(source, output_root=target)
    facts, _ = _pair(target, 'read_facts')
    rows = [r for k, r in facts['source_projection']['rows'] if k == 'source_observation']
    result = project_quote_inputs(rows, policy=QuoteInputPolicy(60, 60), cutoff=datetime.now(UTC))
    assert result['quotes'][0]['state'] == 'observed'
    assert result['quotes'][0]['midpoint'] == '0.500'
    assert result['provenance_class'] == 'synthetic'
