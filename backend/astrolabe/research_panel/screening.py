"""Predeclare a sampled screening batch and verify measured control eligibility.

No source requests, origins, SQL admission or claim of prospective panel acceptance.
The first-stage scheduled draw remains intact; second-stage probabilities are conditional.
"""

import json
import secrets
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _sync_directory
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _time
from astrolabe.feature_store.types import canonical_json

from .assessments import TriggerAssessment, TriggerAssessmentPolicy
from .build_identity import verified_panel_build
from .identity_comparison import VERSION as IDENTITY_POLICY
from .identity_comparison import compare_mapping
from .input_read import _canonical
from .panel_selection import VERSIONS as SELECTION_VERSIONS
from .panel_selection import freshness
from .sampling import FrameMember, SamplingProtocol, plan_sample
from .selection import _member, read_selection
from .trigger_computation import (
    CHILD,
    SnapshotTriggerPolicy,
    declare_snapshot_trigger,
    read_snapshot_trigger,
)
from .window_computation import LIMITS, _check, _save

VERSION = "fs2-screening-v1"
IDENTITY_VERSION = "fs2-screening-identity-v2"
OWNED_VERSION = "fs2-screening-owned-selection-v3"
OWNED_READ_MODE = "full_selection_before_sources; full_cold_replay_before_acceptance"
PER_DECISION_BYTES = LIMITS["max_output_bytes"] + 2 * LIMITS["max_artifact_bytes"]


@dataclass(frozen=True)
class ScreeningPolicy:
    max_window_age_seconds: int
    max_assessment_age_seconds: int

    def __post_init__(self):
        for value in asdict(self).values():
            if type(value) is not int or not 0 <= value <= 86400:
                raise ValueError("bounded explicit screening freshness required")


def _selected(selection):
    report = read_selection(selection)
    if report["schema_version"] not in SELECTION_VERSIONS:
        raise ValueError("fresh declaration-bound selection required")
    policy, _ = _pair(selection, "selection_policy")
    inventory, _ = _pair(selection, "inventory")
    wanted = {r["market_id"]: r for r in report["plan"]["assignments"]}
    if not 1 <= len(wanted) <= 256 or any(r["arm"] != "scheduled" for r in wanted.values()):
        raise ValueError("bounded scheduled first-stage sample required")
    selected = []
    for entry in inventory["pages"]:
        page, ack = _pair(selection / "pages" / entry["capture_id"], "projection")
        if ack["payload_hash"] != entry["projection_hash"]:
            raise ValueError("selection projection changed during screening read")
        for row in page["rows"]:
            if row["market_id"] not in wanted or row["duplicate_of"]:
                continue
            member = _member(row, ack["durable_ack"], policy["declared_at"])
            assignment = wanted[row["market_id"]]
            if (
                member is None
                or member.token_id != assignment["token_id"]
                or member.source_observation_id != assignment["source_observation_id"]
            ):
                raise ValueError("screened member differs from sampled assignment")
            selected.append(
                {
                    "member": asdict(member),
                    "identity": row["identity"],
                    "screening_assignment": assignment,
                }
            )
    if len(selected) != len(wanted):
        raise ValueError("screening selection member closure differs")
    return report, policy, sorted(selected, key=lambda r: r["member"]["market_id"])


def _paths(root, count):
    suffix = root.name.removeprefix("fs2_screening_")
    return [
        {
            "declaration_root": str(root.with_name(f"fs2_trigger_declaration_{suffix}_{i:03d}")),
            "book_root": str(root.with_name(f"fs2_book_computation_screen_{suffix}_{i:03d}")),
        }
        for i in range(count)
    ]


def declare_screening(selection_root, *, output_root, rule, policy, identity_policy=None):
    """Own every assignment before its D066 declaration/source acquisition; no caller seed."""
    frozen, _ = _declare_screening(
        selection_root, output_root=output_root, rule=rule, policy=policy,
        identity_policy=identity_policy, owned=False)
    return frozen


def _prepare_owned_screening(selection_root, *, output_root, rule, policy):
    """Return a process-owned finish operation after authenticating the full selection.

    No supplied payload, cached hash or persisted context can mint this operation.
    Cold readers still reauthenticate every dependency. Its output cannot admit an origin.
    """
    frozen, state = _declare_screening(
        selection_root, output_root=output_root, rule=rule, policy=policy,
        identity_policy=IDENTITY_POLICY, owned=True)
    root = _canonical(output_root)
    _, ack = _pair(root, "screening_policy")
    policy_hash = ack["payload_hash"]
    # Isolate the owned proof from the mutable dictionary returned to the collector.
    proof = canonical_json(state)
    if len(proof.encode()) > LIMITS["max_artifact_bytes"]:
        raise ValueError("owned screening selection context exceeds bounded size")

    def finish():
        if _pair(root, "screening_policy")[1]["payload_hash"] != policy_hash:
            raise ValueError("owned screening policy changed after authentication")
        return _finish_screening(root, selected_state=json.loads(proof))

    return frozen, finish


def _declare_screening(selection_root, *, output_root, rule, policy, identity_policy, owned):
    if identity_policy not in (None, IDENTITY_POLICY):
        raise ValueError("unsupported screening identity policy")
    selection, root = _canonical(selection_root), _canonical(output_root)
    if (
        not root.name.startswith("fs2_screening_")
        or root == selection
        or root in selection.parents
        or selection in root.parents
    ):
        raise ValueError("separate canonical screening root required")
    if root.exists():
        raise FileExistsError("screening attempt already owned")
    if type(rule) is not SnapshotTriggerPolicy or type(policy) is not ScreeningPolicy:
        raise ValueError("explicit screening rule and freshness required")
    started, read_started = time.monotonic(), _clock()
    report, selection_policy, selected = _selected(selection)
    read_completed = _clock()
    freshness(
        selection_policy,
        {
            "interval_start": report["source_interval_start"],
            "interval_end": report["source_interval_end"],
            "frame_available_at": report["original_frame_available_at"],
        },
        read_completed,
    )
    paths = _paths(root, len(selected))
    if any(_canonical(p).exists() for item in paths for p in item.values()):
        raise FileExistsError("screening requires fresh assigned computation paths")
    # This boundary owns declarations/results only. A collector must additionally reserve
    # its bounded source, book, recovery and complete origin/control/target costs.
    required = (
        LIMITS["free_reserve_bytes"]
        + len(selected) * PER_DECISION_BYTES
        + LIMITS["max_output_bytes"]
    )
    if shutil.disk_usage(root.parent).free < required:
        raise ValueError("screening declaration/result capacity unavailable")
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    frozen = {
        "schema_version": (OWNED_VERSION if owned
                           else IDENTITY_VERSION if identity_policy else VERSION),
        **({"selection_read_mode": OWNED_READ_MODE} if owned else {}),
        **({"identity_policy": identity_policy} if identity_policy else {}),
        "build": verified_panel_build(),
        "limits": dict(LIMITS),
        "selection_root": str(selection),
        "selection_report_hash": report["selection_report_hash"],
        "selection_available_at": report["selection_available_at"],
        "read_started_at": read_started,
        "read_completed_at": read_completed,
        "declared_at": _clock(),
        "seed": secrets.token_hex(32),
        "rule": asdict(rule),
        "freshness": asdict(policy),
        "selected": [{**row, **path} for row, path in zip(selected, paths, strict=True)],
        "protocol": selection_policy["panel_protocol"],
        "probability_edges": report["plan"]["protocol"]["probability_edges"],
        "liquidity_edges": report["plan"]["protocol"]["liquidity_edges"],
        "source_provenance_class": report["provenance_class"],
        "reserved_declaration_result_bytes": required - LIMITS["free_reserve_bytes"],
        "collector_reservation_required": True,
    }
    _save(root, "screening_policy", frozen, started)
    for item in frozen["selected"]:
        _check(root, started)
        declare_snapshot_trigger(
            _canonical(item["declaration_root"]),
            book_root=_canonical(item["book_root"]),
            market_id=item["member"]["market_id"],
            token_id=item["member"]["token_id"],
            policy=rule,
        )
    # Retain only the bounded state needed for this draw, not the population inventory.
    state = (
        {k: report[k] for k in (
            "selection_report_hash", "selection_available_at", "provenance_class",
            "source_interval_start", "source_interval_end", "original_frame_available_at")}
        | {"plan": {"protocol": {k: report["plan"]["protocol"][k]
                                 for k in ("probability_edges", "liquidity_edges")}}},
        {"panel_protocol": selection_policy["panel_protocol"]}, selected)
    return frozen, state


def _policy(root):
    value, ack = _pair(root, "screening_policy")
    rule = SnapshotTriggerPolicy(**value["rule"])
    ScreeningPolicy(**value["freshness"])
    if (
        value["schema_version"] not in {VERSION, IDENTITY_VERSION, OWNED_VERSION}
        or (value["schema_version"] != VERSION) != ("identity_policy" in value)
        or (value["schema_version"] == OWNED_VERSION) != ("selection_read_mode" in value)
        or ("selection_read_mode" in value and value["selection_read_mode"] != OWNED_READ_MODE)
        or ("identity_policy" in value and value["identity_policy"] != IDENTITY_POLICY)
        or value["build"] != verified_panel_build()
        or value["limits"] != LIMITS
        or not _ordered_clocks(
            value["selection_available_at"],
            value["read_started_at"],
            value["read_completed_at"],
            value["declared_at"],
            ack["durable_ack"],
        )
    ):
        raise ValueError("screening policy/build/chronology differs")
    count = len(value["selected"])
    if (
        not 1 <= count <= 256
        or len({r["member"]["market_id"] for r in value["selected"]}) != count
        or value["reserved_declaration_result_bytes"]
        != count * PER_DECISION_BYTES + LIMITS["max_output_bytes"]
        or value["collector_reservation_required"] is not True
    ):
        raise ValueError("bounded unique screening assignment/reservation required")
    expected = _paths(root, count)
    for item, paths in zip(value["selected"], expected, strict=True):
        if any(item[k] != v for k, v in paths.items()):
            raise ValueError("screening assigned path differs")
        declaration, da = _pair(_canonical(item["declaration_root"]), "trigger_declaration")
        if (
            declaration["rule"] != asdict(rule)
            or declaration["book_root"] != item["book_root"]
            or declaration["market_id"] != item["member"]["market_id"]
            or declaration["token_id"] != item["member"]["token_id"]
            or not _ordered_clocks(
                ack["durable_ack"], declaration["declared_at"], da["durable_ack"]
            )
        ):
            raise ValueError("screening assignment/declaration lineage differs")
    return value, ack


def _inputs(policy, cutoff):
    records, states = [], []
    started = time.monotonic()
    for item in policy["selected"]:
        if time.monotonic() - started > LIMITS["max_seconds"]:
            raise ValueError("screening evidence read deadline exceeded")
        parent = _canonical(item["declaration_root"])
        result = parent / CHILD
        if not result.exists():
            # A missing journal stays unassessed; recovery rejects later additions.
            states.append({"market_id": item["member"]["market_id"], "state": "not_assessed"})
            continue
        summary = read_snapshot_trigger(result)  # corruption/torn evidence is a hard refusal
        facts, ack = _pair(result, "trigger_computation_facts")
        p = facts["projection"]
        if (
            ack["payload_hash"] != summary["computation_hash"]
            or p["market_id"] != item["member"]["market_id"]
            or p["token_id"] != item["member"]["token_id"]
            or p["rule_hash"] != content_hash(policy["rule"])
            or not _ordered_clocks(summary["computation_available_at"], cutoff)
        ):
            raise ValueError("screening decision identity/rule/cutoff differs")
        state, reasons = p["state"], list(p["reasons"])
        mapping = p["mapping"]
        comparison = None
        matches = (mapping is not None
                   and mapping["mapping_version"] == item["identity"]["mapping_version"])
        if policy['schema_version'] in {IDENTITY_VERSION, OWNED_VERSION}:
            comparison = compare_mapping(item['identity'],
                                         mapping['mapping_version'] if mapping else None)
            matches = comparison['core_identity_equal']
        if not matches:
            state, reasons = "unavailable", reasons + ["frame_mapping_changed_or_unavailable"]
        if p["provenance_class"] != policy["source_provenance_class"]:
            raise ValueError("mixed screening provenance cannot be promoted")
        states.append(
            {
                "market_id": p["market_id"],
                "summary": summary,
                "projection_hash": p["projection_hash"],
                **({"identity_comparison": comparison} if comparison is not None else {}),
                "state": state,
                "reasons": reasons,
            }
        )
        if p["input_window_start"] is None or p["input_window_end"] is None:
            raise ValueError("assessment has no authenticated input window; retain unadmitted")
        records.append(
            TriggerAssessment(
                market_id=p["market_id"],
                token_id=p["token_id"],
                policy_hash=p["rule_hash"],
                evidence_id=summary["computation_hash"],
                state=state,
                input_window_start=_time(p["input_window_start"]),
                input_window_end=_time(p["input_window_end"]),
                available_at=_time(summary["computation_available_at"]),
                unavailable_reason=";".join(reasons)[:256] if state == "unavailable" else None,
            )
        )
    return records, states


def _plan(policy, ack, cutoff, records):
    members = []
    for row in policy["selected"]:
        member = dict(row["member"])
        for key in ("available_at", "group_available_at", "trigger_available_at"):
            if member[key] is not None:
                if not isinstance(member[key], dict) or set(member[key]) != {"$utc"}:
                    raise ValueError("canonical UTC member clock required")
                member[key] = datetime.fromisoformat(member[key]["$utc"].replace("Z", "+00:00"))
        members.append(FrameMember(**member))
    p = policy["protocol"]
    protocol = SamplingProtocol(
        policy["seed"],
        len(members),
        p["triggered_per_stratum"],
        p["controls_per_trigger"],
        len(members),
        tuple(policy["probability_edges"]),
        tuple(policy["liquidity_edges"]),
    )
    result = plan_sample(
        protocol,
        members,
        cutoff=_time(cutoff),
        frame_scope="predeclared scheduled screen sample; complete frame remains in selection",
        frame_status="explicit_list",
        frame_evidence_ids=[policy["selection_report_hash"]],
        max_frame_members=256,
        assessment_policy=TriggerAssessmentPolicy(
            content_hash(policy["rule"]), _time(ack["durable_ack"]), **policy["freshness"]
        ),
        trigger_assessments=records,
    )
    first = {r["member"]["market_id"]: r["screening_assignment"] for r in policy["selected"]}
    for assignment in result["assignments"]:
        assignment["screening_inclusion_probability"] = first[assignment["market_id"]][
            "inclusion_probability"
        ]
        assignment["probability_scope"] = "conditional on screened sample and observed states"
    result.pop("plan_hash")
    result["global_arm_inclusion_probability"] = None
    result["global_arm_probability_reason"] = "second-stage pool depends on measured states"
    result["origin_admitted"] = False
    return {**result, "plan_hash": content_hash(result)}


def finish_screening(root):
    return _finish_screening(root)


def _finish_screening(root, *, selected_state=None):
    root, started = _canonical(root), time.monotonic()
    policy, ack = _policy(root)
    # Exclusive completion intent; no second selection cutoff or retuning after results.
    if (root / "screening_completion_policy.json").exists():
        raise FileExistsError("screening completion already attempted")
    _save(root, "screening_completion_policy", {"read_started_at": _clock()}, started)
    _, ca = _pair(root, "screening_completion_policy")
    cutoff = _clock()
    records, states = _inputs(policy, cutoff)
    computed_at = _clock()
    plan = _plan(policy, ack, cutoff, records)
    _save(
        root,
        "screening_report",
        {
            "schema_version": policy["schema_version"],
            "policy_hash": ack["payload_hash"],
            "completion_hash": ca["payload_hash"],
            "cutoff": cutoff,
            "read_completed_at": computed_at,
            "computed_at": _clock(),
            "states": states,
            "plan": plan,
            "provenance_class": policy["source_provenance_class"],
            "state": "screening_sealed",
            "origin_admitted": False,
            "accepted_panel": False,
        },
        started,
    )
    return _read_screening(root, selected_state=selected_state)


def read_screening(root):
    """Cold recovery always authenticates the complete selection and source dependencies."""
    return _read_screening(root)


def _read_screening(root, *, selected_state=None):
    root, started = _canonical(root), time.monotonic()
    if {p.name for p in root.iterdir()} != {
        n + suffix
        for n in ("screening_policy", "screening_completion_policy", "screening_report")
        for suffix in (".json", "_ack.json")
    }:
        raise ValueError("complete screening journal required")
    _check(root, started)
    policy, ack = _policy(root)
    if selected_state is not None and policy["schema_version"] != OWNED_VERSION:
        raise ValueError("owned selection cannot replace legacy recovery")
    original, selection_policy, selected = (
        _selected(_canonical(policy["selection_root"])) if selected_state is None
        else selected_state)

    if (
        original["selection_report_hash"] != policy["selection_report_hash"]
        or original["selection_available_at"] != policy["selection_available_at"]
        or policy["protocol"] != selection_policy["panel_protocol"]
        or policy["source_provenance_class"] != original["provenance_class"]
        or policy["probability_edges"] != original["plan"]["protocol"]["probability_edges"]
        or policy["liquidity_edges"] != original["plan"]["protocol"]["liquidity_edges"]
        or canonical_json(selected)
        != canonical_json(
            [
                {k: r[k] for k in ("member", "identity", "screening_assignment")}
                for r in policy["selected"]
            ]
        )
    ):
        raise ValueError("screening source selection differs")
    completion, ca = _pair(root, "screening_completion_policy")
    report, ra = _pair(root, "screening_report")
    if (
        report["schema_version"] != policy["schema_version"]
        or report["policy_hash"] != ack["payload_hash"]
        or report["completion_hash"] != ca["payload_hash"]
        or not _ordered_clocks(
            ack["durable_ack"],
            completion["read_started_at"],
            ca["durable_ack"],
            report["cutoff"],
            report["read_completed_at"],
            report["computed_at"],
            ra["durable_ack"],
        )
    ):
        raise ValueError("screening completion chronology differs")
    freshness(
        selection_policy,
        {
            "interval_start": original["source_interval_start"],
            "interval_end": original["source_interval_end"],
            "frame_available_at": original["original_frame_available_at"],
        },
        report["cutoff"],
    )
    records, states = _inputs(policy, report["cutoff"])
    plan = _plan(policy, ack, report["cutoff"], records)
    if (
        canonical_json(plan) != canonical_json(report["plan"])
        or states != report["states"]
        or report["provenance_class"] != policy["source_provenance_class"]
        or report["state"] != "screening_sealed"
        or report["origin_admitted"] is not False
        or report["accepted_panel"] is not False
    ):
        raise ValueError("screening evidence or exact plan replay differs")
    _check(root, started)
    return {
        **report,
        "screening_report_hash": ra["payload_hash"],
        "screening_available_at": ra["durable_ack"],
    }
