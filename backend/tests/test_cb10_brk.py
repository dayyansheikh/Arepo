# ruff: noqa: E501
"""CB10-B tests (offline; synthetic fixtures; no network)."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from astrolabe.research_lab import cb10_brk as br
from astrolabe.research_lab import cb10_common as c10

H = 3600.0
T_START = 1_000_000.0


def _tx(*pts):
    """pts = (seconds after T_START, price, size)."""
    pts = sorted(pts)
    return {"ts": np.array([T_START + a for a, _, _ in pts], float), "price": np.array([p for _, p, _ in pts], float), "size": np.array([s for _, _, s in pts], float)}


SPAN = (T_START - 1.0, T_START + 200 * H)


def _prior(level_side=0.52, n=6, start=0.0, step=3 * H):
    return [(start + i * step, level_side, 5.0) for i in range(n)]


# ---- levels ----------------------------------------------------------------------------------------------------------------------------------


def test_levels_and_pseudo_levels_as_declared():
    assert br.LEVELS == (0.10, 0.25, 0.50, 0.75, 0.90)
    pseudo = sorted(round(x, 2) for x, arm, _ in br.level_table() if arm == "pseudo")
    assert pseudo == [0.07, 0.13, 0.22, 0.28, 0.47, 0.53, 0.72, 0.78, 0.87, 0.93]
    assert br.pairs()[0.5] == (0.47, 0.53)


# ---- episode detection ----------------------------------------------------------------------------------------------------------------------


def test_down_break_first_crossing_and_direction():
    t_b = 30 * H
    eps, cnt = br.detect_episodes(_tx(*_prior(), (t_b, 0.49, 3.0)), SPAN)
    real = [e for e in eps if e["arm"] == "real"]
    assert len(real) == 1 and real[0]["level"] == 0.5 and real[0]["s"] == 1 and real[0]["t_b"] == T_START + t_b
    up, _ = br.detect_episodes(_tx(*_prior(level_side=0.48), (t_b, 0.51, 3.0)), SPAN)
    r = [e for e in up if e["arm"] == "real"]
    assert len(r) == 1 and r[0]["s"] == -1


def test_equality_at_the_level_is_not_a_crossing():
    t_b = 30 * H
    eps, _ = br.detect_episodes(_tx(*_prior(), (t_b, 0.50, 3.0)), SPAN)
    assert [e for e in eps if e["arm"] == "real"] == []
    eps, _ = br.detect_episodes(_tx(*_prior(), (t_b, 0.50, 3.0), (t_b + 60, 0.49, 3.0)), SPAN)
    assert len([e for e in eps if e["arm"] == "real"]) == 1  # >= level then < level


def test_24h_memory_second_crossing_and_return_excluded():
    # cross down at 30h, back up at 31h (a crossing of the same level), down again at 33h: neither later crossing is a first crossing within 24 h
    pts = [*_prior(), (30 * H, 0.49, 3.0), (31 * H, 0.52, 3.0), (33 * H, 0.48, 3.0)]
    eps, cnt = br.detect_episodes(_tx(*pts), SPAN)
    real = [e for e in eps if e["arm"] == "real"]
    assert len(real) == 1 and real[0]["t_b"] == T_START + 30 * H and cnt["not_first_24h"] >= 2
    # after more than 24 h without a crossing the next crossing is a first crossing again
    pts2 = [*_prior(n=9), (30 * H, 0.49, 3.0), (31 * H, 0.52, 3.0), *[(h * H, 0.52, 3.0) for h in (45, 50, 55, 60)], (61 * H, 0.48, 3.0)]
    eps2, _ = br.detect_episodes(_tx(*pts2), SPAN)
    assert [e["t_b"] - T_START for e in eps2 if e["arm"] == "real" and e["level"] == 0.5] == [30 * H, 61 * H]


def test_min_three_prior_transactions_and_span_conditions():
    t_b = 30 * H
    few = [(t_b - 5 * H, 0.55, 1.0), (t_b - 4 * H, 0.55, 1.0), (t_b, 0.49, 1.0)]
    eps, cnt = br.detect_episodes(_tx(*few), SPAN)
    assert [e for e in eps if e["arm"] == "real"] == [] and cnt["few_prior_tx"] >= 1
    # episodes need [t_b - 24 h, t_b + 2 h] inside the covered span
    eps, cnt = br.detect_episodes(_tx(*_prior(), (t_b, 0.49, 3.0)), (T_START + 10 * H, T_START + 200 * H))
    assert eps == [] and cnt["outside_span"] >= 1
    eps, cnt = br.detect_episodes(_tx(*_prior(), (t_b, 0.49, 3.0)), (T_START - 1.0, T_START + t_b + 1.9 * H))
    assert eps == [] and cnt["outside_span"] >= 1


def test_same_arm_two_hour_spacing():
    # a pseudo-level break 90 minutes after the real 0.75 break (outside the 60-minute exclusion) is the first of its arm; the further pseudo and real
    # crossings of the same jump are dropped by the same-type 2 h spacing rule
    pts = [*_prior(level_side=0.76, n=8), (30 * H, 0.74, 3.0), (31.5 * H, 0.49, 3.0)]
    eps, cnt = br.detect_episodes(_tx(*pts), SPAN)
    real = [e for e in eps if e["arm"] == "real"]
    assert [e["level"] for e in real] == [0.75] and cnt["spacing"] >= 2
    assert sum(1 for e in eps if e["arm"] == "pseudo") == 1


def test_mutual_exclusion_drops_both_real_and_pseudo_within_60_minutes():
    t_b = 30 * H
    # one move 0.55 -> 0.46 crosses pseudo 0.53, real 0.50 and pseudo 0.47 within seconds: all dropped
    eps, cnt = br.detect_episodes(_tx(*_prior(), (t_b, 0.46, 3.0)), SPAN)
    assert [e for e in eps if e["level"] in (0.47, 0.5, 0.53)] == [] and cnt["mutual_exclusion"] >= 2
    # a pseudo crossing 61 minutes away from a real crossing keeps both
    pts = [*_prior(level_side=0.60, n=8), (30 * H, 0.52, 3.0), (30 * H + 3660, 0.49, 3.0)]
    eps2, _ = br.detect_episodes(_tx(*pts), SPAN)
    arms = {(e["level"], e["arm"]) for e in eps2}
    assert (0.53, "pseudo") in arms and (0.5, "real") in arms


# ---- marks, reversal, follow-through ---------------------------------------------------------------------------------------------------------


def _ep_path():
    t_b = 30 * H
    pts = [*_prior(), (t_b, 0.49, 3.0), (t_b + 120, 0.485, 10.0), (t_b + 300, 0.48, 30.0), (t_b + 100 * 60, 0.50, 4.0), (t_b + 2 * H - 30, 0.52, 4.0), (t_b + 3 * H, 0.9, 4.0)]
    tx = _tx(*pts)
    eps, _ = br.detect_episodes(tx, SPAN)
    return tx, next(e for e in eps if e["arm"] == "real")


def test_vwap10_excludes_break_and_m2h_uses_only_transactions_at_or_before_2h():
    tx, e = _ep_path()
    out = br.attach_marks(tx, e, 0.05)
    assert out["vwap10"] == pytest.approx((0.485 * 10 + 0.48 * 30) / 40)  # break transaction itself excluded
    assert out["m2h"] == 0.52  # the 0.9 print at 3 h is after the mark time
    assert out["r_e"] == pytest.approx(100 * 1 * (0.52 - out["vwap10"]))  # s = +1 (down-break): cents, positive = moved back
    up_tx, up_e = tx, dict(e, s=-1)
    assert br.attach_marks(up_tx, up_e, 0.05)["r_e"] == pytest.approx(-out["r_e"])


def test_m2h_unavailable_when_last_transaction_older_than_90_minutes():
    t_b = 30 * H
    tx = _tx(*_prior(), (t_b, 0.49, 3.0), (t_b + 120, 0.48, 10.0), (t_b + 80 * 60, 0.50, 4.0))  # last at/before 2 h is at 80 min < 90 min
    eps, _ = br.detect_episodes(tx, SPAN)
    e = next(x for x in eps if x["arm"] == "real")
    out = br.attach_marks(tx, e, 0.05)
    assert out["m2h"] is None and out["r_e"] is None and out["follow"] is True and out["has_m2h"] is False


def test_no_follow_through_when_no_transaction_in_10_minutes():
    t_b = 30 * H
    tx = _tx(*_prior(), (t_b, 0.49, 3.0), (t_b + 700, 0.48, 10.0))
    eps, _ = br.detect_episodes(tx, SPAN)
    e = next(x for x in eps if x["arm"] == "real")
    assert br.follow_through(tx, e) is False
    assert "vwap10" not in br.attach_marks(tx, e, 0.05)


def test_counts_view_carries_no_price_after_the_break():
    tx, e = _ep_path()
    c = br.attach_counts(tx, e)
    assert not set(c) & set(br.CENSUS_FORBIDDEN) and "maker" not in c
    assert c["follow"] is True and c["has_m2h"] is True and isinstance(c["filled_shares"], float)


# ---- maker rule ------------------------------------------------------------------------------------------------------------------------------


def _maker_ep(s=1, level=0.5):
    return {"t_b": T_START + 30 * H, "level": level, "s": s}


def _mtx(*pts):
    return _tx(*[(30 * H + a, p, z) for a, p, z in pts])


def test_trade_through_fills_and_print_at_quote_does_not_fill():
    e = _maker_ep()  # down-break: bid at 0.49
    f = br.maker_fills(_mtx((0, 0.495, 1.0), (120, 0.49, 50.0), (200, 0.48, 30.0)), e)
    assert f["posted"] and f["quote"] == 0.49 and f["filled"] == 30.0  # the print AT 0.49 fills nothing; the print through it fills its size
    f = br.maker_fills(_mtx((0, 0.495, 1.0), (200, 0.49, 500.0)), e)
    assert f["posted"] and f["filled"] == 0.0


def test_fill_size_cap_100_and_live_until_10_minutes():
    e = _maker_ep()
    f = br.maker_fills(_mtx((0, 0.495, 1.0), (100, 0.48, 70.0), (200, 0.47, 70.0), (300, 0.46, 70.0)), e)
    assert f["filled"] == 100.0
    f = br.maker_fills(_mtx((0, 0.495, 1.0), (601, 0.40, 500.0)), e)
    assert f["filled"] == 0.0  # after t_b + 10 min the quote is gone
    f = br.maker_fills(_mtx((0, 0.495, 1.0), (59, 0.40, 5.0)), e)
    assert f["filled"] == 0.0  # before the post time (t_b + 60 s) nothing can fill


def test_not_posted_when_last_transaction_at_or_through_the_quote_at_post_time():
    e = _maker_ep()
    assert br.maker_fills(_mtx((0, 0.49, 1.0)), e)["posted"] is False
    assert br.maker_fills(_mtx((0, 0.48, 1.0)), e)["posted"] is False
    assert br.maker_fills(_mtx((0, 0.50, 1.0), (61, 0.48, 1.0)), e)["posted"] is True  # the transaction after the post time does not decide posting
    up = _maker_ep(s=-1)
    assert br.maker_fills(_mtx((0, 0.51, 1.0)), up)["posted"] is False
    f = br.maker_fills(_mtx((0, 0.505, 1.0), (100, 0.52, 40.0)), up)
    assert f["quote"] == 0.51 and f["posted"] and f["filled"] == 40.0


def test_exit_cost_and_net_per_share():
    assert br.exit_cost(0.5, 0.05) == pytest.approx(0.05 * 0.25 + 0.015)
    assert br.exit_cost(0.5, 0.05, br.HALF_SPREAD_ROBUST) == pytest.approx(0.05 * 0.25 + 0.02)
    tx, e = _ep_path()
    # a fillable maker path
    t_b = e["t_b"] - T_START
    pts = [*_prior(), (t_b, 0.49, 3.0), (t_b + 30, 0.495, 2.0), (t_b + 200, 0.48, 100.0), (t_b + 100 * 60, 0.50, 4.0), (t_b + 2 * H - 30, 0.52, 4.0)]
    tx2 = _tx(*pts)
    eps, _ = br.detect_episodes(tx2, SPAN)
    e2 = next(x for x in eps if x["arm"] == "real")
    m = br.attach_marks(tx2, e2, 0.05)["maker"]
    assert m["posted"] and m["filled"] == 100.0 and m["quote"] == 0.49
    assert m["net_c"] == pytest.approx(100 * ((0.52 - 0.49) - br.exit_cost(0.52, 0.05)))
    assert m["net_c_hs20"] == pytest.approx(m["net_c"] - 0.5)  # half-spread 2.0c instead of 1.5c
    assert m["worst_c"] == pytest.approx(100 * (-0.01 - br.exit_cost(0.5, 0.05)))
    assert m["gross_c"] == pytest.approx(100 * 0.03)
    # absent fee field -> 0.05 default rate (conservative)
    assert br.attach_marks(tx2, e2, math.nan)["maker"]["net_c"] == pytest.approx(m["net_c"])


# ---- census (counts only), frozen weights, gates ----------------------------------------------------------------------------------------------


def _ep(arm, pair, i, *, follow=True, ev=None, day=None, **kw):
    d = {"arm": arm, "pair": pair, "level": pair if arm == "real" else round(pair + 0.03, 2), "s": 1, "follow": follow, "has_m2h": True, "event_key": ev or f"e{i % 120}",
         "day": day or c10.day_add("2026-05-01", i % 70), "month": "2026-05", "t_b": float(i)}
    d.update(kw)
    return d


def _census_eps(n_real=1100, n_pseudo=1100, pairs_=(0.25, 0.5, 0.75)):
    eps = []
    for i in range(n_real):
        eps.append(_ep("real", pairs_[i % len(pairs_)], i, posted=(i % 4 != 0), filled_shares=(100.0 if i % 3 == 0 else 0.0)))
    for i in range(n_pseudo):
        eps.append(_ep("pseudo", pairs_[i % len(pairs_)], i + n_real))
    return eps


def test_census_b_counts_weights_gates_and_forbidden_fields():
    eps = _census_eps()
    markets = [{"split": br.SCREEN, "covered": "1"} for _ in range(95)] + [{"split": br.SCREEN, "covered": "0"} for _ in range(5)]
    doc = br.census_b(eps, markets, {"n_files": 3})
    w = doc["weights_frozen"]
    assert sum(w.values()) == pytest.approx(1.0) and w["0.1"] == 0.0 and w["0.5"] == pytest.approx(1 / 3, rel=0.02)
    assert doc["gate_GB_pass"] and doc["coverage_audit"]["pass"] and doc["label_B1"] is None
    assert doc["gate_GB2_pass"] is True and doc["b2"]["eligible"] == 1100
    for bad in ({"m2h": 0.5}, {"r_e": 1.0}, {"vwap10": 0.4}, {"net_c": 1.0}, {"maker": {}}):
        with pytest.raises(br.Refused):
            br.census_b([{**eps[0], **bad}], markets, {})
    aud = br.census_b(eps, markets[:60] + [{"split": br.SCREEN, "covered": "0"}] * 40, {})
    assert aud["label_B1"] == "not testable (source limited)"  # audit < 90%: the label is source limited, not "no opportunity"
    small = br.census_b(_census_eps(n_real=200, n_pseudo=200), markets, {})
    assert small["label_B1"] == "not testable (no opportunity: round-level breaks are rare)" and not small["gate_GB_pass"]


def test_census_b_pair_with_fewer_than_30_each_gets_zero_weight_no_renormalisation():
    eps = _census_eps(pairs_=(0.25, 0.5))
    eps += [_ep("real", 0.75, 9000 + i) for i in range(50)] + [_ep("pseudo", 0.75, 9100 + i) for i in range(10)]  # 10 pseudo < 30
    doc = br.census_b(eps, [{"split": br.SCREEN, "covered": "1"}], {})
    assert doc["weights_frozen"]["0.75"] == 0.0 and 0.75 in doc["pairs_zeroed"]
    assert sum(doc["weights_frozen"].values()) < 1.0  # no renormalisation: the weights are n_L / sum n over all real-level episodes


def test_holdout_sealed_for_everything_but_rep_b(tmp_path):
    for job in ("census", "screen-B", "dlad-frame", "rep-D"):
        with pytest.raises(br.Refused):
            br.load_market_tx(tmp_path, br.HOLDOUT, "1", job=job)
    with pytest.raises(br.Refused):
        br.load_episodes(tmp_path, tmp_path, br.HOLDOUT, job="census")
    with pytest.raises(br.Refused):
        br.verify_holdout_seal(tmp_path)  # no seal file


# ---- B1 contrast and tests ---------------------------------------------------------------------------------------------------------------------


def test_contrast_is_per_pair_with_frozen_weights():
    vals = [5, 5, 1, 1, 0, 0, 9, 9, 8, 8]
    arm = ["real", "real", "pseudo", "pseudo", "real", "real", "pseudo", "pseudo", "pseudo", "pseudo"]
    pair = [0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]
    _, est, C = c10.contrast_pseudo(vals, arm, pair, {0.5: 0.75, 0.25: 0.25})
    assert C[0.5] == pytest.approx(4.0) and C[0.25] == pytest.approx(-8.5)  # a pair never borrows another pair's pseudo episodes
    assert est == pytest.approx(0.75 * 4.0 + 0.25 * -8.5)
    _, est0, _ = c10.contrast_pseudo(vals, arm, pair, {0.5: 1.0, 0.25: 0.0})
    assert est0 == pytest.approx(4.0)


def _screen_eps(n_per_cell=200, effect=3.0, seed=2, n_events=60, missing_real=0):
    rng = np.random.default_rng(seed)
    eps = []
    i = 0
    for L in (0.25, 0.5, 0.75):
        for arm in ("real", "pseudo"):
            for _ in range(n_per_cell):
                ev = f"e{rng.integers(0, n_events)}"
                day = f"2026-{5 + rng.integers(0, 4):02d}-{1 + rng.integers(0, 28):02d}"
                r = float(rng.normal(effect if arm == "real" else 0.0, 4.0))
                eps.append(_ep(arm, L, i, ev=ev, day=day, r_e=r, r30=r * 0.8, vol10=float(rng.uniform(5, 50)), n_tx10=int(rng.integers(1, 6)), month=day[:7]))
                i += 1
    for e in eps[:missing_real]:
        e["r_e"] = None
    return eps


W3 = {0.25: 1 / 3, 0.5: 1 / 3, 0.75: 1 / 3}


def test_b1_stat_advances_with_a_clear_effect_and_logs_label_swap_placebo():
    r = br.b1_stat(_screen_eps(effect=3.0), W3, n_draws=6)
    assert r["testable"] and r["p"] < 0.01 and r["b1_cents"] > br.B1_FLOOR_C
    assert r["placebo_label_swap"]["event"]["n_draws"] == 6 and r["placebo_label_swap"]["day"]["n_draws"] == 6
    assert r["worst_case_missing_marks"]["holds"] is True and r["advance"] is True
    assert set(r["per_pair_cents"]) == {"0.25", "0.5", "0.75"}


def test_b1_stat_no_effect_does_not_advance_and_floor_binds():
    assert br.b1_stat(_screen_eps(effect=0.0), W3, n_draws=4)["advance"] is False
    weak = br.b1_stat(_screen_eps(effect=3.0), W3, n_draws=4)
    assert weak["b1_cents"] >= br.B1_FLOOR_C == 0.5


def test_b1_worst_case_missing_marks_scoring():
    eps = _screen_eps(effect=1.0, missing_real=0)
    for e in [e for e in eps if e["arm"] == "real"][:140]:
        e["r_e"] = None  # most real episodes lack a mark: worst case scores them -1c against pseudo missing +1c
    r = br.b1_stat(eps, W3, n_draws=2)
    assert r["n_missing_mark"]["real"] == 140 and r["worst_case_missing_marks"]["n_scored"] >= 140
    assert r["worst_case_missing_marks"]["holds"] is False and r["advance"] is False


def test_b1_cascade_label_when_ratio_below_1_2():
    eps = _screen_eps(effect=3.0)
    for e in eps:
        e["vol10"] = 10.0  # same volume after real and pseudo breaks: ratio 1.0
    r = br.b1_stat(eps, W3, n_draws=4)
    assert r["advance"] and r["label"] == "round-level reversal without a measurable cascade" and r["cascade"]["ratio"] == pytest.approx(1.0)


def _b2_eps(n=1400, mean_net=3.0, seed=4, pseudo_mean=0.0):
    rng = np.random.default_rng(seed)
    eps = []
    for i in range(n):
        for arm, mu in (("real", mean_net), ("pseudo", pseudo_mean)):
            filled = float(rng.choice([0.0, 100.0], p=[0.3, 0.7]))
            net = float(rng.normal(mu, 5.0))
            e = _ep(arm, 0.5, i + (0 if arm == "real" else 10_000), ev=f"e{rng.integers(0, 80)}", day=f"2026-0{5 + rng.integers(0, 4)}-{1 + rng.integers(0, 28):02d}")
            e["maker"] = {"posted": True, "quote": 0.49, "filled": filled, "net_c": net if filled else None, "net_c_hs20": net - 0.5, "net_c_m30": net * 0.9, "rebate_c": 0.1,
                          "gross_c": net + 3, "worst_c": -2.5}
            e["maker_latency"] = {"posted": True, "filled": filled, "net_c": net * 0.9 if filled else None}
            e["month"] = e["day"][:7]
            eps.append(e)
    return eps


def test_b2_stat_floor_route_gate_and_pseudo_attribution():
    r = br.b2_stat(_b2_eps())
    assert r["testable"] and r["b2_cents"] >= br.B2_FLOOR_C and r["route_gate"]["holds"] and r["advance"] is True
    assert r["pseudo_attribution"]["credit_stop_cascade_route"] is True and r["label"] is None
    gen = br.b2_stat(_b2_eps(pseudo_mean=3.0))
    assert gen["advance"] is True and gen["label"] == "a generic post-crossing maker, not a round-level route"
    loss = br.b2_stat(_b2_eps(mean_net=-3.0))
    assert loss["advance"] is False and loss["verdict"] == "reversal exists but the maker still loses: no route"


def test_b2_route_gate_counts_not_posted_and_unfilled_as_zero():
    eps = _b2_eps(n=200)
    for e in eps:
        if e["arm"] == "real":
            e["maker"] = {**e["maker"], "posted": False, "filled": 0.0, "net_c": None}
    for e in [x for x in eps if x["arm"] == "real"][:120]:
        e["maker"] = {**e["maker"], "posted": True, "filled": 100.0, "net_c": 4.0, "net_c_hs20": 3.5, "net_c_m30": 3.6}
    r = br.b2_stat(eps)
    # 120 filled episodes at +4c per share x 100 shares / 100 = 4c each over 200 eligible episodes
    assert r["route_gate"]["mean_per_eligible_cents"] == pytest.approx(120 * 4.0 / 200) and r["not_posted"] == 80


# ---- Gamma whitelist for B (no outcome field at all) -----------------------------------------------------------------------------------------


def test_brk_row_has_no_outcome_or_forbidden_fields():
    m = {"id": "9", "conditionId": "0xc", "question": "Will X happen?", "slug": "x", "clobTokenIds": json.dumps(["a", "b"]), "outcomes": json.dumps(["Yes", "No"]),
         "startDate": "2026-04-01T00:00:00Z", "endDate": "2026-06-01T00:00:00Z", "negRisk": False, "feeType": "politics_fees", "volumeNum": 50000.0,
         "events": [{"id": "5", "title": "T", "series": []}], "description": "long text", "outcomePrices": json.dumps(["1", "0"]), "lastTradePrice": 0.99, "bestBid": 0.9,
         "umaResolutionStatus": "resolved", "closedTime": "2026-06-01", "volume": "50000", "liquidity": "5", "oneDayPriceChange": 0.2}
    r = br.brk_row(m)
    blob = json.dumps(r)
    for f in c10.GAMMA_FORBIDDEN:
        assert f not in r
    assert "50000" not in blob and "0.99" not in blob and "resolved" not in blob and "long text" not in blob
    assert r["vol_ok"] == 1 and set(r) == set(br.FRAME_COLUMNS) and "outcome_prices" not in r
    assert br.brk_row({**m, "volumeNum": 9999.0})["vol_ok"] == 0


def test_frame_filters_declared_exclusions():
    ok = {"end_epoch": c10._epoch("2026-06-01T00:00:00Z"), "start_epoch": c10._epoch("2026-04-01T00:00:00Z"), "vol_ok": 1, "exclusion_class": "", "topic": "politics"}
    assert br.frame_reason(ok) is None
    assert br.frame_reason({**ok, "end_epoch": c10._epoch("2026-04-07T00:00:00Z")}) == "end_outside_window"
    assert br.frame_reason({**ok, "end_epoch": c10._epoch("2026-10-01T00:00:00Z")}) == "end_outside_window"
    assert br.frame_reason({**ok, "vol_ok": 0}) == "volume_below_min"
    assert br.frame_reason({**ok, "exclusion_class": "weather"}) == "weather"
    assert br.frame_reason({**ok, "start_epoch": c10._epoch("2026-05-30T00:00:00Z")}) == "overlap_below_min"
    assert (br.N_SAMPLE, br.MAX_PER_EVENT, br.MIN_VOLUME, br.SEED_SAMPLE, br.SEED_SPLIT) == (1400, 3, 10000.0, "arepo-cb10-brk-sample", "arepo-cb10-brk-split")
