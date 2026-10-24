import asyncio
import json

import pytest

from astrolabe.feature_store.stream_probe import probe_market_stream


class Connection:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.sent = []
        self.closed = False

    async def send(self, value):
        self.sent.append(json.loads(value))

    async def recv(self):
        value = next(self.frames, None)
        if value is None:
            await asyncio.Event().wait()
        return value

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_finite_frames_preserve_bytes_and_tag_injected_stream_synthetic(tmp_path):
    connection = Connection([b'{"event_type":"book"}', '[{"event_type":"price_change"}]'])

    async def connect():
        return connection

    captures, report = await probe_market_stream(tmp_path.resolve() / "fs2_capture_stream", "1",
                                                frame_limit=2, connect_factory=connect)
    assert connection.closed and len(connection.sent) == 1
    assert connection.sent[0] == {"assets_ids": ["1"], "type": "market"}
    assert len(captures) == 2
    assert all(c["parsed"]["parse_error"] is None for c in captures)
    assert all(c["receipt"]["capture_kind"] == "synthetic" for c in captures)
    assert all(c["receipt"]["status"] is None for c in captures)
    assert not report["research_admitted"] and not report["complete_continuous_history"]


@pytest.mark.asyncio
async def test_quiet_stream_deadline_preserves_gap_and_closes(tmp_path):
    connection = Connection([])

    async def connect():
        return connection

    captures, _ = await probe_market_stream(tmp_path.resolve() / "fs2_capture_timeout", "1",
                                           seconds=1, connect_factory=connect)
    assert connection.closed
    assert captures[0]["parsed"]["parse_error"] == "TimeoutError"
    assert captures[0]["raw"] == b""


@pytest.mark.asyncio
async def test_oversized_mock_frame_is_bounded(tmp_path):
    connection = Connection([b'a' * 300000])

    async def connect():
        return connection

    captures, report = await probe_market_stream(tmp_path.resolve() / "fs2_capture_limit", "1",
                                                connect_factory=connect)
    assert report["bytes"] == 262144
    assert captures[0]["parsed"]["parse_error"] == "byte_budget_exceeded"
    assert connection.closed


@pytest.mark.asyncio
async def test_local_persistence_failure_is_not_hidden_as_network_failure(tmp_path, monkeypatch):
    from astrolabe.feature_store import stream_probe

    connection = Connection([b'{}'])

    async def connect():
        return connection

    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise OSError("local disk failure")

    monkeypatch.setattr(stream_probe, "_persist_frame", fail)
    with pytest.raises(OSError, match="local disk"):
        await probe_market_stream(tmp_path.resolve() / "fs2_capture_disk", "1",
                                  connect_factory=connect)
    assert calls == 1 and connection.closed
