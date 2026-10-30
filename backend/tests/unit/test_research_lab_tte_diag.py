"""q0100: descriptive C-TTE diagnostics on synthetic data (no counted tests)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import tte_diag as td

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_ml_history.py"
spec = importlib.util.spec_from_file_location("run_ml_history_td", SCRIPT)
rmh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmh)

DAY = 86400.0
T0 = 1_760_000_000.0


OFFSETS = (-40 * DAY, -20 * DAY, -5 * DAY, -10 * 3600.0, -2 * 3600.0, 3 * 3600.0, 10 * 3600.0)


def _synth(n_markets=60, seed=1):
    rng = np.random.default_rng(seed)
    rows, fr = [], []
    for m in range(n_markets):
        end = T0 + (m % 4) * 40 * DAY + 50 * DAY  # far-end markets get >30d at early origins
        # market kinds: 0 normal, 1 closes 3 days before end (look-ahead), 2 closes at end+30min
        kind = m % 6
        close = end - 3 * DAY if kind == 1 else end + 1800 if kind == 2 else end + 5 * DAY
        fr.append({"market_id": str(m), "end_epoch": end, "close_epoch": close})
        for off in OFFSETS:  # 40d..2h before end, then 3h and 10h after end (post-end rows)
            t = end + off
            rows.append({"market_id": str(m), "event_id": str(m // 2), "t_i": t})
    lab = pd.DataFrame(rows)
    end_map = {f["market_id"]: f["end_epoch"] for f in fr}
    end = lab["market_id"].map(end_map).to_numpy()
    lab["ml_log_hours_to_end"] = np.log1p(np.clip((end - lab["t_i"].to_numpy()) / 3600.0, 0, None))
    delta = rng.normal(0.0, 0.05, len(lab)) + np.where(lab["ml_log_hours_to_end"] < 3.2, 0.03, 0.0)
    clusters = {"event": lab["event_id"].to_numpy(), "dep_group": lab["event_id"].to_numpy()}
    return lab, delta, clusters, pd.DataFrame(fr)


def test_split_and_variants():
    lab, delta, clusters, frame = _synth()
    out = td.tte_diagnostics(lab, delta, clusters, frame, n_boot=50)
    assert out["label"] == td.LABEL and out["end_epoch_vs_feature_mismatch_rows"] == 0
    sp = out["bin_lt24h_split"]
    # two origins per market are after end: clipped to 0h, so in "<24h" as post-end
    assert sp["post_end"]["n_rows"] == 120 and sp["post_end"]["n_markets"] == 60
    assert sp["pre_end"]["n_rows"] > 0 and sp["end_unknown"]["n_rows"] == 0
    c = out["contrasts"]
    assert set(c) == {"as_replicated", "lookahead_excluded", "plus_pre_end_only",
                      "plus_post_end_only", "near_end_markets_excluded"}
    for v in c.values():
        assert "utc_day" in v["by_cluster"] and "hull_event_dep_group" in v
        assert v["label"] == td.LABEL
    n_plus = lambda k: c[k]["n_rows"][0]  # noqa: E731
    assert n_plus("plus_pre_end_only") + n_plus("plus_post_end_only") == n_plus("as_replicated")
    assert n_plus("lookahead_excluded") < n_plus("as_replicated")
    assert out["markets"]["n_lookahead"] == 10  # kind 1: m % 6 == 1 -> 10 of 60
    assert out["markets"]["n_near_end"] == 10  # kind 2
    assert n_plus("near_end_markets_excluded") < n_plus("as_replicated")


def test_post_end_rows_have_nonzero_effect_when_planted():
    lab, delta, clusters, frame = _synth()
    post = lab["ml_log_hours_to_end"].to_numpy() == 0.0
    delta = np.where(post, delta + 0.5, delta)
    out = td.tte_diagnostics(lab, delta, clusters, frame, n_boot=50)
    c = out["contrasts"]
    assert c["plus_post_end_only"]["hull_event_dep_group"]["mean"] > \
        c["plus_pre_end_only"]["hull_event_dep_group"]["mean"] + 0.3


def test_near_end_tolerance_is_declared_one_hour():
    assert td.NEAR_END_TOL_S == 3600.0
    fr = pd.DataFrame({"market_id": ["a", "b", "c", "d"], "end_epoch": [0.0, 0.0, 0.0, np.nan],
                       "close_epoch": [3500.0, -3700.0, np.nan, 10.0]})
    f = td.market_flags(fr)
    assert f["near_end"].to_dict() == {"a": True, "b": False, "c": False, "d": False}
    assert not f["lookahead"].any()


def test_lookahead_matches_runner_definition(tmp_path):
    fr = pd.DataFrame({"market_id": ["a", "b"], "end_epoch": [10 * DAY, 10 * DAY],
                       "close_epoch": [10 * DAY - 25 * 3600, 10 * DAY - 23 * 3600]})
    (tmp_path / "frame.csv.gz").write_bytes(b"")
    fr.to_csv(tmp_path / "frame.csv.gz", index=False)
    runner = rmh.lookahead_markets(tmp_path)
    flags = td.market_flags(fr)
    assert runner == set(flags.index[flags["lookahead"]]) == {"a"}


def test_base_cols_check():
    ok = td.check_base_cols({"base_cols": list(rmh.M0V)}, rmh.M0V)
    assert ok["base_cols_equal_m0v"] and ok["m0v_includes_ml_log_hours_to_end"]
    bad = td.check_base_cols({"base_cols": list(rmh.M0V)[:-1]}, rmh.M0V)
    assert not bad["base_cols_equal_m0v"]


def test_run_note_book_boilerplate_only_when_absent():
    assert "Book features absent" in rmh.run_note(False)
    assert "Book features absent" not in rmh.run_note(True)
    assert "No edge, calibration or profitability claim" in rmh.run_note(True)
