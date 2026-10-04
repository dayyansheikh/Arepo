"""Snapshot components keep exact algebra and never imply complete window coverage."""

from copy import deepcopy
from datetime import timedelta
from decimal import localcontext
from fractions import Fraction
from itertools import repeat

import pytest

from astrolabe.research_panel.book_primitives import project_book_primitives
from tests.unit.test_research_panel_quote_inputs import AT, POLICY, book, gamma, row


def project(rows):
    return project_book_primitives(rows, policy=POLICY, cutoff=AT)


def ratio(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def test_exact_components_preserve_every_level_and_repeating_ratios():
    rows = [gamma(), book()]
    before = deepcopy(rows)
    result = project(rows)
    snap = result['snapshots'][0]
    assert result == project(reversed(rows)) and rows == before
    assert snap['state'] == 'observed'
    assert ratio(snap['components']['F08_snapshot']) == Fraction(-3, 7)
    assert ratio(snap['components']['F09_snapshot']) == Fraction(-3, 70)
    assert snap['components']['F08_snapshot']['decimal'] is None
    assert snap['components']['F08_snapshot']['decimal_state'] == 'nonterminating_decimal'
    assert [v['price_raw'] for v in snap['levels']['bids']] == ['0.10', '0.400', '0.3']
    assert snap['levels']['bids'][1]['size_raw'] == '2.00'
    assert ratio(snap['levels']['bids'][0]['notional']) == 0
    assert ratio(snap['levels']['bids'][1]['notional']) == Fraction(4, 5)
    assert snap['continuous_window_eligible'] is False
    assert snap['native_book_age'] is snap['tick_size'] is None
    assert result['origin_admitted'] is result['feature_store_admitted'] is False
    assert result['registered_window_features_available'] is False
    assert result['durable_computation_required'] is True
    assert result['units']['collateral_identity'] == 'unresolved'


def test_positive_one_third_and_microprice_algebra_at_low_decimal_precision():
    with localcontext() as ctx:
        ctx.prec = 2
        snap = project([gamma(), book(bids=[{'price': '0.4', 'size': '2'}],
                                     asks=[{'price': '0.6', 'size': '1'}])])['snapshots'][0]
    values = snap['components']
    assert ratio(values['F08_snapshot']) == Fraction(1, 3)
    assert ratio(values['F09_snapshot']) == Fraction(1, 30)
    assert ratio(values['F09_snapshot']) == (
        ratio(snap['intermediates']['spread']) * ratio(values['F08_snapshot']) / 2)
    assert snap['intermediates']['midpoint']['decimal'] == '0.5'
    assert snap['intermediates']['total_best_size']['decimal'] == '3'


def test_locked_book_and_equal_sizes_have_observed_zero_components():
    snap = project([gamma(), book(bids=[{'price': '0.5', 'size': '1'}],
                                 asks=[{'price': '0.5', 'size': '1'}])])['snapshots'][0]
    assert snap['state'] == 'observed'
    for value in snap['components'].values():
        assert value == {'numerator': '0', 'denominator': '1', 'decimal': '0',
                         'decimal_state': 'exact'}


@pytest.mark.parametrize('changes,state', [
    ({'bids': []}, 'one_sided_or_missing'),
    ({'bids': [{'price': '0.4', 'size': '0'}]}, 'one_sided_or_missing'),
    ({'asks': [{'price': '0.2', 'size': '1'}]}, 'invalid_or_crossed'),
    ({'bids': [{'price': '0.4', 'size': '1'}, {'price': '0.4', 'size': '2'}]},
     'duplicate_price_level'),
])
def test_invalid_book_keeps_levels_but_does_not_make_zero_features(changes, state):
    snap = project([gamma(), book(**changes)])['snapshots'][0]
    assert snap['state'] == state
    assert snap['components'] is snap['intermediates'] is None
    assert snap['levels'] is not None


@pytest.mark.parametrize('identity,quote,state', [
    (gamma(received=-5), book(), 'identity_unresolved_at_receipt'),
    (gamma(received=-61), book(), 'identity_stale'),
    (gamma(), book(received=-11), 'receipt_stale'),
    (gamma(conditionId='0x' + 'b' * 64), book(), 'identity_ambiguous_or_conflicting'),
])
def test_causal_identity_and_freshness_are_not_repaired(identity, quote, state):
    snap = project([identity, quote])['snapshots'][0]
    assert snap['state'] == state and snap['components'] is None


def test_failed_source_keeps_inventory_and_no_trade_price_fallback():
    quote = {**book(), 'missing_reason': 'rate_limited'}
    trade = row(3, 'data.v2.trades', {'price': '0.99'}, -5)
    result = project([gamma(), quote, trade])
    assert len(result['source_inventory']) == 3
    snap = result['snapshots'][0]
    assert snap['state'] == 'rate_limited'
    assert snap['levels'] is snap['components'] is None


@pytest.mark.parametrize('size', ['1e999999999', '1e-257', '9' * 257])
def test_numeric_expansion_is_bounded_without_losing_raw_source(size):
    rows = [gamma(), book(bids=[{'price': '0.4', 'size': size}])]
    before = deepcopy(rows)
    snap = project(rows)['snapshots'][0]
    assert snap['state'] == 'numerical_budget_exceeded'
    assert snap['quote']['state'] == 'observed'
    assert snap['components'] is None and rows == before
    assert snap['levels']['bids'][0]['size_raw'] == size


def test_tiny_component_and_raw_trailing_zeroes_survive():
    tiny = '0.' + '0' * 99 + '1'
    snap = project([gamma(), book(bids=[{'price': tiny, 'size': '2.00'}],
                                 asks=[{'price': '1', 'size': '1'}])])['snapshots'][0]
    assert snap['state'] == 'observed'
    assert ratio(snap['intermediates']['midpoint']) == (Fraction(tiny) + 1) / 2
    assert snap['levels']['bids'][0]['price_raw'] == tiny
    assert snap['levels']['bids'][0]['size_raw'] == '2.00'


def test_level_budget_retains_quote_and_inventory_without_truncating_levels():
    many = [{'price': '0.4', 'size': '1'}] * 10001
    result = project([gamma(), book(bids=many)])
    snap = result['snapshots'][0]
    assert snap['state'] == 'numerical_budget_exceeded'
    assert snap['quote']['state'] == 'duplicate_price_level'
    assert snap['levels'] is snap['components'] is None
    assert len(result['source_inventory']) == 2


@pytest.mark.parametrize('rows', [[], repeat(book()), [gamma(), gamma()],
    [gamma(), {**book(), 'available_to_model_at': AT + timedelta(seconds=1)}]])
def test_empty_unbounded_duplicate_and_future_inputs_refused(rows):
    with pytest.raises(ValueError):
        project(rows)


@pytest.mark.parametrize('lifecycle,state', [
    ({'active': True, 'closed': True, 'archived': False, 'acceptingOrders': False},
     'market_closed'),
    ({'active': True, 'closed': False, 'archived': False, 'acceptingOrders': None},
     'market_lifecycle_unknown'),
    ({'active': False, 'closed': False, 'archived': False, 'acceptingOrders': False},
     'market_not_accepting_orders'),
])
def test_targeted_lifecycle_stays_an_abstention(lifecycle, state):
    from astrolabe.feature_store.sources import SOURCES
    from tests.unit.test_research_panel_quote_inputs import CONDITION
    identity = row(1, 'gamma.market', {
        'id': '1', 'conditionId': CONDITION, 'clobTokenIds': ['1', '2'],
        'outcomes': ['Yes', 'No'], **lifecycle}, -60,
        request_metadata={'request': SOURCES['gamma.market'].request({'market_id': '1'})})
    snap = project([identity, book()])['snapshots'][0]
    assert snap['state'] == state and snap['components'] is None


def test_native_timestamp_and_hash_are_preserved_without_inferred_age():
    snap = project([gamma(), book(timestamp='999999999999999999999',
                                 hash='venue-opaque-hash')])['snapshots'][0]
    assert snap['source_timestamp_raw'] == '999999999999999999999'
    assert snap['source_book_hash_raw'] == 'venue-opaque-hash'
    assert snap['native_book_age'] is None


def test_returned_metadata_cannot_change_future_arithmetic_limits_or_units():
    first = project([gamma(), book()])
    expected = deepcopy(first)
    first['limits']['max_absolute_exponent'] = 999999999
    first['units']['collateral_identity'] = 'invented'
    assert project([gamma(), book()]) == expected
