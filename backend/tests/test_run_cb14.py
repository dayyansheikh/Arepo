# ruff: noqa: E501
"""CB14 runner and queue-draft tests (docs/research_lab/CREATIVE_BATCH_14.md section 4): offline; no network; no real CB14 quantity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb14_common as c14

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts"))
import run_cb14  # noqa: E402

DRAFTS = ROOT / "docs" / "research_lab" / "queue" / "drafts"
JOBS = ROOT / "docs" / "research_lab" / "queue" / "jobs"
IDS = [300, 301, 302, 303, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 316, 317, 318, 319, 320, 321, 322]


def _drafts() -> list[dict]:
    out = []
    for n in IDS:
        fs = sorted(DRAFTS.glob(f"q{n:04d}_cb14_*.json"))
        assert len(fs) == 1, n
        out.append(json.loads(fs[0].read_text()))
    return out


def test_every_draft_exists_parses_and_is_a_draft_not_a_job():
    ds = _drafts()
    assert [d["id"][:5] for d in ds] == [f"q{n:04d}" for n in IDS]
    assert not list(JOBS.glob("q03*_cb14_*.json"))
    ap = run_cb14.build_parser()
    for d in ds:
        assert d["family"] == "creative_batch_14" and "DRAFT" in d["notes"]
        assert d["argv"][0] == "scripts/run_cb14.py"
        a = ap.parse_args(d["argv"][1:])
        assert callable(a.fn)
        if d["resources"]["lane"] == "net" and a.cmd != "smoke":  # smokes write counts only
            assert "--data-dumps-cap-gb" in d["argv"] and d["argv"][d["argv"].index("--data-dumps-cap-gb") + 1] == "40"
        for dep in d["depends_on"]:
            assert dep[:5] in {f"q{n:04d}" for n in IDS} | {"q0276", "q0227"}


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
            assert re.search(rp["until_log_regex"], json.dumps({"status": status}))


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
