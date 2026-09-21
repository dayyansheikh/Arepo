"""Synthetic Gamma enumeration and fault injection, never prospective evidence."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store import capture
from astrolabe.feature_store.capture import Budget, CaptureJournal, _strict_json
from astrolabe.feature_store.sources import SOURCES
from astrolabe.research_panel import _PACKAGE_FILES, frame
from astrolabe.research_panel.build_identity import verified_panel_build
from astrolabe.research_panel.frame import GammaFrameRun, parse_page, read_frame
from tests.unit.test_feature_store_capture import Stream


def market(index=1, **kwargs):
    return {'id': str(index), 'conditionId': '0x' + f'{index:064x}',
            'clobTokenIds': json.dumps([str(index * 2), str(index * 2 + 1)]),
            'outcomes': '["Yes","No"]', 'active': True, 'closed': False, **kwargs}


def body(rows, cursor=None):
    value = {'markets': rows}
    if cursor is not None:
        value['next_cursor'] = cursor
    return json.dumps(value).encode()


def run(tmp_path, pages, *, limit=2, budget=None):
    requests = []
    root = tmp_path.resolve() / 'fs2_capture_frame'

    def handler(request):
        assert (root / 'frame_policy_ack.json').exists()
        requests.append(dict(request.url.params))
        item = pages[len(requests) - 1]
        if isinstance(item, httpx.Response):
            return item
        return httpx.Response(200, stream=Stream([item]))

    result = GammaFrameRun(root, limit=limit, transport=httpx.MockTransport(handler),
                           budget=budget or Budget(requests=len(pages)))
    return result, requests


async def test_scope_cursor_terminal_identity_and_causal_manifest(tmp_path):
    item, requests = run(tmp_path, [body([market(1), market(2)], 'opaque'), body([market(3)])])
    report = await item.collect()
    assert requests == [{'closed': 'false', 'limit': '2'},
                        {'closed': 'false', 'limit': '2', 'after_cursor': 'opaque'}]
    assert report['state'] == 'exhausted_consistent'
    assert report['enumeration_terminal_observed']
    assert not report['population_inference_eligible']
    assert report['provenance_class'] == 'synthetic'
    assert report['source_rows'] == report['unique_market_ids'] == 3
    assert report['interval_start']['utc'] <= report['interval_end']['utc']
    assert report['interval_end']['utc'] <= report['frame_available_at']['utc']
    assert report['pages'][0]['result']['rows'][0]['selected_token_id'] == '2'
    before = {p: p.read_bytes() for p in item.journal.root.rglob('*') if p.is_file()}
    assert read_frame(item.journal.root) == report
    assert await item.collect() == report
    assert len(requests) == 2
    assert before == {p: p.read_bytes() for p in item.journal.root.rglob('*') if p.is_file()}


async def test_first_page_is_not_population_and_all_numerical_bytes_survive(tmp_path):
    raw = body([market(1, liquidity='0.123456789012345678901000'), market(2)], 'next')
    raw = raw.replace(b'"active": true',
                      b'"liquidityNum": 0.123456789012345678901000, "active": true')
    item, _ = run(tmp_path, [raw])
    report = await item.collect()
    assert report['state'] == 'incomplete'
    assert report['stop_reason'] == 'request_budget'
    assert not report['enumeration_terminal_observed']
    folder = item.journal.root / report['pages'][0]['capture_id']
    assert (folder / 'raw.bin').read_bytes() == raw
    parsed = json.loads((folder / 'parsed.json').read_bytes())['value']
    assert parsed['markets'][0]['liquidityNum'] == {'$decimal': '0.123456789012345678901000'}
    assert str(_strict_json(raw)['markets'][0]['liquidityNum']) == '0.123456789012345678901000'


@pytest.mark.parametrize('raw', [
    b'{"markets":[],"next_cursor":"a"}', b'{"markets":[],"next_cursor":null}',
    b'{"markets":[],"next_cursor":""}', b'{"markets":[],"markets":[]}',
    b'[]', b'{"markets":null}', body([market(), market(2)]),
    body([market()], 'short'), body([market(), market(2), market(3)], 'long'),
])
async def test_contradictory_or_invalid_page_never_complete(tmp_path, raw):
    item, _ = run(tmp_path, [raw])
    report = await item.collect()
    assert report['state'] == 'incomplete'
    assert report['errors']
    assert report['stop_reason'] == 'page_error'


async def test_empty_terminal_and_exact_multiple_need_explicit_last_page(tmp_path):
    item, _ = run(tmp_path, [body([market(), market(2)], 'a'), body([])])
    report = await item.collect()
    assert report['state'] == 'exhausted_consistent'
    assert report['verified_attempts'] == 2


async def test_nonconsecutive_cursor_cycle_stops_and_preserves_all_pages(tmp_path):
    item, requests = run(tmp_path, [body([market(), market(2)], cursor)
                                    for cursor in ('a', 'b', 'a')])
    report = await item.collect()
    assert len(requests) == 3
    assert report['state'] == 'incomplete'
    assert report['stop_reason'] == 'cursor_cycle'
    assert report['errors'] == ['cursor_cycle']
    assert report['source_rows'] == 6


async def test_identical_and_changed_repeated_rows_remain_and_conflict_is_not_deduped(tmp_path):
    item, _ = run(tmp_path, [body([market(), market()], 'a'), body([market(liquidity='5')])])
    report = await item.collect()
    assert report['source_rows'] == 3
    assert report['unique_market_ids'] == 1
    assert report['duplicate_market_rows'] == 2
    assert report['conflicting_market_ids'] == ['1']
    assert report['state'] == 'exhausted_inconsistent'


async def test_missing_id_and_mapping_statuses_retained_without_unknown_strata_exclusion(tmp_path):
    missing_id = market()
    del missing_id['id']
    item, _ = run(tmp_path, [body([missing_id, market(2, active=False)], 'a'),
                            body([market(3, clobTokenIds=None), market(4)], 'b'), body([])])
    report = await item.collect()
    assert report['state'] == 'exhausted_inconsistent'
    assert report['exclusion_counts'] == {'market_id_unavailable': 1, 'identity_unresolved': 2,
                                          'inactive': 1}
    assert report['eligible_row_count'] == 1  # absent category/liquidity is not exclusion
    assert report['source_rows'] == 4


async def test_conflicting_token_or_condition_mapping_is_inconsistent(tmp_path):
    item, _ = run(tmp_path, [body([market(), market(2, clobTokenIds='["2","3"]')], 'a'),
                            body([market(3, conditionId=market()['conditionId'])])])
    report = await item.collect()
    assert report['state'] == 'exhausted_inconsistent'
    assert report['conflicting_token_ids'] == ['2', '3']
    assert report['conflicting_condition_ids'] == [market()['conditionId']]


async def test_http_and_partial_body_errors_preserved(tmp_path):
    item, _ = run(tmp_path, [httpx.Response(429, stream=Stream([b'not available']))])
    report = await item.collect()
    assert report['state'] == 'incomplete'
    assert report['pages'][0]['http_status'] == 429
    assert report['errors'] == ['http_non_success']


async def test_byte_budget_retains_truncated_body_and_incomplete_result(tmp_path):
    item, _ = run(tmp_path, [body([market()])], budget=Budget(requests=1, total_bytes=12))
    report = await item.collect()
    assert report['raw_bytes'] == 12
    assert report['errors'] == ['byte_budget_exceeded']
    assert report['state'] == 'incomplete'


async def test_parent_cursor_and_scope_rejected_before_network(tmp_path):
    raw = body([market(), market(2)], 'next')
    store = CaptureJournal(tmp_path.resolve() / 'fs2_capture_cursor',
                           transport=httpx.MockTransport(lambda r: httpx.Response(
                               200, stream=Stream([raw]))))
    params = {'closed': 'false', 'limit': 2}
    for bad in ({**params, 'active': 'true'}, {**params, 'offset': 2}, {**params, 'limit': 101},
                {**params, 'closed': 'true'}, {**params, 'after_cursor': ''}):
        with pytest.raises(ValueError):
            SOURCES[frame.SOURCE].params(bad)
    with pytest.raises(ValueError, match='captured prior'):
        await store.fetch(frame.SOURCE, {**params, 'after_cursor': 'next'})
    assert store.count == 0
    first = await store.fetch(frame.SOURCE, params)
    parent = first['receipt']['capture_id']
    for bad in ({**params, 'after_cursor': 'wrong'},
                {**params, 'limit': 3, 'after_cursor': 'next'}):
        with pytest.raises(ValueError, match='scope|progress'):
            await store.fetch(frame.SOURCE, bad, previous_capture_id=parent)
    assert store.count == 1


async def test_crash_before_page_ack_retained_and_read_does_not_reconstruct(tmp_path, monkeypatch):
    item, _ = run(tmp_path, [body([market()])])
    original_open = Path.open

    def open_with_failure(path, *args, **kwargs):
        if path.name == 'frame_page_ack.json':
            raise OSError('synthetic crash before page seal')
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', open_with_failure)
    with pytest.raises(OSError):
        await item.collect()
    monkeypatch.undo()
    report = read_frame(item.journal.root)
    assert report['state'] == 'incomplete'
    assert report['stop_reason'] == 'interrupted'
    assert report['unverified_attempts'] == 1
    before = {p: p.read_bytes() for p in item.journal.root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='interrupted'):
        await item.collect()
    assert before == {p: p.read_bytes() for p in item.journal.root.rglob('*') if p.is_file()}


async def test_clock_regression_never_complete(tmp_path, monkeypatch):
    item, _ = run(tmp_path, [body([market()])])
    original = capture._clock
    count = 0

    def broken_clock():
        nonlocal count
        result = original()
        count += 1
        if count == 3:
            result['utc'] = '2000-01-01T00:00:00.000000Z'
        return result

    # A loaded-code change must be rejected before the first request.
    monkeypatch.setattr(capture, '_clock', broken_clock)
    with pytest.raises(ValueError, match='loaded measurement code'):
        await item.collect()
    assert item.journal.count == 0
    monkeypatch.undo()
    # Independently corrupt an actual synthetic receipt after capture to test recovery checks.
    await item.collect()
    folder = next(p for p in item.journal.root.iterdir() if p.is_dir())
    receipt_file = folder / 'receipt.json'
    receipt = json.loads(receipt_file.read_bytes())
    receipt['first_received']['utc'] = '2000-01-01T00:00:00.000000Z'
    receipt_file.write_bytes(capture._json_bytes(receipt))
    ack_file = folder / 'raw_ack.json'
    ack = json.loads(ack_file.read_bytes())
    ack['receipt_hash'] = capture._digest(receipt_file.read_bytes())
    ack_file.write_bytes(capture._json_bytes(ack))
    with pytest.raises(ValueError, match='manifest differs'):
        read_frame(item.journal.root)


def test_changed_panel_build_or_parser_refused(tmp_path, monkeypatch):
    verified_panel_build()
    monkeypatch.setitem(_PACKAGE_FILES, 'frame.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        GammaFrameRun(tmp_path.resolve() / 'fs2_capture_changed')
    monkeypatch.undo()
    monkeypatch.setattr(frame, 'parse_page', lambda *args: {})
    with pytest.raises(ValueError, match='loaded panel code'):
        verified_panel_build()
    assert not (tmp_path / 'fs2_capture_changed').exists()


async def test_concurrent_collect_calls_do_not_duplicate_requests(tmp_path):
    item, requests = run(tmp_path, [body([market()])])
    a, b = await asyncio.gather(item.collect(), item.collect())
    assert a == b
    assert len(requests) == 1


def test_parser_refuses_boolean_limit_at_public_boundary():
    with pytest.raises(ValueError):
        SOURCES[frame.SOURCE].params({'closed': 'false', 'limit': True})
    assert parse_page(body([market(active=None)]), 2)['rows'][0]['exclusion_reasons'] == [
        'active_state_unavailable']


async def test_partial_http_read_preserves_unusable_bytes(tmp_path):
    response = httpx.Response(200, stream=Stream([b'{"markets":[', httpx.ReadError('private')]))
    item, _ = run(tmp_path, [response])
    report = await item.collect()
    assert report['raw_bytes'] == len(b'{"markets":[')
    assert report['errors'] == ['ReadError']
    assert report['state'] == 'incomplete'
    assert 'private' not in json.dumps(report)


async def test_torn_report_is_not_filled_on_retry(tmp_path, monkeypatch):
    item, requests = run(tmp_path, [body([market()])])
    original = Path.open

    def fail(path, *args, **kwargs):
        if path.name == 'frame_report_ack.json':
            raise OSError('crash after report payload')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        await item.collect()
    monkeypatch.undo()
    report = read_frame(item.journal.root)
    assert report['state'] == 'incomplete'
    assert report['frame_available_at'] is None
    assert report['enumeration_terminal_observed']
    with pytest.raises(ValueError, match='interrupted'):
        await item.collect()
    assert len(requests) == 1


async def test_restored_journal_remains_same_original_evidence(tmp_path):
    import shutil

    item, _ = run(tmp_path, [body([market()])])
    report = await item.collect()
    copy = tmp_path.resolve() / 'fs2_capture_restored'
    shutil.copytree(item.journal.root, copy)
    assert read_frame(copy) == report


async def test_expired_request_budget_sends_nothing_and_retains_missing_frame(tmp_path):
    item, requests = run(tmp_path, [body([market()])])
    item.journal.started -= 200  # synthetic elapsed-time fixture, never source-clock evidence
    report = await item.collect()
    assert not requests
    assert report['state'] == 'incomplete'
    assert report['stop_reason'] == 'time_budget'
    assert report['source_rows'] == 0
