"""Exact receipt-time diagnostics with no fabricated native continuity."""

import copy
import json
from datetime import UTC, datetime, timedelta
from fractions import Fraction

import pytest

from astrolabe.feature_store.capture import _digest
from astrolabe.research_panel.window_coverage import WindowCoveragePolicy, project_window_coverage

CONDITION = '0x' + 'a' * 64


def clock(ms):
    return {'utc': (datetime(2026, 9, 24, tzinfo=UTC) + timedelta(milliseconds=ms)).isoformat(),
            'monotonic_ns': str(1000000000 + ms * 1000000), 'clock_session_id': 'fixture'}


def book(bid='2', ask='1', **kwargs):
    return {'event_type': 'book', 'asset_id': '1', 'market': CONDITION,
            'bids': [{'price': '0.40', 'size': bid}],
            'asks': [{'price': '0.60', 'size': ask}], 'timestamp': 'native-unadmitted', **kwargs}


def delta(size='1', **kwargs):
    return {'event_type': 'price_change', 'market': CONDITION,
            'price_changes': [{'asset_id': '1', 'price': '0.40', 'size': size, 'side': 'BUY',
                               **kwargs}]}


def project(messages, *, hold=1000, terminal=1000, duration=1000):
    events = []
    for i, (ms, value) in enumerate(messages, 1):
        raw = (value if isinstance(value, bytes) else value.encode() if isinstance(value, str)
               else json.dumps(value).encode())
        events.append({'event': {'ordinal': i, 'kind': 'received', 'observed_at': clock(ms),
                       'raw_hash': _digest(raw), 'wire_type': 'binary' if isinstance(value, bytes)
                       else 'text', 'truncated': False},
                       'raw': raw, 'ack': {'payload_hash': str(i) * 64,
                                           'durable_ack': clock(ms)}})
    return project_window_coverage(
        {'token_id': '1', 'condition_id': CONDITION, 'duration_ms': duration},
        {'subscription_sent_at': clock(0), 'ended_at': clock(terminal),
         'window_report_hash': 'a' * 64, 'provenance_class': 'synthetic'}, events,
        policy=WindowCoveragePolicy(hold))


def ratio(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def test_exact_time_weighting_differs_from_update_count_and_retains_gaps():
    result = project([(100, book()), (400, delta()), (500, 'PONG'),
                      (700, 'bad json'), (800, book('1', '2'))])
    assert result['reconstructed_receipt_duration_ns'] == '800000000'
    assert result['uncovered_duration_ns'] == '200000000'
    assert ratio(result['imbalance_ns_integral']) == Fraction(100000000, 3)
    assert ratio(result['covered_mean_imbalance']) == Fraction(1, 24)
    assert ratio(result['end_imbalance']) == Fraction(-1, 3)
    assert ratio(result['covered_persistence_ratio']) == Fraction(-1, 8)
    first = result['items'][0]['snapshot']
    assert ratio(first['F08_snapshot']) == Fraction(1, 3)
    assert ratio(first['F09_snapshot']) == Fraction(1, 30)
    assert first['F08_snapshot']['decimal'] is None
    assert sum(int(s['duration_ns']) for s in result['segments']) == 1000000000
    assert result['gaps'][0]['reason'] == 'invalid_json'
    assert all(v['value'] is None for v in result['registered_features'].values())
    assert not result['complete_continuous_history'] and not result['origin_admitted']


def test_array_order_has_no_invented_duration_and_zero_is_not_missing():
    result = project([(100, [book(), delta()])])
    assert [v['element_index'] for v in result['items']] == [0, 1]
    assert ratio(result['covered_mean_imbalance']) == 0
    assert ratio(result['end_imbalance']) == 0
    assert result['covered_persistence_ratio'] is None
    assert result['persistence_missing_reason'] == 'zero_denominator'
    assert result['frames'][0]['item_count'] == 2


def test_heartbeat_trade_and_tick_cannot_refresh_book_receipt_age():
    trade = {'event_type': 'last_trade_price', 'market': CONDITION, 'asset_id': '1',
             'price': '0.9', 'size': '2.00', 'side': 'SELL', 'transaction_hash': 'not-a-fill-id'}
    tick = {'event_type': 'tick_size_change', 'market': CONDITION, 'asset_id': '1',
            'old_tick_size': '0.01', 'new_tick_size': '0.001'}
    result = project([(100, book()), (250, 'PONG'), (400, trade), (500, tick)], hold=200)
    assert result['reconstructed_receipt_duration_ns'] == '200000000'
    assert result['uncovered_duration_ns'] == '800000000'
    assert result['end_imbalance'] is None
    assert result['items'][1]['economic_fill_id'] is None
    assert result['items'][2]['new_tick_size']['decimal'] == '0.001'
    assert result['items'][0]['native_timestamp_raw'] == 'native-unadmitted'
    assert result['native_book_age'] is None and not result['native_clock_admitted']


@pytest.mark.parametrize('bad', ['{bad', b'{"event_type":"book"}', [], {'event_type': 'unknown'},
                               {'event_type': 'unknown', 'asset_id': '1', 'market': CONDITION}])
def test_invalid_frame_requires_fresh_snapshot_and_does_not_erase_prior_gap(bad):
    result = project([(100, book()), (200, bad), (250, delta('8')), (400, book())])
    assert result['reconstructed_receipt_duration_ns'] == '700000000'
    assert result['gaps'] and result['items'][-1]['state'] == 'snapshot'
    assert result['items'][-2]['state'] == 'invalid_or_conflicting_message'


def test_unrelated_messages_do_not_invalidate_selected_state():
    result = project([(100, book()), (200, book(asset_id='2')), (300, {
        'event_type': 'unknown', 'market': 'other', 'asset_id': '3'})])
    assert [i['state'] for i in result['items']] == ['snapshot', 'unrelated', 'unrelated']
    assert not result['gaps'] and result['reconstructed_receipt_duration_ns'] == '900000000'


@pytest.mark.parametrize('change', ['condition', 'crossed', 'duplicate', 'one_sided',
                                   'extreme_number', 'best_mismatch', 'missing_assertion'])
def test_bad_book_or_identity_and_false_best_assertions_invalidate(change):
    invalid = book()
    if change == 'condition':
        invalid['market'] = '0x' + 'b' * 64
    elif change == 'crossed':
        invalid['bids'][0]['price'] = '0.9'
    elif change == 'duplicate':
        invalid['bids'] *= 2
    elif change == 'one_sided':
        invalid['asks'] = []
    elif change == 'extreme_number':
        invalid['bids'][0]['size'] = '1e999999999'
    elif change == 'best_mismatch':
        invalid = delta(best_bid='0.1')
    else:
        invalid = {'event_type': 'best_bid_ask', 'asset_id': '1', 'market': CONDITION}
    result = project([(100, book()), (200, invalid)])
    assert result['items'][-1]['state'] == 'invalid_or_conflicting_message'
    assert result['reconstructed_receipt_duration_ns'] == '100000000'
    assert result['end_imbalance'] is None


def test_zero_depth_removal_is_not_cancellation_evidence():
    result = project([(100, book()), (200, delta('0'))])
    assert result['items'][-1]['state'] == 'invalid_or_conflicting_message'
    assert result['registered_features']['F10']['value'] is None


def test_identical_snapshots_keep_separate_receipts_without_new_numerical_change():
    result = project([(100, book()), (200, book('2.000', '1.0'))])
    assert result['items'][0]['numerical_change']
    assert not result['items'][1]['numerical_change']
    assert len(result['frames']) == 2


def test_early_stop_and_late_frame_do_not_fill_unobserved_tail():
    result = project([(100, book())], terminal=300)
    assert result['reconstructed_receipt_duration_ns'] == '200000000'
    assert result['segments'][-1]['state'] == 'capture_ended'
    assert result['end_imbalance'] is None
    late = project([(100, book()), (1000, book('99')), (1001, 'bad')], terminal=1100)
    assert [v['state'] for v in late['frames']][-2:] == ['outside_interval', 'outside_interval']
    assert ratio(late['end_imbalance']) == Fraction(1, 3)


def test_oversized_array_is_not_truncated_and_raw_reference_remains():
    result = project([(100, book()), (200, [book()] * 101)])
    assert result['frames'][1]['state'] == 'message_budget_or_empty_frame'
    assert result['frames'][1]['item_count'] == 0
    assert result['reconstructed_receipt_duration_ns'] == '100000000'


def test_empty_window_is_unavailable_not_observed_zero():
    result = project([])
    assert result['reconstructed_receipt_duration_ns'] == '0'
    assert result['covered_mean_imbalance'] is None and result['end_imbalance'] is None


def test_policy_and_result_dictionary_are_not_aliases():
    result = project([(100, book())])
    expected = copy.deepcopy(result)
    result['limits']['max_items'] = 1
    assert project([(100, book())]) == expected
    for hold in (0, True, 60001):
        with pytest.raises(ValueError):
            WindowCoveragePolicy(hold)


@pytest.mark.parametrize('messages,terminal', [([(400, book()), (200, delta())], 1000),
                                             ([(400, book())], 300)])
def test_regressed_or_post_terminal_source_receipts_are_rejected(messages, terminal):
    with pytest.raises(ValueError, match='clocks/order'):
        project(messages, terminal=terminal)


def test_integer_token_best_assertions_are_not_silently_skipped():
    change = delta(best_bid='0.1')
    change['price_changes'][0]['asset_id'] = 1
    result = project([(100, book()), (200, change)])
    assert result['items'][-1]['state'] == 'invalid_or_conflicting_message'
