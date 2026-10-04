"""Pure receipt-time quote projection; durable computation/origin admission stays closed."""

import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _digest, _strict_json
from astrolabe.feature_store.source_parsers import clob_book, gamma_identity, gamma_market
from astrolabe.feature_store.sources import SOURCES
from astrolabe.feature_store.types import HASH_PATTERN, utc_datetime

from .targets import Quote, quote_state


@dataclass(frozen=True)
class QuoteInputPolicy:
    max_receipt_age_seconds: int
    max_identity_age_seconds: int
    version: str = 'fs2-receipt-quote-input-policy-v1'

    def __post_init__(self):
        for value in (self.max_receipt_age_seconds, self.max_identity_age_seconds):
            if type(value) is not int or not 0 <= value <= 604800:
                raise ValueError('explicit bounded quote/identity freshness required')
        if self.version != 'fs2-receipt-quote-input-policy-v1':
            raise ValueError('unknown quote input policy')


def _at(value):
    if isinstance(value, dict) and set(value) == {'$utc'}:
        value = value['$utc']
    return utc_datetime(datetime.fromisoformat(value) if isinstance(value, str) else value)


def _raw(row):
    encoded = row['raw_payload_inline']
    if not isinstance(encoded, str) or len(encoded) > 4 * ((1048576 + 2) // 3):
        raise ValueError('bounded source payload required')
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > 1048576 or _digest(raw) != row['payload_hash']:
        raise ValueError('source payload hash/size differs')
    return raw


def project_quote_inputs(observations, *, policy, cutoff):
    """No caller assertion here authenticates a source row or actual computation time.

    Durable consumers must obtain these exact rows through verified input-read journals,
    freeze their policy and record actual read/computation/acknowledgement clocks.
    """
    if type(policy) is not QuoteInputPolicy:
        raise ValueError('explicit quote input policy required')
    cutoff = utc_datetime(cutoff)
    rows = list(islice(observations, 11))
    if not 1 <= len(rows) <= 10:
        raise ValueError('nonempty at-most-ten source observations required')
    provenance = {row['provenance_class'] for row in rows}
    if len(provenance) != 1 or not provenance <= {'prospective', 'synthetic'}:
        raise ValueError('one admitted source-run provenance required; no mixed promotion')
    seen, decoded, inventory, total = set(), {}, [], 0
    for row in rows:
        identity = row['id']
        if not isinstance(identity, str) or not HASH_PATTERN.fullmatch(identity):
            raise ValueError('source observation lineage required')
        if identity in seen:
            raise ValueError('duplicate source observation')
        seen.add(identity)
        if row['source_id'] not in {'gamma.market', 'gamma.markets', 'clob.book', 'data.v2.trades'}:
            raise ValueError('source outside admitted input projection')
        if (row['payload_encoding'] != 'base64' or row['missing_reason'] not in {
            'observed', 'permission_denied', 'rate_limited', 'transport_gap',
            'source_error', 'invalid',
        }):
            raise ValueError('admitted source encoding/missingness required')
        received, available = _at(row['first_received_at']), _at(row['available_to_model_at'])
        if not received <= available <= cutoff:
            raise ValueError('source receipt/availability after cutoff or regressed')
        raw = _raw(row)
        total += len(raw)
        if total > 4 * 1048576:
            raise ValueError('total source payload budget exceeded')
        if row['missing_reason'] == 'observed':
            decoded[identity] = _strict_json(raw)
        inventory.append({'observation_id': identity, 'source_id': row['source_id'],
                          'missing_reason': row['missing_reason'],
                          'payload_hash': row['payload_hash'],
                          'received_at': received, 'available_at': available,
                          'provenance_class': row['provenance_class']})
    mappings = []
    for row in rows:
        if row['source_id'] == 'gamma.market' and row['id'] in decoded:
            target = SOURCES['gamma.market'].market_request_id(row['request_metadata']['request'])
            mappings.append((gamma_market(decoded[row['id']], expected_market=target), row))
        if row['source_id'] == 'gamma.markets' and row['id'] in decoded:
            values = decoded[row['id']]
            if not isinstance(values, list) or len(values) > 10:
                raise ValueError('bounded Gamma identity response required')
            for value in values:
                mappings.append((gamma_identity(value), row))
    quotes = []
    for row in sorted(rows, key=lambda r: r['id']):
        if row['source_id'] != 'clob.book':
            continue
        received, available = _at(row['first_received_at']), _at(row['available_to_model_at'])
        record = {'observation_id': row['id'], 'received_at': received,
                  'source_available_at': available, 'provenance_class': row['provenance_class'],
                  'state': row['missing_reason'], 'quality_flags': [], 'mapping': None,
                  'bid': None, 'ask': None, 'bid_size': None, 'ask_size': None,
                  'midpoint': None, 'token_id': None, 'condition_id': None}
        if row['missing_reason'] != 'observed':
            quotes.append(record)
            continue
        book = clob_book(decoded[row['id']], expected_token=(
            row['request_metadata']['request']['params']['token_id']
        ))
        record.update(token_id=book['token_id'], condition_id=book['condition_id'],
                      quality_flags=book['quality_flags'])
        for side, field in (('bids', 'bid'), ('asks', 'ask')):
            levels = [v for v in book[side] if v['size'] > 0]
            if levels:
                best = (max if side == 'bids' else min)(levels, key=lambda v: v['price'])
                record[field], record[field + '_size'] = str(best['price']), str(best['size'])
        candidates = [(mapping, src, outcome) for mapping, src in mappings
                      for outcome in mapping['outcomes'] if outcome['token_id'] == book['token_id']
                      and _at(src['available_to_model_at']) <= received]
        versions = {m['mapping_version'] for m, _, _ in candidates}
        if not candidates:
            record['state'] = 'identity_unresolved_at_receipt'
        elif len(versions) != 1 or any(m['condition_id'] != book['condition_id']
                                       for m, _, _ in candidates):
            record['state'] = 'identity_ambiguous_or_conflicting'
        else:
            mapping, src, outcome = max(candidates, key=lambda item: (
                _at(item[1]['available_to_model_at']), item[1]['id'],
            ))
            record['mapping'] = {
                'observation_id': src['id'], 'mapping_version': mapping['mapping_version'],
                'market_id': mapping['market_id'], 'outcome_index': outcome['outcome_index'],
                'outcome_label': outcome['outcome_label'],
                'available_at': _at(src['available_to_model_at']),
                'received_at': _at(src['first_received_at']),
                'identity_status': 'source_local_only', 'economic_group_status': 'unresolved',
            }
            quote = Quote(row['id'], book['token_id'], received, available,
                          _at(src['available_to_model_at']), record['bid'], record['ask'],
                          record['bid_size'], record['ask_size'])
            state, midpoint = quote_state(quote)
            if 'duplicate_price_level' in book['quality_flags']:
                state = 'duplicate_price_level'
            elif cutoff - _at(src['first_received_at']) > timedelta(
                seconds=policy.max_identity_age_seconds
            ):
                state = 'identity_stale'
            elif cutoff - received > timedelta(seconds=policy.max_receipt_age_seconds):
                state = 'receipt_stale'
            if 'lifecycle' in mapping:
                lifecycle = mapping['lifecycle']
                record['mapping']['lifecycle'] = lifecycle
                if lifecycle['closed'] is True:
                    state = 'market_closed'
                elif lifecycle['archived'] is True:
                    state = 'market_archived'
                elif lifecycle['active'] is False or lifecycle['acceptingOrders'] is False:
                    state = 'market_not_accepting_orders'
                elif any(v is None for v in lifecycle.values()):
                    state = 'market_lifecycle_unknown'
            record['state'] = state
            record['midpoint'] = str(midpoint) if state == 'observed' else None
        quotes.append(record)
    result = {'schema_version': 'fs2-receipt-quote-inputs-v1', 'policy': asdict(policy),
              'cutoff': cutoff, 'source_inventory': sorted(inventory,
                                                         key=lambda r: r['observation_id']),
              'quotes': quotes, 'clock_basis': 'receipt', 'native_clock_admitted': False,
              'runtime_source_verification_required': True, 'durable_computation_required': True,
              'origin_admitted': False, 'feature_store_admitted': False,
              'provenance_class': next(iter(provenance)),
              'economic_value_claim': False}
    return {**result, 'projection_hash': content_hash(result)}
