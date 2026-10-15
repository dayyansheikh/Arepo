"""Bounded origin snapshot manifest; complete windows are never inferred from sparse inputs."""

import time
from datetime import timedelta

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.source_run import _ordered_clocks, _time

from .book_primitives import project_book_primitives
from .origin_window import MAX_BYTES as WINDOW_MAX_BYTES
from .quote_inputs import _at

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


def freeze_eligibility(projection, *, freeze=None):
    """Numerical evidence survives an ineligible origin; values never imply admission."""
    manifest = projection['feature_manifest']
    state = projection['state_at_freeze']
    if state == 'observed':
        state = manifest['snapshot_state']
    manifest['state_at_freeze'] = state
    manifest['snapshot_candidates_eligible_at_freeze'] = state == 'observed'
    if 'pre_origin_window' in projection:
        _freeze_window(projection, freeze, state)
    if len(_json_bytes(manifest)) > POLICY['max_manifest_bytes']:
        raise ValueError('frozen feature manifest byte budget exceeded')


WINDOW_VERSION = 'fs2-origin-window-manifest-v2'
WINDOW_POLICY = {**POLICY, 'version': WINDOW_VERSION,
                 'pre_origin_dependency': 'fs2-origin-window-input-v1'}


def attach_window(projection, window):
    """New explicit manifest version; never retrofit a saved snapshot origin."""
    manifest = projection['feature_manifest']
    manifest['schema_version'] = WINDOW_VERSION
    manifest['policy'] = WINDOW_POLICY
    projection['pre_origin_window'] = window
    manifest['unavailable_families']['price_history'] = {
        'state': 'unavailable', 'reason': 'awaiting_actual_origin_freeze'}
    manifest['pre_origin_window_analysis_hash'] = window['analysis']['computation_hash']
    if len(_json_bytes(manifest)) > POLICY['max_manifest_bytes']:
        raise ValueError('window origin manifest byte budget exceeded')


def _freeze_window(projection, freeze, origin_state):
    window, manifest = projection['pre_origin_window'], projection['feature_manifest']
    if freeze is None or not _ordered_clocks(window['cutoff'], freeze):
        raise ValueError('actual ordered origin freeze required for window eligibility')
    reasons = list(window['history_reasons'])
    if origin_state != 'observed':
        reasons.append('origin_' + origin_state)
    if window['history'] is not None:
        prior_at = _at(window['history']['prior_received_at'])
        if _time(freeze) - prior_at > timedelta(
            milliseconds=window['policy']['max_history_age_ms']
        ):
            reasons.append('prior_quote_stale_at_freeze')
    if _time(freeze) - _time(window['window_ended_at']) > timedelta(
        milliseconds=window['policy']['max_window_age_ms']
    ):
        reasons.append('window_stale_at_freeze')
    window['eligible_at_freeze'] = not reasons and window['history'] is not None
    window['freeze_reasons'] = reasons
    window['frozen_at'] = freeze
    if window['eligible_at_freeze']:
        manifest['price_history'] = window['history']
        manifest['unavailable_families'].pop('price_history', None)
    else:
        manifest.pop('price_history', None)
        manifest['unavailable_families']['price_history'] = {
            'state': 'unavailable', 'reasons': reasons}

    if len(_json_bytes(window)) > WINDOW_MAX_BYTES:
        raise ValueError('frozen origin window manifest byte budget exceeded')
