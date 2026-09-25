"""Actual loopback windows preserve causal binding and immutable transport evidence."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from websockets.asyncio.server import serve

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.socket_window import capture_loopback_socket, capture_market_socket
from astrolabe.research_panel.socket_window_journal import LIMITS, check, read_socket_window
from tests.unit.test_research_panel_bound_window import pre
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_window_coverage import book


def output(tmp_path):
    return tmp_path.resolve() / "fs2_socket_window_test"


def events(root):
    return [
        _pair(root, p.stem)[0]
        for p in sorted(root.glob("event_*.json"))
        if not p.name.endswith("_ack.json")
    ]


async def capture(computation, tmp_path, handler=None, *, duration=500, policy=None):
    async def default(socket):
        await socket.recv()
        await socket.send(json.dumps(book()))
        await socket.send(b"raw\x00")
        await socket.send("invalid json")
        await socket.wait_closed()

    async with serve(handler or default, "127.0.0.1", 0, compression=None) as server:
        return await capture_loopback_socket(
            computation,
            output_root=output(tmp_path),
            port=server.sockets[0].getsockname()[1],
            duration_ms=duration,
            policy=policy or WindowBindingPolicy(60000, 60000),
        )


async def test_wire_binding_receipt_persistence_and_full_recovery(tmp_path):
    source, computation = await pre(tmp_path)
    before = snapshot(source), snapshot(computation)
    result = await capture(computation, tmp_path)
    root = output(tmp_path)
    assert result["state"] == "duration_completed" and result["frame_count"] == 3
    assert result["provenance_class"] == "synthetic"
    assert result["identity_fresh_at_subscription_completion"]
    assert not result["source_admitted"] and not result["continuous_sequence_proven"]
    policy, pa = _pair(root, "socket_window_policy")
    binding, ba = _pair(root, "socket_window_binding")
    assert _ordered_clocks(
        policy["declared_at"],
        pa["durable_ack"],
        binding["read_started_at"],
        binding["read_completed_at"],
        ba["durable_ack"],
        result["subscription_sent_at"],
        result["ended_at"],
        result["socket_window_available_at"],
    )
    rows = events(root)
    intent = next(v for v in rows if v["kind"] == "subscription_intent")
    raw = (root / f"event_{intent['ordinal']:06d}.bin").read_bytes()
    assert json.loads(raw) == {"assets_ids": ["1"], "type": "market"}
    for row in rows:
        _, ack = _pair(root, f"event_{row['ordinal']:06d}")
        assert _ordered_clocks(row["observed_at"], row["recorded_at"], ack["durable_ack"])
    assert [v["wire_type"] for v in rows if v["kind"] == "received"] == ["text", "binary", "text"]
    saved = snapshot(root)
    assert read_socket_window(root) == result
    assert snapshot(root) == saved and before == (snapshot(source), snapshot(computation))
    with pytest.raises(FileExistsError):
        await capture(computation, tmp_path)


async def test_fixed_ten_second_ping_and_exact_pong(tmp_path):
    _, computation = await pre(tmp_path)
    seen = []

    async def handler(socket):
        seen.append(await socket.recv())
        seen.append(await socket.recv())
        await socket.send("PONG")
        await socket.wait_closed()

    result = await capture(computation, tmp_path, handler, duration=10500)
    assert result["state"] == "duration_completed" and result["ping_count"] == 1
    assert seen[1] == "PING"
    assert any(p.read_bytes() == b"PONG" for p in output(tmp_path).glob("event_*.bin"))


@pytest.mark.parametrize(
    "closed,policy", [(True, WindowBindingPolicy(60000, 60000)), (False, WindowBindingPolicy(0, 0))]
)
async def test_closed_and_stale_prebinding_never_opens_socket(tmp_path, closed, policy):
    _, computation = await pre(tmp_path, closed=closed)
    seen = []

    async def handler(socket):
        seen.append(True)

    if closed:
        with pytest.raises(ValueError, match="observed"):
            await capture(computation, tmp_path, handler, policy=policy)
        assert (output(tmp_path) / "socket_window_failure_ack.json").exists()
    else:
        result = await capture(computation, tmp_path, handler, policy=policy)
        assert result["terminal"] == "refused" and result["close_state"] == "not_connected"
    assert not seen


async def test_synthetic_source_cannot_enter_public_socket_path(tmp_path):
    _, computation = await pre(tmp_path)
    result = await capture_market_socket(
        computation,
        output_root=output(tmp_path),
        policy=WindowBindingPolicy(60000, 60000),
        duration_ms=1,
    )
    assert result["terminal"] == "refused" and result["provenance_class"] == "synthetic"
    assert not result["source_provenance_compatible"]
    assert events(output(tmp_path))[0]["reason"] == "provenance_mismatch"
    assert result["frame_count"] == 0 and result["subscription_sent_at"] is None
    assert not result["source_admitted"]


async def test_freshness_rechecked_after_intent_durability_before_actual_send(
    tmp_path, monkeypatch
):
    _, computation = await pre(tmp_path)
    original = Path.open

    def delay(path, *args, **kwargs):
        if path.name == "event_000003_ack.json" and args and args[0] == "xb":
            time.sleep(10.1)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", delay)
    received = []

    async def handler(socket):
        async for message in socket:
            received.append(message)

    result = await capture(computation, tmp_path, handler, policy=WindowBindingPolicy(10000, 10000))
    assert not received
    assert result["terminal"] == "refused" and result["subscription_sent_at"] is None
    assert events(output(tmp_path))[3]["reason"] == "identity_expired_before_subscription"


@pytest.mark.parametrize("oversized", [True, False])
async def test_transport_rejection_preserves_unavailable_bytes_and_close_codes(tmp_path, oversized):
    _, computation = await pre(tmp_path)

    async def handler(socket):
        await socket.recv()
        if oversized:
            await socket.send(b"x" * (262144 + 1))
            await socket.wait_closed()
        else:
            await socket.close(code=1011)

    result = await capture(computation, tmp_path, handler, duration=1000)
    assert result["state"] == "incomplete" and result["terminal"] == "receive_error"
    row = next(v for v in events(output(tmp_path)) if v["kind"] == "receive_error")
    assert row["raw_state"] == "unavailable" and row["raw_hash"] is None
    assert row["received_bytes"] is None
    assert row["error"]["sent_close_code" if oversized else "received_close_code"] == (
        1009 if oversized else 1011
    )
    assert not (output(tmp_path) / f"event_{row['ordinal']:06d}.bin").exists()


async def test_connect_refusal_retained_without_subscription(tmp_path):
    _, computation = await pre(tmp_path)

    async def refuse(connection, request):
        return connection.respond(403, "synthetic refusal")

    async with serve(lambda s: None, "127.0.0.1", 0, process_request=refuse) as server:
        result = await capture_loopback_socket(
            computation,
            output_root=output(tmp_path),
            policy=WindowBindingPolicy(60000, 60000),
            port=server.sockets[0].getsockname()[1],
        )
    assert result["terminal"] == "connect_error" and result["close_state"] == "not_connected"
    assert result["subscription_sent_at"] is None


@pytest.mark.parametrize("change", ["source", "raw", "binding", "clock", "report", "unknown_file"])
async def test_mutation_and_resealed_semantic_changes_refused(tmp_path, change):
    source, computation = await pre(tmp_path)
    await capture(computation, tmp_path)
    root = output(tmp_path)
    if change == "source":
        next(source.glob("*/raw.bin")).write_bytes(b"bad")
    elif change == "raw":
        (root / "event_000005.bin").write_bytes(b"bad")
    elif change == "binding":
        rewrite(
            root, "socket_window_binding", lambda p: p["binding"]["identity"].update(token_id="2")
        )
    elif change == "clock":
        declaration, _ = _pair(root, "socket_window_policy")
        rewrite(root, "event_000005", lambda p: p.update(observed_at=declaration["declared_at"]))
    elif change == "report":
        rewrite(root, "socket_window_report", lambda p: p.update(source_admitted=True))
    else:
        (root / "untracked").write_text("unexpected")
    before = snapshot(root), snapshot(source), snapshot(computation)
    with pytest.raises(ValueError):
        read_socket_window(root)
    assert before == (snapshot(root), snapshot(source), snapshot(computation))


async def test_partial_receipt_ack_and_cancellation_release_socket(tmp_path, monkeypatch):
    source, computation = await pre(tmp_path)
    before = snapshot(source)
    original = Path.open

    def fail(path, *args, **kwargs):
        if path.name == "event_000005_ack.json":
            raise OSError("synthetic disk failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail)
    with pytest.raises(OSError):
        await capture(computation, tmp_path)
    assert (output(tmp_path) / "event_000005.bin").exists()
    assert (output(tmp_path) / "socket_window_failure_ack.json").exists()
    assert not (output(tmp_path) / "socket_window_report.json").exists()
    assert before == snapshot(source)
    monkeypatch.undo()
    entered, closed = asyncio.Event(), asyncio.Event()

    async def quiet(socket):
        await socket.recv()
        entered.set()
        await socket.wait_closed()
        closed.set()

    root = tmp_path / "fs2_socket_window_cancel"
    async with serve(quiet, "127.0.0.1", 0) as server:
        task = asyncio.create_task(
            capture_loopback_socket(
                computation,
                output_root=root,
                policy=WindowBindingPolicy(60000, 60000),
                port=server.sockets[0].getsockname()[1],
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(closed.wait(), 2)
    assert (root / "socket_window_failure_ack.json").exists()


async def test_concurrent_claim_paths_overrides_and_storage_bounds(tmp_path):
    source, computation = await pre(tmp_path)
    results = await asyncio.gather(
        capture(computation, tmp_path), capture(computation, tmp_path), return_exceptions=True
    )
    assert sum(isinstance(r, FileExistsError) for r in results) == 1
    assert sum(isinstance(r, dict) for r in results) == 1
    for parent in (source, computation):
        with pytest.raises(ValueError, match="separate"):
            await capture_loopback_socket(
                computation,
                output_root=parent / "fs2_socket_window_bad",
                policy=WindowBindingPolicy(60000, 60000),
                port=1234,
            )
    for key in ("token_id", "clock", "provenance", "connect_factory", "port"):
        with pytest.raises(TypeError):
            await capture_market_socket(
                computation,
                output_root=output(tmp_path),
                policy=WindowBindingPolicy(60000, 60000),
                **{key: None},
            )
    with pytest.raises(ValueError, match="deadline"):
        check(output(tmp_path), time.monotonic() - 181)
    with pytest.raises(ValueError, match="retained"):
        check(output(tmp_path), time.monotonic(), LIMITS["max_retained_bytes"])


@pytest.mark.parametrize("failure", ["send", "send_timeout", "close"])
async def test_send_and_close_failures_keep_operation_facts(tmp_path, monkeypatch, failure):
    from websockets.asyncio.client import ClientConnection

    _, computation = await pre(tmp_path)

    async def fail(*args, **kwargs):
        if failure == "send_timeout":
            await asyncio.Future()
        raise OSError("synthetic operation failure")

    monkeypatch.setattr(ClientConnection, "close" if failure == "close" else "send", fail)

    async def handler(socket):
        await socket.wait_closed()

    result = await capture(computation, tmp_path, handler)
    assert result["state"] == "incomplete"
    kind = "close_error" if failure == "close" else "subscription_error"
    row = next(v for v in events(output(tmp_path)) if v["kind"] == kind)
    assert row["error"]["exception_type"] == (
        "TimeoutError" if failure == "send_timeout" else "OSError"
    )
    assert _ordered_clocks(row["operation_started_at"], row["observed_at"], row["recorded_at"])
    assert row["raw_state"] == "not_applicable"


@pytest.mark.parametrize("budget", ["raw", "frames"])
async def test_budget_stop_preserves_observed_prefix_or_exact_frame_limit(
    tmp_path, monkeypatch, budget
):
    _, computation = await pre(tmp_path)
    # Reduced synthetic budgets are frozen before collection, never live policy changes.
    monkeypatch.setitem(
        LIMITS, "max_raw_bytes" if budget == "raw" else "max_frames", 1024 if budget == "raw" else 1
    )

    async def handler(socket):
        await socket.recv()
        await socket.send(b"x" * 2048)
        await socket.send(b"next")
        await socket.wait_closed()

    result = await capture(computation, tmp_path, handler)
    assert result["terminal"] == "budget_stop" and result["frame_count"] == 1
    row = next(v for v in events(output(tmp_path)) if v["kind"] == "received")
    assert row["received_bytes"] == 2048
    assert row["truncated"] == (budget == "raw")
    if budget == "raw":
        assert row["raw_bytes"] < 1024
        assert row["received_hash"] != row["raw_hash"]
        assert result["retained_raw_bytes"] == 1024
