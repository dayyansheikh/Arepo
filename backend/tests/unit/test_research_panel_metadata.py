"""Projection fixtures are synthetic; no retrospective availability is inferred."""

import copy
from decimal import Decimal

import pytest

from astrolabe.research_panel.metadata import project_metadata


def test_exact_values_first_outcome_utc_and_original_row_preserved():
    row = {'category': 'Sports', 'endDate': '2026-09-22T12:00:00+01:00',
           'outcomePrices': '["0.01234567890123456789000","0.9"]',
           'liquidity': '12345678901234567890.00000', 'events': [{'id': '12'}]}
    original = copy.deepcopy(row)
    result = project_metadata(row, outcome_count=2)
    assert result['metadata_probability'] == {
        'value': '0.01234567890123456789000', 'state': 'present'}
    assert result['liquidity']['value'] == '12345678901234567890.00000'
    assert result['close_time_utc']['value'] == '2026-09-22T11:00:00.000000Z'
    assert result['economic_event_group'] is None and not result['origin_admitted']
    assert row == original


def test_missing_fields_do_not_borrow_alternate_values_or_exclude_markets():
    result = project_metadata({'liquidityNum': 42, 'sportsMarketType': 'soccer',
                               'bestBid': '0.2', 'bestAsk': '0.3',
                               'endDateIso': '2026-09-23'}, outcome_count=2)
    for key in ('category', 'close_time_utc', 'metadata_probability', 'liquidity'):
        assert result[key] == {'value': None, 'state': 'missing'}
    assert 'eligible' not in result


@pytest.mark.parametrize('value', [0.2, True, 'NaN', 'Infinity', '-0.1', '1.01', 'bad'])
def test_invalid_probability_never_coerced_or_replaced_with_other_outcome(value):
    result = project_metadata({'outcomePrices': [value, '0.5']}, outcome_count=2)
    assert result['metadata_probability'] == {'value': None, 'state': 'invalid'}


@pytest.mark.parametrize('prices', ['["0.2"]', '["0.2","0.8","0.9"]', 'null', '{}', 'bad'])
def test_price_array_requires_exact_mapping_length(prices):
    assert project_metadata({'outcomePrices': prices}, outcome_count=2)[
        'metadata_probability']['state'] == 'invalid'


@pytest.mark.parametrize('end', ['2026-09-22', '2026-09-22T10:00:00', 'bad', 1790020000])
def test_missing_timezone_never_assumed_utc(end):
    assert project_metadata({'endDate': end}, outcome_count=2)['close_time_utc'] == {
        'value': None, 'state': 'invalid'}


def test_decimal_array_and_zero_are_exact_and_present():
    result = project_metadata({'outcomePrices': [Decimal('0.000'), Decimal('1.000')],
                               'liquidity': 0}, outcome_count=2)
    assert result['metadata_probability'] == {'value': '0.000', 'state': 'present'}
    assert result['liquidity'] == {'value': '0', 'state': 'present'}


def test_invalid_category_and_liquidity_are_not_absence_or_zero():
    result = project_metadata({'category': ['Sports'], 'liquidity': -1}, outcome_count=2)
    assert result['category'] == result['liquidity'] == {'value': None, 'state': 'invalid'}


@pytest.mark.parametrize('count', [0, True, 1001])
def test_invalid_identity_count_is_refused(count):
    with pytest.raises(ValueError, match='validated outcome count'):
        project_metadata({}, outcome_count=count)
