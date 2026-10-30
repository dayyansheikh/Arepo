"""Unit tests for the E010 writer on the live cross-venue stream (no network)."""

from __future__ import annotations

import pytest

from astrolabe.research_lab import cross_venue_live as cvl
from astrolabe.research_lab import cross_venue_live_e010 as e010


def _spec():
    m = {
        "m0": {"intercept": 0.0, "r1": 0.0, "r6": 0.0, "lvl": 0.0, "lvl2": 0.0},
        "mgap": {"intercept": 0.0, "r1": 0.0, "r6": 0.0, "lvl": 0.0, "lvl2": 0.0, "gap": 0.5},
        "m1": {
            "intercept": 0.0,
            "r1": 0.0,
            "r6": 0.0,
            "lvl": 0.0,
            "lvl2": 0.0,
            "gap": 0.5,
            "dk1": 0.5,
            "dk6": 0.0,
        },
    }
    return {"models": {"60": m, "360": m}, "_sha256": "y" * 64}


def test_spec_hash_pinned_and_c1():
    s = e010.load_spec()
    assert s["_sha256"] == e010.SPEC_SHA256
    assert s["provenance"]["n_pairs"] == 316 and len(s["provenance"]["dropped_tickers"]) == 25
    assert set(s["models"]) == {"60", "360"}
    with pytest.raises(RuntimeError):
        e010.load_spec(sha="0" * 64)


def test_holm():
    assert e010.holm({"a": 0.01, "b": 0.04}) == {"a": 0.02, "b": 0.04}


def _q(t, pid, pm, pb=None, pa=None):
    pb = pm - 0.005 if pb is None else pb
    pa = pm + 0.005 if pa is None else pa
    return {
        "t": t,
        "pid": pid,
        "p_mid": pm,
        "p_bid": pb,
        "p_ask": pa,
        "p_recv": t + 2,
        "k_recv": t + 1,
        "k_mid": pm + 0.02,
    }


def test_writer_hourly_predictions_then_outcomes_then_analyze(tmp_path):
    w = e010.E010Writer(tmp_path, spec=_spec())
    t0 = 1_800_000_000 - 1_800_000_000 % 3600
    feats = {"r1": 0, "r6": 0, "lvl": 0, "lvl2": 0, "gap": 0.02, "dk1": 0.01, "dk6": 0}
    for i in range(0, 8 * 30 + 1):  # 8 hours of 2-min cycles
        t = t0 + i * 120
        quotes, ready = [], []
        for ev in range(3):
            pid = f"p{ev}"
            pm = 0.40 + (0.015 if t >= t0 + 1800 else 0.0)
            q = _q(t, pid, pm)
            quotes.append(q)
            pair = {"pid": pid, "p_event_id": f"E{ev}", "fee_rate": 0.0}
            ready.append((pair, {**q, "kr": q["k_recv"]}, feats))
        w.on_cycle(t, ready, quotes)
    preds = list(cvl.read_jsonl(tmp_path / e010.PRED_FILE))
    outs = list(cvl.read_jsonl(tmp_path / e010.OUT_FILE))
    assert {r["t"] % 3600 for r in preds} == {0}
    assert len(preds) == 9 * 3
    first = [o for o in outs if o["t0"] == t0]
    assert {o["h"] for o in first} == {60, 360}
    o60 = next(o for o in first if o["h"] == 60)
    assert o60["dp"] == pytest.approx(0.015) and o60["t_obs"] == t0 + 3600
    assert preds[0]["y1"]["60"] == pytest.approx(0.015)
    res = e010.analyze(
        tmp_path,
        start_utc=cvl.utc_iso(t0),
        end_utc=cvl.utc_iso(t0 + 1),  # only the origin before the move
        role=preds[0]["role"],
        n_boot=100,
        now=2e9,
    )
    h = res["horizons"]["60"]
    assert h["n_clusters"] == 3 and h["rel_mse_gain_m1"] > 0.5
    assert set(res["holm_m1"]) == {"60", "360"}


def test_writer_failure_does_not_stop_e009(tmp_path):
    class Boom:
        def on_cycle(self, *a):
            raise ValueError

    from tests.test_research_lab_cross_venue_live import FakeLim, _pair, _write_pairs
    from tests.test_research_lab_cross_venue_live import _spec as spec9

    lim = FakeLim({})
    p = cvl.Poller(lim, lim, root=tmp_path, spec=spec9(), clock=lambda: 1.0)
    p.extras.append(Boom())
    _write_pairs(tmp_path, [_pair(1)])
    assert p.cycle(1200)["pairs"] == 1


def test_registration_constant_and_holm_keeps_both_primaries(tmp_path):
    assert e010.REGISTERED_UTC == "2026-10-13T02:00:00Z"
    res = e010.analyze(tmp_path, start_utc="2026-10-13T02:00:00Z", now=2e9)
    assert res["holm_m1"] == {"60": 1.0, "360": 1.0}
