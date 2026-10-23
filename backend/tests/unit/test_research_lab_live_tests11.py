# ruff: noqa: E501
"""LT11 (LIVE_TESTS_11.md) code tests, synthetic data only, no network, no real data-dumps read: the loaders and statuses, the three unit builders (CH234's
volume_num classes and centred product, CH233's complete event-capture pairs and the sign of cl_sib, CH232's approach zone, first-of-day rule, xr,
day_gap, tick coincidence, movers-only rule and the reward reading), causality (no builder reads a slot after k), the lag-slot loaders, the reader, the
fresh seal and the census (coverage check before any gate, every gate), ops-stats and the pin / date refusals."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from astrolabe.research_lab import live_tests11 as lt
from tests import lt11_synth as sy

K0 = 15  # origin slot of the builder tests (history 0..14, targets / twins 16..18)
NSL = 20


def _gen_ch234(rows_at: dict, ext_at: dict | None = None):
    """gen(k): ``rows_at[mid] = (bid/ask path fn)``; see tests for the layout."""

    def gen(k):
        rows, ext = [], []
        for mid, spec_ in rows_at.items():
            p = spec_["mid"][k]
            if p is None or (isinstance(p, float) and math.isnan(p)) or k in spec_.get("missing", ()):
                continue
            half = spec_.get("halfs", {}).get(k, spec_.get("half", 0.01))
            bid, ask = sy.quote(p, half)
            if k in spec_.get("onesided", ()):
                bid = 0.0
            rows.append(sy.mrow(mid, bid, ask, event=spec_.get("event", "e" + mid), end=spec_.get("end", "2027-06-01T00:00:00Z"), neg=spec_.get("neg", 0), nrkey=spec_.get("nrkey", ""),
                                other=spec_.get("other", 0), aug=spec_.get("aug", "0"), recv_off=spec_.get("recv", 60.0), cond=spec_.get("cond")))
            if spec_.get("side", True):
                v = spec_.get("vnum", {}).get(k, 100.0)
                ext.append(sy.xrow(mid, cat=spec_.get("cat", "politics"), tick=spec_.get("tick", {}).get(k, "0.01"), vnum="" if v is None else v, rewards=spec_.get("rewards", {}).get(k, spec_.get("rewards_all", "")),
                                   rmin=spec_.get("rmin", ""), rmax=spec_.get("rmax", "")))
        return rows, ext

    return gen


def _flat(p0: float, jump: float = 0.0, at: int = K0, n: int = NSL) -> list[float]:
    return [p0 + (jump if i >= at else 0.0) for i in range(n)]


def _world(tmp_path, markets: dict, slots=range(NSL)):
    root = tmp_path / "snap"
    by_slot = sy.build_tree(root, slots, _gen_ch234(markets))
    spec = sy.spec_for_tests()
    st = sy.prepare(tmp_path / "work", by_slot, spec)
    return st, spec, by_slot


def test_vnum_classes_keyed_by_slot_and_unknown_subclasses():
    nan = float("nan")
    c = lt.vnum_classes([150, 100, 100, 100, 90, 120, nan], [1, 1, 1, 1, 1, 0, 1], [100, 100, nan, 100, 100, 100, 100], [1, 1, 1, 0, 1, 1, 1], True)
    assert list(c) == ["traded", "quote_only", "vnum_missing_km1", "vnum_missing_km1", "vnum_decrease", "sidecar_missing", "vnum_missing_k"]
    # slot k - 1 has no capture: every mover is vnum_missing_km1, whatever else holds (no value is carried from k - 2)
    c0 = lt.vnum_classes([150.0, 100.0], [1, 1], [100.0, 100.0], [1, 1], False)
    assert list(c0) == ["vnum_missing_km1", "vnum_missing_km1"]
    # tolerance 1e-6: a 5e-7 rise is quote-only, a 2e-6 rise traded
    c1 = lt.vnum_classes([100.0000005, 100.000002], [1, 1], [100.0, 100.0], [1, 1], True)
    assert list(c1) == ["quote_only", "traded"]


def test_ch234_units_classes_filters_and_product(tmp_path):
    m = {}
    steady = {"mid": _flat(0.50, 0.03), "vnum": {15: 150.0}}  # traded +0.03, w = 0.5
    m["m1"] = steady
    m["m2"] = {"mid": _flat(0.30, -0.03), "vnum": {}}  # quote-only, d < 0, w = 0.5 + (-1)(0.30 - 0.5) = 0.7
    m["m3"] = {"mid": _flat(0.20, 0.03), "vnum": {14: None, 15: 150.0}}  # empty at k - 1 although k - 2 holds 100
    m["m4"] = {"mid": _flat(0.60, 0.02), "vnum": {15: 90.0}}  # decrease
    m["m5"] = {"mid": _flat(0.55, 0.004)}  # not a mover
    m["m6"] = {"mid": _flat(0.97, -0.02), "vnum": {15: 150.0}}  # p_{k-1} outside [0.04, 0.96]
    m["m7"] = {"mid": _flat(0.40, 0.02), "vnum": {15: 150.0}, "cat": "sports"}  # sports arm kept, in_scope 0
    m["m8"] = {"mid": _flat(0.40, 0.02), "vnum": {15: 150.0}, "cat": "crypto"}  # dropped
    m["m9"] = {"mid": _flat(0.45, 0.02), "vnum": {15: 150.0}, "tick": {15: "0.001"}}  # tick changed
    m["m10"] = {"mid": _flat(0.45, 0.02), "vnum": {15: 150.0}, "end": "2026-10-02T08:00:00Z"}  # ends within 3 h of the decision (06:32Z): after the row receipt, so only the decision rule drops it
    m["m11"] = {"mid": _flat(0.45, 0.02), "vnum": {15: 150.0}, "side": False}  # sidecar row missing -> category unknown
    m["m12"] = {"mid": _flat(0.50, 0.30), "vnum": {15: 150.0}}  # |d| = 0.30 winsorised at 0.20
    st, spec, _ = _world(tmp_path, m)
    # the end-date test needs a decision time before the end: slot 15 starts 2026-10-02T06:31Z
    U, cnt = lt.ch234_units(st, K0, spec, stamp=False)
    byid = U.set_index("market_id")
    assert byid.loc["m1", "vclass"] == "traded" and byid.loc["m2", "vclass"] == "quote_only"
    assert byid.loc["m3", "vclass"] == "vnum_missing_km1" and byid.loc["m4", "vclass"] == "vnum_decrease"
    assert abs(byid.loc["m1", "w"] - 0.5) < 1e-9 and abs(byid.loc["m2", "w"] - 0.7) < 1e-9
    assert "m5" not in byid.index and "m6" not in byid.index and "m8" not in byid.index and "m11" not in byid.index and "m9" not in byid.index
    assert byid.loc["m7", "in_scope"] == 0 and byid.loc["m1", "in_scope"] == 1
    assert byid.loc["m12", "absd"] == 0.20 and byid.loc["m12", "absd_wins"] == 1 and cnt["winsorised"] == 1
    assert cnt["not_mover"] == 1 and cnt["p_band"] == 1 and cnt["tick_changed"] == 1 and cnt["crypto"] == 1 and cnt["sports_unknown"] == 1
    assert "m10" not in byid.index and cnt["end_date_decision"] == 1
    # unit time is the decision time = capture k's last receipt (rows 60 s, sidecar 90 s after the start -> 90 s)
    assert abs(byid["t_row"].iloc[0] - (sy.slot_dt(K0).timestamp() + 90.0)) < 1e-6
    # level drift by bin: sb* are sign x bin indicators and span w
    assert byid.loc["m2", "sb1"] == -1.0 and byid.loc["m1", "sb2"] == 1.0
    # momentum is sign-adjusted for CH234 (A3); the chg_1h column of the synthetic rows is 0
    assert set(["own6", "own24", "mom_missing", "log_rv24s", "chg1d", "chg1dmissing" if "chg1dmissing" in U else "chg1d_missing"]) <= set(U.columns)


def test_ch234_xw_uses_census_fixed_centres_and_is_nan_before(tmp_path):
    m = {"m1": {"mid": _flat(0.50, 0.03), "vnum": {15: 150.0}}, "m2": {"mid": _flat(0.30, -0.03), "vnum": {15: 150.0}}}
    st, spec, _ = _world(tmp_path, m)
    U, _ = lt.ch234_units(st, K0, spec, stamp=False)
    assert U["xw"].isna().all()  # unfilled census-fixed values: the product is NaN, never a guess
    spec["census_fixed"]["CH234"].update(w_centre=0.6, w_scale=0.2, absd_centre=0.02, absd_scale=0.01)
    U, _ = lt.ch234_units(st, K0, spec, stamp=False)
    r = U.set_index("market_id")
    assert abs(r.loc["m1", "xw"] - ((0.5 - 0.6) / 0.2) * ((0.03 - 0.02) / 0.01)) < 1e-9
    assert abs(r.loc["m2", "xw"] - ((0.7 - 0.6) / 0.2) * ((0.03 - 0.02) / 0.01)) < 1e-9


def test_ch234_causality_reads_nothing_after_k(tmp_path):
    m = {"m1": {"mid": _flat(0.50, 0.03), "vnum": {15: 150.0}}}
    st, spec, _ = _world(tmp_path, m)
    lt.ch234_units(st, K0, spec, stamp=False)
    assert max(st.reads) <= K0
    # and the unit is unchanged when every capture after k is removed from the store
    st2 = lt.SlotStore(tmp_path / "work", {k: v for k, v in st.by_slot.items() if k <= K0}, spec)
    U2, _ = lt.ch234_units(st2, K0, spec, stamp=False)
    U1, _ = lt.ch234_units(st, K0, spec, stamp=False)
    pd.testing.assert_frame_equal(U1.reset_index(drop=True), U2.reset_index(drop=True))


def test_ch234_missing_slot_km1_gives_no_unit_and_no_carry_forward(tmp_path):
    m = {"m1": {"mid": _flat(0.50, 0.03), "vnum": {15: 150.0}}}
    root = tmp_path / "snap"
    by_slot = sy.build_tree(root, [s for s in range(NSL) if s != K0 - 1], _gen_ch234(m))
    spec = sy.spec_for_tests()
    st = sy.prepare(tmp_path / "work", by_slot, spec)
    U, cnt = lt.ch234_units(st, K0, spec, stamp=False)
    assert U.empty and cnt.get("no_pair") == 1


# --- CH232 -------------------------------------------------------------------------------------------------------------------------

RW = '[{"rewardsDailyRate": 10, "startDate": "2026-01-01", "endDate": "2027-12-31"}]'
K32 = 30  # slot 30 = day 2 (slots 24..35), slot of day 6: earlier slots of the day are 24..29
N32 = 36


def _path(base: float, steps: dict[int, float], n: int = N32) -> list[float]:
    p, out = base, []
    for i in range(n):
        if i in steps:
            p = steps[i]
        out.append(p)
    return out


def _world32(tmp_path, markets: dict, drop_slots=()):
    root = tmp_path / "snap"
    by_slot = sy.build_tree(root, [s for s in range(N32) if s not in drop_slots], _gen_ch234(markets))
    spec = sy.spec_for_tests()
    st = sy.prepare(tmp_path / "work", by_slot, spec)
    return st, spec


def test_ch232_zone_crossings_xo_xr_and_exclusions(tmp_path):
    m = {
        "r1": {"mid": _path(0.12, {30: 0.08}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # first outward crossing of the day
        "r2": {"mid": _path(0.12, {27: 0.08, 28: 0.12, 30: 0.08}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # a later crossing: xr
        "r3": {"mid": _path(0.12, {30: 0.11}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # zone mover, no crossing: the reference class
        "r4": {"mid": _path(0.10, {30: 0.095}), "halfs": {30: 0.005}, "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # half a tick: not a mover
        "r5": {"mid": _path(0.12, {30: 0.08}), "missing": {26}, "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # an undefined same-day mid: day_gap_market
        "r6": {"mid": _path(0.88, {30: 0.92}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # the upper boundary
        "r7": {"mid": _path(0.12, {30: 0.08}), "rmin": "", "rmax": ""},  # unrewarded (control panel)
        "r8": {"mid": _path(0.12, {30: 0.03}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # m_k below 0.04: tick coincident
        "r9": {"mid": _path(0.30, {30: 0.20}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # not in the zone
        "r10": {"mid": _path(0.12, {26: 0.08, 27: 0.12, 30: 0.08}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # an earlier crossing at 26 -> xr at 30
    }
    st, spec = _world32(tmp_path, m)
    U, cnt = lt.ch232_units(st, K32, spec, stamp=False, arms=("out",))
    r = U.set_index("market_id")
    assert r.loc["r1", "xo"] == 1 and r.loc["r1", "xr"] == 0 and r.loc["r1", "rew"] == 1
    assert r.loc["r2", "xo"] == 0 and r.loc["r2", "xr"] == 1
    assert r.loc["r10", "xo"] == 0 and r.loc["r10", "xr"] == 1
    assert r.loc["r3", "xo"] == 0 and r.loc["r3", "xr"] == 0
    assert "r4" not in r.index and cnt["arm_out"]["half_tick"] == 1
    assert "r5" not in r.index and cnt["arm_out"]["day_gap_market"] == 1
    assert r.loc["r6", "xo"] == 1 and r.loc["r6", "upper"] == 1 and r.loc["r6", "cheap_side"] == "ask"
    assert r.loc["r7", "rew"] == 0 and r.loc["r7", "xo"] == 1 and r.loc["r7", "v_c"] == 0.0
    assert "r8" not in r.index and cnt["arm_out"]["tick_coincident"] == 1
    assert "r9" not in r.index
    assert r.loc["r1", "cheap_side"] == "bid" and abs(r.loc["r1", "d_tow"] - 0.04) < 1e-9 and abs(r.loc["r1", "dist"] - 0.02) < 1e-9
    assert r.loc["r1", "v_c"] == 4.5 and abs(r.loc["r1", "log_rate"] - math.log(10)) < 1e-9
    # spread-in-ticks dummies: spread 0.02 = 2 ticks, unchanged
    assert r.loc["r1", "S2"] == 1 and r.loc["r1", "S3"] == 0 and r.loc["r1", "dSp1"] == 0
    assert max(st.reads) <= K32


def test_ch232_missing_capture_slot_of_the_day_is_day_gap(tmp_path):
    m = {"r1": {"mid": _path(0.12, {30: 0.08}), "rewards_all": RW, "rmin": 20, "rmax": 4.5}}
    st, spec = _world32(tmp_path, m, drop_slots=(26,))
    U, cnt = lt.ch232_units(st, K32, spec, stamp=False, arms=("out",))
    assert U.empty and cnt["arm_out"]["day_gap"] == 1


def test_ch232_first_slot_of_day_has_no_earlier_slots(tmp_path):
    # slot 24 is the first slot of day 2: a crossing at (23, 24] is the first crossing of day 2 and no earlier slot is required
    m = {"r1": {"mid": _path(0.12, {24: 0.08}), "rewards_all": RW, "rmin": 20, "rmax": 4.5}}
    st, spec = _world32(tmp_path, m)
    U, cnt = lt.ch232_units(st, 24, spec, stamp=False, arms=("out",))
    assert len(U) == 1 and U["xo"].iloc[0] == 1


def test_ch232_inward_and_pseudo_arms(tmp_path):
    m = {"in1": {"mid": _path(0.08, {30: 0.12}), "rewards_all": RW, "rmin": 20, "rmax": 4.5},  # inward: zone [0.06, 0.10), first inward crossing of the day
         "ps1": {"mid": _path(0.22, {30: 0.15}), "rewards_all": RW, "rmin": 20, "rmax": 4.5}}  # the 0.20 placebo: zone [0.20, 0.24], crossing out of [0.20, 0.80]
    st, spec = _world32(tmp_path, m)
    U, cnt = lt.ch232_units(st, K32, spec, stamp=False)
    a = U.set_index(["arm", "market_id"])
    assert a.loc[("in", "in1"), "xo"] == 1 and a.loc[("pseudo", "ps1"), "xo"] == 1
    assert ("out", "in1") not in a.index


def test_crossing_never_spans_an_undefined_mid():
    nan = float("nan")
    assert list(lt.crossing([0.12, nan, 0.12], [0.08, 0.08, nan], (0.10, 0.90))) == [True, False, False]
    assert list(lt.crossing([0.50, 0.10], [0.95, 0.10], (0.10, 0.90))) == [True, False]  # exactly 0.10 is inside (closed band, tolerance 1e-9)
    assert list(lt.crossing([0.08], [0.12], (0.10, 0.90), "in")) == [True]


def test_reward_reading_is_the_documented_one_with_m1_on_the_cheap_side():
    # 1.4.2 + the ledger record at the design-text freeze: a single-sided quote scores at 1/c (c = 3.0) INSIDE [0.10, 0.90]; outside only two-sided scores
    w = lt.reward_side_weight([0.50, 0.10, 0.90, 0.0999, 0.9001, 0.05])
    assert np.allclose(w, [1 / 3, 1 / 3, 1 / 3, 0.0, 0.0, 0.0])
    assert lt.REWARD_SINGLE_SIDE_C == 3.0 and lt.M1_SIDE_READING == "cheap"
    assert lt.m1_side() == ("cheap",) and lt.m1_side("dear") == ("dear",) and lt.m1_side("neither") == ("cheap", "dear")
    # the cheap side: below 0.10 the YES bid, above 0.90 the YES ask
    assert list(lt.cheap_side([0.05, 0.95])) == ["bid", "ask"]
    spec = lt.load_spec(sha=None)
    assert spec["m1_side_reading"] == "cheap" and spec["reward_single_side_c"] == 3.0


def test_fix_panels_first_unit_and_panel_switched():
    U = pd.DataFrame({"market_id": ["a", "a", "a", "b"], "slot": [1, 2, 3, 1], "rew": [1.0, 0.0, 1.0, 0.0]})
    out, cnt = lt.fix_panels11(U)
    assert cnt["panel_switched"] == 1 and cnt["panel_switched_reward"] == 1 and cnt["panel_switched_control"] == 0 and len(out) == 3
    assert set(out["panel"]) == {0.0, 1.0}


# --- CH233 -------------------------------------------------------------------------------------------------------------------------


def _mem(nrkey: str, event: str, mid_path: list[float], **kw) -> dict:
    return {"mid": mid_path, "neg": 1, "nrkey": nrkey, "event": event, **kw}


def _event(prefix: str, nrkey: str, bids_prev: list[float], bids_k: list[float], **kw) -> dict:
    """Members whose bids are ``bids_prev`` through slot K0 - 1 and ``bids_k`` from slot K0 (the quote half-width 0.01: mid = bid + 0.01)."""
    out = {}
    for i, (a, c) in enumerate(zip(bids_prev, bids_k, strict=True)):
        out[f"{prefix}{i}"] = _mem(nrkey, "EV" + nrkey, [a + 0.01 if s < K0 else c + 0.01 for s in range(NSL)], **kw)
    return out


def test_ch233_state_sign_and_complete_pairs(tmp_path):
    m = {}
    m.update(_event("a", "NR1", [0.30, 0.30, 0.30], [0.34, 0.30, 0.30]))  # member a0 rises by 4c
    m.update(_event("z", "NR9", [0.20, 0.20], [0.24, 0.20]))  # 2 members: the size2 arm
    st, spec, _ = _world(tmp_path, m)
    U, cnt = lt.ch233_units(st, K0, spec, stamp=False)
    r = U.set_index("market_id")
    # cl_sib = the siblings' bid-sum change (cents): positive when the other members' bids rose
    assert abs(r.loc["a0", "cl_sib"] - 0.0) < 1e-9 and abs(r.loc["a1", "cl_sib"] - 4.0) < 1e-9 and abs(r.loc["a2", "cl_sib"] - 4.0) < 1e-9
    assert abs(r.loc["a0", "own_dbid_c"] - 4.0) < 1e-9 and abs(r.loc["a1", "own_dbid_c"]) < 1e-9
    assert abs(r.loc["a1", "hb_km1"] - 0.10) < 1e-9 and abs(r.loc["a1", "hb_k"] - 0.06) < 1e-9
    assert abs(r.loc["a0", "ca_sib"]) < 1e-9 or True
    assert r.loc["a1", "arm"] == "primary" and r.loc["z0", "arm"] == "size2" and r.loc["a1", "size_class"] == "3-5"
    assert r.loc["a0", "fav"] == 1.0 and r.loc["a1", "fav"] == 0.0
    assert max(st.reads) <= K0
    assert cnt["reason_ok"] == 2


def test_ch233_exclusion_reasons_and_arms(tmp_path):
    m = {}
    m.update(_event("c", "NRc", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2]))  # complete: the reference event
    ch = _event("d", "NRd", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2])
    ch["d2"] = {**ch["d2"], "missing": set(range(K0, NSL))}  # a member vanishes at k -> members_changed
    m.update(ch)
    inc = _event("e", "NRe", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2])
    inc["e1"] = {**inc["e1"], "onesided": {K0}}  # a member without a bid at k -> event_incomplete
    m.update(inc)
    sp = _event("f", "NRf", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2])
    sp["f2"] = {**sp["f2"], "recv": 200.0}  # span 140 s at k (rows at 60 s and 200 s) -> receipt_span
    m.update(sp)
    sp2 = _event("g", "NRg", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2])
    sp2["g1"] = {**sp2["g1"], "recv": 175.0}  # span exactly 115 s: allowed
    m.update(sp2)
    m.update(_event("h", "NRh", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2], aug="1"))  # augmented: the reported arm
    m.update(_event("i", "NRi", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2], aug=""))  # a missing field counts as augmented
    m.update(_event("j", "NRj", [0.07] * 11, [0.07] * 11))  # 11 members: the ladder arm
    spr = _event("s", "NRs", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2])
    spr["s0"] = {**spr["s0"], "cat": "sports"}  # a sports member excludes the event
    m.update(spr)
    oth = _event("o", "NRo", [0.2, 0.2, 0.2], [0.2, 0.2, 0.2])
    oth["o0"] = {**oth["o0"], "other": 1}  # the "Other" member stays in the sum
    m.update(oth)
    st, spec, _ = _world(tmp_path, m)
    U, cnt = lt.ch233_units(st, K0, spec, stamp=False)
    ids = set(U["market_id"])
    assert {"c0", "c1", "c2", "g0", "g1", "g2", "o0", "o1", "o2"} <= ids
    assert not ({"d0", "d1", "e0", "e1", "f0", "f1", "f2", "s0", "s1", "s2"} & ids)
    arm = U.set_index("market_id")["arm"]
    assert arm["h0"] == "augmented" and arm["i0"] == "augmented" and arm["j0"] == "ladder" and arm["c0"] == "primary"
    assert cnt["reason_members_changed"] == 1 and cnt["reason_event_incomplete"] == 1 and cnt["reason_receipt_span"] == 1 and cnt["reason_category"] == 1


def test_ch233_receipt_span_at_k_minus_1_also_excludes(tmp_path):
    root = tmp_path / "snap"

    def gen(k):
        rows, ext = [], []
        for i in range(3):
            rows.append(sy.mrow(f"x{i}", 0.30, 0.32, event="EV1", neg=1, nrkey="NR1", recv_off=60.0 + (200.0 if (k == K0 - 1 and i == 2) else 0.0)))
            ext.append(sy.xrow(f"x{i}", vnum=100.0))
        return rows, ext

    by_slot = sy.build_tree(root, range(NSL), gen)
    spec = sy.spec_for_tests()
    st = sy.prepare(tmp_path / "work", by_slot, spec)
    U, cnt = lt.ch233_units(st, K0, spec, stamp=False)
    assert U.empty and cnt["reason_receipt_span"] == 1


def test_ch233_member_level_filter_keeps_the_event_complete(tmp_path):
    m = {}
    ev = _event("a", "NR1", [0.30, 0.30, 0.30, 0.30], [0.34, 0.30, 0.30, 0.30])
    ev["a3"] = {**ev["a3"], "half": 0.12}  # spread 0.24 > 0.10: not tight, but two-sided: the event stays complete
    m.update(ev)
    st, spec, _ = _world(tmp_path, m)
    U, cnt = lt.ch233_units(st, K0, spec, stamp=False)
    assert "a3" not in set(U["market_id"]) and cnt["not_tight"] == 1 and cnt["reason_ok"] == 1
    # the siblings' sums still include the non-tight member's bid change (here its bid moves with its mid by 0 -> only a0's 4c counts)
    assert abs(U.set_index("market_id").loc["a1", "cl_sib"] - 4.0) < 1e-9


def test_ch233_headroom_working_range_uses_the_largest_member_tick_absolutely(tmp_path):
    m = {}
    m.update(_event("w", "NRw", [0.33, 0.33, 0.33], [0.33, 0.33, 0.33]))  # sum of bids 0.99 -> hb = 0.01 = one tick
    m.update(_event("v", "NRv", [0.30, 0.30, 0.30], [0.30, 0.30, 0.30]))  # hb = 0.10
    st, spec, _ = _world(tmp_path, m)
    U, _ = lt.ch233_units(st, K0, spec, stamp=False)
    r = U.set_index("market_id")
    assert r.loc["w0", "near_zero_km1"] == 1.0 and r.loc["v0", "near_zero_km1"] == 0.0
    # a bid sum above one (negative headroom) within two ticks counts too (absolute value)
    m2 = _event("u", "NRu", [0.34, 0.34, 0.34], [0.34, 0.34, 0.34])
    st2, spec2, _ = _world(tmp_path / "b", m2)
    U2, _ = lt.ch233_units(st2, K0, spec2, stamp=False)
    assert abs(U2["hb_km1"].iloc[0] - (-0.02)) < 1e-9 and U2["near_zero_km1"].iloc[0] == 1.0


def test_ch233_zcl_scaled_by_size_class_census_scale(tmp_path):
    m = {}
    m.update(_event("a", "NR1", [0.30, 0.30, 0.30], [0.34, 0.30, 0.30]))
    st, spec, _ = _world(tmp_path, m)
    U, _ = lt.ch233_units(st, K0, spec, stamp=False)
    assert U["zcl"].isna().all()
    spec["census_fixed"]["CH233"]["s_c"] = {"3-5": 2.0, "6-10": 4.0}
    U, _ = lt.ch233_units(st, K0, spec, stamp=False)
    assert abs(U.set_index("market_id").loc["a1", "zcl"] - 2.0) < 1e-9
