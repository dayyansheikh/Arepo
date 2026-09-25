"""Freeze panel timing/sampling/resource intent before reads; no collector or admission."""

import re
import secrets
import shutil
from dataclasses import asdict, dataclass

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import TARGETED_POLICY, _ordered_clocks, _pair, _persist
from astrolabe.feature_store.types import HASH_PATTERN

from .build_identity import verified_panel_build
from .input_read import _canonical
from .quote_computation import computation_limits
from .sampling import SamplingProtocol

VERSION = 'fs2-panel-declaration-v1'
COMPACT_VERSION = 'fs2-panel-declaration-v2'
MIB = 1048576
FIXED = {'selection_bytes': 1024 * MIB, 'frame_read_bytes': 16 * MIB,
         'declaration_bytes': MIB, 'free_reserve_bytes': 2048 * MIB,
         'max_panel_bytes': 128 * 1024 * MIB}
FAMILIES = {
    'price_context': 'planned_receipt_time_primitives',
    'books': 'planned_snapshot_primitives', 'raw_trades': 'planned_bounded_pages',
    'flow': 'unavailable_until_window_completeness',
    'depth_normalised_flow': 'unavailable_until_pretrade_depth',
    'persistent_imbalance': 'unavailable_until_dense_window',
    'depth_withdrawal': 'unavailable_until_dense_window',
    'related_markets': 'unavailable_until_causal_mapping_and_window',
    'external_information': 'unavailable_until_source_admission',
}


@dataclass(frozen=True)
class PanelProtocol:
    scheduled_slots: int
    triggered_slots: int
    controls_per_trigger: int
    cycles: int
    target_attempts: int
    scheduled_per_stratum: int
    triggered_per_stratum: int
    cadence_seconds: int
    max_origin_delay_seconds: int
    max_origin_save_seconds: int
    horizon_seconds: int
    tolerance_seconds: int
    max_frame_age_seconds: int
    max_frame_interval_seconds: int
    max_quote_age_seconds: int
    max_identity_age_seconds: int
    source_response_bytes: int
    source_run_retained_bytes: int

    def __post_init__(self):
        bounds = {
            'scheduled_slots': (1, 256), 'triggered_slots': (0, 256),
            'controls_per_trigger': (1, 16), 'cycles': (1, 24), 'target_attempts': (1, 16),
            'scheduled_per_stratum': (1, 256), 'triggered_per_stratum': (1, 256),
            'cadence_seconds': (1, 86400), 'max_origin_delay_seconds': (0, 86400),
            'max_origin_save_seconds': (1, 86399), 'horizon_seconds': (2, 86400),
            'tolerance_seconds': (0, 86399), 'max_frame_age_seconds': (1, 604800),
            'max_frame_interval_seconds': (1, 86400), 'max_quote_age_seconds': (0, 604800),
            'max_identity_age_seconds': (0, 604800), 'source_response_bytes': (1, MIB),
            'source_run_retained_bytes': (MIB, 256 * MIB),
        }
        for key, (minimum, maximum) in bounds.items():
            value = getattr(self, key)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError('explicit bounded panel protocol required: ' + key)
        if (self.max_origin_save_seconds >= self.horizon_seconds
                or self.tolerance_seconds >= self.horizon_seconds
                or self.max_origin_delay_seconds >= self.cadence_seconds
                or self.target_attempts > self.tolerance_seconds + 1
                or self.max_frame_interval_seconds > self.max_frame_age_seconds):
            raise ValueError('panel timing bounds are inconsistent')
        if self.scheduled_per_stratum > self.scheduled_slots or (
            self.triggered_slots and self.triggered_per_stratum > self.triggered_slots
        ):
            raise ValueError('per-stratum count exceeds role capacity')
        if self.market_slots > 256 or self.market_slots * self.cycles > 1024:
            raise ValueError('panel origin/market reservation exceeds bounded scope')
        if self.duration_seconds > 86400:
            raise ValueError('panel timing window exceeds one day')
        if self.source_run_retained_bytes < 3 * self.source_response_bytes:
            raise ValueError('source quota cannot even retain all origin raw responses')

    @property
    def market_slots(self):
        # Never spend anticipated overlap before actual assignment evidence exists.
        return self.scheduled_slots + self.triggered_slots * (1 + self.controls_per_trigger)

    @property
    def duration_seconds(self):
        return ((self.cycles - 1) * self.cadence_seconds + self.max_origin_delay_seconds
                + self.horizon_seconds + self.tolerance_seconds)


def reservation(protocol, *, storage_profile=None):
    if type(protocol) is not PanelProtocol:
        raise ValueError('explicit immutable panel protocol required')
    origins = protocol.market_slots * protocol.cycles
    targets = origins * protocol.target_attempts
    requests = origins * 3 + targets * 2
    computations = origins + targets
    source_bytes = computations * protocol.source_run_retained_bytes
    computation_bytes = computations * computation_limits(storage_profile)['max_output_bytes']
    total = source_bytes + computation_bytes + sum(
        FIXED[k] for k in ('selection_bytes', 'frame_read_bytes', 'declaration_bytes'))
    if total > FIXED['max_panel_bytes']:
        raise ValueError('aggregate panel reservation exceeds finite storage ceiling')
    return {**({'computation_storage_profile': storage_profile}
               if storage_profile is not None else {}),
            'market_slots': protocol.market_slots, 'origin_slots': origins,
            'scheduled_origin_slots': protocol.scheduled_slots * protocol.cycles,
            'triggered_origin_slots': protocol.triggered_slots * protocol.cycles,
            'control_origin_slots': protocol.triggered_slots * protocol.controls_per_trigger
                                    * protocol.cycles,
            'target_attempt_slots': targets, 'source_run_slots': computations,
            'source_request_slots': requests, 'raw_byte_ceiling': requests
                                                            * protocol.source_response_bytes,
            'source_retained_bytes': source_bytes, 'computation_retained_bytes': computation_bytes,
            'total_retained_bytes': total,
            'required_free_bytes': total + FIXED['free_reserve_bytes'],
            'duration_seconds': protocol.duration_seconds,
            'overlap_discount_applied': False,
            'runtime_source_retention_guard_required': True}


def _paths(frame_root, output_root, commit):
    frame, root = _canonical(frame_root), _canonical(output_root)
    if (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)
            or not root.name.startswith('fs2_panel_')
            or frame == root or frame in root.parents or root in frame.parents):
        raise ValueError('separate panel journal and immutable original-frame commit required')
    return frame, root


def _recipe(protocol, seed):
    return asdict(SamplingProtocol(
        seed=seed, scheduled_per_stratum=protocol.scheduled_per_stratum,
        triggered_per_stratum=protocol.triggered_per_stratum,
        controls_per_trigger=protocol.controls_per_trigger,
        max_unique_markets=protocol.market_slots))


def declare_panel(frame_root, *, implementation_commit, output_root, protocol,
                  storage_profile=None):
    """No numerical reads, caller seed/clocks/provenance, network, SQL or accepted origin."""
    frame, root = _paths(frame_root, output_root, implementation_commit)
    allocation = reservation(protocol, storage_profile=storage_profile)
    version = VERSION if storage_profile is None else COMPACT_VERSION
    if not frame.is_dir():
        raise ValueError('existing frame directory required; numerical verification comes later')
    if root.exists():
        raise FileExistsError('panel declaration retained; never resume or overwrite')
    if shutil.disk_usage(root.parent).free < allocation['required_free_bytes']:
        raise ValueError('insufficient capacity for full panel/control/target reservation')
    build = verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        payload = {
            'schema_version': version, 'protocol': asdict(protocol), 'fixed_limits': FIXED,
            **({'computation_storage_profile': storage_profile}
               if storage_profile is not None else {}),
            'reservation': allocation, 'sampling_recipe': _recipe(protocol, secrets.token_hex(32)),
            'frame_root': str(frame), 'frame_implementation_commit': implementation_commit,
            'build': build, 'source_policy': TARGETED_POLICY, 'feature_families': FAMILIES,
            'declared_at': _clock(), 'frame_verified': False, 'collection_enabled': False,
            'origin_admitted': False, 'feature_store_admitted': False, 'accepted_panel': False,
            'trigger_assessment_policy': 'not_yet_frozen; no measured controls admitted',
            'sampling_recipe_semantics': 'slot ceilings are not a sampling result; do not truncate',
        }
        if len(_json_bytes(payload)) > FIXED['declaration_bytes'] - 65536:
            raise ValueError('panel declaration exceeds bounded artefact quota')
        _persist(root, 'panel_policy', payload)
        return read_panel_declaration(root)
    except BaseException as exc:
        try:
            _persist(root, 'panel_failure', {'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_panel_declaration(output_root):
    root = _canonical(output_root)
    if {p.name for p in root.iterdir()} != {'panel_policy.json', 'panel_policy_ack.json'}:
        raise ValueError('complete isolated panel declaration required')
    if any(p.stat().st_size > FIXED['declaration_bytes'] for p in root.iterdir()):
        raise ValueError('panel declaration exceeds readable quota')
    payload, ack = _pair(root, 'panel_policy')
    _paths(payload['frame_root'], root, payload['frame_implementation_commit'])
    protocol = PanelProtocol(**payload['protocol'])
    profile = payload.get('computation_storage_profile')
    version = VERSION if profile is None else COMPACT_VERSION
    seed = payload['sampling_recipe']['seed']
    if not isinstance(seed, str) or not HASH_PATTERN.fullmatch(seed):
        raise ValueError('invalid frozen panel seed')
    if (payload['schema_version'] != version or payload['build'] != verified_panel_build()
            or payload['fixed_limits'] != FIXED or payload['source_policy'] != TARGETED_POLICY
            or payload['feature_families'] != FAMILIES
            or _json_bytes(payload['reservation']) != _json_bytes(
                reservation(protocol, storage_profile=profile))
            or _json_bytes(payload['sampling_recipe']) != _json_bytes(_recipe(protocol, seed))
            or any(payload[key] is not False for key in ('frame_verified', 'collection_enabled',
                       'origin_admitted', 'feature_store_admitted', 'accepted_panel'))
            or payload['trigger_assessment_policy'] !=
                'not_yet_frozen; no measured controls admitted'
            or payload['sampling_recipe_semantics'] !=
                'slot ceilings are not a sampling result; do not truncate'
            or not _ordered_clocks(payload['declared_at'], ack['durable_ack'])):
        raise ValueError('panel declaration build/policy/chronology differs')
    return {**({'computation_storage_profile': profile} if profile is not None else {}),
            'schema_version': version, 'declaration_hash': ack['payload_hash'],
            'declaration_available_at': ack['durable_ack'],
            'protocol_hash': content_hash(payload['protocol']),
            'reservation': payload['reservation'], 'sampling_recipe': payload['sampling_recipe'],
            'frame_verified': False, 'collection_enabled': False, 'origin_admitted': False,
            'accepted_panel': False}
