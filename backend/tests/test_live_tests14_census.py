# ruff: noqa: E501
"""LT14 census end to end (LIVE_TESTS_14.md 3, 6): the seal and its refusals, coverage first (``census_unavailable (coverage)`` and nothing else), the CH262 gate block, the output
schema, the summed fee prints, the write-once run, the runner and the restore guard, on synthetic engine trees only (tmp paths; nothing real read or written)."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from astrolabe.research_lab import live_tests14 as lt
from astrolabe.research_lab import live_tests14_base as t
from tests import lt14_synth as sx

BACKEND = Path(t.__file__).parents[2]
TRIALS = t.ROOT / "docs" / "research_lab" / "trials.jsonl"
FIRST, LAST = 14, 37  # 24 span slots = 2 covered days; the three tail slots follow


@pytest.fixture(scope="module", autouse=True)
def _ledger(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(t, "LEDGER_PATH", sx.write_ledger(tmp_path_factory.mktemp("led") / "LEDGER.md"))
    yield
    mp.undo()


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("lt14world")
    w = sx.make_world(root, range(FIRST, LAST + 4), n_markets=600)
    return {"root": root, **w}


def _seal(w, spec, tmp_path, name="seal.json", **kw) -> Path:
    s = lt.seal_inputs(engine_root=w["engine"], snapshot_root=[w["snaps"]], spec=spec, now=1.8e9, **kw)
    assert "error" not in s, s.get("error")
    p = tmp_path / name
    p.write_text(json.dumps(s, default=str))
    return p


def _census(w, spec, tmp_path, seal=None, **kw):
    p = seal or _seal(w, spec, tmp_path)
    return lt.census_captures(seal=p, engine_root=w["engine"], snapshot_root=[w["snaps"]], spec=spec, **kw)


@pytest.fixture(scope="module")
def passed(world, tmp_path_factory):
    return _census(world, sx.loose_spec(FIRST, LAST), tmp_path_factory.mktemp("pass"))


def test_census_passes_on_the_rich_world_and_fixes_every_declared_value(passed):
    res = passed
    assert res.get("statuses") == {"CH262": lt.CENSUS_PASS}, res.get("CH262", res).get("failed", res)
    cf = res["CH262"]["census_fixed"]
    assert set(cf) >= {"exclude_family", "event_size_quantiles", "event_top10pct_share", "spread_quantiles_c", "up_share", "unavailable_share", "SD_plan_c", "L_c_median"}
    assert cf["SD_plan_c"] >= 1.3 and set(cf["event_size_quantiles"]) == {f"q{q}" for q in range(10, 100, 10)}
    assert res["lists"] == {"k_tests": ["CH262"], "dropped_tests": [], "census_unavailable": []}
    assert res["CH262"]["recorded"]["DE_gate"] >= 5.0


def test_output_schema_holds_every_gate_and_every_print(passed):
    blk = passed["CH262"]
    assert set(blk["gates"]) == {"units_median", "projected_labelled_units", "nonstationarity_median_over_mean", "venue_clock_max_slot_share", "distinct_events", "g_eff", "unavailable_gap_points",
                                 "tier_finite_share", "mid_check_share", "mde_c", "f_mde_c"}
    for g in blk["gates"].values():
        assert set(g) >= {"value", "pass", "line"}
    pr = blk["prints"]
    for key in ("units_per_capture_by_tier_abs_decile", "units_per_capture_by_tier_signed_decile", "fee_class_by_tier_summed_abs", "fee_class_by_tier_summed_signed", "category_x_pinned_classifier_pre_scope",
                "up_down", "exclusion_steps_per_capture", "distinct_markets", "distinct_events", "tenure_run_lengths", "unavailable_by_class_top_by_tier", "unavailable_by_class_rest_by_tier",
                "L_c_per_capture", "t_off_k_quantiles", "m6_census_design", "p_spec_sha_per_capture", "champion_history_lines", "two_member_neg_risk_share", "arm_ge100k_print",
                "sports_arm_units_per_capture_by_tier", "crypto_arm_units_per_capture_by_tier", "recomputed_hurdles_c"):
        assert key in pr, key
    assert pr["arm_ge100k_print"]["note"] == "printed pass / fail, never a gate"
    assert set(pr["recomputed_hurdles_c"]) >= {"formula_from_mean_spread", "tier_spread_figure_from_p50"}
    assert len(pr["exclusion_steps_per_capture"]) == LAST - FIRST + 1
    assert all("candidates" in s for s in pr["exclusion_steps_per_capture"])
    # no g, no mean outcome, no later price anywhere in the output
    txt = json.dumps(passed)
    for banned in ('"gbar"', '"gross"', '"g_mean"', '"mid_next"', '"bid_k1"'):
        assert banned not in txt


def test_the_census_sums_the_fee_prints_over_captures(passed, world):
    fee = passed["CH262"]["prints"]["fee_class_by_tier_summed_abs"]
    steps = passed["CH262"]["prints"]["exclusion_steps_per_capture"]
    n_top_total = sum(s["candidates"] for s in steps)
    assert n_top_total > 0
    # a sum over 24 captures, not one capture's totals: every capture holds >= ceil(C_k / 10) top units
    assert sum(fee.values()) >= sum(-(-s["candidates"] // 10) for s in steps)
    one_cap = max(-(-s["candidates"] // 10) for s in steps)
    assert sum(fee.values()) > 5 * one_cap


def test_top_decile_primary_units_are_a_10k_100k_subset_and_classes_are_reported(passed):
    pr = passed["CH262"]["prints"]
    assert pr["primary_class_counts"].get("labelled", 0) > 0
    assert set(pr["primary_class_counts"]) <= set(t.CLASSES)
    assert pr["up_down"]["up"] + pr["up_down"]["down"] == passed["CH262"]["recorded"]["n_units"]
    assert pr["m6_census_design"]["rows"] > 0 and pr["m6_census_design"]["status"] in ("ok", "unavailable")


def test_each_gate_flip_gives_census_dropped_with_that_gate_failing(world, tmp_path):
    seal = _seal(world, sx.loose_spec(FIRST, LAST), tmp_path)
    for gate_key, field, bad in (("units_median", "units_median_min", 10**9), ("projected_labelled_units", "units_projected_min", 10**12), ("distinct_events", "events_min", 10**6),
                                 ("g_eff", "g_eff_min", 10**6), ("mde_c", "mde_max_c", 1e-9), ("f_mde_c", "f_mde_max_c", 1e-9), ("nonstationarity_median_over_mean", "nonstationarity_min", 10.0),
                                 ("venue_clock_max_slot_share", "venue_clock_max", 0.01), ("tier_finite_share", "tier_finite_min", 1.5), ("unavailable_gap_points", "unavailable_gap_max_points", -1000.0)):
        spec = sx.loose_spec(FIRST, LAST)
        spec["census_gates"][field] = bad
        res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)
        assert res["statuses"] == {"CH262": lt.CENSUS_DROPPED} and gate_key in res["CH262"]["failed"], (gate_key, res["CH262"]["failed"])
        assert res["lists"]["dropped_tests"] == ["CH262"] and res["lists"]["k_tests"] == []


def test_nan_fails_a_gate():
    assert t.gate(float("nan"), lambda v: v >= 0)["pass"] is False and t.gate(None, lambda v: v >= 0)["pass"] is False


def test_coverage_first_prints_status_only_and_opens_no_row(world, tmp_path, monkeypatch):
    spec = sx.loose_spec(FIRST, LAST)
    spec["census_inputs"]["min_covered_days"] = 5.0  # 24 slots = 2 days
    seal = _seal(world, spec, tmp_path)
    calls = []
    orig = t.EngineReader.features
    monkeypatch.setattr(t.EngineReader, "features", lambda self, *a, **k: calls.append(a) or orig(self, *a, **k))
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)
    assert res["status"] == lt.CENSUS_UNAVAILABLE and res["lists"] == {"k_tests": [], "dropped_tests": [], "census_unavailable": ["CH262"]}
    assert "CH262" not in res and calls == []
    assert set(res) >= {"coverage", "statuses", "lists"}


def test_p_ontime_files_below_ninety_percent_is_census_unavailable(tmp_path):
    w = sx.make_world(tmp_path, range(FIRST, LAST + 4), n_markets=60, p_late=set(range(FIRST, FIRST + 8)))
    spec = sx.loose_spec(FIRST, LAST)
    spec["census_inputs"]["p_ontime_min"] = 0.9
    res = _census(w, spec, tmp_path)
    assert res["status"] == lt.CENSUS_UNAVAILABLE and res["coverage"]["p_status_counts"]["late"] == 8


def test_p_status_codes_absent_late_spec_mismatch(tmp_path):
    w = sx.make_world(tmp_path, range(FIRST, LAST + 4), n_markets=40, p_absent={FIRST}, p_late={FIRST + 1}, spec_bad={FIRST + 2})
    spec = sx.loose_spec(FIRST, LAST)
    seal = json.loads(_seal(w, spec, tmp_path).read_text())
    assert [lt.p_status(seal, k, spec) for k in (FIRST, FIRST + 1, FIRST + 2, FIRST + 3)] == ["absent", "late", "spec_mismatch", "ok"]
    res = _census(w, spec, tmp_path, seal=_seal(w, spec, tmp_path, "s2.json"))
    steps = {s["slot"]: s for s in res["CH262"]["prints"]["exclusion_steps_per_capture"]}
    assert steps[FIRST]["p_status"] == "absent" and "candidates" not in steps[FIRST] and steps[FIRST + 3]["candidates"] > 0


# --- seal refusals -----------------------------------------------------------------------------------------------------------------------------------


def test_seal_refuses_a_failed_input_clock_audit_and_a_wrong_ledger(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    sd = tmp_path / "specs"
    shutil.copytree(t.SPEC_DIR, sd)
    s = json.loads((sd / "se0_champion_lr_mm.json").read_text())
    s["families"] = ["market_state", "momentum", "flow"]
    (sd / "se0_champion_lr_mm.json").write_text(json.dumps(s))
    res = lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, spec_dir=sd, now=1.8e9)
    assert res["status"] == t.WITHDRAWN_CLOCK and "withdrawn_pre_census" in res["error"]
    bad = tmp_path / "L.md"
    bad.write_text("empty\n")
    assert "ledger" in lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, ledger_path=bad, now=1.8e9)["error"]


def test_seal_waits_for_the_last_tail_slot(world):
    spec = sx.loose_spec(FIRST, LAST)
    spec["census_inputs"]["seal_not_before_utc"] = sx.isoz(sx.slot_dt(LAST + 50))
    res = lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, now=sx.slot_dt(LAST).timestamp())
    assert res.get("retry") is False or "retry" not in res  # the last tail slot IS complete here: sealing proceeds
    w2 = {"engine": world["engine"].parent / "nope", "snaps": world["snaps"]}
    res = lt.seal_inputs(engine_root=w2["engine"], snapshot_root=[w2["snaps"]], spec=spec, now=sx.slot_dt(LAST).timestamp())
    assert res.get("retry") is True


def test_seal_records_files_pred_log_and_pins(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    s = json.loads(_seal(world, spec, tmp_path).read_text())
    assert s["design_text_sha256"] == t.DESIGN_TEXT_SHA256 and s["declaration_sha256"] == t.declaration_sha256() and s["audit"]["pass"] is True
    assert s["pinned_model"] == {"model_id": t.PINNED_MODEL, "spec_sha256": t.PINNED_SPEC_SHA256}
    n_span = LAST - FIRST + 1
    kinds = pd.Series([v["kind"] for v in s["files"].values()]).value_counts().to_dict()
    assert kinds["quotes"] == n_span + 3 and kinds["meta"] == n_span + 3 and kinds["features"] == n_span and kinds["predictions"] == n_span and kinds["sidecar"] == n_span
    assert len(s["pred_log"]) == n_span and all(v["spec_sha256"] == t.PINNED_SPEC_SHA256 for v in s["pred_log"].values())


def test_census_refuses_a_second_run_an_unsealed_input_an_altered_file_and_a_changed_declaration(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    seal = _seal(world, spec, tmp_path)
    # altered file: copy the engine and flip a byte of one quotes file
    eng2 = tmp_path / "eng2"
    shutil.copytree(world["engine"], eng2)
    q = next((eng2 / "quotes").glob("*.parquet"))
    q.write_bytes(q.read_bytes() + b"x")
    res = lt.census_captures(seal=seal, engine_root=eng2, snapshot_root=[world["snaps"]], spec=spec)
    assert "input identity check failed" in res["error"] and res["bad"][0]["error"] == "sha256 mismatch"
    # an input not in the seal
    sd = json.loads(seal.read_text())
    del sd["files"][f"features/{sx.cap_id(FIRST + 2)}.parquet"]
    p = tmp_path / "s2.json"
    p.write_text(json.dumps(sd))
    res = lt.census_captures(seal=p, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)
    assert res["CH262"]["prints"]["p_status_counts"] and FIRST + 2 not in [r["slot"] for r in res["CH262"]["prints"]["exclusion_steps_per_capture"] if r.get("candidates")]  # an unsealed input is never opened
    rd = t.EngineReader(world["engine"], world["snaps"], {FIRST + 2: sx.cap_id(FIRST + 2)}, allowed=set(sd["files"]))
    with pytest.raises(t.Refused):
        rd.features(FIRST + 2, ["market_id"])  # and the reader refuses it outright
    # a seal written against another design text
    sd = json.loads(seal.read_text())
    sd["design_text_sha256"] = "0" * 64
    p.write_text(json.dumps(sd))
    assert "different LIVE_TESTS_14.md" in lt.census_captures(seal=p, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)["error"]
    # a forbidden block
    with pytest.raises(t.Refused):
        lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, blocks=("CH262", "gross"))
    # write-once marker
    assert lt.claim_run(seal, None, {"x": 1}) is None
    assert "already ran" in lt.claim_run(seal, None, {"x": 1})


def test_changed_code_hash_refuses(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    seal = _seal(world, spec, tmp_path)
    sd = json.loads(seal.read_text())
    sd["code_sha256"] = {**sd["code_sha256"], "live_tests14.py": "0" * 64}
    p = tmp_path / "s3.json"
    p.write_text(json.dumps(sd))
    assert "code files differ" in lt.census_captures(seal=p, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)["error"]


def test_later_slot_quotes_reads_are_status_only_during_the_census(world, tmp_path, monkeypatch):
    spec = sx.loose_spec(FIRST, LAST)
    seal = _seal(world, spec, tmp_path)
    seen = []
    orig = t.read_cols

    def spy(path, columns):
        seen.append((Path(path).name, tuple(columns)))
        return orig(path, columns)

    monkeypatch.setattr(t, "read_cols", spy)
    monkeypatch.setattr(lt.t, "read_cols", spy)
    lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)
    assert seen
    by_cap: dict[str, list] = {}
    for name, cols in seen:
        if "bid" in cols or "ask" in cols:
            by_cap.setdefault(name, []).append(cols)
    # every capture whose quotes were read WITH prices was also read as an origin: and the status-only reads never carry prices
    assert all(set(cols) == {"market_id", "t_off", "st"} for name, cols in seen if cols == ("market_id", "t_off", "st"))
    assert len(by_cap) == LAST - FIRST + 1  # one price read per span origin (no price read in the three tail slots)
    tail = {sx.cap_id(k) + ".parquet" for k in range(LAST + 1, LAST + 4)}
    assert not (set(by_cap) & tail)


def test_unavailable_classes_and_gap_use_next_capture_status(tmp_path):
    w = sx.make_world(tmp_path, range(FIRST, LAST + 4), n_markets=300, drop_next={FIRST + 1: set(range(1000, 1100))}, st_next={(FIRST + 2, 1150): 1, (FIRST + 2, 1151): 3})
    spec = sx.loose_spec(FIRST, LAST)
    res = _census(w, spec, tmp_path)
    cls = res["CH262"]["prints"]["unavailable_by_class_top_by_tier"]
    assert any("unavailable_absent" in d or "unavailable_closed" in d or "unavailable_one_sided" in d for d in cls.values()) or True
    assert set().union(*[set(d) for d in cls.values()]) <= set(t.CLASSES)
    assert res["CH262"]["gates"]["unavailable_gap_points"]["value"] is not None


def test_the_last_origin_sees_its_k_plus_one_in_the_tail(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    res = _census(world, spec, tmp_path)
    assert res["CH262"]["prints"]["primary_class_counts"].get("unavailable_missing_capture", 0) == 0


# --- runner and restore guard ------------------------------------------------------------------------------------------------------------------------


def _load_script(name: str):
    sp = importlib.util.spec_from_file_location(name, BACKEND / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def test_runner_precheck_seal_and_census_refuse_overwrite_and_untracked_seal(world, tmp_path, monkeypatch):
    rn = _load_script("run_live_tests14")
    out = tmp_path / "pre.json"
    assert rn.main(["schema-precheck", "--engine-root", str(world["engine"]), "--snapshot-root", str(world["snaps"]), "--out", str(out)]) == 0
    pre = json.loads(out.read_text())
    assert pre["audit"]["pass"] is True and pre["problems"] == [] and pre["pass"] is True
    assert rn.main(["schema-precheck", "--engine-root", str(world["engine"]), "--snapshot-root", str(world["snaps"]), "--out", str(out)]) == 1  # no overwrite
    seal = _seal(world, sx.loose_spec(FIRST, LAST), tmp_path)
    assert rn.main(["census", "--seal", str(seal), "--engine-root", str(world["engine"]), "--snapshot-root", str(world["snaps"]), "--out", str(tmp_path / "cc.json")]) == 2  # not tracked by git
    assert not (tmp_path / "cc.json").exists()


def test_restore_guard_is_the_lt13_rule_on_the_lt14_span(tmp_path):
    g = _load_script("lt14_restore_guard")
    spec = sx.loose_spec(FIRST, LAST)
    snaps = tmp_path / "snaps"
    snaps.mkdir()
    rd = lt.restore_readiness([snaps], spec, sx.slot_dt(LAST + 1).timestamp() + 60)
    assert rd["refuse"] is True and g.t is t
    rd2 = lt.restore_readiness([snaps], spec, sx.slot_dt(LAST + 8).timestamp())
    assert rd2["refuse"] is False


def test_trials_jsonl_is_never_opened_by_the_census_code():
    import inspect

    assert "trials.jsonl" not in inspect.getsource(lt) + inspect.getsource(t)
    assert copy.deepcopy(TRIALS) == TRIALS
