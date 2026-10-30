# ruff: noqa: E501
"""Fixed-weight linear pools of other models' write-once predictions (DESIGN_V1 §47, learner ``ens_pool``).

A pool has no fit and no training rows. For a capture it reads its members' stored predictions of that same capture
(same features file, same eligibility mask), dequantises them exactly as the scorer does, averages them with the
spec's fixed weights in probability space, and writes its own write-once file; its receipt time is its own log line,
which always follows every member's file. A target is pooled only if every member's file carries it. A pool never
reads labels, scores, other captures or embargoed members (``specs.embargo_of`` gives a pool its members' embargo)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import store as S

LEARNER = "ens_pool"


def is_pool(spec: dict) -> bool:
    return spec.get("learner") == LEARNER


def members(spec: dict) -> list[str]:
    return list(spec["params"]["members"])


def validate_pool(spec: dict) -> str | None:
    """None if the pool's own fields are well formed (member existence is checked against the registry)."""
    p = spec.get("params") or {}
    mem, w = p.get("members"), p.get("weights")
    if not isinstance(mem, list) or len(mem) < 2 or len(set(mem)) != len(mem):
        return f"members {mem!r} (need >= 2 distinct model ids)"
    if not isinstance(w, list) or len(w) != len(mem) or any(not isinstance(x, (int, float)) or x <= 0 for x in w):
        return f"weights {w!r} (one positive weight per member)"
    pins = p.get("member_sha256")
    if not isinstance(pins, dict) or set(pins) != set(mem):
        return "member_sha256 must pin every member's spec_sha256"
    if abs(sum(w) - 1.0) > 1e-9:
        return f"weights sum {sum(w)} != 1"
    if p.get("space") != "probability":
        return f"space {p.get('space')!r} (only 'probability')"
    if spec["families"] or spec["derived"] or spec["isolates"] or not spec["broad"]:
        return "a pool declares no families, derived sets or isolates and is broad"
    if spec["train"] != {"refit": "none"}:
        return "train must be {'refit': 'none'}"
    return None


def pool_frame(paths: S.Paths, cid: str, spec: dict, feats_sha: str, elig: np.ndarray) -> tuple[pd.DataFrame, dict] | str:
    """(frame, provenance) or the reason the pool cannot be written yet (``members_pending`` / ``member_mismatch``)."""
    from . import predict as P

    mem, w = members(spec), [float(x) for x in spec["params"]["weights"]]
    frames, prov, targets = [], {}, set(spec["targets"])
    for mid in mem:
        fp = paths.predictions(cid, mid)
        if not fp.exists():
            return "members_pending"
        md = S.parquet_meta(fp)
        pf = S.read_parquet(fp)
        if md.get("features_sha256") != feats_sha or len(pf) != len(elig) or not np.array_equal(pf["elig"].to_numpy(), elig):
            return "member_mismatch"
        frames.append(pf)
        prov[mid] = {"fit_id": md.get("fit_id"), "sha256": S.sha256_file(fp)}
        targets &= set(md.get("targets") or [])
    out = {"elig": elig}
    for t in C.DIR_TARGETS:
        dn = np.zeros(len(elig), np.uint16)
        up = np.zeros(len(elig), np.uint16)
        m = (elig & C.ELIG_BITS[t]) > 0
        if t in targets and m.any():
            p = np.zeros((int(m.sum()), 3))
            for wi, pf in zip(w, frames, strict=True):
                p += wi * P.dequantise_dir(pf[f"{t}_dn"].to_numpy()[m], pf[f"{t}_up"].to_numpy()[m])
            dn[m], up[m] = P.quantise(p[:, 0]), P.quantise(p[:, 2])
        out[f"{t}_dn"], out[f"{t}_up"] = dn, up
    q = np.zeros(len(elig), np.uint16)
    t = C.RES_TARGET
    m = (elig & C.ELIG_BITS[t]) > 0
    if t in targets and m.any():
        pr = np.zeros(int(m.sum()))
        for wi, pf in zip(w, frames, strict=True):
            pr += wi * P.dequantise_bin(pf[f"{t}_yes"].to_numpy()[m])
        q[m] = P.quantise(pr)
    out[f"{t}_yes"] = q
    tag = S.canonical_sha256({k: prov[k] for k in mem})[:12]
    return pd.DataFrame(out), {"members": prov, "targets": sorted(targets), "fit_id": f"{spec['model_id']}@pool-{tag}"}
