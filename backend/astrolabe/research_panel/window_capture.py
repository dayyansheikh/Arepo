"""One finite synthetic stream window. No live socket, background task or reconnect."""

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass

from astrolabe.feature_store.capture import _json_bytes

from .window_journal import LIMITS, WindowJournal


@dataclass(frozen=True)
class SyntheticWindowFeed:
    """Sequential relative delays in milliseconds and exact inbound wire payloads."""

    frames: tuple
    disconnect_when_exhausted: bool = False

    def __post_init__(self):
        if type(self.frames) is not tuple or len(self.frames) > LIMITS['max_frames'] + 1:
            raise ValueError('bounded immutable synthetic feed required')
        if type(self.disconnect_when_exhausted) is not bool:
            raise ValueError('explicit synthetic disconnect flag required')
        total = 0
        for entry in self.frames:
            if (type(entry) is not tuple or len(entry) != 2 or type(entry[0]) is not int
                    or not 0 <= entry[0] <= 60000 or type(entry[1]) not in {str, bytes}):
                raise ValueError('bounded delay and exact synthetic wire payload required')
            raw = entry[1].encode('utf-8') if isinstance(entry[1], str) else entry[1]
            if len(raw) > LIMITS['max_frame_bytes'] + 1:
                raise ValueError('synthetic frame allocation exceeded')
            total += len(raw)
        if total > LIMITS['max_raw_bytes'] + LIMITS['max_frame_bytes']:
            raise ValueError('synthetic fixture allocation exceeded')


async def _receive(iterator, disconnect):
    try:
        delay, raw = next(iterator)
    except StopIteration:
        if disconnect:
            raise EOFError('synthetic connection ended') from None
        await asyncio.Future()  # the driver's fixed deadline cancels this pending receive
    await asyncio.sleep(delay / 1000)
    return raw


async def capture_window(root, *, token_id, condition_id, feed, duration_ms=60000):
    """Actual synthetic receive/save clocks; no supplied clocks or prospective override."""
    if type(feed) is not SyntheticWindowFeed:
        raise ValueError('live window transport closed; exact synthetic feed required')
    journal = WindowJournal(root, token_id=token_id, condition_id=condition_id,
                            duration_ms=duration_ms)
    pending = None
    try:
        journal.event('connected')
        subscription = {'assets_ids': [str(token_id)], 'type': 'market'}
        journal.event('subscription_intent', _json_bytes(subscription))
        anchor, _ = journal.event('subscription_sent')
        loop = asyncio.get_running_loop()
        # Account for subscription acknowledgement persistence; do not start a new full
        # interval after that work or use an independent wall-clock anchor.
        elapsed = (time.monotonic_ns() - int(anchor['monotonic_ns'])) / 1000000000
        start = loop.time() - elapsed
        end = start + duration_ms / 1000
        ping_number = 1
        iterator = iter(feed.frames)
        while True:
            if pending is not None and pending.done():
                try:
                    raw = pending.result()
                except EOFError:
                    pending = None
                    journal.event('disconnected', error='EOFError')
                    break
                pending = None
                _, truncated = journal.event('received', raw)
                if truncated:
                    journal.event('budget_stop', error='raw_truncated')
                    break
                continue
            now = loop.time()
            if now >= end:
                journal.event('interval_ended')
                break
            if (journal.frames >= LIMITS['max_frames']
                    or journal.raw_bytes >= LIMITS['max_raw_bytes']):
                journal.event('budget_stop')
                break
            ping_due = start + ping_number * LIMITS['heartbeat_interval_ms'] / 1000
            if now >= ping_due:
                journal.event('ping_intent', 'PING')
                journal.event('ping_sent')
                ping_number += 1
                continue
            if pending is None:
                journal.reserve(LIMITS['max_frame_bytes'] + 16384)
                pending = asyncio.create_task(_receive(iterator, feed.disconnect_when_exhausted))
            await asyncio.wait({pending}, timeout=max(0, min(end, ping_due) - loop.time()))
        if pending is not None:
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending
            pending = None
        journal.event('closed')
        return journal.finish()
    except BaseException as exc:
        try:
            journal.failure(exc)
        except (OSError, ValueError):
            pass
        raise
    finally:
        if pending is not None:
            pending.cancel()
            with suppress(asyncio.CancelledError, EOFError):
                await pending
