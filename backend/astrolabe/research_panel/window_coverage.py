"""Exact received-window diagnostics, never native continuity or feature admission."""

import time
from dataclasses import asdict, dataclass
from fractions import Fraction

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.book_replay import BookReplay
from astrolabe.feature_store.capture import _strict_json
from astrolabe.feature_store.source_run import _ordered_clocks, _time
from astrolabe.feature_store.types import uint_text

from .book_primitives import _number, _ratio

VERSION = 'fs2-receipt-window-coverage-v1'
LIMITS = {'max_array_items': 100, 'max_items': 10000, 'max_levels': 10000,
          'max_processing_seconds': 180}


@dataclass(frozen=True)
class WindowCoveragePolicy:
    max_receipt_hold_ms: int
    version: str = 'fs2-window-coverage-policy-v1'

    def __post_init__(self):
        if (type(self.max_receipt_hold_ms) is not int
                or not 1 <= self.max_receipt_hold_ms <= 60000
                or self.version != 'fs2-window-coverage-policy-v1'):
            raise ValueError('explicit finite receipt-hold policy required')


def _scope(message, token, condition):
    if not isinstance(message, dict):
        raise ValueError('message object required')
    kind = message.get('event_type')
    if kind == 'price_change':
        changes = message.get('price_changes')
        if not isinstance(changes, list) or not changes or len(changes) > LIMITS['max_levels']:
            raise ValueError('bounded changes required')
        if any(not isinstance(c, dict) for c in changes):
            raise ValueError('change object required')
        selected = any(uint_text(c.get('asset_id'), bits=256) == token for c in changes)
    elif 'asset_id' in message:
        selected = uint_text(message['asset_id'], bits=256) == token
    elif isinstance(message.get('assets_ids'), list):
        selected = token in [uint_text(v, bits=256) for v in message['assets_ids']]
    else:
        if message.get('market') not in {None, condition}:
            return 'unrelated'
        raise ValueError('selected token scope unresolved')
    if not selected:
        return 'unrelated'
    if message.get('market') != condition:
        raise ValueError('selected token condition conflict')
    return 'selected'


def _bounds(message):
    if message['event_type'] == 'book':
        rows = []
        for side in ('bids', 'asks'):
            if not isinstance(message.get(side), list):
                raise ValueError('book side required')
            rows.extend(message[side])
    else:
        rows = message['price_changes']
    if len(rows) > LIMITS['max_levels']:
        raise ValueError('book numeric budget exceeded')
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('book level required')
        _number(row.get('price'))
        _number(row.get('size'))


def _top(view):
    if (view['requires_snapshot'] or not view['bids'] or not view['asks']
            or len(view['bids']) + len(view['asks']) > LIMITS['max_levels']):
        raise ValueError('valid two-sided bounded state required')
    bid, bs = map(_number, view['bids'][0])
    ask, ass = map(_number, view['asks'][0])
    if bid > ask or bs <= 0 or ass <= 0:
        raise ValueError('noncrossed positive quote required')
    total, difference = bs + ass, bs - ass
    imbalance = difference / total
    numerator = ask * bs + bid * ass
    midpoint = (bid + ask) / 2
    return {'bid': _ratio(bid), 'ask': _ratio(ask), 'bid_size': _ratio(bs),
            'ask_size': _ratio(ass), 'size_difference': _ratio(difference),
            'total_best_size': _ratio(total), 'microprice_numerator': _ratio(numerator),
            'midpoint': _ratio(midpoint), 'F08_snapshot': _ratio(imbalance),
            'F09_snapshot': _ratio(numerator / total - midpoint)}, imbalance


def _assert_best(message, view, token):
    assertions = ([c for c in message['price_changes']
                   if uint_text(c['asset_id'], bits=256) == token][-1:]
                  if message['event_type'] == 'price_change' else [message])
    if message['event_type'] == 'best_bid_ask' and all(
        message.get(field) is None for field in ('best_bid', 'best_ask')
    ):
        raise ValueError('best-price assertion unavailable')
    for value in assertions:
        for field, side in (('best_bid', 'bids'), ('best_ask', 'asks')):
            if value.get(field) is not None:
                if not view[side] or _number(value[field]) != _number(view[side][0][0]):
                    raise ValueError('best-price assertion differs from replay')


class _Projection:
    def __init__(self, source_policy, summary, policy):
        self.source_policy, self.summary, self.policy = source_policy, summary, policy
        self.start = int(summary['subscription_sent_at']['monotonic_ns'])
        self.end = self.start + source_policy['duration_ms'] * 1000000
        self.terminal = min(self.end, int(summary['ended_at']['monotonic_ns']))
        self.cursor = self.start
        self.items, self.frames, self.segments, self.gaps = [], [], [], []
        self.state = self.state_id = self.state_at = self.imbalance = None
        self.reason = 'awaiting_initial_snapshot'
        self.covered = 0
        self.integral = Fraction(0)
        self.item_count = 0
        self.reset()

    def reset(self):
        self.replay = BookReplay(self.source_policy['token_id'], self.source_policy['condition_id'],
                                 message_budget=LIMITS['max_items'])

    def invalidate(self, reason, at, identity):
        self.state = self.imbalance = None
        self.reason = reason
        self.gaps.append({'reason': reason, 'at_monotonic_ns': str(at), 'item_id': identity})
        self.reset()

    def advance(self, at):
        at = max(self.cursor, min(at, self.end))
        expiry = ((self.state_at + self.policy.max_receipt_hold_ms * 1000000)
                  if self.state is not None else self.cursor)
        until = max(self.cursor, min(at, expiry))
        if self.state is not None and until > self.cursor:
            duration = until - self.cursor
            self.segments.append({'start_ns': str(self.cursor), 'end_ns': str(until),
                                  'duration_ns': str(duration), 'state': 'receipt_reconstruction',
                                  'state_item_id': self.state_id,
                                  'imbalance': _ratio(self.imbalance)})
            self.covered += duration
            self.integral += self.imbalance * duration
            self.cursor = until
        if at > self.cursor:
            self.segments.append({'start_ns': str(self.cursor), 'end_ns': str(at),
                                  'duration_ns': str(at - self.cursor),
                                  'state': 'receipt_stale' if self.state else self.reason,
                                  'state_item_id': None, 'imbalance': None})
            self.cursor = at

    def message(self, message, pointer, event, index):
        at = int(event['observed_at']['monotonic_ns'])
        item_id = pointer + ':' + ('object' if index is None else str(index))
        record = {'item_id': item_id, 'element_index': index, 'frame': pointer,
                  'message_hash': content_hash(message), 'state': None, 'numerical_change': False,
                  'native_timestamp_raw': message.get('timestamp') if isinstance(message, dict)
                    else None, 'snapshot': None}
        self.items.append(record)
        token, condition = self.source_policy['token_id'], self.source_policy['condition_id']
        try:
            scope = _scope(message, token, condition)
            if scope == 'unrelated':
                record['state'] = scope
                return
            kind = message.get('event_type')
            record['event_type'] = kind
            if kind in {'book', 'price_change'}:
                _bounds(message)
                before = self.replay.view()
                view = self.replay.apply(message, evidence_id=item_id,
                    session_id=event['observed_at']['clock_session_id'],
                    received_at=_time(event['observed_at']), monotonic_ns=str(at))
                top, imbalance = _top(view)
                _assert_best(message, view, token)
                record.update(state='snapshot' if kind == 'book' else 'delta', snapshot=top,
                    numerical_change=(before['requires_snapshot'] or before['bids'] != view['bids']
                                      or before['asks'] != view['asks']),
                    book_state_hash=content_hash({'bids': view['bids'], 'asks': view['asks']}),
                    previous_state_item_id=self.state_id,
                    bid_levels=len(view['bids']), ask_levels=len(view['asks']))
                self.state, self.imbalance = top, imbalance
                self.state_id, self.state_at = item_id, at
            elif kind == 'best_bid_ask':
                if self.state is None:
                    record['state'] = 'best_quote_without_snapshot'
                else:
                    _assert_best(message, self.replay.view(), token)
                    record['state'] = 'best_quote_consistent'
            elif kind == 'last_trade_price':
                price, size = _number(message.get('price')), _number(message.get('size'))
                if not 0 <= price <= 1 or size < 0 or message.get('side') not in {'BUY', 'SELL'}:
                    raise ValueError('invalid trade')
                record.update(state='trade_unreconciled', price=_ratio(price), size=_ratio(size),
                              side=message['side'], economic_fill_id=None,
                              transaction_hash_raw=message.get('transaction_hash'))
            elif kind == 'tick_size_change':
                tick = _number(message.get('new_tick_size'))
                if not 0 < tick <= 1:
                    raise ValueError('invalid tick')
                record.update(state='tick_metadata', new_tick_size=_ratio(tick),
                              old_tick_size_raw=message.get('old_tick_size'))
            else:
                record['state'] = 'unsupported_relevant_event'
                self.invalidate(record['state'], at, item_id)
        except (ValueError, TypeError):
            record['state'] = 'invalid_or_conflicting_message'
            self.invalidate(record['state'], at, item_id)

    def frame(self, entry):
        event, ack, raw = entry['event'], entry['ack'], entry['raw']
        at = int(event['observed_at']['monotonic_ns'])
        if event['kind'] != 'received':
            return
        pointer = 'event_' + str(event['ordinal']).zfill(6)
        record = {'frame': pointer, 'event_hash': ack['payload_hash'],
                  'raw_hash': event['raw_hash'],
                  'received_at': event['observed_at'], 'source_available_at': ack['durable_ack'],
                  'state': None, 'item_count': 0}
        self.frames.append(record)
        if at >= self.end or at < self.start:
            record['state'] = 'outside_interval'
            return
        self.advance(at)
        if event['truncated']:
            state = 'truncated'
        elif event['wire_type'] != 'text':
            state = 'binary_uninterpreted'
        elif raw == b'PONG':
            record['state'] = 'heartbeat_control'
            return
        else:
            try:
                payload = _strict_json(raw)
                # Reject an unencodable/deep frame before partial application.
                content_hash(payload)
                messages = payload if isinstance(payload, list) else [payload]
                if (not messages or len(messages) > LIMITS['max_array_items']
                        or self.item_count + len(messages) > LIMITS['max_items']):
                    state = 'message_budget_or_empty_frame'
                else:
                    self.item_count += len(messages)
                    record.update(state='decoded', item_count=len(messages))
                    for index, message in enumerate(messages):
                        self.message(message, pointer, event,
                                     index if isinstance(payload, list) else None)
                    return
            except (ValueError, UnicodeError, RecursionError):
                state = 'invalid_json'
        record['state'] = state
        self.invalidate(state, at, pointer)

    def result(self):
        self.advance(self.terminal)
        if self.terminal < self.end:
            self.invalidate('capture_ended', self.terminal, None)
        self.advance(self.end)
        mean = self.integral / self.covered if self.covered else None
        instant = (self.imbalance if self.state is not None and self.end
                   < self.state_at + self.policy.max_receipt_hold_ms * 1000000 else None)
        ratio = mean / instant if mean is not None and instant not in {None, 0} else None
        return {'schema_version': VERSION, 'policy': asdict(self.policy), 'limits': dict(LIMITS),
                'source_policy': self.source_policy,
                'source_report_hash': self.summary['window_report_hash'],
                'frames': self.frames, 'items': self.items, 'segments': self.segments,
                'gaps': self.gaps, 'declared_duration_ns': str(self.end - self.start),
                'reconstructed_receipt_duration_ns': str(self.covered),
                'uncovered_duration_ns': str(self.end - self.start - self.covered),
                'imbalance_ns_integral': _ratio(self.integral),
                'covered_mean_imbalance': _ratio(mean) if mean is not None else None,
                'end_imbalance': _ratio(instant) if instant is not None else None,
                'covered_persistence_ratio': _ratio(ratio) if ratio is not None else None,
                'persistence_missing_reason': ('observed' if ratio is not None else
                    'zero_denominator' if instant == 0 else 'unavailable'),
                'provenance_class': self.summary['provenance_class'],
                'identity_state': 'declared_source_local_not_causally_admitted',
                'native_clock_admitted': False, 'complete_continuous_history': False,
                'registered_features': {key: {'value': None, 'state': 'prerequisites_unproven'}
                                        for key in ('F02', 'F10', 'F27')},
                'origin_admitted': False, 'feature_store_admitted': False,
                'runtime_source_verification_required': True, 'native_book_age': None}


def project_window_coverage(source_policy, summary, events, *, policy):
    """Pure diagnostic helper; only a durable verified consumer authenticates its inputs."""
    if type(policy) is not WindowCoveragePolicy or summary['provenance_class'] != 'synthetic':
        raise ValueError('explicit policy and supported synthetic window required')
    if (type(source_policy['duration_ms']) is not int
            or not 1 <= source_policy['duration_ms'] <= 60000):
        raise ValueError('bounded declared window duration required')
    started = time.monotonic()
    projection = _Projection(source_policy, summary, policy)
    previous = None
    for ordinal, entry in enumerate(events, 1):
        observed = entry['event']['observed_at']
        if (ordinal > 1032 or not _ordered_clocks(observed, entry['ack']['durable_ack'])
                or observed['clock_session_id']
                != summary['subscription_sent_at']['clock_session_id']
                or (previous is not None and not _ordered_clocks(previous, observed))
                or (entry['event']['kind'] == 'received'
                    and not _ordered_clocks(observed, summary['ended_at']))):
            raise ValueError('window input clocks/order/budget differs')
        previous = entry['ack']['durable_ack']
        if time.monotonic() - started > LIMITS['max_processing_seconds']:
            raise ValueError('window projection processing deadline exceeded')
        projection.frame(entry)
    result = projection.result()
    return {**result, 'projection_hash': content_hash(result)}
