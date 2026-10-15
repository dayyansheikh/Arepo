"""Safety tests for scripts/archive_rotate.py deletion pass (GitHub calls are faked)."""
# ruff: noqa: E501

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


def test_retention_rules_per_directory(tmp_path, monkeypatch):
    files = {}
    root = tmp_path / "root"
    layout = {
        "data-dumps/research_lab/snapshots/c1/rows.csv.gz": (b"rows", 20),  # past its 8 days
        "data-dumps/research_lab/snapshots/c1/manifest.json": (b"man", 20),  # stub kept by glob
        "data-dumps/research_lab/snapshots/c2/rows.csv.gz": (b"new", 3),  # inside its 8 days
        "data-dumps/research_lab/history/h/x.csv": (b"hist", 90),  # directory without a rule
    }
    for rel, (body, age) in layout.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        t = time.time() - age * 86400
        os.utime(p, (t, t))
        files[rel] = _h(body)
    rules = {
        "rules": [
            {
                "prefix": "data-dumps/research_lab/snapshots/",
                "older_than_days": 8,
                "keep": ["*/manifest.json"],
            }
        ]
    }
    (tmp_path / "ret.json").write_text(json.dumps(rules))
    a, _, state, mh = _setup(tmp_path / "s", monkeypatch, files)
    a.root, a.retention = str(root), str(tmp_path / "ret.json")
    ledger = [{"tag": "t", "repo": "r", "manifest_sha256": mh, "files": files}]
    rot.delete_verified(a, str(state), ledger)
    snaps = root / "data-dumps/research_lab/snapshots"
    assert not (snaps / "c1/rows.csv.gz").exists()
    assert (snaps / "c1/manifest.json").exists()
    assert (snaps / "c2/rows.csv.gz").exists()
    assert (root / "data-dumps/research_lab/history/h/x.csv").exists()
    log = [json.loads(x) for x in open(state / "deletions.jsonl")]
    assert [r["path"] for r in log if r["action"] == "deleted"] == [
        "data-dumps/research_lab/snapshots/c1/rows.csv.gz"
    ]


def test_retention_rule_minimum_two_days(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"rules": [{"prefix": "x/", "older_than_days": 1}]}))
    with pytest.raises(SystemExit):
        rot.load_rules(str(p))


# ---- --include-active: point-in-time copies of append-only logs ----

LOG = "data-dumps/research_lab/cross_venue_live/predictions.jsonl"


def test_copy_prefix_stops_at_last_newline(tmp_path):
    src = tmp_path / "live.jsonl"
    src.write_bytes(b'{"a":1}\n{"b":2}\n{"c":3')  # partial trailing line
    before = (src.read_bytes(), src.stat().st_mtime_ns)
    n, h = rot.copy_prefix_to_last_newline(str(src), str(tmp_path / "copy"))
    assert (tmp_path / "copy").read_bytes() == b'{"a":1}\n{"b":2}\n'
    assert n == 16 and h == hashlib.sha256(b'{"a":1}\n{"b":2}\n').hexdigest()
    assert (src.read_bytes(), src.stat().st_mtime_ns) == before  # live file untouched
    src.write_bytes(b"no newline yet")
    assert rot.copy_prefix_to_last_newline(str(src), str(tmp_path / "c2")) == (0, None)
    assert not (tmp_path / "c2").exists()


def _active_env(tmp_path, monkeypatch):
    root = tmp_path / "root"
    f = root / LOG
    f.parent.mkdir(parents=True)
    f.write_bytes(b'{"a":1}\n{"b":2}\n{"c"')  # fresh mtime: newer than any cut-off
    state = tmp_path / "state"
    state.mkdir()
    built = {}

    def fake_build(b):
        built["members"] = [ln.strip() for ln in open(b.list)]
        built["files"] = {m: open(os.path.join(b.base, m), "rb").read() for m in built["members"]}
        built["tag"] = b.tag

    monkeypatch.setattr(rot.ar, "build", fake_build)
    monkeypatch.setattr(rot.ar, "verify", lambda b: 0)
    monkeypatch.setattr(rot.ar, "release_exists", lambda r, t: False)

    def fake_fetch(repo, tag, dest):
        os.makedirs(dest, exist_ok=True)
        open(os.path.join(dest, "MANIFEST.sha256"), "w").write("x")
        json.dump({"verified_utc": "t"}, open(os.path.join(dest, "VERIFY.json"), "w"))
        return {"files.sha256": "f"}, {m: _h(b) for m, b in built["files"].items()}, []

    monkeypatch.setattr(rot.ar, "fetch_meta", fake_fetch)
    a = argparse.Namespace(
        root=str(root), scan=["data-dumps"], exclude=[], older_than_days=1, workdir=str(tmp_path / "w"),
        include_active=["data-dumps/research_lab/cross_venue_live/predictions*.jsonl"], repo="r",
        part_size=1, level=1, long=10, threads=1, no_archive=False, dry_run=False,
    )
    return a, root, state, built


def test_include_active_snapshot_records_hash_and_length(tmp_path, monkeypatch):
    a, root, state, built = _active_env(tmp_path, monkeypatch)
    tag = rot.snapshot_active(a, str(state), [])
    assert tag and tag.endswith("-active")
    snap = [m for m in built["members"] if m.endswith("predictions.jsonl")]
    assert len(snap) == 1 and snap[0].startswith("active_snapshots/")
    assert built["files"][snap[0]] == b'{"a":1}\n{"b":2}\n'  # prefix to last newline only
    side = json.loads(built["files"][[m for m in built["members"] if m.endswith(rot.ACTIVE_SIDECAR)][0]])
    rec = side["files"][0]
    assert side["active_snapshot"] is True and rec["original_path"] == LOG
    assert rec["bytes"] == 16 and rec["sha256"] == _h(b'{"a":1}\n{"b":2}\n') and rec["copied_utc"]
    led = [json.loads(x) for x in open(state / "verified_releases.jsonl")]
    assert led[0]["active_snapshot"] is True
    assert (root / LOG).read_bytes() == b'{"a":1}\n{"b":2}\n{"c"'
    # unchanged prefix: no second snapshot
    built.clear()
    assert rot.snapshot_active(a, str(state), []) is None


def test_active_logs_never_deleted(tmp_path, monkeypatch):
    a, root, state, built = _active_env(tmp_path, monkeypatch)
    rot.snapshot_active(a, str(state), [])
    live = root / LOG
    old = time.time() - 30 * 86400
    os.utime(live, (old, old))  # now old, and byte-identical prefix is archived under the same hash
    h = _h(live.read_bytes())
    monkeypatch.setattr(rot.ar, "release_assets", lambda r, t: ({}, False))
    monkeypatch.setattr(rot.ar, "sha256_file", lambda p: "m1" if p.endswith("MANIFEST.sha256") else _h(open(p, "rb").read()))
    # a (hostile) ledger entry that lists the original path with the matching hash, and a snapshot entry
    ledger = [
        {"tag": "t", "repo": "r", "manifest_sha256": "m1", "files": {LOG: h}},
        {"tag": "t2", "repo": "r", "active_snapshot": True, "manifest_sha256": "m1", "files": {LOG: h}},
    ]
    a.older_than_days, a.dry_run = 7, False
    rot.delete_verified(a, str(state), ledger)
    assert live.exists()
    a.include_active = []  # even without the flag, the snapshot log protects the original path
    rot.delete_verified(a, str(state), ledger)
    assert live.exists()


def test_default_unchanged_without_flag(tmp_path, monkeypatch):
    a, root, state, built = _active_env(tmp_path, monkeypatch)
    cutoff = time.time() - 86400
    assert rot.select(str(root), ["data-dumps"], cutoff, rot.DEFAULT_EXCLUDES) == []  # live log skipped as before
    assert rot.select_active(str(root), ["data-dumps"], cutoff, rot.DEFAULT_EXCLUDES, []) == []
    assert "include_active" in vars(a) and rot.active_protected(str(state), []) == set()


def test_catalogue_flags_active_snapshot():
    from astrolabe.research_lab import data_catalogue as dc

    r = dc.classify("active_snapshots/20261018T043000Z/" + LOG)
    assert r["active_snapshot"] is True and r["original_path"] == LOG
    assert r["capture_time_utc"] == "2026-10-18T04:30:00Z" and r["dir"] == "cross_venue_live"
