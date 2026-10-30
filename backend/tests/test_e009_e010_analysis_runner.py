"""run_e009_e010_analysis.py (queue wrapper) on synthetic, schema-shaped lines only."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import cross_venue_gapfill as gf
from astrolabe.research_lab import cross_venue_live as cvl
from astrolabe.research_lab import cross_venue_live_e010 as e010

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_e009_e010_analysis.py"
SPEC = importlib.util.spec_from_file_location("run_e009_e010_analysis", SCRIPT)
rn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rn)

CLEAN = ("abc123", [])
AFTER = datetime.fromisoformat("2026-11-03T09:00:00+00:00").timestamp()


def ep(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def P(hm, pid, day="2026-10-13", e10=False):
    t = ep(f"{day}T{hm}:00Z")
    hs = (60, 360) if e10 else (10, 20, 60)
    r = {"id": f"{pid}|{t}", "pid": pid, "ev": f"E{pid}", "t": t, "kr": t + 1.0, "pr": t + 2.0,
         "km": 0.51, "pm": 0.5, "pb": 0.49, "pa": 0.51, "f": {"dk1": 0.01},
         "y0": {str(h): 0.0 for h in hs}, "y1": {str(h): 0.001 for h in hs},
         "side": 1, "cost": 0.02, "trade": False, "fee": 0.0, "role": "prospective_confirmation",
         "spec": "s", "code": "c", "v": "v"}
    if e10:
        r["yg"] = {str(h): 0.0 for h in hs}
        r["side"] = {str(h): 1 for h in hs}
        r["trade"] = {str(h): False for h in hs}
    return r


def Out(r, h, status="evaluated"):
    o = {"id": r["id"], "pid": r["pid"], "ev": r["ev"], "h": h, "t0": r["t"],
         "due": r["t"] + h * 60, "role": r["role"], "written_utc": "x", "status": status}
    if status == "evaluated":
        o.update({"t_obs": r["t"] + h * 60, "p_recv": r["t"] + h * 60 + 2, "pm_h": 0.5,
                  "pb_h": 0.49, "pa_h": 0.51, "dp": 0.0, "pnl_taker": -0.02, "pnl_trade": None})
    return o


@pytest.fixture
def srcs(tmp_path):
    can, cop = tmp_path / "live" / "cross_venue_live", tmp_path / "val" / "cross_venue_live"
    can.mkdir(parents=True)
    cop.mkdir(parents=True)
    A, B = P("12:00", "a", "2026-10-15"), P("00:00", "b", "2026-10-14")
    X = P("05:00", "x", "2026-10-14")
    H, I_ = P("12:00", "h", "2026-10-15", e10=True), P("09:00", "i", "2026-10-14", e10=True)
    cvl.append_jsonl(can / "predictions.jsonl", [A, B])
    cvl.append_jsonl(can / "outcomes.jsonl", [Out(A, 20), Out(B, 20, "unavailable")])
    cvl.append_jsonl(can / e010.PRED_FILE, [H])
    cvl.append_jsonl(can / e010.OUT_FILE, [Out(H, 60), Out(H, 360)])
    cvl.append_jsonl(cop / "predictions.jsonl", [B, X])
    cvl.append_jsonl(cop / "outcomes.jsonl", [Out(B, 20), Out(X, 20)])
    cvl.append_jsonl(cop / e010.PRED_FILE, [I_])
    cvl.append_jsonl(cop / e010.OUT_FILE, [Out(I_, 60)])
    # the poller is mid-write: the canonical predictions file ends in a partial line
    with (can / "predictions.jsonl").open("a") as f:
        f.write('{"id": "partial|1", "t": 17')
    expect = {f: rn.digest(cop / f)["sha256"] for f in rn.FILES}
    t = ep("2026-11-03T08:00:00Z")  # the poller wrote after 05:05Z on the day
    for f in rn.FILES:
        os.utime(can / f, (t, t))
    return can, cop, expect


def test_registered_constants():
    assert rn.EXPS["e009"]["start"] == cvl.REGISTERED_UTC == "2026-10-13T00:00:00Z"
    assert rn.EXPS["e010"]["start"] == e010.REGISTERED_UTC
    assert rn.EXPS["e009"]["end"] == rn.EXPS["e010"]["end"] == e010.END_UTC
    assert rn.EXPS["e009"]["not_before"] == "2026-11-03T02:00:00Z"
    assert rn.EXPS["e010"]["not_before"] == rn.FREEZE_NOT_BEFORE == "2026-11-03T08:00:00Z"
    assert (rn.EXPS["e009"]["files"] + rn.EXPS["e010"]["files"]
            == ("predictions.jsonl", "outcomes.jsonl", e010.PRED_FILE, e010.OUT_FILE))
    assert gf.RULE_ID == "gapfill-v2"
    for p in rn.REGISTERED_CODE:
        assert (rn.REPO / p).is_file(), p


def test_dirty_tree_guard():
    assert rn.check_tree(CLEAN)["dirty_tracked"] == []
    assert rn.check_tree(("h", ["docs/research_lab/trials.jsonl"]))["dirty_tracked"]
    with pytest.raises(rn.Refusal):
        rn.check_tree(("h", ["docs/research_lab/trials.jsonl",
                             "backend/astrolabe/research_lab/cross_venue_live.py"]))
    with pytest.raises(rn.Refusal):
        rn.check_tree(("", []))


def test_freeze_refusals(srcs, tmp_path):
    can, cop, expect = srcs
    early = AFTER - 2 * 3600  # 07:00Z
    with pytest.raises(rn.Refusal) as e:
        rn.freeze(tmp_path / "run", can, cop, now=early, expect_copy=expect, state=CLEAN)
    assert e.value.code == rn.TEMPFAIL and not (tmp_path / "run").exists()
    with pytest.raises(rn.Refusal, match="validation copy"):
        rn.freeze(tmp_path / "run", can, cop, now=AFTER,
                  expect_copy={**expect, "outcomes.jsonl": "0" * 64}, state=CLEAN)
    assert not (tmp_path / "run").exists()
    with pytest.raises(rn.Refusal, match="inside"):
        rn.freeze(can / "run", can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    (tmp_path / "run").mkdir()
    with pytest.raises(rn.Refusal, match="exists"):
        rn.freeze(tmp_path / "run", can, cop, now=AFTER, expect_copy=expect, state=CLEAN)


def test_pipeline_end_to_end(srcs, tmp_path):
    can, cop, expect = srcs
    before = {p: p.read_bytes() for d in (can, cop) for p in d.iterdir()}
    run = tmp_path / "analysis"
    fm = rn.freeze(run, can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    # partial tail dropped, every other byte kept; the sources are untouched
    fz = fm["files"]["canonical/predictions.jsonl"]
    assert fz["partial_tail_bytes_dropped"] == len('{"id": "partial|1", "t": 17')
    assert fz["lines"] == 2
    assert (run / "inputs/canonical/predictions.jsonl").read_bytes() == \
        (can / "predictions.jsonl").read_bytes()[: fz["bytes"]]
    assert fm["files"]["copy/outcomes.jsonl"]["sha256"] == expect["outcomes.jsonl"]
    assert {p: p.read_bytes() for d in (can, cop) for p in d.iterdir()} == before

    # merge on the frozen copies; trials.jsonl dirt -> --allow-dirty, disclosed
    rec = rn.merge(run, state=("abc123", ["docs/research_lab/trials.jsonl"]))
    assert rec["rc"] == 0 and "--allow-dirty" in rec["argv"]
    mm = json.loads((run / "merged/MERGE_MANIFEST.json").read_text())
    assert mm["rule_id"] == "gapfill-v2" and mm["inputs_unchanged_after_merge"] is True
    assert mm["counts"]["E009"]["r2_predictions_added"] == 1
    with pytest.raises(rn.Refusal, match="once"):
        rn.merge(run, state=CLEAN)

    # E009 may run from 02:00Z, E010 only from 08:00Z
    with pytest.raises(rn.Refusal) as e:
        rn.analyze(run, "e010", "primary", now=AFTER - 2 * 3600, state=CLEAN)
    assert e.value.code == rn.TEMPFAIL
    outs = {}
    for exp in ("e009", "e010"):
        for label in ("primary", "sensitivity"):
            r = rn.analyze(run, exp, label, now=AFTER, state=CLEAN)
            assert r["rc"] == 0 and r["argv"][-3:] == [rn.EXPS[exp]["flag"],
                                                       rn.EXPS[exp]["start"], rn.EXPS[exp]["end"]]
            want_root = run / ("merged" if label == "primary" else "inputs/canonical")
            assert r["root"] == str(want_root)
            f = run / "results" / f"{exp}_{label}.json"
            outs[(exp, label)] = json.loads(f.read_bytes())
            assert r["output"]["sha256"] == rn.digest(f)["sha256"]
    # the merged root carries the copy origin in W; the canonical one does not
    assert outs[("e009", "primary")] != outs[("e009", "sensitivity")]
    with pytest.raises(rn.Refusal, match="once"):
        rn.analyze(run, "e009", "primary", now=AFTER, state=CLEAN)

    v = rn.verdicts(run, state=CLEAN)
    assert set(v["primary"]) == set(v["sensitivity"]) == {"E009", "E010"}
    assert v["primary"]["E009"]["verdict"] == "Unavailable"  # tiny synthetic sample
    assert (run / "results/VERDICTS.json").is_file()
    with pytest.raises(rn.Refusal):
        rn.verdicts(run, state=CLEAN)


def test_analyze_refuses_changed_inputs(srcs, tmp_path):
    can, cop, expect = srcs
    run = tmp_path / "analysis"
    rn.freeze(run, can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    with pytest.raises(rn.Refusal, match="merge first"):
        rn.analyze(run, "e009", "primary", now=AFTER, state=CLEAN)
    with (run / "inputs/canonical/outcomes.jsonl").open("a") as f:
        f.write("{}\n")
    with pytest.raises(rn.Refusal, match="differ"):
        rn.analyze(run, "e009", "sensitivity", now=AFTER, state=CLEAN)
    assert not (run / "results/e009_sensitivity.json").exists()
    with pytest.raises(rn.Refusal, match="differ"):
        rn.merge(run, state=CLEAN)


def test_queue_drafts_are_consistent():
    drafts = rn.REPO / "docs" / "research_lab" / "queue" / "drafts"
    specs = {s["id"]: s
             for s in (json.loads(p.read_text()) for p in drafts.glob("q077[0-9]_*.json"))}
    assert len(specs) == 8
    for s in specs.values():
        assert (rn.BACKEND / s["argv"][0]).is_file() and s["argv"][0].startswith("scripts/")
        assert all(isinstance(s[k], int) for k in ("timeout_s", "max_retries", "priority"))
        assert s["not_before"] >= rn.FREEZE_NOT_BEFORE
        assert all(d in specs for d in s["depends_on"])
        if s["argv"][0] == "scripts/run_e009_e010_analysis.py":
            assert s["argv"][s["argv"].index("--run-dir") + 1] == \
                "../data-dumps/research_lab/e009_e010_analysis"
        if "analyze" in s["argv"]:
            assert s["max_retries"] == 0
    heavy = [s for s in specs.values() if s["resources"]["mem_mb"] >= 2000]
    assert {s["id"] for s in heavy} == {"q0772_e009_primary", "q0773_e009_sensitivity"}
    assert all(s["resources"].get("exclusive") for s in heavy)


def test_pins_match_current_files_and_refuse_mismatch(monkeypatch):
    t = rn.check_tree(CLEAN)
    assert len(rn.REGISTERED_PINS) == 7
    assert t["registered_code_sha256"] == rn.REGISTERED_PINS
    assert set(t["imported_modules_sha256"]) == set(rn.IMPORTED_MODULES)
    assert all(t["imported_modules_sha256"].values())
    assert isinstance(t["economics_differs_from_9beda37e"], bool)
    assert rn.digest(rn.REPO / rn.RULE_DOC)["sha256"] == rn.RULE_DOC_SHA256
    pins = dict(rn.REGISTERED_PINS)
    first = next(iter(pins))
    pins[first] = "0" * 64
    monkeypatch.setattr(rn, "REGISTERED_PINS", pins)
    with pytest.raises(rn.Refusal, match="pinned") as e:
        rn.check_tree(CLEAN)
    assert e.value.code == rn.REFUSED != rn.TEMPFAIL


def test_modules_recorded_not_enforced(monkeypatch):
    monkeypatch.setattr(rn, "ECONOMICS_9BEDA37E_SHA256", "0" * 64)
    assert rn.check_tree(CLEAN)["economics_differs_from_9beda37e"] is True


def test_pin_mismatch_refuses_every_step(srcs, tmp_path, monkeypatch):
    can, cop, expect = srcs
    monkeypatch.setattr(rn, "REGISTERED_PINS", {**rn.REGISTERED_PINS,
                                                 next(iter(rn.REGISTERED_PINS)): "0" * 64})
    with pytest.raises(rn.Refusal) as e:
        rn.freeze(tmp_path / "r", can, cop, now=AFTER, expect_copy=expect)
    assert e.value.code == rn.REFUSED and not (tmp_path / "r").exists()
    monkeypatch.undo()
    run = tmp_path / "analysis"
    rn.freeze(run, can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    rn.merge(run, state=CLEAN)
    monkeypatch.setattr(rn, "REGISTERED_PINS", {**rn.REGISTERED_PINS,
                                                 next(iter(rn.REGISTERED_PINS)): "0" * 64})
    for call in (lambda: rn.merge(tmp_path / "x"), lambda: rn.verdicts(run),
                 lambda: rn.analyze(run, "e009", "sensitivity", now=AFTER)):
        with pytest.raises(rn.Refusal) as e:
            call()
        assert e.value.code in (rn.REFUSED,)


def test_freeze_records_catchup_and_refuses_stale(srcs, tmp_path):
    can, cop, expect = srcs
    fm = rn.freeze(tmp_path / "ok", can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    c = fm["catchup_check"]
    assert c["poller_caught_up"] is True and set(c["files"]) == {"outcomes.jsonl",
                                                                   "outcomes_e010.jsonl"}
    assert c["files"]["outcomes.jsonl"]["mtime_utc"] == "2026-11-03T08:00:00Z"
    assert c["files"]["outcomes.jsonl"]["written_recently"] is True
    assert json.loads((tmp_path / "ok/inputs/FREEZE_MANIFEST.json").read_text())["catchup_check"]
    old = ep("2026-11-03T05:04:00Z")
    os.utime(can / "outcomes_e010.jsonl", (old, old))
    with pytest.raises(rn.Refusal, match="caught up") as e:
        rn.freeze(tmp_path / "late", can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    assert e.value.code == rn.TEMPFAIL and not (tmp_path / "late").exists()


def test_rule_doc_pin_and_child_75(srcs, tmp_path, monkeypatch):
    can, cop, expect = srcs
    run = tmp_path / "analysis"
    rn.freeze(run, can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    rn.merge(run, state=CLEAN)
    mp = run / "merged/MERGE_MANIFEST.json"
    mm = json.loads(mp.read_text())
    mm["rule_doc_sha256"] = "1" * 64
    mp.write_text(json.dumps(mm))
    with pytest.raises(rn.Refusal, match="rule_doc_sha256"):
        rn.analyze(run, "e009", "primary", now=AFTER, state=CLEAN)
    assert rn._child_code(75) == 1 and rn._child_code(0) == 1 and rn._child_code(3) == 3

    class P:
        returncode, stdout, stderr = 75, b"", b"x"

    monkeypatch.setattr(rn.subprocess, "run", lambda *a, **k: P())
    with pytest.raises(rn.Refusal) as e:
        rn.analyze(run, "e009", "sensitivity", now=AFTER, state=CLEAN)
    assert e.value.code == 1


def test_failure_records_are_timestamped_and_never_overwritten(srcs, tmp_path, monkeypatch):
    can, cop, expect = srcs
    run = tmp_path / "analysis"
    rn.freeze(run, can, cop, now=AFTER, expect_copy=expect, state=CLEAN)

    class P:
        returncode, stdout, stderr = 1, b"", b"boom"

    monkeypatch.setattr(rn.subprocess, "run", lambda *a, **k: P())
    monkeypatch.setattr(rn, "_stamp", lambda t=None: "20261103T090000Z")  # same second twice
    for _ in range(2):
        with pytest.raises(rn.Refusal):
            rn.analyze(run, "e009", "sensitivity", now=AFTER, state=CLEAN)
    fails = sorted(p.name for p in (run / "results").glob("e009_sensitivity.failed-*.json"))
    assert fails == ["e009_sensitivity.failed-20261103T090000Z-1.json",
                     "e009_sensitivity.failed-20261103T090000Z.json"]
    assert not (run / "results/e009_sensitivity.json").exists()


def test_failed_merge_leaves_no_permanent_marker_and_can_be_retried(srcs, tmp_path, monkeypatch):
    can, cop, expect = srcs
    run = tmp_path / "analysis"
    rn.freeze(run, can, cop, now=AFTER, expect_copy=expect, state=CLEAN)
    real = subprocess.run

    class P:
        returncode, stdout, stderr = 2, b"", b"refused: dirty"

    monkeypatch.setattr(rn.subprocess, "run", lambda *a, **k: P())
    with pytest.raises(rn.Refusal) as e:
        rn.merge(run, state=("abc123", ["docs/research_lab/trials.jsonl"]))
    assert e.value.code == rn.TEMPFAIL  # CLI exit 2 -> retryable
    assert not (run / "MERGE_RUN.json").exists() and not (run / "merged").exists()
    assert len(list(run.glob("MERGE_RUN.failed-*.json"))) == 1
    monkeypatch.setattr(rn.subprocess, "run", real)
    # trials.jsonl dirt appearing between checks no longer matters: --allow-dirty is always passed
    rec = rn.merge(run, state=("abc123", ["docs/research_lab/trials.jsonl"]))
    assert rec["rc"] == 0 and "--allow-dirty" in rec["argv"]
    assert (run / "MERGE_RUN.json").is_file()
    with pytest.raises(rn.Refusal):  # a non-allowed dirty file is still refused before the call
        rn.merge(tmp_path / "nope", state=("h", ["backend/x.py"]))
