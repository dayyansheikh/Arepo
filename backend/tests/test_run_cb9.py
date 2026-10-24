# ruff: noqa: E501
"""CB9 runner tests (offline; no network)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import battery2, provenance
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_pyth as py
from astrolabe.research_lab import cb9_sign as sg
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb9  # noqa: E402

JOBS = ("smoke", "sign-audit", "exclusion-keys", "pyth-frame", "pyth-books", "census", "screen", "stage1-label", "sign-fetch", "pyth-live", "rep", "halfday-poll",
        "rules", "key-fingerprint")


def _run(argv, capsys) -> tuple[int, dict]:
    code = run_cb9.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


def test_parser_has_every_job_and_kd_subcommands():
    sub = next(a for a in run_cb9.build_parser()._actions if a.dest == "cmd")
    for j in JOBS:
        assert j in sub.choices
    if run_cb9._kd_module() is not None:
        for j in ("kd-frame", "kd-books", "kd-seal", "screen-kd", "rep-kd"):
            assert j in sub.choices


def test_kd_dispatch():
    if run_cb9._kd_module() is None:
        pytest.skip("cb9_kd not present")
    assert run_cb9.dispatch_argv(["screen", "--family", "KD", "--root", "x"]) == ["screen-kd", "--root", "x"]
    assert run_cb9.dispatch_argv(["rep", "--family=KD"]) == ["rep-kd"]
    assert run_cb9.dispatch_argv(["screen", "--family", "P"]) == ["screen", "--family", "P"]


def test_defaults():
    a = run_cb9.build_parser().parse_args(["pyth-frame"])
    assert a.data_dumps_cap_gb == 40.0 == c9.DATA_DUMPS_CAP_GB
    assert c9.BATCH_HOLM_K1 == 5 and c9.STAGE1_HOLM_FAMILY == ("P1", "P2", "K1", "D1", "S1")


def test_sign_audit_refuses_before_t_seal_and_bad_strata(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(run_cb9.time, "time", lambda: c9.T_SEAL_EPOCH - 60)
    code, out = _run(["sign-audit", "--strata", "a,c", "--root", str(tmp_path)], capsys)
    assert code == 2 and "T_seal" in out["refused"]
    code, out = _run(["sign-audit", "--strata", "a,b", "--root", str(tmp_path)], capsys)
    assert code == 2


def test_declared_arguments_refused(capsys, tmp_path):
    code, out = _run(["sign-audit", "--strata", "b", "--disk-cap-gb", "0.02", "--root", str(tmp_path)], capsys)
    assert code == 2 and "disk_cap_gb" in out["refused"]
    code, out = _run(["pyth-books", "--rps", "3", "--root", str(tmp_path)], capsys)
    assert code == 2 and "rps" in out["refused"]
    code, out = _run(["pyth-books", "--ingress-cap-gb", "50", "--root", str(tmp_path)], capsys)
    assert code == 2 and "ingress" in out["refused"]


def test_refused_roots(capsys, tmp_path):
    code, out = _run(["census", "--root", str(tmp_path / "creative_batch8")], capsys)
    assert code == 2
    with pytest.raises(c9.Refused):
        c9.refuse_read(tmp_path / "h9_flow" / "trades" / "x.csv.gz")
    assert c9.refuse_read(tmp_path / "creative_batch8" / "exclusion_keys.csv.gz")


def test_analysis_jobs_refuse_before_freeze(capsys, tmp_path):
    (tmp_path / "census.json").write_text("{}")
    for fam in ("S0", "P", "S1"):
        code, out = _run(["screen", "--family", fam, "--root", str(tmp_path), "--freeze-spec", str(tmp_path / "missing.json")], capsys)
        assert code == 2 and "freeze" in out["refused"]
    code, out = _run(["rep", "--family", "P", "--root", str(tmp_path), "--freeze-spec", str(tmp_path / "missing.json")], capsys)
    assert code == 2


def test_triggers_refuse(capsys, tmp_path):
    code, out = _run(["sign-fetch", "--root", str(tmp_path)], capsys)
    assert code == 2 and "results_S0" in out["refused"]
    (tmp_path / "results_S0.json").write_text(json.dumps({"s1_triggered_eras": []}))
    code, out = _run(["sign-fetch", "--root", str(tmp_path)], capsys)
    assert code == 2 and "material noise" in out["refused"]
    code, out = _run(["pyth-live", "--root", str(tmp_path)], capsys)
    assert code == 2 and "did not advance" in out["refused"]


def _pyth_rules(tmp_path) -> Path:
    return c9.write_rules("pyth", tmp_path / "cb9_rules.json")


def _keys(tmp_path) -> Path:
    d = tmp_path / "keys" / "creative_batch9"
    d.mkdir(parents=True)
    p = d / "exclusion_keys.csv.gz"
    p.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [["1", "1", "9", "", ""]]))
    from astrolabe.research_lab import h5_seal

    (d / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(p), "disjointness": "verified"}))
    return p


def test_headroom_exit_75(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(run_cb9.time, "time", lambda: c9.T_SEAL_EPOCH + 60)
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"smoke_version": sg.SMOKE_VERSION, "criteria": {"yahoo_clock": True, "gamma_paging": True}}))
    dd = tmp_path / "dd"
    dd.mkdir()
    (dd / "big.bin").write_bytes(b"x" * 4096)
    code, out = _run(["pyth-frame", "--root", str(tmp_path / "cb9"), "--rules", str(_pyth_rules(tmp_path)), "--allow-uncommitted-rules", "--standalone",
                      "--smoke", str(smoke), "--exclusion-keys", str(_keys(tmp_path)), "--data-dumps", str(dd), "--data-dumps-cap-gb", "0.000001"], capsys)
    assert code == 75 and "headroom" in out["tempfail"]


def test_smoke_write_once(capsys, tmp_path):
    out = tmp_path / "smoke.json"
    out.write_text("{}")
    code, res = _run(["smoke", "--out", str(out)], capsys)
    assert code == 2 and "write-once" in res["refused"]


def test_key_fingerprint_strict(capsys, tmp_path):
    p = tmp_path / "nokey"
    code, _ = _run(["key-fingerprint", "--wallet-key-path", str(p)], capsys)
    assert code == 2 and not p.exists()
    p.write_bytes(b"secret-key-bytes")
    os.chmod(p, 0o600)
    code, out = _run(["key-fingerprint", "--wallet-key-path", str(p)], capsys)
    assert code == 0 and out["wallet_key_fingerprint"] == cm.key_fingerprint(b"secret-key-bytes")


def test_rules_kd_written_with_fingerprint(capsys, tmp_path):
    if run_cb9._kd_module() is None:
        pytest.skip("cb9_kd not present")
    code, out = _run(["rules", "--which", "kd", "--path", str(tmp_path / "kd.json"), "--key-fingerprint", "0123456789abcdef"], capsys)
    assert code == 0 and out["wallet_key_fingerprint"] == "0123456789abcdef"
    assert c9.verify_rules("kd", tmp_path / "kd.json", require_committed=False)[1] == "0123456789abcdef"


# ---- census: counts only, no target, no guarded file ---------------------------------------------------------------------------


def _write(p: Path, header, rows) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(hb._gz_csv_bytes(header, rows))


def test_census_receives_no_target(monkeypatch, capsys, tmp_path):
    root = tmp_path / "creative_batch9"
    rows = [{c: "" for c in sg.PRINT_COLUMNS} | {"stratum": "a", "market_id": f"m{i}", "match_status": "matched", "t1_available": "1", "t2_available": "1",
                                                 "t1_side": "BUY", "api_side": "SELL", "receipt_status": "ok", "endpoint": sg.ENDPOINTS[0], "era": "v2",
                                                 "fill_type": "normal", "sports": "0", "api_idx": "0", "t1_idx": "0"} for i in range(5)]
    _write(root / "sign" / "s0a" / "prints_classes.csv.gz", sg.PRINT_COLUMNS, [[r[c] for c in sg.PRINT_COLUMNS] for r in rows])
    seen = []
    orig = sg.census_s

    def spy(rows_by):
        seen.append(rows_by)
        return orig(rows_by)

    monkeypatch.setattr(sg, "census_s", spy)
    monkeypatch.setattr(py, "open_guarded", lambda *a, **k: (_ for _ in ()).throw(AssertionError("census opened a guarded file")))
    _p_fixture(root)
    monkeypatch.setattr(run_cb9, "_kd_module", lambda: None)
    code, out = _run(["census", "--root", str(root), "--trials-path", str(tmp_path / "t.jsonl")], capsys)
    assert code == 0, out
    for s_rows in seen[0].values():
        for r in s_rows:
            assert set(r) <= set(sg.CENSUS_COLUMNS_S) and not set(r) & set(sg.CENSUS_FORBIDDEN_S)
    doc = json.loads((root / "census.json").read_text())
    txt = json.dumps(doc)
    for forbidden in ("q_hat", "mean_cents", "\"net\"", "pnl", "outcome_prices"):
        assert forbidden not in txt
    assert doc["S"]["a"]["n_matched"] == 5 and doc["kd"] == {"status": "cb9_kd unavailable"}
    code, out = _run(["census", "--root", str(root)], capsys)
    assert code == 2  # written once


def _p_fixture(root: Path) -> None:
    fdir, bdir = root / "pyth_frame", root / "pyth"
    day = "2026-05-15"
    _write(fdir / "frame.csv.gz", py.FRAME_COLUMNS + ["ticker_status"], [["1", "c", "a", "b", "0", "NVDA", day, "5", "5", "", "", "", "q", "x", "s", "ok"]])
    _write(fdir / "bars_pre.csv.gz", py.BAR_COLUMNS, [["NVDA", day, py.et_epoch(day, 9, 30) + 3600 * j, py.et_epoch(day, 9, 30) + 3600 * (j + 1), 100, 100] for j in range(6)])
    _write(fdir / "strikes.csv.gz", py.STRIKE_COLUMNS, [["NVDA", day, 100.0, "2026-05-14"]])
    _write(fdir / "outcomes_guarded.csv.gz", py.OUTCOME_COLUMNS, [["1", day, '["Up","Down"]', '["1","0"]']])
    (fdir / "manifest.json").write_text(json.dumps({"status": "pyth_frame_complete"}))
    _write(bdir / "states.csv.gz", py.STATE_COLUMNS, [])
    _write(bdir / "prints.csv.gz", py.PRINT_COLUMNS, [])


# ---- batch-Holm, trial lines and battery2 ---------------------------------------------------------------------------------------


def test_batch_holm_k1_fixed(capsys, tmp_path):
    lab = c9.batch_holm_label({"P1": 0.001})
    assert lab["k"] == 5 and set(lab["tests"]) == {"P1", "P2", "K1", "D1", "S1"} and lab["tests"]["P1"]["reject"]
    assert c9.batch_holm_label({"P1": 0.003})["tests"]["P1"]["reject"] is False  # 0.003 > 0.01/5
    with pytest.raises(c9.Refused):
        c9.batch_holm_label({"S0": 0.001})
    (tmp_path / "results_P.json").write_text(json.dumps({"P1": {"testable": True, "p": 0.001}, "P2": {"testable": False, "p": 1.0}}))
    code, out = _run(["stage1-label", "--root", str(tmp_path)], capsys)
    assert code == 0 and out["batch_holm"]["k"] == 5 and "S1" in out["batch_holm"]["not_run_as_p1"]


def test_trial_lines_counted_through_battery2(tmp_path):
    tp = tmp_path / "trials.jsonl"
    c9.log_test("S", "S0", {"p": None, "testable": True, "verdict": {"a": "near-truth"}}, trials_path=tp)
    c9.log_test("P", "P1", {"p": 0.2, "testable": True}, trials_path=tp, placebo={"advance_rate": 0.01, "n_draws": 200})
    c9.log_test("P", "P2", {"p": 0.004, "testable": False}, trials_path=tp)
    c9.log_test("P", "P1-rep", {"p": 0.5}, replication=True, trials_path=tp, data_role=c9.DATA_ROLE_PROSP)
    c9.log_descriptive("census", {"x": 1}, trials_path=tp)
    r = battery2.cumulative_count(tp)
    assert r["total"] == 4 and r["by_kind"]["cb9_test"] == 0 and r["by_kind"]["cb9_descriptive"] == 0 and r["by_kind"]["ml_explain"] == 4
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert next(x for x in lines if x.get("hypothesis") == "P2" and x["kind"] == "cb9_test")["p"] == 1.0  # not testable -> p = 1
    with pytest.raises(c9.Refused):
        c9.log_test("X", "X1", {}, trials_path=tp)


def test_real_trials_log_still_counts():
    if not provenance.TRIALS_PATH.exists():
        pytest.skip("no trials log")
    assert battery2.cumulative_count()["total"] >= 1131
    for k in ("cb9_test", "cb9_replication", "cb9_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE


# ---- freeze-check fixes (M5, M11) ---------------------------------------------------------------------------------------------------


def test_census_carries_stall_labels(monkeypatch, capsys, tmp_path):
    root = tmp_path / "creative_batch9"
    c9.write_stall(root / "sign" / "s0c", c9.STALL_NOT_RUN_SOURCE, "smoke receipts_v1 failed")
    c9.write_stall(root / "pyth_frame", c9.STALL_NOT_RUN_SOURCE, "smoke yahoo_clock failed")
    monkeypatch.setattr(run_cb9, "_kd_module", lambda: None)
    code, out = _run(["census", "--root", str(root), "--trials-path", str(tmp_path / "t.jsonl")], capsys)
    assert code == 0
    doc = json.loads((root / "census.json").read_text())
    assert doc["S"]["c"]["label"] == "not testable (source)" and doc["S"]["c"]["stall"] == c9.STALL_NOT_RUN_SOURCE
    assert doc["P"]["label_P1"] == "not testable (source)" and doc["P"]["gate_GP_P1"] is False


def test_screen_p_stall_logs_p1_and_results_write_once(capsys, tmp_path):
    root = tmp_path / "creative_batch9"
    c9.write_stall(root / "pyth_frame", c9.STALL_NOT_RUN_SOURCE, "smoke yahoo_clock failed")
    (root / "census.json").write_text("{}")
    spec = tmp_path / "cb9_v1.json"
    spec.write_text("{}")
    rules = c9.write_rules("pyth", tmp_path / "r.json")
    tp = tmp_path / "t.jsonl"
    argv = ["screen", "--family", "P", "--root", str(root), "--freeze-spec", str(spec), "--allow-uncommitted-rules", "--rules", str(rules), "--trials-path", str(tp)]
    code, out = _run(argv, capsys)
    assert code == 0 and out["P1"]["p"] == 1.0
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert {x["hypothesis"] for x in lines if x["kind"] == "cb9_test"} == {"P1", "P2"} and all(x["p"] == 1.0 for x in lines if x["kind"] == "cb9_test")
    n = len(lines)
    code, out = _run(argv, capsys)
    assert code == 2 and "write-once" in out["refused"] and len(tp.read_text().splitlines()) == n


# ---- focused re-check (2026-10-17) fixes ---------------------------------------------------------------------------------------------------


def _stage1(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "results_P.json").write_text(json.dumps({"P1": {"advance": True}, "P2": {"advance": False}}))
    (root / "results_KD.json").write_text(json.dumps({"K1": {"advance": False}, "D1": {"advance": False}}))


def test_rep_p_waits_for_live_complete_end_plus_2d_and_final_outcomes(monkeypatch, capsys, tmp_path):
    from datetime import UTC, datetime

    root = tmp_path / "creative_batch9"
    _stage1(root)
    monkeypatch.setattr(run_cb9, "_commit_epoch", lambda p: datetime(2026, 10, 25, tzinfo=UTC).timestamp())
    sessions = py.stage2_sessions(py.t9_p2_start(datetime(2026, 10, 25, tzinfo=UTC).timestamp()))
    t_end = py.et_epoch(sessions[-1], 23, 59)
    ldir = root / "pyth_live"
    with pytest.raises(c9.NotNow, match="not complete"):  # 1. no pyth-live completion marker
        run_cb9.rep_p_doc(root, now=t_end + 10 * 86400)
    ldir.mkdir()
    (ldir / run_cb9.LIVE_COMPLETE_FILE).write_text("{}")
    with pytest.raises(c9.NotNow, match=r"T9_P2_end \+ 2 d"):  # 2. too early (even though marked complete)
        run_cb9.rep_p_doc(root, now=t_end + 86400)
    (ldir / sessions[0]).mkdir()
    (ldir / sessions[0] / "state.json").write_text(json.dumps({"steps": {"post": {"t": 1}, "outcomes": {"final": False}}}))
    with pytest.raises(c9.NotNow, match="outcomes not final"):  # 3. a pending session is never scored 'unavailable (source)'
        run_cb9.rep_p_doc(root, now=t_end + 3 * 86400)
    # CLI: exit 75, nothing written, no trial line
    spec = tmp_path / "cb9_v1.json"
    spec.write_text("{}")
    rules = c9.write_rules("pyth", tmp_path / "r.json")
    tp = tmp_path / "t.jsonl"
    code, out = _run(["rep", "--family", "P", "--root", str(root), "--freeze-spec", str(spec), "--allow-uncommitted-rules", "--rules", str(rules), "--trials-path", str(tp)], capsys)
    assert code == 75 and "tempfail" in out and not (root / "results_P_rep.json").exists() and not tp.exists()


def test_pyth_live_before_window_exits_75_and_prints_completion_status(monkeypatch, capsys, tmp_path):
    from datetime import UTC, datetime

    root = tmp_path / "creative_batch9"
    _stage1(root)
    spec = tmp_path / "cb9_v1.json"
    spec.write_text("{}")
    rules = c9.write_rules("pyth", tmp_path / "r.json")
    monkeypatch.setattr(run_cb9, "_commit_epoch", lambda p: datetime(2099, 1, 1, tzinfo=UTC).timestamp())  # window far in the future
    monkeypatch.setattr(run_cb9.time, "time", lambda: datetime(2026, 10, 25, tzinfo=UTC).timestamp())
    argv = ["pyth-live", "--root", str(root), "--freeze-spec", str(spec), "--allow-uncommitted-rules", "--rules", str(rules), "--standalone"]
    code, out = _run(argv, capsys)
    assert code == 0 and out["status"] == "idle_heartbeat"  # the first idle run is the heartbeat (resets the queue's tempfail count); the rest exit 75
    code, out = _run(argv, capsys)
    assert code == 75 and "Stage-2 window starts" in out["tempfail"]  # nothing fetched, nothing written but the heartbeat
    assert run_cb9.LIVE_COMPLETE == "pyth_live_complete" == "pyth_live_complete" and py.pyth_live_tick(
        root / "pyth_live", now=py.et_epoch("2027-03-01", 12, 0), start_day="2026-11-16", frame_markets=lambda d: [], yahoo_get=None, book_get=None, prints_get=None)["status"] == run_cb9.LIVE_COMPLETE


def test_wait_until_due_sleeps_to_next_step_only_within_lookahead(tmp_path):
    day = "2026-11-17"
    ck = py.checkpoints(day)
    slept = []
    t = ck[0][2] - 600
    assert run_cb9.wait_until_due(tmp_path, [day], t, slept.append) == ck[0][2] and slept == [pytest.approx(602.0)]
    assert run_cb9.wait_until_due(tmp_path, [day], ck[0][2] - 4 * 3600, slept.append) is None  # nothing due within 35 min
    (tmp_path / day).mkdir()
    (tmp_path / day / "state.json").write_text(json.dumps({"steps": {"ckpt0": {"t": 1}}}))  # done steps are not waited for
    assert run_cb9.wait_until_due(tmp_path, [day], t, slept.append) is None


def test_halfday_session_polls_each_minute_then_yahoo_and_done(tmp_path):
    day = "2026-11-27"
    clock = {"t": py.et_epoch(day, 13, 0)}
    books, yahoo_calls = [], []

    def sleep(s):
        clock["t"] += s

    def book_get(tok):
        books.append(clock["t"])
        return {"bids": [{"price": "0.5", "size": "10"}], "asks": [{"price": "0.52", "size": "10"}]}, clock["t"]

    def yahoo_get(sym, p1, p2):
        yahoo_calls.append((sym, p1, p2))
        if sym == "BAD":
            raise RuntimeError("x")
        return {"chart": {}}

    mk = [{"market_id": "1", "ticker": "NVDA", "token_up": "u", "token_down": "d"}, {"market_id": "2", "ticker": "BAD", "token_up": "u2", "token_down": "d2"}]
    res = run_cb9.halfday_session(tmp_path, day, now_fn=lambda: clock["t"], sleep=sleep, frame_markets=lambda d: mk, book_get=book_get, yahoo_get=yahoo_get)
    assert res["status"] == run_cb9.HALFDAY_DAY_DONE and 170 <= res["minutes_collected"] <= 176
    assert res["yahoo_1m"]["NVDA"] == "ok" and res["yahoo_1m"]["BAD"].startswith("failed") and (tmp_path / day / "yahoo_1m_NVDA.json").exists()
    assert run_cb9.halfday_next(tmp_path, [day, "2026-12-24"]) == "2026-12-24"
    assert run_cb9.halfday_next(tmp_path, [day]) is None


def test_halfday_missed_window_is_recorded_not_backfilled(tmp_path):
    day = "2026-11-27"
    res = run_cb9.halfday_session(tmp_path, day, now_fn=lambda: py.et_epoch(day, 20, 0), sleep=lambda s: None, frame_markets=lambda d: [], book_get=None, yahoo_get=None)
    assert res["result"] == "missed_window" and run_cb9.halfday_next(tmp_path, [day]) is None


def test_halfday_before_window_idles(monkeypatch, capsys, tmp_path):
    from datetime import UTC, datetime

    monkeypatch.setattr(run_cb9.time, "time", lambda: datetime(2026, 10, 25, tzinfo=UTC).timestamp())
    rules = c9.write_rules("pyth", tmp_path / "r.json")
    argv = ["halfday-poll", "--root", str(tmp_path / "cb9"), "--rules", str(rules), "--allow-uncommitted-rules", "--standalone"]
    assert _run(argv, capsys)[1]["status"] == "idle_heartbeat"
    code, out = _run(argv, capsys)
    assert code == 75 and "half session 2026-11-27" in out["tempfail"]
