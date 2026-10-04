"""Durable endpoint diagnostics; agreement never repairs gaps or admits a feature."""

import shutil
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from fractions import Fraction

from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory, verify_capture
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist, _time
from astrolabe.feature_store.types import canonical_json

from .book_computation import read_book_computation
from .book_primitives import _number, _ratio
from .bound_window import CHILD, read_bound_window
from .build_identity import verified_panel_build
from .input_read import _canonical
from .quote_computation import _inputs as book_rows
from .quote_inputs import _at
from .window_computation import _inputs as window_inputs
from .window_coverage import WindowCoveragePolicy, project_window_coverage

VERSION = 'fs2-window-reconciliation-v1'
LIMITS = {'max_output_bytes': 16 * 1048576, 'max_metadata_bytes': 4 * 1048576,
          'max_seconds': 180, 'failure_reserve_bytes': 65536,
          'free_reserve_bytes': 2 * 1024**3}
FIELDS = ('bid', 'ask', 'bid_size', 'ask_size')


@dataclass(frozen=True)
class WindowReconciliationPolicy:
    max_post_age_ms: int
    max_endpoint_separation_ms: int
    max_receipt_hold_ms: int
    version: str = 'fs2-window-reconciliation-policy-v1'

    def __post_init__(self):
        if (any(type(v) is not int or not 0 <= v <= 300000 for v in
                (self.max_post_age_ms, self.max_endpoint_separation_ms))
                or self.version != 'fs2-window-reconciliation-policy-v1'):
            raise ValueError('explicit bounded endpoint freshness policy required')
        WindowCoveragePolicy(self.max_receipt_hold_ms)


def dependencies(bound_root, post_root):
    bound, post = _canonical(bound_root), _canonical(post_root)
    declaration, _ = _pair(bound, 'bound_window_policy')
    pre = _canonical(declaration['pre_computation_root'])
    roots = [bound, post, pre]
    for computation in (pre, post):
        policy, _ = _pair(computation, 'book_policy')
        roots.append(_canonical(policy['source_root']))
    return roots


def _paths(bound_root, post_root, output_root):
    roots, root = dependencies(bound_root, post_root), _canonical(output_root)
    if (not root.name.startswith('fs2_window_reconciliation_')
            or any(root == p or p in root.parents or root in p.parents for p in roots)):
        raise ValueError('separate reconciliation outside all transitive evidence required')
    return roots, root


def _book(root):
    summary = read_book_computation(root)
    facts, ack = _pair(root, 'book_facts')
    if summary['computation_hash'] != ack['payload_hash']:
        raise ValueError('book facts changed during consumption')
    return summary, facts['projection'], book_rows(root, facts['input_read'])


def _load(bound_root, post_root):
    bound = read_bound_window(bound_root)
    binding, _ = _pair(bound_root, 'bound_window_binding')
    declaration, _ = _pair(bound_root, 'bound_window_policy')
    pre_summary, pre, _ = _book(_canonical(declaration['pre_computation_root']))
    if pre_summary != binding['pre_computation']:
        raise ValueError('pre-window computation changed during reconciliation read')
    post_summary, post, rows = _book(post_root)
    if (pre_summary['source_provenance_class'] != 'synthetic'
            or post_summary['source_provenance_class'] != 'synthetic'):
        raise ValueError('synthetic endpoint provenance required')
    policy, _ = _pair(post_root, 'book_policy')
    source = _canonical(policy['source_root'])
    receipts = []
    for row in rows:
        path = _canonical(row['request_metadata']['capture_uri'])
        if path.parent != source:
            raise ValueError('post receipt outside verified source root')
        capture = verify_capture(path)
        receipt = capture['receipt']
        if (capture['raw_ack']['receipt_hash'] != row['request_metadata']['receipt_hash']
                or receipt['raw_hash'] != row['payload_hash']
                or receipt['source_id'] != row['source_id']
                or receipt['capture_id'] != row['request_id']
                or receipt['request'] != row['request_metadata']['request']):
            raise ValueError('post receipt differs from verified source observation')
        receipts.append({'observation_id': row['id'], 'source_id': row['source_id'],
                         'receipt_hash': capture['raw_ack']['receipt_hash'],
                         'request': receipt['request'],
                         'request_started': receipt['request_started'],
                         'first_received': receipt['first_received'],
                         'raw_available_at': capture['raw_ack']['durable_ack'],
                         'missing_reason': row['missing_reason']})
    window, events = window_inputs(bound_root / CHILD)
    if window['source_summary'] != bound['window']:
        raise ValueError('bound window changed during consumption')
    inputs = {'bound_window': bound, 'pre_computation': pre_summary,
              'post_computation': post_summary, 'post_receipts': receipts,
              'window_input': window, 'original_identity_available_at':
              binding['identity_available_at']}
    return inputs, (pre, post, events)


def _fraction(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def _offset_ms(later, earlier):
    delta = _at(later) - _at(earlier)
    return _ratio(Fraction((delta.days * 86400 + delta.seconds) * 1000000
                           + delta.microseconds, 1000))


def _comparison(left, right):
    if left is None or right is None:
        return {'state': 'unavailable', 'left': left, 'right': right, 'right_minus_left': None}
    differences = {k: _ratio(_fraction(right[k]) - _fraction(left[k])) for k in FIELDS}
    return {'state': 'agreement' if all(v['numerator'] == '0' for v in differences.values())
            else 'disagreement', 'left': left, 'right': right, 'right_minus_left': differences}


def _project(inputs, material, policy, at):
    pre, post, events = material
    window = inputs['window_input']
    coverage = project_window_coverage(window['source_policy'], window['source_summary'], events,
                                       policy=WindowCoveragePolicy(policy.max_receipt_hold_ms))
    return _endpoints(inputs, pre, post, coverage, policy, at)


def _endpoints(inputs, pre, post, coverage, policy, at):
    """Pure shared arithmetic; only the owning verified consumer authenticates its envelope."""
    bound = inputs['bound_window']
    items = [v for v in coverage['items'] if v['snapshot'] is not None]
    frames = {v['frame']: v for v in coverage['frames']}
    first = items[0] if items else None
    last = items[-1] if items and coverage['end_imbalance'] is not None else None
    receipts = inputs['post_receipts']
    reasons = []
    if bound['state'] != 'fresh_at_subscription':
        reasons.append('pre_binding_expired')
    if sorted(v['source_id'] for v in receipts) != ['clob.book', 'gamma.market']:
        reasons.append('post_source_pair_unavailable')
    boundary = bound['bound_window_available_at']
    for receipt in receipts:
        if not _ordered_clocks(boundary, receipt['request_started']):
            reasons.append('post_request_not_after_bound_ack')
        if receipt['missing_reason'] != 'observed':
            reasons.append('post_' + receipt['source_id'] + '_' + receipt['missing_reason'])
        if not timedelta(0) <= _time(at) - _time(receipt['first_received']) <= timedelta(
            milliseconds=policy.max_post_age_ms
        ):
            reasons.append('post_source_stale_at_computation')
        request = receipt['request']
        if receipt['source_id'] == 'clob.book' and request['params'].get('token_id') != bound[
            'identity']['token_id']:
            reasons.append('post_requested_token_changed')
        if receipt['source_id'] == 'gamma.market' and request['path_params'].get('id') != (
            bound['identity']['market_id']
        ):
            reasons.append('post_requested_market_changed')
    snapshot = post['snapshots'][0] if len(post['snapshots']) == 1 else None
    quote = snapshot['quote'] if snapshot else None
    if snapshot is None or snapshot['state'] != 'observed':
        reasons.append('post_' + (snapshot['state'] if snapshot else 'snapshot_unavailable'))
    identity = bound['identity']
    mapping = quote['mapping'] if quote else None
    if (mapping is None or any(mapping.get(k) != identity[k] for k in
        ('market_id', 'mapping_version', 'outcome_index', 'outcome_label', 'lifecycle'))
        or quote['token_id'] != identity['token_id']
        or quote['condition_id'] != identity['condition_id']):
        reasons.append('post_identity_or_rules_changed_or_unavailable')
    if last is None:
        reasons.append('window_end_unavailable')
    first_clock = frames[first['frame']]['received_at'] if first else None
    last_clock = frames[last['frame']]['received_at'] if last else None
    post_clock = quote['received_at'] if quote else None
    offset = _offset_ms(post_clock, last_clock['utc']) if post_clock and last_clock else None
    if offset is not None and not 0 <= _fraction(offset) <= policy.max_endpoint_separation_ms:
        reasons.append('post_endpoint_separation_exceeded')
    pre_quote = pre['snapshots'][0]['quote']
    def values(q):
        return {k: _ratio(_number(q[k])) for k in FIELDS}
    start = _comparison(values(pre_quote), {k: first['snapshot'][k] for k in FIELDS}
                        if first else None)
    # Keep raw post facts in their primary computation even when comparison is inadmissible.
    end = _comparison({k: last['snapshot'][k] for k in FIELDS} if last else None,
                      values(quote) if not reasons else None)
    return {'schema_version': VERSION, 'state': 'comparable' if not reasons else 'unavailable',
            'reasons': sorted(set(reasons)), 'comparison_scope': 'best_bid_ask_price_and_size',
            'units': pre['units'],
            'start_comparison': start, 'end_comparison': end,
            'first_stream_item': first['item_id'] if first else None,
            'last_stream_item': last['item_id'] if last else None,
            'first_stream_received_at': first_clock, 'last_stream_received_at': last_clock,
            'pre_to_first_stream_ms': _offset_ms(first_clock['utc'], pre_quote['received_at'])
            if first_clock else None, 'last_stream_to_post_ms': offset,
            'post_quote': quote, 'source_inventory': post['source_inventory'],
            'original_identity': identity,
            'original_identity_available_at': inputs['original_identity_available_at'],
            'raw_window_ended_at': bound['window']['ended_at'],
            'post_request_boundary': boundary,
            'coverage_projection_hash': coverage['projection_hash'],
            'uncovered_duration_ns': coverage['uncovered_duration_ns'],
            'provenance_class': bound['provenance_class'], 'continuous_sequence_proven': False,
            'full_book_equivalence': False, 'origin_admitted': False,
            'feature_store_admitted': False}


def _check(root, started, addition=0):
    if time.monotonic() - started > LIMITS['max_seconds']:
        raise ValueError('reconciliation processing deadline exceeded')
    files = list(root.iterdir())
    if len(files) > 8 or any(p.is_symlink() or not p.is_file() for p in files):
        raise ValueError('invalid reconciliation closure')
    sizes = [p.stat().st_size for p in files]
    if any(n > LIMITS['max_metadata_bytes'] for n in sizes):
        raise ValueError('reconciliation metadata budget exceeded')
    if sum(sizes) + addition > LIMITS['max_output_bytes'] - LIMITS['failure_reserve_bytes']:
        raise ValueError('reconciliation retained budget exceeded')
    if addition and shutil.disk_usage(root).free < LIMITS['free_reserve_bytes'] + addition:
        raise ValueError('reconciliation free reserve reached')


def _save(root, name, payload, started):
    size = len(_json_bytes(payload))
    if size > LIMITS['max_metadata_bytes']:
        raise ValueError('reconciliation metadata budget exceeded')
    _check(root, started, size + 4096)
    _persist(root, name, payload)


def record_window_reconciliation(bound_root, post_root, *, output_root, policy):
    roots, root = _paths(bound_root, post_root, output_root)
    bound_root, post_root = roots[:2]
    if type(policy) is not WindowReconciliationPolicy:
        raise ValueError('explicit reconciliation policy required')
    if root.exists():
        raise FileExistsError('reconciliation terminal; no overwrite/resume')
    if shutil.disk_usage(root.parent).free < (
        LIMITS['free_reserve_bytes'] + LIMITS['max_output_bytes']
    ):
        raise ValueError('reconciliation full storage reserve unavailable')
    started, build = time.monotonic(), verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'window_reconciliation_policy', {'schema_version': VERSION, 'build': build,
              'limits': dict(LIMITS), 'bound_root': str(bound_root), 'post_root': str(post_root),
              'policy': asdict(policy), 'declared_at': _clock()}, started)
        _, pa = _pair(root, 'window_reconciliation_policy')
        read_started = _clock()
        inputs, material = _load(bound_root, post_root)
        completed = _clock()
        _save(root, 'window_reconciliation_input', {'inputs': inputs,
              'policy_hash': pa['payload_hash'], 'read_started_at': read_started,
              'read_completed_at': completed}, started)
        _, ia = _pair(root, 'window_reconciliation_input')
        compute_started = _clock()
        result = _project(inputs, material, policy, compute_started)
        computed = _clock()
        _save(root, 'window_reconciliation_report', {'policy_hash': pa['payload_hash'],
              'input_hash': ia['payload_hash'], 'computation_started_at': compute_started,
              'computed_at': computed, **result}, started)
        return read_window_reconciliation(root)
    except BaseException as exc:
        try:
            _persist(root, 'window_reconciliation_failure', {'schema_version': VERSION,
                'exception_type': type(exc).__name__, 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_window_reconciliation(root):
    root, started = _canonical(root), time.monotonic()
    expected = {name + suffix for name in ('window_reconciliation_policy',
                'window_reconciliation_input', 'window_reconciliation_report')
                for suffix in ('.json', '_ack.json')}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('complete successful reconciliation closure required')
    _check(root, started)
    declaration, pa = _pair(root, 'window_reconciliation_policy')
    roots, root = _paths(declaration['bound_root'], declaration['post_root'], root)
    policy = WindowReconciliationPolicy(**declaration['policy'])
    if (declaration['schema_version'] != VERSION or declaration['limits'] != LIMITS
            or declaration['build'] != verified_panel_build()):
        raise ValueError('reconciliation build/policy differs')
    saved, ia = _pair(root, 'window_reconciliation_input')
    report, ra = _pair(root, 'window_reconciliation_report')
    inputs, material = _load(*roots[:2])
    if (canonical_json(inputs) != canonical_json(saved['inputs'])
            or saved['policy_hash'] != pa['payload_hash']
            or not _ordered_clocks(declaration['declared_at'], pa['durable_ack'],
                saved['read_started_at'], saved['read_completed_at'], ia['durable_ack'],
                report['computation_started_at'], report['computed_at'], ra['durable_ack'])
            or any(not _ordered_clocks(available, saved['read_started_at']) for available in
                (inputs['bound_window']['bound_window_available_at'],
                 inputs['post_computation']['computation_available_at']))):
        raise ValueError('reconciliation input/chronology differs')
    result = _project(inputs, material, policy, report['computation_started_at'])
    expected = {'policy_hash': pa['payload_hash'], 'input_hash': ia['payload_hash'],
                'computation_started_at': report['computation_started_at'],
                'computed_at': report['computed_at'], **result}
    if canonical_json(expected) != canonical_json(report):
        raise ValueError('reconciliation exact replay differs')
    if declaration['build'] != verified_panel_build():
        raise ValueError('reconciliation build changed during replay')
    _check(root, started)
    return {**report, 'window_reconciliation_report_hash': ra['payload_hash'],
            'window_reconciliation_available_at': ra['durable_ack']}
