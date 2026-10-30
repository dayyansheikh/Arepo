# ruff: noqa: E501
"""CB16 freeze-check amendments (section 11): composition permutation test, market-only calibration placebo, validity failure handling, K pin refusal."""

from __future__ import annotations

import math

import numpy as np

from astrolabe.research_lab import cb16_common as c16
from astrolabe.research_lab import cb16_k as k
from astrolabe.research_lab import cb16_q as q
from astrolabe.research_lab import cb16_u as u
from tests.cb16_synth import synth


def _dataset(**kw):
    fills, table = synth(n_mkt=60, per=40, **kw)
    return q.build_dataset(fills, table)


def test_composition_placebo_holds_under_a_pure_grain_effect_with_fine_strata():
    D = _dataset(beta_g=1.5, wide_by_g=(0.5, 0.5), beta_wide=0.0, seed=21)
    r = q.q1_test(D, n_draws=40)
    cp = r["composition_placebo"]
    assert cp["informative"] and cp["observed"] > 1.0 and cp["holds"] and cp["reached"] <= cp["max_reached"], cp


def test_composition_placebo_fails_under_pure_composition():
    D = _dataset(beta_g=0.0, wide_by_g=(0.2, 0.8), beta_wide=3.0, seed=22)
    elig, _ = q.q_eligible(D)
    idx = np.where(elig & np.isfinite(D["m_2-4h"]))[0]
    g = D["g"].astype(float)
    mk = q.make_fe(D["m_2-4h"], g, D)
    obs = q.est_only(mk, idx)
    cp = q.strata_permutation_test(D, idx, D["m_2-4h"], g, q.q_strata(D), obs, sign=1.0, n_draws=200, seed=c16.PLACEBO_SEEDS["Q1_composition"], note="t")
    assert obs > 0.5 and cp["max_reached"] == 3 and cp["holds"] is False and cp["reached"] > 3, cp


def test_strata_permutation_rule_is_three_of_two_hundred():
    D = _dataset(beta_g=1.5, seed=23)
    idx = np.arange(len(D["g"]))[:50]
    kw = dict(sign=1.0, n_draws=200, seed=1, note="t")
    g = D["g"].astype(float)
    huge = q.strata_permutation_test(D, idx, D["m_2-4h"], g, q.q_strata(D), 1e9, **kw)
    assert huge["max_reached"] == 3 and huge["reached"] == 0 and huge["holds"] is True
    tiny = q.strata_permutation_test(D, idx, D["m_2-4h"], g, q.q_strata(D), -1e9, **kw)
    assert tiny["reached"] == 200 and tiny["holds"] is False
    assert q.strata_permutation_test(D, idx, D["m_2-4h"], g, q.q_strata(D), math.nan, **kw)["holds"] is False


def test_calibration_placebo_shuffles_within_market_and_holds_under_a_real_effect():
    D = _dataset(beta_g=1.5, seed=24)
    r = q.q1_test(D, n_draws=c16.PLACEBO_DRAWS)  # the real 200 draws: at most 3 may pass p < 0.01
    assert r["calibration_placebo"]["holds"] and "within market)" in r["calibration_placebo"]["note"] and "hour" not in r["calibration_placebo"]["note"]
    assert r["testable"] and r["est"] > 1.0


def test_u1_composition_uses_the_permutation_test():
    fills, table = synth(beta_g=0.0, beta_x=-1.5, n_mkt=140, per=14, seed=5)
    D = q.build_dataset(fills, table)
    r = u.u1_test(D, n_draws=20)
    if r.get("testable"):
        assert "reached" in r["composition_placebo"] and r["composition_placebo"]["max_reached"] == 0 and "advance_rate" not in r["composition_placebo"]


class _Lim:
    requests = 0

    def __init__(self, status=200, body=None):
        self.status, self.body = status, body

    def get(self, url, params):
        self.requests += 1
        return self.status, self.body


def test_non_200_read_is_failed_not_exhausted_and_not_in_the_share():
    r = u.all_size_silence(lambda off: None, 1000.0)
    assert r["found"] is False and r["failed"] is True and r["exhausted"] is False
    sample = {"wake": [{"condition_id": "a", "tau": 10000.0}] * 3, "non_wake": [{"condition_id": "b", "tau": 10000.0}] * 2}
    res = u.run_validity(sample, _Lim(status=500, body=[]))
    assert res["wake"]["failed"] == 3 and res["wake"]["silent_ge_1h"] == 0 and res["non_wake"]["failed"] == 2
    assert res["wake_share_silent_ge_1h"] is None and res["non_wake_share_silent_lt_1h"] is None and res["label"] is None


def test_no_earlier_print_is_unresolved_counted_separately_and_never_silent():
    res = u.run_validity({"wake": [{"condition_id": "a", "tau": 10000.0}], "non_wake": [{"condition_id": "b", "tau": 10000.0}]}, _Lim(200, []))
    assert res["wake"]["no_earlier_print"] == 1 and res["wake"]["silent_ge_1h"] == 0 and res["wake"]["failed"] == 0
    assert res["non_wake"]["no_earlier_print"] == 1 and res["wake_share_silent_ge_1h"] is None


def test_failed_units_stay_out_of_the_denominator_of_resolved_units():
    ok_body = [{"timestamp": 1000.0, "price": 0.5, "size": 1, "conditionId": "x"}]

    class Mixed(_Lim):
        def get(self, url, params):
            self.requests += 1
            return (500, []) if params["market"] == "bad" else (200, ok_body)

    sample = {"wake": [{"condition_id": "a", "tau": 10000.0}, {"condition_id": "bad", "tau": 10000.0}], "non_wake": []}
    res = u.run_validity(sample, Mixed())
    assert res["wake"]["failed"] == 1 and res["wake"]["silent_ge_1h"] == 1 and res["wake_share_silent_ge_1h"] == 1.0


def test_k_pin_check_refuses_an_unset_pin(tmp_path, monkeypatch):
    pins = dict(k.CROSS_VENUE_PINS)
    assert pins["matches_all.json"] == "f4cde1e952d85fbe6bca8ac1d42620fcee4bc755468381ccaf5cd639d27ca326" and k.MATCHES_ALL_PIN_META["size_bytes"] == 603444
    tmp_path = tmp_path / "cross_venue"
    tmp_path.mkdir()
    (tmp_path / "matches_all.json").write_text("[]")
    monkeypatch.setattr(k, "CROSS_VENUE_PINS", {"matches_all.json": c16.PIN_UNSET})
    v = k.verify_pins(tmp_path)
    assert v["ok"] is False and v["unset"] == ["matches_all.json"] and v["mismatch"] == ["matches_all.json"]
    monkeypatch.setattr(k, "CROSS_VENUE_PINS", {"matches_all.json": ""})
    assert k.verify_pins(tmp_path)["ok"] is False
