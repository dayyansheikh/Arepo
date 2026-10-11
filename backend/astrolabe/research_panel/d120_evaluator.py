"""D120 acceptance evaluator: screen-then-activate pairing with group-disjoint pairs.

``d116_evaluator.py`` is frozen and is not edited. As for D118, this module re-executes the same
compiled D116 code (classification table, citation checks, per-stage classification of screening,
window, origin, history and target states, the common-mode rule) in a copy of the D116 namespace
in which exactly the names in ``OVERRIDES`` differ. The D116 classification table is reused
unchanged (its sha256 must equal ``D116_TABLE_SHA256``).

D120 differs structurally from D116/D118, so the stage driver, the gates, the pairing and the
outcome decision are new (and can only be stricter about the reused per-stage classification):

* screened-only members are judged on their screening stage alone (two receipts, an
  authenticated triggered/untriggered state or a classified DATA reason) and must have no
  binding, window, origin or target;
* activated members (drawn trigger/control roles) additionally have a fresh binding read (two
  receipts, a recomputed snapshot trigger), a window bound to that binding, an origin and a target;
  the D116 window/origin/target classification runs on them with the binding receipts as the
  citation context of the pre-window book;
* hard gates: exact replay of the role draw from the sealed screening states and seed; no two
  activated members share a dependence group; D116-style engineering gates adapted to the
  screened/activated split;
* the recomputed binding trigger state is compared with the screening role descriptively only
  (``state_disagreements``); roles are never relabelled.

Outcome (first match): FAIL (engineering finding, failed gate or common-mode pattern);
INCONCLUSIVE (fewer than 4 drawn strata with a trigger, or screening coverage below 80% for
classified data reasons); PASS (fill >= 0.8 with >= 4 triggers in scope and >= 3 group-disjoint
complete pairs); PASS_WITH_LIMITATION:control_scarcity (fill < 0.8; routes to the "screen the
whole stratum" fallback); PASS_WITH_LIMITATION:pair_member_unobserved_data_reason (fill >= 0.8,
fewer than 3 complete pairs, every incomplete pair member limited by a classified DATA cause);
otherwise FAIL.

Pure and deterministic: no network, no clock, no writes.
"""

import copy
import types
from collections import Counter
from fractions import Fraction
from pathlib import Path

from . import d116_evaluator as _d116
from . import pairing as _pairing
from .pairing_declaration import VERSION as DECLARATION_SCHEMA
from .pairing_declaration import PairingPanelProtocol
from .pairing_selection import PLAN_VERSION as PLAN_SCHEMA
from .pairing_selection import TEMPORAL_REASON
from .pairing_selection import VERSION as SELECTION_SCHEMA
from .pairing_worker import VERSION as WORKER_SCHEMA
from .panel_declaration import LIQUIDITY_POPULATION
from .panel_selection import LIQUIDITY_BELOW, LIQUIDITY_UNKNOWN

EVALUATOR_VERSION = "d120-evaluator-v1"
D116_TABLE_SHA256 = "6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4"
CLASSIFICATION_TABLE = _d116.CLASSIFICATION_TABLE
TABLE_SHA256 = _d116.TABLE_SHA256
if TABLE_SHA256 != D116_TABLE_SHA256:
    raise ImportError("D116 classification table changed; D120 evaluator refuses to load")

OK, ENGINEERING, DATA_CLASSES = _d116.OK, _d116.ENGINEERING, _d116.DATA_CLASSES
common_mode_flags = _d116.common_mode_flags
_utc, _seconds, _gate, _HEX64 = _d116._utc, _d116._seconds, _d116._gate, _d116._HEX64

RUN_NAME = "d120_pairing_1"
FROZEN_PANEL_NAME = "fs2_panel_" + RUN_NAME
FROZEN_ROOT_NAMES = {
    "selection": "fs2_selection_panel_" + RUN_NAME,
    "worker": "fs2_screening_worker_" + RUN_NAME,
    "activation": "fs2_activation_" + RUN_NAME,
    "runtime": "fs2_runtime_" + RUN_NAME,
}
REQUIRED_SCREENING_SCHEMA = "fs2-screening-pairing-v5"
RUNTIME_SCHEMA = "fs2-pairing-window-runtime-v6"
FROZEN_DESIGN = _pairing.PairingDesign(strata=6, screen_per_stratum=12, min_groups_per_stratum=8)
D120_PROTOCOL = {
    "screened_slots": 72, "origin_slots": 12, "cycles": 1, "target_attempts": 1,
    "cadence_seconds": 120, "max_origin_delay_seconds": 60, "max_origin_save_seconds": 5,
    "horizon_seconds": 60, "tolerance_seconds": 15, "max_frame_age_seconds": 3600,
    "max_frame_interval_seconds": 600, "max_quote_age_seconds": 60,
    "max_identity_age_seconds": 180, "source_response_bytes": 65536,
    "source_run_retained_bytes": 1048576, "screened_receipt_bytes": 65536,
    "version": "fs2-pairing-panel-protocol-v1",
}
FROZEN_EXPECTATIONS = copy.deepcopy(_d116.FROZEN_EXPECTATIONS)
FROZEN_EXPECTATIONS["panel"] = {"population_policy": LIQUIDITY_POPULATION,
                                "category_policy": FROZEN_DESIGN.category_policy}
FROZEN_EXPECTATIONS["worker"]["runtime_concurrency"] = 8
ALLOWED_EXCLUSION_REASONS = frozenset({TEMPORAL_REASON, LIQUIDITY_UNKNOWN, LIQUIDITY_BELOW,
                                       _pairing.CATEGORY_POLICY_EXCLUDED})
LIQUID_BANDS = frozenset({"1", "2", "3"})
PASS_FILL = Fraction(4, 5)
MIN_TRIGGERS = 4
MIN_COMPLETE_PAIRS = 3
MIN_SCREENING_COVERAGE = Fraction(4, 5)
BIND_SOURCE = "fs2_capture_bind_"
BIND_DECLARATION = "fs2_trigger_declaration_bind_"

# Exactly these names differ from the D116 namespace (a test asserts it).
OVERRIDES = {
    "EVALUATOR_VERSION": EVALUATOR_VERSION,
    "D116_PROTOCOL": D120_PROTOCOL,
    "FROZEN_PANEL_NAME": FROZEN_PANEL_NAME,
    "FROZEN_ROOT_NAMES": FROZEN_ROOT_NAMES,
    "FROZEN_EXPECTATIONS": FROZEN_EXPECTATIONS,
    "REQUIRED_SCREENING_SCHEMA": REQUIRED_SCREENING_SCHEMA,
}
_GLOBALS = dict(vars(_d116))
_GLOBALS.update(OVERRIDES)


def _rebind(function):
    rebound = types.FunctionType(function.__code__, _GLOBALS, function.__name__,
                                 function.__defaults__, function.__closure__)
    rebound.__kwdefaults__ = copy.copy(function.__kwdefaults__)
    rebound.__doc__ = function.__doc__
    return rebound


class _D120Evaluation(_d116._Evaluation):
    """D116 per-stage classification rebound; D120 driver, gates and decision below."""


REBOUND_METHODS = sorted(name for name, value in vars(_d116._Evaluation).items()
                         if isinstance(value, types.FunctionType))
for _name in REBOUND_METHODS:
    setattr(_D120Evaluation, _name, _rebind(getattr(_d116._Evaluation, _name)))
_GLOBALS["_Evaluation"] = _D120Evaluation
_guarded = _rebind(_d116._guarded)
_GLOBALS["_guarded"] = _guarded
_evaluate = _rebind(_d116.evaluate_d116)
_logic_only = _rebind(_d116.evaluate_d116_logic_only_test_aid)

_base_load = _D120Evaluation.load
_base_frozen_failures = _D120Evaluation.frozen_failures
_base_timeline = _D120Evaluation.timeline


def _fraction(value):
    try:
        return Fraction(int(value["numerator"]), int(value["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


# ----- loading and stages ---------------------------------------------------------------------
def _load(self):
    _base_load(self)
    self.bindings = self.r.pair(self.worker, "bindings", "binding") or {}
    self.binding_items = self.bindings.get("items") or []
    self.design = None
    try:
        self.design = _pairing.design_from_dict(self.panel_policy.get("pairing_design") or {})
    except (TypeError, ValueError, KeyError):
        self.r.note("panel", "missing_or_unreadable_artifact", "pairing design unreadable")
    for k, item in enumerate(self.binding_items):
        market = ((item or {}).get("member") or {}).get("market_id")
        if market not in self.members:
            self.r.note("binding", "missing_or_unreadable_artifact",
                        f"binding {k} market {market} is not a screened member")
            continue
        self.members[market]["binding_index"] = k
        self.members[market]["binding_item"] = item
    self.activated = [m for m in self.order if "binding_index" in self.members[m]]
    self.first_stage = {a.get("market_id"): a for a in
                        (self.plan.get("screened_assignments") or [])}


def binding_stage(self, m):
    market, k = m["market_id"], m["binding_index"]
    info = {"state": None, "reasons": [], "causes": [], "signed_imbalance": None}
    m["stages"]["binding"] = info
    rx = _d116._captures(self.r, self.worker / f"{BIND_SOURCE}{k:03d}", "binding", market)
    m["binding_receipts"] = rx
    for source, items in rx.items():
        for item in items:
            expect = market if source == "gamma.market" else m["token_id"]
            got = item.market_id if source == "gamma.market" else item.token_id
            if source in ("gamma.market", "clob.book") and got != expect:
                self.add(market, "binding", "trigger_reason", "requested_identity_differs",
                         f"{source} binding receipt requested {got}")
    folder = self.worker / f"{BIND_DECLARATION}{k:03d}" / "fs2_trigger_computation_result"
    facts = self.r.pair(folder, "trigger_computation_facts", "binding", market)
    projection = (facts or {}).get("projection") or {}
    if not projection:
        info["state"] = "missing_binding_trigger"
        info["causes"].append({"state": "missing_binding_trigger", "class": ENGINEERING,
                               "rule": "artifact:missing_or_unreadable_artifact"})
        return
    info["state"] = projection.get("state")
    info["reasons"] = list(projection.get("reasons") or [])
    info["signed_imbalance"] = projection.get("signed_imbalance")
    if (projection.get("market_id") != market or projection.get("token_id") != m["token_id"]):
        self.add(market, "binding", "trigger_reason", "requested_identity_differs",
                 "binding trigger identity differs from the activated member")
    ctx = {"receipts": rx, "token_id": m["token_id"], "market_id": market}
    for reason in info["reasons"]:
        f = self.add(market, "binding", "trigger_reason", reason, ctx=ctx)
        info["causes"].append({"state": reason, "class": f["class"], "rule": f["rule"],
                               "citation": f["citation"]})
    if info["state"] not in ("triggered", "untriggered", "unavailable"):
        self.add(market, "binding", "screening_state", str(info["state"]),
                 "binding trigger state outside the three-state rule")


def _role(m):
    arms = {a.get("arm") for a in m["roles"]}
    return "triggered" if arms == {"triggered"} else "control" if arms == {"control"} else None


def _member_stages(self, m):
    market = m["market_id"]
    self.screening_stage(m)
    m["activated"] = "binding_index" in m
    if not m["activated"]:
        m["complete_chain"] = False
        m["causes"] = []
        if m.get("origin_dir") or m.get("target_dirs"):
            self.r.note("origin", "missing_or_unreadable_artifact",
                        "origin or target retained for a screened-only member", market)
        return
    self.binding_stage(m)
    saved = (m["index"], m.get("screen_receipts"))
    m["index"], m["screen_receipts"] = m["binding_index"], m.get("binding_receipts", {})
    try:
        self.window_stage(m)
        self.origin_stage(m)
        self.target_stage(m)
    finally:
        m["index"], m["screen_receipts"] = saved
    stages = m["stages"]
    origin_ok = stages.get("origin", {}).get("state") == "observed"
    history_ok = stages.get("history", {}).get("eligible") is True
    target_ok = stages.get("target", {}).get("state") == "observed"
    m["complete_chain"] = bool(origin_ok and history_ok and target_ok)
    binding = stages.get("binding") or {}
    role = _role(m)
    expected = {"triggered": "triggered", "control": "untriggered"}.get(role)
    m["binding_state"] = binding.get("state")
    m["state_agreement"] = ("unavailable" if binding.get("state") not in
                            ("triggered", "untriggered") else
                            "agree" if binding.get("state") == expected else "disagree")
    if not m["complete_chain"]:
        for stage in ("screening", "binding", "window", "origin", "history", "target"):
            info = stages.get(stage) or {}
            if stage in ("origin", "target") and info.get("state") == "observed":
                continue
            if stage == "history" and info.get("eligible") is not False:
                continue
            if stage == "binding" and info.get("state") in ("triggered", "untriggered"):
                continue
            for cause in info.get("causes", []):
                m["causes"].append({"stage": stage, **cause})
            if info.get("causes"):
                break
        if not m["causes"]:
            m["causes"].append({"stage": "chain", "state": "unknown", "class": ENGINEERING,
                                "rule": "chain_incomplete_without_classified_cause"})
            self.add(market, "chain", "artifact", "missing_or_unreadable_artifact",
                     "chain incomplete without a classified cause")


# ----- gates ----------------------------------------------------------------------------------
def _identity_gate(self):
    """E0: the one frozen D120 run, from the stated commit, on live (public) data."""
    reasons, evidence = [], {}
    if self.panel.name != FROZEN_PANEL_NAME:
        reasons.append(f"panel root name {self.panel.name} != {FROZEN_PANEL_NAME}")
    if self.overrides or not self.derived:
        reasons.append("roots are not derived from the panel root alone")
    actual = {"selection": self.selection, "worker": self.worker,
              "activation": self.activation, "runtime": self.runtime}
    for key, name in FROZEN_ROOT_NAMES.items():
        if actual[key].name != name or actual[key].parent != self.panel.parent:
            reasons.append(f"{key} root {actual[key].name} != {name} beside the panel root")
    launch = self.launch_commit
    if not (isinstance(launch, str) and _d116._COMMIT.fullmatch(launch)):
        reasons.append("launch commit absent or not a 40-hex commit")
    commits = {
        "panel_policy.frame_implementation_commit":
            self.panel_policy.get("frame_implementation_commit"),
        "selection_policy.implementation_commit": self.sel_policy.get("implementation_commit"),
        "frame_read_policy.implementation_commit":
            self.frame_read_policy.get("implementation_commit"),
        "worker_policy.implementation_commit": self.worker_policy.get("implementation_commit"),
        "runtime_read_policy.implementation_commit":
            self.rt_read_policy.get("implementation_commit"),
    }
    for name, value in commits.items():
        if not (isinstance(value, str) and _d116._COMMIT.fullmatch(value)):
            reasons.append(f"{name} absent or malformed")
        elif value != launch:
            reasons.append(f"{name} {value} != launch commit {launch}")
    evidence["commits"] = commits
    schemas = {"screening_policy": self.screen_policy.get("schema_version"),
               "screening_report": self.screen_report.get("schema_version"),
               "worker_report.screening":
                   (self.worker_report.get("screening") or {}).get("schema_version")}
    for name, value in schemas.items():
        if value != REQUIRED_SCREENING_SCHEMA:
            reasons.append(f"{name} schema {value} != {REQUIRED_SCREENING_SCHEMA}")
    evidence["screening_schemas"] = schemas
    recovery = self.worker_report.get("recovery") or []
    provenance = {
        "frame_original_report": self.sel_original.get("provenance_class"),
        "selection_report": self.sel_report.get("provenance_class"),
        "screening_policy.source": self.screen_policy.get("source_provenance_class"),
        "screening_report": self.screen_report.get("provenance_class"),
        "worker_policy": self.worker_policy.get("provenance_class"),
        "worker_report.screening":
            (self.worker_report.get("screening") or {}).get("provenance_class"),
        "worker_report.runtime": (self.worker_report.get("runtime") or {}).get("provenance_class"),
        "activation_facts": self.act_facts.get("provenance_class"),
        "runtime_policy": self.rt_policy.get("provenance_class"),
        "runtime_report": self.rt_report.get("provenance_class"),
        "read_receipt.original_provenance_class":
            self.read_receipt.get("original_provenance_class"),
        "worker_report.recovery[0].original_provenance_class": (
            recovery[0].get("original_provenance_class") if len(recovery) == 1 else None),
    }
    for m in self.members.values():
        market = m["market_id"]
        folders = [("screening", self.worker / f"fs2_capture_screen_{m['index']:03d}")]
        if m.get("activated"):
            k = m["binding_index"]
            folders += [("binding", self.worker / f"{BIND_SOURCE}{k:03d}"),
                        ("origin", (m.get("origin_dir") or Path("/nonexistent"))
                         / "fs2_capture_origin")]
        for stage, folder in folders:
            if folder.is_dir():
                run = self.r.plain(folder / "run.json", stage, market) or {}
                provenance[f"{market}.{stage}_capture"] = run.get("provenance_class")
        for n, target in enumerate(m.get("target_dirs") or []):
            if (target / "fs2_capture_target").is_dir():
                run = self.r.plain(target / "fs2_capture_target" / "run.json", "target", market)
                provenance[f"{market}.target_capture[{n}]"] = (run or {}).get("provenance_class")
        if not m.get("activated"):
            continue
        socket_dir = self.worker / f"fs2_socket_window_{m['binding_index']:03d}"
        if socket_dir.is_dir():
            policy = self.r.pair(socket_dir, "socket_window_policy", "window", market) or {}
            report = self.r.pair(socket_dir, "socket_window_report", "window", market) or {}
            transport = policy.get("transport") or {}
            provenance[f"{market}.socket_policy"] = transport.get("provenance_class")
            provenance[f"{market}.socket_report"] = report.get("provenance_class")
            if transport.get("kind") != _d116.LIVE_SOCKET_KIND:
                reasons.append(f"{market}: socket transport kind {transport.get('kind')}")
        elif (m["stages"].get("window") or {}).get("missing_reason") is None:
            reasons.append(f"{market}: socket window artifacts absent")
    bad = {k: v for k, v in sorted(provenance.items()) if v != _d116.LIVE_PROVENANCE}
    if bad:
        reasons.append(f"provenance is not {_d116.LIVE_PROVENANCE}: {bad}")
    evidence["provenance"] = provenance
    evidence["required_ancestor_commit"] = _d116.REQUIRED_ANCESTOR_COMMIT
    return _gate(not reasons, reasons, **evidence)


def _frozen_failures(self):
    """E1: the D116 frozen-value comparison plus the D120 schemas and design."""
    reasons = _base_frozen_failures(self)
    checks = {
        "panel_policy.schema_version": (self.panel_policy.get("schema_version"),
                                        DECLARATION_SCHEMA),
        "panel_policy.pairing_design": (self.panel_policy.get("pairing_design"),
                                        FROZEN_DESIGN.as_dict()),
        "selection_policy.schema_version": (self.sel_policy.get("schema_version"),
                                            SELECTION_SCHEMA),
        "selection_policy.grouping_policy": (self.sel_policy.get("grouping_policy"),
                                             _pairing.grouping_policy(True)),
        "selection_plan.schema_version": (self.sel_plan.get("schema_version"), PLAN_SCHEMA),
        "selection_plan.pairing_design": (self.sel_plan.get("pairing_design"),
                                          FROZEN_DESIGN.as_dict()),
        "screening_policy.pairing_design": (self.screen_policy.get("pairing_design"),
                                            FROZEN_DESIGN.as_dict()),
        "worker_policy.schema_version": (self.worker_policy.get("schema_version"),
                                         WORKER_SCHEMA),
        "runtime_policy.schema_version": (self.rt_policy.get("schema_version"), RUNTIME_SCHEMA),
        "selection_plan.liquidity_floor": (self.sel_plan.get("liquidity_floor"), "1000"),
    }
    for name, (got, expected) in checks.items():
        if got != expected:
            reasons.append(f"{name} {got!r} != {expected!r}")
    return reasons


def _common(self, rows_of):
    rows = []
    for market in rows_of:
        m = self.members[market]
        receipts = [r for d in (m.get("screen_receipts"), m.get("binding_receipts"),
                                m.get("origin_receipts"), m.get("target_receipts"))
                    for v in (d or {}).values() for r in v]
        failing = any(r.transport_error is not None
                      or (isinstance(r.status, int) and 400 <= r.status < 500)
                      for r in receipts)
        if m.get("activated"):
            complete, causes = m["complete_chain"], m["causes"]
        else:
            complete = bool(m.get("authenticated_state"))
            causes = [{"stage": "screening", **c}
                      for c in (m["stages"].get("screening") or {}).get("causes", [])]
        limiting = None
        if not complete and causes:
            limiting = {k: causes[0].get(k) for k in ("stage", "state", "class")}
        rows.append({"complete": complete, "limiting": limiting,
                     "listed_market_failure": failing})
    return rows


def _common_mode(self):
    flags = [f"screened: {f}" for f in common_mode_flags(_common(self, self.order))]
    if self.activated:
        flags += [f"activated: {f}" for f in common_mode_flags(_common(self, self.activated))]
    return flags


def role_replay(self):
    """Exact replay of the role draw from the sealed screening seed, list and states."""
    reasons = []
    if self.design is None:
        return ["pairing design unreadable: role draw cannot be replayed"], None
    seed = self.screen_policy.get("seed")
    rows, states = [], {}
    for item in self.screen_policy.get("selected") or []:
        first = item.get("screening_assignment") or {}
        rows.append({"market_id": (item.get("member") or {}).get("market_id"),
                     "stratum": first.get("stratum"), "stratum_order": first.get("stratum_order"),
                     "dependence_group": first.get("dependence_group")})
    for entry in self.plan.get("assessment_inventory") or []:
        evidence = (entry.get("assessment") or {}).get("evidence_id")
        states[entry.get("market_id")] = {"state": entry.get("effective_state"),
                                          "evidence_id": evidence}
    try:
        draw = _pairing.role_draw(seed, rows, states, self.design)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"role draw replay failed: {type(exc).__name__}"], None

    def key(a):
        return (a.get("market_id"), a.get("arm"), a.get("stratum"), a.get("trigger_id"),
                tuple(a.get("matched_trigger_ids") or []))

    expected = sorted(key(a) for a in draw["assignments"])
    actual = sorted(key(a) for a in self.plan.get("assignments") or [])
    if expected != actual:
        reasons.append("role assignments differ from the exact replay of the role draw")
    strata = {s.get("stratum"): s for s in self.plan.get("strata") or []}
    for report in draw["strata"]:
        recorded = strata.get(report["stratum"]) or {}
        for field in ("pair_state", "triggered_pool", "untriggered_pool", "unavailable_pool",
                      "not_assessed_pool", "triggers_in_scope", "pairs_drawn"):
            if recorded.get(field) != report[field]:
                reasons.append(f"stratum {str(report['stratum'])[:8]} {field} differs from "
                               "the replay")
    for field in ("triggers_in_scope", "pairs_drawn", "fill", "strata_with_trigger",
                  "control_scarcity_strata"):
        if self.plan.get(field) != draw[field]:
            reasons.append(f"plan {field} differs from the replay")
    return reasons, draw


def dependence_failures(self):
    """Hard gate: no two activated (or screened) members share a dependence group."""
    reasons = []
    groups = {}
    for market in self.order:
        group = (self.first_stage.get(market) or {}).get("dependence_group")
        if not isinstance(group, str) or not group:
            reasons.append(f"{market}: screened member without a dependence group")
            continue
        groups[market] = group
    screened = Counter(groups.values())
    if any(v > 1 for v in screened.values()):
        reasons.append("two screened members share a dependence group")
    active = Counter(groups.get(m) for m in self.activated)
    shared = sorted(str(g) for g, v in active.items() if v > 1)
    if shared:
        reasons.append(f"activated members share dependence groups: {shared}")
    for a in self.plan.get("assignments") or []:
        if a.get("dependence_group") != groups.get(a.get("market_id")):
            reasons.append(f"{a.get('market_id')}: role group differs from the screened group")
    return reasons


def _gates(self):
    g = {"E0": self.identity_gate()}
    proto = self.protocol
    # E1 (frame, frozen values)
    reasons = []
    original = self.sel_original
    if original.get("state") != "exhausted_consistent":
        reasons.append(f"frame state {original.get('state')}")
    start, end = _utc(original.get("interval_start")), _utc(original.get("interval_end"))
    limit = proto.get("max_frame_interval_seconds")
    if start is None or end is None or limit is None or _seconds(end, start) > limit:
        reasons.append(f"interval {_seconds(end, start)} s exceeds {limit}")
    if not _HEX64.fullmatch(str(self.sel_report.get("frame_report_hash"))):
        reasons.append("frame report hash absent")
    pages = self.selection / "pages"
    if not pages.is_dir() or not any(pages.iterdir()):
        reasons.append("raw frame pages not retained in selection root")
    if not _HEX64.fullmatch(str(original.get("page_manifest_hash"))):
        reasons.append("page manifest hash absent")
    reasons += self.age_failures()
    reasons += [f"{e['member']}: {e['rule']}" for e in self.stage_engineering("panel")]
    try:
        PairingPanelProtocol(**proto)
    except (TypeError, ValueError):
        reasons.append("panel protocol is not a valid pairing protocol")
    if self.enforce:
        diff = {k: (proto.get(k), v) for k, v in D120_PROTOCOL.items() if proto.get(k) != v}
        if diff:
            reasons.append(f"panel protocol differs from frozen D120 values: {diff}")
        reasons += self.frozen_failures()
    g["E1"] = _gate(not reasons, reasons)
    # E2 (selection: population, strata, group-disjoint screening draw)
    reasons = []
    available = _utc(self.sel_report.get("original_frame_available_at"))
    declared = _utc(self.panel_policy.get("declared_at"))
    sel_declared = _utc(self.sel_policy.get("declared_at"))
    started = _utc(self.sel_report.get("computation_started_at"))
    if declared is None or available is None or declared < available:
        reasons.append("panel_policy.declared_at precedes frame_available_at (or unreadable)")
    if sel_declared is None or declared is None or sel_declared < declared:
        reasons.append("selection policy declared before the panel declaration")
    if started is None or sel_declared is None or started < sel_declared:
        reasons.append("selection numerical reads precede the selection declaration")
    if not (self.sel_plan.get("protocol") or {}).get("seed"):
        reasons.append("sealed seed absent from selection plan")
    strata = self.sel_plan.get("strata") or []
    sampled = {s.get("stratum"): s for s in strata if s.get("sampling_state") == "sampled"}
    draw = self.sel_plan.get("stratum_draw") or {}
    drawable = [s for s in strata if s.get("drawable") is True]
    design = self.design
    if design is not None:
        if len(sampled) != min(design.strata, len(drawable)):
            reasons.append(f"sampled strata {len(sampled)} != min(strata, drawable)")
        for s in strata:
            groups = s.get("dependence_groups")
            if not isinstance(groups, int) or (groups >= design.min_groups_per_stratum) != (
                    s.get("drawable") is True):
                reasons.append(f"stratum {str(s.get('stratum'))[:8]} drawable flag inconsistent")
    if draw.get("drawable_strata") != len(drawable):
        reasons.append("stratum draw drawable count differs from the strata report")
    for s in sampled.values():
        if _fraction(s.get("stratum_inclusion_probability") or {}) is None:
            reasons.append(f"stratum {str(s.get('stratum'))[:8]} lacks an exact probability")
    counts = self.sel_report.get("counts") or {}
    size = self.sel_plan.get("frame_size")
    exclusions = self.sel_plan.get("exclusions")
    eligible = self.sel_plan.get("selection_eligible_member_count")
    if not isinstance(exclusions, list):
        reasons.append("selection_plan.exclusions unreadable")
        exclusions = []
    if counts.get("sampling_members") != size:
        reasons.append("selection_report.counts.sampling_members != plan frame_size")
    if eligible is None or size != len(exclusions) + eligible:
        reasons.append("frame_size != zero-inclusion exclusions + eligible members")
    reason_counts = Counter(e.get("reason") if isinstance(e, dict) else None for e in exclusions)
    allowed = set(ALLOWED_EXCLUSION_REASONS)
    if design is not None and not design.exclude_categories:
        allowed.discard(_pairing.CATEGORY_POLICY_EXCLUDED)
    unknown = sorted(str(r) for r in reason_counts if r not in allowed)
    if unknown:
        reasons.append(f"exclusion reasons outside the D120 allow-list: {unknown}")
    if self.sel_plan.get("population_exclusion_counts") != dict(
            sorted(reason_counts.items(), key=lambda kv: str(kv[0]))):
        reasons.append("population_exclusion_counts differ from the exclusion list")
    excluded = set(design.exclude_categories) if design is not None else set()
    for s in strata:
        if s.get("liquidity_band") not in LIQUID_BANDS:
            reasons.append(f"eligible stratum {str(s.get('stratum'))[:8]} liquidity band "
                           f"{s.get('liquidity_band')!r} outside liquidity >= 1000")
        category = str(s.get("category"))
        if not category.startswith(_pairing.STRATUM_CATEGORY_PREFIX):
            reasons.append(f"stratum {str(s.get('stratum'))[:8]} category is not fee_category")
        elif category[len(_pairing.STRATUM_CATEGORY_PREFIX):] in excluded:
            reasons.append(f"stratum {str(s.get('stratum'))[:8]} has an excluded category")
    screened = self.sel_plan.get("assignments") or []
    n = self.sel_plan.get("unique_selected_markets")
    if {a.get("arm") for a in screened} - {"screened"}:
        reasons.append("first-stage arms other than screened")
    if len(screened) != n or len(self.members) != n:
        reasons.append(f"screened members {len(self.members)} != selected {n}")
    per = Counter(a.get("stratum") for a in screened)
    for stratum, count in per.items():
        if stratum not in sampled:
            reasons.append(f"screened member in an unsampled stratum {str(stratum)[:8]}")
        if design is not None and count > design.screen_per_stratum:
            reasons.append(f"stratum {str(stratum)[:8]} screened {count} > per-stratum limit")
    if len({a.get("dependence_group") for a in screened}) != len(screened):
        reasons.append("first-stage screened members share a dependence group")
    if self.sel_report.get("unique_selected_markets") != n:
        reasons.append("selected counts differ between report and plan")
    reasons += [f"{e['member']}: {e['rule']}" for e in self.stage_engineering("selection")]
    g["E2"] = _gate(not reasons, reasons, unique_selected_markets=n,
                    zero_inclusion_exclusions=len(exclusions),
                    population_exclusion_counts={str(k): v for k, v in reason_counts.items()},
                    drawable_strata=len(drawable), sampled_strata=len(sampled))
    # E3 (screening of every screened member)
    reasons = []
    worker_state = self.worker_report.get("state")
    if _d116._finding("worker_state", worker_state, stage="screening")["class"] != OK:
        reasons.append(f"worker state {worker_state}")
    states = self.screen_report.get("states") or []
    if len(states) != len(self.members):
        reasons.append("screening state rows != screened members")
    for state in states:
        if "covariates" not in state:
            reasons.append(f"{state.get('market_id')}: screening covariates not retained")
    for e in self.stage_engineering("screening"):
        reasons.append(f"{e['member']}: {e['rule']}")
    started = _utc(self.completion.get("read_started_at"))
    done = _utc(self.screen_available())
    limit = FROZEN_EXPECTATIONS["screening_max_seconds"]
    if started is None or done is None:
        reasons.append("finish-call clocks missing: duration cannot be checked")
    elif _seconds(done, started) > limit:
        reasons.append(f"finish call {_seconds(done, started)} s exceeds {limit}")
    for m in self.members.values():
        if m["stages"]["screening"].get("state") not in ("triggered", "untriggered",
                                                          "unavailable"):
            reasons.append(f"{m['market_id']}: not classified triggered/untriggered/unavailable")
    g["E3"] = _gate(not reasons, reasons, states=dict(sorted(Counter(
        str(m["stages"]["screening"]["state"]) for m in self.members.values()).items())))
    # E4 (binding, window and history of activated members)
    reasons = [f"{e['member']}: {e['rule']}"
               for e in self.stage_engineering("binding", "window", "history")]
    for market in self.activated:
        m = self.members[market]
        w, h = m["stages"].get("window") or {}, m["stages"].get("history") or {}
        if w.get("missing_reason") == "entry_missing":
            reasons.append(f"{market}: no observer attempt or refusal")
        if h.get("eligible") is False and not h.get("causes"):
            reasons.append(f"{market}: ineligible history without reason")
        if sum(len(v) for v in (m.get("binding_receipts") or {}).values()) != 2:
            reasons.append(f"{market}: binding receipts != 2")
    g["E4"] = _gate(not reasons, reasons)
    # E5 (roles: exact replay, dependence, authentication, activation closure)
    reasons, replay = self.role_replay()
    reasons += self.dependence_failures()
    by_trigger = {a.get("trigger_id"): a for a in self.plan.get("assignments") or []
                  if a.get("arm") == "triggered"}
    arms = Counter(a.get("arm") for a in self.plan.get("assignments") or [])
    if set(arms) - {"triggered", "control"}:
        reasons.append(f"second-stage arms other than triggered/control: {dict(arms)}")
    for a in self.plan.get("assignments") or []:
        m = self.members.get(a.get("market_id")) or {}
        if a.get("arm") == "control":
            ids = a.get("matched_trigger_ids") or []
            if len(ids) != 1 or ids[0] not in by_trigger:
                reasons.append(f"control {a.get('market_id')} matches no triggered assignment")
            elif by_trigger[ids[0]].get("stratum") != a.get("stratum"):
                reasons.append(f"control {a.get('market_id')} is not in its trigger's stratum")
            if a.get("assessment_state") != "untriggered" or not m.get("authenticated_state"):
                reasons.append(f"control {a.get('market_id')} is not authenticated untriggered")
        elif a.get("arm") == "triggered":
            if a.get("assessment_state") != "triggered" or not m.get("authenticated_state"):
                reasons.append(f"trigger {a.get('market_id')} is not authenticated triggered")
    roles = sorted({a.get("market_id") for a in self.plan.get("assignments") or []})
    if sorted(self.activated) != roles:
        reasons.append("activated (bound) members differ from the drawn roles")
    if sorted(s.get("market_id") for s in self.act_facts.get("selected") or []) != roles:
        reasons.append("activation members differ from the drawn roles")
    capacity = self.worker_report.get("role_capacity") or {}
    if not capacity.get("fits"):
        reasons.append("role_capacity.fits is not true")
    if (capacity.get("counts_per_cycle") or {}).get("scheduled"):
        reasons.append("scheduled arm is not 0")
    g["E5"] = _gate(not reasons, reasons, roles=dict(arms))
    # E6 (origins of activated members only)
    reasons = [f"{e['member']}: {e['rule']}"
               for e in self.stage_engineering("origin", "activation", "runtime")]
    if len(self.rt_report.get("origins") or []) != len(self.activated):
        reasons.append("origin results != activated members")
    for market in self.activated:
        m = self.members[market]
        if m.get("origin_receipt") is None:
            reasons.append(f"{market}: no durable origin receipt")
        if (m["stages"]["origin"].get("state") == "observed"
                and (m.get("origin_facts") or {}).get("origin_at") is None):
            reasons.append(f"{market}: observed origin without recorded origin_at")
    reasons += self.ack_before_target()
    g["E6"] = _gate(not reasons, reasons)
    # E7 (targets of activated members)
    reasons = [f"{e['member']}: {e['rule']}" for e in self.stage_engineering("target")]
    for market in self.activated:
        t = self.members[market]["stages"]["target"]
        if t.get("state") in ("pending", "incomplete_evidence", "missing_outcome", None):
            reasons.append(f"{market}: target state {t.get('state')}")
        if self.members[market]["stages"]["origin"].get("state") == "observed" and len(
                t.get("attempt_states") or []) != self.protocol.get("target_attempts", 1):
            reasons.append(f"{market}: attempts {len(t.get('attempt_states') or [])}")
    g["E7"] = _gate(not reasons, reasons)
    # E8 (one original-code audit of the complete runtime)
    reasons = []
    recovery = self.worker_report.get("recovery") or []
    run_hash = (self.rt_report.get("__ack__") or {}).get("payload_hash")
    if worker_state != "pilot_collected_unaccepted":
        reasons.append(f"worker state {worker_state}")
    if len(recovery) != 1:
        reasons.append(f"recovery receipts {len(recovery)} != 1")
    else:
        if recovery[0].get("original_report_hash") != run_hash:
            reasons.append("recovery original_report_hash != runtime report hash")
        if not str(recovery[0].get("original_state", "")).startswith("verified_"):
            reasons.append(f"recovery state {recovery[0].get('original_state')}")
    receipt = {k: v for k, v in self.read_receipt.items() if k != "__ack__"}
    if not receipt:
        reasons.append("original read receipt absent or failed its hash check")
    elif len(recovery) == 1 and receipt != recovery[0]:
        reasons.append("read_receipt.json differs from worker_report recovery[0]")
    g["E8"] = _gate(not reasons, reasons)
    # E9 (accounting)
    reasons = self.accounting()
    g["E9"] = _gate(not reasons, reasons)
    return g


def _accounting(self):
    from astrolabe.feature_store.admission import content_hash

    reasons = []
    members, activated = set(self.members), set(self.activated)
    if not members:
        return ["no screened members"]
    stage_sets = {
        "screening_states": ({s.get("market_id") for s in self.screen_report.get("states") or []},
                             members),
        "inventory": ({s.get("market_id") for s in self.plan.get("assessment_inventory") or []},
                      members),
        "bindings": ({((i or {}).get("member") or {}).get("market_id")
                      for i in self.binding_items}, activated),
        "windows": ({m for m in activated if (self.members[m]["stages"].get("window") or {})
                     .get("missing_reason") != "entry_missing"}, activated),
        "origins": ({self.by_intent.get(o.get("intent_id"))
                     for o in self.rt_report.get("origins") or []}, activated),
        "outcomes": ({self.by_intent.get(o.get("origin_id"))
                      for o in self.rt_report.get("outcomes") or []}, activated),
        "activation": ({s.get("market_id") for s in self.act_facts.get("selected") or []},
                       activated),
    }
    for name, (ids, expected) in stage_sets.items():
        if ids != expected:
            reasons.append(f"{name} members differ from the expected set")
    # Windows exist for bindings only (one per activated member), never for screened members.
    on_disk = sorted(p.name for p in self.worker.glob("window_*.json")
                     if not p.name.endswith("_ack.json"))
    if on_disk != [f"window_{k:03d}.json" for k in range(len(self.binding_items))]:
        reasons.append("window entries differ from the binding list")
    for name, rows, key in (("states", self.screen_report.get("states"), "market_id"),
                            ("origins", self.rt_report.get("origins"), "intent_id"),
                            ("outcomes", self.rt_report.get("outcomes"), "origin_id")):
        if any(v != 1 for v in Counter(r.get(key) for r in rows or []).values()):
            reasons.append(f"{name}: a member appears in more than one terminal row")
    attempts = Counter(a.get("origin_id") for a in self.rt_report.get("attempts") or [])
    expected = self.protocol.get("target_attempts", 1)
    if any(v != expected for v in attempts.values()) or len(attempts) != len(activated):
        reasons.append("target attempts per origin differ from the declared number")
    for m in self.members.values():
        screen = sum(len(v) for v in (m.get("screen_receipts") or {}).values())
        if screen != 2:
            reasons.append(f"{m['market_id']}: {screen} screening receipts != 2")
        if (m["stages"].get("origin", {}).get("state") == "observed"
                and sum(len(v) for v in (m.get("origin_receipts") or {}).values()) != 3):
            reasons.append(f"{m['market_id']}: origin receipts != 3")
        if (m["stages"].get("target", {}).get("state") in ("observed", "unavailable", "closed")
                and sum(len(v) for v in (m.get("target_receipts") or {}).values())
                != 2 * expected):
            reasons.append(f"{m['market_id']}: target receipts != {2 * expected}")
        for source, items in [item for d in (m.get("screen_receipts"),
                                             m.get("binding_receipts"),
                                             m.get("origin_receipts"),
                                             m.get("target_receipts"))
                              for item in (d or {}).items()]:
            for item in items:
                if not (item.raw_verified and item.receipt_verified):
                    reasons.append(f"{m['market_id']}: {source} receipt/raw hash mismatch")
    reserved = (self.worker_policy.get("reservation") or {}).get("screening_retained_bytes")
    retained = self.worker_report.get("retained_bytes_before_report")
    if not isinstance(reserved, int) or not isinstance(retained, int) or retained > reserved:
        reasons.append("retained bytes exceed the screening reservation (or unreadable)")
    chain = [self.sel_original.get("frame_available_at"), self.panel_policy.get("declared_at"),
             self.sel_policy.get("declared_at"), self.sel_report.get("computed_at"),
             self.worker_policy.get("declared_at"), self.screen_available(),
             self.bindings.get("declared_at"), self.act_facts.get("read_completed_at"),
             self.rt_report.get("finished_at"), self.worker_report.get("reported_at")]
    times = [_utc(c) for c in chain]
    if any(t is None for t in times) or any(b < a for a, b in zip(times, times[1:],
                                                                    strict=False)):
        reasons.append("ordered stage clocks do not hold across the retained artifacts")
    for market in self.activated:
        slot = (self.members[market].get("origin_intent") or {}).get("slot") or {}
        identity = {k: slot.get(k) for k in ("panel_declaration_hash", "cycle", "market_id",
                                              "token_id")}
        if slot and (content_hash(identity) != slot.get("intent_id")
                     or slot.get("panel_declaration_hash")
                     != self.act_facts.get("panel_declaration_hash")):
            reasons.append(f"{market}: origin slot identity differs from activation")
    return reasons


# ----- pairs, summary and decision ------------------------------------------------------------
def _pairs(self):
    assignments = self.plan.get("assignments") or []
    triggered = {a["trigger_id"]: a for a in assignments if a.get("arm") == "triggered"}
    result, used = [], set()
    for a in sorted(assignments, key=lambda x: (x.get("stratum") or "", x.get("market_id"))):
        if a.get("arm") != "control":
            continue
        for tid in a.get("matched_trigger_ids") or []:
            t = triggered.get(tid)
            markets = [a["market_id"]] + ([t["market_id"]] if t else [])
            complete = [self.members.get(x, {}).get("complete_chain", False) for x in markets]
            missing = [x for x, ok in zip(markets, complete, strict=True) if not ok]
            groups = [(self.first_stage.get(x) or {}).get("dependence_group") for x in markets]
            disjoint = (len(groups) == 2 and None not in groups and groups[0] != groups[1]
                        and not used.intersection(groups))
            both = bool(t) and all(complete)
            if both and disjoint:
                used.update(groups)
            result.append({
                "trigger_id": tid, "stratum": a.get("stratum"),
                "triggered_market": t["market_id"] if t else None,
                "control_market": a["market_id"],
                "dependence_groups": groups, "group_disjoint": disjoint,
                "both_complete": both,
                "group_disjoint_complete": both and disjoint,
                "unobserved_members": missing,
                "unobserved_causes": {x: self.members[x]["causes"] for x in missing
                                      if x in self.members},
                "state_agreement": {x: self.members.get(x, {}).get("state_agreement")
                                    for x in markets},
                "counts_as": "group-disjoint mechanism execution; not an independent "
                             "observation (all origins share run-level shocks)",
            })
    return result


def incomplete_data_only(members, incomplete):
    """True only if at least one pair member is incomplete and EVERY cause of EVERY incomplete
    member is a classified DATA cause (an unknown member or an empty cause list is not)."""
    if not incomplete:
        return False
    for market in incomplete:
        causes = (members.get(market) or {}).get("causes") or []
        if not causes or any(c.get("class") not in DATA_CLASSES for c in causes):
            return False
    return True


def _summarise(self, gates, pairs, common):
    ms = list(self.members.values())
    states = Counter(
        "unauthenticated" if m["stages"]["screening"].get("effective_state")
        in ("triggered", "untriggered") and not m.get("authenticated_state")
        else m["stages"]["screening"].get("effective_state") for m in ms)
    authenticated = sum(1 for m in ms if m.get("authenticated_state"))
    data_unavailable = sum(
        1 for m in ms if not m.get("authenticated_state")
        and (m["stages"]["screening"].get("causes") or [])
        and all(c.get("class") in DATA_CLASSES for c in m["stages"]["screening"]["causes"]))
    triggers = self.plan.get("triggers_in_scope")
    drawn = self.plan.get("pairs_drawn")
    fill = (Fraction(drawn, triggers) if isinstance(triggers, int) and triggers
            and isinstance(drawn, int) else None)
    incomplete = [x for p in pairs for x in p["unobserved_members"]]
    data_only = incomplete_data_only(self.members, incomplete)
    agreement = Counter(self.members[m].get("state_agreement") for m in self.activated)
    return {
        "n_screened": len(ms), "n_activated": len(self.activated),
        "engineering_findings": sum(1 for f in self.r.findings if f["class"] == ENGINEERING),
        "failed_gates": sorted(k for k, v in gates.items()
                               if not v["pass"] and (self.enforce or k != "E0")),
        "common_mode": common,
        "authenticated_state_members": authenticated,
        "screening_coverage": f"{authenticated}/{len(ms)}" if ms else None,
        "screening_coverage_ok": bool(ms) and Fraction(authenticated, len(ms))
        >= MIN_SCREENING_COVERAGE,
        "screening_unassessable_data_reason": data_unavailable,
        "n_triggered_members": states.get("triggered", 0),
        "n_untriggered_members": states.get("untriggered", 0),
        "n_unavailable_members": states.get("unavailable", 0),
        "strata_with_trigger": self.plan.get("strata_with_trigger"),
        "triggers_in_scope": triggers, "pairs_drawn": drawn,
        "fill": None if fill is None else f"{drawn}/{triggers}",
        "fill_ok": fill is not None and fill >= PASS_FILL,
        "control_scarcity_strata": self.plan.get("control_scarcity_strata"),
        "pairs_both_complete": sum(1 for p in pairs if p["both_complete"]),
        "group_disjoint_complete_pairs": sum(1 for p in pairs if p["group_disjoint_complete"]),
        "incomplete_pair_members_data_only": data_only,
        "state_disagreements": agreement.get("disagree", 0),
        "state_agreement_counts": dict(sorted((str(k), v) for k, v in agreement.items())),
        "state_disagreement_note": "descriptive only: roles are fixed at screening and never "
                                   "relabelled; Phase 4 uses the origin_window imbalance fields",
        "pass_requires": "fill >= 0.8 with >= 4 triggers in scope and >= 3 group-disjoint "
                         "complete pairs",
    }


def decide_outcome(summary):
    """D120 exhaustive outcome classes (first match)."""
    reasons = []
    if summary["engineering_findings"]:
        reasons.append(f"{summary['engineering_findings']} engineering finding(s)")
    if summary["failed_gates"]:
        reasons.append("failed gates: " + ",".join(summary["failed_gates"]))
    if summary["common_mode"]:
        reasons.append("common-mode pattern: " + "; ".join(summary["common_mode"]))
    if reasons:
        return "FAIL", reasons
    floor = []
    strata = summary.get("strata_with_trigger")
    if not isinstance(strata, int) or strata < MIN_TRIGGERS:
        floor.append(f"fewer than {MIN_TRIGGERS} drawn strata with a trigger ({strata})")
    if not summary.get("screening_coverage_ok"):
        floor.append("screening coverage below 80% for classified data reasons "
                     f"({summary.get('screening_coverage')})")
    if floor:
        return "INCONCLUSIVE", floor
    triggers = summary.get("triggers_in_scope")
    if (summary["fill_ok"] and isinstance(triggers, int) and triggers >= MIN_TRIGGERS
            and summary["group_disjoint_complete_pairs"] >= MIN_COMPLETE_PAIRS):
        return "PASS", [f"fill {summary['fill']} with {triggers} triggers in scope and "
                        f"{summary['group_disjoint_complete_pairs']} group-disjoint complete "
                        "pairs"]
    if not summary["fill_ok"]:
        return ("PASS_WITH_LIMITATION:control_scarcity",
                [f"fill {summary['fill']} < 0.8: a drawn trigger had no untriggered member in "
                 "its screened stratum; next step is the predeclared screen-the-whole-stratum "
                 "fallback"])
    if summary["incomplete_pair_members_data_only"]:
        return ("PASS_WITH_LIMITATION:pair_member_unobserved_data_reason",
                [f"only {summary['group_disjoint_complete_pairs']} group-disjoint complete "
                 "pairs; every incomplete pair member is limited by a classified DATA cause"])
    return "FAIL", ["fewer than 3 complete pairs without a classified DATA cause"]


def _timeline(self):
    result = _base_timeline(self)
    roles = {a.get("market_id") for a in self.plan.get("assignments") or []}
    margins = result["margins"]
    margins["assessment_ages_at_activation"] = [
        a for a in margins.get("assessment_ages_at_activation", []) if a["market_id"] in roles]
    binding = []
    for market in self.activated:
        m = self.members[market]
        k = m["binding_index"]
        report = self.r.pair(self.worker / f"fs2_socket_window_{k:03d}", "socket_window_report",
                             "window", market, required=False) or {}
        quote = m.get("pre_quote") or {}
        sent, received = _utc(report.get("subscription_sent_at")), _utc(quote.get("received_at"))
        if sent and received:
            binding.append({"market_id": market, "binding_age_at_subscription_s":
                            _seconds(sent, received)})
    margins["binding_age_at_subscription"] = binding
    declared = _utc(self.screen_policy.get("declared_at"))
    sealed = _utc(self.screen_available())
    margins["screening_s"] = _seconds(sealed, declared) if declared and sealed else None
    return result


def _diagnostics(self):
    ms = [self.members[m] for m in self.activated]
    observed = sum(1 for m in ms if m["stages"]["origin"].get("state") == "observed")
    ages = [a["window_age_at_freeze_s"] for a in self.timeline()["margins"].get(
        "window_age_at_freeze", []) if a.get("window_age_at_freeze_s") is not None]
    return {
        "n_screened": len(self.members), "n_activated": len(ms),
        "observed_origins": observed,
        "eligible_completed_histories": sum(
            1 for m in ms if m["stages"]["history"].get("eligible") is True),
        "valid_targets": sum(1 for m in ms if m["stages"]["target"].get("state") == "observed"),
        "max_window_age_at_freeze_s": max(ages) if ages else None,
        "screening_states": dict(sorted(Counter(
            str(m["stages"]["screening"].get("state")) for m in self.members.values()).items())),
        "binding_states": dict(sorted(Counter(str(m.get("binding_state")) for m in ms).items())),
        "descriptive_only": "not acceptance",
    }


def _public(self, m):
    result = {
        "market_id": m["market_id"], "token_id": m["token_id"],
        "activated": bool(m.get("activated")),
        "dependence_group": (self.first_stage.get(m["market_id"]) or {}).get("dependence_group"),
        "fee_category": (self.first_stage.get(m["market_id"]) or {}).get("fee_category"),
        "roles": [{k: a.get(k) for k in ("arm", "stratum", "trigger_id", "matched_trigger_ids",
                                         "assessment_state")} for a in m["roles"]],
        "effective_assessment_state": m.get("assessment_state"),
        "authenticated_state": bool(m.get("authenticated_state")),
        "stages": {name: dict(info) for name, info in m["stages"].items()},
        "complete_chain": m["complete_chain"], "causes": m["causes"],
    }
    if m.get("activated"):
        result.update(binding_state=m.get("binding_state"),
                      state_agreement=m.get("state_agreement"))
    return result


_D120Evaluation.load = _load
_D120Evaluation.binding_stage = binding_stage
_D120Evaluation.member_stages = _member_stages
_D120Evaluation.identity_gate = _identity_gate
_D120Evaluation.frozen_failures = _frozen_failures
_D120Evaluation.role_replay = role_replay
_D120Evaluation.dependence_failures = dependence_failures
_D120Evaluation.gates = _gates
_D120Evaluation.accounting = _accounting
_D120Evaluation.common_mode = _common_mode
_D120Evaluation.pairs = _pairs
_D120Evaluation.summarise = _summarise
_D120Evaluation.timeline = _timeline
_D120Evaluation.diagnostics = _diagnostics
_D120Evaluation.public = _public
OVERRIDES["decide_outcome"] = decide_outcome
_GLOBALS["decide_outcome"] = decide_outcome
D120_METHODS = ("load", "binding_stage", "member_stages", "identity_gate", "frozen_failures",
                "role_replay", "dependence_failures", "gates", "accounting", "common_mode",
                "pairs", "summarise", "timeline", "diagnostics", "public")


def evaluate_d120(panel_root, selection_root=None, worker_root=None, runtime_root=None, *,
                  activation_root=None, launch_commit=None, protocol_check=True):
    """Evaluate one retained D120 run; the only authoritative entry point.

    Same contract as ``evaluate_d116``: ``launch_commit`` is required (E0 fails closed without
    it); root overrides and ``protocol_check=False`` force FAIL and ``authoritative`` false; any
    exception yields a FAIL report.
    """
    return _evaluate(panel_root, selection_root, worker_root, runtime_root,
                     activation_root=activation_root, launch_commit=launch_commit,
                     protocol_check=protocol_check)


def evaluate_d120_logic_only_test_aid(panel_root, **roots):
    """TEST AID ONLY: never authoritative (see ``evaluate_d116_logic_only_test_aid``)."""
    return _logic_only(panel_root, **roots)
