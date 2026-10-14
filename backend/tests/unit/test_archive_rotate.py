"""Safety tests for scripts/archive_rotate.py deletion pass (GitHub calls are faked)."""

import argparse
import hashlib
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import archive_rotate as rot  # noqa: E402


def _h(b):
    return hashlib.sha256(b).hexdigest()


def _setup(tmp_path, monkeypatch, remote_files, draft=False, manifest_hash="m1"):
    root = tmp_path / "root"
    d = root / "data-dumps" / "research_lab" / "x"
    d.mkdir(parents=True)
    old = time.time() - 30 * 86400
    for name, body in {"a.csv": b"aaa", "b.csv": b"bbb", "c.csv": b"ccc"}.items():
        (d / name).write_bytes(body)
        os.utime(d / name, (old, old))
    state = tmp_path / "state"
    state.mkdir()

    def fake_fetch(repo, tag, dest):
        os.makedirs(dest, exist_ok=True)
        (open(os.path.join(dest, "MANIFEST.sha256"), "w")).write("x")
        return {"files.sha256": "f"}, dict(remote_files), []

    monkeypatch.setattr(rot.ar, "fetch_meta", fake_fetch)
    monkeypatch.setattr(rot.ar, "release_assets", lambda r, t: ({}, draft))
    monkeypatch.setattr(
        rot.ar,
        "sha256_file",
        lambda p: "m1" if p.endswith("MANIFEST.sha256") else _h(open(p, "rb").read()),
    )
    a = argparse.Namespace(
        root=str(root), older_than_days=7, workdir=str(tmp_path / "w"), dry_run=False
    )
    return a, root, state, manifest_hash


def test_deletes_only_verified_matching_files(tmp_path, monkeypatch):
    files = {
        "data-dumps/research_lab/x/a.csv": _h(b"aaa"),
        "data-dumps/research_lab/x/b.csv": _h(b"WRONG"),
    }
    a, root, state, mh = _setup(tmp_path, monkeypatch, files)
    ledger = [{"tag": "t", "repo": "r", "manifest_sha256": mh, "files": files}]
    rot.delete_verified(a, str(state), ledger)
    base = root / "data-dumps" / "research_lab" / "x"
    assert not (base / "a.csv").exists()  # verified + hash match -> deleted
    assert (base / "b.csv").exists()  # hash differs from archive -> kept
    assert (base / "c.csv").exists()  # not in any verified release -> untouched
    log = [json.loads(x) for x in open(state / "deletions.jsonl")]
    assert {r["action"] for r in log} == {"deleted", "kept"}
    assert [r["sha256"] for r in log if r["action"] == "deleted"] == [_h(b"aaa")]


def test_refuses_when_release_changed_or_draft(tmp_path, monkeypatch):
    files = {"data-dumps/research_lab/x/a.csv": _h(b"aaa")}
    a, root, state, _ = _setup(tmp_path, monkeypatch, files)
    with pytest.raises(SystemExit):
        rot.delete_verified(
            a, str(state), [{"tag": "t", "repo": "r", "manifest_sha256": "other", "files": files}]
        )
    a, root, state, mh = _setup(tmp_path / "2", monkeypatch, files, draft=True)
    with pytest.raises(SystemExit):
        rot.delete_verified(
            a, str(state), [{"tag": "t", "repo": "r", "manifest_sha256": mh, "files": files}]
        )
    assert (root / "data-dumps" / "research_lab" / "x" / "a.csv").exists()


def test_dry_run_deletes_nothing(tmp_path, monkeypatch):
    files = {"data-dumps/research_lab/x/a.csv": _h(b"aaa")}
    a, root, state, mh = _setup(tmp_path, monkeypatch, files)
    a.dry_run = True
    rot.delete_verified(
        a, str(state), [{"tag": "t", "repo": "r", "manifest_sha256": mh, "files": files}]
    )
    assert (root / "data-dumps" / "research_lab" / "x" / "a.csv").exists()
