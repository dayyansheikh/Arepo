"""Finite raw stream evidence with actual clocks; synthetic capture only in v1."""

import shutil
import time

from astrolabe.feature_store.capture import (
    _clock,
    _digest,
    _json_bytes,
    _sync_directory,
    _write_once,
)
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist
from astrolabe.feature_store.sources import SOURCES
from astrolabe.feature_store.types import HASH_PATTERN, uint_text

from .build_identity import verified_panel_build
from .input_read import _canonical

VERSION = 'fs2-synthetic-window-v1'
LIMITS = {'max_frames': 1000, 'max_frame_bytes': 262144, 'max_raw_bytes': 16 * 1048576,
          'max_retained_bytes': 32 * 1048576, 'failure_reserve_bytes': 65536,
          'free_reserve_bytes': 2 * 1024**3, 'max_events': 1032, 'max_metadata_bytes': 65536,
          'heartbeat_interval_ms': 10000, 'max_processing_seconds': 180}
KINDS = {'connected', 'subscription_intent', 'subscription_sent', 'ping_intent', 'ping_sent',
         'received', 'disconnected', 'interval_ended', 'budget_stop', 'closed'}


def _size(root):
    entries = list(root.iterdir())
    if len(entries) > 3 * LIMITS['max_events'] + 8:
        raise ValueError('window file count exceeded')
    total = 0
    for path in entries:
        if path.is_symlink() or not path.is_file():
            raise ValueError('nonfile/symlink window entry')
        size = path.stat().st_size
        cap = LIMITS['max_frame_bytes'] if path.suffix == '.bin' else LIMITS['max_metadata_bytes']
        if size > cap:
            raise ValueError('window artefact size exceeded')
        total += size
    if total > LIMITS['max_retained_bytes']:
        raise ValueError('window retained budget exceeded')
    return total


def _policy(token_id, condition_id, duration_ms):
    token_id = uint_text(token_id, bits=256)
    if (not isinstance(condition_id, str) or not condition_id or len(condition_id) > 128
            or type(duration_ms) is not int or not 1 <= duration_ms <= 60000):
        raise ValueError('bounded explicit window identity/duration required')
    return {'token_id': token_id, 'condition_id': condition_id, 'duration_ms': duration_ms,
            'subscription': {'assets_ids': [token_id], 'type': 'market'},
            'endpoint': SOURCES['clob.market_stream'].endpoint}


class WindowJournal:
    """Internal synthetic driver boundary; supplied payloads can never claim live provenance."""

    def __init__(self, root, *, token_id, condition_id, duration_ms):
        self.root = _canonical(root)
        if not self.root.name.startswith('fs2_window_'):
            raise ValueError('fs2_window_ directory required')
        policy = _policy(token_id, condition_id, duration_ms)
        self.build = verified_panel_build()
        if shutil.disk_usage(self.root.parent).free < (
            LIMITS['max_retained_bytes'] + LIMITS['free_reserve_bytes']
        ):
            raise ValueError('window storage reserve unavailable')
        self.started = time.monotonic()
        self.count = self.raw_bytes = self.frames = 0
        self.last_hash = None
        self.root.mkdir(mode=0o700)
        _sync_directory(self.root.parent)
        self.save('window_policy', {'schema_version': VERSION, 'limits': dict(LIMITS),
                  'build': self.build, 'policy': policy, 'provenance_class': 'synthetic',
                  'declared_at': _clock()})

    def reserve(self, addition):
        if time.monotonic() - self.started > LIMITS['max_processing_seconds']:
            raise ValueError('window processing deadline exceeded')
        if _size(self.root) + addition > (
            LIMITS['max_retained_bytes'] - LIMITS['failure_reserve_bytes']
        ):
            raise ValueError('window retained budget exhausted')
        if shutil.disk_usage(self.root).free < LIMITS['free_reserve_bytes'] + addition:
            raise ValueError('window free-space reserve exhausted')

    def save(self, name, value):
        data = _json_bytes(value)
        if len(data) > LIMITS['max_metadata_bytes']:
            raise ValueError('window metadata budget exceeded')
        self.reserve(len(data) + 4096)
        _persist(self.root, name, value)

    def event(self, kind, raw=b'', *, error=None):
        observed = _clock()
        if kind not in KINDS or type(raw) not in {bytes, str}:
            raise ValueError('explicit window event and raw bytes/text required')
        if self.count >= LIMITS['max_events']:
            raise ValueError('window event budget exhausted')
        wire_type = 'text' if isinstance(raw, str) else 'binary'
        raw = raw.encode('utf-8') if isinstance(raw, str) else raw
        limit = min(LIMITS['max_frame_bytes'], LIMITS['max_raw_bytes'] - self.raw_bytes)
        kept = raw[:limit]
        truncated = len(raw) > len(kept)
        self.reserve(len(kept) + 8192)
        name = 'event_' + str(self.count + 1).zfill(6)
        _write_once(self.root / (name + '.bin'), kept)
        self.save(name, {'schema_version': VERSION, 'ordinal': self.count + 1, 'kind': kind,
                  'observed_at': observed, 'previous_hash': self.last_hash,
                  'raw_hash': _digest(kept), 'raw_bytes': len(kept), 'wire_type': wire_type,
                  'received_bytes': len(raw), 'received_hash': _digest(raw),
                  'truncated': truncated, 'error': error})
        _, ack = _pair(self.root, name)
        self.count += 1
        self.frames += kind == 'received'
        self.raw_bytes += len(kept)
        self.last_hash = ack['payload_hash']
        return observed, truncated

    def failure(self, exc):
        # Bounded reserve remains after ordinary writes; never overwrite a partial failure.
        _persist(self.root, 'window_failure', {'schema_version': VERSION,
                                             'error_class': type(exc).__name__, 'at': _clock()})

    def finish(self):
        if verified_panel_build() != self.build:
            raise ValueError('window build changed')
        policy, ack = _pair(self.root, 'window_policy')
        report = _replay(self.root, policy, ack, self.count)[0]
        self.save('window_report', report)
        return read_window(self.root)


def _replay(root, declaration, policy_ack, count):
    if (declaration['schema_version'] != VERSION or declaration['limits'] != LIMITS
            or declaration['build'] != verified_panel_build()
            or declaration['provenance_class'] != 'synthetic'):
        raise ValueError('window build/policy differs')
    policy = declaration['policy']
    if policy != _policy(policy['token_id'], policy['condition_id'], policy['duration_ms']):
        raise ValueError('window scope differs')
    started = time.monotonic()
    last_clock, last_hash = policy_ack['durable_ack'], None
    if not _ordered_clocks(declaration['declared_at'], last_clock):
        raise ValueError('window declaration chronology regressed')
    expected = {'window_policy.json', 'window_policy_ack.json'}
    raw_bytes = frames = 0
    kinds, anchor, ended, pending_send, terminal = [], None, None, None, None
    truncated_previous = False
    late_frames = ping_count = 0
    for ordinal in range(1, count + 1):
        if time.monotonic() - started > LIMITS['max_processing_seconds']:
            raise ValueError('window replay processing deadline exceeded')
        name = 'event_' + str(ordinal).zfill(6)
        expected.update({name + '.bin', name + '.json', name + '_ack.json'})
        event, ack = _pair(root, name)
        raw = (root / (name + '.bin')).read_bytes()
        kind, observed = event['kind'], event['observed_at']
        if (event['schema_version'] != VERSION or event['ordinal'] != ordinal
                or kind not in KINDS or event['previous_hash'] != last_hash
                or event['raw_hash'] != _digest(raw) or event['raw_bytes'] != len(raw)
                or event['wire_type'] not in {'text', 'binary'}
                or not isinstance(event['received_hash'], str)
                or not HASH_PATTERN.fullmatch(event['received_hash'])
                or observed['clock_session_id'] != policy_ack['durable_ack']['clock_session_id']
                or ack['durable_ack']['clock_session_id'] != observed['clock_session_id']
                or type(event['received_bytes']) is not int or event['received_bytes'] < len(raw)
                or type(event['truncated']) is not bool
                or event['truncated'] != (event['received_bytes'] > len(raw))
                or (not event['truncated'] and event['received_hash'] != _digest(raw))
                or not _ordered_clocks(last_clock, observed, ack['durable_ack'])):
            raise ValueError('window event lineage/raw/chronology differs')
        if truncated_previous and kind != 'budget_stop':
            raise ValueError('truncated window must stop')
        if event['truncated'] and len(raw) != min(
            LIMITS['max_frame_bytes'], LIMITS['max_raw_bytes'] - raw_bytes
        ):
            raise ValueError('window truncated prefix size differs')
        truncated_previous = event['truncated']
        if truncated_previous and kind != 'received':
            raise ValueError('truncated outbound window event')
        if (kind == 'connected' and ordinal != 1) or (ordinal == 1 and kind != 'connected'):
            raise ValueError('window connection ordering differs')
        if kind == 'subscription_intent':
            if kinds != ['connected'] or raw != _json_bytes(policy['subscription']):
                raise ValueError('window subscription differs')
            pending_send = kind
        elif kind == 'subscription_sent':
            if pending_send != 'subscription_intent' or kinds[-1] != pending_send:
                raise ValueError('window subscription send without intent')
            anchor, pending_send = observed, None
        elif kind in {'ping_intent', 'ping_sent', 'received', 'interval_ended',
                      'budget_stop', 'disconnected'}:
            if anchor is None or terminal is not None:
                raise ValueError('window event outside interval')
            if kind == 'ping_intent':
                if pending_send is not None or raw != b'PING':
                    raise ValueError('window ping intent differs')
                ping_count += 1
                if (int(observed['monotonic_ns']) - int(anchor['monotonic_ns'])
                        < ping_count * LIMITS['heartbeat_interval_ms'] * 1000000):
                    raise ValueError('window heartbeat before fixed schedule')
                pending_send = kind
            elif kind == 'ping_sent':
                if pending_send != 'ping_intent' or kinds[-1] != pending_send:
                    raise ValueError('window ping without intent')
                pending_send = None
            if kind in {'interval_ended', 'budget_stop', 'disconnected'}:
                terminal, ended = kind, observed
        elif kind == 'closed':
            if ordinal != count or terminal is None or pending_send is not None:
                raise ValueError('window close ordering differs')
        if kind not in {'received', 'subscription_intent', 'ping_intent'} and raw:
            raise ValueError('unexpected window event raw payload')
        if kind == 'received' and (int(observed['monotonic_ns'])
                >= int(anchor['monotonic_ns']) + policy['duration_ms'] * 1000000):
            late_frames += 1
        raw_bytes += len(raw)
        frames += kind == 'received'
        if frames > LIMITS['max_frames'] or raw_bytes > LIMITS['max_raw_bytes']:
            raise ValueError('window source budget differs')
        kinds.append(kind)
        last_clock, last_hash = ack['durable_ack'], ack['payload_hash']
    if not kinds or kinds[-1] != 'closed' or anchor is None or ended is None:
        raise ValueError('sealed terminal window required')
    elapsed_ns = int(ended['monotonic_ns']) - int(anchor['monotonic_ns'])
    if terminal == 'interval_ended' and elapsed_ns < policy['duration_ms'] * 1000000:
        raise ValueError('window interval ended prematurely')
    return {'schema_version': VERSION, 'policy_hash': policy_ack['payload_hash'],
            'event_count': count, 'last_event_hash': last_hash, 'frame_count': frames,
            'retained_raw_bytes': raw_bytes, 'late_frame_count': late_frames,
            'subscription_sent_at': anchor,
            'ended_at': ended, 'elapsed_ns': str(elapsed_ns), 'terminal': terminal,
            'state': 'duration_completed' if terminal == 'interval_ended' else 'incomplete',
            'provenance_class': 'synthetic', 'complete_continuous_history': False,
            'native_clock_admitted': False, 'origin_admitted': False,
            'feature_store_admitted': False}, expected


def read_window(root):
    root = _canonical(root)
    if not root.name.startswith('fs2_window_'):
        raise ValueError('fs2_window_ directory required')
    _size(root)
    policy, policy_ack = _pair(root, 'window_policy')
    facts, ack = _pair(root, 'window_report')
    count = facts['event_count']
    if type(count) is not int or not 1 <= count <= LIMITS['max_events']:
        raise ValueError('bounded window event count required')
    replay, expected = _replay(root, policy, policy_ack, count)
    expected.update({'window_report.json', 'window_report_ack.json'})
    _, last_ack = _pair(root, 'event_' + str(count).zfill(6))
    if (facts != replay or {p.name for p in root.iterdir()} != expected
            or not _ordered_clocks(last_ack['durable_ack'], ack['durable_ack'])):
        raise ValueError('window report/closure differs')
    return {**facts, 'window_report_hash': ack['payload_hash'],
            'window_available_at': ack['durable_ack']}
