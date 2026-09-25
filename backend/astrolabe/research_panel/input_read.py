"""Bounded actual reads of completed source journals; no feature/origin admission."""

import shutil
import time
import uuid
from pathlib import Path

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import (
    _ordered_clocks,
    _pair,
    _persist,
    _verify_run,
    read_source_run,
)

from .build_identity import verified_panel_build

VERSION = 'fs2-panel-input-read-v1'
POLICY = {
    'mode': 'completed_source_run_consumption_only',
    'max_requests': 10, 'max_raw_bytes': 4 * 1048576,
    'max_artifact_bytes': 16 * 1048576, 'max_output_bytes': 32 * 1048576,
    'max_seconds': 60, 'free_reserve_bytes': 2 * 1024**3,
    'origin_admitted': False, 'source_clocks_changed': False,
}

COMPACT_VERSION = 'fs2-panel-input-read-v2'
COMPACT_POLICY = {**POLICY, 'storage_profile': 'compact-v1',
                  'max_artifact_bytes': 2 * 1048576, 'max_output_bytes': 4 * 1048576}


def input_limits(storage_profile):
    if storage_profile is None:
        return POLICY
    if storage_profile == 'compact-v1':
        return COMPACT_POLICY
    raise ValueError('unknown input-read storage profile')


def _canonical(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('canonical absolute input-read paths required')
    return path


def _paths(source_root, output_root):
    source, root = _canonical(source_root), _canonical(output_root)
    if (not root.name.startswith('fs2_input_read_') or source == root
            or source in root.parents or root in source.parents):
        raise ValueError('separate fs2_input_read_ journal required')
    return source, root


def _source(source):
    """Read complete current-build facts; callers compare this closure before/after."""
    _, run, ack = _verify_run(source)
    names = sorted(p.name for p in source.iterdir() if p.is_dir())
    if not 1 <= len(names) <= POLICY['max_requests']:
        raise ValueError('nonempty bounded completed source run required')
    for name in names:
        if str(uuid.UUID(name)) != name:
            raise ValueError('canonical source capture ID required')
    rows = read_source_run(source)
    observations = [row for kind, row in rows if kind == 'source_observation']
    if sorted(row['request_id'] for row in observations) != names:
        raise ValueError('source observation/capture closure differs')
    admissions = []
    for name in names:
        payload, receipt = _pair(source / name, 'admission')
        admissions.append({'capture_id': name, 'admission': payload, 'ack': receipt})
    if names != sorted(p.name for p in source.iterdir() if p.is_dir()):
        raise ValueError('source captures changed during input read')
    return {'run': run, 'run_ack': ack, 'admissions': admissions, 'rows': rows}


def _size(root):
    size = 0
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError('unexpected input-read entry')
        size += path.stat().st_size
    return size


def _available(projection, read_started):
    source_acks = [projection['run_ack']['durable_ack'],
                   *[r['ack']['durable_ack'] for r in projection['admissions']]]
    available = [row['available_to_model_at'] if kind == 'source_observation'
                 else row['recorded_at'] for kind, row in projection['rows']]
    if (any(at > _time(read_started) for at in available)
            or any(not _ordered_clocks(at, read_started) for at in source_acks)):
        raise ValueError('source facts unavailable when actual input read began')


def _check(root, started, addition=0, *, writing=False, limits=POLICY):
    if any(p.stat().st_size > limits['max_artifact_bytes'] for p in root.iterdir()):
        raise ValueError('input-read artefact exceeds readable limit')
    if time.monotonic() - started > limits['max_seconds']:
        raise ValueError('input-read processing deadline exceeded')
    if _size(root) + addition > limits['max_output_bytes'] - 65536:
        raise ValueError('input-read retained-byte budget exceeded')
    if writing and shutil.disk_usage(root).free < limits['free_reserve_bytes'] + addition:
        raise ValueError('input-read free-space reserve reached')


def _save(root, name, payload, started, *, limits=POLICY):
    size = len(_json_bytes(payload))
    if size > limits['max_artifact_bytes']:
        raise ValueError('input-read artefact exceeds readable limit')
    _check(root, started, size + 4096, writing=True, limits=limits)
    _persist(root, name, payload)


def record_input_read(source_root, *, output_root, storage_profile=None):
    """Freeze a policy then record an actual complete source read, never caller facts."""
    limits = input_limits(storage_profile)
    version = VERSION if storage_profile is None else COMPACT_VERSION
    source, root = _paths(source_root, output_root)
    if root.exists():
        raise FileExistsError('existing input read retained; never resume or overwrite')
    if shutil.disk_usage(root.parent).free < (
        limits['free_reserve_bytes'] + limits['max_output_bytes']
    ):
        raise ValueError('insufficient input-read storage reserve')
    build, started = verified_panel_build(), time.monotonic()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'read_policy', {
            'schema_version': version, 'policy': limits, 'build': build,
            'source_root': str(source), 'declared_at': _clock(),
        }, started, limits=limits)
        policy, policy_ack = _pair(root, 'read_policy')
        read_started = _clock()
        projection = _source(source)
        completed = _clock()
        _available(projection, read_started)
        if not _ordered_clocks(policy_ack['durable_ack'], read_started, completed):
            raise ValueError('actual input-read clock regression')
        if verified_panel_build() != build:
            raise ValueError('input-read build changed')
        _save(root, 'read_facts', {
            'schema_version': version, 'policy_hash': policy_ack['payload_hash'],
            'source_projection': projection, 'projection_hash': content_hash(projection),
            'read_started_at': read_started, 'projection_completed_at': completed,
            'origin_admitted': False, 'source_clocks_changed': False,
        }, started, limits=limits)
        # A concurrent append/mutation fails this run instead of producing a partial prefix.
        report = read_input_read(root)
        _check(root, started, limits=limits)
        return report
    except BaseException as exc:
        try:
            _persist(root, 'read_failure', {'schema_version': version,
                                          'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_input_read(output_root):
    """Read-only closure verification; no reconstructed acknowledgements or new origin."""
    started = time.monotonic()
    root = _canonical(output_root)
    expected = {name + suffix for name in ('read_policy', 'read_facts')
                for suffix in ('.json', '_ack.json')}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('complete successful input-read closure required')
    _check(root, started)
    policy, policy_ack = _pair(root, 'read_policy')
    profile = (None if policy['schema_version'] == VERSION
               else policy['policy'].get('storage_profile'))
    limits = input_limits(profile)
    version = VERSION if profile is None else COMPACT_VERSION
    _check(root, started, limits=limits)
    source, root = _paths(policy['source_root'], root)
    if (policy['schema_version'] != version or policy['policy'] != limits
            or policy['build'] != verified_panel_build()):
        raise ValueError('input-read build/policy differs')
    facts, ack = _pair(root, 'read_facts')
    if (facts['schema_version'] != version
            or facts['policy_hash'] != policy_ack['payload_hash']
            or facts['origin_admitted'] is not False or facts['source_clocks_changed'] is not False
            or not _ordered_clocks(policy['declared_at'], policy_ack['durable_ack'],
                                   facts['read_started_at'], facts['projection_completed_at'],
                                   ack['durable_ack'])):
        raise ValueError('input-read chronology/lineage differs')
    projection = _source(source)
    if (facts['projection_hash'] != content_hash(facts['source_projection'])
            or _json_bytes(projection) != _json_bytes(facts['source_projection'])):
        raise ValueError('original input-read source closure/projection differs')
    _available(projection, facts['read_started_at'])
    if policy['build'] != verified_panel_build():
        raise ValueError('input-read build changed during verification')
    _check(root, started, limits=limits)
    return {'schema_version': version, 'read_facts_hash': ack['payload_hash'],
            'projection_hash': facts['projection_hash'],
            'read_started_at': facts['read_started_at'],
            'projection_completed_at': facts['projection_completed_at'],
            'read_available_at': ack['durable_ack'],
            'observation_count': len(projection['admissions']),
            'source_provenance_class': projection['run']['provenance_class'],
            'origin_admitted': False, 'source_clocks_changed': False}
