"""Actual read/compute/durability for verified synthetic-window diagnostics."""

import shutil
import time
from dataclasses import asdict

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _digest, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist
from astrolabe.feature_store.types import canonical_json

from .build_identity import verified_panel_build
from .input_read import _canonical
from .window_coverage import WindowCoveragePolicy, project_window_coverage
from .window_journal import LIMITS as SOURCE_LIMITS
from .window_journal import read_window

VERSION = 'fs2-window-computation-v1'
LIMITS = {'max_output_bytes': 64 * 1048576, 'max_artifact_bytes': 16 * 1048576,
          'max_seconds': 180, 'failure_reserve_bytes': 65536,
          'free_reserve_bytes': 2 * 1024**3}


def _paths(source_root, output_root):
    source, root = _canonical(source_root), _canonical(output_root)
    if (not root.name.startswith('fs2_window_computation_') or source == root
            or source in root.parents or root in source.parents):
        raise ValueError('separate fresh fs2_window_computation_ root required')
    return source, root


def _check(root, started, addition=0):
    if time.monotonic() - started > LIMITS['max_seconds']:
        raise ValueError('window computation processing deadline exceeded')
    files = list(root.iterdir())
    if len(files) > 8:
        raise ValueError('window computation file count exceeded')
    total = 0
    for file in files:
        if file.is_symlink() or not file.is_file():
            raise ValueError('invalid window computation file')
        size = file.stat().st_size
        if size > LIMITS['max_artifact_bytes']:
            raise ValueError('window computation artefact budget exceeded')
        total += size
    if total + addition > LIMITS['max_output_bytes'] - LIMITS['failure_reserve_bytes']:
        raise ValueError('window computation retained budget exceeded')
    if addition and shutil.disk_usage(root).free < LIMITS['free_reserve_bytes'] + addition:
        raise ValueError('window computation free-space reserve reached')


def _save(root, name, value, started):
    size = len(_json_bytes(value))
    if size > LIMITS['max_artifact_bytes']:
        raise ValueError('window computation artefact budget exceeded')
    _check(root, started, size + 4096)
    _persist(root, name, value)


def _inputs(source):
    summary = read_window(source)
    declaration, declaration_ack = _pair(source, 'window_policy')
    if declaration_ack['payload_hash'] != summary['policy_hash']:
        raise ValueError('window policy changed during read')
    events, manifest, last_hash = [], [], None
    for ordinal in range(1, summary['event_count'] + 1):
        name = f'event_{ordinal:06d}'
        event, ack = _pair(source, name)
        path = source / (name + '.bin')
        if path.is_symlink() or path.stat().st_size > SOURCE_LIMITS['max_frame_bytes']:
            raise ValueError('bounded original raw window frame required')
        raw = path.read_bytes()
        if (event['previous_hash'] != last_hash or event['ordinal'] != ordinal
                or len(raw) != event['raw_bytes'] or _digest(raw) != event['raw_hash']):
            raise ValueError('window changed during raw consumption')
        events.append({'event': event, 'ack': ack, 'raw': raw})
        manifest.append({'event_hash': ack['payload_hash'], 'raw_hash': event['raw_hash'],
                         'durable_ack': ack['durable_ack']})
        last_hash = ack['payload_hash']
    if summary['last_event_hash'] != last_hash or read_window(source) != summary:
        raise ValueError('window changed during input read')
    binding = {'source_policy': declaration['policy'], 'source_summary': summary,
               'input_manifest_hash': content_hash(manifest)}
    return binding, events


def record_window_computation(source_root, *, output_root, policy):
    source, root = _paths(source_root, output_root)
    if type(policy) is not WindowCoveragePolicy:
        raise ValueError('explicit window coverage policy required')
    if root.exists():
        raise FileExistsError('window computation is terminal; never overwrite/resume')
    if shutil.disk_usage(root.parent).free < (
        LIMITS['free_reserve_bytes'] + LIMITS['max_output_bytes']
    ):
        raise ValueError('window computation storage reserve unavailable')
    started, build = time.monotonic(), verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'window_policy', {'schema_version': VERSION, 'limits': dict(LIMITS),
              'build': build, 'source_root': str(source), 'coverage_policy': asdict(policy),
              'declared_at': _clock()}, started)
        _, pa = _pair(root, 'window_policy')
        read_started = _clock()
        binding, events = _inputs(source)
        read_completed = _clock()
        _save(root, 'window_input', {**binding, 'policy_hash': pa['payload_hash'],
              'read_started_at': read_started, 'read_completed_at': read_completed}, started)
        _, ia = _pair(root, 'window_input')
        computation_started = _clock()
        projection = project_window_coverage(binding['source_policy'], binding['source_summary'],
                                             events, policy=policy)
        completed = _clock()
        if verified_panel_build() != build:
            raise ValueError('window computation build changed')
        _save(root, 'window_facts', {'schema_version': VERSION, 'policy_hash': pa['payload_hash'],
              'input_hash': ia['payload_hash'], 'input_available_at': ia['durable_ack'],
              'computation_started_at': computation_started, 'computed_at': completed,
              'projection': projection, 'origin_admitted': False,
              'feature_store_admitted': False}, started)
        result = read_window_computation(root)
        _check(root, started)
        return result
    except BaseException as exc:
        try:
            _persist(root, 'window_failure', {'schema_version': VERSION,
                                             'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_window_computation(root):
    started, root = time.monotonic(), _canonical(root)
    expected = {name + suffix for name in ('window_policy', 'window_input', 'window_facts')
                for suffix in ('.json', '_ack.json')}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('complete successful window computation closure required')
    _check(root, started)
    declaration, pa = _pair(root, 'window_policy')
    source, root = _paths(declaration['source_root'], root)
    policy = WindowCoveragePolicy(**declaration['coverage_policy'])
    if (declaration['schema_version'] != VERSION or declaration['limits'] != LIMITS
            or declaration['build'] != verified_panel_build()):
        raise ValueError('window computation build/policy differs')
    inputs, ia = _pair(root, 'window_input')
    facts, fa = _pair(root, 'window_facts')
    if (facts['schema_version'] != VERSION or inputs['policy_hash'] != pa['payload_hash']
            or facts['policy_hash'] != pa['payload_hash']
            or facts['input_hash'] != ia['payload_hash']
            or facts['input_available_at'] != ia['durable_ack']
            or facts['origin_admitted'] is not False or facts['feature_store_admitted'] is not False
            or not _ordered_clocks(declaration['declared_at'], pa['durable_ack'],
                inputs['read_started_at'], inputs['read_completed_at'], ia['durable_ack'],
                facts['computation_started_at'], facts['computed_at'], fa['durable_ack'])
            or not _ordered_clocks(inputs['source_summary']['window_available_at'],
                                   inputs['read_started_at'])):
        raise ValueError('window computation input/chronology differs')
    binding, events = _inputs(source)
    if any(inputs[k] != value for k, value in binding.items()):
        raise ValueError('window computation source binding differs')
    projection = project_window_coverage(binding['source_policy'], binding['source_summary'],
                                         events, policy=policy)
    if canonical_json(projection) != canonical_json(facts['projection']):
        raise ValueError('window computation exact replay differs')
    if declaration['build'] != verified_panel_build():
        raise ValueError('window computation build changed during replay')
    _check(root, started)
    return {'schema_version': VERSION, 'computation_hash': fa['payload_hash'],
            'policy_hash': pa['payload_hash'], 'input_hash': ia['payload_hash'],
            'projection_hash': projection['projection_hash'],
            'computation_started_at': facts['computation_started_at'],
            'computed_at': facts['computed_at'], 'computation_available_at': fa['durable_ack'],
            'source_provenance_class': projection['provenance_class'],
            'reconstructed_receipt_duration_ns': projection['reconstructed_receipt_duration_ns'],
            'uncovered_duration_ns': projection['uncovered_duration_ns'],
            'origin_admitted': False, 'feature_store_admitted': False}
