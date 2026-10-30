# ruff: noqa: E501
"""CB17 window jobs q0404-q0412 through the runner (offline; SYNTHETIC worlds only: no real SCREEN_8 / REP_8 / data-dumps file is ever opened). Refusals exit 2, 'not yet' exits 75 and
writes nothing, the screen is counted once, the REP seal gates the Stage-2 rows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb17_common as c17
from astrolabe.research_lab import cb17_wcommon as w
from astrolabe.research_lab import cb17_win as win
from tests.cb17_wsynth import FLOOR, JobEnv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb17  # noqa: E402

DAY = 86400.0
EXP = ("--disk-cap-gb",)


def _run(argv, capsys):
    code = run_cb17.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


def lines(env):
    return [json.loads(x) for x in env.trials.read_text().splitlines()] if env.trials.exists() else []


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    return JobEnv(tmp_path_factory.mktemp("cb17w"))


def after_screen(env):
    return FLOOR + 14 * DAY + 8 * 3600.0


def after_rep(env):
    return FLOOR + 28 * DAY + 8 * 3600.0


def test_every_window_job_refuses_before_its_time_without_writing_or_counting(env, capsys):
    for cmd, fam, win_ in (("frame", "B,C", "screen"), ("frame", "E", "screen")):
        code, out = _run(env.argv(cmd, "--families", fam, "--window", win_, now=FLOOR + 3 * DAY), capsys)
        assert code == 75 and "not before" in out["tempfail"]
    assert not (env.root / "screen").exists() and not lines(env)
    code, out = _run(env.argv("screen", now=FLOOR + 3 * DAY), capsys)
    assert code == 75 and not (env.root / "results_8.json").exists() and not lines(env)


def test_family_a_is_withdrawn_and_no_a_frame_is_built(env, capsys):
    code, out = _run(env.argv("frame", "--families", "A,E", "--window", "screen", now=after_screen(env)), capsys)
    assert code == 2 and "withdrawn" in out["refused"]


def test_exclusion_keys_refuses_the_unset_pin_and_a_missing_smoke(env, capsys, tmp_path):
    code, out = _run(env.argv("exclusion-keys", "--base-sha256", "TODO-COORDINATOR"), capsys)
    assert code == 2 and "TODO-COORDINATOR" in out["refused"]
    code, out = _run(env.argv("exclusion-keys"), capsys)  # no --base-sha256 at all: the default is the unset token
    assert code == 2 and "TODO-COORDINATOR" in out["refused"]
    other = JobEnv(tmp_path / "nosmoke", with_smoke=False)
    code, out = _run(other.argv("exclusion-keys", "--cb16-stopped"), capsys)
    assert code == 2 and "smoke.json missing" in out["refused"]


def test_exclusion_keys_checks_the_pinned_sha_of_the_cb16_file(env, capsys, tmp_path):
    keys = tmp_path / "creative_batch16" / "exclusion_keys.csv.gz"
    keys.parent.mkdir()
    from astrolabe.research_lab import history_backfill as hb

    keys.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids", "sources"], [["1", "1", env.screen["markets"][0]["ev"], "", "", "base"], ["999", "1", "EVX", "", "", "base"]]))
    code, out = _run(env.argv("exclusion-keys", "--base-path", str(keys), "--base-sha256", "0" * 64), capsys)
    assert code == 2 and "!= pinned" in out["refused"]
    code, out = _run(env.argv("exclusion-keys", "--base-path", str(keys), "--base-sha256", c17.sha256_file(keys)), capsys)
    assert code == 0 and out["status"] == win.KEYS_STATUS and out["n_universe"] == 2
    code, out = _run(env.argv("exclusion-keys", "--base-path", str(keys), "--base-sha256", c17.sha256_file(keys)), capsys)
    assert code == 2  # the key files are written once


def test_smoke_refuses_when_a_worn_source_is_missing_and_writes_nothing(env, capsys, tmp_path):
    fresh = JobEnv(tmp_path / "s", with_smoke=False)
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"live_trades/trades-20261012.jsonl": "0" * 64}))
    code, out = _run(fresh.argv("smoke", extra=("--fills-dir", str(tmp_path / "no_such_screen"), "--worn-sha256", str(pins))), capsys)
    assert code == 2 and "refused" in out and not (fresh.root / "smoke.json").exists()


def test_screen_chain_frames_census_and_screen_count_b_and_c_once(env, capsys):
    now = after_screen(env)
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "screen", now=now), capsys)
    assert code == 0 and out["status"] == "frame_bc_complete" and out["units"]["B"] > 0 and out["units"]["C"] > 0
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "screen", now=now), capsys)
    assert code == 0 and out.get("already_complete") is True
    code, out = _run(env.argv("frame", "--families", "E", "--window", "screen", now=now), capsys)
    assert code == 0 and out["status"] == "frame_e_complete" and out["transactions"] > 0
    code, out = _run(env.argv("census", "--window", "screen", now=now), capsys)
    assert code == 0 and out["status"] == "census_complete" and "GBT" in out["gates"]["B"]
    cen = json.loads((env.root / "census_8.json").read_text())
    assert cen["E"]["k"] == 0 and cen["counts_only"] is True and "reentry" in cen["E"]
    c17.assert_clean_result(cen)
    assert cen["overlap"]["universe_markets"] == 2 and cen["overlap"]["B_units_by_source"].get("cb16:base", 0) > 0  # CB16's key rows are overlap counts, never drops
    assert cen["overlap"]["drop_keys"] == 0
    # E011 and CB3 hold the screen
    code, out = _run(env.argv("screen", "--draws", "20", now=FLOOR + 15 * DAY), capsys)
    assert code == 75
    hold = ("--e011-record", str(env.e011), "--cb3-spec-dir", str(env.cb3))
    code, out = _run(env.argv("screen", now=env.late, extra=(*hold, "--draws", "20")), capsys)
    assert code == 0, out
    res = json.loads((env.root / "results_8.json").read_text())
    assert out["status"] == "screen_complete" and set(res) >= {"B1", "B2", "C1", "holm", "triggers", "frozen", "k1"} and res["k1"] == 3
    assert res["holm"]["k1"] == 3 and set(res["holm"]["tests"]) == {"B1", "B2", "C1"}
    ls = lines(env)
    counts = {x["source"]: x["n_tests"] for x in ls if x.get("kind") == "ml_explain"}
    assert counts == {"creative_batch_17:B": 2, "creative_batch_17:C": 1}
    tests = [x for x in ls if x.get("kind") == "cb17_test"]
    assert sorted(x["hypothesis"] for x in tests) == ["B1", "B2", "C1"] and all(x["n_tests"] == 0 for x in tests)
    code, out = _run(env.argv("screen", now=env.late, extra=(*hold, "--draws", "20")), capsys)
    assert code == 2  # results are written once (and nothing is counted twice)
    assert len([x for x in lines(env) if x.get("kind") == "ml_explain"]) == 2


def test_test_hooks_are_refused_without_the_uncommitted_flag(env, capsys):
    argv = [a for a in env.argv("screen", now=FLOOR) if a != "--allow-uncommitted-rules"]
    code, out = _run(argv, capsys)
    assert code == 2 and "test hook" in out["refused"]


def test_rep_frame_waits_for_the_committed_copy_and_is_not_triggered_on_a_null_screen(env, capsys):
    now = after_rep(env)
    res = env.root / "results_8.json"
    assert res.exists()
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "rep", now=now), capsys)
    assert code == 75 and "committed copy" in out["tempfail"]  # the coordinator commits the byte-identical copy first
    (env.seals / win.RESULTS_COPY_NAME).write_bytes(res.read_bytes())
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "rep", now=now), capsys)
    triggers = json.loads(res.read_text())["triggers"]
    if not any(triggers.values()):
        assert code == 0 and out["status"] == "rep_not_triggered" and not (env.root / "rep").exists()
    code, out = _run(env.argv("stage2-final"), capsys)
    if not any(triggers.values()):
        assert code == 2 and "nothing to finalise" in out["refused"]


def test_triggered_stage2_seal_rep_econ_and_final_holm(env, capsys, tmp_path):
    """A crafted Stage-1 result with all three tests advanced triggers every REP_8 test. The rows of REP_8 are read only after the committed copy, the seal copy is verified, and the Stage-2 file
    carries the early-alpha flags and the econ lines; stage2-final adds the one strict Holm."""
    e2 = JobEnv(tmp_path / "trig")
    now = after_rep(e2)
    e2.root.mkdir(parents=True, exist_ok=True)
    crafted = {"B1": {"p": 0.001, "advance": True, "testable": True}, "B2": {"p": 0.002, "advance": True, "testable": True}, "C1": {"p": 0.003, "advance": True, "testable": True},
               "triggers": {"B1": True, "B2": True, "C1": True}, "frozen": {"sd_x": 0.09}, "k1": 3}
    (e2.root / "results_8.json").write_text(json.dumps(crafted))
    (e2.root / "census_8.json").write_text(json.dumps({"B": {}, "C": {}, "E": {}}))
    (e2.seals / win.RESULTS_COPY_NAME).write_bytes((e2.root / "results_8.json").read_bytes())
    pre_keys = e2.root / "keys"
    del pre_keys
    # the rep frame needs the q0405 key files
    from astrolabe.research_lab import cb16_common as c16
    from astrolabe.research_lab import history_backfill as hb

    kd = e2.root / "keys"
    kd.mkdir(parents=True)
    (kd / win.KEYS_NAME).write_bytes(hb._gz_csv_bytes(["market_id", "event_ids", "sources"], []))
    (kd / win.DROP_KEYS_NAME).write_bytes(hb._gz_csv_bytes(["key", "source"], []))
    c16.write_dir_manifest(kd, win.KEYS_STATUS, [kd / win.KEYS_NAME, kd / win.DROP_KEYS_NAME], {})
    code, out = _run(e2.argv("frame", "--families", "B,C", "--window", "rep", now=now), capsys)
    assert code == 0 and out["status"] == "frame_rep_complete", out
    assert (e2.root / "rep" / "b_units.npz").exists() and (e2.root / "rep" / "c_units.npz").exists() and (e2.root / "rep" / "b_marks.npz").exists()
    seal = e2.root / "rep_SEAL.json"
    assert seal.exists() and json.loads(seal.read_text())["source_file_sha256"]
    code, out = _run(e2.argv("rep", "--results-sha256", c17.sha256_file(e2.root / "results_8.json"), now=now, extra=("--e011-record", str(e2.e011), "--cb3-spec-dir", str(e2.cb3), "--draws", "20")), capsys)
    assert code == 2 and "seal" in out["refused"]  # the seal copy is not committed yet
    (e2.seals / w.REP_SEAL_NAME).write_bytes(seal.read_bytes())
    code, out = _run(e2.argv("rep", "--results-sha256", "f" * 64, now=now, extra=("--e011-record", str(e2.e011), "--cb3-spec-dir", str(e2.cb3), "--draws", "20")), capsys)
    assert code == 2 and "differs" in out["refused"]
    code, out = _run(e2.argv("rep", "--results-sha256", c17.sha256_file(e2.root / "results_8.json"), now=now, extra=("--e011-record", str(e2.e011), "--cb3-spec-dir", str(e2.cb3), "--draws", "20")), capsys)
    assert code == 0 and out["status"] == "rep_complete" and set(out["tests"]) == {"B1-rep", "B1-econ", "B2-rep", "B2-econ", "C1-rep", "C1-econ"}
    rep = json.loads((e2.root / "results_rep.json").read_text())
    for t in out["tests"]:
        assert "stage2_early_alpha_ok" in rep[t] and rep[t]["p"] is not None
    # econ lines are 'not run (power)' on this tiny world (minimum 300 fills per bin), counted with p = 1
    assert rep["B1-econ"]["verdict"] == "not run (power)" and rep["B1-econ"]["p"] == 1.0
    rl = [x for x in lines(e2) if x.get("kind") == "ml_explain" and x["source"].endswith(":rep")]
    assert sorted((x["source"], x["n_tests"]) for x in rl) == [("creative_batch_17:B:rep", 4), ("creative_batch_17:C:rep", 2)]
    code, out = _run(e2.argv("stage2-final"), capsys)
    assert code == 0 and out["k2"] == 6 and set(out["verdict"]) == set(out["verdict"]) and (e2.root / "stage2_final.json").exists()
    code, out = _run(e2.argv("stage2-final"), capsys)
    assert code == 0 and out.get("already_written") is True


def test_code_pin_prints_the_code_and_rules_shas(capsys, env):
    code, out = _run(["code-pin", "--rules", str(env.rules), "--allow-uncommitted-rules"], capsys)
    assert code == 0 and out["code_sha256"] == win.code_sha256() and set(out["rules_sha256"]) == set(win.RULE_PARTS) and "cb17_jobs.py" in out["files"]


def test_q0406_refuses_without_the_ruling_6_attestation_and_on_a_stale_code_pin_or_rules_part(env, capsys, tmp_path):
    now = after_screen(env)
    base = ("frame", "--families", "B,C", "--window", "screen")
    good = json.loads(env.freeze.read_text())
    try:
        env.freeze.write_text(json.dumps({**good, "attestation_code_freeze": ""}))
        code, out = _run(env.argv(*base, now=now), capsys)
        assert code == 2 and "attestation" in out["refused"]
        env.freeze.write_text(json.dumps({**good, "code_sha256": "0" * 64}))
        code, out = _run(env.argv(*base, now=now), capsys)
        assert code == 2 and "does not cover" in out["refused"]
        env.freeze.write_text(json.dumps({**good, "rules_sha256": {**good["rules_sha256"], "B": "0" * 64}}))
        code, out = _run(env.argv(*base, now=now), capsys)
        assert code == 2 and "other rules parts" in out["refused"]
    finally:
        env.freeze.write_text(json.dumps(good))
    doc = json.loads(env.rules.read_text())
    doc["parts"]["B"]["rules_sha256"] = "0" * 64  # a rules file that differs from the code's declaration
    other = tmp_path / "other_rules.json"
    other.write_text(json.dumps(doc))
    argv = env.argv(*base, now=now)
    argv[argv.index("--rules") + 1] = str(other)
    code, out = _run(argv, capsys)
    assert code == 2 and "rules hash mismatch" in out["refused"]


def test_declared_arguments_and_the_data_dumps_cap_are_enforced(env, capsys):
    code, out = _run(env.argv("census", "--window", "screen", now=after_screen(env), extra=("--disk-cap-gb", "5")), capsys)
    assert code == 2 and "differ from the declaration" in out["refused"]
    code, out = _run(env.argv("census", "--window", "screen", now=after_screen(env), extra=("--data-dumps-cap-gb", "400")), capsys)
    assert code == 2 and "differ from the declaration" in out["refused"]
    code, out = _run(env.argv("census", "--window", "rep", now=after_screen(env)), capsys)
    assert code == 2


def test_frame_screen_refuses_when_the_smoke_does_not_pass_for_the_family(tmp_path, capsys):
    bad = JobEnv(tmp_path / "badsmoke", with_smoke=False)
    bad.write_smoke(**{k: False for k in w.SMOKE_CRITERIA})
    code, out = _run(bad.argv("frame", "--families", "B,C", "--window", "screen", now=after_screen(bad)), capsys)
    assert code == 2 and "smoke" in out["refused"]
    assert not (bad.root / "screen").exists()
