"""read_panel_compact must equal pd.read_parquet (values, dtypes, column order); synthetic data."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as papq
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_ml_dev.py"
spec = importlib.util.spec_from_file_location("run_ml_dev_under_test", SCRIPT)
rmd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rmd
spec.loader.exec_module(rmd)


def _write(path: Path) -> None:
    rng = np.random.default_rng(0)
    n = 5000
    f = rng.normal(size=n)
    f[::7] = np.nan
    df = pd.DataFrame({
        "market_id": [f"m{i % 300}" for i in range(n)],
        "x": f,
        "dep_group": [None if i % 11 == 0 else f"g{i % 17}" for i in range(n)],
        "period": np.arange(n) % 9,
        "target_available": rng.random(n) > 0.3,
        "y": rng.normal(size=n),
        "event_id": [None] * n,
    })
    papq.write_table(pa.Table.from_pandas(df), path, row_group_size=900)


@pytest.mark.parametrize("cols", [None, ["y", "market_id", "period", "dep_group"]])
def test_compact_read_identical(tmp_path, cols):
    p = tmp_path / "panel.parquet"
    _write(p)
    ref = pd.read_parquet(p, columns=cols)
    got = rmd.read_panel_compact(p, cols)
    pd.testing.assert_frame_equal(got, ref, check_exact=True)
    assert list(got.columns) == list(ref.columns)
    a = [type(v) for v in got["dep_group"].head(12)]
    assert a == [type(v) for v in ref["dep_group"].head(12)]


def test_labelled_consuming_matches_labelled(tmp_path):
    from astrolabe.research_lab import ml_panel

    p = tmp_path / "panel.parquet"
    _write(p)
    ref = ml_panel.labelled(pd.read_parquet(p))
    df = rmd.read_panel_compact(p)
    df.attrs["category_info"] = {"k": 1}
    got = rmd.labelled_consuming(df)
    pd.testing.assert_frame_equal(got, ref, check_exact=True)
    assert got.attrs == {"category_info": {"k": 1}}
    assert df.shape[1] == 0


def test_slim_panel_summary_equals_full():
    import json

    from astrolabe.research_lab import ml_panel

    rng = np.random.default_rng(1)
    n = 600
    d = {c: rng.normal(size=n) for c in ml_panel.EXTENDED_NAMES}
    d["rep_sw_gap"] = rng.normal(size=n)
    for c in ("dmid", "t_i", "t0", "t_j"):
        d[c] = rng.normal(size=n)
    d["period"] = np.arange(n) % 6
    d["capture_i"] = [f"c{i % 6}" for i in range(n)]
    d["target_available"] = rng.random(n) > 0.3
    d["y_class"] = rng.integers(0, 3, n)
    d["event_id"] = [None if i % 5 == 0 else f"e{i % 40}" for i in range(n)]
    d["market_id"] = [f"m{i % 90}" for i in range(n)]
    for c in ("dep_group", "dep_group_season", "dep_group_econ", "dep_group_category_driver"):
        d[c] = [f"{c}{i % 25}" for i in range(n)]
    d["dep_group_no_parent"] = rng.random(n) > 0.5
    df = pd.DataFrame(d)
    full = json.dumps(rmd._clean(rmd.panel_summary(df)), default=rmd._jsonable)
    slim = json.dumps(rmd._clean(rmd.slim_panel_summary(df)), default=rmd._jsonable)
    assert full == slim


def test_read_labelled_panel_equals_labelled_compact(tmp_path):
    from astrolabe.research_lab import ml_panel

    p = tmp_path / "panel.parquet"
    _write(p)
    df = rmd.read_panel_compact(p)
    ref = ml_panel.labelled(df)
    pd.testing.assert_frame_equal(rmd.read_labelled_panel(p), ref, check_exact=True)
    keep = [c for c in ref.columns if not c.startswith("x")]
    got = rmd.read_labelled_panel(p, exclude_prefix="x")
    pd.testing.assert_frame_equal(got, ref[keep], check_exact=True)
    got = rmd.read_labelled_panel(p, columns=["y", "dep_group"])
    pd.testing.assert_frame_equal(got, ref[["dep_group", "y"]], check_exact=True)


def test_shuffle_labels_shallow_copy_leaves_input_untouched():
    rng = np.random.default_rng(1)
    n = 400
    lab = pd.DataFrame({"period": np.arange(n) % 5, "event_id": [f"e{i % 40}" for i in range(n)],
                        "market_id": [f"m{i}" for i in range(n)],
                        "y_class": rng.integers(0, 3, n).astype(float),
                        "f1": rng.normal(size=n), "f2": rng.normal(size=n)})
    before = lab.copy(deep=True)
    out = rmd.shuffle_labels(lab, "period")
    pd.testing.assert_frame_equal(lab, before, check_exact=True)
    ref = before.copy()  # the previous implementation: deep copy
    y = ref["y_class"].to_numpy(float).copy()
    g = np.random.default_rng(rmd.SHUFFLE_SEED)
    for idx in ref.groupby(rmd._block_key(ref, "period"), sort=True).indices.values():
        y[idx] = y[g.permutation(idx)]
    ref["y_class"] = y
    pd.testing.assert_frame_equal(out, ref, check_exact=True)
