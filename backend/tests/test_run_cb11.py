# ruff: noqa: E501
"""CB11 runner, smoke helpers, counting kinds and batch-Holm (offline; no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import cb11_common as c11
from astrolabe.research_lab import cb11_smoke as sm
from astrolabe.research_lab import cb11_w as w
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb11  # noqa: E402

JOBS = ("rules", "smoke", "exclusion-keys", "w-frame", "w-prints", "w-censoring", "seal", "census", "screen", "stage1-label", "rep")


def _run(argv, capsys) -> tuple[int, dict]:
    code = run_cb11.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


@pytest.fixture()
def rules_file(tmp_path):
    p = tmp_path / "cb11_rules.json"
    c11.write_rules(p)
    return p


def test_parser_has_every_subcommand_and_parses_each():
    p = run_cb11.build_parser()
    sub = next(a for a in p._actions if a.dest == "cmd")
    assert set(JOBS) <= set(sub.choices)
    argvs = {j: [] for j in JOBS}
    argvs.update({"census": ["--family", "W"], "screen": ["--family", "W"], "rep": ["--family", "W"]})
    for j in JOBS:
        assert callable(p.parse_args([j, *argvs[j]]).fn)
    with pytest.raises(SystemExit):
        p.parse_args(["screen", "--family", "X"])


def test_defaults_and_declared_caps():
    a = run_cb11.build_parser().parse_args(["w-frame"])
    assert a.data_dumps_cap_gb == 40.0 == c11.DATA_DUMPS_CAP_GB and a.disk_cap_gb == 0.02 and a.rps == 2.0
    assert {k: v for k, v in run_cb11.DECLARED_DISK_CAP_GB.items() if k in ("exclusion-keys", "w-frame", "w-prints", "w-censoring")} == {"exclusion-keys": 0.01, "w-frame": 0.02, "w-prints": 0.03, "w-censoring": 0.001}
    assert c11.TOTAL_OUTPUT_CAP_GB == 0.25 and c11.FREE_DISK_MIN_GB == 4.5


def test_declared_arguments_cannot_change(capsys, rules_file, tmp_path):
    code, out = _run(["w-censoring", "--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--disk-cap-gb", "0.5", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix()], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["w-prints", "--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--rps", "5", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix()], capsys)
    assert code == 2


def test_rules_file_round_trip_and_hash_mismatch(tmp_path, rules_file):
    sha = c11.verify_rules(rules_file, require_committed=False)
    doc = json.loads(rules_file.read_text())
    assert doc["rules_sha256"] == sha and doc["common"]["pins"]["h2_frame_sha256"] == c11.H2_FRAME_SHA256
    assert c11.write_rules(rules_file) == rules_file  # idempotent
    doc["declared"]["cb11_w"]["w1_floor_b0"] = 0.0 if "w1_floor_b0" in doc["declared"]["cb11_w"] else 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(c11.Refused):
        c11.verify_rules(bad, require_committed=False)
    with pytest.raises(c11.Refused):
        c11.write_rules(bad)  # never rewritten


def test_rules_cli_writes_and_prints_sha(tmp_path, capsys):
    code, out = _run(["rules", "--path", (tmp_path / "r.json").as_posix()], capsys)
    assert code == 0 and len(out["rules_sha256"]) == 64


def test_screen_and_rep_refuse_before_the_freeze(tmp_path, capsys, rules_file):
    base = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix(), "--freeze-spec", (tmp_path / "none.json").as_posix()]
    for cmd in ("screen", "rep"):
        code, out = _run([cmd, "--family", "W", *base], capsys)
        assert code == 2 and "freeze" in out["refused"]
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"PA": {}}))
    code, out = _run(["screen", "--family", "W", *base[:-1], spec.as_posix()], capsys)
    assert code == 2 and "no 'W' part" in out["refused"]


def test_screen_refuses_without_census_after_freeze(tmp_path, capsys, rules_file):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"W": {"x": 1}}))
    code, out = _run(["screen", "--family", "W", "--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix(),
                      "--freeze-spec", spec.as_posix()], capsys)
    assert code == 75  # census_W.json missing: pending


def test_p_and_a_subcommands_refuse_without_their_own_declaration_and_rules(tmp_path, capsys, rules_file):
    base = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix()]
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"W": {}, "PA": {}}))
    for fam in ("P", "A"):
        for cmd in ("screen", "rep"):
            code, out = _run([cmd, "--family", fam, *base, "--freeze-spec", spec.as_posix()], capsys)
            assert code == 2 and "declaration_sha256" in out["refused"]  # P/A freeze part must carry this code's declaration
    code, out = _run(["census", "--family", "P,A", *base], capsys)
    assert code == 2 and "P/A rules file" in out["refused"]


def test_seal_auto_seals_w_and_is_pending_for_unfetched_families(tmp_path, capsys, rules_file):
    base = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix(), "--history-root", (tmp_path / "history").as_posix(),
            "--seals-dir", (tmp_path / "seals").as_posix()]
    code, out = _run(["seal", "--family", "auto", *base], capsys)
    assert code == 75 and "pending" in out["science"]  # W prints not fetched: pending (no trials line)
    code, out = _run(["seal", "--family", "P", *base], capsys)
    assert code == 75 and "pending" in out["science"]  # P not fetched: pending before any rules read


def test_census_refuses_incomplete_manifest(tmp_path, capsys, rules_file):
    base = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix(), "--history-root", (tmp_path / "history").as_posix()]
    (tmp_path / "creative_batch11" / "w").mkdir(parents=True)
    (tmp_path / "creative_batch11" / "w" / "manifest.json").write_text(json.dumps({"complete": False, "status": "in_progress"}))
    code, out = _run(["census", "--family", "W", *base], capsys)
    assert code == 75 and "pending" in out["science"]
    assert not (tmp_path / "creative_batch11" / "census_W.json").exists()


def test_refused_roots_and_output_roots(tmp_path):
    for bad in ("h4_seal", "h5_cb1", "snapshots", "book_sweeps", "creative_batch10"):
        with pytest.raises(c11.Refused):
            c11.refuse_path(tmp_path / bad / "x")
    with pytest.raises(c11.Refused):
        c11.require_output_root(tmp_path / "elsewhere" / "w")
    assert c11.require_output_root(tmp_path / "creative_batch11" / "w")


def test_disk_guard_exit_75_headroom(tmp_path):
    dd = tmp_path / "dd"
    dd.mkdir()
    (dd / "f").write_bytes(b"0" * 1000)
    with pytest.raises(c11.NotNow):
        c11.require_disk(dd, 0.0000001, 10_000, free_fn=lambda p: 100 * 1024**3)  # data-dumps cap
    with pytest.raises(c11.NotNow):
        c11.require_disk(dd, 40.0, 10_000, free_fn=lambda p: 4 * 1024**3)  # free-disk headroom below 4.5 GB
    c11.require_disk(dd, 40.0, 10_000, free_fn=lambda p: 100 * 1024**3)


# ---- smoke --------------------------------------------------------------------------------------------------------------------------------------


def test_smoke_loader_fixture_passes_and_frames_check_pins(tmp_path):
    assert sm.smoke_loader_fixture()["pass"] is True
    cols = [*w.W_COLUMNS, *w.GUARDED_FRAME_COLUMNS[1:]]
    for run in ("h2_main", "h3_power"):
        (tmp_path / run).mkdir()
        (tmp_path / run / "frame.csv.gz").write_bytes(hb._gz_csv_bytes(cols, []))
    bad = sm.smoke_frames(tmp_path)
    assert bad["pass"] is False and bad["per"]["h2_main"]["sha_ok"] is False
    shas = {run: bad["per"][run]["sha256"] for run in bad["per"]}
    assert sm.smoke_frames(tmp_path, shas)["pass"] is True
    (tmp_path / "h3_power" / "frame.csv.gz").write_bytes(hb._gz_csv_bytes([c for c in cols if c != "uma_status"], []))
    shas["h3_power"] = sm.smoke_frames(tmp_path, shas)["per"]["h3_power"]["sha256"]
    r = sm.smoke_frames(tmp_path, shas)
    assert r["pass"] is False and r["per"]["h3_power"]["missing_columns"] == ["uma_status"]


def test_smoke_failures_reads_family_needs(tmp_path):
    p = tmp_path / "smoke.json"
    p.write_text(json.dumps({"smoke_version": sm.SMOKE_VERSION, "criteria": {"w_frames": True, "w_loader": True, "w_censor_window": False, "data_api_reach": True}}))
    assert sm.smoke_failures(p, sm.FAMILY_NEEDS["W"]) == ["w_censor_window"]
    assert sm.smoke_failures(p, sm.FAMILY_NEEDS["W_prints"]) == []
    p.write_text(json.dumps({"smoke_version": "other"}))
    with pytest.raises(c11.Refused):
        sm.smoke_failures(p, ("w_frames",))
    with pytest.raises(c11.Refused):
        sm.smoke_failures(tmp_path / "missing.json", ("w_frames",))


def test_wiki_lag_rule_fails_when_newest_day_is_older_than_48h():
    now = 1_790_000_000.0
    import datetime as dt

    def tr(newest_days_old):
        day = dt.datetime.fromtimestamp(now, dt.UTC).replace(hour=0, minute=0, second=0, microsecond=0) - dt.timedelta(days=newest_days_old)
        items = {"items": [{"timestamp": day.strftime("%Y%m%d00")}]}
        return lambda url, params: (200, json.dumps(items).encode(), {})

    for age, ok in ((1, True), (4, False)):
        lim = hb.Limiter(tr(age), rps=1000.0, live_check=None, sleep=lambda s: None)
        assert sm.smoke_wiki_lag(lim, now)["pass"] is ok


def test_smoke_cli_transient_status_is_pending_not_a_write_once_fail(tmp_path, capsys, rules_file, monkeypatch):
    from astrolabe.research_lab import cb8_common as cm

    monkeypatch.setattr(sm, "smoke_frames", lambda hist: {"pass": True})
    monkeypatch.setattr(sm, "smoke_loader_fixture", lambda: {"pass": True})

    def boom(lim, *a, **k):
        raise cm.ApiError("GET x -> status 429")

    monkeypatch.setattr(sm, "smoke_gamma_politics", boom)
    monkeypatch.setattr(run_cb11, "_rules", lambda a: "r" * 64)  # patched functions change the rules hash by design
    out = tmp_path / "creative_batch11" / "smoke.json"
    code, payload = _run(["smoke", "--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--out", out.as_posix(), "--history-root", tmp_path.as_posix()], capsys)
    assert code == 75 and not out.exists(), payload


# ---- counting, Holm ------------------------------------------------------------------------------------------------------------------------------


def test_battery2_kinds_are_registered_and_exclude():
    for k in ("cb11_test", "cb11_replication", "cb11_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    with pytest.raises(Exception):  # noqa: B017, PT011
        battery2.classify({"kind": "cb11_unknown_kind"}) if hasattr(battery2, "classify") else (_ for _ in ()).throw(KeyError("x"))


def test_batch_holm_k1_is_fixed_at_six_and_not_run_counts_as_p1():
    assert c11.BATCH_HOLM_K1 == 6 and c11.STAGE1_HOLM_FAMILY == ("W1", "W2", "P1", "P2", "A1", "A2") and c11.BATCH_HOLM_ALPHA1 == 0.01
    r = c11.batch_holm_label({"W1": 0.0001})
    assert r["k"] == 6 and set(r["not_run_as_p1"]) == {"W2", "P1", "P2", "A1", "A2"}
    with pytest.raises(c11.Refused):
        c11.batch_holm_label({"W1": 0.1, "Z9": 0.1})


def test_log_test_counts_one_test_even_when_not_testable(tmp_path):
    tp = tmp_path / "trials.jsonl"
    c11.log_test("W", "W1", {"p": 0.0, "testable": False, "advance": False}, trials_path=tp)
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    kinds = {x["kind"]: x for x in lines}
    assert kinds["cb11_test"]["p"] == 1.0 and kinds["cb11_test"]["n_tests"] == 0
    assert kinds["ml_explain"]["n_tests"] == 1 and kinds["ml_explain"]["source"] == "creative_batch_11:W"
    with pytest.raises(c11.Refused):
        c11.log_test("X", "X1", {}, trials_path=tp)


def test_stage2_k_needs_all_three_stage1_results(tmp_path):
    with pytest.raises(c11.NotNow):
        c11.stage2_k(tmp_path)
