"""Resilient CLOB market-channel WebSocket client.

Maintains a live, in-memory view of order books for a set of CLOB token ids by consuming
the Polymarket CLOB market WebSocket feed. See ``docs/research-notes.md`` §4 for the
confirmed wire protocol this module implements.

Design notes:
- The network connection is created via an injectable ``connect_factory`` so this module
  can be fully unit-tested with no real network (see ``tests/unit/test_clob_ws.py``).
- Order-book state is maintained directly here (rather than importing
  ``astrolabe.ingest.normalize``) to avoid coupling to that module while it is under
  concurrent development; the book-snapshot parsing performed below is intentionally a
  small, self-contained duplicate of that logic.
- This client never falls back to REST itself — it only *signals* degradation (via
  ``state`` and the optional ``on_degraded`` callback) so a higher-level pipeline can
  decide to poll REST instead.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any, Protocol

from astrolabe.config import Settings, get_settings
from astrolabe.domain.enums import ConnState
from astrolabe.domain.models import BookLevel, OrderBook, SourceHealth, utcnow
from astrolabe.observability.logging import get_logger

logger = get_logger(__name__)

PING_TEXT = "PING"
PONG_TEXT = "PONG"

DEFAULT_DEGRADED_AFTER_FAILURES = 5
DEFAULT_DEDUP_MAXLEN = 4096


class WSConnectionLike(Protocol):
    """Minimal shape required of an injected (or real) WebSocket connection."""

    async def send(self, message: str) -> None: ...

    async def recv(self) -> str: ...

    async def close(self) -> None: ...


class _StaleConnection(Exception):
    """Raised internally when no message has arrived within ``ws_stale_seconds``."""


def _parse_timestamp_ms(raw: Any) -> datetime:
    """Parse a protocol timestamp (string of unix ms) into an aware UTC datetime.

    Defensive: falls back to "now" for missing/unparseable values rather than raising,
    since a malformed timestamp should never take down the WS client.
    """
    if raw is None:
        return utcnow()
    try:
        ms = int(raw)
    except (TypeError, ValueError):
        return utcnow()
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def _parse_levels(raw: Any) -> list[BookLevel]:
    """Parse a raw ``[{"price": "...", "size": "..."}, ...]`` list, dropping zero-size rows."""
    levels: list[BookLevel] = []
    if not raw:
        return levels
    for item in raw:
        try:
            price = float(item["price"])
            size = float(item["size"])
        except (KeyError, TypeError, ValueError):
            continue
        if size <= 0:
            continue
        levels.append(BookLevel(price=price, size=size))
    return levels


def _update_level(
    levels: list[BookLevel], price: float, size: float, *, reverse: bool
) -> list[BookLevel]:
    """Apply one price-level delta to a sorted level list, keeping best-first order.

    ``size == 0`` removes the level; otherwise the level is inserted/replaced.
    """
    remaining = [lvl for lvl in levels if lvl.price != price]
    if size > 0:
        remaining.append(BookLevel(price=price, size=size))
    remaining.sort(key=lambda lvl: lvl.price, reverse=reverse)
    return remaining


class ClobWebSocketClient:
    """A resilient client for the CLOB market-channel WebSocket.

    Not thread-safe; intended to be driven from a single asyncio task via :meth:`run`.
    """

    def __init__(
        self,
        token_ids: list[str],
        settings: Settings | None = None,
        connect_factory: Any | None = None,
        on_snapshot: Any | None = None,
        on_degraded: Any | None = None,
        degraded_after_failures: int = DEFAULT_DEGRADED_AFTER_FAILURES,
        dedup_maxlen: int = DEFAULT_DEDUP_MAXLEN,
    ) -> None:
        """
        Args:
            token_ids: CLOB asset ids to subscribe to on the market channel.
            settings: application settings; defaults to ``get_settings()``.
            connect_factory: async, zero-arg callable returning an object satisfying
                ``WSConnectionLike``. Defaults to a real ``websockets.connect`` factory
                against ``settings.clob_ws_url``. Tests MUST inject a fake here.
            on_snapshot: optional ``(token_id: str, book: OrderBook) -> None`` callback
                invoked whenever a token's book changes.
            on_degraded: optional zero-arg callback invoked the moment the client
                transitions into :attr:`ConnState.DEGRADED`.
            degraded_after_failures: consecutive connect/session failures before we
                declare the source degraded and stop retrying at the base backoff.
            dedup_maxlen: bounded size of the LRU dedup set.
        """
        self.token_ids = list(token_ids)
        self.settings = settings or get_settings()
        self._connect_factory = connect_factory or self._default_connect
        self.on_snapshot = on_snapshot
        self.on_degraded = on_degraded
        self._degraded_after_failures = degraded_after_failures

        self.state: ConnState = ConnState.DISCONNECTED
        self.last_message_at: datetime | None = None
        self.last_trade_prices: dict[str, float] = {}

        self._last_success: datetime | None = None
        self._last_error: str | None = None
        self._consecutive_failures = 0

        self._books: dict[str, OrderBook] = {}
        self._dedup: OrderedDict[tuple, None] = OrderedDict()
        self._dedup_maxlen = dedup_maxlen

        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._session_received_message = False
        self._degraded_notified = False

    # ------------------------------------------------------------------ connection setup
    async def _default_connect(self) -> WSConnectionLike:
        import websockets

        return await websockets.connect(self.settings.clob_ws_url)

    async def _subscribe(self, conn: WSConnectionLike) -> None:
        payload = json.dumps({"assets_ids": self.token_ids, "type": "market"})
        await conn.send(payload)
        logger.info(
            "clob_ws.subscribed",
            extra={"ctx_token_count": len(self.token_ids)},
        )

    async def _ping_loop(self, conn: WSConnectionLike) -> None:
        interval = self.settings.ws_ping_interval_seconds
        while True:
            await asyncio.sleep(interval)
            try:
                await conn.send(PING_TEXT)
            except Exception as exc:  # noqa: BLE001 - connection is dead, stop pinging
                logger.debug("clob_ws.ping_failed", extra={"ctx_error": str(exc)})
                return

    async def _safe_close(self, conn: WSConnectionLike | None) -> None:
        if conn is None:
            return
        with contextlib.suppress(Exception):
            await conn.close()

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    # ------------------------------------------------------------------------- dedup
    def _seen(self, key: tuple) -> bool:
        return key in self._dedup

    def _mark_seen(self, key: tuple) -> None:
        self._dedup[key] = None
        if len(self._dedup) > self._dedup_maxlen:
            self._dedup.popitem(last=False)

    # ---------------------------------------------------------------- message handling
    def _handle_raw_message(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("clob_ws.unparseable_message", extra={"ctx_raw": str(raw)[:200]})
            return
        messages = data if isinstance(data, list) else [data]
        for msg in messages:
            if isinstance(msg, dict):
                self._dispatch(msg)

    def _dispatch(self, msg: dict) -> None:
        event_type = msg.get("event_type")
        if event_type == "book":
            key = ("book", msg.get("asset_id"), msg.get("hash"), msg.get("timestamp"))
            if self._seen(key):
                return
            self._mark_seen(key)
            self._apply_book_snapshot(msg)
        elif event_type == "price_change":
            self._apply_price_change(msg)
        elif event_type == "last_trade_price":
            key = ("last_trade_price", msg.get("asset_id"), msg.get("hash"), msg.get("timestamp"))
            if self._seen(key):
                return
            self._mark_seen(key)
            self._apply_last_trade(msg)
        elif event_type == "tick_size_change":
            key = ("tick_size_change", msg.get("asset_id"), None, msg.get("timestamp"))
            if self._seen(key):
                return
            self._mark_seen(key)
            self._apply_tick_size_change(msg)
        else:
            logger.debug("clob_ws.unknown_event_type", extra={"ctx_event_type": event_type})

    def _apply_book_snapshot(self, msg: dict) -> None:
        asset_id = msg.get("asset_id")
        if not asset_id:
            return
        bids = sorted(_parse_levels(msg.get("bids")), key=lambda lvl: lvl.price, reverse=True)
        asks = sorted(_parse_levels(msg.get("asks")), key=lambda lvl: lvl.price)
        prev = self._books.get(asset_id)
        tick_size = prev.tick_size if prev else None
        if msg.get("tick_size") is not None:
            with contextlib.suppress(TypeError, ValueError):
                tick_size = float(msg["tick_size"])
        book = OrderBook(
            token_id=asset_id,
            bids=bids,
            asks=asks,
            tick_size=tick_size,
            timestamp=_parse_timestamp_ms(msg.get("timestamp")),
        )
        self._books[asset_id] = book
        logger.debug(
            "clob_ws.book_snapshot",
            extra={"ctx_asset_id": asset_id, "ctx_bids": len(bids), "ctx_asks": len(asks)},
        )
        if self.on_snapshot:
            self.on_snapshot(asset_id, book)

    def _apply_price_change(self, msg: dict) -> None:
        ts_raw = msg.get("timestamp")
        ts = _parse_timestamp_ms(ts_raw)
        for change in msg.get("price_changes") or []:
            asset_id = change.get("asset_id")
            if not asset_id:
                continue
            key = ("price_change", asset_id, change.get("hash"), ts_raw)
            if self._seen(key):
                continue
            self._mark_seen(key)
            try:
                price = float(change["price"])
                size = float(change.get("size", "0"))
            except (KeyError, TypeError, ValueError):
                continue
            side = str(change.get("side", "")).upper()
            is_bid = side == "BUY"

            book = self._books.get(asset_id) or OrderBook(token_id=asset_id)
            if is_bid:
                new_bids = _update_level(book.bids, price, size, reverse=True)
                new_asks = book.asks
            else:
                new_asks = _update_level(book.asks, price, size, reverse=False)
                new_bids = book.bids

            book = OrderBook(
                token_id=asset_id,
                bids=new_bids,
                asks=new_asks,
                tick_size=book.tick_size,
                timestamp=ts,
            )
            self._books[asset_id] = book
            logger.debug(
                "clob_ws.price_change",
                extra={
                    "ctx_asset_id": asset_id,
                    "ctx_side": side,
                    "ctx_price": price,
                    "ctx_size": size,
                },
            )
            if self.on_snapshot:
                self.on_snapshot(asset_id, book)

    def _apply_last_trade(self, msg: dict) -> None:
        asset_id = msg.get("asset_id")
        if not asset_id:
            return
        try:
            price = float(msg["price"])
        except (KeyError, TypeError, ValueError):
            return
        self.last_trade_prices[asset_id] = price
        logger.debug(
            "clob_ws.last_trade_price", extra={"ctx_asset_id": asset_id, "ctx_price": price}
        )

    def _apply_tick_size_change(self, msg: dict) -> None:
        asset_id = msg.get("asset_id")
        if not asset_id:
            return
        try:
            new_tick = float(msg["new_tick_size"])
        except (KeyError, TypeError, ValueError):
            return
        prev = self._books.get(asset_id) or OrderBook(token_id=asset_id)
        book = OrderBook(
            token_id=asset_id,
            bids=prev.bids,
            asks=prev.asks,
            tick_size=new_tick,
            timestamp=_parse_timestamp_ms(msg.get("timestamp")),
        )
        self._books[asset_id] = book
        logger.info(
            "clob_ws.tick_size_change",
            extra={"ctx_asset_id": asset_id, "ctx_new_tick_size": new_tick},
        )

    # ------------------------------------------------------------------------- session
    async def _session(self, conn: WSConnectionLike) -> None:
        """Read messages until stale timeout, stop requested, or the connection dies.

        Sets ``self._session_received_message`` so the caller can tell a session that
        received at least one real message (even if it later went stale) apart from one
        that never produced anything useful — used to decide whether backoff resets.
        """
        self.last_message_at = utcnow()
        self._session_received_message = False
        ping_task = asyncio.create_task(self._ping_loop(conn))
        try:
            while not self._stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(
                        conn.recv(), timeout=self.settings.ws_stale_seconds
                    )
                except TimeoutError as exc:
                    raise _StaleConnection() from exc

                now = utcnow()
                self.last_message_at = now
                self._last_success = now

                if raw == PONG_TEXT:
                    continue
                self._session_received_message = True
                self._handle_raw_message(raw)
        finally:
            ping_task.cancel()
            # NOTE: awaiting a task we just cancelled is ambiguous under asyncio's
            # cancellation model -- if *this* coroutine's enclosing task is itself
            # being cancelled right now (e.g. an outer ``asyncio.wait_for`` timing
            # out) while suspended on this very await, that external CancelledError
            # arrives indistinguishably from ping_task's own cancellation completing.
            # A bare ``contextlib.suppress(CancelledError)`` here would silently eat
            # the outer cancellation and the run() loop would never stop. Task.cancelling()
            # (3.11+) lets us tell the two apart: only re-raise if *our* task has a
            # pending cancellation request of its own.
            current = asyncio.current_task()
            try:
                await ping_task
            except asyncio.CancelledError:
                if current is not None and current.cancelling():
                    raise

    # ------------------------------------------------------------------- failure/health
    def _on_failure(self, message: str) -> None:
        self._consecutive_failures += 1
        self._last_error = message
        logger.warning(
            "clob_ws.failure",
            extra={"ctx_error": message, "ctx_consecutive_failures": self._consecutive_failures},
        )
        if self._consecutive_failures >= self._degraded_after_failures:
            self.state = ConnState.DEGRADED
            # ``self.state`` gets reset to CONNECTING at the top of every reconnect
            # attempt (see run()), so it can't be used as the "already notified" guard
            # -- that would refire on_degraded on every single subsequent failure once
            # degraded. Track the notification separately instead.
            if not self._degraded_notified:
                self._degraded_notified = True
                logger.error(
                    "clob_ws.degraded",
                    extra={"ctx_consecutive_failures": self._consecutive_failures},
                )
                if self.on_degraded:
                    self.on_degraded()
        else:
            self.state = ConnState.DISCONNECTED

    def health(self) -> SourceHealth:
        return SourceHealth(
            name="clob_ws",
            state=self.state,
            last_success=self._last_success,
            last_error=self._last_error,
        )

    # ------------------------------------------------------------------------ accessors
    def get_book(self, token_id: str) -> OrderBook | None:
        return self._books.get(token_id)

    def snapshot(self) -> dict[str, OrderBook]:
        return dict(self._books)

    # ----------------------------------------------------------------------------- run
    async def run(self) -> None:
        """Connect, subscribe, and consume messages until :meth:`stop` is called.

        Reconnects with bounded exponential backoff on any failure (connect error,
        subscribe error, session error, or staleness), resubscribing every time. After
        ``degraded_after_failures`` consecutive failures, ``state`` becomes DEGRADED and
        ``on_degraded`` fires (once) so a caller can fall back to REST polling.
        """
        self._task = asyncio.current_task()
        self._stop_event.clear()
        backoff = self.settings.ws_reconnect_base_seconds
        conn: WSConnectionLike | None = None
        try:
            while not self._stop_event.is_set():
                self.state = ConnState.CONNECTING
                logger.info("clob_ws.connecting", extra={"ctx_url": self.settings.clob_ws_url})

                # ``cycle_ok`` tracks whether this attempt was healthy enough to reset
                # backoff to the base interval: a connection that comes up and then dies
                # instantly (before ever receiving a message) should NOT reset backoff,
                # or a flapping server would pin us at the minimum reconnect interval
                # forever. A session that goes stale *after* receiving at least one
                # message, or that ends because ``stop()`` was called, counts as healthy.
                cycle_ok = False
                try:
                    conn = await self._connect_factory()
                except Exception as exc:  # noqa: BLE001 - any connect failure triggers backoff
                    self._on_failure(str(exc))
                    conn = None
                else:
                    try:
                        await self._subscribe(conn)
                    except Exception as exc:  # noqa: BLE001
                        self._on_failure(str(exc))
                        await self._safe_close(conn)
                        conn = None
                    else:
                        self.state = ConnState.CONNECTED
                        self._last_success = utcnow()
                        logger.info(
                            "clob_ws.connected", extra={"ctx_token_count": len(self.token_ids)}
                        )
                        try:
                            await self._session(conn)
                            cycle_ok = True  # loop exited cleanly (stop() was called)
                        except _StaleConnection:
                            # A session that went stale WITHOUT ever receiving a message is a
                            # failed cycle (connect+subscribe OK but no data) — count it so a
                            # persistent "silent server" eventually trips DEGRADED.
                            cycle_ok = self._session_received_message
                            if not self._session_received_message:
                                self._on_failure("stale before first message")
                            logger.warning(
                                "clob_ws.stale",
                                extra={"ctx_last_message_at": str(self.last_message_at)},
                            )
                        except Exception as exc:  # noqa: BLE001 - session died, reconnect
                            self._on_failure(str(exc))
                        finally:
                            await self._safe_close(conn)
                            conn = None
                        # Only a genuinely healthy cycle (received a message, or stopped
                        # cleanly) clears the failure streak. Resetting on mere subscribe
                        # success would let a "connect+subscribe OK, session dies before any
                        # message" loop reconnect forever without ever signalling DEGRADED.
                        if cycle_ok:
                            self._consecutive_failures = 0
                            self._degraded_notified = False

                if self._stop_event.is_set():
                    break
                await self._sleep(backoff)
                backoff = (
                    self.settings.ws_reconnect_base_seconds
                    if cycle_ok
                    else min(backoff * 2, self.settings.ws_reconnect_max_seconds)
                )
        finally:
            await self._safe_close(conn)
            self.state = ConnState.DISCONNECTED
            logger.info("clob_ws.stopped", extra={})

    def stop(self) -> None:
        """Request a graceful stop; cancels the running :meth:`run` task if any."""
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            self._task.cancel()
