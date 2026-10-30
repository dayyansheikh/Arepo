# ruff: noqa: E501
"""CB15 smoke orchestrator (docs/research_lab/CREATIVE_BATCH_15.md CB15-SM): counts only, write-once. Belongs to rules part ``common``.

Two smokes, one per family: ``smoke --part E`` (q0343; ``net`` lane, <= 30 requests, 2-h ``net`` promotion hold before) and ``smoke --part P`` (q0348; ``net`` lane, <= 30 requests). A
family module contributes its checks through three names it defines (hashed with that family's part): ``SMOKE_NEEDS`` (the criteria that family's downstream jobs require),
``smoke_offline(ctx)`` (fixtures, no network) and ``smoke_online(lim, ctx)``. Each result file carries ``part``; ``smoke_failures`` merges nothing across parts.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import cb8_common as cm
from . import cb15_common as c15

Refused = cm.Refused
SMOKE_PARTS = ("E", "P")
MAX_REQUESTS = {"E": 30, "P": 30}


def collect_checks(part: str, ctx: dict, lim=None) -> tuple[dict, dict]:
    """(criteria, detail). Offline checks always run; online checks only if ``lim`` is given. A family's ``_requests`` entry (its request count) becomes a criterion too."""
    if part not in SMOKE_PARTS:
        raise Refused(f"smoke part {part!r}: one of {SMOKE_PARTS}")
    mods = c15.family_modules(part)
    if not mods:
        raise Refused(f"smoke part {part!r} has no module yet")
    crit: dict[str, bool] = {}
    detail: dict[str, dict] = {}
    for mod in mods:
        res = dict(mod.smoke_offline(ctx))
        if lim is not None:
            res.update(mod.smoke_online(lim, ctx))
        for k, v in res.items():
            crit[k] = bool(v.get("pass"))
        detail.update(res)
    return crit, detail


def family_needs(part: str) -> tuple[str, ...]:
    for mod in c15.family_modules(part):
        return tuple(mod.SMOKE_NEEDS)
    raise Refused(f"part {part!r} has no module yet")


def smoke_failures(path, need: tuple[str, ...], part: str | None = None) -> list[str]:
    """Unmet smoke criteria (empty = all met). A missing, foreign-version or wrong-part smoke file is a refusal; a criterion the file does not cover is unmet."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found (the smoke job first)")
    doc = json.loads(p.read_text())
    if doc.get("smoke_version") != c15.SMOKE_VERSION:
        raise Refused(f"smoke version {doc.get('smoke_version')} != {c15.SMOKE_VERSION} in {p}")
    if part is not None and doc.get("part") != part:
        raise Refused(f"smoke file {p} is for part {doc.get('part')!r}, not {part!r}")
    crit = doc.get("criteria") or {}
    return [k for k in need if not crit.get(k)]


def declared() -> dict:
    return {"version": c15.SMOKE_VERSION, "max_requests": MAX_REQUESTS, "write_once": True, "counts_only": True,
            "design": "family modules contribute SMOKE_NEEDS / smoke_offline / smoke_online; the orchestrator is family-agnostic",
            "consequence": "a failed criterion makes the dependent family not testable (source), counted once; no rule is re-fitted"}
