# ruff: noqa: E501
"""CB5-K hour-of-day moderation of the Kalshi lead (astrolabe.research_lab.cb5_hours)."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import cb5_hours as h
from astrolabe.research_lab import cross_venue as cv

ET = ZoneInfo("America/New_York")
T0 = 1_760_000_100 // 600 * 600


def ep(y, mo, d, hh, mm, tz=ET):
    return datetime(y, mo, d, hh, mm, tzinfo=tz).timestamp()


def make_pair(i, *, lead_o=0.5, lead_r=0.5, n=2700, event=None, cat="Politics", seed=None, t0=T0):
    rng = np.random.default_rng(i if seed is None else seed)
    t = t0 + 600.0 * np.arange(n)
    bk = h.buckets_of(t)
    k = np.clip(0.5 + np.cumsum(rng.normal(0, 0.003, n)), 0.1, 0.9)
    dk = np.diff(k, prepend=k[0])
    lead = np.where(bk == 1, lead_o, lead_r)
    dp = np.zeros(n)
    dp[1:] = lead[:-1] * dk[:-1] + rng.normal(0, 0.003, n - 1)
    p = np.clip(0.5 + np.cumsum(dp), 0.1, 0.9)
    return h.KPair(f"p{i}", event or f"e{i // 2}", cat, t, p, k, np.full(n, 0.02), np.ones(n))


def test_dst_transitions_land_in_overnight_bucket():
    for t in (ep(2026, 10, 31, 23, 30), ep(2026, 11, 1, 23, 30), ep(2026, 3, 7, 23, 30), ep(2026, 3, 8, 23, 30)):
        assert h.bucket_of(t) == "O"
    assert h.bucket_of(ep(2026, 11, 2, 9, 30)) == "R" and h.bucket_of(ep(2026, 11, 2, 9, 20)) == "O"
    assert h.bucket_of(ep(2026, 11, 2, 22, 50)) == "R" and h.bucket_of(ep(2026, 11, 2, 23, 0)) == "O"
    utc = datetime(2026, 11, 2, 4, 30, tzinfo=UTC).timestamp()  # 23:30 EST on Nov 1 (after the change)
    assert h.bucket_of(utc) == "O"
    # the same UTC clock time is a different local time on the two sides of a change
    assert h.bucket_of(datetime(2026, 11, 1, 3, 30, tzinfo=UTC).timestamp()) == "O"  # 23:30 EDT Oct 31


def test_asymmetry_matches_the_study_formula_on_a_single_overnight_window():
    start = ep(2026, 11, 2, 23, 0)  # 63 steps, all in O
    pair = make_pair(0, lead_o=0.6, lead_r=0.6, n=63, t0=start)
    assert set(h.buckets_of(pair.t)) == {1}
    tbl = h.step_table([pair])
    S = h._sum_by(tbl, np.zeros(len(tbl.pair), int), 1, np.ones(len(tbl.pair), bool))
    ps = cv.PairSeries("p0", "e0", {"t": pair.t, "p": pair.p, "k": pair.k, "kspr": pair.kspr}, "Politics")
    ll = cv.leadlag([ps], lags=(1, 2), n_boot=10)["lags_min"]
    assert h.asymmetry(S, "O", 1) == pytest.approx(ll[10]["asym"], abs=1e-9)
    assert h.asymmetry(S, "O", 2) == pytest.approx(ll[20]["asym"], abs=1e-9)


def test_k1_detects_planted_moderation_and_is_flat_without_it():
    strong = [make_pair(i, lead_o=0.9, lead_r=0.1, event=f"e{i}") for i in range(30)]
    t = h.step_table(strong)
    res = h.k1_bootstrap(t, n_boot=500)
    assert res["k1"] > 0.1 and res["testable"] and res["p"] < 0.05
    flat = [make_pair(i, lead_o=0.4, lead_r=0.4, event=f"e{i}") for i in range(30)]
    tf = h.step_table(flat)
    assert abs(h.k1(tf)) < 0.1


def test_activity_weights_reproduce_o_cell_shares():
    pairs = [make_pair(i, event=f"e{i}") for i in range(10)]
    t = h.step_table(pairs)
    m = h.primary_mask(t)
    w, info = h.activity_weights(t, m)
    ncell = h.ACT_DECILES * h.ACT_TERCILES
    o = np.bincount(t.cell[m & (t.bucket == 1)], minlength=ncell) / (m & (t.bucket == 1)).sum()
    r_w = np.bincount(t.cell[m & (t.bucket == 0)], weights=w[m & (t.bucket == 0)], minlength=ncell)
    r_w = r_w / r_w.sum()
    keep = o > 0
    assert np.allclose(o[keep & (r_w > 0)] / o[keep & (r_w > 0)].sum(), r_w[keep & (r_w > 0)] / r_w[keep & (r_w > 0)].sum(), atol=1e-9)
    assert (w[t.bucket == 1] == 1.0).all() and info["cells_dropped_empty_in_R"] >= 0
    res = h.activity_matched_k1(t, m)
    assert set(res) >= {"k1", "k1_matched", "ok"}


def test_pseudo_assignment_assigns_whole_blocks_at_the_real_ratio():
    pairs = [make_pair(i, event=f"e{i}") for i in range(8)]
    t = h.step_table(pairs)
    m = h.primary_mask(t)
    sel = np.where(m & (t.bucket == 0))[0]
    codes, nblk = h._codes(t.block[sel])
    q = 0.44
    rng = np.random.default_rng(0)
    ps = h.pseudo_assignment(len(t.pair), sel, codes, nblk, q, rng)
    assert (ps[t.bucket == 1] == -1).all() and set(ps[sel]) <= {0, 1}
    for b in range(nblk):  # every block gets a single label
        assert len(set(ps[sel][codes == b])) == 1
    big = np.concatenate([h.pseudo_assignment(len(t.pair), sel, codes, nblk, q, np.random.default_rng(s))[sel] for s in range(5)])
    assert abs(big.mean() - q) < 0.08


def test_pseudo_split_calibration_on_a_no_moderation_fixture():
    pairs = [make_pair(i, lead_o=0.4, lead_r=0.4, event=f"e{i // 2}", n=2600) for i in range(40)]
    t = h.step_table(pairs)
    res = h.pseudo_split_calibration(t, n_draws=12, n_boot=300)
    assert res["n_tests"] == 24 and res["rate_pooled"] <= 0.25 and 0 < res["o_to_r_ratio"] < 1
    assert set(res) >= {"rate_R", "rate_O", "ok", "max_rate"}


def test_within_pair_uses_equal_pair_weights_and_the_30_step_minimum():
    big = make_pair(0, lead_o=0.9, lead_r=0.1, event="e0")
    small = make_pair(1, lead_o=0.9, lead_r=0.1, event="e1", n=60)  # too short: fewer than 30 steps in at least one bucket
    pairs = [big, small, *[make_pair(i, lead_o=0.9, lead_r=0.1, event=f"e{i}") for i in range(2, 22)]]
    t = h.step_table(pairs)
    res = h.within_pair_k1(t, n_boot=200)
    assert res["n_pairs_below_minimum"] >= 1 and res["n_pairs_eligible"] == len(pairs) - res["n_pairs_below_minimum"]
    kp, elig = h._pair_k1(t, h.primary_mask(t))
    assert res["k1_pair"] == pytest.approx(float(kp[elig & np.isfinite(kp)].mean()))
    assert h.pair_contrast_ok(0.3, 0.2) and not h.pair_contrast_ok(0.3, 0.1) and not h.pair_contrast_ok(0.3, -0.3)


def test_sports_stratum_excluded_from_primary_and_census_counts():
    pairs = [make_pair(0, cat="Politics"), make_pair(1, cat="Sports"), make_pair(2, cat="Politics", event="e1")]
    t = h.step_table(pairs)
    assert not h.primary_mask(t)[t.pair == 1].any() and h.primary_mask(t)[t.pair == 0].all()
    cen = h.k_census(pairs)
    assert cen["n_pairs"] == 3 and cen["primary"]["steps_R"] > 0 and cen["sports"]["steps_R"] > 0
    assert cen["mde"]["mde"] > 0 and "lead" not in str(cen).lower().replace("kalshi_spread", "")


def test_c1_reproduction_assertion():
    pairs = [make_pair(i, event=f"e{i}", n=50) for i in range(4)]
    h.assert_c1_counts(pairs, (4, 4))
    with pytest.raises(AssertionError):
        h.assert_c1_counts(pairs, (316, 183))


def test_cross_venue_live_refused_before_unseal_and_without_signoff(tmp_path):
    live = Path("/x/data-dumps/research_lab/cross_venue_live/poll.csv")
    with pytest.raises(h.RefusedPath):
        h.refuse_path(live, now=datetime(2026, 11, 2, tzinfo=UTC))
    spec, so = tmp_path / "q0114.json", tmp_path / "signoff.json"
    with pytest.raises(h.RefusedPath):  # after the unseal date but without the spec and sign-off
        h.refuse_path(live, now=datetime(2026, 11, 4, tzinfo=UTC), spec=spec, signoff=so)
    spec.write_text("{}")
    so.write_text("{}")
    h.refuse_path(live, now=datetime(2026, 11, 4, tzinfo=UTC), spec=spec, signoff=so)  # both exist: allowed
    h.refuse_path(Path("/x/data-dumps/research_lab/cross_venue/series/a.npz"))  # the historical set is open


def _cap(tmp, name, start, rows):
    d = tmp / name
    d.mkdir()
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False)
    return {"capture_id": name, "dir": str(d), "_start": start}


def test_j4_reads_only_captures_before_t_j4r(tmp_path):
    wide = {"best_bid": [0.30] * 10, "best_ask": [0.60] * 10}
    tight = {"best_bid": [0.49] * 10, "best_ask": [0.51] * 10}
    before_r = datetime(2026, 10, 14, 17, 0, tzinfo=UTC)  # 13:00 ET: R
    before_o = datetime(2026, 10, 14, 5, 0, tzinfo=UTC)  # 01:00 ET: O
    after = datetime(2026, 10, 21, 5, 0, tzinfo=UTC)  # after T_J4R: must never be read
    caps = [_cap(tmp_path, "r", before_r, tight), _cap(tmp_path, "o", before_o, wide), _cap(tmp_path, "late", after, wide)]
    out = h.j4_wide_by_hour(tmp_path, list_captures=lambda root: caps)
    assert out["n_captures"] == 2 and out["rate"]["R"] == 0.0 and out["rate"]["O"] == 1.0
    assert out["label"] == "Polymarket quote state differs by hour (J4 confound possible)"
    assert not math.isnan(out["diff_pp"])


def test_adoption_requires_every_control():
    base = {"testable": True, "p": 0.01, "k1": 0.2, "calibration_ok": True, "matched_ok": True, "pair_ok": True, "robust_ok": True}
    assert h.adoption(base)["adopted"]
    for key in ("calibration_ok", "matched_ok", "pair_ok", "robust_ok"):
        assert not h.adoption({**base, key: None})["adopted"]  # unknown never counts as met
    assert not h.adoption({**base, "k1": 0.05})["adopted"] and not h.adoption({**base, "p": 0.2})["adopted"]
    assert h.k1_mde(0.53, 0.56)["mde"] > 0.15
