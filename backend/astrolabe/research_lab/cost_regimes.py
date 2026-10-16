# ruff: noqa: E501
"""Cost register reader/writer for the CB4 measurements (docs/research_lab/CREATIVE_BATCH_4.md section 2.9, rules R0-R4).

``model_specs/cost_regimes_v1.json`` is written once by ``cb4_measure.commit_register`` (q0089) and read through
:func:`cost_regime`. R0 (one direction only) is enforced here in code:

* every returned fee rate is at least the CB1 section 2.1 conservative rate (``cb1_history.fee_rate``);
* every returned half-spread is at least the CB1 band table value (``cb1_history.half_spread``);
* ``a_as_cents`` is never negative;
* a register that would lower any cost is refused at write time and clamped at read time;
* the CH52 band map is NOT part of :func:`cost_regime`; :func:`planning_band_map` returns it only to a consumer whose
  declared data window does not overlap the pmxt window 2026-04-13..2026-08-10 and that does not use it to select
  categories, bands, events or thresholds.

An absent register gives the CB1 defaults, flagged ``register_status = "absent_defaults"``. This module reads no data
and never edits a frozen test.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, date, datetime
from pathlib import Path

from . import cb1_history

VERSION = "cost-regimes-v1"
REGISTER_PATH = Path(__file__).resolve().parent / "model_specs" / "cost_regimes_v1.json"
LABEL = "unreplicated measurement"

FEE_ERAS = {"sports": "2026-02-18", "other": "2026-03-30", "tier_launch": "2026-05-28"}
EXCLUDED_REGIME_DATES = {"clob_v2_switch": "2026-04-28", "pmxt_gap": ["2026-06-12", "2026-06-17"], "tick_change": "2026-07-02", "fee_step": "2026-07-10"}
ERA_BUFFER_D = 7  # R1: post-rollout data starts 7 days after each rollout date
PMXT_WINDOW = ("2026-04-13", "2026-08-10")
ERA_RULE_POOLED, ERA_RULE_POST = "pooled_allowed", "post_rollout_or_interaction"
MEASUREMENTS = ("N1", "N2", "E1", "E2")
# what the band map may never be used to choose (R0 / challenger item 13)
FORBIDDEN_SELECTS = ("category", "categories", "band", "bands", "event", "events", "threshold", "thresholds", "window", "windows")


class CostRegimeError(RuntimeError):
    """A register or consumer declaration that would break R0."""


def _day(d) -> date:
    if isinstance(d, datetime):
        return d.astimezone(UTC).date() if d.tzinfo else d.date()
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(str(d).replace("Z", "+00:00")).date()


def _nonneg(x) -> tuple[float, bool]:
    """(value >= 0, ok). A missing, non-numeric, negative or non-finite adjustment is read as 0 (R0: never lowers a cost)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0, x is None
    if not math.isfinite(v) or v < 0:
        return 0.0, False
    return v, True


def load_register(path: Path | None = None) -> dict | None:
    p = Path(path) if path is not None else REGISTER_PATH
    if not p.exists():
        return None
    reg = json.loads(p.read_text())
    if reg.get("version") != VERSION:
        raise CostRegimeError(f"{p}: unknown register version {reg.get('version')!r}")
    return reg


def rollout_date(fee_category) -> date:
    return _day(FEE_ERAS["sports"] if cb1_history.is_sports(fee_category) else FEE_ERAS["other"])


def era_window_start(fee_category) -> date:
    """R1: first date of post-rollout data for the category (rollout + 7 days)."""
    from datetime import timedelta

    return rollout_date(fee_category) + timedelta(days=ERA_BUFFER_D)


def cost_regime(on, fee_category, price: float = 0.5, register_path: Path | None = None) -> dict:
    """Cost terms for a date and a fee category. Never below the CB1 section 2.1 defaults (R0); no band map.

    ``fee_rate``: taker rate per ``r*a*(1-a)``; ``half_spread``: half-spread at ``price`` (probability units);
    ``a_as_cents``: the R2 maker adverse-selection term for fills BEFORE the category's rollout date (else 0);
    ``post_rollout`` / ``era_rule``: the R1 inputs."""
    d = _day(on)
    fee_default = float(cb1_history.fee_rate(fee_category))
    hs_default = float(cb1_history.half_spread(float(price)))
    reg = load_register(register_path)
    flags: list[str] = []
    fee_add = hs_add = a_as = 0.0
    era_rule = ERA_RULE_POOLED
    status = "absent_defaults"
    if reg is not None:
        status = "committed"
        fee_add, ok1 = _nonneg(reg.get("fee_rate_add", 0.0))
        hs_add, ok2 = _nonneg(reg.get("half_spread_add", 0.0))
        a_as, ok3 = _nonneg(reg.get("a_AS_cents", 0.0))
        if not (ok1 and ok2 and ok3):
            flags.append("register_adjustment_clamped_to_zero")
        era_rule = reg.get("era_rule") if reg.get("era_rule") in (ERA_RULE_POOLED, ERA_RULE_POST) else ERA_RULE_POOLED
    ro = rollout_date(fee_category)
    out = {
        "date": d.isoformat(), "fee_category": str(fee_category), "price": float(price),
        "fee_rate": max(fee_default, fee_default + fee_add),
        "half_spread": max(hs_default, hs_default + hs_add),
        "a_as_cents": a_as if d < ro else 0.0,
        "rollout_date": ro.isoformat(), "post_rollout": bool(d >= era_window_start(fee_category)),
        "era_rule": era_rule, "register_status": status, "flags": flags,
        "defaults": {"fee_rate": fee_default, "half_spread": hs_default}, "label": LABEL,
    }
    assert "band_map" not in out
    return out


def _window(decl: dict) -> tuple[date, date] | None:
    w = decl.get("data_window")
    if not (isinstance(w, list | tuple) and len(w) == 2):
        return None
    return _day(w[0]), _day(w[1])


def planning_band_map(consumer_declaration: dict, register_path: Path | None = None) -> dict:
    """The CH52 residual band map, for power planning only (R0, R3). Refused when the consumer's declared data window
    overlaps the pmxt window 2026-04-13..2026-08-10 (or is missing), when it is not declared ``planning_only``, or when
    it would use the map to select categories, bands, events or thresholds."""
    decl = consumer_declaration if isinstance(consumer_declaration, dict) else {}
    win = _window(decl)
    if win is None:
        raise CostRegimeError("planning_band_map refused: the consumer declares no data_window")
    lo, hi = _day(PMXT_WINDOW[0]), _day(PMXT_WINDOW[1])
    if win[0] <= hi and win[1] >= lo:
        raise CostRegimeError(f"planning_band_map refused: data window {win[0]}..{win[1]} overlaps the pmxt window {lo}..{hi} the map was computed on")
    if decl.get("planning_only") is not True:
        raise CostRegimeError("planning_band_map refused: the consumer must declare planning_only = true")
    sel = decl.get("selects") or decl.get("uses_to_select") or []
    sel = [sel] if isinstance(sel, str) else list(sel)
    bad = sorted(str(x) for x in sel if str(x).lower() in FORBIDDEN_SELECTS)
    if bad:
        raise CostRegimeError(f"planning_band_map refused: the map may not select {bad}")
    reg = load_register(register_path)
    if reg is None or reg.get("band_map") is None:
        raise CostRegimeError("planning_band_map: no committed register with a band map")
    return json.loads(json.dumps(reg["band_map"]))


def validate_register(payload: dict) -> None:
    """R0 at write time: the register can only add cost terms, and family M must be complete."""
    for k in ("fee_rate_add", "half_spread_add", "a_AS_cents"):
        v = payload.get(k, 0.0)
        try:
            fv = float(v)
        except (TypeError, ValueError):
            raise CostRegimeError(f"{k} is not a number: {v!r}") from None
        if not math.isfinite(fv) or fv < 0:
            raise CostRegimeError(f"{k} = {v!r} would lower a cost (R0); refused")
    if payload.get("version") != VERSION:
        raise CostRegimeError("wrong register version")
    if payload.get("era_rule") not in (ERA_RULE_POOLED, ERA_RULE_POST):
        raise CostRegimeError("era_rule must be pooled_allowed or post_rollout_or_interaction")
    ms = payload.get("measurements") or {}
    if sorted(ms) != sorted(MEASUREMENTS):
        raise CostRegimeError(f"family M incomplete: measurements {sorted(ms)} != {sorted(MEASUREMENTS)}")
    for k, m in ms.items():
        if m.get("label") != LABEL:
            raise CostRegimeError(f"{k}: every register entry carries the label {LABEL!r}")
    if payload.get("family_M_complete") is not True:
        raise CostRegimeError("family M is not complete")


def write_register(payload: dict, path: Path | None = None) -> dict:
    """Write the register once (exclusive create) with a ``.sha256`` side file. Refuses anything R0 forbids."""
    p = Path(path) if path is not None else REGISTER_PATH
    validate_register(payload)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=1, sort_keys=True, default=float) + "\n"
    with open(p, "x", encoding="utf-8") as fh:
        fh.write(body)
    sha = hashlib.sha256(body.encode()).hexdigest()
    Path(str(p) + ".sha256").write_text(sha + "\n")
    return {"path": str(p), "sha256": sha}
