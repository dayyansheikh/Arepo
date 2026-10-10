"""Pure selection metadata projection. No receipt, availability or origin is asserted.

Consumers must bind the original row, validated outcome mapping and actual computation
clocks in a durable journal. Raw source representations remain in that original row.
"""

from datetime import datetime

from astrolabe.feature_store.capture import _strict_json
from astrolabe.feature_store.types import exact_decimal, utc_text

VERSION = 'fs2-gamma-selection-metadata-v1'


def _field(value=None, state='missing'):
    return {'value': value, 'state': state}


def _number(value, *, probability=False):
    if value is None:
        return _field()
    try:
        number = exact_decimal(value)
        if number < 0 or (probability and number > 1):
            raise ValueError('invalid domain')
    except (ValueError, TypeError):
        return _field(state='invalid')
    return _field(str(number), 'present')


def project_metadata(row, *, outcome_count):
    """Project named source fields; never infer absent metadata from similar fields.

    outcome_count must come from the validated source-local identity. Selection always
    refers to the first source-ordered outcome, independently of its metadata price.
    Missing/invalid metadata does not exclude an otherwise eligible market.
    """
    if not isinstance(row, dict):
        raise ValueError('original source row required')
    if type(outcome_count) is not int or not 1 <= outcome_count <= 1000:
        raise ValueError('bounded validated outcome count required')
    category = row.get('category')
    category_field = _field()
    if category is not None:
        category_field = (_field(category, 'present')
                          if isinstance(category, str) and category.strip() and len(category) <= 256
                          else _field(state='invalid'))
    close = row.get('endDate')
    close_field = _field()
    if close is not None:
        try:
            if not isinstance(close, str) or len(close) > 128:
                raise ValueError('explicit timestamp string required')
            close_field = _field(utc_text(datetime.fromisoformat(close)), 'present')
        except ValueError:
            close_field = _field(state='invalid')
    prices = row.get('outcomePrices')
    probability = _field()
    if prices is not None:
        try:
            if isinstance(prices, str):
                if len(prices) > 262144:
                    raise ValueError('bounded price array required')
                prices = _strict_json(prices)
            if not isinstance(prices, list) or len(prices) != outcome_count:
                raise ValueError('price/mapping count differs')
            probability = _number(prices[0], probability=True)
        except (ValueError, TypeError, RecursionError):
            probability = _field(state='invalid')
    return {
        'schema_version': VERSION, 'category': category_field,
        'close_time_utc': close_field, 'metadata_probability': probability,
        'liquidity': _number(row.get('liquidity')),
        'source_fields': {'category': 'category', 'close_time_utc': 'endDate',
                          'metadata_probability': 'outcomePrices[0]', 'liquidity': 'liquidity'},
        'price_semantics': 'Gamma metadata; not CLOB midpoint or executable quote',
        'economic_event_group': None, 'economic_event_group_state': 'unresolved',
        'origin_admitted': False,
    }
