"""Bounded parallel synthetic jobs with exact replay; not empirical timing evidence."""

import asyncio
import threading
from collections import Counter
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import concurrent_runtime as concurrent
from astrolabe.research_panel import runtime
from astrolabe.research_panel.original_reader import read_original_runtime
from astrolabe.research_panel.panel_declaration import declare_panel
from astrolabe.research_panel.panel_selection import create_panel_selection, selection_root
from astrolabe.research_panel.screening import ScreeningPolicy, declare_screening, finish_screening
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


async def setup(tmp_path, code, count=1):
    source = await frame(tmp_path, [market(i) for i in range(1, count + 1)])
    panel = tmp_path / "fs2_panel_concurrent"
    declare_panel(
        source,
        implementation_commit=code[1],
        output_root=panel,
        protocol=protocol(
            cycles=1,
            target_attempts=1,
            scheduled_slots=count,
            scheduled_per_stratum=count,
            triggered_slots=0,
            cadence_seconds=30,
            max_origin_delay_seconds=20,
            max_origin_save_seconds=1,
            horizon_seconds=2,
            tolerance_seconds=1,
            source_response_bytes=65536,
            source_run_retained_bytes=1048576,
        ),
        storage_profile="compact-v1",
        strata_limit=1,
    )
    create_panel_selection(panel, repository=code[0])
    screen = tmp_path / "fs2_screening_concurrent"
    declare_screening(
        selection_root(panel),
        output_root=screen,
        rule=SnapshotTriggerPolicy(1, 3, 60000),
        policy=ScreeningPolicy(60, 60),
    )
    finish_screening(screen)  # explicit scheduled-only sample; no inferred negative controls
    return panel, screen


def transport(*, slow_market=None, cancel=False):
    calls = Counter()
    lock = threading.Lock()
    counts = {"active": 0, "peak": 0}

    async def handler(request):
        key = request.url.path
        with lock:
            calls[key] += 1
            attempt = calls[key]
            counts["active"] += 1
            counts["peak"] = max(counts["peak"], counts["active"])
        try:
            if cancel:
                raise asyncio.CancelledError()
            await asyncio.sleep(
                3.1
                if slow_market is not None and key == f"/markets/{slow_market}" and attempt == 1
                else 0.02
            )
            if key.startswith("/markets/"):
                body = market(int(key.split("/")[-1]), archived=False, acceptingOrders=True)
            elif key == "/book":
                token = request.url.params["token_id"]
                body = {
                    "asset_id": token,
                    "market": "0x" + f"{int(token) // 2:064x}",
                    "bids": [{"price": "0.4", "size": "1"}],
                    "asks": [{"price": "0.6", "size": "1"}],
                }
            else:
                body = {"data": [], "pagination": {"has_more": False, "next_cursor": None}}
            return httpx.Response(200, stream=Stream([_json_bytes(body)]))
        finally:
            with lock:
                counts["active"] -= 1

    return httpx.MockTransport(handler), counts


def test_ready_target_precedes_overdue_origin_and_reserved_capacity_is_exact():
    at = datetime(2026, 9, 27, tzinfo=UTC)
    origin = (at - timedelta(seconds=10), 1, "a", "origin", {})
    target = (at, 0, "z", "target", {})
    future = (at + timedelta(microseconds=1), 0, "future", "target", {})
    assert concurrent._ready([origin, target, future], {}, 2, at) == target
    assert concurrent._ready([origin, future], {}, 2, at) == origin
    active = {"busy": (at, 1, "busy", "origin", {})}
    assert concurrent._ready([origin], active, 2, at) is None
    assert concurrent._ready([origin, target], active, 2, at) == target
    active["target"] = target
    assert concurrent._ready([origin, target], active, 2, at) is None


async def test_delayed_origin_cannot_starve_due_target_and_original_replay(tmp_path, original_code):
    panel, screen = await setup(tmp_path, original_code, count=3)
    _, declaration_ack = _pair(panel, "panel_policy")
    order = sorted(
        range(1, 4),
        key=lambda i: content_hash(
            {
                "panel_declaration_hash": declaration_ack["payload_hash"],
                "cycle": 0,
                "market_id": str(i),
                "token_id": str(2 * i),
            }
        ),
    )
    slow_market = str(order[1])
    mock, counts = transport(slow_market=slow_market)
    report = await runtime.exercise_screened_panel(panel, screen, transport=mock, concurrency=2)
    assert counts["peak"] == 2
    assert len(report["origins"]) == len(report["outcomes"]) == 3
    assert {o["state"] for o in report["outcomes"]} == {"observed"}
    root = runtime.run_root(panel)
    origins = {item["intent_id"]: item for item in report["origins"]}
    slow = next(
        p.parent.name
        for p in (root / "origins").glob("*/origin_intent.json")
        if _pair(p.parent, "origin_intent")[0]["member"]["market_id"] == slow_market
    )
    slow_end = next(
        e["at"] for e in report["events"] if e["id"] == slow and e["event"] == "completed"
    )
    first_target = next(
        e for e in report["events"] if e["kind"] == "target" and e["event"] == "dispatched"
    )
    assert _time(first_target["at"]) < _time(slow_end)
    assert len(origins) == 3
    before = snapshot(root), snapshot(screen)
    assert runtime.read_runtime(panel) == report
    read = read_original_runtime(
        root,
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_runtime_read_concurrent",
    )
    assert read["report"] == report
    assert before == (snapshot(root), snapshot(screen))
    with pytest.raises(ValueError, match="separate"):
        read_original_runtime(
            root,
            implementation_commit=original_code[1],
            repository=original_code[0],
            output_root=screen / "fs2_runtime_read_bad",
        )
    with pytest.raises(FileExistsError):
        await runtime.exercise_screened_panel(panel, screen, transport=mock, concurrency=2)


@pytest.mark.parametrize(
    "change", ["completion_first", "future_dispatch", "concurrency", "outcome", "raw"]
)
async def test_dispatch_capacity_clock_and_outcome_tampering_refused(
    tmp_path, original_code, change
):
    panel, screen = await setup(tmp_path, original_code)
    mock, _ = transport()
    await runtime.exercise_screened_panel(panel, screen, transport=mock, concurrency=2)
    root = runtime.run_root(panel)
    if change == "completion_first":
        amend(root, "runtime_report", lambda p: p["events"][0].update(event="completed"))
    elif change == "future_dispatch":
        amend(
            root,
            "runtime_report",
            lambda p: p["events"][0]["at"].update(utc="2099-01-01T00:00:00Z"),
        )
    elif change == "concurrency":
        amend(root, "runtime_policy", lambda p: p.update(concurrency=1))
    elif change == "outcome":
        amend(root, "runtime_report", lambda p: p["outcomes"][0].update(midpoint_change="0.9"))
    else:
        next(root.glob("origins/*/fs2_capture_origin/*/raw.bin")).write_bytes(b"corrupt fixture")
    with pytest.raises(ValueError):
        runtime.read_runtime(panel)


async def test_cancellation_drains_jobs_and_preserves_terminal_failure(tmp_path, original_code):
    panel, screen = await setup(tmp_path, original_code, count=2)
    mock, _ = transport(cancel=True)
    with pytest.raises(asyncio.CancelledError):
        await runtime.exercise_screened_panel(panel, screen, transport=mock, concurrency=3)
    root = runtime.run_root(panel)
    assert (root / "runtime_failure_ack.json").exists()
    assert not (root / "runtime_report.json").exists()
    before = snapshot(root)
    await asyncio.sleep(0.05)
    assert before == snapshot(root)


@pytest.mark.parametrize("concurrency", [1, True, 9])
async def test_invalid_parallel_bound_refuses_before_writes(tmp_path, concurrency):
    mock, _ = transport()
    with pytest.raises(ValueError, match="bounded concurrency"):
        await runtime.exercise_screened_panel(
            tmp_path / "fs2_panel_absent",
            tmp_path / "screen",
            transport=mock,
            concurrency=concurrency,
        )


async def test_live_transport_remains_disabled(tmp_path):
    with pytest.raises(ValueError, match="explicit synthetic"):
        await runtime.exercise_screened_panel(
            tmp_path / "fs2_panel_absent", tmp_path / "screen", transport=None
        )
