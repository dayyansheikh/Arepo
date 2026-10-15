# ruff: noqa: E501, UP031
"""restore_from_archive.py and data_catalogue.py on tiny synthetic archives (no network, needs the zstd binary)."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import restore_from_archive as rfa  # noqa: E402

from astrolabe.research_lab import data_catalogue as dc  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("zstd") is None, reason="zstd binary not installed")

SNAP = "data-dumps/research_lab/snapshots/20261015T163101Z_ec288b0f/"
FILES = {
    SNAP + "manifest.json": b'{"state": "complete"}',
    SNAP + "rows.csv.gz": os.urandom(5000),
    "data-dumps/research_lab/snapshots/20261015T143101Z_7e95a63c/rows.csv.gz": os.urandom(3000),
    "data-dumps/research_lab/book_sweeps/20261014T010752Z_0c287bab/rows.csv.gz": os.urandom(2000),
    "data-dumps/research_lab/cross_venue_live/quotes/20261015.jsonl": b'{"q": 1}\n' * 50,
}


def _h(b):
    return hashlib.sha256(b).hexdigest()


def build_release(tmp_path, tag="data-test", corrupt=False):
    base = tmp_path / "live"
    for rel, body in FILES.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
    tarp = tmp_path / "a.tar"
    with tarfile.open(str(tarp), "w", format=tarfile.PAX_FORMAT) as t:
        for rel in sorted(FILES):
            t.add(str(base / rel), arcname=rel)
    z = subprocess.run(["zstd", "-q", "--long=27", "-c", str(tarp)], stdout=subprocess.PIPE, check=True).stdout
    rel_dir = tmp_path / "release"
    rel_dir.mkdir()
    half = len(z) // 2
    parts = {"arepo-%s.tar.zst.part-aa" % tag: z[:half], "arepo-%s.tar.zst.part-ab" % tag: z[half:]}
    man = []
    for n, b in parts.items():
        man.append("%s  %s\n" % (_h(b), n))
        (rel_dir / n).write_bytes(b if not (corrupt and n.endswith("ab")) else b[:-1] + bytes([b[-1] ^ 1]))
    fs = "".join("%s  %s\n" % (_h(FILES[r]), r) for r in sorted(FILES))
    (rel_dir / "files.sha256").write_text(fs)
    man.append("%s  files.sha256\n" % _h(fs.encode()))
    (rel_dir / "MANIFEST.sha256").write_text("".join(man))
    cat = tmp_path / "cat"
    cat.mkdir()
    rows = dc.build_rows(tag, {r: _h(b) for r, b in FILES.items()}, sizes={r: len(b) for r, b in FILES.items()})
    (cat / (tag + ".jsonl")).write_text(dc.dump_jsonl(rows))
    return base, rel_dir, cat


def run(tmp_path, rel_dir, cat, *extra):
    dest = tmp_path / "dest"
    args = ["--tag", "data-test", "--parts-dir", str(rel_dir), "--catalogue", str(cat),
            "--dest", str(dest), "--workdir", str(tmp_path / "wk")] + list(extra)
    return rfa.main(args), dest


def test_classify_and_experiments():
    c = dc.classify(SNAP + "rows.csv.gz")
    assert c["dir"] == "snapshots" and c["capture_id"] == "20261015T163101Z_ec288b0f"
    assert c["capture_time_utc"] == "2026-10-15T16:31:01Z"
    assert "E011" in c["experiments"] and "E007" in c["experiments"]
    q = dc.classify("data-dumps/research_lab/cross_venue_live/quotes/20261015.jsonl")
    assert q["date_utc"] == "2026-10-15" and q["experiments"] == ["E009", "E010"]
    assert dc.classify("data-dumps/fs2_capture_ab/x")["experiments"] == ["E001"]
    assert dc.classify("data-dumps/fs2_selection_panel_x/pages/p")["experiments"] == ["PHASE3-FS2"]


def test_restore_subset_by_experiment_dir_and_time(tmp_path):
    base, rel_dir, cat = build_release(tmp_path)
    rc, dest = run(tmp_path, rel_dir, cat, "--experiment", "E009", "--compare-with", str(base))
    assert rc == 0
    got = sorted(os.path.relpath(os.path.join(d, f), str(dest)) for d, _, fs in os.walk(str(dest)) for f in fs if not f.startswith("RESTORE_"))
    assert got == ["data-dumps/research_lab/cross_venue_live/quotes/20261015.jsonl"]
    rep = json.load(open(str(dest / "RESTORE_REPORT_data-test.json")))
    assert rep["passed"] and rep["identical_to_live"] == 1 and rep["selected"] == 1
    shutil.rmtree(str(dest))
    rc, dest = run(tmp_path, rel_dir, cat, "--dir", "snapshots", "--since", "2026-10-15T16:00", "--until", "2026-10-15T17:00")
    assert rc == 0
    assert (dest / SNAP / "rows.csv.gz").read_bytes() == FILES[SNAP + "rows.csv.gz"]
    assert not (dest / "data-dumps/research_lab/snapshots/20261015T143101Z_7e95a63c").exists()


def test_whole_release_and_glob(tmp_path):
    base, rel_dir, cat = build_release(tmp_path)
    rc, dest = run(tmp_path, rel_dir, cat, "--path-glob", "*book_sweeps*")
    assert rc == 0 and len(list(dest.rglob("rows.csv.gz"))) == 1
    shutil.rmtree(str(dest))
    rc, dest = run(tmp_path, rel_dir, cat)
    assert rc == 0
    assert all((dest / r).read_bytes() == b for r, b in FILES.items())


def test_corrupt_part_fails(tmp_path):
    base, rel_dir, cat = build_release(tmp_path, corrupt=True)
    rc, dest = run(tmp_path, rel_dir, cat)
    assert rc == 1


def test_refuses_overwrite_and_detects_changed_live(tmp_path):
    base, rel_dir, cat = build_release(tmp_path)
    rc, dest = run(tmp_path, rel_dir, cat, "--experiment", "E009")
    assert rc == 0
    with pytest.raises(SystemExit):
        run(tmp_path, rel_dir, cat, "--experiment", "E009")
    (base / "data-dumps/research_lab/cross_venue_live/quotes/20261015.jsonl").write_bytes(b"changed")
    rc, _ = run(tmp_path, rel_dir, cat, "--experiment", "E009", "--overwrite", "--compare-with", str(base))
    assert rc == 1  # restored bytes differ from the (modified) live copy


def test_catalogue_hash_disagreement_aborts(tmp_path):
    base, rel_dir, cat = build_release(tmp_path)
    p = cat / "data-test.jsonl"
    rows = dc.load_jsonl(str(p))
    rows[0]["sha256"] = "0" * 64
    p.write_text(dc.dump_jsonl(rows))
    with pytest.raises(SystemExit):
        run(tmp_path, rel_dir, cat, "--dir", "book_sweeps", "--dir", "snapshots", "--dir", "cross_venue_live")
