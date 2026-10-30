"""Benchmark: peak RSS of the old vs new MC1 panel read-back + placebo-stage path, synthetic data
shaped like the real panel (123 cols: 109 float64, 12 string, 1 int64, 1 bool; 78 row groups).

``python scripts/bench_mc1_panel_memory.py gen <dir> <rows>`` then ``... run old|new <dir>``
(each in its own process; prints peak RSS MB and a value hash of lab, shuffled lab, leak lab)."""
from __future__ import annotations

import hashlib
import importlib.util
import resource
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as papq

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rmd", HERE / "run_ml_dev.py")
rmd = importlib.util.module_from_spec(spec)
sys.modules["rmd"] = rmd
spec.loader.exec_module(rmd)
NF, NLEAK = 47, 47  # feature and leak columns (the rest of the 109 floats are unused extras)


def gen(d: Path, n: int) -> None:
    rng = np.random.default_rng(0)
    cols = {}
    for i in range(109):
        v = rng.normal(size=n)
        v[rng.random(n) < 0.1] = np.nan
        cols[f"c{i:03d}"] = v
    names = [f"c{i:03d}" for i in range(109)]
    ren = {}
    for i in range(NF):
        ren[names[i]] = f"f{i}"
    for i in range(NLEAK):
        ren[names[NF + i]] = f"leak_f{i}"
    ren[names[94]], ren[names[95]], ren[names[96]], ren[names[97]] = "y_class", "dmid", "t0", "t_j"
    ren[names[98]], ren[names[99]] = "t_i", "rep_sw_gap"
    cols = {ren.get(k, k): v for k, v in cols.items()}
    cols["y_class"] = rng.integers(0, 3, n).astype(float)
    cols["period"] = np.sort(rng.integers(0, 78, n)).astype(np.int64)
    cols["target_available"] = rng.random(n) > 0.003
    for s in ["market_id", "event_id", "capture_i", "capture_j", "fee_category", "dep_group",
              "dep_group_season", "dep_group_fixture_day", "dep_group_econ",
              "dep_group_category_driver", "dep_group_period", "dep_group_season_period"]:
        cols[s] = np.array([f"{s}{i % 5000}" for i in range(n)], dtype=object)
    cols["dep_group_no_parent"] = rng.random(n)
    t = pa.Table.from_pandas(pd.DataFrame(cols), preserve_index=False)
    d.mkdir(parents=True, exist_ok=True)
    papq.write_table(t, d / "panel.parquet", row_group_size=max(n // 78, 1))


def h(df: pd.DataFrame, cols=None) -> str:
    df = df if cols is None else df[cols]
    x = pd.util.hash_pandas_object(df, index=True).to_numpy()
    return hashlib.sha256(x.tobytes() + "|".join(map(str, df.columns)).encode()).hexdigest()[:16]


def peak() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if sys.platform == "darwin" else r / 1e3


def main(mode: str, d: Path) -> None:
    pq = d / "panel.parquet"
    leak = [f"leak_f{i}" for i in range(NLEAK)]
    feats = [f"f{i}" for i in range(NF)]
    if mode == "old":
        df = rmd.read_panel_compact(pq)
        rmd.slim_panel_summary(df)
        lab = rmd.labelled_consuming(df)
        del df
        shuf = lab.copy()  # shuffle_labels, old implementation (deep copy)
        shuf["y_class"] = np.random.default_rng(1).permutation(shuf["y_class"].to_numpy())
        lk = lab.copy()
        for i in range(NF):
            lk[f"f{i}"] = lab[f"leak_f{i}"]
    else:
        df = rmd.read_panel_compact(pq, list(rmd.DRY_COLUMNS))
        rmd.panel_summary(df.copy(), rmd.feature_nan_rates(pq, feats))
        lab = rmd.read_labelled_panel(pq, exclude_prefix="leak_")
        del df
        shuf = lab.copy(deep=False)
        shuf["y_class"] = np.random.default_rng(1).permutation(shuf["y_class"].to_numpy())
        src = rmd.read_labelled_panel(pq, columns=leak)
        lk = lab.copy(deep=False)
        for i in range(NF):
            lk[f"f{i}"] = src[f"leak_f{i}"].to_numpy()
        del src
    base = [c for c in lab.columns if not c.startswith("leak_")]
    print(f"{mode} peak_rss_mb={peak():.0f} lab_rows={len(lab)} "
          f"hash_lab={h(lab, base)} hash_shuf={h(shuf, base)} hash_leak={h(lk, base)}")


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        main(sys.argv[2], Path(sys.argv[3]))
