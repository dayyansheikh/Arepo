# ruff: noqa: E501
"""CB14 smoke orchestrator (docs/research_lab/CREATIVE_BATCH_14.md CB14-SM): counts only, write-once. Belongs to rules part ``common``.

Two smokes, one per family: ``smoke --part W`` (q0300, ``net`` lane, <= 30 requests) and ``smoke --part S`` (q0301, ``net`` lane, <= 30 requests). A family module contributes its checks
through three names it defines (hashed with that family's part): ``SMOKE_NEEDS`` (the criteria that family's downstream jobs require), ``smoke_offline(ctx)`` (fixtures, no network)
and ``smoke_online(lim, ctx)``. Each result file carries ``part``; ``smoke_failures`` merges nothing across parts. Only engineering criteria and counts are recorded: no price, outcome,
volume or wallet of any market, and no transcript text.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import cb8_common as cm
from . import cb14_common as c14

Refused = cm.Refused
SMOKE_PARTS = ("W", "S")
MAX_REQUESTS = {"W": 30, "S": 30}


def collect_checks(part: str, ctx: dict, lim=None) -> tuple[dict, dict]:
    """(criteria, detail). Offline checks always run; online checks only if ``lim`` is given."""
    if part not in SMOKE_PARTS:
        raise Refused(f"smoke part {part!r}: one of {SMOKE_PARTS}")
    mods = c14.family_modules(part)
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
    for mod in c14.family_modules(part):
        return tuple(mod.SMOKE_NEEDS)
    raise Refused(f"part {part!r} has no module yet")


def smoke_failures(path, need: tuple[str, ...], part: str | None = None) -> list[str]:
    """Unmet smoke criteria (empty = all met). A missing, foreign-version or wrong-part smoke file is a refusal; a criterion the file does not cover is unmet."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found (the smoke job first)")
    doc = json.loads(p.read_text())
    if doc.get("smoke_version") != c14.SMOKE_VERSION:
        raise Refused(f"smoke version {doc.get('smoke_version')} != {c14.SMOKE_VERSION} in {p}")
    if part is not None and doc.get("part") != part:
        raise Refused(f"smoke file {p} is for part {doc.get('part')!r}, not {part!r}")
    crit = doc.get("criteria") or {}
    return [k for k in need if not crit.get(k)]


def declared() -> dict:
    return {"version": c14.SMOKE_VERSION, "max_requests": MAX_REQUESTS, "write_once": True, "counts_only": True,
            "design": "family modules contribute SMOKE_NEEDS / smoke_offline / smoke_online; the orchestrator is family-agnostic",
            "consequence": "a failed criterion stalls the dependent family (not testable (source), counted); no rule is re-fitted"}
