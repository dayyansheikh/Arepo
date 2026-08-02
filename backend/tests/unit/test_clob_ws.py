"""Unit tests for the resilient CLOB market-channel WebSocket client.

No real network is used anywhere here: every test injects a fake ``connect_factory``.
Time is kept deterministic by using tiny ``Settings`` overrides plus, where backoff
timing itself is under test, a monkeypatched ``_sleep`` that never actually waits.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from astrolabe.clients.clob_ws import ClobWebSocketClient
from astrolabe.config import Settings
from astrolabe.domain.enums import ConnState


# --------------------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------------------
class FakeConnectionClosed(Exception):
    """Raised by ``FakeConnection.recv`` once its scripted messages are exhausted."""


class FakeConnection:
    """Yields a scripted list of messages, then raises to simulate server closure."""

    def __init__(self, messages: list[str] | None = None) -> None:
        self.to_send: list[str] = list(messages or [])
        self.sent: list[str] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        if self.to_send:
            return self.to_send.pop(0)
        raise FakeConnectionClosed("exhausted")

    async def close(self) -> None:
        self.closed = True


class StallingConnection(FakeConnection):
    """A connection whose ``recv()`` never resolves on its own.

    Used to exercise stale-timeout and ping-cadence behaviour without ever needing a
    "real" message; the surrounding ``asyncio.wait_for``/stale timeout is what unblocks it.
    """

    async def recv(self) -> str:
        await asyncio.sleep(1000)
        raise AssertionError("StallingConnection.recv should never actually return")


def make_settings(**overrides: float) -> Settings:
    base: dict[str, float] = dict(
        ws_reconnect_base_seconds=0.005,
        ws_reconnect_max_seconds=0.02,
        ws_stale_seconds=1.0,
        ws_ping_interval_seconds=1.0,
    )
    base.update(overrides)
    return Settings(**base)


def factory_returning(conn: object):
    async def _factory():
        return conn

    return _factory


class CountingFactory:
    """connect_factory that hands out a fresh connection (of ``conn_cls``) every call."""

    def __init__(self, conn_cls=StallingConnection) -> None:
        self.conn_cls = conn_cls
        self.connections: list[FakeConnection] = []

    async def __call__(self):
        conn = self.conn_cls()
        self.connections.append(conn)
        return conn


async def _no_real_sleep(seconds: float) -> None:
    """Drop-in replacement for ``ClobWebSocketClient._sleep`` that never really waits."""
    await asyncio.sleep(0)


# --------------------------------------------------------------------------------------
# Subscribe payload
# --------------------------------------------------------------------------------------
async def test_subscribe_message_content_is_correct():
    conn = FakeConnection()
    client = ClobWebSocketClient(
        token_ids=["111", "222"],
        settings=make_settings(),
        connect_factory=factory_returning(conn),
    )
    await client._subscribe(conn)

    assert len(conn.sent) == 1
    payload = json.loads(conn.sent[0])
    assert payload == {"assets_ids": ["111", "222"], "type": "market"}


# --------------------------------------------------------------------------------------
# Book snapshot application
# --------------------------------------------------------------------------------------
async def test_book_snapshot_populates_best_first_ordering():
    client = ClobWebSocketClient(token_ids=["t1"], settings=make_settings())
    msg = {
        "event_type": "book",
        "asset_id": "t1",
        "market": "0xabc",
        "bids": [{"price": "0.48", "size": "50"}, {"price": "0.49", "size": "100"}],
        "asks": [{"price": "0.53", "size": "40"}, {"price": "0.52", "size": "80"}],
        "timestamp": "1700000000000",
        "hash": "h1",
    }

    client._handle_raw_message(json.dumps(msg))
    book = client.get_book("t1")

    assert book is not None
    assert [lvl.price for lvl in book.bids] == [0.49, 0.48]
    assert [lvl.price for lvl in book.asks] == [0.52, 0.53]
    assert book.best_bid == 0.49
    assert book.best_ask == 0.52


# --------------------------------------------------------------------------------------
# price_change deltas: update, remove (size == "0"), best_bid/best_ask
# --------------------------------------------------------------------------------------
async def test_price_change_updates_and_removes_levels_and_respects_best():
    client = ClobWebSocketClient(token_ids=["t1"], settings=make_settings())
    snapshot = {
        "event_type": "book",
        "asset_id": "t1",
        "bids": [{"price": "0.48", "size": "50"}, {"price": "0.49", "size": "100"}],
        "asks": [{"price": "0.53", "size": "40"}, {"price": "0.52", "size": "80"}],
        "timestamp": "1700000000000",
        "hash": "snap1",
    }
    client._handle_raw_message(json.dumps(snapshot))

    change = {
        "event_type": "price_change",
        "market": "0xabc",
        "timestamp": "1700000001000",
        "price_changes": [
            # new best bid at 0.50
            {
                "asset_id": "t1",
                "price": "0.50",
                "size": "20",
                "side": "BUY",
                "hash": "c1",
                "best_bid": "0.50",
                "best_ask": "0.53",
            },
            # remove the level at 0.52 (size == "0"), new best ask becomes 0.53
            {
                "asset_id": "t1",
                "price": "0.52",
                "size": "0",
                "side": "SELL",
                "hash": "c2",
                "best_bid": "0.50",
                "best_ask": "0.53",
            },
        ],
    }
    client._handle_raw_message(json.dumps(change))

    book = client.get_book("t1")
    assert [lvl.price for lvl in book.bids] == [0.50, 0.49, 0.48]
    assert [lvl.price for lvl in book.asks] == [0.53]
    # The server's best_bid/best_ask hints must match what our maintained levels compute.
    assert book.best_bid == float(change["price_changes"][0]["best_bid"])
    assert book.best_ask == float(change["price_changes"][1]["best_ask"])


# --------------------------------------------------------------------------------------
# Dedup
# --------------------------------------------------------------------------------------
async def test_duplicate_message_is_ignored():
    client = ClobWebSocketClient(token_ids=["t1"], settings=make_settings())
    msg = {
        "event_type": "book",
        "asset_id": "t1",
        "bids": [{"price": "0.40", "size": "10"}],
        "asks": [{"price": "0.60", "size": "10"}],
        "timestamp": "1700000000000",
        "hash": "dup1",
    }
    client._handle_raw_message(json.dumps(msg))

    mutated = dict(msg)
    mutated["bids"] = [{"price": "0.10", "size": "999"}]  # would change the book if applied
    client._handle_raw_message(json.dumps(mutated))  # same (event_type, asset_id, hash, ts)

    book = client.get_book("t1")
    assert [lvl.price for lvl in book.bids] == [0.40]


# --------------------------------------------------------------------------------------
# Batched array messages
# --------------------------------------------------------------------------------------
async def test_batched_array_message_is_handled():
    client = ClobWebSocketClient(token_ids=["t1", "t2"], settings=make_settings())
    batch = [
        {
            "event_type": "book",
            "asset_id": "t1",
            "bids": [{"price": "0.4", "size": "10"}],
            "asks": [{"price": "0.6", "size": "10"}],
            "timestamp": "1700000000000",
            "hash": "b1",
        },
        {
            "event_type": "last_trade_price",
            "asset_id": "t2",
            "price": "0.33",
            "size": "5",
            "side": "BUY",
            "timestamp": "1700000000001",
        },
    ]
    client._handle_raw_message(json.dumps(batch))

    assert client.get_book("t1") is not None
    assert client.last_trade_prices["t2"] == 0.33


# --------------------------------------------------------------------------------------
# Stale detection -> reconnect
# --------------------------------------------------------------------------------------
async def test_stale_detection_triggers_reconnect():
    settings = make_settings(
        ws_stale_seconds=0.01,
        ws_reconnect_base_seconds=0.005,
        ws_reconnect_max_seconds=0.02,
    )
    factory = CountingFactory(conn_cls=StallingConnection)
    client = ClobWebSocketClient(token_ids=["t1"], settings=settings, connect_factory=factory)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(client.run(), timeout=0.08)

    assert len(factory.connections) >= 2
    for conn in factory.connections:
        assert conn.sent, "every reconnect must resubscribe"
        payload = json.loads(conn.sent[0])
        assert payload == {"assets_ids": ["t1"], "type": "market"}


# --------------------------------------------------------------------------------------
# Bounded exponential backoff + resubscribe on every reconnect
# --------------------------------------------------------------------------------------
async def test_reconnect_uses_bounded_backoff_and_resubscribes():
    settings = make_settings(
        ws_reconnect_base_seconds=0.01,
        ws_reconnect_max_seconds=0.04,
        ws_stale_seconds=5.0,
    )
    # FakeConnection([]) has recv() raise immediately -> forces a reconnect every cycle.
    factory = CountingFactory(conn_cls=lambda: FakeConnection([]))
    client = ClobWebSocketClient(token_ids=["t1"], settings=settings, connect_factory=factory)

    recorded_backoffs: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded_backoffs.append(seconds)
        await asyncio.sleep(0)

    client._sleep = fake_sleep

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(client.run(), timeout=0.05)

    assert len(factory.connections) >= 3
    for conn in factory.connections:
        assert len(conn.sent) == 1
        payload = json.loads(conn.sent[0])
        assert payload["assets_ids"] == ["t1"]

    assert len(recorded_backoffs) >= 2
    assert all(b1 <= b2 for b1, b2 in zip(recorded_backoffs, recorded_backoffs[1:], strict=False))
    assert recorded_backoffs[0] == pytest.approx(settings.ws_reconnect_base_seconds)
    assert max(recorded_backoffs) <= settings.ws_reconnect_max_seconds
    # With this many fast cycles inside the time budget, backoff should have hit its cap.
    assert settings.ws_reconnect_max_seconds in recorded_backoffs


# --------------------------------------------------------------------------------------
# Degraded state + callback after N consecutive failures
# --------------------------------------------------------------------------------------
async def test_degraded_after_n_consecutive_failures():
    settings = make_settings(ws_reconnect_base_seconds=0.005, ws_reconnect_max_seconds=0.01)
    degraded_calls: list[int] = []
    # State observed *at the moment* on_degraded fires -- this is the meaningful check;
    # after the whole client later stops (see below), state correctly reverts to
    # DISCONNECTED, so asserting on post-stop state would miss the DEGRADED window.
    state_when_degraded: list[ConnState] = []

    async def failing_factory():
        raise ConnectionRefusedError("no route to host")

    def on_degraded() -> None:
        degraded_calls.append(1)
        state_when_degraded.append(client.state)

    client = ClobWebSocketClient(
        token_ids=["t1"],
        settings=settings,
        connect_factory=failing_factory,
        on_degraded=on_degraded,
        degraded_after_failures=3,
    )
    client._sleep = _no_real_sleep

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(client.run(), timeout=0.05)

    assert state_when_degraded == [ConnState.DEGRADED]
    assert len(degraded_calls) == 1  # fires exactly once, not on every subsequent failure
    assert client._consecutive_failures >= 3
    # Once the client has fully stopped (task unwound), it must not keep claiming a
    # stale DEGRADED -- DISCONNECTED is the honest terminal state.
    assert client.state == ConnState.DISCONNECTED


# --------------------------------------------------------------------------------------
# PING cadence
# --------------------------------------------------------------------------------------
async def test_ping_sent_at_expected_cadence():
    settings = make_settings(ws_ping_interval_seconds=0.005, ws_stale_seconds=5.0)
    conn = StallingConnection()
    client = ClobWebSocketClient(
        token_ids=["t1"], settings=settings, connect_factory=factory_returning(conn)
    )

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(client.run(), timeout=0.05)

    pings = [s for s in conn.sent if s == "PING"]
    assert len(pings) >= 1


# --------------------------------------------------------------------------------------
# stop() / health() basics
# --------------------------------------------------------------------------------------
async def test_stop_cancels_run_and_sets_disconnected():
    settings = make_settings(ws_stale_seconds=5.0)
    conn = StallingConnection()
    client = ClobWebSocketClient(
        token_ids=["t1"], settings=settings, connect_factory=factory_returning(conn)
    )

    task = asyncio.create_task(client.run())
    await asyncio.sleep(0.01)  # let it connect + subscribe + start the session
    client.stop()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert client.state == ConnState.DISCONNECTED


async def test_health_reflects_initial_state():
    client = ClobWebSocketClient(token_ids=["t1"], settings=make_settings())
    health = client.health()
    assert health.name == "clob_ws"
    assert health.state == ConnState.DISCONNECTED
    assert health.last_success is None
