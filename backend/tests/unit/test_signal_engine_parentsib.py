# ruff: noqa: E501
"""Aux family `parentsib` (DESIGN_V1 section 45): parent join, the per-pair clock, the sibling share rule, NaN rules."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.signal_engine import parent_sib as PS

T0 = pd.Timestamp("2026-10-30T10:31:00Z")


def _listing(spec):
    """spec: (market_id, event_id, bid, ask, seconds after T0)."""
    return pd.DataFrame({"market_id": [s[0] for s in spec], "event_id": [s[1] for s in spec], "binary": 1, "closed": "false",
                         "active": "true", "best_bid": [s[2] for s in spec], "best_ask": [s[3] for s in spec],
                         "received_utc": [T0 + pd.Timedelta(seconds=s[4]) for s in spec]})


def _ext(parents: dict):
    """parents: market_id -> (event_id, parent or None); market 99 has no lists (unknown)."""
    rows = {m: {"event_id": e, "event_ids": json.dumps([e]), "parent_event_ids": json.dumps([p])} for m, (e, p) in parents.items()}
    rows[99] = {"event_id": "e9", "event_ids": None, "parent_event_ids": None}
    return pd.DataFrame.from_dict(rows, orient="index")


def test_parentsib_hand_example_clock_share_and_nan():
    # parent P: events A (markets 1, 2), B (3, 4), C (5, received 60 s late); market 6 in event D without a parent
    rows = _listing([(1, "A", 0.49, 0.51, 0), (2, "A", 0.29, 0.31, 0), (3, "B", 0.59, 0.61, 1), (4, "B", 0.19, 0.21, 2),
                     (5, "C", 0.79, 0.81, 60), (6, "D", 0.49, 0.51, 0), (99, "E", 0.49, 0.51, 0)])
    ext = _ext({1: ("A", "P"), 2: ("A", "P"), 3: ("B", "P"), 4: ("B", "P"), 5: ("C", "P"), 6: ("D", None)})
    prev = pd.Series({1: 0.50, 2: 0.30, 3: 0.55, 4: 0.20, 5: 0.70, 6: 0.50, 99: 0.5})  # d2h: 0, 0, +0.05, 0, +0.10
    f = pd.DataFrame({"market_id": np.array([1, 3, 5, 6, 99, 123], np.int64)})
    out = PS.parentsib_features(rows, f, prev, ext)
    hp = out["ps_has_parent"].tolist()
    assert hp[:4] == [1, 1, 1, 0] and math.isnan(hp[4]) and math.isnan(hp[5])  # 99: no lists; 123: no listing row
    r1 = out.iloc[0]  # siblings 3, 4 (B) seen; 5 (C) 60 s late counts as no value: 2 of 3 >= 0.5
    assert r1["ps_log_n_child"] == pytest.approx(math.log(2))
    assert r1["ps_sib_d2h"] == pytest.approx(0.025) and r1["ps_sib_abs"] == pytest.approx(0.025) and r1["ps_sib_moving"] == pytest.approx(0.5)
    r3 = out.iloc[1]  # market 3 at +1 s: siblings 1, 2 (A) seen, 5 late
    assert r3["ps_log_n_child"] == pytest.approx(math.log(2)) and r3["ps_sib_d2h"] == pytest.approx(0.0, abs=1e-6)
    r5 = out.iloc[2]  # market 5 at +60 s: all four siblings seen; three children
    assert r5["ps_log_n_child"] == pytest.approx(math.log(3)) and r5["ps_sib_d2h"] == pytest.approx(0.0125)
    assert out.loc[3, PS.PS_COLUMNS[1:]].isna().all()  # no parent: columns NaN, has_parent 0
    # the share rule: with only one of three siblings seen, the mean is missing, never a partial mean
    rows2 = _listing([(1, "A", 0.49, 0.51, 0), (3, "B", 0.59, 0.61, 0), (4, "B", 0.19, 0.21, 30), (5, "C", 0.79, 0.81, 30)])
    o2 = PS.parentsib_features(rows2, pd.DataFrame({"market_id": np.array([1], np.int64)}), prev, ext)
    assert math.isnan(o2.loc[0, "ps_sib_d2h"]) and o2.loc[0, "ps_has_parent"] == 1
    # no sidecar, or no previous quotes: has_parent still read, moves missing
    assert PS.parentsib_features(rows, f, prev, None).isna().all().all()
    o3 = PS.parentsib_features(rows, f, None, ext)
    assert o3["ps_sib_d2h"].isna().all() and o3.loc[0, "ps_has_parent"] == 1
