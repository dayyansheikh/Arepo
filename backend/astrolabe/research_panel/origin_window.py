"""Verified pre-origin window inputs; receipt diagnostics never imply venue continuity."""

from dataclasses import asdict, dataclass
from datetime import timedelta
from fractions import Fraction

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _time

from .book_primitives import _number, _ratio
from .input_read import _canonical
from .quote_inputs import _at
from .socket_analysis import read_socket_analysis

VERSION = 'fs2-origin-window-input-v1'
MAX_BYTES = 16384
COVERAGE_FIELDS = (
    'declared_duration_ns', 'reconstructed_receipt_duration_ns', 'uncovered_duration_ns',
    'imbalance_ns_integral', 'covered_mean_imbalance', 'end_imbalance',
    'covered_persistence_ratio', 'persistence_missing_reason', 'policy',
)


@dataclass(frozen=True)
class OriginWindowPolicy:
    max_history_age_ms: int
    max_window_age_ms: int
    version: str = VERSION

    def __post_init__(self):
        if (self.version != VERSION or any(type(v) is not int or not 0 <= v <= 300000
                for v in (self.max_history_age_ms, self.max_window_age_ms))):
            raise ValueError('explicit bounded origin window freshness required')


def _same_identity(prior, current):
    left, right = prior['mapping'], current['mapping']
    return (left is not None and right is not None
            and all(prior[k] == current[k] for k in ('token_id', 'condition_id'))
            and all(left[k] == right[k] for k in
                    ('market_id', 'mapping_version', 'outcome_index', 'outcome_label')))


def project_origin_window(analysis_root, current_quote, *, provenance, cutoff, policy):
    """Read full immutable dependencies. The origin writer must own the actual cutoff clock.

    This helper creates no prospective record or admission by itself. Pure caller values are
    not source authentication; current_quote must come from the writer's verified projection.
    """
    if type(policy) is not OriginWindowPolicy or provenance not in {'synthetic', 'prospective'}:
        raise ValueError('explicit origin window policy/provenance required')
    root = _canonical(analysis_root)
    summary = read_socket_analysis(root)
    declaration, _ = _pair(root, 'socket_analysis_policy')
    facts, fa = _pair(root, 'socket_analysis_facts')
    saved, _ = _pair(root, 'socket_analysis_input')
    if declaration['post_root'] is not None:
        raise ValueError('origin window must not consume a post-window endpoint analysis')
    if (summary['computation_hash'] != fa['payload_hash']
            or not _ordered_clocks(summary['computation_available_at'], cutoff)
            or summary['source_provenance_class'] != provenance):
        raise ValueError('origin window changed, future or incompatible provenance')
    socket = saved['inputs']['socket']
    socket_policy = saved['inputs']['socket_policy']
    pre_root = _canonical(socket_policy['pre_computation_root'])
    pre_facts, pre_ack = _pair(pre_root, 'book_facts')
    if pre_ack['payload_hash'] != saved['inputs']['pre_computation']['computation_hash']:
        raise ValueError('pre-window book changed after verified read')
    (snapshot,) = pre_facts['projection']['snapshots']
    prior = snapshot['quote']
    coverage = facts['projection']['coverage']
    if (socket['provenance_class'] != provenance
            or saved['inputs']['pre_computation']['source_provenance_class'] != provenance
            or facts['projection']['continuous_sequence_proven'] is not False
            or facts['projection']['native_clock_admitted'] is not False):
        raise ValueError('window provenance or native continuity differs')
    current_mapping = current_quote['mapping']
    for value in (current_quote.get('source_available_at'),
                  current_quote.get('received_at'),
                  current_mapping.get('available_at') if current_mapping else None):
        if value is not None and _at(value) > _time(cutoff):
            raise ValueError('current quote unavailable at origin window cutoff')
    reasons = []
    if prior['state'] != 'observed' or current_quote['state'] != 'observed':
        reasons.append('snapshot_unavailable')
    if not _same_identity(prior, current_quote):
        reasons.append('identity_changed_or_unavailable')
    now = _time(cutoff)
    if not timedelta(0) <= now - _at(prior['received_at']) <= timedelta(
        milliseconds=policy.max_history_age_ms
    ):
        reasons.append('prior_quote_stale')
    if current_quote.get('received_at') is None or (
        _at(current_quote['received_at']) <= _at(prior['received_at'])
        or _at(current_quote['received_at']) < _time(socket['ended_at'])
    ):
        reasons.append('current_quote_not_after_window')
    if not timedelta(0) <= now - _time(socket['ended_at']) <= timedelta(
        milliseconds=policy.max_window_age_ms
    ):
        reasons.append('window_stale')
    history = None
    if not reasons:
        delta = _at(current_quote['received_at']) - _at(prior['received_at'])
        elapsed_us = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        before, after = _number(prior['midpoint']), _number(current_quote['midpoint'])
        history = {
            'prior_observation_id': prior['observation_id'],
            'current_observation_id': current_quote['observation_id'],
            'prior_received_at': prior['received_at'],
            'current_received_at': current_quote['received_at'],
            'prior_midpoint': _ratio(before), 'current_midpoint': _ratio(after),
            'midpoint_change': _ratio(after - before),
            'receipt_separation_ms': _ratio(Fraction(elapsed_us, 1000)),
            'price_units': 'source_local_price_per_share', 'time_basis': 'receipt',
            'regular_cadence': False, 'locked_baseline': False,
        }
    result = {
        'schema_version': VERSION, 'policy': asdict(policy), 'cutoff': cutoff,
        'analysis_root': str(root), 'analysis': summary,
        'socket_report_hash': socket['socket_window_report_hash'],
        'socket_last_event_hash': socket['last_event_hash'],
        'pre_computation': saved['inputs']['pre_computation'],
        'prior_mapping_version': prior['mapping']['mapping_version'],
        'current_mapping_version': current_mapping['mapping_version'] if current_mapping else None,
        'subscription_sent_at': socket['subscription_sent_at'],
        'window_ended_at': socket['ended_at'],
        'history_state': 'observed' if history is not None else 'unavailable',
        'history_reasons': reasons, 'history': history,
        'window_state': 'receipt_diagnostics' if coverage is not None else 'unavailable',
        'coverage': {k: coverage[k] for k in COVERAGE_FIELDS} if coverage is not None else None,
        'coverage_identity_matches_current': _same_identity(prior, current_quote),
        'socket_terminal': socket['terminal'], 'socket_close_state': socket['close_state'],
        'provenance_class': provenance, 'continuous_window_eligible': False,
        'native_clock_admitted': False, 'registered_window_features_available': False,
        'origin_admitted': False, 'feature_store_admitted': False,
    }
    if len(_json_bytes(result)) > MAX_BYTES:
        raise ValueError('bounded origin window manifest exceeded')
    return result
