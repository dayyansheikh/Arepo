# ruff: noqa: E501
"""CB16 runner (offline; synthetic files only; the network is replaced by fakes, never used)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb13_common as c13
from astrolabe.research_lab import cb16_common as c16
from tests.cb16_synth import FREEZE_UTC, S_A, make_cb13_screen_world, make_window_world, write_pin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb16  # noqa: E402

AFTER_SCREEN = S_A + 14 * 86400 + 9 * 3600  # q0384 gate: S_A + 14 d + 8 h
AFTER_E011 = AFTER_SCREEN  # the screen gate (S_A + 14 d + 8 h = 11-16 08:00Z) is later than E011's analysis date (>= 11-11 13:00Z)


def _run(argv, capsys):
    code = run_cb16.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


@pytest.fixture()
def env(tmp_path):
    rules = tmp_path / "cb16_rules.json"
    c16.write_rules(rules)
    spec = tmp_path / "cb16_v1.json"
    spec.write_text(json.dumps({"A": {"rules_sha256": c16.rules_part_file_doc("A")["rules_sha256"], "common_rules_sha256": c16.rules_part_file_doc("common")["rules_sha256"], "frozen_utc": FREEZE_UTC}}))
    w = make_window_world(tmp_path)
    cb13 = make_cb13_screen_world(tmp_path)
    (tmp_path / "history").mkdir()
    (tmp_path / "seals").mkdir()
    pin = write_pin(tmp_path)
    return {"tmp": tmp_path, "rules": rules, "spec": spec, "world": w, "cb13": cb13, "pin": pin, "root": tmp_path / "creative_batch16", "trials": tmp_path / "trials.jsonl"}


def base(env, *, cb13=True):
    t = env["tmp"]
    a = ["--root", str(env["root"]), "--history-root", str(t / "history"), "--trades-dir", str(t / "live_trades"), "--snapshot-dir", str(t / "snapshots"), "--sweep-dir", str(t / "book_sweeps"),
         "--cross-venue-dir", str(t / "cross_venue"), "--seals-dir", str(t / "seals"), "--j4r-pin", str(env["pin"]), "--rules", str(env["rules"]), "--freeze-spec", str(env["spec"]),
         "--allow-uncommitted-rules", "--trials-path", str(env["trials"]), "--data-dumps", str(t / "dd"), "--standalone"]
    return a


def smoke_args(env):
    return ["--cb13-trades-dir", str(env["cb13"]["trades"]), "--cb13-snapshot-dir", str(env["cb13"]["snap"])]


def trial_lines(env):
    return [json.loads(x) for x in env["trials"].read_text().splitlines()] if env["trials"].exists() else []


def counted(env):
    return sum(x["n_tests"] for x in trial_lines(env) if x["kind"] == "ml_explain")


def test_rules_freeze_part_and_declared_arguments(env, capsys, tmp_path):
    code, out = _run(["rules", "--path", str(tmp_path / "r2.json")], capsys)
    assert code == 0 and set(out["parts"]) == {"common", "A", "K"} and out["parts"]["A"]["declared"] and out["parts"]["K"]["declared"] is False
    code, out = _run(["freeze-part", "--part", "A"], capsys)
    assert code == 0 and out["entry"]["rules_sha256"] and out["entry"]["common_rules_sha256"]
    a = base(env)
    code, out = _run(["a-frame", "--window", "screen", *a, "--disk-cap-gb", "0.5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["exclusion-keys", *a, "--rps", "5"], capsys)
    assert code == 2 and "rps" in out["refused"]
    code, out = _run(["u-validity", *a, "--seed", "1"], capsys)
    assert code == 2 and "seed" in out["refused"]
    code, out = _run(["exclusion-keys", *a], capsys)  # the CB15 key file sha256 pin is mandatory
    assert code == 2 and "sha256" in out["refused"]
    code, out = _run(["k-census", *a], capsys)  # part K is undeclared until the matches_all.json pin is set
    assert code == 2 and "not declared" in out["refused"]
    code, out = _run(["a-frame", "--window", "screen", *a], capsys)  # no smoke yet
    assert code == 2 and "smoke" in out["refused"]
    with pytest.raises(c16.Refused, match="test hook"):
        run_cb16._test_only(type("A", (), {"now": 5.0, "allow_uncommitted_rules": False})(), "now")


def test_smoke_a_passes_is_write_once_and_k_is_refused_while_undeclared(env, capsys):
    a = base(env)
    code, out = _run(["smoke", "--parts", "A", *a, *smoke_args(env)], capsys)
    assert code == 0 and out["smoke"] is True and out["pass_by_part"] == {"A": True}, out
    doc = json.loads((env["root"] / "smoke.json").read_text())
    assert doc["requests"] == 0 and doc["counts_only"] and doc["pass"] and doc["detail"]["a_cb13_reproduction"]["pinned_counts"] == doc["detail"]["a_cb13_reproduction"]["independent_counts"]
    code, out = _run(["smoke", "--parts", "A", *a, *smoke_args(env)], capsys)
    assert code == 2 and "write-once" in out["refused"]
    code, out = _run(["smoke", "--parts", "K", "--out", str(env["root"] / "smoke_k.json"), *a], capsys)
    assert code == 2 and "not declared" in out["refused"]
    assert counted(env) == 0 and {x["kind"] for x in trial_lines(env)} == {"cb16_descriptive"}


def test_a_failed_smoke_counts_q1_and_u1_once_and_makes_the_family_terminal(env, capsys, tmp_path):
    a = base(env)
    empty = tmp_path / "empty13"
    code, out = _run(["smoke", "--parts", "A", *a, "--cb13-trades-dir", str(empty / "live_trades"), "--cb13-snapshot-dir", str(empty / "snapshots")], capsys)
    assert code == 0 and out["smoke"] is False and sorted(out["counted_not_testable_source"]) == ["Q", "U"]
    assert counted(env) == 2
    lines = trial_lines(env)
    assert [x["p"] for x in lines if x["kind"] == "cb16_test"] == [1.0, 1.0]
    code, out = _run(["a-frame", "--window", "screen", *a, "--smoke", str(env["root"] / "smoke.json"), "--now", str(AFTER_SCREEN)], capsys)
    assert code == 2  # the smoke criteria are not met
    code, out = _run(["smoke", "--parts", "A", *a, "--out", str(env["root"] / "smoke2.json"), *smoke_args(env)], capsys)
    assert code == 0 and "terminal" in json.dumps(out) and counted(env) == 2  # nothing is counted again


def test_grain_census_gqg_failure_counts_q1_once(env, capsys):
    a = base(env)
    _run(["smoke", "--parts", "A", *a, *smoke_args(env)], capsys)
    code, out = _run(["q-grain-census", *a, *smoke_args(env)], capsys)
    assert code == 0 and out["status"] == "grain_census_complete" and out["gqg"] is False and out["terminal"]["Q"] == "not testable (grain)"
    doc = json.loads((env["root"] / "census_Q_grain.json").read_text())
    assert doc["counts_only"] and doc["Q"]["gqg"]["counts_only"]
    assert counted(env) == 1
    code, out = _run(["q-grain-census", *a, *smoke_args(env)], capsys)
    assert code == 2 and "written once" in out["refused"]


def test_full_chain_frame_census_screen_rep_and_stage2_final(env, capsys):
    a = base(env)
    code, out = _run(["smoke", "--parts", "A", *a, *smoke_args(env)], capsys)
    assert code == 0 and out["smoke"] is True
    # the frame waits for S_A + 14 d + 8 h (exit 75), then runs
    code, out = _run(["a-frame", "--window", "screen", *a, "--now", str(S_A + 14 * 86400)], capsys)
    assert code == 75 and "pending" in out["science"]
    code, out = _run(["a-frame", "--window", "screen", *a, "--now", str(AFTER_SCREEN)], capsys)
    assert code == 0 and out["status"] == "a_frame_complete" and out["n_fills"] > 0, out
    code, out = _run(["a-frame", "--window", "screen", *a, "--now", str(AFTER_SCREEN)], capsys)
    assert out.get("already_complete") is True
    code, out = _run(["census", "--family", "A", *a], capsys)
    assert code == 0 and out["status"] == "census_complete" and out["gq"] is False
    cen = json.loads((env["root"] / "census_A.json").read_text())["A"]
    assert cen["counts_only"] and '"est"' not in json.dumps(cen)
    code, out = _run(["census", "--family", "A", *a], capsys)
    assert code == 2 and "written once" in out["refused"]
    # a tampered fill table refuses (every job re-hashes the manifest)
    fp = env["root"] / "a_screen" / "fills.csv.gz"
    good = fp.read_bytes()
    fp.write_bytes(good + b"x")
    code, out = _run(["census", "--family", "A", *a, "--out", str(env["root"] / "census_A2.json")], capsys)
    assert code == 2
    fp.write_bytes(good)
    # screen: the freeze first, then the E011 hold and the CB3 hold (exit 75), then it counts Q1 and U1 with p = 1 behind the failed GQ / GU gates
    code, out = _run(["screen", "--family", "A", *a, "--freeze-spec", str(env["tmp"] / "nofreeze.json"), "--now", str(AFTER_E011)], capsys)
    assert code == 2 and "freeze" in out["refused"]
    code, out = _run(["screen", "--family", "A", *a, "--now", str(S_A + 14 * 86400 + 3600)], capsys)
    assert code == 75 and "not before" in out["tempfail"]
    code, out = _run(["screen", "--family", "A", *a, "--now", str(AFTER_E011)], capsys)
    assert code == 75 and "E011" in out["tempfail"]
    assert c16.e011_hold_lifted.__doc__ and c16.E011_ANALYSIS_EARLIEST == "2026-11-11T13:00:00Z"
    e011 = env["tmp"] / "e011_analysis_commit.json"
    e011.write_text(json.dumps({"e011_analysis_commit": "abc123"}))
    code, out = _run(["screen", "--family", "A", *a, "--now", str(AFTER_E011), "--e011-record", str(e011)], capsys)
    assert code == 75 and "CB3" in out["tempfail"]
    stop = env["tmp"] / "cb3_stop.json"
    stop.write_text(json.dumps({"cb3_stop": c13.CB3_STOP_TOKEN}))
    code, out = _run(["screen", "--family", "A", *a, "--now", str(AFTER_E011), "--e011-record", str(e011), "--cb3-stop", str(stop), "--cb3-spec-dir", str(env["tmp"] / "nospecs"), "--draws", "3"], capsys)
    assert code == 0 and out["status"] == "screen_A_complete" and out["Q1"]["verdict"] == "not testable (population)" and out["U1"]["verdict"] == "not testable (population)", out
    res = json.loads((env["root"] / "results_A.json").read_text())
    assert res["Q1"]["testable"] is False and res["U1"]["advance"] is False and res["e011_hold"]["lifted_by"] == "e011_analysis_commit" and res["cb3_hold"]["lifted_by"] == "cb3_stop_record"
    assert counted(env) == 2  # both counted with p = 1 (population gate)
    assert {x["kind"] for x in trial_lines(env)} == {"cb16_descriptive", "cb16_test", "ml_explain"}
    sha = run_cb16.hashlib.sha256((env["root"] / "results_A.json").read_bytes()).hexdigest()
    # rep: the committed copy of results_A.json is required before any REP_A row is opened
    code, out = _run(["rep", "--family", "A", *a, "--results-sha256", sha, "--now", str(S_A + 29 * 86400), "--cb3-stop", str(stop), "--cb3-spec-dir", str(env["tmp"] / "nospecs")], capsys)
    assert code == 75 and "copy" in out["tempfail"]
    (env["tmp"] / "seals" / run_cb16.RESULTS_COPY_NAME).write_bytes((env["root"] / "results_A.json").read_bytes())
    code, out = _run(["rep", "--family", "A", *a, "--results-sha256", sha, "--now", str(S_A + 29 * 86400), "--cb3-stop", str(stop), "--cb3-spec-dir", str(env["tmp"] / "nospecs")], capsys)
    assert code == 0 and out["status"] == "rep_A_not_triggered"
    code, out = _run(["rep", "--family", "A", *a, "--results-sha256", "00", "--now", str(S_A + 29 * 86400)], capsys)
    assert code == 2 and "differs" in out["refused"]
    code, out = _run(["stage2-final", *a], capsys)
    assert code == 2 and "nothing to finalise" in out["refused"]
    # u-validity with a fake Data API (the real transport is never constructed)
    class Lim:
        requests = 0

        def get(self, url, params):
            self.requests += 1
            return 200, [{"timestamp": S_A + 100.0, "price": 0.5, "size": 1, "conditionId": params["market"], "side": "BUY", "proxyWallet": "0xw"}]

    run_cb16._limiter = lambda a_, rps, **kw: Lim()
    code, out = _run(["u-validity", *a], capsys)
    assert code == 0 and out["status"] == "u_validity_complete"
    vdoc = json.loads((env["root"] / "u_validity" / "result.json").read_text())
    assert vdoc["reported_only"] and "side" not in json.dumps(vdoc) and "proxyWallet" not in json.dumps(vdoc)
    sample = json.loads((env["root"] / "u_validity" / "sample.json").read_text())
    assert sample["seed"] == 16131 and set(sample["sample"]) == {"wake", "non_wake"}
    code, out = _run(["u-validity", *a], capsys)
    assert out.get("already_complete") is True


def test_rep_frame_needs_the_screen_result_and_its_committed_copy(env, capsys):
    a = base(env)
    _run(["smoke", "--parts", "A", *a, *smoke_args(env)], capsys)
    code, out = _run(["a-frame", "--window", "rep", *a, "--now", str(S_A + 29 * 86400)], capsys)
    assert code == 75 and "results_A.json" in out["tempfail"]


def test_stage2_final_with_a_triggered_family_waits_for_the_rep_result(env, capsys):
    a = base(env)
    env["root"].mkdir(parents=True, exist_ok=True)
    (env["root"] / "results_A.json").write_text(json.dumps({"Q1": {"advance": True, "p": 0.001}, "U1": {"advance": False}}))
    code, out = _run(["stage2-final", *a], capsys)
    assert code == 75 and "results_A_rep.json" in out["tempfail"]
    (env["root"] / "results_A_rep.json").write_text(json.dumps({"Q1": {"p": 0.0124, "testable": True, "checks_ok": True, "stage2_early_alpha_ok": True}, "Q2": {"p": 0.2, "testable": True, "checks_ok": True, "stage2_early_alpha_ok": False}}))
    code, out = _run(["stage2-final", *a], capsys)
    assert code == 0 and out["k2"] == 2 and out["verdict"]["Q1"]["pass"] is True and out["verdict"]["Q2"]["pass"] is False
    code, out = _run(["stage2-final", *a], capsys)
    assert out["already_written"] is True
