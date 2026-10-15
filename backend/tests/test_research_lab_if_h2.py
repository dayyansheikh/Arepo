"""Unit tests for the IF-H2 deadline-ladder grouper and causal signal."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from astrolabe.research_lab import if_h2


def _d(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def test_parse_deadline_variants():
    pd_ = if_h2.parse_deadline
    assert _d(pd_("March 2", "X by March 2?", "2026-02-20T00:00:00Z")) == "2026-03-03"
    assert _d(pd_("", "X by Jan 15?", "2025-12-20T00:00:00Z")) == "2026-01-16"
    assert _d(pd_("", "Out before 2027?", "2025-07-01T00:00:00Z")) == "2027-01-01"
    assert _d(pd_("", "Ceasefire in 2025?", "2025-07-01T00:00:00Z")) == "2026-01-01"
    assert if_h2.parse_deadline("", "Who wins the game?", "2025-07-01T00:00:00Z") is None


def _m(i, q, git="", neg=False):
    return {"id": str(i), "question": q, "groupItemTitle": git, "negRisk": neg,
            "clobTokenIds": f'["{i}1", "{i}2"]', "createdAt": "2026-01-01T00:00:00Z",
            "closedTime": "", "closed": False, "outcomePrices": '["0.1","0.9"]'}


def test_group_ladders_deterministic_and_filters():
    ev = {"id": "7", "title": "X by...?", "negRisk": False, "markets": [
        _m(3, "X happens by March 31, 2026?"), _m(1, "X happens by June 30, 2026?"),
        _m(2, "X happens by March 31, 2026?"),  # duplicate deadline -> lowest id kept
        _m(4, "Unrelated Y by April 1, 2026?"),  # different stem, fewer deadlines
        _m(5, "Will X win?"),  # no deadline word
    ]}
    neg = {"id": "8", "negRisk": True, "markets": [_m(9, "A by May 1, 2026?"),
                                                    _m(10, "A by June 1, 2026?")]}
    sports = {"id": "9", "negRisk": False, "markets": [_m(11, "Team A vs Team B"),
                                                       _m(12, "Team A vs Team B: O/U 2.5")]}
    out = if_h2.group_ladders([ev, neg, sports])
    assert len(out) == 1
    rungs = out[0]["rungs"]
    assert [r["market_id"] for r in rungs] == ["2", "1"]
    assert rungs[0]["deadline"] < rungs[1]["deadline"]
    assert out == if_h2.group_ladders([sports, neg, ev])


def test_ifx_term_zero_when_ladder_follows_constant_hazard():
    h = 0.01  # per day
    d1, d2, t = 30 * 86400.0, 90 * 86400.0, 0.0
    tp = t - if_h2.LOOKBACK_S

    def v(d, u):
        return -math.expm1(-h * (d - u) / 86400)

    R = if_h2.ifx_term_R(v(d1, t), v(d2, t), v(d1, tp), v(d2, tp), d1, d2, t)
    assert abs(R) < 1e-9
    # a near-rung jump with an unchanged far rung gives R > 0
    R2 = if_h2.ifx_term_R(v(d1, t) + 0.02, v(d2, t), v(d1, tp), v(d2, tp), d1, d2, t)
    assert R2 > 0.01


def test_asof_respects_lag_and_age():
    ts = np.array([0.0, 3600.0, 7200.0])
    p = np.array([0.1, 0.2, 0.3])
    assert if_h2.asof(ts, p, 7200.0) == 0.2  # point stamped 7200 not usable until 10800
    assert if_h2.asof(ts, p, 10800.0) == 0.3
    assert math.isnan(if_h2.asof(ts, p, 7200.0 + 20 * 3600))


def test_ladder_rows_features_do_not_use_future_prices():
    base = datetime(2026, 1, 1, tzinfo=UTC).timestamp()
    lad = {"ladder_id": "e:x", "event_id": "e", "rungs": [
        {"market_id": "a", "deadline": base + 40 * 86400, "created_at": "2025-12-01T00:00:00Z",
         "closed_time": "", "closed": False, "outcome_prices": ""},
        {"market_id": "b", "deadline": base + 80 * 86400, "created_at": "2025-12-01T00:00:00Z",
         "closed_time": "", "closed": False, "outcome_prices": ""}]}
    ts = np.arange(base - 20 * 86400, base + 20 * 86400, 3600.0)
    pa = np.full(len(ts), 0.10)
    pb = np.full(len(ts), 0.20)
    grid = np.array([base])
    r0 = if_h2.ladder_rows(lad, {"a": (ts, pa), "b": (ts, pb)}, grid)[0]
    pa2 = pa.copy()
    pa2[ts >= base] = 0.5  # change only at/after t
    r1 = if_h2.ladder_rows(lad, {"a": (ts, pa2), "b": (ts, pb)}, grid)[0]
    for k in ("v1", "v2", "R", "chg_1h", "chg_1d", "rv_1d"):
        assert r0[k] == r1[k] or (math.isnan(r0[k]) and math.isnan(r1[k]))
    assert r1["y_24h"] > r0["y_24h"]


def test_add_z_uses_prior_rows_only():
    t = np.arange(20) * if_h2.GRID_S
    df = pd.DataFrame({"ladder_id": "L", "t": t, "R": np.r_[np.tile([0.01, -0.01], 9), 0.05, 9.0]})
    z = if_h2.add_z(df)["z"].to_numpy()
    assert np.isnan(z[: if_h2.Z_MIN_OBS]).all()
    sd = np.std(df["R"].to_numpy()[:18], ddof=1)
    assert abs(z[18] - 0.05 / sd) < 1e-9
