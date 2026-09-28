"""Bounded origin snapshot manifest; complete windows are never inferred from sparse inputs."""

import time

from astrolabe.feature_store.capture import _json_bytes

from .book_primitives import project_book_primitives

VERSION = 'fs2-origin-snapshot-manifest-v1'
POLICY = {
    'version': VERSION, 'max_manifest_bytes': 16384, 'max_computation_seconds': 30,
    'numerical_recipe': 'fs2-book-snapshot-primitives-v1',
    'full_levels_authority': 'immutable raw source and actual input-read journals',
    'registered_window_features_available': False,
}
UNAVAILABLE = {
    'F01': 'bounded_taker_response_not_complete_fill_window',
    'F02': 'pre_trade_depth_and_fill_order_unverified',
    'F10': 'execution_adjusted_book_deltas_unavailable',
    'F27': 'native_sequence_and_continuous_window_unproven',
    'related_markets': 'economic_relation_and_causal_prices_not_bound',
    'external_information': 'selected_market_source_and_rule_mapping_not_bound',
    'price_history': 'causal_previous_price_not_bound',
}


def project_origin_features(rows, *, policy, cutoff):
    """Pure arithmetic; only the origin writer supplies actual verification/freeze clocks."""
    started = time.monotonic()
    book = project_book_primitives(rows, policy=policy, cutoff=cutoff)
    if len(book['snapshots']) != 1:
        raise ValueError('one origin snapshot required')
    snapshot = book['snapshots'][0]
    quote = snapshot['quote']
    result = {
        'schema_version': VERSION, 'policy': POLICY,
        'computed_cutoff': book['cutoff'], 'book_projection_hash': book['projection_hash'],
        'book_observation_id': quote['observation_id'],
        'input_observation_ids': [row['id'] for row in rows],
        'source_provenance_class': book['provenance_class'],
        'snapshot_state': snapshot['state'], 'units': book['units'],
        'components': snapshot['components'], 'intermediates': snapshot['intermediates'],
        'native_book_age': None, 'continuous_window_eligible': False,
        'raw_trade_observation_ids': [row['id'] for row in rows
                                      if row['source_id'] == 'data.v2.trades'],
        'unavailable_families': {key: {'state': 'unavailable', 'reason': reason}
                                 for key, reason in UNAVAILABLE.items()},
        'validated_predictive_features': False,
    }
    if (len(_json_bytes(result)) > POLICY['max_manifest_bytes']
            or time.monotonic() - started > POLICY['max_computation_seconds']):
        raise ValueError('origin feature manifest numerical/time budget exceeded')
    return result


def freeze_eligibility(projection):
    """Numerical evidence survives an ineligible origin; values never imply admission."""
    manifest = projection['feature_manifest']
    state = projection['state_at_freeze']
    if state == 'observed':
        state = manifest['snapshot_state']
    manifest['state_at_freeze'] = state
    manifest['snapshot_candidates_eligible_at_freeze'] = state == 'observed'
    if len(_json_bytes(manifest)) > POLICY['max_manifest_bytes']:
        raise ValueError('frozen feature manifest byte budget exceeded')
