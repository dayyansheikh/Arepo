# ruff: noqa: E501
"""CB12 smoke orchestrator (docs/research_lab/CREATIVE_BATCH_12.md CB12-S, q0240): counts only, write-once, <= 60 requests.

This module is the family-agnostic part (it belongs to rules part ``common``). Every family module that exists contributes its OWN checks through three names it
defines (and that are hashed with that family's part, not with ``common``): ``SMOKE_NEEDS`` (the criteria that family's downstream jobs require),
``smoke_offline(ctx)`` (fixtures and host-file checks, no network) and ``smoke_online(lim, ctx)`` (network checks; returns a dict of ``{criterion: {"pass": bool, ...}}``).
Family E / F / O smoke checks therefore arrive with their modules and change no hash of M or X. A family whose module is absent is simply not covered by a given smoke
run (``families_covered``); its jobs refuse (``smoke_failures`` finds the criterion missing) until a later smoke covers it (``smoke --families E,F --out smoke_EF.json``).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import cb8_common as cm
from . import cb12_common as c12

Refused = cm.Refused


def collect_checks(families: tuple[str, ...], ctx: dict, lim=None) -> tuple[dict, dict]:
    """(criteria, per-family detail). Offline checks always run; online checks only if ``lim`` is given. A requested family without a module is a refusal."""
    crit: dict[str, bool] = {}
    detail: dict[str, dict] = {}
    for fam in families:
        mods = c12.family_modules(fam)
        if not mods:
            raise Refused(f"smoke family {fam!r} has no module yet (cb12_{fam.lower()}); it cannot be smoked")
        for mod in mods:
            res = dict(mod.smoke_offline(ctx))
            if lim is not None:
                res.update(mod.smoke_online(lim, ctx))
            for k, v in res.items():
                crit[k] = bool(v.get("pass"))
            detail.setdefault(fam, {}).update(res)
    return crit, detail


def family_needs(fam: str) -> tuple[str, ...]:
    for mod in c12.family_modules(fam):
        return tuple(mod.SMOKE_NEEDS)
    raise Refused(f"family {fam!r} has no module yet")


def smoke_failures(paths, need: tuple[str, ...]) -> list[str]:
    """Unmet smoke criteria (empty = all met). Criteria are merged over the smoke files (AND if a criterion appears twice). A missing, foreign-version or empty
    smoke is a refusal; a criterion that no file covers is unmet (a family not yet smoked cannot run)."""
    plist = [Path(p) for p in ([paths] if isinstance(paths, (str, Path)) else list(paths))]
    docs = []
    for p in plist:
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        if doc.get("smoke_version") != c12.SMOKE_VERSION:
            raise Refused(f"smoke version {doc.get('smoke_version')} != {c12.SMOKE_VERSION} in {p}")
        docs.append(doc)
    if not docs:
        raise Refused(f"smoke result not found in {[str(p) for p in plist]} (q0240 first)")
    merged: dict[str, bool] = {}
    for d in docs:
        for k, v in (d.get("criteria") or {}).items():
            merged[k] = merged.get(k, True) and bool(v)
    return [k for k in need if not merged.get(k)]


def declared() -> dict:
    return {"version": c12.SMOKE_VERSION, "max_requests": 60, "write_once": True, "counts_only": True,
            "design": "family modules contribute SMOKE_NEEDS / smoke_offline / smoke_online; the orchestrator is family-agnostic",
            "consequence": "a failed criterion stalls the dependent family (not testable (source), counted); no rule is re-fitted"}
