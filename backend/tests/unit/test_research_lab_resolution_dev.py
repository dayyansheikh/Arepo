import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import resolution_dev as R

DAY = 86400


def _market(**kw):
    base = {"market_id": "1", "start_ts": 0.0, "end_ts": 20 * DAY, "closed_ts": 20 * DAY + 3600,
            "category": "sports", "period": 0, "block": 3, "weight": 2.0, "event_id": "e1",
            "neg_risk": True, "neg_risk_id": "0xabc", "neg_risk_aug": False, "parent": None,
            "outcome0": "Yes", "outcome1": "No", "y": 1}
    base.update(kw)
    return base


def test_frame_eligible_requires_listing_30h_before_end():
    assert R.frame_eligible(_market(start_ts=0.0, end_ts=30 * 3600))
    assert not R.frame_eligible(_market(start_ts=1.0, end_ts=30 * 3600))
    assert not R.frame_eligible(_market(start_ts=None))


def test_draw_by_category_is_seeded_and_records_pi():
    frame = [{"market_id": str(i), "period": i % 2, "category": "sports" if i % 3 else "crypto",
              "pi_block": 0.5} for i in range(300)]
    a = R.draw_by_category(frame, per_cell=10)
    b = R.draw_by_category(list(reversed(frame)), per_cell=10)
    assert [r["market_id"] for r in a] == [r["market_id"] for r in b]
    assert len(a) == 40
    r = a[0]
    assert r["pi"] == pytest.approx(0.5 * 10 / r["N_cell"])
    assert r["weight"] == pytest.approx(1 / r["pi"])


def test_horizon_status_uses_scheduled_end_and_observable_closure():
    m = _market(start_ts=15 * DAY, closed_ts=18 * DAY)
    assert R.horizon_status(m, 7 * DAY) == "not_listed"
    assert R.horizon_status(m, 3 * DAY) == "open"
    assert R.horizon_status(m, 1 * DAY) == "closed_before"


def test_price_features_never_use_points_inside_the_lag():
    t = 10 * DAY
    ts = np.array([t - 7200, t - 1200, t - 300], float)
    ps = np.array([0.2, 0.4, 0.9])
    f = R.price_features(ts, ps, t)
    assert f["p"] == 0.4  # the point 300 s before t is not yet known (lag 600 s)
    assert f["chg_1h"] == pytest.approx(0.4 - 0.2)
    assert f["price_age_h"] == pytest.approx(1200 / 3600)
    assert math.isnan(f["chg_24h"])  # nothing 24h earlier


def test_price_features_stale_price_is_missing():
    t = 10 * DAY
    f = R.price_features(np.array([t - 7 * 3600.0]), np.array([0.5]), t)
    assert math.isnan(f["p"])


def test_compact_trades_signs_and_cutoff():
    raw = [{"timestamp": 10, "side": "BUY", "size": 2, "price": 0.3, "outcomeIndex": 0},
           {"timestamp": 11, "side": "BUY", "size": 1, "price": 0.6, "outcomeIndex": 1},
           {"timestamp": 12, "side": "SELL", "size": 1, "price": 0.6, "outcomeIndex": 1},
           {"timestamp": 50, "side": "BUY", "size": 1, "price": 0.5, "outcomeIndex": 0}]
    out = R.compact_trades(raw, cutoff=50)
    assert [r[0] for r in out] == [10, 11, 12]
    assert [r[1] for r in out] == [1, -1, 1]
    assert out[1][3] == pytest.approx(0.4)


def test_flow_features_strictly_before_and_coverage():
    t = 10 * DAY
    tr = np.array([[t - 2 * DAY, 1, 10, 0.5], [t - 3600, 1, 4, 0.5], [t, 1, 100, 0.5]], float)
    f = R.flow_features(tr, None, t, 0.5)
    assert f["tf_n_24h"] == 1  # the trade at exactly t is excluded
    assert f["tf_lnotional_7d"] == pytest.approx(np.log1p(7.0))
    assert f["tf_last_age_h"] == pytest.approx(1.0)
    g = R.flow_features(tr, t - DAY / 2, t, 0.5)  # older trades unreachable
    assert math.isnan(g["tf_n_24h"]) and math.isnan(g["tf_lnotional_cum"])
    assert not R.flow_covered(t - DAY / 2, t)
    assert R.flow_covered(None, t)


def test_market_rows_one_row_per_open_horizon():
    m = _market(start_ts=0.0, end_ts=20 * DAY, closed_ts=19.5 * DAY)
    ts = np.arange(6 * DAY, 19 * DAY + 1, 600.0)
    prices = [[t, 0.6] for t in ts]
    rows, st = R.market_rows(m, prices, {"trades": [], "covered_from": None})
    assert {r["horizon"] for r in rows} == {"1d", "3d", "7d"}
    assert all(r["dep_group"] == "0xabc" for r in rows)
    early = _market(closed_ts=18 * DAY)
    rows, st = R.market_rows(early, prices, None)
    assert {r["horizon"] for r in rows} == {"3d", "7d"}
    assert st["1d:closed_before"] == 1


def _toy(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    end = np.sort(rng.uniform(0, 300 * DAY, n)) + 10 * DAY
    p = rng.uniform(0.05, 0.95, n)
    y = (rng.uniform(size=n) < p).astype(int)
    d = pd.DataFrame({"market_id": [str(i) for i in range(n)], "end_ts": end, "t": end - DAY,
                      "label_ts": end + 3600, "p": p, "y": y, "weight": 1.0,
                      "event": [f"e{i // 2}" for i in range(n)]})
    d["dep_group"] = d["event"]
    d["parent"] = d["event"]
    d[R.BASE_FEATURE] = R.logit(p)
    d["noise"] = rng.normal(size=n)
    return d


def test_walk_forward_embargo_and_order():
    d = _toy()
    folds = R.walk_forward(d)
    assert len(folds) == R.N_CHUNKS - R.FIRST_TEST_CHUNK
    for f in folds:
        first = d["t"].to_numpy()[f.test_pos].min()
        assert (d["label_ts"].to_numpy()[f.train_pos] + R.EMBARGO < first).all()
        assert not set(f.train_pos) & set(f.test_pos)
    fit, val = R.inner_split(d, folds[-1].train_pos)
    assert d["label_ts"].to_numpy()[fit].max() + R.EMBARGO < d["t"].to_numpy()[val].min()


def test_run_arms_and_compare_on_calibrated_toy():
    d = _toy()
    folds = R.walk_forward(d)
    pred, logs = R.run_arms(d, folds, [R.BASE_FEATURE, "noise"], arms=("price", "platt", "enet"))
    assert pred.loc[folds[0].test_pos].notna().all().all()
    assert pred.loc[folds[0].train_pos[:5]].isna().all().all()  # first chunks never scored
    res = R.compare_arms(d, pred, n_boot=100)
    diff = res["diff"]["enet_vs_price"]["log_loss"]["conservative"]
    assert diff["ci"][0] < 0.01  # calibrated prices: no material improvement expected
    assert set(res["arms"]) == {"price", "platt", "enet"}


def test_weighted_cluster_boot_matches_weighted_mean():
    d = np.array([1.0, 2.0, 3.0, 4.0])
    w = np.array([1.0, 1.0, 2.0, 2.0])
    b = R.weighted_cluster_boot(d, w, np.array(["a", "a", "b", "b"]), n_boot=50)
    assert b["mean"] == pytest.approx((1 + 2 + 6 + 8) / 6)
    assert b["n_clusters"] == 2


def test_collector_window():
    at = lambda h, mi: datetime(2026, 10, 11, h, mi, tzinfo=UTC).timestamp()  # noqa: E731
    assert R.in_collector_window(at(20, 25))
    assert R.in_collector_window(at(22, 59))
    assert not R.in_collector_window(at(20, 24))
    assert not R.in_collector_window(at(21, 30))


def test_fetcher_yields_to_live_pass(monkeypatch):
    monkeypatch.setattr(R, "in_collector_window", lambda now=None: False)
    states = iter([True, True, False])
    slept = []

    class Client:
        def get(self, url, params):
            class Resp:
                status_code = 200

                def json(self):
                    return {"ok": 1}
            return Resp()

    f = R.WindowedFetcher(client=Client(), delay=0.0, sleep=slept.append)
    f.live_check = lambda: next(states)
    data, why = f.get_json("u", {})
    assert why == "ok" and slept[:2] == [30.0, 30.0]


def test_live_pass_detection_ignores_watchers():
    assert R.is_live_pass_command("/bin/zsh /Users/x/arepo_collector/arepo_pass.sh")
    assert R.is_live_pass_command("/Users/x/arepo_pass.sh --once")
    assert not R.is_live_pass_command("/bin/zsh -c while pgrep -f arepo_pass.sh; do sleep 20; done")
