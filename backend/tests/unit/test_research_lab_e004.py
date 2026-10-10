"""Synthetic tests for the E004 multi-period test and execution check."""

from __future__ import annotations

import gzip
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import e004, extract

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_research_e004

SPEC = {
    "model_id": "t_model", "feature": "chg_1h", "coef": -0.33161, "missing": 0,
    "registered_commit": "x", "fitted_on": "synthetic", "_sha256": "abc",
}
REG = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_e002_exclusion(monkeypatch, request):
    """Synthetic captures post-date E002's registration; only the dedicated test applies it."""
    if "e002_exclusion" not in request.node.name:
        monkeypatch.setattr(e004, "e002_capture_ids", lambda caps: set())
FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _rows(cap_id, start, bid, ask, chg, events=None):
    n = len(bid)
    df = pd.DataFrame({c: [None] * n for c in extract.COLUMNS})
    df["capture_id"] = cap_id
    df["capture_start_utc"] = start.strftime(FMT)
    df["received_utc"] = (start + timedelta(seconds=5)).strftime(FMT)
    df["market_id"] = [str(i) for i in range(n)]
    df["condition_id"] = [f"c{i}" for i in range(n)]
    df["event_id"] = [str(i // 2) for i in range(n)] if events is None else events
    df["closed"] = "False"
    df["active"] = "True"
    df["binary"] = 1
    df["best_bid"] = bid
    df["best_ask"] = ask
    df["spread"] = np.asarray(ask) - np.asarray(bid)
    df["chg_1h"] = chg
    df["liquidity"] = 1000.0
    df["volume24hr"] = 50.0
    df["end_date"] = "2030-01-01T00:00:00Z"
    df["dup_count"] = 0
    return df


def _write(root, cap_id, start, df, state="complete"):
    d = root / cap_id
    d.mkdir(parents=True)
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        df.to_csv(fh, index=False)
    man = {"capture_id": cap_id, "state": state, "started_utc": start.strftime(FMT)}
    (d / "manifest.json").write_text(json.dumps(man))
    return d


def _series(root, k, start=REG + timedelta(hours=1), slope=-0.33161, seed=0):
    """k complete snapshots, 2h apart, with mid_j = mid + slope_true * chg_i + small noise."""
    rng = np.random.default_rng(seed)
    n = 400
    mid = rng.uniform(0.3, 0.7, n)
    for s in range(k):
        t = start + timedelta(hours=2 * s)
        chg = rng.normal(0, 0.05, n)
        _write(root, f"S{s:02d}", t, _rows(f"S{s:02d}", t, mid - 0.005, mid + 0.005, chg))
        mid = np.clip(mid + slope * chg + rng.normal(0, 0.002, n), 0.1, 0.9)


def _caps(tmp_path, k, **kw):
    _series(tmp_path / "s", k, **kw)
    from astrolabe.research_lab import forecast
    return forecast.list_complete_captures(tmp_path / "s")


def test_qualification_rule(tmp_path):
    root = tmp_path / "s"
    old = REG - timedelta(hours=5)
    for i in range(3):
        t = old + timedelta(hours=i)
        _write(root, f"old{i}", t, _rows(f"old{i}", t, np.array([0.4]), np.array([0.5]), 0.0))
    t = REG + timedelta(hours=1)
    _write(root, "inc", t, _rows("inc", t, np.array([0.4]), np.array([0.5]), 0.0), "incomplete")
    for i in range(14):
        t = REG + timedelta(hours=2 + i)
        _write(root, f"n{i:02d}", t, _rows(f"n{i:02d}", t, np.array([0.4]), np.array([0.5]), 0.0))
    st = e004.status(root, REG)
    assert st["qualifying"] == 12 and st["ready"]
    assert st["capture_ids"] == [f"n{i:02d}" for i in range(12)]
    assert e004.status(tmp_path / "empty", REG)["qualifying"] == 0


@pytest.mark.parametrize(
    "r2,lo,npos,slope,shi,expected",
    [
        (0.1, 0.05, 8, -0.3, -0.1, "Supported (exploratory, prospective)"),
        (0.1, 0.05, 7, -0.3, -0.1, "Inconclusive"),
        (0.1, -0.01, 11, -0.3, -0.1, "Inconclusive"),
        (0.1, 0.05, 11, -0.3, 0.02, "Inconclusive"),
        (0.0, -0.1, 11, -0.3, -0.1, "Not supported"),
        (-0.1, -0.2, 11, -0.3, -0.1, "Not supported"),
        (0.1, 0.05, 11, 0.1, 0.2, "Not supported"),
    ],
)
def test_verdict_rules(r2, lo, npos, slope, shi, expected):
    assert e004.verdict(r2, (lo, r2 + 0.1), npos, slope, (slope - 0.1, shi)) == expected


def test_execution_pnl_hand_computed():
    # up: buy ask_i 0.52, sell bid_j 0.58 -> +0.06; mid_j 0.60 -> +0.08
    # down: sell bid_i 0.48, buy back ask_j 0.46 -> +0.02; mid_j 0.45 -> +0.03
    # |dmid_hat|=0.01 <= spread/2=0.02 -> not selected
    t = e004.trade_pnl(
        np.array([0.05, -0.05, 0.01]),
        np.array([0.48, 0.48, 0.48]),
        np.array([0.52, 0.52, 0.52]),
        np.array([0.58, 0.44, 0.50]),
        np.array([0.62, 0.46, 0.54]),
        np.array([0.04, 0.04, 0.04]),
    )
    assert list(t["selected"]) == [True, True, False]
    np.testing.assert_allclose(t["pnl_touch"][:2], [0.06, 0.02])
    np.testing.assert_allclose(t["pnl_mid"][:2], [0.08, 0.03])


def test_clustered_mean_ci_constant():
    lo, hi = e004.clustered_mean_ci(np.array(["a", "a", "b", "c"]), np.array([0.1] * 4))
    assert lo == pytest.approx(0.1) and hi == pytest.approx(0.1)


def test_event_cluster_fallback_counting():
    df = pd.DataFrame(
        {"market_id": ["1", "2", "3", "4"], "event_id": ["E", None, "E", float("nan")]}
    )
    key, n_fb = e004.event_clusters(df)
    assert n_fb == 2
    assert list(key) == ["e:E", "m:2", "e:E", "m:4"]


def test_end_to_end_supported_and_refuse_overwrite(tmp_path):
    _series(tmp_path / "s", 13)
    out = tmp_path / "out"
    res = e004.score(tmp_path / "s", out, REG, SPEC)
    assert res is not None
    assert res["primary"]["n_periods"] == 11
    assert res["primary"]["verdict"] == "Supported (exploratory, prospective)"
    prov = res["provenance"]
    assert len(prov["snapshots"]) == 12 and prov["snapshots"][0]["capture_id"] == "S00"
    assert prov["spec_sha256"] == "abc" and len(prov["code_sha256"]) == 64
    assert (out / "results.json").exists()
    assert res["counts"]["pairs_target_unavailable_excluded"] >= 0
    with pytest.raises(FileExistsError):
        e004.score(tmp_path / "s", out, REG, SPEC)


def test_not_ready_returns_none_and_writes_nothing(tmp_path):
    _series(tmp_path / "s", 11)
    out = tmp_path / "out"
    assert e004.score(tmp_path / "s", out, REG, SPEC) is None
    assert not out.exists()


def test_cli_status_and_not_ready(tmp_path, capsys):
    _series(tmp_path / "s", 5)
    args = ["--snapshot-root", str(tmp_path / "s"), "--out-dir", str(tmp_path / "o"),
            "--registration-time", REG.isoformat()]
    assert run_research_e004.main(["score", "--status", *args]) == 0
    assert "5 of 12" in capsys.readouterr().out
    assert run_research_e004.main(["score", *args]) == 0
    assert "5 of 12" in capsys.readouterr().out
    assert not (tmp_path / "o").exists()


def test_e002_exclusion_removes_e002_pair():
    base = datetime(2026, 10, 10, 19, 22, tzinfo=UTC)
    caps = [
        {"capture_id": "e002_first", "state": "complete", "_start": base},
        {"capture_id": "mid", "state": "complete", "_start": base + timedelta(hours=1)},
        {"capture_id": "e002_second", "state": "complete", "_start": base + timedelta(hours=3.2)},
        {"capture_id": "loop1", "state": "complete", "_start": base + timedelta(hours=3.5)},
    ]
    excluded = e004.e002_capture_ids(caps)
    assert excluded == {"e002_first", "e002_second"}
    reg = base + timedelta(minutes=30)
    got = [c["capture_id"] for c in e004.qualifying_captures(caps, reg, n=12)]
    assert got == ["mid", "loop1"]
