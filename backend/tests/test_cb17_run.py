# ruff: noqa: E501
"""CB17 runner (offline; synthetic worn-window files). Refusals exit 2, results are write-once counts, the trials line carries no test."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb17_common as c17
from tests.cb17_synth import (
    ep,
    fill_row,
    print_,
    write_capture,
    write_day,
    write_screen,
    write_sweep,
)
from tests.test_cb17_census import D12, a_world, b_world, c_captures

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb17  # noqa: E402


def _run(argv, capsys):
    code = run_cb17.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


@pytest.fixture()
def env(tmp_path):
    rules = tmp_path / "cb17_rules.json"
    c17.write_rules(rules)
    (tmp_path / "dd").mkdir()
    return {"tmp": tmp_path, "rules": rules, "root": tmp_path / "creative_batch17", "trials": tmp_path / "trials.jsonl"}


def args(env, w, *, extra=()):
    a = ["--root", str(env["root"]), "--rules", str(env["rules"]), "--allow-uncommitted-rules", "--standalone", "--trials-path", str(env["trials"]), "--data-dumps", str(env["tmp"] / "dd"),
         "--snapshot-dir", str(w["snap"]), *extra]
    if "tr" in w:
        a += ["--trades-dir", str(w["tr"])]
    if "screen" in w:
        a += ["--fills-dir", str(w["screen"])]
    if "sw" in w:
        a += ["--sweep-dir", str(w["sw"])]
    return a


def trial_lines(env):
    return [json.loads(x) for x in env["trials"].read_text().splitlines()] if env["trials"].exists() else []


def test_rules_command_declares_pre_common_b_c_e_and_not_a(env, capsys, tmp_path):
    code, out = _run(["rules", "--path", str(tmp_path / "r2.json")], capsys)
    assert code == 0 and out["parts"]["pre"]["declared"] is True and out["parts"]["pre"]["rules_sha256"]
    assert all(out["parts"][p]["declared"] is True for p in ("common", "B", "C", "E"))
    assert out["parts"]["A"]["declared"] is False and "withdrawn uncounted" in out["parts"]["A"]["reason"]
    assert json.loads((tmp_path / "r2.json").read_text()) == json.loads(env["rules"].read_text())
    code, out = _run(["rules", "--path", str(tmp_path / "r2.json")], capsys)  # idempotent for an identical file
    assert code == 0


def as_p1(monkeypatch, env):
    """Make the synthetic world 'reproduce P1' (23 fills, 23 resolved, 0 ambiguous, 22 non-sports, 22 resolved, 16 open, 6 close)."""
    from astrolabe.research_lab import cb17_pre as pre  # noqa: PLC0415

    monkeypatch.setattr(pre, "P1_EXPECTED", {"fills": 23, "token_resolved": 23, "ambiguous_transaction": 0, "non_sports": 22, "non_sports_resolved": 22, "open": 16, "close": 6})
    env["rules"].unlink()
    c17.write_rules(env["rules"])  # P1_EXPECTED is a hashed constant: the tmp rules file is re-sealed for the patched code


def test_pre_census_a_runs_write_once_and_logs_a_non_test_line(env, capsys, monkeypatch):
    as_p1(monkeypatch, env)
    w = a_world(env["tmp"])
    code, out = _run(["pre-census", "--family", "A", *args(env, w)], capsys)
    assert code == 0 and out["status"] == "pre_census_A_complete" and out["branch"] == "T" and out["a_withdrawn_uncounted"] is True and out["branch_recorded"] is True
    doc = json.loads((env["root"] / "pre_census_A.json").read_text())
    assert doc["p1_reproduction"]["matches"] is True and doc["rules_sha256"]["pre"] == c17.rules_part_file_doc("pre")["rules_sha256"] and doc["counts_only"] is True
    c17.assert_clean_result(doc)
    txt = json.dumps(doc)
    assert "WALLET-SECRET" not in txt and "SECRET-MARK" not in txt and "k-secret" not in txt
    (line,) = trial_lines(env)
    assert line["kind"] == "cb17_descriptive" and line["n_tests"] == 0 and line["source"] == "creative_batch_17:pre_census_A" and line["evidence_role"] == "exploratory_historical"
    code, out = _run(["pre-census", "--family", "A", *args(env, w)], capsys)  # written once
    assert code == 2 and "exists" in out["refused"]


def test_the_same_inputs_give_the_same_result_hash(env, capsys, monkeypatch):
    as_p1(monkeypatch, env)
    w = a_world(env["tmp"])
    c1, o1 = _run(["pre-census", "--family", "A", *args(env, w)], capsys)
    other = {**env, "root": env["tmp"] / "other" / "creative_batch17"}
    c2, o2 = _run(["pre-census", "--family", "A", *args(other, w)], capsys)
    assert c1 == c2 == 0 and o1["sha256"] == o2["sha256"]


def test_pre_census_b_and_c_and_cost_lag_map_run(env, capsys):
    wb = b_world(env["tmp"] / "b")
    code, out = _run(["pre-census", "--family", "B", *args(env, wb)], capsys)
    assert code == 0 and out["selected_level_B1"] in (0, 1, 2) and out["tokens_with_both_fresh_and_old"] == 1
    snap = env["tmp"] / "c" / "snapshots"
    c_captures(snap)
    code, out = _run(["pre-census", "--family", "C", *args(env, {"snap": snap})], capsys)
    assert code == 0 and out["events_with_units_having_6_prior"] == 1 and out["selected_level"] in (0, 1, 2)
    wk = {"snap": snap, "sw": env["tmp"] / "k" / "book_sweeps", "tr": env["tmp"] / "k" / "live_trades"}
    write_capture(snap, D12 - 60, [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}], name="20261012T000001Z_aa01aa01")
    write_sweep(wk["sw"], D12, [{"tok": "A", "mid": "1", "bid": "0.48", "ask": "0.50"}], name="20261012T000000Z_00000000")
    write_day(wk["tr"], "20261012", [print_(D12 + 60, "c1", 0.5, tx="t1")])
    code, out = _run(["cost-lag-map", *args(env, wk)], capsys)
    assert code == 0 and out["prints"] == 1 and (env["root"] / "cost_lag_map.json").exists()
    kinds = {x["source"] for x in trial_lines(env)}
    assert kinds == {"creative_batch_17:pre_census_B", "creative_batch_17:pre_census_C", "creative_batch_17:cost_lag_map"} and all(x["n_tests"] == 0 for x in trial_lines(env))


def test_declared_arguments_and_rules_are_enforced(env, capsys):
    w = a_world(env["tmp"])
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--disk-cap-gb", "0.5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--data-dumps-cap-gb", "80"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--part", "A"], capsys)
    assert code == 2 and "pre" in out["refused"]
    doc = json.loads(env["rules"].read_text())
    doc["parts"]["pre"]["constants"]["cb17_pre"]["AGREE_N_MIN"] = 1
    env["rules"].write_text(json.dumps(doc))
    code, out = _run(["pre-census", "--family", "A", *args(env, w)], capsys)
    assert code == 2 and "hash mismatch" in out["refused"]
    code, out = _run(["pre-census", "--family", "A", *args(env, w)[:0], "--rules", str(env["tmp"] / "missing.json"), "--allow-uncommitted-rules", "--standalone"], capsys)
    assert code == 2
    assert not (env["root"] / "pre_census_A.json").exists() and trial_lines(env) == []


def test_uncommitted_rules_are_refused_without_the_test_flag(env, capsys):
    w = a_world(env["tmp"])
    a = [x for x in args(env, w) if x != "--allow-uncommitted-rules"]
    code, out = _run(["pre-census", "--family", "A", *a], capsys)
    assert code == 2 and "not committed" in out["refused"]


def test_holdout_other_batch_and_out_of_window_inputs_are_refused(env, capsys, tmp_path):
    w = a_world(env["tmp"])
    ho = tmp_path / "creative_batch13" / "t_holdout"
    write_screen(tmp_path / "h", [fill_row(1, "c1", D12 + 7200, -1)])
    (tmp_path / "creative_batch13" / "t_holdout").mkdir(parents=True)
    bad = {**w, "screen": ho}
    code, out = _run(["pre-census", "--family", "A", *args(env, bad)], capsys)
    assert code == 2 and ("HOLDOUT" in out["refused"] or "t_screen" in out["refused"])
    bad = {**w, "snap": tmp_path / "creative_batch16" / "snapshots"}
    code, out = _run(["pre-census", "--family", "A", *args(env, bad)], capsys)
    assert code == 2 and "refused root" in out["refused"]
    bad = {**w, "tr": tmp_path / "surprise_live" / "live_trades"}
    code, out = _run(["pre-census", "--family", "A", *args(env, bad)], capsys)
    assert code == 2
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--out", str(tmp_path / "elsewhere.json")], capsys)
    assert code == 2 and "creative_batch17" in out["refused"]
    late = write_screen(tmp_path / "late", [fill_row(1, "c1", ep("2026-10-16T00:00:01Z"), -1)])
    code, out = _run(["pre-census", "--family", "A", *args(env, {**w, "screen": late})], capsys)
    assert code == 2 and "cut-off" in out["refused"]
    assert not (env["root"] / "pre_census_A.json").exists()


def test_disk_guard_is_a_pending_exit_75(env, capsys):
    w = a_world(env["tmp"])
    (env["tmp"] / "dd" / "big.bin").write_bytes(b"0" * 4_000_000)
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--data-dumps-cap-gb", "0.001"], capsys)
    assert code == 75, out
    assert "pending" in out["science"] and trial_lines(env) == [] and not (env["root"] / "pre_census_A.json").exists()


def test_a_p1_mismatch_fails_the_job_and_records_no_branch(env, capsys, monkeypatch):
    w = a_world(env["tmp"])
    code, out = _run(["pre-census", "--family", "A", *args(env, w)], capsys)  # the synthetic world is not probe P1's
    assert code == 2 and out["status"] == "pre_census_A_p1_mismatch" and "P1 mismatch" in out["refused"]
    assert out["p1_matches"] is False and out["branch_recorded"] is False and out["branch"] is None and out["a_withdrawn_uncounted"] is None and out["selected_level"] is None and out["selected_population"] is None
    first = env["root"] / "pre_census_A.json"
    doc = json.loads(first.read_text())
    assert doc["branch"] is None and doc["strata"]["selected_level"] is None and "branch_unrecorded_candidate" in doc
    (line,) = trial_lines(env)
    assert line["status"] == "pre_census_A_p1_mismatch" and line["branch"] is None and line["a_withdrawn_uncounted"] is None and line["selected_level"] is None and line["n_tests"] == 0
    # a rerun: the same path is refused (write-once); a NEW path needs --supersedes, which keeps and hashes the earlier file
    code, out = _run(["pre-census", "--family", "A", *args(env, w)], capsys)
    assert code == 2 and "exists" in out["refused"]
    v2 = env["root"] / "pre_census_A_v2.json"
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--out", str(v2), "--supersedes", str(env["root"] / "missing.json")], capsys)
    assert code == 2 and "must exist" in out["refused"] and not v2.exists()
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--out", str(v2), "--supersedes", str(first)], capsys)
    assert code == 2 and out["status"] == "pre_census_A_p1_mismatch"  # still not P1: failed again
    as_p1(monkeypatch, env)
    v3 = env["root"] / "pre_census_A_v3.json"
    code, out = _run(["pre-census", "--family", "A", *args(env, w), "--out", str(v3), "--supersedes", str(v2)], capsys)
    assert code == 0 and out["branch_recorded"] is True and out["branch"] == "T"
    d3 = json.loads(v3.read_text())
    assert d3["supersedes"]["path"] == str(v2) and len(d3["supersedes"]["sha256"]) == 64 and first.exists() and v2.exists()
