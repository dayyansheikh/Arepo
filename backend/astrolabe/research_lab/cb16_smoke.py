# ruff: noqa: E501
"""CB16 smoke orchestrator (docs/research_lab/CREATIVE_BATCH_16.md CB16-SM): counts only, write-once, NO network. Belongs to rules part ``common``.

One smoke job (q0381) covers both parts: ``A`` (Q and U: pins, refusals, forbidden fields, grain parser, monitor-gap detector, silence standardiser, the CB13 reproduction on raw files) and
``K`` (input pins, exact file counts 148,384 / 326,380 / 958, no outcome field parsed, the topic rule edges). A family module contributes its checks through ``SMOKE_NEEDS`` (the criteria
its downstream jobs require) and ``smoke_offline(ctx)``. A failed criterion makes the dependent part terminal (A: Q1 and U1 counted once each; K: a descriptive line).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import cb8_common as cm
from . import cb16_common as c16

Refused = cm.Refused
SMOKE_PARTS = ("A", "K")


def collect_checks(parts: tuple[str, ...], ctx: dict) -> tuple[dict, dict]:
    """(criteria, detail) over the requested parts. Offline checks only: the smoke never touches the network."""
    crit: dict[str, bool] = {}
    detail: dict[str, dict] = {}
    for part in parts:
        if part not in SMOKE_PARTS:
            raise Refused(f"smoke part {part!r}: one of {SMOKE_PARTS}")
        mods = c16.family_modules(part)
        if not mods:
            raise Refused(f"smoke part {part!r} has no module yet")
        for mod in mods:
            fn = getattr(mod, "smoke_offline", None)
            if fn is None:
                continue
            res = dict(fn(ctx))
            for k, v in res.items():
                crit[k] = bool(v.get("pass"))
            detail.update(res)
    return crit, detail


def family_needs(part: str) -> tuple[str, ...]:
    for mod in c16.family_modules(part):
        needs = getattr(mod, "SMOKE_NEEDS", None)
        if needs:
            return tuple(needs)
    raise Refused(f"part {part!r} has no module yet")


def smoke_failures(path, need: tuple[str, ...]) -> list[str]:
    """Unmet smoke criteria (empty = all met). A missing or foreign-version smoke file is a refusal; a criterion the file does not cover is unmet."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found (the smoke job first)")
    doc = json.loads(p.read_text())
    if doc.get("smoke_version") != c16.SMOKE_VERSION:
        raise Refused(f"smoke version {doc.get('smoke_version')} != {c16.SMOKE_VERSION} in {p}")
    crit = doc.get("criteria") or {}
    return [k for k in need if not crit.get(k)]


def declared() -> dict:
    return {"version": c16.SMOKE_VERSION, "parts": list(SMOKE_PARTS), "network": False, "write_once": True, "counts_only": True,
            "design": "family modules contribute SMOKE_NEEDS / smoke_offline; the orchestrator is family-agnostic",
            "consequence": "a failed criterion makes the dependent part not testable (source): Q1 and U1 counted once each; K a descriptive line; no rule is re-fitted"}
