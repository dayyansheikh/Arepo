"""Regression tests for defects found in the independent adversarial review.

B1: WS never signalled DEGRADED for a "connect+subscribe OK, session dies before any
    message" loop (failure counter was reset on subscribe).
B2: backtest indexed a *filtered* price array by raw frame index -> misalignment / look-ahead
    leak when a frame has no derivable price.
M1: resp.json() could raise a raw JSONDecodeError instead of a typed error.
M3: look-ahead guard was a bare assert (stripped under -O) with no horizon validation.
"""
import asyncio

import httpx
import pytest
import respx

from astrolabe.analytics.backtest import run_backtest
from astrolabe.clients.clob_rest import ClobRestClient
from astrolabe.clients.errors import UpstreamSchemaError
from astrolabe.clients.gamma import GammaClient
from astrolabe.config import Settings
from astrolabe.domain.enums import ConnState


# ---------------------------------------------------------------- B1: WS degraded signalling
class _DyingConnection:
    """Connects and accepts the subscribe, but recv() always dies immediately."""

    def __init__(self):
        self.sent: list[str] = []

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        raise ConnectionError("server closed right after subscribe")

    async def close(self) -> None:
        pass


async def test_ws_signals_degraded_when_session_dies_before_any_message():
    from astrolabe.clients.clob_ws import ClobWebSocketClient

    degraded_calls: list[int] = []
    settings = Settings(
        ws_reconnect_base_seconds=0.001,
        ws_reconnect_max_seconds=0.002,
        ws_stale_seconds=0.05,
        ws_ping_interval_seconds=0.05,
    )

    async def factory():
        return _DyingConnection()

    client = ClobWebSocketClient(
        token_ids=["t1"], settings=settings, connect_factory=factory,
        on_degraded=lambda: degraded_calls.append(1), degraded_after_failures=3,
    )
    # Let the reconnect loop churn briefly, then stop.
    task = asyncio.create_task(client.run())
    await asyncio.sleep(0.2)
    client.stop()
    with pytest.raises((asyncio.CancelledError, Exception)):
        await asyncio.wait_for(task, timeout=1.0)

    # The failure streak must accumulate across cycles and trip DEGRADED (previously it was
    # reset on every successful subscribe, so this never fired).
    assert degraded_calls, "on_degraded should have fired for a persistent failure loop"


# ---------------------------------------------------------------- B2: backtest frame alignment
class _GappyPlayer:
    """Minimal ReplayPlayer stand-in: one market, one token, with a missing-price frame."""

    # prices by frame; None => no price that frame (frame 2 has a gap)
    _P = [0.50, 0.52, None, 0.70, 0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.60, 0.58]

    def __init__(self):
        self.meta = {"seed": 1}

    def market_ids(self):
        return ["mk"]

    def token_ids(self, market_id):
        return ["tok"]

    def n_frames(self, market_id):
        return len(self._P)

    def prices(self, market_id, token_id, upto_index=None):
        end = len(self._P) - 1 if upto_index is None else upto_index
        return [p for p in self._P[: end + 1] if p is not None]

    def volumes(self, market_id, token_id, upto_index=None):
        return []

    def _mk_book(self, mid):
        from astrolabe.domain.models import BookLevel, OrderBook
        if mid is None:
            return OrderBook(token_id="tok")
        return OrderBook(
            token_id="tok",
            bids=[BookLevel(price=max(0.01, mid - 0.01), size=100)],
            asks=[BookLevel(price=min(0.99, mid + 0.01), size=100)],
        )

    def book_at(self, market_id, token_id, index):
        return self._mk_book(self._P[index] if self._P[index] is not None else None)

    def snapshot_at(self, market_id, token_id, index):
        from astrolabe.domain.models import MarketSnapshot
        p = self._P[index]
        return MarketSnapshot(
            token_id="tok", market_id="mk", book=self._mk_book(p),
            last_trade_price=p, midpoint=(p if p is not None else None),
        )


def test_backtest_frame_aligned_entry_and_forward_prices():
    player = _GappyPlayer()
    r = run_backtest(player, strength_threshold=0.0, horizon=3, min_history=3, zscore_window=8)
    # Every scored event's entry/forward price must equal the raw-frame price (not a shifted,
    # filtered-array value). Frame 2 has no price and must never be used as an entry.
    for e in r.events:
        assert e.frame != 2  # no signal anchored on the gap frame
        assert e.entry_price == pytest.approx(_GappyPlayer._P[e.frame])
        if e.forward_price is not None:
            assert e.forward_price == pytest.approx(_GappyPlayer._P[e.frame + r.horizon])


def test_backtest_rejects_bad_horizon():
    with pytest.raises(ValueError):
        run_backtest(_GappyPlayer(), horizon=0)


# ---------------------------------------------------------------- M1: non-JSON body -> typed
@respx.mock
async def test_clob_non_json_body_raises_typed_error():
    respx.get("https://clob.polymarket.com/book").mock(
        return_value=httpx.Response(200, content=b"<html>not json</html>")
    )
    client = ClobRestClient(settings=Settings(http_max_retries=0))
    with pytest.raises(UpstreamSchemaError):
        await client.get_book("t")
    await client.aclose()


@respx.mock
async def test_gamma_non_json_body_raises_typed_error():
    respx.get("https://gamma-api.polymarket.com/markets").mock(
        return_value=httpx.Response(200, content=b"not json at all")
    )
    client = GammaClient(settings=Settings(http_max_retries=0))
    with pytest.raises(UpstreamSchemaError):
        await client.list_markets(limit=1)
    await client.aclose()


# ---------------------------------------------------------------- sanity: default dataset still ok
def test_default_backtest_unchanged_after_fix():
    r = run_backtest()
    assert r.sample_size == 16 and r.hit_rate == pytest.approx(0.625)


def test_ws_import_conn_state():
    # trivial guard that ConnState import path is intact
    assert ConnState.DEGRADED.value == "degraded"
