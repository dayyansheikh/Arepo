from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import features, features_dev


def _frame():
    return pd.DataFrame(
        {
            "chg_1h": [0.01, -0.05, np.nan, 0.03],
            "spread": [0.02, 0.04, 0.01, 0.0],
            "log_liq": [5.0, 7.0, 3.0, 1.0],
            "log_hours_to_end": [2.0, 4.0, 1.0, 0.5],
            "mid": [0.5, 0.9, 0.1, 0.25],
        }
    )


def test_interactions_computed_on_synthetic_data():
    f = _frame()
    c = np.nan_to_num(f["chg_1h"].to_numpy())
    got = lambda n: features.compute_origin(features.REGISTRY[n], f).to_numpy()  # noqa: E731
    np.testing.assert_allclose(got("rev_x_spread"), c * f["spread"])
    np.testing.assert_allclose(got("rev_x_logliq"), c * f["log_liq"])
    np.testing.assert_allclose(got("rev_x_loghours"), c * f["log_hours_to_end"])
    np.testing.assert_allclose(got("rev_x_midext"), c * np.abs(f["mid"] - 0.5))
    np.testing.assert_allclose(got("rev_large_move"), [0.0, -0.05, 0.0, 0.03])


def test_all_new_features_are_origin_only():
    for name in (
        "rev_x_spread",
        "rev_x_logliq",
        "rev_large_move",
        "rev_x_loghours",
        "rev_x_midext",
        "nr_excess",
        "nr_member",
    ):
        spec = features.REGISTRY[name]
        assert not set(spec.requires) & features.LABEL_COLUMNS
        assert spec.version == features_dev.VERSION


def test_registration_refuses_label_columns():
    bad = features.FeatureSpec("leaky_dev", "interaction", "x", lambda o: o["dmid"], ("dmid",))
    with pytest.raises(ValueError, match="label-side"):
        features.register(bad)


def test_feature_ignores_undeclared_label_columns():
    f = _frame()
    f["dmid"], f["mid_j"] = 99.0, 99.0  # target columns present in the frame must not be read
    a = features.compute_origin(features.REGISTRY["rev_x_midext"], f)
    b = features.compute_origin(
        features.REGISTRY["rev_x_midext"], f.drop(columns=["dmid", "mid_j"])
    )
    pd.testing.assert_series_equal(a, b)


def test_variants_resolve_to_registered_features():
    assert len(features_dev.VARIANTS) == 6
    for feats in features_dev.VARIANTS.values():
        assert all(n in features.REGISTRY for n in feats)


def test_negrisk_columns_from_origin_rows_only():
    def row(mid_, bid, ask, g, nr=1):
        return {
            "market_id": mid_,
            "event_id": "e",
            "neg_risk": nr,
            "neg_risk_market_id": g,
            "best_bid": bid,
            "best_ask": ask,
            "event_neg_risk_augmented": 0,
            "neg_risk_other": 0,
            "received_utc": "2026-10-03T04:00:00Z",
        }

    origin = pd.DataFrame(
        [row("a", 0.38, 0.42, "g"), row("b", 0.58, 0.62, "g"), row("c", 0.3, 0.4, None, nr=0)]
    )
    pairs = pd.DataFrame({"market_id": ["a", "b", "c", "z"], "period": [0, 0, 0, 0]})
    out = features_dev.add_negrisk_columns(pairs, {0: origin})
    # S_g = mid(a) + mid(b) = 0.40 + 0.60 = 1.00 -> excess 0; non-members 0 with member=0
    np.testing.assert_allclose(out["nr_excess"], [0.0, 0.0, 0.0, 0.0], atol=1e-12)
    np.testing.assert_array_equal(out["nr_member"], [1, 1, 0, 0])
    origin.loc[0, ["best_bid", "best_ask"]] = [0.48, 0.52]  # S_g = 1.10
    out = features_dev.add_negrisk_columns(pairs, {0: origin})
    np.testing.assert_allclose(out["nr_excess"], [0.10, 0.10, 0.0, 0.0], atol=1e-12)
