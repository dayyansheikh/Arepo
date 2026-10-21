# ruff: noqa: E501
"""CB18 part ``pre`` rules (docs/research_lab/CREATIVE_BATCH_18.md sections 2.3-2.6, 3, 4.1, 6, 12)."""

from __future__ import annotations

import json
import math

import pytest

from astrolabe.research_lab import cb18_rules_pre as r
from astrolabe.research_lab import ext_sidecar

NAN = math.nan


# ---- DE_gate, planning MDE, RS-1 / RS-2 / GP5 ----------------------------------------------------------------------


def test_de_gate_never_below_three_and_nan_fails():
    assert r.de_gate(1.0, 14, 2) == 3.0  # computed 1.12 -> floor 3
    assert r.de_gate(50.0, 14, 2) == pytest.approx(1 + (50 * 7 - 1) * 0.02)  # 7.98 raises the floor
    assert math.isnan(r.de_gate(NAN, 14, 2))
    assert math.isnan(r.de_gate(0.0, 14, 2))
    assert r.de_computed(2.0, 28, 2) == pytest.approx(1 + (2 * 14 - 1) * 0.02)
    assert r.m_by_event([1, 1, 2]) == pytest.approx((1 + 1 + 4) / 4)
    assert math.isnan(r.m_by_event([]))
    assert r.mde_formula(r.M_CB, 6.0, 1400, 1e12, 2.0) != r.mde_formula(r.M_CB, 6.0, 1400, 1e12, 3.0)
    assert math.isnan(r.mde_formula(r.M_CB, 6.0, 1400, 1e12, 2.0))  # a DE below the floor is refused
    assert math.isnan(r.mde_formula(r.M_CB, 6.0, 1400, 1e12, NAN))


def test_planning_numbers_reproduce_the_design():
    # section 3.1: 200 silent a day, 1,400 per arm, SD 6c, DE 3, the 1.5 factor
    assert r.mde_formula(r.M_CB, 6.0, 1400, 1e15, 3.0) == pytest.approx(1.58, abs=0.005)
    assert r.mde_formula(r.M_CB, 6.0, 1400, 5600, 3.0) == pytest.approx(1.77, abs=0.005)
    assert r.mde_formula(r.M_CB, 6.0, 1400, 1400, 3.0) == pytest.approx(2.24, abs=0.005)
    assert r.mde_formula(r.M_LT, 6.0, 5600, 1e15, 3.0) == pytest.approx(0.71, abs=0.005)
    assert r.mde_formula(r.M_LT, 6.0, 5600, 5600, 3.0) == pytest.approx(1.00, abs=0.005)
    # section 4.2: P at 1,680 / 3,360 fades, none = 1.5 F, SD 5c
    assert r.mde_formula(r.M_LT, 5.0, 1680, 2520, 3.0) == pytest.approx(1.39, abs=0.005)
    assert r.mde_formula(r.M_LT, 5.0, 3360, 5040, 3.0) == pytest.approx(0.98, abs=0.005)


def test_rs1_rs2_formulas_with_inflation_floor_and_pessimism():
    se, days = 0.5, 2.0
    de_c = r.de_computed(1.5, 2, 2)
    de14 = r.de_computed(1.5, 14, 2)
    want1 = 3.80 * se * math.sqrt(2 / 14) * math.sqrt(2) * math.sqrt(3.0) * 1.5  # ratio < 3 -> sqrt(3)
    assert r.mde_rs1(se, days, de14, de_c) == pytest.approx(want1)
    de28 = r.de_computed(1.5, 28, 2)
    want2 = 3.388 * se * math.sqrt(2 / 28) * math.sqrt(3.0) * 1.5
    assert r.mde_rs2(se, days, de28, de_c) == pytest.approx(want2)
    big = r.de_computed(400.0, 28, 2)
    assert r.de_inflation(big, r.de_computed(400.0, 2, 2)) > math.sqrt(3.0)
    assert r.de_inflation(1.0, 10.0) == pytest.approx(math.sqrt(3.0))
    for bad in (NAN, 0.0, -1.0):
        assert math.isnan(r.mde_rs1(bad, days, de14, de_c))
        assert math.isnan(r.mde_rs2(bad, days, de28, de_c))
    assert math.isnan(r.mde_rs1(se, days, NAN, de_c))


def test_gp5_is_the_max_rule():
    assert r.mde_gp5(0.4, 0.7) == 0.7
    assert r.mde_gp5(0.9, 0.3) == 0.9
    assert r.mde_gp5(0.4, NAN) == 0.4  # NaN proxy -> formula alone
    assert math.isnan(r.mde_gp5(NAN, 0.2))  # NaN formula fails
    p = r.mde_gp5_proxy(1.0, r.de_computed(1.0, 28, 2), r.de_computed(1.0, 2, 2))
    assert p == pytest.approx(3.388 * math.sqrt(21 / (28 * 12)) * math.sqrt(3.0) * 1.5)
    g = r.gp_gates({"fades_28d_projected": 3000, "fade_share_of_reacted": 0.5, "side_unusable_share": 0.01, "truncated_share": 0.0, "mde_gp5_c": NAN, "gp6_level": 0})
    assert g["GP5"] is False and g["GP1"] is True


def test_gates_fail_closed_and_route_s():
    good = {"gs1_share": 0.1, "gs2_share": 0.1, "gs3_share": 0.01, "gs4_silent_per_day": 600, "gs5_level_cb": 0, "gs5_level_lt": 1}
    g = r.gs_gates(good)
    assert all(g.values())
    assert r.route_s(g, 0.9, 0.5)["route"] == "RS-1"
    assert r.route_s(g, 1.2, 0.5)["route"] == "RS-2"
    assert r.route_s(g, 1.2, 1.1)["route"] == "RS-3"
    assert r.route_s(g, NAN, NAN)["route"] == "RS-3"
    rec = r.route_s(g, 1.2, 0.5)
    assert rec["mde_rs1_c"] == 1.2 and rec["mde_rs2_c"] == 0.5  # both written whatever the route
    for k, bad in (("gs1_share", 0.51), ("gs2_share", NAN), ("gs3_share", None), ("gs4_silent_per_day", 199.9)):
        gg = r.gs_gates({**good, k: bad})
        assert r.route_s(gg, 0.1, 0.1)["route"] == "RS-0"
    only_lt = r.gs_gates({**good, "gs5_level_cb": None})
    assert r.route_s(only_lt, 0.1, 0.5)["route"] == "RS-2"  # RS-1 needs GS5 at q_CB
    none5 = r.gs_gates({**good, "gs5_level_cb": None, "gs5_level_lt": None})
    assert r.route_s(none5, 0.1, 0.1)["route"] == "RS-0"
    assert r.gate_le(None, 1) is False and r.gate_ge(NAN, 1) is False


def test_route_p():
    ok = {f"GP{i}": True for i in range(1, 7)}
    assert r.route_p(ok, ok)["population"] == "non-sports"
    assert r.route_p({**ok, "GP5": False}, ok)["population"].startswith("all categories")
    assert r.route_p({**ok, "GP5": False}, {**ok, "GP1": None})["route"] == "dropped uncounted"


def test_thin_rate_and_hashes():
    assert r.thin_rate(1000, 10000, 2, 14) == 1.0
    assert r.thin_rate(50_000, 400_000, 2, 14) == 0.25  # (50k + q 400k) x 7 <= 1.5M -> q <= 0.41
    assert r.thin_rate(300_000, 0, 2, 14) is None  # silent alone exceeds the cap
    assert r.thin_rate(NAN, 1, 2, 14) is None
    u = r.thin_u("123", "2026-10-15T00:31:00Z")
    assert 0 <= u < 1 and u == r.thin_u("123", "2026-10-15T00:31:00Z")
    assert r.thin_keep("123", "2026-10-15T00:31:00Z", 1.0) is True
    assert r.thin_keep("123", "2026-10-15T00:31:00Z", None) is False
    keep = sum(r.thin_keep(str(i), "2026-10-15T00:31:00Z", 0.25) for i in range(4000))
    assert 850 < keep < 1150
    assert r.arm_of("e1") in (0, 1) and r.arm_of("e1") == r.arm_of("e1")


# ---- class rules ---------------------------------------------------------------------------------------------------


def test_silent_quiet_truth_table():
    recv = 1_000_000_000.0
    assert r.s_class(500.0, 500.0, recv) == "quiet"
    assert r.s_class(500.0, 600.0, recv) == "silent"
    assert r.s_class(600.0, 500.0, recv) == "upd_earlier"
    assert r.s_class(500.0, recv + 5000.0, recv) == "silent"  # exactly receipt + 5 s
    assert r.s_class(500.0, recv + 5001.0, recv) == "upd_after_receipt"
    assert r.s_class(NAN, 500.0, recv) == "upd_missing"
    assert r.s_class(500.0, NAN, recv) == "upd_missing"


def test_chg_flag_status_is_exclusive():
    assert r.chg_flag_status(True, True, True) == "none"
    assert r.chg_flag_status(False, True, True) == "1h_only"
    assert r.chg_flag_status(True, False, True) == "1d_or_1w_not_all"
    assert r.chg_flag_status(False, True, False) == "1d_or_1w_not_all"
    assert r.chg_flag_status(False, False, False) == "all_three"


def test_book_untouched_edges():
    t_prev = 1000.0
    assert r.book_untouched(1_000_000.0, NAN, t_prev) is True  # stamp exactly at t_{k-1}; outcome-1 missing -> outcome-0 only
    assert r.book_untouched(1_000_001.0, NAN, t_prev) is False
    assert r.book_untouched(999_000.0, 1_000_500.0, t_prev) is False
    assert r.book_untouched(NAN, 1.0, t_prev) is None


def test_uma_empty_literal_fixed_from_the_writer():
    assert ext_sidecar._text([]) is not None and json.loads(ext_sidecar._text([])) == []
    assert ext_sidecar._text([]) == r.UMA_EMPTY_LITERAL
    assert ext_sidecar._text("[]") == r.UMA_EMPTY_LITERAL
    assert ext_sidecar._text(None) is None  # absent -> empty CSV field -> 'missing'
    assert r.uma_class("[]") == "empty_literal"
    assert r.uma_class("") == "missing" and r.uma_class(None) == "missing"
    assert r.uma_class('["proposed"]') == "non_empty"
    assert r.uma_class("[] ") == "non_empty"  # bytes, never parsed


def test_p_state_table():
    assert r.p_state(0.0, 0, 1) == "none"
    assert r.p_state(0.0, 3, 1) == "balanced"
    assert r.p_state(-5.0, 2, 1) == "fade"
    assert r.p_state(5.0, 2, 1) == "follow"
    assert r.p_state(5.0, 2, -1) == "fade"


def test_fold_band_records_no_side():
    for mid in (0.004, 0.996):
        assert r.fold_band(mid) == "d_gt_0.49"
    assert r.fold_band(0.03) == r.fold_band(0.97) == "d_0.45_0.49"
    assert r.fold_band(0.05) == r.fold_band(0.95) == "d_0.45_0.49"
    assert r.fold_band(0.5) == "d_lt_0.45"
    assert r.fold_band(NAN) == "no_two_sided"
    assert set(r.M_BANDS) >= {r.fold_band(x) for x in (0.0, 0.2, 0.47, NAN)}


def test_surge_label():
    assert r.surge_label(1600.0, 500.0) is True
    assert r.surge_label(1400.0, 500.0) is False
    assert r.surge_label(1600.0, 0.0) is None
    assert r.surge_label(NAN, 10.0) is None


# ---- strata ------------------------------------------------------------------------------------------------------


def test_permutable_share_and_selection():
    t = r.ep("2026-10-15T00:31:00Z")
    units = [(r.perm_stratum(0, "m1", t), lab) for lab in (0, 0, 1, 1)] + [(r.perm_stratum(0, "m2", t), lab) for lab in (0, 1, 1)]
    s = r.permutable_share(units)
    assert s["numerator"] == 4 and s["denominator"] == 7
    assert r.permutable_share([(("a",), 1)] * 5)["share"] == 0.0  # one label only
    assert r.select_level({0: 0.59, 1: 0.6, 2: 0.9}) == 1
    assert r.select_level({0: None, 1: NAN, 2: 0.2}) is None
    assert r.perm_stratum(2, "m", t) == ("m", r.block_index(t, 7))
    with pytest.raises(r.Refused):
        r.perm_stratum(3, "m", t)
    assert r.informative_share([(("a",), 1), (("a",), 0), (("b",), 1)])["share"] == pytest.approx(2 / 3)


# ---- refusals ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["x/live_trades/trades-20261015.jsonl", "x/creative_batch17/a.json", "x/history/h2_main/p.csv", "x/e003/a", "x/h15_flow/x",
                                 "x/creative_batch13/t_holdout/f.csv.gz", "x/trade_samples/20261016T004036Z_815f487b/wallets.csv.gz", "x/live_tests4/a"])
def test_refused_roots(bad):
    with pytest.raises(r.Refused):
        r.refuse_path(bad)


def test_allowed_restore_paths():
    for ok in ("../data-dumps/research_lab/cb18_census/restore/data-dumps/research_lab/snapshots/20261015T003101Z_363e9924/rows.csv.gz",
               "../data-dumps/research_lab/cb18_census/restore/data-dumps/research_lab/trade_samples/20261016T004036Z_815f487b/trades.csv.gz"):
        r.refuse_path(ok)


def test_census_cutoffs_and_floor():
    r.guard_census_time(r.ep("2026-10-17T22:36:00Z"))
    r.guard_census_time(r.ep("2026-10-17T23:01:00Z"))
    with pytest.raises(r.Refused):
        r.guard_census_time(r.ep("2026-10-17T23:01:01Z"))
    with pytest.raises(r.Refused):
        r.guard_census_time(r.ep("2026-10-22T00:00:00Z"))  # HOLDOUT
    with pytest.raises(r.Refused):
        r.guard_census_time(NAN)
    r.guard_census_time(r.ep("2026-10-15T23:59:59Z"), cutoff=r.MAP_CUTOFF)
    with pytest.raises(r.Refused):
        r.guard_census_time(r.ep("2026-10-16T00:00:00Z"), cutoff=r.MAP_CUTOFF)  # the map's cut-off is exclusive
    with pytest.raises(r.Refused):
        r.guard_window_time(r.ep("2026-10-25T22:31:00Z"))  # the old k - 13 of the first SCREEN_18 origin
    r.guard_window_time(r.ep("2026-10-26T00:31:00Z"))  # k - 12


def test_result_writer_refuses_outcome_keys(tmp_path):
    for key in ("beta_silent", "mark", "target_status", "chg_1h", "tx_hash", "outcome_band", "coef", "pnl_c", "wallet_n", "net", "last_mid", "return_24h"):
        with pytest.raises(r.Refused):
            r.assert_clean_result({"counts": {key: 1}})
    r.assert_clean_result({"markets_n": 1, "se_proxy_c": 0.1, "mde_rs1_c": 1.0, "netted": None, "returned_n": 3})
    out = tmp_path / "cb18_census" / "S.json"
    sha = r.write_result_once(out, {"n": 1, "share": NAN})
    assert len(sha) == 64 and json.loads(out.read_text())["share"] is None
    with pytest.raises(r.Refused):
        r.write_result_once(out, {"n": 2})  # write-once
    with pytest.raises(r.Refused):
        r.write_result_once(tmp_path / "elsewhere" / "S.json", {"n": 1})


# ---- pins and the rules file -------------------------------------------------------------------------------------


def test_pins_hold_and_a_changed_pin_refuses(monkeypatch):
    got = r.verify_pins()
    assert set(got) == set(r.PINNED_IMPORTS)
    monkeypatch.setitem(r.PINNED_IMPORTS, "live_tests3.classify", "0" * 64)
    with pytest.raises(r.Refused):
        r.verify_pins()


def test_rules_file_roundtrip(tmp_path):
    p = r.write_rules(tmp_path / "cb18_rules.json")
    doc = json.loads(p.read_text())
    assert doc["parts"]["pre"]["part_declared"] is True
    assert doc["parts"]["common"]["part_declared"] is False and doc["parts"]["S"]["part_declared"] is False
    assert "J4R_DISCLOSURE" in doc["parts"]["pre"]["constants"]["cb18_rules_pre"]
    assert "GP5_RULE" in doc["parts"]["pre"]["constants"]["cb18_rules_pre"]
    assert r.verify_rules(p, require_committed=False) == doc["parts"]["pre"]["rules_sha256"]
    with pytest.raises(r.Refused):
        r.verify_rules(p, require_committed=False, part="S")
    bad = json.loads(p.read_text())
    bad["parts"]["pre"]["constants"]["cb18_rules_pre"]["GS1_MAX"] = 0.6
    p.write_text(json.dumps(bad))
    with pytest.raises(r.Refused):
        r.verify_rules(p, require_committed=False)
    with pytest.raises(r.Refused):
        r.write_rules(p)  # a declared part is never rewritten
