# ruff: noqa: E501
"""LT12 (LIVE_TESTS_12.md) code tests, synthetic capture trees only (no network, no data-dumps): the three reward-status cases of listed_carry24h_v2
(1.4.1), the event key and pair / ladder completeness (1.4.3), CH245's asymmetry rule, thin-only unit, sym class, control basis and twin NaN rule (2.2-2.3),
the placebo rule (2.3), the identification-gate quantities (6 item 6), CH244's day-fixed status, mixed rule, status_switched / status_nan_unit (re-check
fix 4), the shock excluding the own move, lowliq, the tier (3.2, 1.4.2), the four-cell MDE (3.4), the feed clock (1.2), causality (1.3), ops-stats, the
spec and registration refusals (8.4; LT11 code re-check defect 3) and the one-shot restore rule (7, final verification fix 2)."""

from __future__ import annotations

import copy
import json
import math
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests12 as lt
from tests import lt12_synth as sy

K0 = 15
NSL = 20


def _quote(mid: float, spread: float) -> tuple[float, float]:
    return round(mid - spread / 2.0, 4), round(mid + spread / 2.0, 4)


def _gen(markets: dict):
    """gen(k) for :func:`sy.build_tree`. Per market: ``mid`` (float or fn k), ``spread`` (float or fn k), ``nrkey``, ``event``, ``rw`` (fn k -> clob text),
    ``side`` (False or a set of slots without a sidecar row), ``missing`` (slots without a row), ``onesided`` (slots with bid 0), ``liq`` (float or fn),
    ``recv`` (row receipt offset), ``aug``, ``cat``, ``slugs``, ``eids``, ``tick``, ``neg``."""

    def val(x, k):
        return x(k) if callable(x) else x

    def gen(k):
        rows, ext = [], []
        for mid_id, m in markets.items():
            if k in m.get("missing", ()):
                continue
            mid = val(m.get("mid", 0.5), k) + 0.001 * math.sin(0.9 * k + len(mid_id))
            bid, ask = _quote(mid, val(m.get("spread", 0.02), k))
            if k in m.get("onesided", ()):
                bid = 0.0
            rows.append(sy.mrow(mid_id, bid, ask, event=m.get("event", "E" + mid_id), neg=m.get("neg", 1), nrkey=m.get("nrkey", ""), aug=m.get("aug", "0"),
                                liq=val(m.get("liq", 5e4), k), recv_off=m.get("recv", 60.0)))
            side = m.get("side", True)
            if side is False or (isinstance(side, (set, frozenset)) and k in side):
                continue
            ext.append(sy.xrow(mid_id, cat=m.get("cat", "politics"), tick=m.get("tick", "0.01"), rewards=m.get("rw", lambda _k: "")(k), slugs=m.get("slugs", ""), eids=m.get("eids", "")))
        return rows, ext

    return gen


def _world(tmp_path, markets: dict, slots=range(NSL)):
    by_slot = sy.build_tree(tmp_path / "snap", slots, _gen(markets))
    spec = sy.spec_for_tests()
    st = sy.prepare(tmp_path / "work", by_slot, spec)
    return st, spec, by_slot


def _rw(texts: dict, default: str = ""):
    return lambda k: texts.get(k, default)


ENDS_1002 = '[{"rewardsDailyRate": 10, "startDate": "2026-01-01", "endDate": "2026-10-02"}]'


# --- 1.4.1: the reward status listed_carry24h_v2 ----------------------------------------------------------------------------------------------------


def test_reward_status_three_cases(tmp_path):
    s = 24  # 2026-10-03T00:31Z, the first slot of a UTC day: slot 23 lies on 2026-10-02
    mk = {"m1": {"rw": _rw({s: sy.RW_TEXT})}, "m2": {"rw": _rw({s: sy.RW_ZERO})}, "m3": {"rw": _rw({21: sy.RW_TEXT})}, "m4": {},
          "m5": {"rw": _rw({20: sy.RW_ZERO})}, "m6": {"rw": _rw({s: "{not json"})}, "m7": {"side": {s}}, "m8": {"rw": _rw({23: ENDS_1002})},
          "m9": {"rw": _rw({12: sy.RW_TEXT})}}
    for m in mk.values():
        m.update(neg=0)
    st, spec, _ = _world(tmp_path, mk, slots=[x for x in range(10, 28) if x != 18])  # slot 18 has no capture
    rew, case = lt.rewarded_for(st, s, list(mk))
    got = dict(zip(mk, zip(rew, case, strict=True), strict=True))
    assert got["m1"] == (1.0, "listed_positive")  # (a) listed, positive
    assert got["m2"] == (0.0, "rewards_listed_inactive")  # (a) listed, rate 0
    assert got["m3"] == (1.0, "rewards_null_carried")  # (b) null at s, a positive listed text in the window
    assert got["m4"] == (0.0, "rewards_null_as_zero")  # (b) nothing listed in the window
    assert got["m5"] == (0.0, "rewards_null_window_listed_inactive")  # (b) only rate-0 texts
    assert np.isnan(got["m6"][0]) and got["m6"][1] == "malformed"  # (c) malformed at s
    assert np.isnan(got["m7"][0]) and got["m7"][1] == "absent"  # (c) no sidecar row at s
    assert got["m8"] == (0.0, "rewards_null_window_listed_inactive")  # re-parsed for the UTC day of s: the text of slot 23 has ended
    assert got["m9"] == (0.0, "rewards_null_as_zero")  # slot 12 lies outside the 12-slot window [13, 24]
    rs = st.reward_status(s)
    assert (rs["win_missing"] >= 1).all()  # the missing window slot 18 is skipped and counted, never filled
    assert max(st.reads) <= s  # no slot after s is read


# --- 1.4.3 and 2.2-2.3: the event join and CH245 ---------------------------------------------------------------------------------------------------


def _pair(key: str, s0, s1, **kw) -> dict:
    """Two members of event ``key`` with spread paths s0 / s1 (float or fn of k)."""
    out = {}
    for j, sp in enumerate((s0, s1)):
        m = {"nrkey": key, "event": "E" + key, "spread": sp, "mid": 0.30 + 0.35 * j, "slugs": f'["fam-{key}-{j}"]', "eids": f'["E{key}"]'}
        m.update({k_: (v[j] if isinstance(v, tuple) else v) for k_, v in kw.items()})
        out[f"{key}_{j}"] = m
    return out


def _ch245_markets() -> dict:
    mk = {}
    mk |= _pair("A", 0.04, lambda k: 0.03 if k >= K0 else 0.02)  # asymmetric at k - 1: thin A_0 (4c), dense A_1 widens 2c -> 3c at k
    mk |= _pair("B", 0.02, 0.02)  # symmetric
    mk |= _pair("C", lambda k: 0.12 if k == K0 else 0.03, 0.02)  # not tight at k -> pair_wide
    mk |= _pair("D", 0.03, 0.02, missing=(set(), {K0 - 1}))  # member absent at k - 1 -> members_changed
    mk |= _pair("E", 0.03, 0.02, onesided=(set(), {K0 - 1}))  # one-sided member at k - 1 -> event_incomplete
    mk |= _pair("F", 0.03, 0.02, recv=(60.0, 300.0))  # receipt span 240 s -> receipt_span
    mk |= _pair("G", 0.03, 0.02, aug=("1", "0"))  # augmented arm
    mk |= _pair("H", 0.03, 0.02, cat=("crypto", "politics"))  # crypto on one member -> category
    mk |= _pair("I", 0.03, 0.02, cat="sports")  # all-sports arm
    mk |= _pair("K", 0.05, 0.02, onesided=(set(), {K0 + 3}))  # asymmetric; one-sided at k + 3 -> twin NaN
    for j in range(2):  # an event without neg_risk_market_id: keyed by the Gamma event id
        mk[f"J_{j}"] = {"nrkey": "", "event": "EJ", "spread": 0.04 if j == 0 else 0.02, "mid": 0.3 + 0.35 * j, "slugs": f'["fam-J-{j}"]', "eids": '["EJ"]'}
    return mk


def test_ch245_units_pairs_classes_and_counts(tmp_path):
    st, spec, by_slot = _world(tmp_path, _ch245_markets())
    U, cnt = lt.ch245_units(st, K0, spec, stamp=False)
    th = U[U["line"] == "thin"].set_index("nrkey")
    assert set(th.index) == {"A", "G", "I", "K", "EJ"} and th.index.is_unique  # one thin unit per asymmetric pair-capture
    assert th.loc["A", "market_id"] == "A_0" and th.loc["A", "o_market_id"] == "A_1"
    assert th.loc["A", "o_ds_c"] == pytest.approx(1.0) and th.loc["A", "own_ds_c"] == pytest.approx(0.0)  # the dense book's innovation over (k - 1, k]
    assert th.loc["A", "arm"] == "primary" and th.loc["G", "arm"] == "augmented" and th.loc["I", "arm"] == "sports"
    dn = U[U["line"] == "dense"].set_index("nrkey")
    assert dn.loc["A", "market_id"] == "A_1" and dn.loc["A", "o_ds_c"] == pytest.approx(0.0)
    sym = U[U["line"] == "sym"]
    assert set(sym["nrkey"]) == {"B"} and len(sym) == 2 and "thin" not in set(U.loc[U["nrkey"] == "B", "line"])
    assert cnt["pair_wide"] == 1 and cnt["ev_reason_members_changed"] >= 1 and cnt["ev_reason_event_incomplete"] >= 1
    assert cnt["ev_reason_receipt_span"] >= 1 and cnt["ev_reason_category"] >= 1
    assert not (U["nrkey"].isin(["C", "D", "E", "F", "H"])).any()  # incomplete event-captures give no unit for any member
    # decision time = capture k's last row receipt (the F pair's 300 s row is in capture k)
    assert U["t_row"].iloc[0] == pytest.approx(sy.slot_dt(K0).timestamp() + 300.0)
    # the control basis: the mirror gaps at k - 1 are spanned by own spread at k - 1 and hb (not entered separately)
    a = th.loc["A"]
    assert a["g_ask_km1"] * 100 == pytest.approx(a["own_spread_km1_c"] - a["hb_km1"] * 100, abs=1e-6)
    assert a["g_bid_km1"] * 100 == pytest.approx(a["o_spread_km1_c"] - a["hb_km1"] * 100, abs=1e-6)
    assert not [c for c in lt.CONTROLS["CH245"] if c.startswith("g_") or "gap" in c]
    assert {"own_ds_c", "o_spread_km1_c", "hb_km1", "o_log1p_liq", "o_rewarded", "spread_c"} <= set(lt.CONTROLS["CH245"])
    assert th.loc["A", "o_spread_k_ticks"] == pytest.approx(3.0)
    assert np.isnan(U["zs"]).all()  # census values unfilled: the scaled state is NaN, never guessed


def test_ch245_asymmetry_is_one_tick_of_tick_e(tmp_path):
    mk = _pair("A", 0.03, 0.02) | _pair("B", 0.025, 0.02, tick="0.01")
    st, spec, _ = _world(tmp_path, mk)
    U, cnt = lt.ch245_units(st, K0, spec, stamp=False)
    assert set(U.loc[U["line"] == "thin", "nrkey"]) == {"A"}  # 1c difference = one tick: asymmetric; 0.5c < one tick: sym
    assert set(U.loc[U["line"] == "sym", "nrkey"]) == {"B"}


def test_ch245_causality_reads_nothing_after_k(tmp_path):
    st, spec, by_slot = _world(tmp_path, _ch245_markets())
    U1, _ = lt.ch245_units(st, K0, spec, stamp=False)
    assert max(st.reads) <= K0
    st2 = lt.SlotStore(tmp_path / "work", {k: v for k, v in by_slot.items() if k <= K0}, spec)
    U2, _ = lt.ch245_units(st2, K0, spec, stamp=False)
    pd.testing.assert_frame_equal(U1.reset_index(drop=True), U2.reset_index(drop=True))


def test_ch245_twin_is_nan_unless_the_pair_is_complete_at_k2_and_k3(tmp_path):
    st, spec, by_slot = _world(tmp_path, _ch245_markets())
    cf = {"s_D": 2.0, "s_T": 4.0}
    tw = lt.lag_twin_zs(by_slot[K0 + 2]["dir"], by_slot[K0 + 3]["dir"], ["A", "K"], ["A_1", "K_1"], np.array(["thin", "thin"], dtype=object), cf, spec)
    assert np.isfinite(tw[0]) and np.isnan(tw[1])
    c = lt.twin_components_mirror(by_slot[K0 + 2]["dir"], by_slot[K0 + 3]["dir"], spec)
    assert list(c.columns) == ["ds_tw_c"]  # the lag-slot loader returns the twin term only
    s = lt.twin_components_shock(by_slot[K0 + 2]["dir"], by_slot[K0 + 3]["dir"], spec)
    assert list(s.columns) == ["shock_tw"]


def test_zs_term_scales_and_is_nan_before_the_census():
    x = np.array([2.0, 2.0, 2.0])
    ln = np.array(["thin", "dense", "sym"], dtype=object)
    assert np.isnan(lt.zs_term(x, ln, None)).all()
    assert list(lt.zs_term(x, ln, {"s_D": 2.0, "s_T": 4.0})) == [1.0, 0.5, 1.0]


# --- 2.3: the placebo pair -------------------------------------------------------------------------------------------------------------------------------


def _plac_frame(units: dict) -> pd.DataFrame:
    return pd.DataFrame([{"line": "thin", "arm": "primary", "nrkey": k, "pair_fams": json.dumps(v[0]), "pair_eids": json.dumps(v[1]), "o_ds_c": v[2]} for k, v in units.items()])


def test_placebo_rule_sha_order_family_and_event_ids():
    keys = lt.placebo_order(["P", "Q", "R", "S"])
    assert keys == sorted(["P", "Q", "R", "S"], key=lambda k: __import__("hashlib").sha256(k.encode()).hexdigest())
    a, b_, c, d = keys
    units = {a: (["f1"], ["e1"], 1.0), b_: (["f1"], ["e2"], 2.0), c: (["f3"], ["e1", "e9"], 3.0), d: (["f4"], ["e4"], 4.0)}
    cnt: dict = {}
    U = lt.assign_placebo(_plac_frame(units), {"s_D": 2.0}, cnt).set_index("nrkey")
    assert U.loc[a, "pl_key"] == d  # b_ shares a family with a, c shares an event id with a, d qualifies
    assert U.loc[a, "pl_ds_c"] == 4.0 and U.loc[a, "zs_pl"] == 2.0
    assert U.loc[b_, "pl_key"] == c  # the first qualifying pair after b_ in sha256 order
    assert U.loc[d, "pl_key"] == a  # wrapping
    assert cnt["placebo_none"] == 0


def test_placebo_none_when_no_pair_qualifies():
    cnt: dict = {}
    U = lt.assign_placebo(_plac_frame({"P": (["f1"], ["e1"], 1.0), "Q": (["f1"], ["e2"], 2.0)}), {"s_D": 2.0}, cnt)
    assert U["pl_ds_c"].isna().all() and cnt["placebo_none"] == 2


def test_placebo_condition_is_two_sided():
    from astrolabe.research_lab import live_tests12_analysis as an

    assert an._pc(-0.6, 1.0, 0.5, two_sided=True) is False and an._pc(-0.6, 1.0, 0.5) is True  # a strongly negative placebo is not null
    assert an._pc(0.4, 1.0, 0.5, two_sided=True) is True and an._pc(None, 1.0, 0.5) is False


def test_series_family_and_event_id_set():
    assert lt.series_family('["Elections-2026", "x"]', "K") == "elections-2026" and lt.series_family("", "K") == "none:K"
    assert lt.event_id_set('["1", "2"]', "3") == ["1", "2", "3"] and lt.event_id_set(None, None) == [] and lt.event_id_set("4;5", "") == ["4", "5"]


# --- 6 item 6: the identification quantities ---------------------------------------------------------------------------------------------------------


def test_identification_quantities():
    rows = []
    for i in range(6):  # stratum e1|0: 3 non-zero innovations on 6 units
        rows.append({"event_id": "e1", "day": "0", "slot": i, "o_ds_c": 1.0 if i < 3 else 0.0, "zs": float(i % 3)})
    for i in range(4):  # stratum e2|0: 2 non-zero
        rows.append({"event_id": "e2", "day": "0", "slot": i, "o_ds_c": 1.0 if i < 2 else 0.0, "zs": float(i)})
    T = pd.DataFrame(rows)
    g = {"ident_nonzero_min": 3, "leverage_top_frac": 0.01}
    r = lt.identification_ch245(T, g)
    assert r["nonzero_share"] == pytest.approx(6 / 10)
    dm = lt.strict_expanding_demean(lt.stratum_codes(T), T["slot"].to_numpy(float), T["zs"].to_numpy(float))
    v2 = dm[np.isfinite(dm)] ** 2
    assert r["top_units"] == 1 and r["top_share"] == pytest.approx(v2.max() / v2.sum())
    ev = pd.Series(v2).groupby(T["event_id"].to_numpy()[np.isfinite(dm)]).sum() / v2.sum()
    assert r["event_share_max"] == pytest.approx(ev.max())


# --- 3.2-3.4 and 1.2: CH244 -----------------------------------------------------------------------------------------------------------------------


def _ladder(key: str, n: int, *, liq=None, rw=None, move=None, **kw) -> dict:
    out = {}
    for j in range(n):
        m = {"nrkey": key, "event": "E" + key, "spread": 0.02, "mid": (lambda j_: (lambda k: 0.10 + 0.15 * j_ + ((move or {}).get(j_, 0.0) if k >= K0 else 0.0)))(j),
             "liq": (liq or [5e4] * n)[j], "slugs": f'["lad-{key}"]', "eids": f'["E{key}"]', "rw": (rw or {}).get(j, lambda _k: "")}
        m.update(kw)
        out[f"{key}_{j}"] = m
    return out


def _ch244_markets() -> dict:
    mk = {}
    # L: l0 rewarded throughout; l1 unrewarded; l2 rewarded at its first capture of the day (status slot 11) then listed at rate 0 (switched);
    # l3 day-fixed unrewarded but malformed at k - 1 (own status NaN -> status_nan_unit). l0 moves 3 ticks at k (the only mover).
    mk |= _ladder("L", 4, liq=[1e3, 2e3, 3e4, 5e5], move={0: 0.03},
                  rw={0: lambda k: sy.RW_TEXT, 2: lambda k: sy.RW_TEXT if k <= 11 else sy.RW_ZERO, 3: lambda k: "{bad" if k == K0 - 1 else ""})
    mk |= _ladder("R", 3, rw={j: (lambda k: sy.RW_TEXT) for j in range(3)}, move={1: 0.02})  # all rewarded -> allrew arm
    mk |= _ladder("N", 3, rw={0: lambda k: sy.RW_TEXT, 1: lambda k: "{bad" if k == 11 else ""})  # day-fixed status NaN -> status_nan
    return mk


def test_ch244_day_fixed_status_mixed_rule_switches_and_nan_units(tmp_path):
    st, spec, _ = _world(tmp_path, _ch244_markets())
    U, cnt = lt.ch244_units(st, K0, spec, stamp=False)
    L = U[U["nrkey"] == "L"].set_index("market_id")
    assert set(L.index) == {"L_0", "L_1"}  # L_2 switched, L_3 status_nan_unit
    assert L.loc["L_0", "unrew"] == 0.0 and L.loc["L_1", "unrew"] == 1.0 and (L["arm"] == "primary").all()
    assert cnt["status_switched_unrew0"] == 1 and cnt["status_nan_unit"] == 1  # re-check fix 4: never given the day-fixed status
    # the shock excludes the own move: only L_0 moved (3 ticks), so L_0 has no shock and every sibling has one
    assert L.loc["L_0", "shock"] == 0.0 and L.loc["L_1", "shock"] == 1.0 and L.loc["L_1", "shock_size_raw"] == pytest.approx(3.0, abs=0.2)
    assert L.loc["L_1", "shock_x_unrew"] == 1.0 and L.loc["L_0", "shock_x_unrew"] == 0.0
    # lowliq within event at k - 1 (median of 1e3, 2e3, 3e4, 5e5 = 16,000) and the tier at k - 1
    assert L.loc["L_0", "lowliq"] == 1.0 and L.loc["L_1", "lowliq"] == 1.0
    assert L.loc["L_0", "tier_km1"] == 1.0 and L.loc["L_0", "tl1"] == 1.0 and L.loc["L_0", "tl1_x_shock"] == 0.0
    R = U[U["nrkey"] == "R"]
    assert len(R) and (R["arm"] == "allrew").all()
    assert "N" not in set(U["nrkey"]) and cnt["status_nan_event_captures"] >= 1
    assert max(st.reads) <= K0


def test_ch244_mixed_counts_status_switched_members_by_their_day_fixed_status(tmp_path):
    """Ruling B5: a switched or status_nan_unit member counts toward 'mixed' by its finite day-fixed status (their own units are excluded)."""
    mk = _ladder("M", 3, rw={0: lambda k: sy.RW_TEXT if k <= 11 else sy.RW_ZERO, 1: lambda k: "", 2: lambda k: ""}, move={1: 0.03})
    st, spec, _ = _world(tmp_path, mk)
    U, cnt = lt.ch244_units(st, K0, spec, stamp=False)
    assert cnt["status_switched_unrew0"] == 1 and set(U["market_id"]) == {"M_1", "M_2"} and (U["arm"] == "primary").all()


def test_tier_bins():
    t = lt.tier_of([999.0, 1000.0, 9999.0, 10000.0, 99999.0, 100000.0, float("nan")])
    assert list(t[:6]) == [0, 1, 1, 2, 2, 3] and np.isnan(t[6])
    d = lt.tier_dummies(t, "tl")
    assert list(d["tl1"][:6]) == [0, 1, 1, 0, 0, 0] and np.isnan(d["tl3"][6])


def test_four_cell_class_mde_formula():
    rng = np.random.default_rng(5)
    rows = []
    for e in range(30):
        for s in range(24):
            for u in (0.0, 1.0):
                sh = float(rng.random() < 0.5)
                rows.append({"event_id": f"e{e}", "day": str(s // 12), "slot": s, "unrew": u, "shock": sh, "shock_x_unrew": sh * u, "c1": float(rng.normal())})
    pop = pd.DataFrame(rows)
    a = {"t_sum": 3.47, "day_factor": 1.5, "de_rho": 0.02}
    r = lt.class_mde4(pop, "shock_x_unrew", ["unrew", "shock", "c1"], 2.0, a, 5.0, 0.02)
    c = r["cells_projected"]
    exp = 3.47 * 0.02 * 1.5 * math.sqrt(max(r["design_ss"]["vif_w"], 1.0)) * math.sqrt(5.0) * math.sqrt(sum(1.0 / v for v in c.values())) * 100.0
    assert r["declared_c"] == pytest.approx(exp) and r["mde_class_c"] == pytest.approx(max(exp, r["design_c"]))
    eff = lt.eff12(pop)
    assert c["n_us"] == pytest.approx(2.0 * ((pop["unrew"] == 1) & (pop["shock"] == 1) & eff).sum())


def test_feed_clock_six_hours_and_listing(tmp_path):
    feed = tmp_path / "feed"
    t = sy.slot_dt(K0 - 1)
    sy.write_feed(feed, t - timedelta(hours=7), {"cA": 10.0})
    spec = sy.spec_for_tests()
    fi = lt.FeedIndex(feed, spec)
    assert fi.clock(t.timestamp()) is None  # 7 h before capture k - 1's start: feed_uncovered
    sy.write_feed(feed, t - timedelta(hours=5), {"cA": 10.0, "cB": 0.0})
    sy.write_feed(feed, t + timedelta(minutes=5), {"cA": 0.0})  # after the status capture: never used
    fi = lt.FeedIndex(feed, spec)
    d = fi.clock(t.timestamp())
    assert d is not None and d.startswith((t - timedelta(hours=5)).strftime("%Y%m%dT%H"))
    li = fi.listing(t.timestamp(), ["cA", "cB", "cC"])
    assert list(li["feed_listed_pos"]) == [1.0, 0.0, 0.0] and list(li["feed_listed_zero"]) == [0.0, 1.0, 0.0] and (li["feed_cov"] == 1).all()
    assert li["feed_age_h"].iloc[0] == pytest.approx(5.0)


# --- ops-stats (1.6) -----------------------------------------------------------------------------------------------------------------------------------


def test_ops_stats_reads_no_price_spread_volume_or_liquidity_column(tmp_path, monkeypatch):
    for bad in ("bid", "ask", "spread_c", "o_ds_c", "liq", "vol24", "y", "p_k", "spread_c_h1", "liquidity", "volume24hr"):
        assert bad not in lt.OPS_COLS
    with pytest.raises(ValueError):
        lt._read_ops(tmp_path / "x.csv.gz", ["bid"])
    d = tmp_path / "mirror" / "frozen"
    d.mkdir(parents=True)
    pd.DataFrame({"role": ["r"], "kind": ["mirror"], "line": ["thin"], "arm": ["primary"], "in_scope": [1], "cell": ["rr"], "bid": [0.4], "o_ds_c": [1.0]}).to_csv(d / "x.csv.gz", index=False)
    seen = []
    real = lt._read_ops
    monkeypatch.setattr(lt, "_read_ops", lambda p, cols: seen.append(list(cols)) or real(p, cols))
    out = lt.ops_stats(tmp_path)
    assert out["line_counts"]["mirror:line:thin"] == 1 and all(set(c) <= lt.OPS_COLS for c in seen)


# --- spec, pins and registration refusals (8.4; LT11 code re-check defect 3) --------------------------------------------------------------------------


def test_draft_spec_slots_filled_later_are_null_not_empty():
    spec = lt.load_spec(sha=None)
    for key in ("k_tests", "informed_labels", "dropped_tests", "census_unavailable", "size_check_result", "code_sha256"):
        assert spec[key] is None, key
    assert all(v is None for t in lt.TESTS for k_, v in spec["census_fixed"][t].items())
    assert spec["k_block"]["chg_1d"] is None and spec["f_roles"] == {"CH245": "binding", "CH244": "binding"}
    assert spec["design_text_sha256"] == lt.DESIGN_TEXT_SHA256 and lt.SPEC_SHA256 is None


def _pinned_full() -> dict:
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["_pinned"] = True
    spec["k_tests"] = ["CH245", "CH244"]
    spec["census_fixed"]["CH245"] = {"s_D": 1.2, "s_T": 1.1, "s_w": 0.9, "zs_cuts": [-0.4, 0.4], "zs_gap": 1.5, "rgap_q50_s": 6.0, "rgap_q90_s": 20.0, "exclude_family": "",
                                     "rho_census": 0.5, "rho_census_nan": False}
    spec["census_fixed"]["CH244"] = {"world9_corr": -0.1, "shock_size_scale": 2.0, "exclude_family": ""}
    spec["census_gate_values"] = {"CH245": {"mde_c": 0.5}, "CH244": {"mde_c": 0.7}}
    spec["informed_labels"] = {"CH245": [], "CH244": []}
    spec["dropped_tests"], spec["census_unavailable"] = [], []
    return spec


def test_registration_error_refuses_null_slots():
    assert lt.registration_error(lt.load_spec(sha=None)) is None  # DRAFT
    full = _pinned_full()
    assert lt.registration_error(full) is None
    for key, val, msg in (("informed_labels", None, "informed_labels"), ("k_tests", None, "k_tests"), ("k_tests", [], "k_tests"), ("k_tests", ["CH243"], "unknown"),
                          ("dropped_tests", None, "dropped_tests"), ("census_unavailable", None, "census_unavailable")):
        sp = copy.deepcopy(full)
        sp[key] = val
        assert msg in lt.registration_error(sp)["error"], key
    sp = copy.deepcopy(full)
    sp["informed_labels"] = {"CH245": [], "CH244": None}
    assert "informed_labels" in lt.registration_error(sp)["error"]
    sp = copy.deepcopy(full)
    sp["census_fixed"]["CH245"]["s_w"] = float("nan")
    assert "s_w" in lt.registration_error(sp)["error"]
    sp = copy.deepcopy(full)
    sp["census_fixed"]["CH245"].update(rho_census=None, rho_census_nan=True)  # NaN correlation recorded: world 1 then fails by 1.8.1's rule
    assert lt.registration_error(sp) is None
    sp["census_fixed"]["CH245"]["rho_census_nan"] = False
    assert "rho_census" in lt.registration_error(sp)["error"]
    sp = copy.deepcopy(full)
    sp["census_gate_values"]["CH244"]["mde_c"] = None
    assert "mde_c" in lt.registration_error(sp)["error"]


def test_spec_pin_nan_and_role_refusals(tmp_path):
    p = tmp_path / "s.json"
    raw = json.loads(lt.SPEC_PATH.read_text())
    p.write_text(json.dumps(raw))
    with pytest.raises(RuntimeError, match="mismatch"):
        lt.load_spec(p, sha="0" * 64)
    raw2 = dict(raw, extra=float("nan"))
    p.write_text(json.dumps(raw2))
    with pytest.raises(RuntimeError, match="NaN"):
        lt.load_spec(p, sha=lt.sha256_file(p))
    p.write_text(json.dumps(dict(raw, registered_utc="2026-12-11T00:00:00Z")))
    with pytest.raises(RuntimeError, match="L6"):
        lt.load_spec(p, sha=None)
    spec = lt.load_spec(sha=None)
    with pytest.raises(RuntimeError):
        lt.f_role(dict(spec, f_roles={"CH245": "label", "CH244": "binding"}), "CH245")
    assert lt.role_of(lt.epoch("2026-12-10T02:31:00Z"), lt.REGISTERED_UTC, lt.END_UTC, True) == lt.ROLE_CONF
    assert lt.role_of(lt.epoch("2026-12-10T02:31:00Z"), lt.REGISTERED_UTC, lt.END_UTC, False) == lt.ROLE_UNREG
    assert lt.role_of(lt.epoch("2026-12-31T00:31:00Z"), lt.REGISTERED_UTC, lt.END_UTC, True) == lt.ROLE_UNREG


def test_design_text_is_the_frozen_file():
    assert lt.design_text_sha() == "a543db63baeb3e85ff2dfa0189478086216c708e59b36f6db575c6b84592b62d" and lt.design_text_error() is None


# --- 7 (final verification fix 2): the one-shot restore refuses only while a lag-slot capture is in progress ----------------------------------------


def _restore_spec(last: int = 40) -> dict:
    return sy.census_spec(14, last)


def _cap_dir(root, k: int, state: str | None, *, shift_s: float = 0.0, rows: bool = True):
    t = sy.slot_dt(k) + timedelta(seconds=shift_s)
    d = root / (t.strftime("%Y%m%dT%H%M%SZ") + "_syn")
    d.mkdir(parents=True)
    if rows:
        (d / "rows.csv.gz").write_bytes(b"")
    if state is not None:
        (d / "manifest.json").write_text(json.dumps({"state": state, "started_utc": sy.iso(t)}))
    return d


def test_restore_readiness_cases(tmp_path):
    spec = _restore_spec()
    lag = lt.lag_slots(spec)
    assert lag == [41, 42, 43]
    root = tmp_path / "snap"
    root.mkdir()
    _cap_dir(root, 41, "complete")
    _cap_dir(root, 42, "failed")  # a final non-complete state: missing
    now = sy.slot_dt(43).timestamp() + 600.0
    d43 = _cap_dir(root, 43, "running", shift_s=60.0)  # started 9 min ago, not final: in progress -> refuse
    r = lt.restore_readiness([root], spec, now)
    st_ = {k: v["status"] for k, v in r["lag_slots"].items()}
    assert list(st_.values()) == ["complete", "missing", "in_progress"] and r["refuse"] is True
    # the same capture still open more than one slot (2 h) after its start will not complete: missing, the restore proceeds
    r2 = lt.restore_readiness([root], spec, sy.slot_dt(43).timestamp() + 3 * 3600.0)
    assert r2["refuse"] is False
    assert r2["missing_slots"] == [lt.iso(lt.b.slot_time(42, spec)), lt.iso(lt.b.slot_time(43, spec))]
    (d43 / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": sy.iso(sy.slot_dt(43) + timedelta(seconds=60))}))
    assert lt.restore_readiness([root], spec, now)["refuse"] is False


def test_restore_readiness_no_capture_pending_then_missing(tmp_path):
    spec = _restore_spec()
    root = tmp_path / "snap"
    root.mkdir()
    for k in (41, 42):
        _cap_dir(root, k, "complete")
    t43 = sy.slot_dt(43).timestamp()
    assert lt.restore_readiness([root], spec, t43 + 600.0)["refusing_slots"] == [lt.iso(t43)]  # not yet past the 30 min tolerance: a capture may still start
    r = lt.restore_readiness([root], spec, t43 + 1801.0)
    assert r["refuse"] is False and r["missing_slots"] == [lt.iso(t43)]
    _cap_dir(root, 43, None, shift_s=30.0)  # a directory with no manifest yet: in progress while young
    assert lt.restore_readiness([root], spec, t43 + 1900.0)["refuse"] is True
