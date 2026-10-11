"""D120 screen-then-activate: synthetic owned path and the D120 evaluator.

Fixtures are real artifacts written by ``run_synthetic_pairing_pilot`` (loopback sockets, mock
HTTP, 1 s windows, short horizons) on a pairing declaration with four category strata. Faults are
injected by editing retained JSON in a copy of the tree and re-hashing the pair acknowledgement.
"""

import asyncio
import json
import shutil
from dataclasses import asdict, replace
from pathlib import Path

import httpx
import pytest
from websockets.asyncio.server import serve

from astrolabe.feature_store.capture import Budget
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import d116_evaluator as d116
from astrolabe.research_panel import d120_evaluator as ev
from astrolabe.research_panel import pairing
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.frame import GammaFrameRun
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.owned_windows import OwnedWindowPolicy
from astrolabe.research_panel.pairing_declaration import (
    PairingPanelProtocol,
    declare_pairing_panel,
    panel_protocol,
    read_declaration,
    reservation,
)
from astrolabe.research_panel.pairing_selection import create_pairing_selection
from astrolabe.research_panel.pairing_worker import run_synthetic_pairing_pilot
from astrolabe.research_panel.panel_declaration import PanelProtocol
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.selection import read_selection
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_d116_evaluator import _original_code, edit

PANEL = "fs2_panel_pairing"
FEES = ("sports_fees_v3", "politics_fees", "crypto_fees", "weather_fees")
DESIGN = pairing.PairingDesign(strata=4, screen_per_stratum=3, min_groups_per_stratum=3)


def market(index, **extra):
    return {"id": str(index), "conditionId": "0x" + f"{index:064x}",
            "clobTokenIds": json.dumps([str(index * 2), str(index * 2 + 1)]),
            "outcomes": '["Yes","No"]', "active": True, "closed": False,
            "description": "Rules", "archived": False, "acceptingOrders": True,
            "endDate": "2099-01-01T00:00:00Z", "liquidity": "5000",
            "outcomePrices": '["0.3","0.7"]', **extra}


def rows():
    """Four category strata x four groups (one sibling pair per stratum); one illiquid row."""
    result, index = [], 1
    for c, fee in enumerate(FEES):
        for g in range(4):
            event = {"id": f"{c}{g}", "series": [{"slug": f"series-{c}-{g}"}]}
            result.append(market(index, feeType=fee, events=[event]))
            GROUP[str(index)] = g
            index += 1
            if g == 0:
                result.append(market(index, feeType=fee, events=[event]))
                GROUP[str(index)] = g
                index += 1
    result.append(market(index, feeType=FEES[0], liquidity="10", events=[{"id": "low"}]))
    return result


GROUP = {}


def alternate(row):
    # Two triggered and two untriggered groups per stratum (siblings share a state), so any
    # three screened groups hold both states: bid size 2 vs ask 1 is |imbalance| 1/3.
    return "2" if GROUP.get(row["id"], 1) % 2 == 0 else "1"


def protocol():
    return PairingPanelProtocol(
        screened_slots=12, origin_slots=8, cycles=1, target_attempts=1, cadence_seconds=120,
        max_origin_delay_seconds=45, max_origin_save_seconds=2, horizon_seconds=8,
        tolerance_seconds=5, max_frame_age_seconds=3600, max_frame_interval_seconds=600,
        max_quote_age_seconds=120, max_identity_age_seconds=180, source_response_bytes=65536,
        source_run_retained_bytes=1048576)


def windows():
    return OwnedWindowPolicy(1000, WindowBindingPolicy(120000, 120000),
                             WindowReconciliationPolicy(120000, 120000, 100),
                             OriginWindowPolicy(120000, 60000), binding_mode="observation")


def transport(markets, size_of):
    by_id = {r["id"]: r for r in markets}
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in markets}

    async def handle(request):
        if request.url.path.startswith("/markets/"):
            body = dict(by_id[request.url.path.split("/")[-1]])
            body.pop("events", None)
        elif request.url.path == "/book":
            token = request.url.params["token_id"]
            row = by_token[token]
            body = {"asset_id": token, "market": row["conditionId"],
                    "bids": [{"price": "0.4", "size": size_of(row)}],
                    "asks": [{"price": "0.6", "size": "1"}]}
        else:
            body = {"data": [], "pagination": {"has_more": False, "next_cursor": None}}
        return httpx.Response(200, stream=Stream([json.dumps(body).encode()]))

    return httpx.MockTransport(handle)


async def _build(root, size_of):
    root.mkdir(parents=True)
    code = _original_code(root)
    markets = rows()
    body = json.dumps({"markets": markets}).encode()
    frame = root / "fs2_capture_frame"
    await GammaFrameRun(frame, limit=100, budget=Budget(requests=1),
                        transport=httpx.MockTransport(
                            lambda r: httpx.Response(200, stream=Stream([body])))).collect()
    panel = root / PANEL
    declare_pairing_panel(frame, implementation_commit=code[1], output_root=panel,
                          protocol=protocol(), design=DESIGN, storage_profile="compact-v1")
    create_pairing_selection(panel, repository=code[0])
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in markets}

    async def handle(socket):
        token = json.loads(await socket.recv())["assets_ids"][0]
        await socket.send(json.dumps({
            "event_type": "book", "asset_id": token, "market": by_token[token]["conditionId"],
            "bids": [{"price": "0.4", "size": "2"}], "asks": [{"price": "0.6", "size": "1"}]}))
        await socket.wait_closed()

    async with serve(handle, "127.0.0.1", 0) as server:
        result = await run_synthetic_pairing_pilot(
            panel, implementation_commit=code[1], repository=code[0],
            transport=transport(markets, size_of), port=server.sockets[0].getsockname()[1],
            rule=SnapshotTriggerPolicy(1, 3, 120000), freshness=ScreeningPolicy(120, 120),
            window_policy=windows(), concurrency=4, runtime_concurrency=8)
    shutil.rmtree(root / "original_code")
    return root, result


def _scenario(factory, name, size_of):
    return asyncio.run(_build(factory.mktemp(name) / "tree", size_of))


@pytest.fixture(scope="module")
def baselines(tmp_path_factory):
    return {
        "pair": _scenario(tmp_path_factory, "pair", alternate),
        "scarce": _scenario(tmp_path_factory, "scarce", lambda r: "2"),
    }


@pytest.fixture
def tree(baselines, tmp_path):
    def make(name="pair"):
        target = tmp_path / name
        shutil.copytree(baselines[name][0], target)
        return target

    return make


def evaluate(root):
    report = ev.evaluate_d120_logic_only_test_aid(root / PANEL)
    assert report["authoritative"] is False and report["non_authoritative_logic_only"]
    json.dumps(report, sort_keys=True)
    return report


def batch(root):
    return root / "fs2_screening_worker_pairing" / "fs2_screening_batch"


# ----- pipeline ---------------------------------------------------------------------------------
def test_pipeline_screens_group_disjoint_members_and_activates_pairs_only(baselines):
    root, result = baselines["pair"]
    assert result["state"] == "pilot_collected_unaccepted"
    plan = result["screening"]["plan"]
    assert plan["schema_version"] == "fs2-sampling-plan-v6"
    assert len(result["screening"]["states"]) == 12
    assert all("covariates" in s for s in result["screening"]["states"])
    roles = {a["market_id"]: a["arm"] for a in plan["assignments"]}
    assert set(roles.values()) == {"triggered", "control"}
    assert len(result["bindings"]) == len(roles) == 2 * plan["pairs_drawn"]
    assert len(result["runtime"]["origins"]) == len(roles)
    groups = [a["dependence_group"] for a in plan["screened_assignments"]]
    assert len(groups) == len(set(groups))
    worker = root / "fs2_screening_worker_pairing"
    assert sorted(p.name for p in worker.glob("window_*.json")
                  if not p.name.endswith("_ack.json")) == [
        f"window_{k:03d}.json" for k in range(len(roles))]
    assert not list(worker.glob("fs2_socket_window_*")) or len(
        list(worker.glob("fs2_socket_window_*"))) == len(roles)
    selection = read_selection(root / "fs2_selection_panel_pairing")
    assert selection["plan"]["schema_version"] == "fs2-pairing-selection-plan-v1"
    assert selection["plan"]["population_exclusion_counts"] == {
        "frame_gamma_liquidity_below_1000": 1}
    assert {s["category"] for s in selection["plan"]["strata"]} == {
        "fee:sports", "fee:politics", "fee:crypto", "fee:weather"}


def test_declaration_dispatch_keeps_legacy_protocols_on_the_frozen_path(baselines):
    root, _ = baselines["pair"]
    declaration = read_declaration(root / PANEL)
    assert declaration["schema_version"] == "fs2-pairing-panel-declaration-v1"
    assert declaration["reservation"]["screened_slots"] == 12
    assert declaration["reservation"]["origin_slots"] == 8
    legacy = {"scheduled_slots": 8, "triggered_slots": 8, "controls_per_trigger": 1,
              "cycles": 1, "target_attempts": 1, "scheduled_per_stratum": 2,
              "triggered_per_stratum": 2, "cadence_seconds": 120,
              "max_origin_delay_seconds": 60, "max_origin_save_seconds": 5,
              "horizon_seconds": 60, "tolerance_seconds": 15, "max_frame_age_seconds": 3600,
              "max_frame_interval_seconds": 600, "max_quote_age_seconds": 60,
              "max_identity_age_seconds": 180, "source_response_bytes": 65536,
              "source_run_retained_bytes": 1048576}
    assert type(panel_protocol(legacy)) is PanelProtocol
    assert type(panel_protocol(asdict(protocol()))) is PairingPanelProtocol


def test_reservation_counts_screened_members_as_receipts_not_origins():
    big = replace(protocol(), screened_slots=96, origin_slots=12)
    value = reservation(big, pairing.PairingDesign(6, 16), storage_profile="compact-v1")
    assert value["origin_slots"] == 12 and value["screened_slots"] == 96
    assert value["source_request_slots"] == 96 * 2 + 12 * 2 + 12 * 3 + 12 * 2
    assert value["required_free_bytes"] < 4 * 1024**3
    with pytest.raises(ValueError):
        reservation(big, pairing.PairingDesign(6, 12))
    for bad in ({"origin_slots": 14}, {"origin_slots": 3}, {"cycles": 2},
                {"screened_receipt_bytes": 1024}):
        with pytest.raises(ValueError):
            replace(big, **bad)


# ----- evaluator ----------------------------------------------------------------------------------
def test_pass_with_group_disjoint_complete_pairs(tree):
    report = evaluate(tree())
    summary = report["summary"]
    assert report["gates"] and all(g["pass"] for k, g in report["gates"].items() if k != "E0")
    assert summary["strata_with_trigger"] == 4 and summary["triggers_in_scope"] == 4
    assert summary["fill"] == "4/4" and summary["group_disjoint_complete_pairs"] == 4
    assert report["outcome_reasons"][0] == "non_authoritative_logic_only"
    assert report["outcome"] == "PASS"
    assert summary["state_disagreements"] == 0
    assert all(p["group_disjoint"] for p in report["pairs"])


def test_control_scarcity_is_a_limitation(tree):
    report = evaluate(tree("scarce"))
    assert report["summary"]["fill"] == "0/4"
    assert report["summary"]["control_scarcity_strata"] == 4
    assert report["outcome"] == "PASS_WITH_LIMITATION:control_scarcity"


def test_shared_dependence_group_among_activated_members_fails(tree):
    root = tree()

    def merge(report):
        plan = report["plan"]
        active = sorted({a["market_id"] for a in plan["assignments"]})
        group = next(a["dependence_group"] for a in plan["screened_assignments"]
                     if a["market_id"] == active[0])
        for a in plan["screened_assignments"]:
            if a["market_id"] == active[1]:
                a["dependence_group"] = group

    edit(batch(root), "screening_report", merge)
    report = evaluate(root)
    assert any("share" in r for r in report["gates"]["E5"]["reasons"])
    assert report["outcome"] == "FAIL"


def test_relabelled_role_fails_the_exact_role_replay(tree):
    root = tree()

    def relabel(report):
        for a in report["plan"]["assignments"]:
            a["arm"] = {"triggered": "control", "control": "triggered"}[a["arm"]]

    edit(batch(root), "screening_report", relabel)
    report = evaluate(root)
    assert any("replay" in r for r in report["gates"]["E5"]["reasons"])
    assert report["outcome"] == "FAIL"


def test_bindings_must_cover_every_drawn_role(tree):
    root = tree()
    worker = root / "fs2_screening_worker_pairing"

    def drop(value):
        value["items"] = value["items"][1:]

    edit(worker, "bindings", drop)
    report = evaluate(root)
    assert report["outcome"] == "FAIL"


def test_state_disagreement_is_counted_never_relabelled(tree):
    root = tree()
    worker = root / "fs2_screening_worker_pairing"
    folder = worker / "fs2_trigger_declaration_bind_000" / "fs2_trigger_computation_result"

    def flip(facts):
        state = facts["projection"]["state"]
        facts["projection"]["state"] = {"triggered": "untriggered",
                                        "untriggered": "triggered"}[state]

    edit(folder, "trigger_computation_facts", flip)
    report = evaluate(root)
    assert report["summary"]["state_disagreements"] == 1
    assert report["outcome"] == "PASS"  # descriptive only
    assert {a["arm"] for a in report["members"].values() for a in a["roles"]} == {
        "triggered", "control"}


def test_synthetic_tree_is_never_authoritative_and_e0_names_the_d120_run(tree):
    root = tree()
    report = ev.evaluate_d120(root / PANEL, launch_commit="0" * 40)
    assert report["authoritative"] is False and report["outcome"] == "FAIL"
    assert any("fs2_panel_d120_pairing_1" in r for r in report["gates"]["E0"]["reasons"])
    assert report["evaluator_version"] == "d120-evaluator-v1"


def test_overrides_differ_from_d116_only_in_declared_names():
    names = {k for k in vars(d116) if k in ev._GLOBALS and ev._GLOBALS[k] is not vars(d116)[k]}
    assert names == set(ev.OVERRIDES) | {"_Evaluation", "_guarded"}
    assert ev.TABLE_SHA256 == ev.D116_TABLE_SHA256


# ----- pure decision ------------------------------------------------------------------------------
def summary(**changes):
    base = {"engineering_findings": 0, "failed_gates": [], "common_mode": [],
            "strata_with_trigger": 6, "screening_coverage_ok": True,
            "screening_coverage": "96/96", "triggers_in_scope": 6, "fill": "6/6",
            "fill_ok": True, "group_disjoint_complete_pairs": 5,
            "incomplete_pair_members_data_only": True}
    base.update(changes)
    return base


@pytest.mark.parametrize("changes,outcome", [
    ({}, "PASS"),
    ({"group_disjoint_complete_pairs": 3}, "PASS"),
    ({"engineering_findings": 1}, "FAIL"),
    ({"failed_gates": ["E5"]}, "FAIL"),
    ({"common_mode": ["x"]}, "FAIL"),
    ({"strata_with_trigger": 3, "triggers_in_scope": 3}, "INCONCLUSIVE"),
    ({"screening_coverage_ok": False}, "INCONCLUSIVE"),
    ({"fill": "4/6", "fill_ok": False}, "PASS_WITH_LIMITATION:control_scarcity"),
    ({"group_disjoint_complete_pairs": 2},
     "PASS_WITH_LIMITATION:pair_member_unobserved_data_reason"),
    ({"group_disjoint_complete_pairs": 2, "incomplete_pair_members_data_only": False}, "FAIL"),
])
def test_decision_is_exhaustive(changes, outcome):
    assert ev.decide_outcome(summary(**changes))[0] == outcome


def test_data_reason_limitation_needs_an_incomplete_member_and_every_cause_data():
    data, eng = {"class": "DATA_SOURCE"}, {"class": "ENGINEERING"}
    members = {"a": {"causes": [data]}, "b": {"causes": [data, eng]}, "c": {"causes": []}}
    assert ev.incomplete_data_only(members, ["a"]) is True
    assert ev.incomplete_data_only(members, []) is False          # nothing incomplete
    assert ev.incomplete_data_only(members, ["a", "b"]) is False  # a later cause is ENGINEERING
    assert ev.incomplete_data_only(members, ["c"]) is False       # no classified cause
    assert ev.incomplete_data_only(members, ["zz"]) is False      # unknown member


def test_dry_run_and_estimates_records_exist():
    docs = Path(__file__).resolve().parents[3] / "docs" / "implementation" / "d120"
    estimates = json.loads((docs / "D120_DESIGN_ESTIMATES.json").read_text())
    assert estimates["fidelity"]["reproduces_d118"] is True
    assert set(estimates["headline"]["P_pass_by_scenario"]) == {"S1", "S4", "S4h", "S4q"}


def test_runtime_report_lists_only_activated_origins(baselines):
    root, result = baselines["pair"]
    runtime = root / "fs2_runtime_pairing"
    policy, _ = _pair(runtime, "runtime_policy")
    assert policy["schema_version"] == "fs2-pairing-window-runtime-v6"
    assert len(list((runtime / "origins").iterdir())) == len(result["bindings"])
