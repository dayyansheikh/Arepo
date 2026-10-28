# ruff: noqa: E501
"""The LT12 runner, the q0710 restore guard and the queue drafts q0710-q0716 (LIVE_TESTS_12.md 7, 8.4): refusals and exit codes, synthetic only (no
data-dumps, no network; the guard's restore is a stub)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from tests import lt12_synth as sy

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
DRAFTS = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "drafts"


def _load(name: str):
    sp = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


R = _load("run_live_tests12")
G = _load("lt12_restore_guard")


def test_analyze_refuses_before_the_analysis_date(capsys, tmp_path):
    assert R.main(["analyze", "--out-root", str(tmp_path), "--out", str(tmp_path / "a.json")]) == 2
    assert "refusing" in capsys.readouterr().out and not (tmp_path / "a.json").exists()


def test_analyze_requires_out(tmp_path, capsys):
    """Code-freeze check fix 6: ``analyze`` without ``--out`` is a usage error (the single analysis is never only printed, so it cannot be repeated)."""
    with pytest.raises(SystemExit) as e:
        R.main(["analyze", "--out-root", str(tmp_path)])
    assert e.value.code == 2 and "--out" in capsys.readouterr().err
    from types import SimpleNamespace

    from astrolabe.research_lab import live_tests12_analysis as an

    assert an.analyze_cli(SimpleNamespace(out=None, out_root=tmp_path), lambda *a: 0, 0.0) == 2  # defence in depth below the parser
    assert "needs --out" in capsys.readouterr().out


def test_size_check_refuses_worlds_or_draws_without_dev(capsys):
    assert R.main(["size-check", "--worlds", "5"]) == 2
    assert R.main(["size-check", "--draws", "5"]) == 2


def test_size_check_registered_refuses_unfilled_k_tests(capsys, tmp_path):
    assert R.main(["size-check", "--out", str(tmp_path / "s.json")]) == 2
    assert "k_tests" in capsys.readouterr().out and not (tmp_path / "s.json").exists()


def test_out_is_never_overwritten(tmp_path):
    p = tmp_path / "o.json"
    p.write_text("{}")
    assert R.main(["ops-stats", "--root", str(tmp_path), "--out", str(p)]) == 1
    assert p.read_text() == "{}"


def test_census_refuses_an_uncommitted_seal(tmp_path):
    s = tmp_path / "seal.json"
    s.write_text("{}")
    assert R.main(["census", "--seal", str(s), "--work", str(tmp_path / "w")]) == 2


def test_reader_exits_75_when_nothing_is_new(tmp_path):
    snap, feed, out = tmp_path / "snap", tmp_path / "feed", tmp_path / "out"
    snap.mkdir()
    assert R.main(["reader", "--snapshot-root", str(snap), "--feed-root", str(feed), "--out-root", str(out)]) == 75


def test_parser_has_every_subcommand_and_the_location_note():
    ch = R.build_parser()._subparsers._group_actions[0].choices
    assert {"header-precheck", "seal", "census", "size-check", "size-timing", "reader", "backfill-series", "ops-stats", "analyze"} <= set(ch)
    assert "LT12 ambiguity A28" in R.__doc__


def test_size_timing_refuses_the_development_seed(tmp_path, capsys):
    from astrolabe.research_lab import live_tests12_worlds as W

    assert R.main(["size-timing", "--worlds", "1", "--draws", "1", "--seed", str(W.DEV_SEED), "--out", str(tmp_path / "t.json")]) == 2
    assert "refusing" in capsys.readouterr().out and not (tmp_path / "t.json").exists()


# --- the q0710 restore guard -----------------------------------------------------------------------------------------------------------------------


def _lag_tree(tmp_path, last_state: str):
    from astrolabe.research_lab import live_tests12 as lt

    spec = lt.load_spec(sha=None)
    root = tmp_path / "snap"
    root.mkdir()
    for k in lt.lag_slots(spec):
        t = lt.b.slot_time(k, spec)
        from datetime import UTC, datetime

        dt = datetime.fromtimestamp(t, UTC)
        d = root / (dt.strftime("%Y%m%dT%H%M%SZ") + "_syn")
        d.mkdir()
        (d / "rows.csv.gz").write_bytes(b"")
        state = last_state if k == lt.lag_slots(spec)[-1] else "complete"
        (d / "manifest.json").write_text(json.dumps({"state": state, "started_utc": sy.iso(dt)}))
    return root, lt.b.slot_time(lt.lag_slots(spec)[-1], spec)


def test_guard_exits_75_while_a_lag_slot_capture_is_in_progress(tmp_path, capsys):
    root, t_last = _lag_tree(tmp_path, "running")
    called = []
    rc = G.main(["--snapshot-root", str(root), "--dest", str(tmp_path / "dest")], restore_main=lambda a: called.append(a) or 0, now=t_last + 1200.0)
    assert rc == 75 and not called and "not now" in capsys.readouterr().out


def test_guard_treats_a_failed_lag_capture_as_missing_and_proceeds_to_the_byte_measure(tmp_path, capsys):
    root, t_last = _lag_tree(tmp_path, "failed")
    cat = tmp_path / "cat"
    cat.mkdir()
    (cat / "tagA.jsonl").write_text(json.dumps({"path": "data-dumps/research_lab/snapshots/20261116T223100Z_x/rows.csv.gz", "bytes": 1000, "granularity": "file"}) + "\n")
    called = []
    rc = G.main(["--snapshot-root", str(root), "--catalogue", str(cat), "--dest", str(tmp_path / "dest")], restore_main=lambda a: called.append(a) or 0, now=t_last + 1200.0)
    out = capsys.readouterr().out
    assert rc == 0 and called and '"missing_slots": ["2026-11-17T04:31:00' in out and "lt12_restore_measure" in out


def test_guard_stops_and_asks_when_the_restore_cannot_be_measured(tmp_path, capsys):
    root, t_last = _lag_tree(tmp_path, "complete")
    cat = tmp_path / "cat"
    cat.mkdir()
    (cat / "tagA.jsonl").write_text(json.dumps({"path": "data-dumps/research_lab/snapshots/20261116T223100Z_x/rows.csv.gz", "granularity": "file"}) + "\n")  # no byte count
    called = []
    rc = G.main(["--snapshot-root", str(root), "--catalogue", str(cat), "--dest", str(tmp_path / "dest")], restore_main=lambda a: called.append(a) or 0, now=t_last + 7200.0)
    assert rc == 3 and not called and "STOP AND ASK THE OWNER" in capsys.readouterr().out


# --- the queue drafts (7, 8.4) -------------------------------------------------------------------------------------------------------------------------


def _drafts() -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted(DRAFTS.glob("q071[0-6]_lt12_*.json"))}


def test_drafts_q0710_to_q0716_exist_with_the_frozen_schedule():
    d = _drafts()
    assert set(d) == {"q0710_lt12_census_restore", "q0711_lt12_seal", "q0712_lt12_census", "q0713_lt12_size_check", "q0714_lt12_reader", "q0715_lt12_analysis", "q0716_lt12_size_timing"}
    for k, v in d.items():
        assert v["id"] == k and v["family"] == "live_tests_12" and v["max_retries"] == 1 and "DRAFT" in v["notes"]
        assert (_SCRIPTS / Path(v["argv"][0]).name).exists()
        assert "20261597" not in " ".join(v["argv"])  # no draft passes the registered seed (the size check reads it from the spec)
    r = d["q0710_lt12_census_restore"]
    assert r["not_before"] == "2026-11-17T09:00:00Z" and r["resources"]["lane"] == "net" and r["resources"]["mem_mb"] == 400 and r["resources"]["disk_mb"] == 1400
    assert r["argv"][0] == "scripts/lt12_restore_guard.py" and r["argv"][r["argv"].index("--until") + 1] == "2026-11-17T06:00:00Z"
    globs = [r["argv"][i + 1] for i, a in enumerate(r["argv"]) if a == "--path-glob"]
    assert any("20261106T" in g for g in globs) and any("20261117T" in g for g in globs) and not any("20261118T" in g for g in globs)
    assert d["q0711_lt12_seal"]["resources"]["lane"] == "net" and d["q0711_lt12_seal"]["resources"]["mem_mb"] == 300
    assert d["q0712_lt12_census"]["resources"]["lane"] == "net" and d["q0712_lt12_census"]["resources"]["mem_mb"] == 600
    assert d["q0713_lt12_size_check"]["resources"]["lane"] == "cpu" and d["q0713_lt12_size_check"]["resources"]["mem_mb"] == 800 and "--worlds" not in d["q0713_lt12_size_check"]["argv"]
    a = d["q0715_lt12_analysis"]
    assert a["not_before"] == "2027-01-01T12:00:00Z" and a["resources"]["mem_mb"] == 4000 and a["resources"]["exclusive"] is True
    assert d["q0714_lt12_reader"]["not_before"] == "2026-12-10T00:00:00Z"
    for k in ("q0711_lt12_seal", "q0712_lt12_census"):
        assert d[k]["not_before"] >= "2026-11-17T09:00:00Z"
    t = d["q0716_lt12_size_timing"]
    assert t["argv"][:2] == ["scripts/run_live_tests12.py", "size-timing"] and "--seed" not in t["argv"] and t["resources"]["mem_mb"] <= d["q0713_lt12_size_check"]["resources"]["mem_mb"]
    assert d["q0711_lt12_seal"]["depends_on"] == ["q0710_lt12_census_restore"] and d["q0712_lt12_census"]["depends_on"] == ["q0711_lt12_seal"]
    assert d["q0713_lt12_size_check"]["depends_on"] == ["q0712_lt12_census"]


@pytest.mark.parametrize("cmd", ["seal", "census", "size-check", "size-timing", "reader", "analyze"])
def test_every_draft_subcommand_parses(cmd):
    for v in _drafts().values():
        if v["argv"][0] == "scripts/run_live_tests12.py" and v["argv"][1] == cmd:
            R.build_parser().parse_args(v["argv"][1:])


def test_feed_window_and_census_dates_in_the_spec_match_the_text():
    from astrolabe.research_lab import live_tests12 as lt

    ci = lt.load_spec(sha=None)["census_inputs"]
    assert ci["span"]["start_utc"] == "2026-11-07T00:00:00Z" and ci["span"]["end_utc"] == "2026-11-17T00:00:00Z"
    assert ci["feed_window"] == ["2026-11-06T00:00:00Z", "2026-11-17T00:00:00Z"] and ci["lag_slots_after"] == 3 and ci["lookback_capture_slots"] == 12
    assert lt.iso(lt.b.slot_time(lt.lag_slots(lt.load_spec(sha=None))[-1], lt.load_spec(sha=None))).startswith("2026-11-17T04:31:00")
    assert sy.slot_dt(0) + timedelta(hours=2) == sy.slot_dt(1)
