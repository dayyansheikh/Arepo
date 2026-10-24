"""Verified loopback coverage and separately requested endpoint facts retain their provenance."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel import socket_analysis as module
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.socket_analysis import read_socket_analysis, record_socket_analysis
from astrolabe.research_panel.socket_window import capture_market_socket
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
from tests.unit.test_research_panel_bound_window import pre
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_socket_window import capture
from tests.unit.test_research_panel_socket_window import output as socket_output
from tests.unit.test_research_panel_window_coverage import book
from tests.unit.test_research_panel_window_reconciliation import post


def output(tmp_path):
    return tmp_path.resolve() / "fs2_socket_analysis_test"


def record(tmp_path, post_root=None, **kwargs):
    return record_socket_analysis(
        socket_output(tmp_path),
        post_root=post_root,
        output_root=output(tmp_path),
        policy=WindowReconciliationPolicy(60000, 60000, 1000),
        **kwargs,
    )


async def setup(tmp_path, **kwargs):
    source, computation = await pre(tmp_path)

    # Only a valid book in this test window: no invalid/binary tail from the driver fixture.
    async def handler(socket):
        await socket.recv()
        await socket.send(json.dumps(book()))
        await socket.wait_closed()

    await capture(computation, tmp_path, handler)
    post_source, post_root = await post(tmp_path, **kwargs)
    return source, computation, post_source, post_root


async def test_actual_read_calculation_availability_and_exact_coverage(tmp_path):
    deps = await setup(tmp_path)
    before = tuple(snapshot(p) for p in (*deps, socket_output(tmp_path)))
    result = record(tmp_path, deps[-1])
    facts, fa = _pair(output(tmp_path), "socket_analysis_facts")
    saved, ia = _pair(output(tmp_path), "socket_analysis_input")
    policy, pa = _pair(output(tmp_path), "socket_analysis_policy")
    assert _ordered_clocks(
        policy["declared_at"],
        pa["durable_ack"],
        saved["read_started_at"],
        saved["read_completed_at"],
        ia["durable_ack"],
        facts["computation_started_at"],
        facts["computed_at"],
        fa["durable_ack"],
    )
    projection = facts["projection"]
    assert projection["coverage"]["covered_mean_imbalance"]["denominator"] == "3"
    assert projection["coverage"]["covered_mean_imbalance"]["numerator"] == "1"
    assert int(projection["coverage"]["uncovered_duration_ns"]) > 0
    assert projection["reconciliation"]["end_comparison"]["state"] == "agreement"
    assert projection["provenance_class"] == "synthetic"
    assert not projection["source_admitted"] and not result["origin_admitted"]
    assert not projection["coverage"]["complete_continuous_history"]
    stored = snapshot(output(tmp_path))
    assert read_socket_analysis(output(tmp_path)) == result
    assert stored == snapshot(output(tmp_path))
    assert before == tuple(snapshot(p) for p in (*deps, socket_output(tmp_path)))
    with pytest.raises(FileExistsError):
        record(tmp_path, deps[-1])


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"rules": "Different rules"}, "post_identity_or_rules_changed_or_unavailable"),
        ({"closed": True}, "post_market_closed"),
        ({"gamma_status": 503}, "post_gamma.market_source_error"),
        ({"book_status": 429}, "post_clob.book_rate_limited"),
    ],
)
async def test_invalid_post_evidence_does_not_repair_window_or_mapping(tmp_path, kwargs, reason):
    deps = await setup(tmp_path, **kwargs)
    record(tmp_path, deps[-1])
    facts, _ = _pair(output(tmp_path), "socket_analysis_facts")
    result = facts["projection"]["reconciliation"]
    assert result["state"] == "unavailable" and reason in result["reasons"]
    assert result["end_comparison"]["right"] is None


async def test_disagreement_and_absent_post_are_separate_diagnostics(tmp_path):
    deps = await setup(tmp_path, bid="3")
    record(tmp_path, deps[-1])
    facts, _ = _pair(output(tmp_path), "socket_analysis_facts")
    assert facts["projection"]["reconciliation"]["end_comparison"]["state"] == "disagreement"
    root = tmp_path / "fs2_socket_analysis_missing_post"
    record_socket_analysis(
        socket_output(tmp_path),
        output_root=root,
        policy=WindowReconciliationPolicy(60000, 60000, 1000),
    )
    facts, _ = _pair(root, "socket_analysis_facts")
    assert "post_source_pair_unavailable" in facts["projection"]["reconciliation"]["reasons"]


async def test_early_request_and_no_subscription_never_create_eligible_endpoint(tmp_path):
    _, computation = await pre(tmp_path)
    _, post_root = await post(tmp_path)
    await capture(computation, tmp_path)
    record(tmp_path, post_root)
    facts, _ = _pair(output(tmp_path), "socket_analysis_facts")
    assert "post_request_not_after_bound_ack" in facts["projection"]["reconciliation"]["reasons"]
    refused = tmp_path / "fs2_socket_window_refused"
    await capture_market_socket(
        computation, output_root=refused, policy=WindowBindingPolicy(60000, 60000), duration_ms=1
    )
    root = tmp_path / "fs2_socket_analysis_refused"
    report = record_socket_analysis(
        refused, output_root=root, policy=WindowReconciliationPolicy(60000, 60000, 1000)
    )
    assert report["state"] == "no_subscribed_window"
    facts, _ = _pair(root, "socket_analysis_facts")
    assert facts["projection"]["coverage"] is facts["projection"]["reconciliation"] is None
    assert facts["projection"]["provenance_class"] == "synthetic"


@pytest.mark.parametrize("change", ["raw", "clock", "projection", "provenance"])
async def test_dependency_and_resealed_facts_corruption_refused(tmp_path, change):
    deps = await setup(tmp_path)
    record(tmp_path, deps[-1])
    if change == "raw":
        (socket_output(tmp_path) / "event_000005.bin").write_bytes(b"bad")
    elif change == "clock":
        policy, _ = _pair(output(tmp_path), "socket_analysis_policy")
        rewrite(
            output(tmp_path),
            "socket_analysis_facts",
            lambda p: p.update(computed_at=policy["declared_at"]),
        )
    elif change == "provenance":
        rewrite(
            output(tmp_path),
            "socket_analysis_facts",
            lambda p: p["projection"].update(provenance_class="prospective"),
        )
    else:
        rewrite(
            output(tmp_path),
            "socket_analysis_facts",
            lambda p: p["projection"]["coverage"]["covered_mean_imbalance"].update(numerator="7"),
        )
    before = snapshot(output(tmp_path)), snapshot(socket_output(tmp_path))
    with pytest.raises(ValueError):
        read_socket_analysis(output(tmp_path))
    assert before == (snapshot(output(tmp_path)), snapshot(socket_output(tmp_path)))


async def test_transitive_paths_partial_persistence_and_cancellation(tmp_path, monkeypatch):
    deps = await setup(tmp_path)
    for parent in (*deps, socket_output(tmp_path)):
        with pytest.raises(ValueError, match="separate"):
            record_socket_analysis(
                socket_output(tmp_path),
                post_root=deps[-1],
                output_root=parent / "fs2_socket_analysis_nested",
                policy=WindowReconciliationPolicy(60000, 60000, 1000),
            )
    original = Path.open

    def cancel(path, *args, **kwargs):
        if path.name == "socket_analysis_input_ack.json":
            raise asyncio.CancelledError()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", cancel)
    with pytest.raises(asyncio.CancelledError):
        record(tmp_path, deps[-1])
    assert (output(tmp_path) / "socket_analysis_input.json").exists()
    assert (output(tmp_path) / "socket_analysis_failure_ack.json").exists()
    with pytest.raises(ValueError, match="closure"):
        read_socket_analysis(output(tmp_path))


@pytest.mark.parametrize("limit", ["disk", "max_artifact_bytes", "max_output_bytes", "max_seconds"])
async def test_resource_refusal_preserves_terminal_partial_state(tmp_path, monkeypatch, limit):
    deps = await setup(tmp_path)
    before = tuple(snapshot(p) for p in (*deps, socket_output(tmp_path)))
    if limit == "disk":
        monkeypatch.setattr(module.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    else:
        monkeypatch.setitem(module.LIMITS, limit, 0)
    with pytest.raises(ValueError):
        record(tmp_path, deps[-1])
    if limit == "disk":
        assert not output(tmp_path).exists()
    else:
        assert (output(tmp_path) / "socket_analysis_failure_ack.json").exists()
        with pytest.raises(ValueError):
            read_socket_analysis(output(tmp_path))
    assert before == tuple(snapshot(p) for p in (*deps, socket_output(tmp_path)))


async def test_concurrent_writers_have_one_immutable_winner(tmp_path):
    deps = await setup(tmp_path)

    def attempt():
        try:
            return record(tmp_path, deps[-1])
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    (winner,) = [r for r in results if r is not None]
    assert read_socket_analysis(output(tmp_path)) == winner


async def test_early_close_never_invents_a_terminal_book(tmp_path):
    _, computation = await pre(tmp_path)

    async def handler(socket):
        await socket.recv()
        await socket.send(json.dumps(book()))
        await socket.close()

    await capture(computation, tmp_path, handler, duration=1000)
    _, post_root = await post(tmp_path)
    record(tmp_path, post_root)
    facts, _ = _pair(output(tmp_path), "socket_analysis_facts")
    result = facts["projection"]
    assert result["coverage"]["end_imbalance"] is None
    assert int(result["coverage"]["uncovered_duration_ns"]) > 0
    assert "window_end_unavailable" in result["reconciliation"]["reasons"]
