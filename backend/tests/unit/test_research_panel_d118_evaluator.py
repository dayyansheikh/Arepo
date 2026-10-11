"""D118 evaluator: D116 code with only the declared D118 values, plus the population checks.

Fixtures are real artifacts written by ``run_synthetic_window_pilot`` (loopback sockets, mock
HTTP) on a liquidity-scoped selection (``LIQUIDITY_POPULATION``). Faults are injected by editing
retained JSON in a copy of the tree, re-hashing the pair acknowledgement.
"""

import asyncio
import hashlib
import importlib.util
import json
import shutil
import types
from pathlib import Path

import httpx
import pytest
from websockets.asyncio.server import serve

from astrolabe.research_panel import d116_evaluator as d116
from astrolabe.research_panel import d118_evaluator as ev
from astrolabe.research_panel.panel_declaration import LIQUIDITY_POPULATION, declare_panel
from astrolabe.research_panel.panel_selection import (
    LIQUIDITY_BELOW,
    create_panel_selection,
)
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_d116_evaluator import (
    _live_value,
    _original_code,
    edit,
    fixture_commit,
    summary,
)
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_owned_windows import execute
from tests.unit.test_research_panel_selection import frame

PANEL = "fs2_panel_worker"
MIB = 1048576


def _rows():
    rows = [
        market(i, description="Rules", archived=False, acceptingOrders=True,
               events=[{"id": "42"}], liquidity="5000")
        for i in (1, 2)
    ]
    # A frame row below the floor: retained in the inventory, zero inclusion, never requested.
    rows.append(market(3, description="Rules", archived=False, acceptingOrders=True,
                       events=[{"id": "42"}], liquidity="10"))
    return rows


def _transport(rows, book):
    by_id = {r["id"]: r for r in rows}
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in rows}
    seen = {}

    async def handle(request):
        if request.url.path.startswith("/markets/"):
            body = dict(by_id[request.url.path.split("/")[-1]])
            body.pop("events", None)
        elif request.url.path == "/book":
            token = request.url.params["token_id"]
            row = by_token[token]
            seen[token] = seen.get(token, 0) + 1
            bids, asks = book(row["id"], seen[token])
            body = {"asset_id": token, "market": row["conditionId"], "bids": bids, "asks": asks}
        else:
            body = {"data": [], "pagination": {"has_more": False, "next_cursor": None}}
        return httpx.Response(200, stream=Stream([json.dumps(body).encode()]))

    return httpx.MockTransport(handle)


def _side(size):
    return [{"price": "0.4", "size": size}]


ASK = [{"price": "0.6", "size": "1"}]
BOOKS = {
    # Row "1" bid size 2 against ask size 1: imbalance 1/3 = triggered; size 1 = untriggered.
    "pair": lambda i, n: (_side("2" if i == "1" else "1"), ASK),
    "all": lambda i, n: (_side("2"), ASK),
    "none": lambda i, n: (_side("1"), ASK),
    # Row "2" one-sided throughout: unavailable, so no eligible untriggered control exists.
    "no_untriggered": lambda i, n: (_side("2"), ASK if i == "1" else []),
    # Row "2" untriggered at screening, one-sided at its origin: the drawn pair is unobserved.
    "pair_unobserved": lambda i, n: (_side("2" if i == "1" else "1"),
                                     ASK if i == "1" or n == 1 else []),
}


async def _build(root: Path, book):
    root.mkdir(parents=True)
    code = _original_code(root)
    rows = _rows()
    source = await frame(root, rows)
    panel = root / PANEL
    declare_panel(
        source, implementation_commit=code[1], output_root=panel,
        protocol=protocol(cycles=1, target_attempts=1, scheduled_per_stratum=2,
                          controls_per_trigger=1, source_run_retained_bytes=4 * MIB,
                          max_origin_delay_seconds=45, horizon_seconds=8, tolerance_seconds=5,
                          max_origin_save_seconds=2, max_quote_age_seconds=120),
        strata_limit=1, storage_profile="compact-v1", population_policy=LIQUIDITY_POPULATION)
    create_panel_selection(panel, repository=code[0])
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in rows}

    async def handle(socket):
        token = json.loads(await socket.recv())["assets_ids"][0]
        await socket.send(json.dumps({
            "event_type": "book", "asset_id": token, "market": by_token[token]["conditionId"],
            "bids": _side("2"), "asks": ASK}))
        await socket.wait_closed()

    async with serve(handle, "127.0.0.1", 0) as server:
        await execute(panel, code, _transport(rows, book), server.sockets[0].getsockname()[1])
    shutil.rmtree(root / "original_code")
    return root


@pytest.fixture(scope="module")
def baselines(tmp_path_factory):
    result = {}
    for name, book in BOOKS.items():
        root = tmp_path_factory.mktemp("d118_" + name) / "tree"
        asyncio.run(_build(root, book))
        result[name] = root
    return result


@pytest.fixture
def tree(baselines, tmp_path):
    def make(name="pair"):
        target = tmp_path / name
        shutil.copytree(baselines[name], target)
        return target

    return make


def evaluate(root: Path):
    report = ev.evaluate_d118_logic_only_test_aid(root / PANEL)
    assert report["authoritative"] is False and report["non_authoritative_logic_only"]
    assert report["evaluator_version"] == "d118-evaluator-v1"
    json.dumps(report, sort_keys=True)
    return report


def screening_batch(root):
    return root / "fs2_screening_worker_worker" / "fs2_screening_batch"


def selection(root):
    return root / "fs2_selection_panel_worker"


# ---- reuse of the frozen D116 code -------------------------------------------------------


def test_classification_table_is_d116s_byte_for_byte():
    assert ev.TABLE_SHA256 == d116.TABLE_SHA256 == ev.D116_TABLE_SHA256
    assert ev.D116_TABLE_SHA256 == (
        "6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4")
    assert ev.CLASSIFICATION_TABLE is d116.CLASSIFICATION_TABLE
    assert ev.decide_outcome is d116.decide_outcome
    assert ev.common_mode_flags is d116.common_mode_flags


def test_namespace_differs_from_d116_only_in_declared_overrides():
    original = vars(d116)
    changed = {k for k, v in ev._GLOBALS.items() if original.get(k) is not v}
    assert changed == set(ev.OVERRIDES) | {"_Evaluation", "_guarded"}
    assert d116.EVALUATOR_VERSION == "d116-evaluator-v3"  # the frozen module is untouched
    assert d116.FROZEN_PANEL_NAME == "fs2_panel_d116_integrated_1"


def _names(code):
    found = set(code.co_names)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            found |= _names(const)
    return found


def test_every_d116_code_path_using_an_overridden_name_is_rebound():
    overridden = set(ev.OVERRIDES) | {"_Evaluation", "_guarded"}
    for name, value in vars(d116._Evaluation).items():
        if not isinstance(value, types.FunctionType):
            continue
        assert name in ev.REBOUND_METHODS
        if name in ev.D118_METHODS:
            continue
        mine = vars(ev._D118Evaluation)[name]
        assert mine.__code__ is value.__code__ and mine.__globals__ is ev._GLOBALS
    for name, value in vars(d116).items():
        if (isinstance(value, types.FunctionType) and value.__module__ == d116.__name__
                and _names(value.__code__) & overridden):
            assert name in ev.REBOUND_FUNCTIONS, name
    assert ev._guarded.__code__ is d116._guarded.__code__
    assert ev._evaluate.__code__ is d116.evaluate_d116.__code__


def test_frozen_d118_values():
    from astrolabe.research_panel import screening

    protocol_ = ev.D118_PROTOCOL
    assert {k: v for k, v in protocol_.items() if d116.D116_PROTOCOL[k] != v} == {
        "scheduled_slots": 16, "triggered_slots": 16,
        "scheduled_per_stratum": 4, "triggered_per_stratum": 4}
    frozen = ev.FROZEN_EXPECTATIONS
    assert frozen["panel"] == {"strata_limit": 4, "population_policy": LIQUIDITY_POPULATION}
    assert frozen["worker"]["runtime_concurrency"] == 8
    assert frozen["worker"]["concurrency"] == 8
    assert {k: v for k, v in frozen["worker"].items() if k != "runtime_concurrency"} == {
        k: v for k, v in d116.FROZEN_EXPECTATIONS["worker"].items()
        if k != "runtime_concurrency"}
    assert frozen["screening_limits"] == dict(screening.LIMITS)
    assert ev.FROZEN_PANEL_NAME == "fs2_panel_d118_control_pairing_1"
    assert set(ev.FROZEN_ROOT_NAMES.values()) == {
        "fs2_selection_panel_d118_control_pairing_1",
        "fs2_screening_worker_d118_control_pairing_1",
        "fs2_activation_d118_control_pairing_1", "fs2_runtime_d118_control_pairing_1"}
    assert d116.FROZEN_EXPECTATIONS["worker"]["runtime_concurrency"] == 4  # not mutated


# ---- outcome classes on real synthetic D118-shaped trees -----------------------------------


def test_pass_with_observed_pair(tree):
    report = evaluate(tree("pair"))
    assert report["outcome"] == "PASS", report["outcome_reasons"]
    assert all(g["pass"] for name, g in report["gates"].items() if name != "E0")
    assert report["summary"]["pairs_both_complete"] == 1
    assert report["gates"]["E2"]["population_exclusion_counts"] == {LIQUIDITY_BELOW: 1}
    assert report["diagnostics"]["max_window_age_at_freeze_s"] is not None
    assert "observed_origins_of_16" in report["diagnostics"]
    # The fixture's Gamma market bodies carry no event ids: dependence is not established.
    dependence = report["pairs"][0]["dependence"]
    assert dependence["state"] == "unknown_group_membership"
    assert dependence["counts_as"].startswith("mechanism execution only")


def test_oversubscribed_trigger_branch_and_all_triggered_label(tree):
    root = tree("all")
    report = evaluate(root)
    # Two triggered members, triggered_per_stratum 1: one has no triggered role, and E5 must
    # accept it only because its stratum's triggered_pool exceeds triggered_per_stratum.
    assert report["outcome"] == "PASS_WITH_LIMITATION:all_triggered_no_control"
    assert report["gates"]["E5"]["pass"], report["gates"]["E5"]["reasons"]
    plan = json.loads((screening_batch(root) / "screening_report.json").read_bytes())["plan"]
    assert plan["protocol"]["triggered_per_stratum"] == 1
    assert [s["triggered_pool"] for s in plan["strata"]] == [2]
    roles = [m["roles"] for m in report["members"].values()]
    assert sum(any(r["arm"] == "triggered" for r in rs) for rs in roles) == 1

    def shrink(r):
        r["plan"]["strata"][0]["triggered_pool"] = 1  # no longer oversubscribed

    edit(screening_batch(root), "screening_report", shrink)
    e5 = evaluate(root)["gates"]["E5"]
    assert not e5["pass"]
    assert any("no triggered assignment" in r for r in e5["reasons"])


def test_zero_triggered_label(tree):
    report = evaluate(tree("none"))
    assert report["outcome"] == (
        "PASS_WITH_LIMITATION:zero_triggered_control_matching_not_exercised")


def test_no_eligible_untriggered_label(tree):
    report = evaluate(tree("no_untriggered"))
    assert report["outcome"] == "PASS_WITH_LIMITATION:no_eligible_untriggered", (
        report["outcome_reasons"], report["findings"])
    assert report["summary"]["control_pool_zero_in_triggered_strata"] is True
    assert report["summary"]["n_unavailable_members"] == 1


def test_pair_member_unobserved_label(tree):
    report = evaluate(tree("pair_unobserved"))
    assert report["outcome"] == "PASS_WITH_LIMITATION:pair_member_unobserved_data_reason", (
        report["outcome_reasons"], report["findings"])
    assert report["summary"]["pairs_drawn"] == 1
    assert report["summary"]["pairs_both_complete"] == 0


def test_control_should_have_been_drawn_is_fail(tree):
    root = tree("pair")

    def drop(r):
        r["plan"]["assignments"] = [a for a in r["plan"]["assignments"] if a["arm"] != "control"]
        r["plan"]["strata"][0].update(controls_selected=0, unfilled_control_slots=1)

    edit(screening_batch(root), "screening_report", drop)
    report = evaluate(root)
    assert report["outcome"] == "FAIL" and not report["gates"]["E5"]["pass"]
    assert report["summary"]["control_pool_zero_in_triggered_strata"] is False
    assert ev.decide_outcome(summary(
        n_triggered_members=1, n_members=2, n_untriggered_members=1, control_assignments=0,
        control_pool_zero_in_triggered_strata=False)) == (
        "FAIL",
        ["no control drawn although a stratum with a trigger has a non-empty control pool"])


# ---- D118 population checks ----------------------------------------------------------------


def test_exclusion_reason_outside_allow_list_fails_e2(tree):
    root = tree("pair")
    edit(selection(root), "selection_plan",
         lambda p: p["exclusions"][0].update(reason="spread_above_0.10"))
    e2 = evaluate(root)["gates"]["E2"]
    assert not e2["pass"]
    assert any("allow-list" in r for r in e2["reasons"])
    assert any("population_exclusion_counts" in r for r in e2["reasons"])


def test_illiquid_eligible_stratum_fails_e2(tree):
    root = tree("pair")
    edit(selection(root), "selection_plan",
         lambda p: p["strata"][0].update(liquidity_band="0"))
    e2 = evaluate(root)["gates"]["E2"]
    assert not e2["pass"] and any("liquidity band" in r for r in e2["reasons"])


# ---- run identity (E0) and frozen values (E1) --------------------------------------------

ROOT_RENAMES = {
    "fs2_panel_worker": ev.FROZEN_PANEL_NAME,
    "fs2_selection_panel_worker": ev.FROZEN_ROOT_NAMES["selection"],
    "fs2_screening_worker_worker": ev.FROZEN_ROOT_NAMES["worker"],
    "fs2_activation_worker": ev.FROZEN_ROOT_NAMES["activation"],
    "fs2_runtime_worker": ev.FROZEN_ROOT_NAMES["runtime"],
}


def make_live(root: Path, renames=ROOT_RENAMES):
    for path in sorted(root.rglob("*.json")):
        if path.name.endswith("_ack.json"):
            continue
        payload = json.loads(path.read_bytes())
        before = json.dumps(payload, sort_keys=True)
        _live_value(payload)
        if json.dumps(payload, sort_keys=True) == before:
            continue
        from astrolabe.feature_store.capture import _json_bytes

        data = _json_bytes(payload)
        path.write_bytes(data)
        ack = path.with_name(path.stem + "_ack.json")
        if ack.exists() and "payload_hash" in json.loads(ack.read_bytes()):
            record = json.loads(ack.read_bytes())
            record["payload_hash"] = hashlib.sha256(data).hexdigest()
            ack.write_bytes(_json_bytes(record))
    for old, new in renames.items():
        (root / old).rename(root / new)
    return root / renames["fs2_panel_worker"]


def test_e0_passes_for_d118_names_and_e1_judges_frozen_d118_values(tree):
    root = tree("pair")
    commit = fixture_commit(root)
    panel = make_live(root)
    report = ev.evaluate_d118(panel, launch_commit=commit)
    assert report["gates"]["E0"]["pass"], report["gates"]["E0"]["reasons"]
    assert report["authoritative"] is True
    assert report["outcome"] == "FAIL"  # the fixture protocol is not the frozen D118 protocol
    e1 = " ".join(report["gates"]["E1"]["reasons"])
    assert "strata_limit" in e1 and "runtime_concurrency" in e1
    assert "scheduled_per_stratum" in e1
    assert "selection_plan.schema_version" not in e1  # the D118 population/schema is correct
    assert "panel_policy.schema_version" not in e1
    # The D116 evaluator refuses the D118 run identity.
    assert not d116.evaluate_d116(panel, launch_commit=commit)["gates"]["E0"]["pass"]


def test_d116_run_names_fail_d118_identity(tree):
    root = tree("pair")
    commit = fixture_commit(root)
    renames = {
        "fs2_panel_worker": "fs2_panel_d116_integrated_1",
        "fs2_selection_panel_worker": "fs2_selection_panel_d116_integrated_1",
        "fs2_screening_worker_worker": "fs2_screening_worker_d116_integrated_1",
        "fs2_activation_worker": "fs2_activation_d116_integrated_1",
        "fs2_runtime_worker": "fs2_runtime_d116_integrated_1",
    }
    panel = make_live(root, renames)
    report = ev.evaluate_d118(panel, launch_commit=commit)
    assert not report["gates"]["E0"]["pass"] and not report["authoritative"]
    assert report["outcome"] == "FAIL"


def test_d118_e1_rejects_temporal_only_population(tree):
    root = tree("pair")
    commit = fixture_commit(root)
    panel = make_live(root)
    edit(root / ev.FROZEN_ROOT_NAMES["selection"], "selection_plan",
         lambda p: p.update(schema_version="fs2-panel-selection-plan-v3"))
    e1 = ev.evaluate_d118(panel, launch_commit=commit)["gates"]["E1"]["reasons"]
    assert any("selection_plan.schema_version" in r for r in e1)


def test_exception_yields_d118_fail_report(tmp_path):
    report = ev.evaluate_d118(tmp_path / "fs2_panel_missing", launch_commit="0" * 40)
    assert report["outcome"] == "FAIL" and report["authoritative"] is False
    assert report["evaluator_version"] == "d118-evaluator-v1"


def _load_cli():
    path = Path(__file__).parents[2] / "scripts" / "evaluate_d118.py"
    spec = importlib.util.spec_from_file_location("evaluate_d118", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_requires_launch_commit_and_writes_report(tree, tmp_path, capsys):
    root = tree("pair")
    cli = _load_cli()
    out = tmp_path / "report.json"
    with pytest.raises(SystemExit):
        cli.main([str(root / PANEL), "--out", str(out)])
    assert cli.main([str(root / PANEL), "--out", str(out),
                     "--launch-commit", fixture_commit(root)]) == 0
    report = json.loads(out.read_text())
    assert report["evaluator_version"] == "d118-evaluator-v1"
    assert report["outcome"] == "FAIL" and report["authoritative"] is False
    with pytest.raises(SystemExit):
        cli.main([str(root / PANEL), "--out", str(out), "--launch-commit", "0" * 40])
