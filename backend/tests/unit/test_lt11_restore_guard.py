# ruff: noqa: E501
"""LT11's q0690 restore guard and seal timing drafts (review 2026-10-23 must-fix 6, should-fix 11): synthetic catalogues only, no network."""

import importlib.util
import json
import sys
from collections import namedtuple
from pathlib import Path

from astrolabe.research_lab import live_tests11 as lt

_SP = Path(__file__).resolve().parents[2] / "scripts" / "lt11_restore_guard.py"
_spec = importlib.util.spec_from_file_location("lt11_restore_guard", _SP)
G = importlib.util.module_from_spec(_spec)
sys.modules["lt11_restore_guard"] = G
_spec.loader.exec_module(G)
DRAFTS = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "drafts"
DU = namedtuple("DU", "total used free")


def _cat(tmp_path, rows):
    c = tmp_path / "cat"
    c.mkdir()
    (c / "rel1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return c


ROWS = [{"bytes": 600, "capture_time_utc": "2026-10-28T00:31:00Z", "dir": "snapshots", "path": "data-dumps/research_lab/snapshots/20261028T003100Z_a/rows.csv.gz", "sha256": "x"},
        {"bytes": 400, "capture_time_utc": "2026-10-28T02:31:00Z", "dir": "snapshots", "path": "data-dumps/research_lab/snapshots/20261028T023100Z_b/rows.csv.gz", "sha256": "y"},
        {"bytes": 9999, "capture_time_utc": "2026-10-20T00:31:00Z", "dir": "snapshots", "path": "data-dumps/research_lab/snapshots/20261020T003100Z_c/rows.csv.gz", "sha256": "z"}]


def _args(tmp_path, cat):
    return ["--since", "2026-10-26", "--until", "2026-11-07T06:00:00Z", "--path-glob", "data-dumps/research_lab/snapshots/2026102*/rows.csv.gz", "--catalogue", str(cat),
            "--dest", str(tmp_path / "restore")]


def test_guard_stops_before_any_restore_when_the_disk_is_too_small(tmp_path, monkeypatch, capsys):
    cat = _cat(tmp_path, ROWS)
    called = []
    monkeypatch.setattr(G.shutil, "disk_usage", lambda p: DU(10**9, 0, 1500))
    rc = G.main(["--reserve-gb", "0", *_args(tmp_path, cat)], restore_main=lambda a: called.append(a) or 0)
    out = capsys.readouterr().out
    assert rc == 0 and len(called) == 1 and '"bytes": 1000' in out  # 600 + 400 selected, the 2026-10-20 row is outside --since
    called.clear()
    monkeypatch.setattr(G.shutil, "disk_usage", lambda p: DU(10**9, 0, 999))
    rc = G.main(["--reserve-gb", "0", *_args(tmp_path, cat)], restore_main=lambda a: called.append(a) or 0)
    assert rc == G.STOP and not called and "STOP AND ASK THE OWNER" in capsys.readouterr().out
    monkeypatch.setattr(G.shutil, "disk_usage", lambda p: DU(10**12, 0, 2**30 + 500))
    assert G.main(_args(tmp_path, cat), restore_main=lambda a: called.append(a) or 0) == G.STOP and not called  # the 1 GiB default reserve
    assert not (tmp_path / "restore").exists()


def test_guard_stops_when_a_row_cannot_be_measured_and_passes_args_unchanged(tmp_path, monkeypatch, capsys):
    cat = _cat(tmp_path, [{**ROWS[0], "bytes": None}, ROWS[1]])
    monkeypatch.setattr(G.shutil, "disk_usage", lambda p: DU(10**12, 0, 10**12))
    called = []
    assert G.main(_args(tmp_path, cat), restore_main=lambda a: called.append(a) or 0) == G.STOP and not called
    cat2 = tmp_path / "c2"
    cat2.mkdir()
    (cat2 / "rel1.jsonl").write_text(json.dumps(ROWS[0]) + "\n")
    a = _args(tmp_path, cat2)
    assert G.main(["--reserve-gb", "0", *a], restore_main=lambda x: called.append(x) or 7) == 7 and called == [a]
    assert G.main(["--measure-only", "--reserve-gb", "0", *a], restore_main=lambda x: called.append(x) or 0) == 0 and len(called) == 1


def test_q0690_runs_through_the_guard():
    q = json.loads((DRAFTS / "q0690_lt11_census_restore.json").read_text())
    assert q["argv"][0] == "scripts/lt11_restore_guard.py" and "--dest" in q["argv"] and "STOP AND ASK THE OWNER" in q["next_action"]
    assert q["not_before"] == "2026-11-07T03:00:00Z"  # section 7's own value for q0690


def test_q0691_seal_not_before_is_after_the_bound_plus_capture_completion():
    """Must-fix 6: q0691 may run only after every capture started before the sealed bound (06:00Z) can have completed (the 109-minute reader margin)."""
    q = json.loads((DRAFTS / "q0691_lt11_seal.json").read_text())
    spec = lt.load_spec(sha=None)
    bound = lt.epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    assert lt.epoch(q["not_before"]) >= bound + 109 * 60
    last_twin = lt.epoch(spec["census_inputs"]["span"]["last_slot_utc"]) + 3 * 7200  # 2026-11-07T04:31Z
    assert last_twin < bound <= lt.epoch(q["not_before"])
    assert q["depends_on"] == ["q0690_lt11_census_restore"]
