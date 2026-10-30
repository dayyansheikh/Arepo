# ruff: noqa: E501
"""LT13 stage A census (LIVE_TESTS_13.md 6): the seal and its refusals, coverage first (``census_unavailable (coverage)`` and nothing else), every gate flip, the output schema,
the four lists with CH252 under ``withdrawn_pre_census``, the write-once run, the runner and the restore guard, on synthetic capture trees only (tmp paths; nothing real read or written)."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from astrolabe.research_lab import live_tests12 as lt12
from astrolabe.research_lab import live_tests12_base as b
from astrolabe.research_lab import live_tests13 as lt
from astrolabe.research_lab import live_tests13_base as t
from tests import lt13_synth as sx

BACKEND = Path(t.__file__).parents[2]
TRIALS = t.ROOT / "docs" / "research_lab" / "trials.jsonl"
TRIALS_SHA0 = b.sha256_file(TRIALS) if TRIALS.exists() else None


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
    root = tmp_path_factory.mktemp("lt13census")
    snap = root / "snap"
    sx.make_world(snap, range(0, 46))
    return {"root": root, "snap": snap}


def _seal(tree, spec, tmp_path, name="seal.json", **kw) -> Path:
    s = lt.seal_inputs(snapshot_root=[tree["snap"]], work=tmp_path / "sw", spec=spec, **kw)
    assert "error" not in s, s.get("error")
    p = tmp_path / name
    p.write_text(json.dumps(s, default=str))
    return p


def _census(tree, spec, tmp_path, seal=None, **kw):
    p = seal or _seal(tree, spec, tmp_path)
    return lt.census_captures(seal=p, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec, **kw)


@pytest.fixture(scope="module")
def passed(tree, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pass")
    return _census(tree, sx.loose_spec(), tmp)


def test_census_passes_on_the_rich_world_and_fixes_every_declared_value(passed):
    res = passed
    assert res["statuses"] == {"CH253": lt.CENSUS_PASS}
    cf = res["CH253"]["census_fixed"]
    assert set(cf) >= {"s_bt", "s_w", "zs_cuts", "zs_gap", "rgap_q50_s", "rgap_q90_s", "rho_census", "rho_census_nan", "exclude_family"}
    assert cf["s_bt"] > 0 and cf["s_w"] > 0 and len(cf["zs_cuts"]) == 2 and cf["zs_gap"] > 0 and isinstance(cf["rho_census"], float) and cf["rho_census_nan"] is False
    assert cf["rgap_q50_s"] is not None and cf["rgap_q90_s"] >= cf["rgap_q50_s"]
    assert res["CH253"]["census_gate_values"]["mde_c"] > 0


def test_the_four_lists_are_exclusive_and_ch252_is_withdrawn_pre_census(passed):
    lists = passed["lists"]
    assert lists == {"k_tests": ["CH253"], "dropped_tests": [], "census_unavailable": [], "withdrawn_pre_census": ["CH252"]}
    assert passed["withdrawn_pre_census"] == {"CH252": "withdrawn_pre_census (fee reading unresolved)"}
    flat = [x for v in lists.values() for x in v]
    assert len(flat) == len(set(flat))
    assert "CH252" not in passed and "gate_CH252" not in json.dumps(passed)


def test_output_schema_holds_every_gate_and_every_print(passed):
    c = passed["CH253"]
    assert set(c["gate_CH253"]) == {"batch_join_pinned", "coverage", "completeness", "units_projected", "batches_with_unit", "batches_ge48", "g_eff", "same_slot", "ident_nonzero", "ident_top1",
                                    "ident_batch", "vif_w", "corr_zs_log1p_liq", "corr_zs_log_rv24s", "corr_zs_d", "placebo_coverage", "block_share", "venue_clock", "r_gate", "slope_mde", "f_mde", "pass"}
    for k in ("coverage_cross_event_batch", "batch_completeness_pooled", "units_projected_21d", "units_per_capture", "same_slot", "identification", "vif_w_gate", "design_effect", "controls_rank",
              "slope", "F", "r_gate", "placebo_coverage", "venue_clock", "block_share", "g_eff_batch", "exclude_family", "census_prints", "registry"):
        assert k in c, k
    pr = c["census_prints"]
    for k in ("batch_size_distribution_registry", "cross_event_share", "batch_incomplete_units", "receipt_span_units", "placebo_none", "placebo_none_by_age_decile", "units_by_batch_age_days",
              "gt30_arm_units", "sports_arm_units", "sports_mate_share", "units_by_fee_type_x_fee_category", "pseudo_candidates_by_fee_type_x_fee_category", "placebo_none_by_fee_type_x_fee_category",
              "units_by_fee_type_x_sports_slug", "rows_by_fee_type_x_sports_slug_x_sports_class", "fee_class_and_category_changes_per_capture"):
        assert k in pr, k
    assert pr["fee_class_and_category_changes_per_capture"] and {"fee_class_changed", "category_changed", "sports_changed"} <= set(pr["fee_class_and_category_changes_per_capture"][0])
    rk = c["controls_rank"]
    assert {"rank", "n_cols", "dropped", "status", "zero_variance_dropped"} <= set(rk) and rk["status"] == "ok" and rk["rank"] == rk["n_cols"]
    for k in ("design_text_sha256", "declaration_sha256", "batch_join_code_sha256", "code_sha256", "imported_sha256", "coverage", "k_block"):
        assert k in passed, k
    json.dumps(passed, allow_nan=False)  # serialisable, no NaN tokens
    assert not any("target" in k or "ds_next" in k for k in c)


def test_prints_count_the_fee_step_cells(passed):
    pr = passed["CH253"]["census_prints"]
    assert any("zero_fees" in k for k in pr["units_by_fee_type_x_fee_category"]) and any("politics_fees" in k for k in pr["units_by_fee_type_x_fee_category"])
    assert pr["units_by_batch_age_days"]["genesis_share"] >= 0


def test_coverage_is_checked_first_and_a_failure_prints_nothing_else(tree, tmp_path, monkeypatch):
    spec = sx.loose_spec()
    spec["census_inputs"]["min_covered_days"] = {"CC13": 99.0, "CC13_twins": 99.0}
    seal = _seal(tree, spec, tmp_path)

    def boom(*a, **k):
        raise AssertionError("a row was opened")

    monkeypatch.setattr(t, "write_series13", boom)
    res = lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec)
    assert res["statuses"] == {"CH253": lt.CENSUS_UNAVAILABLE} == {"CH253": "census_unavailable (coverage)"}
    assert set(res["CH253"]) == {"status", "covered_days", "twin_days"}
    assert res["lists"] == {"k_tests": [], "dropped_tests": [], "census_unavailable": ["CH253"], "withdrawn_pre_census": ["CH252"]}
    assert not {"gate_CH253", "census_fixed", "census_prints", "fee_category_values", "counts"} & set(res)


def test_twin_coverage_fails_alone_when_the_twin_days_are_short(tree, tmp_path):
    spec = sx.loose_spec()
    spec["census_inputs"]["min_covered_days"] = {"CC13": 1.0, "CC13_twins": 50.0}
    res = _census(tree, spec, tmp_path)
    assert res["statuses"] == {"CH253": lt.CENSUS_UNAVAILABLE} and res["lists"]["census_unavailable"] == ["CH253"]


@pytest.mark.parametrize("gate,key,val", [("coverage", "coverage_min", 0.99), ("completeness", "completeness_min", 1.01), ("units_projected", "units_projected_min", 1e12),
                                          ("batches_with_unit", "batches_with_unit_min", 10**6), ("batches_ge48", "batches_ge48_min", 10**6), ("vif_w", "vif_w_max", 0.5),
                                          ("placebo_coverage", "placebo_coverage_min", 1.01), ("block_share", "block_share_min", 1.01), ("venue_clock", "venue_clock_max", 0.0),
                                          ("same_slot", "same_slot_share_max", -1.0), ("ident_nonzero", "ident_share_min", 1.01), ("r_gate", "r_gate_max", -2.0)])
def test_each_gate_flips_on_its_own_threshold_and_drops_the_test(tree, tmp_path, gate, key, val):
    spec = sx.loose_spec()
    spec["census_gates"]["CH253"][key] = val
    res = _census(tree, spec, tmp_path)
    g = res["CH253"]["gate_CH253"]
    assert g[gate] is False, g
    assert res["statuses"] == {"CH253": lt.CENSUS_DROPPED} and res["lists"]["dropped_tests"] == ["CH253"] and res["lists"]["k_tests"] == []
    assert [k for k, v in g.items() if v is False and k != "pass"] == [gate]  # a single threshold flips a single gate


def test_mde_gates_flip_on_the_floor_and_nan_fails(tree, tmp_path):
    spec = sx.loose_spec()
    spec["census_gates"]["mde_common"]["mde_max_c"] = {"CH253": 1e-9}
    res = _census(tree, spec, tmp_path)
    assert res["CH253"]["gate_CH253"]["slope_mde"] is False
    (tmp_path / "x").mkdir()
    spec2 = sx.loose_spec()
    spec2["controls_own"] = [*spec2["controls_own"], "spread_km1_c"]  # the declared (exactly collinear) list: the controls are unavailable, the MDE is infinite, NaN fails
    res2 = _census(tree, spec2, tmp_path / "x")
    assert res2["CH253"]["controls_rank"]["status"] == "unavailable"
    assert res2["CH253"]["gate_CH253"]["slope_mde"] is False and res2["CH253"]["gate_CH253"]["f_mde"] is False and res2["statuses"] == {"CH253": lt.CENSUS_DROPPED}


# --- the refusals (6, "what the census code must refuse") ---------------------------------------------------------------------------------------


def _refused(res, text):
    assert "error" in res and text in res["error"], res


def test_refuses_an_input_that_differs_from_the_seal(tree, tmp_path):
    spec = sx.loose_spec()
    snap = tmp_path / "snap"
    shutil.copytree(tree["snap"], snap)
    seal = lt.seal_inputs(snapshot_root=[snap], work=tmp_path / "sw", spec=spec)
    (tmp_path / "s.json").write_text(json.dumps(seal, default=str))
    victim = sorted(snap.glob("*/rows_ext.csv.gz"))[20]
    victim.write_bytes(victim.read_bytes() + b"x")
    res = lt.census_captures(seal=tmp_path / "s.json", snapshot_root=[snap], work=tmp_path / "cw", spec=spec)
    _refused(res, "not named in the seal with an equal sha256")
    assert any(x["error"] == "sha256 mismatch" for x in res["bad"])


def test_refuses_an_input_not_named_in_the_seal(tree, tmp_path):
    spec = sx.loose_spec()
    seal = json.loads(_seal(tree, spec, tmp_path).read_text())
    gone = sorted(k for k in seal["files"] if k.endswith("rows.csv.gz"))[22]
    del seal["files"][gone]
    (tmp_path / "s2.json").write_text(json.dumps(seal))
    res = lt.census_captures(seal=tmp_path / "s2.json", snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec)
    _refused(res, "not named in the seal with an equal sha256")
    assert any(x["error"] in ("not sealed", "sealed but absent locally") for x in res["bad"])


def test_refuses_a_design_text_that_is_not_the_frozen_file_or_a_ledger_without_the_freeze_hash(tree, tmp_path):
    spec = sx.loose_spec()
    seal = _seal(tree, spec, tmp_path)
    d = tmp_path / "LIVE_TESTS_13.md"
    d.write_text(t.DESIGN_PATH.read_text() + "\nx\n")
    res = lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec, design_path=d)
    _refused(res, "ledger's freeze hash")
    assert "error" in lt.seal_inputs(snapshot_root=[tree["snap"]], work=tmp_path / "sw2", spec=spec, design_path=d)
    led = tmp_path / "LEDGER.md"
    led.write_text("nothing here\n")
    _refused(lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw2", spec=spec, ledger_path=led), "no 'LT13 DESIGN TEXT FROZEN' line")
    led.write_text(f"- **LT13 DESIGN TEXT FROZEN:** sha256 `{'0' * 64}`\n")
    _refused(lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw3", spec=spec, ledger_path=led), "no 'LT13 DESIGN TEXT FROZEN' line")
    _refused(lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw4", spec=spec, ledger_path=tmp_path / "missing.md"), "not found")


def test_refuses_a_seal_with_another_design_hash(tree, tmp_path):
    spec = sx.loose_spec()
    s = json.loads(_seal(tree, spec, tmp_path).read_text())
    s["design_text_sha256"] = "0" * 64
    (tmp_path / "s3.json").write_text(json.dumps(s))
    _refused(lt.census_captures(seal=tmp_path / "s3.json", snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec), "freeze hash")


def test_refuses_a_seal_that_does_not_pin_the_batch_join_code_or_pins_another(tree, tmp_path):
    spec = sx.loose_spec()
    s = json.loads(_seal(tree, spec, tmp_path).read_text())
    assert s["batch_join_code_sha256"] == t.batch_join_sha()
    s2 = {k: v for k, v in s.items() if k != "batch_join_code_sha256"}
    (tmp_path / "a.json").write_text(json.dumps(s2))
    _refused(lt.census_captures(seal=tmp_path / "a.json", snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec), "does not pin the batch join")
    s3 = {**s, "batch_join_code_sha256": "1" * 64}
    (tmp_path / "b.json").write_text(json.dumps(s3))
    _refused(lt.census_captures(seal=tmp_path / "b.json", snapshot_root=[tree["snap"]], work=tmp_path / "cw2", spec=spec), "differs from the one pinned")


def test_the_batch_join_hash_moves_with_the_join_code(monkeypatch):
    h0 = t.batch_join_sha()
    monkeypatch.setattr(t, "batch_join_symbols", lambda: (t.event_keys, t.cat_verbatim))
    assert t.batch_join_sha() != h0


def test_refuses_a_seal_that_holds_a_feed_capture_ch252(tree, tmp_path):
    spec = sx.loose_spec()
    s = json.loads(_seal(tree, spec, tmp_path).read_text())
    s["feeds"] = {"20261107T000000Z_feed": {"started_utc": "2026-11-07T00:00:00Z"}}
    (tmp_path / "f.json").write_text(json.dumps(s))
    _refused(lt.census_captures(seal=tmp_path / "f.json", snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec), "CH252 is withdrawn_pre_census")


def test_refuses_when_an_imported_helper_differs_from_its_pin(tree, tmp_path, monkeypatch):
    spec = sx.loose_spec()
    seal = _seal(tree, spec, tmp_path)
    monkeypatch.setitem(t.DECLARED["imported_sha256"], "live_tests12.py", "f" * 64)
    _refused(lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec), "imported helper file differs")
    assert "error" in lt.seal_inputs(snapshot_root=[tree["snap"]], work=tmp_path / "sw2", spec=spec)


def test_refuses_a_seal_written_for_other_spec_blocks_or_without_the_header_precheck(tree, tmp_path):
    spec = sx.loose_spec()
    seal = _seal(tree, spec, tmp_path)
    spec2 = copy.deepcopy(spec)
    spec2["census_gates"]["CH253"]["placebo_coverage_min"] = 0.5  # a changed threshold after the seal
    _refused(lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec2), "differ from those at seal time")
    spec3 = sx.loose_spec()
    spec3["k_block"] = {"chg_1d": None, "chg_1w": None}
    _refused(lt.seal_inputs(snapshot_root=[tree["snap"]], work=tmp_path / "sw3", spec=spec3), "k_block")


@pytest.mark.parametrize("lists", [{"k_tests": ["CH252"]}, {"dropped_tests": ["CH252"]}, {"census_unavailable": ["CH252"]}, {"withdrawn_pre_census": ["CH252", "CH253"]},
                                   {"k_tests": ["CH253"], "dropped_tests": ["CH253"]}])
def test_refuses_a_spec_that_puts_ch252_anywhere_but_withdrawn_or_lists_a_test_twice(tree, tmp_path, lists):
    spec = sx.loose_spec()
    seal = _seal(tree, spec, tmp_path)
    sp = sx.loose_spec()
    sp.update(lists)
    assert "error" in t.scope_error(sp)
    res = lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=sp)
    assert "error" in res and "CH252" in json.dumps(res) or "two of the four lists" in res["error"]


@pytest.mark.parametrize("block", ["CH252", "target", "k+1 target", "LT12 zs_D", "ch244", "outcome", "shock x unrew", "xw"])
def test_refuses_to_compute_a_ch252_block_a_target_or_an_lt11_lt12_object(tree, tmp_path, block):
    spec = sx.loose_spec()
    with pytest.raises(t.Refused, match="refuses to compute|unknown census block"):
        lt.census_captures(seal=tmp_path / "none.json", snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec, blocks=("CH253", block))


def test_a_later_slot_read_by_a_unit_builder_is_refused(tree, tmp_path, monkeypatch):
    spec = sx.loose_spec()
    seal = _seal(tree, spec, tmp_path)
    real = t.units13

    def sneaky(store, bt, k, spec, **kw):
        out = real(store, bt, k, spec, **kw)
        store.ser(k + 1)  # a k + 1 price / spread read after the builder set its limit
        return out

    monkeypatch.setattr(t, "units13", sneaky)
    with pytest.raises(t.Refused, match="causality"):
        lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec)


def test_refuses_a_non_empty_work_directory(tree, tmp_path):
    spec = sx.loose_spec()
    seal = _seal(tree, spec, tmp_path)
    (tmp_path / "cw").mkdir()
    (tmp_path / "cw" / "stale").write_text("x")
    _refused(lt.census_captures(seal=seal, snapshot_root=[tree["snap"]], work=tmp_path / "cw", spec=spec), "not empty")


def test_a_second_run_is_refused_write_once(tmp_path):
    seal = tmp_path / "seal.json"
    seal.write_text("{}")
    out = tmp_path / "cc13.json"
    assert lt.claim_run(seal, out, {"x": 1}) is None
    assert lt.run_marker(seal).exists()
    assert "second run is refused" in lt.claim_run(seal, tmp_path / "other.json", {})
    out.write_text("{}")
    seal2 = tmp_path / "seal2.json"
    seal2.write_text("{}")
    assert "refusing to overwrite" in lt.claim_run(seal2, out, {})
    assert not lt.run_marker(seal2).exists()  # a refused claim does not burn the run


# --- the runner -----------------------------------------------------------------------------------------------------------------------------


def _runner():
    sp = importlib.util.spec_from_file_location("run_live_tests13", BACKEND / "scripts" / "run_live_tests13.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def test_runner_seal_census_and_write_once(tree, tmp_path, monkeypatch, capsys):
    rl = _runner()
    spec = sx.loose_spec()
    monkeypatch.setattr(rl.t, "load_spec", lambda *a, **k: spec)
    seal = tmp_path / "seal.json"
    assert rl.main(["seal", "--snapshot-root", str(tree["snap"]), "--work", str(tmp_path / "sw"), "--out", str(seal)]) == 0
    assert rl.main(["seal", "--snapshot-root", str(tree["snap"]), "--work", str(tmp_path / "sw9"), "--out", str(seal)]) == 1  # refuses to overwrite
    assert rl.main(["census", "--seal", str(seal), "--work", str(tmp_path / "cw"), "--snapshot-root", str(tree["snap"]), "--out", str(tmp_path / "cc.json")]) == 2  # not git-tracked
    monkeypatch.setattr(rl, "_committed", lambda p: (None, "deadbeef"))
    out = tmp_path / "cc13.json"
    assert rl.main(["census", "--seal", str(seal), "--work", str(tmp_path / "cw"), "--snapshot-root", str(tree["snap"]), "--out", str(out)]) == 0
    res = json.loads(out.read_text())
    assert res["statuses"] == {"CH253": lt.CENSUS_PASS} and res["seal_file"]["commit"] == "deadbeef"
    capsys.readouterr()
    assert rl.main(["census", "--seal", str(seal), "--work", str(tmp_path / "cw2"), "--snapshot-root", str(tree["snap"]), "--out", str(tmp_path / "again.json")]) == 2  # a second run
    assert "second run is refused" in capsys.readouterr().out
    assert rl.main(["census", "--seal", str(seal), "--work", str(tmp_path / "cw3"), "--snapshot-root", str(tree["snap"]), "--out", str(out)]) == 1  # existing --out
    assert not (tmp_path / "again.json").exists()


def test_runner_has_no_stage_b_subcommand():
    rl = _runner()
    assert {"header-precheck", "seal", "census"} == set(rl.build_parser()._subparsers._group_actions[0].choices)


def test_header_precheck_reads_headers_only(tree, tmp_path):
    rl = _runner()
    cap = sorted(tree["snap"].glob("*"))[0]
    out = tmp_path / "h.json"
    assert rl.main(["header-precheck", "--capture-dir", str(cap), "--out", str(out)]) == 0
    h = json.loads(out.read_text())
    assert h["chg_1d"] is True and "created_at" in h["sidecar_header"] and not h["rows_missing"] and not h["sidecar_missing"]


# --- restore readiness and the guard ---------------------------------------------------------------------------------------------------------


def _lag_capture(root: Path, spec: dict, i: int, state: str) -> float:
    k = lt12.lag_slots(spec)[i]
    t0 = b.slot_time(k, spec)
    d = root / (b.iso(t0).replace("-", "").replace(":", "")[:15] + "Z_x")
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": state, "started_utc": b.iso(t0)}))
    if state == "complete":
        (d / "rows.csv.gz").write_bytes(b"x")
    return t0


def test_restore_readiness_refuses_only_while_a_lag_slot_capture_is_in_progress(tmp_path):
    spec = t.load_spec()
    root = tmp_path / "snap"
    t0 = _lag_capture(root, spec, 0, "running")
    rd = lt.restore_readiness([root], spec, t0 + 600)
    assert rd["refuse"] and rd["refusing_slots"]
    # a capture in a FINAL non-complete state, or one still open a whole slot after its start, is missing, never awaited
    root2 = tmp_path / "snap2"
    for i, st in enumerate(("failed", "partial", "running")):
        _lag_capture(root2, spec, i, st)
    t_late = b.slot_time(lt12.lag_slots(spec)[-1], spec) + 7200 + 1800 + 5
    rd2 = lt.restore_readiness([root2], spec, t_late)
    assert not rd2["refuse"] and len(rd2["missing_slots"]) == 3


def test_restore_guard_exits_75_while_a_lag_slot_capture_is_in_progress(tmp_path, capsys):
    sp = importlib.util.spec_from_file_location("lt13_restore_guard", BACKEND / "scripts" / "lt13_restore_guard.py")
    g = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(g)
    spec = t.load_spec()
    root = tmp_path / "snap"
    t0 = _lag_capture(root, spec, 0, "running")
    assert g.main(["--snapshot-root", str(root), "--dest", str(tmp_path / "d"), "--path-glob", "x"], now=t0 + 60) == t.TEMPFAIL
    assert "not now" in capsys.readouterr().out


# --- the queue drafts and the trials file ---------------------------------------------------------------------------------------------------------


DRAFTS = t.ROOT / "docs" / "research_lab" / "queue" / "drafts"


@pytest.mark.parametrize("name", ["q0720_lt13_census_restore", "q0721_lt13_seal", "q0722_lt13_census"])
def test_queue_drafts_state_the_design_dates_and_dependencies(name):
    d = json.loads((DRAFTS / f"{name}.json").read_text())
    assert d["id"] == name and d["family"] == "live_tests_13" and d["not_before"] == "2026-11-17T09:00:00Z"
    assert (BACKEND / d["argv"][0]).exists()
    if name.startswith("q0720"):
        assert {"q0710_lt12_census_restore", "q0711_lt12_seal", "q0712_lt12_census"} <= set(d["depends_on"])
        assert d["resources"]["lane"] == "net" and d["resources"]["mem_mb"] == 400 and d["resources"]["disk_mb"] == 1400 and not any("reward_params" in a for a in d["argv"])
    if name.startswith("q0721"):
        assert d["depends_on"] == ["q0720_lt13_census_restore"] and d["resources"]["mem_mb"] == 300 and d["resources"]["lane"] == "net"
    if name.startswith("q0722"):
        assert d["depends_on"] == ["q0721_lt13_seal"] and d["resources"]["lane"] == "cpu" and d["resources"]["mem_mb"] == 750 and "--data-dumps-cap-gb" in d["argv"]


def test_the_trials_file_is_never_touched(passed):
    assert (b.sha256_file(TRIALS) if TRIALS.exists() else None) == TRIALS_SHA0
