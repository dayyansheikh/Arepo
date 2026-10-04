"""Finite journalled socket window; public and loopback paths have distinct provenance."""

import asyncio
import time
from contextlib import suppress

from websockets.exceptions import WebSocketException

from astrolabe.feature_store.capture import _clock, _json_bytes
from astrolabe.feature_store.source_run import _ordered_clocks, _pair

from .bound_window import _fresh, _pre
from .socket_connector import open_loopback_socket, open_market_socket
from .socket_window_journal import LIMITS, SocketJournal, check, scope

NETWORK_ERRORS = (OSError, TimeoutError, WebSocketException)


def _error(exc):
    def code(value):
        result = getattr(value, "code", None)
        return int(result) if isinstance(result, int) and 1000 <= result <= 4999 else None

    return {
        "exception_type": type(exc).__name__,
        "sent_close_code": code(getattr(exc, "sent", None)),
        "received_close_code": code(getattr(exc, "rcvd", None)),
    }


async def _receive(socket):
    try:
        raw = await socket.recv()
    except NETWORK_ERRORS as exc:
        return None, _clock(), _error(exc)
    return raw, _clock(), None


async def _send(journal, socket, binding, policy, payload, kind):
    journal.event(kind + "_intent", raw=payload)
    start = _clock()
    if kind == "subscription" and not _fresh(binding, start, policy):
        journal.event("refused", observed=start, reason="identity_expired_before_subscription")
        return None
    try:
        async with asyncio.timeout(LIMITS["send_timeout_seconds"]):
            await socket.send(payload)
    except NETWORK_ERRORS as exc:
        journal.event(
            kind + "_error", observed=_clock(), error=_error(exc), operation_started=start
        )
        return None
    observed = _clock()
    journal.event(kind + "_sent", observed=observed, operation_started=start)
    return observed


async def _interval(journal, connection, binding, policy, duration_ms):
    payload = _json_bytes(
        {"assets_ids": [binding["identity"]["token_id"]], "type": "market"}
    ).decode("utf-8")
    anchor = await _send(journal, connection.socket, binding, policy, payload, "subscription")
    if anchor is None:
        return
    end_ns = int(anchor["monotonic_ns"]) + duration_ms * 1000000
    ping_number, pending = 1, None
    try:
        while True:
            if pending is not None and pending.done():
                raw, observed, error = pending.result()
                pending = None
                if error:
                    journal.event("receive_error", observed=observed, error=error)
                    break
                _, truncated = journal.event("received", observed=observed, raw=raw)
                if truncated:
                    journal.event("budget_stop")
                    break
                continue
            now = time.monotonic_ns()
            if now >= end_ns:
                journal.event("interval_ended")
                break
            if (
                journal.frames >= LIMITS["max_frames"]
                or journal.raw_bytes + 4 >= LIMITS["max_raw_bytes"]
                or journal.count >= LIMITS["max_events"] - 6
            ):
                journal.event("budget_stop")
                break
            ping_ns = int(anchor["monotonic_ns"]) + ping_number * 10000000000
            if now >= ping_ns:
                # websockets recv cancellation is lossless. Stop the pending receive before
                # sending so operation receipts cannot interleave with send-intent durability.
                if pending is not None:
                    pending.cancel()
                    with suppress(asyncio.CancelledError):
                        await pending
                    pending = None
                if await _send(journal, connection.socket, binding, policy, "PING", "ping") is None:
                    break
                ping_number += 1
                continue
            if pending is None:
                check(journal.root, journal.started, LIMITS["max_frame_bytes"] + 16384)
                pending = asyncio.create_task(_receive(connection.socket))
            await asyncio.wait(
                {pending}, timeout=max(0, min(end_ns, ping_ns) - time.monotonic_ns()) / 1000000000
            )
    finally:
        if pending is not None:
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending


async def _capture(pre_root, *, output_root, policy, duration_ms, port):
    journal = SocketJournal(pre_root, output_root, policy, duration_ms, port)
    connection, failed, stage = None, None, "pre_binding"
    try:
        _, pa = _pair(journal.root, "socket_window_policy")
        read_started = _clock()
        binding = _pre(journal.pre)
        completed = _clock()
        if not _ordered_clocks(
            binding["pre_computation"]["computation_available_at"], read_started
        ):
            raise ValueError("pre-computation unavailable before actual socket read")
        journal.save(
            "socket_window_binding",
            {
                "binding": binding,
                "policy_hash": pa["payload_hash"],
                "read_started_at": read_started,
                "read_completed_at": completed,
            },
        )
        _, ba = _pair(journal.root, "socket_window_binding")
        provenance_ok = (
            binding["pre_computation"]["source_provenance_class"] == scope(port)["provenance_class"]
        )
        fresh = all(_fresh(binding, at, policy) for at in (completed, ba["durable_ack"]))
        if not provenance_ok or not fresh:
            journal.event(
                "refused",
                reason="provenance_mismatch" if not provenance_ok else "pre_binding_stale",
            )
        else:
            stage = "connect"
            now = _clock()
            if not _fresh(binding, now, policy):
                journal.event(
                    "refused", observed=now, reason="identity_expired_before_subscription"
                )
            else:
                journal.event("connect_intent", observed=now)
                start = _clock()
                try:
                    connection = (
                        await open_market_socket()
                        if port is None
                        else await open_loopback_socket(port)
                    )
                except NETWORK_ERRORS as exc:
                    journal.event(
                        "connect_error",
                        observed=_clock(),
                        operation_started=start,
                        error=_error(exc),
                    )
                else:
                    journal.event("connected", observed=_clock(), operation_started=start)
                    if (
                        connection.provenance_class != scope(port)["provenance_class"]
                        or connection.endpoint != scope(port)["endpoint"]
                    ):
                        raise ValueError("socket transport identity/provenance differs")
                    stage = "subscribed_interval"
                    await _interval(journal, connection, binding, policy, duration_ms)
    except BaseException as exc:
        failed = exc
    finally:
        if connection is not None:
            try:
                journal.event("close_intent")
                start = _clock()
                try:
                    await connection.close()
                except NETWORK_ERRORS as exc:
                    journal.event(
                        "close_error", observed=_clock(), operation_started=start, error=_error(exc)
                    )
                else:
                    journal.event("closed", observed=_clock(), operation_started=start)
            except BaseException as exc:
                # Persistence can fail before close starts. Still release the actual socket;
                # retain the original failure and never turn a disk failure into a source error.
                try:
                    await connection.close()
                except BaseException:
                    pass
                if failed is None:
                    failed = exc
                    stage = "cleanup"
    if failed is not None:
        try:
            journal.failure(failed, stage)
        except (OSError, ValueError):
            pass
        raise failed
    try:
        return journal.finish()
    except BaseException as exc:
        with suppress(OSError, ValueError):
            journal.failure(exc, "final_replay")
        raise


async def capture_market_socket(pre_computation_root, *, output_root, policy, duration_ms=60000):
    """Explicit standalone public diagnostic; no production/CLI/scheduler entry point."""
    return await _capture(
        pre_computation_root,
        output_root=output_root,
        policy=policy,
        duration_ms=duration_ms,
        port=None,
    )


async def capture_loopback_socket(
    pre_computation_root, *, output_root, policy, port, duration_ms=60000
):
    """Real local wire tests retain synthetic provenance; never accept an external URI."""
    return await _capture(
        pre_computation_root,
        output_root=output_root,
        policy=policy,
        duration_ms=duration_ms,
        port=port,
    )
