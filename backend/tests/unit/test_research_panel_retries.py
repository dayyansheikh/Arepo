"""Frozen retry lineage; failures are retained, never rewritten as successful responses."""

import json

import httpx
import pytest

from astrolabe.feature_store.capture import Budget, _digest, _json_bytes
from astrolabe.research_panel.frame import FrameRetryPolicy, GammaFrameRun, read_frame
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_frame import body, market


class PartialTimeout(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b'{"markets":['
        raise httpx.ReadTimeout('synthetic partial response')


def run(tmp_path, pages, *, retries=FrameRetryPolicy(), requests=None, budget=None):
    seen = []
    root = tmp_path.resolve() / 'fs2_capture_retry'

    def handle(request):
        seen.append(dict(request.url.params))
        item = pages[len(seen) - 1]
        if isinstance(item, httpx.Response):
            return item
        return httpx.Response(200, stream=Stream([item]))

    item = GammaFrameRun(root, limit=2, budget=budget or Budget(requests=requests or len(pages)),
                         retry_policy=retries, transport=httpx.MockTransport(handle))
    return item, seen


def partial():
    return httpx.Response(200, stream=PartialTimeout())


async def test_partial_first_page_retry_preserves_failed_bytes_and_actual_clock(tmp_path):
    item, seen = run(tmp_path, [partial(), body([market()])])
    result = await item.collect()
    assert result['state'] == 'exhausted_consistent'
    assert result['errors'] == ['ReadTimeout'] and not result['unrecovered_errors']
    assert result['retry_attempts'] == result['recovered_failed_attempts'] == 1
    assert result['source_rows'] == 1 and len(result['pages']) == 2
    assert seen[0] == seen[1]
    failed, good = result['pages']
    assert good['retry_of'] == failed['capture_id']
    assert (item.journal.root / failed['capture_id'] / 'raw.bin').read_bytes() == b'{"markets":['
    before = {p: p.read_bytes() for p in item.journal.root.rglob('*') if p.is_file()}
    assert read_frame(item.journal.root) == result == await item.collect()
    assert len(seen) == 2
    assert before == {p: p.read_bytes() for p in item.journal.root.rglob('*') if p.is_file()}
    assert not result['population_inference_eligible']


async def test_retry_reuses_exact_cursor_and_last_successful_parent(tmp_path):
    item, seen = run(tmp_path, [body([market(1), market(2)], 'next'), partial(), body([market(3)])])
    result = await item.collect()
    assert result['source_rows'] == 3 and result['state'] == 'exhausted_consistent'
    assert seen[1] == seen[2] == {'closed': 'false', 'limit': '2', 'after_cursor': 'next'}
    for page in result['pages'][1:]:
        receipt = json.loads((item.journal.root / page['capture_id'] / 'receipt.json').read_bytes())
        assert receipt['previous_capture_id'] == result['pages'][0]['capture_id']


async def test_second_failure_at_same_cursor_exhausts_policy(tmp_path):
    item, seen = run(tmp_path, [partial(), partial(), body([])])
    result = await item.collect()
    assert len(seen) == 2 and result['stop_reason'] == 'retry_exhausted'
    assert result['state'] == 'incomplete' and result['recovered_failed_attempts'] == 0
    assert result['unrecovered_errors'] == ['ReadTimeout']


async def test_global_retry_cap_never_resets_with_next_cursor(tmp_path):
    pages = [partial(), body([market(1), market(2)], 'next'), partial(), body([])]
    item, seen = run(tmp_path, pages, retries=FrameRetryPolicy(total=1))
    result = await item.collect()
    assert len(seen) == 3 and result['retry_attempts'] == 1
    assert result['recovered_failed_attempts'] == 1 and result['state'] == 'incomplete'


async def test_request_budget_includes_failed_attempts(tmp_path):
    item, seen = run(tmp_path, [partial(), body([])], requests=1)
    result = await item.collect()
    assert len(seen) == 1 and result['stop_reason'] == 'request_budget'
    assert result['state'] == 'incomplete' and result['retry_attempts'] == 0


@pytest.mark.parametrize('status', [401, 403, 429, 500])
async def test_nonadmitted_http_failures_are_not_retried(tmp_path, status):
    item, seen = run(tmp_path, [httpx.Response(status, stream=Stream([b'{}'])), body([])])
    result = await item.collect()
    assert len(seen) == 1 and result['state'] == 'incomplete'
    assert result['stop_reason'] == 'page_error'


async def test_declared_temporary_http_error_can_recover(tmp_path):
    item, seen = run(tmp_path, [httpx.Response(503, stream=Stream([b'{}'])), body([])])
    result = await item.collect()
    assert len(seen) == 2 and result['state'] == 'exhausted_consistent'
    assert result['errors'] == ['http_non_success']


async def test_schema_error_and_default_policy_cannot_retry(tmp_path):
    item, seen = run(tmp_path, [b'{"markets":null}', body([])])
    assert (await item.collect())['stop_reason'] == 'page_error'
    assert len(seen) == 1
    other = tmp_path / 'default'
    other.mkdir()
    item, seen = run(other, [partial(), body([])], retries=None)
    assert (await item.collect())['state'] == 'incomplete'
    assert len(seen) == 1


async def test_reader_rejects_erased_retry_lineage(tmp_path):
    item, _ = run(tmp_path, [partial(), body([])])
    report = await item.collect()
    folder = item.journal.root / report['pages'][1]['capture_id']
    page = json.loads((folder / 'frame_page.json').read_bytes())
    page['retry_of'] = None
    (folder / 'frame_page.json').write_bytes(_json_bytes(page))
    ack = json.loads((folder / 'frame_page_ack.json').read_bytes())
    ack['payload_hash'] = _digest((folder / 'frame_page.json').read_bytes())
    (folder / 'frame_page_ack.json').write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match='retry lineage differs'):
        read_frame(item.journal.root)


@pytest.mark.parametrize('kwargs', [{'total': 9}, {'per_cursor': 2}, {'backoff_seconds': 0}])
def test_retry_counts_and_backoff_are_finite(kwargs):
    with pytest.raises(ValueError, match='finite ceilings'):
        FrameRetryPolicy(**kwargs)


@pytest.mark.parametrize('budget,stop', [
    (Budget(requests=2, total_bytes=12), 'byte_budget'),
    (Budget(requests=2, total_seconds=1), 'time_budget'),
])
async def test_retry_does_not_extend_byte_or_time_budget(tmp_path, budget, stop):
    item, seen = run(tmp_path, [partial(), body([])], budget=budget)
    report = await item.collect()
    assert len(seen) == 1 and report['stop_reason'] == stop
    assert report['state'] == 'incomplete' and report['recovered_failed_attempts'] == 0


def test_backoff_requires_wall_and_same_session_monotonic_elapsed_time():
    from astrolabe.research_panel.frame import _retry_delay_met

    before = {'utc': '2026-09-21T12:00:00Z', 'monotonic_ns': '100', 'clock_session_id': 'same'}
    after = {'utc': '2026-09-21T12:00:02Z', 'monotonic_ns': '2000000100',
             'clock_session_id': 'same'}
    assert _retry_delay_met(before, after, 2)
    assert not _retry_delay_met(before, {**after, 'monotonic_ns': '1999999999'}, 2)
    assert not _retry_delay_met(before, {**after, 'utc': '2026-09-21T12:00:01Z'}, 2)
