# ruff: noqa: E501
"""Maker P&L / liquidity-reward development tooling (paper only, no network)."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import maker_rewards as mr


def test_fill_direction_and_price_in_outcome0_terms():
    side = np.array(["BUY", "SELL", "BUY", "SELL"])
    oi = np.array([0, 0, 1, 1])
    p = np.array([0.3, 0.3, 0.3, 0.3])
    d0, p0 = mr.fill_arrays(side, oi, p)
    assert d0.tolist() == [1, -1, -1, 1]
    assert p0.tolist() == pytest.approx([0.3, 0.3, 0.7, 0.7])


def test_maker_pnl_is_minus_taker_and_costs_complement():
    # taker buys outcome 0 at 0.3; outcome 0 wins -> taker +0.7, maker -0.7; maker bought outcome 1 at 0.7
    f = mr.per_fill(["BUY"], [0], [0.3], [10.0], [0.0], y0=1.0, fee_category="politics")
    assert f["maker_pnl"][0] == pytest.approx(-0.7)
    assert f["maker_cost"][0] == pytest.approx(0.7)
    assert f["taker_cost"][0] == pytest.approx(0.3)
    assert f["fee"][0] == 0.0  # before the fee rollout
    # taker buys outcome 1 at 0.8 (= short outcome 0 at 0.2); outcome 1 wins -> taker +0.2, maker -0.2
    g = mr.per_fill(["BUY"], [1], [0.8], [1.0], [0.0], y0=0.0, fee_category="politics")
    assert g["maker_pnl"][0] == pytest.approx(-0.2)
    assert g["maker_cost"][0] == pytest.approx(0.2)  # maker is long outcome 0 at 0.2


def test_fee_and_rebate_after_rollout():
    ts = mr.FEE_FROM_UTC["default"] + 10
    f = mr.per_fill(["SELL"], [0], [0.5], [1.0], [ts], y0=0.0, fee_category="politics")
    assert f["fee"][0] == pytest.approx(0.04 * 0.25)
    assert f["rebate"][0] == pytest.approx(0.25 * 0.04 * 0.25)
    assert mr.docs_fee_rate("other:zero_fees", ts) == 0.0
    assert mr.docs_fee_rate("unknown", ts) == 0.0
    assert mr.docs_fee_rate("crypto", mr.FEE_FROM_UTC["crypto"] - 1) == 0.0


@pytest.mark.parametrize("raw,want", [('["1", "0"]', 1.0), ('["0", "1"]', 0.0), ('["0.5", "0.5"]', None),
                                      ('["0.15", "0.85"]', None), ("", None), ("garbage", None)])
def test_parse_resolution(raw, want):
    assert mr.parse_resolution(raw) == want


def test_market_class_order():
    assert mr.market_class("sports", 1, 0, 1e9) == "sports"
    assert mr.market_class("crypto", 0, 0, 3600) == "crypto_short"
    assert mr.market_class("crypto", 1, 0, 40 * 86400) == "crypto_other"
    assert mr.market_class("politics", 1, 0, 1e7) == "negrisk_multi"
    assert mr.market_class("politics", 0, 0, 1e7) == "politics_binary"
    assert mr.market_class("unknown", 0, 0, 1e7) == "single_binary"


def test_accumulator_unit_mean_and_identity():
    acc = mr.Accumulator()
    for i in range(40):
        y0 = float(i % 2)
        f = mr.per_fill(["BUY", "SELL"], [0, 0], [0.6, 0.6], [1.0, 3.0], [0.0, 0.0], y0=y0, fee_category="politics")
        acc.add_market(f"e:{i}", "politics_binary", 10 * 86400.0, f)
    units, tab = acc.unit_table(classes=["politics_binary"])
    assert len(units) == 40
    s = mr.summarise(tab, n_boot=200, seed=1)
    # per event: maker pnl = -[1*(y-0.6)] + 3*(y-0.6) = 2*(y-0.6) over 4 shares; half the events y = 1
    exp = 100.0 * sum(2.0 * ((i % 2) - 0.6) for i in range(40)) / 160.0
    assert s["maker_gross_c_pooled"] == pytest.approx(exp)
    assert s["taker_net_c_pooled"] == pytest.approx(-exp)  # no fee before rollout
    lo, hi = s["maker_gross_c_pooled_ci"]
    assert lo <= s["maker_gross_c_pooled"] <= hi
    # fill-weighted: per event -(y-0.6) + (y-0.6) = 0
    assert s["maker_gross_c_pooled_fill"] == pytest.approx(0.0)
    assert s["maker_return_pct_pooled"] == pytest.approx(100.0 * sum(2.0 * ((i % 2) - 0.6) for i in range(40))
                                                         / (40 * (1 * 0.4 + 3 * 0.6)))
    assert mr.summarise(tab[:5], n_boot=10)["status"].startswith("not estimated")
    _, none = acc.unit_table(classes=["sports"])
    assert none.shape[0] == 0


def test_horizon_and_price_bands():
    acc = mr.Accumulator()
    f = mr.per_fill(["BUY", "BUY"], [0, 0], [0.95, 0.05], [1.0, 1.0], [0.0, 0.0], y0=1.0, fee_category="tech")
    acc.add_market("e:1", "single_binary", 40 * 86400.0, f)
    keys = {k[2:] for k in acc.sums}
    # maker sold outcome 0 => bought outcome 1 at 0.05 and 0.95
    assert keys == {("h>30d", "p<0.10"), ("h>30d", "p>=0.90")}


def test_reward_score_and_qmin():
    assert mr.reward_score(0.045, 0.0) == pytest.approx(1.0)
    assert mr.reward_score(0.045, 0.0225) == pytest.approx(0.25)
    assert mr.reward_score(0.045, 0.045) == 0.0
    assert mr.q_min(3.0, 0.0, 0.5) == pytest.approx(1.0)  # single-sided at 1/c inside [0.1, 0.9]
    assert mr.q_min(3.0, 0.0, 0.95) == 0.0  # two-sided only outside


def test_parse_daily_rate():
    raw = json.dumps([{"rewardsDailyRate": 5, "startDate": "2026-10-19", "endDate": "2500-12-31"},
                      {"rewardsDailyRate": 2, "startDate": "2026-11-01", "endDate": None}])
    assert mr.parse_daily_rate(raw) == 7.0
    assert mr.parse_daily_rate(raw, "2026-10-20") == 5.0
    assert mr.parse_daily_rate("", "2026-10-20") == 0.0
    assert mr.parse_daily_rate("{bad", None) == 0.0


def _tok(bb, ba, bs, as_, b1, a1, b5, a5):
    return {"best_bid": bb, "best_ask": ba, "bid_size_1": bs, "ask_size_1": as_, "depth_bid_1c": b1,
            "depth_ask_1c": a1, "depth_bid_5c": b5, "depth_ask_5c": a5}


def test_paper_quote_reward_bounds_and_empty_book():
    t0 = _tok(0.49, 0.51, 100, 100, 100, 100, 100, 100)
    t1 = _tok(0.49, 0.51, 100, 100, 100, 100, 100, 100)
    r = mr.paper_quote_reward(10.0, 4.5, 20.0, t0, t1)
    assert r["scorable"] and r["reward_low"] <= r["reward_high"] <= 10.0
    assert r["capital"] == pytest.approx(20 * (0.5 - 0.0225) + 20 * (1 - 0.5225))
    # empty competing book (all zeros) -> we take the whole pool at the high bound and the low bound
    z = _tok(0.49, 0.51, 0, 0, 0, 0, 0, 0)
    rz = mr.paper_quote_reward(10.0, 4.5, 20.0, z, z)
    assert rz["reward_high"] == pytest.approx(10.0) and rz["reward_low"] == pytest.approx(10.0)
    assert mr.paper_quote_reward(0.0, 4.5, 20.0, t0, t1) is None
    # spread wider than the max spread -> our quote sits outside v -> not scorable
    wide = _tok(0.40, 0.60, 1, 1, 1, 1, 1, 1)
    assert mr.paper_quote_reward(10.0, 4.5, 20.0, wide, None)["scorable"] is False


def _write_run(root, run, sample_rows, trades, progress):
    rd = root / run
    (rd / "trades").mkdir(parents=True)
    pd.DataFrame(sample_rows).to_csv(rd / "sample.csv.gz", index=False)
    for mid, df in trades.items():
        df.to_csv(rd / "trades" / f"{mid}.csv.gz", index=False)
    with open(rd / "progress.jsonl", "w") as fh:
        for p in progress:
            fh.write(json.dumps(p) + "\n")


def test_runner_pnl_end_to_end(tmp_path):
    import importlib.util
    import sys
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("run_maker_dev", Path(__file__).resolve().parents[2] / "scripts" / "run_maker_dev.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_maker_dev"] = mod
    spec.loader.exec_module(mod)
    rows, trades, prog = [], {}, []
    for i in range(40):
        mid = str(1000 + i)
        rows.append({"market_id": mid, "event_id": str(i // 2), "fee_category": "politics", "status": "closed",
                     "closed": 1, "outcome_prices": '["1", "0"]' if i % 2 else '["0", "1"]', "neg_risk": 0,
                     "start_epoch": 0.0, "end_epoch": 1e6, "close_epoch": 1e6})
        trades[mid] = pd.DataFrame({"ts": [10, 20, 2e6], "side": ["BUY", "SELL", "BUY"], "size": [1.0, 1.0, 5.0],
                                    "price": [0.6, 0.4, 0.9], "outcome_index": [0, 0, 0],
                                    "wallet_hash": ["x"] * 3, "trade_key": ["a", "b", "c"]})
        prog.append({"market_id": mid, "trades_truncated": i == 0})
    rows.append({"market_id": "9", "event_id": "99", "fee_category": "politics", "status": "closed", "closed": 1,
                 "outcome_prices": '["0.5", "0.5"]', "neg_risk": 0, "start_epoch": 0.0, "end_epoch": 1e6, "close_epoch": 1e6})
    _write_run(tmp_path, "h2_main", rows, trades, prog)
    out = tmp_path / "out"
    assert mod.main(["pnl", "--history-root", str(tmp_path), "--runs", "h2_main", "--out", str(out),
                     "--n-boot", "50", "--min-units", "5"]) == 0
    res = json.loads((out / "maker_dev_pnl.json").read_text())
    assert res["exclusions"]["trades_truncated"] == 1
    assert res["exclusions"]["not_resolved_0_1 (50/50 or other)"] == 1
    assert res["exclusions"]["fills_dropped_after_close_or_invalid"] == 39  # the post-close print
    c = res["cells"]["class=politics_binary"]
    assert c["units"] == 20 and c["fills"] == 78
    assert mod.main(["pnl", "--history-root", str(tmp_path), "--runs", "h5_cb1", "--out", str(out)]) == 2
    assert math.isfinite(c["maker_gross_c_pooled"])



def test_calibrated_market_pooled_is_unbiased_but_unit_mean_is_not():
    """Placebo: a calibrated (martingale) price p_t = Phi(W_t / sqrt(T - t)), Y = 1[W_T > 0]. Selecting fills by the
    maker's purchase-price band is predictable, so the pooled ratio is ~0; the per-event mean is biased."""
    from math import erf, sqrt

    rng = np.random.default_rng(9)
    acc = mr.Accumulator()
    n = 100
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    phi = np.vectorize(lambda x: 0.5 * (1.0 + erf(x / sqrt(2.0))))
    for e in range(3000):
        w = rng.normal() + np.concatenate([[0.0], np.cumsum(rng.normal(0, sqrt(1.0 / n), n - 1))])
        p = np.clip(phi(w / np.sqrt(1.0 - t)), 1e-4, 1 - 1e-4)
        y0 = float(w[-1] + rng.normal(0, sqrt(1.0 / n)) > 0)
        k = rng.integers(5, 40)
        i = rng.choice(n, k)
        side = rng.choice(["BUY", "SELL"], k)
        f = mr.per_fill(side, np.zeros(k, int), p[i], np.ones(k), t[i], y0, "tech")
        acc.add_market(f"e:{e}", "single_binary", 2.0, f)
    _, tab = acc.unit_table(pbands=["p0.50-0.70"])
    s = mr.summarise(tab, n_boot=200, seed=3)
    lo, hi = s["maker_gross_c_pooled_fill_ci"]
    assert lo <= 0.0 <= hi
    assert s["maker_gross_c_unit_mean_BIASED_reference"] > 3.0
