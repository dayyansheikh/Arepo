"""Surprise-move labels, pre-event features and matched negatives (research lab)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from astrolabe.research_lab import history_backfill as hb
from astrolabe.research_lab import surprise_moves as sm

STEP = 600.0


def series(days=5, level=0.10):
    ts = np.arange(0, days * 86400, STEP)
    return ts, np.full(len(ts), level)


def test_label_spec_hash_is_pinned():
    # the label definitions were fixed and logged before any feature was computed
    assert sm.label_spec_sha256() == (
        "d9cf42f7392a29cb27aa4e09deb9886c4e802e761e614cca8efc6af394a0cd73")


def test_sharp_jump_is_a_surprise_with_departure_just_before_the_jump():
    ts, p = series()
    j = int(3 * 86400 // STEP)
    p[j] = 0.25
    p[j + 1:] = 0.40
    e = sm.detect_events(ts, p, min_move=0.15, window_s=21600)
    assert len(e) == 1
    r = e.iloc[0]
    assert r["t_arr"] == ts[j] and r["t_dep"] == ts[j - 1] and r["direction"] == 1
    assert bool(r["surprise"]) and r["reason"] == "ok" and r["pre_drift_24h"] == 0
    # cooloff: a second jump 2 h later is not a new event
    p2 = p.copy()
    p2[j + 12:] = 0.60
    assert len(sm.detect_events(ts, p2, min_move=0.15, window_s=21600)) == 1


def test_gradual_drift_is_not_sharp_and_pre_drift_is_excluded():
    ts, p = series()
    j = int(3 * 86400 // STEP)
    p[j:j + 72] = 0.10 + 0.2 * np.arange(72) / 72  # 0.20 over 12 h: never 0.15 within 6 h
    p[j + 72:] = 0.30
    assert sm.detect_events(ts, p, min_move=0.15, window_s=21600).empty
    # drift of 0.08 over the prior day, then a jump: a sharp move but not a surprise
    ts, p = series()
    p[j - 144:j] = 0.10 + 0.08 * np.arange(144) / 144
    p[j:] = 0.40
    e = sm.detect_events(ts, p, min_move=0.15, window_s=21600)
    assert len(e) == 1 and not bool(e.iloc[0]["surprise"]) and e.iloc[0]["reason"] == "pre_drift"


def test_final_hour_before_end_and_unknown_pre_window_are_excluded():
    ts, p = series()
    j = int(3 * 86400 // STEP)
    p[j:] = 0.40
    e = sm.detect_events(ts, p, end_epoch=ts[j] + 1800, min_move=0.15, window_s=21600)
    assert e.iloc[0]["reason"] == "final_hour_before_end"
    # too little history before the departure: unknown, never treated as flat
    ts2, p2 = ts[j - 3:], p[j - 3:]
    e2 = sm.detect_events(ts2, p2, min_move=0.15, window_s=21600)
    assert len(e2) == 0 or e2.iloc[0]["reason"] == "pre_window_unknown"


def test_variants_extreme_and_to_resolution():
    ts, p = series(level=0.10)
    j = int(3 * 86400 // STEP)
    p[j:] = 0.22  # 0.12 move from an extreme price: variant only
    ev = sm.events_all_variants(ts, p)
    assert set(ev["variant"]) == {"extreme10_6h"}
    ts, p = series(level=0.50)
    p[j:] = 0.99
    ev = sm.events_all_variants(ts, p)
    assert {"sharp15_6h", "to_resolution_6h"} <= set(ev["variant"])


def trades(ts_list, sizes, sides=None, wallets=None, oi=0, price=0.3):
    n = len(ts_list)
    return pd.DataFrame({"ts": ts_list, "side": sides or ["BUY"] * n, "size": sizes,
                         "price": [price] * n, "outcome_index": [oi] * n,
                         "wallet_hash": wallets or [f"{i:064x}" for i in range(n)]})


def test_features_use_only_trades_strictly_before_t_and_mark_uncovered_windows():
    ts, p = series(level=0.30)
    t = np.array([2 * 86400.0])
    tr = trades([t[0] - 100, t[0] - 1000, t[0] - 5000, t[0]], [10, 20, 30, 1000],
                sides=["BUY", "BUY", "SELL", "BUY"], wallets=["a", "a", "b", "c"])
    f = sm.surprise_features(tr, t, np.array([0.3]), ts, p, covered_from=-np.inf)
    assert f["sm_n_15m"][0] == 1 and f["sm_n_1h"][0] == 2 and f["sm_n_6h"][0] == 3
    assert f["sm_n_24h"][0] == 3  # the trade at exactly t is excluded
    assert abs(f["sm_imb_6h"][0] - (10 + 20 - 30) / 60) < 1e-12
    assert f["sm_n_wallets_6h"][0] == 2 and f["sm_top1_6h"][0] == 0.5
    assert f["sm_same_side_share_6h"][0] == 0.5 and f["sm_n_same_side_6h"][0] == 1
    assert f["sm_covered_24h"][0] == 1.0
    # window not inside the fetched history: NaN, never 0
    g = sm.surprise_features(tr, t, np.array([0.3]), ts, p, covered_from=t[0] - 30000)
    assert np.isnan(g["sm_n_24h"][0]) and g["sm_covered_24h"][0] == 0.0
    assert g["sm_n_6h"][0] == 3 and np.isnan(g["sm_burst_6h"][0])  # burst needs the 24h base
    # no trades at all: all NaN, covered 0
    h = sm.surprise_features(None, t, np.array([0.3]), ts, p, covered_from=np.inf)
    assert np.isnan(h["sm_n_1h"][0]) and h["sm_covered_1h"][0] == 0.0


def test_new_wallet_features_respect_burn_in_and_first_seen():
    ts, p = series(days=40, level=0.30)
    t = np.array([30 * 86400.0])
    old, new = "a" * 64, "b" * 64
    tr = trades([t[0] - 100, t[0] - 200], [10, 10], wallets=[old, new])
    fs = hb.FirstSeen(np.array([int(old[:15], 16), int(new[:15], 16)]),
                      np.array([1.0, t[0] - 86400.0]), 1.0)  # index starts at day 0
    f = sm.surprise_features(tr, t, np.array([0.3]), ts, p, -np.inf, first_seen=fs)
    assert f["sm_new_n_1h"][0] == 1 and f["sm_new_vol_share_1h"][0] == 0.5
    early = np.array([5 * 86400.0])  # inside the 14-day burn-in: NaN
    tr2 = trades([early[0] - 100], [10], wallets=[new])
    g = sm.surprise_features(tr2, early, np.array([0.3]), ts, p, -np.inf, first_seen=fs)
    assert np.isnan(g["sm_new_n_1h"][0])


def test_question_stem_groups_deadline_ladders():
    a = sm.question_stem("US strikes Iran by February 28, 2026?")
    b = sm.question_stem("US strikes Iran by March 31, 2026?")
    assert a == b == "us strikes iran"


def rows_frame(n_pos=3, k=5):
    rng = np.random.default_rng(0)
    n = 400
    t = 7200.0 * np.arange(n)
    df = pd.DataFrame({"market_id": ["m1"] * n, "event_id": ["e1"] * n, "t": t,
                       "fee_category": ["politics"] * n, "traded_before_t": 1.0,
                       "mid": 0.3, "sm_log_notional_24h": rng.normal(size=n),
                       "ml_own_dmid_prev": rng.normal(scale=0.01, size=n),
                       "question_stem": "q"})
    df["y_dep_2h"] = False
    df.loc[[50, 150, 250][:n_pos], "y_dep_2h"] = True
    near = np.zeros(n, bool)
    for i in [50, 150, 250][:n_pos]:
        near[i - 12:i + 13] = True
    df["near_any_dep"] = near
    return df


def test_match_negatives_uses_same_stratum_and_clean_rows():
    df = rows_frame()
    df["mid"] = 0.3
    df.loc[df["y_dep_2h"], "sm_log_notional_24h"] = 5.0  # positives in the top tercile
    cc = sm.match_negatives(df)
    assert cc.attrs["n_pos"] == 3 and (cc["y"] == 1).sum() == 3
    neg = cc[cc["y"] == 0]
    assert not neg["near_any_dep"].any() and not neg["y_dep_2h"].any()
    assert set(neg["stratum"]) <= set(cc[cc["y"] == 1]["stratum"])
    assert len(neg) + cc.attrs["negatives_short"] == 15
    # deterministic under the seed
    again = sm.match_negatives(df)
    assert list(again.index) == list(cc.index)


def test_group_moves_exclude_own_market():
    df = pd.DataFrame({"market_id": ["a", "b", "c", "d"], "event_id": ["e", "e", "e", ""],
                       "t": [0.0, 0.0, 0.0, 0.0], "question_stem": ["q", "q", "", ""],
                       "ml_own_dmid_prev": [0.5, 0.1, 0.2, 0.9]})
    out = sm.add_group_moves(df)
    assert list(out["sib_n"]) == [2, 2, 2, 0]
    assert list(out["sib_max_abs_chg_2h"][:3]) == [0.2, 0.5, 0.5]
    assert list(out["ladder_n"][:2]) == [1, 1] and out["ladder_max_abs_chg_2h"][0] == 0.1
    assert np.isnan(out["sib_max_abs_chg_2h"][3])


def test_price_context_matches_origin_frame():
    rng = np.random.default_rng(1)
    ts = np.arange(0, 12 * 86400, STEP)
    p = np.clip(0.4 + np.cumsum(rng.normal(scale=0.005, size=len(ts))), 0.05, 0.95)
    rec = {"market_id": "m", "event_id": "", "condition_id": "0x1", "fee_category": "politics",
           "status": "active", "liquidity": np.nan, "volume": 1.0, "created_at": "",
           "start_epoch": 0.0, "end_epoch": 20 * 86400.0, "close_epoch": np.nan, "closed": "",
           "stratum": ""}
    of = hb.origin_frame(rec, ts, p, None, False, "r", None)
    i = len(of) // 2
    t = float(of["t_i"].iloc[i])
    live = sm.price_context(ts, p, t, created_ts=0.0, end_ts=20 * 86400.0)
    for src, dst in sm.CONTEXT_MAP.items():
        if dst in live and src in of:
            a, b = float(of[src].iloc[i]), live[dst]
            assert (np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-9, (dst, a, b)
    assert live["dow"] == float(((t // 86400) + 3) % 7)


def test_standardiser_falls_back_when_mad_is_floating_point_noise():
    from astrolabe.research_lab import surprise_learn as sl

    x = np.column_stack([np.where(np.arange(100) < 70, 1.0 - 1e-15, 0.2), np.arange(100.0)])
    st = sl.Standardiser.fit(x, ["a", "b"])
    assert st.scale["a"] > 0.1 and abs(st.center["a"] - 1.0) < 1e-9  # std, not the ~1e-15 MAD
    z = st.transform(np.array([[np.nan, 49.5]]), ["a", "b"])
    assert z[0, 0] == 0.0 and abs(z[0, 1]) < 1e-9  # missing -> centre; median -> 0


def test_enet_rule_spec_reproduces_logit_up_to_intercept():
    from astrolabe.research_lab import detector_eval as de
    from astrolabe.research_lab import surprise_learn as sl

    rng = np.random.default_rng(3)
    cols = ["sm_abs_imb_1h", "rv_1d", "dow"]
    x = rng.normal(size=(300, 3))
    y = (x[:, 1] + 0.3 * rng.normal(size=300) > 0).astype(int)
    m = sl.fit_enet(x, y, cols, C=1.0)
    spec = m.to_rule_spec("sm_t", "1", "sm_imb_1h", "t")
    xt = rng.normal(size=(20, 3))
    panel = pd.DataFrame(xt, columns=cols)
    panel["sm_imb_1h"] = rng.normal(size=20)
    sc = de.score_rule(spec, panel)
    assert np.allclose(sc["score"].to_numpy() + m.intercept, m.logit(xt))


def test_merge_first_seen_takes_the_earlier_time_and_keeps_burn_in_origin(tmp_path):
    import json

    a, b, c = "a" * 64, "b" * 64, "c" * 64
    fsi = hb.FirstSeen(np.array(sorted(hb.FirstSeen.key(h) for h in (a, b)), dtype=np.int64),
                       np.array([1000.0, 2000.0]), 1000.0)
    tbl = tmp_path / "ft.jsonl"
    tbl.write_text("\n".join(json.dumps(x) for x in (
        {"wallet_hash": a, "first_trade_ts": 10},  # earlier than in-sample: wins
        {"wallet_hash": b, "first_trade_ts": 5000},  # later than in-sample: ignored
        {"wallet_hash": c, "first_trade_ts": 42},  # new wallet
        {"wallet_hash": "d" * 64, "first_trade_ts": None})) + "\n")
    merged, info = sm.merge_first_seen(fsi, tbl)
    got = merged.lookup(np.array([a, b, c, "e" * 64]))
    assert list(got[:3]) == [10.0, 2000.0, 42.0] and np.isnan(got[3])
    assert merged.g0 == 1000.0 and info == {"table_wallets": 3, "table_wallets_in_sample": 2,
                                            "index_wallets": 3}


def test_weighted_evaluation_and_matched_excess():
    from astrolabe.research_lab import surprise_learn as sl

    rng = np.random.default_rng(5)
    n = 2000
    t = 7200.0 * (np.arange(n) // 20)
    test = pd.DataFrame({"market_id": [f"m{i % 20}" for i in range(n)],
                         "event_id": [f"e{i % 10}" for i in range(n)], "t": t,
                         "cluster": [f"e{i % 10}" for i in range(n)],
                         "mid": 0.3, "fee_category": "politics",
                         "sm_log_notional_24h": rng.normal(size=n),
                         "sm_imb_1h": rng.normal(size=n), "fwd_move_6h": 0.0,
                         "fwd_move_24h": 0.0})
    score = rng.normal(size=n)
    test["y_dep_6h"] = score > 2.0  # the score is perfectly informative at the top
    test["y_dep_2h"] = False
    w = np.where(np.arange(n) % 2 == 0, 3.0, 1.0)
    events = pd.DataFrame({"market_id": [], "t_dep": [], "t_arr": []})
    r = sl.evaluate_scores(test, score, np.sign(test["sm_imb_1h"].to_numpy()), events,
                           n_boot=50, budgets=(0.01,), weights=w)
    b = r["budgets"]["0.01"]
    assert b["precision_6h"] == 1.0 and b["weighted"]["precision_6h"] == 1.0
    assert abs(b["weighted"]["base_rate_6h"] - np.sum(w * test["y_dep_6h"]) / w.sum()) < 1e-12
    assert b["matched_controls"]["excess_mean"] > 0.9
    assert b["weighted"]["matched_excess"]["excess_mean"] > 0.9
    assert "weighted" not in b["matched_controls"]
