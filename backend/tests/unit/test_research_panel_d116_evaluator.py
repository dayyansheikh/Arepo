"""D116 evaluator: gates, exhaustive classification, citation checks and the outcome classes.

Fixtures are real artifacts written by ``run_synthetic_window_pilot`` (loopback sockets, mock
HTTP). Faults are injected by editing retained JSON in a copy of the tree; the pair acknowledgement
is re-hashed so that the evaluator's own integrity check passes and the fault itself is judged.
"""

import asyncio
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import httpx
import pytest
from websockets.asyncio.server import serve

from astrolabe.feature_store.capture import _json_bytes
from astrolabe.research_panel import d116_evaluator as ev
from astrolabe.research_panel.targets import TARGET_ABSTENTIONS
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_original_reader import git
from tests.unit.test_research_panel_owned_windows import execute, setup

PANEL = "fs2_panel_worker"


def _original_code(root: Path):
    import os

    repo = root / "original_code"
    package = repo / "backend" / "astrolabe"
    package.mkdir(parents=True)
    source = Path(__file__).parents[2] / "astrolabe"
    shutil.copyfile(source / "__init__.py", package / "__init__.py")
    for name in ("feature_store", "research_panel"):
        (package / name).mkdir()
        for file in (source / name).glob("*.py"):
            shutil.copyfile(file, package / name / file.name)
    git(repo, "init", "--quiet")
    git(repo, "add", "backend")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "Original code fixture")
    assert os.path.isdir(repo)
    return repo, git(repo, "rev-parse", "HEAD")


def _source(rows, size_of, down=False):
    by_id = {r["id"]: r for r in rows}
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in rows}

    async def handle(request):
        if down:
            return httpx.Response(503, stream=Stream([b'{"error":"down"}']))
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


async def _build(root: Path, size_of, down=False):
    root.mkdir(parents=True)
    code = _original_code(root)
    _, panel, rows = await setup(root, code)
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in rows}

    async def handle(socket):
        token = json.loads(await socket.recv())["assets_ids"][0]
        await socket.send(json.dumps({
            "event_type": "book", "asset_id": token, "market": by_token[token]["conditionId"],
            "bids": [{"price": "0.4", "size": "2"}], "asks": [{"price": "0.6", "size": "1"}]}))
        await socket.wait_closed()

    async with serve(handle, "127.0.0.1", 0) as server:
        await execute(panel, code, _source(rows, size_of, down), server.sockets[0].getsockname()[1])
    shutil.rmtree(root / "original_code")
    shutil.rmtree(root / ".git", ignore_errors=True)
    return root


def _scenario(factory, name, size_of, down=False):
    root = factory.mktemp(name) / "tree"
    asyncio.run(_build(root, size_of, down))
    return root


@pytest.fixture(scope="module")
def baselines(tmp_path_factory):
    # Row "1" has bid size 2 against ask size 1: imbalance 1/3 = triggered; size 1 = untriggered.
    return {
        "pair": _scenario(tmp_path_factory, "pair", lambda r: "2" if r["id"] == "1" else "1"),
        "none": _scenario(tmp_path_factory, "none", lambda r: "1"),
        "all": _scenario(tmp_path_factory, "all", lambda r: "2"),
        "down": _scenario(tmp_path_factory, "down", lambda r: "1", down=True),
    }


@pytest.fixture
def tree(baselines, tmp_path):
    def make(name="pair"):
        target = tmp_path / name
        shutil.copytree(baselines[name], target)
        return target

    return make


def edit(folder: Path, name: str, mutate):
    path = folder / f"{name}.json"
    payload = json.loads(path.read_bytes())
    mutate(payload)
    data = _json_bytes(payload)
    path.write_bytes(data)
    ack = json.loads((folder / f"{name}_ack.json").read_bytes())
    ack["payload_hash"] = hashlib.sha256(data).hexdigest()
    (folder / f"{name}_ack.json").write_bytes(_json_bytes(ack))


def evaluate(root: Path):
    report = ev.evaluate_d116(root / PANEL, protocol_expectation=None)
    json.dumps(report, sort_keys=True)  # must be JSON-serialisable and sortable
    return report


def rules(report):
    return {f["rule"] for f in report["findings"] if f["class"] == ev.ENGINEERING}


def runtime(root):
    return root / "fs2_runtime_worker"


def test_clean_pass_with_observed_matched_pair(tree):
    report = evaluate(tree("pair"))
    assert report["outcome"] == "PASS", report["outcome_reasons"]
    assert all(g["pass"] for g in report["gates"].values())
    assert report["summary"]["complete_chains"] == 2
    assert report["summary"]["pairs_both_complete"] == 1
    pair = report["pairs"][0]
    assert {pair["triggered_market"], pair["control_market"]} == {"1", "2"}
    assert pair["both_complete"]
    assert report["finding_counts"].get("ENGINEERING", 0) == 0
    assert report["evaluator_version"] == "d116-evaluator-v1"
    assert report["classification_table_sha256"] == ev.TABLE_SHA256
    assert report["diagnostics"]["observed_matched_pairs"] == 1
    assert report["diagnostics"]["target_ratio_5v_ge_4o"] is True


def test_evaluation_is_deterministic(tree):
    root = tree("pair")
    assert json.dumps(evaluate(root), sort_keys=True) == json.dumps(evaluate(root), sort_keys=True)


def test_missing_trigger_journal_fails(tree):
    root = tree("pair")
    shutil.rmtree(root / "fs2_screening_worker_worker" / "fs2_trigger_declaration_batch_000")

    def mutate(report):
        market = report["states"][0]["market_id"]
        report["states"][0] = {"market_id": market, "state": "not_assessed"}
        for entry in report["plan"]["assessment_inventory"]:
            if entry["market_id"] == market:
                entry.update(effective_state="not_assessed", assessment=None,
                             reasons=["not_assessed"])

    edit(root / "fs2_screening_worker_worker" / "fs2_screening_batch", "screening_report", mutate)
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "screening_state:not_assessed" in rules(report)
    assert not report["gates"]["E3"]["pass"]


def test_stale_assessment_fails_even_though_state_row_is_unchanged(tree):
    root = tree("pair")

    def mutate(report):
        entry = report["plan"]["assessment_inventory"][0]
        entry.update(effective_state="unavailable", reasons=["assessment_stale"])

    edit(root / "fs2_screening_worker_worker" / "fs2_screening_batch", "screening_report", mutate)
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "assessment_reason:assessment_stale" in rules(report)


def test_expired_target_attempt_fails(tree):
    root = tree("pair")

    def mutate(report):
        report["attempts"][0]["state"] = "expired"
        report["outcomes"][0].update(state="unavailable")
        report["outcomes"][0]["target"]["exclusions"] = []

    edit(runtime(root), "runtime_report", mutate)
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "target_attempt_state:expired" in rules(report)
    assert not report["gates"]["E7"]["pass"]


def test_origin_failed_fails(tree):
    root = tree("pair")
    edit(runtime(root), "runtime_report", lambda r: r["origins"][0].update(state="failed"))
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "origin_state:failed" in rules(report)
    assert not report["gates"]["E6"]["pass"]


def test_unknown_state_is_engineering(tree):
    root = tree("pair")
    edit(runtime(root), "runtime_report", lambda r: r["origins"][1].update(state="mystery_state"))
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "origin_state:mystery_state" in rules(report)
    assert ev._finding("no_such_namespace", "x", stage="t")["class"] == ev.ENGINEERING


def test_every_member_transport_error_is_common_mode_fail_not_inconclusive(tree):
    report = evaluate(tree("down"))
    assert report["outcome"] == "FAIL"
    assert report["finding_counts"].get("ENGINEERING", 0) == 0  # all causes are classified DATA
    assert report["summary"]["complete_chains"] == 0
    assert len(report["common_mode"]) >= 2
    assert any("same cause" in c for c in report["common_mode"])
    assert any("transport" in c for c in report["common_mode"])
    cited = [f for f in report["findings"]
             if f["state"] == "source_error" and f["stage"] == "origin"]
    assert cited and all(f["class"] == ev.DATA_TRANSPORT and f["citation"] for f in cited)


def test_zero_triggered_is_limitation(tree):
    report = evaluate(tree("none"))
    assert report["outcome"] == (
        "PASS_WITH_LIMITATION:zero_triggered_control_matching_not_exercised")
    assert report["summary"]["n_triggered_members"] == 0
    assert report["summary"]["complete_chains"] == 2


def test_all_triggered_is_limitation(tree):
    report = evaluate(tree("all"))
    assert report["outcome"] == "PASS_WITH_LIMITATION:all_triggered_no_control"
    assert report["summary"]["control_assignments"] == 0
    assert report["summary"]["n_triggered_members"] == 2


def test_data_classification_needs_supporting_raw_receipt(tree):
    root = tree("pair")
    # Claim a one-sided origin book although the retained 2xx response has both sides.
    edit(runtime(root), "runtime_report",
         lambda r: r["origins"][0].update(state="one_sided_or_missing"))
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "citation_failed:book_empty_side:origin_state:one_sided_or_missing" in rules(report)


def test_one_sided_book_with_parsed_empty_side_is_data_source(tree):
    root = tree("pair")
    origin = next((runtime(root) / "origins").iterdir())
    runtime_report = json.loads((runtime(root) / "runtime_report.json").read_bytes())
    intent = json.loads((origin / "origin_intent.json").read_bytes())["slot"]["intent_id"]
    for folder in (origin / "fs2_capture_origin").iterdir():
        if not folder.is_dir():
            continue
        receipt = json.loads((folder / "receipt.json").read_bytes())
        if receipt["source_id"] != "clob.book":
            continue
        body = json.loads((folder / "raw.bin").read_bytes())
        body["asks"] = []
        raw = json.dumps(body).encode()
        (folder / "raw.bin").write_bytes(raw)
        receipt.update(raw_hash=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw))
        data = _json_bytes(receipt)
        (folder / "receipt.json").write_bytes(data)
        ack = json.loads((folder / "raw_ack.json").read_bytes())
        ack.update(raw_hash=receipt["raw_hash"], receipt_hash=hashlib.sha256(data).hexdigest())
        (folder / "raw_ack.json").write_bytes(_json_bytes(ack))
    assert intent in {o["intent_id"] for o in runtime_report["origins"]}
    edit(runtime(root), "runtime_report", lambda r: [
        o.update(state="one_sided_or_missing") for o in r["origins"] if o["intent_id"] == intent])
    report = evaluate(root)
    hit = [f for f in report["findings"] if f["rule"] == "origin_state:one_sided_or_missing"]
    assert hit and hit[0]["class"] == ev.DATA_SOURCE
    assert hit[0]["citation"]["empty_sides"] == ["asks"] and hit[0]["citation"]["raw_hash"]


def test_tampered_artifact_hash_is_engineering(tree):
    root = tree("pair")
    path = runtime(root) / "runtime_report.json"
    path.write_bytes(path.read_bytes() + b" ")
    report = evaluate(root)
    assert report["outcome"] == "FAIL" and "artifact:artifact_hash_mismatch" in rules(report)


def test_missing_runtime_report_fails(tree):
    root = tree("pair")
    (runtime(root) / "runtime_report.json").unlink()
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "artifact:missing_or_unreadable_artifact" in rules(report)


def test_panel_declared_before_frame_availability_fails_e2(tree):
    root = tree("pair")
    edit(root / PANEL, "panel_policy",
         lambda p: p.update(declared_at={"utc": "2000-01-01T00:00:00.000000Z"}))
    report = evaluate(root)
    assert not report["gates"]["E2"]["pass"] and report["outcome"] == "FAIL"


def test_frame_age_beyond_limit_fails_closed(tree):
    root = tree("pair")
    selection = root / "fs2_selection_panel_worker"
    path = selection / "fs2_frame_read_original" / "original_report.json"
    report = json.loads(path.read_bytes())
    report["interval_start"] = {"utc": "2000-01-01T00:00:00.000000Z"}
    path.write_bytes(_json_bytes(report))
    result = evaluate(root)
    assert not result["gates"]["E1"]["pass"]
    assert any("frame age" in r for r in result["gates"]["E1"]["reasons"])


# ---- pure decision table and classification table --------------------------------------------

def summary(**changes):
    base = {"n_members": 4, "engineering_findings": 0, "failed_gates": [], "common_mode": [],
            "complete_chains": 2, "authenticated_state_members": 2, "n_triggered_members": 1,
            "n_untriggered_members": 1, "n_unavailable_members": 0, "control_assignments": 1,
            "pairs_both_complete": 0, "strata_report_computed": True}
    return {**base, **changes}


@pytest.mark.parametrize("changes,outcome", [
    ({"pairs_both_complete": 1}, "PASS"),
    ({"engineering_findings": 1, "pairs_both_complete": 1}, "FAIL"),
    ({"failed_gates": ["E7"]}, "FAIL"),
    ({"common_mode": ["x"]}, "FAIL"),
    ({"complete_chains": 0}, "INCONCLUSIVE"),
    ({"authenticated_state_members": 0}, "INCONCLUSIVE"),
    ({"strata_report_computed": False}, "INCONCLUSIVE"),
    ({"n_triggered_members": 0, "control_assignments": 0},
     "PASS_WITH_LIMITATION:zero_triggered_control_matching_not_exercised"),
    ({"n_triggered_members": 4, "n_members": 4, "control_assignments": 0},
     "PASS_WITH_LIMITATION:all_triggered_no_control"),
    ({"n_triggered_members": 2, "n_members": 4, "n_untriggered_members": 0,
      "control_assignments": 0, "n_unavailable_members": 2},
     "PASS_WITH_LIMITATION:no_eligible_untriggered"),
    ({"control_assignments": 1}, "PASS_WITH_LIMITATION:pair_member_unobserved_data_reason"),
])
def test_decision_is_exhaustive(changes, outcome):
    assert ev.decide_outcome(summary(**changes))[0] == outcome


def test_table_covers_every_quote_state_the_code_can_emit():
    quote = ev.CLASSIFICATION_TABLE["quote_state"]
    assert (TARGET_ABSTENTIONS | {"observed", "closed"}) <= set(quote)
    assert {"market_closed", "identity_unresolved_at_receipt"} <= set(quote)
    for namespace, entries in ev.CLASSIFICATION_TABLE.items():
        for key, row in entries.items():
            assert row["class"] in {ev.OK, ev.DATA_SOURCE, ev.DATA_TRANSPORT, ev.ENGINEERING}, key
            assert row["basis"], (namespace, key)
            if row["class"] in ev.DATA_CLASSES:
                assert row["check"] in ev.CHECKS, (namespace, key)


def test_engineering_timing_states_are_never_data():
    table = ev.CLASSIFICATION_TABLE
    for key in ("late_origin", "late_persistence", "failed", "expired_before_request",
                "expired_during_requests", "receipt_stale_at_origin", "identity_stale_at_origin"):
        assert table["origin_state"][key]["class"] == ev.ENGINEERING
    for key in ("window_stale", "window_stale_at_freeze", "prior_quote_stale_at_freeze"):
        assert table["freeze_reason"][key]["class"] == ev.ENGINEERING
    for key in ("expired", "incomplete_evidence"):
        assert table["target_attempt_state"][key]["class"] == ev.ENGINEERING
    for key in ("input_window_stale", "assessment_stale"):
        assert table["assessment_reason"][key]["class"] == ev.ENGINEERING
    assert table["screening_state"]["not_assessed"]["class"] == ev.ENGINEERING
    assert Counter(r["class"] for r in table["quote_state"].values())[ev.ENGINEERING] >= 6
