# ruff: noqa: E501
"""CB15 runner and queue-draft tests (docs/research_lab/CREATIVE_BATCH_15.md section 4): offline; no network; no real CB15 quantity."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb15_common as c15
from astrolabe.research_lab import cb15_e as e

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))
import run_cb15  # noqa: E402
import test_cb15_e as te  # noqa: E402

DRAFTS = ROOT / "docs" / "research_lab" / "queue" / "drafts"
JOBS = ROOT / "docs" / "research_lab" / "queue" / "jobs"
RULES = ROOT / "docs" / "research_lab" / "seals" / "cb15_rules.json"
E_IDS = [340, 341, 343, 344, 345, 346]


def _run(capsys, argv: list[str]) -> tuple[int, dict]:
    code = run_cb15.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


@pytest.fixture()
def env(tmp_path):
    rules = tmp_path / "rules.json"
    c15.write_rules(rules)
    root = tmp_path / "data" / "research_lab" / "creative_batch15"
    hist = tmp_path / "data" / "research_lab" / "history"
    root.mkdir(parents=True)
    hist.mkdir(parents=True)
    base = ["--rules", str(rules), "--allow-uncommitted-rules", "--root", str(root), "--history-root", str(hist), "--trials-path", str(tmp_path / "trials.jsonl"), "--standalone"]
    return {"tmp": tmp_path, "rules": rules, "root": root, "hist": hist, "base": base, "trials": tmp_path / "trials.jsonl"}


def _trials(env) -> list[dict]:
    p = env["trials"]
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def _freeze_spec(env, entry: dict) -> Path:
    p = env["tmp"] / "cb15_v1.json"
    p.write_text(json.dumps({"E": entry}))
    return p


def _e_entry(env, rm: Path, ge0: dict | None = None, cap: float = 1.5) -> dict:
    doc = json.loads(env["rules"].read_text())["parts"]
    entry = {"rules_sha256": doc["E"]["rules_sha256"], "common_rules_sha256": doc["common"]["rules_sha256"], "race_map_sha256": c15.sha256_file(rm), "disk_cap_gb": cap}
    if ge0 is not None:
        entry.update({f"{k}_sha256": v for k, v in ge0["sha256"].items()})
    else:
        entry.update({f"{k}_sha256": "x" for k in e.GE0_FILES})
    entry["source_manifest_sha256"] = entry.get("source_manifest_sha256", "x")
    return entry


# ---- rules and freeze --------------------------------------------------------------------------------------------------------------------------------


def test_rules_writes_common_and_e_declared_p_pending(tmp_path, capsys):
    p = tmp_path / "r.json"
    code = run_cb15.main(["rules", "--path", str(p)])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["parts"]["common"]["declared"] and out["parts"]["E"]["declared"]
    doc = json.loads(p.read_text())
    assert set(doc["parts"]) == {"common", "E", "P"}
    assert c15.verify_rules(p, require_committed=False, part="E") == doc["parts"]["E"]["rules_sha256"]
    assert run_cb15.main(["rules", "--path", str(p)]) == 0  # idempotent


def test_committed_rules_file_matches_the_code_for_declared_parts():
    doc = json.loads(RULES.read_text())
    for part, d in doc["parts"].items():
        if d.get("part_declared") is not False:
            assert c15.verify_rules(RULES, require_committed=False, part=part)


def test_freeze_part_e_pins_ge0_race_map_and_cap(env, capsys):
    gdir = te.write_ge0(env["tmp"] / "ge0", {"OH": 1})
    g = e.load_ge0(gdir=gdir, require_committed=False, require_pin=False)
    rm = te._write_map(env["hist"] / "rm.csv", [te._race("OH", 1, te.CLOSES[0])])
    code, out = _run(capsys, ["freeze-part", "--part", "E", *env["base"], "--ge0-dir", str(gdir), "--ge0-sha256", g["bundle_sha256"], "--race-map", str(rm), "--disk-cap-gb", "1.5"])
    assert code == 0, out
    ent = out["entry"]
    assert set(c15.E_FREEZE_PINS) <= set(ent) and ent["ge0_bundle_sha256"] == g["bundle_sha256"] and ent["disk_cap_gb"] == 1.5
    code, out = _run(capsys, ["freeze-part", "--part", "E", *env["base"], "--ge0-dir", str(gdir), "--ge0-sha256", c15.PIN_UNSET, "--race-map", str(rm), "--disk-cap-gb", "1.5"])
    assert code == 2 and "unset" in out["refused"]
    code, out = _run(capsys, ["freeze-part", "--part", "E", *env["base"], "--ge0-dir", str(gdir), "--ge0-sha256", g["bundle_sha256"], "--race-map", str(rm), "--disk-cap-gb", "0.5"])
    assert code == 2


# ---- declared arguments and hooks --------------------------------------------------------------------------------------------------------------------


def test_declared_arguments_refused(env, capsys):
    code, out = _run(capsys, ["e-census", *env["base"], "--disk-cap-gb", "0.01"])
    assert code == 2 and "disk_cap_gb" in out["refused"]
    code, out = _run(capsys, ["e-census", *env["base"], "--rps", "3"])
    assert code == 2 and "rps" in out["refused"]
    code, out = _run(capsys, ["e-census", *env["base"], "--data-dumps-cap-gb", "41"])
    assert code == 2


def test_test_hooks_need_the_test_flag(env, capsys):
    base = [x for x in env["base"] if x != "--allow-uncommitted-rules"]
    code, out = _run(capsys, ["screen", "--family", "E", *base, "--draws", "9"])
    assert code == 2 and "test hook" in out["refused"]


def test_pregate_needs_the_smoke(env, capsys):
    code, out = _run(capsys, ["pregate", "--family", "E", *env["base"], "--ge0-sha256", c15.PIN_UNSET])
    assert code == 2 and "smoke" in out["refused"]


def test_smoke_is_write_once(env, capsys):
    (env["root"] / "smoke_E.json").write_text("{}")
    code, out = _run(capsys, ["smoke", "--part", "E", *env["base"], "--rps", "1"])
    assert code == 2 and "write-once" in out["refused"]


# ---- collector ----------------------------------------------------------------------------------------------------------------------------------


def _live_args(env, rm, spec, *extra):
    return ["e-live", *env["base"], "--race-map", str(rm), "--freeze-spec", str(spec), "--not-before", e.T15_E_PRE, "--until", e.T15_E_END, "--no-exit75-in-window", *extra]


def test_e_live_refusals_and_idle(env, capsys):
    rm = te._write_map(env["hist"] / "rm.csv", [te._race("OH", 1, te.CLOSES[0])])
    code, out = _run(capsys, _live_args(env, rm, env["tmp"] / "missing.json", "--now", str(e.ep(e.T15_E_PRE) - 600)))
    assert code == 2 and "freeze" in out["refused"]
    spec = _freeze_spec(env, _e_entry(env, rm))
    code, out = _run(capsys, _live_args(env, rm, spec, "--now", str(e.ep(e.T15_E_PRE) - 600), "--data-dumps", str(env["tmp"] / "data")))
    assert code == 0 and out["status"] == "e_live_idle", out
    code, out = _run(capsys, _live_args(env, rm, spec, "--now", str(e.ep(e.T15_E_PRE) - 600), "--disk-cap-gb", "2.0"))
    assert code == 2 and "frozen collector cap" in out["refused"]
    args = [x for x in _live_args(env, rm, spec, "--now", "1") if x != "--no-exit75-in-window"]
    code, out = _run(capsys, args)
    assert code == 2 and "no-exit75" in out["refused"]
    args = _live_args(env, rm, spec, "--now", "1")
    args[args.index("--until") + 1] = "2026-11-07T00:00:00Z"
    code, out = _run(capsys, args)
    assert code == 2
    other = te._write_map(env["hist"] / "rm2.csv", [te._race("PA", -1, te.CLOSES[0])])
    code, out = _run(capsys, _live_args(env, other, spec, "--now", "1"))
    assert code == 2 and "race_map_sha256" in out["refused"]  # the freeze pins the race map


def test_e_live_after_end_is_closed(env, capsys):
    rm = te._write_map(env["hist"] / "rm.csv", [te._race("OH", 1, te.CLOSES[0])])
    spec = _freeze_spec(env, _e_entry(env, rm))
    code, out = _run(capsys, _live_args(env, rm, spec, "--now", str(e.ep(e.T15_E_END) + 60)))
    assert code == 0 and out["status"] == e.LIVE_STATUS_CLOSED


def test_e_cron_prints_the_block(capsys):
    code, out = _run(capsys, ["e-cron"])
    assert code == 0 and any("hold-lane" in x for x in out["lines"])
    assert (ROOT / e.CRON_FILE_REL).read_text() == e.cron_text()  # the committed crontab block equals the code's


# ---- screen ----------------------------------------------------------------------------------------------------------------------------------------


def test_screen_before_end_is_pending(env, capsys):
    code, out = _run(capsys, ["screen", "--family", "E", *env["base"], "--now", str(e.ep(e.T15_E_END) - 1)])
    assert code == 75 and "tempfail" in out


def test_screen_calendar_missed_is_counted_once(env, capsys):
    late = e.ep(e.T15_E_FREEZE) + 3600
    code, out = _run(capsys, ["screen", "--family", "E", *env["base"], "--now", str(e.ep(e.T15_E_END) + 1), "--freeze-ts", str(late)])
    assert code == 0 and out["terminal"] and out["E1"]["verdict"] == e.NOT_RUN_CALENDAR
    lines = _trials(env)
    count = [x for x in lines if x.get("kind") == "ml_explain"]
    assert len(count) == 1 and count[0]["n_tests"] == 2 and count[0]["source"] == "creative_batch_15:E"
    assert all(x["p"] == 1.0 for x in lines if x.get("kind") == "cb15_test")
    code, out = _run(capsys, ["screen", "--family", "E", *env["base"], "--now", str(e.ep(e.T15_E_END) + 1), "--freeze-ts", str(late)])
    assert code == 2  # results are written once
    assert len([x for x in _trials(env) if x.get("kind") == "ml_explain"]) == 1


def test_screen_runs_against_the_freeze_and_counts_two_tests(env, capsys):
    live, rm = te._setup_screen(env["hist"].parent)
    gdir = te.write_ge0(env["tmp"] / "ge0", {"OH": 1})
    g = e.load_ge0(gdir=gdir, require_committed=False, require_pin=False)
    spec = _freeze_spec(env, _e_entry(env, rm, g))
    argv = ["screen", "--family", "E", *env["base"], "--now", str(e.ep(e.T15_E_END) + 1), "--freeze-ts", str(e.ep(e.T15_E_FREEZE) - 60), "--freeze-spec", str(spec),
            "--ge0-dir", str(gdir), "--ge0-sha256", g["bundle_sha256"], "--draws", "199"]
    code, out = _run(capsys, argv)
    assert code == 0, out
    assert out["E1"]["advance"] and out["E2"]["advance"]
    res = json.loads((env["root"] / "results_E.json").read_text())
    assert res["stage1_holm"]["k"] == 4 and res["race_map_sha256"] == c15.sha256_file(rm) and res["books"]["n_files"] > 0
    count = [x for x in _trials(env) if x.get("kind") == "ml_explain"]
    assert len(count) == 1 and count[0]["n_tests"] == 2
    per = [x for x in _trials(env) if x.get("kind") == "cb15_test"]
    assert {x["hypothesis"] for x in per} == {"E1", "E2"} and all(x["evidence_role"] == "prospective" for x in per)


def test_screen_refuses_a_freeze_that_pins_other_ge0(env, capsys):
    live, rm = te._setup_screen(env["hist"].parent)
    gdir = te.write_ge0(env["tmp"] / "ge0", {"OH": 1})
    g = e.load_ge0(gdir=gdir, require_committed=False, require_pin=False)
    spec = _freeze_spec(env, _e_entry(env, rm, None))
    argv = ["screen", "--family", "E", *env["base"], "--now", str(e.ep(e.T15_E_END) + 1), "--freeze-ts", str(e.ep(e.T15_E_FREEZE) - 60), "--freeze-spec", str(spec),
            "--ge0-dir", str(gdir), "--ge0-sha256", g["bundle_sha256"], "--draws", "9"]
    code, out = _run(capsys, argv)
    assert code == 2 and "pins" in out["refused"]


def test_terminal_family_short_circuits_downstream(env, capsys):
    c15.record_terminal(env["root"], "E", e.NOT_RUN_IDENT, "test", trials_path=env["trials"])
    code, out = _run(capsys, ["e-census", *env["base"]])
    assert code == 0 and out["status"] == c15.TERMINAL_STATUS
    again = c15.record_terminal(env["root"], "E", e.NOT_RUN_POWER, "test", trials_path=env["trials"])
    assert not again["newly_counted"] and again["label"] == e.NOT_RUN_IDENT
    assert len([x for x in _trials(env) if x.get("kind") == "ml_explain"]) == 1


# ---- drafts --------------------------------------------------------------------------------------------------------------------------------------


def _drafts(ids) -> list[dict]:
    """Each id exists exactly once, as a draft or (after a coordinator promotion) as a job."""
    out = []
    for n in ids:
        fs = sorted(DRAFTS.glob(f"q{n:04d}_cb15_*.json")) + sorted(JOBS.glob(f"q{n:04d}_cb15_*.json"))
        assert len(fs) == 1, n
        d = json.loads(fs[0].read_text())
        d["_promoted"] = fs[0].parent == JOBS
        out.append(d)
    return out


def test_e_drafts_exist_parse_and_are_drafts_not_jobs():
    ds = _drafts(E_IDS)
    assert all("PROMOTED" in d["notes"] for d in ds if d["_promoted"])
    ap = run_cb15.build_parser()
    rules = json.loads(RULES.read_text())["parts"]
    for d in ds:
        assert d["family"] == "creative_batch_15" and ("DRAFT" in d["notes"] or d["id"].startswith("q0348")) and d["argv"][0] == "scripts/run_cb15.py"
        a = ap.parse_args(d["argv"][1:])
        assert callable(a.fn)
        if d["resources"]["lane"] == "net" and a.cmd != "smoke":
            assert d["argv"][d["argv"].index("--data-dumps-cap-gb") + 1] == "40"
        if a.cmd in run_cb15.DECLARED_DISK_CAP_GB or f"{a.cmd}-E" in run_cb15.DECLARED_DISK_CAP_GB:
            key = a.cmd if a.cmd in run_cb15.DECLARED_DISK_CAP_GB else f"{a.cmd}-E"
            assert abs(a.disk_cap_gb - run_cb15.DECLARED_DISK_CAP_GB[key]) < 1e-9, d["id"]
        assert getattr(a, "rps", 0.0) <= run_cb15.DECLARED_RPS_MAX.get(a.cmd, run_cb15.DECLARED_RPS_MAX.get(f"{a.cmd}-E", 99.0)) + 1e-9
        if d["_promoted"]:
            continue  # a promoted job keeps the shas it ran under (jobs/ is the coordinator's)
        assert rules["common"]["rules_sha256"] in d["notes"], d["id"]
        if d["id"] != "q0340_cb15_exclusion_keys":
            assert rules["E"]["rules_sha256"] in d["notes"], d["id"]
    pr = {d["id"][:5]: d["priority"] for d in ds}
    assert pr["q0341"] == pr["q0343"] == pr["q0344"] == 99 and pr["q0340"] == 9
    by = {d["id"][:5]: d for d in ds}
    hex64 = re.compile(r"^[0-9a-f]{64}$")  # q0344 / q0346 carry the pinned GE0 bundle sha256 (ba0ce3b); q0340's base-key pin may still be a placeholder or a pinned value
    for k in ("q0344", "q0346"):
        pin = by[k]["argv"][by[k]["argv"].index("--ge0-sha256") + 1]
        assert hex64.match(pin) and pin != c15.PIN_UNSET, k
    pin40 = by["q0340"]["argv"][by["q0340"]["argv"].index("--base-sha256") + 1]
    assert pin40 == c15.PIN_UNSET or hex64.match(pin40)  # promoted 2026-10-21 with the pinned base-key sha
    live = by["q0345"]
    assert live["resources"]["lane"] == "cron" and "--no-exit75-in-window" in live["argv"] and live["argv"][live["argv"].index("--disk-cap-gb") + 1] == "freeze"
    assert by["q0346"]["not_before"] == e.T15_E_END


# ---- part P ----------------------------------------------------------------------------------------------------------------------------------------


P_IDS = [347, 348, 349, 350, 351, 352, 353, 354]


def test_p_birth_census_waits_for_exclusion_keys(env, capsys):
    code, out = _run(capsys, ["p-birth-census", *env["base"]])
    assert code == 75 and "exclusion keys" in out["tempfail"]


def test_p_data_declared_arguments(env, capsys):
    code, out = _run(capsys, ["p-data", *env["base"], "--kalshi-rps", "2"])
    assert code == 2 and "kalshi_rps" in out["refused"]
    code, out = _run(capsys, ["p-data", *env["base"], "--disk-cap-gb", "0.1"])
    assert code == 2 and "disk_cap_gb" in out["refused"]


def test_p_live_refuses_before_the_p_freeze_and_idles_after(env, capsys):
    args = ["p-live", *env["base"], "--not-before", "2026-11-04T00:00:00Z", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--now", str(e.ep("2026-11-04T00:00:00Z") - 60)]
    code, out = _run(capsys, [*args, "--freeze-spec", str(env["tmp"] / "none.json")])
    assert code == 2 and "freeze" in out["refused"]
    from astrolabe.research_lab import cb15_p as p

    doc = json.loads(env["rules"].read_text())["parts"]
    spec = env["tmp"] / "spec.json"
    spec.write_text(json.dumps({"P": {"rules_sha256": doc["P"]["rules_sha256"], "common_rules_sha256": doc["common"]["rules_sha256"], "matcher_sha256": p.verify_matcher(),
                                      "p_freeze_marker": p.P_FREEZE_MARKER}}))
    code, out = _run(capsys, [*args, "--freeze-spec", str(spec), "--freeze-ts", str(e.ep("2026-11-02T00:00:00Z")), "--data-dumps", str(env["tmp"] / "data")])
    assert code == 0 and out["status"] == "p_live_idle", out
    stamp = env["hist"] / p.LIVE_RUN / "disk_check.json"
    assert stamp.is_file()  # the disk guard ran once; a minute later it is not run again (P-12)
    t0 = json.loads(stamp.read_text())["epoch"]
    code, out = _run(capsys, [*args, "--freeze-spec", str(spec), "--freeze-ts", str(e.ep("2026-11-02T00:00:00Z")), "--data-dumps", str(env["tmp"] / "data"), "--now", str(t0 + 60)])
    assert code == 0 and json.loads(stamp.read_text())["epoch"] == t0
    code, out = _run(capsys, ["p-cache", *env["base"], "--kalshi-rps", "2"])
    assert code == 2 and "kalshi_rps" in out["refused"]
    cargs = ["p-cache", *env["base"], "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--freeze-spec", str(spec), "--freeze-ts", str(e.ep("2026-11-02T00:00:00Z")), "--data-dumps", str(env["tmp"] / "data")]
    code, out = _run(capsys, [*cargs, "--now", str(e.ep("2026-11-01T00:00:00Z"))])
    assert code == 0 and out["status"] == "p_cache_idle", out  # more than a day before T15_P2_start
    bad = [*args, "--freeze-spec", str(spec)]
    bad[bad.index("--not-before") + 1] = "2026-11-05T00:00:00Z"
    code, out = _run(capsys, bad)
    assert code == 2


def test_rep_requires_the_results_pin(env, capsys):
    from astrolabe.research_lab import cb15_p as p

    doc = json.loads(env["rules"].read_text())["parts"]
    spec = env["tmp"] / "spec.json"
    spec.write_text(json.dumps({"P": {"rules_sha256": doc["P"]["rules_sha256"], "common_rules_sha256": doc["common"]["rules_sha256"], "matcher_sha256": p.verify_matcher(),
                                      "p_freeze_marker": p.P_FREEZE_MARKER}}))
    (env["root"] / "results_P.json").write_text(json.dumps({"P1": {"advance": False}, "P2": {"advance": False}}))
    code, out = _run(capsys, ["rep", "--family", "P", *env["base"], "--freeze-spec", str(spec), "--results-sha256", c15.PIN_UNSET])
    assert code == 2 and "results-sha256" in out["refused"]
    code, out = _run(capsys, ["rep", "--family", "P", *env["base"], "--freeze-spec", str(spec), "--results-sha256", c15.sha256_file(env["root"] / "results_P.json")])
    assert code == 0 and out["status"] == "rep_P_not_triggered"
    assert not [x for x in _trials(env) if x.get("kind") == "ml_explain"]


def test_p_drafts_exist_parse_and_carry_the_p_sha():
    ds = _drafts(P_IDS)
    ap = run_cb15.build_parser()
    rules = json.loads(RULES.read_text())["parts"]
    assert rules["P"]["part_declared"] is not False
    for d in ds:
        assert d["family"] == "creative_batch_15" and ("DRAFT" in d["notes"] or d["id"].startswith("q0348")) and d["argv"][0] == "scripts/run_cb15.py"
        a = ap.parse_args(d["argv"][1:])
        assert callable(a.fn)
        assert rules["common"]["rules_sha256"] in d["notes"] and rules["P"]["rules_sha256"] in d["notes"], d["id"]
        if d["resources"]["lane"] in ("net", "cron") and a.cmd not in ("smoke",):
            assert d["argv"][d["argv"].index("--data-dumps-cap-gb") + 1] == "40", d["id"]
        if a.cmd in run_cb15.DECLARED_DISK_CAP_GB:
            assert abs(a.disk_cap_gb - run_cb15.DECLARED_DISK_CAP_GB[a.cmd]) < 1e-9
        assert getattr(a, "rps", 0.0) <= run_cb15.DECLARED_RPS_MAX.get(a.cmd, 99.0) + 1e-9
        assert 5 <= d["priority"] <= 9 or d["resources"]["lane"] == "cron" or a.cmd == "smoke"  # the smoke is promoted to queue/jobs with its own (higher) priority
    by = {d["id"][:5]: d for d in ds}
    assert by["q0352"]["not_before"] == "2026-11-04T00:00:00Z" and c15.PIN_UNSET in by["q0353"]["argv"]


# ---- round-2 runner fixes ------------------------------------------------------------------------------------------------------------------------------


def test_smoke_honours_an_existing_terminal_record(env, capsys):
    c15.record_terminal(env["root"], "E", e.NOT_TESTABLE_FRAME, "test", trials_path=env["trials"])
    code, out = _run(capsys, ["smoke", "--part", "E", *env["base"], "--rps", "1"])
    assert code == 0 and out["status"] == c15.TERMINAL_STATUS and not (env["root"] / "smoke_E.json").exists()


def test_watchdog_alerts_on_a_stale_heartbeat_and_a_heavy_job(env, capsys, tmp_path):
    live = env["hist"] / e.RUN
    live.mkdir(parents=True)
    now = e.ep("2026-11-03T21:30:00Z")
    (live / "heartbeat.json").write_text(json.dumps({"epoch": now - 600}))
    q = tmp_path / "q"
    j = tmp_path / "jobs"
    q.mkdir()
    j.mkdir()
    (q / "status.json").write_text(json.dumps({"jobs": [{"id": "qX", "status": "running"}]}))
    (j / "qX.json").write_text(json.dumps({"resources": {"lane": "cpu", "mem_mb": 600}}))
    code, out = _run(capsys, ["e-watchdog", "--history-root", str(env["hist"]), "--queue-root", str(q), "--jobs-dir", str(j), "--now", str(now), "--dry-run"])
    assert code == 0 and len(out["alerts"]) == 2
    (live / "heartbeat.json").write_text(json.dumps({"epoch": now - 30}))
    (j / "qX.json").write_text(json.dumps({"resources": {"lane": "cpu", "mem_mb": 400}}))
    code, out = _run(capsys, ["e-watchdog", "--history-root", str(env["hist"]), "--queue-root", str(q), "--jobs-dir", str(j), "--now", str(now), "--dry-run"])
    assert out["alerts"] == []


def test_e_live_refusal_leaves_a_record_and_no_heartbeat(env, capsys):
    rm = te._write_map(env["hist"] / "rm.csv", [te._race("OH", 1, te.CLOSES[0])])
    code, _ = _run(capsys, _live_args(env, rm, env["tmp"] / "missing.json", "--now", "1"))
    assert code == 2 and (env["hist"] / e.RUN / "last_refusal.json").is_file() and not (env["hist"] / e.RUN / "heartbeat.json").exists()
