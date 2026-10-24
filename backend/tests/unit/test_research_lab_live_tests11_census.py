# ruff: noqa: E501
"""LT11 (LIVE_TESTS_11.md section 7) seal and census tests, synthetic data only: the seal and its refusals, the coverage check that returns BEFORE any gate
(``census_unavailable (coverage)`` against ``census_dropped``), every gate of the three blocks (a loose spec passes them all on a rich synthetic world and
each threshold made impossible flips exactly its gate), NaN failing, the lag-slot loaders, the band unit check, the MDE arithmetic against the design text,
the header pre-check and the runner's refusals."""

from __future__ import annotations

import copy
import json
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests11 as lt
from astrolabe.research_lab import live_tests11_base as b
from tests import lt11_synth as sy

N_SLOTS = 70


@pytest.fixture(scope="module")
def cw(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lt11census")
    sy.rich_world(tmp / "snap", range(N_SLOTS))
    spec = sy.census_spec()
    seal = lt.seal_inputs(snapshot_root=tmp / "snap", work=tmp / "w_seal", spec=spec)
    assert "error" not in seal, seal.get("error")
    sp = tmp / "seal.json"
    sp.write_text(json.dumps(seal, default=str))
    cu = lt.census_units(seal=sp, snapshot_root=tmp / "snap", work=tmp / "w_cu", spec=spec)
    assert "error" not in cu and "unavailable" not in cu
    return {"tmp": tmp, "spec": spec, "seal": seal, "seal_path": sp, "cu": cu, "cache": {}}


def _gates(cw, spec):
    return lt.census_gates(cw["cu"], spec, cw["cache"])


def test_loose_spec_passes_every_gate_block(cw):
    res = _gates(cw, cw["spec"])
    assert res["statuses"] == {"CH234": "census_pass", "CH233": "census_pass", "CH232": "census_pass"}
    for t in lt.TESTS:
        g = res[t][f"gate_{t}"]
        assert g.pop("pass") is True and all(g.values()), {k: v for k, v in g.items() if not v}
        assert res[t]["census_fixed"]
    assert res["coverage"]["ok"] and res["crypto_classifier_shown_to_work"]


# gate key -> (block, parameter, impossible value) for every gate of the three blocks
FLIPS = {
    "CH234": {"traded_units": ("CH234", "units_projected_min", 1e12), "quote_only_units": ("CH234", "quote_only_projected_min", 1e12), "unknown_share": ("CH234", "unknown_share_max", -1.0),
              "unknown_captures": ("CH234", "unknown_capture_frac_max", -1.0), "corr_unknown_xw": ("CH234", "unknown_corr_max", -1.0), "corr_unknown_w": ("CH234", "unknown_corr_max", -1.0),
              "distinct_events": ("CH234", "distinct_events_min", 1e9), "g_eff": ("mde_common", "g_eff_min", 1e9), "cap_share": ("CH234", "cap_share_min", 2.0),
              "w_sd": ("CH234", "w_sd_share_min", 2.0), "resid_iqr": ("CH234", "resid_iqr_share_min", 2.0), "vif_w": ("CH234", "vif_w_max", -1.0),
              "corr_xw_log1p_liq": ("CH234", "corr_max", -1.0), "corr_xw_log_rv24s": ("CH234", "corr_max", -1.0), "corr_xw_d": ("CH234", "corr_max", -1.0),
              "corr_xw_spread_c": ("CH234", "corr_max", -1.0), "venue_clock": ("CH234", "venue_clock_max", 0.0), "block_share": ("CH234", "block_share_min", 2.0),
              "r_gate": ("CH234", "r_gate_max", -2.0), "slope_mde": ("mde_common", "mde_max_c", {"CH234": 0.0, "CH233": 1e9, "CH232": 1e9}),
              "f_mde": ("mde_common", "f_mde_max_c", {"CH234": 0.0, "CH233": 1e9, "CH232": 1e9})},
    "CH233": {"completeness": ("CH233", "completeness_min", 2.0), "receipt_span": ("CH233", "receipt_span_pairs_min", 2.0), "units": ("CH233", "units_projected_min", 1e12),
              "distinct_events": ("CH233", "distinct_events_min", 1e9), "events_ge48": ("CH233", "events_ge48_min", 1e9), "g_eff": ("mde_common", "g_eff_min", 1e9),
              "working_range": ("CH233", "working_range_min", 2.0), "event_sd": ("CH233", "event_sd_share_min", 2.0), "vif_w": ("CH233", "vif_w_max", -1.0),
              **{f"corr_zcl_{x}": ("CH233", "corr_max", -1.0) for x in ("d", "own_dbid_c", "own_dspread_c", "log1p_liq", "log_rv24s", "hb_km1")},
              "venue_clock": ("CH233", "venue_clock_max", 0.0), "block_share": ("CH233", "block_share_min", 2.0), "r_gate": ("CH233", "r_gate_max", -2.0),
              "slope_mde": ("mde_common", "mde_max_c", {"CH234": 1e9, "CH233": 0.0, "CH232": 1e9}), "f_mde": ("mde_common", "f_mde_max_c", {"CH234": 1e9, "CH233": 0.0, "CH232": 1e9})},
    "CH232": {"reward_finite": ("CH232", "reward_finite_min", 2.0), "crossings": ("CH232", "crossings_projected_min", 1e12), "control_crossings": ("CH232", "control_crossings_projected_min", 1e12),
              "f_arm_coverage": ("CH232", "f_arm_coverage_min", 2.0), "recross": ("CH232", "recross_ge3_max", -1.0), "distinct_events": ("CH232", "distinct_events_min", 1e9),
              "g_eff": ("mde_common", "g_eff_min", 1e9), "cap_share": ("CH232", "cap_share_min", 2.0), "venue_clock": ("CH232", "venue_clock_max", 0.0),
              **{f"corr_xo_{x}": ("CH232", "corr_max", -1.0) for x in ("log1p_liq", "log_rv24s", "absd")}, "vif_w": ("CH232", "vif_w_max", -1.0), "block_share": ("CH232", "block_share_min", 2.0),
              "r_gate": ("CH232", "r_gate_max", -2.0), "class_mde": ("mde_common", "mde_max_c", {"CH234": 1e9, "CH233": 1e9, "CH232": 0.0}),
              "f_mde": ("mde_common", "f_mde_max_c", {"CH234": 1e9, "CH233": 1e9, "CH232": 0.0})},
}
FLIP_PARAMS = [(t, k) for t, d in FLIPS.items() for k in d]


@pytest.mark.parametrize("test,key", FLIP_PARAMS)
def test_each_gate_flips_when_its_threshold_is_made_impossible(cw, test, key):
    spec = copy.deepcopy(cw["spec"])
    blk, par, val = FLIPS[test][key]
    spec["census_gates"][blk][par] = val
    res = _gates(cw, spec)
    g = res[test][f"gate_{test}"]
    assert g[key] is False, (test, key, g)
    assert g["pass"] is False and res[test]["status"] == lt.CENSUS_DROPPED
    # the other two blocks are evaluated independently
    for other in lt.TESTS:
        if other != test and not (blk == "mde_common" and par == "g_eff_min"):
            assert res[other]["status"] == lt.CENSUS_PASS


def test_every_gate_of_every_block_is_covered_by_a_flip(cw):
    res = _gates(cw, cw["spec"])
    for t in lt.TESTS:
        keys = {k for k in res[t][f"gate_{t}"] if k != "pass"}
        assert keys == set(FLIPS[t]), (t, keys ^ set(FLIPS[t]))


def test_band_unit_check_failure_makes_every_ch232_gate_fail_with_values_nan(cw):
    spec = copy.deepcopy(cw["spec"])
    spec["census_inputs"]["band_unit_check_cents"] = [100.0, 200.0]  # the served median (4.5c) is outside
    res = _gates(cw, spec)
    g = res["CH232"]["gate_CH232"]
    assert g["pass"] is False and g.get("values_nan") is True and not any(v for k, v in g.items() if k not in ("pass", "values_nan", "band_unit"))
    assert res["CH232"]["status"] == lt.CENSUS_DROPPED and res["CH234"]["status"] == lt.CENSUS_PASS
    chk = lt.band_unit_check([4.5, 4.5, 4.5], cw["spec"])
    assert chk["ok"] and not lt.band_unit_check([0.1], cw["spec"])["ok"] and not lt.band_unit_check([], cw["spec"])["ok"]


def test_nan_fails_a_gate(cw):
    cu = copy.copy(cw["cu"])
    cu["parts"] = {k: [p.assign(**{"rv24_dummy": np.nan}) for p in v] for k, v in cw["cu"]["parts"].items()}
    res = lt.census_gates({**cu, "parts": {**cu["parts"], "CH234": [p.assign(w=np.nan) for p in cu["parts"]["CH234"]]}}, cw["spec"], {})
    assert res["CH234"]["status"] == lt.CENSUS_DROPPED  # NaN collateral weights: the scales and every dependent gate are NaN -> fail
    assert res["CH233"]["status"] == lt.CENSUS_PASS


def test_census_fixed_values_are_filled_from_the_census_units(cw):
    res = _gates(cw, cw["spec"])
    cf = res["CH234"]["census_fixed"]
    assert all(cf[k] is not None for k in ("w_centre", "w_scale", "absd_centre", "absd_scale", "xw_cuts", "xw_gap", "q_unknown"))
    assert cf["q_unknown"] >= 0.15  # world 3's unknown share: floor 0.15 (a declared convention)
    assert set(res["CH233"]["census_fixed"]["s_c"]) == {"3-5", "6-10"} and res["CH233"]["census_fixed"]["s_c"]["3-5"] > 0
    assert "exclude_family" in res["CH232"]["census_fixed"]
    for t in ("CH234", "CH233", "CH232"):  # the census MDE is recorded for 1.9's 'underpowered' label (review should-fix 2)
        assert "mde_c" in res[t]["census_fixed"]


def test_recross_gate_counts_every_outward_crossing(cw):
    """Review should-fix 4 (A12 revised): the re-crossing gate counts every outward crossing between defined mids on a reward-panel crossing market-day; the
    zone / mover-only count is printed beside it and can only be lower or equal."""
    r = _gates(cw, cw["spec"])["CH232"]
    assert r["recross_basis"].startswith("every outward crossing")
    a, z = r["recross_ge2_share"], r["recross_ge2_share_zone_units"]
    assert (a != a and z != z) or a >= z - 1e-12
    assert a == a and z == z and z < 1.0  # both defined (a pass with both shares NaN / 0 would be vacuous)


def test_recross_gate_is_strictly_higher_when_non_mover_crossings_exist(cw):
    """Review 2026-10-23 defect 6: extra outward crossings between defined mids (not in the zone / mover units) raise the gate's share strictly above the
    zone-unit share, so the test cannot pass with both shares 0."""
    base = _gates(cw, cw["spec"])["CH232"]
    cu2 = {**cw["cu"], "xall": list(cw["cu"]["xall"]) * 4}
    r = lt.census_gates(cu2, cw["spec"], {})["CH232"]
    assert r["recross_ge2_share_zone_units"] == base["recross_ge2_share_zone_units"]
    assert r["recross_ge2_share"] > r["recross_ge2_share_zone_units"]


def test_series_family_over_forty_percent_is_excluded(cw):
    cu = copy.copy(cw["cu"])
    big = {}
    for kk, v in cw["cu"]["parts"].items():
        big[kk] = [p.assign(skey="series:big") if kk == "CH234" else p for p in v]
    res = lt.census_gates({**cu, "parts": big}, cw["spec"], {})
    assert res["CH234"]["exclude_family"] == "series:big" and res["CH234"]["top_family_share"] == 1.0


def test_unit_overlaps_and_descriptives_are_printed(cw):
    res = _gates(cw, cw["spec"])
    assert any(k.startswith("CH23") for k in res["unit_overlaps"])
    assert res["CH233"]["receipt_span_distribution"]["n"] > 0 and "q50" in res["CH233"]["receipt_span_distribution"]
    assert res["CH234"]["class_counts"] and res["CH232"]["inward_S1_units"] >= 0 and res["CH232"]["m1_side_reading"] == "cheap"


# --- coverage before any gate ---------------------------------------------------------------------------------------------------------------


def test_coverage_failure_returns_before_any_row_or_gate(cw, monkeypatch):
    spec = copy.deepcopy(cw["spec"])
    spec["census_inputs"]["min_covered_days"] = {"CC11": 7.0, "CC11_twins": 5.0}  # the synthetic span has 4.4 covered days

    def boom(*a, **k):
        raise AssertionError("a row was opened or a gate block was built after a coverage failure")

    seal2 = lt.seal_inputs(snapshot_root=cw["tmp"] / "snap", work=cw["tmp"] / "w_cov_seal", spec=spec)  # census_inputs is a hashed block: a seal under THIS spec
    (cw["tmp"] / "seal_cov.json").write_text(json.dumps(seal2, default=str))
    for name in ("write_series11", "census_ch234", "census_ch233", "census_ch232", "census_gates", "ch234_units", "ch233_units", "ch232_units", "SlotStore"):
        monkeypatch.setattr(lt, name, boom)
    res = lt.census_captures(seal=cw["tmp"] / "seal_cov.json", snapshot_root=cw["tmp"] / "snap", work=cw["tmp"] / "w_cov", spec=spec)
    assert res["statuses"] == {t: lt.CENSUS_UNAVAILABLE for t in lt.TESTS} == {t: res[t]["status"] for t in lt.TESTS}
    assert res["coverage"]["ok"] is False and res["coverage"]["covered_days"] < 7.0
    for t in lt.TESTS:
        assert f"gate_{t}" not in res[t] and set(res[t]) == {"status", "covered_days", "twin_days"}  # only the coverage counts, no descriptive line
    assert lt.CENSUS_UNAVAILABLE != lt.CENSUS_DROPPED


def test_twin_coverage_alone_can_make_the_census_unavailable(cw):
    spec = copy.deepcopy(cw["spec"])
    spec["census_inputs"]["min_covered_days"] = {"CC11": 1.0, "CC11_twins": 6.0}
    cov = lt.seal_coverage(cw["seal"], spec)
    assert cov["covered_days"] >= 1.0 and cov["twin_days"] < 6.0 and cov["ok"] is False


def test_coverage_counts_origins_with_both_captures_and_twin_slots(cw):
    cov = lt.seal_coverage(cw["seal"], cw["spec"])
    assert cov["covered_origins"] == 53 and cov["twin_origins"] == 53 and abs(cov["covered_days"] - 53 / 12.0) < 1e-12
    seal = copy.deepcopy(cw["seal"])
    # remove the sidecar of one slot from the manifest: its origin and the next one (the capture of the slot before it) lose coverage; its twin origins too
    drop = next(d for d, s in seal["slots"].items() if s == sy.iso(sy.slot_dt(30)))
    seal["files"] = {r: v for r, v in seal["files"].items() if not (r.endswith("rows_ext.csv.gz") and f"/{drop}/" in r)}
    cov2 = lt.seal_coverage(seal, cw["spec"])
    assert cov2["covered_origins"] == 51 and cov2["twin_origins"] == 49  # origins 30 and 31 lose a capture of the pair; 27 and 28 lose a twin slot


def test_dropped_is_a_computed_failure_and_distinct_from_unavailable(cw):
    spec = copy.deepcopy(cw["spec"])
    spec["census_gates"]["CH234"]["units_projected_min"] = 1e12
    res = _gates(cw, spec)
    assert res["CH234"]["status"] == lt.CENSUS_DROPPED and res["CH234"]["gate_CH234"]["traded_units"] is False and "traded_units_projected_21d" in res["CH234"]


# --- the seal and its refusals --------------------------------------------------------------------------------------------------------------


def test_seal_records_slots_hashes_design_and_blocks(cw):
    s = cw["seal"]
    assert s["design_text_sha256"] == lt.DESIGN_TEXT_SHA256 and s["spec_blocks_sha256"] == lt.spec_blocks_sha(cw["spec"]) and s["k_block"] == {"chg_1d": True, "chg_1w": True}
    assert s["n_missing"]["captures"] == 0 and s["windows"]["captures"] == [2, 69] and s["n_files"] == 3 * 68
    assert all(len(v["sha256"]) == 64 for v in s["files"].values())


def test_seal_refuses_a_null_header_precheck_a_changed_design_and_the_reward_rule(cw, tmp_path):
    spec = copy.deepcopy(cw["spec"])
    spec["k_block"] = {"chg_1d": None, "chg_1w": True}
    assert "k_block" in lt.seal_inputs(snapshot_root=cw["tmp"] / "snap", work=tmp_path / "a", spec=spec)["error"]
    other = tmp_path / "design.md"
    other.write_text("not the frozen design")
    assert "differs from the text-frozen file" in lt.seal_inputs(snapshot_root=cw["tmp"] / "snap", work=tmp_path / "b", spec=cw["spec"], design_path=other)["error"]
    spec2 = copy.deepcopy(cw["spec"])
    spec2["reward_null_rule"] = "v1"
    assert "listed_carry24h_v2" in lt.seal_inputs(snapshot_root=cw["tmp"] / "snap", work=tmp_path / "c", spec=spec2)["error"]


def test_seal_refuses_the_same_capture_with_different_bytes_in_two_roots(cw, tmp_path):
    root2 = tmp_path / "restore"
    sy.rich_world(root2, range(0, 8), seed=99)  # the same capture ids, different bytes
    spec = copy.deepcopy(cw["spec"])
    res = lt.seal_inputs(snapshot_root=[cw["tmp"] / "snap", root2], work=tmp_path / "w", spec=spec)
    assert "two roots with different bytes" in res.get("error", "")


def test_seal_refuses_a_slot_at_or_after_the_bound(cw, tmp_path):
    spec = copy.deepcopy(cw["spec"])
    spec["census_inputs"]["refuse_at_or_after_utc"] = sy.iso(sy.slot_dt(40))
    res = lt.seal_inputs(snapshot_root=cw["tmp"] / "snap", work=tmp_path / "w", spec=spec)
    assert "error" not in res and all(lt.epoch(s) < lt.epoch(spec["census_inputs"]["refuse_at_or_after_utc"]) for s in res["slots"].values())  # later captures are simply not sealed
    seal2 = copy.deepcopy(cw["seal"])
    assert lt.bound_violations(seal2, spec) and lt.bound_violations(seal2, cw["spec"]) == []


def _census(cw, tmp_path, seal=None, spec=None, snap=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    sp = tmp_path / "seal.json"
    sp.write_text(json.dumps(seal if seal is not None else cw["seal"], default=str))
    return lt.census_captures(seal=sp, snapshot_root=snap or (cw["tmp"] / "snap"), work=tmp_path / "work", spec=spec or cw["spec"])


def test_census_refuses_a_changed_design_text_and_other_seal_design(cw, tmp_path):
    seal = copy.deepcopy(cw["seal"])
    seal["design_text_sha256"] = "0" * 64
    assert "different LIVE_TESTS_11.md" in _census(cw, tmp_path, seal=seal)["error"]


def test_census_refuses_a_spec_whose_blocks_changed_since_the_seal(cw, tmp_path):
    spec = copy.deepcopy(cw["spec"])
    spec["census_gates"]["CH234"]["units_projected_min"] = 5
    assert "census blocks differ" in _census(cw, tmp_path, spec=spec)["error"]
    spec2 = copy.deepcopy(cw["spec"])
    spec2["census_fixed"]["CH234"]["q_unknown"] = 0.5  # census_fixed is deliberately outside the hash
    assert lt.spec_blocks_sha(spec2) == lt.spec_blocks_sha(cw["spec"])


def test_census_refuses_a_sealed_file_with_a_changed_hash_or_missing(cw, tmp_path):
    import shutil

    snap = tmp_path / "snap_copy"
    shutil.copytree(cw["tmp"] / "snap", snap)
    d = next(p for p in sorted(snap.iterdir()) if p.name.startswith("20261003"))
    with open(d / "rows.csv.gz", "ab") as fh:
        fh.write(b"x")
    res = _census(cw, tmp_path, snap=snap)
    assert "input identity" in res["error"] and any(x["error"] == "sha256 mismatch" for x in res["bad"])
    shutil.rmtree(d)
    res2 = _census(cw, tmp_path / "again", snap=snap)
    assert "error" in res2 and ("input identity" in res2["error"])


def test_census_refuses_a_non_empty_work_dir(cw, tmp_path):
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "stale").write_text("x")
    assert "not empty" in _census(cw, tmp_path)["error"]


def test_census_refuses_while_the_header_precheck_is_unfilled(cw, tmp_path):
    spec = copy.deepcopy(cw["spec"])
    spec["k_block"] = {"chg_1d": None, "chg_1w": None}
    res = _census(cw, tmp_path, spec=spec)
    assert "error" in res and ("k_block" in res["error"] or "census blocks differ" in res["error"])


# --- causality of the census and the lag-slot loaders -------------------------------------------------------------------------------------


def test_census_units_open_no_row_of_the_lag_slots(cw, tmp_path, monkeypatch):
    opened = []
    real = pd.read_csv

    def spy(path, *a, **k):
        opened.append(str(path))
        return real(path, *a, **k)

    monkeypatch.setattr(lt.pd, "read_csv", spy)
    sp = tmp_path / "seal.json"
    sp.write_text(json.dumps(cw["seal"], default=str))
    cu = lt.census_units(seal=sp, snapshot_root=cw["tmp"] / "snap", work=tmp_path / "w", spec=cw["spec"])
    last = cu["ORG"][-1]
    later = {cw["cu"]["by_slot"][s]["id"] for s in (last + 1, last + 2, last + 3)}
    assert opened and not [p for p in opened if any(i in p for i in later)]
    first = cu["ORG"][0] - 12
    assert not [p for p in opened if cw["cu"]["by_slot"][first - 1]["id"] in p] if (first - 1) in cw["cu"]["by_slot"] else True


def test_lag_loaders_return_only_the_twin_term_on_the_census_pass(cw):
    by_slot = cw["cu"]["by_slot"]
    k = 20
    xw = lt.lag_twin_xw(by_slot[k + 2]["dir"], by_slot[k + 3]["dir"], ["a0", "a1", "nope"], {"w_centre": 0.5, "w_scale": 0.1, "absd_centre": 0.0, "absd_scale": 0.02}, cw["spec"])
    assert isinstance(xw, pd.Series) and xw.name == "xw_tw" and xw.dtype == float and math.isnan(xw["nope"])
    xo = lt.twin_flag_xo(by_slot[k + 2]["dir"], by_slot[k + 3]["dir"], ["h0", "h1"], cw["spec"])
    assert set(xo.dropna().unique()) <= {0.0, 1.0} and xo.name == "xo_tw"
    z = lt.lag_twin_zcl(by_slot[k + 2]["dir"], by_slot[k + 3]["dir"], ["n0_0", "n0_1"], {"s_c": {"3-5": 1.0, "6-10": 1.0}}, cw["spec"])
    assert z.name == "zcl_tw" and z.notna().any()


# --- MDE arithmetic against the design text (planning figures) --------------------------------------------------------------------------------


def test_planning_mdes_reproduce_the_design_text():
    a = {"t_sum": 3.47, "day_factor": 1.5}
    # CH234 (2.5): DE 6.196, VIF_w 1.3, SD 4c, 900 traded units a capture, n_eff = units x 252 x 0.8, gap 2.2 SD -> 0.31c; F-MDE (r_w 0.1) 0.46c
    per_sd = b.mde_slope_declared(900 * 252 * 0.8, 0.04, 6.196, a, 1.3)
    assert abs(per_sd * 2.2 * 100 - 0.305) < 0.01
    assert abs(lt.f_mde_gate(per_sd * 2.2 * 100, 0.1, 0.0)["f_mde_c"] - 0.46) < 0.01
    # CH233 (3.4): DE 31, VIF_w 1.5, SD 2c, 1,440 units a capture -> 0.29c, F-MDE (r_w 0.2) 0.46c
    m33 = b.mde_slope_declared(1440 * 252 * 0.8, 0.02, 31.0, a, 1.5) * 2.2 * 100
    assert abs(m33 - 0.29) < 0.01 and abs(lt.f_mde_gate(m33, 0.2, 0.0)["f_mde_c"] - 0.46) < 0.01
    # CH232 (4.4): DE 31, VIF_w 1.3, SD 2c, 30 crossings and 90 reference units a capture -> 0.98c, F-MDE (r_w 0.2) 1.55c
    m32 = b.mde_class(30 * 201.6, 90 * 201.6, 0.02, 31.0, a, 1.3) * 100
    assert abs(m32 - 0.98) < 0.01 and abs(lt.f_mde_gate(m32, 0.2, 0.0)["f_mde_c"] - 1.55) < 0.01
    # the count gates sit at the design's kill lines (7): 745 x 252, 335 x 252, 1,000 x 252, 67 x 252, 24 x 252
    g = lt.load_spec(sha=None)["census_gates"]
    assert g["CH234"]["units_projected_min"] == 745 * 252 and g["CH234"]["quote_only_projected_min"] == 335 * 252
    assert g["CH233"]["units_projected_min"] == 1000 * 252 and g["CH232"]["crossings_projected_min"] == 67 * 252 and g["CH232"]["control_crossings_projected_min"] == 24 * 252
    assert g["CH234"]["de_floor"] == 6.196 and g["CH233"]["de_floor"] == 5.0 and g["CH232"]["de_floor"] == 5.0


def test_de_gate_is_max_of_floor_and_computed_and_t_sum_is_the_larger_of_declared_and_exact(cw):
    a = b.mde_common(cw["spec"])
    assert a["t_sum"] >= 3.47 and abs(a["t_sum"] - b.exact_t_sum()) < 1e-12
    de = b.design_effect(pd.Series(["e1"] * 10 + ["e2"] * 2), 1.0, 0.02)
    assert b.de_gate(de, 6.196) == 6.196  # floor binds when the computed value is smaller
    assert math.isnan(b.de_gate({"DE": float("nan")}, 5.0))


def test_g_eff_is_the_kish_effective_event_count():
    assert abs(lt.g_eff(["a"] * 4 + ["b"] * 4) - 2.0) < 1e-12 and abs(lt.g_eff(["a"] * 6 + ["b"] + ["c"]) - 64 / 38) < 1e-12 and math.isnan(lt.g_eff([]))


def test_header_precheck_reads_headers_only(cw, tmp_path):
    by_slot = cw["cu"]["by_slot"]
    pre = lt.header_precheck(capture_dir=by_slot[20]["dir"], spec=cw["spec"])
    assert pre["chg_1d"] is True and pre["chg_1w"] is True and pre["rows_missing"] == [] and pre["sidecar_missing"] == [] and pre["manifest_has_state"]
    import gzip

    d = tmp_path / "cap"
    d.mkdir()
    with gzip.open(d / "rows.csv.gz", "wt") as fh:
        fh.write("market_id,best_bid,best_ask\nm1,0.4,0.5\n")
    pre2 = lt.header_precheck(capture_dir=d, spec=cw["spec"])
    assert pre2["chg_1d"] is False and "received_utc" in pre2["rows_missing"]
