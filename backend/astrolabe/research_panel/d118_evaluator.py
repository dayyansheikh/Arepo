"""D118 acceptance evaluator: the frozen D116 evaluator with only D118's declared values changed.

``d116_evaluator.py`` is frozen and is not edited. Its gates read module-level constants (run
identity, frozen protocol and policy values, evaluator version). This module re-executes the
*same compiled code* of every ``_Evaluation`` method and of the entry functions against a copy of
the D116 module namespace in which exactly the names in ``OVERRIDES`` are replaced. Everything
else is the D116 object itself: the classification table (its sha256 must equal D116's
``D116_TABLE_SHA256``), the citation checks, the common-mode guard and ``decide_outcome``.

D118-only additions (they can only add failures, never remove one):

* E1 (frozen values): the panel declaration ``fs2-panel-declaration-v5``, the selection policy
  ``fs2-panel-selection-v4`` and plan ``fs2-panel-selection-plan-v4`` with the liquidity
  population and the ``1000`` floor.
* E2 (population): every zero-inclusion exclusion reason is in ``ALLOWED_EXCLUSION_REASONS``;
  ``population_exclusion_counts`` equals the exclusion list; every eligible selection stratum has
  liquidity band 1, 2 or 3 (liquidity >= 1000). Missing or unknown values fail closed.

Pure and deterministic: no network, no clock, no writes.
"""

import copy
import types
from collections import Counter

from . import d116_evaluator as _d116
from .panel_declaration import LIQUIDITY_FLOOR, LIQUIDITY_POPULATION
from .panel_declaration import LIQUIDITY_VERSION as DECLARATION_SCHEMA
from .panel_selection import LIQUIDITY_BELOW, LIQUIDITY_UNKNOWN
from .panel_selection import LIQUIDITY_VERSION as SELECTION_SCHEMA

EVALUATOR_VERSION = "d118-evaluator-v1"
# The D116 classification table is reused unchanged; D118 refuses to run if it ever differs.
D116_TABLE_SHA256 = "6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4"
CLASSIFICATION_TABLE = _d116.CLASSIFICATION_TABLE
TABLE_SHA256 = _d116.TABLE_SHA256
if TABLE_SHA256 != D116_TABLE_SHA256:
    raise ImportError("D116 classification table changed; D118 evaluator refuses to load")

decide_outcome = _d116.decide_outcome
common_mode_flags = _d116.common_mode_flags

D118_PROTOCOL = {
    **_d116.D116_PROTOCOL,
    "scheduled_slots": 16,
    "triggered_slots": 16,
    "scheduled_per_stratum": 4,
    "triggered_per_stratum": 4,
}
RUN_NAME = "d118_control_pairing_1"
FROZEN_PANEL_NAME = "fs2_panel_" + RUN_NAME
FROZEN_ROOT_NAMES = {
    "selection": "fs2_selection_panel_" + RUN_NAME,
    "worker": "fs2_screening_worker_" + RUN_NAME,
    "activation": "fs2_activation_" + RUN_NAME,
    "runtime": "fs2_runtime_" + RUN_NAME,
}
WRAPPER_PREFIX = "fs2_d118_control_pairing_1"
FROZEN_EXPECTATIONS = copy.deepcopy(_d116.FROZEN_EXPECTATIONS)
FROZEN_EXPECTATIONS["panel"] = {"strata_limit": 4, "population_policy": LIQUIDITY_POPULATION}
FROZEN_EXPECTATIONS["worker"]["runtime_concurrency"] = 8
PLAN_SCHEMA = "fs2-panel-selection-plan-v4"
TEMPORAL_REASON = "scheduled_end_at_or_before_selection_declaration"
ALLOWED_EXCLUSION_REASONS = frozenset({TEMPORAL_REASON, LIQUIDITY_UNKNOWN, LIQUIDITY_BELOW})
LIQUID_BANDS = frozenset({"1", "2", "3"})

# Exactly these names differ from the D116 namespace (a test asserts it).
OVERRIDES = {
    "EVALUATOR_VERSION": EVALUATOR_VERSION,
    "D116_PROTOCOL": D118_PROTOCOL,
    "FROZEN_PANEL_NAME": FROZEN_PANEL_NAME,
    "FROZEN_ROOT_NAMES": FROZEN_ROOT_NAMES,
    "FROZEN_EXPECTATIONS": FROZEN_EXPECTATIONS,
}
_GLOBALS = dict(vars(_d116))
_GLOBALS.update(OVERRIDES)


def _rebind(function):
    """The identical D116 code object, resolving module names in the D118 namespace."""
    rebound = types.FunctionType(
        function.__code__, _GLOBALS, function.__name__, function.__defaults__,
        function.__closure__,
    )
    rebound.__kwdefaults__ = copy.copy(function.__kwdefaults__)
    rebound.__doc__ = function.__doc__
    return rebound


class _D118Evaluation(_d116._Evaluation):
    """Every D116 method rebound below; the D118 additions wrap ``gates``/``frozen_failures``."""


REBOUND_METHODS = sorted(
    name for name, value in vars(_d116._Evaluation).items()
    if isinstance(value, types.FunctionType)
)
for _name in REBOUND_METHODS:
    setattr(_D118Evaluation, _name, _rebind(getattr(_d116._Evaluation, _name)))
_GLOBALS["_Evaluation"] = _D118Evaluation
_guarded = _rebind(_d116._guarded)
_GLOBALS["_guarded"] = _guarded
_evaluate = _rebind(_d116.evaluate_d116)
_logic_only = _rebind(_d116.evaluate_d116_logic_only_test_aid)
REBOUND_FUNCTIONS = ("_guarded", "evaluate_d116", "evaluate_d116_logic_only_test_aid")

_base_gates = _D118Evaluation.gates
_base_frozen_failures = _D118Evaluation.frozen_failures
_base_diagnostics = _D118Evaluation.diagnostics
_base_pairs = _D118Evaluation.pairs


def _frozen_failures(self):
    """E1: the D116 frozen-value comparison plus the D118 population and schema versions."""
    reasons = _base_frozen_failures(self)
    checks = {
        "panel_policy.schema_version": (self.panel_policy.get("schema_version"),
                                        DECLARATION_SCHEMA),
        "selection_policy.schema_version": (self.sel_policy.get("schema_version"),
                                            SELECTION_SCHEMA),
        "selection_policy.population_policy": (self.sel_policy.get("population_policy"),
                                               LIQUIDITY_POPULATION),
        "selection_plan.schema_version": (self.sel_plan.get("schema_version"), PLAN_SCHEMA),
        "selection_plan.population_policy": (self.sel_plan.get("population_policy"),
                                             LIQUIDITY_POPULATION),
        "selection_plan.liquidity_floor": (self.sel_plan.get("liquidity_floor"),
                                           LIQUIDITY_FLOOR),
        "selection_plan.protocol.liquidity_edges[0]": (
            ((self.sel_plan.get("protocol") or {}).get("liquidity_edges") or [None])[0],
            LIQUIDITY_FLOOR),
    }
    for name, (actual, expected) in checks.items():
        if actual != expected:
            reasons.append(f"{name} {actual!r} != {expected!r}")
    return reasons


def population_failures(self):
    """E2 (D118): zero-inclusion reasons are allow-listed and the drawn frame is liquid."""
    reasons = []
    exclusions = self.sel_plan.get("exclusions")
    if not isinstance(exclusions, list):
        return ["selection_plan.exclusions unreadable"], {}
    counts = Counter(e.get("reason") if isinstance(e, dict) else None for e in exclusions)
    unknown = sorted(str(r) for r in counts if r not in ALLOWED_EXCLUSION_REASONS)
    if unknown:
        reasons.append(f"exclusion reasons outside the D118 allow-list: {unknown}")
    liquidity_scope = self.enforce or (
        self.sel_plan.get("population_policy") == LIQUIDITY_POPULATION
    )
    if liquidity_scope:
        recorded = self.sel_plan.get("population_exclusion_counts")
        if recorded != dict(sorted(counts.items(), key=lambda kv: str(kv[0]))):
            reasons.append("population_exclusion_counts differ from the exclusion list")
        for s in self.sel_plan.get("strata") or []:
            if s.get("liquidity_band") not in LIQUID_BANDS:
                reasons.append(
                    f"eligible stratum {str(s.get('stratum'))[:8]} has liquidity band "
                    f"{s.get('liquidity_band')!r} outside the liquidity >= 1000 population"
                )
    return reasons, {str(k): v for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))}


def _gates(self):
    g = _base_gates(self)
    extra, counts = self.population_failures()
    e2 = dict(g["E2"])
    e2["reasons"] = [*e2["reasons"], *extra]
    e2["pass"] = bool(e2["pass"] and not extra)
    e2["population_exclusion_counts"] = counts
    e2["allowed_exclusion_reasons"] = sorted(ALLOWED_EXCLUSION_REASONS)
    g["E2"] = e2
    return g


def _diagnostics(self):
    result = _base_diagnostics(self)
    n = D118_PROTOCOL["scheduled_slots"]
    result.pop("observed_origins_of_8", None)
    result.pop("eligible_histories_of_8", None)
    result[f"observed_origins_of_{n}"] = f"{result['observed_origins']}/{n}"
    result[f"eligible_histories_of_{n}"] = f"{result['eligible_completed_histories']}/{n}"
    ages = [a["window_age_at_freeze_s"] for a in self.timeline()["margins"].get(
        "window_age_at_freeze", []) if a.get("window_age_at_freeze_s") is not None]
    result["max_window_age_at_freeze_s"] = max(ages) if ages else None
    return result


def _groups(self, market):
    """Event / neg-risk group ids in the member's verified 2xx screening Gamma receipts."""
    found, verified = {"event_ids": set(), "neg_risk_market_ids": set()}, False
    member = self.members.get(market) or {}
    for receipt in (member.get("screen_receipts") or {}).get("gamma.market", []):
        body = receipt.body() if receipt.ok2xx else None
        if not isinstance(body, dict):
            continue
        verified = True
        for event in body.get("events") or []:
            if isinstance(event, dict) and event.get("id") is not None:
                found["event_ids"].add(str(event["id"]))
        if body.get("negRiskMarketID"):
            found["neg_risk_market_ids"].add(str(body["negRiskMarketID"]))
    return found, verified


def _pairs(self):
    """D116 pairs plus a dependence disclosure (descriptive; never changes the outcome)."""
    result = []
    for pair in _base_pairs(self):
        members = [x for x in (pair.get("triggered_market"), pair.get("control_market")) if x]
        groups = [_groups(self, x) for x in members]
        shared = {
            key: sorted(set.intersection(*(g[0][key] for g in groups)))
            if len(groups) == 2 else []
            for key in ("event_ids", "neg_risk_market_ids")
        }
        if any(shared.values()):
            state = "dependent_same_event_or_neg_risk_group"
        elif len(groups) == 2 and all(v and g["event_ids"] for g, v in groups):
            state = "no_shared_group_observed"
        else:
            state = "unknown_group_membership"
        result.append({**pair, "dependence": {
            "state": state, "shared": shared,
            "basis": "verified 2xx screening gamma.market receipts (events[].id, "
                     "negRiskMarketID)",
            "counts_as": "mechanism execution only; never an independent observation",
        }})
    return result


_D118Evaluation.frozen_failures = _frozen_failures
_D118Evaluation.population_failures = population_failures
_D118Evaluation.gates = _gates
_D118Evaluation.diagnostics = _diagnostics
_D118Evaluation.pairs = _pairs
D118_METHODS = ("frozen_failures", "population_failures", "gates", "diagnostics", "pairs")


def evaluate_d118(panel_root, selection_root=None, worker_root=None, runtime_root=None, *,
                  activation_root=None, launch_commit=None, protocol_check=True):
    """Evaluate one retained D118 run; the only authoritative entry point.

    Same contract as ``evaluate_d116``: ``launch_commit`` is required (E0 fails closed without
    it); root overrides and ``protocol_check=False`` force FAIL and ``authoritative`` false; any
    exception yields a FAIL report.
    """
    return _evaluate(panel_root, selection_root, worker_root, runtime_root,
                     activation_root=activation_root, launch_commit=launch_commit,
                     protocol_check=protocol_check)


def evaluate_d118_logic_only_test_aid(panel_root, **roots):
    """TEST AID ONLY: never authoritative (see ``evaluate_d116_logic_only_test_aid``)."""
    return _logic_only(panel_root, **roots)
