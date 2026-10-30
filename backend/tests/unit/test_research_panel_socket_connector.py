"""Actual local sockets exercise fixed transport bounds without contacting public services."""

import asyncio
import json

import pytest
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedError, InvalidStatus

from astrolabe.research_panel import socket_connector as module
from astrolabe.research_panel.socket_connector import (
    connector_contract,
    open_loopback_socket,
    open_market_socket,
)


def port(server):
    return server.sockets[0].getsockname()[1]


async def test_loopback_raw_subscription_text_binary_and_ping_pong(monkeypatch):
    received = []
    async def handler(socket):
        received.append(await socket.recv())
        await socket.send('{"event_type":"book","bids":[]}')
        await socket.send(b'\x00raw')
        received.append(await socket.recv())
        await socket.send('PONG')
        await socket.wait_closed()
    # Invalid proxy must never be consulted, even for loopback.
    monkeypatch.setenv('ALL_PROXY', 'http://127.0.0.1:1')
    monkeypatch.setenv('WS_PROXY', 'http://127.0.0.1:1')
    async with serve(handler, '127.0.0.1', 0, compression=None) as server:
        connection = await open_loopback_socket(port(server))
        try:
            assert connection.provenance_class == 'synthetic'
            assert connection.socket.ping_interval is None
            assert not connection.socket.protocol.extensions
            subscription = {'assets_ids': ['1'], 'type': 'market'}
            await connection.socket.send(json.dumps(subscription))
            assert await connection.socket.recv() == '{"event_type":"book","bids":[]}'
            assert await connection.socket.recv() == b'\x00raw'
            await connection.socket.send('PING')
            assert await connection.socket.recv() == 'PONG'
        finally:
            await connection.close()
        assert connection.socket.state.name == 'CLOSED'
    assert json.loads(received[0]) == subscription and received[1] == 'PING'


@pytest.mark.parametrize('status', [301, 302, 307, 308])
async def test_redirect_never_opens_second_connection(status):
    requests = []
    async def reject(connection, request):
        requests.append(request.path)
        response = connection.respond(status, 'redirect test')
        response.headers['Location'] = '/alternate'
        return response
    async def handler(socket):
        raise AssertionError('redirected connection must not reach handler')
    async with serve(handler, '127.0.0.1', 0, process_request=reject) as server:
        with pytest.raises(InvalidStatus):
            await open_loopback_socket(port(server))
    assert requests == ['/ws/market']


async def test_oversized_wire_message_is_rejected_without_invented_raw_prefix():
    async def handler(socket):
        await socket.send(b'x' * (262144 + 1))
        await socket.wait_closed()
    async with serve(handler, '127.0.0.1', 0, compression=None) as server:
        connection = await open_loopback_socket(port(server))
        try:
            with pytest.raises(ConnectionClosedError) as failure:
                await connection.socket.recv()
            assert failure.value.sent.code == 1009
            # recv raised; there is no raw payload/prefix available to a future journal.
        finally:
            await connection.close()


async def test_cancelled_quiet_receive_and_peer_close_leave_no_live_connection():
    async def quiet(socket):
        await socket.wait_closed()
    async with serve(quiet, '127.0.0.1', 0) as server:
        connection = await open_loopback_socket(port(server))
        pending = asyncio.create_task(connection.socket.recv())
        await asyncio.sleep(.01)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        await connection.close()
        assert connection.socket.state.name == 'CLOSED'
    async def peer_close(socket):
        await socket.close(code=1011)
    async with serve(peer_close, '127.0.0.1', 0) as server:
        connection = await open_loopback_socket(port(server))
        try:
            with pytest.raises(ConnectionClosedError) as failure:
                await connection.socket.recv()
            assert failure.value.rcvd.code == 1011
        finally:
            await connection.close()


async def test_public_factory_fixed_contract_no_connection_arguments(monkeypatch):
    calls = []
    sentinel = object()
    async def fake(uri, **kwargs):
        calls.append((uri, kwargs))
        return sentinel
    monkeypatch.setattr(module, '_NoRedirectConnect', fake)
    connection = await open_market_socket()
    contract = connector_contract()
    assert calls == [(contract['endpoint'], contract['options'])]
    assert connection.socket is sentinel and connection.provenance_class == 'prospective'
    assert contract['options']['proxy'] is None
    assert contract['options']['max_queue'] == 4
    assert contract['redirects'] == 'refused' and contract['retries'] == 0
    for key in ('endpoint', 'headers', 'token', 'provenance', 'connect_factory'):
        with pytest.raises(TypeError):
            await open_market_socket(**{key: None})
    # Mutating a returned manifest cannot alter later frozen contracts.
    contract['options']['proxy'] = True
    assert connector_contract()['options']['proxy'] is None


@pytest.mark.parametrize('value', [True, 0, 65536, '80', 'ws://example.com'])
async def test_loopback_seam_rejects_remote_or_invalid_target(value):
    with pytest.raises(ValueError, match='loopback'):
        await open_loopback_socket(value)


async def test_unverified_library_and_open_failure_do_not_retry(monkeypatch):
    monkeypatch.setattr(module.websockets, '__version__', '999.0')
    with pytest.raises(ValueError, match='unverified'):
        await open_market_socket()
    monkeypatch.undo()
    calls = []
    async def fail(*args, **kwargs):
        calls.append(args)
        raise OSError('synthetic connect failure')
    monkeypatch.setattr(module, '_NoRedirectConnect', fail)
    with pytest.raises(OSError):
        await open_market_socket()
    assert len(calls) == 1


async def test_cancelled_connect_and_close_failure_abort_without_hiding_error(monkeypatch):
    entered = asyncio.Event()
    async def wait(*args, **kwargs):
        entered.set()
        await asyncio.Future()
    monkeypatch.setattr(module, '_NoRedirectConnect', wait)
    task = asyncio.create_task(open_market_socket())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    class Fake:
        transport = None
        aborted = False
        def abort(self):
            self.aborted = True
        async def close(self):
            raise OSError('synthetic close error')
    fake = Fake()
    fake.transport = fake
    with pytest.raises(OSError):
        await module.MarketConnection(fake, 'synthetic', 'loopback').close()
    assert fake.aborted


async def test_actual_handshake_timeout_has_one_attempt_and_no_retry():
    entered, release = asyncio.Event(), asyncio.Event()
    requests = []
    async def stall(connection, request):
        requests.append(request.path)
        entered.set()
        await release.wait()
        return connection.respond(503, 'fixture done')
    async def handler(socket):
        raise AssertionError('timed-out handshake cannot reach handler')
    async with serve(handler, '127.0.0.1', 0, process_request=stall) as server:
        task = asyncio.create_task(open_loopback_socket(port(server)))
        await entered.wait()
        try:
            with pytest.raises(TimeoutError):
                await task
        finally:
            release.set()
    assert requests == ['/ws/market']


async def test_close_deadline_aborts_and_preserves_timeout_even_if_abort_fails():
    class Stalled:
        transport = None
        aborted = False
        def abort(self):
            self.aborted = True
            raise RuntimeError('secondary abort failure')
        async def close(self):
            await asyncio.Future()
    socket = Stalled()
    socket.transport = socket
    with pytest.raises(TimeoutError):
        await module.MarketConnection(socket, 'synthetic', 'loopback').close()
    assert socket.aborted
