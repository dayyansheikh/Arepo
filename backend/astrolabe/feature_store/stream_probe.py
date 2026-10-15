"""Finite public market-channel diagnostic; no reconnect loop or background task."""

import asyncio
import json
import time
import uuid
from dataclasses import asdict

import httpx

from .capture import (
    Budget,
    CaptureJournal,
    _clock,
    _digest,
    _json_bytes,
    _sync_directory,
    _write_once,
    finish_parse,
)
from .sources import SOURCES
from .types import uint_text


def _persist_frame(journal, raw, subscription, started, received, *, error=None):
    journal.count += 1
    journal.bytes += len(raw)
    source = SOURCES["clob.market_stream"]
    capture_id = str(uuid.uuid4())
    folder = journal.root / capture_id
    folder.mkdir(mode=0o700)
    _sync_directory(journal.root)
    receipt = {
        "schema_version": "fs2-receipt-v2", "capture_id": capture_id,
        "session_hash": _digest((journal.root / "session.json").read_bytes()),
        "session_id": journal.session_id, "receipt_ordinal": journal.count,
        "capture_kind": journal.kind, "source_id": source.source_id,
        "source_version": source.version, "source_contract": asdict(source),
        "request": {"method": "WS_RECEIVE", "url": source.endpoint, "params": subscription},
        "previous_capture_id": None, "request_started": started,
        "first_byte": None, "first_received": received, "status": None, "headers": {},
        "transport_error": error, "raw_bytes": len(raw), "raw_hash": _digest(raw),
        "clock_error_bound_ms": None,
        "scope": "bounded stream diagnostic; continuity and sequence completeness unproven",
    }
    _write_once(folder / "raw.bin", raw)
    content = _json_bytes(receipt)
    _write_once(folder / "receipt.json", content)
    _write_once(folder / "raw_ack.json", _json_bytes({"receipt_hash": _digest(content),
                                                    "raw_hash": _digest(raw),
                                                    "durable_ack": _clock()}))
    return finish_parse(folder)


async def probe_market_stream(root, token_id, *, frame_limit=3, seconds=10, connect_factory=None):
    """One subscription, <=5 frames, <=10s including connection; no access workaround."""
    token_id = uint_text(token_id, bits=256)
    if type(frame_limit) is not int or not 1 <= frame_limit <= 5:
        raise ValueError("frame limit must be in 1..5")
    if type(seconds) is not int or not 1 <= seconds <= 10:
        raise ValueError("stream diagnostic duration must be in 1..10 seconds")
    journal = CaptureJournal(
        root, budget=Budget(requests=frame_limit, total_seconds=seconds),
        transport=(httpx.MockTransport(lambda request: None)
                   if connect_factory is not None else None),
    )
    source = SOURCES["clob.market_stream"]
    subscription = {"assets_ids": [token_id], "type": "market"}
    started, start_monotonic = _clock(), time.monotonic()
    results = []
    connection = None
    network_pending = False
    try:
        async with asyncio.timeout(seconds):
            network_pending = True
            if connect_factory is not None:
                connection = await connect_factory()
            else:
                import websockets

                connection = await websockets.connect(
                    source.endpoint, open_timeout=min(5, seconds), close_timeout=1,
                    compression=None, max_size=journal.budget.bytes_per_response,
                    max_queue=4, ping_interval=None,
                    user_agent_header="Arepo-Research-Verification/2.0",
                )
            await connection.send(json.dumps(subscription))
            network_pending = False
            for _ in range(frame_limit):
                if journal.bytes >= journal.budget.total_bytes:
                    break
                network_pending = True
                raw = await connection.recv()
                network_pending = False
                received = _clock()
                raw = raw.encode("utf-8") if isinstance(raw, str) else raw
                if not isinstance(raw, bytes):
                    raise ValueError("unexpected WebSocket frame type")
                remaining = min(journal.budget.bytes_per_response,
                                journal.budget.total_bytes - journal.bytes)
                error = "byte_budget_exceeded" if len(raw) > remaining else None
                results.append(_persist_frame(journal, raw[:remaining], subscription,
                                              started, received, error=error))
                if error:
                    break
    except asyncio.CancelledError:
        if journal.count < frame_limit:
            results.append(_persist_frame(journal, b"", subscription, started, _clock(),
                                          error="cancelled"))
        raise
    except (TimeoutError, OSError) as exc:
        if not network_pending:
            raise  # local persistence failures are not converted into upstream failures
        if journal.count < frame_limit:
            results.append(_persist_frame(journal, b"", subscription, started, _clock(),
                                          error=type(exc).__name__))
    except Exception as exc:
        from websockets.exceptions import WebSocketException

        if not isinstance(exc, WebSocketException):
            raise
        if journal.count < frame_limit:
            results.append(_persist_frame(journal, b"", subscription, started, _clock(),
                                          error=type(exc).__name__))
    finally:
        if connection is not None:
            try:
                async with asyncio.timeout(2):
                    await connection.close()
            except (TimeoutError, OSError):
                pass  # captured frames remain intact even when transport close fails
    report = {"schema_version": "fs2-stream-probe-v1", "capture_directory": str(root),
              "frames_or_failed_attempts": len(results), "bytes": journal.bytes,
              "elapsed_seconds": str(time.monotonic() - start_monotonic),
              "research_admitted": False, "complete_continuous_history": False}
    _write_once(journal.root / "stream_report.json", _json_bytes(report))
    return results, report
