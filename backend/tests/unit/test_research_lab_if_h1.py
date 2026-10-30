"""IF-H1 historical machinery tests (no network)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import if_h1 as ih

RULE = {"c_fee_categories": ["sports"], "c_keywords": ["vs", "bitcoin"],
        "a_keywords": ["strike*", "nobel"], "b_keywords": ["out", "election*"]}
SPEC = {"identity": {"fresh_age_days": 14, "fresh_max_prior_trades": 100, "dormant_days": 60,
                     "focus_F": 0.8, "focus_max_markets": 3},
        "label": {"horizon_days": 7, "delta": 0.10, "max_quote_age_s": 21600},
        "vetoes": {"pre_trend_window_s": 7200}}
D = 86400


def test_classify_order_and_word_boundaries():
    assert ih.classify("Lakers vs. Celtics", None, RULE) == "C"
    assert ih.classify("Will the US strike Iran?", None, RULE) == "A"
    assert ih.classify("Maduro out by Jan 31?", "politics", RULE) == "B"
    assert ih.classify("Anything", "sports", RULE) == "C"
    assert ih.classify("Outback steakhouse", None, RULE) == "unclassified"  # 'out' whole word
    assert ih.classify("Bitcoin strike", None, RULE) == "C"  # C checked first


def test_acquisitions_and_gate_points():
    cen = pd.DataFrame({
        "ts": [0, 100, 200, 9000, 20000], "condition_id": ["m"] * 5,
        "wallet_hash": ["w"] * 5, "side": ["BUY", "SELL", "BUY", "BUY", "BUY"],
        "outcome_index": [0, 1, 0, 0, 0], "price": [0.1, 0.9, 0.2, 0.1, 0.1],
        "size": [5000, 2000, 4000, 1000, 20000]})
    acq = ih.acquisitions(cen)
    assert list(acq["o"]) == [0, 0, 0, 0, 0] and np.isclose(acq["p_o"].iloc[1], 0.1)
    gp = ih.gate_points(acq, n_min=1000.0, gap_s=7200)
    # episode 1: prints at 0,100,200 (n = 500, 200, 800) -> gate at ts 200; 9000 starts a new
    # episode (gap > 2h) that never reaches $1000; 20000 is a third episode reaching it at once
    assert list(gp["t_gate"]) == [200, 20000]
    r = gp.iloc[0]
    assert r["t_E"] == 0 and np.isclose(r["n_E"], 1500) and np.isclose(r["S"], 11000)
    assert np.isclose(r["pbar"], 1500 / 11000)


def test_v_m_and_x1():
    cen = pd.DataFrame({"ts": [D * 10 + 5, D * 11 + 5], "condition_id": ["m", "m"],
                        "cash": [1000.0, 3000.0]})
    daily = ih.daily_notional(cen)
    vm = ih.v_m(daily, np.array(["m"]), np.array([D * 12 + 1.0]), days=2)
    assert vm[0] == 2000.0
    assert ih.x1(np.array([10000.0]), np.array([0.1]), np.array([0.0]), 100.0)[0] == 90.0


def _act(ts, typ="TRADE", cid="m", usdc=10.0, ev="e"):
    return {"timestamp": ts, "type": typ, "conditionId": cid, "usdcSize": usdc, "eventSlug": ev}


def test_wallet_profile_identity():
    t = 100 * D
    fresh = ih.wallet_profile([_act(t - 2 * D)], None, t, "e", "m", 500)
    assert fresh["complete"] and fresh["k_w"] == 1 and fresh["F"] == 1.0
    idf = ih.identity(fresh, 5000.0, t, SPEC)
    assert idf["fresh"] and idf["focused"] and idf["identity_pass"]
    old = ih.wallet_profile([_act(t - 300 * D, cid=f"c{i}") for i in range(10)]
                            + [_act(t - D, typ="REWARD")], None, t, "e", "m", 500)
    io = ih.identity(old, 5000.0, t, SPEC)
    assert not io["fresh"] and not io["focused"] and not io["dormant"]
    assert old["reward_or_merge_30d"] is True
    dormant = ih.wallet_profile([_act(t - 200 * D, cid=f"c{i}", usdc=50) for i in range(5)],
                                None, t, "e", "m", 500)
    assert ih.identity(dormant, 1000.0, t, SPEC)["dormant"]
    # truncated page: unknown k_w -> not fresh even if young
    full = [_act(t - D + i) for i in range(500)]
    tr = ih.wallet_profile(full, [], t, "e", "m", 500)
    assert tr["k_w"] is None and not ih.identity(tr, 5000.0, t, SPEC)["fresh"]
    # future events are ignored
    fut = ih.wallet_profile([_act(t + 5)], None, t, "e", "m", 500)
    assert fut["first_trade_ts"] is None


def test_label_7d_and_settled_proxy():
    ts = np.arange(0, 10 * D, 600, dtype=float)
    p = np.where(ts < 5 * D, 0.1, 0.3)
    lab = ih.label_7d(ts, p, 1 * D, SPEC)
    assert lab["hit"] == 1.0 and np.isclose(lab["D7"], 0.2)
    ts2 = np.arange(0, 3 * D, 600, dtype=float)
    lab2 = ih.label_7d(ts2, np.where(ts2 < 2 * D, 0.1, 0.99), 1 * D, SPEC)
    assert lab2["settled_proxy"] and lab2["hit"] == 1.0
    lab3 = ih.label_7d(ts2, np.full(len(ts2), 0.5), 1 * D, SPEC)
    assert np.isnan(lab3["hit"])


def test_top_k_and_controls():
    c = pd.DataFrame({"week": [1, 1, 1, 2], "event_key": ["a", "a", "b", "c"], "o": [0, 0, 0, 0],
                      "X1": [5.0, 9.0, 7.0, 1.0], "condition_id": ["m1", "m2", "m3", "m4"],
                      "t_gate": [1, 2, 3, 4]})
    top = ih.top_k_per_week(c, 1)
    assert list(top["X1"]) == [9.0, 1.0]
    alerts = pd.DataFrame({"cls": ["A"], "band": [0], "week": [1], "event_key": ["a"],
                           "X1": [10.0], "tte_days": [5.0]})
    pool = pd.DataFrame({"cls": ["A", "A", "A", "B"], "band": [0, 0, 0, 0], "week": [1, 1, 1, 1],
                         "event_key": ["a", "x", "y", "z"], "X1": [10.0, 11.0, 100.0, 10.0],
                         "tte_days": [5.0, 5.0, 5.0, 5.0], "condition_id": list("pqrs"),
                         "t_gate": [1, 2, 3, 4]})
    m = ih.match_controls(alerts, pool, 5)
    assert m[0] == [1, 2]  # same event and other class excluded, nearest first


def test_cluster_boot_excess_and_mde():
    r = ih.cluster_boot_excess(np.array([1.0, 1.0, 0.0, 1.0]), np.array(list("abcd")), 500, 1)
    assert r["mean"] == 0.75 and r["clusters"] == 4 and 0 < r["p_one_sided"] <= 1
    assert 0 < ih.two_sample_mde(0.1, 300, 1000) < ih.two_sample_mde(0.1, 30, 100)


def test_load_spec_refuses_unfrozen_or_modified(tmp_path):
    spec = {"rule_id": "x", "a": 1}
    sp, ix = tmp_path / "s.json", tmp_path / "i.json"
    sp.write_text(json.dumps(spec))
    with pytest.raises(ih.SpecError):
        ih.load_spec(sp, ix)
    ix.write_text(json.dumps({"sha256": ih.spec_sha256(spec)}))
    assert ih.load_spec(sp, ix) == spec
    sp.write_text(json.dumps({**spec, "a": 2}))
    with pytest.raises(ih.SpecError):
        ih.load_spec(sp, ix)
