"""DEVELOPMENT-only candidate features for reversal-moderation screening (not evidence).

Pre-listed screening family (written BEFORE any run; six variants, nothing else is tried):
  1. rev_x_spread      = chg_1h * spread
  2. rev_x_logliq      = chg_1h * log_liq
  3. rev_large_move    = chg_1h * 1[|chg_1h| > 0.02]  (excess slope for large moves; the 0.02
                         threshold is fixed here a priori, no other threshold is tried)
  4. rev_x_loghours    = chg_1h * log_hours_to_end
  5. rev_x_midext      = chg_1h * |mid - 0.5|
  6. nr_excess, nr_member = (S_g - 1) * member, member flag; S_g = sum of member mids in a valid
                         E005 neg-risk group, members only (descriptive, NOT E005's band feature)

Every feature reads origin (capture i) columns only; registration refuses label-side columns
(``features.register``). Missing inputs are imputed with 0 (chg_1h is already 0-imputed upstream).
Neg-risk columns are attached by ``add_negrisk_columns`` from the ORIGIN capture's rows only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import e005, features
from .features import FeatureSpec

LARGE_MOVE = 0.02
VERSION = "dev-v1"
NR_COLUMNS = ("nr_excess", "nr_member")


def _col(o: pd.DataFrame, name: str) -> np.ndarray:
    return np.nan_to_num(o[name].to_numpy(float), nan=0.0)


def _rev_x(other: str):
    def compute(o: pd.DataFrame) -> pd.Series:
        return pd.Series(_col(o, "chg_1h") * _col(o, other), index=o.index)

    return compute


def _rev_x_midext(o: pd.DataFrame) -> pd.Series:
    return pd.Series(_col(o, "chg_1h") * np.abs(_col(o, "mid") - 0.5), index=o.index)


def _rev_large(o: pd.DataFrame) -> pd.Series:
    c = _col(o, "chg_1h")
    return pd.Series(c * (np.abs(c) > LARGE_MOVE), index=o.index)


def _passthrough(name: str):
    def compute(o: pd.DataFrame) -> pd.Series:
        return pd.Series(_col(o, name), index=o.index)

    return compute


def _register() -> None:
    inter = "interaction"
    specs = [
        FeatureSpec(
            "rev_x_spread",
            inter,
            VERSION,
            _rev_x("spread"),
            ("chg_1h", "spread"),
            ("chg_1h", "spread"),
        ),
        FeatureSpec(
            "rev_x_logliq",
            inter,
            VERSION,
            _rev_x("log_liq"),
            ("chg_1h", "log_liq"),
            ("chg_1h", "log_liq"),
        ),
        FeatureSpec("rev_large_move", inter, VERSION, _rev_large, ("chg_1h",), ("chg_1h",)),
        FeatureSpec(
            "rev_x_loghours",
            inter,
            VERSION,
            _rev_x("log_hours_to_end"),
            ("chg_1h", "log_hours_to_end"),
            ("chg_1h", "log_hours_to_end"),
        ),
        FeatureSpec(
            "rev_x_midext", inter, VERSION, _rev_x_midext, ("chg_1h", "mid"), ("chg_1h", "mid")
        ),
        FeatureSpec("nr_excess", "context", VERSION, _passthrough("nr_excess"), ("nr_excess",)),
        FeatureSpec("nr_member", "context", VERSION, _passthrough("nr_member"), ("nr_member",)),
    ]
    for s in specs:
        if s.name not in features.REGISTRY:
            features.register(s)


_register()

VARIANTS: dict[str, tuple[str, ...]] = {
    "v1_rev_x_spread": ("rev_x_spread",),
    "v2_rev_x_logliq": ("rev_x_logliq",),
    "v3_rev_large_move": ("rev_large_move",),
    "v4_rev_x_loghours": ("rev_x_loghours",),
    "v5_rev_x_midext": ("rev_x_midext",),
    "v6_negrisk_excess": ("nr_excess", "nr_member"),
}


def add_negrisk_columns(
    pairs: pd.DataFrame, origin_by_period: dict[int, pd.DataFrame]
) -> pd.DataFrame:
    """Attach nr_excess / nr_member per pair from the ORIGIN capture of its period only.

    ``origin_by_period[p]`` holds the capture-i rows (with neg-risk columns) of period p.
    nr_excess = S_g - 1 (S_g: sum of member mids, bid NaN -> 0) for members of an E005-valid
    group, else 0; nr_member = 1 for those members. Non-members and invalid groups get 0/0.
    """
    out = pairs.copy()
    ex = np.zeros(len(out))
    mem = np.zeros(len(out))
    for p, rows in origin_by_period.items():
        sel = np.flatnonzero(out["period"].to_numpy() == p)
        if not len(sel):
            continue
        m, _, _ = e005.group_members(rows)
        s_g = ((m["A_g"] + m["B_g"]) / 2.0).rename("s_g")
        s_by_mkt = s_g[~s_g.index.duplicated()]
        v = s_by_mkt.reindex(out["market_id"].iloc[sel]).to_numpy(float)
        ok = ~np.isnan(v)
        ex[sel] = np.where(ok, v - 1.0, 0.0)
        mem[sel] = ok.astype(float)
    out["nr_excess"], out["nr_member"] = ex, mem
    return out
