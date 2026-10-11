"""run_ml_history: optional external joins (book, wallet age) keep NaN where absent."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_ml_history.py"
spec = importlib.util.spec_from_file_location("run_ml_history", SCRIPT)
rmh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmh)

T_IN = datetime(2026, 5, 1, tzinfo=UTC).timestamp()  # inside the pmxt window
T_OUT = datetime(2026, 9, 1, tzinfo=UTC).timestamp()  # after it


def _panel():
    t = [T_IN, T_IN + 21600, T_IN, T_OUT]
    return pd.DataFrame({"market_id": ["1", "1", "2", "1"], "t_i": t, "ml_sw_imb_top": np.nan})


def test_join_book_restricts_to_window_and_keeps_nan(tmp_path):
    bf = pd.DataFrame({"market_id": ["1"], "origin_ts": [T_IN], "ml_sw_imb_top": [0.3],
                       "state": ["two_sided"]})
    p = tmp_path / "book.csv.gz"
    bf.to_csv(p, index=False)
    out, info = rmh.join_external(_panel(), p, None)
    assert len(out) == 3 and (out["t_i"] < T_OUT).all()  # out-of-window origin dropped
    assert out["ml_sw_imb_top"].notna().sum() == 1  # only the matched (market, origin)
    assert info["book"]["rows_with_book"] == 1 and info["wallet_age"] is None


def test_join_absent_tables_is_noop():
    out, info = rmh.join_external(_panel(), None, None)
    assert len(out) == 4 and info == {"book": None, "wallet_age": None}


def test_join_wallet_age(tmp_path):
    wa = pd.DataFrame({"market_id": ["2"], "origin_ts": [T_IN], "ml_wage_median_days": [12.0],
                       "other": [1]})
    p = tmp_path / "wa.csv"
    wa.to_csv(p, index=False)
    out, info = rmh.join_external(_panel(), None, p)
    assert len(out) == 4 and out["ml_wage_median_days"].notna().sum() == 1
    assert "other" not in out.columns
