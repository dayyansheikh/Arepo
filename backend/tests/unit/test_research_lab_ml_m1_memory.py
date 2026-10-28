"""The M1 memory reduction must not move a single bit: chunked/in-place design vs the old one."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sklearn")

from astrolabe.research_lab import ml_models as mm  # noqa: E402
from astrolabe.research_lab import ml_panel  # noqa: E402
from tests.unit.test_research_lab_ml_models import _manifest, _panel  # noqa: E402

COLS = mm.M12_FEATURES


# ---- verbatim copies of the pre-change implementation (reference) ----
def _old_prep_transform(prep, x):
    z = np.where(np.isnan(x), prep.med, x)
    return (np.clip(z, prep.lo, prep.hi) - prep.mu) / prep.sd


class _OldDesign:
    def __init__(self, cols):
        self.cols = tuple(cols)

    def fit(self, x):
        from sklearn.preprocessing import SplineTransformer

        self.prep = mm._Prep(self.cols).fit(x)
        z = _old_prep_transform(self.prep, x)
        self.si = [self.cols.index(c) for c in mm.SPLINE_FEATURES]
        self.ii = [self.cols.index(c) for c in mm.INTERACTION_PARTNERS]
        self.ci = self.cols.index("ml_chg_1h")
        self.spl = SplineTransformer(
            n_knots=5, degree=3, knots="uniform", extrapolation="constant"
        ).fit(z[:, self.si])
        return self

    def transform(self, x):
        z = _old_prep_transform(self.prep, x)
        inter = z[:, [self.ci]] * z[:, self.ii]
        return np.hstack([z, self.spl.transform(z[:, self.si]), inter])


def _old_fit_m1(df, train_pos, test_pos, inner, **_):
    cols = mm.M12_FEATURES
    itr, iva = inner
    xtr_all = mm._xmat(df.iloc[train_pos], cols)
    design_in = _OldDesign(cols).fit(mm._xmat(df.iloc[itr], cols))
    xin, xva = design_in.transform(mm._xmat(df.iloc[itr], cols)), design_in.transform(
        mm._xmat(df.iloc[iva], cols)
    )
    yin, yva = mm._y(df, itr), mm._y(df, iva)
    search, best = [], None
    for cfg in mm.M1_GRID:
        m = mm._m1_model(cfg)
        nonconv = mm._quiet_fit(m, xin, yin)
        p = mm._finalise(mm._expand_classes(m.classes_, m.predict_proba(xva)))
        loss = float(mm.log_loss_rows(p, yva).mean())
        search.append({"config": cfg, "inner_val_log_loss": loss, "nonconverged": nonconv})
        if best is None or loss < best[0]:
            best = (loss, cfg, p)
    temp = mm.fit_temperature(best[2], yva)
    design = _OldDesign(cols).fit(xtr_all)
    m = mm._m1_model(best[1])
    nonconv = mm._quiet_fit(m, design.transform(xtr_all), mm._y(df, train_pos))
    xte = design.transform(mm._xmat(df.iloc[test_pos], cols))
    p = mm._expand_classes(m.classes_, m.predict_proba(xte))
    return mm.FoldFit(
        mm.apply_temperature(mm._finalise(p), temp),
        {"selected": best[1], "temperature": temp, "hyper_search": search,
         "nonconverged": nonconv}, None), m


def _x(n, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, len(COLS))) * rng.uniform(0.1, 30, size=len(COLS))
    x[rng.random(x.shape) < 0.08] = np.nan
    return x


@pytest.mark.parametrize("n,chunk", [(1, 4), (10, 4), (12, 4), (13, 4), (7, 100), (1000, 97)])
def test_chunked_transform_is_bit_identical(n, chunk):
    x = _x(max(n, 300))
    old = _OldDesign(COLS).fit(x)
    new = mm._M1Design(COLS).fit(x)
    assert np.array_equal(old.spl.bsplines_[0].t, new.spl.bsplines_[0].t)
    xt = _x(n, seed=3) * 2.0  # test rows incl. values outside the fitted range (extrapolation)
    ref = old.transform(xt)
    out = new.transform(xt, chunk=chunk)
    assert out.dtype == ref.dtype and out.shape == ref.shape
    assert np.array_equal(out, ref, equal_nan=True)
    assert np.array_equal(new.transform(xt), ref, equal_nan=True)  # default chunk


def test_fit_small_chunk_matches_old_fit(monkeypatch):
    monkeypatch.setattr(mm, "M1_CHUNK_ROWS", 37)
    x = _x(500)
    old, new = _OldDesign(COLS).fit(x), mm._M1Design(COLS).fit(x)
    assert np.array_equal(old.transform(x), new.transform(x), equal_nan=True)
    assert np.array_equal(old.prep.mu, new.prep.mu) and np.array_equal(old.prep.sd, new.prep.sd)


def test_fit_m1_end_to_end_bit_identical(monkeypatch):
    monkeypatch.setattr(mm, "M1_CHUNK_ROWS", 501)  # several chunks per matrix, ragged tail
    df = _panel()
    man = _manifest(df)
    fold = man["folds"][0]
    train_pos = np.where(df["period"].isin(fold["train_periods"]).to_numpy())[0]
    test_pos = np.where(df["period"].isin(fold["test_periods"]).to_numpy())[0]
    inner = mm.inner_split(df, train_pos, man["embargo_s"])
    new = mm.fit_m1(df, train_pos, test_pos, inner)
    old, _ = _old_fit_m1(df, train_pos, test_pos, inner)
    assert np.array_equal(new.proba, old.proba)
    assert new.diag["selected"] == old.diag["selected"]
    assert new.diag["temperature"] == old.diag["temperature"]
    assert new.diag["hyper_search"] == old.diag["hyper_search"]
    assert ml_panel.EXTENDED_NAMES == COLS
