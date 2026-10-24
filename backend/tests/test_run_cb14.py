# ruff: noqa: E501
"""CB14 runner and queue-draft tests (docs/research_lab/CREATIVE_BATCH_14.md section 4): offline; no network; no real CB14 quantity."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb14_common as c14

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts"))
import run_cb14  # noqa: E402

DRAFTS = ROOT / "docs" / "research_lab" / "queue" / "drafts"
JOBS = ROOT / "docs" / "research_lab" / "queue" / "jobs"
IDS = [300, 301, 302, 303, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 316, 317, 318, 319, 320, 321, 322, 323]
PROMOTED = {300, 301, 302, 303, 305}  # promoted to queue/jobs by the coordinator: the smokes after the re-check of 515d68d, then q0302 / q0303 / q0305 (their notes carry the shas at promotion)


def _drafts() -> list[dict]:
    out = []
    for n in IDS:
        fs = sorted((JOBS if n in PROMOTED else DRAFTS).glob(f"q{n:04d}_cb14_*.json"))
        assert len(fs) == 1, n
        out.append(json.loads(fs[0].read_text()))
    return out


def test_every_draft_exists_parses_and_is_a_draft_not_a_job():
    ds = _drafts()
    assert [d["id"][:5] for d in ds] == [f"q{n:04d}" for n in IDS]
    assert {int(p.name[1:5]) for p in JOBS.glob("q03*_cb14_*.json")} == PROMOTED  # nothing else promoted by an implementer
    ap = run_cb14.build_parser()
    for d in ds:
        assert d["family"] == "creative_batch_14" and ("DRAFT" in d["notes"] or int(d["id"][1:5]) in PROMOTED)
        assert d["argv"][0] == "scripts/run_cb14.py"
        a = ap.parse_args(d["argv"][1:])
        assert callable(a.fn)
        if d["resources"]["lane"] == "net" and a.cmd != "smoke":  # smokes write counts only
            assert "--data-dumps-cap-gb" in d["argv"] and d["argv"][d["argv"].index("--data-dumps-cap-gb") + 1] == "40"
        for dep in d["depends_on"]:
            assert dep[:5] in {f"q{n:04d}" for n in IDS} | {"q0276", "q0227", "q0221"}


def test_drafts_carry_the_declared_arguments_and_the_current_rules_shas():
    rules = json.loads((ROOT / "docs" / "research_lab" / "seals" / "cb14_rules.json").read_text())["parts"]
    for d in _drafts():
        a = run_cb14.build_parser().parse_args(d["argv"][1:])
        cmd = a.cmd
        if cmd in run_cb14.DECLARED_DISK_CAP_GB and hasattr(a, "disk_cap_gb"):
            assert abs(a.disk_cap_gb - run_cb14.DECLARED_DISK_CAP_GB[cmd]) < 1e-9, d["id"]
        if cmd == "s-data":
            assert abs(a.disk_cap_gb - run_cb14.DECLARED_DISK_CAP_S_DATA[a.subset]) < 1e-9
        assert getattr(a, "rps", 0.0) <= run_cb14.DECLARED_RPS_MAX.get(cmd, 99.0) + 1e-9
        if int(d["id"][1:5]) in PROMOTED:
            continue
        assert rules["common"]["rules_sha256"] in d["notes"], d["id"]
        fam = getattr(a, "part", None) or getattr(a, "family", None) or ("S" if cmd.startswith("s-") else "W")
        if cmd != "exclusion-keys":
            assert rules[fam]["rules_sha256"] in d["notes"], d["id"]
    live = json.loads(next(DRAFTS.glob("q0310_cb14_*.json")).read_text())
    assert live["not_before"] == "2026-10-26T00:00:00Z" and live["resources"]["lane"] == "cron"


def test_repeat_regexes_match_the_complete_status_lines():
    import re

    for d in _drafts():
        rp = d.get("repeat")
        if rp:
            status = re.search(r'"status": "([^"]+)"', rp["until_log_regex"].replace("\\", "")).group(1)
            for alt in status.strip("()").split("|"):  # every alternative (completion and terminal statuses) ends the repeat
                assert re.search(rp["until_log_regex"], json.dumps({"status": alt})), (d["id"], alt)


def test_rules_file_matches_the_code_for_every_part():
    p = ROOT / "docs" / "research_lab" / "seals" / "cb14_rules.json"
    for part in c14.PARTS:
        assert c14.verify_rules(p, require_committed=False, part=part)


def test_analysis_jobs_and_live_refuse_before_the_freeze(tmp_path, capsys):
    for argv in (["screen", "--family", "W"], ["screen", "--family", "S"], ["rep", "--family", "W", "--results-sha256", "0" * 64], ["w-live", "--standalone"]):
        code = run_cb14.main([*argv, "--root", str(tmp_path / "creative_batch14"), "--allow-uncommitted-rules"])
        out = capsys.readouterr().out
        assert code == run_cb14.REFUSED, (argv, out)


def test_declared_arguments_cannot_be_loosened(tmp_path, capsys):
    code = run_cb14.main(["w-frame", "--rps", "5", "--root", str(tmp_path / "creative_batch14")])
    assert code == run_cb14.REFUSED
    assert "declaration" in capsys.readouterr().out
    code = run_cb14.main(["smoke", "--part", "W", "--rps", "3", "--root", str(tmp_path / "creative_batch14")])
    assert code == run_cb14.REFUSED
    code = run_cb14.main(["w-revisions", "--maxlag", "9", "--root", str(tmp_path / "creative_batch14")])
    assert code == run_cb14.REFUSED


def test_n_data_refuses_without_the_open_token(tmp_path, capsys):
    code = run_cb14.main(["s-data", "--subset", "N", "--root", str(tmp_path / "creative_batch14"), "--allow-uncommitted-rules"])
    assert code in (run_cb14.REFUSED, run_cb14.TEMPFAIL)
    capsys.readouterr()


def test_unknown_family_refused(tmp_path, capsys):
    code = run_cb14.main(["pregate", "--family", "X", "--root", str(tmp_path / "creative_batch14"), "--allow-uncommitted-rules"])
    assert code == run_cb14.REFUSED
    capsys.readouterr()


@pytest.mark.parametrize("part", ["W", "S"])
def test_freeze_part_prints_a_declaration(part, capsys):
    assert run_cb14.main(["freeze-part", "--part", part]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["part"] == part and len(doc["rules_sha256"]) == 64


def test_strict_holm_k1_is_four_fixed_and_equality_does_not_reject():
    assert c14.BATCH_HOLM_K1 == 4 and c14.STAGE1_HOLM_FAMILY == ("W1", "W2", "S1", "S2")
    out = c14.stage1_holm({"W1": 0.0125, "W2": None, "S1": None, "S2": None})
    assert out["k"] == 4 and out["tests"]["W1"]["reject"] is False  # p == alpha / 4 is NOT p < alpha / 4
    assert c14.stage1_holm({"W1": 0.0124, "W2": None})["tests"]["W1"]["reject"] is True
    assert sorted(out["not_run_as_p1"]) == ["S1", "S2", "W2"]
    with pytest.raises(c14.Refused):
        c14.stage1_holm({"W1": 0.01, "X9": 0.01})


def test_early_stage2_rule_is_alpha_over_four_strict():
    assert c14.EARLY_ALPHA2 == pytest.approx(0.0125)
    assert c14.early_stage2_ok(0.0124) and not c14.early_stage2_ok(0.0125) and not c14.early_stage2_ok(None)


# =====================================================================================================================================================
# Freeze-check fixes (CREATIVE_BATCH_14.md section 11): regression tests
# =====================================================================================================================================================


def _base_argv(tmp_path, rules):
    return ["--root", str(tmp_path / "creative_batch14"), "--history-root", str(tmp_path / "history"), "--rules", str(rules), "--allow-uncommitted-rules",
            "--trials-path", str(tmp_path / "trials.jsonl")]


def _count_lines(tp, fam):
    if not tp.exists():
        return []
    return [json.loads(x) for x in tp.read_text().splitlines() if x.strip() and json.loads(x).get("source") == f"creative_batch_14:{fam}" and json.loads(x).get("kind") == "ml_explain"]


def test_f4_n_exemption_survives_a_base_file_that_already_holds_the_h12_say_ids():
    found = {"h12_say": {"market_id": {"s1", "s2", "s3"}}, "h13_touch": {"market_id": {"s3", "t1"}}}
    base = {"s1", "s2", "s3", "b9"}  # q0276 already unions the CB12 frames
    ks = c14.split_key_sets(found, seal_ids={"s2"}, base_ids=base)
    assert ks["s_exempt"] == {"s1"}  # only-from-h12_say, regardless of the base file (s2: a seal copy; s3: another frame)
    assert ks["lookup"] == {"t1", "s1"} and ks["new_ids"] == {"t1"}
    rows = [["x1", "1", "E1;E2", "N1", "S1"]]
    ex = c14.exempt_rows([["s1", "1", "E1;E9", "N1", "S1;S7"]], rows)
    assert ex == [["s1", "1", "E9", "", "S7"]]  # an exempt market never lifts a key another source also needs


def test_f5_a_recorded_stall_is_counted_once_and_downstream_jobs_end_with_exit_0(tmp_path, capsys):
    from astrolabe.research_lab import cb9_common as c9

    rules = c14.write_rules(tmp_path / "rules.json")
    (tmp_path / "history" / "h14_wiki").mkdir(parents=True)
    c9.write_stall(tmp_path / "history" / "h14_wiki", c9.STALL_DISJOINTNESS, "exclusion keys: more than 2% of ids without metadata")
    tp = tmp_path / "trials.jsonl"
    code = run_cb14.main(["pregate", "--family", "W", *_base_argv(tmp_path, rules)])
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and out["status"] == c14.TERMINAL_STATUS and "disjointness" in out["label"]  # not an endless exit 75
    lines = _count_lines(tp, "W")
    assert len(lines) == 1 and lines[0]["n_tests"] == 2  # W1 and W2 counted with p = 1, once
    tests = [json.loads(x) for x in tp.read_text().splitlines() if json.loads(x).get("kind") == "cb14_test"]
    assert sorted(t["hypothesis"] for t in tests) == ["W1", "W2"] and all(t["p"] == 1.0 and t["testable"] is False for t in tests)
    for argv in (["census", "--family", "W"], ["w-revisions"], ["w-prints"], ["w-live", "--standalone"], ["screen", "--family", "W"]):  # w-live: no W Stage 2 to collect
        code = run_cb14.main([*argv, *_base_argv(tmp_path, rules)])
        capsys.readouterr()
        assert code == 0, argv
    assert len(_count_lines(tp, "W")) == 1 and not _count_lines(tp, "S")  # nothing counted a second time; S untouched
    res = json.loads((tmp_path / "creative_batch14" / "results_W.json").read_text())
    assert res["W1"]["p"] == 1.0 and res["terminal"]["family"] == "W" and res["stage1_holm"]["k"] == 4
    # exclusion keys with disjointness unverified make BOTH families terminal (counted once each)
    root2 = tmp_path / "r2" / "creative_batch14"
    root2.mkdir(parents=True)
    (root2 / c14.c9.EXCLUSION_REPORT_NAME).write_text(json.dumps({"disjointness": c14.UNVERIFIED}))
    code = run_cb14.main(["pregate", "--family", "S", "--root", str(root2), "--history-root", str(tmp_path / "history"), "--rules", str(rules), "--allow-uncommitted-rules",
                          "--trials-path", str(tmp_path / "t2.jsonl")])
    capsys.readouterr()
    assert code == 0 and len(_count_lines(tmp_path / "t2.jsonl", "S")) == 1 and c14.read_terminal(root2, "S")["label"] == "not testable (disjointness unverified)"
    # a smoke run AFTER the family became terminal counts nothing a second time (it never runs)
    code = run_cb14.main(["smoke", "--part", "S", "--standalone", "--root", str(root2), "--history-root", str(tmp_path / "history"), "--rules", str(rules), "--allow-uncommitted-rules",
                          "--trials-path", str(tmp_path / "t2.jsonl")])
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and out["status"] == c14.TERMINAL_STATUS and len(_count_lines(tmp_path / "t2.jsonl", "S")) == 1 and not (root2 / "smoke_S.json").exists()


def test_f6_stage2_final_holm_can_add_a_pass_after_the_early_alpha_over_four(tmp_path, capsys):
    root = tmp_path / "creative_batch14"
    root.mkdir()
    (root / "results_W.json").write_text(json.dumps({"W1": {"advance": False}, "W2": {"advance": True}}))
    (root / "results_S.json").write_text(json.dumps({"S1": {"advance": False}, "S2": {"advance": False}}))
    stale = tmp_path / "stale_rules.json"
    stale.write_text(json.dumps({"rules_version": c14.RULES_VERSION, "parts": {}}))
    base = ["stage2-final", "--root", str(root), "--history-root", str(tmp_path / "history"), "--trials-path", str(tmp_path / "t.jsonl"), "--allow-uncommitted-rules"]
    assert run_cb14.main([*base, "--rules", str(stale)]) == run_cb14.REFUSED  # the final step verifies the rules file first
    capsys.readouterr()
    argv = [*base, "--rules", str(c14.write_rules(tmp_path / "rules.json"))]
    assert run_cb14.main(argv) == 0 and json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "idle_heartbeat"  # a long wait: heartbeat first
    assert run_cb14.main(argv) == run_cb14.TEMPFAIL  # W triggered Stage 2 and its rep is not final: pending
    capsys.readouterr()
    (root / "results_W_rep.json").write_text(json.dumps({"W2_rep": {"p": 0.03, "testable": True, "checks_ok": True, "stage2_early_alpha_ok": False}}))
    assert run_cb14.main(argv) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["k2"] == 1 and out["verdict"]["W2"] == {"checks_ok": True, "early_alpha_over_4": False, "final_holm_reject": True, "pass": True}  # 0.03 > alpha/4 but < alpha/1: added
    assert run_cb14.main(argv) == 0 and json.loads(capsys.readouterr().out.strip().splitlines()[-1])["already_written"] is True
    with pytest.raises(c14.Refused):
        c14.stage2_final({"W9": 0.01})
    assert c14.stage2_final({"W2": 0.02, "S1": None})["tests"]["W2-rep"]["reject"] is True


def test_f6_stage2_k_is_validated_against_the_smallest_admissible_count(tmp_path):
    assert c14.stage2_k_min(1, None, ("S1", "S2")) == 3  # S not final: both S tests assumed triggered
    assert c14.stage2_k_min(1, {"S1": {"advance": True}, "S2": {"advance": False}}, ("S1", "S2")) == 2
    a = run_cb14.build_parser().parse_args(["rep", "--family", "W", "--stage2-k", "TODO-COORDINATOR", "--root", str(tmp_path / "creative_batch14")])
    with pytest.raises(c14.Refused):
        run_cb14._stage2_k(a, "W", 1, tmp_path)
    a.stage2_k = "2"
    with pytest.raises(c14.Refused):  # results_S.json absent -> k_min = 1 + 2 = 3
        run_cb14._stage2_k(a, "W", 1, tmp_path)
    a.stage2_k = "3"
    assert run_cb14._stage2_k(a, "W", 1, tmp_path) == 3


def test_f9_the_freeze_entry_must_pin_the_verified_rules_and_model_shas(tmp_path):
    spec = tmp_path / "cb14_v1.json"
    spec.write_text(json.dumps({"W": {"rules_sha256": "a" * 64}, "S": {"rules_sha256": "c" * 64, "s_model_sha256": "d" * 64, "s_model_rebased_sha256": "e" * 64}}))
    with pytest.raises(c14.Refused, match="does not cover"):
        c14.require_freeze("W", spec, require_committed=False, rules_shas={"W": "b" * 64})
    assert len(c14.require_freeze("W", spec, require_committed=False, rules_shas={"W": "a" * 64})) == 64
    with pytest.raises(c14.Refused, match="model pins"):
        c14.require_freeze("S", spec, require_committed=False, rules_shas={"S": "c" * 64})
    with pytest.raises(c14.Refused, match="s_model_sha256"):
        c14.require_freeze("S", spec, require_committed=False, rules_shas={"S": "c" * 64, "S_MODEL": "0" * 64, "S_MODEL_REBASED": "e" * 64})
    assert c14.require_freeze("S", spec, require_committed=False, rules_shas={"S": "c" * 64, "S_MODEL": "d" * 64, "S_MODEL_REBASED": "e" * 64})
    with pytest.raises(c14.Refused):
        c14.require_freeze("W", spec, require_committed=False)  # the verified sha is mandatory


def test_f16_id_only_readers_open_named_holdout_frames_ids_only(tmp_path):
    import gzip

    hist = tmp_path / "research_lab" / "history"
    p = hist / "h11_attn" / "holdout" / "frame_hold.csv.gz"
    p.parent.mkdir(parents=True)
    with gzip.open(p, "wt") as fh:
        fh.write("market_id,event_id,question,outcome_prices\nm1,e1,secret question,[1 0]\n")
    assert c14.read_id_columns(p) == {"market_id": {"m1"}, "event_id": {"e1"}}  # ids only leave the reader
    for bad in ("h11_attn/holdout/closes_hold.csv.gz", "h11_attn/holdout/pageviews.csv.gz", "h11_attn/pageviews.csv.gz", "h12_say/holdout/events.csv.gz", "h12_say/outcomes_guarded_screen.csv.gz"):
        with pytest.raises(c14.Refused):
            c14.guard_id_file(hist / bad)
    fills = c14.id_source_path("creative_batch13/t_holdout/fills.csv.gz", hist)
    assert fills == tmp_path / "research_lab" / "creative_batch13" / "t_holdout" / "fills.csv.gz" and c14.guard_id_file(fills)
    found, absent = c14.frame_ids(hist)
    assert found == {"h11_attn": {"market_id": {"m1"}, "event_id": {"e1"}}} and "creative_batch13/t_screen/fills.csv.gz" in absent and "h13_touch/holdout/events.csv.gz" in absent


def test_f7_f13_f17_drafts_carry_the_pins_tokens_windows_and_repeats():
    by = {d["id"][:5]: d for d in _drafts()}
    q302 = by["q0302"]
    pin302 = q302["argv"][q302["argv"].index("--base-sha256") + 1]  # promoted with the pinned base-key sha (or still unset as a draft)
    assert (pin302 == c14.PIN_UNSET or re.fullmatch(r"[0-9a-f]{64}", pin302)) and "exclusion_keys_complete" in q302["repeat"]["until_log_regex"]
    assert "never opens h12_say" not in q302["notes"] and "id columns" in q302["notes"]
    for q, tok in (("q0303", "w_frame_complete"), ("q0307", "w_prints_complete"), ("q0312", "s_frame_complete")):
        assert tok in by[q]["repeat"]["until_log_regex"], q
    for q in ("q0311", "q0322"):
        d = by[q]
        assert d["not_before"] and d["argv"][d["argv"].index("--results-sha256") + 1] == c14.PIN_UNSET and d["argv"][d["argv"].index("--stage2-k") + 1] == c14.PIN_UNSET
        assert "--rules" in d["argv"]
    assert by["q0311"]["not_before"] >= "2027-01-27T00:00:00Z"
    assert by["q0321"]["repeat"]["max_runs"] >= 600 and "s_stage2_outcomes_final" in by["q0321"]["repeat"]["until_log_regex"] and "s_stage2_window_closed" not in by["q0321"]["repeat"]["until_log_regex"]
    assert "terminal_not_testable" in by["q0321"]["repeat"]["until_log_regex"]
    assert "q0227b_cb11_attn_frame" in q302["depends_on"] and "q0227_cb11_attn_frame" not in q302["depends_on"]
    assert "q0221b_cb11_exclusion_keys" in q302["depends_on"] and "q0221_cb11_exclusion_keys" not in q302["depends_on"] and "q0276_cb13_exclusion_keys" in q302["depends_on"]
    fin = by["q0323"]
    assert fin["argv"][1] == "stage2-final" and fin["resources"]["lane"] == "cpu" and fin["not_before"]
