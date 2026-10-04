"""Synthetic due collection preserves schedules, identity and failed earlier evidence."""

import asyncio
import shutil
import time
from datetime import timedelta

import httpx
import pytest

from astrolabe.feature_store.capture import _clock, _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import due_worker
from astrolabe.research_panel.due_worker import exercise_targets, read_target_run, run_root
from astrolabe.research_panel.origin_worker import exercise_origins
from astrolabe.research_panel.panel_declaration import declare_panel
from astrolabe.research_panel.panel_selection import create_panel_selection
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_origin_worker import only_origin
from tests.unit.test_research_panel_origin_worker import transport as origin_transport
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


async def setup(tmp_path, original_code, *, attempts=1, origin_status=200, horizon=5, tolerance=4):
    source = await frame(tmp_path, [market(1)])
    panel = tmp_path / "fs2_panel_due"
    declare_panel(
        source,
        implementation_commit=original_code[1],
        output_root=panel,
        protocol=protocol(
            cycles=1,
            target_attempts=attempts,
            scheduled_slots=1,
            triggered_slots=0,
            max_origin_save_seconds=1,
            horizon_seconds=horizon,
            tolerance_seconds=tolerance,
            source_response_bytes=65536,
            source_run_retained_bytes=1048576,
        ),
        storage_profile="compact-v1",
    )
    create_panel_selection(panel, repository=original_code[0])
    origins = await exercise_origins(
        panel, transport=origin_transport(panel, [], book_status=origin_status)
    )
    return panel, origins


def transport(panel, calls, *, changed=False, closed=False, status=200, cancel=False):
    async def handler(request):
        facts, _ = _pair(only_origin(panel), "origin_facts")
        _, ack = _pair(only_origin(panel), "origin_receipt")
        now = _time(_clock())
        policy, _ = _pair(panel, "panel_policy")
        assert now >= _time(facts["origin_at"]) + timedelta(
            seconds=policy["protocol"]["horizon_seconds"]
        )
        assert now > _time(ack["durable_ack"])
        calls.append((request.url.path, dict(request.url.params)))
        if cancel:
            raise asyncio.CancelledError()
        if request.url.path == "/markets/1":
            body = market(1, active=True, closed=closed, archived=False, acceptingOrders=True)
            if changed:
                body["description"] = "changed target rules"
            code = 200
        else:
            assert request.url.path == "/book"
            body = {
                "asset_id": "2",
                "market": "0x" + f"{1:064x}",
                "bids": [{"price": "0.50", "size": "3.0"}],
                "asks": [{"price": "0.70", "size": "5.0"}],
            }
            code = status
        return httpx.Response(code, stream=Stream([_json_bytes(body)]))

    return httpx.MockTransport(handler)


def attempt_roots(panel):
    return sorted(p for p in run_root(panel).iterdir() if p.is_dir())


async def test_due_after_durable_origin_exact_delta_and_read_only_replay(tmp_path, original_code):
    panel, origins = await setup(tmp_path, original_code)
    before = snapshot(only_origin(panel))
    calls = []
    result = await exercise_targets(panel, transport=transport(panel, calls))
    assert [p for p, _ in calls] == ["/markets/1", "/book"]
    assert calls[1][1] == {"token_id": "2"}
    outcome = result["outcomes"][0]
    assert outcome["state"] == "observed"
    assert outcome["midpoint_change"] == "0.100"
    assert outcome["target"]["selected"]["midpoint"] == "0.60"
    assert outcome["economic_value_claim"] is False
    assert (
        outcome["target"]["selected"]["available_at"]
        == _time(result["attempts"][0]["available_at"]).isoformat()
    )
    assert result["provenance_class"] == "synthetic"
    assert result["accepted_panel"] is result["feature_store_admitted"] is False
    assert result["attempts"][0]["origin_id"] == origins["results"][0]["intent_id"]
    saved = snapshot(run_root(panel))
    assert read_target_run(panel) == result
    assert saved == snapshot(run_root(panel)) and before == snapshot(only_origin(panel))
    with pytest.raises(FileExistsError):
        await exercise_targets(panel, transport=transport(panel, calls))
    assert len(calls) == 2


@pytest.mark.parametrize(
    "kwargs,state,reason",
    [
        ({"changed": True, "closed": True}, "unavailable", "identity_changed_since_origin"),
        ({"closed": True}, "closed", None),
        ({"status": 429}, "unavailable", "rate_limited"),
    ],
)
async def test_identity_closure_and_failure_outcomes(
    tmp_path, original_code, kwargs, state, reason
):
    panel, _ = await setup(tmp_path, original_code)
    result = await exercise_targets(panel, transport=transport(panel, [], **kwargs))
    outcome = result["outcomes"][0]
    assert outcome["state"] == state and outcome["midpoint_change"] is None
    if reason:
        assert outcome["target"]["exclusions"][0]["reason"] == reason
    if state == "closed":
        assert outcome["target"]["censoring_observation_id"] is not None


async def test_ineligible_origin_keeps_all_attempts_without_requests(tmp_path, original_code):
    panel, _ = await setup(tmp_path, original_code, attempts=2, origin_status=429)
    calls = []
    result = await exercise_targets(panel, transport=transport(panel, calls))
    assert not calls
    assert len(result["attempts"]) == 2
    assert {a["state"] for a in result["attempts"]} == {"origin_ineligible"}
    assert result["outcomes"][0]["state"] == "origin_ineligible"


async def test_expired_window_is_not_rescheduled(tmp_path, original_code):
    panel, _ = await setup(tmp_path, original_code, horizon=2, tolerance=1)
    await asyncio.sleep(3.1)
    calls = []
    result = await exercise_targets(panel, transport=transport(panel, calls))
    assert not calls and result["attempts"][0]["state"] == "expired"
    assert result["outcomes"][0]["state"] == "unavailable"


async def test_failed_earlier_computation_blocks_later_valid_target(
    tmp_path, original_code, monkeypatch
):
    panel, _ = await setup(tmp_path, original_code, attempts=2)
    original = due_worker.record_quote_computation
    attempts = []

    def fail_first(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise ValueError("synthetic computation fault after raw capture")
        return original(*args, **kwargs)

    monkeypatch.setattr(due_worker, "record_quote_computation", fail_first)
    calls = []
    result = await exercise_targets(panel, transport=transport(panel, calls))
    assert len(calls) == 4
    assert [a["state"] for a in result["attempts"]] == ["incomplete_evidence", "recorded"]
    outcome = result["outcomes"][0]
    assert outcome["state"] == "incomplete_evidence" and outcome["target"] is None
    assert outcome["blocking_attempt_ids"] == [result["attempts"][0]["attempt_id"]]
    first = run_root(panel) / result["attempts"][0]["attempt_id"]
    assert len(list((first / due_worker.SOURCE).glob("*/raw.bin"))) == 2
    assert read_target_run(panel) == result


async def test_cancelled_worker_preserves_partial_and_refuses_resume(tmp_path, original_code):
    panel, _ = await setup(tmp_path, original_code)
    with pytest.raises(asyncio.CancelledError):
        await exercise_targets(panel, transport=transport(panel, [], cancel=True))
    assert (run_root(panel) / "target_worker_failure_ack.json").exists()
    assert (attempt_roots(panel)[0] / "target_intent_ack.json").exists()
    with pytest.raises(FileExistsError):
        await exercise_targets(panel, transport=transport(panel, []))


@pytest.mark.parametrize("change", ["raw", "delta", "schedule", "adaptation_resealed", "extra"])
async def test_recovery_rejects_changed_source_schedule_or_outcome(tmp_path, original_code, change):
    panel, _ = await setup(tmp_path, original_code)
    await exercise_targets(panel, transport=transport(panel, []))
    child = attempt_roots(panel)[0]
    if change == "raw":
        next((child / due_worker.SOURCE).glob("*/raw.bin")).write_bytes(b"changed")
    elif change == "delta":
        amend(
            run_root(panel), "target_report", lambda p: p["outcomes"][0].update(midpoint_change="9")
        )
    elif change == "schedule":
        amend(run_root(panel), "target_plan", lambda p: p["jobs"][0].update(attempt_index=99))
    elif change == "adaptation_resealed":
        amend(
            child,
            "target_facts",
            lambda p: p["projection"]["adaptation"]["quote"].update(bid="0.99"),
        )
        inventory = due_worker._inventory(child, 10 * 1048576)
        amend(child, "target_receipt", lambda p: p.update(inventory=inventory))
    else:
        (run_root(panel) / "unexpected").write_text("{}")
    with pytest.raises(ValueError):
        read_target_run(panel)


async def test_one_owner_and_read_only_low_disk_recovery(tmp_path, original_code, monkeypatch):
    panel, _ = await setup(tmp_path, original_code)
    calls = []
    results = await asyncio.gather(
        exercise_targets(panel, transport=transport(panel, calls)),
        exercise_targets(panel, transport=transport(panel, calls)),
        return_exceptions=True,
    )
    assert sum(isinstance(r, FileExistsError) for r in results) == 1
    result = next(r for r in results if isinstance(r, dict))
    assert len(calls) == 2
    monkeypatch.setattr(shutil, "disk_usage", lambda p: shutil._ntuple_diskusage(1, 1, 0))
    assert read_target_run(panel) == result


async def test_live_transport_caller_clocks_and_low_capacity_refused(
    tmp_path, original_code, monkeypatch
):
    panel, _ = await setup(tmp_path, original_code)
    with pytest.raises(ValueError, match="synthetic"):
        await exercise_targets(panel, transport=None)
    with pytest.raises(TypeError):
        await exercise_targets(panel, transport=transport(panel, []), clock=None)
    monkeypatch.setattr(shutil, "disk_usage", lambda p: shutil._ntuple_diskusage(1, 1, 0))
    with pytest.raises(ValueError, match="reservation"):
        await exercise_targets(panel, transport=transport(panel, []))
    assert not run_root(panel).exists()


async def test_actual_late_receipt_is_retained_without_rescheduling(
    tmp_path, original_code, monkeypatch
):
    panel, _ = await setup(tmp_path, original_code)
    persist = due_worker._persist

    def delayed_intent(root, name, payload):
        if name == "target_intent":
            time.sleep(0.25)
        return persist(root, name, payload)

    monkeypatch.setattr(due_worker, "_persist", delayed_intent)
    base = transport(panel, [])

    async def late(request):
        if request.url.path == "/book":
            intent, _ = _pair(attempt_roots(panel)[0], "target_intent")
            until = due_worker._at(intent["job"]["deadline_at"]) + timedelta(milliseconds=50)
            await asyncio.sleep(max(0, (until - _time(_clock())).total_seconds()))
        return await base.handle_async_request(request)

    result = await exercise_targets(panel, transport=httpx.MockTransport(late))
    outcome = result["outcomes"][0]
    assert result["attempts"][0]["state"] == "recorded"
    assert outcome["state"] == "unavailable" and outcome["midpoint_change"] is None
    assert outcome["target"]["exclusions"][0]["reason"] == "late"
    assert read_target_run(panel) == result


async def test_actual_adapter_save_delay_is_part_of_target_availability(
    tmp_path, original_code, monkeypatch
):
    panel, _ = await setup(tmp_path, original_code)
    persist = due_worker._persist

    def delayed_facts(root, name, payload):
        if name == "target_facts":
            time.sleep(0.2)
        return persist(root, name, payload)

    monkeypatch.setattr(due_worker, "_persist", delayed_facts)
    result = await exercise_targets(panel, transport=transport(panel, []))
    facts, ack = _pair(attempt_roots(panel)[0], "target_facts")
    earlier = _time(facts["projection"]["computation"]["computation_available_at"])
    actual = due_worker._at(result["outcomes"][0]["target"]["selected"]["available_at"])
    assert actual >= _time(ack["durable_ack"]) > earlier + timedelta(seconds=0.2)
    assert actual == _time(result["attempts"][0]["available_at"])
    assert read_target_run(panel) == result
