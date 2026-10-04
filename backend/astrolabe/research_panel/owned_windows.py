"""Bounded pre-origin observers owned by the selected screening worker, never caller history."""

import asyncio
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
from .socket_window_journal import read_socket_window, scope
from .window_computation import LIMITS as ANALYSIS_LIMITS
from .window_reconciliation import WindowReconciliationPolicy

VERSION = 'fs2-owned-window-worker-v6'


@dataclass(frozen=True)
class OwnedWindowPolicy:
    duration_ms: int
    binding: WindowBindingPolicy
    analysis: WindowReconciliationPolicy
    origin: OriginWindowPolicy

    def __post_init__(self):
        if (type(self.duration_ms) is not int or not 1 <= self.duration_ms <= 60000
                or type(self.binding) is not WindowBindingPolicy
                or type(self.analysis) is not WindowReconciliationPolicy
                or type(self.origin) is not OriginWindowPolicy):
            raise ValueError('explicit bounded owned window policies required')


def policy_from_dict(value):
    return OwnedWindowPolicy(value['duration_ms'], WindowBindingPolicy(**value['binding']),
        WindowReconciliationPolicy(**value['analysis']), OriginWindowPolicy(**value['origin']))


def reservation(slots):
    return slots * (SOCKET_LIMITS['max_retained_bytes'] + ANALYSIS_LIMITS['max_output_bytes'])


def paths(root, index):
    return (root / f'fs2_socket_window_{index:03d}',
            root / f'fs2_socket_analysis_{index:03d}')


def _pre_state(item, provenance):
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
    if snap['state'] != 'observed' or quote['state'] != 'observed':
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
    pre, missing = _pre_state(item, provenance)
    started = _clock()
    socket, analysis = paths(root, index)
    result = {'item': item, 'pre_computation': pre, 'read_started_at': started,
              'missing_reason': missing, 'analysis': None, 'socket': None}
    if missing is None:
        async def capture():
            args = dict(output_root=socket, policy=policy.binding, duration_ms=policy.duration_ms)
            if port is None:
                return await capture_market_socket(item['book_root'], **args)
            return await capture_loopback_socket(item['book_root'], port=port, **args)
        result['socket'] = asyncio.run(capture())
        result['analysis'] = record_socket_analysis(socket, output_root=analysis,
                                                    policy=policy.analysis)
    result['completed_at'] = _clock()
    _save(root, f'window_{index:03d}', result)
    return result


def read(root, selected, provenance):
    """Replay only bounded owned window inputs; complete selection authentication is upstream."""
    from .panel_declaration import read_panel_declaration
    from .screening_worker import allocation, worker_root

    wp, wa = _pair(root, 'worker_policy')
    config = policy_from_dict(wp['window_policy'])
    port = wp['window_port']
    if (wp['schema_version'] != VERSION or wp['build'] != verified_panel_build()
            or worker_root(wp['panel_root']) != root
            or wp['provenance_class'] != provenance or scope(port)['provenance_class'] != provenance
            or wp['reservation'] != allocation(
                read_panel_declaration(wp['panel_root']), windows=True)):
        raise ValueError('owned window worker lineage/reservation differs')
    if not 1 <= len(selected) <= wp['reservation']['screen_slots']:
        raise ValueError('owned window scope differs')
    expected, results = set(), {}
    for index, item in enumerate(selected):
        name = f'window_{index:03d}'
        entry, ack = _pair(root, name)
        pre, missing = _pre_state(item, provenance)
        socket_root, analysis_root = paths(root, index)
        socket = analysis = None
        if missing is None:
            socket = read_socket_window(socket_root)
            analysis = read_socket_analysis(analysis_root)
            sp, _ = _pair(socket_root, 'socket_window_policy')
            ap, _ = _pair(analysis_root, 'socket_analysis_policy')
            if (sp['pre_computation_root'] != item['book_root']
                    or sp['binding_policy'] != asdict(config.binding)
                    or sp['transport'] != scope(port)
                    or sp['duration_ms'] != config.duration_ms
                    or socket['provenance_class'] != provenance
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
        expected.update({name + '.json', name + '_ack.json'})
        results[item['member']['market_id']] = {
            'analysis_root': str(analysis_root) if analysis else None,
            'missing_reason': missing, 'entry_hash': ack['payload_hash'],
            'available_at': ack['durable_ack'],
        }
    actual = {p.name for p in root.iterdir() if p.name.startswith(
        ('window_', 'fs2_socket_window_', 'fs2_socket_analysis_'))}
    if actual != expected:
        raise ValueError('owned window closure differs')
    return {'worker_root': str(root), 'worker_policy_hash': wa['payload_hash'],
            'policy': asdict(config), 'members': results}
