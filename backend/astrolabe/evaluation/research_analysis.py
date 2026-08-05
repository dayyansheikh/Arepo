"""Measurement engine: score every predictor on the same frozen observations (prompt sections 6-9,
14). Pure and deterministic; the service layer converts DB rows into these structures.

Two separate objectives are kept apart (prompt section 7): forward repricing (did the midpoint move
in the predicted direction over 1h/6h/24h/7d, before and after execution costs) and final resolution
(did the market resolve as predicted). A directional call is never treated as a probability.
"""
from __future__ import annotations

import statistics as _stats
from dataclasses import dataclass

from .execution import evaluate_execution
from .replay_stats import classify_directional, sample_verdict, wilson_interval
from .research_constants import MIN_PROSPECTIVE_SAMPLE
from .research_predictors import ABLATIONS, BASELINES, EntryView, agreement_rate


@dataclass(frozen=True)
class HorizonObs:
    """One entry's realised microstructure at a horizon (raw, not folded into a direction)."""

    entry: EntryView
    entry_midpoint: float | None
    entry_spread: float | None
    entry_depth: float | None
    forward_midpoint: float | None
    forward_spread: float | None
    forward_depth: float | None

    @property
    def raw_move(self) -> float | None:
        if self.entry_midpoint is None or self.forward_midpoint is None:
            return None
        return self.forward_midpoint - self.entry_midpoint


def _executable_move(direction: str | None, o: HorizonObs) -> float | None:
    r = evaluate_execution(
        direction=direction, entry_midpoint=o.entry_midpoint, forward_midpoint=o.forward_midpoint,
        entry_spread=o.entry_spread, entry_depth=o.entry_depth,
        forward_spread=o.forward_spread, forward_depth=o.forward_depth,
    )
    return r.executable_move


def score_predictor(direction_of, obs: list[HorizonObs]) -> dict:
    """Score one predictor (given a direction function) over a set of horizon observations."""
    correct = incorrect = flat = 0
    mid_moves: list[float] = []
    exe_moves: list[float] = []
    dirs: list[str | None] = []
    for o in obs:
        d = direction_of(o.entry)
        dirs.append(d)
        outcome = classify_directional(d, o.raw_move)
        if outcome == "correct":
            correct += 1
        elif outcome == "incorrect":
            incorrect += 1
        elif outcome == "flat":
            flat += 1
        if d in ("up", "down") and o.raw_move is not None:
            sign = 1.0 if d == "up" else -1.0
            mid_moves.append(sign * o.raw_move)
            ex = _executable_move(d, o)
            if ex is not None:
                exe_moves.append(ex)
    n = correct + incorrect
    lo, hi = wilson_interval(correct, n)
    return {
        "evaluated": n, "correct": correct, "incorrect": incorrect, "flat": flat,
        "hit_rate": (correct / n) if n else None,
        "ci95": [round(lo, 3), round(hi, 3)],
        "mean_midpoint_move": round(_stats.mean(mid_moves), 4) if mid_moves else None,
        "median_midpoint_move": round(_stats.median(mid_moves), 4) if mid_moves else None,
        "mean_executable_move": round(_stats.mean(exe_moves), 4) if exe_moves else None,
        "median_executable_move": round(_stats.median(exe_moves), 4) if exe_moves else None,
        "executable_evaluated": len(exe_moves),
        "verdict": sample_verdict(n),
        "_dirs": dirs,
    }


def baseline_table(obs: list[HorizonObs]) -> dict:
    """Score every baseline (prompt section 8) on the same observations, plus the Arepo/momentum
    agreement rate (the near-self-reference diagnostic)."""
    out: dict = {}
    for key, spec in BASELINES.items():
        s = score_predictor(spec.fn, obs)
        s["name"] = spec.name
        s["inputs"] = spec.inputs
        s["note"] = spec.note
        out[key] = s
    arepo_dirs = out.get("full_arepo", {}).get("_dirs", [])
    mom_dirs = out.get("momentum", {}).get("_dirs", [])
    for s in out.values():
        s.pop("_dirs", None)
    return {
        "baselines": out,
        "arepo_momentum_agreement": agreement_rate(arepo_dirs, mom_dirs),
        "probabilistic_metrics_note": (
            "Brier score and log loss are not computed here: Arepo emits a directional call, not a "
            "calibrated probability. See the calibration status."
        ),
    }


def ablation_table(obs: list[HorizonObs]) -> dict:
    """Feature ablation (prompt section 9): each variant scored on the same observations, with the
    difference in hit rate and mean executable move versus the full model and versus momentum."""
    scored = {}
    for key, spec in ABLATIONS.items():
        s = score_predictor(spec.fn, obs)
        s["name"] = spec.name
        scored[key] = s
    full = scored.get("full_model", {})
    mom = scored.get("momentum_only", {})

    def _diff(a, b, field):
        av, bv = a.get(field), b.get(field)
        return round(av - bv, 4) if (av is not None and bv is not None) else None

    for s in scored.values():
        s["hit_rate_vs_full"] = _diff(s, full, "hit_rate")
        s["hit_rate_vs_momentum"] = _diff(s, mom, "hit_rate")
        s["executable_vs_full"] = _diff(s, full, "mean_executable_move")
        s["executable_vs_momentum"] = _diff(s, mom, "mean_executable_move")
        s.pop("_dirs", None)
    return scored


@dataclass(frozen=True)
class EdgeVerdict:
    edge_supported: bool
    message: str
    criteria: dict
    evaluable_sample: int


def edge_verdict(
    *,
    evaluable_sample: int,
    arepo: dict,
    momentum: dict,
    price_only: dict,
    implied: dict,
    all_prospective: bool,
    walk_forward_stable: bool | None,
    ablation_beats_momentum: bool | None,
    thresholds_unchanged: bool = True,
    adversarial_passed: bool | None = None,
) -> EdgeVerdict:
    """Apply the ten edge-acceptance criteria (prompt section 14). Conservative: any unmet or
    unknown criterion yields 'not supported' with the honest inconclusive message."""
    def _beats(a, b):
        return (
            a.get("hit_rate") is not None and b.get("hit_rate") is not None
            and a["hit_rate"] > b["hit_rate"]
        )
    exe = arepo.get("mean_executable_move")
    criteria = {
        "frozen_before_outcome": all_prospective,
        "meets_minimum_sample": evaluable_sample >= MIN_PROSPECTIVE_SAMPLE,
        "positive_after_costs": exe is not None and exe > 0,
        "interval_supports_positive": arepo.get("ci95", [0, 1])[0] > 0.5,
        "beats_momentum": _beats(arepo, momentum),
        "beats_price_only": _beats(arepo, price_only),
        "beats_current_implied": _beats(arepo, implied),
        "walk_forward_stable": bool(walk_forward_stable),
        "ablation_adds_value": bool(ablation_beats_momentum),
        "thresholds_unchanged": thresholds_unchanged,
        "adversarial_passed": bool(adversarial_passed),
    }
    supported = all(criteria.values())
    from .research_constants import INCONCLUSIVE_MSG, NOT_ENOUGH_EVIDENCE_MSG

    if not criteria["meets_minimum_sample"]:
        msg = NOT_ENOUGH_EVIDENCE_MSG
    elif supported:
        msg = "Edge criteria met on the current prospective sample. See the detailed table."
    else:
        msg = INCONCLUSIVE_MSG
    return EdgeVerdict(supported, msg, criteria, evaluable_sample)
