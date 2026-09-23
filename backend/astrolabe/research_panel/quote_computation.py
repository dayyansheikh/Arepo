"""Durable bounded quote computations over verified source reads; no origin admission."""

import shutil
import time
from collections import Counter
from dataclasses import asdict

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist

from .build_identity import verified_panel_build
from .input_read import _canonical, input_limits, read_input_read, record_input_read
from .quote_inputs import QuoteInputPolicy, project_quote_inputs

VERSION = 'fs2-quote-computation-v1'
CHILD = 'fs2_input_read_source'
LIMITS = {'max_output_bytes': 64 * 1048576, 'max_artifact_bytes': 16 * 1048576,
          'max_seconds': 180, 'free_reserve_bytes': 2 * 1024**3,
          'failure_reserve_bytes': 65536}

COMPACT_VERSION = 'fs2-quote-computation-v2'
COMPACT_LIMITS = {**LIMITS, 'storage_profile': 'compact-v1',
                  'max_output_bytes': 8 * 1048576, 'max_artifact_bytes': 2 * 1048576}


def computation_limits(storage_profile):
    if storage_profile is None:
        return LIMITS
    if storage_profile == 'compact-v1':
        return COMPACT_LIMITS
    raise ValueError('unknown quote computation storage profile')


def _paths(source_root, output_root):
    source, root = _canonical(source_root), _canonical(output_root)
    if (not root.name.startswith('fs2_quote_computation_') or source == root
            or source in root.parents or root in source.parents):
        raise ValueError('separate fs2_quote_computation_ journal required')
    return source, root


def _size(root, limits=LIMITS):
    """Finite-depth accounting includes the full child, with no symlink traversal."""
    files = []
    for path in root.iterdir():
        if path.is_symlink():
            raise ValueError('symlink in quote computation')
        if path.is_dir():
            if path.name != CHILD:
                raise ValueError('unexpected quote computation child')
            files.extend(path.iterdir())
        else:
            files.append(path)
    if len(files) > 16:
        raise ValueError('quote computation file count exceeded')
    total = 0
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError('unexpected nested quote computation entry')
        size = path.stat().st_size
        if size > limits['max_artifact_bytes']:
            raise ValueError('quote computation artefact exceeds readable limit')
        total += size
    return total


def _check(root, started, addition=0, *, writing=False, limits=LIMITS):
    if time.monotonic() - started > limits['max_seconds']:
        raise ValueError('quote computation processing deadline exceeded')
    if (_size(root, limits) + addition
            > limits['max_output_bytes'] - limits['failure_reserve_bytes']):
        raise ValueError('quote computation total retained-byte budget exceeded')
    if writing and shutil.disk_usage(root).free < limits['free_reserve_bytes'] + addition:
        raise ValueError('quote computation free-space reserve reached')


def _save(root, name, payload, started, *, limits=LIMITS):
    size = len(_json_bytes(payload))
    if size > limits['max_artifact_bytes']:
        raise ValueError('quote computation artefact exceeds readable limit')
    _check(root, started, size + 4096, writing=True, limits=limits)
    _persist(root, name, payload)


def _inputs(root, summary):
    facts, ack = _pair(root / CHILD, 'read_facts')
    if (ack['payload_hash'] != summary['read_facts_hash']
            or ack['durable_ack'] != summary['read_available_at']
            or facts['projection_hash'] != summary['projection_hash']
            or content_hash(facts['source_projection']) != summary['projection_hash']):
        raise ValueError('input-read facts changed during actual consumption')
    return [row for kind, row in facts['source_projection']['rows'] if kind == 'source_observation']


def record_quote_computation(source_root, *, output_root, policy, storage_profile=None):
    """Create a fresh computation, accepting no caller rows, clocks or admission flags."""
    limits, child_limits = computation_limits(storage_profile), input_limits(storage_profile)
    version = VERSION if storage_profile is None else COMPACT_VERSION
    source, root = _paths(source_root, output_root)
    if type(policy) is not QuoteInputPolicy:
        raise ValueError('explicit finite quote input policy required')
    if root.exists():
        raise FileExistsError('existing computation retained; never resume or overwrite')
    if shutil.disk_usage(root.parent).free < (
        limits['free_reserve_bytes'] + limits['max_output_bytes']
    ):
        raise ValueError('insufficient quote computation storage reserve')
    build, started = verified_panel_build(), time.monotonic()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'quote_policy', {
            'schema_version': version, 'limits': limits, 'child_limits': child_limits,
            'source_root': str(source), 'child_name': CHILD, 'build': build,
            'quote_policy': asdict(policy), 'quote_policy_hash': content_hash(asdict(policy)),
            'declared_at': _clock(),
        }, started, limits=limits)
        _, policy_ack = _pair(root, 'quote_policy')
        _check(root, started, child_limits['max_output_bytes'], writing=True, limits=limits)
        read = record_input_read(source, output_root=root / CHILD, storage_profile=storage_profile)
        _check(root, started, limits=limits)
        computation_started = _clock()
        rows = _inputs(root, read)
        projection = project_quote_inputs(rows, policy=policy, cutoff=_time(computation_started))
        completed = _clock()
        if not _ordered_clocks(policy_ack['durable_ack'], read['read_started_at'],
                               read['read_available_at'], computation_started, completed):
            raise ValueError('quote computation chronology regressed')
        if verified_panel_build() != build:
            raise ValueError('quote computation build changed')
        _save(root, 'quote_facts', {
            'schema_version': version, 'policy_hash': policy_ack['payload_hash'],
            'input_read': read, 'projection': projection,
            'computation_started_at': computation_started, 'computed_at': completed,
            'origin_admitted': False, 'feature_store_admitted': False,
        }, started, limits=limits)
        result = read_quote_computation(root)
        _check(root, started, limits=limits)
        return result
    except BaseException as exc:
        try:
            _persist(root, 'quote_failure', {'schema_version': version,
                                           'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_quote_computation(output_root):
    """Verify source closure and replay at the original actual cutoff without new clocks."""
    started = time.monotonic()
    root = _canonical(output_root)
    expected = {CHILD, *[name + suffix for name in ('quote_policy', 'quote_facts')
                        for suffix in ('.json', '_ack.json')]}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('complete successful quote computation closure required')
    _check(root, started)
    declaration, policy_ack = _pair(root, 'quote_policy')
    profile = (None if declaration['schema_version'] == VERSION
               else declaration['limits'].get('storage_profile'))
    limits, child_limits = computation_limits(profile), input_limits(profile)
    version = VERSION if profile is None else COMPACT_VERSION
    _check(root, started, limits=limits)
    source, root = _paths(declaration['source_root'], root)
    policy = QuoteInputPolicy(**declaration['quote_policy'])
    build = verified_panel_build()
    if (declaration['schema_version'] != version or declaration['limits'] != limits
            or declaration['child_limits'] != child_limits or declaration['child_name'] != CHILD
            or declaration['build'] != build
            or declaration['quote_policy_hash'] != content_hash(asdict(policy))):
        raise ValueError('quote computation build/policy differs')
    child_policy, child_ack = _pair(root / CHILD, 'read_policy')
    if (child_policy['policy'] != child_limits or child_policy['source_root'] != str(source)
            or child_policy['build'] != build
            or not _ordered_clocks(declaration['declared_at'], policy_ack['durable_ack'],
                                   child_policy['declared_at'], child_ack['durable_ack'])):
        raise ValueError('quote computation child lineage/declaration differs')
    read = read_input_read(root / CHILD)
    _check(root, started, limits=limits)
    facts, ack = _pair(root, 'quote_facts')
    if (facts['schema_version'] != version or facts['policy_hash'] != policy_ack['payload_hash']
            or facts['input_read'] != read or facts['origin_admitted'] is not False
            or facts['feature_store_admitted'] is not False
            or not _ordered_clocks(read['read_available_at'], facts['computation_started_at'],
                                   facts['computed_at'], ack['durable_ack'])):
        raise ValueError('quote computation chronology/input lineage differs')
    projection = project_quote_inputs(_inputs(root, read), policy=policy,
                                      cutoff=_time(facts['computation_started_at']))
    if _json_bytes(projection) != _json_bytes(facts['projection']):
        raise ValueError('quote computation exact replay differs')
    if verified_panel_build() != build:
        raise ValueError('quote computation build changed during verification')
    _check(root, started, limits=limits)
    return {'schema_version': version, 'computation_hash': ack['payload_hash'],
            'policy_hash': policy_ack['payload_hash'], 'input_read_hash': read['read_facts_hash'],
            'projection_hash': projection['projection_hash'],
            'computation_started_at': facts['computation_started_at'],
            'computed_at': facts['computed_at'], 'computation_available_at': ack['durable_ack'],
            'source_provenance_class': projection['provenance_class'],
            'source_observation_count': len(projection['source_inventory']),
            'quote_count': len(projection['quotes']),
            'quote_states': dict(sorted(Counter(q['state'] for q in projection['quotes']).items())),
            'origin_admitted': False, 'feature_store_admitted': False}
