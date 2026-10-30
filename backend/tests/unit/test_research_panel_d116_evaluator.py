"""D116 evaluator: gates, exhaustive classification, citation checks and the outcome classes.

Fixtures are real artifacts written by ``run_synthetic_window_pilot`` (loopback sockets, mock
HTTP). Faults are injected by editing retained JSON in a copy of the tree; the pair acknowledgement
is re-hashed so that the evaluator's own integrity check passes and the fault itself is judged.
"""

import asyncio
import hashlib
import importlib.util
import json
import shutil
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

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
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "Original code fixture",
    )
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
            body = {
                "asset_id": token,
                "market": row["conditionId"],
                "bids": [{"price": "0.4", "size": size_of(row)}],
                "asks": [{"price": "0.6", "size": "1"}],
            }
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
        await socket.send(
            json.dumps(
                {
                    "event_type": "book",
                    "asset_id": token,
                    "market": by_token[token]["conditionId"],
                    "bids": [{"price": "0.4", "size": "2"}],
                    "asks": [{"price": "0.6", "size": "1"}],
                }
            )
        )
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
    def make(name="pair", tag=""):
        target = tmp_path / (name + tag)
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
    # Test aid: every gate except E0 / frozen values; the report is never authoritative.
    report = ev.evaluate_d116_logic_only_test_aid(root / PANEL)
    assert report["authoritative"] is False and report["non_authoritative_logic_only"]
    json.dumps(report, sort_keys=True)  # must be JSON-serialisable and sortable
    return report


def rules(report):
    return {f["rule"] for f in report["findings"] if f["class"] == ev.ENGINEERING}


def runtime(root):
    return root / "fs2_runtime_worker"


def test_clean_pass_with_observed_matched_pair(tree):
    report = evaluate(tree("pair"))
    assert report["outcome"] == "PASS", report["outcome_reasons"]
    assert all(g["pass"] for name, g in report["gates"].items() if name != "E0")
    assert not report["gates"]["E0"]["pass"] and report["authoritative"] is False
    assert report["summary"]["complete_chains"] == 2
    assert report["summary"]["pairs_both_complete"] == 1
    pair = report["pairs"][0]
    assert {pair["triggered_market"], pair["control_market"]} == {"1", "2"}
    assert pair["both_complete"]
    assert report["finding_counts"].get("ENGINEERING", 0) == 0
    assert report["evaluator_version"] == "d116-evaluator-v3"
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
                entry.update(
                    effective_state="not_assessed", assessment=None, reasons=["not_assessed"]
                )

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
    cited = [
        f for f in report["findings"] if f["state"] == "source_error" and f["stage"] == "origin"
    ]
    assert cited and all(f["class"] == ev.DATA_TRANSPORT and f["citation"] for f in cited)


def test_zero_triggered_is_limitation(tree):
    report = evaluate(tree("none"))
    assert report["outcome"] == (
        "PASS_WITH_LIMITATION:zero_triggered_control_matching_not_exercised"
    )
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
    edit(
        runtime(root),
        "runtime_report",
        lambda r: r["origins"][0].update(state="one_sided_or_missing"),
    )
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
    edit(
        runtime(root),
        "runtime_report",
        lambda r: [
            o.update(state="one_sided_or_missing") for o in r["origins"] if o["intent_id"] == intent
        ],
    )
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
    edit(
        root / PANEL,
        "panel_policy",
        lambda p: p.update(declared_at={"utc": "2000-01-01T00:00:00.000000Z"}),
    )
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
    base = {
        "n_members": 4,
        "engineering_findings": 0,
        "failed_gates": [],
        "common_mode": [],
        "complete_chains": 2,
        "authenticated_state_members": 2,
        "n_triggered_members": 1,
        "n_untriggered_members": 1,
        "n_unavailable_members": 0,
        "control_assignments": 1,
        "pairs_both_complete": 0,
        "strata_report_computed": True,
        "control_pool_zero_in_triggered_strata": True,
    }
    return {**base, **changes}


@pytest.mark.parametrize(
    "changes,outcome",
    [
        ({"pairs_both_complete": 1}, "PASS"),
        ({"engineering_findings": 1, "pairs_both_complete": 1}, "FAIL"),
        ({"failed_gates": ["E7"]}, "FAIL"),
        ({"common_mode": ["x"]}, "FAIL"),
        ({"complete_chains": 0}, "INCONCLUSIVE"),
        ({"authenticated_state_members": 0}, "INCONCLUSIVE"),
        ({"strata_report_computed": False}, "INCONCLUSIVE"),
        (
            {"n_triggered_members": 0, "control_assignments": 0},
            "PASS_WITH_LIMITATION:zero_triggered_control_matching_not_exercised",
        ),
        (
            {"n_triggered_members": 4, "n_members": 4, "control_assignments": 0},
            "PASS_WITH_LIMITATION:all_triggered_no_control",
        ),
        (
            {
                "n_triggered_members": 2,
                "n_members": 4,
                "n_untriggered_members": 0,
                "control_assignments": 0,
                "n_unavailable_members": 2,
            },
            "PASS_WITH_LIMITATION:no_eligible_untriggered",
        ),
        ({"control_assignments": 1}, "PASS_WITH_LIMITATION:pair_member_unobserved_data_reason"),
        # no_eligible_untriggered needs an empty control pool in every stratum with a trigger
        (
            {
                "n_triggered_members": 2,
                "n_members": 4,
                "n_untriggered_members": 0,
                "control_assignments": 0,
                "n_unavailable_members": 2,
                "control_pool_zero_in_triggered_strata": False,
            },
            "FAIL",
        ),
    ],
)
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
    for key in (
        "late_origin",
        "late_persistence",
        "failed",
        "expired_before_request",
        "expired_during_requests",
        "receipt_stale_at_origin",
        "identity_stale_at_origin",
    ):
        assert table["origin_state"][key]["class"] == ev.ENGINEERING
    for key in ("window_stale", "window_stale_at_freeze", "prior_quote_stale_at_freeze"):
        assert table["freeze_reason"][key]["class"] == ev.ENGINEERING
    for key in ("expired", "incomplete_evidence"):
        assert table["target_attempt_state"][key]["class"] == ev.ENGINEERING
    for key in ("input_window_stale", "assessment_stale"):
        assert table["assessment_reason"][key]["class"] == ev.ENGINEERING
    assert table["screening_state"]["not_assessed"]["class"] == ev.ENGINEERING
    assert Counter(r["class"] for r in table["quote_state"].values())[ev.ENGINEERING] >= 6


# ---- review round 2: run identity (E0), common mode, citations, fail-closed gates ------------

LIVE = "fs2_panel_d116_integrated_1"
ROOT_RENAMES = {
    "fs2_panel_worker": LIVE,
    "fs2_selection_panel_worker": "fs2_selection_panel_d116_integrated_1",
    "fs2_screening_worker_worker": "fs2_screening_worker_d116_integrated_1",
    "fs2_activation_worker": "fs2_activation_d116_integrated_1",
    "fs2_runtime_worker": "fs2_runtime_d116_integrated_1",
}
PROVENANCE_KEYS = {"provenance_class", "source_provenance_class", "original_provenance_class"}


def fixture_commit(root: Path):
    policy = json.loads((root / PANEL / "panel_policy.json").read_bytes())
    return policy["frame_implementation_commit"]


def _live_value(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in PROVENANCE_KEYS and value == "synthetic":
                node[key] = "prospective"
            elif key == "kind" and value == "loopback":
                node[key] = "public"
            else:
                _live_value(value)
    elif isinstance(node, list):
        for item in node:
            _live_value(item)


def make_live_identity(root: Path):
    """Rewrite a synthetic tree so every E0 identity check can pass (tests the pass path only).

    The tree stays a fixture: E1 frozen values, E2 and others still judge it."""
    for path in sorted(root.rglob("*.json")):
        if path.name.endswith("_ack.json"):
            continue
        payload = json.loads(path.read_bytes())
        before = json.dumps(payload, sort_keys=True)
        _live_value(payload)
        if json.dumps(payload, sort_keys=True) == before:
            continue
        data = _json_bytes(payload)
        path.write_bytes(data)
        ack = path.with_name(path.stem + "_ack.json")
        if ack.exists() and "payload_hash" in json.loads(ack.read_bytes()):
            record = json.loads(ack.read_bytes())
            record["payload_hash"] = hashlib.sha256(data).hexdigest()
            ack.write_bytes(_json_bytes(record))
    for old, new in ROOT_RENAMES.items():
        (root / old).rename(root / new)
    return root / LIVE


def live_tree(tree):
    root = tree("pair")
    commit = fixture_commit(root)
    return root, make_live_identity(root), commit


def test_synthetic_tree_fails_identity_gate_and_is_not_authoritative(tree):
    root = tree("pair")
    report = ev.evaluate_d116(root / PANEL, launch_commit=fixture_commit(root))
    assert report["outcome"] == "FAIL" and report["authoritative"] is False
    e0 = report["gates"]["E0"]
    assert not e0["pass"]
    joined = " ".join(e0["reasons"])
    assert "panel root name" in joined and "provenance is not prospective" in joined
    assert "loopback" in joined
    assert "failed gates: E0" in " ".join(report["outcome_reasons"])
    # E2 fails closed when the temporal population count is absent
    e2 = report["gates"]["E2"]["reasons"]
    assert any("selection_eligible_member_count absent" in r for r in e2)
    assert "synthetic" not in json.dumps(report["gates"]["E1"]["reasons"])


def test_missing_launch_commit_fails_closed(tree):
    root = tree("pair")
    report = ev.evaluate_d116(root / PANEL)
    assert report["outcome"] == "FAIL" and not report["authoritative"]
    assert any("launch commit absent" in r for r in report["gates"]["E0"]["reasons"])


def test_e0_passes_only_for_frozen_names_commits_schema_and_live_provenance(tree):
    root, panel, commit = live_tree(tree)
    report = ev.evaluate_d116(panel, launch_commit=commit)
    assert report["gates"]["E0"]["pass"], report["gates"]["E0"]["reasons"]
    assert report["authoritative"] is True  # identity proven; the fixture still fails E1/E2 values
    assert report["outcome"] == "FAIL" and not report["gates"]["E1"]["pass"]
    assert any("strata_limit" in r for r in report["gates"]["E1"]["reasons"])
    assert report["required_ancestor_commit"] == "8afbdff"
    assert report["launch_commit"] == commit


def test_e0_rejects_wrong_commit_schema_provenance_and_root_names(tree):
    root, panel, commit = live_tree(tree)
    assert not ev.evaluate_d116(panel, launch_commit="0" * 40)["gates"]["E0"]["pass"]
    assert not ev.evaluate_d116(panel, launch_commit=commit.upper())["gates"]["E0"]["pass"]

    selection = root / "fs2_selection_panel_d116_integrated_1"
    edit(selection, "selection_policy", lambda p: p.update(implementation_commit="1" * 40))
    report = ev.evaluate_d116(panel, launch_commit=commit)
    assert not report["gates"]["E0"]["pass"] and not report["authoritative"]
    e0 = report["gates"]["E0"]["reasons"]
    assert any("selection_policy.implementation_commit" in r for r in e0)
    edit(selection, "selection_policy", lambda p: p.update(implementation_commit=commit))

    batch = root / "fs2_screening_worker_d116_integrated_1" / "fs2_screening_batch"
    edit(batch, "screening_report", lambda p: p.update(schema_version="fs2-screening-v1"))
    report = ev.evaluate_d116(panel, launch_commit=commit)
    assert any("schema" in r for r in report["gates"]["E0"]["reasons"])
    edit(batch, "screening_report", lambda p: p.update(schema_version=ev.REQUIRED_SCREENING_SCHEMA))

    edit(runtime_live(root), "runtime_report", lambda p: p.update(provenance_class="synthetic"))
    report = ev.evaluate_d116(panel, launch_commit=commit)
    assert any("runtime_report" in r for r in report["gates"]["E0"]["reasons"])

    moved = panel.with_name("fs2_panel_other")
    panel.rename(moved)
    assert not ev.evaluate_d116(moved, launch_commit=commit)["gates"]["E0"]["pass"]


def runtime_live(root):
    return root / "fs2_runtime_d116_integrated_1"


def test_e0_rejects_synthetic_socket_and_read_receipt(tree):
    root, panel, commit = live_tree(tree)
    worker = root / "fs2_screening_worker_d116_integrated_1"
    edit(
        worker / "fs2_runtime_read_batch",
        "read_receipt",
        lambda p: p.update(original_provenance_class="synthetic"),
    )
    edit(
        worker / "fs2_socket_window_000",
        "socket_window_report",
        lambda p: p.update(provenance_class="synthetic"),
    )
    reasons = " ".join(ev.evaluate_d116(panel, launch_commit=commit)["gates"]["E0"]["reasons"])
    assert "read_receipt.original_provenance_class" in reasons and "socket_report" in reasons


def test_override_flags_force_fail_and_are_recorded(tree):
    root, panel, commit = live_tree(tree)
    base = ev.evaluate_d116(panel, launch_commit=commit)
    assert base["authoritative"] is True
    for kwargs in (
        {"protocol_check": False},
        {"selection_root": root / "fs2_selection_panel_d116_integrated_1"},
        {"worker_root": root / "fs2_screening_worker_d116_integrated_1"},
        {"runtime_root": runtime_live(root)},
        {"activation_root": root / "fs2_activation_d116_integrated_1"},
    ):
        report = ev.evaluate_d116(panel, launch_commit=commit, **kwargs)
        assert report["outcome"] == "FAIL" and report["authoritative"] is False
        assert report["test_override_used"]
        assert report["outcome_reasons"][0].startswith("test_override_used")


def _load_cli():
    path = Path(__file__).parents[2] / "scripts" / "evaluate_d116.py"
    spec = importlib.util.spec_from_file_location("evaluate_d116_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_requires_launch_commit_and_never_authoritative_on_synthetic(tree, tmp_path, capsys):
    cli = _load_cli()
    root = tree("pair")
    with pytest.raises(SystemExit):
        cli.main([str(root / PANEL), "--out", str(tmp_path / "a.json")])
    out = tmp_path / "report.json"
    assert (
        cli.main(
            [
                str(root / PANEL),
                "--launch-commit",
                fixture_commit(root),
                "--no-protocol-check",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_bytes())
    assert report["outcome"] == "FAIL" and report["authoritative"] is False
    assert report["outcome_reasons"][0].startswith("test_override_used")
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["authoritative"] is False
    with pytest.raises(SystemExit):
        cli.main([str(root / PANEL), "--launch-commit", "x", "--out", str(out)])  # exists


def test_exception_yields_fail_report(tree, monkeypatch):
    root = tree("pair")

    def boom(self):
        raise RuntimeError("secret detail must not leak")

    monkeypatch.setattr(ev._Evaluation, "run", boom)
    report = ev.evaluate_d116(root / PANEL, launch_commit=fixture_commit(root))
    assert report["outcome"] == "FAIL" and report["authoritative"] is False
    assert report["outcome_reasons"] == ["evaluator_exception:RuntimeError"]
    assert "secret" not in json.dumps(report)
    json.dumps(report, sort_keys=True)
    # an unreadable root also yields a FAIL report, never an exception
    missing = ev.evaluate_d116(root / "nowhere", launch_commit="a" * 40)
    assert missing["outcome"] == "FAIL"


# ---- common-mode guard (pure) ------------------------------------------------------------------


def member(
    complete=False, stage="origin", state="one_sided_or_missing", cls=ev.DATA_SOURCE, failing=False
):
    return {
        "complete": complete,
        "limiting": None if complete else {"stage": stage, "state": state, "class": cls},
        "listed_market_failure": failing,
    }


def test_two_one_sided_among_eight_is_a_data_outcome_not_common_mode():
    rows = [member(), member()] + [member(complete=True) for _ in range(6)]
    assert ev.common_mode_flags(rows) == []
    # two identical causes among otherwise different incomplete members: not common mode
    rows = [member(), member()] + [member(state=f"other_{i}") for i in range(6)]
    assert ev.common_mode_flags(rows) == []


def test_common_mode_rule_a_same_stage_state_everywhere_no_complete_chain():
    rows = [member(stage="screening", state="x") for _ in range(8)]
    assert any("same cause" in f for f in ev.common_mode_flags(rows))
    assert ev.common_mode_flags([member()]) == []  # a single member is not "same cause"
    # one complete chain defeats (a)
    assert ev.common_mode_flags([member(complete=True)] + [member() for _ in range(7)]) == []
    # different stage with the same state is a different cause
    rows = [member(stage="window"), member(stage="origin")]
    assert ev.common_mode_flags(rows) == []


def test_common_mode_rule_b_all_transport_limiting():
    rows = [member(state=f"s{i}", cls=ev.DATA_TRANSPORT) for i in range(8)]
    assert any("transport failure" in f for f in ev.common_mode_flags(rows))
    rows[0] = member(complete=True)
    assert ev.common_mode_flags(rows) == []


def test_common_mode_rule_c_half_with_transport_or_4xx():
    rows = [member(complete=True, failing=i < 4) for i in range(8)]
    assert any("4 of 8" in f for f in ev.common_mode_flags(rows))
    rows = [member(complete=True, failing=i < 3) for i in range(8)]
    assert ev.common_mode_flags(rows) == []


def test_common_mode_counts_screening_and_window_causes(tree):
    root = tree("down")  # fixture built lazily below; causes are screening-stage transport errors
    report = evaluate(root)
    assert any("'screening'" in f for f in report["common_mode"])
    assert {m["causes"][0]["stage"] for m in report["members"].values()} == {"screening"}


# ---- citation: invalid ---------------------------------------------------------------------------


def receipt(status, body, source_id="clob.book", token="7", market="1", **extra):
    fields = {
        "raw_verified": True,
        "transport_error": None,
        "status": status,
        "token_id": token,
        "market_id": market,
        "body": lambda: body,
        "raw_text": b"not json" if body is None else json.dumps(body).encode(),
    }
    fields.update(extra)
    return SimpleNamespace(**fields)


COND = "0x" + "c" * 64
GOOD_BOOK = {"asset_id": "7", "market": COND, "bids": [], "asks": []}


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (404, GOOD_BOOK, True),
        (400, None, True),
        (422, {"x": 1}, True),
        (401, None, False),
        (403, None, False),
        (429, None, False),
        (200, GOOD_BOOK, False),  # valid book: not invalid
        (200, None, True),  # not JSON
        (200, {"bids": [], "asks": []}, True),  # asset_id missing
        (200, {"asset_id": "8", "bids": [], "asks": []}, True),  # not the requested token
        (200, {"asset_id": "7", "bids": []}, True),  # asks missing
        (200, {**GOOD_BOOK, "bids": [{"price": "1.5", "size": "1"}]}, True),  # price out of range
        (301, GOOD_BOOK, False),
        (500, None, False),
        (None, None, False),
    ],
)
def test_invalid_citation_book(status, body, expected):
    assert ev._invalid_supported(receipt(status, body), "clob.book") is expected


def test_invalid_citation_gamma_and_unverified_raw():
    good = {"id": "1", "conditionId": COND, "clobTokenIds": '["7"]', "outcomes": '["Yes"]'}
    assert ev._invalid_supported(receipt(200, good), "gamma.market") is False
    assert ev._invalid_supported(receipt(200, {"id": "1", "conditionId": COND}), "gamma.market")
    assert not ev._invalid_supported(receipt(404, None, raw_verified=False), "gamma.market")
    assert not ev._invalid_supported(receipt(404, None, transport_error="x"), "gamma.market")


def test_invalid_verdict_records_parser_exception():
    ok, exc = ev._invalid_verdict(receipt(200, None), "clob.book")
    assert ok and exc and exc.split(":")[0].endswith("Error")
    assert ev._invalid_verdict(receipt(200, GOOD_BOOK), "clob.book") == (False, None)


def test_two_xx_invalid_with_valid_book_body_is_engineering(tree):
    root = tree("pair")
    edit(runtime(root), "runtime_report", lambda r: r["origins"][0].update(state="invalid"))
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert "citation_failed:http_invalid:origin_state:invalid" in rules(report)


def test_not_decimal_excludes_zero_size_and_counts_non_finite():
    def ctx(levels):
        r = receipt(200, {"asset_id": "7", "bids": levels, "asks": []}, ok2xx=True)
        r.cite = lambda: {}
        return {"receipts": {"clob.book": [r]}}

    zero = ctx([{"price": "0.4", "size": "0"}])
    assert ev._chk_non_decimal(zero, {})[0] is False
    for bad in (
        {"price": "x", "size": "1"},
        {"price": "NaN", "size": "1"},
        {"price": "0.4", "size": "Infinity"},
    ):
        assert ev._chk_non_decimal(ctx([bad]), {})[0] is True


def test_token_or_condition_mismatch_is_engineering_not_data():
    mapping = {"market_id": "1", "outcome_index": 0, "outcome_label": "Yes"}
    member_ = {
        "token_id": "7",
        "condition_id": "0xc",
        "market_id": "1",
        "outcome_index": 0,
        "outcome_label": "Yes",
    }
    quote = {"token_id": "7", "condition_id": "0xc", "mapping": mapping}
    base = {
        "member": member_,
        "quote": quote,
        "identity_comparison": {"core_identity_equal": True, "state": "x"},
    }
    assert ev._chk_origin_mapping(base, {})[0] is False  # nothing differs
    for field in ("token_id", "condition_id"):
        ctx = {**base, "quote": {**base["quote"], field: "other"}}
        assert ev._chk_origin_mapping(ctx, {})[0] is False
    ctx = {**base, "quote": {**base["quote"], "mapping": {**mapping, "market_id": "2"}}}
    assert ev._chk_origin_mapping(ctx, {})[0] is True
    pre = {
        "member": member_,
        "identity": {"condition_id": "0xc"},
        "pre_quote": {"token_id": "7", "condition_id": "0xc", "mapping": mapping},
    }
    assert ev._chk_pre_identity(pre, {})[0] is False
    other_token = {**pre["pre_quote"], "token_id": "9"}
    assert ev._chk_pre_identity({**pre, "pre_quote": other_token}, {})[0] is False
    changed = {**pre["pre_quote"], "mapping": {**mapping, "market_id": "2"}}
    assert ev._chk_pre_identity({**pre, "pre_quote": changed}, {})[0] is True


# ---- fail-closed gates -------------------------------------------------------------------------


def screening_batch(root):
    return root / "fs2_screening_worker_worker" / "fs2_screening_batch"


def test_sampling_underfill_of_controls_fails_e5(tree):
    root = tree("pair")

    def mutate(report):
        stratum = report["plan"]["strata"][0]
        stratum.update(controls_selected=0, unfilled_control_slots=1)

    edit(screening_batch(root), "screening_report", mutate)
    report = evaluate(root)
    assert report["outcome"] == "FAIL" and not report["gates"]["E5"]["pass"]
    assert any("min(controls_wanted, control_pool)" in r for r in report["gates"]["E5"]["reasons"])


def test_triggered_member_without_triggered_assignment_fails_e5(tree):
    root = tree("pair")

    def mutate(report):
        report["plan"]["assignments"] = [
            a for a in report["plan"]["assignments"] if a["arm"] != "triggered"
        ]

    edit(screening_batch(root), "screening_report", mutate)
    report = evaluate(root)
    assert not report["gates"]["E5"]["pass"]
    assert any("no triggered assignment" in r for r in report["gates"]["E5"]["reasons"])


def test_unauthenticated_triggered_state_is_not_counted_as_triggered(tree):
    root = tree("pair")

    def mutate(report):
        for entry in report["plan"]["assessment_inventory"]:
            if entry["effective_state"] == "triggered":
                entry["assessment"]["evidence_id"] = "not-a-hash"

    edit(screening_batch(root), "screening_report", mutate)
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert report["summary"]["n_triggered_members"] == 0
    assert "artifact:missing_or_unreadable_artifact" in rules(report)


def test_finish_duration_missing_clock_fails_e3_and_uses_frozen_600(tree):
    root = tree("pair")
    edit(screening_batch(root), "screening_completion_policy", lambda p: p.pop("read_started_at"))
    report = evaluate(root)
    assert not report["gates"]["E3"]["pass"]
    assert any("clocks missing" in r for r in report["gates"]["E3"]["reasons"])
    root = tree("pair", "2")
    edit(screening_batch(root), "screening_policy", lambda p: p["limits"].update(max_seconds=10**6))
    edit(
        screening_batch(root),
        "screening_completion_policy",
        lambda p: p.update(read_started_at={"utc": "2000-01-01T00:00:00.000000Z"}),
    )
    report = evaluate(root)
    assert any("exceeds 600" in r for r in report["gates"]["E3"]["reasons"])
    assert ev.FROZEN_EXPECTATIONS["screening_max_seconds"] == 600


def test_read_receipt_must_match_recovery_and_pass_hash_check(tree):
    root = tree("pair")
    batch = root / "fs2_screening_worker_worker" / "fs2_runtime_read_batch"
    edit(batch, "read_receipt", lambda p: p.update(output_hash="0" * 64))
    report = evaluate(root)
    assert not report["gates"]["E8"]["pass"]
    assert any("differs from worker_report recovery" in r for r in report["gates"]["E8"]["reasons"])
    root = tree("pair", "2")
    path = root / "fs2_screening_worker_worker" / "fs2_runtime_read_batch" / "read_receipt.json"
    path.write_bytes(path.read_bytes() + b" ")
    report = evaluate(root)
    assert "artifact:artifact_hash_mismatch" in rules(report) and not report["gates"]["E8"]["pass"]


def test_socket_event_hash_is_verified(tree):
    root = tree("pair")
    event = root / "fs2_screening_worker_worker" / "fs2_socket_window_000" / "event_000002.json"
    event.write_bytes(event.read_bytes() + b" ")
    report = evaluate(root)
    assert report["outcome"] == "FAIL" and "artifact:artifact_hash_mismatch" in rules(report)
    root = tree("pair", "2")
    frame = root / "fs2_screening_worker_worker" / "fs2_socket_window_000" / "event_000003.bin"
    frame.write_bytes(frame.read_bytes() + b" ")
    assert "artifact:artifact_hash_mismatch" in rules(evaluate(root))


def test_socket_event_missing_frame_is_engineering(tree):
    root = tree("pair")
    frame = root / "fs2_screening_worker_worker" / "fs2_socket_window_000" / "event_000003.bin"
    frame.unlink()
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert any(
        "raw frame event_000003.bin missing" in (f["detail"] or "") for f in report["findings"]
    )


def test_socket_event_ordinal_gap_is_engineering(tree):
    root = tree("pair")
    folder = root / "fs2_screening_worker_worker" / "fs2_socket_window_000"
    (folder / "event_000002.json").unlink()
    (folder / "event_000002_ack.json").unlink()
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert any("not contiguous" in (f["detail"] or "") for f in report["findings"])


def test_cli_resolves_relative_panel_root_and_refuses_symlink(tree, tmp_path, monkeypatch):
    cli = _load_cli()
    root = tree("pair")
    monkeypatch.chdir(root)
    out = tmp_path / "rel.json"
    assert (
        cli.main(
            [
                PANEL,
                "--launch-commit",
                fixture_commit(root),
                "--no-protocol-check",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_bytes())
    assert not any(r.startswith("evaluator_exception") for r in report["outcome_reasons"])
    link = tmp_path / "link"
    link.symlink_to(root / PANEL)
    with pytest.raises(SystemExit):
        cli.main([str(link), "--launch-commit", "a" * 40, "--out", str(tmp_path / "x.json")])


def test_target_folder_matching_no_origin_is_engineering(tree):
    root = tree("pair")
    folder = next((runtime(root) / "targets").iterdir())
    edit(folder, "target_intent", lambda p: p["job"].update(origin_id="f" * 64))
    report = evaluate(root)
    assert report["outcome"] == "FAIL"
    assert any("matches no origin" in (f["detail"] or "") for f in report["findings"])


def test_frozen_constants_match_the_code_they_cite():
    from astrolabe.research_panel import screening
    from astrolabe.research_panel.panel_declaration import TEMPORAL_POPULATION

    frozen = ev.FROZEN_EXPECTATIONS
    assert ev.REQUIRED_SCREENING_SCHEMA == screening.OWNED_VERSION
    assert screening.LIMITS["max_seconds"] == frozen["screening_max_seconds"] == 600
    assert frozen["panel"] == {"strata_limit": 4, "population_policy": TEMPORAL_POPULATION}
    protocol = ev.D116_PROTOCOL
    assert protocol["scheduled_per_stratum"] == protocol["triggered_per_stratum"] == 2
    assert frozen["worker"]["rule"]["max_age_ms"] == 60000
    assert frozen["worker"]["freshness"] == {
        "max_window_age_seconds": 120,
        "max_assessment_age_seconds": 120,
    }
    assert frozen["worker"]["window_policy"]["binding_mode"] == "observation"
    assert ev.FROZEN_PANEL_NAME == "fs2_panel_d116_integrated_1"
