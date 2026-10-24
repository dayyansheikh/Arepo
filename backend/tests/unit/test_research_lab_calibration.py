"""Synthetic tests for development study C1 (price calibration). No network."""

from __future__ import annotations

import json
import math

import httpx
import numpy as np

from astrolabe.research_lab import calibration as C


def test_point_in_time_price_never_uses_future_points():
    hist = [{"t": 100, "p": 0.2}, {"t": 200, "p": 0.4}, {"t": 301, "p": 0.99}]
    p, age, why = C.point_in_time_price(hist, 300, max_age=1000)
    assert (p, age, why) == (0.4, 100, "ok")
    p, _, why = C.point_in_time_price(hist, 50)
    assert p is None and why == "empty"
    p, age, why = C.point_in_time_price(hist, 300 + 10 * 3600, max_age=3600)
    assert p is None and why == "stale" and age > 3600
    # a point exactly at the lead time is allowed, the next second is not
    assert C.point_in_time_price([{"t": 300, "p": 0.7}], 300)[0] == 0.7
    assert C.point_in_time_price([{"t": 301, "p": 0.7}], 300)[2] == "empty"


def test_point_in_time_ignores_malformed_points():
    hist = [{"t": "x", "p": 0.5}, {"t": 10}, {"t": 20, "p": 1.5}, {"t": 30, "p": 0.3}]
    assert C.point_in_time_price(hist, 100, max_age=1000)[0] == 0.3


def mk(prices, status="resolved"):
    return {"umaResolutionStatus": status, "outcomePrices": json.dumps(prices)}


def test_parse_outcome_and_exclusions():
    assert C.parse_outcome(mk(["1", "0"])) == (1, "ok")
    assert C.parse_outcome(mk(["0", "1"])) == (0, "ok")
    assert C.parse_outcome(mk(["0.5", "0.5"])) == (None, "split_50_50")
    assert C.parse_outcome(mk(["0.7", "0.3"])) == (None, "other_price_vector")
    assert C.parse_outcome(mk(["1", "0"], status="disputed")) == (None, "not_resolved")
    assert C.parse_outcome({"umaResolutionStatus": "resolved"}) == (None, "bad_prices")
    assert C.parse_outcome(mk(["1", "0", "0"])) == (None, "bad_prices")
    assert C.parse_outcome(mk(["a", "b"])) == (None, "bad_prices")


def test_parse_ts_formats():
    assert C.parse_ts("2026-09-02 03:37:28+00") == C.parse_ts("2026-09-02T03:37:28Z")
    assert C.parse_ts("2026-09-01T00:00:00Z") == 1788220800.0
    assert C.parse_ts(None) is None and C.parse_ts("garbage") is None


def test_anchor_is_earlier_of_end_and_close():
    assert C.anchor_ts(100.0, 200.0) == 100.0
    assert C.anchor_ts(300.0, 200.0) == 200.0
    assert C.anchor_ts(None, 200.0) == 200.0 and C.anchor_ts(None, None) is None


def test_wilson_interval_known_values():
    lo, hi = C.wilson(5, 10)
    assert math.isclose(lo, 0.2366, abs_tol=2e-3) and math.isclose(hi, 0.7634, abs_tol=2e-3)
    lo, hi = C.wilson(0, 20)
    assert lo == 0.0 and 0.1 < hi < 0.2
    assert all(math.isnan(v) for v in C.wilson(0, 0))


def test_reliability_binning_weights_and_edges():
    p = np.array([0.01, 0.01, 0.55, 0.55, 1.0])
    y = np.array([0, 1, 1, 1, 1.0])
    w = np.array([1, 3, 1, 1, 1.0])
    rows = C.reliability(p, y, w)
    first = rows[0]
    assert first["n"] == 2 and math.isclose(first["freq"], 0.75)
    assert math.isclose(first["mean_price"], 0.01)
    assert rows[7]["n"] == 2 and rows[7]["freq"] == 1.0  # [0.5, 0.6)
    assert rows[-1]["n"] == 1  # p == 1.0 lands in the last bin
    assert sum(r["n"] for r in rows) == len(p)
    assert all(r["ci_lo"] <= r["freq"] <= r["ci_hi"] for r in rows if r["n"])


def simulate(slope, intercept, n=40000, seed=1):
    rng = np.random.default_rng(seed)
    p = np.clip(rng.beta(0.6, 0.6, n), 0.005, 0.995)
    true = 1 / (1 + np.exp(-(intercept + slope * C.logit(p))))
    return p, (rng.random(n) < true).astype(float)


def test_calibration_slope_recovered_under_simulated_miscalibration():
    for slope, intercept in ((1.0, 0.0), (0.7, 0.0), (1.4, 0.3)):
        p, y = simulate(slope, intercept)
        a, b = C.fit_logistic(C.logit(p), y, np.ones_like(p))
        assert abs(b - slope) < 0.06 and abs(a - intercept) < 0.06


def test_scores_calibrated_vs_miscalibrated():
    p, y = simulate(1.0, 0.0, seed=2)
    s = C.scores(p, y, np.ones_like(p))
    assert abs(s["brier_excess"]) < 0.004 and abs(s["slope"] - 1) < 0.06
    p2, y2 = simulate(0.5, 0.0, seed=3)
    s2 = C.scores(p2, y2, np.ones_like(p2))
    assert s2["brier_excess"] > 0.01 and s2["brier_recalibrated"] < s2["brier"]
    assert s2["log_loss_excess"] > 0.02


def test_weighted_fit_recovers_population_under_oversampling():
    rng = np.random.default_rng(5)
    n = 60000
    p = rng.uniform(0.02, 0.98, n)
    y = (rng.random(n) < 1 / (1 + np.exp(-(0.8 * C.logit(p))))).astype(float)
    keep_prob = np.where(p > 0.5, 0.2, 1.0)  # oversample low prices
    keep = rng.random(n) < keep_prob
    w = 1.0 / keep_prob[keep]
    _, b = C.fit_logistic(C.logit(p[keep]), y[keep], w)
    assert abs(b - 0.8) < 0.06


def test_cluster_bootstrap_ci_covers_truth_and_is_wider_with_clusters():
    p, y = simulate(0.8, 0.0, n=6000, seed=7)
    w = np.ones_like(p)
    ev = np.arange(len(p)) // 1

    def stat(pp, yy, ww):
        return {"slope": C.scores(pp, yy, ww)["slope"]}

    ci = C.cluster_bootstrap(p, y, w, ev, stat, n_boot=200)["slope"]
    assert ci[0] < 0.8 < ci[1]
    big = np.arange(len(p)) // 300
    ci_big = C.cluster_bootstrap(p, y, w, big, stat, n_boot=200)["slope"]
    assert (ci_big[1] - ci_big[0]) > 0  # computed on 20 clusters
    assert C.cluster_bootstrap(p, y, w, np.zeros(len(p)), stat) == {}


def test_inclusion_weights_horvitz_thompson_and_label_blindness():
    frame = []
    for i in range(1000):
        frame.append({"market_id": str(i), "period": i % 3, "pi_block": 12 / 111,
                      "volume": [150.0, 5e3, 5e4, 5e5][i % 4], "y": i % 2})
    s = C.draw_stage2(frame, per_cell=20)
    assert len(s) == 12 * 20
    # weights sum to the (block-weighted) frame size: HT estimator of the population count
    assert math.isclose(sum(r["weight"] for r in s), len(frame) * 111 / 12, rel_tol=1e-9)
    assert all(math.isclose(r["pi"], r["pi_block"] * r["n_cell"] / r["N_cell"]) for r in s)
    # selection must not depend on any outcome field
    flipped = [{**r, "y": 1 - r["y"]} for r in frame]
    assert [r["market_id"] for r in C.draw_stage2(flipped, per_cell=20)] == [
        r["market_id"] for r in s]
    small = C.draw_stage2(frame[:30], per_cell=500)
    assert len(small) == 30 and all(r["n_cell"] == r["N_cell"] for r in small)


def test_blocks_and_block_draw_are_deterministic_and_stratified():
    blocks = C.make_blocks()
    assert len(blocks) == 332 and blocks[0][0] == C.WINDOW_START.timestamp()
    d1, d2 = C.draw_blocks(len(blocks)), C.draw_blocks(len(blocks))
    assert d1 == d2 and len(d1) == 36
    assert {r["period"] for r in d1} == {0, 1, 2}
    assert all(sum(1 for r in d1 if r["period"] == k) == 12 for k in range(3))


def test_compact_market_and_categories():
    raw = {"id": 7, "conditionId": "0xc", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]',
           "volumeNum": 1234.5, "startDate": "2026-01-01T00:00:00Z",
           "endDate": "2026-09-01T00:00:00Z", "closedTime": "2026-09-02 03:37:28+00",
           "events": [{"id": 99}], "tags": [{"slug": "nfl"}, {"slug": "politics"}]}
    c = C.compact_market(raw)
    assert c["token0"] == "a" and c["event_id"] == "99" and c["category"] == "sports"
    assert C.compact_market({**raw, "outcomes": '["A","B","C"]'}) is None
    assert C.coarse_category(["bitcoin"]) == "crypto" and C.coarse_category([]) == "other"
    assert C.volume_band(99.0) is None and C.volume_band(100.0) == 0
    assert C.volume_band(1e5) == 3


def test_fold_favourite():
    p, y = np.array([0.8, 0.2, 0.5]), np.array([1.0, 1.0, 0.0])
    fp, fy = C.fold_favourite(p, y)
    assert list(fp) == [0.8, 0.8, 0.5] and list(fy) == [1.0, 0.0, 0.0]


def test_fetcher_backs_off_on_403_and_never_raises():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if len(calls) < 3:
            return httpx.Response(403, text="<html>blocked</html>")
        return httpx.Response(200, json={"history": [{"t": 1, "p": 0.5}]})

    slept: list[float] = []
    f = C.PoliteFetcher(httpx.Client(transport=httpx.MockTransport(handler)), delay=0.0,
                        sleep=slept.append)
    data, why = f.get_json("http://x/y", {})
    assert why == "ok" and data["history"][0]["p"] == 0.5 and f.blocked == 2
    assert max(slept) >= 30.0
    capped = C.PoliteFetcher(httpx.Client(transport=httpx.MockTransport(handler)),
                             max_requests=0, sleep=lambda s: None)
    assert capped.get_json("http://x/y", {}) == (None, "request_cap")
