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
    assert not (tmp_path / "creative_batch11" / run_cb11.CENSUS_W_NAME).exists()


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
    assert not (env["tmp"] / "creative_batch11" / c11.EXCLUSION_RUN).exists()  # nothing written while pending
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


# ---- q0221b amendment (2026-10-19): id sources are sampled sets only, keys reused from sources, Gamma lookup only where missing ---------------------


def _gz_jsonl(path: Path, recs) -> None:
    import gzip

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress("".join(json.dumps(r) + "\n" for r in recs).encode()))


def _gamma_id_world(requested: list):
    """A Gamma stub answering id lookups (closed-first); every id is found with event ``e<id>`` and series ``s<id>``; ids are recorded."""
    def tr(url, params):
        ids = list(params.get("id") or [])
        requested.extend(ids)
        return 200, json.dumps([{"id": x, "negRiskMarketID": "", "events": [{"id": f"e{x}", "series": [{"id": f"s{x}"}]}]} for x in ids]).encode(), {}

    return tr


def _ek_tr(env, tr, **kw):
    return c11.exclusion_keys(env["tmp"] / "creative_batch11", tr, rules_sha="r" * 64, hist_root=env["hist"], base_sha256=env["base_sha"], seals_dir=env["seals"], external_dir=env["ext"],
                              rps=1000.0, sleep=lambda s: None, data_dumps=None, sample_pins=env["pins"], allow_absent_c1_t5=True, **kw)


def _read_keys(path: Path) -> dict:
    import csv
    import gzip

    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        return {r["market_id"]: r for r in csv.DictReader(fh)}


WALK_REC = {"closed_mode": True, "event_id": "100000", "end_epoch": 1.7e9, "n_markets": 1, "series": [{"id": "10471", "slug": "cwbb"}], "weather_title": 0,
            "markets": [{"condition_id": "0x02ee", "market_id": "895462", "neg_risk": 0, "token0": "41113676899602530408177395539852999864414424096397961499466716808226893315607", "token1": "8280"}]}
UNIT_REC = {"unit_id": "s9:e1:e2", "series_id": "10007", "pred_event_id": "67280", "succ_event_id": "80636", "pred_market_ids": ["40"],
            "pred_markets": [{"market_id": "40", "condition_id": "0xa", "token0": "1", "token1": "2"}], "succ_markets": [{"market_id": "41", "condition_id": "0xb", "token0": "3", "token1": "4"}]}


def test_q0221b_series_source_is_the_sampled_unit_frame_never_the_walk(keys_env):
    env = keys_env
    assert ("h7_cb4_series", "units.jsonl.gz") in c11.ID_SOURCES and not any("walk" in fn for _, fn in c11.ID_SOURCES)
    _gz_jsonl(env["hist"] / "h7_cb4_series" / "walk_events.jsonl.gz", [WALK_REC])
    _gz_jsonl(env["hist"] / "h7_cb4_series" / "units.jsonl.gz", [UNIT_REC])
    asked: list = []
    m = _ek_tr(env, _gamma_id_world(asked))
    assert m["status"] == c11.EXCLUSION_KEYS_COMPLETE
    assert "895462" not in asked and {"40", "41"} <= set(asked)
    rep = json.loads((env["tmp"] / "creative_batch11" / "exclusion_report.json").read_text())
    assert rep["sets"]["h7_cb4_series/units.jsonl.gz"] == 2 and rep["run_id"] == "exclusion_run11b"
    assert "895462" not in _read_keys(env["tmp"] / "creative_batch11" / "exclusion_keys.csv.gz")


def test_q0221b_jsonl_readers_yield_market_ids_only(tmp_path):
    gamma_event = {"id": "777", "negRisk": True, "title": "t", "markets": [{"id": "55", "negRisk": True, "conditionId": "0xc", "clobTokenIds": "[\"9\"]"}]}
    weather_event = {"event_id": "888", "markets": [{"market_id": "66", "condition_id": "0xd", "token_yes": "123456789012345678901234567890"}]}
    nested = {"event_id": "1", "markets": [{"market_id": "12"}], "extra": {"market_id": "999", "markets": [{"id": "998"}]}, "series": [{"id": "5"}]}
    for rec, want in ((WALK_REC, {"895462"}), (UNIT_REC, {"40", "41"}), (gamma_event, {"55"}), (weather_event, {"66"}), (nested, {"12"})):
        p = tmp_path / "x.jsonl.gz"
        _gz_jsonl(p, [rec])
        assert c11.read_id_set(p) == want  # no event, series, token or nested id ever leaves
    for bad in ({"markets": [{"market_id": "0x02ee"}]}, {"markets": [{"market_id": "4111367689960253040817739553985299986441"}]}, {"markets": [{"condition_id": "0xa"}]},
                {"markets": {"market_id": "1"}}):
        _gz_jsonl(tmp_path / "bad.jsonl.gz", [bad])
        with pytest.raises(c11.Refused):
            c11.read_id_set(tmp_path / "bad.jsonl.gz")
    (tmp_path / "ids.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id"], [["12"], ["1002717__112005"]]))
    with pytest.raises(c11.Refused, match="not Gamma market ids"):
        c11.read_id_set(tmp_path / "ids.csv.gz")


def test_q0221b_keys_come_from_sources_and_only_missing_ids_are_looked_up(keys_env):
    from astrolabe.research_lab import cb6_tail as c6

    env = keys_env
    hdr = ["market_id", "event_id", "event_ids", "neg_risk_market_id", "series_ids", "question"]
    (env["hist"] / "h8_text").mkdir(parents=True)
    (env["hist"] / "h8_text" / "frame.csv.gz").write_bytes(hb._gz_csv_bytes(hdr, [["60", "e60", "e60", "0xn60", "s1", "q"], ["61", "", "", "", "", "q"]]))
    (env["hist"] / "h8_geo").mkdir(parents=True)
    (env["hist"] / "h8_geo" / "frame.csv.gz").write_bytes(hb._gz_csv_bytes(hdr, [["60", "e60", "e60;e61", "", "s2", "q"]]))
    _gz_jsonl(env["hist"] / "h6_weather" / "events.jsonl.gz", [{"event_id": "e70", "markets": [{"market_id": "70"}]}])
    (env["hist"] / "h7_cb4_era").mkdir(parents=True)
    (env["hist"] / "h7_cb4_era" / "frame.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id", "event_id", "neg_risk"], [["80", "e80", "0"]]))  # partial keys: looked up
    asked: list = []
    m = _ek_tr(env, _gamma_id_world(asked))
    assert m["status"] == c11.EXCLUSION_KEYS_COMPLETE
    assert set(asked) == {"10", "11", "20", "61", "70", "80"}  # 60 carries its keys; 1 and 2 are in the base key file
    keys = _read_keys(env["tmp"] / "creative_batch11" / "exclusion_keys.csv.gz")
    assert set(keys) == {"1", "2", "10", "11", "20", "60", "61", "70", "80"}
    assert (keys["60"]["found"], keys["60"]["event_ids"], keys["60"]["neg_risk_market_id"], keys["60"]["series_ids"]) == ("1", "e60;e61", "0xn60", "s1;s2")
    assert keys["70"]["event_ids"] == "e70" and keys["70"]["series_ids"] == "s70"
    rep = json.loads((env["tmp"] / "creative_batch11" / "exclusion_report.json").read_text())
    assert (rep["n_keys_from_sources"], rep["n_lookup_ids"], rep["n_ids"], rep["n_missing"]) == (1, 6, 2 + 1 + 6, 0)
    assert rep["key_sources"] == {"h8_text/frame.csv.gz": 1, "h8_geo/frame.csv.gz": 1}
    assert c6.load_key_sets(env["tmp"] / "creative_batch11" / "exclusion_keys.csv.gz")["neg_risk_market"] == {"0xn60"}


def test_q0221b_partial_is_compact_gzip_charged_resumable_and_the_old_run_is_untouched(keys_env):
    import gzip

    env = keys_env
    old = env["tmp"] / "creative_batch11" / "exclusion_run11" / "exclusion_keys_partial.jsonl"
    old.parent.mkdir(parents=True)
    old.write_text('{"batch": 0, "found": [], "ids": 50, "retried_found": 0}\n')
    with pytest.raises(c11.Refused):
        c11.refuse_path(old)
    _gz_jsonl(env["hist"] / "h6_weather" / "events.jsonl.gz", [{"event_id": "e", "markets": [{"market_id": str(100 + i)} for i in range(120)]}])
    calls = {"n": 0}

    def stop_after_one():
        calls["n"] += 1
        return calls["n"] > 1

    asked: list = []
    m1 = _ek_tr(env, _gamma_id_world(asked), should_stop=stop_after_one)
    assert m1["status"] == "in_progress"
    rdir = env["tmp"] / "creative_batch11" / "exclusion_run11b"
    part = rdir / c11.EXCLUSION_PARTIAL
    recs = [json.loads(x) for x in gzip.decompress(part.read_bytes()).decode().splitlines()]
    assert len(recs) == 1 and recs[0]["b"] == 0 and recs[0]["n"] == 50 and set(recs[0]) == {"b", "h", "n", "r", "f"}
    part.write_bytes(part.read_bytes() + gzip.compress(b'{"b": 1}\n')[:12])  # a chunk killed mid-append
    m2 = _ek_tr(env, _gamma_id_world(asked))
    assert m2["status"] == c11.EXCLUSION_KEYS_COMPLETE and not part.exists()
    assert len(asked) == len(set(asked)) == 123  # 120 weather + h2/h3 ids; batch 0 was not asked again
    assert old.read_text() == '{"batch": 0, "found": [], "ids": 50, "retried_found": 0}\n' and sorted(p.name for p in old.parent.iterdir()) == ["exclusion_keys_partial.jsonl"]


def test_q0221b_a_changed_id_set_between_chunks_is_refused_and_the_cap_binds(keys_env):
    env = keys_env
    _gz_jsonl(env["hist"] / "h6_weather" / "events.jsonl.gz", [{"event_id": "e", "markets": [{"market_id": str(100 + i)} for i in range(120)]}])
    calls = {"n": 0}

    def stop_after_one():
        calls["n"] += 1
        return calls["n"] > 1

    assert _ek_tr(env, _gamma_id_world([]), should_stop=stop_after_one)["status"] == "in_progress"
    _gz_jsonl(env["hist"] / "h6_weather" / "events.jsonl.gz", [{"event_id": "e", "markets": [{"market_id": str(101 + i)} for i in range(120)]}])  # "100" (in batch 0) left the set
    with pytest.raises(c11.Refused, match="does not match the current id set"):
        _ek_tr(env, _gamma_id_world([]))
    import shutil

    shutil.rmtree(env["tmp"] / "creative_batch11")
    m = _ek_tr(env, _gamma_id_world([]), disk_cap=1500)
    assert m["status"] == "disk_budget"
    assert _ek_tr(env, _gamma_id_world([]), disk_cap=10**7)["status"] == "disk_budget"  # sticky


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

    q21 = _cb11_spec("q0221b_cb11_exclusion_keys.json")["repeat"]
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


# q0220 finished (smoke PASS) and q0221 is parked and superseded by q0221b, both under rules W 2d2bb169 (before the 2026-10-19 q0221b amendment); a finished
# spec is never edited (the worker ignores it and flags it), and q0221's spec stays as it ran.
W_6D3F = "6d3f1613d74431eb53de888e5dec83bac8f8c0eb516348d05a33919bb8582a33"  # part W before the section 11.3 half-open window fix (2026-10-19)
RAN_UNDER_PRIOR_W_RULES = {"q0220_cb11_smoke": "2d2bb1690aa0a5be4446466c0b617b5a31ece07db0d2f5eecf1b5aed1c7b8ae1",
                           "q0221_cb11_exclusion_keys": "2d2bb1690aa0a5be4446466c0b617b5a31ece07db0d2f5eecf1b5aed1c7b8ae1",
                           # finished under 6d3f1613; q0222-q0231 are superseded by the W v2 drafts q0222b-q0231b (section 11.3)
                           **{k: W_6D3F for k in ("q0221b_cb11_exclusion_keys", "q0222_cb11_w_frame", "q0223_cb11_w_prints", "q0224_cb11_w_censoring", "q0230_cb11_seal", "q0231_cb11_census_W")}}
# finished (q0225, q0226) or terminal-failed and superseded (q0227 -> q0227b) under the P/A rules before the q0227b bounded-memory fix
RAN_UNDER_PRIOR_PA_RULES = {k: "2d48bd73e455424b3f6fa16657b92b43461c9a82236fbec0e3a2c2eeb761afec" for k in ("q0225_cb11_pol_frame", "q0226_cb11_pol_prices", "q0227_cb11_attn_frame")}


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
        if f.stem in RAN_UNDER_PRIOR_W_RULES:  # finished or superseded under the prior part-W rules: the spec keeps the sha it ran with
            assert RAN_UNDER_PRIOR_W_RULES[f.stem] in d["notes"] and uses_w, f.name
            continue
        if f.stem in RAN_UNDER_PRIOR_PA_RULES:
            assert RAN_UNDER_PRIOR_PA_RULES[f.stem] in d["notes"] and uses_pa, f.name
            continue
        assert (w_sha in d["notes"]) == uses_w, f.name
        assert (pa_sha in d["notes"]) == uses_pa, f.name
        seen.add((uses_w, uses_pa))
    assert seen == {(True, False), (False, True)}  # b2: no job verifies both parts any more (W and P/A seal in separate jobs)


def test_b2_c1_c2_draft_graph_and_repeats():
    """b2: W seals alone (q0230), P/A seal in q0238; the W census waits on the W seal only, the P/A census on the P/A seal. c1/c2: q0227 and q0229 repeat until completion
    or a terminal stall. The net-lane jobs declare their network."""
    import re

    d = {f.name.split("_")[0]: json.loads(f.read_text()) for f in _cb11_spec_files("q02[23]*_cb11_*.json")}
    assert set(d) == {f"q02{n}" for n in (20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39)} | {"q0221b", "q0227b", "q0222b", "q0223b", "q0224b", "q0230b", "q0231b"}
    deps = {k[1:]: {x.split("_")[0][1:] for x in v["depends_on"]} for k, v in d.items()}
    # q0221b supersedes the parked q0221 (2026-10-19 amendment): every job that needed the exclusion keys waits on q0221b, none on q0221
    assert d["q0221b"]["supersedes"] == "q0221_cb11_exclusion_keys" and deps["0221b"] == {"0220"}
    assert deps["0222"] == deps["0225"] == deps["0227"] == deps["0227b"] == deps["0222b"] == {"0221b"} and not any("0221" in v for v in deps.values())
    assert d["q0221b"]["argv"][d["q0221b"]["argv"].index("--disk-cap-gb") + 1] == "0.01" and d["q0221b"]["resources"]["lane"] == "net"
    # q0227b replaces the terminal-failed q0227 (MemoryError); q0229 waits on q0227b only
    assert deps["0229"] == {"0227b"} and d["q0227b"]["argv"] == d["q0227"]["argv"] and d["q0227b"]["resources"]["mem_mb"] <= 2500
    assert deps["0230"] == {"0223"} and deps["0238"] == {"0226", "0229"}
    assert deps["0231"] == {"0222", "0223", "0224", "0230"} and deps["0239"] == {"0226", "0229", "0238"}
    # W chain v2 (section 11.3 half-open window defect): same graph on the b ids; the W screen waits on the v2 census
    assert deps["0223b"] == deps["0224b"] == {"0222b"} and deps["0230b"] == {"0223b"} and deps["0231b"] == {"0222b", "0223b", "0224b", "0230b"} and deps["0232"] == {"0231b"}
    for k in ("q0222b", "q0223b", "q0224b", "q0230b", "q0231b"):
        assert d[k]["supersedes"] == d[k[:-1]]["id"] and d[k]["argv"] == d[k[:-1]]["argv"] and "11.3" in d[k]["notes"]
        assert not any("/w/" in o or "h11_wprints_b" in o or o.endswith("census_W.json") for o in d[k]["outputs"])
    # the prints stay in the shared history/h11_wprints (the CB12-CB15 id readers' canonical path) under manifest_b.json; the q0223 stall manifest.json is never an output
    assert "history/h11_wprints/manifest_b.json" in d["q0223b"]["outputs"] and not any(o.endswith("h11_wprints/manifest.json") for k in d if k.endswith("b") for o in d[k]["outputs"])
    assert "--family" in d["q0230"]["argv"] and d["q0230"]["argv"][d["q0230"]["argv"].index("--family") + 1] == "W" and "--pa-rules" not in d["q0230"]["argv"]
    assert d["q0238"]["argv"][d["q0238"]["argv"].index("--family") + 1] == "P,A" and "--rules" not in d["q0238"]["argv"]
    for k in ("q0230", "q0238"):
        assert d[k]["resources"]["lane"] == "net" and "gamma-api" in d[k]["resources"]["network"]
        assert re.search(d[k]["repeat"]["until_log_regex"], json.dumps({"status": "seal_all_complete"}))
    for k, st in (("q0227", "attn_frame_complete"), ("q0227b", "attn_frame_complete"), ("q0229", "attn_data_complete")):
        rx = d[k]["repeat"]["until_log_regex"]
        assert re.search(rx, json.dumps({"status": st})) and re.search(rx, json.dumps({"status": c11.STALL_NOT_RUN_SOURCE}))
        assert not re.search(rx, json.dumps({"status": "in_progress"}))
    for k in ("q0236", "q0237"):
        assert "--results-sha256" in d[k]["argv"] and "--stage2-k" in d[k]["argv"]


def test_q0221b_merge_keys_returns_conflicting_neg_risk_ids_for_lookup():
    into = {"1": ("e1", "nrA", "s1"), "2": ("e2", "", "")}
    conf = c11._merge_keys(into, {"1": ("e1;e9", "nrB", "s2"), "2": ("e2", "nrC", ""), "3": ("e3", "nrD", "")})
    assert conf == {"1"}  # an empty value is not a conflict
    assert into["1"] == ("e1;e9", "nrA", "s1;s2") and into["2"] == ("e2", "nrC", "") and into["3"] == ("e3", "nrD", "")
