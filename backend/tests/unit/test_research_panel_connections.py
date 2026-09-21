"""Real loopback HTTP and synthetic faults; never live source/population evidence."""

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import pytest

from astrolabe.feature_store import capture
from astrolabe.feature_store.capture import (
    REUSED_HTTP_POLICY,
    Budget,
    CaptureJournal,
    _digest,
    _json_bytes,
    connection_policy,
    verify_capture,
)
from astrolabe.research_panel.frame import FrameRetryPolicy, GammaFrameRun, read_frame
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_frame import body, market
from tests.unit.test_research_panel_retries import PartialTimeout


class TrackedTransport(httpx.MockTransport):
    def __init__(self, handler):
        super().__init__(handler)
        self.closed = 0

    async def aclose(self):
        self.closed += 1
        await super().aclose()


@asynccontextmanager
async def loopback(*, close_after_response=False):
    connections, requests, tasks = [], [], set()

    async def handle(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        connections.append(writer.get_extra_info('peername'))
        try:
            while True:
                try:
                    request = await reader.readuntil(b'\r\n\r\n')
                except asyncio.IncompleteReadError:
                    break
                requests.append(request)
                response = body([market(1), market(2)], 'next') if len(requests) == 1 else body([])
                connection = b'close' if close_after_response else b'keep-alive'
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n'
                             b'Set-Cookie: unwanted=state\r\nConnection: ' + connection
                             + b'\r\nContent-Length: ' + str(len(response)).encode()
                             + b'\r\n\r\n' + response)
                await writer.drain()
                if close_after_response:
                    break
        finally:
            writer.close()
            await writer.wait_closed()
            tasks.discard(task)

    server = await asyncio.start_server(handle, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]

    class LocalTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.inner = httpx.AsyncHTTPTransport(
                retries=0, limits=httpx.Limits(max_connections=1, max_keepalive_connections=1))
            self.closed = 0

        async def handle_async_request(self, request):
            # Any injected transport is synthetic, even when it exercises real local sockets.
            url = request.url.copy_with(scheme='http', host='127.0.0.1', port=port)
            return await self.inner.handle_async_request(httpx.Request(
                request.method, url, headers=request.headers, extensions=request.extensions))

        async def aclose(self):
            self.closed += 1
            await self.inner.aclose()

    transport = LocalTransport()
    try:
        yield transport, connections, requests
    finally:
        await transport.inner.aclose()
        server.close()
        await server.wait_closed()
        if tasks:
            await asyncio.wait_for(asyncio.gather(*list(tasks)), 2)


@pytest.mark.parametrize('reuse,server_close,expected_connections', [
    (False, False, 2), (True, False, 1), (True, True, 2),
])
async def test_real_http_reuse_close_reconnect_and_stateless_cursors(
        tmp_path, reuse, server_close, expected_connections):
    async with loopback(close_after_response=server_close) as (transport, sockets, requests):
        run = GammaFrameRun(tmp_path.resolve() / 'fs2_capture_local', limit=2,
                            budget=Budget(requests=2), transport=transport,
                            reuse_connections=reuse)
        report = await run.collect()
        assert len(requests) == 2 and len(sockets) == expected_connections
        assert b'after_cursor=next' in requests[1]
        assert all(b'\r\ncookie:' not in r.lower() for r in requests)
        assert transport.closed == (1 if reuse else 2)
        assert run.journal._client is None
        assert report['provenance_class'] == 'synthetic'
        assert report['state'] == 'exhausted_consistent'
        assert not report['population_inference_eligible']
        policy = json.loads((run.journal.root / 'frame_policy.json').read_bytes())
        assert policy['http_connection_policy'] == (REUSED_HTTP_POLICY if reuse else None)
        assert read_frame(run.journal.root) == report


async def test_partial_retry_keeps_bytes_clocks_and_one_client(tmp_path):
    calls = []

    def handle(request):
        calls.append(dict(request.url.params))
        stream = PartialTimeout() if len(calls) == 1 else Stream([body([])])
        return httpx.Response(200, stream=stream)

    transport = TrackedTransport(handle)
    run = GammaFrameRun(tmp_path.resolve() / 'fs2_capture_partial', transport=transport,
                        budget=Budget(requests=2), retry_policy=FrameRetryPolicy(),
                        reuse_connections=True)
    report = await run.collect()
    assert calls[0] == calls[1] and transport.closed == 1
    assert report['errors'] == ['ReadTimeout'] and not report['unrecovered_errors']
    assert report['recovered_failed_attempts'] == 1
    failed, good = report['pages']
    assert good['retry_of'] == failed['capture_id']
    assert (run.journal.root / failed['capture_id'] / 'raw.bin').read_bytes() == b'{"markets":['
    assert failed['first_received']['utc'] < good['request_started']['utc']


@pytest.mark.parametrize('cancel', [False, True])
async def test_deadline_or_cancel_preserves_partial_and_closes_pool(tmp_path, cancel):
    received = asyncio.Event()

    class WaitingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"markets":['
            received.set()
            await asyncio.Event().wait()

    transport = TrackedTransport(lambda r: httpx.Response(200, stream=WaitingStream()))
    run = GammaFrameRun(tmp_path.resolve() / 'fs2_capture_stop', transport=transport,
                        budget=Budget(requests=1, seconds_per_request=1), reuse_connections=True)
    task = asyncio.create_task(run.collect())
    await received.wait()
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        assert (await task)['state'] == 'incomplete'
    folder = next(p for p in run.journal.root.iterdir() if p.is_dir())
    capture = verify_capture(folder)
    assert capture['raw'] == b'{"markets":['
    assert capture['receipt']['transport_error'] == ('cancelled' if cancel else 'TimeoutError')
    assert transport.closed == 1 and run.journal._client is None


async def test_no_hidden_retry_or_budget_extension(tmp_path):
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ConnectError('private exception detail must not be retained')

    transport = TrackedTransport(handle)
    run = GammaFrameRun(tmp_path.resolve() / 'fs2_capture_error', transport=transport,
                        budget=Budget(requests=2), reuse_connections=True)
    report = await run.collect()
    assert len(calls) == 1 and transport.closed == 1
    assert report['state'] == 'incomplete' and report['retry_attempts'] == 0
    assert report['errors'] == ['ConnectError']
    assert 'private exception detail' not in ''.join(
        p.read_text() for p in run.journal.root.rglob('*.json'))


async def test_scope_required_without_consuming_attempt_and_nested_scope_refused(tmp_path):
    store = CaptureJournal(tmp_path.resolve() / 'fs2_capture_scope', reuse_connections=True,
                           transport=TrackedTransport(lambda r: httpx.Response(
                               200, stream=Stream([b'{}']))))
    with pytest.raises(ValueError, match='active scope'):
        await store.fetch('coinbase.btc_usd.ticker', {})
    assert store.count == 0
    async with store.connection_scope():
        with pytest.raises(ValueError, match='already active'):
            async with store.connection_scope():
                pytest.fail('nested scope admitted')
        await store.fetch('coinbase.btc_usd.ticker', {})
    assert store.transport.closed == 1


async def test_frame_rejects_connection_policy_mismatch(tmp_path):
    run = GammaFrameRun(tmp_path.resolve() / 'fs2_capture_mismatch', reuse_connections=True,
                        transport=TrackedTransport(lambda r: httpx.Response(
                            200, stream=Stream([body([])]))))
    await run.collect()
    path = run.journal.root / 'frame_policy.json'
    policy = json.loads(path.read_bytes())
    policy['http_connection_policy'] = None
    path.write_bytes(_json_bytes(policy))
    ack_path = run.journal.root / 'frame_policy_ack.json'
    ack = json.loads(ack_path.read_bytes())
    ack['payload_hash'] = _digest(path.read_bytes())
    ack_path.write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match='policy/build/source/clock differs'):
        read_frame(run.journal.root)


def test_unknown_transport_policy_and_implicit_boolean_rejected(tmp_path):
    with pytest.raises(ValueError, match='connection policy differs'):
        connection_policy({'schema_version': 'fs2-capture-v2',
                           'http_connection_policy': {
                               **REUSED_HTTP_POLICY, 'transport_retries': 1}})
    with pytest.raises(ValueError, match='explicit boolean'):
        GammaFrameRun(tmp_path.resolve() / 'fs2_capture_bad', reuse_connections=1)
    assert not (tmp_path / 'fs2_capture_bad').exists()


async def test_storage_failure_retains_unacknowledged_bytes_and_closes_client(
        tmp_path, monkeypatch):
    transport = TrackedTransport(lambda r: httpx.Response(200, stream=Stream([body([])])))
    run = GammaFrameRun(tmp_path.resolve() / 'fs2_capture_storage', transport=transport,
                        reuse_connections=True)
    original = capture.os.fsync
    calls = 0

    def fail_raw_sync(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('synthetic disk failure')
        original(fd)

    monkeypatch.setattr(capture.os, 'fsync', fail_raw_sync)
    with pytest.raises(OSError, match='synthetic disk failure'):
        await run.collect()
    folder = next(p for p in run.journal.root.iterdir() if p.is_dir())
    assert (folder / 'raw.bin').read_bytes() == body([])
    assert not (folder / 'raw_ack.json').exists()
    assert transport.closed == 1 and run.journal._client is None
    assert read_frame(run.journal.root)['state'] == 'incomplete'
