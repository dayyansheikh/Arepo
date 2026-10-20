# ruff: noqa: E501
"""Frozen model specs, the registry, the champion history and the embargo check.

A spec is a JSON file in ``specs/``; its identity is ``spec_sha256`` = sha256 of the canonical JSON (sorted keys, no
whitespace). ``specs/registry.json`` pins every model's sha; loading refuses any mismatch, so a spec can never change
under the same id (a change is a new ``model_id`` / ``version``). Champion changes are appended to
``champion/history.jsonl`` on the host (append-only); the initial champion comes from the registry.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config as C
from . import store as S
from .features import FAMILIES

LEARNERS = ("logreg", "lgbm")
DERIVED = ("base", "tte")
REQUIRED = ("model_id", "version", "features_version", "learner", "families", "derived", "isolates", "broad",
            "targets", "train", "params", "description")


class SpecError(ValueError):
    pass


def spec_sha256(spec: dict) -> str:
    return S.canonical_sha256({k: v for k, v in spec.items() if not k.startswith("_")})


def validate(spec: dict) -> None:
    miss = [k for k in REQUIRED if k not in spec]
    if miss:
        raise SpecError(f"{spec.get('model_id')}: missing {miss}")
    if spec["learner"] not in LEARNERS:
        raise SpecError(f"{spec['model_id']}: learner {spec['learner']!r}")
    bad = [f for f in spec["families"] if f not in FAMILIES]
    if bad or not {"market_state", "momentum"} <= set(spec["families"]):
        raise SpecError(f"{spec['model_id']}: families {spec['families']} (must include market_state + momentum)")
    if any(d not in DERIVED for d in spec["derived"]) or "base" not in spec["derived"]:
        raise SpecError(f"{spec['model_id']}: derived {spec['derived']}")
    if any(t not in C.TARGETS for t in spec["targets"]):
        raise SpecError(f"{spec['model_id']}: targets {spec['targets']}")
    if spec["features_version"] != C.FEATURES_VERSION:
        raise SpecError(f"{spec['model_id']}: features_version {spec['features_version']} != {C.FEATURES_VERSION}")
    extra = (set(spec["families"]) - {"market_state", "momentum"}) | (set(spec["derived"]) - {"base"})
    if not spec["broad"] and not extra <= set(spec["isolates"]):
        raise SpecError(f"{spec['model_id']}: isolates {spec['isolates']} must list every added family/derived set {sorted(extra)}")
    tr = spec["train"]
    for k in ("window_days", "res_window_days", "max_rows", "min_rows", "require_sources"):
        if k not in tr:
            raise SpecError(f"{spec['model_id']}: train.{k} missing")


def load_registry(spec_dir: Path = C.SPEC_DIR) -> dict:
    reg = json.loads((Path(spec_dir) / "registry.json").read_text())
    models = {}
    for m in reg["models"]:
        spec = json.loads((Path(spec_dir) / m["file"]).read_text())
        validate(spec)
        sha = spec_sha256(spec)
        if sha != m["spec_sha256"]:
            raise SpecError(f"{m['model_id']}: spec sha256 {sha} != pinned {m['spec_sha256']}")
        if spec["model_id"] != m["model_id"]:
            raise SpecError(f"{m['file']}: model_id {spec['model_id']} != registry {m['model_id']}")
        spec["_sha256"] = sha
        spec["_status"] = m["status"]
        spec["_added_utc"] = m.get("added_utc")
        models[m["model_id"]] = spec
    if reg["initial_champion"] not in models:
        raise SpecError("initial_champion not in registry")
    return {"initial_champion": reg["initial_champion"], "models": models, "rule": reg.get("promotion_rule")}


def active_models(reg: dict) -> dict[str, dict]:
    return {k: v for k, v in reg["models"].items() if v["_status"] == "active"}


def champion_history(paths: S.Paths) -> list[dict]:
    p = paths.sub("champion", "history.jsonl")
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def current_champion(paths: S.Paths, reg: dict) -> str:
    hist = champion_history(paths)
    for h in reversed(hist):
        if h.get("champion") in reg["models"]:
            return h["champion"]
    return reg["initial_champion"]


def append_champion(paths: S.Paths, row: dict) -> None:
    p = paths.sub("champion", "history.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    import os
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(S.clean_json(row), sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def embargo_of(spec: dict, now: float, embargo=C.EMBARGO) -> dict | None:
    """The latest active embargo matching a token the spec isolates (None for broad specs and the champion set)."""
    if spec.get("broad"):
        return None
    hits = [e for e in embargo if e["token"] in set(spec.get("isolates") or []) and now < S.epoch(e["until"])]
    if not hits:
        return None
    last = max(hits, key=lambda e: S.epoch(e["until"]))
    return {"until": last["until"], "tests": sorted({t for e in hits for t in e["tests"]}),
            "tokens": sorted({e["token"] for e in hits})}
