"""D120 panel declaration: screened receipt slots separate from at most 12 origin slots.

``panel_declaration.py`` is frozen (D116/D118). This module adds a new declaration version whose
protocol separates the screened members (receipts and screening computations only; never an
origin, window or target) from the activated origin slots, so the reservation no longer counts a
screened member as an origin. Legacy panels are always delegated to the frozen reader unchanged.

``panel_protocol`` / ``read_declaration`` / ``role_capacity`` dispatch on the declared version:
legacy dictionaries and panels take exactly the frozen code path.
"""

import json
import re
import secrets
import shutil
from collections import Counter
from dataclasses import asdict, dataclass

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import TARGETED_POLICY, _ordered_clocks, _pair, _persist
from astrolabe.feature_store.types import HASH_PATTERN

from . import panel_declaration as legacy
from .build_identity import verified_panel_build
from .input_read import _canonical
from .pairing import PairingDesign, design_from_dict
from .quote_computation import computation_limits
from .sampling import SamplingProtocol

VERSION = 'fs2-pairing-panel-declaration-v1'
PROTOCOL_VERSION = 'fs2-pairing-panel-protocol-v1'
POPULATIONS = (legacy.LIQUIDITY_POPULATION,)
MIB = 1048576
# Per screened member: two bounded receipts plus the bounded screening computation metadata
# (book computation, trigger declaration and computation journals). Enforced at runtime by the
# pairing worker's retained-byte check, never assumed.
SCREENED_METADATA_BYTES = 2 * MIB
SEMANTICS = ('screened slots hold receipts and screening computations only; origin slots hold '
             'activated trigger/control members; slot ceilings are not a sampling result')


@dataclass(frozen=True)
class PairingPanelProtocol:
    screened_slots: int
    origin_slots: int
    cycles: int
    target_attempts: int
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
    screened_receipt_bytes: int = 65536
    version: str = PROTOCOL_VERSION

    def __post_init__(self):
        bounds = {
            'screened_slots': (2, 256), 'origin_slots': (2, 12), 'cycles': (1, 1),
            'target_attempts': (1, 16), 'cadence_seconds': (1, 86400),
            'max_origin_delay_seconds': (0, 86400), 'max_origin_save_seconds': (1, 86399),
            'horizon_seconds': (2, 86400), 'tolerance_seconds': (0, 86399),
            'max_frame_age_seconds': (1, 604800), 'max_frame_interval_seconds': (1, 86400),
            'max_quote_age_seconds': (0, 604800), 'max_identity_age_seconds': (0, 604800),
            'source_response_bytes': (1, MIB), 'source_run_retained_bytes': (MIB, 256 * MIB),
            'screened_receipt_bytes': (1, MIB),
        }
        for key, (minimum, maximum) in bounds.items():
            value = getattr(self, key)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError('explicit bounded pairing protocol required: ' + key)
        if (self.version != PROTOCOL_VERSION or self.origin_slots % 2
                or self.origin_slots > self.screened_slots
                or self.screened_receipt_bytes != self.source_response_bytes):
            raise ValueError('pairing slots/receipt bound inconsistent')
        if (self.max_origin_save_seconds >= self.horizon_seconds
                or self.tolerance_seconds >= self.horizon_seconds
                or self.max_origin_delay_seconds >= self.cadence_seconds
                or self.target_attempts > self.tolerance_seconds + 1
                or self.max_frame_interval_seconds > self.max_frame_age_seconds):
            raise ValueError('panel timing bounds are inconsistent')
        if self.source_run_retained_bytes < 3 * self.source_response_bytes:
            raise ValueError('source quota cannot even retain all origin raw responses')

    @property
    def market_slots(self):
        return self.origin_slots

    @property
    def scheduled_slots(self):
        return 0

    @property
    def duration_seconds(self):
        return ((self.cycles - 1) * self.cadence_seconds + self.max_origin_delay_seconds
                + self.horizon_seconds + self.tolerance_seconds)


def panel_protocol(value):
    """Legacy dictionaries take the frozen ``PanelProtocol`` exactly."""
    if isinstance(value, dict) and value.get('version') == PROTOCOL_VERSION:
        return PairingPanelProtocol(**value)
    return legacy.PanelProtocol(**value)


def is_pairing_protocol(value):
    return isinstance(value, dict) and value.get('version') == PROTOCOL_VERSION


def _peek(root):
    try:
        return json.loads((root / 'panel_policy.json').read_bytes()).get('schema_version')
    except Exception:  # noqa: BLE001 - any doubt goes to the frozen reader and its own errors
        return None


def is_pairing_panel(panel_root):
    try:
        return _peek(_canonical(panel_root)) == VERSION
    except ValueError:
        return False


def read_declaration(output_root):
    """Dispatch: pairing panels to ``read_pairing_declaration``, all others to the frozen reader."""
    if is_pairing_panel(output_root):
        return read_pairing_declaration(output_root)
    return legacy.read_panel_declaration(output_root)


def reservation(protocol, design, *, storage_profile=None):
    if type(protocol) is not PairingPanelProtocol or type(design) is not PairingDesign:
        raise ValueError('explicit immutable pairing protocol and design required')
    if (design.screened_slots != protocol.screened_slots
            or design.origin_slots != protocol.origin_slots):
        raise ValueError('pairing design and protocol slot counts differ')
    origins = protocol.origin_slots * protocol.cycles
    targets = origins * protocol.target_attempts
    screened = protocol.screened_slots
    # Screening: 2 requests per screened member; binding: 2 per activated member; origin: 3;
    # target: 2 per attempt.
    requests = screened * 2 + origins * 2 + origins * 3 + targets * 2
    computations = origins + targets
    source_bytes = computations * protocol.source_run_retained_bytes
    computation_bytes = computations * computation_limits(storage_profile)['max_output_bytes']
    screened_bytes = screened * (2 * protocol.screened_receipt_bytes + SCREENED_METADATA_BYTES)
    total = source_bytes + computation_bytes + screened_bytes + sum(
        legacy.FIXED[k] for k in ('selection_bytes', 'frame_read_bytes', 'declaration_bytes'))
    if total > legacy.FIXED['max_panel_bytes']:
        raise ValueError('aggregate panel reservation exceeds finite storage ceiling')
    return {**({'computation_storage_profile': storage_profile}
               if storage_profile is not None else {}),
            'screened_slots': screened, 'screened_receipt_bytes': protocol.screened_receipt_bytes,
            'screened_metadata_bytes': SCREENED_METADATA_BYTES,
            'screened_retained_bytes': screened_bytes,
            'market_slots': protocol.origin_slots, 'origin_slots': origins,
            'scheduled_origin_slots': 0, 'triggered_origin_slots': origins // 2,
            'control_origin_slots': origins // 2, 'binding_slots': origins,
            'target_attempt_slots': targets, 'source_run_slots': computations,
            'source_request_slots': requests,
            'raw_byte_ceiling': requests * protocol.source_response_bytes,
            'source_retained_bytes': source_bytes, 'computation_retained_bytes': computation_bytes,
            'total_retained_bytes': total,
            'required_free_bytes': total + legacy.FIXED['free_reserve_bytes'],
            'duration_seconds': protocol.duration_seconds,
            'overlap_discount_applied': False,
            'runtime_source_retention_guard_required': True}


def _recipe(protocol, seed):
    # The pairing design carries the real shape; the sampling recipe supplies the seed, the
    # frozen stratum edges and the screened-member ceiling. Its per-stratum counts are unused.
    return asdict(SamplingProtocol(seed=seed, scheduled_per_stratum=1, triggered_per_stratum=1,
                                   controls_per_trigger=1,
                                   max_unique_markets=protocol.screened_slots))


def _paths(frame_root, output_root, commit):
    frame, root = _canonical(frame_root), _canonical(output_root)
    if (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)
            or not root.name.startswith('fs2_panel_')
            or frame == root or frame in root.parents or root in frame.parents):
        raise ValueError('separate panel journal and immutable original-frame commit required')
    return frame, root


def declare_pairing_panel(frame_root, *, implementation_commit, output_root, protocol, design,
                          storage_profile=None, population_policy=legacy.LIQUIDITY_POPULATION):
    """No numerical reads, caller seed/clocks/provenance, network, SQL or accepted origin."""
    frame, root = _paths(frame_root, output_root, implementation_commit)
    allocation = reservation(protocol, design, storage_profile=storage_profile)
    if population_policy not in POPULATIONS:
        raise ValueError('unknown prospective population policy')
    if not frame.is_dir():
        raise ValueError('existing frame directory required; numerical verification comes later')
    if root.exists():
        raise FileExistsError('panel declaration retained; never resume or overwrite')
    if shutil.disk_usage(root.parent).free < allocation['required_free_bytes']:
        raise ValueError('insufficient capacity for full screened/origin/target reservation')
    build = verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        payload = {
            'schema_version': VERSION, 'protocol': asdict(protocol),
            'pairing_design': design.as_dict(), 'category_policy': design.category_policy,
            'population_policy': population_policy, 'fixed_limits': legacy.FIXED,
            **({'computation_storage_profile': storage_profile}
               if storage_profile is not None else {}),
            'reservation': allocation, 'sampling_recipe': _recipe(protocol, secrets.token_hex(32)),
            'frame_root': str(frame), 'frame_implementation_commit': implementation_commit,
            'build': build, 'source_policy': TARGETED_POLICY,
            'feature_families': legacy.FAMILIES, 'declared_at': _clock(),
            'frame_verified': False, 'collection_enabled': False, 'origin_admitted': False,
            'feature_store_admitted': False, 'accepted_panel': False,
            'trigger_assessment_policy': 'not_yet_frozen; roles drawn only after screening',
            'sampling_recipe_semantics': SEMANTICS,
        }
        if len(_json_bytes(payload)) > legacy.FIXED['declaration_bytes'] - 65536:
            raise ValueError('panel declaration exceeds bounded artefact quota')
        _persist(root, 'panel_policy', payload)
        return read_pairing_declaration(root)
    except BaseException as exc:
        try:
            _persist(root, 'panel_failure', {'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_pairing_declaration(output_root):
    root = _canonical(output_root)
    if {p.name for p in root.iterdir()} != {'panel_policy.json', 'panel_policy_ack.json'}:
        raise ValueError('complete isolated panel declaration required')
    if any(p.stat().st_size > legacy.FIXED['declaration_bytes'] for p in root.iterdir()):
        raise ValueError('panel declaration exceeds readable quota')
    payload, ack = _pair(root, 'panel_policy')
    _paths(payload['frame_root'], root, payload['frame_implementation_commit'])
    protocol = PairingPanelProtocol(**payload['protocol'])
    design = design_from_dict(payload['pairing_design'])
    profile = payload.get('computation_storage_profile')
    seed = payload['sampling_recipe']['seed']
    if not isinstance(seed, str) or not HASH_PATTERN.fullmatch(seed):
        raise ValueError('invalid frozen panel seed')
    if (payload['schema_version'] != VERSION
            or payload['population_policy'] not in POPULATIONS
            or payload['category_policy'] != design.category_policy
            or payload['build'] != verified_panel_build()
            or payload['fixed_limits'] != legacy.FIXED
            or payload['source_policy'] != TARGETED_POLICY
            or payload['feature_families'] != legacy.FAMILIES
            or _json_bytes(payload['reservation']) != _json_bytes(
                reservation(protocol, design, storage_profile=profile))
            or _json_bytes(payload['sampling_recipe']) != _json_bytes(_recipe(protocol, seed))
            or any(payload[key] is not False for key in ('frame_verified', 'collection_enabled',
                       'origin_admitted', 'feature_store_admitted', 'accepted_panel'))
            or payload['trigger_assessment_policy']
                != 'not_yet_frozen; roles drawn only after screening'
            or payload['sampling_recipe_semantics'] != SEMANTICS
            or not _ordered_clocks(payload['declared_at'], ack['durable_ack'])):
        raise ValueError('panel declaration build/policy/chronology differs')
    return {'population_policy': payload['population_policy'],
            **({'computation_storage_profile': profile} if profile is not None else {}),
            'schema_version': VERSION, 'declaration_hash': ack['payload_hash'],
            'declaration_available_at': ack['durable_ack'],
            'protocol_hash': content_hash(payload['protocol']),
            'pairing_design': payload['pairing_design'],
            'category_policy': payload['category_policy'],
            'reservation': payload['reservation'], 'sampling_recipe': payload['sampling_recipe'],
            'frame_verified': False, 'collection_enabled': False, 'origin_admitted': False,
            'accepted_panel': False}


def role_capacity(plan, protocol):
    """Legacy protocols take the frozen function; pairing counts screened and activated roles."""
    if type(protocol) is not PairingPanelProtocol:
        return legacy.role_capacity(plan, protocol)
    counts = Counter(row['arm'] for row in plan['assignments'])
    ceilings = {'screened': protocol.screened_slots,
                'triggered': protocol.origin_slots // 2, 'control': protocol.origin_slots // 2}
    fits = set(counts) <= set(ceilings) and all(counts[arm] <= cap for arm, cap in ceilings.items())
    return {'counts_per_cycle': dict(counts), 'ceilings_per_cycle': ceilings,
            'fits': fits, 'overlap_discount_applied': False,
            'origin_admitted': False, 'accepted_panel': False}
