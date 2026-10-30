"""Snapshot components frozen causally inside origins, without inventing window features."""

from fractions import Fraction

import httpx
import pytest

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import concurrent_runtime, origin_features, origin_worker, runtime
from astrolabe.research_panel.original_reader import read_original_runtime
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_concurrent_runtime import setup
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, snapshot

original_code = _original_code


def transport(*, changed=False, book_status=200):
    def handler(request):
        status = 200
        if request.url.path.startswith("/markets/"):
            body = market(1, archived=False, acceptingOrders=True)
            if changed:
                body["description"] = "revised rules"
        elif request.url.path == "/book":
            status = book_status
            body = {
                "asset_id": "2",
                "market": "0x" + f"{1:064x}",
                "bids": [{"price": "0.400", "size": "2.00"}],
                "asks": [{"price": "0.600", "size": "1.00"}],
            }
        else:
            body = {"data": [], "pagination": {"has_more": False, "next_cursor": None}}
        return httpx.Response(status, stream=Stream([_json_bytes(body)]))

    return httpx.MockTransport(handler)


def ratio(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def root_origin(panel):
    return next((runtime.run_root(panel) / "origins").iterdir())


def rebind_inventory(child):
    # Reseal only synthetic fixtures so semantic replay, not the outer hash, is exercised.
    receipt, _ = _pair(child, "origin_receipt")
    receipt["inventory"] = origin_worker._snapshot(child, 10 * 1048576)
    amend(child, "origin_receipt", lambda value: value.update(receipt))


async def test_components_causal_freeze_due_targets_and_original_recovery(tmp_path, original_code):
    panel, screen = await setup(tmp_path, original_code)
    result = await runtime.exercise_screened_panel(
        panel, screen, transport=transport(), features=True
    )
    assert result["schema_version"] == concurrent_runtime.FEATURE_VERSION
    assert result["origins"][0]["state"] == result["outcomes"][0]["state"] == "observed"
    child = root_origin(panel)
    facts, ack = _pair(child, "origin_facts")
    manifest = facts["projection"]["feature_manifest"]
    assert facts["schema_version"] == origin_worker.FEATURE_VERSION
    assert ratio(manifest["components"]["F08_snapshot"]) == Fraction(1, 3)
    assert manifest["components"]["F08_snapshot"]["decimal"] is None
    assert ratio(manifest["components"]["F09_snapshot"]) == Fraction(1, 30)
    assert len(manifest["input_observation_ids"]) == 3
    assert len(manifest["raw_trade_observation_ids"]) == 1
    assert manifest["snapshot_candidates_eligible_at_freeze"]
    assert set(manifest["unavailable_families"]) == set(origin_features.UNAVAILABLE)
    assert all(v["state"] == "unavailable" for v in manifest["unavailable_families"].values())
    assert (
        not manifest["validated_predictive_features"] and not manifest["continuous_window_eligible"]
    )
    assert (
        _time(facts["read_started_at"])
        <= _time(facts["feature_computed_at"])
        <= (_time(facts["origin_at"]))
        <= _time(ack["durable_ack"])
    )
    assert len(_json_bytes(manifest)) <= origin_features.POLICY["max_manifest_bytes"]
    before = snapshot(runtime.run_root(panel))
    original = read_original_runtime(
        runtime.run_root(panel),
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_runtime_read_features",
    )
    assert original["report"] == result
    assert before == snapshot(runtime.run_root(panel))
    # Retained successful fixture can exercise multiple semantic corruptions without more capture.
    intent, _ = _pair(child, "origin_intent")
    panel_policy, _ = _pair(panel, "panel_policy")
    from astrolabe.research_panel.activation import read_activation

    activation = read_activation(panel)
    originals = snapshot(child)
    for change in ("component", "future_compute", "eligibility", "cutoff"):
        import copy

        broken = copy.deepcopy(facts)
        if change == "component":
            broken["projection"]["feature_manifest"]["components"]["F08_snapshot"]["numerator"] = (
                "2"
            )
        elif change == "future_compute":
            broken["feature_computed_at"] = ack["durable_ack"]
        elif change == "eligibility":
            broken["projection"]["feature_manifest"]["unavailable_families"]["F27"]["state"] = (
                "observed"
            )
        else:
            broken["projection"]["feature_manifest"]["computed_cutoff"] = {
                "$utc": "2000-01-01T00:00:00Z"
            }
        amend(child, "origin_facts", lambda value, broken=broken: value.update(broken))
        rebind_inventory(child)
        with pytest.raises(ValueError):
            origin_worker._read_one(
                child, intent["slot"], intent["member"], panel_policy, activation
            )
        for path, data in originals.items():
            (child / path).write_bytes(data)


@pytest.mark.parametrize(
    "kwargs,state",
    [
        ({"changed": True}, "identity_changed_since_selection"),
        ({"book_status": 429}, "rate_limited"),
    ],
)
async def test_unsupported_origins_never_gain_feature_eligibility(
    tmp_path, original_code, kwargs, state
):
    panel, screen = await setup(tmp_path, original_code)
    report = await runtime.exercise_screened_panel(
        panel, screen, transport=transport(**kwargs), features=True
    )
    facts, _ = _pair(root_origin(panel), "origin_facts")
    manifest = facts["projection"]["feature_manifest"]
    assert report["origins"][0]["state"] == state
    assert manifest["state_at_freeze"] == state
    assert not manifest["snapshot_candidates_eligible_at_freeze"]
    assert runtime.read_runtime(panel) == report


async def test_feature_mode_requires_explicit_boolean(tmp_path):
    with pytest.raises(ValueError, match="explicit feature"):
        await runtime.exercise_screened_panel(tmp_path, tmp_path, transport=transport(), features=1)


def test_manifest_limit_fails_closed_without_changing_inputs(monkeypatch):
    import copy

    from tests.unit.test_research_panel_quote_inputs import AT, POLICY, book, gamma

    rows = [gamma(), book()]
    original = copy.deepcopy(rows)
    monkeypatch.setitem(origin_features.POLICY, "max_manifest_bytes", 1)
    with pytest.raises(ValueError, match="budget"):
        origin_features.project_origin_features(rows, policy=POLICY, cutoff=AT)
    assert rows == original


def test_stale_cutoff_keeps_unavailable_components_and_native_age_unknown():
    from datetime import timedelta

    from tests.unit.test_research_panel_quote_inputs import AT, POLICY, book, gamma

    result = origin_features.project_origin_features(
        [gamma(), book()], policy=POLICY, cutoff=AT + timedelta(days=1)
    )
    assert result["snapshot_state"] != "observed"
    assert result["components"] is None and result["native_book_age"] is None


@pytest.mark.parametrize(
    "origin_state,snapshot_state",
    [
        ("late_origin", "observed"),
        ("identity_changed_since_selection", "observed"),
        ("observed", "numerical_budget_exceeded"),
    ],
)
def test_freeze_ineligibility_preserves_values(origin_state, snapshot_state):
    projection = {
        "state_at_freeze": origin_state,
        "feature_manifest": {
            "snapshot_state": snapshot_state,
            "components": {"F08_snapshot": {"numerator": "1", "denominator": "3"}},
        },
    }
    origin_features.freeze_eligibility(projection)
    assert not projection["feature_manifest"]["snapshot_candidates_eligible_at_freeze"]
    assert projection["feature_manifest"]["components"]["F08_snapshot"]["numerator"] == "1"
