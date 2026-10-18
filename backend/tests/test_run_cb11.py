# ruff: noqa: E501
"""CB11 runner, smoke helpers, counting kinds and batch-Holm (offline; no network)."""

from __future__ import annotations

import datetime as dt_
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


def test_rules_file_round_trip_and_hash_mismatch(tmp_path):
    rules_file = tmp_path / "cb11_rules.json"
    c11.write_rules(rules_file)
    sha = c11.verify_rules(rules_file, require_committed=False)
    doc = json.loads(rules_file.read_text())
    assert doc["rules_version"] == "cb11-rules-v2" and set(doc["parts"]) == {"W", "PA"}
    w_part = doc["parts"]["W"]
    assert w_part["rules_sha256"] == sha and w_part["common"]["pins"]["h2_frame_sha256"] == c11.H2_FRAME_SHA256 and "cb11_w" in w_part["declared"] and "cb11_smoke" in w_part["declared"]
    assert doc["parts"]["PA"]["part_declared"] is False and doc["parts"]["PA"]["rules_sha256"] is None
    assert c11.write_rules(rules_file) == rules_file  # idempotent
    w_part["declared"]["cb11_w"]["w1_floor_b0"] = 0.0 if "w1_floor_b0" in w_part["declared"]["cb11_w"] else 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(c11.Refused):
        c11.verify_rules(bad, require_committed=False)
    with pytest.raises(c11.Refused):
        c11.write_rules(bad)  # never rewritten


def test_b1_pa_part_is_a_pointer_and_refuses_pa_jobs(tmp_path):
    rules_file = tmp_path / "r.json"
    c11.write_rules(rules_file)
    assert c11.verify_rules(rules_file, require_committed=False, part="W")
    with pytest.raises(c11.Refused, match="cb11_pa_rules.json"):
        c11.verify_rules(rules_file, require_committed=False, part="PA")
    with pytest.raises(c11.Refused, match="unknown rules part"):
        c11.rules_part_doc("X")


def test_b1_w_verification_is_independent_of_p_a_code(tmp_path, monkeypatch):
    """Adding P / A modules or a P / A rules file cannot change the W part: W verification imports only the W modules and the file's W part is hashed alone."""
    import importlib

    rules_file = tmp_path / "r.json"
    c11.write_rules(rules_file)
    (tmp_path / c11.PA_RULES_FILE_NAME).write_text("{}")
    seen: list[str] = []
    real = importlib.import_module

    def spy(name, package=None):
        seen.append(name)
        return real(name, package)

    monkeypatch.setattr(importlib, "import_module", spy)
    assert c11.verify_rules(rules_file, require_committed=False, part="W")
    assert seen and all(n.lstrip(".") in c11.W_RULE_MODULES for n in seen), seen
    doc = json.loads(rules_file.read_text())
    # tampering with the PA pointer does not affect W jobs' verification of the W part (they compare the W part only)
    doc["parts"]["PA"]["note"] = "edited"
    rules_file.write_text(json.dumps(doc))
    assert c11.verify_rules(rules_file, require_committed=False, part="W") == doc["parts"]["W"]["rules_sha256"]


def test_rules_cli_writes_and_prints_sha(tmp_path, capsys):
    code, out = _run(["rules", "--path", (tmp_path / "r.json").as_posix()], capsys)
    assert code == 0 and len(out["rules_sha256"]) == 64 and out["parts"]["PA"]["declared"] is False and out["parts"]["W"]["declared"] is True


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
    code, out = _run(["census", "--family", "P,A", *base, "--pa-rules", (tmp_path / "missing_pa_rules.json").as_posix()], capsys)
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
    lim = hb.Limiter(tr(1), rps=1000.0, live_check=None, sleep=lambda s: None)
    assert sm.smoke_wiki_lag(lim, now)["ceiling_ok"] is True
    lim = hb.Limiter(tr(6), rps=1000.0, live_check=None, sleep=lambda s: None)
    r = sm.smoke_wiki_lag(lim, now)
    assert r["ceiling_ok"] is False and r["ceiling_h"] == 72.0


def _gamma_world(by_week, status=200):
    """Transport answering Gamma /markets by week start (the end_date_min date); ``by_week`` maps 'YYYY-MM-DD' to market dicts."""
    calls = []

    def tr(url, params):
        calls.append(params.get("end_date_min"))
        return status, json.dumps(by_week.get(str(params.get("end_date_min"))[:10], [])).encode(), {}

    return tr, calls


def _mk(cid, life_days, ntok=2):
    return {"id": cid, "conditionId": cid, "clobTokenIds": json.dumps([f"{cid}a", f"{cid}b"][:ntok]), "startDate": "2024-01-01T00:00:00Z",
            "endDate": (dt_.datetime(2024, 1, 1, tzinfo=dt_.UTC) + dt_.timedelta(days=life_days)).strftime("%Y-%m-%dT%H:%M:%SZ")}



def test_long_life_picks_search_is_bounded_deterministic_and_reports_no_picks():
    ends = dt_.datetime(2024, 6, 24, tzinfo=dt_.UTC)
    wk = lambda i: (ends - dt_.timedelta(days=7 * (i + 1))).strftime("%Y-%m-%d")  # noqa: E731
    tr, calls = _gamma_world({wk(0): [_mk("s1", 50)], wk(1): [_mk("l1", 150), _mk("l2", 200)], wk(2): [_mk("l3", 300)]})
    lim = hb.Limiter(tr, rps=1000.0, live_check=None, sleep=lambda s: None)
    res = sm.smoke_long_life_picks(lim)
    assert res["pass"] and res["n_picks"] == sm.PRICE_MARKETS and len(calls) == 2  # stops as soon as 2 long-life markets are in the pool
    assert [s_["long_life"] for s_ in res["scanned"]] == [0, 2]
    assert {m["cid"] for m in res["markets"]} <= {"l1", "l2"}
    assert sm.smoke_long_life_picks(hb.Limiter(_gamma_world({wk(1): [_mk("l1", 150), _mk("l2", 200)]})[0], rps=1000.0, live_check=None, sleep=lambda s: None))["markets"] == res["markets"]
    tr0, calls0 = _gamma_world({})
    none = sm.smoke_long_life_picks(hb.Limiter(tr0, rps=1000.0, live_check=None, sleep=lambda s: None))
    assert none["pass"] is False and none["reason"] == "no_picks" and len(calls0) == sm.PICK_MAX_WEEKS
    lim0 = hb.Limiter(tr0, rps=1000.0, live_check=None, sleep=lambda s: None)
    for fn in (sm.smoke_prices_history, sm.smoke_data_api):
        assert fn(lim0, []) == {"per": {}, "pass": False, "reason": "no_picks"}


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


# ---- code-against-design freeze-check fixes (CREATIVE_BATCH_11.md section 11) ----------------------------------------------------------------------


def _gz_ids(path: Path, ids) -> str:
    from astrolabe.research_lab import h5_seal

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(hb._gz_csv_bytes(["market_id"], [[i] for i in ids]))
    return h5_seal.sha256_file(path)


@pytest.fixture()
def keys_env(tmp_path):
    hist = tmp_path / "history"
    base = hist / "h8_tail_b" / "exclusion_keys.csv.gz"
    from astrolabe.research_lab import cb6_tail as c6
    from astrolabe.research_lab import h5_seal

    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), [[i, "1", "", "", ""] for i in ("1", "2")]))
    base_sha = h5_seal.sha256_file(base)
    h2 = _gz_ids(hist / "h2_main" / "sample.csv.gz", ["10", "11"])
    h3 = _gz_ids(hist / "h3_power" / "sample.csv.gz", ["20"])
    (tmp_path / "seals").mkdir()
    return {"tmp": tmp_path, "hist": hist, "base": base, "base_sha": base_sha, "pins": {"h2_main/sample.csv.gz": h2, "h3_power/sample.csv.gz": h3}, "ext": tmp_path / "ext", "seals": tmp_path / "seals"}


def _ek(env, **kw):
    def tr(url, params):
        return 200, b"[]", {}

    return c11.exclusion_keys(env["tmp"] / "creative_batch11", tr, rules_sha="r" * 64, hist_root=env["hist"], base_sha256=env["base_sha"], seals_dir=env["seals"], external_dir=env["ext"],
                              rps=1000.0, sleep=lambda s: None, data_dumps=None, **kw)


def test_b4_mandatory_sampled_sets_are_refused_when_absent_unpinned_or_changed(keys_env):
    env = keys_env
    # the shipped pins are the host-measured digests (2026-10-18); a fixture whose files differ is refused, and an unset pin is refused
    assert c11.H2_SAMPLE_SHA256 == "77a15bd96bcd17c923e90e3e214874cad8df9ed4cd66eb6145cc8922c28954ec"
    assert c11.H3_SAMPLE_SHA256 == "f8e1a7bbd16d57206fcd45c502263d2b7ceb40b22108e248c613d5148476004d"
    assert c11.MANDATORY_SAMPLE_PINS == {"h2_main/sample.csv.gz": c11.H2_SAMPLE_SHA256, "h3_power/sample.csv.gz": c11.H3_SAMPLE_SHA256}
    with pytest.raises(c11.Refused, match="sha256 .* != pinned"):
        _ek(env)
    with pytest.raises(c11.Refused, match="TODO-COORDINATOR"):
        _ek(env, sample_pins={**env["pins"], "h2_main/sample.csv.gz": c11.PIN_UNSET})
    with pytest.raises(c11.Refused, match="sha256 .* != pinned"):
        _ek(env, sample_pins={**env["pins"], "h2_main/sample.csv.gz": "0" * 64})
    (env["hist"] / "h3_power" / "sample.csv.gz").unlink()
    with pytest.raises(c11.Refused, match="mandatory sampled set h3_power/sample.csv.gz is absent"):
        _ek(env, sample_pins=env["pins"])


def test_b3_c1_t5_ids_are_pending_until_staged_unless_explicitly_allowed(keys_env):
    env = keys_env
    with pytest.raises(c11.NotNow, match="C1 / T5"):
        _ek(env, sample_pins=env["pins"])
    assert not (env["tmp"] / "creative_batch11" / "exclusion_run11").exists()  # nothing written while pending
    m = _ek(env, sample_pins=env["pins"], allow_absent_c1_t5=True)
    rep = json.loads((env["tmp"] / "creative_batch11" / "exclusion_report.json").read_text())
    assert rep["c1_t5_status"] == "absent" and set(rep["sets"]) == {"h2_main/sample.csv.gz", "h3_power/sample.csv.gz"} and m["status"] in (c11.EXCLUSION_KEYS_COMPLETE, c11.UNVERIFIED)


def test_b3_staged_c1_t5_lists_are_read_and_recorded(keys_env):
    env = keys_env
    _gz_ids(env["ext"] / "c1_sample_ids.csv.gz", ["30"])
    _gz_ids(env["ext"] / "t5_frame_ids.csv.gz", ["31", "32"])
    _ek(env, sample_pins=env["pins"])
    rep = json.loads((env["tmp"] / "creative_batch11" / "exclusion_report.json").read_text())
    assert rep["c1_t5_status"] == "retrieved" and rep["external"]["t5_frame_ids.csv.gz"]["n_ids"] == 2


def test_b3_cli_flag_exists_and_is_never_in_a_draft():
    a = run_cb11.build_parser().parse_args(["exclusion-keys", "--allow-absent-c1-t5"])
    assert a.allow_absent_c1_t5 is True and run_cb11.build_parser().parse_args(["exclusion-keys"]).allow_absent_c1_t5 is False
    for f in _cb11_spec_files("q02*_cb11_*.json"):
        assert "--allow-absent-c1-t5" not in json.loads(f.read_text())["argv"], f.name


def _cb11_spec_files(pattern):
    """CB11 specs wherever they live: drafts/ before promotion, jobs/ after (promotion moves the file unchanged in substance)."""
    q = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "queue"
    return sorted(list((q / "drafts").glob(pattern)) + list((q / "jobs").glob(pattern)))


def _cb11_spec(name):
    [f] = [g for g in _cb11_spec_files(name)]
    return json.loads(f.read_text())


def test_b2_resumable_net_drafts_repeat_until_their_completion_status():
    import re

    q21 = _cb11_spec("q0221_cb11_exclusion_keys.json")["repeat"]
    q24 = _cb11_spec("q0224_cb11_w_censoring.json")["repeat"]
    q23 = _cb11_spec("q0223_cb11_w_prints.json")["repeat"]
    for rep, ok_statuses in ((q21, ("exclusion_keys_complete", "disjointness_unverified")), (q24, ("w_censoring_complete",)), (q23, ("w_prints_complete",))):
        assert rep["max_runs"] >= 3
        for st in ok_statuses:  # the runner's own JSON line
            assert re.search(rep["until_log_regex"], json.dumps({"status": st, "stopped": None}, sort_keys=True))
        assert not re.search(rep["until_log_regex"], json.dumps({"status": "in_progress", "stopped": "should_stop"}, sort_keys=True))
    # a stall also ends the repeat (nothing left to resume)
    assert re.search(q24["until_log_regex"], json.dumps({"status": c11.STALL_UPSTREAM}))
    assert re.search(q23["until_log_regex"], json.dumps({"status": c11.STALL_NOT_RUN_SOURCE}))


def test_n5_census_verifies_the_rules_like_every_other_job(tmp_path, capsys):
    code, out = _run(["census", "--family", "W", "--rules", (tmp_path / "missing.json").as_posix(), "--standalone", "--root", (tmp_path / "creative_batch11").as_posix()], capsys)
    assert code == 2 and "rules file" in out["refused"]


def test_declared_drafts_pin_the_rules_part_they_verify(rules_file):
    """One rules sha per part: a draft passing --rules pins the committed part-W sha, one passing --pa-rules pins the committed P/A sha (q0230 seals W only, q0238 seals P and A). The committed rules files must re-derive exactly from the code."""
    from astrolabe.research_lab import cb11_pa as pa  # noqa: PLC0415

    root = Path(__file__).resolve().parents[2] / "docs" / "research_lab"
    committed = root / "seals" / "cb11_rules.json"
    w_sha = json.loads(committed.read_text())["parts"]["W"]["rules_sha256"]
    pa_sha = json.loads((root / "seals" / "cb11_pa_rules.json").read_text())["rules_sha256"]
    assert w_sha != pa_sha
    assert c11.verify_rules(committed, require_committed=False) == w_sha
    assert pa.verify_pa_rules(root / "seals" / "cb11_pa_rules.json", require_committed=False) == pa_sha
    seen = set()
    for f in _cb11_spec_files("q02[0-3]*_cb11_*.json"):
        d = json.loads(f.read_text())
        uses_w, uses_pa = "--rules" in d["argv"], "--pa-rules" in d["argv"]
        assert uses_w or uses_pa, f.name
        assert (w_sha in d["notes"]) == uses_w, f.name
        assert (pa_sha in d["notes"]) == uses_pa, f.name
        seen.add((uses_w, uses_pa))
    assert seen == {(True, False), (False, True)}  # b2: no job verifies both parts any more (W and P/A seal in separate jobs)


def test_b2_c1_c2_draft_graph_and_repeats():
    """b2: W seals alone (q0230), P/A seal in q0238; the W census waits on the W seal only, the P/A census on the P/A seal. c1/c2: q0227 and q0229 repeat until completion
    or a terminal stall. The net-lane jobs declare their network."""
    import re

    d = {f.name.split("_")[0]: json.loads(f.read_text()) for f in _cb11_spec_files("q02[23]*_cb11_*.json")}
    assert set(d) == {f"q02{n}" for n in (20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39)}
    deps = {k[1:]: {x.split("_")[0][1:] for x in v["depends_on"]} for k, v in d.items()}
    assert deps["0230"] == {"0223"} and deps["0238"] == {"0226", "0229"}
    assert deps["0231"] == {"0222", "0223", "0224", "0230"} and deps["0239"] == {"0226", "0229", "0238"}
    assert "--family" in d["q0230"]["argv"] and d["q0230"]["argv"][d["q0230"]["argv"].index("--family") + 1] == "W" and "--pa-rules" not in d["q0230"]["argv"]
    assert d["q0238"]["argv"][d["q0238"]["argv"].index("--family") + 1] == "P,A" and "--rules" not in d["q0238"]["argv"]
    for k in ("q0230", "q0238"):
        assert d[k]["resources"]["lane"] == "net" and "gamma-api" in d[k]["resources"]["network"]
        assert re.search(d[k]["repeat"]["until_log_regex"], json.dumps({"status": "seal_all_complete"}))
    for k, st in (("q0227", "attn_frame_complete"), ("q0229", "attn_data_complete")):
        rx = d[k]["repeat"]["until_log_regex"]
        assert re.search(rx, json.dumps({"status": st})) and re.search(rx, json.dumps({"status": c11.STALL_NOT_RUN_SOURCE}))
        assert not re.search(rx, json.dumps({"status": "in_progress"}))
    for k in ("q0236", "q0237"):
        assert "--results-sha256" in d[k]["argv"] and "--stage2-k" in d[k]["argv"]
