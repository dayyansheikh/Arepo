# ruff: noqa: E501
"""LT13 stage A (LIVE_TESTS_13.md 1.4.4, 3.2-3.3, 6): the batch registry and join, the unit builder, the pseudo-batch rule, the twin-state loader and the aliased-controls rule,
on tiny synthetic stores (tmp paths; nothing real is read or written; ``trials.jsonl`` untouched)."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests12 as lt12
from astrolabe.research_lab import live_tests12_base as b
from astrolabe.research_lab import live_tests13 as lt
from astrolabe.research_lab import live_tests13_base as t
from tests import lt13_synth as sx

K0 = 20  # an origin well inside the synthetic tree


def prepare(tmp_path: Path, slots=range(0, 30), **kw):
    by = sx.make_world(tmp_path / "snap", slots, **kw)
    spec = sx.loose_spec()
    work = tmp_path / "w"
    store = t.SlotStore13(work, by, spec)
    reg = t.Registry()
    for k in sorted(by):
        t.write_series13(work, by[k], spec)
        reg.add(t.read_reg13(work, by[k]["id"]))
    return by, spec, store, reg


def units(tmp_path, k=K0, **kw):
    by, spec, store, reg = prepare(tmp_path, **kw)
    u, cnt = t.units13(store, reg.batches(), k, spec)
    return u, cnt, by, spec, store, reg


def innov_of(store: t.SlotStore13, ids, k=K0) -> dict:
    sk, sp = store.ser(k), store.ser(k - 1)
    return {m: round(float((sk.loc[m, "ask"] - sk.loc[m, "bid"]) - (sp.loc[m, "ask"] - sp.loc[m, "bid"])) * 100.0, 10) for m in ids}


# --- the registry and the chain (1.4.4) ------------------------------------------------------------------------------------------------------


def _reg(rows):
    r = t.Registry()
    r.add(pd.DataFrame(rows, columns=["market_id", "condition_id", "created", "ekey"]))
    return r


def test_chain_closes_when_the_next_creation_is_MORE_than_120_s_after_the_previous():
    r = _reg([("a", "c1", 1000.0, "e1"), ("b", "c2", 1120.0, "e2"), ("c", "c3", 1240.0, "e3"), ("d", "c4", 1361.0, "e4")])  # gaps 120, 120, 121
    bt = r.batches()
    assert list(bt.size) == [3, 1]
    assert bool(bt.cross[0]) and not bool(bt.cross[1])
    assert bt.n_events[0] == 3


def test_cross_event_needs_at_least_three_markets_and_two_event_keys():
    assert not _reg([("a", "c1", 1.0, "e"), ("b", "c2", 2.0, "e"), ("c", "c3", 3.0, "e")]).batches().cross[0]  # one event key
    assert not _reg([("a", "c1", 1.0, "e1"), ("b", "c2", 2.0, "e2")]).batches().cross[0]  # two markets
    assert _reg([("a", "c1", 1.0, "e1"), ("b", "c2", 2.0, "e1"), ("c", "c3", 3.0, "e2")]).batches().cross[0]


def test_batch_key_is_the_earliest_creation_and_the_smallest_condition_id_among_those_and_is_stable_when_a_later_member_joins():
    r = _reg([("a", "cz", 1000.0, "e1"), ("b", "ca", 1000.0, "e2"), ("c", "cm", 1050.0, "e3")])
    k0 = r.batches().key[0]
    assert k0.endswith("|ca")  # two members share the earliest created_at: the smaller condition_id names the batch
    r.add(pd.DataFrame([("d", "c9", 1100.0, "e4")], columns=["market_id", "condition_id", "created", "ekey"]))
    assert r.batches().key[0] == k0 and r.batches().size[0] == 4  # a later member joins: the key is unchanged
    r.add(pd.DataFrame([("e", "c0", 900.0, "e5")], columns=["market_id", "condition_id", "created", "ekey"]))
    assert r.batches().key[0] != k0  # an EARLIER member joins within 120 s: the batch is now named by it (documented, A5)


def test_the_registry_never_forgets_a_market():
    r = _reg([("a", "c1", 1.0, "e1"), ("b", "c2", 2.0, "e2")])
    r.add(pd.DataFrame([("z", "c9", 5.0, "e9")], columns=["market_id", "condition_id", "created", "ekey"]))  # a later capture that does not list a and b
    assert set(r.df.index) == {"a", "b", "z"}
    r.add(pd.DataFrame([("a", "c1", 1.0, "eNEW")], columns=["market_id", "condition_id", "created", "ekey"]))
    assert r.df.loc["a", "ekey"] == "eNEW" and len(r) == 3  # the event key is refreshed, no duplicate


def test_event_key_prefers_neg_risk_market_id_then_event_id_then_the_condition_id():
    ek = t.event_keys(["NR1", "", None, "nan"], ["E1", "E2", "", ""], ["c1", "c2", "c3", "c4"])
    assert list(ek) == ["NR1", "E2", "m:c3", "m:c4"]


# --- the unit builder on synthetic created_at (3.2) --------------------------------------------------------------------------------------------


def test_batch_join_follows_created_at_and_excludes_same_event_mates(tmp_path):
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=4, per_batch=6, n_events=3, singles=10)
    p = u[u["arm"] == "primary"]
    assert set(p["market_id"].str.split("_").str[0]) == {"b0", "b1", "b2", "b3"}  # singletons and the crypto market have no unit
    assert (p["n_mates"] == 4).all()  # 6 members, 2 in the unit's own event
    row = p[p["market_id"] == "b1_0"].iloc[0]
    ms = [f"b1_{j}" for j in range(6) if j % 3 != 0]  # events EB1_(j % 3): b1_0 and b1_3 share an event
    inn = innov_of(store, ms)
    assert row["mbar"] == pytest.approx(np.mean(list(inn.values())))
    assert row["own_ds_c"] == pytest.approx(innov_of(store, ["b1_0"])["b1_0"])
    assert p[p["batch_id"] == row["batch_id"]]["batch_members"].eq(6).all()


def test_a_121_s_creation_gap_splits_every_batch_and_a_120_s_gap_does_not(tmp_path):
    u120, *_ = units(tmp_path / "a", n_batches=3, created_gap_s=24.0, per_batch=6, singles=3)  # 5 gaps of 24 s: fine
    assert len(u120) > 0
    u_big, *_ = units(tmp_path / "b", n_batches=3, created_gap_s=121.0, per_batch=6, singles=3)
    assert len(u_big) == 0  # every creation is more than 120 s after the previous one: only singleton batches
    u_edge, *_ = units(tmp_path / "c", n_batches=3, created_gap_s=120.0, per_batch=6, singles=3)
    assert len(u_edge) > 0  # exactly 120 s chains


def test_a_batch_inside_one_event_gives_no_unit(tmp_path):
    u, *_ = units(tmp_path, n_batches=3, per_batch=6, same_event_batches=(0,), singles=3)
    assert "b0" not in set(u["market_id"].str.split("_").str[0]) and "b1" in set(u["market_id"].str.split("_").str[0])


def test_the_cap_is_30_complete_cross_event_mates_above_it_is_the_reported_arm(tmp_path):
    u31, c31, *_ = units(tmp_path / "a", n_batches=1, per_batch=31, n_events=31, singles=2)  # 30 mates each: primary
    assert (u31["arm"] == "primary").all() and (u31["n_mates"] == 30).all()
    u32, c32, *_ = units(tmp_path / "b", n_batches=1, per_batch=32, n_events=32, singles=2)  # 31 mates: the > 30 arm
    assert (u32["arm"] == "gt30").all() and c32["gt30_units"] == 32 and c32.get("units_primary", 0) == 32 - 32


def test_a_batch_capture_below_60_percent_complete_gives_no_unit_and_is_counted(tmp_path):
    drop = {f"b0_{j}": {K0} for j in range(3)}  # 3 of 6 members absent at k: 50% complete
    u, cnt, *_ = units(tmp_path / "a", n_batches=2, per_batch=6, singles=3, drop=drop)
    assert "b0" not in set(u["market_id"].str.split("_").str[0]) and "b1" in set(u["market_id"].str.split("_").str[0])
    assert cnt["batch_incomplete_units"] >= 1
    u2, *_ = units(tmp_path / "b", n_batches=2, per_batch=6, singles=3, drop={f"b0_{j}": {K0} for j in range(2)})  # 4 of 6 = 66.7%: kept
    assert "b0" in set(u2["market_id"].str.split("_").str[0])


def test_the_120_s_receipt_rule_drops_a_late_mate_and_a_late_unit(tmp_path):
    u, cnt, store = None, None, None
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=2, per_batch=6, singles=3, drop={("late", "b0_1"): True})
    assert "b0_1" not in set(u["market_id"]) and cnt["receipt_span_units"] >= 1
    row = u[u["market_id"] == "b0_0"].iloc[0]
    assert row["n_mates"] == 3  # b0_1 (another event than b0_0) is dropped from the mate set
    inn = innov_of(store, ["b0_2", "b0_4", "b0_5"])
    assert row["mbar"] == pytest.approx(np.mean(list(inn.values())))


def test_unit_builders_never_read_a_slot_after_k_and_the_store_refuses_one(tmp_path):
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=2, per_batch=6, singles=3)
    assert max(store.reads) <= K0
    assert store.limit == K0
    with pytest.raises(t.Refused, match="causality"):
        store.ser(K0 + 1)
    with pytest.raises(t.Refused):
        store.t_dec(K0 + 2)


def test_decision_time_is_capture_k_last_receipt_and_no_target_column_exists(tmp_path):
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=2, per_batch=6, singles=3)
    assert (u["t_row"] == lt12.capture_last_receipt(by[K0]["dir"])).all()
    forbidden = {c for c in u.columns if c.startswith(("ds_", "tgt", "target", "out_", "y_")) or c in {"ds", "spread_k1", "spread_next"}}
    assert not forbidden


def test_cbar_is_the_category_mean_innovation_outside_the_units_batch(tmp_path):
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=4, per_batch=6, singles=12)
    row = u[u["market_id"] == "b0_0"].iloc[0]
    sk = store.ser(K0)
    # every non-crypto series market passes the synthetic quote rules at k - 1 and k: they are all eligible complete units of capture k
    pool = [m for m in sk.index if m != "x0" and not m.startswith("b0_") and sk.loc[m, "fee_cat"] == row["cat"]]
    inn = innov_of(store, pool)
    assert len(pool) > 5
    assert row["cbar"] == pytest.approx(np.mean(list(inn.values())))
    other = u[u["market_id"] == "b0_1"].iloc[0]  # same batch: the same factor (the factor is over non-batch units of the category)
    assert other["cbar"] == pytest.approx(row["cbar"]) if other["cat"] == row["cat"] else True


# --- the pseudo-batch (rule 21) -------------------------------------------------------------------------------------------------------------


def _el(n=100, seed=3):
    rng = np.random.default_rng(seed)
    day = 86400.0
    return pd.DataFrame({"condition_id": [f"c{i:03d}" for i in range(n)], "cat": ["A"] * n, "created": 1e9 + rng.permutation(n) * 10 * day, "ekey": [f"e{i}" for i in range(n)],
                         "fam": [f"f{i % 7}" for i in range(n)], "batch": [str(i) for i in range(n)], "innov": rng.normal(0, 1, n)})


def test_pseudo_mates_are_the_first_m_in_sha256_order_that_pass_all_four_conditions():
    EL = _el()
    cap_id = "20261107T003100Z_syn"
    res = t.assign_pseudo_batch(EL, np.array([5]), np.array([3]), cap_id)
    created = EL["created"].to_numpy(float)
    cuts = np.quantile(created, [i / 10 for i in range(1, 10)])
    dec = np.searchsorted(cuts, created, side="right")
    order = sorted(range(len(EL)), key=lambda p: hashlib.sha256((EL["condition_id"][p] + cap_id).encode()).hexdigest())
    want = [p for p in order if EL["cat"][p] == EL["cat"][5] and dec[p] == dec[5] and abs(created[p] - created[5]) >= 7 * 86400 and EL["ekey"][p] != EL["ekey"][5]
            and EL["fam"][p] != EL["fam"][5] and EL["batch"][p] != EL["batch"][5]][:3]
    assert len(want) == 3 and res["mbar_pb"][0] == pytest.approx(EL["innov"].to_numpy(float)[want].mean())
    assert res["decile"][0] == dec[5] and not res["none"][0]


@pytest.mark.parametrize("what", ["category", "decile", "age", "batch", "event", "family"])
def test_each_pseudo_batch_condition_excludes_its_candidates(what):
    EL = _el(40)
    base = t.assign_pseudo_batch(EL, np.array([0]), np.array([1]), "cap")["mbar_pb"][0]
    assert np.isfinite(base)
    # find the candidate that was chosen, then break exactly one condition on it and check it is no longer chosen
    cap = "cap"
    created = EL["created"].to_numpy(float)
    cuts = np.quantile(created, [i / 10 for i in range(1, 10)])
    dec = np.searchsorted(cuts, created, side="right")
    order = sorted(range(len(EL)), key=lambda p: hashlib.sha256((EL["condition_id"][p] + cap).encode()).hexdigest())
    chosen = next(p for p in order if p != 0 and dec[p] == dec[0] and abs(created[p] - created[0]) >= 7 * 86400 and EL["ekey"][p] != EL["ekey"][0] and EL["fam"][p] != EL["fam"][0])
    E2 = EL.copy()
    if what == "category":
        E2.loc[chosen, "cat"] = "B"
    elif what == "age":
        E2.loc[chosen, "created"] = created[0] + 3 * 86400
    elif what == "batch":
        E2.loc[chosen, "batch"] = E2.loc[0, "batch"]
    elif what == "event":
        E2.loc[chosen, "ekey"] = E2.loc[0, "ekey"]
    elif what == "family":
        E2.loc[chosen, "fam"] = E2.loc[0, "fam"]
    elif what == "decile":
        E2.loc[chosen, "created"] = E2["created"].max() + 100 * 86400 if dec[0] != 9 else E2["created"].min() - 100 * 86400
    after = t.assign_pseudo_batch(E2, np.array([0]), np.array([1]), cap)["mbar_pb"][0]
    assert after != base or not np.isfinite(after)


def test_fewer_than_m_qualifying_candidates_gives_placebo_none():
    EL = _el(12)
    res = t.assign_pseudo_batch(EL, np.array([0]), np.array([40]), "cap")
    assert np.isnan(res["mbar_pb"][0]) and res["none"][0]


def test_pseudo_batch_reads_only_the_category_verbatim_so_other_zero_fees_is_a_literal_level(tmp_path):
    assert t.cat_verbatim("other:zero_fees") == "other:zero_fees" and t.cat_verbatim(None) == "unknown" and t.cat_verbatim(float("nan")) == "unknown" and t.cat_verbatim("Politics") == "Politics"
    EL = _el(100)
    EL.loc[EL.index[10:], "cat"] = "other:zero_fees"
    r = t.assign_pseudo_batch(EL, np.array([20]), np.array([2]), "cap")
    assert not r["none"][0]


# --- the twin-state loader (states only) ------------------------------------------------------------------------------------------------------------


def test_twin_state_is_the_mean_of_the_mates_spread_changes_over_k_plus_2_to_k_plus_3_and_one_number_per_unit(tmp_path):
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=3, per_batch=6, singles=4)
    ex = cnt.pop("_extras")
    p = u[u["arm"] == "primary"].reset_index(drop=True)
    tw = t.lag_twin_state(by[K0 + 2]["dir"], by[K0 + 3]["dir"], p, ex["batches"], spec)
    assert isinstance(tw, np.ndarray) and tw.dtype == float and tw.shape == (len(p),)
    row = p[p["market_id"] == "b2_0"].iloc[0]
    mates = [f"b2_{j}" for j in range(6) if j % 3 != 0]
    a = store.__class__(store.work, by, spec)  # a fresh store with no limit: the TEST reads the later slots to build the expectation
    sa, sb = a.ser(K0 + 2), a.ser(K0 + 3)
    want = np.mean([round(float((sb.loc[m, "ask"] - sb.loc[m, "bid"]) - (sa.loc[m, "ask"] - sa.loc[m, "bid"])) * 100.0, 10) for m in mates])
    assert tw[row.name] == pytest.approx(want)


def test_twin_state_is_nan_when_fewer_than_two_mates_are_complete_at_the_twin_slots(tmp_path):
    drop = {f"b0_{j}": {K0 + 3} for j in range(1, 6)}
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=2, per_batch=6, singles=3, drop=drop)
    # the builder only sees <= k, so the units exist; the loader reads k + 2, k + 3 and finds the batch thin there
    ex = cnt.pop("_extras")
    p = u[u["arm"] == "primary"].reset_index(drop=True)
    tw = t.lag_twin_state(by[K0 + 2]["dir"], by[K0 + 3]["dir"], p, ex["batches"], spec)
    b0 = p["market_id"].str.startswith("b0_").to_numpy()
    assert np.isnan(tw[b0]).all() and np.isfinite(tw[~b0]).any()


# --- the aliased-controls rule (3.3) ---------------------------------------------------------------------------------------------------------


def _D(**cols):
    return pd.DataFrame(cols)


def _rng_cols(n=200, names=("p_k", "own6", "log1p_liq"), seed=1):
    r = np.random.default_rng(seed)
    return {c: r.normal(size=n) for c in names}


def test_a_collinear_fee_category_dummy_set_drops_the_last_level_first():
    r = np.random.default_rng(0)
    n = 300
    a = (r.random(n) < 0.3).astype(float)
    bb = ((r.random(n) < 0.3) & (a == 0)).astype(float)
    D = _D(zs=r.normal(size=n), fc_0_a=a, fc_1_b=bb, fee_on=a + bb, **_rng_cols(n))
    res = t.resolve_aliased_controls(D, "zs", ["fc_0_a", "fc_1_b", "fee_on", "p_k", "own6", "log1p_liq"], {"fc_0_a": "a", "fc_1_b": "b"})
    assert res["status"] == "ok" and res["dropped"] == ["fc_1_b"]  # "b" is the last level in lexicographic order: dropped first
    assert res["rank"] == res["n_cols"] == 5 and res["n_cols_before"] == 6


def test_only_a_span_redundant_column_is_dropped_otherwise_the_next_is_tested():
    r = np.random.default_rng(1)
    n = 300
    sd1, sd2 = (r.random(n) < 0.4).astype(float), (r.random(n) < 0.4).astype(float)
    fa, fb = (r.random(n) < 0.3).astype(float), (r.random(n) < 0.3).astype(float)
    D = _D(zs=r.normal(size=n), fc_0_a=fa, fc_1_b=fb, fee_on=sd1 + sd2, sd1=sd1, sd2=sd2, **_rng_cols(n))
    res = t.resolve_aliased_controls(D, "zs", ["fc_0_a", "fc_1_b", "fee_on", "sd1", "sd2", "p_k", "own6", "log1p_liq"], {"fc_0_a": "a", "fc_1_b": "b"})
    assert res["dropped"] == ["fee_on"]  # the two fee_category dummies are NOT in a dependency: kept; the fee-class dummy is (group 2 before the slot dummies)


def test_slot_dummies_are_dropped_latest_slot_first():
    r = np.random.default_rng(2)
    n = 300
    s1, s2 = (r.random(n) < 0.4).astype(float), (r.random(n) < 0.4).astype(float)
    D = _D(zs=r.normal(size=n), sd1=s1, sd2=s2, sd11=s1 + s2, **_rng_cols(n))
    res = t.resolve_aliased_controls(D, "zs", ["sd1", "sd2", "sd11", "p_k", "own6", "log1p_liq"], {})
    assert res["dropped"] == ["sd11"]
    D2 = D.assign(sd11=r.normal(size=n), sd3=s1 + s2)
    assert t.resolve_aliased_controls(D2, "zs", ["sd1", "sd2", "sd3", "sd11", "p_k", "own6", "log1p_liq"], {})["dropped"] == ["sd3"]


def test_a_control_that_is_still_deficient_after_the_three_groups_is_nan_unavailable():
    r = np.random.default_rng(3)
    n = 200
    p = r.normal(size=n)
    D = _D(zs=r.normal(size=n), p_k=p, own6=p.copy(), log1p_liq=r.normal(size=n))  # two K columns identical: not in groups (1)-(3)
    res = t.resolve_aliased_controls(D, "zs", ["p_k", "own6", "log1p_liq"], {})
    assert res["status"] == "unavailable" and res["dropped"] == [] and res["rank"] == 2 < res["n_cols"]
    assert "rank-deficient" in res["reason"]


def test_zs_in_the_span_of_the_retained_controls_is_aliased_and_never_dropped():
    r = np.random.default_rng(4)
    n = 200
    c1, c2 = r.normal(size=n), r.normal(size=n)
    D = _D(zs=2 * c1 - c2, p_k=c1, own6=c2, log1p_liq=r.normal(size=n))
    res = t.resolve_aliased_controls(D, "zs", ["p_k", "own6", "log1p_liq"], {})
    assert res["term_aliased"] and res["status"] == "unavailable" and res["dropped"] == []


def test_zero_variance_columns_are_removed_before_the_rank_and_reported():
    r = np.random.default_rng(5)
    n = 100
    D = _D(zs=r.normal(size=n), p_k=r.normal(size=n), own6=np.zeros(n), log1p_liq=r.normal(size=n))
    res = t.resolve_aliased_controls(D, "zs", ["p_k", "own6", "log1p_liq"], {})
    assert res["zero_variance_dropped"] == ["own6"] and res["status"] == "ok" and res["n_cols"] == 2


def test_the_rank_tolerance_is_max_n_p_times_eps_times_sigma_max():
    r = np.random.default_rng(6)
    n = 400
    x = r.normal(size=n)
    D = _D(zs=r.normal(size=n), p_k=x, own6=x + 1e-3 * r.normal(size=n), log1p_liq=r.normal(size=n))  # nearly, not exactly, collinear: full rank
    assert t.resolve_aliased_controls(D, "zs", ["p_k", "own6", "log1p_liq"], {})["status"] == "ok"
    D2 = D.assign(own6=x + 1e-15 * r.normal(size=n))  # collinear to rounding: below max(n, p) x eps x sigma_max
    assert t.resolve_aliased_controls(D2, "zs", ["p_k", "own6", "log1p_liq"], {})["status"] == "unavailable"


def test_the_declared_control_list_is_exactly_collinear_stage_A_finding_A3(tmp_path):
    """3.3 + 1.7 as written: K holds spread_k, 3.3 adds spread_{k-1} and the own innovation spread_k - spread_{k-1}. None is in groups (1)-(3): the rule returns NaN. Documented, not resolved."""
    u, cnt, by, spec, store, reg = units(tmp_path, n_batches=6, per_batch=6, singles=20, slots=range(0, 40))
    T = u[u["arm"] == "primary"].copy()
    s = T["mbar"].std(ddof=0)
    T["zs"] = T["mbar"] / s
    T["thin_x_zs"] = T["thin"] * T["zs"]
    A = T.assign(event_id=T["batch_id"])
    A, fcn, lev = t.fee_cat_dummies(A)
    declared = t.load_spec()
    cols = t.controls13(A, fcn, declared)
    assert {"spread_km1_c", "spread_c", "own_ds_c"} <= set(cols)
    res = t.resolve_aliased_controls(lt12.demeaned_frame(A, ["zs", *cols]), "zs", cols, lev)
    assert res["status"] == "unavailable" and not set(res["dropped"]) & {"spread_km1_c", "spread_c", "own_ds_c"}


# --- provenance, scope and hygiene -------------------------------------------------------------------------------------------------------------


def test_imported_files_hash_to_their_declared_pins():
    assert t.imported_hashes() == t.DECLARED["imported_sha256"]
    assert lt.imported_error() is None


def test_shared_declared_blocks_equal_the_lt12_spec_blocks():
    s12 = json.loads((Path(t.__file__).parent / "model_specs" / "live_tests12_v1.json").read_text())
    d = t.DECLARED
    assert d["grid"] == s12["grid"] and d["crypto_rule"]["slug_regex"] == s12["crypto_rule"]["slug_regex"] and d["crypto_rule"]["fee_type_prefix"] == s12["crypto_rule"]["fee_type_prefix"]
    assert d["rv"] == {k: s12["rv"][k] for k in d["rv"]} and d["receipt_span_s"] == s12["receipt_span_s"] and d["eligibility"]["spread_max"] == s12["eligibility"]["spread_max"]
    assert d["tiers"]["cuts_usd"] == s12["tiers"]["cuts_usd"] and d["census_inputs"]["span"] == s12["census_inputs"]["span"]
    mc12, mc = s12["census_gates"]["mde_common"], d["census_gates"]["mde_common"]
    assert all(mc[k] == mc12[k] for k in ("t_sum", "t_sum_exact", "day_factor", "sd_ds", "de_rho", "family_cap", "g_eff_min"))
    g12, g = s12["census_gates"]["CH245"], d["census_gates"]["CH253"]
    for k in ("completeness_min", "same_slot_abs_corr", "same_slot_share_max", "ident_nonzero_min", "ident_share_min", "leverage_top_frac", "leverage_top_share_max", "vif_w_max", "corr_max",
              "venue_clock_max", "venue_clock_abs_z", "block_share_min", "block_min_captures", "placebo_coverage_min", "r_gate_max", "de_floor"):
        assert g[k] == g12[k], k  # LT12's form reused where the design says so


def test_declared_thresholds_are_exactly_the_design_values():
    g = t.DECLARED["census_gates"]["CH253"]
    assert (g["coverage_min"], g["completeness_min"], g["units_projected_min"], g["batches_with_unit_min"], g["batches_ge48_min"], g["placebo_coverage_min"]) == (0.2, 0.6, 217224, 500, 100, 0.9)
    assert g["units_projected_min"] == 862 * 252 and g["same_slot_min_units"] == 24 and g["same_slot_share_max"] == 0.5
    assert t.DECLARED["batch"] == {**t.DECLARED["batch"], "chain_gap_s": 120.0, "min_markets": 3, "min_events": 2, "min_mates": 2, "max_mates": 30, "completeness_min": 0.6, "pseudo_min_age_days": 7.0}
    assert t.DECLARED["seeds"]["size_check"] == 20261797 and t.DECLARED["seeds"]["world10_calibration"] == 20261797 * 100 + 61 and t.DECLARED["seeds"]["power_runs"]["CH253"] == 20261797 * 100 + 52
    assert t.DECLARED["census_inputs"]["min_covered_days"] == {"CC13": 7.0, "CC13_twins": 5.0}
    assert t.declaration_sha256() == hashlib.sha256(t._canon(t.DECLARED).encode()).hexdigest()


def test_the_design_text_hash_constant_is_the_frozen_file():
    assert b.sha256_file(t.DESIGN_PATH) == t.DESIGN_TEXT_SHA256 == "ae594aa1a81aa93591d98f3210d907dff4df47ee3ad1dc0bbd44c5dccf59f738"
    assert t.design_text_error() is None  # the real ledger carries the freeze line


def _sources():
    here = Path(t.__file__).parent
    return {n: (here / n).read_text() for n in ("live_tests13.py", "live_tests13_base.py")} | {"run": (Path(t.__file__).parents[2] / "scripts" / "run_live_tests13.py").read_text()}


def test_no_lt11_lt12_object_or_older_live_test_module_is_computed_or_imported():
    for name, src in _sources().items():
        tree = ast.parse(src)
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert not called & {"ch245_units", "ch244_units", "twin_components_mirror", "twin_components_shock", "lag_twin_zs", "lag_twin_shock", "assign_placebo", "outcome_h1", "run_once"}, name
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names} | {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not {m for m in imported if any(m == f"live_tests{i}" or m.startswith(f"live_tests{i}_") for i in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11))}, name
        assert "E026" not in src or name == "live_tests13_base.py"
        for banned in ("copy_skilled", "wallet_skill", "costs"):
            assert f"import {banned}" not in src and f"from . import {banned}" not in src


def test_no_registered_seed_is_used_by_the_census_code():
    for name, src in _sources().items():
        assert "20261797" not in src.replace('"size_check": 20261797', "").replace("2026179752", "").replace("2026179761", "") or name == "live_tests13_base.py"
        assert "default_rng" not in src and "np.random" not in src and "import random" not in src, name  # the stage A census draws nothing


def test_nothing_writes_the_counted_trials_file():
    for name, src in _sources().items():
        tree = ast.parse(src)
        for n in ast.walk(tree):  # docstrings may MENTION the file; code may not
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
                n.body[0].value.value = ""
        code = ast.unparse(tree)
        assert "trials.jsonl" not in code and "append_jsonl" not in code and "battery2" not in code, name
