"""Durably bind a synthetic window to identity actually known before subscription."""

import shutil
import time
from dataclasses import asdict, dataclass
from datetime import timedelta

from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist, _time

from .book_computation import read_book_computation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .quote_inputs import _at
from .window_capture import SyntheticWindowFeed, capture_window
from .window_journal import _size as window_size
from .window_journal import read_window

VERSION = 'fs2-bound-synthetic-window-v1'
CHILD = 'fs2_window_capture'
LIMITS = {'max_output_bytes': 40 * 1048576, 'max_metadata_bytes': 2 * 1048576,
          'max_seconds': 180, 'failure_reserve_bytes': 65536,
          'free_reserve_bytes': 2 * 1024**3}


@dataclass(frozen=True)
class WindowBindingPolicy:
    max_quote_age_ms: int
    max_identity_age_ms: int
    version: str = 'fs2-window-binding-policy-v1'

    def __post_init__(self):
        if (any(type(v) is not int or not 0 <= v <= 300000 for v in
                (self.max_quote_age_ms, self.max_identity_age_ms))
                or self.version != 'fs2-window-binding-policy-v1'):
            raise ValueError('explicit bounded source freshness policy required')


def _pre(root):
    summary = read_book_computation(root)
    facts, ack = _pair(root, 'book_facts')
    declaration, _ = _pair(root, 'book_policy')
    if ack['payload_hash'] != summary['computation_hash']:
        raise ValueError('pre-window facts changed during read')
    projection = facts['projection']
    inventory = projection['source_inventory']
    if (len(projection['snapshots']) != 1
            or sorted(v['source_id'] for v in inventory) != ['clob.book', 'gamma.market']
            or any(v['missing_reason'] != 'observed' for v in inventory)):
        raise ValueError('one observed targeted identity/book pair required')
    snapshot = projection['snapshots'][0]
    quote = snapshot['quote']
    if snapshot['state'] != 'observed' or quote['state'] != 'observed':
        raise ValueError('observed pre-window quote and components required')
    mapping = quote['mapping']
    if mapping.get('lifecycle') != {
        'active': True, 'closed': False, 'archived': False, 'acceptingOrders': True,
    }:
        raise ValueError('explicit active source lifecycle required')
    return {'pre_computation': summary, 'pre_source_root': declaration['source_root'],
            'identity': {**{key: mapping[key] for key in ('market_id', 'mapping_version',
                         'outcome_index', 'outcome_label', 'lifecycle')},
                         'token_id': quote['token_id'], 'condition_id': quote['condition_id']},
            'quote_received_at': quote['received_at'],
            'identity_received_at': mapping['received_at'],
            'identity_available_at': mapping['available_at'],
            'book_observation_id': quote['observation_id'],
            'identity_observation_id': mapping['observation_id']}


def _fresh(binding, at, policy):
    return all(timedelta(0) <= _time(at) - _at(binding[field]) <= timedelta(milliseconds=limit)
               for field, limit in (('quote_received_at', policy.max_quote_age_ms),
                                    ('identity_received_at', policy.max_identity_age_ms)))


def _paths(pre_root, output_root):
    pre, root = _canonical(pre_root), _canonical(output_root)
    declaration, _ = _pair(pre, 'book_policy')
    dependencies = [pre, _canonical(declaration['source_root'])]
    if (not root.name.startswith('fs2_bound_window_')
            or any(root == p or p in root.parents or root in p.parents for p in dependencies)):
        raise ValueError('separate bound window outside all pre-window evidence required')
    return pre, root


def _check(root, started, addition=0):
    if time.monotonic() - started > LIMITS['max_seconds']:
        raise ValueError('bound window processing deadline exceeded')
    entries = list(root.iterdir())
    if len(entries) > 9:
        raise ValueError('bound window entry count exceeded')
    total = 0
    for p in entries:
        if p.is_symlink():
            raise ValueError('bound window symlink refused')
        if p.is_dir() and p.name == CHILD:
            total += window_size(p)
        elif p.is_file() and p.stat().st_size <= LIMITS['max_metadata_bytes']:
            total += p.stat().st_size
        else:
            raise ValueError('unexpected bound window entry')
    if total + addition > LIMITS['max_output_bytes'] - LIMITS['failure_reserve_bytes']:
        raise ValueError('bound window retained budget exceeded')
    if addition and shutil.disk_usage(root).free < LIMITS['free_reserve_bytes'] + addition:
        raise ValueError('bound window free reserve reached')


def _save(root, name, value, started):
    size = len(_json_bytes(value))
    if size > LIMITS['max_metadata_bytes']:
        raise ValueError('bound window metadata budget exceeded')
    _check(root, started, size + 4096)
    _persist(root, name, value)


async def capture_bound_window(pre_computation_root, *, output_root, feed, policy,
                               duration_ms=60000):
    if type(feed) is not SyntheticWindowFeed or type(policy) is not WindowBindingPolicy:
        raise ValueError('synthetic feed and explicit window binding policy required')
    if type(duration_ms) is not int or not 1 <= duration_ms <= 60000:
        raise ValueError('bounded window duration required')
    pre, root = _paths(pre_computation_root, output_root)
    if root.exists():
        raise FileExistsError('bound window is terminal; no overwrite/resume')
    if shutil.disk_usage(root.parent).free < (
        LIMITS['free_reserve_bytes'] + LIMITS['max_output_bytes']
    ):
        raise ValueError('bound window full storage reserve unavailable')
    build, started = verified_panel_build(), time.monotonic()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'bound_window_policy', {'schema_version': VERSION, 'build': build,
              'limits': dict(LIMITS), 'pre_computation_root': str(pre), 'child': CHILD,
              'binding_policy': asdict(policy), 'duration_ms': duration_ms,
              'declared_at': _clock()}, started)
        _, pa = _pair(root, 'bound_window_policy')
        read_started = _clock()
        binding = _pre(pre)
        completed = _clock()
        if (binding['pre_computation']['source_provenance_class'] != 'synthetic'
                or not _ordered_clocks(binding['pre_computation']['computation_available_at'],
                                       read_started)):
            raise ValueError('synthetic pre-window evidence must precede its actual read')
        if not _fresh(binding, completed, policy):
            raise ValueError('pre-window source evidence stale before binding')
        _save(root, 'bound_window_binding', {**binding, 'policy_hash': pa['payload_hash'],
              'read_started_at': read_started, 'read_completed_at': completed}, started)
        _, ba = _pair(root, 'bound_window_binding')
        if not _fresh(binding, ba['durable_ack'], policy):
            raise ValueError('pre-window source evidence stale at binding durability')
        _check(root, started, 32 * 1048576)
        await capture_window(root / CHILD, token_id=binding['identity']['token_id'],
                             condition_id=binding['identity']['condition_id'], feed=feed,
                             duration_ms=duration_ms)
        report = _replay(root)[0]
        _save(root, 'bound_window_report', report, started)
        result = read_bound_window(root)
        _check(root, started)
        return result
    except BaseException as exc:
        try:
            _persist(root, 'bound_window_failure', {'schema_version': VERSION,
                        'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def _replay(root):
    declaration, pa = _pair(root, 'bound_window_policy')
    pre, root = _paths(declaration['pre_computation_root'], root)
    policy = WindowBindingPolicy(**declaration['binding_policy'])
    if (declaration['schema_version'] != VERSION or declaration['limits'] != LIMITS
            or declaration['build'] != verified_panel_build() or declaration['child'] != CHILD):
        raise ValueError('bound window build/policy differs')
    binding, ba = _pair(root, 'bound_window_binding')
    expected = _pre(pre)
    if (any(binding[key] != value for key, value in expected.items())
            or binding['policy_hash'] != pa['payload_hash']
            or expected['pre_computation']['source_provenance_class'] != 'synthetic'
            or not _ordered_clocks(declaration['declared_at'], pa['durable_ack'],
                binding['read_started_at'], binding['read_completed_at'], ba['durable_ack'])
            or not _ordered_clocks(expected['pre_computation']['computation_available_at'],
                                   binding['read_started_at'])
            or not _fresh(binding, binding['read_completed_at'], policy)
            or not _fresh(binding, ba['durable_ack'], policy)):
        raise ValueError('bound window identity/read/freshness differs')
    window = read_window(root / CHILD)
    child, ca = _pair(root / CHILD, 'window_policy')
    if (child['policy']['token_id'] != binding['identity']['token_id']
            or child['policy']['condition_id'] != binding['identity']['condition_id']
            or child['policy']['duration_ms'] != declaration['duration_ms']
            or window['provenance_class'] != 'synthetic'
            or not _ordered_clocks(ba['durable_ack'], child['declared_at'], ca['durable_ack'],
                                   window['subscription_sent_at'], window['window_available_at'])):
        raise ValueError('bound window subscription/identity lineage differs')
    state = ('fresh_at_subscription' if _fresh(binding, window['subscription_sent_at'], policy)
             else 'identity_expired_before_subscription')
    return {'schema_version': VERSION, 'policy_hash': pa['payload_hash'],
            'binding_hash': ba['payload_hash'], 'binding_available_at': ba['durable_ack'],
            'identity': binding['identity'], 'window': window, 'state': state,
            'provenance_class': 'synthetic', 'origin_admitted': False,
            'feature_store_admitted': False, 'continuous_sequence_proven': False}, window


def read_bound_window(root):
    root, started = _canonical(root), time.monotonic()
    expected = {CHILD, *[name + suffix for name in ('bound_window_policy', 'bound_window_binding',
                'bound_window_report') for suffix in ('.json', '_ack.json')]}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('complete successful bound window closure required')
    _check(root, started)
    report, window = _replay(root)
    facts, ack = _pair(root, 'bound_window_report')
    if (facts != report or not _ordered_clocks(window['window_available_at'], ack['durable_ack'])):
        raise ValueError('bound window report differs')
    _check(root, started)
    return {**facts, 'bound_window_report_hash': ack['payload_hash'],
            'bound_window_available_at': ack['durable_ack']}
