"""Synthetic tests for the E002 forecast/score module."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import evaluate, extract, forecast

SPEC = {
    "model_id": "t_model", "feature": "chg_1h", "coef": -0.33161, "missing": 0,
    "registered_commit": "x", "fitted_on": "synthetic", "_sha256": "abc",
}


def _rows(cap_id, start, mid, chg, bid_ask_half=0.005, end_date="2030-01-01T00:00:00Z"):
    n = len(mid)
    rec = (start + timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    df = pd.DataFrame({c: [None] * n for c in extract.COLUMNS})
    df["capture_id"] = cap_id
    df["capture_start_utc"] = start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    df["received_utc"] = rec
    df["market_id"] = [str(i) for i in range(n)]
    df["condition_id"] = [f"c{i}" for i in range(n)]
    df["event_id"] = [str(i // 2) for i in range(n)]
    df["closed"] = "False"
    df["active"] = "True"
    df["binary"] = 1
    df["best_bid"] = mid - bid_ask_half
    df["best_ask"] = mid + bid_ask_half
    df["spread"] = 2 * bid_ask_half
    df["chg_1h"] = chg
    df["liquidity"] = np.linspace(100, 10000, n)
    df["volume24hr"] = 50.0
    df["end_date"] = end_date
    df["dup_count"] = 0
    df["page_index"] = 0
    return df


def _write(root: Path, cap_id: str, start: datetime, df: pd.DataFrame, state="complete"):
    d = root / cap_id
    d.mkdir(parents=True)
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        df.to_csv(fh, index=False)
    man = {"capture_id": cap_id, "state": state,
           "started_utc": start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    (d / "manifest.json").write_text(json.dumps(man))
    return d


def _pair(tmp_path, slope, noise=0.01, n=3000, seed=1):
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    mid = rng.uniform(0.2, 0.8, n)
    chg = rng.normal(0, 0.03, n)
    mid_j = np.clip(mid + slope * chg + rng.normal(0, noise, n), 0.05, 0.95)
    a = _write(tmp_path / "s", "A", t0, _rows("A", t0, mid, chg))
    t1 = t0 + timedelta(hours=6)
    b = _write(tmp_path / "s", "B", t1, _rows("B", t1, mid_j, np.zeros(n)))
    return a, b


def test_prediction_uses_only_origin_row():
    rng = np.random.default_rng(0)
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    mid, chg = rng.uniform(0.2, 0.8, 50), rng.normal(0, 0.05, 50)
    base = forecast.predict_frame(_rows("A", t0, mid, chg), SPEC)
    # changing every other (later-capture style) field must not matter; changing chg must
    altered = _rows("A", t0, mid, chg)
    altered["page_index"] = 7
    altered["updated_at"] = "2099-01-01T00:00:00Z"
    assert np.array_equal(base["dmid_hat"], forecast.predict_frame(altered, SPEC)["dmid_hat"])
    np.testing.assert_allclose(base["dmid_hat"], -0.33161 * chg)
    chg2 = chg.copy()
    chg2[0] += 1
    new = forecast.predict_frame(_rows("A", t0, mid, chg2), SPEC)
    assert new["dmid_hat"].iloc[0] != base["dmid_hat"].iloc[0]


def test_forecast_eligibility_rules():
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    df = _rows("A", t0, np.full(4, 0.5), np.array([0.01, np.nan, 0.02, 0.03]))
    df.loc[2, "end_date"] = (t0 + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    df.loc[3, "end_date"] = None
    out = forecast.predict_frame(df, SPEC)
    assert list(out["market_id"]) == ["0", "1", "3"]
    assert out.loc[out["market_id"] == "1", "dmid_hat"].iloc[0] == 0.0


def test_append_only_refusal(tmp_path):
    a, _ = _pair(tmp_path, -0.3)
    froot = tmp_path / "f"
    forecast.predict(a, SPEC, froot)
    with pytest.raises(FileExistsError):
        forecast.predict(a, SPEC, froot)


def test_predict_refuses_incomplete(tmp_path):
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    d = _write(tmp_path / "s", "X", t0, _rows("X", t0, np.full(3, 0.5), np.zeros(3)), "incomplete")
    with pytest.raises(ValueError):
        forecast.predict(d, SPEC, tmp_path / "f")


def test_score_equals_logged_forecast_and_detects_tamper(tmp_path):
    a, b = _pair(tmp_path, -0.3)
    froot = tmp_path / "f"
    forecast.predict(a, SPEC, froot)
    res = forecast.score(a, b, SPEC, froot)
    chk = res["logged_forecast_check"]
    assert chk["logged"] and chk["n_compared"] == res["counts"]["eligible"]
    assert chk["n_scored_without_logged_forecast"] == 0
    csv_path, man_path = forecast.forecast_paths(a, SPEC, froot)
    tampered = pd.read_csv(
        csv_path, dtype={"market_id": str, "event_id": str}, float_precision="round_trip"
    )
    tampered.loc[0, "dmid_hat"] += 0.001
    with gzip.open(csv_path, "wt", newline="") as fh:
        tampered.to_csv(fh, index=False, float_format="%.17g")
    man = json.loads(man_path.read_text())
    man["forecast_csv_sha256"] = forecast.sha256_file(csv_path)
    man_path.write_text(json.dumps(man))
    with pytest.raises(AssertionError):
        forecast.score(a, b, SPEC, froot)


@pytest.mark.parametrize(
    "slope,noise,expected",
    [
        (-0.33, 0.01, "Confirmed (exploratory, prospective)"),
        (0.33, 0.01, "Not confirmed"),
        (-0.15, 0.08, "Inconclusive"),
    ],
)
def test_verdicts(tmp_path, slope, noise, expected):
    a, b = _pair(tmp_path, slope, noise=noise, n=400, seed=3)
    res = forecast.score(a, b, SPEC, tmp_path / "f")
    assert res["primary"]["verdict"] == expected, res["primary"]


def test_verdict_logic_edges():
    assert forecast.verdict(0.02, (0.01, 0.03), -0.3, (-0.4, -0.2)).startswith("Confirmed")
    assert forecast.verdict(0.02, (-0.01, 0.03), -0.3, (-0.4, -0.2)) == "Inconclusive"
    assert forecast.verdict(0.02, (0.01, 0.03), -0.3, (-0.4, 0.1)) == "Inconclusive"
    assert forecast.verdict(-0.01, (-0.02, 0.0), -0.3, (-0.4, -0.2)) == "Not confirmed"


def test_slope_bootstrap_deterministic_and_covers():
    rng = np.random.default_rng(5)
    m = np.repeat(np.arange(200), 3)
    x = rng.normal(size=600)
    y = -0.3 * x + rng.normal(0, 0.5, 600)
    ci1 = evaluate.clustered_bootstrap_slope(m, x, y)
    assert ci1 == evaluate.clustered_bootstrap_slope(m, x, y)
    assert ci1 != evaluate.clustered_bootstrap_slope(m, x, y, seed=7)
    assert ci1[0] < evaluate.ols_origin_slope(x, y) < ci1[1]
    assert ci1[0] < -0.3 < ci1[1] or abs(ci1[1] + 0.3) < 0.1


def _cap(start, state="complete"):
    s = datetime.fromisoformat(start).replace(tzinfo=UTC)
    return {"capture_id": start, "state": state, "_start": s, "dir": start}


def test_capture_selection_guard():
    reg = datetime(2026, 10, 10, 19, 20, 42, tzinfo=UTC)
    caps = [
        _cap("2026-10-10T19:00:00"),  # pre-registration: ignored
        _cap("2026-10-10T19:22:08"),
        _cap("2026-10-10T21:00:00"),  # < 3h after first: skipped
        _cap("2026-10-10T22:36:00"),  # 3h14m after first: qualifies
        _cap("2026-10-11T04:00:00"),
    ]
    first, second = forecast.select_e002_pair(caps, reg)
    assert first["capture_id"] == "2026-10-10T19:22:08"
    assert second["capture_id"] == "2026-10-10T22:36:00"
    assert forecast.select_e002_pair(caps[:3], reg) is None
    assert forecast.select_e002_pair(caps[:1], reg) is None


def test_list_complete_captures_ignores_incomplete(tmp_path):
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    df = _rows("X", t0, np.full(3, 0.5), np.zeros(3))
    _write(tmp_path, "X", t0, df, "incomplete:time_cap")
    _write(tmp_path, "Y", t0 + timedelta(hours=1), df)
    assert [c["capture_id"] for c in forecast.list_complete_captures(tmp_path)] == ["Y"]
