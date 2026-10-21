# ruff: noqa: E501
"""LT6 (LIVE_TESTS_6.md) code unit 4-5: the reader (write-once files, the .late / .noprev / .nosweep / .noprevsweep / .e022boundary markers,
look-back lines, the running-capture guard, the disk cap, the pinned-code check, the run lock, exit 75), ``ops-stats`` (no price column)
and the analysis entry point (refusals, pin checks, the Unavailable family, the counting line). Synthetic data only."""

from __future__ import annotations

import copy
import fcntl
import importlib.util
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests6 as lt
from astrolabe.research_lab import live_tests6_analysis as la
from tests.unit.test_research_lab_live_tests6_census import (
    G0,
    _iso,
    write_capture,
    write_sample,
    write_sweep,
)

REG, END = "2026-10-02T00:00:00Z", "2026-10-03T00:00:00Z"  # slots 12 .. 23 are window origins; slots 0 .. 11 are look-back
NOW_DRY = lt.epoch("2026-10-05T00:00:00Z")


def _slot_t(k: int) -> float:
    return G0.timestamp() + 7200 * k


def _spec(**over) -> dict:
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["_pinned"] = False
    spec.update(over)
    return spec


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lt6reader")
    snap, sw, smp = tmp / "snap", tmp / "sweeps", tmp / "samples"
    for p in (snap, sw, smp):
        p.mkdir()
    ids = {k: write_capture(snap, k) for k in range(48)}
    sweep_names = {k: write_sweep(sw, ids[k], k) for k in range(11, 36)}
    sids = {k: write_sample(smp, ids[k], k) for k in range(13, 36)}
    return {"tmp": tmp, "snap": snap, "sweeps": sw, "samples": smp, "ids": ids, "sweep_names": sweep_names, "sids": sids}


def _run(w, root, spec=None, now=NOW_DRY, **kw):
    kw.setdefault("allow_late", True)
    kw.setdefault("max_items", 10_000)
    return lt.run_once(snapshot_root=kw.pop("snapshot_root", w["snap"]), sample_root=w["samples"], sweep_root=kw.pop("sweep_root", w["sweeps"]), root=root,
                       spec=spec or _spec(), registered_utc=REG, end_utc=END, now=now, **kw)


def _frozen(root, kind, cid):
    return pd.read_csv(Path(root) / kind / "frozen" / f"{cid}.csv.gz", float_precision="round_trip")


@pytest.fixture(scope="module")
def ran(world, tmp_path_factory):
    root = tmp_path_factory.mktemp("lt6out")
    st = _run(world, root)
    return {"root": root, "stats": st}


# --- the pass ---------------------------------------------------------------------------------------------------------------------------


def test_pass_writes_series_sweeps_freezes_and_outcomes_write_once(world, ran):
    st, root, ids = ran["stats"], ran["root"], world["ids"]
    assert st["status"] == "wrote" and st["series"] > 0 and st["sweeps"] > 0 and st["outcomes"] > 0 and st["lookback_labels"] > 0
    for sub in ("series", "status", "members"):
        assert (root / sub / f"{ids[0]}.csv.gz").exists() and (root / sub / f"{ids[23]}.csv.gz").exists()  # look-back (slot 0) and window captures
    assert (root / "series" / f"{ids[36]}.csv.gz").exists() and not (root / "series" / f"{ids[38]}.csv.gz").exists()  # up to END + 13 slots
    assert (root / "sweeps" / f"{ids[20]}.csv.gz").exists()
    for kind in ("vote", "deadline", "birth"):
        assert (root / kind / "frozen" / f"{ids[14]}.csv.gz").exists() and not (root / kind / "frozen" / f"{ids[11]}.csv.gz").exists() and not (root / kind / "frozen" / f"{ids[24]}.csv.gz").exists()
    assert (root / "clips" / "frozen" / f"{world['sids'][14]}.csv.gz").exists()
    v = _frozen(root, "vote", ids[20])
    assert len(v) > 0 and set(v["role"]) == {lt.ROLE_UNREG} and (v["capture_t"] == _slot_t(20)).all() and {"v", "v_prev", "lt", "h0", "k_slot", "capture_id"} <= set(v.columns)
    assert not ({"end_raw", "fee_cat", "osz"} & set(v.columns)) and (v["spec_sha"].astype(str) == _spec()["_sha256"][:16]).all() and (v["code_sha"].astype(str) == lt.reader_sha()).all()
    for tag in ("h1", "h3", "s1", "s3"):
        assert (root / "vote" / "outcomes" / f"{ids[20]}.{tag}.csv.gz").exists()
    for tag in ("h1", "h3", "h12"):
        assert (root / "deadline" / "outcomes" / f"{ids[14]}.{tag}.csv.gz").exists() and (root / "birth" / "outcomes" / f"{ids[14]}.{tag}.csv.gz").exists()
    o = pd.read_csv(root / "deadline" / "outcomes" / f"{ids[14]}.h12.csv.gz")
    assert o["status"].eq("two_sided").any() and o["cap_start"].dropna().iloc[0] == _slot_t(26)
    c = _frozen(root, "clips", world["sids"][15])
    assert len(c) > 0 and {"clip_share", "class_k", "g_path", "sample_id"} <= set(c.columns)
    assert (root / "deadline" / "lookback" / f"{ids[5]}.csv.gz").exists() and (root / "birth" / "lookback" / f"{ids[5]}.csv.gz").exists()
    assert not (root / "deadline" / "frozen" / f"{ids[5]}.csv.gz").exists()  # look-back lines are never units
    log = [json.loads(x) for x in (root / "passes.jsonl").read_text().splitlines()]
    assert any(r["kind"] == "lookback_series" for r in log) and any(r["kind"] == "vote_frozen" for r in log) and log[-1]["kind"] == "run"


def test_second_pass_is_idempotent_and_exit_75(world, ran):
    st = _run(world, ran["root"])
    assert st["written"] == 0 and st["status"] == "nothing_new"
    mod = _runner()
    rc = mod.main(["run", "--root", str(ran["root"]), "--snapshot-root", str(world["snap"]), "--sample-root", str(world["samples"]), "--sweep-root", str(world["sweeps"]),
                   "--dry-run-start", REG, "--dry-run-end", END])
    assert rc == lt.TEMPFAIL


def test_frozen_lines_are_byte_stable_under_later_data(world, ran, tmp_path):
    """Causality: wild prices in captures after k leave the frozen vote / deadline / birth lines of k identical (frozen_utc aside)."""
    snap = tmp_path / "snap"
    shutil.copytree(world["snap"], snap)
    for k in range(16, 48):
        d = snap / world["ids"][k]
        rows = pd.read_csv(d / "rows.csv.gz")
        rows["best_bid"], rows["best_ask"], rows["last_trade_price"] = 0.001, 0.999, 0.7
        rows.to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    root = tmp_path / "out"
    _run(world, root, snapshot_root=snap)
    for kind in ("vote", "deadline", "birth"):
        a, b_ = _frozen(ran["root"], kind, world["ids"][14]), _frozen(root, kind, world["ids"][14])
        pd.testing.assert_frame_equal(a.drop(columns=["frozen_utc"]), b_.drop(columns=["frozen_utc"]))


def test_late_rule_marks_units_but_series_and_sweeps_are_still_written(world, tmp_path):
    root = tmp_path / "o"
    now = _slot_t(14) + 3600.0  # slots 12 and 13 can no longer be frozen in time; 14 can
    st = _run(world, root, allow_late=False, now=now)
    ids = world["ids"]
    for kind in ("deadline", "birth"):
        assert (root / kind / "frozen" / f"{ids[12]}.late.csv.gz").exists() and (root / kind / "frozen" / f"{ids[13]}.late.csv.gz").exists()
        assert (root / kind / "frozen" / f"{ids[14]}.csv.gz").exists()
    assert st["refused_late"] >= 6 and (root / "clips" / "frozen" / f"{world['sids'][13]}.late.csv.gz").exists()
    for k in (12, 13):  # the late pass still wrote its series / status / members / sweeps lines (the next pass's k - 1 inputs)
        assert all((root / s / f"{ids[k]}.csv.gz").exists() for s in ("series", "status", "members", "sweeps"))
    assert (root / "vote" / "frozen" / f"{ids[13]}.late.csv.gz").exists() and not (root / "vote" / "frozen" / f"{ids[13]}.csv.gz").exists()
    # a later pass never re-reads a late unit
    st2 = _run(world, root, allow_late=False, now=now + 3 * 7200.0)
    assert not (root / "deadline" / "frozen" / f"{ids[13]}.csv.gz").exists() and st2["status"] in ("wrote", "nothing_new")


def test_a_late_pass_without_a_sweep_is_late_not_nosweep(world, tmp_path):
    empty = tmp_path / "nosweeps"
    empty.mkdir()
    root = tmp_path / "o"
    _run(world, root, allow_late=False, now=_slot_t(14) + 3600.0, sweep_root=empty)
    ids = world["ids"]
    assert (root / "vote" / "frozen" / f"{ids[12]}.late.csv.gz").exists()
    assert not (root / "vote" / "frozen" / f"{ids[12]}.nosweep.csv.gz").exists() and not (root / "vote" / "frozen" / f"{ids[12]}.noprevsweep.csv.gz").exists()


def test_noprev_nosweep_noprevsweep_and_e022_boundary_markers(world, tmp_path):
    ids = world["ids"]
    snap, sw = tmp_path / "snap", tmp_path / "sw"
    shutil.copytree(world["snap"], snap)
    shutil.copytree(world["sweeps"], sw)
    shutil.rmtree(snap / ids[11])  # capture k - 1 of the first origin never existed
    shutil.rmtree(sw / world["sweep_names"][20])  # the pass-20 sweep is missing
    spec = _spec(e022={**_spec()["e022"], "end_utc": lt.iso(_slot_t(16) + 600.0)})  # passes whose k - 1 starts before it are e022_boundary
    root = tmp_path / "o"
    _run(world, root, spec=spec, snapshot_root=snap, sweep_root=sw)
    assert (root / "deadline" / "frozen" / f"{ids[12]}.noprev.csv.gz").exists() and (root / "birth" / "frozen" / f"{ids[12]}.noprev.csv.gz").exists()
    assert (root / "vote" / "frozen" / f"{ids[20]}.nosweep.csv.gz").exists() and (root / "vote" / "frozen" / f"{ids[21]}.noprevsweep.csv.gz").exists()
    assert (root / "vote" / "frozen" / f"{ids[14]}.e022boundary.csv.gz").exists() and (root / "vote" / "frozen" / f"{ids[17]}.e022boundary.csv.gz").exists()  # k - 1 = 16 starts before the end
    assert (root / "vote" / "frozen" / f"{ids[18]}.csv.gz").exists()  # 18's k - 1 (capture and sweep) start after E022's END_UTC: the first origin
    assert not (root / "deadline" / "frozen" / f"{ids[14]}.e022boundary.csv.gz").exists()  # D and B are not bound by E022's end
    ops = lt.ops_stats(root)
    assert ops["vote/frozen"]["nosweep"] == 1 and ops["vote/frozen"]["noprevsweep"] == 1 and ops["vote/frozen"]["e022boundary"] >= 2 and ops["deadline/frozen"]["noprev"] == 1


def test_running_capture_guard(world, tmp_path):
    snap = tmp_path / "snap"
    shutil.copytree(world["snap"], snap)
    ids = world["ids"]
    run_dir = snap / ids[30]
    (run_dir / "manifest.json").write_text(json.dumps({"state": "running", "started_utc": _iso(G0 + timedelta(hours=60))}))
    (run_dir / "rows.csv.gz").unlink()
    now = _slot_t(30) + 1800.0
    assert lt.running_capture_start(snap, 0.0, now) == pytest.approx(_slot_t(30), abs=1)
    assert lt.running_capture_start(snap, 0.0, _slot_t(30) + 5 * 3600.0) == float("inf")  # older than 4 h: a failed capture, ignored
    assert lt.running_capture_start(world["snap"], 0.0, now) == float("inf")  # complete: no guard
    root = tmp_path / "o"
    st = _run(world, root, snapshot_root=snap, now=now)
    assert st["blocked_by_running_capture"] > 0
    assert (root / "series" / f"{ids[29]}.csv.gz").exists() and not (root / "series" / f"{ids[31]}.csv.gz").exists() and not (root / "series" / f"{ids[35]}.csv.gz").exists()


def test_disk_cap_pinned_code_lock_and_dry_run_guards(world, tmp_path, monkeypatch):
    root = tmp_path / "o"
    monkeypatch.setattr(lt, "DISK_CAP_BYTES", 1)
    (root).mkdir()
    (root / "x").write_bytes(b"xx")
    assert _run(world, root)["status"] == "disk_cap"
    monkeypatch.setattr(lt, "DISK_CAP_BYTES", int(1.5e9))
    pinned = _spec()
    pinned["_pinned"], pinned["code_sha256"] = True, {n: "0" * 64 for n in lt.CODE_FILES}
    with pytest.raises(RuntimeError, match="LIVE_TESTS6_CODE_MISMATCH"):
        lt.check_pinned_code(pinned)
    with pytest.raises(RuntimeError, match="LIVE_TESTS6_CODE_MISMATCH"):
        _run(world, tmp_path / "p", spec=pinned, allow_late=False)
    with pytest.raises(ValueError, match="allow_late"):
        _run(world, tmp_path / "p2", spec=pinned, allow_late=True)
    ok = _spec()
    ok["_pinned"], ok["code_sha256"] = True, lt.code_hashes()
    lt.check_pinned_code(ok)  # matching pins: silent
    lt.check_pinned_code(_spec())  # a DRAFT never checks
    with pytest.raises(ValueError, match="null in the DRAFT"):
        lt.run_once(snapshot_root=world["snap"], sample_root=world["samples"], sweep_root=world["sweeps"], root=tmp_path / "q", spec=_spec(), now=NOW_DRY)
    root2 = tmp_path / "l"
    root2.mkdir()
    with open(root2 / "run.lock", "a") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        st = _run(world, root2)
        assert st["status"] == "locked" and st["written"] == 0


def test_kinds_not_in_k_tests_are_switched_off(world, tmp_path):
    root = tmp_path / "o"
    _run(world, root, spec=_spec(k_tests=["K", "D"]))
    assert lt.enabled_kinds(_spec(k_tests=["K", "D"])) == {"vote": False, "clips": True, "deadline": True, "birth": False}
    assert not (root / "vote").exists() and not (root / "birth").exists() and (root / "deadline" / "frozen").exists() and (root / "clips" / "frozen").exists()


def test_backfill_mode_and_lookback_missing_counted(world, tmp_path):
    snap = tmp_path / "snap"
    shutil.copytree(world["snap"], snap)
    for k in (3, 4):
        shutil.rmtree(snap / world["ids"][k])
    root = tmp_path / "o"
    st = _run(world, root, snapshot_root=snap, mode="backfill")
    assert st["mode"] == "backfill" and st["series"] > 0 and st["lookback_labels"] > 0 and st["vote"] == st["clips"] == st["deadline"] == st["birth"] == 0
    assert not (root / "vote").exists() and not (root / "deadline" / "frozen").exists() and not list(root.glob("*/outcomes"))
    ops = lt.ops_stats(root, spec=_spec(), registered_utc=REG)
    miss = ops["lookback_missing"]
    assert miss["n"] == 2 and miss["slots"] == [lt.iso(_slot_t(3)), lt.iso(_slot_t(4))]
    # arrival after the backfill: a later full run keeps the existing look-back files untouched (write-once)
    before = {p: p.stat().st_mtime_ns for p in (root / "series").glob("*.csv.gz")}
    _run(world, root, snapshot_root=snap)
    assert all((root / "series" / p.name).stat().st_mtime_ns == m for p, m in before.items())


def _runner():
    spec_ = importlib.util.spec_from_file_location("run_lt6r", Path(lt.ROOT) / "backend" / "scripts" / "run_live_tests6.py")
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    return mod


def test_runner_run_guards(world, tmp_path):
    mod = _runner()
    live = lt.OUT_ROOT
    assert mod.main(["run", "--root", str(live), "--dry-run-start", REG, "--dry-run-end", END]) == 2  # never a dry run into the live root
    assert mod.main(["run", "--root", str(tmp_path / "o"), "--snapshot-root", str(world["snap"]), "--sample-root", str(world["samples"]), "--sweep-root", str(world["sweeps"]),
                     "--dry-run-start", REG, "--dry-run-end", END, "--max-items", "5"]) == 0
    assert mod.main(["backfill-series", "--root", str(live), "--dry-run-start", REG, "--dry-run-end", END]) == 2


# --- ops-stats ------------------------------------------------------------------------------------------------------------------------


def test_ops_stats_reads_no_price_column(ran, monkeypatch):
    seen = []
    real = pd.read_csv

    def spy(path, *a, **k):
        seen.append((str(path), k.get("usecols"), k.get("nrows")))
        return real(path, *a, **k)

    monkeypatch.setattr(lt.pd, "read_csv", spy)
    out = lt.ops_stats(ran["root"])
    assert out["vote/frozen"]["files"] == 12 and out["outcome_status_counts"] and out["line_counts"]
    assert out["deadline/lookback"]["files"] > 0
    for _, use, nrows in seen:
        assert nrows == 0 or (use is not None and set(use) <= lt.OPS_COLS)
    with pytest.raises(ValueError):
        lt._read_ops(ran["root"] / "vote" / "frozen" / f"{next(iter((ran['root'] / 'vote' / 'frozen').glob('*.csv.gz'))).name}", ["mid_k"])


# --- analysis entry point ---------------------------------------------------------------------------------------------------------------


def _aspec(**over) -> dict:
    spec = _spec()
    spec["registered_utc"], spec["end_utc"], spec["analysis_not_before"] = REG, END, "2026-10-04T12:00:00Z"
    spec["k_tests"] = ["V", "K", "D", "B"]
    spec["gates"]["draws"] = 20
    for t in ("v", "k", "d", "b"):
        spec[t]["exclude_family"], spec[t]["perm_stratum"] = "", "day"
    spec["v"].update(c_v=0.0, s_v=0.3, terciles=[-0.5, 0.5], tercile_gap=2.2)
    spec["b"]["fake_birth_terciles"] = [0.01, 0.02]
    spec["labels"]["partially_seen_d"] = False
    spec["e022"]["dropped"] = True
    spec.update(over)
    return spec


def test_analyze_refusals_and_pin_checks(ran):
    root = ran["root"]
    with pytest.raises(RuntimeError, match="DRAFT"):
        la.analyze(root, spec=_spec())
    with pytest.raises(RuntimeError, match="before"):
        la.analyze(root, spec=_aspec(), now=lt.epoch("2026-10-04T11:59:59Z"))
    with pytest.raises(RuntimeError, match="not pinned"):
        la.analyze(root, spec=_aspec(), now=lt.epoch("2026-10-04T12:00:00Z"))
    pinned = _aspec()
    pinned["_pinned"], pinned["code_sha256"] = True, {n: "1" * 64 for n in lt.CODE_FILES}
    with pytest.raises(RuntimeError, match="does not match the registered pins"):
        la.analyze(root, spec=pinned, now=lt.epoch("2026-10-04T12:00:00Z"))
    pinned["code_sha256"] = lt.code_hashes()
    pinned["k_tests"] = None
    with pytest.raises(RuntimeError, match="unfilled"):
        la.analyze(root, spec=pinned, now=lt.epoch("2026-10-04T12:00:00Z"))
    with pytest.raises(RuntimeError, match="not pinned"):
        la.analyze(root, spec=_aspec(), force=True)


def test_analyze_no_data_is_a_well_formed_unavailable_family(tmp_path):
    res = la.analyze(tmp_path, spec=_aspec(), force=True, require_pinned=False)
    assert res["holm"]["m"] == 4 and res["holm"]["p_raw"] == {"V": 1.0, "K": 1.0, "D": 1.0, "B": 1.0}
    for t in ("V", "K", "D", "B"):
        assert res["tests"][t]["verdict"]["verdict"].startswith("Unavailable") and res["tests"][t]["available"] is False
    assert res["trial"]["n_tests"] == 4 and res["window"] == [REG, END] and res["code_check"]["status"]
    sub = la.analyze(tmp_path, spec=_aspec(k_tests=["K", "B"]), force=True, require_pinned=False)
    assert sub["holm"]["tests"] == ["K", "B"] and sub["trial"]["n_tests"] == 2
    line = la.trial_line(sub)
    assert line["kind"] == "live_tests6" and line["n_tests"] == 2 and line["evidence_role"] == lt.ROLE_CONF and line["experiments"] == ["K", "B"]


def test_loaders_filter_by_role_spec_sha_and_code_sha_and_count_markers(ran, world):
    root = ran["root"]
    start, end = lt.epoch(REG), lt.epoch(END)
    df, acc = la.load_kind(root, "deadline", start, end, (lt.ROLE_UNREG,), _spec(), la.TAGS["D"])
    assert acc["files"] == 12 and acc["dropped_role"] == 0 and len(df) > 0 and "status_h12" in df
    df0, acc0 = la.load_kind(root, "deadline", start, end, (lt.ROLE_CONF,), _spec(), la.TAGS["D"])
    assert df0.empty and acc0["dropped_role"] == len(df)
    pinned = _spec()
    pinned["_pinned"], pinned["code_sha256"] = True, lt.code_hashes()
    _, acc1 = la.load_kind(root, "deadline", start, end, (lt.ROLE_UNREG,), pinned, la.TAGS["D"])
    assert acc1["dropped_spec_sha"] == 0 and acc1["dropped_code_sha"] == 0  # lines of this spec and this code are kept
    other = dict(pinned, _sha256="f" * 64)
    _, acc2 = la.load_kind(root, "deadline", start, end, (lt.ROLE_UNREG,), other, la.TAGS["D"])
    assert acc2["dropped_spec_sha"] > 0  # lines of another spec are dropped and counted
    other2 = dict(pinned, code_sha256={**lt.code_hashes(), "live_tests6.py": "e" * 64})
    _, acc3 = la.load_kind(root, "deadline", start, end, (lt.ROLE_UNREG,), other2, la.TAGS["D"])
    assert acc3["dropped_code_sha"] > 0 and acc3["dropped_spec_sha"] == 0
    # a pinned reader-sha: the lines were written by the code on disk, so only the spec hash differs
    s = _spec()
    s["_pinned"], s["code_sha256"] = True, lt.code_hashes()
    assert lt.pinned_reader_sha(s) == lt.reader_sha()
    dfw, accw = la.load_kind(root, "deadline", start, end, (lt.ROLE_UNREG,), _spec(), la.TAGS["D"])
    assert accw["late_loss_share"] == 0.0


def test_analyze_on_a_dry_run_store_runs_end_to_end(ran):
    spec = _aspec()
    for t in ("v", "k", "d", "b"):
        for f in spec[t]["floors"]:
            spec[t]["floors"][f] = 1
    res = la.analyze(ran["root"], spec=spec, force=True, require_pinned=False, roles=(lt.ROLE_UNREG,), n_boot=20, mask_late=False)
    assert res["trial"]["n_tests"] == 4 and set(res["tests"]) == {"V", "K", "D", "B"}
    for t, r in res["tests"].items():
        assert r["verdict"]["verdict"]
        assert res["accounts"][t]["files"] > 0 and "late_loss_share" in res["accounts"][t]
    assert any(res["tests"][t].get("available") for t in res["tests"])


def test_analyze_cli_trials_flag_appends_one_counted_line(tmp_path, monkeypatch):
    from astrolabe.research_lab import provenance

    mod = _runner()
    monkeypatch.setattr(la, "analyze", lambda root: {"tests": {"K": {"verdict": "x"}}, "holm": {"tests": ["K"], "m": 1}, "spec_sha": "s", "code_sha256": {}, "window": [REG, END]})
    lines = []
    monkeypatch.setattr(provenance, "append_trial", lambda rec: lines.append(rec))
    assert mod.main(["analyze", "--root", str(tmp_path), "--out", str(tmp_path / "r.json")]) == 0 and lines == []
    assert mod.main(["analyze", "--root", str(tmp_path), "--out", str(tmp_path / "r2.json"), "--trials"]) == 0
    assert len(lines) == 1 and lines[0]["kind"] == "live_tests6" and lines[0]["n_tests"] == 1
    assert mod.main(["analyze", "--root", str(tmp_path), "--out", str(tmp_path / "r2.json")]) == 1  # never overwrites
    assert np.isfinite(1.0) and datetime.now(UTC)


def test_reader_freezes_reported_arms_and_the_analysis_reads_main_only(world, ran):
    root, ids = ran["root"], world["ids"]
    v = _frozen(root, "vote", ids[20])
    assert {"main", "sports"} <= set(v["arm"].astype(str)) and (v.loc[v["arm"] == "sports", "sports"] == 1).all() and (v.loc[v["arm"] == "main", "sports"] == 0).all()
    for kind in ("deadline", "birth"):
        assert (_frozen(root, kind, ids[20])["arm"].astype(str).isin(["main", "sports", "decided", "tail"])).all()
    df, _ = la.load_kind(root, "vote", lt.epoch(REG), lt.epoch(END), (lt.ROLE_UNREG,), None, ("h1", "h3", "s1", "s3"))
    fr, cnt = la.build_frame("V", df, root, _spec(), mask_late=False)
    assert cnt["arm_lines_not_main"] > 0 and (fr["sports"] == 0).all()


def test_analyze_end_to_end_computes_the_readings_for_every_test(ran):
    spec = _aspec()
    for t in ("v", "k", "d", "b"):
        for f in spec[t]["floors"]:
            spec[t]["floors"][f] = 1
    res = la.analyze(ran["root"], spec=spec, force=True, require_pinned=False, roles=(lt.ROLE_UNREG,), n_boot=20, mask_late=False)
    for t in ("V", "K", "D", "B"):
        r = res["tests"][t]
        assert "readings" in r and r["readings"], t
        rd = r["readings"]
        assert {"attrition", "thanksgiving_sensitivity", "economics", "secondaries"} <= set(rd), (t, set(rd))
    assert {"M1", "M2_own_sweep", "M3", "P_vprev"} <= set(res["tests"]["V"]["readings"])
    assert {"M1", "M2", "M3", "P1", "P2"} <= set(res["tests"]["K"]["readings"])
    assert {"M1", "M1_remainder", "M2", "P1"} <= set(res["tests"]["D"]["readings"]) and res["tests"]["D"]["readings"]["P1"]["computed"] is False
    assert {"M1", "M2", "fake_birth_counts"} <= set(res["tests"]["B"]["readings"])
    assert "_pre" not in res["accounts"]["V"]
