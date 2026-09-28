"""Finite synthetic acquisition, source failures, parallel bounds and raw-backed recovery."""

import asyncio
import json
import threading
from dataclasses import replace

import httpx
import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import screening_worker as worker
from astrolabe.research_panel.panel_declaration import declare_panel, read_panel_declaration
from astrolabe.research_panel.panel_selection import create_panel_selection
from astrolabe.research_panel.screening import ScreeningPolicy, read_screening
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import frame

original_code = _original_code


async def prepared(tmp_path, code, **changes):
    rows = [market(i, description="Rules", archived=False, acceptingOrders=True) for i in (1, 2)]
    source = await frame(tmp_path, rows)
    panel = tmp_path / "fs2_panel_worker"
    p = protocol(
        cycles=1,
        target_attempts=1,
        scheduled_per_stratum=2,
        controls_per_trigger=1,
        source_run_retained_bytes=4 * 1048576,
        **changes,
    )
    declare_panel(
        source,
        implementation_commit=code[1],
        output_root=panel,
        protocol=p,
        strata_limit=1,
        storage_profile="compact-v1",
    )
    create_panel_selection(panel, repository=code[0])
    return source, panel, rows


def mock(rows, *, status=200, all_positive=False, changed=False):
    by_id = {r["id"]: r for r in rows}
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in rows}
    calls = {"active": 0, "peak": 0, "requests": []}

    async def handle(request):
        calls["active"] += 1
        calls["peak"] = max(calls["peak"], calls["active"])
        calls["requests"].append(str(request.url))
        try:
            await asyncio.sleep(0.02)
            gamma = request.url.path.startswith("/markets/")
            if gamma:
                data = dict(by_id[request.url.path.split("/")[-1]])
                if changed:
                    data["description"] = "Changed rules"
            else:
                token = request.url.params["token_id"]
                row = by_token[token]
                data = {
                    "market": row["conditionId"],
                    "asset_id": token,
                    "bids": [
                        {"price": "0.4", "size": "2" if all_positive or row["id"] == "1" else "1"}
                    ],
                    "asks": [{"price": "0.6", "size": "1"}],
                    "timestamp": "1",
                }
            return httpx.Response(
                status if gamma else 200, stream=Stream([json.dumps(data).encode()])
            )
        finally:
            calls["active"] -= 1

    return httpx.MockTransport(handle), calls


async def run(panel, code, transport, **changes):
    return await worker.run_synthetic_screening(
        panel,
        implementation_commit=code[1],
        repository=code[0],
        transport=transport,
        rule=SnapshotTriggerPolicy(1, 3, 60000),
        freshness=ScreeningPolicy(60, 60),
        **changes,
    )


async def test_complete_owned_parallel_sources_exact_controls_and_original_recovery(
    tmp_path, original_code
):
    source, panel, rows = await prepared(tmp_path, original_code)
    transport, calls = mock(rows)
    before = snapshot(source), snapshot(panel)
    result = await run(panel, original_code, transport, concurrency=2)
    root = worker.worker_root(panel)
    assert result["state"] == "screening_complete"
    assert result["screening"]["provenance_class"] == "synthetic"
    assert result["role_capacity"]["counts_per_cycle"] == {
        "scheduled": 2,
        "triggered": 1,
        "control": 1,
    }
    assert result["role_capacity"]["fits"] and not result["origin_admitted"]
    assert len(result["recovery"]) == 1
    assert calls["peak"] == 2 and len(calls["requests"]) == 4
    policy, ack = _pair(root, "worker_policy")
    assert policy["reservation"] == worker.allocation(read_panel_declaration(panel))
    for intent_file in root.glob("intent_*.json"):
        if intent_file.name.endswith("_ack.json"):
            continue
        intent, ia = _pair(root, intent_file.stem)
        assert ack["durable_ack"]["utc"] <= intent["at"]["utc"] <= ia["durable_ack"]["utc"]
    assert read_screening(root / "fs2_screening_batch") == result["screening"]
    assert before == (snapshot(source), snapshot(panel))
    saved = snapshot(root)
    with pytest.raises(FileExistsError):
        await run(panel, original_code, transport)
    assert saved == snapshot(root) and len(calls["requests"]) == 4


@pytest.mark.parametrize("options", [{"status": 503}, {"changed": True}])
async def test_failed_or_changed_source_never_becomes_negative_or_replaced(
    tmp_path, original_code, options
):
    _, panel, rows = await prepared(tmp_path, original_code)
    transport, calls = mock(rows, **options)
    result = await run(panel, original_code, transport, concurrency=1)
    assert calls["peak"] == 1 and len(calls["requests"]) == 4
    assert result["role_capacity"]["counts_per_cycle"] == {"scheduled": 2}
    assert all(
        r["assessment_state"] == "unavailable" for r in result["screening"]["plan"]["assignments"]
    )
    assert not result["accepted_panel"]


async def test_role_overflow_is_retained_without_truncation_or_activation(tmp_path, original_code):
    _, panel, rows = await prepared(tmp_path, original_code, triggered_slots=0)
    transport, _ = mock(rows, all_positive=True)
    result = await run(panel, original_code, transport)
    assert result["state"] == "blocked_role_capacity"
    assert result["role_capacity"]["counts_per_cycle"]["triggered"] == 1
    assert not result["role_capacity"]["fits"] and not result["origin_admitted"]
    assert not list(tmp_path.glob("fs2_activation_*"))


async def test_full_capacity_fails_before_any_requests_or_new_journal(
    tmp_path, original_code, monkeypatch
):
    _, panel, rows = await prepared(tmp_path, original_code)
    transport, calls = mock(rows)
    needed = worker.allocation(read_panel_declaration(panel))["required_free_bytes"]
    monkeypatch.setattr(
        worker.shutil,
        "disk_usage",
        lambda _: worker.shutil._ntuple_diskusage(needed, 1, needed - 1),
    )
    with pytest.raises(ValueError, match="full screening/source/recovery/runtime"):
        await run(panel, original_code, transport)
    assert calls["requests"] == [] and not worker.worker_root(panel).exists()


async def test_changed_commit_refused_before_requests(tmp_path, original_code):
    _, panel, rows = await prepared(tmp_path, original_code)
    transport, calls = mock(rows)
    with pytest.raises(ValueError):
        await run(panel, (original_code[0], "f" * 40), transport)
    assert not calls["requests"] and not worker.worker_root(panel).exists()


@pytest.mark.parametrize("concurrency", [0, True, 9])
async def test_invalid_concurrency_does_not_start(concurrency, tmp_path):
    with pytest.raises(ValueError, match="bounded concurrency"):
        await run(
            tmp_path / "fs2_panel_missing",
            (tmp_path, "a" * 40),
            httpx.MockTransport(lambda r: None),
            concurrency=concurrency,
        )


async def test_live_transport_is_not_enabled(tmp_path):
    with pytest.raises(ValueError, match="explicit synthetic"):
        await run(tmp_path / "fs2_panel_missing", (tmp_path, "a" * 40), None)


async def test_failed_acquisition_retains_raw_failure_and_does_not_retry(tmp_path, original_code):
    _, panel, _ = await prepared(tmp_path, original_code)
    calls = []

    def oversized(request):
        calls.append(str(request.url))
        return httpx.Response(200, stream=Stream([b"x" * (262144 + 1)]))

    result = await run(panel, original_code, httpx.MockTransport(oversized), concurrency=1)
    root = worker.worker_root(panel)
    assert len(calls) == len(set(calls)) == 4
    assert result["role_capacity"]["counts_per_cycle"] == {"scheduled": 2}
    assert all(
        r["assessment_state"] == "unavailable" for r in result["screening"]["plan"]["assignments"]
    )
    assert list(root.glob("fs2_capture_*/*/raw.bin"))


async def test_computation_failure_retains_evidence_and_cancels_without_detached_writers(
    tmp_path, original_code, monkeypatch
):
    _, panel, rows = await prepared(tmp_path, original_code)
    transport, calls = mock(rows)

    def refuse(*args, **kwargs):
        raise OSError("synthetic computation storage refusal")

    monkeypatch.setattr(worker, "record_book_computation", refuse)
    with pytest.raises(ExceptionGroup):
        await run(panel, original_code, transport, concurrency=1)
    root = worker.worker_root(panel)
    assert (root / "worker_failure_ack.json").exists()
    assert not (root / "worker_report.json").exists()
    saved = snapshot(root)
    await asyncio.sleep(0.05)
    assert saved == snapshot(root)
    assert 2 <= len(calls["requests"]) <= 4
    assert list(root.glob("fs2_capture_*/*/raw.bin"))


async def test_cancellation_waits_for_durable_thread_before_returning():
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def operation():
        started.set()
        release.wait(timeout=5)
        finished.set()

    task = asyncio.create_task(worker._durable_call(operation))
    await asyncio.to_thread(started.wait, 5)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()


def test_allocation_accounts_for_screening_and_entire_future_runtime():
    from astrolabe.research_panel.panel_declaration import reservation

    p = protocol(cycles=2, target_attempts=2, scheduled_slots=4, scheduled_per_stratum=2)
    declaration = {"reservation": reservation(p, storage_profile="compact-v1")}
    result = worker.allocation(declaration)
    assert result["screen_slots"] == 4
    assert (
        result["future_runtime_retained_bytes"] > declaration["reservation"]["total_retained_bytes"]
    )
    expected_screens = (
        4
        * (
            p.source_run_retained_bytes
            + worker.BOOK_LIMITS["max_output_bytes"]
            + worker.PER_DECISION_BYTES
        )
        + worker.SCREEN_LIMITS["max_output_bytes"]
        + worker.LIMITS["worker_metadata_bytes"]
        + worker.LIMITS["original_read_bytes"]
    )
    assert result["screening_retained_bytes"] == expected_screens
    assert result["required_free_bytes"] == (
        result["total_retained_bytes"] + worker.LIMITS["free_reserve_bytes"]
    )
    assert not result["overlap_discount_applied"]
    # More cycles/targets add future costs rather than discounting observed role overlap.
    larger = {"reservation": reservation(replace(p, cycles=3), storage_profile="compact-v1")}
    assert worker.allocation(larger)["required_free_bytes"] > result["required_free_bytes"]


async def test_public_entry_rejects_synthetic_lineage_before_source_creation(
    tmp_path, original_code, monkeypatch
):
    source, panel, _ = await prepared(tmp_path, original_code)
    before = snapshot(source), snapshot(panel)

    def forbidden(*args, **kwargs):
        pytest.fail("public source constructed for synthetic assignments")

    monkeypatch.setattr(worker, "SourceRun", forbidden)
    with pytest.raises(ValueError, match="provenance"):
        await worker.run_public_screening(
            panel, implementation_commit=original_code[1], repository=original_code[0],
            rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(60, 60))
    root = worker.worker_root(panel)
    policy, _ = _pair(root, "worker_policy")
    assert policy["schema_version"] == worker.PUBLIC_VERSION
    assert policy["provenance_class"] == "prospective"
    assert policy["live_collection_enabled"]
    assert not list(root.glob("fs2_capture_*"))
    assert (root / "worker_failure.json").exists()
    assert before == (snapshot(source), snapshot(panel))


async def test_public_api_cannot_accept_injected_transport_or_provenance(tmp_path):
    kwargs = dict(implementation_commit="a" * 40, rule=SnapshotTriggerPolicy(1, 3, 60000),
                  freshness=ScreeningPolicy(60, 60))
    for override in ({"transport": httpx.MockTransport(lambda _: None)},
                     {"provenance": "prospective"}):
        with pytest.raises(TypeError):
            await worker.run_public_screening(tmp_path / "fs2_panel_public", **kwargs, **override)
    assert not list(tmp_path.iterdir())
