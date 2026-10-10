"""Feature registry for leakage-safe model comparison.

Every feature is computed from origin-side (capture i) columns only. ``FeatureSpec.compute``
receives a frame restricted to ``requires`` and registration refuses label-side columns, so a
feature cannot read the target or anything observed at j. The E001 set delegates to
``panel.compute_features`` (not reimplemented). Pair frames built by ``panel.build_panel`` carry
those features already materialised; ``feature_matrix`` uses the stored column when the raw
origin columns are absent.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import panel

LABEL_COLUMNS = frozenset({"t_j", "mid_j", "dmid", "horizon_h"})
FAMILIES = ("price", "momentum", "context", "interaction", "book")
E001_ORIGIN_COLUMNS = (
    "best_bid",
    "best_ask",
    "spread",
    "chg_1h",
    "chg_1d",
    "chg_1w",
    "liquidity",
    "volume24hr",
    "end_date",
    "last_trade_price",
    "received_utc",
)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    family: str
    version: str
    compute: Callable[[pd.DataFrame], pd.Series]
    requires: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = field(default_factory=tuple)  # other features it is built from


REGISTRY: dict[str, FeatureSpec] = {}


def register(spec: FeatureSpec) -> FeatureSpec:
    if spec.family not in FAMILIES:
        raise ValueError(f"unknown family {spec.family!r}")
    if spec.name in REGISTRY:
        raise ValueError(f"feature {spec.name!r} already registered")
    bad = (set(spec.requires) | {spec.name}) & LABEL_COLUMNS
    if bad:
        raise ValueError(f"feature {spec.name!r} touches label-side columns {sorted(bad)}")
    REGISTRY[spec.name] = spec
    return spec


def compute_origin(spec: FeatureSpec, origin_df: pd.DataFrame) -> pd.Series:
    """Run ``spec.compute`` on only its declared origin columns."""
    missing = [c for c in spec.requires if c not in origin_df.columns]
    if missing:
        raise KeyError(f"feature {spec.name!r} needs origin columns {missing}")
    return spec.compute(origin_df[list(spec.requires)])


def _e001(name: str) -> Callable[[pd.DataFrame], pd.Series]:
    def compute(o: pd.DataFrame) -> pd.Series:
        t_i = panel._epoch(o["received_utc"])
        return panel.compute_features(o, t_i)[name]

    return compute


def _register_e001() -> None:
    groups = {
        "price": ["mid", "spread"],
        "momentum": [
            "chg_1h",
            "chg_1d",
            "chg_1w",
            "chg_1h_missing",
            "chg_1d_missing",
            "chg_1w_missing",
        ],
        "context": [
            "log_liq",
            "log_vol",
            "log_hours_to_end",
            "end_unknown",
            "ltp_minus_mid",
            "ltp_missing",
        ],
        "interaction": ["chg1d_x_logliq"],
    }
    assert sorted(sum(groups.values(), [])) == sorted(panel.FEATURES_B3)
    for fam, names in groups.items():
        for n in names:
            register(
                FeatureSpec(
                    n,
                    fam,
                    "e001-v1",
                    _e001(n),
                    E001_ORIGIN_COLUMNS,
                    ("chg_1d", "log_liq") if fam == "interaction" else (),
                )
            )


def _book_imbalance(o: pd.DataFrame) -> pd.Series:
    b, a = o["bid_depth"].astype(float), o["ask_depth"].astype(float)
    tot = (b + a).where((b + a) > 0)
    return ((b - a) / tot).fillna(0.0)


_register_e001()
register(
    FeatureSpec("book_imbalance", "book", "book-v1", _book_imbalance, ("bid_depth", "ask_depth"))
)


def available(frame: pd.DataFrame, spec: FeatureSpec) -> bool:
    """Computable from raw origin columns, or already materialised in ``frame``."""
    return set(spec.requires) <= set(frame.columns) or spec.name in frame.columns


def expand(items: list[str] | tuple[str, ...], frame: pd.DataFrame | None = None) -> list[str]:
    """Expand feature names and ``family:<name>`` tokens into ordered, unique feature names.

    Family members come in registry order; with ``frame`` only available ones are kept (so book
    features appear only when book columns exist).
    """
    out: list[str] = []
    for it in items:
        if it.startswith("family:"):
            fam = it.split(":", 1)[1]
            if fam not in FAMILIES:
                raise ValueError(f"unknown family {fam!r}")
            names = [
                s.name
                for s in REGISTRY.values()
                if s.family == fam and (frame is None or available(frame, s))
            ]
        elif it in REGISTRY:
            names = [it]
        else:
            raise KeyError(f"unknown feature {it!r}")
        out += [n for n in names if n not in out]
    return out


def feature_matrix(frame: pd.DataFrame, names: list[str]) -> np.ndarray:
    cols = []
    for n in names:
        spec = REGISTRY[n]
        if set(spec.requires) <= set(frame.columns):
            s = compute_origin(spec, frame)
        elif n in frame.columns:
            s = frame[n]
        else:
            raise KeyError(f"feature {n!r} not computable: missing {list(spec.requires)}")
        cols.append(s.to_numpy(float))
    X = np.column_stack(cols) if cols else np.empty((len(frame), 0))
    if not np.isfinite(X).all():
        raise ValueError("non-finite feature values; features must be imputed with flags")
    return X


def versions(names: list[str]) -> dict[str, dict[str, str]]:
    return {n: {"family": REGISTRY[n].family, "version": REGISTRY[n].version} for n in names}
