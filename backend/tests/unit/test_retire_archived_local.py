"""Fail-closed tests for scripts/retire_archived_local.py (GitHub calls are faked)."""

import gzip
import hashlib
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import retire_archived_local as ret  # noqa: E402


def _h(b):
    return hashlib.sha256(b).hexdigest()


def _world(tmp_path, monkeypatch, rows_extra=(), part_size=10, remote_hash=None):
    base = tmp_path / "repo"
    d = base / "data-dumps" / "fs2_x" / "sub"
    d.mkdir(parents=True)
    (d / "a.json").write_bytes(b"aaa")
    (d / "b.json").write_bytes(b"bbb-changed")
    (base / "data-dumps" / "empty_before").mkdir()
    src = tmp_path / "remote"
    src.mkdir()
    rows = [
        ("data-dumps/fs2_x/sub/a.json", _h(b"aaa")),
        ("data-dumps/fs2_x/sub/b.json", _h(b"bbb")),
        *rows_extra,
    ]
    man = src / "M.tsv.gz"
    with gzip.open(man, "wt") as o:
        o.write("sha256\tbytes\trelease\tparts\tpath\n")
        for p, h in rows:
            o.write(f"{h}\t3\trel\taa..aa\t{p}\n")
    files = {p: (remote_hash or h) for p, h in rows}
    (src / "VERIFY.json").write_text(
        json.dumps(
            {
                "passed": True,
                "files_sha256": "F",
                "verified_utc": "t",
                "parts": [{"name": "x.tar.zst.part-aa", "bytes": 10}],
            }
        )
    )

    def fake_run(cmd, check=True):
        dest = cmd[cmd.index("-D") + 1]
        name = cmd[cmd.index("-p") + 1]
        shutil.copy(
            src / ("M.tsv.gz" if name.endswith(".tsv.gz") else name), os.path.join(dest, name)
        )
        return 0, "", ""

    monkeypatch.setattr(ret.ar, "run", fake_run)
    monkeypatch.setattr(
        ret.ar,
        "fetch_meta",
        lambda r, t, d: (
            os.makedirs(d, exist_ok=True),
            ({"files.sha256": "F"}, files, [("x.tar.zst.part-aa", "h")]),
        )[1],
    )
    monkeypatch.setattr(
        ret.ar, "release_assets", lambda r, t: ({"x.tar.zst.part-aa": part_size}, False)
    )
    argv = [
        "x",
        "--manifest-name",
        "M.tsv.gz",
        "--manifest-sha256",
        _h(man.read_bytes()),
        "--base",
        str(base),
        "--workdir",
        str(tmp_path / "w"),
        "--log-dir",
        str(tmp_path / "logs"),
    ]
    return base, argv


def test_dry_run_deletes_nothing(tmp_path, monkeypatch):
    base, argv = _world(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", argv)
    ret.main()
    assert (base / "data-dumps" / "fs2_x" / "sub" / "a.json").exists()


def test_confirm_requires_session(tmp_path, monkeypatch):
    base, argv = _world(tmp_path, monkeypatch)
    monkeypatch.delenv("AREPO_RETIREMENT_SESSION", raising=False)
    monkeypatch.setattr(sys, "argv", [*argv, "--confirm"])
    with pytest.raises(SystemExit):
        ret.main()
    assert (base / "data-dumps" / "fs2_x" / "sub" / "a.json").exists()


def test_confirm_deletes_only_matching_and_keeps_preexisting_empty_dirs(tmp_path, monkeypatch):
    base, argv = _world(tmp_path, monkeypatch)
    monkeypatch.setenv("AREPO_RETIREMENT_SESSION", "1")
    monkeypatch.setattr(sys, "argv", [*argv, "--confirm"])
    ret.main()
    assert not (base / "data-dumps" / "fs2_x" / "sub" / "a.json").exists()
    assert (base / "data-dumps" / "fs2_x" / "sub" / "b.json").exists()  # changed locally -> kept
    assert (base / "data-dumps" / "empty_before").is_dir()  # not touched by the sweep
    assert (base / "data-dumps").is_dir()


@pytest.mark.parametrize(
    "kw",
    [
        {"part_size": 9},  # asset size differs from VERIFY.json
        {"remote_hash": "0" * 64},  # manifest disagrees with release files.sha256
        {"rows_extra": [("data-dumps/research_lab/x.csv", "0" * 64)]},  # out of scope
        {"rows_extra": [("data-dumps/../etc/x", "0" * 64)]},  # traversal
    ],
)
def test_fails_closed(tmp_path, monkeypatch, kw):
    base, argv = _world(tmp_path, monkeypatch, **kw)
    monkeypatch.setenv("AREPO_RETIREMENT_SESSION", "1")
    monkeypatch.setattr(sys, "argv", [*argv, "--confirm"])
    with pytest.raises(SystemExit):
        ret.main()
    assert (base / "data-dumps" / "fs2_x" / "sub" / "a.json").exists()
