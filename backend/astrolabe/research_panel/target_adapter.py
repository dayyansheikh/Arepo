"""Pure target adaptation; durable journal verification remains the caller's obligation."""

from dataclasses import asdict
from datetime import timedelta
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.sources import SOURCES

from .quote_inputs import QuoteInputPolicy, _at, project_quote_inputs
from .targets import TARGET_ABSTENTIONS, Quote, quote_state

VERSION = 'fs2-frozen-identity-target-adapter-v1'


def _identity(quote):
    mapping = quote['mapping']
    return (quote['token_id'], quote['condition_id'], mapping['market_id'],
            mapping['mapping_version'], mapping['outcome_index'], mapping['outcome_label'])


def adapt_target_quote(origin_quote, *, origin_at, source_rows, projection,
                       computation_available_at):
    """Bind exact known inputs without inventing source clocks or authenticating payloads.

    The future due writer must supply journal-verified facts and persist this result with
    its actual read/computation clocks. This helper's parameters are not an admission API.
    """
    origin_at, available = _at(origin_at), _at(computation_available_at)
    mapping = origin_quote['mapping']
    if (origin_quote['state'] != 'observed' or mapping is None
            or not _at(origin_quote['received_at']) <= origin_at < available
            or not _at(mapping['received_at']) <= _at(mapping['available_at'])
                <= _at(origin_quote['received_at'])
            or _at(origin_quote['source_available_at']) > origin_at):
        raise ValueError('observed causal frozen origin identity required')
    frozen = Quote(origin_quote['observation_id'], origin_quote['token_id'],
                   _at(origin_quote['received_at']), _at(origin_quote['source_available_at']),
                   _at(mapping['available_at']), *[origin_quote[k] for k in
                     ('bid', 'ask', 'bid_size', 'ask_size')])
    state, midpoint = quote_state(frozen)
    if state != 'observed' or str(midpoint) != origin_quote['midpoint']:
        raise ValueError('exact observed origin quote required')
    rows = list(islice(source_rows, 3))
    if len(rows) != 2:
        raise ValueError('exact two-request target inventory required')
    by_source = {r['source_id']: r for r in rows}
    expected = {'gamma.market': {'market_id': mapping['market_id']},
                'clob.book': {'token_id': origin_quote['token_id']}}
    if set(by_source) != set(expected):
        raise ValueError('fixed identity/book target sources required')
    for source, params in expected.items():
        row = by_source[source]
        if (row['request_metadata']['request'] != SOURCES[source].request(params)
                or row['provenance_class'] != origin_quote['provenance_class']
                or _at(row['first_received_at']) < origin_at):
            raise ValueError('target request, provenance or origin chronology differs')
    policy = QuoteInputPolicy(**projection['policy'])
    cutoff = _at(projection['cutoff'])
    if cutoff > available:
        raise ValueError('target computation availability precedes cutoff')
    replay = project_quote_inputs(rows, policy=policy, cutoff=cutoff)
    if _json_bytes(replay) != _json_bytes(projection) or len(replay['quotes']) != 1:
        raise ValueError('target projection replay differs')
    quote = replay['quotes'][0]
    state = quote['state']
    fresh = quote['mapping']
    if fresh is not None:
        if _identity(quote) != _identity(origin_quote):
            state = 'identity_changed_since_origin'
        elif available - _at(fresh['received_at']) > timedelta(
            seconds=policy.max_identity_age_seconds
        ):
            state = 'identity_stale'
        elif available - _at(quote['received_at']) > timedelta(
            seconds=policy.max_receipt_age_seconds
        ):
            state = 'receipt_stale'
        elif state == 'market_closed':
            state = 'closed'
    if state not in TARGET_ABSTENTIONS | {'observed', 'closed'}:
        raise ValueError('unrecognised target projection state')
    # Only request metadata is always present, including failed/empty book responses.
    token = by_source['clob.book']['request_metadata']['request']['params']['token_id']
    adapted = Quote(quote['observation_id'], token, _at(quote['received_at']), available,
                    _at(mapping['available_at']),
                    *[quote[k] for k in ('bid', 'ask', 'bid_size', 'ask_size')],
                    source_status=state)
    result = {'schema_version': VERSION, 'origin_quote_hash': content_hash(origin_quote),
              'origin_at': origin_at, 'projection_hash': projection['projection_hash'],
              'original_quote_hash': content_hash(quote), 'original_state': quote['state'],
              'frozen_mapping': mapping, 'fresh_mapping': fresh,
              'quote': asdict(adapted), 'provenance_class': origin_quote['provenance_class'],
              'clock_basis': 'receipt', 'origin_admitted': False,
              'feature_store_admitted': False, 'economic_value_claim': False}
    return {**result, 'adaptation_hash': content_hash(result)}
