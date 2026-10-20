# ruff: noqa: E501
"""Prospective predictions: on each new capture every active model writes, write-once, its probabilities for every
eligible market (``predictions/<capture>/<model_id>.parquet``), using the newest fit made at or before the capture's
start. Rows are aligned with ``features/<capture>.parquet`` (same order; its sha256 is in the metadata). The receipt
time is the ``written_utc`` of the ``predictions`` log line appended after the file is in place; the scorer treats a
prediction as valid for a target only if that time precedes the target capture's slot (direction) or the market's
close (resolution). Embargoed models still write predictions (their scores are withheld; see scoring)."""

from __future__ import annotations

import time
from collections import Counter

import numpy as np
import pandas as pd

from . import config as C
from . import labels as L
from . import learners
from . import specs as SP
from . import store as S
from . import training as T
from .features import ALL_FEATURES, KEY_COLUMNS


def quantise(p: np.ndarray) -> np.ndarray:
    return np.floor(np.clip(p, 0.0, 1.0) * C.Q).astype(np.uint16)


def dequantise_dir(dn: np.ndarray, up: np.ndarray) -> np.ndarray:
    """(n, 3) probabilities [down, flat, up] from stored uint16 down/up (flat = remainder), clipped and renormalised."""
    pdn, pup = dn.astype(np.float64) / C.Q, up.astype(np.float64) / C.Q
    p = np.column_stack([pdn, 1.0 - pdn - pup, pup])
    p = np.clip(p, C.P_CLIP, 1.0)
    return p / p.sum(axis=1, keepdims=True)


def dequantise_bin(q: np.ndarray) -> np.ndarray:
    return np.clip(q.astype(np.float64) / C.Q, C.P_CLIP, 1 - C.P_CLIP)


def predict_frame(spec: dict, arts: dict[str, dict], feats: pd.DataFrame, elig: np.ndarray) -> pd.DataFrame:
    out = {"elig": elig}
    for t in C.DIR_TARGETS:
        dn = np.zeros(len(feats), np.uint16)
        up = np.zeros(len(feats), np.uint16)
        bit = C.ELIG_BITS[t]
        m = (elig & bit) > 0
        if t in arts and m.any():
            p = learners.predict(spec, arts[t], feats[m])
            dn[m], up[m] = quantise(p[:, 0]), quantise(p[:, 2])
        out[f"{t}_dn"], out[f"{t}_up"] = dn, up
    q = np.zeros(len(feats), np.uint16)
    m = (elig & C.ELIG_BITS[C.RES_TARGET]) > 0
    if C.RES_TARGET in arts and m.any():
        q[m] = quantise(learners.predict(spec, arts[C.RES_TARGET], feats[m])[:, 1])
    out[f"{C.RES_TARGET}_yes"] = q
    return pd.DataFrame(out)


def run_predict(paths: S.Paths, reg: dict, now: float | None = None, max_items: int = 4) -> dict:
    now = S.now_ts() if now is None else now
    index = S.load_index(paths)
    models = SP.active_models(reg)
    fit_cache: dict[str, tuple[str, dict]] = {}
    fits = {mid: T.list_fits(paths, mid) for mid in models}
    written, skipped = [], []
    todo = []
    for slot, m in sorted(index.items(), reverse=True):  # newest first: its 2 h target is the most urgent
        cid = m["capture_id"]
        if now >= S.slot_time(slot + L.horizon_slots(max(C.HORIZONS_H))):
            continue  # every direction target has started: a prediction now could not be prospective
        start = S.epoch(m["started_utc"])
        missing = []
        for mid in models:
            if paths.predictions(cid, mid).exists():
                continue
            fit = T.pick_fit(fits[mid], start)
            if fit is None:
                skipped.append({"capture_id": cid, "model_id": mid, "reason": "no_fit"})
            else:
                missing.append((mid, fit))
        if missing:
            todo.append((slot, m, missing))
    for slot, m, missing in todo[:max_items]:
        cid = m["capture_id"]
        start = S.epoch(m["started_utc"])
        fp = paths.features(cid)
        feats = S.read_parquet(fp, KEY_COLUMNS + ALL_FEATURES)
        feats_sha = S.sha256_file(fp)
        elig = L.elig_mask(feats, slot, start)
        for mid, fit in missing:
            spec = models[mid]
            t0 = time.time()
            if mid not in fit_cache or fit_cache[mid][0] != fit["fit_id"]:
                fit_cache[mid] = (fit["fit_id"], T.load_artifacts(fit))
            arts = fit_cache[mid][1]
            pf = predict_frame(spec, arts, feats, elig)
            md = {"capture_id": cid, "slot": slot, "model_id": mid, "spec_sha256": spec["_sha256"], "fit_id": fit["fit_id"],
                  "features_sha256": feats_sha, "n_rows": int(len(pf)), "targets": sorted(arts),
                  "created_utc": S.iso(S.now_ts()), "engine_version": C.ENGINE_VERSION}
            path = paths.predictions(cid, mid)
            if not S.write_once_parquet(path, pf, md):
                skipped.append({"capture_id": cid, "model_id": mid, "reason": "exists"})
                continue
            t_written = S.now_ts()
            emb = SP.embargo_of(spec, t_written)
            line = {"capture_id": cid, "slot": slot, "model_id": mid, "spec_sha256": spec["_sha256"],
                    "fit_id": fit["fit_id"], "sha256": S.sha256_file(path), "n_rows": int(len(pf)),
                    "targets": sorted(arts), "written_utc": S.iso(t_written), "embargoed_until": emb and emb["until"],
                    "seconds": round(time.time() - t0, 2)}
            S.append_log(paths, "predictions", [line], at=t_written)
            written.append({k: line[k] for k in ("capture_id", "model_id", "fit_id", "n_rows", "seconds")})
    return {"written": written, "skipped": dict(Counter(x["reason"] for x in skipped)), "pending_captures": max(0, len(todo) - max_items),
            "peak_rss_mb": S.peak_rss_mb()}


def prediction_log(paths: S.Paths, since: float | None = None) -> dict[tuple[str, str], dict]:
    """(capture_id, model_id) -> first valid log line (the receipt time of the write-once file)."""
    out: dict[tuple[str, str], dict] = {}
    for r in S.read_logs(paths, "predictions", since):
        key = (r.get("capture_id"), r.get("model_id"))
        if key not in out:
            out[key] = r
    return out
