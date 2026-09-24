"""Exact snapshot candidate components; no dense-window or admission claims."""

from decimal import Decimal
from fractions import Fraction
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _strict_json
from astrolabe.feature_store.source_parsers import clob_book
from astrolabe.feature_store.types import exact_decimal

from .quote_inputs import _raw, project_quote_inputs

VERSION = 'fs2-book-snapshot-primitives-v1'
LIMITS = {'max_levels_per_book': 10000, 'max_coefficient_digits': 256,
          'max_absolute_exponent': 256}
UNITS = {'price': 'source_local_price_per_share', 'size': 'shares',
         'notional': 'source_local_price_times_shares', 'ratio': 'dimensionless',
         'collateral_identity': 'unresolved'}


def _number(value):
    number = exact_decimal(value)
    parts = number.as_tuple()
    if (len(parts.digits) > LIMITS['max_coefficient_digits']
            or abs(parts.exponent) > LIMITS['max_absolute_exponent']):
        raise ValueError('snapshot arithmetic budget exceeded; raw source retained')
    return Fraction(number)


def _ratio(value):
    """A reduced rational is authoritative; no rounded decimal masquerades as exact."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    decimal = None
    if denominator == 1:
        places = max(twos, fives)
        coefficient = value.numerator * 2 ** (places - twos) * 5 ** (places - fives)
        decimal = str(Decimal((int(coefficient < 0),
                              tuple(int(c) for c in str(abs(coefficient))), -places)))
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator),
            'decimal': decimal,
            'decimal_state': 'exact' if decimal is not None else 'nonterminating_decimal'}


def _arithmetic(quote, book):
    bid, ask, bid_size, ask_size = [_number(quote[k]) for k in
                                    ('bid', 'ask', 'bid_size', 'ask_size')]
    levels = {}
    for side in ('bids', 'asks'):
        levels[side] = [{**level, 'notional': _ratio(_number(level['price'])
                                                    * _number(level['size']))}
                        for level in book[side]]
    total = bid_size + ask_size
    imbalance = (bid_size - ask_size) / total
    midpoint = (bid + ask) / 2
    microprice = (ask * bid_size + bid * ask_size) / total
    return {'levels': levels,
            'intermediates': {k: _ratio(v) for k, v in {
                'midpoint': midpoint, 'spread': ask - bid,
                'size_difference': bid_size - ask_size, 'total_best_size': total,
                'microprice_numerator': ask * bid_size + bid * ask_size,
                'microprice': microprice}.items()},
            'components': {'F08_snapshot': _ratio(imbalance),
                           'F09_snapshot': _ratio(microprice - midpoint)}}


def project_book_primitives(observations, *, policy, cutoff):
    """Pure candidate arithmetic. A later durable consumer must authenticate every input.

    Source receipt freshness is not venue age; a snapshot is not a continuous window.
    Values do not become model-ready features simply by calling this function.
    """
    rows = list(islice(observations, 11))
    quotes = project_quote_inputs(rows, policy=policy, cutoff=cutoff)
    by_id = {row['id']: row for row in rows}
    snapshots = []
    for quote in quotes['quotes']:
        record = {'quote': quote, 'state': quote['state'], 'levels': None,
                  'components': None, 'intermediates': None,
                  'native_book_age': None, 'tick_size': None,
                  'source_timestamp_raw': None, 'source_book_hash_raw': None,
                  'continuous_window_eligible': False,
                  'missing_fields': {'native_book_age': 'unavailable',
                                     'tick_size': 'unavailable'}}
        source = by_id[quote['observation_id']]
        if source['missing_reason'] == 'observed':
            book = clob_book(_strict_json(_raw(source)),
                             expected_token=source['request_metadata']['request']['params']['token_id'])
            record.update(source_timestamp_raw=book['timestamp_raw'],
                          source_book_hash_raw=book['native_hash'])
            if sum(len(book[side]) for side in ('bids', 'asks')) > LIMITS['max_levels_per_book']:
                record['state'] = 'numerical_budget_exceeded'
            else:
                # Original source ordering/strings and zero-size levels remain visible even
                # when the snapshot cannot supply candidate numerical components.
                record['levels'] = {side: book[side] for side in ('bids', 'asks')}
                if quote['state'] == 'observed':
                    try:
                        record.update(_arithmetic(quote, book))
                    except ValueError:
                        record['state'] = 'numerical_budget_exceeded'
        for field in ('levels', 'components', 'intermediates'):
            if record[field] is None:
                record['missing_fields'][field] = record['state']
        snapshots.append(record)
    result = {'schema_version': VERSION, 'limits': dict(LIMITS), 'units': dict(UNITS),
              'quote_projection_hash': quotes['projection_hash'], 'policy': quotes['policy'],
              'cutoff': quotes['cutoff'], 'source_inventory': quotes['source_inventory'],
              'snapshots': snapshots, 'clock_basis': 'receipt', 'native_clock_admitted': False,
              'provenance_class': quotes['provenance_class'],
              'runtime_source_verification_required': True, 'durable_computation_required': True,
              'origin_admitted': False, 'feature_store_admitted': False,
              'registered_window_features_available': False, 'economic_value_claim': False}
    return {**result, 'projection_hash': content_hash(result)}
