"""run_e011_analysis.py (queue wrapper) on synthetic, schema-shaped lines only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import surprise_snapshot as ss

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_e011_analysis.py"
SPEC = importlib.util.spec_from_file_location("run_e011_analysis", SCRIPT)
rn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rn)

CLEAN = ("abc123", [])
AFTER = datetime.fromisoformat("2026-11-11T13:30:00+00:00").timestamp()
BEFORE = datetime.fromisoformat("2026-11-11T12:59:00+00:00").timestamp()
T0 = datetime.fromisoformat("2026-10-20T00:00:00+00:00").timestamp()


def jl(rows, partial=""):
    return "".join(json.dumps(r) + "\n" for r in rows) + partial


def build(src: Path, n=40, *, unknown_every=10, bad_pass=1, tail="") -> None:
    src.mkdir(parents=True, exist_ok=True)
    alerts, outs = [], []
    for i in range(n):
        t = T0 + i * 7200
        aid = f"a{i}"
        alerts.append({"type": "alert", "alert_id": aid, "t": t + 600, "capture_t": t,
                       "market_id": f"m{i}", "event_id": f"e{i % 15}",
                       "fee_category": "unknown" if i % unknown_every == 0 else "sports",
                       "evidence_role": "prospective_confirmation"})
        for k in range(2):
            alerts.append({"type": "control", "alert_id": f"{aid}c{k}", "control_for": aid,
                           "t": t + 600, "capture_t": t, "market_id": f"c{i}{k}"})
        outs.append({"what": "label", "alert_id": aid, "status": "evaluated",
                     "hit_6h": float(i % 3 == 0), "sharp_any_6h": float(i % 2 == 0),
                     "fwd_move_6h": 0.1, "fwd_move_24h": 0.2})
        for k in range(2):
            outs.append({"what": "label", "alert_id": f"{aid}c{k}", "status": "evaluated",
                         "hit_6h": float(i % 7 == 0), "sharp_any_6h": 0.0,
                         "fwd_move_6h": 0.0, "fwd_move_24h": 0.0})
    # outside the window: must not count
    alerts.append({"type": "alert", "alert_id": "late", "t": 1.9e9, "capture_t": 1.9e9,
                   "market_id": "mx", "event_id": "ex", "fee_category": "unknown",
                   "evidence_role": "prospective_unregistered"})
    (src / "alerts.jsonl").write_text(jl(alerts, tail))
    (src / "outcomes.jsonl").write_text(jl(outs, tail))
    passes = [{"capture_id": f"c{i}", "status": "ok", "written_utc": f"2026-10-20T0{i}:31:00Z"}
              for i in range(5)]
    passes.append({"capture_id": "x", "status": "already_scored",
                   "written_utc": "2026-10-21T00:31:00Z"})
    (src / "passes.jsonl").write_text(jl(passes) + "not json\n" * bad_pass)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def src(tmp_path):
    s = tmp_path / "live" / "surprise_live"
    build(s, tail='{"type": "alert", "alert_id": "half')
    return s


def test_pins_are_the_seven_of_the_ruling_and_match_head():
    assert len(rn.REGISTERED_PINS) == 7
    assert rn.REGISTERED_PINS["backend/astrolabe/research_lab/surprise_snapshot.py"].startswith(
        "413107af")
    rn.check_tree(CLEAN)  # all seven files equal their pin in this checkout


def test_registered_constants_equal_registered_module():
    assert rn.REGISTERED_UTC == ss.REGISTERED_UTC and rn.END_UTC == ss.END_UTC
    assert rn.ROLE == "prospective_confirmation"


def test_time_refusal_is_75_before_and_ok_after(tmp_path, src):
    with pytest.raises(rn.Refusal) as e:
        rn.freeze(tmp_path / "D", src, now=BEFORE, state=CLEAN)
    assert e.value.code == 75
    with pytest.raises(rn.Refusal) as e:
        rn.analyze(tmp_path / "D", now=BEFORE, state=CLEAN)
    assert e.value.code == 75
    assert not (tmp_path / "D").exists()


def test_pin_mismatch_and_dirty_tree_are_exit_2_never_75(tmp_path, src, monkeypatch):
    pins = dict(rn.REGISTERED_PINS)
    pins["backend/astrolabe/research_lab/ml_explain.py"] = "0" * 64
    monkeypatch.setattr(rn, "REGISTERED_PINS", pins)
    with pytest.raises(rn.Refusal) as e:
        rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    assert e.value.code == 2 and "ml_explain.py" in str(e.value)
    assert not (tmp_path / "D").exists()
    monkeypatch.undo()
    with pytest.raises(rn.Refusal) as e:
        rn.freeze(tmp_path / "D", src, now=AFTER,
                  state=("abc", ["backend/astrolabe/research_lab/ml_explain.py"]))
    assert e.value.code == 2
    rn.check_tree(("abc", ["docs/research_lab/trials.jsonl"]))  # the one allowed dirty path


def test_missing_pinned_file_refuses(monkeypatch):
    pins = dict(rn.REGISTERED_PINS)
    pins["backend/astrolabe/research_lab/no_such_file.py"] = "0" * 64
    monkeypatch.setattr(rn, "REGISTERED_PINS", pins)
    with pytest.raises(rn.Refusal) as e:
        rn.check_tree(CLEAN)
    assert e.value.code == 2


def test_freeze_cuts_partial_tail_and_records_outcome_blind_counts(tmp_path, src):
    before = {f: sha(src / f) for f in ("alerts.jsonl", "outcomes.jsonl", "passes.jsonl")}
    man = rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    inp = tmp_path / "D" / "inputs"
    assert not list((tmp_path / "D").glob("inputs.partial-*"))
    assert {f: sha(src / f) for f in before} == before  # source untouched
    for f in ("alerts.jsonl", "outcomes.jsonl"):
        assert (inp / f).read_bytes().endswith(b"}\n")
        assert man["files"][f]["partial_tail_bytes_dropped"] > 0
        assert man["files"][f]["sha256"] == sha(inp / f)
    pre = json.loads((inp / "PRE_RUN.json").read_text())
    assert pre["passes"]["by_status"] == {"ok": 5, "already_scored": 1}
    assert pre["passes"]["non_ok"] == 1 and pre["passes"]["unparsable_lines"] == 1
    assert pre["passes"]["last_written_utc"] == "2026-10-21T00:31:00Z"
    assert pre["alerts_jsonl"]["window_alert_lines"] == 40  # 'late' is outside the window
    assert pre["alerts_jsonl"]["window_alert_lines_fee_category_unknown"] == 4  # i = 0,10,20,30
    assert pre["alerts_jsonl"]["alert_lines"] == 41
    assert pre["outcomes_jsonl"]["lines"] == 120
    assert man["pre_run_sha256"] == hashlib.sha256((inp / "PRE_RUN.json").read_bytes()).hexdigest()
    assert man["git_head"] == "abc123"


def test_freeze_runs_once_and_refuses_bad_sources(tmp_path, src):
    rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    with pytest.raises(rn.Refusal) as e:
        rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    assert e.value.code == 2
    with pytest.raises(rn.Refusal):
        rn.freeze(src / "D2", src, now=AFTER, state=CLEAN)  # run folder inside the source
    (src / "passes.jsonl").unlink()
    with pytest.raises(rn.Refusal):
        rn.freeze(tmp_path / "D3", src, now=AFTER, state=CLEAN)
    assert not (tmp_path / "D3").exists()


def test_analyze_runs_registered_cli_on_frozen_copy_and_is_write_once(tmp_path, src):
    rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    inp = tmp_path / "D" / "inputs"
    # the live files keep growing after the cut; the analysis must not see it
    with (src / "alerts.jsonl").open("a") as f:
        f.write(json.dumps({"type": "alert", "alert_id": "new", "t": T0 + 5, "capture_t": T0 + 5,
                            "market_id": "mnew",
                            "evidence_role": "prospective_confirmation"}) + "\n")
    rec = rn.analyze(tmp_path / "D", now=AFTER, state=CLEAN)
    out = tmp_path / "D" / "results" / "e011_analysis.json"
    expected = json.dumps(ss.analyze(root=inp), indent=1) + "\n"  # what the CLI prints
    assert out.read_text() == expected
    got = json.loads(out.read_text())
    assert got["n_alert_lines"] == 40 and got["window"] == [rn.REGISTERED_UTC, rn.END_UTC]
    assert rec["inputs_unchanged_after"] is True and rec["rc"] == 0
    assert rec["registered_code_sha256"] == rn.REGISTERED_PINS
    sp = tmp_path / "D" / "results" / "e011_secondaries_not_produced.json"
    sec = json.loads(sp.read_text())
    assert all(sec[k].startswith("not produced") for k in sec if k != "note")
    assert set(sec) >= {"c_2h_label_excess", "e_sports_vs_non_sports_split",
                        "f_control_match_composition", "g_passes_missed_and_request_timing_stats"}
    with pytest.raises(rn.Refusal) as e:  # analyse once
        rn.analyze(tmp_path / "D", now=AFTER, state=CLEAN)
    assert e.value.code == 2 and out.read_text() == expected


def test_analyze_refuses_tampered_or_missing_inputs(tmp_path, src):
    with pytest.raises(rn.Refusal):
        rn.analyze(tmp_path / "D", now=AFTER, state=CLEAN)  # no freeze
    rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    with (tmp_path / "D" / "inputs" / "outcomes.jsonl").open("a") as f:
        f.write("{}\n")
    with pytest.raises(rn.Refusal) as e:
        rn.analyze(tmp_path / "D", now=AFTER, state=CLEAN)
    assert e.value.code == 2
    assert not (tmp_path / "D" / "results").exists()


def test_failed_child_leaves_only_unique_failure_records_and_maps_75(tmp_path, src, monkeypatch):
    rn.freeze(tmp_path / "D", src, now=AFTER, state=CLEAN)
    monkeypatch.setattr(rn, "CHILD_BOOT", "import sys; sys.stderr.write('boom'); sys.exit(75)")
    with pytest.raises(rn.Refusal) as e:
        rn.analyze(tmp_path / "D", now=AFTER, state=CLEAN)
    assert e.value.code == 1  # never 75: the queue must not auto-retry a registered analysis
    with pytest.raises(rn.Refusal):
        rn.analyze(tmp_path / "D", now=AFTER, state=CLEAN)
    res = tmp_path / "D" / "results"
    fails = sorted(res.glob("e011_analysis.failed-*.json"))
    assert len(fails) == 2 and "boom" in fails[0].read_text()
    assert not (res / "e011_analysis.json").exists()
    assert not (res / "e011_analysis.run.json").exists()

