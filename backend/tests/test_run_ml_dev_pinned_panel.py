"""--panel-hash: a pinned panel loads without any snapshot dir, refuses when absent/mismatched,
and gives the same fold plan / resume identity in every slice. Synthetic fixture only."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_ml_dev.py"
spec = importlib.util.spec_from_file_location("run_ml_dev_pinned_under_test", SCRIPT)
rmd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rmd
spec.loader.exec_module(rmd)

H = "ab" * 32
N_PERIODS = 20


def _counts():
    return [{"period": p, "capture_i": f"c{p}", "capture_j": f"c{p + 1}", "gap_h": 2.0}
            for p in range(N_PERIODS)]


def _make(cache_root: Path, h: str = H, leak: bool = True, meta_extra: dict | None = None):
    d = cache_root / h
    d.mkdir(parents=True)
    rows = []
    for p in range(N_PERIODS):
        for k in range(6):
            t0 = 1_000_000.0 + p * 7200
            rows.append({"period": p, "capture_i": f"c{p}", "t0": t0, "t_i": t0, "t_j": t0 + 7200,
                         "target_available": k != 0, "dmid": 0.01 * k, "y_class": k % 3, "event_id": f"e{k}", "dep_group": f"g{k}",
                         "rep_sw_gap": 0.0, "market_id": f"m{k}",
                         "x": float(p + k), **({"leak_x": 1.0} if leak else {})})
    pd.DataFrame(rows).to_parquet(d / "panel.parquet")
    meta = {"counts": _counts(), "category_info": {"k": 1}, "n_rows": len(rows)}
    meta.update(meta_extra or {})
    (d / "meta.json").write_text(json.dumps(meta))
    return d


def test_pinned_load_works_without_snapshots(tmp_path):
    _make(tmp_path)
    df, counts, h, cdir, cached = rmd.load_pinned_panel(tmp_path, H, columns=["period", "t0"])
    assert h == H and cached is True and cdir == tmp_path / H
    assert list(df.columns) == ["period", "t0"] and len(df) == N_PERIODS * 6
    assert df.attrs["category_info"] == {"k": 1} and len(counts) == N_PERIODS


@pytest.mark.parametrize("case", ["missing", "bad_hex", "meta_mismatch", "no_leak", "no_meta"])
def test_pinned_refuses(tmp_path, case):
    pin = H
    if case == "bad_hex":
        _make(tmp_path)
        pin = "xyz"
    elif case == "meta_mismatch":
        _make(tmp_path, meta_extra={"panel_hash": "cd" * 32})
    elif case == "no_leak":
        _make(tmp_path, leak=False)
    elif case == "no_meta":
        (_make(tmp_path) / "meta.json").unlink()
    with pytest.raises(SystemExit) as e:
        rmd.load_pinned_panel(tmp_path, pin)
    assert "REFUSED" in str(e.value)
    assert not (tmp_path / "periods").exists()  # nothing was built


def test_gate_comes_from_panel_periods(tmp_path):
    caps, gate, rep = rmd.pinned_context(_counts(), 10)
    assert gate["met"] and gate["longest_consecutive_run"] == N_PERIODS + 1
    assert len(caps) == N_PERIODS + 1 and rep["pinned"]
    assert not rmd.pinned_context(_counts(), 40)[1]["met"]


def test_same_fold_plan_whatever_the_snapshot_dir(tmp_path, monkeypatch):
    _make(tmp_path)
    plans, idents = [], []
    for snap_files in (0, 3):  # snapshot dir content differs between invocations
        snaps = tmp_path / f"snaps{snap_files}"
        snaps.mkdir()
        for i in range(snap_files):
            (snaps / f"s{i}").mkdir()
        df, _, h, _, _ = rmd.load_pinned_panel(tmp_path, H, columns=list(rmd.DRY_COLUMNS))
        man, why = rmd.plan(df)
        assert man is not None and man["folds"], why
        plans.append(rmd.fold_plan_sha256(man))
        args = SimpleNamespace(argv=["--panel-hash", H])
        idents.append(rmd.resume_identity(args, man, h))
    assert plans[0] == plans[1]
    assert idents[0] == idents[1] and idents[0]["panel_hash"] == H
