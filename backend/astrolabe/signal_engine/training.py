# ruff: noqa: E501
"""Walk-forward training frames and the daily refit.

A fit at time ``F`` uses only origin captures that started before ``F`` and labels that were AVAILABLE before ``F``
(direction: the target capture finished before ``F``; resolution: the fetch receipt before ``F``). Frames are built
capture by capture from the feature store: only the needed columns are read, rows are subsampled per capture with a
seeded generator (so the frame never exceeds ``max_rows`` per target), and everything is float32. Peak memory is about
(max_rows x columns x 4 bytes) plus one capture, far below the MC1 failure mode (a 2.1M x 123 float64 panel).
"""

from __future__ import annotations

import math
import time
import traceback
import zlib

import numpy as np
import pandas as pd

from . import config as C
from . import labels as L
from . import learners
from . import specs as SP
from . import store as S
from .aux import AUX_ALL, read_features, spec_aux_families
from .features import ALL_FEATURES, KEY_COLUMNS, SOURCE_FAMILIES

FRAME_COLUMNS = KEY_COLUMNS + ALL_FEATURES + AUX_ALL


def _rng(*parts) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32("|".join(map(str, parts)).encode()))


def _sources(meta: dict, f: pd.DataFrame | None = None) -> dict[str, bool]:
    """Base stream availability from the capture meta, plus each aux family's join result for the read frame."""
    src = meta.get("sources") or {}
    out = {fam: bool(src.get(fam)) for fam in SOURCE_FAMILIES}
    if f is not None:
        out.update({fam: bool(ok) for fam, ok in f.attrs.get("aux_ok", {}).items()})
    return out


def direction_frame(paths: S.Paths, index: dict[int, dict], fit_time: float, window_days: float, max_rows: int,
                    now: float, seed: str = "dir") -> pd.DataFrame:
    """Rows with at least one direction label available before ``fit_time``; y_<target> = -1 where none."""
    lo = fit_time - window_days * 86400.0
    caps = [(k, m) for k, m in sorted(index.items()) if lo <= S.epoch(m["started_utc"]) < fit_time]
    if not caps:
        return pd.DataFrame()
    per_cap = int(math.ceil(max_rows / len(caps)))
    qc = L.QuoteCache(paths, index, keep=40)
    parts = []
    for slot, m in caps:
        p = paths.features(m["capture_id"])
        if not p.exists():
            continue
        f = read_features(paths, m["capture_id"], FRAME_COLUMNS)
        src = _sources(m, f)
        start = S.epoch(m["started_utc"])
        ids, mid = f["market_id"].to_numpy(np.int64), f["ms_mid"].to_numpy(np.float64)
        any_lab = np.zeros(len(f), bool)
        ys, lts = {}, {}
        for h, t in zip(C.HORIZONS_H, C.DIR_TARGETS, strict=True):
            y, st, lt = L.direction_labels(qc, index, slot, h, ids, mid, now)
            ok = (st == L.LABELLED) & L.dir_eligible(f["end_ts"].to_numpy(float), slot, h) & (lt < fit_time)
            y = np.where(ok, y, -1).astype(np.int8)
            ys[t], lts[t] = y, np.where(ok, lt, np.nan)
            any_lab |= ok
        if not any_lab.any():
            continue
        idx = np.flatnonzero(any_lab)
        if len(idx) > per_cap:
            idx = np.sort(_rng(seed, m["capture_id"]).choice(idx, per_cap, replace=False))
        g = f.iloc[idx].reset_index(drop=True)
        for t in C.DIR_TARGETS:
            g[f"y_{t}"] = ys[t][idx]
            g[f"lt_{t}"] = lts[t][idx]
        g["otime"] = start
        for fam, ok in src.items():
            g[f"src_{fam}"] = ok
        parts.append(g)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out["category"] = out["category"].astype("category")
    return out


def resolution_frame(paths: S.Paths, index: dict[int, dict], res: pd.DataFrame, fit_time: float, window_days: float,
                     max_rows: int, now: float, seed: str = "res") -> pd.DataFrame:
    lo = fit_time - window_days * 86400.0
    caps = [(k, m) for k, m in sorted(index.items()) if lo <= S.epoch(m["started_utc"]) < fit_time]
    if not caps or res.empty:
        return pd.DataFrame()
    per_cap = int(math.ceil(max_rows / len(caps)))
    parts = []
    for _slot, m in caps:
        p = paths.features(m["capture_id"])
        if not p.exists():
            continue
        start = S.epoch(m["started_utc"])
        f = read_features(paths, m["capture_id"], FRAME_COLUMNS)
        src = _sources(m, f)
        el = L.res_eligible(f["end_ts"].to_numpy(float), start)
        if not el.any():
            continue
        f = f[el].reset_index(drop=True)
        y, st, lt, _closed = L.resolution_labels(res, f["market_id"].to_numpy(np.int64), f["end_ts"].to_numpy(float), now, fit_time)
        ok = st == L.LABELLED
        if not ok.any():
            continue
        idx = np.flatnonzero(ok)
        if len(idx) > per_cap:
            idx = np.sort(_rng(seed, m["capture_id"]).choice(idx, per_cap, replace=False))
        g = f.iloc[idx].reset_index(drop=True)
        g["y_res_7d"] = y[idx]
        g["lt_res_7d"] = lt[idx]
        g["otime"] = start
        for fam, okk in src.items():
            g[f"src_{fam}"] = okk
        parts.append(g)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out["category"] = out["category"].astype("category")
    return out


def select_rows(frame: pd.DataFrame, spec: dict, target: str, fit_time: float) -> pd.DataFrame:
    tr = spec["train"]
    wd = tr["res_window_days"] if target == C.RES_TARGET else tr["window_days"]
    m = (frame[f"y_{target}"].to_numpy() >= 0) & (frame["otime"].to_numpy(float) >= fit_time - wd * 86400.0)
    for fam in tr["require_sources"]:
        m &= frame[f"src_{fam}"].to_numpy(bool)
    sub = frame[m]
    if len(sub) > tr["max_rows"]:
        sub = sub.iloc[np.sort(_rng(spec["model_id"], target, fit_time).choice(len(sub), tr["max_rows"], replace=False))]
    return sub.reset_index(drop=True)


def aux_coverage(frame: pd.DataFrame, spec: dict, target: str, fit_time: float) -> dict:
    """Per aux family of the spec: labelled captures in the target's window, how many joined the family, and a hash
    of the joined capture list (reproducibility record)."""
    fams = spec_aux_families(spec)
    if not fams or frame.empty or f"y_{target}" not in frame:
        return {}
    tr = spec["train"]
    wd = tr["res_window_days"] if target == C.RES_TARGET else tr["window_days"]
    win = (frame[f"y_{target}"].to_numpy() >= 0) & (frame["otime"].to_numpy(float) >= fit_time - wd * 86400.0)
    caps = frame.loc[win, ["otime"] + [f"src_{f}" for f in fams]].groupby("otime").max()
    out = {}
    for fam in fams:
        joined = caps.index[caps[f"src_{fam}"].to_numpy(bool)]
        out[fam] = {"captures": int(len(caps)), "with": int(len(joined)),
                    "captures_sha256": S.canonical_sha256([S.iso(float(t)) for t in joined])}
    return out


def fit_stamp(t: float) -> str:
    return S.iso_s(t).replace("-", "").replace(":", "")


def refit_all(paths: S.Paths, reg: dict, fit_time: float, now: float, models: dict[str, dict] | None = None,
              write: bool = True, frames: dict | None = None) -> dict:
    """Fit every (active) model x target on data available before ``fit_time``. Returns {model_id: {target: art}}
    plus a summary; with ``write`` the artifacts and a write-once ``fit.json`` are stored per model."""
    models = models if models is not None else SP.active_models(reg)
    index = S.load_index(paths)
    t0 = time.time()
    if frames is None:
        dir_max = max(s["train"]["max_rows"] for s in models.values())
        dir_win = max(s["train"]["window_days"] for s in models.values())
        res_win = max(s["train"]["res_window_days"] for s in models.values())
        res = L.load_resolutions(paths)
        frames = {"dir": direction_frame(paths, index, fit_time, dir_win, dir_max, now),
                  "res": resolution_frame(paths, index, res, fit_time, res_win, dir_max, now)}
    t_frames = time.time() - t0
    arts: dict[str, dict] = {}
    summary = {"fit_time": S.iso(fit_time), "frame_rows": {k: int(len(v)) for k, v in frames.items()},
               "frame_s": round(t_frames, 1), "models": {}}
    for mid, spec in models.items():
        arts[mid] = {}
        rec = {"spec_sha256": spec["_sha256"], "targets": {}}
        for target in spec["targets"]:
            fr = frames["res" if target == C.RES_TARGET else "dir"]
            t1 = time.time()
            if fr.empty or f"y_{target}" not in fr:
                rec["targets"][target] = {"status": "no_data"}
                continue
            cov = aux_coverage(fr, spec, target, fit_time)
            if cov and spec["train"].get("require_full_coverage") and any(c["with"] < c["captures"] for c in cov.values()):
                # comparability with the champion: an aux challenger trains only once every capture of its window
                # has the family, so it never learns from a different (shorter, more recent) row set
                rec["targets"][target] = {"status": "insufficient_coverage", "aux_coverage": cov}
                continue
            sub = select_rows(fr, spec, target, fit_time)
            n_days = len(np.unique(np.floor(sub["otime"].to_numpy(float) / 86400.0))) if len(sub) else 0
            if len(sub) < spec["train"]["min_rows"] or n_days < spec["train"].get("min_days", 1):
                rec["targets"][target] = {"status": "insufficient", "rows": int(len(sub)), "days": int(n_days)}
                continue
            k = 2 if target == C.RES_TARGET else 3
            y = sub[f"y_{target}"].to_numpy(np.int64)
            try:
                art = learners.fit(spec, sub, y, sub["otime"].to_numpy(float), sub[f"lt_{target}"].to_numpy(float), k)
            except Exception as exc:  # noqa: BLE001 - one failed fit never stops the others
                rec["targets"][target] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:300],
                                          "trace": traceback.format_exc().splitlines()[-1][:200]}
                continue
            art.update({"model_id": mid, "target": target, "spec_sha256": spec["_sha256"], "fit_time": S.iso(fit_time),
                        "n_train": int(len(sub)), "train_days": int(n_days),
                        "otime_min": S.iso(float(sub["otime"].min())), "otime_max": S.iso(float(sub["otime"].max())),
                        "label_time_max": S.iso(float(np.nanmax(sub[f"lt_{target}"].to_numpy(float)))),
                        "class_counts": np.bincount(y, minlength=k).tolist()})
            if cov:
                art["aux_coverage"] = cov
            arts[mid][target] = art
            rec["targets"][target] = {"status": "ok", "rows": int(len(sub)), "days": int(n_days),
                                      "seconds": round(time.time() - t1, 1), **({"aux_coverage": cov} if cov else {})}
        summary["models"][mid] = rec
        if write and arts[mid]:
            write_fit(paths, spec, fit_time, arts[mid], rec)
    summary["seconds"] = round(time.time() - t0, 1)
    summary["peak_rss_mb"] = S.peak_rss_mb()
    return {"arts": arts, "summary": summary}


def write_fit(paths: S.Paths, spec: dict, fit_time: float, arts: dict, rec: dict) -> str:
    stamp = fit_stamp(fit_time)
    d = paths.sub("models", spec["model_id"], stamp)
    shas = {}
    for target, art in arts.items():
        data = learners.dumps(art)
        S.write_once_bytes(d / f"{target}.json", data)
        shas[target] = S.sha256_file(d / f"{target}.json")
    fit = {"fit_id": f"{spec['model_id']}@{stamp}", "model_id": spec["model_id"], "spec_sha256": spec["_sha256"],
           "fit_time": S.iso(fit_time), "fit_time_epoch": fit_time, "targets": rec["targets"], "artifact_sha256": shas,
           "engine_version": C.ENGINE_VERSION, "features_version": C.FEATURES_VERSION, "code_commit": S.git_commit(),
           "written_utc": S.iso(S.now_ts())}
    S.write_once_json(d / "fit.json", fit)  # written last: its presence marks a complete fit
    S.append_log(paths, "fits", [fit])
    return fit["fit_id"]


def list_fits(paths: S.Paths, model_id: str) -> list[dict]:
    """Complete fits of a model (``fit.json`` present), oldest first."""
    import json

    d = paths.sub("models", model_id)
    out = []
    for fp in d.glob("*/fit.json") if d.exists() else []:
        try:
            fit = json.loads(fp.read_text())
        except (OSError, ValueError):
            continue
        fit["_dir"] = str(fp.parent)
        out.append(fit)
    return sorted(out, key=lambda f: f["fit_time_epoch"])


def pick_fit(fits: list[dict], before: float) -> dict | None:
    """The newest fit with fit_time <= ``before`` (strictly no later data than the prediction origin)."""
    best = None
    for f in fits:
        if f["fit_time_epoch"] <= before:
            best = f
    return best


def latest_fit(paths: S.Paths, model_id: str, before: float) -> dict | None:
    return pick_fit(list_fits(paths, model_id), before)


def load_artifacts(fit: dict) -> dict[str, dict]:
    import json
    from pathlib import Path

    out = {}
    for target, sha in fit["artifact_sha256"].items():
        p = Path(fit["_dir"]) / f"{target}.json"
        if S.sha256_file(p) != sha:
            raise RuntimeError(f"artifact sha mismatch {p}")
        out[target] = json.loads(p.read_text())
    return out
