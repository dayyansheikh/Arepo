"""Diagnostic identity binding; observing a book does not make its midpoint available."""

from astrolabe.feature_store.source_run import _pair

from .book_computation import read_book_computation

VERSION = 'fs2-observation-identity-binding-v1'


def read_observation_binding(root):
    """Verify saved inputs without admitting a socket, origin, history or fresh identity.

    The eventual writer must persist actual read clocks and recheck identity/book freshness
    at subscription. This reader deliberately leaves legacy two-sided binding unchanged.
    """
    summary = read_book_computation(root)
    facts, ack = _pair(root, 'book_facts')
    declaration, _ = _pair(root, 'book_policy')
    if ack['payload_hash'] != summary['computation_hash']:
        raise ValueError('pre-window facts changed during read')
    projection = facts['projection']
    inventory = projection['source_inventory']
    if (len(projection['snapshots']) != 1
            or sorted(v['source_id'] for v in inventory) != ['clob.book', 'gamma.market']
            or any(v['missing_reason'] != 'observed' for v in inventory)):
        raise ValueError('one observed targeted identity/book pair required')
    snapshot = projection['snapshots'][0]
    quote = snapshot['quote']
    if (snapshot['state'] != quote['state']
            or quote['state'] not in {'observed', 'one_sided_or_missing'}):
        raise ValueError('valid observed or one-sided source book required')
    mapping = quote['mapping']
    if mapping is None or mapping.get('lifecycle') != {
        'active': True, 'closed': False, 'archived': False, 'acceptingOrders': True,
    }:
        raise ValueError('explicit active source identity required')
    return {
        'schema_version': VERSION, 'pre_computation': summary,
        'pre_source_root': declaration['source_root'],
        'identity': {**{key: mapping[key] for key in ('market_id', 'mapping_version',
                     'outcome_index', 'outcome_label', 'lifecycle')},
                     'token_id': quote['token_id'], 'condition_id': quote['condition_id']},
        'book_received_at': quote['received_at'],
        'identity_received_at': mapping['received_at'],
        'identity_available_at': mapping['available_at'],
        'book_observation_id': quote['observation_id'],
        'identity_observation_id': mapping['observation_id'],
        'pre_quote_state': quote['state'], 'pre_midpoint': quote['midpoint'],
        'requires_actual_subscription_freshness_check': True,
        'origin_admitted': False, 'history_admitted': False, 'socket_admitted': False,
    }
