# ruff: noqa: E501
"""CB4 measurement helpers (cb4_measure): determinism, ingress cap, band classification, H rule, family-M adoption and register guards."""
from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from astrolabe.research_lab import cb4_declaration as D
from astrolabe.research_lab import cb4_measure as M
from astrolabe.research_lab import cost_regimes


def test_sample_hours_and_order_are_seeded_and_alternate():
    days = M.analysis_days()
    assert days and all(w in ("pre", "post") for _, w in days)
    a = M.sample_hours("s", days, 1.0)
    assert a == M.sample_hours("s", days, 1.0) and a != M.sample_hours("t", days, 1.0)
    assert len(a) == len(days)
    o = M.hour_order("s", a)
    assert sorted(h["hour"] for h in o) == sorted(h["hour"] for h in a)
    assert o[0]["window"] != o[1]["window"]


def test_excluded_days_are_not_sampled():
    # 2026-05-28 and 05-29 are outside both declared windows
    for d in (datetime(2026, 5, 28, tzinfo=UTC), datetime(2026, 5, 29, tzinfo=UTC), datetime(2026, 7, 2, tzinfo=UTC)):
        assert M.window_of(d) is None


def test_ingress_meter_stops_at_cap():
    m = M.IngressMeter(100)
    m.add(60)
    assert not m.exceeded
    m.add(40)
    assert m.exceeded


def test_classify_bands_and_vwap():
    assert M.classify(0.10, 0.02, rho=0.5, mu=0.005) == "hi"
    assert M.classify(0.02, 0.03, rho=0.5, mu=0.005) == "mid"
    assert M.classify(0.01, 0.03, rho=0.5, mu=0.005) == "lo"
    assert M.classify(0.001, 0.03, rho=0.5, mu=0.005) == "none"
    assert M.vwap_ask([(0.5, 10.0), (0.6, 10.0)], shares=20) == pytest.approx(0.55)
    assert math.isnan(M.vwap_ask([(0.5, 5.0)], shares=20))


def test_pilot_power_h_rule_and_untestable():
    ok = M.pilot_power(1e9, 0.3, 5.0, 1.5)
    assert ok["testable"] and ok["H"] in D.N["H_grid"] and ok["H"] == min(ok["H_mde"], ok["H_cap"])
    heavy = M.pilot_power(1e12, 0.3, 5.0, 1.5)  # no H fits under the 150 GB cap
    assert not heavy["testable"] and heavy["H"] == 0


def test_period_of_boundaries():
    assert M.period_of(D.epoch("2000-01-01T00:00Z")) is None


def _res(p, est, **kw):
    return {"estimate": est, "p": p, "ci95": [est - 0.01, est + 0.01], "placebo_p": 0.5, "top5_ok": True, "cluster_equal_sign": {"event": True, "day": True}, "pseudo_band_ok": True, "sign_agree": True, **kw}


def test_adoption_requires_holm_floor_placebo_and_robustness():
    big = {t: D.FLOORS[t] * 3 for t in D.TESTS["M"]}
    allok = {t: _res(1e-6, big[t]) for t in D.TESTS["M"]}
    assert all(v["adopted"] for v in M.adoption(allok).values())
    below = {**allok, "N1": _res(1e-6, D.FLOORS["N1"] / 10)}
    assert not M.adoption(below)["N1"]["adopted"]  # floor not met
    plc = {**allok, "E1": _res(1e-6, big["E1"], placebo_p=0.01)}
    assert not M.adoption(plc)["E1"]["adopted"]  # placebo rejects
    rob = {**allok, "N2": _res(1e-6, big["N2"], pseudo_band_ok=False)}
    assert not M.adoption(rob)["N2"]["adopted"]
    unp = {**allok, "E2": _res(0.2, big["E2"])}
    assert not M.adoption(unp)["E2"]["adopted"]  # Holm does not reject


def test_commit_register_refuses_incomplete_and_never_overwrites(tmp_path):
    partial = {"N1": _res(0.5, 0.0), "N2": _res(0.5, 0.0)}
    with pytest.raises(cost_regimes.CostRegimeError):
        M.commit_register(partial, None, tmp_path / "reg.json")
    assert not (tmp_path / "reg.json").exists()
    full = {t: _res(0.5, 0.0) for t in D.TESTS["M"]}
    M.commit_register(full, None, tmp_path / "reg.json")
    with pytest.raises(Exception):  # noqa: B017 - any refusal to overwrite
        M.commit_register(full, None, tmp_path / "reg.json")


def test_design_effect_from_event_clustering():
    import numpy as np

    rng = np.random.default_rng(0)
    ev = np.repeat(np.arange(40), 10)
    iid = rng.normal(size=400)
    clustered = np.repeat(rng.normal(size=40), 10) + 0.1 * rng.normal(size=400)
    assert M.design_effect_from_clusters(iid, ev) < 1.6
    assert M.design_effect_from_clusters(clustered, ev) > 8.0  # ICC near 1 -> deff near the cluster size 10
    assert math.isnan(M.design_effect_from_clusters([1.0, 2.0], [1, 2]))
    # the pilot power uses the estimate, with the declared floor 1.5
    low = M.pilot_power(1e8, 0.1, 10.0, 1.0)["mde_by_H"]["168"]
    hi = M.pilot_power(1e8, 0.1, 10.0, 6.0)["mde_by_H"]["168"]
    assert hi > low


def test_ols_contrast_robust_reports_top5_and_cluster_equal_sign_per_way():
    import numpy as np

    rng = np.random.default_rng(1)
    n_ev = 60
    ev = np.repeat(np.arange(n_ev), 20)
    day = np.tile(np.arange(20), n_ev)
    post = (day >= 10).astype(float)
    y = 0.5 * post + rng.normal(size=len(ev))
    X = np.column_stack([np.ones(len(ev)), post])
    r = M.ols_contrast(y, X, [0.0, 1.0], {"event": ev, "day": day}, min_units=100, min_clusters=20, robust=True)
    assert r["testable"] and set(r["top5_dropped"]) == {"event", "day"} and set(r["cluster_equal_sign"]) == {"event", "day"}
    assert all(r["cluster_equal_sign"].values()) and r["top5_dropped"]["event"]["testable"]
    # one dominant cluster drives the effect: dropping the top 5 event clusters kills it
    y2 = rng.normal(size=len(ev)) + np.where(ev < 3, 40.0 * post, 0.0)
    r2 = M.ols_contrast(y2, X, [0.0, 1.0], {"event": ev, "day": day}, min_units=100, min_clusters=20, robust=True)
    assert r2["top5_dropped"]["event"]["p"] > 0.05
    res = {t: _res(1e-6, D.FLOORS[t] * 3) for t in D.TESTS["M"]}
    res["N1"] = {**res["N1"], "top5_dropped": {"event": {"testable": True, "p": 0.4, "estimate": D.FLOORS["N1"] * 3}, "day": {"testable": True, "p": 1e-6, "estimate": D.FLOORS["N1"] * 3}}}
    assert not M.adoption(res)["N1"]["adopted"] and M.adoption(res)["N2"]["adopted"]
    res["E1"] = {k: v for k, v in res["E1"].items() if k != "cluster_equal_sign"}
    assert not M.adoption(res)["E1"]["adopted"]  # a missing cluster-equal check blocks


def test_era_panel_d6h_is_in_cents():
    import numpy as np
    import pandas as pd

    end = D.epoch("2026-03-10T00:00Z")
    ts = np.arange(end - 10 * 86400, end + 2 * 86400, 600.0)
    vals = np.full(len(ts), 0.50)
    vals[ts >= end - 60 * 3600] = 0.52
    tr = pd.DataFrame({"ts": [end - 71.5 * 3600.0], "price": [0.5], "size": [10.0], "side": ["BUY"], "outcome_index": [0]})
    rec = {"market_id": "m1", "event_id": "e1", "end_epoch": end, "group": "O", "period": "P1", "fee_category": "x"}
    p = M.era_panel(rec, ts, vals, tr, False, None)
    assert len(p) and p["d6h"].abs().max() > 1.0 and p["d6h"].abs().max() <= 2.5  # 0.02 -> 2 cents, not 0.02
