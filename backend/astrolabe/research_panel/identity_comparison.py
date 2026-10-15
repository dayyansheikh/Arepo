"""Compare authenticated Gamma identities without filling absent event membership."""

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.types import HASH_PATTERN

VERSION = 'fs2-gamma-identity-comparison-v1'
FIELDS = frozenset({
    'venue', 'market_id', 'condition_id', 'question_id', 'question', 'rules_text', 'rules_hash',
    'resolution_source', 'source_event_ids', 'outcomes', 'chain_id', 'token_contract',
    'collateral_address', 'identity_status', 'economic_group_status',
})


def compare_mapping(frame_identity, current_mapping_version):
    """Caller must authenticate the current hash from its raw-backed quote projection.

    Hash comparison proves all other fields equal; it neither refreshes old event IDs nor
    establishes economic independence. Original parser/mapping hashes remain unchanged.
    """
    if not isinstance(frame_identity, dict) or set(frame_identity) != FIELDS | {'mapping_version'}:
        raise ValueError('complete versioned Gamma frame identity required')
    material = {key: frame_identity[key] for key in FIELDS}
    frame_hash = frame_identity['mapping_version']
    events = material['source_event_ids']
    if (not isinstance(events, list) or any(not isinstance(v, str) for v in events)
            or frame_hash != content_hash(material)):
        raise ValueError('frame identity hash or event representation differs')
    if current_mapping_version is not None and (
        not isinstance(current_mapping_version, str)
        or not HASH_PATTERN.fullmatch(current_mapping_version)
    ):
        raise ValueError('authenticated mapping hash or explicit absence required')
    state, core_equal, membership = 'mapping_unavailable', False, 'unavailable'
    if current_mapping_version == frame_hash:
        state, core_equal = 'exact_mapping', True
        membership = 'reported_equal' if events else 'unavailable'
    elif current_mapping_version is not None:
        omitted = {**material, 'source_event_ids': []}
        if events and current_mapping_version == content_hash(omitted):
            state, core_equal = 'core_equal_event_membership_unavailable', True
        else:
            # A differing hash cannot distinguish a core change from changed event IDs.
            state, membership = 'mapping_differs', 'unverified'
    return {
        'schema_version': VERSION, 'frame_mapping_version': frame_hash,
        'current_mapping_version': current_mapping_version, 'state': state,
        'core_identity_equal': core_equal, 'current_event_membership': membership,
        'economic_group_status': 'unresolved', 'admission_decision': False,
    }
