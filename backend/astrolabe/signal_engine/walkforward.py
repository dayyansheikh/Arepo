# ruff: noqa: E501
"""Development / historical bootstrap. Until prospective scores accumulate, the dashboard shows a walk-forward run over
the feature store, labelled ``development_historical`` and kept apart from prospective scores (separate files, separate
dashboard block, never pooled, never used by the promotion rule).

For each test day D: every non-embargoed model is fitted on data available before D 00:00 UTC (``training.refit_all``,
nothing written), predicts every capture of day D in memory, and is scored with the labels known now. This is
retrospective (labels and inputs were all on disk when it ran), so it is development evidence only.
"""

from __future__ import annotations

import copy
import time

import numpy as np
import pandas as pd

from . import config as C
from . import labels as L
from . import learners
from . import scoring as SC
from . import specs as SP
from . import store as S
from . import training as T
from .features import ALL_FEATURES, KEY_COLUMNS


def run_walkforward(paths: S.Paths, reg: dict, champion: str, now: float, max_test_days: int = 7,
                    max_rows: int | None = None, write: bool = True) -> dict:
    t0 = time.time()
    index = S.load_index(paths)
    by_day: dict[str, list[tuple[int, dict]]] = {}
    for slot, m in sorted(index.items()):
        by_day.setdefault(S.day_of(S.epoch(m["started_utc"])), []).append((slot, m))
    days = sorted(by_day)
    models = {k: copy.deepcopy(v) for k, v in SP.active_models(reg).items() if not SP.embargo_of(v, now)}
    if max_rows:
        for s in models.values():
            s["train"]["max_rows"] = min(s["train"]["max_rows"], max_rows)
    min_days = max(s["train"].get("min_days", 1) for s in models.values())
    test_days = [d for d in days[min_days:] if d < S.day_of(now)][-max_test_days:]
    res = L.load_resolutions(paths)
    qc = L.QuoteCache(paths, index, keep=16)
    agg = SC.Agg(test_days[-1] if test_days else S.day_of(now), (max(len(test_days), 1),))
    fits = []
    for day in test_days:
        fit_time = pd.Timestamp(day, tz="UTC").timestamp()
        out = T.refit_all(paths, reg, fit_time, now, models=models, write=False)
        fits.append({"day": day, **{k: out["summary"][k] for k in ("frame_rows", "seconds")},
                     "status": {m: {t: v.get("status") for t, v in r["targets"].items()} for m, r in out["summary"]["models"].items()}})
        arts = out["arts"]
        for slot, m in by_day[day]:
            start = S.epoch(m["started_utc"])
            f = S.read_parquet(paths.features(m["capture_id"]), KEY_COLUMNS + ALL_FEATURES)
            ids = f["market_id"].to_numpy(np.int64)
            cl = SC.cluster_ids(f["event_id"].to_numpy(), ids)
            cats = f["category"].astype(str).to_numpy()
            elig = L.elig_mask(f, slot, start)
            for h, t in zip(C.HORIZONS_H, C.DIR_TARGETS, strict=True):
                y, st, _ = L.direction_labels(qc, index, slot, h, ids, f["ms_mid"].to_numpy(np.float64), now)
                _score(agg, models, arts, champion, t, day, f, (elig & C.ELIG_BITS[t]) > 0, y, st, cl, cats)
            y, st, _lt, _cl = L.resolution_labels(res, ids, f["end_ts"].to_numpy(float), now)
            _score(agg, models, arts, champion, C.RES_TARGET, day, f, (elig & C.ELIG_BITS[C.RES_TARGET]) > 0, y, st, cl, cats)
    lb = SC.leaderboard(agg, reg, champion, now, role="development_historical", windows=(max(len(test_days), 1),),
                        end_day=test_days[-1] if test_days else None)
    lb.update({"test_days": test_days, "fits": fits, "seconds": round(time.time() - t0, 1), "peak_rss_mb": S.peak_rss_mb(),
               "label": "development/historical (walk-forward, retrospective; not prospective evidence)"})
    if write:
        stamp = T.fit_stamp(now)
        S.write_once_json(paths.sub("dev", f"walkforward_{stamp}.json"), lb)
        S.replace_json(paths.sub("dev", "latest.json"), lb)
    return lb


def _score(agg, models, arts, champion, t, day, f, e, y, st, cl, cats) -> None:
    lab = e & (st == L.LABELLED)
    agg.add_labels(t, day, st[e])
    if not lab.any():
        return
    ll_by = {}
    sub = f[lab]
    for mid, spec in models.items():
        art = arts.get(mid, {}).get(t)
        if art is None:
            continue
        p = learners.predict(spec, art, sub)
        p = np.clip(p, C.P_CLIP, 1.0)
        p = p / p.sum(axis=1, keepdims=True)
        agg.add_cov(t, mid, day, int(e.sum()), int(e.sum()), 0)
        pr = p[:, 1] if t == C.RES_TARGET else p
        ll_by[mid] = agg.add_model(t, mid, day, y[lab].astype(np.int64), pr, cats[lab])
    if champion in ll_by:
        for mid, ll in ll_by.items():
            if mid != champion:
                agg.add_pair(t, mid, day, cl[lab], cats[lab], ll_by[champion] - ll)
