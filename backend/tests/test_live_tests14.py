# ruff: noqa: E501
"""LT14 census building blocks (LIVE_TESTS_14.md 1.3, 1.5, 1.6, 3): pins and refusals, the input-clock audit, the exclusion order, the |s| decile and its tie-break, tiers, outcome classes,
the fee-class split SUMMED across captures (the CH269 defect), LT13's aliasing rule, and the no-later-price guard. Synthetic only (tmp paths); the real trials.jsonl is never opened."""

from __future__ import annotations

import ast
import inspect
import json
import math
import shutil

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests14 as lt
from astrolabe.research_lab import live_tests14_base as t
from tests import lt14_synth as sx

TRIALS = t.ROOT / "docs" / "research_lab" / "trials.jsonl"
TRIALS_SHA0 = t.b.sha256_file(TRIALS) if TRIALS.exists() else None


def _reg_sha(model_id: str) -> str:
    return next(m["spec_sha256"] for m in json.loads((t.SPEC_DIR / "registry.json").read_text())["models"] if m["model_id"] == model_id)


def test_pins_are_the_frozen_values_and_the_real_design_file_hashes_to_them(tmp_path):
    assert t.DESIGN_TEXT_SHA256 == "f047c00059ebffd0fe81dd76b6615969d0a127c593aacee0291971fd0e52f815"
    assert t.PINNED_MODEL == "se0_champion_lr_mm" and t.PINNED_SPEC_SHA256 == "19549cb403b41de6974a8f3e7acf7378baf433779b16cae46d367fe6fb5ff919"
    assert t.DECLARED["pinned_model"]["spec_sha256"] == t.PINNED_SPEC_SHA256
    led = sx.write_ledger(tmp_path / "L.md")
    assert t.design_text_error(None, led) is None


def test_design_text_and_ledger_refusals(tmp_path):
    d = tmp_path / "LIVE_TESTS_14.md"
    d.write_text(t.DESIGN_PATH.read_text() + "\nx")
    led = sx.write_ledger(tmp_path / "L.md")
    assert "differs from the text-frozen" in t.design_text_error(d, led)["error"]
    led.write_text("nothing\n")
    assert "no 'LT14 DESIGN TEXT FROZEN' line" in t.design_text_error(None, led)["error"]
    led.write_text(f"- **{t.LEDGER_FREEZE_MARKER}:** sha256 `{t.DESIGN_TEXT_SHA256}`\n")
    assert "Pinned" in t.design_text_error(None, led)["error"]


def test_the_declared_constants_hash_is_stable_and_imported_pins_hold():
    assert t.declaration_sha256() == t.declaration_sha256()
    assert t.imported_error() is None
    mutated = json.loads(json.dumps(t.DECLARED))
    mutated["horizon"]["tol_s"] = 901.0
    assert t._canon(mutated) != t._canon(t.DECLARED)


def test_the_real_pinned_model_passes_the_input_clock_audit_and_others_are_refused(tmp_path):
    au = t.audit_input_clock()
    assert au["pass"], au["reasons"]
    assert au["families"] == ["market_state", "momentum"]
    sd = tmp_path / "specs"
    shutil.copytree(t.SPEC_DIR, sd)
    spec = json.loads((sd / "se0_champion_lr_mm.json").read_text())
    spec["families"] = ["market_state", "momentum", "flow"]
    (sd / "se0_champion_lr_mm.json").write_text(json.dumps(spec))
    bad = t.audit_input_clock(sd)
    assert not bad["pass"] and any("canonical sha256" in r for r in bad["reasons"]) and any("flow" in r for r in bad["reasons"])
    d2 = json.loads(json.dumps(t.DECLARED["pinned_model"]))
    r18 = t.audit_input_clock(t.SPEC_DIR, {**d2, "model_id": "se18_lgbm_all_b0", "spec_sha256": _reg_sha("se18_lgbm_all_b0")})
    assert not r18["pass"] and any("flow" in x for x in r18["reasons"]) and any("wallet" in x for x in r18["reasons"])
    r13 = t.audit_input_clock(t.SPEC_DIR, {**d2, "model_id": "se13_lgbm_xvenue", "spec_sha256": _reg_sha("se13_lgbm_xvenue")})
    assert not r13["pass"] and any("xvenue" in x for x in r13["reasons"])
    r1 = t.audit_input_clock(t.SPEC_DIR, {**d2, "model_id": "se1_lgbm_mm", "spec_sha256": _reg_sha("se1_lgbm_mm")})
    assert r1["pass"]  # the designer's pre-audit: se1 / se17 are market_state + momentum only (they are simply not the pinned P)


def test_check_blocks_refuses_gross_later_prices_and_other_tests():
    t.check_blocks(("CH262",))
    for bad in ("gross", "gbar", "k+1 target", "LT13", "M1 slope", "m2", "placebo", "twin"):
        with pytest.raises(t.Refused):
            t.check_blocks((bad,))
    with pytest.raises(t.Refused):
        t.check_blocks(("CH999",))


# --- exclusions, decile, tiers ---------------------------------------------------------------------------------------------------------------------------


def _frame(n: int, feat=None, pred=None, ext=None):
    ids = np.arange(1, n + 1)
    f = pd.DataFrame({"market_id": ids.astype(np.int64), "event_id": np.arange(n, dtype=np.int64) // 2, "category": "politics", "t_row": 1.0e9 + np.arange(n, dtype=float), "end_ts": np.nan,
                      "ms_mid": np.full(n, 0.5, np.float32), "ms_spread": np.full(n, 0.02, np.float32), "ms_log_liq": np.log1p(np.full(n, 20000.0)).astype(np.float32),
                      "ms_hours_to_end": np.full(n, 100.0, np.float32), "ms_rv24": np.full(n, 0.01, np.float32), "ms_tick": np.full(n, 0.01, np.float32), "ms_neg_risk": np.zeros(n, np.float32),
                      "mo_d2h": np.zeros(n, np.float32)})
    p = pd.DataFrame({"elig": np.ones(n, np.uint8), "dir_2h_dn": np.zeros(n, np.uint16), "dir_2h_up": (np.arange(n) + 1).astype(np.uint16)})
    q = pd.DataFrame({"market_id": ids.astype(np.int64), "t_off": np.full(n, 60.0, np.float32), "bid": np.full(n, 0.49, np.float32), "ask": np.full(n, 0.51, np.float32), "st": np.zeros(n, np.int8)})
    e = pd.DataFrame({"fee_type": "politics_fees", "fee_category": "politics", "series_slugs": '["f"]', "fee_schedule": sx.FEE_ON, "fees_enabled": "true"}, index=pd.Index(ids, name="market_id"))
    e.attrs["has_fees_enabled"] = True
    if feat:
        feat(f)
    if pred:
        pred(p)
    if ext:
        e = ext(e)
    return f, p, q, e


def test_exclusions_run_in_the_declared_order_and_each_step_is_counted():
    def mod_feat(f):
        f.loc[3, "ms_log_liq"] = np.nan  # tier_na
        f.loc[5, "market_id"] = f.loc[4, "market_id"]  # duplicate (market 5 appears twice, row 5 dropped)

    def mod_pred(p):
        p.loc[1, "elig"] = 0  # not dir_2h eligible
        p.loc[2, "dir_2h_up"] = 0  # s_zero

    def mod_ext(e):
        e = e.drop(index=[7])  # sidecar missing
        e.loc[8, ["fee_type", "fee_category"]] = ["sports_fees", "sports"]
        e.loc[9, ["fee_type", "fee_category"]] = ["crypto_fees", "crypto"]
        e.attrs["has_fees_enabled"] = True
        return e

    feat, pred, quo, ext = _frame(20, mod_feat, mod_pred, mod_ext)
    C, steps, pre = t.candidates(feat, pred, quo, ext)
    assert steps["rows"] == 20 and steps["not_dir2h_eligible"] == 1 and steps["duplicate_market"] == 1 and steps["sidecar_missing"] == 1
    assert steps["scope_sports"] == 1 and steps["scope_crypto_or_unknown"] == 1 and steps["tier_na"] == 1 and steps["s_zero"] == 1
    assert steps["candidates"] == 20 - 1 - 1 - 1 - 2 - 1 - 1 == len(C)
    assert set(pre["label"]) >= {"sports", "crypto", "non_crypto"}


def test_decile_is_ceil_n_over_10_by_abs_s_with_market_id_tiebreak():
    def mod_pred(p):
        p["dir_2h_up"] = np.array([100] * 5 + [50] * 18, np.uint16)
        p.loc[0, "dir_2h_up"], p.loc[0, "dir_2h_dn"] = 0, 100  # a DOWN call with |s| equal to the up ties: the sign must not matter to the order

    feat, pred, quo, ext = _frame(23, pred=mod_pred)
    C, _, _ = t.candidates(feat, pred, quo, ext)
    d = t.deciles(C)
    assert d["n_top"] == 3 == t.top_count(23)  # ceil(23 / 10)
    assert list(C.iloc[d["top"]]["market_id"]) == [1, 2, 3]  # ties by market_id ascending, the down call included
    R = C.iloc[::-1].reset_index(drop=True)
    d2 = t.deciles(R)
    assert sorted(R.iloc[d2["top"]]["market_id"]) == [1, 2, 3]  # input row order does not matter
    assert t.top_count(100) == 10 and t.top_count(101) == 11 and t.top_count(1) == 1


def test_signed_decile_differs_from_abs_decile_when_a_down_call_is_strongest():
    def mod_pred(p):
        p["dir_2h_up"], p["dir_2h_dn"] = np.uint16(1), np.uint16(0)
        p.loc[0, "dir_2h_dn"] = 900  # strongest call is DOWN
        p.loc[1, "dir_2h_up"] = 500

    feat, pred, quo, ext = _frame(20, pred=mod_pred)
    C, _, _ = t.candidates(feat, pred, quo, ext)
    a, s = t.deciles(C), t.deciles(C, signed=True)
    assert C.iloc[a["top"][0]]["market_id"] == 1 and C.iloc[s["top"][0]]["market_id"] == 2


def test_middle_deciles_are_positions_three_to_six_tenths():
    feat, pred, quo, ext = _frame(100)
    C, _, _ = t.candidates(feat, pred, quo, ext)
    d = t.deciles(C)
    assert d["n_top"] == 10 and len(d["middle"]) == 30 and set(d["middle"]).isdisjoint(set(d["top"]))
    assert len(d["rest"]) == 90


def test_tier_cuts_use_expm1_of_the_stored_float32_and_lower_edge_inclusive():
    liq = np.array([999.0, 1000.5, 9999.0, 10000.5, 99999.0, 100000.5], dtype=np.float64)
    ll = np.log1p(liq).astype(np.float32)
    assert list(t.tier_codes(ll)) == [0, 1, 1, 2, 2, 3]
    assert t.tier_codes(np.array([np.nan], np.float32))[0] == -1


def test_gross_spread_and_mid_fields_come_from_quotes_at_k_only():
    feat, pred, quo, ext = _frame(12)
    C, _, _ = t.candidates(feat, pred, quo, ext)
    assert np.allclose(C["spread_c"], 2.0, atol=1e-4)  # ask_k - bid_k, not ms_spread
    assert (np.abs(C["mid_k"] - C["ms_mid"].astype(np.float64)) <= 1e-6).all()


# --- outcome classes at k + 1 ----------------------------------------------------------------------------------------------------------------------


def test_classify_next_gives_exactly_one_class_per_unit_and_never_reads_a_price():
    ids = np.arange(1, 9)
    t_row = np.full(8, 1000.0)
    nxt = pd.DataFrame({"market_id": [1, 2, 3, 4, 5, 6], "t_off": [100.0, 100.0, 100.0, 100.0, 100.0, 4000.0], "st": [0, 1, 2, 3, 0, 0]})
    start_next = 1000.0 + 7200.0 - 100.0  # market 1: exactly 2 h; market 6: far off
    out = t.classify_next(ids, t_row, nxt, start_next)
    assert list(out[:6]) == ["labelled", "unavailable_closed", "unavailable_inactive", "unavailable_one_sided", "labelled", "unavailable_timing"]
    assert list(out[6:]) == ["unavailable_absent", "unavailable_absent"]
    assert set(t.classify_next(ids, t_row, None, None)) == {"unavailable_missing_capture"}
    with pytest.raises(t.Refused):
        t.classify_next(ids, t_row, nxt.assign(bid=0.5), start_next)
    assert set(out) <= set(t.CLASSES)


def test_horizon_rule_boundary_is_inclusive_at_fifteen_minutes():
    ids, t_row = np.array([1, 2]), np.array([0.0, 0.0])
    nxt = pd.DataFrame({"market_id": [1, 2], "t_off": [0.0, 0.0], "st": [0, 0]})
    assert list(t.classify_next(ids, t_row, nxt, 7200.0 + 900.0)) == ["labelled"] * 2
    assert list(t.classify_next(ids, t_row, nxt, 7200.0 + 901.0)) == ["unavailable_timing"] * 2


def test_engine_reader_refuses_a_later_slot_price_and_an_unsealed_file(tmp_path):
    w = sx.make_world(tmp_path, range(0, 4), n_markets=20)
    slots = {k: sx.cap_id(k) for k in range(0, 4)}
    rd = t.EngineReader(w["engine"], w["snaps"], slots)
    assert set(rd.quotes(1, 2, ["market_id", "t_off", "st"]).columns) == {"market_id", "t_off", "st"}
    for cols in (["bid"], ["market_id", "ask"], ["market_id", "t_off", "st", "bid"]):
        with pytest.raises(t.Refused):
            rd.quotes(1, 2, cols)
    assert {"bid", "ask"} <= set(rd.quotes(1, 1, ["market_id", "bid", "ask"]).columns)  # the origin's own prices are origin-side
    rd2 = t.EngineReader(w["engine"], w["snaps"], slots, allowed={f"quotes/{sx.cap_id(1)}.parquet"})
    rd2.quotes(1, 1, ["market_id"])
    with pytest.raises(t.Refused):
        rd2.features(1, ["market_id"])


def test_no_code_path_forms_g_or_imports_forbidden_modules():
    src = inspect.getsource(lt) + inspect.getsource(t)
    names = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
    assert not {n for n in names if "gross" in n or n.startswith("g_") or "outcome" in n}
    imports = "\n".join(ln for ln in src.splitlines() if ln.startswith(("import ", "from ")))
    for banned in ("live_tests11", "live_tests13", "live_tests10", "signal_engine", "costs", "copy_skilled", "wallet_skill", "census_map_ch269", "ch245", "ch244"):
        assert banned not in imports
    assert "mid_k1" not in src and "ask_k1" not in src and "bid_k1" not in src


# --- the fee-class split is SUMMED across captures (the CH269 defect) ---------------------------------------------------------------------------------------


def test_fee_class_split_sums_across_captures_and_a_dict_comprehension_would_not():
    feat1, pred1, quo1, ext1 = _frame(40)
    feat2, pred2, quo2, ext2 = _frame(60, ext=lambda e: e.assign(fee_schedule=sx.FEE_FREE))
    c1, _, _ = t.candidates(feat1, pred1, quo1, ext1)
    c2, _, _ = t.candidates(feat2, pred2, quo2, ext2)
    s1 = t.fee_split(c1, t.deciles(c1)["top"])
    s2 = t.fee_split(c2, t.deciles(c2)["top"])
    assert s1 == {"10k-100k/fee_on": 4} and s2 == {"10k-100k/fee_free": 6}
    assert t.sum_fee_splits([s1, s2]) == {"10k-100k/fee_on": 4, "10k-100k/fee_free": 6}
    same = t.sum_fee_splits([s1, s1])
    assert same == {"10k-100k/fee_on": 8}  # a last-capture-wins comprehension gives 4
    wrong = {k: v for row in [s1, s1] for k, v in row.items()}  # the CH269 defect (census_map_ch269.py:951-952)
    assert wrong != same


# --- LT13's aliasing rule with LT14's drop order ------------------------------------------------------------------------------------------------------------


def _design(n=400, seed=1, **extra) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({c: rng.normal(size=n) for c in t.DECLARED["m6"]["controls"]})
    d["D"] = rng.normal(size=n)
    for k_, v in extra.items():
        d[k_] = v(d)
    return d


def test_full_rank_design_keeps_every_control_and_D():
    r = t.resolve_aliased_controls14(_design(), "D", t.DECLARED["m6"]["controls"])
    assert r["status"] == "ok" and r["dropped"] == [] and r["rank"] == r["n_cols"] == len(t.DECLARED["m6"]["controls"])


def test_drop_order_slot_dummies_latest_first_then_hte_unknown_rv_missing_hours_absmid():
    cols = t.DECLARED["m6"]["controls"]
    assert t.drop_order14(cols)[:11] == [f"sd{i}" for i in range(11, 0, -1)]
    assert t.drop_order14(cols)[11:] == ["hte_unknown", "rv_missing", "log1p_hte", "absmid"]
    r = t.resolve_aliased_controls14(_design(sd11=lambda x: x["sd10"] + x["sd9"]), "D", cols)
    assert r["status"] == "ok" and r["dropped"] == ["sd11"]
    r = t.resolve_aliased_controls14(_design(absmid=lambda x: x["log1p_hte"] * 2.0), "D", cols)
    assert r["status"] == "ok" and r["dropped"] == ["log1p_hte"]  # of an exactly collinear pair the one EARLIER in the declared order goes (absmid is last in the order)
    assert "D" not in r["dropped"]


def test_unlisted_collinear_column_leaves_the_fit_unavailable_and_D_in_the_span_is_nan():
    cols = t.DECLARED["m6"]["controls"]
    r = t.resolve_aliased_controls14(_design(mo_d2h=lambda x: 2 * x["spread_c"]), "D", cols)  # neither mo_d2h nor spread_c is in a drop group
    assert r["status"] == "unavailable" and "rank-deficient" in r["reason"]
    r = t.resolve_aliased_controls14(_design(D=lambda x: x["sd1"] + x["spread_c"]), "D", cols)
    assert r["status"] == "unavailable" and r["term_aliased"] is True


def test_zero_variance_demeaned_control_is_removed_and_reported_before_the_rank():
    r = t.resolve_aliased_controls14(_design(hte_unknown=lambda x: 0.0 * x["spread_c"]), "D", t.DECLARED["m6"]["controls"])
    assert r["zero_variance_dropped"] == ["hte_unknown"] and r["status"] == "ok"


# --- the other pieces --------------------------------------------------------------------------------------------------------------------------------


def test_gate_helper_fails_nan_and_kish_and_design_effect():
    assert t.gate(math.nan, lambda v: v > 0)["pass"] is False
    assert t.gate(5.0, lambda v: v >= 5)["pass"] is True
    assert abs(t.kish([1, 1, 1, 1]) - 4.0) < 1e-12 and t.kish([10, 1]) < 2.0
    assert abs(t.de_cluster([3, 3], 1.0, 0.02) - 1.04) < 1e-12


def test_trials_jsonl_is_never_touched():
    src = inspect.getsource(lt) + inspect.getsource(t)
    assert "trials.jsonl" not in src
    assert (t.b.sha256_file(TRIALS) if TRIALS.exists() else None) == TRIALS_SHA0
