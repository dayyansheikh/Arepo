import hashlib
import json
import subprocess

import pytest

from astrolabe.research_lab import compare, provenance


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("one")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def test_dirty_flag_tracked_only(repo):
    assert provenance.git_state(repo)["git_dirty"] is False
    (repo / "untracked.txt").write_text("x")
    assert provenance.git_state(repo)["git_dirty"] is False
    (repo / "a.txt").write_text("two")
    st = provenance.git_state(repo)
    assert st["git_dirty"] is True and len(st["git_head"]) == 40


def test_git_unavailable_is_unknown(tmp_path):
    st = provenance.git_state(tmp_path / "missing")
    assert st == {"git_head": "unknown", "git_dirty": None}


def test_module_hashes_match_file_bytes():
    prov = provenance.run_provenance()
    for name in ("compare.py", "features.py", "panel.py", "evaluate.py", "models.py", "extract.py"):
        data = (provenance.HERE / name).read_bytes()
        assert prov["modules_sha256"][name] == hashlib.sha256(data).hexdigest()
    assert prov["env"]["python"] and "numpy" in prov["env"]


def test_append_only(tmp_path):
    path = tmp_path / "trials.jsonl"
    first = provenance.append_trial({"status": "ok", "dataset": "d"}, path)
    before = path.read_bytes()
    second = provenance.append_trial({"status": "ok", "dataset": "d"}, path)
    after = path.read_bytes()
    assert after.startswith(before) and after.count(b"\n") == 2
    assert first["trial_id"] != second["trial_id"]
    assert first["label"] == provenance.DEV_LABEL


def test_failed_record_roundtrip(tmp_path):
    path = tmp_path / "t.jsonl"
    provenance.append_trial({"status": "failed", "error_type": "KeyError"}, path)
    rec = json.loads(path.read_text())
    assert rec["status"] == "failed" and rec["error_type"] == "KeyError"


def test_results_contain_provenance_v2(monkeypatch):
    from astrolabe.research_lab import evaluate

    from .test_research_lab_compare import _pairs

    monkeypatch.setattr(evaluate, "MIN_TRAIN", 50)
    res = compare.run_comparison(_pairs(n=200), compare.e001_models(), n_boot=20)
    assert "provenance" in res and "provenance_v2" in res
    assert "git_dirty" in res["provenance_v2"]
    assert set(res["provenance_v2"]["modules_sha256"]) >= {"compare.py", "panel.py", "models.py"}
    assert provenance.summarize_pooled(res)
