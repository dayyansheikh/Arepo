"""Screened-role scheduling is synthetic software validation, never a live pilot."""

from datetime import timedelta

import pytest

from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import activation
from astrolabe.research_panel.activation import (
    activate_panel,
    activate_screened_panel,
    activation_root,
    read_activation,
)
from astrolabe.research_panel.original_reader import read_original_activation
from astrolabe.research_panel.panel_selection import selection_root
from astrolabe.research_panel.screening import ScreeningPolicy, declare_screening, finish_screening
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_research_panel_activation import prepared as legacy_prepared
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_screening import assessed
from tests.unit.test_research_panel_screening_worker import prepared as worker_prepared
from tests.unit.test_research_panel_selection import amend

original_code = _original_code


async def prepared(tmp_path, code, *, unassessed=False, **changes):
    source, panel, rows = await worker_prepared(tmp_path, code, **changes)
    root = tmp_path / "fs2_screening_activation"
    policy = declare_screening(
        selection_root(panel),
        output_root=root,
        rule=SnapshotTriggerPolicy(1, 3, 60000),
        policy=ScreeningPolicy(60, 60),
    )
    if not unassessed:
        await assessed(tmp_path, policy, rows)
    report = finish_screening(root)
    return source, panel, root, report


async def test_exact_roles_deduplicated_schedules_and_original_recovery(tmp_path, original_code):
    source, panel, screen, report = await prepared(tmp_path, original_code)
    saved = snapshot(source), snapshot(panel), snapshot(screen), snapshot(selection_root(panel))
    result = activate_screened_panel(panel, screen)
    assert result["schema_version"] == "fs2-panel-activation-v2"
    assert result["screening_report_hash"] == report["screening_report_hash"]
    assert result["screening_available_at"] == report["screening_available_at"]
    assert result["role_capacity"]["fits"]
    assert result["role_capacity"]["counts_per_cycle"] == {
        "scheduled": 2,
        "triggered": 1,
        "control": 1,
    }
    assert len(result["selected"]) == len(result["slots"]) == 2
    assert len({row["intent_id"] for row in result["slots"]}) == 2
    for member in result["selected"]:
        assert member["roles"] == [
            r for r in report["plan"]["assignments"] if r["market_id"] == member["market_id"]
        ]
        assert member["source_observation_id"] == member["roles"][0]["source_observation_id"]
    facts, ack = _pair(activation_root(panel), "activation_facts")
    assert report["screening_available_at"]["utc"] <= facts["read_started_at"]["utc"]
    assert all(
        _time({"utc": r["scheduled_at"]}) == _time(ack["durable_ack"]) + timedelta(seconds=2)
        for r in result["slots"]
    )
    original = read_original_activation(
        activation_root(panel),
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_activation_read_test",
    )
    assert original["report"] == {"facts": facts, "summary": result}
    assert read_activation(panel) == result
    assert saved == (
        snapshot(source),
        snapshot(panel),
        snapshot(screen),
        snapshot(selection_root(panel)),
    )
    assert not result["origin_admitted"] and not result["accepted_panel"]
    with pytest.raises(FileExistsError):
        activate_screened_panel(panel, screen)


async def test_unassessed_keeps_scheduled_only_without_negative_controls(tmp_path, original_code):
    _, panel, screen, _ = await prepared(tmp_path, original_code, unassessed=True)
    result = activate_screened_panel(panel, screen)
    assert result["role_capacity"]["counts_per_cycle"] == {"scheduled": 2}
    assert all(m["roles"][0]["assessment_state"] == "not_assessed" for m in result["selected"])
    assert read_activation(panel) == result


async def test_role_overflow_preserved_and_refused_before_schedules(tmp_path, original_code):
    _, panel, screen, _ = await prepared(tmp_path, original_code, triggered_slots=0)
    with pytest.raises(ValueError, match="role capacity"):
        activate_screened_panel(panel, screen)
    root = activation_root(panel)
    assert (root / "activation_failure_ack.json").exists()
    assert not (root / "activation_facts.json").exists()


async def test_stale_assessment_at_actual_activation_cutoff_is_not_redrawn(
    tmp_path, original_code, monkeypatch
):
    _, panel, screen, _ = await prepared(tmp_path, original_code)
    prior = snapshot(screen)
    clock = activation._clock
    calls = 0

    def delayed_read():
        nonlocal calls
        value = clock()
        calls += 1
        if calls == 3:  # synthetic delayed read completion, before any activation facts save
            value["utc"] = (_time(value) + timedelta(seconds=61)).isoformat()
            value["monotonic_ns"] = str(int(value["monotonic_ns"]) + 61 * 10**9)
        return value

    monkeypatch.setattr(activation, "_clock", delayed_read)
    with pytest.raises(ValueError, match="stale or future"):
        activate_screened_panel(panel, screen)
    assert snapshot(screen) == prior
    assert not (activation_root(panel) / "activation_facts.json").exists()


async def test_recovery_uses_original_cutoff_not_current_clock_or_disk(
    tmp_path, original_code, monkeypatch
):
    _, panel, screen, _ = await prepared(tmp_path, original_code)
    result = activate_screened_panel(panel, screen)
    monkeypatch.setattr(activation, "_clock", lambda: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(
        activation.shutil, "disk_usage", lambda p: activation.shutil._ntuple_diskusage(1, 1, 0)
    )
    assert read_activation(panel) == result


@pytest.mark.parametrize(
    "change",
    [
        "seed",
        "screen_hash",
        "weight",
        "token",
        "capacity",
        "source",
        "screen_clock",
        "activation_clock",
        "legacy_schema",
    ],
)
async def test_resealed_role_identity_context_or_source_changes_refused(
    tmp_path, original_code, change
):
    _, panel, screen, _ = await prepared(tmp_path, original_code)
    activate_screened_panel(panel, screen)
    root = activation_root(panel)
    if change == "seed":
        amend(root, "activation_facts", lambda p: p.update(screening_seed="0" * 64))
    elif change == "screen_hash":
        amend(root, "activation_facts", lambda p: p.update(screening_report_hash="0" * 64))
    elif change == "weight":
        amend(
            root,
            "activation_facts",
            lambda p: p["selected"][0]["roles"][0]["screening_inclusion_probability"].update(
                numerator="0"
            ),
        )
    elif change == "token":
        amend(root, "activation_facts", lambda p: p["selected"][0].update(token_id="999"))
    elif change == "capacity":
        amend(root, "activation_facts", lambda p: p["role_capacity"].update(fits=False))
    elif change == "source":
        next(tmp_path.glob("fs2_capture_screen_*/*/raw.bin")).write_bytes(b"corrupt fixture")
    elif change == "screen_clock":
        amend(screen, "screening_report", lambda p: p["cutoff"].update(utc="2099-01-01T00:00:00Z"))
    elif change == "activation_clock":
        amend(
            root,
            "activation_facts",
            lambda p: p["read_started_at"].update(utc="2000-01-01T00:00:00Z"),
        )
    else:
        amend(
            root, "activation_policy", lambda p: p.update(schema_version="fs2-panel-activation-v1")
        )
    with pytest.raises(ValueError):
        read_activation(panel)


async def test_foreign_or_missing_screening_cannot_schedule(tmp_path, original_code):
    _, panel, screen, _ = await prepared(tmp_path, original_code)
    amend(screen, "screening_policy", lambda p: p.update(selection_root=str(tmp_path / "missing")))
    with pytest.raises((ValueError, FileNotFoundError)):
        activate_screened_panel(panel, screen)
    assert not (activation_root(panel) / "activation_facts.json").exists()


@pytest.mark.parametrize("nested", ["screen", "source"])
async def test_original_recovery_output_cannot_write_into_evidence(tmp_path, original_code, nested):
    source, panel, screen, _ = await prepared(tmp_path, original_code)
    activate_screened_panel(panel, screen)
    target = (screen if nested == "screen" else source) / "fs2_activation_read_nested"
    with pytest.raises(ValueError, match="separate"):
        read_original_activation(
            activation_root(panel),
            implementation_commit=original_code[1],
            repository=original_code[0],
            output_root=target,
        )
    assert not target.exists()


async def test_legacy_activation_recovery_and_no_injected_screening_context(
    tmp_path, original_code
):
    _, panel, _, _ = await legacy_prepared(tmp_path, original_code)
    result = activate_panel(panel)
    assert result["schema_version"] == "fs2-panel-activation-v1"
    assert "screening_seed" not in result
    original = read_original_activation(
        activation_root(panel),
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_activation_read_legacy",
    )
    assert original["report"]["summary"] == result
    amend(activation_root(panel), "activation_facts", lambda p: p.update(screening_seed="0" * 64))
    with pytest.raises(ValueError, match="screening context"):
        read_activation(panel)


def test_measured_role_age_is_exact_and_never_recomputed_at_recovery():
    from tests.unit.test_research_panel_bound_selection import clock

    report = {
        "screening_available_at": clock(0),
        "plan": {
            "assessment_policy": {"max_window_age_seconds": 60, "max_assessment_age_seconds": 60},
            "assessment_inventory": [
                {
                    "market_id": "1",
                    "effective_state": "triggered",
                    "assessment": {
                        "evidence_id": "a" * 64,
                        "input_window_end": {"$utc": clock(0)["utc"]},
                        "available_at": {"$utc": clock(0)["utc"]},
                    },
                }
            ],
            "assignments": [
                {"market_id": "1", "arm": "triggered", "assessment_evidence_id": "a" * 64}
            ],
        },
    }
    activation._screen_fresh(report, clock(60))
    with pytest.raises(ValueError, match="stale or future"):
        activation._screen_fresh(report, clock(60.000001))
    with pytest.raises(ValueError, match="unavailable"):
        activation._screen_fresh(report, clock(-1))
    report["plan"]["assessment_inventory"][0]["assessment"]["evidence_id"] = "b" * 64
    with pytest.raises(ValueError, match="authenticated assessment"):
        activation._screen_fresh(report, clock(1))
