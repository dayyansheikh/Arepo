# ruff: noqa: E501, F811
"""Freeze-check fixes 1-7 (2026-10-20) and the smoke pin / restore-root options. Synthetic data only; no host access."""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb17_b as fb
from astrolabe.research_lab import cb17_c as fc
from astrolabe.research_lab import cb17_common as c17
from astrolabe.research_lab import cb17_jobs as jobs
from astrolabe.research_lab import cb17_smoke as sm
from astrolabe.research_lab import cb17_wcommon as w
from astrolabe.research_lab import cb17_win as win
from tests.cb17_synth import print_, write_capture, write_day
from tests.cb17_wsynth import FLOOR, JobEnv, world
from tests.unit.test_research_lab_cb17_probe_ports import worn  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb17  # noqa: E402

Refused, NotNow = c17.Refused, c17.NotNow
DAY = 86400.0


def _run(argv, capsys):
    code = run_cb17.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


def _keys(env, capsys):
    code, out = _run(env.argv("exclusion-keys", "--cb16-stopped"), capsys)
    assert code == 0, out


@pytest.fixture(autouse=True)
def _reset_stopped():
    win.set_monitor_stopped([])
    yield
    win.set_monitor_stopped([])


# ---- 1: missing monitor days / snapshot files are pending, never skipped ---------------------------------------------------------------------------------


def test_missing_monitor_day_is_pending_unless_a_stopped_record_covers_it(tmp_path):
    tr = tmp_path / "live_trades"
    write_day(tr, "20261026", [print_(FLOOR + 100, "c1", 0.4, tx="t1", mkt="m1")])  # 20261027 is missing
    with pytest.raises(NotNow, match="restore.*byte for byte.*restore_from_archive"):
        list(win.iter_monitor(tr, FLOOR, FLOOR + 3600.0, Counter()))
    from astrolabe.research_lab import cb17_e as fe

    with pytest.raises(NotNow, match="byte for byte"):
        list(fe.iter_prints(tr, FLOOR, FLOOR + 3600.0, Counter()))
    rec = tmp_path / "seals"
    rec.mkdir()
    (rec / win.MONITOR_STOPPED_NAME).write_text(json.dumps({"stopped_days": ["20261027"]}))
    win.set_monitor_stopped(win.read_monitor_stopped(rec, require_committed=False))
    st = Counter()
    assert len(list(win.iter_monitor(tr, FLOOR, FLOOR + 3600.0, st))) == 1 and st["monitor_days_stopped_recorded"] == 1
    (rec / win.MONITOR_STOPPED_NAME).write_text(json.dumps({"stopped_days": ["bad"]}))
    with pytest.raises(Refused):
        win.read_monitor_stopped(rec, require_committed=False)
    with pytest.raises(Refused, match="not committed"):
        win.read_monitor_stopped(rec, require_committed=True)


def test_missing_snapshot_row_files_are_pending(tmp_path):
    d = write_capture(tmp_path / "snapshots", FLOOR + 600.0, [{"mid": "1", "cid": "c1", "eid": "E1", "bid": "0.48", "ask": "0.50"}])
    assert len(win.list_captures(tmp_path / "snapshots", FLOOR, FLOOR + DAY, Counter())) == 1
    (d / "rows_ext.csv.gz").unlink()
    with pytest.raises(NotNow, match="rows_ext.csv.gz is missing.*byte for byte"):
        win.list_captures(tmp_path / "snapshots", FLOOR, FLOOR + DAY, Counter())


def test_frame_job_exits_75_on_a_missing_day_and_runs_with_a_committed_stopped_record(tmp_path, capsys):
    env = JobEnv(tmp_path / "e")
    _keys(env, capsys)
    day = "20261030"
    (env.host / "live_trades" / f"trades-{day}.jsonl").unlink()
    now = FLOOR + 14 * DAY + 8 * 3600.0
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "screen", now=now), capsys)
    assert code == 75 and "byte for byte" in out["tempfail"] and not (env.root / "screen" / "bc" / "manifest.json").exists()
    (env.seals / win.MONITOR_STOPPED_NAME).write_text(json.dumps({"stopped_days": [day]}))
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "screen", now=now), capsys)
    assert code == 0 and out["status"] == "frame_bc_complete"


def test_rep_seal_source_listing_refuses_a_missing_declared_file(tmp_path):
    env = JobEnv(tmp_path / "e")
    W = w.windows8(env.s8)["rep"]
    lo, hi = W["read"][0], W["marks"][1]
    e = jobs.Env(root=env.root, trades=env.host / "live_trades", snaps=env.host / "snapshots", sweeps=env.host / "book_sweeps", data_dumps=env.dd, committed=False)
    assert jobs.source_files(e, lo, hi)
    cap = next(p for p in sorted((env.host / "snapshots").iterdir()) if p.is_dir() and win.c17.stamp_epoch(p.name.split("_")[0]) >= lo)
    (cap / "rows.csv.gz").unlink()
    with pytest.raises(NotNow, match="declared source file.*byte for byte"):
        jobs.source_files(e, lo, hi)


# ---- 2: smoke gated on the committed code freeze; stores code_sha256 ---------------------------------------------------------------------------------


def test_smoke_needs_the_code_freeze_and_a_smoke_of_other_code_is_refused(tmp_path, capsys):
    env = JobEnv(tmp_path / "e", with_smoke=False)
    good = json.loads(env.freeze.read_text())
    env.freeze.write_text(json.dumps({**good, "code_sha256": "0" * 64}))
    code, out = _run(env.argv("smoke"), capsys)
    assert code == 2 and "does not cover" in out["refused"]
    env.freeze.write_text(json.dumps({**good, "attestation_code_freeze": ""}))  # the attestation is NOT needed for q0404: the gate passes, the missing worn file refuses
    code, out = _run(env.argv("smoke", "--fills-dir", str(tmp_path / "none")), capsys)
    assert code == 2 and "worn source" in out["refused"]
    env2 = JobEnv(tmp_path / "e2")
    sp = env2.root / "smoke.json"
    sp.write_text(json.dumps({**json.loads(sp.read_text()), "code_sha256": "1" * 64}))
    with pytest.raises(Refused, match="other code"):
        jobs.require_smoke(jobs.Env(root=env2.root, trades=env2.host, snaps=env2.host, sweeps=env2.host, data_dumps=env2.dd), "B")


# ---- 3-5: float64 spreads, unknown is never met, econ events among flagged fills -----------------------------------------------------------------------


def test_b0_a0_are_float64_and_1c_2c_5c_spreads_are_exact_after_the_roundtrip(tmp_path):
    assert "b0" in fb.F64_COLS and "a0" in fb.F64_COLS and "b0" not in fb.FLOAT_COLS and "a0" not in fb.FLOAT_COLS
    ww = world(tmp_path, FLOOR, n_events=14, members=2, n_passes=30)
    f = fb.build_frame(ww["sw"], ww["snap"], ww["tr"], units=(FLOOR, FLOOR + 5 * DAY), read_lo=FLOOR, marks_hi=FLOOR + 5 * DAY + 8 * 3600.0, arm=0)
    a = f["arrays"]
    assert a["b0"].dtype == np.float64 and a["a0"].dtype == np.float64
    spread = a["a0"] - a["b0"]
    assert np.all(np.abs(spread - 0.02) < 1e-9)  # the synthetic touch is 0.02 wide; float32 would not give exactly this


def test_unknown_is_never_met():
    assert win.placebo_holds({"testable": False, "p": float("nan")}) is False
    assert win.placebo_holds({"testable": True, "p": 0.005}) is False and win.placebo_holds({"testable": True, "p": 0.5}) is True
    ok = {"a": True, "b": True}
    assert win.robust_met(ok, True, {"x": True}) is True
    assert win.robust_met({**ok, "c": None}, True, {"x": True}) is False  # a robustness variant that could not be computed is not met
    assert win.robust_met({**ok, "c": False}, True, {"x": True}) is False and win.robust_met(ok, False, {"x": True}) is False and win.robust_met(ok, True, {"x": False}) is False


def test_econ_event_minimum_counts_events_among_flagged_fills_only():
    rng = np.random.default_rng(3)
    n = 600
    mk = rng.integers(0, 60, n)
    ev = mk // 2  # 30 events
    flag = (ev < 5) & (rng.random(n) < 0.9)  # flagged fills lie in only 5 events; the rest fills cover the other 25
    rest = ~flag
    net = -2.0 * flag + rng.normal(0, 1.0, n)
    D = win.set_ways({}, ev, mk % 7, 1_800_000_000.0 + rng.integers(0, 14, n) * DAY)
    r = win.econ_test(net, flag, rest, mk, D, min_fills=20, min_events=10, events=ev, rest_min=None)
    assert r["verdict"] == "not run (power)" and r["events"] == len(set(ev[flag].tolist())) <= 5


# ---- 6: the B frame is written (own status) before C starts, so a budget stop resumes ------------------------------------------------------------------


def test_q0406_writes_the_b_frame_before_c_and_resumes_after_a_budget_stop(tmp_path, capsys, monkeypatch):
    env = JobEnv(tmp_path / "e")
    _keys(env, capsys)
    now = FLOOR + 14 * DAY + 8 * 3600.0
    real_c = fc.build_frame

    def stop(*a, **k):
        raise NotNow("C frame unfinished after 3 of 9 captures (budget)")

    monkeypatch.setattr(fc, "build_frame", stop)
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "screen", now=now), capsys)
    assert code == 0 and out["status"] == "frame_bc_progress" and out["complete"] is False
    mani = json.loads((env.root / "screen" / "bc" / "manifest.json").read_text())
    assert mani["status"] == jobs.B_STATUS and "b_units.npz" in mani["file_sha256"]
    monkeypatch.setattr(fc, "build_frame", real_c)

    def no_b(*a, **k):
        raise AssertionError("the B stage must not be rebuilt on resume")

    monkeypatch.setattr(fb, "build_frame", no_b)
    code, out = _run(env.argv("frame", "--families", "B,C", "--window", "screen", now=now), capsys)
    assert code == 0 and out["status"] == "frame_bc_complete" and out["units"]["B"] > 0 and out["units"]["C"] > 0
    fin = json.loads((env.root / "screen" / "bc" / "manifest.json").read_text())
    assert fin["status"] == "frame_bc_complete" and "b_units.npz" in fin["file_sha256"] and any(k.startswith("c_") for k in fin["file_sha256"])


# ---- 7: caps in every job, stage-2 pins ---------------------------------------------------------------------------------------------------------------


def test_every_job_enforces_the_total_cap_and_a_frame_output_cap(tmp_path, capsys, monkeypatch):
    env = JobEnv(tmp_path / "e")
    monkeypatch.setattr(jobs, "_tree_bytes", lambda d: int(0.299 * 1024**3))
    for cmd in (("census", "--window", "screen"), ("screen",), ("rep",), ("stage2-final",), ("exclusion-keys",), ("smoke",)):
        code, out = _run(env.argv(*cmd, now=FLOOR + 30 * DAY), capsys)
        assert code == 2 and "total cap" in out["refused"], (cmd, out)
    monkeypatch.undo()
    d = tmp_path / "creative_batch17" / "o"
    d.mkdir(parents=True)
    (d / "f").write_bytes(b"x" * 2048)
    monkeypatch.setitem(w.DISK_CAP_GB, "frame-screen-BC", 1e-9)
    with pytest.raises(Refused, match="exceeds its declared"):
        jobs._cap_out("frame-screen-BC", d)


def test_stage2_final_verifies_the_rules_and_code_pins(tmp_path, capsys):
    env = JobEnv(tmp_path / "e")
    good = json.loads(env.freeze.read_text())
    env.freeze.write_text(json.dumps({**good, "code_sha256": "0" * 64}))
    code, out = _run(env.argv("stage2-final"), capsys)
    assert code == 2 and "does not cover" in out["refused"]
    env.freeze.write_text(json.dumps(good))
    code, out = _run(env.argv("stage2-final"), capsys)
    assert code == 75 and "pending" in out["tempfail"]  # pins verified; Stage 1 not there yet


# ---- worn-manifest, --worn-sha256, restore roots ----------------------------------------------------------------------------------------------------


def _worn_args(worn):
    return ["--fills-dir", str(worn / "creative_batch13" / "t_screen"), "--snapshot-dir", str(worn / "snapshots"), "--trades-dir", str(worn / "live_trades"), "--sweep-dir", str(worn / "book_sweeps")]


def test_worn_manifest_keys_are_archive_relative_and_roots_do_not_change_them(worn, tmp_path, capsys):
    code, out = _run(["worn-manifest", *_worn_args(worn)], capsys)
    m = out["worn_sha256"]
    assert code == 0 and out["n_files"] == len(m) and "creative_batch13/t_screen/fills.csv.gz" in m and "live_trades/trades-20261012.jsonl" in m
    assert "snapshots/20261012T003103Z_2df48d64/rows_ext.csv.gz" in m and any(k.startswith("book_sweeps/20261015T") for k in m)
    rest = tmp_path / "restore"
    shutil.copytree(worn / "snapshots", rest / "snapshots")
    shutil.copytree(worn / "live_trades", rest / "live_trades")
    code, out2 = _run(["worn-manifest", "--fills-dir", str(worn / "creative_batch13" / "t_screen"), "--sweep-dir", str(worn / "book_sweeps"), "--snapshot-root", str(rest / "snapshots"),
                       "--live-trades-root", str(rest / "live_trades")], capsys)
    assert code == 0 and out2["worn_sha256"] == m  # a byte-identical restore tree hashes to the same archive-relative map
    code, out3 = _run(["worn-manifest", *_worn_args(worn), "--snapshot-root", str(rest)], capsys)
    assert code == 2 and "named 'snapshots'" in out3["refused"]
    (rest / "snapshots" / "20261012T003103Z_2df48d64" / "rows_ext.csv.gz").unlink()  # retention removed it: a missing worn file is a refusal naming the restore
    code, out4 = _run(["worn-manifest", "--fills-dir", str(worn / "creative_batch13" / "t_screen"), "--sweep-dir", str(worn / "book_sweeps"), "--snapshot-root", str(rest / "snapshots"),
                       "--live-trades-root", str(rest / "live_trades")], capsys)
    assert code == 2 and "byte for byte" in out4["refused"]


def test_smoke_worn_sha256_pin_applies_to_whatever_root_is_used(worn, tmp_path, capsys):
    code, out = _run(["worn-manifest", *_worn_args(worn)], capsys)
    pins = out["worn_sha256"]
    pf = tmp_path / "pins.json"
    pf.write_text(json.dumps(pins))
    rest = tmp_path / "restore"
    shutil.copytree(worn / "snapshots", rest / "snapshots")
    shutil.copytree(worn / "live_trades", rest / "live_trades")
    env = JobEnv(tmp_path / "e", with_smoke=False)
    roots = ["--fills-dir", str(worn / "creative_batch13" / "t_screen"), "--sweep-dir", str(worn / "book_sweeps"), "--snapshot-root", str(rest / "snapshots"), "--live-trades-root", str(rest / "live_trades")]
    bad = dict(pins)
    bad["live_trades/trades-20261013.jsonl"] = "0" * 64
    pf2 = tmp_path / "bad.json"
    pf2.write_text(json.dumps(bad))
    code, out = _run(env.argv("smoke", extra=(*roots, "--worn-sha256", str(pf2))), capsys)
    assert code == 2 and "differ from the pins" in out["refused"] and not (env.root / "smoke.json").exists()
    short = {k: v for k, v in pins.items() if not k.startswith("book_sweeps/")}
    pf3 = tmp_path / "short.json"
    pf3.write_text(json.dumps(short))
    code, out = _run(env.argv("smoke", extra=(*roots, "--worn-sha256", str(pf3))), capsys)
    assert code == 2 and "unpinned" in out["refused"]
    code, out = _run(env.argv("smoke", extra=(*roots, "--worn-sha256", str(pf))), capsys)
    assert code == 0  # pins hold; the synthetic counts differ from the real probes, so the smoke FAILS (counted), it is not refused
    res = json.loads((env.root / "smoke.json").read_text())
    assert res["code_sha256"] == win.code_sha256() and res["worn_pins"]["n_files"] == len(pins) and res["pass"] is False
    assert sm.worn_manifest(worn / "creative_batch13" / "t_screen", rest / "live_trades", rest / "snapshots", worn / "book_sweeps") == pins
