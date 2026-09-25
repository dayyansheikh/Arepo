"""Durable exact snapshot components over verified source reads; no origin admission."""

import shutil
import time
from collections import Counter
from dataclasses import asdict

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist
from astrolabe.feature_store.types import canonical_json

from . import quote_computation as journal
from .book_primitives import project_book_primitives
from .build_identity import verified_panel_build
from .input_read import _canonical, input_limits, read_input_read, record_input_read
from .quote_inputs import QuoteInputPolicy

VERSION = 'fs2-book-computation-v1'
CHILD = journal.CHILD
PROFILE = 'compact-v1'
LIMITS = {'max_output_bytes': 16 * 1048576, 'max_artifact_bytes': 4 * 1048576,
          'max_seconds': 180, 'free_reserve_bytes': 2 * 1024**3,
          'failure_reserve_bytes': 65536}


def _paths(source_root, output_root):
    source, root = _canonical(source_root), _canonical(output_root)
    if (not root.name.startswith('fs2_book_computation_') or source == root
            or source in root.parents or root in source.parents):
        raise ValueError('separate fs2_book_computation_ journal required')
    return source, root


def _check(root, started, addition=0, *, writing=False):
    journal._check(root, started, addition, writing=writing, limits=LIMITS)


def _save(root, name, payload, started):
    journal._save(root, name, payload, started, limits=LIMITS)


def record_book_computation(source_root, *, output_root, policy):
    source, root = _paths(source_root, output_root)
    if type(policy) is not QuoteInputPolicy:
        raise ValueError('explicit finite quote input policy required')
    if root.exists():
        raise FileExistsError('existing computation retained; never resume or overwrite')
    if shutil.disk_usage(root.parent).free < (
        LIMITS['free_reserve_bytes'] + LIMITS['max_output_bytes']
    ):
        raise ValueError('insufficient book computation storage reserve')
    build, started = verified_panel_build(), time.monotonic()
    child_limits = input_limits(PROFILE)
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'book_policy', {
            'schema_version': VERSION, 'limits': LIMITS, 'child_limits': child_limits,
            'source_root': str(source), 'child_name': CHILD, 'build': build,
            'quote_policy': asdict(policy), 'quote_policy_hash': content_hash(asdict(policy)),
            'storage_profile': PROFILE, 'declared_at': _clock(),
        }, started)
        _, policy_ack = _pair(root, 'book_policy')
        _check(root, started, child_limits['max_output_bytes'], writing=True)
        read = record_input_read(source, output_root=root / CHILD, storage_profile=PROFILE)
        _check(root, started)
        computation_started = _clock()
        projection = project_book_primitives(journal._inputs(root, read), policy=policy,
                                             cutoff=_time(computation_started))
        completed = _clock()
        if not _ordered_clocks(policy_ack['durable_ack'], read['read_started_at'],
                               read['read_available_at'], computation_started, completed):
            raise ValueError('book computation chronology regressed')
        if verified_panel_build() != build:
            raise ValueError('book computation build changed')
        _save(root, 'book_facts', {
            'schema_version': VERSION, 'policy_hash': policy_ack['payload_hash'],
            'input_read': read, 'projection': projection,
            'computation_started_at': computation_started, 'computed_at': completed,
            'origin_admitted': False, 'feature_store_admitted': False,
        }, started)
        result = read_book_computation(root)
        _check(root, started)
        return result
    except BaseException as exc:
        try:
            _persist(root, 'book_failure', {'schema_version': VERSION,
                                          'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_book_computation(output_root):
    started, root = time.monotonic(), _canonical(output_root)
    expected = {CHILD, *[name + suffix for name in ('book_policy', 'book_facts')
                        for suffix in ('.json', '_ack.json')]}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('complete successful book computation closure required')
    _check(root, started)
    declaration, policy_ack = _pair(root, 'book_policy')
    source, root = _paths(declaration['source_root'], root)
    policy = QuoteInputPolicy(**declaration['quote_policy'])
    build = verified_panel_build()
    child_limits = input_limits(PROFILE)
    if (declaration['schema_version'] != VERSION or declaration['limits'] != LIMITS
            or declaration['child_limits'] != child_limits or declaration['child_name'] != CHILD
            or declaration['storage_profile'] != PROFILE or declaration['build'] != build
            or declaration['quote_policy_hash'] != content_hash(asdict(policy))):
        raise ValueError('book computation build/policy differs')
    child_policy, child_ack = _pair(root / CHILD, 'read_policy')
    if (child_policy['policy'] != child_limits or child_policy['source_root'] != str(source)
            or child_policy['build'] != build
            or not _ordered_clocks(declaration['declared_at'], policy_ack['durable_ack'],
                                   child_policy['declared_at'], child_ack['durable_ack'])):
        raise ValueError('book computation child lineage/declaration differs')
    read = read_input_read(root / CHILD)
    _check(root, started)
    facts, ack = _pair(root, 'book_facts')
    if (facts['schema_version'] != VERSION or facts['policy_hash'] != policy_ack['payload_hash']
            or facts['input_read'] != read or facts['origin_admitted'] is not False
            or facts['feature_store_admitted'] is not False
            or not _ordered_clocks(read['read_available_at'], facts['computation_started_at'],
                                   facts['computed_at'], ack['durable_ack'])):
        raise ValueError('book computation chronology/input lineage differs')
    projection = project_book_primitives(journal._inputs(root, read), policy=policy,
                                         cutoff=_time(facts['computation_started_at']))
    # Canonical JSON admits tagged Decimals stored in facts without converting to floats.
    if canonical_json(projection) != canonical_json(facts['projection']):
        raise ValueError('book computation exact replay differs')
    if verified_panel_build() != build:
        raise ValueError('book computation build changed during verification')
    _check(root, started)
    return {'schema_version': VERSION, 'computation_hash': ack['payload_hash'],
            'policy_hash': policy_ack['payload_hash'], 'input_read_hash': read['read_facts_hash'],
            'projection_hash': projection['projection_hash'],
            'computation_started_at': facts['computation_started_at'],
            'computed_at': facts['computed_at'], 'computation_available_at': ack['durable_ack'],
            'source_provenance_class': projection['provenance_class'],
            'source_observation_count': len(projection['source_inventory']),
            'snapshot_count': len(projection['snapshots']),
            'snapshot_states': dict(sorted(Counter(
                s['state'] for s in projection['snapshots']).items())),
            'origin_admitted': False, 'feature_store_admitted': False}
