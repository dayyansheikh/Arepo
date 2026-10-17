# ruff: noqa: E501
"""CB10 common + runner tests (offline; no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import battery2, provenance
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb10_brk as br
from astrolabe.research_lab import cb10_common as c10
from astrolabe.research_lab import cb10_dlad as dl
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb10  # noqa: E402

JOBS = ("rules", "smoke", "exclusion-keys", "dlad-frame", "deribit-trades", "brk-frame", "brk-prints", "brk-seal", "census", "screen", "stage1-label", "dlad-live", "rep")
PAST_SEAL = c10.T_SEAL_EPOCH + 3600


def _run(argv, capsys) -> tuple[int, dict]:
    code = run_cb10.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


def _write(p: Path, header, rows) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(hb._gz_csv_bytes(header, rows))


# ---- CLI --------------------------------------------------------------------------------------------------------------------------------------


def test_parser_has_every_subcommand_and_parses_each():
    sub = next(a for a in run_cb10.build_parser()._actions if a.dest == "cmd")
    assert set(JOBS) <= set(sub.choices)
    p = run_cb10.build_parser()
    argvs = {"rules": [], "smoke": [], "exclusion-keys": ["--cb9-keys-sha256", "0" * 64], "dlad-frame": [], "deribit-trades": [], "brk-frame": [], "brk-prints": [], "brk-seal": [],
             "census": [], "screen": ["--family", "D"], "stage1-label": [], "dlad-live": ["--origin", "auto"], "rep": ["--family", "B"]}
    for j in JOBS:
        a = p.parse_args([j, *argvs[j]])
        assert callable(a.fn)
    assert p.parse_args(["screen", "--family", "B"]).family == "B"
    with pytest.raises(SystemExit):
        p.parse_args(["screen", "--family", "X"])
    with pytest.raises(SystemExit):
        p.parse_args(["exclusion-keys"])  # the pinned sha256 of CB9 q0182's keys is required


def test_defaults_and_fixed_constants():
    a = run_cb10.build_parser().parse_args(["dlad-frame"])
    assert a.data_dumps_cap_gb == 40.0 == c10.DATA_DUMPS_CAP_GB and a.disk_cap_gb == 0.01 and a.rps == 2.0
    assert c10.BATCH_HOLM_K1 == 3 and c10.STAGE1_HOLM_FAMILY == ("D1", "B1", "B2")
    assert (c10.SEED_BOOT, c10.N_BOOT, c10.PLACEBO_DRAWS, c10.PLACEBO_MAX_ADVANCE, c10.SEED_GDP) == (1010, 2000, 200, 0.015, 10107)
    assert c10.FREE_DISK_MIN_GB == 4.5 and c10.TOTAL_OUTPUT_CAP_GB == 0.12
    assert c10.T_SEAL == "2026-10-22T00:00:00Z" and c10.T10_HIST_END == "2026-10-01T00:00:00Z"


# ---- rules file: determinism, tamper, no overwrite ----------------------------------------------------------------------------------------


def test_rules_file_deterministic_and_verified(tmp_path):
    p1 = c10.write_rules(tmp_path / "a.json")
    p2 = c10.write_rules(tmp_path / "b.json")
    assert p1.read_bytes() == p2.read_bytes()
    doc = json.loads(p1.read_text())
    assert doc["rules_sha256"] and c10.verify_rules(p1, require_committed=False) == doc["rules_sha256"]
    assert c10.write_rules(p1) == p1  # idempotent on identical content
    assert doc["wallet"]["read"] is False and set(doc["declared"]) == {"cb10_dlad", "cb10_brk"}
    for needle in ("1010", "10107", "0.999"):
        assert needle in json.dumps(doc)


def test_rules_tamper_and_overwrite_refused(tmp_path):
    p = c10.write_rules(tmp_path / "r.json")
    doc = json.loads(p.read_text())
    doc["common"] = {**doc["common"], "tamper": 1}
    p.write_text(json.dumps(doc))
    with pytest.raises(c10.Refused, match="hash mismatch"):
        c10.verify_rules(p, require_committed=False)
    with pytest.raises(c10.Refused, match="never rewritten"):
        c10.write_rules(p)
    with pytest.raises(c10.Refused, match="not found"):
        c10.verify_rules(tmp_path / "missing.json", require_committed=False)


def test_rules_hash_changes_with_a_declared_constant(monkeypatch):
    a = c10.rules_file_doc()["rules_sha256"]
    monkeypatch.setattr(dl, "D1_FLOOR", 0.31)
    b = c10.rules_file_doc()["rules_sha256"]
    assert a != b
    monkeypatch.undo()
    monkeypatch.setattr(br, "B1_FLOOR_C", 0.6)
    assert c10.rules_file_doc()["rules_sha256"] not in (a, b)


def test_committed_rules_file_matches_code_if_present():
    p = c10.RULES_FILE
    if not p.exists():
        pytest.skip("rules file not generated yet")
    assert c10.verify_rules(p, require_committed=False) == json.loads(p.read_text())["rules_sha256"]


def test_rules_command(capsys, tmp_path):
    code, out = _run(["rules", "--path", str(tmp_path / "x.json")], capsys)
    assert code == 0 and len(out["rules_sha256"]) == 64 and Path(out["written"]).exists()


# ---- refusals, time gates, disk guard ---------------------------------------------------------------------------------------------------------


def test_refused_roots_runs_and_reads(tmp_path):
    for root in ("creative_batch8", "creative_batch9", "h10_sign", "h4_seal", "h9_flow", "live_trades", "cross_venue"):
        with pytest.raises(c10.Refused):
            c10.refuse_path(tmp_path / root / "x")
    assert c10.refuse_path(tmp_path / "creative_batch10" / "x") and c10.refuse_path(tmp_path / "history" / "h10_dlad")
    with pytest.raises(c10.Refused):
        c10.refuse_read(tmp_path / "h9_flow" / "trades" / "x.csv.gz")
    assert c10.refuse_read(tmp_path / "creative_batch9" / "exclusion_keys.csv.gz")  # ids and keys only
    with pytest.raises(c10.Refused):
        c10.refuse_run_id("h10_sign", "dlad_frame")
    with pytest.raises(c10.Refused):
        c10.refuse_run_id("brk_prints", "dlad_frame")


def test_refused_root_via_cli(capsys, tmp_path):
    code, out = _run(["census", "--root", str(tmp_path / "creative_batch9")], capsys)
    assert code == 2 and "refused" in out["refused"]


def test_net_jobs_refuse_before_t_seal_and_smoke_is_allowed(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(run_cb10.time, "time", lambda: c10.T_SEAL_EPOCH - 60)
    rules = c10.write_rules(tmp_path / "r.json")
    code, out = _run(["exclusion-keys", "--cb9-keys-sha256", "0" * 64, "--root", str(tmp_path / "cb10"), "--rules", str(rules), "--allow-uncommitted-rules"], capsys)
    assert code == 2 and "T_seal" in out["refused"]
    with pytest.raises(c10.Refused, match="T_seal"):
        c10.require_after_t_seal(c10.T_SEAL_EPOCH - 1, "x")
    c10.require_after_t_seal(c10.T_SEAL_EPOCH, "x")
    smoke = tmp_path / "smoke.json"
    smoke.write_text("{}")
    code, out = _run(["smoke", "--out", str(smoke)], capsys)
    assert code == 2 and "write-once" in out["refused"]  # reaches the write-once guard: no T_seal gate on q0200
    with pytest.raises(c10.Refused, match="T_seal"):
        dl.dlad_frame(tmp_path / "h", None, rules_sha="x", smoke_path=smoke, exclusion_keys_path=smoke, now=c10.T_SEAL_EPOCH - 60)


def test_declared_arguments_refused(capsys, tmp_path):
    for argv, key in ((["dlad-frame", "--disk-cap-gb", "0.5"], "disk_cap_gb"), (["brk-prints", "--rps", "3"], "rps"), (["smoke", "--rps", "2"], "rps"),
                      (["deribit-trades", "--disk-cap-gb", "0.01"], "disk_cap_gb"), (["dlad-live", "--origin", "auto", "--rps", "2"], "rps")):
        code, out = _run([*argv, "--root", str(tmp_path / "cb10")], capsys)
        assert code == 2 and key in out["refused"], argv
    code, out = _run(["dlad-live", "--origin", "09:00", "--root", str(tmp_path / "cb10")], capsys)
    assert code == 2 and "auto" in out["refused"]


def test_disk_guard_exit_75_data_dumps_and_free_disk(tmp_path):
    dd = tmp_path / "dd"
    dd.mkdir()
    (dd / "big.bin").write_bytes(b"x" * 4096)
    with pytest.raises(cm.NotNow, match="headroom|data-dumps|cap"):
        c10.require_disk(dd, 0.000001, 1000)
    with pytest.raises(cm.NotNow, match="free"):
        c10.require_disk(dd, 40.0, int(0.06 * 1024**3), free_fn=lambda p: int(4.4e9))
    ok = c10.require_disk(dd, 40.0, int(0.06 * 1024**3), free_fn=lambda p: int(4.7e9))
    assert ok["free_min_gb"] == 4.5 and ok["cap_gb"] == 40.0
    with pytest.raises(cm.NotNow):
        c10.require_disk(dd, 40.0, int(0.06 * 1024**3), free_fn=lambda p: int(4.5e9 + 0.05e9))  # free - cap < 4.5 GB
    assert cm.TEMPFAIL_EXIT == 75 == run_cb10.TEMPFAIL


def test_headroom_exit_75_via_cli(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(run_cb10.time, "time", lambda: PAST_SEAL)
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"smoke_version": dl.SMOKE_VERSION, "criteria": {k: True for k in ("ladder_frame", "live_flags", "data_api_paging", "tx_aggregation", "whitelist")}}))
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    keys = keys_dir / "exclusion_keys.csv.gz"
    _write(keys, ["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [["1", "1", "9", "", ""]])
    from astrolabe.research_lab import h5_seal

    (keys_dir / c10.EXCLUSION_REPORT_NAME).write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified"}))
    dd = tmp_path / "dd"
    dd.mkdir()
    (dd / "big.bin").write_bytes(b"x" * 4096)
    rules = c10.write_rules(tmp_path / "r.json")
    code, out = _run(["dlad-frame", "--history-root", str(tmp_path / "hist"), "--rules", str(rules), "--allow-uncommitted-rules", "--standalone", "--smoke", str(smoke),
                      "--exclusion-keys", str(keys), "--data-dumps", str(dd), "--data-dumps-cap-gb", "0.000001"], capsys)
    assert code == 75, out
    assert "tempfail" in out and "pending" in out["science"]
    assert not (tmp_path / "hist" / "h10_dlad" / "dlad_frame" / "manifest.json").exists()


def test_missing_inputs_refuse_or_wait(capsys, tmp_path):
    with pytest.raises(c10.Refused, match="not found"):
        dl.smoke_ok(tmp_path / "nosmoke.json", ("deribit",))
    bad = tmp_path / "s.json"
    bad.write_text(json.dumps({"smoke_version": "other"}))
    with pytest.raises(c10.Refused, match="smoke version"):
        dl.smoke_failures(bad, ("deribit",))
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"smoke_version": dl.SMOKE_VERSION, "criteria": {"deribit": True, "whitelist": False}}))
    assert dl.smoke_failures(ok, ("deribit", "whitelist")) == ["whitelist"]
    with pytest.raises(c10.Refused, match="criteria not met"):
        dl.smoke_ok(ok, ("whitelist",))
    # the census waits (exit 75) for q0202 / q0203 / the seal
    code, out = _run(["census", "--root", str(tmp_path / "cb10"), "--history-root", str(tmp_path / "hist")], capsys)
    assert code == 75 and "pending" in out["science"]
    code, out = _run(["screen", "--family", "D", "--root", str(tmp_path / "cb10"), "--freeze-spec", str(tmp_path / "f.json")], capsys)
    assert code == 2 and "freeze" in out["refused"]


def test_exclusion_pin_must_be_sha256(tmp_path):
    with pytest.raises(c10.Refused):
        run_cb10._extra_pins(["a:b"])
    assert run_cb10._extra_pins([f"n:p:{'a' * 64}"])[0]["name"] == "n"
    p = tmp_path / "ids.csv.gz"
    _write(p, ["market_id"], [["1"], ["2"]])
    with pytest.raises(c10.Refused, match="differs from the pin"):
        c10.read_ids_only(p, "0" * 64)
    from astrolabe.research_lab import h5_seal

    assert c10.read_ids_only(p, h5_seal.sha256_file(p)) == {"1", "2"}


# ---- freeze, triggers, Stage 2 -----------------------------------------------------------------------------------------------------------------


def test_analysis_jobs_refuse_before_freeze_and_triggers_refuse(capsys, tmp_path):
    (tmp_path / "census.json").write_text("{}")
    miss = str(tmp_path / "missing.json")
    for fam in ("D", "B"):
        code, out = _run(["screen", "--family", fam, "--root", str(tmp_path), "--freeze-spec", miss], capsys)
        assert code == 2 and "freeze" in out["refused"]
        code, out = _run(["rep", "--family", fam, "--root", str(tmp_path), "--freeze-spec", miss], capsys)
        assert code == 2 and "freeze" in out["refused"]
    spec = tmp_path / "cb10_v1.json"
    spec.write_text("{}")
    rules = c10.write_rules(tmp_path / "r.json")
    base = ["--freeze-spec", str(spec), "--allow-uncommitted-rules", "--rules", str(rules), "--root", str(tmp_path)]
    code, out = _run(["dlad-live", "--origin", "auto", *base], capsys)
    assert code == 2 and "did not advance" in out["refused"]
    code, out = _run(["rep", "--family", "D", *base], capsys)
    assert code == 75 and "pending" in out["science"]  # Stage-2 k needs both Stage-1 results final
    (tmp_path / "results_D.json").write_text(json.dumps({"D1": {"advance": False}}))
    (tmp_path / "results_B.json").write_text(json.dumps({"B1": {"advance": False}, "B2": {"advance": False}}))
    code, out = _run(["rep", "--family", "B", *base], capsys)
    assert code == 2 and "no B Stage 2" in out["refused"]
    code, out = _run(["rep", "--family", "D", *base], capsys)
    assert code == 2


def test_stage2_k_is_derived_and_fixed(tmp_path):
    with pytest.raises(cm.NotNow):
        c10.stage2_k(tmp_path)
    (tmp_path / "results_D.json").write_text(json.dumps({"D1": {"advance": True}}))
    with pytest.raises(cm.NotNow):
        c10.stage2_k(tmp_path)  # both Stage-1 files are needed
    (tmp_path / "results_B.json").write_text(json.dumps({"B1": {"advance": True}, "B2": {"advance": False}}))
    k = c10.stage2_k(tmp_path)
    assert k["k"] == 2 and k["advanced"] == ["D1", "B1"] and k["alpha_each"] == pytest.approx(0.025)


def test_dlad_live_exits_zero_after_t10_d2_end(monkeypatch, capsys, tmp_path):
    root = tmp_path / "cb10"
    root.mkdir()
    (root / "results_D.json").write_text(json.dumps({"D1": {"advance": True}, "written_epoch": 1_800_000_000.0}))
    spec = tmp_path / "cb10_v1.json"
    spec.write_text("{}")
    rules = c10.write_rules(tmp_path / "r.json")
    monkeypatch.setattr(run_cb10, "_commit_epoch", lambda p: 1_800_000_000.0)
    monkeypatch.setattr(run_cb10.time, "time", lambda: 1_800_000_000.0 + 200 * 86400)
    code, out = _run(["dlad-live", "--origin", "auto", "--root", str(root), "--freeze-spec", str(spec), "--allow-uncommitted-rules", "--rules", str(rules), "--standalone"], capsys)
    assert code == 0 and out["status"] == "stage2_over" and out["requests"] == 0


# ---- census: counts only, no guarded file, stalls carried --------------------------------------------------------------------------------------


def _d_fixture(hist: Path) -> None:
    import datetime as _dt

    d, lag = "2026-03-10", 5
    t = c10.noon_et(c10.day_add(d, -lag))
    fdir, ddir = hist / "h10_dlad" / "dlad_frame", hist / "h10_dlad" / "deribit"
    o = {c: "" for c in dl.ORIGIN_COLUMNS} | {"market_id": "m1", "asset": "BTC", "d": d, "lag": lag, "t": t, "strike": 70000.0, "status": dl.ST_ELIGIBLE, "truncated_for_t": 0,
                                              "p": 0.5, "t_p": t - 600, "size_p": 10, "p_reg": 0.45, "t_reg": t - 3000, "p_alt": 0.44, "p10": 0.5, "p_reg10": 0.45}
    _write(fdir / "origins.csv.gz", dl.ORIGIN_COLUMNS, [[o[c] for c in dl.ORIGIN_COLUMNS]])
    (fdir / "manifest.json").write_text(json.dumps({"status": "dlad_frame_complete", "reasons": {}, "drops": {}, "prints": {}}))
    exp = _dt.datetime(2026, 3, 10, 8, tzinfo=_dt.UTC)
    nm = exp.strftime("%d%b%y").upper().lstrip("0")
    rows = [["BTC", int(t), int(t * 1000) - 600_000 + i * 1000, f"BTC-{nm}-{70000 + (i - 4) * 1000}-C", 50.0 + i * 0.1, 70000.0, 1.0 + i, 0] for i in range(9)]
    _write(ddir / "trades.csv.gz", dl.TRADE_COLUMNS, rows)
    _write(ddir / "deribit_origins.csv.gz", dl.DORIGIN_COLUMNS, [["BTC", int(t), "ok", 9, 9, 0, 0, 0, 1, 1.0]])
    _write(ddir / "perp_bars.csv.gz", dl.BAR_COLUMNS, [])
    _write(ddir / "dvol.csv.gz", dl.DVOL_COLUMNS, [])
    _write(fdir / "outcomes_guarded.csv.gz", dl.OUTCOME_COLUMNS, [["m1", d, '["Yes","No"]', '["1","0"]']])
    _write(ddir / "settle_index_guarded.csv.gz", dl.SETTLE_COLUMNS, [["BTC", d, 0, 0, 71000.0]])


def test_census_opens_no_guarded_file_and_carries_b_stall(monkeypatch, capsys, tmp_path):
    hist, root = tmp_path / "hist", tmp_path / "cb10"
    _d_fixture(hist)
    c10.write_stall(hist / "h10_brk" / "brk_frame", c10.STALL_NOT_RUN_SOURCE, "smoke whitelist failed", "not testable (source)")
    monkeypatch.setattr(dl, "open_guarded", lambda *a, **k: (_ for _ in ()).throw(AssertionError("census opened a guarded file")))
    monkeypatch.setattr(br, "load_market_tx", lambda *a, **k: (_ for _ in ()).throw(AssertionError("census read a transaction file")))
    tp = tmp_path / "t.jsonl"
    code, out = _run(["census", "--root", str(root), "--history-root", str(hist), "--trials-path", str(tp)], capsys)
    assert code == 0, out
    doc = json.loads((root / "census.json").read_text())
    txt = json.dumps(doc)
    for forbidden in ("outcome_prices", "index_price\": 71000", "pnl", "mean_cents"):
        assert forbidden not in txt
    assert doc["counts_only"] is True and doc["D"]["n_units"] == 1 and doc["D"]["label_D1"] == "not testable (gate GD)" and doc["D"]["d1_runs"] is False
    assert doc["B"]["label_B1"] == "not testable (source)" and doc["B"]["weights_frozen"] == {}
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert [x["kind"] for x in lines] == ["cb10_descriptive"] and lines[0]["n_tests"] == 0
    code, out = _run(["census", "--root", str(root), "--history-root", str(hist)], capsys)
    assert code == 2  # the census is written once


# ---- screens: GDP / gate failure writes the counted p = 1 line ---------------------------------------------------------------------------------


def _screen_env(tmp_path, census: dict):
    root = tmp_path / "cb10"
    root.mkdir()
    (root / "census.json").write_text(json.dumps(census))
    spec = tmp_path / "cb10_v1.json"
    spec.write_text("{}")
    rules = c10.write_rules(tmp_path / "r.json")
    tp = tmp_path / "t.jsonl"
    return root, ["--root", str(root), "--history-root", str(tmp_path / "hist"), "--freeze-spec", str(spec), "--allow-uncommitted-rules", "--rules", str(rules), "--trials-path", str(tp)], tp


def test_mde_above_one_means_d1_not_run_counted_with_p_one(capsys, tmp_path):
    label = "not run (power): MDE 1.250 > 1.0"
    root, base, tp = _screen_env(tmp_path, {"D": {"d1_runs": False, "label_D1": label, "gate_GDP": {"mde": 1.25, "pass": False}}, "B": {}})
    code, out = _run(["screen", "--family", "D", *base], capsys)
    assert code == 0 and out["D1"]["p"] == 1.0 and out["D1"]["advance"] is False and out["D1"]["verdict"] == label
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    t = next(x for x in lines if x["kind"] == "cb10_test")
    assert t["hypothesis"] == "D1" and t["p"] == 1.0 and t["testable"] is False and t["n_tests"] == 0
    cnt = [x for x in lines if x["kind"] == "ml_explain"]
    assert len(cnt) == 1 and cnt[0]["n_tests"] == 1 and cnt[0]["source"] == "creative_batch_10:D"
    code, out = _run(["screen", "--family", "D", *base], capsys)
    assert code == 2 and "write-once" in out["refused"] and len(tp.read_text().splitlines()) == len(lines)


def test_screen_d_runs_only_when_census_says_so_and_does_not_open_guarded_otherwise(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(dl, "open_guarded", lambda *a, **k: (_ for _ in ()).throw(AssertionError("guarded file opened despite d1_runs False")))
    root, base, tp = _screen_env(tmp_path, {"D": {"d1_runs": False, "label_D1": "not testable (gate GD)"}, "B": {}})
    code, out = _run(["screen", "--family", "D", *base], capsys)
    assert code == 0 and out["D1"]["verdict"] == "not testable (gate GD)"


def test_screen_b_gate_failure_counts_b1_and_b2_with_p_one(capsys, tmp_path):
    root, base, tp = _screen_env(tmp_path, {"D": {}, "B": {"label_B1": "not testable (source limited)", "label_B2": "not testable (source limited)", "weights_frozen": {}}})
    code, out = _run(["screen", "--family", "B", *base], capsys)
    assert code == 0 and out["B1"]["p"] == 1.0 and out["B2"]["p"] == 1.0
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert {x["hypothesis"] for x in lines if x["kind"] == "cb10_test"} == {"B1", "B2"} and all(x["p"] == 1.0 for x in lines if x["kind"] == "cb10_test")
    assert sum(x["n_tests"] for x in lines if x["kind"] == "ml_explain") == 2


def test_screen_b_never_opens_holdout(monkeypatch, capsys, tmp_path):
    seen = []
    orig = br.load_market_tx
    monkeypatch.setattr(br, "load_market_tx", lambda rdir, split, mid, *, job: (seen.append((split, job)), orig(rdir, split, mid, job=job))[1])
    for split in (br.HOLDOUT,):
        for job in ("census", "screen-B"):
            with pytest.raises(br.Refused):
                br.load_market_tx(tmp_path, split, "1", job=job)
    assert all(s == br.HOLDOUT for s, _ in seen)


# ---- batch-Holm, trial lines and battery2 ---------------------------------------------------------------------------------------------------


def test_batch_holm_k1_fixed_at_three(capsys, tmp_path):
    lab = c10.batch_holm_label({"D1": 0.001})
    assert lab["k"] == 3 and set(lab["tests"]) == {"D1", "B1", "B2"} and lab["tests"]["D1"]["reject"]
    assert c10.batch_holm_label({"D1": 0.004})["tests"]["D1"]["reject"] is False  # 0.004 > 0.01 / 3
    assert c10.batch_holm_label({"D1": 0.003})["tests"]["D1"]["reject"] is True
    assert c10.batch_holm_label({"D1": 0.001})["not_run_as_p1"] == ["B1", "B2"]
    with pytest.raises(c10.Refused):
        c10.batch_holm_label({"D1-rep": 0.001})
    (tmp_path / "results_D.json").write_text(json.dumps({"D1": {"testable": True, "p": 0.001}}))
    (tmp_path / "results_B.json").write_text(json.dumps({"B1": {"testable": False, "p": 1.0}, "B2": {"testable": True, "p": 0.2}}))
    code, out = _run(["stage1-label", "--root", str(tmp_path)], capsys)
    assert code == 0 and out["batch_holm"]["k"] == 3 and out["batch_holm"]["tests"]["D1"]["reject"] and "B1" in out["batch_holm"]["not_run_as_p1"]


def test_trial_lines_counted_through_battery2(tmp_path):
    tp = tmp_path / "trials.jsonl"
    c10.log_test("D", "D1", {"p": 0.2, "testable": True, "effect": 0.1, "n": 100}, trials_path=tp, placebo={"note": "w", "advance_rate": 0.01, "n_draws": 200})
    c10.log_test("B", "B1", {"p": 0.004, "testable": False}, trials_path=tp)
    c10.log_test("B", "B2", {"p": 0.5, "testable": True}, trials_path=tp)
    c10.log_test("D", "D1-rep", {"p": 0.5}, replication=True, trials_path=tp, data_role=c10.DATA_ROLE_PROSP)
    c10.log_descriptive("census", {"x": 1}, trials_path=tp)
    r = battery2.cumulative_count(tp)
    assert r["total"] == 4 and r["by_kind"]["cb10_test"] == 0 and r["by_kind"]["cb10_replication"] == 0 and r["by_kind"]["cb10_descriptive"] == 0 and r["by_kind"]["ml_explain"] == 4
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert next(x for x in lines if x.get("hypothesis") == "B1" and x["kind"] == "cb10_test")["p"] == 1.0  # not testable -> p = 1
    assert sum(1 for x in lines if x.get("evidence_role") == "placebo") == 1 and all(x["n_tests"] == 0 for x in lines if x.get("evidence_role") == "placebo")
    assert next(x for x in lines if x["kind"] == "cb10_replication" and x["hypothesis"] == "D1-rep")["data_role"] == c10.DATA_ROLE_PROSP
    with pytest.raises(c10.Refused):
        c10.log_test("X", "X1", {}, trials_path=tp)


def test_battery2_kind_rules_exclude_cb10_and_unknown_kinds_raise():
    for k in ("cb10_test", "cb10_replication", "cb10_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    if provenance.TRIALS_PATH.exists():
        assert battery2.cumulative_count()["total"] >= 1131


# ---- end-to-end frame run on a fake transport: nothing forbidden is written or logged ------------------------------------------------------------


def _fake_transport(market: dict, prints: list[dict]):
    calls = []

    def transport(url, params):
        calls.append((url, dict(params)))
        if url == hb.GAMMA_MARKETS:
            body = [market] if int(params.get("offset", 0)) == 0 else []
        elif url == hb.DATA_TRADES:
            body = prints if int(params.get("offset", 0)) == 0 else []
        else:
            return 404, b"", {}
        return 200, json.dumps(body).encode(), {}

    return transport, calls


def test_dlad_frame_end_to_end_writes_no_forbidden_field_and_guards_outcomes(tmp_path):
    from tests.test_cb10_dlad import _live_market

    d = "2026-10-20"
    m = _live_market(d)
    t = c10.noon_et(c10.day_add(d, -5))
    prints = [{"timestamp": t - 600, "outcomeIndex": 0, "price": 0.5, "size": 10, "transactionHash": "0x1", "proxyWallet": "0xWALLET", "side": "BUY"},
              {"timestamp": t - 4000, "outcomeIndex": 0, "price": 0.45, "size": 10, "transactionHash": "0x2", "proxyWallet": "0xWALLET2", "side": "SELL"}]
    tr, calls = _fake_transport(m, prints)
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"smoke_version": dl.SMOKE_VERSION, "criteria": {k: True for k in ("ladder_frame", "live_flags", "data_api_paging", "tx_aggregation", "whitelist")}}))
    kd = tmp_path / "keys"
    kd.mkdir()
    keys = kd / "exclusion_keys.csv.gz"
    _write(keys, ["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [["1", "1", "9", "", ""]])
    from astrolabe.research_lab import h5_seal

    (kd / c10.EXCLUSION_REPORT_NAME).write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified"}))
    root = tmp_path / "h10_dlad"
    res = dl.dlad_frame(root, tr, rules_sha="r" * 64, smoke_path=smoke, exclusion_keys_path=keys, now=PAST_SEAL, rps=1000.0, window=(d, c10.day_add(d, 1)),
                        data_dumps=None, sleep=lambda s: None)
    assert res["status"] == "dlad_frame_complete", res
    rdir = root / dl.FRAME_RUN
    from astrolabe.research_lab import cb7_common as c7

    for name in ("frame.csv.gz", "frame_all.csv.gz", "origins.csv.gz"):
        text = "\n".join(json.dumps(r) for r in c7.read_csv_gz(rdir / name))
        for forbidden in (*c10.GAMMA_FORBIDDEN, "0.99", "123456", "resolved", "WALLET", "BUY", "SELL", "0x1", "0x2", "Binance"):
            assert forbidden not in text, (name, forbidden)
    for f in rdir.iterdir():
        if f.name not in dl.GUARDED_FILES and f.suffix == ".json":
            assert "outcomePrices" not in f.read_text() and "outcome_prices" not in f.read_text()
    assert "outcome_prices" in "\n".join(json.dumps(r) for r in c7.read_csv_gz(rdir / "outcomes_guarded.csv.gz"))
    org = list(c7.read_csv_gz(rdir / "origins.csv.gz"))
    assert len(org) == 2 and org[0]["status"] == dl.ST_ELIGIBLE and float(org[0]["p"]) == 0.5 and float(org[0]["p_reg"]) == 0.45
    assert set(org[0]) == set(dl.ORIGIN_COLUMNS)
    assert all(u == hb.GAMMA_MARKETS or u == hb.DATA_TRADES for u, _ in calls)
    again = dl.dlad_frame(root, tr, rules_sha="r" * 64, smoke_path=smoke, exclusion_keys_path=keys, now=PAST_SEAL, window=(d, c10.day_add(d, 1)), data_dumps=None)
    assert again["complete"] is True  # idempotent re-run
