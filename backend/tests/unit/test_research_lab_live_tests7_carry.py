# ruff: noqa: E501
"""LT7 ruling 13.7: the causal listed carry-forward ``listed_carry24h_v2`` (``RewardCarry``, the unit builders' counts, the CH193 bookkeeping columns)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from astrolabe.research_lab import live_tests7 as lt
from tests.unit.test_research_lab_live_tests7 import (
    CAP,
    K0,
    SPEC,
    T0,
    ser_frame,
    store_with,
    sweep_frame_sizes,
)

DAY = "2026-10-09"  # UTC day of K0 (12:31Z); K0 - 6 is 00:31Z of the same day, K0 - 7 .. K0 - 11 are on 2026-10-08


def prog(start: str, end: str, rate: float = 10.0) -> str:
    return f'[{{"startDate":"{start}","endDate":"{end}","rewardsDailyRate":{rate}}}]'


ACT = prog("2026-01-01", "2027-01-01")
NULLROW = (None, None, 20.0, 3.5)


def slot_frame(rows: dict, k: int = K0) -> pd.DataFrame:
    """Series-like frame of one slot: ``rows`` market -> (clob_rewards cell, status override or None, rew_min, rew_maxspread). The status and rate are
    decided as the slot's own capture would (day of that slot)."""
    ids = list(rows)
    ser = ser_frame(dict.fromkeys(ids, 0.5), t=T0 + 7200.0 * (k - K0))
    own_day = DAY if k >= K0 - 6 else "2026-10-08"
    sts, rates, raws, mins, mss = [], [], [], [], []
    for m in ids:
        cell, status, rmin, rms = rows[m]
        if status is None:
            st, rate = lt.reward_status(cell, True, own_day)
        else:
            st, rate = status, float("nan")
        sts.append(st)
        rates.append(rate)
        raws.append(cell if st == "listed" else None)
        mins.append(rmin)
        mss.append(rms)
    ser["rew_status"], ser["rew_rate"], ser["rew_raw"], ser["rew_min"], ser["rew_maxspread"] = sts, rates, np.array(raws, object), mins, mss
    return ser


def build(slots: dict[int, dict], k: int = K0) -> tuple[lt.RewardCarry, pd.DataFrame]:
    """Add every slot <= k (ascending) to a store and apply the carry at k; returns (store, the frame of k after apply)."""
    c = lt.RewardCarry()
    out = None
    for s in sorted(slots):
        f = slot_frame(slots[s], s)
        c.add(s, f)
        if s == k:
            out = c.apply(f, k, DAY)
    return c, out


def test_no_slot_after_k_is_ever_read():
    # a LISTED positive text at k + 1 (and k + 5) must be ignored, even if it sits in the store
    c = lt.RewardCarry()
    c.add(K0 - 1, slot_frame({"a": NULLROW}, K0 - 1))
    c.add(K0, slot_frame({"a": NULLROW}, K0))
    c.add(K0 + 1, slot_frame({"a": (ACT, None, 99.0, 9.9)}, K0 + 1))
    c.add(K0 + 5, slot_frame({"a": (ACT, None, 99.0, 9.9)}, K0 + 5))
    out = c.apply(slot_frame({"a": NULLROW}, K0), K0, DAY)
    assert out.loc["a", "rew_status"] == "null" and out.loc["a", "rew_rate"] == 0.0 and np.isnan(out.loc["a", "rew_carry_lag"])
    assert out.loc["a", "rew_min"] == 20.0 and out.loc["a", "rew_win_inactive"] == 0.0
    assert out.loc["a", "rew_trans"] == 0.0  # the later slots do not enter the transition count either
    # the census loops add slot k only after reading it: the store never holds a later slot in the first place
    c2 = lt.RewardCarry()
    c2.add(K0, slot_frame({"a": NULLROW}, K0))
    assert set(c2.slots) == {K0}


def test_window_is_exactly_k_minus_11_to_k():
    inside = build({K0 - 11: {"a": (ACT, None, 20.0, 3.5)}, K0: {"a": NULLROW}})[1]
    assert inside.loc["a", "rew_carry_lag"] == 11 and inside.loc["a", "rew_rate"] == 10.0
    outside = build({K0 - 12: {"a": (ACT, None, 20.0, 3.5)}, K0: {"a": NULLROW}})[1]
    assert np.isnan(outside.loc["a", "rew_carry_lag"]) and outside.loc["a", "rew_rate"] == 0.0


def test_cross_day_reparse_uses_the_day_of_k():
    # slot K0 - 8 is on 2026-10-08. A programme that ENDED on 10-08 was positive when parsed on its own day but is 0 for day(k) = 10-09: not carried.
    ended = prog("2026-01-01", "2026-10-08")
    # a programme that STARTS on 10-09 parses as 0 on 10-08 (listed-inactive that day) but is positive for day(k): carried
    starts = prog("2026-10-09", "2027-01-01")
    _, out = build({K0 - 8: {"ended": (ended, None, 20.0, 3.5), "starts": (starts, None, 20.0, 3.5)}, K0: {"ended": NULLROW, "starts": NULLROW}})
    assert lt.reward_status(ended, True, "2026-10-08")[1] == 10.0 and lt.reward_status(starts, True, "2026-10-08")[1] == 0.0
    assert np.isnan(out.loc["ended", "rew_carry_lag"]) and out.loc["ended", "rew_rate"] == 0.0 and out.loc["ended", "rew_win_inactive"] == 1.0
    assert out.loc["starts", "rew_carry_lag"] == 8 and out.loc["starts", "rew_rate"] == 10.0


def test_gap_slots_are_skipped_and_counted_never_filled():
    # only K0 - 3 and K0 are stored: 10 of the 12 window slots are missing; the source is K0 - 3 (lag 3)
    _, out = build({K0 - 3: {"a": (ACT, None, 20.0, 3.5)}, K0: {"a": NULLROW}})
    assert out.loc["a", "rew_carry_lag"] == 3 and out.loc["a", "rew_win_missing"] == 10.0
    # a fully missing window: null stays unrewarded and is counted as "no listed capture in the window"
    _, out2 = build({K0: {"a": NULLROW}})
    assert np.isnan(out2.loc["a", "rew_carry_lag"]) and out2.loc["a", "rew_win_missing"] == 11.0 and out2.loc["a", "rew_rate"] == 0.0 and out2.loc["a", "rew_win_inactive"] == 0.0
    cnt: dict = {}
    lt._reward_cols(out2, cnt)
    assert cnt["rewards_null_as_zero"] == 1 and cnt["reward_window_slots_missing"] == 11 and cnt["rewards_null_carried"] == 0


def test_malformed_and_absent_are_unchanged_and_not_carried_from():
    prior = {"m": (ACT, None, 20.0, 3.5), "x": (ACT, None, 20.0, 3.5), "bad_then_null": ("garbage", None, 20.0, 3.5), "ok": (ACT, None, 20.0, 3.5)}
    now = {"m": ("garbage", None, 20.0, 3.5), "x": (None, "absent", float("nan"), float("nan")), "bad_then_null": NULLROW, "ok": NULLROW}
    _, out = build({K0 - 2: prior, K0: now})
    assert out.loc["m", "rew_status"] == "malformed" and np.isnan(out.loc["m", "rew_rate"]) and np.isnan(out.loc["m", "rew_carry_lag"])
    assert out.loc["x", "rew_status"] == "absent" and np.isnan(out.loc["x", "rew_rate"]) and np.isnan(out.loc["x", "rew_carry_lag"])
    assert np.isnan(out.loc["bad_then_null", "rew_carry_lag"]) and out.loc["bad_then_null", "rew_rate"] == 0.0  # an earlier malformed text is never read as listed
    assert out.loc["ok", "rew_carry_lag"] == 2 and out.loc["ok", "rew_rate"] == 10.0
    assert out.loc[["m", "x"], "rew_win_inactive"].eq(0.0).all()


def test_listed_at_k_is_unchanged_even_if_an_earlier_text_is_positive():
    _, out = build({K0 - 1: {"a": (ACT, None, 20.0, 3.5)}, K0: {"a": (prog("2026-12-01", "2027-01-01"), None, 20.0, 3.5)}})
    assert out.loc["a", "rew_status"] == "listed" and out.loc["a", "rew_rate"] == 0.0 and np.isnan(out.loc["a", "rew_carry_lag"])


def test_carried_params_come_from_the_latest_positive_source_capture():
    slots = {K0 - 9: {"a": (ACT, None, 50.0, 7.0), "b": (ACT, None, 20.0, 3.5), "c": (ACT, None, 20.0, 3.5)},
             K0 - 4: {"a": (prog("2026-01-01", "2026-01-02"), None, 30.0, 5.0), "b": (ACT, None, 20.0, 3.5), "c": (ACT, None, 25.0, 3.5)},  # a: inactive on day(k)
             K0: {"a": NULLROW, "b": NULLROW, "c": NULLROW}}
    _, out = build(slots)
    assert out.loc["a", "rew_carry_lag"] == 9 and (out.loc["a", "rew_min"], out.loc["a", "rew_maxspread"]) == (50.0, 7.0) and out.loc["a", "rew_param_differs"] == 1.0
    assert out.loc["b", "rew_carry_lag"] == 4 and (out.loc["b", "rew_min"], out.loc["b", "rew_maxspread"]) == (20.0, 3.5) and out.loc["b", "rew_param_differs"] == 0.0
    assert out.loc["c", "rew_carry_lag"] == 4 and out.loc["c", "rew_min"] == 25.0 and out.loc["c", "rew_param_differs"] == 1.0  # latest source wins (K0 - 4, not K0 - 9)
    assert out.loc["a", "rew_rate_v1"] == 0.0  # the k-only (v1) rate is kept for the sensitivity


def test_transitions_per_market_one_versus_two_or_more():
    a_ = (ACT, None, 20.0, 3.5)
    slots = {K0 - 3: {"a": a_, "b": a_}, K0 - 2: {"a": NULLROW, "b": NULLROW}, K0 - 1: {"a": NULLROW, "b": a_}, K0: {"a": NULLROW, "b": NULLROW}}
    _, out = build(slots)
    assert out.loc["a", "rew_trans"] == 1.0 and out.loc["b", "rew_trans"] == 3.0
    cnt: dict = {}
    lt._reward_cols(out, cnt)
    assert cnt["reward_switch_markets_1"] == 1 and cnt["reward_switch_markets_ge2"] == 1


def test_lag_bucket_counts_and_unit_builders():
    ids = ["l1", "l2", "l3", "l4", "l11", "none", "inactive", "listed", "mal"]
    off = {"l1": 1, "l2": 2, "l3": 3, "l4": 4, "l11": 11}
    slots: dict[int, dict] = {K0: {m: NULLROW for m in ids}}
    slots[K0]["listed"] = (ACT, None, 20.0, 3.5)
    slots[K0]["mal"] = ("garbage", None, 20.0, 3.5)
    for m, o in off.items():
        slots.setdefault(K0 - o, {})[m] = (ACT, None, 20.0, 3.5)
    slots.setdefault(K0 - 5, {})["inactive"] = (prog("2026-01-01", "2026-01-02"), None, 20.0, 3.5)
    for s in list(slots):
        for m in ids:  # every market is present (null) in every stored slot it is not listed in, so only the listed texts differ
            slots[s].setdefault(m, NULLROW)
    _, ser_k = build(slots)
    ser_p = ser_frame(dict.fromkeys(ids, 0.5), t=T0 - 7200)
    sw = sweep_frame_sizes({m: (0.49, 0.51, 50, 40, 150, 120) for m in ids}, T0)
    u, cnt = lt.patient_units(ser_k, ser_p, None, sw, CAP, K0, SPEC)
    assert (cnt["rewards_null_carried_lag1"], cnt["rewards_null_carried_lag2_3"], cnt["rewards_null_carried_lag4_11"], cnt["rewards_null_carried"]) == (1, 2, 2, 5)
    assert cnt["rewards_null_as_zero"] == 1 and cnt["rewards_null_window_listed_inactive"] == 1 and cnt["reward_unparseable"] == 1 and cnt["rewards_listed_inactive"] == 0
    assert cnt["reward_window_slots_missing"] == 12 - len(slots)
    assert set(u["market_id"]) == set(ids) - {"mal"}
    r = dict(zip(u["market_id"], u["rewarded"], strict=True))
    assert [r[m] for m in ("l1", "l2", "l3", "l4", "l11")] == [1.0] * 5 and r["none"] == 0.0 and r["inactive"] == 0.0 and r["listed"] == 1.0
    v1 = dict(zip(u["market_id"], u["rewarded_v1"], strict=True))
    assert v1["l1"] == 0.0 and v1["listed"] == 1.0 and dict(zip(u["market_id"], u["listed_k"], strict=True))["listed"] == 1.0
    assert not ({"rew_carry_lag", "rewarded_v1", "listed_k"} & (set(lt.CONTROLS_197) | set(lt.CONTROLS_192)))
    paths = {m: [0.5 + 0.01 * (i % 2) for i in range(85)] for m in ids}
    st = store_with(paths, K0)
    kp = ser_frame({m: p[-2] for m, p in paths.items()}, t=T0 - 7200)
    u2, c2 = lt.ivr_units(ser_k, kp, st, CAP, K0, SPEC, pd.Series(dict.fromkeys(ids, 0.02)))
    assert c2["rewards_null_carried"] == 5 and c2["rewards_null_as_zero"] == 1 and set(u2["market_id"]) == set(ids) - {"mal"}


def test_ch193_unit_frame_carries_the_reward_bookkeeping_columns_only():
    mids = {"a": 0.5, "b": 0.5}
    ser_p = ser_frame(mids, vol=1000.0, t=T0 - 7200)
    ser_k = ser_frame(mids, vol=1500.0, t=T0)
    ser_k["rew_status"], ser_k["rew_min"], ser_k["osz"], ser_k["rew_carry_lag"] = ["null", "listed"], [30.0, 20.0], [5.0, 7.0], [2.0, np.nan]
    store = store_with({m: [0.5] * 13 for m in mids}, K0)
    u, cnt = lt.absorbed_units(ser_k, ser_p, store, CAP, K0, SPEC)
    assert len(u) == 2 and {"rew_status", "rew_min", "osz", "rew_carry_lag"} <= set(u.columns)
    assert dict(zip(u["market_id"], u["rew_min"], strict=True)) == {"a": 30.0, "b": 20.0}
    assert not any(c.startswith("rewards_") for c in cnt)  # no reward-based exclusion or count in CH193
    assert not ({"rew_status", "rew_min", "osz", "rew_carry_lag"} & set(lt.CONTROLS_191))


def test_series7_frame_stores_raw_text_of_listed_cells_only(tmp_path):
    from tests.unit.test_research_lab_live_tests7_census import Tree

    t = Tree(tmp_path / "t", slots=range(90, 92), sweep_slots=[], sample_slots=[])
    d = t.snap / t.cid[90]
    rows, ext = lt.load_rows7(d), lt.load_ext7(d)
    ids = [str(m) for m in rows["market_id"].astype(str)[:3]]
    ext.loc[ids[0], "clob_rewards"] = ACT
    ext.loc[ids[1], "clob_rewards"] = np.nan
    ext.loc[ids[2], "clob_rewards"] = "garbage"
    ser = lt.series7_frame(rows, ext, lt.load_spec(sha=None), DAY).set_index("market_id")
    assert ser.loc[ids[0], "rew_raw"] == ACT and ser.loc[ids[1], "rew_raw"] is None and ser.loc[ids[2], "rew_raw"] is None
    assert lt.series7_frame(rows, None, lt.load_spec(sha=None), DAY)["rew_raw"].isna().all()


def test_cs7_slots_cover_the_carry_window_of_each_ch197_origin():
    spec = lt.load_spec(sha=None)
    sl = lt.cs7_slots(spec, set())
    first, _ = lt._span(spec)
    for k in sl["K"]:
        if lt.slot_in_day(k) == spec["tests"]["CH197"]["slot_index_in_day"]:
            assert {j for j in range(k - 11, k + 1) if j >= first} <= sl["full"]
    assert spec["reward_null_rule"] == "listed_carry24h_v2" and spec["reward_carry_slots"] == lt.REWARD_CARRY_SLOTS == 12
