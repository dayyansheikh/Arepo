# ruff: noqa: E501
"""LT14 census end to end (LIVE_TESTS_14.md 3, 6): the seal and its refusals, coverage first (``census_unavailable (coverage)`` and nothing else), the CH262 gate block, the output
schema, the summed fee prints, the write-once run, the runner and the restore guard, on synthetic engine trees only (tmp paths; nothing real read or written)."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests14 as lt
from astrolabe.research_lab import live_tests14_base as t
from tests import lt14_synth as sx

BACKEND = Path(t.__file__).parents[2]
TRIALS = t.ROOT / "docs" / "research_lab" / "trials.jsonl"
TRIALS_STAT0 = (os.stat(TRIALS).st_size, os.stat(TRIALS).st_mtime_ns) if TRIALS.exists() else None  # stat only: this module never reads the file's bytes
DRAFTS = t.ROOT / "docs" / "research_lab" / "queue" / "drafts"
FIRST, LAST = 14, 37  # 24 span slots = 2 covered days; the three tail slots follow


@pytest.fixture(scope="module", autouse=True)
def _ledger(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(t, "LEDGER_PATH", sx.write_ledger(tmp_path_factory.mktemp("led") / "LEDGER.md"))
    mp.setattr(t, "ALLOW_NONDECLARED_SPEC", True)  # the synthetic worlds run on loose specs; one test below switches it off
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
                                 ("venue_clock_max_slot_share", "venue_clock_max", 0.01), ("tier_finite_share", "tier_finite_min", 1.5), ("unavailable_gap_points", "unavailable_gap_max_points", -1000.0),
                                 ("mid_check_share", "mid_check_share_min", 1.5)):
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
    assert "error" not in res and "retry" not in res and res["n_files"] > 0  # the last tail slot's meta IS present here: sealing proceeds before seal_not_before
    w2 = {"engine": world["engine"].parent / "nope", "snaps": world["snaps"]}
    res = lt.seal_inputs(engine_root=w2["engine"], snapshot_root=[w2["snaps"]], spec=spec, now=sx.slot_dt(LAST).timestamp())
    assert res.get("retry") is True and "waits for the" in res["error"]


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
    # an input not in the seal, read by the CENSUS (not only by the reader): the tail slot's quotes file is a census input (k + 1 of the last origin) but not a coverage input
    sd = json.loads(seal.read_text())
    tail_q = f"quotes/{sx.cap_id(LAST + 1)}.parquet"
    assert tail_q in sd["files"]
    del sd["files"][tail_q]
    p = tmp_path / "s2.json"
    p.write_text(json.dumps(sd))
    with pytest.raises(t.Refused, match="not in the seal"):
        lt.census_captures(seal=p, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec)
    rd = t.EngineReader(world["engine"], world["snaps"], {FIRST + 2: sx.cap_id(FIRST + 2)}, allowed=set(sd["files"]) - {f"features/{sx.cap_id(FIRST + 2)}.parquet"})
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
    price_reads = Counter(name for name, cols in seen if "bid" in cols or "ask" in cols)
    origins = {sx.cap_id(k) + ".parquet" for k in range(FIRST, LAST + 1)}
    tail = {sx.cap_id(k) + ".parquet" for k in range(LAST + 1, LAST + 4)}
    # EACH span origin's quotes file is read with prices exactly once (an origin that is also a later slot of an earlier origin is not re-read with prices); the tail never
    assert set(price_reads) == origins and set(price_reads.values()) == {1}
    assert not (set(price_reads) & tail)
    status_only = Counter(name for name, cols in seen if cols == ("market_id", "t_off", "st"))
    assert set(status_only) & tail == {sx.cap_id(LAST + 1) + ".parquet"} and set(status_only) <= origins | tail  # only k + 1 of the last origin is opened in the tail, for status only
    assert status_only[sx.cap_id(LAST + 1) + ".parquet"] == 1


def test_unavailable_classes_and_gap_use_next_capture_status(tmp_path):
    ids = range(1000, 1300)
    w = sx.make_world(tmp_path, range(FIRST, LAST + 4), n_markets=300, drop_next={FIRST + 1: set(ids)}, st_next={**{(FIRST + 3, m): 1 for m in ids}, **{(FIRST + 5, m): 3 for m in ids}})
    spec = sx.loose_spec(FIRST, LAST)
    res = _census(w, spec, tmp_path)
    top = res["CH262"]["prints"]["unavailable_by_class_top_by_tier"]
    tot = Counter()
    for d in top.values():
        tot.update(d)
    assert set(tot) <= set(t.CLASSES)
    # slot FIRST's k + 1 quotes file holds no row (absent), FIRST + 2's k + 1 is all closed, FIRST + 4's is all one-sided; every other origin is labelled
    assert tot["unavailable_absent"] > 0 and tot["unavailable_closed"] > 0 and tot["unavailable_one_sided"] > 0 and tot["labelled"] > 0
    gap = res["CH262"]["gates"]["unavailable_gap_points"]["value"]
    assert gap is not None and math_isfinite(gap)


def math_isfinite(x) -> bool:
    return x == x and abs(x) != float("inf")


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
    # the tests read nothing from the file; its size and mtime are unchanged after every census run in this module (stat only)
    assert ((os.stat(TRIALS).st_size, os.stat(TRIALS).st_mtime_ns) if TRIALS.exists() else None) == TRIALS_STAT0


# --- code-freeze check fixes (LT14_CODE_FREEZE_CHECK_2026-10-30.md): one test per MUST / SHOULD, each failing on the code before the fix -----------------------


def test_must1_an_altered_or_deleted_sealed_sidecar_refuses(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    seal = _seal(world, spec, tmp_path)
    snaps2 = tmp_path / "snaps2"
    shutil.copytree(world["snaps"], snaps2)
    f = snaps2 / sx.cap_id(FIRST + 4) / "rows_ext.csv.gz"
    f.write_bytes(f.read_bytes() + b"x")
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[snaps2], spec=spec)
    assert "input identity check failed" in res["error"]
    assert res["bad"] == [{"file": f"snapshots/{sx.cap_id(FIRST + 4)}/rows_ext.csv.gz", "error": "sha256 mismatch", "root": str(snaps2)}]
    f.unlink()
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[snaps2], spec=spec)
    assert "input identity check failed" in res["error"] and res["bad"] == [{"file": f"snapshots/{sx.cap_id(FIRST + 4)}/rows_ext.csv.gz", "error": "absent"}]
    # the unaltered original root next to the damaged copy still passes (a deleted copy in one root is fine while another root holds the sealed bytes)
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"], snaps2], spec=spec)
    assert "error" not in res


def test_must2_a_quotes_file_sealed_as_absent_at_k_plus_one_is_unavailable_missing_capture_not_a_refusal(tmp_path):
    w = sx.make_world(tmp_path / "w", range(FIRST, LAST + 4), n_markets=300)
    (w["engine"] / "quotes" / f"{sx.cap_id(LAST + 1)}.parquet").unlink()
    spec = sx.loose_spec(FIRST, LAST)
    seal = _seal(w, spec, tmp_path)
    assert f"quotes/{sx.cap_id(LAST + 1)}.parquet" in json.loads(seal.read_text())["absent_files"]
    res = _census(w, spec, tmp_path, seal=seal)
    assert "error" not in res
    top = res["CH262"]["prints"]["unavailable_by_class_top_by_tier"]
    assert sum(d.get("unavailable_missing_capture", 0) for d in top.values()) > 0
    # a file that is neither sealed nor recorded as absent still refuses
    sd = json.loads(seal.read_text())
    sd["absent_files"] = []
    p = tmp_path / "noabs.json"
    p.write_text(json.dumps(sd))
    with pytest.raises(t.Refused, match="not in the seal"):
        lt.census_captures(seal=p, engine_root=w["engine"], snapshot_root=[w["snaps"]], spec=spec)


def _fixture_cu() -> dict:
    """8 labelled primary units, 24 covered origins (2 covered days, f = 10.5): events A x3, B x2, C x2, D x1; day 0 holds 3 units, day 1 holds 5; constant mo_d2h (SD_plan = the 1.3c floor)."""
    rows = [("A", 0, 0), ("A", 0, 1), ("B", 0, 2), ("A", 1, 12), ("C", 1, 13), ("C", 1, 14), ("D", 1, 15), ("B", 1, 16)]
    U = pd.DataFrame({"slot": [r[2] for r in rows], "sod": [r[2] % 12 for r in rows], "day": [r[1] for r in rows], "market_id": range(1, 9), "ekey": [r[0] for r in rows],
                      "event_id": range(1, 9), "tier": 2, "fee_class": "fee_on", "category": "x", "fam": [f"fam{i}" for i in range(8)], "sign": 1, "spread_c": 2.0, "mid_k": 0.5, "mid_diff": 0.0,
                      "t_off_k": 60.0, "t_off_k1": 60.0, "ms_neg_risk": 0, "mo_d2h": 0.01, "esize": 1, "cls": "labelled", "s_int": 1})
    cov = {"origins": list(range(24)), "covered_days": 2.0, "p_status_counts": {}}
    return {"cov": cov, "U": U, "M": pd.DataFrame(), "rest": pd.DataFrame(), "pre": pd.DataFrame(), "fee_abs": [], "fee_sgn": [], "abs_counts": {}, "sgn_counts": {},
            "arm_counts": {"sports": {}, "crypto": {}}, "cat_values": {}, "lc": {}, "toff_k": np.array([]), "toff_k1": np.array([]), "seal": {"pred_meta": {}, "champion_history": []},
            "per_cap": [{"slot": k, "covered": True, "cap": f"c{k}", "steps": {"in_scope": 10, "tier_na": 0}, "p_status": "ok"} for k in range(24)]}


def test_must3_projection_zeros_design_effect_and_design_se_by_hand_with_unscaled_cluster_sizes():
    spec = t.load_spec()
    blk = lt.census_ch262(_fixture_cu(), spec)
    rec, gates, pr = blk["recorded"], blk["gates"], blk["prints"]
    f = 21.0 / 2.0
    assert pr["projection_factor"] == f and rec["n_units"] == 8 and rec["n_labelled"] == 8 and rec["n_projected_labelled"] == 8 * f == 84.0
    # per-capture zeros: 8 of the 24 covered captures hold one unit each -> median 0, mean 1/3
    assert pr["primary_units_per_capture"]["n"] == 24 and gates["units_median"]["value"] == 0.0 and gates["nonstationarity_median_over_mean"]["value"] == 0.0
    # unscaled DE: events [3, 2, 2, 1] -> m = 18 / 8 = 2.25; days [3, 5] -> m = 34 / 8 = 4.25; event x day [2, 1, 1, 2, 1, 1] -> m = 12 / 8 = 1.5; rho = 0.02
    assert rec["DE"]["event"] == pytest.approx(1 + 1.25 * 0.02) and rec["DE"]["day"] == pytest.approx(1 + 3.25 * 0.02) and rec["DE"]["twoway"] == pytest.approx(1.025 + 1.065 - 1.01)
    # SD_plan = max(1.3, 100 x std = 0) = 1.3; n = 84 projected labelled units; the two-way SE (DE 1.08) is the largest
    se = {"event": 1.3 * math.sqrt(1.025 / 84), "twoway": 1.3 * math.sqrt(1.08 / 84), "day": 1.3 * math.sqrt(1.065 / 84)}
    assert rec["ses_c"] == pytest.approx(se) and blk["census_fixed"]["SD_plan_c"] == 1.3
    mult = 3.47 * 1.5
    assert rec["mde_design_c"] == pytest.approx(mult * se["twoway"])
    # m_21 = 8 units / 8 markets x 10.5 = 10.5 -> DE_gate = max(5, 1 + 9.5 x 0.02) = 5; declared MDE = 3.47 x 1.5 x 1.3 x sqrt(5 / (0.8 x 84))
    assert rec["m_21"] == pytest.approx(10.5) and rec["DE_gate"] == 5.0
    assert rec["mde_declared_c"] == pytest.approx(mult * 1.3 * math.sqrt(5 / (0.8 * 84)))
    assert gates["mde_c"]["value"] == pytest.approx(max(rec["mde_declared_c"], rec["mde_design_c"]))
    # the scaled values (cluster sizes x 10.5) are print only: days [31.5, 52.5] -> m = 3748.5 / 84 = 44.625; events -> 1984.5 / 84 = 23.625
    sc = rec["print_only_scaled_cluster"]
    assert sc["DE"]["day"] == pytest.approx(1 + 43.625 * 0.02) and sc["DE"]["event"] == pytest.approx(1 + 22.625 * 0.02) and "print only" in sc["note"]
    assert sc["mde_design_c"] > rec["mde_design_c"] and gates["mde_c"]["value"] != sc["mde_design_c"]


def test_must3_the_scaled_reading_no_longer_decides_the_mde_gates():
    cu = _fixture_cu()
    big = pd.concat([cu["U"]] * 150, ignore_index=True)  # 1,200 units over 2 days: unscaled DE_day uses m ~ 600, the scaled print uses 10.5 x that
    big["market_id"] = range(len(big))
    cu["U"] = big
    blk = lt.census_ch262(cu, t.load_spec())
    assert blk["recorded"]["DE"]["day"] < blk["recorded"]["print_only_scaled_cluster"]["DE"]["day"] / 5
    assert blk["recorded"]["mde_design_c"] < blk["recorded"]["print_only_scaled_cluster"]["mde_design_c"]


def _registry_dir(tmp_path) -> Path:
    sd = tmp_path / "specs"
    shutil.copytree(t.SPEC_DIR, sd)
    return sd


def test_must4_an_unrelated_registry_change_does_not_refuse_but_a_changed_p_entry_does(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    sd = _registry_dir(tmp_path)
    seal = _seal(world, spec, tmp_path, spec_dir=sd)
    sealed = json.loads(seal.read_text())
    assert sealed["registry_entry"]["model_id"] == t.PINNED_MODEL and sealed["spec_canonical_sha256"] == t.PINNED_SPEC_SHA256 and sealed["registry_sha256"]
    reg_p = sd / "registry.json"
    reg = json.loads(reg_p.read_text())
    other = next(m for m in reg["models"] if m["model_id"] != t.PINNED_MODEL)
    other["status"] = "retired_in_a_later_commit"
    reg["models"].append({**other, "model_id": "se_new_model_after_the_seal"})
    reg_p.write_text(json.dumps(reg))
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, spec_dir=sd)
    assert res["statuses"] == {"CH262": lt.CENSUS_PASS} and res["registry_sha256_now"] != res["registry_sha256_sealed"]  # printed, not compared
    # F3: a changed STATUS of P's entry never refuses (printed, sealed and now); a changed added_utc does
    ent = next(m for m in reg["models"] if m["model_id"] == t.PINNED_MODEL)
    sealed_status = ent.get("status")
    ent["status"] = "demoted_after_the_seal"
    reg_p.write_text(json.dumps(reg))
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, spec_dir=sd)
    assert res["statuses"] == {"CH262": lt.CENSUS_PASS} and "error" not in res
    assert res["p_registry_status"] == {"sealed": sealed_status, "now": "demoted_after_the_seal"} and res["p_registry_status"]["sealed"] != res["p_registry_status"]["now"]
    ent["added_utc"] = "2099-01-01T00:00:00Z"
    reg_p.write_text(json.dumps(reg))
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, spec_dir=sd)
    assert "registry entry" in res["error"] and "durable" not in res


def test_f3_a_changed_spec_sha_of_p_refuses(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    sd = _registry_dir(tmp_path)
    seal = _seal(world, spec, tmp_path, spec_dir=sd)
    reg_p = sd / "registry.json"
    reg = json.loads(reg_p.read_text())
    next(m for m in reg["models"] if m["model_id"] == t.PINNED_MODEL)["status"] = "demoted_after_the_seal"
    next(m for m in reg["models"] if m["model_id"] == t.PINNED_MODEL)["spec_sha256"] = "0" * 64
    reg_p.write_text(json.dumps(reg))
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, spec_dir=sd)
    assert "error" in res and res["statuses"] == {"CH262": t.WITHDRAWN_CLOCK}  # the input-clock audit (pin) catches it first; never a pass


def test_must5_the_sidecar_restore_draft_runs_before_the_seal_and_fills_the_seal_s_second_root():
    q1 = json.loads((DRAFTS / "q0741_lt14_seal.json").read_text())
    q3 = json.loads((DRAFTS / "q0743_lt14_sidecar_restore.json").read_text())
    assert q3["id"] in q1["depends_on"] and q3["not_before"] == q1["not_before"]
    assert q3["argv"][0] == "scripts/lt14_restore_guard.py"
    globs = [a for i, a in enumerate(q3["argv"]) if i and q3["argv"][i - 1] == "--path-glob"]
    assert globs == [f"data-dumps/research_lab/snapshots/202611{d:02d}T*/rows_ext.csv.gz" for d in range(7, 17)]
    dest = q3["argv"][q3["argv"].index("--dest") + 1]
    assert f"{dest}/data-dumps/research_lab/snapshots" in q1["argv"]  # the seal's second --snapshot-root is the restore tree
    q2 = json.loads((DRAFTS / "q0742_lt14_census.json").read_text())
    assert f"{dest}/data-dumps/research_lab/snapshots" in q2["argv"] and "docs/research_lab/seals/lt14_cc14.json" in q2["outputs"]


def test_should1_a_spec_other_than_declared_is_refused_and_the_runner_is_hashed(world, monkeypatch):
    monkeypatch.setattr(t, "ALLOW_NONDECLARED_SPEC", False)
    spec = sx.loose_spec(FIRST, LAST)
    assert "differs from DECLARED" in lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, now=1.8e9)["error"]
    assert "differs from DECLARED" not in str(lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], now=1.8e9).get("error"))
    ch = t.code_hashes()
    assert set(ch) == {"live_tests14.py", "live_tests14_base.py", "run_live_tests14.py"} and all(ch.values())
    assert "run_live_tests14.py" in t.CODE_FILES


def test_should2_a_census_time_audit_failure_is_a_durable_withdrawal(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    sd = _registry_dir(tmp_path)
    seal = _seal(world, spec, tmp_path, spec_dir=sd)
    p = json.loads((sd / "se0_champion_lr_mm.json").read_text())
    p["families"] = ["market_state", "momentum", "flow"]
    (sd / "se0_champion_lr_mm.json").write_text(json.dumps(p))
    res = lt.census_captures(seal=seal, engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, spec_dir=sd)
    assert res["durable"] is True and res["status"] == t.WITHDRAWN_CLOCK and res["statuses"] == {"CH262": t.WITHDRAWN_CLOCK} and res["lists"]["withdrawn_pre_census"] == ["CH262"]


def test_should2_the_crypto_fail_safe_is_a_durable_dropped_status_checked_before_any_row(tmp_path, monkeypatch):
    import gzip

    w = sx.make_world(tmp_path / "w", range(FIRST, LAST + 4), n_markets=120)
    for f in w["snaps"].glob("*/rows_ext.csv.gz"):
        df = pd.read_csv(f, dtype=str)
        df["fee_category"] = df["fee_category"].replace("crypto", "other")
        with gzip.open(f, "wt") as fh:
            df.to_csv(fh, index=False)
    spec = sx.loose_spec(FIRST, LAST)
    seal = _seal(w, spec, tmp_path)
    calls = []
    orig = t.EngineReader.features
    monkeypatch.setattr(t.EngineReader, "features", lambda self, *a, **k: calls.append(a) or orig(self, *a, **k))
    res = lt.census_captures(seal=seal, engine_root=w["engine"], snapshot_root=[w["snaps"]], spec=spec)
    assert "error" not in res and calls == []  # no features row was read
    assert res["statuses"] == {"CH262": lt.CENSUS_DROPPED_FAILSAFE} and res["lists"]["dropped_tests"] == ["CH262"]
    assert set(res["CH262"]["gates"]) == set(lt.GATE_FIELDS) and all(g["value"] is None and g["pass"] is False for g in res["CH262"]["gates"].values())
    assert set(res["CH262"]["failed"]) == set(lt.GATE_FIELDS)


def test_should3_a_log_line_that_attests_another_file_is_not_on_time(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    s = json.loads(_seal(world, spec, tmp_path).read_text())
    assert lt.p_status(s, FIRST + 3, spec) == "ok"
    cid = sx.cap_id(FIRST + 3)
    s["pred_log"][cid]["sha256"] = "0" * 64
    assert lt.p_status(s, FIRST + 3, spec) == "log_file_mismatch"
    assert lt.p_status(s, FIRST + 4, spec) == "ok"


def test_should5_the_seal_is_written_once_across_paths(world, tmp_path):
    spec = sx.loose_spec(FIRST, LAST)
    sdir = tmp_path / "seals"
    sdir.mkdir()
    assert "error" not in lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, now=1.8e9, seals_dir=sdir)
    (sdir / "lt14_census_inputs_elsewhere.json").write_text("{}")
    res = lt.seal_inputs(engine_root=world["engine"], snapshot_root=[world["snaps"]], spec=spec, now=1.8e9, seals_dir=sdir)
    assert "already exists" in res["error"] and "written once" in res["error"]


def test_should2_and_6_runner_writes_a_durable_result_and_copies_cc14_under_git(world, tmp_path, monkeypatch):
    rn = _load_script("run_live_tests14")
    seal = _seal(world, sx.loose_spec(FIRST, LAST), tmp_path)
    monkeypatch.setattr(rn, "_committed", lambda p: (None, "deadbeef"))
    out, copydir = tmp_path / "cc.json", tmp_path / "committed"
    argv = ["census", "--seal", str(seal), "--engine-root", str(world["engine"]), "--snapshot-root", str(world["snaps"]), "--out", str(out), "--commit-copy-dir", str(copydir)]
    assert rn.main(argv) == 0  # the real span is not in the synthetic seal: census_unavailable (coverage), a written outcome
    res = json.loads(out.read_text())
    assert res["status"] == t.CENSUS_UNAVAILABLE and res["seal_file"]["commit"] == "deadbeef"
    assert (copydir / "lt14_cc14.json").read_bytes() == out.read_bytes()
    assert rn.main([*argv[:-4], "--out", str(tmp_path / "cc2.json"), "--commit-copy-dir", str(copydir)]) == 2  # a second run is refused (marker)
    # a durable error result is written, not turned into exit 3
    seal2 = _seal(world, sx.loose_spec(FIRST, LAST), tmp_path, name="seal2.json")
    monkeypatch.setattr(rn.lt, "census_captures", lambda **kw: {"error": "x", "durable": True, "status": t.WITHDRAWN_CLOCK, "statuses": {"CH262": t.WITHDRAWN_CLOCK}})
    out3 = tmp_path / "cc3.json"
    assert rn.main(["census", "--seal", str(seal2), "--engine-root", str(world["engine"]), "--snapshot-root", str(world["snaps"]), "--out", str(out3), "--commit-copy-dir", str(tmp_path / "c2")]) == 0
    assert json.loads(out3.read_text())["status"] == t.WITHDRAWN_CLOCK


def test_should7_the_census_prints_the_nan_mid_count(passed):
    pr = passed["CH262"]["prints"]
    assert pr["mid_k_nan_units_primary"] == 0 and pr["mid_k_nan_units_top_all_tiers"] >= 0


# ---- re-check F1 / F2: the restore guard (synthetic trees, injected restore) -------------------------------------------------------------------------------------------------------

NOW_LATE = 4102444800.0  # 2100-01-01: every lag slot is long past its tolerance


@pytest.fixture()
def loose_guard_spec(monkeypatch):
    spec = sx.loose_spec(FIRST, LAST)
    monkeypatch.setattr(t, "load_spec", lambda *a, **k: spec)


def _cat_row(tag, cid, nbytes=1000):
    return {"release": tag, "path": f"data-dumps/research_lab/snapshots/{cid}/rows_ext.csv.gz", "dir": "snapshots", "capture_id": cid, "capture_time_utc": "2026-11-08T00:31:00Z", "bytes": nbytes, "sha256": "a" * 64}


def _guard_world(tmp_path, tags_rows, gap_slots=()):
    cat = tmp_path / "cat"
    cat.mkdir()
    for tag, rows in tags_rows.items():
        (cat / f"{tag}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    engine, snaps, dest = tmp_path / "eng", tmp_path / "snaps", tmp_path / "dest"
    (engine / "meta").mkdir(parents=True)
    snaps.mkdir()
    return cat, engine, snaps, dest


def _guard_argv(cat, engine, snaps, dest, *extra):
    return ["--snapshot-root", str(snaps), "--engine-root", str(engine), "--data-dumps-root", str(snaps), "--reserve-gb", "0", "--since", "2026-11-07", "--until", "2026-11-17T06:00:00Z",
            "--path-glob", "data-dumps/research_lab/snapshots/*/rows_ext.csv.gz", "--catalogue", str(cat), "--dest", str(dest), *extra]


@pytest.mark.usefixtures("loose_guard_spec")
def test_f1_guard_stops_when_no_catalogue_row_matches_and_never_calls_restore(tmp_path, capsys):
    g = _load_script("lt14_restore_guard")
    cat, engine, snaps, dest = _guard_world(tmp_path, {"data-20261020-x": [{**_cat_row("data-20261020-x", "20261020T000000Z_aa"), "capture_time_utc": "2026-10-20T00:31:00Z"}]})
    called = []
    rc = g.main(_guard_argv(cat, engine, snaps, dest), restore_main=lambda a: called.append(a) or 0, now=NOW_LATE, used_bytes=0)
    assert rc == 3 and not called and "STOP AND ASK THE OWNER" in capsys.readouterr().out


@pytest.mark.usefixtures("loose_guard_spec")
def test_f1_guard_passes_explicit_tags_only_for_matching_releases(tmp_path):
    g = _load_script("lt14_restore_guard")
    cat, engine, snaps, dest = _guard_world(tmp_path, {"data-old": [{**_cat_row("data-old", "o"), "capture_time_utc": "2026-10-20T00:31:00Z"}], "data-new": [_cat_row("data-new", "n")]})
    seen = []
    # an empty engine: no slot has a meta, so the coverage check has nothing to demand
    rc = g.main(_guard_argv(cat, engine, snaps, dest), restore_main=lambda a: seen.append(list(a)) or 0, now=NOW_LATE, used_bytes=0)
    assert rc == 0 and len(seen) == 1
    tags = [seen[0][i + 1] for i, x in enumerate(seen[0]) if x == "--tag"]
    assert tags == ["data-new"]
    # an explicit --tag from the caller is left alone
    seen.clear()
    g.main(_guard_argv(cat, engine, snaps, dest, "--tag", "data-old"), restore_main=lambda a: seen.append(list(a)) or 0, now=NOW_LATE, used_bytes=0)
    assert [seen[0][i + 1] for i, x in enumerate(seen[0]) if x == "--tag"] == ["data-old"]


@pytest.mark.usefixtures("loose_guard_spec")
def test_f1_post_restore_coverage_gap_exits_3_and_full_coverage_exits_0(tmp_path, capsys):
    g = _load_script("lt14_restore_guard")
    spec = sx.loose_spec(FIRST, LAST)
    cat, engine, snaps, dest = _guard_world(tmp_path, {"data-new": [_cat_row("data-new", "n")]})
    for k in (FIRST, FIRST + 1):
        (engine / "meta" / f"{sx.cap_id(k)}.json").write_text(json.dumps({"slot": k, "capture_id": sx.cap_id(k)}))
    assert [x["slot"] for x in g.coverage_gaps(engine, [snaps, dest], spec)["gaps"]] == [FIRST, FIRST + 1]
    (snaps / sx.cap_id(FIRST)).mkdir()
    (snaps / sx.cap_id(FIRST) / "rows_ext.csv.gz").write_bytes(b"x")  # in the host root
    r2 = dest / "data-dumps" / "research_lab" / "snapshots" / sx.cap_id(FIRST + 1)  # in the restore tree
    r2.mkdir(parents=True)
    (r2 / "rows_ext.csv.gz").write_bytes(b"y")
    assert g.coverage_gaps(engine, [snaps, dest / "data-dumps" / "research_lab" / "snapshots"], spec) == {"slots_with_meta": 2, "gaps": []}
    # through main with the span of the real spec: loose spec is not what main loads, so exercise the exit path with a patched loader
    if True:
        shutil.rmtree(dest)  # the restore wrote nothing: slot FIRST+1 is a gap
        rc = g.main(_guard_argv(cat, engine, snaps, dest), restore_main=lambda a: 0, now=NOW_LATE, used_bytes=0)
        assert rc == 3 and "STOP AND ASK THE OWNER" in capsys.readouterr().out
        r2.mkdir(parents=True)
        (r2 / "rows_ext.csv.gz").write_bytes(b"y")
        assert g.main(_guard_argv(cat, engine, snaps, dest), restore_main=lambda a: 0, now=NOW_LATE, used_bytes=0) == 0


@pytest.mark.usefixtures("loose_guard_spec")
def test_f2_guard_refuses_when_used_plus_bytes_plus_reserve_exceed_the_data_cap(tmp_path, capsys):
    g = _load_script("lt14_restore_guard")
    cat, engine, snaps, dest = _guard_world(tmp_path, {"data-new": [_cat_row("data-new", "n", 2**30)]})
    called = []
    now = NOW_LATE
    argv = [*_guard_argv(cat, engine, snaps, dest), "--data-cap-gb", "55"]
    rc = g.main(argv, restore_main=lambda a: called.append(a) or 0, now=now, used_bytes=int(54.5 * 2**30))
    out = capsys.readouterr().out
    assert rc == 3 and not called and "data cap" in out and "STOP AND ASK THE OWNER" in out
    assert g.cap_check(10 * 2**30, 2**30, 2**30, 55)["fits_cap"] is True and g.cap_check(54 * 2**30, 2**30, 2**30 + 1, 55)["fits_cap"] is False
    assert g.main(argv, restore_main=lambda a: called.append(a) or 0, now=now, used_bytes=10 * 2**30) == 0 and called
