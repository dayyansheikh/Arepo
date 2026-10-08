"""Bounded pre-origin observers owned by the selected screening worker, never caller history."""

import asyncio
import hashlib
import json
import os
import stat
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from astrolabe.feature_store.capture import _clock, _json_bytes
from astrolabe.feature_store.source_run import _ordered_clocks, _pair

from .book_computation import read_book_computation
from .bound_window import WindowBindingPolicy
from .build_identity import verified_panel_build
from .origin_window import OriginWindowPolicy
from .socket_analysis import read_socket_analysis, record_socket_analysis
from .socket_window import capture_loopback_socket, capture_market_socket
from .socket_window_journal import LIMITS as SOCKET_LIMITS
from .socket_window_journal import OBSERVATION_VERSION as OBSERVATION_SOCKET_VERSION
from .socket_window_journal import VERSION as SOCKET_VERSION
from .socket_window_journal import read_socket_window, scope
from .window_computation import LIMITS as ANALYSIS_LIMITS
from .window_reconciliation import WindowReconciliationPolicy

VERSION = 'fs2-owned-window-worker-v6'
OBSERVATION_VERSION = 'fs2-owned-observation-worker-v7'


@dataclass(frozen=True)
class OwnedWindowPolicy:
    duration_ms: int
    binding: WindowBindingPolicy
    analysis: WindowReconciliationPolicy
    origin: OriginWindowPolicy
    binding_mode: str = 'quote'

    def __post_init__(self):
        if (type(self.duration_ms) is not int or not 1 <= self.duration_ms <= 60000
                or type(self.binding) is not WindowBindingPolicy
                or type(self.analysis) is not WindowReconciliationPolicy
                or type(self.origin) is not OriginWindowPolicy
                or self.binding_mode not in ('quote', 'observation')):
            raise ValueError('explicit bounded owned window policies required')


def policy_from_dict(value):
    return OwnedWindowPolicy(value['duration_ms'], WindowBindingPolicy(**value['binding']),
        WindowReconciliationPolicy(**value['analysis']), OriginWindowPolicy(**value['origin']),
        value.get('binding_mode', 'quote'))


def policy_dict(policy):
    value = asdict(policy)
    if policy.binding_mode == 'quote':
        del value['binding_mode']  # preserve the legacy persisted policy shape
    return value


def version(policy):
    return OBSERVATION_VERSION if policy.binding_mode == 'observation' else VERSION


def reservation(slots):
    return slots * (SOCKET_LIMITS['max_retained_bytes'] + ANALYSIS_LIMITS['max_output_bytes'])


def paths(root, index):
    return (root / f'fs2_socket_window_{index:03d}',
            root / f'fs2_socket_analysis_{index:03d}')


def _pre_state(item, provenance, binding_mode='quote'):
    pre = Path(item['book_root'])
    summary = read_book_computation(pre)
    facts, ack = _pair(pre, 'book_facts')
    if summary['source_provenance_class'] != provenance or (
        summary['computation_hash'] != ack['payload_hash']
    ):
        raise ValueError('owned window pre-book provenance/hash differs')
    snapshots = facts['projection']['snapshots']
    if len(snapshots) != 1:
        return summary, 'pre_snapshot_unavailable'
    snap = snapshots[0]
    quote = snap['quote']
    states = {'observed', 'one_sided_or_missing'} if binding_mode == 'observation' else {'observed'}
    if snap['state'] != quote['state'] or quote['state'] not in states:
        return summary, 'pre_snapshot_unavailable'
    member, mapping = item['member'], quote['mapping']
    if mapping is None or quote['token_id'] != member['token_id'] or (
        quote['condition_id'] != item['identity']['condition_id']
        or mapping['market_id'] != member['market_id']
    ):
        return summary, 'pre_identity_differs'
    if mapping.get('lifecycle') != {
        'active': True, 'closed': False, 'archived': False, 'acceptingOrders': True,
    }:
        return summary, 'pre_lifecycle_unavailable'
    return summary, None


def collect(root, index, item, policy, port):
    """Called in an isolated event loop thread; the worker drains this job on cancellation."""
    from .screening_worker import _save

    provenance = scope(port)['provenance_class']
    pre, missing = _pre_state(item, provenance, policy.binding_mode)
    started = _clock()
    socket, analysis = paths(root, index)
    socket_seal = None
    result = {'item': item, 'pre_computation': pre, 'read_started_at': started,
              'missing_reason': missing, 'analysis': None, 'socket': None}
    if missing is None:
        async def capture():
            args = dict(output_root=socket, policy=policy.binding, duration_ms=policy.duration_ms,
                        binding_mode=policy.binding_mode)
            if port is None:
                return await capture_market_socket(item['book_root'], **args)
            return await capture_loopback_socket(item['book_root'], port=port, **args)
        result['socket'] = asyncio.run(capture())
        # Seal before the analysis writer's full socket verification; never adopt a
        # changed post-verification byte stream as the authenticated window.
        socket_seal = _manifest((socket,), SOCKET_LIMITS['max_retained_bytes'])
        result['analysis'] = record_socket_analysis(socket, output_root=analysis,
                                                    policy=policy.analysis)
    result['completed_at'] = _clock()
    _save(root, f'window_{index:03d}', result)
    return result, socket_seal


def _worker(root, provenance):
    from .panel_declaration import read_panel_declaration
    from .screening_worker import allocation, worker_root

    wp, wa = _pair(root, 'worker_policy')
    config = policy_from_dict(wp['window_policy'])
    port = wp['window_port']
    if (wp['schema_version'] != version(config) or wp['build'] != verified_panel_build()
            or worker_root(wp['panel_root']) != root
            or wp['provenance_class'] != provenance or scope(port)['provenance_class'] != provenance
            or wp['reservation'] != allocation(
                read_panel_declaration(wp['panel_root']), windows=True)):
        raise ValueError('owned window worker lineage/reservation differs')
    return wp, wa, config


def _entry(root, index, item, wp, wa, config, pre, missing, socket, analysis):
    """Check the same persisted envelope for owned writer outputs and cold replay."""
    name = f'window_{index:03d}'
    entry, ack = _pair(root, name)
    socket_root, analysis_root = paths(root, index)
    expected = {name + '.json', name + '_ack.json'}
    if missing is None:
        sp, _ = _pair(socket_root, 'socket_window_policy')
        ap, _ = _pair(analysis_root, 'socket_analysis_policy')
        socket_version = (OBSERVATION_SOCKET_VERSION if config.binding_mode == 'observation'
                          else SOCKET_VERSION)
        if (sp['schema_version'] != socket_version
                or socket['schema_version'] != socket_version
                or sp['pre_computation_root'] != item['book_root']
                or sp['binding_policy'] != asdict(config.binding)
                or sp['transport'] != scope(wp['window_port'])
                or sp['duration_ms'] != config.duration_ms
                or socket['provenance_class'] != wp['provenance_class']
                or ap['socket_root'] != str(socket_root) or ap['post_root'] is not None
                or ap['policy'] != asdict(config.analysis)
                or not _ordered_clocks(entry['read_started_at'], sp['declared_at'],
                                       analysis['computation_available_at'],
                                       entry['completed_at'])):
            raise ValueError('owned window dependency policy/chronology differs')
        expected.update({socket_root.name, analysis_root.name})
    if (_json_bytes(entry['item']) != _json_bytes(item) or entry['pre_computation'] != pre
            or entry['missing_reason'] != missing or entry['socket'] != socket
            or entry['analysis'] != analysis
            or not _ordered_clocks(wa['durable_ack'], pre['computation_available_at'],
                                   entry['read_started_at'], entry['completed_at'],
                                   ack['durable_ack'])):
        raise ValueError('owned window entry replay differs')
    return expected, {
        'analysis_root': str(analysis_root) if analysis else None,
        'missing_reason': missing, 'entry_hash': ack['payload_hash'],
        'available_at': ack['durable_ack'],
    }


def _closure(root, expected):
    actual = {p.name for p in root.iterdir() if p.name.startswith(
        ('window_', 'fs2_socket_window_', 'fs2_socket_analysis_'))}
    if actual != expected:
        raise ValueError('owned window closure differs')


def _scope(selected, wp):
    if (not 1 <= len(selected) <= wp['reservation']['screen_slots']
            or len({i['member']['market_id'] for i in selected}) != len(selected)):
        raise ValueError('owned window scope differs')


def _result(root, wa, config, results):
    return {'worker_root': str(root), 'worker_policy_hash': wa['payload_hash'],
            'policy': policy_dict(config), 'members': results}


def read(root, selected, provenance):
    """Full bounded dependency replay, including in original-code recovery."""
    wp, wa, config = _worker(root, provenance)
    _scope(selected, wp)
    expected, results = set(), {}
    for index, item in enumerate(selected):
        pre, missing = _pre_state(item, provenance, config.binding_mode)
        socket_root, analysis_root = paths(root, index)
        socket = read_socket_window(socket_root) if missing is None else None
        analysis = read_socket_analysis(analysis_root) if missing is None else None
        names, result = _entry(root, index, item, wp, wa, config, pre, missing, socket, analysis)
        expected.update(names)
        results[item['member']['market_id']] = result
    _closure(root, expected)
    return _result(root, wa, config, results)


def _manifest(roots, max_bytes):
    """Bounded streaming byte seal; only owned, already verified writers mint a proof.

    Include directories as well as files so added/removed entries cannot escape the seal.
    Never follow symlinks or allocate an unbounded raw payload/listing.
    """
    result, total = {}, 0

    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns)

    def visit(path, depth=0):
        nonlocal total
        if depth > 8 or len(result) >= 3456 or path.resolve() != path:
            raise ValueError('owned window manifest path/count bound exceeded')
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            result[str(path)] = None
            with os.scandir(path) as entries:
                for entry in entries:
                    visit(Path(entry.path), depth + 1)
        elif stat.S_ISREG(info.st_mode):
            if info.st_size > max_bytes - total:
                raise ValueError('owned window manifest byte bound exceeded')
            digest, size = hashlib.sha256(), 0
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                if identity(os.fstat(stream.fileno())) != identity(info):
                    raise ValueError('owned window dependency changed during seal')
                while chunk := stream.read(1048576):
                    size += len(chunk)
                    if size > info.st_size:
                        raise ValueError('owned window dependency grew during seal')
                    digest.update(chunk)
                if (identity(os.fstat(stream.fileno())) != identity(info)
                        or identity(path.lstat()) != identity(info)):
                    raise ValueError('owned window dependency changed during seal')
            if size != info.st_size:
                raise ValueError('owned window dependency size differs')
            total += size
            result[str(path)] = (size, digest.hexdigest())
        else:
            raise ValueError('owned window dependency must be regular file/directory')

    for root in roots:
        visit(root)
    return result


def _prepare(root, selected, provenance):
    """Mint acquisition/finish closures, never accepting caller results or persisted proofs.

    Only per-index acquisition calls the real writer. Its bounded, private state cannot be
    populated by passing hashes, clocks, decoded histories or an externally acquired root.
    No full dependency replay is required before activation; cold readers remain unchanged.
    """
    from .book_computation import LIMITS as BOOK_LIMITS
    from .screening_worker import LIMITS

    wp, wa, config = _worker(root, provenance)
    _scope(selected, wp)
    frozen = _json_bytes(selected)
    if len(frozen) > LIMITS['artifact_bytes']:
        raise ValueError('owned window assignment context exceeds bound')
    selected = json.loads(frozen)
    policy_bytes = _json_bytes((wp, wa))
    bound = (wp['reservation']['source_bytes_per_screen']
             + BOOK_LIMITS['max_output_bytes'] + reservation(1) + LIMITS['artifact_bytes'] * 2)
    lock, claimed, completed = threading.Lock(), set(), {}
    finished = False

    def acquire(index):
        with lock:
            if (finished or type(index) is not int or not 0 <= index < len(selected)
                    or index in claimed):
                raise ValueError('owned window slot unavailable or already claimed')
            claimed.add(index)
        item = selected[index]
        pre = Path(item['book_root'])
        bp, _ = _pair(pre, 'book_policy')
        source = root / f'fs2_capture_screen_{index:03d}'
        if bp['source_root'] != str(source):
            raise ValueError('owned window source substituted')
        prior_roots = (pre, source)
        prior = _manifest(prior_roots, bound)
        value, socket_seal = collect(root, index, item, config, wp['window_port'])
        if _manifest(prior_roots, bound) != prior:
            raise ValueError('owned window prior dependency changed during acquisition')
        names, result = _entry(root, index, item, wp, wa, config,
            value['pre_computation'], value['missing_reason'], value['socket'], value['analysis'])
        roots = (*prior_roots, *(root / name for name in sorted(names)))
        seal = _manifest(roots, bound)
        entry, _ = _pair(root, f'window_{index:03d}')
        if _json_bytes(entry) != _json_bytes(value):
            raise ValueError('owned window writer result changed')
        if socket_seal is not None:
            socket, analysis = paths(root, index)
            if _manifest((socket,), SOCKET_LIMITS['max_retained_bytes']) != socket_seal:
                raise ValueError('owned window socket changed during analysis')
            facts, fa = _pair(analysis, 'socket_analysis_facts')
            inputs, ia = _pair(analysis, 'socket_analysis_input')
            _, pa = _pair(analysis, 'socket_analysis_policy')
            summary = value['analysis']
            if (fa['payload_hash'] != summary['computation_hash']
                    or fa['durable_ack'] != summary['computation_available_at']
                    or pa['payload_hash'] != summary['policy_hash']
                    or facts['policy_hash'] != pa['payload_hash']
                    or facts['input_hash'] != ia['payload_hash']
                    or inputs['inputs']['socket'] != value['socket']
                    or inputs['inputs']['pre_computation'] != value['pre_computation']):
                raise ValueError('owned window analysis differs from actual writer results')
        if _manifest(roots, bound) != seal:
            raise ValueError('owned window dependency changed while binding proof')
        # Serialize results now: callers never hold a mutable reference to the private proof.
        proof = _json_bytes(result)
        if len(proof) > LIMITS['artifact_bytes']:
            raise ValueError('owned window result context exceeds bound')
        with lock:
            completed[index] = (names, roots, seal, proof)

    def finish():
        nonlocal finished
        with lock:
            if finished or set(completed) != set(range(len(selected))):
                raise ValueError('owned window context incomplete or consumed')
            finished = True
        if (_json_bytes(_pair(root, 'worker_policy')) != policy_bytes
                or verified_panel_build() != wp['build']):
            raise ValueError('owned window policy/build changed after acquisition')
        expected, results = set(), {}
        for index, item in enumerate(selected):
            names, roots, seal, proof = completed[index]
            if _manifest(roots, bound) != seal:
                raise ValueError('owned window dependency changed after acquisition')
            expected.update(names)
            results[item['member']['market_id']] = json.loads(proof)
        _closure(root, expected)
        return _result(root, wa, config, results)

    return acquire, finish
