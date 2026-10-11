"""Synthetic tests for the DEVELOPMENT lead/lag screen (origin-only sibling features)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from astrolabe.research_lab import features
from astrolabe.research_lab import leadlag_screen as ls

COLS = ls.USECOLS


def snap(rows: list[dict]) -> pd.DataFrame:
    base = {"event_id": None, "neg_risk": np.nan, "neg_risk_market_id": None,
            "neg_risk_other": np.nan, "event_neg_risk_augmented": np.nan,
            "received_utc": "2026-10-10T00:00:00Z", "best_bid": 0.4, "best_ask": 0.42,
            "spread": 0.02, "last_trade_price": 0.41, "chg_1h": 0.0, "chg_1d": 0.0,
            "chg_1w": 0.0, "liquidity": 100.0, "volume24hr": 10.0,
            "end_date": "2027-01-01T00:00:00Z", "closed": False, "active": True, "binary": 1}
    return pd.DataFrame([{**base, **r} for r in rows])[COLS]


def test_sibling_aggregation_excludes_self_and_is_liquidity_weighted():
    s = snap([
        {"market_id": "a", "event_id": "e", "chg_1h": 0.50, "liquidity": 10.0},
        {"market_id": "b", "event_id": "e", "chg_1h": 0.10, "liquidity": 100.0},
        {"market_id": "c", "event_id": "e", "chg_1h": -0.20, "liquidity": 300.0},
    ])
    f = ls.sibling_features(s)
    assert np.isclose(f.loc["a", "l1_sib_chg"], (0.10 * 100 - 0.20 * 300) / 400)
    assert np.isclose(f.loc["b", "l1_sib_chg"], (0.50 * 10 - 0.20 * 300) / 310)
    assert np.isclose(f.loc["c", "l1_sib_chg"], (0.50 * 10 + 0.10 * 100) / 110)
    assert (f["l1_no_sib"] == 0).all() and (f["n_sib"] == 2).all()


def test_sibling_features_use_origin_snapshot_only():
    """The function sees one snapshot; changing the next snapshot cannot change the feature."""
    rows = [{"market_id": m, "event_id": "e", "chg_1h": c} for m, c in
            (("a", 0.1), ("b", 0.2), ("c", -0.3))]
    origin, nxt = snap(rows), snap([{**r, "chg_1h": 9.0} for r in rows])
    before = ls.sibling_features(origin)
    pairs_i, _ = ls.build_period(origin, nxt, "2026-10-10T06:00:00Z", 0, None)
    pairs_j, _ = ls.build_period(origin, snap([{**r, "chg_1h": -7.0, "best_bid": 0.5,
                                                 "best_ask": 0.52} for r in rows]),
                                 "2026-10-10T06:00:00Z", 0, None)
    got = pairs_i.set_index("market_id")["l1_sib_chg"]
    assert np.allclose(got.reindex(before.index), before["l1_sib_chg"])
    for col in ("l1_sib_chg", "l2_diverg", "log_n_sib", "log_n_moving", "l3_dS"):
        assert np.allclose(pairs_i[col], pairs_j[col])
    assert not np.allclose(pairs_i["dmid"], pairs_j["dmid"])  # only the target differs


def test_single_market_event_and_missing_event_are_flagged():
    s = snap([
        {"market_id": "solo", "event_id": "x", "chg_1h": 0.3},
        {"market_id": "n1", "event_id": None, "chg_1h": 0.3},
        {"market_id": "n2", "event_id": None, "chg_1h": 0.4},
        {"market_id": "p", "event_id": "y", "chg_1h": 0.1},
        {"market_id": "q", "event_id": "y", "chg_1h": np.nan},
    ])
    f = ls.sibling_features(s)
    for m in ("solo", "n1", "n2", "p"):  # p's only sibling has no chg_1h
        assert f.loc[m, "l1_no_sib"] == 1 and f.loc[m, "l1_sib_chg"] == 0
        assert f.loc[m, "n_sib"] == 0
    assert f.loc["q", "l1_no_sib"] == 0 and np.isclose(f.loc["q", "l1_sib_chg"], 0.1)


def test_inactive_closed_siblings_excluded_and_zero_liquidity_falls_back_to_equal_weights():
    s = snap([
        {"market_id": "a", "event_id": "e", "chg_1h": 0.0, "liquidity": 0.0},
        {"market_id": "b", "event_id": "e", "chg_1h": 0.2, "liquidity": 0.0},
        {"market_id": "c", "event_id": "e", "chg_1h": 0.4, "liquidity": 0.0},
        {"market_id": "d", "event_id": "e", "chg_1h": 5.0, "closed": True},
        {"market_id": "z", "event_id": "e", "chg_1h": 5.0, "active": False},
    ])
    f = ls.sibling_features(s)
    assert np.isclose(f.loc["a", "l1_sib_chg"], 0.3)
    assert f.loc["a", "n_sib"] == 2


def test_moving_count_threshold():
    s = snap([
        {"market_id": "a", "event_id": "e", "chg_1h": 0.0},
        {"market_id": "b", "event_id": "e", "chg_1h": 0.02},
        {"market_id": "c", "event_id": "e", "chg_1h": -0.011},
        {"market_id": "d", "event_id": "e", "chg_1h": 0.01},
    ])
    assert ls.sibling_features(s).loc["a", "n_moving_sib"] == 2


def nr(rows):
    return snap([{"neg_risk": 1, "neg_risk_market_id": "g", "neg_risk_other": 0,
                  "event_neg_risk_augmented": 0, **r} for r in rows])


def test_group_change_uses_previous_snapshot_only():
    prev = nr([{"market_id": "a", "best_bid": 0.30, "best_ask": 0.32},
               {"market_id": "b", "best_bid": 0.40, "best_ask": 0.42},
               {"market_id": "c", "best_bid": 0.10, "best_ask": 0.12}])
    cur = nr([{"market_id": "a", "best_bid": 0.35, "best_ask": 0.37},
              {"market_id": "b", "best_bid": 0.40, "best_ask": 0.42},
              {"market_id": "c", "best_bid": 0.20, "best_ask": 0.22}])
    d = ls.group_change(ls.neg_risk_table(cur), ls.neg_risk_table(prev))
    assert np.isclose(d["g"], 0.05 + 0.0 + 0.10)
    # the function takes no later snapshot; an altered "next" table cannot matter, and a
    # different previous table does
    prev2 = nr([{"market_id": "a", "best_bid": 0.0, "best_ask": 0.0}])
    assert len(ls.group_change(ls.neg_risk_table(cur), ls.neg_risk_table(prev2))) == 0
    assert len(ls.group_change(ls.neg_risk_table(cur), None)) == 0


def test_group_change_in_pairs_matches_previous_and_flags_absent_members():
    prev = nr([{"market_id": "a", "event_id": "e", "best_bid": 0.30, "best_ask": 0.32},
               {"market_id": "b", "event_id": "e", "best_bid": 0.40, "best_ask": 0.42}])
    cur = nr([{"market_id": "a", "event_id": "e", "best_bid": 0.35, "best_ask": 0.37},
              {"market_id": "b", "event_id": "e", "best_bid": 0.45, "best_ask": 0.47},
              {"market_id": "x", "event_id": "f", "neg_risk_market_id": "other"}])
    nxt = snap([{"market_id": m, "event_id": "e"} for m in ("a", "b", "x")])
    pairs, cnt = ls.build_period(cur, nxt, "2026-10-10T06:00:00Z", 0, ls.neg_risk_table(prev))
    p = pairs.set_index("market_id")
    assert np.isclose(p.loc["a", "l3_dS"], 0.10) and p.loc["a", "l3_in"] == 1
    assert p.loc["x", "l3_in"] == 0 and p.loc["x", "l3_dS"] == 0
    assert bool(p["nr_data"].all()) and cnt["l3_data_available"]
    first, _ = ls.build_period(cur, nxt, "2026-10-10T06:00:00Z", 0, None)
    assert (first["l3_in"] == 0).all() and not first["nr_data"].any()


def test_tainted_and_small_groups_excluded():
    prev = nr([{"market_id": "a"}, {"market_id": "b", "neg_risk_other": 1}])
    assert len(ls.neg_risk_table(prev)) == 0
    one = nr([{"market_id": "a"}])
    assert len(ls.group_change(ls.neg_risk_table(one), ls.neg_risk_table(one))) == 0


def test_features_registered_temporarily_and_origin_only():
    assert "l1_sib_chg" not in features.REGISTRY
    with ls.registered_features():
        assert set(ls.NEW_FEATURES) <= set(features.REGISTRY)
    assert "l1_sib_chg" not in features.REGISTRY
    for v in ls.FAMILY.values():
        assert not set(v["features"]) & features.LABEL_COLUMNS


def test_diff_handles_either_key_order():
    blk = {"diffs": {"B3|R": {"diff_r2": 0.02, "ci_lo": 0.01, "ci_hi": 0.05}}}
    assert ls._diff(blk, "B3", "R")["diff_r2"] == 0.02
    flipped = ls._diff(blk, "R", "B3")
    assert flipped == {"diff_r2": -0.02, "ci_lo": -0.05, "ci_hi": -0.01}
    assert ls._diff(blk, "R", "X") is None
