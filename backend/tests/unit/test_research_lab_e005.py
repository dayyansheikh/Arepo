"""Synthetic tests for E005 (neg-risk arbitrage-band deviation)."""

from __future__ import annotations

import gzip
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import e004, e005, extract, forecast

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_research_e005

SPEC = {
    "model_id": "t_model", "feature": "chg_1h", "coef": -0.3, "missing": 0,
    "registered_commit": "x", "fitted_on": "synthetic", "_sha256": "abc",
}
REG = datetime(2026, 11, 1, tzinfo=UTC)
FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


@pytest.fixture(autouse=True)
def _no_e002_exclusion(monkeypatch):
    monkeypatch.setattr(e004, "e002_capture_ids", lambda caps: set())


def _rows(ids, bid, ask, gid, start=REG, aug=0, other=0, recv_off=None, chg=0.0, binary=1):
    n = len(ids)
    df = pd.DataFrame({c: [None] * n for c in extract.COLUMNS})
    df["capture_id"], df["capture_start_utc"] = "C", start.strftime(FMT)
    offs = recv_off if recv_off is not None else [5] * n
    df["received_utc"] = [(start + timedelta(seconds=s)).strftime(FMT) for s in offs]
    df["market_id"], df["event_id"] = ids, [f"e{g}" for g in gid]
    df["closed"], df["active"], df["binary"] = "False", "True", binary
    df["best_bid"], df["best_ask"] = bid, ask
    df["spread"] = np.asarray(ask, float) - np.asarray(bid, float)
    df["chg_1h"], df["liquidity"], df["volume24hr"] = chg, 1000.0, 50.0
    df["end_date"] = "2030-01-01T00:00:00Z"
    df["neg_risk"], df["neg_risk_market_id"] = 1, gid
    df["neg_risk_other"], df["event_neg_risk_augmented"] = other, aug
    return df


def test_dev_both_sides_and_inside_band():
    # ask sum of others for m0: 0.30+0.30 -> SB=0.40 ; bid sum others 0.20+0.20 -> SA=0.60
    rows = _rows(["0", "1", "2"], [0.10, 0.20, 0.20], [0.12, 0.30, 0.30], ["g"] * 3)
    m, gt, ex = e005.group_members(rows)
    assert ex["groups_valid"] == 1
    mid0 = 0.11
    assert m.loc["0", "sb"] == pytest.approx(0.40) and m.loc["0", "sa"] == pytest.approx(0.60)
    assert m.loc["0", "dev"] == pytest.approx(0.40 - mid0)  # below SB: positive
    # m1: others ask 0.12+0.30=0.42 -> SB=0.58; others bid .1+.2=.3 -> SA=.70; mid=.25 -> dev .33
    assert m.loc["1", "dev"] == pytest.approx(0.58 - 0.25)
    # inside the band -> 0
    rows2 = _rows(["0", "1"], [0.45, 0.45], [0.55, 0.55], ["h"] * 2)
    m2, gt2, _ = e005.group_members(rows2)  # SB=1-.55=.45, SA=1-.45=.55, mid=.5
    assert (m2["dev"] == 0).all()
    # above SA -> negative: others bid sum 0.9 -> SA=0.1, mid=0.5 -> -(0.4)
    rows3 = _rows(["0", "1"], [0.5, 0.9], [0.52, 0.92], ["k"] * 2)
    m3, _, _ = e005.group_members(rows3)
    assert m3.loc["0", "dev"] == pytest.approx(-(0.51 - (1 - 0.9)))
    assert m3.loc["0", "dev"] < 0


def test_descriptive_arb_flags():
    rows = _rows(["0", "1"], [0.60, 0.50], [0.65, 0.55], ["g"] * 2)
    _, gt, _ = e005.group_members(rows)
    assert bool(gt.loc["g", "arb_bid_gt_1"]) and not bool(gt.loc["g", "arb_ask_lt_1"])
    assert gt.loc["g", "N_g"] == 2 and gt.loc["g", "A_g"] == pytest.approx(1.2)


@pytest.mark.parametrize(
    "kw,reason",
    [
        ({"aug": 1}, "aug"),
        ({"other": 1}, "other"),
        ({"recv_off": [5, 200]}, "span_bad"),
    ],
)
def test_group_exclusions(kw, reason):
    rows = _rows(["0", "1"], [0.4, 0.4], [0.5, 0.5], ["g"] * 2, **kw)
    m, _, ex = e005.group_members(rows)
    assert len(m) == 0 and ex[f"excluded_{reason}"] == 1 and ex["groups_valid"] == 0


def test_exclusion_single_member_and_missing_ask():
    rows = _rows(["0"], [0.4], [0.5], ["g"])
    _, _, ex = e005.group_members(rows)
    assert ex["excluded_few"] == 1 and ex["groups_valid"] == 0
    rows = _rows(["0", "1"], [0.4, 0.4], [0.5, np.nan], ["g"] * 2)
    _, _, ex = e005.group_members(rows)
    assert ex["excluded_noask"] == 1 and ex["groups_valid"] == 0


def test_span_exactly_120s_is_kept():
    rows = _rows(["0", "1"], [0.4, 0.4], [0.5, 0.5], ["g"] * 2, recv_off=[0, 120])
    assert e005.group_members(rows)[2]["groups_valid"] == 1


def test_missing_bid_is_zero_and_ineligible_members_count_in_band():
    # member 2 has no bid (ineligible for E001) but its ask enters the band; bid counted as 0
    rows = _rows(["0", "1", "2"], [0.30, 0.30, np.nan], [0.40, 0.40, 0.90], ["g"] * 3)
    m, _, ex = e005.group_members(rows)
    assert ex["groups_valid"] == 1
    assert m.loc["0", "sb"] == pytest.approx(1 - (0.40 + 0.90))
    assert m.loc["0", "sa"] == pytest.approx(1 - (0.30 + 0.0))
    assert m.loc["2", "dev"] == pytest.approx(
        max(0, (1 - 0.80) - 0.45) - max(0, 0.45 - (1 - 0.60))
    )


def _pair_snaps(dev_sign=1):
    gid = ["g"] * 3 + ["h"] * 2
    ids = [str(i) for i in range(5)]
    bid = [0.10, 0.20, 0.20, 0.46, 0.46]
    ask = [0.12, 0.30, 0.30, 0.54, 0.54]
    si = _rows(ids, bid, ask, gid, chg=[0.1, 0.0, 0.0, 0.0, 0.0])
    sj = _rows(ids, bid, ask, gid, start=REG + timedelta(hours=2))
    return si, sj


def test_origin_only_and_pairs_in_group():
    si, sj = _pair_snaps()
    sj2 = sj.copy()
    sj2["neg_risk_market_id"] = "zzz"  # target-side group info must be ignored
    sj2["event_neg_risk_augmented"] = 1
    starts = [REG.strftime(FMT), (REG + timedelta(hours=2)).strftime(FMT)]
    a, _ = e005.build_pairs([si, sj], starts)
    b, _ = e005.build_pairs([si, sj2], starts)
    pd.testing.assert_frame_equal(a, b)
    assert a["in_group"].all() and len(a) == 5
    assert a.set_index("market_id").loc["0", "dev"] > 0
    assert (a.set_index("market_id").loc[["3", "4"], "dev"] == 0).all()


@pytest.mark.parametrize(
    "npairs,ngroups,slope_lo,expected",
    [
        (199, 50, 0.1, "Unavailable (no verdict)"),
        (500, 29, 0.1, "Unavailable (no verdict)"),
        (200, 30, 0.1, "Supported (exploratory)"),
        (500, 50, -0.1, "Inconclusive"),
    ],
)
def test_verdict_thresholds(npairs, ngroups, slope_lo, expected):
    v = e005.verdict(npairs, ngroups, 0.05, (0.01, 0.1), 8, 0.5, (slope_lo, 0.9))
    assert v == expected


def test_verdict_not_supported_and_period_rule():
    assert e005.verdict(500, 50, -0.01, (-0.1, 0.1), 11, 0.5, (0.1, 0.9)) == "Not supported"
    assert e005.verdict(500, 50, 0.05, (0.01, 0.1), 11, -0.1, (-0.2, 0.0)) == "Not supported"
    assert e005.verdict(500, 50, 0.05, (0.01, 0.1), 7, 0.5, (0.1, 0.9)) == "Inconclusive"
    assert e005.verdict(500, 50, 0.05, (-0.01, 0.1), 11, 0.5, (0.1, 0.9)) == "Inconclusive"


def _series_rows(k, seed=0, true_b=0.5, ngroups=60, start=None):
    """k captures of ngroups groups of 3; mid_j moves toward the band (true_b*dev)."""
    rng = np.random.default_rng(seed)
    n = ngroups * 3
    gid = [f"g{i // 3}" for i in range(n)]
    ids = [str(i) for i in range(n)]
    bid = rng.uniform(0.15, 0.35, n)
    ask = bid + 0.02
    out = []
    start = start or REG + timedelta(hours=1)
    for s in range(k):
        t = start + timedelta(hours=2 * s)
        chg = rng.normal(0, 0.03, n)
        out.append((t, _rows(ids, bid.copy(), ask.copy(), gid, start=t, chg=chg)))
        m, _, _ = e005.group_members(out[-1][1])
        dev = m["dev"].reindex(ids).to_numpy()
        step = -0.3 * chg + true_b * dev + rng.normal(0, 0.001, n)
        mid = np.clip((bid + ask) / 2 + step, 0.1, 0.9)
        bid, ask = mid - 0.01, mid + 0.01
    return out


def _write_snaps(root, series):
    for i, (t, df) in enumerate(series):
        cid = f"S{i:02d}"
        d = root / cid
        d.mkdir(parents=True)
        df = df.assign(capture_id=cid)
        with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
            df.to_csv(fh, index=False)
        (d / "manifest.json").write_text(
            json.dumps({"capture_id": cid, "state": "complete", "started_utc": t.strftime(FMT)})
        )


def _write_dev(dev_dir, series):
    dev_dir.mkdir(parents=True)
    frames, caps = [], []
    for i, (t, df) in enumerate(series):
        cid = f"D{i}"
        frames.append(df.assign(capture_id=cid))
        caps.append({"capture_id": cid, "start_utc": t.strftime(FMT)})
    allrows = pd.concat(frames)
    allrows.to_csv(dev_dir / "snapshots.csv.gz", index=False)
    (dev_dir / "manifest.json").write_text(json.dumps({"captures": caps}))


def test_fit_dev_recovers_b_and_refuses_overwrite(tmp_path):
    _write_dev(tmp_path / "dev", _series_rows(6, seed=1, start=REG - timedelta(days=3)))
    fit = e005.fit_dev(tmp_path / "dev", tmp_path / "out", SPEC)
    assert fit["b"] == pytest.approx(0.5, abs=0.1)
    assert fit["n_pairs"] > 0 and fit["n_groups_dev_nonzero"] > 0
    assert len(fit["per_period"]) == 5 and len(fit["provenance"]["code_sha256"]) == 64
    assert len(fit["drift_baseline"]["coef"]) == 3
    with pytest.raises(FileExistsError):
        e005.fit_dev(tmp_path / "dev", tmp_path / "out", SPEC)


def test_score_requires_fit_status_and_refuses_overwrite(tmp_path, capsys):
    root = tmp_path / "s"
    _write_snaps(root, _series_rows(11, seed=2))
    args = ["--snapshot-root", str(root), "--out-dir", str(tmp_path / "o"),
            "--registration-time", REG.isoformat()]
    assert run_research_e005.main(["score", "--status", *args]) == 0
    assert "11 of 12" in capsys.readouterr().out
    assert run_research_e005.main(["score", *args]) == 0
    assert not (tmp_path / "o").exists()  # <12 -> nothing written
    root2 = tmp_path / "s2"
    _write_snaps(root2, _series_rows(13, seed=3))
    with pytest.raises(FileNotFoundError):
        e005.score(root2, tmp_path / "o2", REG, SPEC)
    _write_dev(tmp_path / "dev", _series_rows(6, seed=4, start=REG - timedelta(days=3)))
    e005.fit_dev(tmp_path / "dev", tmp_path / "o2", SPEC)
    res = e005.score(root2, tmp_path / "o2", REG, SPEC)
    assert res["primary"]["n_periods"] == 11
    assert res["primary"]["verdict"] == "Supported (exploratory)"
    assert res["counts"]["groups_dev_nonzero"] >= 30
    assert "lost_to_target_unavailability" in res["execution"]
    assert res["provenance"]["dev_fit_sha256"]
    with pytest.raises(FileExistsError):
        e005.score(root2, tmp_path / "o2", REG, SPEC)
    assert forecast.sha256_file(tmp_path / "o2" / "results.json")


def test_baseline_frozen_in_fit_and_used(tmp_path):
    _write_dev(tmp_path / "dev", _series_rows(6, seed=5, start=REG - timedelta(days=3)))
    fit = e005.fit_dev(tmp_path / "dev", tmp_path / "out", SPEC)
    bl = fit["baseline"]
    assert bl["coef"] == -0.3 and np.isfinite(bl["a"]) and np.isfinite(bl["s"])
    p = pd.DataFrame({"spread": [0.02, 0.04], "chg_1h": [0.1, -0.1]})
    got = e005.base_hat(p, SPEC, 0.001, 0.5)
    np.testing.assert_allclose(got, [0.001 + 0.01 - 0.03, 0.001 + 0.02 + 0.03])


def test_baseline_fit_recovers_spread_drift():
    rng = np.random.default_rng(0)
    sp = rng.uniform(0.01, 0.09, 2000)
    chg = rng.normal(0, 0.05, 2000)
    d = pd.DataFrame({"spread": sp, "chg_1h": chg})
    d["dmid"] = 0.002 + 0.4 * sp - 0.3 * chg
    a, s = e005.fit_baseline(d, SPEC)
    assert a == pytest.approx(0.002) and s == pytest.approx(0.4)


def test_cluster_fallback_chain_counted():
    av = pd.DataFrame(
        {
            "event_id": ["E", None, "", None],
            "gid": ["G1", "G2", "G3", None],
            "market_id": ["1", "2", "3", "4"],
        }
    )
    key, fb = e005.cluster_keys(av)
    assert list(key) == ["e:E", "g:G2", "g:G3", "m:4"]
    assert fb == {
        "cluster_fallback_to_neg_risk_market_id_rows": 2,
        "cluster_fallback_to_market_id_rows": 1,
    }


def test_max_spread_over_present_spreads():
    rows = _rows(["0", "1", "2"], [0.30, 0.20, np.nan], [0.32, 0.30, 0.50], ["g"] * 3)
    m, _, _ = e005.group_members(rows)
    assert m["max_spread"].iloc[0] == pytest.approx(0.10)


def test_secondaries_include_tight_and_sign_slopes(tmp_path):
    root = tmp_path / "s"
    _write_snaps(root, _series_rows(13, seed=6))
    _write_dev(tmp_path / "dev", _series_rows(6, seed=7, start=REG - timedelta(days=3)))
    e005.fit_dev(tmp_path / "dev", tmp_path / "o", SPEC)
    sec = e005.score(root, tmp_path / "o", REG, SPEC)["secondary"]
    for k in ("tight_groups_max_spread_le_0.03", "dev_positive_only", "dev_negative_only"):
        assert k in sec and "slope" in sec[k]
    assert sec["tight_groups_max_spread_le_0.03"]["n"] > 0
